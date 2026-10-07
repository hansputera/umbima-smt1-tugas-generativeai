"""Shell context: branding, role label, and role-based nav items (port of
src/lib/branding.ts + role layouts + src/lib/status.ts ROLE_LABEL)."""

from accounts.models import AppSettings

ROLE_LABEL = {"admin": "Admin", "lecturer": "Dosen", "student": "Mahasiswa"}

NAV_BY_ROLE = {
    "admin": [
        ("Beranda", "/admin", True),
        ("Kursus saya", "/admin/courses", False),
        ("Administrasi", "/admin/users", False),
    ],
    "lecturer": [
        ("Beranda", "/lecturer/home", True),
        ("Kursus saya", "/lecturer/courses", False),
        ("Pengumpulan", "/lecturer/submissions", False),
    ],
    "student": [
        ("Beranda", "/student/home", True),
        ("Kursus saya", "/student/courses", False),
        ("Tugas", "/student/tasks", False),
    ],
}

ROLE_HOME = {"admin": "/admin", "lecturer": "/lecturer/home", "student": "/student/home"}


def _active_role(user):
    """Mirror ProxyMiddleware's notion of an active session user."""
    if user is None or not getattr(user, "is_authenticated", False):
        return None
    if getattr(user, "status", None) != "active":
        return None
    return getattr(user, "role", None)


def shell(request):
    row, _ = AppSettings.objects.get_or_create(id=1)
    footer_text = row.footer_text or ""
    has_logo = row.logo is not None
    branding = {
        "app_name": row.app_name,
        "footer_text": footer_text,
        "footer_of": footer_text.strip() or row.app_name,
        "has_logo": has_logo,
        "logo_src": f"/logo?v={row.logo_version}" if has_logo else None,
        "logo_version": row.logo_version,
    }

    user = getattr(request, "user", None)
    role = _active_role(user)

    nav_items = []
    for label, href, exact in NAV_BY_ROLE.get(role, []):
        path = request.path
        active = path == href if exact else path == href or path.startswith(href + "/")
        nav_items.append({"label": label, "href": href, "active": active})

    return {
        "branding": branding,
        "role_label": ROLE_LABEL.get(role, ""),
        "user_name": getattr(user, "name", "") if role else "",
        "home_href": ROLE_HOME.get(role, "/login"),
        "nav_items": nav_items,
    }
