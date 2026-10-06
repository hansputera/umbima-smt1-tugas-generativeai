import ExcelJS from "exceljs";
import { requireRole } from "@/lib/session";

export async function GET(): Promise<Response> {
  await requireRole("admin");

  const workbook = new ExcelJS.Workbook();
  const sheet = workbook.addWorksheet("Pengguna");
  const header = sheet.addRow(["Nama", "Email", "Peran", "Status"]);
  header.eachCell((cell) => {
    cell.font = { bold: true };
  });
  sheet.addRow(["Budi Santoso", "budi@contoh.test", "mahasiswa", "aktif"]);
  sheet.addRow(["Siti Aminah", "siti@contoh.test", "dosen", "aktif"]);
  sheet.getColumn(1).width = 28;
  sheet.getColumn(2).width = 30;
  sheet.getColumn(3).width = 14;
  sheet.getColumn(4).width = 12;

  const guide = workbook.addWorksheet("Petunjuk");
  guide.addRow(["Cara pakai:"]);
  guide.addRow([
    "1. Isi sheet Pengguna, satu baris per pengguna. Jangan mengubah baris judul.",
  ]);
  guide.addRow([
    "2. Peran: Admin, Dosen, atau Mahasiswa. Status: Aktif atau Nonaktif (kosong = Aktif).",
  ]);
  guide.addRow(["3. Semua pengguna baru memakai kata sandi default: password123"]);
  guide.addRow([
    "4. Email yang sudah terdaftar akan dilewati, bukan diubah.",
  ]);
  guide.addRow(["5. Maksimal 500 baris per impor."]);
  guide.getColumn(1).width = 90;

  const buffer = await workbook.xlsx.writeBuffer();
  return new Response(new Uint8Array(buffer), {
    headers: {
      "Content-Type":
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      "Content-Disposition":
        'attachment; filename="template-pengguna.xlsx"',
    },
  });
}
