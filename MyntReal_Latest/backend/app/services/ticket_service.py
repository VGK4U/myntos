"""
Support Ticketing Service Layer
Handles all ticket operations, SLA tracking, and escalation logic
DC Protocol Jan 2026: Enhanced with EV Service workflow support
"""

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, and_, or_
from app.models.ticket import ServiceTicket, TicketComment, TicketAssignment, TicketAttachment, TicketLog, ServiceTicketSpareRequest, ServiceTicketBilling, ServiceTicketBillingItem
from app.models.user import User
from app.models.marketplace import MarketspareItem, MarketplacePurchaseOrder, MarketplacePOItem, MarketplaceProcurementRequest, MarketplaceCategoryConfig
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import pytz
import logging
import secrets

logger = logging.getLogger(__name__)


def _derive_ticket_company_id(
    db: Session,
    *,
    service_technician_id: Optional[int] = None,
    service_manager_id: Optional[int] = None,
    partner_id: Optional[int] = None,
) -> Optional[int]:
    """[DC_DAR_003 / Task #53] Derive a ServiceTicket's company_id at write time.

    Precedence matches the startup back-fill in main.py:
      technician.base_company_id → manager.base_company_id → partner.company_id.
    Returns None if no source is available; the column is nullable.
    """
    try:
        from app.models.staff import StaffEmployee
        if service_technician_id:
            cid = db.query(StaffEmployee.base_company_id).filter(
                StaffEmployee.id == service_technician_id
            ).scalar()
            if cid:
                return int(cid)
        if service_manager_id:
            cid = db.query(StaffEmployee.base_company_id).filter(
                StaffEmployee.id == service_manager_id
            ).scalar()
            if cid:
                return int(cid)
        if partner_id:
            from app.models.staff_accounts import OfficialPartner
            cid = db.query(OfficialPartner.company_id).filter(
                OfficialPartner.id == partner_id
            ).scalar()
            if cid:
                return int(cid)
    except Exception as e:
        logger.warning(f"[DC_DAR_003] _derive_ticket_company_id failed: {e}")
    return None

# DC Protocol Jan 2026: Working hours configuration for TAT calculation
IST_TZ = pytz.timezone('Asia/Kolkata')
WORKING_HOURS_START = 9  # 9 AM IST
WORKING_HOURS_END = 18   # 6 PM IST
WORKING_DAYS = [0, 1, 2, 3, 4, 5]  # Mon-Sat (Monday=0, Sunday=6)

# Sub-status workflow states
SUB_STATUS_WORKFLOW = {
    'new': 'acknowledged',
    'acknowledged': 'diagnosing',
    'diagnosing': 'awaiting_spares',  # or 'ready_for_work' if no spares needed
    'awaiting_spares': 'procurement_in_progress',
    'procurement_in_progress': 'ready_for_work',
    'ready_for_work': 'work_complete',
    'work_complete': 'closed'
}


