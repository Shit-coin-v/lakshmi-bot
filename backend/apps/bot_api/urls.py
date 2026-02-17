from django.urls import path

from .views import (
    ActiveOrdersView,
    AssembledTodayView,
    BotActivityCreateView,
    BotOrderDetailView,
    CompletedTodayView,
    CourierMessageBulkDeleteView,
    CourierMessageDeleteView,
    CourierMessageListView,
    CourierProfileView,
    CourierToggleAcceptingView,
    NewOrdersView,
    NewsletterOpenView,
    OneCMapUpsertView,
    PickerActiveOrdersView,
    PickerMessageBulkDeleteView,
    PickerMessageListView,
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
    path("courier/profile/", CourierProfileView.as_view(), name="bot-courier-profile"),
    path("courier/toggle-accepting/", CourierToggleAcceptingView.as_view(), name="bot-courier-toggle-accepting"),
    # Picker bot
    path("orders/new/", NewOrdersView.as_view(), name="bot-orders-new"),
    path("orders/my-active/", PickerActiveOrdersView.as_view(), name="bot-orders-my-active"),
    path("orders/assembled-today/", AssembledTodayView.as_view(), name="bot-orders-assembled-today"),
    path("picker-messages/", PickerMessageListView.as_view(), name="bot-picker-messages"),
    path("picker-messages/bulk-delete/", PickerMessageBulkDeleteView.as_view(), name="bot-picker-messages-bulk-delete"),
]
