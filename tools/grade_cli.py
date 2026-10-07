#!/usr/bin/env python3
"""CLI simulasi penilaian tugas.

Alur: tentukan tugas + rubrik (dan soal untuk PG), isi jawaban mahasiswa, lalu
uji penilaian dengan LLM, otomatis (PG), atau manual.

Jalankan dari root repositori:

    .venv/bin/python tools/grade_cli.py

Konfigurasi model LLM dibaca dari .env.local (LLM_BASE_URL, LLM_API_KEY,
LLM_MODEL_NAME). Tidak memerlukan PostgreSQL. Definisi disimpan in-memory
saja (hilang saat keluar).
"""

import math
import os
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nilai.settings")

import django  # noqa: E402

django.setup()

from assessment.ai import call_chat  # noqa: E402
from assessment.lib import (  # noqa: E402
    SYSTEM_PREAMBLE_DEFAULT,
    compute_nilai,
    predikat_of,
)
from assessment.prompt import build_messages  # noqa: E402
from assessment.validate import parse_model_response  # noqa: E402

TEMPERATURE = 0.2
MAX_TOKENS = 1200
LEVELS = ("level_1", "level_2", "level_3", "level_4")
LEVEL_LABELS = {
    "level_1": "Dangkal",
    "level_2": "Sebagian / tanpa penjelasan",
    "level_3": "Cukup jelas",
    "level_4": "Lengkap dan tepat",
}


def premis(title):
    print()
    print(title)
    print("-" * len(title))


def ask(label, default=""):
    suffix = f" [{default}]" if default else ""
    while True:
        raw = input(f"{label}{suffix}: ").strip()
        if raw:
            return raw
        if default:
            return default
        print("  ! Wajib diisi.")


def ask_int(label, lo, hi, default=None):
    while True:
        raw = input(f"{label}: ").strip()
        if not raw and default is not None:
            return default
        try:
            value = int(raw)
        except ValueError:
            print(f"  ! Masukkan bilangan bulat {lo}-{hi}.")
            continue
        if value < lo or value > hi:
            print(f"  ! Nilai harus antara {lo} dan {hi}.")
            continue
        return value


def ask_choice(label, choices, default=None):
    opts = "/".join(choices)
    suffix = f" [{default}]" if default else ""
    while True:
        raw = input(f"{label} ({opts}){suffix}: ").strip().lower()
        if not raw and default:
            return default
        if raw in choices:
            return raw
        print(f"  ! Pilih salah satu: {opts}.")


def ask_level(score, name):
    raw = input(f"Deskripsi skor {score} - {name} (kosongkan = '{name}'): ").strip()
    return raw or name


def new_state():
    return {
        "assignment": {"title": "", "type": "", "instructions": ""},
        "rubric": [],
        "questions": [],
        "answer": None,
    }


def has_assignment(state):
    return bool(state["assignment"]["title"])


# ---------------------------------------------------------------------------
# Definisi tugas, rubrik, dan soal
# ---------------------------------------------------------------------------


def setup_assignment(state):
    premis("Tentukan tugas")
    state["assignment"]["title"] = ask("Judul tugas")
    state["assignment"]["type"] = ask_choice("Tipe tugas", ("essay", "pg"))
    state["assignment"]["instructions"] = ask(
        "Instruksi/pertanyaan untuk mahasiswa", default="Kerjakan tugas berikut."
    )
    print("  Tugas disimpan.")


def setup_rubric(state):
    premis("Tentukan rubrik (total bobot sebaiknya 100)")
    rubric = []
    while True:
        print(f"\nKriteria #{len(rubric) + 1}")
        rubric.append(
            {
                "id": str(uuid.uuid4()),
                "name": ask("Nama kriteria"),
                "weight": ask_int("Bobot (1-100)", 1, 100),
                "level_1": ask_level(1, LEVEL_LABELS["level_1"]),
                "level_2": ask_level(2, LEVEL_LABELS["level_2"]),
                "level_3": ask_level(3, LEVEL_LABELS["level_3"]),
                "level_4": ask_level(4, LEVEL_LABELS["level_4"]),
                "prompt_notes": ask("Catatan penilaian (opsional)", default="-"),
            }
        )
        print(f"  Total bobot saat ini: {sum(c['weight'] for c in rubric)}")
        if ask_choice("Tambah kriteria lagi?", ("y", "n"), default="n") == "n":
            break
    state["rubric"] = rubric
    total = sum(c["weight"] for c in rubric)
    if total != 100:
        print(f"  ! Total bobot {total}, seharusnya 100. Skala nilai tetap memakai bobot ini.")
    else:
        print("  Rubrik disimpan (total bobot 100).")


