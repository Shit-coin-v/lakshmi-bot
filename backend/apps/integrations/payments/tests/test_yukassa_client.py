"""Tests for ЮKassa HTTP client retry logic."""

import requests
from unittest.mock import MagicMock, patch
from django.test import TestCase

from apps.integrations.payments.yukassa_client import (
    _extract_status_code,
    _is_logical_error,
    _is_retryable_error,
    _with_http_retry,
    YukassaLogicalError,
)


class ExtractStatusCodeTests(TestCase):
    def test_requests_http_error(self):
        resp = MagicMock(status_code=400)
        exc = requests.HTTPError(response=resp)
        self.assertEqual(_extract_status_code(exc), 400)

    def test_exception_with_status_code_attr(self):
        exc = Exception("fail")
        exc.status_code = 503
        self.assertEqual(_extract_status_code(exc), 503)

    def test_no_status_in_plain_exception(self):
        exc = Exception("HTTP 502 Bad Gateway")
        self.assertIsNone(_extract_status_code(exc))

    def test_no_status(self):
        exc = Exception("network timeout")
        self.assertIsNone(_extract_status_code(exc))


class IsRetryableErrorTests(TestCase):
    def test_429_is_retryable(self):
        resp = MagicMock(status_code=429)
        exc = requests.HTTPError(response=resp)
        self.assertTrue(_is_retryable_error(exc))

    def test_502_is_retryable(self):
        resp = MagicMock(status_code=502)
        exc = requests.HTTPError(response=resp)
        self.assertTrue(_is_retryable_error(exc))

    def test_503_is_retryable(self):
        resp = MagicMock(status_code=503)
        exc = requests.HTTPError(response=resp)
        self.assertTrue(_is_retryable_error(exc))

    def test_504_is_retryable(self):
        resp = MagicMock(status_code=504)
        exc = requests.HTTPError(response=resp)
        self.assertTrue(_is_retryable_error(exc))

    def test_400_is_not_retryable(self):
        resp = MagicMock(status_code=400)
        exc = requests.HTTPError(response=resp)
        self.assertFalse(_is_retryable_error(exc))

    def test_403_is_not_retryable(self):
        resp = MagicMock(status_code=403)
        exc = requests.HTTPError(response=resp)
        self.assertFalse(_is_retryable_error(exc))

    def test_connection_error_is_retryable(self):
        exc = requests.ConnectionError("refused")
        self.assertTrue(_is_retryable_error(exc))

    def test_timeout_is_retryable(self):
        exc = requests.Timeout("timeout")
        self.assertTrue(_is_retryable_error(exc))

    def test_os_error_is_retryable(self):
        exc = OSError("broken pipe")
        self.assertTrue(_is_retryable_error(exc))

    def test_value_error_is_not_retryable(self):
        exc = ValueError("bad value")
        self.assertFalse(_is_retryable_error(exc))


class IsLogicalErrorTests(TestCase):
    def test_400_is_logical(self):
        resp = MagicMock(status_code=400)
        exc = requests.HTTPError(response=resp)
        self.assertTrue(_is_logical_error(exc))

    def test_401_is_logical(self):
        resp = MagicMock(status_code=401)
        exc = requests.HTTPError(response=resp)
        self.assertTrue(_is_logical_error(exc))

    def test_404_is_logical(self):
        resp = MagicMock(status_code=404)
        exc = requests.HTTPError(response=resp)
        self.assertTrue(_is_logical_error(exc))

    def test_409_is_logical(self):
        resp = MagicMock(status_code=409)
        exc = requests.HTTPError(response=resp)
        self.assertTrue(_is_logical_error(exc))

    def test_429_is_not_logical(self):
        resp = MagicMock(status_code=429)
        exc = requests.HTTPError(response=resp)
        self.assertFalse(_is_logical_error(exc))

    def test_502_is_not_logical(self):
        resp = MagicMock(status_code=502)
        exc = requests.HTTPError(response=resp)
        self.assertFalse(_is_logical_error(exc))

    def test_connection_error_is_not_logical(self):
        exc = requests.ConnectionError("refused")
        self.assertFalse(_is_logical_error(exc))


class WithHttpRetryTests(TestCase):
    @patch("apps.integrations.payments.yukassa_client.time.sleep")
    def test_success_on_first_attempt(self, mock_sleep):
        fn = MagicMock(return_value="ok")
        result = _with_http_retry(fn, "arg1", key="val")
        self.assertEqual(result, "ok")
        fn.assert_called_once_with("arg1", key="val")
        mock_sleep.assert_not_called()

    @patch("apps.integrations.payments.yukassa_client.time.sleep")
    def test_retry_on_connection_error_then_success(self, mock_sleep):
        fn = MagicMock(side_effect=[requests.ConnectionError("fail"), "ok"])
        result = _with_http_retry(fn, "arg1")
        self.assertEqual(result, "ok")
        self.assertEqual(fn.call_count, 2)
        mock_sleep.assert_called_once_with(1)

    @patch("apps.integrations.payments.yukassa_client.time.sleep")
    def test_retry_on_timeout_exhausted(self, mock_sleep):
        fn = MagicMock(side_effect=requests.Timeout("timeout"))
        with self.assertRaises(requests.Timeout):
            _with_http_retry(fn)
        self.assertEqual(fn.call_count, 2)
        mock_sleep.assert_called_once_with(1)

    @patch("apps.integrations.payments.yukassa_client.time.sleep")
    def test_retry_on_429_then_success(self, mock_sleep):
        resp_429 = MagicMock(status_code=429)
        fn = MagicMock(side_effect=[
            requests.HTTPError(response=resp_429),
            "ok",
        ])
        result = _with_http_retry(fn)
        self.assertEqual(result, "ok")
        self.assertEqual(fn.call_count, 2)

    @patch("apps.integrations.payments.yukassa_client.time.sleep")
    def test_logical_error_400_no_retry(self, mock_sleep):
        resp_400 = MagicMock(status_code=400)
        fn = MagicMock(side_effect=requests.HTTPError(response=resp_400))
        with self.assertRaises(YukassaLogicalError):
            _with_http_retry(fn)
        self.assertEqual(fn.call_count, 1)
        mock_sleep.assert_not_called()

    @patch("apps.integrations.payments.yukassa_client.time.sleep")
    def test_logical_error_403_no_retry(self, mock_sleep):
        resp_403 = MagicMock(status_code=403)
        fn = MagicMock(side_effect=requests.HTTPError(response=resp_403))
        with self.assertRaises(YukassaLogicalError):
            _with_http_retry(fn)
        self.assertEqual(fn.call_count, 1)

    @patch("apps.integrations.payments.yukassa_client.time.sleep")
    def test_unknown_error_not_retried(self, mock_sleep):
        fn = MagicMock(side_effect=ValueError("bad"))
        with self.assertRaises(ValueError):
            _with_http_retry(fn)
        self.assertEqual(fn.call_count, 1)
        mock_sleep.assert_not_called()

    @patch("apps.integrations.payments.yukassa_client.time.sleep")
    def test_retry_on_502_then_success(self, mock_sleep):
        resp_502 = MagicMock(status_code=502)
        fn = MagicMock(side_effect=[
            requests.HTTPError(response=resp_502),
            "ok",
        ])
        result = _with_http_retry(fn)
        self.assertEqual(result, "ok")
        self.assertEqual(fn.call_count, 2)
