"""Phase 4 chunk-B3 verification: submission detail + grade editor."""
import html
import json
import os
import re
import sys
import uuid
from datetime import timedelta

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nilai.settings")

import django

django.setup()

from django.test import Client  # noqa: E402
from django.utils import timezone  # noqa: E402

from accounts.models import ModelSettings, User  # noqa: E402
from academics.models import Topic  # noqa: E402
from assessment.models import (  # noqa: E402
    Assignment,
    Grade,
    GradeRevision,
    RubricCriterion,
    Submission,
)
from nilai.templatetags.nilai_tags import fmt_date  # noqa: E402

ok = 0
fail = []


def check(name, cond, extra=""):
    global ok
    if cond:
        ok += 1
    else:
        fail.append(f"{name} {extra}"[:300])


def norm(t):
    return re.sub(r"\s+", " ", t)


ALDY = "f1000000-0000-4000-8000-000000000001"
MIRATIL = "f1000000-0000-4000-8000-000000000002"
ISMAIL = "f1000000-0000-4000-8000-000000000003"
FITRI = "f1000000-0000-4000-8000-000000000004"
ESSAY = "d1000000-0000-4000-8000-000000000001"
PG = "d1000000-0000-4000-8000-000000000002"
PDF = "d1000000-0000-4000-8000-000000000003"
DOCX = "d1000000-0000-4000-8000-000000000004"
C_BDB = "b1000000-0000-4000-8000-000000000003"
CR = [
    "e1000000-0000-4000-8000-000000000001",
    "e1000000-0000-4000-8000-000000000002",
    "e1000000-0000-4000-8000-000000000003",
    "e1000000-0000-4000-8000-000000000004",
]
U_ALDY = f"/lecturer/submissions/{ALDY}"
U_MIRATIL = f"/lecturer/submissions/{MIRATIL}"
U_ISMAIL = f"/lecturer/submissions/{ISMAIL}"
U_FITRI = f"/lecturer/submissions/{FITRI}"

STU_ALDY = "a1000000-0000-4000-8000-000000000011"
STU_MIRATIL = "a1000000-0000-4000-8000-000000000012"
STU_ISMAIL = "a1000000-0000-4000-8000-000000000013"
STU_FITRI = "a1000000-0000-4000-8000-000000000014"
LECT = "a1000000-0000-4000-8000-000000000002"

now = timezone.now()
created = []


def make_submission(**kw):
    kw.setdefault("status", "submitted")
    kw.setdefault("submitted_at", now)
    kw.setdefault("updated_at", now)
    s = Submission.objects.create(**kw)
    created.append(s)
    return s


def cleanup():
    for s in created:
        GradeRevision.objects.filter(grade__submission=s).delete()
        Grade.objects.filter(submission=s).delete()
        Submission.objects.filter(id=s.id).delete()
    created.clear()


ms = ModelSettings.objects.get(id=1)
MS_FIELDS = [
    "base_url",
    "api_key",
    "model_name",
    "emb_base_url",
    "emb_api_key",
    "emb_model_name",
]
MS_SNAP = {f: getattr(ms, f) for f in MS_FIELDS}


def restore_settings():
    for f in MS_FIELDS:
        setattr(ms, f, MS_SNAP[f])
    ms.save()


# ---------- gates ----------
anon = Client()
r = anon.get(U_ALDY)
check("anon get gate", r.status_code == 302 and r["Location"] == "/login", r.get("Location"))
r = anon.post(U_ALDY, {"action": "run_grade"})
check("anon post gate", r.status_code == 302 and r["Location"] == "/login", r.get("Location"))

stu = Client()
stu.force_login(User.objects.get(email="aldy@nilai.test"))
r = stu.get(U_ALDY)
check("student get gate", r.status_code == 302 and r["Location"] == "/student/home", r.get("Location"))
r = stu.post(U_ALDY, {"action": "save_grade"})
check("student post gate", r.status_code == 302 and r["Location"] == "/student/home", r.get("Location"))

adm = Client()
adm.force_login(User.objects.get(email="audyah@nilai.test"))
r = adm.get(U_ALDY)
check("admin get gate", r.status_code == 302 and r["Location"] == "/admin", r.get("Location"))
r = adm.post(U_ALDY, {"action": "run_grade"})
check("admin post gate", r.status_code == 302 and r["Location"] == "/admin", r.get("Location"))

