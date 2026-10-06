import Link from "next/link";
import { notFound } from "next/navigation";
import { q, q1 } from "@/db/pool";
import { requireRole } from "@/lib/session";
import { buttonClass } from "@/components/ui/button";
import { Card, PageHeader, StatusDot } from "@/components/ui/misc";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { statusOf } from "@/lib/status";
import { AssignClient } from "./assign-client";

export const dynamic = "force-dynamic";

type Person = { id: string; name: string; email: string };

export default async function CourseDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  await requireRole("admin");
  const { id } = await params;

  const course = await q1<{
    id: string;
    code: string;
    name: string;
    semester: number;
    sks: number;
    archived_at: string | null;
    period_name: string;
    section: string;
  }>(
    `SELECT c.id, c.code, c.name, c.semester, c.sks, c.archived_at,
            p.name AS period_name, c.section
     FROM courses c
     JOIN periods p ON p.id = c.period_id
     WHERE c.id = $1`,
    [id],
  );
  if (!course) notFound();

  const lecturers = await q<Person & { assigned: boolean }>(
    `SELECT u.id, u.name, u.email, (cl.user_id IS NOT NULL) AS assigned
     FROM users u
     LEFT JOIN course_lecturers cl ON cl.user_id = u.id AND cl.course_id = $1
     WHERE u.role = 'lecturer' AND u.status = 'active'
     ORDER BY u.name`,
    [id],
  );

  const students = await q<Person & { enrolled: boolean }>(
    `SELECT u.id, u.name, u.email, (e.student_id IS NOT NULL) AS enrolled
     FROM users u
     LEFT JOIN enrollments e ON e.student_id = u.id AND e.course_id = $1
     WHERE u.role = 'student' AND u.status = 'active'
     ORDER BY u.name`,
    [id],
  );

  const archived = course.archived_at ? statusOf("archived") : statusOf("aktif");

  return (
    <div className="flex flex-col gap-6">
      <Breadcrumb
        rootHref="/admin"
        items={[
          { label: "Mata kuliah", href: "/admin/courses" },
          { label: course.code },
        ]}
      />
      <PageHeader
        title={`${course.code} — ${course.name}`}
        description={`Kelas ${course.section} · ${course.period_name} · Semester ${course.semester} · ${course.sks} SKS`}
        action={
          <Link href="/admin/courses" className={buttonClass()}>
            Kembali
          </Link>
        }
      />

      <Card className="p-6">
        <dl className="grid grid-cols-[160px_1fr] gap-y-2 text-[14px]">
          <dt className="label">Kode</dt>
          <dd>{course.code}</dd>
          <dt className="label">Nama</dt>
          <dd>{course.name}</dd>
          <dt className="label">Periode</dt>
          <dd>{course.period_name}</dd>
          <dt className="label">Kelas</dt>
          <dd>{course.section}</dd>
          <dt className="label">Semester</dt>
          <dd>{course.semester}</dd>
          <dt className="label">SKS</dt>
          <dd>{course.sks}</dd>
          <dt className="label">Status</dt>
          <dd>
            <StatusDot label={archived.label} color={archived.color} icon={archived.Icon} />
          </dd>
        </dl>
      </Card>

      <AssignClient
        courseId={course.id}
        lecturers={lecturers}
        students={students}
        initialLecturerIds={lecturers.filter((l) => l.assigned).map((l) => l.id)}
        initialStudentIds={students.filter((s) => s.enrolled).map((s) => s.id)}
      />
    </div>
  );
}
