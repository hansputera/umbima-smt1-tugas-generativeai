import type { ReactNode } from "react";
import { requireRole } from "@/lib/session";
import { AppShell } from "@/components/shell";
import type { NavItem } from "@/components/navbar";

export default async function StudentLayout({
  children,
}: {
  children: ReactNode;
}) {
  const user = await requireRole("student");
  const items: NavItem[] = [
    { href: "/student/home", label: "Beranda", exact: true },
    { href: "/student/courses", label: "Kursus saya" },
    { href: "/student/tasks", label: "Tugas" },
  ];
  return (
    <AppShell
      items={items}
      homeHref="/student/home"
      userName={user.name}
      roleLabel="Mahasiswa"
    >
      {children}
    </AppShell>
  );
}
