from pathlib import Path

import qrcode


BASE_DIR = Path(__file__).resolve().parent
QR_CODES_DIR = BASE_DIR / "qr_codes"
QR_CODES_DIR.mkdir(parents=True, exist_ok=True)


def generate_qr_code(telegram_id: int) -> str:
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(str(telegram_id))
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    filename = f"qr_{telegram_id}.png"
    filepath = QR_CODES_DIR / filename
    img.save(filepath)

    return str(filepath)


def resolve_qr_code_path(path: str) -> Path:
    """Возвращает абсолютный путь к QR-коду."""
    file_path = Path(path)
    if file_path.is_absolute():
        return file_path

    resolved = (BASE_DIR / file_path).resolve()
    if resolved.exists():
        return resolved

    return (QR_CODES_DIR / file_path.name).resolve()