class TicketService:
    """Service for ticketing system operations"""
    
    @staticmethod
    def generate_ticket_id(db=None) -> str:
        """Generate unique ticket ID (format: TKT{YYYYMMDD}{NNNN}).
        DC Protocol Mar 2026: Sequential 4-digit daily counter starting at 0001.
        Falls back to random suffix if db is unavailable.
        """
        today = datetime.utcnow().strftime('%Y%m%d')
        prefix = f"TKT{today}"
        if db is not None:
            try:
                last = (
                    db.query(ServiceTicket.ticket_id)
                    .filter(ServiceTicket.ticket_id.like(f"{prefix}%"))
                    .order_by(ServiceTicket.ticket_id.desc())
                    .first()
                )
                if last and last[0] and len(last[0]) == len(prefix) + 4:
                    seq = int(last[0][len(prefix):]) + 1
                else:
                    seq = 1
                return f"{prefix}{seq:04d}"
            except Exception:
                pass
        random_suffix = secrets.token_hex(2).upper()
        return f"{prefix}{random_suffix}"
    
    @staticmethod
    def calculate_sla_deadline(created_date: datetime) -> datetime:
        """Calculate SLA deadline (24 hours from creation)"""
        return created_date + timedelta(hours=24)
    
    @staticmethod
    def check_sla_status(ticket: ServiceTicket) -> str:
        """Check and update SLA status"""
        if ticket.status in ['Resolved', 'Closed']:
            return ticket.sla_status
        
        now = datetime.utcnow()
        if now > ticket.sla_deadline:
            return 'SLA Breached'
        return 'Within SLA'
    
    @staticmethod
    def create_ticket(
        db: Session,
        user_id: str,
        issue_category: str,
        issue_description: str,
        priority: str = 'Medium',
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> ServiceTicket:
        """Create new support ticket"""
        try:
            ticket_id = TicketService.generate_ticket_id(db=db)
            created_date = datetime.utcnow()
            sla_deadline = TicketService.calculate_sla_deadline(created_date)
            
            ticket = ServiceTicket(
                ticket_id=ticket_id,
                user_id=user_id,
                issue_category=issue_category,
                issue_description=issue_description,
                priority=priority,
                status='Open',
                sub_status='new',
                ticket_type='general',
                created_date=created_date,
                sla_deadline=sla_deadline,
                sla_status='Within SLA',
                ip_address=ip_address,
                user_agent=user_agent,
                # [DC_DAR_003] No technician/manager/partner yet — column stays
                # NULL until acknowledge_ticket() assigns a technician.
                company_id=None,
            )
            
            db.add(ticket)
            db.flush()
            
            # Create activity log
            log = TicketLog(
                ticket_id=ticket.id,
                action_type='Created',
                action_description=f'Ticket created by user {user_id}',
                performed_by=user_id,
                performed_at=created_date,
                new_value='Open',
                ip_address=ip_address
            )
            db.add(log)
            
            db.commit()
            db.refresh(ticket)
            
            logger.info(f"✅ Ticket created: {ticket_id} by user {user_id}")
            return ticket
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating ticket: {str(e)}")
            raise
    
    @staticmethod
    def get_user_tickets(db: Session, user_id: str, status_filter: Optional[str] = None) -> List[ServiceTicket]:
        """Get all tickets for a user"""
        query = db.query(ServiceTicket).filter(ServiceTicket.user_id == user_id)
        
        if status_filter:
            query = query.filter(ServiceTicket.status == status_filter)
        
        tickets = query.order_by(desc(ServiceTicket.created_date)).all()
        
        # Update SLA status for open tickets
        for ticket in tickets:
            if ticket.status not in ['Resolved', 'Closed']:
                new_sla_status = TicketService.check_sla_status(ticket)
                if new_sla_status != ticket.sla_status:
                    ticket.sla_status = new_sla_status
        
        db.commit()
        return tickets
    
    @staticmethod
    def get_admin_tickets(
        db: Session,
        status_filter: Optional[str] = None,
        priority_filter: Optional[str] = None,
        assigned_to: Optional[str] = None
    ) -> List[ServiceTicket]:
        """Get all tickets for admin view"""
        query = db.query(ServiceTicket)
        
        if status_filter:
            query = query.filter(ServiceTicket.status == status_filter)
        if priority_filter:
            query = query.filter(ServiceTicket.priority == priority_filter)
        if assigned_to:
            query = query.filter(ServiceTicket.assigned_to == assigned_to)
        
        tickets = query.order_by(desc(ServiceTicket.created_date)).all()
        
        # Update SLA status
        for ticket in tickets:
            if ticket.status not in ['Resolved', 'Closed']:
                new_sla_status = TicketService.check_sla_status(ticket)
                if new_sla_status != ticket.sla_status:
                    ticket.sla_status = new_sla_status
        
        db.commit()
        return tickets
    
    @staticmethod
    def assign_ticket(
        db: Session,
        ticket_id: int,
        assigned_to: str,
        assigned_by: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Assign ticket to admin"""
        try:
            ticket = db.query(ServiceTicket).filter(ServiceTicket.id == ticket_id).first()
            if not ticket:
                return {"success": False, "message": "Ticket not found"}
            
            old_assignee = ticket.assigned_to
            ticket.assigned_to = assigned_to
            ticket.assigned_date = datetime.utcnow()
            
            if ticket.status == 'Open':
                ticket.status = 'In Progress'
                ticket.in_progress_date = datetime.utcnow()
            
            # Deactivate previous assignments
            db.query(TicketAssignment).filter(
                TicketAssignment.ticket_id == ticket_id,
                TicketAssignment.is_active == True
            ).update({'is_active': False, 'completed_date': datetime.utcnow()})
            
            # Create new assignment
            assignment = TicketAssignment(
                ticket_id=ticket_id,
                assigned_from=assigned_by,
                assigned_to=assigned_to,
                assigned_date=datetime.utcnow(),
                assignment_reason=reason,
                is_active=True
            )
            db.add(assignment)
            
            # Create activity log
            log = TicketLog(
                ticket_id=ticket_id,
                action_type='Assigned',
                action_description=f'Ticket assigned to {assigned_to}',
                performed_by=assigned_by,
                performed_at=datetime.utcnow(),
                old_value=old_assignee,
                new_value=assigned_to,
                comments=reason
            )
            db.add(log)
            
            db.commit()
            
            logger.info(f"✅ Ticket {ticket.ticket_id} assigned to {assigned_to}")
            return {"success": True, "message": "Ticket assigned successfully"}
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error assigning ticket: {str(e)}")
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def add_comment(
        db: Session,
        ticket_id: int,
        user_id: str,
        comment_text: str,
        comment_type: str = 'user_response',
        is_internal: bool = False,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> TicketComment:
        """Add comment to ticket"""
        try:
            comment = TicketComment(
                ticket_id=ticket_id,
                user_id=user_id,
                comment_text=comment_text,
                comment_type=comment_type,
                is_internal=is_internal,
                is_visible_to_user=not is_internal,
                created_at=datetime.utcnow(),
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            db.add(comment)
            
            # Update ticket last response date
            ticket = db.query(ServiceTicket).filter(ServiceTicket.id == ticket_id).first()
            if ticket:
                ticket.last_response_date = datetime.utcnow()
                if comment_type == 'admin_response':
                    ticket.admin_response = comment_text
            
            db.commit()
            db.refresh(comment)
            
            logger.info(f"✅ Comment added to ticket {ticket_id} by {user_id}")
            return comment
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error adding comment: {str(e)}")
            raise
    
    @staticmethod
    def resolve_ticket(
        db: Session,
        ticket_id: int,
        resolved_by: str,
        resolution_summary: str,
        admin_response: Optional[str] = None
    ) -> Dict[str, Any]:
        """Resolve ticket"""
        try:
            ticket = db.query(ServiceTicket).filter(ServiceTicket.id == ticket_id).first()
            if not ticket:
                return {"success": False, "message": "Ticket not found"}
            
            now = datetime.utcnow()
            ticket.status = 'Resolved'
            ticket.resolved_date = now
            ticket.resolution_summary = resolution_summary
            
            if admin_response:
                ticket.admin_response = admin_response
            
            # Calculate resolution time
            resolution_time = (now - ticket.created_date).total_seconds() / 3600
            ticket.resolution_time_hours = resolution_time
            
            # Create activity log
            log = TicketLog(
                ticket_id=ticket_id,
                action_type='Resolved',
                action_description=f'Ticket resolved by {resolved_by}',
                performed_by=resolved_by,
                performed_at=now,
                old_value='In Progress',
                new_value='Resolved',
                comments=resolution_summary
            )
            db.add(log)

            # DC_STOCK_ESTIMATE_RESOLVE_001: Auto-confirm any soft estimate stock entries
            # linked to this ticket so they become real SERVICE_CONSUMPTION deductions.
            # Non-fatal — ticket resolution always succeeds even if stock confirm fails.
            _stock_confirmed = 0
            _stock_errors = []
            try:
                from app.services.stock_service import confirm_estimate_ledger_entry
                from sqlalchemy import text as _text
                _soft_rows = db.execute(_text("""
                    SELECT id FROM stock_ledger
                    WHERE is_estimate = TRUE
                      AND (
                        reference_number = :tkt_str
                        OR (reference_type = 'SERVICE' AND reference_id = :tkt_int)
                      )
                """), {"tkt_str": ticket.ticket_id, "tkt_int": ticket.id}).fetchall()

                for _row in _soft_rows:
                    try:
                        confirm_estimate_ledger_entry(db=db, entry_id=_row.id, updated_by_id=None)
                        _stock_confirmed += 1
                    except Exception as _ce:
                        _stock_errors.append(f"entry {_row.id}: {_ce}")

                if _stock_confirmed:
                    logger.info(
                        f"[DC_STOCK_ESTIMATE] Ticket {ticket.ticket_id} resolved — "
                        f"{_stock_confirmed} estimate stock entries confirmed as real SERVICE_CONSUMPTION"
                    )
                if _stock_errors:
                    logger.warning(
                        f"[DC_STOCK_ESTIMATE] Ticket {ticket.ticket_id}: "
                        f"{len(_stock_errors)} stock confirm error(s): {_stock_errors}"
                    )
            except Exception as _stock_block_err:
                logger.warning(
                    f"[DC_STOCK_ESTIMATE] Stock auto-confirm block failed for ticket "
                    f"{ticket.ticket_id}: {_stock_block_err}"
                )

            db.commit()
            
            logger.info(f"✅ Ticket {ticket.ticket_id} resolved in {resolution_time:.2f} hours")
            msg = "Ticket resolved successfully"
            if _stock_confirmed:
                msg += f" — {_stock_confirmed} estimate stock usage(s) confirmed"
            return {"success": True, "message": msg}
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error resolving ticket: {str(e)}")
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def close_ticket(
        db: Session,
        ticket_id: int,
        closed_by: str,
        customer_satisfaction: Optional[int] = None,
        force_close: bool = False
    ) -> Dict[str, Any]:
        """Close ticket"""
        try:
            ticket = db.query(ServiceTicket).filter(ServiceTicket.id == ticket_id).first()
            if not ticket:
                return {"success": False, "message": "Ticket not found"}
            
            if ticket.status != 'Resolved':
                return {"success": False, "message": "Only resolved tickets can be closed"}
            
            if not force_close:
                pending_spares = db.query(ServiceTicketSpareRequest).filter(
                    ServiceTicketSpareRequest.ticket_id == ticket_id,
                    ServiceTicketSpareRequest.procurement_status.in_(('pending', 'acknowledged', 'ordered'))
                ).count()
                if pending_spares > 0:
                    return {
                        "success": False,
                        "message": f"Cannot close ticket — {pending_spares} spare request(s) are still unresolved (pending/acknowledged/ordered). Cancel or resolve all spares before closing."
                    }
            
            ticket.status = 'Closed'
            ticket.sub_status = 'closed'
            ticket.closed_date = datetime.utcnow()
            
            if customer_satisfaction:
                ticket.customer_satisfaction = customer_satisfaction
            
            # Create activity log
            log = TicketLog(
                ticket_id=ticket_id,
                action_type='Closed',
                action_description=f'Ticket closed by {closed_by}',
                performed_by=closed_by,
                performed_at=datetime.utcnow(),
                old_value='Resolved',
                new_value='Closed'
            )
            db.add(log)
            
            db.commit()
            
            logger.info(f"✅ Ticket {ticket.ticket_id} closed")
            return {"success": True, "message": "Ticket closed successfully"}
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error closing ticket: {str(e)}")
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def get_timeline_stats(db: Session, days: int = 30) -> Dict[str, Any]:
        """Get ticket timeline statistics"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            tickets = db.query(ServiceTicket).filter(
                ServiceTicket.created_date >= cutoff_date
            ).all()
            
            total = len(tickets)
            open_count = sum(1 for t in tickets if t.status == 'Open')
            in_progress = sum(1 for t in tickets if t.status == 'In Progress')
            resolved = sum(1 for t in tickets if t.status == 'Resolved')
            closed = sum(1 for t in tickets if t.status == 'Closed')
            sla_breached = sum(1 for t in tickets if t.sla_status == 'SLA Breached')
            
            resolution_times = [t.resolution_time_hours for t in tickets if t.resolution_time_hours]
            avg_resolution = sum(resolution_times) / len(resolution_times) if resolution_times else None
            
            satisfaction_ratings = [t.customer_satisfaction for t in tickets if t.customer_satisfaction]
            avg_satisfaction = sum(satisfaction_ratings) / len(satisfaction_ratings) if satisfaction_ratings else None
            
            return {
                "total_tickets": total,
                "open_tickets": open_count,
                "in_progress_tickets": in_progress,
                "resolved_tickets": resolved,
                "closed_tickets": closed,
                "sla_breached_count": sla_breached,
                "average_resolution_time": avg_resolution,
                "customer_satisfaction_avg": avg_satisfaction
            }
            
        except Exception as e:
            logger.error(f"Error getting timeline stats: {str(e)}")
            return {}
    
    # DC Protocol Jan 2026: EV Service Workflow Methods
    
    @staticmethod
    def calculate_tat_due(start_time: datetime, working_hours: int) -> datetime:
        """
        Calculate TAT due date based on working hours (9 AM - 6 PM IST, Mon-Sat)
        working_hours: Number of working hours to add
        """
        current = start_time.astimezone(IST_TZ) if start_time.tzinfo else IST_TZ.localize(start_time)
        hours_remaining = working_hours
        
        while hours_remaining > 0:
            if current.weekday() in WORKING_DAYS:
                if WORKING_HOURS_START <= current.hour < WORKING_HOURS_END:
                    hours_in_day = min(hours_remaining, WORKING_HOURS_END - current.hour)
                    hours_remaining -= hours_in_day
                    if hours_remaining <= 0:
                        current = current.replace(hour=current.hour + int(hours_in_day))
                        break
                    current = current.replace(hour=WORKING_HOURS_END)
                elif current.hour < WORKING_HOURS_START:
                    current = current.replace(hour=WORKING_HOURS_START, minute=0, second=0)
                else:
                    current = current + timedelta(days=1)
                    current = current.replace(hour=WORKING_HOURS_START, minute=0, second=0)
            else:
                current = current + timedelta(days=1)
                current = current.replace(hour=WORKING_HOURS_START, minute=0, second=0)
        
        return current.replace(tzinfo=None)
    
    @staticmethod
    def create_service_ticket(
        db: Session,
        user_id: str,
        issue_category: str,
        issue_description: str,
        priority: str = 'Medium',
        ticket_type: str = 'technical',
        source_channel: str = 'website',
        partner_id: Optional[int] = None,
        customer_name: Optional[str] = None,
        customer_phone: Optional[str] = None,
        customer_email: Optional[str] = None,
        customer_address: Optional[str] = None,
        product_name: Optional[str] = None,
        product_serial: Optional[str] = None,
        product_model: Optional[str] = None,
        warranty_status: Optional[str] = None,
        assigned_department_id: Optional[int] = None,
        warranty_invoice_number: Optional[str] = None,
        warranty_sale_date=None,
        warranty_motor_number: Optional[str] = None,
        warranty_chassis_number: Optional[str] = None,
        warranty_model: Optional[str] = None,
        warranty_notes: Optional[str] = None,
        spares_required: bool = False,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        staff_id: Optional[int] = None
    ) -> ServiceTicket:
        """Create new EV service ticket with full customer and product details"""
        try:
            ticket_id = TicketService.generate_ticket_id(db=db)
            created_date = datetime.utcnow()
            sla_deadline = TicketService.calculate_sla_deadline(created_date)
            
            base_tat_hours = 24 if ticket_type == 'technical' else 48
            tat_due = TicketService.calculate_tat_due(created_date, base_tat_hours)
            
            ticket = ServiceTicket(
                ticket_id=ticket_id,
                user_id=user_id,
                issue_category=issue_category,
                issue_description=issue_description,
                priority=priority,
                status='Open',
                created_date=created_date,
                sla_deadline=sla_deadline,
                sla_status='Within SLA',
                ip_address=ip_address,
                user_agent=user_agent,
                ticket_type=ticket_type,
                sub_status='new',
                source_channel=source_channel,
                partner_id=partner_id,
                customer_name=customer_name,
                customer_phone=customer_phone,
                customer_email=customer_email,
                customer_address=customer_address,
                product_name=product_name,
                product_serial=product_serial,
                product_model=product_model,
                warranty_status=warranty_status,
                assigned_department_id=assigned_department_id if assigned_department_id else (17 if ticket_type == 'spares' else None),
                warranty_invoice_number=warranty_invoice_number,
                warranty_sale_date=warranty_sale_date,
                warranty_motor_number=warranty_motor_number,
                warranty_chassis_number=warranty_chassis_number,
                warranty_model=warranty_model,
                warranty_notes=warranty_notes,
                spares_required=spares_required,
                tat_committed_at=created_date,
                tat_due_at=tat_due,
                tat_base_hours=base_tat_hours,
                # [DC_DAR_003] Derive company from partner at creation time;
                # later refreshed when a technician/manager is assigned.
                company_id=_derive_ticket_company_id(db, partner_id=partner_id),
            )
            
            db.add(ticket)
            db.flush()
            
            log = TicketLog(
                ticket_id=ticket.id,
                action_type='Created',
                action_description=f'Service ticket created via {source_channel}',
                performed_by=user_id,
                performed_at=created_date,
                new_value='new',
                ip_address=ip_address,
                staff_performer_id=staff_id
            )
            db.add(log)
            
            db.commit()
            db.refresh(ticket)
            
            logger.info(f"✅ Service ticket created: {ticket_id} - {ticket_type} via {source_channel}")
            return ticket
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating service ticket: {str(e)}")
            raise
    
    @staticmethod
    def acknowledge_ticket(
        db: Session,
        ticket_id: int,
        staff_id: int,
        user_id: str,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Service team acknowledges ticket
        DC Protocol Mar 2026:
        - Sets service_technician_id (FK) so queue shows technician name.
        - Logs an 'Assigned' entry so assignment is audited.
        - For spares tickets: warns if acknowledger is not from Store dept.
        """
        try:
            from app.models.staff import StaffEmployee
            ticket = db.query(ServiceTicket).filter(ServiceTicket.id == ticket_id).first()
            if not ticket:
                return {"success": False, "message": "Ticket not found"}
            
            if ticket.sub_status != 'new':
                return {"success": False, "message": f"Cannot acknowledge ticket in status: {ticket.sub_status}"}

            staff = db.query(StaffEmployee).filter(StaffEmployee.id == staff_id).first()
            staff_name = staff.full_name if staff else f"Staff #{staff_id}"
            dept_name = (staff.department.name if staff and staff.department else '').lower()

            # DC Protocol Mar 2026: Spares tickets must be handled by Store dept
            store_dept_warning = None
            if (ticket.ticket_type or '').lower() == 'spares':
                if 'store' not in dept_name:
                    store_dept_warning = (
                        f"⚠ This is a Spares ticket. It should be assigned to a Store department staff. "
                        f"Current acknowledger ({staff_name}) is from '{staff.department.name if staff and staff.department else 'Unknown'}' dept. "
                        f"Please reassign to a Store dept member."
                    )

            old_status = ticket.sub_status
            ticket.sub_status = 'acknowledged'
            ticket.status = 'In Progress'
            ticket.in_progress_date = datetime.utcnow()
            ticket.service_technician_id = staff_id
            # [DC_DAR_003] Always assign (even None) so we never retain a
            # stale company tag from a prior assignment — preventing
            # cross-company leakage in the DAR.
            ticket.company_id = _derive_ticket_company_id(
                db,
                service_technician_id=staff_id,
                service_manager_id=ticket.service_manager_id,
                partner_id=ticket.partner_id,
            )
            
            now = datetime.utcnow()
            performed_by = user_id if isinstance(user_id, str) and user_id.startswith('MNR') else None

            status_log = TicketLog(
                ticket_id=ticket_id,
                action_type='Status Changed',
                action_description=f'Ticket acknowledged by {staff_name}',
                performed_by=performed_by,
                performed_at=now,
                old_value=old_status,
                new_value='acknowledged',
                comments=notes,
                staff_performer_id=staff_id
            )
            db.add(status_log)

            assign_log = TicketLog(
                ticket_id=ticket_id,
                action_type='Assigned',
                action_description=f'Ticket assigned to {staff_name} on acknowledgment',
                performed_by=performed_by,
                performed_at=now,
                old_value='Unassigned',
                new_value=staff_name,
                staff_performer_id=staff_id
            )
            db.add(assign_log)
            
            db.commit()
            logger.info(f"✅ Ticket {ticket.ticket_id} acknowledged & assigned to {staff_name} (id={staff_id})")
            result = {"success": True, "message": "Ticket acknowledged successfully", "technician_name": staff_name}
            if store_dept_warning:
                result["store_dept_warning"] = store_dept_warning
            return result
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error acknowledging ticket: {str(e)}")
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def diagnose_ticket(
        db: Session,
        ticket_id: int,
        staff_id: int,
        user_id: str,
        diagnosis_notes: str,
        spares_required: bool = False
    ) -> Dict[str, Any]:
        """Complete diagnosis and determine if spares are needed"""
        try:
            ticket = db.query(ServiceTicket).filter(ServiceTicket.id == ticket_id).first()
            if not ticket:
                return {"success": False, "message": "Ticket not found"}
            
            if ticket.sub_status != 'acknowledged':
                return {"success": False, "message": f"Cannot diagnose ticket in status: {ticket.sub_status}"}
            
            old_status = ticket.sub_status
            ticket.diagnosed_at = datetime.utcnow()
            ticket.diagnosis_notes = diagnosis_notes
            ticket.spares_required = spares_required
            
            if spares_required:
                ticket.sub_status = 'awaiting_spares'
                ticket.tat_extension_hours = 48
                new_tat = TicketService.calculate_tat_due(datetime.utcnow(), 48)
                ticket.tat_due_at = new_tat
            else:
                ticket.sub_status = 'ready_for_work'
            
            log = TicketLog(
                ticket_id=ticket_id,
                action_type='Status Changed',
                action_description=f'Diagnosis complete - Spares required: {spares_required}',
                performed_by=user_id if isinstance(user_id, str) and user_id.startswith('MNR') else None,
                performed_at=datetime.utcnow(),
                old_value=old_status,
                new_value=ticket.sub_status,
                comments=diagnosis_notes,
                staff_performer_id=staff_id
            )
            db.add(log)
            
            db.commit()
            logger.info(f"✅ Ticket {ticket.ticket_id} diagnosed - spares_required: {spares_required}")
            return {"success": True, "message": "Diagnosis recorded successfully", "spares_required": spares_required}
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error diagnosing ticket: {str(e)}")
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def request_spares(
        db: Session,
        ticket_id: int,
        staff_id: int,
        user_id: str,
        spare_items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Request spare parts for a ticket.
        Supports two modes per item:
        A) Marketplace pick: item has 'marketplace_spare_id' → WVV: compute pricing,
           auto-create ZYPO (in-stock) or ZYPR (out-of-stock), link to spare_request.
        B) Free-text (is_custom=True): legacy path unchanged.
        """
        from app.services.marketplace_pricing import enrich_product_with_pricing

        def _gen_po_number(company_id: int) -> tuple:
            from sqlalchemy import text as _text
            ym = datetime.utcnow().strftime('%Y%m')
            prefix = f'ZYPO-{ym}-'
            row = db.execute(_text(
                "SELECT COUNT(*)+1 FROM marketplace_purchase_orders WHERE po_number LIKE :pfx AND company_id=:cid"
            ), {'pfx': prefix + '%', 'cid': company_id}).fetchone()
            cnt = int(row[0]) if row else 1
            po_num = f'{prefix}{cnt:04d}'
            while db.query(MarketplacePurchaseOrder).filter_by(po_number=po_num).first():
                cnt += 1
                po_num = f'{prefix}{cnt:04d}'
            return po_num, cnt

        def _gen_proc_number(company_id: int) -> str:
            from sqlalchemy import text as _text
            ym = datetime.utcnow().strftime('%Y%m')
            prefix = f'ZYPR-{ym}-'
            row = db.execute(_text(
                "SELECT COUNT(*)+1 FROM marketplace_procurement_requests WHERE procurement_number LIKE :pfx AND company_id=:cid"
            ), {'pfx': prefix + '%', 'cid': company_id}).fetchone()
            cnt = int(row[0]) if row else 1
            proc_num = f'{prefix}{cnt:04d}'
            while db.query(MarketplaceProcurementRequest).filter_by(procurement_number=proc_num).first():
                cnt += 1
                proc_num = f'{prefix}{cnt:04d}'
            return proc_num

        try:
            ticket = db.query(ServiceTicket).filter(ServiceTicket.id == ticket_id).first()
            if not ticket:
                return {"success": False, "message": "Ticket not found"}

            # DC Protocol Mar 2026: Allow spare requests from any active ticket state except Resolved/Closed
            if ticket.status in ['Resolved', 'Closed']:
                return {"success": False, "message": f"Cannot request spares — ticket is {ticket.status}"}

            ticket.spare_requested_at = datetime.utcnow()
            ticket.sub_status = 'awaiting_spares'

            company_id = getattr(ticket, 'company_id', None) or 1
            source_type = 'technical_ticket' if ticket.ticket_type == 'technical' else 'service_ticket'

            spare_requests = []
            created_pos = []
            created_procs = []

            for item in spare_items:
                mkt_spare_id = item.get('marketplace_spare_id')
                discount_mode = item.get('discount_mode')
                qty = int(item.get('quantity', 1))

                marketplace_po_id = None
                marketplace_procurement_id = None
                unit_price = 0.0
                gst_rate = 18.0
                gst_amount = 0.0
                total_with_gst = 0.0
                hsn_code = item.get('hsn_code')
                spare_name = item.get('name', '')
                spare_code = item.get('code', '')
                is_custom = mkt_spare_id is None and item.get('stock_item_id') is None

                if mkt_spare_id:
                    # ── WVV: READ ──────────────────────────────────────────────
                    mkt_spare = db.query(MarketspareItem).filter(
                        MarketspareItem.id == mkt_spare_id,
                        MarketspareItem.company_id == company_id,
                        MarketspareItem.is_active == True,
                    ).first()
                    if not mkt_spare:
                        logger.warning(f'[SPARE-PICK] marketplace_spare_id={mkt_spare_id} not found, falling back to custom (ticket={getattr(ticket, "ticket_number", None) or ticket_id}, item="{spare_name}")')
                        is_custom = True
                    else:
                        # ── WVV: VERIFY ────────────────────────────────────────
                        cfg = db.query(MarketplaceCategoryConfig).filter(
                            MarketplaceCategoryConfig.company_id == company_id,
                            MarketplaceCategoryConfig.category_name == mkt_spare.category_name,
                        ).first()
                        cfg_dict = cfg.to_dict() if cfg else {}
                        enriched = enrich_product_with_pricing(
                            mkt_spare.to_dict(), cfg_dict, discount_mode
                        )
                        unit_price = float(enriched.get('net_before_tax', enriched.get('dealer_price', 0)))
                        gst_rate = float(enriched.get('gst_percent', 18))
                        gst_amount = float(enriched.get('gst_amount', 0))
                        total_with_gst = float(enriched.get('final_price', 0))
                        hsn_code = enriched.get('hsn_code') or hsn_code
                        spare_name = mkt_spare.name
                        spare_code = mkt_spare.sku
                        aq = int(mkt_spare.available_qty or 0)

                        # ── WVV: WRITE (PO or Procurement) ────────────────────
                        if aq >= qty:
                            # In-stock → auto-create ZYPO (do NOT decrement available_qty;
                            # decremented only on physical release per DC Protocol)
                            po_num, po_cnt = _gen_po_number(company_id)
                            po = MarketplacePurchaseOrder(
                                po_number=po_num,
                                po_count=po_cnt,
                                customer_name=f'Service Ticket {ticket.ticket_id}',
                                customer_phone='N/A',
                                customer_type='service_ticket',
                                discount_mode=discount_mode,
                                discount_name=f'{discount_mode.upper()} discount' if discount_mode else None,
                                total_items=1,
                                total_ordered_qty=qty,
                                total_value=total_with_gst * qty,
                                status='confirmed',
                                notes=f'Auto-created for service ticket {ticket.ticket_id}',
                                source_type=source_type,
                                source_ticket_id=ticket.id,
                                company_id=company_id,
                            )
                            db.add(po)
                            db.flush()
                            # ── Store task hook ──────────────────────────
                            try:
                                from app.services.store_task_service import add_po_phase as _stk_po
                                _stk_po(db, po, company_id)
                            except Exception as _e:
                                logger.error(f'[StoreTask] ticket_service PO hook: {_e}')
                            # ────────────────────────────────────────────

                            po_item = MarketplacePOItem(
                                po_id=po.id,
                                sku=spare_code,
                                product_name=spare_name,
                                category_name=mkt_spare.category_name,
                                brand=mkt_spare.brand,
                                specifications=mkt_spare.specifications,
                                color=mkt_spare.color,
                                ordered_qty=qty,
                                dealer_price=float(mkt_spare.dealer_price or 0),
                                discount_amount=float(enriched.get('discount_amount', 0)),
                                net_price=unit_price,
                                gst_percent=gst_rate,
                                gst_amount=gst_amount * qty,
                                unit_final_price=total_with_gst,
                                line_total=total_with_gst * qty,
                                stock_available=aq,
                                procurement_required=False,
                                company_id=company_id,
                            )
                            db.add(po_item)
                            db.flush()

                            marketplace_po_id = po.id
                            created_pos.append(po_num)
                            logger.info(f'[SPARE-PICK] ✅ ZYPO {po_num} created for spare {spare_code} (ticket {ticket.ticket_id})')

                        else:
                            # Out-of-stock → auto-create ZYPR
                            # Check for open procurement already
                            existing_proc = db.query(MarketplaceProcurementRequest).filter(
                                MarketplaceProcurementRequest.sku == spare_code,
                                MarketplaceProcurementRequest.company_id == company_id,
                                MarketplaceProcurementRequest.status.in_(['pending', 'ordered']),
                            ).first()

                            if not existing_proc:
                                proc_num = _gen_proc_number(company_id)
                                proc = MarketplaceProcurementRequest(
                                    procurement_number=proc_num,
                                    sku=spare_code,
                                    product_name=spare_name,
                                    ordered_qty=qty,
                                    available_qty=aq,
                                    shortfall_qty=qty - aq,
                                    status='pending',
                                    triggered_by=source_type,
                                    source_type=source_type,
                                    source_ticket_id=ticket.id,
                                    procurement_notes=f'Auto-raised: service ticket {ticket.ticket_id}',
                                    company_id=company_id,
                                )
                                db.add(proc)
                                db.flush()
                                # ── Store task hook ──────────────────────
                                try:
                                    from app.services.store_task_service import add_pr_phase as _stk_pr
                                    _stk_pr(db, proc, company_id)
                                except Exception as _e:
                                    logger.error(f'[StoreTask] ticket_service PR hook: {_e}')
                                # ─────────────────────────────────────────
                                marketplace_procurement_id = proc.id
                                created_procs.append(proc_num)
                                logger.info(f'[SPARE-PICK] ⚠️ ZYPR {proc_num} created for out-of-stock spare {spare_code}')
                            else:
                                marketplace_procurement_id = existing_proc.id
                                logger.info(f'[SPARE-PICK] Reusing existing ZYPR for {spare_code}')

                            # ── Also create ZYPO with status='procurement_pending' ─────
                            # So the order is visible on the PO page while procurement runs
                            _pr_ref = proc_num if not existing_proc else (
                                existing_proc.procurement_number if existing_proc else '')
                            po_num, po_cnt = _gen_po_number(company_id)
                            po_oos = MarketplacePurchaseOrder(
                                po_number=po_num,
                                po_count=po_cnt,
                                customer_name=f'Service Ticket {ticket.ticket_id}',
                                customer_phone='N/A',
                                customer_type='service_ticket',
                                discount_mode=discount_mode,
                                total_items=1,
                                total_ordered_qty=qty,
                                total_value=round(total_with_gst * qty, 2),
                                status='procurement_pending',
                                notes=f'Awaiting procurement for ticket {ticket.ticket_id} | {_pr_ref}',
                                source_type=source_type,
                                source_ticket_id=ticket.id,
                                company_id=company_id,
                            )
                            db.add(po_oos)
                            db.flush()
                            try:
                                from app.services.store_task_service import add_po_phase as _stk_po_oos
                                _stk_po_oos(db, po_oos, company_id)
                            except Exception as _e:
                                logger.error(f'[StoreTask] ticket_service oos PO hook: {_e}')
                            po_item_oos = MarketplacePOItem(
                                po_id=po_oos.id,
                                sku=spare_code,
                                product_name=spare_name,
                                category_name=mkt_spare.category_name,
                                brand=mkt_spare.brand,
                                specifications=mkt_spare.specifications,
                                color=mkt_spare.color,
                                ordered_qty=qty,
                                dealer_price=float(mkt_spare.dealer_price or 0),
                                discount_amount=float(enriched.get('discount_amount', 0)),
                                net_price=unit_price,
                                gst_percent=gst_rate,
                                gst_amount=gst_amount * qty,
                                unit_final_price=total_with_gst,
                                line_total=round(total_with_gst * qty, 2),
                                stock_available=aq,
                                procurement_required=True,
                                company_id=company_id,
                            )
                            db.add(po_item_oos)
                            db.flush()
                            marketplace_po_id = po_oos.id
                            created_pos.append(po_num)
                            logger.info(f'[SPARE-PICK] 🔄 ZYPO {po_num} (procurement_pending) for out-of-stock spare {spare_code}')
                            # ──────────────────────────────────────────────────────────

                # ── Draft ZYPO for custom/free-text spares ────────────────────
                if is_custom and not marketplace_po_id:
                    po_num, po_cnt = _gen_po_number(company_id)
                    _est_cost = float(item.get('estimated_cost') or unit_price or 0)
                    _gst_pct = float(gst_rate or 18)
                    _gst_val = round(_est_cost * _gst_pct / 100, 2)
                    _total   = round((_est_cost + _gst_val) * qty, 2)
                    po = MarketplacePurchaseOrder(
                        po_number=po_num,
                        po_count=po_cnt,
                        customer_name=f'Service Ticket {ticket.ticket_id}',
                        customer_phone='N/A',
                        customer_type='service_ticket',
                        discount_mode=discount_mode,
                        total_items=1,
                        total_ordered_qty=qty,
                        total_value=_total,
                        status='draft',
                        notes=f'Draft PO for custom spare on ticket {ticket.ticket_id}',
                        source_type=source_type,
                        source_ticket_id=ticket.id,
                        company_id=company_id,
                    )
                    db.add(po)
                    db.flush()
                    # ── Store task hook ──────────────────────────────────
                    try:
                        from app.services.store_task_service import add_po_phase as _stk_po2
                        _stk_po2(db, po, company_id)
                    except Exception as _e:
                        logger.error(f'[StoreTask] ticket_service draft PO hook: {_e}')
                    # ────────────────────────────────────────────────────
                    po_item = MarketplacePOItem(
                        po_id=po.id,
                        sku=spare_code or 'CUSTOM',
                        product_name=spare_name or 'Custom Spare',
                        ordered_qty=qty,
                        dealer_price=_est_cost,
                        net_price=_est_cost,
                        gst_percent=_gst_pct,
                        gst_amount=_gst_val * qty,
                        unit_final_price=round(_est_cost + _gst_val, 2),
                        line_total=_total,
                        stock_available=0,
                        procurement_required=True,
                        company_id=company_id,
                    )
                    db.add(po_item)
                    db.flush()
                    marketplace_po_id = po.id
                    created_pos.append(po_num)
                    logger.info(f'[SPARE-PICK] ✅ Draft ZYPO {po_num} created for custom spare "{spare_name}" (ticket {ticket.ticket_id})')

                # ── Create the spare request ───────────────────────────────────
                # Parse warranty fields from item payload
                _is_warranty        = bool(item.get('is_warranty', False))
                _warranty_sale_date = None
                if item.get('warranty_sale_date'):
                    try:
                        from datetime import date as _date
                        _warranty_sale_date = _date.fromisoformat(str(item['warranty_sale_date']))
                    except Exception:
                        pass
                spare_request = ServiceTicketSpareRequest(
                    ticket_id=ticket_id,
                    spare_item_name=spare_name,
                    spare_item_code=spare_code,
                    spare_description=item.get('description'),
                    quantity_required=qty,
                    estimated_cost=item.get('estimated_cost') or (unit_price or None),
                    unit_price=unit_price,
                    # FIX-4: also write net_before_tax so auto-populate always finds it first
                    net_before_tax=(unit_price if unit_price and unit_price > 0 else None),
                    gst_rate=gst_rate,
                    gst_amount=gst_amount,
                    total_with_gst=total_with_gst,
                    hsn_code=hsn_code,
                    stock_item_id=item.get('stock_item_id'),
                    is_custom=is_custom,
                    original_item_name=(spare_name if is_custom else None),
                    request_notes=item.get('notes'),
                    requested_by_id=staff_id,
                    procurement_status='pending',
                    marketplace_spare_id=mkt_spare_id,
                    marketplace_po_id=marketplace_po_id,
                    marketplace_procurement_id=marketplace_procurement_id,
                    discount_mode=discount_mode,
                    # Warranty fields (DC Protocol Mar 2026)
                    is_warranty=_is_warranty,
                    warranty_invoice_number=item.get('warranty_invoice_number'),
                    warranty_sale_date=_warranty_sale_date,
                    warranty_motor_number=item.get('warranty_motor_number'),
                    warranty_chassis_number=item.get('warranty_chassis_number'),
                    warranty_model=item.get('warranty_model'),
                    warranty_notes=item.get('warranty_notes'),
                )
                db.add(spare_request)
                db.flush()
                spare_requests.append(spare_request)

            log = TicketLog(
                ticket_id=ticket_id,
                action_type='Updated',
                action_description=f'Spare parts requested: {len(spare_items)} items'
                    + (f'; {len(created_pos)} ZYPO(s) created' if created_pos else '')
                    + (f'; {len(created_procs)} ZYPR(s) raised' if created_procs else ''),
                performed_by=user_id if isinstance(user_id, str) and str(user_id).startswith('MNR') else None,
                performed_at=datetime.utcnow(),
                new_value='awaiting_spares',
                staff_performer_id=staff_id
            )
            db.add(log)

            db.commit()
            logger.info(f'✅ {len(spare_items)} spare requests created for ticket {ticket.ticket_id}')
            sr_list = []
            for sr in spare_requests:
                d = {'id': sr.id, 'name': sr.spare_item_name}
                if sr.marketplace_po_id:
                    d['marketplace_po_id'] = sr.marketplace_po_id
                if sr.marketplace_procurement_id:
                    d['marketplace_procurement_id'] = sr.marketplace_procurement_id
                sr_list.append(d)
            return {
                "success": True,
                "message": f"{len(spare_items)} spare parts requested",
                "spare_count": len(spare_items),
                "spare_requests": sr_list,
                "zypo_created": created_pos,
                "zypr_raised": created_procs,
            }

        except Exception as e:
            db.rollback()
            logger.error(f'Error requesting spares: {str(e)}')
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def acknowledge_spare_request(
        db: Session,
        spare_request_id: int,
        staff_id: int,
        user_id: str,
        stock_available: bool,
        stock_quantity: int = 0,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Procurement team acknowledges spare request"""
        try:
            spare = db.query(ServiceTicketSpareRequest).filter(ServiceTicketSpareRequest.id == spare_request_id).first()
            if not spare:
                return {"success": False, "message": "Spare request not found"}
            
            spare.acknowledged_at = datetime.utcnow()
            spare.acknowledged_by_id = staff_id
            spare.acknowledgment_notes = notes
            spare.stock_available = stock_available
            spare.stock_quantity = stock_quantity
            
            if stock_available and stock_quantity >= spare.quantity_required:
                spare.procurement_status = 'acknowledged'
            else:
                spare.procurement_status = 'ordered'
            
            ticket = spare.ticket
            if ticket:
                ticket.spare_acknowledged_at = datetime.utcnow()
                ticket.sub_status = 'procurement_in_progress'
                
                log = TicketLog(
                    ticket_id=ticket.id,
                    action_type='Updated',
                    action_description=f'Spare acknowledged - Stock available: {stock_available}',
                    performed_by=user_id if isinstance(user_id, str) and str(user_id).startswith('MNR') else None,
                    performed_at=datetime.utcnow(),
                    new_value='procurement_in_progress',
                    comments=notes,
                    staff_performer_id=staff_id
                )
                db.add(log)
            
            db.commit()
            logger.info(f"✅ Spare request {spare_request_id} acknowledged - stock: {stock_available}")
            return {"success": True, "message": "Spare request acknowledged"}
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error acknowledging spare: {str(e)}")
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def release_spares(
        db: Session,
        spare_request_id: int,
        staff_id: int,
        user_id: str,
        actual_cost: Optional[float] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Release spare parts for a ticket"""
        try:
            spare = db.query(ServiceTicketSpareRequest).filter(ServiceTicketSpareRequest.id == spare_request_id).first()
            if not spare:
                return {"success": False, "message": "Spare request not found"}
            
            spare.released_at = datetime.utcnow()
            spare.released_by_id = staff_id
            spare.release_notes = notes
            spare.procurement_status = 'released'
            if actual_cost:
                spare.actual_cost = actual_cost

            # ── Decrement marketplace stock on physical release (DC Protocol) ──
            if spare.marketplace_spare_id and spare.marketplace_po_id:
                from app.models.marketplace import MarketspareItem as _MS
                mkt_item = db.query(_MS).filter(_MS.id == spare.marketplace_spare_id).first()
                if mkt_item:
                    qty_to_decrement = int(spare.quantity_required or 1)
                    mkt_item.available_qty = max(0, int(mkt_item.available_qty or 0) - qty_to_decrement)
                    logger.info(f'[RELEASE] Decremented marketplace stock for SKU {mkt_item.sku} by {qty_to_decrement} → {mkt_item.available_qty}')

            ticket = spare.ticket
            if ticket:
                all_spares = db.query(ServiceTicketSpareRequest).filter(
                    ServiceTicketSpareRequest.ticket_id == ticket.id
                ).all()
                
                all_released = all(s.procurement_status == 'released' for s in all_spares)
                
                if all_released:
                    ticket.spare_released_at = datetime.utcnow()
                    ticket.sub_status = 'ready_for_work'
                    
                    log = TicketLog(
                        ticket_id=ticket.id,
                        action_type='Status Changed',
                        action_description='All spares released - Ready for work',
                        performed_by=user_id if isinstance(user_id, str) and str(user_id).startswith('MNR') else None,
                        performed_at=datetime.utcnow(),
                        old_value='procurement_in_progress',
                        new_value='ready_for_work',
                        staff_performer_id=staff_id
                    )
                    db.add(log)
            
            db.commit()
            logger.info(f"✅ Spare request {spare_request_id} released")
            return {"success": True, "message": "Spare released successfully"}
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error releasing spare: {str(e)}")
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def complete_work(
        db: Session,
        ticket_id: int,
        staff_id: int,
        user_id: str,
        resolution_summary: str
    ) -> Dict[str, Any]:
        """Mark service work as complete"""
        try:
            ticket = db.query(ServiceTicket).filter(ServiceTicket.id == ticket_id).first()
            if not ticket:
                return {"success": False, "message": "Ticket not found"}
            
            if ticket.sub_status != 'ready_for_work':
                return {"success": False, "message": f"Cannot complete work in status: {ticket.sub_status}"}
            
            old_status = ticket.sub_status
            ticket.sub_status = 'work_complete'
            ticket.status = 'Resolved'
            ticket.resolved_date = datetime.utcnow()
            ticket.resolution_summary = resolution_summary
            
            resolution_time = (datetime.utcnow() - ticket.created_date).total_seconds() / 3600
            ticket.resolution_time_hours = resolution_time
            
            log = TicketLog(
                ticket_id=ticket_id,
                action_type='Resolved',
                action_description='Service work completed',
                performed_by=user_id if isinstance(user_id, str) and user_id.startswith('MNR') else None,
                performed_at=datetime.utcnow(),
                old_value=old_status,
                new_value='work_complete',
                comments=resolution_summary,
                staff_performer_id=staff_id
            )
            db.add(log)
            
            db.commit()
            logger.info(f"✅ Ticket {ticket.ticket_id} work completed in {resolution_time:.2f} hours")
            return {"success": True, "message": "Work completed successfully"}
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error completing work: {str(e)}")
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def close_service_ticket(
        db: Session,
        ticket_id: int,
        staff_id: int,
        user_id: str,
        customer_satisfaction: Optional[int] = None,
        force_close: bool = False
    ) -> Dict[str, Any]:
        """Close service ticket after billing is complete"""
        try:
            ticket = db.query(ServiceTicket).filter(ServiceTicket.id == ticket_id).first()
            if not ticket:
                return {"success": False, "message": "Ticket not found"}
            
            if ticket.sub_status != 'work_complete':
                return {"success": False, "message": f"Cannot close ticket in status: {ticket.sub_status}"}
            
            if not force_close:
                pending_spares = db.query(ServiceTicketSpareRequest).filter(
                    ServiceTicketSpareRequest.ticket_id == ticket_id,
                    ServiceTicketSpareRequest.procurement_status.in_(('pending', 'acknowledged', 'ordered'))
                ).count()
                if pending_spares > 0:
                    return {
                        "success": False,
                        "message": f"Cannot close ticket — {pending_spares} spare request(s) are still unresolved (pending/acknowledged/ordered). Cancel or resolve all spares before closing."
                    }
            
            old_status = ticket.sub_status
            ticket.sub_status = 'closed'
            ticket.status = 'Closed'
            ticket.closed_date = datetime.utcnow()
            
            if customer_satisfaction:
                ticket.customer_satisfaction = customer_satisfaction
            
            # DC Protocol Jan 2026: For staff actions, use staff_performer_id only
            # performed_by expects String(12) FK to user.id (MNR IDs), not integer staff_id
            log = TicketLog(
                ticket_id=ticket_id,
                action_type='Closed',
                action_description='Service ticket closed',
                performed_by=None,  # Staff action - no MNR user ID
                performed_at=datetime.utcnow(),
                old_value=old_status,
                new_value='closed',
                staff_performer_id=staff_id
            )
            db.add(log)
            
            db.commit()
            logger.info(f"✅ Ticket {ticket.ticket_id} closed")
            return {"success": True, "message": "Ticket closed successfully"}
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error closing ticket: {str(e)}")
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def get_service_queue(
        db: Session,
        service_center_id: Optional[int] = None,
        sub_status_filter: Optional[str] = None,
        ticket_type_filter: Optional[str] = None,
        staff_id_filter: Optional[int] = None
    ) -> List[ServiceTicket]:
        """Get tickets for service team queue
        DC Protocol Mar 2026: Eager-load relationships to guarantee technician/manager
        names are always available without lazy-load failures in to_dict().
        DC Protocol Mar 2026 (RBAC): staff_id_filter restricts results to tickets where
        the caller is the assigned service_manager OR service_technician.
        Privileged roles (key_leadership, vgk4u, manager, service_head) pass None to see all tickets.
        """
        from app.models.staff_accounts import OfficialPartner
        from app.models.staff import StaffEmployee
        from sqlalchemy import or_
        from datetime import datetime, timedelta
        # DC-SQ-PERF-001: Eager-load spare_requests to avoid N+1 (one query per ticket)
        # DC-SQ-PERF-002: Closed/cancelled limited to last 30 days to avoid full-table scan
        _thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        query = db.query(ServiceTicket).options(
            joinedload(ServiceTicket.service_technician),
            joinedload(ServiceTicket.service_manager),
            joinedload(ServiceTicket.partner),
            joinedload(ServiceTicket.spare_requests),
        ).filter(
            or_(
                ServiceTicket.sub_status.in_(['new', 'acknowledged', 'diagnosing', 'awaiting_spares', 'procurement_in_progress', 'ready_for_work', 'work_complete']),
                and_(
                    ServiceTicket.sub_status.in_(['closed', 'cancelled']),
                    ServiceTicket.created_date >= _thirty_days_ago
                )
            )
        )
        
        if service_center_id:
            query = query.filter(ServiceTicket.partner_id == service_center_id)
        if sub_status_filter:
            query = query.filter(ServiceTicket.sub_status == sub_status_filter)
        if ticket_type_filter:
            query = query.filter(ServiceTicket.ticket_type == ticket_type_filter)
        if staff_id_filter is not None:
            query = query.filter(
                or_(
                    ServiceTicket.service_manager_id == staff_id_filter,
                    ServiceTicket.service_technician_id == staff_id_filter
                )
            )
        
        return query.order_by(desc(ServiceTicket.created_date)).all()
    
    @staticmethod
    def get_procurement_queue(db: Session) -> List[ServiceTicketSpareRequest]:
        """Get pending spare requests for procurement team"""
        return db.query(ServiceTicketSpareRequest).filter(
            ServiceTicketSpareRequest.procurement_status.in_(['pending', 'acknowledged', 'ordered'])
        ).order_by(ServiceTicketSpareRequest.requested_at).all()
    
    @staticmethod
    def create_billing(
        db: Session,
        ticket_id: int,
        document_type: str = 'bill',
        is_gst_invoice: bool = False,
        company_id: Optional[int] = None,
        created_by_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create billing record for a service ticket"""
        try:
            ticket = db.query(ServiceTicket).filter(ServiceTicket.id == ticket_id).first()
            if not ticket:
                return {"success": False, "message": "Ticket not found"}
            
            existing = db.query(ServiceTicketBilling).filter(
                ServiceTicketBilling.ticket_id == ticket_id,
                ServiceTicketBilling.status.in_(['draft', 'confirmed'])
            ).first()
            if existing:
                if existing.status == 'confirmed':
                    return {"success": False, "message": "Confirmed billing already exists for this ticket"}
                return {"success": False, "message": "Active draft billing already exists for this ticket. Cancel it first to create a new one."}
            
            # DC Protocol Jan 2026: Document type based on GST selection
            # is_gst_invoice=True → document_type='invoice', INV-YYYYMMDD-XXXX
            # is_gst_invoice=False → document_type='estimate', EST-YYYYMMDD-XXXX
            actual_document_type = 'invoice' if is_gst_invoice else 'estimate'
            
            billing = ServiceTicketBilling(
                ticket_id=ticket_id,
                document_type=actual_document_type,
                is_gst_invoice=is_gst_invoice,
                status='draft',
                company_id=company_id,
                service_center_id=ticket.partner_id,
                billing_customer_name=ticket.customer_name,
                billing_customer_phone=ticket.customer_phone,
                billing_customer_address=getattr(ticket, 'customer_address', None),
                billing_customer_gstin=getattr(ticket, 'customer_gstin', None),
                created_by_id=created_by_id
            )
            
            if is_gst_invoice:
                billing.invoice_number = TicketService._generate_invoice_number(db)
                billing.bill_reference = None
            else:
                billing.bill_reference = TicketService._generate_estimate_number(db)
                billing.invoice_number = None
            
            db.add(billing)
            db.commit()
            db.refresh(billing)
            
            logger.info(f"✅ Billing created for ticket {ticket.ticket_id}")
            return {"success": True, "billing": billing.to_dict()}
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating billing: {str(e)}")
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def _generate_invoice_number(db: Session) -> str:
        """Generate unique invoice number for GST invoices: INV-YYYYMMDD-XXXX"""
        date_str = datetime.utcnow().strftime('%Y%m%d')
        prefix = f"INV-{date_str}"
        last = db.query(ServiceTicketBilling).filter(
            ServiceTicketBilling.invoice_number.like(f"{prefix}%")
        ).order_by(desc(ServiceTicketBilling.id)).first()
        
        if last and last.invoice_number:
            seq = int(last.invoice_number.split('-')[-1]) + 1
        else:
            seq = 1
        
        return f"{prefix}-{seq:04d}"
    
    @staticmethod
    def _generate_estimate_number(db: Session) -> str:
        """Generate unique estimate number for non-GST bills: EST-YYYYMMDD-XXXX"""
        date_str = datetime.utcnow().strftime('%Y%m%d')
        prefix = f"EST-{date_str}"
        last = db.query(ServiceTicketBilling).filter(
            ServiceTicketBilling.bill_reference.like(f"{prefix}%")
        ).order_by(desc(ServiceTicketBilling.id)).first()
        
        if last and last.bill_reference:
            seq = int(last.bill_reference.split('-')[-1]) + 1
        else:
            seq = 1
        
        return f"{prefix}-{seq:04d}"
    
    @staticmethod
    def add_billing_item(
        db: Session,
        billing_id: int,
        item_type: str,
        description: str,
        quantity: float,
        rate: float,
        hsn_code: Optional[str] = None,
        tax_rate: float = 0.0,
        is_intrastate: bool = True,
        spare_request_id: Optional[int] = None,
        specification: Optional[str] = None,
        warranty_info: Optional[str] = None,
        product_category: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Add line item to billing with GST calculation"""
        try:
            billing = db.query(ServiceTicketBilling).filter(
                ServiceTicketBilling.id == billing_id
            ).first()
            if not billing:
                return {"success": False, "message": "Billing not found"}
            
            # DC Protocol: labour/other/service/shipping — staff enters tax-INCLUSIVE total
            # Back-calculate ex-tax amount; line_total = exact entered amount
            ALWAYS_18_INCLUSIVE_TYPES = {'labour', 'other', 'service', 'shipping'}
            if item_type in ALWAYS_18_INCLUSIVE_TYPES:
                tax_rate = 18.0
                line_total = round(quantity * rate, 2)        # what customer pays — exact entered
                taxable_amount = round(line_total / 1.18, 2)  # back-calculated ex-tax
            else:
                taxable_amount = round(quantity * rate, 2)
                line_total = None  # computed after GST below

            cgst_rate = sgst_rate = igst_rate = 0.0
            cgst_amount = sgst_amount = igst_amount = 0.0

            if billing.is_gst_invoice and tax_rate > 0:
                if is_intrastate:
                    cgst_rate = sgst_rate = tax_rate / 2
                    cgst_amount = round(taxable_amount * cgst_rate / 100, 2)
                    sgst_amount = round(taxable_amount * sgst_rate / 100, 2)
                else:
                    igst_rate = tax_rate
                    igst_amount = round(taxable_amount * igst_rate / 100, 2)

            if line_total is None:
                line_total = taxable_amount + cgst_amount + sgst_amount + igst_amount
            
            item = ServiceTicketBillingItem(
                billing_id=billing_id,
                item_type=item_type,
                description=description,
                quantity=quantity,
                rate=rate,
                hsn_code=hsn_code,
                taxable_amount=taxable_amount,
                tax_rate=tax_rate,
                cgst_rate=cgst_rate,
                cgst_amount=cgst_amount,
                sgst_rate=sgst_rate,
                sgst_amount=sgst_amount,
                igst_rate=igst_rate,
                igst_amount=igst_amount,
                line_total=line_total,
                spare_request_id=spare_request_id,
                specification=specification,
                warranty_info=warranty_info,
                product_category=product_category or None,
            )
            db.add(item)
            db.flush()  # DC Protocol: flush so the new item is visible to the recalculation query
            
            TicketService._recalculate_billing_totals(db, billing)
            
            db.commit()
            db.refresh(item)
            
            return {"success": True, "item": item.to_dict()}
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error adding billing item: {str(e)}")
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def _recalculate_billing_totals(db: Session, billing: ServiceTicketBilling):
        """Recalculate billing totals from line items.
        DC Protocol Mar 2026: Coupon discount is applied BEFORE GST (pre-tax discount).
        taxable_amount / cgst_amount / sgst_amount / igst_amount store the RAW (pre-coupon) values.
        total_amount and net_payable reflect the final payable after coupon-reduced GST.
        """
        items = db.query(ServiceTicketBillingItem).filter(
            ServiceTicketBillingItem.billing_id == billing.id
        ).all()

        service_amount = sum(i.taxable_amount for i in items if i.item_type == 'service')
        spares_amount  = sum(i.taxable_amount for i in items if i.item_type == 'spare')
        labour_amount  = sum(i.taxable_amount for i in items if i.item_type == 'labour')

        # Raw (pre-coupon) totals from line items
        taxable_raw = sum(i.taxable_amount for i in items)
        cgst_raw    = sum(i.cgst_amount or 0 for i in items)
        sgst_raw    = sum(i.sgst_amount or 0 for i in items)
        igst_raw    = sum(i.igst_amount or 0 for i in items)

        billing.service_amount = service_amount
        billing.spares_amount  = spares_amount
        billing.labour_amount  = labour_amount
        # Store raw amounts for reference / display of original subtotals
        billing.taxable_amount = taxable_raw
        billing.cgst_amount    = cgst_raw
        billing.sgst_amount    = sgst_raw
        billing.igst_amount    = igst_raw

        # DC Protocol: Apply coupon discount BEFORE GST
        discount_pct = float(billing.coupon_discount_pct or 0)
        if discount_pct > 0:
            discount_ratio = 1.0 - discount_pct / 100.0
            discount_on_taxable = round(taxable_raw * discount_pct / 100.0, 2)
            discounted_taxable  = round(taxable_raw * discount_ratio, 2)
            discounted_cgst     = round(cgst_raw    * discount_ratio, 2)
            discounted_sgst     = round(sgst_raw    * discount_ratio, 2)
            discounted_igst     = round(igst_raw    * discount_ratio, 2)
            billing.discount_amount = discount_on_taxable
            total_amount = discounted_taxable + discounted_cgst + discounted_sgst + discounted_igst
        else:
            billing.discount_amount = 0.0
            total_amount = taxable_raw + cgst_raw + sgst_raw + igst_raw

        billing.total_amount = round(total_amount, 2)
        # DC Protocol: Manual discount is applied AFTER GST (flat rupee deduction post-tax)
        manual_disc = float(billing.manual_discount_amount or 0)
        billing.net_payable  = round(total_amount - manual_disc + float(billing.round_off or 0), 2)
        billing.amount_due   = round(billing.net_payable - float(billing.amount_paid or 0), 2)
    
    @staticmethod
    def finalize_billing(
        db: Session,
        billing_id: int,
        payment_mode: Optional[str] = None,
        amount_paid: float = 0.0,
        payment_reference: Optional[str] = None
    ) -> Dict[str, Any]:
        """Finalize billing and update payment status"""
        try:
            billing = db.query(ServiceTicketBilling).filter(
                ServiceTicketBilling.id == billing_id
            ).first()
            if not billing:
                return {"success": False, "message": "Billing not found"}
            
            billing.payment_mode = payment_mode
            billing.amount_paid = amount_paid
            billing.payment_reference = payment_reference
            billing.amount_due = billing.net_payable - amount_paid
            
            if billing.amount_due <= 0:
                billing.payment_status = 'paid'
            elif amount_paid > 0:
                billing.payment_status = 'partial'
            else:
                billing.payment_status = 'pending'
            
            db.commit()
            
            logger.info(f"✅ Billing {billing_id} finalized with payment status: {billing.payment_status}")
            return {"success": True, "billing": billing.to_dict()}
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error finalizing billing: {str(e)}")
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def post_to_sfms(db: Session, billing_id: int, posted_by_id: Optional[int] = None) -> Dict[str, Any]:
        """Post billing to SFMS accounting system"""
        try:
            billing = db.query(ServiceTicketBilling).filter(
                ServiceTicketBilling.id == billing_id
            ).first()
            if not billing:
                return {"success": False, "message": "Billing not found"}
            
            if billing.sfms_status == 'posted':
                return {"success": False, "message": "Already posted to SFMS"}
            
            billing.sfms_status = 'posted'
            billing.sfms_posted_at = datetime.utcnow()
            billing.posted_by_id = posted_by_id
            
            db.commit()
            
            logger.info(f"✅ Billing {billing_id} posted to SFMS")
            return {"success": True, "message": "Posted to SFMS successfully"}
            
        except Exception as e:
            db.rollback()
            billing.sfms_status = 'draft'
            billing.sfms_error = str(e)
            db.commit()
            logger.error(f"Error posting to SFMS: {str(e)}")
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def get_billing_by_ticket(db: Session, ticket_id: int) -> Optional[ServiceTicketBilling]:
        """Get billing record for a ticket"""
        return db.query(ServiceTicketBilling).filter(
            ServiceTicketBilling.ticket_id == ticket_id
        ).first()
