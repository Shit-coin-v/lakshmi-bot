from django.core.management.base import BaseCommand

from apps.integrations.onec.category_resolver import resolve_category
from apps.main.models import Product


class Command(BaseCommand):
    help = "Привязать товары к категориям по category_text"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Показать что будет привязано, без записи",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        orphans = Product.objects.filter(
            category__isnull=True,
            category_text__isnull=False,
        )
        total = orphans.count()
        self.stdout.write(f"Товаров без категории: {total}")

        if total == 0:
            self.stdout.write(self.style.SUCCESS("Нечего привязывать."))
            return

        # Кеш: category_text → Category
        cache = {}
        not_found = set()

        texts = orphans.values_list("category_text", flat=True).distinct()
        for text in texts:
            cat = resolve_category(text)
            if cat:
                cache[text] = cat
            else:
                not_found.add(text)

        # Привязка
        to_update = []
        for product in orphans.iterator(chunk_size=500):
            cat = cache.get(product.category_text)
            if cat:
                product.category = cat
                to_update.append(product)

        if dry_run:
            self.stdout.write(f"[DRY RUN] Будет привязано: {len(to_update)}")
            if not_found:
                self.stdout.write(f"[DRY RUN] Не найдено категорий для: {not_found}")
            return

        if to_update:
            Product.objects.bulk_update(to_update, ["category_id"], batch_size=500)

        self.stdout.write(self.style.SUCCESS(f"Привязано: {len(to_update)}"))
        if not_found:
            self.stdout.write(self.style.WARNING(f"Не найдено категорий для: {not_found}"))
