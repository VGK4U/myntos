"""
Staff Task Management Models (DC Protocol Compliant)
Single source of truth for all task-related data

Tables:
- staff_tasks: Master task records
- staff_task_assignees: Primary + Secondary assignees (max 3 total)
- staff_task_comments: Discussion thread (immutable)
- staff_task_activity_log: Complete audit trail (immutable)
- staff_task_time_entries: Time logged per task
- staff_task_attachments: File attachments (DC Compliant)
- staff_task_attachment_audit: Image compression audit trail (NEW - DC Dual Evidence)

Key Features:
- Anyone can assign tasks to anyone (no hierarchy restriction)
- Primary (1 mandatory) + Secondary (up to 2) assignees
- Running tasks: Anyone can invite others or reassign
- Full activity logging for audit trail
- File attachments: Max 2 per task, Images up to 5MB (auto-compress to <500KB), Documents 500KB limit
- Cold Storage Archive: Originals moved to cold storage after 30 days (cost optimization + DC compliance)

Created: Nov 26, 2025
Updated: Nov 28, 2025 - Added image compression with cold storage archive
DC Protocol: Write-Verify-Validate at all levels + Dual Evidence for attachments
"""

from sqlalchemy import (
    Column, Integer, String, DateTime, Date, Boolean, Text, 
    ForeignKey, CheckConstraint, Index, Sequence, Numeric
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import pytz

from app.models.base import Base


def get_indian_time():
    """Get current time in Indian timezone (IST)"""
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist).replace(tzinfo=None)


staff_task_id_seq = Sequence('staff_task_id_seq', start=1, increment=1)


