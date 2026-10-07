from playwright.sync_api import sync_playwright
import sys

BASE = "http://localhost:3001"
results = []
def check(name, ok, extra=""):
    results.append((name, ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else " -> " + extra))

def submit(page, email, pw):
    with page.expect_response(lambda r: r.request.method == "POST") as resp_info:
        page.click("button[type=submit]")
    return resp_info.value

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=True)
    page = browser.new_page()

    # 1. Login page must not expose any user identity
    page.goto(BASE + "/login", wait_until="networkidle")
    body = page.inner_text("body")
    html = page.content()
    leaks = [s for s in ["Nur Audyah", "Ramadan Agung", "Aldy", "Miratil", "Ismail", "Fitri",
                          "audyah@", "ramadan@", "aldy@", "miratil@", "ismail@", "fitri@",
                          "Peran", "<option"] if s.lower() in body.lower() or s in html]
    check("no user/role exposure on login page", not leaks, "leaked: " + ", ".join(leaks))
    check("has email + password fields",
          page.locator("input[name=email]").count() == 1 and page.locator("input[name=password]").count() == 1)

    # 2. Wrong password -> generic error (await the POST response, then the text)
    page.fill("input[name=email]", "ramadan@nilai.test")
    page.fill("input[name=password]", "wrongpass")
    with page.expect_response(lambda r: r.request.method == "POST"):
        page.click("button[type=submit]")
    page.wait_for_selector("text=Email atau kata sandi salah", timeout=8000)
    check("wrong password shows generic error", True)

    # 3. Unknown email -> same generic error (no user enumeration)
    page.fill("input[name=email]", "nobody@nilai.test")
    page.fill("input[name=password]", "password123")
    with page.expect_response(lambda r: r.request.method == "POST"):
        page.click("button[type=submit]")
    page.wait_for_selector("text=Email atau kata sandi salah", timeout=8000)
    check("unknown email shows same generic error", True)

    # 4. Correct credentials -> session + redirect (lecturer)
    page.fill("input[name=email]", "ramadan@nilai.test")
    page.fill("input[name=password]", "password123")
    page.wait_for_timeout(300)  # let React settle from the previous action
    with page.expect_response(lambda r: r.request.method == "POST"):
        page.click("button[type=submit]")
    page.wait_for_url("**/lecturer/home", timeout=20000)
    check("lecturer login redirects + greets", "Ramadan" in page.inner_text("body"), page.url)

    # 5. Student login (fresh session — /login bounces authed users to their home)
    page.context.clear_cookies()
    page.goto(BASE + "/login", wait_until="networkidle")
    page.fill("input[name=email]", "miratil@nilai.test")
    page.fill("input[name=password]", "password123")
    with page.expect_response(lambda r: r.request.method == "POST"):
        page.click("button[type=submit]")
    page.wait_for_url("**/student/home", timeout=20000)
    check("student login works", "Mir'atil" in page.inner_text("body"))

    # 6. Admin login
    page.context.clear_cookies()
    page.goto(BASE + "/login", wait_until="networkidle")
    page.fill("input[name=email]", "audyah@nilai.test")
    page.fill("input[name=password]", "password123")
    with page.expect_response(lambda r: r.request.method == "POST"):
        page.click("button[type=submit]")
    page.wait_for_url("**/admin", timeout=20000)
    check("admin login works", True, page.url)

    # 7. Session persists across reload
    page.reload(wait_until="networkidle")
    check("session persists after reload", "/login" not in page.url, page.url)

    # 8. Password input is masked
    page.context.clear_cookies()
    page.goto(BASE + "/login", wait_until="networkidle")
    check("password field is type=password",
          page.get_attribute("input[name=password]", "type") == "password")

    browser.close()

fails = [n for n, ok in results if not ok]
print(f"{len(results)-len(fails)}/{len(results)} passed")
sys.exit(1 if fails else 0)
