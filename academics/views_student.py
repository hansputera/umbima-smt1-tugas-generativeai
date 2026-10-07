"""Student pages (port of src/app/student/*)."""

from uuid import UUID

from django.http import Http404
from django.shortcuts import render

from assessment.lib import submission_status
from .lib import (
    course_context,
    course_frame,
    recent_grades,
    student_course_cards,
    student_upcoming_all,
    upcoming,
)
from .models import Course, CourseLecturer, Enrollment, MateriBlock, Topic

ROLE_HOME = "/student/home"


def get_student(request):
    user = request.user
    if not user.is_authenticated or user.role != "student":
        return None
    return user


def _guard_student_course(request, course_id):
    """Node notFound(): course must exist and this student must be enrolled."""
    student = get_student(request)
    if student is None:
        return None, None, None, render_error_home()
    try:
        cid = UUID(str(course_id))
    except (ValueError, TypeError, AttributeError):
        raise Http404
    course = (
        Course.objects.filter(id=cid, enrolled__student=student)
        .select_related("period")
        .first()
    )
    if course is None:
        raise Http404
    return student, course, None, None


def render_error_home():
    from django.shortcuts import redirect

    return redirect(ROLE_HOME)


def _course_base(student, course):
    return {
        "course": course_context(course),
        "crumb_root": ROLE_HOME,
        "crumbs": [
            {"label": "Kursus", "href": "/student/courses"},
            {"label": course.code},
        ],
        "frame": course_frame(course, "student", student.id),
    }


def home(request):
    student = get_student(request)
    if student is None:
        return render_error_home()
    cards = student_course_cards(student)
    return render(
        request,
        "student/home.html",
        {
            "cards": cards,
            "upcoming": student_upcoming_all(student),
            "crumbs": [{"label": "Beranda"}],
        },
    )


def courses(request):
    student = get_student(request)
    if student is None:
        return render_error_home()
    return render(
        request,
        "student/courses.html",
        {
            "cards": student_course_cards(student),
            "crumbs": [{"label": "Kursus saya"}],
        },
    )


def course_page(request, course_id):
    student, course, err, _ = _guard_student_course(request, course_id)
    if err is not None:
        return err
    base = _course_base(student, course)
    for t in base["frame"]["topics"]:
        rows_a = [i for i in t["items"] if i["kind"] == "assignment"]
        t["a_count"] = len(rows_a)
        t["answered"] = sum(1 for i in rows_a if i.get("status"))
    return render(
        request,
        "student/course.html",
        {
            **base,
            "upcoming": upcoming(
                course.id, role="student", student_id=student.id
            ),
            "recent": recent_grades(
                course.id, "student", student.id
            ),
        },
    )


def peserta_page(request, course_id):
    student, course, err, _ = _guard_student_course(request, course_id)
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
    ctx = _course_base(student, course)
    ctx["crumbs"] = ctx["crumbs"] + [{"label": "Peserta"}]
    ctx["lecturer_rows"] = [
        {"name": cl.user.name, "email": cl.user.email} for cl in lecturers
    ]
    ctx["student_rows"] = [
        {"name": e.student.name, "email": e.student.email} for e in students
    ]
    return render(request, "lecturer/peserta.html", ctx)


def tugas_page(request, course_id):
    from assessment.models import Assignment, Grade, Submission

    student, course, err, _ = _guard_student_course(request, course_id)
    if err is not None:
        return err
    assignments = list(
        Assignment.objects.filter(topic__course=course).order_by(
            "topic__week", "created_at"
        )
    )
    subs = {
        row[0]: (row[1], row[2])
        for row in Submission.objects.filter(
            assignment_id__in=[a.id for a in assignments],
            student_id=student.id,
        ).values_list("assignment_id", "id", "status")
    }
    grade_by_sub = {}
    sub_ids = [v[0] for v in subs.values()]
    for row in Grade.objects.filter(submission_id__in=sub_ids).values_list(
        "submission_id", "state", "nilai"
    ):
        grade_by_sub[row[0]] = (row[1], row[2])

    rows = []
    for a in assignments:
        sub = subs.get(a.id)
        status = sub[1] if sub else None
        g = grade_by_sub.get(sub[0]) if sub else None
        grade_state = g[0] if g else None
        nilai = g[1] if g else None
        rows.append(
            {
                "id": a.id,
                "title": a.title,
                "week": a.topic.week,
                "due_at": a.due_at,
                "status_key": submission_status(
                    status, grade_state == "published"
                ),
                "nilai": nilai if grade_state == "published" else None,
            }
        )
    ctx = _course_base(student, course)
    ctx["crumbs"] = ctx["crumbs"] + [{"label": "Tugas"}]
    ctx["rows"] = rows
    return render(request, "student/tugas.html", ctx)


def nilai_page(request, course_id):
    from django.db.models import F

    from assessment.models import Grade

    student, course, err, _ = _guard_student_course(request, course_id)
    if err is not None:
        return err
    grades = (
        Grade.objects.filter(
            state="published",
            submission__student_id=student.id,
            submission__assignment__topic__course=course,
        )
        .select_related("submission__assignment__topic")
        .order_by(
            F("published_at").desc(nulls_last=True),
            "-updated_at",
        )
    )
    rows = [
        {
            "assignment_id": g.submission.assignment_id,
            "title": g.submission.assignment.title,
            "week": g.submission.assignment.topic.week,
            "nilai": g.nilai,
            "predikat": g.predikat,
            "published_at": g.published_at,
        }
        for g in grades
    ]
    ctx = _course_base(student, course)
    ctx["crumbs"] = ctx["crumbs"] + [{"label": "Nilai"}]
    ctx["rows"] = rows
    return render(request, "student/nilai.html", ctx)


