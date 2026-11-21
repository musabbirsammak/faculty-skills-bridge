from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .models import Notification


@login_required
def notification_list(request):
    return render(request, "notifications/list.html", {
        "notifications": request.user.notifications.all()[:100],
    })


@login_required
def notification_open(request, pk):
    note = get_object_or_404(Notification, pk=pk, recipient=request.user)
    if note.read_at is None:
        note.read_at = timezone.now()
        note.save(update_fields=["read_at"])
    if note.url and url_has_allowed_host_and_scheme(note.url, allowed_hosts={request.get_host()}):
        return redirect(note.url)
    return redirect("notifications:list")


@login_required
@require_POST
def mark_all_read(request):
    request.user.notifications.filter(read_at__isnull=True).update(read_at=timezone.now())
    return redirect("notifications:list")
