"use client";

import { useActionState, useState } from "react";
import { Download, Pencil, Plus, Upload } from "lucide-react";
import {
  confirmUsersImport,
  previewUsersImport,
  saveUser,
  toggleUserStatus,
  type ConfirmState,
  type PreviewState,
  type UserFormState,
} from "./actions";
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
import type { ImportRow, ImportSummary } from "@/lib/users-import";

export type UserRow = {
  id: string;
  name: string;
  email: string;
  role: string;
  status: string;
};

function PreviewTable({ rows }: { rows: ImportRow[] }) {
  const shown = rows.slice(0, 100);
  return (
    <div className="overflow-x-auto rounded-lg border border-border bg-white">
      <Table>
        <thead>
          <tr>
            <Th>Baris</Th>
            <Th>Nama</Th>
            <Th>Email</Th>
            <Th>Peran</Th>
            <Th>Status baris</Th>
          </tr>
        </thead>
        <tbody>
          {shown.map((r) => (
            <Tr key={`${r.line}-${r.email}`}>
              <Td>{r.line}</Td>
              <Td className="font-medium">{r.name || "—"}</Td>
              <Td className="text-muted">{r.email || "—"}</Td>
              <Td>{(ROLE_LABEL[r.role] ?? r.role) || "—"}</Td>
              <Td>
                {r.error ? (
                  <span className="text-[13px] text-danger">{r.error}</span>
                ) : r.skip ? (
                  <span className="text-[13px] text-muted">{r.skip}</span>
                ) : (
                  <span className="text-[13px] font-medium text-ok">
                    Siap diimpor
                  </span>
                )}
              </Td>
            </Tr>
          ))}
        </tbody>
      </Table>
      {rows.length > shown.length ? (
        <p className="px-4 py-2 text-[13px] text-muted">
          Menampilkan 100 dari {rows.length} baris.
        </p>
      ) : null}
    </div>
  );
}

