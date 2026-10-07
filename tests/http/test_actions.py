import base64
import io
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from session import Session

BASE = "http://localhost:3001"
REPO = "/Users/mac/Documents/Hanif/umbima-smt1-tugas-generativeai"
PG = "d1000000-0000-4000-8000-000000000002"
ESSAY = "d1000000-0000-4000-8000-000000000001"
DOCX = "d1000000-0000-4000-8000-000000000004"
TOPIC_BD3 = "c1000000-0000-4000-8000-000000000003"
DINA_SUB = "f1000000-0000-4000-8000-000000000002"
EKO_SUB = "f1000000-0000-4000-8000-000000000003"
U_FITRI = "a1000000-0000-4000-8000-000000000014"
U_ISMAIL = "a1000000-0000-4000-8000-000000000013"
U_MIRATIL = "a1000000-0000-4000-8000-000000000012"


def psql(sql):
    return subprocess.check_output(
        ["docker", "compose", "exec", "-T", "db", "psql", "-U", "nilai",
         "-d", "nilai", "-tAc", sql],
        text=True, cwd=REPO).strip()


def _path(url):
    return url.replace(BASE, "", 1)


def get(url, sess):
    return sess.get(_path(url))


def fetch_page(url, sess):
    _, body = sess.get(_path(url))
    return body


def post_action(url, sess, marker, fields=None, files=None, page=None,
                action_fields=None, form_index=0):
    # Django forms carry a session-wide csrfmiddlewaretoken (scraped by
    # Session.post); marker/action_fields from the old Next e2e are unused.
    return sess.post(_path(url), fields=fields, files=files, page=page)


def raw_get(sess, path):
    req = urllib.request.Request(
        BASE + path,
        headers={"Cookie": "; ".join("%s=%s" % (k, v) for k, v in sess.jar.items())})
    try:
        resp = urllib.request.urlopen(req)
        return resp.status, resp.headers, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers, b""


def _sql_str(v):
    return "'" + (v or "").replace("'", "''") + "'"


def _maybe(v):
    return "NULL" if v == "" or v is None else _sql_str(v)


results = []
def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(("PASS " if ok else "FAIL ") + name + ("  " + detail if detail else ""))


s_ismail = Session().login("ismail@nilai.test")
s_miratil = Session().login("miratil@nilai.test")
s_fitri = Session().login("fitri@nilai.test")
l_ramadan = Session().login("ramadan@nilai.test")
a_admin = Session().login("audyah@nilai.test")
guest = Session()

# Seed-state snapshots restored by the net-zero cleanup at the end.
_D = " || chr(31) || "
seed_eko = psql(
    "SELECT state%s criteria::text%s feedback%s summary%s nilai%s predikat%s "
    "coalesce(source,'')%s coalesce(created_by::text,'')%s "
    "coalesce(updated_by::text,'')%s coalesce(published_at::text,'') || chr(31) || 'x' "
    "FROM grades WHERE submission_id='%s'" % ((_D,) * 9 + (EKO_SUB,)))
seed_essay_rubric = psql(
    "SELECT id%s position%s name%s weight%s level_1%s level_2%s level_3%s "
    "level_4%s prompt_notes || chr(31) || 'x' FROM rubric_criteria WHERE assignment_id='%s' "
    "ORDER BY position" % ((_D,) * 8 + (ESSAY,)))
SEED_SUBS = psql("SELECT count(*) FROM submissions")
SEED_GRADES = psql("SELECT count(*) FROM grades")
SEED_ASSIGNS = psql("SELECT count(*) FROM assignments")
SEED_REVISION_IDS = psql("SELECT id FROM grade_revisions").splitlines()

# --- SSR: quiz palette (fresh), locked view (submitted), rail, overview ----
code, body = get(f"{BASE}/student/assignments/{PG}", s_fitri)
check("PG quiz SSR: palette + 3 soal",
      code == 200 and "Navigasi soal" in body and "sisa 3 soal" in body
      and 'aria-label="Soal 3"' in body and 'aria-label="Navigasi halaman"' in body,
      body[:120].replace("\n", " "))

code, body = get(f"{BASE}/student/assignments/{PG}", s_ismail)
check("PG locked SSR (sudah terkunci)",
      code == 200 and "Pengumpulan terkunci" in body and "Jawaban Anda" in body
      and "Kunci jawaban" not in body and "Pilihan Anda" in body)

