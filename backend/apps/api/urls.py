from django.urls import path

from apps.common.health import healthz
from apps.integrations.onec.customer_sync import onec_customer_sync
from apps.integrations.onec.health import onec_health
from apps.integrations.onec.order_create import onec_order_create
from apps.integrations.onec.order_status import onec_order_status
from apps.integrations.onec.orders_pending import onec_orders_pending
from apps.integrations.onec.product_sync_endpoint import onec_product_sync
from apps.integrations.onec.receipt import onec_receipt
from apps.integrations.onec.stock_sync_endpoint import onec_stock_sync
from apps.loyalty.views import PurchaseAPIView
from apps.main.views import CustomerProfileView, SendMessageAPIView
from apps.notifications.views import NotificationViewSet, PushRegisterView, UpdateFCMTokenView
from apps.orders.views import OrderCancelView, OrderCreateView, OrderDetailView, OrderListUserView, ProductListView

urlpatterns = [
    # Health checks
    path("healthz/", healthz, name="healthz"),
    path("onec/health", onec_health, name="onec_health"),
    # 1C integrations
    path("onec/receipt", onec_receipt, name="onec_receipt"),
    path("onec/customer", onec_customer_sync, name="onec_customer_sync"),
    path("onec/product", onec_product_sync, name="onec_product_sync"),
    path("onec/stock", onec_stock_sync, name="onec_stock_sync"),
    path("onec/order", onec_order_create, name="onec_order_create"),
    path("onec/orders/pending", onec_orders_pending, name="onec_orders_pending"),
    path("onec/order/status", onec_order_status, name="onec_order_status"),
    # API endpoints
    path("api/purchase/", PurchaseAPIView.as_view(), name="purchase"),
    path("api/send-message/", SendMessageAPIView.as_view(), name="send-message"),
    path("api/push/register/", PushRegisterView.as_view(), name="push-register"),
    path("api/fcm/token/", UpdateFCMTokenView.as_view(), name="fcm-token"),
    path("api/products/", ProductListView.as_view(), name="product-list"),
    path("api/orders/create/", OrderCreateView.as_view(), name="order-create"),
    path("api/orders/", OrderListUserView.as_view(), name="order-history"),
    path("api/orders/<int:pk>/", OrderDetailView.as_view(), name="order-detail"),
    path("api/orders/<int:pk>/cancel/", OrderCancelView.as_view(), name="order-cancel"),
    path("api/customer/<int:pk>/", CustomerProfileView.as_view(), name="customer-profile"),
    # Notifications
    path("api/notifications/", NotificationViewSet.as_view({"get": "list"}), name="notifications-list"),
    path("api/notifications/<int:pk>/", NotificationViewSet.as_view({"get": "retrieve"}), name="notifications-detail"),
    path("api/notifications/unread-count/", NotificationViewSet.as_view({"get": "unread_count"}), name="notifications-unread-count"),
    path("api/notifications/<int:pk>/read/", NotificationViewSet.as_view({"post": "mark_read"}), name="notifications-mark-read"),
]
