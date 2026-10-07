from django.urls import path

from . import views_student

urlpatterns = [
    path("home", views_student.home, name="student_home"),
    path("courses", views_student.courses, name="student_courses"),
    path("courses/<uuid:course_id>", views_student.course_page, name="student_course"),
    path(
        "courses/<uuid:course_id>/tugas",
        views_student.tugas_page,
        name="student_tugas",
    ),
    path(
        "courses/<uuid:course_id>/nilai",
        views_student.nilai_page,
        name="student_nilai",
    ),
    path(
        "courses/<uuid:course_id>/peserta",
        views_student.peserta_page,
        name="student_peserta",
    ),
    path(
        "courses/<uuid:course_id>/topics/<uuid:topic_id>",
        views_student.topic_page,
        name="student_topic",
    ),
    path("tasks", views_student.tasks, name="student_tasks"),
]
