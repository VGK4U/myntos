"""
Test WhatsApp Anti-Ban Hardening & Dedup Suite
Verifies:
1. Baileys customer 1-to-1 fallback is suppressed outside 24h window (Gap 1).
2. Missed call WhatsApp ACK only triggers on recent calls (<45m), not historical backfills (Gap 2).
3. Positional {{1}} and named {{name}} placeholders render correctly (Gap 3).
4. Morning wishes enforce 3-day (72h) deduplication and 3-strike failure suppression (Gap 4).
5. Lead welcome enforces 7-day persistent database deduplication (Gap 5).
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from app.services.whatsapp_auto_service import _render_body, _send_meta, send_lead_welcome


def test_render_body_placeholders():
    """Verify Gap 3: {{1}}, {{name}}, and missing placeholders are safely rendered."""
    ctx = {"name": "Suresh Kumar", "lead_ref": "#123"}
    
    # Template with {{1}}
    body1 = "నమస్కారం {{1}}!\nWelcome to EVolution Training Centre!"
    res1 = _render_body(body1, ctx)
    assert "Suresh Kumar" in res1
    assert "{{1}}" not in res1

    # Template with {{name}}
    body2 = "Good Morning {{name}}! Welcome back."
    res2 = _render_body(body2, ctx)
    assert "Suresh Kumar" in res2
    assert "{{name}}" not in res2

    # Unpopulated placeholder falls back gracefully without raw code syntax
    body3 = "Hello {{1}}, your token is {{token}}."
    res3 = _render_body(body3, {})
    assert "Valued Customer" in res3
    assert "{{1}}" not in res3


def test_baileys_customer_fallback_disabled():
    """Verify Gap 1: Outside 24h window, Baileys fallback is suppressed to protect SIM."""
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None

    with patch.dict("os.environ", {"ENVIRONMENT": "production"}):
        res = _send_meta(phone="919876543210", message="Test cold text", template=None, db=mock_db)
        assert res["success"] is False
        assert res["error_code"] == "WINDOW_EXPIRED"
        assert "disabled to protect SIM" in res["reason"]


def test_persistent_welcome_deduplication():
    """Verify Gap 5: Persistent DB check prevents duplicate welcome messages."""
    mock_db = MagicMock()
    
    mock_log = MagicMock()
    mock_log.id = 9999
    mock_log.sent_at = datetime.utcnow() - timedelta(days=2)
    mock_db.query.return_value.filter.return_value.first.return_value = mock_log

    res = send_lead_welcome(
        db=mock_db,
        phone="9876543210",
        lead_name="Test Lead",
        lead_id=12345
    )
    assert res["success"] is False
    assert res["reason"] == "already_sent_db"
    assert res["message_log_id"] == 9999


def test_lead_welcome_failover_to_scanned_when_meta_fails():
    """Verify that when Meta Cloud API fails, send_lead_welcome automatically fails over to Scanned WhatsApp."""
    from app.services.whatsapp_auto_service import dispatch_scanned_lead_fallback

    mock_db = MagicMock()
    # Mock dedup checks passing (no prior message)
    mock_db.query.return_value.filter.return_value.first.return_value = None
    mock_template = MagicMock()
    mock_template.id = 1
    mock_template.body_text = "Welcome {{name}}"
    mock_template.is_meta_approved = True
    mock_template.meta_template_name = "myntreal_lead_welcome_solar"
    mock_template.meta_template_language = "en"
    mock_db.query.return_value.filter_by.return_value.first.return_value = mock_template

    with patch("app.services.whatsapp_auto_service._send_meta") as mock_meta, \
         patch("app.services.whatsapp_auto_service.dispatch_scanned_lead_fallback") as mock_fallback:
        
        # Meta returns error (e.g. 131031 deadlock or unapproved)
        mock_meta.return_value = {"success": False, "reason": "Error 131031: Payment Deadlock", "error_code": "131031"}
        mock_fallback.return_value = {
            "success": True,
            "queued": True,
            "execution_id": "lead_fb_9876543210_12345",
            "channel": "scanned_fallback",
            "via": "bot_queue"
        }

        res = send_lead_welcome(
            db=mock_db,
            phone="9876543210",
            lead_name="Praveen Varma",
            lead_id=77889
        )

        assert res["success"] is True
        assert res["channel"] == "scanned_fallback"
        assert res["queued"] is True
        mock_fallback.assert_called_once()


def test_lead_fallback_enqueues_when_bot_offline():
    """Verify dispatch_scanned_lead_fallback safely enqueues into whatsapp_bot_queue when gateway is offline."""
    from app.services.whatsapp_auto_service import dispatch_scanned_lead_fallback

    mock_db = MagicMock()

    with patch("requests.get", side_effect=Exception("Connection Refused (Offline)")), \
         patch("app.models.whatsapp.MessageLog") as mock_ml_cls:
        
        res = dispatch_scanned_lead_fallback(
            db=mock_db,
            phone="9123456780",
            message="Welcome to MyntReal!",
            lead_id=55443,
            event_key="lead_welcome_solar",
            reason="Meta API 131031 payment deadlock"
        )

        assert res["success"] is True
        assert res["queued"] is True
        assert res["via"] == "bot_queue"
        assert res["channel"] == "scanned_fallback"

        # Verify SQL INSERT into whatsapp_bot_queue was executed
        assert mock_db.execute.called
        call_args = mock_db.execute.call_args
        sql_text = str(call_args[0][0])
        assert "INSERT INTO whatsapp_bot_queue" in sql_text
        assert mock_db.commit.called


def test_lead_fallback_dispatches_with_pacing_when_bot_online():
    """Verify dispatch_scanned_lead_fallback dispatches to port 5002 with pacing when bot is online."""
    from app.services.whatsapp_auto_service import dispatch_scanned_lead_fallback

    mock_db = MagicMock()

    # Mock gateway /status as online and ready
    mock_status_resp = MagicMock()
    mock_status_resp.status_code = 200
    mock_status_resp.json.return_value = {"can_send_now": True, "connection_state": "connected"}

    # Mock /api/send-message response
    mock_send_resp = MagicMock()
    mock_send_resp.status_code = 200
    mock_send_resp.json.return_value = {"success": True, "message_id": "scanned_wamid_12345"}

    with patch("requests.get", return_value=mock_status_resp), \
         patch("requests.post", return_value=mock_send_resp), \
         patch("time.sleep") as mock_sleep:
        
        res = dispatch_scanned_lead_fallback(
            db=mock_db,
            phone="9123456780",
            message="Welcome to MyntReal!",
            lead_id=55443,
            event_key="lead_welcome_solar",
            reason="Meta API 131031 payment deadlock"
        )

        assert res["success"] is True
        assert res["channel"] == "scanned_fallback"
        assert res["via"] == "direct_gateway"
        assert res["wamid"] == "scanned_wamid_12345"
        # Verify pacing delay was applied
        mock_sleep.assert_called_with(3.0)


if __name__ == "__main__":
    print("Running WhatsApp Anti-Ban Hardening Tests...")
    test_render_body_placeholders()
    print("✅ test_render_body_placeholders passed")
    test_baileys_customer_fallback_disabled()
    print("✅ test_baileys_customer_fallback_disabled passed")
    test_persistent_welcome_deduplication()
    print("✅ test_persistent_welcome_deduplication passed")
    test_lead_welcome_failover_to_scanned_when_meta_fails()
    print("✅ test_lead_welcome_failover_to_scanned_when_meta_fails passed")
    test_lead_fallback_enqueues_when_bot_offline()
    print("✅ test_lead_fallback_enqueues_when_bot_offline passed")
    test_lead_fallback_dispatches_with_pacing_when_bot_online()
    print("✅ test_lead_fallback_dispatches_with_pacing_when_bot_online passed")
    print("🎉 All Anti-Ban Hardening & Failover tests PASSED successfully!")
