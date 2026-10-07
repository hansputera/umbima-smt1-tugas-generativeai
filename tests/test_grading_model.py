"""Chunk C verification: prompt/validate/rag/ai + compute_grade model path (mocked LLM)."""
import json
import os
import sys
import threading
import uuid
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nilai.settings")

import django

django.setup()

from django.conf import settings as dj_settings  # noqa: E402
from django.test import Client  # noqa: E402
from django.utils import timezone  # noqa: E402

from accounts.models import ModelSettings, User  # noqa: E402
from academics.models import Topic  # noqa: E402
from assessment import rag as ragmod  # noqa: E402
from assessment import grading as G  # noqa: E402
from assessment.ai import call_chat, embed_call, test_connection  # noqa: E402
from assessment.models import (  # noqa: E402
    Assignment,
    DocumentChunk,
    Grade,
    GradeRevision,
    RubricCriterion,
    Submission,
)
from assessment.prompt import build_messages  # noqa: E402
from assessment.rag import chunk_text, ensure_chunks, retrieve_excerpts  # noqa: E402
from assessment.validate import parse_model_response  # noqa: E402

ok = 0
fail = []


def check(name, cond, extra=""):
    global ok
    if cond:
        ok += 1
    else:
        fail.append(f"{name} {extra}"[:300])


MIRATIL = "f1000000-0000-4000-8000-000000000002"
FITRI = "f1000000-0000-4000-8000-000000000004"
ESSAY = "d1000000-0000-4000-8000-000000000001"
PDF = "d1000000-0000-4000-8000-000000000003"
C_BDB = "b1000000-0000-4000-8000-000000000003"
CR = [
    "e1000000-0000-4000-8000-000000000001",
    "e1000000-0000-4000-8000-000000000002",
    "e1000000-0000-4000-8000-000000000003",
    "e1000000-0000-4000-8000-000000000004",
]
LECT = "a1000000-0000-4000-8000-000000000002"
STU_ISMAIL = "a1000000-0000-4000-8000-000000000013"
STU_ALDY = "a1000000-0000-4000-8000-000000000011"

# ===========================================================================
# 1. validate.parse_model_response
# ===========================================================================
RUB = [
    {"id": "r1", "name": "Alpha", "weight": 50},
    {"id": "r2", "name": "Beta", "weight": 50},
]
E1 = {"id": "r1", "score": 3, "quote": "kutip A", "comment": "ok A"}
E2 = {"id": "r2", "score": 4, "quote": "kutip B", "comment": "ok B"}


def ok_payload(criteria=None, feedback="Fb.", summary="Sm."):
    return {
        "criteria": criteria or [E1, E2],
        "feedback": feedback,
        "summary": summary,
    }


def parse(raw, rubric=None):
    return parse_model_response(raw, rubric or RUB)


r = parse(json.dumps(ok_payload()))
check("v plain ok", r["ok"], r.get("errors"))
check("v plain scores", r["ok"] and [c["score"] for c in r["data"]["criteria"]] == [3, 4])
check("v plain trim", r["ok"] and r["data"]["feedback"] == "Fb.")

rev = ok_payload([E2, E1])
r = parse(json.dumps(rev))
check("v rubric order", r["ok"] and [c["id"] for c in r["data"]["criteria"]] == ["r1", "r2"])

r = parse("```json\n" + json.dumps(ok_payload()) + "\n```")
check("v fence json", r["ok"], r.get("errors"))
r = parse("```\n" + json.dumps(ok_payload()) + "\n```")
check("v fence plain", r["ok"], r.get("errors"))
r = parse("Berikut hasilnya:\n" + json.dumps(ok_payload()) + "\nSemoga membantu.")
check("v prose", r["ok"], r.get("errors"))

