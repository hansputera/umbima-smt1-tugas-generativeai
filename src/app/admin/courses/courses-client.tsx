"use client";

import { useActionState, useState } from "react";
import Link from "next/link";
import { Pencil, Plus } from "lucide-react";
import { deleteCourse, saveCourse, toggleArchive } from "./actions";
import type { CourseFormState } from "./actions";
import { Button, buttonClass } from "@/components/ui/button";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Field, Input, Select } from "@/components/ui/field";
import { Card, ErrorLine, PageHeader, StatusDot } from "@/components/ui/misc";
import { Table, Td, Th, Tr } from "@/components/ui/table";
import { statusOf } from "@/lib/status";

export type CourseRow = {
  id: string;
  code: string;
  name: string;
  semester: number;
  sks: number;
  archived_at: string | null;
  period_id: string;
  section: string;
  period_name: string;
  lecturers: string | null;
  student_count: number;
};

export type PeriodOption = {
  id: string;
  name: string;
  is_active: boolean;
};

export function CoursesClient({
  courses,
  periods,
}: {
  courses: CourseRow[];
  periods: PeriodOption[];
}) {
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<CourseRow | null>(null);
  const [periodFilter, setPeriodFilter] = useState("all");
  const [state, formAction, pending] = useActionState<CourseFormState, FormData>(
    saveCourse,
    undefined,
  );
  const [rowError, setRowError] = useState<string | null>(null);

  const open = creating || editing !== null;

  const [seenState, setSeenState] = useState(state);
  if (state !== seenState) {
    setSeenState(state);
    if (state && !state.errors) {
      setCreating(false);
      setEditing(null);
    }
  }

  async function rowAction(
    fn: (fd: FormData) => Promise<{ error?: string } | undefined>,
    id: string,
    confirmText?: string,
  ) {
    if (confirmText && !window.confirm(confirmText)) return;
    const fd = new FormData();
    fd.set("id", id);
    const result = await fn(fd);
    setRowError(result?.error ?? null);
  }

  const errors = state?.errors ?? {};
  const close = () => {
    setCreating(false);
    setEditing(null);
  };

  const activePeriodId =
    periods.find((p) => p.is_active)?.id ?? periods[0]?.id ?? "";
  const visible = courses.filter(
    (c) => periodFilter === "all" || c.period_id === periodFilter,
  );

  return (
    <div className="flex flex-col gap-6">
      <Breadcrumb items={[{ label: "Mata kuliah" }]} />
      <PageHeader
        title="Mata kuliah"
        description="Kelas mata kuliah per periode, beserta dosen pengampu dan mahasiswanya."
        action={
          !open ? (
            <Button variant="primary" onClick={() => setCreating(true)}>
              <Plus size={16} strokeWidth={1.5} aria-hidden />
              Tambah kelas
            </Button>
          ) : undefined
        }
      />

      {rowError ? <ErrorLine>{rowError}</ErrorLine> : null}

      {open ? (
        <Card className="p-6">
          <h2>{editing ? "Ubah kelas" : "Tambah kelas"}</h2>
          <form action={formAction} className="mt-4 flex flex-col gap-4">
            {editing ? <input type="hidden" name="id" value={editing.id} /> : null}
            <div className="grid grid-cols-2 gap-4">
              <Field label="Kode" htmlFor="c-code" error={errors.code}>
                <Input
                  id="c-code"
                  name="code"
                  placeholder="IF201"
                  defaultValue={editing?.code ?? ""}
                />
              </Field>
              <Field label="Nama" htmlFor="c-name" error={errors.name}>
                <Input
                  id="c-name"
                  name="name"
                  placeholder="Basis Data"
                  defaultValue={editing?.name ?? ""}
                />
              </Field>
              <Field label="Periode" htmlFor="c-period" error={errors.period_id}>
                <Select
                  id="c-period"
                  name="period_id"
                  defaultValue={editing?.period_id ?? activePeriodId}
                >
                  {periods.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                      {p.is_active ? " (aktif)" : ""}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label="Kelas" htmlFor="c-section" error={errors.section}>
                <Input
                  id="c-section"
                  name="section"
                  placeholder="A"
                  defaultValue={editing?.section ?? "A"}
                />
              </Field>
              <Field label="Semester" htmlFor="c-semester" error={errors.semester}>
                <Input
                  id="c-semester"
                  name="semester"
                  type="number"
                  min="1"
                  max="14"
                  defaultValue={editing?.semester ?? 4}
                />
              </Field>
              <Field label="SKS" htmlFor="c-sks" error={errors.sks}>
                <Input
                  id="c-sks"
                  name="sks"
                  type="number"
                  min="1"
                  max="10"
                  defaultValue={editing?.sks ?? 3}
                />
              </Field>
            </div>
            <div className="flex gap-3">
              <Button type="submit" variant="primary" disabled={pending}>
                {pending ? "Menyimpan..." : "Simpan"}
              </Button>
              <Button type="button" onClick={close}>
                Batal
              </Button>
            </div>
          </form>
        </Card>
      ) : null}

      <div className="flex flex-wrap items-end justify-between gap-3">
        <p className="text-[14px] text-muted">
          {visible.length} dari {courses.length} kelas
        </p>
        <Field label="Filter periode" htmlFor="c-filter">
          <Select
            id="c-filter"
            value={periodFilter}
            onChange={(e) => setPeriodFilter(e.target.value)}
          >
            <option value="all">Semua periode</option>
            {periods.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
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
            <Th>Periode</Th>
            <Th>Kelas</Th>
            <Th>Semester</Th>
            <Th>SKS</Th>
            <Th>Dosen</Th>
            <Th>Mahasiswa</Th>
            <Th>Status</Th>
            <Th className="text-right">Aksi</Th>
          </tr>
        </thead>
        <tbody>
          {visible.map((c) => {
            const s = c.archived_at ? statusOf("archived") : statusOf("aktif");
            return (
              <Tr key={c.id}>
                <Td className="font-medium">{c.code}</Td>
                <Td>{c.name}</Td>
                <Td>{c.period_name}</Td>
                <Td>{c.section}</Td>
                <Td>{c.semester}</Td>
                <Td>{c.sks}</Td>
                <Td className="text-muted">{c.lecturers ?? "—"}</Td>
                <Td>{c.student_count}</Td>
                <Td>
                  <StatusDot label={s.label} color={s.color} icon={s.Icon} />
                </Td>
                <Td>
                  <div className="flex justify-end gap-2">
                    <Link
                      href={`/admin/courses/${c.id}`}
                      className={`${buttonClass()} px-2.5 py-1 text-[13px]`}
                    >
                      Buka
                    </Link>
                    <button
                      type="button"
                      className={`${buttonClass()} px-2.5 py-1 text-[13px]`}
                      onClick={() => {
                        setEditing(c);
                        setCreating(false);
                      }}
                    >
                      <Pencil size={16} strokeWidth={1.5} aria-hidden />
                      Ubah
                    </button>
                    <button
                      type="button"
                      className={`${buttonClass()} px-2.5 py-1 text-[13px]`}
                      onClick={() => rowAction(toggleArchive, c.id)}
                    >
                      {c.archived_at ? "Buka arsip" : "Arsipkan"}
                    </button>
                    <button
                      type="button"
                      className={`${buttonClass()} px-2.5 py-1 text-[13px]`}
                      onClick={() =>
                        rowAction(
                          deleteCourse,
                          c.id,
                          `Hapus ${c.code} ${c.name}?`,
                        )
                      }
                    >
                      Hapus
                    </button>
                  </div>
                </Td>
              </Tr>
            );
          })}
        </tbody>
      </Table>
    </div>
  );
}
