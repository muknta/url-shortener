from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone as dj_tz

from apps.metrics.models import EnrichmentStatus, extract_request_metadata

from .models import Profile


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_profile(sender, instance, **kwargs):
    instance.profile.save()


@receiver(user_logged_in)
def refresh_profile_snapshot(sender, request, user, **kwargs):
    """Refresh the Profile's connection snapshot on login, but only when the IP changes."""
    try:
        profile = user.profile
    except Profile.DoesNotExist:
        return

    metadata = extract_request_metadata(request)
    new_ip = metadata.get("ip_address")

    if new_ip and new_ip == profile.ip_address:
        return

    profile.ip_address = new_ip
    profile.user_agent = metadata.get("user_agent", "")
    profile.accept_language = metadata.get("accept_language", "")
    profile.referrer = metadata.get("referrer", "")
    profile.origin_updated_at = dj_tz.now()
    profile.enrichment_status = EnrichmentStatus.PENDING
    profile.enriched_at = None
    profile.save(
        update_fields=[
            "ip_address",
            "user_agent",
            "accept_language",
            "referrer",
            "origin_updated_at",
            "enrichment_status",
            "enriched_at",
        ]
    )
