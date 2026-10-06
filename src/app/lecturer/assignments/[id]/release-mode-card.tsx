"use client";

import { useActionState, useState } from "react";
import { saveReleaseMode, type ModeSaveState } from "./actions";
import { Button } from "@/components/ui/button";
import { Card, ErrorLine, Notice } from "@/components/ui/misc";

export function ReleaseModeCard({
  assignmentId,
  initialMode,
  rubricSum,
  modelOk,
  embedOk,
  needsEmbedding,
}: {
  assignmentId: string;
  initialMode: string;
  rubricSum: number;
  modelOk: boolean;
  embedOk: boolean;
  needsEmbedding: boolean;
}) {
  const [mode, setMode] = useState(initialMode === "langsung" ? "langsung" : "review");
  const [confirmed, setConfirmed] = useState(false);
  const [state, action, pending] = useActionState<ModeSaveState, FormData>(
    saveReleaseMode,
    undefined,
  );

  const [seenMode, setSeenMode] = useState(initialMode);
  if (initialMode !== seenMode) {
    setSeenMode(initialMode);
    setMode(initialMode === "langsung" ? "langsung" : "review");
  }

  const [seenState, setSeenState] = useState(state);
  if (state !== seenState) {
    setSeenState(state);
    if (state?.info) setConfirmed(false);
  }

  const blockers: string[] = [];
  if (mode === "langsung") {
    if (rubricSum !== 100) blockers.push("Rubrik harus berjumlah 100.");
    if (!modelOk) blockers.push("Model belum disetel.");
    if (needsEmbedding && !embedOk) blockers.push("Embedding belum disetel.");
  }

  const options: { value: string; label: string; desc: string }[] = [
    {
      value: "review",
      label: "Review dulu",
      desc: "Nilai disimpan sebagai draf sampai dosen menerbitkannya.",
    },
    {
      value: "langsung",
      label: "Langsung rilis",
      desc: "Nilai langsung terlihat mahasiswa saat disimpan.",
    },
  ];

  return (
    <Card className="p-6">
      <h3>Mode rilis</h3>
      <form action={action} className="mt-4 flex flex-col gap-4">
        <input type="hidden" name="assignment_id" value={assignmentId} />
        <input type="hidden" name="mode" value={mode} />

        <div className="flex flex-col gap-2">
          {options.map((o) => (
            <label
              key={o.value}
              className={`flex cursor-pointer items-start gap-3 rounded-md border p-3 transition-colors ${
                mode === o.value ? "border-ink" : "border-border"
              }`}
            >
              <input
                type="radio"
                name="mode_choice"
                value={o.value}
                className="mt-1 size-4 accent-accent"
                checked={mode === o.value}
                onChange={() => setMode(o.value)}
              />
              <span className="flex flex-col gap-0.5">
                <span className="text-[15px] font-medium">{o.label}</span>
                <span className="text-[13px] text-muted">{o.desc}</span>
              </span>
            </label>
          ))}
        </div>

        {mode === "langsung" ? (
          <div className="flex flex-col gap-3 rounded-md border border-[#ffe69c] bg-[#fff3cd] p-4 text-[#664d03]">
            <p className="text-[14px] leading-relaxed">
              Nilai terbit tanpa review. Mahasiswa langsung melihat nilai,
              predikat, dan umpan balik. Nilai tetap bisa diubah setelahnya.
            </p>
            <label className="flex cursor-pointer items-start gap-2.5 text-[14px] font-medium">
              <input
                type="checkbox"
                name="confirm"
                className="mt-0.5 size-4 accent-accent"
                checked={confirmed}
                onChange={(e) => setConfirmed(e.target.checked)}
              />
              Saya mengerti nilai terbit tanpa review.
            </label>
            {blockers.map((b) => (
              <ErrorLine key={b}>{b}</ErrorLine>
            ))}
          </div>
        ) : null}

        {state?.error ? <ErrorLine>{state.error}</ErrorLine> : null}
        {state?.info ? <Notice dot="#1d7a3e">{state.info}</Notice> : null}

        <div className="flex items-center gap-3 border-t border-border pt-4">
          <Button
            type="submit"
            disabled={
              pending ||
              blockers.length > 0 ||
              (mode === "langsung" && !confirmed)
            }
          >
            {pending ? "Menyimpan..." : "Simpan mode"}
          </Button>
          <p className="text-[13px] text-muted">Berlaku untuk semua pengumpulan.</p>
        </div>
      </form>
    </Card>
  );
}
