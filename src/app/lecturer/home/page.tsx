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

export default async function LecturerHomePage() {
  const lecturer = await requireRole("lecturer");

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
       JOIN course_lecturers cl ON cl.course_id = c.id AND cl.user_id = $1
       WHERE a.due_at > now()
       ORDER BY a.due_at ASC
       LIMIT 5`,
      [lecturer.id],
    ),
  ]);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <Breadcrumb items={[{ label: "Beranda" }]} />
        <PageHeader
          title="Beranda"
          description={`Selamat datang, ${lecturer.name}.`}
        />
      </div>

      {courses.length === 0 ? (
        <EmptyState message="Belum ada mata kuliah. Buat kelas pertama Anda, yuk!" />
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

      <Block label="Yang akan datang" empty="Tidak ada tenggat mendatang.">
        {upcoming.length === 0
          ? undefined
          : upcoming.map((item) => (
              <Link
                key={item.id}
                href={`/lecturer/assignments/${item.id}`}
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
