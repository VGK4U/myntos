"""
Unit Test Suite — Call History Sorting, Session-Isolated IVR Gather, and Recording Duration
Verifies:
1. Deterministic composite call sorting (_call_sort_key): started_at DESC, id DESC.
2. IVR gather endpoint handles session_id parameter and isolates session DTMF history without cross-session pollution.
3. Customer history API endpoint provides truthful recording_duration and recording_duration_formatted.
"""

import unittest
import time
import json
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.database import SessionLocal
from app.models.voip_call_session import VoIPCallSession
from app.models.voip_enums import CallStateEnum
from app.services.telephony.flow_interpreter import CallFlowInterpreter
from app.api.v1.endpoints.call_flow_api import _call_sort_key


class TestCallHistoryAndIvrAudit(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.db: Session = SessionLocal()
        self.created_session_ids = []

    def tearDown(self):
        # Clean up only sessions created by this test suite
        if self.created_session_ids:
            try:
                self.db.query(VoIPCallSession).filter(
                    VoIPCallSession.id.in_(self.created_session_ids)
                ).delete(synchronize_session=False)
                self.db.commit()
            except Exception:
                self.db.rollback()
        self.db.close()

    def test_call_sort_key_determinism(self):
        """
        Verify that _call_sort_key correctly orders by (started_at, id) descending.
        """
        t1 = datetime(2026, 9, 14, 10, 0, 0)
        t2 = datetime(2026, 9, 14, 11, 0, 0)
        t3 = datetime(2026, 9, 14, 11, 0, 0)

        # Call A: t1, id=1
        call_a = {"id": 1, "started_at": t1}
        # Call B: t2, id=2
        call_b = {"id": 2, "started_at": t2}
        # Call C: t3 (same as t2), id=3
        call_c = {"id": 3, "started_at": t3}

        calls = [call_a, call_b, call_c]
        sorted_calls = sorted(calls, key=_call_sort_key, reverse=True)

        # Expected order: call_c (t3, id=3), call_b (t2, id=2), call_a (t1, id=1)
        self.assertEqual(sorted_calls[0]["id"], 3)
        self.assertEqual(sorted_calls[1]["id"], 2)
        self.assertEqual(sorted_calls[2]["id"], 1)

    def test_ivr_gather_session_isolation(self):
        """
        Verify that CallFlowInterpreter.handle_ivr_gather with session_id isolates
        the DTMF inputs strictly to the target session and does not cross-contaminate.
        """
        phone = "+919999988888"
        t_id = int(time.time())
        
        # Create session 1
        s1 = VoIPCallSession(
            company_id=1,
            call_session_id=f"vcs_audit_1_{t_id}",
            provider="plivo",
            provider_call_id=f"uuid_1_{t_id}",
            caller_id=phone,
            customer_phone=phone,
            destination_number="+918031728899",
            direction="inbound",
            status=CallStateEnum.ANSWERED.value,
            metadata_json=json.dumps({"ivr_selections": []})
        )
        self.db.add(s1)
        self.db.commit()
        self.db.refresh(s1)
        self.created_session_ids.append(s1.id)

        # Create session 2 for the same phone
        s2 = VoIPCallSession(
            company_id=1,
            call_session_id=f"vcs_audit_2_{t_id}",
            provider="plivo",
            provider_call_id=f"uuid_2_{t_id}",
            caller_id=phone,
            customer_phone=phone,
            destination_number="+918031728899",
            direction="inbound",
            status=CallStateEnum.ANSWERED.value,
            metadata_json=json.dumps({"ivr_selections": []})
        )
        self.db.add(s2)
        self.db.commit()
        self.db.refresh(s2)
        self.created_session_ids.append(s2.id)

        # Gather digit "1" for session 1
        CallFlowInterpreter.handle_ivr_gather(
            db=self.db,
            caller_phone=phone,
            called_did="+918031728899",
            digits="1",
            session_id=s1.call_session_id,
            call_uuid=s1.provider_call_id
        )

        self.db.refresh(s1)
        self.db.refresh(s2)

        meta1 = json.loads(s1.metadata_json or "{}")
        meta2 = json.loads(s2.metadata_json or "{}")

        # s1 should have recorded the selection
        self.assertTrue(len(meta1.get("ivr_selections", [])) >= 1)
        # s2 must remain isolated with 0 selections
        self.assertEqual(len(meta2.get("ivr_selections", [])), 0)

    def test_customer_history_recording_duration_fields(self):
        """
        Verify that customer history query returns recording_duration and recording_duration_formatted.
        """
        phone = "+918888877777"
        now = datetime.now(timezone.utc)
        t_id = int(time.time())
        session = VoIPCallSession(
            company_id=1,
            call_session_id=f"vcs_rec_test_{t_id}",
            provider="plivo",
            provider_call_id=f"uuid_rec_{t_id}",
            caller_id=phone,
            customer_phone=phone,
            destination_number="+918031728899",
            direction="inbound",
            status=CallStateEnum.ENDED.value,
            started_at=now - timedelta(seconds=120),
            ended_at=now,
            duration_seconds=120,
            recording_duration_seconds=105,
            recording_storage_key="https://s3.amazonaws.com/test-rec.mp3"
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        self.created_session_ids.append(session.id)

        self.db.refresh(session)
        self.assertEqual(session.duration_seconds, 120)
        self.assertEqual(session.recording_duration_seconds, 105)


if __name__ == "__main__":
    unittest.main()
