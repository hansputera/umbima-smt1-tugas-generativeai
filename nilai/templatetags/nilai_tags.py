"""Template filters/tags for Indonesian formatting and shared UI blocks."""

from datetime import datetime

from django import template
from django.utils import timezone

from nilai.context_processors import ROLE_LABEL

register = template.Library()

MONTHS = [
    "Jan", "Feb", "Mar", "Apr", "Mei", "Jun",
    "Jul", "Agu", "Sep", "Okt", "Nov", "Des",
]

STATUS = {
    "belum": ("Belum", "circle", "st-muted"),
    "draft": ("Draft", "pencil", "st-muted"),
    "terkumpul": ("Terkumpul", "clock", "st-accent"),
    "dinilai": ("Dinilai", "circle-check", "st-ok"),
    "perlu_review": ("Perlu review", "alert-triangle", "st-warn"),
    "active": ("Aktif", "circle-check", "st-ok"),
    "aktif": ("Aktif", "circle-check", "st-ok"),
    "inactive": ("Nonaktif", "circle", "st-muted"),
    "archived": ("Diarsipkan", "circle", "st-muted"),
    "published": ("Terbit", "circle-check", "st-ok"),
    "error": ("Gagal", "circle-x", "st-danger"),
}


def _fmt_date(value):
    """Port of fmtDate: '12 Okt 2025, 14:05' in local time; '—' when empty."""
    if value in (None, ""):
        return "—"
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return "—"
    if not isinstance(value, datetime):
        return "—"
    if timezone.is_naive(value):
        value = timezone.make_aware(value)
    try:
        value = timezone.localtime(value)
    except ValueError:
        return "—"
    return (
        f"{value.day} {MONTHS[value.month - 1]} {value.year}, "
        f"{value.hour:02d}:{value.minute:02d}"
    )


@register.filter
def fmt_date(value):
    return _fmt_date(value)


@register.filter
def role_label(value):
    return ROLE_LABEL.get(value, "")


@register.inclusion_tag("components/status.html")
def status_dot(key, label=None):
    """Port of StatusDot: colored icon + plain ink label."""
    status_label, icon, cls = STATUS.get(key, STATUS["belum"])
    if label:
        status_label = label
    return {"label": status_label, "icon": f"icons/{icon}.html", "cls": cls}


@register.inclusion_tag("components/breadcrumb.html", takes_context=True)
def breadcrumb(context):
    """Port of Breadcrumb: flat page crumbs, optional app-name root."""
    crumbs = [dict(c) for c in (context.get("crumbs") or [])]
    root = context.get("crumb_root")
    if root:
        crumbs = [{"label": context["branding"]["app_name"], "href": root}] + crumbs
    out = []
    for i, c in enumerate(crumbs):
        c["sep"] = i > 0
        c["last"] = i == len(crumbs) - 1
        out.append(c)
    return {"crumbs": out}


@register.inclusion_tag("components/flashes.html", takes_context=True)
def flashes(context):
    """Render Django messages as ErrorLine/Notice (Node rowError / Notice)."""
    return {"flashes": list(context.get("messages") or [])}


_ADMIN_TABS = [
    ("/admin", "Ringkasan", True),
    ("/admin/users", "Pengguna", False),
    ("/admin/courses", "Mata kuliah", False),
    ("/admin/periods", "Periode", False),
    ("/admin/placement", "Penempatan", False),
    ("/admin/branding", "Aplikasi", False),
    ("/admin/settings", "Setelan model", False),
]


@register.inclusion_tag("components/admin-tabs.html", takes_context=True)
def admin_tabs(context):
    path = context["request"].path
    tabs = []
    for href, label, exact in _ADMIN_TABS:
        active = path == href if exact else path == href or path.startswith(href + "/")
        tabs.append({"href": href, "label": label, "active": active})
    return {"tabs": tabs}


@register.filter
def fmt_nilai(value):
    """Port of fmtNilai: integer as-is, else two decimals; '—' when empty."""
    if value in (None, ""):
        return "—"
    try:
        n = float(value)
    except (TypeError, ValueError):
        return "—"
    if n == int(n):
        return str(int(n))
    return f"{n:.2f}"


# ---- Phase 4: lecturer course surfaces ----

TYPE_LABEL = {
    "essay": "Esai",
    "pg": "Pilihan ganda",
    "pdf": "Unggah PDF",
    "docx": "Unggah DOCX",
}
MODE_LABEL = {"review": "Review dulu", "langsung": "Langsung rilis"}

ACTIVITY = {
    "materi": ("book-open", "#0f6cbf"),
    "essay": ("pen-line", "#d9534f"),
    "pg": ("list-checks", "#f0ad4e"),
    "pdf": ("file-down", "#5cb85c"),
    "docx": ("file-up", "#5bc0de"),
}


@register.filter
def type_label(value):
    return TYPE_LABEL.get(value, value or "")


@register.filter
def mode_label(value):
    return MODE_LABEL.get(value, value or "")


@register.inclusion_tag("components/activity-icon.html")
def activity_icon(type_, size=40):
    """Port of ActivityIcon: colored rounded square with a white glyph."""
    icon, color = ACTIVITY.get(type_, ACTIVITY["materi"])
    return {"icon": f"icons/{icon}.html", "color": color, "size": int(size)}


@register.inclusion_tag("components/course-tabs.html", takes_context=True)
def course_tabs(context):
    """Port of courseTabs: path-driven tab bar for course pages."""
    course = context.get("course")
    role = context["user"].role
    base = f"/{role}/courses/{course['id']}"
    tabs = [
        ("Kursus", base, "prefix"),
        ("Peserta", base + "/peserta", "exact"),
        ("Tugas", base + "/tugas", "exact"),
        ("Nilai", base + "/nilai", "exact"),
    ]
    if role == "lecturer":
        tabs.append(("Pengaturan", base + "/pengaturan", "exact"))
    path = context["request"].path
    out = []
    for label, href, mode in tabs:
        if mode == "prefix":
            active = path == href or path.startswith(href + "/topics/")
        else:
            active = path == href
        out.append({"label": label, "href": href, "active": active})
    return {"tabs": out}


@register.inclusion_tag("components/course-sidebar.html", takes_context=True)
def course_sidebar(context):
    return {
        "frame": context.get("frame"),
        "course": context.get("course"),
        "active_topic_id": str(context.get("active_topic_id") or ""),
        "role": context["user"].role,
    }
