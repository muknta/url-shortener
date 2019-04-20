from django.db import models
from django.urls import reverse
import random
from string import ascii_letters, digits


class Surl(models.Model):
    def rand_N_symb():
        N = 6
        # SystemRandom() - *nix; CryptGenRandom() - Windows
        return ''.join(random.SystemRandom().choice(digits+ascii_letters) for _ in range(N))

    given_url = models.CharField(max_length=300)
    short_url = '%s' %(rand_N_symb(),)

    def get_absolute_url(self):
        return reverse('surl-detail', kwargs={'short_url': self.short_url})


