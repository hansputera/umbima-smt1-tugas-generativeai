"""Phase 4 chunk-1 verification: lecturer course pages (Django test client)."""
import html
import json
import os
import re
import sys

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nilai.settings")

import django

django.setup()

from django.test import Client  # noqa: E402

from accounts.models import User  # noqa: E402
from academics.models import Course, MateriBlock, Topic  # noqa: E402
from assessment.models import Assignment, AssignmentQuestion  # noqa: E402

ok = 0
fail = []


def check(name, cond, extra=""):
    global ok
    if cond:
        ok += 1
    else:
        fail.append(f"{name} {extra}"[:300])


BD = "b1000000-0000-4000-8000-000000000001"
WEB = "b1000000-0000-4000-8000-000000000002"
BDB = "b1000000-0000-4000-8000-000000000003"
bd = Course.objects.get(id=BD)
t1 = Topic.objects.get(course=bd, week=1)

# ---------- role gates ----------
c = Client()
r = c.get("/lecturer/home")
check("anon home -> login", r.status_code == 302 and r["Location"] == "/login", r.get("Location"))
r = c.get(f"/lecturer/courses/{BD}")
check("anon course -> login", r.status_code == 302 and r["Location"] == "/login", r.get("Location"))

stu = Client()
stu.force_login(User.objects.get(email="aldy@nilai.test"))
r = stu.get("/lecturer/home")
check("student home gate", r.status_code == 302 and r["Location"] == "/student/home", r.get("Location"))
r = stu.get(f"/lecturer/courses/{BD}")
check("student course gate", r.status_code == 302 and r["Location"] == "/student/home", r.get("Location"))

adm = Client()
adm.force_login(User.objects.get(email="audyah@nilai.test"))
r = adm.get("/lecturer/home")
check("admin home gate", r.status_code == 302 and r["Location"] == "/admin", r.get("Location"))

c = Client()
c.force_login(User.objects.get(email="ramadan@nilai.test"))

# ---------- lecturer home ----------
r = c.get("/lecturer/home")
t = r.content.decode()
check("home 200", r.status_code == 200, r.status_code)
check("home h1", ">Beranda<" in t)
check("home welcome", "Selamat datang, Ramadan Agung Wibawa." in t)
check("home cards", "Basis Data" in t and "Pembangunan Aplikasi Web" in t)
check("home card counts", "3 pertemuan · 2 tugas" in t)
check("home card meta", "Kelas A · 2025/2026 Ganjil" in t)
check("home progress", "Tugas ada pengumpulan" in t and "2/2" in t and "1/2" in t)
check("home status", "Aktif" in t)
check("home upcoming", "Yang akan datang" in t)
check("home upcoming items", "Esai: bentuk normalisasi" in t and "Unggah laporan analisis (PDF)" in t)
check("home no empty", "Belum ada mata kuliah" not in t)
check("home band", "course-card-band" in t)
check("home progress bar", "progress-bar" in t and "width:" in t)

# ---------- courses page ----------
r = c.get("/lecturer/courses")
t = r.content.decode()
check("courses 200", r.status_code == 200)
check("courses header", ">Kursus saya<" in t and "Mata kuliah yang Anda ampu." in t)
check("courses crumb", "Kursus saya" in t)
check("courses cards", t.count("course-card-link") >= 2)
check("courses code", "IF201" in t and "IF315" in t)
check("courses meta", "Kelas A · 2025/2026 Ganjil" in t)
check("courses no empty", "Belum ada mata kuliah" not in t)

# ---------- guards ----------
r = c.get(f"/lecturer/courses/{BDB}")
check("unassigned course", r.status_code == 302 and r["Location"] == "/lecturer/courses", r.get("Location"))
r = c.get(f"/lecturer/courses/{BD}/topics/00000000-0000-4000-8000-000000000000")
check("missing topic", r.status_code == 302 and r["Location"] == "/lecturer/courses", r.get("Location"))

def active_tab(html_text, expected_suffix):
    m = re.search(r'class="course-tab is-active" href="([^"]+)"', html_text)
    if not m:
        return False
    return m.group(1) == f"/lecturer/courses/{BD}" + expected_suffix


