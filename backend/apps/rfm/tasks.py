import calendar
import logging
from datetime import date
from celery import shared_task
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name="apps.rfm.tasks.recalculate_all_rfm")
def recalculate_all_rfm():
    """Ежедневный пересчёт RFM-профилей (механизм A).

    Не трогает CustomerBonusTier и CustomerCampaignAssignment.
    """
    from .services import calculate_all_customers_rfm

    start = timezone.now()
    result = calculate_all_customers_rfm()
    duration = (timezone.now() - start).total_seconds()

    logger.info(
        "rfm.recalculate_all_rfm INFO completed: "
        "processed=%d created=%d updated=%d skipped=%d duration=%.1fs",
        result["processed"],
        result["created"],
        result["updated"],
        result["skipped"],
        duration,
    )
    return result


@shared_task(name="apps.rfm.tasks.fix_monthly_bonus_tiers")
def fix_monthly_bonus_tiers():
    """Месячная фиксация бонусного статуса (механизм B).

    Запускается 1-го числа в 00:05 Asia/Yakutsk.
    Самостоятельно вычисляет eligibility по агрегатам CustomUser.
    Не читает CustomerRFMProfile.
    Не трогает CustomerCampaignAssignment.
    """
    from apps.main.models import CustomUser

    from .models import CustomerBonusTier
    from .services import compute_segment_for_customer_data

    start = timezone.now()
    today = date.today()

    effective_from = today.replace(day=1)
    last_day = calendar.monthrange(today.year, today.month)[1]
    effective_to = today.replace(day=last_day)

    guest_tid = getattr(settings, "GUEST_TELEGRAM_ID", 0)
    customers = CustomUser.objects.exclude(telegram_id=guest_tid)

    champions_count = 0
    standard_count = 0
    skipped_existing = 0
    errors = 0
    total = 0

    for customer in customers.iterator():
        total += 1
        try:
            exists = CustomerBonusTier.objects.filter(
                customer=customer,
                effective_from=effective_from,
            ).exists()
            if exists:
                skipped_existing += 1
                continue

            _, segment_label = compute_segment_for_customer_data(
                last_purchase_date=customer.last_purchase_date,
                purchase_count=customer.purchase_count,
                total_spent=customer.total_spent,
                now=start,
            )

            tier = "champions" if segment_label == "champions" else "standard"

            CustomerBonusTier.objects.create(
                customer=customer,
                tier=tier,
                segment_label_at_fixation=segment_label,
                effective_from=effective_from,
                effective_to=effective_to,
            )

            if tier == "champions":
                champions_count += 1
            else:
                standard_count += 1

        except Exception:
            errors += 1
            logger.exception(
                "rfm.fix_monthly_bonus_tiers ERROR customer_id=%d",
                customer.id,
            )

    duration = (timezone.now() - start).total_seconds()

    created = champions_count + standard_count
    if created == 0 and total > 0:
        logger.error(
            "rfm.fix_monthly_bonus_tiers ERROR total=0 created records "
            "for %d customers, date=%s",
            total,
            effective_from,
        )
    else:
        logger.info(
            "rfm.fix_monthly_bonus_tiers INFO completed: "
            "champions=%d standard=%d skipped=%d errors=%d total=%d duration=%.1fs",
            champions_count,
            standard_count,
            skipped_existing,
            errors,
            total,
            duration,
        )

    return {
        "effective_from": str(effective_from),
        "effective_to": str(effective_to),
        "champions": champions_count,
        "standard": standard_count,
        "skipped_existing": skipped_existing,
        "errors": errors,
        "total": total,
        "duration_seconds": duration,
    }
