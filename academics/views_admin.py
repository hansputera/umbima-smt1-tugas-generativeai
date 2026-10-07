"""Admin pages: periods, placement, courses (port of src/app/admin/*)."""

import math
import re
import uuid

from django.contrib import messages
from django.db import connection
from django.db.models import BooleanField, Count, ExpressionWrapper, F, Q
from django.http import HttpResponseNotFound
from django.shortcuts import redirect, render
from django.utils import timezone

from accounts.models import User

from .models import Course, CourseLecturer, Enrollment, Period

PAGE_404 = "Halaman tidak ditemukan."


def _uuid(value):
    try:
        return uuid.UUID(str(value).strip())
    except (ValueError, TypeError, AttributeError):
        return None


def _parse_int(raw):
    """Node Number(x) semantics for integer fields: full-string numeric parse."""
    s = (raw or "").strip()
    if not s:
        return None
    if re.fullmatch(r"[+-]?0[xX][0-9a-fA-F]+", s):
        sign = -1 if s[0] == "-" else 1
        return sign * int(s.lstrip("+-"), 16)
    if re.fullmatch(r"[+-]?0[bB][01]+", s):
        sign = -1 if s[0] == "-" else 1
        return sign * int(s.lstrip("+-"), 2)
    if re.fullmatch(r"[+-]?0[oO][0-7]+", s):
        sign = -1 if s[0] == "-" else 1
        return sign * int(s.lstrip("+-"), 8)
    try:
        f = float(s)
    except ValueError:
        return None
    if not math.isfinite(f) or f != int(f):
        return None
    return int(f)


def _period_options():
    return list(Period.objects.order_by("-is_active", "-created_at", "name"))


def _lecturer_names():
    grouped = {}
    pairs = CourseLecturer.objects.order_by("user__name").values_list(
        "course_id", "user__name"
    )
    for course_id, name in pairs:
        grouped.setdefault(course_id, []).append(name)
    return {cid: ", ".join(names) for cid, names in grouped.items()}


def _student_counts():
    rows = Enrollment.objects.values("course_id").annotate(n=Count("student_id"))
    return {r["course_id"]: r["n"] for r in rows}


def _admin_courses():
    return list(
        Course.objects.select_related("period").order_by(
            F("archived_at").asc(nulls_first=True),
            "-period__is_active",
            "period__created_at",
            "code",
            "section",
        )
    )


def _placement_courses():
    return list(
        Course.objects.select_related("period")
        .filter(archived_at__isnull=True)
        .order_by("-period__is_active", "period__created_at", "code", "section")
    )


def _not_found():
    return HttpResponseNotFound(PAGE_404)


def _table_response(request, partial, ctx, error=None):
    """HTMX toggle -> partial with OOB error; plain POST -> redirect + flash."""
    if request.htmx:
        ctx["row_error"] = error
        ctx["oob"] = True
        return render(request, partial, ctx)
    if error:
        messages.error(request, error)
    return redirect(request.path)


def _toggle_join(table, col_a, col_b, a, b):
    with connection.cursor() as cur:
        cur.execute(
            f"SELECT 1 FROM {table} WHERE {col_a} = %s AND {col_b} = %s", [a, b]
        )
        exists = cur.fetchone() is not None
        if exists:
            cur.execute(
                f"DELETE FROM {table} WHERE {col_a} = %s AND {col_b} = %s", [a, b]
            )
        else:
            cur.execute(
                f"INSERT INTO {table} ({col_a}, {col_b}) VALUES (%s, %s)", [a, b]
            )


# ---- Periods ----


def _periods_ctx(form=None, errors=None, row_error=None):
    periods = list(
        Period.objects.annotate(class_count=Count("courses")).order_by(
            "-is_active", "-created_at", "name"
        )
    )
    return {
        "periods": periods,
        "form": form,
        "form_errors": errors or {},
        "row_error": row_error,
        "crumbs": [{"label": "Periode"}],
    }


