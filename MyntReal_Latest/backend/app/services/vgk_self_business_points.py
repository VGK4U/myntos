"""
VGK Self-Business Points Engine
Authoritative service for self-business points milestone evaluation,
incremental DVR processing, partner-level concurrency locking,
liability tracking, and reversals.

Business Rules:
- Threshold: Every ₹5,00,000 (5 Lakhs) cumulative qualifying SELF-business DVR = 50,000 points.
- Formula:
    milestones = floor(cumulative_valid_self_business / 500000)
    points_entitled = milestones * 50000
- Carry Forward: Any remainder above a milestone carries forward to subsequent business.
- Incremental: Only newly crossed milestones generate new points.
- Concurrency: Partner row-level lock (with_for_update()) serializes concurrent lead updates.
- Payout Capacity: Uplines receive 0 business points for team business.
- Reversal: Recalculates milestone entitlement; never makes points balance negative;
  tracks unrecovered liabilities and offsets future business points.
"""

from decimal import Decimal
import logging
from sqlalchemy.orm import Session
from app.models.staff_accounts import OfficialPartner
from app.models.crm import CRMLead
from app.models.vgk_business_points import VGKSelfBusinessPointsAccrualLedger
from app.models.staff_accounts import get_indian_time

logger = logging.getLogger(__name__)

DVR_MILESTONE_THRESHOLD = Decimal('500000.00')  # ₹5,00,000 per milestone
POINTS_PER_MILESTONE = Decimal('50000.00')     # 50,000 points per milestone


