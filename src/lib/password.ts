import { randomBytes, scryptSync, timingSafeEqual } from "crypto";

const N = 16384;
const R = 8;
const P = 1;
const KEY_LEN = 64;

export const DEFAULT_PASSWORD = "password123";

export function hashPassword(password: string): string {
  const salt = randomBytes(16).toString("hex");
  const hash = scryptSync(password, salt, KEY_LEN, { N, r: R, p: P }).toString(
    "hex",
  );
  return `scrypt$${N}$${R}$${P}$${salt}$${hash}`;
}

export function verifyPassword(
  password: string,
  stored: string | null,
): boolean {
  if (!stored) return false;
  const parts = stored.split("$");
  if (parts.length !== 6 || parts[0] !== "scrypt") return false;
  const [, n, r, p, salt, expectedHex] = parts;
  const expected = Buffer.from(expectedHex, "hex");
  if (expected.length === 0) return false;
  let derived: Buffer;
  try {
    derived = scryptSync(password, salt, expected.length, {
      N: Number(n),
      r: Number(r),
      p: Number(p),
    });
  } catch {
    return false;
  }
  if (derived.length !== expected.length) return false;
  return timingSafeEqual(derived, expected);
}

// Checked when an email has no account, so "unknown email" and "wrong
// password" take the same time.
export const DUMMY_PASSWORD_HASH = hashPassword(randomBytes(16).toString("hex"));
