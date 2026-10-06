import { q } from "@/db/pool";
import { requireRole } from "@/lib/session";
import { EmptyState, PageHeader } from "@/components/ui/misc";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { CourseCard, CourseProgress } from "@/components/course-card";

export const dynamic = "force-dynamic";

export default async function StudentCoursesPage() {
  const student = await requireRole("student");

  const courses = await q<{
    id: string;
    code: string;
    name: string;
    semester: number;
    sks: number;
    archived_at: string | null;
    period_name: string;
    section: string;
    lecturers: string | null;
    assignment_count: number;
    done_count: number;
  }>(
    `SELECT c.id, c.code, c.name, c.semester, c.sks, c.archived_at,
            p.name AS period_name, c.section,
            (SELECT string_agg(u.name, ', ' ORDER BY u.name)
               FROM course_lecturers cl JOIN users u ON u.id = cl.user_id
              WHERE cl.course_id = c.id) AS lecturers,
            (SELECT count(*)::int FROM assignments a
               JOIN topics t2 ON t2.id = a.topic_id
              WHERE t2.course_id = c.id) AS assignment_count,
            (SELECT count(*)::int FROM submissions s
               JOIN assignments a2 ON a2.id = s.assignment_id
               JOIN topics t3 ON t3.id = a2.topic_id
               JOIN grades g ON g.submission_id = s.id
              WHERE t3.course_id = c.id AND s.student_id = $1
                AND g.state = 'published') AS done_count
     FROM courses c
     JOIN periods p ON p.id = c.period_id
     JOIN enrollments e ON e.course_id = c.id AND e.student_id = $1
     ORDER BY p.is_active DESC, p.created_at, c.code, c.section`,
    [student.id],
  );

  return (
    <div className="flex flex-col gap-6">
      <Breadcrumb items={[{ label: "Kursus saya" }]} />
      <PageHeader
        title="Kursus saya"
        description="Mata kuliah yang Anda ikuti."
      />

      {courses.length === 0 ? (
        <EmptyState message="Belum ada mata kuliah. Hubungi dosen ya supaya bisa ikut kelas." />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {courses.map((c) => (
            <CourseCard
              key={c.id}
              href={`/student/courses/${c.id}`}
              code={c.code}
              name={c.name}
              semester={c.semester}
              sks={c.sks}
              statusKey={c.archived_at ? "archived" : "aktif"}
              meta={
                [`Kelas ${c.section} · ${c.period_name}`, c.lecturers]
                  .filter(Boolean)
                  .join(" · ") || undefined
              }
              footer={
                <CourseProgress
                  done={c.done_count}
                  total={c.assignment_count}
                />
              }
            />
          ))}
        </div>
      )}
    </div>
  );
}
