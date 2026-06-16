from django.conf import settings
from django.core.validators import URLValidator
from django.db import models
from uuid6 import uuid7

from apps.metrics.models import VisitorMetadata


class ShortLink(VisitorMetadata):
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    code = models.SlugField(max_length=20, unique=True, db_index=True)
    given_url = models.URLField(
        max_length=500, validators=[URLValidator(schemes=["http", "https"])]
    )
    visit_count = models.IntegerField(default=0)
    created_date = models.DateTimeField(auto_now_add=True)
    # Ownership only — null for anonymous creators. Creation context (IP/UA/etc.)
    # lives in the inherited VisitorMetadata fields so anon creators are still tracked.
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="links",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["-visit_count", "-created_date"],
                name="urlapp_shortlink_visit_c_idx",
            )
        ]

    def __str__(self):
        return self.given_url
