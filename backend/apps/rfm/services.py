from decimal import Decimal

from django.conf import settings
from django.utils import timezone

from apps.main.models import CustomUser

from .models import CustomerRFMProfile

# ---------------------------------------------------------------------------
# Границы квантилей для R, F, M scoring.
# Каждый список содержит 4 порога, разбивающих клиентов на 5 групп (1..5).
# Значения подобраны как разумные стартовые для розничной торговли.
# При необходимости заменить на расчёт по перцентилям.
# ---------------------------------------------------------------------------

# Recency: меньше дней = лучше → выше score
RECENCY_THRESHOLDS = [7, 30, 90, 180]  # дни

# Frequency: больше покупок = лучше → выше score
FREQUENCY_THRESHOLDS = [2, 5, 10, 20]  # количество

# Monetary: больше потрачено = лучше → выше score
MONETARY_THRESHOLDS = [
    Decimal("1000"),
    Decimal("5000"),
    Decimal("15000"),
    Decimal("50000"),
]

# ---------------------------------------------------------------------------
# Карта rfm_code → segment_label.
# Ключи — множества rfm_code, значения — имя сегмента.
# Порядок проверки имеет значение: первое совпадение побеждает.
# ---------------------------------------------------------------------------
SEGMENT_MAP: list[tuple[set[str], str]] = [
    # Champions: высокие R, F, M
    ({"555", "554", "545", "544", "455", "454", "445"}, "champions"),
    # Loyal: высокие F и M, средний-высокий R
    ({"553", "552", "543", "542", "535", "534", "525", "524", "453", "452", "443"}, "loyal"),
    # Potential loyalists: высокий R, средний F
    ({"551", "541", "531", "521", "444", "434", "443", "433"}, "potential_loyalists"),
    # New customers: высокий R, низкий F и M
    ({"512", "511", "412", "411", "513", "413"}, "new_customers"),
    # At risk: средний R, высокий F и M
    ({"355", "354", "345", "344", "335", "334", "255", "254", "245", "244"}, "at_risk"),
    # Hibernating: низкий R, средний F
    ({"253", "252", "243", "242", "235", "234", "225", "224",
      "155", "154", "145", "144", "135", "134", "125", "124"}, "hibernating"),
    # Lost: низкий R, низкий F и M — всё остальное
]


def _score_recency(days: int | None) -> int:
    """Recency score: меньше дней → выше score."""
    if days is None:
        return 1
    for i, threshold in enumerate(RECENCY_THRESHOLDS):
        if days <= threshold:
            return 5 - i
    return 1


def _score_frequency(count: int) -> int:
    """Frequency score: больше покупок → выше score."""
    for i, threshold in enumerate(reversed(FREQUENCY_THRESHOLDS)):
        if count >= threshold:
            return 5 - i
    return 1


def _score_monetary(value: Decimal) -> int:
    """Monetary score: больше потрачено → выше score."""
    for i, threshold in enumerate(reversed(MONETARY_THRESHOLDS)):
        if value >= threshold:
            return 5 - i
    return 1


def _get_segment_label(rfm_code: str) -> str:
    """Определяет segment_label по rfm_code из SEGMENT_MAP."""
    for codes, label in SEGMENT_MAP:
        if rfm_code in codes:
            return label
    return "lost"


def compute_segment_for_customer_data(
    last_purchase_date,
    purchase_count: int | None,
    total_spent: Decimal | None,
    now=None,
) -> tuple[str, str]:
    """Вычисляет segment_label по сырым данным клиента.

    Общая утилита для RFM-сервиса и monthly bonus tier batch.
    Не обращается к БД, не создаёт/обновляет записи.

    Returns:
        (rfm_code, segment_label)
    """
    if now is None:
        now = timezone.now()

    recency_days = None
    if last_purchase_date:
        delta = now - last_purchase_date
        recency_days = max(delta.days, 0)

    frequency = purchase_count or 0
    monetary = total_spent or Decimal("0")

    r_score = _score_recency(recency_days)
    f_score = _score_frequency(frequency)
    m_score = _score_monetary(monetary)

    rfm_code = f"{r_score}{f_score}{m_score}"
    segment_label = _get_segment_label(rfm_code)
    return rfm_code, segment_label


def calculate_customer_rfm(customer_id: int) -> CustomerRFMProfile:
    """
    Рассчитывает RFM-профиль для одного клиента.
    Создаёт или обновляет CustomerRFMProfile.
    """
    customer = CustomUser.objects.get(id=customer_id)
    now = timezone.now()

    # --- Raw metrics ---
    recency_days = None
    if customer.last_purchase_date:
        delta = now - customer.last_purchase_date
        recency_days = max(delta.days, 0)

    frequency_count = customer.purchase_count or 0
    monetary_value = customer.total_spent or Decimal("0")

    # --- Scoring ---
    r_score = _score_recency(recency_days)
    f_score = _score_frequency(frequency_count)
    m_score = _score_monetary(monetary_value)

    rfm_code = f"{r_score}{f_score}{m_score}"
    segment_label = _get_segment_label(rfm_code)

    profile, _ = CustomerRFMProfile.objects.update_or_create(
        customer=customer,
        defaults={
            "recency_days": recency_days,
            "frequency_count": frequency_count,
            "monetary_value": monetary_value,
            "r_score": r_score,
            "f_score": f_score,
            "m_score": m_score,
            "rfm_code": rfm_code,
            "segment_label": segment_label,
            "calculated_at": now,
        },
    )
    return profile


def calculate_all_customers_rfm() -> dict:
    """
    Пакетный расчёт RFM для всех клиентов.
    Возвращает статистику выполнения.
    """
    now = timezone.now()
    guest_tid = getattr(settings, "GUEST_TELEGRAM_ID", 0)
    customers = CustomUser.objects.exclude(telegram_id=guest_tid)
    total_customers = customers.count()

    created = 0
    updated = 0
    skipped = 0

    for customer in customers.iterator():
        try:
            recency_days = None
            if customer.last_purchase_date:
                delta = now - customer.last_purchase_date
                recency_days = max(delta.days, 0)

            frequency_count = customer.purchase_count or 0
            monetary_value = customer.total_spent or Decimal("0")

            r_score = _score_recency(recency_days)
            f_score = _score_frequency(frequency_count)
            m_score = _score_monetary(monetary_value)

            rfm_code = f"{r_score}{f_score}{m_score}"
            segment_label = _get_segment_label(rfm_code)

            _, was_created = CustomerRFMProfile.objects.update_or_create(
                customer=customer,
                defaults={
                    "recency_days": recency_days,
                    "frequency_count": frequency_count,
                    "monetary_value": monetary_value,
                    "r_score": r_score,
                    "f_score": f_score,
                    "m_score": m_score,
                    "rfm_code": rfm_code,
                    "segment_label": segment_label,
                    "calculated_at": now,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1
        except Exception:
            skipped += 1

    return {
        "total_customers": total_customers,
        "processed": created + updated,
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "calculated_at": now,
    }
