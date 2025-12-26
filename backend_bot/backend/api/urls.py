from django.urls import path

from .views import (
    ProductListView,
    OrderCreateView,
    PurchaseAPIView,
    SendMessageAPIView,
    PushRegisterView,
    OrderListUserView,
    OrderDetailView,
    CustomerProfileView,
    NotificationViewSet,
    UpdateFCMTokenView,
    onec_orders_pending,
    onec_order_create,
    onec_order_status,
    healthz,
    onec_customer_sync,
    onec_health,
    onec_product_sync,
    onec_receipt,
)

urlpatterns = [
    path("healthz/", healthz, name="healthz"),
    path('onec/health', onec_health, name='onec_health'),
    path('onec/receipt', onec_receipt, name='onec_receipt'),
    path('onec/customer', onec_customer_sync, name='onec_customer_sync'),
    path('onec/product', onec_product_sync, name='onec_product_sync'),
    path('api/purchase/', PurchaseAPIView.as_view(), name='purchase'),
    path('api/send-message/', SendMessageAPIView.as_view(), name='send-message'),
    path('api/push/register/', PushRegisterView.as_view(), name='push-register'),
    path('api/fcm/token/', UpdateFCMTokenView.as_view(), name='fcm-token'),
    path('api/products/', ProductListView.as_view(), name='product-list'),
    path('api/orders/create/', OrderCreateView.as_view(), name='order-create'),
    path('api/orders/', OrderListUserView.as_view(), name='order-history'),
    path('api/orders/<int:pk>/', OrderDetailView.as_view(), name='order-detail'),
    path('api/customer/<int:pk>/', CustomerProfileView.as_view(), name='customer-profile'),
    path('onec/order', onec_order_create, name='onec_order_create'),
    path('onec/orders/pending', onec_orders_pending, name='onec_orders_pending'),
    path('onec/order/status', onec_order_status, name='onec_order_status'),
]

notifications_list = NotificationViewSet.as_view({"get": "list"})
notifications_detail = NotificationViewSet.as_view({"get": "retrieve"})

urlpatterns += [
    path("api/notifications/", notifications_list, name="notifications-list"),
    path("api/notifications/<int:pk>/", notifications_detail, name="notifications-detail"),
]

notifications_unread = NotificationViewSet.as_view({"get": "unread_count"})
notifications_mark_read = NotificationViewSet.as_view({"post": "mark_read"})

urlpatterns += [
    path("api/notifications/unread-count/", notifications_unread, name="notifications-unread-count"),
    path("api/notifications/<int:pk>/read/", notifications_mark_read, name="notifications-mark-read"),
]
