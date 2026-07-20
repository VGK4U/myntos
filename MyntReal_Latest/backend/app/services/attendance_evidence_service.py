"""
Attendance Evidence Service
DC Protocol: Compliant upload handling for clock-in/out and break evidence
WVV Protocol: Live selfie capture with GPS validation

FEATURES:
- Captures live selfie photos during clock-in/out and break events
- GPS location tagging with accuracy validation
- DC-compliant semantic file naming (SAE_{EMP_CODE}_{DATE}_{EVENT_TYPE}_{TIMESTAMP}.jpg)
- Immutable evidence records with complete audit trails
- Integration with Universal Upload System

USAGE:
    result = await AttendanceEvidenceService.capture_evidence(
        photo_data="base64_encoded_image...",
        event_type="clock_in",
        attendance_id=1,
        gps_data={"latitude": 19.0760, "longitude": 72.8777, "accuracy_m": 10.5},
        employee=staff_employee_obj,
        db=db_session
    )

DC Protocol: Nov 29, 2025
"""

import base64
import io
import logging
import os
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, Union
from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session
import pytz

from app.services.universal_upload_service import UniversalUploadService
from app.services.object_storage import storage_service
from app.models.staff_attendance import StaffAttendanceEvidence, log_attendance_activity

logger = logging.getLogger(__name__)

IST = pytz.timezone('Asia/Kolkata')

VALID_EVENT_TYPES = {'clock_in', 'clock_out', 'break_start', 'break_end'}
CLOCK_EVENT_TYPES = {'clock_in', 'clock_out'}

MAX_GPS_STALENESS_SECONDS = 300
MAX_GPS_ACCURACY_METERS = 200
EVIDENCE_IMMUTABLE = True


