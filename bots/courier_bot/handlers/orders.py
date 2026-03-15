import logging
import os
from functools import partial
from html import escape
from types import SimpleNamespace

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramNetworkError
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from shared.bot_utils.access import check_staff_access
from shared.bot_utils.chat_cleanup import send_clean
from shared.bot_utils.notifications import cleanup_notifications
from shared.bot_utils.order_helpers import fetch_order_with_items
from shared.bot_utils.retry import is_in_flight, schedule_retry
from config import backend, STORE_LOCATION
from keyboards import (
    get_orders_list_keyboard,
    get_order_detail_keyboard,
    get_cancel_reasons_keyboard,
    payment_label,
)

logger = logging.getLogger(__name__)

router = Router()


async def _check_access(telegram_id: int) -> bool:
    return await check_staff_access(backend, telegram_id, "courier")


# Statuses visible to couriers
_ACTIVE_STATUSES = ("ready", "delivery", "arrived")
DELIVERY_RATE = int(os.environ.get("COURIER_DELIVERY_RATE", "150"))

_STATUS_DISPLAY = {
    "ready": "Заказ собран, ждёт курьера",
    "delivery": "Курьер забрал заказ и в пути",
    "arrived": "Курьер пришёл и ждёт вас",
}

# Transition map: action -> (expected_current_status, new_status)
_TRANSITIONS = {
    "pickup": ("ready", "delivery"),
    "arrived": ("delivery", "arrived"),
    "complete": ("arrived", "completed"),
}


async def _fetch_active_orders(courier_tg_id: int):
    """Fetch orders assigned to this courier."""
    orders = await backend.get_active_orders(courier_tg_id)
    result = []
    for o in orders:
        if "total_price" in o and o["total_price"] is not None:
            o["total_price"] = float(o["total_price"])
        result.append(SimpleNamespace(**o))
    return result


async def _fetch_completed_today(courier_tg_id: int):
    """Fetch count of completed orders for today by this courier."""
    result = await backend.get_completed_today(courier_tg_id)
    if result is None:
        return 0
    return result.get("count", 0)


async def _fetch_order_with_items(order_id: int):
    return await fetch_order_with_items(backend, order_id)


def _format_order_detail(order) -> str:
    """Format order details for the courier message."""
    lines = [
        f"<b>Заказ #{order.id}</b>",
        f"\U0001f4cd {STORE_LOCATION}",
        f"\U0001f3e0 Адрес: {escape(str(order.address or ''))}",
        f"\U0001f4de Телефон: {escape(str(order.phone or ''))}",
    ]

    if order.comment:
        lines.append(f"\U0001f4ac Комментарий: {escape(str(order.comment))}")

    lines.append("")
    lines.append("<b>Состав:</b>")
    for item in order.items:
        name = escape(item.product.name) if item.product else f"Товар #{item.product_id}"
        price = int(item.price_at_moment) if item.price_at_moment == int(item.price_at_moment) else item.price_at_moment
        lines.append(f"  \u2022 {name} x{item.quantity} \u2014 {price}\u20bd")

    total = int(order.total_price) if order.total_price == int(order.total_price) else order.total_price
    lines.append("")
    lines.append(f"<b>Итого:</b> {total}\u20bd")
    lines.append(f"<b>Оплата:</b> {payment_label(order.payment_method)}")

    status_text = _STATUS_DISPLAY.get(order.status, order.status)
    lines.append(f"<b>Статус:</b> {status_text}")

    return "\n".join(lines)


async def _update_order_status(
    order_id: int, new_status: str, courier_id: int | None = None,
) -> tuple[bool, bool]:
    """POST status change to backend. Returns (success, is_retryable)."""
    return await backend.update_order_status(
        order_id, new_status, courier_id=courier_id,
    )


# --- Cleanup: delete Celery-sent notification messages ---

async def _cleanup_notifications(bot: Bot, chat_id: int, user_id: int):
    await cleanup_notifications(backend, bot, chat_id, user_id, "courier")


# --- Command: /orders ---

