from django.db import models
from django.contrib.auth.models import User


class Surl(models.Model):
    short_url = models.SlugField(max_length=6, primary_key=True)
    given_url = models.URLField(max_length=300)
    visit_count = models.IntegerField(default=0)
    creat_date = models.DateTimeField(auto_now=True)
    author = models.ForeignKey(User, related_name='user',
                    on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return self.given_url
    

