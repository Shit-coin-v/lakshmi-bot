import logging
from functools import partial
from types import SimpleNamespace

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from shared.clients.backend_client import BackendClient
from shared.bot_utils.access import check_allowed
from shared.bot_utils.chat_cleanup import send_clean
from shared.bot_utils.retry import is_in_flight, schedule_retry
from config import PICKER_ALLOWED_TG_IDS, BACKEND_URL, INTEGRATION_API_KEY
from keyboards import (
    get_new_orders_keyboard,
    get_active_orders_keyboard,
    get_order_detail_keyboard,
    payment_label,
    fulfillment_label,
)

logger = logging.getLogger(__name__)

router = Router()

backend = BackendClient(BACKEND_URL, INTEGRATION_API_KEY)

_STATUS_DISPLAY = {
    "new": "Новый заказ",
    "accepted": "Заказ принят",
    "assembly": "Заказ собирается",
    "ready": "Заказ собран",
    "completed": "Завершён",
}

# Transition map: action -> (expected_current_status, new_status)
_TRANSITIONS = {
    "accept": ("new", "accepted"),
    "assemble": ("accepted", "assembly"),
    "ready": ("assembly", "ready"),
    "pickup_complete": ("ready", "completed"),
}

# Statuses visible to picker
_PICKER_STATUSES = ("new", "accepted", "assembly", "ready")


def _to_namespace(orders: list[dict]) -> list[SimpleNamespace]:
    result = []
    for o in orders:
        if "total_price" in o and o["total_price"] is not None:
            o["total_price"] = float(o["total_price"])
        result.append(SimpleNamespace(**o))
    return result


async def _fetch_new_orders():
    orders = await backend.get_new_orders()
    return _to_namespace(orders)


async def _fetch_active_orders(picker_tg_id: int):
    orders = await backend.get_picker_active_orders(picker_tg_id)
    return _to_namespace(orders)


async def _fetch_order_with_items(order_id: int):
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


def _format_order_detail(order) -> str:
    lines = [
        f"<b>Заказ #{order.id}</b>",
        f"📦 Тип: {fulfillment_label(order.fulfillment_type)}",
        f"🏠 Адрес: {order.address}",
        f"📞 Телефон: {order.phone}",
    ]

    if order.comment:
        lines.append(f"💬 Комментарий: {order.comment}")

    lines.append("")
    lines.append("<b>Состав:</b>")
    for item in order.items:
        name = item.product.name if item.product else f"Товар #{item.product_id}"
        price = int(item.price_at_moment) if item.price_at_moment == int(item.price_at_moment) else item.price_at_moment
        lines.append(f"  • {name} x{item.quantity} — {price}₽")

    total = int(order.total_price) if order.total_price == int(order.total_price) else order.total_price
    lines.append("")
    lines.append(f"<b>Итого:</b> {total}₽")
    lines.append(f"<b>Оплата:</b> {payment_label(order.payment_method)}")

    status_text = _STATUS_DISPLAY.get(order.status, order.status)
    lines.append(f"<b>Статус:</b> {status_text}")

    return "\n".join(lines)


async def _update_order_status(order_id: int, new_status: str, assembler_id: int | None = None) -> bool:
    return await backend.update_order_status(
        order_id, new_status, assembler_id=assembler_id,
    )


# --- Cleanup notifications ---

async def _cleanup_notifications(bot: Bot, chat_id: int, user_id: int):
    notifications = await backend.get_picker_messages(user_id)
    if not notifications:
        return
    for n in notifications:
        try:
            await bot.delete_message(chat_id, n["telegram_message_id"])
        except Exception:
            pass
    ids = [n["id"] for n in notifications]
    await backend.bulk_delete_picker_messages(ids)


# --- Command: /orders ---

@router.message(Command("orders"))
async def cmd_orders(message: Message):
    if not check_allowed(message.from_user.id, PICKER_ALLOWED_TG_IDS):
        await send_clean(message, "Доступ запрещён.")
        return
    await _cleanup_notifications(message.bot, message.chat.id, message.from_user.id)
    orders = await _fetch_new_orders()
    keyboard = get_new_orders_keyboard(orders)
    await send_clean(message, "📦 Новые заказы:", reply_markup=keyboard)


# --- Command: /active ---

@router.message(Command("active"))
async def cmd_active(message: Message):
    if not check_allowed(message.from_user.id, PICKER_ALLOWED_TG_IDS):
        await send_clean(message, "Доступ запрещён.")
        return
    orders = await _fetch_active_orders(message.from_user.id)
    keyboard = get_active_orders_keyboard(orders)
    await send_clean(message, "🔧 Мои заказы:", reply_markup=keyboard)


# --- Command: /completed ---

@router.message(Command("completed"))
async def cmd_completed(message: Message):
    if not check_allowed(message.from_user.id, PICKER_ALLOWED_TG_IDS):
        await send_clean(message, "Доступ запрещён.")
        return

    result = await backend.get_assembled_today(message.from_user.id)
    count = result.get("count", 0) if result else 0

    if count == 0:
        await send_clean(message, "📋 Сегодня собранных заказов пока нет.")
        return

    await send_clean(message, f"📋 Отчёт за сегодня:\n\n📦 Собрано заказов: {count}")


