from __future__ import annotations

from apps.orders.views import OrderCreateView  # noqa: F401
from apps.orders.views import OrderDetailView  # noqa: F401
from apps.orders.views import OrderListUserView  # noqa: F401
from apps.orders.views import ProductListView  # noqa: F401
from apps.loyalty.views import PurchaseAPIView  # noqa: F401
from apps.main.views import CustomerProfileView  # noqa: F401
from apps.main.views import SendMessageAPIView  # noqa: F401
from apps.notifications.views import NotificationViewSet  # noqa: F401
from apps.notifications.views import PushRegisterView  # noqa: F401
from apps.notifications.views import UpdateFCMTokenView  # noqa: F401
