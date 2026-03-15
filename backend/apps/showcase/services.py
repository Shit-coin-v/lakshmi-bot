from __future__ import annotations

import logging
import math
from collections import defaultdict, deque
from datetime import timedelta

from django.db import transaction
from django.db.models import Q, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.loyalty.models import Transaction
from apps.main.models import Category, Product

from .models import ProductRanking

logger = logging.getLogger(__name__)

# Период для подсчёта продаж. 90 дней — стандарт для розницы,
# совпадает с порогом recency в apps.rfm (RECENCY_THRESHOLDS = [7, 30, 90, 180]).
SALES_PERIOD_DAYS = 90

# --- Personal ranking constants ---
CATEGORY_WEIGHT = 0.7
REPEAT_WEIGHT = 0.3
PERSONAL_WEIGHT = 0.6
GLOBAL_WEIGHT = 0.4
REPEAT_DECAY = 0.5
CATEGORY_DEPTH = 1


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


# ---------------------------------------------------------------------------
# Personal ranking
# ---------------------------------------------------------------------------


def _build_category_depth_map() -> dict[int, int | None]:
    """Map every category to its resolved ancestor at CATEGORY_DEPTH.

    depth 0 = root (parent IS NULL), depth 1 = children of root, etc.
    Returns {category_id: resolved_category_id}.
    Categories at depth <= CATEGORY_DEPTH resolve to themselves.
    """
    rows = list(Category.objects.values_list("id", "parent_id"))
    children_of: dict[int | None, list[int]] = defaultdict(list)
    for cat_id, parent_id in rows:
        children_of[parent_id].append(cat_id)

    result: dict[int, int | None] = {}

    # BFS from roots, tracking depth and the ancestor at CATEGORY_DEPTH
    queue: deque[tuple[int, int, int | None]] = deque()  # (cat_id, depth, resolved)
    for root_id in children_of[None]:
        resolved = root_id  # depth 0 → resolve to self
        queue.append((root_id, 0, resolved))

    while queue:
        cat_id, depth, resolved = queue.popleft()
        result[cat_id] = resolved
        for child_id in children_of.get(cat_id, []):
            child_depth = depth + 1
            if child_depth <= CATEGORY_DEPTH:
                child_resolved = child_id
            else:
                child_resolved = resolved
            queue.append((child_id, child_depth, child_resolved))

    return result


