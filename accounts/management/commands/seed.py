"""Port of src/db/seed.ts: idempotent demo data with fixed UUIDs."""

import os
import uuid
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import AppSettings, ModelSettings, User
from academics.models import (
    Course,
    CourseLecturer,
    Enrollment,
    MateriBlock,
    Period,
    Topic,
)
from assessment.models import (
    Assignment,
    AssignmentQuestion,
    Grade,
    GradeRevision,
    RubricCriterion,
    Submission,
)

DEFAULT_PASSWORD = "password123"

U = {
    "admin": uuid.UUID("a1000000-0000-4000-8000-000000000001"),
    "ramadan": uuid.UUID("a1000000-0000-4000-8000-000000000002"),
    "aldy": uuid.UUID("a1000000-0000-4000-8000-000000000011"),
    "miratil": uuid.UUID("a1000000-0000-4000-8000-000000000012"),
    "ismail": uuid.UUID("a1000000-0000-4000-8000-000000000013"),
    "fitri": uuid.UUID("a1000000-0000-4000-8000-000000000014"),
}
P = {
    "ganjil": uuid.UUID("b2000000-0000-4000-8000-000000000001"),
    "genap": uuid.UUID("b2000000-0000-4000-8000-000000000002"),
}
C = {
    "bd": uuid.UUID("b1000000-0000-4000-8000-000000000001"),
    "web": uuid.UUID("b1000000-0000-4000-8000-000000000002"),
    "bd_b": uuid.UUID("b1000000-0000-4000-8000-000000000003"),
}
T = {
    "bd1": uuid.UUID("c1000000-0000-4000-8000-000000000001"),
    "bd2": uuid.UUID("c1000000-0000-4000-8000-000000000002"),
    "bd3": uuid.UUID("c1000000-0000-4000-8000-000000000003"),
    "web1": uuid.UUID("c1000000-0000-4000-8000-000000000004"),
    "web2": uuid.UUID("c1000000-0000-4000-8000-000000000005"),
}
A = {
    "essay": uuid.UUID("d1000000-0000-4000-8000-000000000001"),
    "pg": uuid.UUID("d1000000-0000-4000-8000-000000000002"),
    "pdf": uuid.UUID("d1000000-0000-4000-8000-000000000003"),
    "docx": uuid.UUID("d1000000-0000-4000-8000-000000000004"),
}
CR = {
    "c1": uuid.UUID("e1000000-0000-4000-8000-000000000001"),
    "c2": uuid.UUID("e1000000-0000-4000-8000-000000000002"),
    "c3": uuid.UUID("e1000000-0000-4000-8000-000000000003"),
    "c4": uuid.UUID("e1000000-0000-4000-8000-000000000004"),
}
S = {
    "aldy": uuid.UUID("f1000000-0000-4000-8000-000000000001"),
    "miratil": uuid.UUID("f1000000-0000-4000-8000-000000000002"),
    "ismail": uuid.UUID("f1000000-0000-4000-8000-000000000003"),
    "fitri": uuid.UUID("f1000000-0000-4000-8000-000000000004"),
}
G = {
    "aldy": uuid.UUID("a0000000-0000-4000-8000-000000000001"),
    "ismail": uuid.UUID("a0000000-0000-4000-8000-000000000002"),
}