# ---------- course page ----------
r = c.get(f"/lecturer/courses/{BD}")
t = r.content.decode()
check("course 200", r.status_code == 200)
check("course h1", ">Basis Data<" in t)
check("course sub", "IF201 · Semester 4 · 3 SKS" in t)
check("course crumb", '"Kursus"' in t or ">Kursus<" in t)
check("course tabs", all(x in t for x in ["Peserta", "Tugas", "Nilai", "Pengaturan"]))
check("course tab active", active_tab(t, ""))
check("course index", "Indeks kursus" in t and "IF201 — Basis Data" in t)
check("course index topics", "Pertemuan 1: Relasi dan model data" in t)
check("course index toggle", "Sembunyikan indeks kursus" in t and "data-index-toggle" in t)
check("course toolbar", "Tambah pertemuan" in t)
check("course topics", "Pertemuan 2: Normalisasi" in t and "Pertemuan 3: Kueri SQL" in t)
check("course topic foot", "Tambah aktivitas" in t)
check("course link item", "Dokumentasi PostgreSQL — tutorial pemula" in t)
check("course file item", "materi-pertemuan-1.pdf" in t)
check("course counts", "2/4 terkumpul" in t and "1/4 terkumpul" in t)
check("course icons", "activity-icon" in t)
check("course rail", "Yang akan datang" in t)
check("course rail items", "Esai: bentuk normalisasi" in t)
check("course no empty", "Belum ada pertemuan" not in t)

r = c.get(f"/lecturer/courses/{BD}?form=new")
t = r.content.decode()
check("course form panel", "Pertemuan baru" in t and 'id="t-title"' in t and 'id="t-week"' in t)

# ---------- create topic ----------
r = c.post(f"/lecturer/courses/{BD}", {"action": "create_topic", "title": "", "week": "4"})
t = r.content.decode()
check("topic err title", "Judul wajib diisi." in t, t[:200])
r = c.post(f"/lecturer/courses/{BD}", {"action": "create_topic", "title": "X", "week": "31"})
check("topic err week range", "Minggu harus 1–30." in r.content.decode())
r = c.post(f"/lecturer/courses/{BD}", {"action": "create_topic", "title": "X", "week": "abc"})
check("topic err week nan", "Minggu harus 1–30." in r.content.decode())
r = c.post(f"/lecturer/courses/{BD}", {"action": "create_topic", "title": "X", "week": "2"})
check("topic err dup", "Minggu sudah dipakai." in r.content.decode())
r = c.post(f"/lecturer/courses/{BD}", {"action": "create_topic", "title": "Percobaan", "week": "4"})
check("topic create", r.status_code == 302, r.status_code)
loc = r.get("Location", "")
check("topic create loc", loc.startswith(f"/lecturer/courses/{BD}/topics/"), loc)
new_tid = loc.rsplit("/", 1)[-1]
check("topic create db", Topic.objects.filter(id=new_tid, week=4, title="Percobaan").exists())
Topic.objects.filter(id=new_tid).delete()
check("topic cleanup", Topic.objects.filter(id=new_tid).count() == 0)

# ---------- peserta ----------
r = c.get(f"/lecturer/courses/{BD}/peserta")
t = r.content.decode()
check("peserta 200", r.status_code == 200)
check("peserta sections", ">Dosen<" in t and ">Mahasiswa<" in t)
check("peserta counts", "1 orang" in t and "4 terdaftar" in t)
t_raw = html.unescape(t)
check(
    "peserta people",
    all(
        x in t_raw
        for x in [
            "Ramadan Agung Wibawa",
            "ramadan@nilai.test",
            "Aldy",
            "Mir'atil Hayati",
            "Ismail Saputra",
            "Fitri Lestari",
        ]
    ),
)
check("peserta tab", active_tab(t, "/peserta"))

