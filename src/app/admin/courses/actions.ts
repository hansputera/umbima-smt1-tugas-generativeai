"use server";

import { revalidatePath } from "next/cache";
import { q1 } from "@/db/pool";
import { requireRole } from "@/lib/session";

export type CourseFormState = { errors?: Record<string, string> } | undefined;
export type RowState = { error?: string } | undefined;

function str(value: FormDataEntryValue | null): string {
  return typeof value === "string" ? value.trim() : "";
}

export async function saveCourse(
  _prev: CourseFormState,
  formData: FormData,
): Promise<CourseFormState> {
  await requireRole("admin");

  const id = str(formData.get("id")) || null;
  const code = str(formData.get("code")).toUpperCase();
  const name = str(formData.get("name"));
  const semesterRaw = str(formData.get("semester"));
  const sksRaw = str(formData.get("sks"));
  const periodId = str(formData.get("period_id"));
  const section = (str(formData.get("section")) || "A").toUpperCase();

  const errors: Record<string, string> = {};
  if (!code) errors.code = "Kode wajib diisi.";
  if (!name) errors.name = "Nama mata kuliah wajib diisi.";

  const semester = Number(semesterRaw);
  if (!Number.isInteger(semester) || semester < 1 || semester > 14) {
    errors.semester = "Semester harus 1–14.";
  }
  const sks = Number(sksRaw);
  if (!Number.isInteger(sks) || sks < 1 || sks > 10) {
    errors.sks = "SKS harus 1–10.";
  }
  if (!periodId) {
    errors.period_id = "Periode wajib dipilih.";
  } else if (!/^[A-Z0-9]{1,8}$/.test(section)) {
    errors.section = "Kelas maksimal 8 karakter (huruf atau angka).";
  }

  if (Object.keys(errors).length === 0) {
    const period = await q1("SELECT 1 AS ok FROM periods WHERE id = $1", [
      periodId,
    ]);
    if (!period) errors.period_id = "Periode tidak ditemukan.";
  }

  if (Object.keys(errors).length === 0) {
    const existing = await q1(
      `SELECT 1 AS ok FROM courses
       WHERE upper(code) = upper($1) AND period_id = $2 AND upper(section) = upper($3)
         AND ($4::uuid IS NULL OR id <> $4)
       LIMIT 1`,
      [code, periodId, section, id],
    );
    if (existing) errors.code = "Kelas untuk kode, periode, dan seksi ini sudah ada.";
  }

  if (Object.keys(errors).length > 0) return { errors };

  if (id) {
    await q1(
      `UPDATE courses
       SET code = $2, name = $3, semester = $4, sks = $5, period_id = $6, section = $7
       WHERE id = $1`,
      [id, code, name, semester, sks, periodId, section],
    );
    revalidatePath(`/admin/courses/${id}`);
  } else {
    await q1(
      `INSERT INTO courses (code, name, semester, sks, period_id, section)
       VALUES ($1, $2, $3, $4, $5, $6)`,
      [code, name, semester, sks, periodId, section],
    );
  }

  revalidatePath("/admin/courses");
  revalidatePath("/admin/placement");
  return {};
}

export async function toggleArchive(formData: FormData): Promise<RowState> {
  await requireRole("admin");
  const id = str(formData.get("id"));
  if (!id) return { error: "Mata kuliah tidak ditemukan." };

  await q1(
    `UPDATE courses SET archived_at = CASE WHEN archived_at IS NULL THEN now() ELSE NULL END
     WHERE id = $1`,
    [id],
  );
  revalidatePath("/admin/courses");
  return {};
}

export async function deleteCourse(formData: FormData): Promise<RowState> {
  await requireRole("admin");
  const id = str(formData.get("id"));
  if (!id) return { error: "Mata kuliah tidak ditemukan." };

  const enrolled = await q1<{ n: string }>(
    "SELECT count(*)::text AS n FROM enrollments WHERE course_id = $1",
    [id],
  );
  if (Number(enrolled?.n ?? 0) > 0) {
    return {
      error: "Masih ada mahasiswa terdaftar. Arsipkan, jangan dihapus.",
    };
  }

  await q1("DELETE FROM courses WHERE id = $1", [id]);
  revalidatePath("/admin/courses");
  return {};
}

export async function toggleLecturer(formData: FormData): Promise<RowState> {
  await requireRole("admin");
  const courseId = str(formData.get("course_id"));
  const userId = str(formData.get("user_id"));
  if (!courseId || !userId) return { error: "Data tidak lengkap." };

  const existing = await q1(
    "SELECT 1 AS ok FROM course_lecturers WHERE course_id = $1 AND user_id = $2",
    [courseId, userId],
  );
  if (existing) {
    await q1(
      "DELETE FROM course_lecturers WHERE course_id = $1 AND user_id = $2",
      [courseId, userId],
    );
  } else {
    await q1(
      "INSERT INTO course_lecturers (course_id, user_id) VALUES ($1, $2)",
      [courseId, userId],
    );
  }
  revalidatePath(`/admin/courses/${courseId}`);
  return {};
}

export async function toggleEnrollment(formData: FormData): Promise<RowState> {
  await requireRole("admin");
  const courseId = str(formData.get("course_id"));
  const studentId = str(formData.get("student_id"));
  if (!courseId || !studentId) return { error: "Data tidak lengkap." };

  const existing = await q1(
    "SELECT 1 AS ok FROM enrollments WHERE course_id = $1 AND student_id = $2",
    [courseId, studentId],
  );
  if (existing) {
    await q1(
      "DELETE FROM enrollments WHERE course_id = $1 AND student_id = $2",
      [courseId, studentId],
    );
  } else {
    await q1(
      "INSERT INTO enrollments (course_id, student_id) VALUES ($1, $2)",
      [courseId, studentId],
    );
  }
  revalidatePath(`/admin/courses/${courseId}`);
  revalidatePath("/admin/placement");
  revalidatePath("/student/courses");
  return {};
}
