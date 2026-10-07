"""Lecturer course pages (port of src/app/lecturer/courses/*)."""

from uuid import UUID

from django.shortcuts import redirect, render

from .lib import course_cards, with_card_meta, course_context, course_frame, get_lecturer, get_lecturer_course, upcoming
from .models import CourseLecturer, Enrollment, Topic
from .views_admin import _parse_int

ROLE_HOME = "/lecturer/home"


def _guard_course(request, course_id):
    """Returns (lecturer, course, response) — response set means redirect/404."""
    lecturer = get_lecturer(request)
    if lecturer is None:
        return None, None, redirect(ROLE_HOME)
    try:
        cid = UUID(str(course_id))
    except (ValueError, TypeError, AttributeError):
        return lecturer, None, redirect("/lecturer/courses")
    course = get_lecturer_course(cid, lecturer)
    if course is None:
        return lecturer, None, redirect("/lecturer/courses")
    return lecturer, course, None


def _course_base(request, course, frame=None):
    ctx = {
        "course": course_context(course),
        "crumb_root": ROLE_HOME,
        "crumbs": [
            {"label": "Kursus", "href": "/lecturer/courses"},
            {"label": course.code},
        ],
    }
    if frame is None:
        frame = course_frame(course, "lecturer")
    ctx["frame"] = frame
    return ctx


def courses_page(request):
    lecturer = get_lecturer(request)
    if lecturer is None:
        return redirect(ROLE_HOME)
    cards = with_card_meta(course_cards(lecturer))
    return render(
        request,
        "lecturer/courses.html",
        {"cards": cards, "crumbs": [{"label": "Kursus saya"}]},
    )


def course_page(request, course_id):
    lecturer, course, err = _guard_course(request, course_id)
    if err is not None:
        return err
    if request.method == "POST":
        return _create_topic(request, course)

    form_open = request.GET.get("form") == "new"
    return render(
        request,
        "lecturer/course.html",
        {
            **_course_base(request, course),
            "upcoming": upcoming(course.id),
            "form_open": form_open,
            "form_errors": {},
            "form_values": {},
        },
    )


def _create_topic(request, course):
    title = (request.POST.get("title") or "").strip()
    week_raw = (request.POST.get("week") or "").strip()
    values = {"title": title, "week": week_raw}
    errors = {}
    if not title:
        errors["title"] = "Judul wajib diisi."
    week = _parse_int(week_raw)
    if week is None or week < 1 or week > 30:
        errors["week"] = "Minggu harus 1–30."
    if not errors and Topic.objects.filter(course=course, week=week).exists():
        errors["week"] = "Minggu sudah dipakai."
    if errors:
        return render(
            request,
            "lecturer/course.html",
            {
                **_course_base(request, course),
                "upcoming": upcoming(course.id),
                "form_open": True,
                "form_errors": errors,
                "form_values": values,
            },
        )
    topic = Topic.objects.create(course=course, week=week, title=title)
    return redirect(f"/lecturer/courses/{course.id}/topics/{topic.id}")


def peserta_page(request, course_id):
    lecturer, course, err = _guard_course(request, course_id)
    if err is not None:
        return err
    lecturers = list(
        CourseLecturer.objects.filter(course=course)
        .select_related("user")
        .order_by("user__name")
    )
    students = list(
        Enrollment.objects.filter(course=course)
        .select_related("student")
        .order_by("student__name")
    )
    ctx = _course_base(request, course)
    ctx["crumbs"] = ctx["crumbs"] + [{"label": "Peserta"}]
    ctx["lecturer_rows"] = [
        {"name": cl.user.name, "email": cl.user.email} for cl in lecturers
    ]
    ctx["student_rows"] = [
        {"name": e.student.name, "email": e.student.email} for e in students
    ]
    return render(request, "lecturer/peserta.html", ctx)


def tugas_page(request, course_id):
    lecturer, course, err = _guard_course(request, course_id)
    if err is not None:
        return err
    from assessment.models import Assignment, RubricCriterion, Submission

    assignments = list(
        Assignment.objects.filter(topic__course=course).order_by(
            "topic__week", "created_at"
        )
    )
    submitted_counts = _count_submitted([a.id for a in assignments])
    rubric_stats = _rubric_stats([a.id for a in assignments])
    rows = []
    for a in assignments:
        count, wsum = rubric_stats.get(a.id, (0, 0))
        if a.type == "pg":
            rubric_key = "pg"
        elif count == 0:
            rubric_key = "empty"
        elif wsum == 100:
            rubric_key = "ok"
        else:
            rubric_key = "bad"
        rows.append(
            {
                "id": a.id,
                "title": a.title,
                "week": a.topic.week,
                "type": a.type,
                "release_mode": a.release_mode,
                "due_at": a.due_at,
                "submitted": submitted_counts.get(a.id, 0),
                "rubric_count": count,
                "rubric_weight": wsum,
                "rubric_key": rubric_key,
            }
        )
    ctx = _course_base(request, course)
    ctx["crumbs"] = ctx["crumbs"] + [{"label": "Tugas"}]
    ctx["rows"] = rows
    return render(request, "lecturer/tugas.html", ctx)


