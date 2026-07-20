"""
DC_WA_TEMPLATES_SEED_001 — WhatsApp Standard Templates Seeder
Seeds 16 UTILITY templates + WhatsAppAutoTrigger rows.
Submits to Meta API in a background thread (15s delay, non-blocking).
Idempotent: slug conflict → skip; event_key conflict → only wire if template_id is NULL.
"""

import logging
import re
import time
import threading
from datetime import datetime
from typing import List, Optional

logger = logging.getLogger(__name__)

_SEEDED = False   # module-level guard — prevents re-run on hot-reload

# ── Template definitions ───────────────────────────────────────────────────────
# body_text uses named {{vars}} — _submit_one converts to positional {{1}} for Meta.
# example_values must align in ORDER with the named vars in body_text.

_TEMPLATES = [
    {
        "slug": "mnr_morning_team_greeting",
        "name": "MNR Morning Team Greeting",
        "body_text": (
            "🌅 Good morning, {{name}}!\n\n"
            "📅 *{{date}}*\n\n"
            "Your action plan for today 📋\n\n"
            "📌 Active Tasks: {{active_tasks}} pending\n"
            "📊 KRAs Due Today: {{kras_due}}\n"
            "⚠️ Overdue Items: {{overdue_count}}\n\n"
            "Let's make today count! 💪\n"
            "🔗 {{portal_url}}"
        ),
        "footer_text": "MNR Mega Natural Resources",
        "segment": "staff",
        "meta_category": "UTILITY",
        "event_key": "staff_morning_reminder",
        "event_label": "Staff Daily Morning Greeting",
        "event_category": "staff",
        "example_values": ["Rahul Kumar", "Wed, 07 May 2026", "3", "2", "1",
                           "mnrteam.com/staff/dashboard"],
    },
    {
        "slug": "mnr_morning_leadership_summary",
        "name": "MNR Morning Leadership Summary",
        "body_text": (
            "🏢 Good morning, {{name}}!\n\n"
            "📅 *{{date}}* — Team Snapshot 📊\n\n"
            "👥 Active Staff: {{active_staff}}\n"
            "📋 Open Tasks: {{open_tasks}} | ⚠️ Overdue: {{overdue_tasks}}\n"
            "📞 Open Leads: {{open_leads}} | 🔴 Follow-up Due: {{overdue_leads}}\n"
            "🎫 Open Tickets: {{open_tickets}} | ✅ Closed Today: {{closed_today}}\n\n"
            "Drive the team forward! 🚀\n"
            "🔗 {{portal_url}}"
        ),
        "footer_text": "MNR Mega Natural Resources",
        "segment": "staff",
        "meta_category": "UTILITY",
        "event_key": "staff_morning_leadership",
        "event_label": "Leadership Morning Team Summary",
        "event_category": "staff",
        "example_values": ["Anjali Singh", "Wed, 07 May 2026", "24", "12", "3",
                           "45", "8", "7", "2", "mnrteam.com/staff/dashboard"],
    },
    {
        "slug": "mnr_task_overdue_alert",
        "name": "MNR Task Overdue Alert",
        "body_text": (
            "⚠️ Hi {{name}}, a task assigned to you is *overdue*!\n\n"
            "📋 Task: {{task_title}}\n"
            "📅 Due Date: {{due_date}}\n"
            "⏰ Overdue By: {{overdue_days}} day(s)\n"
            "👔 Assigned By: {{assigned_by}}\n\n"
            "Please update the status or contact your manager.\n"
            "➡️ mnrteam.com/staff/tasks"
        ),
        "footer_text": "MNR Mega Natural Resources",
        "segment": "staff",
        "meta_category": "UTILITY",
        "event_key": "task_overdue_alert",
        "event_label": "Staff Task Overdue Alert",
        "event_category": "staff",
        "example_values": ["Rahul Kumar", "Update Solar Pipeline Report",
                           "05 May 2026", "2", "Priya Sharma"],
    },
    {
        "slug": "mnr_kra_overdue_alert",
        "name": "MNR KRA Overdue Alert",
        "body_text": (
            "🔴 Hi {{name}}, your KRA for today is *pending*!\n\n"
            "📊 KRA: {{kra_name}}\n"
            "🗓️ Date: {{kra_date}}\n"
            "🎯 Target: {{kra_target}}\n"
            "📋 Status: {{completion_status}}\n\n"
            "Please update your KRA completion status.\n"
            "➡️ mnrteam.com/staff/kra-status"
        ),
        "footer_text": "MNR Mega Natural Resources",
        "segment": "staff",
        "meta_category": "UTILITY",
        "event_key": "kra_overdue_alert",
        "event_label": "Staff KRA Overdue Alert",
        "event_category": "staff",
        "example_values": ["Rahul Kumar", "Daily Lead Calls",
                           "07 May 2026", "10 calls", "Pending"],
    },
    {
        "slug": "mnr_ticket_created_customer",
        "name": "MNR Service Ticket Created",
        "body_text": (
            "✅ Dear {{name}}, your service request is registered!\n\n"
            "🎫 Ticket ID: {{ticket_id}}\n"
            "📝 Issue: {{issue}}\n"
            "📅 Date: {{date}}\n"
            "🔄 Status: Open\n\n"
            "Our team will contact you shortly.\n"
            "Quote your Ticket ID for updates.\n\n"
            "Thank you for choosing MNR! 🙏"
        ),
        "footer_text": "mnrteam.com",
        "segment": "general",
        "meta_category": "UTILITY",
        "event_key": "ticket_created_customer",
        "event_label": "Service Ticket Created — Customer",
        "event_category": "ticket",
        "example_values": ["Ramesh Kumar", "TKT-2026-001",
                           "EV Battery Not Charging", "07 May 2026"],
    },
    {
        "slug": "mnr_ticket_closed_customer",
        "name": "MNR Service Ticket Closed",
        "body_text": (
            "🎉 Dear {{name}}, your service ticket is *resolved*! ✅\n\n"
            "🎫 Ticket ID: {{ticket_id}}\n"
            "📝 Issue: {{issue}}\n"
            "📅 Closed On: {{date}}\n\n"
            "We hope the issue is resolved to your satisfaction.\n"
            "Your feedback matters — thank you for being with MNR! ⭐"
        ),
        "footer_text": "mnrteam.com",
        "segment": "general",
        "meta_category": "UTILITY",
        "event_key": "ticket_closed_customer",
        "event_label": "Service Ticket Closed — Customer",
        "event_category": "ticket",
        "example_values": ["Ramesh Kumar", "TKT-2026-001",
                           "EV Battery Not Charging", "07 May 2026"],
    },
    {
        "slug": "mnr_ticket_acknowledged_customer",
        "name": "MNR Ticket Acknowledged",
        "body_text": (
            "👋 Dear {{name}}, we have received your service ticket!\n\n"
            "🎫 Ticket ID: {{ticket_id}}\n"
            "🔄 Status: Acknowledged\n\n"
            "Our service team is reviewing your issue.\n"
            "We will keep you updated on progress.\n\n"
            "Thank you for your patience! 🙏"
        ),
        "footer_text": "mnrteam.com",
        "segment": "general",
        "meta_category": "UTILITY",
        "event_key": "ticket_acknowledged",
        "event_label": "Ticket Acknowledged — Customer",
        "event_category": "ticket",
        "example_values": ["Ramesh Kumar", "TKT-2026-001"],
    },
    {
        "slug": "mnr_ticket_resolved_customer",
        "name": "MNR Ticket Work Complete",
        "body_text": (
            "🎯 Dear {{name}}, your service issue is *work complete*!\n\n"
            "🎫 Ticket ID: {{ticket_id}}\n"
            "📝 Issue: {{issue}}\n"
            "✅ Status: Work Complete\n\n"
            "The ticket will be formally closed shortly.\n"
            "Thank you for choosing MNR! 🙏"
        ),
        "footer_text": "mnrteam.com",
        "segment": "general",
        "meta_category": "UTILITY",
        "event_key": "ticket_resolved",
        "event_label": "Ticket Work Complete — Customer",
        "event_category": "ticket",
        "example_values": ["Ramesh Kumar", "TKT-2026-001", "EV Battery Not Charging"],
    },
    {
        "slug": "mnr_ticket_status_update_customer",
        "name": "MNR Ticket Status Update",
        "body_text": (
            "🔔 Dear {{name}}, your ticket status has been updated!\n\n"
            "🎫 Ticket ID: {{ticket_id}}\n"
            "🔄 New Status: {{status}}\n"
            "📅 Updated On: {{date}}\n\n"
            "For queries, visit mnrteam.com 🙏"
        ),
        "footer_text": "mnrteam.com",
        "segment": "general",
        "meta_category": "UTILITY",
        "event_key": "ticket_status_update_customer",
        "event_label": "Ticket Status Update — Customer",
        "event_category": "ticket",
        "example_values": ["Ramesh Kumar", "TKT-2026-001",
                           "Work In Progress", "07 May 2026"],
    },
    {
        "slug": "mnr_lead_thankyou_general",
        "name": "MNR Lead Thank You",
        "body_text": (
            "🙏 Dear {{name}}, thank you for your interest in MNR!\n\n"
            "We have received your enquiry and our team will\n"
            "connect with you shortly.\n\n"
            "📞 Reference: {{lead_ref}}\n"
            "📅 Received: {{date}}\n\n"
            "Our executive will reach out within 24 hours.\n\n"
            "Exciting things ahead! 🌟"
        ),
        "footer_text": "MNR Mega Natural Resources",
        "segment": "general",
        "meta_category": "UTILITY",
        "event_key": "crm_lead_created",
        "event_label": "New Lead Thank You — Customer",
        "event_category": "crm",
        "example_values": ["Suresh Patel", "MNR-LEAD-1042", "07 May 2026"],
    },
    {
        "slug": "mnr_walkin_thankyou_customer",
        "name": "MNR Walk-in Thank You",
        "body_text": (
            "🙏 Dear {{name}}, thank you for visiting our showroom!\n\n"
            "We are delighted to have you here.\n"
            "Our team will connect with you shortly.\n\n"
            "📞 Reference: {{lead_ref}}\n"
            "📅 Visit Date: {{date}}\n"
            "🏬 Location: {{partner_name}}\n\n"
            "Looking forward to serving you! 😊"
        ),
        "footer_text": "MNR Mega Natural Resources",
        "segment": "general",
        "meta_category": "UTILITY",
        "event_key": "crm_lead_walkin_created",
        "event_label": "Walk-in Thank You — Customer",
        "event_category": "crm",
        "example_values": ["Suresh Patel", "MNR-LEAD-1042",
                           "07 May 2026", "MNR Solar Hub Hyderabad"],
    },
    {
        "slug": "mnr_lead_assigned_staff",
        "name": "MNR Lead Assigned to Staff",
        "body_text": (
            "📞 Hi {{staff_name}}, a new lead has been assigned to you!\n\n"
            "👤 Lead Name: {{lead_name}}\n"
            "📱 Phone: {{phone}}\n"
            "🏷️ Source: {{source}}\n"
            "📅 Assigned On: {{date}}\n\n"
            "Please follow up at the earliest! 💼\n"
            "➡️ mnrteam.com/staff/crm"
        ),
        "footer_text": "MNR Mega Natural Resources",
        "segment": "staff",
        "meta_category": "UTILITY",
        "event_key": "lead_assigned_staff",
        "event_label": "Lead Assigned — Staff Notification",
        "event_category": "crm",
        "example_values": ["Priya Sharma", "Suresh Patel",
                           "9876543210", "Walk-in", "07 May 2026"],
    },
    {
        "slug": "mnr_lead_overdue_sales",
        "name": "MNR Overdue Leads — Sales",
        "body_text": (
            "🔔 Hi {{name}}, you have *{{count}} overdue lead(s)* pending!\n\n"
            "📋 Oldest Lead: {{oldest_lead}}\n"
            "📅 Overdue Since: {{overdue_since}}\n\n"
            "Please take action today to keep your pipeline moving. 💼\n"
            "➡️ mnrteam.com/staff/crm"
        ),
        "footer_text": "MNR Mega Natural Resources",
        "segment": "staff",
        "meta_category": "UTILITY",
        "event_key": "lead_overdue_sales",
        "event_label": "Overdue Leads — Sales Staff Alert",
        "event_category": "crm",
        "example_values": ["Priya Sharma", "3", "Suresh Patel - Solar EV", "04 May 2026"],
    },
    {
        "slug": "mnr_lead_overdue_leadership",
        "name": "MNR Overdue Leads — Leadership",
        "body_text": (
            "🏢 Team Lead Overdue Report — {{date}}\n\n"
            "Hi {{name}}, your team overdue lead summary:\n\n"
            "🔴 Total Overdue Leads: {{total_overdue}}\n"
            "👥 Staff with Overdue: {{staff_count}}\n"
            "📊 Longest Overdue: {{max_days}} day(s)\n\n"
            "Please review and follow up with your team.\n"
            "➡️ mnrteam.com/staff/crm"
        ),
        "footer_text": "MNR Mega Natural Resources",
        "segment": "staff",
        "meta_category": "UTILITY",
        "event_key": "lead_overdue_leadership",
        "event_label": "Overdue Leads Summary — Leadership",
        "event_category": "crm",
        "example_values": ["07 May 2026", "Anjali Singh", "12", "4", "5"],
    },
    {
        "slug": "mnr_kra_daily_summary_leader",
        "name": "MNR KRA Daily Summary — Leader",
        "body_text": (
            "📊 Good morning, {{name}}!\n\n"
            "Team KRA summary for {{date}}:\n\n"
            "✅ Completed: {{completed_count}}\n"
            "⏳ Pending: {{pending_count}}\n"
            "🔴 Delayed: {{delayed_count}}\n"
            "👥 Total Staff: {{total_staff}}\n\n"
            "Review and motivate your team! 💪\n"
            "➡️ mnrteam.com/staff/kra-status"
        ),
        "footer_text": "MNR Mega Natural Resources",
        "segment": "staff",
        "meta_category": "UTILITY",
        "event_key": "kra_daily_summary_leader",
        "event_label": "KRA Daily Summary — Team Leader",
        "event_category": "staff",
        "example_values": ["Anjali Singh", "07 May 2026", "8", "3", "2", "13"],
    },
    {
        "slug": "mnr_lead_followup_reminder",
        "name": "MNR Lead Follow-up Reminder",
        "body_text": (
            "⏰ Hi {{name}}, you have *{{count}} lead(s)* due for follow-up today!\n\n"
            "📋 Next Up: {{next_lead}}\n"
            "📞 Phone: {{phone}}\n"
            "📅 Follow-up Due: Today\n\n"
            "Don't let any lead go cold — act now! 🔥\n"
            "➡️ mnrteam.com/staff/crm"
        ),
        "footer_text": "MNR Mega Natural Resources",
        "segment": "staff",
        "meta_category": "UTILITY",
        "event_key": "lead_followup_reminder",
        "event_label": "Lead Follow-up Reminder — Sales Staff",
        "event_category": "crm",
        "example_values": ["Priya Sharma", "4", "Ramesh Kumar - EV B2B", "9876543210"],
    },
    # T17 — Partner Walk-in Notification (to partner when their walkin lead is registered)
    {
        "slug": "mnr_walkin_partner_notify",
        "name": "MNR Walk-in Partner Notify",
        "body_text": (
            "🎉 New Walk-in at *{{partner_name}}*!\n\n"
            "Customer *{{customer_name}}* has visited your outlet today.\n"
            "📅 Date: {{date}}\n"
            "📋 Lead Ref: {{lead_ref}}\n\n"
            "Our team will follow up with them shortly.\n"
            "Thank you for your partnership! 🙏"
        ),
        "footer_text": "MNR Partner Network",
        "segment": "partner",
        "meta_category": "UTILITY",
        "event_key": "crm_lead_walkin_partner_notify",
        "event_label": "Walk-in Lead Registered — Partner Notification",
        "event_category": "crm",
        "example_values": ["VGK Hub Hyderabad", "Rajesh Kumar", "07 May 2026", "MNR-LEAD-00123"],
    },
]


