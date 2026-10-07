# Analisis Logika Perhitungan Nilai

Analisis berikut mengacu pada logika nyata di dalam codebase ini, khususnya
`assessment/lib.py` (`compute_nilai`, `predikat_of`) dan `assessment/grading.py`
(`compute_grade`, `apply_grade_edits`). Fitur ini adalah bagian aplikasi "Nilai"
(platform penilaian akademik berbantuan AI, Django 5.2 + HTMX) yang paling sesuai
dengan pertanyaan analisis program (variabel, tipe data, masukan, perhitungan, dan
percabangan if-else).

## 1. Apa fungsi setiap variabel?

- `criteria` — daftar kriteria rubrik; tiap elemen berupa dict berisi `score` (1–4)
  dan `weight` (bobot kontribusi terhadap nilai).
- `c` — variabel loop; satu dict kriteria saat iterasi.
- `total` — akumulator nilai terbobot, dimulai dari `0.0`.
- `nilai` — hasil akhir skala 0–100 dengan dua angka desimal.
- `sub` — dict konteks pengumpulan (jawaban, tipe tugas, rubrik, dan data terkait).
- `rubric` — daftar kriteria rubrik dari dosen.
- `questions`, `answers` — daftar soal dan jawaban mahasiswa (jalur pilihan ganda).
- `correct` / `total` (jalur PG) — jumlah jawaban benar / jumlah soal.
- `text` — teks jawaban essay atau teks hasil ekstraksi dokumen.
- `is_file`, `need_rag`, `extraction_ok` — penanda boolean (dokumen?/perlu RAG?/ekstraksi berhasil?).
- `settings` — konfigurasi model AI (`ModelSettings`).
- `messages`, `temperature`, `result`, `parsed`, `entry` — pesan ke LLM, suhu sampling,
  hasil pemanggilan model, hasil parsing JSON, dan satu entri kriteria hasil model.
- `input_` — dict masukan form dosen (scores, quotes, comments, feedback, summary, publish).

## 2. Apa tipe data yang digunakan?

- `int` — `weight`, jumlah soal/jawaban benar, `temperature`/`max_tokens`, skor hasil `int()`.
- `float` — akumulator `total`, konversi `float(score)`, dan `nilai`.
- `str` — teks jawaban, `feedback`, `summary`, `predikat`, `source`.
- `bool` — `is_file`, `need_rag`, `extraction_ok`, `publish`.
- `list` — `criteria`, `rubric`, `questions`, `answers`, `options`.
- `dict` — tiap kriteria, konteks submission, `input_`, hasil `parsed`.
- `Decimal` — kolom `Grade.nilai` (`DecimalField(max_digits=5, decimal_places=2)`).
- `NoneType` — nilai opsional seperti `submitted_at` dan `extracted_text`.

## 3. Mengapa menggunakan input()?

Codebase ini **tidak memakai fungsi bawaan `input()` Python** karena berupa aplikasi
web Django (server), bukan program terminal interaktif. Fungsi `input()` hanya cocok
untuk CLI yang membaca ketikan pengguna secara langsung. Sebagai gantinya, masukan
pengguna masuk lewat permintaan HTTP:

- `request.POST` (mis. `criteria`, `feedback`, `summary`, `intent`) dan `request.FILES`
  (unggah berkas) di `assessment/views_lecturer.py` (`_save_grade`, `_run_grade`).
- Nilai-nilai itu dirapikan menjadi sebuah **dict bernama `input_`** yang dikirim ke
  `apply_grade_edits(submission_id, input_)` di `assessment/grading.py`.

Alasan konseptualnya tetap sama: program perlu menerima masukan dari pengguna (skor
tiap kriteria, umpan balik, jawaban). Bedanya hanya medianya — di sini lewat form/HTTP,
bukan `input()`.

## 4. Bagaimana proses perhitungannya?

Terdapat dua jalur perhitungan:

- **Rubrik (essay/dokumen):** `compute_nilai` menjumlahkan kontribusi tiap kriteria
  `(score/4) × weight`, lalu membulatkan dua desimal dengan cara *half-up*:
  `nilai = floor(total × 100 + 0.5) / 100`. Karena skor 1–4 dan total bobot = 100,
  rentang nilai adalah 0–100.
- **Pilihan ganda (PG):** `compute_grade` menghitung `correct/total × 100` dengan
  pembulatan serupa: `floor((correct/total) × 10000 + 0.5) / 100` (contoh pada uji: 66,67).
- Jika jawaban kosong, semua kriteria diberi skor 1 tanpa memanggil model.
- Hasil `nilai` kemudian dipetakan ke `predikat` dan disimpan ke `Grade`
  (beserta snapshot di `grade_revisions`).

## 5. Mengapa menggunakan if-else?

`if-else` dipakai untuk percabangan keputusan dan penanganan kondisi:

- `predikat_of` memetakan nilai ke huruf: `if nilai >= 85 → A; >= 70 → B; >= 55 → C; else D`.
- `compute_grade` memilih jalur berdasarkan kondisi: apakah `type == "pg"` (dinilai
  otomatis dari kunci), apakah berkas gagal diekstrak, apakah teks kosong, apakah
  rubrik/model/embedding sudah disetel, dan apakah respons model valid — masing-masing
  mengembalikan aksi atau pesan berbeda.
- `apply_grade_edits` memakai `if` untuk validasi (umpan balik wajib diisi, skor harus
  1–4) dan *fallback* ke nilai sebelumnya bila masukan kosong.

Tanpa `if-else`, program tidak dapat memilih cara penilaian yang tepat, memvalidasi
masukan, maupun menangani kegagalan.
