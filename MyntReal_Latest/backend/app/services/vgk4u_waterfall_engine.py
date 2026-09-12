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

        # Inactive/Suspended Producer Gate (VGK4U Phase 3E.2):
        if not is_producer_active:
            apex_gross = (deal_val * (max_network_pool / Decimal('100'))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            apex_info = career_status_map.get(ROOT_APEX_PARTNER_ID, {
                'partner_code': ROOT_APEX_PARTNER_CODE,
                'partner_name': 'VGK Support',
                'career_designation': DESIGNATION_APEX_NODE,
                'personal_prod_qualification': None,
            })
            allocations = [
                {
                    'role': 'PRODUCER',
                    'level': 1,
                    'partner_id': producer_partner_id,
                    'partner_code': producer_status['partner_code'],
                    'partner_name': producer_status['partner_name'],
                    'career_designation': producer_career,
                    'personal_prod_qualification': producer_prod_qual,
                    'commission_pct': Decimal('0.00'),
                    'commission_amount': Decimal('0.00'),
                    'admin_charges': Decimal('0.00'),
                    'tds_amount': Decimal('0.00'),
                    'net_payout': Decimal('0.00'),
                    'is_differential': False,
                    'notes': 'Producer Inactive/Suspended - Personal Commission Forfeited (0.00%)'
                },
                {
                    'role': 'APEX_REMAINDER',
                    'level': 0,
                    'partner_id': ROOT_APEX_PARTNER_ID,
                    'partner_code': apex_info.get('partner_code', ROOT_APEX_PARTNER_CODE),
                    'partner_name': apex_info.get('partner_name', 'VGK Support'),
                    'career_designation': apex_info.get('career_designation', DESIGNATION_APEX_NODE),
                    'personal_prod_qualification': apex_info.get('personal_prod_qualification', None),
                    'commission_pct': max_network_pool,
                    'commission_amount': apex_gross,
                    'admin_charges': Decimal('0.00'),
                    'tds_amount': Decimal('0.00'),
                    'net_payout': apex_gross,
                    'is_differential': False,
                    'notes': f'Apex Corporate Remainder (Inactive Producer Forfeiture {max_network_pool}%)'
                }
            ]

            # Operational Field Support & Showroom are outside network pool:
            if support_partner_id and support_partner_id in career_status_map:
                sup_info = career_status_map[support_partner_id]
                if is_end_to_end_support:
                    sup_pct = Decimal(str(cfg.support_end_to_end_pct))
                elif support_journey_count >= 2:
                    sup_pct = Decimal(str(cfg.support_journey_pct))
                else:
                    sup_pct = Decimal('0.00')

                if sup_pct > Decimal('0.00'):
                    sup_gross = (deal_val * (sup_pct / Decimal('100'))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    sup_ded = cls.compute_deductions(sup_gross)
                    allocations.append({
                        'role': 'FIELD_SUPPORT',
                        'level': 5,
                        'partner_id': support_partner_id,
                        'partner_code': sup_info['partner_code'],
                        'partner_name': sup_info['partner_name'],
                        'career_designation': sup_info['career_designation'],
                        'personal_prod_qualification': sup_info['personal_prod_qualification'],
                        'commission_pct': sup_pct,
                        'commission_amount': sup_gross,
                        'admin_charges': sup_ded['admin'],
                        'tds_amount': sup_ded['tds'],
                        'net_payout': sup_ded['net'],
                        'is_differential': False,
                        'notes': f'Field Support Fee ({sup_pct}% outside network pool)'
                    })

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

            return {
                'success': True,
                'deal_value': deal_val,
                'category_slug': category_slug,
                'version_label': version_label,
                'max_network_pool_pct': max_network_pool,
                'total_network_pct': max_network_pool,
                'total_network_gross': apex_gross,
                'producer_rate_pct': Decimal('0.00'),
                'allocations': allocations,
            }


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
        elif producer_status['own_qualifying_files'] == 0:
            # Rule: 1st personal file qualifies at base rate (6.0% for Solar) upon closing
            effective_producer_pct = base_rate
        else:
            effective_producer_pct = max(
                career_rates.get(producer_career, base_rate),
                prod_rates.get(producer_prod_qual, base_rate),
            )

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

        # 4. Differential Waterfall with Model A Direct Sponsor Carve-Out
        # Available differential headroom
        remaining_differential_pool = max_network_pool - effective_producer_pct
        current_tier_rate = effective_producer_pct

        # Track tier absorption by producer
        manager_layer_absorbed = (effective_producer_pct >= (base_rate + mgr_diff_rate))
        gm_absorbed = (effective_producer_pct >= (base_rate + mgr_diff_rate + gm_diff_rate))
        rm_absorbed = (effective_producer_pct >= max_network_pool)

        manager_allocated = manager_layer_absorbed
        gm_allocated = gm_absorbed
        rm_allocated = rm_absorbed

        # A. Resolve Direct Sponsor: Lead override takes precedence over natural parent
        resolved_sponsor_id = direct_sponsor_id or producer_status.get('parent_partner_id')
        sponsor_info = career_status_map.get(resolved_sponsor_id) if resolved_sponsor_id else None

        is_sponsor_valid = (
            sponsor_info is not None and
            resolved_sponsor_id != producer_partner_id and
            sponsor_info.get('is_active', False) is True
        )

        sponsor_visited = set()
        if resolved_sponsor_id:
            sponsor_visited.add(resolved_sponsor_id)

        # B. Allocate Direct Sponsor from Manager Tier
        if not manager_layer_absorbed and remaining_differential_pool > Decimal('0.00'):
            if is_sponsor_valid:
                sponsor_career = sponsor_info['career_designation']
                if sponsor_career == DESIGNATION_REGIONAL_MANAGER:
                    # Case D: RM sponsor absorbs Manager (1.5%) + GM (1.0%) + RM (0.5%) = 3.0%
                    alloc_pct = min(mgr_diff_rate + gm_diff_rate + rm_diff_rate, remaining_differential_pool)
                    alloc_gross = (deal_val * (alloc_pct / Decimal('100'))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    ded = cls.compute_deductions(alloc_gross)
                    allocations.append({
                        'role': 'DIRECT_SPONSOR_OVERRIDE',
                        'level': 2,
                        'partner_id': resolved_sponsor_id,
                        'partner_code': sponsor_info['partner_code'],
                        'partner_name': sponsor_info['partner_name'],
                        'career_designation': sponsor_career,
                        'personal_prod_qualification': sponsor_info['personal_prod_qualification'],
                        'commission_pct': alloc_pct,
                        'commission_amount': alloc_gross,
                        'admin_charges': ded['admin'],
                        'tds_amount': ded['tds'],
                        'net_payout': ded['net'],
                        'is_differential': True,
                        'notes': f'Direct Sponsor Override (RM Absorbs All Differentials: +{alloc_pct}%)'
                    })
                    manager_allocated = True
                    gm_allocated = True
                    rm_allocated = True
                    remaining_differential_pool -= alloc_pct
                    current_tier_rate += alloc_pct
                elif sponsor_career == DESIGNATION_GENERAL_MANAGER:
                    # Case C: GM sponsor absorbs Manager (1.5%) + GM (1.0%) = 2.5%
                    alloc_pct = min(mgr_diff_rate + gm_diff_rate, remaining_differential_pool)
                    alloc_gross = (deal_val * (alloc_pct / Decimal('100'))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    ded = cls.compute_deductions(alloc_gross)
                    allocations.append({
                        'role': 'DIRECT_SPONSOR_OVERRIDE',
                        'level': 2,
                        'partner_id': resolved_sponsor_id,
                        'partner_code': sponsor_info['partner_code'],
                        'partner_name': sponsor_info['partner_name'],
                        'career_designation': sponsor_career,
                        'personal_prod_qualification': sponsor_info['personal_prod_qualification'],
                        'commission_pct': alloc_pct,
                        'commission_amount': alloc_gross,
                        'admin_charges': ded['admin'],
                        'tds_amount': ded['tds'],
                        'net_payout': ded['net'],
                        'is_differential': True,
                        'notes': f'Direct Sponsor Override (GM Absorbs Manager+GM: +{alloc_pct}%)'
                    })
                    manager_allocated = True
                    gm_allocated = True
                    remaining_differential_pool -= alloc_pct
                    current_tier_rate += alloc_pct
                elif sponsor_career in (DESIGNATION_MANAGER, DESIGNATION_APEX_NODE):
                    # Case B: Manager sponsor absorbs full Manager layer (1.5%)
                    alloc_pct = min(mgr_diff_rate, remaining_differential_pool)
                    alloc_gross = (deal_val * (alloc_pct / Decimal('100'))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    ded = cls.compute_deductions(alloc_gross)
                    allocations.append({
                        'role': 'DIRECT_SPONSOR_OVERRIDE',
                        'level': 2,
                        'partner_id': resolved_sponsor_id,
                        'partner_code': sponsor_info['partner_code'],
                        'partner_name': sponsor_info['partner_name'],
                        'career_designation': sponsor_career,
                        'personal_prod_qualification': sponsor_info['personal_prod_qualification'],
                        'commission_pct': alloc_pct,
                        'commission_amount': alloc_gross,
                        'admin_charges': ded['admin'],
                        'tds_amount': ded['tds'],
                        'net_payout': ded['net'],
                        'is_differential': True,
                        'notes': f'Direct Sponsor Override (Manager Absorbs Full Tier: +{alloc_pct}%)'
                    })
                    manager_allocated = True
                    remaining_differential_pool -= alloc_pct
                    current_tier_rate += alloc_pct
                else:
                    # Case A: Member or Channel Partner sponsor receives sponsor_override_pct (1.00%)
                    if sponsor_rate_cfg > Decimal('0.00'):
                        alloc_pct = min(sponsor_rate_cfg, remaining_differential_pool)
                        alloc_gross = (deal_val * (alloc_pct / Decimal('100'))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                        ded = cls.compute_deductions(alloc_gross)
                        allocations.append({
                            'role': 'DIRECT_SPONSOR_OVERRIDE',
                            'level': 2,
                            'partner_id': resolved_sponsor_id,
                            'partner_code': sponsor_info['partner_code'],
                            'partner_name': sponsor_info['partner_name'],
                            'career_designation': sponsor_career,
                            'personal_prod_qualification': sponsor_info['personal_prod_qualification'],
                            'commission_pct': alloc_pct,
                            'commission_amount': alloc_gross,
                            'admin_charges': ded['admin'],
                            'tds_amount': ded['tds'],
                            'net_payout': ded['net'],
                            'is_differential': False,
                            'notes': f'Direct Sponsor Override (+{alloc_pct}%)'
                        })
                        remaining_differential_pool -= alloc_pct
                        current_tier_rate += alloc_pct
            else:
                # Inactive / missing sponsor: sponsor receives 0%
                # Reserved sponsor_rate_cfg (1.00%) is retained by company for Apex Remainder
                # Do NOT compress upward to Manager!
                if sponsor_rate_cfg > Decimal('0.00'):
                    remaining_differential_pool -= min(sponsor_rate_cfg, remaining_differential_pool)

        # C. Upline Traversal for Residual Manager, GM, and RM Differentials
        curr_parent_id = sponsor_info.get('parent_partner_id') if sponsor_info else producer_status.get('parent_partner_id')
        visited_parents = set(sponsor_visited)

        while curr_parent_id and remaining_differential_pool > Decimal('0.00'):
            if curr_parent_id in visited_parents:
                logger.warning(f'Cycle detected in unilevel tree at partner {curr_parent_id}')
                break
            visited_parents.add(curr_parent_id)

            parent_info = career_status_map.get(curr_parent_id)
            if not parent_info:
                break

            parent_career = parent_info['career_designation']
            parent_is_active = parent_info.get('is_active', False) is True

            if not parent_is_active:
                curr_parent_id = parent_info.get('parent_partner_id')
                continue

            # 1. Residual Manager Differential
            if not manager_allocated and not manager_layer_absorbed:
                if parent_career in (DESIGNATION_MANAGER, DESIGNATION_GENERAL_MANAGER, DESIGNATION_REGIONAL_MANAGER, DESIGNATION_APEX_NODE):
                    # Residual Manager tier = mgr_diff_rate - sponsor_rate_cfg (e.g. 1.50% - 1.00% = 0.50%)
                    diff_pct = min(mgr_diff_rate - sponsor_rate_cfg, remaining_differential_pool)
                    if diff_pct > Decimal('0.00'):
                        diff_gross = (deal_val * (diff_pct / Decimal('100'))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                        ded = cls.compute_deductions(diff_gross)
                        allocations.append({
                            'role': 'MANAGER_DIFFERENTIAL',
                            'level': 2,
                            'partner_id': curr_parent_id,
                            'partner_code': parent_info['partner_code'],
                            'partner_name': parent_info['partner_name'],
                            'career_designation': parent_career,
                            'personal_prod_qualification': parent_info['personal_prod_qualification'],
                            'commission_pct': diff_pct,
                            'commission_amount': diff_gross,
                            'admin_charges': ded['admin'],
                            'tds_amount': ded['tds'],
                            'net_payout': ded['net'],
                            'is_differential': True,
                            'notes': f'Manager Differential Override (+{diff_pct}%)'
                        })
                        remaining_differential_pool -= diff_pct
                        current_tier_rate += diff_pct
                    manager_allocated = True

            # 2. GM Differential (+1.0%)
            elif not gm_allocated and not gm_absorbed and remaining_differential_pool > Decimal('0.00'):
                if parent_career in (DESIGNATION_GENERAL_MANAGER, DESIGNATION_REGIONAL_MANAGER, DESIGNATION_APEX_NODE):
                    diff_pct = min(gm_diff_rate, remaining_differential_pool)
                    if diff_pct > Decimal('0.00'):
                        diff_gross = (deal_val * (diff_pct / Decimal('100'))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                        ded = cls.compute_deductions(diff_gross)
                        allocations.append({
                            'role': 'GM_DIFFERENTIAL',
                            'level': 3,
                            'partner_id': curr_parent_id,
                            'partner_code': parent_info['partner_code'],
                            'partner_name': parent_info['partner_name'],
                            'career_designation': parent_career,
                            'personal_prod_qualification': parent_info['personal_prod_qualification'],
                            'commission_pct': diff_pct,
                            'commission_amount': diff_gross,
                            'admin_charges': ded['admin'],
                            'tds_amount': ded['tds'],
                            'net_payout': ded['net'],
                            'is_differential': True,
                            'notes': f'General Manager Differential Override (+{diff_pct}%)'
                        })
                        remaining_differential_pool -= diff_pct
                        current_tier_rate += diff_pct
                    gm_allocated = True

            # 3. RM Differential (+0.5%)
            elif not rm_allocated and not rm_absorbed and remaining_differential_pool > Decimal('0.00'):
                if parent_career in (DESIGNATION_REGIONAL_MANAGER, DESIGNATION_APEX_NODE):
                    diff_pct = min(rm_diff_rate, remaining_differential_pool)
                    if diff_pct > Decimal('0.00'):
                        diff_gross = (deal_val * (diff_pct / Decimal('100'))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                        ded = cls.compute_deductions(diff_gross)
                        allocations.append({
                            'role': 'RM_DIFFERENTIAL',
                            'level': 4,
                            'partner_id': curr_parent_id,
                            'partner_code': parent_info['partner_code'],
                            'partner_name': parent_info['partner_name'],
                            'career_designation': parent_career,
                            'personal_prod_qualification': parent_info['personal_prod_qualification'],
                            'commission_pct': diff_pct,
                            'commission_amount': diff_gross,
                            'admin_charges': ded['admin'],
                            'tds_amount': ded['tds'],
                            'net_payout': ded['net'],
                            'is_differential': True,
                            'notes': f'Regional Manager Differential Override (+{diff_pct}%)'
                        })
                        remaining_differential_pool -= diff_pct
                        current_tier_rate += diff_pct
                    rm_allocated = True

            curr_parent_id = parent_info.get('parent_partner_id')

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
        if support_partner_id and support_partner_id in career_status_map:
            sup_info = career_status_map[support_partner_id]
            # Semantic fix: end-to-end gets 1.50%; journey support (>= 2 visits) gets 0.75%; else 0.00%
            if is_end_to_end_support:
                sup_pct = Decimal(str(cfg.support_end_to_end_pct))
            elif support_journey_count >= 2:
                sup_pct = Decimal(str(cfg.support_journey_pct))
            else:
                sup_pct = Decimal('0.00')

            if sup_pct > Decimal('0.00'):
                sup_gross = (deal_val * (sup_pct / Decimal('100'))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                sup_ded = cls.compute_deductions(sup_gross)
                allocations.append({
                    'role': 'FIELD_SUPPORT',
                    'level': 5,
                    'partner_id': support_partner_id,
                    'partner_code': sup_info['partner_code'],
                    'partner_name': sup_info['partner_name'],
                    'career_designation': sup_info['career_designation'],
                    'personal_prod_qualification': sup_info['personal_prod_qualification'],
                    'commission_pct': sup_pct,
                    'commission_amount': sup_gross,
                    'admin_charges': sup_ded['admin'],
                    'tds_amount': sup_ded['tds'],
                    'net_payout': sup_ded['net'],
                    'is_differential': False,
                    'notes': f'Field Support Fee ({sup_pct}% outside network pool)'
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
            'allocations': allocations,
        }
