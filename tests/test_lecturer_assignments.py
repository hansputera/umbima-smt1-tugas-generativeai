"""Phase 4 chunk-B1 verification: assignment detail page (Django test client)."""
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

from accounts.models import ModelSettings, User  # noqa: E402
from academics.models import CourseLecturer, Topic  # noqa: E402
from assessment.models import Assignment, RubricCriterion  # noqa: E402

ok = 0
fail = []


def check(name, cond, extra=""):
    global ok
    if cond:
        ok += 1
    else:
        fail.append(f"{name} {extra}"[:300])


def btn_disabled(t, attr):
    m = re.search(r"<button[^>]*" + attr + r"[^>]*>", t)
    return bool(m) and "disabled" in m.group(0)


def row_count(t):
    return t.split("<template")[0].count("data-rubric-row")


ESSAY = "d1000000-0000-4000-8000-000000000001"
PG = "d1000000-0000-4000-8000-000000000002"
PDF = "d1000000-0000-4000-8000-000000000003"
BDB = "b1000000-0000-4000-8000-000000000003"

eurl = f"/lecturer/assignments/{ESSAY}"
purl = f"/lecturer/assignments/{PG}"
furl = f"/lecturer/assignments/{PDF}"

# original state
orig_mode = Assignment.objects.get(id=ESSAY).release_mode
orig_rows = [
    {
        "id": str(c.id),
        "name": c.name,
        "weight": c.weight,
        "level_1": c.level_1,
        "level_2": c.level_2,
        "level_3": c.level_3,
        "level_4": c.level_4,
        "prompt_notes": c.prompt_notes,
        "position": c.position,
    }
    for c in RubricCriterion.objects.filter(assignment_id=ESSAY).order_by("position")
]
ms = ModelSettings.objects.get(id=1)
orig_settings = {
    "api_key": ms.api_key,
    "base_url": ms.base_url,
    "model_name": ms.model_name,
    "emb_api_key": ms.emb_api_key,
    "emb_base_url": ms.emb_base_url,
    "emb_model_name": ms.emb_model_name,
}


def restore_rubric():
    RubricCriterion.objects.filter(assignment_id=ESSAY).delete()
    for r in orig_rows:
        RubricCriterion.objects.create(
            id=r["id"], assignment_id=ESSAY, position=r["position"],
            name=r["name"], weight=r["weight"], level_1=r["level_1"],
            level_2=r["level_2"], level_3=r["level_3"], level_4=r["level_4"],
            prompt_notes=r["prompt_notes"],
        )


def restore_settings():
    for k, v in orig_settings.items():
        setattr(ms, k, v)
    ms.save(update_fields=list(orig_settings))


# ---------- role gates ----------
c = Client()
r = c.get(eurl)
check("anon -> login", r.status_code == 302 and r["Location"] == "/login", r.get("Location"))

stu = Client()
stu.force_login(User.objects.get(email="aldy@nilai.test"))
r = stu.get(eurl)
check("student gate", r.status_code == 302 and r["Location"] == "/student/home", r.get("Location"))
r = stu.post(eurl, {"action": "save_mode", "mode": "review"})
check("student post gate", r.status_code == 302 and r["Location"] == "/student/home", r.get("Location"))

adm = Client()
adm.force_login(User.objects.get(email="audyah@nilai.test"))
r = adm.get(eurl)
check("admin gate", r.status_code == 302 and r["Location"] == "/admin", r.get("Location"))
r = adm.post(eurl, {"action": "save_rubric", "criteria": "[]"})
check("admin post gate", r.status_code == 302 and r["Location"] == "/admin", r.get("Location"))

c = Client()
c.force_login(User.objects.get(email="ramadan@nilai.test"))

# ---------- guard: unassigned course ----------
g_topic = Topic.objects.create(course_id=BDB, week=9, title="Guard topic")
g_asg = Assignment.objects.create(topic=g_topic, title="Guard asg", type="essay")
r = c.get(f"/lecturer/assignments/{g_asg.id}")
check("guard redirect", r.status_code == 302 and r["Location"] == "/lecturer/courses", r.get("Location"))
r = c.post(f"/lecturer/assignments/{g_asg.id}", {"action": "save_rubric", "criteria": "[]"})
check("guard post redirect", r.status_code == 302 and r["Location"] == "/lecturer/courses", r.get("Location"))
g_asg.delete()
g_topic.delete()

