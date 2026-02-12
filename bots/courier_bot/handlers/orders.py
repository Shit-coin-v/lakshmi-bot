import logging
from datetime import date

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import Date, cast, func, select
from sqlalchemy.orm import selectinload

from bots.customer_bot.database.models import SessionLocal, Order, OrderItem, CourierNotificationMessage
from shared.clients.onec_client import post_to_onec
from config import COURIER_ALLOWED_TG_IDS, BACKEND_URL, INTEGRATION_API_KEY
from chat_cleanup import send_clean
from keyboards import get_orders_list_keyboard, get_order_detail_keyboard, payment_label
from retry import is_in_flight, schedule_retry

logger = logging.getLogger(__name__)

router = Router()

# Statuses visible to couriers
_ACTIVE_STATUSES = ("ready", "delivery", "arrived")

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


def _check_courier(user_id: int) -> bool:
    return user_id in COURIER_ALLOWED_TG_IDS


async def _fetch_active_orders():
    """Fetch orders with active statuses, sorted by created_at."""
    async with SessionLocal() as session:
        result = await session.execute(
            select(Order)
            .where(Order.status.in_(_ACTIVE_STATUSES))
            .order_by(Order.created_at)
        )
        return result.scalars().all()


async def _fetch_completed_today():
    """Fetch count and total sum of completed orders for today."""
    today = date.today()
    async with SessionLocal() as session:
        result = await session.execute(
            select(
                func.count(Order.id),
                func.coalesce(func.sum(Order.total_price), 0),
            ).where(
                Order.status == "completed",
                cast(Order.updated_at, Date) == today,
            )
        )
        row = result.one()
        return row[0], float(row[1])


async def _fetch_order_with_items(order_id: int):
    """Fetch a single order with items and products eagerly loaded."""
    async with SessionLocal() as session:
        result = await session.execute(
            select(Order)
            .where(Order.id == order_id)
            .options(selectinload(Order.items).selectinload(OrderItem.product))
        )
        return result.scalar_one_or_none()


def _format_order_detail(order) -> str:
    """Format order details for the courier message."""
    lines = [
        f"<b>Заказ #{order.id}</b>",
        "\U0001f4cd село Намцы",
        f"\U0001f3e0 Адрес: {order.address}",
        f"\U0001f4de Телефон: {order.phone}",
    ]

    if order.comment:
        lines.append(f"\U0001f4ac Комментарий: {order.comment}")

    lines.append("")
    lines.append("<b>Состав:</b>")
    for item in order.items:
        name = item.product.name if item.product else f"Товар #{item.product_id}"
        price = int(item.price_at_moment) if item.price_at_moment == int(item.price_at_moment) else item.price_at_moment
        lines.append(f"  \u2022 {name} x{item.quantity} \u2014 {price}\u20bd")

    total = int(order.total_price) if order.total_price == int(order.total_price) else order.total_price
    lines.append("")
    lines.append(f"<b>Итого:</b> {total}\u20bd")
    lines.append(f"<b>Оплата:</b> {payment_label(order.payment_method)}")

    status_text = _STATUS_DISPLAY.get(order.status, order.status)
    lines.append(f"<b>Статус:</b> {status_text}")

    return "\n".join(lines)


async def _update_order_status(order_id: int, new_status: str) -> bool:
    """POST status change to backend via onec endpoint. Returns True on success."""
    url = f"{BACKEND_URL}/onec/order/status"
    payload = {"order_id": order_id, "status": new_status}
    result = await post_to_onec(url, INTEGRATION_API_KEY, payload)
    if result and result.get("status") == "ok":
        return True
    logger.error("Failed to update order %s to %s: %s", order_id, new_status, result)
    return False


# --- Cleanup: delete Celery-sent notification messages ---

