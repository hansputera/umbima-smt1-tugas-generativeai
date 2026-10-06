import { requireLecturerCourse } from "@/lib/lecturer";
import { getCourseFrame } from "@/lib/course-view";
import { CourseTabShell } from "@/components/course/course-tab-shell";
import { Card, StatusDot } from "@/components/ui/misc";
import { statusOf } from "@/lib/status";

export const dynamic = "force-dynamic";

export default async function LecturerPengaturanPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const { course } = await requireLecturerCourse(id);

  const frame = await getCourseFrame(course.id, "lecturer");
  const archived = course.archived_at ? statusOf("archived") : statusOf("aktif");

  return (
    <CourseTabShell
      role="lecturer"
      course={course}
      frame={frame}
      tab="Pengaturan"
    >
      <div className="flex max-w-2xl flex-col gap-3">
        <Card className="flex flex-col gap-4 p-6">
          <h2>Informasi mata kuliah</h2>
          <p className="text-[14px] text-muted">
            Informasi ini diatur oleh admin dan tidak bisa diubah dari sini.
            Dosen mengelola pertemuan, tugas, rubrik, dan penilaian.
          </p>
          <dl className="grid grid-cols-[160px_1fr] gap-y-2 text-[14px]">
            <dt className="label">Kode</dt>
            <dd>{course.code}</dd>
            <dt className="label">Nama mata kuliah</dt>
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
              <StatusDot
                label={archived.label}
                color={archived.color}
                icon={archived.Icon}
              />
            </dd>
          </dl>
        </Card>
      </div>
    </CourseTabShell>
  );
}
