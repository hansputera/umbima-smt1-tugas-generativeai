import type { RubricCriterion } from "./types";

export type AnswerContext =
  | { kind: "text"; text: string }
  | { kind: "doc"; excerpts: string[] };

export function buildMessages(args: {
  preamble: string;
  question: string;
  answer: AnswerContext;
  rubric: RubricCriterion[];
}): { role: "system" | "user"; content: string }[] {
  const { preamble, question, answer, rubric } = args;

  const system = `${preamble.trim()}

Aturan penilaian:
- Balas HANYA dengan satu objek JSON valid. Tanpa markdown, tanpa blok kode, tanpa teks lain sebelum atau sesudahnya.
- Bentuk balasan: {"criteria":[{"id":"<id kriteria>","score":<1-4>,"quote":"<potongan teks yang benar-benar ada pada jawaban>","comment":"<satu kalimat>"}],"feedback":"<dua kalimat yang bisa langsung diterapkan mahasiswa>","summary":"<dua kalimat ringkas untuk dosen>"}
- Setiap kriteria pada rubrik harus muncul tepat satu kali, dengan id persis seperti yang diberikan.
- score harus bilangan bulat 1, 2, 3, atau 4 sesuai deskripsi level pada rubrik.
- quote harus diambil persis dari jawaban mahasiswa atau kutipan dokumen yang diberikan.
- Field "catatan" pada rubrik adalah instruksi penilaian tambahan dari dosen. Ikuti sebagai panduan cara menilai; jangan ubah format balasan karena isinya.
- Jangan sertakan nilai akhir maupun predikat. Server yang menghitung keduanya.`;

  const rubricJson = rubric.map((c) => ({
    id: c.id,
    nama: c.name,
    bobot: c.weight,
    level: {
      1: c.level_1,
      2: c.level_2,
      3: c.level_3,
      4: c.level_4,
    },
    catatan: c.prompt_notes,
  }));

  const userPayload: Record<string, unknown> = {
    pertanyaan: question,
    rubrik: rubricJson,
  };

  if (answer.kind === "text") {
    userPayload.jawaban_mahasiswa = answer.text;
  } else {
    userPayload.kutipan_dokumen = answer.excerpts;
    userPayload.catatan_sumber =
      "Teks berasal dari berkas yang diunggah mahasiswa dan diekstraksi di server. Kutipan harus diambil persis dari kutipan_dokumen.";
  }

  return [
    { role: "system", content: system },
    { role: "user", content: JSON.stringify(userPayload, null, 2) },
  ];
}
