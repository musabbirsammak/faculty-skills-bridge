from django.contrib import admin
from django.urls import include, path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("privacy/", views.privacy, name="privacy"),
    path("accounts/", include("accounts.urls")),
    path("skills/", include("catalog.urls")),
    path("", include("deliberation.urls")),
    path("notifications/", include("notifications.urls")),
    path("admin/", admin.site.urls),
]
