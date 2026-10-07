"""Lecturer-side helpers shared by academics and assessment views.

Ports of src/lib/course-view.ts (frame/upcoming), src/lib/lecturer.ts
(guards), and the course-list queries in src/app/lecturer.
"""

from collections import Counter

from django.db.models import Count, Q
from django.utils import timezone

from assessment.models import Assignment, Submission
from .models import Course, Enrollment, MateriBlock, Topic


def get_lecturer(request):
    """Port of requireLecturer (middleware already gates auth + role + status)."""
    user = request.user
    if not user.is_authenticated or user.role != "lecturer":
        return None
    return user


def get_lecturer_course(course_id, lecturer):
    """Port of requireLecturerCourse: course only if this lecturer is assigned."""
    if lecturer is None:
        return None
    return (
        Course.objects.filter(id=course_id, lecturers__user=lecturer)
        .select_related("period")
        .first()
    )


def course_context(course):
    """Fields shared by every course sub-page."""
    return {
        "id": course.id,
        "code": course.code,
        "name": course.name,
        "semester": course.semester,
        "sks": course.sks,
        "section": course.section,
        "archived_at": course.archived_at,
        "period_name": course.period.name,
        "period_active": course.period.is_active,
    }


def course_cards(lecturer):
    """Port of the /lecturer/courses and /lecturer/home course-grid query."""
    courses = list(
        Course.objects.filter(lecturers__user=lecturer)
        .select_related("period")
        .order_by(
            "archived_at",
            "-period__is_active",
            "period__created_at",
            "code",
            "section",
        )
    )
    if not courses:
        return []
    ids = [c.id for c in courses]

    topic_counts = dict(
        Topic.objects.filter(course_id__in=ids)
        .values_list("course_id")
        .annotate(n=Count("id"))
    )
    assignments = list(
        Assignment.objects.filter(topic__course_id__in=ids).values(
            "id", "topic__course_id"
        )
    )
    assignment_counts = Counter(a["topic__course_id"] for a in assignments)
    collected_ids = set(
        Submission.objects.exclude(status="draft")
        .filter(assignment_id__in=[a["id"] for a in assignments])
        .values_list("assignment_id", flat=True)
    )
    collected_counts = Counter(
        a["topic__course_id"] for a in assignments if a["id"] in collected_ids
    )

    cards = []
    for c in courses:
        cid = c.id
        cards.append(
            {
                "id": cid,
                "code": c.code,
                "name": c.name,
                "semester": c.semester,
                "sks": c.sks,
                "section": c.section,
                "archived": bool(c.archived_at),
                "period_name": c.period.name,
                "topic_count": topic_counts.get(cid, 0),
                "assignment_count": assignment_counts.get(cid, 0),
                "collected_count": collected_counts.get(cid, 0),
            }
        )
    return cards


def materi_title(block):
    """Port of materiTitle (src/lib/course-view.ts)."""
    if block.type == "file":
        return (block.file_name or "").strip() or "Berkas"
    if block.type == "link":
        return (block.body or "").strip() or (block.url or "").strip() or "Tautan"
    first = next(
        (line.strip() for line in (block.body or "").split("\n") if line.strip()),
        None,
    )
    if not first:
        return "Materi"
    return first[:60] + "…" if len(first) > 60 else first


def course_frame(course, role, student_id=None):
    """Port of getCourseFrame: lecturer (submitted counts) or student (status)."""
    topics = list(Topic.objects.filter(course=course).order_by("week"))
    blocks = list(
        MateriBlock.objects.filter(topic__course=course).order_by(
            "topic__week", "position"
        )
    )
    assignments = list(
        Assignment.objects.filter(topic__course=course).order_by(
            "topic__week", "created_at"
        )
    )

    student_subs = {}
    student_grades = {}
    if role == "student" and assignments:
        from assessment.models import Grade

        subs = Submission.objects.filter(
            assignment_id__in=[a.id for a in assignments],
            student_id=student_id,
        ).values_list("assignment_id", "id", "status")
        sub_ids = [row[1] for row in subs]
        grade_by_sub = {
            row[0]: (row[1], row[2])
            for row in Grade.objects.filter(
                submission_id__in=sub_ids
            ).values_list("submission_id", "state", "nilai")
        }
        for aid, sid, status in subs:
            student_subs[aid] = status
            student_grades[aid] = grade_by_sub.get(sid)
    else:
        submitted_counts = dict(
            Submission.objects.exclude(status="draft")
            .filter(assignment_id__in=[a.id for a in assignments])
            .values_list("assignment_id")
            .annotate(n=Count("id"))
        )

    blocks_by_topic = {}
    for b in blocks:
        blocks_by_topic.setdefault(b.topic_id, []).append(b)
    assignments_by_topic = {}
    for a in assignments:
        assignments_by_topic.setdefault(a.topic_id, []).append(a)

    frame_topics = []
    for t in topics:
        items = []
        for b in blocks_by_topic.get(t.id, []):
            items.append(
                {
                    "kind": "materi",
                    "id": b.id,
                    "topic_id": t.id,
                    "title": materi_title(b),
                    "type": "materi",
                    "href": f"/{role}/courses/{course.id}/topics/{t.id}",
                }
            )
        for a in assignments_by_topic.get(t.id, []):
            item = {
                "kind": "assignment",
                "id": a.id,
                "topic_id": t.id,
                "title": a.title,
                "type": a.type,
                "release_mode": a.release_mode,
                "due_at": a.due_at,
                "href": f"/{role}/assignments/{a.id}",
            }
            if role == "student":
                g = student_grades.get(a.id)
                item["status"] = student_subs.get(a.id)
                item["grade_state"] = g[0] if g else None
                item["nilai"] = g[1] if g else None
            else:
                item["submitted_count"] = submitted_counts.get(a.id, 0)
            items.append(item)
        frame_topics.append(
            {
                "id": t.id,
                "week": t.week,
                "title": t.title,
                "href": f"/{role}/courses/{course.id}/topics/{t.id}",
                "items": items,
            }
        )
    return {
        "topics": frame_topics,
        "enrolled": Enrollment.objects.filter(course=course).count(),
    }


