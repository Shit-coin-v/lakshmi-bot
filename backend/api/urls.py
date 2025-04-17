from django.urls import path

from .views import PurchaseView

urlpatterns = [
    path('api/purchase/', PurchaseView.as_view(), name='purchase'),
]
