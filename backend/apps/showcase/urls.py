from django.urls import path

from .views import ShowcaseView

urlpatterns = [
    path("", ShowcaseView.as_view(), name="showcase"),
]
