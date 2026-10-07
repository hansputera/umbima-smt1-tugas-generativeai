import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.db.models.expressions import RawSQL
from pgvector.django import VectorField

from accounts.models import GEN_UUID, NOW

RAW_EMPTY_JSON = RawSQL("'[]'::jsonb", [])


class Assignment(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        db_default=GEN_UUID,
    )
    topic = models.ForeignKey(
        "academics.Topic",
        on_delete=models.CASCADE,
        related_name="assignments",
        db_constraint=False,
        db_index=False,
    )
    title = models.TextField()
    type = models.TextField()
    release_mode = models.TextField(db_default="review")
    due_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(db_default=NOW, editable=False)

    class Meta:
        db_table = "assignments"
        constraints = [
            models.CheckConstraint(
                condition=Q(type__in=("essay", "pg", "pdf", "docx")),
                name="assignments_type_check",
            ),
            models.CheckConstraint(
                condition=Q(release_mode__in=("review", "langsung")),
                name="assignments_release_mode_check",
            ),
        ]


class AssignmentQuestion(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        db_default=GEN_UUID,
    )
    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name="questions",
        db_constraint=False,
        db_index=False,
    )
    position = models.IntegerField(db_default=0)
    question = models.TextField()
    options = models.JSONField(null=True)
    answer_key = models.TextField(null=True)

    class Meta:
        db_table = "assignment_questions"
        constraints = [
            models.UniqueConstraint(
                fields=["assignment", "position"],
                name="assignment_questions_assignment_id_position_key",
            ),
        ]


class RubricCriterion(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        db_default=GEN_UUID,
    )
    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name="criteria",
        db_constraint=False,
        db_index=False,
    )
    position = models.IntegerField(db_default=0)
    name = models.TextField()
    weight = models.IntegerField()
    level_1 = models.TextField(db_default="")
    level_2 = models.TextField(db_default="")
    level_3 = models.TextField(db_default="")
    level_4 = models.TextField(db_default="")
    prompt_notes = models.TextField(db_default="")

    class Meta:
        db_table = "rubric_criteria"


class Submission(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        db_default=GEN_UUID,
    )
    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name="submissions",
        db_constraint=False,
        db_index=False,
    )
    student = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="submissions",
        db_constraint=False,
        db_index=False,
    )
    answer_text = models.TextField(null=True)
    answers = models.JSONField(default=list, db_default=RAW_EMPTY_JSON)
    file_name = models.TextField(null=True)
    extracted_text = models.TextField(null=True)
    extraction_ok = models.BooleanField(null=True)
    status = models.TextField(db_default="draft")
    submitted_at = models.DateTimeField(null=True)
    updated_at = models.DateTimeField(db_default=NOW, editable=False)

    class Meta:
        db_table = "submissions"
        constraints = [
            models.UniqueConstraint(
                fields=["assignment", "student"],
                name="submissions_assignment_id_student_id_key",
            ),
            models.CheckConstraint(
                condition=Q(status__in=("draft", "submitted", "needs_review")),
                name="submissions_status_check",
            ),
        ]


class DocumentChunk(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        db_default=GEN_UUID,
    )
    submission = models.ForeignKey(
        Submission,
        on_delete=models.CASCADE,
        related_name="chunks",
        db_constraint=False,
        db_index=False,
    )
    position = models.IntegerField()
    content = models.TextField()
    embedding = VectorField(dimensions=settings.EMBEDDING_DIM, null=True)

    class Meta:
        db_table = "document_chunks"
        # index document_chunks_submission_idx is created via RunSQL (31 chars,
        # over Django's 30-char index-name limit, but matches the original DDL)


class Grade(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        db_default=GEN_UUID,
    )
    submission = models.OneToOneField(
        Submission, on_delete=models.CASCADE, related_name="grade", db_constraint=False
    )
    state = models.TextField(db_default="draft")
    criteria = models.JSONField(default=list, db_default=RAW_EMPTY_JSON)
    feedback = models.TextField(db_default="")
    summary = models.TextField(db_default="")
    nilai = models.DecimalField(
        max_digits=5, decimal_places=2, db_default=Decimal("0")
    )
    predikat = models.TextField(db_default="D")
    source = models.TextField()
    created_by = models.ForeignKey(
        "accounts.User",
        null=True,
        on_delete=models.DO_NOTHING,
        related_name="+",
        db_column="created_by",
        db_constraint=False,
        db_index=False,
    )
    updated_by = models.ForeignKey(
        "accounts.User",
        null=True,
        on_delete=models.DO_NOTHING,
        related_name="+",
        db_column="updated_by",
        db_constraint=False,
        db_index=False,
    )
    published_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(db_default=NOW, editable=False)
    updated_at = models.DateTimeField(db_default=NOW, editable=False)

    class Meta:
        db_table = "grades"
        constraints = [
            models.CheckConstraint(
                condition=Q(state__in=("draft", "published")), name="grades_state_check"
            ),
            models.CheckConstraint(
                condition=Q(source__in=("model", "manual", "empty", "code")),
                name="grades_source_check",
            ),
        ]


class GradeRevision(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        db_default=GEN_UUID,
    )
    grade = models.ForeignKey(
        Grade, on_delete=models.CASCADE, related_name="revisions", db_constraint=False, db_index=False
    )
    snapshot = models.JSONField()
    nilai = models.DecimalField(max_digits=5, decimal_places=2)
    predikat = models.TextField()
    state = models.TextField()
    changed_by = models.ForeignKey(
        "accounts.User",
        null=True,
        on_delete=models.DO_NOTHING,
        related_name="+",
        db_column="changed_by",
        db_constraint=False,
        db_index=False,
    )
    changed_at = models.DateTimeField(db_default=NOW, editable=False)

    class Meta:
        db_table = "grade_revisions"
