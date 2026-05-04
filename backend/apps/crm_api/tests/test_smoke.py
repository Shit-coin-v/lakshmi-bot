"""Smoke-тест: app зарегистрирован и доступен Django."""
from django.apps import apps
from django.test import TestCase


class CrmApiSmokeTests(TestCase):
    def test_app_is_registered(self):
        self.assertTrue(apps.is_installed("apps.crm_api"))

    def test_permission_class_importable(self):
        from apps.crm_api.permissions import IsCRMStaff
        self.assertTrue(callable(IsCRMStaff))

    def test_pagination_class_importable(self):
        from apps.crm_api.pagination import CRMHeaderPagination
        self.assertEqual(CRMHeaderPagination.page_size, 50)
        self.assertEqual(CRMHeaderPagination.max_page_size, 200)
