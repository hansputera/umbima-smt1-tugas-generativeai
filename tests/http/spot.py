import sys

from session import BASE, Session

C_BD = "b1000000-0000-4000-8000-000000000001"
TOPIC_BD3 = "c1000000-0000-4000-8000-000000000003"
PG = "d1000000-0000-4000-8000-000000000002"
ESSAY = "d1000000-0000-4000-8000-000000000001"
DINA_SUB = "f1000000-0000-4000-8000-000000000002"

t_miratil = Session(BASE).login("miratil@nilai.test")
t_aldy = Session(BASE).login("aldy@nilai.test")
t_ramadan = Session(BASE).login("ramadan@nilai.test")
t_admin = Session(BASE).login("audyah@nilai.test")

PAGES = [
    ("student", t_miratil, [
        ("/student/home", ["Beranda", "Yang akan datang"]),
        ("/student/courses", ["Kursus saya"]),
        (f"/student/courses/{C_BD}", ["terkumpul", "Indeks kursus"]),
        (f"/student/courses/{C_BD}/peserta", ["Peserta", "Mahasiswa"]),
        (f"/student/courses/{C_BD}/tugas", ["Tenggat", "Status"]),
        (f"/student/courses/{C_BD}/topics/{TOPIC_BD3}", ["Ke mata kuliah", "Materi"]),
        ("/student/tasks", ["Belum dikerjakan"]),
        (f"/student/assignments/{ESSAY}", ["Jawaban Anda", "Pengumpulan terkunci"]),
        (f"/student/assignments/{PG}", ["Navigasi soal"]),
    ]),
    ("student-aldy", t_aldy, [
        (f"/student/courses/{C_BD}/nilai", ["Predikat", "Diterbitkan"]),
    ]),

    ("lecturer", t_ramadan, [
        ("/lecturer/home", ["Beranda", "Yang akan datang"]),
        ("/lecturer/courses", ["Kursus saya", "Kelas"]),
        (f"/lecturer/courses/{C_BD}", ["Tambah pertemuan", "Indeks kursus"]),
        (f"/lecturer/courses/{C_BD}/peserta", ["Dosen", "Mahasiswa"]),
        (f"/lecturer/courses/{C_BD}/tugas", ["Pengumpulan", "Rubrik", "kriteria", "Buka"]),
        (f"/lecturer/courses/{C_BD}/nilai", ["Rata-rata", "Mahasiswa"]),
        (f"/lecturer/courses/{C_BD}/pengaturan", ["Informasi mata kuliah", "Periode", "Kelas"]),
        (f"/lecturer/courses/{C_BD}/topics/{TOPIC_BD3}", ["Ke mata kuliah", "Tugas"]),
        ("/lecturer/submissions", ["Seluruh pengumpulan"]),
        (f"/lecturer/assignments/{ESSAY}", ["Rubrik", "Mode rilis", "Ke pertemuan"]),
        (f"/lecturer/submissions/{DINA_SUB}", ["Jawaban mahasiswa", "Nilai dengan model", "Simpan nilai", "Terbitkan"]),
    ]),
    ("admin", t_admin, [
        ("/admin", ["Ringkasan", "Pengguna", "Mata kuliah", "Setelan model",
                    "Aplikasi", "MiniCourse"]),
        ("/admin/users", ["Pengguna", "Ringkasan", "Impor Excel"]),
        ("/admin/branding", ["Aplikasi", "Nama aplikasi", "Teks footer",
                             "Logo", "Simpan"]),
        ("/admin/courses", ["Mata kuliah", "Ringkasan", "Periode", "Kelas"]),
        (f"/admin/courses/{C_BD}", ["Periode", "Dosen pengampu", "Cari mahasiswa"]),
        ("/admin/periods", ["Periode", "Aktif", "Tambah periode"]),
        ("/admin/placement", ["Penempatan", "Pilih mahasiswa"]),
        ("/admin/settings", ["Penilaian model", "Embedding", "Ringkasan"]),
    ]),
]

# guest checks (no session)
guest = [
    ("/login", ["Masuk", "Email", "Kata sandi"]),
]

fails = 0
for role, sess, pages in PAGES:
    for path, expects in pages:
        code, body = sess.get(path)
        missing = [e for e in expects if e not in body]
        ok = code == 200 and not missing
        if not ok:
            fails += 1
        print(("PASS " if ok else "FAIL ") + f"[{role}] {path}"
              + ("" if ok else f"  status={code} missing={missing}"))

guest_sess = Session(BASE)
for path, expects in guest:
    code, body = guest_sess.get(path)
    missing = [e for e in expects if e not in body]
    ok = code == 200 and not missing
    if not ok:
        fails += 1
    print(("PASS " if ok else "FAIL ") + f"[guest] {path}"
          + ("" if ok else f"  status={code} missing={missing}"))

sys.exit(1 if fails else 0)