# ---------- essay page GET ----------
r = c.get(eurl)
t = html.unescape(r.content.decode())
check("essay 200", r.status_code == 200, r.status_code)
check("essay h1", "Esai: bentuk normalisasi" in t)
check("essay sub", "IF201 — Basis Data · Pertemuan 2: Normalisasi" in t)
check("essay crumb course", 'href="/lecturer/courses"' in t)
check("essay crumb topic", "Pertemuan 2" in t)
check("essay crumb last", '<span class="crumb is-last">Esai: bentuk normalisasi</span>' in t)
check("essay ke pertemuan", 'href="/lecturer/courses/b1000000-0000-4000-8000-000000000001/topics/c1000000-0000-4000-8000-000000000002">Ke pertemuan' in t)
check("essay meta type", "Esai" in t and "Rilis: Review dulu" in t)
check("essay no count", " soal</span>" not in t)
check("essay pertanyaan label", "Pertanyaan" in t and "Soal 1" not in t)
check("essay no kunci", "Kunci jawaban" not in t)
check("essay question body", "Jelaskan bentuk normalisasi 1NF, 2NF, dan 3NF" in t)
check("essay no options", "opt-list" not in t)
check("essay mode card", "Mode rilis" in t and "Review dulu" in t)
check("essay mode desc", "Nilai disimpan sebagai draf sampai dosen menerbitkannya." in t)
check("essay langsung desc", "Nilai langsung terlihat mahasiswa saat disimpan." in t)
check("essay warn hidden", '<div class="mode-warn" data-mode-warn hidden>' in t)
check("essay mode foot", "Simpan mode" in t and "Berlaku untuk semua pengumpulan." in t)
check("essay mode enabled", not btn_disabled(t, "data-mode-submit"))
check("essay rubric head", "Rubrik" in t and "Tambah kriteria" in t)
check("essay rubric rows", row_count(t) == 4, row_count(t))
check("essay rubric total", "Total bobot: 100%" in t and "is-bad" not in t.split("rubric-total")[1][:80])
check("essay rubric submit on", not btn_disabled(t, "data-rubric-submit"))
check("essay rubric aria", 'aria-label="Nama kriteria 1"' in t and 'aria-label="Hapus kriteria 4"' in t)
check("essay rubric placeholders", 'placeholder="Nama kriteria"' in t and 'placeholder="Skor 1: ..."' in t)
check("essay rubric names", "Ketepatan konsep" in t and "Kelengkapan" in t)
check("essay criteria json", 'name="criteria" id="criteria-json"' in t)
check("essay pengumpulan", "Pengumpulan" in t)
check("essay inbox students", "Aldy" in t and "Mir'atil Hayati" in t)
check("essay inbox statuses", "Dinilai" in t and "Terkumpul" in t)
check("essay inbox nilai", "87.50" in t)
check("essay inbox empty nilai", t.count("—") >= 1)
check("essay inbox buka", f'href="/lecturer/submissions/f1000000-0000-4000-8000-000000000001">Buka' in t)
check("essay no empty inbox", "Belum ada pengumpulan" not in t)
check("essay rubrik anchor", 'id="rubrik"' in t)

# ---------- pg page GET ----------
r = c.get(purl)
t = html.unescape(r.content.decode())
check("pg 200", r.status_code == 200, r.status_code)
check("pg soal count", "3 soal" in t)
check("pg soal labels", "Soal 1" in t and "Soal 3" in t)
check("pg no pertanyaan label", '<span class="label">Pertanyaan</span>' not in t)
check("pg kunci", "Kunci jawaban:" in t and "<b>B</b>" in t)
check("pg options", "GROUP BY" in t and "INTERSECT" in t)
check("pg empty rubric", "Belum ada kriteria rubrik. Tambahkan kriteria pertama." in t)
check("pg table hidden", '<div class="rubric-scroll" data-rubric-table hidden>' in t)
check("pg inbox student", "Ismail Saputra" in t and "Terkumpul" in t)
check("pg rubric empty not hidden", 'data-rubric-empty >' in t)

# ---------- info display ----------
r = c.get(eurl + "?info=Rubrik+disimpan.&f=rubric")
t = html.unescape(r.content.decode())
check("info rubric notice", "Rubrik disimpan." in t)
check("info rubric once", t.count("Rubrik disimpan.") == 1, t.count("Rubrik disimpan."))
r = c.get(eurl + "?info=Mode+review+dulu+aktif.&f=mode")
t = html.unescape(r.content.decode())
check("info mode notice", "Mode review dulu aktif." in t)
check("info mode once", t.count("Mode review dulu aktif.") == 1)

