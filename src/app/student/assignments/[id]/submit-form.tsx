"use client";

import { useActionState, useState } from "react";
import { submitAssignment, type SubmitState } from "./actions";
import { Button } from "@/components/ui/button";
import { Field, Textarea } from "@/components/ui/field";
import { ErrorLine } from "@/components/ui/misc";

type Question = {
  position: number;
  question: string;
  options: { key: string; text: string }[] | null;
};

export function SubmitForm({
  assignment,
  questions,
}: {
  assignment: { id: string; type: string };
  questions: Question[];
}) {
  const [answer, setAnswer] = useState("");
  const [answers, setAnswers] = useState<string[]>(
    questions.map(() => ""),
  );
  const [current, setCurrent] = useState(0);
  const [fileName, setFileName] = useState("");
  const [state, action, pending] = useActionState<SubmitState, FormData>(
    submitAssignment,
    undefined,
  );

  const unanswered = answers.filter((a) => !a).length;
  const serializedAnswers = JSON.stringify(answers);
  const isPg = assignment.type === "pg";
  const pgQuestion = isPg ? questions[current] : undefined;
  const pgOptions = Array.isArray(pgQuestion?.options)
    ? pgQuestion.options
    : [];

  return (
    <form action={action} className="flex flex-col gap-4">
      <input type="hidden" name="assignment_id" value={assignment.id} />
      {isPg ? (
        <input type="hidden" name="answers" value={serializedAnswers} />
      ) : null}

      {assignment.type === "essay" ? (
        <Field
          label="Jawaban"
          htmlFor="answer"
          hint="Tulis jawaban secara lengkap."
        >
          <Textarea
            id="answer"
            name="answer"
            rows={8}
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            placeholder="Tulis jawaban Anda..."
          />
        </Field>
      ) : null}

      {isPg && pgQuestion ? (
        <div className="flex flex-col gap-4">
          {questions.length > 1 ? (
            <div className="flex flex-col gap-2">
              <span className="label">Navigasi soal</span>
              <div className="flex flex-wrap gap-1.5">
                {questions.map((q, i) => {
                  const answered = Boolean(answers[i]);
                  const isCurrent = i === current;
                  return (
                    <button
                      key={q.position}
                      type="button"
                      aria-label={`Soal ${i + 1}`}
                      aria-current={isCurrent ? "true" : undefined}
                      onClick={() => setCurrent(i)}
                      className={`flex size-9 cursor-pointer items-center justify-center rounded-md border text-[14px] transition duration-[220ms] ease-in-out ${
                        answered
                          ? "border-accent bg-accent text-white"
                          : "border-border text-muted hover:border-accent hover:text-accent"
                      } ${
                        isCurrent
                          ? "shadow-[0_0_0_3px_rgba(15,108,191,0.25)]"
                          : ""
                      }`}
                    >
                      {i + 1}
                    </button>
                  );
                })}
              </div>
              <p className="text-[13px] text-muted">
                Soal {current + 1} dari {questions.length}
                {unanswered > 0
                  ? ` · sisa ${unanswered} soal belum dijawab`
                  : ""}
              </p>
            </div>
          ) : null}

          <div className="flex flex-col gap-2">
            <span className="label">
              {questions.length > 1 ? `Soal ${current + 1}` : "Pertanyaan"}
            </span>
            <p className="text-[16px] leading-relaxed whitespace-pre-wrap">
              {pgQuestion.question}
            </p>
            <div className="mt-2 flex flex-col gap-1 border-t border-border pt-4">
              {pgOptions.map((o) => (
                <label
                  key={o.key}
                  className={`flex cursor-pointer items-center gap-3 rounded-md border p-3 transition-colors ${
                    answers[current] === o.key ? "border-ink" : "border-border"
                  }`}
                >
                  <input
                    type="radio"
                    name={`choice_${current}`}
                    value={o.key}
                    className="size-4 accent-accent"
                    checked={answers[current] === o.key}
                    onChange={() =>
                      setAnswers((prev) =>
                        prev.map((a, i) => (i === current ? o.key : a)),
                      )
                    }
                  />
                  <span className="text-[15px]">
                    <span className="font-medium">{o.key}.</span> {o.text}
                  </span>
                </label>
              ))}
            </div>
          </div>

          {questions.length > 1 ? (
            <div className="flex items-center gap-3 border-t border-border pt-4">
              <Button
                type="button"
                disabled={current === 0}
                onClick={() => setCurrent((c) => Math.max(0, c - 1))}
              >
                Sebelumnya
              </Button>
              <Button
                type="button"
                disabled={current === questions.length - 1}
                onClick={() =>
                  setCurrent((c) => Math.min(questions.length - 1, c + 1))
                }
              >
                Selanjutnya
              </Button>
            </div>
          ) : null}
        </div>
      ) : null}

      {assignment.type === "pdf" || assignment.type === "docx" ? (
        <Field
          label={`Berkas ${assignment.type.toUpperCase()}`}
          htmlFor="file"
          hint="Ukuran wajar, teks akan diekstrak untuk penilaian."
        >
          <input
            id="file"
            name="file"
            type="file"
            accept={assignment.type === "pdf" ? ".pdf" : ".docx"}
            className="text-[14px] text-muted file:mr-3 file:cursor-pointer file:rounded-md file:border file:border-border file:bg-white file:px-3 file:py-1.5 file:text-[14px] file:text-ink"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) setFileName(f.name);
            }}
          />
          {fileName ? (
            <p className="mt-1.5 text-[13px] text-muted">
              Terpilih: {fileName}
            </p>
          ) : null}
        </Field>
      ) : null}

      {state?.error ? <ErrorLine>{state.error}</ErrorLine> : null}

      <div className="flex items-center gap-3 border-t border-border pt-4">
        <Button
          type="submit"
          variant="primary"
          disabled={pending || (isPg && unanswered > 0)}
        >
          {pending ? "Mengirim..." : "Kirim jawaban"}
        </Button>
        <p className="text-[13px] text-muted">
          {isPg && unanswered > 0
            ? `Sisa ${unanswered} soal belum dijawab.`
            : "Setelah dikirim, jawaban terkunci dan tidak dapat diubah lagi."}
        </p>
      </div>
    </form>
  );
}
