import { q } from "@/db/pool";
import { requireRole } from "@/lib/session";
import { PageHeader } from "@/components/ui/misc";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { CourseCard, CourseProgress } from "@/components/course-card";

export const dynamic = "force-dynamic";

export default async function LecturerCoursesPage() {
  const lecturer = await requireRole("lecturer");

  const courses = await q<{
    id: string;
    code: string;
    name: string;
    semester: number;
    sks: number;
    archived_at: string | null;
    period_name: string;
    section: string;
    topic_count: number;
    assignment_count: number;
    collected_count: number;
  }>(
    `SELECT c.id, c.code, c.name, c.semester, c.sks, c.archived_at,
            p.name AS period_name, c.section,
            (SELECT count(*)::int FROM topics t WHERE t.course_id = c.id) AS topic_count,
            (SELECT count(*)::int FROM assignments a
               JOIN topics t2 ON t2.id = a.topic_id
              WHERE t2.course_id = c.id) AS assignment_count,
            (SELECT count(*)::int FROM assignments a2
               JOIN topics t3 ON t3.id = a2.topic_id
              WHERE t3.course_id = c.id
                AND EXISTS (
                  SELECT 1 FROM submissions s
                   WHERE s.assignment_id = a2.id AND s.status <> 'draft'
                )) AS collected_count
     FROM courses c
     JOIN periods p ON p.id = c.period_id
     JOIN course_lecturers cl ON cl.course_id = c.id AND cl.user_id = $1
     ORDER BY c.archived_at NULLS FIRST, p.is_active DESC, p.created_at, c.code, c.section`,
    [lecturer.id],
  );

  return (
    <div className="flex flex-col gap-6">
      <Breadcrumb items={[{ label: "Kursus saya" }]} />
      <PageHeader
        title="Kursus saya"
        description="Mata kuliah yang Anda ampu."
      />

      {courses.length === 0 ? (
        <p className="text-[15px] text-muted">
          Belum ada mata kuliah. Buat kelas pertama Anda, yuk!
        </p>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {courses.map((c) => (
            <CourseCard
              key={c.id}
              href={`/lecturer/courses/${c.id}`}
              code={c.code}
              name={c.name}
              semester={c.semester}
              sks={c.sks}
              statusKey={c.archived_at ? "archived" : "aktif"}
              meta={`Kelas ${c.section} · ${c.period_name}`}
              footer={
                <div className="flex flex-col gap-3">
                  <span className="text-[13px] text-muted">
                    {c.topic_count} pertemuan · {c.assignment_count} tugas
                  </span>
                  <CourseProgress
                    done={c.collected_count}
                    total={c.assignment_count}
                    label="Tugas ada pengumpulan"
                  />
                </div>
              }
            />
          ))}
        </div>
      )}
    </div>
  );
}
