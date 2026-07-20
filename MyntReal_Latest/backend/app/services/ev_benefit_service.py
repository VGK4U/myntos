"""
EV Benefit Service - Comprehensive Benefit Calculation & Application
Handles all 7 benefit types: EV_Discount, RoyalEV_Bonus, Training_Cashback, 
Referral_Opportunity, Franchise_Referral, Insurance_Referral, Fleet_Referral
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from decimal import Decimal
from datetime import datetime
import random
import string
from typing import Optional, Dict, List

from app.models.ev_discount import (
    CouponBenefit, ReferralIncome, FranchisePurchase, 
    InsurancePolicy, FleetOrder, Purchase, EV
)
from app.models.coupon import EnhancedCoupon
from app.models.user import User


class EVBenefitService:
    """Comprehensive EV Benefit Management Service"""
    
    @staticmethod
    def generate_code(prefix: str) -> str:
        """Generate unique code for benefits"""
        random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        timestamp = datetime.now().strftime('%y%m%d')
        return f"{prefix}{timestamp}{random_str}"
    
    
    # ==================== RoyalEV Bonus System ====================
    
    @staticmethod
    def apply_royal_ev_bonus(
        db: Session,
        user_id: str,
        purchase_id: int,
        ev_model: str,
        ev_price: Decimal,
        package_tier: str,
        coupon_id: Optional[int] = None
    ) -> Optional[CouponBenefit]:
        """
        Apply RoyalEV Bonus for premium vehicle purchases (selected models only)
        
        Bonus Structure (on invoice value):
        - Blue Package: 5% bonus (cap: MIN(coupon_value + upgrade_wallet, ₹15,000))
        - Loyal Package: 10% bonus (cap: MIN(coupon_value + upgrade_wallet, ₹15,000))
        - Diamond Package: 5% bonus (cap: MIN(coupon_value + upgrade_wallet, ₹15,000))
        - Platinum Package: 15% bonus (cap: Fixed ₹15,000)
        
        CRITICAL VALIDATION: Total of (coupon_value + upgrade_wallet) is capped at ₹15,000 maximum for Blue/Loyal/Diamond
        Applies ONLY to selected models (admin-configured with max_discount_percentage=100)
        """
        if 'Royal' not in ev_model:
            return None
        
        # Get user's wallet data for dynamic cap calculation
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        
        # Get coupon value if available
        coupon_value = Decimal('0')
        if coupon_id:
            coupon = db.query(EnhancedCoupon).filter(EnhancedCoupon.coupon_id == coupon_id).first()
            if coupon:
                coupon_value = Decimal(str(coupon.coupon_value))
        
        # Get upgrade wallet balance (defensive: default to 0 if not exists)
        upgrade_wallet_balance = Decimal(str(getattr(user, 'upgrade_wallet_balance', 0) or 0))
        
        # CRITICAL VALIDATION: For Blue/Loyal/Diamond, TOTAL of (coupon_value + upgrade_wallet) capped at ₹15,000
        MAX_TOTAL_CAP = Decimal('15000')
        
        # Calculate bonus rate and cap based on package tier with proper validations
        if package_tier in ['Blue', 'Star']:  # Star kept for backward compatibility if exists in old data
            bonus_rate = Decimal('0.05')
            # TOTAL cap: MIN(coupon_value + upgrade_wallet_balance, ₹15,000)
            max_cap = min(coupon_value + upgrade_wallet_balance, MAX_TOTAL_CAP)
        elif package_tier == 'Loyal':
            bonus_rate = Decimal('0.10')
            # TOTAL cap: MIN(coupon_value + upgrade_wallet_balance, ₹15,000)
            max_cap = min(coupon_value + upgrade_wallet_balance, MAX_TOTAL_CAP)
        elif package_tier == 'Diamond':
            bonus_rate = Decimal('0.05')
            # TOTAL cap: MIN(coupon_value + upgrade_wallet_balance, ₹15,000)
            max_cap = min(coupon_value + upgrade_wallet_balance, MAX_TOTAL_CAP)
        elif package_tier == 'Platinum':
            bonus_rate = Decimal('0.15')
            # Platinum has fixed cap of ₹15,000 (no coupon/wallet contribution)
            max_cap = Decimal('15000')
        else:
            return None
        
        # Calculate bonus amount
        bonus_amount = ev_price * bonus_rate
        
        # Apply cap
        if bonus_amount > max_cap:
            bonus_amount = max_cap
        
        benefit = CouponBenefit(
            ev_coupon_id=coupon_id or 0,
            user_id=user_id,
            purchase_id=purchase_id,
            benefit_type='RoyalEV_Bonus',
            benefit_description=f"RoyalEV Bonus ({int(bonus_rate * 100)}%, max ₹{max_cap:,.0f}) on {ev_model}",
            original_amount=ev_price,
            discount_amount=Decimal('0'),
            final_amount=ev_price,
            cashback_amount=bonus_amount,
            status='Applied',
            applied_date=datetime.utcnow(),
            verification_status='Pending'
        )
        
        db.add(benefit)
        db.commit()
        db.refresh(benefit)
        
        return benefit
    
    
    # ==================== Referral Opportunity System ====================
    
    @staticmethod
    def calculate_referral_commission(
        db: Session,
        purchaser_id: str,
        purchase_amount: Decimal,
        referral_type: str = 'EV'
    ) -> List[ReferralIncome]:
        """
        Calculate and create referral income when someone makes a purchase
        
        Commission Structure:
        - Direct Referrer: 3% of purchase amount
        - Indirect Referrer (upline): 1.5% of purchase amount
        """
        purchaser = db.query(User).filter(User.id == purchaser_id).first()
        
        if not purchaser or not purchaser.referrer_id:
            return []
        
        incomes_created = []
        
        # Direct referrer gets 3%
        direct_commission = purchase_amount * Decimal('0.03')
        direct_income = ReferralIncome(
            referral_code=EVBenefitService.generate_code('REF'),
            earner_user_id=purchaser.referrer_id,
            purchaser_user_id=purchaser_id,
            referral_type=referral_type,
            purchase_amount=purchase_amount,
            commission_rate=Decimal('3.0'),
            commission_amount=direct_commission,
            status='Pending',
            earned_date=datetime.utcnow()
        )
        db.add(direct_income)
        incomes_created.append(direct_income)
        
        # Indirect referrer (referrer's referrer) gets 1.5%
        direct_referrer = db.query(User).filter(User.id == purchaser.referrer_id).first()
        if direct_referrer and direct_referrer.referrer_id:
            indirect_commission = purchase_amount * Decimal('0.015')
            indirect_income = ReferralIncome(
                referral_code=EVBenefitService.generate_code('REF'),
                earner_user_id=direct_referrer.referrer_id,
                purchaser_user_id=purchaser_id,
                referral_type=referral_type,
                purchase_amount=purchase_amount,
                commission_rate=Decimal('1.5'),
                commission_amount=indirect_commission,
                status='Pending',
                earned_date=datetime.utcnow()
            )
            db.add(indirect_income)
            incomes_created.append(indirect_income)
        
        db.commit()
        return incomes_created
    
    
    # ==================== Franchise Referral System ====================
    
    @staticmethod
    def create_franchise_purchase(
        db: Session,
        franchisee_user_id: str,
        franchise_name: str,
        vehicle_model: str,
        vehicle_count: int,
        unit_price: Decimal,
        gst_number: Optional[str] = None,
        is_initial_investment: bool = True
    ) -> FranchisePurchase:
        """
        Create franchise purchase with simplified commission structure
        
        Commission Structure (UPDATED):
        - Initial Investment: 2% commission (stored as "Tier1" for backward compatibility)
        - Future Billings: 1% commission (stored as "Tier2" for backward compatibility)
        
        Note: min 5 vehicles every 2 months required for future billings (enforced at UI layer)
        """
        total_amount = unit_price * vehicle_count
        
        # Simplified commission structure with backward-compatible tier names
        if is_initial_investment:
            commission_rate = Decimal('2.0')
            tier = 'Tier1'  # Keep existing tier name for backward compatibility
        else:
            commission_rate = Decimal('1.0')
            tier = 'Tier2'  # Keep existing tier name for backward compatibility
        
        total_commission = total_amount * (commission_rate / 100)
        
        franchise = FranchisePurchase(
            franchise_code=EVBenefitService.generate_code('FRN'),
            franchisee_user_id=franchisee_user_id,
            franchise_name=franchise_name,
            gst_number=gst_number,
            vehicle_count=vehicle_count,
            vehicle_model=vehicle_model,
            unit_price=unit_price,
            total_amount=total_amount,
            discount_amount=Decimal('0'),
            final_amount=total_amount,
            commission_tier=tier,
            commission_rate=commission_rate,
            total_commission=total_commission,
            status='Pending',
            order_date=datetime.utcnow()
        )
        
        db.add(franchise)
        db.commit()
        db.refresh(franchise)
        
        # Calculate referral income for franchisee's upline
        EVBenefitService.calculate_referral_commission(
            db, franchisee_user_id, total_amount, 'Franchise'
        )
        
        return franchise
    
    
    # ==================== Insurance Referral System ====================
    
    @staticmethod
    def create_insurance_policy(
        db: Session,
        user_id: str,
        vehicle_registration: str,
        insurance_provider: str,
        policy_type: str,
        coverage_amount: Decimal,
        premium_amount: Decimal,
        policy_start_date: datetime,
        policy_end_date: datetime,
        referred_by_user_id: Optional[str] = None,
        commission_percentage: Optional[Decimal] = None
    ) -> InsurancePolicy:
        """
        Create insurance policy with referral commission
        
        Commission: Admin-configurable 5%-25% based on policy referred
        Default: 5% if not specified
        """
        commission_amount = None
        
        # Use admin-configured commission percentage (5%-25% range)
        if commission_percentage is None:
            commission_percentage = Decimal('5.0')
        
        # Validate commission is within allowed range
        if commission_percentage < Decimal('5.0') or commission_percentage > Decimal('25.0'):
            commission_percentage = Decimal('5.0')
        
        if referred_by_user_id:
            commission_amount = premium_amount * (commission_percentage / 100)
        
        policy = InsurancePolicy(
            policy_number=EVBenefitService.generate_code('INS'),
            user_id=user_id,
            vehicle_registration=vehicle_registration,
            insurance_provider=insurance_provider,
            policy_type=policy_type,
            coverage_amount=coverage_amount,
            premium_amount=premium_amount,
            referred_by_user_id=referred_by_user_id,
            commission_rate=commission_percentage,
            commission_amount=commission_amount,
            policy_start_date=policy_start_date,
            policy_end_date=policy_end_date,
            issue_date=datetime.utcnow(),
            status='Active'
        )
        
        db.add(policy)
        db.commit()
        db.refresh(policy)
        
        # Create referral income
        if referred_by_user_id and commission_amount:
            referral_income = ReferralIncome(
                referral_code=EVBenefitService.generate_code('REF'),
                earner_user_id=referred_by_user_id,
                purchaser_user_id=user_id,
                referral_type='Insurance',
                purchase_amount=premium_amount,
                commission_rate=commission_percentage,
                commission_amount=commission_amount,
                status='Pending',
                earned_date=datetime.utcnow()
            )
            db.add(referral_income)
            db.commit()
        
        return policy
    
    
    # ==================== Fleet Referral System ====================
    
    @staticmethod
    def create_fleet_order(
        db: Session,
        company_name: str,
        contact_person_user_id: str,
        gst_number: str,
        vehicle_model: str,
        quantity: int,
        unit_price: Decimal,
        negotiated_discount: Decimal = Decimal('0'),
        primary_referrer_id: Optional[str] = None,
        is_initial_investment: bool = True,
        monthly_investor_income: Optional[Decimal] = None
    ) -> FleetOrder:
        """
        Create fleet order with simplified commission structure
        
        Commission Structure (UPDATED):
        - Initial Investment: 2% on investment amount
        - Monthly Payout: 1% on investor income
        
        Note: Removed complex tier system (Small/Medium/Large) and 70%/30% split per user requirements
        """
        total_order_value = unit_price * quantity
        final_order_value = total_order_value - negotiated_discount
        
        # Simplified commission structure
        if is_initial_investment:
            # Initial investment: 2% commission
            base_rate = Decimal('2.0')
            bonus_rate = Decimal('0')
            tier = 'Small'  # Keep for backward compatibility
            commission_base = final_order_value
        else:
            # Monthly payout: 1% on investor income
            base_rate = Decimal('1.0')
            bonus_rate = Decimal('0')
            tier = 'Medium'  # Keep for backward compatibility
            commission_base = monthly_investor_income or Decimal('0')
        
        total_commission_rate = base_rate
        total_commission_pool = commission_base * (total_commission_rate / 100)
        
        fleet_order = FleetOrder(
            fleet_order_number=EVBenefitService.generate_code('FLT'),
            company_name=company_name,
            contact_person_user_id=contact_person_user_id,
            gst_number=gst_number,
            vehicle_model=vehicle_model,
            quantity=quantity,
            unit_price=unit_price,
            total_order_value=total_order_value,
            negotiated_discount=negotiated_discount,
            final_order_value=final_order_value,
            tier_level=tier,
            base_commission_rate=base_rate,
            bonus_commission_rate=bonus_rate,
            total_commission_pool=total_commission_pool,
            primary_referrer_id=primary_referrer_id,
            secondary_referrer_id=None,  # Removed split per new requirements
            status='Pending',
            order_date=datetime.utcnow()
        )
        
        db.add(fleet_order)
        db.commit()
        db.refresh(fleet_order)
        
        # Create referral income (single referrer only, no split)
        if primary_referrer_id and total_commission_pool > 0:
            referral_income = ReferralIncome(
                referral_code=EVBenefitService.generate_code('REF'),
                earner_user_id=primary_referrer_id,
                purchaser_user_id=contact_person_user_id,
                referral_type='Fleet',
                purchase_amount=commission_base,
                commission_rate=total_commission_rate,
                commission_amount=total_commission_pool,
                status='Pending',
                earned_date=datetime.utcnow()
            )
            db.add(referral_income)
            db.commit()
        
        return fleet_order
    
    
    # ==================== Benefit Analytics ====================
    
    @staticmethod
    def get_user_benefit_summary(db: Session, user_id: str) -> Dict:
        """Get comprehensive benefit summary for user"""
        
        # Total benefits received
        total_benefits = db.query(CouponBenefit).filter(
            CouponBenefit.user_id == user_id
        ).all()
        
        # Referral incomes earned
        referral_incomes = db.query(ReferralIncome).filter(
            ReferralIncome.earner_user_id == user_id
        ).all()
        
        # Breakdown by benefit type
        benefit_breakdown = {}
        total_discount = Decimal('0')
        total_cashback = Decimal('0')
        
        for benefit in total_benefits:
            if benefit.benefit_type not in benefit_breakdown:
                benefit_breakdown[benefit.benefit_type] = {
                    'count': 0,
                    'total_discount': Decimal('0'),
                    'total_cashback': Decimal('0')
                }
            benefit_breakdown[benefit.benefit_type]['count'] += 1
            benefit_breakdown[benefit.benefit_type]['total_discount'] += benefit.discount_amount or Decimal('0')
            benefit_breakdown[benefit.benefit_type]['total_cashback'] += benefit.cashback_amount or Decimal('0')
            
            total_discount += benefit.discount_amount or Decimal('0')
            total_cashback += benefit.cashback_amount or Decimal('0')
        
        # Referral income breakdown
        referral_breakdown = {}
        total_referral_income = Decimal('0')
        
        for income in referral_incomes:
            if income.referral_type not in referral_breakdown:
                referral_breakdown[income.referral_type] = {
                    'count': 0,
                    'total_commission': Decimal('0'),
                    'pending': Decimal('0'),
                    'approved': Decimal('0'),
                    'paid': Decimal('0')
                }
            referral_breakdown[income.referral_type]['count'] += 1
            referral_breakdown[income.referral_type]['total_commission'] += income.commission_amount
            
            if income.status == 'Pending':
                referral_breakdown[income.referral_type]['pending'] += income.commission_amount
            elif income.status == 'Approved':
                referral_breakdown[income.referral_type]['approved'] += income.commission_amount
            elif income.status == 'Paid':
                referral_breakdown[income.referral_type]['paid'] += income.commission_amount
            
            total_referral_income += income.commission_amount
        
        return {
            'total_benefits_count': len(total_benefits),
            'total_discount_received': float(total_discount),
            'total_cashback_received': float(total_cashback),
            'benefit_breakdown': {k: {
                'count': v['count'],
                'total_discount': float(v['total_discount']),
                'total_cashback': float(v['total_cashback'])
            } for k, v in benefit_breakdown.items()},
            'total_referral_incomes_count': len(referral_incomes),
            'total_referral_income': float(total_referral_income),
            'referral_breakdown': {k: {
                'count': v['count'],
                'total_commission': float(v['total_commission']),
                'pending': float(v['pending']),
                'approved': float(v['approved']),
                'paid': float(v['paid'])
            } for k, v in referral_breakdown.items()}
        }
    
    
    @staticmethod
    def get_admin_benefit_analytics(db: Session) -> Dict:
        """Get system-wide benefit analytics for admin"""
        
        all_benefits = db.query(CouponBenefit).all()
        all_referral_incomes = db.query(ReferralIncome).all()
        
        # System-wide totals
        total_benefits = len(all_benefits)
        total_discount = sum(b.discount_amount or Decimal('0') for b in all_benefits)
        total_cashback = sum(b.cashback_amount or Decimal('0') for b in all_benefits)
        
        total_referral_commission = sum(r.commission_amount for r in all_referral_incomes)
        pending_commission = sum(r.commission_amount for r in all_referral_incomes if r.status == 'Pending')
        
        # Benefit type distribution
        benefit_distribution = {}
        for benefit in all_benefits:
            if benefit.benefit_type not in benefit_distribution:
                benefit_distribution[benefit.benefit_type] = 0
            benefit_distribution[benefit.benefit_type] += 1
        
        # Referral type distribution
        referral_distribution = {}
        for income in all_referral_incomes:
            if income.referral_type not in referral_distribution:
                referral_distribution[income.referral_type] = {
                    'count': 0,
                    'total': Decimal('0')
                }
            referral_distribution[income.referral_type]['count'] += 1
            referral_distribution[income.referral_type]['total'] += income.commission_amount
        
        return {
            'total_benefits': total_benefits,
            'total_discount_given': float(total_discount),
            'total_cashback_given': float(total_cashback),
            'benefit_distribution': benefit_distribution,
            'total_referral_commission': float(total_referral_commission),
            'pending_commission': float(pending_commission),
            'referral_distribution': {k: {
                'count': v['count'],
                'total': float(v['total'])
            } for k, v in referral_distribution.items()}
        }
