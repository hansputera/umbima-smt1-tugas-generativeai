import { q } from "@/db/pool";
import { requireLecturer } from "@/lib/lecturer";
import { PageHeader } from "@/components/ui/misc";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { SubmissionsInbox, type InboxRow } from "./submissions-inbox";

export const dynamic = "force-dynamic";

export default async function LecturerSubmissionsPage() {
  const lecturer = await requireLecturer();

  const rows = await q<InboxRow>(
    `SELECT s.id, s.status, s.submitted_at,
            u.name AS student_name,
            c.id AS course_id, c.code AS course_code, c.name AS course_name,
            a.id AS assignment_id, a.title AS assignment_title, a.type,
            COALESCE(g.state = 'published', false) AS published, g.nilai
     FROM submissions s
     JOIN assignments a ON a.id = s.assignment_id
     JOIN topics t ON t.id = a.topic_id
     JOIN courses c ON c.id = t.course_id
     JOIN course_lecturers cl ON cl.course_id = c.id AND cl.user_id = $1
     JOIN users u ON u.id = s.student_id
     LEFT JOIN grades g ON g.submission_id = s.id
     ORDER BY s.submitted_at DESC NULLS LAST, u.name`,
    [lecturer.id],
  );

  return (
    <div className="flex flex-col gap-6">
      <Breadcrumb items={[{ label: "Pengumpulan" }]} />
      <PageHeader
        title="Pengumpulan"
        description="Seluruh pengumpulan tugas pada mata kuliah Anda."
      />
      <SubmissionsInbox rows={rows} />
    </div>
  );
}