c = Client()
c.force_login(User.objects.get(email="ramadan@nilai.test"))

# ---------- not found ----------
random_id = str(uuid.uuid4())
r = c.get(f"/lecturer/submissions/{random_id}")
t = html.unescape(r.content.decode())
check("missing 200", r.status_code == 200, r.status_code)
check("missing h1", "<h1>Pengumpulan</h1>" in t)
check("missing text", '<p class="empty-plain">Tidak ditemukan.</p>' in t)
check(
    "missing link",
    'class="btn" href="/lecturer/submissions">Ke daftar pengumpulan</a>' in t,
)

r = c.get("/lecturer/submissions/not-a-uuid")
check("malformed 404", r.status_code == 404, r.status_code)

# ---------- unassigned course ----------
tmp_topic = Topic.objects.create(course_id=C_BDB, week=9, title="Percobaan")
tmp_asg = Assignment.objects.create(
    topic_id=tmp_topic.id,
    title="Tugas percobaan",
    type="essay",
    release_mode="review",
)
tmp_sub = make_submission(
    assignment_id=tmp_asg.id, student_id=STU_FITRI, answer_text="jawaban."
)
U_TMP = f"/lecturer/submissions/{tmp_sub.id}"
r = c.get(U_TMP)
t = html.unescape(r.content.decode())
check("unassigned 200 missing", r.status_code == 200 and "Tidak ditemukan." in t)
r = c.post(U_TMP, {"action": "save_grade", "feedback": "x", "criteria": "[]"})
t = html.unescape(r.content.decode())
check("unassigned post missing", "Tidak ditemukan." in t)
check("unassigned no grade", not Grade.objects.filter(submission=tmp_sub).exists())
GradeRevision.objects.filter(grade__submission=tmp_sub).delete()
Grade.objects.filter(submission=tmp_sub).delete()
Submission.objects.filter(id=tmp_sub.id).delete()
Assignment.objects.filter(id=tmp_asg.id).delete()
Topic.objects.filter(id=tmp_topic.id).delete()

# ---------- essay page (aldy, graded) ----------
r = c.get(U_ALDY)
t = html.unescape(r.content.decode())
check("aldy 200", r.status_code == 200, r.status_code)
check("aldy h1", "<h1>Aldy</h1>" in t)
check(
    "aldy sub",
    "Esai: bentuk normalisasi · IF201 — Basis Data" in t,
)
aldy_sub = Submission.objects.get(id=ALDY)
check("aldy meta type", "<span>Esai</span>" in t)
check("aldy meta date", f"<span>{fmt_date(aldy_sub.submitted_at)}</span>" in t)
check("aldy crumb last", 'class="crumb is-last">Aldy</span>' in t)
check(
    "aldy crumb submissions",
    'class="crumb-link" href="/lecturer/submissions">Pengumpulan</span>' not in t
    and 'href="/lecturer/submissions">Pengumpulan</a>' in t,
)
check(
    "aldy crumb assignment",
    f'href="/lecturer/assignments/{ESSAY}">Esai: bentuk normalisasi</a>' in t,
)
check("aldy ke tugas", f'href="/lecturer/assignments/{ESSAY}">Ke tugas</a>' in t)
check("aldy answer", "Normalisasi adalah proses menyusun tabel agar redundansi data berkurang." in t)
check("aldy question", "Jelaskan bentuk normalisasi 1NF, 2NF, dan 3NF" in t)
check("aldy badge", "<span>Terbit</span>" in t)
check("aldy live score", 'data-ge-live>87.5<' in t)
check("aldy predikat", 'Predikat <span data-ge-predikat>A</span>' in t)
check("aldy no weight warn", "Bobot rubrik berjumlah" not in t)
check("aldy no belumdinilai", "Belum dinilai." not in t)
check("aldy editor h3", "<h3>Penilaian</h3>" in t)
for name in ("Ketepatan konsep", "Kelengkapan", "Struktur argumen", "Contoh penerapan"):
    check(f"aldy row {name}", f'aria-label="Skor {name}"' in t)