class StaffTask(Base):
    """
    Master Task Record
    DC: Single source of truth for all task data
    WVV: All fields validated before insert/update
    """
    __tablename__ = 'staff_tasks'
    
    id = Column(Integer, primary_key=True, index=True)
    task_code = Column(String(32), unique=True, nullable=False, index=True)
    title = Column(String(256), nullable=False)
    description = Column(Text, nullable=True)
    
    category = Column(String(64), nullable=False, default='general')
    priority = Column(String(16), nullable=False, default='medium')
    status = Column(String(32), nullable=False, default='pending')
    
    created_by = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=False, index=True)
    original_assigner_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True, index=True)
    primary_assignee_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=False, index=True)
    
    due_date = Column(Date, nullable=True)
    start_date = Column(Date, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    completion_notes = Column(Text, nullable=True)
    
    estimated_hours = Column(Numeric(5, 2), nullable=True)
    actual_hours = Column(Numeric(5, 2), nullable=True, default=0)
    
    progress = Column(Integer, nullable=False, default=0)
    
    attachments = Column(JSONB, default=list)
    tags = Column(JSONB, default=list)
    
    # Manager Review System
    manager_review_status = Column(String(32), nullable=False, default='pending_review', index=True)
    manager_reviewed_by_employee_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True, index=True)
    manager_review_date = Column(DateTime, nullable=True)
    manager_edit_notes = Column(Text, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    original_values = Column(JSONB, nullable=True)
    
    contact_phone = Column(String(20), nullable=True)
    contact_person_name = Column(String(128), nullable=True)
    
    is_deleted = Column(Boolean, default=False, index=True)
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time)
    
    __table_args__ = (
        CheckConstraint(
            "category IN ('general', 'development', 'support', 'admin', 'meeting', 'review', 'documentation', 'other')",
            name='staff_tasks_category_check'
        ),
        CheckConstraint(
            "priority IN ('low', 'medium', 'high', 'critical')",
            name='staff_tasks_priority_check'
        ),
        CheckConstraint(
            "status IN ('pending', 'in_progress', 'on_hold', 'under_review', 'completed', 'cancelled')",
            name='staff_tasks_status_check'
        ),
        Index('idx_staff_tasks_status_priority', 'status', 'priority'),
        Index('idx_staff_tasks_due_date', 'due_date'),
        Index('idx_staff_tasks_created_at', 'created_at'),
    )
    
    creator = relationship("StaffEmployee", foreign_keys=[created_by], backref="tasks_created")
    original_assigner = relationship("StaffEmployee", foreign_keys=[original_assigner_id])
    primary_assignee = relationship("StaffEmployee", foreign_keys=[primary_assignee_id], backref="tasks_as_primary")
    secondary_assignees = relationship("StaffTaskAssignee", back_populates="task", cascade="all, delete-orphan")
    comments = relationship("StaffTaskComment", back_populates="task", cascade="all, delete-orphan", order_by="StaffTaskComment.created_at")
    activity_logs = relationship("StaffTaskActivityLog", back_populates="task", cascade="all, delete-orphan", order_by="StaffTaskActivityLog.created_at.desc()")
    time_entries = relationship("StaffTaskTimeEntry", back_populates="task", cascade="all, delete-orphan")
    attachment_files = relationship("StaffTaskAttachment", back_populates="task", cascade="all, delete-orphan")
    
    def to_dict(self, include_assignees=True, include_comments=False, include_attachments=True):
        data = {
            "id": self.id,
            "task_code": self.task_code,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "priority": self.priority,
            "status": self.status,
            "created_by": self.created_by,
            "creator_name": self.creator.full_name if self.creator else None,
            "creator_code": self.creator.emp_code if self.creator else None,
            # DC PROTOCOL: Add assigned_by object for "Assigned To Me" page (new field only, no table changes)
            "assigned_by": {
                "id": self.creator.id,
                "full_name": self.creator.full_name,
                "emp_code": self.creator.emp_code
            } if self.creator else None,
            "original_assigner_id": self.original_assigner_id,
            "original_assigner_name": self.original_assigner.full_name if self.original_assigner else None,
            "original_assigner_code": self.original_assigner.emp_code if self.original_assigner else None,
            "primary_assignee_id": self.primary_assignee_id,
            "primary_assignee_name": self.primary_assignee.full_name if self.primary_assignee else None,
            "primary_assignee_code": self.primary_assignee.emp_code if self.primary_assignee else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "completion_notes": self.completion_notes,
            "estimated_hours": float(self.estimated_hours) if self.estimated_hours else None,
            "actual_hours": float(self.actual_hours) if self.actual_hours else 0,
            "progress": self.progress if self.progress is not None else 0,
            "tags": self.tags or [],
            "contact_phone": self.contact_phone,
            "contact_person_name": self.contact_person_name,
            "is_deleted": self.is_deleted,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_overdue": self.due_date and self.due_date < datetime.now().date() and self.status not in ['completed', 'cancelled']
        }
        
        if include_assignees and self.secondary_assignees:
            data["secondary_assignees"] = [
                {
                    "id": sa.id,
                    "employee_id": sa.employee_id,
                    "employee_name": sa.employee.full_name if sa.employee else None,
                    "employee_code": sa.employee.emp_code if sa.employee else None,
                    "assigned_at": sa.assigned_at.isoformat() if sa.assigned_at else None
                }
                for sa in self.secondary_assignees
            ]
        else:
            data["secondary_assignees"] = []
        
        if include_comments and self.comments:
            data["comments"] = [c.to_dict() for c in self.comments]
        
        # DC PROTOCOL: Maintain backward compatibility with legacy JSONB attachments
        # Keep BOTH old and new attachment systems until migration is complete
        if include_attachments:
            # New attachment system (StaffTaskAttachment table)
            if hasattr(self, 'attachment_files'):
                data["attachment_files"] = [
                    att.to_dict() for att in self.attachment_files if not att.is_deleted
                ]
            else:
                data["attachment_files"] = []
            
            # Legacy JSONB attachments (for backward compatibility)
            data["attachments"] = self.attachments or []
            
            # Total count from both sources
            new_count = len(data["attachment_files"])
            legacy_count = len(data["attachments"])
            data["attachment_count"] = new_count + legacy_count
        else:
            data["attachment_files"] = []
            data["attachments"] = []
            data["attachment_count"] = 0
        
        data["total_assignees"] = 1 + len(self.secondary_assignees) if self.secondary_assignees else 1
        
        # DC Protocol (Dec 21, 2025): Multi-Stage Task System - Include phases
        if hasattr(self, 'phases') and self.phases:
            active_phases = [p for p in self.phases if not p.is_deleted]
            data["phases"] = [p.to_dict() for p in sorted(active_phases, key=lambda x: x.phase_number)]
            data["phases_count"] = len(active_phases)
            data["phases_completed"] = sum(1 for p in active_phases if p.phase_status == 'completed')
            # Calculate phase-based progress (if phases exist)
            if active_phases:
                data["phase_progress"] = int((data["phases_completed"] / data["phases_count"]) * 100)
            else:
                data["phase_progress"] = 0
        else:
            data["phases"] = []
            data["phases_count"] = 0
            data["phases_completed"] = 0
            data["phase_progress"] = 0
        
        # DC Protocol: Check if this task is a phase child task
        data["is_phase_task"] = 'phase-task' in (self.tags or [])
        parent_tag = next((t for t in (self.tags or []) if t.startswith('parent-')), None)
        data["parent_task_code"] = parent_tag.replace('parent-', '') if parent_tag else None
        
        return data


