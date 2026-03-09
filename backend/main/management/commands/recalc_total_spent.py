"""Recalculate total_spent and purchase_count for all customers.

total_spent = sum of Transaction.total_amount grouped by customer
purchase_count = count of distinct receipt_guid per customer

Usage:
    python manage.py recalc_total_spent          # dry-run (показывает расхождения)
    python manage.py recalc_total_spent --apply   # применяет исправления
"""

from decimal import Decimal as D

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Count, Sum

from main.models import CustomUser, Transaction


class Command(BaseCommand):
    help = "Recalculate total_spent and purchase_count from transactions"

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply changes (default is dry-run)",
        )

    def handle(self, *args, **options):
        apply = options["apply"]
        guest_tid = getattr(settings, "GUEST_TELEGRAM_ID", 0)

        # Агрегируем по клиентам из транзакций (без гостя)
        aggregated = (
            Transaction.objects.filter(customer__isnull=False)
            .exclude(customer__telegram_id=guest_tid)
            .values("customer_id")
            .annotate(
                calc_spent=Sum("total_amount"),
                calc_count=Count("receipt_guid", distinct=True),
            )
        )

        agg_map = {
            row["customer_id"]: row
            for row in aggregated
        }

        users = CustomUser.objects.exclude(telegram_id=guest_tid)
        fixed = 0
        total_drift = D("0")

        for user in users:
            agg = agg_map.get(user.id)
            db_spent = user.total_spent or D("0")
            db_count = user.purchase_count or 0

            if agg:
                calc_spent = agg["calc_spent"] or D("0")
                calc_count = agg["calc_count"] or 0
            else:
                calc_spent = D("0")
                calc_count = 0

            spent_diff = db_spent - calc_spent
            count_diff = db_count - calc_count

            if spent_diff != 0 or count_diff != 0:
                self.stdout.write(
                    f"User {user.telegram_id} (id={user.id}): "
                    f"total_spent {db_spent} -> {calc_spent} "
                    f"(delta={spent_diff:+}), "
                    f"purchase_count {db_count} -> {calc_count} "
                    f"(delta={count_diff:+})"
                )
                total_drift += abs(spent_diff)

                if apply:
                    CustomUser.objects.filter(id=user.id).update(
                        total_spent=calc_spent,
                        purchase_count=calc_count,
                    )
                    fixed += 1

        self.stdout.write("")
        self.stdout.write(f"Total users with drift: {fixed if apply else 'see above'}")
        self.stdout.write(f"Total absolute drift: {total_drift}")

        if not apply:
            self.stdout.write(
                self.style.WARNING("\nDry-run mode. Use --apply to fix.")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"\nFixed {fixed} users.")
            )
