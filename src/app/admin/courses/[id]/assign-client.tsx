"use client";

import { useState } from "react";
import { Search } from "lucide-react";
import { toggleEnrollment, toggleLecturer } from "../actions";
import { Field, Input } from "@/components/ui/field";

type Person = { id: string; name: string; email: string };

function matches(person: Person, query: string): boolean {
  const q = query.trim().toLowerCase();
  if (!q) return true;
  return (
    person.name.toLowerCase().includes(q) ||
    person.email.toLowerCase().includes(q)
  );
}

export function AssignClient({
  courseId,
  lecturers,
  students,
  initialLecturerIds,
  initialStudentIds,
}: {
  courseId: string;
  lecturers: Person[];
  students: Person[];
  initialLecturerIds: string[];
  initialStudentIds: string[];
}) {
  const [lecturerIds, setLecturerIds] = useState<Set<string>>(
    new Set(initialLecturerIds),
  );
  const [studentIds, setStudentIds] = useState<Set<string>>(
    new Set(initialStudentIds),
  );
  const [error, setError] = useState<string | null>(null);
  const [lecturerQuery, setLecturerQuery] = useState("");
  const [studentQuery, setStudentQuery] = useState("");

  const visibleLecturers = lecturers.filter((l) => matches(l, lecturerQuery));
  const visibleStudents = students.filter((s) => matches(s, studentQuery));

  async function toggle(
    kind: "lecturer" | "student",
    personId: string,
    currentlyOn: boolean,
    revert: () => void,
  ) {
    const fd = new FormData();
    fd.set("course_id", courseId);
    fd.set(kind === "lecturer" ? "user_id" : "student_id", personId);
    const fn = kind === "lecturer" ? toggleLecturer : toggleEnrollment;
    const result = await fn(fd);
    if (result?.error) {
      revert();
      setError(result.error);
    } else {
      setError(null);
    }
  }

  return (
    <>
      {error ? (
        <p className="text-[13px] leading-snug text-danger">{error}</p>
      ) : null}

      <section className="flex flex-col gap-3">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <h2>Dosen pengampu</h2>
          <Field label="Cari dosen" htmlFor="assign-lecturer-q">
            <div className="relative">
              <Search
                size={14}
                strokeWidth={1.5}
                aria-hidden
                className="pointer-events-none absolute top-1/2 left-2.5 -translate-y-1/2 text-muted"
              />
              <Input
                id="assign-lecturer-q"
                value={lecturerQuery}
                onChange={(e) => setLecturerQuery(e.target.value)}
                placeholder="Nama atau email"
                className="min-w-[220px] pl-7"
              />
            </div>
          </Field>
        </div>
        <div className="rounded-lg border border-border bg-white shadow-menu">
          {visibleLecturers.length === 0 ? (
            <p className="px-4 py-3 text-[14px] text-muted">
              Tidak ada dosen yang cocok.
            </p>
          ) : null}
          {visibleLecturers.map((l, i) => {
            const on = lecturerIds.has(l.id);
            return (
              <label
                key={l.id}
                className={`flex cursor-pointer items-center gap-3 px-4 py-2.5 transition-colors hover:bg-row-hover ${
                  i > 0 ? "border-t border-border" : ""
                }`}
              >
                <input
                  type="checkbox"
                  className="size-4 accent-accent"
                  checked={on}
                  onChange={() => {
                    const next = new Set(lecturerIds);
                    if (on) next.delete(l.id);
                    else next.add(l.id);
                    setLecturerIds(next);
                    void toggle(
                      "lecturer",
                      l.id,
                      on,
                      () => setLecturerIds(new Set(lecturerIds)),
                    );
                  }}
                />
                <span className="text-[14px] font-medium">{l.name}</span>
                <span className="text-[13px] text-muted">{l.email}</span>
              </label>
            );
          })}
        </div>
      </section>

      <section className="flex flex-col gap-3">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <h2>Mahasiswa</h2>
          <Field label="Cari mahasiswa" htmlFor="assign-student-q">
            <div className="relative">
              <Search
                size={14}
                strokeWidth={1.5}
                aria-hidden
                className="pointer-events-none absolute top-1/2 left-2.5 -translate-y-1/2 text-muted"
              />
              <Input
                id="assign-student-q"
                value={studentQuery}
                onChange={(e) => setStudentQuery(e.target.value)}
                placeholder="Nama atau email"
                className="min-w-[220px] pl-7"
              />
            </div>
          </Field>
        </div>
        <div className="rounded-lg border border-border bg-white shadow-menu">
          {visibleStudents.length === 0 ? (
            <p className="px-4 py-3 text-[14px] text-muted">
              Tidak ada mahasiswa yang cocok.
            </p>
          ) : null}
          {visibleStudents.map((s, i) => {
            const on = studentIds.has(s.id);
            return (
              <label
                key={s.id}
                className={`flex cursor-pointer items-center gap-3 px-4 py-2.5 transition-colors hover:bg-row-hover ${
                  i > 0 ? "border-t border-border" : ""
                }`}
              >
                <input
                  type="checkbox"
                  className="size-4 accent-accent"
                  checked={on}
                  onChange={() => {
                    const next = new Set(studentIds);
                    if (on) next.delete(s.id);
                    else next.add(s.id);
                    setStudentIds(next);
                    void toggle(
                      "student",
                      s.id,
                      on,
                      () => setStudentIds(new Set(studentIds)),
                    );
                  }}
                />
                <span className="text-[14px] font-medium">{s.name}</span>
                <span className="text-[13px] text-muted">{s.email}</span>
              </label>
            );
          })}
        </div>
      </section>
    </>
  );
}
