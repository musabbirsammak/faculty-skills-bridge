from django.conf import settings

from .models import Institution


def institution(request):
    """Makes the running university's details available to every template."""
    return {"institution": Institution.load(), "privacy_min_group": settings.PRIVACY_MIN_GROUP}
