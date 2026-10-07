"""Phase 3 academics admin pages verification (Django test client)."""
import os
import sys

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nilai.settings")

import django

django.setup()

from django.test import Client  # noqa: E402

from accounts.models import User  # noqa: E402
from academics.models import Course, CourseLecturer, Enrollment, Period  # noqa: E402

ok = 0
fail = []


def check(name, cond, extra=""):
    global ok
    if cond:
        ok += 1
    else:
        fail.append(f"{name} {extra}"[:300])


c = Client()
from django.contrib.auth import get_user_model  # noqa: E402

au = get_user_model().objects.get(email="audyah@nilai.test")
c.force_login(au)

# --- Periods page
r = c.get("/admin/periods")
check("periods 200", r.status_code == 200, r.status_code)
t = r.content.decode()
check("periods title", "Tahun ajaran / semester akademik. Kelas mata kuliah ditautkan ke satu periode." in t)
check("periods add btn", "Tambah periode" in t)
check("periods th", all(x in t for x in [">Nama<", ">Status<", ">Jumlah kelas<", ">Aksi<"]))
check("periods crumb", "Periode" in t)
check("periods active dot", "Aktif" in t or "Nonaktif" in t)

# form panel
r = c.get("/admin/periods?form=new")
check("periods form", "Tambah periode" in r.content.decode() and 'id="p-name"' in r.content.decode())

# validation: empty name
r = c.post("/admin/periods", {"action": "save", "name": ""})
t = r.content.decode()
check("periods err empty", "Nama periode wajib diisi." in t)

# validation: >60
r = c.post("/admin/periods", {"action": "save", "name": "x" * 61})
check("periods err len", "Nama periode maksimal 60 karakter." in r.content.decode())

# create
r = c.post("/admin/periods", {"action": "save", "name": "2026/2027 Genap"}, follow=True)
check("periods create", "2026/2027 Genap" in r.content.decode())
p = Period.objects.get(name="2026/2027 Genap")

# duplicate
r = c.post("/admin/periods", {"action": "save", "name": "2026/2027 genap"})
check("periods dup", "Nama periode sudah dipakai." in r.content.decode())

# edit form prefilled
r = c.get(f"/admin/periods?form={p.id}")
check("periods edit prefilled", f'value="{p.name}"' in r.content.decode())

# htmx activate
prior_active = Period.objects.filter(is_active=True).first()
r = c.post(
    "/admin/periods",
    {"action": "activate", "id": str(p.id)},
    HTTP_HX_REQUEST="true",
)
t = r.content.decode()
check("periods htmx table", 'id="periods-table"' in t, t[:200])
check("periods htmx oob", 'id="row-error" hx-swap-oob="true"' in t)
p.refresh_from_db()
check("periods activated", p.is_active is True)
other = Period.objects.filter(is_active=True).exclude(id=p.id)
check("periods old deactivated", not other.exists())

# htmx delete active -> error via oob
r = c.post(
    "/admin/periods",
    {"action": "delete", "id": str(p.id)},
    HTTP_HX_REQUEST="true",
)
check(
    "periods delete active err",
    "Tidak bisa menghapus periode aktif." in r.content.decode(),
)

# plain POST delete active -> flash + redirect
r = c.post("/admin/periods", {"action": "delete", "id": str(p.id)})
check("periods plain delete redirect", r.status_code == 302)

# reactivate the originally-active period to not break others, delete ours
Period.objects.update(is_active=False)
prior_active.is_active = True
prior_active.save()
r = c.post("/admin/periods", {"action": "delete", "id": str(p.id)})
check("periods delete ok", not Period.objects.filter(id=p.id).exists())

# --- Courses page
r = c.get("/admin/courses")
t = r.content.decode()
check("courses 200", r.status_code == 200, r.status_code)
check("courses desc", "Kelas mata kuliah per periode, beserta dosen pengampu dan mahasiswanya." in t)
check("courses add btn", "Tambah kelas" in t)
check("courses counter", "kelas</p>" in t)
check("courses filter", "Semua periode" in t)

r = c.get("/admin/courses?form=new")
t = r.content.decode()
check("courses form", 'id="c-code"' in t and 'id="c-sks"' in t and "Simpan" in t)

# invalid semester (Node Number parity: 1.5 is not integer)
active_p = Period.objects.filter(is_active=True).first() or Period.objects.first()
r = c.post(
    "/admin/courses",
    {
        "action": "save",
        "code": "XX99",
        "name": "Tes",
        "period_id": str(active_p.id),
        "section": "A",
        "semester": "1.5",
        "sks": "3",
    },
)
check("courses err semester", "Semester harus 1–14." in r.content.decode())

r = c.post(
    "/admin/courses",
    {
        "action": "save",
        "code": "XX99",
        "name": "Tes Paritas",
        "period_id": str(active_p.id),
        "section": "A",
        "semester": "4",
        "sks": "3",
    },
    follow=True,
)
t = r.content.decode()
check("courses create", "Tes Paritas" in t and "XX99" in t)
course = Course.objects.get(code="XX99")

