from django.conf import settings
from django.db import models
from uuid6 import uuid7


class EnrichmentStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    DONE = "DONE", "Done"
    FAILED = "FAILED", "Failed"


class VisitorMetadata(models.Model):
    # Captured immediately from the request
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")
    accept_language = models.CharField(max_length=255, blank=True, default="")
    referrer = models.TextField(blank=True, default="")

    # Filled later by the enrichment batch job
    country_code = models.CharField(max_length=2, blank=True, default="")
    region = models.CharField(max_length=128, blank=True, default="")
    city = models.CharField(max_length=128, blank=True, default="")
    timezone = models.CharField(max_length=64, blank=True, default="")
    isp = models.CharField(max_length=255, blank=True, default="")
    asn = models.CharField(max_length=64, blank=True, default="")
    is_proxy = models.BooleanField(null=True)
    is_hosting = models.BooleanField(null=True)
    is_mobile = models.BooleanField(null=True)
    enrichment_status = models.CharField(
        max_length=10,
        choices=EnrichmentStatus.choices,
        default=EnrichmentStatus.PENDING,
        db_index=True,
    )
    enriched_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True


class ClickEvent(VisitorMetadata):
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    clicked_at = models.DateTimeField(auto_now_add=True, db_index=True)
    short_link = models.ForeignKey(
        "urlapp.ShortLink",
        on_delete=models.CASCADE,
        related_name="clicks",
    )
    # Points at User (not Profile) to avoid .profile lookup on the hot redirect path
    accessed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="clicks",
    )

    class Meta:
        ordering = ["-clicked_at"]
        indexes = [models.Index(fields=["short_link", "-clicked_at"])]

    def __str__(self):
        return f"Click on {self.short_link_id} at {self.clicked_at}"


def extract_request_metadata(request):
    """Extract visitor metadata fields from an HTTP request."""
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    # First hop of X-Forwarded-For (trustworthy only behind a known proxy such as Render)
    ip_address = xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR")
    return {
        "ip_address": ip_address or None,
        "user_agent": request.META.get("HTTP_USER_AGENT", ""),
        "accept_language": request.META.get("HTTP_ACCEPT_LANGUAGE", ""),
        "referrer": request.META.get("HTTP_REFERER", ""),
    }


def record_click(request, link):
    """Create a ClickEvent for a redirect. Keeps the view thin."""
    metadata = extract_request_metadata(request)
    accessed_by = request.user if request.user.is_authenticated else None
    ClickEvent.objects.create(short_link=link, accessed_by=accessed_by, **metadata)
