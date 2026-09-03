"""
Live Inbound Call Flow Interpreter & Plivo XML Generator — MyntOS Native Telephony
Executes active published Call Flow DAGs during live inbound telecom calls.
Translates graph nodes and decision branches into standard Plivo XML (<Speak>, <GetDigits>, <Dial>, <User>, <Record>, <Hangup>).
Created: Sep 2026
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import os
import pytz
import logging
import re
from xml.sax.saxutils import escape as xml_escape
from sqlalchemy.orm import Session

from app.core.config import settings
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
        base_api_url: str = "",
        call_session_id: str = ""
    ) -> str:
        """
        Primary entry point when Plivo invokes Answer URL.
        1. Checks if outbound browser call (WebRTC SIP -> Customer)
        2. Resolves DID -> company_id
        3. Evaluates inbound IVR flow
        4. Returns Plivo XML
        """
        logger.info(f"[FLOW-INTERPRETER] Call received on DID/Destination '{called_did}' from '{caller_phone}' (UUID: {provider_call_id}, Session: {call_session_id})")

        # 0. Robust Detection for Outbound Browser Softphone Calling (WebRTC SIP Leg -> Customer PSTN)
        caller_str = str(caller_phone or '').strip()
        called_str = str(called_did or '').strip()

        is_sip_caller = (
            caller_str.startswith('sip:') or 
            '@' in caller_str or 
            'agent' in caller_str.lower() or 
            not caller_str.replace('+', '').isdigit() or
            len(re.sub(r'\D', '', caller_str)) < 10
        )

        clean_dest = re.sub(r'[^\d+]', '', called_str)
        if not clean_dest.startswith('+'):
            digits_only = re.sub(r'[^\d]', '', clean_dest)
            clean_dest = f"+91{digits_only[-10:]}" if len(digits_only) >= 10 else f"+{digits_only}"

        outbound_caller_id = (
            getattr(settings, 'PLIVO_DEFAULT_CALLER_ID', None) or 
            os.getenv("PLIVO_DEFAULT_CALLER_ID", "+918031728899")
        )

        if is_sip_caller:
            logger.info(f"[FLOW-INTERPRETER] Bridging Outbound WebRTC call from {caller_str} to customer {clean_dest} with callerId {outbound_caller_id}")
            return cls._generate_xml_response([
                f'<Dial callerId="{outbound_caller_id}">',
                f'  <Number>{clean_dest}</Number>',
                f'</Dial>'
            ])

        # Check if called number is an incoming company DID or an outbound customer number
        clean_called = re.sub(r'\D', '', called_str)
        is_inbound_did = False
        try:
            if clean_called:
                did_exists = db.query(TelephonyDIDMapping).filter(
                    TelephonyDIDMapping.did_number.ilike(f"%{clean_called[-10:]}%"),
                    TelephonyDIDMapping.is_active == True
                ).first()
                if did_exists:
                    is_inbound_did = True
        except Exception as e:
            logger.warning(f"[FLOW-INTERPRETER] DID lookup error: {e}")

        if not is_inbound_did:
            # Dynamically resolve registered staff Plivo endpoint from DB
            operator_sip = None
            ep_rec = None
            try:
                # 1. Locate VoIPCallSession
                session_obj = None
                if call_session_id:
                    session_obj = db.query(VoIPCallSession).filter(VoIPCallSession.call_session_id == call_session_id).first()
                if not session_obj and provider_call_id:
                    session_obj = db.query(VoIPCallSession).filter(VoIPCallSession.provider_call_id == provider_call_id).first()
                if not session_obj and clean_dest:
                    session_obj = db.query(VoIPCallSession).filter(
                        VoIPCallSession.customer_phone == clean_dest,
                        VoIPCallSession.direction == 'outbound'
                    ).order_by(VoIPCallSession.id.desc()).first()

                op_id = session_obj.operator_id if session_obj else None
                comp_id = session_obj.company_id if session_obj else None

                # 2. Match exact TelephonyPlivoEndpoint
                if op_id and comp_id:
                    ep_rec = db.query(TelephonyPlivoEndpoint).filter(
                        TelephonyPlivoEndpoint.staff_id == op_id,
                        TelephonyPlivoEndpoint.company_id == comp_id
                    ).first()

                if not ep_rec and op_id:
                    ep_rec = db.query(TelephonyPlivoEndpoint).filter(
                        TelephonyPlivoEndpoint.staff_id == op_id
                    ).order_by(TelephonyPlivoEndpoint.is_registered.desc(), TelephonyPlivoEndpoint.id.desc()).first()

                if not ep_rec and comp_id:
                    ep_rec = db.query(TelephonyPlivoEndpoint).filter(
                        TelephonyPlivoEndpoint.company_id == comp_id
                    ).order_by(TelephonyPlivoEndpoint.is_registered.desc(), TelephonyPlivoEndpoint.id.desc()).first()

                if not ep_rec:
                    ep_rec = db.query(TelephonyPlivoEndpoint).filter(
                        TelephonyPlivoEndpoint.is_registered == True
                    ).order_by(TelephonyPlivoEndpoint.id.desc()).first()

                if ep_rec and ep_rec.plivo_username:
                    operator_sip = f"sip:{ep_rec.plivo_username}@phone.plivo.com"
            except Exception as e:
                logger.warning(f"[FLOW-INTERPRETER] Dynamic endpoint lookup error: {e}")

            agent_phone = None
            if op_id:
                staff_user = db.query(StaffEmployee).filter(StaffEmployee.id == op_id).first()
                if staff_user and staff_user.phone:
                    clean_ag_phone = re.sub(r'[^\d+]', '', str(staff_user.phone))
                    if not clean_ag_phone.startswith('+'):
                        clean_ag_phone = f"+91{clean_ag_phone[-10:]}"
                    agent_phone = clean_ag_phone

            if operator_sip:
                logger.info(
                    f"[FLOW-INTERPRETER] Outbound call to customer {clean_dest} answered. Bridging to agent SIP {operator_sip} "
                    f"with callerId {outbound_caller_id}"
                )
                return cls._generate_xml_response([
                    f'<Dial callerId="{outbound_caller_id}">',
                    f'  <User>{operator_sip}</User>',
                    f'</Dial>'
                ])
            elif agent_phone:
                logger.info(
                    f"[FLOW-INTERPRETER] Outbound call to customer {clean_dest} answered. Bridging to agent phone {agent_phone} "
                    f"with callerId {outbound_caller_id}"
                )
                return cls._generate_xml_response([
                    f'<Dial callerId="{outbound_caller_id}">',
                    f'  <Number>{agent_phone}</Number>',
                    f'</Dial>'
                ])
            else:
                return cls._generate_xml_response([
                    f'<Speak voice="Polly.Aditi" language="en-IN">Connecting your call with Mynt Real staff. Please hold the line.</Speak>',
                    f'<Wait length="30" />'
                ])

        # 1. Resolve Company from DID
        company_id = cls._resolve_company_from_did(db, called_did) or 1

        # 2. Check Sticky-Agent Routing (Repeat caller returning call to previous staff within 7 days)
        sticky_agent_xml = cls._check_sticky_agent(db, caller_phone, called_did, company_id)
        if sticky_agent_xml:
            return sticky_agent_xml

        # 2. Check Standard Inbound Flowchart (media_1788347339035.png)
        # Schedule: 09:30 AM - 06:30 PM Monday to Sunday
        now_ist = datetime.now(IST)
        current_time_str = now_ist.strftime("%H:%M")
        is_working_hours = "09:30" <= current_time_str <= "18:30"

        if not is_working_hours:
            logger.info(f"[FLOW-INTERPRETER] Inbound call after hours ({current_time_str} IST) from {caller_phone}. Routing to Voicemail.")
            return cls._generate_xml_response([
                f'<Speak voice="Polly.Aditi" language="en-IN">Thank you for calling Mynt Real. Our office hours are 9:30 AM to 6:30 PM, Monday to Sunday. Please leave a message after the tone, and our team will get back to you shortly.</Speak>',
                f'<Record maxLength="120" finishOnKey="#" action="https://www.myntreal.com/api/v1/telephony/plivo/voicemail" />',
                f'<Hangup />'
            ])

        # 3. Working Hours Menu 1 (Main IVR Greeting & GetDigits)
        gather_url = "https://www.myntreal.com/api/v1/telephony/plivo/ivr/gather?menu=main"
        logger.info(f"[FLOW-INTERPRETER] Presenting Working Hours Main Menu to {caller_phone}")
        return cls._generate_xml_response([
            f'<GetDigits action="{gather_url}" method="POST" numDigits="1" timeout="7" retries="1">',
            f'  <Speak voice="Polly.Aditi" language="en-IN">Welcome to Mynt Real. Press 1 for Automotive, Electric Vehicles and Service. Press 2 for Solar. Press 3 for Evolution Training Center. Press 4 for Insurance. Press 5 for Real Estate.</Speak>',
            f'</GetDigits>',
            f'<Speak voice="Polly.Aditi" language="en-IN">We did not receive your input. Connecting you to our central Tele-sales team. Please hold.</Speak>',
            cls._build_telesales_simultaneous_dial(db, company_id, "Tele-sales", called_did)
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
                xml_elements.append('<Wait length="1" />')
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
                xml_elements.append('<Wait length="2" />')
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
    def _check_sticky_agent(cls, db: Session, caller_phone: str, called_did: str, company_id: int) -> Optional[str]:
        """
        Sticky Agent routing: If an employee recently called or spoke with this customer
        within the last 7 days, route the callback directly to that employee's browser softphone.
        """
        if not caller_phone:
            return None
        clean_digits = re.sub(r'\D', '', caller_phone)[-10:]
        if not clean_digits:
            return None

        # Look for recent outbound session
        recent_session = db.query(VoIPCallSession).filter(
            VoIPCallSession.destination_number.ilike(f"%{clean_digits}%"),
            VoIPCallSession.operator_id.isnot(None)
        ).order_by(VoIPCallSession.id.desc()).first()

        if recent_session and recent_session.operator_id:
            emp = db.query(StaffEmployee).filter(StaffEmployee.id == recent_session.operator_id).first()
            if emp:
                sip_endpoint = cls._resolve_staff_sip_endpoint(db, company_id, emp.id)
                logger.info(f"[STICKY-AGENT] Returning caller {caller_phone} matched to recent staff {emp.full_name} ({emp.id}) -> {sip_endpoint}")
                return cls._generate_xml_response([
                    f'<Speak voice="Polly.Aditi" language="en-IN">Welcome back to Mynt Real. Connecting you directly to your relationship manager, {emp.full_name}. Please hold.</Speak>',
                    f'<Dial timeout="30" callerId="{called_did}">',
                    f'  <User>{sip_endpoint}</User>',
                    f'</Dial>',
                    f'<Speak voice="Polly.Aditi" language="en-IN">Your relationship manager is currently on another call. Connecting you to our central Tele-sales team. Please hold.</Speak>',
                    cls._build_telesales_simultaneous_dial(db, company_id, "Tele-sales", called_did)
                ])

        return None

    @classmethod
    def _build_telesales_simultaneous_dial(cls, db: Session, company_id: int, department_name: str, called_did: str) -> str:
        """
        Builds a multi-user simultaneous <Dial> XML for Tele-sales team.
        All available agent softphones ring in parallel.
        The first agent to answer is connected; others are automatically cancelled.
        """
        # Fetch active staff in company
        staff_list = db.query(StaffEmployee).filter(
            StaffEmployee.status == 'ACTIVE'
        ).limit(10).all()

        user_tags = []
        for st in staff_list:
            sip_uri = cls._resolve_staff_sip_endpoint(db, company_id, st.id)
            user_tags.append(f'  <User>{sip_uri}</User>')

        if not user_tags:
            user_tags.append(f'  <User>sip:agent_c{company_id}_general@phone.plivo.com</User>')

        users_joined = "\n".join(user_tags)
        dial_xml = f"""<Dial timeout="30" callerId="{called_did}" action="https://www.myntreal.com/api/v1/telephony/plivo/ivr/dial-complete">
{users_joined}
</Dial>"""
        return dial_xml

    @classmethod
    def handle_ivr_gather(cls, db: Session, caller_phone: str, called_did: str, digits: str, menu_type: str = "main") -> str:
        """
        Routes the customer's IVR keypad selection as per media_1788347339035.png flowchart.
        """
        company_id = cls._resolve_company_from_did(db, called_did) or 1
        d = str(digits or '').strip()

        logger.info(f"[IVR-GATHER] Inbound call from {caller_phone} at {menu_type} selected digit: '{d}'")

        if menu_type == "menu2":
            # Sub-Menu 2: Automotive EV vs Service
            if d == "1":
                # Manthra EV Sales -> Tele-sales Simultaneous Ring
                return cls._generate_xml_response([
                    f'<Speak voice="Polly.Aditi" language="en-IN">Connecting your call to our Manthra E V sales team. Please hold the line.</Speak>',
                    cls._build_telesales_simultaneous_dial(db, company_id, "Manthra EV Sales", called_did)
                ])
            elif d == "2":
                # Vehicle Service & Support Team
                return cls._generate_xml_response([
                    f'<Speak voice="Polly.Aditi" language="en-IN">Connecting your call to our Vehicle Service and Support team. Please hold the line.</Speak>',
                    cls._build_telesales_simultaneous_dial(db, company_id, "Vehicle Service", called_did)
                ])
            else:
                # Invalid in sub-menu -> Re-prompt
                return cls._generate_xml_response([
                    f'<Speak voice="Polly.Aditi" language="en-IN">Invalid selection. Connecting you to our central Tele-sales desk. Please hold.</Speak>',
                    cls._build_telesales_simultaneous_dial(db, company_id, "Tele-sales", called_did)
                ])

        # Main Menu Routing (media_1788347339035.png)
        if d == "1":
            # Menu 2: EV & Service
            gather_url = "https://www.myntreal.com/api/v1/telephony/plivo/ivr/gather?menu=menu2"
            return cls._generate_xml_response([
                f'<GetDigits action="{gather_url}" method="POST" numDigits="1" timeout="7" retries="1">',
                f'  <Speak voice="Polly.Aditi" language="en-IN">Press 1 for Manthra E V sales. Press 2 for Vehicle Service and Support.</Speak>',
                f'</GetDigits>',
                f'<Speak voice="Polly.Aditi" language="en-IN">Connecting to Manthra E V team. Please hold.</Speak>',
                cls._build_telesales_simultaneous_dial(db, company_id, "Manthra EV", called_did)
            ])
        elif d == "2":
            # Solar Tele-sales
            return cls._generate_xml_response([
                f'<Speak voice="Polly.Aditi" language="en-IN">Connecting your call to our Solar Solutions team. Please hold the line.</Speak>',
                cls._build_telesales_simultaneous_dial(db, company_id, "Solar", called_did)
            ])
        elif d == "3":
            # Evolution Training Center
            return cls._generate_xml_response([
                f'<Speak voice="Polly.Aditi" language="en-IN">Connecting your call to our Evolution Training Center desk. Please hold the line.</Speak>',
                cls._build_telesales_simultaneous_dial(db, company_id, "Evolution Training", called_did)
            ])
        elif d == "4":
            # Insurance Tele-sales
            return cls._generate_xml_response([
                f'<Speak voice="Polly.Aditi" language="en-IN">Connecting your call to our Insurance desk. Please hold the line.</Speak>',
                cls._build_telesales_simultaneous_dial(db, company_id, "Insurance", called_did)
            ])
        elif d == "5":
            # Real Estate Tele-sales
            return cls._generate_xml_response([
                f'<Speak voice="Polly.Aditi" language="en-IN">Connecting your call to our Real Estate Advisory team. Please hold the line.</Speak>',
                cls._build_telesales_simultaneous_dial(db, company_id, "Real Estate", called_did)
            ])
        else:
            # Fallback to Tele-sales Hunt Group
            return cls._generate_xml_response([
                f'<Speak voice="Polly.Aditi" language="en-IN">Connecting your call to our Tele-sales team. Please hold.</Speak>',
                cls._build_telesales_simultaneous_dial(db, company_id, "Tele-sales", called_did)
            ])
