"""
Live Inbound Call Flow Interpreter & Plivo XML Generator — MyntOS Native Telephony
Executes active published Call Flow DAGs during live inbound telecom calls.
Translates graph nodes and decision branches into standard Plivo XML (<Speak>, <GetDigits>, <Dial>, <User>, <Record>, <Hangup>).
Created: Sep 2026
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import pytz
import logging
import re
from xml.sax.saxutils import escape as xml_escape
from sqlalchemy.orm import Session

from app.models.telephony_call_flow import (
    TelephonyCallFlow, TelephonyCallFlowVersion, TelephonyFlowNode,
    TelephonyFlowEdge, TelephonyRingGroup, TelephonyRingGroupMember,
    TelephonyBusinessHours, TelephonyHoliday, TelephonyPlivoEndpoint,
    TelephonyFlowExecutionLog
)
from app.models.operator_calls import TelephonyDIDMapping
from app.models.crm import CRMLead
from app.models.staff import StaffEmployee
from app.models.voip_call_session import VoIPCallSession
from app.models.voip_enums import CallMethodEnum, CallStateEnum

logger = logging.getLogger(__name__)
IST = pytz.timezone('Asia/Kolkata')


class CallFlowInterpreter:
    """
    Stateful execution engine for live Call Flows.
    Compiles flow nodes into clean, compliant Plivo XML.
    """

    MAX_INTERPRETER_STEPS = 20

    @classmethod
    def handle_inbound_call(
        cls,
        db: Session,
        caller_phone: str,
        called_did: str,
        provider_call_id: str,
        base_api_url: str = ""
    ) -> str:
        """
        Primary entry point when Plivo invokes Answer URL.
        1. Resolves DID -> company_id
        2. Resolves active published flow
        3. Initializes VoIPCallSession and FlowExecutionLog
        4. Evaluates flow starting from trigger_did node
        5. Returns Plivo XML
        """
        logger.info(f"[FLOW-INTERPRETER] Inbound call received on DID {called_did} from {caller_phone} (UUID: {provider_call_id})")

        # 1. Resolve Company from DID Mapping or Call Flow DID
        company_id = cls._resolve_company_from_did(db, called_did)
        if not company_id:
            logger.warning(f"[FLOW-INTERPRETER] Unmapped DID {called_did}. Hanging up.")
            return cls._generate_xml_response([
                f'<Speak voice="Polly.Aditi" language="en-IN">Thank you for calling. This number is not currently configured.</Speak>',
                f'<Hangup />'
            ])

        # 2. Find Active Published Call Flow for this DID / Company
        flow = db.query(TelephonyCallFlow).filter(
            TelephonyCallFlow.company_id == company_id,
            TelephonyCallFlow.did_number == called_did,
            TelephonyCallFlow.status == 'published'
        ).first()

        if not flow:
            # Fallback to any active company default flow
            flow = db.query(TelephonyCallFlow).filter(
                TelephonyCallFlow.company_id == company_id,
                TelephonyCallFlow.status == 'published'
            ).order_by(TelephonyCallFlow.id.asc()).first()

        if not flow or not flow.current_published_version_id:
            logger.warning(f"[FLOW-INTERPRETER] No published flow found for company {company_id}.")
            return cls._generate_xml_response([
                f'<Speak voice="Polly.Aditi" language="en-IN">Welcome to Mynt Real. No active call routing flow is configured. Please try again later.</Speak>',
                f'<Hangup />'
            ])

        # 3. Fetch Published Version
        flow_version = db.query(TelephonyCallFlowVersion).filter(
            TelephonyCallFlowVersion.id == flow.current_published_version_id
        ).first()

        if not flow_version or not flow_version.flow_data:
            return cls._generate_xml_response([
                f'<Speak voice="Polly.Aditi">Error loading call flow version.</Speak>',
                f'<Hangup />'
            ])

        # 4. Create/Upsert VoIPCallSession & FlowExecutionLog
        session_id = f"vcs_in_{provider_call_id[-12:]}"
        session = db.query(VoIPCallSession).filter(VoIPCallSession.call_session_id == session_id).first()
        if not session:
            session = VoIPCallSession(
                company_id=company_id,
                call_session_id=session_id,
                provider='plivo',
                provider_call_id=provider_call_id,
                caller_id=called_did,
                customer_phone=caller_phone,
                destination_number=caller_phone,
                direction='inbound',
                call_method=CallMethodEnum.IN_APP_PSTN.value,
                status=CallStateEnum.RINGING.value
            )
            db.add(session)

        exec_log = TelephonyFlowExecutionLog(
            call_session_id=session_id,
            company_id=company_id,
            flow_id=flow.id,
            flow_version_id=flow_version.id,
            caller_phone=caller_phone,
            did_number=called_did,
            current_node_key="entry",
            traversed_nodes=[],
            final_outcome="in_progress"
        )
        db.add(exec_log)
        db.commit()

        # 5. Begin Traversal from Entry Node
        return cls._execute_flow_node(
            db=db,
            flow_data=flow_version.flow_data,
            company_id=company_id,
            caller_phone=caller_phone,
            called_did=called_did,
            call_session_id=session_id,
            provider_call_id=provider_call_id,
            current_node_key=None,  # Start at root
            dtmf_input=None,
            exec_log=exec_log,
            base_api_url=base_api_url
        )

    @classmethod
    def handle_flow_step(
        cls,
        db: Session,
        call_session_id: str,
        current_node_key: str,
        dtmf_input: Optional[str],
        base_api_url: str = ""
    ) -> str:
        """
        Continuation callback when Plivo submits DTMF digits or step action.
        """
        logger.info(f"[FLOW-INTERPRETER] Step continuation for {call_session_id} at {current_node_key} (Digits: {dtmf_input})")

        exec_log = db.query(TelephonyFlowExecutionLog).filter(
            TelephonyFlowExecutionLog.call_session_id == call_session_id
        ).order_by(TelephonyFlowExecutionLog.id.desc()).first()

        if not exec_log:
            logger.error(f"[FLOW-INTERPRETER] Execution log missing for {call_session_id}")
            return cls._generate_xml_response([f'<Hangup />'])

        flow_version = db.query(TelephonyCallFlowVersion).filter(
            TelephonyCallFlowVersion.id == exec_log.flow_version_id
        ).first()

        if not flow_version or not flow_version.flow_data:
            return cls._generate_xml_response([f'<Hangup />'])

        return cls._execute_flow_node(
            db=db,
            flow_data=flow_version.flow_data,
            company_id=exec_log.company_id,
            caller_phone=exec_log.caller_phone,
            called_did=exec_log.did_number or "",
            call_session_id=call_session_id,
            provider_call_id="",
            current_node_key=current_node_key,
            dtmf_input=dtmf_input,
            exec_log=exec_log,
            base_api_url=base_api_url
        )

    @classmethod
    def _execute_flow_node(
        cls,
        db: Session,
        flow_data: Dict[str, Any],
        company_id: int,
        caller_phone: str,
        called_did: str,
        call_session_id: str,
        provider_call_id: str,
        current_node_key: Optional[str],
        dtmf_input: Optional[str],
        exec_log: TelephonyFlowExecutionLog,
        base_api_url: str
    ) -> str:
        """
        Internal recursive/iterative node processor compiling to Plivo XML.
        """
        nodes_list = flow_data.get('nodes', [])
        edges_list = flow_data.get('edges', [])
        node_map = { (n.get('id') or n.get('node_key')): n for n in nodes_list }

        # Build outgoing edge index
        outgoing_edges: Dict[str, List[Dict[str, Any]]] = {}
        for edge in edges_list:
            src = (edge.get('from') or edge.get('source') or edge.get('source_node') or edge.get('source_node_key') or '').strip()
            if src not in outgoing_edges:
                outgoing_edges[src] = []
            outgoing_edges[src].append(edge)

        # Locate starting node
        if not current_node_key:
            for n_key, n_val in node_map.items():
                if (n_val.get('type') or n_val.get('node_type')) == 'trigger_did':
                    current_node_key = n_key
                    break
            if not current_node_key and nodes_list:
                current_node_key = nodes_list[0].get('id') or nodes_list[0].get('node_key')

        step_count = 0
        xml_elements: List[str] = []
        now_ist = datetime.now(IST)

        # Lookup CRM Lead
        clean_phone = re.sub(r'[^\d]', '', caller_phone)[-10:]
        crm_lead = db.query(CRMLead).filter(
            CRMLead.company_id == company_id,
            (CRMLead.phone.ilike(f"%{clean_phone}%") | CRMLead.alternate_phone.ilike(f"%{clean_phone}%"))
        ).first()

        traversed_history = list(exec_log.traversed_nodes or [])

        while current_node_key and step_count < cls.MAX_INTERPRETER_STEPS:
            step_count += 1
            curr_node = node_map.get(current_node_key)
            if not curr_node:
                break

            n_type = curr_node.get('type') or curr_node.get('node_type')
            n_name = curr_node.get('name', current_node_key)
            n_cfg = curr_node.get('config', {})

            traversed_history.append({
                'node_key': current_node_key,
                'node_name': n_name,
                'node_type': n_type,
                'time': now_ist.strftime('%H:%M:%S')
            })
            exec_log.current_node_key = current_node_key
            exec_log.traversed_nodes = traversed_history

            next_condition = 'always'
            requires_telecom_action = False

            # ── 1. TRIGGER DID ───────────────────────────────────────────────
            if n_type == 'trigger_did':
                next_condition = 'always'

            # ── 2. TIME ROUTER ───────────────────────────────────────────────
            elif n_type == 'time_router':
                is_open, reason = cls._evaluate_business_hours(db, company_id, n_cfg, now_ist)
                next_condition = 'open' if is_open else ('holiday' if 'holiday' in reason.lower() else 'closed')
                logger.info(f"[FLOW-INTERPRETER] Time router evaluated: {reason} -> '{next_condition}'")

            # ── 3. CALLER LOOKUP ─────────────────────────────────────────────
            elif n_type == 'caller_lookup':
                has_owner = bool(crm_lead and (crm_lead.telecaller_id or crm_lead.primary_owner_id))
                next_condition = 'assigned_owner' if has_owner else 'unassigned_or_generic'

            # ── 4. SPEAK PROMPT ──────────────────────────────────────────────
            elif n_type == 'speak_prompt':
                text = xml_escape(n_cfg.get('text', ''))
                voice = n_cfg.get('voice', 'Polly.Aditi')
                lang = n_cfg.get('language', 'en-IN')
                xml_elements.append(f'<Speak voice="{voice}" language="{lang}">{text}</Speak>')
                next_condition = 'next'

            # ── 5. PLAY AUDIO ────────────────────────────────────────────────
            elif n_type == 'play_audio':
                url = xml_escape(n_cfg.get('audio_url', ''))
                xml_elements.append(f'<Play>{url}</Play>')
                next_condition = 'next'

            # ── 6. IVR MENU ──────────────────────────────────────────────────
            elif n_type == 'ivr_menu':
                if dtmf_input is not None:
                    # We are processing digits returned from previous step
                    next_condition = f"digit_{dtmf_input}"
                    dtmf_input = None  # Consumed
                else:
                    # Generate Plivo <GetDigits>
                    prompt = xml_escape(n_cfg.get('text', 'Please select an option.'))
                    voice = n_cfg.get('voice', 'Polly.Aditi')
                    lang = n_cfg.get('language', 'en-IN')
                    timeout = n_cfg.get('timeout_seconds', 6)
                    num_digits = n_cfg.get('num_digits', 1)
                    retries = n_cfg.get('max_retries', 2)

                    action_url = f"{base_api_url}/api/v1/telephony/plivo/flow-step?session_id={call_session_id}&amp;node_key={current_node_key}"
                    xml_elements.append(
                        f'<GetDigits action="{action_url}" method="POST" timeout="{timeout}" numDigits="{num_digits}" retries="{retries}">'
                        f'<Speak voice="{voice}" language="{lang}">{prompt}</Speak>'
                        f'</GetDigits>'
                    )
                    # Add timeout redirect
                    xml_elements.append(
                        f'<Redirect method="POST">{action_url}&amp;Digits=timeout</Redirect>'
                    )
                    requires_telecom_action = True
                    break

            # ── 7. DIAL USER ─────────────────────────────────────────────────
            elif n_type == 'dial_user':
                staff_id = n_cfg.get('staff_id')
                endpoint_uri = cls._resolve_staff_sip_endpoint(db, company_id, staff_id)
                timeout = n_cfg.get('timeout_seconds', 25)
                caller_id_val = called_did or n_cfg.get('caller_id', '+918031728899')
                action_url = f"{base_api_url}/api/v1/telephony/plivo/dial-action?session_id={call_session_id}&amp;node_key={current_node_key}"

                xml_elements.append(
                    f'<Dial timeout="{timeout}" callerId="{caller_id_val}" action="{action_url}" method="POST">'
                    f'<User>{endpoint_uri}</User>'
                    f'</Dial>'
                )
                exec_log.selected_destination = f"User #{staff_id}"
                exec_log.connected_staff_id = staff_id
                requires_telecom_action = True
                break

            # ── 8. DIAL RING GROUP ───────────────────────────────────────────
            elif n_type == 'dial_ring_group':
                rg_id = n_cfg.get('ring_group_id')
                endpoints = cls._resolve_ring_group_endpoints(db, company_id, rg_id)
                timeout = n_cfg.get('timeout_seconds', 25)
                caller_id_val = called_did or n_cfg.get('caller_id', '+918031728899')
                action_url = f"{base_api_url}/api/v1/telephony/plivo/dial-action?session_id={call_session_id}&amp;node_key={current_node_key}"

                if endpoints:
                    user_tags = "".join([f"<User>{ep}</User>" for ep in endpoints])
                    xml_elements.append(
                        f'<Dial timeout="{timeout}" callerId="{caller_id_val}" action="{action_url}" method="POST">'
                        f'{user_tags}'
                        f'</Dial>'
                    )
                else:
                    logger.warning(f"[FLOW-INTERPRETER] No active endpoints in ring group {rg_id}. Proceeding to fallback.")
                    next_condition = 'no_answer'

                exec_log.selected_destination = f"Ring Group #{rg_id} ({len(endpoints)} agents)"
                if endpoints:
                    requires_telecom_action = True
                    break

            # ── 9. VOICEMAIL ─────────────────────────────────────────────────
            elif n_type == 'voicemail':
                prompt = xml_escape(n_cfg.get('prompt_text', 'Please leave a message after the tone.'))
                voice = n_cfg.get('voice', 'Polly.Aditi')
                max_len = n_cfg.get('max_duration_seconds', 120)
                finish_key = n_cfg.get('finish_on_key', '#')
                rec_action = f"{base_api_url}/api/v1/telephony/plivo/recording-callback?session_id={call_session_id}"

                xml_elements.append(f'<Speak voice="{voice}">{prompt}</Speak>')
                xml_elements.append(f'<Record action="{rec_action}" method="POST" maxLength="{max_len}" finishOnKey="{finish_key}" playBeep="true" />')
                exec_log.final_outcome = "voicemail"
                requires_telecom_action = True
                break

            # ── 10. FORWARD PSTN ─────────────────────────────────────────────
            elif n_type == 'forward_pstn':
                dest = n_cfg.get('destination_phone', '')
                caller_id_val = called_did or n_cfg.get('caller_id', '+918031728899')
                xml_elements.append(
                    f'<Dial callerId="{caller_id_val}">'
                    f'<Number>{dest}</Number>'
                    f'</Dial>'
                )
                exec_log.selected_destination = f"PSTN Forward: {dest}"
                requires_telecom_action = True
                break

            # ── 11. HANGUP ───────────────────────────────────────────────────
            elif n_type == 'hangup':
                xml_elements.append('<Hangup />')
                exec_log.final_outcome = "hangup"
                requires_telecom_action = True
                break

            # Resolve next node via edges
            node_outs = outgoing_edges.get(current_node_key, [])
            matched_edge = None

            for e in node_outs:
                c = (e.get('condition') or 'always').strip().lower()
                if c == next_condition.lower():
                    matched_edge = e
                    break

            if not matched_edge and next_condition.startswith('digit_'):
                d_val = next_condition.split('_')[1]
                for e in node_outs:
                    c = (e.get('condition') or '').strip().lower()
                    if c in (d_val, f"key_{d_val}", f"digit_{d_val}"):
                        matched_edge = e
                        break

            if not matched_edge and next_condition in ('timeout', 'invalid', 'no_answer'):
                for e in node_outs:
                    c = (e.get('condition') or '').strip().lower()
                    if c in ('timeout', 'invalid', 'fallback', 'timeout_or_invalid', 'no_answer', 'default'):
                        matched_edge = e
                        break

            if not matched_edge:
                for e in node_outs:
                    c = (e.get('condition') or '').strip().lower()
                    if c in ('always', 'next', 'default', ''):
                        matched_edge = e
                        break

            if matched_edge:
                current_node_key = (matched_edge.get('to') or matched_edge.get('target') or matched_edge.get('target_node') or matched_edge.get('target_node_key') or '').strip()
            else:
                current_node_key = None

        db.commit()
        return cls._generate_xml_response(xml_elements)

    @classmethod
    def _generate_xml_response(cls, elements: List[str]) -> str:
        body = "\n  ".join(elements) if elements else "<Hangup />"
        return f'<Response>\n  {body}\n</Response>'

    @classmethod
    def _resolve_company_from_did(cls, db: Session, did_number: str) -> Optional[int]:
        """
        Resolves tenant company_id from DID Mapping table or explicit Call Flow association.
        Returns None if the DID is unmapped, ensuring strict multi-tenant isolation.
        """
        if not did_number:
            return None
        clean_did = re.sub(r'[^\d+]', '', did_number)
        if not clean_did:
            return None

        # 1. Check primary telephony_did_mappings table
        mapping = db.query(TelephonyDIDMapping).filter(
            (TelephonyDIDMapping.did_number == clean_did) | (TelephonyDIDMapping.did_number.ilike(f"%{clean_did[-10:]}%")),
            TelephonyDIDMapping.is_active == True
        ).first()
        if mapping:
            return mapping.company_id

        # 2. Check explicit Call Flow did_number binding
        flow = db.query(TelephonyCallFlow).filter(
            TelephonyCallFlow.did_number.ilike(f"%{clean_did[-10:]}%")
        ).first()
        if flow:
            return flow.company_id

        return None

    @classmethod
    def _resolve_staff_sip_endpoint(cls, db: Session, company_id: int, staff_id: int) -> str:
        """Resolves real mapped Plivo SIP endpoint or constructs company-scoped endpoint"""
        endpoint = db.query(TelephonyPlivoEndpoint).filter(
            TelephonyPlivoEndpoint.company_id == company_id,
            TelephonyPlivoEndpoint.staff_id == staff_id
        ).first()
        if endpoint and endpoint.plivo_username:
            return f"sip:{endpoint.plivo_username}@phone.plivo.com"
        return f"sip:agent_c{company_id}_s{staff_id}@phone.plivo.com"

    @classmethod
    def _resolve_ring_group_endpoints(cls, db: Session, company_id: int, ring_group_id: int) -> List[str]:
        """Resolves all available agent SIP endpoints in a ring group"""
        members = db.query(TelephonyRingGroupMember).filter(
            TelephonyRingGroupMember.ring_group_id == ring_group_id,
            TelephonyRingGroupMember.is_active == True
        ).order_by(TelephonyRingGroupMember.priority_order.asc()).all()

        endpoints = []
        for m in members:
            ep = cls._resolve_staff_sip_endpoint(db, company_id, m.staff_id)
            endpoints.append(ep)
        return endpoints

    @classmethod
    def _evaluate_business_hours(
        cls,
        db: Session,
        company_id: int,
        config: Dict[str, Any],
        now_dt: datetime
    ) -> Tuple[bool, str]:
        """Evaluates weekly schedule and holiday table"""
        date_str = now_dt.strftime('%Y-%m-%d')
        weekday_key = now_dt.strftime('%a').lower()[:3]
        time_str = now_dt.strftime('%H:%M')

        # Check Holiday table
        holiday = db.query(TelephonyHoliday).filter(
            TelephonyHoliday.company_id == company_id,
            TelephonyHoliday.holiday_date == date_str,
            TelephonyHoliday.is_active == True
        ).first()
        if holiday:
            return False, f"Holiday: {holiday.name}"

        # Check Business Hours table
        bh = db.query(TelephonyBusinessHours).filter(
            TelephonyBusinessHours.company_id == company_id,
            TelephonyBusinessHours.is_active == True
        ).first()

        schedule = (bh.schedule_data if bh else None) or config.get('schedule', {})
        if not schedule:
            if weekday_key in ('mon', 'tue', 'wed', 'thu', 'fri') and "09:30" <= time_str <= "18:30":
                return True, "Standard Business Hours"
            return False, "After Hours"

        day_cfg = schedule.get(weekday_key, {})
        if not day_cfg or day_cfg == 'closed' or day_cfg.get('enabled') is False:
            return False, "Closed today"

        open_t = day_cfg.get('start', '09:30')
        close_t = day_cfg.get('end', '18:30')
        if open_t <= time_str <= close_t:
            return True, f"Open ({open_t}-{close_t})"
        return False, f"Closed ({open_t}-{close_t})"

    @classmethod
    def _mask_phone(cls, phone: str) -> str:
        clean = re.sub(r'[^\d]', '', phone)
        if len(clean) >= 4:
            return f"******{clean[-4:]}"
        return "******"