class AttendanceEvidenceService:
    """
    Attendance evidence capture service for WVV-compliant verification
    DC Protocol: Semantic file naming and immutable evidence storage
    WVV Protocol: Live selfie + GPS validation
    """
    
    ALLOWED_IMAGE_TYPES = {'image/jpeg', 'image/jpg', 'image/png'}
    MAX_FILE_SIZE = 5 * 1024 * 1024
    
    STORAGE_ROOT = Path(__file__).parent.parent.parent.parent / "frontend" / "storage"
    SEGMENT_KEY = 'attendance_evidence'
    SEGMENT_CODE = 'SAE'
    
    @classmethod
    def validate_event_type(cls, event_type: str) -> str:
        """
        Validate event type is allowed
        WVV: Whitelist validation
        """
        if event_type not in VALID_EVENT_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid event_type '{event_type}'. Must be one of: {', '.join(VALID_EVENT_TYPES)}"
            )
        return event_type
    
    @classmethod
    def check_evidence_immutability(
        cls,
        db: Session,
        attendance_id: int,
        event_type: str,
        break_id: Optional[int] = None
    ) -> None:
        """
        Check if evidence already exists for this event (immutability enforcement)
        DC Protocol: Evidence records are immutable once created
        
        Raises:
            HTTPException if evidence already exists for this event
        """
        if not EVIDENCE_IMMUTABLE:
            return
        
        query = db.query(StaffAttendanceEvidence).filter(
            StaffAttendanceEvidence.attendance_id == attendance_id,
            StaffAttendanceEvidence.event_type == event_type
        )
        
        if break_id is not None:
            query = query.filter(StaffAttendanceEvidence.break_id == break_id)
        elif event_type in CLOCK_EVENT_TYPES:
            query = query.filter(StaffAttendanceEvidence.break_id == None)
        
        existing = query.first()
        
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Evidence already captured for {event_type.replace('_', ' ')}. Evidence is immutable once created."
            )
    
    @classmethod
    def validate_gps_data(cls, gps_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate GPS data completeness and accuracy
        WVV: GPS presence and accuracy validation
        
        Args:
            gps_data: Dict with latitude, longitude, accuracy_m (optional: altitude, timestamp)
            
        Returns:
            Validated GPS data dict
            
        Raises:
            HTTPException if GPS data is invalid or missing
        """
        if not gps_data:
            raise HTTPException(
                status_code=400,
                detail="GPS location data is required for attendance evidence"
            )
        
        required_fields = ['latitude', 'longitude']
        for field in required_fields:
            if field not in gps_data or gps_data[field] is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"GPS {field} is required for attendance evidence"
                )
        
        try:
            latitude = float(gps_data['latitude'])
            longitude = float(gps_data['longitude'])
            
            if not (-90 <= latitude <= 90):
                raise ValueError("Latitude must be between -90 and 90")
            if not (-180 <= longitude <= 180):
                raise ValueError("Longitude must be between -180 and 180")
                
        except (TypeError, ValueError) as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid GPS coordinates: {str(e)}"
            )
        
        accuracy_m = gps_data.get('accuracy_m')
        if accuracy_m is not None:
            try:
                accuracy_m = float(accuracy_m)
                if accuracy_m < 0:
                    raise ValueError("Accuracy cannot be negative")
                if accuracy_m > MAX_GPS_ACCURACY_METERS:
                    raise HTTPException(
                        status_code=400,
                        detail=f"GPS accuracy ({accuracy_m:.1f}m) exceeds maximum allowed ({MAX_GPS_ACCURACY_METERS}m). Please ensure location services are enabled."
                    )
            except (TypeError, ValueError) as e:
                if "exceeds maximum" not in str(e):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid GPS accuracy value: {str(e)}"
                    )
                raise
        
        validated = {
            'latitude': latitude,
            'longitude': longitude,
            'accuracy_m': accuracy_m,
            'altitude': gps_data.get('altitude'),
        }
        
        if 'address' in gps_data:
            validated['address'] = gps_data.get('address')
        
        return validated
    
    @classmethod
    def validate_image_content(cls, content: bytes, content_type: str) -> None:
        """
        Validate image content type and size
        WVV: Image validation for attendance selfies
        """
        if content_type not in cls.ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Only JPEG/PNG images are allowed for attendance evidence. Received: {content_type}"
            )
        
        if len(content) == 0:
            raise HTTPException(
                status_code=400,
                detail="Image file is empty"
            )
        
        if len(content) > cls.MAX_FILE_SIZE:
            size_mb = len(content) / (1024 * 1024)
            raise HTTPException(
                status_code=400,
                detail=f"Image size ({size_mb:.2f}MB) exceeds maximum allowed (5MB)"
            )
    
    @classmethod
    def build_semantic_filename(
        cls,
        emp_code: str,
        event_type: str,
        captured_at: datetime,
        extension: str = '.jpg'
    ) -> str:
        """
        Generate DC-compliant semantic filename for attendance evidence
        
        Format: SAE_{EMP_CODE}_{DATE}_{EVENT_TYPE}_{TIMESTAMP}{.ext}
        Example: SAE_MR10009_20251129_CLOCK_IN_153045.jpg
        
        DC Protocol: Immutable filename with full audit context
        """
        safe_emp_code = re.sub(r'[^a-zA-Z0-9]', '', emp_code.upper())
        
        date_str = captured_at.strftime('%Y%m%d')
        
        safe_event_type = event_type.upper().replace('-', '_')
        
        time_str = captured_at.strftime('%H%M%S')
        
        ext = extension.lower() if extension.startswith('.') else f'.{extension.lower()}'
        
        filename = f"{cls.SEGMENT_CODE}_{safe_emp_code}_{date_str}_{safe_event_type}_{time_str}{ext}"
        
        return filename[:255]
    
    @classmethod
    def get_storage_path(cls, emp_code: str, captured_at: datetime) -> Path:
        """
        Generate storage directory path for attendance evidence
        
        Structure: attendance_evidence/{year}/{emp_code}/
        Example: attendance_evidence/2025/MR10009/
        
        DC Protocol: Organized file storage with date-based partitioning
        """
        year = captured_at.strftime('%Y')
        safe_emp_code = re.sub(r'[^a-zA-Z0-9]', '', emp_code.upper())
        
        storage_dir = cls.STORAGE_ROOT / 'attendance_evidence' / year / safe_emp_code
        
        return storage_dir
    
    @classmethod
    async def decode_base64_image(cls, base64_data: str) -> tuple[bytes, str]:
        """
        Decode base64 image data and determine content type
        
        Returns:
            Tuple of (image_bytes, content_type)
        """
        if ',' in base64_data:
            header, base64_data = base64_data.split(',', 1)
            if 'image/png' in header:
                content_type = 'image/png'
            elif 'image/jpeg' in header or 'image/jpg' in header:
                content_type = 'image/jpeg'
            else:
                content_type = 'image/jpeg'
        else:
            content_type = 'image/jpeg'
        
        try:
            image_bytes = base64.b64decode(base64_data)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid base64 image data: {str(e)}"
            )
        
        return image_bytes, content_type
    
    @classmethod
    async def capture_evidence(
        cls,
        photo_data: Union[str, UploadFile],
        event_type: str,
        attendance_id: int,
        gps_data: Dict[str, Any],
        employee,
        db: Session,
        break_id: Optional[int] = None,
        device_info: Optional[Dict[str, Any]] = None,
        remarks: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Capture and store attendance evidence with photo and GPS
        
        DC Protocol: Complete evidence capture with audit trail
        WVV Protocol: Live selfie + GPS validation
        
        Args:
            photo_data: Base64 encoded image string or UploadFile
            event_type: One of 'clock_in', 'clock_out', 'break_start', 'break_end'
            attendance_id: ID of the attendance record
            gps_data: Dict with latitude, longitude, accuracy_m, etc.
            employee: StaffEmployee object (for emp_code and id)
            db: Database session
            break_id: Optional ID of the break record (for break events)
            device_info: Optional device/browser information
            remarks: Optional notes
            
        Returns:
            Dict with evidence_id, storage_path, and metadata
            
        Raises:
            HTTPException on validation failure
        """
        cls.validate_event_type(event_type)
        
        cls.check_evidence_immutability(db, attendance_id, event_type, break_id)
        
        validated_gps = cls.validate_gps_data(gps_data)
        
        now_utc = datetime.now(timezone.utc)
        captured_at = now_utc.astimezone(IST)
        
        if isinstance(photo_data, str):
            image_bytes, content_type = await cls.decode_base64_image(photo_data)
        else:
            content = await photo_data.read()
            image_bytes = content
            content_type = photo_data.content_type or 'image/jpeg'
            await photo_data.seek(0)
        
        cls.validate_image_content(image_bytes, content_type)
        
        extension = '.png' if 'png' in content_type.lower() else '.jpg'
        
        filename = cls.build_semantic_filename(
            emp_code=employee.emp_code,
            event_type=event_type,
            captured_at=captured_at,
            extension=extension
        )
        
        # DC Jan 2026: Use Object Storage directly for production persistence
        # Local filesystem is ephemeral in production - photos would be lost on restart
        relative_path = f"attendance_evidence/{captured_at.strftime('%Y')}/{re.sub(r'[^a-zA-Z0-9]', '', employee.emp_code.upper())}/{filename}"
        
        # DC Protocol: Determine environment for storage strategy
        is_production = os.environ.get('REPL_DEPLOYMENT', '').lower() == 'true' or os.environ.get('REPLIT_DEPLOYMENT', '').lower() == '1'
        
        try:
            # Step 1: Upload to Object Storage (persists across production restarts)
            logger.info(f"[DC-EVIDENCE-UPLOAD] Uploading to Object Storage: {relative_path}")
            success = storage_service.upload_file(relative_path, image_bytes)
            
            if success:
                # Step 2: Verify upload succeeded (exists check)
                verified = storage_service.file_exists(relative_path)
                if verified:
                    logger.info(f"[DC-EVIDENCE-UPLOAD] ✅ Upload verified: {relative_path}")
                else:
                    logger.error(f"[DC-EVIDENCE-UPLOAD] ❌ Upload returned success but file not found: {relative_path}")
                    success = False
            
            if not success:
                if is_production:
                    # DC Protocol: FAIL HARD in production - don't allow ephemeral local storage
                    logger.error(f"[DC-EVIDENCE-UPLOAD] ❌ PRODUCTION FAILURE: Object Storage upload failed for {relative_path}")
                    raise HTTPException(
                        status_code=500,
                        detail="Photo upload failed. Please try again. If the problem persists, contact support."
                    )
                else:
                    # Development only: Fallback to local storage
                    storage_dir = cls.get_storage_path(employee.emp_code, captured_at)
                    storage_dir.mkdir(parents=True, exist_ok=True)
                    file_path = storage_dir / filename
                    with open(file_path, 'wb') as f:
                        f.write(image_bytes)
                    logger.warning(f"[DC-EVIDENCE-UPLOAD] ⚠️ DEV ONLY: Saved locally: {relative_path}")
                    
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"[DC-EVIDENCE-UPLOAD] ❌ Exception during upload: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to save evidence file: {str(e)}"
            )
        
        location_meta = {
            'raw_gps': gps_data,
            'validated': True,
            'captured_at_utc': now_utc.isoformat(),
            'captured_at_ist': captured_at.isoformat()
        }
        
        try:
            # DC_PHOTO_TIMESTAMP_001: Extract timestamp & face detection metadata from request
            timestamp_overlay = gps_data.get('timestamp_overlay', True)
            face_detected = gps_data.get('face_detected', False)
            face_confidence = gps_data.get('face_confidence', 0)
            
            evidence = StaffAttendanceEvidence(
                attendance_id=attendance_id,
                break_id=break_id,
                event_type=event_type,
                captured_at=captured_at,
                photo_path=relative_path,
                photo_filename=filename,
                download_filename=filename,
                uses_new_naming=True,
                gps_latitude=validated_gps['latitude'],
                gps_longitude=validated_gps['longitude'],
                gps_accuracy_m=validated_gps.get('accuracy_m'),
                gps_altitude=validated_gps.get('altitude'),
                location_address=validated_gps.get('address'),
                location_meta=location_meta,
                device_info=device_info,
                timestamp_overlay=timestamp_overlay,
                face_detected=face_detected,
                face_confidence=face_confidence,
                remarks=remarks,
                created_by=employee.id
            )
            
            db.add(evidence)
            db.flush()
            
            # DC Protocol: Evidence logging is handled directly in staff_attendance_evidence table
            # No need for separate activity log entry - activity log is managed by clock_in/clock_out endpoints
            
            logger.info(
                f"Attendance evidence captured: employee={employee.emp_code}, "
                f"event={event_type}, attendance_id={attendance_id}, evidence_id={evidence.id}"
            )
            
            return {
                'evidence_id': evidence.id,
                'storage_path': relative_path,
                'filename': filename,
                'event_type': event_type,
                'captured_at': captured_at.isoformat(),
                'gps': {
                    'latitude': validated_gps['latitude'],
                    'longitude': validated_gps['longitude'],
                    'accuracy_m': validated_gps.get('accuracy_m')
                },
                'file_size_bytes': len(image_bytes)
            }
            
        except HTTPException:
            # Cleanup: Try to delete from Object Storage and local
            try:
                storage_service.delete_file(relative_path)
            except Exception:
                pass
            raise
        except Exception as e:
            # Cleanup: Try to delete from Object Storage and local
            try:
                storage_service.delete_file(relative_path)
            except Exception:
                pass
            logger.error(f"Failed to create evidence record: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create evidence record: {str(e)}"
            )
    
    @classmethod
    async def get_evidence_for_attendance(
        cls,
        attendance_id: int,
        db: Session
    ) -> list[Dict[str, Any]]:
        """
        Retrieve all evidence records for an attendance entry
        
        DC Protocol: Complete evidence retrieval for audit
        """
        evidence_list = db.query(StaffAttendanceEvidence).filter(
            StaffAttendanceEvidence.attendance_id == attendance_id
        ).order_by(StaffAttendanceEvidence.captured_at.asc()).all()
        
        return [
            {
                'id': e.id,
                'event_type': e.event_type,
                'captured_at': e.captured_at.isoformat() if e.captured_at else None,
                'photo_path': e.photo_path,
                'filename': e.photo_filename,
                'gps': {
                    'latitude': float(e.gps_latitude) if e.gps_latitude else None,
                    'longitude': float(e.gps_longitude) if e.gps_longitude else None,
                    'accuracy_m': float(e.gps_accuracy_m) if e.gps_accuracy_m else None,
                    'address': e.location_address
                },
                'remarks': e.remarks
            }
            for e in evidence_list
        ]
    
    @classmethod
    async def get_evidence_for_break(
        cls,
        break_id: int,
        db: Session
    ) -> list[Dict[str, Any]]:
        """
        Retrieve all evidence records for a break entry
        
        DC Protocol: Complete evidence retrieval for audit
        """
        evidence_list = db.query(StaffAttendanceEvidence).filter(
            StaffAttendanceEvidence.break_id == break_id
        ).order_by(StaffAttendanceEvidence.captured_at.asc()).all()
        
        return [
            {
                'id': e.id,
                'event_type': e.event_type,
                'captured_at': e.captured_at.isoformat() if e.captured_at else None,
                'photo_path': e.photo_path,
                'filename': e.photo_filename,
                'gps': {
                    'latitude': float(e.gps_latitude) if e.gps_latitude else None,
                    'longitude': float(e.gps_longitude) if e.gps_longitude else None,
                    'accuracy_m': float(e.gps_accuracy_m) if e.gps_accuracy_m else None,
                    'address': e.location_address
                },
                'remarks': e.remarks
            }
            for e in evidence_list
        ]
