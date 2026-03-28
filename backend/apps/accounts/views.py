import logging

from django.core.cache import cache
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.authentication import JWTAuthentication, decode_token, generate_tokens
from apps.common.permissions import ApiKeyPermission, CustomerPermission
from apps.common.throttling import AnonAuthThrottle, VerifyCodeThrottle
from apps.main.models import CustomUser

from . import email_service
from .serializers import (
    LinkEmailSerializer,
    LinkTelegramByQrSerializer,
    LinkTelegramConfirmSerializer,
    LoginQrSerializer,
    LoginSerializer,
    RefreshSerializer,
    RegisterSerializer,
    ResetPasswordConfirmSerializer,
    ResetPasswordSerializer,
    VerifyEmailSerializer,
)

logger = logging.getLogger(__name__)


class RegisterView(APIView):
    """POST /api/auth/register/ — save registration data to cache, send verification code."""

    permission_classes = [AllowAny]
    throttle_classes = [AnonAuthThrottle]

    def post(self, request):
        ser = RegisterSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        email = d["email"].lower().strip()

        if CustomUser.objects.filter(email__iexact=email).exists():
            # Don't reveal that email exists — return same response as success
            return Response({"detail": "Код подтверждения отправлен", "email": email})

        # Save to cache, NOT to DB — user is created only after email verification
        cache.set(
            f"pending_reg:{email}",
            {
                "email": email,
                "password": d["password"],
                "full_name": d["full_name"],
                "phone": d.get("phone") or None,
                "referral_code": (d.get("referral_code") or "").strip() or None,
            },
            timeout=600,
        )

        try:
            email_service.send_verification_code(email)
        except Exception:
            logger.exception("Failed to send verification email to %s", email)

        return Response({"detail": "Код подтверждения отправлен", "email": email})


