import type { ReactNode } from "react";
import { requireRole } from "@/lib/session";
import { AppShell } from "@/components/shell";
import type { NavItem } from "@/components/navbar";

export default async function LecturerLayout({
  children,
}: {
  children: ReactNode;
}) {
  const user = await requireRole("lecturer");
  const items: NavItem[] = [
    { href: "/lecturer/home", label: "Beranda", exact: true },
    { href: "/lecturer/courses", label: "Kursus saya" },
    { href: "/lecturer/submissions", label: "Pengumpulan" },
  ];
  return (
    <AppShell
      items={items}
      homeHref="/lecturer/home"
      userName={user.name}
      roleLabel="Dosen"
    >
      {children}
    </AppShell>
  );
}