class StaffTaskAssignee(Base):
    """
    Secondary Task Assignees (Max 2 per task)
    DC: Separate table for secondary assignees with max 2 constraint
    WVV: Validate count <= 2 before insert at service layer
    """
    __tablename__ = 'staff_task_assignees'
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey('staff_tasks.id', ondelete='CASCADE'), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='CASCADE'), nullable=False, index=True)
    
    assigned_at = Column(DateTime, default=get_indian_time, nullable=False)
    assigned_by = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    
    role = Column(String(32), default='secondary')
    
    __table_args__ = (
        Index('idx_task_assignees_unique', 'task_id', 'employee_id', unique=True),
        CheckConstraint(
            "role IN ('secondary', 'invited', 'reassigned')",
            name='staff_task_assignees_role_check'
        ),
    )
    
    task = relationship("StaffTask", back_populates="secondary_assignees")
    employee = relationship("StaffEmployee", foreign_keys=[employee_id])
    assigner = relationship("StaffEmployee", foreign_keys=[assigned_by])
    
    def to_dict(self):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "employee_id": self.employee_id,
            "employee_name": self.employee.full_name if self.employee else None,
            "employee_code": self.employee.emp_code if self.employee else None,
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "assigned_by": self.assigned_by,
            "assigner_name": self.assigner.full_name if self.assigner else None,
            "role": self.role
        }


