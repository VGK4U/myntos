"""
Main API router for FastAPI v1
Aggregates all API endpoints preserving Flask app functionality
Includes 368 auto-generated route scaffolds for complete migration
"""

from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth, dashboard, users, admin, admin_pins, admin_earnings, 
    admin_tickets, admin_bulk, admin_password_reset, admin_members_search, rvz, rvz_supreme, rvz_awards_config, rvz_awards_regenerate, rvz_expenses, rvz_department_management, finance_admin, finance_awards_procurement, super_admin, team_management,
    income_verification, award_management, award_processing, awards_fast, financial_operations, profile, bank_kyc_admin, coupon_transfers, banners, tickets, ev_discount, whatsapp, password_reset, bonanza, financial_reports, expense_management, red_coupon_voting, secondary_verification, withdrawal, award_price_management, user_management_comprehensive, system_controls, rate_configuration, system_configuration, daily_ceiling, emergency_wallet, expense_categories, log_reports, testing, rvz_production_reset, ev_scooter_claims, training_claims, admin_data_access, rvz_recovery, rvz_password_change, user_update_controls, dc_protocol, compliance, company_earnings, feedback, gift_wise_status, unified_awards_lifecycle,
    staff_auth, staff_employees, staff_departments, staff_nda, staff_tasks, staff_day_plans, staff_time_tracker, staff_kra,
    staff_field_work, staff_work_intervals, staff_journeys, staff_timesheet, staff_accounts, staff_snapshot,
    staff_menu_settings, staff_reimbursements, staff_payroll,
    staff_mnr_user_sidebar,
    staff_offboarding,
    partner_orders,
    partner_auth,
    crm,
    universal_engagement,
    sandbox,
    myntreal_incentives,
    facebook_leads,
    receipt,
    staff_points_insurance,
    staff_field_allowance,
    mnr_financial_statement,
    member_lifecycle,
    call_tracking,
    call_quality,
    crm_dialer,
    crm_lead_sync,
    crm_commissions,
    catalog,
    session_analytics,
    marketplace,
    marketplace_po,
    etc_students,
    pingme,
    vgk_team,
    vgk_auth,
    vgk_cash_income,
    vgk_gallery,
    whatsapp_config,
    operator_calls,
    promo,
)

# Scaffold routers are mounted in main.py at ROOT level to match Flask routing