def _count_submitted(assignment_ids):
    from django.db.models import Count

    from assessment.models import Submission

    return dict(
        Submission.objects.exclude(status="draft")
        .filter(assignment_id__in=assignment_ids)
        .values_list("assignment_id")
        .annotate(n=Count("id"))
    )


def _rubric_stats(assignment_ids):
    from django.db.models import Count, Sum

    from assessment.models import RubricCriterion

    rows = (
        RubricCriterion.objects.filter(assignment_id__in=assignment_ids)
        .values("assignment_id")
        .annotate(n=Count("id"), w=Sum("weight"))
    )
    return {r["assignment_id"]: (r["n"], r["w"] or 0) for r in rows}


def nilai_page(request, course_id):
    lecturer, course, err = _guard_course(request, course_id)
    if err is not None:
        return err
    from assessment.models import Assignment, Grade, Submission

    students = list(
        Enrollment.objects.filter(course=course)
        .select_related("student")
        .order_by("student__name")
    )
    assignments = list(
        Assignment.objects.filter(topic__course=course).order_by(
            "topic__week", "created_at"
        )
    )
    grade_rows = Grade.objects.filter(
        submission__assignment__in=assignments
    ).values_list(
        "submission__student_id", "submission__assignment_id", "nilai", "state"
    )
    cells = {}
    for sid, aid, nilai, state in grade_rows:
        key = (sid, aid)
        if key in cells and cells[key][1] == "published":
            continue
        if key in cells and state != "published":
            continue
        cells[key] = (nilai, state)

    sheet = []
    for s in students:
        row_cells = []
        for a in assignments:
            cell = cells.get((s.student_id, a.id))
            if cell is None:
                row_cells.append({"kind": "none"})
            elif cell[1] == "published":
                row_cells.append({"kind": "published", "nilai": cell[0]})
            else:
                row_cells.append({"kind": "draft", "nilai": cell[0]})
        sheet.append({"name": s.student.name, "cells": row_cells})

    averages = []
    for a in assignments:
        vals = []
        for s in students:
            cell = cells.get((s.student_id, a.id))
            if cell and cell[1] == "published":
                try:
                    vals.append(float(cell[0]))
                except (TypeError, ValueError):
                    pass
        averages.append((sum(vals) / len(vals)) if vals else None)

    ctx = _course_base(request, course)
    ctx["crumbs"] = ctx["crumbs"] + [{"label": "Nilai"}]
    ctx["columns"] = [{"id": a.id, "title": a.title} for a in assignments]
    ctx["sheet"] = sheet
    ctx["averages"] = averages
    ctx["empty_reason"] = (
        "no_assignments"
        if not assignments
        else ("no_students" if not students else None)
    )
    return render(request, "lecturer/nilai.html", ctx)


def pengaturan_page(request, course_id):
    lecturer, course, err = _guard_course(request, course_id)
    if err is not None:
        return err
    ctx = _course_base(request, course)
    ctx["crumbs"] = ctx["crumbs"] + [{"label": "Pengaturan"}]
    return render(request, "lecturer/pengaturan.html", ctx)


# ---- Topic detail (port of topics/[topicId]) ----

import json
import re as _re

from assessment.models import Assignment, AssignmentQuestion
from .models import MateriBlock


def _topic_guard(request, course_id, topic_id):
    lecturer, course, err = _guard_course(request, course_id)
    if err is not None:
        return None, None, err
    topic = Topic.objects.filter(id=topic_id, course=course).first()
    if topic is None:
        return course, None, redirect("/lecturer/courses")
    return course, topic, None