# ---------- tugas ----------
r = c.get(f"/lecturer/courses/{BD}/tugas")
t = r.content.decode()
check("tugas 200", r.status_code == 200)
check(
    "tugas head",
    all(
        x in t
        for x in ["Tipe", "Rilis", "Tenggat", "Pengumpulan", "Rubrik", ">Buka<"]
    ),
)
check("tugas essay row", "Esai: bentuk normalisasi" in t and "Pertemuan 2" in t)
check("tugas essay type", ">Esai<" in t and ">Review dulu<" in t)
check("tugas essay count", "2 pengumpulan" in t)
check("tugas rubric ok", "4 kriteria · 100%" in t)
check("tugas pg row", "Pilihan ganda: kueri JOIN" in t and "Pertemuan 3" in t)
check("tugas pg type", ">Pilihan ganda<" in t)
check("tugas pg count", "1 pengumpulan" in t)
check("tugas pg rubric", "td-muted\">—" in t)
check("tugas no empty", "Belum ada tugas di kursus ini." not in t)
check("tugas tab", active_tab(t, "/tugas"))

# ---------- nilai ----------
r = c.get(f"/lecturer/courses/{BD}/nilai")
t = r.content.decode()
check("nilai 200", r.status_code == 200)
check("nilai headers", ">Mahasiswa<" in t and "Esai: bentuk normalisasi" in t and "Pilihan ganda: kueri JOIN" in t)
check(
    "nilai names",
    all(x in html.unescape(t) for x in ["Aldy", "Mir'atil Hayati", "Ismail Saputra", "Fitri Lestari"]),
)
check("nilai published", "87.50" in t)
check("nilai draft", "100 (draf)" in t)
check("nilai empty cell", "td-faint\">—" in t)
check("nilai footer", "Rata-rata" in t and "sheet-foot" in t)
check("nilai no empty", "Belum ada tugas" not in t)
check("nilai tab", active_tab(t, "/nilai"))

# ---------- pengaturan ----------
r = c.get(f"/lecturer/courses/{BD}/pengaturan")
t = r.content.decode()
check("pengaturan 200", r.status_code == 200)
check("pengaturan card", "Informasi mata kuliah" in t)
check(
    "pengaturan desc",
    "Informasi ini diatur oleh admin dan tidak bisa diubah dari sini. Dosen mengelola pertemuan, tugas, rubrik, dan penilaian."
    in t,
)
check(
    "pengaturan rows",
    all(
        x in t
        for x in [
            ">Kode<",
            "IF201",
            ">Nama mata kuliah<",
            ">Periode<",
            "2025/2026 Ganjil",
            ">Kelas<",
            ">Semester<",
            ">SKS<",
            ">Status<",
            "Aktif",
        ]
    ),
)
check("pengaturan tab", active_tab(t, "/pengaturan"))

# ---------- topic detail (GET) ----------
turl = f"/lecturer/courses/{BD}/topics/{t1.id}"
r = c.get(turl)
t = r.content.decode()
check("topic 200", r.status_code == 200)
check("topic h1", "Pertemuan 1: Relasi dan model data" in t)
check("topic sub", "IF201 — Basis Data" in t)
check("topic crumb", "Pertemuan 1" in t)
check("topic active index", "is-active" in t)
check("topic tab", active_tab(t, ""))
check("topic actions", "Ke mata kuliah" in t and "Tambah tugas" in t)
check("topic form values", 'id="td-title" name="title"' in t and 'value="Relasi dan model data"' in t)
check("topic week value", 'id="td-week"' in t and 'value="1"' in t)
check("topic save", "Simpan pertemuan" in t)
check("topic hint", "Tautan materi tersimpan, berkas hanya namanya." in t)
check("topic blocks labels", all(x in t for x in ["Materi 1", "Materi 2", "Materi 3"]))
check("topic block types", all(x in t for x in [">Teks<", ">Tautan<", ">Berkas<"]))
check("topic richtext", "Baca materi model data relasional" in t)
check("topic link", "Dokumentasi PostgreSQL — tutorial pemula" in t)
check("topic link url", "https://www.postgresql.org/docs/current/tutorial-start.html" in t)
check("topic file", "materi-pertemuan-1.pdf" in t)
check("topic submit label", "Simpan pertemuan" in t)
check("topic assign table", all(x in t for x in [">Judul<", ">Mode rilis<", ">Pengumpulan<", ">Aksi<"]))
check("topic no assign empty", "Belum ada tugas di pertemuan ini." not in t)
check("topic create btn", "Buat tugas" not in t)

