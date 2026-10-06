"use server";

import { revalidatePath } from "next/cache";
import { requireLecturer } from "@/lib/lecturer";
import {
  applyGradeEdits,
  computeGrade,
  getGrade,
  getLecturerSubmission,
  persistGrade,
} from "@/lib/grading";
import type { GradeCriterion } from "@/lib/grading/types";

export type GradeActionState = {
  error?: string;
  raw?: string;
  info?: string;
  grade?: {
    criteria: GradeCriterion[];
    feedback: string;
    summary: string;
    nilai: number;
    predikat: string;
    state: "draft" | "published";
  };
} | undefined;

function str(value: FormDataEntryValue | null): string {
  return typeof value === "string" ? value.trim() : "";
}

async function guard(submissionId: string) {
  const lecturer = await requireLecturer();
  const sub = await getLecturerSubmission(submissionId, lecturer.id);
  if (!sub) return null;
  return { lecturer, sub };
}

function revalidate(submissionId: string, assignmentId: string) {
  revalidatePath(`/lecturer/submissions/${submissionId}`);
  revalidatePath(`/lecturer/assignments/${assignmentId}`);
}

export async function runGrade(
  _prev: GradeActionState,
  formData: FormData,
): Promise<GradeActionState> {
  const submissionId = str(formData.get("submission_id"));
  const g = await guard(submissionId);
  if (!g) return { error: "Pengumpulan tidak ditemukan." };

  const publish =
    str(formData.get("intent")) === "publish" ||
    g.sub.release_mode === "langsung";

  const outcome = await computeGrade(submissionId);
  if (!outcome.ok) {
    return { error: outcome.message, raw: outcome.raw };
  }

  const saved = await persistGrade({
    submissionId,
    data: outcome,
    actorId: g.lecturer.id,
    publish,
  });

  revalidate(submissionId, g.sub.assignment_id);
  return {
    info:
      saved.state === "published"
        ? "Nilai terbit."
        : "Nilai disimpan sebagai draf.",
    grade: {
      criteria: outcome.criteria,
      feedback: outcome.feedback,
      summary: outcome.summary,
      nilai: Number(outcome.nilai),
      predikat: outcome.predikat,
      state: saved.state,
    },
  };
}

export async function saveGrade(
  _prev: GradeActionState,
  formData: FormData,
): Promise<GradeActionState> {
  const submissionId = str(formData.get("submission_id"));
  const g = await guard(submissionId);
  if (!g) return { error: "Pengumpulan tidak ditemukan." };

  let rows: {
    id: string;
    score: number;
    quote: string;
    comment: string;
  }[] = [];
  try {
    const parsed = JSON.parse(str(formData.get("criteria")) || "[]");
    if (Array.isArray(parsed)) rows = parsed;
  } catch {
    return { error: "Data nilai tidak valid." };
  }

  const scores: Record<string, number> = {};
  const quotes: Record<string, string> = {};
  const comments: Record<string, string> = {};
  for (const r of rows) {
    scores[r.id] = Number(r.score);
    quotes[r.id] = String(r.quote ?? "");
    comments[r.id] = String(r.comment ?? "");
  }

  const publish =
    str(formData.get("intent")) === "publish" ||
    g.sub.release_mode === "langsung";

  const result = await applyGradeEdits(submissionId, {
    scores,
    quotes,
    comments,
    feedback: str(formData.get("feedback")),
    summary: str(formData.get("summary")),
    publish,
    actorId: g.lecturer.id,
  });
  if (!result.ok) return { error: result.error };

  const grade = await getGrade(submissionId);
  revalidate(submissionId, g.sub.assignment_id);
  return {
    info:
      result.state === "published"
        ? "Nilai terbit."
        : "Nilai disimpan sebagai draf.",
    grade: grade
      ? {
          criteria: grade.criteria,
          feedback: grade.feedback,
          summary: grade.summary,
          nilai: Number(grade.nilai),
          predikat: grade.predikat,
          state: grade.state,
        }
      : undefined,
  };
}
