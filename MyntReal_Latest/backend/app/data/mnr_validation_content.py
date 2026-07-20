"""
DC Protocol: MNR System Validation Content
Enterprise-grade enforcement validation data for all MNR pages.
Covers financial correctness, approval chains, status transitions, and security.
"""

MNR_VALIDATION_SECTION_DESCRIPTIONS = {
    "mnr-users": {
        "description": "Validate member registration, binary tree placement, activation flow, KYC integrity, and sponsorship chain.",
        "icon": "fas fa-users",
        "risk_level": "critical"
    },
    "mnr-approvals": {
        "description": "Validate KYC/Bank approval chain, multi-stage verification, rejection handling, and data consistency.",
        "icon": "fas fa-check-double",
        "risk_level": "critical"
    },
    "mnr-pins": {
        "description": "Validate PIN purchase, generation, assignment, activation flow, and point value calculation (Platinum=1.0, Diamond=0.5, Star=0.0).",
        "icon": "fas fa-key",
        "risk_level": "critical"
    },
    "mnr-income": {
        "description": "Validate 4-stream income calculation: Direct Referral, Matching Referral, Ved Income, Guru Dakshina (2%). Precision and daily auto-approval.",
        "icon": "fas fa-chart-line",
        "risk_level": "critical"
    },
    "mnr-finance": {
        "description": "Validate financial reporting accuracy, transaction reconciliation, and compliance with Indian accounting standards.",
        "icon": "fas fa-landmark",
        "risk_level": "critical"
    },
    "mnr-withdrawals": {
        "description": "Validate auto-generated withdrawal pipeline (Mon-Sat 7AM, >Rs 2000, Rs 1000 buffer), 8% Admin Charge + 2% TDS deductions, and dual-wallet splits.",
        "icon": "fas fa-money-bill-wave",
        "risk_level": "critical"
    },
    "mnr-awards": {
        "description": "Validate 6-stage award lifecycle, qualification criteria, approval chain, and EV coupon redemption (6 benefits).",
        "icon": "fas fa-trophy",
        "risk_level": "high"
    },
    "mnr-communications": {
        "description": "Validate announcement submission, review workflow, media handling, and role-based distribution.",
        "icon": "fas fa-bullhorn",
        "risk_level": "medium"
    },
    "mnr-config": {
        "description": "Validate system configuration persistence, package definitions, rate tables, and cascade effects on live members.",
        "icon": "fas fa-cogs",
        "risk_level": "critical"
    },
    "mnr-data": {
        "description": "Validate data export accuracy, report generation, member statistics, and aggregation correctness.",
        "icon": "fas fa-database",
        "risk_level": "high"
    },
    "mnr-security": {
        "description": "Validate access control, password policies, session management, and admin action audit trails.",
        "icon": "fas fa-shield-alt",
        "risk_level": "critical"
    },
    "mnr-admin": {
        "description": "Validate admin panel functions, supreme admin restrictions, and admin-only operation enforcement.",
        "icon": "fas fa-user-shield",
        "risk_level": "critical"
    },
    "mnr-user": {
        "description": "Validate member portal functions, self-service capabilities, and data visibility restrictions.",
        "icon": "fas fa-user",
        "risk_level": "high"
    },
    "staff_mnr_user_dashboard": {
        "description": "Validate staff MNR access, cross-portal data viewing, and audit logging for staff-initiated MNR actions.",
        "icon": "fas fa-tachometer-alt",
        "risk_level": "high"
    },
    "staff_mnr_user_members": {
        "description": "Validate staff access to member data with ownership checks and audit trail.",
        "icon": "fas fa-users-cog",
        "risk_level": "high"
    },
    "staff_mnr_user_mnr": {
        "description": "Validate staff MNR operations, approval capabilities, and action scope limitations.",
        "icon": "fas fa-sitemap",
        "risk_level": "high"
    },
    "staff_mnr_user_awards": {
        "description": "Validate staff award management, qualification verification, and approval permissions.",
        "icon": "fas fa-medal",
        "risk_level": "medium"
    },
    "staff_mnr_user_coupons": {
        "description": "Validate coupon management, redemption tracking, and benefit allocation.",
        "icon": "fas fa-ticket-alt",
        "risk_level": "medium"
    },
    "staff_mnr_user_announcements": {
        "description": "Validate staff announcement management for MNR members.",
        "icon": "fas fa-megaphone",
        "risk_level": "low"
    },
    "staff_mnr_user_myntreal": {
        "description": "Validate Mynt Real integration pages and data consistency.",
        "icon": "fas fa-building",
        "risk_level": "medium"
    },
    "staff_mnr_user_system": {
        "description": "Validate system configuration pages accessible via staff MNR portal.",
        "icon": "fas fa-server",
        "risk_level": "high"
    },
    "staff_mnr_user_zynova": {
        "description": "Validate VGK4U dual-segment pages accessible via staff MNR portal.",
        "icon": "fas fa-layer-group",
        "risk_level": "medium"
    },
}

MNR_VALIDATION_SECTION_ORDER = [
    "mnr-users", "mnr-approvals", "mnr-pins", "mnr-income",
    "mnr-finance", "mnr-withdrawals", "mnr-awards", "mnr-communications",
    "mnr-config", "mnr-data", "mnr-security", "mnr-admin", "mnr-user",
    "staff_mnr_user_dashboard", "staff_mnr_user_members", "staff_mnr_user_mnr",
    "staff_mnr_user_awards", "staff_mnr_user_coupons",
    "staff_mnr_user_announcements", "staff_mnr_user_myntreal",
    "staff_mnr_user_system", "staff_mnr_user_zynova"
]

