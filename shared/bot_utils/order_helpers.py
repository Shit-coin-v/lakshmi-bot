"""Shared order helpers for staff bots (courier, picker)."""
from __future__ import annotations

from types import SimpleNamespace

from shared.clients.backend_client import BackendClient


async def fetch_order_with_items(backend: BackendClient, order_id: int):
    """Fetch a single order with items via HTTP API. Returns SimpleNamespace or None."""
    data = await backend.get_order_detail(order_id)
    if data is None:
        return None

    items = []
    for item_data in data.get("items", []):
        product = SimpleNamespace(
            name=item_data.get("product_name", ""),
            id=item_data.get("product_id"),
        )
        item = SimpleNamespace(
            product=product,
            product_id=item_data.get("product_id"),
            quantity=item_data["quantity"],
            price_at_moment=float(item_data["price_at_moment"]),
        )
        items.append(item)

    order_fields = {k: v for k, v in data.items() if k != "items"}
    for field in ("total_price", "products_price", "delivery_price"):
        if field in order_fields and order_fields[field] is not None:
            order_fields[field] = float(order_fields[field])

    order = SimpleNamespace(**order_fields)
    order.items = items
    return order


def to_order_namespace(orders: list[dict]) -> list[SimpleNamespace]:
    """Convert list of order dicts to SimpleNamespace objects."""
    result = []
    for o in orders:
        if "total_price" in o and o["total_price"] is not None:
            o["total_price"] = float(o["total_price"])
        result.append(SimpleNamespace(**o))
    return result
