"""Phase 5b verification: student assignment detail + submit (Django test client)."""
import html
import os
import sys
from decimal import Decimal
from io import BytesIO

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nilai.settings")

import django

django.setup()

from django.core.files.uploadedfile import SimpleUploadedFile  # noqa: E402
from django.test import Client  # noqa: E402

from accounts.models import User  # noqa: E402
from academics.models import Course, Enrollment  # noqa: E402
from assessment import views_student as VS  # noqa: E402
from assessment.models import Assignment, Grade, Submission  # noqa: E402

ok = 0
fail = []


def check(name, cond, extra=""):
    global ok
    if cond:
        ok += 1
    else:
        fail.append(f"{name} {extra}"[:300])


def get(client, path, cookie=None):
    if cookie is not None:
        client.cookies["nilai_flash"] = cookie
    r = client.get(path)
    return r, html.unescape(r.content.decode())


def post(client, path, data):
    r = client.post(path, data=data)
    return r, html.unescape(r.content.decode())


def make_pdf(text):
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
    ]
    stream = ("BT /F1 24 Tf 72 720 Td (" + text + ") Tj ET").encode()
    objs.append(
        b"<< /Length "
        + str(len(stream)).encode()
        + b" >>\nstream\n"
        + stream
        + b"\nendstream"
    )
    objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, o in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + o + b"\nendobj\n"
    xref_pos = len(out)
    out += f"xref\n0 {len(objs) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_pos}\n%%EOF\n"
    ).encode()
    return bytes(out)


def make_docx(text):
    from docx import Document

    buf = BytesIO()
    doc = Document()
    doc.add_paragraph(text)
    doc.save(buf)
    return buf.getvalue()


ESSAY = Assignment.objects.get(title="Esai: bentuk normalisasi")
PG = Assignment.objects.get(title="Pilihan ganda: kueri JOIN")
PDF = Assignment.objects.get(title="Unggah laporan analisis (PDF)")
DOCX = Assignment.objects.get(title="Unggah rancangan skema (DOCX)")
aldy = User.objects.get(email="aldy@nilai.test")
ismail = User.objects.get(email="ismail@nilai.test")
ramadan = User.objects.get(email="ramadan@nilai.test")
C1 = Course.objects.get(code="IF201", section="A")
C2 = Course.objects.get(code="IF315")

EURL = f"/student/assignments/{ESSAY.id}"
PURL = f"/student/assignments/{PG.id}"
FURL = f"/student/assignments/{PDF.id}"
DURL = f"/student/assignments/{DOCX.id}"

for stale in (
    "baru@nilai.test", "pg1@nilai.test", "pg2@nilai.test", "pdf1@nilai.test",
    "pdf2@nilai.test", "dx1@nilai.test", "dx2@nilai.test",
):
    for u in User.objects.filter(email=stale):
        u.delete()

temp_users = []


def make_student(email, courses):
    u = User.objects.create(
        email=email, name=email.split("@")[0].title(), role="student"
    )
    u.set_password("password123")
    u.save()
    for c in courses:
        Enrollment.objects.create(course=c, student=u)
    temp_users.append(u)
    return u


BASE_SUBS = Submission.objects.count()
BASE_GRADES = Grade.objects.count()
BASE_ENROLL = Enrollment.objects.count()

# ---------- gates & 404s ----------
anon = Client()
r = anon.get(EURL)
check("anon GET gate", r.status_code == 302 and r["Location"] == "/login", r.get("Location"))
r = anon.post(EURL, {"assignment_id": str(ESSAY.id), "answer": "x"})
check("anon POST gate", r.status_code == 302 and r["Location"] == "/login", r.get("Location"))

lec = Client()
lec.force_login(ramadan)
r = lec.get(EURL)
check("lecturer GET gate", r.status_code == 302 and r["Location"] == "/lecturer/home", r.get("Location"))
r = lec.post(EURL, {"assignment_id": str(ESSAY.id), "answer": "x"})
check("lecturer POST gate", r.status_code == 302 and r["Location"] == "/lecturer/home", r.get("Location"))

baru = make_student("baru@nilai.test", [C1])
baru_c = Client()
baru_c.force_login(baru)

