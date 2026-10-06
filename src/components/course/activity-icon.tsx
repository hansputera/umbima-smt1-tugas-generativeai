import {
  BookOpen,
  FileDown,
  FileUp,
  ListChecks,
  PenLine,
  type LucideIcon,
} from "lucide-react";

const ACTIVITY: Record<string, { Icon: LucideIcon; color: string }> = {
  materi: { Icon: BookOpen, color: "#0f6cbf" },
  essay: { Icon: PenLine, color: "#d9534f" },
  pg: { Icon: ListChecks, color: "#f0ad4e" },
  pdf: { Icon: FileDown, color: "#5cb85c" },
  docx: { Icon: FileUp, color: "#5bc0de" },
};

export function activityMeta(type: string): { Icon: LucideIcon; color: string } {
  return ACTIVITY[type] ?? ACTIVITY.materi;
}

export function ActivityIcon({
  type,
  size = 40,
}: {
  type: string;
  size?: number;
}) {
  const { Icon, color } = activityMeta(type);
  return (
    <span
      className="grid shrink-0 place-items-center rounded-[4px] text-white"
      style={{ width: size, height: size, background: color }}
      aria-hidden
    >
      <Icon size={Math.round(size * 0.45)} strokeWidth={2} />
    </span>
  );
}
