"use client";

import { useState } from "react";
import Link from "next/link";
import { fmtDate, fmtNilai } from "@/lib/format";
import { submissionStatus, statusOf, TYPE_LABEL } from "@/lib/status";
import { buttonClass } from "@/components/ui/button";
import { Select } from "@/components/ui/field";
import { EmptyState, StatusDot } from "@/components/ui/misc";
import { Table, Td, Th, Tr } from "@/components/ui/table";

export type InboxRow = {
  id: string;
  status: string;
  submitted_at: string | null;
  student_name: string;
  course_id: string;
  course_code: string;
  course_name: string;
  assignment_id: string;
  assignment_title: string;
  type: string;
  published: boolean;
  nilai: number | string | null;
};

const STATUS_FILTERS: { value: string; label: string }[] = [
  { value: "all", label: "Semua status" },
  { value: "terkumpul", label: "Terkumpul" },
  { value: "perlu_review", label: "Perlu review" },
  { value: "dinilai", label: "Dinilai" },
  { value: "draft", label: "Draft" },
];

export function SubmissionsInbox({ rows }: { rows: InboxRow[] }) {
  const [course, setCourse] = useState("all");
  const [status, setStatus] = useState("all");

  const courses = Array.from(
    new Map(
      rows.map((r) => [r.course_id, `${r.course_code} — ${r.course_name}`]),
    ),
  ).sort((a, b) => a[1].localeCompare(b[1]));

  const filtered = rows.filter((r) => {
    if (course !== "all" && r.course_id !== course) return false;
    if (status !== "all" && submissionStatus(r.status, r.published) !== status) {
      return false;
    }
    return true;
  });

  const hasFilter = course !== "all" || status !== "all";

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end gap-4">
        <label className="flex flex-col gap-1.5">
          <span className="label">Mata kuliah</span>
          <Select
            className="w-64"
            value={course}
            onChange={(e) => setCourse(e.target.value)}
          >
            <option value="all">Semua mata kuliah</option>
            {courses.map(([id, label]) => (
              <option key={id} value={id}>
                {label}
              </option>
            ))}
          </Select>
        </label>
        <label className="flex flex-col gap-1.5">
          <span className="label">Status</span>
          <Select
            className="w-44"
            value={status}
            onChange={(e) => setStatus(e.target.value)}
          >
            {STATUS_FILTERS.map((f) => (
              <option key={f.value} value={f.value}>
                {f.label}
              </option>
            ))}
          </Select>
        </label>
        <p className="pb-2 text-[13px] text-muted">
          {filtered.length} dari {rows.length} pengumpulan
        </p>
      </div>

      {filtered.length === 0 ? (
        <EmptyState
          message={
            hasFilter
              ? "Tidak ada pengumpulan yang cocok dengan filter."
              : "Belum ada pengumpulan. Jawaban akan muncul di sini."
          }
        />
      ) : (
        <Table>
          <thead>
            <tr>
              <Th>Mahasiswa</Th>
              <Th>Mata kuliah</Th>
              <Th>Tugas</Th>
              <Th>Status</Th>
              <Th>Nilai</Th>
              <Th>Dikumpulkan</Th>
              <Th className="text-right">Aksi</Th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((r) => {
              const s = statusOf(submissionStatus(r.status, r.published));
              return (
                <Tr key={r.id}>
                  <Td className="font-medium">{r.student_name}</Td>
                  <Td>
                    <span className="font-medium">{r.course_code}</span>
                    <span className="ml-1.5 text-muted">
                      {r.course_name}
                    </span>
                  </Td>
                  <Td>
                    <span className="font-medium">{r.assignment_title}</span>
                    <span className="ml-1.5 text-muted">
                      {TYPE_LABEL[r.type] ?? r.type}
                    </span>
                  </Td>
                  <Td>
                    <StatusDot label={s.label} color={s.color} icon={s.Icon} />
                  </Td>
                  <Td>{r.nilai !== null && r.published ? fmtNilai(r.nilai) : "—"}</Td>
                  <Td>{fmtDate(r.submitted_at)}</Td>
                  <Td>
                    <div className="flex justify-end">
                      <Link
                        href={`/lecturer/submissions/${r.id}`}
                        className={`${buttonClass()} px-2.5 py-1 text-[13px]`}
                      >
                        Buka
                      </Link>
                    </div>
                  </Td>
                </Tr>
              );
            })}
          </tbody>
        </Table>
      )}
    </div>
  );
}
