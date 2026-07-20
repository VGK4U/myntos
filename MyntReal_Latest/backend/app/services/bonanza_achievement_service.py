"""
Bonanza Achievement Data Service
DC Protocol: Centralized single source of truth for bonanza achievement tracking
Used by: Achievement Data tab, Bonanza Management, Award Management, Procurement
Access: MNR Members and Staff only (no admin/third-party)
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)


class BonanzaAchievementService:

    def __init__(self, db: Session):
        self.db = db

    def get_campaign_list(self) -> List[Dict[str, Any]]:
        rows = self.db.execute(text("""
            SELECT name,
                   MIN(start_date) as earliest_start,
                   MAX(end_date) as latest_end,
                   COUNT(*) as level_count,
                   MAX(CASE WHEN status = 'Approved' AND end_date >= NOW() THEN 1 ELSE 0 END) as is_active
            FROM bonanza
            WHERE is_deleted = false
            GROUP BY name
            ORDER BY MAX(end_date) DESC, name
        """)).fetchall()
        result = []
        for r in rows:
            result.append({
                "name": r[0],
                "earliest_start": r[1].isoformat() if r[1] else None,
                "latest_end": r[2].isoformat() if r[2] else None,
                "level_count": r[3],
                "is_active": bool(r[4])
            })
        return result

    def get_campaign_levels(self, campaign_name: str) -> Dict[str, List[Dict]]:
        rows = self.db.execute(text("""
            SELECT id, criteria_type, target_requirement, award_name, reward_type, reward_amount,
                   start_date, end_date, status, consume_achievements, max_winners
            FROM bonanza
            WHERE name = :name AND is_deleted = false
            ORDER BY criteria_type, target_requirement, id
        """), {"name": campaign_name}).fetchall()

        direct_levels = []
        group_levels = []
        for r in rows:
            level = {
                "bonanza_id": r[0],
                "criteria_type": r[1],
                "target": r[2],
                "award_name": r[3] or f"Level {r[2]}",
                "reward_type": r[4],
                "reward_amount": float(r[5]) if r[5] else None,
                "start_date": r[6].isoformat() if r[6] else None,
                "end_date": r[7].isoformat() if r[7] else None,
                "status": r[8],
                "consume_achievements": r[9],
                "max_winners": r[10]
            }
            if r[1] in ('direct_referral', 'direct_referrals'):
                direct_levels.append(level)
            else:
                group_levels.append(level)

        return {"direct": direct_levels, "group": group_levels}

    def _get_all_user_claims_bulk(self, user_ids: List[str], bonanza_ids: List[int]) -> Dict[str, Dict[int, Dict]]:
        if not user_ids or not bonanza_ids:
            return {}
        placeholders = ",".join([str(bid) for bid in bonanza_ids])
        uid_placeholders = ",".join([f"'{uid}'" for uid in user_ids])
        rows = self.db.execute(text(f"""
            SELECT dbh.user_id, dbh.bonanza_id, dbh.claimed_at, dbh.processed_status,
                   dbh.direct_count_achieved, dbh.matching_count_achieved,
                   b.target_requirement
            FROM dynamic_bonanza_history dbh
            JOIN bonanza b ON b.id = dbh.bonanza_id
            WHERE dbh.user_id IN ({uid_placeholders})
                AND dbh.bonanza_id IN ({placeholders})
                AND dbh.claimed_at IS NOT NULL
        """)).fetchall()
        result = {}
        for r in rows:
            uid = r[0]
            if uid not in result:
                result[uid] = {}
            result[uid][r[1]] = {
                "claimed_at": r[2].isoformat() if r[2] else None,
                "processed_status": r[3],
                "direct_count": r[4] or 0,
                "matching_count": r[5] or 0,
                "target": r[6]
            }
        return result

    def get_achievement_data(
        self,
        campaign_name: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
        search: Optional[str] = None
    ) -> Dict[str, Any]:
        levels = self.get_campaign_levels(campaign_name)
        all_levels = levels["direct"] + levels["group"]
        if not all_levels:
            return {"success": True, "data": [], "levels": levels, "total": 0, "page": page, "page_size": page_size}

        direct_levels = levels["direct"]
        group_levels = levels["group"]

        start_date = None
        end_date = None
        if all_levels:
            all_starts = [l["start_date"] for l in all_levels if l["start_date"]]
            all_ends = [l["end_date"] for l in all_levels if l["end_date"]]
            if all_starts:
                start_date = min(all_starts)
            if all_ends:
                end_date = max(all_ends)

        if date_from:
            start_date = date_from
        if date_to:
            end_date = date_to

        if not start_date or not end_date:
            return {"success": True, "data": [], "levels": levels, "total": 0, "page": page, "page_size": page_size}

        direct_max_target = max([l["target"] for l in direct_levels], default=0)
        group_max_target = max([l["target"] for l in group_levels], default=0)

        direct_min_threshold = max(1, int(direct_max_target * 0.01)) if direct_max_target > 0 else 1
        group_min_threshold = max(1, int(group_max_target * 0.01)) if group_max_target > 0 else 1

        search_clause = ""
        params = {
            "start_date": start_date,
            "end_date": end_date,
        }

        if search:
            search_clause = "AND (u.id ILIKE :search OR u.name ILIKE :search OR u.referrer_id ILIKE :search)"
            params["search"] = f"%{search}%"

        achievement_rows = []
        all_user_ids = set()

        if direct_levels:
            direct_sql = f"""
                SELECT u.id as mnr_id, u.name, u.referrer_id,
                       ref_u.name as referrer_name,
                       MIN(dr.activation_date) as started_achieving_date,
                       COUNT(dr.id) as total_count,
                       COUNT(CASE WHEN dr.is_welcome_coupon = true THEN 1 END) as welcome_count,
                       u.is_welcome_coupon as is_wc_user,
                       u.coupon_status as user_coupon_status,
                       u.kyc_status as user_kyc_status,
                       CASE WHEN EXISTS (
                           SELECT 1 FROM "user" elig
                           WHERE elig.referrer_id = u.id
                               AND elig.coupon_status = 'Activated'
                               AND elig.package_points > 0
                               AND elig.activation_date >= '2025-11-17'
                       ) THEN true ELSE false END as is_eligible,
                       COALESCE((SELECT COUNT(*) FROM "user" ec
                           WHERE ec.referrer_id = u.id
                               AND ec.coupon_status = 'Activated'
                               AND ec.activation_date >= :start_date
                               AND ec.activation_date <= :end_date
                               AND (ec.is_welcome_coupon = true OR ec.package_points = 0)
                       ), 0) as exempted_coupon_count
                FROM "user" u
                LEFT JOIN "user" ref_u ON ref_u.id = u.referrer_id
                INNER JOIN "user" dr ON dr.referrer_id = u.id
                    AND dr.coupon_status = 'Activated'
                    AND dr.activation_date >= :start_date
                    AND dr.activation_date <= :end_date
                    AND dr.package_points > 0
                WHERE 1=1
                {search_clause}
                GROUP BY u.id, u.name, u.referrer_id, ref_u.name, u.is_welcome_coupon, u.coupon_status, u.kyc_status
                HAVING COUNT(dr.id) >= :min_threshold
                ORDER BY COUNT(dr.id) DESC
            """
            params["min_threshold"] = direct_min_threshold
            d_rows = self.db.execute(text(direct_sql), params).fetchall()

            for r in d_rows:
                total_count = r[5]
                welcome_count = r[6] or 0
                is_wc_user = bool(r[7]) if r[7] else False
                user_coupon_status = r[8] or 'Unknown'
                user_kyc_status = r[9] or 'Pending'
                is_eligible = bool(r[10]) if r[10] is not None else False
                exempted_count = r[11] or 0
                all_user_ids.add(r[0])
                effective_target = direct_max_target + (1 if is_wc_user else 0) + exempted_count
                achievement_rows.append({
                    "mnr_id": r[0],
                    "name": r[1],
                    "referrer_id": r[2],
                    "referrer_name": r[3],
                    "started_achieving_date": r[4].isoformat() if r[4] else None,
                    "type": "Direct",
                    "target": effective_target,
                    "max_achieved": total_count + exempted_count,
                    "raw_achieved": total_count,
                    "welcome_coupon_count": welcome_count,
                    "exempted_coupon_count": exempted_count,
                    "has_welcome_bonus": is_wc_user or welcome_count > 0 or exempted_count > 0,
                    "coupon_status": user_coupon_status,
                    "kyc_status": user_kyc_status,
                    "is_eligible": is_eligible,
                    "_levels": direct_levels,
                    "_type_key": "direct"
                })

            if "min_threshold" in params:
                del params["min_threshold"]

        if group_levels:
            has_matching = any(l["criteria_type"] == "matching_points" for l in group_levels)
            has_team = any(l["criteria_type"] == "team_size" for l in group_levels)

            if has_team:
                team_sql = f"""
                    SELECT u.id as mnr_id, u.name, u.referrer_id,
                           ref_u.name as referrer_name,
                           MIN(tm.activation_date) as started_achieving_date,
                           COUNT(tm.id) as achieved_count,
                           u.is_welcome_coupon as is_wc_user,
                           u.coupon_status as user_coupon_status,
                           u.kyc_status as user_kyc_status,
                           CASE WHEN EXISTS (
                               SELECT 1 FROM "user" elig
                               WHERE elig.referrer_id = u.id
                                   AND elig.coupon_status = 'Activated'
                                   AND elig.package_points > 0
                                   AND elig.activation_date >= '2025-11-17'
                           ) THEN true ELSE false END as is_eligible,
                           COALESCE((SELECT COUNT(*) FROM placement ep
                               INNER JOIN "user" ec ON ec.id = ep.child_id
                               WHERE ep.parent_id = u.id
                                   AND ec.account_status = 'Active'
                                   AND ec.activation_date >= :start_date
                                   AND ec.activation_date <= :end_date
                                   AND (ec.is_welcome_coupon = true OR ec.package_points = 0)
                           ), 0) as exempted_coupon_count
                    FROM "user" u
                    LEFT JOIN "user" ref_u ON ref_u.id = u.referrer_id
                    INNER JOIN placement p ON p.parent_id = u.id
                    INNER JOIN "user" tm ON tm.id = p.child_id
                        AND tm.account_status = 'Active'
                        AND tm.activation_date >= :start_date
                        AND tm.activation_date <= :end_date
                        AND (tm.is_welcome_coupon IS NULL OR tm.is_welcome_coupon = false)
                        AND tm.package_points > 0
                    WHERE 1=1
                    {search_clause}
                    GROUP BY u.id, u.name, u.referrer_id, ref_u.name, u.is_welcome_coupon, u.coupon_status, u.kyc_status
                    HAVING COUNT(tm.id) >= :min_threshold
                    ORDER BY COUNT(tm.id) DESC
                """
                params["min_threshold"] = group_min_threshold
                g_rows = self.db.execute(text(team_sql), params).fetchall()

                for r in g_rows:
                    is_wc_user = bool(r[6]) if r[6] else False
                    user_coupon_status = r[7] or 'Unknown'
                    user_kyc_status = r[8] or 'Pending'
                    is_eligible = bool(r[9]) if r[9] is not None else False
                    exempted_count = r[10] or 0
                    all_user_ids.add(r[0])
                    effective_target = group_max_target + (1 if is_wc_user else 0) + exempted_count
                    achievement_rows.append({
                        "mnr_id": r[0],
                        "name": r[1],
                        "referrer_id": r[2],
                        "referrer_name": r[3],
                        "started_achieving_date": r[4].isoformat() if r[4] else None,
                        "type": "Group",
                        "target": effective_target,
                        "max_achieved": r[5] + exempted_count,
                        "raw_achieved": r[5],
                        "welcome_coupon_count": 0,
                        "exempted_coupon_count": exempted_count,
                        "has_welcome_bonus": is_wc_user or exempted_count > 0,
                        "coupon_status": user_coupon_status,
                        "kyc_status": user_kyc_status,
                        "is_eligible": is_eligible,
                        "_levels": group_levels,
                        "_type_key": "group"
                    })

                if "min_threshold" in params:
                    del params["min_threshold"]

            if has_matching:
                match_sql = f"""
                    SELECT u.id as mnr_id, u.name, u.referrer_id,
                           ref_u.name as referrer_name,
                           MIN(t.created_at) as started_achieving_date,
                           COUNT(t.id) as achieved_count,
                           u.is_welcome_coupon as is_wc_user,
                           u.coupon_status as user_coupon_status,
                           u.kyc_status as user_kyc_status,
                           CASE WHEN EXISTS (
                               SELECT 1 FROM "user" elig
                               WHERE elig.referrer_id = u.id
                                   AND elig.coupon_status = 'Activated'
                                   AND elig.package_points > 0
                                   AND elig.activation_date >= '2025-11-17'
                           ) THEN true ELSE false END as is_eligible
                    FROM "user" u
                    LEFT JOIN "user" ref_u ON ref_u.id = u.referrer_id
                    INNER JOIN transaction t ON t.user_id = u.id
                        AND t.transaction_type = 'Matching Referral Income'
                        AND t.created_at >= :start_date
                        AND t.created_at <= :end_date
                        AND t.gross_amount > 0
                    WHERE 1=1
                    {search_clause}
                    GROUP BY u.id, u.name, u.referrer_id, ref_u.name, u.is_welcome_coupon, u.coupon_status, u.kyc_status
                    HAVING COUNT(t.id) >= :min_threshold
                    ORDER BY COUNT(t.id) DESC
                """
                params["min_threshold"] = group_min_threshold
                m_rows = self.db.execute(text(match_sql), params).fetchall()

                for r in m_rows:
                    is_wc_user = bool(r[6]) if r[6] else False
                    user_coupon_status = r[7] or 'Unknown'
                    user_kyc_status = r[8] or 'Pending'
                    is_eligible = bool(r[9]) if r[9] is not None else False
                    existing = next((x for x in achievement_rows if x["mnr_id"] == r[0] and x["type"] == "Group"), None)
                    if existing:
                        if r[5] > existing["raw_achieved"]:
                            existing["raw_achieved"] = r[5]
                            existing["max_achieved"] = r[5] + existing.get("exempted_coupon_count", 0)
                        if is_wc_user:
                            existing["has_welcome_bonus"] = True
                        if is_eligible:
                            existing["is_eligible"] = True
                    else:
                        all_user_ids.add(r[0])
                        effective_target = group_max_target + (1 if is_wc_user else 0)
                        achievement_rows.append({
                            "mnr_id": r[0],
                            "name": r[1],
                            "referrer_id": r[2],
                            "referrer_name": r[3],
                            "started_achieving_date": r[4].isoformat() if r[4] else None,
                            "type": "Group",
                            "target": effective_target,
                            "max_achieved": r[5],
                            "raw_achieved": r[5],
                            "welcome_coupon_count": 0,
                            "exempted_coupon_count": 0,
                            "has_welcome_bonus": is_wc_user,
                            "coupon_status": user_coupon_status,
                            "kyc_status": user_kyc_status,
                            "is_eligible": is_eligible,
                            "_levels": group_levels,
                            "_type_key": "group"
                        })

                if "min_threshold" in params:
                    del params["min_threshold"]

        all_bonanza_ids = [l["bonanza_id"] for l in all_levels]
        all_claims = self._get_all_user_claims_bulk(list(all_user_ids), all_bonanza_ids)

        direct_bonanza_ids = [l["bonanza_id"] for l in direct_levels]
        group_bonanza_ids = [l["bonanza_id"] for l in group_levels]

        for row in achievement_rows:
            uid = row["mnr_id"]
            type_levels = row.pop("_levels")
            type_key = row.pop("_type_key")

            net_achieved = self._apply_consumption_deductions(uid, row["raw_achieved"], type_levels, type_key)
            row["achieved"] = net_achieved

            user_claims = all_claims.get(uid, {})

            claimed_points = 0
            for lvl in type_levels:
                bid = lvl["bonanza_id"]
                if bid in user_claims:
                    claim = user_claims[bid]
                    if type_key == "direct":
                        claimed_points += claim["direct_count"] or claim["target"]
                    else:
                        claimed_points += claim["matching_count"] or claim["target"]

            row["claimed_points"] = claimed_points
            row["balance_points"] = max(0, row["raw_achieved"] - claimed_points)

            is_wc = row.get("has_welcome_bonus", False)
            wc_bonus = 1 if is_wc else 0

            direct_level_statuses = []
            for lvl in direct_levels:
                bid = lvl["bonanza_id"]
                claim_info = user_claims.get(bid)
                if type_key == "direct":
                    target = lvl["target"] + wc_bonus
                    if claim_info:
                        direct_level_statuses.append({
                            "bonanza_id": bid,
                            "award_name": lvl["award_name"],
                            "target": target,
                            "status": "Claimed",
                            "claimed_status": claim_info["processed_status"],
                            "claimed_at": claim_info["claimed_at"],
                            "pending": 0
                        })
                    elif net_achieved >= target:
                        direct_level_statuses.append({
                            "bonanza_id": bid,
                            "award_name": lvl["award_name"],
                            "target": target,
                            "status": "Achieved",
                            "claimed_status": None,
                            "claimed_at": None,
                            "pending": 0
                        })
                    else:
                        pending = target - net_achieved
                        direct_level_statuses.append({
                            "bonanza_id": bid,
                            "award_name": lvl["award_name"],
                            "target": target,
                            "status": f"{pending}",
                            "claimed_status": None,
                            "claimed_at": None,
                            "pending": pending
                        })
                else:
                    direct_level_statuses.append({
                        "bonanza_id": bid,
                        "award_name": lvl["award_name"],
                        "target": lvl["target"],
                        "status": "-",
                        "claimed_status": None,
                        "claimed_at": None,
                        "pending": None
                    })

            group_level_statuses = []
            for lvl in group_levels:
                bid = lvl["bonanza_id"]
                claim_info = user_claims.get(bid)
                if type_key == "group":
                    target = lvl["target"] + wc_bonus
                    if claim_info:
                        group_level_statuses.append({
                            "bonanza_id": bid,
                            "award_name": lvl["award_name"],
                            "target": target,
                            "status": "Claimed",
                            "claimed_status": claim_info["processed_status"],
                            "claimed_at": claim_info["claimed_at"],
                            "pending": 0
                        })
                    elif net_achieved >= target:
                        group_level_statuses.append({
                            "bonanza_id": bid,
                            "award_name": lvl["award_name"],
                            "target": target,
                            "status": "Achieved",
                            "claimed_status": None,
                            "claimed_at": None,
                            "pending": 0
                        })
                    else:
                        pending = target - net_achieved
                        group_level_statuses.append({
                            "bonanza_id": bid,
                            "award_name": lvl["award_name"],
                            "target": target,
                            "status": f"{pending}",
                            "claimed_status": None,
                            "claimed_at": None,
                            "pending": pending
                        })
                else:
                    group_level_statuses.append({
                        "bonanza_id": bid,
                        "award_name": lvl["award_name"],
                        "target": lvl["target"],
                        "status": "-",
                        "claimed_status": None,
                        "claimed_at": None,
                        "pending": None
                    })

            row["direct_level_statuses"] = direct_level_statuses
            row["group_level_statuses"] = group_level_statuses
            del row["raw_achieved"]

        achievement_rows.sort(key=lambda x: (-x["achieved"], x["mnr_id"]))

        total = len(achievement_rows)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated = achievement_rows[start_idx:end_idx]

        return {
            "success": True,
            "data": paginated,
            "levels": levels,
            "total": total,
            "page": page,
            "page_size": page_size,
            "campaign_name": campaign_name,
            "date_range": {"from": start_date, "to": end_date}
        }

    def get_campaign_summary(
        self,
        campaign_name: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> Dict[str, Any]:
        levels = self.get_campaign_levels(campaign_name)
        all_levels = levels["direct"] + levels["group"]
        if not all_levels:
            return {"success": True, "summary": [], "campaign_name": campaign_name}

        all_starts = [l["start_date"] for l in all_levels if l["start_date"]]
        all_ends = [l["end_date"] for l in all_levels if l["end_date"]]
        start_date = date_from or (min(all_starts) if all_starts else None)
        end_date = date_to or (max(all_ends) if all_ends else None)

        if not start_date or not end_date:
            return {"success": True, "summary": [], "campaign_name": campaign_name}

        summary = []
        for lvl in all_levels:
            bid = lvl["bonanza_id"]
            criteria_type = lvl["criteria_type"]
            target = lvl["target"]
            level_type = "Direct" if criteria_type in ('direct_referral', 'direct_referrals') else "Group"

            if criteria_type in ('direct_referral', 'direct_referrals'):
                count_sql = """
                    SELECT COUNT(DISTINCT u.id)
                    FROM "user" u
                    INNER JOIN "user" dr ON dr.referrer_id = u.id
                        AND dr.coupon_status = 'Activated'
                        AND dr.activation_date >= :start_date
                        AND dr.activation_date <= :end_date
                        AND dr.package_points > 0
                    GROUP BY u.id
                    HAVING COUNT(dr.id) >= :target
                """
            elif criteria_type == 'team_size':
                count_sql = """
                    SELECT COUNT(DISTINCT u.id)
                    FROM "user" u
                    INNER JOIN placement p ON p.parent_id = u.id
                    INNER JOIN "user" tm ON tm.id = p.child_id
                        AND tm.account_status = 'Active'
                        AND tm.activation_date >= :start_date
                        AND tm.activation_date <= :end_date
                        AND (tm.is_welcome_coupon IS NULL OR tm.is_welcome_coupon = false)
                        AND tm.package_points > 0
                    GROUP BY u.id
                    HAVING COUNT(tm.id) >= :target
                """
            else:
                count_sql = """
                    SELECT COUNT(DISTINCT u.id)
                    FROM "user" u
                    INNER JOIN transaction t ON t.user_id = u.id
                        AND t.transaction_type = 'Matching Referral Income'
                        AND t.created_at >= :start_date
                        AND t.created_at <= :end_date
                        AND t.gross_amount > 0
                    GROUP BY u.id
                    HAVING COUNT(t.id) >= :target
                """

            try:
                achieved_rows = self.db.execute(text(count_sql), {
                    "start_date": start_date, "end_date": end_date, "target": target
                }).fetchall()
                achieved_count = len(achieved_rows)
            except Exception as e:
                logger.error(f"Error counting achieved for bonanza {bid}: {e}")
                achieved_count = 0

            try:
                claimed_row = self.db.execute(text("""
                    SELECT COUNT(DISTINCT dbh.user_id)
                    FROM dynamic_bonanza_history dbh
                    WHERE dbh.bonanza_id = :bid
                        AND dbh.claimed_at IS NOT NULL
                        AND COALESCE(dbh.processed_status, '') != 'Rejected'
                """), {"bid": bid}).fetchone()
                claimed_count = claimed_row[0] if claimed_row else 0
            except Exception as e:
                logger.error(f"Error counting claims for bonanza {bid}: {e}")
                claimed_count = 0

            summary.append({
                "bonanza_id": bid,
                "award_name": lvl["award_name"],
                "level_type": level_type,
                "criteria_type": criteria_type,
                "target": target,
                "reward_type": lvl["reward_type"],
                "reward_amount": lvl["reward_amount"],
                "achieved_count": achieved_count,
                "claimed_count": claimed_count,
                "start_date": lvl["start_date"],
                "end_date": lvl["end_date"],
                "status": lvl["status"],
                "max_winners": lvl.get("max_winners")
            })

        return {"success": True, "summary": summary, "campaign_name": campaign_name}

    def get_achievement_contributors(
        self,
        campaign_name: str,
        user_id: str,
        achievement_type: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> Dict[str, Any]:
        levels = self.get_campaign_levels(campaign_name)
        type_levels = levels["direct"] if achievement_type == "direct" else levels["group"]
        if not type_levels:
            return {"success": True, "contributors": [], "user_id": user_id}

        all_starts = [l["start_date"] for l in type_levels if l["start_date"]]
        all_ends = [l["end_date"] for l in type_levels if l["end_date"]]
        start_date = date_from or (min(all_starts) if all_starts else None)
        end_date = date_to or (max(all_ends) if all_ends else None)

        if not start_date or not end_date:
            return {"success": True, "contributors": [], "user_id": user_id}

        def _pkg_name(pts):
            pts = float(pts) if pts else 0
            if pts >= 1.0:
                return "Platinum"
            elif pts >= 0.5:
                return "Diamond"
            elif pts > 0:
                return "Star"
            return "-"

        def _side_label(side):
            if side == 'left':
                return 'Group A'
            elif side == 'right':
                return 'Group B'
            return side or '-'

        contributors = []

        if achievement_type == "direct":
            rows = self.db.execute(text("""
                SELECT dr.id, dr.name, dr.package_points,
                       dr.activation_date, dr.coupon_status
                FROM "user" dr
                WHERE dr.referrer_id = :user_id
                    AND dr.coupon_status = 'Activated'
                    AND dr.activation_date >= :start_date
                    AND dr.activation_date <= :end_date
                    AND dr.is_welcome_coupon = false
                    AND dr.package_points > 0
                ORDER BY dr.activation_date
            """), {"user_id": user_id, "start_date": start_date, "end_date": end_date}).fetchall()

            for r in rows:
                pkg_pts = float(r[2]) if r[2] else 0
                contributors.append({
                    "mnr_id": r[0],
                    "name": r[1],
                    "package": _pkg_name(pkg_pts),
                    "points": pkg_pts,
                    "activation_date": r[3].isoformat() if r[3] else None,
                    "status": r[4]
                })
        else:
            has_team = any(l["criteria_type"] == "team_size" for l in type_levels)
            has_matching = any(l["criteria_type"] == "matching_points" for l in type_levels)

            if has_team:
                rows = self.db.execute(text("""
                    SELECT tm.id, tm.name, tm.package_points,
                           tm.activation_date, p.side, tm.coupon_status
                    FROM placement p
                    INNER JOIN "user" tm ON tm.id = p.child_id
                    WHERE p.parent_id = :user_id
                        AND tm.account_status = 'Active'
                        AND tm.activation_date >= :start_date
                        AND tm.activation_date <= :end_date
                        AND (tm.is_welcome_coupon IS NULL OR tm.is_welcome_coupon = false)
                        AND tm.package_points > 0
                    ORDER BY p.side, tm.activation_date
                """), {"user_id": user_id, "start_date": start_date, "end_date": end_date}).fetchall()

                for r in rows:
                    pkg_pts = float(r[2]) if r[2] else 0
                    contributors.append({
                        "mnr_id": r[0],
                        "name": r[1],
                        "package": _pkg_name(pkg_pts),
                        "points": pkg_pts,
                        "activation_date": r[3].isoformat() if r[3] else None,
                        "side": _side_label(r[4]),
                        "status": r[5],
                        "source": "team"
                    })

            if has_matching:
                rows = self.db.execute(text("""
                    SELECT t.id, t.transaction_type, t.gross_amount, t.created_at,
                           t.referred_id, ru.name as referred_name
                    FROM transaction t
                    LEFT JOIN "user" ru ON ru.id = t.referred_id
                    WHERE t.user_id = :user_id
                        AND t.transaction_type = 'Matching Referral Income'
                        AND t.created_at >= :start_date
                        AND t.created_at <= :end_date
                        AND t.gross_amount > 0
                    ORDER BY t.created_at
                """), {"user_id": user_id, "start_date": start_date, "end_date": end_date}).fetchall()

                for r in rows:
                    contributors.append({
                        "transaction_id": r[0],
                        "type": r[1],
                        "amount": float(r[2]) if r[2] else 0,
                        "date": r[3].isoformat() if r[3] else None,
                        "referred_id": r[4],
                        "referred_name": r[5],
                        "source": "matching"
                    })

        return {
            "success": True,
            "contributors": contributors,
            "user_id": user_id,
            "type": achievement_type,
            "total": len(contributors)
        }

    def _apply_consumption_deductions(
        self,
        user_id: str,
        raw_achieved: int,
        levels: List[Dict],
        type_key: str
    ) -> int:
        consume_levels = [l for l in levels if l.get("consume_achievements")]
        if not consume_levels:
            return raw_achieved

        bonanza_ids = [l["bonanza_id"] for l in levels]
        is_direct = type_key == "direct"

        placeholders = ",".join([str(bid) for bid in bonanza_ids])
        rows = self.db.execute(text(f"""
            SELECT dbh.bonanza_id, dbh.direct_count_achieved, dbh.matching_count_achieved,
                   b.criteria_type, b.target_requirement
            FROM dynamic_bonanza_history dbh
            JOIN bonanza b ON b.id = dbh.bonanza_id
            WHERE dbh.user_id = :user_id
                AND dbh.claimed_at IS NOT NULL
                AND b.consume_achievements = true
                AND b.is_deleted = false
                AND dbh.bonanza_id NOT IN ({placeholders})
        """), {"user_id": user_id}).fetchall()

        total_consumed = 0
        for r in rows:
            claimed_criteria = r[3]
            if is_direct and claimed_criteria in ('direct_referral', 'direct_referrals'):
                total_consumed += r[1] or r[4]
            elif not is_direct and claimed_criteria in ('team_size', 'matching_points'):
                total_consumed += r[2] or r[4]

        return max(0, raw_achieved - total_consumed)
