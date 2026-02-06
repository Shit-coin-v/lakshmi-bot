from django.db import models
from django.utils import timezone


class Product(models.Model):
    product_code = models.CharField(max_length=50, unique=True, blank=True, null=True)
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=100, blank=True, null=True)
    stock = models.IntegerField(blank=True, null=True)
    store_id = models.IntegerField()
    image = models.ImageField(upload_to='products/', null=True, blank=True, verbose_name="Фото")
    description = models.TextField(null=True, blank=True, verbose_name="Описание")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    is_promotional = models.BooleanField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    one_c_guid = models.CharField(max_length=64, unique=True, blank=True, null=True)

    class Meta:
        db_table = "products"
        verbose_name = "Товар"
        verbose_name_plural = "Товары"

    def __str__(self):
        return self.name

class CustomUser(models.Model):
    telegram_id = models.BigIntegerField(unique=True)
    first_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=True, blank=True)
    full_name = models.CharField(max_length=200, null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True, verbose_name="Телефон")
    email = models.EmailField(null=True, blank=True, verbose_name="Email")
    birth_date = models.DateTimeField(null=True, blank=True)
    registration_date = models.DateTimeField(null=True, blank=True)
    qr_code = models.CharField(max_length=500, null=True, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name="Аватар")
    bonuses = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    referrer = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="referrals",
        db_column="referrer_id",
        to_field="telegram_id"
    )
    last_purchase_date = models.DateTimeField(null=True, blank=True)
    total_spent = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    purchase_count = models.IntegerField(null=True, blank=True)
    personal_data_consent = models.BooleanField(null=True, blank=True)
    newsletter_enabled = models.BooleanField("Подписка на рассылки", default=True)
    promo_enabled = models.BooleanField("Акции и скидки", default=True)
    news_enabled = models.BooleanField("Новости магазина", default=True)
    general_enabled = models.BooleanField("Общие уведомления", default=True)
    created_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "customers"
        verbose_name = "Клиент"
        verbose_name_plural = "Клиенты"

    def __str__(self):
        return self.full_name or f"User {self.telegram_id}"


class CustomerDevice(models.Model):
    PLATFORM_CHOICES = (
        ("android", "Android"),
        ("ios", "iOS"),
        ("web", "Web"),
    )

    customer = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="devices",
        verbose_name="Клиент",
    )
    fcm_token = models.CharField(max_length=255, unique=True, verbose_name="FCM токен")
    platform = models.CharField(
        max_length=20, choices=PLATFORM_CHOICES, default="android", verbose_name="Платформа"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создан")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлен")

    class Meta:
        db_table = "customer_devices"
        verbose_name = "Устройство клиента"
        verbose_name_plural = "Устройства клиентов"

    def __str__(self):
        return f"{self.customer_id} | {self.platform}"
    

class Notification(models.Model):
    TYPE_CHOICES = (
        ("personal", "Персональное"),
        ("broadcast", "Массовое"),
    )

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name="Клиент",
    )
    title = models.CharField(max_length=200, verbose_name="Заголовок")
    body = models.TextField(verbose_name="Текст")
    is_read = models.BooleanField(default=False, verbose_name="Прочитано")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Создано")
    type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default="personal",
        db_index=True,
        verbose_name="Тип",
    )

    class Meta:
        db_table = "notifications"
        verbose_name = "Уведомление"
        verbose_name_plural = "Уведомления"
        indexes = [
            models.Index(fields=["user", "-created_at"], name="notif_user_created_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} | {self.type} | {self.title}"
    

class NotificationOpenEvent(models.Model):
    SOURCE_CHOICES = (
        ("inapp", "In-app"),
        ("push", "Push"),
    )

    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name="open_events",
        verbose_name="Уведомление",
    )
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="notification_open_events",
        verbose_name="Клиент",
    )
    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default="inapp",
        db_index=True,
        verbose_name="Источник",
    )
    occurred_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name="Открыто",
    )

    class Meta:
        db_table = "notification_open_events"
        verbose_name = "Открытие уведомления"
        verbose_name_plural = "Открытия уведомлений"
        constraints = [
            models.UniqueConstraint(
                fields=["notification"],
                name="uniq_notification_open_once",
            )
        ]

    def __str__(self) -> str:
        return f"{self.user_id} | notif={self.notification_id} | {self.source}"


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

    customer = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='orders', verbose_name="Клиент")
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

    def __str__(self):
        return f"Заказ #{self.id} ({self.get_status_display()})"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, verbose_name="Товар")
    quantity = models.IntegerField(default=1, verbose_name="Количество")
    price_at_moment = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена на момент заказа")

    class Meta:
        db_table = "order_items"
        verbose_name = "Позиция заказа"
        verbose_name_plural = "Позиции заказа"

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"


