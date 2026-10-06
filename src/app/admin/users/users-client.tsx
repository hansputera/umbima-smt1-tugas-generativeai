"use client";

import { useActionState, useState } from "react";
import { Pencil, Plus } from "lucide-react";
import { saveUser, toggleUserStatus, type UserFormState } from "./actions";
import { Button, buttonClass } from "@/components/ui/button";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Field, Input, Select } from "@/components/ui/field";
import {
  Card,
  ErrorLine,
  PageHeader,
  StatusDot,
} from "@/components/ui/misc";
import { Table, Td, Th, Tr } from "@/components/ui/table";
import { ROLE_LABEL, statusOf } from "@/lib/status";

export type UserRow = {
  id: string;
  name: string;
  email: string;
  role: string;
  status: string;
};

export function UsersClient({ users }: { users: UserRow[] }) {
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<UserRow | null>(null);
  const [state, formAction, pending] = useActionState<UserFormState, FormData>(
    saveUser,
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

  async function handleToggle(user: UserRow) {
    const fd = new FormData();
    fd.set("id", user.id);
    const result = await toggleUserStatus(fd);
    setRowError(result?.error ?? null);
  }

  const errors = state?.errors ?? {};
  const value = (key: keyof UserRow): string => {
    if (editing) return String(editing[key]);
    return "";
  };

  return (
    <div className="flex flex-col gap-6">
      <Breadcrumb items={[{ label: "Pengguna" }]} />
      <PageHeader
        title="Pengguna"
        description="Akun admin, dosen, dan mahasiswa."
        action={
          !open ? (
            <Button variant="primary" onClick={() => setCreating(true)}>
              <Plus size={16} strokeWidth={1.5} aria-hidden />
              Tambah pengguna
            </Button>
          ) : undefined
        }
      />

      {rowError ? <ErrorLine>{rowError}</ErrorLine> : null}

      {open ? (
        <Card className="p-6">
          <h2>{editing ? "Ubah pengguna" : "Tambah pengguna"}</h2>
          <form
            action={formAction}
            className="mt-4 flex flex-col gap-4"
          >
            {editing ? <input type="hidden" name="id" value={editing.id} /> : null}
            <div className="grid grid-cols-2 gap-4">
              <Field label="Nama" htmlFor="u-name" error={errors.name}>
                <Input
                  id="u-name"
                  name="name"
                  defaultValue={value("name")}
                  placeholder="Nama lengkap"
                />
              </Field>
              <Field label="Email" htmlFor="u-email" error={errors.email}>
                <Input
                  id="u-email"
                  name="email"
                  type="email"
                  defaultValue={value("email")}
                  placeholder="nama@nilai.test"
                />
              </Field>
              <Field label="Peran" htmlFor="u-role" error={errors.role}>
                <Select
                  id="u-role"
                  name="role"
                  defaultValue={editing ? editing.role : "student"}
                >
                  <option value="admin">Admin</option>
                  <option value="lecturer">Dosen</option>
                  <option value="student">Mahasiswa</option>
                </Select>
              </Field>
              <Field label="Status" htmlFor="u-status" error={errors.status}>
                <Select
                  id="u-status"
                  name="status"
                  defaultValue={editing ? editing.status : "active"}
                >
                  <option value="active">Aktif</option>
                  <option value="inactive">Nonaktif</option>
                </Select>
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
            <Th>Email</Th>
            <Th>Peran</Th>
            <Th>Status</Th>
            <Th className="text-right">Aksi</Th>
          </tr>
        </thead>
        <tbody>
          {users.map((u) => {
            const s = statusOf(
              u.status === "active" ? "active" : "inactive",
            );
            return (
              <Tr key={u.id}>
                <Td className="font-medium">{u.name}</Td>
                <Td className="text-muted">{u.email}</Td>
                <Td>{ROLE_LABEL[u.role] ?? u.role}</Td>
                <Td>
                  <StatusDot label={s.label} color={s.color} icon={s.Icon} />
                </Td>
                <Td>
                  <div className="flex justify-end gap-2">
                    <button
                      type="button"
                      className={`${buttonClass()} px-2.5 py-1 text-[13px]`}
                      onClick={() => {
                        setEditing(u);
                        setCreating(false);
                      }}
                    >
                      <Pencil size={16} strokeWidth={1.5} aria-hidden />
                      Ubah
                    </button>
                    <button
                      type="button"
                      className={`${buttonClass()} px-2.5 py-1 text-[13px]`}
                      onClick={() => handleToggle(u)}
                    >
                      {u.status === "active" ? "Nonaktifkan" : "Aktifkan"}
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
