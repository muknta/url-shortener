from django.contrib.auth.models import User
from django.core.validators import URLValidator
from django.db import models


class Surl(models.Model):
    short_url = models.SlugField(max_length=6, primary_key=True)
    given_url = models.URLField(
        max_length=500, validators=[URLValidator(schemes=["http", "https"])]
    )
    visit_count = models.IntegerField(default=0)
    created_date = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(
        User, related_name="user", on_delete=models.CASCADE, blank=True, null=True
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["-visit_count", "-created_date"],
                name="urlapp_surl_visit_c_74c517_idx",
            )
        ]

    def __str__(self):
        return self.given_url
