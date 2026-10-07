from django.urls import path

from . import views_admin

urlpatterns = [
    path("periods", views_admin.periods_page),
    path("placement", views_admin.placement_page),
    path("courses", views_admin.courses_page),
    path("courses/<uuid:course_id>", views_admin.course_detail),
]
