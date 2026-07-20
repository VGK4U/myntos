"""
Task #54 — Earner card KYC photo wiring regression test.

Verifies that _get_kyc_photo_bytes:
  1. Returns VGK profile_photo bytes when available (priority 1)
  2. Falls back to kyc_document passport_photo when VGK photo is absent (priority 2)
  3. Returns None when neither source yields bytes (→ gold initials fallback)
  4. compose_earner_card() renders without error when photo_bytes=None
  5. compose_earner_card() renders without error when photo_bytes is a valid JPEG

Run: python3.11 backend/tests/test_earner_card_kyc_photo.py
Exit code 0 on success, 1 on any failure.
"""

from __future__ import annotations

import io
import sys
import types
import unittest.mock as mock
from pathlib import Path

PASSED: list[str] = []
FAILED: list[tuple[str, str]] = []


def _ok(name: str) -> None:
    print(f"  ✓ {name}")
    PASSED.append(name)


def _fail(name: str, msg: str) -> None:
    print(f"  ✗ {name}: {msg}")
    FAILED.append((name, msg))


def banner(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


def _make_fake_jpeg(w: int = 10, h: int = 10) -> bytes:
    """Return a minimal valid JPEG in bytes."""
    try:
        from PIL import Image
        buf = io.BytesIO()
        Image.new('RGB', (w, h), color=(180, 120, 60)).save(buf, format='JPEG')
        return buf.getvalue()
    except Exception as e:
        raise RuntimeError(f"Cannot create fake JPEG (PIL missing?): {e}") from e


def _mock_db(vgk_row=None, kyc_row=None):
    """
    Build a mock SQLAlchemy-like db that returns vgk_row for the first execute
    call (vgk_kyc_documents query) and kyc_row for the second (kyc_document).
    """
    call_count = [0]

    def side_effect(sql, params=None):
        call_count[0] += 1
        result = mock.MagicMock()
        if call_count[0] == 1:
            result.fetchone.return_value = vgk_row
        else:
            result.fetchone.return_value = kyc_row
        return result

    db = mock.MagicMock()
    db.execute.side_effect = side_effect
    return db


def _import_module():
    """Import vgk_earner_card with storage_service patched out."""
    # Patch object_storage so we don't need Replit credentials
    fake_storage = mock.MagicMock()
    fake_storage.download_file.return_value = None  # default: nothing in storage

    storage_mod = types.ModuleType('app.services.object_storage')
    storage_mod.storage_service = fake_storage

    # Insert stub modules so the import chain resolves cleanly
    sys.modules.setdefault('app', types.ModuleType('app'))
    sys.modules.setdefault('app.services', types.ModuleType('app.services'))
    sys.modules['app.services.object_storage'] = storage_mod

    # Now import the real module from the file path
    import importlib.util
    spec_path = Path(__file__).resolve().parent.parent / 'app' / 'services' / 'vgk_earner_card.py'
    spec = importlib.util.spec_from_file_location('vgk_earner_card', spec_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, fake_storage


def test_priority1_vgk_profile_photo():
    banner("Test 1: VGK profile_photo is returned when available (priority 1)")
    mod, storage = _import_module()
    photo = _make_fake_jpeg()
    storage.download_file.return_value = photo

    # vgk_row returns a file_path + object_storage type
    db = _mock_db(
        vgk_row=('kyc_documents/vgk_profile.jpg', 'object_storage'),
        kyc_row=('kyc_documents/passport.jpg', 'object_storage'),
    )
    result = mod._get_kyc_photo_bytes(db, partner_id=1)
    if result == photo:
        _ok("VGK profile_photo bytes returned correctly")
    else:
        _fail("VGK profile_photo priority", f"Expected photo bytes, got {result!r}")


def test_priority2_fallback_to_kyc_passport():
    banner("Test 2: Falls back to kyc_document passport_photo when VGK photo absent")
    mod, storage = _import_module()
    photo = _make_fake_jpeg()

    call_count = [0]
    def storage_side(fp):
        call_count[0] += 1
        # First call is for vgk_kyc_documents → return None
        # Second call is for kyc_document → return photo
        if call_count[0] == 1:
            return None
        return photo

    storage.download_file.side_effect = storage_side

    db = _mock_db(
        vgk_row=('kyc_documents/vgk_profile.jpg', 'object_storage'),
        kyc_row=('kyc_documents/passport.jpg', 'object_storage'),
    )
    result = mod._get_kyc_photo_bytes(db, partner_id=2)
    if result == photo:
        _ok("Fell back to passport_photo bytes correctly")
    else:
        _fail("passport_photo fallback", f"Expected photo bytes, got {result!r}")


def test_no_rows_returns_none():
    banner("Test 3: Returns None when neither DB row exists → gold initials fallback")
    mod, storage = _import_module()
    storage.download_file.return_value = None

    db = _mock_db(vgk_row=None, kyc_row=None)
    result = mod._get_kyc_photo_bytes(db, partner_id=99)
    if result is None:
        _ok("Returns None (gold initials fallback) when no KYC rows exist")
    else:
        _fail("no-rows returns None", f"Expected None, got {result!r}")


def test_storage_failure_returns_none():
    banner("Test 4: Returns None when storage fetch fails for both sources")
    mod, storage = _import_module()
    storage.download_file.side_effect = Exception("storage down")

    db = _mock_db(
        vgk_row=('kyc_documents/vgk_profile.jpg', 'object_storage'),
        kyc_row=('kyc_documents/passport.jpg', 'object_storage'),
    )
    result = mod._get_kyc_photo_bytes(db, partner_id=3)
    if result is None:
        _ok("Returns None gracefully when storage raises exceptions")
    else:
        _fail("storage-failure fallback", f"Expected None, got {result!r}")


def test_compose_earner_card_no_photo():
    banner("Test 5: compose_earner_card renders without error when photo_bytes=None")
    mod, _ = _import_module()
    try:
        card = mod.compose_earner_card(
            partner_name='Test Partner',
            partner_code='TST001',
            location='Mumbai, Maharashtra',
            designation='Channel Partner',
            gross_amount=5000.0,
            overall_earnings=15000.0,
            photo_bytes=None,
            name_title='Mr',
        )
        if isinstance(card, bytes) and len(card) > 100:
            _ok("compose_earner_card succeeds with photo_bytes=None (gold initials rendered)")
        else:
            _fail("compose no photo", f"Unexpected return: {type(card)}, len={len(card) if isinstance(card, bytes) else 'N/A'}")
    except Exception as e:
        _fail("compose no photo raised", str(e))


def test_compose_earner_card_with_photo():
    banner("Test 6: compose_earner_card renders without error when photo_bytes is a valid image")
    mod, _ = _import_module()
    photo = _make_fake_jpeg(60, 60)
    try:
        card = mod.compose_earner_card(
            partner_name='Test Partner',
            partner_code='TST001',
            location='Delhi',
            designation='Master Franchise',
            gross_amount=12000.0,
            overall_earnings=45000.0,
            photo_bytes=photo,
            name_title='Ms',
        )
        if isinstance(card, bytes) and len(card) > 100:
            _ok("compose_earner_card succeeds with photo_bytes set (member face rendered)")
        else:
            _fail("compose with photo", f"Unexpected return: {type(card)}, len={len(card) if isinstance(card, bytes) else 'N/A'}")
    except Exception as e:
        _fail("compose with photo raised", str(e))


def main() -> int:
    banner(f"Task #54 — Earner Card KYC Photo Regression Tests")
    test_priority1_vgk_profile_photo()
    test_priority2_fallback_to_kyc_passport()
    test_no_rows_returns_none()
    test_storage_failure_returns_none()
    test_compose_earner_card_no_photo()
    test_compose_earner_card_with_photo()

    banner("Summary")
    print(f"  passed: {len(PASSED)}")
    print(f"  failed: {len(FAILED)}")
    for name, msg in FAILED:
        print(f"    - {name}: {msg}")
    return 0 if not FAILED else 1


if __name__ == "__main__":
    sys.exit(main())
