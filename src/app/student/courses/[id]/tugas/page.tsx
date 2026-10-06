import Link from "next/link";
import { notFound } from "next/navigation";
import { q, q1 } from "@/db/pool";
import { requireRole } from "@/lib/session";
import { fmtDate, fmtNilai } from "@/lib/format";
import { statusOf, submissionStatus } from "@/lib/status";
import { getCourseFrame } from "@/lib/course-view";
import { StatusDot } from "@/components/ui/misc";
import { Table, Td, Th, Tr } from "@/components/ui/table";
import { CourseTabShell } from "@/components/course/course-tab-shell";

export const dynamic = "force-dynamic";

export default async function StudentTugasPage({
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

  const [frame, rows] = await Promise.all([
    getCourseFrame(course.id, "student", student.id),
    q<{
      id: string;
      title: string;
      week: number;
      due_at: string | null;
      status: string | null;
      grade_state: string | null;
      nilai: number | string | null;
    }>(
      `SELECT a.id, a.title, t.week, a.due_at,
              s.status, g.state AS grade_state, g.nilai
       FROM assignments a
       JOIN topics t ON t.id = a.topic_id
       LEFT JOIN submissions s ON s.assignment_id = a.id AND s.student_id = $2
       LEFT JOIN grades g ON g.submission_id = s.id
       WHERE t.course_id = $1
       ORDER BY t.week, a.created_at`,
      [course.id, student.id],
    ),
  ]);

  return (
    <CourseTabShell role="student" course={course} frame={frame} tab="Tugas">
      {rows.length === 0 ? (
        <div className="rounded-lg border border-border bg-white px-4 py-5 shadow-menu">
          <p className="text-[14px] text-muted">Belum ada tugas di kursus ini.</p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border border-border bg-white">
          <Table>
            <thead>
              <tr>
                <Th>Tugas</Th>
                <Th>Tenggat</Th>
                <Th>Status</Th>
                <Th className="text-right">Nilai</Th>
              </tr>
            </thead>
            <tbody>
              {rows.map((a) => {
                const s = statusOf(
                  submissionStatus(a.status, a.grade_state === "published"),
                );
                const nilai =
                  a.grade_state === "published" && a.nilai !== null
                    ? fmtNilai(a.nilai)
                    : "—";
                return (
                  <Tr key={a.id}>
                    <Td>
                      <Link
                        href={`/student/assignments/${a.id}`}
                        className="font-medium text-link underline-offset-2 hover:underline"
                      >
                        {a.title}
                      </Link>
                      <span className="block text-[13px] text-muted">
                        Pertemuan {a.week}
                      </span>
                    </Td>
                    <Td className="whitespace-nowrap text-muted">
                      {fmtDate(a.due_at)}
                    </Td>
                    <Td>
                      <StatusDot label={s.label} color={s.color} icon={s.Icon} />
                    </Td>
                    <Td className="text-right font-medium">{nilai}</Td>
                  </Tr>
                );
              })}
            </tbody>
          </Table>
        </div>
      )}
    </CourseTabShell>
  );
}
