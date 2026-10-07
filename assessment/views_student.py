"""Student assignment detail + submit (port of src/app/student/assignments/[id]/*)."""

import json
from uuid import UUID

from django.http import Http404, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.utils import timezone

from .extract import extract_file_text
from .grading import compute_grade, persist_grade
from .lib import submission_status
from .models import Assignment, AssignmentQuestion, Grade, Submission

STATUS_HINT = {
    "belum": "Kerjakan dan kirim jawaban Anda untuk mengumpulkan.",
    "draft": "Dosen sedang menyiapkan draf nilai.",
    "terkumpul": "Menunggu penilaian dosen.",
    "perlu_review": "Dosen sedang mereview jawaban Anda.",
    "dinilai": "Nilai sudah diterbitkan. Periksa hasil penilaian di bawah.",
}


def _student(request):
    user = request.user
    if not user.is_authenticated or user.role != "student":
        return None
    return user


def _str(value):
    """Node str(): trimmed string or empty."""
    return value.strip() if isinstance(value, str) else ""


def _assignment_for(assignment_id, student):
    try:
        aid = UUID(str(assignment_id))
    except (ValueError, TypeError, AttributeError):
        raise Http404
    assignment = (
        Assignment.objects.filter(
            id=aid, topic__course__enrolled__student=student
        )
        .select_related("topic__course")
        .first()
    )
    if assignment is None:
        raise Http404
    return assignment


def _question_dicts(assignment):
    return [
        {
            "position": q.position,
            "question": q.question,
            "options": q.options,
            "answer_key": q.answer_key,
        }
        for q in AssignmentQuestion.objects.filter(assignment=assignment).order_by(
            "position"
        )
    ]


def _page_ctx(request, student, assignment, form_error=None, form_answers=None, form_answer=""):
    questions = _question_dicts(assignment)
    course = assignment.topic.course
    submission = Submission.objects.filter(
        assignment=assignment, student=student
    ).first()
    grade = None
    if submission is not None:
        grade = Grade.objects.filter(
            submission_id=submission.id, state="published"
        ).first()

    status_key = submission_status(
        submission.status if submission else None, grade is not None
    )
    waiting = grade is None and submission is not None
    waiting_text = ""
    if waiting:
        if submission.status == "needs_review":
            waiting_text = "Tenang, jawabanmu sedang menunggu review dosen."
        else:
            waiting_text = "Tenang, nilai akan terbit setelah dosen me-review jawabanmu."

    just_submitted = (
        request.COOKIES.get("nilai_flash")
        == f"terkirim:{assignment.id}:{student.id}"
    )

    revealed = grade is not None
    lk_rows = []
    if submission is not None and assignment.type == "pg":
        sub_answers = submission.answers or []
        total = len(questions)
        for i, q in enumerate(questions):
            chosen = sub_answers[i] if i < len(sub_answers) else ""
            opts = []
            for o in (q["options"] or []):
                is_chosen = o.get("key") == chosen
                correct = revealed and q["answer_key"] == o.get("key")
                wrong = revealed and is_chosen and not correct
                opts.append(
                    {
                        "key": o.get("key"),
                        "text": o.get("text"),
                        "chosen": is_chosen,
                        "correct": correct,
                        "wrong": wrong,
                        "right_label": (
                            ("Benar" if is_chosen else "Kunci jawaban")
                            if correct
                            else None
                        ),
                    }
                )
            lk_rows.append(
                {
                    "question": q["question"],
                    "opts": opts,
                    "chosen": chosen,
                    "unanswered": not chosen,
                    "show_no": total > 1,
                }
            )

    answer_display = ""
    answer_empty = True
    if submission is not None and assignment.type == "essay":
        answer_display = (submission.answer_text or "").strip()
        answer_empty = not answer_display

    quiz_rows = []
    if assignment.type == "pg":
        selected = list(form_answers or [])
        for i, q in enumerate(questions):
            opts = []
            for o in (q["options"] or []):
                opts.append(
                    {
                        "key": o.get("key"),
                        "text": o.get("text"),
                        "checked": i < len(selected) and selected[i] == o.get("key"),
                    }
                )
            quiz_rows.append({"question": q["question"], "opts": opts})

    answers_json = json.dumps(list(form_answers or []))

    unanswered = 0
    if assignment.type == "pg":
        selected = list(form_answers or [])
        unanswered = sum(
            1
            for i in range(len(questions))
            if i >= len(selected) or not selected[i]
        )

    return {
        "revealed": revealed,
        "unanswered": unanswered,
        "crumb_root": "/student/home",
        "crumbs": [
            {"label": "Kursus", "href": "/student/courses"},
            {"label": course.code, "href": f"/student/courses/{course.id}"},
            {
                "label": f"Pertemuan {assignment.topic.week}",
                "href": f"/student/courses/{course.id}/topics/{assignment.topic_id}",
            },
            {"label": assignment.title},
        ],
        "asg": {
            "id": assignment.id,
            "title": assignment.title,
            "type": assignment.type,
            "release_mode": assignment.release_mode,
            "course_id": course.id,
            "code": course.code,
            "name": course.name,
            "week": assignment.topic.week,
            "topic_title": assignment.topic.title,
            "topic_id": assignment.topic_id,
            "questions": questions,
        },
        "sub": submission,
        "grade": grade,
        "status_key": status_key,
        "status_hint": STATUS_HINT.get(status_key),
        "waiting": waiting,
        "waiting_text": waiting_text,
        "just_submitted": just_submitted,
        "lk_rows": lk_rows,
        "answer_display": answer_display,
        "answer_empty": answer_empty,
        "quiz_rows": quiz_rows,
        "answers_json": answers_json,
        "form_error": form_error or "",
        "form_answer": form_answer or "",
        "total_questions": len(questions),
    }


