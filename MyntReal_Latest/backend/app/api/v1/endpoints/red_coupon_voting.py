"""
Red Coupon Voting System Endpoints
Account reactivation approval with 3-tier workflow and voting
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.models.red_coupon import RedCouponApproval, RedCouponReassignmentVote, RedCouponAuditLog
from app.models.user import User
from app.core.database import get_db
from app.core.security import get_current_user

router = APIRouter(prefix="/red-coupon", tags=["Red Coupon Voting"])


class ApprovalDecision(BaseModel):
    action: str
    comments: Optional[str] = None


class VoteSubmission(BaseModel):
    vote: str
    vote_reason: Optional[str] = None


@router.get("/approvals")
async def list_red_coupon_approvals(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all Red Coupon approval requests
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Super Admin', 'Admin', 'Finance Admin']:
    #     raise HTTPException(status_code=403, detail="Admin access required")
    
    query = db.query(RedCouponApproval)
    
    if status:
        query = query.filter(RedCouponApproval.status == status)
    
    approvals = query.order_by(RedCouponApproval.requested_date.desc()).all()
    
    return {
        "success": True,
        "approvals": [
            {
                "id": a.id,
                "tracker_id": a.tracker_id,
                "user_id": a.user_id,
                "approval_type": a.approval_type,
                "status": a.status,
                "requires_super_admin": a.requires_super_admin,
                "requires_accounts_admin": a.requires_accounts_admin,
                "requires_member_votes": a.requires_member_votes,
                "requested_by": a.requested_by,
                "approved_by": a.approved_by,
                "requested_date": a.requested_date.strftime('%Y-%m-%d %H:%M:%S'),
                "approved_date": a.approved_date.strftime('%Y-%m-%d %H:%M:%S') if a.approved_date else None,
                "voting_closed": a.voting_closed
            }
            for a in approvals
        ]
    }


@router.post("/process-approval/{request_id}")
async def process_red_coupon_approval(
    request_id: int,
    data: ApprovalDecision,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Process admin approval/rejection of Red Coupon reactivation
    """
    approval_request = db.query(RedCouponApproval).filter(
        RedCouponApproval.id == request_id
    ).first()
    
    if not approval_request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if approval_request.status != 'pending':
        raise HTTPException(status_code=400, detail="Request already processed")
    
    # Check if requires voting instead
    if approval_request.requires_member_votes > 0:
        raise HTTPException(
            status_code=400,
            detail="This request requires 3-person voting. Use voting interface."
        )
    
    # Authorization check
    user_role = getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', '')
    # DC Protocol: Menu-based access control - page assignment = full access
    # can_approve = False
    # if approval_request.requires_super_admin:
    #     if user_role != 'Super Admin':
    #         raise HTTPException(status_code=403, detail="Super Admin approval required")
    #     can_approve = True
    # elif approval_request.requires_accounts_admin:
    #     if user_role not in ['Super Admin', 'Finance Admin']:
    #         raise HTTPException(status_code=403, detail="Accounts Admin approval required")
    #     can_approve = True
    # else:
    #     if user_role in ['Super Admin', 'Admin', 'Finance Admin']:
    #         can_approve = True
    # if not can_approve:
    #     raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Process decision
    if data.action == 'approve':
        approval_request.status = 'approved'
        approval_request.approved_by = current_user.id
        approval_request.approved_date = datetime.utcnow()
        approval_request.approval_reason = data.comments
        
        # Create audit log
        audit_entry = RedCouponAuditLog(
            tracker_id=approval_request.tracker_id,
            user_id=approval_request.user_id,
            performed_by=current_user.id,
            action_type='reactivation_approved',
            action_description=f'Account reactivated by {user_role}: {data.comments}',
            old_status='locked',
            new_status='active',
            ip_address=request.client.host,
            user_agent=request.headers.get('user-agent', '')
        )
        
        message = 'Red Coupon reactivation approved successfully'
        
    elif data.action == 'reject':
        approval_request.status = 'rejected'
        approval_request.approved_by = current_user.id
        approval_request.rejected_date = datetime.utcnow()
        approval_request.rejection_reason = data.comments
        
        # Create audit log
        audit_entry = RedCouponAuditLog(
            tracker_id=approval_request.tracker_id,
            user_id=approval_request.user_id,
            performed_by=current_user.id,
            action_type='reactivation_rejected',
            action_description=f'Reactivation rejected by {user_role}: {data.comments}',
            ip_address=request.client.host,
            user_agent=request.headers.get('user-agent', '')
        )
        
        message = 'Red Coupon reactivation rejected'
    else:
        raise HTTPException(status_code=400, detail="Invalid action")
    
    db.add(audit_entry)
    db.commit()
    
    return {
        "success": True,
        "message": message
    }