r = parse('{"feedback": "x", "summary": "y", "criteria": [{"id": "r1"')
check(
    "v truncated",
    not r["ok"]
    and r["errors"]
    == [
        "Respons terpotong. Naikkan Max tokens pada Setelan model "
        "lalu ulangi penilaian."
    ],
    r,
)
r = parse("maaf saya tidak bisa menjawab")
check("v garbage", not r["ok"] and r["errors"] == ["Balasan bukan JSON valid."], r)
r = parse("[1, 2, 3]")
check("v array", not r["ok"] and r["errors"] == ["Balasan bukan objek JSON."], r)
r = parse('{"a": NaN}')
check("v nan", not r["ok"] and r["errors"] == ["Balasan bukan JSON valid."], r)
r = parse(json.dumps({"summary": "s", "criteria": [E1, E2]}))
check(
    "v no feedback",
    not r["ok"] and r["errors"] == ['Field "feedback" tidak ada atau kosong.'],
    r,
)
r = parse(json.dumps({"feedback": "f", "criteria": [E1, E2]}))
check(
    "v no summary",
    not r["ok"] and r["errors"] == ['Field "summary" tidak ada atau kosong.'],
    r,
)
r = parse(json.dumps({"feedback": "  ", "summary": "s", "criteria": [E1, E2]}))
check("v blank feedback", not r["ok"] and 'feedback' in r["errors"][0], r)
r = parse(json.dumps({"feedback": 12, "summary": "s", "criteria": [E1, E2]}))
check("v num feedback", not r["ok"] and r["errors"][0].startswith('Field "feedback"'), r)
r = parse(json.dumps({"feedback": "f", "summary": "s", "criteria": "x"}))
check(
    "v criteria not list",
    not r["ok"] and r["errors"] == ['Field "criteria" bukan array.'],
    r,
)
r = parse(json.dumps(ok_payload([E1])))
check(
    "v missing beta",
    not r["ok"] and r["errors"] == ['Kriteria "Beta" tidak ada dalam balasan.'],
    r,
)
r = parse(json.dumps(ok_payload([E1, E1, E2])))
check(
    "v duplicate",
    not r["ok"] and r["errors"] == ['Kriteria "Alpha" muncul lebih dari sekali.'],
    r,
)
bad = dict(E1, score=9)
r = parse(json.dumps(ok_payload([bad, E2])))
check(
    "v score 9",
    not r["ok"]
    and r["errors"]
    == ['Kriteria "Alpha" punya score tidak valid (harus integer 1-4).'],
    r,
)
bad = dict(E1, score="2")
r = parse(json.dumps(ok_payload([bad, E2])))
check("v score str", r["ok"] and r["data"]["criteria"][0]["score"] == 2, r)
bad = dict(E1, score=2.5)
r = parse(json.dumps(ok_payload([bad, E2])))
check("v score 2.5", not r["ok"] and "score" in r["errors"][0], r)
bad = dict(E1, score=0)
r = parse(json.dumps(ok_payload([bad, E2])))
check("v score 0", not r["ok"] and "score tidak valid" in r["errors"][0], r)
bad = dict(E1, score=5)
r = parse(json.dumps(ok_payload([bad, E2])))
check("v score 5", not r["ok"] and "score tidak valid" in r["errors"][0], r)
bad = dict(E1, quote="  ")
r = parse(json.dumps(ok_payload([bad, E2])))
check(
    "v empty quote",
    not r["ok"] and r["errors"] == ['Kriteria "Alpha" tanpa kutipan.'],
    r,
)
bad = dict(E1, comment=" ")
r = parse(json.dumps(ok_payload([bad, E2])))
check(
    "v empty comment",
    not r["ok"] and r["errors"] == ['Kriteria "Alpha" tanpa komentar.'],
    r,
)
r = parse(json.dumps(ok_payload([E1, E2, {"id": "x9", "score": 3, "quote": "q", "comment": "c"}])))
check(
    "v unknown id",
    not r["ok"] and r["errors"] == ['Kriteria tidak dikenal dengan id "x9".'],
    r,
)
r = parse(json.dumps(ok_payload([{"score": 3, "quote": "q", "comment": "c"}, E2])))
check("v no id", not r["ok"] and "Ada kriteria tanpa id." in r["errors"], r)
r = parse(json.dumps(ok_payload(feedback="  halo  ")))
check("v feedback trim", r["ok"] and r["data"]["feedback"] == "halo", r)