def process_incremental_self_business_points(db: Session, lead_id: int) -> dict:
    """
    Evaluates incremental deal_value_received (DVR) for a lead and awards self-business points.
    Thread-safe and idempotent: serializes per partner using SELECT FOR UPDATE.
    """
    lead = db.query(CRMLead).filter(CRMLead.id == lead_id).first()
    if not lead:
        return {'success': False, 'error': f'Lead #{lead_id} not found'}

    partner_id = lead.associated_partner_id
    if not partner_id:
        return {'success': True, 'skipped': True, 'reason': 'No associated partner on lead'}

    # 1. Partner row-level lock (serializes concurrent deal evaluations for this producer)
    partner = db.query(OfficialPartner).filter(
        OfficialPartner.id == partner_id
    ).with_for_update().first()

    if not partner:
        return {'success': False, 'error': f'Partner #{partner_id} not found'}

    # 2. Incremental DVR calculation on the lead
    curr_lead_dvr = Decimal(str(lead.deal_value_received or 0))
    prev_lead_dvr = Decimal(str(lead.points_evaluated_dvr or 0))
    incremental_dvr = curr_lead_dvr - prev_lead_dvr

    if incremental_dvr <= Decimal('0'):
        return {
            'success': True,
            'skipped': True,
            'reason': 'No incremental DVR to evaluate',
            'current_lead_dvr': float(curr_lead_dvr),
            'points_evaluated_dvr': float(prev_lead_dvr),
        }

    # 3. Cumulative DVR on partner
    prev_cum_dvr = Decimal(str(partner.cumulative_self_business_dvr or 0))
    new_cum_dvr = prev_cum_dvr + incremental_dvr

    # 4. Milestone evaluation (₹5,00,000 blocks)
    milestones_before = int(prev_cum_dvr // DVR_MILESTONE_THRESHOLD)
    milestones_after = int(new_cum_dvr // DVR_MILESTONE_THRESHOLD)
    milestones_crossed = milestones_after - milestones_before
    points_entitled = Decimal(str(milestones_crossed)) * POINTS_PER_MILESTONE
    carry_forward = new_cum_dvr % DVR_MILESTONE_THRESHOLD

    # 4.5. Business Activation Rule: 1 completed qualifying lead activates partner
    if curr_lead_dvr > Decimal('0') and not getattr(partner, 'is_business_activated', False):
        partner.is_business_activated = True
        partner.is_active = True
        logger.info(f"[VGK-ACTIVATION] Partner #{partner.id} business-activated by lead #{lead.id} (DVR: ₹{curr_lead_dvr:,.2f})")

    # 5. Liability Offset & Points Award
    points_to_credit = Decimal('0')
    liability_offset = Decimal('0')
    ledger_entry_id = None

    if points_entitled > Decimal('0'):
        current_liability = Decimal(str(partner.points_recovery_liability or 0))
        if current_liability > Decimal('0'):
            if points_entitled <= current_liability:
                liability_offset = points_entitled
                partner.points_recovery_liability = current_liability - points_entitled
                points_to_credit = Decimal('0')
            else:
                liability_offset = current_liability
                partner.points_recovery_liability = Decimal('0')
                points_to_credit = points_entitled - current_liability
        else:
            points_to_credit = points_entitled

        if points_to_credit > Decimal('0'):
            from app.services.vgk_commission import add_vgk_points_entry
            pts_entry = add_vgk_points_entry(
                db=db,
                partner_id=partner.id,
                points_credit=points_to_credit,
                points_debit=Decimal('0'),
                reason_code='BUSINESS_V2',
                reference_type='CRM_LEAD',
                reference_id=lead.id,
                notes=(
                    f'Self-business points bonus — lead #{lead.id} '
                    f'(DVR +₹{incremental_dvr:,.2f}, cum ₹{new_cum_dvr:,.2f}, '
                    f'{milestones_crossed} milestone(s) crossed)'
                ),
            )
            ledger_entry_id = pts_entry.id

    # 6. Update Partner and Lead State
    partner.cumulative_self_business_dvr = new_cum_dvr
    lead.points_evaluated_dvr = curr_lead_dvr

    # 7. Audit log in vgk_self_business_points_accrual_ledger
    accrual_row = VGKSelfBusinessPointsAccrualLedger(
        partner_id=partner.id,
        lead_id=lead.id,
        previous_lead_dvr=prev_lead_dvr,
        current_lead_dvr=curr_lead_dvr,
        incremental_dvr=incremental_dvr,
        partner_cumulative_dvr_before=prev_cum_dvr,
        partner_cumulative_dvr_after=new_cum_dvr,
        milestones_crossed=milestones_crossed,
        points_awarded=points_entitled,
        carry_forward_volume=carry_forward,
        ledger_entry_id=ledger_entry_id,
        transaction_type='ACCRUAL',
        liability_offset_amount=liability_offset,
    )
    db.add(accrual_row)
    db.flush()

    logger.info(
        f'[VGK-SELF-BUSINESS-PTS] Lead #{lead.id} processed for partner #{partner.id}: '
        f'inc_dvr=₹{float(incremental_dvr):,.2f}, cum_dvr=₹{float(new_cum_dvr):,.2f}, '
        f'milestones_crossed={milestones_crossed}, points_entitled={float(points_entitled)}, '
        f'points_credited={float(points_to_credit)}, liability_offset={float(liability_offset)}, '
        f'carry_forward=₹{float(carry_forward):,.2f}'
    )

    return {
        'success': True,
        'lead_id': lead.id,
        'partner_id': partner.id,
        'incremental_dvr': float(incremental_dvr),
        'cumulative_dvr': float(new_cum_dvr),
        'milestones_crossed': milestones_crossed,
        'points_entitled': float(points_entitled),
        'points_credited': float(points_to_credit),
        'liability_offset': float(liability_offset),
        'carry_forward': float(carry_forward),
        'ledger_entry_id': ledger_entry_id,
        'partner_balance_after': float(partner.vgk_points_balance or 0),
        'points_recovery_liability': float(partner.points_recovery_liability or 0),
    }


def reverse_self_business_points(
    db: Session, lead_id: int, reason: str = 'Deal cancellation / DVR reduction'
) -> dict:
    """
    Reverses self-business points when lead DVR is reduced or cancelled.
    Idempotent and safe: never forces balance negative; stores unrecovered points as liability.
    """
    lead = db.query(CRMLead).filter(CRMLead.id == lead_id).first()
    if not lead:
        return {'success': False, 'error': f'Lead #{lead_id} not found'}

    partner_id = lead.associated_partner_id
    if not partner_id:
        return {'success': True, 'skipped': True, 'reason': 'No associated partner on lead'}

    # 1. Partner row-level lock
    partner = db.query(OfficialPartner).filter(
        OfficialPartner.id == partner_id
    ).with_for_update().first()

    if not partner:
        return {'success': False, 'error': f'Partner #{partner_id} not found'}

    curr_lead_dvr = Decimal(str(lead.deal_value_received or 0))
    prev_lead_dvr = Decimal(str(lead.points_evaluated_dvr or 0))

    # Era guard: leads with 0 evaluated V2 DVR are exempt from V2 points reversal
    if prev_lead_dvr <= Decimal('0'):
        return {
            'success': True,
            'skipped': True,
            'reason': 'Lead has zero evaluated DVR under V2 — exempt from V2 points reversal',
            'current_lead_dvr': float(curr_lead_dvr),
            'points_evaluated_dvr': float(prev_lead_dvr),
        }

    dvr_difference = curr_lead_dvr - prev_lead_dvr

    if dvr_difference >= Decimal('0'):
        return {
            'success': True,
            'skipped': True,
            'reason': 'No DVR reduction on lead',
            'current_lead_dvr': float(curr_lead_dvr),
            'points_evaluated_dvr': float(prev_lead_dvr),
        }

    reversed_dvr = abs(dvr_difference)
    prev_cum_dvr = Decimal(str(partner.cumulative_self_business_dvr or 0))
    new_cum_dvr = max(Decimal('0'), prev_cum_dvr - reversed_dvr)

    # 2. Milestone recalculation on reduced cumulative volume
    milestones_before = int(prev_cum_dvr // DVR_MILESTONE_THRESHOLD)
    milestones_after = int(new_cum_dvr // DVR_MILESTONE_THRESHOLD)
    milestones_to_reverse = max(0, milestones_before - milestones_after)
    points_to_reverse = Decimal(str(milestones_to_reverse)) * POINTS_PER_MILESTONE
    carry_forward = new_cum_dvr % DVR_MILESTONE_THRESHOLD

    # 3. Points Debit and Liability Handling
    points_debited = Decimal('0')
    unrecovered = Decimal('0')
    ledger_entry_id = None

    if points_to_reverse > Decimal('0'):
        avail_pts = Decimal(str(partner.vgk_points_balance or 0))
        points_debited = min(avail_pts, points_to_reverse)
        unrecovered = points_to_reverse - points_debited

        if points_debited > Decimal('0'):
            from app.services.vgk_commission import add_vgk_points_entry
            pts_entry = add_vgk_points_entry(
                db=db,
                partner_id=partner.id,
                points_credit=Decimal('0'),
                points_debit=points_debited,
                reason_code='BUSINESS_REVERSAL_V2',
                reference_type='CRM_LEAD',
                reference_id=lead.id,
                notes=(
                    f'Self-business points reversal — lead #{lead.id} DVR reduced by '
                    f'₹{reversed_dvr:,.2f} ({reason})'
                ),
            )
            ledger_entry_id = pts_entry.id

        if unrecovered > Decimal('0'):
            partner.points_recovery_liability = (
                Decimal(str(partner.points_recovery_liability or 0)) + unrecovered
            )

    # 4. Update Partner and Lead State
    partner.cumulative_self_business_dvr = new_cum_dvr
    lead.points_evaluated_dvr = curr_lead_dvr

    # 5. Audit log in vgk_self_business_points_accrual_ledger
    accrual_row = VGKSelfBusinessPointsAccrualLedger(
        partner_id=partner.id,
        lead_id=lead.id,
        previous_lead_dvr=prev_lead_dvr,
        current_lead_dvr=curr_lead_dvr,
        incremental_dvr=-reversed_dvr,
        partner_cumulative_dvr_before=prev_cum_dvr,
        partner_cumulative_dvr_after=new_cum_dvr,
        milestones_crossed=-milestones_to_reverse,
        points_awarded=-points_to_reverse,
        carry_forward_volume=carry_forward,
        ledger_entry_id=ledger_entry_id,
        transaction_type='REVERSAL',
        liability_offset_amount=unrecovered,
    )
    db.add(accrual_row)
    db.flush()

    logger.warning(
        f'[VGK-SELF-BUSINESS-REVERSAL] Lead #{lead.id} reversal for partner #{partner.id}: '
        f'reversed_dvr=₹{float(reversed_dvr):,.2f}, cum_dvr=₹{float(new_cum_dvr):,.2f}, '
        f'milestones_reversed={milestones_to_reverse}, points_to_reverse={float(points_to_reverse)}, '
        f'points_debited={float(points_debited)}, unrecovered_liability={float(unrecovered)}'
    )

    return {
        'success': True,
        'lead_id': lead.id,
        'partner_id': partner.id,
        'reversed_dvr': float(reversed_dvr),
        'cumulative_dvr': float(new_cum_dvr),
        'milestones_reversed': milestones_to_reverse,
        'points_to_reverse': float(points_to_reverse),
        'points_debited': float(points_debited),
        'unrecovered_liability': float(unrecovered),
        'carry_forward': float(carry_forward),
        'ledger_entry_id': ledger_entry_id,
        'partner_balance_after': float(partner.vgk_points_balance or 0),
        'points_recovery_liability': float(partner.points_recovery_liability or 0),
    }
