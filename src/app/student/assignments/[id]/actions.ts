"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";
import { q, q1 } from "@/db/pool";
import { requireRole } from "@/lib/session";
import { computeGrade, persistGrade } from "@/lib/grading";
import { extractFileText } from "@/lib/grading/extract";

export type SubmitState = { error?: string } | undefined;

function str(value: FormDataEntryValue | null): string {
  return typeof value === "string" ? value.trim() : "";
}

export async function submitAssignment(
  _prev: SubmitState,
  formData: FormData,
): Promise<SubmitState> {
  const student = await requireRole("student");
  const assignmentId = str(formData.get("assignment_id"));

  const a = await q1<{
    id: string;
    type: string;
    release_mode: string;
    course_id: string;
    enrolled: boolean;
  }>(
    `SELECT a.id, a.type, a.release_mode, t.course_id,
            EXISTS (
              SELECT 1 FROM enrollments e
               WHERE e.course_id = t.course_id AND e.student_id = $2
            ) AS enrolled
     FROM assignments a
     JOIN topics t ON t.id = a.topic_id
     WHERE a.id = $1`,
    [assignmentId, student.id],
  );
  if (!a || !a.enrolled) return { error: "Tugas tidak ditemukan." };

  const existing = await q1<{ id: string }>(
    "SELECT id FROM submissions WHERE assignment_id = $1 AND student_id = $2",
    [a.id, student.id],
  );
  if (existing) return { error: "Pengumpulan sudah terkunci." };

  let answer_text: string | null = null;
  let answers: string[] = [];
  let file_name: string | null = null;
  let extracted_text: string | null = null;
  let extraction_ok: boolean | null = null;

  if (a.type === "essay") {
    answer_text = str(formData.get("answer"));
    if (!answer_text) return { error: "Tulis jawaban terlebih dahulu." };
  }

  if (a.type === "pg") {
    const questions = await q<{
      position: number;
      options: { key: string; text: string }[] | null;
    }>(
      `SELECT position, options FROM assignment_questions
       WHERE assignment_id = $1 ORDER BY position`,
      [a.id],
    );
    if (questions.length === 0) return { error: "Soal belum tersedia." };

    let parsed: unknown;
    try {
      parsed = JSON.parse(str(formData.get("answers")) || "[]");
    } catch {
      parsed = null;
    }
    const submitted = Array.isArray(parsed)
      ? parsed.map((v) => String(v ?? "").trim())
      : [];
    if (submitted.length !== questions.length) {
      return { error: "Jawaban tidak lengkap. Kerjakan seluruh soal." };
    }
    for (let i = 0; i < questions.length; i++) {
      const rawOpts = questions[i].options;
      const opts = Array.isArray(rawOpts) ? rawOpts : [];
      if (!submitted[i] || !opts.some((o) => o.key === submitted[i])) {
        return { error: `Soal ke-${i + 1}: pilih salah satu jawaban.` };
      }
    }
    answers = submitted;
  }

  if (a.type === "pdf" || a.type === "docx") {
    const file = formData.get("file");
    const hasFile =
      file instanceof File && file.size > 0 && file.name.trim() !== "";
    if (!hasFile) return { error: "Pilih berkas terlebih dahulu." };
    const name = file.name.toLowerCase();
    const wantExt = a.type === "pdf" ? ".pdf" : ".docx";
    if (!name.endsWith(wantExt)) {
      return { error: `Berkas harus berformat ${wantExt.slice(1).toUpperCase()}.` };
    }
    file_name = file.name;
    const result = await extractFileText(file);
    if (result.ok) {
      extracted_text = result.text;
      extraction_ok = true;
    } else {
      extracted_text = null;
      extraction_ok = false;
    }
  }

  const sub = await q1<{ id: string }>(
    `INSERT INTO submissions
       (assignment_id, student_id, answer_text, answers, file_name,
        extracted_text, extraction_ok, status, submitted_at, updated_at)
     VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7, 'submitted', now(), now())
     RETURNING id`,
    [
      a.id,
      student.id,
      answer_text,
      JSON.stringify(answers),
      file_name,
      extracted_text,
      extraction_ok,
    ],
  );
  if (!sub) return { error: "Gagal mengirim jawaban." };

  if (a.release_mode === "langsung") {
    const outcome = await computeGrade(sub.id);
    if (outcome.ok) {
      await persistGrade({
        submissionId: sub.id,
        data: outcome,
        actorId: null,
        publish: true,
      });
    } else {
      await q1(
        "UPDATE submissions SET status = 'needs_review', updated_at = now() WHERE id = $1",
        [sub.id],
      );
    }
  }

  revalidatePath(`/student/assignments/${a.id}`);
  revalidatePath(`/student/courses/${a.course_id}`);
  const store = await cookies();
  store.set("nilai_flash", `terkirim:${a.id}:${student.id}`, {
    path: "/",
    maxAge: 30,
    sameSite: "lax",
    httpOnly: false,
  });
  redirect(`/student/assignments/${a.id}`);
}
