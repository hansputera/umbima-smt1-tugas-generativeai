"use client";

import { useActionState, useState } from "react";
import { Pencil, Plus } from "lucide-react";
import { activatePeriod, deletePeriod, savePeriod, type PeriodFormState, type RowState } from "./actions";
import { Button, buttonClass } from "@/components/ui/button";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Field, Input } from "@/components/ui/field";
import { Card, ErrorLine, PageHeader, StatusDot } from "@/components/ui/misc";
import { Table, Td, Th, Tr } from "@/components/ui/table";
import { statusOf } from "@/lib/status";

export type PeriodRow = {
  id: string;
  name: string;
  is_active: boolean;
  class_count: number;
};

export function PeriodsClient({ periods }: { periods: PeriodRow[] }) {
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<PeriodRow | null>(null);
  const [state, formAction, pending] = useActionState<PeriodFormState, FormData>(
    savePeriod,
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

  async function rowAction(fn: (fd: FormData) => Promise<RowState>, id: string) {
    const fd = new FormData();
    fd.set("id", id);
    const result = await fn(fd);
    setRowError(result?.error ?? null);
  }

  const errors = state?.errors ?? {};

  return (
    <div className="flex flex-col gap-6">
      <Breadcrumb items={[{ label: "Periode" }]} />
      <PageHeader
        title="Periode"
        description="Tahun ajaran / semester akademik. Kelas mata kuliah ditautkan ke satu periode."
        action={
          !open ? (
            <Button variant="primary" onClick={() => setCreating(true)}>
              <Plus size={16} strokeWidth={1.5} aria-hidden />
              Tambah periode
            </Button>
          ) : undefined
        }
      />

      {rowError ? <ErrorLine>{rowError}</ErrorLine> : null}

      {open ? (
        <Card className="p-6">
          <h2>{editing ? "Ubah periode" : "Tambah periode"}</h2>
          <form action={formAction} className="mt-4 flex flex-col gap-4">
            {editing ? <input type="hidden" name="id" value={editing.id} /> : null}
            <div className="grid grid-cols-2 gap-4">
              <Field label="Nama periode" htmlFor="p-name" error={errors.name}>
                <Input
                  id="p-name"
                  name="name"
                  defaultValue={editing?.name ?? ""}
                  placeholder="2025/2026 Ganjil"
                />
              </Field>
            </div>
            <div className="flex gap-3">
              <Button type="submit" variant="primary" disabled={pending}>
                {pending ? "Menyimpan..." : "Simpan"}
              </Button>
              <Button
                type="button"
                onClick={() => {
                  setCreating(false);
                  setEditing(null);
                }}
              >
                Batal
              </Button>
            </div>
          </form>
        </Card>
      ) : null}

      <Table>
        <thead>
          <tr>
            <Th>Nama</Th>
            <Th>Status</Th>
            <Th>Jumlah kelas</Th>
            <Th className="text-right">Aksi</Th>
          </tr>
        </thead>
        <tbody>
          {periods.map((p) => {
            const s = statusOf(p.is_active ? "active" : "inactive");
            return (
              <Tr key={p.id}>
                <Td className="font-medium">{p.name}</Td>
                <Td>
                  <StatusDot label={s.label} color={s.color} icon={s.Icon} />
                </Td>
                <Td>{p.class_count}</Td>
                <Td>
                  <div className="flex justify-end gap-2">
                    <button
                      type="button"
                      className={`${buttonClass()} px-2.5 py-1 text-[13px]`}
                      onClick={() => {
                        setEditing(p);
                        setCreating(false);
                      }}
                    >
                      <Pencil size={16} strokeWidth={1.5} aria-hidden />
                      Ubah
                    </button>
                    {!p.is_active ? (
                      <button
                        type="button"
                        className={`${buttonClass()} px-2.5 py-1 text-[13px]`}
                        onClick={() => rowAction(activatePeriod, p.id)}
                      >
                        Jadikan aktif
                      </button>
                    ) : null}
                    <button
                      type="button"
                      className={`${buttonClass()} px-2.5 py-1 text-[13px]`}
                      onClick={() => rowAction(deletePeriod, p.id)}
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
