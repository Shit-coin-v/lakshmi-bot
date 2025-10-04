import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import qr_code


@pytest.fixture(autouse=True)
def reset_qr_paths(tmp_path, monkeypatch):
    base_dir = tmp_path / "src"
    codes_dir = base_dir / "qr_codes"
    codes_dir.mkdir(parents=True)
    monkeypatch.setattr(qr_code, "BASE_DIR", base_dir)
    monkeypatch.setattr(qr_code, "QR_CODES_DIR", codes_dir)
    yield


def test_resolve_relative_path(tmp_path):
    expected = qr_code.QR_CODES_DIR / "qr_1.png"
    expected.touch()

    resolved = qr_code.resolve_qr_code_path("qr_codes/qr_1.png")

    assert resolved == expected


def test_resolve_windows_absolute_path(tmp_path):
    expected = qr_code.QR_CODES_DIR / "qr_2.png"
    expected.touch()

    raw_path = r"C:\\bots\\project\\src\\qr_codes\\qr_2.png"

    resolved = qr_code.resolve_qr_code_path(raw_path)

    assert resolved == expected


def test_resolve_windows_relative_path(tmp_path):
    expected = qr_code.QR_CODES_DIR / "qr_3.png"
    expected.touch()

    raw_path = r"qr_codes\\qr_3.png"

    resolved = qr_code.resolve_qr_code_path(raw_path)

    assert resolved == expected


def test_returns_target_location_when_file_missing(tmp_path):
    resolved = qr_code.resolve_qr_code_path("qr_codes/qr_unknown.png")

    assert resolved == qr_code.QR_CODES_DIR / "qr_unknown.png"
