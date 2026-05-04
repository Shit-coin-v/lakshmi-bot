"""URL-маршруты CRM-API."""
from django.urls import path

from apps.crm_api.views.auth import LoginView, LogoutView, MeView
from apps.crm_api.views.clients import ClientListView, ClientDetailView
from apps.crm_api.views.dashboard import DashboardView
from apps.crm_api.views.campaigns import CampaignListView
from apps.crm_api.views.orders import OrderListView

app_name = "crm_api"

urlpatterns = [
    path("auth/login/",  LoginView.as_view(),  name="auth-login"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/me/",     MeView.as_view(),     name="auth-me"),
    path("dashboard/",   DashboardView.as_view(), name="dashboard"),
    path("clients/",     ClientListView.as_view(), name="clients-list"),
    path("clients/<str:card_id>/", ClientDetailView.as_view(), name="clients-detail"),
    path("orders/",      OrderListView.as_view(), name="orders-list"),
    path("campaigns/",   CampaignListView.as_view(), name="campaigns-list"),
    # Data (Tasks 11-13): добавляются по мере имплементации
]
