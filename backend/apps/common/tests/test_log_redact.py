"""Тесты маскирования токенов и redact-фильтра логирования."""
import logging
import re

from django.test import SimpleTestCase

from shared.log_redact import RedactSecretsFilter, mask_token


class MaskTokenTests(SimpleTestCase):
    def test_long_token_masked_with_prefix_suffix_hash(self):
        """Длинный токен -> "<префикс6>…<суффикс4>#<8hex>"."""
        result = mask_token("1234567890abcdefghij")
        # Структура: 6 символов "…" 4 символа "#" 8 hex.
        self.assertRegex(result, r"^123456…ghij#[0-9a-f]{8}$")

    def test_empty_string_returns_placeholder(self):
        self.assertEqual(mask_token(""), "<empty>")

    def test_none_returns_placeholder(self):
        self.assertEqual(mask_token(None), "<empty>")

    def test_short_token_returns_short_hash(self):
        """Токен длиной <= prefix+suffix не печатается, только хеш."""
        result = mask_token("short")
        self.assertRegex(result, r"^<short#[0-9a-f]{8}>$")

    def test_boundary_short_token(self):
        """Длина ровно prefix+suffix (10) тоже считается коротким."""
        result = mask_token("1234567890")
        self.assertRegex(result, r"^<short#[0-9a-f]{8}>$")

    def test_same_token_yields_same_hash_suffix(self):
        """Детерминизм: одно значение -> один хеш-суффикс."""
        a = mask_token("abcdefghij_token_value_xyz")
        b = mask_token("abcdefghij_token_value_xyz")
        self.assertEqual(a, b)

    def test_different_tokens_yield_different_hash_suffix(self):
        a = mask_token("token_one_value_long_enough")
        b = mask_token("token_two_value_long_enough")
        # Хеш-сегмент после '#' должен отличаться.
        self.assertNotEqual(a.split("#")[-1], b.split("#")[-1])


class RedactSecretsFilterTests(SimpleTestCase):
    def setUp(self):
        self.filter = RedactSecretsFilter()

    def _make_record(self, msg: str, args=None) -> logging.LogRecord:
        return logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname=__file__,
            lineno=1,
            msg=msg,
            args=args,
            exc_info=None,
        )

    def test_password_value_redacted(self):
        record = self._make_record("auth ok password=hunter2 user=alice")
        self.assertTrue(self.filter.filter(record))
        rendered = record.getMessage()
        self.assertIn("password=***", rendered)
        # Несекретный ключ user= остаётся как есть.
        self.assertIn("user=alice", rendered)

    def test_token_key_redacted(self):
        record = self._make_record("login token=abcdef12345 id=42")
        self.assertTrue(self.filter.filter(record))
        rendered = record.getMessage()
        self.assertIn("token=***", rendered)
        self.assertIn("id=42", rendered)

    def test_api_key_redacted(self):
        record = self._make_record("call api_key=SECRETVALUE count=10")
        self.assertTrue(self.filter.filter(record))
        rendered = record.getMessage()
        self.assertIn("api_key=***", rendered)
        self.assertIn("count=10", rendered)

    def test_bot_token_redacted(self):
        record = self._make_record("bot_token=12345:abcdef started")
        self.assertTrue(self.filter.filter(record))
        rendered = record.getMessage()
        self.assertIn("bot_token=***", rendered)

    def test_secret_redacted(self):
        record = self._make_record("config secret=topsecret mode=prod")
        self.assertTrue(self.filter.filter(record))
        rendered = record.getMessage()
        self.assertIn("secret=***", rendered)
        self.assertIn("mode=prod", rendered)

    def test_authorization_redacted(self):
        record = self._make_record("header authorization=Bearer_xyz123 ok")
        self.assertTrue(self.filter.filter(record))
        rendered = record.getMessage()
        self.assertIn("authorization=***", rendered)

    def test_non_secret_keys_untouched(self):
        record = self._make_record("user=alice id=42 count=5")
        self.assertTrue(self.filter.filter(record))
        rendered = record.getMessage()
        self.assertEqual(rendered, "user=alice id=42 count=5")

    def test_filter_returns_true_to_keep_record(self):
        """Фильтр не должен глотать записи."""
        record = self._make_record("plain message without secrets")
        self.assertTrue(self.filter.filter(record))

    def test_args_are_rendered_before_redaction(self):
        """args подставляются в msg, затем маскируются."""
        record = self._make_record("login password=%s ok", args=("hunter2",))
        self.assertTrue(self.filter.filter(record))
        rendered = record.getMessage()
        self.assertIn("password=***", rendered)
        self.assertNotIn("hunter2", rendered)

    def test_quoted_value_redacted(self):
        record = self._make_record('payload password="hunter2" ok')
        self.assertTrue(self.filter.filter(record))
        rendered = record.getMessage()
        # Кавычки сохраняются, значение заменено.
        self.assertRegex(rendered, r'password="\*\*\*"')
