import Link from "next/link";
import { q } from "@/db/pool";
import { requireLecturerCourse } from "@/lib/lecturer";
import { fmtDate } from "@/lib/format";
import { MODE_LABEL, TYPE_LABEL } from "@/lib/status";
import { getCourseFrame } from "@/lib/course-view";
import { buttonClass } from "@/components/ui/button";
import { Table, Td, Th, Tr } from "@/components/ui/table";
import { CourseTabShell } from "@/components/course/course-tab-shell";

export const dynamic = "force-dynamic";

export default async function LecturerTugasPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const { course } = await requireLecturerCourse(id);

  const [frame, rows] = await Promise.all([
    getCourseFrame(course.id, "lecturer"),
    q<{
      id: string;
      title: string;
      week: number;
      type: string;
      release_mode: string;
      due_at: string | null;
      submitted_count: number;
      rubric_count: number;
      rubric_weight: number;
    }>(
      `SELECT a.id, a.title, t.week, a.type, a.release_mode, a.due_at,
              (SELECT count(*)::int FROM submissions s
               WHERE s.assignment_id = a.id AND s.status <> 'draft') AS submitted_count,
              COALESCE(rc.crit_count, 0) AS rubric_count,
              COALESCE(rc.weight_sum, 0) AS rubric_weight
       FROM assignments a
       JOIN topics t ON t.id = a.topic_id
       LEFT JOIN (SELECT assignment_id, count(*)::int AS crit_count,
                         COALESCE(sum(weight), 0)::int AS weight_sum
                  FROM rubric_criteria GROUP BY assignment_id) rc
         ON rc.assignment_id = a.id
       WHERE t.course_id = $1
       ORDER BY t.week, a.created_at`,
      [course.id],
    ),
  ]);

  return (
    <CourseTabShell role="lecturer" course={course} frame={frame} tab="Tugas">
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
                <Th>Tipe</Th>
                <Th>Rilis</Th>
                <Th>Tenggat</Th>
                <Th className="text-right">Pengumpulan</Th>
                <Th>Rubrik</Th>
                <Th className="text-right">Buka</Th>
              </tr>
            </thead>
            <tbody>
              {rows.map((a) => (
                <Tr key={a.id}>
                  <Td>
                    <Link
                      href={`/lecturer/assignments/${a.id}`}
                      className="font-medium text-ink hover:text-link hover:underline"
                    >
                      {a.title}
                    </Link>
                    <span className="block text-[13px] text-muted">
                      Pertemuan {a.week}
                    </span>
                  </Td>
                  <Td className="whitespace-nowrap text-muted">
                    {TYPE_LABEL[a.type] ?? a.type}
                  </Td>
                  <Td className="whitespace-nowrap text-muted">
                    {MODE_LABEL[a.release_mode] ?? a.release_mode}
                  </Td>
                  <Td className="whitespace-nowrap text-muted">
                    {fmtDate(a.due_at)}
                  </Td>
                  <Td className="whitespace-nowrap text-right">
                    {a.submitted_count} pengumpulan
                  </Td>
                  <Td className="whitespace-nowrap">
                    {a.type === "pg" ? (
                      <span className="text-muted">—</span>
                    ) : a.rubric_count === 0 ? (
                      <Link
                        href={`/lecturer/assignments/${a.id}#rubrik`}
                        className="text-muted hover:text-link hover:underline"
                      >
                        Belum diisi
                      </Link>
                    ) : a.rubric_weight === 100 ? (
                      <Link
                        href={`/lecturer/assignments/${a.id}#rubrik`}
                        className="text-ok hover:underline"
                      >
                        {a.rubric_count} kriteria · 100%
                      </Link>
                    ) : (
                      <Link
                        href={`/lecturer/assignments/${a.id}#rubrik`}
                        className="text-danger hover:underline"
                      >
                        {a.rubric_count} kriteria · {a.rubric_weight}%
                      </Link>
                    )}
                  </Td>
                  <Td className="text-right">
                    <Link
                      href={`/lecturer/assignments/${a.id}`}
                      className={`${buttonClass()} px-2.5 py-1 text-[13px]`}
                    >
                      Buka
                    </Link>
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