def _topic_ctx(request, course, topic, **extra):
    frame = course_frame(course, "lecturer")
    blocks = list(MateriBlock.objects.filter(topic=topic).order_by("position"))
    block_rows = [
        {
            "type": b.type,
            "body": b.body,
            "url": b.url,
            "file_name": b.file_name,
        }
        for b in blocks
    ]
    assignments = list(
        Assignment.objects.filter(topic=topic).order_by("created_at")
    )
    from assessment.models import Submission

    counts = _all_submission_counts([a.id for a in assignments])
    ctx = {
        "course": course_context(course),
        "frame": frame,
        "active_topic_id": str(topic.id),
        "crumb_root": ROLE_HOME,
        "crumbs": [
            {"label": "Kursus", "href": "/lecturer/courses"},
            {"label": course.code, "href": f"/lecturer/courses/{course.id}"},
            {"label": f"Pertemuan {topic.week}"},
        ],
        "topic": {"id": topic.id, "week": topic.week, "title": topic.title},
        "block_rows": block_rows,
        "blocks_json": json.dumps(block_rows, ensure_ascii=False),
        "blocks_value": json.dumps(block_rows, ensure_ascii=False),
        "t_values": {"title": topic.title, "week": str(topic.week)},
        "t_errors": {},
        "t_error": None,
        "info": None,
        "assignments": [
            {
                "id": a.id,
                "title": a.title,
                "type": a.type,
                "release_mode": a.release_mode,
                "submission_count": counts.get(a.id, 0),
            }
            for a in assignments
        ],
        "a_open": request.GET.get("form") == "new",
        "a_values": {"title": "", "type": "essay", "question": ""},
        "a_questions_json": "[]",
        "a_errors": {},
        "a_error": None,
    }
    ctx.update(extra)
    ctx["a_questions"] = _display_questions(ctx.get("a_questions_json") or "[]")
    ctx["default_opts"] = [{"key": k, "text": ""} for k in "ABCD"]
    return ctx


def _display_questions(raw):
    try:
        qs = json.loads(raw)
    except ValueError:
        qs = []
    if not isinstance(qs, list):
        qs = []
    out = []
    for q in qs:
        if not isinstance(q, dict):
            continue
        opts = []
        for o in (q.get("options") or []):
            if isinstance(o, dict) and o.get("key"):
                opts.append({"key": str(o["key"]), "text": str(o.get("text") or "")})
        out.append(
            {
                "question": str(q.get("question") or ""),
                "opts": opts,
                "answer_key": str(q.get("answer_key") or ""),
            }
        )
    return out


def _display_blocks(blocks):
    rows = []
    for b in blocks:
        if not isinstance(b, dict):
            continue
        btype = b.get("type")
        if btype not in ("richtext", "link", "file"):
            btype = "richtext"
        rows.append(
            {
                "type": btype,
                "body": str(b.get("body") or ""),
                "url": str(b.get("url") or ""),
                "file_name": str(b.get("file_name") or ""),
            }
        )
    return rows


def _all_submission_counts(assignment_ids):
    from django.db.models import Count

    from assessment.models import Submission

    return dict(
        Submission.objects.filter(assignment_id__in=assignment_ids)
        .values_list("assignment_id")
        .annotate(n=Count("id"))
    )


def topic_detail(request, course_id, topic_id):
    course, topic, err = _topic_guard(request, course_id, topic_id)
    if err is not None:
        return err
    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()
        if action == "save_topic":
            return _save_topic(request, course, topic)
        if action == "create_assignment":
            return _create_assignment(request, course, topic)
    return render(
        request, "lecturer/topic_detail.html", _topic_ctx(request, course, topic)
    )


def _save_topic(request, course, topic):
    title = (request.POST.get("title") or "").strip()
    week_raw = (request.POST.get("week") or "").strip()
    t_values = {"title": title, "week": week_raw}
    errors = {}
    if not title:
        errors["title"] = "Judul wajib diisi."
    week = _parse_int(week_raw)
    if week is None or week < 1 or week > 30:
        errors["week"] = "Minggu harus 1–30."
    if not errors and week != topic.week:
        if Topic.objects.filter(course=course, week=week).exclude(id=topic.id).exists():
            errors["week"] = "Minggu sudah dipakai."
    if errors:
        return render(
            request,
            "lecturer/topic_detail.html",
            _topic_ctx(request, course, topic, t_values=t_values, t_errors=errors),
        )

    raw_blocks = (request.POST.get("blocks") or "").strip()
    try:
        parsed = json.loads(raw_blocks or "[]")
        if not isinstance(parsed, list):
            parsed = None
    except ValueError:
        parsed = None
    if parsed is None:
        return render(
            request,
            "lecturer/topic_detail.html",
            _topic_ctx(
                request,
                course,
                topic,
                t_values=t_values,
                t_error="Data materi tidak valid.",
                blocks_value=raw_blocks or "[]",
            ),
        )

    blocks = parsed
    n = len(blocks)
    for i in range(n):
        b = blocks[i] if isinstance(blocks[i], dict) else {}
        btype = b.get("type")
        label = i + 1
        if btype not in ("richtext", "link", "file"):
            t_error = f"Materi ke-{label}: tipe tidak dikenal."
            break
        if btype == "richtext" and not (b.get("body") or "").strip():
            t_error = f"Materi ke-{label}: teks wajib diisi."
            break
        if btype == "link":
            url = (b.get("url") or "").strip()
            if not url:
                t_error = f"Materi ke-{label}: URL wajib diisi."
                break
            if not _re.match(r"^https?://", url, _re.IGNORECASE):
                t_error = f"Materi ke-{label}: URL harus diawali http(s)."
                break
        if btype == "file" and not (b.get("file_name") or "").strip():
            t_error = f"Materi ke-{label}: nama berkas wajib diisi."
            break
    else:
        t_error = None

    if t_error:
        return render(
            request,
            "lecturer/topic_detail.html",
            _topic_ctx(
                request,
                course,
                topic,
                t_values=t_values,
                t_error=t_error,
                block_rows=_display_blocks(blocks),
                blocks_value=raw_blocks or "[]",
            ),
        )

    topic.title = title
    topic.week = week
    topic.save()
    MateriBlock.objects.filter(topic=topic).delete()
    for i, b in enumerate(blocks):
        btype = b.get("type")
        MateriBlock.objects.create(
            topic=topic,
            type=btype,
            body=(b.get("body") or "") if btype in ("richtext", "link") else None,
            url=(b.get("url") or "") if btype == "link" else None,
            file_name=(b.get("file_name") or "") if btype == "file" else None,
            position=i,
        )
    return render(
        request,
        "lecturer/topic_detail.html",
        _topic_ctx(request, course, topic, info="Pertemuan disimpan."),
    )


