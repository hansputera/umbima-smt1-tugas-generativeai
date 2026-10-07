from django.urls import path

from . import views_lecturer

urlpatterns = [
    path("courses", views_lecturer.courses_page),
    path("courses/<uuid:course_id>", views_lecturer.course_page),
    path("courses/<uuid:course_id>/peserta", views_lecturer.peserta_page),
    path("courses/<uuid:course_id>/tugas", views_lecturer.tugas_page),
    path("courses/<uuid:course_id>/nilai", views_lecturer.nilai_page),
    path("courses/<uuid:course_id>/pengaturan", views_lecturer.pengaturan_page),
    path(
        "courses/<uuid:course_id>/topics/<uuid:topic_id>",
        views_lecturer.topic_detail,
    ),
]