check("aldy sel 3", t.count('<option value="3" selected>3</option>') == 2, t.count('<option value="3" selected>3</option>'))
check("aldy sel 4", t.count('<option value="4" selected>4</option>') == 2, t.count('<option value="4" selected>4</option>'))
check("aldy sel 1", t.count('<option value="1" selected>1</option>') == 0)
check("aldy labels", '<label class="label" for="gf">Umpan balik</label>' in t and '<label class="label" for="gs">Ringkasan</label>' in t)
aldy_grade = Grade.objects.get(id="a0000000-0000-4000-8000-000000000001")
check("aldy fb value", f'<textarea class="textarea" id="gf" rows="3" data-ge-feedback>{aldy_grade.feedback}</textarea>' in t)
check("aldy summary value", f'id="gs" rows="2" data-ge-summary>{aldy_grade.summary}</textarea>' in t)
check("aldy btn model", 'data-run-btn>Nilai dengan model</button>' in t)
check("aldy btn save", 'data-intent="draft">Simpan nilai</button>' in t)
check("aldy btn publish", 'data-intent="publish">Terbitkan</button>' in t)
check("aldy hint", "Saran nilai dari model, Anda tetap bisa memperbaikinya." in t)
check("aldy quote value", 'placeholder="Kutipan dari jawaban"' in t)
check("aldy comment value", 'placeholder="Komentar"' in t)
check("aldy bobot", "bobot 25%" in t)

raw = r.content.decode()
m = re.search(r'data-ge-criteria value="([^"]*)"', raw)
check("aldy criteria json present", m is not None)
if m:
    payload = json.loads(html.unescape(m.group(1)))
    check("aldy criteria len", len(payload) == 4, len(payload))
    check("aldy criteria ids", [p["id"] for p in payload] == CR, payload)
    check("aldy criteria scores", [p["score"] for p in payload] == [3, 4, 3, 4], payload)
    check("aldy criteria quote", payload[0]["quote"] == aldy_grade.criteria[0]["quote"])

check("aldy revisions h2", "<h2>Riwayat nilai</h2>" in t)
check("aldy revision val", 'rev-val">87.50 · A<' in t)
check("aldy revision by", "<span>Ramadan Agung Wibawa</span>" in t)
check("aldy revision sep", '<span class="rev-sep">·</span>' in t)
check("aldy revision date", fmt_date(aldy_sub.submitted_at) in t)
check("aldy no raw", "Respons model mentah" not in t)

# ---------- pg page (ismail, graded draft) ----------
r = c.get(U_ISMAIL)
t = html.unescape(r.content.decode())
check("ismail 200", r.status_code == 200, r.status_code)
check("ismail h1", "<h1>Ismail Saputra</h1>" in t)
check("ismail label", '<span class="label">Penilaian otomatis</span>' in t)
check("ismail score", '<p class="ge-score">100<span class="ge-predikat">Predikat A</span></p>' in t)
check("ismail draft", "<span>Draft</span>" in t)
check("ismail fb", '<p class="ge-feedback">3 dari 3 jawaban benar.</p>' in t)
check("ismail no editor rows", "data-ge-row" not in t)
check("ismail no umpan balik label", 'for="gf">Umpan balik</label>' not in t)
check("ismail no save btn", "data-save-btn" not in t)
check("ismail no hint run", "Nilai dengan model" not in t)
check("ismail hitung", ">Hitung nilai</button>" in t)
check("ismail pg hint", "Dihitung dari kunci jawaban, tanpa model." in t)
check("ismail intent publish", '<input type="hidden" name="intent" value="publish">' in t)
check("ismail no save form", "data-save-form" not in t)
check("ismail question 1", "Klausa yang digunakan untuk menggabungkan dua tabel" in t)
check("ismail answer 1", '<span class="fw500">B</span> — JOIN' in t)
check("ismail answer 2", '<span class="fw500">A</span> — UNION' in t)
check("ismail answer 3", '<span class="fw500">C</span> — COUNT' in t)
check("ismail revisions", 'rev-val">100 · A<' in t)
check("ismail revision sistem", "<span>Sistem</span>" in t)

