import logging

from apps.main.models import Category

logger = logging.getLogger(__name__)


def resolve_category(category_text: str) -> Category | None:
    """Найти Category по точному совпадению с category_text."""
    if not category_text:
        return None

    categories = list(Category.objects.filter(name=category_text))

    if not categories:
        logger.warning("Category not found for text: %s", category_text)
        return None

    if len(categories) == 1:
        return categories[0]

    # Несколько совпадений — предпочитаем leaf (без детей)
    for cat in categories:
        if not cat.children.exists():
            return cat

    return categories[0]
