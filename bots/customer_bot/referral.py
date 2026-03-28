"""Pure helpers for referral start-payload parsing."""


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
