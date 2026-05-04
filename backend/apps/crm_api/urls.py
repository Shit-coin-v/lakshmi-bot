"""URL-маршруты CRM-API."""
from django.urls import path

from apps.crm_api.views.auth import LoginView, LogoutView, MeView

app_name = "crm_api"

urlpatterns = [
    path("auth/login/",  LoginView.as_view(),  name="auth-login"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/me/",     MeView.as_view(),     name="auth-me"),
    # Data (Tasks 6-13): добавляются по мере имплементации
]
