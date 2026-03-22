from apps.common.authentication import JWTAuthentication
from apps.common.permissions import CustomerPermission


class CustomerAuthMixin:
    """Mixin for views requiring customer JWT authentication.

    Adds JWTAuthentication so expired tokens return 401 (not 403),
    enabling the frontend token refresh interceptor.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [CustomerPermission]