def calculate_personal_rankings(
    customer_id: int,
    global_scores: dict[int, float] | None = None,
    category_map: dict[int, int | None] | None = None,
    active_product_ids: set[int] | None = None,
    product_categories_all: dict[int, int] | None = None,
) -> dict:
    """Calculate personal rankings for a single customer.

    Writes final blended score to ProductRanking(customer=customer_id).
    Returns stats dict.
    """
    now = timezone.now()
    cutoff = now.date() - timedelta(days=SALES_PERIOD_DAYS)

    txns = list(
        Transaction.objects.filter(
            customer_id=customer_id,
            purchase_date__gte=cutoff,
            product__isnull=False,
            quantity__isnull=False,
            quantity__gt=0,
        )
        .values_list("product_id", "product__category_id", "quantity")
    )

    # Cold-start: no transactions → delete old personal records
    if not txns:
        deleted, _ = ProductRanking.objects.filter(customer_id=customer_id).delete()
        return {"customer_id": customer_id, "created": 0, "deleted": deleted, "cold_start": True}

    # Lazy-load shared data if not provided
    if global_scores is None:
        global_scores = dict(
            ProductRanking.objects.filter(customer__isnull=True)
            .values_list("product_id", "score")
        )
    if category_map is None:
        category_map = _build_category_depth_map()

    # --- Aggregate per-product and per-resolved-category ---
    product_times: dict[int, int] = defaultdict(int)       # product_id → purchase event count
    category_qty: dict[int | None, int] = defaultdict(int) # resolved_cat → total qty
    total_qty = 0

    for product_id, cat_id, qty in txns:
        product_times[product_id] += 1  # count purchase events, not units
        resolved_cat = category_map.get(cat_id) if cat_id else None
        if resolved_cat is not None:
            category_qty[resolved_cat] += qty
        total_qty += qty

    # Lazy-load product data if not provided
    if active_product_ids is None:
        active_product_ids = set(
            Product.objects.filter(is_active=True).values_list("id", flat=True)
        )
    if product_categories_all is None:
        product_categories_all = dict(
            Product.objects.filter(
                is_active=True, category_id__isnull=False,
            ).values_list("id", "category_id")
        )

    rankings = []
    for pid in active_product_ids:
        # category_score: based on resolved category
        raw_cat_id = product_categories_all.get(pid)
        resolved_cat = category_map.get(raw_cat_id) if raw_cat_id else None
        if resolved_cat is not None and resolved_cat in category_qty and total_qty > 0:
            cat_score = (category_qty[resolved_cat] / total_qty) * 1000
        else:
            cat_score = 0.0

        # repeat_score: based on purchase event count (not quantity)
        times_bought = product_times.get(pid, 0)
        if times_bought > 0:
            rep_score = (1 - math.exp(-REPEAT_DECAY * times_bought)) * 1000
        else:
            rep_score = 0.0

        # Sparse storage: skip if no personal signal
        if cat_score == 0.0 and rep_score == 0.0:
            continue

        personal_score = cat_score * CATEGORY_WEIGHT + rep_score * REPEAT_WEIGHT
        g_score = global_scores.get(pid, 0.0)
        final_score = personal_score * PERSONAL_WEIGHT + g_score * GLOBAL_WEIGHT

        rankings.append(
            ProductRanking(
                customer_id=customer_id,
                product_id=pid,
                score=final_score,
                calculated_at=now,
            )
        )

    with transaction.atomic():
        deleted, _ = ProductRanking.objects.filter(customer_id=customer_id).delete()
        ProductRanking.objects.bulk_create(rankings, batch_size=500)

    logger.info(
        "Personal ranking customer=%s: %d записей создано, %d удалено.",
        customer_id, len(rankings), deleted,
    )
    return {
        "customer_id": customer_id,
        "created": len(rankings),
        "deleted": deleted,
        "cold_start": False,
    }


def calculate_all_personal_rankings() -> dict:
    """Orchestrate personal ranking calculation for all eligible customers."""
    now = timezone.now()
    cutoff = now.date() - timedelta(days=SALES_PERIOD_DAYS)

    # Pre-load shared data once
    global_scores = dict(
        ProductRanking.objects.filter(customer__isnull=True)
        .values_list("product_id", "score")
    )
    category_map = _build_category_depth_map()
    active_product_ids = set(
        Product.objects.filter(is_active=True).values_list("id", flat=True)
    )
    product_categories_all = dict(
        Product.objects.filter(
            is_active=True, category_id__isnull=False,
        ).values_list("id", "category_id")
    )

    # Customers with transactions in the window
    customer_ids = list(
        Transaction.objects.filter(
            purchase_date__gte=cutoff,
            product__isnull=False,
            quantity__isnull=False,
            quantity__gt=0,
        )
        .values_list("customer_id", flat=True)
        .distinct()
    )
    # Filter out NULL customer_id
    customer_ids = [cid for cid in customer_ids if cid is not None]

    total_created = 0
    total_deleted = 0
    cold_starts = 0

    for cid in customer_ids:
        stats = calculate_personal_rankings(
            cid, global_scores, category_map,
            active_product_ids, product_categories_all,
        )
        total_created += stats["created"]
        total_deleted += stats["deleted"]
        if stats["cold_start"]:
            cold_starts += 1

    # Cleanup: remove personal records for customers no longer in the window
    stale_deleted, _ = (
        ProductRanking.objects
        .filter(customer__isnull=False)
        .exclude(customer_id__in=customer_ids)
        .delete()
    )

    logger.info(
        "Personal rankings: %d клиентов, %d записей создано, "
        "%d удалено, %d stale удалено, %d cold-start.",
        len(customer_ids), total_created, total_deleted,
        stale_deleted, cold_starts,
    )
    return {
        "customers_processed": len(customer_ids),
        "total_created": total_created,
        "total_deleted": total_deleted,
        "stale_deleted": stale_deleted,
        "cold_starts": cold_starts,
        "calculated_at": now,
    }
