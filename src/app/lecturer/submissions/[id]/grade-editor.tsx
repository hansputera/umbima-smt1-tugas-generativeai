"use client";

import { useActionState, useRef, useState } from "react";
import {
  runGrade,
  saveGrade,
  type GradeActionState,
} from "./actions";
import { Button } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/field";
import { ErrorLine, Notice, StatusDot } from "@/components/ui/misc";
import { statusOf } from "@/lib/status";

type RubricC = {
  id: string;
  name: string;
  weight: number;
};

type GradeC = {
  criterion_id: string;
  name: string;
  weight: number;
  score: number;
  quote: string;
  comment: string;
};

type Row = {
  id: string;
  name: string;
  weight: number;
  score: number;
  quote: string;
  comment: string;
};

function buildRows(rubric: RubricC[], criteria: GradeC[]): Row[] {
  return rubric.map((c) => {
    const prev = criteria.find((x) => x.criterion_id === c.id);
    return {
      id: c.id,
      name: c.name,
      weight: Number(c.weight),
      score: prev ? Number(prev.score) : 1,
      quote: prev?.quote ?? "",
      comment: prev?.comment ?? "",
    };
  });
}

function predikatOf(nilai: number): string {
  if (nilai >= 85) return "A";
  if (nilai >= 70) return "B";
  if (nilai >= 55) return "C";
  return "D";
}

