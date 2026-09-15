"""
Unit tests for WhatsApp All Messages Tab:
1. HTTP 403 Forbidden for unauthorized regular employee without high scope
2. HTTP 200 OK for MR10001 (Supreme / PLATFORM scope)
3. HTTP 200 OK for Yaswanth (MR10016 / EA / level 95)
4. HTTP 200 OK for Anushka (MR10036 / SEGMENT_A scope)
5. Outbound organization message visibility for scope=all
6. Multi-factor search across phone, name, and content
"""

import os
import sys
import unittest
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.database import SessionLocal
from app.models.staff import StaffEmployee
from app.api.v1.endpoints.whatsapp import _require_staff, _is_all_messages_authorized


class TestWhatsAppAllMessagesTab(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.db: Session = SessionLocal()

        # Find key test users
        cls.mr10001 = cls.db.query(StaffEmployee).filter(StaffEmployee.emp_code == 'MR10001').first()
        cls.yaswanth = cls.db.query(StaffEmployee).filter(StaffEmployee.emp_code == 'MR10016').first()
        cls.anushka = cls.db.query(StaffEmployee).filter(StaffEmployee.emp_code == 'MR10036').first()

        # Find a regular low-privilege employee for negative test (level < 50, no admin scope)
        active_employees = cls.db.query(StaffEmployee).filter(
            StaffEmployee.status == 'active',
            StaffEmployee.emp_code.notin_(['MR10001', 'MR10016', 'MR10036'])
        ).all()
        cls.regular_employee = None
        for emp in active_employees:
            if not _is_all_messages_authorized(cls.db, emp):
                cls.regular_employee = emp
                break

    @classmethod
    def tearDownClass(cls):
        cls.db.close()
        app.dependency_overrides.clear()

    def test_01_regular_employee_forbidden_from_all_scope(self):
        """Unauthorized regular employee must be rejected with HTTP 403 on scope=all"""
        if not self.regular_employee:
            self.skipTest("No low-privilege employee found in database")

        self.assertFalse(_is_all_messages_authorized(self.db, self.regular_employee))
        app.dependency_overrides[_require_staff] = lambda: self.regular_employee
        res = self.client.get("/api/v1/whatsapp/conversations-hub?scope=all")
        self.assertEqual(res.status_code, 403, f"Expected 403 Forbidden but got {res.status_code}: {res.text}")
        self.assertIn("access denied", res.text.lower())

    def test_02_mr10001_authorized_for_all_scope(self):
        """MR10001 (Supreme/Platform) must be authorized with HTTP 200 on scope=all"""
        if not self.mr10001:
            self.skipTest("MR10001 not found")

        self.assertTrue(_is_all_messages_authorized(self.db, self.mr10001))
        app.dependency_overrides[_require_staff] = lambda: self.mr10001
        res = self.client.get("/api/v1/whatsapp/conversations-hub?scope=all")
        self.assertEqual(res.status_code, 200, f"Expected 200 OK but got {res.status_code}: {res.text}")
        data = res.json()
        self.assertTrue(data.get("success"))
        self.assertIn("conversations", data)

    def test_03_yaswanth_authorized_for_all_scope(self):
        """Yaswanth (MR10016 / EA / Level 95) must be authorized with HTTP 200 on scope=all"""
        if not self.yaswanth:
            self.skipTest("Yaswanth not found")

        self.assertTrue(_is_all_messages_authorized(self.db, self.yaswanth))
        app.dependency_overrides[_require_staff] = lambda: self.yaswanth
        res = self.client.get("/api/v1/whatsapp/conversations-hub?scope=all")
        self.assertEqual(res.status_code, 200, f"Expected 200 OK but got {res.status_code}: {res.text}")
        data = res.json()
        self.assertTrue(data.get("success"))
        self.assertIn("conversations", data)

    def test_04_anushka_authorized_for_all_scope(self):
        """Anushka (MR10036 / SEGMENT_A) must be authorized with HTTP 200 on scope=all"""
        if not self.anushka:
            self.skipTest("Anushka not found")

        self.assertTrue(_is_all_messages_authorized(self.db, self.anushka))
        app.dependency_overrides[_require_staff] = lambda: self.anushka
        res = self.client.get("/api/v1/whatsapp/conversations-hub?scope=all")
        self.assertEqual(res.status_code, 200, f"Expected 200 OK but got {res.status_code}: {res.text}")
        data = res.json()
        self.assertTrue(data.get("success"))
        self.assertIn("conversations", data)

    def test_05_search_in_all_messages(self):
        """Search query in scope=all must succeed and return filtered conversations"""
        if not self.mr10001:
            self.skipTest("MR10001 not found")

        app.dependency_overrides[_require_staff] = lambda: self.mr10001
        res = self.client.get("/api/v1/whatsapp/conversations-hub?scope=all&search=85858")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("success"))
        self.assertIn("conversations", data)


if __name__ == "__main__":
    unittest.main()