# ---------- pdf page (fitri, ungraded) ----------
r = c.get(U_FITRI)
t = html.unescape(r.content.decode())
check("fitri 200", r.status_code == 200, r.status_code)
check("fitri h1", "<h1>Fitri Lestari</h1>" in t)
check("fitri extracted", "Laporan analisis basis data akademik." in t)
check("fitri scroll", 'class="answer-scroll"' in t)
check("fitri not unreadable", "Teks tidak terbaca." not in t)
check("fitri draft", "<span>Draft</span>" in t)
check("fitri live 25", "data-ge-live>25<" in t)
check("fitri pred D", "data-ge-predikat>D<" in t)
check("fitri empty fb", 'data-ge-feedback></textarea>' in t)
check("fitri empty summary", 'data-ge-summary></textarea>' in t)
check("fitri sel1 x4", t.count('<option value="1" selected>1</option>') == 4, t.count('<option value="1" selected>1</option>'))
check("fitri no revisions", "Riwayat nilai" not in t)
check("fitri review hint", "Saran nilai dari model, Anda tetap bisa memperbaikinya." in t)
check("fitri pdf type", "<span>Unggah PDF</span>" in t)

# ---------- docx page (langsung, ungraded) ----------
docx_sub = make_submission(
    assignment_id=DOCX,
    student_id=STU_FITRI,
    file_name="rancangan.docx",
    extracted_text="Daftar tabel mahasiswa dan relasi kunci asing.",
    extraction_ok=True,
)
U_DOCX = f"/lecturer/submissions/{docx_sub.id}"
r = c.get(U_DOCX)
t = html.unescape(r.content.decode())
check("docx 200", r.status_code == 200, r.status_code)
check("docx langsung hint", "Mode langsun rilis: nilai terbit saat disimpan." in t)
check("docx extracted", "Daftar tabel mahasiswa dan relasi kunci asing." in t)
check("docx type", "<span>Unggah DOCX</span>" in t)

# ---------- save errors (miratil, no grade yet) ----------
check("pre miratil no grade", not Grade.objects.filter(submission_id=MIRATIL).exists())

r = c.post(U_MIRATIL, {"action": "save_grade", "criteria": "nope", "feedback": "x"})
t = html.unescape(r.content.decode())
check("bad json error", r.status_code == 200 and "Data nilai tidak valid." in t)
check("bad json no grade", not Grade.objects.filter(submission_id=MIRATIL).exists())

crit_ok = json.dumps(
    [
        {"id": CR[0], "score": 2, "quote": "kutipan1", "comment": "komentar1"},
        {"id": CR[1], "score": 3, "quote": "kutipan2", "comment": "komentar2"},
        {"id": CR[2], "score": 3, "quote": "kutipan3", "comment": "komentar3"},
        {"id": CR[3], "score": 4, "quote": "kutipan4", "comment": "komentar4"},
    ]
)

r = c.post(U_MIRATIL, {"action": "save_grade", "criteria": crit_ok, "feedback": "   ", "summary": "s"})
t = html.unescape(r.content.decode())
check("empty feedback error", "Umpan balik wajib diisi." in t)
check("empty feedback redisplay", 'value="kutipan1"' in t, "")
check("empty feedback no grade", not Grade.objects.filter(submission_id=MIRATIL).exists())

crit_bad = json.dumps(
    [
        {"id": CR[0], "score": 9, "quote": "kutipan1", "comment": "komentar1"},
        {"id": CR[1], "score": 3, "quote": "kutipan2", "comment": "komentar2"},
        {"id": CR[2], "score": 3, "quote": "kutipan3", "comment": "komentar3"},
        {"id": CR[3], "score": 4, "quote": "kutipan4", "comment": "komentar4"},
    ]
)
r = c.post(U_MIRATIL, {"action": "save_grade", "criteria": crit_bad, "feedback": "f", "summary": "s"})
t = html.unescape(r.content.decode())
check("bad score error", 'Skor tidak valid pada "Ketepatan konsep".' in t)
check("bad score fallback sel", t.count('<option value="1" selected>1</option>') == 1, t.count('<option value="1" selected>1</option>'))
check("bad score keeps others", t.count('<option value="3" selected>3</option>') == 2)
check("bad score no grade", not Grade.objects.filter(submission_id=MIRATIL).exists())

