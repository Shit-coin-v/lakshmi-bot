from django.urls import path

from . import views

urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="auth-register"),
    path("login/", views.LoginView.as_view(), name="auth-login"),
    path("refresh/", views.RefreshView.as_view(), name="auth-refresh"),
    path("verify-email/", views.VerifyEmailView.as_view(), name="auth-verify-email"),
    path("reset-password/", views.ResetPasswordView.as_view(), name="auth-reset-password"),
    path("reset-password/confirm/", views.ResetPasswordConfirmView.as_view(), name="auth-reset-password-confirm"),
    path("link-email/", views.LinkEmailView.as_view(), name="auth-link-email"),
    path("link-telegram/request/", views.LinkTelegramRequestView.as_view(), name="auth-link-telegram-request"),
    path("link-telegram/confirm/", views.LinkTelegramConfirmView.as_view(), name="auth-link-telegram-confirm"),
    path("link-telegram/by-qr/", views.LinkTelegramByQrView.as_view(), name="auth-link-telegram-by-qr"),
    path("generate-qr/", views.GenerateUserQrView.as_view(), name="auth-generate-qr"),
]
