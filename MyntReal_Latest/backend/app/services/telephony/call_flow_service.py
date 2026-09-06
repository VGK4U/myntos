"""
Call Flow Domain Service — MyntOS Native Telephony
Orchestrates CRUD operations, draft management, server-side validation, version publishing,
rollback, ring groups, business hours, and Plivo endpoint mapping.
Created: Sep 2026
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.telephony_call_flow import (
    TelephonyCallFlow, TelephonyCallFlowVersion, TelephonyFlowNode,
    TelephonyFlowEdge, TelephonyRingGroup, TelephonyRingGroupMember,
    TelephonyBusinessHours, TelephonyHoliday, TelephonyPlivoEndpoint,
    TelephonyFlowExecutionLog
)
from app.services.telephony.flow_validator import CallFlowValidator
from app.services.telephony.flow_simulator import CallFlowSimulator
from app.models.staff import StaffEmployee
from app.models.base import get_indian_time


class CallFlowService:
    """
    Central business logic coordinator for MyntOS Call Flow Designer.
    """

    @classmethod
    def list_flows(cls, db: Session, company_id: int) -> List[Dict[str, Any]]:
        flows = db.query(TelephonyCallFlow).filter(
            TelephonyCallFlow.company_id.in_([company_id, 1, 4]),
            TelephonyCallFlow.status != 'archived'
        ).order_by(TelephonyCallFlow.id.desc()).all()
        if not flows:
            flows = db.query(TelephonyCallFlow).filter(
                TelephonyCallFlow.status != 'archived'
            ).order_by(TelephonyCallFlow.id.desc()).all()
        # Sort so primary DID flow (+918031728899) or published flow is first
        sorted_flows = sorted(flows, key=lambda f: (f.did_number == '+918031728899', f.status == 'published', f.id), reverse=True)
        return [f.to_dict() for f in sorted_flows]

    @classmethod
    def create_flow(
        cls,
        db: Session,
        company_id: int,
        name: str,
        description: Optional[str] = None,
        did_number: Optional[str] = None,
        staff_id: Optional[int] = None,
        initial_graph: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create new Call Flow with initial draft Version 1"""
        if not initial_graph:
            initial_graph = cls._get_default_starter_graph(did_number)

        flow = TelephonyCallFlow(
            company_id=company_id,
            name=name,
            description=description,
            did_number=did_number,
            status='draft',
            created_by_staff_id=staff_id
        )
        db.add(flow)
        db.flush()

        version = TelephonyCallFlowVersion(
            flow_id=flow.id,
            company_id=company_id,
            version_number=1,
            status='draft',
            flow_data=initial_graph
        )
        db.add(version)
        db.commit()
        db.refresh(flow)

        res = flow.to_dict()
        res['draft_version'] = version.to_dict()
        return res

    @classmethod
    def get_flow_details(cls, db: Session, company_id: int, flow_id: int) -> Dict[str, Any]:
        flow = db.query(TelephonyCallFlow).filter(
            TelephonyCallFlow.id == flow_id,
            TelephonyCallFlow.company_id == company_id
        ).first()
        if not flow:
            raise HTTPException(status_code=404, detail="Call Flow not found")

        # Get latest draft version or current published version
        draft_version = db.query(TelephonyCallFlowVersion).filter(
            TelephonyCallFlowVersion.flow_id == flow_id,
            TelephonyCallFlowVersion.status == 'draft'
        ).order_by(TelephonyCallFlowVersion.version_number.desc()).first()

        published_version = None
        if flow.current_published_version_id:
            published_version = db.query(TelephonyCallFlowVersion).filter(
                TelephonyCallFlowVersion.id == flow.current_published_version_id
            ).first()
        elif not draft_version:
            published_version = db.query(TelephonyCallFlowVersion).filter(
                TelephonyCallFlowVersion.flow_id == flow_id
            ).order_by(TelephonyCallFlowVersion.version_number.desc()).first()

        res = flow.to_dict()
        draft_dict = draft_version.to_dict() if draft_version else None
        pub_dict = published_version.to_dict() if published_version else None

        # If graph is empty or minimal skeleton, populate comprehensive production graph
        if not draft_dict and not pub_dict:
            pub_dict = {
                'id': 1,
                'version_number': 1,
                'status': 'published',
                'flow_data': cls._get_default_starter_graph(flow.did_number)
            }
        elif pub_dict and (not pub_dict.get('flow_data') or len(pub_dict.get('flow_data', {}).get('nodes', [])) < 3):
            pub_dict['flow_data'] = cls._get_default_starter_graph(flow.did_number)

        if draft_dict and (not draft_dict.get('flow_data') or len(draft_dict.get('flow_data', {}).get('nodes', [])) < 3):
            draft_dict['flow_data'] = cls._get_default_starter_graph(flow.did_number)

        res['draft_version'] = draft_dict
        res['published_version'] = pub_dict
        return res

    @classmethod
    def save_draft(
        cls,
        db: Session,
        company_id: int,
        flow_id: int,
        flow_data: Dict[str, Any],
        name: Optional[str] = None,
        description: Optional[str] = None,
        did_number: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update draft version for flow. If no draft exists, fork one from published version."""
        flow = db.query(TelephonyCallFlow).filter(
            TelephonyCallFlow.id == flow_id,
            TelephonyCallFlow.company_id == company_id
        ).first()
        if not flow:
            raise HTTPException(status_code=404, detail="Call Flow not found")

        if name: flow.name = name
        if description is not None: flow.description = description
        if did_number is not None: flow.did_number = did_number

        draft = db.query(TelephonyCallFlowVersion).filter(
            TelephonyCallFlowVersion.flow_id == flow_id,
            TelephonyCallFlowVersion.status == 'draft'
        ).first()

        if not draft:
            # Fork new draft with version_number = max + 1
            max_ver = db.query(TelephonyCallFlowVersion.version_number).filter(
                TelephonyCallFlowVersion.flow_id == flow_id
            ).order_by(TelephonyCallFlowVersion.version_number.desc()).first()
            new_ver_num = (max_ver[0] + 1) if max_ver else 1

            draft = TelephonyCallFlowVersion(
                flow_id=flow_id,
                company_id=company_id,
                version_number=new_ver_num,
                status='draft',
                flow_data=flow_data
            )
            db.add(draft)
        else:
            draft.flow_data = flow_data

        db.commit()
        db.refresh(flow)
        db.refresh(draft)

        res = flow.to_dict()
        res['draft_version'] = draft.to_dict()
        return res

    @classmethod
    def validate_flow(
        cls,
        db: Session,
        company_id: int,
        flow_id: int,
        flow_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Run server-side graph validator on flow data or current draft"""
        if not flow_data:
            draft = db.query(TelephonyCallFlowVersion).filter(
                TelephonyCallFlowVersion.flow_id == flow_id,
                TelephonyCallFlowVersion.status == 'draft'
            ).first()
            if not draft:
                raise HTTPException(status_code=404, detail="No draft version found to validate")
            flow_data = draft.flow_data

        is_valid, issues = CallFlowValidator.validate_flow_graph(flow_data, company_id=company_id, db=db)
        return {
            'is_valid': is_valid,
            'issues_count': len(issues),
            'issues': issues
        }

    @classmethod
    def publish_flow(
        cls,
        db: Session,
        company_id: int,
        flow_id: int,
        staff_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Validate draft and publish it as an immutable active version.
        Deactivates previous published version and activates the new one without restarting app.
        """
        flow = db.query(TelephonyCallFlow).filter(
            TelephonyCallFlow.id == flow_id,
            TelephonyCallFlow.company_id == company_id
        ).first()
        if not flow:
            raise HTTPException(status_code=404, detail="Call Flow not found")

        draft = db.query(TelephonyCallFlowVersion).filter(
            TelephonyCallFlowVersion.flow_id == flow_id,
            TelephonyCallFlowVersion.status == 'draft'
        ).first()
        if not draft:
            raise HTTPException(status_code=400, detail="No active draft to publish")

        # 1. Run strict server-side validation
        is_valid, issues = CallFlowValidator.validate_flow_graph(draft.flow_data, company_id=company_id, db=db)
        if not is_valid:
            error_msgs = [i['message'] for i in issues if i['severity'] == 'error']
            raise HTTPException(status_code=400, detail=f"Flow validation failed: {'; '.join(error_msgs)}")

        # 2. Archive previous published version
        if flow.current_published_version_id:
            old_published = db.query(TelephonyCallFlowVersion).filter(
                TelephonyCallFlowVersion.id == flow.current_published_version_id
            ).first()
            if old_published:
                old_published.status = 'superseded'

        # 3. Mark draft as published (immutable)
        now_ist = get_indian_time()
        draft.status = 'published'
        draft.published_at = now_ist
        draft.published_by_staff_id = staff_id

        # 4. Update parent flow pointer
        flow.current_published_version_id = draft.id
        flow.status = 'published'

        # 5. Populate normalized node and edge entities for quick SQL querying
        db.query(TelephonyFlowNode).filter(TelephonyFlowNode.flow_version_id == draft.id).delete()
        db.query(TelephonyFlowEdge).filter(TelephonyFlowEdge.flow_version_id == draft.id).delete()

        nodes_list = draft.flow_data.get('nodes', [])
        for n in nodes_list:
            node_ent = TelephonyFlowNode(
                flow_version_id=draft.id,
                node_key=n.get('id') or n.get('node_key'),
                node_type=n.get('type') or n.get('node_type'),
                name=n.get('name', 'Node'),
                config=n.get('config', {}),
                position_x=n.get('position', {}).get('x', 100),
                position_y=n.get('position', {}).get('y', 100)
            )
            db.add(node_ent)

        edges_list = draft.flow_data.get('edges', [])
        for e in edges_list:
            edge_ent = TelephonyFlowEdge(
                flow_version_id=draft.id,
                source_node_key=e.get('from') or e.get('source_node') or e.get('source_node_key'),
                target_node_key=e.get('to') or e.get('target_node') or e.get('target_node_key'),
                condition=e.get('condition', 'always'),
                priority=e.get('priority', 0)
            )
            db.add(edge_ent)

        db.commit()
        db.refresh(flow)
        db.refresh(draft)

        res = flow.to_dict()
        res['published_version'] = draft.to_dict()
        return res

    @classmethod
    def rollback_flow(
        cls,
        db: Session,
        company_id: int,
        flow_id: int,
        target_version_id: int,
        staff_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Roll back active published flow to a prior published version"""
        flow = db.query(TelephonyCallFlow).filter(
            TelephonyCallFlow.id == flow_id,
            TelephonyCallFlow.company_id == company_id
        ).first()
        if not flow:
            raise HTTPException(status_code=404, detail="Call Flow not found")

        target_ver = db.query(TelephonyCallFlowVersion).filter(
            TelephonyCallFlowVersion.id == target_version_id,
            TelephonyCallFlowVersion.flow_id == flow_id
        ).first()
        if not target_ver:
            raise HTTPException(status_code=404, detail="Target version not found")

        # Set flow to target version
        if flow.current_published_version_id:
            curr = db.query(TelephonyCallFlowVersion).filter(
                TelephonyCallFlowVersion.id == flow.current_published_version_id
            ).first()
            if curr:
                curr.status = 'superseded'

        target_ver.status = 'published'
        target_ver.published_at = get_indian_time()
        target_ver.published_by_staff_id = staff_id
        flow.current_published_version_id = target_ver.id
        flow.status = 'published'

        db.commit()
        db.refresh(flow)
        res = flow.to_dict()
        res['published_version'] = target_ver.to_dict()
        return res

    @classmethod
    def simulate_flow(
        cls,
        db: Session,
        company_id: int,
        flow_id: int,
        caller_phone: str,
        simulated_datetime: Optional[datetime] = None,
        dtmf_inputs: Optional[List[str]] = None,
        override_graph: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Dry-run simulate flow without real call"""
        if override_graph:
            flow_data = override_graph
        else:
            draft = db.query(TelephonyCallFlowVersion).filter(
                TelephonyCallFlowVersion.flow_id == flow_id,
                TelephonyCallFlowVersion.status == 'draft'
            ).first()
            if draft:
                flow_data = draft.flow_data
            else:
                flow = db.query(TelephonyCallFlow).filter(TelephonyCallFlow.id == flow_id).first()
                if not flow or not flow.current_published_version_id:
                    raise HTTPException(status_code=404, detail="No flow version found for simulation")
                pub = db.query(TelephonyCallFlowVersion).filter(TelephonyCallFlowVersion.id == flow.current_published_version_id).first()
                flow_data = pub.flow_data

        return CallFlowSimulator.simulate_flow(
            db=db,
            flow_data=flow_data,
            company_id=company_id,
            caller_phone=caller_phone,
            simulated_datetime=simulated_datetime,
            dtmf_inputs=dtmf_inputs
        )

    # ── RING GROUP METHODS ───────────────────────────────────────────────────

    @classmethod
    def list_ring_groups(cls, db: Session, company_id: int) -> List[Dict[str, Any]]:
        # Query groups for company or standard tenant
        groups = db.query(TelephonyRingGroup).filter(
            (TelephonyRingGroup.company_id == company_id) | (TelephonyRingGroup.company_id == 1) | (TelephonyRingGroup.company_id == 4),
            TelephonyRingGroup.is_active == True
        ).order_by(TelephonyRingGroup.id.asc()).all()

        if not groups:
            # Auto-seed standard organization ring groups
            standard_groups = [
                {"name": "Solar Sales Ring Group", "strategy": "simultaneous", "timeout_seconds": 25, "fallback_action": "voicemail"},
                {"name": "Insurance Sales Ring Group", "strategy": "simultaneous", "timeout_seconds": 25, "fallback_action": "voicemail"},
                {"name": "Training Ring Group", "strategy": "simultaneous", "timeout_seconds": 25, "fallback_action": "voicemail"},
                {"name": "Manthra EV Ring Group", "strategy": "simultaneous", "timeout_seconds": 25, "fallback_action": "voicemail"},
                {"name": "VGK 4U Ring Group", "strategy": "simultaneous", "timeout_seconds": 25, "fallback_action": "voicemail"},
                {"name": "Service Support Ring Group", "strategy": "simultaneous", "timeout_seconds": 25, "fallback_action": "voicemail"},
                {"name": "Customer Care Executives Ring Group", "strategy": "simultaneous", "timeout_seconds": 25, "fallback_action": "voicemail"}
            ]
            for sg in standard_groups:
                rg = TelephonyRingGroup(
                    company_id=company_id or 1,
                    name=sg["name"],
                    strategy=sg["strategy"],
                    timeout_seconds=sg["timeout_seconds"],
                    fallback_action=sg["fallback_action"],
                    is_active=True
                )
                db.add(rg)
            db.commit()

            groups = db.query(TelephonyRingGroup).filter(
                (TelephonyRingGroup.company_id == company_id) | (TelephonyRingGroup.company_id == 1) | (TelephonyRingGroup.company_id == 4),
                TelephonyRingGroup.is_active == True
            ).order_by(TelephonyRingGroup.id.asc()).all()

        res = []
        for g in groups:
            g_dict = g.to_dict()
            g_dict['members'] = [m.to_dict() for m in g.members if getattr(m, 'is_active', True)]
            res.append(g_dict)
        return res

    @classmethod
    def create_ring_group(
        cls,
        db: Session,
        company_id: int,
        name: str,
        strategy: str = 'simultaneous',
        timeout_seconds: int = 25,
        fallback_action: str = 'voicemail',
        member_staff_ids: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        group = TelephonyRingGroup(
            company_id=company_id,
            name=name,
            strategy=strategy,
            timeout_seconds=timeout_seconds,
            fallback_action=fallback_action,
            is_active=True
        )
        db.add(group)
        db.flush()

        if member_staff_ids:
            for idx, staff_id in enumerate(member_staff_ids):
                mem = TelephonyRingGroupMember(
                    ring_group_id=group.id,
                    staff_id=staff_id,
                    priority_order=idx + 1,
                    is_active=True
                )
                db.add(mem)

        db.commit()
        db.refresh(group)
        g_dict = group.to_dict()
        g_dict['members'] = [m.to_dict() for m in group.members if getattr(m, 'is_active', True)]
        return g_dict

    @classmethod
    def update_ring_group(
        cls,
        db: Session,
        rg_id: int,
        payload: Dict[str, Any],
        company_id: Optional[int] = None
    ) -> Dict[str, Any]:
        rg = db.query(TelephonyRingGroup).filter(TelephonyRingGroup.id == rg_id).first()
        if not rg:
            raise HTTPException(status_code=404, detail="Ring Group not found")

        if "name" in payload and payload["name"]:
            rg.name = payload["name"].strip()
        if "strategy" in payload:
            rg.strategy = payload["strategy"]
        if "timeout_seconds" in payload:
            rg.timeout_seconds = int(payload["timeout_seconds"])
        if "fallback_action" in payload:
            rg.fallback_action = payload["fallback_action"]
        if "is_active" in payload:
            rg.is_active = bool(payload["is_active"])

        if "member_staff_ids" in payload:
            staff_ids = payload["member_staff_ids"] or []
            # Remove old members
            db.query(TelephonyRingGroupMember).filter(TelephonyRingGroupMember.ring_group_id == rg.id).delete()
            # Insert new members
            for idx, sid in enumerate(staff_ids):
                mem = TelephonyRingGroupMember(
                    ring_group_id=rg.id,
                    staff_id=int(sid),
                    priority_order=idx + 1,
                    is_active=True
                )
                db.add(mem)

        db.commit()
        db.refresh(rg)
        g_dict = rg.to_dict()
        g_dict['members'] = [m.to_dict() for m in rg.members if getattr(m, 'is_active', True)]
        return g_dict

    # ── DEFAULT STARTER GRAPH ────────────────────────────────────────────────

    @classmethod
    def _get_default_starter_graph(cls, did_number: Optional[str] = None) -> Dict[str, Any]:
        did_val = did_number or "+918031728899"
        return {
            "nodes": [
                {
                    "id": "node_trigger_did_1",
                    "type": "trigger_did",
                    "name": f"Incoming DID ({did_val})",
                    "position": {"x": 50, "y": 280},
                    "config": {"did_number": did_val}
                },
                {
                    "id": "node_time_check_1",
                    "type": "time_router",
                    "name": "Operating Hours Check (09:00–20:00 IST)",
                    "position": {"x": 340, "y": 280},
                    "config": {
                        "timezone": "Asia/Kolkata",
                        "start_time": "09:00",
                        "end_time": "20:00",
                        "days": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
                    }
                },
                {
                    "id": "node_caller_lookup_1",
                    "type": "caller_lookup",
                    "name": "CRM Sticky Agent Lookup",
                    "position": {"x": 660, "y": 200},
                    "config": {
                        "sticky_agent": True,
                        "fallback_to_ivr": True,
                        "timeout_seconds": 25
                    }
                },
                {
                    "id": "node_closed_vm_1",
                    "type": "voicemail",
                    "name": "After-Hours Voicemail",
                    "position": {"x": 660, "y": 420},
                    "config": {
                        "prompt": "Thank you for calling Mynt Real. Our office is currently closed. Our working hours are 9 AM to 8 PM Indian Standard Time. Please leave a message after the beep.",
                        "voice": "Polly.Aditi",
                        "max_length_seconds": 120
                    }
                },
                {
                    "id": "node_sales_ivr_1",
                    "type": "ivr_menu",
                    "name": "Sales & Services IVR",
                    "position": {"x": 980, "y": 200},
                    "config": {
                        "text": "Welcome to Mynt Real. Press 1 for Solar. Press 2 for Insurance. Press 3 for Training. Press 4 for Manthra EV. Press 5 for VGK 4U. Press 6 for Service Support. Press 9 to speak with Customer Care Executives. Press 0 to repeat this menu.",
                        "voice": "Polly.Aditi",
                        "language": "en-IN",
                        "timeout_seconds": 8,
                        "num_digits": 1,
                        "max_retries": 2
                    }
                },
                {
                    "id": "node_solar_group",
                    "type": "dial_ring_group",
                    "name": "Solar Sales Ring Group",
                    "position": {"x": 1360, "y": 40},
                    "config": {"department": "Solar", "ring_group_id": 1, "strategy": "simultaneous", "timeout_seconds": 25, "fallback": "voicemail", "staff_ids": []}
                },
                {
                    "id": "node_insurance_group",
                    "type": "dial_ring_group",
                    "name": "Insurance Sales Ring Group",
                    "position": {"x": 1360, "y": 120},
                    "config": {"department": "Insurance", "ring_group_id": 2, "strategy": "simultaneous", "timeout_seconds": 25, "fallback": "voicemail", "staff_ids": []}
                },
                {
                    "id": "node_training_group",
                    "type": "dial_ring_group",
                    "name": "Training Ring Group",
                    "position": {"x": 1360, "y": 200},
                    "config": {"department": "Training", "ring_group_id": 3, "strategy": "simultaneous", "timeout_seconds": 25, "fallback": "voicemail", "staff_ids": []}
                },
                {
                    "id": "node_ev_group",
                    "type": "dial_ring_group",
                    "name": "Manthra EV Ring Group",
                    "position": {"x": 1360, "y": 280},
                    "config": {"department": "Manthra EV", "ring_group_id": 4, "strategy": "simultaneous", "timeout_seconds": 25, "fallback": "voicemail", "staff_ids": []}
                },
                {
                    "id": "node_vgk4u_group",
                    "type": "dial_ring_group",
                    "name": "VGK 4U Ring Group",
                    "position": {"x": 1360, "y": 360},
                    "config": {"department": "VGK 4U", "ring_group_id": 5, "strategy": "simultaneous", "timeout_seconds": 25, "fallback": "voicemail", "staff_ids": []}
                },
                {
                    "id": "node_support_group",
                    "type": "dial_ring_group",
                    "name": "Service Support Ring Group",
                    "position": {"x": 1360, "y": 440},
                    "config": {"department": "Service Support", "ring_group_id": 6, "strategy": "simultaneous", "timeout_seconds": 25, "fallback": "voicemail", "staff_ids": []}
                },
                {
                    "id": "node_care_group",
                    "type": "dial_ring_group",
                    "name": "Customer Care Ring Group",
                    "position": {"x": 1360, "y": 520},
                    "config": {"department": "Customer Care", "ring_group_id": 7, "strategy": "simultaneous", "timeout_seconds": 25, "fallback": "voicemail", "staff_ids": []}
                },
                {
                    "id": "node_fallback_vm",
                    "type": "voicemail",
                    "name": "Exhausted Fallback Voicemail",
                    "position": {"x": 1720, "y": 280},
                    "config": {
                        "prompt": "All of our executives are currently attending to other customers. Please leave your name and contact number after the tone and we will call you back shortly.",
                        "voice": "Polly.Aditi",
                        "max_length_seconds": 120
                    }
                },
                {
                    "id": "node_hangup_1",
                    "type": "hangup",
                    "name": "End Call",
                    "position": {"x": 2040, "y": 350},
                    "config": {"reason": "normal"}
                }
            ],
            "edges": [
                {"from": "node_trigger_did_1", "to": "node_time_check_1", "condition": "always"},
                {"from": "node_time_check_1", "to": "node_caller_lookup_1", "condition": "open"},
                {"from": "node_time_check_1", "to": "node_closed_vm_1", "condition": "closed"},
                {"from": "node_closed_vm_1", "to": "node_hangup_1", "condition": "next"},
                {"from": "node_caller_lookup_1", "to": "node_sales_ivr_1", "condition": "unmatched"},
                {"from": "node_sales_ivr_1", "to": "node_solar_group", "condition": "digit_1"},
                {"from": "node_sales_ivr_1", "to": "node_insurance_group", "condition": "digit_2"},
                {"from": "node_sales_ivr_1", "to": "node_training_group", "condition": "digit_3"},
                {"from": "node_sales_ivr_1", "to": "node_ev_group", "condition": "digit_4"},
                {"from": "node_sales_ivr_1", "to": "node_vgk4u_group", "condition": "digit_5"},
                {"from": "node_sales_ivr_1", "to": "node_support_group", "condition": "digit_6"},
                {"from": "node_sales_ivr_1", "to": "node_care_group", "condition": "digit_9"},
                {"from": "node_sales_ivr_1", "to": "node_sales_ivr_1", "condition": "digit_0"},
                {"from": "node_sales_ivr_1", "to": "node_care_group", "condition": "timeout"},
                {"from": "node_solar_group", "to": "node_fallback_vm", "condition": "no_answer"},
                {"from": "node_insurance_group", "to": "node_fallback_vm", "condition": "no_answer"},
                {"from": "node_training_group", "to": "node_fallback_vm", "condition": "no_answer"},
                {"from": "node_ev_group", "to": "node_fallback_vm", "condition": "no_answer"},
                {"from": "node_vgk4u_group", "to": "node_fallback_vm", "condition": "no_answer"},
                {"from": "node_support_group", "to": "node_fallback_vm", "condition": "no_answer"},
                {"from": "node_care_group", "to": "node_fallback_vm", "condition": "no_answer"},
                {"from": "node_fallback_vm", "to": "node_hangup_1", "condition": "next"}
            ]
        }
