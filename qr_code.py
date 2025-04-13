import qrcode
import os

QR_CODES_DIR = "qr_codes"
os.makedirs(QR_CODES_DIR, exist_ok=True)


def generate_qr_code(telegram_id: int) -> str:
    data = f"https://t.me/retail33412_bot?start={telegram_id}"
    img = qrcode.make(data)
    path = f"{QR_CODES_DIR}/{telegram_id}.png"
    img.save(path)
    return path
