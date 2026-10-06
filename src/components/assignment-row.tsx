import Link from "next/link";
import {
  ArrowRight,
  FileDown,
  FileUp,
  ListChecks,
  PenLine,
  type LucideIcon,
} from "lucide-react";
import { MODE_LABEL, TYPE_LABEL, statusOf, type StatusKey } from "@/lib/status";
import { StatusDot } from "@/components/ui/misc";

const TYPE_ICON: Record<string, LucideIcon> = {
  essay: PenLine,
  pg: ListChecks,
  pdf: FileDown,
  docx: FileUp,
};

export function AssignmentRow({
  href,
  title,
  type,
  releaseMode,
  statusKey,
  nilai,
  action,
  subtitle,
}: {
  href: string;
  title: string;
  type: string;
  releaseMode: string;
  statusKey: StatusKey;
  nilai?: string | null;
  action?: string;
  subtitle?: string;
}) {
  const Icon = TYPE_ICON[type] ?? PenLine;
  const s = statusOf(statusKey);
  return (
    <Link
      href={href}
      className="group flex flex-wrap items-center gap-4 rounded-lg border border-border bg-white px-4 py-3.5 transition duration-[220ms] ease-in-out hover:border-accent hover:shadow-menu"
    >
      <span className="flex size-9 shrink-0 items-center justify-center rounded-md border border-border text-muted">
        <Icon size={16} strokeWidth={1.5} aria-hidden />
      </span>
      <span className="flex min-w-0 flex-col">
        <span className="truncate text-[15px] font-medium">{title}</span>
        <span className="truncate text-[13px] text-muted">
          {subtitle ?? `${TYPE_LABEL[type] ?? type} · ${MODE_LABEL[releaseMode] ?? releaseMode}`}
        </span>
      </span>
      <span className="ml-auto flex items-center gap-4">
        <StatusDot label={s.label} color={s.color} icon={s.Icon} />
        <span className="w-16 text-right text-[15px] font-medium">
          {nilai ?? "—"}
        </span>
        <span
          className="flex size-8 items-center justify-center text-muted transition-transform group-hover:translate-x-1.5 group-hover:text-ink"
          aria-hidden
        >
          <ArrowRight size={16} strokeWidth={1.5} />
        </span>
      </span>
      {action ? (
        <span className="sr-only">{action}</span>
      ) : null}
    </Link>
  );
}
