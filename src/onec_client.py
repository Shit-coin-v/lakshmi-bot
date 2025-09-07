import aiohttp
import hmac
import hashlib
import json
import logging
import uuid
from datetime import timezone

import config
from database.models import upsert_onec_client_map

async def send_customer_to_onec(session, user, referrer_id=None):
    if not config.ONEC_CUSTOMER_URL or not config.ONEC_API_KEY or not config.ONEC_API_SECRET:
        logging.error("1C integration is not configured")
        return

    payload = {
        "telegram_id": user.telegram_id,
        "qr_code": user.qr_code,
        "registration_date": user.registration_date.replace(tzinfo=timezone.utc).isoformat(),
    }
    if referrer_id is not None:
        payload["referrer_telegram_id"] = referrer_id

    body = json.dumps(payload, ensure_ascii=False)
    headers = {
        "Content-Type": "application/json",
        "X-Api-Key": config.ONEC_API_KEY,
        "Idempotency-Key": str(uuid.uuid4()),
    }
    sign = hmac.new(config.ONEC_API_SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()
    headers["X-Sign"] = sign

    try:
        async with aiohttp.ClientSession() as client:
            async with client.post(config.ONEC_CUSTOMER_URL, data=body, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    guid = data.get("one_c_guid")
                    if guid:
                        user.bonuses = data.get("bonus_balance", user.bonuses)
                        session.add(user)
                        await upsert_onec_client_map(session, user.id, guid)
                else:
                    logging.error("1C registration failed: %s", await resp.text())
    except Exception:
        logging.exception("Failed to send customer data to 1C")
