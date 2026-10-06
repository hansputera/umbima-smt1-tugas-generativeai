import type { CourseTab } from "./course-frame";

export function courseTabs(
  courseId: string,
  role: "student" | "lecturer",
): CourseTab[] {
  const base = `/${role}/courses/${courseId}`;
  const tabs: CourseTab[] = [
    { href: base, label: "Kursus", activePrefixes: [`${base}/topics/`] },
    { href: `${base}/peserta`, label: "Peserta", exact: true },
    { href: `${base}/tugas`, label: "Tugas", exact: true },
    { href: `${base}/nilai`, label: "Nilai", exact: true },
  ];
  if (role === "lecturer") {
    tabs.push({ href: `${base}/pengaturan`, label: "Pengaturan", exact: true });
  }
  return tabs;
}