RUBRIC = [
    {
        "name": "Ketepatan konsep",
        "weight": 25,
        "level_1": "Menyebut istilah tanpa penjelasan.",
        "level_2": "Definisi tidak lengkap, ada kesalahan kecil.",
        "level_3": "Definisi benar dan lengkap sebagian besar.",
        "level_4": "Definisi tepat dan konsisten sepanjang jawaban.",
        "prompt_notes": "Abaikan salah ketik asal makna tetap jelas.",
    },
    {
        "name": "Kelengkapan",
        "weight": 25,
        "level_1": "Hanya satu poin yang disebut.",
        "level_2": "Dua dari tiga poin utama ada.",
        "level_3": "Semua poin ada, satu belum dikembangkan.",
        "level_4": "Semua poin ada dan dikembangkan.",
        "prompt_notes": "Wajib menyebut ketiga poin yang ditanyakan.",
    },
    {
        "name": "Struktur argumen",
        "weight": 25,
        "level_1": "Tidak ada urutan logis.",
        "level_2": "Urutan terlihat tetapi lompat-lompat.",
        "level_3": "Terstruktur dengan pembuka dan penutup.",
        "level_4": "Terstruktur rapi, setiap poin didukung alasan.",
        "prompt_notes": "Jangan menilai gaya bahasa, hanya urutan.",
    },
    {
        "name": "Contoh penerapan",
        "weight": 25,
        "level_1": "Tanpa contoh.",
        "level_2": "Contoh disebut tanpa penjelasan.",
        "level_3": "Contoh benar, penjelasan singkat.",
        "level_4": "Contoh konkret dan dihubungkan ke teori.",
        "prompt_notes": "Contoh hipotetis diperbolehkan.",
    },
]

ALDY_ANSWER = (
    "Normalisasi adalah proses menyusun tabel agar redundansi data berkurang. "
    "Bentuk pertama (1NF) menghilangkan nilai ganda sehingga setiap sel berisi "
    "satu nilai. Bentuk kedua (2NF) menghilangkan ketergantungan parsial dengan "
    "memindahkan atribut yang hanya bergantung pada sebagian kunci ke tabel lain. "
    "Bentuk ketiga (3NF) menghilangkan ketergantungan transitif. Contohnya, tabel "
    "transaksi yang menyimpan nama pelanggan sebaiknya dipisah ke tabel pelanggan "
    "agar perubahan nama cukup diubah di satu tempat."
)

MIRATIL_ANSWER = (
    "Normalisasi dipakai supaya data tidak dobel. Kalau tabelnya banyak maka "
    "query jadi lambat, jadi dibuat terpisah menurut kebutuhan."
)

FITRI_TEXT = (
    "Laporan analisis basis data akademik. Tabel mahasiswa menyimpan nim, nama, "
    "dan email. Tabel kelas menyimpan id_kelas, kode_matakuliah, dan dosen. "
    "Ditemukan redundansi penyimpanan nama dosen pada setiap baris kelas. "
    "Rekomendasi: pindahkan data dosen ke tabel dosen dan hubungkan dengan kunci asing."
)


