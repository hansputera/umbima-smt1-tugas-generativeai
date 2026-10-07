"""Phase 4 chunk-B2 verification: lecturer submissions inbox (Django test client)."""
import html
import os
import sys

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nilai.settings")

import django

django.setup()

from django.test import Client  # noqa: E402

from accounts.models import User  # noqa: E402
from assessment.models import Submission  # noqa: E402

ok = 0
fail = []


def check(name, cond, extra=""):
    global ok
    if cond:
        ok += 1
    else:
        fail.append(f"{name} {extra}"[:300])


URL = "/lecturer/submissions"

# ---------- gates ----------
anon = Client()
r = anon.get(URL)
check("anon gate", r.status_code == 302 and r["Location"] == "/login", r.get("Location"))

stu = Client()
stu.force_login(User.objects.get(email="aldy@nilai.test"))
r = stu.get(URL)
check("student gate", r.status_code == 302 and r["Location"] == "/student/home", r.get("Location"))

adm = Client()
adm.force_login(User.objects.get(email="audyah@nilai.test"))
r = adm.get(URL)
check("admin gate", r.status_code == 302 and r["Location"] == "/admin", r.get("Location"))

c = Client()
c.force_login(User.objects.get(email="ramadan@nilai.test"))

# ---------- page content ----------
r = c.get(URL)
t = html.unescape(r.content.decode())
check("200", r.status_code == 200, r.status_code)
check("h1", "<h1>Pengumpulan</h1>" in t)
check("desc", "Seluruh pengumpulan tugas pada mata kuliah Anda." in t)
check("crumb single", '<span class="crumb is-last">Pengumpulan</span>' in t)
check("crumb no root", 'class="crumb-link"' not in t)
check("nav active", 'class="nav-link is-active" href="/lecturer/submissions"' in t)

# filters
check("course label", '<span class="label">Mata kuliah</span>' in t)
check("status label", '<span class="label">Status</span>' in t)
check("course default", '<option value="all">Semua mata kuliah</option>' in t)
check("status options", t.count("<option value=") >= 6, t.count("<option value="))
check("status option labels", "Semua status" in t and "Terkumpul" in t and "Perlu review" in t and "Dinilai" in t and "Draft" in t)
check("course option", '<option value="b1000000-0000-4000-8000-000000000001">IF201 — Basis Data</option>' in t)
check("course option 2", '<option value="b1000000-0000-4000-8000-000000000002">IF315 — Pembangunan Aplikasi Web</option>' in t)
# sorted by label: IF201 before IF315
i1 = t.find(">IF201 — Basis Data<")
i2 = t.find(">IF315 — Pembangunan Aplikasi Web<")
check("course options sorted", 0 < i1 < i2, f"{i1} {i2}")
check("count line", 'data-inbox-count>4 dari 4 pengumpulan</p>' in t)

# rows
check("row count", t.count("data-inbox-row") == 4, t.count("data-inbox-row"))
check("table visible", '<div class="table-wrap card-table" data-inbox-table>' in t)
check("empty none hidden", 'data-inbox-empty-none hidden>' in t)
check("empty filter hidden", 'data-inbox-empty-filter hidden>' in t)

# statuses per row
check("status terkumpul", 'data-status="terkumpul"' in t)
check("status dinilai", 'data-status="dinilai"' in t)
check("status st-ok", "st-ok" in t and "Dinilai" in t)

# nilai: only published grades show
check("nilai published", '<td class="td td-nowrap">87.50</td>' in t)
check("nilai unpublished dashes", t.count('<td class="td td-nowrap">—</td>') == 3,
      t.count('<td class="td td-nowrap">—</td>'))

# cells
check("cell course", '<span class="fw500">IF201</span><span class="td-pair">Basis Data</span>' in t)
check("cell assignment", '<span class="fw500">Pilihan ganda: kueri JOIN</span><span class="td-pair">Pilihan ganda</span>' in t)
check("cell type", '<span class="td-pair">Esai</span>' in t)
check("buka links", '/lecturer/submissions/f1000000-0000-4000-8000-000000000004">Buka' in t)

# order: submitted_at DESC (fitri/miratil -1d > ismail -2d > aldy -3d), tie by name
order = [t.find(n) for n in ("Fitri Lestari", "Mir'atil Hayati", "Ismail Saputra", "Aldy")]
check("row order", all(x > 0 for x in order) and order == sorted(order), order)

# ---------- NULLS LAST with a draft submission ----------
draft = Submission.objects.create(
    assignment_id="d1000000-0000-4000-8000-000000000002",
    student_id=User.objects.get(email="fitri@nilai.test").id,
    status="draft",
    submitted_at=None,
)
r = c.get(URL)
t = html.unescape(r.content.decode())
check("draft count", 'data-inbox-count>5 dari 5 pengumpulan</p>' in t)
check("draft status", 'data-status="draft"' in t)
last_pos = t.rfind("data-inbox-row")
check(
    "nulls last",
    t.rfind("Fitri Lestari") > t.find("Ismail Saputra") and t.rfind("data-inbox-row") > t.find("Aldy"),
    (t.find("Fitri Lestari"), t.rfind("Fitri Lestari"), t.find("Aldy")),
)
draft.delete()

# ---------- restored ----------
r = c.get(URL)
t = html.unescape(r.content.decode())
check("restored count", 'data-inbox-count>4 dari 4 pengumpulan</p>' in t)
check("restored rows", t.count("data-inbox-row") == 4, t.count("data-inbox-row"))
check("db no draft", not Submission.objects.filter(status="draft", submitted_at=None).exists())

print(f"PASS {ok}  FAIL {len(fail)}")
for f in fail:
    print("  -", f)
sys.exit(1 if fail else 0)
