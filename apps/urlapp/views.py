import random
from string import ascii_letters, digits

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import IntegrityError
from django.db.models import F
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import ListView

from apps.metrics.models import record_click

from .models import ShortLink


def index(request):
    return render(request, "urlapp/index.html")


def shorten_url(request):
    if request.method == "POST":
        url = request.POST.get("url", "").strip()
        if not url:
            return JsonResponse({"error": "URL is required"}, status=400)
        validator = URLValidator(schemes=["http", "https"])
        try:
            validator(url)
        except ValidationError:
            return JsonResponse({"error": "Enter a valid http or https URL"}, status=400)

        code = rand_N_symb(6)
        author = None
        if request.user.is_authenticated:
            try:
                author = request.user.profile
            except Exception:
                author = None

        link = ShortLink(code=code, given_url=url, author=author)
        try:
            link.save()
        except IntegrityError:
            code = rand_N_symb(6)
            link.code = code
            link.save()

        response_data = {"url": f"{request.scheme}://{request.get_host()}/{link.code}"}
        return JsonResponse(response_data)
    return redirect("urlapp:index")


def rand_N_symb(N):
    alph = digits + ascii_letters
    while True:
        # SystemRandom() - *nix; CryptGenRandom() - Windows
        code = "".join(random.SystemRandom().choice(alph) for _ in range(N))
        if not ShortLink.objects.filter(code=code).exists():
            return code


def redirect_to_long(request, code):
    link = get_object_or_404(ShortLink, code=code)
    record_click(request, link)
    ShortLink.objects.filter(pk=link.pk).update(visit_count=F("visit_count") + 1)
    return redirect(link.given_url)


class NobodysSurlListView(ListView):
    model = ShortLink
    template_name = "urlapp/surls.html"
    context_object_name = "surls"

    def get_queryset(self):
        return ShortLink.objects.filter(author=None).order_by("-visit_count", "-created_date")


class UserSurlListView(LoginRequiredMixin, ListView):
    model = ShortLink
    template_name = "urlapp/surls.html"
    context_object_name = "surls"

    def get_queryset(self):
        return ShortLink.objects.filter(author=self.request.user.profile).order_by(
            "-visit_count", "-created_date"
        )
