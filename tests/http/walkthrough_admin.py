from playwright.sync_api import sync_playwright
import re
import subprocess
import sys

BASE = "http://localhost:3001"
C_BD = "b1000000-0000-4000-8000-000000000001"
CB_B = "b1000000-0000-4000-8000-000000000003"
U_ALDY = "a1000000-0000-4000-8000-000000000011"
U_FITRI = "a1000000-0000-4000-8000-000000000014"
PER_ACTIVE = "b2000000-0000-4000-8000-000000000001"

results = []


def check(name, ok, extra=""):
    results.append((name, ok))
    print(("PASS " if ok else "FAIL ") + name + (("  -> " + str(extra)) if not ok and extra else ""))


def psql(sql):
    return subprocess.check_output(
        ["docker", "compose", "exec", "-T", "db", "psql", "-U", "nilai",
         "-d", "nilai", "-tAc", sql],
        text=True, cwd="/Users/mac/Documents/Hanif/umbima-smt1-tugas-generativeai").strip()


def login(page, email):
    page.goto(BASE + "/login", wait_until="networkidle")
    page.fill("input[name=email]", email)
    page.fill("input[name=password]", "password123")
    with page.expect_response(lambda r: r.request.method == "POST"):
        page.click("button[type=submit]")
    for _ in range(50):
        if not page.url.rstrip("/").endswith("/login"):
            break
        page.wait_for_timeout(200)
    page.wait_for_load_state("networkidle")


def submit(page, fn):
    with page.expect_response(lambda r: r.request.method == "POST"):
        fn()


