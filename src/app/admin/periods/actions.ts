"use server";

import { revalidatePath } from "next/cache";
import { q1 } from "@/db/pool";
import { requireRole } from "@/lib/session";

export type PeriodFormState = { errors?: Record<string, string> } | undefined;
export type RowState = { error?: string } | undefined;

function str(value: FormDataEntryValue | null): string {
  return typeof value === "string" ? value.trim() : "";
}

export async function savePeriod(
  _prev: PeriodFormState,
  formData: FormData,
): Promise<PeriodFormState> {
  await requireRole("admin");

  const id = str(formData.get("id")) || null;
  const name = str(formData.get("name"));

  const errors: Record<string, string> = {};
  if (!name) errors.name = "Nama periode wajib diisi.";
  else if (name.length > 60) errors.name = "Nama periode maksimal 60 karakter.";

  if (Object.keys(errors).length === 0) {
    const existing = await q1<{ id: string }>(
      `SELECT id FROM periods WHERE lower(name) = lower($1)
         AND ($2::uuid IS NULL OR id <> $2)
       LIMIT 1`,
      [name, id],
    );
    if (existing) errors.name = "Nama periode sudah dipakai.";
  }

  if (Object.keys(errors).length > 0) return { errors };

  if (id) {
    await q1(`UPDATE periods SET name = $2 WHERE id = $1`, [id, name]);
  } else {
    await q1(`INSERT INTO periods (name) VALUES ($1)`, [name]);
  }

  revalidatePath("/admin/periods");
  revalidatePath("/admin/courses");
  return {};
}

export async function activatePeriod(formData: FormData): Promise<RowState> {
  await requireRole("admin");
  const id = str(formData.get("id"));
  if (!id) return { error: "Periode tidak ditemukan." };

  await q1(`UPDATE periods SET is_active = (id = $1)`, [id]);
  revalidatePath("/admin/periods");
  revalidatePath("/admin/courses");
  revalidatePath("/admin/placement");
  return {};
}

export async function deletePeriod(formData: FormData): Promise<RowState> {
  await requireRole("admin");
  const id = str(formData.get("id"));
  if (!id) return { error: "Periode tidak ditemukan." };

  const period = await q1<{ is_active: boolean }>(
    "SELECT is_active FROM periods WHERE id = $1",
    [id],
  );
  if (!period) return { error: "Periode tidak ditemukan." };
  if (period.is_active) {
    return { error: "Tidak bisa menghapus periode aktif. Aktifkan periode lain dulu." };
  }

  const classes = await q1<{ n: string }>(
    "SELECT count(*)::text AS n FROM courses WHERE period_id = $1",
    [id],
  );
  if (Number(classes?.n ?? 0) > 0) {
    return { error: "Periode masih punya kelas. Hapus kelasnya dulu." };
  }

  await q1("DELETE FROM periods WHERE id = $1", [id]);
  revalidatePath("/admin/periods");
  return {};
}
