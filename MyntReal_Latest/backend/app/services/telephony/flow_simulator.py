"""
Call Flow Simulator & Trace Engine — MyntOS Native Telephony
Simulates inbound call traversal through a Call Flow DAG without placing real telecom calls.
Evaluates time rules, DTMF paths, agent ring resolutions, and fallbacks to generate an exact execution trace.
Created: Sep 2026
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import pytz
import logging
from sqlalchemy.orm import Session

from app.models.telephony_call_flow import (
    TelephonyCallFlow, TelephonyCallFlowVersion, TelephonyRingGroup,
    TelephonyRingGroupMember, TelephonyBusinessHours, TelephonyHoliday,
    TelephonyPlivoEndpoint
)
from app.models.crm import CRMLead
from app.models.staff import StaffEmployee

logger = logging.getLogger(__name__)
IST = pytz.timezone('Asia/Kolkata')


class CallFlowSimulator:
    """
    Simulates execution of a Call Flow graph for testing and pre-flight validation.
    """

    MAX_SIMULATION_STEPS = 25  # Safeguard against infinite loops

    @classmethod
    def simulate_flow(
        cls,
        db: Session,
        flow_data: Dict[str, Any],
        company_id: int,
        caller_phone: str = "+919876543210",
        simulated_datetime: Optional[datetime] = None,
        dtmf_inputs: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Execute dry-run simulation of flow graph.
        Returns execution trace, final destination, and decision log.
        """
        if simulated_datetime is None:
            simulated_datetime = datetime.now(IST)
        elif simulated_datetime.tzinfo is None:
            simulated_datetime = IST.localize(simulated_datetime)

        dtmf_queue = list(dtmf_inputs or [])
        nodes_list = flow_data.get('nodes', [])
        edges_list = flow_data.get('edges', [])

        node_map = { (n.get('id') or n.get('node_key')): n for n in nodes_list }
        
        # Build outgoing edge index: src_key -> list of edges
        outgoing_edges: Dict[str, List[Dict[str, Any]]] = {}
        for edge in edges_list:
            src = (edge.get('from') or edge.get('source_node') or edge.get('source_node_key') or '').strip()
            if src not in outgoing_edges:
                outgoing_edges[src] = []
            outgoing_edges[src].append(edge)

        # 1. Locate entry node
        entry_node_key = None
        for n_key, n_val in node_map.items():
            if (n_val.get('type') or n_val.get('node_type')) == 'trigger_did':
                entry_node_key = n_key
                break

        if not entry_node_key and nodes_list:
            entry_node_key = nodes_list[0].get('id') or nodes_list[0].get('node_key')

        if not entry_node_key:
            return {
                'success': False,
                'error': 'No entry node found in flow graph',
                'steps': [],
                'final_outcome': 'error'
            }

        trace_steps: List[Dict[str, Any]] = []
        current_node_key = entry_node_key
        step_count = 0
        final_destination = None
        final_outcome = 'in_progress'

        # Lookup CRM lead context for simulation
        crm_lead = db.query(CRMLead).filter(
            CRMLead.company_id == company_id,
            CRMLead.phone.ilike(f"%{caller_phone[-10:]}%")
        ).first() if db else None

        while current_node_key and step_count < cls.MAX_SIMULATION_STEPS:
            step_count += 1
            curr_node = node_map.get(current_node_key)
            if not curr_node:
                trace_steps.append({
                    'step': step_count,
                    'node_key': current_node_key,
                    'node_name': 'Unknown Node',
                    'node_type': 'unknown',
                    'decision': 'Node not found in graph',
                    'status': 'error'
                })
                final_outcome = 'error'
                break

            n_type = curr_node.get('type') or curr_node.get('node_type')
            n_name = curr_node.get('name', current_node_key)
            n_cfg = curr_node.get('config', {})

            step_record = {
                'step': step_count,
                'node_key': current_node_key,
                'node_name': n_name,
                'node_type': n_type,
                'details': {},
                'decision': '',
                'next_node_key': None
            }

            next_node_key = None
            next_condition = 'always'

            # ── EVALUATE NODE TYPE ──────────────────────────────────────────
            if n_type == 'trigger_did':
                did = n_cfg.get('did_number', 'Default DID')
                step_record['details'] = {
                    'did': did,
                    'caller_phone': caller_phone,
                    'matched_lead': {
                        'id': crm_lead.id,
                        'name': crm_lead.name,
                        'owner_id': crm_lead.telecaller_id or crm_lead.primary_owner_id
                    } if crm_lead else None
                }
                step_record['decision'] = f'Call received on DID {did} from {caller_phone}'
                next_condition = 'always'

            elif n_type == 'time_router':
                is_open, reason = cls._check_business_hours(db, company_id, n_cfg, simulated_datetime)
                cond_to_match = 'open' if is_open else ('holiday' if 'holiday' in reason.lower() else 'closed')
                step_record['details'] = {
                    'simulated_time': simulated_datetime.strftime('%Y-%m-%d %H:%M:%S %Z'),
                    'day_of_week': simulated_datetime.strftime('%A'),
                    'status': 'OPEN' if is_open else 'CLOSED',
                    'reason': reason
                }
                step_record['decision'] = f"Business Hours Check: {reason} -> Branching to '{cond_to_match}'"
                next_condition = cond_to_match

            elif n_type == 'caller_lookup':
                has_owner = bool(crm_lead and (crm_lead.telecaller_id or crm_lead.primary_owner_id))
                cond_to_match = 'assigned_owner' if has_owner else 'unassigned_or_generic'
                step_record['details'] = {
                    'lead_found': bool(crm_lead),
                    'lead_id': crm_lead.id if crm_lead else None,
                    'assigned_owner_id': (crm_lead.telecaller_id or crm_lead.primary_owner_id) if crm_lead else None
                }
                step_record['decision'] = f"Caller lookup resolved: {cond_to_match}"
                next_condition = cond_to_match

            elif n_type == 'speak_prompt':
                prompt_text = n_cfg.get('text', '')
                voice = n_cfg.get('voice', 'Polly.Aditi')
                step_record['details'] = {'text': prompt_text, 'voice': voice}
                step_record['decision'] = f'Spoken Prompt: "{prompt_text[:50]}..."'
                next_condition = 'next'

            elif n_type == 'play_audio':
                url = n_cfg.get('audio_url', '')
                step_record['details'] = {'audio_url': url}
                step_record['decision'] = f'Audio File Played: {url}'
                next_condition = 'next'

            elif n_type == 'ivr_menu':
                prompt = n_cfg.get('text', '')
                digit = dtmf_queue.pop(0) if dtmf_queue else None
                step_record['details'] = {
                    'prompt': prompt,
                    'simulated_digit_pressed': digit
                }
                if digit:
                    step_record['decision'] = f'IVR Menu: Caller pressed digit "{digit}"'
                    next_condition = f'digit_{digit}'
                else:
                    step_record['decision'] = 'IVR Menu: No DTMF provided -> Triggering timeout/fallback'
                    next_condition = 'timeout'

            elif n_type == 'dial_user':
                staff_id = n_cfg.get('staff_id')
                staff_member = db.query(StaffEmployee).filter(StaffEmployee.id == staff_id).first() if db and staff_id else None
                step_record['details'] = {
                    'staff_id': staff_id,
                    'staff_name': staff_member.full_name if staff_member else f'Staff #{staff_id}',
                    'sip_endpoint': f'sip:agent_{company_id}_{staff_id}@phone.plivo.com'
                }
                step_record['decision'] = f'Ringing Agent: {staff_member.full_name if staff_member else staff_id}'
                final_destination = f'Agent: {staff_member.full_name if staff_member else staff_id}'
                final_outcome = 'connected'

            elif n_type == 'dial_ring_group':
                rg_id = n_cfg.get('ring_group_id')
                ring_group = db.query(TelephonyRingGroup).filter(TelephonyRingGroup.id == rg_id).first() if db and rg_id else None
                members = db.query(TelephonyRingGroupMember).filter(TelephonyRingGroupMember.ring_group_id == rg_id).all() if db and rg_id else []
                step_record['details'] = {
                    'ring_group_id': rg_id,
                    'ring_group_name': ring_group.name if ring_group else f'Ring Group #{rg_id}',
                    'strategy': ring_group.strategy if ring_group else n_cfg.get('strategy', 'simultaneous'),
                    'members_count': len(members)
                }
                group_display_name = ring_group.name if ring_group else (n_name if n_name and n_name != current_node_key else f'Group #{rg_id}')
                step_record['decision'] = f"Ringing Ring Group: {group_display_name} ({len(members)} agents)"
                final_destination = f"Ring Group: {group_display_name}"
                final_outcome = 'connected'

            elif n_type == 'voicemail':
                step_record['details'] = {
                    'prompt': n_cfg.get('prompt_text', 'Leave message after beep'),
                    'max_seconds': n_cfg.get('max_duration_seconds', 120)
                }
                step_record['decision'] = 'Voicemail Recording Prompt Activated'
                final_destination = 'Voicemail Box'
                final_outcome = 'voicemail_recorded'

            elif n_type == 'forward_pstn':
                dest = n_cfg.get('destination_phone', '')
                step_record['details'] = {'destination_phone': dest}
                step_record['decision'] = f'PSTN External Forward to {dest}'
                final_destination = f'External: {dest}'
                final_outcome = 'forwarded'

            elif n_type == 'hangup':
                step_record['details'] = {'reason': n_cfg.get('reason', 'normal')}
                step_record['decision'] = 'Call Gracefully Terminated'
                final_destination = 'Hung Up'
                final_outcome = 'hangup'

            # ── RESOLVE NEXT NODE VIA EDGES ─────────────────────────────────
            node_outs = outgoing_edges.get(current_node_key, [])
            matched_edge = None

            # Priority 1: Exact condition match
            for e in node_outs:
                c = (e.get('condition') or 'always').strip().lower()
                if c == next_condition.lower():
                    matched_edge = e
                    break

            # Priority 2: Digit variation matching (e.g. "1" matches "digit_1" or "key_1")
            if not matched_edge and next_condition.startswith('digit_'):
                d_val = next_condition.split('_')[1]
                for e in node_outs:
                    c = (e.get('condition') or '').strip().lower()
                    if c in (d_val, f"key_{d_val}", f"digit_{d_val}"):
                        matched_edge = e
                        break

            # Priority 3: Fallback / Timeout matching
            if not matched_edge and next_condition in ('timeout', 'invalid'):
                for e in node_outs:
                    c = (e.get('condition') or '').strip().lower()
                    if c in ('timeout', 'invalid', 'fallback', 'timeout_or_invalid', 'default'):
                        matched_edge = e
                        break

            # Priority 4: Always / Next matching
            if not matched_edge:
                for e in node_outs:
                    c = (e.get('condition') or '').strip().lower()
                    if c in ('always', 'next', 'default', ''):
                        matched_edge = e
                        break

            if matched_edge:
                next_node_key = (matched_edge.get('to') or matched_edge.get('target_node') or matched_edge.get('target_node_key') or '').strip()
                step_record['next_node_key'] = next_node_key
            else:
                next_node_key = None

            trace_steps.append(step_record)

            # If node is terminal or has no next node, finish simulation
            if n_type in ('dial_user', 'dial_ring_group', 'voicemail', 'forward_pstn', 'hangup') or not next_node_key:
                break

            current_node_key = next_node_key

        return {
            'success': True,
            'total_steps': len(trace_steps),
            'caller_phone': caller_phone,
            'simulated_time': simulated_datetime.strftime('%Y-%m-%d %H:%M:%S %Z'),
            'final_destination': final_destination or 'End of Flow',
            'final_outcome': final_outcome,
            'steps': trace_steps
        }

    @classmethod
    def _check_business_hours(
        cls,
        db: Session,
        company_id: int,
        config: Dict[str, Any],
        sim_time: datetime
    ) -> Tuple[bool, str]:
        """Evaluate if simulated datetime falls within operating business hours"""
        date_str = sim_time.strftime('%Y-%m-%d')
        weekday_key = sim_time.strftime('%a').lower()[:3]  # mon, tue, wed, thu, fri, sat, sun
        current_time_str = sim_time.strftime('%H:%M')

        # 1. Check holiday calendar in database
        if db:
            holiday = db.query(TelephonyHoliday).filter(
                TelephonyHoliday.company_id == company_id,
                TelephonyHoliday.holiday_date == date_str,
                TelephonyHoliday.is_active == True
            ).first()
            if holiday:
                return False, f"Holiday: {holiday.name}"

        # 2. Check inline holidays in config
        holidays_list = config.get('holidays', [])
        if date_str in holidays_list:
            return False, f"Holiday calendar match ({date_str})"

        # 3. Check schedule in config or DB
        schedule = config.get('schedule', {})
        if not schedule and db:
            bh_record = db.query(TelephonyBusinessHours).filter(
                TelephonyBusinessHours.company_id == company_id,
                TelephonyBusinessHours.is_active == True
            ).first()
            if bh_record and bh_record.schedule_data:
                schedule = bh_record.schedule_data

        if not schedule:
            # Default standard MyntOS calling hours: 09:00 - 20:00 Monday to Sunday
            if "09:00" <= current_time_str <= "20:00":
                return True, "Standard Calling Window (09:00-20:00 IST)"
            return False, "After hours (outside 09:00-20:00 IST)"

        day_sched = schedule.get(weekday_key) or schedule.get(f"{weekday_key}_hours")
        if not day_sched or day_sched == 'closed' or day_sched.get('enabled') is False:
            return False, f"Closed on {sim_time.strftime('%A')}"

        open_time = day_sched.get('start') or day_sched.get('open', '09:30')
        close_time = day_sched.get('end') or day_sched.get('close', '18:30')

        if open_time <= current_time_str <= close_time:
            return True, f"Within business hours ({open_time} - {close_time})"
        return False, f"Outside business hours ({open_time} - {close_time})"
