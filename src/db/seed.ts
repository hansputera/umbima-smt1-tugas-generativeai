import type { PoolClient } from "pg";
import { DEFAULT_PASSWORD, hashPassword } from "@/lib/password";

const U = {
  admin: "a1000000-0000-4000-8000-000000000001",
  ramadan: "a1000000-0000-4000-8000-000000000002",
  aldy: "a1000000-0000-4000-8000-000000000011",
  miratil: "a1000000-0000-4000-8000-000000000012",
  ismail: "a1000000-0000-4000-8000-000000000013",
  fitri: "a1000000-0000-4000-8000-000000000014",
};

const P = {
  ganjil: "b2000000-0000-4000-8000-000000000001",
  genap: "b2000000-0000-4000-8000-000000000002",
};

const C = {
  bd: "b1000000-0000-4000-8000-000000000001",
  web: "b1000000-0000-4000-8000-000000000002",
  bd_b: "b1000000-0000-4000-8000-000000000003",
};

const T = {
  bd1: "c1000000-0000-4000-8000-000000000001",
  bd2: "c1000000-0000-4000-8000-000000000002",
  bd3: "c1000000-0000-4000-8000-000000000003",
  web1: "c1000000-0000-4000-8000-000000000004",
  web2: "c1000000-0000-4000-8000-000000000005",
};

const A = {
  essay: "d1000000-0000-4000-8000-000000000001",
  pg: "d1000000-0000-4000-8000-000000000002",
  pdf: "d1000000-0000-4000-8000-000000000003",
  docx: "d1000000-0000-4000-8000-000000000004",
};

const CR = {
  c1: "e1000000-0000-4000-8000-000000000001",
  c2: "e1000000-0000-4000-8000-000000000002",
  c3: "e1000000-0000-4000-8000-000000000003",
  c4: "e1000000-0000-4000-8000-000000000004",
};

const S = {
  aldy: "f1000000-0000-4000-8000-000000000001",
  miratil: "f1000000-0000-4000-8000-000000000002",
  ismail: "f1000000-0000-4000-8000-000000000003",
  fitri: "f1000000-0000-4000-8000-000000000004",
};

const G = {
  aldy: "a0000000-0000-4000-8000-000000000001",
  ismail: "a0000000-0000-4000-8000-000000000002",
};

const RUBRIC = [
  {
    name: "Ketepatan konsep",
    weight: 25,
    level_1: "Menyebut istilah tanpa penjelasan.",
    level_2: "Definisi tidak lengkap, ada kesalahan kecil.",
    level_3: "Definisi benar dan lengkap sebagian besar.",
    level_4: "Definisi tepat dan konsisten sepanjang jawaban.",
    prompt_notes: "Abaikan salah ketik asal makna tetap jelas.",
  },
  {
    name: "Kelengkapan",
    weight: 25,
    level_1: "Hanya satu poin yang disebut.",
    level_2: "Dua dari tiga poin utama ada.",
    level_3: "Semua poin ada, satu belum dikembangkan.",
    level_4: "Semua poin ada dan dikembangkan.",
    prompt_notes: "Wajib menyebut ketiga poin yang ditanyakan.",
  },
  {
    name: "Struktur argumen",
    weight: 25,
    level_1: "Tidak ada urutan logis.",
    level_2: "Urutan terlihat tetapi lompat-lompat.",
    level_3: "Terstruktur dengan pembuka dan penutup.",
    level_4: "Terstruktur rapi, setiap poin didukung alasan.",
    prompt_notes: "Jangan menilai gaya bahasa, hanya urutan.",
  },
  {
    name: "Contoh penerapan",
    weight: 25,
    level_1: "Tanpa contoh.",
    level_2: "Contoh disebut tanpa penjelasan.",
    level_3: "Contoh benar, penjelasan singkat.",
    level_4: "Contoh konkret dan dihubungkan ke teori.",
    prompt_notes: "Contoh hipotetis diperbolehkan.",
  },
];