def setup_questions(state):
    premis("Tentukan soal pilihan ganda")
    questions = []
    while True:
        print(f"\nSoal #{len(questions) + 1}")
        questions.append(
            {"question": ask("Pertanyaan"), "answer_key": ask("Kunci jawaban")}
        )
        if ask_choice("Tambah soal lagi?", ("y", "n"), default="n") == "n":
            break
    state["questions"] = questions
    print(f"  {len(questions)} soal disimpan.")


# ---------------------------------------------------------------------------
# Jawaban mahasiswa
# ---------------------------------------------------------------------------


def answer_essay(state):
    premis("Isi jawaban mahasiswa (essay)")
    state["answer"] = {"kind": "essay", "text": ask("Jawaban")}
    print("  Jawaban disimpan.")


def answer_pg(state):
    if not state["questions"]:
        print("  ! Belum ada soal. Tentukan soal dulu (menu 3).")
        return
    premis("Isi jawaban mahasiswa (PG)")
    choices = []
    for i, q in enumerate(state["questions"], 1):
        print(f"{i}. {q['question']}")
        choices.append(ask("   Jawaban"))
    state["answer"] = {"kind": "pg", "choices": choices}
    print("  Jawaban disimpan.")


# ---------------------------------------------------------------------------
# Penilaian
# ---------------------------------------------------------------------------


def llm_settings():
    return SimpleNamespace(
        base_url=(os.environ.get("LLM_BASE_URL") or "").strip(),
        api_key=(os.environ.get("LLM_API_KEY") or "").strip(),
        model_name=(os.environ.get("LLM_MODEL_NAME") or "").strip(),
    )


def model_configured(settings):
    return bool(settings.api_key and settings.base_url and settings.model_name)


def show_result(criteria, nilai, predikat, feedback="", summary=""):
    print()
    print(f"NILAI    : {nilai}")
    print(f"PREDIKAT : {predikat}")
    if criteria:
        print("Kriteria :")
        for c in criteria:
            print(f"  - {c['name']} (bobot {c['weight']}): skor {c['score']}")
            if c.get("quote"):
                print(f"      kutipan : {c['quote']}")
            if c.get("comment"):
                print(f"      komentar: {c['comment']}")
    if feedback:
        print(f"Feedback : {feedback}")
    if summary:
        print(f"Summary  : {summary}")


def grade_llm(state):
    if not has_assignment(state):
        print("  ! Tentukan tugas dulu (menu 1).")
        return
    if state["assignment"]["type"] != "essay":
        print("  ! Penilaian LLM hanya untuk tugas essay.")
        return
    if not state["rubric"]:
        print("  ! Rubrik belum diisi (menu 2).")
        return
    if not state["answer"] or state["answer"].get("kind") != "essay":
        print("  ! Isi jawaban mahasiswa dulu (menu 4).")
        return

    settings = llm_settings()
    if not model_configured(settings):
        print("  ! Model belum disetel (LLM_BASE_URL/LLM_API_KEY/LLM_MODEL_NAME di .env.local).")
        return

    premis("Uji penilaian dengan LLM")
    print(f"  Model: {settings.model_name} @ {settings.base_url}")
    messages = build_messages(
        preamble=SYSTEM_PREAMBLE_DEFAULT,
        question=state["assignment"]["instructions"],
        answer={"kind": "text", "text": state["answer"]["text"]},
        rubric=state["rubric"],
    )
    print("  Memanggil model...")
    result = call_chat(settings, messages, temperature=TEMPERATURE, max_tokens=MAX_TOKENS)
    if not result["ok"]:
        print(f"  ! Gagal memanggil model: {result['message']}")
        return

    parsed = parse_model_response(result["content"], state["rubric"])
    if not parsed["ok"]:
        print("  ! Respons model tidak valid:")
        for err in parsed["errors"]:
            print(f"    - {err}")
        return

    by_id = {c["id"]: c for c in state["rubric"]}
    criteria = []
    for entry in parsed["data"]["criteria"]:
        c = by_id.get(entry["id"])
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
    show_result(
        criteria,
        nilai,
        predikat_of(nilai),
        parsed["data"]["feedback"],
        parsed["data"]["summary"],
    )