# ---------- save_rubric errors ----------
def post_rubric(criteria):
    payload = {"action": "save_rubric", "assignment_id": ESSAY, "criteria": criteria}
    return c.post(eurl, payload)


r = post_rubric("nope")
t = html.unescape(r.content.decode())
check("rub err json", r.status_code == 200 and "Data rubrik tidak valid." in t, r.status_code)
check("rub err json db rows", row_count(t) == 4, row_count(t))

r = post_rubric("[]")
t = html.unescape(r.content.decode())
check("rub err empty", "Tambahkan minimal satu kriteria." in t)
check("rub err empty state", "Belum ada kriteria rubrik. Tambahkan kriteria pertama." in t)

r = post_rubric(json.dumps([{"name": "  ", "weight": 100}]))
check("rub err name", "Nama kriteria wajib diisi." in html.unescape(r.content.decode()))

r = post_rubric(json.dumps([{"name": "Kuat", "weight": 0}]))
t = html.unescape(r.content.decode())
check("rub err weight 0", 'Bobot "Kuat" tidak valid.' in t)
r = post_rubric(json.dumps([{"name": "Kuat", "weight": 101}]))
check("rub err weight 101", 'Bobot "Kuat" tidak valid.' in html.unescape(r.content.decode()))
r = post_rubric(json.dumps([{"name": "Kuat", "weight": "abc"}]))
check("rub err weight nan", 'Bobot "Kuat" tidak valid.' in html.unescape(r.content.decode()))
r = post_rubric(json.dumps([{"name": "Kuat", "weight": 10.5}]))
check("rub err weight float", 'Bobot "Kuat" tidak valid.' in html.unescape(r.content.decode()))

rows99 = [
    {"id": orig_rows[0]["id"], "name": "Ketepatan konsep", "weight": 30,
     "level_1": "a", "level_2": "b", "level_3": "c", "level_4": "d", "prompt_notes": "n"},
    {"id": orig_rows[1]["id"], "name": "Kelengkapan", "weight": 69,
     "level_1": "", "level_2": "", "level_3": "", "level_4": "", "prompt_notes": ""},
]
r = post_rubric(json.dumps(rows99))
t = html.unescape(r.content.decode())
check("rub err total", "Bobot harus berjumlah 100." in t)
check("rub redisplay rows", row_count(t) == 2, row_count(t))
check("rub redisplay total", "Total bobot: 99%" in t and "is-bad" in t)
check("rub redisplay disabled", btn_disabled(t, "data-rubric-submit"))
check("rub redisplay kept name", 'value="Ketepatan konsep"' in t)
check("rub redisplay weight", 'value="30"' in t)

# ---------- save_rubric success ----------
new_rows = [
    {"id": orig_rows[1]["id"], "name": "Kelengkapan revisi", "weight": 40,
     "level_1": "x", "level_2": "y", "level_3": "z", "level_4": "w", "prompt_notes": "p"},
    {"id": "", "name": "Baru kriteria", "weight": 60,
     "level_1": "1", "level_2": "2", "level_3": "3", "level_4": "4", "prompt_notes": ""},
]
r = post_rubric(json.dumps(new_rows))
check("rub ok redirect", r.status_code == 302, r.status_code)
loc = r.get("Location", "")
check("rub ok loc", loc == f"{eurl}?info=Rubrik+disimpan.&f=rubric", loc)
saved = list(RubricCriterion.objects.filter(assignment_id=ESSAY).order_by("position"))
check("rub ok count", len(saved) == 2, len(saved))
check(
    "rub ok content",
    saved[0].name == "Kelengkapan revisi" and saved[0].weight == 40 and saved[0].position == 0
    and saved[0].level_1 == "x" and saved[0].prompt_notes == "p",
)
check("rub ok new", saved[1].name == "Baru kriteria" and saved[1].weight == 60 and saved[1].position == 1)
check("rub ok deleted", not RubricCriterion.objects.filter(id=orig_rows[0]["id"]).exists())
r = c.get(loc)
t = html.unescape(r.content.decode())
check("rub ok re-render", "Total bobot: 100%" in t and "Kelengkapan revisi" in t and "Rubrik disimpan." in t)

restore_rubric()