def topic_page(request, course_id, topic_id):
    from assessment.models import Assignment, Grade, Submission

    student, course, err, _ = _guard_student_course(request, course_id)
    if err is not None:
        return err
    try:
        tid = UUID(str(topic_id))
    except (ValueError, TypeError, AttributeError):
        raise Http404
    topic = Topic.objects.filter(id=tid, course=course).first()
    if topic is None:
        raise Http404

    frame = course_frame(course, "student", student.id)
    idx = next(
        (i for i, t in enumerate(frame["topics"]) if t["id"] == topic.id), -1
    )
    prev_t = frame["topics"][idx - 1] if idx > 0 else None
    next_t = (
        frame["topics"][idx + 1]
        if 0 <= idx < len(frame["topics"]) - 1
        else None
    )

    blocks = list(
        MateriBlock.objects.filter(topic=topic).order_by("position")
    )
    assignments = list(
        Assignment.objects.filter(topic=topic).order_by("created_at")
    )
    subs = {
        row[0]: (row[1], row[2])
        for row in Submission.objects.filter(
            assignment_id__in=[a.id for a in assignments],
            student_id=student.id,
        ).values_list("assignment_id", "id", "status")
    }
    grade_by_sub = {}
    sub_ids = [v[0] for v in subs.values()]
    for row in Grade.objects.filter(submission_id__in=sub_ids).values_list(
        "submission_id", "state", "nilai"
    ):
        grade_by_sub[row[0]] = (row[1], row[2])

    rows = []
    for a in assignments:
        sub = subs.get(a.id)
        status = sub[1] if sub else None
        g = grade_by_sub.get(sub[0]) if sub else None
        grade_state = g[0] if g else None
        nilai = g[1] if g else None
        rows.append(
            {
                "id": a.id,
                "href": f"/student/assignments/{a.id}",
                "title": a.title,
                "type": a.type,
                "release_mode": a.release_mode,
                "status_key": submission_status(
                    status, grade_state == "published"
                ),
                "nilai": nilai if grade_state == "published" else None,
                "action": (
                    "Lihat jawaban" if status is not None else "Kerjakan"
                ),
            }
        )

    return render(
        request,
        "student/topic_detail.html",
        {
            **_course_base(student, course),
            "active_topic_id": str(topic.id),
            "crumbs": [
                {"label": "Kursus", "href": "/student/courses"},
                {"label": course.code, "href": f"/student/courses/{course.id}"},
                {"label": f"Pertemuan {topic.week}"},
            ],
            "topic": {"id": topic.id, "week": topic.week, "title": topic.title},
            "block_rows": [
                {
                    "type": b.type,
                    "body": b.body,
                    "url": b.url,
                    "file_name": b.file_name,
                }
                for b in blocks
            ],
            "rows": rows,
            "prev": prev_t,
            "next": next_t,
        },
    )


def tasks(request):
    from assessment.models import Assignment, Grade, Submission

    student = get_student(request)
    if student is None:
        return render_error_home()
    rows = list(
        Assignment.objects.filter(topic__course__enrolled__student=student)
        .select_related("topic__course")
        .order_by(
            "topic__course__code",
            "topic__week",
            "created_at",
        )
    )
    sub_map = {
        row[0]: (row[1], row[2])
        for row in Submission.objects.filter(
            assignment_id__in=[a.id for a in rows],
            student_id=student.id,
        ).values_list("assignment_id", "id", "status")
    }
    grade_by_sub = {}
    sub_ids = [v[0] for v in sub_map.values()]
    for row in Grade.objects.filter(
        submission_id__in=sub_ids, state="published"
    ).values_list("submission_id", "nilai"):
        grade_by_sub[row[0]] = row[1]

    enriched = []
    for a in rows:
        sub = sub_map.get(a.id)
        status = sub[1] if sub else None
        nilai = grade_by_sub.get(sub[0]) if sub else None
        submitted = status is not None
        enriched.append(
            {
                "id": a.id,
                "href": f"/student/assignments/{a.id}",
                "title": a.title,
                "type": a.type,
                "release_mode": a.release_mode,
                "week": a.topic.week,
                "course_code": a.topic.course.code,
                "sub": f"{a.topic.course.code} · Pertemuan {a.topic.week}",
                "sub_status": status,
                "status_key": submission_status(
                    status, sub is not None and sub[0] in grade_by_sub
                ),
                "nilai": nilai,
                "action": "Lihat jawaban" if submitted else "Kerjakan",
            }
        )

    todo = [r for r in enriched if r["sub_status"] is None]
    done = [r for r in enriched if r["sub_status"] is not None]

    if not enriched:
        description = "Semua tugas dari mata kuliah yang Anda ikuti."
    elif todo:
        description = f"{len(todo)} tugas belum dikerjakan."
    else:
        description = "Semua tugas sudah dikumpulkan."

    return render(
        request,
        "student/tasks.html",
        {
            "todo": todo,
            "done": done,
            "description": description,
            "crumbs": [{"label": "Tugas"}],
        },
    )
