import { createHmac, timingSafeEqual } from "crypto";

export type Role = "admin" | "lecturer" | "student";

export const SESSION_COOKIE = "nilai_sid";

const SECRET = () => process.env.SESSION_SECRET ?? "nilai-dev-secret";

export function isRole(value: unknown): value is Role {
  return value === "admin" || value === "lecturer" || value === "student";
}

function sign(payload: string): string {
  return createHmac("sha256", SECRET()).update(payload).digest("base64url");
}

export function signToken(userId: string, role: Role): string {
  const payload = `${userId}.${role}`;
  return `${payload}.${sign(payload)}`;
}

export function verifyToken(
  token: string | undefined | null,
): { userId: string; role: Role } | null {
  if (!token) return null;
  const idx = token.lastIndexOf(".");
  if (idx <= 0) return null;
  const payload = token.slice(0, idx);
  const given = token.slice(idx + 1);
  const expected = sign(payload);
  const a = Buffer.from(given);
  const b = Buffer.from(expected);
  if (a.length !== b.length || !timingSafeEqual(a, b)) return null;
  const dot = payload.indexOf(".");
  if (dot <= 0) return null;
  const userId = payload.slice(0, dot);
  const role = payload.slice(dot + 1);
  if (!isRole(role)) return null;
  return { userId, role };
}

export function roleHome(role: Role): string {
  if (role === "admin") return "/admin";
  if (role === "lecturer") return "/lecturer/home";
  return "/student/home";
}
