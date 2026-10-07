"""Phase 5a verification: student pages (Django test client)."""
import html
import os
import sys

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nilai.settings")

import django

django.setup()

from django.test import Client  # noqa: E402

from accounts.models import AppSettings, User  # noqa: E402
from academics.models import Course, Enrollment, Topic  # noqa: E402
from assessment.models import Assignment, Grade, Submission  # noqa: E402
from nilai.templatetags.nilai_tags import STATUS, fmt_date, fmt_nilai  # noqa: E402

ok = 0
fail = []


def check(name, cond, extra=""):
    global ok
    if cond:
        ok += 1
    else:
        fail.append(f"{name} {extra}"[:300])


def get(client, path):
    r = client.get(path)
    return r, html.unescape(r.content.decode())


APP = AppSettings.objects.get(id=1).app_name
C1 = Course.objects.get(code="IF201", section="A")
C2 = Course.objects.get(code="IF315")
C3 = Course.objects.get(code="IF201", section="B")
aldy = User.objects.get(email="aldy@nilai.test")

topics = {t.week: t for t in Topic.objects.filter(course=C1).order_by("week")}
BD1, BD2, BD3 = topics[1], topics[2], topics[3]
ESSAY = Assignment.objects.get(title="Esai: bentuk normalisasi")
PG = Assignment.objects.get(title="Pilihan ganda: kueri JOIN")
DOCX = Assignment.objects.get(title="Unggah rancangan skema (DOCX)")
PDF = Assignment.objects.get(title="Unggah laporan analisis (PDF)")
SUB_ESSAY = Submission.objects.get(assignment=ESSAY, student=aldy)
GRADE = Grade.objects.get(submission__student=aldy, state="published")

# ---------- gates ----------
anon = Client()
r = anon.get("/student/home")
check("anon GET home gate", r.status_code == 302 and r["Location"] == "/login", r.get("Location"))
r = anon.post("/student/home")
check("anon POST home gate", r.status_code == 302 and r["Location"] == "/login", r.get("Location"))
r = anon.get("/student/tasks")
check("anon GET tasks gate", r.status_code == 302 and r["Location"] == "/login", r.get("Location"))

ram = Client()
ram.force_login(User.objects.get(email="ramadan@nilai.test"))
r = ram.get("/student/home")
check("lecturer GET home gate", r.status_code == 302 and r["Location"] == "/lecturer/home", r.get("Location"))
r = ram.post("/student/home")
check("lecturer POST home gate", r.status_code == 302 and r["Location"] == "/lecturer/home", r.get("Location"))
r = ram.get(f"/student/courses/{C1.id}")
check("lecturer course gate", r.status_code == 302 and r["Location"] == "/lecturer/home", r.get("Location"))

adm = Client()
adm.force_login(User.objects.get(email="audyah@nilai.test"))
r = adm.get("/student/home")
check("admin GET home gate", r.status_code == 302 and r["Location"] == "/admin", r.get("Location"))
r = adm.post("/student/tasks")
check("admin POST tasks gate", r.status_code == 302 and r["Location"] == "/admin", r.get("Location"))

a = Client()
a.force_login(aldy)
r = a.get("/lecturer/home")
check("student crosses to lecturer", r.status_code == 302 and r["Location"] == "/student/home", r.get("Location"))

