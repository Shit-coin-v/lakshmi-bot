"""Backfill receipt_total_amount from sum of position total_amount per receipt.

For each receipt_guid, sets receipt_total_amount on the first line (min receipt_line)
equal to the sum of total_amount across all lines of that receipt.

Usage:
    python manage.py backfill_receipt_totals          # dry-run
    python manage.py backfill_receipt_totals --apply   # apply
"""

from django.core.management.base import BaseCommand
from django.db.models import Min, Sum

from main.models import Transaction


class Command(BaseCommand):
    help = "Backfill receipt_total_amount on first line of each receipt"

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply changes (default is dry-run)",
        )

    def handle(self, *args, **options):
        apply = options["apply"]

        # Find receipts where first line has no receipt_total_amount
        receipts = (
            Transaction.objects.filter(receipt_guid__isnull=False)
            .exclude(receipt_guid="")
            .values("receipt_guid")
            .annotate(
                first_line=Min("receipt_line"),
                receipt_sum=Sum("total_amount"),
            )
        )

        updated = 0
        skipped = 0

        for r in receipts:
            first_tx = Transaction.objects.filter(
                receipt_guid=r["receipt_guid"],
                receipt_line=r["first_line"],
            ).first()

            if not first_tx:
                continue

            if first_tx.receipt_total_amount is not None:
                skipped += 1
                continue

            if apply:
                Transaction.objects.filter(pk=first_tx.pk).update(
                    receipt_total_amount=r["receipt_sum"],
                )
            updated += 1

        self.stdout.write(f"Receipts to update: {updated}")
        self.stdout.write(f"Already filled: {skipped}")

        if not apply:
            self.stdout.write(
                self.style.WARNING("\nDry-run. Use --apply to update.")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"\nUpdated {updated} receipts.")
            )
