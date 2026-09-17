"""
VGK4U Universal Commission Waterfall Engine
Created: 2026-09-12
Scope: Authoritative calculation engine for VGK4U Differential Commissions across all categories.

Architectural Invariants Enforced:
1. MAX NETWORK POOL CEILING: Total network commissions (Producer + Differentials) NEVER exceed the configured pool (e.g. 9.0% for Solar).
2. DIFFERENTIAL ABSORPTION: Higher producer rates (via Career rank or Personal Production) absorb the corresponding differential layers.
3. PERSONAL PRODUCTION ISOLATION: High personal production elevates personal producer economics, but does NOT grant downline team overrides.
4. OUT-OF-POOL INDEPENDENCE: Support (0.75%/1.50%) and Showroom (3.50%) are strictly operational layers outside the network pool.
5. IMMUTABILITY & IDEMPOTENCY: Safely previewable in simulation mode, idempotent when writing drafts to vgk_cash_income_entries.
"""

import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.staff_accounts import OfficialPartner
from app.models.vgk4u_models import VGK4UCategoryCommissionConfig
from app.services.vgk4u_career_service import (
    VGK4UCareerService,
    DESIGNATION_MEMBER,
    DESIGNATION_CHANNEL_PARTNER,
    DESIGNATION_MANAGER,
    DESIGNATION_GENERAL_MANAGER,
    DESIGNATION_REGIONAL_MANAGER,
    DESIGNATION_APEX_NODE,
    PROD_QUAL_NONE,
    PROD_QUAL_BASE,
    PROD_QUAL_GM,
    PROD_QUAL_RM,
    ROOT_APEX_PARTNER_ID,
    ROOT_APEX_PARTNER_CODE,
)

logger = logging.getLogger(__name__)

# Default Constants
DEFAULT_VERSION = 'v2_sep2026'
ADMIN_CHARGE_PCT = Decimal('8.00')
TDS_PCT = Decimal('2.00')


