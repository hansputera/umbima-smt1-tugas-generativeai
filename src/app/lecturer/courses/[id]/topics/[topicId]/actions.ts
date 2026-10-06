"use server";

import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";
import { q1 } from "@/db/pool";
import { requireLecturerTopic } from "@/lib/lecturer";

export type TopicSaveState = {
  errors?: Record<string, string>;
  error?: string;
  info?: string;
} | undefined;

export type AssignmentFormState = {
  errors?: Record<string, string>;
  error?: string;
} | undefined;

type BlockInput = {
  type: string;
  body?: string;
  url?: string;
  file_name?: string;
};

function str(value: FormDataEntryValue | null): string {
  return typeof value === "string" ? value.trim() : "";
}

export async function saveTopic(
  _prev: TopicSaveState,
  formData: FormData,
): Promise<TopicSaveState> {
  const topicId = str(formData.get("topic_id"));
  const { topic, course } = await requireLecturerTopic(topicId);

  const title = str(formData.get("title"));
  const weekRaw = str(formData.get("week"));

  const errors: Record<string, string> = {};
  if (!title) errors.title = "Judul wajib diisi.";
  const week = Number(weekRaw);
  if (!Number.isInteger(week) || week < 1 || week > 30) {
    errors.week = "Minggu harus 1–30.";
  }
  if (Object.keys(errors).length === 0 && week !== topic.week) {
    const clash = await q1(
      "SELECT 1 AS ok FROM topics WHERE course_id = $1 AND week = $2 AND id <> $3",
      [course.id, week, topic.id],
    );
    if (clash) errors.week = "Minggu sudah dipakai.";
  }
  if (Object.keys(errors).length > 0) return { errors };

  let blocks: BlockInput[] = [];
  try {
    const parsed = JSON.parse(str(formData.get("blocks")) || "[]");
    if (Array.isArray(parsed)) blocks = parsed as BlockInput[];
  } catch {
    return { error: "Data materi tidak valid." };
  }

  for (let i = 0; i < blocks.length; i++) {
    const b = blocks[i];
    if (!["richtext", "link", "file"].includes(b.type)) {
      return { error: `Materi ke-${i + 1}: tipe tidak dikenal.` };
    }
    if (b.type === "richtext" && !(b.body ?? "").trim()) {
      return { error: `Materi ke-${i + 1}: teks wajib diisi.` };
    }
    if (b.type === "link") {
      const url = (b.url ?? "").trim();
      if (!url) return { error: `Materi ke-${i + 1}: URL wajib diisi.` };
      if (!/^https?:\/\//i.test(url)) {
        return { error: `Materi ke-${i + 1}: URL harus diawali http(s).` };
      }
    }
    if (b.type === "file" && !(b.file_name ?? "").trim()) {
      return { error: `Materi ke-${i + 1}: nama berkas wajib diisi.` };
    }
  }

  await q1("UPDATE topics SET title = $2, week = $3 WHERE id = $1", [
    topic.id,
    title,
    week,
  ]);
  await q1("DELETE FROM materi_blocks WHERE topic_id = $1", [topic.id]);
  for (let i = 0; i < blocks.length; i++) {
    const b = blocks[i];
    await q1(
      `INSERT INTO materi_blocks (topic_id, type, body, url, file_name, position)
       VALUES ($1, $2, $3, $4, $5, $6)`,
      [
        topic.id,
        b.type,
        b.type === "richtext" ? (b.body ?? "") : b.type === "link" ? (b.body ?? "") : null,
        b.type === "link" ? (b.url ?? "") : null,
        b.type === "file" ? (b.file_name ?? "") : null,
        i,
      ],
    );
  }

  revalidatePath(`/lecturer/courses/${course.id}/topics/${topic.id}`);
  revalidatePath(`/lecturer/courses/${course.id}`);
  revalidatePath(`/student/courses/${course.id}`);
  return { info: "Pertemuan disimpan." };
}

type PgQuestionInput = {
  question: string;
  options: { key: string; text: string }[];
  answer_key: string;
};

export async function createAssignment(
  _prev: AssignmentFormState,
  formData: FormData,
): Promise<AssignmentFormState> {
  const topicId = str(formData.get("topic_id"));
  const { topic, course } = await requireLecturerTopic(topicId);

  const title = str(formData.get("title"));
  const type = str(formData.get("type"));
  const dueRaw = str(formData.get("due_at"));

  const errors: Record<string, string> = {};
  if (!title) errors.title = "Judul wajib diisi.";
  if (!["essay", "pg", "pdf", "docx"].includes(type)) {
    errors.type = "Tipe tidak dikenal.";
  }
  let dueAt: string | null = null;
  if (dueRaw) {
    const parsedDue = new Date(dueRaw);
    if (Number.isNaN(parsedDue.getTime())) errors.due_at = "Tenggat tidak valid.";
    else dueAt = parsedDue.toISOString();
  }

  let questions: PgQuestionInput[] = [];

  if (type === "pg") {
    let parsed: unknown;
    try {
      parsed = JSON.parse(str(formData.get("questions")) || "[]");
    } catch {
      parsed = null;
    }
    if (!Array.isArray(parsed) || parsed.length === 0) {
      errors.question = "Tulis minimal satu soal.";
    } else {
      questions = parsed as PgQuestionInput[];
      for (let i = 0; i < questions.length; i++) {
        const item = questions[i];
        if (!item || !(item.question ?? "").trim()) {
          errors.question = `Soal ke-${i + 1}: teks soal wajib diisi.`;
          break;
        }
        const opts = Array.isArray(item.options)
          ? item.options.filter(
              (o) => o && typeof o.key === "string" && (o.text ?? "").trim(),
            )
          : [];
        if (opts.length < 2) {
          errors.options = `Soal ke-${i + 1}: isi minimal dua opsi.`;
          break;
        }
        if (!opts.some((o) => o.key === item.answer_key)) {
          errors.options = `Soal ke-${i + 1}: pilih kunci jawaban dari opsi yang terisi.`;
          break;
        }
        questions[i] = { question: item.question.trim(), options: opts, answer_key: item.answer_key };
      }
    }
  } else {
    const question = str(formData.get("question"));
    if (!question) errors.question = "Pertanyaan wajib diisi.";
    else questions = [{ question, options: [], answer_key: "" }];
  }

  if (Object.keys(errors).length > 0) return { errors };

  const created = await q1<{ id: string }>(
    `INSERT INTO assignments (topic_id, title, type, due_at)
     VALUES ($1, $2, $3, $4)
     RETURNING id`,
    [topic.id, title, type, dueAt],
  );
  if (!created) return { error: "Gagal membuat tugas." };

  for (let i = 0; i < questions.length; i++) {
    const item = questions[i];
    await q1(
      `INSERT INTO assignment_questions (assignment_id, position, question, options, answer_key)
       VALUES ($1, $2, $3, $4::jsonb, $5)`,
      [
        created.id,
        i,
        item.question,
        type === "pg" ? JSON.stringify(item.options) : null,
        type === "pg" ? item.answer_key : null,
      ],
    );
  }

  revalidatePath(`/lecturer/courses/${course.id}/topics/${topic.id}`);
  revalidatePath(`/lecturer/courses/${course.id}`);
  redirect(`/lecturer/assignments/${created.id}`);
}