class Transaction(models.Model):
    customer = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.DO_NOTHING, null=True, blank=True)
    quantity = models.IntegerField(null=True, blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    bonus_earned = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    purchase_date = models.DateField(null=True, blank=True)
    purchase_time = models.TimeField(null=True, blank=True)
    store_id = models.IntegerField()
    is_promotional = models.BooleanField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    purchased_at = models.DateTimeField(null=True, blank=True)
    idempotency_key = models.UUIDField(unique=True, null=True, blank=True)
    receipt_total_amount   = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    receipt_discount_total = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    receipt_bonus_spent    = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    receipt_bonus_earned   = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    receipt_guid = models.CharField(max_length=64, null=True, blank=True)
    receipt_line = models.IntegerField()

    class Meta:
        db_table = "transactions"
        constraints = [
            models.UniqueConstraint(fields=["receipt_guid", "receipt_line"], name="uniq_receipt_line")
        ]

    def __str__(self):
        return f"Transaction #{self.id}"

class BroadcastMessage(models.Model):
    CATEGORY_CHOICES = (
        ("general", "Общая"),
        ("promo", "Акции и скидки"),
        ("news", "Новости магазина"),
    )

    message_text = models.TextField("Текст сообщения", null=False)
    created_at = models.DateTimeField("Дата создания", default=timezone.now)
    send_to_all = models.BooleanField("Всем пользователям", default=True)
    target_user_ids = models.TextField(
        "ID пользователей (через запятую)",
        null=True,
        blank=True,
        help_text="Пример: 123456789, 987654321"
    )
    category = models.CharField(
        "Категория",
        max_length=10,
        choices=CATEGORY_CHOICES,
        default="general",
    )

    class Meta:
        verbose_name = 'Рассылка'
        verbose_name_plural = 'Рассылки'
        db_table = 'broadcast_messages'
        ordering = ['-created_at']


class BotActivity(models.Model):
    customer = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='bot_activities')
    action = models.CharField(max_length=255)
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = 'История'
        verbose_name_plural = 'Истории'
        db_table = 'bot_activities'

    def __str__(self):
        return f"{self.customer}: {self.action} at {self.timestamp}"


class NewsletterDelivery(models.Model):
    CHANNEL_CHOICES = (
        ("telegram", "Telegram"),
        ("push", "Push"),
    )

    message = models.ForeignKey(
        BroadcastMessage,
        on_delete=models.CASCADE,
        related_name="deliveries",
    )
    customer = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="newsletter_deliveries",
    )
    chat_id = models.BigIntegerField(null=True, blank=True)
    telegram_message_id = models.BigIntegerField(null=True, blank=True)
    open_token = models.CharField(max_length=64, unique=True, null=True, blank=True, db_index=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    channel = models.CharField(
        "Канал доставки",
        max_length=10,
        choices=CHANNEL_CHOICES,
        default="telegram",
        db_index=True,
    )
    notification = models.ForeignKey(
        Notification,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="newsletter_deliveries",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "newsletter_deliveries"
        verbose_name = "Доставка рассылки"
        verbose_name_plural = "Доставки рассылок"
        indexes = [
            models.Index(fields=["message", "customer"], name="newsletter_delivery_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["message", "customer"],
                name="newsletter_delivery_uc",
            )
        ]

    def __str__(self):
        return f"Delivery #{self.id} for {self.customer_id}"


class NewsletterOpenEvent(models.Model):
    delivery = models.ForeignKey(
        NewsletterDelivery,
        on_delete=models.CASCADE,
        related_name="open_events",
    )
    occurred_at = models.DateTimeField(default=timezone.now)
    raw_callback_data = models.CharField(max_length=128, blank=True)
    telegram_user_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "newsletter_open_events"
        verbose_name = "Открытие рассылки"
        verbose_name_plural = "Открытия рассылок"
        indexes = [
            models.Index(fields=["delivery"], name="newsletter_open_delivery_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["delivery"],
                name="newsletter_open_events_delivery_key",
            )
        ]

    def __str__(self):
        return f"Open event #{self.id} for delivery {self.delivery_id}"