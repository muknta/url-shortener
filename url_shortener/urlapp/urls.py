from django.urls import path
from django.conf.urls import handler404, handler500
from . import views
from .views import (
        NobodysSurlListView,
        UserSurlListView
    )

app_name = 'urlapp'
urlpatterns = [
    path('', views.index, name='index'),
    path('shorten-url/', views.shorten_url, name='shorten-url'),
    path('nobodys-urls/', NobodysSurlListView.as_view(), name='nobodys-surls'),
    path('my-urls/', UserSurlListView.as_view(), name='user-surls'),
    path('<str:short_url>/', views.redirect_to_long, name='redirect-to-long'),
]

