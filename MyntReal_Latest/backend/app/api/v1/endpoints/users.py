"""
User Endpoints - Complete Implementation
All user-facing functionality with 100% feature parity from Flask
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status, Body, Form, File, UploadFile, Query, Response, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, text, or_
from sqlalchemy.exc import IntegrityError
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, EmailStr
from datetime import datetime

logger = logging.getLogger(__name__)

from app.core.database import get_db
from app.core.rbac import require_user
from app.core.security import SecurityManager, get_current_user, require_activated_user
from app.core.config import settings
from app.models.user import User
from app.models.transaction import Transaction
from app.models.api_response import success_response, error_response
from app.services.user_service import UserService
from app.services.wallet_service import WalletService
from app.services.wallet_balance_service import get_earning_wallet, get_withdrawable_wallet
from app.core.audit import AuditLogger

router = APIRouter()

# ===== REQUEST/RESPONSE MODELS =====

class ProfileUpdateRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    mobile: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None

class BankingInfoRequest(BaseModel):
    bank_name: Optional[str] = None
    account_holder_name: Optional[str] = None
    account_number: Optional[str] = None
    ifsc_code: Optional[str] = None
    pan_number: Optional[str] = None
    aadhar_number: Optional[str] = None

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str

class WithdrawalRequest(BaseModel):
    amount: float
    withdrawal_type: str = 'bank_transfer'

class TermsAcceptRequest(BaseModel):
    """Terms and conditions acceptance request"""
    version: str

# ===== PROFILE ENDPOINTS =====
# NOTE: Specific routes (/profile) must come BEFORE parameterized routes (/{user_id})

@router.get("/profile")
async def get_user_profile(
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Get comprehensive user profile"""
    try:
        user_service = UserService(db)
        wallet_service = WalletService(db)
        
        wallet_data = wallet_service.get_wallet_balance(str(current_user.id))
        
        # DC Protocol Phase 1.4: Shadow Mode - Compute balances from materialized views
        computed_earning = get_earning_wallet(db, str(current_user.id))
        computed_withdrawable = get_withdrawable_wallet(db, str(current_user.id))
        
        # Get package information using NEW decimal point system
        package_points = getattr(current_user, 'package_points', 0) or 0
        package_name = current_user.get_package_type()  # Uses NEW decimal system: 1=Platinum, 0.5=Diamond, 0=Star/Loyal
        
        profile_data = {
            "id": str(current_user.id),
            "name": str(getattr(current_user, 'name', '')),
            "email": str(getattr(current_user, 'email', '')),
            "mobile": str(getattr(current_user, 'phone_number', '')),
            "user_type": str(getattr(current_user, 'user_type', 'User')),
            "registration_date": getattr(current_user, 'registration_date', datetime.now()).isoformat(),
            "activation_date": getattr(current_user, 'activation_date', None).isoformat() if getattr(current_user, 'activation_date', None) else None,
            "coupon_status": str(getattr(current_user, 'coupon_status', 'Eligible')),
            "is_active": bool(getattr(current_user, 'is_active', True)),
            "gender": str(getattr(current_user, 'gender', '') or 'Not provided'),
            "actual_dob": getattr(current_user, 'actual_date_of_birth', None).isoformat() if getattr(current_user, 'actual_date_of_birth', None) else None,
            "certificate_dob": getattr(current_user, 'certificate_date_of_birth', None).isoformat() if getattr(current_user, 'certificate_date_of_birth', None) else None,
            "address": str(getattr(current_user, 'address', '')),
            "city": str(getattr(current_user, 'city', '')),
            "state": str(getattr(current_user, 'state', '')),
            "pincode": str(getattr(current_user, 'pincode', '')),
            # NEW KYC-Enforced Wallet System (PRODUCTION - using stored values)
            "earning_wallet": wallet_data.get('earning_wallet', 0),  # Income waiting for KYC
            "withdrawable_wallet": wallet_data.get('withdrawable_wallet', 0),  # Available after KYC
            "upgrade_wallet_balance": wallet_data.get('upgrade_wallet_balance', 0),
            "wallet_balance": wallet_data.get('wallet_balance', 0),  # OLD (deprecated)
            "total_earnings": wallet_data.get('total_earnings', 0),
            "kyc_status": wallet_data.get('kyc_status', 'Pending'),
            "last_wallet_sync_at": wallet_data.get('last_wallet_sync_at', None),
            "sponsor_id": str(getattr(current_user, 'sponsor_id', '')),
            "referrer_id": str(getattr(current_user, 'referrer_id', '')),
            "is_ved": bool(getattr(current_user, 'is_ved', False)),
            "package_type": package_name,
            "package_points": package_points,
            "bank_name": str(getattr(current_user, 'bank_name', '')),
            # KYC Fields (DC Protocol - single source of truth)
            "aadhaar_number": str(getattr(current_user, 'aadhaar_number', '') or ''),
            "pan_number": str(getattr(current_user, 'pan_number', '') or ''),
            # DC Protocol Phase 1.4: Shadow Mode - Computed balances for monitoring
            "dc_protocol_shadow_mode": {
                "earning_wallet_computed": float(computed_earning),
                "withdrawable_wallet_computed": float(computed_withdrawable),
                "earning_matches": abs(wallet_data.get('earning_wallet', 0) - float(computed_earning)) <= 0.01,
                "withdrawable_matches": abs(wallet_data.get('withdrawable_wallet', 0) - float(computed_withdrawable)) <= 0.01,
                "note": "Computed values from ledger (pending_income + withdrawal_request tables). Production uses stored values."
            }
        }
        
        return success_response(
            message="Profile retrieved successfully",
            data=profile_data
        )
    
    except Exception as e:
        logger.error(f"❌ PROFILE ENDPOINT ERROR: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

@router.put("/profile")
async def update_user_profile(
    profile_data: ProfileUpdateRequest,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Update user profile information"""
    try:
        user_service = UserService(db)
        updates = profile_data.dict(exclude_unset=True)
        
        # DC Protocol (Jan 2026): Users cannot change their own name or mobile
        # These fields are protected and can only be changed by admin/staff
        protected_fields = ['first_name', 'last_name', 'name', 'mobile', 'phone']
        for field in protected_fields:
            updates.pop(field, None)
        
        result = user_service.update_user_profile(
            user_id=str(current_user.id),
            update_data=updates
        )
        
        if result.get('success'):
            AuditLogger.log_action(
                db=db,
                user=current_user,
                action='UPDATE',
                resource_type='USER_PROFILE',
                resource_id=str(current_user.id),
                details=updates
            )
            
            return success_response(
                message="Profile updated successfully",
                data=result
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get('error', 'Update failed')
            )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

@router.post("/accept-terms")
async def accept_terms(
    request: Request,
    terms_data: TermsAcceptRequest,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Accept terms and conditions"""
    try:
        from app.models.banner import UserCouponAcceptance
        
        # DC Protocol Feb 2026: Reload user in this endpoint's db session to avoid detached instance error
        user = db.query(User).filter(User.id == current_user.id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Update user table
        user.accepted_terms_version = terms_data.version
        user.acceptance_timestamp = datetime.now()
        
        # Get client info for audit trail
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "unknown")
        
        # Count how many times this user has accepted T&C (for login_attempt_number)
        previous_acceptances = db.query(UserCouponAcceptance).filter(
            UserCouponAcceptance.user_id == user.id
        ).count()
        login_attempt = previous_acceptances + 1
        
        # Create audit record in UserCouponAcceptance table (only for first 3 attempts)
        # Table has CHECK constraint limiting login_attempt_number to 1-3
        if login_attempt <= 3:
            audit_record = UserCouponAcceptance(
                user_id=user.id,
                login_attempt_number=login_attempt,
                ip_address=client_ip,
                user_agent=user_agent,
                accepted_terms_version=terms_data.version,
                acceptance_timestamp=user.acceptance_timestamp
            )
            db.add(audit_record)
        
        accepted_version = terms_data.version
        accepted_timestamp = user.acceptance_timestamp
        
        db.commit()
        
        try:
            AuditLogger.log_action(
                db=db,
                user=user,
                action='ACCEPT',
                resource_type='TERMS_CONDITIONS',
                resource_id=accepted_version,
                details={
                    'version': accepted_version, 
                    'timestamp': accepted_timestamp.isoformat(),
                    'ip': client_ip,
                    'login_attempt': login_attempt
                }
            )
        except Exception as audit_err:
            print(f"[WARN] Audit log failed for accept-terms (non-fatal): {audit_err}")
        
        return success_response(
            message="Terms and conditions accepted successfully",
            data={
                "version": accepted_version,
                "timestamp": accepted_timestamp.isoformat()
            }
        )
    
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

@router.get("/{mnr_id}/basic-info")
async def get_user_basic_info(
    mnr_id: str,
    db: Session = Depends(get_db)
):
    """Get basic user information by MNR ID (for referrer verification during signup)"""
    try:
        user = db.query(User).filter(User.id == mnr_id).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "User not found"}
            )
        
        return success_response(
            message="User information retrieved",
            data={
                "mnr_id": str(user.id),
                "name": str(user.name),
                "account_status": str(user.account_status)
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )


@router.get("/{mnr_id}/contributors")
async def get_user_contributors(
    mnr_id: str,
    type: str = Query(..., description="Type: direct, matching, or bonanza"),
    tier_required: Optional[int] = Query(None, description="Cumulative required count for the award tier - limits results to only relevant contributors"),
    db: Session = Depends(get_db)
):
    """
    Get contributors for a user's awards/bonanza achievement.
    DC Protocol Feb 2026: Returns only contributors relevant to the specific award tier.
    Uses Oct 21, 2025 reset date filter and limits results to tier_required count.
    """
    from app.models.placement import Placement
    from datetime import datetime
    
    RESET_DATE = datetime(2025, 10, 21)
    
    user = db.query(User).filter(User.id == mnr_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    result = {
        "user_id": mnr_id,
        "user_name": user.name,
        "type": type
    }
    
    if type == 'direct':
        referrals = db.query(User).filter(
            User.referrer_id == mnr_id,
            User.coupon_status == 'Activated',
            User.activation_date >= RESET_DATE,
            User.is_welcome_coupon != True
        ).order_by(User.activation_date.asc()).all()
        
        # DC Protocol Feb 2026: Subtract bonanza-consumed referrals
        # When a bonanza with direct_referral criteria is claimed, those referrals
        # are consumed and should not count toward regular direct awards
        from app.models.bonanza import DynamicBonanzaHistory
        bonanza_direct_deductions = db.query(DynamicBonanzaHistory).filter(
            DynamicBonanzaHistory.user_id == mnr_id,
            DynamicBonanzaHistory.deduction_applied_to_direct_awards == True,
            DynamicBonanzaHistory.deduction_amount_direct > 0,
            DynamicBonanzaHistory.claimed_at.isnot(None)
        ).all()
        
        total_consumed = sum(h.deduction_amount_direct or 0 for h in bonanza_direct_deductions)
        
        delivered_debt = 0
        delivered_debt_details = []
        if total_consumed > 0:
            from app.models.awards import UserAwardProgress, DirectAwardTier
            delivered_awards = db.query(UserAwardProgress, DirectAwardTier).join(
                DirectAwardTier, UserAwardProgress.award_tier_id == DirectAwardTier.id
            ).filter(
                UserAwardProgress.user_id == mnr_id,
                UserAwardProgress.processed_status.in_(['Delivered', 'Dispatched', 'Procurement Pending', 'Processed for Dispatch'])
            ).order_by(DirectAwardTier.cumulative_required.asc()).all()
            
            total_raw_points = sum(float(r.package_points or 0) for r in referrals)
            effective_points = max(0, total_raw_points - total_consumed)
            
            for award, tier in delivered_awards:
                if effective_points < tier.cumulative_required:
                    points_short = tier.cumulative_required - effective_points
                    debt_for_this = min(points_short, tier.cumulative_required)
                    delivered_debt += debt_for_this
                    delivered_debt_details.append({
                        "award_name": tier.award_name,
                        "gift_name": tier.award_description,
                        "tier_required": tier.cumulative_required,
                        "status": award.processed_status,
                        "debt_points": debt_for_this
                    })
        
        available_refs = referrals[total_consumed:] if total_consumed > 0 else referrals
        
        display_refs = available_refs[:tier_required] if tier_required else available_refs
        
        result["direct_referrals"] = [
            {
                "id": ref.id,
                "name": ref.name,
                "package": ref.get_package_type(),
                "package_points": float(ref.package_points or 0),
                "activation_date": ref.activation_date.isoformat() if ref.activation_date else None,
                "coupon_status": ref.coupon_status
            }
            for ref in display_refs
        ]
        result["total_count"] = len(display_refs)
        result["total_available"] = len(available_refs)
        result["total_raw"] = len(referrals)
        result["bonanza_consumed"] = total_consumed
        result["delivered_debt"] = delivered_debt
        result["delivered_debt_details"] = delivered_debt_details
        
    elif type == 'matching':
        def get_descendants_filtered(parent_id: str, max_count: int = 200) -> list:
            """Recursively get post-reset descendants using Placement table.
            DC Protocol Feb 2026: Traverse ALL nodes but only collect non-WC activated users.
            Must traverse inactive nodes too since their children may be active."""
            descendants = []
            queue = [parent_id]
            visited = set()
            while queue and len(descendants) < max_count:
                current_id = queue.pop(0)
                if current_id in visited:
                    continue
                visited.add(current_id)
                all_children = db.query(Placement, User).join(
                    User, Placement.child_id == User.id
                ).filter(
                    Placement.parent_id == current_id
                ).all()
                for placement, child_user in all_children:
                    queue.append(child_user.id)
                    if (child_user.coupon_status == 'Activated' and 
                        child_user.activation_date and 
                        child_user.activation_date >= RESET_DATE and
                        not child_user.is_welcome_coupon and
                        len(descendants) < max_count):
                        descendants.append(child_user)
            return descendants
        
        from app.models.bonanza import DynamicBonanzaHistory
        bonanza_matching_deductions = db.query(DynamicBonanzaHistory).filter(
            DynamicBonanzaHistory.user_id == mnr_id,
            DynamicBonanzaHistory.deduction_applied_to_matching_awards == True,
            DynamicBonanzaHistory.deduction_amount_matching > 0,
            DynamicBonanzaHistory.claimed_at.isnot(None)
        ).all()
        matching_consumed = sum(h.deduction_amount_matching or 0 for h in bonanza_matching_deductions)
        
        group_a_root = db.query(Placement).filter(
            Placement.parent_id == mnr_id,
            Placement.side == 'left'
        ).first()
        
        group_b_root = db.query(Placement).filter(
            Placement.parent_id == mnr_id,
            Placement.side == 'right'
        ).first()
        
        group_a_members = []
        group_b_members = []
        
        if group_a_root:
            root_user = db.query(User).filter(
                User.id == group_a_root.child_id, 
                User.coupon_status == 'Activated',
                User.activation_date >= RESET_DATE
            ).first()
            if root_user:
                group_a_members.append(root_user)
            group_a_members.extend(get_descendants_filtered(group_a_root.child_id))
        
        if group_b_root:
            root_user = db.query(User).filter(
                User.id == group_b_root.child_id, 
                User.coupon_status == 'Activated',
                User.activation_date >= RESET_DATE
            ).first()
            if root_user:
                group_b_members.append(root_user)
            group_b_members.extend(get_descendants_filtered(group_b_root.child_id))
        
        if matching_consumed > 0:
            group_a_members = group_a_members[matching_consumed:]
            group_b_members = group_b_members[matching_consumed:]
        
        if tier_required:
            paired_limit = min(tier_required, len(group_a_members), len(group_b_members))
            group_a_display = group_a_members[:paired_limit]
            group_b_display = group_b_members[:paired_limit]
        else:
            group_a_display = group_a_members
            group_b_display = group_b_members
        
        def format_member(m):
            return {
                "id": m.id,
                "name": m.name,
                "package": m.get_package_type(),
                "package_points": float(m.package_points or 0),
                "activation_date": m.activation_date.isoformat() if m.activation_date else None
            }
        
        result["matching_data"] = {
            "group_a": [format_member(m) for m in group_a_display],
            "group_b": [format_member(m) for m in group_b_display]
        }
        result["group_a_count"] = len(group_a_display)
        result["group_b_count"] = len(group_b_display)
        result["total_group_a"] = len(group_a_members)
        result["total_group_b"] = len(group_b_members)
        result["bonanza_consumed"] = matching_consumed
        
        delivered_debt = 0
        delivered_debt_details = []
        if matching_consumed > 0:
            from app.models.awards import UserMatchingAwardProgress, MatchingAwardTier
            delivered_matching = db.query(UserMatchingAwardProgress, MatchingAwardTier).join(
                MatchingAwardTier, UserMatchingAwardProgress.matching_award_tier_id == MatchingAwardTier.id
            ).filter(
                UserMatchingAwardProgress.user_id == mnr_id,
                UserMatchingAwardProgress.processed_status.in_(['Delivered', 'Dispatched', 'Procurement Pending', 'Processed for Dispatch'])
            ).order_by(MatchingAwardTier.cumulative_required.asc()).all()
            
            raw_pairs = min(len(group_a_display) + matching_consumed, len(group_b_display) + matching_consumed)
            effective_pairs = max(0, raw_pairs - matching_consumed)
            
            for award, tier in delivered_matching:
                if effective_pairs < tier.cumulative_required:
                    points_short = tier.cumulative_required - effective_pairs
                    debt_for_this = min(points_short, tier.cumulative_required)
                    delivered_debt += debt_for_this
                    delivered_debt_details.append({
                        "award_name": tier.award_name,
                        "gift_name": tier.award_description,
                        "tier_required": tier.cumulative_required,
                        "status": award.processed_status,
                        "debt_points": debt_for_this
                    })
        result["delivered_debt"] = delivered_debt
        result["delivered_debt_details"] = delivered_debt_details
        
    elif type == 'bonanza':
        from app.models.bonanza import DynamicBonanzaHistory
        bonanza_claims = db.query(DynamicBonanzaHistory).filter(
            DynamicBonanzaHistory.user_id == mnr_id
        ).order_by(DynamicBonanzaHistory.claimed_at.desc()).all()
        
        all_direct = []
        all_matching = None
        for claim in bonanza_claims:
            if claim.direct_contributors_snapshot:
                for contrib in claim.direct_contributors_snapshot:
                    all_direct.append(contrib)
            if claim.matching_contributors_snapshot:
                all_matching = claim.matching_contributors_snapshot
        
        if all_direct:
            result["direct_referrals"] = all_direct
            result["total_count"] = len(all_direct)
        elif all_matching:
            result["matching_data"] = all_matching
        else:
            result["direct_referrals"] = []
            result["total_count"] = 0
    
    else:
        result["message"] = "Unsupported type. Use 'direct', 'matching', or 'bonanza'"
    
    return result


@router.get("/profile/banking")
async def get_banking_info(
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Get user banking information"""
    banking_data = {
        "bank_name": str(getattr(current_user, 'bank_name', '')),
        "account_holder_name": str(getattr(current_user, 'account_holder_name', '')),
        "account_number": str(getattr(current_user, 'bank_account_number', '')),
        "ifsc_code": str(getattr(current_user, 'bank_ifsc_code', '')),
        "pan_number": str(getattr(current_user, 'pan_number', '')),
        "aadhar_number": str(getattr(current_user, 'aadhar_number', '')),
    }
    
    return success_response(
        message="Banking information retrieved successfully",
        data=banking_data
    )

@router.put("/profile/banking")
async def update_banking_info(
    banking_data: BankingInfoRequest,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Update user banking information"""
    try:
        updates = {}
        if banking_data.bank_name:
            setattr(current_user, 'bank_name', banking_data.bank_name)
            updates['bank_name'] = banking_data.bank_name
        if banking_data.account_holder_name:
            setattr(current_user, 'account_holder_name', banking_data.account_holder_name)
            updates['account_holder_name'] = banking_data.account_holder_name
        if banking_data.account_number:
            setattr(current_user, 'bank_account_number', banking_data.account_number)
            updates['account_number'] = banking_data.account_number
        if banking_data.ifsc_code:
            setattr(current_user, 'bank_ifsc_code', banking_data.ifsc_code)
            updates['ifsc_code'] = banking_data.ifsc_code
        if banking_data.pan_number:
            setattr(current_user, 'pan_number', banking_data.pan_number)
            updates['pan_number'] = banking_data.pan_number
        if banking_data.aadhar_number:
            setattr(current_user, 'aadhar_number', banking_data.aadhar_number)
            updates['aadhar_number'] = banking_data.aadhar_number
        
        db.commit()
        
        AuditLogger.log_action(
            db=db,
            user=current_user,
            action='UPDATE',
            resource_type='BANKING_INFO',
            resource_id=str(current_user.id),
            details=updates
        )
        
        return success_response(
            message="Banking information updated successfully",
            data=updates
        )
    
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

@router.post("/profile/change-password")
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Change user password"""
    try:
        if password_data.new_password != password_data.confirm_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New passwords do not match"
            )
        
        if not SecurityManager.verify_password(password_data.current_password, str(getattr(current_user, 'password', ''))):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is incorrect"
            )
        
        new_hash = SecurityManager.hash_password(password_data.new_password)
        setattr(current_user, 'password', new_hash)
        db.commit()
        
        AuditLogger.log_action(
            db=db,
            user=current_user,
            action='PASSWORD_CHANGE',
            resource_type='USER_SECURITY',
            resource_id=str(current_user.id)
        )
        
        return success_response(
            message="Password changed successfully",
            data={"changed_at": datetime.now().isoformat()}
        )
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

# ===== WALLET & TRANSACTIONS =====

@router.get("/wallet")
async def get_wallet_balance(
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Get user wallet balance"""
    wallet_service = WalletService(db)
    result = wallet_service.get_wallet_balance(str(current_user.id))
    
    if result.get('success'):
        return success_response(
            message="Wallet balance retrieved successfully",
            data=result
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.get('error', 'User not found')
        )

@router.get("/wallet-summary")
async def get_wallet_summary(
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """
    DC Protocol Phase 1.7: Wallet summary from SINGLE SOURCE (DashboardService)
    Shows GROSS values (before deductions) using canonical data
    NO improvised reverse calculations - all values from database ledgers
    - Overall Earning: GROSS total earned
    - Withdrawn: GROSS total withdrawn (from withdrawal_amount column)
    - Pending: GROSS pending (calculated by DashboardService)
    - Status breakdown: admin_pending, super_admin_pending, finance_pending, rejected
    """
    from app.models.transaction import PendingIncome
    user_id = str(current_user.id)
    
    # DC Protocol: Use SINGLE SOURCE OF TRUTH
    # WalletService wraps DashboardService (canonical financial summary)
    wallet_service = WalletService(db)
    earnings_summary = wallet_service.get_earnings_summary(user_id)
    
    # Extract canonical GROSS values (no calculations, no reverse math!)
    total_earned_gross = earnings_summary.get('total_gross_earnings', 0)
    withdrawn_gross = earnings_summary.get('withdrawn_gross', 0)
    pending_gross = earnings_summary.get('pending_balance_gross', 0)
    
    # Query for status breakdown from PendingIncome
    all_income = db.query(PendingIncome).filter(
        PendingIncome.user_id == user_id
    ).all()
    
    # Calculate status breakdown (GROSS values)
    admin_pending = sum(float(t.gross_amount or 0) for t in all_income 
                        if t.verification_status == 'Pending' and t.income_type != 'Ved Income')
    super_admin_pending = sum(float(t.gross_amount or 0) for t in all_income 
                              if t.verification_status == 'Admin Verified' and t.income_type != 'Ved Income')
    finance_pending = sum(float(t.gross_amount or 0) for t in all_income 
                          if t.verification_status == 'Super Admin Approved' and t.income_type != 'Ved Income')
    rejected = sum(float(t.gross_amount or 0) for t in all_income 
                   if t.verification_status == 'Rejected' and t.income_type != 'Ved Income')
    total_paid = sum(float(t.gross_amount or 0) for t in all_income 
                     if t.verification_status == 'Completed' and t.income_type != 'Ved Income')
    
    # Calculate final earnings (after 12% deduction)
    final_earnings = round(total_earned_gross * 0.88)
    
    return success_response(
        message="Wallet summary retrieved successfully (GROSS values only)",
        data={
            "overall_earning": round(total_earned_gross),
            "withdrawn": round(withdrawn_gross),
            "pending": round(pending_gross),
            "total_net_earnings": final_earnings,
            "total_paid": round(total_paid),
            "admin_pending": round(admin_pending),
            "super_admin_pending": round(super_admin_pending),
            "finance_pending": round(finance_pending),
            "rejected": round(rejected)
        }
    )

@router.get("/transactions")
async def get_transaction_history(
    limit: int = 100,
    offset: int = 0,
    transaction_type: Optional[str] = None,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Get user transaction history"""
    wallet_service = WalletService(db)
    result = wallet_service.get_transaction_history(
        user_id=str(current_user.id),
        limit=limit,
        offset=offset,
        transaction_type=transaction_type
    )
    
    return success_response(
        message="Transaction history retrieved successfully",
        data=result
    )

@router.get("/activated-counts")
async def get_activated_counts(
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Get activated team counts - direct referrals and entire self team (all generations)"""
    try:
        from app.models.placement import Placement
        from collections import deque
        
        # Count activated direct referrals
        direct_referrals = db.query(User).filter(
            User.referrer_id == current_user.id
        ).all()
        direct_activated = sum(1 for ref in direct_referrals if ref.activation_date is not None)
        
        # Count activated self team (ENTIRE binary tree downline - all generations)
        # Use iterative approach with queue for better performance
        def get_all_downline_activated(user_id: str) -> int:
            """Iteratively count all activated members in entire binary tree downline"""
            count = 0
            queue = deque([user_id])
            visited = set()
            
            while queue:
                current_id = queue.popleft()
                
                if current_id in visited:
                    continue
                visited.add(current_id)
                
                # Get direct children in binary tree
                placements = db.query(Placement).filter(
                    Placement.parent_id == current_id
                ).all()
                
                for placement in placements:
                    child_id = placement.child_id
                    
                    # Get user data
                    child = db.query(User).filter(User.id == child_id).first()
                    if child:
                        # Count if activated
                        if child.activation_date is not None:
                            count += 1
                        
                        # Add to queue for processing
                        queue.append(child_id)
            
            return count
        
        self_team_activated = get_all_downline_activated(current_user.id)
        
        return success_response(
            message="Activated counts retrieved successfully",
            data={
                "direct_activated": direct_activated,
                "self_team_activated": self_team_activated
            }
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

@router.get("/ved-counts")
async def get_ved_counts(
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Get Ved ID counts - eligible Ved count and non-eligible Ved count"""
    try:
        from app.core.scheduler import check_direct_referrals_both_sides, check_first_matching_achieved
        
        # Get all direct referrals ordered by registration date
        direct_referrals = db.query(User).filter(
            User.referrer_id == current_user.id
        ).order_by(User.registration_date).all()
        
        # Ved IDs start from 3rd referral onwards (3rd, 4th, 5th, etc.)
        total_ved_ids = max(0, len(direct_referrals) - 2) if len(direct_referrals) >= 3 else 0
        
        # Check if current user (Ved owner/referrer) meets eligibility requirements for Ved income
        has_1_1_active = check_direct_referrals_both_sides(db, current_user.id)
        has_first_matching = check_first_matching_achieved(db, current_user.id)
        is_ved_eligible = has_1_1_active and has_first_matching
        
        # Count eligible and non-eligible Ved IDs
        eligible_ved_count = 0
        non_eligible_ved_count = 0
        
        if len(direct_referrals) >= 3:
            ved_referrals = direct_referrals[2:]  # Get from 3rd position onwards
            
            for ved_ref in ved_referrals:
                # Ved member must be activated
                if ved_ref.activation_date is not None:
                    # If referrer (current_user) meets Ved income requirements, count as eligible
                    if is_ved_eligible:
                        eligible_ved_count += 1
                    else:
                        non_eligible_ved_count += 1
                else:
                    # Not activated yet = non-eligible
                    non_eligible_ved_count += 1
        
        return success_response(
            message="Ved counts retrieved successfully",
            data={
                "total_ved_ids": total_ved_ids,
                "eligible_ved_count": eligible_ved_count,
                "non_eligible_ved_count": non_eligible_ved_count,
                "is_ved_eligible": is_ved_eligible  # For debugging/display
            }
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

@router.get("/earnings-summary")
async def get_earnings_summary(
    current_user: User = Depends(require_activated_user),
    db: Session = Depends(get_db)
):
    """Get earnings summary by type - DC Protocol: Requires activated membership"""
    wallet_service = WalletService(db)
    result = wallet_service.get_earnings_summary(str(current_user.id))
    
    return success_response(
        message="Earnings summary retrieved successfully",
        data=result
    )

@router.get("/income-transactions")
async def get_income_transactions(
    days: int = 30,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Get income transactions for date-wise earnings breakdown - Mobile Parity"""
    from app.models.transaction import PendingIncome
    from datetime import datetime, timedelta
    
    query = db.query(PendingIncome).filter(
        PendingIncome.user_id == str(current_user.id)
    )
    
    if days > 0:
        start_date = datetime.now() - timedelta(days=days)
        query = query.filter(PendingIncome.created_at >= start_date)
    
    transactions = query.order_by(PendingIncome.business_date.desc()).all()
    
    result = []
    for t in transactions:
        result.append({
            "id": t.id,
            "business_date": t.business_date.isoformat() if t.business_date else None,
            "income_type": t.income_type,
            "gross_amount": float(t.gross_amount or 0),
            "net_amount": float(t.net_amount or 0),
            "points": 1,
            "verification_status": t.verification_status,
            "source_user_name": getattr(t, 'source_user_name', None),
            "created_at": t.created_at.isoformat() if t.created_at else None
        })
    
    return success_response(
        message="Income transactions retrieved successfully",
        data={"transactions": result, "total": len(result)}
    )

@router.get("/dashboard-data-fast")
async def get_dashboard_data_fast(
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db),
    response: Response = None
):
    """Ultra-fast dashboard using cached metrics (reduces load from 15-31s to <2s)"""
    try:
        # Prevent browser caching
        if response:
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        import time
        start_time = time.time()
        
        # DC Protocol: Staff users accessing MNR dashboard via Staff MNR Access System
        from app.models.staff import StaffEmployee
        if isinstance(current_user, StaffEmployee):
            print(f"[DC-STAFF-DASH] Staff user {current_user.id} accessed MNR dashboard-data-fast (not applicable for staff accounts)")
            return success_response(
                message="Dashboard data not applicable for staff accounts",
                data={
                    "is_staff_view": True,
                    "profile": {"id": str(current_user.id), "name": getattr(current_user, 'full_name', ''), "package_type": "N/A", "active_status": False},
                    "team": {"direct_referrals": 0, "matching_referrals_count": 0, "binary_tree": {"left_count": 0, "right_count": 0, "total_count": 0}, "binary_tree_active": {"left_count": 0, "right_count": 0, "total_count": 0}, "team_activated": 0},
                    "activated": {"direct_activated": 0, "self_team_activated": 0},
                    "ved": {"total_ved_ids": 0, "eligible_ved_count": 0, "non_eligible_ved_count": 0, "is_ved_eligible": False, "ved_head": None, "ved_team_total": 0, "ved_team_activated": 0, "ved_total": 0, "ved_eligible": 0},
                    "earnings": {"total_gross_earnings": 0},
                    "previous_counts": {},
                    "yesterday_earnings": {"Direct Referral": 0, "Matching Referral": 0, "Ved Income": 0, "Guru Dakshina": 0},
                    "yesterday_withdrawal": 0,
                    "wallet_summary": {"overall_earning": 0, "withdrawn": 0, "admin_pending": 0, "finance_pending": 0, "total_pending": 0}
                }
            )
        
        logger.debug(f"dashboard-data-fast called for user: {current_user.id}") if settings.DEBUG else None
        
        user_id = str(current_user.id)
        failed_sections = []
        wallet_service = WalletService(db)
        from app.services.leg_metrics_cache_service import LegMetricsCacheService
        
        # 1. User Profile Data (FAST)
        wallet_data = wallet_service.get_wallet_balance(user_id)
        package_points = getattr(current_user, 'package_points', 0) or 0
        package_name = current_user.get_package_type()
        
        # DC Protocol: Get award ranks for mobile parity
        from app.services.award_service import AwardService
        award_service = AwardService(db)
        direct_progress = award_service.get_user_direct_award_progress(user_id)
        matching_progress = award_service.get_user_matching_award_progress(user_id)
        
        direct_rank = "No Rank"
        matching_rank = "No Rank"
        for tier in direct_progress.get("tier_progress", []):
            if tier.get("achieved", False):
                direct_rank = tier.get("award_name", "No Rank")
        for tier in matching_progress.get("tier_progress", []):
            if tier.get("achieved", False):
                matching_rank = tier.get("award_name", "No Rank")
        
        # Compute active_status for mobile parity
        is_active = current_user.activation_date is not None
        
        # DC Protocol (Jan 2026): Welcome Coupon display
        is_welcome_coupon = getattr(current_user, 'is_welcome_coupon', False)
        display_package_name = "Welcome Coupon" if is_welcome_coupon else package_name
        display_payment = 0 if is_welcome_coupon else (15000 if package_points >= 1.0 else 7500 if package_points >= 0.5 else 0)
        
        profile_data = {
            "id": current_user.id,
            "name": current_user.name,
            "mnr_id": current_user.id,
            "email": current_user.email,
            "mobile": current_user.phone_number,
            "package_type": display_package_name,
            "package": display_package_name,
            "package_points": package_points,
            "registration_date": current_user.registration_date.isoformat() if current_user.registration_date else None,
            "activation_date": current_user.activation_date.isoformat() if current_user.activation_date else None,
            "active_status": is_active,
            "active_date": current_user.activation_date.isoformat() if current_user.activation_date else None,
            "direct_referral_rank": direct_rank,
            "matching_referral_rank": matching_rank,
            "coupon_status": current_user.coupon_status,
            "bank_name": current_user.bank_name,
            "wallet": wallet_data,
            "is_welcome_coupon": is_welcome_coupon,
            "is_exception_coupon": is_welcome_coupon,
            "payment_amount": display_payment,
            "points_display": 15000 if is_welcome_coupon else int(package_points * 30000) if package_points else 0,
            "receipt_downloadable": not is_welcome_coupon
        }
        
        # 2. Get cached metrics (INSTANT - no recursion!)
        cache_service = LegMetricsCacheService(db)
        cached_metrics = cache_service.get_user_metrics(user_id)
        
        # If no cache exists, create it on-demand (first time only)
        if not cached_metrics:
            print(f"⚠️ No cache for user {user_id}, creating on-demand...")
            cached_metrics = cache_service.refresh_user_metrics(user_id, source='on_demand')
        
        # Use cached data (FAST!) - Show ACTUAL counts (not delta)
        if cached_metrics:
            # Show actual counts directly (users expect to see their total team, not growth)
            display_direct_referrals = cached_metrics.total_direct_referrals
            display_active_referrals = cached_metrics.active_direct_referrals
            display_matching_count = cached_metrics.effective_matching_count
            display_left_team = cached_metrics.left_team_count
            display_right_team = cached_metrics.right_team_count
            display_left_active = cached_metrics.left_active_count
            display_right_active = cached_metrics.right_active_count
            
            team_data = {
                "direct_referrals": display_direct_referrals,
                "matching_referrals_count": display_matching_count,
                "binary_tree": {
                    "left_count": display_left_team,
                    "right_count": display_right_team,
                    "total_count": display_left_team + display_right_team
                },
                "binary_tree_active": {
                    "left_count": display_left_active,
                    "right_count": display_right_active,
                    "total_count": display_left_active + display_right_active
                },
                "team_activated": display_left_active + display_right_active
            }
            
            activated_data = {
                "direct_activated": display_active_referrals,
                "self_team_activated": display_left_active + display_right_active
            }
            
            # Ved eligibility from cache
            is_ved_eligible = cached_metrics.has_left_direct and cached_metrics.has_right_direct and cached_metrics.first_match_achieved
        else:
            # Fallback if cache fails (shouldn't happen)
            team_data = {
                "direct_referrals": 0,
                "matching_referrals_count": 0,
                "binary_tree": {"left_count": 0, "right_count": 0, "total_count": 0},
                "binary_tree_active": {"left_count": 0, "right_count": 0, "total_count": 0},
                "team_activated": 0
            }
            activated_data = {"direct_activated": 0, "self_team_activated": 0}
            is_ved_eligible = False
        
        # 3. Ved data calculation
        total_ved_ids = 0
        eligible_ved_count = 0
        non_eligible_ved_count = 0
        ved_head_data = None
        try:
            direct_referrals_ordered = db.query(User).filter(
                User.referrer_id == current_user.id
            ).order_by(User.registration_date.asc(), User.id.asc()).all()
            
            total_ved_ids = max(0, len(direct_referrals_ordered) - 2) if len(direct_referrals_ordered) >= 3 else 0
            
            if len(direct_referrals_ordered) >= 3:
                ved_head = direct_referrals_ordered[2]
                ved_head_data = {
                    "id": ved_head.id,
                    "name": ved_head.name,
                    "package": ved_head.get_package_type(),
                    "package_points": float(ved_head.package_points or 0),
                    "registration_date": ved_head.registration_date.isoformat() if ved_head.registration_date else None,
                    "activation_date": ved_head.activation_date.isoformat() if ved_head.activation_date else None,
                    "is_activated": ved_head.activation_date is not None,
                    "coupon_status": ved_head.coupon_status
                }
            
            if len(direct_referrals_ordered) >= 3:
                ved_referrals = direct_referrals_ordered[2:]
                for ved_ref in ved_referrals:
                    if ved_ref.activation_date is not None:
                        if is_ved_eligible:
                            eligible_ved_count += 1
                        else:
                            non_eligible_ved_count += 1
                    else:
                        non_eligible_ved_count += 1
        except Exception as ved_err:
            failed_sections.append("ved_data")
            logger.warning(f"[DC-PARTIAL] Ved data calculation failed for {user_id}: {ved_err}")
        
        # 3b. Ved Team Statistics (DC Protocol - READ FROM CACHE, NO RECALCULATION!)
        # Data updated only by: (1) midnight scheduler, (2) user activation
        # Dashboard performs pure SELECT - NO recursive queries for performance
        ved_team_total = 0
        ved_team_activated = 0
        
        if cached_metrics:
            # FAST: Read pre-calculated values from cache (DC Protocol - single source)
            ved_team_total = cached_metrics.ved_team_total or 0
            ved_team_activated = cached_metrics.ved_team_active or 0
        # No fallback calculation - if cache missing, return 0 (scheduler will update)
        
        # Ved counts: Show ACTUAL counts (no snapshot subtraction)
        # Matches Ved Team and Ved Income API behavior
        ved_data = {
            "total_ved_ids": total_ved_ids,
            "eligible_ved_count": eligible_ved_count,
            "non_eligible_ved_count": non_eligible_ved_count,
            "is_ved_eligible": is_ved_eligible,
            "ved_head": ved_head_data,  # NEW: Ved Head details (3rd position)
            "ved_team_total": ved_team_total,  # ACTUAL count (no baseline subtraction)
            "ved_team_activated": ved_team_activated,  # ACTUAL count (no baseline subtraction)
            "ved_total": ved_team_total,  # Frontend expects this field name
            "ved_eligible": ved_team_activated  # Frontend expects this field name
        }
        
        # 3c. Calculate PREVIOUS (Difference from Snapshot) - COUNTS
        previous_counts = {
            "direct_referrals": 0,
            "direct_activated": 0,
            "my_team": 0,
            "matching": 0,
            "left_team": 0,
            "left_active": 0,
            "right_team": 0,
            "right_active": 0,
            "ved_overall": 0,
            "ved_activated": 0
        }
        
        if cached_metrics:
            previous_counts = {
                "direct_referrals": (cached_metrics.total_direct_referrals or 0) - (cached_metrics.snapshot_direct_referrals or 0),
                "direct_activated": (cached_metrics.active_direct_referrals or 0) - (cached_metrics.snapshot_active_direct_referrals or 0),
                "my_team": ((cached_metrics.left_team_count or 0) + (cached_metrics.right_team_count or 0)) - ((cached_metrics.snapshot_left_team or 0) + (cached_metrics.snapshot_right_team or 0)),
                "matching": (cached_metrics.effective_matching_count or 0) - (cached_metrics.snapshot_matching_count or 0),
                "left_team": (cached_metrics.left_team_count or 0) - (cached_metrics.snapshot_left_team or 0),
                "left_active": (cached_metrics.left_active_count or 0) - (cached_metrics.snapshot_left_active or 0),
                "right_team": (cached_metrics.right_team_count or 0) - (cached_metrics.snapshot_right_team or 0),
                "right_active": (cached_metrics.right_active_count or 0) - (cached_metrics.snapshot_right_active or 0),
                # DC Protocol: Calculate Ved DELTA (daily change) from snapshot
                "ved_overall": ved_team_total - (cached_metrics.snapshot_ved_total or 0),
                "ved_activated": ved_team_activated - (cached_metrics.snapshot_ved_active or 0)
            }
        
        # 4. Earnings Summary (already fast)
        try:
            earnings_data = wallet_service.get_earnings_summary(user_id)
        except Exception as earn_err:
            failed_sections.append("earnings")
            logger.warning(f"[DC-PARTIAL] Earnings summary failed for {user_id}: {earn_err}")
            earnings_data = {"total_gross_earnings": 0, "direct_referral": 0, "matching_referral": 0, "ved_income": 0, "guru_dakshina": 0}
        
        # 5. Previous Earnings (difference from last snapshot)
        from datetime import datetime, timedelta
        from app.models.transaction import Transaction, PendingIncome
        
        yesterday_earnings = {}
        yesterday_withdrawal = 0.0
        expected_types = ['Direct Referral', 'Matching Referral', 'Ved Income', 'Guru Dakshina']
        try:
            yesterday_start = (datetime.now() - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            yesterday_end = (datetime.now() - timedelta(days=1)).replace(hour=23, minute=59, second=59, microsecond=999999)
            
            yesterday_txn = db.query(
                Transaction.transaction_type,
                func.sum(Transaction.amount).label('total')
            ).filter(
                Transaction.referrer_id == user_id,
                Transaction.timestamp.between(yesterday_start, yesterday_end)
            ).group_by(Transaction.transaction_type).all()
            
            yesterday_pending = db.query(
                PendingIncome.income_type,
                func.sum(PendingIncome.gross_amount).label('total')
            ).filter(
                PendingIncome.user_id == user_id,
                PendingIncome.business_date.between(yesterday_start, yesterday_end)
            ).group_by(PendingIncome.income_type).all()
            
            for earning_type, total in yesterday_txn:
                yesterday_earnings[str(earning_type)] = float(total or 0)
            for earning_type, total in yesterday_pending:
                current = yesterday_earnings.get(str(earning_type), 0.0)
                yesterday_earnings[str(earning_type)] = current + float(total or 0)
        except Exception as yest_err:
            failed_sections.append("yesterday_earnings")
            logger.warning(f"[DC-PARTIAL] Yesterday earnings query failed for {user_id}: {yest_err}")
        
        for income_type in expected_types:
            if income_type not in yesterday_earnings:
                yesterday_earnings[income_type] = 0.0
        
        # Wallet Summary (for Overall - Wallet section)
        wallet_summary = {
            "overall_earning": 0,
            "withdrawn": 0,
            "admin_pending": 0,
            "finance_pending": 0,
            "total_pending": 0
        }
        try:
            wallet_summary_data = wallet_service.get_earnings_summary(user_id)
            total_gross_earnings = wallet_summary_data.get('total_gross_earnings', 0)
            
            all_income = db.query(PendingIncome).filter(
                PendingIncome.user_id == user_id
            ).all()
            
            PAID_STATUSES = ['Completed', 'Completed']
            finance_paid = [t for t in all_income if t.verification_status in PAID_STATUSES]
            withdrawn_gross_db = sum(float(t.gross_amount or 0) for t in finance_paid if t.income_type != 'Ved Income')
            
            ved_income_withdrawn = sum(float(t.gross_amount or 0) for t in finance_paid if t.income_type == 'Ved Income')
            withdrawn_gross = withdrawn_gross_db + ved_income_withdrawn
            
            total_pending_gross = total_gross_earnings - withdrawn_gross
            
            admin_pending_gross = sum(float(t.gross_amount or 0) for t in all_income if t.verification_status == 'Pending' and t.income_type != 'Ved Income')
            
            finance_pending_gross = sum(float(t.gross_amount or 0) for t in all_income if t.verification_status in ('Admin Verified', 'Super Admin Approved') and t.income_type != 'Ved Income')
            
            from app.services.reference_service import ReferenceService
            reference_service = ReferenceService(db)
            ved_income_data = reference_service.calculate_ved_income(user_id, "1970-01")
            calculated_ved_income = float(ved_income_data.get('ved_amount', 0)) if ved_income_data else 0
            
            wallet_summary = {
                "overall_earning": round(total_gross_earnings),
                "withdrawn": round(withdrawn_gross),
                "admin_pending": round(admin_pending_gross),
                "finance_pending": round(finance_pending_gross),
                "total_pending": round(total_pending_gross)
            }
        except Exception as wallet_err:
            failed_sections.append("wallet_summary")
            logger.warning(f"[DC-PARTIAL] Wallet summary calculation failed for {user_id}: {wallet_err}")
        
        elapsed = time.time() - start_time
        print(f"⚡ CACHED dashboard load time: {elapsed:.3f}s (was 15-31s before cache!)")
        
        # Combine all data
        dashboard_data = {
            "profile": profile_data,
            "team": team_data,
            "activated": activated_data,
            "ved": ved_data,
            "earnings": earnings_data,
            "previous_counts": previous_counts,  # NEW: Difference from snapshot
            "yesterday_earnings": yesterday_earnings,  # Keep for backward compatibility
            "yesterday_withdrawal": float(yesterday_withdrawal),
            "wallet_summary": wallet_summary
        }
        
        if failed_sections:
            dashboard_data["partial_data"] = True
            dashboard_data["failed_sections"] = failed_sections
            logger.warning(f"[DC-PARTIAL] Dashboard for {user_id} returned partial data. Failed: {failed_sections}")
        
        logger.debug(f"🎯 RETURNING DATA for {current_user.id}:")
        print(f"   Direct Referrals: {team_data['direct_referrals']}")
        print(f"   Left Team: {team_data['binary_tree']['left_count']}")
        print(f"   Right Team: {team_data['binary_tree']['right_count']}")
        print(f"   Right Active: {team_data['binary_tree_active']['right_count']}")
        print(f"   Matching: {team_data['matching_referrals_count']}")
        
        return success_response(
            message="Dashboard data retrieved successfully" if not failed_sections else "Dashboard data retrieved with partial sections",
            data=dashboard_data
        )
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

@router.get("/dashboard-data")
async def get_dashboard_data(
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Get all dashboard data in a single optimized call"""
    try:
        import time
        start_time = time.time()
        
        from app.services.reference_service import ReferenceService
        from app.core.scheduler import check_direct_referrals_both_sides, check_first_matching_achieved
        
        user_id = str(current_user.id)
        reference_service = ReferenceService(db)
        wallet_service = WalletService(db)
        
        # 1. User Profile Data
        t1 = time.time()
        wallet_data = wallet_service.get_wallet_balance(user_id)
        logger.debug(f"⏱️ Wallet balance: {time.time() - t1:.3f}s")
        package_points = getattr(current_user, 'package_points', 0) or 0
        package_name = current_user.get_package_type()  # NEW decimal system: 1=Platinum, 0.5=Diamond, 0=Star/Loyal
        
        profile_data = {
            "id": current_user.id,
            "name": current_user.name,
            "email": current_user.email,
            "package_type": package_name,
            "package_points": package_points,
            "registration_date": current_user.registration_date.isoformat() if current_user.registration_date else None,
            "coupon_status": current_user.coupon_status,
            "bank_name": current_user.bank_name,
            "wallet": wallet_data
        }
        
        # 2. Team Counts (both all and active)
        t2 = time.time()
        team_stats_all = reference_service.get_team_counts(user_id, active_only=False)
        logger.debug(f"⏱️ Team stats all: {time.time() - t2:.3f}s")
        
        t3 = time.time()
        team_stats_active = reference_service.get_team_counts(user_id, active_only=True)
        logger.debug(f"⏱️ Team stats active: {time.time() - t3:.3f}s")
        
        # Get matching referrals count
        from app.core.scheduler import calculate_effective_matching_count
        t4 = time.time()
        matching_result = calculate_effective_matching_count(db, user_id)
        logger.debug(f"⏱️ Matching count: {time.time() - t4:.3f}s")
        
        team_data = {
            "direct_referrals": team_stats_all.get('direct_referrals', 0),
            "matching_referrals_count": matching_result['effective_count'],
            "binary_tree": team_stats_all,
            "binary_tree_active": team_stats_active,
            "team_activated": team_stats_active.get('total_count', 0)
        }
        
        # 3. Activated Counts
        direct_refs = db.query(User).filter(User.referrer_id == current_user.id).all()
        direct_activated = sum(1 for ref in direct_refs if ref.activation_date is not None)
        
        activated_data = {
            "direct_activated": direct_activated,
            "self_team_activated": team_stats_active.get('total_count', 0)
        }
        
        # 4. Ved Counts - Query actual Ved members from database
        # VED PROGRAM RULE: ONLY 3rd direct referral becomes Ved Head
        # Query all Ved members owned by this user
        ved_members_all = db.query(User).filter(
            User.ved_owner_id == current_user.id,
            User.is_ved == True
        ).all()
        
        # Count activated Ved members (activation_date + package_points >= 0.5)
        ved_members_activated = [
            vm for vm in ved_members_all 
            if vm.activation_date is not None and (vm.package_points or 0) >= 0.5
        ]
        
        # Check Ved income eligibility
        has_1_1_active = check_direct_referrals_both_sides(db, current_user.id)
        has_first_matching = check_first_matching_achieved(db, current_user.id)
        is_ved_eligible = has_1_1_active and has_first_matching
        
        ved_data = {
            "total_ved_ids": len(ved_members_all),
            "eligible_ved_count": len(ved_members_activated) if is_ved_eligible else 0,
            "non_eligible_ved_count": len(ved_members_all) - len(ved_members_activated),
            "is_ved_eligible": is_ved_eligible
        }
        
        # 5. Earnings Summary
        t5 = time.time()
        earnings_data = wallet_service.get_earnings_summary(user_id)
        logger.debug(f"⏱️ Earnings summary: {time.time() - t5:.3f}s")
        
        logger.debug(f"⏱️ TOTAL dashboard load time: {time.time() - start_time:.3f}s")
        
        # Combine all data
        dashboard_data = {
            "profile": profile_data,
            "team": team_data,
            "activated": activated_data,
            "ved": ved_data,
            "earnings": earnings_data
        }
        
        return success_response(
            message="Dashboard data retrieved successfully",
            data=dashboard_data
        )
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

@router.post("/withdrawal-request")
async def request_withdrawal(
    withdrawal_data: WithdrawalRequest,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Submit a withdrawal request"""
    wallet_service = WalletService(db)
    result = wallet_service.request_withdrawal(
        user_id=str(current_user.id),
        amount=withdrawal_data.amount,
        withdrawal_type=withdrawal_data.withdrawal_type
    )
    
    if result.get('success'):
        AuditLogger.log_financial_operation(
            db=db,
            user=current_user,
            operation='WITHDRAWAL_REQUEST',
            amount=withdrawal_data.amount,
            transaction_id=result.get('request_id'),
            details={'type': withdrawal_data.withdrawal_type}
        )
        
        return success_response(
            message=result.get('message', 'Withdrawal request submitted'),
            data=result
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get('error', 'Withdrawal request failed')
        )

@router.get("/withdrawal-requests")
async def get_withdrawal_requests(
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """
    Get user's withdrawal requests - DC Protocol Phase 1.7
    Uses WithdrawalRequest table (correct source) instead of Transaction table
    """
    from app.models.withdrawal import WithdrawalRequest
    
    # Query the CORRECT table - withdrawal_request
    withdrawals = db.query(WithdrawalRequest).filter(
        WithdrawalRequest.user_id == str(current_user.id)
    ).order_by(WithdrawalRequest.created_at.desc()).limit(50).all()
    
    # Format response to match frontend expectations
    withdrawal_list = [
        {
            "id": w.id,
            "withdrawal_amount": float(w.withdrawal_amount or 0),
            "final_payout": float(w.final_payout or 0),
            "status": w.status,
            "created_at": w.created_at.isoformat() if w.created_at else None,
            "payment_reference": w.payment_reference,
            "payment_date": w.payment_date.isoformat() if w.payment_date else None
        }
        for w in withdrawals
    ]
    
    return withdrawal_list  # Frontend expects direct array, not wrapped in success_response

# ===== TEAM & REFERRALS =====

@router.get("/team")
async def get_user_team(
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Get user's team (direct referrals)"""
    try:
        from app.services.reference_service import ReferenceService
        
        reference_service = ReferenceService(db)
        team_data = reference_service.get_user_team(str(current_user.id))
        
        return success_response(
            message="Team data retrieved successfully",
            data=team_data
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

@router.get("/team/downline")
async def get_downline_tree(
    levels: int = 5,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Get user's complete downline tree"""
    try:
        from app.services.reference_service import ReferenceService
        
        reference_service = ReferenceService(db)
        downline = reference_service.get_downline_tree(str(current_user.id), levels)
        
        return success_response(
            message="Downline tree retrieved successfully",
            data={"downline": downline, "levels": levels}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

@router.get("/team/stats")
async def get_team_statistics(
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Get team statistics"""
    try:
        from app.services.reference_service import ReferenceService
        from app.models.user import User as UserModel
        
        reference_service = ReferenceService(db)
        team_counts = reference_service.get_team_counts(str(current_user.id))
        
        # Get direct referrals count
        direct_referrals = db.query(UserModel).filter(
            UserModel.referrer_id == str(current_user.id)
        ).count()
        
        stats = {
            "left_team_count": team_counts["left_count"],
            "right_team_count": team_counts["right_count"],
            "total_team_size": team_counts["total_count"],
            "direct_referrals": direct_referrals
        }
        
        return success_response(
            message="Team statistics retrieved successfully",
            data=stats
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

@router.get("/team/all-members")
async def get_all_team_members(
    position: str = None,
    level: str = None,
    referrer_id: str = None,
    ved_owner_id: str = None,
    user_id: str = None,
    start_date: str = None,
    end_date: str = None,
    package: str = None,
    status_filter: str = None,
    coupon_status: str = None,
    name: str = None,
    include_removed: bool = False,
    page: int = 1,
    page_size: int = 50,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Fast paginated endpoint to get all downline members - optimized for 233+ users with referrer and ved owner filters"""
    try:
        from app.services.sql_utils import get_binary_downline_sql
        from datetime import datetime
        
        # For admin users, allow filtering by specific user_id
        target_user_id = str(current_user.id)
        if user_id and (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) in ['Admin', 'Finance Admin', 'Super Admin', 'RVZ ID']:
            target_user_id = user_id
        
        # Get ALL downline members using recursive SQL (fast!)
        downline_members = get_binary_downline_sql(
            db=db,
            parent_id=target_user_id,
            max_depth=20,  # Deep tree support
            active_only=False,
            package_filter=None
        )
        
        # Now apply filters in Python
        filtered_members = []
        
        package_points_map = {
            "Platinum": 1.0,
            "Diamond": 0.5,
            "Star": 0.0,
            "Loyal": 0.0,
            "Eligible": 0.0
        }
        
        for member in downline_members:
            # Position filter (Left/Right)
            if position and position.lower() in ['left', 'right']:
                if member['side'] and member['side'].lower() != position.lower():
                    continue
            
            # Level filter
            if level is not None and level.strip():
                level_int = int(level) if level.isdigit() else None
                if level_int is not None:
                    if level_int == 10:  # "10+" means 10 or more
                        if member['level'] < 10:
                            continue
                    elif member['level'] != level_int:
                        continue
            
            # Package filter
            if package and package.strip():
                if package in package_points_map:
                    if member['package_points'] != package_points_map[package]:
                        continue
            
            # Status filter (Active/Inactive)
            if status_filter:
                is_active = member['activation_date'] is not None
                if status_filter.lower() == 'active' and not is_active:
                    continue
                elif status_filter.lower() == 'inactive' and is_active:
                    continue
            
            # Coupon status filter
            if coupon_status and member.get('coupon_status') != coupon_status:
                continue
            
            # Referrer ID filter - needs database lookup
            if referrer_id and referrer_id.strip():
                user_record = db.query(User).filter(User.id == member['id']).first()
                if not user_record or user_record.referrer_id != referrer_id:
                    continue
            
            # Ved Owner ID filter - needs database lookup
            if ved_owner_id and ved_owner_id.strip():
                user_record = db.query(User).filter(User.id == member['id']).first()
                if not user_record or user_record.ved_owner_id != ved_owner_id:
                    continue
            
            # Name/ID filter (case-insensitive partial match - searches BOTH name and MNR ID)
            if name and name.strip():
                member_name = member.get('name', '').lower()
                member_id = str(member.get('id', '')).lower()
                search_name = name.strip().lower()
                # Match if search text is in EITHER name OR ID
                if search_name not in member_name and search_name not in member_id:
                    continue
            
            # Date range filters
            if start_date and member.get('registration_date'):
                reg_date = member['registration_date']
                if isinstance(reg_date, str):
                    reg_date = datetime.fromisoformat(reg_date.replace('Z', '+00:00'))
                start_dt = datetime.fromisoformat(start_date)
                if reg_date < start_dt:
                    continue
            
            if end_date and member.get('registration_date'):
                reg_date = member['registration_date']
                if isinstance(reg_date, str):
                    reg_date = datetime.fromisoformat(reg_date.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end_date)
                if reg_date > end_dt:
                    continue
            
            filtered_members.append(member)
        
        # Pagination
        total_count = len(filtered_members)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_members = filtered_members[start_idx:end_idx]
        
        # Fetch referrer_id and ved_owner information for paginated members
        member_ids = [m['id'] for m in paginated_members]
        user_records = db.query(User).filter(User.id.in_(member_ids)).all()
        user_dict = {u.id: u for u in user_records}
        
        # Fetch ved owner names
        ved_owner_ids = [u.ved_owner_id for u in user_records if u.ved_owner_id]
        ved_owners = db.query(User).filter(User.id.in_(ved_owner_ids)).all() if ved_owner_ids else []
        ved_owner_names = {vo.id: vo.name for vo in ved_owners}
        
        # Format response with referrer_id and ved_owner
        members_list = []
        for m in paginated_members:
            user_record = user_dict.get(m['id'])
            ved_owner_name = None
            if user_record and user_record.ved_owner_id:
                ved_owner_name = ved_owner_names.get(user_record.ved_owner_id, user_record.ved_owner_id)
            
            members_list.append({
                "mnr_id": str(m['id']),
                "name": m['name'],
                "package": user_record.get_package_type() if user_record else ("Platinum" if m['package_points'] == 1.0 else "Diamond" if m['package_points'] == 0.5 else "Eligible"),
                "position": m['side'].capitalize() if m['side'] else "Root",
                "level": m['level'],
                "registration_date": m['registration_date'].isoformat() if m['registration_date'] else None,
                "activation_date": m['activation_date'].isoformat() if m['activation_date'] else None,
                "status": "Active" if m['activation_date'] else "Inactive",
                "coupon_status": m.get('coupon_status') or "N/A",
                "referrer_id": user_record.referrer_id if user_record else None,
                "ved_owner_id": user_record.ved_owner_id if user_record else None,
                "ved_owner_name": ved_owner_name
            })
        
        return success_response(
            message=f"Team members retrieved (page {page}/{((total_count-1)//page_size)+1 if total_count > 0 else 1})",
            data={
                "members": members_list,
                "total": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": ((total_count - 1) // page_size) + 1 if total_count > 0 else 1
            }
        )
    except Exception as e:
        import traceback
        logger.error(f"Error in get_all_team_members: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

@router.get("/team/direct-referrals-filtered")
async def get_direct_referrals_filtered(
    user_id: str = None,
    start_date: str = None,
    end_date: str = None,
    package: str = None,
    status_filter: str = None,
    coupon_status: str = None,
    position: str = None,
    name: str = None,
    include_removed: bool = False,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Get direct referrals with filters (admins can specify user_id)"""
    try:
        # Determine target user ID: use provided user_id if admin, otherwise current user
        target_user_id = None
        if user_id and (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) in ['Admin', 'Super Admin', 'Finance Admin', 'RVZ ID']:
            # Admin requesting another user's data
            target_user_id = user_id
        else:
            # Regular user or admin viewing their own data
            target_user_id = str(current_user.id) if current_user.id else None
        
        query = db.query(User).filter(User.referrer_id == target_user_id)
        
        # Apply filters
        if start_date:
            start_dt = datetime.fromisoformat(start_date)
            query = query.filter(User.registration_date >= start_dt)
        
        if end_date:
            end_dt = datetime.fromisoformat(end_date)
            query = query.filter(User.registration_date <= end_dt)
        
        # Package filter
        if package and package != "All Packages":
            query = query.filter(User.package_points == {
                "Platinum": 1.0, "Diamond": 0.5, "Star": 0.0, "Eligible": 0.0, "Loyal": 0.0
            }.get(package, -1))
        
        if status_filter and status_filter.lower() == 'active':
            query = query.filter(User.activation_date.isnot(None))
        elif status_filter and status_filter.lower() == 'inactive':
            query = query.filter(User.activation_date.is_(None))
        
        if coupon_status and coupon_status != "All":
            query = query.filter(User.coupon_status == coupon_status)
        
        # Name filter (case-insensitive partial match)
        if name and name.strip():
            query = query.filter(User.name.ilike(f"%{name.strip()}%"))
        
        # Position filter (left/right/root placement)
        if position and position.lower() in ['left', 'right', 'root']:
            query = query.filter(User.position == position.lower())
        
        referrals = query.order_by(User.registration_date.desc()).all()
        
        from app.models.placement import Placement
        null_position_ids = [str(r.id) for r in referrals if not r.position]
        placement_lookup = {}
        if null_position_ids:
            placements = db.query(Placement.child_id, Placement.side).filter(
                Placement.child_id.in_(null_position_ids),
                Placement.status == 'active'
            ).all()
            placement_lookup = {p.child_id: p.side.upper() if p.side else None for p in placements}
        
        def get_group_label(r):
            pos = r.position
            if not pos:
                pos = placement_lookup.get(str(r.id))
            if not pos:
                return "-"
            pos_upper = pos.upper()
            if pos_upper in ('LEFT', 'L'):
                return "Group A"
            elif pos_upper in ('RIGHT', 'R'):
                return "Group B"
            return pos.capitalize()
        
        referrals_list = [
            {
                "mnr_id": str(r.id),
                "name": r.name,
                "package": r.get_package_type() if r else "N/A",
                "position": get_group_label(r),
                "registration_date": r.registration_date.isoformat() if r.registration_date else None,
                "activation_date": r.activation_date.isoformat() if r.activation_date else None,
                "status": "Active" if r.activation_date else "Inactive",
                "coupon_status": r.coupon_status or "N/A"
            }
            for r in referrals
        ]
        
        return success_response(
            message="Direct referrals retrieved successfully",
            data={"referrals": referrals_list, "total": len(referrals_list)}
        )
    except Exception as e:
        import traceback
        logger.error(f"Error in get_direct_referrals_filtered: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

@router.get("/team/ved-members")
async def get_ved_members_filtered(
    user_id: str = None,
    start_date: str = None,
    end_date: str = None,
    package: str = None,
    status_filter: str = None,
    coupon_status: str = None,
    position: str = None,
    level: str = None,
    name: str = None,
    include_removed: bool = False,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Get Ved team members with filters (admins can specify user_id)"""
    try:
        from app.services.sql_utils import get_binary_downline_sql
        
        # Determine target user ID: use provided user_id if admin, otherwise current user
        target_user_id = None
        if user_id and (getattr(current_user, 'staff_type', None) or (getattr(current_user, 'staff_type', None) or getattr(current_user, 'user_type', ''))) in ['Admin', 'Super Admin', 'Finance Admin', 'RVZ ID']:
            target_user_id = user_id
        else:
            target_user_id = str(current_user.id) if current_user.id else None
        
        # DC PROTOCOL FIX (Dec 27, 2025): Removed incorrect is_ved check
        # A user who is_ved=TRUE means THEIR Ved position income goes to their Ved Owner
        # But they can STILL have their OWN Ved Team (3rd+ direct referrals) and earn Ved Income from THAT team
        # The is_ved status should NOT block viewing their own Ved Team
        target_user = db.query(User).filter(User.id == target_user_id).first()
        
        # Get all direct referrals ordered by REGISTRATION date
        all_referrals = db.query(User).filter(
            User.referrer_id == target_user_id
        ).order_by(User.registration_date.asc(), User.id.asc()).all()
        
        # CORRECT LOGIC: Only the 3rd registered direct referral is a Ved (NOT 4th, 5th, 6th+)
        ved_root = all_referrals[2] if len(all_referrals) >= 3 else None
        
        # If no Ved root exists, return empty
        if not ved_root:
            return success_response(
                message="No Ved members found",
                data={"ved_members": [], "total": 0, "is_ved": current_user.is_ved or False, "ved_owner": current_user.ved_owner_id}
            )
        
        # Get the ENTIRE binary tree downline of the Ved root ONLY
        all_ved_members = []
        
        # Process only the single Ved root
        idx = 3  # Position 3
        
        # DC PROTOCOL: Use ved_team_member table as SINGLE SOURCE
        # Show ALL members (active AND removed) for complete visibility
        ved_team_query = text("""
            SELECT 
                vtm.member_id as user_id,
                u.name,
                u.package_points,
                u.activation_date,
                u.registration_date,
                u.coupon_status,
                u.is_ved,
                u.ved_owner_id,
                u.referrer_id,
                vtm.position as side,
                vtm.level,
                vtm.is_active,
                vtm.removed_date
            FROM ved_team_member vtm
            INNER JOIN "user" u ON u.id = vtm.member_id
            WHERE vtm.ved_owner_id = :current_user
                AND vtm.ved_head_id = :ved_root_id
                AND (CAST(:include_removed AS BOOLEAN) = true OR vtm.is_active = true)
            ORDER BY vtm.level, u.name
        """)
        
        result = db.execute(ved_team_query, {
            'ved_root_id': str(ved_root.id),
            'current_user': target_user_id,
            'include_removed': include_removed
        })
        downline_members = result.fetchall()
        
        # Add the Ved root itself
        # CRITICAL: Ved Head status shows if income is being generated
        # "Active" = Ved Head activated → Income goes to owner
        # "Missed" = Ved Head NOT activated → NO income generated
        ved_head_activated = ved_root.activation_date is not None and (ved_root.package_points or 0) >= 0.5
        ved_income_status = "Active" if ved_head_activated else "Missed"
        
        root_data = {
            "mnr_id": str(ved_root.id),
            "name": ved_root.name,
            "package": ved_root.get_package_type() if ved_root else "N/A",
            "registration_date": ved_root.registration_date.isoformat() if ved_root.registration_date else None,
            "activation_date": ved_root.activation_date.isoformat() if ved_root.activation_date else None,
            "status": "Active" if ved_root.activation_date else "Inactive",
            "ved_income_status": ved_income_status,
            "coupon_status": ved_root.coupon_status or "N/A",
            "ved_position": idx,
            "is_ved_root": True,
            "downline_count": len(downline_members),
            "position": "Root",
            "level": 0,
            "is_ved_head_activated": ved_head_activated,
            "ved_income_note": "Generating income" if ved_head_activated else "Income missed (Ved Head not activated)"
        }
        
        # ALWAYS include Ved Head regardless of filters (critical for visibility)
        # Package/status filters should only apply to Ved Team members, not Ved Head
        all_ved_members.append(root_data)
        
        # Add all downline members
        for downline in downline_members:
            # Map package_points to package type
            pkg_points = downline.package_points or 0
            if pkg_points >= 1.0:
                pkg_type = "Platinum"
            elif pkg_points >= 0.5:
                pkg_type = "Diamond"
            elif pkg_points > 0:
                pkg_type = "Star"
            else:
                pkg_type = "Eligible"
            
            # Determine member status - show if removed from Ved Team
            member_status = "Active" if downline.activation_date else "Inactive"
            if not downline.is_active and downline.removed_date:
                member_status = "Moved"
            
            downline_data = {
                "mnr_id": str(downline.user_id),
                "name": downline.name,
                "package": pkg_type,
                "registration_date": downline.registration_date.isoformat() if downline.registration_date else None,
                "activation_date": downline.activation_date.isoformat() if downline.activation_date else None,
                "status": member_status,
                "coupon_status": downline.coupon_status or "N/A",
                "ved_position": idx,
                "ved_root_id": str(ved_root.id),
                "ved_root_name": ved_root.name,
                "is_ved_root": False,
                "level": downline.level,
                "position": downline.side.capitalize() if downline.side else "N/A",
                "is_active_in_ved": downline.is_active,
                "removed_date": downline.removed_date.isoformat() if downline.removed_date else None
            }
            
            # Apply filters to downline member
            if _apply_ved_filters(downline_data, start_date, end_date, package, status_filter, coupon_status, position, level, name):
                all_ved_members.append(downline_data)
        
        # Separate Ved Head from Ved Team members for frontend display
        ved_head_info = root_data if root_data in all_ved_members else root_data
        ved_team_members = [m for m in all_ved_members if not m.get('is_ved_root', False)]
        
        return success_response(
            message="Ved members retrieved successfully",
            data={
                "ved_head": ved_head_info,  # NEW: Separate Ved Head for prominent display
                "ved_members": ved_team_members,  # Ved Team (excluding Ved Head)
                "all_ved_members": all_ved_members,  # Complete list including Ved Head
                "total": len(all_ved_members),
                "ved_team_count": len(ved_team_members),
                "is_ved": current_user.is_ved or False,
                "ved_owner": current_user.ved_owner_id
            }
        )
    except Exception as e:
        import traceback
        logger.error(f"Error in get_ved_members_filtered: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

def _apply_ved_filters(member_data: dict, start_date: str, end_date: str, package: str, status_filter: str, coupon_status: str, position: str = None, level: str = None, name: str = None) -> bool:
    """Helper function to apply filters to Ved members"""
    # Name filter (case-insensitive partial match)
    if name and name.strip():
        member_name = member_data.get('name', '').lower()
        search_name = name.strip().lower()
        if search_name not in member_name:
            return False
    
    # Position filter
    if position and position != "All Positions":
        member_position = member_data.get("position", "").lower()
        if position.lower() == "left" and member_position != "left":
            return False
        elif position.lower() == "right" and member_position != "right":
            return False
        elif position.lower() == "root" and member_position != "root":
            return False
    
    # Level filter
    if level and level != "All Levels":
        try:
            level_num = int(level)
            if member_data.get("level") != level_num:
                return False
        except (ValueError, TypeError):
            pass
    
    # Date filter
    if start_date and member_data.get("registration_date"):
        try:
            reg_date = datetime.fromisoformat(member_data["registration_date"].replace('Z', '+00:00'))
            filter_date = datetime.fromisoformat(start_date)
            if reg_date < filter_date:
                return False
        except:
            pass
    
    if end_date and member_data.get("registration_date"):
        try:
            reg_date = datetime.fromisoformat(member_data["registration_date"].replace('Z', '+00:00'))
            filter_date = datetime.fromisoformat(end_date)
            if reg_date > filter_date:
                return False
        except:
            pass
    
    # Package filter
    if package and package != "All Packages" and member_data.get("package") != package:
        return False
    
    # Status filter
    if status_filter:
        if status_filter.lower() == 'active' and member_data.get("status") != "Active":
            return False
        if status_filter.lower() == 'inactive' and member_data.get("status") == "Active":
            return False
    
    # Coupon status filter
    if coupon_status and coupon_status != "All" and member_data.get("coupon_status") != coupon_status:
        return False
    
    return True

@router.get("/team/matching-members")
async def get_matching_members(
    side: str = None,
    start_date: str = None,
    end_date: str = None,
    package: str = None,
    status_filter: str = None,
    coupon_status: str = None,
    root_user: str = None,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Get ALL matching referral (binary tree) members with filters - OPTIMIZED with bulk SQL"""
    try:
        from app.services.sql_utils import get_binary_downline_sql
        
        # Use root_user if provided (for viewing downline of specific user), else current user
        user_id = root_user if root_user else str(current_user.id)
        
        # Get ALL downline members in ONE optimized query (100x faster!)
        all_members_data = get_binary_downline_sql(
            db=db,
            parent_id=user_id,
            max_depth=10,  # Reduced from 20 to 10 levels for faster loading
            active_only=False,  # Get all members regardless of status
            package_filter=None  # No package filter in bulk query
        )
        
        # Apply filters on bulk data - ALL in Python memory (super fast!)
        filtered_members = []
        for member_data in all_members_data:
            member_id = member_data.get("id")
            member_name = member_data.get("name", "Unknown")
            member_pkg_points = member_data.get("package_points", 0)
            member_activation = member_data.get("activation_date")
            member_registration = member_data.get("registration_date")
            member_coupon_status = member_data.get("coupon_status")
            member_side = member_data.get("side")  # 'left' or 'right'
            
            # Map package_points to package_type
            if member_pkg_points >= 1.0:
                pkg_type = "Platinum"
            elif member_pkg_points >= 0.5:
                pkg_type = "Diamond"
            elif member_pkg_points > 0:
                pkg_type = "Star"
            else:
                pkg_type = "Eligible"
            
            # Side filter
            if side and side.lower() in ['left', 'right'] and member_side != side.lower():
                continue
            
            # Package filter
            if package and package != "All Packages" and pkg_type != package:
                continue
            
            # Status filter
            if status_filter and status_filter.lower() == 'active' and not member_activation:
                continue
            if status_filter and status_filter.lower() == 'inactive' and member_activation:
                continue
            
            # Date filter - NO database query needed!
            if start_date and member_registration:
                try:
                    if member_registration < datetime.fromisoformat(start_date):
                        continue
                except:
                    pass
            if end_date and member_registration:
                try:
                    if member_registration > datetime.fromisoformat(end_date):
                        continue
                except:
                    pass
            
            # Coupon status filter - NO database query needed!
            if coupon_status and coupon_status != "All":
                if member_coupon_status != coupon_status:
                    continue
            
            filtered_members.append({
                "mnr_id": str(member_id),
                "name": member_name,
                "package": pkg_type,
                "position": member_side.capitalize() if member_side else "Unknown",
                "registration_date": member_registration.isoformat() if member_registration else None,
                "activation_date": member_activation.isoformat() if member_activation else None,
                "status": "Active" if member_activation else "Inactive",
                "coupon_status": member_coupon_status or "N/A",
                "points": float(member_pkg_points)
            })
        
        return success_response(
            message="Matching members retrieved successfully",
            data={"members": filtered_members, "total": len(filtered_members)}
        )
    except Exception as e:
        import traceback
        logger.error(f"Error in get_matching_members: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

@router.get("/team/binary-tree")
async def get_binary_tree(
    user_id: str = None,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Get binary tree structure with root user and nested children up to 4 levels for picture view"""
    try:
        from app.models.placement import Placement
        
        # Use provided user_id or current user
        target_user_id = user_id if user_id else str(current_user.id)
        
        # Get root user
        root_user = db.query(User).filter(User.id == target_user_id).first()
        if not root_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        def user_to_dict(user):
            if not user:
                return None
            return {
                "mnr_id": str(user.id),
                "name": user.name,
                "package": user.get_package_type() if user else "N/A",
                "registration_date": user.registration_date.isoformat() if user.registration_date else None,
                "activation_date": user.activation_date.isoformat() if user.activation_date else None,
                "status": "Active" if user.activation_date else "Inactive",
                "coupon_status": user.coupon_status or "N/A"
            }
        
        def get_children_recursive(parent_id: str, max_depth: int = 4, current_depth: int = 0):
            """Recursively get children up to max_depth levels"""
            if current_depth >= max_depth:
                return None
            
            # Get left child - SHOW ALL (not just active)
            left_placement = db.query(Placement, User).join(
                User, Placement.child_id == User.id
            ).filter(
                Placement.parent_id == parent_id,
                Placement.side == 'left'
            ).first()
            
            # Get right child - SHOW ALL (not just active)
            right_placement = db.query(Placement, User).join(
                User, Placement.child_id == User.id
            ).filter(
                Placement.parent_id == parent_id,
                Placement.side == 'right'
            ).first()
            
            left_user = left_placement[1] if left_placement else None
            right_user = right_placement[1] if right_placement else None
            
            result = {}
            
            if left_user:
                left_dict = user_to_dict(left_user)
                # Recursively get children of left child
                left_children = get_children_recursive(str(left_user.id), max_depth, current_depth + 1)
                if left_children and (left_children.get('left_child') or left_children.get('right_child')):
                    left_dict.update(left_children)
                result['left_child'] = left_dict
            else:
                result['left_child'] = None
            
            if right_user:
                right_dict = user_to_dict(right_user)
                # Recursively get children of right child
                right_children = get_children_recursive(str(right_user.id), max_depth, current_depth + 1)
                if right_children and (right_children.get('left_child') or right_children.get('right_child')):
                    right_dict.update(right_children)
                result['right_child'] = right_dict
            else:
                result['right_child'] = None
            
            return result
        
        # Build tree with nested children
        tree_data = {
            "root": user_to_dict(root_user)
        }
        
        # Get children recursively up to 4 levels
        children = get_children_recursive(target_user_id)
        if children:
            tree_data.update(children)
        
        # DC PROTOCOL: Add left/right total and active counts for Picture View
        from app.services.sql_utils import get_leg_counts
        leg_counts = get_leg_counts(db, target_user_id)
        tree_data['left_count'] = leg_counts.get('left_total', 0)
        tree_data['right_count'] = leg_counts.get('right_total', 0)
        tree_data['left_active_count'] = leg_counts.get('left_active', 0)
        tree_data['right_active_count'] = leg_counts.get('right_active', 0)
        
        return success_response(
            message="Matching referral tree retrieved successfully",
            data=tree_data
        )
    except Exception as e:
        import traceback
        logger.error(f"Error in get_binary_tree: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

@router.get("/team/level-members")
async def get_level_members(
    level: int = None,
    referrer_id: str = None,
    start_date: str = None,
    end_date: str = None,
    package: str = None,
    status_filter: str = None,
    coupon_status: str = None,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Get ALL team members with LEVEL and POSITION columns from binary tree"""
    try:
        from app.models.placement import Placement
        
        # Get ALL binary tree members with level and position using BFS traversal
        def get_all_with_levels(root_id: str) -> List[Dict]:
            from collections import deque
            
            members_with_levels = []
            queue = deque([(root_id, 1, None)])  # (user_id, level, position)
            
            while queue:
                current_id, current_level, position = queue.popleft()
                
                # Get user data
                user = db.query(User).filter(User.id == current_id).first()
                if not user:
                    continue
                
                # Add member with level and position (skip root user at level 1)
                if current_level > 1:
                    members_with_levels.append({
                        "user": user,
                        "level": current_level,
                        "position": position
                    })
                
                # Get children placements
                placements = db.query(Placement).filter(
                    Placement.parent_id == current_id,
                    Placement.status == 'active'
                ).all()
                
                for placement in placements:
                    queue.append((placement.child_id, current_level + 1, placement.side))
            
            return members_with_levels
        
        # Get all members with levels
        user_id = str(current_user.id) if current_user.id else None
        all_members = get_all_with_levels(user_id)
        
        # Apply filters
        filtered_members = []
        for member_data in all_members:
            user = member_data["user"]
            member_level = member_data["level"]
            member_position = member_data["position"]
            
            # Level filter
            if level and member_level != level:
                continue
            
            # Date filter
            if start_date and user.registration_date and user.registration_date < datetime.fromisoformat(start_date):
                continue
            if end_date and user.registration_date and user.registration_date > datetime.fromisoformat(end_date):
                continue
            
            # Package filter
            if package and package != "All Packages" and user.get_package_type() != package:
                continue
            
            # Status filter
            if status_filter and status_filter.lower() == 'active' and not user.activation_date:
                continue
            if status_filter and status_filter.lower() == 'inactive' and user.activation_date:
                continue
            
            # Coupon status filter
            if coupon_status and coupon_status != "All" and user.coupon_status != coupon_status:
                continue
            
            # Referrer filter
            if referrer_id and user.referrer_id != referrer_id:
                continue
            
            filtered_members.append({
                "mnr_id": str(user.id),
                "name": user.name,
                "package": user.get_package_type() if user else "N/A",
                "level": member_level,
                "position": member_position.capitalize() if member_position else "Unknown",
                "registration_date": user.registration_date.isoformat() if user.registration_date else None,
                "activation_date": user.activation_date.isoformat() if user.activation_date else None,
                "status": "Active" if user.activation_date else "Inactive",
                "coupon_status": user.coupon_status or "N/A",
                "referrer_id": user.referrer_id
            })
        
        # Group by level for summary
        from collections import defaultdict
        by_level = defaultdict(int)
        for m in filtered_members:
            by_level[m["level"]] += 1
        
        return success_response(
            message=f"Team members with levels retrieved successfully",
            data={
                "members": filtered_members,
                "total": len(filtered_members),
                "by_level": dict(by_level)
            }
        )
    except Exception as e:
        import traceback
        logger.error(f"Error in get_level_members: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )


# ===== SUPPORT TICKETS =====

class TicketCreateRequest(BaseModel):
    subject: str
    description: str
    category: str = 'General'

@router.post("/tickets")
async def create_support_ticket(
    ticket_data: TicketCreateRequest,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Create a new support ticket"""
    try:
        from app.services.ticket_service import TicketService
        
        ticket_service = TicketService(db)
        result = ticket_service.create_ticket(
            user_id=str(current_user.id),
            subject=ticket_data.subject,
            description=ticket_data.description,
            category=ticket_data.category
        )
        
        return success_response(
            message=result.get('message', 'Ticket created'),
            data=result
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

@router.get("/tickets")
async def get_user_tickets(
    status_filter: Optional[str] = None,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Get user's support tickets"""
    try:
        from app.services.ticket_service import TicketService
        
        ticket_service = TicketService(db)
        result = ticket_service.get_user_tickets(
            user_id=str(current_user.id),
            status=status_filter
        )
        
        return success_response(
            message="Tickets retrieved successfully",
            data=result
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

# ===== AWARDS =====

@router.get("/awards")
async def get_user_awards(
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """
    Get user's awards - unified endpoint for web and mobile
    DC Protocol: DC_UNIFIED_AWARDS_001 (Jan 2026)
    Returns comprehensive award data matching both platforms
    """
    try:
        from app.services.award_service import AwardService
        
        award_service = AwardService(db)
        # DC Protocol Fix: Use correct method get_user_award_summary instead of non-existent get_user_awards
        summary = award_service.get_user_award_summary(str(current_user.id))
        
        # Transform data for mobile compatibility while preserving web structure
        direct_progress = summary.get("direct_award_progress", {})
        matching_progress = summary.get("matching_award_progress", {})
        
        # Build mobile-compatible awards list from tier progress
        awards_list = []
        
        # Process direct awards
        for tier in direct_progress.get("tier_progress", []):
            awards_list.append({
                "id": tier.get("tier_id", 0),
                "award_type": "Direct",
                "award_name": tier.get("tier_info", {}).get("rank_name", ""),
                "amount": tier.get("tier_info", {}).get("actual_price", 0),
                "status": "Achieved" if tier.get("achieved") else "Pending",
                "awarded_on": tier.get("achievement_date"),
                "stage": tier.get("current_stage", "Allocated"),
                "requirement": tier.get("tier_info", {}).get("cumulative_required", 0),
                "current_progress": tier.get("effective_points", 0),
                "remaining": tier.get("remaining_points", 0),
                "achievement_status": "Achieved" if tier.get("achieved") else "Pending",
                "processed_status": tier.get("processed_status", "Not Processed"),
                "dispatch_date": tier.get("dispatch_date"),
                "received_date": tier.get("received_date"),
                "bonanza_claimed": tier.get("bonanza_deductions", 0)
            })
        
        # Process matching awards
        for tier in matching_progress.get("tier_progress", []):
            awards_list.append({
                "id": tier.get("tier_id", 0),
                "award_type": "Matching",
                "award_name": tier.get("tier_info", {}).get("rank_name", ""),
                "amount": tier.get("tier_info", {}).get("actual_price", 0),
                "status": "Achieved" if tier.get("achieved") else "Pending",
                "awarded_on": tier.get("achievement_date"),
                "stage": tier.get("current_stage", "Allocated"),
                "requirement": tier.get("tier_info", {}).get("cumulative_required", 0),
                "current_progress": tier.get("effective_count", 0),
                "remaining": tier.get("remaining_count", 0),
                "achievement_status": "Achieved" if tier.get("achieved") else "Pending",
                "processed_status": tier.get("processed_status", "Not Processed"),
                "dispatch_date": tier.get("dispatch_date"),
                "received_date": tier.get("received_date"),
                "bonanza_claimed": tier.get("bonanza_deductions", 0)
            })
        
        return success_response(
            message="Awards retrieved successfully",
            data={
                # Mobile-compatible fields
                "awards": awards_list,
                "direct_awards": [a for a in awards_list if a["award_type"] == "Direct"],
                "matching_awards": [a for a in awards_list if a["award_type"] == "Matching"],
                # Summary counts
                "achieved_count": sum(1 for a in awards_list if a["status"] == "Achieved"),
                "pending_count": sum(1 for a in awards_list if a["status"] == "Pending"),
                "total_count": len(awards_list),
                # Web-compatible full data
                "direct_award_progress": direct_progress,
                "matching_award_progress": matching_progress,
                "achievement_summary": summary.get("achievement_summary", {}),
                "active_bonanzas": summary.get("active_bonanzas", [])
            }
        )
    except Exception as e:
        logger.error(f"[Awards] Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

@router.get("/awards/eligibility")
async def check_award_eligibility(
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Check user's eligibility for awards"""
    try:
        from app.services.award_service import AwardService
        
        award_service = AwardService(db)
        eligibility = award_service.check_eligibility(str(current_user.id))
        
        return success_response(
            message="Award eligibility retrieved successfully",
            data=eligibility
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

# ===== KYC =====

@router.get("/kyc/status")
async def get_kyc_status(
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Get KYC status"""
    kyc_data = {
        "kyc_status": str(getattr(current_user, 'kyc_status', 'Pending')),
        "pan_verified": bool(getattr(current_user, 'pan_verified', False)),
        "aadhar_verified": bool(getattr(current_user, 'aadhar_verified', False)),
        "bank_verified": bool(getattr(current_user, 'bank_verified', False)),
        "kyc_approved_date": getattr(current_user, 'kyc_approved_date', None)
    }
    
    return success_response(
        message="KYC status retrieved successfully",
        data=kyc_data
    )

# ===== FIELD ALLOWANCES =====

@router.get("/field-allowances")
async def get_field_allowances(
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Get user's field allowances"""
    try:
        field_allowances = db.query(Transaction).filter(
            Transaction.referrer_id == str(current_user.id),
            Transaction.transaction_type == 'Field Allowance'
        ).order_by(Transaction.timestamp.desc()).limit(50).all()
        
        allowance_list = [
            {
                "id": str(getattr(fa, 'id', '')),
                "amount": float(getattr(fa, 'amount', 0) or 0),
                "timestamp": getattr(fa, 'timestamp', datetime.now()).isoformat(),
                "description": str(getattr(fa, 'description', ''))
            }
            for fa in field_allowances
        ]
        
        total = sum(a['amount'] for a in allowance_list)
        
        return success_response(
            message="Field allowances retrieved successfully",
            data={"allowances": allowance_list, "total": total}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

@router.get("/field-allowances-status")
async def get_field_allowances_status(
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Get comprehensive field allowance status with requirements, progress, and target dates"""
    try:
        from app.services.field_allowance_service import FieldAllowanceService
        
        allowance_service = FieldAllowanceService()
        result = allowance_service.get_user_allowance_status(current_user.id, db)
        
        if not result.get("success"):
            return error_response(message=result.get("message", "Failed to fetch allowance status"))
        
        return success_response(
            message="Field allowance status retrieved successfully",
            data=result["data"]
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

# ===== LEGACY AWARD ROUTE WRAPPERS =====
# These routes redirect to the correct award_management endpoints  
# Some pages call /awards/* but actual routes are at /award-management/user/{user_id}/*

from app.api.v1.endpoints.award_management import router as award_router

@router.get("/awards/direct/progress")
async def get_direct_awards_progress_legacy(
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Legacy wrapper for direct awards progress"""
    from app.services.award_service import AwardService
    award_service = AwardService(db)
    result = award_service.get_user_direct_award_progress(str(current_user.id))
    return success_response(message="Direct awards retrieved", data=result)

@router.get("/awards/matching/progress")
async def get_matching_awards_progress_legacy(
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Legacy wrapper for matching awards progress"""
    from app.services.award_service import AwardService
    award_service = AwardService(db)
    result = award_service.get_user_matching_award_progress(str(current_user.id))
    return success_response(message="Matching awards retrieved", data=result)

@router.get("/awards/bonanza/active")
async def get_active_bonanza_unified(
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db),
    status_filter: str = None
):
    """
    Get active bonanza campaigns with user-specific progress
    DC Protocol: DC_UNIFIED_BONANZA_001 (Jan 2026)
    Returns bonanza data with user progress for web-mobile parity
    """
    from app.services.award_service import AwardService
    from app.models.bonanza import DynamicBonanza, DynamicBonanzaReward
    from app.models.base import get_indian_time
    from sqlalchemy import and_
    
    award_service = AwardService(db)
    user_id = str(current_user.id)
    
    # Get active bonanza campaigns
    now = get_indian_time()
    try:
        bonanzas = db.query(DynamicBonanza).filter(
            and_(
                DynamicBonanza.status == 'active',
                DynamicBonanza.start_date <= now,
                DynamicBonanza.end_date >= now
            )
        ).all()
    except Exception:
        bonanzas = []
    
    # Get user's direct/matching progress for bonanza eligibility
    try:
        direct_progress = award_service.get_user_direct_award_progress(user_id)
        matching_progress = award_service.get_user_matching_award_progress(user_id)
        current_direct_points = direct_progress.get("total_package_points", 0)
        current_matching_count = matching_progress.get("effective_matching_count", 0)
    except Exception:
        current_direct_points = 0
        current_matching_count = 0
    
    # Build bonanza list with user progress
    bonanza_list = []
    for bonanza in bonanzas:
        # Get rewards for this bonanza
        try:
            rewards = db.query(DynamicBonanzaReward).filter(
                DynamicBonanzaReward.bonanza_id == bonanza.id
            ).order_by(DynamicBonanzaReward.tier_level).all()
        except Exception:
            rewards = []
        
        # Calculate user progress for this bonanza
        target_direct = getattr(bonanza, 'direct_target', 0) or 0
        target_matching = getattr(bonanza, 'matching_target', 0) or 0
        
        if target_direct > 0:
            progress_pct = min(100, int((current_direct_points / target_direct) * 100))
            target_value = target_direct
            current_value = current_direct_points
        elif target_matching > 0:
            progress_pct = min(100, int((current_matching_count / target_matching) * 100))
            target_value = target_matching
            current_value = current_matching_count
        else:
            progress_pct = 0
            target_value = 0
            current_value = 0
        
        # Determine user status for this bonanza
        if progress_pct >= 100:
            user_status = "achieved"
        elif now > bonanza.end_date:
            user_status = "expired"
        else:
            user_status = "active"
        
        # Apply status filter if provided
        if status_filter and status_filter != 'all':
            if user_status != status_filter.lower():
                continue
        
        bonanza_list.append({
            "id": bonanza.id,
            "name": bonanza.bonanza_name,
            "description": bonanza.description or "",
            "start_date": bonanza.start_date.isoformat() if bonanza.start_date else None,
            "end_date": bonanza.end_date.isoformat() if bonanza.end_date else None,
            "status": user_status,
            "target_value": target_value,
            "current_value": current_value,
            "progress_percentage": progress_pct,
            "reward_value": float(rewards[0].reward_value) if rewards else 0,
            "reward_type": rewards[0].reward_type if rewards else "cash",
            "achieved_date": None,
            "expiry_date": bonanza.end_date.isoformat() if bonanza.end_date else None,
            "rewards": [
                {
                    "id": r.id,
                    "name": r.reward_name,
                    "description": r.reward_description,
                    "value": float(r.reward_value) if r.reward_value else 0,
                    "type": r.reward_type,
                    "tier_level": r.tier_level,
                    "direct_target": r.direct_referral_target,
                    "matching_target": r.matching_referral_target
                }
                for r in rewards
            ]
        })
    
    return success_response(
        message="Active bonanzas retrieved",
        data={
            # Mobile-compatible fields
            "awards": bonanza_list,
            "bonanza": bonanza_list,
            "current_rank": "Starter",
            "next_rank": "Bronze" if bonanza_list else None,
            "progress_percentage": bonanza_list[0]["progress_percentage"] if bonanza_list else 0,
            "required_points": bonanza_list[0]["target_value"] if bonanza_list else 100,
            "current_points": bonanza_list[0]["current_value"] if bonanza_list else 0,
            # Summary
            "total_campaigns": len(bonanza_list),
            "achieved_count": sum(1 for b in bonanza_list if b["status"] == "achieved"),
            "active_count": sum(1 for b in bonanza_list if b["status"] == "active")
        }
    )

# ===== LEGACY INCOME ROUTE WRAPPERS =====
# These routes redirect to the correct financial_operations endpoints
# Frontend calls /users/income/* but actual routes are at /income/{user_id}/*

@router.get("/income/direct")
async def get_user_direct_income_legacy(
    current_user: User = Depends(require_activated_user),
    db: Session = Depends(get_db)
):
    """Legacy wrapper: Redirect to /income/{user_id}/direct-referral - DC Protocol: Requires activated membership"""
    from app.services.reference_service import ReferenceService
    reference_service = ReferenceService(db)
    result = reference_service.calculate_direct_referral_income(str(current_user.id))
    return success_response(message="Direct referral income retrieved", data=result)

@router.get("/income/matching")
async def get_user_matching_income_legacy(
    current_user: User = Depends(require_activated_user),
    db: Session = Depends(get_db)
):
    """Legacy wrapper: Redirect to /income/{user_id}/matching-referral - DC Protocol: Requires activated membership"""
    from app.services.reference_service import ReferenceService
    reference_service = ReferenceService(db)
    result = reference_service.calculate_matching_referral_income(str(current_user.id))
    return success_response(message="Matching referral income retrieved", data=result)

@router.get("/income/ved")
async def get_user_ved_income_legacy(
    current_user: User = Depends(require_activated_user),
    db: Session = Depends(get_db)
):
    """Legacy wrapper: Redirect to /income/{user_id}/ved-income - DC Protocol: Requires activated membership"""
    from app.services.reference_service import ReferenceService
    reference_service = ReferenceService(db)
    result = reference_service.calculate_ved_income(str(current_user.id))
    return success_response(message="Ved income retrieved", data=result)

@router.get("/income/guru-dakshina")
async def get_user_guru_dakshina_legacy(
    current_user: User = Depends(require_activated_user),
    db: Session = Depends(get_db)
):
    """Legacy wrapper: Redirect to /income/{user_id}/guru-dakshina - DC Protocol: Requires activated membership"""
    from app.services.reference_service import ReferenceService
    reference_service = ReferenceService(db)
    result = reference_service.calculate_guru_dakshina(str(current_user.id))
    return success_response(message="Guru Dakshina retrieved", data=result)

# ===== PIN MANAGEMENT =====

class PinPurchaseRequest(BaseModel):
    package_type: str  # '500', '1000', '7500', '15000'
    quantity: int = 1
    payment_method: str = 'wallet'

@router.get("/pins")
async def get_user_pins(
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Get user's PIN inventory with activated_for field (DC Protocol Dec 24, 2025)"""
    try:
        from app.models.coupon import Coupon, CouponActivationTracker
        from app.models.transaction import PendingIncome
        from app.utils.pin_masking import mask_pin
        from sqlalchemy import func
        from sqlalchemy.orm import aliased
        
        # Create alias for User table to join for activated_for
        ActivatedUser = aliased(User)
        UsedByUser = aliased(User)
        
        # Query coupons with both used_by and activated_for information
        pins_query = db.query(
            Coupon,
            PendingIncome.user_id.label('used_by_id'),
            UsedByUser.name.label('used_by_name'),
            CouponActivationTracker.user_id.label('activated_for_id'),
            ActivatedUser.name.label('activated_for_name')
        ).outerjoin(
            PendingIncome,
            Coupon.id == PendingIncome.coupon_id
        ).outerjoin(
            UsedByUser,
            PendingIncome.user_id == UsedByUser.id
        ).outerjoin(
            CouponActivationTracker,
            Coupon.id == CouponActivationTracker.coupon_id
        ).outerjoin(
            ActivatedUser,
            CouponActivationTracker.user_id == ActivatedUser.id
        ).filter(
            Coupon.owner_id == str(current_user.id)
        ).all()
        
        pin_list = []
        for p, used_by_id, used_by_name, activated_for_id, activated_for_name in pins_query:
            # Create used_by display text
            used_by = "-"
            if used_by_id and used_by_name:
                used_by = f"{used_by_id} - {used_by_name}"
            elif used_by_id:
                used_by = str(used_by_id)
            
            # Create activated_for display text (DC Protocol Dec 24, 2025)
            activated_for = "-"
            if activated_for_id and activated_for_name:
                activated_for = f"{activated_for_id} - {activated_for_name}"
            elif activated_for_id:
                activated_for = str(activated_for_id)
            
            # Mask PIN for security (show only first 4 and last 4 digits)
            masked_pin = mask_pin(str(p.id))
            
            pin_list.append({
                "id": str(p.id),
                "coupon_code": masked_pin,  # Masked PIN code for security
                "coupon_type": str(p.coupon_type) if p.coupon_type else 'Unknown',
                "status": str(p.status) if p.status else 'Unknown',
                "amount": float(p.coupon_type) if p.coupon_type and p.coupon_type.isdigit() else 0,
                "created_at": p.assignment_status_changed_at.isoformat() if p.assignment_status_changed_at else datetime.now().isoformat(),
                "activated_at": p.activated_at.isoformat() if p.activated_at else None,
                "used_by": used_by,
                "activated_for": activated_for  # DC Protocol Dec 24, 2025: New field
            })
        
        return success_response(
            message="PINs retrieved successfully",
            data={"pins": pin_list, "total_pins": len(pin_list)}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

@router.post("/pins/purchase-request")
async def request_pin_purchase(
    package_type: str = Form(...),
    quantity: int = Form(...),
    transaction_id: str = Form(...),
    transaction_date: str = Form(...),
    amount_paid: float = Form(...),
    payment_mode: str = Form(...),
    payment_screenshot: UploadFile = File(...),
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Submit a PIN purchase request with payment proof"""
    try:
        from app.models.coupon import PINPurchaseRequest as PinPurchaseModel
        from app.models.base import get_indian_time
        from decimal import Decimal, InvalidOperation
        from datetime import datetime
        import os
        import shutil
        from pathlib import Path
        import logging
        
        logger = logging.getLogger(__name__)
        
        if quantity <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quantity must be greater than 0"
            )
        
        # Validate and parse package cost - map package names to prices
        from app.constants import PACKAGE_SYSTEM
        
        # Map package name (Platinum, Diamond) to price
        package_name_upper = package_type.upper()
        if package_name_upper in PACKAGE_SYSTEM:
            package_cost = Decimal(str(PACKAGE_SYSTEM[package_name_upper]['price']))
        else:
            # Try to parse as direct price (for backward compatibility)
            try:
                package_cost = Decimal(str(package_type))
                if package_cost <= 0:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid package price"
                    )
            except (InvalidOperation, ValueError) as e:
                logger.error(f"Invalid package_type: {package_type}, error: {e}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid package type: {package_type}. Must be Platinum or Diamond"
                )
        
        # RESTRICTION: Block Star (1000) and Loyal (500) purchases for regular users
        # Only Admin, Super Admin, and RVZ ID can purchase/assign these packages
        package_cost_int = int(package_cost)
        if package_cost_int in [1000, 500]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Star and Loyal packages cannot be purchased by users. Please contact admin for assistance."
            )
        
        # DC Protocol: Validate file size BEFORE creating DB records (prevent orphan records)
        file_content = await payment_screenshot.read()
        file_size = len(file_content)
        payment_screenshot.file.seek(0)  # Reset for UniversalUploadService (synchronous seek for SpooledTemporaryFile)
        
        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is empty"
            )
        
        # Universal Upload System: 5MB limit for images
        MAX_IMAGE_SIZE = 5000000  # 5MB (will be auto-compressed)
        if file_size > MAX_IMAGE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File size ({round(file_size/1024, 2)}KB) exceeds maximum allowed size (5MB). File will be automatically compressed after upload."
            )
        
        # Calculate amounts
        total_amount = package_cost * quantity
        
        # Parse transaction date
        try:
            trans_date = datetime.strptime(transaction_date, '%Y-%m-%d')
        except ValueError as e:
            logger.error(f"Invalid date format: {transaction_date}, error: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid date format. Expected YYYY-MM-DD, got: {transaction_date}"
            )
        
        # Check for duplicate transaction_id (case-insensitive, global uniqueness)
        existing_request = db.query(PinPurchaseModel).filter(
            func.lower(PinPurchaseModel.transaction_id) == func.lower(transaction_id)
        ).first()
        
        if existing_request is not None:
            logger.warning(f"Duplicate transaction_id attempted: {transaction_id} by user {current_user.id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Transaction ID '{transaction_id}' has already been used. Please use a unique transaction ID."
            )
        
        # Universal Upload System: 5MB for images, auto-compression, dual storage
        from app.services.universal_upload_service import UniversalUploadService
        
        # Create payment details text
        payment_details_text = f"Package: {package_type}, Payment Mode: {payment_mode}, Transaction ID: {transaction_id}, Amount Paid: ₹{amount_paid}, Date: {transaction_date}"
        
        # Database expects numeric package_type ('15000', '7500', etc.) not package names
        package_type_numeric = str(int(package_cost))  # Convert to numeric string for DB constraint
        
        # DC Protocol: Atomic transaction - ALL changes commit together
        new_request = None
        upload_result = None
        try:
            # Create placeholder record to get ID (within transaction - NOT committed yet)
            new_request = PinPurchaseModel(
                user_id=str(current_user.id),
                package_type=package_type_numeric,  # DB expects numeric: '15000', '7500', etc.
                package_value=int(package_cost),  # DB column: package_value (integer)
                quantity=quantity,  # DB column: quantity
                total_amount=total_amount,
                payment_method=payment_mode,
                transaction_id=transaction_id,
                payment_amount=Decimal(str(amount_paid)),  # DB column: payment_amount
                payment_details=payment_details_text,  # DB column: payment_details (NOT NULL)
                payment_screenshot_path="pending",  # Temporary
                request_date=get_indian_time(),
                status='Pending'
            )
            db.add(new_request)
            db.flush()  # Get request ID for upload (still within transaction)
            
            # Upload file using request ID (if this fails, transaction rolls back)
            # DC Protocol: defer_scheduler=True ensures job only scheduled AFTER db.commit()
            upload_result = await UniversalUploadService.handle_upload(
                file=payment_screenshot,
                table_name='pin_purchase_requests',
                record_id=new_request.id,
                uploaded_by_id=current_user.id,
                uploaded_by_type='user',
                storage_dir='payment_proofs',
                db=db,
                defer_scheduler=True  # DC: Transaction safety - schedule job AFTER commit
            )
            
            # DC Protocol: Update request with ALL metadata from upload result
            new_request.payment_screenshot_path = upload_result['file_path']
            
            # DC PROTOCOL: Generate semantic download filename (NEW - Nov 29, 2025)
            try:
                import pytz
                
                ist_tz = pytz.timezone('Asia/Kolkata')
                uploaded_at_ist = datetime.now(ist_tz)
                
                download_name = UniversalUploadService.generate_download_filename(
                    segment_key='payment_screenshot',
                    entity_type='payment',
                    entity_id=new_request.id,
                    attachment_id=new_request.id,
                    uploader_code=current_user.id,  # User.id IS the MNR ID
                    original_filename=payment_screenshot.filename,
                    uploaded_at=uploaded_at_ist
                )
                
                new_request.download_filename = download_name
                new_request.uses_new_naming = True
            except HTTPException:
                raise
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Failed to generate download filename for payment {new_request.id}: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Failed to generate semantic filename: {str(e)}")
            
            # DC: Log audit in SAME transaction
            AuditLogger.log_action(
                db=db,
                user=current_user,
                action='PIN_PURCHASE_REQUEST',
                resource_type='PIN',
                resource_id=str(new_request.id),
                details={
                    "package_type": package_type,
                    "quantity": quantity,
                    "total_amount": float(total_amount),
                    "payment_method": payment_mode,
                    "transaction_id": transaction_id,
                    "file_uploaded": upload_result['file_name']
                }
            )
            
            # DC Protocol: Single commit for request + audit log (atomic operation)
            # PostCommitScheduler will automatically enqueue deferred jobs AFTER this commit
            db.commit()
            db.refresh(new_request)
            
        except HTTPException as e:
            # DC PROTOCOL: Preserve validation errors
            db.rollback()
            raise e
        except Exception as upload_error:
            # DC Protocol: Transaction rollback removes BOTH request and audit log
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to upload payment screenshot: {str(upload_error)}"
            )
        
        return success_response(
            message="PIN purchase request submitted successfully. Awaiting Admin & Finance approval.",
            data={
                "request_id": str(getattr(new_request, 'id', '')),
                "package_type": package_type,
                "quantity": quantity,
                "total_amount": float(total_amount),
                "transaction_id": transaction_id,
                "status": "Pending",
                "created_at": getattr(new_request, 'request_date', datetime.now()).isoformat()
            }
        )
    except HTTPException:
        raise
    except IntegrityError as e:
        db.rollback()
        # Handle race condition where duplicate transaction_id was inserted between check and commit
        if 'transaction_id' in str(e).lower() or 'unique' in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Transaction ID '{transaction_id}' has already been used. Please use a unique transaction ID."
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database integrity error occurred"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

@router.get("/pins/purchase-requests")
async def get_my_purchase_requests(
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Get user's own PIN purchase requests"""
    try:
        from app.models.coupon import PINPurchaseRequest
        
        requests = db.query(PINPurchaseRequest).filter(
            PINPurchaseRequest.user_id == current_user.id
        ).order_by(PINPurchaseRequest.request_date.desc()).all()
        
        requests_data = []
        for req in requests:
            # Use correct attribute names from PINPurchaseRequest model
            # Provide both old and new field names for backward compatibility
            requests_data.append({
                "id": str(req.id),
                "package_type": req.package_type,
                "quantity": req.quantity,
                "total_amount": float(req.total_amount),
                "payment_method": req.payment_method,
                "transaction_id": req.transaction_id,
                "status": req.status,
                "requested_at": req.request_date.isoformat(),
                # Legacy fields (for frontend compatibility)
                "approved_at": req.superadmin_approved_date.isoformat() if req.superadmin_approved_date else (req.finance_validated_date.isoformat() if req.finance_validated_date else None),
                "admin_notes": req.superadmin_notes or req.finance_admin_notes or "",
                # New detailed fields
                "superadmin_approved_at": req.superadmin_approved_date.isoformat() if req.superadmin_approved_date else None,
                "finance_validated_at": req.finance_validated_date.isoformat() if req.finance_validated_date else None,
                "superadmin_notes": req.superadmin_notes or "",
                "finance_notes": req.finance_admin_notes or ""
            })
        
        return success_response(
            message="Purchase requests retrieved successfully",
            data={"requests": requests_data}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

@router.get("/pins/history")
async def get_pin_history(
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Get PIN purchase and activation history"""
    try:
        from app.models.coupon import Coupon
        from app.models.coupon import PINPurchaseRequest
        from app.utils.pin_masking import mask_pin
        from sqlalchemy import func
        
        pins = db.query(Coupon).filter(
            Coupon.owner_id == str(current_user.id)
        ).limit(100).all()
        
        # Get the user's most recent completed PIN purchase request for fallback date
        latest_purchase = db.query(PINPurchaseRequest).filter(
            PINPurchaseRequest.user_id == str(current_user.id),
            PINPurchaseRequest.status == 'Approved'
        ).order_by(PINPurchaseRequest.completed_date.desc()).first()
        
        # Fallback date from purchase request
        fallback_date = latest_purchase.completed_date if latest_purchase and latest_purchase.completed_date else None
        
        history = [
            {
                "pin_code": mask_pin(str(p.id)),  # Masked for security
                "type": str(p.coupon_type) if p.coupon_type else 'Unknown',
                "status": str(p.status) if p.status else 'Unknown',
                "purchased_at": (p.assignment_status_changed_at.isoformat() if p.assignment_status_changed_at 
                                else (p.assignment_status_changed_date.isoformat() if p.assignment_status_changed_date 
                                      else (fallback_date.isoformat() if fallback_date else None))),
                "activated_at": p.activated_at.isoformat() if p.activated_at else None,
                "used_by": str(p.used_by) if hasattr(p, 'used_by') and p.used_by else 'Not Used'
            }
            for p in pins
        ]
        
        return success_response(
            message="PIN history retrieved successfully",
            data={"history": history}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

# ===== COUPON MANAGEMENT =====

@router.get("/coupons")
async def get_user_coupons(
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Get user's coupon status and history"""
    try:
        coupon_data = {
            "coupon_status": str(getattr(current_user, 'coupon_status', 'Eligible')),
            "current_package": str(getattr(current_user, 'coupon_type', '')),
            "activation_date": getattr(current_user, 'coupon_activation_date', None),
            "is_red_coupon": bool(getattr(current_user, 'is_red_coupon', False)),
            "red_coupon_locked": bool(getattr(current_user, 'red_coupon_locked', False))
        }
        
        return success_response(
            message="Coupon status retrieved successfully",
            data=coupon_data
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

@router.get("/coupons/summary")
async def get_coupon_summary(
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """Get comprehensive coupon summary"""
    try:
        from app.models.coupon import Coupon
        
        owned_coupons = db.query(Coupon).filter(
            Coupon.owner_id == str(current_user.id)
        ).all()
        
        summary = {
            "total_coupons": len(owned_coupons),
            "active_coupons": len([c for c in owned_coupons if getattr(c, 'status', '') == 'Active']),
            "used_coupons": len([c for c in owned_coupons if getattr(c, 'status', '') == 'Used']),
            "available_coupons": len([c for c in owned_coupons if getattr(c, 'status', '') == 'Available']),
            "user_status": str(getattr(current_user, 'coupon_status', 'Eligible'))
        }
        
        return success_response(
            message="Coupon summary retrieved successfully",
            data=summary
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server error: {str(e)}"
        )

# ===== PIN ACTIVATION ENDPOINT =====

class ActivatePINRequest(BaseModel):
    pin_code: str
    user_id: Optional[str] = None  # If None, activate for self

@router.post("/pins/activate")
async def activate_pin(
    request: ActivatePINRequest,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """
    Activate a PIN for a user (self or another inactive user)
    """
    try:
        from app.models.coupon import Coupon
        from app.models.base import get_indian_time
        from app.constants import COUPON_PACKAGE_MAP, PACKAGE_SYSTEM
        # DC Protocol (Feb 2026): Scheduler imports removed - no real-time income at activation
        
        # Determine target user (self or specified user)
        target_user_id = request.user_id if request.user_id else str(current_user.id)
        target_member = db.query(User).filter(User.id == target_user_id).first()
        
        if not target_member:
            return {
                "success": False,
                "message": "Target user not found"
            }
        
        # Check if target user is inactive
        if target_member.coupon_status != 'Inactive':
            return {
                "success": False,
                "message": f"User {target_user_id} is already {target_member.coupon_status}"
            }
        
        # DC Protocol (Dec 22, 2025): Validate mobile uniqueness before activation
        from app.services.user_service import UserService
        user_service = UserService(db)
        mobile_check = user_service.ensure_unique_active_mobile(target_member.phone_number, target_user_id)
        if not mobile_check.get("success"):
            return {
                "success": False,
                "message": mobile_check.get("error", "Mobile number validation failed"),
                "requires_mobile_update": True
            }
        
        # Find the PIN/Coupon
        coupon = db.query(Coupon).filter(
            Coupon.id == request.pin_code,
            Coupon.owner_id == str(current_user.id),
            Coupon.status == 'Active'
        ).first()
        
        if not coupon:
            return {
                "success": False,
                "message": "PIN not found or not available for activation"
            }
        
        # Get package configuration
        package_type_str = str(coupon.package_type)
        package_name = COUPON_PACKAGE_MAP.get(package_type_str)
        
        if not package_name or package_name not in PACKAGE_SYSTEM:
            return {
                "success": False,
                "message": f"Invalid package type: {package_type_str}"
            }
        
        config = PACKAGE_SYSTEM[package_name]
        
        # Update target member package_points
        target_member.package_points = config['points']
        
        # CRITICAL: Set activation_date on user
        activation_time = get_indian_time()
        target_member.activation_date = activation_time
        target_member.coupon_status = 'Activated'
        
        # Mark coupon as used
        coupon.status = 'Used'
        coupon.activation_date = activation_time
        
        # DC Protocol (Feb 2026): ALL income (Direct Referral, Guru Dakshina, Ved Income)
        # is generated by midnight scheduler ONLY. No real-time income creation at activation.
        # The midnight scheduler will pick up this activation via activation_date check.
        
        # CRITICAL: Refresh leg metrics in REAL-TIME for activated user and entire upline chain
        # This ensures matching referral calculations are immediately accurate (don't wait for 11:30 PM job)
        try:
            from app.services.leg_metrics_cache_service import LegMetricsCacheService
            from app.models.placement import Placement
            
            leg_service = LegMetricsCacheService(db)
            
            # Step 1: Refresh the newly activated user's metrics
            leg_service.refresh_user_metrics(target_member.id, source='activation')
            
            # Step 2: Refresh ALL upline ancestors' metrics (they gain a new downline member)
            # Walk up the placement tree to root
            upline_ids = []
            current_id = target_member.id
            visited = set()  # Prevent infinite loops
            
            while current_id and current_id not in visited:
                visited.add(current_id)
                
                # Get parent in placement tree
                placement = db.query(Placement).filter(Placement.child_id == current_id).first()
                if placement and placement.parent_id:
                    upline_ids.append(placement.parent_id)
                    current_id = placement.parent_id
                else:
                    break
            
            # Refresh all upline users' metrics
            for upline_id in upline_ids:
                leg_service.refresh_user_metrics(upline_id, source='activation')
                
            logger.info(f"✅ Real-time leg metrics refreshed for {target_member.id} and {len(upline_ids)} upline users")
            
        except Exception as e:
            logger.error(f"⚠️ Failed to refresh leg metrics after activation: {e}")
            # Don't fail the activation if metrics refresh fails
        
        db.commit()
        
        return {
            "success": True,
            "message": f"PIN activated successfully for {target_member.name or target_user_id}",
            "data": {
                "user_id": target_user_id,
                "package": package_name,
                "points": config['points']
            }
        }
        
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "message": f"Error activating PIN: {str(e)}"
        }

# ===== USER SEARCH ENDPOINT =====

@router.get("/search-inactive")
async def search_inactive_users(
    query: str = Query(..., min_length=1, description="Search by MNR ID or name"),
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """
    Search for inactive users by MNR ID or name for PIN activation
    Returns users with status 'Inactive' that can receive PIN activation
    """
    try:
        # Search by MNR ID or name (case-insensitive)
        users = db.query(User).filter(
            or_(
                User.id.ilike(f"%{query}%"),
                User.name.ilike(f"%{query}%")
            ),
            User.coupon_status == 'Inactive'  # Only inactive users can receive PIN activation
        ).limit(10).all()
        
        users_data = []
        for user in users:
            users_data.append({
                "id": str(user.id),
                "name": str(user.name) if user.name else "No Name",
                "email": str(user.email) if user.email else "",
                "status": str(user.coupon_status) if user.coupon_status else "Inactive",
                "user_type": str(user.user_type) if user.user_type else "Member"
            })
        
        return {
            "success": True,
            "users": users_data,
            "count": len(users_data)
        }
    except Exception as e:
        return {
            "success": False,
            "users": [],
            "error": str(e)
        }

# ===== ZYNOVA MOBILE ENDPOINTS =====
# DC Protocol (Jan 2026): Mobile parity endpoints for Zynova segments

@router.get("/zynova/real-estate")
async def get_zynova_real_estate_unified(
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """
    Get user's Zynova Real Estate segment data - unified endpoint for web and mobile
    DC Protocol: DC_UNIFIED_ZYNOVA_RE_001 (Jan 2026)
    Returns consistent data structure for both platforms
    """
    try:
        from app.models.myntreal_incentive import ZynovaMember
        
        membership = db.query(ZynovaMember).filter(
            ZynovaMember.user_id == current_user.id,
            ZynovaMember.is_active == True
        ).first()
        
        if not membership:
            # Return default structure for non-members - works for both web and mobile
            return {
                "success": True,
                "data": {
                    "is_member": False,
                    # Mobile-compatible fields
                    "role": "Associate",
                    "next_role": "Executive",
                    "progress_percentage": 0,
                    "current_points": 0,
                    "required_points": 100,
                    "total_earnings": 0,
                    "pending_earnings": 0,
                    "team_count": 0,
                    "properties_referred": 0,
                    # Web-compatible fields
                    "current_role": "promoter",
                    "current_role_display": "Associate",
                    "next_role_display": "Executive",
                    "self_revenue": 0,
                    "team_revenue": 0,
                    "total_revenue": 0,
                    "promotion_target": 100000,
                    "promotion_progress": {"progress": 0, "remaining": 100000},
                    "earnings": {"pending": 0, "approved": 0, "disbursed": 0, "total": 0},
                    "message": "Join VGK4U Real Estate to start earning through property referrals"
                }
            }
        
        # Calculate actual data for members
        current_role = membership.real_estate_role or 'promoter'
        role_map = {'promoter': 'Associate', 'team_leader': 'Executive', 'zonal_manager': 'Manager', 'director': 'Director'}
        next_role_map = {'promoter': 'team_leader', 'team_leader': 'zonal_manager', 'zonal_manager': 'director', 'director': None}
        
        display_role = role_map.get(current_role, 'Associate')
        next_role = next_role_map.get(current_role)
        display_next = role_map.get(next_role, 'Executive') if next_role else None
        
        # Calculate progress
        self_revenue = float(membership.real_estate_revenue_self or 0)
        team_revenue = float(membership.real_estate_revenue_team or 0) if hasattr(membership, 'real_estate_revenue_team') else 0
        total_revenue = float(membership.real_estate_revenue_total or 0)
        target_revenue = 100000  # ₹1 lakh target for promotion
        progress = min(100, int((total_revenue / target_revenue) * 100)) if target_revenue > 0 else 0
        remaining = max(0, target_revenue - total_revenue)
        
        # Get team count
        team_count = db.query(ZynovaMember).filter(
            ZynovaMember.real_estate_upline_id == membership.id,
            ZynovaMember.is_active == True
        ).count()
        
        return {
            "success": True,
            "data": {
                "is_member": True,
                # Mobile-compatible fields
                "role": display_role,
                "next_role": display_next if display_next else "Top Level",
                "progress_percentage": progress,
                "current_points": int(total_revenue / 1000),
                "required_points": 100,
                "total_earnings": total_revenue,
                "pending_earnings": 0,
                "team_count": team_count,
                "properties_referred": 0,
                # Web-compatible fields
                "current_role": current_role,
                "current_role_display": display_role,
                "next_role_display": display_next,
                "self_revenue": self_revenue,
                "team_revenue": team_revenue,
                "total_revenue": total_revenue,
                "promotion_target": target_revenue,
                "promotion_progress": {"progress": progress, "remaining": remaining},
                "earnings": {"pending": 0, "approved": 0, "disbursed": total_revenue, "total": total_revenue}
            }
        }
    except Exception as e:
        logger.error(f"[Zynova RE] Error: {e}")
        return {
            "success": True,
            "data": {
                "is_member": False,
                "role": "Associate",
                "next_role": "Executive",
                "progress_percentage": 0,
                "current_points": 0,
                "required_points": 100,
                "total_earnings": 0,
                "pending_earnings": 0,
                "team_count": 0,
                "properties_referred": 0,
                "current_role": "promoter",
                "current_role_display": "Associate",
                "next_role_display": "Executive",
                "self_revenue": 0,
                "team_revenue": 0,
                "total_revenue": 0,
                "promotion_target": 100000,
                "promotion_progress": {"progress": 0, "remaining": 100000},
                "earnings": {"pending": 0, "approved": 0, "disbursed": 0, "total": 0}
            }
        }


@router.get("/zynova/insurance")
async def get_zynova_insurance_unified(
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """
    Get user's Zynova Insurance segment data - unified endpoint for web and mobile
    DC Protocol: DC_UNIFIED_ZYNOVA_INS_001 (Jan 2026)
    Returns consistent data structure for both platforms
    """
    try:
        from app.models.myntreal_incentive import ZynovaMember
        
        membership = db.query(ZynovaMember).filter(
            ZynovaMember.user_id == current_user.id,
            ZynovaMember.is_active == True
        ).first()
        
        if not membership:
            # Return default structure for non-members - works for both web and mobile
            return {
                "success": True,
                "data": {
                    "is_member": False,
                    # Mobile-compatible fields
                    "role": "Associate",
                    "next_role": "Executive",
                    "progress_percentage": 0,
                    "current_points": 0,
                    "required_points": 100,
                    "total_earnings": 0,
                    "pending_earnings": 0,
                    "team_count": 0,
                    "policies_sold": 0,
                    # Web-compatible fields
                    "current_role": "promoter",
                    "current_role_display": "Associate",
                    "next_role_display": "Executive",
                    "self_revenue": 0,
                    "team_revenue": 0,
                    "total_revenue": 0,
                    "promotion_target": 100000,
                    "promotion_progress": {"progress": 0, "remaining": 100000},
                    "earnings": {"pending": 0, "approved": 0, "disbursed": 0, "total": 0},
                    "message": "Join Zynova Insurance to start earning through insurance referrals"
                }
            }
        
        # Calculate actual data for members
        current_role = membership.insurance_role or 'promoter'
        role_map = {'promoter': 'Associate', 'team_leader': 'Executive', 'zonal_manager': 'Manager', 'director': 'Director'}
        next_role_map = {'promoter': 'team_leader', 'team_leader': 'zonal_manager', 'zonal_manager': 'director', 'director': None}
        
        display_role = role_map.get(current_role, 'Associate')
        next_role = next_role_map.get(current_role)
        display_next = role_map.get(next_role, 'Executive') if next_role else None
        
        # Calculate progress
        self_revenue = float(membership.insurance_revenue_self or 0) if hasattr(membership, 'insurance_revenue_self') else 0
        team_revenue = float(membership.insurance_revenue_team or 0) if hasattr(membership, 'insurance_revenue_team') else 0
        total_revenue = float(membership.insurance_revenue_total or 0)
        target_revenue = 100000  # ₹1 lakh target for promotion
        progress = min(100, int((total_revenue / target_revenue) * 100)) if target_revenue > 0 else 0
        remaining = max(0, target_revenue - total_revenue)
        
        # Get team count
        team_count = db.query(ZynovaMember).filter(
            ZynovaMember.insurance_upline_id == membership.id,
            ZynovaMember.is_active == True
        ).count()
        
        return {
            "success": True,
            "data": {
                "is_member": True,
                # Mobile-compatible fields
                "role": display_role,
                "next_role": display_next if display_next else "Top Level",
                "progress_percentage": progress,
                "current_points": int(total_revenue / 1000),
                "required_points": 100,
                "total_earnings": total_revenue,
                "pending_earnings": 0,
                "team_count": team_count,
                "policies_sold": 0,
                # Web-compatible fields
                "current_role": current_role,
                "current_role_display": display_role,
                "next_role_display": display_next,
                "self_revenue": self_revenue,
                "team_revenue": team_revenue,
                "total_revenue": total_revenue,
                "promotion_target": target_revenue,
                "promotion_progress": {"progress": progress, "remaining": remaining},
                "earnings": {"pending": 0, "approved": 0, "disbursed": total_revenue, "total": total_revenue}
            }
        }
    except Exception as e:
        logger.error(f"[Zynova Insurance] Error: {e}")
        return {
            "success": True,
            "data": {
                "is_member": False,
                "role": "Associate",
                "next_role": "Executive",
                "progress_percentage": 0,
                "current_points": 0,
                "required_points": 100,
                "total_earnings": 0,
                "pending_earnings": 0,
                "team_count": 0,
                "policies_sold": 0,
                "current_role": "promoter",
                "current_role_display": "Associate",
                "next_role_display": "Executive",
                "self_revenue": 0,
                "team_revenue": 0,
                "total_revenue": 0,
                "promotion_target": 100000,
                "promotion_progress": {"progress": 0, "remaining": 100000},
                "earnings": {"pending": 0, "approved": 0, "disbursed": 0, "total": 0}
            }
        }


@router.get("/zynova/training")
async def get_zynova_training_unified(
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """
    Get user's Zynova Training segment data - unified endpoint for web and mobile
    DC Protocol: DC_UNIFIED_ZYNOVA_TRN_001 (Jan 2026)
    Returns training modules and progress
    """
    try:
        # Training modules with detailed info for mobile
        modules = [
            {"id": 1, "title": "Real Estate Basics", "description": "Learn property valuation and market analysis", "status": "Pending", "progress": 0, "completed_on": None},
            {"id": 2, "title": "Insurance Fundamentals", "description": "Understand insurance products and coverage", "status": "Pending", "progress": 0, "completed_on": None},
            {"id": 3, "title": "Sales Techniques", "description": "Master effective sales and closing techniques", "status": "Pending", "progress": 0, "completed_on": None},
            {"id": 4, "title": "Customer Relations", "description": "Build lasting customer relationships", "status": "Pending", "progress": 0, "completed_on": None},
            {"id": 5, "title": "Compliance Training", "description": "Legal requirements and industry compliance", "status": "Pending", "progress": 0, "completed_on": None}
        ]
        
        completed_count = sum(1 for m in modules if m["status"] == "Completed")
        overall_progress = int((completed_count / len(modules)) * 100) if modules else 0
        
        return {
            "success": True,
            "data": {
                # Mobile-compatible fields
                "overall_progress": overall_progress,
                "modules_completed": completed_count,
                "total_modules": len(modules),
                "certificate_eligible": completed_count == len(modules),
                "modules": modules,
                # Additional web-compatible fields
                "progress_percentage": overall_progress,
                "benefits": [
                    "Learn about real estate and insurance",
                    "Improve your sales skills",
                    "Get certified to access premium leads",
                    "Unlock higher commission rates"
                ]
            }
        }
    except Exception as e:
        logger.error(f"[Zynova Training] Error: {e}")
        return {
            "success": True,
            "data": {
                "overall_progress": 0,
                "modules_completed": 0,
                "total_modules": 5,
                "certificate_eligible": False,
                "modules": [],
                "progress_percentage": 0,
                "benefits": []
            }
        }


# ===== MNR Accidental Insurance Status (DC Protocol Feb 2026) =====

@router.get("/my-insurance-status")
async def get_my_insurance_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's accidental insurance status for banner display
    DC Protocol Feb 2026: 5 Lakhs insurance for paid MNR members
    Eligibility:
    - New users (activated >= Feb 3, 2026): Auto-eligible
    - Old users (activated < Feb 3, 2026): Need 2 direct referrals activated after Feb 3, 2026
    """
    from app.models.myntreal_incentive import MNRAccidentalInsurance
    from sqlalchemy import func, and_, or_
    from datetime import datetime
    
    INSURANCE_ELIGIBILITY_DATE = datetime(2026, 2, 3, 0, 0, 0)
    REQUIRED_REFERRALS = 2
    
    # DC Debug: Log user status
    import logging
    logging.info(f'[DC-Insurance] User {current_user.id} coupon_status: {current_user.coupon_status}')
    
    kyc_status = getattr(current_user, 'kyc_status', 'Pending') or 'Pending'
    kyc_approved = kyc_status.lower() in ['approved', 'verified']
    
    if current_user.coupon_status not in ['Active', 'Activated']:
        return {
            "success": True,
            "has_insurance": False,
            "is_eligible": False,
            "show_banner": True,
            "banner_type": "not_activated",
            "kyc_status": kyc_status,
            "kyc_approved": kyc_approved,
            "message": "Activate your membership to unlock insurance benefits"
        }
    
    # DC Protocol: Welcome Coupon users need 2 successful referrals for insurance
    if getattr(current_user, 'is_welcome_coupon', False):
        wc_referral_count = db.query(func.count(User.id)).filter(
            User.referrer_id == current_user.id,
            User.coupon_status.in_(['Active', 'Activated']),
            User.is_welcome_coupon == False,
            or_(
                User.activation_date >= INSURANCE_ELIGIBILITY_DATE,
                and_(
                    User.activation_date == None,
                    User.coupon_status_changed_at >= INSURANCE_ELIGIBILITY_DATE
                )
            )
        ).scalar() or 0
        
        if wc_referral_count >= REQUIRED_REFERRALS:
            return {
                "success": True,
                "has_insurance": False,
                "is_eligible": True,
                "show_banner": True,
                "banner_type": "eligible",
                "kyc_status": kyc_status,
                "kyc_approved": kyc_approved,
                "referrals_count": wc_referral_count,
                "referrals_needed": 0,
                "message": "You are eligible for Rs. 5,00,000 Accidental Insurance! Insurance will be issued soon."
            }
        else:
            return {
                "success": True,
                "has_insurance": False,
                "is_eligible": False,
                "show_banner": True,
                "banner_type": "referral_required",
                "kyc_status": kyc_status,
                "kyc_approved": kyc_approved,
                "referrals_count": wc_referral_count,
                "referrals_needed": REQUIRED_REFERRALS - wc_referral_count,
                "message": f"2 successful business referrals required for insurance eligibility. You have {wc_referral_count} of {REQUIRED_REFERRALS} required."
            }
    
    existing = db.query(MNRAccidentalInsurance).filter(
        MNRAccidentalInsurance.user_id == current_user.id,
        MNRAccidentalInsurance.status.in_(['Active', 'Issued'])
    ).first()
    
    if existing:
        days_remaining = (existing.expiry_date - datetime.now()).days if existing.expiry_date else 0
        return {
            "success": True,
            "has_insurance": True,
            "is_eligible": True,
            "show_banner": True,
            "banner_type": "insured",
            "kyc_status": kyc_status,
            "kyc_approved": kyc_approved,
            "policy_number": existing.policy_number,
            "insurer_name": existing.insurer_name,
            "insured_amount": existing.insured_amount,
            "insured_date": existing.insured_date.strftime('%d %b %Y') if existing.insured_date else None,
            "expiry_date": existing.expiry_date.strftime('%d %b %Y') if existing.expiry_date else None,
            "days_remaining": max(0, days_remaining),
            "message": f"Congratulations! You are insured for Rs. 5,00,000"
        }
    
    activation_date = current_user.activation_date or current_user.coupon_status_changed_at
    is_new_activation = activation_date and activation_date >= INSURANCE_ELIGIBILITY_DATE
    
    if is_new_activation:
        return {
            "success": True,
            "has_insurance": False,
            "is_eligible": True,
            "show_banner": True,
            "banner_type": "eligible",
            "kyc_status": kyc_status,
            "kyc_approved": kyc_approved,
            "message": "You are eligible for Rs. 5,00,000 Accidental Insurance! Insurance will be issued soon."
        }
    
    # DC Protocol Feb 2026: Alternative eligibility paths for old users
    # Path 1: Check for points usage on service categories
    from app.models.myntreal_incentive import MNRPointsTransaction
    SERVICE_CATEGORIES = ['VGK_REAL_DREAMS', 'VGK_CARE', 'EV_PURCHASE', 'SOLAR_SERVICES']
    
    service_usage_count = db.query(func.count(MNRPointsTransaction.id)).filter(
        MNRPointsTransaction.user_id == current_user.id,
        MNRPointsTransaction.transaction_type == 'debit',
        MNRPointsTransaction.benefit_category.in_(SERVICE_CATEGORIES)
    ).scalar() or 0
    
    if service_usage_count > 0:
        return {
            "success": True,
            "has_insurance": False,
            "is_eligible": True,
            "show_banner": True,
            "banner_type": "eligible",
            "kyc_status": kyc_status,
            "kyc_approved": kyc_approved,
            "message": "You are eligible for Rs. 5,00,000 Accidental Insurance! Insurance will be issued soon."
        }
    
    # Path 2: Check for referral count (kept for backward compatibility)
    referral_count = db.query(func.count(User.id)).filter(
        User.referrer_id == current_user.id,
        User.coupon_status.in_(['Active', 'Activated']),
        or_(
            User.activation_date >= INSURANCE_ELIGIBILITY_DATE,
            and_(
                User.activation_date == None,
                User.coupon_status_changed_at >= INSURANCE_ELIGIBILITY_DATE
            )
        )
    ).scalar() or 0
    
    if referral_count >= REQUIRED_REFERRALS:
        return {
            "success": True,
            "has_insurance": False,
            "is_eligible": True,
            "show_banner": True,
            "banner_type": "eligible",
            "kyc_status": kyc_status,
            "kyc_approved": kyc_approved,
            "referrals_count": referral_count,
            "referrals_needed": 0,
            "message": "You are eligible for Rs. 5,00,000 Accidental Insurance! Insurance will be issued soon."
        }
    
    group_a_referrals = db.query(func.count(User.id)).filter(
        User.referrer_id == current_user.id,
        func.lower(User.position) == 'left',
        User.coupon_status.in_(['Active', 'Activated']),
        or_(
            User.activation_date >= INSURANCE_ELIGIBILITY_DATE,
            and_(
                User.activation_date == None,
                User.coupon_status_changed_at >= INSURANCE_ELIGIBILITY_DATE
            )
        )
    ).scalar() or 0
    
    group_b_referrals = db.query(func.count(User.id)).filter(
        User.referrer_id == current_user.id,
        func.lower(User.position) == 'right',
        User.coupon_status.in_(['Active', 'Activated']),
        or_(
            User.activation_date >= INSURANCE_ELIGIBILITY_DATE,
            and_(
                User.activation_date == None,
                User.coupon_status_changed_at >= INSURANCE_ELIGIBILITY_DATE
            )
        )
    ).scalar() or 0
    
    return {
        "success": True,
        "has_insurance": False,
        "is_eligible": False,
        "show_banner": True,
        "banner_type": "referral_required",
        "kyc_status": kyc_status,
        "kyc_approved": kyc_approved,
        "referrals_count": referral_count,
        "referrals_needed": REQUIRED_REFERRALS,
        "group_a_referrals": group_a_referrals,
        "group_b_referrals": group_b_referrals,
        "message": f"Bring {REQUIRED_REFERRALS - referral_count} more activated referral(s) after Feb 3, 2026 to unlock insurance"
    }


# ===== LEGACY ENDPOINT (keep for compatibility) =====
# NOTE: This MUST be at the END to avoid catching specific routes

@router.get("/{user_id}")
async def get_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user by ID (preserves Flask user access logic)"""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        return {"error": "User not found"}
    
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "user_type": user.user_type,
        "coupon_status": user.coupon_status
    }