# ---------- home ----------
r, t = get(a, "/student/home")
check("home 200", r.status_code == 200, r.status_code)
check("home h1", "<h1>Beranda</h1>" in t)
check("home desc", "Selamat datang, Aldy." in t)
check("home crumb last", '<span class="crumb is-last">Beranda</span>' in t)
check("home crumb no link", 'class="crumb-link"' not in t)
check("home nav", 'class="nav-link is-active" href="/student/home"' in t)
check("home 2 cards", t.count('<div class="course-card">') == 2, t.count('<div class="course-card">'))
check("home card code", '<span class="course-card-code">IF201</span>' in t)
check("home card name", '<span class="course-card-name">Basis Data</span>' in t)
meta1 = f"Semester 4 · 3 SKS · Kelas A · {C1.period.name} · Ramadan Agung Wibawa"
check("home card meta", meta1 in t, meta1)
check("home card sr", '<span class="sr-only">IF201 — Basis Data</span>' in t)
check("home card aktif", t.count(">Aktif</span>") >= 2, t.count(">Aktif</span>"))
check("home progress label", t.count('<span class="progress-label">Tugas dinilai</span>') == 2)
check("home progress 1/2", '<span class="progress-value">1/2</span>' in t)
check("home progress 0/2", '<span class="progress-value">0/2</span>' in t)
check("home progress 50", '<span style="width: 50%"></span>' in t)
check("home progress 0", '<span style="width: 0%"></span>' in t)
check("home no lecturer label", "Tugas ada pengumpulan" not in t)
check("home upcoming head", 'rail-block-head">Yang akan datang</div>' in t)
check("home upcoming 3", t.count('class="rail-item"') == 3, t.count('class="rail-item"'))
order = t.index(str(PG.id)) < t.index(str(PDF.id)) < t.index(str(DOCX.id))
check("home upcoming order", order)
check(
    "home upcoming meta",
    f"IF201 · Pilihan ganda · Tenggat {fmt_date(PG.due_at)}" in t,
)
check(
    "home upcoming pdf meta",
    f"IF315 · Unggah PDF · Tenggat {fmt_date(PDF.due_at)}" in t,
)
check("home upcoming no essay", "Esai: bentuk normalisasi" not in t)
check("home upcoming icon40", "width:40px" in t)

# draft submission is upcoming again
SUB_ESSAY.status = "draft"
SUB_ESSAY.save()
r, t = get(a, "/student/home")
check("home draft 4", t.count('class="rail-item"') == 4, t.count('class="rail-item"'))
check("home draft first", t.index(str(ESSAY.id)) < t.index(str(PG.id)))
check("home draft meta", f"IF201 · Esai · Tenggat {fmt_date(ESSAY.due_at)}" in t)
SUB_ESSAY.status = "submitted"
SUB_ESSAY.save()

# all deadlines past
orig_due = {x.id: x.due_at for x in (ESSAY, PG, DOCX, PDF)}
import datetime as _dt

past = _dt.datetime(2020, 1, 1, tzinfo=_dt.timezone.utc)
for x in (ESSAY, PG, DOCX, PDF):
    x.due_at = past
    x.save()
r, t = get(a, "/student/home")
check("home past empty", 'rail-empty">Tidak ada tenggat mendatang.</p>' in t)
check("home past 0 rows", t.count('class="rail-item"') == 0)
for x in (ESSAY, PG, DOCX, PDF):
    x.due_at = orig_due[x.id]
    x.save()
r, t = get(a, "/student/home")
check("home due restored", t.count('class="rail-item"') == 3)

# ---------- empty new student ----------
newu = User.objects.create(name="Mahasiswa Baru", email="baru@nilai.test", role="student", password="x")
b = Client()
b.force_login(newu)
r, t = get(b, "/student/home")
check("empty home 200", r.status_code == 200, r.status_code)
check("empty home desc", "Selamat datang, Mahasiswa Baru." in t)
check("empty home cards", t.count('<div class="course-card">') == 0)
check(
    "empty home msg",
    "Belum ada mata kuliah. Hubungi dosen ya supaya bisa ikut kelas." in t,
)
check("empty home rail", 'rail-empty">Tidak ada tenggat mendatang.</p>' in t)

r, t = get(b, "/student/courses")
check("empty courses 200", r.status_code == 200, r.status_code)
check("empty courses h1", "<h1>Kursus saya</h1>" in t)
check("empty courses desc", "Mata kuliah yang Anda ikuti." in t)
check("empty courses msg", "Belum ada mata kuliah. Hubungi dosen ya supaya bisa ikut kelas." in t)
check("empty courses crumb", '<span class="crumb is-last">Kursus saya</span>' in t)
check("empty courses nav", 'class="nav-link is-active" href="/student/courses"' in t)