r = c.get(turl + "?form=new")
t = r.content.decode()
check("topic form new", "Tugas baru" in t and 'id="a-title"' in t and 'id="a-type"' in t)
check("topic form new fields", "Esai: bentuk normalisasi" in t)  # placeholder
check("topic form cancel", ">Batal<" in t)
check("topic form question", 'id="a-question"' in t and ">Pertanyaan<" in t)
check("topic form options", all(x in t for x in ["Esai", "Pilihan ganda", "Unggah PDF", "Unggah DOCX"]))

# ---------- save_topic validations ----------
orig_title, orig_week = t1.title, t1.week
orig_blocks = [
    {"type": b.type, "body": b.body or "", "url": b.url or "", "file_name": b.file_name or ""}
    for b in MateriBlock.objects.filter(topic=t1).order_by("position")
]
orig_json = json.dumps(orig_blocks, ensure_ascii=False)


def post_topic(**data):
    payload = {"action": "save_topic", "topic_id": str(t1.id)}
    payload.update(data)
    return c.post(turl, payload)


r = post_topic(title="", week="1", blocks=orig_json)
check("save err title", "Judul wajib diisi." in r.content.decode(), r.status_code)
r = post_topic(title="Ok", week="31", blocks=orig_json)
check("save err week", "Minggu harus 1–30." in r.content.decode())
r = post_topic(title="Ok", week="2", blocks=orig_json)
check("save err dup", "Minggu sudah dipakai." in r.content.decode())
r = post_topic(title="Ok", week="1", blocks="nope")
check("save err json", "Data materi tidak valid." in r.content.decode())
r = post_topic(title="Ok", week="1", blocks='[{"type":"zzz"}]')
check("save err type", "Materi ke-1: tipe tidak dikenal." in r.content.decode())
r = post_topic(title="Ok", week="1", blocks='[{"type":"richtext","body":"  "}]')
check("save err richtext", "Materi ke-1: teks wajib diisi." in r.content.decode())
r = post_topic(title="Ok", week="1", blocks='[{"type":"link","url":""}]')
check("save err link empty", "Materi ke-1: URL wajib diisi." in r.content.decode())
r = post_topic(title="Ok", week="1", blocks='[{"type":"link","url":"ftp://x"}]')
check("save err link scheme", "Materi ke-1: URL harus diawali http(s)." in r.content.decode())
r = post_topic(title="Ok", week="1", blocks='[{"type":"file"}]')
check("save err file", "Materi ke-1: nama berkas wajib diisi." in r.content.decode())
r = post_topic(title="Ok", week="1", blocks='[{"type":"richtext","body":"x"},{"type":"file"}]')
check("save err block 2", "Materi ke-2: nama berkas wajib diisi." in r.content.decode())

new_blocks = [
    {"type": "richtext", "body": "Isu baru untuk topik."},
    {"type": "link", "body": "Judul tautan", "url": "https://example.com/docs"},
    {"type": "file", "file_name": "catatan.pdf"},
]
r = post_topic(
    title="Relasi dan model data",
    week="1",
    blocks=json.dumps(new_blocks, ensure_ascii=False),
)
t = r.content.decode()
check("save ok", r.status_code == 200 and "Pertemuan disimpan." in t, r.status_code)
db_blocks = list(MateriBlock.objects.filter(topic=t1).order_by("position"))
check("save ok db", len(db_blocks) == 3, len(db_blocks))
if db_blocks:
    check("save ok db richtext", db_blocks[0].type == "richtext" and db_blocks[0].body == "Isu baru untuk topik.")
    check("save ok db link", db_blocks[1].type == "link" and db_blocks[1].url == "https://example.com/docs")
    check("save ok db file", db_blocks[2].type == "file" and db_blocks[2].file_name == "catatan.pdf")

# restore original blocks
MateriBlock.objects.filter(topic=t1).delete()
for i, b in enumerate(orig_blocks):
    MateriBlock.objects.create(
        topic=t1,
        type=b["type"],
        body=b["body"] or None,
        url=b["url"] or None,
        file_name=b["file_name"] or None,
        position=i,
    )
restored = list(MateriBlock.objects.filter(topic=t1).order_by("position"))
check(
    "blocks restored",
    len(restored) == len(orig_blocks)
    and [x.type for x in restored] == [b["type"] for b in orig_blocks],
)

# ---------- create_assignment ----------
def post_assign(**data):
    payload = {"action": "create_assignment", "topic_id": str(t1.id)}
    payload.update(data)
    return c.post(turl, payload)


