"""
Tests for Option C Dual-Ring Sticky Agent Routing & WhatsApp Group Alert Queueing.
"""

import unittest
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session

from app.services.telephony.flow_interpreter import CallFlowInterpreter
from app.models.staff import StaffEmployee
from app.models.telephony_call_flow import TelephonyPlivoEndpoint
from app.services.whatsapp_group_alert_service import send_group_bot_message


class TestStickyAgentOptionC(unittest.TestCase):

    def setUp(self):
        self.db = MagicMock(spec=Session)

    def test_dual_ring_when_softphone_registered_and_phone_present(self):
        """Test Option C: When staff has both registered softphone and personal phone, Plivo dials both in parallel."""
        mock_emp = MagicMock(spec=StaffEmployee)
        mock_emp.id = 320
        mock_emp.full_name = "Mrs. Janapala Hema"
        mock_emp.phone = "7036039473"
        mock_emp.status = "active"

        mock_endpoint = MagicMock(spec=TelephonyPlivoEndpoint)
        mock_endpoint.is_registered = True
        mock_endpoint.plivo_username = "agentc4s28018571317797514970"

        with patch.object(CallFlowInterpreter, '_evaluate_business_hours', return_value=(True, "Open")):
            with patch.object(CallFlowInterpreter, '_resolve_caller_assigned_staff', return_value=(mock_emp, "recent_voip_session")):
                # Mock endpoint query
                query_mock = MagicMock()
                self.db.query.return_value = query_mock
                query_mock.filter.return_value = query_mock
                query_mock.order_by.return_value = query_mock
                query_mock.first.return_value = mock_endpoint

                with patch.object(CallFlowInterpreter, '_build_telesales_simultaneous_dial', return_value="<Dial><Number>+918000</Number></Dial>"):
                    xml_output = CallFlowInterpreter._check_sticky_agent(
                        db=self.db,
                        caller_phone="+919876543210",
                        called_did="+918031728899",
                        company_id=1
                    )

                    self.assertIsNotNone(xml_output)
                    self.assertIn("<User>sip:agentc4s28018571317797514970@phone.plivo.com</User>", xml_output)
                    self.assertIn("<Number>+917036039473</Number>", xml_output)
                    self.assertIn('callerId="+918031728899"', xml_output)
                    self.assertIn('Mrs. Janapala Hema', xml_output)
                    print("✓ Dual-Ring: Successfully generated simultaneous <User> and <Number> targets")

    def test_single_ring_personal_phone_when_softphone_unregistered(self):
        """Test Option C Fallback: When staff is offline/unregistered, Plivo dials personal mobile phone directly."""
        mock_emp = MagicMock(spec=StaffEmployee)
        mock_emp.id = 320
        mock_emp.full_name = "Mrs. Janapala Hema"
        mock_emp.phone = "7036039473"
        mock_emp.status = "active"

        # Endpoint is unregistered / offline
        mock_endpoint = MagicMock(spec=TelephonyPlivoEndpoint)
        mock_endpoint.is_registered = False
        mock_endpoint.plivo_username = "agentc4s28018571317797514970"

        with patch.object(CallFlowInterpreter, '_evaluate_business_hours', return_value=(True, "Open")):
            with patch.object(CallFlowInterpreter, '_resolve_caller_assigned_staff', return_value=(mock_emp, "recent_voip_session")):
                query_mock = MagicMock()
                self.db.query.return_value = query_mock
                query_mock.filter.return_value = query_mock
                query_mock.order_by.return_value = query_mock
                query_mock.first.return_value = mock_endpoint

                with patch.object(CallFlowInterpreter, '_build_telesales_simultaneous_dial', return_value="<Dial><Number>+918000</Number></Dial>"):
                    xml_output = CallFlowInterpreter._check_sticky_agent(
                        db=self.db,
                        caller_phone="+919876543210",
                        called_did="+918031728899",
                        company_id=1
                    )

                    self.assertIsNotNone(xml_output)
                    # Softphone SIP URI should NOT be included because is_registered is False
                    self.assertNotIn("<User>", xml_output)
                    # Personal phone MUST be included
                    self.assertIn("<Number>+917036039473</Number>", xml_output)
                    print("✓ Offline Softphone: Successfully fell back to personal mobile phone")

    def test_returns_none_when_neither_softphone_nor_phone_available(self):
        """Test Option C: When neither softphone nor personal phone exists, returns None for Main IVR fallback."""
        mock_emp = MagicMock(spec=StaffEmployee)
        mock_emp.id = 320
        mock_emp.full_name = "Mrs. Janapala Hema"
        mock_emp.phone = None
        mock_emp.status = "active"

        with patch.object(CallFlowInterpreter, '_evaluate_business_hours', return_value=(True, "Open")):
            with patch.object(CallFlowInterpreter, '_resolve_caller_assigned_staff', return_value=(mock_emp, "recent_voip_session")):
                query_mock = MagicMock()
                self.db.query.return_value = query_mock
                query_mock.filter.return_value = query_mock
                query_mock.order_by.return_value = query_mock
                query_mock.first.return_value = None

                xml_output = CallFlowInterpreter._check_sticky_agent(
                    db=self.db,
                    caller_phone="+919876543210",
                    called_did="+918031728899",
                    company_id=1
                )

                self.assertIsNone(xml_output)
                print("✓ No Contact Targets: Returned None to gracefully proceed to Sales IVR")


