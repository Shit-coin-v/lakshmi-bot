from django.urls import path


def _lazy_view(view_name):
    view_callable = None

    def _view(*args, **kwargs):
        nonlocal view_callable
        if view_callable is None:
            from apps.api import views

            view = getattr(views, view_name)
            view_callable = view.as_view() if hasattr(view, "as_view") else view
        return view_callable(*args, **kwargs)

    return _view


def _lazy_viewset(viewset_name, actions):
    view_callable = None

    def _view(*args, **kwargs):
        nonlocal view_callable
        if view_callable is None:
            from apps.api import views

            viewset = getattr(views, viewset_name)
            view_callable = viewset.as_view(actions)
        return view_callable(*args, **kwargs)

    return _view

urlpatterns = [
    path("healthz/", _lazy_view("healthz"), name="healthz"),
    path("onec/health", _lazy_view("onec_health"), name="onec_health"),
    path("onec/receipt", _lazy_view("onec_receipt"), name="onec_receipt"),
    path("onec/customer", _lazy_view("onec_customer_sync"), name="onec_customer_sync"),
    path("onec/product", _lazy_view("onec_product_sync"), name="onec_product_sync"),
    path("api/purchase/", _lazy_view("PurchaseAPIView"), name="purchase"),
    path("api/send-message/", _lazy_view("SendMessageAPIView"), name="send-message"),
    path("api/push/register/", _lazy_view("PushRegisterView"), name="push-register"),
    path("api/fcm/token/", _lazy_view("UpdateFCMTokenView"), name="fcm-token"),
    path("api/products/", _lazy_view("ProductListView"), name="product-list"),
    path("api/orders/create/", _lazy_view("OrderCreateView"), name="order-create"),
    path("api/orders/", _lazy_view("OrderListUserView"), name="order-history"),
    path("api/orders/<int:pk>/", _lazy_view("OrderDetailView"), name="order-detail"),
    path("api/customer/<int:pk>/", _lazy_view("CustomerProfileView"), name="customer-profile"),
    path("onec/order", _lazy_view("onec_order_create"), name="onec_order_create"),
    path("onec/orders/pending", _lazy_view("onec_orders_pending"), name="onec_orders_pending"),
    path("onec/order/status", _lazy_view("onec_order_status"), name="onec_order_status"),
]

notifications_list = _lazy_viewset("NotificationViewSet", {"get": "list"})
notifications_detail = _lazy_viewset("NotificationViewSet", {"get": "retrieve"})

urlpatterns += [
    path("api/notifications/", notifications_list, name="notifications-list"),
    path("api/notifications/<int:pk>/", notifications_detail, name="notifications-detail"),
]

notifications_unread = _lazy_viewset("NotificationViewSet", {"get": "unread_count"})
notifications_mark_read = _lazy_viewset("NotificationViewSet", {"post": "mark_read"})

urlpatterns += [
    path("api/notifications/unread-count/", notifications_unread, name="notifications-unread-count"),
    path("api/notifications/<int:pk>/read/", notifications_mark_read, name="notifications-mark-read"),
]
