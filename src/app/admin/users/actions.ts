"use server";

import { revalidatePath } from "next/cache";
import { q1 } from "@/db/pool";
import { DEFAULT_PASSWORD, hashPassword } from "@/lib/password";
import { requireRole } from "@/lib/session";

export type UserFormState = { errors?: Record<string, string> } | undefined;
export type ToggleState = { error?: string } | undefined;

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