# Create main API router
api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(team_management.router, prefix="/team", tags=["team"])
api_router.include_router(financial_operations.router, prefix="/financial-operations/income", tags=["financial-operations"])
api_router.include_router(award_management.router, prefix="/award-management", tags=["award-management"])
api_router.include_router(award_processing.router, prefix="/awards", tags=["Award Processing Workflow"])
api_router.include_router(awards_fast.router, tags=["Fast Awards - Optimized"])
api_router.include_router(admin.router, tags=["admin"])
api_router.include_router(admin_pins.router, prefix="/admin", tags=["admin-pins"])
api_router.include_router(admin_earnings.router, prefix="/admin", tags=["admin-earnings"])
api_router.include_router(admin_tickets.router, prefix="/admin", tags=["admin-tickets"])
api_router.include_router(admin_bulk.router, prefix="/admin", tags=["admin-bulk"])
api_router.include_router(admin_password_reset.router, prefix="/admin", tags=["admin-password-reset"])
api_router.include_router(admin_data_access.router, tags=["Admin Data Access"])
api_router.include_router(admin_members_search.router, tags=["Admin Members Search"])
api_router.include_router(finance_admin.router, tags=["Finance Admin"])
api_router.include_router(finance_awards_procurement.router, tags=["Finance Admin - Awards & Bonanza Procurement (WV/DC)"])
api_router.include_router(super_admin.router, tags=["Super Admin"])
# REMOVED: api_router.include_router(rvz.router, tags=["RVZ ID Supreme Admin"]) - Duplicate registration (already in main.py)
api_router.include_router(rvz_supreme.router, tags=["RVZ Supreme Withdrawal Management"])
api_router.include_router(rvz_awards_config.router, tags=["RVZ Awards Configuration - Master Data"])
api_router.include_router(mnr_financial_statement.router, tags=["MNR Financial Statement"])
api_router.include_router(rvz_awards_regenerate.router, tags=["RVZ Awards Regeneration"])
api_router.include_router(rvz_expenses.router, tags=["RVZ Expense Management - Supreme Authority"])
api_router.include_router(income_verification.router, prefix="/income-verification", tags=["Income Verification"])
api_router.include_router(profile.router, prefix="/profile", tags=["User Profile"])
api_router.include_router(bank_kyc_admin.router, prefix="/kyc-bank", tags=["KYC & Bank Admin"])
api_router.include_router(coupon_transfers.router, prefix="/coupon-transfers", tags=["Coupon Transfers"])
api_router.include_router(banners.router, tags=["Banners & Communication"])
api_router.include_router(tickets.router, tags=["Support Tickets"])
api_router.include_router(ev_discount.router, tags=["EV Discount Coupons"])
api_router.include_router(whatsapp.router, tags=["WhatsApp Messaging"])
api_router.include_router(password_reset.router, tags=["Password Reset"])
api_router.include_router(bonanza.router, tags=["Bonanza System"])
api_router.include_router(financial_reports.router, tags=["Financial Reports"])
api_router.include_router(expense_management.router, tags=["Expense Management"])
api_router.include_router(red_coupon_voting.router, tags=["Red Coupon Voting"])
api_router.include_router(secondary_verification.router, prefix="/secondary", tags=["Secondary Verification"])
api_router.include_router(withdrawal.router, tags=["Withdrawal & Payout"])
api_router.include_router(award_price_management.router, tags=["Award Price Management"])
api_router.include_router(user_management_comprehensive.router, prefix="/users", tags=["User Management"])
api_router.include_router(system_controls.router, tags=["RVZ ID System Controls"])
api_router.include_router(rate_configuration.router, tags=["RVZ ID Rate Configuration"])
api_router.include_router(system_configuration.router, tags=["RVZ ID System Configuration"])
api_router.include_router(daily_ceiling.router, tags=["RVZ ID Daily Ceiling"])
api_router.include_router(emergency_wallet.router, tags=["RVZ ID Emergency Wallet"])
api_router.include_router(expense_categories.router, tags=["Expense Categories"])
api_router.include_router(log_reports.router, prefix="/log-reports", tags=["Log Reports"])
api_router.include_router(testing.router, tags=["System Testing"])

# Task #33 — VGK4U Member Parity Phase 1 (audience tab switch audit)
from app.api.v1.endpoints import audience_audit  # noqa: E402
api_router.include_router(audience_audit.router, tags=["VGK4U Audience Audit"])

# Task #34 — VGK4U Member Parity Phase 2 (Write-Flow Modules)
from app.api.v1.endpoints import vgk_member_writes  # noqa: E402
api_router.include_router(vgk_member_writes.router, prefix="/vgk-member", tags=["VGK4U Member Writes (Phase 2)"])

# Task #37 — VGK4U Member Reads (audience-aware data for the 16 VGK4U pages)
from app.api.v1.endpoints import vgk_member_reads  # noqa: E402
api_router.include_router(vgk_member_reads.awards_router)
api_router.include_router(vgk_member_reads.income_router)
api_router.include_router(vgk_member_reads.ev_router)
api_router.include_router(vgk_member_reads.franchise_router)
api_router.include_router(vgk_member_reads.insurance_router)
api_router.include_router(vgk_member_reads.training_router)
api_router.include_router(vgk_member_reads.vgk_router)
api_router.include_router(rvz_production_reset.router, tags=["RVZ ID Production Reset"])
api_router.include_router(ev_scooter_claims.router, tags=["EV Scooter Claims"])
api_router.include_router(training_claims.router, tags=["Training Course Claims"])
api_router.include_router(rvz_recovery.router, tags=["RVZ Data Recovery"])
api_router.include_router(rvz_password_change.router, prefix="/rvz/password", tags=["RVZ Password Management"])
api_router.include_router(user_update_controls.router, prefix="/rvz", tags=["RVZ User Update Controls"])
api_router.include_router(dc_protocol.router, prefix="/dc-protocol", tags=["DC Protocol - Shadow Mode"])
api_router.include_router(compliance.router, prefix="/compliance", tags=["Compliance Tracking - TDS/GST/Handling Charges"])
api_router.include_router(company_earnings.router, prefix="/company-earnings", tags=["Company Earnings - Revenue & Expense Tracking"])
api_router.include_router(feedback.router, prefix="/feedback", tags=["User Feedback & Announcements"])
api_router.include_router(gift_wise_status.router, prefix="/award-management", tags=["Gift-Wise Status - Finance & RVZ ONLY"])
api_router.include_router(unified_awards_lifecycle.router, tags=["Unified Awards & Bonanza Lifecycle - DC Protocol"])