# ── Public entry point ─────────────────────────────────────────────────────────

def seed_wa_templates(db_factory):
    """
    Idempotent startup seeder — call once from schema_bootstrap.
    Uses module-level _SEEDED guard so hot-reload doesn't re-run.
    """
    global _SEEDED
    if _SEEDED:
        return
    _SEEDED = True

    db = db_factory()
    try:
        new_ids = _do_seed(db)
    finally:
        db.close()

    if new_ids:
        t = threading.Thread(
            target=_submit_all_delayed,
            args=(db_factory, new_ids),
            daemon=True
        )
        t.start()
        msg = f"[DC_WA_TEMPLATES_SEED_001] ✅ {len(new_ids)} new template(s) seeded — Meta submission in 15s"
        logger.info(msg)
        print(msg, flush=True)
    else:
        msg = "[DC_WA_TEMPLATES_SEED_001] ✅ All templates already present — skipped"
        logger.info(msg)
        print(msg, flush=True)


# ── Internal helpers ───────────────────────────────────────────────────────────

def _do_seed(db) -> List[int]:
    """
    Seed templates + triggers into DB. Returns list of newly created template IDs.
    """
    from app.models.whatsapp import WhatsAppTemplate, WhatsAppAutoTrigger

    new_ids: List[int] = []

    for tdef in _TEMPLATES:
        existing = db.query(WhatsAppTemplate).filter_by(slug=tdef["slug"]).first()
        if not existing:
            tpl = WhatsAppTemplate(
                name=tdef["name"],
                slug=tdef["slug"],
                body_text=tdef["body_text"],
                footer_text=tdef.get("footer_text", ""),
                segment=tdef.get("segment", "general"),
                template_type="custom",
                is_system=False,
                is_active=True,
                meta_category=tdef.get("meta_category", "UTILITY"),
                meta_template_name=tdef["slug"],
                meta_template_language="en",
                example_values=tdef.get("example_values", []),
            )
            db.add(tpl)
            db.flush()
            new_ids.append(tpl.id)
            logger.info(f"[DC_WA_SEED] Created template: {tdef['slug']}")

    db.commit()

    # Wire AutoTrigger → template  (skip if trigger already has a template set)
    for tdef in _TEMPLATES:
        tpl = db.query(WhatsAppTemplate).filter_by(slug=tdef["slug"]).first()
        if not tpl:
            continue
        trig = db.query(WhatsAppAutoTrigger).filter_by(event_key=tdef["event_key"]).first()
        if not trig:
            db.add(WhatsAppAutoTrigger(
                event_key=tdef["event_key"],
                event_label=tdef["event_label"],
                event_category=tdef["event_category"],
                template_id=tpl.id,
                is_enabled=True,
            ))
            logger.info(f"[DC_WA_SEED] Created trigger: {tdef['event_key']}")
        elif trig.template_id is None:
            trig.template_id = tpl.id
            logger.info(f"[DC_WA_SEED] Wired template to existing trigger: {tdef['event_key']}")

    db.commit()
    return new_ids


