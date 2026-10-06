import Link from "next/link";
import { q } from "@/db/pool";
import { requireRole } from "@/lib/session";
import { fmtDate } from "@/lib/format";
import { TYPE_LABEL } from "@/lib/status";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { EmptyState, PageHeader } from "@/components/ui/misc";
import { CourseCard, CourseProgress } from "@/components/course-card";
import { ActivityIcon } from "@/components/course/activity-icon";
import { Block } from "@/components/course/right-blocks";

export const dynamic = "force-dynamic";

export default async function StudentHomePage() {
  const student = await requireRole("student");

  const [courses, upcoming] = await Promise.all([
    q<{
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
    ),
    q<{
      id: string;
      title: string;
      type: string;
      due_at: string;
      code: string;
    }>(
      `SELECT a.id, a.title, a.type, a.due_at, c.code
       FROM assignments a
       JOIN topics t ON t.id = a.topic_id
       JOIN courses c ON c.id = t.course_id
       JOIN enrollments e ON e.course_id = c.id AND e.student_id = $1
       LEFT JOIN submissions s ON s.assignment_id = a.id AND s.student_id = $1
       WHERE a.due_at > now() AND (s.id IS NULL OR s.status = 'draft')
       ORDER BY a.due_at ASC
       LIMIT 5`,
      [student.id],
    ),
  ]);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <Breadcrumb items={[{ label: "Beranda" }]} />
        <PageHeader
          title="Beranda"
          description={`Selamat datang, ${student.name}.`}
        />
      </div>

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

      <Block label="Yang akan datang" empty="Tidak ada tenggat mendatang.">
        {upcoming.length === 0
          ? undefined
          : upcoming.map((item) => (
              <Link
                key={item.id}
                href={`/student/assignments/${item.id}`}
                className="flex items-center gap-3 border-b border-border px-4 py-3 transition-colors last:border-b-0 hover:bg-canvas"
              >
                <ActivityIcon type={item.type} size={40} />
                <span className="flex min-w-0 flex-col">
                  <span className="truncate text-[14px] font-medium text-ink">
                    {item.title}
                  </span>
                  <span className="text-[13px] text-muted">
                    {item.code} · {TYPE_LABEL[item.type] ?? item.type} ·
                    Tenggat {fmtDate(item.due_at)}
                  </span>
                </span>
              </Link>
            ))}
      </Block>
    </div>
  );
}
