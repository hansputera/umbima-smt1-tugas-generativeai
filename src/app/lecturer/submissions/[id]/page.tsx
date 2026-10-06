import Link from "next/link";
import { q } from "@/db/pool";
import { getGrade, getRubric, getLecturerSubmission } from "@/lib/grading";
import { requireLecturer } from "@/lib/lecturer";
import { fmtDate, fmtNilai } from "@/lib/format";
import { TYPE_LABEL, statusOf } from "@/lib/status";
import { buttonClass } from "@/components/ui/button";
import { StatusDot } from "@/components/ui/misc";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { ActivityIcon } from "@/components/course/activity-icon";
import { GradeEditor } from "./grade-editor";

export const dynamic = "force-dynamic";

export default async function SubmissionPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const lecturer = await requireLecturer();
  const sub = await getLecturerSubmission(id, lecturer.id);
  if (!sub) {
    return (
      <div className="flex flex-col gap-6">
        <h1>Pengumpulan</h1>
        <p className="text-[15px] text-muted">Tidak ditemukan.</p>
        <Link href="/lecturer/submissions" className={buttonClass()}>
          Ke daftar pengumpulan
        </Link>
      </div>
    );
  }

  const [rubric, grade, revisions] = await Promise.all([
    sub.type === "pg" ? Promise.resolve([]) : getRubric(sub.assignment_id),
    getGrade(sub.id),
    q<{
      id: string;
      nilai: number | string;
      predikat: string;
      state: string;
      changed_at: string;
      changed_by_name: string | null;
    }>(
      `SELECT r.id, r.nilai, r.predikat, r.state, r.changed_at, u.name AS changed_by_name
       FROM grade_revisions r
       JOIN grades g ON g.id = r.grade_id
       LEFT JOIN users u ON u.id = r.changed_by
       WHERE g.submission_id = $1
       ORDER BY r.changed_at DESC`,
      [sub.id],
    ),
  ]);

  const questions = sub.questions ?? [];
  const answers = sub.answers ?? [];

  return (
    <div className="flex flex-col gap-4">
      <Breadcrumb
        rootHref="/lecturer/home"
        items={[
          { label: "Pengumpulan", href: "/lecturer/submissions" },
          {
            label: sub.assignment_title,
            href: `/lecturer/assignments/${sub.assignment_id}`,
          },
          { label: sub.student_name },
        ]}
      />

      <div className="flex items-start justify-between gap-4">
        <div className="flex min-w-0 items-start gap-3">
          <ActivityIcon type={sub.type} size={40} />
          <div className="min-w-0">
            <h1>{sub.student_name}</h1>
            <p className="mt-1 text-[14px] text-muted">
              {sub.assignment_title} · {sub.course_code} — {sub.course_name}
            </p>
            <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1.5 text-[14px] text-muted">
              <span>{TYPE_LABEL[sub.type] ?? sub.type}</span>
              <span>{fmtDate(sub.submitted_at)}</span>
            </div>
          </div>
        </div>
        <Link
          href={`/lecturer/assignments/${sub.assignment_id}`}
          className={`${buttonClass()} shrink-0`}
        >
          Ke tugas
        </Link>
      </div>

      <div className="grid items-start gap-4 lg:grid-cols-[1fr_400px]">
        <div className="flex min-w-0 flex-col gap-4">
          <div className="rounded-lg border border-border bg-white p-6 shadow-menu">
            <div className="flex flex-col gap-4">
              {questions.map((item, i) => (
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
                </div>
              ))}
            </div>
            <div className="mt-4 border-t border-border pt-4">
              <span className="label">Jawaban mahasiswa</span>
              <div className="mt-2 text-[16px] leading-relaxed whitespace-pre-wrap">
                {sub.type === "pg" ? (
                  questions.length === 0 ? (
                    <span className="text-muted">
                      Belum ada jawaban dari mahasiswa.
                    </span>
                  ) : (
                    <ol className="flex flex-col gap-2">
                      {questions.map((item, i) => {
                        const chosen = Array.isArray(item.options)
                          ? item.options.find((o) => o.key === answers[i])
                          : undefined;
                        return (
                          <li key={item.position} className="text-[15px]">
                            <span className="text-muted">Soal {i + 1}:</span>{" "}
                            {answers[i] ? (
                              <>
                                <span className="font-medium">
                                  {answers[i]}
                                </span>
                                {chosen ? ` — ${chosen.text}` : ""}
                              </>
                            ) : (
                              <span className="text-muted">
                                Belum dijawab.
                              </span>
                            )}
                          </li>
                        );
                      })}
                    </ol>
                  )
                ) : sub.type === "essay" ? (
                  sub.answer_text?.trim() ? (
                    sub.answer_text
                  ) : (
                    <span className="text-muted">Jawaban kosong.</span>
                  )
                ) : sub.extraction_ok === false ? (
                  <span className="text-danger">Teks tidak terbaca.</span>
                ) : sub.extracted_text?.trim() ? (
                  <span className="block max-h-80 overflow-y-auto">
                    {sub.extracted_text}
                  </span>
                ) : (
                  <span className="text-muted">
                    Berkas: {sub.file_name ?? "—"}
                  </span>
                )}
              </div>
            </div>
          </div>

          {revisions.length > 0 ? (
            <section className="flex flex-col gap-3">
              <h2>Riwayat nilai</h2>
              <div className="rounded-lg border border-border bg-white shadow-menu">
                {revisions.map((r, i) => (
                  <div
                    key={r.id}
                    className={`flex items-center justify-between gap-4 px-4 py-3 ${
                      i > 0 ? "border-t border-border" : ""
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <StatusDot
                        label={statusOf(
                          r.state === "published" ? "published" : "draft",
                        ).label}
                        color={statusOf(
                          r.state === "published" ? "published" : "draft",
                        ).color}
                        icon={statusOf(
                          r.state === "published" ? "published" : "draft",
                        ).Icon}
                      />
                      <span className="text-[14px]">
                        {fmtNilai(r.nilai)} · {r.predikat}
                      </span>
                    </div>
                    <div className="text-right text-[13px] text-muted">
                      <span>{r.changed_by_name ?? "Sistem"}</span>
                      <span className="mx-2">·</span>
                      <span>{fmtDate(r.changed_at)}</span>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          ) : null}
        </div>

        <GradeEditor
          submission={{
            id: sub.id,
            type: sub.type,
            release_mode: sub.release_mode,
          }}
          rubric={rubric.map((c) => ({
            id: c.id,
            name: c.name,
            weight: Number(c.weight),
          }))}
          initialGrade={
            grade
              ? {
                  criteria: grade.criteria,
                  feedback: grade.feedback,
                  summary: grade.summary,
                  nilai: Number(grade.nilai),
                  predikat: grade.predikat,
                  state: grade.state,
                }
              : null
          }
        />
      </div>
    </div>
  );
}
