from __future__ import annotations

import logging
from datetime import timedelta

from django.db import transaction
from django.db.models import Q, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.loyalty.models import Transaction
from apps.main.models import Product

from .models import ProductRanking

logger = logging.getLogger(__name__)

# Период для подсчёта продаж. 90 дней — стандарт для розницы,
# совпадает с порогом recency в apps.rfm (RECENCY_THRESHOLDS = [7, 30, 90, 180]).
SALES_PERIOD_DAYS = 90


def calculate_global_rankings() -> dict:
    """Пакетный расчёт глобальной витрины (customer=NULL).

    Логика score:
    1. Считаем суммарное количество проданных единиц товара за последние
       SALES_PERIOD_DAYS дней из таблицы transactions.
    2. Нормализуем в диапазон 0..1000:
       score = (total_sold / max_total_sold) * 1000
    3. Товары без продаж получают score = 0.

    Нормализация нужна, чтобы score был сравним между товарами
    и не зависел от абсолютных значений продаж.

    Возвращает статистику выполнения.
    """
    now = timezone.now()
    cutoff = now.date() - timedelta(days=SALES_PERIOD_DAYS)

    # 1. Все активные товары с суммой продаж за период
    products_with_sales = (
        Product.objects
        .filter(is_active=True)
        .annotate(
            total_sold=Coalesce(
                Sum(
                    "transaction__quantity",
                    filter=Q(transaction__purchase_date__gte=cutoff),
                ),
                0,
            ),
        )
        .values_list("id", "total_sold")
    )

    product_sales = list(products_with_sales)
    if not product_sales:
        logger.info("Нет активных товаров для расчёта витрины.")
        return {"total_products": 0, "calculated_at": now}

    # 2. Нормализация
    max_sold = max(sold for _, sold in product_sales)

    rankings = []
    for product_id, total_sold in product_sales:
        if max_sold > 0:
            score = (total_sold / max_sold) * 1000
        else:
            score = 0.0
        rankings.append(
            ProductRanking(
                customer=None,
                product_id=product_id,
                score=score,
                calculated_at=now,
            )
        )

    # 3. Атомарная замена: удаляем старые глобальные записи, создаём новые
    with transaction.atomic():
        deleted, _ = ProductRanking.objects.filter(customer__isnull=True).delete()
        ProductRanking.objects.bulk_create(rankings, batch_size=500)

    logger.info(
        "Глобальная витрина рассчитана: %d товаров, удалено %d старых записей.",
        len(rankings),
        deleted,
    )

    return {
        "total_products": len(rankings),
        "max_sold": max_sold,
        "deleted_old": deleted,
        "calculated_at": now,
    }
