from rest_framework import serializers


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)
    full_name = serializers.CharField(max_length=200)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class RefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class VerifyEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(min_length=6, max_length=6)


class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ResetPasswordConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(min_length=6, max_length=6)
    new_password = serializers.CharField(min_length=8, write_only=True)


class LinkEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)


class LinkTelegramRequestSerializer(serializers.Serializer):
    """No input needed — user is already authenticated."""
    pass


class LinkTelegramConfirmSerializer(serializers.Serializer):
    code = serializers.CharField(min_length=6, max_length=6)
    telegram_id = serializers.IntegerField()


class LoginQrSerializer(serializers.Serializer):
    qr_code = serializers.CharField(max_length=500)


class LinkTelegramByQrSerializer(serializers.Serializer):
    telegram_id = serializers.IntegerField()
