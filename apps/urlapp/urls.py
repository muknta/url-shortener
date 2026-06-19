from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.urls import path
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import RedirectView

from . import api
from .views import redirect_to_long

app_name = "urlapp"


@ensure_csrf_cookie
def shell_view(request):
    return render(request, "urlapp/app.html")


urlpatterns = [
    path("", shell_view, name="index"),
    path("public-urls/", shell_view, name="public-surls"),
    path("my-urls/", login_required(shell_view), name="user-surls"),
    # Backward compat: old "nobody's urls" path
    path("nobodys-urls/", RedirectView.as_view(url="/public-urls/", permanent=True)),
    # API
    path("api/shorten/", api.api_shorten, name="api-shorten"),
    path("api/urls/public/", api.api_public_urls, name="api-public-urls"),
    path("api/urls/mine/", api.api_my_urls, name="api-my-urls"),
    path("api/urls/<uuid:pk>/delete/", api.api_delete_url, name="api-delete-url"),
    # Redirect — keep last so explicit routes win
    path("<slug:code>/", redirect_to_long, name="redirect-to-long"),
]