class StaffTaskComment(Base):
    """
    Task Discussion Thread (Immutable)
    DC: Comments cannot be deleted, only added for audit trail
    """
    __tablename__ = 'staff_task_comments'
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey('staff_tasks.id', ondelete='CASCADE'), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=False)
    
    comment = Column(Text, nullable=False)
    attachments = Column(JSONB, default=list)
    
    is_system_comment = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False, index=True)
    
    task = relationship("StaffTask", back_populates="comments")
    employee = relationship("StaffEmployee", foreign_keys=[employee_id])
    
    def to_dict(self):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "employee_id": self.employee_id,
            "employee_name": self.employee.full_name if self.employee else "System",
            "employee_code": self.employee.emp_code if self.employee else None,
            "comment": self.comment,
            "attachments": self.attachments or [],
            "is_system_comment": self.is_system_comment,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class StaffTaskActivityLog(Base):
    """
    Complete Task Audit Trail (Immutable)
    DC: Auto-logged on every task modification
    WVV: Cannot be modified after creation
    """
    __tablename__ = 'staff_task_activity_log'
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey('staff_tasks.id', ondelete='CASCADE'), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    
    action = Column(String(64), nullable=False, index=True)
    field_changed = Column(String(64), nullable=True)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    
    details = Column(JSONB, nullable=True)
    ip_address = Column(String(64), nullable=True)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False, index=True)
    
    __table_args__ = (
        CheckConstraint(
            "action IN ('created', 'updated', 'status_changed', 'assigned', 'reassigned', 'invited', 'removed_assignee', 'commented', 'time_logged', 'completed', 'reopened', 'cancelled', 'deleted', 'file_uploaded', 'attachment_added_via_edit', 'attachment_deleted', 'assigner_updated', 'manager_approved', 'manager_bulk_approved', 'manager_edited', 'manager_rejected', 'attachment_previewed', 'phase_reassigned', 'status_change', 'progress_update', 'phase_status_change')",
            name='staff_task_activity_action_check'
        ),
    )
    
    task = relationship("StaffTask", back_populates="activity_logs")
    employee = relationship("StaffEmployee", foreign_keys=[employee_id])
    
    def to_dict(self):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "employee_id": self.employee_id,
            "employee_name": self.employee.full_name if self.employee else "System",
            "action": self.action,
            "field_changed": self.field_changed,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "details": self.details,
            "ip_address": self.ip_address,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class StaffTaskTimeEntry(Base):
    """
    Time Logging per Task
    DC: Track actual time spent on tasks
    WVV: Validate time entries are reasonable
    """
    __tablename__ = 'staff_task_time_entries'
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey('staff_tasks.id', ondelete='CASCADE'), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=False, index=True)
    
    date = Column(Date, nullable=False, index=True)
    hours = Column(Numeric(4, 2), nullable=False)
    description = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time)
    
    __table_args__ = (
        CheckConstraint("hours > 0 AND hours <= 24", name='staff_task_time_hours_check'),
        Index('idx_task_time_date', 'date'),
    )
    
    task = relationship("StaffTask", back_populates="time_entries")
    employee = relationship("StaffEmployee", foreign_keys=[employee_id])
    
    def to_dict(self):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "task_code": self.task.task_code if self.task else None,
            "task_title": self.task.title if self.task else None,
            "employee_id": self.employee_id,
            "employee_name": self.employee.full_name if self.employee else None,
            "employee_code": self.employee.emp_code if self.employee else None,
            "date": self.date.isoformat() if self.date else None,
            "hours": float(self.hours) if self.hours else 0,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class StaffTaskAttachment(Base):
    """
    Task File Attachments
    DC Protocol: New table (does not modify existing staff_tasks table)
    WVV: File validation before storage (type, size, count limits)
    
    Constraints:
    - Max 2 attachments per task
    - Allowed formats: Images (JPEG, PNG, GIF, WebP, BMP, TIFF) up to 5MB, Documents (PDF, DOC, DOCX, XLS, XLSX, PPT, PPTX, TXT) 500KB
    - Images auto-compressed to <500KB for dashboard display
    - Originals archived to cold storage after 30 days
    - Immutable once uploaded (delete-only workflow)
    """
    __tablename__ = 'staff_task_attachments'
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey('staff_tasks.id', ondelete='CASCADE'), nullable=False, index=True)
    
    file_name = Column(String(256), nullable=False)
    file_path = Column(String(512), nullable=False)  # Path to ORIGINAL file (DC: Primary evidence, immutable)
    compressed_path = Column(String(512), nullable=True)  # Path to compressed version (DC: Optimized evidence)
    file_type = Column(String(128), nullable=False)  # MIME type
    file_size = Column(Integer, nullable=False)  # IMMUTABLE: Original upload size (DC: primary evidence, never changes)
    
    # NEW: Image compression tracking (DC Protocol compliance)
    compressed_size_bytes = Column(Integer, nullable=True)  # Compressed file size (NULL until compression completes)
    has_original = Column(Boolean, default=True, nullable=False)  # Track if original exists
    has_compressed = Column(Boolean, default=False, nullable=False)  # Track if compressed version exists
    storage_tier = Column(String(20), default='hot', nullable=False)  # 'hot' or 'cold'
    processing_status = Column(String(20), default='completed', nullable=False)  # 'pending', 'processing', 'completed', 'failed'
    
    # DC Protocol: Checksums for integrity verification (self-contained, no audit join required)
    original_checksum = Column(String(64), nullable=True)  # SHA-256 of original file
    compressed_checksum = Column(String(64), nullable=True)  # SHA-256 of compressed file (NULL if not compressed)
    checksum_algorithm = Column(String(20), default='SHA-256', nullable=False)  # Algorithm used
    
    # DC Protocol: Dual Storage Architecture (object storage vs local)
    original_storage_type = Column(String(20), default='local', nullable=True)  # 'local' or 'object_storage'
    original_storage_key = Column(String(500), nullable=True)  # Actual object storage key (if object_storage)
    
    uploaded_by = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=False)
    uploaded_at = Column(DateTime, nullable=False, default=get_indian_time)
    
    # DC Protocol: Download filename with full context (NEW - Nov 29, 2025)
    download_filename = Column(String(255), nullable=True, index=True)
    uses_new_naming = Column(Boolean, default=False, nullable=False)
    
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    
    __table_args__ = (
        # NEW: 5MB limit for all files (images auto-compress to <500KB, documents validated at application level)
        CheckConstraint("file_size > 0 AND file_size <= 5000000", name='staff_task_attachment_size_check'),
        CheckConstraint("""file_type IN (
            'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp', 'image/bmp', 'image/tiff',
            'application/pdf', 'application/msword', 
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel', 
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.ms-powerpoint', 
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'text/plain'
        )""", name='staff_task_attachment_type_check'),
        CheckConstraint("storage_tier IN ('hot', 'cold')", name='staff_task_attachment_storage_tier_check'),
        CheckConstraint("processing_status IN ('pending', 'processing', 'completed', 'failed')", name='staff_task_attachment_processing_status_check'),
        Index('idx_task_attachment_task', 'task_id', 'is_deleted'),
    )
    
    task = relationship("StaffTask", back_populates="attachment_files")
    uploader = relationship("StaffEmployee", foreign_keys=[uploaded_by])
    
    def to_dict(self):
        # DC: Serve compressed version if available, original as fallback
        from pathlib import Path
        
        # DC PROTOCOL: Safe path extraction (guard against NULL values)
        original_filename = Path(self.file_path).name if self.file_path else None
        compressed_filename = Path(self.compressed_path).name if (self.compressed_path and self.has_compressed) else None
        
        # Determine serving path/size (compressed if available, original otherwise)
        serving_path = self.compressed_path if (self.has_compressed and self.compressed_path) else self.file_path
        serving_size = self.compressed_size_bytes if (self.has_compressed and self.compressed_size_bytes) else self.file_size
        serving_filename = compressed_filename if (self.has_compressed and compressed_filename) else original_filename
        
        return {
            "id": self.id,
            "task_id": self.task_id,
            # Legacy fields (backward compatibility)
            "filename": self.file_name,  # Original upload filename
            "file_type": self.file_type,
            "file_size": self.file_size,  # DC Protocol: IMMUTABLE original upload size (architect-mandated)
            "stored_filename": serving_filename,  # Backward compatibility: filename being served
            # DC Protocol: Immutable original evidence
            "original_path": self.file_path,  # Always available (never changes)
            "original_filename": original_filename,
            "original_size": self.file_size,  # IMMUTABLE: Original upload size
            # DC Protocol: Mutable compressed evidence (NULL if not compressed)
            "compressed_path": self.compressed_path if self.has_compressed else None,
            "compressed_filename": compressed_filename,
            "compressed_size": self.compressed_size_bytes if self.has_compressed else None,
            # DC Protocol: Serving metadata (what client actually gets)
            "serving_path": serving_path,
            "serving_filename": serving_filename,
            "serving_size": serving_size,
            # DC Protocol: Status flags
            "has_original": self.has_original,
            "has_compressed": self.has_compressed,
            "storage_tier": self.storage_tier,
            "processing_status": self.processing_status,
            # DC Protocol: Checksums (integrity verification)
            "original_checksum": self.original_checksum,
            "compressed_checksum": self.compressed_checksum if self.has_compressed else None,
            "checksum_algorithm": self.checksum_algorithm,
            # Upload metadata
            "uploaded_by": self.uploaded_by,
            "uploaded_by_name": self.uploader.full_name if self.uploader else None,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
            "created_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
            # DC Protocol: Download filename (NEW)
            "download_filename": self.download_filename,
            "uses_new_naming": self.uses_new_naming,
            "is_deleted": self.is_deleted
        }


