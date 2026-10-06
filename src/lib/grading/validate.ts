import { z } from "zod";
import type { ModelPayload, RubricCriterion } from "./types";

export type Validation =
  | { ok: true; data: ModelPayload }
  | { ok: false; errors: string[] };

// ---------------------------------------------------------------------------
// JSON extraction: models often wrap the object in markdown fences or prose.
// ---------------------------------------------------------------------------

type Extracted =
  | { kind: "ok"; text: string }
  | { kind: "truncated" }
  | { kind: "none" };

function safeParse(text: string): boolean {
  try {
    JSON.parse(text);
    return true;
  } catch {
    return false;
  }
}

function scanFrom(s: string, start: number): { kind: "ok"; text: string } | { kind: "truncated" } | { kind: "none" } {
  if (start < 0) return { kind: "none" };
  let depth = 0;
  let inStr = false;
  let esc = false;
  for (let i = start; i < s.length; i++) {
    const ch = s[i];
    if (inStr) {
      if (esc) esc = false;
      else if (ch === "\\") esc = true;
      else if (ch === '"') inStr = false;
      continue;
    }
    if (ch === '"') inStr = true;
    else if (ch === "{") depth++;
    else if (ch === "}") {
      depth--;
      if (depth === 0) return { kind: "ok", text: s.slice(start, i + 1) };
    }
  }
  return { kind: "truncated" };
}

function extractJson(content: string): Extracted {
  const trimmed = content.trim();
  if (safeParse(trimmed)) return { kind: "ok", text: trimmed };

  for (const m of trimmed.matchAll(/```(?:json)?\s*([\s\S]*?)```/gi)) {
    const inner = m[1].trim();
    if (safeParse(inner)) return { kind: "ok", text: inner };
    const scanned = scanFrom(inner, inner.indexOf("{"));
    if (scanned.kind === "ok" && safeParse(scanned.text)) {
      return { kind: "ok", text: scanned.text };
    }
  }

  let idx = trimmed.indexOf("{");
  while (idx >= 0) {
    const scanned = scanFrom(trimmed, idx);
    if (scanned.kind === "truncated") {
      // The object opened at this "{" never closes: the response was cut off.
      return { kind: "truncated" };
    }
    if (scanned.kind === "ok" && safeParse(scanned.text)) {
      return { kind: "ok", text: scanned.text };
    }
    idx = trimmed.indexOf("{", idx + 1);
  }
  return { kind: "none" };
}

// ---------------------------------------------------------------------------
// Zod schemas
// ---------------------------------------------------------------------------

const nonEmptyTrimmed = z.string().trim().min(1);

// Models sometimes stringify numbers ("3" instead of 3).
const scoreSchema = z.preprocess((v) => {
  if (typeof v === "string" && v.trim() !== "") {
    const n = Number(v.trim());
    return Number.isNaN(n) ? v : n;
  }
  return v;
}, z.number().int().min(1).max(4));

const entrySchema = z.object({
  id: z.string(),
  score: scoreSchema,
  quote: nonEmptyTrimmed,
  comment: nonEmptyTrimmed,
});

export function parseModelResponse(
  content: string,
  rubric: RubricCriterion[],
): Validation {
  const extracted = extractJson(content);
  if (extracted.kind === "truncated") {
    return {
      ok: false,
      errors: [
        "Respons terpotong. Naikkan Max tokens pada Setelan model lalu ulangi penilaian.",
      ],
    };
  }
  if (extracted.kind === "none") {
    return { ok: false, errors: ["Balasan bukan JSON valid."] };
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(extracted.text);
  } catch {
    return { ok: false, errors: ["Balasan bukan JSON valid."] };
  }

  if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
    return { ok: false, errors: ["Balasan bukan objek JSON."] };
  }

  const obj = parsed as Record<string, unknown>;
  const errors: string[] = [];

  if (!nonEmptyTrimmed.safeParse(obj.feedback).success) {
    errors.push('Field "feedback" tidak ada atau kosong.');
  }
  if (!nonEmptyTrimmed.safeParse(obj.summary).success) {
    errors.push('Field "summary" tidak ada atau kosong.');
  }
  if (!z.array(z.unknown()).safeParse(obj.criteria).success) {
    errors.push('Field "criteria" bukan array.');
    return { ok: false, errors };
  }

  const byId = new Map<string, unknown[]>();
  for (const entry of obj.criteria as unknown[]) {
    const id =
      typeof entry === "object" && entry !== null
        ? (entry as { id?: unknown }).id
        : undefined;
    if (typeof id !== "string") {
      errors.push("Ada kriteria tanpa id.");
      continue;
    }
    const list = byId.get(id) ?? [];
    list.push(entry);
    byId.set(id, list);
  }

  const seenIds = new Set<string>();
  const clean: ModelPayload["criteria"] = [];

  for (const criterion of rubric) {
    const matches = byId.get(criterion.id) ?? [];
    if (matches.length === 0) {
      errors.push(`Kriteria "${criterion.name}" tidak ada dalam balasan.`);
      continue;
    }
    if (matches.length > 1) {
      errors.push(`Kriteria "${criterion.name}" muncul lebih dari sekali.`);
      continue;
    }
    seenIds.add(criterion.id);

    const entry = entrySchema.safeParse(matches[0]);
    if (!entry.success) {
      for (const issue of entry.error.issues) {
        const field = issue.path[0];
        if (field === "score") {
          errors.push(
            `Kriteria "${criterion.name}" punya score tidak valid (harus integer 1-4).`,
          );
        } else if (field === "quote") {
          errors.push(`Kriteria "${criterion.name}" tanpa kutipan.`);
        } else if (field === "comment") {
          errors.push(`Kriteria "${criterion.name}" tanpa komentar.`);
        } else if (field === "id") {
          errors.push("Ada kriteria tanpa id.");
        }
      }
      continue;
    }

    clean.push({
      id: criterion.id,
      score: entry.data.score,
      quote: entry.data.quote,
      comment: entry.data.comment,
    });
  }

  for (const id of byId.keys()) {
    if (!seenIds.has(id) && rubric.some((r) => r.id === id)) continue;
    if (!rubric.some((r) => r.id === id)) {
      errors.push(`Kriteria tidak dikenal dengan id "${id}".`);
    }
  }

  if (errors.length > 0) return { ok: false, errors };

  return {
    ok: true,
    data: {
      criteria: clean,
      feedback: (obj.feedback as string).trim(),
      summary: (obj.summary as string).trim(),
    },
  };
}
