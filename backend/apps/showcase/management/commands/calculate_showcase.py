from django.core.management.base import BaseCommand

from apps.showcase.services import calculate_global_rankings


class Command(BaseCommand):
    help = "Рассчитать глобальную витрину (ranking товаров по продажам)"

    def handle(self, *args, **options):
        self.stdout.write("Запуск расчёта глобальной витрины...")

        stats = calculate_global_rankings()

        self.stdout.write(
            self.style.SUCCESS(
                f"Готово. Товаров: {stats['total_products']}, "
                f"макс. продаж: {stats.get('max_sold', 0)}, "
                f"удалено старых: {stats.get('deleted_old', 0)}."
            )
        )