# RVZ Department Management (VGK/EA/HR - Nov 29, 2025)
api_router.include_router(rvz_department_management.router, prefix="/rvz/departments", tags=["RVZ Department Management - Advanced"])

# Staff System Routes (DC Protocol Compliant)
api_router.include_router(staff_auth.router, tags=["Staff Auth"])
api_router.include_router(staff_employees.router, tags=["Staff Employees"])
api_router.include_router(staff_departments.router, tags=["Staff Departments"])
api_router.include_router(staff_nda.router, tags=["Staff NDA Management"])
api_router.include_router(staff_tasks.router, prefix="/staff/tasks", tags=["Staff Task Management"])
api_router.include_router(staff_day_plans.router, prefix="/staff/day-plans", tags=["Staff Day Planner"])
api_router.include_router(staff_time_tracker.router, prefix="/staff/attendance", tags=["Staff Time Tracker & Attendance"])
api_router.include_router(staff_kra.router, prefix="/staff/kra", tags=["Staff KRA Performance Management"])
api_router.include_router(staff_field_work.router, prefix="/staff/field-work", tags=["Staff Field Work & KM Tracking"])
api_router.include_router(staff_work_intervals.router, prefix="/staff/intervals", tags=["Staff Work Intervals & Activity Linking"])
api_router.include_router(staff_journeys.router, prefix="/staff/journeys", tags=["Staff Journey Tracking & Reimbursement"])
api_router.include_router(staff_timesheet.router, prefix="/staff/timesheet", tags=["Staff Timesheet Entry & Approval"])
api_router.include_router(staff_snapshot.router, prefix="/staff", tags=["Staff Operations Snapshot"])

# Staff Financial Management System (DC_SFMS_001 - Dec 06, 2025)
api_router.include_router(staff_accounts.router, tags=["Staff Financial Management - Accounts"])
api_router.include_router(staff_reimbursements.router, tags=["Staff Reimbursement Claims"])
api_router.include_router(staff_offboarding.router, tags=["Staff Offboarding & Data Transfer"])

# Official Partner Order Management System (DC_PARTNER_001 - Dec 06, 2025)
api_router.include_router(partner_orders.router, tags=["Official Partner Order Management"])

# Partner Authentication System (DC_PARTNER_AUTH_001 - Dec 2025)
api_router.include_router(partner_auth.router, tags=["Partner Authentication"])

# Universal CRM/Lead Management System (DC Protocol - Dec 08, 2025)
api_router.include_router(crm.router, prefix="/crm", tags=["Universal CRM - Lead Management"])

# Universal Engagement System (DC Protocol - Dec 08, 2025)
api_router.include_router(universal_engagement.router, tags=["Universal Engagement - Ratings, Comments, Shares"])

# RVZ Menu Visibility & Accessibility Control (DC Protocol - Dec 08, 2025)
api_router.include_router(staff_menu_settings.router, tags=["Staff Menu Access Control"])

# Sandbox Testing Environment (DC Protocol - Dec 2025)
api_router.include_router(sandbox.router, prefix="/staff", tags=["Sandbox Testing Environment"])

# MyntReal & Zynova Incentive System (DC Protocol - Dec 28, 2025)
api_router.include_router(myntreal_incentives.router, prefix="/myntreal", tags=["MyntReal & Zynova Incentive System"])