r = baru_c.get(DURL)
check("not enrolled GET 404", r.status_code == 404, r.status_code)
r, t = post(baru_c, DURL, {"assignment_id": str(DOCX.id)})
check("not enrolled POST 404", r.status_code == 404, r.status_code)
r = baru_c.get("/student/assignments/not-a-uuid")
check("bad uuid 404", r.status_code == 404, r.status_code)
r = baru_c.get("/student/assignments/11111111-1111-4111-8111-111111111111")
check("unknown uuid 404", r.status_code == 404, r.status_code)

# ---------- essay page: fresh GET ----------
r, t = get(baru_c, EURL)
check("essay 200", r.status_code == 200, r.status_code)
check("essay h1", "<h1>Esai: bentuk normalisasi</h1>" in t)
check("essay sub", "IF201 — Basis Data · Pertemuan 2: Normalisasi" in t)
check("essay type label", 'asg-muted">Esai</span>' in t)
check("essay review mode", "Rilis: Review dulu" in t)
check("essay status belum", ">Belum</span>" in t)
check("essay status hint", "Kerjakan dan kirim jawaban Anda untuk mengumpulkan." in t)
check("essay icon", "M21.174 6.812" in t)
check("essay crumb topic", "Pertemuan 2</a>" in t)
check("essay crumb last", f'class="crumb is-last">{ESSAY.title}</span>' in t)
check(
    "essay ke pertemuan",
    f'href="/student/courses/{C1.id}/topics/{ESSAY.topic_id}"' in t and "Ke pertemuan" in t,
)
check("essay question block", '<span class="label">Pertanyaan</span>' in t)
check("essay question text", "Jelaskan bentuk normalisasi 1NF" in t)
check("essay form h3", "<h3>Kerjakan tugas</h3>" in t)
check(
    "essay textarea",
    'id="sf-answer"' in t and 'placeholder="Tulis jawaban Anda..."' in t and 'rows="8"' in t,
)
check("essay field hint", "Tulis jawaban secara lengkap." in t)
check("essay field label", 'for="sf-answer">Jawaban</label>' in t)
check("essay submit hint", "Setelah dikirim, jawaban terkunci dan tidak dapat diubah lagi." in t)
check("essay hidden id", f'name="assignment_id" value="{ESSAY.id}"' in t)
check("essay no quiz", "data-sf-quiz" not in t)
check("essay no file input", 'type="file"' not in t)
check("essay no grade", "Hasil penilaian" not in t)
check("essay no waiting", "Tenang" not in t)
check("essay no notice", "Terkirim!" not in t)

# ---------- essay submit: errors ----------
r, t = post(baru_c, EURL, {"assignment_id": str(ESSAY.id), "answer": "   "})
check("essay empty 200", r.status_code == 200, r.status_code)
check("essay empty err", "Tulis jawaban terlebih dahulu." in t)
check("essay empty no cookie", "nilai_flash" not in r.cookies, list(r.cookies))
check("essay empty no sub", not Submission.objects.filter(assignment=ESSAY, student=baru).exists())
check("essay empty keeps form", "<h3>Kerjakan tugas</h3>" in t)

r, t = post(baru_c, EURL, {"assignment_id": "not-a-uuid", "answer": "x"})
check("essay bad form id", r.status_code == 200 and "Tugas tidak ditemukan." in t, t[:0])
check("essay bad form keeps form", "<h3>Kerjakan tugas</h3>" in t)
check("essay bad form no cookie", "nilai_flash" not in r.cookies, list(r.cookies))

# ---------- essay submit: success ----------
r, t = post(
    baru_c,
    EURL,
    {"assignment_id": str(ESSAY.id), "answer": "Normalisasi mengurangi redundansi data."},
)
check("essay 302", r.status_code == 302 and r["Location"] == EURL, f"{r.status_code} {r.get('Location')}")
check(
    "essay cookie",
    "nilai_flash" in r.cookies
    and r.cookies["nilai_flash"].value == f"terkirim:{ESSAY.id}:{baru.id}",
    dict(r.cookies),
)
es_sub = Submission.objects.filter(assignment=ESSAY, student=baru).first()
check(
    "essay sub created",
    es_sub is not None
    and es_sub.status == "submitted"
    and es_sub.answer_text == "Normalisasi mengurangi redundansi data."
    and es_sub.submitted_at is not None,
)
check("essay sub no grade", es_sub is not None and not Grade.objects.filter(submission=es_sub).exists())