crit_str = crit_bad.replace('"score": 9', '"score": "abc"')
r = c.post(U_MIRATIL, {"action": "save_grade", "criteria": crit_str, "feedback": "f", "summary": "s"})
t = html.unescape(r.content.decode())
check("str score error", 'Skor tidak valid pada "Ketepatan konsep".' in t)

# ---------- guard: no grade + no rubric (pg submission) ----------
guard_sub = make_submission(assignment_id=PG, student_id=STU_FITRI, answers=[])
r = c.post(
    f"/lecturer/submissions/{guard_sub.id}",
    {"action": "save_grade", "criteria": "[]", "feedback": "Masukan.", "summary": ""},
)
t = html.unescape(r.content.decode())
check(
    "guard no grade error",
    "Belum ada nilai. Jalankan penilaian otomatis terlebih dahulu." in t,
)
check("guard no write", not Grade.objects.filter(submission=guard_sub).exists())
GradeRevision.objects.filter(grade__submission=guard_sub).delete()
Grade.objects.filter(submission=guard_sub).delete()
Submission.objects.filter(id=guard_sub.id).delete()
created[:] = [s for s in created if s.id != guard_sub.id]

# ---------- save success chain (miratil) ----------
# 1) empty criteria -> defaults to score 1
r = c.post(U_MIRATIL, {"action": "save_grade", "criteria": "[]", "feedback": "Semangat.", "summary": "Singkat."})
check("save [] redirect", r.status_code == 302, r.status_code)
loc = r.get("Location", "")
check("save [] loc", loc == f"{U_MIRATIL}?info=Nilai+disimpan+sebagai+draf.", loc)
g = Grade.objects.get(submission_id=MIRATIL)
check("save [] state", g.state == "draft", g.state)
check("save [] source", g.source == "manual", g.source)
check("save [] nilai", float(g.nilai) == 25.0, g.nilai)
check("save [] predikat", g.predikat == "D", g.predikat)
check("save [] scores", [x["score"] for x in g.criteria] == [1, 1, 1, 1], g.criteria)
check("save [] fb", g.feedback == "Semangat." and g.summary == "Singkat.")
check("save [] by", str(g.created_by_id) == LECT and str(g.updated_by_id) == LECT)
check("save [] no published", g.published_at is None)
check("save [] revision", GradeRevision.objects.filter(grade=g).count() == 1)
rev = GradeRevision.objects.filter(grade=g).first()
check("save [] rev state", rev.state == "draft")
check("save [] rev by", str(rev.changed_by_id) == LECT)
check("save [] snapshot", rev.snapshot["feedback"] == "Semangat." and len(rev.snapshot["criteria"]) == 4)

r = c.get(loc)
t = html.unescape(r.content.decode())
check("save [] info", "Nilai disimpan sebagai draf." in t)
check("save [] live", "data-ge-live>25<" in t)

# 2) real criteria -> 75 (update path)
r = c.post(U_MIRATIL, {"action": "save_grade", "criteria": crit_ok, "feedback": "Terima kasih.", "summary": "Perlu contoh."})
check("save real redirect", r.status_code == 302, r.get("Location"))
check("save real loc", r.get("Location") == f"{U_MIRATIL}?info=Nilai+disimpan+sebagai+draf.", r.get("Location"))
g = Grade.objects.get(submission_id=MIRATIL)
check("save real nilai", float(g.nilai) == 75.0, g.nilai)
check("save real predikat", g.predikat == "B", g.predikat)
check("save real scores", [x["score"] for x in g.criteria] == [2, 3, 3, 4], g.criteria)
check("save real quote", g.criteria[0]["quote"] == "kutipan1")
check("save real state", g.state == "draft")
check("save real rev count", GradeRevision.objects.filter(grade=g).count() == 2)
check("save real created stable", GradeRevision.objects.filter(grade=g).count() == 2)
check("save real ids stable", Grade.objects.filter(submission_id=MIRATIL).count() == 1)

r = c.get(U_MIRATIL)
t = html.unescape(r.content.decode())
check("save real live", "data-ge-live>75<" in t)
check("save real pred B", "data-ge-predikat>B<" in t)
check("save real fb", 'data-ge-feedback>Terima kasih.</textarea>' in t)
check("save real rev rows", t.count('class="rev-row"') == 2, t.count('class="rev-row"'))
check("save real rev latest first", t.find("75 · B") < t.find("25 · D"))

