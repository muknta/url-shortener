from django.shortcuts import render, redirect, get_object_or_404
from urlapp.models import Surl
from django.http import HttpResponse
from string import digits, ascii_letters
import random, json


def index(request):
    return render(request, "urlapp/index.html")

def shorten_url(request):
    if request.method == "POST":
        url = request.POST.get("url", '')
        if url != '':
            short_url = rand_N_symb(6)
            surl = Surl(given_url=url, short_url=short_url)
            surl.save()
     
            response_data = {}
            response_data['url'] = f"{request.get_host()}/{short_url}"
            return HttpResponse(json.dumps(response_data), content_type="application/json")
        return HttpResponse(json.dumps({"error": "empty link"}),
             content_type="application/json")
    else:
        return redirect("index")
 
def rand_N_symb(N):
    alph = digits + ascii_letters
    while True:
        short_url = ''.join(random.SystemRandom().choice(alph) for _ in range(N))
        try:
            surl = Surl.objects.get(pk=short_url)
        except:
            return short_url

def redirect_to_long(request, short_url):
    surl = get_object_or_404(Surl, pk=short_url)
    surl.visit_count += 1
    surl.save()
    return redirect(surl.given_url)