r, t = get(b, "/student/tasks")
check("empty tasks desc", "Semua tugas dari mata kuliah yang Anda ikuti." in t)
check(
    "empty tasks msg",
    "Belum ada tugas nih. Begitu dosen menambahkannya, tugas akan muncul di sini." in t,
)
check("empty tasks no sections", "<h2>Belum dikerjakan</h2>" not in t)

# ---------- courses (aldy) ----------
r, t = get(a, "/student/courses")
check("courses 200", r.status_code == 200, r.status_code)
check("courses h1", "<h1>Kursus saya</h1>" in t)
check("courses desc", "Mata kuliah yang Anda ikuti." in t)
check("courses 2 cards", t.count('<div class="course-card">') == 2)
check("courses crumb", '<span class="crumb is-last">Kursus saya</span>' in t)
check("courses nav", 'class="nav-link is-active" href="/student/courses"' in t)
check("courses meta if315", f"Semester 6 · 3 SKS · Kelas A · {C2.period.name} · Ramadan Agung Wibawa" in t)

# ---------- course page ----------
r, t = get(a, f"/student/courses/{C1.id}")
check("course 200", r.status_code == 200, r.status_code)
check("course crumb root", f'<a class="crumb-link" href="/student/home">{APP}</a>' in t)
check("course crumb kursus", '<a class="crumb-link" href="/student/courses">Kursus</a>' in t)
check("course crumb last", '<span class="crumb is-last">IF201</span>' in t)
check("course title", '<h1 class="course-title">Basis Data</h1>' in t)
check("course sub", '<p class="course-sub">IF201 · Semester 4 · 3 SKS</p>' in t)
base = f"/student/courses/{C1.id}"
check("course tab aktif", f'class="course-tab is-active" href="{base}">Kursus</a>' in t)
check("course tab peserta", f'<a class="course-tab" href="{base}/peserta">Peserta</a>' in t)
check("course tab tugas", f'<a class="course-tab" href="{base}/tugas">Tugas</a>' in t)
check("course tab nilai", f'<a class="course-tab" href="{base}/nilai">Nilai</a>' in t)
check("course no pengaturan", "Pengaturan" not in t)
check("course nav", 'class="nav-link is-active" href="/student/courses"' in t)
check("course index head", '<span class="label">Indeks kursus</span>' in t)
check(
    "course index course",
    f'<a class="course-index-course" href="{base}">IF201 — Basis Data</a>' in t,
)
check("course index topics", t.count('class="course-index-topic') == 3, t.count('class="course-index-topic'))
for w, tp in ((1, BD1), (2, BD2), (3, BD3)):
    check(
        f"course topic card {w}",
        f'<a class="topic-card-title" href="{base}/topics/{tp.id}">Pertemuan {w}: {tp.title}</a>' in t,
    )
check("course badge 1/1", '<span class="topic-card-count">1/1 terkumpul</span>' in t)
check("course badge 0/1", '<span class="topic-card-count">0/1 terkumpul</span>' in t)
check("course badge count", t.count('class="topic-card-count"') == 2, t.count('class="topic-card-count"'))
check("course materi rows", t.count('<span class="topic-item-meta">Materi</span>') == 6, t.count("Materi"))
check(
    "course essay sub",
    f'<span class="topic-item-meta">Esai · Tenggat {fmt_date(ESSAY.due_at)}</span>' in t,
)
check(
    "course pg sub",
    f'<span class="topic-item-meta">Pilihan ganda · Tenggat {fmt_date(PG.due_at)}</span>' in t,
)
check("course essay nilai", '<span class="topic-item-nilai">87.50</span>' in t)
check("course essay ok icon", '<span class="ic-ok">' in t)
check("course pg circle", '<span class="ic-faint">' in t)
check("course sr submitted", '<span class="sr-only">Sudah dikumpulkan</span>' in t)
check("course sr unsubmitted", '<span class="sr-only">Belum dikumpulkan</span>' in t)
check(
    "course item href essay",
    f'<a class="topic-item" href="/student/assignments/{ESSAY.id}">' in t,
)
# rail regions
i1 = t.index("Yang akan datang")
i2 = t.index("Nilai terbaru")
rail1 = t[i1:i2]
rail2 = t[i2:]
check("rail upcoming 1", rail1.count('class="rail-item"') == 1, rail1.count('class="rail-item"'))
check("rail upcoming meta", f"Pilihan ganda · Tenggat {fmt_date(PG.due_at)}" in rail1)
check("rail upcoming no code", "IF201 ·" not in rail1 and "IF315 ·" not in rail1)
check("rail upcoming icon32", "width:32px" in rail1)
check("rail recent 1", rail2.count('class="rail-item rail-item-split"') == 1)
check("rail recent title", "Esai: bentuk normalisasi" in rail2)
check("rail recent date", fmt_date(GRADE.published_at) in rail2)
check("rail recent val", '<span class="rail-item-val">87.50 · A</span>' in rail2)
check("rail recent href", f'href="/student/assignments/{ESSAY.id}"' in rail2)

