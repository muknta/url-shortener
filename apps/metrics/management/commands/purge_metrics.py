from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone as dj_tz

from apps.metrics.models import ClickEvent


class Command(BaseCommand):
    help = (
        "PII retention: delete old ClickEvents; null ip_address on old ShortLink/Profile rows. "
        "Cutoff controlled by METRICS_RETENTION_DAYS (default 1000)."
    )

    def handle(self, *args, **options):
        from apps.urlapp.models import ShortLink
        from apps.users.models import Profile

        retention_days = getattr(settings, "METRICS_RETENTION_DAYS", 1000)
        cutoff = dj_tz.now() - timedelta(days=retention_days)

        # ClickEvent rows are pure event logs — delete them entirely.
        deleted, _ = ClickEvent.objects.filter(clicked_at__lt=cutoff).delete()
        self.stdout.write(f"Deleted {deleted} ClickEvent(s) older than {retention_days} days.")

        # ShortLink and Profile must survive; null the precise identifier instead.
        links_updated = (
            ShortLink.objects.filter(
                created_date__lt=cutoff,
            )
            .exclude(ip_address=None)
            .update(ip_address=None, user_agent="")
        )
        self.stdout.write(
            f"Anonymised {links_updated} ShortLink(s) older than {retention_days} days."
        )

        profiles_updated = (
            Profile.objects.filter(
                enriched_at__lt=cutoff,
            )
            .exclude(ip_address=None)
            .update(ip_address=None, user_agent="")
        )
        self.stdout.write(f"Anonymised {profiles_updated} Profile(s) with stale geo data.")