# ---------- essay flash GET ----------
r, t = get(baru_c, EURL, cookie=f"terkirim:{ESSAY.id}:{baru.id}")
check("flash notice", "Terkirim! Jawaban Anda sudah terkunci dan tidak bisa diubah lagi." in t)
check("flash ok cls", 'class="status st-ok notice"' in t, t[t.find("Terkirim!") - 120:t.find("Terkirim!")])
check("flash waiting", "Tenang, nilai akan terbit setelah dosen me-review jawabanmu." in t)
check("flash lock header", "<h3>Jawaban Anda</h3>" in t)
check("flash lock status", "Pengumpulan terkunci" in t)
check("flash lock sent", "Terkirim " in t)
check("flash answer shown", "Normalisasi mengurangi redundansi data." in t)
check("flash question muted", "lk-q-muted" in t)
check("flash no form", "<h3>Kerjakan tugas</h3>" not in t and "sf-answer" not in t)
check("flash status terkumpul", ">Terkumpul</span>" in t)
check("flash hint", "Menunggu penilaian dosen." in t)
check("flash no grade", "Hasil penilaian" not in t)
check("flash cookie cleared", "nilai_flash" in r.cookies and r.cookies["nilai_flash"].value == "", dict(r.cookies))

r, t = get(baru_c, EURL, cookie=f"terkirim:{ESSAY.id}:{ismail.id}")
check("flash wrong actor", "Terkirim! Jawaban" not in t)

# ---------- essay re-POST locked ----------
r, t = post(baru_c, EURL, {"assignment_id": str(ESSAY.id), "answer": "lagi"})
check("essay locked 200", r.status_code == 200, r.status_code)
check("essay locked view", "<h3>Jawaban Anda</h3>" in t)
check("essay locked no form", "<h3>Kerjakan tugas</h3>" not in t)
check("essay locked no cookie", "nilai_flash" not in r.cookies, list(r.cookies))
check("essay locked count", Submission.objects.filter(assignment=ESSAY, student=baru).count() == 1)
check("essay locked answer kept", "Normalisasi mengurangi redundansi data." in t)

# ---------- essay graded page (aldy, published) ----------
aldy_c = Client()
aldy_c.force_login(aldy)
r, t = get(aldy_c, EURL)
check("aldy 200", r.status_code == 200, r.status_code)
check("aldy status dinilai", ">Dinilai</span>" in t)
check("aldy hint", "Nilai sudah diterbitkan. Periksa hasil penilaian di bawah." in t)
check("aldy no waiting", "Tenang" not in t)
check("aldy lock header", "<h3>Jawaban Anda</h3>" in t)
check("aldy answer", "Normalisasi adalah proses menyusun tabel agar redundansi data berkurang." in t)
check("aldy grade title", "<h3>Hasil penilaian</h3>" in t)
check("aldy grade dot", ">Terbit</span>" in t)
check("aldy nilai", ">87.50" in t)
check("aldy predikat", "Predikat A" in t)
check("aldy crit rows", t.count('class="asg-crit"') == 4, t.count('class="asg-crit"'))
check("aldy crit weight", "bobot 25%" in t)
check("aldy crit name", "Ketepatan konsep" in t)
check("aldy crit comment", "Definisi benar tetapi belum menyebut tujuan" in t)
check("aldy crit score 3", ">3/4</span>" in t)
check("aldy crit score 4", ">4/4</span>" in t)
check("aldy feedback label", "Umpan balik" in t)
check("aldy feedback", "Tulis juga tujuan normalisasi di pembuka" in t)
check("aldy summary label", ">Ringkasan</span>" in t)
check("aldy summary", "Jawaban lengkap mencakup ketiga bentuk" in t)
check("aldy no form", "<h3>Kerjakan tugas</h3>" not in t)
check("aldy no quiz", "data-sf-quiz" not in t)

