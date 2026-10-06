"use server";

import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";
import { q1 } from "@/db/pool";
import { requireLecturerCourse } from "@/lib/lecturer";

export type TopicFormState = { errors?: Record<string, string> } | undefined;

function str(value: FormDataEntryValue | null): string {
  return typeof value === "string" ? value.trim() : "";
}

export async function createTopic(
  _prev: TopicFormState,
  formData: FormData,
): Promise<TopicFormState> {
  const courseId = str(formData.get("course_id"));
  const { course } = await requireLecturerCourse(courseId);

  const title = str(formData.get("title"));
  const weekRaw = str(formData.get("week"));

  const errors: Record<string, string> = {};
  if (!title) errors.title = "Judul wajib diisi.";
  const week = Number(weekRaw);
  if (!Number.isInteger(week) || week < 1 || week > 30) {
    errors.week = "Minggu harus 1–30.";
  }

  if (Object.keys(errors).length === 0) {
    const existing = await q1(
      "SELECT 1 AS ok FROM topics WHERE course_id = $1 AND week = $2",
      [course.id, week],
    );
    if (existing) errors.week = "Minggu sudah dipakai.";
  }

  if (Object.keys(errors).length > 0) return { errors };

  const topic = await q1<{ id: string }>(
    "INSERT INTO topics (course_id, week, title) VALUES ($1, $2, $3) RETURNING id",
    [course.id, week, title],
  );

  revalidatePath(`/lecturer/courses/${course.id}`);
  if (topic) redirect(`/lecturer/courses/${course.id}/topics/${topic.id}`);
  return {};
}
