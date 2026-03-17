"""Стартовое заполнение CustomerBonusTier на текущий месяц.

Идемпотентная команда: пропускает клиентов, для которых tier уже существует.
Использует ту же логику eligibility, что и monthly batch (compute_segment_for_customer_data).

Использование:
    python manage.py backfill_bonus_tiers
"""

import calendar

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.main.models import CustomUser
from apps.rfm.models import CustomerBonusTier
from apps.rfm.services import compute_segment_for_customer_data


class Command(BaseCommand):
    help = "Заполнить CustomerBonusTier на текущий месяц для всех клиентов"

    def handle(self, *args, **options):
        now = timezone.now()
        today = timezone.localdate()
        effective_from = today.replace(day=1)
        last_day = calendar.monthrange(today.year, today.month)[1]
        effective_to = today.replace(day=last_day)

        guest_tid = getattr(settings, "GUEST_TELEGRAM_ID", 0)
        customers = CustomUser.objects.exclude(telegram_id=guest_tid)

        champions = 0
        standard = 0
        skipped = 0
        errors = 0

        for customer in customers.iterator():
            try:
                exists = CustomerBonusTier.objects.filter(
                    customer=customer,
                    effective_from=effective_from,
                ).exists()
                if exists:
                    skipped += 1
                    continue

                _, segment_label = compute_segment_for_customer_data(
                    last_purchase_date=customer.last_purchase_date,
                    purchase_count=customer.purchase_count,
                    total_spent=customer.total_spent,
                    now=now,
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
                    champions += 1
                else:
                    standard += 1

            except Exception as e:
                errors += 1
                self.stderr.write(f"ERROR customer_id={customer.id}: {e}")

        self.stdout.write(
            f"Backfill done: champions={champions} standard={standard} "
            f"skipped={skipped} errors={errors} "
            f"period={effective_from}–{effective_to}"
        )
