"use client";

import { useMemo, useState } from "react";
import { Search } from "lucide-react";
import { toggleEnrollment } from "../courses/actions";
import { Field, Input, Select } from "@/components/ui/field";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { ErrorLine, PageHeader } from "@/components/ui/misc";
import { Table, Td, Th, Tr } from "@/components/ui/table";

export type PeriodOption = {
  id: string;
  name: string;
  is_active: boolean;
};

export type StudentRow = {
  id: string;
  name: string;
  email: string;
};

export type ClassRow = {
  id: string;
  code: string;
  name: string;
  section: string;
  period_id: string;
  period_name: string;
  lecturers: string | null;
};

export type EnrollmentPair = {
  course_id: string;
  student_id: string;
};

export function PlacementClient({
  periods,
  students,
  classes,
  pairs,
}: {
  periods: PeriodOption[];
  students: StudentRow[];
  classes: ClassRow[];
  pairs: EnrollmentPair[];
}) {
  const activePeriodId =
    periods.find((p) => p.is_active)?.id ?? periods[0]?.id ?? "";
  const [periodId, setPeriodId] = useState(activePeriodId);
  const [selectedStudent, setSelectedStudent] = useState<StudentRow | null>(
    null,
  );
  const [studentQuery, setStudentQuery] = useState("");
  const [enrolled, setEnrolled] = useState<Set<string>>(
    () => new Set(pairs.map((p) => `${p.course_id}:${p.student_id}`)),
  );
  const [error, setError] = useState<string | null>(null);

  const studentCounts = useMemo(() => {
    const counts = new Map<string, number>();
    for (const p of pairs) {
      counts.set(p.student_id, (counts.get(p.student_id) ?? 0) + 1);
    }
    return counts;
  }, [pairs]);

  const visibleStudents = students.filter((s) => {
    const q = studentQuery.trim().toLowerCase();
    if (!q) return true;
    return (
      s.name.toLowerCase().includes(q) || s.email.toLowerCase().includes(q)
    );
  });

  const periodClasses = classes.filter((c) => c.period_id === periodId);

  async function toggle(classId: string, on: boolean) {
    if (!selectedStudent) return;
    const key = `${classId}:${selectedStudent.id}`;
    const next = new Set(enrolled);
    if (on) next.delete(key);
    else next.add(key);
    setEnrolled(next);

    const fd = new FormData();
    fd.set("course_id", classId);
    fd.set("student_id", selectedStudent.id);
    const result = await toggleEnrollment(fd);
    if (result?.error) {
      setEnrolled(enrolled);
      setError(result.error);
    } else {
      setError(null);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <Breadcrumb items={[{ label: "Penempatan" }]} />
      <PageHeader
        title="Penempatan"
        description="Tempatkan mahasiswa ke kelas tiap periode. Penempatan hanya diatur admin."
      />

      {error ? <ErrorLine>{error}</ErrorLine> : null}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[320px_1fr]">
        <div className="flex flex-col gap-3">
          <Field label="Pilih mahasiswa" htmlFor="placement-student-q">
            <div className="relative">
              <Search
                size={14}
                strokeWidth={1.5}
                aria-hidden
                className="pointer-events-none absolute top-1/2 left-2.5 -translate-y-1/2 text-muted"
              />
              <Input
                id="placement-student-q"
                value={studentQuery}
                onChange={(e) => setStudentQuery(e.target.value)}
                placeholder="Nama atau email"
                className="pl-7"
              />
            </div>
          </Field>
          <div className="max-h-[520px] overflow-y-auto rounded-lg border border-border bg-white shadow-menu">
            {visibleStudents.length === 0 ? (
              <p className="px-4 py-3 text-[14px] text-muted">
                Tidak ada mahasiswa yang cocok.
              </p>
            ) : null}
            {visibleStudents.map((s, i) => {
              const on = selectedStudent?.id === s.id;
              return (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => setSelectedStudent(s)}
                  className={`flex w-full flex-col items-start gap-0.5 px-4 py-2.5 text-left transition-colors hover:bg-row-hover ${
                    i > 0 ? "border-t border-border" : ""
                  } ${on ? "bg-row-hover" : ""}`}
                >
                  <span
                    className={`text-[14px] ${on ? "font-medium text-ink" : "text-ink"}`}
                  >
                    {s.name}
                  </span>
                  <span className="text-[13px] text-muted">
                    {s.email} · {studentCounts.get(s.id) ?? 0} kelas
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        <div className="flex flex-col gap-3">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <h2>Kelas</h2>
              <p className="text-[14px] text-muted">
                {selectedStudent
                  ? `Penempatan untuk ${selectedStudent.name}`
                  : "Pilih mahasiswa terlebih dahulu."}
              </p>
            </div>
            <Field label="Periode" htmlFor="placement-period">
              <Select
                id="placement-period"
                value={periodId}
                onChange={(e) => setPeriodId(e.target.value)}
              >
                {periods.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                    {p.is_active ? " (aktif)" : ""}
                  </option>
                ))}
              </Select>
            </Field>
          </div>

          <Table>
            <thead>
              <tr>
                <Th>Kode</Th>
                <Th>Nama</Th>
                <Th>Kelas</Th>
                <Th>Dosen</Th>
                <Th className="text-center">Terdaftar</Th>
              </tr>
            </thead>
            <tbody>
              {periodClasses.length === 0 ? (
                <Tr>
                  <Td className="text-muted" colSpan={5}>
                    Belum ada kelas di periode ini.
                  </Td>
                </Tr>
              ) : null}
              {periodClasses.map((c) => {
                const on = selectedStudent
                  ? enrolled.has(`${c.id}:${selectedStudent.id}`)
                  : false;
                return (
                  <Tr key={c.id}>
                    <Td className="font-medium">{c.code}</Td>
                    <Td>{c.name}</Td>
                    <Td>{c.section}</Td>
                    <Td className="text-muted">{c.lecturers ?? "—"}</Td>
                    <Td className="text-center">
                      <input
                        type="checkbox"
                        className="size-4 accent-accent"
                        checked={on}
                        disabled={!selectedStudent}
                        onChange={() => toggle(c.id, on)}
                        aria-label={`Daftarkan ke ${c.code} kelas ${c.section}`}
                      />
                    </Td>
                  </Tr>
                );
              })}
            </tbody>
          </Table>
        </div>
      </div>
    </div>
  );
}
