"""Admin pages: users + Excel import, settings, branding (port of src/app/admin)."""

import io
import json
import math
import re
import uuid

from django.contrib import messages
from django.db import connection
from django.db.models import Case, IntegerField, When
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from accounts.models import AppSettings, ModelSettings, User
from accounts.users_import import (
    IMPORT_MAX_BYTES,
    IMPORT_MAX_ROWS,
    mark_existing_emails,
    normalize_row,
    parse_users_workbook,
    sanitize_client_rows,
    summarize,
)
from assessment.ai import test_connection
from nilai.context_processors import ROLE_LABEL

ROLES = ["admin", "lecturer", "student"]
STATUSES = ["active", "inactive"]
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
DEFAULT_PASSWORD = "password123"
MAX_LOGO_BYTES = 512 * 1024
LOGO_TYPES = ["image/png", "image/jpeg", "image/webp", "image/gif"]
HTTP_URL_RE = re.compile(r"^https?://", re.IGNORECASE)

PAGE_404 = "Halaman tidak ditemukan."


def _uuid(value):
    try:
        return uuid.UUID(str(value).strip())
    except (ValueError, TypeError, AttributeError):
        return None


def _js_number(raw):
    """Node Number(x): full-string numeric parse (float or integer)."""
    s = (raw or "").strip()
    if s == "":
        return 0.0  # Number("") === 0
    if re.fullmatch(r"[+-]?0[xX][0-9a-fA-F]+", s):
        sign = -1.0 if s[0] == "-" else 1.0
        return sign * float(int(s.lstrip("+-"), 16))
    if re.fullmatch(r"[+-]?0[bB][01]+", s):
        sign = -1.0 if s[0] == "-" else 1.0
        return sign * float(int(s.lstrip("+-"), 2))
    if re.fullmatch(r"[+-]?0[oO][0-7]+", s):
        sign = -1.0 if s[0] == "-" else 1.0
        return sign * float(int(s.lstrip("+-"), 8))
    try:
        return float(s)
    except ValueError:
        return float("nan")


def _parse_int(raw):
    n = _js_number(raw)
    if math.isnan(n) or math.isinf(n) or n != int(n):
        return None
    return int(n)


def _js_number_str(value):
    f = float(value)
    if math.isnan(f) or math.isinf(f):
        return str(value)
    if f.is_integer():
        return str(int(f))
    return repr(f)


def _mask_key(key):
    k = (key or "").strip()
    if not k:
        return ""
    if len(k) <= 8:
        return "•" * 8
    return k[:3] + "•" * 6 + k[-4:]


def _not_found():
    from django.http import HttpResponseNotFound

    return HttpResponseNotFound(PAGE_404)


def _table_response(request, partial, ctx, error=None):
    if request.htmx:
        ctx["row_error"] = error
        ctx["oob"] = True
        return render(request, partial, ctx)
    if error:
        messages.error(request, error)
    return redirect(request.path)


# ---- Users ----


def _users_ordered():
    role_order = Case(
        When(role="admin", then=0),
        When(role="lecturer", then=1),
        default=2,
        output_field=IntegerField(),
    )
    return list(User.objects.order_by(role_order, "name"))


def _users_ctx(form=None, errors=None, panel_open=False, **extra):
    ctx = {
        "users": _users_ordered(),
        "form": form,
        "form_errors": errors or {},
        "panel_open": panel_open,
        "crumbs": [{"label": "Pengguna"}],
    }
    ctx.update(extra)
    return ctx


def users_page(request):
    if request.method == "POST":
        return _users_post(request)
    form = None
    raw = request.GET.get("form", "")
    if raw == "new":
        form = {
            "id": "",
            "name": "",
            "email": "",
            "role": "student",
            "status": "active",
        }
    elif raw:
        uid = _uuid(raw)
        user = User.objects.filter(id=uid).first() if uid else None
        if user is None:
            return redirect("/admin/users")
        form = {
            "id": str(user.id),
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "status": user.status,
        }
    panel_open = request.GET.get("import") == "1" and form is None
    return render(
        request, "admin/users.html", _users_ctx(form, panel_open=panel_open)
    )


