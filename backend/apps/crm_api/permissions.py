from rest_framework.permissions import BasePermission


class IsCRMStaff(BasePermission):
    """Доступ к CRM-API: только аутентифицированные сотрудники (is_staff=True).

    Любой не-staff аккаунт (включая обычных клиентов с CustomUser, если у
    кого-то совпали email/пароль с django.User) получит 403.
    """

    message = "Нет доступа в CRM"

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        return bool(user and user.is_authenticated and user.is_staff)