def assignment_detail(request, assignment_id):
    student = _student(request)
    if student is None:
        return redirect("/login")
    assignment = _assignment_for(assignment_id, student)
    if request.method == "POST":
        return _submit(request, student, assignment)
    response = render(
        request, "student/assignment_detail.html", _page_ctx(request, student, assignment)
    )
    if "nilai_flash" in request.COOKIES:
        response.delete_cookie("nilai_flash")
    return response


def _render_form(request, student, assignment, error, answers=None, answer=""):
    return render(
        request,
        "student/assignment_detail.html",
        _page_ctx(
            request,
            student,
            assignment,
            form_error=error,
            form_answers=answers,
            form_answer=answer,
        ),
    )


def _submit(request, student, assignment):
    form_id = _str(request.POST.get("assignment_id"))
    try:
        form_uuid = UUID(form_id) if form_id else None
    except (ValueError, TypeError):
        form_uuid = None
    if form_uuid is None or form_uuid != assignment.id:
        return _render_form(request, student, assignment, "Tugas tidak ditemukan.")

    existing = Submission.objects.filter(
        assignment=assignment, student=student
    ).first()
    if existing is not None:
        return _render_form(request, student, assignment, "Pengumpulan sudah terkunci.")

    answer_text = None
    answers = []
    file_name = None
    extracted_text = None
    extraction_ok = None

    if assignment.type == "essay":
        answer_text = _str(request.POST.get("answer"))
        if not answer_text:
            return _render_form(
                request, student, assignment, "Tulis jawaban terlebih dahulu."
            )

    if assignment.type == "pg":
        questions = list(
            AssignmentQuestion.objects.filter(assignment=assignment).order_by(
                "position"
            )
        )
        if not questions:
            return _render_form(request, student, assignment, "Soal belum tersedia.")
        raw = _str(request.POST.get("answers"))
        try:
            parsed = json.loads(raw or "[]")
        except ValueError:
            parsed = None
        submitted = (
            [str(v).strip() if v is not None else "" for v in parsed]
            if isinstance(parsed, list)
            else []
        )
        radio = [
            _str(request.POST.get(f"choice_{i}")) for i in range(len(questions))
        ]
        if len(submitted) != len(questions) and all(radio):
            submitted = radio
        if len(submitted) != len(questions):
            return _render_form(
                request,
                student,
                assignment,
                "Jawaban tidak lengkap. Kerjakan seluruh soal.",
                answers=radio if any(radio) else submitted,
            )
        for i, q in enumerate(questions):
            opts = q.options if isinstance(q.options, list) else []
            if not submitted[i] or not any(o.get("key") == submitted[i] for o in opts):
                return _render_form(
                    request,
                    student,
                    assignment,
                    f"Soal ke-{i + 1}: pilih salah satu jawaban.",
                    answers=submitted,
                )
        answers = submitted

    if assignment.type in ("pdf", "docx"):
        upload = request.FILES.get("file")
        if upload is None or not upload.name.strip() or upload.size == 0:
            return _render_form(
                request, student, assignment, "Pilih berkas terlebih dahulu."
            )
        want_ext = ".pdf" if assignment.type == "pdf" else ".docx"
        if not upload.name.lower().endswith(want_ext):
            return _render_form(
                request,
                student,
                assignment,
                f"Berkas harus berformat {want_ext[1:].upper()}.",
            )
        file_name = upload.name
        result = extract_file_text(upload.name, upload.read())
        if result["ok"]:
            extracted_text = result["text"]
            extraction_ok = True
        else:
            extracted_text = None
            extraction_ok = False

    now = timezone.now()
    submission = Submission(
        assignment=assignment,
        student=student,
        answer_text=answer_text,
        answers=answers,
        file_name=file_name,
        extracted_text=extracted_text,
        extraction_ok=extraction_ok,
        status="submitted",
        submitted_at=now,
    )
    submission.save()

    if assignment.release_mode == "langsung":
        outcome = compute_grade(str(submission.id))
        if outcome.get("ok"):
            persist_grade(
                str(submission.id),
                {
                    "criteria": outcome["criteria"],
                    "feedback": outcome["feedback"],
                    "summary": outcome["summary"],
                    "nilai": outcome["nilai"],
                    "predikat": outcome["predikat"],
                    "source": outcome["source"],
                },
                None,
                True,
            )
        else:
            submission.status = "needs_review"
            submission.save()

    response = HttpResponseRedirect(f"/student/assignments/{assignment.id}")
    response.set_cookie(
        "nilai_flash",
        f"terkirim:{assignment.id}:{student.id}",
        max_age=30,
        samesite="Lax",
    )
    return response
