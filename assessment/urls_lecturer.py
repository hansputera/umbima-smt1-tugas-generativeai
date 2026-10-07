from django.urls import path

from . import views, views_lecturer

urlpatterns = [
    path("home", views.lecturer_home, name="lecturer_home"),
    path(
        "assignments/<uuid:assignment_id>",
        views_lecturer.assignment_detail,
        name="lecturer_assignment_detail",
    ),
    path("submissions", views_lecturer.submissions_inbox, name="lecturer_submissions"),
    path(
        "submissions/<uuid:submission_id>",
        views_lecturer.submission_detail,
        name="lecturer_submission_detail",
    ),
]
