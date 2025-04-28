from django.urls import path

from .views import PurchaseAPIView, SendMessageAPIView

urlpatterns = [
    path('api/purchase/', PurchaseAPIView.as_view(), name='purchase'),
    path('api/send-message/', SendMessageAPIView.as_view(), name='send-message'),
]
