"use server";

import { redirect } from "next/navigation";
import { q1 } from "@/db/pool";
import { DUMMY_PASSWORD_HASH, verifyPassword } from "@/lib/password";
import { endSession, roleHome, startSession } from "@/lib/session";
import { isRole } from "@/lib/token";

export type ActionState = { error?: string } | undefined;

export async function login(
  _prev: ActionState,
  formData: FormData,
): Promise<ActionState> {
  const email = String(formData.get("email") ?? "").trim();
  const password = String(formData.get("password") ?? "");
  if (!email || !password) return { error: "Email dan kata sandi wajib diisi." };

  const user = await q1<{
    id: string;
    role: string;
    status: string;
    password_hash: string | null;
  }>(
    "SELECT id, role, status, password_hash FROM users WHERE lower(email) = lower($1)",
    [email],
  );
  const passwordOk = verifyPassword(
    password,
    user?.password_hash ?? DUMMY_PASSWORD_HASH,
  );
  if (!user || !passwordOk) return { error: "Email atau kata sandi salah." };
  if (user.status !== "active") return { error: "Akun ini nonaktif." };
  if (!isRole(user.role)) return { error: "Peran tidak dikenal." };

  await startSession(user.id, user.role);
  redirect(roleHome(user.role));
}

export async function logout(): Promise<void> {
  await endSession();
  redirect("/login");
}
