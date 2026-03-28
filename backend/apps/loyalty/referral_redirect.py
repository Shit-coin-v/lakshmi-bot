"""Public referral landing page — shows code + store links."""

from django.conf import settings
from django.http import Http404
from django.shortcuts import render

from apps.main.models import CustomUser


def referral_landing(request, code):
    """GET /ref/<code>/ — public page with referral code + app store links."""
    if not CustomUser.objects.filter(referral_code=code).exists():
        raise Http404

    return render(request, "referral/landing.html", {
        "referral_code": code,
        "appstore_url": getattr(settings, "APPSTORE_URL", ""),
        "google_play_url": getattr(settings, "GOOGLE_PLAY_URL", ""),
    })