code, body = get(f"{BASE}/lecturer/submissions", l_ramadan)
check("overview: header + nav + rows",
      code == 200 and "Seluruh pengumpulan" in body
      and 'href="/lecturer/submissions"' in body
      and "Ismail Saputra" in body)

# --- v3: pertemuan cards, topic page, tasks page, breadcrumbs ---------------
C_BD = "b1000000-0000-4000-8000-000000000001"
TOPIC_BD3 = "c1000000-0000-4000-8000-000000000003"

code, body = get(f"{BASE}/student/courses", s_miratil)
check("course list: cards link into courses",
      code == 200 and "IF201" in body and 'href="/student/courses/' in body,
      body[:120].replace("\n", " "))

code, body = get(f"{BASE}/student/courses/{C_BD}", s_miratil)
check("course detail: pertemuan cards + breadcrumb",
      code == 200 and f"/topics/" in body and "terkumpul" in body
      and 'aria-label="Navigasi halaman"' in body,
      body[:120].replace("\n", " "))

code, body = get(f"{BASE}/student/courses/{C_BD}/topics/{TOPIC_BD3}", s_miratil)
check("topic page: materi + tugas + prev/next",
      code == 200 and "Pertemuan 3" in body and "Materi" in body
      and "Tugas" in body and "Ke mata kuliah" in body,
      body[:120].replace("\n", " "))

code, body = get(f"{BASE}/student/tasks", s_miratil)
check("tasks page: grouped list + rail item",
      code == 200 and "Belum dikerjakan" in body and "Sudah dikumpulkan" in body
      and 'href="/student/tasks"' in body,
      body[:120].replace("\n", " "))

# --- multi-question PG submit flow (fitri) ---------------------------------
pg_page = fetch_page(f"{BASE}/student/assignments/{PG}", s_fitri)
code, body = post_action(f"{BASE}/student/assignments/{PG}", s_fitri,
                         "assignment_id",
                         {"assignment_id": PG, "answers": json.dumps(["B", "A"])},
                         page=pg_page)
check("PG incomplete answers rejected",
      code == 200 and "Jawaban tidak lengkap" in body)

code, body = post_action(f"{BASE}/student/assignments/{PG}", s_fitri,
                         "assignment_id",
                         {"assignment_id": PG, "answers": json.dumps(["X", "A", "C"])},
                         page=pg_page)
check("PG invalid choice rejected",
      code == 200 and "Soal ke-1" in body)

code, body = post_action(f"{BASE}/student/assignments/{PG}", s_fitri,
                         "assignment_id",
                         {"assignment_id": PG, "answers": json.dumps(["B", "A", "B"])},
                         page=pg_page)
check("PG submit redirects to assignment + answers",
      code == 200 and "Terkirim! Jawaban Anda" in body
      and "Jawaban Anda" in body and "Pengumpulan terkunci" in body,
      body[:160].replace("\n", " "))
check("PG answers saved",
      psql("SELECT answers::text FROM submissions WHERE assignment_id='%s' AND student_id='%s'"
           % (PG, U_FITRI)) == '["B", "A", "B"]')

code, body = get(f"{BASE}/student/assignments/{PG}", s_fitri)
check("flash notice not replayable on refresh",
      code == 200 and "Terkirim! Jawaban Anda" not in body)
code, body = get(f"{BASE}/student/assignments/{PG}?terkirim=1", s_fitri)
check("?terkirim=1 URL no longer shows notice",
      code == 200 and "Terkirim! Jawaban Anda" not in body)

code, body = post_action(f"{BASE}/student/assignments/{PG}", s_fitri,
                         "assignment_id",
                         {"assignment_id": PG, "answers": json.dumps(["B", "A", "C"])},
                         page=pg_page)
check("PG resubmit rejected (locked)",
      code == 200 and "Pengumpulan terkunci" in body
      and psql("SELECT answers::text FROM submissions WHERE assignment_id='%s' AND student_id='%s'"
               % (PG, U_FITRI)) == '["B", "A", "B"]')

# --- code grading: 2/3 correct and 3/3 correct -----------------------------
fitri_pg_sub = psql("SELECT id FROM submissions WHERE assignment_id='%s' AND student_id='%s'"
                    % (PG, U_FITRI))