MNR_RISK_DEFINITIONS = {
    "critical": {"label": "CRITICAL", "color": "#dc2626", "description": "Financial loss, data corruption, or regulatory non-compliance"},
    "major": {"label": "MAJOR", "color": "#f59e0b", "description": "Significant business impact, approval chain bypass, or income miscalculation"},
    "moderate": {"label": "MODERATE", "color": "#3b82f6", "description": "Operational disruption or data inconsistency without financial impact"},
    "low": {"label": "LOW", "color": "#059669", "description": "Minor cosmetic or non-blocking issue"}
}

MNR_GLOBAL_ENFORCEMENT_RULES = {
    "financial_precision": {
        "title": "Financial Precision & Calculation Rules",
        "status": "MANDATORY",
        "checks": [
            "All monetary values stored as DECIMAL(18,2) — never FLOAT",
            "Income calculations use banker's rounding (ROUND_HALF_EVEN)",
            "Wallet balance updates use row-level locking (SELECT ... FOR UPDATE)",
            "Earning/Withdrawable wallet splits enforced at database trigger level",
            "Deduction percentages (8% Admin + 2% TDS) applied server-side only",
            "Rs 1,000 buffer enforced in withdrawal query — not front-end JS",
            "Daily income auto-approval capped at system-configured maximum",
            "All financial operations wrapped in database transactions with rollback"
        ]
    },
    "approval_chain_integrity": {
        "title": "Approval Chain Integrity",
        "status": "MANDATORY",
        "checks": [
            "Multi-stage approval enforced: cannot skip stages via direct API",
            "Self-approval blocked at API level — approver != requestor",
            "Approval actions require explicit role verification per MENU_MASTER",
            "Rejected items require re-submission, cannot be directly re-approved",
            "Bulk approval validates each record individually within transaction",
            "Approval timestamps are server-generated, not client-submitted",
            "All approval/rejection actions audit-logged with user ID and reason"
        ]
    },
    "binary_tree_integrity": {
        "title": "Binary Tree Structure Enforcement",
        "status": "MANDATORY",
        "checks": [
            "Automatic binary placement algorithm enforced server-side",
            "Sponsor chain validated — cannot sponsor self or create circular reference",
            "Left/Right placement validated — no duplicate placement in same position",
            "Tree depth limits enforced to prevent stack overflow in traversal",
            "Binary tree modifications logged in audit trail",
            "Sponsor ID validated against active member records",
            "Re-placement after deactivation follows documented rules"
        ]
    },
    "api_security": {
        "title": "API Security & Access Control",
        "status": "MANDATORY",
        "checks": [
            "JWT token validated on every MNR endpoint",
            "MNR ID format validation (pattern matching) on all member references",
            "Admin endpoints restricted to verified admin roles only",
            "Member endpoints enforce data ownership — can only view own data",
            "SQL injection prevention via SQLAlchemy ORM parameterized queries",
            "Rate limiting on financial endpoints to prevent abuse",
            "CORS policy enforced — no cross-origin financial operations",
            "All file uploads validated for type, size, and path traversal"
        ]
    },
    "data_consistency": {
        "title": "Cross-Module Data Consistency",
        "status": "MANDATORY",
        "checks": [
            "Wallet balance = SUM(credits) - SUM(debits) — verified by reconciliation job",
            "Income records match wallet credit entries — daily reconciliation",
            "Withdrawal amounts match wallet debit entries — no orphaned debits",
            "PIN point values match package configuration — no manual overrides",
            "Member activation status synced with PIN usage records",
            "Award qualifications re-validated on status transitions",
            "Binary tree member count matches active member records"
        ]
    },
    "mobile_web_enforcement": {
        "title": "Mobile vs Web Parity Rules",
        "status": "MANDATORY",
        "checks": [
            "Same API endpoints used by both web and mobile (Capacitor)",
            "All form validations present in both platforms",
            "All approval buttons and actions available in both platforms",
            "Income/withdrawal/wallet views identical across platforms",
            "KYC/Bank document upload works identically on both",
            "Any platform-specific difference = DEFECT to be filed and tracked"
        ]
    }
}

