from django.db import models
from django.urls import reverse
from .basechanger import decimal2base_n, base_n2decimal


class Surl(models.Model):
    given_url = models.URLField(max_length=300)

    @staticmethod
    def shorten(link):
        l, _ = Surl.objects.get_or_create(given_url=link.given_url)
        return str(decimal2base_n(l.pk))

    @staticmethod
    def expand(slug):
        link_id = int(base_n2decimal(slug))
        l = Surl.objects.get(pk=link_id)
        return l.given_url

    def get_absolute_url(self):
        return reverse('surl-detail', kwargs={'pk': self.pk})


    def short_url(self):
        return reverse("redirect_short_url",
                   kwargs={"short_url": Surl.shorten(self)})

