# Analisis `tools/grade_cli.py`

Analisis lima pertanyaan (variabel, tipe data, `input()`, perhitungan, if-else)
untuk CLI simulasi penilaian di `tools/grade_cli.py`. CLI ini memakai ulang logika
aplikasi (`assessment/ai.py`, `assessment/prompt.py`, `assessment/validate.py`, dan
`assessment/lib.py`) dan tidak memerlukan PostgreSQL.

## 1. Apa fungsi setiap variabel?

- `ROOT` — `Path` root repositori; dimasukkan ke `sys.path` agar paket `assessment`
  dapat diimpor.
- `state` — dict utama (in-memory) yang menampung seluruh status simulasi:
  `assignment`, `rubric`, `questions`, dan `answer`.
- `state["assignment"]` — dict `title`/`type`/`instructions`.
- `state["rubric"]` / `state["questions"]` — list definisi yang diisi dosen.
- `state["answer"]` — dict jawaban mahasiswa (`kind: "essay"` + `text`, atau
  `kind: "pg"` + `choices`).
- `TEMPERATURE`, `MAX_TOKENS` — konstanta parameter panggilan LLM.
- `LEVELS`, `LEVEL_LABELS` — tuple kunci level (`level_1`…`level_4`) dan dict label
  humanis (Dangkal, Sebagian / tanpa penjelasan, Cukup jelas, Lengkap dan tepat).
- Helper input: `label`, `default`, `lo`, `hi`, `choices`, `opts`, `suffix`, `raw`,
  `value`.
- `ask_level`: `score` (nomor skor) dan `name` (label). `premis`: `title` (judul bagian).
- `setup_rubric`: `rubric` (list lokal) dan `total` (jumlah bobot).
- `setup_questions`: `questions` (list lokal).
- `answer_pg`: `choices` (list jawaban mahasiswa).
- `grade_llm`: `settings`, `messages`, `result`, `parsed`, `by_id` (map id→kriteria),
  `criteria`, `entry`, `c`, `nilai`.
- `grade_pg`: `questions`, `choices`, `total` (jumlah soal), `correct` (jumlah benar),
  `nilai`, `got`, `mark`, `i`, `q`.
- `grade_manual`: `criteria`, `c`, `feedback`, `score`, `lv`.
- `main`: `choice` (pilihan menu).

## 2. Apa tipe data yang digunakan?

- `int` — `lo`/`hi`/`value`, `weight`, `score`, `total`, `correct`.
- `float` — `nilai` (hasil `compute_nilai` / `math.floor`).
- `str` — `label`, `default`, `raw`, `title`, `name`, teks jawaban, `kind`,
  `base_url`/`api_key`/`model_name`, `predikat`, `mark`.
- `bool` — hasil `raw in choices`, `model_configured(...)`, dan hasil tiap kondisi.
- `list` — `rubric`, `questions`, `choices`, `criteria`.
- `dict` — `state`, `assignment`, item rubrik, `answer`, `result`, `parsed`.
- `tuple` — `LEVELS`, `("essay", "pg")`, `("y", "n")`.
- `Path` — `ROOT`.
- `SimpleNamespace` — `settings` (shim konfigurasi LLM dari environment).
- `NoneType` — `answer` awal `None`, `default=None`.

## 3. Mengapa menggunakan input()?

Karena ini program CLI interaktif — kebalikan dari aplikasi web. Tidak ada server
atau HTTP, sehingga satu-satunya jalur masukan adalah keyboard lewat `input()`.
Fungsi ini dipakai di `ask`, `ask_int`, `ask_choice`, `ask_level`, dan
`input("Pilih menu: ")`. Konsekuensinya, `input()` selalu mengembalikan **string**,
sehingga konversi (`int(raw)`) dan validasi berulang harus dilakukan manual — itulah
sebabnya setiap helper pembaca masukan memakai loop sampai nilai valid.

## 4. Bagaimana proses perhitungannya?

CLI tidak menghitung sendiri; ia memanggil fungsi aplikasi agar hasilnya identik:

- `compute_nilai(criteria)` = `Σ (score/4 × weight)`, dibulatkan dengan
  `floor(total × 100 + 0.5) / 100` — dipakai jalur LLM dan manual.
- Jalur PG: `total = len(questions)`, `correct = Σ (jawaban == kunci)`,
  `nilai = floor((correct/total) × 10000 + 0.5) / 100`.
- Hasil `nilai` dipetakan ke `predikat` lewat `predikat_of(nilai)`, lalu ditampilkan
  oleh `show_result`.

## 5. Mengapa menggunakan if-else?

- `main()` — dispatch menu: `if/elif choice == "1" …` memilih aksi yang dijalankan.
- Guard di `grade_llm`/`grade_pg`/`grade_manual` — memvalidasi prasyarat (tugas,
  rubrik, jawaban, konfigurasi model) dengan *early return* dan pesan yang jelas.
- Helper input (`ask`, `ask_int`, `ask_choice`) — loop validasi sampai masukan benar.
- `grade_llm` — `if not result["ok"]` (gagal memanggil model) dan
  `if not parsed["ok"]` (respons tidak valid); `if c is None: continue`.
- `ask_level` — `return raw or name` (memakai label default bila kosong).
- `predikat_of` yang dipanggil juga bertumpu pada if-else berantai.

Singkatnya: pada aplikasi web, masukan datang dari HTTP dan perhitungan dipicu oleh
request; pada CLI ini, `input()` dan `if-else` yang mengemudikan seluruh alur.
