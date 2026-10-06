import type { ReactNode } from "react";
import { requireRole } from "@/lib/session";
import { AppShell } from "@/components/shell";
import type { NavItem } from "@/components/navbar";
import { AdminTabs } from "./admin-tabs";

export default async function AdminLayout({
  children,
}: {
  children: ReactNode;
}) {
  const user = await requireRole("admin");
  const items: NavItem[] = [
    { href: "/admin", label: "Beranda", exact: true },
    { href: "/admin/courses", label: "Kursus saya" },
    { href: "/admin/users", label: "Administrasi" },
  ];
  return (
    <AppShell
      items={items}
      homeHref="/admin"
      userName={user.name}
      roleLabel="Admin"
    >
      <AdminTabs />
      {children}
    </AppShell>
  );
}