class LoginView(APIView):
    """POST /api/auth/login/ — email + password login."""

    permission_classes = [AllowAny]
    throttle_classes = [AnonAuthThrottle]

    def post(self, request):
        ser = LoginSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        email = d["email"].lower().strip()

        try:
            user = CustomUser.objects.get(email__iexact=email)
        except CustomUser.DoesNotExist:
            return Response(
                {"detail": "Неверный email или пароль"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.password_hash or not user.check_password(d["password"]):
            return Response(
                {"detail": "Неверный email или пароль"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        tokens = generate_tokens(user)
        return Response({
            "user_id": user.pk,
            "email": user.email,
            "email_verified": user.email_verified,
            "telegram_id": user.telegram_id,
            "tokens": tokens,
        })


class LoginQrView(APIView):
    """POST /api/auth/login-qr/ — QR code login (mobile app)."""

    permission_classes = [AllowAny]
    throttle_classes = [AnonAuthThrottle]

    def post(self, request):
        ser = LoginQrSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        qr_code = ser.validated_data["qr_code"].strip()

        user = CustomUser.objects.filter(qr_code=qr_code).first()
        if not user:
            logger.warning("QR login failed: qr_code not found ip=%s", request.META.get("REMOTE_ADDR", ""))
            return Response(
                {"detail": "Неверный QR-код"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        tokens = generate_tokens(user)
        return Response({
            "user_id": user.pk,
            "telegram_id": user.telegram_id,
            "tokens": tokens,
            "customer": {
                "id": user.pk,
                "telegram_id": user.telegram_id,
                "qr_code": user.qr_code,
                "bonus_balance": float(user.bonuses or 0),
            },
        })


class RefreshView(APIView):
    """POST /api/auth/refresh/ — get new access token via refresh token."""

    permission_classes = [AllowAny]
    throttle_classes = [AnonAuthThrottle]

    def post(self, request):
        ser = RefreshSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        user_id = decode_token(ser.validated_data["refresh"], expected_type="refresh")
        if user_id is None:
            return Response(
                {"detail": "Невалидный или просроченный refresh token"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            user = CustomUser.objects.get(pk=user_id)
        except CustomUser.DoesNotExist:
            return Response(
                {"detail": "Пользователь не найден"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        tokens = generate_tokens(user)
        return Response({"tokens": tokens})


class VerifyEmailView(APIView):
    """POST /api/auth/verify-email/ — verify email with 6-digit code."""

    permission_classes = [AllowAny]
    throttle_classes = [VerifyCodeThrottle]

    def post(self, request):
        ser = VerifyEmailSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        email = d["email"].lower().strip()

        if not email_service.verify_code(email, d["code"]):
            return Response(
                {"detail": "Неверный код или код истёк"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if this is a new registration (data in cache)
        pending = cache.get(f"pending_reg:{email}")

        if pending:
            # New registration — create user in DB now
            user = CustomUser(
                email=pending["email"],
                full_name=pending["full_name"],
                phone=pending.get("phone"),
                auth_method="email",
                email_verified=True,
                registration_date=timezone.now(),
                created_at=timezone.now(),
            )
            user.set_password(pending["password"])
            user.save()

            # Resolve referral_code -> referrer
            referral_code = pending.get("referral_code")
            if referral_code:
                referrer = CustomUser.objects.filter(referral_code=referral_code).first()
                if referrer and referrer.pk != user.pk:
                    CustomUser.objects.filter(pk=user.pk).update(referrer=referrer)

            cache.delete(f"pending_reg:{email}")

            tokens = generate_tokens(user)
            return Response({
                "detail": "Email подтверждён",
                "user_id": user.pk,
                "email": user.email,
                "card_id": user.card_id,
                "tokens": tokens,
            })

        # Existing user (link-email, re-verification)
        try:
            user = CustomUser.objects.get(email__iexact=email)
        except CustomUser.DoesNotExist:
            return Response(
                {"detail": "Пользователь не найден"},
                status=status.HTTP_404_NOT_FOUND,
            )

        user.email_verified = True
        user.save(update_fields=["email_verified"])

        return Response({"detail": "Email подтверждён"})


class ResetPasswordView(APIView):
    """POST /api/auth/reset-password/ — send reset code to email."""

    permission_classes = [AllowAny]
    throttle_classes = [AnonAuthThrottle]

    def post(self, request):
        ser = ResetPasswordSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        email = ser.validated_data["email"].lower().strip()

        if not CustomUser.objects.filter(email__iexact=email, password_hash__isnull=False).exists():
            # Don't reveal whether user exists
            return Response({"detail": "Если аккаунт существует, код отправлен на email"})

        try:
            email_service.send_reset_code(email)
        except Exception:
            logger.exception("Failed to send reset email to %s", email)

        return Response({"detail": "Если аккаунт существует, код отправлен на email"})


class ResetPasswordConfirmView(APIView):
    """POST /api/auth/reset-password/confirm/ — set new password with code."""

    permission_classes = [AllowAny]
    throttle_classes = [VerifyCodeThrottle]

    def post(self, request):
        ser = ResetPasswordConfirmSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        email = d["email"].lower().strip()

        if not email_service.verify_reset_code(email, d["code"]):
            return Response(
                {"detail": "Неверный код или код истёк"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = CustomUser.objects.get(email__iexact=email)
        except CustomUser.DoesNotExist:
            return Response(
                {"detail": "Пользователь не найден"},
                status=status.HTTP_404_NOT_FOUND,
            )

        user.set_password(d["new_password"])
        user.save(update_fields=["password_hash"])

        return Response({"detail": "Пароль обновлён"})


class LinkEmailView(APIView):
    """POST /api/auth/link-email/ — add email+password to existing (Telegram) account."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [CustomerPermission]

    def post(self, request):
        ser = LinkEmailSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        email = d["email"].lower().strip()
        user = request.telegram_user

        if CustomUser.objects.filter(email__iexact=email).exclude(pk=user.pk).exists():
            return Response(
                {"detail": "Этот email уже привязан к другому аккаунту"},
                status=status.HTTP_409_CONFLICT,
            )

        user.email = email
        user.set_password(d["password"])
        user.email_verified = False
        user.save(update_fields=["email", "password_hash", "email_verified"])

        try:
            email_service.send_verification_code(email)
        except Exception:
            logger.exception("Failed to send verification email to %s", email)

        return Response({"detail": "Email привязан. Код подтверждения отправлен."})


class LinkTelegramRequestView(APIView):
    """POST /api/auth/link-telegram/request/ — generate code for linking Telegram."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [CustomerPermission]

    def post(self, request):
        user = request.telegram_user

        if user.telegram_id:
            return Response(
                {"detail": "Telegram уже привязан"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        code = email_service.send_link_code(user.pk)
        return Response({"code": code, "detail": "Отправьте этот код боту командой /link"})


class LinkTelegramConfirmView(APIView):
    """POST /api/auth/link-telegram/confirm/ — called by bot to complete linking."""

    permission_classes = [ApiKeyPermission]
    throttle_classes = [VerifyCodeThrottle]

    def post(self, request):
        ser = LinkTelegramConfirmSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        code = d["code"]
        telegram_id = d["telegram_id"]

        # Verify code → get email-account user_id
        email_user_id = email_service.verify_link_code(code)
        if email_user_id is None:
            return Response(
                {"detail": "Неверный код или код истёк"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            email_user = CustomUser.objects.get(pk=email_user_id)
        except CustomUser.DoesNotExist:
            return Response(
                {"detail": "Аккаунт не найден"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Check if a separate Telegram-account exists
        telegram_user = CustomUser.objects.filter(telegram_id=telegram_id).first()

        if telegram_user and telegram_user.pk == email_user.pk:
            return Response({"detail": "Этот Telegram уже привязан к вашему аккаунту"})

        if telegram_user:
            # Merge: move all data from telegram_user → email_user
            from .merge import merge_accounts
            merge_accounts(keep=email_user, remove=telegram_user)
        else:
            # Simple link
            email_user.telegram_id = telegram_id
            email_user.save(update_fields=["telegram_id"])

        return Response({"detail": "Telegram привязан", "user_id": email_user.pk})


class LinkTelegramByQrView(APIView):
    """POST /api/auth/link-telegram/by-qr/ — link Telegram via scanned bot QR."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [CustomerPermission]

    def post(self, request):
        ser = LinkTelegramByQrSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        telegram_id = ser.validated_data["telegram_id"]
        user = request.telegram_user

        if user.telegram_id:
            return Response(
                {"detail": "Telegram уже привязан"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        existing = CustomUser.objects.filter(telegram_id=telegram_id).first()

        if existing and existing.pk == user.pk:
            return Response({"detail": "Этот Telegram уже привязан к вашему аккаунту"})

        if existing:
            from .merge import merge_accounts
            merge_accounts(keep=user, remove=existing)
        else:
            user.telegram_id = telegram_id
            user.save(update_fields=["telegram_id"])

        user.refresh_from_db()
        return Response({
            "detail": "Telegram привязан",
            "telegram_id": user.telegram_id,
            "bonuses": str(user.bonuses or 0),
            "qr_code": user.qr_code,
        })


class GenerateUserQrView(APIView):
    """POST /api/auth/generate-qr/ — generate QR for email-only user."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [CustomerPermission]

    def post(self, request):
        user = request.telegram_user

        if user.qr_code:
            return Response({"qr_code": user.qr_code})

        user.qr_code = str(user.pk)
        user.save(update_fields=["qr_code"])
        return Response({"qr_code": user.qr_code, "detail": "QR-код создан"})