@router.message(Command("orders"))
async def cmd_orders(message: Message):
    if not await _check_access(message.from_user.id):
        await send_clean(message, "Доступ запрещён.")
        return
    await _cleanup_notifications(message.bot, message.chat.id, message.from_user.id)
    orders = await _fetch_active_orders(message.from_user.id)
    keyboard = get_orders_list_keyboard(orders)
    await send_clean(message, "📦 Мои заказы:", reply_markup=keyboard)


# --- Command: /completed ---

@router.message(Command("completed"))
async def cmd_completed(message: Message):
    if not await _check_access(message.from_user.id):
        await send_clean(message, "Доступ запрещён.")
        return

    count = await _fetch_completed_today(message.from_user.id)

    if count == 0:
        await send_clean(message, "📋 Сегодня доставленных заказов пока нет.")
        return

    total = count * DELIVERY_RATE
    text = (
        f"📋 Отчёт за сегодня:\n\n"
        f"📦 Количество: {count}\n"
        f"💰 Сумма: {total} ₽"
    )
    await send_clean(message, text)


# --- Callback: back to orders list ---

@router.callback_query(F.data == "orders:back")
async def orders_back(callback: CallbackQuery):
    if not await _check_access(callback.from_user.id):
        await callback.answer("Доступ запрещён.", show_alert=True)
        return

    orders = await _fetch_active_orders(callback.from_user.id)
    keyboard = get_orders_list_keyboard(orders)
    await callback.message.edit_text("📦 Мои заказы:", reply_markup=keyboard)
    await callback.answer()


# --- Callback: noop for empty list ---

@router.callback_query(F.data == "noop")
async def noop_callback(callback: CallbackQuery):
    await callback.answer()


# --- Callback: pending button noop ---

@router.callback_query(F.data.startswith("order:") & F.data.endswith(":pending"))
async def order_pending_noop(callback: CallbackQuery):
    await callback.answer("Статус обновляется, подождите...", show_alert=False)


# --- Callback: order detail ---

@router.callback_query(F.data.startswith("order:") & F.data.endswith(":detail"))
async def order_detail(callback: CallbackQuery):
    if not await _check_access(callback.from_user.id):
        await callback.answer("Доступ запрещён.", show_alert=True)
        return

    parts = callback.data.split(":")
    try:
        order_id = int(parts[1])
    except (IndexError, ValueError):
        await callback.answer("Неверный заказ.", show_alert=True)
        return

    order = await _fetch_order_with_items(order_id)
    if not order or order.status not in _ACTIVE_STATUSES:
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
            # Get courier tg_id from the completed order to fetch remaining orders
            completed_order = await _fetch_order_with_items(order_id)
            courier_tg_id = getattr(completed_order, "delivered_by", None) if completed_order else None
            orders = await _fetch_active_orders(courier_tg_id) if courier_tg_id else []
            if orders:
                keyboard = get_orders_list_keyboard(orders)
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=f"✅ Заказ #{order_id} доставлен!\n\n📦 Активные заказы:",
                    reply_markup=keyboard,
                )
            else:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=f"✅ Заказ #{order_id} доставлен!\n\nВсе заказы выполнены 🎉",
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


# --- Callback: reassign order to another courier ---

@router.callback_query(F.data.startswith("order:") & F.data.endswith(":reassign"))
async def order_reassign(callback: CallbackQuery):
    if not await _check_access(callback.from_user.id):
        await callback.answer("Доступ запрещён.", show_alert=True)
        return

    parts = callback.data.split(":")
    try:
        order_id = int(parts[1])
    except (IndexError, ValueError):
        await callback.answer("Неверные данные.", show_alert=True)
        return

    order = await _fetch_order_with_items(order_id)
    if not order:
        await callback.answer("Заказ не найден.", show_alert=True)
        return

    if order.status != "ready":
        await callback.answer("Передать можно только заказ в статусе «Собран».", show_alert=True)
        return

    success = await backend.reassign_order(order_id)
    if success:
        orders = await _fetch_active_orders(callback.from_user.id)
        if orders:
            keyboard = get_orders_list_keyboard(orders)
            await callback.message.edit_text(
                f"🔁 Заказ #{order_id} передан другому курьеру.\n\n📦 Активные заказы:",
                reply_markup=keyboard,
            )
        else:
            await callback.message.edit_text(
                f"🔁 Заказ #{order_id} передан другому курьеру.\n\nВсе заказы выполнены 🎉",
            )
        await callback.answer()
    else:
        await callback.answer("Не удалось передать заказ. Попробуйте позже.", show_alert=True)


