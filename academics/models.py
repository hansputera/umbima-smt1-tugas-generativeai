import uuid

from django.db import models
from django.db.models import Q

from accounts.models import NOW, GEN_UUID


class Period(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        db_default=GEN_UUID,
    )
    name = models.TextField()
    is_active = models.BooleanField(db_default=False)
    created_at = models.DateTimeField(db_default=NOW, editable=False)

    class Meta:
        db_table = "periods"
        constraints = [
            models.UniqueConstraint(fields=["name"], name="periods_name_key"),
        ]

    def __str__(self):
        return self.name


class Course(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        db_default=GEN_UUID,
    )
    code = models.TextField()
    name = models.TextField()
    semester = models.IntegerField()
    sks = models.IntegerField()
    period = models.ForeignKey(
        Period,
        on_delete=models.DO_NOTHING,
        related_name="courses",
        db_constraint=False,
        db_index=False,
    )
    section = models.TextField(db_default="A")
    archived_at = models.DateTimeField(null=True)

    class Meta:
        db_table = "courses"
        constraints = [
            models.UniqueConstraint(
                fields=["code", "period", "section"],
                name="courses_code_period_section_key",
            ),
        ]

    def __str__(self):
        return f"{self.code} {self.name}"


class CourseLecturer(models.Model):
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, primary_key=True, related_name="lecturers"
    )
    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="+"
    )

    class Meta:
        managed = False
        db_table = "course_lecturers"


class Enrollment(models.Model):
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, primary_key=True, related_name="enrolled"
    )
    student = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="+"
    )
    created_at = models.DateTimeField(db_default=NOW, editable=False)

    class Meta:
        managed = False
        db_table = "enrollments"


class Topic(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        db_default=GEN_UUID,
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="topics",
        db_constraint=False,
        db_index=False,
    )
    week = models.IntegerField()
    title = models.TextField()

    class Meta:
        db_table = "topics"
        constraints = [
            models.UniqueConstraint(
                fields=["course", "week"], name="topics_course_id_week_key"
            ),
        ]


class MateriBlock(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        db_default=GEN_UUID,
    )
    topic = models.ForeignKey(
        Topic,
        on_delete=models.CASCADE,
        related_name="blocks",
        db_constraint=False,
        db_index=False,
    )
    type = models.TextField()
    body = models.TextField(null=True)
    url = models.TextField(null=True)
    file_name = models.TextField(null=True)
    position = models.IntegerField(db_default=0)

    class Meta:
        db_table = "materi_blocks"
        constraints = [
            models.CheckConstraint(
                condition=Q(type__in=("richtext", "link", "file")),
                name="materi_blocks_type_check",
            ),
        ]
