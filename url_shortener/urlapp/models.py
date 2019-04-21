from django.db import models


class Surl(models.Model):
    given_url = models.URLField(max_length=300)
    short_url = models.SlugField(max_length=6, primary_key=True)
    visit_count = models.IntegerField(default=0)
    creat_date = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.given_url
    

