import logging
from datetime import datetime, timezone

import config
from shared.clients.backend_client import BackendClient
from shared.clients.onec_client import post_to_onec

backend = BackendClient(config.BACKEND_URL, config.ONEC_API_KEY or "")


async def send_customer_to_onec(user_data, referrer_id=None):
    """
    Отправляет данные клиента в 1С (или в ваш Django-/proxy-эндпоинт).
    Требуются переменные окружения:
      - ONEC_CUSTOMER_URL
      - INTEGRATION_API_KEY

    Args:
        user_data: dict from API response (keys: id, telegram_id, qr_code, registration_date, ...)
        referrer_id: optional referrer telegram_id
    """
    if not config.ONEC_CUSTOMER_URL or not config.ONEC_API_KEY:
        logging.info(
            "Skipping 1C customer sync: ONEC_CUSTOMER_URL/ONEC_API_KEY not configured"
        )
        return

    # Parse registration_date from ISO string
    reg_dt_str = user_data.get("registration_date")
    if reg_dt_str:
        reg_dt = datetime.fromisoformat(str(reg_dt_str).replace("Z", "+00:00"))
    else:
        reg_dt = datetime.now(timezone.utc)

    if reg_dt.tzinfo is None:
        reg_dt = reg_dt.replace(tzinfo=timezone.utc)
    else:
        reg_dt = reg_dt.astimezone(timezone.utc)

    payload = {
        "telegram_id": user_data["telegram_id"],
        "qr_code": user_data.get("qr_code"),
        "created_at": reg_dt.isoformat(),
    }
    full_name = user_data.get("full_name")
    if full_name:
        payload["full_name"] = full_name

    birth_date = user_data.get("birth_date")
    if birth_date:
        # birth_date may be a string from API
        if isinstance(birth_date, str):
            payload["birth_date"] = birth_date
        else:
            payload["birth_date"] = birth_date.isoformat()

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

    user_id = user_data["id"]

    if guid:
        await backend.upsert_onec_map(user_id, guid)

    if bonus is not None:
        await backend.patch_user(user_id, {"bonuses": str(bonus)})

    logging.info("1C registration OK for tg=%s", user_data.get("telegram_id"))
