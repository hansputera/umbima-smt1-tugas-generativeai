import Link from "next/link";
import { q } from "@/db/pool";
import { requireRole } from "@/lib/session";
import {
  getSettings,
  isEmbeddingConfigured,
  isModelConfigured,
} from "@/lib/settings";
import { buttonClass } from "@/components/ui/button";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Card, PageHeader, Section, StatusDot } from "@/components/ui/misc";
import { AlertTriangle, CircleCheck } from "lucide-react";
import { Table, Td, Th, Tr } from "@/components/ui/table";
import { fmtDate } from "@/lib/format";
import { ROLE_LABEL, statusOf } from "@/lib/status";

export const dynamic = "force-dynamic";

export default async function AdminHomePage() {
  await requireRole("admin");

  const settings = await getSettings();
  const recent = await q<{
    id: string;
    name: string;
    email: string;
    role: string;
    status: string;
    created_at: string;
  }>(
    `SELECT id, name, email, role, status, created_at
     FROM users ORDER BY created_at DESC LIMIT 8`,
  );

  const modelOk = isModelConfigured(settings);
  const embOk = isEmbeddingConfigured(settings);

  return (
    <div className="flex flex-col gap-6">
      <Breadcrumb items={[{ label: "Beranda" }]} />
      <PageHeader
        title="Beranda"
        description="Status model dan pengguna terbaru."
        action={
          <Link href="/admin/settings" className={buttonClass("primary")}>
            Setelan model
          </Link>
        }
      />

      <Section title="Status model">
        <Card className="p-6">
          <dl className="grid grid-cols-[200px_1fr] gap-y-2 text-[14px]">
            <dt className="label">Label penyedia</dt>
            <dd>{settings.provider_label || "—"}</dd>
            <dt className="label">Alamat dasar</dt>
            <dd className="break-all">{settings.base_url || "—"}</dd>
            <dt className="label">Nama model</dt>
            <dd>{settings.model_name || "—"}</dd>
            <dt className="label">Status penilaian</dt>
            <dd>
              {modelOk ? (
                <StatusDot label="Grading aktif" color="#1d7a3e" icon={CircleCheck} />
              ) : (
                <StatusDot label="Model belum disetel" color="#664d03" icon={AlertTriangle} />
              )}
            </dd>
            <dt className="label">Status embedding</dt>
            <dd>
              {embOk ? (
                <StatusDot label="Embedding aktif" color="#1d7a3e" icon={CircleCheck} />
              ) : (
                <StatusDot label="Embedding belum disetel" color="#664d03" icon={AlertTriangle} />
              )}
            </dd>
            <dt className="label">Terakhir disimpan</dt>
            <dd>{fmtDate(settings.updated_at)}</dd>
          </dl>
        </Card>
      </Section>

      <Section
        title="Pengguna terbaru"
        action={
          <Link href="/admin/users" className={buttonClass()}>
            Semua pengguna
          </Link>
        }
      >
        <Table>
          <thead>
            <tr>
              <Th>Nama</Th>
              <Th>Email</Th>
              <Th>Peran</Th>
              <Th>Status</Th>
              <Th>Ditambahkan</Th>
            </tr>
          </thead>
          <tbody>
            {recent.map((u) => {
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
                  <Td className="text-muted">{fmtDate(u.created_at)}</Td>
                </Tr>
              );
            })}
          </tbody>
        </Table>
      </Section>
    </div>
  );
}