code, body = post_action(f"{BASE}/lecturer/submissions/{fitri_pg_sub}", l_ramadan,
                         "submission_id",
                         {"action": "run_grade", "submission_id": fitri_pg_sub, "intent": "draft"})
check("runGrade PG 2/3 -> 66.67 C",
      psql("SELECT nilai || '|' || predikat || '|' || source || '|' || feedback FROM grades WHERE submission_id='%s'"
           % fitri_pg_sub) == "66.67|C|code|2 dari 3 jawaban benar.",
      psql("SELECT nilai || '|' || predikat || '|' || source || '|' || feedback FROM grades WHERE submission_id='%s'" % fitri_pg_sub))

# fitri grade is published -> answer key + marks revealed on his locked view
code, body = post_action(f"{BASE}/lecturer/submissions/{fitri_pg_sub}", l_ramadan,
                         "submission_id",
                         {"action": "run_grade", "submission_id": fitri_pg_sub, "intent": "publish"})
code, body = get(f"{BASE}/student/assignments/{PG}", s_fitri)
check("PG reveal: benar + kurang tepat + kunci",
      code == 200 and "Benar" in body and "Kurang tepat" in body
      and "Kunci jawaban" in body,
      body[:120].replace("\n", " "))

code, body = post_action(f"{BASE}/lecturer/submissions/{EKO_SUB}", l_ramadan,
                         "submission_id", {"action": "run_grade", "submission_id": EKO_SUB, "intent": "draft"})
check("runGrade PG 3/3 -> 100 A (seed)",
      psql("SELECT nilai || '|' || predikat || '|' || source FROM grades WHERE submission_id='%s'"
           % EKO_SUB) == "100.00|A|code")

code, body = post_action(f"{BASE}/lecturer/submissions/{EKO_SUB}", l_ramadan,
                         "submission_id", {"action": "run_grade", "submission_id": EKO_SUB, "intent": "publish"})
check("runGrade publish (ismail)",
      psql("SELECT state FROM grades WHERE submission_id='%s'" % EKO_SUB) == "published")
code, body = get(f"{BASE}/student/assignments/{PG}", s_ismail)
check("PG reveal all correct: benar, no kurang tepat",
      code == 200 and "Benar" in body and "Kurang tepat" not in body
      and "Pilihan Anda" not in body)

# --- essay: fresh submit (ismail) then lock ---------------------------------
ess_page = fetch_page(f"{BASE}/student/assignments/{ESSAY}", s_ismail)
ans = ("Normalisasi mengurangi redundansi. 1NF menghilangkan nilai ganda, "
       "2NF menghilangkan ketergantungan parsial, 3NF menghilangkan ketergantungan "
       "transitif. Contoh: pisahkan nama pelanggan ke tabel pelanggan.")
code, body = post_action(f"{BASE}/student/assignments/{ESSAY}", s_ismail,
                         "answer", {"assignment_id": ESSAY, "answer": ans},
                         page=ess_page)
check("essay submit redirects + answers",
      code == 200 and "Terkirim! Jawaban Anda" in body
      and "Jawaban Anda" in body,
      body[:160].replace("\n", " "))
check("essay answer saved",
      psql("SELECT answer_text FROM submissions WHERE assignment_id='%s' AND student_id='%s'"
           % (ESSAY, U_ISMAIL)) == ans)

code, body = post_action(f"{BASE}/student/assignments/{ESSAY}", s_ismail,
                         "answer", {"assignment_id": ESSAY, "answer": ans + " DITOLAK"},
                         page=ess_page)
check("essay resubmit rejected (locked)",
      code == 200 and "Pengumpulan terkunci" in body
      and psql("SELECT answer_text FROM submissions WHERE assignment_id='%s' AND student_id='%s'"
               % (ESSAY, U_ISMAIL)) == ans)

_mir_before = psql("SELECT answer_text FROM submissions WHERE assignment_id='%s' AND student_id='%s'"
                   % (ESSAY, U_MIRATIL))
mir_page = fetch_page(f"{BASE}/student/assignments/{ESSAY}", s_miratil)
code, body = post_action(f"{BASE}/student/assignments/{ESSAY}", s_miratil,
                         "answer", {"assignment_id": ESSAY, "answer": "PENGGANTI DITOLAK"},
                         page=mir_page)
