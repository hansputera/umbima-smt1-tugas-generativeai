import type { ReactNode } from "react";
import { Navbar, type NavItem } from "@/components/navbar";

export function AppShell({
  items,
  homeHref,
  userName,
  roleLabel,
  children,
}: {
  items: NavItem[];
  homeHref: string;
  userName: string;
  roleLabel: string;
  children: ReactNode;
}) {
  return (
    <div className="flex min-h-screen flex-col bg-canvas">
      <Navbar
        items={items}
        homeHref={homeHref}
        userName={userName}
        roleLabel={roleLabel}
      />
      <main className="flex-1 px-6 py-6">{children}</main>
      <footer className="flex items-center justify-between border-t border-border bg-white px-6 py-3 text-[13px] text-muted">
        <span>Nilai</span>
        <span>{roleLabel}</span>
      </footer>
    </div>
  );
}
