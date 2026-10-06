import type { LucideIcon } from "lucide-react";
import {
  AlertTriangle,
  Circle,
  CircleCheck,
  CircleX,
  Clock,
  Pencil,
} from "lucide-react";

export type StatusKey =
  | "belum"
  | "draft"
  | "terkumpul"
  | "dinilai"
  | "perlu_review"
  | "active"
  | "inactive"
  | "archived"
  | "aktif"
  | "published"
  | "error";

const STATUS: Record<StatusKey, { label: string; color: string; Icon: LucideIcon }> = {
  belum: { label: "Belum", color: "#6a737b", Icon: Circle },
  draft: { label: "Draft", color: "#6a737b", Icon: Pencil },
  terkumpul: { label: "Terkumpul", color: "#0f6cbf", Icon: Clock },
  dinilai: { label: "Dinilai", color: "#1d7a3e", Icon: CircleCheck },
  perlu_review: { label: "Perlu review", color: "#664d03", Icon: AlertTriangle },
  active: { label: "Aktif", color: "#1d7a3e", Icon: CircleCheck },
  inactive: { label: "Nonaktif", color: "#6a737b", Icon: Circle },
  archived: { label: "Diarsipkan", color: "#6a737b", Icon: Circle },
  aktif: { label: "Aktif", color: "#1d7a3e", Icon: CircleCheck },
  published: { label: "Terbit", color: "#1d7a3e", Icon: CircleCheck },
  error: { label: "Gagal", color: "#ca3120", Icon: CircleX },
};

export function statusOf(key: StatusKey): {
  label: string;
  color: string;
  Icon: LucideIcon;
} {
  return STATUS[key] ?? STATUS.belum;
}

export function submissionStatus(
  status: string | null,
  hasPublishedGrade: boolean,
): StatusKey {
  if (!status) return "belum";
  if (status === "needs_review") return "perlu_review";
  if (status === "draft") return "draft";
  if (status === "submitted") return hasPublishedGrade ? "dinilai" : "terkumpul";
  return "belum";
}

export const ROLE_LABEL: Record<string, string> = {
  admin: "Admin",
  lecturer: "Dosen",
  student: "Mahasiswa",
};

export const TYPE_LABEL: Record<string, string> = {
  essay: "Esai",
  pg: "Pilihan ganda",
  pdf: "Unggah PDF",
  docx: "Unggah DOCX",
};

export const MODE_LABEL: Record<string, string> = {
  review: "Review dulu",
  langsung: "Langsung rilis",
};