# --- Callback: back to orders list ---

@router.callback_query(F.data == "orders:back")
async def orders_back(callback: CallbackQuery):
    if not check_allowed(callback.from_user.id, PICKER_ALLOWED_TG_IDS):
        await callback.answer("Доступ запрещён.", show_alert=True)
        return

    orders = await _fetch_new_orders()
    keyboard = get_new_orders_keyboard(orders)
    await callback.message.edit_text("📦 Новые заказы:", reply_markup=keyboard)
    await callback.answer()


# --- Callback: noop ---

@router.callback_query(F.data == "noop")
async def noop_callback(callback: CallbackQuery):
    await callback.answer()


# --- Callback: pending ---

@router.callback_query(F.data.startswith("order:") & F.data.endswith(":pending"))
async def order_pending_noop(callback: CallbackQuery):
    await callback.answer("Статус обновляется, подождите...", show_alert=False)


# --- Callback: order detail ---

@router.callback_query(F.data.startswith("order:") & F.data.endswith(":detail"))
async def order_detail(callback: CallbackQuery):
    if not check_allowed(callback.from_user.id, PICKER_ALLOWED_TG_IDS):
        await callback.answer("Доступ запрещён.", show_alert=True)
        return

    parts = callback.data.split(":")
    try:
        order_id = int(parts[1])
    except (IndexError, ValueError):
        await callback.answer("Неверный заказ.", show_alert=True)
        return

    order = await _fetch_order_with_items(order_id)
    if not order or order.status not in _PICKER_STATUSES:
        await callback.answer("Заказ не найден или уже завершён.", show_alert=True)
        return

    text = _format_order_detail(order)
    keyboard = get_order_detail_keyboard(order)
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


# --- Retry callbacks ---

async def _on_retry_success(
    bot: Bot, chat_id: int, message_id: int, order_id: int, new_status: str,
) -> None:
    try:
        if new_status == "completed":
            # Pickup completed
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=f"🤝 Заказ #{order_id} выдан клиенту!",
            )
            return

        order = await _fetch_order_with_items(order_id)
        if not order:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=f"✅ Статус заказа #{order_id} обновлён.",
            )
            return

        text = _format_order_detail(order)
        keyboard = get_order_detail_keyboard(order)
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML",
        )
    except Exception:
        logger.exception("Failed to update message after retry success for order %d", order_id)


async def _on_retry_failure(
    bot: Bot, chat_id: int, message_id: int, order_id: int, new_status: str,
) -> None:
    try:
        order = await _fetch_order_with_items(order_id)
        if order:
            text = _format_order_detail(order)
            text += "\n\n❌ <b>Не удалось обновить статус. Попробуйте снова.</b>"
            keyboard = get_order_detail_keyboard(order)
        else:
            text = f"❌ Не удалось обновить статус заказа #{order_id}. Попробуйте снова."
            keyboard = None

        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML",
        )
    except Exception:
        logger.exception("Failed to update message after retry failure for order %d", order_id)


# --- Callback: status transitions ---

@router.callback_query(F.data.startswith("order:") & (
    F.data.endswith(":accept")
    | F.data.endswith(":assemble")
    | F.data.endswith(":ready")
    | F.data.endswith(":pickup_complete")
))
async def order_status_change(callback: CallbackQuery):
    if not check_allowed(callback.from_user.id, PICKER_ALLOWED_TG_IDS):
        await callback.answer("Доступ запрещён.", show_alert=True)
        return

    parts = callback.data.split(":")
    try:
        order_id = int(parts[1])
        action = parts[2]
    except (IndexError, ValueError):
        await callback.answer("Неверные данные.", show_alert=True)
        return

    transition = _TRANSITIONS.get(action)
    if not transition:
        await callback.answer("Неизвестное действие.", show_alert=True)
        return

    expected_status, new_status = transition

    if is_in_flight(order_id):
        await callback.answer("Статус уже обновляется, подождите...", show_alert=False)
        return

    # Verify current order status
    order = await _fetch_order_with_items(order_id)
    if not order:
        await callback.answer("Заказ не найден.", show_alert=True)
        return

    if order.status != expected_status:
        await callback.answer(
            f'Заказ уже в статусе "{_STATUS_DISPLAY.get(order.status, order.status)}".',
            show_alert=True,
        )
        return

    # Pickup complete: only for pickup orders
    if action == "pickup_complete" and order.fulfillment_type != "pickup":
        await callback.answer("Этот заказ на доставку, не самовывоз.", show_alert=True)
        return

    # Immediate response
    pending_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="⏳ Обновляю статус...",
            callback_data=f"order:{order_id}:pending",
        )]
    ])
    await callback.message.edit_reply_markup(reply_markup=pending_kb)
    await callback.answer("Обновляю статус...")

    # Launch background retry
    assembler_id = callback.from_user.id if action == "accept" else None
    update_fn = partial(_update_order_status, assembler_id=assembler_id)
    schedule_retry(
        bot=callback.bot,
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
        order_id=order_id,
        new_status=new_status,
        update_fn=update_fn,
        on_success=_on_retry_success,
        on_failure=_on_retry_failure,
    )
