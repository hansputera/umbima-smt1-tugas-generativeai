"""Phase 3 accounts admin verification: users, import, settings, branding."""
import io
import os
import sys
from unittest import mock

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nilai.settings")

import django

django.setup()

from django.test import Client  # noqa: E402
from openpyxl import Workbook  # noqa: E402

from accounts.models import AppSettings, ModelSettings, User  # noqa: E402

ok = 0
fail = []


def check(name, cond, extra=""):
    global ok
    if cond:
        ok += 1
    else:
        fail.append(f"{name} {extra}"[:300])


admin = User.objects.get(email="audyah@nilai.test")
c = Client()
c.force_login(admin)


def make_xlsx(rows=(), headers=("Nama", "Email", "Peran", "Status"), sheet="Pengguna"):
    buf = io.BytesIO()
    wb = Workbook()
    ws = wb.active
    ws.title = sheet
    if headers:
        ws.append(list(headers))
    for r in rows:
        ws.append(list(r))
    wb.save(buf)
    return buf.getvalue()


# --- users page
r = c.get("/admin/users")
t = r.content.decode()
check("users 200", r.status_code == 200, r.status_code)
check("users desc", "Akun admin, dosen, dan mahasiswa." in t)
check("users tabs", "Ringkasan" in t and "Setelan model" in t)
check("users actions", "Impor Excel" in t and "Tambah pengguna" in t)
check("users table", "Audyahtul" in t or admin.name in t)
check("users role label", "Dosen" in t and "Mahasiswa" in t)
check("users crumb", "Pengguna" in t)

r = c.get("/admin/users?form=new")
t = r.content.decode()
check("users form", 'id="u-name"' in t and "Tambah pengguna" in t and 'placeholder="nama@nilai.test"' in t)

# validation
r = c.post("/admin/users", {"action": "save", "name": "", "email": "x", "role": "x", "status": "x"})
t = r.content.decode()
check("users err name", "Nama wajib diisi." in t)
check("users err role", "Peran tidak valid." in t)
check("users err status", "Status tidak valid." in t)

r = c.post("/admin/users", {"action": "save", "name": "Tes", "email": "", "role": "student", "status": "active"})
check("users err email empty", "Email wajib diisi." in r.content.decode())
r = c.post("/admin/users", {"action": "save", "name": "Tes", "email": "bad", "role": "student", "status": "active"})
check("users err email invalid", "Email tidak valid." in r.content.decode())
r = c.post("/admin/users", {"action": "save", "name": "Tes", "email": admin.email, "role": "student", "status": "active"})
check("users err dup", "Email sudah dipakai." in r.content.decode())

# create
r = c.post(
    "/admin/users",
    {"action": "save", "name": "Impor User", "email": "Impor.User@Nilai.TEST", "role": "lecturer", "status": "active"},
    follow=True,
)
check("users create redirect", r.status_code == 200)
nu = User.objects.get(email__iexact="impor.user@nilai.test")
check("users create lowercased", nu.email == "impor.user@nilai.test", nu.email)
check("users create role", nu.role == "lecturer")
check("users default pw", nu.check_password("password123"))
check("users create rendered", "Impor User" in r.content.decode())

# edit keeps password
old_hash = nu.password
r = c.post(
    "/admin/users",
    {"action": "save", "id": str(nu.id), "name": "Impor User 2", "email": "impor.user@nilai.test", "role": "lecturer", "status": "inactive"},
    follow=True,
)
nu.refresh_from_db()
check("users edit name", nu.name == "Impor User 2")
check("users edit status", nu.status == "inactive")
check("users edit keeps pw", nu.password == old_hash)

# toggle htmx on
r = c.post("/admin/users", {"action": "toggle_status", "id": str(nu.id)}, HTTP_HX_REQUEST="true")
t = r.content.decode()
check("users htmx table", 'id="users-table"' in t, t[:120])
check("users htmx oob", 'id="row-error" hx-swap-oob="true"' in t)
nu.refresh_from_db()
check("users toggled", nu.status == "active")
check("users htmx label", "Nonaktifkan" in t)