async def _cleanup_notifications(bot: Bot, chat_id: int, user_id: int):
    """Delete tracked courier notification messages sent by Celery."""
    async with SessionLocal() as session:
        result = await session.execute(
            select(CourierNotificationMessage)
            .where(CourierNotificationMessage.courier_tg_id == user_id)
        )
        notifications = result.scalars().all()
        for n in notifications:
            try:
                await bot.delete_message(chat_id, n.telegram_message_id)
            except Exception:
                pass  # Already deleted or too old
            await session.delete(n)
        if notifications:
            await session.commit()


# --- Command: /orders ---

@router.message(Command("orders"))
async def cmd_orders(message: Message):
    if not _check_courier(message.from_user.id):
        await send_clean(message, "Доступ запрещён.")
        return
    await _cleanup_notifications(message.bot, message.chat.id, message.from_user.id)
    orders = await _fetch_active_orders()
    keyboard = get_orders_list_keyboard(orders)
    await send_clean(message, "\U0001f4e6 Активные заказы:", reply_markup=keyboard)


# --- Command: /completed ---

@router.message(Command("completed"))
async def cmd_completed(message: Message):
    if not _check_courier(message.from_user.id):
        await send_clean(message, "Доступ запрещён.")
        return

    count, total = await _fetch_completed_today()

    if count == 0:
        await send_clean(message, "📋 Сегодня выполненных заказов пока нет.")
        return

    text = (
        f"📋 Выполненные заказы за сегодня:\n\n"
        f"📦 Количество: {count}\n"
        f"💰 Сумма: {int(total)} ₽"
    )
    await send_clean(message, text)


# --- Callback: back to orders list ---

@router.callback_query(F.data == "orders:back")
async def orders_back(callback: CallbackQuery):
    if not _check_courier(callback.from_user.id):
        await callback.answer("Доступ запрещён.", show_alert=True)
        return

    orders = await _fetch_active_orders()
    keyboard = get_orders_list_keyboard(orders)
    await callback.message.edit_text("\U0001f4e6 Активные заказы:", reply_markup=keyboard)
    await callback.answer()


# --- Callback: noop for empty list ---

@router.callback_query(F.data == "noop")
async def noop_callback(callback: CallbackQuery):
    await callback.answer()


# --- Callback: pending button noop ---

@router.callback_query(F.data.startswith("order:") & F.data.endswith(":pending"))
async def order_pending_noop(callback: CallbackQuery):
    await callback.answer("Статус обновляется, подождите...", show_alert=False)


# --- Callback: show customer phone ---

@router.callback_query(F.data.startswith("order:") & F.data.endswith(":phone"))
async def order_phone(callback: CallbackQuery):
    if not _check_courier(callback.from_user.id):
        await callback.answer("Доступ запрещён.", show_alert=True)
        return

    parts = callback.data.split(":")
    try:
        order_id = int(parts[1])
    except (IndexError, ValueError):
        await callback.answer("Неверные данные.", show_alert=True)
        return

    order = await _fetch_order_with_items(order_id)
    if not order or not order.phone:
        await callback.answer("Телефон не найден.", show_alert=True)
        return

    await callback.answer(f"\U0001f4de {order.phone}", show_alert=True)


# --- Callback: order detail ---

@router.callback_query(F.data.startswith("order:") & F.data.endswith(":detail"))
async def order_detail(callback: CallbackQuery):
    if not _check_courier(callback.from_user.id):
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
            orders = await _fetch_active_orders()
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


# --- Callback: status transitions (pickup, arrived, complete) ---

@router.callback_query(F.data.startswith("order:") & (
    F.data.endswith(":pickup") | F.data.endswith(":arrived") | F.data.endswith(":complete")
))
async def order_status_change(callback: CallbackQuery):
    if not _check_courier(callback.from_user.id):
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
    await callback.message.edit_reply_markup(reply_markup=pending_kb)
    await callback.answer("Обновляю статус...")

    # Launch background retry task
    schedule_retry(
        bot=callback.bot,
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
        order_id=order_id,
        new_status=new_status,
        update_fn=_update_order_status,
        on_success=_on_retry_success,
        on_failure=_on_retry_failure,
    )
