from django.db import models


class AnalyticsEvent(models.Model):
    EVENT_TYPES = (
        ("session_start", "Начало сессии"),
        ("session_end", "Конец сессии"),
        ("screen_view", "Просмотр экрана"),
        ("cart_add", "Добавление в корзину"),
        ("cart_remove", "Удаление из корзины"),
        ("search", "Поисковый запрос"),
        ("promo_click", "Клик по акции/баннеру"),
    )

    user = models.ForeignKey(
        "main.CustomUser",
        on_delete=models.CASCADE,
        related_name="analytics_events",
    )
    event_type = models.CharField(max_length=30, choices=EVENT_TYPES, db_index=True)
    screen = models.CharField(max_length=100, blank=True, default="")
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "analytics_events"
        indexes = [
            models.Index(fields=["user", "event_type"], name="analytics_user_type_idx"),
            models.Index(fields=["created_at"], name="analytics_created_idx"),
        ]

    def __str__(self):
        return f"{self.user_id} | {self.event_type} | {self.created_at}"
