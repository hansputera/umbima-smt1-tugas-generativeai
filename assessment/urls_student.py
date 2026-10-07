from django.urls import path

from . import views_student

urlpatterns = [
    path(
        "assignments/<uuid:assignment_id>",
        views_student.assignment_detail,
        name="student_assignment",
    ),
]
