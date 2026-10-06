"use server";

import { revalidatePath } from "next/cache";
import { q, q1 } from "@/db/pool";
import { requireLecturerAssignment } from "@/lib/lecturer";
import {
  getSettings,
  isEmbeddingConfigured,
  isModelConfigured,
} from "@/lib/settings";

export type RubricSaveState = {
  error?: string;
  info?: string;
  criteria?: {
    id: string;
    name: string;
    weight: number;
    level_1: string;
    level_2: string;
    level_3: string;
    level_4: string;
    prompt_notes: string;
  }[];
} | undefined;

export type ModeSaveState = {
  error?: string;
  info?: string;
} | undefined;

type CriterionInput = {
  id?: string | null;
  name: string;
  weight: number;
  level_1: string;
  level_2: string;
  level_3: string;
  level_4: string;
  prompt_notes: string;
};

const UUID =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function str(value: FormDataEntryValue | null): string {
  return typeof value === "string" ? value.trim() : "";
}

export async function saveRubric(
  _prev: RubricSaveState,
  formData: FormData,
): Promise<RubricSaveState> {
  const assignmentId = str(formData.get("assignment_id"));
  const { assignment } = await requireLecturerAssignment(assignmentId);

  let rows: CriterionInput[] = [];
  try {
    const parsed = JSON.parse(str(formData.get("criteria")) || "[]");
    if (Array.isArray(parsed)) rows = parsed as CriterionInput[];
  } catch {
    return { error: "Data rubrik tidak valid." };
  }

  if (rows.length === 0) return { error: "Tambahkan minimal satu kriteria." };

  let total = 0;
  for (const row of rows) {
    if (!row.name || !String(row.name).trim()) {
      return { error: "Nama kriteria wajib diisi." };
    }
    const weight = Number(row.weight);
    if (!Number.isInteger(weight) || weight < 1 || weight > 100) {
      return { error: `Bobot "${row.name}" tidak valid.` };
    }
    total += weight;
  }
  if (total !== 100) {
    return { error: "Bobot harus berjumlah 100." };
  }

  const existing = await q<{ id: string }>(
    "SELECT id FROM rubric_criteria WHERE assignment_id = $1",
    [assignment.id],
  );
  const keepIds = new Set(
    rows
      .map((r) => (r.id && UUID.test(r.id) ? r.id : null))
      .filter((id): id is string => Boolean(id)),
  );

  for (const row of existing) {
    if (!keepIds.has(row.id)) {
      await q1("DELETE FROM rubric_criteria WHERE id = $1", [row.id]);
    }
  }

  for (let i = 0; i < rows.length; i++) {
    const r = rows[i];
    const weight = Number(r.weight);
    const values = [
      assignment.id,
      i,
      String(r.name).trim(),
      weight,
      r.level_1 ?? "",
      r.level_2 ?? "",
      r.level_3 ?? "",
      r.level_4 ?? "",
      r.prompt_notes ?? "",
    ];
    if (r.id && UUID.test(r.id)) {
      await q1(
        `UPDATE rubric_criteria
         SET position = $3, name = $4, weight = $5,
             level_1 = $6, level_2 = $7, level_3 = $8, level_4 = $9,
             prompt_notes = $10
         WHERE id = $1 AND assignment_id = $2`,
        [r.id, assignment.id, i, String(r.name).trim(), weight,
         r.level_1 ?? "", r.level_2 ?? "", r.level_3 ?? "", r.level_4 ?? "",
         r.prompt_notes ?? ""],
      );
    } else {
      await q1(
        `INSERT INTO rubric_criteria
           (assignment_id, position, name, weight, level_1, level_2, level_3, level_4, prompt_notes)
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)`,
        values,
      );
    }
  }

  const saved = await q<{
    id: string;
    name: string;
    weight: number;
    level_1: string;
    level_2: string;
    level_3: string;
    level_4: string;
    prompt_notes: string;
  }>(
    `SELECT id, name, weight, level_1, level_2, level_3, level_4, prompt_notes
     FROM rubric_criteria WHERE assignment_id = $1 ORDER BY position, name`,
    [assignment.id],
  );

  revalidatePath(`/lecturer/assignments/${assignment.id}`);
  return { info: "Rubrik disimpan.", criteria: saved };
}

export async function saveReleaseMode(
  _prev: ModeSaveState,
  formData: FormData,
): Promise<ModeSaveState> {
  const assignmentId = str(formData.get("assignment_id"));
  const { assignment } = await requireLecturerAssignment(assignmentId);

  const mode = str(formData.get("mode"));
  if (mode !== "review" && mode !== "langsung") {
    return { error: "Mode tidak dikenal." };
  }

  if (mode === "langsung") {
    if (!formData.has("confirm")) {
      return {
        error: 'Centang "Saya mengerti nilai terbit tanpa review."',
      };
    }

    const sum = await q1<{ total: string }>(
      "SELECT COALESCE(SUM(weight), 0)::text AS total FROM rubric_criteria WHERE assignment_id = $1",
      [assignment.id],
    );
    if (Number(sum?.total ?? 0) !== 100) {
      return { error: "Rubrik harus berjumlah 100." };
    }

    const settings = await getSettings();
    if (!isModelConfigured(settings)) {
      return { error: "Model belum disetel." };
    }
    if (
      (assignment.type === "pdf" || assignment.type === "docx") &&
      !isEmbeddingConfigured(settings)
    ) {
      return { error: "Embedding belum disetel." };
    }
  }

  await q1("UPDATE assignments SET release_mode = $2 WHERE id = $1", [
    assignment.id,
    mode,
  ]);

  revalidatePath(`/lecturer/assignments/${assignment.id}`);
  return mode === "langsung"
    ? { info: "Mode langsun rilis aktif." }
    : { info: "Mode review dulu aktif." };
}