# toggle self -> error
r = c.post("/admin/users", {"action": "toggle_status", "id": str(admin.id)}, HTTP_HX_REQUEST="true")
check("users self toggle err", "Tidak bisa menonaktifkan akun sendiri." in r.content.decode())
r = c.post("/admin/users", {"action": "toggle_status", "id": ""}, HTTP_HX_REQUEST="true")
check("users empty id err", "Pengguna tidak ditemukan." in r.content.decode())

# --- template download
r = c.get("/admin/users/template")
check("template ctype", "spreadsheetml" in r["Content-Type"])
check("template disp", 'template-pengguna.xlsx' in r["Content-Disposition"])
check("template xlsx magic", r.content[:2] == b"PK")

# --- import: field errors
r = c.get("/admin/users?import=1")
t = r.content.decode()
check("import panel", "Impor pengguna dari Excel" in t)
check("import desc", "Isi template lalu unggah berkas .xlsx." in t)
check("import desc pw", "kata sandi default password123" in t)
check("import template link", "/admin/users/template" in t)
check("import buttons", "Pratinjau" in t and "Batal" in t)

r = c.post("/admin/users", {"action": "preview"})
check("preview no file", "Pilih berkas .xlsx terlebih dahulu." in r.content.decode())
# simulate wrong extension via SimpleUploadedFile
from django.core.files.uploadedfile import SimpleUploadedFile  # noqa: E402

r = c.post(
    "/admin/users",
    {"action": "preview", "file": SimpleUploadedFile("data.csv", b"a,b", content_type="text/csv")},
)
check("preview ext", "Format berkas harus .xlsx." in r.content.decode())
r = c.post(
    "/admin/users",
    {"action": "preview", "file": SimpleUploadedFile("data.xlsx", b"not-a-zip-file-content", content_type="application/vnd.ms-excel")},
)
check("preview not zip", "Berkas bukan file Excel yang valid." in r.content.decode())
big = SimpleUploadedFile("big.xlsx", b"x" * (2 * 1024 * 1024 + 1))
r = c.post("/admin/users", {"action": "preview", "file": big})
check("preview too big", "Ukuran berkas maksimal 2 MB." in r.content.decode())