# ===========================================================================
# 2. prompt.build_messages
# ===========================================================================
PREAMBLE = "Anda adalah asisten penilaian."
full_rub = G.get_rubric(ESSAY)
msgs = build_messages(
    preamble=PREAMBLE,
    question="Q1\nQ2",
    answer={"kind": "text", "text": "jawaban mahasiswa"},
    rubric=full_rub,
)
check("p count", len(msgs) == 2)
check("p roles", msgs[0]["role"] == "system" and msgs[1]["role"] == "user")
sys_c = msgs[0]["content"]
check("p preamble", sys_c.startswith(PREAMBLE + "\n\n"))
check("p rules head", "\nAturan penilaian:\n" in sys_c)
check(
    "p rule json",
    "- Balas HANYA dengan satu objek JSON valid. Tanpa markdown, tanpa blok kode, "
    "tanpa teks lain sebelum atau sesudahnya." in sys_c,
)
check(
    "p rule tail",
    sys_c.endswith("- Jangan sertakan nilai akhir maupun predikat. "
                   "Server yang menghitung keduanya."),
)
up = json.loads(msgs[1]["content"])
check("p user keys", set(up) == {"pertanyaan", "rubrik", "jawaban_mahasiswa"}, set(up))
check("p pertanyaan", up["pertanyaan"] == "Q1\nQ2")
check("p answer text", up["jawaban_mahasiswa"] == "jawaban mahasiswa")
check("p rubric len", len(up["rubrik"]) == 4, len(up["rubrik"]))
check(
    "p rubric keys",
    set(up["rubrik"][0]) == {"id", "nama", "bobot", "level", "catatan"},
    set(up["rubrik"][0]),
)
check("p level keys", set(up["rubrik"][0]["level"]) == {"1", "2", "3", "4"})
check("p bobot", up["rubrik"][0]["bobot"] == 25)
check("p rubric order", [x["id"] for x in up["rubrik"]] == CR)
check("p json indent", msgs[1]["content"].startswith('{\n  "pertanyaan"'))

msgs = build_messages(
    preamble=PREAMBLE,
    question="Q",
    answer={"kind": "doc", "excerpts": ["kutipan 1", "kutipan 2"]},
    rubric=full_rub,
)
up = json.loads(msgs[1]["content"])
check("p doc key", "kutipan_dokumen" in up and "jawaban_mahasiswa" not in up, set(up))
check("p doc excerpts", up["kutipan_dokumen"] == ["kutipan 1", "kutipan 2"])
check(
    "p doc catatan",
    up["catatan_sumber"]
    == "Teks berasal dari berkas yang diunggah mahasiswa dan diekstraksi di server. "
    "Kutipan harus diambil persis dari kutipan_dokumen.",
)

# ===========================================================================
# 3. rag.chunk_text
# ===========================================================================
check("c simple", chunk_text("Halo dunia.") == ["Halo dunia."])
check("c paragraphs", chunk_text("a\n\nb\nc") == ["a\nb\nc"])
check("c empty", chunk_text("") == [""])

p1 = "A" * 760 + " paragraf pertama."
p2 = "B" * 760 + " paragraf kedua."
p3 = "C" * 760 + " paragraf ketiga."
chunks = chunk_text("\n\n".join([p1, p2, p3]))
check("c multi count", len(chunks) >= 2, len(chunks))
check("c overlap", chunks[1].startswith(p1[-200:] + " "), chunks[1][:60])
check("c coverage", all(x.split()[0][:5] in "".join(chunks) for x in (p1, p2, p3)))
check("c max len", all(len(c) <= 1401 for c in chunks), [len(c) for c in chunks])

long_para = " ".join(f"Kalimat nomor {i} tentang basis data." for i in range(80))
check("c long para", len(long_para) > 1200, len(long_para))
chunks = chunk_text(long_para)
check("c sentence split", len(chunks) >= 2, len(chunks))
check("c sentence max", all(len(c) <= 1401 for c in chunks), [len(c) for c in chunks])
check("c sentence coverage", "Kalimat nomor 0" in chunks[0] and "Kalimat nomor 79" in "".join(chunks))

