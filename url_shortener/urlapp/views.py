from django.shortcuts import render, redirect
from urlapp.models import Surl
from django.views.generic import (
    DetailView,
    CreateView
)


def index(request):
    return render(request, "urlapp/index.html")

def surl_detail(request, given_url):
    return redirect(given_url)


class SurlDetailView(DetailView):
    model = Surl
   

class SurlCreateView(CreateView):
    model = Surl
    fields = ["given_url"]