# ---------- 404s before enrollment ----------
r = a.get(f"/student/courses/{C3.id}")
check("foreign course 404", r.status_code == 404, r.status_code)
r = a.get("/student/courses/not-a-uuid")
check("bad uuid 404", r.status_code == 404, r.status_code)
WEB1 = Topic.objects.get(title="Arsitektur aplikasi web")
r = a.get(f"/student/courses/{C1.id}/topics/{WEB1.id}")
check("foreign topic 404", r.status_code == 404, r.status_code)
r = a.get(f"/student/courses/{C1.id}/topics/00000000-0000-0000-0000-000000000000")
check("missing topic 404", r.status_code == 404, r.status_code)

# ---------- enrolled in empty course ----------
enr = Enrollment.objects.create(course=C3, student=aldy)
try:
    r, t = get(a, f"/student/courses/{C3.id}")
    check("c3 course 200", r.status_code == 200, r.status_code)
    check(
        "c3 empty topics",
        "Belum ada pertemuan nih. Materi dan tugas akan muncul di sini setelah dosen menambahkannya." in t,
    )
    check("c3 index empty", '<p class="course-index-empty">Belum ada pertemuan.</p>' in t)
    check("c3 rail empty", 'rail-empty">Tidak ada tenggat mendatang.</p>' in t)
    check("c3 recent empty", 'rail-empty">Belum ada nilai terbit.</p>' in t)

    r, t = get(a, f"/student/courses/{C3.id}/tugas")
    check("c3 tugas 200", r.status_code == 200, r.status_code)
    check("c3 tugas empty", '<p>Belum ada tugas di kursus ini.</p>' in t)

    r, t = get(a, f"/student/courses/{C3.id}/nilai")
    check("c3 nilai 200", r.status_code == 200, r.status_code)
    check("c3 nilai empty", '<p>Belum ada nilai terbit.</p>' in t)

    r, t = get(a, f"/student/courses/{C3.id}/peserta")
    check("c3 peserta 200", r.status_code == 200, r.status_code)
    check("c3 peserta no dosen", '<p>Belum ada dosen pengampu.</p>' in t)
    check("c3 peserta 1", '<span class="section-action">1 terdaftar</span>' in t)
    check("c3 peserta me", "aldy@nilai.test" in t)
finally:
    enr.delete()

# ---------- tugas page ----------
r, t = get(a, f"/student/courses/{C1.id}/tugas")
check("tugas 200", r.status_code == 200, r.status_code)
check("tugas crumb", '<span class="crumb is-last">Tugas</span>' in t)
check("tugas tab active", f'class="course-tab is-active" href="{base}/tugas">Tugas</a>' in t)
check("tugas th tugas", '<th class="th">Tugas</th>' in t)
check("tugas th tenggat", '<th class="th">Tenggat</th>' in t)
check("tugas th status", '<th class="th">Status</th>' in t)
check("tugas th nilai", '<th class="th th-right">Nilai</th>' in t)
body = t[t.index("<tbody>") : t.index("</tbody>")]
check("tugas rows", body.count('<tr class="tr">') == 2, body.count('<tr class="tr">'))
check(
    "tugas essay link",
    f'<a class="td-link fw500" href="/student/assignments/{ESSAY.id}">Esai: bentuk normalisasi</a>' in body,
)
check("tugas essay week", '<span class="td-sub">Pertemuan 2</span>' in body)
check("tugas pg week", '<span class="td-sub">Pertemuan 3</span>' in body)
check("tugas essay due", f'<td class="td td-muted td-nowrap">{fmt_date(ESSAY.due_at)}</td>' in body)
check("tugas essay order", body.index(str(ESSAY.id)) < body.index(str(PG.id)))
check("tugas essay status", '<span class="status st-ok">' in body and "Dinilai" in body)
check("tugas pg status", '<span class="status st-muted">' in body and ">Belum</span>" in body)
check("tugas essay nilai", '<td class="td td-right fw500">87.50</td>' in body)
check("tugas pg nilai", '<td class="td td-right fw500">—</td>' in body)

