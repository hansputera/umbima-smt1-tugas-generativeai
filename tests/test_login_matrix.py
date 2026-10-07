import os
import sys

sys.path.insert(0, os.getcwd())

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nilai.settings")
django.setup()

from django.test import Client  # noqa: E402

results = []


def check(label, cond, extra=""):
    results.append((label, bool(cond), extra))


c = Client(enforce_csrf_checks=False)

# 1. root redirects to /login
r = c.get("/")
check("GET / redirects to /login", r.status_code == 302 and r["Location"] == "/login", r["Location"])

# 2. login page renders (no trailing slash)
r = c.get("/login")
body = r.content.decode()
check("GET /login 200", r.status_code == 200, r.status_code)
check("login shows Indonesian welcome", "Selamat datang!" in body)
check("login has form + csrf", "csrfmiddlewaretoken" in body and "/login" in body)

# 3. empty credentials
r = c.post("/login", {"email": "", "password": ""})
check("empty creds error", "Email dan kata sandi wajib diisi." in r.content.decode())

# 4. unknown email vs wrong password -> same message
r = c.post("/login", {"email": "nobody@nilai.test", "password": "x"})
m1 = "Email atau kata sandi salah." in r.content.decode()
r = c.post("/login", {"email": "audyah@nilai.test", "password": "wrong"})
m2 = "Email atau kata sandi salah." in r.content.decode()
check("unknown email -> wrong-creds message", m1)
check("wrong password -> wrong-creds message", m2)

# 5. role logins + redirect matrix
for email, role, dest in [
    ("audyah@nilai.test", "admin", "/admin"),
    ("ramadan@nilai.test", "lecturer", "/lecturer/home"),
    ("aldy@nilai.test", "student", "/student/home"),
]:
    r = c.post("/login", {"email": email, "password": "password123"})
    ok = r.status_code == 302 and r["Location"] == dest
    check(f"{role} login -> {dest}", ok, f"{r.status_code} {r.get('Location', '')}")
    r2 = c.get(dest)
    check(f"{role} landing 200", r2.status_code == 200, r2.status_code)
    c.get("/logout")

# 6. admin subpages
c.post("/login", {"email": "audyah@nilai.test", "password": "password123"})
for path in ["/admin", "/admin/users", "/admin/settings", "/admin/branding"]:
    r = c.get(path)
    check(f"GET {path} 200", r.status_code == 200, r.status_code)

# 7. logout clears session
r = c.get("/logout")
check("logout redirects to /login", r.status_code == 302 and r["Location"] == "/login")
r = c.get("/admin")
check("after logout /admin -> /login", r.status_code == 302 and r["Location"] == "/login", str(r.status_code))

# 8. inactive account message
from accounts.models import User  # noqa: E402

u = User.objects.get(email="fitri@nilai.test")
u.status = "inactive"
u.save(update_fields=["status"])
r = c.post("/login", {"email": "fitri@nilai.test", "password": "password123"})
check("inactive -> Akun ini nonaktif.", "Akun ini nonaktif." in r.content.decode())
u.status = "active"
u.save(update_fields=["status"])

# 9. case-insensitive email
r = c.post("/login", {"email": "AUDYAH@nilai.test", "password": "password123"})
check("case-insensitive email login", r.status_code == 302 and r.get("Location") == "/admin")

width = max(len(lbl) for lbl, _, _ in results)
fails = 0
for lbl, ok, extra in results:
    if not ok:
        fails += 1
    print(f"{'PASS' if ok else 'FAIL'}  {lbl:<{width}}  {'' if ok else extra}")
print(f"\n{len(results) - fails}/{len(results)} passed")
