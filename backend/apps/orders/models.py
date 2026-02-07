from django.db import models

# Re-export Product for backward-compat (used by orders/serializers.py)
from apps.main.models import Product  # noqa: F401


class Order(models.Model):
    STATUS_CHOICES = [
        ('new', 'Новый'),
        ('assembly', 'В сборке'),
        ('delivery', 'Курьер едет'),
        ('completed', 'Доставлен'),
        ('canceled', 'Отменен'),
    ]

    FULFILLMENT_CHOICES = [
    ("delivery", "Доставка"),
    ("pickup", "Самовывоз"),
    ]

    PAYMENT_CHOICES = [
        ('card_courier', 'Картой курьеру'),
        ('cash', 'Наличными'),
        ('sbp', 'СБП'),
    ]

    customer = models.ForeignKey("main.CustomUser", on_delete=models.CASCADE, related_name='orders', verbose_name="Клиент")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new', verbose_name="Статус")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создан")

    # Данные доставки
    address = models.TextField(verbose_name="Адрес доставки")
    phone = models.CharField(max_length=20, verbose_name="Телефон")
    comment = models.TextField(null=True, blank=True, verbose_name="Комментарий")

    # Деньги
    products_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Сумма товаров")
    delivery_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Стоимость доставки")
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Итого к оплате")

    # Способ оплаты
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_CHOICES,
        default='card_courier',
        verbose_name="Способ оплаты"
    )

    fulfillment_type = models.CharField(
        max_length=20,
        choices=FULFILLMENT_CHOICES,
        default="delivery",
        verbose_name="Способ получения",
    )

    # --- 1C sync ---
    onec_guid = models.CharField(max_length=64, null=True, blank=True, db_index=True, verbose_name="GUID 1С")
    sync_status = models.CharField(max_length=20, default="new", db_index=True, verbose_name="Синхр. статус")
    sent_to_onec_at = models.DateTimeField(null=True, blank=True, verbose_name="Отправлен в 1С")
    last_sync_error = models.TextField(null=True, blank=True, verbose_name="Ошибка синхронизации")
    sync_attempts = models.IntegerField(default=0, verbose_name="Попыток синхронизации")


    class Meta:
        db_table = "orders"
        verbose_name = "Заказ доставки"
        verbose_name_plural = "Заказы доставки"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=["customer", "-created_at"], name="order_customer_created_idx"),
        ]

    def __str__(self):
        return f"Заказ #{self.id} ({self.get_status_display()})"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey("main.Product", on_delete=models.PROTECT, verbose_name="Товар")
    quantity = models.IntegerField(default=1, verbose_name="Количество")
    price_at_moment = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена на момент заказа")

    class Meta:
        db_table = "order_items"
        verbose_name = "Позиция заказа"
        verbose_name_plural = "Позиции заказа"

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"