def _create_assignment(request, course, topic):
    title = (request.POST.get("title") or "").strip()
    atype = (request.POST.get("type") or "").strip()
    due_raw = (request.POST.get("due_at") or "").strip()
    raw_q = (request.POST.get("questions") or "").strip()
    values = {"title": title, "type": atype, "question": (request.POST.get("question") or "")}
    errors = {}
    if not title:
        errors["title"] = "Judul wajib diisi."
    if atype not in ("essay", "pg", "pdf", "docx"):
        errors["type"] = "Tipe tidak dikenal."
    due_at = None
    if due_raw:
        from django.utils import dateparse, timezone

        parsed_due = dateparse.parse_datetime(due_raw)
        if parsed_due is None:
            errors["due_at"] = "Tenggat tidak valid."
        else:
            if timezone.is_naive(parsed_due):
                parsed_due = timezone.make_aware(parsed_due)
            due_at = parsed_due

    questions = []
    if atype == "pg":
        raw_q = (request.POST.get("questions") or "").strip()
        try:
            parsed = json.loads(raw_q or "[]")
        except ValueError:
            parsed = None
        if not isinstance(parsed, list) or not parsed:
            errors["question"] = "Tulis minimal satu soal."
        else:
            ok = True
            for i, item in enumerate(parsed):
                label = i + 1
                if not isinstance(item, dict) or not (
                    str(item.get("question") or "").strip()
                ):
                    errors["question"] = f"Soal ke-{label}: teks soal wajib diisi."
                    ok = False
                    break
                raw_opts = item.get("options")
                opts = [
                    o
                    for o in (raw_opts if isinstance(raw_opts, list) else [])
                    if isinstance(o, dict)
                    and isinstance(o.get("key"), str)
                    and str(o.get("text") or "").strip()
                ]
                if len(opts) < 2:
                    errors["options"] = f"Soal ke-{label}: isi minimal dua opsi."
                    ok = False
                    break
                if not any(o["key"] == item.get("answer_key") for o in opts):
                    errors[
                        "options"
                    ] = f"Soal ke-{label}: pilih kunci jawaban dari opsi yang terisi."
                    ok = False
                    break
                questions.append(
                    {
                        "question": str(item.get("question")).strip(),
                        "options": opts,
                        "answer_key": item.get("answer_key"),
                    }
                )
            if not ok:
                questions = []
    else:
        question = (request.POST.get("question") or "").strip()
        if not question:
            errors["question"] = "Pertanyaan wajib diisi."
        else:
            questions = [{"question": question, "options": [], "answer_key": ""}]

    if errors:
        return render(
            request,
            "lecturer/topic_detail.html",
            _topic_ctx(
                request,
                course,
                topic,
                a_open=True,
                a_values=values,
                a_errors=errors,
                a_questions_json=raw_q or "[]",
            ),
        )

    try:
        assignment = Assignment.objects.create(
            topic=topic, title=title, type=atype, due_at=due_at
        )
    except Exception:
        return render(
            request,
            "lecturer/topic_detail.html",
            _topic_ctx(
                request,
                course,
                topic,
                a_open=True,
                a_values=values,
                a_error="Gagal membuat tugas.",
                a_questions_json=raw_q or "[]",
            ),
        )
    for i, item in enumerate(questions):
        AssignmentQuestion.objects.create(
            assignment=assignment,
            position=i,
            question=item["question"],
            options=item["options"] if atype == "pg" else None,
            answer_key=item["answer_key"] if atype == "pg" else None,
        )
    return redirect(f"/lecturer/assignments/{assignment.id}")
