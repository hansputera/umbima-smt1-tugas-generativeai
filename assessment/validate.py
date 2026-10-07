"""Port of src/lib/grading/validate.ts (model response extraction + validation)."""

import json
import math
import re

from .lib import number_value


def _safe_parse(text):
    try:
        json.loads(
            text,
            parse_constant=lambda name: (_ for _ in ()).throw(ValueError(name)),
        )
        return True
    except (ValueError, TypeError):
        return False


def _scan_from(s, start):
    """Port of scanFrom: brace-scan a balanced object starting at `start`."""
    if start < 0:
        return {"kind": "none"}
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(s)):
        ch = s[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return {"kind": "ok", "text": s[start : i + 1]}
    return {"kind": "truncated"}


def extract_json(content):
    """Port of extractJson: find a parseable JSON object in model output."""
    trimmed = content.strip()
    if _safe_parse(trimmed):
        return {"kind": "ok", "text": trimmed}

    for match in re.finditer(r"```(?:json)?\s*([\s\S]*?)```", trimmed, re.I):
        inner = match.group(1).strip()
        if _safe_parse(inner):
            return {"kind": "ok", "text": inner}
        scanned = _scan_from(inner, inner.find("{"))
        if scanned["kind"] == "ok" and _safe_parse(scanned["text"]):
            return {"kind": "ok", "text": scanned["text"]}

    idx = trimmed.find("{")
    while idx >= 0:
        scanned = _scan_from(trimmed, idx)
        if scanned["kind"] == "truncated":
            return {"kind": "truncated"}
        if scanned["kind"] == "ok" and _safe_parse(scanned["text"]):
            return {"kind": "ok", "text": scanned["text"]}
        idx = trimmed.find("{", idx + 1)
    return {"kind": "none"}


def _non_empty_trimmed(value):
    return isinstance(value, str) and value.strip() != ""


def _clean_score(value):
    """Port of the zod score preprocess (string numbers coerced)."""
    if isinstance(value, str) and value.strip() != "":
        n = number_value(value.strip())
        if not math.isnan(n):
            return n
        return value
    return value


def parse_model_response(content, rubric):
    """Port of parseModelResponse: validate + normalize the model payload."""
    extracted = extract_json(content)
    if extracted["kind"] == "truncated":
        return {
            "ok": False,
            "errors": [
                "Respons terpotong. Naikkan Max tokens pada Setelan model "
                "lalu ulangi penilaian."
            ],
        }
    if extracted["kind"] == "none":
        return {"ok": False, "errors": ["Balasan bukan JSON valid."]}

    try:
        parsed = json.loads(
            extracted["text"],
            parse_constant=lambda name: (_ for _ in ()).throw(ValueError(name)),
        )
    except (ValueError, TypeError):
        return {"ok": False, "errors": ["Balasan bukan JSON valid."]}

    if not isinstance(parsed, dict):
        return {"ok": False, "errors": ["Balasan bukan objek JSON."]}

    errors = []
    if not _non_empty_trimmed(parsed.get("feedback")):
        errors.append('Field "feedback" tidak ada atau kosong.')
    if not _non_empty_trimmed(parsed.get("summary")):
        errors.append('Field "summary" tidak ada atau kosong.')
    if not isinstance(parsed.get("criteria"), list):
        errors.append('Field "criteria" bukan array.')
        return {"ok": False, "errors": errors}

    by_id = {}
    for entry in parsed["criteria"]:
        eid = entry.get("id") if isinstance(entry, dict) else None
        if not isinstance(eid, str):
            errors.append("Ada kriteria tanpa id.")
            continue
        by_id.setdefault(eid, []).append(entry)

    rubric_ids = {c["id"] for c in rubric}
    seen_ids = set()
    clean = []

    for criterion in rubric:
        cid = criterion["id"]
        matches = by_id.get(cid, [])
        if len(matches) == 0:
            errors.append(f'Kriteria "{criterion["name"]}" tidak ada dalam balasan.')
            continue
        if len(matches) > 1:
            errors.append(f'Kriteria "{criterion["name"]}" muncul lebih dari sekali.')
            continue
        seen_ids.add(cid)

        entry = matches[0]
        entry_errors = []
        score = _clean_score(entry.get("score"))
        valid_score = (
            isinstance(score, (int, float))
            and not isinstance(score, bool)
            and float(score).is_integer()
            and 1 <= float(score) <= 4
        )
        if not valid_score:
            entry_errors.append("score")
        if not _non_empty_trimmed(entry.get("quote")):
            entry_errors.append("quote")
        if not _non_empty_trimmed(entry.get("comment")):
            entry_errors.append("comment")

        if entry_errors:
            for field in entry_errors:
                if field == "score":
                    errors.append(
                        f'Kriteria "{criterion["name"]}" punya score tidak valid '
                        "(harus integer 1-4)."
                    )
                elif field == "quote":
                    errors.append(f'Kriteria "{criterion["name"]}" tanpa kutipan.')
                else:
                    errors.append(f'Kriteria "{criterion["name"]}" tanpa komentar.')
            continue

        clean.append(
            {
                "id": cid,
                "score": int(float(score)),
                "quote": entry["quote"].strip(),
                "comment": entry["comment"].strip(),
            }
        )

    for eid in by_id:
        if eid not in rubric_ids:
            errors.append(f'Kriteria tidak dikenal dengan id "{eid}".')

    if errors:
        return {"ok": False, "errors": errors}

    return {
        "ok": True,
        "data": {
            "criteria": clean,
            "feedback": parsed["feedback"].strip(),
            "summary": parsed["summary"].strip(),
        },
    }
