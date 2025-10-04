from pathlib import Path, PureWindowsPath

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
    raw_path = path.strip()
    file_path = Path(raw_path)

    if file_path.is_absolute() and file_path.exists():
        return file_path

    # Попробуем восстановить относительный путь от каталога исходников
    resolved = (BASE_DIR / file_path).resolve()
    if resolved.exists():
        return resolved

    windows_path = PureWindowsPath(raw_path)
    windows_parts = list(windows_path.parts)

    if "qr_codes" in windows_parts:
        relative_parts = windows_parts[windows_parts.index("qr_codes") + 1 :]
        candidate = QR_CODES_DIR.joinpath(*relative_parts)
        if candidate.exists():
            return candidate

    filename = windows_path.name or file_path.name
    return (QR_CODES_DIR / filename).resolve()