with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=True)
    ctx = browser.new_context()
    page = ctx.new_page()
    page.on("dialog", lambda d: d.accept())

    # --- admin login ---
    login(page, "audyah@nilai.test")
    check("admin lands on /admin", page.url.rstrip("/").endswith("/admin"), page.url)

    # --- periods CRUD ---
    page.goto(BASE + "/admin/periods", wait_until="networkidle")
    page.click("a:has-text('Tambah periode')")
    page.fill("#p-name", "Periode Walkthrough")
    submit(page, lambda: page.click("button:has-text('Simpan')"))
    page.wait_for_selector("tr:has-text('Periode Walkthrough')", timeout=10000)
    check("period row created",
          psql("SELECT count(*) FROM periods WHERE name='Periode Walkthrough'") == "1")

    row = page.locator("tr", has_text="Periode Walkthrough")
    row.get_by_role("link", name="Ubah").click()
    page.wait_for_selector("#p-name")
    check("period edit form prefilled",
          page.input_value("#p-name") == "Periode Walkthrough")
    page.click("a:has-text('Batal')")
    page.wait_for_selector("#p-name", state="detached")

    row.get_by_role("button", name="Hapus").click()
    page.wait_for_selector("tr:has-text('Periode Walkthrough')", state="detached",
                           timeout=10000)
    check("period row deleted",
          psql("SELECT count(*) FROM periods WHERE name='Periode Walkthrough'") == "0")

    # --- class (mata kuliah) CRUD with periode + seksi ---
    page.goto(BASE + "/admin/courses", wait_until="networkidle")
    page.click("a:has-text('Tambah kelas')")
    page.fill("input[name=code]", "ZZZ999")
    page.fill("input[name=name]", "Kelas Walkthrough")
    page.select_option("select[name=period_id]", PER_ACTIVE)
    page.fill("input[name=section]", "W")
    submit(page, lambda: page.click("button:has-text('Simpan')"))
    page.wait_for_selector("tr:has-text('ZZZ999')", timeout=10000)
    cls_row = page.locator("tr", has_text="ZZZ999")
    row_txt = cls_row.inner_text()
    check("class row shows Periode + Kelas",
          "W" in row_txt and "Ganjil" in row_txt and
          psql("SELECT period_id || '|' || section FROM courses WHERE code='ZZZ999'")
          == "%s|W" % PER_ACTIVE, row_txt.replace("\n", " "))

    cls_row.get_by_role("link", name="Ubah").click()
    page.wait_for_selector("input[name=code]")
    check("class edit form prefilled",
          page.input_value("input[name=code]") == "ZZZ999"
          and page.input_value("input[name=section]") == "W"
          and page.input_value("input[name=name]") == "Kelas Walkthrough")
    page.fill("input[name=name]", "Kelas Walkthrough Dua")
    submit(page, lambda: page.click("button:has-text('Simpan')"))
    page.wait_for_selector("tr:has-text('Kelas Walkthrough Dua')", timeout=10000)
    check("class renamed via edit",
          psql("SELECT name FROM courses WHERE code='ZZZ999'") == "Kelas Walkthrough Dua")

    page.locator("tr", has_text="ZZZ999").get_by_role("button", name="Hapus").click()
    page.wait_for_selector("tr:has-text('ZZZ999')", state="detached", timeout=10000)
    check("class row deleted (confirm dialog)",
          psql("SELECT count(*) FROM courses WHERE code='ZZZ999'") == "0")

    # --- course detail: periode/kelas + search + assignment ---
    page.goto(BASE + "/admin/courses/" + C_BD, wait_until="networkidle")
    body = page.inner_text("body")
    check("detail shows Periode + Kelas values",
          "Periode" in body and "Kelas" in body and "2025/2026 Ganjil" in body)
    check("seeded lecturer checkbox checked",
          page.locator("label", has_text="Ramadan Agung Wibawa").locator("input").is_checked())

    page.fill("#assign-student-q", "fitri")
    page.wait_for_selector("text=Fitri Lestari", timeout=5000)
    check("student search filters list",
          page.locator("#assign-students label", has_text="Ismail Saputra").evaluate(
              "el => getComputedStyle(el).display === 'none'")
          and page.locator("#assign-students label", has_text="Fitri Lestari").evaluate(
              "el => getComputedStyle(el).display !== 'none'"))

    fitri_box = page.locator("label", has_text="Fitri Lestari").locator("input").first
    import time

    pre = psql("SELECT count(*) FROM enrollments WHERE course_id='%s' AND student_id='%s'"
               % (C_BD, U_FITRI))

    def enr():
        return psql("SELECT count(*) FROM enrollments WHERE course_id='%s' AND student_id='%s'"
                    % (C_BD, U_FITRI))

    def poll(want):
        for _ in range(30):
            if enr() == want:
                return True
            time.sleep(0.2)
        return False

    if not fitri_box.is_checked():
        fitri_box.check()
    check("detail assign enrolls student", poll("1") and enr() == "1")

    fitri_box = page.locator("label", has_text="Fitri Lestari").locator("input").first
    if fitri_box.is_checked():
        fitri_box.uncheck()
    check("detail assign removes student", poll("0") and enr() == "0")

    if pre == "1":
        fitri_box = page.locator("label", has_text="Fitri Lestari").locator("input").first
        if not fitri_box.is_checked():
            fitri_box.check()
        poll("1")
    check("detail assign restored initial state", enr() == pre)

    # --- placement tab ---
    page.goto(BASE + "/admin/placement", wait_until="networkidle")
    page.fill("#placement-student-q", "aldy")
    page.wait_for_selector("button:has-text('aldy@nilai.test')", timeout=5000)
    page.locator("button", has_text="aldy@nilai.test").first.click()
    page.wait_for_selector("text=Penempatan untuk Aldy", timeout=5000)
    check("class table lists active-period classes",
          page.locator("tr", has_text="IF201").count() == 2
          and page.locator("tr", has_text="IF315").count() == 1)

    cnt_btn = page.locator("button", has_text="aldy@nilai.test").first
    m = re.search(r"(\d+) kelas", cnt_btn.inner_text())
    pre_n = int(m.group(1)) if m else -1

    def benr():
        return psql("SELECT count(*) FROM enrollments WHERE course_id='%s' AND student_id='%s'"
                    % (CB_B, U_ALDY))

    def bpoll(want):
        for _ in range(30):
            if benr() == want:
                return True
            time.sleep(0.2)
        return False

    pre_e = benr()
    page.locator('input[aria-label="Daftarkan ke IF201 kelas B"]').click()
    first = "0" if pre_e == "1" else "1"
    ok_first = bpoll(first) and benr() == first
    if pre_e == "0":
        check("placement enrolls into class B", ok_first)
        target_n = pre_n + 1
    else:
        check("placement unenrolls from class B", ok_first)
        target_n = pre_n - 1
    if pre_n >= 0:
        page.wait_for_function(
            "txt => document.body.innerText.includes(txt)",
            arg="%d kelas" % target_n, timeout=5000)
        check("placement student count refreshes",
              "%d kelas" % target_n in page.inner_text("body"))

    page.locator('input[aria-label="Daftarkan ke IF201 kelas B"]').click()
    bpoll(pre_e)
    if pre_e == "0":
        check("placement unenrolls from class B (net-zero)", benr() == pre_e)
    else:
        check("placement re-enrolls into class B (net-zero)", benr() == pre_e)

    # --- branding: Aplikasi tab (rename, logo, remove, revert) ---
    import base64

    def appset():
        return psql("SELECT app_name || '|' || footer_text || '|' || "
                    "coalesce(logo_type, '-') FROM app_settings WHERE id=1")

    def poll_appset(want, n=40):
        for _ in range(n):
            if appset() == want:
                return True
            time.sleep(0.25)
        return False

    page.goto(BASE + "/admin/branding", wait_until="networkidle")
    page.fill("#b-name", "Branding Uji")
    page.fill("#b-footer", "Footer Uji")
    submit(page, lambda: page.click("button:has-text('Simpan')"))
    check("branding rename + footer saved",
          poll_appset("Branding Uji|Footer Uji|-"), appset())
    page.wait_for_selector("text=Pengaturan aplikasi disimpan", timeout=10000)
    check("save notice shown", True)

    page.goto(BASE + "/admin", wait_until="networkidle")
    body = page.inner_text("body")
    check("shell reflects new brand",
          "Branding Uji" in body and "Footer Uji" in body)
    check("browser title uses app name",
          page.title() == "Branding Uji", page.title())

    page.goto(BASE + "/admin/branding", wait_until="networkidle")
    PNG_1PX = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQ"
        "GAhKmMIQAAAABJRU5ErkJggg==")
    page.set_input_files("#b-logo", {
        "name": "logo.png", "mimeType": "image/png", "buffer": PNG_1PX})
    submit(page, lambda: page.click("button:has-text('Simpan')"))
    check("logo upload stored",
          poll_appset("Branding Uji|Footer Uji|image/png"), appset())
    page.wait_for_selector('img[src*="/logo"]', timeout=10000)
    check("branding preview shows logo image",
          page.locator('img[src*="/logo"]').count() > 0)

    page.goto(BASE + "/admin", wait_until="networkidle")
    check("navbar uses uploaded logo",
          page.locator('img[src*="/logo"]').count() >= 1)

    page.goto(BASE + "/admin/branding", wait_until="networkidle")
    page.set_input_files("#b-logo", [])
    page.check("input[name=remove_logo]")
    submit(page, lambda: page.click("button:has-text('Simpan')"))
    check("remove logo clears image",
          poll_appset("Branding Uji|Footer Uji|-"), appset())
    page.goto(BASE + "/admin", wait_until="networkidle")
    check("navbar back to letter after logo removal",
          page.locator('img[src*="/logo"]').count() == 0)

    page.goto(BASE + "/admin/branding", wait_until="networkidle")
    page.fill("#b-name", "MiniCourse")
    page.fill("#b-footer", "")
    submit(page, lambda: page.click("button:has-text('Simpan')"))
    check("branding reverted to defaults",
          poll_appset("MiniCourse||-"), appset())

    # --- Excel import: preview -> confirm -> cleanup ---
    import io as _io

    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Pengguna"
    ws.append(["Nama", "Email", "Peran", "Status"])
    ws.append(["Uji Walkthrough", "walkthrough.impor@nilai.test", "mahasiswa", "aktif"])
    ws.append(["Ismail Saputra", "ismail@nilai.test", "dosen", "aktif"])
    ws.append(["Tanpa Email", "", "mahasiswa", "aktif"])
    _buf = _io.BytesIO()
    wb.save(_buf)
    fixture = _buf.getvalue()

    page.goto(BASE + "/admin/users", wait_until="networkidle")
    page.click("a:has-text('Impor Excel')")
    page.wait_for_selector("input[type=file]", timeout=5000)
    page.set_input_files("input[type=file]", {
        "name": "impor.xlsx",
        "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "buffer": fixture})
    submit(page, lambda: page.click("button:has-text('Pratinjau')"))
    page.wait_for_selector("text=baris terbaca", timeout=10000)
    body = page.inner_text("body")
    check("preview classifies rows",
          "3 baris terbaca" in body and "1 siap diimpor" in body
          and "1 dilewati" in body and "1 gagal" in body,
          body[body.find("baris terbaca") - 8:][:80])

    submit(page, lambda: page.click("button:has-text('Konfirmasi impor')"))
    page.wait_for_selector("text=pengguna ditambahkan", timeout=10000)
    body = page.inner_text("body")
    check("confirm result summary",
          "1 pengguna ditambahkan" in body and "1 dilewati" in body)
    check("imported user visible in table",
          page.locator("tr", has_text="walkthrough.impor@nilai.test").count() > 0)
    check("imported user persisted with defaults",
          psql("SELECT name || '|' || role || '|' || status FROM users "
               "WHERE email='walkthrough.impor@nilai.test'")
          == "Uji Walkthrough|student|active")

    psql("DELETE FROM users WHERE email='walkthrough.impor@nilai.test'")
    check("import cleanup (net-zero)",
          psql("SELECT count(*) FROM users WHERE email='walkthrough.impor@nilai.test'")
          == "0")

    # --- lecturer: card meta + read-only pengaturan ---
    ctx.clear_cookies()
    login(page, "ramadan@nilai.test")
    page.goto(BASE + "/lecturer/courses", wait_until="networkidle")
    body = page.inner_text("body")
    check("lecturer cards show Kelas + Periode",
          "Kelas A" in body and "2025/2026 Ganjil" in body)

    page.goto(BASE + "/lecturer/courses/" + C_BD + "/pengaturan", wait_until="networkidle")
    body = page.inner_text("body")
    check("pengaturan read-only notice",
          "diatur oleh admin" in body)
    low = body.lower()
    check("pengaturan shows Periode + Kelas",
          "periode" in low and "kelas" in low and "2025/2026 ganjil" in low)
    n_ctrl = page.locator("input:not([type=hidden]), textarea, select").count()
    check("pengaturan has no editable controls", n_ctrl == 0, n_ctrl)

    # --- student: card meta ---
    ctx.clear_cookies()
    login(page, "miratil@nilai.test")
    page.goto(BASE + "/student/courses", wait_until="networkidle")
    body = page.inner_text("body")
    check("student cards show Kelas + Periode",
          "Kelas A" in body and "2025/2026 Ganjil" in body)

    browser.close()

fails = [r for r in results if not r[1]]
print("\n%d/%d passed" % (len(results) - len(fails), len(results)))
sys.exit(1 if fails else 0)
