"""URL-маршруты CRM-API."""
from django.urls import path

from apps.crm_api.views.auth import LoginView, LogoutView, MeView
from apps.crm_api.views.dashboard import DashboardView

app_name = "crm_api"

urlpatterns = [
    path("auth/login/",  LoginView.as_view(),  name="auth-login"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/me/",     MeView.as_view(),     name="auth-me"),
    path("dashboard/",   DashboardView.as_view(), name="dashboard"),
    # Data (Tasks 7-13): добавляются по мере имплементации
]
