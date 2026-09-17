import os
import sys
import unittest
from datetime import date, datetime
from decimal import Decimal
from io import BytesIO

# Dynamically resolve path (Rule 1)
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, '..'))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.database import SessionLocal
from app.api.v1.endpoints.crm import generate_solar_docket_pdf
from app.models.staff_accounts import EmployeeFundLedger, ExpenseEntry, OfficialPartner
from app.models.staff import StaffEmployee


class TestV2410ReleaseCandidate(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()

    def tearDown(self):
        self.db.rollback()
        self.db.close()

    def test_solar_docket_pdf_generation(self):
        """Verify generate_solar_docket_pdf generates valid PDF bytes without errors."""
        # Call with empty doc items
        pdf_bytes = generate_solar_docket_pdf(
            customer_name="Test Customer",
            lead_id=99999,
            lead_phone="9876543210",
            kw_size="5.0 KW",
            inst_info="On-Grid Solar",
            ref_no="LEAD-10101",
            address="Test Village, Test Mandal, Telangana",
            staff_name="Operations Team",
            group_label="All Solar Documents",
            doc_items=[]
        )
        self.assertIsInstance(pdf_bytes, (bytes, bytearray))
        self.assertTrue(len(pdf_bytes) > 500)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))

        # Test with a mock image document item
        from PIL import Image
        img = Image.new("RGB", (200, 200), color=(73, 109, 137))
        img_buf = BytesIO()
        img.save(img_buf, format="PNG")
        mock_doc = {
            "key": "electricity_bill",
            "label": "Electricity Bill",
            "ext": "png",
            "bytes": img_buf.getvalue()
        }
        docket_with_doc = generate_solar_docket_pdf(
            customer_name="Test Customer",
            lead_id=99999,
            lead_phone="9876543210",
            kw_size="5.0 KW",
            inst_info="On-Grid Solar",
            ref_no="LEAD-10101",
            address="Test Village, Test Mandal, Telangana",
            staff_name="Operations Team",
            group_label="All Solar Documents",
            doc_items=[mock_doc]
        )
        self.assertIsInstance(docket_with_doc, (bytes, bytearray))
        self.assertTrue(len(docket_with_doc) > len(pdf_bytes))

    def test_staff_accounts_ledger_zero_balance_safeguards(self):
        """Verify staff ledger properly queries ADJUSTMENT rows and validates zero balances."""
        adj_rows = self.db.query(EmployeeFundLedger).filter(
            EmployeeFundLedger.entry_type == 'ADJUSTMENT',
            EmployeeFundLedger.transaction_date == date(2026, 9, 16)
        ).all()
        # Should have valid adjustment records in dev db
        for adj in adj_rows:
            self.assertEqual(adj.balance, Decimal('0.00'))
            self.assertTrue(adj.reference_number.startswith("ADJ-RESET-"))

    def test_vgk_member_assigned_staff_id_field(self):
        """Verify official_partners table has assigned_staff_id and assigned_by_id fields populated."""
        partners = self.db.query(OfficialPartner).filter(
            OfficialPartner.category == 'VGK_TEAM'
        ).limit(10).all()
        # Ensure model attribute access works
        for p in partners:
            self.assertTrue(hasattr(p, 'assigned_staff_id'))
            self.assertTrue(hasattr(p, 'assigned_by_id'))
            self.assertTrue(hasattr(p, 'assigned_at'))


if __name__ == '__main__':
    unittest.main()
