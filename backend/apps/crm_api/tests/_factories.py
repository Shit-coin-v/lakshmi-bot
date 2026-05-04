"""Хелперы для создания тестовых пользователей в CRM-тестах."""
from django.contrib.auth import get_user_model

User = get_user_model()


def create_staff(email: str = "manager@example.com", password: str = "secret123") -> User:
    """Менеджер CRM (is_staff=True)."""
    return User.objects.create_user(
        username=email,
        email=email,
        password=password,
        is_staff=True,
    )


def create_regular_user(email: str = "regular@example.com", password: str = "secret123") -> User:
    """Обычный пользователь (is_staff=False)."""
    return User.objects.create_user(
        username=email,
        email=email,
        password=password,
        is_staff=False,
    )