# --- Callback: cancel order ---

@router.callback_query(F.data.startswith("order:") & F.data.endswith(":cancel"))
async def order_cancel(callback: CallbackQuery):
    if not await _check_access(callback.from_user.id):
        await callback.answer("Доступ запрещён.", show_alert=True)
        return

    parts = callback.data.split(":")
    try:
        order_id = int(parts[1])
    except (IndexError, ValueError):
        await callback.answer("Неверные данные.", show_alert=True)
        return

    keyboard = get_cancel_reasons_keyboard(order_id)
    await callback.message.edit_text(
        f"Заказ #{order_id}\n\nУкажите причину отмены:",
        reply_markup=keyboard,
    )
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("order:") and ":cancelreason:" in c.data)
async def order_cancel_reason(callback: CallbackQuery):
    """Step 2: cancel the order with the selected reason."""
    if not await _check_access(callback.from_user.id):
        await callback.answer("Доступ запрещён.", show_alert=True)
        return

    parts = callback.data.split(":")
    try:
        order_id = int(parts[1])
        reason = parts[3]
    except (IndexError, ValueError):
        await callback.answer("Неверные данные.", show_alert=True)
        return

    # Show "processing" state
    pending_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="⏳ Отменяю заказ...",
            callback_data=f"order:{order_id}:pending",
        )]
    ])
    try:
        await callback.message.edit_reply_markup(reply_markup=pending_kb)
    except (TelegramBadRequest, TelegramNetworkError):
        pass  # UI update is non-critical
    try:
        await callback.answer("Отменяю заказ...")
    except (TelegramBadRequest, TelegramNetworkError):
        pass

    success = await backend.cancel_order(
        order_id,
        reason=reason,
        role="courier",
        courier_tg_id=callback.from_user.id,
    )

    if success:
        orders = await _fetch_active_orders(callback.from_user.id)
        if orders:
            keyboard = get_orders_list_keyboard(orders)
            await callback.message.edit_text(
                f"❌ Заказ #{order_id} отменён.\n\n📦 Активные заказы:",
                reply_markup=keyboard,
            )
        else:
            await callback.message.edit_text(
                f"❌ Заказ #{order_id} отменён.\n\nНет активных заказов.",
            )
    else:
        order = await _fetch_order_with_items(order_id)
        if order and order.status in _ACTIVE_STATUSES:
            text = _format_order_detail(order)
            text += "\n\n❌ <b>Не удалось отменить заказ. Попробуйте снова.</b>"
            keyboard = get_order_detail_keyboard(order)
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        else:
            await callback.message.edit_text(
                f"❌ Не удалось отменить заказ #{order_id}.",
            )


# --- Callback: status transitions (pickup, arrived, complete) ---

@router.callback_query(F.data.startswith("order:") & (
    F.data.endswith(":pickup") | F.data.endswith(":arrived") | F.data.endswith(":complete")
))
async def order_status_change(callback: CallbackQuery):
    if not await _check_access(callback.from_user.id):
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

    # Guard: reject if retry already in flight for this order
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

    # Immediate response: replace buttons with "Updating..."
    pending_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="⏳ Обновляю статус...",
            callback_data=f"order:{order_id}:pending",
        )]
    ])
    try:
        await callback.message.edit_reply_markup(reply_markup=pending_kb)
    except (TelegramBadRequest, TelegramNetworkError):
        pass  # UI update is non-critical, proceed to schedule_retry
    try:
        await callback.answer("Обновляю статус...")
    except (TelegramBadRequest, TelegramNetworkError):
        pass

    # Launch background retry task
    update_fn = partial(_update_order_status, courier_id=callback.from_user.id)
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