def _users_post(request):
    action = request.POST.get("action", "")
    if action == "save":
        return _save_user(request)
    if action == "toggle_status":
        return _toggle_user_status(request)
    if action == "preview":
        return _import_preview(request)
    if action == "confirm":
        return _import_confirm(request)
    return redirect("/admin/users")


def _save_user(request):
    post = request.POST
    uid_raw = (post.get("id") or "").strip()
    uid = _uuid(uid_raw)
    name = (post.get("name") or "").strip()
    email = (post.get("email") or "").strip().lower()
    role = (post.get("role") or "").strip()
    status = (post.get("status") or "").strip()

    form = {
        "id": uid_raw,
        "name": name,
        "email": (post.get("email") or "").strip(),
        "role": role,
        "status": status,
    }
    errors = {}
    if not name:
        errors["name"] = "Nama wajib diisi."
    if not email:
        errors["email"] = "Email wajib diisi."
    elif not EMAIL_RE.match(email):
        errors["email"] = "Email tidak valid."
    if role not in ROLES:
        errors["role"] = "Peran tidak valid."
    if status not in STATUSES:
        errors["status"] = "Status tidak valid."
    if not errors:
        dup = User.objects.filter(email__iexact=email)
        if uid:
            dup = dup.exclude(id=uid)
        if dup.exists():
            errors["email"] = "Email sudah dipakai."
    if errors:
        return render(
            request, "admin/users.html", _users_ctx(form, errors=errors)
        )

    if uid_raw:
        User.objects.filter(id=uid).update(
            name=name, email=email, role=role, status=status
        )
    else:
        user = User(name=name, email=email, role=role, status=status)
        user.set_password(DEFAULT_PASSWORD)
        user.save()
    return redirect("/admin/users")


def _toggle_user_status(request):
    uid = _uuid(request.POST.get("id") or "")
    error = None
    if not uid:
        error = "Pengguna tidak ditemukan."
    elif request.user and uid == request.user.id:
        error = "Tidak bisa menonaktifkan akun sendiri."
    else:
        user = User.objects.filter(id=uid).first()
        if user is not None:
            user.status = "inactive" if user.status == "active" else "active"
            user.save(update_fields=["status"])
    return _table_response(request, "admin/partials/users_table.html", _users_ctx(), error)


def _import_preview(request):
    file = request.FILES.get("file")
    if file is None or file.size == 0 or not (file.name or "").strip():
        return render(
            request,
            "admin/users.html",
            _users_ctx(
                panel_open=True, imp_error="Pilih berkas .xlsx terlebih dahulu."
            ),
        )
    if not file.name.lower().endswith(".xlsx"):
        return render(
            request,
            "admin/users.html",
            _users_ctx(
                panel_open=True, imp_error="Format berkas harus .xlsx."
            ),
        )
    if file.size > IMPORT_MAX_BYTES:
        return render(
            request,
            "admin/users.html",
            _users_ctx(
                panel_open=True, imp_error="Ukuran berkas maksimal 2 MB."
            ),
        )

    data = file.read()
    if len(data) < 4 or data[0] != 0x50 or data[1] != 0x4B:
        return render(
            request,
            "admin/users.html",
            _users_ctx(
                panel_open=True,
                imp_error="Berkas bukan file Excel yang valid.",
            ),
        )

    rows, file_errors = parse_users_workbook(data)
    if not rows:
        return render(
            request,
            "admin/users.html",
            _users_ctx(
                panel_open=True,
                imp_error=None,
                imp_file_errors=file_errors or ["Tidak ada baris data."],
            ),
        )
    mark_existing_emails(rows)
    preview = summarize(rows)
    preview["rows"] = rows
    preview["rows_json"] = json.dumps(
        [r.as_dict() for r in rows], ensure_ascii=False
    )
    preview["file_errors"] = file_errors
    return render(
        request,
        "admin/users.html",
        _users_ctx(panel_open=True, preview=preview),
    )


