"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const TABS: { href: string; label: string; exact?: boolean }[] = [
  { href: "/admin", label: "Ringkasan", exact: true },
  { href: "/admin/users", label: "Pengguna" },
  { href: "/admin/courses", label: "Mata kuliah" },
  { href: "/admin/periods", label: "Periode" },
  { href: "/admin/placement", label: "Penempatan" },
  { href: "/admin/branding", label: "Aplikasi" },
  { href: "/admin/settings", label: "Setelan model" },
];

export function AdminTabs() {
  const pathname = usePathname();
  return (
    <nav
      aria-label="Tab administrasi"
      className="mb-6 flex gap-1 overflow-x-auto border-b border-border"
    >
      {TABS.map((tab) => {
        const active = tab.exact
          ? pathname === tab.href
          : pathname === tab.href || pathname.startsWith(`${tab.href}/`);
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