# ---------- pg page: fresh GET (pg1) ----------
pg1 = make_student("pg1@nilai.test", [C1])
pg1_c = Client()
pg1_c.force_login(pg1)
r, t = get(pg1_c, PURL)
check("pg 200", r.status_code == 200, r.status_code)
check("pg h1", "<h1>Pilihan ganda: kueri JOIN</h1>" in t)
check("pg type label", 'asg-muted">Pilihan ganda</span>' in t)
check("pg no question block", '<span class="label">Pertanyaan</span>' not in t)
check("pg quiz", 'data-sf-quiz' in t and 'data-total="3"' in t)
check("pg navigasi", "Navigasi soal" in t)
check("pg dots", t.count("data-quiz-dot=") == 3, t.count("data-quiz-dot="))
check("pg counter", "Soal 1 dari 3 · sisa 3 soal belum dijawab" in t)
check("pg hint", "Sisa 3 soal belum dijawab." in t)
check("pg q label", '<span class="label">Soal 1</span>' in t)
check("pg hidden 2", t.count("is-hidden") == 2, t.count("is-hidden"))
check("pg radio count", t.count('type="radio"') == 12, t.count('type="radio"'))
check("pg radio names", 'name="choice_0"' in t and 'name="choice_2"' in t)
check("pg answers hidden", 'name="answers" data-sf-answers value="[]"' in t)
check("pg nav buttons", "Sebelumnya</button>" in t and "Selanjutnya</button>" in t)
check("pg counter elem", 'data-quiz-counter' in t)
check("pg question text", "Klausa yang digunakan untuk menggabungkan dua tabel" in t)
check("pg options", "JOIN</span>" in t or "JOIN" in t)
check("pg submit disabled attr", "data-sf-submit" in t)
check("pg no file", 'type="file"' not in t)

# ---------- pg submit: errors ----------
r, t = post(pg1_c, PURL, {"assignment_id": str(PG.id), "answers": "not-json"})
check("pg bad json err", "Jawaban tidak lengkap. Kerjakan seluruh soal." in t)
check("pg bad json no cookie", "nilai_flash" not in r.cookies, list(r.cookies))
r, t = post(pg1_c, PURL, {"assignment_id": str(PG.id), "answers": '["B", ""]'})
check("pg short err", "Jawaban tidak lengkap. Kerjakan seluruh soal." in t)
check("pg short checked 1", t.count("quiz-radio\" checked") == 1, t.count("quiz-radio\" checked"))
check("pg short counter", "sisa 2 soal belum dijawab" in t, t[t.find("quiz-counter"):t.find("quiz-counter") + 90])
check("pg short hint", "Sisa 2 soal belum dijawab." in t)
r, t = post(pg1_c, PURL, {"assignment_id": str(PG.id), "answers": '["B", "", "C"]'})
check("pg empty entry err", "Soal ke-2: pilih salah satu jawaban." in t)
check(
    "pg empty entry preserved",
    t.count("quiz-radio\" checked") == 2,
    t.count("quiz-radio\" checked"),
)
r, t = post(pg1_c, PURL, {"assignment_id": str(PG.id), "answers": '["B", "X", "C"]'})
check("pg invalid key err", "Soal ke-2: pilih salah satu jawaban." in t)
r, t = post(pg1_c, PURL, {"assignment_id": str(PG.id), "choice_0": "B"})
check("pg radio-only partial", "Jawaban tidak lengkap. Kerjakan seluruh soal." in t)
check("pg radio preserved", t.count("quiz-radio\" checked") == 1, t.count("quiz-radio\" checked"))
check("pg radio counter", "sisa 2 soal belum dijawab" in t)
check("pg no sub yet", not Submission.objects.filter(assignment=PG, student=pg1).exists())

# ---------- pg submit: success (hidden answers JSON) ----------
r, t = post(pg1_c, PURL, {"assignment_id": str(PG.id), "answers": '["B", "A", "C"]'})
check("pg success 302", r.status_code == 302 and r["Location"] == PURL, f"{r.status_code} {r.get('Location')}")
check(
    "pg success cookie",
    "nilai_flash" in r.cookies
    and r.cookies["nilai_flash"].value == f"terkirim:{PG.id}:{pg1.id}",
)
psub = Submission.objects.get(assignment=PG, student=pg1)
check("pg sub answers", psub.answers == ["B", "A", "C"] and psub.status == "submitted")
check("pg sub time", psub.submitted_at is not None)
check("pg review no grade", not Grade.objects.filter(submission=psub).exists())

