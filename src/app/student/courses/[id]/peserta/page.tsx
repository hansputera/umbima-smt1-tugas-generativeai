import { notFound } from "next/navigation";
import { q, q1 } from "@/db/pool";
import { requireRole } from "@/lib/session";
import { getCourseFrame } from "@/lib/course-view";
import { CourseTabShell } from "@/components/course/course-tab-shell";
import { PesertaContent, type Person } from "@/components/course/peserta-content";

export const dynamic = "force-dynamic";

export default async function StudentPesertaPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const student = await requireRole("student");

  const course = await q1<{
    id: string;
    code: string;
    name: string;
    semester: number;
    sks: number;
  }>(
    `SELECT c.id, c.code, c.name, c.semester, c.sks
     FROM courses c
     JOIN enrollments e ON e.course_id = c.id AND e.student_id = $2
     WHERE c.id = $1`,
    [id, student.id],
  );
  if (!course) notFound();

  const [frame, lecturers, students] = await Promise.all([
    getCourseFrame(course.id, "student", student.id),
    q<Person>(
      `SELECT u.name, u.email
       FROM course_lecturers cl
       JOIN users u ON u.id = cl.user_id
       WHERE cl.course_id = $1
       ORDER BY u.name`,
      [course.id],
    ),
    q<Person>(
      `SELECT u.name, u.email
       FROM enrollments e
       JOIN users u ON u.id = e.student_id
       WHERE e.course_id = $1
       ORDER BY u.name`,
      [course.id],
    ),
  ]);

  return (
    <CourseTabShell role="student" course={course} frame={frame} tab="Peserta">
      <PesertaContent lecturers={lecturers} students={students} />
    </CourseTabShell>
  );
}
