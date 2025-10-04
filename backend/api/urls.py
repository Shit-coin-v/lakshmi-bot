from django.urls import path

from .views import (
    PurchaseAPIView,
    SendMessageAPIView,
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
]
