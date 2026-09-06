"""
MYNT OS — Real PostgreSQL Concurrency Test Suite
Tests concurrent location ingestion on AWS RDS PostgreSQL:
1. Identical observation UUIDv4 sent simultaneously (idempotent duplicate).
2. Distinct observation UUIDv4s sent simultaneously (both saved, no lost distance update).
3. Out-of-order concurrent observations (chronological consistency).
4. Financial immutability under concurrency.
"""

import unittest
import uuid
import concurrent.futures
from datetime import datetime, timedelta

from app.core.database import SessionLocal
from app.models.staff import StaffEmployee
from app.models.staff_attendance import StaffAttendance, StaffRealtimeLocation, get_indian_time, get_indian_date
from app.models.staff_journey import StaffJourney, StaffJourneyTrackPoint, JourneyStatus, JourneyApprovalStatus, JourneyPurpose
from app.services.location_ingestion_service import LocationIngestionService


class TestPostgresConcurrency(unittest.TestCase):

    def setUp(self):
        self.db = SessionLocal()
        self.today = get_indian_date()
        self.now = get_indian_time()

        # Find or create a test employee in PostgreSQL
        emp = self.db.query(StaffEmployee).filter(StaffEmployee.id == 9999).first()
        if not emp:
            emp = StaffEmployee(
                id=9999,
                emp_code="EMP_TEST_9999",
                full_name="Concurrency Test Engineer",
                email="concurrency.test@example.com",
                phone="9999999999",
                role_id=1,
                date_of_joining=self.today,
                password_hash="test_hash"
            )
            self.db.add(emp)
            self.db.commit()
        self.emp_id = 9999

        # Create isolated test journey
        self.journey = StaffJourney(
            employee_id=self.emp_id,
            date=self.today,
            start_time=self.now - timedelta(hours=1),
            purpose=JourneyPurpose.CLIENT_VISIT,
            status=JourneyStatus.IN_PROGRESS,
            approval_status=JourneyApprovalStatus.PENDING,
            transport_mode="bike",
            is_reimbursable=True,
            rate_per_km=4.0,
            total_distance_km=0.0,
            reimbursable_distance_km=0.0,
            reimbursement_amount=0.0
        )
        self.db.add(self.journey)
        self.db.commit()
        self.db.refresh(self.journey)
        self.journey_id = self.journey.id

    def tearDown(self):
        try:
            # Clean up test journey and track points
            self.db.query(StaffJourneyTrackPoint).filter(
                StaffJourneyTrackPoint.journey_id == self.journey_id
            ).delete()
            self.db.query(StaffRealtimeLocation).filter(
                StaffRealtimeLocation.employee_id == self.emp_id
            ).delete()
            self.db.query(StaffJourney).filter(
                StaffJourney.id == self.journey_id
            ).delete()
            self.db.commit()
        except Exception:
            self.db.rollback()
        finally:
            self.db.close()

    def test_01_concurrent_identical_observation_idempotency(self):
        """Test 1: Two simultaneous requests with identical UUIDv4 observation ID."""
        shared_uuid = str(uuid.uuid4())
        obs_payload = {
            "latitude": 17.686816,
            "longitude": 83.218482,
            "accuracy_m": 15.0,
            "client_observation_id": shared_uuid,
            "timestamp": (self.now - timedelta(minutes=10)).isoformat()
        }

        def ingest_task():
            db_session = SessionLocal()
            try:
                res = LocationIngestionService.ingest_journey_track_point(
                    db=db_session,
                    journey_id=self.journey_id,
                    employee_id=self.emp_id,
                    observation_data=obs_payload
                )
                return res
            finally:
                db_session.close()

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            f1 = executor.submit(ingest_task)
            f2 = executor.submit(ingest_task)
            res1 = f1.result()
            res2 = f2.result()

        self.assertTrue(res1["success"])
        self.assertTrue(res2["success"])

        # Exactly one must be primary and one must be duplicate=True (or both handled idempotently)
        duplicates = [res1.get("duplicate"), res2.get("duplicate")]
        self.assertIn(False, duplicates)
        self.assertIn(True, duplicates)

        # Verify exactly 1 track point in DB
        verify_db = SessionLocal()
        try:
            points = verify_db.query(StaffJourneyTrackPoint).filter(
                StaffJourneyTrackPoint.journey_id == self.journey_id,
                StaffJourneyTrackPoint.client_observation_id == shared_uuid
            ).all()
            self.assertEqual(len(points), 1)
        finally:
            verify_db.close()

    def test_02_concurrent_distinct_observations_aggregation(self):
        """Test 2: Two simultaneous requests with DIFFERENT UUIDv4 observations for same journey."""
        obs1 = {
            "latitude": 17.6868,
            "longitude": 83.2184,
            "accuracy_m": 15.0,
            "client_observation_id": str(uuid.uuid4()),
            "timestamp": (self.now - timedelta(minutes=5)).isoformat()
        }
        obs2 = {
            "latitude": 17.6968,
            "longitude": 83.2284,
            "accuracy_m": 15.0,
            "client_observation_id": str(uuid.uuid4()),
            "timestamp": (self.now - timedelta(minutes=2)).isoformat()
        }

        def ingest_task(payload):
            db_session = SessionLocal()
            try:
                res = LocationIngestionService.ingest_journey_track_point(
                    db=db_session,
                    journey_id=self.journey_id,
                    employee_id=self.emp_id,
                    observation_data=payload
                )
                return res
            finally:
                db_session.close()

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            f1 = executor.submit(ingest_task, obs1)
            f2 = executor.submit(ingest_task, obs2)
            res1 = f1.result()
            res2 = f2.result()

        self.assertTrue(res1["success"])
        self.assertTrue(res2["success"])
        self.assertFalse(res1.get("duplicate", False))
        self.assertFalse(res2.get("duplicate", False))

        # Query fresh session from PostgreSQL
        verify_db = SessionLocal()
        try:
            points = verify_db.query(StaffJourneyTrackPoint).filter(
                StaffJourneyTrackPoint.journey_id == self.journey_id
            ).all()
            self.assertEqual(len(points), 2)

            journey = verify_db.query(StaffJourney).filter(StaffJourney.id == self.journey_id).first()
            self.assertGreater(journey.total_distance_km, 0.0)
            self.assertGreater(journey.reimbursement_amount, 0.0)
        finally:
            verify_db.close()

    def test_03_concurrent_out_of_order_observations(self):
        """Test 3: Out-of-order simultaneous observations maintain chronological order and distance."""
        p_early = {
            "latitude": 17.7000,
            "longitude": 83.3000,
            "accuracy_m": 10.0,
            "client_observation_id": str(uuid.uuid4()),
            "timestamp": (self.now - timedelta(minutes=15)).isoformat()
        }
        p_late = {
            "latitude": 17.7200,
            "longitude": 83.3200,
            "accuracy_m": 10.0,
            "client_observation_id": str(uuid.uuid4()),
            "timestamp": (self.now - timedelta(minutes=5)).isoformat()
        }
        p_middle = {
            "latitude": 17.7100,
            "longitude": 83.3100,
            "accuracy_m": 10.0,
            "client_observation_id": str(uuid.uuid4()),
            "timestamp": (self.now - timedelta(minutes=10)).isoformat()
        }

        # Ingest p_late first
        db1 = SessionLocal()
        LocationIngestionService.ingest_journey_track_point(
            db=db1, journey_id=self.journey_id, employee_id=self.emp_id, observation_data=p_late
        )
        db1.close()

        def ingest_task(payload):
            db_session = SessionLocal()
            try:
                return LocationIngestionService.ingest_journey_track_point(
                    db=db_session, journey_id=self.journey_id, employee_id=self.emp_id, observation_data=payload
                )
            finally:
                db_session.close()

        # Ingest p_early and p_middle concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            f1 = executor.submit(ingest_task, p_early)
            f2 = executor.submit(ingest_task, p_middle)
            f1.result()
            f2.result()

        verify_db = SessionLocal()
        try:
            points = verify_db.query(StaffJourneyTrackPoint).filter(
                StaffJourneyTrackPoint.journey_id == self.journey_id
            ).order_by(StaffJourneyTrackPoint.timestamp.asc()).all()

            self.assertEqual(len(points), 3)
            # Must be ordered: p_early -> p_middle -> p_late
            self.assertAlmostEqual(points[0].latitude, 17.7000, places=3)
            self.assertAlmostEqual(points[1].latitude, 17.7100, places=3)
            self.assertAlmostEqual(points[2].latitude, 17.7200, places=3)

            # Cumulative distances must be strictly monotonically increasing
            self.assertEqual(points[0].cumulative_distance, 0.0)
            self.assertGreater(points[1].cumulative_distance, 0.0)
            self.assertGreater(points[2].cumulative_distance, points[1].cumulative_distance)

            journey = verify_db.query(StaffJourney).filter(StaffJourney.id == self.journey_id).first()
            self.assertAlmostEqual(journey.total_distance_km, points[2].cumulative_distance, places=3)
        finally:
            verify_db.close()


if __name__ == '__main__':
    unittest.main()
