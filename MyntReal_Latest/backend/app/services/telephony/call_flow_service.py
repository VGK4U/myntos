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
            TelephonyCallFlow.company_id == company_id,
            TelephonyCallFlow.status != 'archived'
        ).order_by(TelephonyCallFlow.id.desc()).all()
        return [f.to_dict() for f in flows]

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

        res = flow.to_dict()
        res['draft_version'] = draft_version.to_dict() if draft_version else None
        res['published_version'] = published_version.to_dict() if published_version else None
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
        groups = db.query(TelephonyRingGroup).filter(
            TelephonyRingGroup.company_id == company_id,
            TelephonyRingGroup.is_active == True
        ).all()
        res = []
        for g in groups:
            g_dict = g.to_dict()
            g_dict['members'] = [m.to_dict() for m in g.members if m.is_active]
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
            fallback_action=fallback_action
        )
        db.add(group)
        db.flush()

        if member_staff_ids:
            for idx, staff_id in enumerate(member_staff_ids):
                mem = TelephonyRingGroupMember(
                    ring_group_id=group.id,
                    staff_id=staff_id,
                    priority_order=idx + 1
                )
                db.add(mem)

        db.commit()
        db.refresh(group)
        g_dict = group.to_dict()
        g_dict['members'] = [m.to_dict() for m in group.members]
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
                    "config": { "did_number": did_val }
                },
                {
                    "id": "node_time_check_1",
                    "type": "time_router",
                    "name": "Operating Hours Check",
                    "config": {
                        "timezone": "Asia/Kolkata",
                        "schedule": {
                            "mon": { "start": "09:30", "end": "18:30", "enabled": True },
                            "tue": { "start": "09:30", "end": "18:30", "enabled": True },
                            "wed": { "start": "09:30", "end": "18:30", "enabled": True },
                            "thu": { "start": "09:30", "end": "18:30", "enabled": True },
                            "fri": { "start": "09:30", "end": "18:30", "enabled": True },
                            "sat": { "start": "10:00", "end": "16:00", "enabled": True },
                            "sun": "closed"
                        }
                    }
                },
                {
                    "id": "node_greeting_1",
                    "type": "speak_prompt",
                    "name": "Welcome Greeting",
                    "config": {
                        "text": "Welcome to Mynt Real. Please hold while we connect you to our team.",
                        "voice": "Polly.Aditi",
                        "language": "en-IN"
                    }
                },
                {
                    "id": "node_ring_sales_1",
                    "type": "dial_ring_group",
                    "name": "General Inbound Team",
                    "config": {
                        "ring_group_id": 1,
                        "strategy": "simultaneous",
                        "timeout_seconds": 25,
                        "caller_id": did_val
                    }
                },
                {
                    "id": "node_voicemail_1",
                    "type": "voicemail",
                    "name": "After Hours / Missed Voicemail",
                    "config": {
                        "prompt_text": "All agents are currently busy or our offices are closed. Please leave your message after the tone.",
                        "voice": "Polly.Aditi",
                        "max_duration_seconds": 120
                    }
                },
                {
                    "id": "node_hangup_1",
                    "type": "hangup",
                    "name": "End Call",
                    "config": { "reason": "normal" }
                }
            ],
            "edges": [
                { "from": "node_trigger_did_1", "to": "node_time_check_1", "condition": "always" },
                { "from": "node_time_check_1", "to": "node_greeting_1", "condition": "open" },
                { "from": "node_time_check_1", "to": "node_voicemail_1", "condition": "closed" },
                { "from": "node_time_check_1", "to": "node_voicemail_1", "condition": "holiday" },
                { "from": "node_greeting_1", "to": "node_ring_sales_1", "condition": "next" },
                { "from": "node_ring_sales_1", "to": "node_voicemail_1", "condition": "no_answer" },
                { "from": "node_ring_sales_1", "to": "node_hangup_1", "condition": "answered" },
                { "from": "node_voicemail_1", "to": "node_hangup_1", "condition": "recording_saved" }
            ]
        }
