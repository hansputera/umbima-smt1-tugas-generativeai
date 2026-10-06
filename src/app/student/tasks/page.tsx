import { q } from "@/db/pool";
import { requireRole } from "@/lib/session";
import { fmtNilai } from "@/lib/format";
import { submissionStatus } from "@/lib/status";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { EmptyState, PageHeader, Section } from "@/components/ui/misc";
import { AssignmentRow } from "@/components/assignment-row";

export const dynamic = "force-dynamic";

export default async function StudentTasksPage() {
  const student = await requireRole("student");

  const rows = await q<{
    id: string;
    title: string;
    type: string;
    release_mode: string;
    week: number;
    course_id: string;
    course_code: string;
    sub_status: string | null;
    grade_state: string | null;
    nilai: number | string | null;
  }>(
    `SELECT a.id, a.title, a.type, a.release_mode,
            t.week, c.id AS course_id, c.code AS course_code,
            s.status AS sub_status, g.state AS grade_state, g.nilai
     FROM assignments a
     JOIN topics t ON t.id = a.topic_id
     JOIN courses c ON c.id = t.course_id
     JOIN enrollments e ON e.course_id = c.id AND e.student_id = $1
     LEFT JOIN submissions s
            ON s.assignment_id = a.id AND s.student_id = $1
     LEFT JOIN grades g
            ON g.submission_id = s.id AND g.state = 'published'
     ORDER BY (s.id IS NULL) DESC, c.code, t.week, a.created_at`,
    [student.id],
  );

  const todo = rows.filter((r) => r.sub_status === null);
  const done = rows.filter((r) => r.sub_status !== null);

  const description =
    rows.length === 0
      ? "Semua tugas dari mata kuliah yang Anda ikuti."
      : todo.length > 0
        ? `${todo.length} tugas belum dikerjakan.`
        : "Semua tugas sudah dikumpulkan.";

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <Breadcrumb items={[{ label: "Tugas" }]} />
        <PageHeader title="Tugas" description={description} />
      </div>

      {rows.length === 0 ? (
        <EmptyState message="Belum ada tugas nih. Begitu dosen menambahkannya, tugas akan muncul di sini." />
      ) : (
        <>
          <Section title="Belum dikerjakan">
            {todo.length === 0 ? (
              <div className="rounded-lg border border-border bg-white px-4 py-5 shadow-menu">
                <p className="text-[14px] text-muted">
                  Semua tugas sudah dikumpulkan. Kerja bagus!
                </p>
              </div>
            ) : (
              <div className="flex flex-col gap-3">
                {todo.map((r) => (
                  <AssignmentRow
                    key={r.id}
                    href={`/student/assignments/${r.id}`}
                    title={r.title}
                    type={r.type}
                    releaseMode={r.release_mode}
                    statusKey="belum"
                    subtitle={`${r.course_code} · Pertemuan ${r.week}`}
                    action="Kerjakan"
                  />
                ))}
              </div>
            )}
          </Section>

          {done.length > 0 ? (
            <Section title="Sudah dikumpulkan">
              <div className="flex flex-col gap-3">
                {done.map((r) => {
                  const key = submissionStatus(
                    r.sub_status,
                    r.grade_state === "published",
                  );
                  const nilai =
                    r.grade_state === "published" && r.nilai !== null
                      ? fmtNilai(r.nilai)
                      : null;
                  return (
                    <AssignmentRow
                      key={r.id}
                      href={`/student/assignments/${r.id}`}
                      title={r.title}
                      type={r.type}
                      releaseMode={r.release_mode}
                      statusKey={key}
                      nilai={nilai}
                      subtitle={`${r.course_code} · Pertemuan ${r.week}`}
                      action="Lihat jawaban"
                    />
                  );
                })}
              </div>
            </Section>
          ) : null}
        </>
      )}
    </div>
  );
}
