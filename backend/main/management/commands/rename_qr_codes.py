from __future__ import annotations

from django.core.management.base import BaseCommand

from src.qr_code import (
    QR_DIR,
    QR_EXTENSION,
    QR_LEGACY_PREFIX,
    get_telegram_id_from_filename,
    qr_code_filename,
    qr_code_media_url_from_filename,
)


class Command(BaseCommand):
    help = "Переименовывает QR-коды с префиксом qr_ в формат user_<telegram_id>.png"

    def handle(self, *args, **options):
        if not QR_DIR.exists():
            self.stdout.write(self.style.WARNING(f"Каталог {QR_DIR} не найден"))
            return

        processed = 0
        renamed = 0
        already_new = 0
        skipped = 0

        pattern = f"{QR_LEGACY_PREFIX}*{QR_EXTENSION}"
        for legacy_path in sorted(QR_DIR.glob(pattern)):
            processed += 1
            telegram_id = get_telegram_id_from_filename(legacy_path.name)
            if telegram_id is None:
                skipped += 1
                continue

            new_filename = qr_code_filename(telegram_id)
            new_path = QR_DIR / new_filename
            if new_path.exists():
                already_new += 1
                continue

            legacy_path.rename(new_path)
            renamed += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f"Переименовано {legacy_path.name} -> {new_filename}"
                )
            )

        self.stdout.write("")
        self.stdout.write(f"Каталог: {QR_DIR}")
        self.stdout.write(f"Обработано файлов: {processed}")
        self.stdout.write(self.style.SUCCESS(f"Переименовано: {renamed}"))
        self.stdout.write(f"Уже в новом формате: {already_new}")
        self.stdout.write(f"Пропущено (не распознано): {skipped}")
        sample_id = 123456789
        sample_filename = qr_code_filename(sample_id)
        sample_url = qr_code_media_url_from_filename(sample_filename)
        placeholder = str(sample_id)
        self.stdout.write("")
        self.stdout.write(
            "Новый формат: "
            f"{sample_filename.replace(placeholder, '<telegram_id>')}"
        )
        self.stdout.write(
            "Пример URL: "
            f"{sample_url.replace(placeholder, '<telegram_id>')}"
        )
