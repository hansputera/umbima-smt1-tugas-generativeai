import { Section } from "@/components/ui/misc";
import { Table, Td, Th, Tr } from "@/components/ui/table";

export type Person = { name: string; email: string };

export function PesertaContent({
  lecturers,
  students,
}: {
  lecturers: Person[];
  students: Person[];
}) {
  return (
    <>
      <Section
        title="Dosen"
        action={
          <span className="text-[13px] text-muted">{lecturers.length} orang</span>
        }
      >
        {lecturers.length === 0 ? (
          <div className="rounded-lg border border-border bg-white px-4 py-5 shadow-menu">
            <p className="text-[14px] text-muted">Belum ada dosen pengampu.</p>
          </div>
        ) : (
          <div className="overflow-hidden rounded-lg border border-border bg-white">
            {lecturers.map((l) => (
              <div
                key={l.email}
                className="flex items-center justify-between gap-4 border-b border-border px-4 py-3 last:border-b-0"
              >
                <span className="flex min-w-0 flex-col">
                  <span className="truncate text-[15px] font-medium text-ink">
                    {l.name}
                  </span>
                  <span className="truncate text-[13px] text-muted">
                    {l.email}
                  </span>
                </span>
              </div>
            ))}
          </div>
        )}
      </Section>

      <Section
        title="Mahasiswa"
        action={
          <span className="text-[13px] text-muted">
            {students.length} terdaftar
          </span>
        }
      >
        {students.length === 0 ? (
          <div className="rounded-lg border border-border bg-white px-4 py-5 shadow-menu">
            <p className="text-[14px] text-muted">Belum ada mahasiswa terdaftar.</p>
          </div>
        ) : (
          <div className="overflow-hidden rounded-lg border border-border bg-white">
            <Table>
              <thead>
                <tr>
                  <Th>Nama</Th>
                  <Th>Email</Th>
                </tr>
              </thead>
              <tbody>
                {students.map((s) => (
                  <Tr key={s.email}>
                    <Td className="font-medium text-ink">{s.name}</Td>
                    <Td className="text-muted">{s.email}</Td>
                  </Tr>
                ))}
              </tbody>
            </Table>
          </div>
        )}
      </Section>
    </>
  );
}
