from django.urls import path
from . import views
from .views import (
    SurlDetailView,
    SurlCreateView
)

urlpatterns = [
    path('', SurlCreateView.as_view(), name='surl-create'),
    path('<str:short_url>', views.surl_detail, name="surl-detail"),
]
