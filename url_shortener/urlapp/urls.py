from django.urls import path
from . import views


urlpatterns = [
    path('', views.index, name='index'),
    path('shorten-url/', views.shorten_url, name='shorten-url'),
    path('<str:short_url>/', views.redirect_to_long, name='redirect-to-long'),
]