r, t = get(pg1_c, PURL)
check("pg flash notice", t.count("Terkirim!") == 1, t.count("Terkirim!"))
check("pg locked rows", t.count('class="lk-q"') == 3, t.count('class="lk-q"'))
check("pg locked q label", '<span class="label">Soal 1</span>' in t)
check("pg locked no quiz", "data-sf-quiz" not in t)
check("pg locked pilihan", t.count("Pilihan Anda") == 3, t.count("Pilihan Anda"))
check("pg locked not revealed", "Kunci jawaban" not in t and ">Benar<" not in t and "Kurang tepat" not in t)
check("pg locked no unanswered", "Soal ini tidak dijawab." not in t)
check("pg locked status", ">Terkumpul</span>" in t)
check("pg locked waiting", "Tenang, nilai akan terbit setelah dosen me-review jawabanmu." in t)
check("pg locked no form", "Kerjakan tugas" not in t)
r2, t2 = get(pg1_c, PURL)
check("pg second get no notice", t2.count("Terkirim!") == 0, t2.count("Terkirim!"))
check("pg second get cookie cleared", "nilai_flash" not in r2.cookies or r2.cookies["nilai_flash"].value == "", dict(r2.cookies))

# ---------- pg submit: radio fallback (pg2) ----------
pg2 = make_student("pg2@nilai.test", [C1])
pg2_c = Client()
pg2_c.force_login(pg2)
r, t = post(pg2_c, PURL, {"assignment_id": str(PG.id), "choice_0": "B", "choice_1": "A"})
check("pg radio partial err", "Jawaban tidak lengkap. Kerjakan seluruh soal." in t)
r, t = post(
    pg2_c,
    PURL,
    {"assignment_id": str(PG.id), "choice_0": "B", "choice_1": "A", "choice_2": "C"},
)
check("pg radio success", r.status_code == 302 and r["Location"] == PURL, r.status_code)
psub2 = Submission.objects.get(assignment=PG, student=pg2)
check("pg radio answers", psub2.answers == ["B", "A", "C"])
r, t = post(
    pg2_c,
    PURL,
    {"assignment_id": str(PG.id), "choice_0": "B", "choice_1": "A", "choice_2": "C"},
)
check("pg radio locked 200", r.status_code == 200, r.status_code)
check("pg radio locked view", "<h3>Jawaban Anda</h3>" in t)
check("pg radio locked no form", "Kerjakan tugas" not in t)
check("pg radio locked count", Submission.objects.filter(assignment=PG, student=pg2).count() == 1)

# ---------- ismail: draft grade hidden ----------
is_c = Client()
is_c.force_login(ismail)
r, t = get(is_c, PURL)
check("ismail 200", r.status_code == 200, r.status_code)
check("ismail status terkumpul", ">Terkumpul</span>" in t)
check("ismail no grade block", "Hasil penilaian" not in t)
check("ismail waiting", "Tenang, nilai akan terbit setelah dosen me-review jawabanmu." in t)
check("ismail pilihan", t.count("Pilihan Anda") == 3, t.count("Pilihan Anda"))
check("ismail not revealed", "Kunci jawaban" not in t and ">Benar<" not in t)

# ---------- pdf page + submit ----------
pdf1 = make_student("pdf1@nilai.test", [C2])
p1c = Client()
p1c.force_login(pdf1)
r, t = get(p1c, FURL)
check("pdf 200", r.status_code == 200, r.status_code)
check("pdf label", 'asg-muted">Unggah PDF</span>' in t)
check("pdf file label", "Berkas PDF" in t)
check("pdf accept", 'accept=".pdf"' in t)
check("pdf question", "Unggah laporan analisis basis data dalam PDF" in t)
check("pdf hint", "Setelah dikirim, jawaban terkunci dan tidak dapat diubah lagi." in t)
check("pdf no quiz", "data-sf-quiz" not in t)

