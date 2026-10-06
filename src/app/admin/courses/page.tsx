import { q } from "@/db/pool";
import { CoursesClient, type CourseRow, type PeriodOption } from "./courses-client";

export const dynamic = "force-dynamic";

export default async function CoursesPage() {
  const courses = await q<CourseRow>(
    `SELECT c.id, c.code, c.name, c.semester, c.sks, c.archived_at,
            c.period_id, c.section, p.name AS period_name,
            (SELECT string_agg(u.name, ', ' ORDER BY u.name)
             FROM course_lecturers cl JOIN users u ON u.id = cl.user_id
             WHERE cl.course_id = c.id) AS lecturers,
            (SELECT count(*)::int FROM enrollments e WHERE e.course_id = c.id) AS student_count
     FROM courses c
     JOIN periods p ON p.id = c.period_id
     ORDER BY c.archived_at NULLS FIRST, p.is_active DESC, p.created_at, c.code, c.section`,
  );

  const periods = await q<PeriodOption>(
    `SELECT id, name, is_active FROM periods
     ORDER BY is_active DESC, created_at DESC, name`,
  );

  return <CoursesClient courses={courses} periods={periods} />;
}