def _submit_all_delayed(db_factory, template_ids: List[int], delay: int = 15):
    """Background thread: wait, then submit each new template to Meta."""
    time.sleep(delay)
    db = db_factory()
    try:
        for tid in template_ids:
            try:
                _submit_one(db, tid)
                time.sleep(1.5)   # avoid Meta rate-limit
            except Exception as e:
                logger.warning(f"[DC_WA_SEED] Meta submit error for id={tid}: {e}")
    except Exception as e:
        logger.error(f"[DC_WA_SEED] Submit thread fatal error: {e}")
    finally:
        db.close()


def _submit_one(db, template_id: int):
    """Submit a single template to the Meta WhatsApp Business API."""
    import os
    import requests as _req
    from app.models.whatsapp import WhatsAppTemplate
    from app.services.wa_credentials import get_wa_credentials

    tpl = db.query(WhatsAppTemplate).get(template_id)
    if not tpl:
        return

    if tpl.meta_submitted_at:
        return   # already submitted

    creds = get_wa_credentials(db)
    access_token = (creds.get("access_token") or "").strip() or os.environ.get("META_WHATSAPP_ACCESS_TOKEN", "")
    waba_id = (creds.get("business_account_id") or "").strip() or os.environ.get("META_WHATSAPP_BUSINESS_ACCOUNT_ID", "")

    if not access_token or not waba_id:
        logger.info(f"[DC_WA_SEED] No Meta credentials — skipping submission for {tpl.slug}")
        return

    name = re.sub(r'[^a-z0-9_]', '_', (tpl.meta_template_name or tpl.slug).lower())[:60]

    # Convert named {{vars}} → positional {{1}}, {{2}}, … (Meta requirement)
    raw_body = (tpl.body_text or '').strip()
    named_vars = re.findall(r'\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}', raw_body)
    if named_vars:
        seen: dict = {}
        counter = [0]

        def _replace(m):
            v = m.group(1)
            if v not in seen:
                counter[0] += 1
                seen[v] = counter[0]
            return f"{{{{{seen[v]}}}}}"

        raw_body = re.sub(r'\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}', _replace, raw_body)

    positional_count = len(re.findall(r'\{\{\d+\}\}', raw_body))
    examples = tpl.example_values or []

    components = []
    body_comp: dict = {"type": "BODY", "text": raw_body}
    if positional_count > 0 and examples:
        body_comp["example"] = {"body_text": [list(examples[:positional_count])]}
    components.append(body_comp)

    if tpl.footer_text and tpl.footer_text.strip():
        components.append({"type": "FOOTER", "text": tpl.footer_text.strip()[:60]})

    payload = {
        "name": name,
        "language": tpl.meta_template_language or "en",
        "category": tpl.meta_category or "UTILITY",
        "components": components,
    }

    try:
        url = f"https://graph.facebook.com/v21.0/{waba_id}/message_templates"
        resp = _req.post(
            url, json=payload,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=30
        )
        raw = resp.json()

        if resp.status_code in (200, 201):
            meta_id = raw.get("id", "")
            meta_status = raw.get("status", "PENDING")
            tpl.meta_template_name = name
            tpl.meta_template_id = meta_id
            tpl.meta_approval_status = meta_status
            tpl.is_meta_approved = (meta_status == "APPROVED")
            tpl.meta_submitted_at = datetime.utcnow()
            db.commit()
            logger.info(f"[DC_WA_SEED] ✅ Submitted to Meta: {name} → {meta_status}")
        else:
            err = raw.get("error", {})
            logger.warning(
                f"[DC_WA_SEED] ⚠️ Meta rejected '{name}': "
                f"code={err.get('code')} msg={err.get('message','unknown')}"
            )
    except Exception as e:
        logger.error(f"[DC_WA_SEED] Exception submitting '{tpl.slug}': {e}")