check("seed submission also locked (miratil)",
      code == 200 and "Pengumpulan terkunci" in body
      and psql("SELECT answer_text FROM submissions WHERE assignment_id='%s' AND student_id='%s'"
               % (ESSAY, U_MIRATIL)) == _mir_before)

# --- rubric round-trip ------------------------------------------------------
rows = psql(
    "SELECT id || '|' || name || '|' || weight FROM rubric_criteria "
    "WHERE assignment_id='%s' ORDER BY position" % ESSAY)
criteria = []
for line in rows.splitlines():
    cid, name, weight = line.split("|")
    criteria.append({
        "id": cid, "name": name, "weight": int(weight),
        "level_1": "l1 " + name, "level_2": "l2", "level_3": "l3", "level_4": "l4",
        "prompt_notes": "diedit-dosen",
    })
code, body = post_action(f"{BASE}/lecturer/assignments/{ESSAY}", l_ramadan,
                         "criteria",
                         {"action": "save_rubric", "assignment_id": ESSAY, "criteria": json.dumps(criteria)})
check("rubric save", code == 200 and "Rubrik disimpan" in body)
check("rubric prompt_notes updated",
      psql("SELECT count(*) FROM rubric_criteria WHERE assignment_id='%s' AND prompt_notes='diedit-dosen'" % ESSAY) == "4")
check("rubric count still 4",
      psql("SELECT count(*) FROM rubric_criteria WHERE assignment_id='%s'" % ESSAY) == "4")

bad = [dict(c, weight=30) for c in criteria]
code, body = post_action(f"{BASE}/lecturer/assignments/{ESSAY}", l_ramadan,
                         "criteria",
                         {"action": "save_rubric", "assignment_id": ESSAY, "criteria": json.dumps(bad)})
check("rubric sum != 100 rejected", code == 200 and "Bobot harus berjumlah 100" in body)

# --- manual draft grade for miratil -------------------------------------------
scores = [{"id": c["id"], "score": 3, "quote": "kutipan", "comment": "komentar"} for c in criteria]
code, body = post_action(f"{BASE}/lecturer/submissions/{DINA_SUB}", l_ramadan,
                         "feedback",
                         {"action": "save_grade", "submission_id": DINA_SUB,
                          "criteria": json.dumps(scores),
                          "feedback": "Jawaban sudah membaik.",
                          "summary": "Cukup lengkap.",
                          "intent": "draft"})
check("grade save (draft)", code == 200 and "draf" in body)
check("grade draft nilai = 75",
      psql("SELECT state || '|' || nilai || '|' || predikat FROM grades WHERE submission_id='%s'" % DINA_SUB)
      == "draft|75.00|B")

# --- docx upload on langsung (fitri) ---------------------------------------
buf = io.BytesIO()
with zipfile.ZipFile(buf, "w") as z:
    z.writestr("[Content_Types].xml",
               '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
               '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
               '<Default Extension="xml" ContentType="application/xml"/>'
               '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
               '</Types>')
    z.writestr("_rels/.rels",
               '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
               '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
               '</Relationships>')
    z.writestr("word/document.xml",
               '<?xml version="1.0"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
               '<w:body><w:p><w:r><w:t>Rancangan skema: tabel mahasiswa berisi nim dan nama. '
               'Tabel kelas berisi id dan kode matakuliah. Relasi satu ke banyak.</w:t></w:r></w:p></w:body></w:document>')
docx_bytes = buf.getvalue()

