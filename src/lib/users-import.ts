import ExcelJS from "exceljs";
import { q } from "@/db/pool";

export const IMPORT_MAX_ROWS = 500;
export const IMPORT_MAX_BYTES = 2 * 1024 * 1024;

export type ImportRow = {
  line: number;
  name: string;
  email: string;
  role: string;
  status: string;
  error: string | null;
  skip: string | null;
};

export type ImportSummary = {
  total: number;
  importable: number;
  skipped: number;
  errors: number;
};

export type ImportPreview = ImportSummary & {
  rows: ImportRow[];
  at: number;
};

export type ImportOutcome = {
  inserted: number;
  skipped: { email: string; reason: string }[];
  errors: { line: number; message: string }[];
  total: number;
  at: number;
};

const ROLE_ALIAS: Record<string, string> = {
  admin: "admin",
  dosen: "lecturer",
  lecturer: "lecturer",
  mahasiswa: "student",
  student: "student",
};

const STATUS_ALIAS: Record<string, string> = {
  aktif: "active",
  active: "active",
  nonaktif: "inactive",
  "tidak aktif": "inactive",
  inactive: "inactive",
};

type RawRow = { name: string; email: string; role: string; status: string };

export function normalizeRow(line: number, raw: RawRow): ImportRow {
  const name = (raw.name ?? "").trim().replace(/\s+/g, " ");
  const email = (raw.email ?? "").trim().toLowerCase();
  const roleRaw = (raw.role ?? "").trim().toLowerCase();
  const statusRaw = (raw.status ?? "").trim().toLowerCase();

  let error: string | null = null;
  if (!name) {
    error = "Nama wajib diisi.";
  } else if (name.length > 120) {
    error = "Nama maksimal 120 karakter.";
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    error = "Email tidak valid.";
  }

  let role = ROLE_ALIAS[roleRaw] ?? "";
  if (!error && !role) {
    if (roleRaw === "") role = "student";
    else error = `Peran tidak valid: "${raw.role}". Gunakan Admin, Dosen, atau Mahasiswa.`;
  }

  let status = STATUS_ALIAS[statusRaw] ?? "";
  if (!error && !status) {
    if (statusRaw === "") status = "active";
    else error = `Status tidak valid: "${raw.status}". Gunakan Aktif atau Nonaktif.`;
  }

  return { line, name, email, role, status, error, skip: null };
}

export function detectInFileDups(rows: ImportRow[]): void {
  const seen = new Set<string>();
  for (const row of rows) {
    if (row.error) continue;
    if (seen.has(row.email)) row.skip = "Email kembar di file ini.";
    else seen.add(row.email);
  }
}

export async function markExistingEmails(rows: ImportRow[]): Promise<void> {
  const emails = [
    ...new Set(rows.filter((r) => !r.error && !r.skip).map((r) => r.email)),
  ];
  if (emails.length === 0) return;
  const found = await q<{ email: string }>(
    "SELECT lower(email) AS email FROM users WHERE lower(email) = ANY($1::text[])",
    [emails],
  );
  const existing = new Set(found.map((r) => r.email));
  for (const row of rows) {
    if (!row.error && !row.skip && existing.has(row.email)) {
      row.skip = "Email sudah terdaftar.";
    }
  }
}

export function summarize(rows: ImportRow[]): ImportSummary {
  let importable = 0;
  let skipped = 0;
  let errors = 0;
  for (const row of rows) {
    if (row.error) errors++;
    else if (row.skip) skipped++;
    else importable++;
  }
  return { total: rows.length, importable, skipped, errors };
}

