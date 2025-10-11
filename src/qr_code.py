from pathlib import Path
from datetime import datetime
from typing import Optional
import hashlib

try:
    import qrcode
except Exception as e:
    raise RuntimeError("qrcode package is required: pip install qrcode[pil]") from e

MEDIA_ROOT = (Path(__file__).resolve().parents[1] / "backend" / "media").resolve()
QR_DIR = MEDIA_ROOT / "qr_codes"
QR_DIR.mkdir(parents=True, exist_ok=True)

def generate_qr_code(data: str, filename: Optional[str] = None) -> str:
    data_str = str(data)
    if not filename:
        digest = hashlib.sha1(data_str.encode("utf-8")).hexdigest()[:10]
        ts = int(datetime.utcnow().timestamp())
        filename = f"qr_{digest}_{ts}.png"
    filepath = (QR_DIR / filename).resolve()
    if MEDIA_ROOT not in filepath.parents and filepath != MEDIA_ROOT:
        raise ValueError("Invalid filename/path for QR code")
    img = qrcode.make(data_str)
    img.save(filepath)
    return f"/media/qr_codes/{filename}"

def resolve_qr_code_path(relative_url: str) -> Path:
    """
    Принимает:
      - 'qr_codes/<file>'
      - '/media/qr_codes/<file>'
      - '/app/media/qr_codes/<file>' (абсолютный путь из контейнера)
    Возвращает абсолютный путь внутри MEDIA_ROOT.
    """
    s = str(relative_url).strip()

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

    # 'media/qr_codes/...' -> <MEDIA_ROOT>/qr_codes/...
    filepath = (MEDIA_ROOT / s[len("media/"):]).resolve()
    if MEDIA_ROOT not in filepath.parents and filepath != MEDIA_ROOT:
        raise ValueError("Resolved path escapes MEDIA_ROOT")
    return filepath
