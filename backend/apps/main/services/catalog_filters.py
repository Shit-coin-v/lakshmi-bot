"""Хелперы для скрытия категорий и товаров из клиентских API.

Категория с ``hide_from_app=True`` (и все её потомки) не возвращается
клиенту: каталог, поиск, витрина, рекомендации. Staff/Photo Studio
получают полный каталог через ``?include_hidden=true`` + валидный
``X-Api-Key``.
"""

from __future__ import annotations

from hmac import compare_digest

from apps.main.models import Category


_TRUE_TOKENS = {"true", "1", "yes"}


def get_hidden_category_ids() -> set[int]:
    """ID скрытых категорий + всех их потомков (BFS).

    Скрывается рекурсивно: если родитель помечен ``hide_from_app=True``,
    его дочерние тоже скрыты — даже если у них флаг не выставлен.
    """
    initial = list(
        Category.objects.filter(hide_from_app=True).values_list("id", flat=True)
    )
    if not initial:
        return set()

    result: set[int] = set(initial)
    queue: list[int] = list(initial)
    while queue:
        parent_id = queue.pop()
        children = list(
            Category.objects.filter(parent_id=parent_id).values_list("id", flat=True)
        )
        for cid in children:
            if cid not in result:
                result.add(cid)
                queue.append(cid)
    return result


def request_can_view_hidden(request) -> bool:
    """Разрешить показ скрытых данных, если запрос прошёл staff-аутентификацию.

    Условия:
    - валидный ``X-Api-Key`` (совпадает с ``INTEGRATION_API_KEY``);
    - параметр ``?include_hidden=true`` в query string.

    Без обоих — False (обычный клиент Flutter).
    """
    if not _request_has_valid_api_key(request):
        return False
    raw = (request.query_params.get("include_hidden") or "").strip().lower()
    return raw in _TRUE_TOKENS


def _request_has_valid_api_key(request) -> bool:
    from django.conf import settings as dj_settings

    api_key = (getattr(dj_settings, "INTEGRATION_API_KEY", "") or "").strip()
    if not api_key:
        from apps.common.security import API_KEY as security_api_key

        api_key = (security_api_key or "").strip()
    if not api_key:
        return False

    provided = (
        request.headers.get("X-Api-Key")
        or request.META.get("HTTP_X_API_KEY")
        or ""
    ).strip()
    if not provided:
        return False
    return compare_digest(provided, api_key)
