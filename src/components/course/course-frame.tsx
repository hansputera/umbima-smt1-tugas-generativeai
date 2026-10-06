"use client";

import { useState, type ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { PanelLeftClose, PanelLeftOpen } from "lucide-react";
import { ActivityIcon } from "./activity-icon";

export type IndexItem = {
  id: string;
  title: string;
  type: string;
  href: string;
};

export type IndexTopic = {
  id: string;
  week: number;
  title: string;
  href: string;
  items: IndexItem[];
};

export type CourseTab = {
  href: string;
  label: string;
  exact?: boolean;
  activePrefixes?: string[];
};

function tabActive(pathname: string, tab: CourseTab): boolean {
  if (tab.activePrefixes) {
    if (pathname === tab.href) return true;
    return tab.activePrefixes.some(
      (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
    );
  }
  if (tab.exact) return pathname === tab.href;
  return pathname === tab.href || pathname.startsWith(`${tab.href}/`);
}

function TabBar({ tabs }: { tabs: CourseTab[] }) {
  const pathname = usePathname();
  return (
    <nav className="flex gap-1 overflow-x-auto border-b border-border">
      {tabs.map((tab) => {
        const active = tabActive(pathname, tab);
        return (
          <Link
            key={tab.href}
            href={tab.href}
            className={`-mb-px flex shrink-0 items-center border-b-[3px] px-3 py-2.5 text-[14px] transition-colors ${
              active
                ? "border-accent font-medium text-ink"
                : "border-transparent text-muted hover:text-ink"
            }`}
          >
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}

export function CourseFrame({
  courseLabel,
  courseHref,
  index,
  activeTopicId,
  title,
  action,
  tabs,
  blocks,
  children,
}: {
  courseLabel: string;
  courseHref: string;
  index: IndexTopic[];
  activeTopicId?: string;
  title: ReactNode;
  action?: ReactNode;
  tabs: CourseTab[];
  blocks?: ReactNode;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(true);

  return (
    <div className="flex flex-col gap-5 xl:flex-row xl:items-start xl:gap-6">
      {open ? (
        <aside className="w-full shrink-0 self-stretch rounded-lg border border-border bg-white xl:sticky xl:top-[76px] xl:w-[285px] xl:self-start xl:border-r xl:border-b">
          <div className="flex items-center justify-between border-b border-border px-4 py-3">
            <span className="label">Indeks kursus</span>
            <button
              type="button"
              onClick={() => setOpen(false)}
              aria-label="Sembunyikan indeks kursus"
              title="Sembunyikan indeks kursus"
              className="cursor-pointer rounded-md p-1 text-muted transition-colors hover:bg-canvas hover:text-ink"
            >
              <PanelLeftClose size={16} strokeWidth={1.75} aria-hidden />
            </button>
          </div>
          <nav className="flex flex-col gap-0.5 overflow-y-auto p-2">
            <Link
              href={courseHref}
              className="rounded px-2 py-1.5 text-[14px] font-semibold text-ink hover:bg-canvas"
            >
              {courseLabel}
            </Link>
            {index.map((topic) => {
              const active = topic.id === activeTopicId;
              return (
                <div key={topic.id}>
                  <Link
                    href={topic.href}
                    className={`block truncate rounded border-l-[3px] px-2 py-1.5 text-[14px] transition-colors ${
                      active
                        ? "border-accent bg-accent-soft font-medium text-ink"
                        : "border-transparent text-ink hover:bg-canvas"
                    }`}
                    title={`Pertemuan ${topic.week}: ${topic.title}`}
                  >
                    Pertemuan {topic.week}: {topic.title}
                  </Link>
                  {topic.items.map((item) => (
                    <Link
                      key={item.id}
                      href={item.href}
                      className="flex items-center gap-2 border-l-[3px] border-transparent py-1 pl-6 pr-2 text-[13px] text-muted transition-colors hover:text-ink"
                    >
                      <ActivityIcon type={item.type} size={18} />
                      <span className="truncate">{item.title}</span>
                    </Link>
                  ))}
                </div>
              );
            })}
            {index.length === 0 ? (
              <p className="px-2 py-1.5 text-[13px] text-muted">
                Belum ada pertemuan.
              </p>
            ) : null}
          </nav>
        </aside>
      ) : null}

      <div className="flex min-w-0 flex-1 flex-col gap-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex min-w-0 items-start gap-2">
            {!open ? (
              <button
                type="button"
                onClick={() => setOpen(true)}
                aria-label="Tampilkan indeks kursus"
                title="Tampilkan indeks kursus"
                className="mt-1.5 cursor-pointer rounded-md border border-border bg-white p-1.5 text-muted transition-colors hover:bg-canvas hover:text-ink"
              >
                <PanelLeftOpen size={16} strokeWidth={1.75} aria-hidden />
              </button>
            ) : null}
            <div className="min-w-0">{title}</div>
          </div>
          {action ? <div className="shrink-0">{action}</div> : null}
        </div>

        <TabBar tabs={tabs} />

        <div className="flex flex-col gap-6">{children}</div>
      </div>

      {blocks ? (
        <aside className="flex w-full shrink-0 flex-col gap-4 xl:w-[315px]">
          {blocks}
        </aside>
      ) : null}
    </div>
  );
}