def periods_page(request):
    if request.method == "POST":
        return _periods_post(request)
    form = None
    raw = request.GET.get("form", "")
    if raw == "new":
        form = {"id": "", "name": ""}
    elif raw:
        pid = _uuid(raw)
        period = Period.objects.filter(id=pid).first() if pid else None
        if not period:
            return redirect("/admin/periods")
        form = {"id": str(period.id), "name": period.name}
    return render(request, "academics/periods.html", _periods_ctx(form))


def _periods_post(request):
    action = request.POST.get("action", "")
    if action == "save":
        name = (request.POST.get("name") or "").strip()
        pid = (request.POST.get("id") or "").strip()
        errors = {}
        if not name:
            errors["name"] = "Nama periode wajib diisi."
        elif len(name) > 60:
            errors["name"] = "Nama periode maksimal 60 karakter."
        else:
            dup = Period.objects.filter(name__iexact=name)
            uid = _uuid(pid)
            if uid:
                dup = dup.exclude(id=uid)
            if dup.exists():
                errors["name"] = "Nama periode sudah dipakai."
        if errors:
            return render(
                request,
                "academics/periods.html",
                _periods_ctx(form={"id": pid, "name": name}, errors=errors),
            )
        uid = _uuid(pid)
        if pid:
            Period.objects.filter(id=uid).update(name=name)
        else:
            Period.objects.create(name=name)
        return redirect("/admin/periods")

    uid = _uuid(request.POST.get("id") or "")
    error = None
    if action == "activate":
        if not uid:
            error = "Periode tidak ditemukan."
        else:
            Period.objects.update(
                is_active=ExpressionWrapper(
                    Q(id=uid), output_field=BooleanField()
                )
            )
    elif action == "delete":
        period = Period.objects.filter(id=uid).first() if uid else None
        if period is None:
            error = "Periode tidak ditemukan."
        elif period.is_active:
            error = "Tidak bisa menghapus periode aktif. Aktifkan periode lain dulu."
        elif Course.objects.filter(period_id=period.id).exists():
            error = "Periode masih punya kelas. Hapus kelasnya dulu."
        else:
            period.delete()
    return _table_response(
        request, "academics/partials/periods_table.html", _periods_ctx(), error
    )


# ---- Courses list ----


def _new_course_form(periods):
    active = next((p for p in periods if p.is_active), periods[0] if periods else None)
    return {
        "id": "",
        "code": "",
        "name": "",
        "period_id": str(active.id) if active else "",
        "section": "A",
        "semester": "4",
        "sks": "3",
    }


def _courses_ctx(form=None, errors=None, row_error=None):
    courses = _admin_courses()
    lecturers = _lecturer_names()
    counts = _student_counts()
    for c in courses:
        c.lecturer_names = lecturers.get(c.id)
        c.student_count = counts.get(c.id, 0)
    periods = _period_options()
    return {
        "courses": courses,
        "periods": periods,
        "form": form,
        "form_errors": errors or {},
        "row_error": row_error,
        "crumbs": [{"label": "Mata kuliah"}],
    }


def courses_page(request):
    if request.method == "POST":
        return _courses_post(request)
    periods = _period_options()
    form = None
    raw = request.GET.get("form", "")
    if raw == "new":
        form = _new_course_form(periods)
    elif raw:
        cid = _uuid(raw)
        course = Course.objects.filter(id=cid).first() if cid else None
        if not course:
            return redirect("/admin/courses")
        form = {
            "id": str(course.id),
            "code": course.code,
            "name": course.name,
            "period_id": str(course.period_id),
            "section": course.section,
            "semester": str(course.semester),
            "sks": str(course.sks),
        }
    ctx = _courses_ctx(form)
    return render(request, "academics/courses.html", ctx)


def _courses_post(request):
    action = request.POST.get("action", "")
    if action == "save":
        return _save_course(request)

    cid = _uuid(request.POST.get("id") or "")
    error = None
    if action == "archive":
        course = Course.objects.filter(id=cid).first() if cid else None
        if course is None:
            error = "Mata kuliah tidak ditemukan."
        else:
            course.archived_at = None if course.archived_at else timezone.now()
            course.save(update_fields=["archived_at"])
    elif action == "delete":
        course = Course.objects.filter(id=cid).first() if cid else None
        if course is None:
            error = "Mata kuliah tidak ditemukan."
        elif Enrollment.objects.filter(course_id=course.id).exists():
            error = "Masih ada mahasiswa terdaftar. Arsipkan, jangan dihapus."
        else:
            course.delete()
    return _table_response(
        request, "academics/partials/courses_table.html", _courses_ctx(), error
    )