export function UsersClient({ users }: { users: UserRow[] }) {
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<UserRow | null>(null);
  const [state, formAction, pending] = useActionState<UserFormState, FormData>(
    saveUser,
    undefined,
  );
  const [rowError, setRowError] = useState<string | null>(null);

  const [importOpen, setImportOpen] = useState(false);
  const [panelHiddenAt, setPanelHiddenAt] = useState(0);
  const [dismissedAt, setDismissedAt] = useState(0);
  const [previewState, previewAction, previewPending] = useActionState<
    PreviewState,
    FormData
  >(previewUsersImport, undefined);
  const [confirmState, confirmAction, confirmPending] = useActionState<
    ConfirmState,
    FormData
  >(confirmUsersImport, undefined);

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

  const preview = previewState?.preview;
  const result = confirmState?.result;
  const resultActive =
    !!result && result.at > dismissedAt && (!preview || result.at > preview.at);
  const panelOpen =
    (importOpen || !!preview) && (!preview || preview.at > panelHiddenAt);
  const previewActive = panelOpen && !!preview && !resultActive;
  const summary: ImportSummary | null = preview
    ? {
        total: preview.total,
        importable: preview.importable,
        skipped: preview.skipped,
        errors: preview.errors,
      }
    : null;

  return (
    <div className="flex flex-col gap-6">
      <Breadcrumb items={[{ label: "Pengguna" }]} />
      <PageHeader
        title="Pengguna"
        description="Akun admin, dosen, dan mahasiswa."
        action={
          !open ? (
            <div className="flex gap-2">
              <Button
                onClick={() => {
                  if (importOpen && preview) setPanelHiddenAt(preview.at);
                  setImportOpen((v) => !v);
                  setRowError(null);
                }}
              >
                <Upload size={16} strokeWidth={1.5} aria-hidden />
                Impor Excel
              </Button>
              <Button variant="primary" onClick={() => setCreating(true)}>
                <Plus size={16} strokeWidth={1.5} aria-hidden />
                Tambah pengguna
              </Button>
            </div>
          ) : undefined
        }
      />

      {rowError ? <ErrorLine>{rowError}</ErrorLine> : null}

      {resultActive && result ? (
        <Card className="flex flex-col gap-3 p-4">
          <div className="flex items-start justify-between gap-4">
            <div className="text-[14px] text-ink">
              <span className="font-medium">{result.inserted}</span> pengguna
              ditambahkan, {result.skipped.length} dilewati,{" "}
              {result.errors.length} baris gagal dari {result.total} baris.
            </div>
            <Button onClick={() => setDismissedAt(result.at)}>Tutup</Button>
          </div>
          {result.skipped.length > 0 ? (
            <div className="text-[13px] text-muted">
              <span className="font-medium text-ink">Dilewati:</span>{" "}
              {result.skipped
                .slice(0, 20)
                .map((s) => `${s.email} (${s.reason})`)
                .join("; ")}
              {result.skipped.length > 20
                ? `; dan ${result.skipped.length - 20} lainnya`
                : ""}
            </div>
          ) : null}
          {result.errors.length > 0 ? (
            <div className="text-[13px] text-danger">
              <span className="font-medium">Gagal:</span>{" "}
              {result.errors
                .slice(0, 20)
                .map((e) => `baris ${e.line}: ${e.message}`)
                .join("; ")}
              {result.errors.length > 20
                ? `; dan ${result.errors.length - 20} lainnya`
                : ""}
            </div>
          ) : null}
        </Card>
      ) : null}

      {!open && panelOpen ? (
        <Card className="flex flex-col gap-4 p-6">
          <div className="flex items-center justify-between gap-4">
            <h2>Impor pengguna dari Excel</h2>
            <a
              href="/admin/users/template"
              className={buttonClass()}
              download
            >
              <Download size={16} strokeWidth={1.5} aria-hidden />
              Unduh template
            </a>
          </div>
          <p className="text-[14px] text-muted">
            Isi template lalu unggah berkas .xlsx. Maksimal 500 baris dan 2 MB.
            Semua pengguna baru memakai kata sandi default password123. Email
            yang sudah terdaftar akan dilewati.
          </p>

          <form action={previewAction} className="flex flex-col gap-3">
            <Field
              label="Berkas Excel (.xlsx)"
              htmlFor="imp-file"
              error={previewState?.error}
            >
              <input
                id="imp-file"
                name="file"
                type="file"
                accept=".xlsx"
                className="w-full cursor-pointer rounded border border-border bg-white px-2 py-1.5 text-[14px] text-ink file:mr-3 file:cursor-pointer file:rounded file:border file:border-border file:bg-canvas file:px-3 file:py-1 file:text-[14px] file:text-ink"
              />
            </Field>
            {previewState?.fileErrors?.length ? (
              <ErrorLine>{previewState.fileErrors.join(" ")}</ErrorLine>
            ) : null}
            <div className="flex gap-2">
              <Button type="submit" disabled={previewPending}>
                {previewPending ? "Membaca berkas..." : "Pratinjau"}
              </Button>
              <Button
                onClick={() => {
                  if (preview) setPanelHiddenAt(preview.at);
                  setImportOpen(false);
                }}
              >
                Batal
              </Button>
            </div>
          </form>

          {confirmState?.error ? <ErrorLine>{confirmState.error}</ErrorLine> : null}

          {previewActive && preview && summary ? (
            <div className="flex flex-col gap-3">
              <p className="text-[14px] text-ink">
                <span className="font-medium">{summary.total}</span> baris
                terbaca ·{" "}
                <span className="font-medium">{summary.importable}</span> siap
                diimpor · {summary.skipped} dilewati · {summary.errors} gagal
              </p>
              <PreviewTable rows={preview.rows} />
              {preview.importable > 0 ? (
                <form action={confirmAction} className="flex gap-2">
                  <input
                    type="hidden"
                    name="rows"
                    value={JSON.stringify(preview.rows)}
                  />
                  <Button
                    type="submit"
                    variant="primary"
                    disabled={confirmPending}
                  >
                    {confirmPending
                      ? "Mengimpor..."
                      : `Konfirmasi impor (${preview.importable})`}
                  </Button>
                </form>
              ) : (
                <p className="text-[14px] text-muted">
                  Tidak ada baris yang siap diimpor.
                </p>
              )}
            </div>
          ) : null}
        </Card>
      ) : null}

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
