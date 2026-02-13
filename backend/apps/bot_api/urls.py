from django.urls import path

from .views import (
    ActiveOrdersView,
    BotActivityCreateView,
    BotOrderDetailView,
    CompletedTodayView,
    CourierMessageBulkDeleteView,
    CourierMessageDeleteView,
    CourierMessageListView,
    NewsletterOpenView,
    OneCMapUpsertView,
    UserByTelegramIdView,
    UserPatchView,
    UserRegisterView,
)

urlpatterns = [
    # Customer bot
    path("users/by-telegram-id/<int:telegram_id>/", UserByTelegramIdView.as_view(), name="bot-user-by-tg"),
    path("users/register/", UserRegisterView.as_view(), name="bot-user-register"),
    path("users/<int:pk>/", UserPatchView.as_view(), name="bot-user-patch"),
    path("activities/", BotActivityCreateView.as_view(), name="bot-activity-create"),
    path("newsletter/open/", NewsletterOpenView.as_view(), name="bot-newsletter-open"),
    path("onec-map/upsert/", OneCMapUpsertView.as_view(), name="bot-onec-map-upsert"),
    # Courier bot
    path("orders/active/", ActiveOrdersView.as_view(), name="bot-orders-active"),
    path("orders/<int:pk>/detail/", BotOrderDetailView.as_view(), name="bot-order-detail"),
    path("orders/completed-today/", CompletedTodayView.as_view(), name="bot-orders-completed-today"),
    path("courier-messages/", CourierMessageListView.as_view(), name="bot-courier-messages"),
    path("courier-messages/<int:pk>/", CourierMessageDeleteView.as_view(), name="bot-courier-message-delete"),
    path("courier-messages/bulk-delete/", CourierMessageBulkDeleteView.as_view(), name="bot-courier-messages-bulk-delete"),
]
