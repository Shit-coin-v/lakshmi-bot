"""
Shared QR code configuration and utilities.

This module contains constants and pure functions for QR code handling
that are shared between backend and bots.
"""
from __future__ import annotations

from typing import Optional

# QR code file naming conventions
QR_FILENAME_PREFIX = "user_"
QR_LEGACY_PREFIX = "qr_"
QR_EXTENSION = ".png"


def qr_code_filename(telegram_id: int) -> str:
    """Generate standard QR code filename for a telegram user."""
    return f"{QR_FILENAME_PREFIX}{int(telegram_id)}{QR_EXTENSION}"


def legacy_qr_code_filename(telegram_id: int) -> str:
    """Generate legacy QR code filename for a telegram user."""
    return f"{QR_LEGACY_PREFIX}{int(telegram_id)}{QR_EXTENSION}"


def qr_code_media_url(filename: str) -> str:
    """Generate media URL for a QR code file."""
    return f"/media/qr_codes/{filename}"


def extract_telegram_id_from_filename(filename: str) -> Optional[int]:
    """
    Extract telegram ID from a QR code filename.

    Supports both new format (user_<id>.png) and legacy format (qr_<id>.png).
    Returns None if the filename doesn't match expected patterns.
    """
    stem = filename
    if stem.endswith(QR_EXTENSION):
        stem = stem[: -len(QR_EXTENSION)]

    if stem.startswith(QR_FILENAME_PREFIX):
        candidate = stem[len(QR_FILENAME_PREFIX):]
    elif stem.startswith(QR_LEGACY_PREFIX):
        candidate = stem[len(QR_LEGACY_PREFIX):]
    else:
        return None

    if candidate.isdigit():
        try:
            return int(candidate)
        except ValueError:
            return None
    return None


__all__ = [
    "QR_FILENAME_PREFIX",
    "QR_LEGACY_PREFIX",
    "QR_EXTENSION",
    "qr_code_filename",
    "legacy_qr_code_filename",
    "qr_code_media_url",
    "extract_telegram_id_from_filename",
]
