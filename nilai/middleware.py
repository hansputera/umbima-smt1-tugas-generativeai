ROLE_HOME = {"admin": "/admin", "lecturer": "/lecturer/home", "student": "/student/home"}
ROLE_PREFIXES = ("admin", "lecturer", "student")


class ProxyMiddleware:
    """Route guard mirroring src/proxy.ts rules."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        if path in ("/logo", "/favicon.ico"):
            return self.get_response(request)

        user = getattr(request, "user", None)
        active = bool(
            user is not None
            and getattr(user, "is_authenticated", False)
            and getattr(user, "status", None) == "active"
        )
        role = user.role if active else None

        if path == "/login":
            if active:
                from django.shortcuts import redirect

                return redirect(ROLE_HOME[role])
            return self.get_response(request)

        from django.shortcuts import redirect

        if path == "/":
            if active:
                return redirect(ROLE_HOME[role])
            return redirect("/login")

        if not active:
            return redirect("/login")

        first = path.lstrip("/").split("/", 1)[0]
        if first in ROLE_PREFIXES and first != role:
            return redirect(ROLE_HOME[role])

        return self.get_response(request)
