import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { q1 } from "@/db/pool";
import {
  SESSION_COOKIE,
  isRole,
  roleHome,
  signToken,
  verifyToken,
  type Role,
} from "./token";

export type SessionUser = {
  id: string;
  name: string;
  email: string;
  role: Role;
  status: string;
};

export async function getSession(): Promise<SessionUser | null> {
  const store = await cookies();
  const token = store.get(SESSION_COOKIE)?.value;
  const parsed = verifyToken(token);
  if (!parsed) return null;
  const user = await q1<SessionUser>(
    "SELECT id, name, email, role, status FROM users WHERE id = $1",
    [parsed.userId],
  );
  if (!user || user.status !== "active" || !isRole(user.role)) return null;
  return user;
}

export async function requireRole(...roles: Role[]): Promise<SessionUser> {
  const user = await getSession();
  if (!user) redirect("/login");
  if (!roles.includes(user.role)) redirect(roleHome(user.role));
  return user;
}

export async function startSession(userId: string, role: Role): Promise<void> {
  const store = await cookies();
  store.set(SESSION_COOKIE, signToken(userId, role), {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 24 * 7,
  });
}

export async function endSession(): Promise<void> {
  const store = await cookies();
  store.delete(SESSION_COOKIE);
}

export { roleHome };
