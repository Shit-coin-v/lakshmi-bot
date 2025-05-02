import qrcode
import os

QR_CODES_DIR = "qr_codes"
os.makedirs(QR_CODES_DIR, exist_ok=True)


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
    filepath = os.path.join(QR_CODES_DIR, filename)
    img.save(filepath)

    return filepath
