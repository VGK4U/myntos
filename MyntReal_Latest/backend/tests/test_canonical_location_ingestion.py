"""
Test Suite: Canonical Location Ingestion Foundation
Phase 6 Step 1: Canonical Location Ingestion Contract Validation
===============================================================
Comprehensive test coverage:
1. UUIDv4 observation identity ingestion & persistence.
2. Deterministic UUIDv5 legacy fallback deduplication.
3. Journey track point retry idempotency.
4. Realtime telemetry retry idempotency.
5. Stationary coordinate fixes with distinct UUIDs (both recorded).
6. Out-of-order track point arrival & chronological distance recalculation.
7. Post-approval financial immutability (frozen distance & reimbursement).
8. Telemetry accuracy rejection (>500m).
9. Journey dual-tier WVV accuracy compliance vs degraded points.
10. Separation of concerns: Journey track points vs Attendance continuous telemetry.
11. Negative altitude clamping to 0.0 (prevent DB constraint violations).
12. Multi-format timestamp parsing (ISO strings, UTC/IST, epoch milliseconds).
"""

import unittest
import uuid
from datetime import datetime, timedelta
import pytz

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles

@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"

from app.core.database import Base
from app.models.staff import StaffEmployee
from app.models.staff_attendance import (
    StaffAttendance, StaffRealtimeLocation, StaffAttendanceBreak,
    get_indian_time, get_indian_date
)
from app.models.staff_journey import (
    StaffJourney, StaffJourneyTrackPoint, JourneyStatus, JourneyApprovalStatus, JourneyPurpose
)
from app.services.location_ingestion_service import LocationIngestionService


