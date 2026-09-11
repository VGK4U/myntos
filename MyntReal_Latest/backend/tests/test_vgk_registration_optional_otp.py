"""
Comprehensive Test Suite — Optional WhatsApp OTP & Registration Verification
DC-VGK-OPTIONAL-OTP-001 / DC-PHONE-OTP-001

Test Matrix:
1.  Scenario 1:  OTP delivered -> OTP verified -> registration succeeds -> VERIFIED status (phone_verified=True)
2.  Scenario 2:  OTP send fails -> registration continues -> UNVERIFIED / PENDING status (phone_verified=False)
3.  Scenario 3:  User skips OTP -> registration succeeds -> UNVERIFIED / PENDING status (phone_verified=False)
4.  Scenario 4:  Wrong OTP entered -> verification fails -> cannot claim VERIFIED status
5.  Scenario 5:  Expired OTP entered -> verification fails -> cannot claim VERIFIED status
6.  Scenario 6:  Successful later verification -> state updates from False to True
7.  Scenario 7:  Meta error 131031 (Account locked) -> registration remains possible
8.  Scenario 8:  Meta error 131047 (Re-engagement window) -> registration remains possible
9.  Scenario 9:  Meta provider inconsistency (NO_WAMID) -> registration remains possible
10. Scenario 10: Frontend skip + backend registration -> succeeds with phone_verified=False
11. Scenario 11: Direct API request without OTP token -> follows optional rule (mobile_verified=False)
12. Scenario 12: Mandatory validations (missing name, short password, duplicate checks) strictly enforced
"""

import unittest
import time
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import text as sa_text

from app.main import app
from app.core.database import SessionLocal
from app.models.staff_accounts import OfficialPartner
from app.models.user import User