export function GradeEditor({
  submission,
  rubric,
  initialGrade,
}: {
  submission: {
    id: string;
    type: string;
    release_mode: string;
  };
  rubric: RubricC[];
  initialGrade: {
    criteria: GradeC[];
    feedback: string;
    summary: string;
    nilai: number;
    predikat: string;
    state: "draft" | "published";
  } | null;
}) {
  const isPg = submission.type === "pg";
  const isLangsung = submission.release_mode === "langsung";

  const [rows, setRows] = useState<Row[]>(() =>
    buildRows(rubric, initialGrade?.criteria ?? []),
  );
  const [feedback, setFeedback] = useState(initialGrade?.feedback ?? "");
  const [summary, setSummary] = useState(initialGrade?.summary ?? "");
  const [grade, setGrade] = useState(initialGrade);
  const saveForm = useRef<HTMLFormElement>(null);
  const runForm = useRef<HTMLFormElement>(null);

  const [saveState, saveAction, savePending] = useActionState<
    GradeActionState,
    FormData
  >(saveGrade, undefined);
  const [runState, runAction, runPending] = useActionState<
    GradeActionState,
    FormData
  >(runGrade, undefined);

  const state = saveState ?? runState;

  const [seenState, setSeenState] = useState(state);
  if (state !== seenState) {
    setSeenState(state);
    if (state?.grade) {
      setGrade(state.grade);
      setRows(buildRows(rubric, state.grade.criteria));
      setFeedback(state.grade.feedback);
      setSummary(state.grade.summary);
    }
  }

  function submitSave(intent: "draft" | "publish") {
    const form = saveForm.current;
    if (!form) return;
    const input = form.querySelector<HTMLInputElement>('input[name="intent"]');
    if (input) input.value = intent;
    form.requestSubmit();
  }

  const total = rows.reduce((s, r) => s + (r.score / 4) * r.weight, 0);
  const liveNilai = Math.round(total * 100) / 100;
  const weightSum = rows.reduce((s, r) => s + r.weight, 0);
  const shownNilai = grade ? Number(grade.nilai) : liveNilai;
  const shownPredikat = grade ? grade.predikat : predikatOf(liveNilai);
  const stateBadge = statusOf(
    (grade?.state ?? "draft") === "published" ? "published" : "draft",
  );

  const payload = rows.map((r) => ({
    id: r.id,
    score: r.score,
    quote: r.quote,
    comment: r.comment,
  }));

  if (isPg) {
    return (
      <div className="flex flex-col gap-4 rounded-lg border border-border bg-white p-6 shadow-menu">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <span className="label">Penilaian otomatis</span>
            <StatusDot label={stateBadge.label} color={stateBadge.color} icon={stateBadge.Icon} />
          </div>
          {grade ? (
            <p className="text-[28px] leading-none font-semibold tracking-tight">
              {shownNilai}
              <span className="ml-2 align-middle text-[14px] font-normal text-muted">
                Predikat {shownPredikat}
              </span>
            </p>
          ) : null}
        </div>
        <p className="text-[14px] leading-relaxed whitespace-pre-wrap">
          {grade?.feedback || "Belum dinilai."}
        </p>
        {state?.error ? <ErrorLine>{state.error}</ErrorLine> : null}
        {state?.info ? <Notice dot="#1d7a3e">{state.info}</Notice> : null}
        <form action={runAction} className="flex items-center gap-3 border-t border-border pt-4">
          <input type="hidden" name="submission_id" value={submission.id} />
          <input type="hidden" name="intent" value="publish" />
          <Button type="submit" variant="primary" disabled={runPending}>
            {runPending ? "Menghitung..." : "Hitung nilai"}
          </Button>
          <p className="text-[13px] text-muted">
            Dihitung dari kunci jawaban, tanpa model.
          </p>
        </form>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 rounded-lg border border-border bg-white p-6 shadow-menu">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <h3>Penilaian</h3>
          <StatusDot label={stateBadge.label} color={stateBadge.color} icon={stateBadge.Icon} />
        </div>
        <p className="text-[28px] leading-none font-semibold tracking-tight">
          {liveNilai}
          <span className="ml-2 align-middle text-[14px] font-normal text-muted">
            Predikat {predikatOf(liveNilai)}
          </span>
        </p>
      </div>

      <div className="flex flex-col border-t border-border">
        {rows.map((r, i) => (
          <div
            key={r.id}
            className="flex flex-col gap-2 border-b border-border py-3"
          >
            <div className="flex items-center justify-between gap-4">
              <span className="text-[15px] font-medium">
                {r.name}
                <span className="ml-2 text-[13px] font-normal text-muted">
                  bobot {r.weight}%
                </span>
              </span>
              <select
                aria-label={`Skor ${r.name}`}
                className="h-9 w-20 cursor-pointer rounded-md border border-border bg-transparent px-2 text-[16px]"
                value={r.score}
                onChange={(e) => {
                  const v = Number(e.target.value);
                  setRows((prev) =>
                    prev.map((row, j) => (j === i ? { ...row, score: v } : row)),
                  );
                }}
              >
                <option value={1}>1</option>
                <option value={2}>2</option>
                <option value={3}>3</option>
                <option value={4}>4</option>
              </select>
            </div>
            <Input
              placeholder="Kutipan dari jawaban"
              value={r.quote}
              onChange={(e) => {
                const v = e.target.value;
                setRows((prev) =>
                  prev.map((row, j) => (j === i ? { ...row, quote: v } : row)),
                );
              }}
            />
            <Input
              placeholder="Komentar"
              value={r.comment}
              onChange={(e) => {
                const v = e.target.value;
                setRows((prev) =>
                  prev.map((row, j) => (j === i ? { ...row, comment: v } : row)),
                );
              }}
            />
          </div>
        ))}
      </div>

      {weightSum !== 100 ? (
        <ErrorLine>Bobot rubrik berjumlah {weightSum}%, seharusnya 100%.</ErrorLine>
      ) : null}

      <div className="flex flex-col gap-3">
        <label className="label" htmlFor="gf">
          Umpan balik
        </label>
        <Textarea
          id="gf"
          rows={3}
          value={feedback}
          onChange={(e) => setFeedback(e.target.value)}
        />
        <label className="label" htmlFor="gs">
          Ringkasan
        </label>
        <Textarea
          id="gs"
          rows={2}
          value={summary}
          onChange={(e) => setSummary(e.target.value)}
        />
      </div>

      {state?.error ? <ErrorLine>{state.error}</ErrorLine> : null}
      {state?.info ? <Notice dot="#1d7a3e">{state.info}</Notice> : null}
      {state?.raw ? (
        <div className="flex flex-col gap-1.5">
          <span className="label">Respons model mentah</span>
          <pre className="max-h-64 overflow-auto rounded-md border border-border bg-white p-3 shadow-menu font-mono text-[13px] leading-relaxed whitespace-pre-wrap break-all">
            {state.raw}
          </pre>
        </div>
      ) : null}

      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-4">
        <div className="flex items-center gap-3">
          <Button
            type="button"
            onClick={() => runForm.current?.requestSubmit()}
            disabled={runPending}
          >
            {runPending ? "Memproses..." : "Nilai dengan model"}
          </Button>
          <p className="text-[13px] text-muted">
            {isLangsung
              ? "Mode langsun rilis: nilai terbit saat disimpan."
              : "Saran nilai dari model, Anda tetap bisa memperbaikinya."}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button
            type="button"
            disabled={savePending}
            onClick={() => submitSave("draft")}
          >
            {savePending ? "Menyimpan..." : "Simpan nilai"}
          </Button>
          <Button
            type="button"
            variant="primary"
            disabled={savePending}
            onClick={() => submitSave("publish")}
          >
            Terbitkan
          </Button>
        </div>
      </div>

      <form ref={saveForm} action={saveAction} className="hidden">
        <input type="hidden" name="submission_id" value={submission.id} />
        <input type="hidden" name="criteria" value={JSON.stringify(payload)} />
        <input type="hidden" name="feedback" value={feedback} />
        <input type="hidden" name="summary" value={summary} />
        <input type="hidden" name="intent" defaultValue="draft" />
      </form>
      <form ref={runForm} action={runAction} className="hidden">
        <input type="hidden" name="submission_id" value={submission.id} />
        <input type="hidden" name="intent" value="draft" />
      </form>
    </div>
  );
}
