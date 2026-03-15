from django.conf import settings
from django.core.management.base import BaseCommand

from apps.showcase.services import (
    calculate_all_personal_rankings,
    calculate_personal_rankings,
)


class Command(BaseCommand):
    help = "Рассчитать персональные rankings для витрины"

    def add_arguments(self, parser):
        parser.add_argument(
            "--customer-id", type=int, default=None,
            help="ID клиента для расчёта (без этого — все клиенты)",
        )
        parser.add_argument(
            "--force", action="store_true",
            help="Игнорировать PERSONAL_RANKING_ENABLED",
        )

    def handle(self, *args, **options):
        if not options["force"] and not getattr(settings, "PERSONAL_RANKING_ENABLED", False):
            self.stdout.write(
                self.style.WARNING("PERSONAL_RANKING_ENABLED=False. Используйте --force.")
            )
            return

        customer_id = options["customer_id"]

        if customer_id:
            self.stdout.write(f"Расчёт для клиента {customer_id}...")
            stats = calculate_personal_rankings(customer_id)
        else:
            self.stdout.write("Расчёт для всех клиентов...")
            stats = calculate_all_personal_rankings()

        self.stdout.write(self.style.SUCCESS(f"Готово: {stats}"))