# 3) publish
r2 = c.post(
    U_MIRATIL,
    {"action": "save_grade", "criteria": crit_ok, "feedback": "Terima kasih.", "summary": "Perlu contoh.", "intent": "publish"},
)
check("publish loc", r2.get("Location") == f"{U_MIRATIL}?info=Nilai+terbit.", r2.get("Location"))
g = Grade.objects.get(submission_id=MIRATIL)
check("publish state", g.state == "published", g.state)
check("publish at", g.published_at is not None)
check("publish rev", GradeRevision.objects.filter(grade=g).count() == 3)
rev = GradeRevision.objects.filter(grade=g).order_by("-changed_at").first()
check("publish rev state", rev.state == "published")
r = c.get(r2.get("Location"))
t = html.unescape(r.content.decode())
check("publish info", "Nilai terbit." in t)
check("publish badge", "<span>Terbit</span>" in t)

# 4) docx langsung forces publish even with draft intent
docx_rubric = list(
    RubricCriterion.objects.filter(assignment_id=DOCX).order_by("position", "name")
)
crit_docx = json.dumps(
    [{"id": str(x.id), "score": 3, "quote": "q", "comment": "c"} for x in docx_rubric]
)
r = c.post(
    U_DOCX,
    {"action": "save_grade", "criteria": crit_docx, "feedback": "OK.", "summary": "OK."},
)
check("langsung loc", r.get("Location") == f"{U_DOCX}?info=Nilai+terbit.", r.get("Location"))
g = Grade.objects.get(submission=docx_sub)
check("langsung state", g.state == "published", g.state)
check("langsung source", g.source == "manual")
check("langsung nilai", float(g.nilai) == 75.0, g.nilai)

# cleanup save chain
for sid in (MIRATIL, docx_sub.id):
    GradeRevision.objects.filter(grade__submission_id=sid).delete()
    Grade.objects.filter(submission_id=sid).delete()

# ---------- run grade: pg code path ----------
run_sub = make_submission(assignment_id=PG, student_id=STU_FITRI, answers=["B", "B", "C"])
U_RUN = f"/lecturer/submissions/{run_sub.id}"
r = c.post(U_RUN, {"action": "run_grade", "submission_id": str(run_sub.id), "intent": "publish"})
check("pg run loc", r.get("Location") == f"{U_RUN}?info=Nilai+terbit.", r.get("Location"))
g = Grade.objects.get(submission=run_sub)
check("pg run state", g.state == "published", g.state)
check("pg run source", g.source == "code", g.source)
check("pg run nilai", float(g.nilai) == 66.67, g.nilai)
check("pg run predikat", g.predikat == "C", g.predikat)
check("pg run feedback", g.feedback == "2 dari 3 jawaban benar.", g.feedback)
check("pg run summary", g.summary == "Dinilai otomatis dari kunci jawaban, tanpa model.")
check("pg run criteria", g.criteria == [])
check("pg run by", str(g.created_by_id) == LECT)
check("pg run published at", g.published_at is not None)
check("pg run rev", GradeRevision.objects.filter(grade=g).count() == 1)
r = c.get(U_RUN)
t = html.unescape(r.content.decode())
check("pg run page score", '<p class="ge-score">66.67<span class="ge-predikat">Predikat C</span></p>' in t)
check("pg run page fb", '<p class="ge-feedback">2 dari 3 jawaban benar.</p>' in t)
check("pg run badge", "<span>Terbit</span>" in t)
GradeRevision.objects.filter(grade__submission=run_sub).delete()
Grade.objects.filter(submission=run_sub).delete()
Submission.objects.filter(id=run_sub.id).delete()
created[:] = [s for s in created if s.id != run_sub.id]

