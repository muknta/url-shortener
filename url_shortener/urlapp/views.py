from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from urlapp.models import Surl
from django.http import JsonResponse
from django.views.generic import ListView
from string import digits, ascii_letters
import random


def index(request):
    return render(request, "urlapp/index.html")

def shorten_url(request):
    if request.method == "POST":
        url = request.POST.get("url", '')
        short_url = rand_N_symb(6)
        if request.user.is_authenticated:
            surl = Surl(author=request.user, given_url=url, short_url=short_url)
        else:
            surl = Surl(given_url=url, short_url=short_url)
        surl.save()

        response_data = {}
        response_data['url'] = f"{request.scheme}://{request.get_host()}/{short_url}"
        return JsonResponse(response_data)
    return redirect("index")
 
def rand_N_symb(N):
    alph = digits + ascii_letters
    while True:
        # SystemRandom() - *nix; CryptGenRandom() - Windows
        short_url = ''.join(random.SystemRandom().choice(alph) for _ in range(N))
        try:
            surl = Surl.objects.get(pk=short_url)
        except Surl.DoesNotExist:
            return short_url

def redirect_to_long(request, short_url):
    surl = get_object_or_404(Surl, pk=short_url)
    surl.visit_count += 1
    surl.save()
    return redirect(surl.given_url)


class NobodysSurlListView(ListView):
    model = Surl
    template_name = "urlapp/surls.html"
    context_object_name = "surls"

    def get_queryset(self):
        context = Surl.objects.filter(
                author=None).order_by('-visit_count', '-creat_date')
        return context


class UserSurlListView(LoginRequiredMixin, ListView):
    model = Surl
    template_name = "urlapp/surls.html"
    context_object_name = "surls"

    def get_queryset(self):
        context = Surl.objects.filter(
                author=self.request.user).order_by('-visit_count', '-creat_date')
        return context
    

