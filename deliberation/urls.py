from django.urls import path

from . import views

app_name = "deliberation"

urlpatterns = [
    path("proposals/", views.document_list, {"kind": "policy"}, name="proposals"),
    path("proposals/new/", views.document_create, {"kind": "policy"}, name="proposal_create"),
    path("studio/", views.document_list, {"kind": "redesign"}, name="studio"),
    path("studio/new/", views.document_create, {"kind": "redesign"}, name="redesign_create"),
    path("documents/<int:pk>/", views.document_detail, name="detail"),
    path("documents/<int:pk>/edit/", views.document_edit, name="edit"),
    path("documents/<int:pk>/status/", views.document_status, name="status"),
    path("documents/<int:pk>/stance/", views.stance, name="stance"),
    path("documents/<int:pk>/comment/", views.comment_create, name="comment"),
    path("documents/<int:pk>/sections/add/", views.section_add, name="section_add"),
    path("sections/<int:pk>/edit/", views.section_edit, name="section_edit"),
    path("sections/<int:pk>/history/", views.section_history, name="section_history"),
    path("comments/<int:pk>/resolve/", views.comment_resolve, name="comment_resolve"),
]
