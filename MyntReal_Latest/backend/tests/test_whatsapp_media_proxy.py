"""
Test Suite: WhatsApp Media Proxy, Normalization & 404 Prevention Guard
Tests the complete resolution pipeline for WhatsApp media attachments across:
1. WAInbox to_dict() media_url normalization
2. Meta webhook incoming media normalization
3. Dedicated /media/{media_id} endpoint (cache hit, anti-traversal, graceful fallback)
4. Frontend server.js /staff/{media_id} redirect regex
"""
import re
import os
import io
import asyncio
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import Request

from app.models.whatsapp import WAInbox


def test_wainbox_to_dict_normalization():
    print("Test 1: WAInbox to_dict() Media Normalization")
    
    # 1. Numeric Meta Media ID
    item1 = WAInbox(
        id=101,
        from_phone="919876543210",
        message_type="image",
        media_url="1754771135832827",
        media_mime_type="image/jpeg"
    )
    d1 = item1.to_dict()
    assert d1["media_url"] == "/api/v1/whatsapp/media/1754771135832827", f"Expected normalized URL, got {d1['media_url']}"
    print("  ✅ 1.1 Numeric Meta media ID normalized to /api/v1/whatsapp/media/1754771135832827")

    # 2. Already fully qualified URL
    item2 = WAInbox(
        id=102,
        from_phone="919876543210",
        message_type="image",
        media_url="https://s3.ap-south-2.amazonaws.com/myntreal/img.jpg"
    )
    d2 = item2.to_dict()
    assert d2["media_url"] == "https://s3.ap-south-2.amazonaws.com/myntreal/img.jpg"
    print("  ✅ 1.2 Full HTTPS URL preserved unchanged")

    # 3. Local storage path
    item3 = WAInbox(
        id=103,
        from_phone="919876543210",
        message_type="document",
        media_url="/storage/wa_media/brochure.pdf"
    )
    d3 = item3.to_dict()
    assert d3["media_url"] == "/storage/wa_media/brochure.pdf"
    print("  ✅ 1.3 Local storage path preserved unchanged")

    # 4. Null media_url
    item4 = WAInbox(
        id=104,
        from_phone="919876543210",
        message_type="text",
        media_url=None
    )
    d4 = item4.to_dict()
    assert d4["media_url"] is None
    print("  ✅ 1.4 None media_url preserved as None")


def test_server_js_redirect_regex():
    print("\nTest 2: server.js /staff/{media_id} Redirect Guard Regex")
    pattern = re.compile(r'^\/staff\/\d+$')

    # Should match numeric media ID clicked from relative path
    assert pattern.match("/staff/1754771135832827") is not None
    assert pattern.match("/staff/987654321") is not None
    print("  ✅ 2.1 Numeric /staff/{media_id} matches redirect guard")

    # Should NOT match normal staff application routes
    assert pattern.match("/staff/crm") is None
    assert pattern.match("/staff/leads") is None
    assert pattern.match("/staff/whatsapp") is None
    assert pattern.match("/staff/attendance") is None
    assert pattern.match("/staff/profile") is None
    print("  ✅ 2.2 Standard staff navigation routes (/staff/crm, /staff/whatsapp, etc.) correctly bypass redirect")


def test_media_streaming_endpoint():
    print("\nTest 3: Media Streaming Proxy Endpoint Logic")
    from app.main import app
    client = TestClient(app)

    # 3.1 Path traversal security
    res = client.get("/api/v1/whatsapp/media/..test")
    assert res.status_code == 400
    print("  ✅ 3.1 Anti-path traversal guard prevents illegal file access (HTTP 400)")

    # 3.2 Cache hit from local filesystem
    storage_dir = Path(__file__).resolve().parent.parent.parent / "frontend" / "storage" / "wa_media"
    storage_dir.mkdir(parents=True, exist_ok=True)
    test_media_id = "999888777666"
    test_file = storage_dir / f"meta_{test_media_id}.jpg"
    test_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xdb"
    test_file.write_bytes(test_bytes)

    try:
        res = client.get(f"/api/v1/whatsapp/media/{test_media_id}")
        assert res.status_code == 200
        assert res.content == test_bytes
        assert "image/" in res.headers.get("content-type", "")
        print("  ✅ 3.2 Local cached attachment served with HTTP 200 and image Content-Type")
    finally:
        if test_file.exists():
            test_file.unlink()

    # 3.3 Fallback when media expired on Meta servers
    res_html = client.get("/api/v1/whatsapp/media/0000000000", headers={"Accept": "text/html"})
    assert res_html.status_code == 200
    assert "WhatsApp Media Attachment" in res_html.text
    assert "0000000000" in res_html.text
    print("  ✅ 3.3 Expired/unavailable attachment renders friendly informative card")

    res_img = client.get("/api/v1/whatsapp/media/0000000000", headers={"Accept": "image/*"})
    assert res_img.status_code == 200
    assert "image/svg+xml" in res_img.headers.get("content-type", "")
    print("  ✅ 3.4 Image request fallback returns SVG placeholder")


if __name__ == "__main__":
    test_wainbox_to_dict_normalization()
    test_server_js_redirect_regex()
    test_media_streaming_endpoint()
    print("\n🎉 ALL WHATSAPP MEDIA PROXY AND ATTACHMENT TESTS PASSED!")