MNR_WORKFLOW_VALIDATIONS = {
    "member_activation": {
        "title": "Member Activation Pipeline",
        "module": "mnr-users",
        "states": ["Registered", "PIN Purchased", "Payment Verified", "PIN Generated", "PIN Assigned", "PIN Used", "Account Active"],
        "transitions": [
            {"from": "Registered", "to": "PIN Purchased", "who": "Member/Sponsor", "condition": "Valid package selected, payment initiated"},
            {"from": "PIN Purchased", "to": "Payment Verified", "who": "Admin/System", "condition": "Payment receipt verified or auto-confirmed"},
            {"from": "Payment Verified", "to": "PIN Generated", "who": "System", "condition": "Auto-generation on payment verification"},
            {"from": "PIN Generated", "to": "PIN Assigned", "who": "Admin/Sponsor", "condition": "PIN linked to target member"},
            {"from": "PIN Assigned", "to": "PIN Used", "who": "Member", "condition": "Member activates with assigned PIN"},
            {"from": "PIN Used", "to": "Account Active", "who": "System", "condition": "Binary tree placement completed, income engine activated"},
        ],
        "invalid_transitions": [
            {"from": "Registered", "to": "Account Active", "reason": "Cannot skip PIN purchase and activation stages"},
            {"from": "PIN Purchased", "to": "PIN Used", "reason": "Payment must be verified and PIN generated first"},
            {"from": "Account Active", "to": "Registered", "reason": "Cannot deactivate to registered state — separate deactivation flow"},
            {"from": "PIN Generated", "to": "Payment Verified", "reason": "Cannot reverse PIN generation"},
        ],
        "lock_conditions": [
            "Active accounts cannot be re-activated with different PIN",
            "Used PINs permanently locked — cannot be reassigned",
            "Payment verification locks payment record from modification"
        ],
        "escalation": "Unverified payments older than 48 hours escalated to admin",
        "audit_required": True,
        "risk_level": "critical"
    },
    "kyc_bank_approval": {
        "title": "KYC & Bank Approval Flow",
        "module": "mnr-approvals",
        "states": ["Not Submitted", "Submitted", "Under Review", "Staff Verified", "Admin Approved", "Rejected", "Re-Submitted"],
        "transitions": [
            {"from": "Not Submitted", "to": "Submitted", "who": "Member", "condition": "All required documents uploaded"},
            {"from": "Submitted", "to": "Under Review", "who": "System", "condition": "Auto-queued for staff review"},
            {"from": "Under Review", "to": "Staff Verified", "who": "Staff", "condition": "Document authenticity verified"},
            {"from": "Staff Verified", "to": "Admin Approved", "who": "Admin", "condition": "Final approval with authority check"},
            {"from": "Under Review", "to": "Rejected", "who": "Staff/Admin", "condition": "Rejection reason mandatory"},
            {"from": "Staff Verified", "to": "Rejected", "who": "Admin", "condition": "Override rejection with reason"},
            {"from": "Rejected", "to": "Re-Submitted", "who": "Member", "condition": "Updated documents uploaded"},
            {"from": "Re-Submitted", "to": "Under Review", "who": "System", "condition": "Auto-queued for re-review"},
        ],
        "invalid_transitions": [
            {"from": "Not Submitted", "to": "Admin Approved", "reason": "Cannot approve without document submission and review"},
            {"from": "Rejected", "to": "Admin Approved", "reason": "Must re-submit and go through review again"},
            {"from": "Admin Approved", "to": "Not Submitted", "reason": "Cannot revert approved KYC — separate revocation flow"},
        ],
        "lock_conditions": [
            "Approved KYC locked — modification requires admin revocation",
            "Bank details locked after first successful withdrawal",
            "Approved documents cannot be replaced without admin override"
        ],
        "escalation": "Pending reviews older than 72 hours escalated to admin",
        "audit_required": True,
        "risk_level": "critical"
    },
    "income_pipeline": {
        "title": "Income Calculation & Credit Pipeline",
        "module": "mnr-income",
        "states": ["Triggered", "Calculated", "Pending Approval", "Approved", "Credited to Wallet", "Disputed"],
        "transitions": [
            {"from": "Triggered", "to": "Calculated", "who": "System (APScheduler)", "condition": "Binary tree event triggers calculation"},
            {"from": "Calculated", "to": "Pending Approval", "who": "System", "condition": "Auto-queued for daily approval batch"},
            {"from": "Pending Approval", "to": "Approved", "who": "System (Daily Auto)", "condition": "Daily auto-approval at configured time"},
            {"from": "Approved", "to": "Credited to Wallet", "who": "System", "condition": "Wallet credit transaction executed"},
            {"from": "Approved", "to": "Disputed", "who": "Admin", "condition": "Manual hold for investigation"},
            {"from": "Disputed", "to": "Approved", "who": "Admin", "condition": "Investigation resolved, cleared for credit"},
        ],
        "invalid_transitions": [
            {"from": "Triggered", "to": "Credited to Wallet", "reason": "Cannot skip calculation and approval stages"},
            {"from": "Credited to Wallet", "to": "Calculated", "reason": "Cannot reverse credited income — separate reversal flow"},
            {"from": "Calculated", "to": "Credited to Wallet", "reason": "Must pass through approval stage"},
        ],
        "lock_conditions": [
            "Credited income locked — reversal requires separate admin action with audit",
            "Daily auto-approval window: configured time only, no manual trigger of batch",
            "Income calculation uses snapshot of tree at trigger time — immutable"
        ],
        "escalation": "Disputed income not resolved within 7 days escalated to supreme admin",
        "audit_required": True,
        "risk_level": "critical"
    },
    "withdrawal_chain": {
        "title": "Withdrawal Processing Chain",
        "module": "mnr-withdrawals",
        "states": ["Auto-Generated", "Pending Review", "Admin Approved", "Processing", "Paid", "Rejected", "Cancelled"],
        "transitions": [
            {"from": "Auto-Generated", "to": "Pending Review", "who": "System", "condition": "Mon-Sat 7AM, balance > Rs 2000, Rs 1000 buffer maintained"},
            {"from": "Pending Review", "to": "Admin Approved", "who": "Admin", "condition": "KYC approved, bank verified, no holds"},
            {"from": "Admin Approved", "to": "Processing", "who": "Finance", "condition": "Payment batch initiated"},
            {"from": "Processing", "to": "Paid", "who": "System", "condition": "Bank confirmation received"},
            {"from": "Pending Review", "to": "Rejected", "who": "Admin", "condition": "Rejection reason mandatory, amount refunded to wallet"},
            {"from": "Pending Review", "to": "Cancelled", "who": "Member/System", "condition": "Member cancels or system timeout"},
        ],
        "invalid_transitions": [
            {"from": "Auto-Generated", "to": "Paid", "reason": "Cannot skip admin approval and processing"},
            {"from": "Paid", "to": "Auto-Generated", "reason": "Cannot reverse paid withdrawal — separate refund flow"},
            {"from": "Rejected", "to": "Admin Approved", "reason": "Rejected withdrawal must be re-generated"},
            {"from": "Cancelled", "to": "Processing", "reason": "Cancelled withdrawal cannot be resumed"},
        ],
        "lock_conditions": [
            "Paid withdrawals permanently locked",
            "Processing withdrawals cannot be cancelled",
            "Sunday: no auto-generation (Mon-Sat only)",
            "KYC must be approved before any withdrawal can be approved",
            "Bank details must be verified before withdrawal approval"
        ],
        "escalation": "Pending withdrawals > 5 days escalated to finance head",
        "audit_required": True,
        "risk_level": "critical"
    },
    "award_lifecycle": {
        "title": "Award & Recognition Lifecycle",
        "module": "mnr-awards",
        "states": ["Qualification Check", "Nominated", "Under Review", "Approved", "Awarded", "Redeemed"],
        "transitions": [
            {"from": "Qualification Check", "to": "Nominated", "who": "System", "condition": "Member meets all qualification criteria"},
            {"from": "Nominated", "to": "Under Review", "who": "System", "condition": "Auto-queued for admin review"},
            {"from": "Under Review", "to": "Approved", "who": "Admin", "condition": "Qualification re-verified, approved"},
            {"from": "Approved", "to": "Awarded", "who": "System", "condition": "Award record created, member notified"},
            {"from": "Awarded", "to": "Redeemed", "who": "Member", "condition": "Award benefit claimed"},
            {"from": "Under Review", "to": "Qualification Check", "who": "Admin", "condition": "Rejected — criteria not met, re-check scheduled"},
        ],
        "invalid_transitions": [
            {"from": "Qualification Check", "to": "Awarded", "reason": "Cannot skip nomination and approval"},
            {"from": "Redeemed", "to": "Nominated", "reason": "Cannot un-redeem an award"},
            {"from": "Awarded", "to": "Under Review", "reason": "Cannot revoke awarded status — separate revocation flow"},
        ],
        "lock_conditions": [
            "Redeemed awards permanently locked",
            "Award qualification snapshot taken at nomination — tree changes don't affect",
            "EV coupon benefits locked after partial redemption"
        ],
        "escalation": "Pending nominations > 14 days auto-escalated",
        "audit_required": True,
        "risk_level": "high"
    },
    "pin_management": {
        "title": "PIN Purchase & Assignment Flow",
        "module": "mnr-pins",
        "states": ["Order Placed", "Payment Pending", "Payment Verified", "PIN Generated", "Assigned", "Used", "Expired"],
        "transitions": [
            {"from": "Order Placed", "to": "Payment Pending", "who": "Member/Sponsor", "condition": "Package selected, order confirmed"},
            {"from": "Payment Pending", "to": "Payment Verified", "who": "Admin/System", "condition": "Payment receipt uploaded and verified"},
            {"from": "Payment Verified", "to": "PIN Generated", "who": "System", "condition": "Auto-generation with unique PIN code"},
            {"from": "PIN Generated", "to": "Assigned", "who": "Purchaser/Admin", "condition": "Target member MNR ID provided"},
            {"from": "Assigned", "to": "Used", "who": "Member", "condition": "Member activates account with PIN"},
            {"from": "PIN Generated", "to": "Expired", "who": "System", "condition": "Unused PIN expired after configured period"},
            {"from": "Assigned", "to": "Expired", "who": "System", "condition": "Assigned but unused PIN expired"},
        ],
        "invalid_transitions": [
            {"from": "Used", "to": "Assigned", "reason": "Used PIN cannot be unassigned or reassigned"},
            {"from": "Expired", "to": "PIN Generated", "reason": "Expired PIN cannot be reactivated"},
            {"from": "Order Placed", "to": "Used", "reason": "Cannot skip payment and generation stages"},
        ],
        "lock_conditions": [
            "Used PINs permanently locked with full audit trail",
            "PIN point values (Platinum=1.0, Diamond=0.5, Star=0.0) set at generation, immutable",
            "PIN code uniqueness enforced at database constraint level",
            "Expired PINs cannot be reactivated — new purchase required"
        ],
        "escalation": "Unverified payments > 72 hours escalated to admin",
        "audit_required": True,
        "risk_level": "critical"
    },
    "ev_coupon_redemption": {
        "title": "EV Coupon Redemption Flow",
        "module": "mnr-awards",
        "states": ["Issued", "Active", "Partial Redemption", "Fully Redeemed", "Expired", "Cancelled"],
        "transitions": [
            {"from": "Issued", "to": "Active", "who": "System", "condition": "Award approved, coupon activated"},
            {"from": "Active", "to": "Partial Redemption", "who": "Member", "condition": "1-5 of 6 benefits claimed"},
            {"from": "Partial Redemption", "to": "Fully Redeemed", "who": "Member", "condition": "All 6 benefits claimed"},
            {"from": "Active", "to": "Expired", "who": "System", "condition": "Validity period ended"},
            {"from": "Partial Redemption", "to": "Expired", "who": "System", "condition": "Validity ended with remaining benefits"},
            {"from": "Active", "to": "Cancelled", "who": "Admin", "condition": "Admin cancellation with reason"},
        ],
        "invalid_transitions": [
            {"from": "Fully Redeemed", "to": "Active", "reason": "Cannot un-redeem benefits"},
            {"from": "Expired", "to": "Active", "reason": "Cannot reactivate expired coupon"},
            {"from": "Cancelled", "to": "Active", "reason": "Cancelled coupons cannot be reactivated"},
        ],
        "lock_conditions": [
            "Each benefit can only be redeemed once",
            "Fully redeemed coupons permanently locked",
            "Benefit redemption order not enforced but tracked"
        ],
        "escalation": "Expiring coupons trigger member notification 30 days before",
        "audit_required": True,
        "risk_level": "high"
    },
    "announcement_workflow": {
        "title": "Announcement Review & Publishing",
        "module": "mnr-communications",
        "states": ["Draft", "Submitted", "Under Review", "Approved", "Published", "Rejected", "Archived"],
        "transitions": [
            {"from": "Draft", "to": "Submitted", "who": "Member/Staff", "condition": "Content and media attached"},
            {"from": "Submitted", "to": "Under Review", "who": "System", "condition": "Auto-queued for admin review"},
            {"from": "Under Review", "to": "Approved", "who": "Admin", "condition": "Content policy compliance verified"},
            {"from": "Approved", "to": "Published", "who": "System/Admin", "condition": "Scheduled or immediate publication"},
            {"from": "Under Review", "to": "Rejected", "who": "Admin", "condition": "Policy violation, reason mandatory"},
            {"from": "Published", "to": "Archived", "who": "Admin/System", "condition": "Expiry date reached or manual archive"},
        ],
        "invalid_transitions": [
            {"from": "Draft", "to": "Published", "reason": "Cannot publish without review and approval"},
            {"from": "Rejected", "to": "Published", "reason": "Must re-submit and go through review again"},
        ],
        "lock_conditions": [
            "Published announcements cannot be edited — only archived",
            "Archived announcements read-only"
        ],
        "escalation": "Pending reviews > 24 hours flagged to admin",
        "audit_required": True,
        "risk_level": "medium"
    },
}

