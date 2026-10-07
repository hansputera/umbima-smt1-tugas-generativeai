"""Lecturer assignment detail + submission pages (ports of
src/app/lecturer/assignments/[id] and src/app/lecturer/submissions)."""

import json
from urllib.parse import urlencode

from django.core.exceptions import ValidationError
from django.db.models import F, Sum
from django.shortcuts import redirect, render

from academics.lib import course_context, get_lecturer
from nilai.templatetags.nilai_tags import fmt_date, fmt_nilai

from .grading import apply_grade_edits, compute_grade, get_grade, persist_grade
from .lib import (
    UUID_RE,
    compute_nilai,
    get_settings,
    is_embedding_configured,
    is_model_configured,
    js_number,
    number_value as _jsnum,
    predikat_of,
    require_lecturer_assignment,
    submission_status,
)
from .models import GradeRevision, RubricCriterion, Submission

ROLE_HOME = "/lecturer/home"


def _text(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def assignment_detail(request, assignment_id):
    lecturer = get_lecturer(request)
    if lecturer is None:
        return redirect(ROLE_HOME)
    assignment = require_lecturer_assignment(request, assignment_id)
    if assignment is None:
        return redirect("/lecturer/courses")
    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()
        if action == "save_rubric":
            return _save_rubric(request, assignment)
        if action == "save_mode":
            return _save_mode(request, assignment)
    extra = {}
    info = request.GET.get("info")
    if info:
        if request.GET.get("f") == "rubric":
            extra["rubric_info"] = info
        else:
            extra["mode_info"] = info
    return render(
        request, "lecturer/assignment_detail.html", _assignment_ctx(request, assignment, **extra)
    )


def _prg(assignment, info, form):
    return redirect(
        "/lecturer/assignments/%s?%s"
        % (assignment.id, urlencode({"info": info, "f": form}))
    )


def _db_rubric_rows(assignment):
    return [
        {
            "id": str(c.id),
            "name": c.name,
            "weight": c.weight,
            "level_1": c.level_1,
            "level_2": c.level_2,
            "level_3": c.level_3,
            "level_4": c.level_4,
            "prompt_notes": c.prompt_notes,
        }
        for c in assignment.criteria.order_by("position", "name")
    ]


def _redisplay_rows(rows):
    out = []
    for r in rows:
        if not isinstance(r, dict):
            r = {}
        rid = r.get("id")
        out.append(
            {
                "id": rid if isinstance(rid, str) else "",
                "name": _text(r.get("name")),
                "weight": r.get("weight") if r.get("weight") is not None else 0,
                "level_1": _text(r.get("level_1")),
                "level_2": _text(r.get("level_2")),
                "level_3": _text(r.get("level_3")),
                "level_4": _text(r.get("level_4")),
                "prompt_notes": _text(r.get("prompt_notes")),
            }
        )
    return out


def _rows_total(rows):
    """Client live total: sum of Number(weight) || 0 across display rows."""
    total = 0.0
    for r in rows:
        if not isinstance(r, dict):
            continue
        w = _jsnum(r.get("weight"))
        if w == w:  # NaN contributes 0, matching `Number(x) || 0`
            total += w
    return total


def _assignment_ctx(request, assignment, **extra):
    topic = assignment.topic
    course = topic.course
    questions = list(assignment.questions.order_by("position"))
    settings = get_settings()
    inbox = (
        Submission.objects.filter(assignment=assignment)
        .select_related("student", "grade")
        .order_by("student__name")
    )
    inbox_rows = []
    for s in inbox:
        grade = getattr(s, "grade", None)
        published = bool(grade is not None and grade.state == "published")
        inbox_rows.append(
            {
                "id": s.id,
                "student_name": s.student.name,
                "status_key": submission_status(s.status, published),
                "submitted_at": s.submitted_at,
                "nilai": grade.nilai if grade is not None else None,
            }
        )

    rubric_rows = _db_rubric_rows(assignment)
    rubric_sum = sum(r["weight"] for r in rubric_rows)
    mode = assignment.release_mode

    ctx = {
        "assignment": {
            "id": assignment.id,
            "title": assignment.title,
            "type": assignment.type,
            "release_mode": assignment.release_mode,
        },
        "topic": {"id": topic.id, "week": topic.week, "title": topic.title},
        "course": course_context(course),
        "crumb_root": ROLE_HOME,
        "crumbs": [
            {"label": "Kursus", "href": "/lecturer/courses"},
            {"label": course.code, "href": f"/lecturer/courses/{course.id}"},
            {
                "label": f"Pertemuan {topic.week}",
                "href": f"/lecturer/courses/{course.id}/topics/{topic.id}",
            },
            {"label": assignment.title},
        ],
        "questions": [
            {
                "question": q.question,
                "opts": q.options if isinstance(q.options, list) else [],
                "answer_key": q.answer_key,
            }
            for q in questions
        ],
        "n_questions": len(questions),
        "rubric_rows": rubric_rows,
        "rubric_sum": rubric_sum,
        "criteria_value": json.dumps(
            [
                {
                    "id": r["id"] or None,
                    "name": r["name"],
                    "weight": r["weight"],
                    "level_1": r["level_1"],
                    "level_2": r["level_2"],
                    "level_3": r["level_3"],
                    "level_4": r["level_4"],
                    "prompt_notes": r["prompt_notes"],
                }
                for r in rubric_rows
            ],
            ensure_ascii=False,
        ),
        "rubric_error": None,
        "rubric_info": None,
        "inbox": inbox_rows,
        "mode": mode if mode in ("review", "langsung") else "review",
        "mode_error": None,
        "mode_info": None,
        "confirm": False,
        "model_ok": is_model_configured(settings),
        "embed_ok": is_embedding_configured(settings),
        "needs_embedding": assignment.type in ("pdf", "docx"),
    }
    ctx.update(extra)
    ctx["rubric_sum_text"] = js_number(ctx["rubric_sum"])

    blockers = []
    if ctx["rubric_sum"] != 100:
        blockers.append("Rubrik harus berjumlah 100.")
    if not ctx["model_ok"]:
        blockers.append("Model belum disetel.")
    if ctx["needs_embedding"] and not ctx["embed_ok"]:
        blockers.append("Embedding belum disetel.")
    ctx["blockers"] = blockers
    ctx["mode_disabled"] = ctx["mode"] == "langsung" and (
        bool(blockers) or not ctx["confirm"]
    )
    return ctx


def _save_rubric(request, assignment):
    raw = (request.POST.get("criteria") or "").strip()
    try:
        parsed = json.loads(raw or "[]")
    except ValueError:
        return render(
            request,
            "lecturer/assignment_detail.html",
            _assignment_ctx(
                request, assignment, rubric_error="Data rubrik tidak valid."
            ),
        )

    rows = parsed if isinstance(parsed, list) else []
    extra = {"rubric_rows": _redisplay_rows(rows)}
    total_display = _rows_total(rows)
    extra["rubric_sum"] = total_display
    extra["criteria_value"] = json.dumps(
        [
            {
                "id": r["id"] or None,
                "name": r["name"],
                "weight": r["weight"],
                "level_1": r["level_1"],
                "level_2": r["level_2"],
                "level_3": r["level_3"],
                "level_4": r["level_4"],
                "prompt_notes": r["prompt_notes"],
            }
            for r in extra["rubric_rows"]
        ],
        ensure_ascii=False,
    )

    def fail(msg):
        extra["rubric_error"] = msg
        return render(
            request, "lecturer/assignment_detail.html", _assignment_ctx(request, assignment, **extra)
        )

    if len(rows) == 0:
        return fail("Tambahkan minimal satu kriteria.")

    total = 0
    for r in rows:
        if not isinstance(r, dict):
            r = {}
        name = r.get("name")
        if not name or not str(name).strip():
            return fail("Nama kriteria wajib diisi.")
        weight = _jsnum(r.get("weight"))
        if not weight.is_integer() or weight < 1 or weight > 100:
            return fail(f'Bobot "{name}" tidak valid.')
        total += int(weight)
    if total != 100:
        return fail("Bobot harus berjumlah 100.")

    existing_ids = {str(i) for i in assignment.criteria.values_list("id", flat=True)}
    keep_ids = set()
    for r in rows:
        rid = r.get("id")
        if rid and UUID_RE.match(str(rid)):
            keep_ids.add(str(rid))
    for rid in existing_ids - keep_ids:
        RubricCriterion.objects.filter(id=rid).delete()

    for i, r in enumerate(rows):
        if not isinstance(r, dict):
            r = {}
        values = {
            "position": i,
            "name": str(r.get("name")).strip(),
            "weight": int(_jsnum(r.get("weight"))),
            "level_1": _text(r.get("level_1")),
            "level_2": _text(r.get("level_2")),
            "level_3": _text(r.get("level_3")),
            "level_4": _text(r.get("level_4")),
            "prompt_notes": _text(r.get("prompt_notes")),
        }
        rid = r.get("id")
        if rid and UUID_RE.match(str(rid)):
            RubricCriterion.objects.filter(id=rid, assignment=assignment).update(
                **values
            )
        else:
            RubricCriterion.objects.create(assignment=assignment, **values)

    return _prg(assignment, "Rubrik disimpan.", "rubric")


def _save_mode(request, assignment):
    mode = (request.POST.get("mode") or "").strip()
    if mode not in ("review", "langsung"):
        return render(
            request,
            "lecturer/assignment_detail.html",
            _assignment_ctx(request, assignment, mode_error="Mode tidak dikenal."),
        )

    confirm = "confirm" in request.POST
    extra = {"mode": mode, "confirm": confirm}

    if mode == "langsung":
        if not confirm:
            extra["mode_error"] = 'Centang "Saya mengerti nilai terbit tanpa review."'
        else:
            total = (
                assignment.criteria.aggregate(t=Sum("weight"))["t"] or 0
            )
            if total != 100:
                extra["mode_error"] = "Rubrik harus berjumlah 100."
            else:
                settings = get_settings()
                if not is_model_configured(settings):
                    extra["mode_error"] = "Model belum disetel."
                elif assignment.type in ("pdf", "docx") and not is_embedding_configured(
                    settings
                ):
                    extra["mode_error"] = "Embedding belum disetel."

    if extra.get("mode_error"):
        return render(
            request, "lecturer/assignment_detail.html", _assignment_ctx(request, assignment, **extra)
        )

    assignment.release_mode = mode
    assignment.save(update_fields=["release_mode"])
    info = (
        "Mode langsun rilis aktif."
        if mode == "langsung"
        else "Mode review dulu aktif."
    )
    return _prg(assignment, info, "mode")


def submissions_inbox(request):
    """Port of src/app/lecturer/submissions/page.tsx + submissions-inbox.tsx."""
    lecturer = get_lecturer(request)
    if lecturer is None:
        return redirect(ROLE_HOME)
    subs = (
        Submission.objects.filter(
            assignment__topic__course__lecturers__user=lecturer
        )
        .select_related("student", "assignment__topic__course", "grade")
        .order_by(F("submitted_at").desc(nulls_last=True), "student__name")
    )
    rows = []
    for s in subs:
        course = s.assignment.topic.course
        grade = getattr(s, "grade", None)
        published = bool(grade is not None and grade.state == "published")
        rows.append(
            {
                "id": s.id,
                "status_key": submission_status(s.status, published),
                "submitted_at": s.submitted_at,
                "student_name": s.student.name,
                "course_id": str(course.id),
                "course_code": course.code,
                "course_name": course.name,
                "assignment_id": s.assignment_id,
                "assignment_title": s.assignment.title,
                "type": s.assignment.type,
                "published": published,
                "nilai": grade.nilai if grade is not None else None,
            }
        )
    courses = sorted(
        {(r["course_id"], f'{r["course_code"]} — {r["course_name"]}') for r in rows},
        key=lambda x: x[1],
    )
    return render(
        request,
        "lecturer/submissions.html",
        {
            "rows": rows,
            "courses": courses,
            "count": len(rows),
            "crumbs": [{"label": "Pengumpulan"}],
        },
    )


# ---------------------------------------------------------------------------
# Submission detail + grade editor (port of src/app/lecturer/submissions/[id])
# ---------------------------------------------------------------------------


def submission_detail(request, submission_id):
    lecturer = get_lecturer(request)
    if lecturer is None:
        return redirect(ROLE_HOME)
    sub = _require_lecturer_submission(lecturer, submission_id)
    if sub is None:
        return render(request, "lecturer/submission_notfound.html", {})
    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()
        if action == "save_grade":
            return _save_grade(request, lecturer, sub)
        if action == "run_grade":
            return _run_grade(request, lecturer, sub)
    extra = {}
    info = request.GET.get("info")
    if info:
        extra["g_info"] = info
    return render(
        request, "lecturer/submission_detail.html", _submission_ctx(sub, **extra)
    )


def _require_lecturer_submission(lecturer, submission_id):
    try:
        return (
            Submission.objects.filter(
                id=submission_id,
                assignment__topic__course__lecturers__user=lecturer,
            )
            .select_related("student", "assignment__topic__course__period")
            .first()
        )
    except (ValueError, ValidationError):
        return None


def _str_post(request, key):
    value = request.POST.get(key)
    return value.strip() if isinstance(value, str) else ""


def _build_grade_rows(rubric_rows, criteria):
    """Port of GradeEditor buildRows: rubric rows joined with stored criteria."""
    rows = []
    for c in rubric_rows:
        prev = next(
            (
                x
                for x in criteria
                if isinstance(x, dict) and x.get("criterion_id") == c["id"]
            ),
            None,
        )
        score = 1
        if prev is not None:
            s = _jsnum(prev.get("score"))
            if s.is_integer() and 1 <= s <= 4:
                score = int(s)
        rows.append(
            {
                "id": c["id"],
                "name": c["name"],
                "weight": c["weight"],
                "score": score,
                "quote": _text(prev.get("quote")) if prev else "",
                "comment": _text(prev.get("comment")) if prev else "",
            }
        )
    return rows


def _rows_json(rows):
    return json.dumps(
        [
            {
                "id": r["id"],
                "score": r["score"],
                "quote": r["quote"],
                "comment": r["comment"],
            }
            for r in rows
        ],
        ensure_ascii=False,
    )


def _submission_ctx(sub, **extra):
    assignment = sub.assignment
    course = assignment.topic.course
    student = sub.student
    questions = list(assignment.questions.order_by("position"))
    is_pg = assignment.type == "pg"
    rubric_rows = [] if is_pg else _db_rubric_rows(assignment)
    grade = get_grade(sub.id)
    revisions = (
        GradeRevision.objects.filter(grade__submission=sub)
        .select_related("changed_by")
        .order_by("-changed_at")
    )

    criteria = grade.criteria if grade is not None else []
    rows = _build_grade_rows(rubric_rows, criteria)

    answers = sub.answers if isinstance(sub.answers, list) else []
    answer_lines = []
    if is_pg:
        for i, q in enumerate(questions):
            a = answers[i] if i < len(answers) else None
            line = {"n": i + 1, "empty": not a, "key": _text(a), "suffix": ""}
            if a and isinstance(q.options, list):
                chosen = next(
                    (
                        o
                        for o in q.options
                        if isinstance(o, dict) and o.get("key") == a
                    ),
                    None,
                )
                if chosen is not None:
                    line["suffix"] = " — " + _text(chosen.get("text"))
            answer_lines.append(line)

    live = compute_nilai(
        [{"score": r["score"], "weight": r["weight"]} for r in rows]
    )
    weight_sum = sum(r["weight"] for r in rows)
    state_key = (
        "published" if grade is not None and grade.state == "published" else "draft"
    )

    ctx = {
        "crumb_root": ROLE_HOME,
        "crumbs": [
            {"label": "Pengumpulan", "href": "/lecturer/submissions"},
            {
                "label": assignment.title,
                "href": f"/lecturer/assignments/{assignment.id}",
            },
            {"label": student.name},
        ],
        "student_name": student.name,
        "assignment": {
            "id": assignment.id,
            "title": assignment.title,
            "type": assignment.type,
            "release_mode": assignment.release_mode,
        },
        "course": {"id": course.id, "code": course.code, "name": course.name},
        "submitted_at": sub.submitted_at,
        "submission_id": str(sub.id),
        "is_pg": is_pg,
        "n_questions": len(questions),
        "questions": [{"question": q.question} for q in questions],
        "answer_lines": answer_lines,
        "answer_text": sub.answer_text or "",
        "answer_nonempty": bool(sub.answer_text and sub.answer_text.strip()),
        "extracted_text": sub.extracted_text or "",
        "extracted_nonempty": bool(
            sub.extracted_text and sub.extracted_text.strip()
        ),
        "extraction_ok": sub.extraction_ok,
        "file_name": sub.file_name,
        "revisions": [
            {
                "state_key": "published" if r.state == "published" else "draft",
                "nilai": fmt_nilai(r.nilai),
                "predikat": r.predikat,
                "changed_by": r.changed_by.name if r.changed_by else "Sistem",
                "changed_at": fmt_date(r.changed_at),
            }
            for r in revisions
        ],
        "has_grade": grade is not None,
        "state_key": state_key,
        "shown_nilai": js_number(float(grade.nilai)) if grade is not None else "",
        "shown_predikat": grade.predikat if grade is not None else "",
        "pg_feedback": (
            grade.feedback
            if grade is not None and grade.feedback
            else "Belum dinilai."
        ),
        "e_rows": rows,
        "e_criteria_json": _rows_json(rows),
        "e_feedback": grade.feedback if grade is not None else "",
        "e_summary": grade.summary if grade is not None else "",
        "live_nilai": js_number(live),
        "live_predikat": predikat_of(live),
        "weight_sum": weight_sum,
        "weight_sum_text": js_number(weight_sum),
        "is_langsung": assignment.release_mode == "langsung",
        "g_error": None,
        "g_info": None,
        "g_raw": None,
    }
    ctx.update(extra)
    return ctx


def _prg_submission(sub, info):
    return redirect(
        "/lecturer/submissions/%s?%s" % (sub.id, urlencode({"info": info}))
    )


def _save_grade(request, lecturer, sub):
    raw = _str_post(request, "criteria")
    try:
        parsed = json.loads(raw or "[]")
    except ValueError:
        return render(
            request,
            "lecturer/submission_detail.html",
            _submission_ctx(sub, g_error="Data nilai tidak valid."),
        )
    rows = parsed if isinstance(parsed, list) else []

    scores, quotes, comments = {}, {}, {}
    for r in rows:
        if not isinstance(r, dict):
            continue
        rid = r.get("id")
        if not isinstance(rid, str):
            continue
        scores[rid] = _jsnum(r.get("score"))
        quotes[rid] = _text(r.get("quote"))
        comments[rid] = _text(r.get("comment"))

    feedback_raw = request.POST.get("feedback") or ""
    summary_raw = request.POST.get("summary") or ""
    publish = (
        _str_post(request, "intent") == "publish"
        or sub.assignment.release_mode == "langsung"
    )

    result = apply_grade_edits(
        str(sub.id),
        {
            "scores": scores,
            "quotes": quotes,
            "comments": comments,
            "feedback": feedback_raw.strip(),
            "summary": summary_raw.strip(),
            "publish": publish,
            "actor_id": lecturer.id,
        },
    )
    if not result["ok"]:
        rubric_rows = (
            [] if sub.assignment.type == "pg" else _db_rubric_rows(sub.assignment)
        )
        submitted = [
            {
                "criterion_id": r.get("id"),
                "score": r.get("score"),
                "quote": r.get("quote"),
                "comment": r.get("comment"),
            }
            for r in rows
            if isinstance(r, dict)
        ]
        rows_disp = _build_grade_rows(rubric_rows, submitted)
        live = compute_nilai(
            [{"score": r["score"], "weight": r["weight"]} for r in rows_disp]
        )
        return render(
            request,
            "lecturer/submission_detail.html",
            _submission_ctx(
                sub,
                g_error=result["error"],
                e_rows=rows_disp,
                e_criteria_json=_rows_json(rows_disp),
                e_feedback=feedback_raw,
                e_summary=summary_raw,
                live_nilai=js_number(live),
                live_predikat=predikat_of(live),
            ),
        )

    info = (
        "Nilai terbit."
        if result["state"] == "published"
        else "Nilai disimpan sebagai draf."
    )
    return _prg_submission(sub, info)


def _run_grade(request, lecturer, sub):
    publish = (
        _str_post(request, "intent") == "publish"
        or sub.assignment.release_mode == "langsung"
    )
    outcome = compute_grade(str(sub.id))
    if not outcome.get("ok"):
        return render(
            request,
            "lecturer/submission_detail.html",
            _submission_ctx(
                sub,
                g_error=outcome.get("message"),
                g_raw=outcome.get("raw"),
            ),
        )

    saved = persist_grade(
        str(sub.id),
        {
            "criteria": outcome["criteria"],
            "feedback": outcome["feedback"],
            "summary": outcome["summary"],
            "nilai": outcome["nilai"],
            "predikat": outcome["predikat"],
            "source": outcome["source"],
        },
        lecturer.id,
        publish,
    )
    info = (
        "Nilai terbit."
        if saved["state"] == "published"
        else "Nilai disimpan sebagai draf."
    )
    return _prg_submission(sub, info)