code, body = post_action(
    f"{BASE}/student/assignments/{DOCX}", s_fitri, "file",
    {"assignment_id": DOCX},
    files={"file": ("rancangan-fitri.docx", docx_bytes,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document")})
check("docx submit (langsung) redirects + answers",
      code == 200 and "Terkirim! Jawaban Anda" in body
      and "Jawaban Anda" in body,
      body[:200].replace("\n", " "))
row = psql("SELECT status || '|' || coalesce(extraction_ok::text,'-') || '|' || "
           "coalesce(left(extracted_text,20),'') FROM submissions "
           "WHERE assignment_id='%s' AND student_id='%s'" % (DOCX, U_FITRI))
check("docx submitted + extracted + auto-graded (langsung configured)",
      row.startswith("submitted|true|Rancangan skema"), row)
grade_row = psql("SELECT g.state || '|' || g.source FROM grades g JOIN submissions s ON s.id=g.submission_id "
                 "WHERE s.assignment_id='%s' AND s.student_id='%s'" % (DOCX, U_FITRI))
check("docx auto-grade published from model (RAG e2e)",
      grade_row == "published|model", grade_row)

# --- release mode validation (model + embeddings configured) ---------------
code, body = post_action(f"{BASE}/lecturer/assignments/{DOCX}", l_ramadan,
                         "assignment_id",
                         {"action": "save_mode", "assignment_id": DOCX, "mode": "langsung"})
check("langsung without confirm rejected",
      code == 200 and 'Centang' in body, body[:160].replace("\n", " "))
check("release_mode unchanged",
      psql("SELECT release_mode FROM assignments WHERE id='%s'" % DOCX) == "langsung")

code, body = post_action(f"{BASE}/lecturer/assignments/{DOCX}", l_ramadan,
                         "assignment_id",
                         {"action": "save_mode", "assignment_id": DOCX, "mode": "langsung", "confirm": "on"})
check("langsung save succeeds when configured",
      code == 200 and "Mode langsun rilis aktif" in body,
      body[:200].replace("\n", " "))

def env_var(name):
    for line in open("/Users/mac/Documents/Hanif/umbima-smt1-tugas-generativeai/.env.local"):
        if line.startswith(name + "="):
            return line.strip().split("=", 1)[1]
    return ""

psql("UPDATE model_settings SET api_key='' WHERE id=1")
code, body = post_action(f"{BASE}/lecturer/assignments/{DOCX}", l_ramadan,
                         "assignment_id",
                         {"action": "save_mode", "assignment_id": DOCX, "mode": "langsung", "confirm": "on"})
check("langsung blocked without model",
      code == 200 and "Model belum disetel" in body)
psql("UPDATE model_settings SET api_key='%s' WHERE id=1"
     % env_var("LLM_API_KEY").replace("'", "''"))

psql("UPDATE model_settings SET emb_api_key='' WHERE id=1")
code, body = post_action(f"{BASE}/lecturer/assignments/{DOCX}", l_ramadan,
                         "assignment_id",
                         {"action": "save_mode", "assignment_id": DOCX, "mode": "langsung", "confirm": "on"})
check("langsung blocked without embeddings (docx)",
      code == 200 and "Embedding belum disetel" in body)
psql("UPDATE model_settings SET emb_api_key='%s' WHERE id=1"
     % env_var("EMB_API_KEY").replace("'", "''"))

# --- multi-question assignment creation ------------------------------------
C_BD = "b1000000-0000-4000-8000-000000000001"
topic_url = f"{BASE}/lecturer/courses/{C_BD}/topics/{TOPIC_BD3}"
qjson = json.dumps([
    {"question": "Soal A: klaus JOIN?", "options": [
        {"key": "A", "text": "UNION"}, {"key": "B", "text": "JOIN"}], "answer_key": "B"},
    {"question": "Soal B: fungsi agregat jumlah?", "options": [
        {"key": "A", "text": "COUNT"}, {"key": "B", "text": "SUM"}], "answer_key": "B"},
    {"question": "Soal C: klausa unik?", "options": [
        {"key": "A", "text": "DISTINCT"}, {"key": "B", "text": "ORDER BY"}], "answer_key": "A"},
])
code, body = post_action(topic_url, l_ramadan, None,
                         {"action": "create_assignment", "title": "PG uji tiga soal",
                          "type": "pg", "questions": qjson})
check("create 3-Q PG redirects to assignment",
      code == 200 and "PG uji tiga soal" in body
      and "Soal C: klausa unik?" in body, body[:160].replace("\n", " "))
check("3 question rows inserted",
      psql("SELECT count(*) FROM assignment_questions q JOIN assignments a ON a.id=q.assignment_id "
           "WHERE a.title='PG uji tiga soal'") == "3")
check("answer keys order B,B,A",
      psql("SELECT string_agg(answer_key, ',' ORDER BY position) FROM assignment_questions q "
           "JOIN assignments a ON a.id=q.assignment_id WHERE a.title='PG uji tiga soal'") == "B,B,A")

badq = json.dumps([{"question": "Satu opsi saja", "options": [
    {"key": "A", "text": "satu"}], "answer_key": "A"}])
code, body = post_action(topic_url, l_ramadan, None,
                         {"action": "create_assignment", "title": "PG uji gagal",
                          "type": "pg", "questions": badq})
check("1-option question rejected",
      code == 200 and "isi minimal dua opsi" in body,
      body[:160].replace("\n", " "))
check("failed creation not persisted",
      psql("SELECT count(*) FROM assignments WHERE title='PG uji gagal'") == "0")

# --- admin: period, class (periode+seksi), placement (net-zero) -------------
code, body = post_action(f"{BASE}/admin/periods", a_admin, None,
                         {"action": "save", "name": "Uji Periode 2099"})
check("admin create period via action",
      code == 200 and
      psql("SELECT count(*) FROM periods WHERE name='Uji Periode 2099'") == "1",
      body[:120].replace("\n", " "))
PER_UJI = psql("SELECT id FROM periods WHERE name='Uji Periode 2099'")

code, body = post_action(f"{BASE}/admin/courses", a_admin, None,
                         {"action": "save", "code": "ZZZ999", "name": "Kelas Uji",
                          "semester": "1", "sks": "2",
                          "period_id": PER_UJI, "section": "X"})
check("admin create class with periode + seksi",
      code == 200 and
      psql("SELECT period_id || '|' || section FROM courses WHERE code='ZZZ999'")
      == "%s|X" % PER_UJI,
      body[:120].replace("\n", " "))
CLS_UJI = psql("SELECT id FROM courses WHERE code='ZZZ999'")

code, _ = post_action(f"{BASE}/admin/placement", a_admin, None,
                      {"action": "toggle", "course_id": CLS_UJI, "student_id": U_FITRI})
check("placement enrolls student into class",
      code == 200 and
      psql("SELECT count(*) FROM enrollments WHERE course_id='%s' AND student_id='%s'"
           % (CLS_UJI, U_FITRI)) == "1")

code, _ = post_action(f"{BASE}/admin/placement", a_admin, None,
                      {"action": "toggle", "course_id": CLS_UJI, "student_id": U_FITRI})
check("placement removes student from class",
      code == 200 and
      psql("SELECT count(*) FROM enrollments WHERE course_id='%s' AND student_id='%s'"
           % (CLS_UJI, U_FITRI)) == "0")

code, _ = post_action(f"{BASE}/admin/courses", a_admin, None,
                      {"action": "delete", "id": CLS_UJI})
check("admin deletes test class",
      code == 200 and psql("SELECT count(*) FROM courses WHERE code='ZZZ999'") == "0")

code, _ = post_action(f"{BASE}/admin/periods", a_admin, None,
                      {"action": "delete", "id": PER_UJI})
check("admin deletes test period",
      code == 200 and
      psql("SELECT count(*) FROM periods WHERE name='Uji Periode 2099'") == "0")

# --- admin: application branding (Aplikasi tab) ------------------------------
def appset():
    return psql("SELECT app_name || '|' || footer_text || '|' || coalesce(logo_type, '-') "
                "FROM app_settings WHERE id=1")

def poll_appset(want):
    for _ in range(30):
        if appset() == want:
            return True
        time.sleep(0.2)
    return False

code, body = post_action(f"{BASE}/admin/branding", a_admin, None,
                         {"app_name": "KelasKu", "footer_text": "Portal Kuliah"})
check("branding rename + footer saved",
      code == 200 and poll_appset("KelasKu|Portal Kuliah|-"), appset())

code, body = get(f"{BASE}/login", guest)
check("rename reflected in guest page title + navbar",
      code == 200 and "<title>KelasKu</title>" in body and "KelasKu" in body,
      body[:120].replace("\n", " "))

PNG_1PX = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQ"
    "GAhKmMIQAAAABJRU5ErkJggg==")

code, _ = post_action(f"{BASE}/admin/branding", a_admin, None,
                      {"app_name": "KelasKu", "footer_text": "Portal Kuliah"},
                      files={"logo": ("logo.png", PNG_1PX, "image/png")})
check("logo upload stored",
      code == 200 and poll_appset("KelasKu|Portal Kuliah|image/png"), appset())

lstatus, lheaders, blob = raw_get(a_admin, "/logo")
check("/logo serves uploaded image",
      lstatus == 200 and "image/png" in lheaders.get("Content-Type", "")
      and blob == PNG_1PX,
      "status=%s ct=%s len=%d" % (lstatus, lheaders.get("Content-Type"), len(blob)))

code, _ = post_action(f"{BASE}/admin/branding", a_admin, None,
                      {"app_name": "KelasKu", "footer_text": "Portal Kuliah",
                       "remove_logo": "on"})
check("remove logo clears stored image",
      code == 200 and poll_appset("KelasKu|Portal Kuliah|-"), appset())

logo_code, _, _ = raw_get(a_admin, "/logo")
check("/logo 404 after removal", logo_code == 404, "status=%s" % logo_code)

code, _ = post_action(f"{BASE}/admin/branding", a_admin, None,
                      {"app_name": "MiniCourse", "footer_text": ""})
check("branding reverted to defaults",
      code == 200 and poll_appset("MiniCourse||-"), appset())

# state round-trip via the real SSR form (its $ACTION_KEY is scraped)
code, body = post_action(f"{BASE}/admin/branding", a_admin, "app_name",
                         {"app_name": "", "footer_text": "Portal Kuliah"})
check("branding validation error rendered from returned state",
      code == 200 and "Nama aplikasi wajib diisi." in body,
      body[:160].replace("\n", " "))
check("invalid save did not persist", appset() == "MiniCourse||-", appset())

# --- admin: Excel import (preview -> confirm, skip existing) ----------------
from openpyxl import Workbook

_wb = Workbook()
_ws = _wb.active
_ws.title = "Pengguna"
_ws.append(["Nama", "Email", "Peran", "Status"])
_ws.append(["Uji Impor", "uji.impor@nilai.test", "mahasiswa", "aktif"])
_ws.append(["Ismail Saputra", "ismail@nilai.test", "dosen", "aktif"])
_ws.append(["Tanpa Email", "", "mahasiswa", "aktif"])
_buf = io.BytesIO()
_wb.save(_buf)
fixture = _buf.getvalue()

tstatus, theaders, tpl = raw_get(a_admin, "/admin/users/template")
check("template download is xlsx",
      tstatus == 200 and "spreadsheetml" in theaders.get("Content-Type", "")
      and tpl[:2] == b"PK" and "template-pengguna.xlsx" in
      theaders.get("Content-Disposition", ""),
      theaders.get("Content-Disposition", ""))

users_before = psql("SELECT count(*) FROM users")
code, body = post_action(f"{BASE}/admin/users", a_admin, None, {"action": "preview"},
                         files={"file": ("impor.xlsx", fixture,
                                         "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
check("preview action parses upload without side effects",
      code == 200 and psql("SELECT count(*) FROM users") == users_before,
      "status=%s" % code)

bad = b"bukan xlsx"
code, body = post_action(f"{BASE}/admin/users", a_admin, None, {"action": "preview"},
                         files={"file": ("impor.xlsx", bad,
                                         "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
check("preview rejects corrupt workbook",
      code == 200 and psql("SELECT count(*) FROM users") == users_before,
      "status=%s" % code)

rows_json = json.dumps([
    {"line": 2, "name": "Uji Impor", "email": "uji.impor@nilai.test",
     "role": "mahasiswa", "status": "aktif"},
    {"line": 3, "name": "Ismail Saputra", "email": "ismail@nilai.test",
     "role": "dosen", "status": "aktif"},
    {"line": 4, "name": "Tanpa Email", "email": "",
     "role": "mahasiswa", "status": "aktif"},
])
code, body = post_action(f"{BASE}/admin/users", a_admin, None,
                         {"action": "confirm", "rows": rows_json})
check("confirm inserts only the new valid user",
      code == 200 and
      psql("SELECT name || '|' || role || '|' || status || '|' || "
           "(password_hash IS NOT NULL) FROM users WHERE email='uji.impor@nilai.test'")
      == "Uji Impor|student|active|true")
check("confirm skips existing email (row untouched)",
      psql("SELECT role || '|' || (password_hash IS NOT NULL) FROM users "
           "WHERE email='ismail@nilai.test'") == "student|true")
check("confirm adds exactly one user",
      psql("SELECT count(*) FROM users") == str(int(users_before) + 1))

psql("DELETE FROM users WHERE email='uji.impor@nilai.test'")
check("cleanup deleted imported user (net-zero)",
      psql("SELECT count(*) FROM users WHERE email='uji.impor@nilai.test'") == "0")

# --- net-zero cleanup: restore seed state --------------------------------
psql("DELETE FROM document_chunks WHERE submission_id IN "
     "(SELECT id FROM submissions WHERE assignment_id='%s' AND student_id='%s')"
     % (DOCX, U_FITRI))
psql("DELETE FROM grades WHERE submission_id IN (SELECT id FROM submissions "
     "WHERE (assignment_id='%s' AND student_id='%s') OR "
     "(assignment_id='%s' AND student_id='%s') OR "
     "(assignment_id='%s' AND student_id='%s'))"
     % (PG, U_FITRI, ESSAY, U_ISMAIL, DOCX, U_FITRI))
psql("DELETE FROM submissions WHERE "
     "(assignment_id='%s' AND student_id='%s') OR "
     "(assignment_id='%s' AND student_id='%s') OR "
     "(assignment_id='%s' AND student_id='%s')"
     % (PG, U_FITRI, ESSAY, U_ISMAIL, DOCX, U_FITRI))
psql("DELETE FROM grades WHERE submission_id='%s'" % DINA_SUB)
psql("DELETE FROM assignment_questions WHERE assignment_id IN "
     "(SELECT id FROM assignments WHERE title='PG uji tiga soal')")
psql("DELETE FROM assignments WHERE title='PG uji tiga soal'")

_eko_cols = seed_eko.split("\x1f")
assert _eko_cols[-1] == "x", repr(seed_eko)
(_st, _cr, _fb, _sm, _nl, _pr, _sr, _cb, _ub, _pt) = _eko_cols[:-1]
psql("UPDATE grades SET state=%s, criteria=%s::jsonb, feedback=%s, summary=%s, "
     "nilai=%s, predikat=%s, source=%s, created_by=%s, updated_by=%s, "
     "published_at=%s WHERE submission_id='%s'"
     % (_sql_str(_st), _sql_str(_cr), _sql_str(_fb), _sql_str(_sm), _nl,
        _sql_str(_pr), _maybe(_sr), _maybe(_cb), _maybe(_ub), _maybe(_pt),
        EKO_SUB))

for _line in seed_essay_rubric.splitlines():
    _rc_cols = _line.split("\x1f")
    assert _rc_cols[-1] == "x", repr(_line)
    (_cid, _pos, _name, _w, _l1, _l2, _l3, _l4, _notes) = _rc_cols[:-1]
    psql("UPDATE rubric_criteria SET position=%s, name=%s, weight=%s, "
         "level_1=%s, level_2=%s, level_3=%s, level_4=%s, prompt_notes=%s "
         "WHERE id=%s"
         % (_pos, _sql_str(_name), _w, _sql_str(_l1), _sql_str(_l2),
            _sql_str(_l3), _sql_str(_l4), _sql_str(_notes), _sql_str(_cid)))

for _rid in psql("SELECT id FROM grade_revisions").splitlines():
    if _rid not in SEED_REVISION_IDS:
        psql("DELETE FROM grade_revisions WHERE id='%s'" % _rid)
check("cleanup: grade_revisions net-zero",
      psql("SELECT count(*) FROM grade_revisions") == str(len(SEED_REVISION_IDS)))
check("cleanup: submissions net-zero",
      psql("SELECT count(*) FROM submissions") == SEED_SUBS)
check("cleanup: grades net-zero",
      psql("SELECT count(*) FROM grades") == SEED_GRADES)
check("cleanup: assignments net-zero",
      psql("SELECT count(*) FROM assignments") == SEED_ASSIGNS)
check("cleanup: ismail PG grade restored",
      psql("SELECT state || chr(31) || criteria::text || chr(31) || feedback || "
           "chr(31) || summary || chr(31) || nilai || chr(31) || predikat || "
           "chr(31) || coalesce(source,'') || chr(31) || "
           "coalesce(created_by::text,'') || chr(31) || "
           "coalesce(updated_by::text,'') || chr(31) || "
           "coalesce(published_at::text,'') || chr(31) || 'x' FROM grades "
           "WHERE submission_id='%s'" % EKO_SUB) == seed_eko)
check("cleanup: essay rubric restored",
      psql("SELECT count(*) FROM rubric_criteria WHERE assignment_id='%s' "
           "AND prompt_notes='diedit-dosen'" % ESSAY) == "0")

fails = [r for r in results if not r[1]]
print("\n%d/%d passed" % (len(results) - len(fails), len(results)))
sys.exit(1 if fails else 0)