# ===========================================================================
# 4. ai.call_chat / embed_call / test_connection against a local server
# ===========================================================================
LAST = {}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, code, body, ctype="application/json"):
        data = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(n).decode()
        data = json.loads(raw)
        LAST["path"] = self.path
        LAST["body"] = data
        LAST["auth"] = self.headers.get("Authorization")
        if self.path.endswith("/chat/completions"):
            model = data.get("model", "")
            if model == "err500":
                self._send(500, '{"error":"server down"}')
            elif model == "notjson":
                self._send(200, "bukan json", "text/plain")
            elif model == "nocontent":
                self._send(200, "{}")
            elif model == "emptycontent":
                self._send(200, json.dumps({"choices": [{"message": {"content": "  "}}]}))
            else:
                self._send(200, json.dumps({"choices": [{"message": {"content": "Halo"}}]}))
        elif self.path.endswith("/embeddings"):
            em = data.get("model", "")
            inputs = data.get("input") or []
            if em == "err500":
                self._send(500, '{"error":"emb down"}')
            elif em == "mismatch":
                self._send(200, json.dumps({"data": [{"index": 0, "embedding": [0.1]}]}))
            elif em == "badvec":
                self._send(
                    200,
                    json.dumps({"data": [{"index": i, "embedding": []} for i in range(len(inputs))]}),
                )
            else:
                self._send(
                    200,
                    json.dumps(
                        {
                            "data": [
                                {"index": 1, "embedding": [2.0, 2.0]},
                                {"index": 0, "embedding": [1.0, 1.0]},
                            ]
                        }
                    ),
                )
        else:
            self._send(404, "{}")


srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()
PORT = srv.server_address[1]
BASE = f"http://127.0.0.1:{PORT}/v1"


class S:
    pass


s = S()
s.base_url = BASE
s.api_key = "sk-test-123"
s.model_name = "ok"
s.emb_base_url = BASE
s.emb_api_key = "emb-key"
s.emb_model_name = "ok"

r = call_chat(s, [{"role": "user", "content": "hi"}], temperature=0.2, max_tokens=1200)
check("ai chat ok", r == {"ok": True, "content": "Halo"}, r)
check("ai chat path", LAST["path"] == "/v1/chat/completions", LAST["path"])
check("ai chat auth", LAST["auth"] == "Bearer sk-test-123", LAST["auth"])
check("ai chat model", LAST["body"]["model"] == "ok")
check("ai chat temp", LAST["body"]["temperature"] == 0.2)
check("ai chat maxtok", LAST["body"]["max_tokens"] == 1200)
check("ai chat msgs", LAST["body"]["messages"][0]["content"] == "hi")

s.model_name = "err500"
r = call_chat(s, [], temperature=0, max_tokens=8)
check(
    "ai chat 500",
    not r["ok"]
    and r["message"].startswith("HTTP 500")
    and "server down" in r["message"],
    r,
)
s.model_name = "notjson"
r = call_chat(s, [], temperature=0, max_tokens=8)
check("ai chat notjson", not r["ok"] and r["message"] == "Respons server bukan JSON.", r)
s.model_name = "nocontent"
r = call_chat(s, [], temperature=0, max_tokens=8)
check("ai chat nocontent", not r["ok"] and r["message"] == "Respons tidak berisi teks.", r)
s.model_name = "emptycontent"
r = call_chat(s, [], temperature=0, max_tokens=8)
check("ai chat emptycontent", not r["ok"] and r["message"] == "Respons tidak berisi teks.", r)

s2 = S()
s2.base_url = "http://127.0.0.1:9/v1"
s2.api_key = "k"
s2.model_name = "m"
r = call_chat(s2, [], temperature=0, max_tokens=8)
check("ai chat refused", not r["ok"] and r["message"] == "fetch failed", r)

