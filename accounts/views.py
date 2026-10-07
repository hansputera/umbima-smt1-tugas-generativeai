from django.contrib.auth import authenticate, login as auth_login, logout
from django.shortcuts import redirect, render

from .models import ModelSettings, User

ROLE_HOME = {"admin": "/admin", "lecturer": "/lecturer/home", "student": "/student/home"}

SYSTEM_PREAMBLE_DEFAULT = (
    "Anda adalah asisten penilaian mata kuliah. "
    "Balas dalam bahasa Indonesia yang singkat dan jelas."
)


def login_view(request):
    error = None
    if request.method == "POST":
        email = (request.POST.get("email") or "").strip()
        password = request.POST.get("password") or ""
        if not email or not password:
            error = "Email dan kata sandi wajib diisi."
        else:
            user = authenticate(request, username=email, password=password)
            if user is None:
                error = "Email atau kata sandi salah."
            elif user.status != "active":
                error = "Akun ini nonaktif."
            elif user.role not in ROLE_HOME:
                error = "Peran tidak dikenal."
            else:
                auth_login(request, user)
                return redirect(ROLE_HOME[user.role])
    return render(request, "login.html", {"error": error})


def logout_view(request):
    logout(request)
    return redirect("/login")


def admin_home(request):
    ms, _ = ModelSettings.objects.get_or_create(
        id=1, defaults={"system_preamble": SYSTEM_PREAMBLE_DEFAULT}
    )
    recent = (
        User.objects.order_by("-created_at")
        .values("name", "email", "role", "status", "created_at")[:8]
    )
    model_ok = all(
        getattr(ms, f).strip() for f in ("api_key", "base_url", "model_name")
    )
    emb_ok = all(
        getattr(ms, f).strip() for f in ("emb_api_key", "emb_base_url", "emb_model_name")
    )
    return render(
        request,
        "admin/home.html",
        {
            "model_settings": ms,
            "model_ok": model_ok,
            "emb_ok": emb_ok,
            "recent": recent,
            "crumbs": [{"label": "Beranda"}],
        },
    )


def users_page(request):
    return render(request, "admin/users.html")


def users_template(request):
    from django.http import HttpResponseNotFound

    return HttpResponseNotFound("Belum tersedia")


def settings_page(request):
    return render(request, "admin/settings.html")


def branding_page(request):
    return render(request, "admin/branding.html")