# ---------- save_mode errors ----------
def post_mode(**data):
    payload = {"action": "save_mode", "assignment_id": ESSAY}
    payload.update(data)
    return c.post(eurl, payload)


r = post_mode(mode="bogus")
t = html.unescape(r.content.decode())
check("mode err unknown", r.status_code == 200 and "Mode tidak dikenal." in t, r.status_code)

r = post_mode(mode="langsung")
check("mode err confirm", 'Centang "Saya mengerti nilai terbit tanpa review."' in html.unescape(r.content.decode()))

r = c.post(purl, {"action": "save_mode", "assignment_id": PG, "mode": "langsung", "confirm": "on"})
t = html.unescape(r.content.decode())
check("mode err rubric sum", "Rubrik harus berjumlah 100." in t)
check("mode err keeps submitted", '<input type="radio" name="mode" value="langsung" checked>' in t)
check("mode err confirm kept", 'name="confirm" checked' in t)

# model unconfigured
ms.api_key = ""
ms.base_url = ""
ms.model_name = ""
ms.save(update_fields=["api_key", "base_url", "model_name"])
r = post_mode(mode="langsung", confirm="on")
check("mode err model", "Model belum disetel." in html.unescape(r.content.decode()))

# model ok but embedding missing (pdf)
ms.api_key = "k"
ms.base_url = "https://x"
ms.model_name = "m"
ms.emb_api_key = ""
ms.emb_base_url = ""
ms.emb_model_name = ""
ms.save(update_fields=["api_key", "base_url", "model_name", "emb_api_key", "emb_base_url", "emb_model_name"])
r = c.post(furl, {"action": "save_mode", "assignment_id": PDF, "mode": "langsung", "confirm": "on"})
check("mode err embedding", "Embedding belum disetel." in html.unescape(r.content.decode()))

# ---------- save_mode success ----------
ms.api_key = "k"
ms.base_url = "https://x.example"
ms.model_name = "m"
ms.save(update_fields=["api_key", "base_url", "model_name"])
r = post_mode(mode="review")
check("mode review redirect", r.status_code == 302, r.status_code)
loc = r.get("Location", "")
check("mode review loc", loc == f"{eurl}?info=Mode+review+dulu+aktif.&f=mode", loc)
check("mode review db", Assignment.objects.get(id=ESSAY).release_mode == "review")

# langsung with everything configured (essay: no embedding needed)
r = post_mode(mode="langsung", confirm="on")
check("mode langsung redirect", r.status_code == 302, r.status_code)
loc = r.get("Location", "")
check("mode langsung loc typo", loc == f"{eurl}?info=Mode+langsun+rilis+aktif.&f=mode", loc)
check("mode langsung db", Assignment.objects.get(id=ESSAY).release_mode == "langsung")
r = c.get(loc)
t = html.unescape(r.content.decode())
check("mode langsung info", "Mode langsun rilis aktif." in t)
check("mode langsung warn visible", 'data-mode-warn >' in t)
check("mode langsung confirm unchecked", 'name="confirm" checked' not in t)
check("mode langsung disabled", btn_disabled(t, "data-mode-submit"))

# blockers visible with langsung + model unset
ms.api_key = ""
ms.base_url = ""
ms.model_name = ""
ms.save(update_fields=["api_key", "base_url", "model_name"])
r = c.get(eurl)
t = html.unescape(r.content.decode())
check("blocker model", "Model belum disetel." in t)
check("blocker in warn", 'data-mode-warn >' in t)

# restore + review rendering
Assignment.objects.filter(id=ESSAY).update(release_mode=orig_mode)
restore_settings()
r = c.get(eurl)
t = html.unescape(r.content.decode())
check("restored mode", f'value="{orig_mode}" checked' in t)
check("restored warn hidden", 'data-mode-warn hidden' in t)
check("restored rubric", "Ketepatan konsep" in t and "Total bobot: 100%" in t)

# ---------- db integrity ----------
check("db rubric restored", RubricCriterion.objects.filter(assignment_id=ESSAY).count() == 4,
      RubricCriterion.objects.filter(assignment_id=ESSAY).count())
check("db mode restored", Assignment.objects.get(id=ESSAY).release_mode == orig_mode)
check(
    "db weights restored",
    sum(c.weight for c in RubricCriterion.objects.filter(assignment_id=ESSAY)) == 100,
)
restore_settings()

print(f"PASS {ok}  FAIL {len(fail)}")
for f in fail:
    print("  -", f)
sys.exit(1 if fail else 0)
