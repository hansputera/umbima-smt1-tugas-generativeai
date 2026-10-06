import { q } from "@/db/pool";
import { requireLecturerCourse } from "@/lib/lecturer";
import { getCourseFrame } from "@/lib/course-view";
import { CourseTabShell } from "@/components/course/course-tab-shell";
import { PesertaContent, type Person } from "@/components/course/peserta-content";

export const dynamic = "force-dynamic";

export default async function LecturerPesertaPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const { course } = await requireLecturerCourse(id);

  const [frame, lecturers, students] = await Promise.all([
    getCourseFrame(course.id, "lecturer"),
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
    <CourseTabShell role="lecturer" course={course} frame={frame} tab="Peserta">
      <PesertaContent lecturers={lecturers} students={students} />
    </CourseTabShell>
  );
}