# ---------- nilai page ----------
r, t = get(a, f"/student/courses/{C1.id}/nilai")
check("nilai 200", r.status_code == 200, r.status_code)
check("nilai crumb", '<span class="crumb is-last">Nilai</span>' in t)
check("nilai tab active", f'class="course-tab is-active" href="{base}/nilai">Nilai</a>' in t)
check("nilai th", '<th class="th th-right">Nilai</th>' in t)
check("nilai th predikat", '<th class="th">Predikat</th>' in t)
check("nilai th status", '<th class="th">Status</th>' in t)
check("nilai th diterbitkan", '<th class="th">Diterbitkan</th>' in t)
body = t[t.index("<tbody>") : t.index("</tbody>")]
check("nilai rows", body.count('<tr class="tr">') == 1, body.count('<tr class="tr">'))
check("nilai link", f'href="/student/assignments/{ESSAY.id}">Esai: bentuk normalisasi</a>' in body)
check("nilai week", '<span class="td-sub">Pertemuan 2</span>' in body)
check("nilai value", '<td class="td td-right">87.50</td>' in body)
check("nilai predikat", '<td class="td">A</td>' in body)
check("nilai status", '<span class="status st-ok">' in body and "Terbit" in body)
check("nilai date", f'<td class="td td-muted td-nowrap">{fmt_date(GRADE.published_at)}</td>' in body)

r, t = get(a, f"/student/courses/{C2.id}/nilai")
check("nilai empty if315", '<p>Belum ada nilai terbit.</p>' in t)

# ---------- peserta page ----------
r, t = get(a, f"/student/courses/{C1.id}/peserta")
check("peserta 200", r.status_code == 200, r.status_code)
check("peserta crumb", '<span class="crumb is-last">Peserta</span>' in t)
check("peserta tab", f'class="course-tab is-active" href="{base}/peserta">Peserta</a>' in t)
check("peserta dosen h2", "<h2>Dosen</h2>" in t)
check("peserta dosen count", '<span class="section-action">1 orang</span>' in t)
check("peserta dosen name", "Ramadan Agung Wibawa" in t)
check("peserta dosen email", "ramadan@nilai.test" in t)
check("peserta mhs h2", "<h2>Mahasiswa</h2>" in t)
check("peserta mhs count", '<span class="section-action">4 terdaftar</span>' in t)
for email in ("aldy@nilai.test", "fitri@nilai.test", "ismail@nilai.test", "miratil@nilai.test"):
    check(f"peserta {email}", email in t)
check("peserta no form", 'name="action"' not in t)