# no header sheet
r = c.post(
    "/admin/users",
    {"action": "preview", "file": SimpleUploadedFile("t.xlsx", make_xlsx(headers=None, rows=[("a",), ("b",)]), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
)
check("preview no header", "Baris judul tidak ditemukan." in r.content.decode())

# --- real preview + confirm
payload = make_xlsx(
    rows=[
        ("Budi Doremi", "budi@contoh.test", "mahasiswa", "aktif"),
        ("Siti Aminah", "siti@contoh.test", "dosen", "aktif"),
        ("Budi Doremi", "budi@contoh.test", "mahasiswa", "aktif"),  # in-file dup
        ("Tau Ngapain", admin.email, "dosen", "aktif"),  # existing email
        ("", "kosong@x.test", "dosen", "aktif"),  # name missing
        ("Role Jelek", "role@x.test", "guru", "aktif"),  # bad role
        ("Status Jelek", "status@x.test", "dosen", "karyawan"),  # bad status
        ("Default Values", "default@x.test", "", ""),  # defaults
    ]
)
r = c.post(
    "/admin/users",
    {"action": "preview", "file": SimpleUploadedFile("pengguna.xlsx", payload, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
)
t = r.content.decode()
check("preview 8 rows", "<strong>8</strong> baris terbaca" in t.replace('fw500', 'strong') or "baris terbaca" in t)
check("preview summary", "siap diimpor" in t)
check("preview skip dup", "Email kembar di file ini." in t)
check("preview skip existing", "Email sudah terdaftar." in t)
check("preview err name", "Nama wajib diisi." in t)
import html as _html

tu = _html.unescape(t)
check("preview err role", 'Peran tidak valid: "guru". Gunakan Admin, Dosen, atau Mahasiswa.' in tu)
check("preview err status", 'Status tidak valid: "karyawan". Gunakan Aktif atau Nonaktif.' in tu)
check("preview siap", "Siap diimpor" in t)
check("preview default role student", "default@x.test" in t)
# extract rows json
import re as _re  # noqa: E402

m = _re.search(r'name="rows" value="([^"]*)"', t)
check("preview rows json", bool(m))
rows_json = (
    m.group(1)
    .replace("&quot;", '"')
    .replace("&#x27;", "'")
    .replace("&amp;", "&")
    .replace("&lt;", "<")
    .replace("&gt;", ">")
)
import json as _json  # noqa: E402

parsed = _json.loads(rows_json)
check("rows json len", len(parsed) == 8, len(parsed))
check("konfirmasi btn", "Konfirmasi impor (3)" in t, t[t.find("Konfirmasi") : t.find("Konfirmasi") + 40])

# confirm
r = c.post("/admin/users", {"action": "confirm", "rows": rows_json})
t = r.content.decode()
check("confirm result", "pengguna ditambahkan" in t)
check("confirm inserted 5", '<span class="fw500">5</span> pengguna ditambahkan' in t)
check("confirm errs count 1", "2 dilewati, 1 baris gagal" in t)
check("confirm skipped text", "budi@contoh.test (Email kembar di file ini.)" in t)
check("confirm errs text", "baris 6: Nama wajib diisi." in t)
check("confirm rescued role", User.objects.filter(email__iexact="role@x.test", role="student", status="active").exists())
check("confirm rescued status", User.objects.filter(email__iexact="status@x.test", role="lecturer", status="active").exists())
check("confirm created budi", User.objects.filter(email__iexact="budi@contoh.test").exists())
check("confirm created default", User.objects.filter(email__iexact="default@x.test").exists())
du = User.objects.get(email__iexact="default@x.test")
check("confirm default role", du.role == "student" and du.status == "active")
check("confirm pw", du.check_password("password123"))
check("confirm not existing", not User.objects.filter(email__iexact=f"TAU-NGAPAIN-SENTINEL@x.test").exists())

# confirm invalid rows
r = c.post("/admin/users", {"action": "confirm", "rows": "not-json"})
check("confirm bad rows", "Impor tidak valid atau kedaluwarsa." in r.content.decode())

# --- settings
ms = ModelSettings.objects.get(id=1)
_fields = [
    "provider_label", "model_name", "base_url", "api_key", "temperature",
    "max_tokens", "system_preamble", "emb_base_url", "emb_model_name",
    "emb_api_key",
]
from decimal import Decimal as _D  # noqa: E402

orig = {
    "provider_label": os.environ.get("LLM_PROVIDER_LABEL", "").strip() or "Penyedia utama",
    "model_name": os.environ.get("LLM_MODEL_NAME", "").strip(),
    "base_url": os.environ.get("LLM_BASE_URL", "").strip(),
    "api_key": os.environ.get("LLM_API_KEY", "").strip(),
    "temperature": _D("0.20"),
    "max_tokens": 1200,
    "system_preamble": "Anda adalah asisten penilaian mata kuliah. Balas dalam bahasa Indonesia yang singkat dan jelas.",
    "emb_base_url": os.environ.get("EMB_BASE_URL", "").strip(),
    "emb_model_name": os.environ.get("EMB_MODEL_NAME", "").strip(),
    "emb_api_key": os.environ.get("EMB_API_KEY", "").strip(),
}
for f in _fields:
    setattr(ms, f, orig[f])
ms.save()
r = c.get("/admin/settings")
t = r.content.decode()
check("settings 200", r.status_code == 200, r.status_code)
check("settings desc", "Berlaku untuk semua panggilan penilaian." in t)
check("settings tabs active", "Setelan model" in t)
_exp_temp = str(float(orig["temperature"]))
check("settings temp display", f'value="{_exp_temp}"' in t, t[t.find("temperature") : t.find("temperature") + 80])
check("settings maxtok", f'value="{ms.max_tokens}"' in t)
check("settings graded", "Grading aktif." in t or "Grading nonaktif" in t)
from django.conf import settings as _settings

check("settings emb dim", f"Dimensi vector: {_settings.EMBEDDING_DIM}." in t)
check("settings mask", "••••••" in t)
check("settings hint", "Kosongkan kolom untuk menghapus." in t)
check("settings test row", "Uji koneksi" in t and "Menguji pengaturan yang tersimpan." in t)
check("settings preamble", orig["system_preamble"][:40] in t)

# save validations
base = {
    "action": "save",
    "provider_label": ms.provider_label,
    "base_url": "ftp://bad",
    "model_name": "m",
    "temperature": "0.5",
    "max_tokens": "1200",
    "system_preamble": "p",
    "emb_base_url": "https://e.test/v1",
    "emb_model_name": "emb",
}
r = c.post("/admin/settings", base)
check("settings err scheme", "Alamat dasar harus diawali http:// atau https://." in r.content.decode())
base["base_url"] = "https://ok.test/v1"
base["temperature"] = "3"
r = c.post("/admin/settings", base)
check("settings err temp", "Temperature harus antara 0 dan 2." in r.content.decode())
base["temperature"] = "0.7"
base["max_tokens"] = "4.5"
r = c.post("/admin/settings", base)
check("settings err maxtok", "Max tokens harus bilangan bulat 1–16000." in r.content.decode())
base["max_tokens"] = "900"
base["system_preamble"] = ""
r = c.post("/admin/settings", base)
check("settings err preamble", "System preamble wajib diisi." in r.content.decode())
base["system_preamble"] = "preamble baru"
# api_key present but no model_name
r = c.post("/admin/settings", {**base, "api_key": "sk-test", "model_name": ""})
check("settings err model for key", "Nama model wajib diisi saat kunci API terisi." in r.content.decode())

# valid save
old_key = ms.api_key
r = c.post("/admin/settings", {**base, "temperature": "0.6", "max_tokens": "900"}, follow=True)
t = r.content.decode()
check("settings saved flash", "Pengaturan disimpan." in t)
ms.refresh_from_db()
check("settings db temp", float(ms.temperature) == 0.6, ms.temperature)
check("settings db maxtok", ms.max_tokens == 900)
check("settings db preamble", ms.system_preamble == "preamble baru")
check("settings key unchanged", ms.api_key == old_key)
check("settings temp reparse", 'value="0.6"' in t)

# api_key clearing: empty submitted clears
r = c.post("/admin/settings", {**base, "api_key": ""}, follow=True)
ms.refresh_from_db()
check("settings key cleared", ms.api_key == "")
# restore
r = c.post("/admin/settings", {**base, "api_key": old_key}, follow=True)
ms.refresh_from_db()
check("settings key restored", ms.api_key == old_key)

# reveal
r = c.post("/admin/settings/reveal", {"key": "api_key"})
check("settings reveal", r.content.decode() == old_key, r.content[:40])
r = c.post("/admin/settings/reveal", {"key": "emb_api_key"})
check("settings reveal emb", r.status_code == 200)

# test connection (mocked)
with mock.patch("accounts.views_admin.test_connection") as tc:
    tc.return_value = {"ok": True, "message": "Koneksi berhasil."}
    r = c.post("/admin/settings", {"action": "test"}, follow=True)
check("settings test ok", "Koneksi berhasil." in r.content.decode())
# not-configured path
ms2 = ModelSettings.objects.get(id=1)
saved = ms2.api_key
ms2.api_key = ""
ms2.save()
r = c.post("/admin/settings", {"action": "test"}, follow=True)
check("settings test unset", "Model belum disetel." in r.content.decode())
ms2.api_key = saved
ms2.save()

# restore original settings state
ms = ModelSettings.objects.get(id=1)
for f in _fields:
    setattr(ms, f, orig[f])
ms.save()

# --- branding
r = c.get("/admin/branding")
t = r.content.decode()
check("branding 200", r.status_code == 200)
check("branding desc", "Nama aplikasi, teks footer, dan logo yang tampil di seluruh halaman." in t)
check("branding hint", "Tampil di tab browser, navbar, dan breadcrumb." in t)
check("branding no logo", "Hapus logo" not in t)

r = c.post("/admin/branding", {"app_name": "", "footer_text": ""}, follow=False)
check("branding err name", "Nama aplikasi wajib diisi." in r.content.decode())
r = c.post("/admin/branding", {"app_name": "x" * 51, "footer_text": ""})
check("branding err len", "Nama aplikasi maksimal 50 karakter." in r.content.decode())
r = c.post("/admin/branding", {"app_name": "Ok", "footer_text": "y" * 121})
check("branding err footer", "Teks footer maksimal 120 karakter." in r.content.decode())

b0 = AppSettings.objects.get(id=1)
v0 = b0.logo_version
# logo: wrong type
r = c.post(
    "/admin/branding",
    {"app_name": "Ok", "footer_text": "F", "logo": SimpleUploadedFile("l.svg", b"<svg/>", content_type="image/svg+xml")},
)
check("branding logo type", "Logo harus berformat PNG, JPG, WebP, atau GIF." in r.content.decode())
# logo: too big
r = c.post(
    "/admin/branding",
    {"app_name": "Ok", "footer_text": "F", "logo": SimpleUploadedFile("l.png", b"a" * (512 * 1024 + 1), content_type="image/png")},
)
check("branding logo size", "Ukuran logo maksimal 512 KB." in r.content.decode())
# logo: valid
png = b"\x89PNG\r\n\x1a\n" + b"0" * 32
r = c.post(
    "/admin/branding",
    {"app_name": "NilaiApp", "footer_text": "Footer Teks", "logo": SimpleUploadedFile("l.png", png, content_type="image/png")},
    follow=True,
)
b = AppSettings.objects.get(id=1)
check("branding saved", b.app_name == "NilaiApp" and b.footer_text == "Footer Teks")
check("branding logo saved", b.logo is not None and b.logo_type == "image/png")
check("branding version", b.logo_version == v0 + 1, b.logo_version)
check("branding flash", "Pengaturan aplikasi disimpan." in r.content.decode())
check("branding logo preview", "Hapus logo" in r.content.decode() and "Logo aplikasi saat ini" in r.content.decode())
# logo endpoint reflects
r = c.get("/logo")
check("logo serves", r.status_code == 200 and r.content[:4] == b"\x89PNG")
# remove logo
r = c.post("/admin/branding", {"app_name": "NilaiApp", "footer_text": "Footer Teks", "remove_logo": "on"}, follow=True)
b.refresh_from_db()
check("branding logo removed", b.logo is None and b.logo_type is None)
check("branding version bump", b.logo_version == v0 + 2, b.logo_version)

# cleanup created users + restore branding
User.objects.filter(email__in=["impor.user@nilai.test", "budi@contoh.test", "siti@contoh.test", "default@x.test", "role@x.test", "status@x.test", "tau-ngapain@x.test"]).delete()
b.app_name = "MiniCourse"
b.footer_text = ""
b.updated_at = None
b.save()

# role gates
c2 = Client()
lect = User.objects.filter(role="lecturer").first()
c2.force_login(lect)
for url in ["/admin/users", "/admin/settings", "/admin/branding", "/admin/users/template", "/admin/settings/reveal"]:
    r = c2.post(url, {}) if "reveal" in url else c2.get(url)
    check(f"gate {url}", r.status_code == 302 and r["Location"] == "/lecturer/home", (r.status_code, r.get("Location")))

print(f"PASSED: {ok}")
if fail:
    print("FAILED:")
    for f_ in fail:
        print(" -", f_)
    sys.exit(1)
print("ALL OK")
