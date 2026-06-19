from django.db.models import F
from django.shortcuts import get_object_or_404, redirect

from apps.metrics.services import record_click

from .models import ACTIVE, ShortLink


def redirect_to_long(request, code):
    link = get_object_or_404(ShortLink, ACTIVE, code=code)
    record_click(request, link)
    ShortLink.objects.filter(pk=link.pk).update(visit_count=F("visit_count") + 1)
    return redirect(link.given_url)
