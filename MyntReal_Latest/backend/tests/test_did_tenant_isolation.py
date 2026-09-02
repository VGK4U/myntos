"""
Unit & Integration Test Suite — Telephony DID Multi-Tenant Isolation
Tests:
1. Mapped DID in telephony_did_mappings resolves to the exact tenant company_id
2. Mapped DID in telephony_call_flows resolves to the exact tenant company_id
3. Inactive DID mapping (is_active=False) is ignored and returns None
4. Unmapped DID returns None from _resolve_company_from_did (no hardcoded company_id=1 fallback)
5. Unmapped DID inbound call receives quarantine message and does NOT execute any tenant's call flow
6. Mapped DID inbound call executes the correct tenant's published flow
Created: Sep 2026
"""

import unittest
import time
import uuid
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.operator_calls import TelephonyDIDMapping
from app.models.telephony_call_flow import (
    TelephonyCallFlow, TelephonyCallFlowVersion, TelephonyFlowExecutionLog
)
from app.models.voip_call_session import VoIPCallSession
from app.services.telephony.flow_interpreter import CallFlowInterpreter


class TestDIDTenantIsolation(unittest.TestCase):
    """
    Test Suite verifying strict multi-tenant isolation in DID resolution
    """

    def setUp(self):
        self.db: Session = SessionLocal()
        self.test_mapping_ids = []
        self.test_flow_ids = []
        self.test_session_ids = []

        # Unique numeric test DIDs
        ts = int(time.time() * 1000)
        self.mapped_did_comp4 = f"+9180{(ts % 10000000):08d}"
        self.mapped_did_comp1 = f"+9180{((ts + 100) % 10000000):08d}"
        self.unmapped_did = f"+9199{((ts + 200) % 10000000):08d}"

        # Create Company 4 DID mapping
        m1 = TelephonyDIDMapping(
            did_number=self.mapped_did_comp4,
            company_id=4,
            provider="plivo",
            is_active=True
        )
        self.db.add(m1)
        self.db.commit()
        self.test_mapping_ids.append(m1.id)

        # Create Company 1 Published Call Flow (to verify unmapped calls NEVER route to it)
        f1 = TelephonyCallFlow(
            company_id=1,
            name="Company 1 Secret Flow",
            status="published",
            did_number=self.mapped_did_comp1
        )
        self.db.add(f1)
        self.db.commit()
        self.test_flow_ids.append(f1.id)

        v1 = TelephonyCallFlowVersion(
            flow_id=f1.id,
            company_id=1,
            version_number=1,
            status="published",
            flow_data={
                "nodes": [
                    {"id": "t1", "type": "trigger_did", "name": "Trigger"},
                    {"id": "s1", "type": "speak_prompt", "name": "Company 1 Prompt", "config": {"text": "Secret Company One Greeting"}}
                ],
                "edges": [
                    {"source": "t1", "target": "s1", "condition": "always"}
                ]
            }
        )
        self.db.add(v1)
        self.db.commit()
        f1.current_published_version_id = v1.id
        self.db.commit()

    def tearDown(self):
        try:
            for mid in self.test_mapping_ids:
                self.db.query(TelephonyDIDMapping).filter(TelephonyDIDMapping.id == mid).delete()
            for fid in self.test_flow_ids:
                self.db.query(TelephonyFlowExecutionLog).filter(TelephonyFlowExecutionLog.call_flow_id == fid).delete()
                self.db.query(TelephonyCallFlowVersion).filter(TelephonyCallFlowVersion.flow_id == fid).delete()
                self.db.query(TelephonyCallFlow).filter(TelephonyCallFlow.id == fid).delete()
            for sid in self.test_session_ids:
                self.db.query(VoIPCallSession).filter(VoIPCallSession.call_session_id == sid).delete()
            self.db.commit()
        except Exception:
            self.db.rollback()
        finally:
            self.db.close()

    # 1. Mapped DID in telephony_did_mappings resolves to exact company_id
    def test_01_mapped_did_in_mappings_resolves_correct_company(self):
        resolved_cid = CallFlowInterpreter._resolve_company_from_did(
            db=self.db,
            did_number=self.mapped_did_comp4
        )
        self.assertEqual(resolved_cid, 4)

    # 2. Mapped DID in telephony_call_flows resolves to exact company_id
    def test_02_mapped_did_in_call_flows_resolves_correct_company(self):
        resolved_cid = CallFlowInterpreter._resolve_company_from_did(
            db=self.db,
            did_number=self.mapped_did_comp1
        )
        self.assertEqual(resolved_cid, 1)

    # 3. Inactive DID mapping is ignored and returns None
    def test_03_inactive_did_mapping_returns_none(self):
        inactive_did = f"+918088{uuid.uuid4().hex[:6]}"
        m_inactive = TelephonyDIDMapping(
            did_number=inactive_did,
            company_id=2,
            provider="plivo",
            is_active=False
        )
        self.db.add(m_inactive)
        self.db.commit()
        self.test_mapping_ids.append(m_inactive.id)

        resolved_cid = CallFlowInterpreter._resolve_company_from_did(
            db=self.db,
            did_number=inactive_did
        )
        self.assertIsNone(resolved_cid)

    # 4. Unmapped DID returns None (No hardcoded fallback to company 1)
    def test_04_unmapped_did_returns_none(self):
        resolved_cid = CallFlowInterpreter._resolve_company_from_did(
            db=self.db,
            did_number=self.unmapped_did
        )
        self.assertIsNone(resolved_cid)

    # 5. Unmapped DID inbound call receives quarantine message and does NOT execute Company 1's flow
    def test_05_unmapped_did_inbound_call_quarantined(self):
        xml_resp = CallFlowInterpreter.handle_inbound_call(
            db=self.db,
            caller_phone="+919876543210",
            called_did=self.unmapped_did,
            provider_call_id="call_unmapped_test_123",
            base_api_url="https://api.myntreal.com"
        )

        # Must return unconfigured message and Hangup
        self.assertIn("This number is not currently configured", xml_resp)
        self.assertIn("<Hangup />", xml_resp)

        # Must NOT execute Company 1's secret flow
        self.assertNotIn("Secret Company One Greeting", xml_resp)

    # 6. Mapped DID inbound call executes the correct tenant's published flow
    def test_06_mapped_did_inbound_call_executes_correct_flow(self):
        xml_resp = CallFlowInterpreter.handle_inbound_call(
            db=self.db,
            caller_phone="+919876543210",
            called_did=self.mapped_did_comp1,
            provider_call_id="call_mapped_comp1_test",
            base_api_url="https://api.myntreal.com"
        )

        # Should execute Company 1's flow
        self.assertIn("Secret Company One Greeting", xml_resp)


if __name__ == '__main__':
    unittest.main()
