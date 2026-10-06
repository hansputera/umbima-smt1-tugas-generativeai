import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { Circle } from "lucide-react";

export function StatusDot({
  label,
  color,
  icon: Icon = Circle,
  className = "",
}: {
  label: string;
  color: string;
  icon?: LucideIcon;
  className?: string;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 text-[13px] whitespace-nowrap ${className}`}
    >
      <Icon size={14} strokeWidth={2} className="shrink-0" style={{ color }} aria-hidden />
      {label}
    </span>
  );
}

export function Badge({ children }: { children: ReactNode }) {
  return (
    <span className="inline-flex items-center text-[13px] font-medium text-muted">
      {children}
    </span>
  );
}

export function Card({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`rounded-lg border border-border bg-white shadow-menu ${className}`}>
      {children}
    </div>
  );
}

export function PageHeader({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-6">
      <div className="min-w-0">
        <h1>{title}</h1>
        {description ? (
          <p className="mt-1 text-[14px] text-muted">{description}</p>
        ) : null}
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
}

export function Section({
  title,
  action,
  children,
  className = "",
}: {
  title: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`flex flex-col gap-3 ${className}`}>
      <div className="flex items-center justify-between gap-4">
        <h2>{title}</h2>
        {action}
      </div>
      {children}
    </section>
  );
}

export function EmptyState({
  message,
  action,
}: {
  message: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-lg border border-border bg-white px-4 py-5 shadow-menu">
      <p className="text-[14px] text-muted">{message}</p>
      {action}
    </div>
  );
}

export function ErrorLine({ children }: { children: ReactNode }) {
  return <p className="text-[13px] leading-snug text-danger">{children}</p>;
}

export function Notice({
  dot = "#664d03",
  children,
  className = "",
}: {
  dot?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <StatusDot
      label={String(children)}
      color={dot}
      className={`text-muted ${className}`}
    />
  );
}

export function Page({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`flex flex-col gap-6 ${className}`}>{children}</div>
  );
}
