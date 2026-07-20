"""
User Service for FastAPI - User Management Operations
Preserves exact Flask user management and validation logic
"""

from typing import List, Dict, Optional, Any
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc

from app.models.user import User
from app.models.placement import Placement
from app.models.transaction import Transaction
from app.models.coupon import Coupon, CouponActivationTracker
from app.models.base import get_indian_time
from app.core.security import SecurityManager

class UserService:
    """
    User Service handling all user management operations
    Preserves exact Flask user management logic
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by MNR ID (preserves Flask User.query.get logic)"""
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email address"""
        return self.db.query(User).filter(User.email == email).first()
    
    def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create new user with full validation
        Preserves Flask user creation logic
        """
        # Validate required fields (email is optional - collected during KYC)
        # Both first_name and last_name are now mandatory for all new users
        required_fields = ['first_name', 'last_name', 'phone_number', 'password']
        for field in required_fields:
            if field not in user_data or not user_data[field]:
                return {"success": False, "error": f"Missing required field: {field}"}
        
        # Validate that last_name is not just whitespace
        if not user_data['last_name'].strip():
            return {"success": False, "error": "Last name cannot be empty. Please provide both first and last name."}
        
        # Check if email already exists (only if email is provided)
        if user_data.get('email'):
            existing_user = self.get_user_by_email(user_data['email'])
            if existing_user:
                return {"success": False, "error": "Email already registered"}
        
        # DC Protocol (Dec 22, 2025): Allow duplicate mobile numbers during signup
        # Mobile uniqueness is now enforced only at activation time
        # This allows family members or shared phones during registration
        # Users must update to unique mobile before activation
        
        # Generate MNR ID using exact original format: MNR1823XXXXX
        # Format: MNR1823 + 5 random digits (total 12 characters)
        # Example: MNR182345678, MNR182300123, MNR182371007
        import random
        
        # Reserved admin IDs (must never be generated for regular users)
        RESERVED_ADMIN_IDS = {
            'MNR182371007',  # Super Admin
            'MNR182322707',  # System Admin
            'MNR182371010'   # Finance Admin
        }
        
        # Fixed prefix for all MNR IDs
        FIXED_PREFIX = 'MNR1823'
        
        # Generate unique random 5-digit number (00000-99999)
        # Keep trying until we find a non-reserved, unused ID
        max_attempts = 10000  # Increased for better collision handling
        new_user_id = None
        
        for attempt in range(max_attempts):
            random_suffix = random.randint(0, 99999)
            candidate_id = f"{FIXED_PREFIX}{random_suffix:05d}"
            
            # Check if this ID is reserved for admin use
            if candidate_id in RESERVED_ADMIN_IDS:
                continue
            
            # Check if this ID already exists in database
            existing_user = self.db.query(User).filter(User.id == candidate_id).first()
            if not existing_user:
                new_user_id = candidate_id
                break
        
        # If all attempts failed, raise error (should be extremely rare with 100,000 possible IDs)
        if new_user_id is None:
            return {"success": False, "error": "Unable to generate unique MNR ID after maximum attempts. Please try again."}
        
        # Hash password
        hashed_password = SecurityManager.get_password_hash(user_data['password'])
        
        # Create user object (combine first_name + last_name into name)
        full_name = f"{user_data['first_name']} {user_data['last_name']}"
        new_user = User(
            id=new_user_id,
            name=full_name,
            email=user_data.get('email'),  # Optional - collected during KYC if not provided
            phone_number=user_data['phone_number'],
            password=hashed_password,
            referrer_id=user_data.get('sponsor_id'),  # sponsor_id from input maps to referrer_id in DB
            registration_date=get_indian_time(),
            user_type='Member',  # Updated: User type migrated to Member
            account_status='Active',  # Use account_status instead of is_active
            coupon_status='Inactive',  # Default to Inactive until coupon is assigned
            package_points=0,  # Default package points
            placement_status='Unplaced'  # Will be updated after placement
        )
        
        try:
            self.db.add(new_user)
            self.db.commit()
            
            try:
                from app.models.member_lifecycle import MemberLifecycleTracker
                lifecycle = MemberLifecycleTracker(
                    user_id=new_user_id,
                    user_name=full_name,
                    registration_date=new_user.registration_date
                )
                lifecycle.calculate_progress()
                self.db.add(lifecycle)
                self.db.commit()
            except Exception:
                pass
            
            return {
                "success": True,
                "user_id": new_user_id,
                "message": "User created successfully",
                "user_details": {
                    "mnr_id": new_user_id,
                    "user_id": new_user_id,
                    "name": f"{user_data['first_name']} {user_data['last_name']}",
                    "email": user_data.get('email'),
                    "phone_number": user_data['phone_number'],
                    "registration_date": new_user.registration_date.isoformat()
                }
            }
        
        except Exception as e:
            self.db.rollback()
            return {"success": False, "error": f"Database error: {str(e)}"}
    
    def update_user_profile(self, user_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update user profile information
        Preserves Flask profile update logic
        """
        user = self.get_user_by_id(user_id)
        if not user:
            return {"success": False, "error": "User not found"}
        
        # Define updatable fields
        updatable_fields = [
            'first_name', 'last_name', 'mobile', 'address', 'city', 'state', 
            'pincode', 'pan_number', 'aadhar_number', 'bank_account_number',
            'bank_ifsc_code', 'bank_name', 'account_holder_name'
        ]
        
        updated_fields = []
        for field in updatable_fields:
            if field in update_data:
                setattr(user, field, update_data[field])
                updated_fields.append(field)
        
        # Update modification timestamp
        user.last_updated = get_indian_time()
        
        try:
            self.db.commit()
            return {
                "success": True,
                "message": "Profile updated successfully",
                "updated_fields": updated_fields
            }
        except Exception as e:
            self.db.rollback()
            return {"success": False, "error": f"Update failed: {str(e)}"}
    
    def change_password(self, user_id: str, old_password: str, new_password: str) -> Dict[str, Any]:
        """
        Change user password with validation
        Preserves Flask password change logic
        """
        user = self.get_user_by_id(user_id)
        if not user:
            return {"success": False, "error": "User not found"}
        
        # Verify old password
        if not SecurityManager.verify_password(old_password, user.password):
            return {"success": False, "error": "Current password is incorrect"}
        
        # Validate new password strength
        if len(new_password) < 6:
            return {"success": False, "error": "New password must be at least 6 characters"}
        
        # Hash and update new password
        user.password = SecurityManager.get_password_hash(new_password)
        user.last_updated = get_indian_time()
        
        try:
            self.db.commit()
            return {"success": True, "message": "Password changed successfully"}
        except Exception as e:
            self.db.rollback()
            return {"success": False, "error": f"Password change failed: {str(e)}"}
    
    def get_user_dashboard_data(self, user_id: str) -> Dict[str, Any]:
        """
        Get comprehensive dashboard data for user
        Preserves Flask dashboard data structure
        """
        user = self.get_user_by_id(user_id)
        if not user:
            return {"error": "User not found"}
        
        # Get basic user info
        dashboard_data = {
            "user_info": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "mobile": user.phone_number,
                "registration_date": user.registration_date.isoformat() if user.registration_date else None,
                "user_type": user.user_type,
                "is_active": user.activation_date is not None,
                "current_package": getattr(user, 'current_package_type', 'none')
            }
        }
        
        # Get team statistics using corrected binary tree logic
        from app.services.reference_service import ReferenceService
        reference_service = ReferenceService(self.db)
        team_counts = reference_service.get_team_counts(user_id)
        
        dashboard_data["team_stats"] = {
            "left_team_count": team_counts["left_count"],
            "right_team_count": team_counts["right_count"],
            "total_team_size": team_counts["total_count"],
            "direct_referrals": self.db.query(User).filter(User.referrer_id == user_id).count()
        }
        
        # Get financial summary
        current_month = datetime.now().strftime("%Y-%m")
        current_month_transactions = self.db.query(Transaction).filter(
            and_(
                Transaction.user_id == user_id,
                Transaction.financial_period == current_month
            )
        ).all()
        
        total_earnings = sum(t.net_amount for t in current_month_transactions if t.transaction_type == 'credit')
        total_deductions = sum(abs(t.net_amount) for t in current_month_transactions if t.transaction_type == 'debit')
        
        dashboard_data["financial_summary"] = {
            "current_month_earnings": float(total_earnings),
            "current_month_deductions": float(total_deductions),
            "net_current_month": float(total_earnings - total_deductions),
            "wallet_balance": float(getattr(user, 'wallet_balance', 0)),
            "total_transactions": len(current_month_transactions)
        }
        
        # Get active coupons
        active_coupons = self.db.query(Coupon).filter(
            and_(
                Coupon.owner_id == user_id,
                Coupon.status == 'Active'
            )
        ).all()
        
        dashboard_data["coupon_summary"] = {
            "active_coupons_count": len(active_coupons),
            "coupons": [
                {
                    "coupon_code": coupon.coupon_code,
                    "package_type": coupon.package_type,
                    "package_value": float(coupon.package_value),
                    "issue_date": coupon.issue_date.isoformat() if coupon.issue_date else None,
                    "status": coupon.status
                }
                for coupon in active_coupons
            ]
        }
        
        # Get Red Coupon status
        red_coupon_tracker = self.db.query(CouponActivationTracker).filter(
            and_(
                CouponActivationTracker.user_id == user_id,
                CouponActivationTracker.status == 'Pending'
            )
        ).first()
        
        dashboard_data["red_coupon_status"] = {
            "is_red_coupon": getattr(user, 'is_red_coupon', False),
            "red_coupon_locked": getattr(user, 'red_coupon_locked', False),
            "has_pending_activation": red_coupon_tracker is not None,
            "activation_deadline": red_coupon_tracker.activation_deadline.isoformat() if red_coupon_tracker else None
        }
        
        return dashboard_data
    
    def get_user_financial_history(self, user_id: str, limit: int = 50) -> Dict[str, Any]:
        """
        Get user's financial transaction history
        Preserves Flask financial history logic
        """
        user = self.get_user_by_id(user_id)
        if not user:
            return {"error": "User not found"}
        
        transactions = self.db.query(Transaction).filter(
            Transaction.user_id == user_id
        ).order_by(desc(Transaction.transaction_date)).limit(limit).all()
        
        transaction_list = []
        for transaction in transactions:
            transaction_list.append({
                "id": transaction.id,
                "transaction_type": transaction.transaction_type,
                "income_type": transaction.income_type,
                "gross_amount": float(transaction.gross_amount),
                "admin_deduction": float(transaction.admin_deduction),
                "tds_deduction": float(transaction.tds_deduction),
                "net_amount": float(transaction.net_amount),
                "transaction_date": transaction.transaction_date.isoformat(),
                "financial_period": transaction.financial_period,
                "description": transaction.description
            })
        
        # Calculate summary statistics
        total_credits = sum(t.net_amount for t in transactions if t.transaction_type == 'credit')
        total_debits = sum(abs(t.net_amount) for t in transactions if t.transaction_type == 'debit')
        
        return {
            "user_id": user_id,
            "transactions": transaction_list,
            "summary": {
                "total_records": len(transactions),
                "total_credits": float(total_credits),
                "total_debits": float(total_debits),
                "net_balance": float(total_credits - total_debits)
            }
        }
    
    def search_users(self, search_query: str, user_type: Optional[str] = None, 
                    limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search users by various criteria
        Preserves Flask user search functionality
        """
        query = self.db.query(User)
        
        # Apply search filters
        if search_query:
            search_filter = or_(
                User.id.ilike(f"%{search_query}%"),
                User.name.ilike(f"%{search_query}%"),
                User.email.ilike(f"%{search_query}%"),
                User.phone_number.ilike(f"%{search_query}%")
            )
            query = query.filter(search_filter)
        
        # Filter by user type if specified
        if user_type:
            query = query.filter(User.user_type == user_type)
        
        users = query.limit(limit).all()
        
        user_list = []
        for user in users:
            user_list.append({
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "mobile": user.phone_number,
                "user_type": user.user_type,
                "registration_date": user.registration_date.isoformat() if user.registration_date else None,
                "is_active": user.activation_date is not None,
                "sponsor_id": user.referrer_id  # Return as sponsor_id for API compatibility
            })
        
        return user_list
    
    def get_user_team_list(self, user_id: str, levels: int = 5) -> Dict[str, Any]:
        """
        Get user's team members list with hierarchy
        Preserves Flask team list functionality
        """
        user = self.get_user_by_id(user_id)
        if not user:
            return {"error": "User not found"}
        
        def get_team_recursive(current_user_id: str, current_level: int) -> List[Dict[str, Any]]:
            if current_level >= levels:
                return []
            
            team_members = []
            
            # Get direct team members
            direct_members = self.db.query(User).filter(User.referrer_id == current_user_id).all()
            
            for member in direct_members:
                member_data = {
                    "id": member.id,
                    "name": member.name,
                    "email": member.email,
                    "mobile": member.phone_number,
                    "registration_date": member.registration_date.isoformat() if member.registration_date else None,
                    "level": current_level + 1,
                    "sponsor_id": member.referrer_id,
                    "is_active": member.activation_date is not None,
                    "team_members": get_team_recursive(member.id, current_level + 1)
                }
                team_members.append(member_data)
            
            return team_members
        
        team_data = get_team_recursive(user_id, 0)
        
        return {
            "user_id": user_id,
            "team_hierarchy": team_data,
            "total_levels": levels
        }
    
    def update_user_password(self, user_id: str, hashed_password: str) -> bool:
        """
        Update user password with hashed password
        RVZ ID functionality for password resets
        """
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return False
            
            user.password = hashed_password
            self.db.commit()
            return True
            
        except Exception as e:
            self.db.rollback()
            return False
    
    def ensure_unique_active_mobile(self, phone_number: str, current_user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        DC Protocol (Dec 22, 2025): Validate mobile number uniqueness for activation
        
        Checks if the given mobile number is already used by another ACTIVE user.
        Active users are those with activation_date IS NOT NULL.
        
        Args:
            phone_number: The mobile number to validate
            current_user_id: The user being activated (excluded from the check)
        
        Returns:
            dict with 'success' (bool) and 'error' (str) if validation fails
        """
        if not phone_number:
            return {"success": False, "error": "Mobile number is required for activation"}
        
        normalized_phone = phone_number.strip()
        if not normalized_phone:
            return {"success": False, "error": "Mobile number cannot be empty"}
        
        query = self.db.query(User).filter(
            User.phone_number == normalized_phone,
            User.activation_date.isnot(None)
        )
        
        if current_user_id:
            query = query.filter(User.id != current_user_id)
        
        existing_active_user = query.first()
        
        if existing_active_user:
            return {
                "success": False,
                "error": "Please update the different mobile number as it's already used for other active member",
                "conflicting_user_id": existing_active_user.id
            }
        
        return {"success": True}
    
    def activate_user(self, user_id: str, activation_sequence: Optional[int] = None) -> Dict[str, Any]:
        """
        DC Protocol (Dec 22, 2025): Activate a user account
        
        This method:
        1. Validates mobile number uniqueness against active users
        2. Sets activation_date, coupon_status, account_status
        3. Triggers cache refresh
        
        Args:
            user_id: The MNR ID of the user to activate
            activation_sequence: Optional activation sequence number
        
        Returns:
            dict with activation result
        """
        user = self.get_user_by_id(user_id)
        if not user:
            return {"success": False, "error": "User not found"}
        
        if user.activation_date is not None:
            return {"success": False, "error": f"User {user_id} is already activated"}
        
        mobile_check = self.ensure_unique_active_mobile(user.phone_number, user_id)
        if not mobile_check.get("success"):
            return mobile_check
        
        activation_time = get_indian_time()
        user.activation_date = activation_time
        user.coupon_status = 'Active'
        user.account_status = 'Active'
        
        if activation_sequence is not None:
            user.activation_sequence = activation_sequence
        
        try:
            self.db.commit()
            
            try:
                from app.services.leg_metrics_cache_service import LegMetricsCacheService
                cache_service = LegMetricsCacheService(self.db)
                cache_service.refresh_user_metrics(user_id, source='activation_hook')
            except Exception as e:
                pass
            
            return {
                "success": True,
                "message": f"User {user_id} activated successfully",
                "user_id": user_id,
                "activation_date": activation_time.isoformat()
            }
            
        except Exception as e:
            self.db.rollback()
            return {"success": False, "error": f"Activation failed: {str(e)}"}