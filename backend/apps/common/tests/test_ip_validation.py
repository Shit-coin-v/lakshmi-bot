from unittest.mock import patch

from django.test import RequestFactory, TestCase

from apps.common.security import _client_ip, _ip_allowed


class ClientIPTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_client_ip_from_x_forwarded_for(self):
        """_client_ip returns LAST IP in XFF (appended by nginx, not spoofable)."""
        request = self.factory.get("/", HTTP_X_FORWARDED_FOR="1.2.3.4, 5.6.7.8")
        self.assertEqual(_client_ip(request), "5.6.7.8")

    def test_client_ip_from_x_real_ip(self):
        request = self.factory.get("/", HTTP_X_REAL_IP="10.0.0.1")
        self.assertEqual(_client_ip(request), "10.0.0.1")

    def test_client_ip_from_remote_addr(self):
        request = self.factory.get("/", REMOTE_ADDR="192.168.1.1")
        self.assertEqual(_client_ip(request), "192.168.1.1")

    def test_xff_takes_precedence_over_x_real_ip(self):
        request = self.factory.get(
            "/", HTTP_X_FORWARDED_FOR="1.1.1.1", HTTP_X_REAL_IP="2.2.2.2"
        )
        self.assertEqual(_client_ip(request), "1.1.1.1")


class IPAllowedTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @patch("apps.common.security._ALLOWED_IPS", ())
    def test_empty_whitelist_allows_all(self):
        request = self.factory.get("/", REMOTE_ADDR="1.2.3.4")
        self.assertTrue(_ip_allowed(request))

    @patch("apps.common.security._ALLOWED_IPS", ("10.0.0.1",))
    def test_exact_match(self):
        request = self.factory.get("/", REMOTE_ADDR="10.0.0.1")
        self.assertTrue(_ip_allowed(request))

    @patch("apps.common.security._ALLOWED_IPS", ("192.168.*",))
    def test_wildcard_match(self):
        request = self.factory.get("/", REMOTE_ADDR="192.168.1.50")
        self.assertTrue(_ip_allowed(request))

    @patch("apps.common.security._ALLOWED_IPS", ("10.0.0.1",))
    def test_no_match_returns_false(self):
        request = self.factory.get("/", REMOTE_ADDR="99.99.99.99")
        self.assertFalse(_ip_allowed(request))

    @patch("apps.common.security._ALLOWED_IPS", ("10.0.0.1",))
    def test_ip_allowed_uses_client_ip_not_x_real_ip(self):
        """Key test: _ip_allowed must use _client_ip() which reads XFF first,
        not HTTP_X_REAL_IP directly. If XFF says 10.0.0.1 but X-Real-IP
        says 99.99.99.99, access should be allowed."""
        request = self.factory.get(
            "/",
            HTTP_X_FORWARDED_FOR="10.0.0.1",
            HTTP_X_REAL_IP="99.99.99.99",
            REMOTE_ADDR="99.99.99.99",
        )
        self.assertTrue(_ip_allowed(request))

    @patch("apps.common.security._ALLOWED_IPS", ("10.0.0.1",))
    def test_ip_allowed_denies_when_xff_not_in_whitelist(self):
        """Complementary: XFF says 99.99.99.99 but X-Real-IP says 10.0.0.1 —
        should be denied because _client_ip reads XFF first."""
        request = self.factory.get(
            "/",
            HTTP_X_FORWARDED_FOR="99.99.99.99",
            HTTP_X_REAL_IP="10.0.0.1",
            REMOTE_ADDR="10.0.0.1",
        )
        self.assertFalse(_ip_allowed(request))
