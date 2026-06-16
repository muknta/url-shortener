from django.core.validators import URLValidator
from django.db import models
from uuid6 import uuid7


class ShortLink(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    code = models.SlugField(max_length=20, unique=True, db_index=True)
    given_url = models.URLField(
        max_length=500, validators=[URLValidator(schemes=["http", "https"])]
    )
    visit_count = models.IntegerField(default=0)
    created_date = models.DateTimeField(auto_now_add=True)
    # String FK to avoid import cycle (urlapp → users); CASCADE→SET_NULL so deleting a user
    # does not delete their links.
    author = models.ForeignKey(
        "users.Profile",
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
