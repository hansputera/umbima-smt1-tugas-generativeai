import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft, ArrowRight } from "lucide-react";
import { q, q1 } from "@/db/pool";
import { requireRole } from "@/lib/session";
import { fmtNilai } from "@/lib/format";
import { submissionStatus } from "@/lib/status";
import { getCourseFrame } from "@/lib/course-view";
import { buttonClass } from "@/components/ui/button";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { CourseFrame } from "@/components/course/course-frame";
import { courseTabs } from "@/components/course/tabs";
import { AssignmentRow } from "@/components/assignment-row";

export const dynamic = "force-dynamic";

type Block = {
  type: string;
  body: string | null;
  url: string | null;
  file_name: string | null;
};

export default async function StudentTopicPage({
  params,
}: {
  params: Promise<{ id: string; topicId: string }>;
}) {
  const { id, topicId } = await params;
  const student = await requireRole("student");

  const course = await q1<{
    id: string;
    code: string;
    name: string;
  }>(
    `SELECT c.id, c.code, c.name
     FROM courses c
     JOIN enrollments e ON e.course_id = c.id AND e.student_id = $2
     WHERE c.id = $1`,
    [id, student.id],
  );
  if (!course) notFound();

  const topic = await q1<{ id: string; week: number; title: string }>(
    "SELECT id, week, title FROM topics WHERE id = $1 AND course_id = $2",
    [topicId, course.id],
  );
  if (!topic) notFound();

  const frame = await getCourseFrame(course.id, "student", student.id);
  const idx = frame.topics.findIndex((t) => t.id === topic.id);
  const prev = idx > 0 ? frame.topics[idx - 1] : null;
  const next =
    idx >= 0 && idx < frame.topics.length - 1 ? frame.topics[idx + 1] : null;

  const blocks = await q<Block>(
    `SELECT type, body, url, file_name FROM materi_blocks
     WHERE topic_id = $1 ORDER BY position`,
    [topic.id],
  );

  const assignments = await q<{
    id: string;
    title: string;
    type: string;
    release_mode: string;
    status: string | null;
    grade_state: string | null;
    nilai: number | string | null;
  }>(
    `SELECT a.id, a.title, a.type, a.release_mode,
            s.status, g.state AS grade_state, g.nilai
     FROM assignments a
     LEFT JOIN submissions s ON s.assignment_id = a.id AND s.student_id = $2
     LEFT JOIN grades g ON g.submission_id = s.id
     WHERE a.topic_id = $1
     ORDER BY a.created_at`,
    [topic.id, student.id],
  );

  return (
    <div className="flex flex-col gap-4">
      <Breadcrumb
        rootHref="/student/home"
        items={[
          { label: "Kursus", href: "/student/courses" },
          { label: course.code, href: `/student/courses/${course.id}` },
          { label: `Pertemuan ${topic.week}` },
        ]}
      />
      <CourseFrame
        courseLabel={`${course.code} — ${course.name}`}
        courseHref={`/student/courses/${course.id}`}
        index={frame.topics}
        activeTopicId={topic.id}
        title={
          <>
            <h1 className="course-title">
              Pertemuan {topic.week}: {topic.title}
            </h1>
            <p className="mt-1 text-[14px] text-muted">
              {course.code} — {course.name}
            </p>
          </>
        }
        action={
          <Link
            href={`/student/courses/${course.id}`}
            className={buttonClass()}
          >
            Ke mata kuliah
          </Link>
        }
        tabs={courseTabs(course.id, "student")}
      >
        <section className="flex flex-col gap-3">
          <h2>Materi</h2>
          {blocks.length === 0 ? (
            <div className="rounded-lg border border-border bg-white px-4 py-5 shadow-menu">
              <p className="text-[14px] text-muted">
                Belum ada materi di pertemuan ini.
              </p>
            </div>
          ) : (
            <div className="rounded-lg border border-border bg-white p-4 shadow-menu">
              <ul className="flex flex-col gap-2.5">
                {blocks.map((b, i) => (
                  <li
                    key={i}
                    className="flex items-start gap-2.5 text-[15px] leading-relaxed"
                  >
                    <span className="mt-2 inline-block size-1.5 shrink-0 rounded-full bg-border" />
                    {b.type === "richtext" ? (
                      <span className="whitespace-pre-wrap">{b.body}</span>
                    ) : b.type === "link" ? (
                      <a
                        href={b.url ?? "#"}
                        target="_blank"
                        rel="noreferrer"
                        className="text-ink underline underline-offset-2 hover:text-link"
                      >
                        {b.body || b.url}
                      </a>
                    ) : (
                      <span className="text-muted">Berkas: {b.file_name}</span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>

        <section className="flex flex-col gap-3">
          <h2>Tugas</h2>
          {assignments.length === 0 ? (
            <div className="rounded-lg border border-border bg-white px-4 py-5 shadow-menu">
              <p className="text-[14px] text-muted">
                Belum ada tugas di pertemuan ini. Cek pertemuan lain, yuk!
              </p>
            </div>
          ) : (
            <div className="flex flex-col gap-3">
              {assignments.map((a) => {
                const key = submissionStatus(
                  a.status,
                  a.grade_state === "published",
                );
                const nilai =
                  a.grade_state === "published" && a.nilai !== null
                    ? fmtNilai(a.nilai)
                    : null;
                return (
                  <AssignmentRow
                    key={a.id}
                    href={`/student/assignments/${a.id}`}
                    title={a.title}
                    type={a.type}
                    releaseMode={a.release_mode}
                    statusKey={key}
                    nilai={nilai}
                    action={a.status === null ? "Kerjakan" : "Lihat jawaban"}
                  />
                );
              })}
            </div>
          )}
        </section>

        <nav className="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-4">
          {prev ? (
            <Link
              href={prev.href}
              className="group flex items-center gap-2 text-[14px] text-muted hover:text-ink"
            >
              <ArrowLeft
                size={16}
                strokeWidth={1.5}
                className="transition-transform group-hover:-translate-x-1"
                aria-hidden
              />
              <span className="max-w-[240px] truncate">
                Pertemuan {prev.week}: {prev.title}
              </span>
            </Link>
          ) : (
            <span />
          )}
          {next ? (
            <Link
              href={next.href}
              className="group flex items-center gap-2 text-right text-[14px] text-muted hover:text-ink"
            >
              <span className="max-w-[240px] truncate">
                Pertemuan {next.week}: {next.title}
              </span>
              <ArrowRight
                size={16}
                strokeWidth={1.5}
                className="transition-transform group-hover:translate-x-1"
                aria-hidden
              />
            </Link>
          ) : (
            <span />
          )}
        </nav>
      </CourseFrame>
    </div>
  );
}
