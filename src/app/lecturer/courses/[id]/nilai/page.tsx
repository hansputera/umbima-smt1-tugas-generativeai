import { q } from "@/db/pool";
import { requireLecturerCourse } from "@/lib/lecturer";
import { fmtNilai } from "@/lib/format";
import { getCourseFrame } from "@/lib/course-view";
import { Table, Td, Th, Tr } from "@/components/ui/table";
import { CourseTabShell } from "@/components/course/course-tab-shell";

export const dynamic = "force-dynamic";

type GradeCell = { nilai: number | string; state: string };

function avg(values: number[]): number | null {
  if (values.length === 0) return null;
  return values.reduce((a, b) => a + b, 0) / values.length;
}

function AvgText({ value }: { value: number | null }) {
  return <>{value === null ? "—" : fmtNilai(value)}</>;
}

function GradeValue({ cell }: { cell: GradeCell | undefined }) {
  if (!cell) return <span className="text-faint">—</span>;
  const text = fmtNilai(cell.nilai);
  if (cell.state === "published") {
    return <span className="font-medium text-ink">{text}</span>;
  }
  return <span className="text-muted">{text} (draf)</span>;
}

export default async function LecturerNilaiPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const { course } = await requireLecturerCourse(id);

  const [frame, students, assignments, gradeRows] = await Promise.all([
    getCourseFrame(course.id, "lecturer"),
    q<{ id: string; name: string }>(
      `SELECT u.id, u.name
       FROM enrollments e
       JOIN users u ON u.id = e.student_id
       WHERE e.course_id = $1
       ORDER BY u.name`,
      [course.id],
    ),
    q<{ id: string; title: string; week: number }>(
      `SELECT a.id, a.title, t.week
       FROM assignments a
       JOIN topics t ON t.id = a.topic_id
       WHERE t.course_id = $1
       ORDER BY t.week, a.created_at`,
      [course.id],
    ),
    q<{
      student_id: string;
      assignment_id: string;
      nilai: number | string;
      state: string;
    }>(
      `SELECT s.student_id, s.assignment_id, g.nilai, g.state
       FROM grades g
       JOIN submissions s ON s.id = g.submission_id
       JOIN assignments a ON a.id = s.assignment_id
       JOIN topics t ON t.id = a.topic_id
       WHERE t.course_id = $1`,
      [course.id],
    ),
  ]);

  const grades = new Map<string, GradeCell>();
  for (const g of gradeRows) {
    const key = `${g.student_id}:${g.assignment_id}`;
    const cur = grades.get(key);
    if (!cur || (cur.state !== "published" && g.state === "published")) {
      grades.set(key, { nilai: g.nilai, state: g.state });
    }
  }

  const publishedNum = (key: string): number | null => {
    const cell = grades.get(key);
    if (!cell || cell.state !== "published") return null;
    const n = Number(cell.nilai);
    return Number.isFinite(n) ? n : null;
  };

  const colAvg = assignments.map((a) =>
    avg(
      students
        .map((s) => publishedNum(`${s.id}:${a.id}`))
        .filter((v): v is number => v !== null),
    ),
  );

  return (
    <CourseTabShell role="lecturer" course={course} frame={frame} tab="Nilai">
      {assignments.length === 0 ? (
        <div className="rounded-lg border border-border bg-white px-4 py-5 shadow-menu">
          <p className="text-[14px] text-muted">Belum ada tugas di kursus ini.</p>
        </div>
      ) : students.length === 0 ? (
        <div className="rounded-lg border border-border bg-white px-4 py-5 shadow-menu">
          <p className="text-[14px] text-muted">
            Belum ada mahasiswa terdaftar.
          </p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border border-border bg-white">
          <Table>
            <thead>
              <tr>
                <Th>Mahasiswa</Th>
                {assignments.map((a) => (
                  <Th key={a.id} className="text-right">
                    {a.title}
                  </Th>
                ))}
              </tr>
            </thead>
            <tbody>
              {students.map((s) => (
                <Tr key={s.id}>
                  <Td className="whitespace-nowrap font-medium text-ink">
                    {s.name}
                  </Td>
                  {assignments.map((a) => (
                    <Td key={a.id} className="text-right">
                      <GradeValue cell={grades.get(`${s.id}:${a.id}`)} />
                    </Td>
                  ))}
                </Tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="border-t-2 border-border bg-canvas">
                <Td className="font-semibold text-ink">Rata-rata</Td>
                {colAvg.map((value, i) => (
                  <Td key={assignments[i].id} className="text-right font-semibold">
                    <AvgText value={value} />
                  </Td>
                ))}
              </tr>
            </tfoot>
          </Table>
        </div>
      )}
    </CourseTabShell>
  );
}
