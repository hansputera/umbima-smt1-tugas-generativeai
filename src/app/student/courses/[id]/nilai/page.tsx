import Link from "next/link";
import { notFound } from "next/navigation";
import { q, q1 } from "@/db/pool";
import { requireRole } from "@/lib/session";
import { fmtDate, fmtNilai } from "@/lib/format";
import { statusOf } from "@/lib/status";
import { getCourseFrame } from "@/lib/course-view";
import { StatusDot } from "@/components/ui/misc";
import { Table, Td, Th, Tr } from "@/components/ui/table";
import { CourseTabShell } from "@/components/course/course-tab-shell";

export const dynamic = "force-dynamic";

export default async function StudentNilaiPage({
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
      assignment_id: string;
      title: string;
      week: number;
      nilai: number | string;
      predikat: string;
      published_at: string | null;
    }>(
      `SELECT a.id AS assignment_id, a.title, t.week,
              g.nilai, g.predikat, g.published_at
       FROM grades g
       JOIN submissions s ON s.id = g.submission_id
       JOIN assignments a ON a.id = s.assignment_id
       JOIN topics t ON t.id = a.topic_id
       WHERE t.course_id = $1 AND s.student_id = $2 AND g.state = 'published'
       ORDER BY g.published_at DESC NULLS LAST, g.updated_at DESC`,
      [course.id, student.id],
    ),
  ]);

  const published = statusOf("published");

  return (
    <CourseTabShell role="student" course={course} frame={frame} tab="Nilai">
      {rows.length === 0 ? (
        <div className="rounded-lg border border-border bg-white px-4 py-5 shadow-menu">
          <p className="text-[14px] text-muted">Belum ada nilai terbit.</p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border border-border bg-white">
          <Table>
            <thead>
              <tr>
                <Th>Tugas</Th>
                <Th className="text-right">Nilai</Th>
                <Th>Predikat</Th>
                <Th>Status</Th>
                <Th>Diterbitkan</Th>
              </tr>
            </thead>
            <tbody>
              {rows.map((g) => (
                <Tr key={g.assignment_id}>
                  <Td>
                    <Link
                      href={`/student/assignments/${g.assignment_id}`}
                      className="font-medium text-link underline-offset-2 hover:underline"
                    >
                      {g.title}
                    </Link>
                    <span className="block text-[13px] text-muted">
                      Pertemuan {g.week}
                    </span>
                  </Td>
                  <Td className="text-right text-[15px] font-semibold">
                    {fmtNilai(g.nilai)}
                  </Td>
                  <Td>{g.predikat}</Td>
                  <Td>
                    <StatusDot
                      label={published.label}
                      color={published.color}
                      icon={published.Icon}
                    />
                  </Td>
                  <Td className="whitespace-nowrap text-muted">
                    {fmtDate(g.published_at)}
                  </Td>
                </Tr>
              ))}
            </tbody>
          </Table>
        </div>
      )}
    </CourseTabShell>
  );
}