def _save_course(request):
    post = request.POST
    code = (post.get("code") or "").strip().upper()
    name = (post.get("name") or "").strip()
    section = (post.get("section") or "").strip() or "A"
    section = section.upper()
    semester = _parse_int((post.get("semester") or "").strip())
    sks = _parse_int((post.get("sks") or "").strip())
    period_id = (post.get("period_id") or "").strip()
    pid = _uuid(period_id)
    course_id = (post.get("id") or "").strip()
    cid = _uuid(course_id)

    form = {
        "id": course_id,
        "code": code,
        "name": name,
        "period_id": period_id,
        "section": section,
        "semester": (post.get("semester") or "").strip(),
        "sks": (post.get("sks") or "").strip(),
    }
    errors = {}
    if not code:
        errors["code"] = "Kode wajib diisi."
    if not name:
        errors["name"] = "Nama mata kuliah wajib diisi."
    if semester is None or semester < 1 or semester > 14:
        errors["semester"] = "Semester harus 1–14."
    if sks is None or sks < 1 or sks > 10:
        errors["sks"] = "SKS harus 1–10."
    if not period_id:
        errors["period_id"] = "Periode wajib dipilih."
    elif not re.fullmatch(r"[A-Z0-9]{1,8}", section):
        errors["section"] = "Kelas maksimal 8 karakter (huruf atau angka)."
    if not errors:
        if not pid or not Period.objects.filter(id=pid).exists():
            errors["period_id"] = "Periode tidak ditemukan."
    if not errors:
        dup = Course.objects.filter(
            code__iexact=code, period_id=pid, section__iexact=section
        )
        if cid:
            dup = dup.exclude(id=cid)
        if dup.exists():
            errors["code"] = "Kelas untuk kode, periode, dan seksi ini sudah ada."
    if errors:
        return render(
            request, "academics/courses.html", _courses_ctx(form=form, errors=errors)
        )
    if course_id:
        Course.objects.filter(id=cid).update(
            code=code, name=name, semester=semester, sks=sks,
            period_id=pid, section=section,
        )
    else:
        Course.objects.create(
            code=code, name=name, semester=semester, sks=sks,
            period_id=pid, section=section,
        )
    return redirect("/admin/courses")


# ---- Course detail / assignment ----


def _assign_ctx(course, row_error=None):
    lecturers = list(
        User.objects.filter(role="lecturer", status="active").order_by("name")
    )
    students = list(
        User.objects.filter(role="student", status="active").order_by("name")
    )
    assigned = set(
        CourseLecturer.objects.filter(course_id=course.id).values_list(
            "user_id", flat=True
        )
    )
    enrolled = set(
        Enrollment.objects.filter(course_id=course.id).values_list(
            "student_id", flat=True
        )
    )
    for u in lecturers:
        u.assigned = u.id in assigned
    for u in students:
        u.enrolled = u.id in enrolled
    return {
        "c": course,
        "lecturers": lecturers,
        "students": students,
        "assigned": assigned,
        "enrolled": enrolled,
        "row_error": row_error,
        "crumb_root": "/admin",
        "crumbs": [
            {"label": "Mata kuliah", "href": "/admin/courses"},
            {"label": course.code},
        ],
    }


def course_detail(request, course_id):
    cid = _uuid(course_id)
    course = (
        Course.objects.select_related("period").filter(id=cid).first()
        if cid
        else None
    )
    if course is None:
        return _not_found()
    if request.method == "POST":
        return _assign_post(request, course)
    return render(request, "academics/course_detail.html", _assign_ctx(course))