def upcoming(course_id, limit=5, role="lecturer", student_id=None):
    """Port of getUpcoming: future deadlines, this course (role-aware)."""
    now = timezone.now()
    qs = Assignment.objects.filter(topic__course_id=course_id, due_at__gt=now)
    if role == "student":
        from django.db.models import Exists, OuterRef

        mine = Submission.objects.filter(
            assignment_id=OuterRef("pk"), student_id=student_id
        )
        qs = qs.annotate(
            my_draft=Exists(mine.filter(status="draft")),
            my_sub=Exists(mine),
        ).filter(Q(my_draft=True) | Q(my_sub=False))
    rows = qs.order_by("due_at")
    out = []
    for a in rows:
        out.append(
            {
                "id": a.id,
                "title": a.title,
                "type": a.type,
                "due_at": a.due_at,
                "href": f"/{role}/assignments/{a.id}",
            }
        )
        if len(out) >= limit:
            break
    return out


def upcoming_all(lecturer, limit=5):
    """Port of the home-page upcoming query: all courses, by due date."""
    now = timezone.now()
    rows = (
        Assignment.objects.filter(
            topic__course__lecturers__user=lecturer, due_at__gt=now
        )
        .select_related("topic__course")
        .order_by("due_at")[:limit]
    )
    return [
        {
            "id": a.id,
            "title": a.title,
            "type": a.type,
            "due_at": a.due_at,
            "code": a.topic.course.code,
            "href": f"/lecturer/assignments/{a.id}",
        }
        for a in rows
    ]


def with_card_meta(cards):
    """Course-card meta line + progress percent (Math.round parity)."""
    import math

    for c in cards:
        c["meta"] = f"Kelas {c['section']} · {c['period_name']}"
        c["progress"] = (
            math.floor(c["collected_count"] / c["assignment_count"] * 100 + 0.5)
            if c["assignment_count"]
            else 0
        )
    return cards


def student_course_cards(student):
    """Port of the /student/home and /student/courses course-grid query."""
    import math

    from assessment.models import Grade

    from .models import CourseLecturer

    courses = list(
        Course.objects.filter(enrolled__student=student)
        .select_related("period")
        .order_by(
            "-period__is_active",
            "period__created_at",
            "code",
            "section",
        )
    )
    if not courses:
        return []
    ids = [c.id for c in courses]

    assignment_counts = dict(
        Assignment.objects.filter(topic__course_id__in=ids)
        .values_list("topic__course_id")
        .annotate(n=Count("id"))
    )
    done_counts = dict(
        Grade.objects.filter(
            state="published",
            submission__student_id=student.id,
            submission__assignment__topic__course_id__in=ids,
        )
        .values_list("submission__assignment__topic__course_id")
        .annotate(n=Count("id"))
    )
    lecturers = {}
    for cid, name in (
        CourseLecturer.objects.filter(course_id__in=ids)
        .values_list("course_id", "user__name")
        .order_by("user__name")
    ):
        lecturers.setdefault(cid, []).append(name)

    cards = []
    for c in courses:
        cid = c.id
        meta = f"Kelas {c.section} · {c.period.name}"
        names = lecturers.get(cid)
        if names:
            meta += " · " + ", ".join(names)
        total = assignment_counts.get(cid, 0)
        done = done_counts.get(cid, 0)
        cards.append(
            {
                "id": cid,
                "code": c.code,
                "name": c.name,
                "semester": c.semester,
                "sks": c.sks,
                "archived": bool(c.archived_at),
                "meta": meta,
                "done": done,
                "total": total,
                "progress": math.floor(done / total * 100 + 0.5) if total else 0,
            }
        )
    return cards


def student_upcoming_all(student, limit=5):
    """Port of the student home-page upcoming query."""
    from django.db.models import Exists, OuterRef

    now = timezone.now()
    mine = Submission.objects.filter(
        assignment_id=OuterRef("pk"), student_id=student.id
    )
    rows = (
        Assignment.objects.filter(
            topic__course__enrolled__student=student, due_at__gt=now
        )
        .annotate(my_draft=Exists(mine.filter(status="draft")), my_sub=Exists(mine))
        .filter(Q(my_draft=True) | Q(my_sub=False))
        .select_related("topic__course")
        .order_by("due_at")[:limit]
    )
    return [
        {
            "id": a.id,
            "title": a.title,
            "type": a.type,
            "due_at": a.due_at,
            "code": a.topic.course.code,
            "href": f"/student/assignments/{a.id}",
        }
        for a in rows
    ]


def recent_grades(course_id, role, student_id=None, limit=5):
    """Port of getRecentGrades: latest published grades for the course rail."""
    from django.db.models import F

    from assessment.models import Grade

    qs = Grade.objects.filter(
        state="published",
        submission__assignment__topic__course_id=course_id,
    ).select_related("submission__assignment")
    if role == "student":
        qs = qs.filter(submission__student_id=student_id)
    qs = qs.order_by(F("published_at").desc(nulls_last=True), "-updated_at")[:limit]
    return [
        {
            "assignment_id": g.submission.assignment_id,
            "title": g.submission.assignment.title,
            "nilai": g.nilai,
            "predikat": g.predikat,
            "published_at": g.published_at,
            "href": f"/{role}/assignments/{g.submission.assignment_id}",
        }
        for g in qs
    ]