# dup
r = c.post(
    "/admin/courses",
    {
        "action": "save",
        "code": "xx99",
        "name": "Lain",
        "period_id": str(course.period_id),
        "section": "a",
        "semester": "4",
        "sks": "3",
    },
)
check("courses dup", "Kelas untuk kode, periode, dan seksi ini sudah ada." in r.content.decode())

# --- Course detail
r = c.get(f"/admin/courses/{course.id}")
t = r.content.decode()
check("detail 200", r.status_code == 200, r.status_code)
check("detail header", "XX99 — Tes Paritas" in t)
check("detail labels", all(x in t for x in ["Dosen pengampu", "Mahasiswa", "Cari dosen", "Cari mahasiswa"]))
check("detail empty msg", "Tidak ada dosen yang cocok." in t and "Tidak ada mahasiswa yang cocok." in t)
check("detail crumbs", "Mata kuliah" in t and "XX99" in t)

lect = User.objects.filter(role="lecturer", status="active").first()
stud = User.objects.filter(role="student", status="active").first()

# htmx toggle lecturer on
r = c.post(
    f"/admin/courses/{course.id}",
    {"action": "toggle_lecturer", "user_id": str(lect.id)},
    HTTP_HX_REQUEST="true",
)
t = r.content.decode()
check("detail htmx lect row", 'class="pick-check"' in t and '"user_id"' in t)
check("detail htmx checked", "checked" in t)
check("detail htmx oob", 'id="row-error" hx-swap-oob="true"' in t)
check("detail joined", CourseLecturer.objects.filter(course_id=course.id, user_id=lect.id).exists())

# htmx toggle off
r = c.post(
    f"/admin/courses/{course.id}",
    {"action": "toggle_lecturer", "user_id": str(lect.id)},
    HTTP_HX_REQUEST="true",
)
check("detail toggled off", "checked" not in r.content.decode())
check("detail removed", not CourseLecturer.objects.filter(course_id=course.id, user_id=lect.id).exists())

# plain POST toggle student on + redirect
r = c.post(
    f"/admin/courses/{course.id}",
    {"action": "toggle_enrollment", "student_id": str(stud.id)},
)
check("detail plain toggle redirect", r.status_code == 302)
check("detail enrolled", Enrollment.objects.filter(course_id=course.id, student_id=stud.id).exists())

# --- Placement page
r = c.get("/admin/placement")
t = r.content.decode()
check("placement 200", r.status_code == 200, r.status_code)
check("placement desc", "Tempatkan mahasiswa ke kelas tiap periode. Penempatan hanya diatur admin." in t)
check("placement pick", "Pilih mahasiswa" in t)
check("placement hint", "Pilih mahasiswa terlebih dahulu." in t)
check("placement th", "Terdaftar" in t)
check("placement row", "XX99" in t)
check("placement aria", "Daftarkan ke XX99 kelas A" in t)
check("placement student row", stud.email in t)

# select student via GET
r = c.get(f"/admin/placement?student={stud.id}")
t = r.content.decode()
check("placement selected", f"Penempatan untuk {stud.name}" in t)

# htmx toggle on
Enrollment.objects.filter(course_id=course.id, student_id=stud.id).delete()
r = c.post(
    "/admin/placement",
    {"action": "toggle", "course_id": str(course.id), "student_id": str(stud.id)},
    HTTP_HX_REQUEST="true",
)
t = r.content.decode()
check("placement htmx input root", t.lstrip().startswith("<input"), t[:80])
check("placement htmx checked", "checked" in t)
check("placement htmx oob", 'id="row-error" hx-swap-oob="true"' in t)
check("placement htmx count oob", 'id="placement-count" class="pick-meta" hx-swap-oob="outerHTML"' in t)
check("placement toggled", Enrollment.objects.filter(course_id=course.id, student_id=stud.id).exists())

# htmx toggle off
r = c.post(
    "/admin/placement",
    {"action": "toggle", "course_id": str(course.id), "student_id": str(stud.id)},
    HTTP_HX_REQUEST="true",
)
check("placement off", "checked" not in r.content.decode())

# --- role gate
c2 = Client()
c2.force_login(User.objects.filter(role="student").first())
for url in ["/admin/periods", "/admin/courses", "/admin/placement", f"/admin/courses/{course.id}"]:
    r = c2.get(url, follow=False)
    check(f"gate {url}", r.status_code == 302 and r["Location"] == "/student/home", (r.status_code, r.get("Location")))

# cleanup test course
CourseLecturer.objects.filter(course_id=course.id).delete()
Enrollment.objects.filter(course_id=course.id).delete()
course.delete()

print(f"PASSED: {ok}")
if fail:
    print("FAILED:")
    for f_ in fail:
        print(" -", f_)
    sys.exit(1)
print("ALL OK")
