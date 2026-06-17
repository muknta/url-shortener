from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.urls import path
from django.views.decorators.csrf import ensure_csrf_cookie

from . import api
from .views import redirect_to_long

app_name = "urlapp"


@ensure_csrf_cookie
def shell_view(request):
    return render(request, "urlapp/app.html")


urlpatterns = [
    path("", shell_view, name="index"),
    path("nobodys-urls/", shell_view, name="nobodys-surls"),
    path("my-urls/", login_required(shell_view), name="user-surls"),
    # API
    path("api/shorten/", api.api_shorten, name="api-shorten"),
    path("api/urls/public/", api.api_public_urls, name="api-public-urls"),
    path("api/urls/mine/", api.api_my_urls, name="api-my-urls"),
    # Redirect — keep last so explicit routes win
    path("<slug:code>/", redirect_to_long, name="redirect-to-long"),
]
