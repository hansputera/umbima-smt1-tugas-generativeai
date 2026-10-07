"""Grading core (port of src/lib/grading/index.ts grading functions)."""

import math

from django.core.exceptions import ValidationError
from django.utils import timezone

from .ai import call_chat
from .lib import (
    compute_nilai,
    get_settings,
    is_embedding_configured,
    is_model_configured,
    number_value,
    predikat_of,
)
from .models import Grade, GradeRevision, RubricCriterion, Submission
from .prompt import build_messages
from .rag import ensure_chunks, retrieve_excerpts
from .validate import parse_model_response


def _text(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def submission_context(submission_id):
    """ORM port of SUBMISSION_SQL: submission joined with assignment chain."""
    try:
        sub = (
            Submission.objects.select_related(
                "assignment__topic__course__period", "student"
            )
            .get(id=submission_id)
        )
    except (Submission.DoesNotExist, ValueError, ValidationError):
        return None
    assignment = sub.assignment
    topic = assignment.topic
    course = topic.course
    questions = [
        {
            "position": q.position,
            "question": q.question,
            "options": q.options,
            "answer_key": q.answer_key,
        }
        for q in assignment.questions.order_by("position")
    ]
    return {
        "id": str(sub.id),
        "assignment_id": str(sub.assignment_id),
        "student_id": str(sub.student_id),
        "answer_text": sub.answer_text,
        "answers": sub.answers,
        "file_name": sub.file_name,
        "extracted_text": sub.extracted_text,
        "extraction_ok": sub.extraction_ok,
        "status": sub.status,
        "submitted_at": sub.submitted_at,
        "updated_at": sub.updated_at,
        "assignment_title": assignment.title,
        "type": assignment.type,
        "questions": questions,
        "release_mode": assignment.release_mode,
        "topic_id": str(topic.id),
        "topic_title": topic.title,
        "week": topic.week,
        "course_id": str(course.id),
        "course_code": course.code,
        "course_name": course.name,
        "student_name": sub.student.name,
        "student_email": sub.student.email,
    }


def get_rubric(assignment_id):
    """Port of getRubric: ordered rubric criteria as plain dicts."""
    return [
        {
            "id": str(c.id),
            "assignment_id": str(c.assignment_id),
            "position": c.position,
            "name": c.name,
            "weight": c.weight,
            "level_1": c.level_1,
            "level_2": c.level_2,
            "level_3": c.level_3,
            "level_4": c.level_4,
            "prompt_notes": c.prompt_notes,
        }
        for c in RubricCriterion.objects.filter(
            assignment_id=assignment_id
        ).order_by("position", "name")
    ]


def get_grade(submission_id):
    return Grade.objects.filter(submission_id=submission_id).first()


def is_lecturer_assigned(course_id, lecturer_id):
    from academics.models import CourseLecturer

    return CourseLecturer.objects.filter(
        course_id=course_id, user_id=lecturer_id
    ).exists()


def get_lecturer_submission(submission_id, lecturer_id):
    ctx = submission_context(submission_id)
    if ctx is None:
        return None
    return ctx if is_lecturer_assigned(ctx["course_id"], lecturer_id) else None


# ---------------------------------------------------------------------------
# Grading
# ---------------------------------------------------------------------------


def compute_grade(submission_id):
    """Port of computeGrade: pg code path, empty path, and model pipeline."""
    sub = submission_context(submission_id)
    if sub is None:
        return {"ok": False, "message": "Pengumpulan tidak ditemukan."}
    rubric = get_rubric(sub["assignment_id"])

    if sub["type"] == "pg":
        questions = sub["questions"] or []
        answers = sub["answers"] or []
        total = len(questions)
        correct = sum(
            1
            for i, q in enumerate(questions)
            if q["answer_key"] and i < len(answers) and answers[i] == q["answer_key"]
        )
        nilai = 0 if total == 0 else math.floor((correct / total) * 10000 + 0.5) / 100
        return {
            "ok": True,
            "criteria": [],
            "feedback": f"{correct} dari {total} jawaban benar.",
            "summary": "Dinilai otomatis dari kunci jawaban, tanpa model.",
            "nilai": nilai,
            "predikat": predikat_of(nilai),
            "source": "code",
        }

    is_file = sub["type"] in ("pdf", "docx")
    text = (sub["extracted_text"] or "") if is_file else (sub["answer_text"] or "")
    prompt_text = "\n".join(
        item["question"] for item in (sub["questions"] or [])
    )

    if is_file and sub["extraction_ok"] is False:
        return {"ok": False, "message": "Teks tidak terbaca."}

    if not text.strip():
        if len(rubric) == 0:
            return {"ok": False, "message": "Rubrik belum disetel."}
        criteria = [
            {
                "criterion_id": c["id"],
                "name": c["name"],
                "weight": c["weight"],
                "score": 1,
                "quote": "",
                "comment": "Jawaban kosong.",
            }
            for c in rubric
        ]
        nilai = compute_nilai(criteria)
        return {
            "ok": True,
            "criteria": criteria,
            "feedback": "Jawaban kosong.",
            "summary": "Jawaban kosong, model tidak dipanggil.",
            "nilai": nilai,
            "predikat": predikat_of(nilai),
            "source": "empty",
        }

    settings = get_settings()
    if not is_model_configured(settings):
        return {"ok": False, "message": "Model belum disetel."}
    if len(rubric) == 0:
        return {"ok": False, "message": "Rubrik belum disetel."}

    need_rag = is_file or len(text) > 6000
    if need_rag:
        if not is_embedding_configured(settings):
            return {"ok": False, "message": "Embedding belum disetel."}
        try:
            ensure_chunks(sub["id"], text, settings)
            query = (
                prompt_text
                + "\n"
                + "\n".join(c["name"] for c in rubric)
            )
            excerpts = retrieve_excerpts(sub["id"], query, settings)
            if len(excerpts) == 0:
                return {"ok": False, "message": "Teks tidak terbaca."}
            answer = {"kind": "doc", "excerpts": excerpts}
        except Exception as err:  # noqa: BLE001 - Node catches any error here
            detail = str(err) if isinstance(err, Exception) else "tidak diketahui"
            return {"ok": False, "message": f"Embedding gagal. {detail}"[:300]}
    else:
        answer = {"kind": "text", "text": text}

    messages = build_messages(
        preamble=settings.system_preamble,
        question=prompt_text,
        answer=answer,
        rubric=rubric,
    )

    temperature = number_value(settings.temperature)
    if temperature.is_integer():
        temperature = int(temperature)
    result = call_chat(
        settings,
        messages,
        temperature=temperature,
        max_tokens=int(number_value(settings.max_tokens)),
    )
    if not result["ok"]:
        return {"ok": False, "message": f"Gagal memanggil model. {result['message']}"}

    parsed = parse_model_response(result["content"], rubric)
    if not parsed["ok"]:
        return {
            "ok": False,
            "message": "Respons model tidak valid. " + " ".join(parsed["errors"]),
            "raw": result["content"],
        }

    criteria = []
    for entry in parsed["data"]["criteria"]:
        c = next((r for r in rubric if r["id"] == entry["id"]), None)
        if c is None:
            continue
        criteria.append(
            {
                "criterion_id": c["id"],
                "name": c["name"],
                "weight": c["weight"],
                "score": entry["score"],
                "quote": entry["quote"],
                "comment": entry["comment"],
            }
        )

    nilai = compute_nilai(criteria)
    return {
        "ok": True,
        "criteria": criteria,
        "feedback": parsed["data"]["feedback"],
        "summary": parsed["data"]["summary"],
        "nilai": nilai,
        "predikat": predikat_of(nilai),
        "source": "model",
    }


def persist_grade(submission_id, data, actor_id, publish):
    """Port of persistGrade: upsert grade + append revision row."""
    existing = (
        Grade.objects.filter(submission_id=submission_id)
        .values("id", "state")
        .first()
    )
    state = "published" if publish else (existing["state"] if existing else "draft")
    just_published = state == "published" and (
        existing is None or existing["state"] != "published"
    )
    now = timezone.now()
    snapshot = {
        "criteria": data["criteria"],
        "feedback": data["feedback"],
        "summary": data["summary"],
    }

    if existing:
        grade = Grade.objects.get(id=existing["id"])
        grade.state = state
        grade.criteria = data["criteria"]
        grade.feedback = data["feedback"]
        grade.summary = data["summary"]
        grade.nilai = data["nilai"]
        grade.predikat = data["predikat"]
        grade.source = data["source"]
        grade.updated_by_id = actor_id
        grade.updated_at = now
        if just_published:
            grade.published_at = now
        grade.save()
    else:
        grade = Grade.objects.create(
            submission_id=submission_id,
            state=state,
            criteria=data["criteria"],
            feedback=data["feedback"],
            summary=data["summary"],
            nilai=data["nilai"],
            predikat=data["predikat"],
            source=data["source"],
            created_by_id=actor_id,
            updated_by_id=actor_id,
            published_at=now if state == "published" else None,
        )

    GradeRevision.objects.create(
        grade_id=grade.id,
        snapshot=snapshot,
        nilai=data["nilai"],
        predikat=data["predikat"],
        state=state,
        changed_by_id=actor_id,
    )
    return {"id": str(grade.id), "state": state}


def apply_grade_edits(submission_id, input_):
    """Port of applyGradeEdits: validate manual edits, compute, persist."""
    grade = get_grade(submission_id)

    ctx = submission_context(submission_id)
    if ctx is None:
        return {"ok": False, "error": "Pengumpulan tidak ditemukan."}

    feedback = _text(input_.get("feedback"))
    summary = _text(input_.get("summary"))
    if not feedback.strip():
        return {"ok": False, "error": "Umpan balik wajib diisi."}

    rubric = [] if ctx["type"] == "pg" else get_rubric(ctx["assignment_id"])

    if grade is None and len(rubric) == 0:
        return {
            "ok": False,
            "error": "Belum ada nilai. Jalankan penilaian otomatis terlebih dahulu.",
        }

    scores = input_.get("scores") or {}
    quotes = input_.get("quotes") or {}
    comments = input_.get("comments") or {}

    if len(rubric) > 0:
        criteria = []
        prev_list = grade.criteria if grade is not None else []
        for c in rubric:
            cid = c["id"]
            prev = next(
                (
                    x
                    for x in prev_list
                    if isinstance(x, dict) and x.get("criterion_id") == cid
                ),
                None,
            )
            raw = scores.get(cid)
            if raw is None:
                raw = prev.get("score") if prev is not None else 1
            score = number_value(raw)
            if not score.is_integer() or score < 1 or score > 4:
                return {
                    "ok": False,
                    "error": f'Skor tidak valid pada "{c["name"]}".',
                }
            quote = quotes.get(cid)
            if quote is None:
                quote = prev.get("quote") if prev is not None else ""
                if quote is None:
                    quote = ""
            comment = comments.get(cid)
            if comment is None:
                comment = prev.get("comment") if prev is not None else ""
                if comment is None:
                    comment = ""
            criteria.append(
                {
                    "criterion_id": cid,
                    "name": c["name"],
                    "weight": c["weight"],
                    "score": int(score),
                    "quote": _text(quote),
                    "comment": _text(comment),
                }
            )
    else:
        criteria = grade.criteria

    nilai = compute_nilai(criteria) if len(criteria) > 0 else float(grade.nilai)
    predikat = predikat_of(nilai)

    saved = persist_grade(
        submission_id,
        {
            "criteria": criteria,
            "feedback": feedback.strip(),
            "summary": summary.strip(),
            "nilai": nilai,
            "predikat": predikat,
            "source": grade.source if grade is not None else "manual",
        },
        input_.get("actor_id"),
        input_.get("publish", False),
    )
    return {"ok": True, "nilai": nilai, "predikat": predikat, "state": saved["state"]}
