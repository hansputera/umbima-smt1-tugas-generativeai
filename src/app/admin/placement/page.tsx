import { q } from "@/db/pool";
import {
  PlacementClient,
  type ClassRow,
  type EnrollmentPair,
  type PeriodOption,
  type StudentRow,
} from "./placement-client";

export const dynamic = "force-dynamic";

export default async function PlacementPage() {
  const periods = await q<PeriodOption>(
    `SELECT id, name, is_active FROM periods
     ORDER BY is_active DESC, created_at DESC, name`,
  );

  const students = await q<StudentRow>(
    `SELECT id, name, email FROM users
     WHERE role = 'student' AND status = 'active'
     ORDER BY name`,
  );

  const classes = await q<ClassRow>(
    `SELECT c.id, c.code, c.name, c.section, c.period_id,
            p.name AS period_name,
            (SELECT string_agg(u.name, ', ' ORDER BY u.name)
             FROM course_lecturers cl JOIN users u ON u.id = cl.user_id
             WHERE cl.course_id = c.id) AS lecturers
     FROM courses c
     JOIN periods p ON p.id = c.period_id
     WHERE c.archived_at IS NULL
     ORDER BY p.is_active DESC, p.created_at, c.code, c.section`,
  );

  const pairs = await q<EnrollmentPair>(
    "SELECT course_id, student_id FROM enrollments",
  );

  return (
    <PlacementClient
      periods={periods}
      students={students}
      classes={classes}
      pairs={pairs}
    />
  );
}
