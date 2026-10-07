from django.urls import path

from . import views, views_admin

urlpatterns = [
    path("", views.admin_home),
    path("users", views_admin.users_page),
    path("users/template", views_admin.users_template),
    path("settings", views_admin.settings_page),
    path("settings/reveal", views_admin.settings_reveal),
    path("branding", views_admin.branding_page),
]
