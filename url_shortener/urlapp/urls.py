from django.urls import path
from . import views
from .views import (
    SurlDetailView,
    SurlCreateView,
    RedirectToLongURL
)

urlpatterns = [
    path('', SurlCreateView.as_view(), name='surl-create'),
    path('<int:pk>/', SurlDetailView.as_view(), name="surl-detail"),
    path('r/<str:short_url>/', RedirectToLongURL.as_view(),
              name='redirect_short_url')
]
