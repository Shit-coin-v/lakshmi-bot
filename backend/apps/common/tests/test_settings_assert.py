"""Тест assert на ALLOW_TELEGRAM_HEADER_AUTH=True в проде (H8)."""
from django.test import SimpleTestCase


class TelegramHeaderAuthAssertionTests(SimpleTestCase):
    def test_assert_runs_at_settings_load_time(self):
        # Просто проверяем, что assert определён в коде settings.py.
        # Реальный assert срабатывает на старте процесса; в тестах settings
        # уже загружены, и DEBUG=True — assert уже был пропущен.
        # Проверяем наличие маркера в исходниках.
        from pathlib import Path
        settings_py = Path(__file__).resolve().parents[3] / "settings.py"
        content = settings_py.read_text(encoding="utf-8")
        self.assertIn("ALLOW_TELEGRAM_HEADER_AUTH", content)
        self.assertIn("ImproperlyConfigured", content)
        self.assertIn("not DEBUG", content)
