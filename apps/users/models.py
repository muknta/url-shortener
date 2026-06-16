from django.contrib.auth.models import User
from django.db import models

from apps.metrics.models import VisitorMetadata


class Profile(VisitorMetadata):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # When the login-origin snapshot was last refreshed (overwritten, not history)
    origin_updated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} Profile"
