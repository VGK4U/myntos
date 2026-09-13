"""
VGK Team Lead Points Engine (V2 Rule)
Authoritative service for awarding and reversing +2,000 V2 points
when a direct team member adds a qualifying CRM lead.

Business Rules:
1. When a direct team member adds a qualifying lead, their direct sponsor receives +2,000 V2 points.
2. Producer receives 0 points from this rule.
3. Uplines (L2, L3, etc.) receive 0 points from this rule (strict direct sponsor only).
4. One lead = maximum ONE 2,000-point reward (deterministic idempotency).
5. Self-lead = 0 points.
6. Missing/inactive sponsor = 0 points (no upline compression).
7. Prospective only: no backfill for historical leads.
8. Reversal upon genuine deletion/cancellation: points debited up to available balance;
   excess charged to points_recovery_liability so points balance never becomes negative.
"""

from decimal import Decimal
import logging
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.staff_accounts import OfficialPartner, VGKPointsLedger, get_indian_time
from app.models.crm import CRMLead

logger = logging.getLogger(__name__)

DIRECT_TEAM_LEAD_POINTS = Decimal('2000.00')  # +2,000 points per qualifying direct team lead


def award_direct_team_lead_points(db: Session, lead_id: int) -> dict:
    """
    Awards +2,000 V2 points to the direct sponsor of the partner who produced the lead.
    Thread-safe, deterministic, and idempotent via database partial unique index and row-level lock.
    """
    lead = db.query(CRMLead).filter(CRMLead.id == lead_id).first()
    if not lead:
        return {'success': False, 'error': f'Lead #{lead_id} not found'}

    # 1. Idempotency fast check on lead attribute
    if getattr(lead, 'direct_team_lead_points_awarded', False):
        return {
            'success': True,
            'skipped': True,
            'reason': 'Points already awarded for this lead (lead flag)',
            'lead_id': lead_id,
        }

    # 2. Database idempotency check in vgk_points_ledger
    existing_entry = db.query(VGKPointsLedger).filter(
        VGKPointsLedger.reference_type == 'CRM_LEAD',
        VGKPointsLedger.reference_id == lead_id,
        VGKPointsLedger.reason_code == 'DIRECT_TEAM_LEAD_V2',
    ).first()
    if existing_entry:
        lead.direct_team_lead_points_awarded = True
        return {
            'success': True,
            'skipped': True,
            'reason': 'Points already awarded for this lead (ledger record exists)',
            'lead_id': lead_id,
            'ledger_entry_id': existing_entry.id,
        }

    # 3. Producer validation
    producer_id = lead.associated_partner_id
    if not producer_id:
        return {
            'success': True,
            'skipped': True,
            'reason': 'No associated partner on lead',
            'lead_id': lead_id,
        }

    producer = db.query(OfficialPartner).filter(OfficialPartner.id == producer_id).first()
    if not producer:
        return {'success': False, 'error': f'Producer partner #{producer_id} not found'}

    if producer.category != 'VGK_TEAM':
        return {
            'success': True,
            'skipped': True,
            'reason': f'Producer {producer.partner_code} is not a VGK_TEAM partner ({producer.category})',
            'lead_id': lead_id,
        }

    # 4. Direct Sponsor resolution & eligibility
    sponsor_id = producer.parent_partner_id
    if not sponsor_id:
        return {
            'success': True,
            'skipped': True,
            'reason': f'Producer {producer.partner_code} has no direct sponsor',
            'lead_id': lead_id,
        }

    # Self-sponsorship / circular guard
    if sponsor_id == producer.id:
        return {
            'success': True,
            'skipped': True,
            'reason': 'Self-sponsorship detected — 0 points awarded',
            'lead_id': lead_id,
        }

    # Acquire row-level lock on sponsor to serialize concurrent balance mutations
    sponsor = db.query(OfficialPartner).filter(
        OfficialPartner.id == sponsor_id
    ).with_for_update().first()

    if not sponsor:
        return {'success': False, 'error': f'Sponsor partner #{sponsor_id} not found'}

    if sponsor.category != 'VGK_TEAM':
        return {
            'success': True,
            'skipped': True,
            'reason': f'Sponsor {sponsor.partner_code} is not a VGK_TEAM partner',
            'lead_id': lead_id,
        }

    if not sponsor.is_active:
        return {
            'success': True,
            'skipped': True,
            'reason': f'Sponsor {sponsor.partner_code} is inactive — follows existing eligibility rules (0 points)',
            'lead_id': lead_id,
        }

    # Exclude root company account
    if (sponsor.partner_code or '').upper() == 'VGK07102207':
        return {
            'success': True,
            'skipped': True,
            'reason': 'Root company account excluded from referral points',
            'lead_id': lead_id,
        }

    # 5. Qualifying lead validation (customer contact & self-lead checks)
    lead_name = (lead.name or '').strip()
    lead_phone = (lead.phone or '').strip().replace(' ', '').replace('-', '')
    if not lead_name or len(lead_phone) < 10:
        return {
            'success': True,
            'skipped': True,
            'reason': 'Lead missing valid customer name or 10-digit phone',
            'lead_id': lead_id,
        }

    # Self-lead check: customer phone cannot be sponsor's own phone
    sponsor_phone = (sponsor.phone or '').strip().replace(' ', '').replace('-', '')
    if sponsor_phone and lead_phone.endswith(sponsor_phone[-10:]):
        return {
            'success': True,
            'skipped': True,
            'reason': 'Self-lead detected: customer phone matches sponsor phone',
            'lead_id': lead_id,
        }

    # 6. Award +2,000 points to direct sponsor
    from app.services.vgk_commission import add_vgk_points_entry
    now = get_indian_time()
    try:
        pts_entry = add_vgk_points_entry(
            db=db,
            partner_id=sponsor.id,
            points_credit=DIRECT_TEAM_LEAD_POINTS,
            points_debit=Decimal('0'),
            reason_code='DIRECT_TEAM_LEAD_V2',
            reference_type='CRM_LEAD',
            reference_id=lead.id,
            notes=(
                f'Direct team lead referral — lead #{lead.id} ({lead_name}) '
                f'submitted by direct team member {producer.partner_code} ({producer.partner_name})'
            ),
            created_by=None,
        )

        lead.direct_team_lead_points_awarded = True
        lead.direct_team_lead_points_awarded_at = now
        lead.direct_team_lead_sponsor_id = sponsor.id
        db.flush()

        logger.info(
            f'[VGK-TEAM-LEAD-POINTS] +2,000 V2 points awarded to sponsor {sponsor.partner_code} '
            f'(id={sponsor.id}) for lead #{lead.id} produced by {producer.partner_code} (id={producer.id})'
        )

        return {
            'success': True,
            'awarded': True,
            'points': float(DIRECT_TEAM_LEAD_POINTS),
            'sponsor_id': sponsor.id,
            'sponsor_code': sponsor.partner_code,
            'producer_id': producer.id,
            'producer_code': producer.partner_code,
            'lead_id': lead.id,
            'ledger_entry_id': pts_entry.id,
            'sponsor_balance_after': float(pts_entry.balance_after),
        }
    except Exception as exc:
        logger.warning(f'[VGK-TEAM-LEAD-POINTS] Award failed for lead #{lead_id}: {exc}')
        return {'success': False, 'error': str(exc)}


