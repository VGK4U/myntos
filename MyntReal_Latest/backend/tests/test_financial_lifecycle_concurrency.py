"""
MYNT OS — Real Production Financial Lifecycle Concurrency Test Suite
Tests concurrent production financial operations on AWS RDS PostgreSQL:
1. GPS Ingestion vs Real Production `end_journey()`
2. GPS Ingestion vs Real Production `approve_journey()`
3. GPS Ingestion vs Real Production `force_stop_journey()` (Cancellation/Force Stop)
4. Real Production `end_journey()` vs Real Production `approve_journey()`
"""

import unittest
import uuid
import asyncio
import concurrent.futures
from datetime import datetime, timedelta

from app.core.database import SessionLocal
from app.models.staff import StaffEmployee
from app.models.staff_attendance import get_indian_time, get_indian_date
from app.models.staff_journey import StaffJourney, StaffJourneyTrackPoint, JourneyStatus, JourneyApprovalStatus, JourneyPurpose
from app.services.location_ingestion_service import LocationIngestionService
from app.api.v1.endpoints.staff_journeys import (
    end_journey, approve_journey, force_stop_journey,
    EndJourneyRequest, ApprovalActionRequest, ForceStopRequest, LocationData
)


class TestFinancialLifecycleConcurrency(unittest.TestCase):

    def setUp(self):
        self.db = SessionLocal()
        self.today = get_indian_date()
        self.now = get_indian_time()

        # Manager account (role_id 1 = VGK Mentor, hierarchy level 150)
        manager = self.db.query(StaffEmployee).filter(StaffEmployee.id == 9997).first()
        if not manager:
            manager = StaffEmployee(
                id=9997,
                emp_code="EMP_MGR_9997",
                first_name="VGK",
                last_name="Manager",
                full_name="VGK Manager",
                email="mgr.concurrency@example.com",
                phone="9997776665",
                role_id=1,
                date_of_joining=self.today,
                password_hash="test_hash"
            )
            self.db.add(manager)

        # Field Staff account
        emp = self.db.query(StaffEmployee).filter(StaffEmployee.id == 9998).first()
        if not emp:
            emp = StaffEmployee(
                id=9998,
                emp_code="EMP_STAFF_9998",
                first_name="Field",
                last_name="Staff",
                full_name="Field Staff",
                email="staff.concurrency@example.com",
                phone="9998887776",
                role_id=5,
                date_of_joining=self.today,
                password_hash="test_hash"
            )
            self.db.add(emp)

        self.db.commit()
        self.manager_id = 9997
        self.emp_id = 9998

    def tearDown(self):
        try:
            self.db.query(StaffJourneyTrackPoint).filter(
                StaffJourneyTrackPoint.journey_id.in_(
                    self.db.query(StaffJourney.id).filter(StaffJourney.employee_id == self.emp_id)
                )
            ).delete(synchronize_session=False)
            self.db.query(StaffJourney).filter(StaffJourney.employee_id == self.emp_id).delete()
            self.db.commit()
        except Exception:
            self.db.rollback()
        finally:
            self.db.close()

    def test_01_gps_ingestion_vs_real_end_journey(self):
        """Test 1: Concurrent GPS ingestion and real production end_journey() execution."""
        journey = StaffJourney(
            employee_id=self.emp_id,
            date=self.today,
            start_time=self.now - timedelta(hours=1),
            purpose=JourneyPurpose.CLIENT_VISIT,
            status=JourneyStatus.IN_PROGRESS,
            approval_status=JourneyApprovalStatus.PENDING,
            transport_mode="bike",
            is_reimbursable=True,
            rate_per_km=5.0,
            total_distance_km=0.0,
            reimbursable_distance_km=0.0,
            reimbursement_amount=0.0
        )
        self.db.add(journey)
        self.db.commit()
        self.db.refresh(journey)
        j_id = journey.id

        # Seed start track point
        p_start = StaffJourneyTrackPoint(
            journey_id=j_id,
            latitude=17.7000,
            longitude=83.3000,
            accuracy=15.0,
            speed_kmh=15.0,
            wvv_compliant=True,
            distance_from_prev=0.0,
            cumulative_distance=0.0,
            timestamp=self.now - timedelta(hours=1),
            client_observation_id=str(uuid.uuid4())
        )
        self.db.add(p_start)
        self.db.commit()

        gps_payload = {
            "latitude": 17.7020,
            "longitude": 83.3020,
            "accuracy_m": 15.0,
            "client_observation_id": str(uuid.uuid4()),
            "timestamp": (self.now - timedelta(minutes=5)).isoformat()
        }

        def ingest_task():
            db_s = SessionLocal()
            try:
                return LocationIngestionService.ingest_journey_track_point(
                    db=db_s, journey_id=j_id, employee_id=self.emp_id, observation_data=gps_payload
                )
            finally:
                db_s.close()

        def end_journey_task():
            db_s = SessionLocal()
            try:
                staff_user = db_s.query(StaffEmployee).filter(StaffEmployee.id == self.emp_id).first()
                end_req = EndJourneyRequest(
                    notes="Completed field visit",
                    location=LocationData(
                        latitude=17.7050,
                        longitude=83.3050,
                        accuracy=10.0,
                        client_observation_id=str(uuid.uuid4())
                    )
                )
                return asyncio.run(end_journey(
                    journey_id=j_id,
                    request=end_req,
                    http_request=None,
                    db=db_s,
                    current_user=staff_user
                ))
            finally:
                db_s.close()

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            f1 = executor.submit(ingest_task)
            f2 = executor.submit(end_journey_task)
            r1 = f1.result()
            r2 = f2.result()

        self.assertTrue(r1["success"])
        self.assertTrue(r2["success"])

        verify_db = SessionLocal()
        try:
            j_final = verify_db.query(StaffJourney).filter(StaffJourney.id == j_id).first()
            self.assertEqual(j_final.status, JourneyStatus.COMPLETED)
            self.assertIsNotNone(j_final.end_time)
            self.assertGreater(j_final.total_distance_km, 0.0)
            self.assertEqual(j_final.reimbursement_amount, round(j_final.reimbursable_distance_km * 5.0, 2))
        finally:
            verify_db.close()

    def test_02_gps_ingestion_vs_real_approve_journey(self):
        """Test 2: Late GPS arrival during real production approve_journey() execution."""
        journey = StaffJourney(
            employee_id=self.emp_id,
            date=self.today,
            start_time=self.now - timedelta(hours=2),
            end_time=self.now - timedelta(minutes=30),
            purpose=JourneyPurpose.CLIENT_VISIT,
            status=JourneyStatus.COMPLETED,
            approval_status=JourneyApprovalStatus.PENDING,
            transport_mode="bike",
            is_reimbursable=True,
            rate_per_km=4.0,
            total_distance_km=10.0,
            reimbursable_distance_km=10.0,
            reimbursement_amount=40.0
        )
        self.db.add(journey)
        self.db.commit()
        self.db.refresh(journey)
        j_id = journey.id

        # Ingest 6 compliant track points (>= 5 required for validation approval)
        base_points = [
            (17.7000, 83.3000, 0.0, 0.0, 110),
            (17.7100, 83.3100, 2.0, 2.0, 90),
            (17.7200, 83.3200, 2.0, 4.0, 70),
            (17.7300, 83.3300, 2.0, 6.0, 50),
            (17.7400, 83.3400, 2.0, 8.0, 40),
            (17.7500, 83.3500, 2.0, 10.0, 30),
        ]
        for lat, lon, d_prev, c_dist, mins_ago in base_points:
            p = StaffJourneyTrackPoint(
                journey_id=j_id,
                latitude=lat,
                longitude=lon,
                accuracy=15.0,
                speed_kmh=20.0,
                wvv_compliant=True,
                distance_from_prev=d_prev,
                cumulative_distance=c_dist,
                timestamp=self.now - timedelta(minutes=mins_ago),
                client_observation_id=str(uuid.uuid4())
            )
            self.db.add(p)
        self.db.commit()

        late_gps = {
            "latitude": 17.7600,
            "longitude": 83.3600,
            "accuracy_m": 20.0,
            "client_observation_id": str(uuid.uuid4()),
            "timestamp": (self.now - timedelta(minutes=45)).isoformat()
        }

        # Step 1: Run real approve_journey endpoint logic
        db_approve = SessionLocal()
        mgr_user = db_approve.query(StaffEmployee).filter(StaffEmployee.id == self.manager_id).first()
        app_req = ApprovalActionRequest(action="approve", remarks="Verified & Approved")
        res_app = asyncio.run(approve_journey(
            journey_id=j_id,
            request=app_req,
            db=db_approve,
            current_user=mgr_user
        ))
        db_approve.close()
        self.assertTrue(res_app["success"])

        # Step 2: Late GPS arrives after approval
        db_ingest = SessionLocal()
        res_ingest = LocationIngestionService.ingest_journey_track_point(
            db=db_ingest, journey_id=j_id, employee_id=self.emp_id, observation_data=late_gps
        )
        db_ingest.close()
        self.assertTrue(res_ingest["success"])

        # Invariant: Journey is APPROVED, late track point recorded, but financial totals remain frozen!
        verify_db = SessionLocal()
        try:
            j_final = verify_db.query(StaffJourney).filter(StaffJourney.id == j_id).first()
            self.assertEqual(j_final.approval_status, JourneyApprovalStatus.APPROVED)
            self.assertEqual(j_final.total_distance_km, 10.0)
            self.assertEqual(j_final.reimbursable_distance_km, 10.0)
            self.assertEqual(j_final.reimbursement_amount, 40.0)

            # Late point was recorded for visual route audit history
            pt = verify_db.query(StaffJourneyTrackPoint).filter(
                StaffJourneyTrackPoint.client_observation_id == late_gps["client_observation_id"]
            ).first()
            self.assertIsNotNone(pt)
        finally:
            verify_db.close()

    def test_03_gps_ingestion_vs_real_force_stop_journey(self):
        """Test 3: Concurrent GPS point arrival during real force_stop_journey() execution."""
        journey = StaffJourney(
            employee_id=self.emp_id,
            date=self.today,
            start_time=self.now - timedelta(hours=1),
            purpose=JourneyPurpose.CLIENT_VISIT,
            status=JourneyStatus.IN_PROGRESS,
            approval_status=JourneyApprovalStatus.PENDING,
            transport_mode="bike",
            is_reimbursable=True,
            rate_per_km=4.0,
            total_distance_km=5.0,
            reimbursable_distance_km=5.0,
            reimbursement_amount=20.0
        )
        self.db.add(journey)
        self.db.commit()
        self.db.refresh(journey)
        j_id = journey.id

        gps_payload = {
            "latitude": 17.7800,
            "longitude": 83.3800,
            "accuracy_m": 15.0,
            "client_observation_id": str(uuid.uuid4()),
            "timestamp": (self.now - timedelta(minutes=2)).isoformat()
        }

        def ingest_task():
            db_s = SessionLocal()
            try:
                return LocationIngestionService.ingest_journey_track_point(
                    db=db_s, journey_id=j_id, employee_id=self.emp_id, observation_data=gps_payload
                )
            finally:
                db_s.close()

        def force_stop_task():
            db_s = SessionLocal()
            try:
                mgr_user = db_s.query(StaffEmployee).filter(StaffEmployee.id == self.manager_id).first()
                stop_req = ForceStopRequest(reason="Shift ended by manager")
                return asyncio.run(force_stop_journey(
                    journey_id=j_id,
                    request=stop_req,
                    http_request=None,
                    db=db_s,
                    current_user=mgr_user
                ))
            finally:
                db_s.close()

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            f1 = executor.submit(ingest_task)
            f2 = executor.submit(force_stop_task)
            r1 = f1.result()
            r2 = f2.result()

        self.assertTrue(r1["success"])
        self.assertTrue(r2["success"])

        verify_db = SessionLocal()
        try:
            j_final = verify_db.query(StaffJourney).filter(StaffJourney.id == j_id).first()
            self.assertEqual(j_final.status, JourneyStatus.COMPLETED)
            self.assertTrue(j_final.force_stopped)
            self.assertEqual(j_final.force_stopped_by, self.manager_id)
            self.assertIsNotNone(j_final.end_time)
        finally:
            verify_db.close()

    def test_04_real_end_journey_vs_real_approve_journey(self):
        """Test 4: Real end_journey() executed concurrently with real approve_journey()."""
        journey = StaffJourney(
            employee_id=self.emp_id,
            date=self.today,
            start_time=self.now - timedelta(hours=1),
            purpose=JourneyPurpose.CLIENT_VISIT,
            status=JourneyStatus.IN_PROGRESS,
            approval_status=JourneyApprovalStatus.PENDING,
            transport_mode="bike",
            is_reimbursable=True,
            rate_per_km=4.0,
            total_distance_km=8.0,
            reimbursable_distance_km=8.0,
            reimbursement_amount=32.0
        )
        self.db.add(journey)
        self.db.commit()
        self.db.refresh(journey)
        j_id = journey.id

        # Add 6 valid track points
        base_points = [
            (17.7000, 83.3000, 0.0, 0.0, 60),
            (17.7100, 83.3100, 1.6, 1.6, 50),
            (17.7200, 83.3200, 1.6, 3.2, 40),
            (17.7300, 83.3300, 1.6, 4.8, 30),
            (17.7400, 83.3400, 1.6, 6.4, 20),
            (17.7500, 83.3500, 1.6, 8.0, 10),
        ]
        for lat, lon, d_prev, c_dist, mins_ago in base_points:
            p = StaffJourneyTrackPoint(
                journey_id=j_id,
                latitude=lat,
                longitude=lon,
                accuracy=15.0,
                speed_kmh=20.0,
                wvv_compliant=True,
                distance_from_prev=d_prev,
                cumulative_distance=c_dist,
                timestamp=self.now - timedelta(minutes=mins_ago),
                client_observation_id=str(uuid.uuid4())
            )
            self.db.add(p)
        self.db.commit()

        def end_task():
            db_s = SessionLocal()
            try:
                staff_user = db_s.query(StaffEmployee).filter(StaffEmployee.id == self.emp_id).first()
                end_req = EndJourneyRequest(
                    notes="Finished route",
                    location=LocationData(
                        latitude=17.7550,
                        longitude=83.3550,
                        accuracy=10.0,
                        client_observation_id=str(uuid.uuid4())
                    )
                )
                return asyncio.run(end_journey(
                    journey_id=j_id,
                    request=end_req,
                    http_request=None,
                    db=db_s,
                    current_user=staff_user
                ))
            finally:
                db_s.close()

        def approve_task():
            db_s = SessionLocal()
            try:
                mgr_user = db_s.query(StaffEmployee).filter(StaffEmployee.id == self.manager_id).first()
                app_req = ApprovalActionRequest(action="approve", remarks="Approved route")
                return asyncio.run(approve_journey(
                    journey_id=j_id,
                    request=app_req,
                    db=db_s,
                    current_user=mgr_user
                ))
            except Exception as e:
                return {"success": False, "error": str(e)}
            finally:
                db_s.close()

        # Execute end_task and approve_task
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            f1 = executor.submit(end_task)
            f2 = executor.submit(approve_task)
            r_end = f1.result()
            r_app = f2.result()

        self.assertTrue(r_end["success"])

        verify_db = SessionLocal()
        try:
            j_final = verify_db.query(StaffJourney).filter(StaffJourney.id == j_id).first()
            self.assertEqual(j_final.status, JourneyStatus.COMPLETED)
            self.assertIsNotNone(j_final.end_time)
            self.assertGreater(j_final.total_distance_km, 8.0)
            self.assertGreater(j_final.reimbursable_distance_km, 8.0)
            self.assertEqual(j_final.reimbursement_amount, round(j_final.reimbursable_distance_km * 4.0, 2))

            # Explicit state machine assertion:
            # If approval executed after/with end_journey, approval succeeded.
            # If approval executed before end_journey committed, it rejected with 'Journey must be completed before approval'.
            if r_app.get("success"):
                self.assertEqual(j_final.approval_status, JourneyApprovalStatus.APPROVED)
                self.assertEqual(j_final.approved_by, self.manager_id)
            else:
                self.assertIn("Journey must be completed before approval", r_app.get("error", ""))
                self.assertEqual(j_final.approval_status, JourneyApprovalStatus.PENDING)
        finally:
            verify_db.close()


if __name__ == '__main__':
    unittest.main()
