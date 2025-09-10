import aiohttp
import hmac
import hashlib
import json
import logging
import uuid
import time
from datetime import timezone

import config
from database.models import upsert_onec_client_map


async def send_customer_to_onec(session, user, referrer_id=None):
    """
    Отправляет данные клиента в 1С (или в ваш Django-/proxy-эндпоинт).
    Требуются переменные окружения:
      - ONEC_CUSTOMER_URL
      - INTEGRATION_API_KEY
      - INTEGRATION_HMAC_SECRET

    Подпись: HMAC-SHA256(secret, f"{ts}.{raw_body}")
    Заголовки: X-Api-Key, X-Timestamp, X-Sign, X-Idempotency-Key
    """
    if not config.ONEC_CUSTOMER_URL or not config.ONEC_API_KEY or not config.ONEC_API_SECRET:
        logging.error("1C integration is not configured")
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
        # Если стучитесь в Django /onec/customer — он ждёт ключ 'created_at'
        "created_at": reg_dt.isoformat(),
    }
    # Доп. опциональные поля — не обязательны для сервера, но могут пригодиться
    if getattr(user, "full_name", None):
        payload["full_name"] = user.full_name
    if getattr(user, "birth_date", None):
        payload["birth_date"] = user.birth_date.isoformat()

    if referrer_id is not None:
        payload["referrer_telegram_id"] = referrer_id

    body = json.dumps(payload, ensure_ascii=False)

    ts = str(int(time.time()))
    sign = hmac.new(
        config.ONEC_API_SECRET.encode(),
        f"{ts}.{body}".encode(),
        hashlib.sha256,
    ).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "X-Api-Key": config.ONEC_API_KEY,
        "X-Timestamp": ts,
        "X-Sign": sign,
        "X-Idempotency-Key": str(uuid.uuid4()),
    }

    try:
        async with aiohttp.ClientSession() as client:
            async with client.post(config.ONEC_CUSTOMER_URL, data=body, headers=headers) as resp:
                text = await resp.text()
                if resp.status == 200:
                    # Ответ может быть как {"one_c_guid": "...", "bonus_balance": ...}
                    # так и {"status":"ok","customer":{...}} — поддержим оба.
                    try:
                        data = json.loads(text)
                    except Exception:
                        logging.error("1C registration: invalid JSON response: %s", text)
                        return

                    customer_block = data.get("customer") or {}
                    guid = data.get("one_c_guid") or customer_block.get("one_c_guid")
                    bonus = data.get("bonus_balance")
                    if bonus is None:
                        bonus = customer_block.get("bonus_balance")

                    if guid:
                        # Сохраняем соответствие user.id <-> GUID в маппинге
                        await upsert_onec_client_map(session, user.id, guid)

                    if bonus is not None:
                        # Обновим баланс в нашей БД
                        try:
                            user.bonuses = bonus
                            session.add(user)
                        except Exception as e:
                            logging.warning("Failed to update bonuses locally: %s", e)

                    logging.info("1C registration OK for tg=%s", user.telegram_id)
                else:
                    logging.error("1C registration failed: %s", text)
    except Exception:
        logging.exception("Failed to send customer data to 1C")