# ---------- run grade: empty answer path ----------
empty_sub = make_submission(assignment_id=ESSAY, student_id=STU_FITRI, answer_text="")
U_EMPTY = f"/lecturer/submissions/{empty_sub.id}"
r = c.post(U_EMPTY, {"action": "run_grade", "submission_id": str(empty_sub.id), "intent": "draft"})
check("empty run loc", r.get("Location") == f"{U_EMPTY}?info=Nilai+disimpan+sebagai+draf.", r.get("Location"))
g = Grade.objects.get(submission=empty_sub)
check("empty run state", g.state == "draft")
check("empty run source", g.source == "empty", g.source)
check("empty run nilai", float(g.nilai) == 25.0, g.nilai)
check("empty run predikat", g.predikat == "D")
check("empty run fb", g.feedback == "Jawaban kosong.")
check("empty run summary", g.summary == "Jawaban kosong, model tidak dipanggil.")
check("empty run scores", [x["score"] for x in g.criteria] == [1, 1, 1, 1])
check("empty run comment", all(x["comment"] == "Jawaban kosong." for x in g.criteria))
check("empty run quote", all(x["quote"] == "" for x in g.criteria))
check("empty run by", str(g.created_by_id) == LECT)
GradeRevision.objects.filter(grade__submission=empty_sub).delete()
Grade.objects.filter(submission=empty_sub).delete()
Submission.objects.filter(id=empty_sub.id).delete()
created[:] = [s for s in created if s.id != empty_sub.id]

# ---------- run grade: extraction failed ----------
bad_sub = make_submission(
    assignment_id=PDF, student_id=STU_ALDY, file_name="scan.pdf", extraction_ok=False
)
U_BAD = f"/lecturer/submissions/{bad_sub.id}"
r = c.post(U_BAD, {"action": "run_grade", "submission_id": str(bad_sub.id), "intent": "draft"})
t = html.unescape(r.content.decode())
check("extract fail error", r.status_code == 200 and "Teks tidak terbaca." in t)
check("extract fail no grade", not Grade.objects.filter(submission=bad_sub).exists())
GradeRevision.objects.filter(grade__submission=bad_sub).delete()
Grade.objects.filter(submission=bad_sub).delete()
Submission.objects.filter(id=bad_sub.id).delete()
created[:] = [s for s in created if s.id != bad_sub.id]

# ---------- run grade: settings gates ----------
try:
    for f in ("base_url", "api_key", "model_name"):
        setattr(ms, f, "")
    ms.save()
    r = c.post(U_MIRATIL, {"action": "run_grade", "submission_id": MIRATIL, "intent": "draft"})
    t = html.unescape(r.content.decode())
    check("model unset error", r.status_code == 200 and "Model belum disetel." in t)
    check("model unset no grade", not Grade.objects.filter(submission_id=MIRATIL).exists())

    ms.base_url = "https://llm.example/v1"
    ms.api_key = "sk-test"
    ms.model_name = "test-model"
    ms.emb_base_url = ""
    ms.emb_api_key = ""
    ms.emb_model_name = ""
    ms.save()
    r = c.post(U_FITRI, {"action": "run_grade", "submission_id": FITRI, "intent": "draft"})
    t = html.unescape(r.content.decode())
    check("embed unset error", r.status_code == 200 and "Embedding belum disetel." in t)
    check("embed unset no grade", not Grade.objects.filter(submission_id=FITRI).exists())
finally:
    restore_settings()

# ---------- invalid submission_id in POST falls back to not-found page ----------
r = c.post("/lecturer/submissions/00000000-0000-4000-8000-000000000000", {"action": "run_grade"})
t = html.unescape(r.content.decode())
check("missing sub post", r.status_code == 200 and "Tidak ditemukan." in t)

cleanup()
restore_settings()

# ---------- DB integrity ----------
check("no stray grades", not Grade.objects.filter(submission_id__in=[MIRATIL]).exists())
check("seed grades intact", Grade.objects.filter(submission_id=ALDY).exists() and Grade.objects.filter(submission_id=ISMAIL).exists())
check("seed aldy untouched", float(Grade.objects.get(submission_id=ALDY).nilai) == 87.5)
check("seed ismail draft", Grade.objects.get(submission_id=ISMAIL).state == "draft")
check("seed revision count", GradeRevision.objects.count() == 2, GradeRevision.objects.count())
check("seed submission count", Submission.objects.count() == 4, Submission.objects.count())

print(f"PASS {ok}  FAIL {len(fail)}")
for f in fail:
    print(" -", f)
sys.exit(1 if fail else 0)
