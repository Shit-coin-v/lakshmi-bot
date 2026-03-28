"""Re-export from shared.referral for bot convenience."""
from shared.referral import parse_start_payload, resolve_referrer_tg_id  # noqa: F401

__all__ = ["parse_start_payload", "resolve_referrer_tg_id"]
