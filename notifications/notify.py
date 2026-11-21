"""Send notifications to the people involved in something. Messages never reveal anonymous authors."""
from django.conf import settings
from django.core.mail import send_mail

from .models import Notification


def notify(recipients, message, url="", exclude=None):
    """Create one notification per recipient (users or user ids), skipping `exclude` and inactive users."""
    from django.contrib.auth import get_user_model

    ids = {getattr(r, "pk", r) for r in recipients if r}
    if exclude is not None:
        ids.discard(getattr(exclude, "pk", exclude))
    users = list(get_user_model().objects.filter(pk__in=ids, is_active=True))
    Notification.objects.bulk_create(Notification(recipient=u, message=message[:300], url=url) for u in users)
    if settings.NOTIFY_BY_EMAIL:
        link = settings.SITE_URL.rstrip("/") + url if url else settings.SITE_URL
        for user in users:
            if user.email:
                send_mail(f"Faculty Skills Bridge: {message[:80]}", f"{message}\n\n{link}\n",
                          None, [user.email], fail_silently=True)
    return len(users)
