import calendar
import logging
import math
import random
from datetime import date
from celery import shared_task
from django.conf import settings
from django.utils import timezone

import requests

logger = logging.getLogger(__name__)


@shared_task(name="apps.rfm.tasks.recalculate_all_rfm")
def recalculate_all_rfm():
    """Ежедневный пересчёт RFM-профилей (механизм A).

    Не трогает CustomerBonusTier и CustomerCampaignAssignment.
    """
    from apps.common.locks import task_lock
    from .services import calculate_all_customers_rfm

    with task_lock("rfm-recalc", ttl_seconds=3600) as acquired:
        if not acquired:
            logger.info("recalculate_all_rfm: lock held, skipping")
            return None

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

    if getattr(settings, "ONEC_RFM_SYNC_ENABLED", False) and created > 0:
        sync_rfm_segments_to_onec.delay(str(effective_from))

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


@shared_task(bind=True, max_retries=3, name="apps.rfm.tasks.sync_rfm_segments_to_onec")
def sync_rfm_segments_to_onec(self, effective_month: str):
    """Синхронизация RFM-сегментов в 1С. Отправляет chunks по card_id + segment."""
    from apps.integrations.onec.onec_client import send_rfm_chunk_to_onec

    from .models import CustomerBonusTier, RFMSegmentSyncLog

    # Kill switch
    if not getattr(settings, "ONEC_RFM_SYNC_ENABLED", False):
        logger.info("sync_rfm_segments_to_onec: disabled via ONEC_RFM_SYNC_ENABLED")
        return {"status": "disabled"}

    rfm_sync_url = getattr(settings, "ONEC_RFM_SYNC_URL", "") or ""
    if not rfm_sync_url:
        logger.info("sync_rfm_segments_to_onec: ONEC_RFM_SYNC_URL not configured")
        return {"status": "skipped", "reason": "no_url"}

    effective_date = date.fromisoformat(effective_month)

    sync_log, _created = RFMSegmentSyncLog.objects.get_or_create(
        effective_month=effective_date,
    )

    # Idempotency: уже успешно отправлено
    if sync_log.status == RFMSegmentSyncLog.Status.SUCCESS:
        logger.info(
            "sync_rfm_segments_to_onec: already SUCCESS for %s, skipping",
            effective_month,
        )
        return {"status": "already_sent", "effective_month": effective_month}

    try:
        # Читаем CustomerBonusTier за месяц, только с card_id
        bonus_tiers = (
            CustomerBonusTier.objects
            .filter(effective_from=effective_date)
            .select_related("customer")
            .exclude(customer__card_id__isnull=True)
            .exclude(customer__card_id="")
        )

        segment_ru = {
            "champions": "Чемпионы",
            "loyal": "Лояльные",
            "potential_loyalists": "Потенциально лояльные",
            "new_customers": "Новые клиенты",
            "at_risk": "Под угрозой",
            "hibernating": "Спящие",
            "lost": "Потерянные",
        }

        customers_payload = [
            {
                "card_id": bt.customer.card_id,
                "segment": segment_ru.get(bt.segment_label_at_fixation, bt.segment_label_at_fixation),
            }
            for bt in bonus_tiers
        ]

        total_customers = len(customers_payload)
        if total_customers == 0:
            logger.info(
                "sync_rfm_segments_to_onec: no customers with card_id for %s",
                effective_month,
            )
            sync_log.status = RFMSegmentSyncLog.Status.SUCCESS
            sync_log.completed_at = timezone.now()
            sync_log.save(update_fields=["status", "completed_at"])
            return {"status": "empty", "effective_month": effective_month}

        chunk_size = getattr(settings, "ONEC_RFM_SYNC_CHUNK_SIZE", 500)
        total_chunks = math.ceil(total_customers / chunk_size)

        # Обновляем sync_log: IN_PROGRESS
        sync_log.status = RFMSegmentSyncLog.Status.IN_PROGRESS
        sync_log.started_at = timezone.now()
        sync_log.total_customers = total_customers
        sync_log.total_chunks = total_chunks
        sync_log.chunks_sent = 0
        sync_log.chunks_failed = 0
        sync_log.last_error = ""
        sync_log.save(update_fields=[
            "status", "started_at", "total_customers", "total_chunks",
            "chunks_sent", "chunks_failed", "last_error",
        ])

        # Отправляем chunks последовательно
        for i in range(total_chunks):
            chunk = customers_payload[i * chunk_size : (i + 1) * chunk_size]
            try:
                send_rfm_chunk_to_onec(chunk)
                sync_log.chunks_sent += 1
                logger.info(
                    "sync_rfm_segments_to_onec: chunk %d/%d sent (%d customers)",
                    i + 1, total_chunks, len(chunk),
                )
            except (requests.RequestException, RuntimeError, ValueError) as chunk_exc:
                sync_log.chunks_failed += 1
                sync_log.last_error = str(chunk_exc)[:1000]
                logger.exception(
                    "sync_rfm_segments_to_onec: chunk %d/%d failed: %s",
                    i + 1, total_chunks, chunk_exc,
                )
            # Сохраняем прогресс после каждого chunk
            sync_log.save(update_fields=["chunks_sent", "chunks_failed", "last_error"])

        # Финальный статус
        if sync_log.chunks_failed == 0:
            sync_log.status = RFMSegmentSyncLog.Status.SUCCESS
        elif sync_log.chunks_sent > 0:
            sync_log.status = RFMSegmentSyncLog.Status.PARTIAL
        else:
            sync_log.status = RFMSegmentSyncLog.Status.FAILED

        sync_log.completed_at = timezone.now()
        sync_log.save(update_fields=["status", "completed_at"])

        logger.info(
            "sync_rfm_segments_to_onec: completed month=%s status=%s "
            "customers=%d chunks_sent=%d chunks_failed=%d",
            effective_month, sync_log.status,
            total_customers, sync_log.chunks_sent, sync_log.chunks_failed,
        )

        return {
            "status": sync_log.status,
            "effective_month": effective_month,
            "total_customers": total_customers,
            "chunks_sent": sync_log.chunks_sent,
            "chunks_failed": sync_log.chunks_failed,
        }

    except Exception as exc:
        error_msg = str(exc)[:1000]
        sync_log.status = RFMSegmentSyncLog.Status.FAILED
        sync_log.last_error = error_msg
        sync_log.completed_at = timezone.now()
        sync_log.save(update_fields=["status", "last_error", "completed_at"])

        logger.exception(
            "sync_rfm_segments_to_onec: task failed month=%s error=%s",
            effective_month, error_msg,
        )

        if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
            return {"status": "failed", "reason": error_msg}

        if self.request.retries >= self.max_retries:
            return {"status": "failed", "reason": error_msg}

        base = min(20 + self.request.retries * 10, 70)
        countdown = base + random.uniform(0, base * 0.3)
        raise self.retry(exc=exc, countdown=countdown)
