import Link from "next/link";
import { notFound } from "next/navigation";
import { cookies } from "next/headers";
import { q1 } from "@/db/pool";
import { requireRole } from "@/lib/session";
import { fmtDate, fmtNilai } from "@/lib/format";
import {
  MODE_LABEL,
  TYPE_LABEL,
  statusOf,
  submissionStatus,
} from "@/lib/status";
import { buttonClass } from "@/components/ui/button";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Card, Notice, StatusDot } from "@/components/ui/misc";
import { ActivityIcon } from "@/components/course/activity-icon";
import { ClearFlash } from "@/components/clear-flash";
import { LockedView } from "./locked-view";
import { SubmitForm } from "./submit-form";

export const dynamic = "force-dynamic";

type GradeCriteria = {
  criterion_id: string;
  name: string;
  weight: number;
  score: number;
  quote: string;
  comment: string;
};

const STATUS_HINT: Record<string, string> = {
  belum: "Kerjakan dan kirim jawaban Anda untuk mengumpulkan.",
  draft: "Dosen sedang menyiapkan draf nilai.",
  terkumpul: "Menunggu penilaian dosen.",
  perlu_review: "Dosen sedang mereview jawaban Anda.",
  dinilai: "Nilai sudah diterbitkan. Periksa hasil penilaian di bawah.",
};

