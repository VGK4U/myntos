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


if __name__ == "__main__":
    unittest.main()