const ALDY_ANSWER = `Normalisasi adalah proses menyusun tabel agar redundansi data berkurang. Bentuk pertama (1NF) menghilangkan nilai ganda sehingga setiap sel berisi satu nilai. Bentuk kedua (2NF) menghilangkan ketergantungan parsial dengan memindahkan atribut yang hanya bergantung pada sebagian kunci ke tabel lain. Bentuk ketiga (3NF) menghilangkan ketergantungan transitif. Contohnya, tabel transaksi yang menyimpan nama pelanggan sebaiknya dipisah ke tabel pelanggan agar perubahan nama cukup diubah di satu tempat.`;

const MIRATIL_ANSWER = `Normalisasi dipakai supaya data tidak dobel. Kalau tabelnya banyak maka query jadi lambat, jadi dibuat terpisah menurut kebutuhan.`;

const FITRI_TEXT = `Laporan analisis basis data akademik. Tabel mahasiswa menyimpan nim, nama, dan email. Tabel kelas menyimpan id_kelas, kode_matakuliah, dan dosen. Ditemukan redundansi penyimpanan nama dosen pada setiap baris kelas. Rekomendasi: pindahkan data dosen ke tabel dosen dan hubungkan dengan kunci asing.`;

async function insertRubric(
  c: PoolClient,
  assignmentId: string,
  fixedIds?: string[],
): Promise<void> {
  for (let i = 0; i < RUBRIC.length; i++) {
    const r = RUBRIC[i];
    const fixedId = fixedIds?.[i];
    if (fixedId) {
      await c.query(
        `INSERT INTO rubric_criteria (id, assignment_id, position, name, weight, level_1, level_2, level_3, level_4, prompt_notes)
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)`,
        [
          fixedId,
          assignmentId,
          i,
          r.name,
          r.weight,
          r.level_1,
          r.level_2,
          r.level_3,
          r.level_4,
          r.prompt_notes,
        ],
      );
    } else {
      await c.query(
        `INSERT INTO rubric_criteria (assignment_id, position, name, weight, level_1, level_2, level_3, level_4, prompt_notes)
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)`,
        [
          assignmentId,
          i,
          r.name,
          r.weight,
          r.level_1,
          r.level_2,
          r.level_3,
          r.level_4,
          r.prompt_notes,
        ],
      );
    }
  }
}

export async function seedIfEmpty(c: PoolClient): Promise<boolean> {
  const { rows } = await c.query<{ n: string }>("SELECT count(*)::text AS n FROM users");
  if (Number(rows[0].n) > 0) return false;

  await c.query("BEGIN");
  try {
    await seedData(c);
  } catch (err) {
    await c.query("ROLLBACK");
    throw err;
  }
  await c.query("COMMIT");
  return true;
}