class TestVGKRegistrationOptionalOTP(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)
        self.db: Session = SessionLocal()
        self.created_partner_phones = []
        self.created_user_mobiles = []

    def tearDown(self):
        try:
            for phone in self.created_partner_phones:
                self.db.query(OfficialPartner).filter(OfficialPartner.phone == phone).delete()
                self.db.execute(sa_text("DELETE FROM phone_otp_verifications WHERE phone = :p"), {"p": phone})
            for mobile in self.created_user_mobiles:
                self.db.query(User).filter(User.phone_number == mobile).delete()
                self.db.execute(sa_text("DELETE FROM phone_otp_verifications WHERE phone = :p"), {"p": mobile})
            self.db.commit()
        except Exception:
            self.db.rollback()
        finally:
            self.db.close()

    def _get_latest_otp(self, phone: str, purpose: str = None):
        if purpose:
            row = self.db.execute(sa_text(
                "SELECT otp_code FROM phone_otp_verifications "
                "WHERE phone = :p AND purpose = :purpose ORDER BY created_at DESC LIMIT 1"
            ), {"p": phone, "purpose": purpose}).fetchone()
        else:
            row = self.db.execute(sa_text(
                "SELECT otp_code FROM phone_otp_verifications "
                "WHERE phone = :p ORDER BY created_at DESC LIMIT 1"
            ), {"p": phone}).fetchone()
        return row[0] if row else None

    # 1. OTP delivered -> OTP verified -> registration succeeds -> phone_verified=True
    @patch("app.services.whatsapp_canonical_service.WhatsAppCanonicalService.send_meta_template_message")
    def test_01_otp_verified_registration_succeeds_as_verified(self, mock_send):
        mock_send.return_value = {"success": True, "wamid": "wamid.TEST01", "status": "sent"}
        phone = f"91000{int(time.time()) % 100000:05d}"
        self.created_partner_phones.append(phone)

        # 1. Send OTP
        send_res = self.client.post("/api/v1/vgk/auth/signup/send-otp", json={"phone": phone})
        self.assertEqual(send_res.status_code, 200)
        self.assertTrue(send_res.json()["success"])
        self.assertTrue(send_res.json()["otp_sent"])

        # Extract stored OTP code from DB
        otp_code = self._get_latest_otp(phone)
        self.assertIsNotNone(otp_code)

        # 2. Verify OTP -> get token
        verify_res = self.client.post("/api/v1/vgk/auth/signup/verify-otp", json={"phone": phone, "otp_code": otp_code})
        self.assertEqual(verify_res.status_code, 200)
        token = verify_res.json().get("phone_verified_token")
        self.assertTrue(token)

        # 3. Register with verified token
        reg_payload = {
            "partner_name": "Test Verified Partner",
            "phone": phone,
            "password": "Password@123",
            "phone_verified_token": token,
        }
        res = self.client.post("/api/v1/vgk/auth/signup", json=reg_payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["phone_verified"], True)

        # Check in DB
        partner = self.db.query(OfficialPartner).filter_by(phone=phone).first()
        self.assertIsNotNone(partner)
        self.assertTrue(partner.phone_verified)

    # 2. OTP send fails -> registration continues -> phone_verified=False
    @patch("app.services.whatsapp_canonical_service.WhatsAppCanonicalService.send_meta_template_message")
    def test_02_otp_send_fails_registration_continues_unverified(self, mock_send):
        mock_send.return_value = {
            "success": False,
            "error_code": 131031,
            "error_message": "Business Account locked",
            "status": "failed",
        }
        phone = f"91001{int(time.time()) % 100000:05d}"
        self.created_partner_phones.append(phone)

        # Send OTP returns non-blocking success with otp_sent=False
        send_res = self.client.post("/api/v1/vgk/auth/signup/send-otp", json={"phone": phone})
        self.assertEqual(send_res.status_code, 200)
        self.assertTrue(send_res.json()["success"])
        self.assertFalse(send_res.json()["otp_sent"])

        # User proceeds to register without token
        reg_payload = {
            "partner_name": "Test Unverified Partner",
            "phone": phone,
            "password": "Password@123",
            "phone_verified_token": None,
        }
        res = self.client.post("/api/v1/vgk/auth/signup", json=reg_payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["phone_verified"], False)

        # Check DB
        partner = self.db.query(OfficialPartner).filter_by(phone=phone).first()
        self.assertIsNotNone(partner)
        self.assertFalse(partner.phone_verified)

    # 3. User skips OTP -> registration succeeds -> phone_verified=False
    def test_03_user_skips_otp_registration_succeeds_unverified(self):
        phone = f"91002{int(time.time()) % 100000:05d}"
        self.created_partner_phones.append(phone)

        reg_payload = {
            "partner_name": "Test Skipped OTP Partner",
            "phone": phone,
            "password": "Password@123",
        }
        res = self.client.post("/api/v1/vgk/auth/signup", json=reg_payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["phone_verified"], False)

        partner = self.db.query(OfficialPartner).filter_by(phone=phone).first()
        self.assertIsNotNone(partner)
        self.assertFalse(partner.phone_verified)

    # 4. Wrong OTP entered -> cannot claim VERIFIED status
    @patch("app.services.whatsapp_canonical_service.WhatsAppCanonicalService.send_meta_template_message")
    def test_04_wrong_otp_cannot_claim_verified(self, mock_send):
        mock_send.return_value = {"success": True, "wamid": "wamid.TEST04", "status": "sent"}
        phone = f"91003{int(time.time()) % 100000:05d}"
        self.created_partner_phones.append(phone)

        # Send OTP
        self.client.post("/api/v1/vgk/auth/signup/send-otp", json={"phone": phone})

        # Try wrong OTP
        verify_res = self.client.post("/api/v1/vgk/auth/signup/verify-otp", json={"phone": phone, "otp_code": "000000"})
        self.assertEqual(verify_res.status_code, 400)
        self.assertIn("Invalid OTP", verify_res.json()["detail"])

        # Try registering with invalid token string
        reg_payload = {
            "partner_name": "Test Invalid Token Partner",
            "phone": phone,
            "password": "Password@123",
            "phone_verified_token": "fake_token_123",
        }
        res = self.client.post("/api/v1/vgk/auth/signup", json=reg_payload)
        self.assertEqual(res.status_code, 400)
        self.assertIn("Phone verification required", res.json()["detail"])

    # 5. Expired OTP entered -> cannot claim VERIFIED status
    def test_05_expired_otp_cannot_claim_verified(self):
        phone = f"91004{int(time.time()) % 100000:05d}"
        self.created_partner_phones.append(phone)

        # Insert expired OTP directly
        self.db.execute(sa_text(
            "INSERT INTO phone_otp_verifications (phone, purpose, otp_code, expires_at, created_at) "
            "VALUES (:p, 'vgk_signup', '123456', NOW() - INTERVAL '10 minutes', NOW() - INTERVAL '20 minutes')"
        ), {"p": phone})
        self.db.commit()

        verify_res = self.client.post("/api/v1/vgk/auth/signup/verify-otp", json={"phone": phone, "otp_code": "123456"})
        self.assertEqual(verify_res.status_code, 400)
        self.assertIn("expired", verify_res.json()["detail"])

    # 6. Successful later verification -> state updates from False to True
    @patch("app.services.whatsapp_canonical_service.WhatsAppCanonicalService.send_meta_template_message")
    def test_06_later_verification_updates_state_to_verified(self, mock_send):
        mock_send.return_value = {"success": True, "wamid": "wamid.LATER01", "status": "sent"}
        phone = f"91005{int(time.time()) % 100000:05d}"
        self.created_partner_phones.append(phone)

        # 1. Register with OTP skipped
        reg_res = self.client.post("/api/v1/vgk/auth/signup", json={
            "partner_name": "Test Later Verify Partner",
            "phone": phone,
            "password": "Password@123",
        })
        self.assertEqual(reg_res.status_code, 200)
        partner = self.db.query(OfficialPartner).filter_by(phone=phone).first()
        self.assertFalse(partner.phone_verified)

        # 2. Trigger later verification send-otp
        send_res = self.client.post("/api/v1/vgk/auth/verify-phone/send-otp", json={"phone": phone})
        self.assertEqual(send_res.status_code, 200)

        otp_code = self._get_latest_otp(phone)
        self.assertIsNotNone(otp_code)

        # 3. Confirm later verification OTP
        confirm_res = self.client.post("/api/v1/vgk/auth/verify-phone/confirm", json={
            "phone": phone,
            "otp_code": otp_code,
        })
        self.assertEqual(confirm_res.status_code, 200)
        self.assertTrue(confirm_res.json()["phone_verified"])

        # 4. Check DB
        self.db.refresh(partner)
        self.assertTrue(partner.phone_verified)

    # 7. Meta error 131031 (Account locked) -> registration remains possible
    @patch("app.services.whatsapp_canonical_service.WhatsAppCanonicalService.send_meta_template_message")
    def test_07_meta_131031_locked_account_registration_remains_possible(self, mock_send):
        mock_send.return_value = {
            "success": False,
            "error_code": 131031,
            "error_message": "Business Account locked",
            "status": "failed"
        }
        phone = f"91006{int(time.time()) % 100000:05d}"
        self.created_partner_phones.append(phone)

        send_res = self.client.post("/api/v1/vgk/auth/signup/send-otp", json={"phone": phone})
        self.assertEqual(send_res.status_code, 200)
        self.assertFalse(send_res.json()["otp_sent"])

        # Registration succeeds
        reg_res = self.client.post("/api/v1/vgk/auth/signup", json={
            "partner_name": "Test 131031 Partner",
            "phone": phone,
            "password": "Password@123",
        })
        self.assertEqual(reg_res.status_code, 200)
        self.assertTrue(reg_res.json()["success"])

    # 8. Meta error 131047 (Re-engagement window) -> registration remains possible
    @patch("app.services.whatsapp_canonical_service.WhatsAppCanonicalService.send_meta_template_message")
    def test_08_meta_131047_reengagement_registration_remains_possible(self, mock_send):
        mock_send.return_value = {
            "success": False,
            "error_code": 131047,
            "error_message": "Re-engagement message",
            "status": "failed"
        }
        phone = f"91007{int(time.time()) % 100000:05d}"
        self.created_partner_phones.append(phone)

        send_res = self.client.post("/api/v1/vgk/auth/signup/send-otp", json={"phone": phone})
        self.assertEqual(send_res.status_code, 200)
        self.assertFalse(send_res.json()["otp_sent"])

        reg_res = self.client.post("/api/v1/vgk/auth/signup", json={
            "partner_name": "Test 131047 Partner",
            "phone": phone,
            "password": "Password@123",
        })
        self.assertEqual(reg_res.status_code, 200)
        self.assertTrue(reg_res.json()["success"])

    # 9. Meta provider inconsistency (NO_WAMID) -> registration remains possible
    @patch("app.services.whatsapp_canonical_service.WhatsAppCanonicalService.send_meta_template_message")
    def test_09_meta_no_wamid_inconsistency_registration_remains_possible(self, mock_send):
        mock_send.return_value = {
            "success": False,
            "error_code": "PROVIDER_INCONSISTENCY",
            "error_message": "Meta responded 200 but returned no message ID",
            "status": "failed"
        }
        phone = f"91008{int(time.time()) % 100000:05d}"
        self.created_partner_phones.append(phone)

        send_res = self.client.post("/api/v1/vgk/auth/signup/send-otp", json={"phone": phone})
        self.assertEqual(send_res.status_code, 200)
        self.assertFalse(send_res.json()["otp_sent"])

        reg_res = self.client.post("/api/v1/vgk/auth/signup", json={
            "partner_name": "Test NO_WAMID Partner",
            "phone": phone,
            "password": "Password@123",
        })
        self.assertEqual(reg_res.status_code, 200)
        self.assertTrue(reg_res.json()["success"])

    # 10. Frontend skip + backend registration -> succeeds with phone_verified=False
    def test_10_frontend_skip_backend_registration(self):
        phone = f"91009{int(time.time()) % 100000:05d}"
        self.created_partner_phones.append(phone)

        reg_payload = {
            "partner_name": "Frontend Skip Partner",
            "phone": phone,
            "password": "Password@123",
            "phone_verified_token": None
        }
        res = self.client.post("/api/v1/vgk/auth/signup", json=reg_payload)
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.json()["phone_verified"])

    # 11. Direct API request without OTP token -> follows optional rule (MNR User Registration)
    def test_11_direct_user_registration_without_otp_token(self):
        mobile = f"91010{int(time.time()) % 100000:05d}"
        self.created_user_mobiles.append(mobile)

        sponsor = self.db.query(User).first()
        sponsor_id = sponsor.id if sponsor else "MR10001"

        user_payload = {
            "name": "Direct Reg User",
            "mobile": mobile,
            "password": "Password@123",
            "sponsor_id": sponsor_id,
            "position": "Left",
            "first_name": "Direct",
            "last_name": "User"
        }
        res = self.client.post("/api/v1/users/register", json=user_payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["mobile_verified"], False)

        user = self.db.query(User).filter_by(phone_number=mobile).first()
        self.assertIsNotNone(user)
        self.assertFalse(user.mobile_verified)

    # 12. Mandatory validations (missing name, short password, duplicate checks) strictly enforced
    def test_12_mandatory_validations_strictly_enforced(self):
        phone = f"91011{int(time.time()) % 100000:05d}"
        self.created_partner_phones.append(phone)

        # 1. Missing / invalid partner name
        res = self.client.post("/api/v1/vgk/auth/signup", json={
            "partner_name": "",
            "phone": phone,
            "password": "Password@123",
        })
        self.assertIn(res.status_code, (400, 422))

        # 2. Short password (<6 chars)
        res = self.client.post("/api/v1/vgk/auth/signup", json={
            "partner_name": "Short Pass User",
            "phone": phone,
            "password": "123",
        })
        self.assertIn(res.status_code, (400, 422))

        # 3. Duplicate phone registration
        # First registration succeeds
        res1 = self.client.post("/api/v1/vgk/auth/signup", json={
            "partner_name": "Duplicate Test User 1",
            "phone": phone,
            "password": "Password@123",
        })
        self.assertEqual(res1.status_code, 200)

        # Second registration with same phone must fail
        res2 = self.client.post("/api/v1/vgk/auth/signup", json={
            "partner_name": "Duplicate Test User 2",
            "phone": phone,
            "password": "Password@123",
        })
        self.assertEqual(res2.status_code, 400)
        self.assertIn("already registered", res2.json()["detail"])


if __name__ == "__main__":
    unittest.main()
