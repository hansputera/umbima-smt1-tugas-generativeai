"use server";

import { revalidatePath } from "next/cache";
import { q, q1 } from "@/db/pool";
import { DEFAULT_PASSWORD, hashPassword } from "@/lib/password";
import { requireRole } from "@/lib/session";
import {
  IMPORT_MAX_BYTES,
  markExistingEmails,
  parseUsersWorkbook,
  sanitizeClientRows,
  summarize,
  type ImportOutcome,
  type ImportPreview,
} from "@/lib/users-import";

export type UserFormState = { errors?: Record<string, string> } | undefined;
export type ToggleState = { error?: string } | undefined;
export type PreviewState =
  | { error?: string; fileErrors?: string[]; preview?: ImportPreview }
  | undefined;
export type ConfirmState = { error?: string; result?: ImportOutcome } | undefined;

const ROLES = ["admin", "lecturer", "student"];
const STATUSES = ["active", "inactive"];

function str(value: FormDataEntryValue | null): string {
  return typeof value === "string" ? value.trim() : "";
}

export async function saveUser(
  _prev: UserFormState,
  formData: FormData,
): Promise<UserFormState> {
  await requireRole("admin");

  const id = str(formData.get("id")) || null;
  const name = str(formData.get("name"));
  const email = str(formData.get("email")).toLowerCase();
  const role = str(formData.get("role"));
  const status = str(formData.get("status"));

  const errors: Record<string, string> = {};
  if (!name) errors.name = "Nama wajib diisi.";
  if (!email) {
    errors.email = "Email wajib diisi.";
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    errors.email = "Email tidak valid.";
  }
  if (!ROLES.includes(role)) errors.role = "Peran tidak valid.";
  if (!STATUSES.includes(status)) errors.status = "Status tidak valid.";

  if (Object.keys(errors).length === 0) {
    const existing = await q1<{ id: string }>(
      `SELECT id FROM users WHERE lower(email) = lower($1)
         AND ($2::uuid IS NULL OR id <> $2)
       LIMIT 1`,
      [email, id],
    );
    if (existing) errors.email = "Email sudah dipakai.";
  }

  if (Object.keys(errors).length > 0) return { errors };

  if (id) {
    await q1(
      `UPDATE users SET name = $2, email = $3, role = $4, status = $5 WHERE id = $1`,
      [id, name, email, role, status],
    );
  } else {
    await q1(
      `INSERT INTO users (name, email, role, status, password_hash)
       VALUES ($1, $2, $3, $4, $5)`,
      [name, email, role, status, hashPassword(DEFAULT_PASSWORD)],
    );
  }

  revalidatePath("/admin/users");
  revalidatePath("/admin");
  return {};
}

export async function toggleUserStatus(
  formData: FormData,
): Promise<ToggleState> {
  const admin = await requireRole("admin");
  const id = str(formData.get("id"));
  if (!id) return { error: "Pengguna tidak ditemukan." };
  if (id === admin.id) return { error: "Tidak bisa menonaktifkan akun sendiri." };

  await q1(
    `UPDATE users SET status = CASE WHEN status = 'active' THEN 'inactive' ELSE 'active' END
     WHERE id = $1`,
    [id],
  );
  revalidatePath("/admin/users");
  revalidatePath("/admin");
  return {};
}

export async function previewUsersImport(
  _prev: PreviewState,
  formData: FormData,
): Promise<PreviewState> {
  await requireRole("admin");

  const file = formData.get("file");
  if (!(file instanceof File) || file.size === 0 || file.name.trim() === "") {
    return { error: "Pilih berkas .xlsx terlebih dahulu." };
  }
  if (!file.name.toLowerCase().endsWith(".xlsx")) {
    return { error: "Format berkas harus .xlsx." };
  }
  if (file.size > IMPORT_MAX_BYTES) {
    return { error: "Ukuran berkas maksimal 2 MB." };
  }

  const buf = Buffer.from(await file.arrayBuffer());
  if (buf.length < 4 || buf[0] !== 0x50 || buf[1] !== 0x4b) {
    return { error: "Berkas bukan file Excel yang valid." };
  }

  const { rows, fileErrors } = await parseUsersWorkbook(buf);
  if (rows.length === 0) {
    return { fileErrors: fileErrors.length ? fileErrors : ["Tidak ada baris data."] };
  }
  await markExistingEmails(rows);
  return {
    preview: { ...summarize(rows), rows, at: Date.now() },
    fileErrors: fileErrors.length ? fileErrors : undefined,
  };
}

export async function confirmUsersImport(
  _prev: ConfirmState,
  formData: FormData,
): Promise<ConfirmState> {
  await requireRole("admin");

  const raw = str(formData.get("rows"));
  let parsed: unknown = null;
  try {
    parsed = JSON.parse(raw);
  } catch {
    parsed = null;
  }
  const rows = sanitizeClientRows(parsed);
  if (!rows) {
    return { error: "Impor tidak valid atau kedaluwarsa. Unggah ulang berkas." };
  }
  await markExistingEmails(rows);

  const skipped: { email: string; reason: string }[] = [];
  const errors: { line: number; message: string }[] = [];
  const ready: typeof rows = [];
  for (const row of rows) {
    if (row.error) errors.push({ line: row.line, message: row.error });
    else if (row.skip) skipped.push({ email: row.email, reason: row.skip });
    else ready.push(row);
  }

  let inserted = 0;
  if (ready.length > 0) {
    const hash = hashPassword(DEFAULT_PASSWORD);
    const insertedRows = await q<{ email: string }>(
      `INSERT INTO users (name, email, role, status, password_hash)
       SELECT u.name, u.email, u.role, u.status, $1
       FROM unnest($2::text[], $3::text[], $4::text[], $5::text[])
         AS u(name, email, role, status)
       ON CONFLICT (email) DO NOTHING
       RETURNING lower(email) AS email`,
      [
        hash,
        ready.map((r) => r.name),
        ready.map((r) => r.email),
        ready.map((r) => r.role),
        ready.map((r) => r.status),
      ],
    );
    const insertedSet = new Set(insertedRows.map((r) => r.email));
    inserted = insertedSet.size;
    for (const row of ready) {
      if (!insertedSet.has(row.email)) {
        skipped.push({ email: row.email, reason: "Email sudah terdaftar." });
      }
    }
  }

  revalidatePath("/admin/users");
  revalidatePath("/admin");
  return {
    result: { inserted, skipped, errors, total: rows.length, at: Date.now() },
  };
}
