"""
DC_WA_TEMPLATES_SEED_001 — WhatsApp Standard Templates Seeder
Seeds 16 UTILITY templates + WhatsAppAutoTrigger rows.
Submits to Meta API in a background thread (15s delay, non-blocking).
Idempotent: slug conflict → skip; event_key conflict → only wire if template_id is NULL.
"""

from app.core.timezone import get_indian_time
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
        "slug": "myntreal_morning_team_greeting",
        "name": "Myntreal Morning Team Greeting",
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
        "footer_text": "Myntreal.com",
        "segment": "staff",
        "meta_category": "UTILITY",
        "event_key": "staff_morning_reminder",
        "event_label": "Staff Daily Morning Greeting",
        "event_category": "staff",
        "example_values": ["Rahul Kumar", "Wed, 07 May 2026", "3", "2", "1",
                           "myntreal.com/staff/dashboard"],
    },
    {
        "slug": "myntreal_morning_leadership_summary",
        "name": "Myntreal Morning Leadership Summary",
        "body_text": (
            "🏢 Good morning, {{name}}!\n\n"
            "📅 *{{date}}* — Team Snapshot 📊\n\n"
            "👥 Active Staff: {{active_staff}}\n"
            "📋 Open Tasks: {{open_tasks}} | ⚠️ Overdue: {{overdue_tasks}}\n"
            "🎫 Open Tickets: {{open_tickets}} | ✅ Closed Today: {{closed_today}}\n\n"
            "📞 *Leads Performance:*\n"
            "• Open Leads: {{open_leads}} | 🔴 Follow-up Due: {{overdue_leads}}\n"
            "• New Leads (Overall): {{new_leads_overall}}\n"
            "• Yesterday New: {{yesterday_new_leads}} | Yesterday Lost: {{yesterday_lost_leads}}\n\n"
            "🏦 *Bank Balances (Company-wise):*\n"
            "{{bank_balances_block}}\n\n"
            "💵 *Cash Balances (Person-wise):*\n"
            "{{cash_balances_block}}\n\n"
            "Drive the team forward! 🚀\n"
            "🔗 {{portal_url}}"
        ),
        "footer_text": "Myntreal.com",
        "segment": "staff",
        "meta_category": "UTILITY",
        "event_key": "staff_morning_leadership",
        "event_label": "Leadership Morning Team Summary",
        "event_category": "staff",
        "example_values": ["Anjali Singh", "Mon, 12 Oct 2026", "27", "55", "48",
                           "79", "0", "2915", "1623", "264", "4", "0",
                           "Bank Balances", "Cash Balances", "myntreal.com/staff/dashboard"],
    },
    {
        "slug": "myntreal_task_overdue_alert",
        "name": "Task Overdue Alert",
        "body_text": (
            "⚠️ Hi {{name}}, a task assigned to you is *overdue*!\n\n"
            "📋 Task: {{task_title}}\n"
            "📅 Due Date: {{due_date}}\n"
            "⏰ Overdue By: {{overdue_days}} day(s)\n"
            "👔 Assigned By: {{assigned_by}}\n\n"
            "Please update the status or contact your manager.\n"
            "➡️ myntreal.com/staff/tasks"
        ),
        "footer_text": "Myntreal.com",
        "segment": "staff",
        "meta_category": "UTILITY",
        "event_key": "task_overdue_alert",
        "event_label": "Staff Task Overdue Alert",
        "event_category": "staff",
        "example_values": ["Rahul Kumar", "Update Solar Pipeline Report",
                           "05 May 2026", "2", "Priya Sharma"],
    },
    {
        "slug": "myntreal_kra_overdue_alert",
        "name": "KRA Overdue Alert",
        "body_text": (
            "🔴 Hi {{name}}, your KRA for today is *pending*!\n\n"
            "📊 KRA: {{kra_name}}\n"
            "🗓️ Date: {{kra_date}}\n"
            "🎯 Target: {{kra_target}}\n"
            "📋 Status: {{completion_status}}\n\n"
            "Please update your KRA completion status.\n"
            "➡️ myntreal.com/staff/kra-status"
        ),
        "footer_text": "Myntreal.com",
        "segment": "staff",
        "meta_category": "UTILITY",
        "event_key": "kra_overdue_alert",
        "event_label": "Staff KRA Overdue Alert",
        "event_category": "staff",
        "example_values": ["Rahul Kumar", "Daily Lead Calls",
                           "07 May 2026", "10 calls", "Pending"],
    },
    {
        "slug": "myntreal_ticket_created_customer",
        "name": "Myntreal Service Ticket Created",
        "body_text": (
            "✅ Dear {{name}}, your service request is registered!\n\n"
            "🎫 Ticket ID: {{ticket_id}}\n"
            "📝 Issue: {{issue}}\n"
            "📅 Date: {{date}}\n"
            "🔄 Status: Open\n\n"
            "Our team will contact you shortly.\n"
            "Quote your Ticket ID for updates.\n\n"
            "Thank you for choosing Myntreal.com! 🙏"
        ),
        "footer_text": "myntreal.com",
        "segment": "general",
        "meta_category": "UTILITY",
        "event_key": "ticket_created_customer",
        "event_label": "Service Ticket Created — Customer",
        "event_category": "ticket",
        "example_values": ["Ramesh Kumar", "TKT-2026-001",
                           "EV Battery Not Charging", "07 May 2026"],
    },
    {
        "slug": "myntreal_ticket_closed_customer",
        "name": "Myntreal Service Ticket Closed",
        "body_text": (
            "🎉 Dear {{name}}, your service ticket is *resolved*! ✅\n\n"
            "🎫 Ticket ID: {{ticket_id}}\n"
            "📝 Issue: {{issue}}\n"
            "📅 Closed On: {{date}}\n\n"
            "We hope the issue is resolved to your satisfaction.\n"
            "Your feedback matters — thank you for choosing Myntreal.com! ⭐"
        ),
        "footer_text": "myntreal.com",
        "segment": "general",
        "meta_category": "UTILITY",
        "event_key": "ticket_closed_customer",
        "event_label": "Service Ticket Closed — Customer",
        "event_category": "ticket",
        "example_values": ["Ramesh Kumar", "TKT-2026-001",
                           "EV Battery Not Charging", "07 May 2026"],
    },
    {
        "slug": "myntreal_ticket_acknowledged_customer",
        "name": "Myntreal Ticket Acknowledged",
        "body_text": (
            "👋 Dear {{name}}, we have received your service ticket!\n\n"
            "🎫 Ticket ID: {{ticket_id}}\n"
            "🔄 Status: Acknowledged\n\n"
            "Our service team is reviewing your issue.\n"
            "We will keep you updated on progress.\n\n"
            "Thank you for choosing Myntreal.com! 🙏"
        ),
        "footer_text": "myntreal.com",
        "segment": "general",
        "meta_category": "UTILITY",
        "event_key": "ticket_acknowledged",
        "event_label": "Ticket Acknowledged — Customer",
        "event_category": "ticket",
        "example_values": ["Ramesh Kumar", "TKT-2026-001"],
    },
    {
        "slug": "myntreal_ticket_resolved_customer",
        "name": "Myntreal Ticket Work Complete",
        "body_text": (
            "🎯 Dear {{name}}, your service issue is *work complete*!\n\n"
            "🎫 Ticket ID: {{ticket_id}}\n"
            "📝 Issue: {{issue}}\n"
            "✅ Status: Work Complete\n\n"
            "The ticket will be formally closed shortly.\n"
            "Thank you for choosing Myntreal.com! 🙏"
        ),
        "footer_text": "myntreal.com",
        "segment": "general",
        "meta_category": "UTILITY",
        "event_key": "ticket_resolved",
        "event_label": "Ticket Work Complete — Customer",
        "event_category": "ticket",
        "example_values": ["Ramesh Kumar", "TKT-2026-001", "EV Battery Not Charging"],
    },
    {
        "slug": "myntreal_ticket_status_update_customer",
        "name": "Myntreal Ticket Status Update",
        "body_text": (
            "🔔 Dear {{name}}, your ticket status has been updated!\n\n"
            "🎫 Ticket ID: {{ticket_id}}\n"
            "🔄 New Status: {{status}}\n"
            "📅 Updated On: {{date}}\n\n"
            "For queries, visit www.myntreal.com 🙏"
        ),
        "footer_text": "myntreal.com",
        "segment": "general",
        "meta_category": "UTILITY",
        "event_key": "ticket_status_update_customer",
        "event_label": "Ticket Status Update — Customer",
        "event_category": "ticket",
        "example_values": ["Ramesh Kumar", "TKT-2026-001",
                           "Work In Progress", "07 May 2026"],
    },
    {
        "slug": "myntreal_lead_thankyou_general",
        "name": "Myntreal Lead Thank You",
        "body_text": (
            "🙏 Dear {{name}}, thank you for choosing Myntreal.com!\n\n"
            "We have received your enquiry and our green energy team will\n"
            "connect with you shortly.\n\n"
            "📞 Reference: {{lead_ref}}\n"
            "📅 Received: {{date}}\n\n"
            "Our executive will reach out within 24 hours.\n\n"
            "Thank you for choosing Myntreal.com! 🌟"
        ),
        "footer_text": "Myntreal.com",
        "segment": "general",
        "meta_category": "UTILITY",
        "event_key": "crm_lead_created",
        "event_label": "New Lead Thank You — Customer",
        "event_category": "crm",
        "example_values": ["Suresh Patel", "MYNTREAL-LEAD-1042", "07 May 2026"],
    },
    {
        "slug": "myntreal_walkin_thankyou_customer",
        "name": "Myntreal Walk-in Thank You",
        "body_text": (
            "🙏 Dear {{name}}, thank you for visiting our showroom!\n\n"
            "We are delighted to have you here.\n"
            "Our team will connect with you shortly.\n\n"
            "📞 Reference: {{lead_ref}}\n"
            "📅 Visit Date: {{date}}\n"
            "🏬 Location: {{partner_name}}\n\n"
            "Thank you for choosing Myntreal.com! 😊"
        ),
        "footer_text": "Myntreal.com",
        "segment": "general",
        "meta_category": "UTILITY",
        "event_key": "crm_lead_walkin_created",
        "event_label": "Walk-in Thank You — Customer",
        "event_category": "crm",
        "example_values": ["Suresh Patel", "MYNTREAL-LEAD-1042",
                           "07 May 2026", "Myntreal Solar Hub Hyderabad"],
    },
    {
        "slug": "myntreal_lead_assigned_staff",
        "name": "Myntreal Lead Assigned to Staff",
        "body_text": (
            "📞 Hi {{staff_name}}, a new lead has been assigned to you!\n\n"
            "👤 Lead Name: {{lead_name}}\n"
            "📱 Phone: {{phone}}\n"
            "🏷️ Source: {{source}}\n"
            "📅 Assigned On: {{date}}\n\n"
            "Please follow up at the earliest! 💼\n"
            "➡️ myntreal.com/staff/crm"
        ),
        "footer_text": "Myntreal.com",
        "segment": "staff",
        "meta_category": "UTILITY",
        "event_key": "lead_assigned_staff",
        "event_label": "Lead Assigned — Staff Notification",
        "event_category": "crm",
        "example_values": ["Priya Sharma", "Suresh Patel",
                           "9876543210", "Walk-in", "07 May 2026"],
    },
    {
        "slug": "myntreal_lead_overdue_sales",
        "name": "Overdue Leads — Sales Alert",
        "body_text": (
            "🔔 Hi {{name}}, you have *{{count}} overdue lead(s)* pending!\n\n"
            "📋 Oldest Lead: {{oldest_lead}}\n"
            "📅 Overdue Since: {{overdue_since}}\n\n"
            "Please take action today to keep your pipeline moving. 💼\n"
            "➡️ myntreal.com/staff/crm"
        ),
        "footer_text": "Myntreal.com",
        "segment": "staff",
        "meta_category": "UTILITY",
        "event_key": "lead_overdue_sales",
        "event_label": "Overdue Leads — Sales Staff Alert",
        "event_category": "crm",
        "example_values": ["Priya Sharma", "3", "Suresh Patel - Solar EV", "04 May 2026"],
    },
    {
        "slug": "myntreal_lead_overdue_leadership",
        "name": "Overdue Leads — Leadership Summary",
        "body_text": (
            "🏢 Team Lead Overdue Report — {{date}}\n\n"
            "Hi {{name}}, your team overdue lead summary:\n\n"
            "🔴 Total Overdue Leads: {{total_overdue}}\n"
            "👥 Staff with Overdue: {{staff_count}}\n"
            "📊 Longest Overdue: {{max_days}} day(s)\n\n"
            "Please review and follow up with your team.\n"
            "➡️ myntreal.com/staff/crm"
        ),
        "footer_text": "Myntreal.com",
        "segment": "staff",
        "meta_category": "UTILITY",
        "event_key": "lead_overdue_leadership",
        "event_label": "Overdue Leads Summary — Leadership",
        "event_category": "crm",
        "example_values": ["07 May 2026", "Anjali Singh", "12", "4", "5"],
    },
    {
        "slug": "myntreal_kra_daily_summary_leader",
        "name": "KRA Daily Summary — Leader",
        "body_text": (
            "📊 Good morning, {{name}}!\n\n"
            "Team KRA summary for {{date}}:\n\n"
            "✅ Completed: {{completed_count}}\n"
            "⏳ Pending: {{pending_count}}\n"
            "🔴 Delayed: {{delayed_count}}\n"
            "👥 Total Staff: {{total_staff}}\n\n"
            "Review and motivate your team! 💪\n"
            "➡️ myntreal.com/staff/kra-status"
        ),
        "footer_text": "Myntreal.com",
        "segment": "staff",
        "meta_category": "UTILITY",
        "event_key": "kra_daily_summary_leader",
        "event_label": "KRA Daily Summary — Team Leader",
        "event_category": "staff",
        "example_values": ["Anjali Singh", "07 May 2026", "8", "3", "2", "13"],
    },
    {
        "slug": "myntreal_lead_followup_reminder",
        "name": "Lead Follow-up Reminder",
        "body_text": (
            "⏰ Hi {{name}}, you have *{{count}} lead(s)* due for follow-up today!\n\n"
            "📋 Next Up: {{next_lead}}\n"
            "📞 Phone: {{phone}}\n"
            "📅 Follow-up Due: Today\n\n"
            "Don't let any lead go cold — act now! 🔥\n"
            "➡️ myntreal.com/staff/crm"
        ),
        "footer_text": "Myntreal.com",
        "segment": "staff",
        "meta_category": "UTILITY",
        "event_key": "lead_followup_reminder",
        "event_label": "Lead Follow-up Reminder — Sales Staff",
        "event_category": "crm",
        "example_values": ["Priya Sharma", "4", "Ramesh Kumar - EV B2B", "9876543210"],
    },
    {
        "slug": "vgk_walkin_partner_notify",
        "name": "VGK Walk-in Partner Notify",
        "body_text": (
            "🎉 New Walk-in at *{{partner_name}}*!\n\n"
            "Customer *{{customer_name}}* has visited your outlet today.\n"
            "📅 Date: {{date}}\n"
            "📋 Lead Ref: {{lead_ref}}\n\n"
            "Our team will follow up with them shortly.\n"
            "Thank you for choosing VGK4U.com! 🙏"
        ),
        "footer_text": "VGK4U Partner Network",
        "segment": "partner",
        "meta_category": "UTILITY",
        "event_key": "crm_lead_walkin_partner_notify",
        "event_label": "Walk-in Lead Registered — Partner Notification",
        "event_category": "crm",
        "example_values": ["VGK Hub Hyderabad", "Rajesh Kumar", "07 May 2026", "MNR-LEAD-00123"],
    },
    {
        "slug": "zynova_tenant_approved",
        "name": "Zynova Tenant Approved",
        "body_text": (
            "🚀 Welcome to *Zynova OS*!\n\n"
            "Dear {{name}},\n"
            "Your tenant account *{{company_name}}* has been officially activated!\n\n"
            "Your SaaS workspace is ready. Access your dashboard using the sign-in details below:\n\n"
            "🌐 *Sign-In Page Link:* https://www.zynovaos.com/saas/login\n"
            "👤 *Username:* {{username}}\n"
            "🔑 *Temporary Password:* {{password}}\n\n"
            "⚠️ _For security reasons, the system will prompt you to change this temporary password immediately upon your first login._\n\n"
            "Thank you for choosing Zynova OS!"
        ),
        "footer_text": "Zynova OS Team",
        "segment": "saas",
        "meta_category": "UTILITY",
        "event_key": "saas_tenant_approved",
        "event_label": "SaaS Tenant Approved",
        "event_category": "saas",
        "example_values": ["Suresh Patel", "Green Energy Corp", "suresh@greenenergy.com", "MN00124"],
    },
    {
        "slug": "myntreal_reward_claim_ack",
        "name": "Myntreal Reward Claim Acknowledgment",
        "body_text": (
            "🎉 Congratulations, {{name}}!\n\n"
            "Your scratch card cash reward of *₹{{amount}}* for mobile recharge ({{mobile}}) has been successfully claimed and credited! ✅\n\n"
            "🌟 *Get Great Discounts on Our Services by Connecting with Us!*\n\n"
            "As a valued Myntreal customer, you are eligible for exclusive discounts across our ecosystem:\n"
            "☀️ Suryanz Solar — Save up to 90% on electricity bills + up to ₹78,000 PM Surya Ghar Govt. Subsidy & exclusive installation discounts!\n"
            "⚡ Electric Mobility Solutions — Smart electric 2-wheelers with exclusive cashback & test ride offers\n"
            "🛠️ EVolution Skill Training — Certified technical courses for EV technology\n"
            "🛡️ VGK Care & Real Dreams — Verified real estate ventures & protection schemes\n\n"
            "📞 Call or WhatsApp our team directly:\n"
            "👉 +91 85858 52738\n\n"
            "Warm Regards,\n"
            "Team Myntreal"
        ),
        "footer_text": "myntreal.com",
        "segment": "general",
        "meta_category": "UTILITY",
        "event_key": "recharge_scratch_claim_ack",
        "event_label": "Recharge Scratch Reward Claimed Acknowledgment",
        "event_category": "reward",
        "buttons": [
            {"type": "QUICK_REPLY", "text": "Interested in Solar"},
            {"type": "QUICK_REPLY", "text": "Interested in EV"},
            {"type": "QUICK_REPLY", "text": "Interested in Training"}
        ],
        "example_values": ["Ramesh Kumar", "10.00", "98****3210"],
    },
    {
        "slug": "vgk_general_broadcast_v1",
        "name": "VGK4U & MyntReal General Update (Universal Envelope)",
        "body_text": (
            "Namaste {{name}} Ji 🙏,\n\n"
            "Here is an important update regarding your *{{segment}}* profile with *VGK4U & MyntReal Group*:\n\n"
            "{{message_body}}\n\n"
            "{{signature}}\n"
            "Thank you for being a valued member of the VGK4U & MyntReal network."
        ),
        "footer_text": "VGK4U & MyntReal Official",
        "segment": "general",
        "meta_category": "UTILITY",
        "event_key": "general_broadcast_utility_envelope",
        "event_label": "General Broadcast Utility Envelope",
        "event_category": "partner",
        "buttons": [
            {"type": "QUICK_REPLY", "text": "Interested / Call Back"},
            {"type": "QUICK_REPLY", "text": "Need More Info"},
            {"type": "QUICK_REPLY", "text": "Thank You"}
        ],
        "example_values": [
            "Ramesh Kumar",
            "VGK4U Partner Network",
            "Your partner profile and monthly activity update for this cycle are now available on the portal.",
            "Warm Regards, VGK4U Supreme Administration"
        ],
    },
    {
        "slug": "mnr_promotional_campaign_v1",
        "name": "MyntReal Promotional Wishes & Campaign Envelope",
        "body_text": (
            "Namaste {{name}} Ji 🌟,\n\n"
            "Warm greetings from *VGK4U & MyntReal Group*!\n\n"
            "{{campaign_message}}\n\n"
            "Explore our flagship services in Rooftop Solar, Electric Vehicles, EV Skill Training & Verified Real Estate at https://www.myntreal.com\n\n"
            "{{signature}}\n"
            "Reply to this message anytime for priority assistance from our team."
        ),
        "footer_text": "myntreal.com | vgk4u.com",
        "segment": "general",
        "meta_category": "MARKETING",
        "event_key": "general_broadcast_marketing_envelope",
        "event_label": "General Broadcast Marketing & Wishes Envelope",
        "event_category": "crm",
        "buttons": [
            {"type": "QUICK_REPLY", "text": "Interested in Solar"},
            {"type": "QUICK_REPLY", "text": "Interested in EV"},
            {"type": "QUICK_REPLY", "text": "Call Me Back"}
        ],
        "example_values": [
            "Suresh Kumar",
            "Wishing you and your family a prosperous season! Claim up to Rs.78,000 PM Surya Ghar Solar Subsidy and exclusive benefits this month.",
            "Warm Regards, Team MyntReal & VGK4U"
        ],
    },
    {
        "slug": "vgk_general_broadcast_img_v1",
        "name": "VGK4U & MyntReal General Update (With Image Header)",
        "header_type": "image",
        "body_text": (
            "Namaste {{name}} Ji 🙏,\n\n"
            "Here is an important update regarding your *{{segment}}* profile with *VGK4U & MyntReal Group*:\n\n"
            "{{message_body}}\n\n"
            "{{signature}}\n"
            "Thank you for being a valued member of the VGK4U & MyntReal network."
        ),
        "footer_text": "VGK4U & MyntReal Official",
        "segment": "general",
        "meta_category": "UTILITY",
        "event_key": "general_broadcast_utility_img_envelope",
        "event_label": "General Broadcast Utility Image Envelope",
        "event_category": "partner",
        "buttons": [
            {"type": "QUICK_REPLY", "text": "Interested / Call Back"},
            {"type": "QUICK_REPLY", "text": "Need More Info"},
            {"type": "QUICK_REPLY", "text": "Thank You"}
        ],
        "example_values": [
            "Ramesh Kumar",
            "VGK4U Partner Network",
            "Your partner profile and monthly activity update for this cycle are now available on the portal.",
            "Warm Regards, VGK4U Supreme Administration"
        ],
    },
    {
        "slug": "mnr_promotional_campaign_img_v1",
        "name": "MyntReal Promotional Wishes & Flyer Campaign (With Image Header)",
        "header_type": "image",
        "body_text": (
            "Namaste {{name}} Ji 🌟,\n\n"
            "Warm greetings from *VGK4U & MyntReal Group*!\n\n"
            "{{campaign_message}}\n\n"
            "Explore our flagship services in Rooftop Solar, Electric Vehicles, EV Skill Training & Verified Real Estate at https://www.myntreal.com\n\n"
            "{{signature}}\n"
            "Reply to this message anytime for priority assistance from our team."
        ),
        "footer_text": "myntreal.com | vgk4u.com",
        "segment": "general",
        "meta_category": "MARKETING",
        "event_key": "general_broadcast_marketing_img_envelope",
        "event_label": "General Broadcast Marketing Image Envelope",
        "event_category": "crm",
        "buttons": [
            {"type": "QUICK_REPLY", "text": "Interested in Solar"},
            {"type": "QUICK_REPLY", "text": "Interested in EV"},
            {"type": "QUICK_REPLY", "text": "Call Me Back"}
        ],
        "example_values": [
            "Suresh Kumar",
            "Wishing you and your family a prosperous season! Claim up to Rs.78,000 PM Surya Ghar Solar Subsidy and exclusive benefits this month.",
            "Warm Regards, Team MyntReal & VGK4U"
        ],
    },
    {
        "slug": "mnr_catalog_proposal_v1",
        "name": "MyntReal Catalog Proposal V1",
        "meta_template_name": "mnr_catalog_proposal_v1",
        "body_text": (
            "Dear {{name}}! 👋\n\n"
            "Here is your personalized *{{catalog_title}}* proposal prepared by *{{staff_name}}*:\n\n"
            "📖 *Interactive Web Proposal & Calculator:*\n"
            "👉 {{url}}\n\n"
            "For queries or an immediate consultation, feel free to reply directly.\n\n"
            "Best regards,\n"
            "*{{staff_name}}*\n"
            "📞 Helpline: {{helpline}}\n"
            "MYNTREAL"
        ),
        "segment": "customer",
        "meta_category": "MARKETING",
        "event_key": "catalog_proposal_en",
        "event_label": "Digital Catalog Proposal (English)",
        "event_category": "crm",
        "example_values": [
            "Anil Kumar",
            "EVolution Training Centre — Professional EV Certifications",
            "Rahul Sharma",
            "https://www.myntreal.com/c/sample123",
            "+91 858585 2738"
        ],
    },
    {
        "slug": "mnr_catalog_proposal_te_v1",
        "name": "MyntReal Catalog Proposal Telugu V1",
        "meta_template_name": "mnr_catalog_proposal_te_v1",
        "meta_template_language": "te",
        "body_text": (
            "నమస్కారం {{name}} గారు! 👋\n\n"
            "మీ కోసం సిద్ధం చేసిన *{{catalog_title}}* ప్రతిపాదన వివరాలు ఇక్కడ ఉన్నాయి (తయారు చేసిన వారు: *{{staff_name}}*):\n\n"
            "📖 *ఆన్‌లైన్ ప్రతిపాదన మరియు వివరాలు:*\n"
            "👉 {{url}}\n\n"
            "ఏవైనా సందేహాలు ఉంటే నేరుగా మాకు సమాధానం ఇవ్వవచ్చు.\n\n"
            "ధన్యవాదాలు,\n"
            "*{{staff_name}}*\n"
            "📞 హెల్ప్‌లైన్: {{helpline}}\n"
            "MYNTREAL"
        ),
        "segment": "customer",
        "meta_category": "MARKETING",
        "event_key": "catalog_proposal_te",
        "event_label": "Digital Catalog Proposal (Telugu)",
        "event_category": "crm",
        "example_values": [
            "అనిల్ కుమార్",
            "EVolution Training Centre — Professional EV Certifications",
            "రాహుల్ శర్మ",
            "https://www.myntreal.com/c/sample123",
            "+91 858585 2738"
        ],
    },
    {
        "slug": "mnr_catalog_brochure_v1",
        "name": "MyntReal Catalog With Brochure V1",
        "meta_template_name": "mnr_catalog_brochure_v1",
        "body_text": (
            "Dear {{name}}! 👋\n\n"
            "Here is your personalized *{{catalog_title}}* proposal prepared by *{{staff_name}}*:\n\n"
            "📖 *Interactive Web Proposal:*\n"
            "👉 {{url}}\n\n"
            "📄 *Official PDF Brochure (Direct Download):*\n"
            "👉 {{pdf_url}}\n\n"
            "For queries or an immediate consultation, feel free to reply directly.\n\n"
            "Best regards,\n"
            "*{{staff_name}}*\n"
            "📞 Helpline: {{helpline}}\n"
            "MYNTREAL"
        ),
        "segment": "customer",
        "meta_category": "MARKETING",
        "event_key": "catalog_proposal_brochure",
        "event_label": "Digital Catalog With PDF Brochure",
        "event_category": "crm",
        "example_values": [
            "Anil Kumar",
            "Commercial & Residential Solar",
            "Rahul Sharma",
            "https://www.myntreal.com/c/sample123",
            "https://www.myntreal.com/catalog/mnr-catalog-web.pdf",
            "+91 858585 2738"
        ],
    },
    {
        "slug": "mnr_catalog_etc_training_v1",
        "name": "EVolution Training Centre Proposal V1",
        "meta_template_name": "mnr_catalog_etc_training_v1",
        "body_text": (
            "Dear {{name}}! 👋\n\n"
            "Here is your *EVolution Training Centre (ETC)* Certification Course Proposal prepared by *{{staff_name}}*:\n\n"
            "🎓 *Explore Course Modules, Syllabus & Pricing:*\n"
            "👉 {{url}}\n\n"
            "For admissions or batched schedules, feel free to reply directly.\n\n"
            "Best regards,\n"
            "*{{staff_name}}*\n"
            "📞 Admissions Helpline: {{helpline}}\n"
            "EVolution Training Centre — MYNTREAL"
        ),
        "segment": "customer",
        "meta_category": "MARKETING",
        "event_key": "catalog_proposal_etc",
        "event_label": "ETC Training Center Catalog Proposal",
        "event_category": "crm",
        "example_values": [
            "Anil Kumar",
            "Rahul Sharma",
            "https://www.myntreal.com/c/sample123",
            "+91 858585 2738"
        ],
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
                buttons=tdef.get("buttons", []),
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

    # Count unique positional variables {{1}}, {{2}}, etc.
    unique_positions = set(re.findall(r'\{\{(\d+)\}\}', raw_body))
    positional_count = len(unique_positions)
    examples = list(tpl.example_values or [])
    while len(examples) < positional_count:
        examples.append(f"Sample {len(examples) + 1}")
    sample_list = [str(x) for x in examples[:positional_count]]

    components = []
    body_comp: dict = {"type": "BODY", "text": raw_body}
    if positional_count > 0:
        body_comp["example"] = {"body_text": [sample_list]}
    components.append(body_comp)

    if tpl.footer_text and tpl.footer_text.strip():
        components.append({"type": "FOOTER", "text": tpl.footer_text.strip()[:60]})

    if tpl.buttons and isinstance(tpl.buttons, list) and len(tpl.buttons) > 0:
        btn_list = []
        for b in tpl.buttons[:3]: # Meta allows up to 3 quick reply buttons
            if isinstance(b, dict):
                btn_list.append({
                    "type": b.get("type", "QUICK_REPLY"),
                    "text": b.get("text", "")[:25]
                })
            elif isinstance(b, str):
                btn_list.append({
                    "type": "QUICK_REPLY",
                    "text": b[:25]
                })
        if btn_list:
            components.append({
                "type": "BUTTONS",
                "buttons": btn_list
            })

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
            tpl.meta_submitted_at = get_indian_time()
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
