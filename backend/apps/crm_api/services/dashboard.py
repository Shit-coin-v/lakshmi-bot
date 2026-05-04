"""Расчёты для CRM Dashboard. Кэшируются в Django cache на 5 минут."""
from datetime import timedelta
from decimal import Decimal

from django.core.cache import cache
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.rfm.constants import SEGMENT_LABEL_RU

CACHE_KEY = "crm:dashboard:v1"
CACHE_TTL = 5 * 60  # 5 минут


def compute_dashboard() -> dict:
    """Собрать payload для GET /api/crm/dashboard/.

    Кэширует целиком; повторные запросы в течение 5 мин не читают БД.
    """
    cached = cache.get(CACHE_KEY)
    if cached is not None:
        return cached
    payload = _compute_dashboard_uncached()
    cache.set(CACHE_KEY, payload, CACHE_TTL)
    return payload


def _compute_dashboard_uncached() -> dict:
    from django.conf import settings

    from apps.main.models import CustomUser
    from apps.orders.models import Order
    from apps.campaigns.models import Campaign

    now = timezone.now()
    week_start = now - timedelta(days=7)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Исключаем гостевого пользователя из клиентских агрегаций
    guest_id = getattr(settings, "GUEST_TELEGRAM_ID", 0)
    customers_qs = CustomUser.objects.exclude(telegram_id=guest_id)
    customers_total = customers_qs.count()
    orders_today = Order.objects.filter(created_at__gte=today_start).count()
    revenue_week = (
        Order.objects.filter(created_at__gte=week_start, status="completed")
        .aggregate(total=Sum("total_price"))["total"] or Decimal("0")
    )
    bonuses_total = (
        customers_qs.aggregate(total=Sum("bonuses"))["total"] or Decimal("0")
    )

    daily = list(
        Order.objects.filter(created_at__gte=now - timedelta(days=14))
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(orders=Count("id"), revenue=Sum("total_price"))
        .order_by("day")
    )
    daily_serialized = [
        {
            "date": d["day"].isoformat(),
            "orders": d["orders"],
            "revenue": int(d["revenue"] or 0),
        }
        for d in daily
    ]

    active_campaigns = list(
        Campaign.objects.filter(is_active=True)
        .select_related("segment")
        .order_by("-priority")[:5]
    )
    campaigns_payload = [
        {
            "id": f"CMP-{c.id}",
            "name": c.name,
            "hint": (
                SEGMENT_LABEL_RU.get(c.rfm_segment, c.rfm_segment)
                if c.rfm_segment
                else (c.segment.name if c.segment_id else "Все")
            ),
        }
        for c in active_campaigns
    ]

    rfm_segments = _compute_rfm_segments()

    return {
        "kpis": [
            {
                "id": "customers",
                "label": "Активные клиенты",
                "value": customers_total,
                "delta": 0,
                "deltaLabel": "",
                "format": "number",
            },
            {
                "id": "orders",
                "label": "Заказы сегодня",
                "value": orders_today,
                "delta": 0,
                "deltaLabel": "",
                "format": "number",
            },
            {
                "id": "revenue",
                "label": "Выручка за неделю",
                "value": int(revenue_week),
                "delta": 0,
                "deltaLabel": "",
                "format": "rubShort",
            },
            {
                "id": "bonuses",
                "label": "Бонусов на балансе",
                "value": int(bonuses_total),
                "delta": 0,
                "deltaLabel": "",
                "format": "number",
            },
        ],
        "daily": daily_serialized,
        "activeCampaigns": campaigns_payload,
        "rfmSegments": rfm_segments,
    }


def _compute_rfm_segments() -> list[dict]:
    """Распределение клиентов по RFM-сегментам.

    Источник: CustomerRFMProfile.segment_label. Если профилей нет —
    возвращаем пустой список (фронт корректно отрендерит)."""
    from apps.rfm.models import CustomerRFMProfile

    rows = (
        CustomerRFMProfile.objects.values("segment_label")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    total = sum(r["count"] for r in rows)
    if total == 0:
        return []
    return [
        {
            "name": SEGMENT_LABEL_RU.get(r["segment_label"], r["segment_label"]) or "—",
            "count": r["count"],
            "share": round(r["count"] * 100.0 / total, 1),
        }
        for r in rows
    ]