# ---------- topic page: essay topic ----------
tp = f"{base}/topics/{BD2.id}"
r, t = get(a, tp)
check("topic 200", r.status_code == 200, r.status_code)
check("topic crumb root", f'<a class="crumb-link" href="/student/home">{APP}</a>' in t)
check("topic crumb kursus", '<a class="crumb-link" href="/student/courses">Kursus</a>' in t)
check("topic crumb course", f'<a class="crumb-link" href="{base}">IF201</a>' in t)
check("topic crumb last", '<span class="crumb is-last">Pertemuan 2</span>' in t)
check("topic title", '<h1 class="course-title">Pertemuan 2: Normalisasi</h1>' in t)
check("topic sub", '<p class="course-sub">IF201 — Basis Data</p>' in t)
check("topic action", f'<a class="btn" href="{base}">Ke mata kuliah</a>' in t)
check("topic tab active", f'class="course-tab is-active" href="{base}">Kursus</a>' in t)
check("topic sidebar active", 'course-index-topic is-active' in t)
check("topic h2 materi", "<h2>Materi</h2>" in t)
check("topic h2 tugas", "<h2>Tugas</h2>" in t)
check("topic mat card", 'class="mat-card"' in t)
check("topic mat items", t.count('<li class="mat-item">') == 2, t.count('<li class="mat-item">'))
check("topic one row", t.count('<a class="assignment-row"') == 1, t.count('<a class="assignment-row"'))
check("topic row href", f'<a class="assignment-row" href="/student/assignments/{ESSAY.id}">' in t)
check("topic row title", '<span class="ar-title">Esai: bentuk normalisasi</span>' in t)
check("topic row sub", '<span class="ar-sub">Esai · Review dulu</span>' in t)
check("topic row dot", '<span class="status st-ok">' in t and "Dinilai" in t)
check("topic row nilai", '<span class="ar-nilai">87.50</span>' in t)
check("topic row action", '<span class="sr-only">Lihat jawaban</span>' in t)
check("topic row icon", "M21.174 6.812a1 1 0 0 0-3.986-3.987" in t)
check("topic nav prev", f'<a class="topic-nav-link" href="{base}/topics/{BD1.id}">' in t)
check("topic nav prev label", "Pertemuan 1: Relasi dan model data" in t)
check("topic nav next", f'<a class="topic-nav-link right" href="{base}/topics/{BD3.id}">' in t)
check("topic nav next label", "Pertemuan 3: Kueri SQL" in t)

# first topic: no prev, empty tugas
tp = f"{base}/topics/{BD1.id}"
r, t = get(a, tp)
check("first topic 200", r.status_code == 200, r.status_code)
check("first topic crumb", '<span class="crumb is-last">Pertemuan 1</span>' in t)
check("first topic no prev", t.count('class="topic-nav-link"') == 0, t.count('class="topic-nav-link"'))
check("first topic has next", t.count('class="topic-nav-link right"') == 1)
check("first topic no rows", '<a class="assignment-row"' not in t)
check(
    "first topic empty tugas",
    "Belum ada tugas di pertemuan ini. Cek pertemuan lain, yuk!" in t,
)
check("first topic mat items", t.count('<li class="mat-item">') == 3, t.count('<li class="mat-item">'))

# last topic (pg): no next, Kerjakan
tp = f"{base}/topics/{BD3.id}"
r, t = get(a, tp)
check("last topic 200", r.status_code == 200, r.status_code)
check("last topic next", t.count('class="topic-nav-link right"') == 0)
check("last topic prev", t.count('class="topic-nav-link"') == 1)
check("last topic action", '<span class="sr-only">Kerjakan</span>' in t)
check("last topic nilai dash", '<span class="ar-nilai">—</span>' in t)
check("last topic sub", '<span class="ar-sub">Pilihan ganda · Review dulu</span>' in t)
check("last topic icon", "m3 17 2 2 4-4" in t)
check("last topic dot", ">Belum</span>" in t)

# temporary empty topic
t9 = Topic.objects.create(course=C1, week=9, title="Percobaan kosong")
try:
    r, t = get(a, f"{base}/topics/{t9.id}")
    check("empty topic 200", r.status_code == 200, r.status_code)
    check("empty topic crumb", '<span class="crumb is-last">Pertemuan 9</span>' in t)
    check("empty topic materi", '<p>Belum ada materi di pertemuan ini.</p>' in t)
    check(
        "empty topic tugas",
        "Belum ada tugas di pertemuan ini. Cek pertemuan lain, yuk!" in t,
    )
    check("empty topic prev", f'href="{base}/topics/{BD3.id}"' in t)
    check("empty topic no next", t.count('class="topic-nav-link right"') == 0)
finally:
    t9.delete()

