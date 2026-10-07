from django.urls import include, path

from accounts.views import admin_home, login_view, logout_view

from . import views

# Route spellings mirror the Next.js app exactly: no trailing slashes.
urlpatterns = [
    path("", views.root),
    path("logo", views.logo, name="logo"),
    path("favicon.ico", views.favicon),
    path("login", login_view, name="login"),
    path("logout", logout_view, name="logout"),
    path("admin", admin_home, name="admin_home"),
    path("admin/", include("accounts.urls")),
    path("admin/", include("academics.urls")),
    path("lecturer/", include("academics.urls_lecturer")),
    path("lecturer/", include("assessment.urls_lecturer")),
    path("student/", include("academics.urls_student")),
    path("student/", include("assessment.urls_student")),
]


def handler404(request, exception=None):
    from django.http import HttpResponseNotFound

    return HttpResponseNotFound("Halaman tidak ditemukan.")
