"""
VGK Member Quick Alerts Model
Enables one-click application and immediate support alerts from the VGK4U member portal.
Includes staff atomic claim locks, lifecycle tracking, and SLA escalation tracking.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.base import Base, get_indian_time


class VGKMemberQuickAlert(Base):
    """
    Tracks instant member requests ('I Have an Application' & 'Immediate Support').
    Broadcasts alerts to WhatsApp groups with secure one-click claim links for staff.
    """
    __tablename__ = 'vgk_member_quick_alerts'

    id = Column(Integer, primary_key=True)
    alert_code = Column(String(30), unique=True, nullable=False, index=True)  # e.g. VQA-APP-20261013-0001
    alert_type = Column(String(30), nullable=False, index=True)               # 'APPLICATION' | 'IMMEDIATE_SUPPORT'
    
    # Partner attribution
    partner_id = Column(Integer, ForeignKey('official_partners.id'), nullable=False, index=True)
    partner_code = Column(String(50), nullable=False, index=True)
    partner_name = Column(String(200), nullable=False)
    partner_phone = Column(String(20), nullable=False)
    
    # Multi-tenant isolation
    company_id = Column(Integer, ForeignKey('associated_companies.id'), nullable=True, index=True)
    tenant_id = Column(Integer, ForeignKey('platform_clients.id'), nullable=True, index=True)
    
    # Payload details
    notes = Column(Text, nullable=True)
    priority = Column(String(20), default='High', nullable=False)
    
    # Lifecycle Status: 'PENDING' | 'CLAIMED' | 'IN_PROGRESS' | 'PROCESSED' | 'CANCELLED'
    status = Column(String(30), default='PENDING', nullable=False, index=True)
    
    # Secure atomic claim token
    claim_token = Column(String(64), unique=True, nullable=False, index=True)
    
    # Staff Claim Tracking
    claimed_by_staff_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True, index=True)
    claimed_at = Column(DateTime, nullable=True)
    
    # Resolution / Processing Details
    processed_by_staff_id = Column(Integer, ForeignKey('staff_employees.id'), nullable=True)
    processed_at = Column(DateTime, nullable=True)
    processing_notes = Column(Text, nullable=True)
    
    # Optional cross-links
    linked_crm_lead_id = Column(Integer, nullable=True, index=True)
    linked_ticket_id = Column(Integer, nullable=True, index=True)

    # Waiting for Customer Details & SLA Clock Pause
    waiting_for_details_at = Column(DateTime, nullable=True)
    details_received_at = Column(DateTime, nullable=True)
    total_waiting_seconds = Column(Integer, default=0, nullable=True)
    waiting_notes = Column(Text, nullable=True)

    # Timestamps & Hourly Escalation Tracking (Strictly IST per app.core.timezone)
    created_at = Column(DateTime, default=get_indian_time, nullable=False, index=True)
    updated_at = Column(DateTime, default=get_indian_time, onupdate=get_indian_time)
    reminder_count = Column(Integer, default=0, nullable=False)
    last_reminder_at = Column(DateTime, nullable=True)
    is_escalated_12h = Column(Boolean, default=False, nullable=False, index=True)
    escalated_12h_at = Column(DateTime, nullable=True)

    # Relationships
    partner = relationship('OfficialPartner', foreign_keys=[partner_id])
    claimed_by_staff = relationship('StaffEmployee', foreign_keys=[claimed_by_staff_id])
    processed_by_staff = relationship('StaffEmployee', foreign_keys=[processed_by_staff_id])

    @staticmethod
    def _serialize_ist_iso(dt_val):
        if not dt_val:
            return None
        if dt_val.tzinfo is not None:
            return dt_val.isoformat()
        return f"{dt_val.isoformat()}+05:30"

    @staticmethod
    def _format_ist_display(dt_val):
        if not dt_val:
            return None
        return dt_val.strftime("%d %b %Y, %I:%M %p IST")

    def to_dict(self, now_ist=None, now_utc=None):
        now_ist = now_ist or now_utc or get_indian_time()
        if now_ist and hasattr(now_ist, 'tzinfo') and now_ist.tzinfo:
            now_ist = now_ist.replace(tzinfo=None)

        claimed_staff_name = None
        claimed_emp_code = None
        if self.claimed_by_staff:
            claimed_staff_name = getattr(self.claimed_by_staff, 'full_name', '') or getattr(self.claimed_by_staff, 'username', '')
            claimed_emp_code = getattr(self.claimed_by_staff, 'emp_code', '') or getattr(self.claimed_by_staff, 'employee_code', '')
        
        processed_staff_name = None
        processed_emp_code = None
        if self.processed_by_staff:
            processed_staff_name = getattr(self.processed_by_staff, 'full_name', '') or getattr(self.processed_by_staff, 'username', '')
            processed_emp_code = getattr(self.processed_by_staff, 'emp_code', '') or getattr(self.processed_by_staff, 'employee_code', '')

        created_dt = (self.created_at.replace(tzinfo=None) if self.created_at and self.created_at.tzinfo else self.created_at) or now_ist
        claimed_dt = (self.claimed_at.replace(tzinfo=None) if self.claimed_at and self.claimed_at.tzinfo else self.claimed_at)
        processed_dt = (self.processed_at.replace(tzinfo=None) if self.processed_at and self.processed_at.tzinfo else self.processed_at)
        waiting_dt = (self.waiting_for_details_at.replace(tzinfo=None) if self.waiting_for_details_at and self.waiting_for_details_at.tzinfo else self.waiting_for_details_at)

        pending_since_seconds = max(0, int((now_ist - created_dt).total_seconds()))

        claim_wait_seconds = None
        if claimed_dt and created_dt:
            claim_wait_seconds = max(0, int((claimed_dt - created_dt).total_seconds()))
        elif self.status == 'PENDING':
            claim_wait_seconds = pending_since_seconds

        handling_seconds = None
        acc_waiting_secs = self.total_waiting_seconds or 0

        if self.status == 'WAITING_FOR_DETAILS':
            ref_start = claimed_dt or created_dt
            pause_pt = waiting_dt or now_ist
            raw_elapsed = max(0, int((pause_pt - ref_start).total_seconds())) if ref_start else 0
            handling_seconds = max(0, raw_elapsed - acc_waiting_secs)
        elif self.status in ('CLAIMED', 'IN_PROGRESS'):
            ref_start = claimed_dt or created_dt
            raw_elapsed = max(0, int((now_ist - ref_start).total_seconds())) if ref_start else 0
            handling_seconds = max(0, raw_elapsed - acc_waiting_secs)
        elif self.status == 'PROCESSED' and processed_dt:
            ref_start = claimed_dt or created_dt
            raw_elapsed = max(0, int((processed_dt - ref_start).total_seconds())) if ref_start else 0
            handling_seconds = max(0, raw_elapsed - acc_waiting_secs)

        total_turnaround_seconds = None
        if self.status == 'PROCESSED' and processed_dt and created_dt:
            raw_total = max(0, int((processed_dt - created_dt).total_seconds()))
            total_turnaround_seconds = max(0, raw_total - acc_waiting_secs)

        # 3-Hour (10,800 seconds) Re-Claim SLA Rule:
        # Any application/support request pending > 3h OR claimed/in-progress > 3h without completion
        # can be claimed / re-claimed by anyone else in eligible department staff.
        # EXCLUSION: If currently in WAITING_FOR_DETAILS, SLA clock is frozen and cannot be re-claimed.
        is_reclaimable_3h = False
        reclaim_reason = None
        if self.status == 'PENDING' and pending_since_seconds >= 10800:
            is_reclaimable_3h = True
            reclaim_reason = "Unclaimed for over 3 hours"
        elif self.status in ('CLAIMED', 'IN_PROGRESS'):
            active_duration = handling_seconds if handling_seconds is not None else 0
            if active_duration >= 10800:
                is_reclaimable_3h = True
                reclaim_reason = "Pending completion for over 3 hours (excluding waiting time)"

        display_type = "APPLICATION" if self.alert_type == "APPLICATION" else "SUPPORT"

        return {
            "id": self.id,
            "alert_code": self.alert_code,
            "alert_type": self.alert_type,
            "display_type": display_type,
            "partner_id": self.partner_id,
            "partner_code": self.partner_code,
            "partner_name": self.partner_name,
            "partner_phone": self.partner_phone,
            "company_id": self.company_id,
            "tenant_id": self.tenant_id,
            "notes": self.notes,
            "priority": self.priority,
            "status": self.status,
            "claim_token": self.claim_token,
            "claimed_by_staff_id": self.claimed_by_staff_id,
            "claimed_by_staff_name": claimed_staff_name,
            "claimed_by_emp_code": claimed_emp_code,
            "claimed_at": self._serialize_ist_iso(claimed_dt),
            "claimed_at_ist": self._format_ist_display(claimed_dt),
            "processed_by_staff_id": self.processed_by_staff_id,
            "processed_by_staff_name": processed_staff_name,
            "processed_by_emp_code": processed_emp_code,
            "processed_at": self._serialize_ist_iso(processed_dt),
            "processed_at_ist": self._format_ist_display(processed_dt),
            "processing_notes": self.processing_notes,
            "linked_crm_lead_id": self.linked_crm_lead_id,
            "linked_ticket_id": self.linked_ticket_id,
            "created_at": self._serialize_ist_iso(created_dt),
            "created_at_ist": self._format_ist_display(created_dt),
            "updated_at": self._serialize_ist_iso(self.updated_at),
            "reminder_count": self.reminder_count,
            "is_escalated_12h": self.is_escalated_12h,
            "escalated_12h_at": self._serialize_ist_iso(self.escalated_12h_at),
            "pending_since_seconds": pending_since_seconds,
            "claim_wait_seconds": claim_wait_seconds,
            "handling_seconds": handling_seconds,
            "total_turnaround_seconds": total_turnaround_seconds,
            "is_reclaimable_3h": is_reclaimable_3h,
            "reclaim_reason": reclaim_reason,
            "waiting_for_details_at": self._serialize_ist_iso(self.waiting_for_details_at),
            "waiting_for_details_at_ist": self._format_ist_display(self.waiting_for_details_at),
            "details_received_at": self._serialize_ist_iso(self.details_received_at),
            "total_waiting_seconds": self.total_waiting_seconds or 0,
            "waiting_notes": self.waiting_notes,
        }