# ---------- tasks page ----------
r, t = get(a, "/student/tasks")
check("tasks 200", r.status_code == 200, r.status_code)
check("tasks h1", "<h1>Tugas</h1>" in t)
check("tasks desc", '<p class="page-desc">3 tugas belum dikerjakan.</p>' in t)
check("tasks crumb", '<span class="crumb is-last">Tugas</span>' in t)
check("tasks nav", 'class="nav-link is-active" href="/student/tasks"' in t)
check("tasks h2 todo", "<h2>Belum dikerjakan</h2>" in t)
check("tasks h2 done", "<h2>Sudah dikumpulkan</h2>" in t)
i1 = t.index("Belum dikerjakan")
i2 = t.index("Sudah dikumpulkan")
todo = t[i1:i2]
done = t[i2:]
check("tasks todo rows", todo.count('<a class="assignment-row"') == 3, todo.count('<a class="assignment-row"'))
check("tasks todo order", todo.index(str(PG.id)) < todo.index(str(DOCX.id)) < todo.index(str(PDF.id)))
check("tasks todo sub pg", '<span class="ar-sub">IF201 · Pertemuan 3</span>' in todo)
check("tasks todo sub docx", '<span class="ar-sub">IF315 · Pertemuan 1</span>' in todo)
check("tasks todo sub pdf", '<span class="ar-sub">IF315 · Pertemuan 2</span>' in todo)
check("tasks todo kerjakan", todo.count('<span class="sr-only">Kerjakan</span>') == 3)
check("tasks todo dot", ">Belum</span>" in todo)
check("tasks todo nilai", '<span class="ar-nilai">—</span>' in todo)
check("tasks todo icons", "m3 17 2 2 4-4" in todo and "M12 12v6" in todo and "M12 18v-6" in todo)
check("tasks done rows", done.count('<a class="assignment-row"') == 1, done.count('<a class="assignment-row"'))
check("tasks done essay", '<span class="ar-title">Esai: bentuk normalisasi</span>' in done)
check("tasks done sub", '<span class="ar-sub">IF201 · Pertemuan 2</span>' in done)
check("tasks done action", '<span class="sr-only">Lihat jawaban</span>' in done)
check("tasks done nilai", '<span class="ar-nilai">87.50</span>' in done)
check("tasks done dot", "Dinilai" in done)
check("tasks done icon", "M21.174 6.812a1 1 0 0 0-3.986-3.987" in done)

# all submitted
created = [
    Submission.objects.create(assignment=x, student=aldy, status="draft")
    for x in (PG, DOCX, PDF)
]
try:
    r, t = get(a, "/student/tasks")
    check("tasks all desc", '<p class="page-desc">Semua tugas sudah dikumpulkan.</p>' in t)
    check(
        "tasks all box",
        '<p>Semua tugas sudah dikumpulkan. Kerja bagus!</p>' in t,
    )
    check("tasks all todo 0", t.count('<a class="assignment-row"') == 4, t.count('<a class="assignment-row"'))
    check("tasks all done section", "<h2>Sudah dikumpulkan</h2>" in t)
    check("tasks all draft", ">Draft</span>" in t)
finally:
    for s in created:
        s.delete()
r, t = get(a, "/student/tasks")
check("tasks restored desc", '<p class="page-desc">3 tugas belum dikerjakan.</p>' in t)
check("tasks restored rows", t.count('<a class="assignment-row"') == 4)

# ---------- seed integrity ----------
check("integrity submissions", Submission.objects.count() == 4, Submission.objects.count())
check("integrity grades", Grade.objects.count() == 2, Grade.objects.count())
check("integrity aldy enroll", Enrollment.objects.filter(student=aldy).count() == 2)
check("integrity topics", Topic.objects.count() == 5, Topic.objects.count())
check("integrity assignments", Assignment.objects.count() == 4, Assignment.objects.count())
check("integrity essay status", Submission.objects.get(id=SUB_ESSAY.id).status == "submitted")
check("integrity no temp topic", not Topic.objects.filter(week=9).exists())
newu.delete()
check("integrity no temp user", not User.objects.filter(email="baru@nilai.test").exists())

print(f"PASS {ok}  FAIL {len(fail)}")
for f in fail:
    print("  -", f)
sys.exit(1 if fail else 0)
