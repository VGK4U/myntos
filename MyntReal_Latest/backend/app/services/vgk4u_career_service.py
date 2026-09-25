"""
VGK4U Career & Personal Production Service
Created: 2026-09-12
Scope: Authoritative service to resolve VGK4U Career Designations, Active Team Legs,
       and Personal Production Commission Qualifications.

Approved Business Rules Enforced:
1. Option A: Strict Sequential Career Progression (Must close >= 1 personal file before advancing beyond Member).
2. Option B: Whole-subtree Unilevel Leg-Capping (Maximum 1 active partner counted per direct sponsorship leg).
3. Personal Production Qualification: Cumulative lifetime personal qualifying files (Base 1-4, GM 5-9, RM 10+).
4. Performance & Safety: Bounded iterative tree traversal protecting against cycles, corrupt parents, and N+1 query explosions.
"""

import logging
from typing import Dict, List, Optional, Any, Set
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)

# Canonical Career Designations
DESIGNATION_MEMBER = 'Member'
DESIGNATION_CHANNEL_PARTNER = 'Channel Partner'
DESIGNATION_SENIOR = 'Senior'
DESIGNATION_EXTENDED = 'Extended'
DESIGNATION_CORE = 'Core'
DESIGNATION_APEX_NODE = 'Company Apex Node'

# Backward-compatible aliases
DESIGNATION_MANAGER = 'Senior'
DESIGNATION_GENERAL_MANAGER = 'Extended'
DESIGNATION_REGIONAL_MANAGER = 'Core'

# Canonical Personal Production Qualifications
PROD_QUAL_NONE = 'None'
PROD_QUAL_BASE = 'Base'
PROD_QUAL_GM = 'GM Commission Qualified'
PROD_QUAL_EXT = 'Extended Commission Qualified'
PROD_QUAL_CORE = 'Core Commission Qualified'
PROD_QUAL_APEX = 'Apex Top Commission Qualified'
PROD_QUAL_RM = 'Core Commission Qualified'

# Corporate Master Root ID
ROOT_APEX_PARTNER_ID = 31
ROOT_APEX_PARTNER_CODE = 'VGK07102207'


