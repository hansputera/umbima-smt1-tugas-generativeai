import uuid
from decimal import Decimal

from django.contrib.auth.hashers import make_password, check_password
from django.db import models
from django.db.models import Q
from django.db.models.expressions import RawSQL
from django.utils.crypto import salted_hmac

NOW = RawSQL("now()", [])
GEN_UUID = RawSQL("gen_random_uuid()", [])


class User(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        db_default=GEN_UUID,
    )
    name = models.TextField()
    email = models.TextField()
    password = models.TextField(db_column="password_hash", null=True)
    role = models.TextField()
    status = models.TextField(db_default="active")
    created_at = models.DateTimeField(db_default=NOW, editable=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    is_anonymous = False

    class Meta:
        db_table = "users"
        constraints = [
            models.UniqueConstraint(fields=["email"], name="users_email_key"),
            models.CheckConstraint(
                condition=Q(role__in=("admin", "lecturer", "student")),
                name="users_role_check",
            ),
            models.CheckConstraint(
                condition=Q(status__in=("active", "inactive")),
                name="users_status_check",
            ),
        ]

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return self.status == "active"

    def get_username(self):
        return self.email

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def get_session_auth_hash(self):
        return salted_hmac(
            "accounts.User.get_session_auth_hash", self.password or ""
        ).hexdigest()

    def __str__(self):
        return f"{self.name} <{self.email}>"


class ModelSettings(models.Model):
    id = models.IntegerField(primary_key=True)
    provider_label = models.TextField(db_default="")
    base_url = models.TextField(db_default="")
    api_key = models.TextField(db_default="")
    model_name = models.TextField(db_default="")
    temperature = models.DecimalField(
        max_digits=3, decimal_places=2, db_default=Decimal("0.20")
    )
    max_tokens = models.IntegerField(db_default=1200)
    system_preamble = models.TextField(db_default="")
    emb_base_url = models.TextField(db_default="")
    emb_api_key = models.TextField(db_default="")
    emb_model_name = models.TextField(db_default="")
    updated_at = models.DateTimeField(null=True)
    updated_by = models.ForeignKey(
        User,
        null=True,
        on_delete=models.DO_NOTHING,
        related_name="+",
        db_column="updated_by",
        db_constraint=False,
        db_index=False,
    )

    class Meta:
        db_table = "model_settings"
        constraints = [
            models.CheckConstraint(condition=Q(id=1), name="model_settings_id_check"),
        ]


class AppSettings(models.Model):
    id = models.IntegerField(primary_key=True)
    app_name = models.TextField(db_default="MiniCourse")
    footer_text = models.TextField(db_default="")
    logo = models.BinaryField(null=True)
    logo_type = models.TextField(null=True)
    logo_version = models.IntegerField(db_default=0)
    updated_at = models.DateTimeField(null=True)
    updated_by = models.ForeignKey(
        User,
        null=True,
        on_delete=models.DO_NOTHING,
        related_name="+",
        db_column="updated_by",
        db_constraint=False,
        db_index=False,
    )

    class Meta:
        db_table = "app_settings"
        constraints = [
            models.CheckConstraint(condition=Q(id=1), name="app_settings_id_check"),
        ]