export default async function StudentAssignmentPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const student = await requireRole("student");
  const flash = (await cookies()).get("nilai_flash")?.value ?? "";
  const justSubmitted = flash === `terkirim:${id}:${student.id}`;

  const a = await q1<{
    id: string;
    title: string;
    type: string;
    questions: {
      position: number;
      question: string;
      options: { key: string; text: string }[] | null;
      answer_key: string | null;
    }[];
    release_mode: string;
    course_id: string;
    course_code: string;
    course_name: string;
    week: number;
    topic_title: string;
    topic_id: string;
    enrolled: boolean;
  }>(
    `SELECT a.id, a.title, a.type, a.release_mode,
            COALESCE((
              SELECT jsonb_agg(
                       jsonb_build_object(
                         'position', q.position,
                         'question', q.question,
                         'options', q.options,
                         'answer_key', q.answer_key
                       ) ORDER BY q.position
                     )
              FROM assignment_questions q
              WHERE q.assignment_id = a.id
            ), '[]'::jsonb) AS questions,
            t.course_id, t.week, t.title AS topic_title, t.id AS topic_id,
            c.code AS course_code, c.name AS course_name,
            EXISTS (
              SELECT 1 FROM enrollments e
               WHERE e.course_id = t.course_id AND e.student_id = $2
            ) AS enrolled
     FROM assignments a
     JOIN topics t ON t.id = a.topic_id
     JOIN courses c ON c.id = t.course_id
     WHERE a.id = $1`,
    [id, student.id],
  );
  if (!a || !a.enrolled) notFound();

  const submission = await q1<{
    id: string;
    answer_text: string | null;
    answers: string[];
    file_name: string | null;
    extraction_ok: boolean | null;
    status: string;
    submitted_at: string | null;
  }>(
    `SELECT id, answer_text, answers, file_name, extraction_ok, status, submitted_at
     FROM submissions
     WHERE assignment_id = $1 AND student_id = $2`,
    [a.id, student.id],
  );

  const grade = submission
    ? await q1<{
        state: string;
        criteria: GradeCriteria[];
        feedback: string;
        summary: string;
        nilai: number | string;
        predikat: string;
      }>(
        `SELECT state, criteria, feedback, summary, nilai, predikat
         FROM grades WHERE submission_id = $1 AND state = 'published'`,
        [submission.id],
      )
    : null;

  const statusKey = submissionStatus(
    submission?.status ?? null,
    Boolean(grade),
  );
  const status = statusOf(statusKey);
  const waiting = !grade && Boolean(submission);

  return (
    <div className="flex flex-col gap-4">
      <Breadcrumb
        rootHref="/student/home"
        items={[
          { label: "Kursus", href: "/student/courses" },
          { label: a.course_code, href: `/student/courses/${a.course_id}` },
          {
            label: `Pertemuan ${a.week}`,
            href: `/student/courses/${a.course_id}/topics/${a.topic_id}`,
          },
          { label: a.title },
        ]}
      />

      <div className="flex items-start justify-between gap-4">
        <div className="flex min-w-0 items-start gap-3">
          <ActivityIcon type={a.type} size={40} />
          <div className="min-w-0">
            <h1>{a.title}</h1>
            <p className="mt-1 text-[14px] text-muted">
              {a.course_code} — {a.course_name} · Pertemuan {a.week}:{" "}
              {a.topic_title}
            </p>
            <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-[14px]">
              <span className="text-muted">
                {TYPE_LABEL[a.type] ?? a.type}
              </span>
              <StatusDot
                label={status.label}
                color={status.color}
                icon={status.Icon}
              />
              <span className="text-muted">
                Rilis: {MODE_LABEL[a.release_mode] ?? a.release_mode}
              </span>
              {submission?.submitted_at ? (
                <span className="text-muted">
                  Dikumpulkan {fmtDate(submission.submitted_at)}
                </span>
              ) : null}
            </div>
            {STATUS_HINT[statusKey] ? (
              <p className="mt-1.5 text-[13px] text-muted">
                {STATUS_HINT[statusKey]}
              </p>
            ) : null}
          </div>
        </div>
        <Link
          href={`/student/courses/${a.course_id}/topics/${a.topic_id}`}
          className={`${buttonClass()} shrink-0`}
        >
          Ke pertemuan
        </Link>
      </div>

      {justSubmitted ? (
        <>
          <Notice dot="#1d7a3e">
            Terkirim! Jawaban Anda sudah terkunci dan tidak bisa diubah lagi.
          </Notice>
          <ClearFlash name="nilai_flash" />
        </>
      ) : null}

      {waiting ? (
        <Notice>
          {submission?.status === "needs_review"
            ? "Tenang, jawabanmu sedang menunggu review dosen."
            : "Tenang, nilai akan terbit setelah dosen me-review jawabanmu."}
        </Notice>
      ) : null}

      <Card className="overflow-hidden">
        {!submission && a.type !== "pg" ? (
          <div className="border-b border-border p-6">
            <span className="label">Pertanyaan</span>
            <p className="mt-2 text-[16px] leading-relaxed whitespace-pre-wrap">
              {a.questions[0]?.question}
            </p>
          </div>
        ) : null}

        {submission ? (
          <LockedView
            type={a.type}
            revealed={Boolean(grade)}
            questions={a.questions.map((item) => ({
              position: item.position,
              question: item.question,
              options: item.options,
              answer_key: grade ? item.answer_key : null,
            }))}
            submission={{
              answer_text: submission.answer_text,
              answers: submission.answers ?? [],
              file_name: submission.file_name,
              extraction_ok: submission.extraction_ok,
              submitted_at: submission.submitted_at,
            }}
          />
        ) : (
          <div className="p-6">
            <h3 className="mb-4">Kerjakan tugas</h3>
            <SubmitForm
              assignment={{ id: a.id, type: a.type }}
              questions={a.questions.map((item) => ({
                position: item.position,
                question: item.question,
                options: item.options,
              }))}
            />
          </div>
        )}

        {grade ? (
          <div className="border-t border-border p-6">
            <div className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <h3>Hasil penilaian</h3>
                <StatusDot
                  label={statusOf("published").label}
                  color={statusOf("published").color}
                  icon={statusOf("published").Icon}
                />
              </div>
              <p className="text-[32px] leading-none font-semibold tracking-tight">
                {fmtNilai(grade.nilai)}
                <span className="ml-3 align-middle text-[14px] font-normal text-muted">
                  Predikat {grade.predikat}
                </span>
              </p>
            </div>

            {grade.criteria.length > 0 ? (
              <div className="mt-5 flex flex-col border-t border-border">
                {grade.criteria.map((c) => (
                  <div
                    key={c.criterion_id}
                    className="flex items-start justify-between gap-6 border-b border-border py-3"
                  >
                    <div className="flex flex-col gap-1">
                      <span className="text-[15px] font-medium">
                        {c.name}
                        <span className="ml-2 text-[13px] font-normal text-muted">
                          bobot {c.weight}%
                        </span>
                      </span>
                      <span className="text-[14px] leading-relaxed text-muted">
                        {c.comment}
                      </span>
                    </div>
                    <span className="shrink-0 text-[15px] font-medium">
                      {c.score}/4
                    </span>
                  </div>
                ))}
              </div>
            ) : null}

            <div className="mt-5 border-t border-border pt-4">
              <span className="label">Umpan balik</span>
              <p className="mt-2 text-[15px] leading-relaxed whitespace-pre-wrap">
                {grade.feedback}
              </p>
              {grade.summary ? (
                <>
                  <span className="label mt-4 block">Ringkasan</span>
                  <p className="mt-2 text-[15px] leading-relaxed whitespace-pre-wrap text-muted">
                    {grade.summary}
                  </p>
                </>
              ) : null}
            </div>
          </div>
        ) : null}
      </Card>
    </div>
  );
}
