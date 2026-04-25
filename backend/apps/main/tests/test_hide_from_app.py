"""Тесты скрытия категорий через Category.hide_from_app.

Покрывают все клиентские сценарии, где скрытая категория или её товары
не должны попадать в Flutter-приложение: каталог, дочерние категории,
список товаров, поиск, витрина (showcase). Также проверяют staff-bypass
через ``?include_hidden=true`` + валидный X-Api-Key.
"""

from __future__ import annotations

from django.test import Client, TestCase, override_settings
from django.utils import timezone

from apps.main.models import Category, Product
from apps.showcase.models import ProductRanking


_TEST_SETTINGS = {
    "CACHES": {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
    "INTEGRATION_API_KEY": "test-key",
    "ALLOW_TELEGRAM_HEADER_AUTH": True,
}


@override_settings(**_TEST_SETTINGS)
class HiddenCategoryClientTests(TestCase):
    """Скрытая категория не приходит в клиентский каталог."""

    def setUp(self):
        self.client = Client()
        self.visible = Category.objects.create(
            name="Овощи", is_active=True, hide_from_app=False,
        )
        self.hidden = Category.objects.create(
            name="ТАБАЧНЫЕ ИЗДЕЛИЯ", is_active=True, hide_from_app=True,
        )
        self.hidden_child = Category.objects.create(
            name="Сигареты", parent=self.hidden, is_active=True, hide_from_app=False,
        )
        self.visible_child = Category.objects.create(
            name="Помидоры", parent=self.visible, is_active=True, hide_from_app=False,
        )

    def test_hidden_root_not_in_catalog(self):
        response = self.client.get("/api/catalog/root/")
        self.assertEqual(response.status_code, 200)
        names = [c["name"] for c in response.json()]
        self.assertIn("Овощи", names)
        self.assertNotIn("ТАБАЧНЫЕ ИЗДЕЛИЯ", names)

    def test_hidden_descendant_not_in_children(self):
        # Запрашиваем потомков самого скрытого корня — должен вернуть пусто
        response = self.client.get(f"/api/catalog/{self.hidden.pk}/children/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_visible_children_returned(self):
        response = self.client.get(f"/api/catalog/{self.visible.pk}/children/")
        self.assertEqual(response.status_code, 200)
        names = [c["name"] for c in response.json()]
        self.assertIn("Помидоры", names)


@override_settings(**_TEST_SETTINGS)
class HiddenCategoryStaffTests(TestCase):
    """Staff (Photo Studio) с include_hidden=true видят скрытое."""

    def setUp(self):
        self.client = Client()
        Category.objects.create(
            name="Овощи", is_active=True, hide_from_app=False,
        )
        Category.objects.create(
            name="Тестовая группа", is_active=True, hide_from_app=True,
        )

    def test_staff_sees_hidden_with_api_key_and_param(self):
        response = self.client.get(
            "/api/catalog/root/?include_hidden=true",
            HTTP_X_API_KEY="test-key",
        )
        self.assertEqual(response.status_code, 200)
        names = [c["name"] for c in response.json()]
        self.assertIn("Тестовая группа", names)
        self.assertIn("Овощи", names)

    def test_param_without_api_key_ignored(self):
        # Обычный клиент пытается обмануть параметром — должен получить
        # обычный (отфильтрованный) ответ.
        response = self.client.get("/api/catalog/root/?include_hidden=true")
        self.assertEqual(response.status_code, 200)
        names = [c["name"] for c in response.json()]
        self.assertNotIn("Тестовая группа", names)

    def test_param_with_invalid_api_key_ignored(self):
        response = self.client.get(
            "/api/catalog/root/?include_hidden=true",
            HTTP_X_API_KEY="wrong-key",
        )
        self.assertEqual(response.status_code, 200)
        names = [c["name"] for c in response.json()]
        self.assertNotIn("Тестовая группа", names)

    def test_api_key_without_param_filters(self):
        # Photo Studio шлёт X-Api-Key, но без include_hidden — фильтр работает.
        response = self.client.get(
            "/api/catalog/root/",
            HTTP_X_API_KEY="test-key",
        )
        self.assertEqual(response.status_code, 200)
        names = [c["name"] for c in response.json()]
        self.assertNotIn("Тестовая группа", names)


@override_settings(**_TEST_SETTINGS)
class HiddenProductTests(TestCase):
    """Товары скрытых категорий не приходят в клиентские API."""

    def setUp(self):
        self.client = Client()
        self.visible_cat = Category.objects.create(
            name="Овощи", is_active=True, hide_from_app=False,
        )
        self.hidden_cat = Category.objects.create(
            name="НЕПРОДОВОЛЬСТВЕННЫЕ ТОВАРЫ", is_active=True, hide_from_app=True,
        )
        self.hidden_subcat = Category.objects.create(
            name="Бытовая химия", parent=self.hidden_cat,
            is_active=True, hide_from_app=False,
        )
        self.visible_product = Product.objects.create(
            product_code="V1", name="Помидор", price="50.00", store_id=1,
            category=self.visible_cat,
        )
        self.hidden_product = Product.objects.create(
            product_code="H1", name="Сигареты Marlboro", price="200.00", store_id=1,
            category=self.hidden_cat,
        )
        # Товар в дочерней категории скрытого корня — тоже должен быть скрыт.
        self.hidden_descendant_product = Product.objects.create(
            product_code="H2", name="Чистящее средство", price="150.00", store_id=1,
            category=self.hidden_subcat,
        )

    def test_hidden_product_not_in_product_list(self):
        response = self.client.get("/api/products/")
        self.assertEqual(response.status_code, 200)
        codes = [p["product_code"] for p in response.json()]
        self.assertIn("V1", codes)
        self.assertNotIn("H1", codes)
        self.assertNotIn("H2", codes)

    def test_hidden_product_not_found_via_search(self):
        # Поиск по имени скрытого товара не должен его находить в клиенте.
        response = self.client.get("/api/products/?search=Marlboro")
        self.assertEqual(response.status_code, 200)
        codes = [p["product_code"] for p in response.json()]
        self.assertNotIn("H1", codes)

    def test_hidden_product_not_in_filtered_by_hidden_category(self):
        # Если клиент знает id скрытой категории — товары всё равно скрыты.
        response = self.client.get(
            f"/api/products/?category_id={self.hidden_cat.pk}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_client_cannot_use_include_hidden(self):
        # Обычный клиент не может получить скрытые товары через include_hidden.
        response = self.client.get("/api/products/?include_hidden=true")
        self.assertEqual(response.status_code, 200)
        codes = [p["product_code"] for p in response.json()]
        self.assertNotIn("H1", codes)
        self.assertNotIn("H2", codes)

    def test_staff_can_see_hidden_products(self):
        response = self.client.get(
            "/api/products/?include_hidden=true",
            HTTP_X_API_KEY="test-key",
        )
        self.assertEqual(response.status_code, 200)
        codes = [p["product_code"] for p in response.json()]
        self.assertIn("V1", codes)
        self.assertIn("H1", codes)
        self.assertIn("H2", codes)


@override_settings(**_TEST_SETTINGS)
class HiddenInShowcaseTests(TestCase):
    """Скрытые товары не попадают на витрину (главная страница Flutter)."""

    def setUp(self):
        self.client = Client()
        self.visible_cat = Category.objects.create(
            name="Овощи", is_active=True, hide_from_app=False,
        )
        self.hidden_cat = Category.objects.create(
            name="Тимир тест", is_active=True, hide_from_app=True,
        )
        self.visible_product = Product.objects.create(
            product_code="SV1", name="Помидор", price="50.00", store_id=1,
            category=self.visible_cat, stock=10,
        )
        self.hidden_product = Product.objects.create(
            product_code="SH1", name="Тестовый товар", price="999.00", store_id=1,
            category=self.hidden_cat, stock=10,
        )
        # Эмулируем глобальный ranking — пусть скрытый товар имеет высокий
        # score, чтобы убедиться, что фильтрация не зависит от ranking.
        now = timezone.now()
        ProductRanking.objects.create(
            customer=None, product=self.hidden_product, score=999.0,
            calculated_at=now,
        )
        ProductRanking.objects.create(
            customer=None, product=self.visible_product, score=10.0,
            calculated_at=now,
        )

    def test_hidden_product_excluded_from_showcase(self):
        response = self.client.get("/api/showcase/")
        self.assertEqual(response.status_code, 200)
        codes = [p["product_code"] for p in response.json()]
        self.assertIn("SV1", codes)
        self.assertNotIn("SH1", codes)

    def test_hidden_product_not_found_via_showcase_search(self):
        response = self.client.get("/api/showcase/?search=Тестовый")
        self.assertEqual(response.status_code, 200)
        codes = [p["product_code"] for p in response.json()]
        self.assertNotIn("SH1", codes)
