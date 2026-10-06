import type { ReactNode } from "react";
import Link from "next/link";
import { statusOf, type StatusKey } from "@/lib/status";
import { StatusDot } from "@/components/ui/misc";

export function CourseCard({
  href,
  code,
  name,
  semester,
  sks,
  statusKey,
  meta,
  footer,
}: {
  href: string;
  code: string;
  name: string;
  semester: number;
  sks: number;
  statusKey: StatusKey;
  meta?: string;
  footer?: ReactNode;
}) {
  const s = statusOf(statusKey);
  return (
    <div className="group relative flex flex-col overflow-hidden rounded-lg border border-border bg-white transition-colors hover:border-border-hover">
      <div className="aspect-[16/9] bg-band" aria-hidden />
      <Link
        href={href}
        className="absolute inset-0 z-10 rounded-lg focus-visible:outline-2 focus-visible:outline-accent"
      >
        <span className="sr-only">
          {code} — {name}
        </span>
      </Link>
      <div className="flex flex-1 flex-col gap-1.5 px-5 py-4">
        <div className="flex items-center justify-between gap-3">
          <span className="text-[13px] font-medium tracking-wide text-muted uppercase">
            {code}
          </span>
          <StatusDot label={s.label} color={s.color} icon={s.Icon} />
        </div>
        <span className="text-[15px] leading-snug font-semibold text-ink">
          {name}
        </span>
        <span className="text-[13px] text-muted">
          Semester {semester} · {sks} SKS
          {meta ? ` · ${meta}` : ""}
        </span>
        {footer ? <div className="mt-auto pt-3">{footer}</div> : null}
      </div>
    </div>
  );
}

export function CourseProgress({
  done,
  total,
  label = "Tugas dinilai",
}: {
  done: number;
  total: number;
  label?: string;
}) {
  const pct = total === 0 ? 0 : Math.round((done / total) * 100);
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center justify-between gap-3 text-[13px]">
        <span className="text-muted">{label}</span>
        <span className="font-medium text-ink">
          {done}/{total}
        </span>
      </div>
      <div className="h-1 overflow-hidden rounded-full bg-border">
        <div
          className="h-full rounded-full bg-accent"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