class Command(BaseCommand):
    help = "Seed demo data if the users table is empty (port of src/db/seed.ts)"

    @transaction.atomic
    def handle(self, *args, **options):
        AppSettings.objects.get_or_create(id=1)
        if User.objects.exists():
            self.stdout.write("Seed skipped: users already exist.")
            return

        users = [
            (U["admin"], "Nur Audyah Ramadhani", "audyah@nilai.test", "admin"),
            (U["ramadan"], "Ramadan Agung Wibawa", "ramadan@nilai.test", "lecturer"),
            (U["aldy"], "Aldy", "aldy@nilai.test", "student"),
            (U["miratil"], "Mir'atil Hayati", "miratil@nilai.test", "student"),
            (U["ismail"], "Ismail Saputra", "ismail@nilai.test", "student"),
            (U["fitri"], "Fitri Lestari", "fitri@nilai.test", "student"),
        ]
        for uid, name, email, role in users:
            user = User(id=uid, name=name, email=email, role=role)
            user.set_password(DEFAULT_PASSWORD)
            user.save()

        Period.objects.create(id=P["ganjil"], name="2025/2026 Ganjil", is_active=True)
        Period.objects.create(id=P["genap"], name="2025/2026 Genap", is_active=False)

        Course.objects.create(
            id=C["bd"], code="IF201", name="Basis Data", semester=4, sks=3,
            period_id=P["ganjil"], section="A",
        )
        Course.objects.create(
            id=C["web"], code="IF315", name="Pembangunan Aplikasi Web", semester=6, sks=3,
            period_id=P["ganjil"], section="A",
        )
        Course.objects.create(
            id=C["bd_b"], code="IF201", name="Basis Data", semester=4, sks=3,
            period_id=P["ganjil"], section="B",
        )

        for course_id in (C["bd"], C["web"]):
            CourseLecturer.objects.create(course_id=course_id, user_id=U["ramadan"])

        for student_id in (U["aldy"], U["miratil"], U["ismail"], U["fitri"]):
            for course_id in (C["bd"], C["web"]):
                Enrollment.objects.create(course_id=course_id, student_id=student_id)

        topics = [
            (T["bd1"], C["bd"], 1, "Relasi dan model data"),
            (T["bd2"], C["bd"], 2, "Normalisasi"),
            (T["bd3"], C["bd"], 3, "Kueri SQL"),
            (T["web1"], C["web"], 1, "Arsitektur aplikasi web"),
            (T["web2"], C["web"], 2, "Server components dan data"),
        ]
        for tid, cid, week, title in topics:
            Topic.objects.create(id=tid, course_id=cid, week=week, title=title)

        materi = [
            (T["bd1"], "richtext", "Baca materi model data relasional: entitas, atribut, kunci primer, dan kunci asing. Catat satu pertanyaan sebelum pertemuan.", None, None),
            (T["bd1"], "link", "Dokumentasi PostgreSQL — tutorial pemula", "https://www.postgresql.org/docs/current/tutorial-start.html", None),
            (T["bd1"], "file", None, None, "materi-pertemuan-1.pdf"),
            (T["bd2"], "richtext", "Normalisasi dari 1NF sampai 3NF. Kerjakan latihan normalisasi pada lembar kerja sebelum pertemuan.", None, None),
            (T["bd2"], "file", None, None, "lembar-normalisasi.docx"),
            (T["bd3"], "richtext", "SELECT, JOIN, dan subkueri. Latihan soal memakai basis data contoh kampus.", None, None),
            (T["web1"], "richtext", "Arsitektur aplikasi web: client, server, dan keputusan rendering.", None, None),
            (T["web1"], "link", "Dokumentasi Next.js — App Router", "https://nextjs.org/docs/app", None),
            (T["web2"], "richtext", "Server components, fetching data di server, dan batas antara klien serta server.", None, None),
            (T["web2"], "file", None, None, "materi-server-components.pdf"),
        ]
        position = 0
        last_topic = None
        for topic_id, mtype, body, url, file_name in materi:
            if topic_id != last_topic:
                position = 0
                last_topic = topic_id
            MateriBlock.objects.create(
                topic_id=topic_id, type=mtype, body=body, url=url,
                file_name=file_name, position=position,
            )
            position += 1

        now = timezone.now()
        Assignment.objects.create(
            id=A["essay"], topic_id=T["bd2"], title="Esai: bentuk normalisasi",
            type="essay", release_mode="review", due_at=now + timedelta(days=2),
        )
        Assignment.objects.create(
            id=A["pg"], topic_id=T["bd3"], title="Pilihan ganda: kueri JOIN",
            type="pg", release_mode="review", due_at=now + timedelta(days=4),
        )
        Assignment.objects.create(
            id=A["pdf"], topic_id=T["web2"], title="Unggah laporan analisis (PDF)",
            type="pdf", release_mode="review", due_at=now + timedelta(days=6),
        )
        Assignment.objects.create(
            id=A["docx"], topic_id=T["web1"], title="Unggah rancangan skema (DOCX)",
            type="docx", release_mode="langsung", due_at=now + timedelta(days=9),
        )

        AssignmentQuestion.objects.create(
            assignment_id=A["essay"], position=0,
            question="Jelaskan bentuk normalisasi 1NF, 2NF, dan 3NF beserta satu contoh penerapan pada basis data kampus.",
        )
        AssignmentQuestion.objects.create(
            assignment_id=A["pg"], position=0,
            question="Klausa yang digunakan untuk menggabungkan dua tabel berdasarkan kunci adalah ...",
            options=[
                {"key": "A", "text": "UNION"},
                {"key": "B", "text": "JOIN"},
                {"key": "C", "text": "GROUP BY"},
                {"key": "D", "text": "HAVING"},
            ],
            answer_key="B",
        )
        AssignmentQuestion.objects.create(
            assignment_id=A["pg"], position=1,
            question="Klausa yang menggabungkan hasil dua pernyataan SELECT dan menghilangkan baris duplikat adalah ...",
            options=[
                {"key": "A", "text": "UNION"},
                {"key": "B", "text": "INTERSECT"},
                {"key": "C", "text": "EXCEPT"},
                {"key": "D", "text": "ORDER BY"},
            ],
            answer_key="A",
        )
        AssignmentQuestion.objects.create(
            assignment_id=A["pg"], position=2,
            question="Fungsi agregat yang menghitung jumlah baris pada hasil kueri adalah ...",
            options=[
                {"key": "A", "text": "SUM"},
                {"key": "B", "text": "AVG"},
                {"key": "C", "text": "COUNT"},
                {"key": "D", "text": "MAX"},
            ],
            answer_key="C",
        )
        AssignmentQuestion.objects.create(
            assignment_id=A["pdf"], position=0,
            question="Unggah laporan analisis basis data dalam PDF: identifikasi tabel, kolom, dan rekomendasi normalisasi.",
        )
        AssignmentQuestion.objects.create(
            assignment_id=A["docx"], position=0,
            question="Unggah rancangan skema basis data aplikasi dalam DOCX berisi daftar tabel dan relasi.",
        )

        for assignment_id, fixed_ids in (
            (A["essay"], [CR["c1"], CR["c2"], CR["c3"], CR["c4"]]),
            (A["pdf"], None),
            (A["docx"], None),
        ):
            for i, r in enumerate(RUBRIC):
                kwargs = {"assignment_id": assignment_id, "position": i, **r}
                if fixed_ids:
                    kwargs["id"] = fixed_ids[i]
                RubricCriterion.objects.create(**kwargs)

        Submission.objects.create(
            id=S["aldy"], assignment_id=A["essay"], student_id=U["aldy"],
            answer_text=ALDY_ANSWER, status="submitted",
            submitted_at=now - timedelta(days=3), updated_at=now - timedelta(days=3),
        )
        Submission.objects.create(
            id=S["miratil"], assignment_id=A["essay"], student_id=U["miratil"],
            answer_text=MIRATIL_ANSWER, status="submitted",
            submitted_at=now - timedelta(days=1), updated_at=now - timedelta(days=1),
        )
        Submission.objects.create(
            id=S["ismail"], assignment_id=A["pg"], student_id=U["ismail"],
            answers=["B", "A", "C"], status="submitted",
            submitted_at=now - timedelta(days=2), updated_at=now - timedelta(days=2),
        )
        Submission.objects.create(
            id=S["fitri"], assignment_id=A["pdf"], student_id=U["fitri"],
            file_name="laporan-analisis.pdf", extracted_text=FITRI_TEXT,
            extraction_ok=True, status="submitted",
            submitted_at=now - timedelta(days=1), updated_at=now - timedelta(days=1),
        )

        aldy_criteria = [
            {
                "criterion_id": str(CR["c1"]),
                "name": "Ketepatan konsep",
                "weight": 25,
                "score": 3,
                "quote": "Normalisasi adalah proses menyusun tabel agar redundansi data berkurang.",
                "comment": "Definisi benar tetapi belum menyebut tujuan pengurangan redundansi secara eksplisit.",
            },
            {
                "criterion_id": str(CR["c2"]),
                "name": "Kelengkapan",
                "weight": 25,
                "score": 4,
                "quote": "Bentuk kedua (2NF) menghilangkan ketergantungan parsial dengan memindahkan atribut yang hanya bergantung pada sebagian kunci ke tabel lain.",
                "comment": "Ketiga bentuk normalisasi dijelaskan lengkap.",
            },
            {
                "criterion_id": str(CR["c3"]),
                "name": "Struktur argumen",
                "weight": 25,
                "score": 3,
                "quote": "Bentuk pertama (1NF) menghilangkan nilai ganda sehingga setiap sel berisi satu nilai.",
                "comment": "Urutan jelas dari 1NF ke 3NF, penutupnya masih singkat.",
            },
            {
                "criterion_id": str(CR["c4"]),
                "name": "Contoh penerapan",
                "weight": 25,
                "score": 4,
                "quote": "tabel transaksi yang menyimpan nama pelanggan sebaiknya dipisah ke tabel pelanggan",
                "comment": "Contoh konkret dan dihubungkan dengan perubahan data.",
            },
        ]
        aldy_feedback = (
            "Tulis juga tujuan normalisasi di pembuka, bukan hanya definisinya. "
            "Satu contoh kasus kampus akan memperkuat jawaban Anda."
        )
        aldy_summary = (
            "Jawaban lengkap mencakup ketiga bentuk dengan contoh tepat. "
            "Perlu memperjelas tujuan di bagian pembuka."
        )
        Grade.objects.create(
            id=G["aldy"], submission_id=S["aldy"], state="published",
            criteria=aldy_criteria, feedback=aldy_feedback, summary=aldy_summary,
            nilai=Decimal("87.50"), predikat="A", source="model",
            created_by_id=U["ramadan"], updated_by_id=U["ramadan"],
            published_at=now - timedelta(days=3),
            created_at=now - timedelta(days=3), updated_at=now - timedelta(days=3),
        )
        GradeRevision.objects.create(
            grade_id=G["aldy"],
            snapshot={"criteria": aldy_criteria, "feedback": aldy_feedback, "summary": aldy_summary},
            nilai=Decimal("87.50"), predikat="A", state="published",
            changed_by_id=U["ramadan"], changed_at=now - timedelta(days=3),
        )

        ismail_feedback = "3 dari 3 jawaban benar."
        ismail_summary = "Dinilai otomatis dari kunci jawaban, tanpa model."
        Grade.objects.create(
            id=G["ismail"], submission_id=S["ismail"], state="draft",
            criteria=[], feedback=ismail_feedback, summary=ismail_summary,
            nilai=Decimal("100.00"), predikat="A", source="code",
        )
        GradeRevision.objects.create(
            grade_id=G["ismail"],
            snapshot={"criteria": [], "feedback": ismail_feedback, "summary": ismail_summary},
            nilai=Decimal("100.00"), predikat="A", state="draft",
        )

        ModelSettings.objects.get_or_create(
            id=1,
            defaults={
                "provider_label": os.environ.get("LLM_PROVIDER_LABEL", "").strip() or "Penyedia utama",
                "base_url": os.environ.get("LLM_BASE_URL", "").strip(),
                "api_key": os.environ.get("LLM_API_KEY", "").strip(),
                "model_name": os.environ.get("LLM_MODEL_NAME", "").strip(),
                "emb_base_url": os.environ.get("EMB_BASE_URL", "").strip(),
                "emb_api_key": os.environ.get("EMB_API_KEY", "").strip(),
                "emb_model_name": os.environ.get("EMB_MODEL_NAME", "").strip(),
                "system_preamble": "Anda adalah asisten penilaian mata kuliah. Balas dalam bahasa Indonesia yang singkat dan jelas.",
                "temperature": Decimal("0.20"),
                "max_tokens": 1200,
            },
        )

        self.stdout.write(self.style.SUCCESS("Seeded demo data."))