def reverse_direct_team_lead_points(db: Session, lead_id: int, reason: str = 'Lead cancelled/deleted') -> dict:
    """
    Reverses the +2,000 V2 points previously awarded for a direct team lead.
    If available balance is insufficient (already used for payout capacity),
    offsets available points down to 0 and records the rest as points_recovery_liability.
    Partner points balance never becomes negative.
    """
    lead = db.query(CRMLead).filter(CRMLead.id == lead_id).first()
    if not lead:
        return {'success': False, 'error': f'Lead #{lead_id} not found'}

    # 1. Locate existing points award entry
    pts_entry = db.query(VGKPointsLedger).filter(
        VGKPointsLedger.reference_type == 'CRM_LEAD',
        VGKPointsLedger.reference_id == lead_id,
        VGKPointsLedger.reason_code == 'DIRECT_TEAM_LEAD_V2',
    ).first()

    if not pts_entry:
        return {
            'success': True,
            'skipped': True,
            'reason': 'No direct team lead points were awarded for this lead',
            'lead_id': lead_id,
        }

    # 2. Check if already reversed
    rev_entry = db.query(VGKPointsLedger).filter(
        VGKPointsLedger.reference_type == 'CRM_LEAD',
        VGKPointsLedger.reference_id == lead_id,
        VGKPointsLedger.reason_code == 'DIRECT_TEAM_LEAD_REVERSAL_V2',
    ).first()
    if rev_entry:
        lead.direct_team_lead_points_awarded = False
        return {
            'success': True,
            'skipped': True,
            'reason': 'Points already reversed for this lead',
            'lead_id': lead_id,
            'reversal_entry_id': rev_entry.id,
        }

    # 3. Lock sponsor for balance adjustment
    sponsor = db.query(OfficialPartner).filter(
        OfficialPartner.id == pts_entry.partner_id
    ).with_for_update().first()

    if not sponsor:
        return {'success': False, 'error': f'Sponsor #{pts_entry.partner_id} not found'}

    avail_pts = sponsor.vgk_points_balance or Decimal('0')
    points_to_debit = min(avail_pts, DIRECT_TEAM_LEAD_POINTS)
    unrecovered = DIRECT_TEAM_LEAD_POINTS - points_to_debit
    ledger_entry_id = None

    from app.services.vgk_commission import add_vgk_points_entry

    if points_to_debit > Decimal('0'):
        rev = add_vgk_points_entry(
            db=db,
            partner_id=sponsor.id,
            points_credit=Decimal('0'),
            points_debit=points_to_debit,
            reason_code='DIRECT_TEAM_LEAD_REVERSAL_V2',
            reference_type='CRM_LEAD',
            reference_id=lead.id,
            notes=(
                f'Reversal of direct team lead referral points — lead #{lead.id} ({reason})'
            ),
        )
        ledger_entry_id = rev.id

    if unrecovered > Decimal('0'):
        current_liability = Decimal(str(sponsor.points_recovery_liability or 0))
        sponsor.points_recovery_liability = current_liability + unrecovered

    lead.direct_team_lead_points_awarded = False
    lead.direct_team_lead_points_awarded_at = None
    db.flush()

    logger.info(
        f'[VGK-TEAM-LEAD-REVERSAL] Lead #{lead.id} reversed for sponsor #{sponsor.id}: '
        f'debited={float(points_to_debit)}, unrecovered_liability={float(unrecovered)}'
    )

    return {
        'success': True,
        'reversed': True,
        'points_debited': float(points_to_debit),
        'unrecovered_liability': float(unrecovered),
        'sponsor_id': sponsor.id,
        'lead_id': lead.id,
        'reversal_entry_id': ledger_entry_id,
    }