@router.get("/voting/{approval_id}")
async def get_voting_details(
    approval_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get voting details for 3-person Red Coupon decision
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Super Admin', 'Admin', 'Finance Admin']:
    #     raise HTTPException(status_code=403, detail="Voting privileges required")
    
    approval_request = db.query(RedCouponApproval).filter(
        RedCouponApproval.id == approval_id
    ).first()
    
    if not approval_request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if approval_request.requires_member_votes <= 0:
        raise HTTPException(
            status_code=400,
            detail="This request requires admin approval, not voting"
        )
    
    # Get existing votes
    existing_votes = db.query(RedCouponReassignmentVote).filter(
        RedCouponReassignmentVote.approval_id == approval_id
    ).order_by(RedCouponReassignmentVote.voted_date.desc()).all()
    
    # Check if user has voted
    user_vote = db.query(RedCouponReassignmentVote).filter(
        and_(
            RedCouponReassignmentVote.approval_id == approval_id,
            RedCouponReassignmentVote.voter_id == current_user.id
        )
    ).first()
    
    # Calculate vote summary
    approve_votes = len([v for v in existing_votes if v.vote == 'approve'])
    reject_votes = len([v for v in existing_votes if v.vote == 'reject'])
    total_votes = len(existing_votes)
    voting_complete = total_votes >= 3 or approve_votes >= 2 or reject_votes >= 2
    
    return {
        "success": True,
        "approval_request": {
            "id": approval_request.id,
            "user_id": approval_request.user_id,
            "approval_type": approval_request.approval_type,
            "status": approval_request.status,
            "requested_date": approval_request.requested_date.strftime('%Y-%m-%d %H:%M:%S'),
            "voting_closed": approval_request.voting_closed
        },
        "voting_summary": {
            "approve_votes": approve_votes,
            "reject_votes": reject_votes,
            "total_votes": total_votes,
            "voting_complete": voting_complete
        },
        "user_has_voted": user_vote is not None,
        "existing_votes": [
            {
                "voter_id": v.voter_id,
                "vote": v.vote,
                "vote_reason": v.vote_reason,
                "voter_role": v.voter_role,
                "voted_date": v.voted_date.strftime('%Y-%m-%d %H:%M:%S')
            }
            for v in existing_votes
        ]
    }


@router.post("/submit-vote/{approval_id}")
async def submit_red_coupon_vote(
    approval_id: int,
    data: VoteSubmission,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submit vote for Red Coupon reactivation (3-person voting)
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Super Admin', 'Admin', 'Finance Admin']:
    #     raise HTTPException(status_code=403, detail="Voting privileges required")
    
    # Lock approval record for atomic voting
    approval_request = db.query(RedCouponApproval).filter(
        RedCouponApproval.id == approval_id
    ).with_for_update().first()
    
    if not approval_request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if approval_request.requires_member_votes <= 0:
        raise HTTPException(
            status_code=400,
            detail="This request requires admin approval, not voting"
        )
    
    if approval_request.status != 'pending':
        raise HTTPException(
            status_code=400,
            detail=f"Request already {approval_request.status}"
        )
    
    if approval_request.voting_closed:
        raise HTTPException(status_code=400, detail="Voting has been closed")
    
    # Check if user already voted
    existing_vote = db.query(RedCouponReassignmentVote).filter(
        and_(
            RedCouponReassignmentVote.approval_id == approval_id,
            RedCouponReassignmentVote.voter_id == current_user.id
        )
    ).with_for_update().first()
    
    if existing_vote:
        raise HTTPException(status_code=400, detail="You have already voted")
    
    # Get current vote counts
    existing_votes = db.query(RedCouponReassignmentVote).filter(
        RedCouponReassignmentVote.approval_id == approval_id
    ).with_for_update().all()
    
    approve_count = len([v for v in existing_votes if v.vote == 'approve'])
    reject_count = len([v for v in existing_votes if v.vote == 'reject'])
    total_votes = len(existing_votes)
    
    # Check for early majority
    if approve_count >= 2:
        raise HTTPException(
            status_code=400,
            detail="Voting closed - majority approval already reached"
        )
    elif reject_count >= 2:
        raise HTTPException(
            status_code=400,
            detail="Voting closed - majority rejection already reached"
        )
    elif total_votes >= 3:
        raise HTTPException(status_code=400, detail="Voting closed - maximum votes reached")
    
    # Create vote record
    vote_record = RedCouponReassignmentVote(
        approval_id=approval_id,
        voter_id=current_user.id,
        vote=data.vote,
        vote_reason=data.vote_reason,
        vote_weight=1,
        voter_role=(getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', '')),
        is_qualified_voter=True
    )
    
    db.add(vote_record)
    
    # Update vote counts
    if data.vote == 'approve':
        approve_count += 1
    else:
        reject_count += 1
    total_votes += 1
    
    # Check if voting should close
    final_decision_made = False
    
    if approve_count >= 2:
        approval_request.status = 'approved'
        approval_request.approved_by = current_user.id
        approval_request.approved_date = datetime.utcnow()
        approval_request.voting_closed = True
        approval_request.voting_closed_date = datetime.utcnow()
        approval_request.early_majority_reached = True
        message = "Vote recorded. Majority approval reached - request approved"
        final_decision_made = True
    elif reject_count >= 2:
        approval_request.status = 'rejected'
        approval_request.approved_by = current_user.id
        approval_request.rejected_date = datetime.utcnow()
        approval_request.voting_closed = True
        approval_request.voting_closed_date = datetime.utcnow()
        approval_request.early_majority_reached = True
        message = "Vote recorded. Majority rejection reached - request rejected"
        final_decision_made = True
    elif total_votes >= 3:
        # Determine final decision based on vote count
        if approve_count > reject_count:
            approval_request.status = 'approved'
            approval_request.approved_by = current_user.id
            approval_request.approved_date = datetime.utcnow()
            message = "Vote recorded. All votes cast - request approved"
        else:
            approval_request.status = 'rejected'
            approval_request.approved_by = current_user.id
            approval_request.rejected_date = datetime.utcnow()
            message = "Vote recorded. All votes cast - request rejected"
        approval_request.voting_closed = True
        approval_request.voting_closed_date = datetime.utcnow()
        final_decision_made = True
    else:
        message = f"Vote recorded. {3 - total_votes} more vote(s) needed"
    
    # Create audit log for vote
    audit_entry = RedCouponAuditLog(
        tracker_id=approval_request.tracker_id,
        user_id=approval_request.user_id,
        performed_by=current_user.id,
        action_type=f'vote_cast_{data.vote}',
        action_description=f"{getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', '')} voted {data.vote}: {data.vote_reason}",
        ip_address=request.client.host,
        user_agent=request.headers.get('user-agent', '')
    )
    db.add(audit_entry)
    
    # Create terminal audit log if decision is final
    if final_decision_made:
        terminal_audit = RedCouponAuditLog(
            tracker_id=approval_request.tracker_id,
            user_id=approval_request.user_id,
            performed_by=current_user.id,
            action_type=f'voting_finalized_{approval_request.status}',
            action_description=f'Voting completed: {message} (Approve: {approve_count}, Reject: {reject_count})',
            old_status='pending',
            new_status=approval_request.status,
            ip_address=request.client.host,
            user_agent=request.headers.get('user-agent', '')
        )
        db.add(terminal_audit)
    
    db.commit()
    
    return {
        "success": True,
        "message": message,
        "voting_summary": {
            "approve_votes": approve_count,
            "reject_votes": reject_count,
            "total_votes": total_votes,
            "voting_closed": approval_request.voting_closed
        }
    }


@router.get("/audit-log/{user_id}")
async def get_red_coupon_audit_log(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get audit log for Red Coupon actions for a user
    """
    # DC Protocol: Menu-based access control - page assignment = full access
    # if (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) not in ['Super Admin', 'Admin', 'Finance Admin']:
    #     raise HTTPException(status_code=403, detail="Admin access required")
    
    audit_logs = db.query(RedCouponAuditLog).filter(
        RedCouponAuditLog.user_id == user_id
    ).order_by(RedCouponAuditLog.performed_date.desc()).all()
    
    return {
        "success": True,
        "audit_logs": [
            {
                "id": log.id,
                "action_type": log.action_type,
                "action_description": log.action_description,
                "old_status": log.old_status,
                "new_status": log.new_status,
                "performed_by": log.performed_by,
                "performed_date": log.performed_date.strftime('%Y-%m-%d %H:%M:%S'),
                "ip_address": log.ip_address
            }
            for log in audit_logs
        ]
    }