r = post_assign(title="", type="essay", question="")
t = r.content.decode()
check("assign err title", "Judul wajib diisi." in t)
check("assign err question", "Pertanyaan wajib diisi." in t)
r = post_assign(title="T", type="bogus", question="x")
check("assign err type", "Tipe tidak dikenal." in r.content.decode())
r = post_assign(title="T", type="pg", questions="[]")
check("assign pg empty", "Tulis minimal satu soal." in r.content.decode())
r = post_assign(title="T", type="pg", questions="not-json")
check("assign pg bad json", "Tulis minimal satu soal." in r.content.decode())
r = post_assign(
    title="T",
    type="pg",
    questions=json.dumps([{"question": "", "options": [], "answer_key": ""}]),
)
check("assign pg q empty", "Soal ke-1: teks soal wajib diisi." in r.content.decode())
r = post_assign(
    title="T",
    type="pg",
    questions=json.dumps([{"question": "Q", "options": [{"key": "A", "text": "satu"}], "answer_key": "A"}]),
)
check("assign pg opts", "Soal ke-1: isi minimal dua opsi." in r.content.decode())
r = post_assign(
    title="T",
    type="pg",
    questions=json.dumps(
        [{"question": "Q", "options": [{"key": "A", "text": "a"}, {"key": "B", "text": "b"}], "answer_key": ""}]
    ),
)
check("assign pg key", "Soal ke-1: pilih kunci jawaban dari opsi yang terisi." in r.content.decode())

# re-render keeps values
r = post_assign(title="Judul kirim", type="essay", question="")
t = r.content.decode()
check("assign keeps title", 'value="Judul kirim"' in t)
check("assign keeps open", "Tugas baru" in t)

before = Assignment.objects.count()
r = post_assign(title="Tugas coba esai", type="essay", question="Jelaskan sesuatu.")
check("assign essay ok", r.status_code == 302, r.status_code)
loc = r.get("Location", "")
check("assign essay loc", loc.startswith("/lecturer/assignments/"), loc)
new_aid = loc.rsplit("/", 1)[-1]
a = Assignment.objects.filter(id=new_aid).first()
check("assign essay db", a is not None and a.type == "essay" and a.topic_id == t1.id)
qs = list(AssignmentQuestion.objects.filter(assignment_id=new_aid))
check("assign essay q", len(qs) == 1 and qs[0].question == "Jelaskan sesuatu." and qs[0].options is None)
AssignmentQuestion.objects.filter(assignment_id=new_aid).delete()
Assignment.objects.filter(id=new_aid).delete()

r = post_assign(
    title="Tugas coba pg",
    type="pg",
    questions=json.dumps(
        [
            {
                "question": "Soal pertama?",
                "options": [{"key": "A", "text": "opsi a"}, {"key": "B", "text": "opsi b"}],
                "answer_key": "B",
            }
        ]
    ),
)
check("assign pg ok", r.status_code == 302, r.status_code)
loc = r.get("Location", "")
new_aid2 = loc.rsplit("/", 1)[-1]
qs = list(AssignmentQuestion.objects.filter(assignment_id=new_aid2))
check(
    "assign pg db",
    len(qs) == 1
    and qs[0].answer_key == "B"
    and len(qs[0].options) == 2
    and qs[0].options[1]["text"] == "opsi b",
)
AssignmentQuestion.objects.filter(assignment_id=new_aid2).delete()
Assignment.objects.filter(id=new_aid2).delete()

# ---------- db restored ----------
check("db topics count", Topic.objects.filter(course=bd).count() == 3, Topic.objects.filter(course=bd).count())
check("db topic title", Topic.objects.get(id=t1.id).title == orig_title)
check("db topic week", Topic.objects.get(id=t1.id).week == orig_week)
check("db assignments count", Assignment.objects.filter(topic__course=bd).count() == 2)

# ---------- run twice sanity ----------
r = c.get(turl)
check("topic re-render", r.status_code == 200 and "Pertemuan 1: Relasi dan model data" in r.content.decode())

print(f"PASS {ok}  FAIL {len(fail)}")
for f in fail:
    print("  -", f)
sys.exit(1 if fail else 0)
