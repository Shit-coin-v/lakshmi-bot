import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

import qr_code


@pytest.fixture()
def tmp_media(monkeypatch, tmp_path):
    media_root = tmp_path / "media"
    qr_dir = media_root / "qr_codes"
    qr_dir.mkdir(parents=True)
    monkeypatch.setattr(qr_code, "MEDIA_ROOT", media_root, raising=False)
    monkeypatch.setattr(qr_code, "QR_DIR", qr_dir, raising=False)
    return qr_dir


def test_qr_code_filename_and_url():
    assert qr_code.qr_code_filename(42) == "user_42.png"
    assert qr_code.qr_code_media_url_from_filename("user_42.png") == "/media/qr_codes/user_42.png"
    assert qr_code.get_telegram_id_from_filename("qr_42.png") == 42
    assert qr_code.get_telegram_id_from_filename("user_42.png") == 42


def test_generate_qr_code_creates_file(tmp_media):
    url = qr_code.generate_qr_code("payload", telegram_id=7)
    path, normalized = qr_code.resolve_qr_code_path(url, telegram_id=7)
    assert normalized == "/media/qr_codes/user_7.png"
    assert path.exists()
    assert path.read_bytes()  # file is not empty


def test_resolve_legacy_filename(tmp_media):
    legacy_path = qr_code.QR_DIR / "qr_55.png"
    legacy_path.write_bytes(b"legacy")

    path, normalized = qr_code.resolve_qr_code_path("/media/qr_codes/qr_55.png")

    assert normalized == "/media/qr_codes/user_55.png"
    assert path.name == "user_55.png"
    assert path.exists()
    assert path.read_bytes() == b"legacy"
    assert not legacy_path.exists()
