import Link from "next/link";
import { notFound } from "next/navigation";
import { Circle, CircleCheck } from "lucide-react";
import { q1 } from "@/db/pool";
import { requireRole } from "@/lib/session";
import { fmtDate, fmtNilai } from "@/lib/format";
import { TYPE_LABEL } from "@/lib/status";
import {
  getCourseFrame,
  getRecentGrades,
  getUpcoming,
  type FrameItem,
} from "@/lib/course-view";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { EmptyState } from "@/components/ui/misc";
import { CourseFrame } from "@/components/course/course-frame";
import { courseTabs } from "@/components/course/tabs";
import { ActivityIcon } from "@/components/course/activity-icon";
import { RecentGrades, UpcomingList } from "@/components/course/right-blocks";

export const dynamic = "force-dynamic";

function activitySubtitle(item: FrameItem): string {
  if (item.kind === "materi") return "Materi";
  const label = TYPE_LABEL[item.type] ?? item.type;
  return item.due_at ? `${label} · Tenggat ${fmtDate(item.due_at)}` : label;
}

function StudentRow({ item }: { item: FrameItem }) {
  const submitted = Boolean(item.status);
  const nilai =
    item.kind === "assignment" &&
    item.grade_state === "published" &&
    item.nilai !== null &&
    item.nilai !== undefined
      ? fmtNilai(item.nilai)
      : null;
  return (
    <Link
      href={item.href}
      className="flex items-center gap-3 border-b border-border px-4 py-3.5 transition-colors last:border-b-0 hover:bg-row-hover"
    >
      <ActivityIcon type={item.type} size={40} />
      <span className="flex min-w-0 flex-col">
        <span className="truncate text-[15px] font-medium text-ink">
          {item.title}
        </span>
        <span className="text-[13px] text-muted">
          {activitySubtitle(item)}
        </span>
      </span>
      {item.kind === "assignment" ? (
        <span className="ml-auto flex shrink-0 items-center gap-3">
          {nilai ? (
            <span className="text-[15px] font-medium text-ink">{nilai}</span>
          ) : null}
          {submitted ? (
            <CircleCheck size={16} strokeWidth={2} className="text-ok" aria-hidden />
          ) : (
            <Circle size={16} strokeWidth={2} className="text-faint" aria-hidden />
          )}
          <span className="sr-only">
            {submitted ? "Sudah dikumpulkan" : "Belum dikumpulkan"}
          </span>
        </span>
      ) : null}
    </Link>
  );
}

export default async function StudentCoursePage({
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

  const [frame, upcoming, recent] = await Promise.all([
    getCourseFrame(course.id, "student", student.id),
    getUpcoming(course.id, "student", student.id),
    getRecentGrades(course.id, "student", student.id),
  ]);

  return (
    <div className="flex flex-col gap-4">
      <Breadcrumb
        rootHref="/student/home"
        items={[
          { label: "Kursus", href: "/student/courses" },
          { label: course.code },
        ]}
      />
      <CourseFrame
        courseLabel={`${course.code} — ${course.name}`}
        courseHref={`/student/courses/${course.id}`}
        index={frame.topics}
        title={
          <>
            <h1 className="course-title">{course.name}</h1>
            <p className="mt-1 text-[14px] text-muted">
              {course.code} · Semester {course.semester} · {course.sks} SKS
            </p>
          </>
        }
        tabs={courseTabs(course.id, "student")}
        blocks={
          <>
            <UpcomingList items={upcoming} />
            <RecentGrades items={recent} />
          </>
        }
      >
        {frame.topics.length === 0 ? (
          <EmptyState message="Belum ada pertemuan nih. Materi dan tugas akan muncul di sini setelah dosen menambahkannya." />
        ) : (
          frame.topics.map((t) => {
            const rows = t.items.filter((i) => i.kind === "assignment");
            const answered = rows.filter((i) => i.status).length;
            return (
              <section
                key={t.id}
                className="overflow-hidden rounded-lg border border-border bg-white"
              >
                <div className="flex items-center justify-between gap-4 border-b border-border px-4 py-3">
                  <Link
                    href={t.href}
                    className="truncate text-[15px] font-semibold text-ink hover:text-link"
                  >
                    Pertemuan {t.week}: {t.title}
                  </Link>
                  {rows.length > 0 ? (
                    <span className="shrink-0 text-[13px] text-muted">
                      {answered}/{rows.length} terkumpul
                    </span>
                  ) : null}
                </div>
                {t.items.length === 0 ? (
                  <p className="px-4 py-4 text-[14px] text-muted">
                    Belum ada isi di pertemuan ini.
                  </p>
                ) : (
                  t.items.map((item) => (
                    <StudentRow key={item.id} item={item} />
                  ))
                )}
              </section>
            );
          })
        )}
      </CourseFrame>
    </div>
  );
}