v = embed_call(s, ["a", "b"])
check("ai emb sort", v == [[1.0, 1.0], [2.0, 2.0]], v)
check("ai emb auth", LAST["auth"] == "Bearer emb-key", LAST["auth"])
check("ai emb path", LAST["path"] == "/v1/embeddings", LAST["path"])
check("ai emb input", LAST["body"]["input"] == ["a", "b"] and LAST["body"]["model"] == "ok")

s.emb_model_name = "mismatch"
try:
    embed_call(s, ["a", "b"])
    check("ai emb mismatch", False, "no raise")
except RuntimeError as e:
    check("ai emb mismatch", str(e) == "Jumlah embedding tidak sesuai.", e)
s.emb_model_name = "badvec"
try:
    embed_call(s, ["a"])
    check("ai emb badvec", False, "no raise")
except RuntimeError as e:
    check("ai emb badvec", str(e) == "Respons embedding tidak valid.", e)
s.emb_model_name = "err500"
try:
    embed_call(s, ["a"])
    check("ai emb 500", False, "no raise")
except RuntimeError as e:
    check("ai emb 500", str(e).startswith("HTTP 500") and "emb down" in str(e), e)
s.emb_model_name = "ok"

s.model_name = "ok"
r = test_connection(s)
check("ai test ok", r == {"ok": True, "message": "Koneksi berhasil."}, r)
s.model_name = "err500"
r = test_connection(s)
check(
    "ai test fail",
    not r["ok"] and r["message"].startswith("Koneksi gagal. HTTP 500"),
    r,
)
s.model_name = "ok"

srv.shutdown()

# ===========================================================================
# 5. compute_grade model path (mocked call_chat)
# ===========================================================================
ms = ModelSettings.objects.get(id=1)
MS_FIELDS = [
    "base_url", "api_key", "model_name",
    "emb_base_url", "emb_api_key", "emb_model_name",
    "temperature", "max_tokens", "system_preamble",
]
MS_SNAP = {f: getattr(ms, f) for f in MS_FIELDS}


def restore_settings():
    for f in MS_FIELDS:
        setattr(ms, f, MS_SNAP[f])
    ms.save()


def configure_model():
    ms.base_url = "https://llm.example/v1"
    ms.api_key = "sk-test"
    ms.model_name = "test-model"
    ms.save()


def configure_emb():
    ms.emb_base_url = "https://emb.example/v1"
    ms.emb_api_key = "emb-test"
    ms.emb_model_name = "emb-model"
    ms.save()


long_sub = tmp_sub = tmp_asg = tmp_topic = None
orig_cc = G.call_chat
orig_ensure = G.ensure_chunks
orig_retrieve = G.retrieve_excerpts
orig_embed = ragmod.embed_call
CAP = {}
CALLS = []


def fake_ok(content):
    def _f(settings, messages, temperature, max_tokens):
        CAP.clear()
        CAP.update(messages=messages, temperature=temperature, max_tokens=max_tokens)
        return {"ok": True, "content": content}

    return _f


def make_payload(rubric_ids):
    return {
        "criteria": [
            {"id": cid, "score": 3 + (i % 2), "quote": f"kutipan {i}", "comment": f"komentar {i}"}
            for i, cid in enumerate(rubric_ids)
        ],
        "feedback": "Umpan balik model.",
        "summary": "Ringkasan model.",
    }