class StaffTaskAttachmentAudit(Base):
    """
    Image Compression Audit Trail (DC Protocol: Dual Evidence)
    
    Purpose:
    - Track original vs compressed file metadata
    - Record quality metrics (SSIM scores)
    - Monitor storage tier transitions (hot → cold)
    - Provide complete audit trail for all image processing
    
    DC Compliance:
    - Immutable record of original upload
    - Checksums for verification
    - Employee attribution (who uploaded, who archived)
    - Complete timestamp trail
    
    WVV Compliance:
    - Quality validation (SSIM scores)
    - Processing duration tracking
    - Storage tier auditing
    """
    __tablename__ = 'staff_task_attachment_audit'
    
    id = Column(Integer, primary_key=True, index=True)
    attachment_id = Column(Integer, ForeignKey('staff_task_attachments.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Original File Metadata (DC: Immutable Evidence)
    original_filename = Column(String(255), nullable=False)
    original_size_bytes = Column(Integer, nullable=False)
    original_checksum = Column(String(64), nullable=False)  # SHA-256
    original_dimensions = Column(String(20), nullable=True)  # e.g., "1920x1080"
    
    # Compressed File Metadata
    compressed_size_bytes = Column(Integer, nullable=False)
    compressed_checksum = Column(String(64), nullable=False)  # SHA-256 of compressed file (DC: verification)
    compressed_dimensions = Column(String(20), nullable=True)
    compression_ratio = Column(Numeric(6, 2), nullable=False)  # e.g., 10.67 (10.67x smaller)
    compression_quality = Column(Integer, nullable=True)  # JPEG quality used (60-95)
    
    # Quality Metrics (WVV: Verification)
    ssim_score = Column(Numeric(4, 3), nullable=True)  # Structural Similarity (0.000-1.000, target >=0.950)
    processing_method = Column(String(50), default='pillow', nullable=False)
    processing_duration_ms = Column(Integer, nullable=True)  # Time taken to compress
    
    # Storage Tier Tracking (DC: Audit Trail)
    storage_tier = Column(String(20), default='hot', nullable=False)  # 'hot' or 'cold'
    archived_at = Column(DateTime, nullable=True)  # When moved to cold storage
    archived_by = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)  # Who triggered archive
    archive_reason = Column(String(100), nullable=True)  # 'auto_30day' or 'manual'
    retrieval_count = Column(Integer, default=0, nullable=False)  # How many times original was retrieved
    last_retrieved_at = Column(DateTime, nullable=True)
    
    # DC: Employee Attribution
    uploaded_by = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=False)
    uploaded_ip = Column(String(45), nullable=True)
    uploaded_device = Column(String(255), nullable=True)
    
    # DC: Immutable Timestamps
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time, nullable=False)
    
    __table_args__ = (
        Index('idx_attachment_audit_attachment', 'attachment_id'),
        Index('idx_attachment_audit_tier', 'storage_tier'),
        Index('idx_attachment_audit_archived', 'archived_at'),
        CheckConstraint("compression_ratio > 0", name='compression_ratio_check'),
        CheckConstraint("ssim_score IS NULL OR (ssim_score >= 0 AND ssim_score <= 1)", name='ssim_score_range'),
    )
    
    attachment = relationship("StaffTaskAttachment", backref="audit_record")
    uploader = relationship("StaffEmployee", foreign_keys=[uploaded_by])
    archiver = relationship("StaffEmployee", foreign_keys=[archived_by])
    
    def to_dict(self):
        return {
            "id": self.id,
            "attachment_id": self.attachment_id,
            "original_filename": self.original_filename,
            "original_size_bytes": self.original_size_bytes,
            "original_size_mb": round(self.original_size_bytes / 1048576, 2),
            "compressed_size_bytes": self.compressed_size_bytes,
            "compressed_size_kb": round(self.compressed_size_bytes / 1024, 2),
            "compression_ratio": float(self.compression_ratio) if self.compression_ratio else None,
            "ssim_score": float(self.ssim_score) if self.ssim_score else None,
            "storage_tier": self.storage_tier,
            "archived_at": self.archived_at.isoformat() if self.archived_at else None,
            "uploaded_by": self.uploaded_by,
            "uploaded_by_name": self.uploader.full_name if self.uploader else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class StaffTaskPhase(Base):
    """
    Multi-Stage Task Phase System (DC Protocol Compliant)
    
    Enables hierarchical task breakdown with:
    - Parent task with multiple phases (stages)
    - Each phase auto-creates a child task for the assignee
    - Status synchronization between child and parent
    - Phase-specific target dates and descriptions
    
    Key Features:
    - Phases are OPTIONAL - existing tasks work unchanged
    - Each phase creates a NEW task for the assignee
    - When assignee updates child task, phase status syncs
    - Parent task progress = % of completed phases
    
    Created: Dec 21, 2025
    DC Protocol: Company segregation via parent task
    WVV Protocol: All phase operations logged to activity trail
    """
    __tablename__ = 'staff_task_phases'
    
    id = Column(Integer, primary_key=True, index=True)
    
    parent_task_id = Column(Integer, ForeignKey('staff_tasks.id', ondelete='CASCADE'), nullable=False, index=True)
    child_task_id = Column(Integer, ForeignKey('staff_tasks.id', ondelete='SET NULL'), nullable=True, index=True)
    
    phase_number = Column(Integer, nullable=False)
    phase_title = Column(String(256), nullable=False)
    phase_description = Column(Text, nullable=True)
    
    phase_assignee_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=False, index=True)
    target_date = Column(Date, nullable=True)
    
    phase_status = Column(String(32), nullable=False, default='pending', index=True)
    completion_notes = Column(Text, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    ordering_token = Column(Integer, nullable=True)
    
    contact_phone = Column(String(20), nullable=True)
    contact_person_name = Column(String(128), nullable=True)
    
    created_by = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=False)
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time)
    
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    
    __table_args__ = (
        CheckConstraint(
            "phase_status IN ('pending', 'in_progress', 'on_hold', 'completed', 'cancelled')",
            name='staff_task_phase_status_check'
        ),
        CheckConstraint("phase_number > 0", name='staff_task_phase_number_check'),
        Index('idx_task_phases_parent', 'parent_task_id', 'is_deleted'),
        Index('idx_task_phases_child', 'child_task_id'),
        Index('idx_task_phases_assignee', 'phase_assignee_id'),
        Index('idx_task_phases_parent_number', 'parent_task_id', 'phase_number', unique=True),
    )
    
    parent_task = relationship("StaffTask", foreign_keys=[parent_task_id], backref="phases")
    child_task = relationship("StaffTask", foreign_keys=[child_task_id])
    assignee = relationship("StaffEmployee", foreign_keys=[phase_assignee_id])
    creator = relationship("StaffEmployee", foreign_keys=[created_by])
    
    def to_dict(self, include_child_task=False):
        data = {
            "id": self.id,
            "parent_task_id": self.parent_task_id,
            "child_task_id": self.child_task_id,
            "phase_number": self.phase_number,
            "phase_title": self.phase_title,
            "phase_description": self.phase_description,
            "phase_assignee_id": self.phase_assignee_id,
            "assignee_name": self.assignee.full_name if self.assignee else None,
            "assignee_code": self.assignee.emp_code if self.assignee else None,
            "target_date": self.target_date.isoformat() if self.target_date else None,
            "phase_status": self.phase_status,
            "completion_notes": self.completion_notes,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "ordering_token": self.ordering_token,
            "contact_phone": self.contact_phone,
            "contact_person_name": self.contact_person_name,
            "created_by": self.created_by,
            "creator_name": self.creator.full_name if self.creator else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_deleted": self.is_deleted,
            "is_overdue": self.target_date and self.target_date < datetime.now().date() and self.phase_status not in ['completed', 'cancelled']
        }
        
        if include_child_task and self.child_task:
            data["child_task"] = {
                "id": self.child_task.id,
                "task_code": self.child_task.task_code,
                "title": self.child_task.title,
                "status": self.child_task.status,
                "progress": self.child_task.progress
            }
            if hasattr(self.child_task, 'secondary_assignees') and self.child_task.secondary_assignees:
                data["secondary_assignees"] = [
                    {
                        "id": sa.id,
                        "employee_id": sa.employee_id,
                        "employee_name": sa.employee.full_name if sa.employee else None,
                        "employee_code": sa.employee.emp_code if sa.employee else None,
                    }
                    for sa in self.child_task.secondary_assignees
                ]
            else:
                data["secondary_assignees"] = []
        else:
            data["secondary_assignees"] = []
        
        return data


