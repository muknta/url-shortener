from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone as dj_tz

from apps.metrics.models import ClickEvent


class Command(BaseCommand):
    help = "Delete ClickEvent rows older than METRICS_RETENTION_DAYS (default 1000)"

    def handle(self, *args, **options):
        retention_days = getattr(settings, "METRICS_RETENTION_DAYS", 1000)
        cutoff = dj_tz.now() - timedelta(days=retention_days)
        deleted, _ = ClickEvent.objects.filter(clicked_at__lt=cutoff).delete()
        self.stdout.write(f"Purged {deleted} click event(s) older than {retention_days} days.")