class VGK4UWaterfallEngine:
    """
    Authoritative Differential Waterfall Calculation Engine for VGK4U.
    """

    @classmethod
    def get_category_config(
        cls, db: Session, category_slug: str, version_label: str = DEFAULT_VERSION
    ) -> Optional[VGK4UCategoryCommissionConfig]:
        """
        Fetch active category commission configuration.
        """
        slug = (category_slug or 'solar').strip().lower()
        cfg = db.query(VGK4UCategoryCommissionConfig).filter(
            VGK4UCategoryCommissionConfig.category_slug == slug,
            VGK4UCategoryCommissionConfig.version_label == version_label,
            VGK4UCategoryCommissionConfig.is_active == True,
        ).first()

        if not cfg:
            # Fallback to solar if unknown
            cfg = db.query(VGK4UCategoryCommissionConfig).filter(
                VGK4UCategoryCommissionConfig.category_slug == 'solar',
                VGK4UCategoryCommissionConfig.is_active == True,
            ).first()
        return cfg

    @classmethod
    def compute_deductions(cls, gross_amount: Decimal) -> Dict[str, Decimal]:
        """
        Compute standard statutory and platform deductions:
        Gross Amount
        - 8.00% Admin Charges
        = Payable Amount
        - 2.00% TDS (on payable amount)
        = Net Payout Amount
        """
        gross = Decimal(str(gross_amount or 0)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        if gross <= 0:
            return {'gross': Decimal('0.00'), 'admin': Decimal('0.00'), 'tds': Decimal('0.00'), 'net': Decimal('0.00')}

        admin = (gross * (ADMIN_CHARGE_PCT / Decimal('100'))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        payable = gross - admin
        tds = (payable * (TDS_PCT / Decimal('100'))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        net = payable - tds
        return {'gross': gross, 'admin': admin, 'tds': tds, 'net': net}

    @classmethod
    def calculate_commission_structure(
        cls,
        db: Session,
        producer_partner_id: int,
        deal_value: Decimal,
        category_slug: str = 'solar',
        direct_sponsor_id: Optional[int] = None,
        support_partner_id: Optional[int] = None,
        support_journey_count: int = 0,
        is_end_to_end_support: bool = False,
        is_staff_involved: bool = False,
        showroom_partner_id: Optional[int] = None,
        version_label: str = DEFAULT_VERSION,
    ) -> Dict[str, Any]:
        """
        Core mathematical calculation of the VGK4U Differential Waterfall.
        Guarantees:
        1. Total network pool <= max_network_pool_pct
        2. Exact differential absorption
        3. Clear separation of producer, upline overrides, support, and showroom
        """
        cfg = cls.get_category_config(db, category_slug, version_label)
        if not cfg:
            raise ValueError(f'Configuration not found for category {category_slug} version {version_label}')

        deal_val = Decimal(str(deal_value or 0)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        if deal_val <= 0:
            return {'success': False, 'error': 'Deal value must be greater than 0', 'allocations': []}

        # 1. Resolve Producer Career & Qualification Status
        career_status_map = VGK4UCareerService.get_bulk_partner_career_status(db)
        producer_status = career_status_map.get(producer_partner_id)
        if not producer_status:
            return {'success': False, 'error': f'Producer partner {producer_partner_id} not found in VGK_TEAM'}

        producer_career = producer_status['career_designation']
        producer_prod_qual = producer_status['personal_prod_qualification']
        is_apex_producer = producer_status['is_apex_node']
        is_producer_active = producer_status.get('is_active', False) is True

        # 2. Determine Producer Personal Sales Rate
        base_rate = Decimal(str(cfg.producer_base_pct))
        mgr_diff_rate = Decimal(str(cfg.manager_diff_pct))
        gm_diff_rate = Decimal(str(cfg.gm_diff_pct))
        rm_diff_rate = Decimal(str(cfg.rm_diff_pct))
        sponsor_rate_cfg = Decimal(str(getattr(cfg, 'sponsor_override_pct', Decimal('0.00')) or Decimal('0.00')))
        max_network_pool = Decimal(str(cfg.max_network_pool_pct))


        # Career tier base rates
        career_rates = {
            DESIGNATION_MEMBER: Decimal('0.00'),
            DESIGNATION_CHANNEL_PARTNER: base_rate,
            DESIGNATION_MANAGER: base_rate + mgr_diff_rate,
            DESIGNATION_GENERAL_MANAGER: base_rate + mgr_diff_rate + gm_diff_rate,
            DESIGNATION_REGIONAL_MANAGER: base_rate + mgr_diff_rate + gm_diff_rate + rm_diff_rate,
            DESIGNATION_APEX_NODE: max_network_pool,
        }

        # Personal production tier rates
        prod_rates = {
            PROD_QUAL_NONE: Decimal('0.00'),
            PROD_QUAL_BASE: base_rate,
            PROD_QUAL_GM: base_rate + mgr_diff_rate + gm_diff_rate,
            'GM_QUALIFIED': base_rate + mgr_diff_rate + gm_diff_rate,
            PROD_QUAL_RM: base_rate + mgr_diff_rate + gm_diff_rate + rm_diff_rate,
            'RM_QUALIFIED': base_rate + mgr_diff_rate + gm_diff_rate + rm_diff_rate,
        }

        if is_apex_producer:
            effective_producer_pct = max_network_pool
        else:
            # Pure Model: Personal sales commission is flat base_rate (5.00%)
            # (+ 1.00% Brand Allowance disbursed separately).
            # Higher designations earn team overrides on downline sales, not higher self rates.
            effective_producer_pct = base_rate

        # 3. Build Network Allocations
        allocations: List[Dict[str, Any]] = []

        # A. Producer Allocation
        producer_gross = (deal_val * (effective_producer_pct / Decimal('100'))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        prod_deductions = cls.compute_deductions(producer_gross)

        allocations.append({
            'role': 'PRODUCER',
            'level': 1,
            'partner_id': producer_partner_id,
            'partner_code': producer_status['partner_code'],
            'partner_name': producer_status['partner_name'],
            'career_designation': producer_career,
            'personal_prod_qualification': producer_prod_qual,
            'commission_pct': effective_producer_pct,
            'commission_amount': producer_gross,
            'admin_charges': prod_deductions['admin'],
            'tds_amount': prod_deductions['tds'],
            'net_payout': prod_deductions['net'],
            'is_differential': False,
            'notes': f'Producer Personal Sales Commission ({effective_producer_pct}%)'
        })

        # 4. Dynamic Roll-Up Team Leadership Overrides (3.00% Pool)
        remaining_differential_pool = max_network_pool - effective_producer_pct
        current_tier_rate = effective_producer_pct

        # Rates per tier:
        # Senior: sponsor_rate_cfg (1.50%)
        # Extended: mgr_diff_rate (1.00%)
        # Core: gm_diff_rate (0.50%)
        senior_rate = sponsor_rate_cfg if sponsor_rate_cfg > Decimal('0.00') else Decimal('1.50')
        extended_rate = mgr_diff_rate if mgr_diff_rate > Decimal('0.00') else Decimal('1.00')
        core_rate = gm_diff_rate if gm_diff_rate > Decimal('0.00') else Decimal('0.50')

        senior_allocated = False
        extended_allocated = False
        core_allocated = False

        # If producer absorbed any tiers (e.g. higher producer rate):
        if effective_producer_pct >= (base_rate + senior_rate):
            senior_allocated = True
        if effective_producer_pct >= (base_rate + senior_rate + extended_rate):
            extended_allocated = True
        if effective_producer_pct >= max_network_pool:
            core_allocated = True

        def _get_rank_order(career_desig: Optional[str], is_apex: bool = False) -> int:
            if is_apex:
                return 4
            desig = (career_desig or '').strip().lower()
            if any(k in desig for k in ('core', 'regional manager', 'apex', 'director')):
                return 4
            if any(k in desig for k in ('extended', 'general manager', 'zonal')):
                return 3
            if any(k in desig for k in ('senior', 'manager')):
                return 2
            if 'channel partner' in desig:
                return 1
            return 0

        # Traverse upline chain starting with direct sponsor
        resolved_sponsor_id = direct_sponsor_id or producer_status.get('parent_partner_id')
        curr_partner_id = resolved_sponsor_id
        visited_parents = {producer_partner_id}

        while curr_partner_id and remaining_differential_pool > Decimal('0.00') and not (senior_allocated and extended_allocated and core_allocated):
            if curr_partner_id in visited_parents:
                logger.warning(f'Cycle detected in unilevel tree at partner {curr_partner_id}')
                break
            visited_parents.add(curr_partner_id)

            p_info = career_status_map.get(curr_partner_id)
            if not p_info:
                break

            p_career = p_info.get('career_designation')
            p_is_apex = p_info.get('is_apex_node', False) or (curr_partner_id == ROOT_APEX_PARTNER_ID)
            p_rank = _get_rank_order(p_career, p_is_apex)

            claimed_pct = Decimal('0.00')
            notes_parts = []

            # 1. Senior Override (1.50%)
            if p_rank >= 2 and not senior_allocated:
                claimed_pct += senior_rate
                senior_allocated = True
                notes_parts.append(f'Senior Override (+{senior_rate}%)')

            # 2. Extended Override (1.00%)
            if p_rank >= 3 and not extended_allocated:
                claimed_pct += extended_rate
                extended_allocated = True
                notes_parts.append(f'Extended Differential (+{extended_rate}%)')

            # 3. Core Override (0.50%)
            if p_rank >= 4 and not core_allocated:
                claimed_pct += core_rate
                core_allocated = True
                notes_parts.append(f'Core Differential (+{core_rate}%)')

            if claimed_pct > Decimal('0.00'):
                alloc_pct = min(claimed_pct, remaining_differential_pool)
                if alloc_pct > Decimal('0.00'):
                    alloc_gross = (deal_val * (alloc_pct / Decimal('100'))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    ded = cls.compute_deductions(alloc_gross)

                    is_direct_sponsor = (curr_partner_id == resolved_sponsor_id)
                    if is_direct_sponsor:
                        role_name = 'DIRECT_SPONSOR_OVERRIDE'
                        level_num = 2
                    elif p_rank >= 4:
                        role_name = 'RM_DIFFERENTIAL'
                        level_num = 4
                    elif p_rank >= 3:
                        role_name = 'GM_DIFFERENTIAL'
                        level_num = 3
                    else:
                        role_name = 'MANAGER_DIFFERENTIAL'
                        level_num = 2

                    allocations.append({
                        'role': role_name,
                        'level': level_num,
                        'partner_id': curr_partner_id,
                        'partner_code': p_info['partner_code'],
                        'partner_name': p_info['partner_name'],
                        'career_designation': p_career,
                        'personal_prod_qualification': p_info['personal_prod_qualification'],
                        'commission_pct': alloc_pct,
                        'commission_amount': alloc_gross,
                        'admin_charges': ded['admin'],
                        'tds_amount': ded['tds'],
                        'net_payout': ded['net'],
                        'is_differential': True,
                        'notes': f"{', '.join(notes_parts)} (Total: +{alloc_pct}%)"
                    })
                    remaining_differential_pool -= alloc_pct
                    current_tier_rate += alloc_pct

            curr_partner_id = p_info.get('parent_partner_id')

        # D. Apex Remainder Absorption
        field_roles = ('PRODUCER', 'DIRECT_SPONSOR_OVERRIDE', 'MANAGER_DIFFERENTIAL', 'GM_DIFFERENTIAL', 'RM_DIFFERENTIAL')
        total_field_network_pct = sum(a['commission_pct'] for a in allocations if a['role'] in field_roles)
        apex_remainder_pct = max_network_pool - total_field_network_pct

        if apex_remainder_pct > Decimal('0.00'):
            apex_gross = (deal_val * (apex_remainder_pct / Decimal('100'))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            apex_info = career_status_map.get(ROOT_APEX_PARTNER_ID, {
                'partner_code': ROOT_APEX_PARTNER_CODE,
                'partner_name': 'VGK Support',
                'career_designation': DESIGNATION_APEX_NODE,
                'personal_prod_qualification': None,
            })
            allocations.append({
                'role': 'APEX_REMAINDER',
                'level': 0,
                'partner_id': ROOT_APEX_PARTNER_ID,
                'partner_code': apex_info.get('partner_code', ROOT_APEX_PARTNER_CODE),
                'partner_name': apex_info.get('partner_name', 'VGK Support'),
                'career_designation': apex_info.get('career_designation', DESIGNATION_APEX_NODE),
                'personal_prod_qualification': apex_info.get('personal_prod_qualification', None),
                'commission_pct': apex_remainder_pct,
                'commission_amount': apex_gross,
                'admin_charges': Decimal('0.00'),
                'tds_amount': Decimal('0.00'),
                'net_payout': apex_gross,
                'is_differential': False,
                'notes': f'Apex Corporate Remainder ({apex_remainder_pct}%)'
            })

        # 5. Operational Field Support (Outside Network Pool)
        support_pct = Decimal('0.00')
        full_support_pct = Decimal('0.00')

        if support_partner_id and support_partner_id in career_status_map:
            sup_info = career_status_map[support_partner_id]
            is_self_support = (support_partner_id == producer_partner_id)

            # Base support (+0.75%)
            support_pct = Decimal(str(cfg.support_journey_pct))

            # Full support (+0.75%) only when is_end_to_end_support and NOT is_staff_involved
            if is_end_to_end_support and not is_staff_involved:
                full_support_pct = Decimal(str(cfg.support_end_to_end_pct)) - support_pct
            else:
                full_support_pct = Decimal('0.00')

            if support_pct > Decimal('0.00'):
                sup_gross = (deal_val * (support_pct / Decimal('100'))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                sup_ded = cls.compute_deductions(sup_gross)
                allocations.append({
                    'role': 'FIELD_SUPPORT',
                    'level': 5,
                    'partner_id': support_partner_id,
                    'partner_code': sup_info['partner_code'],
                    'partner_name': sup_info['partner_name'],
                    'career_designation': sup_info['career_designation'],
                    'personal_prod_qualification': sup_info['personal_prod_qualification'],
                    'commission_pct': support_pct,
                    'commission_amount': sup_gross,
                    'admin_charges': sup_ded['admin'],
                    'tds_amount': sup_ded['tds'],
                    'net_payout': sup_ded['net'],
                    'is_differential': False,
                    'notes': f'{"Direct " if is_self_support else "Field "}Support Fee ({support_pct}% outside network pool)'
                })

            if full_support_pct > Decimal('0.00'):
                full_gross = (deal_val * (full_support_pct / Decimal('100'))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                full_ded = cls.compute_deductions(full_gross)
                allocations.append({
                    'role': 'FULL_SUPPORT',
                    'level': 7,
                    'partner_id': support_partner_id,
                    'partner_code': sup_info['partner_code'],
                    'partner_name': sup_info['partner_name'],
                    'career_designation': sup_info['career_designation'],
                    'personal_prod_qualification': sup_info['personal_prod_qualification'],
                    'commission_pct': full_support_pct,
                    'commission_amount': full_gross,
                    'admin_charges': full_ded['admin'],
                    'tds_amount': full_ded['tds'],
                    'net_payout': full_ded['net'],
                    'is_differential': False,
                    'notes': f'{"Direct Full-Service Closing Incentive" if is_self_support else "Full Closing Incentive"} ({full_support_pct}% outside network pool)'
                })

        # 6. Showroom Override (Outside Network Pool)
        if showroom_partner_id and showroom_partner_id in career_status_map:
            if showroom_partner_id not in (producer_partner_id, support_partner_id):
                sh_info = career_status_map[showroom_partner_id]
                sh_pct = Decimal(str(cfg.showroom_pct))
                if sh_pct > Decimal('0.00'):
                    sh_gross = (deal_val * (sh_pct / Decimal('100'))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    sh_ded = cls.compute_deductions(sh_gross)
                    allocations.append({
                        'role': 'SHOWROOM',
                        'level': 6,
                        'partner_id': showroom_partner_id,
                        'partner_code': sh_info['partner_code'],
                        'partner_name': sh_info['partner_name'],
                        'career_designation': sh_info['career_designation'],
                        'personal_prod_qualification': sh_info['personal_prod_qualification'],
                        'commission_pct': sh_pct,
                        'commission_amount': sh_gross,
                        'admin_charges': sh_ded['admin'],
                        'tds_amount': sh_ded['tds'],
                        'net_payout': sh_ded['net'],
                        'is_differential': False,
                        'notes': f'Showroom Override Fee ({sh_pct}% outside network pool)'
                    })

        # Network Pool Invariant Assertion
        network_roles = ('PRODUCER', 'DIRECT_SPONSOR_OVERRIDE', 'MANAGER_DIFFERENTIAL', 'GM_DIFFERENTIAL', 'RM_DIFFERENTIAL', 'APEX_REMAINDER')
        total_network_pct = sum(a['commission_pct'] for a in allocations if a['role'] in network_roles)
        total_network_gross = sum(a['commission_amount'] for a in allocations if a['role'] in network_roles)

        assert total_network_pct <= max_network_pool, f'CRITICAL: Network pool {total_network_pct}% exceeded max {max_network_pool}%'

        return {
            'success': True,
            'deal_value': deal_val,
            'category_slug': category_slug,
            'version_label': version_label,
            'max_network_pool_pct': max_network_pool,
            'total_network_pct': total_network_pct,
            'total_network_gross': total_network_gross,
            'producer_rate_pct': effective_producer_pct,
            'support_pct': support_pct,
            'full_support_pct': full_support_pct,
            'total_support_pct': support_pct + full_support_pct,
            'is_staff_involved': is_staff_involved,
            'allocations': allocations,
        }