try:
    configure_model()
    good_content = json.dumps(make_payload(CR))

    # --- 5a: valid model response, text path (miratil essay) ---
    G.call_chat = fake_ok(good_content)
    out = G.compute_grade(MIRATIL)
    check("m ok", out["ok"], out)
    check("m source", out.get("source") == "model")
    check("m nilai", out.get("nilai") == 87.5, out.get("nilai"))
    check("m predikat", out.get("predikat") == "A")
    check("m fb", out.get("feedback") == "Umpan balik model.")
    check("m summary", out.get("summary") == "Ringkasan model.")
    check(
        "m criteria",
        [c["criterion_id"] for c in out.get("criteria", [])] == CR
        and out["criteria"][0]["name"] == "Ketepatan konsep"
        and out["criteria"][0]["weight"] == 25
        and out["criteria"][0]["score"] == 3
        and out["criteria"][1]["score"] == 4,
        out.get("criteria"),
    )
    exp_t = float(MS_SNAP["temperature"])
    exp_t = int(exp_t) if exp_t.is_integer() else exp_t
    check("m temperature", CAP.get("temperature") == exp_t, CAP.get("temperature"))
    check("m max_tokens", CAP.get("max_tokens") == int(MS_SNAP["max_tokens"]))
    msgs = CAP.get("messages", [])
    check("m msgs", len(msgs) == 2 and msgs[0]["role"] == "system" and msgs[1]["role"] == "user")
    check("m preamble in system", MS_SNAP["system_preamble"].strip() in msgs[0]["content"])
    up = json.loads(msgs[1]["content"])
    mir = Submission.objects.get(id=MIRATIL)
    check("m jawaban", up["jawaban_mahasiswa"] == mir.answer_text, up.keys())
    check("m rubrik in payload", [x["id"] for x in up["rubrik"]] == CR)

    # --- 5b: invalid JSON content ---
    G.call_chat = fake_ok("bukan json sama sekali")
    out = G.compute_grade(MIRATIL)
    check(
        "m invalid json",
        not out["ok"]
        and out["message"] == "Respons model tidak valid. Balasan bukan JSON valid."
        and out["raw"] == "bukan json sama sekali",
        out,
    )

    # --- 5c: truncated content ---
    trunc = '{"criteria": [{"id": "r1", "score": 3'
    G.call_chat = fake_ok(trunc)
    out = G.compute_grade(MIRATIL)
    check(
        "m truncated",
        not out["ok"]
        and out["message"]
        == "Respons model tidak valid. Respons terpotong. Naikkan Max tokens "
        "pada Setelan model lalu ulangi penilaian."
        and out["raw"] == trunc,
        out,
    )

    # --- 5d: call failure ---
    def fail_cc(settings, messages, temperature, max_tokens):
        return {"ok": False, "message": "HTTP 500 — server down"}

    G.call_chat = fail_cc
    out = G.compute_grade(MIRATIL)
    check(
        "m call fail",
        not out["ok"] and out["message"] == "Gagal memanggil model. HTTP 500 — server down",
        out,
    )

    # --- 5e: view raw display on parse failure ---
    c = Client()
    c.force_login(User.objects.get(email="ramadan@nilai.test"))
    U_MIR = f"/lecturer/submissions/{MIRATIL}"
    G.call_chat = fake_ok("bukan-json-model")
    r = c.post(U_MIR, {"action": "run_grade", "submission_id": MIRATIL, "intent": "draft"})
    t = r.content.decode()
    check("v raw status", r.status_code == 200, r.status_code)
    check(
        "v raw error",
        "Respons model tidak valid. Balasan bukan JSON valid." in t,
    )
    check("v raw label", "Respons model mentah" in t)
    check("v raw body", "bukan-json-model" in t)
    check("v raw no grade", not Grade.objects.filter(submission_id=MIRATIL).exists())

    # --- 5f: view success through run_grade ---
    G.call_chat = fake_ok(good_content)
    r = c.post(U_MIR, {"action": "run_grade", "submission_id": MIRATIL, "intent": "draft"})
    check("v run loc", r.get("Location") == f"{U_MIR}?info=Nilai+disimpan+sebagai+draf.", r.get("Location"))
    g = Grade.objects.get(submission_id=MIRATIL)
    check("v run state", g.state == "draft")
    check("v run source", g.source == "model", g.source)
    check("v run nilai", float(g.nilai) == 87.5, g.nilai)
    check("v run fb", g.feedback == "Umpan balik model.")
    check("v run rev", GradeRevision.objects.filter(grade=g).count() == 1)
    check("v run by", str(g.created_by_id) == LECT)
    r = c.get(U_MIR)
    t = r.content.decode()
    check("v run draft badge", "<span>Draft</span>" in t)
    check("v run fb shown", "Umpan balik model." in t)

    # --- 5g: RAG path with mocked chunk/retrieve (fitri pdf) ---
    configure_emb()
    U_FIT = f"/lecturer/submissions/{FITRI}"
    pdf_rub = G.get_rubric(PDF)
    pdf_payload = make_payload([x["id"] for x in pdf_rub])
    seen = {}

    def ensure_spy(submission_id, text, settings):
        seen["ensure"] = (submission_id, text)

    def retrieve_ok(submission_id, query, settings):
        seen["query"] = query
        return ["kutipan dokumen 1", "kutipan dokumen 2"]

    G.call_chat = fake_ok(json.dumps(pdf_payload))
    G.ensure_chunks = ensure_spy
    G.retrieve_excerpts = retrieve_ok
    out = G.compute_grade(FITRI)
    check("rag ok", out["ok"], out)
    check("rag ensure called", seen.get("ensure", ("", ""))[0] == FITRI, seen)
    fit = Submission.objects.get(id=FITRI)
    check("rag ensure text", seen.get("ensure", ("", ""))[1] == fit.extracted_text)
    up = json.loads(CAP["messages"][1]["content"])
    check("rag doc key", "kutipan_dokumen" in up and "jawaban_mahasiswa" not in up, set(up))
    check("rag excerpts", up["kutipan_dokumen"] == ["kutipan dokumen 1", "kutipan dokumen 2"])
    check("rag query has names", pdf_rub[0]["name"] in seen.get("query", ""), seen.get("query"))
    check("rag source", out.get("source") == "model")

    def retrieve_empty(submission_id, query, settings):
        return []

    G.retrieve_excerpts = retrieve_empty
    out = G.compute_grade(FITRI)
    check(
        "rag empty excerpts",
        not out["ok"] and out["message"] == "Teks tidak terbaca.",
        out,
    )

    def retrieve_raise(submission_id, query, settings):
        raise RuntimeError("HTTP 503 — bad gateway")

    G.retrieve_excerpts = retrieve_raise
    out = G.compute_grade(FITRI)
    check(
        "rag embed error",
        not out["ok"] and out["message"] == "Embedding gagal. HTTP 503 — bad gateway",
        out,
    )

    # --- 5h: long essay answer triggers RAG (temp submission) ---
    long_text = "Paragraf penjelas mahasiswa tentang topik. " * 160  # ~6.4k
    check("lg len", len(long_text) > 6000, len(long_text))
    now = timezone.now()
    long_sub = Submission.objects.create(
        assignment_id=ESSAY,
        student_id=STU_ISMAIL,
        answer_text=long_text,
        status="submitted",
        submitted_at=now,
        updated_at=now,
    )
    G.call_chat = fake_ok(good_content)
    G.ensure_chunks = ensure_spy
    G.retrieve_excerpts = retrieve_ok
    out = G.compute_grade(str(long_sub.id))
    check("lg ok", out["ok"], out)
    check("lg ensure", seen.get("ensure", ("", ""))[0] == str(long_sub.id), seen)
    up = json.loads(CAP["messages"][1]["content"])
    check("lg doc kind", up.get("kutipan_dokumen") == ["kutipan dokumen 1", "kutipan dokumen 2"])

    # --- 5i: rubric missing (temp assignment without rubric) ---
    tmp_topic = Topic.objects.create(course_id=C_BDB, week=8, title="Tanpa rubrik")
    tmp_asg = Assignment.objects.create(
        topic_id=tmp_topic.id,
        title="Tugas tanpa rubrik",
        type="essay",
        release_mode="review",
    )
    tmp_sub = Submission.objects.create(
        assignment_id=tmp_asg.id,
        student_id=STU_ALDY,
        answer_text="Jawaban ada isinya.",
        status="submitted",
        submitted_at=now,
        updated_at=now,
    )
    out = G.compute_grade(str(tmp_sub.id))
    check("nr rubric error", not out["ok"] and out["message"] == "Rubrik belum disetel.", out)

    # --- 5j: temperature integer form ---
    ms.temperature = Decimal("1.00")
    ms.save()
    G.call_chat = fake_ok(good_content)
    G.compute_grade(MIRATIL)
    check("m temp int", CAP.get("temperature") == 1 and isinstance(CAP.get("temperature"), int), CAP.get("temperature"))

    # --- 5k: real ensure_chunks / retrieve_excerpts (pgvector) ---
    chunk_count = {"embed": 0}

    def embed_ok(settings, inputs):
        chunk_count["embed"] += 1
        return [[0.1] * 3072 for _ in inputs]

    ragmod.embed_call = embed_ok
    DocumentChunk.objects.filter(submission_id=FITRI).delete()
    ensure_chunks(FITRI, fit.extracted_text, ms)
    rows = list(DocumentChunk.objects.filter(submission_id=FITRI).order_by("position"))
    exp_chunks = chunk_text(fit.extracted_text)
    check("rc rows", len(rows) == len(exp_chunks), (len(rows), len(exp_chunks)))
    check("rc content", rows[0].content == exp_chunks[0])
    check("rc embed called once", chunk_count["embed"] == 1, chunk_count)
    ensure_chunks(FITRI, fit.extracted_text, ms)
    check("rc idempotent", chunk_count["embed"] == 1, chunk_count)

    def embed_query(settings, inputs):
        chunk_count["query"] = chunk_count.get("query", 0) + 1
        return [[0.0] * 3072 for _ in inputs]

    ragmod.embed_call = embed_query
    excerpts = retrieve_excerpts(FITRI, "kueri pencarian", ms)
    check("rc retrieve", sorted(excerpts) == sorted(r.content for r in rows), excerpts)
    check("rc topk", len(excerpts) <= dj_settings.EMBEDDING_TOP_K)
    check("rc query called", chunk_count.get("query") == 1)

    # embed failure propagates and inserts no rows
    def embed_raise(settings, inputs):
        raise RuntimeError("Jumlah embedding tidak sesuai.")

    ragmod.embed_call = embed_raise
    try:
        ensure_chunks(str(tmp_sub.id), "teks", ms)
        check("rc embed error propagates", False, "no raise")
    except RuntimeError as e:
        check("rc embed error propagates", str(e) == "Jumlah embedding tidak sesuai.", e)
    check(
        "rc no rows on error",
        not DocumentChunk.objects.filter(submission_id=tmp_sub.id).exists(),
    )

