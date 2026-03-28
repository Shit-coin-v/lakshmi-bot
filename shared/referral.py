"""Pure helpers for referral start-payload parsing and 1C integration."""


def parse_start_payload(text: str) -> tuple:
    """Parse /start payload into (referrer_id, referral_code).

    Returns:
        (referrer_id: int | None, referral_code: str | None)

    Examples:
        "/start ref123456789" → (123456789, None)   # legacy telegram_id
        "/start ref_A7K2M9XP" → (None, "A7K2M9XP") # new referral_code
        "/start"              → (None, None)
    """
    referrer_id = None
    referral_code = None
    command_args = text.split()
    if len(command_args) > 1:
        payload = command_args[1]
        if payload.startswith("ref_"):
            referral_code = payload[4:] or None
        elif payload.startswith("ref"):
            try:
                referrer_id = int(payload[3:])
            except ValueError:
                referrer_id = None
    return referrer_id, referral_code


def resolve_referrer_tg_id(state_data: dict, user_response: dict) -> int | None:
    """Determine the referrer's telegram_id to send to 1C.

    In legacy flow, state_data["referrer_id"] is already the telegram_id.
    In code-based flow, state_data has no referrer_id, so we read
    referrer_telegram_id from the API response.

    Args:
        state_data: FSM state dict (keys: referrer_id, referral_code, ...)
        user_response: JSON response from POST /api/bot/users/register/

    Returns:
        referrer's telegram_id (int) or None
    """
    # Legacy: referrer_id in state IS the telegram_id (parsed from /start ref{tg_id})
    tg_id = state_data.get("referrer_id")
    if tg_id:
        return int(tg_id)
    # Code-based: referrer_telegram_id comes from API response
    tg_id = user_response.get("referrer_telegram_id")
    if tg_id:
        return int(tg_id)
    return None
