from django.http import HttpResponse, HttpResponseNotFound
from django.shortcuts import redirect
from django.conf import settings

from accounts.models import AppSettings


def root(request):
    return redirect("login")


def favicon(request):
    path = settings.BASE_DIR / "static" / "favicon.ico"
    if not path.exists():
        return HttpResponseNotFound()
    return HttpResponse(path.read_bytes(), content_type="image/x-icon")


def logo(request):
    """Port of src/app/logo/route.ts."""
    row = AppSettings.objects.filter(pk=1).first()
    if not row or not row.logo or not row.logo_type:
        return HttpResponseNotFound("Logo tidak tersedia")
    response = HttpResponse(bytes(row.logo), content_type=row.logo_type)
    response["Cache-Control"] = "public, max-age=31536000, immutable"
    return response
