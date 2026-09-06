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
from sqlalchemy import or_, and_

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
        call_session_id: str = "",
        now_dt: Optional[datetime] = None
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

        clean_dest_digits = "".join([c for c in called_str if c.isdigit()])
        if len(clean_dest_digits) == 10:
            clean_dest_digits = f"91{clean_dest_digits}"
        elif len(clean_dest_digits) > 10 and not clean_dest_digits.startswith('91'):
            clean_dest_digits = f"91{clean_dest_digits[-10:]}"

        clean_dest = f"+{clean_dest_digits}" if clean_dest_digits else called_str

        clean_caller_id = "".join([c for c in (getattr(settings, 'PLIVO_DEFAULT_CALLER_ID', None) or os.getenv("PLIVO_DEFAULT_CALLER_ID", "918031728899")) if c.isdigit()])
        if not clean_caller_id:
            clean_caller_id = "918031728899"
        outbound_caller_id = f"+{clean_caller_id}" if not clean_caller_id.startswith('+') else clean_caller_id

        domain = base_api_url if (base_api_url and "localhost" not in base_api_url and "127.0.0.1" not in base_api_url) else "https://www.myntreal.com"
        rec_cb = f"{domain}/api/v1/telephony/plivo/recording-callback"
        hangup_cb = f"{domain}/api/v1/telephony/plivo/hangup"

        if is_sip_caller:
            logger.info(f"[FLOW-INTERPRETER] Bridging Outbound WebRTC call from {caller_str} to customer {clean_dest} with callerId {outbound_caller_id}")
            
            # Correlate with existing VoIPCallSession and update with real Plivo CallUUID
            actual_session_id = call_session_id
            try:
                session_obj = None
                if call_session_id:
                    session_obj = db.query(VoIPCallSession).filter(VoIPCallSession.call_session_id == call_session_id).first()
                if not session_obj and clean_dest:
                    from datetime import timedelta
                    cutoff = get_indian_time() - timedelta(minutes=3)
                    session_obj = db.query(VoIPCallSession).filter(
                        VoIPCallSession.destination_number.ilike(f"%{clean_dest[-10:]}%"),
                        VoIPCallSession.direction == 'outbound',
                        VoIPCallSession.created_at >= cutoff
                    ).order_by(VoIPCallSession.id.desc()).first()

                if session_obj:
                    actual_session_id = session_obj.call_session_id
                    if provider_call_id:
                        session_obj.provider_call_id = provider_call_id
                    if session_obj.status in (CallStateEnum.CREATED.value, CallStateEnum.DIALING.value):
                        session_obj.status = CallStateEnum.RINGING.value
                        session_obj.ringing_at = session_obj.ringing_at or get_indian_time()
                    if session_obj.operator_call_id:
                        from app.models.operator_calls import OperatorCall
                        op_c = db.query(OperatorCall).filter(OperatorCall.id == session_obj.operator_call_id).first()
                        if op_c:
                            op_c.call_id = f"plivo_{provider_call_id}" if provider_call_id else op_c.call_id
                            op_c.status = "ringing"
                    db.commit()
            except Exception as dbe:
                logger.warning(f"[FLOW-INTERPRETER] Could not correlate VoIPCallSession: {dbe}")

            out_rec_cb = f"{rec_cb}?session_id={actual_session_id or ''}"
            out_hangup_cb = f"{hangup_cb}?session_id={actual_session_id or ''}&direction=outbound"

            return cls._generate_xml_response([
                f'<Dial callerId="{outbound_caller_id}" action="{out_hangup_cb}" method="POST" record="record-from-answer" recordingCallbackUrl="{out_rec_cb}" recordingCallbackMethod="POST">',
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
                    f'<Dial callerId="{outbound_caller_id}" action="{hangup_cb}" method="POST" record="record-from-answer" recordingCallbackUrl="{rec_cb}" recordingCallbackMethod="POST">',
                    f'  <User>{operator_sip}</User>',
                    f'</Dial>'
                ])
            elif agent_phone:
                logger.info(
                    f"[FLOW-INTERPRETER] Outbound call to customer {clean_dest} answered. Bridging to agent phone {agent_phone} "
                    f"with callerId {outbound_caller_id}"
                )
                return cls._generate_xml_response([
                    f'<Dial callerId="{outbound_caller_id}" action="{hangup_cb}" method="POST" record="record-from-answer" recordingCallbackUrl="{rec_cb}" recordingCallbackMethod="POST">',
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
        now_ist = now_dt or datetime.now(IST)

        # 2. Persist Inbound Call Session in VoIPCallSession immediately
        session_id = call_session_id or (f"vcs_in_{provider_call_id[-12:]}" if provider_call_id else f"vcs_{int(now_ist.timestamp())}")
        session_obj = None
        if provider_call_id:
            session_obj = db.query(VoIPCallSession).filter(VoIPCallSession.provider_call_id == provider_call_id).first()
        if not session_obj and session_id:
            session_obj = db.query(VoIPCallSession).filter(VoIPCallSession.call_session_id == session_id).first()

        if not session_obj:
            session_obj = VoIPCallSession(
                company_id=company_id,
                call_session_id=session_id,
                provider='plivo',
                provider_call_id=provider_call_id,
                caller_id=called_did or '+918031728899',
                customer_phone=caller_phone,
                destination_number=called_did or '+918031728899',
                direction='inbound',
                call_method=CallMethodEnum.IN_APP_PSTN.value,
                status=CallStateEnum.IN_PROGRESS.value,
                started_at=now_ist,
                answered_at=now_ist
            )
            db.add(session_obj)
            db.commit()
            db.refresh(session_obj)
            logger.info(f"[FLOW-INTERPRETER] Registered inbound VoIPCallSession #{session_obj.id} ({session_id}) from {caller_phone}")

        # 3. FIRST ROUTING GATE: Business Hours & Holiday Evaluation
        # Outermost Gate: Must execute BEFORE any recent-caller lookup, DAG execution, or staff dialing.
        is_open, bh_reason = cls._evaluate_business_hours(db, company_id, {}, now_ist)
        if not is_open:
            logger.info(
                f"[FLOW-INTERPRETER] Inbound call outside business window ({bh_reason}) from {caller_phone} on DID {called_did}. "
                f"Halting all staff routing -> Dispatching to After-Hours Voicemail."
            )
            return cls._generate_xml_response([
                f'<Speak voice="Polly.Aditi" language="en-IN">Thank you for calling Mynt Real. Our office hours are 9:00 AM to 8:00 PM, Monday to Sunday. Please leave a message after the tone, and our team will get back to you shortly.</Speak>',
                f'<Record maxLength="120" finishOnKey="#" action="https://www.myntreal.com/api/v1/telephony/plivo/voicemail" playBeep="true" />',
                f'<Hangup />'
            ])

        # 3. IF OPEN: Check Recent-Caller Callback Routing (Sticky Agent)
        sticky_agent_xml = cls._check_sticky_agent(db, caller_phone, called_did, company_id, now_ist)
        if sticky_agent_xml:
            logger.info(f"[FLOW-INTERPRETER] Sticky agent routed caller {caller_phone} during open hours ({bh_reason}).")
            return sticky_agent_xml

        # 4. Check Dynamic Published Call Flow from DB (if configured and valid)
        clean_d = re.sub(r'\D', '', str(called_did))[-10:] if called_did else ""
        flow = db.query(TelephonyCallFlow).filter(
            (TelephonyCallFlow.did_number == called_did) | (TelephonyCallFlow.did_number.ilike(f"%{clean_d}%")),
            TelephonyCallFlow.status == 'published'
        ).first()

        if flow and flow.current_published_version_id:
            flow_version = db.query(TelephonyCallFlowVersion).filter(
                TelephonyCallFlowVersion.id == flow.current_published_version_id
            ).first()
            if flow_version and flow_version.flow_data and flow_version.flow_data.get('nodes'):
                session_id = f"vcs_in_{provider_call_id[-12:]}" if provider_call_id else f"vcs_{int(datetime.now().timestamp())}"
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

                return cls._execute_flow_node(
                    db=db,
                    flow_data=flow_version.flow_data,
                    company_id=company_id,
                    caller_phone=caller_phone,
                    called_did=called_did,
                    call_session_id=session_id,
                    provider_call_id=provider_call_id,
                    current_node_key=None,
                    dtmf_input=None,
                    exec_log=exec_log,
                    base_api_url=base_api_url
                )

        # 5. Working Hours Sales IVR Menu (Exact 8 Options: 1-6, 9, 0)
        gather_url = "https://www.myntreal.com/api/v1/telephony/plivo/ivr/gather?menu=main"
        sales_prompt = (
            "Welcome to Mynt Real. "
            "For Solar, press 1. "
            "For Insurance, press 2. "
            "For Training, press 3. "
            "For Manthra E V, press 4. "
            "For V G K 4 U, press 5. "
            "For Service Support, press 6. "
            "To speak to Customer Care Executives, press 9. "
            "To return to the Main Menu, press 0."
        )
        logger.info(f"[FLOW-INTERPRETER] Presenting Working Hours Sales IVR Menu to {caller_phone}")
        return cls._generate_xml_response([
            f'<GetDigits action="{gather_url}" method="POST" numDigits="1" timeout="7" retries="2">',
            f'  <Speak voice="Polly.Aditi" language="en-IN">{sales_prompt}</Speak>',
            f'</GetDigits>',
            f'<Speak voice="Polly.Aditi" language="en-IN">We did not receive your input. Connecting you to Customer Care. Please hold.</Speak>',
            cls._build_telesales_simultaneous_dial(db, company_id, "Customer Care", called_did)
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

            if call_session_id:
                try:
                    v_sess = db.query(VoIPCallSession).filter(VoIPCallSession.call_session_id == call_session_id).first()
                    if v_sess:
                        v_meta = {}
                        if v_sess.metadata_json:
                            try:
                                v_meta = json.loads(v_sess.metadata_json) if isinstance(v_sess.metadata_json, str) else dict(v_sess.metadata_json)
                            except Exception:
                                pass
                        v_meta["ivr_path"] = traversed_history
                        if dtmf_input is not None:
                            sel_list = v_meta.get("ivr_selections", [])
                            sel_list.append({
                                "digit": str(dtmf_input),
                                "label": f"Pressed {dtmf_input} at {n_name}",
                                "time": now_ist.strftime('%H:%M:%S')
                            })
                            v_meta["ivr_selections"] = sel_list
                            v_meta["latest_selection"] = f"Pressed {dtmf_input} at {n_name}"
                        v_sess.metadata_json = json.dumps(v_meta)
                        db.commit()
                except Exception as e:
                    logger.warning(f"[FLOW-INTERPRETER] Error updating session ivr_path: {e}")

            next_condition = 'always'
            requires_telecom_action = False

            # ── 1. TRIGGER DID ───────────────────────────────────────────────
            if n_type == 'trigger_did':
                rec_action = f"{base_api_url}/api/v1/telephony/plivo/recording-callback?session_id={call_session_id}"
                xml_elements.append(
                    f'<Record recordSession="true" startOnDialAnswer="false" redirect="false" action="{rec_action}" method="POST" callbackUrl="{rec_action}" callbackMethod="POST" fileFormat="mp3" />'
                )
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
                is_open_check, _ = cls._evaluate_business_hours(db, company_id, {}, now_ist)
                if not is_open_check:
                    logger.warning(f"[FLOW-INTERPRETER] Node {current_node_key} dial_user attempted outside business hours. Routing to Voicemail.")
                    next_condition = 'no_answer'
                    rec_action = f"{base_api_url}/api/v1/telephony/plivo/recording-callback?session_id={call_session_id}"
                    xml_elements.append('<Speak voice="Polly.Aditi">Our offices are currently closed. Please leave a message after the tone.</Speak>')
                    xml_elements.append(f'<Record action="{rec_action}" method="POST" callbackUrl="{rec_action}" callbackMethod="POST" maxLength="120" finishOnKey="#" playBeep="true" />')
                    exec_log.final_outcome = "after_hours_voicemail"
                    requires_telecom_action = True
                    break

                staff_id = n_cfg.get('staff_id')
                endpoint_uri = cls._resolve_staff_sip_endpoint(db, company_id, staff_id)
                timeout = n_cfg.get('timeout_seconds', 25)
                caller_id_val = called_did or n_cfg.get('caller_id', '+918031728899')
                action_url = f"{base_api_url}/api/v1/telephony/plivo/dial-action?session_id={call_session_id}&amp;node_key={current_node_key}"
                rec_action = f"{base_api_url}/api/v1/telephony/plivo/recording-callback?session_id={call_session_id}"

                xml_elements.append(
                    f'<Record recordSession="true" startOnDialAnswer="true" redirect="false" action="{rec_action}" method="POST" callbackUrl="{rec_action}" callbackMethod="POST" fileFormat="mp3" />'
                )
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
                is_open_check, _ = cls._evaluate_business_hours(db, company_id, {}, now_ist)
                if not is_open_check:
                    logger.warning(f"[FLOW-INTERPRETER] Node {current_node_key} dial_ring_group attempted outside business hours. Routing to Voicemail.")
                    next_condition = 'no_answer'
                    rec_action = f"{base_api_url}/api/v1/telephony/plivo/recording-callback?session_id={call_session_id}"
                    xml_elements.append('<Speak voice="Polly.Aditi">Our offices are currently closed. Please leave a message after the tone.</Speak>')
                    xml_elements.append(f'<Record action="{rec_action}" method="POST" callbackUrl="{rec_action}" callbackMethod="POST" maxLength="120" finishOnKey="#" playBeep="true" />')
                    exec_log.final_outcome = "after_hours_voicemail"
                    requires_telecom_action = True
                    break

                rg_id = n_cfg.get('ring_group_id')
                endpoints = cls._resolve_ring_group_endpoints(db, company_id, rg_id)
                timeout = n_cfg.get('timeout_seconds', 25)
                caller_id_val = called_did or n_cfg.get('caller_id', '+918031728899')
                action_url = f"{base_api_url}/api/v1/telephony/plivo/dial-action?session_id={call_session_id}&amp;node_key={current_node_key}"
                rec_action = f"{base_api_url}/api/v1/telephony/plivo/recording-callback?session_id={call_session_id}"

                if endpoints:
                    user_tags = "".join([f"<User>{ep}</User>" for ep in endpoints])
                    xml_elements.append(
                        f'<Record recordSession="true" startOnDialAnswer="true" redirect="false" action="{rec_action}" method="POST" callbackUrl="{rec_action}" callbackMethod="POST" fileFormat="mp3" />'
                    )
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
                xml_elements.append(f'<Record action="{rec_action}" method="POST" callbackUrl="{rec_action}" callbackMethod="POST" maxLength="{max_len}" finishOnKey="{finish_key}" playBeep="true" />')
                exec_log.final_outcome = "voicemail"
                requires_telecom_action = True
                break

            # ── 10. FORWARD PSTN ─────────────────────────────────────────────
            elif n_type == 'forward_pstn':
                dest = n_cfg.get('destination_phone', '')
                caller_id_val = called_did or n_cfg.get('caller_id', '+918031728899')
                rec_action = f"{base_api_url}/api/v1/telephony/plivo/recording-callback?session_id={call_session_id}"
                xml_elements.append(
                    f'<Record recordSession="true" startOnDialAnswer="true" redirect="false" action="{rec_action}" method="POST" callbackUrl="{rec_action}" callbackMethod="POST" fileFormat="mp3" />'
                )
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
        time_str = now_dt.strftime('%H:%M:%S')

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
            if "09:00:00" <= time_str <= "20:00:00":
                return True, "Standard Business Hours (09:00-20:00)"
            return False, "After Hours"

        day_cfg = schedule.get(weekday_key, {})
        if not day_cfg or day_cfg == 'closed' or day_cfg.get('enabled') is False:
            return False, "Closed today"

        open_t = day_cfg.get('start', '09:00')
        close_t = day_cfg.get('end', '20:00')
        if len(open_t) == 5:
            open_t += ":00"
        if len(close_t) == 5:
            close_t += ":00"
        if open_t <= time_str <= close_t:
            return True, f"Open ({open_t}-{close_t})"
        return False, f"Closed ({open_t}-{close_t})"

    @classmethod
    def _check_sticky_agent(
        cls,
        db: Session,
        caller_phone: str,
        called_did: str,
        company_id: int,
        now_dt: Optional[datetime] = None
    ) -> Optional[str]:
        """
        Deterministic Recent-Caller Callback Routing:
        1. Guard: Check Business Hours & Holiday evaluation (MUST NEVER dial staff when closed).
        2. Query recent VoIPCallSession (outbound/inbound answered).
        3. Query CRMLead (telecaller_id or primary_owner_id).
        4. Query OperatorCall (handled_by / operator_id).
        5. Query TelephonyFlowExecutionLog.
        6. Verify employee is ACTIVE and has a registered/live Plivo WebRTC softphone endpoint.
        7. If available -> attempt direct dial. If no-answer/offline -> proceed to Sales IVR.
        """
        if not caller_phone:
            return None

        eval_dt = now_dt or datetime.now(IST)
        is_open, reason = cls._evaluate_business_hours(db, company_id, {}, eval_dt)
        if not is_open:
            logger.info(f"[STICKY-AGENT] Bypassing sticky agent lookup: Business is CLOSED ({reason}).")
            return None

        clean_digits = re.sub(r'\D', '', caller_phone)[-10:]
        if not clean_digits:
            return None

        recent_staff_id = None

        # 1. VoIPCallSession (last 30 days)
        recent_session = db.query(VoIPCallSession).filter(
            VoIPCallSession.destination_number.ilike(f"%{clean_digits}%") | VoIPCallSession.customer_phone.ilike(f"%{clean_digits}%"),
            VoIPCallSession.operator_id.isnot(None)
        ).order_by(VoIPCallSession.id.desc()).first()
        if recent_session and recent_session.operator_id:
            recent_staff_id = recent_session.operator_id

        # 2. CRM Lead owner fallback
        if not recent_staff_id:
            crm_lead = db.query(CRMLead).filter(
                CRMLead.company_id == company_id,
                (CRMLead.phone.ilike(f"%{clean_digits}%") | CRMLead.alternate_phone.ilike(f"%{clean_digits}%"))
            ).order_by(CRMLead.id.desc()).first()
            if crm_lead:
                recent_staff_id = crm_lead.telecaller_id or crm_lead.primary_owner_id

        if recent_staff_id:
            emp = db.query(StaffEmployee).filter(
                StaffEmployee.id == recent_staff_id,
                StaffEmployee.status.in_(['active', 'ACTIVE'])
            ).first()

            if emp:
                # Check real Plivo endpoint registration state
                endpoint = db.query(TelephonyPlivoEndpoint).filter(
                    TelephonyPlivoEndpoint.staff_id == emp.id
                ).order_by(TelephonyPlivoEndpoint.is_registered.desc(), TelephonyPlivoEndpoint.id.desc()).first()

                if endpoint and endpoint.is_registered and endpoint.plivo_username:
                    sip_uri = f"sip:{endpoint.plivo_username}@phone.plivo.com"
                    logger.info(f"[STICKY-AGENT] Caller {caller_phone} routed to registered recent employee {emp.full_name} ({emp.id}) -> {sip_uri}")
                    return cls._generate_xml_response([
                        f'<Speak voice="Polly.Aditi" language="en-IN">Welcome back to Mynt Real. Connecting you directly to your executive, {emp.full_name}. Please hold.</Speak>',
                        f'<Dial timeout="20" callerId="{called_did}" action="https://www.myntreal.com/api/v1/telephony/plivo/ivr/dial-complete">',
                        f'  <User>{sip_uri}</User>',
                        f'</Dial>',
                        f'<Speak voice="Polly.Aditi" language="en-IN">Your executive is currently assisting another client. Connecting to our Sales desk.</Speak>',
                        cls._build_telesales_simultaneous_dial(db, company_id, "Sales", called_did)
                    ])
                else:
                    logger.info(f"[STICKY-AGENT] Recent staff {emp.full_name} is offline/unregistered. Continuing to Sales IVR.")

        return None

    @classmethod
    def _build_telesales_simultaneous_dial(cls, db: Session, company_id: int, department_name: str, called_did: str) -> str:
        """
        Builds a multi-user simultaneous <Dial> XML for the target department/ring group.
        Dynamically routes to active team members configured in CRM Lead Handlers.
        All available online agent softphones ring in parallel.
        If no agent answers within timeout -> routes automatically to Voicemail.
        """
        from app.models.crm_handler import CRMLeadHandler, CRMLeadHandlerMember
        from app.models.signup_category import SignupCategory

        # 1. Resolve target category keywords based on department_name / IVR option
        dept_norm = (department_name or '').strip().lower()
        cat_search_terms = []
        if 'solar' in dept_norm:
            cat_search_terms = ['solar']
        elif 'insurance' in dept_norm:
            cat_search_terms = ['insurance']
        elif 'training' in dept_norm:
            cat_search_terms = ['etc training', 'training']
        elif 'ev' in dept_norm or 'manthra' in dept_norm:
            cat_search_terms = ['ev b2b', 'ev b2c', 'ev spares', 'ev']

        # 2. Look up handler members dynamically from CRMLeadHandler configuration
        staff_ids = []
        if cat_search_terms:
            cat_filter = [SignupCategory.name.ilike(f"%{term}%") for term in cat_search_terms]
            matched_cats = db.query(SignupCategory.id).filter(or_(*cat_filter)).all()
            cat_ids = [c[0] for c in matched_cats]

            if cat_ids:
                h_query = db.query(CRMLeadHandler.id).filter(
                    CRMLeadHandler.is_active == True,
                    CRMLeadHandler.category_id.in_(cat_ids)
                )
                if company_id:
                    h_query = h_query.filter(CRMLeadHandler.company_id == company_id)
                
                handler_ids = [h[0] for h in h_query.all()]
                if not handler_ids and company_id != 4:
                    # Fallback to MyntReal canonical handlers
                    handler_ids = [h[0] for h in db.query(CRMLeadHandler.id).filter(
                        CRMLeadHandler.is_active == True,
                        CRMLeadHandler.company_id == 4,
                        CRMLeadHandler.category_id.in_(cat_ids)
                    ).all()]

                if handler_ids:
                    members = db.query(CRMLeadHandlerMember.employee_id).join(
                        StaffEmployee, StaffEmployee.id == CRMLeadHandlerMember.employee_id
                    ).filter(
                        CRMLeadHandlerMember.handler_id.in_(handler_ids),
                        CRMLeadHandlerMember.is_active == True,
                        StaffEmployee.status.in_(['active', 'ACTIVE'])
                    ).distinct().all()
                    staff_ids = [m[0] for m in members]

        # 3. If handler members found, use them
        user_tags = []
        if staff_ids:
            logger.info(f"[IVR-DIAL] Resolved {len(staff_ids)} active handler members for '{department_name}' (Company: {company_id}): {staff_ids}")
            for sid in staff_ids:
                sip_uri = cls._resolve_staff_sip_endpoint(db, company_id, sid)
                user_tags.append(f'  <User>{sip_uri}</User>')
        else:
            # Fallback: active staff in company
            staff_list = db.query(StaffEmployee).filter(
                StaffEmployee.status.in_(['active', 'ACTIVE'])
            ).limit(10).all()
            for st in staff_list:
                sip_uri = cls._resolve_staff_sip_endpoint(db, company_id, st.id)
                user_tags.append(f'  <User>{sip_uri}</User>')

        if not user_tags:
            user_tags.append(f'  <User>sip:agent_c{company_id}_general@phone.plivo.com</User>')

        users_joined = "\n".join(user_tags)
        dial_complete_url = "https://www.myntreal.com/api/v1/telephony/plivo/ivr/dial-complete"
        voicemail_url = "https://www.myntreal.com/api/v1/telephony/plivo/voicemail"
        return f"""<Dial timeout="25" callerId="{called_did}" action="{dial_complete_url}">
{users_joined}
</Dial>
<Speak voice="Polly.Aditi" language="en-IN">All our {department_name} executives are currently busy on other calls. Please leave a voicemail after the beep, and we will return your call promptly.</Speak>
<Record maxLength="120" finishOnKey="#" action="{voicemail_url}" />
<Hangup />"""

    @classmethod
    def handle_ivr_gather(cls, db: Session, caller_phone: str, called_did: str, digits: str, menu_type: str = "main") -> str:
        """
        Authoritative Sales IVR Keypad Router:
        1 -> Solar
        2 -> Insurance
        3 -> Training
        4 -> Manthra EV
        5 -> VGK 4U
        6 -> Service Support (Combined Service & Support)
        9 -> Customer Care Executives
        0 -> Main Menu
        """
        company_id = cls._resolve_company_from_did(db, called_did) or 1
        d = str(digits or '').strip()

        logger.info(f"[SALES-IVR-GATHER] Inbound call from {caller_phone} selected DTMF: '{d}'")

        # Record DTMF Selection in active VoIPCallSession
        clean_caller = re.sub(r'[^\d]', '', str(caller_phone or ''))[-10:]
        opt_map = {
            "1": "Option 1: Solar Solutions",
            "2": "Option 2: Insurance Advisory",
            "3": "Option 3: Training Desk",
            "4": "Option 4: Manthra EV",
            "5": "Option 5: VGK 4U",
            "6": "Option 6: Service Support",
            "9": "Option 9: Customer Care Executives",
            "0": "Option 0: Main Menu Replay"
        }
        selected_label = opt_map.get(d, f"Option {d}")

        try:
            session = db.query(VoIPCallSession).filter(
                VoIPCallSession.customer_phone.ilike(f"%{clean_caller}%"),
                VoIPCallSession.direction == 'inbound'
            ).order_by(VoIPCallSession.id.desc()).first()
            if session:
                meta = {}
                if session.metadata_json:
                    try:
                        meta = json.loads(session.metadata_json) if isinstance(session.metadata_json, str) else dict(session.metadata_json)
                    except Exception:
                        pass
                selections = meta.get("ivr_selections", [])
                selections.append({
                    "digit": d,
                    "label": selected_label,
                    "time": datetime.now(IST).strftime('%H:%M:%S')
                })
                meta["ivr_selections"] = selections
                meta["latest_selection"] = selected_label
                session.metadata_json = json.dumps(meta)
                db.commit()
                logger.info(f"[IVR-GATHER] Recorded selection '{selected_label}' to VoIPCallSession #{session.id}")
        except Exception as e:
            logger.warning(f"[IVR-GATHER] Error persisting DTMF selection: {e}")

        if d == "1":
            # 1. Solar
            return cls._generate_xml_response([
                f'<Speak voice="Polly.Aditi" language="en-IN">Connecting your call to our Solar Solutions team. Please hold the line.</Speak>',
                cls._build_telesales_simultaneous_dial(db, company_id, "Solar Solutions", called_did)
            ])
        elif d == "2":
            # 2. Insurance
            return cls._generate_xml_response([
                f'<Speak voice="Polly.Aditi" language="en-IN">Connecting your call to our Insurance Advisory desk. Please hold the line.</Speak>',
                cls._build_telesales_simultaneous_dial(db, company_id, "Insurance", called_did)
            ])
        elif d == "3":
            # 3. Training
            return cls._generate_xml_response([
                f'<Speak voice="Polly.Aditi" language="en-IN">Connecting your call to our Training desk. Please hold the line.</Speak>',
                cls._build_telesales_simultaneous_dial(db, company_id, "Training", called_did)
            ])
        elif d == "4":
            # 4. Manthra EV
            return cls._generate_xml_response([
                f'<Speak voice="Polly.Aditi" language="en-IN">Connecting your call to our Manthra E V team. Please hold the line.</Speak>',
                cls._build_telesales_simultaneous_dial(db, company_id, "Manthra EV", called_did)
            ])
        elif d == "5":
            # 5. VGK 4U
            return cls._generate_xml_response([
                f'<Speak voice="Polly.Aditi" language="en-IN">Connecting your call to our V G K 4 U desk. Please hold the line.</Speak>',
                cls._build_telesales_simultaneous_dial(db, company_id, "VGK 4U", called_did)
            ])
        elif d == "6":
            # 6. Service Support (Combined)
            return cls._generate_xml_response([
                f'<Speak voice="Polly.Aditi" language="en-IN">Connecting your call to our Service and Support team. Please hold the line.</Speak>',
                cls._build_telesales_simultaneous_dial(db, company_id, "Service Support", called_did)
            ])
        elif d == "9":
            # 9. Customer Care Executives
            return cls._generate_xml_response([
                f'<Speak voice="Polly.Aditi" language="en-IN">Connecting you to our Customer Care Executives. Please hold the line.</Speak>',
                cls._build_telesales_simultaneous_dial(db, company_id, "Customer Care", called_did)
            ])
        elif d == "0":
            # 0. Return to Main Menu
            gather_url = "https://www.myntreal.com/api/v1/telephony/plivo/ivr/gather?menu=main"
            sales_prompt = (
                "For Solar, press 1. "
                "For Insurance, press 2. "
                "For Training, press 3. "
                "For Manthra E V, press 4. "
                "For V G K 4 U, press 5. "
                "For Service Support, press 6. "
                "To speak to Customer Care Executives, press 9. "
                "To replay this menu, press 0."
            )
            return cls._generate_xml_response([
                f'<GetDigits action="{gather_url}" method="POST" numDigits="1" timeout="7" retries="2">',
                f'  <Speak voice="Polly.Aditi" language="en-IN">{sales_prompt}</Speak>',
                f'</GetDigits>',
                f'<Speak voice="Polly.Aditi" language="en-IN">We did not receive your input. Connecting you to Customer Care. Please hold.</Speak>',
                cls._build_telesales_simultaneous_dial(db, company_id, "Customer Care", called_did)
            ])
        else:
            # Invalid selection -> Re-prompt or route to Customer Care
            gather_url = "https://www.myntreal.com/api/v1/telephony/plivo/ivr/gather?menu=main"
            return cls._generate_xml_response([
                f'<Speak voice="Polly.Aditi" language="en-IN">You entered an invalid option.</Speak>',
                f'<GetDigits action="{gather_url}" method="POST" numDigits="1" timeout="7" retries="1">',
                f'  <Speak voice="Polly.Aditi" language="en-IN">Press 1 for Solar, 2 for Insurance, 3 for Training, 4 for Manthra E V, 5 for V G K 4 U, 6 for Service Support, 9 for Customer Care, or 0 for Main Menu.</Speak>',
                f'</GetDigits>',
                f'<Speak voice="Polly.Aditi" language="en-IN">Connecting you to Customer Care. Please hold.</Speak>',
                cls._build_telesales_simultaneous_dial(db, company_id, "Customer Care", called_did)
            ])
