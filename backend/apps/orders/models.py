from django.db import models

# Re-export Product for backward-compat (used by orders/serializers.py)
from apps.main.models import Product  # noqa: F401


class Order(models.Model):
    STATUS_CHOICES = [
        ('new', 'Новый'),
        ('accepted', 'Заказ принят'),
        ('assembly', 'Заказ собирается'),
        ('ready', 'Заказ собран'),
        ('delivery', 'Курьер забрал заказ и в пути'),
        ('arrived', 'Курьер пришёл и ждёт вас'),
        ('completed', 'Заказ доставлен'),
        ('canceled', 'Отменён'),
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

    CANCEL_REASON_CHOICES = [
        ('client_refused', 'Клиент отказался'),
        ('client_absent', 'Клиент отсутствует'),
        ('long_wait', 'Клиент долго ждал'),
        ('damaged', 'Товар повреждён'),
        ('other', 'Другая причина'),
    ]

    CANCELED_BY_CHOICES = [
        ('client', 'Клиент'),
        ('courier', 'Курьер'),
        ('picker', 'Сборщик'),
        ('admin', 'Администратор'),
        ('onec', '1С'),
    ]

    customer = models.ForeignKey("main.CustomUser", on_delete=models.CASCADE, related_name='orders', verbose_name="Клиент")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new', verbose_name="Статус")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создан")

    # Delivery data
    address = models.TextField(verbose_name="Адрес доставки")
    phone = models.CharField(max_length=20, verbose_name="Телефон")
    comment = models.TextField(null=True, blank=True, verbose_name="Комментарий")

    # Prices
    products_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Сумма товаров")
    delivery_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Стоимость доставки")
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Итого к оплате")

    # Payment method
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

    # --- Assembly ---
    assembled_by = models.BigIntegerField(null=True, blank=True, db_index=True, verbose_name="Telegram ID сборщика")

    # --- Delivery ---
    delivered_by = models.BigIntegerField(null=True, blank=True, db_index=True, verbose_name="Telegram ID курьера")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Время завершения")

    # --- Payment (YooKassa) ---
    PAYMENT_STATUS_CHOICES = [
        ("none", "Нет онлайн-оплаты"),
        ("pending", "Ожидает оплаты"),
        ("authorized", "Авторизован (hold)"),
        ("captured", "Списан"),
        ("canceled", "Отменён"),
        ("failed", "Ошибка"),
    ]
    payment_id = models.CharField(max_length=64, null=True, blank=True, db_index=True,
                                  verbose_name="ID платежа ЮKassa")
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES,
                                      default="none", db_index=True, verbose_name="Статус платежа")
    manual_check_required = models.BooleanField(default=False,
                                                verbose_name="Требует ручной проверки")

    # --- Cancellation ---
    cancel_reason = models.CharField(max_length=20, choices=CANCEL_REASON_CHOICES,
                                     null=True, blank=True, verbose_name="Причина отмены")
    canceled_by = models.CharField(max_length=20, choices=CANCELED_BY_CHOICES,
                                   null=True, blank=True, verbose_name="Кто отменил")

    # --- 1C sync ---
    onec_guid = models.CharField(max_length=64, null=True, blank=True, db_index=True, verbose_name="GUID 1С")
    sync_status = models.CharField(max_length=20, default="new", db_index=True, verbose_name="Синхр. статус")
    sent_to_onec_at = models.DateTimeField(null=True, blank=True, verbose_name="Отправлен в 1С")
    last_sync_error = models.TextField(null=True, blank=True, verbose_name="Ошибка синхронизации")
    sync_attempts = models.IntegerField(default=0, verbose_name="Попыток синхронизации")
    sync_idempotency_key = models.UUIDField(null=True, blank=True, verbose_name="Ключ идемпотентности синхронизации")


    class Meta:
        db_table = "orders"
        verbose_name = "Заказ доставки"
        verbose_name_plural = "Заказы доставки"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=["customer", "-created_at"], name="order_customer_created_idx"),
        ]
        constraints = [
            models.CheckConstraint(check=models.Q(products_price__gte=0), name="order_products_price_non_negative"),
            models.CheckConstraint(check=models.Q(delivery_price__gte=0), name="order_delivery_price_non_negative"),
            models.CheckConstraint(check=models.Q(total_price__gte=0), name="order_total_price_non_negative"),
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
        constraints = [
            models.CheckConstraint(check=models.Q(quantity__gte=1), name="orderitem_quantity_positive"),
            models.CheckConstraint(check=models.Q(price_at_moment__gte=0), name="orderitem_price_non_negative"),
        ]

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"


class CourierProfile(models.Model):
    """Courier availability profile for round-robin assignment."""
    telegram_id = models.BigIntegerField(unique=True, db_index=True, verbose_name="Telegram ID")
    full_name = models.CharField(max_length=200, blank=True, default="", verbose_name="ФИО")
    phone = models.CharField(max_length=20, blank=True, default="", verbose_name="Телефон")
    is_approved = models.BooleanField(default=False, verbose_name="Подтверждён")
    is_blacklisted = models.BooleanField(default=False, verbose_name="Чёрный список")
    accepting_orders = models.BooleanField(default=True, verbose_name="Принимает заказы")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создан")

    class Meta:
        db_table = "courier_profiles"
        verbose_name = "Курьер"
        verbose_name_plural = "Курьеры"

    def __str__(self):
        name = self.full_name or str(self.telegram_id)
        return f"{name} (tg:{self.telegram_id})"


class PickerProfile(models.Model):
    """Picker (assembler) profile for access control."""
    telegram_id = models.BigIntegerField(unique=True, db_index=True, verbose_name="Telegram ID")
    full_name = models.CharField(max_length=200, blank=True, default="", verbose_name="ФИО")
    phone = models.CharField(max_length=20, blank=True, default="", verbose_name="Телефон")
    is_approved = models.BooleanField(default=False, verbose_name="Подтверждён")
    is_blacklisted = models.BooleanField(default=False, verbose_name="Чёрный список")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создан")

    class Meta:
        db_table = "picker_profiles"
        verbose_name = "Сборщик"
        verbose_name_plural = "Сборщики"

    def __str__(self):
        name = self.full_name or str(self.telegram_id)
        return f"{name} (tg:{self.telegram_id})"


class RoundRobinCursor(models.Model):
    """Stores last assigned courier per store for fair round-robin distribution."""
    store_id = models.IntegerField(unique=True, verbose_name="ID магазина")
    last_courier_tg_id = models.BigIntegerField(null=True, blank=True, verbose_name="Последний назначенный курьер")

    class Meta:
        db_table = "round_robin_cursors"
        verbose_name = "Round-Robin курсор"
        verbose_name_plural = "Round-Robin курсоры"

    def __str__(self):
        return f"Store {self.store_id} → last courier {self.last_courier_tg_id}"
