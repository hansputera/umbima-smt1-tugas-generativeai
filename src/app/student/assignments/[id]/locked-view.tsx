import { fmtDate } from "@/lib/format";
import { StatusDot } from "@/components/ui/misc";
import { CircleCheck, CircleX } from "lucide-react";

type Question = {
  position: number;
  question: string;
  options: { key: string; text: string }[] | null;
  answer_key: string | null;
};

export function LockedView({
  type,
  questions,
  revealed,
  submission,
}: {
  type: string;
  questions: Question[];
  revealed: boolean;
  submission: {
    answer_text: string | null;
    answers: string[];
    file_name: string | null;
    extraction_ok: boolean | null;
    submitted_at: string | null;
  };
}) {
  return (
    <div className="p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h3>Jawaban Anda</h3>
        <span className="text-[13px] text-muted">
          {submission.submitted_at
            ? `Terkirim ${fmtDate(submission.submitted_at)}`
            : "Terkirim"}
          <span className="mx-2">·</span>
          Pengumpulan terkunci
        </span>
      </div>

      <div className="mt-4 flex flex-col gap-4 border-t border-border pt-4">
        {type === "pg"
          ? questions.map((item, i) => {
              const opts = Array.isArray(item.options) ? item.options : [];
              const chosenKey = submission.answers[i];
              return (
                <div key={item.position} className="flex flex-col gap-2">
                  {questions.length > 1 ? (
                    <span className="label">Soal {i + 1}</span>
                  ) : null}
                  <p className="text-[15px] leading-relaxed whitespace-pre-wrap">
                    {item.question}
                  </p>
                  <ul className="flex flex-col gap-1.5">
                    {opts.map((o) => {
                      const chosen = o.key === chosenKey;
                      const correct =
                        revealed && item.answer_key === o.key;
                      const wrongChosen = revealed && chosen && !correct;
                      return (
                        <li
                          key={o.key}
                          className={`flex items-center justify-between gap-3 rounded-md border px-3 py-2 text-[15px] ${
                            chosen
                              ? "border-ink font-medium"
                              : correct
                                ? "border-border"
                                : "border-border text-muted"
                          }`}
                        >
                          <span>
                            {o.key}. {o.text}
                          </span>
                          {chosen && !revealed ? (
                            <span className="text-[13px] text-muted">
                              Pilihan Anda
                            </span>
                          ) : null}
                          {correct ? (
                            <StatusDot
                              label={chosen ? "Benar" : "Kunci jawaban"}
                              color="#1d7a3e"
                              icon={CircleCheck}
                            />
                          ) : null}
                          {wrongChosen ? (
                            <StatusDot
                              label="Kurang tepat"
                              color="#ca3120"
                              icon={CircleX}
                            />
                          ) : null}
                        </li>
                      );
                    })}
                  </ul>
                  {!chosenKey ? (
                    <p className="text-[13px] text-muted">
                      Soal ini tidak dijawab.
                    </p>
                  ) : null}
                </div>
              );
            })
          : type === "essay" ? (
            <>
              <p className="text-[15px] leading-relaxed whitespace-pre-wrap text-muted">
                {questions[0]?.question}
              </p>
              <div className="flex flex-col gap-2 border-t border-border pt-4">
                <span className="label">Jawaban Anda</span>
                <div className="rounded-md border border-border p-4 text-[16px] leading-relaxed whitespace-pre-wrap">
                  {submission.answer_text?.trim() || (
                    <span className="text-muted">Jawaban kosong.</span>
                  )}
                </div>
              </div>
            </>
          ) : (
            <>
              <p className="text-[15px] leading-relaxed whitespace-pre-wrap text-muted">
                {questions[0]?.question}
              </p>
              <div className="flex flex-col gap-2 border-t border-border pt-4">
                <span className="label">Berkas Anda</span>
                <div className="rounded-md border border-border p-4">
                  <p className="text-[15px]">
                    {submission.file_name ?? "—"}
                    {submission.extraction_ok === false ? (
                      <span className="ml-3 text-danger">
                        Teks tidak terbaca.
                      </span>
                    ) : (
                      <span className="ml-3 text-muted">
                        Berkas terunggah.
                      </span>
                    )}
                  </p>
                </div>
              </div>
            </>
          )}
      </div>
    </div>
  );
}
