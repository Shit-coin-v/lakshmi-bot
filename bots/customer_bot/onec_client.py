import logging
from datetime import timezone

import config
from database.models import upsert_onec_client_map
from shared.clients.onec_client import post_to_onec


async def send_customer_to_onec(session, user, referrer_id=None):
    """
    Отправляет данные клиента в 1С (или в ваш Django-/proxy-эндпоинт).
    Требуются переменные окружения:
      - ONEC_CUSTOMER_URL
      - INTEGRATION_API_KEY
    Заголовки: X-Api-Key, X-Idempotency-Key
    """
    if not config.ONEC_CUSTOMER_URL or not config.ONEC_API_KEY:
        logging.info(
            "Skipping 1C customer sync: ONEC_CUSTOMER_URL/ONEC_API_KEY not configured"
        )
        return

    # Готовим payload (created_at в UTC ISO-8601)
    reg_dt = user.registration_date
    if getattr(reg_dt, "tzinfo", None) is None:
        reg_dt = reg_dt.replace(tzinfo=timezone.utc)
    else:
        reg_dt = reg_dt.astimezone(timezone.utc)

    payload = {
        "telegram_id": user.telegram_id,
        "qr_code": user.qr_code,
        "created_at": reg_dt.isoformat(),
    }
    if getattr(user, "full_name", None):
        payload["full_name"] = user.full_name
    if getattr(user, "birth_date", None):
        payload["birth_date"] = user.birth_date.isoformat()

    if referrer_id is not None:
        payload["referrer_telegram_id"] = referrer_id

    data = await post_to_onec(
        url=config.ONEC_CUSTOMER_URL,
        api_key=config.ONEC_API_KEY,
        payload=payload,
    )
    if data is None:
        return

    # Ответ может быть как {"one_c_guid": "...", "bonus_balance": ...}
    # так и {"status":"ok","customer":{...}} — поддержим оба.
    customer_block = data.get("customer") or {}
    guid = data.get("one_c_guid") or customer_block.get("one_c_guid")
    bonus = data.get("bonus_balance")
    if bonus is None:
        bonus = customer_block.get("bonus_balance")

    if guid:
        await upsert_onec_client_map(session, user.id, guid)

    if bonus is not None:
        try:
            user.bonuses = bonus
            session.add(user)
            await session.commit()
            refresh = getattr(session, "refresh", None)
            if callable(refresh):
                await refresh(user)
        except Exception as e:
            logging.warning("Failed to update bonuses locally: %s", e)
            rollback = getattr(session, "rollback", None)
            if callable(rollback):
                try:
                    await rollback()
                except Exception:
                    logging.exception("Failed to rollback bonuses update")

    logging.info("1C registration OK for tg=%s", user.telegram_id)
