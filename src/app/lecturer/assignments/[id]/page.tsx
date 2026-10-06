import Link from "next/link";
import { q } from "@/db/pool";
import { getAssignmentQuestions, getRubric } from "@/lib/grading";
import { requireLecturerAssignment } from "@/lib/lecturer";
import {
  getSettings,
  isEmbeddingConfigured,
  isModelConfigured,
} from "@/lib/settings";
import { fmtDate, fmtNilai } from "@/lib/format";
import { MODE_LABEL, TYPE_LABEL, statusOf, submissionStatus } from "@/lib/status";
import { buttonClass } from "@/components/ui/button";
import { EmptyState, Section, StatusDot } from "@/components/ui/misc";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { ActivityIcon } from "@/components/course/activity-icon";
import { Table, Td, Th, Tr } from "@/components/ui/table";
import { ReleaseModeCard } from "./release-mode-card";
import { RubricEditor } from "./rubric-editor";

export const dynamic = "force-dynamic";

export default async function AssignmentPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const { assignment, topic, course } = await requireLecturerAssignment(id);

  const [questions, rubric, settings, inbox] = await Promise.all([
    getAssignmentQuestions(assignment.id),
    getRubric(assignment.id),
    getSettings(),
    q<{
      id: string;
      status: string | null;
      submitted_at: string | null;
      student_name: string;
      published: boolean;
      nilai: number | string | null;
    }>(
      `SELECT s.id, s.status, s.submitted_at, u.name AS student_name,
              COALESCE(g.state = 'published', false) AS published, g.nilai
       FROM submissions s
       JOIN users u ON u.id = s.student_id
       LEFT JOIN grades g ON g.submission_id = s.id
       WHERE s.assignment_id = $1
       ORDER BY u.name`,
      [assignment.id],
    ),
  ]);

  const rubricSum = rubric.reduce((sum, c) => sum + Number(c.weight), 0);
  const needsEmbedding =
    assignment.type === "pdf" || assignment.type === "docx";

  return (
    <div className="flex flex-col gap-4">
      <Breadcrumb
        rootHref="/lecturer/home"
        items={[
          { label: "Kursus", href: "/lecturer/courses" },
          { label: course.code, href: `/lecturer/courses/${course.id}` },
          {
            label: `Pertemuan ${topic.week}`,
            href: `/lecturer/courses/${course.id}/topics/${topic.id}`,
          },
          { label: assignment.title },
        ]}
      />

      <div className="flex items-start justify-between gap-4">
        <div className="flex min-w-0 items-start gap-3">
          <ActivityIcon type={assignment.type} size={40} />
          <div className="min-w-0">
            <h1>{assignment.title}</h1>
            <p className="mt-1 text-[14px] text-muted">
              {course.code} — {course.name} · Pertemuan {topic.week}:{" "}
              {topic.title}
            </p>
            <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-[14px] text-muted">
              <span>{TYPE_LABEL[assignment.type] ?? assignment.type}</span>
              <span>
                Rilis:{" "}
                {MODE_LABEL[assignment.release_mode] ??
                  assignment.release_mode}
              </span>
              {questions.length > 1 ? <span>{questions.length} soal</span> : null}
            </div>
          </div>
        </div>
        <Link
          href={`/lecturer/courses/${course.id}/topics/${topic.id}`}
          className={`${buttonClass()} shrink-0`}
        >
          Ke pertemuan
        </Link>
      </div>

      <div className="rounded-lg border border-border bg-white p-6 shadow-menu">
        <div className="mt-1 flex flex-col gap-4">
          {questions.length === 1 ? (
            <span className="label">Pertanyaan</span>
          ) : null}
          {questions.map((item, i) => {
            const opts = Array.isArray(item.options)
              ? (item.options as { key: string; text: string }[])
              : [];
            return (
              <div
                key={item.position}
                className={
                  questions.length > 1
                    ? "flex flex-col gap-2 rounded-md border border-border p-4"
                    : "flex flex-col gap-2"
                }
              >
                {questions.length > 1 ? (
                  <span className="label">Soal {i + 1}</span>
                ) : null}
                <p className="text-[16px] leading-relaxed whitespace-pre-wrap">
                  {item.question}
                </p>
                {assignment.type === "pg" ? (
                  <>
                    <p className="text-[14px] text-muted">
                      Kunci jawaban:{" "}
                      <span className="font-medium text-ink">
                        {item.answer_key ?? "—"}
                      </span>
                    </p>
                    {opts.length > 0 ? (
                      <ul className="flex flex-col gap-1">
                        {opts.map((o) => (
                          <li key={o.key} className="text-[14px] text-muted">
                            <span className="font-medium text-ink">{o.key}.</span>{" "}
                            {o.text}
                          </li>
                        ))}
                      </ul>
                    ) : null}
                  </>
                ) : null}
              </div>
            );
          })}
        </div>
      </div>

      <ReleaseModeCard
        assignmentId={assignment.id}
        initialMode={assignment.release_mode}
        rubricSum={rubricSum}
        modelOk={isModelConfigured(settings)}
        embedOk={isEmbeddingConfigured(settings)}
        needsEmbedding={needsEmbedding}
      />

      <RubricEditor assignmentId={assignment.id} initialRows={rubric} />

      <Section title="Pengumpulan">
        {inbox.length === 0 ? (
          <EmptyState message="Belum ada pengumpulan. Jawaban mahasiswa akan muncul di sini." />
        ) : (
          <Table>
            <thead>
              <tr>
                <Th>Mahasiswa</Th>
                <Th>Status</Th>
                <Th>Dikumpulkan</Th>
                <Th>Nilai</Th>
                <Th className="text-right">Aksi</Th>
              </tr>
            </thead>
            <tbody>
              {inbox.map((s) => {
                const key = submissionStatus(s.status, s.published);
                const status = statusOf(key);
                return (
                  <Tr key={s.id}>
                    <Td className="font-medium">{s.student_name}</Td>
                    <Td>
                      <StatusDot label={status.label} color={status.color} icon={status.Icon} />
                    </Td>
                    <Td>{fmtDate(s.submitted_at)}</Td>
                    <Td>{s.nilai !== null ? fmtNilai(s.nilai) : "—"}</Td>
                    <Td>
                      <div className="flex justify-end">
                        <Link
                          href={`/lecturer/submissions/${s.id}`}
                          className={`${buttonClass()} px-2.5 py-1 text-[13px]`}
                        >
                          Buka
                        </Link>
                      </div>
                    </Td>
                  </Tr>
                );
              })}
            </tbody>
          </Table>
        )}
      </Section>
    </div>
  );
}
