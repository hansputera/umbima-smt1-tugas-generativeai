from django.shortcuts import redirect, render

from academics.lib import course_cards, get_lecturer, upcoming_all, with_card_meta


def lecturer_home(request):
    """Port of src/app/lecturer/home/page.tsx."""
    lecturer = get_lecturer(request)
    if lecturer is None:
        return redirect("/login")
    return render(
        request,
        "lecturer/home.html",
        {
            "cards": with_card_meta(course_cards(lecturer)),
            "upcoming": upcoming_all(lecturer),
            "crumbs": [{"label": "Beranda"}],
        },
    )