class TestWhatsAppGroupAlertQueueing(unittest.TestCase):

    def test_fallback_to_queue_when_bot_gateway_returns_503(self):
        """Test that when WhatsApp Bot returns 503 (qr_ready / not connected), message is enqueued to DB."""
        mock_db = MagicMock(spec=Session)
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = [999]
        mock_db.execute.return_value = mock_cursor

        mock_resp = MagicMock()
        mock_resp.status_code = 503
        mock_resp.json.return_value = {"success": False, "error": "WhatsApp bot not connected. Scan QR code at /qr"}
        mock_resp.text = "WhatsApp bot not connected. Scan QR code at /qr"

        with patch("requests.post", return_value=mock_resp):
            res = send_group_bot_message(
                message_text="🚨 *NEW LEAD RECEIVED!*",
                invite_code="LfX8mGootXa7SpwNIz7P5C",
                group_id="120363410784518818@g.us",
                db=mock_db
            )

            self.assertTrue(res.get("success"))
            self.assertTrue(res.get("queued"))
            self.assertEqual(res.get("queue_id"), 999)
            mock_db.commit.assert_called_once()
            print("✓ WhatsApp Queue Fallback: Successfully caught HTTP 503 and enqueued directly to whatsapp_bot_queue")


class TestScreenOffWakeupAndStickyRetry(unittest.TestCase):

    def test_sticky_dial_complete_screen_off_retry_then_voicemail(self):
        """Test that handle_sticky_dial_complete performs a 25s WebRTC SIP retry when mobile screen wakes up, then falls back to voicemail on retry=1."""
        mock_db = MagicMock(spec=Session)
        mock_emp = MagicMock()
        mock_emp.id = 45
        mock_emp.first_name = "Anusha"
        mock_emp.full_name = "Anusha"

        mock_ep = MagicMock()
        mock_ep.staff_id = 45
        mock_ep.plivo_username = "myntos_staff_1_45_abcd1234"
        mock_ep.endpoint_username = "myntos_staff_1_45_abcd1234"
        mock_ep.endpoint_alias = "staff_1_45"
        mock_ep.is_active = True

        def query_side_effect(model):
            q = MagicMock()
            q.filter.return_value = q
            q.order_by.return_value = q
            if getattr(model, "__name__", "") in ("Employee", "StaffEmployee"):
                q.first.return_value = mock_emp
            elif getattr(model, "__name__", "") == "TelephonyPlivoEndpoint":
                q.first.return_value = mock_ep
            else:
                q.first.return_value = None
            return q

        mock_db.query.side_effect = query_side_effect

        # 1st attempt timeout (retry="0") -> should return <Wait length="3" /> + <Dial timeout="25"> with retry=1
        xml_retry = CallFlowInterpreter.handle_sticky_dial_complete(
            db=mock_db,
            form_data={"DialStatus": "no-answer", "From": "+919876543210", "To": "+918031728899"},
            query_params={"staff_id": "45", "session_id": "sess_test_1", "retry": "0"},
        )
        self.assertIn('<Wait length="3" />', xml_retry)
        self.assertIn('<User>sip:myntos_staff_1_45_abcd1234@phone.plivo.com</User>', xml_retry)
        self.assertIn("retry=1", xml_retry)

        # 2nd attempt timeout (retry="1") -> should proceed to executive voicemail
        xml_vm = CallFlowInterpreter.handle_sticky_dial_complete(
            db=mock_db,
            form_data={"DialStatus": "no-answer", "From": "+919876543210", "To": "+918031728899"},
            query_params={"staff_id": "45", "session_id": "sess_test_1", "retry": "1"},
        )
        self.assertIn("<Record", xml_vm)
        self.assertIn("currently assisting another client", xml_vm)
        print("✓ Screen-Off Sticky Dial Retry: Verified 1st timeout retries SIP after 3s wakeup, 2nd timeout goes to voicemail")

    def test_mobile_call_notifier_ringing_lookup(self):
        """Test MobileCallNotifier stores active ringing call and marks cancelled calls for screen-off standby polling."""
        from app.services.telephony.mobile_push_service import MobileCallNotifier, _CALL_STATE_CACHE
        _CALL_STATE_CACHE.clear()
        mock_db = MagicMock(spec=Session)
        q = MagicMock()
        q.filter.return_value = q
        q.all.return_value = []
        q.first.return_value = None
        mock_db.query.return_value = q

        MobileCallNotifier.notify_inbound_call(
            caller_phone="+919876543210",
            called_did="+918031728899",
            provider_call_id="uuid_99",
            call_session_id="sess_screenoff_99",
            target_staff_ids=[45],
            company_id=1,
            lead_name="Returning Customer",
            db=mock_db,
        )
        active = MobileCallNotifier.get_active_ringing_call_for_staff(45)
        self.assertIsNotNone(active)
        self.assertEqual(active["state"], "ringing")
        self.assertEqual(active["payload"]["call_session_id"], "sess_screenoff_99")

        MobileCallNotifier.notify_call_cancelled(
            call_session_id="sess_screenoff_99",
            provider_call_id="uuid_99",
            target_staff_ids=[45],
            company_id=1,
            reason="caller_hangup",
            db=mock_db,
        )
        cancelled = MobileCallNotifier.get_active_ringing_call_for_staff(45)
        self.assertIsNotNone(cancelled)
        self.assertEqual(cancelled["state"], "cancelled")
        print("✓ MobileCallNotifier Standby Cache: Verified active ringing and cancelled call state retrieval")


if __name__ == "__main__":
    unittest.main()

