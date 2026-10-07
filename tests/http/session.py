"""Live-server session helper for the Django app (Phase 6 e2e scripts).

Replaces the old Next.js HMAC cookie helper: performs a real form login,
carries the Django session/csrf cookie jar, and posts forms with
csrfmiddlewaretoken like a browser would.
"""

import re
import urllib.error
import urllib.parse
import urllib.request

BASE = "http://localhost:3001"


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_no_redirect = urllib.request.build_opener(_NoRedirect)


def _abs(base, path):
    return path if path.startswith("http") else base.rstrip("/") + path


def _cookie_header(jar):
    return "; ".join(f"{k}={v}" for k, v in jar.items())


def _absorb(headers, jar):
    for sc in headers.get_all("Set-Cookie") or []:
        kv = sc.split(";")[0].strip()
        if "=" not in kv:
            continue
        name, value = kv.split("=", 1)
        name = name.strip()
        if value:
            jar[name] = value.strip()
        else:
            jar.pop(name, None)


class Session:
    def __init__(self, base=BASE):
        self.base = base.rstrip("/")
        self.jar = {}
        self.last_location = None

    def _open(self, url, data, headers, method, follow):
        opener = urllib.request.build_opener() if follow else _no_redirect
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            resp = opener.open(req, timeout=30)
            _absorb(resp.headers, self.jar)
            return resp.status, resp.read().decode(errors="replace")
        except urllib.error.HTTPError as e:
            _absorb(e.headers, self.jar)
            return e.code, e.read().decode(errors="replace")

    def request(self, path, data=None, headers=None, method=None, follow=True):
        """Single request; when follow=True redirects are walked manually so
        Set-Cookie (sessionid / nilai_flash) lands in the jar."""
        url = _abs(self.base, path)
        hdrs = {"Cookie": _cookie_header(self.jar)}
        if headers:
            hdrs.update(headers)
        body = data
        meth = method or ("POST" if body is not None else "GET")
        for _ in range(8):
            req = urllib.request.Request(url, data=body, headers=hdrs, method=meth)
            try:
                resp = _no_redirect.open(req, timeout=30)
                _absorb(resp.headers, self.jar)
                self.last_location = None
                return resp.status, resp.read().decode(errors="replace")
            except urllib.error.HTTPError as e:
                _absorb(e.headers, self.jar)
                code, text = e.code, e.read().decode(errors="replace")
                loc = e.headers.get("Location")
                self.last_location = loc
                if not follow or code not in (301, 302, 303, 307, 308) or not loc:
                    return code, text
                url = urllib.parse.urljoin(url, loc)
                body = None
                meth = "GET"
                hdrs.pop("Content-Type", None)
                hdrs.pop("Origin", None)
                hdrs.pop("Referer", None)
                hdrs["Cookie"] = _cookie_header(self.jar)
        raise SystemExit("too many redirects: " + path)

    def get(self, path, follow=True):
        return self.request(path, follow=follow)

    def csrf(self, page):
        m = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', page or "")
        if m:
            return m.group(1)
        return self.jar.get("csrftoken", "")

    def post(self, path, fields=None, files=None, page=None, follow=True):
        """Multipart form post. `page` = HTML of the form page (fetched when
        omitted) used to pick up the per-form csrfmiddlewaretoken."""
        fields = dict(fields or {})
        if "csrfmiddlewaretoken" not in fields:
            if page is None:
                _, page = self.get(path)
            fields["csrfmiddlewaretoken"] = self.csrf(page)

        boundary = "----boundary-dj" + str(id(fields)) + str(len(fields))
        chunks = []

        def add(name, value):
            chunks.append(("--%s\r\n" % boundary).encode())
            chunks.append(
                ('Content-Disposition: form-data; name="%s"\r\n\r\n' % name).encode()
            )
            chunks.append(value if isinstance(value, bytes) else str(value).encode())
            chunks.append(b"\r\n")

        for name, value in fields.items():
            add(name, value)
        for name, (fname, data, ctype) in (files or {}).items():
            chunks.append(("--%s\r\n" % boundary).encode())
            chunks.append(
                (
                    'Content-Disposition: form-data; name="%s"; filename="%s"\r\n'
                    "Content-Type: %s\r\n\r\n" % (name, fname, ctype)
                ).encode()
            )
            chunks.append(data)
            chunks.append(b"\r\n")
        chunks.append(("--%s--\r\n" % boundary).encode())

        origin = urllib.parse.urlsplit(self.base).scheme + "://" + urllib.parse.urlsplit(
            self.base
        ).netloc
        return self.request(
            path,
            data=b"".join(chunks),
            headers={
                "Content-Type": "multipart/form-data; boundary=" + boundary,
                "Origin": origin,
                "Referer": origin + path,
            },
            follow=follow,
        )

    def login(self, email, password="password123"):
        status, page = self.get("/login")
        if "csrfmiddlewaretoken" not in (page or ""):
            raise SystemExit("login page has no csrf token: " + email)
        self.post(
            "/login",
            {"email": email, "password": password},
            page=page,
            follow=True,
        )
        if "sessionid" not in self.jar:
            raise SystemExit("login failed: " + email)
        return self


def login(email, password="password123", base=BASE):
    return Session(base).login(email, password)
