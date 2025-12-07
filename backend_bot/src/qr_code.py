from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

try:
    import qrcode
except Exception as e:
    raise RuntimeError("qrcode package is required: pip install qrcode[pil]") from e

MEDIA_ROOT = (Path(__file__).resolve().parents[1] / "backend" / "media").resolve()
QR_DIR = MEDIA_ROOT / "qr_codes"
QR_DIR.mkdir(parents=True, exist_ok=True)

QR_FILENAME_PREFIX = "user_"
QR_LEGACY_PREFIX = "qr_"
QR_EXTENSION = ".png"


def qr_code_filename(telegram_id: int) -> str:
    return f"{QR_FILENAME_PREFIX}{int(telegram_id)}{QR_EXTENSION}"


def legacy_qr_code_filename(telegram_id: int) -> str:
    return f"{QR_LEGACY_PREFIX}{int(telegram_id)}{QR_EXTENSION}"


def qr_code_media_url_from_filename(filename: str) -> str:
    return f"/media/qr_codes/{filename}"


def _safe_qr_path(filename: str) -> Path:
    filepath = (QR_DIR / filename).resolve()
    if QR_DIR not in filepath.parents and filepath != QR_DIR:
        raise ValueError("Invalid filename/path for QR code")
    return filepath


def _extract_telegram_id(filename: str) -> Optional[int]:
    stem = filename
    if stem.endswith(QR_EXTENSION):
        stem = stem[: -len(QR_EXTENSION)]
    if stem.startswith(QR_FILENAME_PREFIX):
        candidate = stem[len(QR_FILENAME_PREFIX) :]
    elif stem.startswith(QR_LEGACY_PREFIX):
        candidate = stem[len(QR_LEGACY_PREFIX) :]
    else:
        return None
    if candidate.isdigit():
        try:
            return int(candidate)
        except ValueError:
            return None
    return None


def generate_qr_code(
    data: str,
    filename: Optional[str] = None,
    telegram_id: Optional[int] = None,
) -> str:
    data_str = str(data)
    target_id: Optional[int]
    if telegram_id is not None:
        target_id = int(telegram_id)
    else:
        try:
            target_id = int(data_str)
        except (TypeError, ValueError):
            target_id = None

    if filename is None:
        if target_id is None:
            raise ValueError("telegram_id is required when filename is not provided")
        filename = qr_code_filename(target_id)

    filepath = _safe_qr_path(filename)

    img = qrcode.make(data_str)
    img.save(filepath)
    return qr_code_media_url_from_filename(Path(filename).name)


def resolve_qr_code_path(
    relative_url: str, telegram_id: Optional[int] = None
) -> Tuple[Path, str]:
    """
    Принимает:
      - 'qr_codes/<file>'
      - '/media/qr_codes/<file>'
      - '/app/media/qr_codes/<file>' (абсолютный путь из контейнера)
    Возвращает кортеж (путь в файловой системе, нормализованный URL).
    """
    s = str(relative_url).strip()
    if not s:
        raise ValueError("QR code path is empty")

    # абсол. путь контейнера -> /media/qr_codes/<file>
    if s.startswith("/app/media/"):
        s = "/" + s.split("/app/", 1)[1]  # теперь '/media/...'

    # убрать ведущий слэш
    s = s.lstrip("/")

    # голый 'qr_codes/...' -> 'media/qr_codes/...'
    if s.startswith("qr_codes/"):
        s = "media/" + s

    if not s.startswith("media/qr_codes/"):
        raise ValueError(f"Unexpected QR url: {relative_url}")

    filename = s[len("media/qr_codes/"):]
    original_path = _safe_qr_path(filename)

    candidate_id = telegram_id if telegram_id is not None else _extract_telegram_id(filename)

    if candidate_id is not None:
        expected_filename = qr_code_filename(candidate_id)
        expected_path = _safe_qr_path(expected_filename)
        normalized_url = qr_code_media_url_from_filename(expected_filename)

        if filename == expected_filename and original_path == expected_path:
            return expected_path, normalized_url

        if expected_path.exists():
            return expected_path, normalized_url

        legacy_filename = legacy_qr_code_filename(candidate_id)
        legacy_path = _safe_qr_path(legacy_filename)
        if legacy_path.exists():
            if not expected_path.exists():
                legacy_path.rename(expected_path)
            return expected_path, normalized_url

        if original_path.exists():
            return original_path, normalized_url

        return expected_path, normalized_url

    normalized_url = qr_code_media_url_from_filename(filename)
    return original_path, normalized_url


def get_telegram_id_from_filename(filename: str) -> Optional[int]:
    return _extract_telegram_id(filename)


__all__ = [
    "MEDIA_ROOT",
    "QR_DIR",
    "QR_EXTENSION",
    "QR_FILENAME_PREFIX",
    "QR_LEGACY_PREFIX",
    "get_telegram_id_from_filename",
    "generate_qr_code",
    "legacy_qr_code_filename",
    "qr_code_filename",
    "qr_code_media_url_from_filename",
    "resolve_qr_code_path",
]