async function seedData(c: PoolClient): Promise<void> {
  const users: [string, string, string, string][] = [
    [U.admin, "Nur Audyah Ramadhani", "audyah@nilai.test", "admin"],
    [U.ramadan, "Ramadan Agung Wibawa", "ramadan@nilai.test", "lecturer"],
    [U.aldy, "Aldy", "aldy@nilai.test", "student"],
    [U.miratil, "Mir'atil Hayati", "miratil@nilai.test", "student"],
    [U.ismail, "Ismail Saputra", "ismail@nilai.test", "student"],
    [U.fitri, "Fitri Lestari", "fitri@nilai.test", "student"],
  ];
  for (const [id, name, email, role] of users) {
    await c.query(
      `INSERT INTO users (id, name, email, role, password_hash)
       VALUES ($1, $2, $3, $4, $5)`,
      [id, name, email, role, hashPassword(DEFAULT_PASSWORD)],
    );
  }

  await c.query(
    `INSERT INTO periods (id, name, is_active) VALUES
     ($1, '2025/2026 Ganjil', true),
     ($2, '2025/2026 Genap', false)`,
    [P.ganjil, P.genap],
  );

  await c.query(
    `INSERT INTO courses (id, code, name, semester, sks, period_id, section) VALUES
     ($1, 'IF201', 'Basis Data', 4, 3, $3, 'A'),
     ($2, 'IF315', 'Pembangunan Aplikasi Web', 6, 3, $3, 'A'),
     ($4, 'IF201', 'Basis Data', 4, 3, $3, 'B')`,
    [C.bd, C.web, P.ganjil, C.bd_b],
  );

  for (const [courseId, lecturerId] of [
    [C.bd, U.ramadan],
    [C.web, U.ramadan],
  ]) {
    await c.query(
      `INSERT INTO course_lecturers (course_id, user_id) VALUES ($1, $2)`,
      [courseId, lecturerId],
    );
  }

  for (const studentId of [U.aldy, U.miratil, U.ismail, U.fitri]) {
    for (const courseId of [C.bd, C.web]) {
      await c.query(
        `INSERT INTO enrollments (course_id, student_id) VALUES ($1, $2)`,
        [courseId, studentId],
      );
    }
  }

  const topics: [string, string, number, string][] = [
    [T.bd1, C.bd, 1, "Relasi dan model data"],
    [T.bd2, C.bd, 2, "Normalisasi"],
    [T.bd3, C.bd, 3, "Kueri SQL"],
    [T.web1, C.web, 1, "Arsitektur aplikasi web"],
    [T.web2, C.web, 2, "Server components dan data"],
  ];
  for (const [id, courseId, week, title] of topics) {
    await c.query(
      `INSERT INTO topics (id, course_id, week, title) VALUES ($1, $2, $3, $4)`,
      [id, courseId, week, title],
    );
  }

  const materi: [string, string, string | null, string | null, string | null][] = [
    [T.bd1, "richtext", "Baca materi model data relasional: entitas, atribut, kunci primer, dan kunci asing. Catat satu pertanyaan sebelum pertemuan.", null, null],
    [T.bd1, "link", "Dokumentasi PostgreSQL — tutorial pemula", "https://www.postgresql.org/docs/current/tutorial-start.html", null],
    [T.bd1, "file", null, null, "materi-pertemuan-1.pdf"],
    [T.bd2, "richtext", "Normalisasi dari 1NF sampai 3NF. Kerjakan latihan normalisasi pada lembar kerja sebelum pertemuan.", null, null],
    [T.bd2, "file", null, null, "lembar-normalisasi.docx"],
    [T.bd3, "richtext", "SELECT, JOIN, dan subkueri. Latihan soal memakai basis data contoh kampus.", null, null],
    [T.web1, "richtext", "Arsitektur aplikasi web: client, server, dan keputusan rendering.", null, null],
    [T.web1, "link", "Dokumentasi Next.js — App Router", "https://nextjs.org/docs/app", null],
    [T.web2, "richtext", "Server components, fetching data di server, dan batas antara klien serta server.", null, null],
    [T.web2, "file", null, null, "materi-server-components.pdf"],
  ];
  let position = 0;
  let lastTopic = "";
  for (const [topicId, type, body, url, fileName] of materi) {
    if (topicId !== lastTopic) {
      position = 0;
      lastTopic = topicId;
    }
    await c.query(
      `INSERT INTO materi_blocks (topic_id, type, body, url, file_name, position)
       VALUES ($1, $2, $3, $4, $5, $6)`,
      [topicId, type, body, url, fileName, position],
    );
    position += 1;
  }

  await c.query(
    `INSERT INTO assignments (id, topic_id, title, type, release_mode, due_at) VALUES
     ($1, $2, 'Esai: bentuk normalisasi', 'essay', 'review', now() + interval '2 days'),
     ($3, $4, 'Pilihan ganda: kueri JOIN', 'pg', 'review', now() + interval '4 days'),
     ($5, $6, 'Unggah laporan analisis (PDF)', 'pdf', 'review', now() + interval '6 days'),
     ($7, $8, 'Unggah rancangan skema (DOCX)', 'docx', 'langsung', now() + interval '9 days')`,
    [A.essay, T.bd2, A.pg, T.bd3, A.pdf, T.web2, A.docx, T.web1],
  );

  await c.query(
    `INSERT INTO assignment_questions (assignment_id, position, question, options, answer_key) VALUES
     ($1, 0, 'Jelaskan bentuk normalisasi 1NF, 2NF, dan 3NF beserta satu contoh penerapan pada basis data kampus.', null, null),
     ($2, 0, 'Klausa yang digunakan untuk menggabungkan dua tabel berdasarkan kunci adalah ...', $3::jsonb, 'B'),
     ($2, 1, 'Klausa yang menggabungkan hasil dua pernyataan SELECT dan menghilangkan baris duplikat adalah ...', $4::jsonb, 'A'),
     ($2, 2, 'Fungsi agregat yang menghitung jumlah baris pada hasil kueri adalah ...', $5::jsonb, 'C'),
     ($6, 0, 'Unggah laporan analisis basis data dalam PDF: identifikasi tabel, kolom, dan rekomendasi normalisasi.', null, null),
     ($7, 0, 'Unggah rancangan skema basis data aplikasi dalam DOCX berisi daftar tabel dan relasi.', null, null)`,
    [
      A.essay,
      A.pg,
      JSON.stringify([
        { key: "A", text: "UNION" },
        { key: "B", text: "JOIN" },
        { key: "C", text: "GROUP BY" },
        { key: "D", text: "HAVING" },
      ]),
      JSON.stringify([
        { key: "A", text: "UNION" },
        { key: "B", text: "INTERSECT" },
        { key: "C", text: "EXCEPT" },
        { key: "D", text: "ORDER BY" },
      ]),
      JSON.stringify([
        { key: "A", text: "SUM" },
        { key: "B", text: "AVG" },
        { key: "C", text: "COUNT" },
        { key: "D", text: "MAX" },
      ]),
      A.pdf,
      A.docx,
    ],
  );

  await insertRubric(c, A.essay, [CR.c1, CR.c2, CR.c3, CR.c4]);
  await insertRubric(c, A.pdf);
  await insertRubric(c, A.docx);

  // Submissions -------------------------------------------------------------
  await c.query(
    `INSERT INTO submissions (id, assignment_id, student_id, answer_text, status, submitted_at, updated_at)
     VALUES ($1, $2, $3, $4, 'submitted', now() - interval '3 days', now() - interval '3 days')`,
    [S.aldy, A.essay, U.aldy, ALDY_ANSWER],
  );
  await c.query(
    `INSERT INTO submissions (id, assignment_id, student_id, answer_text, status, submitted_at, updated_at)
     VALUES ($1, $2, $3, $4, 'submitted', now() - interval '1 day', now() - interval '1 day')`,
    [S.miratil, A.essay, U.miratil, MIRATIL_ANSWER],
  );
  await c.query(
    `INSERT INTO submissions (id, assignment_id, student_id, answers, status, submitted_at, updated_at)
     VALUES ($1, $2, $3, $4::jsonb, 'submitted', now() - interval '2 days', now() - interval '2 days')`,
    [S.ismail, A.pg, U.ismail, JSON.stringify(["B", "A", "C"])],
  );
  await c.query(
    `INSERT INTO submissions (id, assignment_id, student_id, file_name, extracted_text, extraction_ok, status, submitted_at, updated_at)
     VALUES ($1, $2, $3, 'laporan-analisis.pdf', $4, true, 'submitted', now() - interval '1 day', now() - interval '1 day')`,
    [S.fitri, A.pdf, U.fitri, FITRI_TEXT],
  );

  // Published grade for Aldy's essay ---------------------------------------
  const aldyCriteria = [
    {
      criterion_id: CR.c1,
      name: "Ketepatan konsep",
      weight: 25,
      score: 3,
      quote: "Normalisasi adalah proses menyusun tabel agar redundansi data berkurang.",
      comment: "Definisi benar tetapi belum menyebut tujuan pengurangan redundansi secara eksplisit.",
    },
    {
      criterion_id: CR.c2,
      name: "Kelengkapan",
      weight: 25,
      score: 4,
      quote: "Bentuk kedua (2NF) menghilangkan ketergantungan parsial dengan memindahkan atribut yang hanya bergantung pada sebagian kunci ke tabel lain.",
      comment: "Ketiga bentuk normalisasi dijelaskan lengkap.",
    },
    {
      criterion_id: CR.c3,
      name: "Struktur argumen",
      weight: 25,
      score: 3,
      quote: "Bentuk pertama (1NF) menghilangkan nilai ganda sehingga setiap sel berisi satu nilai.",
      comment: "Urutan jelas dari 1NF ke 3NF, penutupnya masih singkat.",
    },
    {
      criterion_id: CR.c4,
      name: "Contoh penerapan",
      weight: 25,
      score: 4,
      quote: "tabel transaksi yang menyimpan nama pelanggan sebaiknya dipisah ke tabel pelanggan",
      comment: "Contoh konkret dan dihubungkan dengan perubahan data.",
    },
  ];
  const aldyFeedback =
    "Tulis juga tujuan normalisasi di pembuka, bukan hanya definisinya. Satu contoh kasus kampus akan memperkuat jawaban Anda.";
  const aldySummary =
    "Jawaban lengkap mencakup ketiga bentuk dengan contoh tepat. Perlu memperjelas tujuan di bagian pembuka.";
  await c.query(
    `INSERT INTO grades (id, submission_id, state, criteria, feedback, summary, nilai, predikat, source, created_by, updated_by, published_at, created_at, updated_at)
     VALUES ($1, $2, 'published', $3::jsonb, $4, $5, 87.50, 'A', 'model', $6, $6, now() - interval '3 days', now() - interval '3 days', now() - interval '3 days')`,
    [G.aldy, S.aldy, JSON.stringify(aldyCriteria), aldyFeedback, aldySummary, U.ramadan],
  );
  await c.query(
    `INSERT INTO grade_revisions (grade_id, snapshot, nilai, predikat, state, changed_by, changed_at)
     VALUES ($1, $2::jsonb, 87.50, 'A', 'published', $3, now() - interval '3 days')`,
    [
      G.aldy,
      JSON.stringify({
        criteria: aldyCriteria,
        feedback: aldyFeedback,
        summary: aldySummary,
      }),
      U.ramadan,
    ],
  );

  // Draft code-graded grade for Ismail's multiple choice ------------------------
  const ismailFeedback = "3 dari 3 jawaban benar.";
  const ismailSummary = "Dinilai otomatis dari kunci jawaban, tanpa model.";
  await c.query(
    `INSERT INTO grades (id, submission_id, state, criteria, feedback, summary, nilai, predikat, source, created_by, updated_by)
     VALUES ($1, $2, 'draft', '[]'::jsonb, $3, $4, 100.00, 'A', 'code', null, null)`,
    [G.ismail, S.ismail, ismailFeedback, ismailSummary],
  );
  await c.query(
    `INSERT INTO grade_revisions (grade_id, snapshot, nilai, predikat, state, changed_by)
     VALUES ($1, $2::jsonb, 100.00, 'A', 'draft', null)`,
    [
      G.ismail,
      JSON.stringify({ criteria: [], feedback: ismailFeedback, summary: ismailSummary }),
    ],
  );

  // Model settings row (first boot only; UI edits win until volume reset) ---
  const env = (name: string): string => (process.env[name] ?? "").trim();
  await c.query(
    `INSERT INTO model_settings
       (id, provider_label, base_url, api_key, model_name,
        emb_base_url, emb_api_key, emb_model_name,
        system_preamble, temperature, max_tokens)
     VALUES (1, $1, $2, $3, $4, $5, $6, $7, $8, 0.20, 1200)
     ON CONFLICT (id) DO NOTHING`,
    [
      env("LLM_PROVIDER_LABEL") || "Penyedia utama",
      env("LLM_BASE_URL"),
      env("LLM_API_KEY"),
      env("LLM_MODEL_NAME"),
      env("EMB_BASE_URL"),
      env("EMB_API_KEY"),
      env("EMB_MODEL_NAME"),
      "Anda adalah asisten penilaian mata kuliah. Balas dalam bahasa Indonesia yang singkat dan jelas.",
    ],
  );
}