def _import_confirm(request):
    raw = (request.POST.get("rows") or "").strip()
    try:
        parsed = json.loads(raw)
    except ValueError:
        parsed = None
    rows = sanitize_client_rows(parsed)
    if rows is None:
        return render(
            request,
            "admin/users.html",
            _users_ctx(
                panel_open=True,
                confirm_error="Impor tidak valid atau kedaluwarsa. Unggah ulang berkas.",
            ),
        )
    mark_existing_emails(rows)

    skipped = []
    errors = []
    ready = []
    for row in rows:
        if row.error:
            errors.append({"line": row.line, "message": row.error})
        elif row.skip:
            skipped.append({"email": row.email, "reason": row.skip})
        else:
            ready.append(row)

    inserted = 0
    if ready:
        from django.contrib.auth.hashers import make_password

        pwd_hash = make_password(DEFAULT_PASSWORD)
        with connection.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (name, email, role, status, password_hash)
                SELECT u.name, u.email, u.role, u.status, %s
                FROM unnest(%s::text[], %s::text[], %s::text[], %s::text[])
                  AS u(name, email, role, status)
                ON CONFLICT (email) DO NOTHING
                RETURNING lower(email) AS email
                """,
                [
                    pwd_hash,
                    [r.name for r in ready],
                    [r.email for r in ready],
                    [r.role for r in ready],
                    [r.status for r in ready],
                ],
            )
            inserted_set = {r[0] for r in cur.fetchall()}
        inserted = len(inserted_set)
        for row in ready:
            if row.email not in inserted_set:
                skipped.append(
                    {"email": row.email, "reason": "Email sudah terdaftar."}
                )

    preview = summarize(rows)
    preview["rows"] = rows
    preview["rows_json"] = json.dumps(
        [r.as_dict() for r in rows], ensure_ascii=False
    )
    preview["file_errors"] = []
    result = {
        "inserted": inserted,
        "skipped": skipped,
        "errors": errors,
        "total": len(rows),
    }
    skipped_text = "; ".join(
        f"{s['email']} ({s['reason']})" for s in skipped[:20]
    )
    if len(skipped) > 20:
        skipped_text += f"; dan {len(skipped) - 20} lainnya"
    errors_text = "; ".join(
        f"baris {e['line']}: {e['message']}" for e in errors[:20]
    )
    if len(errors) > 20:
        errors_text += f"; dan {len(errors) - 20} lainnya"
    result["skipped_text"] = skipped_text
    result["errors_text"] = errors_text
    return render(
        request,
        "admin/users.html",
        _users_ctx(panel_open=True, preview=preview, result=result),
    )


def users_template(request):
    from openpyxl import Workbook
    from openpyxl.styles import Font

    wb = Workbook()
    ws = wb.active
    ws.title = "Pengguna"
    ws.append(["Nama", "Email", "Peran", "Status"])
    for cell in ws[1]:
        cell.font = Font(bold=True)
    ws.append(["Budi Santoso", "budi@contoh.test", "mahasiswa", "aktif"])
    ws.append(["Siti Aminah", "siti@contoh.test", "dosen", "aktif"])
    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 30
    ws.column_dimensions["C"].width = 14
    ws.column_dimensions["D"].width = 12

    guide = wb.create_sheet("Petunjuk")
    guide.append(["Cara pakai:"])
    guide.append(
        ["1. Isi sheet Pengguna, satu baris per pengguna. Jangan mengubah baris judul."]
    )
    guide.append(
        ["2. Peran: Admin, Dosen, atau Mahasiswa. Status: Aktif atau Nonaktif (kosong = Aktif)."]
    )
    guide.append(["3. Semua pengguna baru memakai kata sandi default: password123"])
    guide.append(["4. Email yang sudah terdaftar akan dilewati, bukan diubah."])
    guide.append(["5. Maksimal 500 baris per impor."])
    guide.column_dimensions["A"].width = 90

    buf = io.BytesIO()
    wb.save(buf)
    response = HttpResponse(
        buf.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = (
        'attachment; filename="template-pengguna.xlsx"'
    )
    return response


# ---- Settings ----


def _model_settings():
    ms, _ = ModelSettings.objects.get_or_create(
        id=1,
        defaults={
            "system_preamble": (
                "Anda adalah asisten penilaian mata kuliah. "
                "Balas dalam bahasa Indonesia yang singkat dan jelas."
            )
        },
    )
    return ms


def _settings_ctx(ms, form=None, errors=None, **extra):
    temperature = _js_number_str(ms.temperature)
    max_tokens = str(ms.max_tokens)
    api_key_masked = _mask_key(ms.api_key)
    emb_api_key_masked = _mask_key(ms.emb_api_key)
    if form:
        temperature = form.get("temperature", temperature)
        max_tokens = form.get("max_tokens", max_tokens)
        api_key_masked = form.get("api_key_masked", api_key_masked)
        emb_api_key_masked = form.get("emb_api_key_masked", emb_api_key_masked)
    ctx = {
        "provider_label": form.get("provider_label", ms.provider_label) if form else ms.provider_label,
        "base_url": form.get("base_url", ms.base_url) if form else ms.base_url,
        "api_key_masked": api_key_masked,
        "api_key_submitted": form.get("api_key_submitted", False) if form else False,
        "model_name": form.get("model_name", ms.model_name) if form else ms.model_name,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "system_preamble": form.get("system_preamble", ms.system_preamble) if form else ms.system_preamble,
        "emb_base_url": form.get("emb_base_url", ms.emb_base_url) if form else ms.emb_base_url,
        "emb_model_name": form.get("emb_model_name", ms.emb_model_name) if form else ms.emb_model_name,
        "emb_api_key_masked": emb_api_key_masked,
        "emb_api_key_submitted": form.get("emb_api_key_submitted", False) if form else False,
        "model_configured": all(
            getattr(ms, f).strip()
            for f in ("api_key", "base_url", "model_name")
        ),
        "emb_configured": all(
            getattr(ms, f).strip()
            for f in ("emb_api_key", "emb_base_url", "emb_model_name")
        ),
        "emb_dim": _emb_dim(),
        "form_errors": errors or {},
        "crumbs": [{"label": "Setelan model"}],
    }
    ctx.update(extra)
    return ctx


def _emb_dim():
    from django.conf import settings

    return settings.EMBEDDING_DIM


def settings_page(request):
    if request.method == "POST":
        if request.POST.get("action") == "test":
            return _settings_test(request)
        return _settings_save(request)
    ms = _model_settings()
    test = request.session.pop("settings_test", None)
    return render(request, "admin/settings.html", _settings_ctx(ms, test=test))


def _settings_save(request):
    ms = _model_settings()
    post = request.POST
    form = {
        "provider_label": (post.get("provider_label") or "").strip(),
        "base_url": (post.get("base_url") or "").strip(),
        "model_name": (post.get("model_name") or "").strip(),
        "temperature": (post.get("temperature") or "").strip(),
        "max_tokens": (post.get("max_tokens") or "").strip(),
        "system_preamble": (post.get("system_preamble") or "").strip(),
        "emb_base_url": (post.get("emb_base_url") or "").strip(),
        "emb_model_name": (post.get("emb_model_name") or "").strip(),
        "api_key_submitted": "api_key" in post,
        "emb_api_key_submitted": "emb_api_key" in post,
    }
    api_key = (
        (post.get("api_key") or "").strip()
        if "api_key" in post
        else ms.api_key
    )
    emb_api_key = (
        (post.get("emb_api_key") or "").strip()
        if "emb_api_key" in post
        else ms.emb_api_key
    )

    errors = {}
    if form["base_url"] and not HTTP_URL_RE.match(form["base_url"]):
        errors["base_url"] = "Alamat dasar harus diawali http:// atau https://."
    if api_key and not form["base_url"]:
        errors["base_url"] = "Alamat dasar wajib diisi saat kunci API terisi."
    if api_key and not form["model_name"]:
        errors["model_name"] = "Nama model wajib diisi saat kunci API terisi."

    temperature = _js_number(form["temperature"])
    if (
        form["temperature"] == ""
        or math.isnan(temperature)
        or temperature < 0
        or temperature > 2
    ):
        errors["temperature"] = "Temperature harus antara 0 dan 2."

    max_tokens = _parse_int(form["max_tokens"])
    if (
        form["max_tokens"] == ""
        or max_tokens is None
        or max_tokens < 1
        or max_tokens > 16000
    ):
        errors["max_tokens"] = "Max tokens harus bilangan bulat 1–16000."

    if not form["system_preamble"]:
        errors["system_preamble"] = "System preamble wajib diisi."

    if emb_api_key and not HTTP_URL_RE.match(form["emb_base_url"]):
        errors["emb_base_url"] = "Alamat dasar harus diawali http:// atau https://."
    if emb_api_key and not form["emb_model_name"]:
        errors["emb_model_name"] = "Nama model embedding wajib diisi."

    if errors:
        form["api_key_masked"] = api_key if "api_key" in post else _mask_key(ms.api_key)
        form["emb_api_key_masked"] = (
            emb_api_key
            if "emb_api_key" in post
            else _mask_key(ms.emb_api_key)
        )
        return render(
            request,
            "admin/settings.html",
            _settings_ctx(ms, form=form, errors=errors),
        )

    ms.provider_label = form["provider_label"]
    ms.base_url = form["base_url"]
    ms.api_key = api_key
    ms.model_name = form["model_name"]
    ms.temperature = temperature
    ms.max_tokens = max_tokens
    ms.system_preamble = form["system_preamble"]
    ms.emb_base_url = form["emb_base_url"]
    ms.emb_api_key = emb_api_key
    ms.emb_model_name = form["emb_model_name"]
    ms.updated_at = timezone.now()
    ms.updated_by = request.user
    ms.save()
    messages.success(request, "Pengaturan disimpan.")
    return redirect("/admin/settings")


def _settings_test(request):
    ms = _model_settings()
    if not all(
        getattr(ms, f).strip() for f in ("api_key", "base_url", "model_name")
    ):
        request.session["settings_test"] = {
            "ok": False,
            "message": "Model belum disetel.",
        }
    else:
        request.session["settings_test"] = test_connection(ms)
    return redirect("/admin/settings")


def settings_reveal(request):
    if request.method != "POST":
        return _not_found()
    ms = _model_settings()
    key = request.POST.get("key", "")
    if key == "api_key":
        return HttpResponse(ms.api_key, content_type="text/plain")
    if key == "emb_api_key":
        return HttpResponse(ms.emb_api_key, content_type="text/plain")
    return HttpResponse("", content_type="text/plain")


# ---- Branding ----


def _branding_row():
    row, _ = AppSettings.objects.get_or_create(id=1)
    return row


def branding_page(request):
    if request.method == "POST":
        return _branding_save(request)
    row = _branding_row()
    return render(
        request,
        "admin/branding.html",
        {
            "app_name": row.app_name,
            "footer_text": row.footer_text,
            "form_errors": {},
            "crumbs": [{"label": "Aplikasi"}],
        },
    )


def _branding_save(request):
    row = _branding_row()
    post = request.POST
    app_name = (post.get("app_name") or "").strip()
    footer_text = (post.get("footer_text") or "").strip()
    remove_logo = post.get("remove_logo") == "on"

    errors = {}
    if not app_name:
        errors["app_name"] = "Nama aplikasi wajib diisi."
    elif len(app_name) > 50:
        errors["app_name"] = "Nama aplikasi maksimal 50 karakter."
    if len(footer_text) > 120:
        errors["footer_text"] = "Teks footer maksimal 120 karakter."

    logo = None
    logo_type = None
    file = request.FILES.get("logo")
    if file is not None and file.size > 0 and (file.name or "").strip():
        ctype = (file.content_type or "").lower()
        if ctype not in LOGO_TYPES:
            errors["logo"] = "Logo harus berformat PNG, JPG, WebP, atau GIF."
        elif file.size > MAX_LOGO_BYTES:
            errors["logo"] = "Ukuran logo maksimal 512 KB."
        else:
            logo = file.read()
            logo_type = ctype

    if errors:
        return render(
            request,
            "admin/branding.html",
            {
                "app_name": app_name,
                "footer_text": footer_text,
                "form_errors": errors,
                "crumbs": [{"label": "Aplikasi"}],
            },
        )

    now = timezone.now()
    if logo is not None:
        row.app_name = app_name
        row.footer_text = footer_text
        row.logo = logo
        row.logo_type = logo_type
        row.logo_version = row.logo_version + 1
        row.updated_at = now
        row.updated_by = request.user
        row.save()
    elif remove_logo:
        row.app_name = app_name
        row.footer_text = footer_text
        row.logo = None
        row.logo_type = None
        row.logo_version = row.logo_version + 1
        row.updated_at = now
        row.updated_by = request.user
        row.save()
    else:
        row.app_name = app_name
        row.footer_text = footer_text
        row.updated_at = now
        row.updated_by = request.user
        row.save()
    messages.success(request, "Pengaturan aplikasi disimpan.")
    return redirect("/admin/branding")