export function sanitizeClientRows(input: unknown): ImportRow[] | null {
  if (!Array.isArray(input) || input.length === 0) return null;
  if (input.length > IMPORT_MAX_ROWS) return null;
  const rows: ImportRow[] = [];
  for (let i = 0; i < input.length; i++) {
    const item: unknown = input[i];
    if (typeof item !== "object" || item === null) return null;
    const o = item as Record<string, unknown>;
    if (
      typeof o.name !== "string" ||
      typeof o.email !== "string" ||
      typeof o.role !== "string" ||
      typeof o.status !== "string"
    ) {
      return null;
    }
    rows.push(
      normalizeRow(typeof o.line === "number" ? o.line : i + 1, {
        name: o.name,
        email: o.email,
        role: o.role,
        status: o.status,
      }),
    );
  }
  detectInFileDups(rows);
  return rows;
}

function cellText(value: ExcelJS.CellValue): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  if (value instanceof Date) return value.toISOString();
  if (typeof value === "object") {
    if ("richText" in value && Array.isArray(value.richText)) {
      return value.richText.map((t) => t.text).join("");
    }
    if ("text" in value && typeof value.text === "string") return value.text;
    if ("result" in value && value.result !== null && value.result !== undefined) {
      return String(value.result);
    }
    if ("error" in value) return "";
  }
  return "";
}

function headerKey(text: string): string {
  const v = text.trim().toLowerCase();
  if (v === "nama" || v === "nama lengkap" || v === "name") return "name";
  if (v === "email" || v === "e-mail" || v === "surel") return "email";
  if (v === "peran" || v === "role") return "role";
  if (v === "status") return "status";
  return "";
}

export async function parseUsersWorkbook(
  data: Buffer,
): Promise<{ rows: ImportRow[]; fileErrors: string[] }> {
  const workbook = new ExcelJS.Workbook();
  try {
    await workbook.xlsx.load(new Uint8Array(data).buffer);
  } catch {
    return {
      rows: [],
      fileErrors: ["Berkas tidak valid. Pastikan berkas berformat .xlsx."],
    };
  }
  const sheet = workbook.worksheets[0];
  if (!sheet || sheet.rowCount < 2) {
    return {
      rows: [],
      fileErrors: ["Berkas tidak berisi data. Gunakan template yang disediakan."],
    };
  }

  let headerAt = -1;
  let cols: { name: number; email: number; role: number; status: number } | null =
    null;
  for (let r = 1; r <= Math.min(sheet.rowCount, 20); r++) {
    const found = { name: -1, email: -1, role: -1, status: -1 };
    sheet.getRow(r).eachCell({ includeEmpty: false }, (cell, col) => {
      const key = headerKey(cellText(cell.value));
      if (key === "name") found.name = col;
      else if (key === "email") found.email = col;
      else if (key === "role") found.role = col;
      else if (key === "status") found.status = col;
    });
    if (found.name !== -1 && found.email !== -1) {
      headerAt = r;
      cols = found;
      break;
    }
  }
  if (!cols || headerAt === -1) {
    return {
      rows: [],
      fileErrors: [
        "Baris judul tidak ditemukan. Kolom Nama dan Email wajib ada. Gunakan template yang disediakan.",
      ],
    };
  }

  const rows: ImportRow[] = [];
  const fileErrors: string[] = [];
  for (let r = headerAt + 1; r <= sheet.rowCount; r++) {
    if (rows.length >= IMPORT_MAX_ROWS) {
      fileErrors.push(
        `Maksimal ${IMPORT_MAX_ROWS} baris per impor. Baris berikutnya tidak dibaca.`,
      );
      break;
    }
    const row = sheet.getRow(r);
    const raw: RawRow = {
      name: cellText(row.getCell(cols.name).value),
      email: cellText(row.getCell(cols.email).value),
      role: cols.role > 0 ? cellText(row.getCell(cols.role).value) : "",
      status: cols.status > 0 ? cellText(row.getCell(cols.status).value) : "",
    };
    if (!raw.name.trim() && !raw.email.trim()) continue;
    rows.push(normalizeRow(r, raw));
  }
  if (rows.length === 0) fileErrors.push("Tidak ada baris data.");
  detectInFileDups(rows);
  return { rows, fileErrors };
}
