"""CRM-специфичная пагинация. Наследует HeaderPagination — все дефолты
(page_size=50, max=200) уже выставлены в базовом классе.
Класс существует как точка расширения для будущих CRM-специфичных тонкостей."""
from apps.common.pagination import HeaderPagination


class CRMHeaderPagination(HeaderPagination):
    pass
