"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Bell, ChevronDown, LogOut } from "lucide-react";
import { logout } from "@/lib/actions/auth";

export type NavItem = {
  href: string;
  label: string;
  exact?: boolean;
};

function isActive(pathname: string, item: NavItem): boolean {
  if (item.exact) return pathname === item.href;
  return pathname === item.href || pathname.startsWith(`${item.href}/`);
}

export function Navbar({
  items,
  homeHref,
  userName,
  roleLabel,
}: {
  items: NavItem[];
  homeHref: string;
  userName: string;
  roleLabel: string;
}) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onDown(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [open]);

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-white">
      <div className="flex min-h-[60px] flex-wrap items-center gap-x-5 gap-y-0 px-6">
        <Link href={homeHref} className="flex shrink-0 items-center gap-2 py-3">
          <span
            className="grid size-7 place-items-center rounded-[4px] bg-accent text-[14px] font-bold text-white"
            aria-hidden
          >
            N
          </span>
          <span className="text-[17px] leading-none font-semibold text-ink">
            Nilai
          </span>
        </Link>

        <nav className="flex items-center">
          {items.map((item) => {
            const active = isActive(pathname, item);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center border-b-[3px] px-3 py-4 text-[14px] transition-colors ${
                  active
                    ? "border-accent font-medium text-ink"
                    : "border-transparent text-muted hover:text-ink"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="ml-auto flex items-center gap-2 py-2">
          <button
            type="button"
            aria-label="Notifikasi"
            title="Notifikasi"
            className="relative flex size-8 cursor-pointer items-center justify-center rounded-md text-muted transition-colors hover:bg-canvas hover:text-ink"
          >
            <Bell size={17} strokeWidth={1.75} aria-hidden />
            <span
              className="absolute top-1.5 right-1.5 size-2 rounded-full bg-danger"
              aria-hidden
            />
          </button>

          <div className="relative" ref={menuRef}>
            <button
              type="button"
              onClick={() => setOpen((v) => !v)}
              aria-expanded={open}
              aria-haspopup="menu"
              className="flex cursor-pointer items-center gap-1.5 rounded-md px-2 py-1.5 text-left transition-colors hover:bg-canvas"
            >
              <span className="max-w-[140px] truncate text-[14px] font-medium text-ink">
                {userName}
              </span>
              <span className="hidden text-[13px] text-muted sm:inline">
                {roleLabel}
              </span>
              <ChevronDown
                size={14}
                strokeWidth={1.75}
                className="text-muted"
                aria-hidden
              />
            </button>

            {open ? (
              <div
                role="menu"
                className="absolute right-0 top-full z-50 w-56 rounded-lg border border-border bg-white p-2 shadow-elevated"
              >
                <div className="px-2 py-1.5">
                  <div className="truncate text-[14px] font-medium text-ink">
                    {userName}
                  </div>
                  <div className="text-[13px] text-muted">{roleLabel}</div>
                </div>
                <form action={logout}>
                  <button
                    type="submit"
                    className="flex w-full cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-[14px] text-ink transition-colors hover:bg-canvas"
                  >
                    <LogOut size={15} strokeWidth={1.75} aria-hidden />
                    Keluar
                  </button>
                </form>
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </header>
  );
}