# Facebook Lead Ads Integration (DC Protocol - Jan 04, 2026)
api_router.include_router(facebook_leads.router, prefix="/facebook-leads", tags=["Facebook Lead Ads Integration"])

# Staff Payroll Management System (DC Protocol - Jan 07, 2026)
api_router.include_router(staff_payroll.router, tags=["Staff Payroll Management"])

# Staff MNR User Sidebar (DC Protocol - Jan 08, 2026)
api_router.include_router(staff_mnr_user_sidebar.router, tags=["Staff MNR User Sidebar - Member Data Access"])

# Receipt Downloads (DC Protocol - Jan 2026)
api_router.include_router(receipt.router, prefix="/receipt", tags=["Receipt Downloads"])

# MNR Points & Insurance Management (DC Protocol - Feb 2026)
api_router.include_router(staff_points_insurance.router, prefix="/staff/points-insurance", tags=["Staff MNR Points & Insurance Management"])

# Staff Field Allowance Management (DC Protocol - Feb 2026)
api_router.include_router(staff_field_allowance.router, tags=["Staff Field Allowance Management"])

# Member Lifecycle Tracker (DC Protocol - Feb 17, 2026)
api_router.include_router(member_lifecycle.router, tags=["Member Lifecycle Tracker"])

# Staff Call Tracking System (DC Protocol - Feb 2026)
api_router.include_router(call_tracking.router, prefix="/call-tracking", tags=["Staff Call Tracking System"])
api_router.include_router(call_quality.router, tags=["Call Quality Review System"])
api_router.include_router(crm_dialer.router, prefix="/crm", tags=["CRM Auto Dialer"])
api_router.include_router(crm_lead_sync.router, prefix="/crm", tags=["CRM Google Sheets Lead Sync"])
api_router.include_router(crm_commissions.router, tags=["CRM Commissions"])

# Catalog Sharing & Analytics (DC Protocol - Feb 26, 2026)
api_router.include_router(catalog.router, prefix="/catalog", tags=["Catalog Sharing & Analytics"])
api_router.include_router(session_analytics.router, prefix="/staff", tags=["Session Analytics"])

# MNR E-Com Lite — Marketplace Phase 1 + 2 (DC Protocol - Feb 2026)
api_router.include_router(marketplace.router, prefix="/marketplace", tags=["MNR Marketplace Lite"])
api_router.include_router(marketplace_po.router, prefix="/marketplace", tags=["VGK4U PO Management"])
api_router.include_router(etc_students.router, prefix="/etc", tags=["ETC Training Centre"])

# VGK Assistant — AI Voice & Text Assistant (DC_VGK_001 - Mar 2026)
api_router.include_router(pingme.router, tags=["VGK Assistant"])

# VGK Team Partner Module (DC Protocol Mar 2026)
api_router.include_router(vgk_team.router,        prefix="/vgk", tags=["VGK Team"])
api_router.include_router(vgk_auth.router,        prefix="/vgk", tags=["VGK Auth"])
api_router.include_router(vgk_cash_income.router, prefix="/vgk", tags=["VGK Cash Income"])
api_router.include_router(vgk_gallery.router,     tags=["VGK Gallery"])

# VGK Vendor Master System (DC Protocol Mar 2026)
from app.api.v1.endpoints import vgk_vendors
api_router.include_router(vgk_vendors.router, tags=["VGK Vendor System"])

# Health check for API
# WhatsApp Configuration Center (DC Protocol Mar 2026)
api_router.include_router(whatsapp_config.router, prefix="/whatsapp-config", tags=["WhatsApp Config"])

# MyOperator Call Dashboard (DC Protocol Mar 2026)
api_router.include_router(operator_calls.router, prefix="/operator-calls", tags=["MyOperator Call Dashboard"])

# Promoter / Influencer Referral System (DC Protocol Apr 2026)
api_router.include_router(promo.router, prefix="/promo", tags=["Promoter Referral System"])

@api_router.get("/health")
async def api_health():
    """API health check"""
    return {
        "status": "healthy",
        "api_version": "v1",
        "message": "MNR Reference System API is running"
    }