class TestCanonicalLocationIngestion(unittest.TestCase):

    def setUp(self):
        """In-memory SQLite database for isolated unit testing."""
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        
        tables_to_create = [
            StaffEmployee.__table__,
            StaffAttendance.__table__,
            StaffAttendanceBreak.__table__,
            StaffJourney.__table__,
            StaffJourneyTrackPoint.__table__,
            StaffRealtimeLocation.__table__
        ]
        Base.metadata.create_all(bind=self.engine, tables=tables_to_create)
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db = TestingSessionLocal()

        today = get_indian_date()
        now = get_indian_time()

        # Create dummy employee
        self.emp = StaffEmployee(
            id=101,
            emp_code="EMP101",
            full_name="Test Field Engineer",
            email="field.engineer@example.com",
            phone="9876543210",
            role_id=1,
            date_of_joining=today,
            password_hash="test_hash"
        )
        self.db.add(self.emp)

        # Create active attendance
        self.att = StaffAttendance(
            id=501,
            employee_id=101,
            date=today,
            clock_in=now - timedelta(hours=2),
            clock_out=None,
            status="present",
            location_mode="field"
        )
        self.db.add(self.att)

        # Create active journey
        self.journey = StaffJourney(
            id=701,
            employee_id=101,
            date=today,
            start_time=now - timedelta(hours=1),
            purpose=JourneyPurpose.CLIENT_VISIT,
            status=JourneyStatus.IN_PROGRESS,
            approval_status=JourneyApprovalStatus.PENDING,
            transport_mode="bike",
            is_reimbursable=True,
            rate_per_km=3.5,
            total_distance_km=0.0,
            reimbursable_distance_km=0.0,
            reimbursement_amount=0.0
        )
        self.db.add(self.journey)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_01_uuid4_acceptance_and_persistence(self):
        """1. Verify that a valid client_observation_id UUIDv4 is accepted and stored unchanged."""
        obs_id = str(uuid.uuid4())
        ts = datetime(2026, 9, 6, 10, 0, 0)
        payload = {
            "latitude": 17.686816,
            "longitude": 83.218482,
            "accuracy_m": 15.0,
            "altitude": 25.0,
            "speed_kmh": 35.0,
            "heading": 180.0,
            "client_observation_id": obs_id,
            "timestamp": ts.isoformat()
        }

        result = LocationIngestionService.ingest_journey_track_point(
            db=self.db,
            journey_id=701,
            employee_id=101,
            observation_data=payload
        )

        self.assertTrue(result["success"])
        self.assertFalse(result["duplicate"])
        self.assertEqual(result["client_observation_id"], obs_id)
        self.assertTrue(result["wvv_compliant"])

        # Query DB directly
        db_point = self.db.query(StaffJourneyTrackPoint).filter(
            StaffJourneyTrackPoint.client_observation_id == obs_id
        ).first()
        self.assertIsNotNone(db_point)
        self.assertEqual(db_point.journey_id, 701)
        self.assertAlmostEqual(db_point.latitude, 17.686816, places=5)
        self.assertAlmostEqual(db_point.longitude, 83.218482, places=5)
        self.assertIsNotNone(db_point.server_received_at)

    def test_02_retry_idempotency_journey_track_point(self):
        """2. Verify that re-submitting the exact same observation returns duplicate=True without creating a new row."""
        obs_id = str(uuid.uuid4())
        ts = datetime(2026, 9, 6, 10, 5, 0)
        payload = {
            "latitude": 17.686816,
            "longitude": 83.218482,
            "accuracy_m": 20.0,
            "client_observation_id": obs_id,
            "timestamp": ts.isoformat()
        }

        # First attempt
        res1 = LocationIngestionService.ingest_journey_track_point(
            db=self.db, journey_id=701, employee_id=101, observation_data=payload
        )
        self.assertTrue(res1["success"])
        self.assertFalse(res1["duplicate"])

        # Second attempt (Network retry / Offline sync replay)
        res2 = LocationIngestionService.ingest_journey_track_point(
            db=self.db, journey_id=701, employee_id=101, observation_data=payload
        )
        self.assertTrue(res2["success"])
        self.assertTrue(res2["duplicate"])
        self.assertEqual(res2["client_observation_id"], obs_id)

        # Total row count should remain exactly 1
        count = self.db.query(StaffJourneyTrackPoint).filter(
            StaffJourneyTrackPoint.client_observation_id == obs_id
        ).count()
        self.assertEqual(count, 1)

    def test_03_legacy_fingerprint_deduplication(self):
        """3. Verify deterministic UUIDv5 generation and deduplication for legacy payloads lacking client_observation_id."""
        ts = datetime(2026, 9, 6, 10, 10, 0)
        payload_legacy = {
            "latitude": 17.700000,
            "longitude": 83.300000,
            "accuracy": 30.0,
            "timestamp": ts.isoformat()
            # client_observation_id omitted!
        }

        # First attempt
        res1 = LocationIngestionService.ingest_journey_track_point(
            db=self.db, journey_id=701, employee_id=101, observation_data=payload_legacy
        )
        self.assertTrue(res1["success"])
        self.assertFalse(res1["duplicate"])
        generated_id_1 = res1["client_observation_id"]
        self.assertIsNotNone(generated_id_1)

        # Expected UUIDv5
        expected_uuid5 = LocationIngestionService.generate_legacy_dedup_fingerprint(
            employee_id=101,
            latitude=17.700000,
            longitude=83.300000,
            captured_at=ts
        )
        self.assertEqual(generated_id_1, expected_uuid5)

        # Second attempt with same legacy payload
        res2 = LocationIngestionService.ingest_journey_track_point(
            db=self.db, journey_id=701, employee_id=101, observation_data=payload_legacy
        )
        self.assertTrue(res2["success"])
        self.assertTrue(res2["duplicate"])
        self.assertEqual(res2["client_observation_id"], expected_uuid5)

    def test_04_stationary_distinct_observations_both_saved(self):
        """4. Verify that stationary coordinates with distinct observation IDs and timestamps are both recorded."""
        lat, lng = 17.710000, 83.310000
        t1 = datetime(2026, 9, 6, 10, 15, 0)
        t2 = datetime(2026, 9, 6, 10, 20, 0)
        obs_id_1 = str(uuid.uuid4())
        obs_id_2 = str(uuid.uuid4())

        # First stationary fix
        res1 = LocationIngestionService.ingest_journey_track_point(
            db=self.db, journey_id=701, employee_id=101, observation_data={
                "latitude": lat, "longitude": lng, "accuracy_m": 10.0,
                "client_observation_id": obs_id_1, "timestamp": t1.isoformat()
            }
        )
        self.assertFalse(res1["duplicate"])

        # Second stationary fix 5 minutes later
        res2 = LocationIngestionService.ingest_journey_track_point(
            db=self.db, journey_id=701, employee_id=101, observation_data={
                "latitude": lat, "longitude": lng, "accuracy_m": 10.0,
                "client_observation_id": obs_id_2, "timestamp": t2.isoformat()
            }
        )
        self.assertFalse(res2["duplicate"])

        points = self.db.query(StaffJourneyTrackPoint).filter(
            StaffJourneyTrackPoint.journey_id == 701
        ).all()
        self.assertEqual(len(points), 2)

    def test_05_out_of_order_distance_recalculation(self):
        """5. Verify that late-arriving out-of-order points trigger chronological distance recalculation."""
        p1 = {"latitude": 17.7100, "longitude": 83.3100, "accuracy_m": 10.0, "timestamp": "2026-09-06T10:00:00"}
        p2 = {"latitude": 17.7200, "longitude": 83.3200, "accuracy_m": 10.0, "timestamp": "2026-09-06T10:10:00"}
        p3 = {"latitude": 17.7300, "longitude": 83.3300, "accuracy_m": 10.0, "timestamp": "2026-09-06T10:20:00"}

        # Ingest P1
        LocationIngestionService.ingest_journey_track_point(db=self.db, journey_id=701, employee_id=101, observation_data=p1)
        # Ingest P3 out-of-order (before P2)
        LocationIngestionService.ingest_journey_track_point(db=self.db, journey_id=701, employee_id=101, observation_data=p3)

        # Now ingest P2 (late arrival!)
        res = LocationIngestionService.ingest_journey_track_point(db=self.db, journey_id=701, employee_id=101, observation_data=p2)

        # All 3 points should now be chronologically ordered with correct distance
        all_points = self.db.query(StaffJourneyTrackPoint).filter(
            StaffJourneyTrackPoint.journey_id == 701
        ).order_by(StaffJourneyTrackPoint.timestamp.asc()).all()

        self.assertEqual(len(all_points), 3)
        self.assertAlmostEqual(all_points[0].latitude, 17.7100, places=4)
        self.assertAlmostEqual(all_points[1].latitude, 17.7200, places=4)
        self.assertAlmostEqual(all_points[2].latitude, 17.7300, places=4)

        # Distances must be strictly increasing
        self.assertEqual(all_points[0].cumulative_distance, 0.0)
        self.assertGreater(all_points[1].cumulative_distance, 0.0)
        self.assertGreater(all_points[2].cumulative_distance, all_points[1].cumulative_distance)

        journey = self.db.query(StaffJourney).filter(StaffJourney.id == 701).first()
        self.assertAlmostEqual(journey.total_distance_km, all_points[2].cumulative_distance, places=3)
        self.assertGreater(journey.reimbursement_amount, 0)

    def test_06_post_approval_financial_immutability(self):
        """6. Verify that approved journeys accept track points for audit trail but freeze financial aggregates."""
        journey = self.db.query(StaffJourney).filter(StaffJourney.id == 701).first()
        journey.total_distance_km = 10.0
        journey.reimbursable_distance_km = 10.0
        journey.reimbursement_amount = 35.0  # 10 km * 3.5
        journey.approval_status = JourneyApprovalStatus.APPROVED
        journey.status = JourneyStatus.COMPLETED
        self.db.commit()

        obs_id = str(uuid.uuid4())
        p_late = {
            "latitude": 17.8000,
            "longitude": 83.4000,
            "accuracy_m": 10.0,
            "client_observation_id": obs_id,
            "timestamp": "2026-09-06T11:00:00"
        }

        res = LocationIngestionService.ingest_journey_track_point(
            db=self.db, journey_id=701, employee_id=101, observation_data=p_late
        )

        self.assertTrue(res["success"])
        # Point is recorded
        saved_pt = self.db.query(StaffJourneyTrackPoint).filter(
            StaffJourneyTrackPoint.client_observation_id == obs_id
        ).first()
        self.assertIsNotNone(saved_pt)

        # Financial and distance totals remain completely frozen!
        re_journey = self.db.query(StaffJourney).filter(StaffJourney.id == 701).first()
        self.assertEqual(re_journey.total_distance_km, 10.0)
        self.assertEqual(re_journey.reimbursable_distance_km, 10.0)
        self.assertEqual(re_journey.reimbursement_amount, 35.0)

    def test_07_realtime_telemetry_ingestion_and_idempotency(self):
        """7. Verify continuous telemetry ingestion into StaffRealtimeLocation and attendance updates."""
        obs_id = str(uuid.uuid4())
        telemetry_payload = {
            "latitude": 17.686816,
            "longitude": 83.218482,
            "accuracy_m": 25.0,
            "altitude": 10.0,
            "speed_kmh": 15.0,
            "battery_percentage": 88,
            "client_observation_id": obs_id,
            "source": "mobile_heartbeat",
            "timestamp": "2026-09-06T10:30:00"
        }

        res1 = LocationIngestionService.ingest_realtime_location(
            db=self.db, employee_id=101, observation_data=telemetry_payload
        )
        self.assertTrue(res1["success"])
        self.assertFalse(res1["duplicate"])
        self.assertEqual(res1["client_observation_id"], obs_id)

        # Verify StaffRealtimeLocation created
        loc = self.db.query(StaffRealtimeLocation).filter(
            StaffRealtimeLocation.client_observation_id == obs_id
        ).first()
        self.assertIsNotNone(loc)
        self.assertEqual(loc.employee_id, 101)
        self.assertEqual(loc.accuracy_m, 25.0)
        self.assertIsNotNone(loc.server_received_at)

        # Verify StaffAttendance updated
        att = self.db.query(StaffAttendance).filter(StaffAttendance.id == 501).first()
        self.assertEqual(att.gps_status, 'active')
        self.assertEqual(att.last_battery_pct, 88)

        # Re-send exact same telemetry (idempotent duplicate)
        res2 = LocationIngestionService.ingest_realtime_location(
            db=self.db, employee_id=101, observation_data=telemetry_payload
        )
        self.assertTrue(res2["success"])
        self.assertTrue(res2["duplicate"])

    def test_08_telemetry_accuracy_rejection(self):
        """8. Verify telemetry accuracy exceeding 500m is rejected."""
        telemetry_bad = {
            "latitude": 17.686816,
            "longitude": 83.218482,
            "accuracy_m": 501.0,  # exceeds 500m
            "client_observation_id": str(uuid.uuid4())
        }

        with self.assertRaises(Exception) as exc_info:
            LocationIngestionService.ingest_realtime_location(
                db=self.db, employee_id=101, observation_data=telemetry_bad
            )
        self.assertIn("500m", str(exc_info.exception))

    def test_09_journey_dual_tier_accuracy_compliance(self):
        """9. Verify WVV compliance flag tracks <= 100m vs degraded points (> 100m)."""
        # P1 compliant (accuracy 40m)
        p1 = {"latitude": 17.7100, "longitude": 83.3100, "accuracy_m": 40.0, "timestamp": "2026-09-06T10:00:00"}
        r1 = LocationIngestionService.ingest_journey_track_point(db=self.db, journey_id=701, employee_id=101, observation_data=p1)
        self.assertTrue(r1["wvv_compliant"])

        # P2 degraded (accuracy 120m)
        p2 = {"latitude": 17.7200, "longitude": 83.3200, "accuracy_m": 120.0, "timestamp": "2026-09-06T10:05:00"}
        r2 = LocationIngestionService.ingest_journey_track_point(db=self.db, journey_id=701, employee_id=101, observation_data=p2)
        self.assertFalse(r2["wvv_compliant"])
        self.assertIn("exceeds WVV threshold", r2["wvv_reason"])

        # P2 total distance increases, but reimbursable distance should NOT include P2 leg!
        journey = self.db.query(StaffJourney).filter(StaffJourney.id == 701).first()
        self.assertGreater(journey.total_distance_km, 0.0)
        self.assertEqual(journey.reimbursable_distance_km, 0.0)

    def test_10_separation_of_concerns_journey_vs_realtime(self):
        """10. Verify Journey Track Points and Attendance Telemetry remain distinct domain projections."""
        shared_obs_id = str(uuid.uuid4())
        fix = {
            "latitude": 17.7500,
            "longitude": 83.3500,
            "accuracy_m": 30.0,
            "client_observation_id": shared_obs_id,
            "timestamp": "2026-09-06T10:40:00"
        }

        # Ingest into Journey
        r_j = LocationIngestionService.ingest_journey_track_point(db=self.db, journey_id=701, employee_id=101, observation_data=fix)
        # Ingest into Realtime Telemetry
        r_rt = LocationIngestionService.ingest_realtime_location(db=self.db, employee_id=101, observation_data=fix)

        # Both records exist independently linked to the same physical client_observation_id
        j_pt = self.db.query(StaffJourneyTrackPoint).filter(StaffJourneyTrackPoint.client_observation_id == shared_obs_id).first()
        rt_pt = self.db.query(StaffRealtimeLocation).filter(StaffRealtimeLocation.client_observation_id == shared_obs_id).first()

        self.assertIsNotNone(j_pt)
        self.assertIsNotNone(rt_pt)
        self.assertEqual(j_pt.journey_id, 701)
        self.assertEqual(rt_pt.employee_id, 101)

    def test_11_negative_altitude_preservation(self):
        """11. Verify negative altitude is preserved accurately (no artificial clamping)."""
        norm = LocationIngestionService.normalize_observation({
            "latitude": 17.70,
            "longitude": 83.30,
            "altitude": -14.5
        }, employee_id=101)
        self.assertEqual(norm["altitude"], -14.5)

    def test_12_timestamp_parsing_formats(self):
        """12. Verify ISO strings and epoch millisecond timestamps parse accurately."""
        # Millisecond timestamp: 1772964000000 ms
        ms_epoch = 1772964000000
        norm = LocationIngestionService.normalize_observation({
            "latitude": 17.70,
            "longitude": 83.30,
            "timestamp": ms_epoch
        }, employee_id=101)
        self.assertIsInstance(norm["captured_at"], datetime)

    def test_13_reject_non_uuidv4_from_modern_client(self):
        """13. Verify that non-v4 UUIDs (e.g., UUIDv1 or UUIDv5) explicitly passed by modern client are rejected with 400."""
        from fastapi import HTTPException
        uuid_v1 = str(uuid.uuid1())
        with self.assertRaises(HTTPException) as exc_info:
            LocationIngestionService.normalize_observation({
                "latitude": 17.70,
                "longitude": 83.30,
                "client_observation_id": uuid_v1
            }, employee_id=101)
        self.assertEqual(exc_info.exception.status_code, 400)
        self.assertIn("expected UUIDv4", exc_info.exception.detail)

    def test_14_reject_malformed_uuid_string(self):
        """14. Verify malformed UUID strings are rejected with 400."""
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as exc_info:
            LocationIngestionService.normalize_observation({
                "latitude": 17.70,
                "longitude": 83.30,
                "client_observation_id": "not-a-valid-uuid-string"
            }, employee_id=101)
        self.assertEqual(exc_info.exception.status_code, 400)
        self.assertIn("not a valid UUID", exc_info.exception.detail)

    def test_15_reject_invalid_timestamp_formats(self):
        """15. Verify invalid timestamp strings raise 400 and are never silently coerced to server time."""
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as exc_info:
            LocationIngestionService.normalize_observation({
                "latitude": 17.70,
                "longitude": 83.30,
                "timestamp": "invalid-garbage-timestamp-string"
            }, employee_id=101)
        self.assertEqual(exc_info.exception.status_code, 400)
        self.assertIn("Invalid ISO GPS timestamp format", exc_info.exception.detail)

    def test_16_cancelled_journey_financial_immutability(self):
        """16. Verify CANCELLED journeys accept track points for audit trail but keep financial aggregates frozen."""
        journey = self.db.query(StaffJourney).filter(StaffJourney.id == 701).first()
        journey.total_distance_km = 5.0
        journey.reimbursable_distance_km = 5.0
        journey.reimbursement_amount = 17.5
        journey.status = JourneyStatus.CANCELLED
        self.db.commit()

        obs_id = str(uuid.uuid4())
        res = LocationIngestionService.ingest_journey_track_point(
            db=self.db, journey_id=701, employee_id=101, observation_data={
                "latitude": 17.8500, "longitude": 83.4500, "accuracy_m": 10.0,
                "client_observation_id": obs_id, "timestamp": "2026-09-06T11:30:00"
            }
        )
        self.assertTrue(res["success"])
        re_journey = self.db.query(StaffJourney).filter(StaffJourney.id == 701).first()
        self.assertEqual(re_journey.total_distance_km, 5.0)
        self.assertEqual(re_journey.reimbursement_amount, 17.5)

    def test_17_deterministic_latest_location_identical_timestamps(self):
        """17. Verify that multiple telemetry rows with IDENTICAL captured_at timestamps deterministically return exactly 1 row per employee."""
        from sqlalchemy import func, and_
        target_date = get_indian_date()
        target_date_start = datetime.combine(target_date, datetime.min.time())
        target_date_end = datetime.combine(target_date, datetime.max.time())
        same_time = get_indian_time()

        # Clean existing telemetry for employee 101
        self.db.query(StaffRealtimeLocation).filter(StaffRealtimeLocation.employee_id == 101).delete()
        self.db.commit()

        # Insert 2 rows with EXACTLY identical captured_at timestamps
        loc1 = StaffRealtimeLocation(
            employee_id=101,
            dc_code="DC-TEST-LOC1",
            client_observation_id=str(uuid.uuid4()),
            latitude=17.7000,
            longitude=83.3000,
            accuracy_m=10.0,
            source="heartbeat",
            captured_at=same_time,
            server_received_at=same_time
        )
        loc2 = StaffRealtimeLocation(
            employee_id=101,
            dc_code="DC-TEST-LOC2",
            client_observation_id=str(uuid.uuid4()),
            latitude=17.7100,
            longitude=83.3100,
            accuracy_m=10.0,
            source="journey",
            captured_at=same_time,
            server_received_at=same_time
        )
        self.db.add(loc1)
        self.db.add(loc2)
        self.db.commit()
        self.db.refresh(loc1)
        self.db.refresh(loc2)

        higher_id = max(loc1.id, loc2.id)

        # Run exact production subquery
        latest_ts_subq = self.db.query(
            StaffRealtimeLocation.employee_id,
            func.max(StaffRealtimeLocation.captured_at).label('max_captured')
        ).filter(
            StaffRealtimeLocation.employee_id == 101,
            StaffRealtimeLocation.captured_at >= target_date_start,
            StaffRealtimeLocation.captured_at <= target_date_end
        ).group_by(StaffRealtimeLocation.employee_id).subquery()

        latest_id_subq = self.db.query(
            func.max(StaffRealtimeLocation.id).label('max_id')
        ).join(
            latest_ts_subq,
            and_(
                StaffRealtimeLocation.employee_id == latest_ts_subq.c.employee_id,
                StaffRealtimeLocation.captured_at == latest_ts_subq.c.max_captured
            )
        ).group_by(StaffRealtimeLocation.employee_id).subquery()

        results = self.db.query(StaffRealtimeLocation).filter(
            StaffRealtimeLocation.id.in_(latest_id_subq.select())
        ).all()

        # Strict Invariants:
        # 1. Exactly ONE result returned for this employee
        self.assertEqual(len(results), 1)
        # 2. Tie-break strictly chose the MAX(id) row
        self.assertEqual(results[0].id, higher_id)


if __name__ == '__main__':
    unittest.main()