def _assign_post(request, course):
    action = request.POST.get("action", "")
    user_id = _uuid(request.POST.get("user_id") or "")
    student_id = _uuid(request.POST.get("student_id") or "")
    error = None
    if action == "toggle_lecturer":
        if not user_id:
            error = "Data tidak lengkap."
        else:
            _toggle_join("course_lecturers", "course_id", "user_id", course.id, user_id)
    elif action == "toggle_enrollment":
        if not student_id:
            error = "Data tidak lengkap."
        else:
            _toggle_join("enrollments", "course_id", "student_id", course.id, student_id)
    else:
        return redirect(f"/admin/courses/{course.id}")

    if request.htmx:
        if action == "toggle_lecturer":
            template = "academics/partials/assign_lecturer_row.html"
            checked = user_id and CourseLecturer.objects.filter(
                course_id=course.id, user_id=user_id
            ).exists()
            person = User.objects.filter(id=user_id).first() if user_id else None
            ctx = {"c": course, "p": person, "on": bool(checked)}
        else:
            template = "academics/partials/assign_student_row.html"
            checked = student_id and Enrollment.objects.filter(
                course_id=course.id, student_id=student_id
            ).exists()
            person = User.objects.filter(id=student_id).first() if student_id else None
            ctx = {"c": course, "p": person, "on": bool(checked)}
        ctx["row_error"] = error
        ctx["oob"] = True
        return render(request, template, ctx)
    if error:
        messages.error(request, error)
    return redirect(f"/admin/courses/{course.id}")


# ---- Placement ----


def placement_page(request):
    if request.method == "POST":
        return _placement_post(request)
    return render(request, "academics/placement.html", _placement_ctx(request))


def _placement_ctx(request):
    students = list(
        User.objects.filter(role="student", status="active").order_by("name")
    )
    counts = {}
    for _, sid in Enrollment.objects.values_list("course_id", "student_id"):
        counts[sid] = counts.get(sid, 0) + 1
    for s in students:
        s.class_count = counts.get(s.id, 0)
    periods = _period_options()
    active = next((p for p in periods if p.is_active), periods[0] if periods else None)

    student = None
    sid = _uuid(request.GET.get("student") or "")
    if sid:
        student = next((s for s in students if s.id == sid), None)

    period = None
    pid = _uuid(request.GET.get("period") or "")
    if pid:
        period = next((p for p in periods if p.id == pid), None)
    if period is None:
        period = active

    enrolled = (
        set(
            Enrollment.objects.filter(student_id=student.id).values_list(
                "course_id", flat=True
            )
        )
        if student
        else set()
    )

    classes = (
        [c for c in _placement_courses() if c.period_id == period.id]
        if period
        else []
    )
    lecturers = _lecturer_names()
    for c in classes:
        c.lecturer_names = lecturers.get(c.id)
        c.on = c.id in enrolled
    return {
        "students": students,
        "student_counts": counts,
        "periods": periods,
        "period": period,
        "student": student,
        "classes": classes,
        "enrolled": enrolled,
        "row_error": None,
        "crumbs": [{"label": "Penempatan"}],
    }


def _placement_post(request):
    action = request.POST.get("action", "")
    if action != "toggle":
        return redirect("/admin/placement")
    cid = _uuid(request.POST.get("course_id") or "")
    sid = _uuid(request.POST.get("student_id") or "")
    error = None
    if not cid or not sid:
        error = "Data tidak lengkap."
    else:
        _toggle_join("enrollments", "course_id", "student_id", cid, sid)

    if request.htmx:
        on = (
            Enrollment.objects.filter(course_id=cid, student_id=sid).exists()
            if cid and sid
            else False
        )
        course = Course.objects.filter(id=cid).first() if cid else None
        student = User.objects.filter(id=sid).first() if sid else None
        if course is None or student is None:
            from django.http import HttpResponse

            escaped = (
                (error or "Data tidak lengkap.")
                .replace("&", "&amp;")
                .replace("<", "&lt;")
            )
            return HttpResponse(
                f'<div id="row-error" hx-swap-oob="true">'
                f'<p class="error-line">{escaped}</p></div>'
            )
        return render(
            request,
            "academics/partials/placement_cell.html",
            {
                "c": course,
                "student": student,
                "on": on,
                "row_error": error,
                "show_count": True,
                "class_count": Enrollment.objects.filter(student_id=sid).count(),
            },
        )
    if error:
        messages.error(request, error)
    return redirect("/admin/placement")