def grade_pg(state):
    if state["assignment"].get("type") != "pg":
        print("  ! Penilaian otomatis hanya untuk tugas PG.")
        return
    if not state["questions"]:
        print("  ! Belum ada soal (menu 3).")
        return
    if not state["answer"] or state["answer"].get("kind") != "pg":
        print("  ! Isi jawaban mahasiswa dulu (menu 4).")
        return

    premis("Penilaian otomatis (PG)")
    questions = state["questions"]
    choices = state["answer"]["choices"]
    total = len(questions)
    correct = sum(
        1
        for i, q in enumerate(questions)
        if q["answer_key"] and i < len(choices) and choices[i] == q["answer_key"]
    )
    nilai = 0 if total == 0 else math.floor((correct / total) * 10000 + 0.5) / 100
    for i, q in enumerate(questions, 1):
        got = choices[i - 1] if i - 1 < len(choices) else ""
        mark = "benar" if q["answer_key"] and got == q["answer_key"] else "salah"
        print(f"  {i}. jawaban '{got}' (kunci '{q['answer_key']}') -> {mark}")
    show_result([], nilai, predikat_of(nilai), f"{correct} dari {total} jawaban benar.")


def grade_manual(state):
    if not state["rubric"]:
        print("  ! Rubrik belum diisi (menu 2).")
        return
    premis("Penilaian manual")
    criteria = []
    for c in state["rubric"]:
        print(f"\n{c['name']} (bobot {c['weight']})")
        for score, lv in enumerate(LEVELS, 1):
            print(f"  {score} - {LEVEL_LABELS[lv]}: {c[lv]}")
        criteria.append(
            {
                "criterion_id": c["id"],
                "name": c["name"],
                "weight": c["weight"],
                "score": ask_int("Skor (1-4)", 1, 4),
                "quote": "",
                "comment": ask("Komentar (opsional)", default="-"),
            }
        )
    feedback = ask("Feedback untuk mahasiswa", default="-")
    nilai = compute_nilai(criteria)
    show_result(criteria, nilai, predikat_of(nilai), feedback)


# ---------------------------------------------------------------------------
# Tampilan & menu
# ---------------------------------------------------------------------------


def show_definition(state):
    premis("Definisi tugas")
    a = state["assignment"]
    if not a["title"]:
        print("  (belum ada tugas)")
    else:
        print(f"  Judul     : {a['title']}")
        print(f"  Tipe      : {a['type']}")
        print(f"  Instruksi : {a['instructions']}")
    if state["rubric"]:
        print("\n  Rubrik:")
        for c in state["rubric"]:
            print(f"    - {c['name']} (bobot {c['weight']})")
        print(f"    Total bobot: {sum(c['weight'] for c in state['rubric'])}")
    if state["questions"]:
        print("\n  Soal:")
        for i, q in enumerate(state["questions"], 1):
            print(f"    {i}. {q['question']} (kunci: {q['answer_key']})")


def main_menu(state):
    print()
    print("=== MENU ===")
    print("1. Tentukan tugas")
    print("2. Tentukan rubrik")
    print("3. Tentukan soal (PG)")
    print("4. Isi jawaban mahasiswa")
    print("5. Uji penilaian dengan LLM")
    print("6. Penilaian otomatis (PG)")
    print("7. Penilaian manual")
    print("8. Lihat definisi")
    print("9. Reset definisi")
    print("0. Keluar")


def main():
    print("=" * 52)
    print(" CLI Simulasi Penilaian Tugas - Nilai")
    print("=" * 52)
    state = new_state()

    while True:
        main_menu(state)
        choice = input("Pilih menu: ").strip()

        if choice == "1":
            setup_assignment(state)
        elif choice == "2":
            setup_rubric(state)
        elif choice == "3":
            setup_questions(state)
        elif choice == "4":
            if state["assignment"].get("type") == "pg":
                answer_pg(state)
            else:
                answer_essay(state)
        elif choice == "5":
            grade_llm(state)
        elif choice == "6":
            grade_pg(state)
        elif choice == "7":
            grade_manual(state)
        elif choice == "8":
            show_definition(state)
        elif choice == "9":
            state = new_state()
            print("  Definisi direset.")
        elif choice == "0":
            print("Selesai.")
            break
        else:
            print("  ! Pilihan tidak dikenal.")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nKeluar.")