r, t = post(p1c, FURL, {"assignment_id": str(PDF.id)})
check("pdf no file err", r.status_code == 200 and "Pilih berkas terlebih dahulu." in t)
r, t = post(p1c, FURL, {"assignment_id": str(PDF.id), "file": SimpleUploadedFile("x.docx", b"zz")})
check("pdf wrong ext err", "Berkas harus berformat PDF." in t)
r, t = post(p1c, FURL, {"assignment_id": str(PDF.id), "file": SimpleUploadedFile("empty.pdf", b"")})
check("pdf empty file err", "Pilih berkas terlebih dahulu." in t)
check("pdf errors no cookie", "nilai_flash" not in r.cookies, list(r.cookies))

r, t = post(p1c, FURL, {"assignment_id": str(PDF.id), "file": SimpleUploadedFile("bad.pdf", b"not a pdf")})
check("pdf garbage 302", r.status_code == 302 and r["Location"] == FURL, f"{r.status_code} {r.get('Location')}")
fsub = Submission.objects.get(assignment=PDF, student=pdf1)
check("pdf garbage extraction", fsub.extraction_ok is False and fsub.extracted_text is None)
check("pdf garbage status", fsub.status == "submitted")
check("pdf garbage no grade", not Grade.objects.filter(submission=fsub).exists())
r, t = get(p1c, FURL, cookie=f"terkirim:{PDF.id}:{pdf1.id}")
check("pdf locked name", "bad.pdf" in t)
check("pdf locked fail", "Teks tidak terbaca." in t)
check("pdf locked no ok", "Berkas terunggah." not in t)
check("pdf locked label", "Berkas Anda" in t)
check("pdf locked waiting", "Tenang, nilai akan terbit setelah dosen me-review jawabanmu." in t)

pdf2 = make_student("pdf2@nilai.test", [C2])
p2c = Client()
p2c.force_login(pdf2)
r, t = post(
    p2c,
    FURL,
    {
        "assignment_id": str(PDF.id),
        "file": SimpleUploadedFile("laporan.pdf", make_pdf("Laporan analisis basis data kampus")),
    },
)
check("pdf valid 302", r.status_code == 302, r.status_code)
vsub = Submission.objects.get(assignment=PDF, student=pdf2)
check(
    "pdf valid extraction",
    vsub.extraction_ok is True
    and vsub.extracted_text == "Laporan analisis basis data kampus",
    vsub.extracted_text,
)
r, t = get(p2c, FURL, cookie=f"terkirim:{PDF.id}:{pdf2.id}")
check("pdf valid ok msg", "Berkas terunggah." in t)
check("pdf valid no fail", "Teks tidak terbaca." not in t)

# ---------- docx langsung: garbage -> needs_review ----------
dx1 = make_student("dx1@nilai.test", [C2])
d1c = Client()
d1c.force_login(dx1)
r, t = get(d1c, DURL)
check("docx 200", r.status_code == 200, r.status_code)
check("docx label", 'asg-muted">Unggah DOCX</span>' in t)
check("docx file label", "Berkas DOCX" in t)
check("docx accept", 'accept=".docx"' in t)
check("docx mode", "Rilis: Langsung rilis" in t)
check("docx question", "Unggah rancangan skema basis data aplikasi dalam DOCX" in t)

r, t = post(d1c, DURL, {"assignment_id": str(DOCX.id), "file": SimpleUploadedFile("bad.docx", b"garbage bytes")})
check("docx garbage 302", r.status_code == 302 and r["Location"] == DURL, f"{r.status_code} {r.get('Location')}")
dsub = Submission.objects.get(assignment=DOCX, student=dx1)
check("docx garbage needs_review", dsub.status == "needs_review" and dsub.extraction_ok is False)
check("docx garbage no grade", not Grade.objects.filter(submission=dsub).exists())
check("docx grades baseline", Grade.objects.count() == BASE_GRADES, Grade.objects.count())
r, t = get(d1c, DURL, cookie=f"terkirim:{DOCX.id}:{dx1.id}")
check("docx review status", ">Perlu review</span>" in t)
check("docx review hint", "Dosen sedang mereview jawaban Anda." in t)
check("docx review waiting", "Tenang, jawabanmu sedang menunggu review dosen." in t)

