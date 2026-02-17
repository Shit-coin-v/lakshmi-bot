from django.test import Client, TestCase

from apps.common import security


class OneCTestBase(TestCase):
    """Shared setUp for all 1C integration tests."""

    API_KEY = "test-key"

    def setUp(self):
        security.API_KEY = self.API_KEY
        self.client = Client()
