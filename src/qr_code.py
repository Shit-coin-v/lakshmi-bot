from pathlib import Path
<<<<<<< Updated upstream

=======
import os
>>>>>>> Stashed changes
import qrcode

MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT", "/app/media")).resolve()
QR_CODES_DIR = Path(os.getenv("QR_CODES_DIR", str(MEDIA_ROOT / "qr_codes"))).resolve()
QR_CODES_DIR.mkdir(parents=True, exist_ok=True)

def qr_file_path(telegram_id: int) -> Path:
    return QR_CODES_DIR / f"qr_{telegram_id}.png"

def generate_qr_code(telegram_id: int) -> str:
<<<<<<< Updated upstream
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
=======
    """Генерирует (или возвращает) путь к PNG в персистентном каталоге."""
    path = qr_file_path(telegram_id)
    if not path.exists():
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(str(telegram_id))
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(path)
    return str(path)
>>>>>>> Stashed changes
