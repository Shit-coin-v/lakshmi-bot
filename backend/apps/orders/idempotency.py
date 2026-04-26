"""Кеш идемпотентности для OrderCreate.

Хранит соответствие (customer_id, idempotency_key) → order_id на 1 час,
чтобы повторный POST с тем же ключом возвращал уже созданный заказ
вместо создания дубликата.
"""
from django.core.cache import cache

_TTL_SECONDS = 3600


def _key(customer_id: int, raw_key: str) -> str:
    return f"order-idem:{customer_id}:{raw_key}"


def get_cached_order_id(customer_id: int, raw_key: str) -> int | None:
    val = cache.get(_key(customer_id, raw_key))
    return int(val) if val is not None else None


def set_cached_order_id(customer_id: int, raw_key: str, order_id: int) -> None:
    cache.set(_key(customer_id, raw_key), order_id, _TTL_SECONDS)
