from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("mine/", views.my_skills, name="my_skills"),
    path("suggestions/", views.suggestions, name="suggestions"),
    path("feedback/<int:pk>/", views.feedback, name="feedback"),
    path("courses/", views.course_list, name="course_list"),
    path("courses/new/", views.course_create, name="course_create"),
    path("courses/<int:pk>/", views.course_detail, name="course_detail"),
    path("courses/<int:pk>/edit/", views.course_edit, name="course_edit"),
    path("courses/<int:pk>/status/", views.course_status, name="course_status"),
    path("courses/<int:pk>/vote/", views.course_vote, name="course_vote"),
    path("reviews/", views.edit_list, name="edit_list"),
    path("reviews/<int:pk>/", views.edit_review, name="edit_review"),
    path("new-skill/", views.skill_create, name="skill_create"),
    path("insights/", views.dashboard, name="dashboard"),
]