MNR_VALIDATION_CONTENT = {
    "mnr_member_list": {
        "risk_level": "critical",
        "ui_components": ["Member Table", "Search Filters", "Status Badges", "Tree Position", "Bulk Actions", "Export Button"],
        "field_rules": [
            {"field": "MNR ID", "type": "string", "required": True, "format": "MNR-XXXXX pattern", "editable_by": "System only", "validation": "Auto-generated, unique, immutable"},
            {"field": "Full Name", "type": "string", "required": True, "max_length": 128, "editable_by": "Admin/Member (limited)", "validation": "Must match KYC documents"},
            {"field": "Mobile Number", "type": "string", "required": True, "format": "10-digit Indian mobile", "editable_by": "Admin only", "validation": "Regex: ^[6-9]\\d{9}$, unique across system"},
            {"field": "Sponsor ID", "type": "reference", "required": True, "format": "Valid MNR ID", "editable_by": "System only", "validation": "Must reference active member, no circular sponsorship"},
            {"field": "Package Type", "type": "enum", "required": True, "format": "Platinum/Diamond/Star", "editable_by": "System (at activation)", "validation": "Set from PIN type, immutable after activation"},
            {"field": "Binary Position", "type": "enum", "required": True, "format": "Left/Right", "editable_by": "System (auto-placement)", "validation": "Auto-calculated, one position per parent node"},
        ],
        "button_validations": [
            {"button": "View Details", "api": "GET /api/v1/mnr/members/{id}", "requires": "Valid member ID", "role": "Admin", "double_click": "No side effects — safe"},
            {"button": "Deactivate", "api": "PUT /api/v1/mnr/members/{id}/deactivate", "requires": "Active status, no pending transactions", "role": "Admin only", "double_click": "Confirmation modal + reason required"},
            {"button": "Export", "api": "GET /api/v1/mnr/members/export", "requires": "Admin role", "role": "Admin", "double_click": "Debounced, rate limited"},
        ],
        "backend_checks": [
            "MNR ID format validated server-side before any query",
            "Sponsor chain validated for circular references on every modification",
            "Binary tree placement algorithm executes within database transaction",
            "Bulk operations validate each record individually, report per-record results",
            "Export function rate-limited to prevent data scraping",
            "Member data access enforced by role — members see only own data"
        ],
        "mobile_parity": [
            {"check": "View member list", "web": "Full table", "mobile": "Card layout", "status": "VERIFY"},
            {"check": "Search & filter", "web": "Yes", "mobile": "Yes", "status": "PASS"},
            {"check": "Deactivate member", "web": "Yes", "mobile": "No (admin-only)", "status": "WEB-ONLY"},
        ],
        "risks": [
            {"level": "critical", "description": "Circular sponsorship chain could break tree traversal and income calculation"},
            {"level": "critical", "description": "Duplicate binary placement could corrupt tree structure permanently"},
            {"level": "major", "description": "MNR ID manipulation via API could allow unauthorized data access"},
            {"level": "moderate", "description": "Bulk export without rate limiting enables data scraping"},
        ]
    },

    "mnr_kyc_approval": {
        "risk_level": "critical",
        "ui_components": ["Approval Queue", "Document Viewer", "Status Panel", "Approval Buttons", "Rejection Form", "History Log"],
        "field_rules": [
            {"field": "Document Type", "type": "enum", "required": True, "format": "Aadhaar/PAN/Passport/Voter ID", "editable_by": "Member (upload)", "validation": "Accepted types only, per KYC requirements"},
            {"field": "Document Number", "type": "string", "required": True, "format": "Type-specific pattern", "editable_by": "Member", "validation": "Aadhaar: 12 digits, PAN: ABCDE1234F pattern"},
            {"field": "Document File", "type": "file", "required": True, "format": "JPEG/PNG/PDF, max 5MB", "editable_by": "Member", "validation": "Server-side type check, path traversal blocked, virus scan"},
            {"field": "Bank Account Number", "type": "string", "required": True, "format": "9-18 digits", "editable_by": "Member", "validation": "Numeric only, length validation"},
            {"field": "IFSC Code", "type": "string", "required": True, "format": "ABCD0XXXXXX pattern", "editable_by": "Member", "validation": "11 chars, starts with 4 alpha + 0 + 6 alphanum"},
            {"field": "Account Holder Name", "type": "string", "required": True, "format": "Must match registered name", "editable_by": "Member", "validation": "Cross-referenced with KYC name"},
        ],
        "button_validations": [
            {"button": "Approve KYC", "api": "PUT /api/v1/mnr/kyc/{id}/approve", "requires": "Under Review status, staff/admin role", "role": "Staff (verify) / Admin (approve)", "double_click": "Disabled after first click, confirmation modal"},
            {"button": "Reject KYC", "api": "PUT /api/v1/mnr/kyc/{id}/reject", "requires": "Under Review status, rejection reason filled", "role": "Staff/Admin", "double_click": "Confirmation with reason validation"},
            {"button": "Approve Bank", "api": "PUT /api/v1/mnr/bank/{id}/approve", "requires": "KYC approved first, bank details verified", "role": "Admin only", "double_click": "Disabled after click"},
        ],
        "backend_checks": [
            "Two-stage approval: Staff verifies -> Admin approves — cannot skip",
            "Self-approval blocked — approver cannot be the member or previous verifier",
            "Document file validated for type, size, and malicious content",
            "Bank details locked after first successful withdrawal — change requires admin override",
            "KYC approval enables withdrawal capability — synchronized atomically",
            "All approval/rejection actions audit-logged with timestamp and user ID"
        ],
        "mobile_parity": [
            {"check": "Upload documents", "web": "Yes", "mobile": "Yes (camera + gallery)", "status": "PASS"},
            {"check": "View approval status", "web": "Yes", "mobile": "Yes", "status": "PASS"},
            {"check": "Approve/Reject", "web": "Yes", "mobile": "Limited (admin-only)", "status": "VERIFY"},
        ],
        "risks": [
            {"level": "critical", "description": "Skipping staff verification stage could approve fraudulent documents"},
            {"level": "critical", "description": "Bank detail change after withdrawal could enable fraud"},
            {"level": "major", "description": "Document file without virus scan could introduce malware"},
            {"level": "major", "description": "Self-approval bypass via direct API call must be strictly blocked"},
        ]
    },

    "mnr_income_dashboard": {
        "risk_level": "critical",
        "ui_components": ["Income Summary Cards", "Stream Breakdown", "Daily Chart", "Period Selector", "Detail Table", "Export"],
        "field_rules": [
            {"field": "Direct Referral Income", "type": "decimal(18,2)", "required": True, "format": "Auto-calculated", "editable_by": "System only", "validation": "Based on direct referral count and package rates"},
            {"field": "Matching Referral Income", "type": "decimal(18,2)", "required": True, "format": "Auto-calculated", "editable_by": "System only", "validation": "Based on binary tree matching pairs"},
            {"field": "Ved Income", "type": "decimal(18,2)", "required": True, "format": "Auto-calculated", "editable_by": "System only", "validation": "Based on specific qualification criteria"},
            {"field": "Guru Dakshina", "type": "decimal(18,2)", "required": True, "format": "2% of qualified income", "editable_by": "System only", "validation": "Exactly 2%, calculated after other incomes"},
            {"field": "Total Income", "type": "decimal(18,2)", "required": True, "format": "Sum of 4 streams", "editable_by": "System only", "validation": "Must equal sum of individual streams exactly"},
        ],
        "button_validations": [
            {"button": "View Breakdown", "api": "GET /api/v1/mnr/income/breakdown", "requires": "Valid date range", "role": "Admin/Member (own data)", "double_click": "Safe — read-only"},
            {"button": "Export Report", "api": "GET /api/v1/mnr/income/export", "requires": "Date range selected", "role": "Admin", "double_click": "Rate limited"},
            {"button": "Dispute Income", "api": "POST /api/v1/mnr/income/{id}/dispute", "requires": "Income record exists, reason provided", "role": "Admin", "double_click": "Confirmation required"},
        ],
        "backend_checks": [
            "All 4 income streams calculated by APScheduler — no manual calculation API",
            "Income amounts use DECIMAL(18,2) — never float arithmetic",
            "Daily auto-approval runs at configured time with advisory lock",
            "Total income cross-validated: must equal sum of 4 streams exactly",
            "Wallet credit amount matches income record — reconciliation enforced",
            "Income calculation uses binary tree snapshot at trigger time — immutable",
            "Historical income records are read-only — no modification API exists"
        ],
        "mobile_parity": [
            {"check": "View income summary", "web": "Yes", "mobile": "Yes", "status": "PASS"},
            {"check": "View breakdown", "web": "Full table", "mobile": "Card view", "status": "VERIFY"},
            {"check": "Export", "web": "Yes", "mobile": "No", "status": "WEB-ONLY"},
        ],
        "risks": [
            {"level": "critical", "description": "Float arithmetic in income calculation could cause rounding errors at scale"},
            {"level": "critical", "description": "Race condition in daily auto-approval could duplicate income credits"},
            {"level": "critical", "description": "Matching referral miscalculation due to stale tree cache"},
            {"level": "major", "description": "Guru Dakshina 2% applied on wrong base amount"},
            {"level": "major", "description": "Income-wallet desync: income approved but wallet not credited"},
        ]
    },

    "mnr_wallet_management": {
        "risk_level": "critical",
        "ui_components": ["Earning Wallet Card", "Withdrawable Wallet Card", "Upgrade Wallet Card", "Transaction History", "Balance Chart"],
        "field_rules": [
            {"field": "Earning Wallet Balance", "type": "decimal(18,2)", "required": True, "format": "Calculated", "editable_by": "System only", "validation": "SUM(credits) - SUM(debits), cannot be negative"},
            {"field": "Withdrawable Wallet Balance", "type": "decimal(18,2)", "required": True, "format": "Calculated", "editable_by": "System only", "validation": "Package-specific split ratio applied"},
            {"field": "Upgrade Wallet Balance", "type": "decimal(18,2)", "required": True, "format": "Calculated", "editable_by": "System only", "validation": "Reserved for package upgrade only"},
            {"field": "Transaction Amount", "type": "decimal(18,2)", "required": True, "format": "Positive number", "editable_by": "System only", "validation": "Must be > 0, precision enforced"},
        ],
        "button_validations": [
            {"button": "View Transactions", "api": "GET /api/v1/mnr/wallet/transactions", "requires": "Valid member ID", "role": "Admin/Member (own)", "double_click": "Safe — read-only"},
        ],
        "backend_checks": [
            "Wallet balance calculated from transaction ledger — not stored as single field",
            "Package-specific split ratios enforced at credit time, not withdrawal",
            "Row-level locking (SELECT ... FOR UPDATE) on all wallet modifications",
            "Negative balance blocked at transaction level — CHECK constraint",
            "Wallet reconciliation runs daily: balance = SUM(credits) - SUM(debits)",
            "Concurrent wallet operations serialized via database advisory locks",
            "Wallet modification audit trail includes before/after balances"
        ],
        "mobile_parity": [
            {"check": "View balances", "web": "Yes", "mobile": "Yes", "status": "PASS"},
            {"check": "Transaction history", "web": "Full table", "mobile": "Scrollable list", "status": "PASS"},
        ],
        "risks": [
            {"level": "critical", "description": "Race condition on concurrent wallet credits could create phantom balance"},
            {"level": "critical", "description": "Negative balance allowed due to missing CHECK constraint"},
            {"level": "critical", "description": "Split ratio misconfiguration could divert funds to wrong wallet"},
            {"level": "major", "description": "Wallet reconciliation failure not alerting administrators"},
        ]
    },

    "mnr_withdrawal_processing": {
        "risk_level": "critical",
        "ui_components": ["Withdrawal Queue", "Auto-Generation Log", "Deduction Breakdown", "Approval Panel", "Payment Status", "Rejection Form"],
        "field_rules": [
            {"field": "Withdrawal Amount", "type": "decimal(18,2)", "required": True, "format": "Auto-calculated", "editable_by": "System only", "validation": "Withdrawable balance - Rs 1,000 buffer"},
            {"field": "Admin Charge (8%)", "type": "decimal(18,2)", "required": True, "format": "8% of withdrawal", "editable_by": "System only", "validation": "Exactly 8%, calculated server-side"},
            {"field": "TDS (2%)", "type": "decimal(18,2)", "required": True, "format": "2% of withdrawal", "editable_by": "System only", "validation": "Exactly 2%, calculated server-side"},
            {"field": "Net Payout", "type": "decimal(18,2)", "required": True, "format": "Amount - Admin - TDS", "editable_by": "System only", "validation": "Must equal Withdrawal - 8% - 2% exactly"},
            {"field": "Bank Account", "type": "reference", "required": True, "format": "Approved bank details", "editable_by": "System", "validation": "Must be admin-approved bank account"},
        ],
        "button_validations": [
            {"button": "Approve Withdrawal", "api": "PUT /api/v1/mnr/withdrawals/{id}/approve", "requires": "KYC approved, bank verified, pending status", "role": "Admin", "double_click": "Single-click lock with confirmation"},
            {"button": "Reject Withdrawal", "api": "PUT /api/v1/mnr/withdrawals/{id}/reject", "requires": "Pending status, reason filled", "role": "Admin", "double_click": "Confirmation with reason validation"},
            {"button": "Process Batch", "api": "POST /api/v1/mnr/withdrawals/batch-process", "requires": "All approved, payment file ready", "role": "Finance Admin", "double_click": "Advisory lock prevents duplicate batch"},
        ],
        "backend_checks": [
            "Auto-generation runs Mon-Sat 7AM via APScheduler with advisory lock",
            "Rs 2,000 minimum balance check enforced in withdrawal query",
            "Rs 1,000 buffer retained in wallet — not available for withdrawal",
            "8% Admin Charge + 2% TDS calculated server-side, not front-end",
            "Net payout cross-validated: Amount - 8% - 2% = Net (exact match)",
            "KYC approval status checked at approval time, not just generation time",
            "Rejected withdrawal amount returned to wallet in same transaction",
            "Duplicate withdrawal detection: one active withdrawal per member at a time",
            "Sunday auto-generation disabled by day-of-week check"
        ],
        "mobile_parity": [
            {"check": "View withdrawal status", "web": "Yes", "mobile": "Yes", "status": "PASS"},
            {"check": "View deduction breakdown", "web": "Yes", "mobile": "Yes", "status": "PASS"},
            {"check": "Approve/Reject", "web": "Yes", "mobile": "No (admin-only)", "status": "WEB-ONLY"},
        ],
        "risks": [
            {"level": "critical", "description": "Duplicate auto-generation could create multiple withdrawals for same balance"},
            {"level": "critical", "description": "Deduction calculation error: 8%+2% applied on wrong base could cause financial loss"},
            {"level": "critical", "description": "Buffer amount not enforced could drain wallet below Rs 1,000"},
            {"level": "critical", "description": "Rejected withdrawal amount not returned to wallet = permanent fund loss"},
            {"level": "major", "description": "KYC revoked between generation and approval — withdrawal paid to unverified account"},
            {"level": "major", "description": "Batch processing without advisory lock could double-process payments"},
        ]
    },

    "mnr_pin_management": {
        "risk_level": "critical",
        "ui_components": ["PIN Generation Panel", "Payment Verification Queue", "Assignment Interface", "PIN History", "Expiry Tracker"],
        "field_rules": [
            {"field": "PIN Code", "type": "string", "required": True, "format": "System-generated unique code", "editable_by": "System only", "validation": "Unique constraint at DB level, auto-generated"},
            {"field": "Package Type", "type": "enum", "required": True, "format": "Platinum/Diamond/Star", "editable_by": "Purchaser (at order)", "validation": "Determines point value: 1.0/0.5/0.0"},
            {"field": "Point Value", "type": "decimal(2,1)", "required": True, "format": "Set from package", "editable_by": "System only", "validation": "Immutable after generation"},
            {"field": "Purchaser MNR ID", "type": "reference", "required": True, "format": "Valid MNR ID", "editable_by": "System", "validation": "Must be active member"},
            {"field": "Assigned To MNR ID", "type": "reference", "required": False, "format": "Valid MNR ID", "editable_by": "Purchaser/Admin", "validation": "Cannot assign to already-active member"},
        ],
        "button_validations": [
            {"button": "Generate PIN", "api": "POST /api/v1/mnr/pins/generate", "requires": "Payment verified", "role": "System/Admin", "double_click": "Idempotency key prevents duplicate generation"},
            {"button": "Verify Payment", "api": "PUT /api/v1/mnr/pins/payment/{id}/verify", "requires": "Payment receipt uploaded", "role": "Admin", "double_click": "Single-click lock"},
            {"button": "Assign PIN", "api": "PUT /api/v1/mnr/pins/{id}/assign", "requires": "Generated status, target member valid", "role": "Purchaser/Admin", "double_click": "Confirmation with target member details"},
        ],
        "backend_checks": [
            "PIN uniqueness enforced via UNIQUE constraint at database level",
            "Point values (Platinum=1.0, Diamond=0.5, Star=0.0) set from package config, not user input",
            "Used PINs permanently locked — no reassignment or modification",
            "Payment verification triggers PIN generation in same transaction",
            "Assignment validates target member is not already active",
            "PIN expiry handled by scheduled job, not on-demand check",
            "Idempotency keys prevent duplicate PIN generation on retry"
        ],
        "mobile_parity": [
            {"check": "Purchase PIN", "web": "Yes", "mobile": "Yes", "status": "PASS"},
            {"check": "View PIN status", "web": "Yes", "mobile": "Yes", "status": "PASS"},
            {"check": "Assign PIN", "web": "Yes", "mobile": "Yes", "status": "PASS"},
        ],
        "risks": [
            {"level": "critical", "description": "Duplicate PIN generation could allow double activation"},
            {"level": "critical", "description": "Point value manipulation via API could alter income calculations system-wide"},
            {"level": "major", "description": "PIN assignment to already-active member could corrupt binary tree"},
            {"level": "major", "description": "Payment verification without receipt could enable fraudulent PINs"},
        ]
    },

    "mnr_award_management": {
        "risk_level": "high",
        "ui_components": ["Award Dashboard", "Qualification Checker", "Nomination Queue", "Approval Panel", "Redemption Tracker"],
        "field_rules": [
            {"field": "Award Type", "type": "enum", "required": True, "format": "Configured award types", "editable_by": "System", "validation": "Must match active award configuration"},
            {"field": "Qualification Criteria", "type": "json", "required": True, "format": "Criteria snapshot", "editable_by": "System only", "validation": "Snapshot taken at nomination time, immutable"},
            {"field": "Member MNR ID", "type": "reference", "required": True, "format": "Valid MNR ID", "editable_by": "System", "validation": "Must be active member meeting criteria"},
        ],
        "button_validations": [
            {"button": "Approve Award", "api": "PUT /api/v1/mnr/awards/{id}/approve", "requires": "Under Review status, criteria re-verified", "role": "Admin", "double_click": "Confirmation modal"},
            {"button": "Redeem Benefit", "api": "POST /api/v1/mnr/awards/{id}/redeem", "requires": "Awarded status, benefit not yet claimed", "role": "Member", "double_click": "Single-redemption lock per benefit"},
        ],
        "backend_checks": [
            "Qualification re-verified at approval time, not just nomination",
            "6-stage lifecycle enforced — no stage skipping via API",
            "EV coupon benefits tracked individually — partial redemption supported",
            "Award revocation requires separate admin flow with audit",
            "Duplicate award for same criteria and period blocked"
        ],
        "mobile_parity": [
            {"check": "View awards", "web": "Yes", "mobile": "Yes", "status": "PASS"},
            {"check": "Redeem benefits", "web": "Yes", "mobile": "Yes", "status": "PASS"},
            {"check": "Approve awards", "web": "Yes", "mobile": "No (admin-only)", "status": "WEB-ONLY"},
        ],
        "risks": [
            {"level": "major", "description": "Qualification criteria change after nomination could invalidate approved awards"},
            {"level": "major", "description": "Double redemption of same benefit due to race condition"},
            {"level": "moderate", "description": "Award notification failure leaving member unaware of earned award"},
        ]
    },

    "mnr_system_config": {
        "risk_level": "critical",
        "ui_components": ["Package Configuration", "Rate Tables", "Income Parameters", "Withdrawal Settings", "System Toggles"],
        "field_rules": [
            {"field": "Package Rate", "type": "decimal(18,2)", "required": True, "format": "Positive number", "editable_by": "Supreme Admin only", "validation": "Cannot be zero or negative"},
            {"field": "Admin Charge %", "type": "decimal(5,2)", "required": True, "format": "0-100", "editable_by": "Supreme Admin only", "validation": "Currently fixed at 8%"},
            {"field": "TDS %", "type": "decimal(5,2)", "required": True, "format": "0-100", "editable_by": "Supreme Admin only", "validation": "Currently fixed at 2%, statutory compliance"},
            {"field": "Withdrawal Buffer", "type": "decimal(18,2)", "required": True, "format": "Positive number", "editable_by": "Supreme Admin only", "validation": "Currently Rs 1,000"},
            {"field": "Min Withdrawal Balance", "type": "decimal(18,2)", "required": True, "format": "Positive number", "editable_by": "Supreme Admin only", "validation": "Currently Rs 2,000"},
        ],
        "button_validations": [
            {"button": "Save Configuration", "api": "PUT /api/v1/mnr/config/update", "requires": "Supreme Admin role, all fields valid", "role": "Supreme Admin only", "double_click": "Confirmation with change summary"},
        ],
        "backend_checks": [
            "Configuration changes take effect on next calculation cycle, not retroactively",
            "Previous configuration version retained for audit — never overwritten",
            "Configuration change audit log includes before/after values",
            "Rate changes validated for reasonableness (alerts on >50% change)",
            "Only Supreme Admin role can modify financial parameters",
            "Configuration used by scheduler pulled at execution time, not cached"
        ],
        "mobile_parity": [
            {"check": "View configuration", "web": "Yes", "mobile": "No (admin-only)", "status": "WEB-ONLY"},
            {"check": "Modify configuration", "web": "Yes", "mobile": "No (admin-only)", "status": "WEB-ONLY"},
        ],
        "risks": [
            {"level": "critical", "description": "Configuration change applied retroactively could recalculate all historical income"},
            {"level": "critical", "description": "Unauthorized config modification could alter deduction rates affecting all members"},
            {"level": "major", "description": "Config cache not invalidated after change could use stale rates"},
            {"level": "major", "description": "No confirmation/preview before config save could cause accidental changes"},
        ]
    },
}