# ---------- docx langsung: valid -> published grade (patched compute) ----------
dx2 = make_student("dx2@nilai.test", [C2])
d2c = Client()
d2c.force_login(dx2)
calls = []
real_compute = VS.compute_grade


def fake_compute(submission_id):
    calls.append(submission_id)
    return {
        "ok": True,
        "criteria": [
            {
                "criterion_id": "x",
                "name": "Kelengkapan",
                "weight": 50,
                "score": 4,
                "quote": "",
                "comment": "Lengkap.",
            }
        ],
        "feedback": "Bagus.",
        "summary": "Rapi.",
        "nilai": 92.5,
        "predikat": "A",
        "source": "model",
    }


VS.compute_grade = fake_compute
try:
    r, t = post(
        d2c,
        DURL,
        {
            "assignment_id": str(DOCX.id),
            "file": SimpleUploadedFile("rancangan.docx", make_docx("Rancangan skema relasi")),
        },
    )
finally:
    VS.compute_grade = real_compute
check("docx success 302", r.status_code == 302 and r["Location"] == DURL, f"{r.status_code} {r.get('Location')}")
check("docx compute called once", len(calls) == 1, calls)
dsub2 = Submission.objects.get(assignment=DOCX, student=dx2)
check(
    "docx valid extraction",
    dsub2.extraction_ok is True and dsub2.extracted_text == "Rancangan skema relasi",
    dsub2.extracted_text,
)
check("docx valid status", dsub2.status == "submitted")
g2 = Grade.objects.get(submission=dsub2)
check("docx grade published", g2.state == "published" and g2.source == "model")
check("docx grade nilai", g2.nilai == Decimal("92.50"), g2.nilai)
check("docx grades +1", Grade.objects.count() == BASE_GRADES + 1, Grade.objects.count())
r, t = get(d2c, DURL, cookie=f"terkirim:{DOCX.id}:{dx2.id}")
check("docx grade title", "<h3>Hasil penilaian</h3>" in t)
check("docx grade nilai", ">92.50" in t and "Predikat A" in t)
check("docx grade crit", "Kelengkapan" in t and ">4/4</span>" in t)
check("docx grade feedback", "Bagus." in t)
check("docx grade summary", "Rapi." in t)
check("docx grade no waiting", "Tenang" not in t)
check("docx grade status dinilai", ">Dinilai</span>" in t)
check("docx grade no form", "Kerjakan tugas" not in t)

# ---------- cookie not shown for other assignments ----------
r, t = get(baru_c, PURL, cookie=f"terkirim:{ESSAY.id}:{baru.id}")
check("flash other page", "Terkirim! Jawaban" not in t)

# ---------- cleanup ----------
for u in temp_users:
    u.delete()
check("cleanup subs", Submission.objects.count() == BASE_SUBS, Submission.objects.count())
check("cleanup grades", Grade.objects.count() == BASE_GRADES, Grade.objects.count())
check("cleanup enroll", Enrollment.objects.count() == BASE_ENROLL, Enrollment.objects.count())
check(
    "cleanup users",
    not User.objects.filter(
        email__in=[
            "baru@nilai.test",
            "pg1@nilai.test",
            "pg2@nilai.test",
            "pdf1@nilai.test",
            "pdf2@nilai.test",
            "dx1@nilai.test",
            "dx2@nilai.test",
        ]
    ).exists(),
)

# ---------- seed integrity ----------
check("integrity assignments", Assignment.objects.count() == 4, Assignment.objects.count())
check(
    "integrity aldy essay",
    Submission.objects.filter(assignment=ESSAY, student=aldy, status="submitted").count() == 1,
)
check(
    "integrity ismail answers",
    Submission.objects.get(assignment=PG, student=ismail).answers == ["B", "A", "C"],
)
check("integrity published grade", Grade.objects.filter(state="published").count() == 1)
check("integrity draft grade", Grade.objects.filter(state="draft").count() == 1)
check("integrity baru gone", not Enrollment.objects.filter(student__email="baru@nilai.test").exists())

print(f"PASS {ok}  FAIL {len(fail)}")
for f in fail:
    print("  -", f)
sys.exit(1 if fail else 0)
