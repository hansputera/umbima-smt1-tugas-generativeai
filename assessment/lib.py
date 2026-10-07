"""Shared helpers for lecturer assessment pages (port of src/lib/lecturer.ts,
src/lib/settings.ts, src/lib/status.ts and src/lib/grading/score.ts)."""

import math
import re
from decimal import Decimal

from accounts.models import ModelSettings

UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I
)

SYSTEM_PREAMBLE_DEFAULT = (
    "Anda adalah asisten penilaian mata kuliah. "
    "Balas dalam bahasa Indonesia yang singkat dan jelas."
)


def get_settings():
    """Port of getSettings: ensure model_settings id=1 exists."""
    ms, _ = ModelSettings.objects.get_or_create(
        id=1, defaults={"system_preamble": SYSTEM_PREAMBLE_DEFAULT}
    )
    return ms


def is_model_configured(s):
    """Port of isModelConfigured."""
    return bool(s.api_key.strip() and s.base_url.strip() and s.model_name.strip())


def is_embedding_configured(s):
    """Port of isEmbeddingConfigured."""
    return bool(
        s.emb_api_key.strip() and s.emb_base_url.strip() and s.emb_model_name.strip()
    )


def require_lecturer_assignment(request, assignment_id):
    """Port of requireLecturerAssignment: assignment only for this lecturer."""
    from academics.lib import get_lecturer

    from .models import Assignment

    lecturer = get_lecturer(request)
    if lecturer is None:
        return None
    return (
        Assignment.objects.filter(
            id=assignment_id, topic__course__lecturers__user=lecturer
        )
        .select_related("topic__course__period")
        .first()
    )


def submission_status(status, has_published_grade):
    """Port of submissionStatus from src/lib/status.ts."""
    if not status:
        return "belum"
    if status == "needs_review":
        return "perlu_review"
    if status == "draft":
        return "draft"
    if status == "submitted":
        return "dinilai" if has_published_grade else "terkumpul"
    return "belum"


def predikat_of(nilai):
    """Port of predikatOf."""
    if nilai >= 85:
        return "A"
    if nilai >= 70:
        return "B"
    if nilai >= 55:
        return "C"
    return "D"


def compute_nilai(criteria):
    """Port of computeNilai: round(sum(score/4 * weight) * 100) / 100."""
    total = 0.0
    for c in criteria:
        total += (float(c.get("score")) / 4) * float(c.get("weight"))
    return math.floor(total * 100 + 0.5) / 100


def number_value(value):
    """Port of JavaScript Number() (used for user-supplied numeric fields)."""
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if value is None:
        return 0.0
    if isinstance(value, (int, float, Decimal)):
        return float(value)
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return 0.0
        try:
            return float(s)
        except ValueError:
            return float("nan")
    return float("nan")


def js_number(value):
    """Format a number like JavaScript String(number) for display."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)
