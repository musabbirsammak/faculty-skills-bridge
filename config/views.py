from django.conf import settings
from django.shortcuts import render

from catalog.models import Course, TeacherSkill
from deliberation.models import Comment, Document


def home(request):
    context = {
        "stats": {
            "courses": Course.objects.count(),
            "teachers": TeacherSkill.objects.values("teacher").distinct().count(),
            "proposals": Document.objects.filter(kind=Document.Kind.POLICY).count(),
            "redesigns": Document.objects.filter(kind=Document.Kind.REDESIGN).count(),
        }
    }
    if request.user.is_authenticated:
        context["recent_comments"] = (
            Comment.objects.select_related("author", "document", "section").order_by("-created")[:6]
        )
        context["has_skills"] = request.user.skills.exists()
    return render(request, "home.html", context)


def privacy(request):
    return render(request, "privacy.html", {"min_group": settings.PRIVACY_MIN_GROUP})