class StaffDayPlan(Base):
    __tablename__ = 'staff_day_plans'
    
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey('staff_employees.id', ondelete='CASCADE'), nullable=False, index=True)
    plan_date = Column(Date, nullable=False, index=True)
    
    status = Column(String(32), nullable=False, default='active')
    notes = Column(Text, nullable=True)
    
    total_planned = Column(Integer, nullable=False, default=0)
    total_completed = Column(Integer, nullable=False, default=0)
    total_in_progress = Column(Integer, nullable=False, default=0)
    total_pending = Column(Integer, nullable=False, default=0)
    
    finalized_at = Column(DateTime, nullable=True)
    finalized_by = Column(Integer, ForeignKey('staff_employees.id', ondelete='SET NULL'), nullable=True)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time)
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'finalized', 'cancelled')",
            name='staff_day_plans_status_check'
        ),
        Index('idx_day_plans_employee_date', 'employee_id', 'plan_date', unique=True),
    )
    
    employee = relationship("StaffEmployee", foreign_keys=[employee_id])
    finalizer = relationship("StaffEmployee", foreign_keys=[finalized_by])
    items = relationship("StaffDayPlanItem", back_populates="day_plan", cascade="all, delete-orphan", order_by="StaffDayPlanItem.priority_order")
    
    def to_dict(self, include_items=True):
        data = {
            "id": self.id,
            "employee_id": self.employee_id,
            "employee_name": self.employee.full_name if self.employee else None,
            "employee_code": self.employee.emp_code if self.employee else None,
            "plan_date": self.plan_date.isoformat() if self.plan_date else None,
            "status": self.status,
            "notes": self.notes,
            "total_planned": self.total_planned,
            "total_completed": self.total_completed,
            "total_in_progress": self.total_in_progress,
            "total_pending": self.total_pending,
            "finalized_at": self.finalized_at.isoformat() if self.finalized_at else None,
            "finalized_by": self.finalized_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_items:
            data["items"] = [item.to_dict() for item in (self.items or [])]
        return data


class StaffDayPlanItem(Base):
    __tablename__ = 'staff_day_plan_items'
    
    id = Column(Integer, primary_key=True, index=True)
    day_plan_id = Column(Integer, ForeignKey('staff_day_plans.id', ondelete='CASCADE'), nullable=False, index=True)
    
    item_type = Column(String(16), nullable=False, default='task')
    task_id = Column(Integer, ForeignKey('staff_tasks.id', ondelete='CASCADE'), nullable=False, index=True)
    phase_id = Column(Integer, ForeignKey('staff_task_phases.id', ondelete='SET NULL'), nullable=True, index=True)
    
    priority_order = Column(Integer, nullable=False, default=1)
    
    planned_status = Column(String(32), nullable=True)
    eod_status = Column(String(32), nullable=True)
    eod_progress = Column(Integer, nullable=True)
    eod_notes = Column(Text, nullable=True)
    time_spent_minutes = Column(Integer, default=0, nullable=False)
    
    is_carried_forward = Column(Boolean, default=False, nullable=False)
    carried_from_date = Column(Date, nullable=True)
    
    created_at = Column(DateTime, default=get_indian_time, nullable=False)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time)
    
    __table_args__ = (
        CheckConstraint(
            "item_type IN ('task', 'phase')",
            name='staff_day_plan_items_type_check'
        ),
        Index('idx_day_plan_items_plan', 'day_plan_id', 'priority_order'),
    )
    
    day_plan = relationship("StaffDayPlan", back_populates="items")
    task = relationship("StaffTask", foreign_keys=[task_id])
    phase = relationship("StaffTaskPhase", foreign_keys=[phase_id])
    
    def to_dict(self):
        data = {
            "id": self.id,
            "day_plan_id": self.day_plan_id,
            "item_type": self.item_type,
            "task_id": self.task_id,
            "phase_id": self.phase_id,
            "priority_order": self.priority_order,
            "planned_status": self.planned_status,
            "eod_status": self.eod_status,
            "eod_progress": self.eod_progress,
            "eod_notes": self.eod_notes,
            "time_spent_minutes": self.time_spent_minutes or 0,
            "is_carried_forward": self.is_carried_forward,
            "carried_from_date": self.carried_from_date.isoformat() if self.carried_from_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if self.task:
            data["task_title"] = self.task.title
            data["task_code"] = self.task.task_code
            data["task_status"] = self.task.status
            data["task_priority"] = self.task.priority
            data["task_category"] = self.task.category
            data["task_due_date"] = self.task.due_date.isoformat() if self.task.due_date else None
            data["task_progress"] = self.task.progress
            data["task_assignee_name"] = self.task.primary_assignee.full_name if self.task.primary_assignee else None
            data["task_creator_name"] = self.task.creator.full_name if self.task.creator else None
        if self.phase:
            data["phase_title"] = self.phase.phase_title
            data["phase_number"] = self.phase.phase_number
            data["phase_status"] = self.phase.phase_status
            data["phase_target_date"] = self.phase.target_date.isoformat() if self.phase.target_date else None
        return data


def generate_task_code(db):
    """
    Generate unique task code in format TSK00001, TSK00002, etc.
    DC: Uses max(id) + 1 for reliable code generation without sequence dependency
    WVV: Write-Verify-Validate compliant
    """
    max_task = db.query(StaffTask).order_by(StaffTask.id.desc()).first()
    
    if max_task and max_task.task_code:
        try:
            current_num = int(max_task.task_code.replace('TSK', ''))
            next_id = current_num + 1
        except (ValueError, AttributeError):
            next_id = (max_task.id if max_task.id else 0) + 1
    else:
        next_id = 1
    
    return f"TSK{str(next_id).zfill(5)}"


def log_task_activity(db, task_id, employee_id, action, field_changed=None, 
                       old_value=None, new_value=None, details=None, ip_address=None):
    """
    Helper function to create task activity log entries
    DC: Ensures consistent audit logging across all task operations
    """
    activity = StaffTaskActivityLog(
        task_id=task_id,
        employee_id=employee_id,
        action=action,
        field_changed=field_changed,
        old_value=str(old_value) if old_value is not None else None,
        new_value=str(new_value) if new_value is not None else None,
        details=details,
        ip_address=ip_address
    )
    db.add(activity)
    return activity