class VGK4UCareerService:
    """
    Authoritative service for resolving VGK4U Career Designations and Personal Production Qualifications.
    """

    @staticmethod
    def is_lead_qualifying(lead_status: Optional[str], solar_pipeline_status: Optional[str]) -> bool:
        """
        Rule E: A lead qualifies if status == 'completed' OR solar_pipeline_status in ('subsidy_pending', 'completed').
        """
        st = (lead_status or '').strip().lower()
        sps = (solar_pipeline_status or '').strip().lower()
        return (st == 'completed') or (sps in ('subsidy_pending', 'completed'))

    @classmethod
    def get_bulk_partner_career_status(
        cls, db: Session, partner_ids: Optional[List[int]] = None
    ) -> Dict[int, Dict[str, Any]]:
        """
        High-performance bulk calculation of career status and personal production qualification
        for all or specified VGK_TEAM partners.
        Constructs the entire unilevel tree in memory in O(N) time with zero recursion stack overflow risk.
        """
        # 1. Fetch official partners
        query_partners = """
            SELECT id, partner_code, partner_name, parent_partner_id, is_active,
                   is_apex_node, vgk4u_current_designation, vgk4u_personal_prod_qualification
            FROM official_partners
            WHERE category = 'VGK_TEAM'
            ORDER BY id
        """
        partners_raw = db.execute(text(query_partners)).fetchall()
        partners_by_id = {r[0]: r for r in partners_raw}

        if not partners_by_id:
            return {}

        # 2. Fetch qualifying file counts per partner
        query_qual = """
            SELECT associated_partner_id, count(*) as file_count
            FROM crm_leads
            WHERE associated_partner_id IS NOT NULL
              AND (status = 'completed' OR solar_pipeline_status IN ('subsidy_pending', 'completed'))
            GROUP BY associated_partner_id
        """
        qual_raw = db.execute(text(query_qual)).fetchall()
        qual_file_map = {r[0]: r[1] for r in qual_raw}

        # 3. Build unilevel child map with cycle protection
        children_map = defaultdict(list)
        parent_map = {}
        for pid, p in partners_by_id.items():
            parent_id = p[3]
            # Valid parent must exist in VGK_TEAM and cannot be self
            if parent_id and parent_id in partners_by_id and parent_id != pid:
                parent_map[pid] = parent_id
                children_map[parent_id].append(pid)

        # 4. Identify active producers (personal files >= 1)
        is_active_producer = {
            pid: (qual_file_map.get(pid, 0) >= 1)
            for pid in partners_by_id
        }

        # 5. Pre-compute whether each node's subtree contains ANY active producer
        # Safe post-order or memoized iterative evaluation
        subtree_active_cache: Dict[int, bool] = {}

        def node_has_active_producer_in_subtree(start_node_id: int) -> bool:
            if start_node_id in subtree_active_cache:
                return subtree_active_cache[start_node_id]

            visited = set()
            stack = [start_node_id]
            has_active = False

            while stack:
                curr = stack.pop()
                if curr in visited:
                    continue
                visited.add(curr)

                if is_active_producer.get(curr, False):
                    has_active = True
                    break

                for child_id in children_map.get(curr, []):
                    if child_id not in visited:
                        stack.append(child_id)

            subtree_active_cache[start_node_id] = has_active
            return has_active

        # 6. Calculate active legs for each partner (Option B: 1 per direct sponsorship leg)
        active_legs_map: Dict[int, int] = {}
        active_leg_details_map: Dict[int, List[str]] = {}

        for pid in partners_by_id:
            direct_children = children_map.get(pid, [])
            active_legs = 0
            active_leg_roots = []
            for child_id in direct_children:
                if node_has_active_producer_in_subtree(child_id):
                    active_legs += 1
                    active_leg_roots.append(partners_by_id[child_id][1])
            active_legs_map[pid] = active_legs
            active_leg_details_map[pid] = active_leg_roots

        # 7. Evaluate Career Designation and Personal Production Qualification
        results: Dict[int, Dict[str, Any]] = {}

        for pid, p in partners_by_id.items():
            partner_code = p[1]
            partner_name = p[2]
            is_apex = (pid == ROOT_APEX_PARTNER_ID) or bool(p[5])
            own_files = qual_file_map.get(pid, 0)
            active_legs = active_legs_map[pid]

            # --- A. Career Designation (Organizational Leadership) ---
            # Dual criteria: Cumulative Personal Files AND Active Team Legs
            if is_apex:
                career_desig = DESIGNATION_APEX_NODE
            elif own_files == 0:
                career_desig = DESIGNATION_MEMBER
            elif own_files >= 16 and active_legs >= 10:
                career_desig = DESIGNATION_CORE
            elif own_files >= 10 and active_legs >= 5:
                career_desig = DESIGNATION_EXTENDED
            elif own_files >= 5 and active_legs >= 1:
                career_desig = DESIGNATION_SENIOR
            elif own_files >= 1:
                career_desig = DESIGNATION_CHANNEL_PARTNER
            else:
                career_desig = DESIGNATION_MEMBER

            # --- B. Personal Direct Sales Commission & Production Qualification ---
            if is_apex:
                prod_qual = None
                effective_personal_rate = 0.0  # Corporate entity; does not earn personal commissions
            elif own_files >= 1:
                prod_qual = PROD_QUAL_BASE
                effective_personal_rate = 5.00  # Pure Model: Flat 5.00% Personal Direct Sales Commission
            else:
                prod_qual = PROD_QUAL_NONE
                effective_personal_rate = 0.0  # Unlocks 5.00% upon closing 1st personal file

            # --- C. Leadership Team Differentials & Direct Sponsor Override ---
            if is_apex:
                team_diff_rate = 0.0
                cum_diff_rate = 0.0
                sponsor_rate = 0.0
            elif career_desig == DESIGNATION_CORE:
                team_diff_rate = 0.50
                cum_diff_rate = 3.00  # 1.50% (Senior) + 1.00% (Extended) + 0.50% (Core)
                sponsor_rate = 1.00
            elif career_desig == DESIGNATION_EXTENDED:
                team_diff_rate = 1.00
                cum_diff_rate = 2.50  # 1.50% (Senior) + 1.00% (Extended)
                sponsor_rate = 1.00
            elif career_desig == DESIGNATION_SENIOR:
                team_diff_rate = 1.50
                cum_diff_rate = 1.50  # 1.50% (Senior)
                sponsor_rate = 1.00
            elif career_desig == DESIGNATION_CHANNEL_PARTNER:
                team_diff_rate = 0.00
                cum_diff_rate = 0.00
                sponsor_rate = 1.00
            else:
                team_diff_rate = 0.00
                cum_diff_rate = 0.00
                sponsor_rate = 0.00

            # --- D. Next Career Milestone ---
            if is_apex:
                next_career = {'target_title': None, 'required_files': 0, 'current_files': 0, 'remaining_files': 0, 'required_legs': 0, 'current_legs': active_legs, 'remaining': 0, 'remaining_legs': 0}
            elif career_desig == DESIGNATION_MEMBER:
                next_career = {
                    'target_title': DESIGNATION_CHANNEL_PARTNER,
                    'required_files': 1,
                    'current_files': own_files,
                    'remaining': max(0, 1 - own_files),
                    'remaining_files': max(0, 1 - own_files),
                    'required_legs': 0,
                    'current_legs': active_legs,
                    'remaining_legs': 0
                }
            elif career_desig == DESIGNATION_CHANNEL_PARTNER:
                rem_files = max(0, 5 - own_files)
                rem_legs = max(0, 1 - active_legs)
                next_career = {
                    'target_title': DESIGNATION_SENIOR,
                    'required_files': 5,
                    'current_files': own_files,
                    'remaining': rem_files + rem_legs,
                    'remaining_files': rem_files,
                    'required_legs': 1,
                    'current_legs': active_legs,
                    'remaining_legs': rem_legs
                }
            elif career_desig == DESIGNATION_SENIOR:
                rem_files = max(0, 10 - own_files)
                rem_legs = max(0, 5 - active_legs)
                next_career = {
                    'target_title': DESIGNATION_EXTENDED,
                    'required_files': 10,
                    'current_files': own_files,
                    'remaining': rem_files + rem_legs,
                    'remaining_files': rem_files,
                    'required_legs': 5,
                    'current_legs': active_legs,
                    'remaining_legs': rem_legs
                }
            elif career_desig == DESIGNATION_EXTENDED:
                rem_files = max(0, 16 - own_files)
                rem_legs = max(0, 10 - active_legs)
                next_career = {
                    'target_title': DESIGNATION_CORE,
                    'required_files': 16,
                    'current_files': own_files,
                    'remaining': rem_files + rem_legs,
                    'remaining_files': rem_files,
                    'required_legs': 10,
                    'current_legs': active_legs,
                    'remaining_legs': rem_legs
                }
            else: # Core
                next_career = {
                    'target_title': 'Top Rank Achieved',
                    'required_files': 16,
                    'current_files': own_files,
                    'remaining': 0,
                    'remaining_files': 0,
                    'required_legs': 10,
                    'current_legs': active_legs,
                    'remaining_legs': 0
                }

            # --- E. Next Personal Production Milestone ---
            if is_apex:
                next_prod = {'target_tier': None, 'required_files': 0, 'current_files': own_files, 'remaining': 0}
            elif own_files >= 1:
                next_prod = {'target_tier': 'Personal Sales Commission (Flat 5.0%) Qualified', 'required_files': 1, 'current_files': own_files, 'remaining': 0}
            else:
                next_prod = {'target_tier': 'Active Channel Partner (5.0% Direct Commission)', 'required_files': 1, 'current_files': 0, 'remaining': 1}

            sponsor_name = ""
            sponsor_code = ""
            if p[3] and p[3] in partners_by_id:
                sponsor_name = partners_by_id[p[3]][2] or ""
                sponsor_code = partners_by_id[p[3]][1] or ""

            results[pid] = {
                'partner_id': pid,
                'partner_code': partner_code,
                'partner_name': partner_name,
                'parent_partner_id': p[3],
                'direct_sponsor_id': p[3],
                'direct_sponsor_name': sponsor_name,
                'direct_sponsor_code': sponsor_code,
                'is_active': bool(p[4]),
                'is_apex_node': is_apex,
                'own_qualifying_files': own_files,
                'active_team_legs': active_legs,
                'active_leg_roots': active_leg_details_map[pid],
                'career_designation': career_desig,
                'personal_prod_qualification': prod_qual,
                'effective_personal_producer_rate': effective_personal_rate,
                'team_differential_rate': team_diff_rate,
                'cumulative_differential_rate': cum_diff_rate,
                'sponsor_override_rate': sponsor_rate,
                'next_career_milestone': next_career,
                'next_personal_milestone': next_prod,
            }

        if partner_ids is not None:
            return {pid: results[pid] for pid in partner_ids if pid in results}
        return results

    @classmethod
    def get_partner_career_status(cls, db: Session, partner_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetch career status and personal production qualification for a single partner.
        """
        bulk_res = cls.get_bulk_partner_career_status(db, partner_ids=[partner_id])
        return bulk_res.get(partner_id)

    @classmethod
    def sync_partner_career_status_to_db(cls, db: Session, partner_id: int) -> Optional[Dict[str, Any]]:
        """
        Synchronize dynamic career status and qualification to official_partners read-cache columns
        for a single partner.
        """
        if not partner_id:
            return None
        res = cls.get_partner_career_status(db, partner_id)
        if not res:
            return None

        db.execute(text("""
            UPDATE official_partners
            SET vgk4u_current_designation = :desig,
                vgk4u_personal_prod_qualification = :prod_qual,
                vgk4u_own_qualifying_files = :files,
                vgk4u_active_team_count = :active_legs,
                vgk4u_designation_updated_at = NOW()
            WHERE id = :pid
        """), {
            'desig': res['career_designation'],
            'prod_qual': res['personal_prod_qualification'],
            'files': res['own_qualifying_files'],
            'active_legs': res['active_team_legs'],
            'pid': partner_id,
        })
        db.flush()
        return res

    @classmethod
    def sync_bulk_career_status_to_db(cls, db: Session, partner_ids: Optional[List[int]] = None) -> int:
        """
        Batch synchronize dynamic career status and qualification to official_partners
        for all or specified partners.
        """
        bulk_res = cls.get_bulk_partner_career_status(db, partner_ids=partner_ids)
        if not bulk_res:
            return 0

        for pid, res in bulk_res.items():
            db.execute(text("""
                UPDATE official_partners
                SET vgk4u_current_designation = :desig,
                    vgk4u_personal_prod_qualification = :prod_qual,
                    vgk4u_own_qualifying_files = :files,
                    vgk4u_active_team_count = :active_legs,
                    vgk4u_designation_updated_at = NOW()
                WHERE id = :pid
            """), {
                'desig': res['career_designation'],
                'prod_qual': res['personal_prod_qualification'],
                'files': res['own_qualifying_files'],
                'active_legs': res['active_team_legs'],
                'pid': pid,
            })
        db.flush()
        return len(bulk_res)