finally:
    G.call_chat = orig_cc
    G.ensure_chunks = orig_ensure
    G.retrieve_excerpts = orig_retrieve
    ragmod.embed_call = orig_embed
    GradeRevision.objects.filter(grade__submission_id=MIRATIL).delete()
    Grade.objects.filter(submission_id=MIRATIL).delete()
    DocumentChunk.objects.all().delete()
    if long_sub is not None:
        Submission.objects.filter(id=long_sub.id).delete()
    if tmp_sub is not None:
        Submission.objects.filter(id=tmp_sub.id).delete()
    if tmp_asg is not None:
        Assignment.objects.filter(id=tmp_asg.id).delete()
    if tmp_topic is not None:
        Topic.objects.filter(id=tmp_topic.id).delete()
    restore_settings()

# ---------- integrity ----------
check("seed grades intact", Grade.objects.filter(submission_id="f1000000-0000-4000-8000-000000000001").exists()
      and Grade.objects.filter(submission_id="f1000000-0000-4000-8000-000000000003").exists())
check("seed revisions", GradeRevision.objects.count() == 2, GradeRevision.objects.count())
check("submission count", Submission.objects.count() == 4, Submission.objects.count())
check("no chunks", DocumentChunk.objects.count() == 0, DocumentChunk.objects.count())
check("assignment count", Assignment.objects.count() == 4, Assignment.objects.count())
check("topic count", Topic.objects.count() == 5, Topic.objects.count())

print(f"PASS {ok}  FAIL {len(fail)}")
for f in fail:
    print(" -", f)
sys.exit(1 if fail else 0)
