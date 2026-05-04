from rest_framework import serializers


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=1, max_length=128)


class MeSerializer(serializers.Serializer):
    """Информация о текущем пользователе (для /auth/me/ и для ответа /login/)."""

    id = serializers.IntegerField(source="pk", read_only=True)
    email = serializers.EmailField(read_only=True)
    name = serializers.SerializerMethodField()

    def get_name(self, user) -> str:
        full = f"{user.first_name} {user.last_name}".strip()
        return full or user.email or user.username
