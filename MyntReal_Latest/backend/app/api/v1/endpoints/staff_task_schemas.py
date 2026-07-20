"""
Staff Task Management Pydantic Schemas (DC Protocol Compliant)
Request/Response models for task and attendance endpoints

Created: Nov 26, 2025
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
import base64


class TaskPhaseInput(BaseModel):
    """Phase definition for task creation/update (DC Protocol Compliant)"""
    phase_number: int = Field(..., ge=1, le=20, description="Phase sequence number (1-20)")
    phase_title: str = Field(..., min_length=3, max_length=256, description="Phase title")
    phase_description: Optional[str] = Field(None, max_length=2000, description="Phase description")
    phase_assignee_id: int = Field(..., description="Employee ID to assign this phase (primary)")
    secondary_phase_assignee_ids: List[int] = Field(default_factory=list, description="Secondary assignee IDs for this phase (max 2)")
    target_date: Optional[date] = Field(None, description="Target completion date for phase")
    contact_phone: Optional[str] = Field(None, max_length=20, description="Contact mobile number for this phase")
    contact_person_name: Optional[str] = Field(None, max_length=128, description="Contact person name for this phase (optional)")

    @validator('secondary_phase_assignee_ids')
    def validate_phase_secondary_limit(cls, v, values):
        if len(v) > 2:
            raise ValueError("Maximum 2 secondary assignees allowed per phase")
        primary = values.get('phase_assignee_id')
        if primary and primary in v:
            raise ValueError("Primary phase assignee cannot be a secondary assignee")
        if len(v) != len(set(v)):
            raise ValueError("Duplicate secondary assignee IDs not allowed")
        return v


class CreateTaskRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=256)
    description: Optional[str] = Field(None, max_length=5000)
    category: str = Field(default="general")
    priority: str = Field(default="medium")
    primary_assignee_id: int
    secondary_assignee_ids: List[int] = Field(default_factory=list)
    due_date: Optional[datetime] = None
    start_date: Optional[date] = None
    estimated_hours: Optional[float] = Field(None, ge=0, le=1000)
    tags: List[str] = Field(default_factory=list)
    contact_phone: Optional[str] = Field(None, max_length=20, description="Contact mobile number for this task")
    contact_person_name: Optional[str] = Field(None, max_length=128, description="Contact person name (optional)")
    custom_assigner_id: Optional[int] = None
    phases: Optional[List[TaskPhaseInput]] = Field(default_factory=list, description="Optional phases for multi-stage tasks (max 10)")
    
    @validator('category')
    def validate_category(cls, v):
        valid = ['general', 'development', 'support', 'admin', 'meeting', 'review', 'documentation', 'other']
        if v not in valid:
            raise ValueError(f"Category must be one of: {valid}")
        return v
    
    @validator('priority')
    def validate_priority(cls, v):
        valid = ['low', 'medium', 'high', 'critical']
        if v not in valid:
            raise ValueError(f"Priority must be one of: {valid}")
        return v
    
    @validator('secondary_assignee_ids')
    def validate_secondary_limit(cls, v, values):
        if len(v) > 2:
            raise ValueError("Maximum 2 secondary assignees allowed")
        primary = values.get('primary_assignee_id')
        if primary and primary in v:
            raise ValueError("Primary assignee cannot be a secondary assignee")
        return v
    
    @validator('phases')
    def validate_phases(cls, v):
        if v is None:
            return []
        if len(v) > 10:
            raise ValueError("Maximum 10 phases allowed per task")
        phase_numbers = [p.phase_number for p in v]
        if len(phase_numbers) != len(set(phase_numbers)):
            raise ValueError("Phase numbers must be unique")
        return v


class UpdateTaskRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=256)
    description: Optional[str] = Field(None, max_length=5000)
    category: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    due_date: Optional[datetime] = None
    start_date: Optional[date] = None
    estimated_hours: Optional[float] = Field(None, ge=0, le=1000)
    progress: Optional[int] = Field(None, ge=0, le=100)
    tags: Optional[List[str]] = None
    contact_phone: Optional[str] = Field(None, max_length=20, description="Contact mobile number")
    contact_person_name: Optional[str] = Field(None, max_length=128, description="Contact person name")
    new_assigner_id: Optional[int] = None
    secondary_assignee_ids: Optional[List[int]] = Field(None, description="Update secondary assignees (max 2)")
    time_taken_minutes: Optional[int] = Field(None, ge=1, le=1440, description="Time taken in minutes for this update")

    @validator('secondary_assignee_ids')
    def validate_secondary_limit(cls, v):
        if v is None:
            return v
        if len(v) > 2:
            raise ValueError("Maximum 2 secondary assignees allowed")
        if len(v) != len(set(v)):
            raise ValueError("Duplicate secondary assignee IDs not allowed")
        return v
    
    @validator('category')
    def validate_category(cls, v):
        if v is None:
            return v
        valid = ['general', 'development', 'support', 'admin', 'meeting', 'review', 'documentation', 'other']
        if v not in valid:
            raise ValueError(f"Category must be one of: {valid}")
        return v
    
    @validator('priority')
    def validate_priority(cls, v):
        if v is None:
            return v
        valid = ['low', 'medium', 'high', 'critical']
        if v not in valid:
            raise ValueError(f"Priority must be one of: {valid}")
        return v
    
    @validator('status')
    def validate_status(cls, v):
        if v is None:
            return v
        valid = ['pending', 'in_progress', 'on_hold', 'under_review', 'completed', 'cancelled']
        if v not in valid:
            raise ValueError(f"Status must be one of: {valid}")
        return v


class UpdateTaskProgressRequest(BaseModel):
    progress: int = Field(..., ge=0, le=100)
    status: Optional[str] = None
    notes: Optional[str] = Field(None, max_length=1000)
    
    @validator('status')
    def validate_status(cls, v):
        if v is None:
            return v
        valid = ['pending', 'in_progress', 'on_hold', 'under_review', 'completed', 'cancelled']
        if v not in valid:
            raise ValueError(f"Status must be one of: {valid}")
        return v


class UpdateTaskStatusRequest(BaseModel):
    status: str
    notes: Optional[str] = Field(None, max_length=1000)
    time_taken_minutes: Optional[int] = Field(None, ge=1, le=1440, description="Time taken in minutes for this status change")
    
    @validator('status')
    def validate_status(cls, v):
        valid = ['pending', 'in_progress', 'on_hold', 'under_review', 'completed', 'cancelled']
        if v not in valid:
            raise ValueError(f"Status must be one of: {valid}")
        return v


class AddSecondaryAssigneeRequest(BaseModel):
    employee_id: int


class ReassignPrimaryRequest(BaseModel):
    new_primary_id: int
    notes: Optional[str] = Field(None, max_length=500)


class AddCommentRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)


class LogTimeRequest(BaseModel):
    hours: float = Field(..., gt=0, le=24)
    work_date: date
    notes: Optional[str] = Field(None, max_length=1000)


class LocationData(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    accuracy: Optional[float] = None
    address: Optional[str] = Field(None, max_length=500)


class EvidenceData(BaseModel):
    """
    Evidence data for attendance verification (WVV Protocol - DC Compliant)
    Contains selfie photo with timestamp overlay, face detection, and GPS location data
    DC_PHOTO_TIMESTAMP_001: Photos include visible IST timestamp overlay
    DC_PHOTO_AI_001: Face detection validates human presence
    """
    photo_base64: str = Field(..., description="Base64 encoded selfie image with timestamp overlay (JPEG/PNG, minimum 5KB)")
    gps_latitude: float = Field(..., ge=-90, le=90, description="GPS latitude coordinate")
    gps_longitude: float = Field(..., ge=-180, le=180, description="GPS longitude coordinate")
    gps_accuracy_m: Optional[float] = Field(None, ge=0, description="GPS accuracy in meters")
    gps_altitude: Optional[float] = Field(None, description="GPS altitude in meters")
    gps_source: Optional[str] = Field("preflight_camera", description="GPS acquisition source")
    location_address: Optional[str] = Field(None, max_length=500, description="Reverse-geocoded address")
    captured_at: Optional[str] = Field(None, description="ISO timestamp when captured")
    timestamp_overlay: Optional[bool] = Field(True, description="Photo has visible timestamp overlay (IST)")
    face_detected: Optional[bool] = Field(False, description="Human face detected in photo")
    face_confidence: Optional[int] = Field(0, ge=0, le=100, description="Face detection confidence percentage")
    
    @validator('photo_base64')
    def validate_photo(cls, v):
        """
        DC_PHOTO_VALIDATION_001: Comprehensive photo base64 validation
        - Must start with data:image/
        - Minimum 5KB (WVV requirement for 1920x1080 JPEG)
        - Maximum 10MB base64
        """
        if not v or not isinstance(v, str):
            raise ValueError("[DC_ERROR] Photo data is required and must be string")
        
        if not v.startswith('data:image/'):
            raise ValueError("[DC_ERROR] Photo must be base64 data URL (data:image/...)")
        
        if len(v) < 6000:
            raise ValueError("[WVV_ERROR] Photo size too small (minimum 5KB required for WVV compliance)")
        
        if len(v) > 10 * 1024 * 1024:
            raise ValueError("[DC_ERROR] Photo exceeds maximum size (10MB base64)")
        
        # DC_PHOTO_FORMAT_CHECK: Validate JPEG header FFD8FF or PNG header
        try:
            if ',' in v:
                _, data = v.split(',', 1)
            else:
                data = v
            
            decoded_sample = base64.b64decode(data[:1000])
            if not (decoded_sample.startswith(b'\xff\xd8\xff') or decoded_sample.startswith(b'\x89PNG')):
                raise ValueError("[DC_ERROR] Invalid image format - must be JPEG or PNG")
        except Exception as e:
            if "[DC_ERROR]" in str(e) or "[WVV_ERROR]" in str(e):
                raise
            raise ValueError("[DC_ERROR] Photo data validation failed: " + str(e))
        
        return v


class ClockInRequest(BaseModel):
    work_mode: str = Field(default="office")
    location: Optional[LocationData] = None
    notes: Optional[str] = Field(None, max_length=500)
    evidence: Optional[EvidenceData] = Field(None, description="WVV: Selfie + GPS evidence for verification")
    
    @validator('work_mode')
    def validate_work_mode(cls, v):
        valid = ['office', 'wfh', 'field', 'hybrid']
        if v not in valid:
            raise ValueError(f"Work mode must be one of: {valid}")
        return v


class ClockOutRequest(BaseModel):
    location: Optional[LocationData] = None
    notes: Optional[str] = Field(None, max_length=500)
    evidence: Optional[EvidenceData] = Field(None, description="WVV: Selfie + GPS evidence for verification")


class BreakStartRequest(BaseModel):
    break_type: str = Field(default="personal")
    break_type_id: Optional[int] = Field(None, description="DC: Reference to staff_break_types table")
    
    @validator('break_type')
    def validate_break_type(cls, v):
        valid = ['lunch', 'tea', 'personal', 'meeting', 'client_visit', 'travel', 'emergency', 'other']
        if v not in valid:
            raise ValueError(f"Break type must be one of: {valid}")
        return v


class BreakEndRequest(BaseModel):
    notes: Optional[str] = Field(None, max_length=200)


# ==================== LOCATION DRIFT TRACKING SCHEMAS ====================

class LocationDriftRequest(BaseModel):
    """
    Request to record a location drift event
    WVV Protocol: GPS validation (accuracy REQUIRED, max 100m)
    DC Protocol: Immutable records with audit trails
    """
    latitude: float = Field(..., ge=-90, le=90, description="Current GPS latitude")
    longitude: float = Field(..., ge=-180, le=180, description="Current GPS longitude")
    accuracy_m: float = Field(..., ge=0, le=100, description="WVV: GPS accuracy required, max 100m")
    address: Optional[str] = Field(None, max_length=512, description="Optional reverse-geocoded address")
    capture_method: str = Field(default="foreground_poll", description="How location was captured")
    device_info: Optional[dict] = Field(None, description="Device/browser metadata")
    
    @validator('capture_method')
    def validate_capture_method(cls, v):
        valid = ['foreground_poll', 'explicit_capture', 'resume', 'manual']
        if v not in valid:
            raise ValueError(f"Capture method must be one of: {valid}")
        return v


# ==================== TASK MANAGER REVIEW SCHEMAS ====================

class TaskManagerApproveRequest(BaseModel):
    """Request to approve a task (DC: Dual authority - assigner OR manager)"""
    task_id: int = Field(..., gt=0)
    notes: Optional[str] = Field(None, max_length=1000)


class TaskManagerEditRequest(BaseModel):
    """Request to edit and auto-approve a task"""
    task_id: int = Field(..., gt=0)
    progress: Optional[int] = Field(None, ge=0, le=100)
    actual_hours: Optional[float] = Field(None, ge=0, le=1000)
    completion_notes: Optional[str] = Field(None, max_length=2000)
    manager_edit_notes: Optional[str] = Field(None, max_length=1000)


class TaskManagerRejectRequest(BaseModel):
    """Request to reject a task"""
    task_id: int = Field(..., gt=0)
    rejection_reason: str = Field(..., min_length=10, max_length=1000)


class TaskManagerBulkApproveRequest(BaseModel):
    """Request to bulk approve multiple tasks"""
    task_ids: List[int] = Field(..., min_length=1, max_length=50)
    notes: Optional[str] = Field(None, max_length=500)
