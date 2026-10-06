"use client";

import Link from "next/link";
import { ChevronRight } from "lucide-react";
import { useBranding } from "@/components/branding-context";

export type Crumb = { label: string; href?: string };

export function Breadcrumb({
  items,
  rootHref,
}: {
  items: Crumb[];
  rootHref?: string;
}) {
  const { appName } = useBranding();
  const all: Crumb[] = rootHref
    ? [{ label: appName, href: rootHref }, ...items]
    : items;
  return (
    <nav
      aria-label="Navigasi halaman"
      className="flex flex-wrap items-center gap-x-1.5 gap-y-1 text-[14px] text-muted"
    >
      {all.map((item, i) => {
        const last = i === all.length - 1;
        return (
          <span key={`${item.label}-${i}`} className="flex items-center gap-1.5">
            {i > 0 ? (
              <ChevronRight
                size={13}
                strokeWidth={1.5}
                className="text-faint"
                aria-hidden
              />
            ) : null}
            {item.href && !last ? (
              <Link
                href={item.href}
                className="underline-offset-2 hover:text-link hover:underline"
              >
                {item.label}
              </Link>
            ) : (
              <span className={last ? "text-ink" : undefined}>{item.label}</span>
            )}
          </span>
        );
      })}
    </nav>
  );
}
