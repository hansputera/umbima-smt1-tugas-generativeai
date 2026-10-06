import Link from "next/link";
import { fmtDate, fmtNilai } from "@/lib/format";
import { TYPE_LABEL } from "@/lib/status";
import type { RecentGradeItem, UpcomingItem } from "@/lib/course-view";
import { ActivityIcon } from "./activity-icon";

export function Block({
  label,
  empty,
  children,
}: {
  label: string;
  empty: string;
  children?: React.ReactNode;
}) {
  return (
    <section className="overflow-hidden rounded-lg border border-border bg-white">
      <div className="label border-b border-border bg-canvas px-4 py-2.5">
        {label}
      </div>
      <div className="flex flex-col">
        {children ?? <p className="px-4 py-4 text-[13px] text-muted">{empty}</p>}
      </div>
    </section>
  );
}

export function UpcomingList({ items }: { items: UpcomingItem[] }) {
  if (items.length === 0) {
    return <Block label="Yang akan datang" empty="Tidak ada tenggat mendatang." />;
  }
  return (
    <Block label="Yang akan datang" empty="Tidak ada tenggat mendatang.">
      {items.map((item) => (
        <Link
          key={item.id}
          href={item.href}
          className="flex items-center gap-3 border-b border-border px-4 py-3 last:border-b-0 transition-colors hover:bg-canvas"
        >
          <ActivityIcon type={item.type} size={32} />
          <span className="flex min-w-0 flex-col">
            <span className="truncate text-[14px] font-medium text-ink">
              {item.title}
            </span>
            <span className="text-[13px] text-muted">
              {TYPE_LABEL[item.type] ?? item.type} · Tenggat {fmtDate(item.due_at)}
            </span>
          </span>
        </Link>
      ))}
    </Block>
  );
}

export function RecentGrades({ items }: { items: RecentGradeItem[] }) {
  if (items.length === 0) {
    return <Block label="Nilai terbaru" empty="Belum ada nilai terbit." />;
  }
  return (
    <Block label="Nilai terbaru" empty="Belum ada nilai terbit.">
      {items.map((item) => (
        <Link
          key={`${item.title}-${item.published_at}`}
          href={item.href}
          className="flex items-center justify-between gap-3 border-b border-border px-4 py-3 last:border-b-0 transition-colors hover:bg-canvas"
        >
          <span className="flex min-w-0 flex-col">
            <span className="truncate text-[14px] text-ink">{item.title}</span>
            <span className="text-[13px] text-muted">
              {fmtDate(item.published_at)}
            </span>
          </span>
          <span className="shrink-0 text-[14px] font-semibold text-ink">
            {fmtNilai(item.nilai)} · {item.predikat}
          </span>
        </Link>
      ))}
    </Block>
  );
}
