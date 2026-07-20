"""
DC Protocol: MNR System Guide Content
Dynamic training documentation for all MNR pages.
Maps menu_code -> detailed guide content for MNR admin, RVZ, and member pages.
"""

MNR_SECTION_DESCRIPTIONS = {
    "mnr-users": {
        "description": "Manage all MNR members - view profiles, KYC status, activation details, binary tree positions, and member lifecycle tracking.",
        "icon": "fas fa-users"
    },
    "mnr-pins": {
        "description": "PIN and coupon management - generate PINs, approve purchases, track coupon status, and manage activation codes.",
        "icon": "fas fa-key"
    },
    "mnr-approvals": {
        "description": "Bank and KYC approval workflows - validate member documents, approve bank details, and manage verification queues.",
        "icon": "fas fa-check-double"
    },
    "mnr-income": {
        "description": "Income monitoring and management - track all four income streams, manage pending calculations, and supreme oversight.",
        "icon": "fas fa-chart-line"
    },
    "mnr-finance": {
        "description": "Financial oversight - company-level financial statements, supreme finance dashboard, and cross-module financial summaries.",
        "icon": "fas fa-university"
    },
    "mnr-withdrawals": {
        "description": "Withdrawal processing pipeline - approve member payout requests, track withdrawal history, and supreme withdrawal oversight.",
        "icon": "fas fa-money-check-alt"
    },
    "mnr-awards": {
        "description": "Award and bonanza management - process milestone awards, manage bonanza claims, and track achievement lifecycle.",
        "icon": "fas fa-trophy"
    },
    "mnr-communications": {
        "description": "Member communications - announcement management, banner analytics, feedback review, and broadcast tools.",
        "icon": "fas fa-bullhorn"
    },
    "mnr-config": {
        "description": "System configuration - rate settings, daily ceilings, package management, role assignments, scheduler controls, and menu access.",
        "icon": "fas fa-cogs"
    },
    "mnr-data": {
        "description": "Data management and recovery - delete management, data recovery tools, production reset status, and audit operations.",
        "icon": "fas fa-database"
    },
    "mnr-security": {
        "description": "Security management - password changes, secondary password setup, user credential management, and access security.",
        "icon": "fas fa-shield-alt"
    },
    "mnr-admin": {
        "description": "RVZ Admin panel - supreme administrative control over all MNR operations including users, income, withdrawals, and awards.",
        "icon": "fas fa-crown"
    },
    "mnr-user": {
        "description": "MNR Member portal pages - the member-facing experience including dashboard, earnings, connections, withdrawals, and benefits.",
        "icon": "fas fa-user"
    },
    "staff_mnr_user_dashboard": {
        "description": "Staff mirror of the MNR member dashboard - view member data as they see it with staff audit logging.",
        "icon": "fas fa-desktop"
    },
    "staff_mnr_user_members": {
        "description": "Staff view of member connections - binary tree visualization, team gallery, and downline management on behalf of members.",
        "icon": "fas fa-sitemap"
    },
    "staff_mnr_user_mnr": {
        "description": "Staff access to member financial data - earnings overview, wallet balances, withdrawal status, and income breakdowns.",
        "icon": "fas fa-wallet"
    },
    "staff_mnr_user_myntreal": {
        "description": "Staff access to member MyntReal services - property listings, insurance, and franchise data viewed on member's behalf.",
        "icon": "fas fa-building"
    },
    "staff_mnr_user_awards": {
        "description": "Staff view of member awards and bonanza claims - track achievement progress and claim status.",
        "icon": "fas fa-medal"
    },
    "staff_mnr_user_announcements": {
        "description": "Staff view of member announcements - review submissions, check approval status, and moderate content.",
        "icon": "fas fa-newspaper"
    },
    "staff_mnr_user_coupons": {
        "description": "Staff view of member coupon and points data - MNR points balance, utilization history, and coupon benefits.",
        "icon": "fas fa-ticket-alt"
    },
    "staff_mnr_user_system": {
        "description": "Staff access to member system settings - password management, feedback, and account configuration.",
        "icon": "fas fa-cog"
    },
    "staff_mnr_user_zynova": {
        "description": "Staff view of member VGK4U services - real estate (Real Dreams), insurance (VGK Care), and training (ETC) access.",
        "icon": "fas fa-layer-group"
    },
}

MNR_SECTION_ORDER = [
    "mnr-users", "mnr-approvals", "mnr-pins", "mnr-income", "mnr-finance",
    "mnr-withdrawals", "mnr-awards", "mnr-communications", "mnr-config",
    "mnr-data", "mnr-security",
    "mnr-admin", "mnr-user",
    "staff_mnr_user_dashboard", "staff_mnr_user_members",
    "staff_mnr_user_mnr", "staff_mnr_user_myntreal",
    "staff_mnr_user_awards", "staff_mnr_user_announcements",
    "staff_mnr_user_coupons", "staff_mnr_user_system", "staff_mnr_user_zynova"
]

MNR_GUIDE_CONTENT = {

    "staff_new_mnr_users": {
        "purpose": "Central hub for viewing and managing all registered MNR members. Shows every member's profile, activation status, KYC completion, package type, and position in the binary tree.",
        "who_can_access": "Staff with MNR Users menu access (Admin, Manager, HR roles)",
        "main_sections": [
            {"name": "Member List", "description": "Searchable, filterable table of all MNR members with MNR ID, name, phone, sponsor, package, activation status, and join date."},
            {"name": "Filter Panel", "description": "Filter by package type (Platinum/Diamond/Star), activation status (Active/Inactive), KYC status, date range, and sponsor."},
            {"name": "Member Details", "description": "Click any member to view full profile - personal info, tree position, income summary, wallet balances, and documents."}
        ],
        "usage_flow": [
            "Open the All Users page from MNR sidebar",
            "Use filters to narrow down members (by package, status, date, etc.)",
            "Click a member row to view their full profile",
            "Review KYC documents, bank details, and activation status",
            "Use action buttons for specific operations (view tree, check income, etc.)"
        ],
        "fields": [
            {"name": "MNR ID", "description": "Unique 12-character identifier (format: MNR1823XXXXX) assigned at registration"},
            {"name": "Package", "description": "Member's subscription level - Platinum (1.0 points), Diamond (0.5 points), or Star/Loyal (0.0 points)"},
            {"name": "Sponsor ID", "description": "MNR ID of the person who referred this member"},
            {"name": "Activation Status", "description": "Whether the member has used a PIN to activate their account"},
            {"name": "KYC Status", "description": "Document verification progress - Pending, Validated, or Approved"},
            {"name": "Join Date", "description": "Date when the member registered in the system"}
        ],
        "statuses": [
            {"status": "Active", "color": "#059669", "meaning": "Member has activated their account using a PIN and is earning income"},
            {"status": "Inactive", "color": "#6b7280", "meaning": "Registered but not yet activated - no PIN used"},
            {"status": "Suspended", "color": "#dc2626", "meaning": "Account temporarily disabled by admin"}
        ],
        "tips": [
            "Use the search bar for quick lookup by MNR ID, name, or phone number",
            "Filter by 'Inactive' status to identify members who need activation follow-up",
            "Check KYC + Bank status together - both must be approved for withdrawals to process",
            "Sort by join date to see newest members and track recent growth"
        ],
        "common_mistakes": [
            "Confusing Sponsor ID (who referred them) with Placement Parent (binary tree position) - they can be different",
            "Not checking both KYC and Bank approval before expecting withdrawals to work",
            "Searching by partial MNR ID without the full format"
        ]
    },

    "staff_mnr_birthdays": {
        "purpose": "View upcoming and past birthday details of MNR members for engagement and relationship building. Helps staff send birthday wishes and plan member engagement activities.",
        "who_can_access": "Staff with MNR Users menu access",
        "main_sections": [
            {"name": "Birthday Calendar", "description": "List of members with birthdays today, this week, and this month"},
            {"name": "Member Details", "description": "Quick view of member name, MNR ID, package, and contact information"}
        ],
        "usage_flow": [
            "Open Birthday Details from MNR sidebar",
            "View today's birthdays at the top",
            "Check upcoming birthdays for the week/month",
            "Click on a member to view their full profile if needed"
        ],
        "fields": [
            {"name": "Member Name", "description": "Full name of the MNR member"},
            {"name": "Date of Birth", "description": "Member's registered birthday"},
            {"name": "Package", "description": "Current subscription level"},
            {"name": "Sponsor", "description": "Name of the referring member"}
        ],
        "statuses": [],
        "tips": [
            "Check this page daily for personalized member engagement",
            "Use birthday data for team-building and recognition programs"
        ],
        "common_mistakes": [
            "Not verifying DOB accuracy - some members may have entered incorrect dates during registration"
        ]
    },

    "staff_mnr_field_allowances": {
        "purpose": "Manage field allowances for MNR members - Group A and Group B classifications for travel, accommodation, and operational allowances during field activities.",
        "who_can_access": "Staff with MNR Users or Finance menu access",
        "main_sections": [
            {"name": "Allowance Requests", "description": "List of pending and processed field allowance requests from members"},
            {"name": "Group Classification", "description": "Group A (metro/tier-1 cities) and Group B (other locations) rate management"},
            {"name": "Progress Tracking", "description": "Real-time mobile progress showing field activity and allowance utilization"}
        ],
        "usage_flow": [
            "Review incoming field allowance requests",
            "Verify the group classification (A or B) based on location",
            "Check the allowance rates applicable for the group",
            "Approve or return the request with comments",
            "Track disbursement status"
        ],
        "fields": [
            {"name": "Group A", "description": "Metro and Tier-1 city rates - higher allowance amounts"},
            {"name": "Group B", "description": "Other location rates - standard allowance amounts"},
            {"name": "Activity Type", "description": "Type of field work (meeting, training, event, etc.)"},
            {"name": "Amount", "description": "Calculated allowance based on group and activity duration"}
        ],
        "statuses": [
            {"status": "Pending", "color": "#f59e0b", "meaning": "Request submitted, awaiting review"},
            {"status": "Approved", "color": "#059669", "meaning": "Allowance approved for disbursement"},
            {"status": "Rejected", "color": "#dc2626", "meaning": "Request rejected with reason"}
        ],
        "tips": [
            "Always verify the city/location before approving Group A rates",
            "Check for duplicate requests for the same date/activity"
        ],
        "common_mistakes": [
            "Approving Group A rates for non-metro locations",
            "Not checking if the member actually performed the field activity before approving"
        ]
    },

    "staff_mnr_pin_approvals": {
        "purpose": "Review and approve PIN purchase requests from members. Members upload payment proof when buying PINs, and staff must verify the payment before generating activation PINs.",
        "who_can_access": "Staff with PIN Approvals menu access (Finance, Admin roles)",
        "main_sections": [
            {"name": "Pending Approvals", "description": "Queue of PIN purchase requests with payment proof uploads awaiting verification"},
            {"name": "Approved PINs", "description": "History of approved PIN requests with generated codes"},
            {"name": "Rejected Requests", "description": "Declined requests with rejection reasons"}
        ],
        "usage_flow": [
            "Open PIN Approvals page",
            "Review the pending purchase requests queue",
            "Click on a request to view payment proof (screenshot/receipt)",
            "Verify the payment amount matches the package price",
            "Cross-check the payment reference/UTR number if applicable",
            "Approve to generate PINs or Reject with a clear reason",
            "On approval, system auto-generates the PIN code (e.g., 15-digit code starting with 615 for Platinum)"
        ],
        "fields": [
            {"name": "Request ID", "description": "Unique identifier for the PIN purchase request"},
            {"name": "Member MNR ID", "description": "The member who is purchasing the PIN"},
            {"name": "Package Type", "description": "Platinum, Diamond, or Star - determines PIN value and price"},
            {"name": "Payment Proof", "description": "Uploaded screenshot or receipt of payment"},
            {"name": "Amount", "description": "Payment amount that should match the package price"},
            {"name": "UTR/Reference", "description": "Bank transaction reference number for verification"}
        ],
        "statuses": [
            {"status": "Pending", "color": "#f59e0b", "meaning": "Payment proof uploaded, awaiting staff verification"},
            {"status": "Approved", "color": "#059669", "meaning": "Payment verified, PIN generated and ready for use"},
            {"status": "Rejected", "color": "#dc2626", "meaning": "Payment proof invalid or insufficient, request declined"}
        ],
        "tips": [
            "Always verify the UTR/reference number against bank records when possible",
            "Check for duplicate payment proofs - same screenshot used for multiple requests",
            "Platinum PINs generate codes starting with 615, Diamond with different prefix",
            "Approving a PIN does NOT activate the member - they must separately use the PIN"
        ],
        "common_mistakes": [
            "Approving without verifying the payment amount matches the package price",
            "Not checking if the same payment proof was already used for another request",
            "Confusing PIN approval (generating a code) with member activation (using the code)"
        ]
    },

    "staff_mnr_coupon_status": {
        "purpose": "Track the status of all MNR coupons across the system - see which PINs are generated, used, expired, or pending. Provides a complete lifecycle view of every coupon.",
        "who_can_access": "Staff with PIN/Coupon menu access",
        "main_sections": [
            {"name": "Coupon Dashboard", "description": "Overview cards showing total coupons, used, unused, and expired counts"},
            {"name": "Coupon List", "description": "Detailed table of all coupons with status, owner, usage date, and package type"},
            {"name": "Search & Filter", "description": "Find specific coupons by code, owner MNR ID, package type, or status"}
        ],
        "usage_flow": [
            "Open Coupon Status from sidebar",
            "Review the dashboard summary cards for overall picture",
            "Use filters to find specific coupons (by status, package, or date)",
            "Click a coupon to see full details including who purchased and who used it",
            "Track coupon lifecycle from generation to usage"
        ],
        "fields": [
            {"name": "Coupon Code", "description": "15-digit unique PIN code generated by the system"},
            {"name": "Package Type", "description": "Platinum, Diamond, or Star - determines the coupon's activation value"},
            {"name": "Purchaser", "description": "MNR ID of the member who bought this coupon"},
            {"name": "Used By", "description": "MNR ID of the member who used this coupon for activation (may differ from purchaser)"},
            {"name": "Generated Date", "description": "When the PIN was created after payment approval"},
            {"name": "Used Date", "description": "When the PIN was consumed for member activation"}
        ],
        "statuses": [
            {"status": "Generated", "color": "#3b82f6", "meaning": "PIN created and ready for use"},
            {"status": "Used", "color": "#059669", "meaning": "PIN has been consumed to activate a member"},
            {"status": "Expired", "color": "#6b7280", "meaning": "PIN validity period has passed without being used"},
            {"status": "Cancelled", "color": "#dc2626", "meaning": "PIN was cancelled by admin"}
        ],
        "tips": [
            "A member can buy PINs and give them to others for activation",
            "Track unused PINs approaching expiry to notify members",
            "Use this page to troubleshoot activation issues - verify if the PIN was already used"
        ],
        "common_mistakes": [
            "Not realizing the purchaser and user of a PIN can be different people",
            "Trying to reactivate an already-used PIN"
        ]
    },

    "staff_mnr_pins": {
        "purpose": "Master view of all PINs in the system. Manage PIN inventory, view generation history, and handle PIN-related operations.",
        "who_can_access": "Staff with PINs menu access (Admin, Finance)",
        "main_sections": [
            {"name": "PIN Inventory", "description": "Complete list of all PINs with their current status and ownership"},
            {"name": "Generation History", "description": "Timeline of when PINs were generated and by whom"},
            {"name": "Bulk Operations", "description": "Tools for bulk PIN generation or status updates"}
        ],
        "usage_flow": [
            "Navigate to PINs page from MNR sidebar",
            "Review current PIN inventory by package type",
            "Search for specific PINs by code or owner",
            "Monitor PIN distribution across members",
            "Track PIN utilization rates"
        ],
        "fields": [
            {"name": "PIN Code", "description": "Unique activation code (15-digit format)"},
            {"name": "Package", "description": "Associated package type (Platinum/Diamond/Star)"},
            {"name": "Status", "description": "Current state of the PIN (Generated/Used/Expired)"},
            {"name": "Owner", "description": "Member who purchased or was assigned this PIN"},
            {"name": "Points Value", "description": "Platinum = 1.0, Diamond = 0.5, Star = 0.0 points"}
        ],
        "statuses": [
            {"status": "Available", "color": "#3b82f6", "meaning": "PIN is generated and ready to use"},
            {"status": "Assigned", "color": "#8b5cf6", "meaning": "PIN assigned to a member but not yet used"},
            {"status": "Used", "color": "#059669", "meaning": "PIN consumed for activation"},
            {"status": "Expired", "color": "#6b7280", "meaning": "PIN validity has lapsed"}
        ],
        "tips": [
            "Monitor PIN utilization rates to understand activation bottlenecks",
            "Platinum PINs (1.0 point) are the highest value and most impactful for tree growth",
            "Each package type has different income implications for the referral chain"
        ],
        "common_mistakes": [
            "Not tracking expired PINs and failing to notify members before expiry",
            "Confusing PIN generation (admin action) with PIN usage (member action)"
        ]
    },

    "staff_mnr_bank_pending": {
        "purpose": "Process pending bank detail verifications. Members submit their bank account information for withdrawal eligibility, and staff must validate and approve the details through a 2-step process.",
        "who_can_access": "Staff with Bank Approvals access (Finance Admin, Accounts team)",
        "main_sections": [
            {"name": "Pending Queue", "description": "Bank details submitted by members awaiting first validation"},
            {"name": "Validation Queue", "description": "Details that passed first check, awaiting final approval"},
            {"name": "Document Viewer", "description": "View uploaded bank proof documents (cancelled cheque, passbook, etc.)"}
        ],
        "usage_flow": [
            "Open Bank Pending page",
            "Review the pending bank submissions queue",
            "Click on a submission to view bank details and documents",
            "Step 1 - VALIDATE: Verify account number, IFSC code, and holder name match the uploaded proof",
            "Step 2 - APPROVE: Final approval by senior staff/finance admin",
            "On approval, member's wallet automatically syncs - funds move from Earning to Withdrawable wallet"
        ],
        "fields": [
            {"name": "Account Number", "description": "Bank account number submitted by the member"},
            {"name": "IFSC Code", "description": "Bank branch IFSC code for NEFT/RTGS transfers"},
            {"name": "Account Holder Name", "description": "Name on the bank account - must match member's registered name"},
            {"name": "Bank Name", "description": "Name of the bank institution"},
            {"name": "Proof Document", "description": "Uploaded cancelled cheque, passbook photo, or bank statement"}
        ],
        "statuses": [
            {"status": "Pending", "color": "#f59e0b", "meaning": "Bank details submitted, awaiting first validation"},
            {"status": "Validated by Admin", "color": "#3b82f6", "meaning": "First check passed, awaiting final approval"},
            {"status": "Approved", "color": "#059669", "meaning": "Bank details verified and approved - withdrawals enabled"},
            {"status": "Rejected", "color": "#dc2626", "meaning": "Bank details incorrect or documents invalid"}
        ],
        "tips": [
            "CRITICAL: Both KYC AND Bank must be approved for withdrawals to work",
            "Verify the account holder name exactly matches the member's registered name",
            "Cross-check IFSC code format (11 characters, 4th character always '0')",
            "Approval triggers automatic wallet sync - Earning wallet funds move to Withdrawable"
        ],
        "common_mistakes": [
            "Approving bank details where holder name doesn't match the member name",
            "Not verifying IFSC code format before approval",
            "Approving bank without checking if KYC is also approved - both are required"
        ]
    },

    "staff_mnr_bank_all": {
        "purpose": "View all bank detail submissions across all statuses - pending, validated, approved, and rejected. Provides a complete audit view of all bank verifications in the system.",
        "who_can_access": "Staff with Bank Details view access",
        "main_sections": [
            {"name": "All Bank Records", "description": "Complete list of all bank submissions with current status"},
            {"name": "Status Filters", "description": "Filter by Pending, Validated, Approved, or Rejected"},
            {"name": "History", "description": "View approval/rejection history with timestamps and staff names"}
        ],
        "usage_flow": [
            "Open All Bank Details page",
            "Use status filters to find specific types of records",
            "Search by member MNR ID or name",
            "Review individual records with full audit trail",
            "Export data for reconciliation if needed"
        ],
        "fields": [
            {"name": "Member MNR ID", "description": "Member who submitted the bank details"},
            {"name": "Bank Details", "description": "Account number, IFSC, holder name, and bank name"},
            {"name": "Status", "description": "Current verification status"},
            {"name": "Validated By", "description": "Staff member who performed first validation"},
            {"name": "Approved By", "description": "Staff member who gave final approval"},
            {"name": "Action Date", "description": "Date of the most recent status change"}
        ],
        "statuses": [
            {"status": "Pending", "color": "#f59e0b", "meaning": "Awaiting first validation"},
            {"status": "Validated", "color": "#3b82f6", "meaning": "First check passed"},
            {"status": "Approved", "color": "#059669", "meaning": "Fully verified"},
            {"status": "Rejected", "color": "#dc2626", "meaning": "Declined with reason"}
        ],
        "tips": [
            "Use this page for audit purposes and reconciliation",
            "Filter by 'Rejected' to follow up with members who need to resubmit"
        ],
        "common_mistakes": [
            "Using this page to approve - approvals should be done from Bank Pending page",
            "Not filtering results and trying to review the entire list at once"
        ]
    },

    "staff_mnr_income_supreme": {
        "purpose": "Supreme-level income monitoring dashboard. Provides the highest-level overview of all income calculations across the entire MNR Business Access Program - total payouts, pending income, and income health metrics.",
        "who_can_access": "Supreme Admin / Finance Supreme only",
        "main_sections": [
            {"name": "Income Dashboard", "description": "Real-time totals across all four income streams - Direct Referral, Matching Referral, Ved Income, and Guru Dakshina"},
            {"name": "Daily Calculations", "description": "View daily income calculation runs, success/failure counts, and processing status"},
            {"name": "Income Health", "description": "System health indicators for income calculation engine"}
        ],
        "usage_flow": [
            "Open Supreme Income Monitor from MNR sidebar",
            "Review the dashboard for overall income health",
            "Check daily calculation summaries to ensure auto-approval ran correctly",
            "Drill into specific income types for detailed analysis",
            "Monitor pending income queue for processing delays"
        ],
        "fields": [
            {"name": "Total Direct Referral", "description": "Sum of all direct referral income calculated across the network"},
            {"name": "Total Matching Referral", "description": "Sum of all matching (binary pair) income"},
            {"name": "Total Ved Income", "description": "Sum of all Ved ownership income (from 3rd direct referral rule)"},
            {"name": "Total Guru Dakshina", "description": "Sum of all 2% mandatory deductions from gross earnings"},
            {"name": "Daily Processing", "description": "Status of the daily auto-approval scheduled job"},
            {"name": "Pending Count", "description": "Number of income entries awaiting processing"}
        ],
        "statuses": [
            {"status": "Calculated", "color": "#3b82f6", "meaning": "Income computed and pending approval"},
            {"status": "Approved", "color": "#059669", "meaning": "Income approved and credited to wallets"},
            {"status": "On Hold", "color": "#f59e0b", "meaning": "Income calculation paused due to system ceiling or review"},
            {"status": "Failed", "color": "#dc2626", "meaning": "Calculation error - requires investigation"}
        ],
        "tips": [
            "Check this page daily to ensure the auto-approval scheduler ran successfully",
            "Ved Income uses the 'No Cascading' rule - when a downline becomes a Ved Owner, they disconnect from upline's Ved team",
            "Guru Dakshina is always 2% of gross earnings - it's a system deduction, not configurable per member",
            "Daily ceiling limits may cause some income to be held - check the ceiling dashboard for details"
        ],
        "common_mistakes": [
            "Not checking the scheduler status - if auto-approval fails, all income stays in 'Calculated' state",
            "Ignoring 'Failed' calculations - these indicate data issues that need manual resolution",
            "Not understanding the difference between calculated income and approved income"
        ]
    },

    "staff_mnr_income_records": {
        "purpose": "Detailed record of all income transactions across the system. View individual income entries by member, income type, date, and status. Useful for resolving member income queries.",
        "who_can_access": "Staff with Income Records menu access",
        "main_sections": [
            {"name": "Income Records Table", "description": "Filterable, searchable table of all income entries with member details"},
            {"name": "Filters", "description": "Filter by income type (Direct/Matching/Ved/Guru Dakshina), date range, member, and status"},
            {"name": "Member Income View", "description": "Click a record to see the full income context for that member"}
        ],
        "usage_flow": [
            "Open Income Records from MNR sidebar",
            "Use filters to find specific income entries",
            "Filter by member MNR ID to investigate a specific member's income",
            "Check dates to verify correct calculation periods",
            "Review income source (which downline action triggered the income)"
        ],
        "fields": [
            {"name": "Income Type", "description": "One of four types: Direct Referral, Matching Referral, Ved Income, or Guru Dakshina"},
            {"name": "Amount", "description": "Calculated income amount for this entry"},
            {"name": "Source Member", "description": "The downline member whose action triggered this income"},
            {"name": "Beneficiary", "description": "The member who receives this income"},
            {"name": "Calculation Date", "description": "Date when the income was calculated"},
            {"name": "Status", "description": "Whether the income is pending, approved, or credited to wallet"}
        ],
        "statuses": [
            {"status": "Pending", "color": "#f59e0b", "meaning": "Calculated but not yet approved"},
            {"status": "Approved", "color": "#059669", "meaning": "Approved and credited to member's wallet"},
            {"status": "Rejected", "color": "#dc2626", "meaning": "Income entry rejected due to validation failure"}
        ],
        "tips": [
            "Direct Referral income is earned when a direct downline member activates their package",
            "Matching Referral is calculated based on paired points from Left and Right binary tree legs",
            "Ved Income triggers when a member gets their 3rd direct referral - that 3rd person becomes the Ved Head",
            "Use date range filters to isolate income for specific periods"
        ],
        "common_mistakes": [
            "Confusing income 'source' (who triggered it) with 'beneficiary' (who earns it)",
            "Not understanding the Ved Income cascading rule - downstream Ved Owners disconnect",
            "Looking at individual entries without considering daily ceiling limits"
        ]
    },

    "staff_mnr_income_unified": {
        "purpose": "Unified income management view combining all four income streams into a single management interface. Provides tools for income review, manual adjustments, and bulk operations.",
        "who_can_access": "Staff with Income Management menu access",
        "main_sections": [
            {"name": "Unified Dashboard", "description": "Combined view of all income types with summary totals and trend charts"},
            {"name": "Income Queue", "description": "Pending income entries that need review or approval"},
            {"name": "Manual Operations", "description": "Tools for manual income adjustments when needed"}
        ],
        "usage_flow": [
            "Open Income Management from MNR sidebar",
            "Review the unified dashboard for overall income picture",
            "Check the pending queue for items needing attention",
            "Use search to find specific member income records",
            "Process any manual adjustments with proper documentation"
        ],
        "fields": [
            {"name": "Direct Referral", "description": "Income from personally referred members who activate"},
            {"name": "Matching Referral", "description": "Binary tree pair matching income (Left-Right leg points)"},
            {"name": "Ved Income", "description": "Multi-level ownership income from 3rd direct referral chain"},
            {"name": "Guru Dakshina", "description": "2% mandatory deduction from gross earnings"}
        ],
        "statuses": [],
        "tips": [
            "Use this page for day-to-day income management",
            "The daily auto-approval runs Mon-Sat at 7 AM - check after this time for latest data",
            "Any manual adjustments must be documented with clear reasons"
        ],
        "common_mistakes": [
            "Making manual adjustments without proper authorization",
            "Not waiting for the daily auto-approval before manually processing entries"
        ]
    },

    "staff_mnr_withdrawal_approvals": {
        "purpose": "Process member withdrawal requests through the multi-step approval pipeline. Withdrawals follow a strict chain: Admin Verified -> Super Admin Approved -> Finance Admin (Final Payout).",
        "who_can_access": "Staff with Withdrawal Approvals menu access (Admin, Super Admin, Finance Admin)",
        "main_sections": [
            {"name": "Approval Queue", "description": "Withdrawal requests at your approval stage - based on your role"},
            {"name": "Processing Pipeline", "description": "Visual pipeline showing requests at each approval stage"},
            {"name": "Payout Details", "description": "Final payout information including deductions and net amount"}
        ],
        "usage_flow": [
            "Open Withdrawal Approvals from MNR sidebar",
            "Review your queue of pending approvals (based on your role level)",
            "Click a request to see member details, wallet balance, and withdrawal amount",
            "Verify the member has approved KYC and Bank details",
            "Step 1 - Admin Verified: First-level approval confirming the request is valid",
            "Step 2 - Super Admin Approved: Second-level confirmation",
            "Step 3 - Finance Admin: Final payout processing with deduction calculations",
            "System auto-calculates: 8% Admin Charge + 2% TDS = Net payout amount"
        ],
        "fields": [
            {"name": "Withdrawal Amount", "description": "Gross amount requested by the member"},
            {"name": "Admin Charge (8%)", "description": "Standard administrative deduction from withdrawal"},
            {"name": "TDS (2%)", "description": "Tax deducted at source as per regulations"},
            {"name": "Net Payout", "description": "Final amount the member receives (Gross - 8% - 2%)"},
            {"name": "Wallet Balance", "description": "Member's current Withdrawable wallet balance"},
            {"name": "Bank Details", "description": "Approved bank account where payout will be sent"}
        ],
        "statuses": [
            {"status": "Pending", "color": "#f59e0b", "meaning": "Auto-generated request awaiting first approval"},
            {"status": "Admin Verified", "color": "#3b82f6", "meaning": "First-level approval completed"},
            {"status": "Super Admin Approved", "color": "#8b5cf6", "meaning": "Second-level approval completed"},
            {"status": "Finance Approved", "color": "#059669", "meaning": "Final approval - payout processed"},
            {"status": "Rejected", "color": "#dc2626", "meaning": "Request declined at any stage with reason"},
            {"status": "On Hold", "color": "#6b7280", "meaning": "Temporarily paused for investigation"}
        ],
        "tips": [
            "Withdrawals are now AUTO-GENERATED (Mon-Sat, 7 AM) for balances above Rs 2,000 with Rs 1,000 buffer",
            "Manual withdrawal requests are deprecated - system handles it automatically",
            "Always verify KYC + Bank are both 'Approved' before processing a withdrawal",
            "Deductions: 8% Admin Charge + 2% TDS are automatically calculated",
            "Net payout = Withdrawal Amount - 8% Admin Charge - 2% TDS"
        ],
        "common_mistakes": [
            "Processing a withdrawal when KYC or Bank details are not fully approved",
            "Trying to manually override deduction calculations",
            "Approving withdrawals that exceed the member's Withdrawable wallet balance",
            "Not checking if the member's bank details were recently changed (potential fraud indicator)"
        ]
    },

    "staff_mnr_withdrawal_history": {
        "purpose": "Complete historical record of all withdrawal transactions. Track payouts, view deduction breakdowns, and audit the full withdrawal timeline for any member.",
        "who_can_access": "Staff with Withdrawal History menu access",
        "main_sections": [
            {"name": "Transaction History", "description": "Chronological list of all processed withdrawals with amounts, dates, and statuses"},
            {"name": "Filters", "description": "Filter by date range, member, status, or amount range"},
            {"name": "Transaction Details", "description": "Full breakdown showing gross amount, deductions, and net payout"}
        ],
        "usage_flow": [
            "Open Withdrawal History from MNR sidebar",
            "Use filters to find specific transactions",
            "Search by member MNR ID to see their complete withdrawal history",
            "Click a transaction to view full deduction breakdown",
            "Export data for reconciliation or reporting"
        ],
        "fields": [
            {"name": "Transaction ID", "description": "Unique identifier for the withdrawal transaction"},
            {"name": "Member", "description": "MNR ID and name of the withdrawing member"},
            {"name": "Gross Amount", "description": "Original withdrawal amount before deductions"},
            {"name": "Admin Charge", "description": "8% administrative deduction"},
            {"name": "TDS", "description": "2% tax deducted at source"},
            {"name": "Net Amount", "description": "Final payout amount after all deductions"},
            {"name": "Payout Date", "description": "Date when the payout was processed"}
        ],
        "statuses": [
            {"status": "Completed", "color": "#059669", "meaning": "Payout successfully processed"},
            {"status": "Rejected", "color": "#dc2626", "meaning": "Withdrawal was rejected"},
            {"status": "Reversed", "color": "#f59e0b", "meaning": "Payout was reversed and funds returned to wallet"}
        ],
        "tips": [
            "Use this page to resolve member queries about their withdrawal status",
            "Check the deduction breakdown if a member questions their net payout amount",
            "Export feature is useful for monthly reconciliation with finance"
        ],
        "common_mistakes": [
            "Confusing gross amount with net payout when communicating with members",
            "Not checking the full approval chain history when investigating disputed transactions"
        ]
    },

    "staff_mnr_withdrawal_supreme": {
        "purpose": "Supreme-level oversight of the entire withdrawal system. Provides aggregate statistics, system health monitoring, and emergency controls for the withdrawal pipeline.",
        "who_can_access": "Supreme Admin only",
        "main_sections": [
            {"name": "Withdrawal Dashboard", "description": "Aggregate totals - total payouts, pending amounts, daily/weekly/monthly trends"},
            {"name": "Pipeline Health", "description": "Status of the auto-withdrawal scheduler and processing pipeline"},
            {"name": "Emergency Controls", "description": "Ability to pause/resume the withdrawal system if needed"}
        ],
        "usage_flow": [
            "Open Withdrawal Supreme from MNR sidebar",
            "Review aggregate withdrawal statistics",
            "Monitor the auto-withdrawal scheduler status",
            "Check for pipeline bottlenecks (requests stuck at any approval stage)",
            "Use emergency controls only when absolutely necessary"
        ],
        "fields": [
            {"name": "Total Processed", "description": "Sum of all successfully processed withdrawals"},
            {"name": "Pending Pipeline", "description": "Total value of requests currently in the approval pipeline"},
            {"name": "Daily Volume", "description": "Today's withdrawal processing volume"},
            {"name": "Auto-Generator Status", "description": "Whether the Mon-Sat 7 AM auto-generation is running"}
        ],
        "statuses": [],
        "tips": [
            "Check this dashboard daily to ensure the withdrawal system is operating normally",
            "If the auto-generator shows 'Failed', investigate immediately as members won't get automatic withdrawals",
            "Pipeline bottlenecks usually indicate a staffing or approval workflow issue"
        ],
        "common_mistakes": [
            "Using emergency pause without notifying all stakeholders",
            "Not monitoring the auto-generator status regularly"
        ]
    },

    "staff_mnr_awards_all": {
        "purpose": "Manage the complete awards lifecycle for MNR members. Track milestone achievements, process award claims, and manage the 6-stage award lifecycle from nomination to delivery.",
        "who_can_access": "Staff with Awards menu access",
        "main_sections": [
            {"name": "Awards Dashboard", "description": "Overview of all award types, total nominations, processing status, and delivery tracking"},
            {"name": "Award Queue", "description": "List of pending award nominations and claims requiring processing"},
            {"name": "Award History", "description": "Complete history of all processed awards with delivery status"}
        ],
        "usage_flow": [
            "Open All Awards from MNR sidebar",
            "Review the awards dashboard for pending nominations",
            "Click on an award to view the member's achievement details",
            "Verify the member meets the qualification criteria",
            "Process through the 6-stage lifecycle: Nominated -> Verified -> Approved -> Ordered -> Dispatched -> Delivered",
            "Update delivery tracking information as the award ships"
        ],
        "fields": [
            {"name": "Award Type", "description": "Category of the award (milestone, performance, rank achievement, etc.)"},
            {"name": "Member", "description": "MNR ID and name of the award recipient"},
            {"name": "Qualification Criteria", "description": "What the member achieved to earn this award"},
            {"name": "Stage", "description": "Current position in the 6-stage lifecycle"},
            {"name": "Tracking Info", "description": "Shipping/delivery tracking for physical awards"}
        ],
        "statuses": [
            {"status": "Nominated", "color": "#8b5cf6", "meaning": "Member qualifies, nomination created"},
            {"status": "Verified", "color": "#3b82f6", "meaning": "Qualification criteria verified by staff"},
            {"status": "Approved", "color": "#059669", "meaning": "Award approved for processing"},
            {"status": "Ordered", "color": "#f59e0b", "meaning": "Physical award ordered from vendor"},
            {"status": "Dispatched", "color": "#06b6d4", "meaning": "Award shipped, tracking available"},
            {"status": "Delivered", "color": "#059669", "meaning": "Award received by member - lifecycle complete"}
        ],
        "tips": [
            "The 6-stage lifecycle ensures full tracking from nomination to delivery",
            "Always verify qualification criteria before moving to 'Verified' stage",
            "Update tracking information promptly when awards are dispatched",
            "Members can see their award status in their portal - keep stages current"
        ],
        "common_mistakes": [
            "Skipping the verification stage and jumping directly to approved",
            "Not updating tracking information after dispatch",
            "Approving awards for members who don't meet the criteria"
        ]
    },

    "staff_mnr_bonanza_claims": {
        "purpose": "Manage staff bonanza programs - special reward programs with claim submission and approval workflows. Staff submit claims for bonanza achievements, which are reviewed and approved.",
        "who_can_access": "Staff with Bonanza Claims menu access",
        "main_sections": [
            {"name": "Active Bonanzas", "description": "Currently running bonanza programs with eligibility criteria"},
            {"name": "Claims Queue", "description": "Submitted claims awaiting review and approval"},
            {"name": "Claims History", "description": "Past bonanza claims with approval/rejection outcomes"}
        ],
        "usage_flow": [
            "Open Bonanza Claims from MNR sidebar",
            "Review active bonanza programs and their criteria",
            "Check the claims queue for pending submissions",
            "Verify each claim against the bonanza criteria",
            "Approve eligible claims or reject with documented reasons"
        ],
        "fields": [
            {"name": "Bonanza Name", "description": "Name/title of the bonanza program"},
            {"name": "Criteria", "description": "What must be achieved to qualify for the bonanza"},
            {"name": "Claim Amount", "description": "Value of the bonanza reward"},
            {"name": "Receipt Number", "description": "Unique receipt number generated for approved claims"},
            {"name": "Claimant", "description": "Staff member who submitted the claim"}
        ],
        "statuses": [
            {"status": "Submitted", "color": "#f59e0b", "meaning": "Claim submitted, awaiting review"},
            {"status": "Approved", "color": "#059669", "meaning": "Claim verified and approved - receipt generated"},
            {"status": "Rejected", "color": "#dc2626", "meaning": "Claim does not meet criteria"}
        ],
        "tips": [
            "Each approved claim generates a unique receipt number for tracking",
            "Verify bonanza criteria carefully before approving claims",
            "Check for duplicate claims from the same person for the same bonanza"
        ],
        "common_mistakes": [
            "Approving claims without verifying the criteria were actually met",
            "Not checking for duplicate submissions"
        ]
    },

    "staff_mnr_banner_analytics": {
        "purpose": "Track the performance of announcement banners displayed to MNR members. View impression counts, click-through rates, and engagement metrics for each banner.",
        "who_can_access": "Staff with Communications menu access",
        "main_sections": [
            {"name": "Banner Performance", "description": "Analytics dashboard showing impressions, clicks, and engagement for each banner"},
            {"name": "Active Banners", "description": "Currently displayed banners with real-time performance data"},
            {"name": "Historical Data", "description": "Past banner performance for trend analysis"}
        ],
        "usage_flow": [
            "Open Banner Analytics from MNR sidebar",
            "Review active banner performance metrics",
            "Compare engagement rates across different banners",
            "Identify high-performing and low-performing content",
            "Use insights to optimize future banner campaigns"
        ],
        "fields": [
            {"name": "Banner Title", "description": "Name/title of the announcement banner"},
            {"name": "Impressions", "description": "Number of times the banner was shown to members"},
            {"name": "Clicks", "description": "Number of times members clicked on the banner"},
            {"name": "CTR", "description": "Click-through rate (Clicks / Impressions * 100)"},
            {"name": "Active Period", "description": "Date range when the banner was/is displayed"}
        ],
        "statuses": [],
        "tips": [
            "Higher CTR indicates more engaging content - study what works",
            "Check analytics before removing or replacing banners"
        ],
        "common_mistakes": [
            "Removing banners without checking their analytics first",
            "Not A/B testing different banner messages"
        ]
    },

    "staff_mnr_rate_configuration": {
        "purpose": "Configure income calculation rates for the MNR system. Set percentages for each income type, define package-specific rates, and manage the wallet split ratios between Earning and Withdrawable wallets.",
        "who_can_access": "Supreme Admin / System Configuration access only",
        "main_sections": [
            {"name": "Income Rates", "description": "Percentage configuration for Direct Referral, Matching Referral, Ved Income rates"},
            {"name": "Package Rates", "description": "Per-package rate configurations (Platinum/Diamond/Star)"},
            {"name": "Wallet Split", "description": "Configuration for how income splits between Earning and Withdrawable wallets"}
        ],
        "usage_flow": [
            "Open Rate Configuration from MNR Config sidebar",
            "Review current rate settings for each income type",
            "Modify rates only with proper authorization",
            "Save changes - they take effect from the next calculation cycle",
            "Verify the changes in a test calculation before going live"
        ],
        "fields": [
            {"name": "Direct Referral Rate", "description": "Percentage earned when a direct referral activates"},
            {"name": "Matching Referral Rate", "description": "Percentage for binary tree leg matching"},
            {"name": "Ved Income Rate", "description": "Percentage for Ved ownership chain income"},
            {"name": "Guru Dakshina Rate", "description": "Mandatory deduction percentage (standard: 2%)"},
            {"name": "Wallet Split Ratio", "description": "How income divides between Earning and Withdrawable wallets per package"}
        ],
        "statuses": [],
        "tips": [
            "Rate changes affect ALL future calculations - change with extreme caution",
            "Always document the reason for any rate change",
            "Guru Dakshina rate is typically fixed at 2% and rarely changed",
            "Test changes in sandbox environment before applying to production"
        ],
        "common_mistakes": [
            "Changing rates without understanding the ripple effect on all members",
            "Forgetting that rate changes only affect future calculations, not past income",
            "Modifying rates without proper Supreme Admin authorization"
        ]
    },

    "staff_mnr_daily_ceiling": {
        "purpose": "Set and manage daily income ceilings for the MNR system. Ceilings limit the maximum total income that can be distributed in a single day, protecting against system anomalies.",
        "who_can_access": "Supreme Admin only",
        "main_sections": [
            {"name": "Current Ceiling", "description": "Today's ceiling setting and how much of it has been utilized"},
            {"name": "Ceiling History", "description": "Past ceiling settings and utilization percentages"},
            {"name": "Ceiling Configuration", "description": "Set new ceiling amounts and activation dates"}
        ],
        "usage_flow": [
            "Open Daily Ceiling from MNR Config sidebar",
            "Review today's ceiling and current utilization",
            "If approaching the ceiling, investigate for anomalies",
            "Adjust ceiling amount if justified (with documentation)",
            "Monitor utilization trends over time"
        ],
        "fields": [
            {"name": "Ceiling Amount", "description": "Maximum total income distributable in a single day"},
            {"name": "Utilized Amount", "description": "How much of today's ceiling has been consumed"},
            {"name": "Utilization %", "description": "Percentage of ceiling consumed (Utilized / Ceiling * 100)"},
            {"name": "Effective Date", "description": "Date when the ceiling setting takes effect"}
        ],
        "statuses": [],
        "tips": [
            "If utilization hits 100%, income calculations for that day will be held until the next day",
            "Monitor trends - consistently hitting ceiling may indicate need for adjustment",
            "Sudden spikes in utilization could indicate bulk activations or system issues"
        ],
        "common_mistakes": [
            "Setting the ceiling too low, causing legitimate income to be delayed",
            "Setting the ceiling too high, removing the safety net against anomalies",
            "Not monitoring utilization daily"
        ]
    },

    "staff_mnr_emergency_wallet": {
        "purpose": "Emergency wallet controls for exceptional situations. Allows authorized staff to manually adjust wallet balances, process emergency credits/debits, and handle edge cases that automated systems cannot resolve.",
        "who_can_access": "Supreme Admin only",
        "main_sections": [
            {"name": "Emergency Operations", "description": "Tools for manual wallet adjustments with mandatory reason logging"},
            {"name": "Adjustment History", "description": "Audit trail of all emergency wallet operations"}
        ],
        "usage_flow": [
            "Open Emergency Wallet from MNR Config sidebar",
            "Search for the member by MNR ID",
            "Review their current wallet balances (Earning + Withdrawable)",
            "Enter the adjustment amount and mandatory reason",
            "Confirm the operation - it's logged with your staff ID and timestamp"
        ],
        "fields": [
            {"name": "Member MNR ID", "description": "Target member for the wallet adjustment"},
            {"name": "Current Balance", "description": "Member's current Earning and Withdrawable wallet amounts"},
            {"name": "Adjustment Amount", "description": "Amount to credit (+) or debit (-) from the wallet"},
            {"name": "Reason", "description": "Mandatory reason for the emergency adjustment"},
            {"name": "Adjusted By", "description": "Staff member who performed the operation"}
        ],
        "statuses": [],
        "tips": [
            "CRITICAL: Every emergency operation is permanently logged and auditable",
            "Only use for genuine emergencies - system errors, reversal corrections, etc.",
            "Always document the reason clearly and specifically",
            "Verify the member MNR ID twice before confirming"
        ],
        "common_mistakes": [
            "Using emergency wallet for routine operations that should go through normal channels",
            "Not providing a specific enough reason for the adjustment",
            "Adjusting the wrong member's wallet due to MNR ID entry error"
        ]
    },

    "staff_mnr_role_management": {
        "purpose": "Define and manage roles within the MNR system. Control which staff members have access to specific MNR administrative functions through role assignments.",
        "who_can_access": "Supreme Admin / HR Admin",
        "main_sections": [
            {"name": "Role Definitions", "description": "List of all defined roles with their permission scopes"},
            {"name": "Role Assignments", "description": "Staff-to-role mapping showing who has which roles"},
            {"name": "Permission Matrix", "description": "Detailed view of what each role can do"}
        ],
        "usage_flow": [
            "Open Role Management from MNR Config sidebar",
            "Review existing roles and their permissions",
            "Assign roles to staff members based on their responsibilities",
            "Create new roles if needed for specific MNR functions",
            "Remove role assignments when staff change positions"
        ],
        "fields": [
            {"name": "Role Name", "description": "Title of the role (Admin, Finance Admin, Supreme Admin, etc.)"},
            {"name": "Permissions", "description": "List of actions this role can perform"},
            {"name": "Assigned Staff", "description": "Staff members currently assigned to this role"},
            {"name": "Last Modified", "description": "When this role was last updated"}
        ],
        "statuses": [],
        "tips": [
            "Follow the principle of least privilege - assign minimum necessary permissions",
            "Review role assignments quarterly to remove stale access",
            "Document the reason for every role assignment change"
        ],
        "common_mistakes": [
            "Giving Supreme Admin access when lower-level access would suffice",
            "Not revoking access when staff change departments or leave",
            "Creating too many granular roles instead of using existing ones"
        ]
    },

    "staff_mnr_add_packages": {
        "purpose": "Manage MNR package definitions - create, modify, and configure package types (Platinum, Diamond, Star) including their pricing, point values, and income calculation parameters.",
        "who_can_access": "Supreme Admin only",
        "main_sections": [
            {"name": "Package List", "description": "All defined packages with their configuration details"},
            {"name": "Package Configuration", "description": "Pricing, point values, and income parameters per package"},
            {"name": "MNR Points Allocation", "description": "Points given upon activation per package (Platinum: 30k, Diamond: 15k, Star: 2k)"}
        ],
        "usage_flow": [
            "Open Add Packages from MNR Config sidebar",
            "Review existing package configurations",
            "Modify pricing or point values if authorized",
            "Save changes - they apply to future activations only"
        ],
        "fields": [
            {"name": "Package Name", "description": "Platinum, Diamond, or Star"},
            {"name": "Decimal Points", "description": "Point value for binary tree matching: Platinum=1.0, Diamond=0.5, Star=0.0"},
            {"name": "Price", "description": "Cost to purchase a PIN for this package"},
            {"name": "MNR Points", "description": "Points allocated upon activation (expire in 24 months)"},
            {"name": "Income Eligibility", "description": "Which income types this package qualifies for"}
        ],
        "statuses": [],
        "tips": [
            "Package changes only affect future activations - existing members keep their current package terms",
            "Platinum (1.0 point) members drive the most binary tree growth",
            "MNR Points expire in 24 months - this is system-wide, not per-package configurable"
        ],
        "common_mistakes": [
            "Modifying package pricing without coordinating with PIN pricing",
            "Not understanding that point values directly affect Matching Referral calculations"
        ]
    },

    "staff_mnr_menu_access_config": {
        "purpose": "Configure which menu items are accessible to which roles. This is the Zero-Default Access Policy enforcement page - new staff start with NO access and must be explicitly granted permissions.",
        "who_can_access": "Supreme Admin / HR Admin only",
        "main_sections": [
            {"name": "Menu Tree", "description": "Hierarchical view of all menu items across the system"},
            {"name": "Role Mapping", "description": "Which roles have access to which menu items"},
            {"name": "Staff Access", "description": "Individual staff member's menu access configuration"}
        ],
        "usage_flow": [
            "Open Menu Access Config from MNR Config sidebar",
            "Select a staff member or role to configure",
            "Check/uncheck menu items to grant/revoke access",
            "Granting a parent section cascades access to all children",
            "Save the configuration - takes effect immediately"
        ],
        "fields": [
            {"name": "Menu Item", "description": "Page or section name in the system"},
            {"name": "Access Granted", "description": "Whether the selected role/user has access (checkbox)"},
            {"name": "Cascade", "description": "Whether granting parent access automatically includes children"}
        ],
        "statuses": [],
        "tips": [
            "Zero-Default: New staff have NO access until explicitly granted",
            "Use role-based assignment for consistency rather than per-person",
            "Parent section cascade is useful but review child items to ensure no over-granting",
            "All access changes are audit-logged"
        ],
        "common_mistakes": [
            "Granting a parent section without reviewing all child items included",
            "Not understanding that changes take effect immediately",
            "Assigning per-person access instead of using roles for consistency"
        ]
    },

    "staff_mnr_scheduler_dashboard": {
        "purpose": "Monitor and manage all automated scheduled jobs in the MNR system - daily income calculations, auto-withdrawal generation, ceiling resets, and other periodic tasks.",
        "who_can_access": "Supreme Admin / System Admin",
        "main_sections": [
            {"name": "Scheduler Status", "description": "Real-time status of all scheduled jobs (running, stopped, failed)"},
            {"name": "Job History", "description": "Execution history with success/failure logs for each job"},
            {"name": "Controls", "description": "Start, stop, or reschedule individual jobs"}
        ],
        "usage_flow": [
            "Open Scheduler Dashboard from MNR Config sidebar",
            "Review the status of all scheduled jobs",
            "Check the 'Last Run' and 'Next Run' times for each job",
            "Investigate any 'Failed' jobs and their error logs",
            "Restart failed jobs after resolving the underlying issue"
        ],
        "fields": [
            {"name": "Job Name", "description": "Name of the scheduled task (e.g., 'Daily Income Auto-Approval', 'Auto-Withdrawal Generator')"},
            {"name": "Schedule", "description": "Cron expression or frequency (e.g., 'Mon-Sat 7:00 AM')"},
            {"name": "Status", "description": "Running, Stopped, or Failed"},
            {"name": "Last Run", "description": "When the job last executed"},
            {"name": "Next Run", "description": "When the job is next scheduled to run"},
            {"name": "Last Result", "description": "Success/Failure with details of the last execution"}
        ],
        "statuses": [
            {"status": "Running", "color": "#059669", "meaning": "Job is active and will execute on schedule"},
            {"status": "Stopped", "color": "#6b7280", "meaning": "Job is manually paused and won't execute"},
            {"status": "Failed", "color": "#dc2626", "meaning": "Last execution failed - requires investigation"}
        ],
        "tips": [
            "CRITICAL: If 'Daily Income Auto-Approval' fails, all income stays pending until fixed",
            "If 'Auto-Withdrawal Generator' fails, no new withdrawal requests are created",
            "Check this dashboard first thing every morning",
            "Failed jobs usually indicate database or configuration issues"
        ],
        "common_mistakes": [
            "Not monitoring scheduler status daily - failures go unnoticed",
            "Stopping a job for testing and forgetting to restart it",
            "Not investigating the root cause of failures before restarting"
        ]
    },

    "staff_mnr_change_user_password": {
        "purpose": "Reset or change an MNR member's login password. Used when members cannot access their account or have forgotten their password.",
        "who_can_access": "Staff with Security menu access",
        "main_sections": [
            {"name": "Member Search", "description": "Find the member by MNR ID, name, or phone number"},
            {"name": "Password Reset", "description": "Set a new password for the member"}
        ],
        "usage_flow": [
            "Open Change User Password from MNR Security sidebar",
            "Search for the member by MNR ID or phone number",
            "Verify the member's identity through security questions or other verification",
            "Enter the new password",
            "Confirm the change - member will need to use the new password for next login"
        ],
        "fields": [
            {"name": "MNR ID", "description": "Member's unique identifier to find their account"},
            {"name": "New Password", "description": "The replacement password"},
            {"name": "Confirm Password", "description": "Re-enter to prevent typos"}
        ],
        "statuses": [],
        "tips": [
            "Always verify the member's identity before resetting their password",
            "Advise members to change the password again after login for security",
            "Password resets are logged in the audit trail"
        ],
        "common_mistakes": [
            "Resetting password without proper identity verification",
            "Not communicating the new password securely to the member",
            "Resetting the wrong member's password due to MNR ID confusion"
        ]
    },

    "staff_mnr_password_change": {
        "purpose": "Staff tool for managing password policies and bulk password operations. Different from individual password change - this handles policy enforcement and system-wide password management.",
        "who_can_access": "Supreme Admin / Security Admin",
        "main_sections": [
            {"name": "Password Policy", "description": "Configure password complexity requirements and expiry settings"},
            {"name": "Bulk Operations", "description": "Mass password-related operations for multiple members"}
        ],
        "usage_flow": [
            "Open Password Change from MNR Security sidebar",
            "Review current password policies",
            "Modify policies if authorized",
            "Run bulk operations if needed (e.g., force password reset for all inactive members)"
        ],
        "fields": [],
        "statuses": [],
        "tips": [
            "Password policy changes affect all members going forward",
            "Bulk operations should be used sparingly and with proper authorization"
        ],
        "common_mistakes": [
            "Making password policies too strict, causing member login issues",
            "Running bulk operations without proper testing"
        ]
    },

    "staff_mnr_secondary_password_setup": {
        "purpose": "Configure secondary password (transaction password) for high-value operations. This adds an extra security layer for sensitive actions like withdrawals and profile changes.",
        "who_can_access": "Staff with Security menu access",
        "main_sections": [
            {"name": "Secondary Password Setup", "description": "Enable/configure secondary password for members"},
            {"name": "Reset Requests", "description": "Process member requests to reset their secondary password"}
        ],
        "usage_flow": [
            "Open Secondary Password Setup from MNR Security sidebar",
            "Find the member who needs secondary password setup or reset",
            "Verify identity through primary password and security questions",
            "Set up or reset the secondary password",
            "Inform the member about when secondary password will be required"
        ],
        "fields": [
            {"name": "MNR ID", "description": "Member's unique identifier"},
            {"name": "Secondary Password Status", "description": "Whether secondary password is enabled for this member"},
            {"name": "Required For", "description": "Which operations require the secondary password (withdrawals, profile updates, etc.)"}
        ],
        "statuses": [],
        "tips": [
            "Secondary password provides crucial security for financial operations",
            "Always verify identity through primary means before resetting",
            "Document all secondary password resets in the audit trail"
        ],
        "common_mistakes": [
            "Setting up secondary password without explaining to the member when it will be needed",
            "Not verifying identity before resetting secondary password"
        ]
    },

    "staff_mnr_delete_management": {
        "purpose": "Manage data deletion requests and operations. Handles member data removal, account deactivation, and GDPR-style data management with full audit trails.",
        "who_can_access": "Supreme Admin only",
        "main_sections": [
            {"name": "Deletion Queue", "description": "Pending deletion requests requiring approval"},
            {"name": "Deletion History", "description": "Audit trail of all completed deletions with reasons and timestamps"},
            {"name": "Impact Analysis", "description": "Shows what data will be affected by a deletion (binary tree, income records, etc.)"}
        ],
        "usage_flow": [
            "Open Delete Management from MNR Data sidebar",
            "Review pending deletion requests",
            "Run impact analysis to understand what will be affected",
            "Approve or reject with documented reasoning",
            "Deletions are soft-delete (data retained but marked as deleted) unless explicitly permanent"
        ],
        "fields": [
            {"name": "Request Type", "description": "Type of deletion (account, data, partial)"},
            {"name": "Target", "description": "What is being deleted (member account, specific records, etc.)"},
            {"name": "Impact", "description": "Analysis of what else will be affected (downline, income, tree position)"},
            {"name": "Reason", "description": "Documented reason for the deletion"},
            {"name": "Requested By", "description": "Who initiated the deletion request"}
        ],
        "statuses": [
            {"status": "Requested", "color": "#f59e0b", "meaning": "Deletion requested, awaiting review"},
            {"status": "Under Review", "color": "#3b82f6", "meaning": "Impact analysis being conducted"},
            {"status": "Approved", "color": "#059669", "meaning": "Deletion approved and executed"},
            {"status": "Rejected", "color": "#dc2626", "meaning": "Deletion request declined"}
        ],
        "tips": [
            "CRITICAL: Always run impact analysis before approving any deletion",
            "Deleting a member affects their entire downline's binary tree",
            "Most deletions are soft-delete - data is retained but hidden",
            "All deletions are permanently logged for audit compliance"
        ],
        "common_mistakes": [
            "Approving deletion without understanding the impact on the binary tree",
            "Not checking if the member has active downline who would be affected",
            "Permanent deletion without proper authorization"
        ]
    },

    "staff_mnr_data_recovery": {
        "purpose": "Recover previously deleted or archived data. Undo soft-deletions, restore member accounts, and recover lost data from the system's recovery points.",
        "who_can_access": "Supreme Admin only",
        "main_sections": [
            {"name": "Recovery Queue", "description": "Recoverable items that were previously deleted or archived"},
            {"name": "Recovery History", "description": "Log of all recovery operations performed"}
        ],
        "usage_flow": [
            "Open Data Recovery from MNR Data sidebar",
            "Search for the deleted item by MNR ID, name, or date",
            "Review what was deleted and when",
            "Initiate recovery - system restores the data to its pre-deletion state",
            "Verify the recovery was successful"
        ],
        "fields": [
            {"name": "Deleted Item", "description": "What was deleted (member account, income records, etc.)"},
            {"name": "Deleted Date", "description": "When the deletion occurred"},
            {"name": "Deleted By", "description": "Who performed the deletion"},
            {"name": "Recovery Status", "description": "Whether the item can be recovered"}
        ],
        "statuses": [
            {"status": "Recoverable", "color": "#3b82f6", "meaning": "Item can be restored to its original state"},
            {"status": "Recovered", "color": "#059669", "meaning": "Item has been successfully restored"},
            {"status": "Permanent", "color": "#dc2626", "meaning": "Item was permanently deleted and cannot be recovered"}
        ],
        "tips": [
            "Only soft-deleted items can be recovered - permanent deletions cannot be undone",
            "Recovery restores all associated data (profile, income, tree position)",
            "Document the reason for recovery in the audit trail"
        ],
        "common_mistakes": [
            "Attempting to recover permanently deleted items",
            "Not verifying that recovery was complete (check all associated data)"
        ]
    },

    "staff_mnr_production_reset_status": {
        "purpose": "Monitor and manage production data reset operations. Track the status of system resets, database refresh operations, and data synchronization status.",
        "who_can_access": "Supreme Admin / System Admin",
        "main_sections": [
            {"name": "Reset Status", "description": "Current status of any ongoing or recent reset operations"},
            {"name": "Reset History", "description": "Log of all past reset operations with results"}
        ],
        "usage_flow": [
            "Open Production Reset Status from MNR Data sidebar",
            "Check if any reset operations are currently running",
            "Review the status and progress of ongoing operations",
            "Verify completion of past reset operations"
        ],
        "fields": [
            {"name": "Operation Type", "description": "Type of reset (data sync, cache refresh, etc.)"},
            {"name": "Status", "description": "Running, Completed, or Failed"},
            {"name": "Started At", "description": "When the operation began"},
            {"name": "Completed At", "description": "When the operation finished"},
            {"name": "Result", "description": "Outcome details and any errors"}
        ],
        "statuses": [
            {"status": "Running", "color": "#f59e0b", "meaning": "Reset operation in progress"},
            {"status": "Completed", "color": "#059669", "meaning": "Reset finished successfully"},
            {"status": "Failed", "color": "#dc2626", "meaning": "Reset encountered errors"}
        ],
        "tips": [
            "Never run production resets during peak usage hours",
            "Always verify reset completion before resuming normal operations"
        ],
        "common_mistakes": [
            "Running resets without proper planning or off-hours scheduling",
            "Not verifying data integrity after a reset operation"
        ]
    },

    "staff_mnr_finance_supreme": {
        "purpose": "Supreme-level financial oversight dashboard. Provides aggregate financial summaries across the entire MNR Business Access Program - total income distributed, total withdrawals, wallet balances, and financial health indicators.",
        "who_can_access": "Supreme Admin / Finance Supreme only",
        "main_sections": [
            {"name": "Financial Dashboard", "description": "Aggregate financial metrics - total income, total withdrawals, net wallet balances"},
            {"name": "Trend Analysis", "description": "Daily/weekly/monthly financial trends and projections"},
            {"name": "Cross-Module Summary", "description": "Financial impact across income, withdrawals, awards, and coupons"}
        ],
        "usage_flow": [
            "Open Finance Supreme from MNR Finance sidebar",
            "Review the financial dashboard for overall system health",
            "Check trend charts for unusual patterns",
            "Drill into specific financial modules for detailed analysis",
            "Export financial summaries for reporting"
        ],
        "fields": [
            {"name": "Total Income Distributed", "description": "Sum of all approved income across all members"},
            {"name": "Total Withdrawals Processed", "description": "Sum of all completed withdrawal payouts"},
            {"name": "Total Wallet Balance", "description": "Aggregate of all members' Earning + Withdrawable wallets"},
            {"name": "Net Financial Position", "description": "System-level financial summary"}
        ],
        "statuses": [],
        "tips": [
            "Review this dashboard daily for early detection of financial anomalies",
            "Compare daily totals against ceilings to ensure system is operating within limits",
            "Unusual spikes could indicate bulk activations, fraud, or system errors"
        ],
        "common_mistakes": [
            "Not reviewing daily - financial anomalies are easier to fix when caught early",
            "Confusing Earning wallet (pre-KYC) with Withdrawable wallet (post-KYC)"
        ]
    },

    "staff_mnr_financial_statement": {
        "purpose": "Generate and view financial statements for the MNR system. Produces formal financial reports including income statements, balance summaries, and transaction reports for compliance and auditing.",
        "who_can_access": "Finance Admin / Supreme Admin",
        "main_sections": [
            {"name": "Report Generator", "description": "Configure and generate financial reports by date range and type"},
            {"name": "Generated Reports", "description": "List of previously generated reports available for download"},
            {"name": "Compliance Reports", "description": "Regulatory compliance reports (TDS, income declarations, etc.)"}
        ],
        "usage_flow": [
            "Open Financial Statement from MNR Finance sidebar",
            "Select the report type and date range",
            "Configure any additional filters (by package, by region, etc.)",
            "Generate the report",
            "Download or export in the required format"
        ],
        "fields": [
            {"name": "Report Type", "description": "Income Statement, Balance Summary, Transaction Report, TDS Report, etc."},
            {"name": "Period", "description": "Date range for the report"},
            {"name": "Format", "description": "Export format (PDF, Excel, CSV)"},
            {"name": "Generated Date", "description": "When the report was created"}
        ],
        "statuses": [],
        "tips": [
            "Generate TDS reports monthly for compliance",
            "Keep generated reports archived for audit purposes",
            "Compare financial statements across periods to identify trends"
        ],
        "common_mistakes": [
            "Generating reports with incorrect date ranges",
            "Not archiving reports for compliance records"
        ]
    },

    "user_announcements": {
        "purpose": "View system announcements and company communications. Members can read important updates, policy changes, event notifications, and also submit their own announcements for approval.",
        "who_can_access": "All MNR Members",
        "main_sections": [
            {"name": "Announcements Feed", "description": "Chronological list of approved announcements with media attachments"},
            {"name": "Submit Announcement", "description": "Form to submit your own announcement for admin review"},
            {"name": "My Submissions", "description": "Track the status of your submitted announcements"}
        ],
        "usage_flow": [
            "Open Announcements from your member dashboard",
            "Browse the announcements feed for latest updates",
            "Click on an announcement to view full details and media",
            "To submit: Click 'Submit Announcement', fill in title, content, and optional media",
            "Track your submission status in 'My Submissions' tab"
        ],
        "fields": [
            {"name": "Title", "description": "Announcement headline"},
            {"name": "Content", "description": "Full announcement text"},
            {"name": "Media", "description": "Images, videos, or documents attached to the announcement"},
            {"name": "Category", "description": "Type of announcement (update, event, policy, etc.)"},
            {"name": "Published Date", "description": "When the announcement was made visible"}
        ],
        "statuses": [
            {"status": "Draft", "color": "#6b7280", "meaning": "Your submission is saved but not yet submitted"},
            {"status": "Pending", "color": "#f59e0b", "meaning": "Submitted and awaiting admin review"},
            {"status": "Approved", "color": "#059669", "meaning": "Approved and visible to all members"},
            {"status": "Rejected", "color": "#dc2626", "meaning": "Not approved - check rejection reason"}
        ],
        "tips": [
            "Check announcements regularly for important system updates",
            "When submitting, be clear and concise in your announcement content",
            "Include relevant media to make your announcement more engaging"
        ],
        "common_mistakes": [
            "Not checking announcements regularly and missing important updates",
            "Submitting announcements without proper content or context"
        ]
    },

    "user_daywise_income": {
        "purpose": "View your daily income breakdown across all four income streams. See exactly how much you earned each day from Direct Referral, Matching Referral, Ved Income, and Guru Dakshina deductions.",
        "who_can_access": "All Active MNR Members",
        "main_sections": [
            {"name": "Daily Income View", "description": "Day-by-day breakdown of all income received"},
            {"name": "Income Type Breakdown", "description": "Split of each day's income by type"},
            {"name": "Date Range Filter", "description": "View income for specific periods"}
        ],
        "usage_flow": [
            "Open Daywise Income from your member dashboard",
            "View today's income at the top",
            "Scroll down or use date filters for historical data",
            "Click on a day to see the detailed breakdown by income type",
            "See which downline actions generated each income entry"
        ],
        "fields": [
            {"name": "Date", "description": "The earning date"},
            {"name": "Direct Referral", "description": "Income from your direct referrals' activations"},
            {"name": "Matching Referral", "description": "Income from Left-Right leg pair matching"},
            {"name": "Ved Income", "description": "Income from your Ved ownership chain"},
            {"name": "Guru Dakshina", "description": "2% deduction from gross (shown as negative)"},
            {"name": "Net Income", "description": "Total income for the day after Guru Dakshina deduction"}
        ],
        "statuses": [
            {"status": "Credited", "color": "#059669", "meaning": "Income approved and added to your wallet"},
            {"status": "Pending", "color": "#f59e0b", "meaning": "Income calculated but awaiting approval"},
            {"status": "On Hold", "color": "#6b7280", "meaning": "Income held due to daily ceiling or review"}
        ],
        "tips": [
            "Income is auto-approved daily (Mon-Sat) - check after 7 AM for the latest",
            "Guru Dakshina (2%) is automatically deducted from your gross earnings",
            "If you see 'On Hold' income, it usually clears the next business day"
        ],
        "common_mistakes": [
            "Confusing gross income with net income (after Guru Dakshina)",
            "Not understanding that held income will be processed in subsequent days"
        ]
    },

    "user_direct_referral": {
        "purpose": "View your direct referral network - see all the members you personally referred, their activation status, and the income you earned from each referral.",
        "who_can_access": "All MNR Members",
        "main_sections": [
            {"name": "Referral List", "description": "All members you personally referred with their MNR IDs and status"},
            {"name": "Income from Referrals", "description": "Income earned from each direct referral's activation"},
            {"name": "Referral Stats", "description": "Total referrals, active count, and earning summary"}
        ],
        "usage_flow": [
            "Open Direct Referral from your member dashboard",
            "View your complete referral list",
            "Check which referrals are active vs inactive",
            "See income earned from each active referral",
            "Track your 3rd referral - they become your Ved Head (triggers Ved Income)"
        ],
        "fields": [
            {"name": "Referral MNR ID", "description": "MNR ID of the person you referred"},
            {"name": "Name", "description": "Name of your referral"},
            {"name": "Package", "description": "Package they activated with (Platinum/Diamond/Star)"},
            {"name": "Activation Date", "description": "When they activated their account"},
            {"name": "Income Earned", "description": "Direct referral income you earned from their activation"}
        ],
        "statuses": [
            {"status": "Active", "color": "#059669", "meaning": "Referral has activated their package"},
            {"status": "Inactive", "color": "#6b7280", "meaning": "Referral registered but not yet activated"}
        ],
        "tips": [
            "Your 3rd direct referral is special - they become your Ved Head, triggering Ved Income",
            "Platinum referrals generate higher income than Diamond or Star",
            "Follow up with inactive referrals to help them activate"
        ],
        "common_mistakes": [
            "Not tracking the 3rd referral which triggers the Ved Income benefit",
            "Confusing direct referrals (you referred) with downline (in your binary tree)"
        ]
    },

    "user_matching_referral": {
        "purpose": "View your matching referral (binary pair) income details. Shows how your Left and Right binary tree legs are matched and the income generated from paired points.",
        "who_can_access": "All Active MNR Members",
        "main_sections": [
            {"name": "Leg Summary", "description": "Left leg and Right leg point totals and balance"},
            {"name": "Matching Details", "description": "Day-wise matching calculations showing which points were paired"},
            {"name": "Carry Forward", "description": "Unmatched points carried forward to the next period"}
        ],
        "usage_flow": [
            "Open Matching Referral from your member dashboard",
            "View your Left and Right leg point totals",
            "See how many points were matched (paired) today",
            "Check the income generated from matched pairs",
            "View carry-forward points for the next cycle"
        ],
        "fields": [
            {"name": "Left Leg Points", "description": "Total points accumulated in your left binary tree leg"},
            {"name": "Right Leg Points", "description": "Total points accumulated in your right binary tree leg"},
            {"name": "Matched Points", "description": "Points that were paired (minimum of left and right) to generate income"},
            {"name": "Carry Forward", "description": "Excess points on the stronger side, carried to next cycle"},
            {"name": "Matching Income", "description": "Income calculated from the matched points"}
        ],
        "statuses": [],
        "tips": [
            "Matching works on the weaker leg - income is based on the LOWER of left/right points",
            "Build both legs equally for maximum matching efficiency",
            "Carry forward points don't expire but only match when the other leg catches up",
            "Platinum members contribute 1.0 point, Diamond 0.5 point to your legs"
        ],
        "common_mistakes": [
            "Focusing on only one leg and leaving the other empty - this creates zero matching",
            "Not understanding that matching is based on the weaker leg, not the stronger one"
        ]
    },

    "user_guru_dakshina": {
        "purpose": "View your Guru Dakshina deductions - the mandatory 2% contribution from your gross earnings. This page shows the running total and daily deductions.",
        "who_can_access": "All Active MNR Members",
        "main_sections": [
            {"name": "Deduction Summary", "description": "Total Guru Dakshina deducted to date"},
            {"name": "Daily Deductions", "description": "Day-wise breakdown of 2% deductions from gross income"}
        ],
        "usage_flow": [
            "Open Guru Dakshina from your member dashboard",
            "View total lifetime Guru Dakshina deductions",
            "Check daily breakdown to understand deduction calculations",
            "Cross-reference with your daywise income for verification"
        ],
        "fields": [
            {"name": "Gross Income", "description": "Your total income before Guru Dakshina deduction"},
            {"name": "Guru Dakshina (2%)", "description": "2% deduction amount"},
            {"name": "Net Income", "description": "Income after Guru Dakshina (Gross - 2%)"},
            {"name": "Date", "description": "Date of the deduction"}
        ],
        "statuses": [],
        "tips": [
            "Guru Dakshina is a flat 2% of gross earnings - it's non-negotiable",
            "This deduction appears automatically on every income calculation",
            "Net income = Gross income - 2% Guru Dakshina"
        ],
        "common_mistakes": [
            "Expecting the full gross amount in your wallet - 2% is always deducted",
            "Confusing Guru Dakshina with TDS (TDS is deducted at withdrawal, not at earning)"
        ]
    },

    "user_ev_benefits": {
        "purpose": "View your EV (Electric Vehicle) benefits and coupon entitlements. Shows available EV discounts, scooter purchase benefits, and the 6-benefit redemption system for EV coupons.",
        "who_can_access": "All Active MNR Members",
        "main_sections": [
            {"name": "Available Benefits", "description": "List of EV benefits you're entitled to based on your package and achievements"},
            {"name": "Redemption Status", "description": "Which benefits you've redeemed and which are still available"},
            {"name": "EV Coupon Details", "description": "Your EV coupon code and its 6-benefit breakdown"}
        ],
        "usage_flow": [
            "Open EV Benefits from your member dashboard",
            "Review your available EV benefits",
            "Check which of the 6 benefit categories apply to you",
            "Initiate redemption for eligible benefits",
            "Track redemption status until fulfilled"
        ],
        "fields": [
            {"name": "Benefit Type", "description": "Category of EV benefit (scooter discount, charging, training, etc.)"},
            {"name": "Eligibility", "description": "Whether you qualify based on package and activation"},
            {"name": "Coupon Code", "description": "Your EV benefit coupon for redemption"},
            {"name": "Redemption Status", "description": "Whether the benefit has been claimed"}
        ],
        "statuses": [
            {"status": "Available", "color": "#3b82f6", "meaning": "Benefit is available for redemption"},
            {"status": "Redeemed", "color": "#059669", "meaning": "Benefit has been claimed and processed"},
            {"status": "Expired", "color": "#6b7280", "meaning": "Benefit validity period has passed"}
        ],
        "tips": [
            "EV coupons have a 6-benefit redemption system - review all 6 categories",
            "Redemption requires staff approval - allow processing time",
            "Check benefit expiry dates to avoid missing out"
        ],
        "common_mistakes": [
            "Not redeeming benefits before they expire",
            "Trying to redeem benefits you're not eligible for based on your package"
        ]
    },

    "user_ev_discount": {
        "purpose": "Access your EV discount coupon for electric vehicle purchases. View discount percentage, applicable vehicles, and redemption instructions.",
        "who_can_access": "Eligible MNR Members (based on package and activation)",
        "main_sections": [
            {"name": "Discount Details", "description": "Your discount percentage and applicable EV models"},
            {"name": "Redemption Process", "description": "How to use your discount at authorized dealers"}
        ],
        "usage_flow": [
            "Open EV Discount from your member dashboard",
            "View your discount percentage and coupon code",
            "Check which EV models are eligible for the discount",
            "Present the coupon code at an authorized dealer for redemption"
        ],
        "fields": [
            {"name": "Discount Percentage", "description": "Your EV purchase discount rate"},
            {"name": "Coupon Code", "description": "Unique code to present at the dealer"},
            {"name": "Valid Until", "description": "Expiry date for the discount"},
            {"name": "Applicable Models", "description": "Which EV models this discount covers"}
        ],
        "statuses": [],
        "tips": [
            "Present the coupon code at authorized dealers only",
            "Check validity before visiting the dealer"
        ],
        "common_mistakes": [
            "Trying to use the coupon at non-authorized dealers",
            "Using an expired coupon"
        ]
    },

    "user_feedback_submit": {
        "purpose": "Submit feedback, suggestions, or complaints to the MNR administration. Your feedback is reviewed by the admin team and tracked for resolution.",
        "who_can_access": "All MNR Members",
        "main_sections": [
            {"name": "Submit Feedback", "description": "Form to submit your feedback with category selection"},
            {"name": "My Feedback History", "description": "Track status of previously submitted feedback"}
        ],
        "usage_flow": [
            "Open Submit Feedback from your member dashboard",
            "Select the feedback category (suggestion, complaint, query, etc.)",
            "Write your feedback in detail",
            "Submit the form",
            "Track the response in My Feedback History"
        ],
        "fields": [
            {"name": "Category", "description": "Type of feedback (Suggestion, Complaint, Query, Bug Report)"},
            {"name": "Subject", "description": "Brief summary of your feedback"},
            {"name": "Description", "description": "Detailed feedback content"},
            {"name": "Priority", "description": "Urgency level (Low, Medium, High)"}
        ],
        "statuses": [
            {"status": "Submitted", "color": "#3b82f6", "meaning": "Feedback received, awaiting review"},
            {"status": "Under Review", "color": "#f59e0b", "meaning": "Admin is reviewing your feedback"},
            {"status": "Resolved", "color": "#059669", "meaning": "Feedback addressed and resolved"},
            {"status": "Closed", "color": "#6b7280", "meaning": "Feedback closed (resolved or not actionable)"}
        ],
        "tips": [
            "Be specific and detailed in your feedback for faster resolution",
            "Include screenshots if reporting a bug or issue",
            "Check back for admin responses on your submissions"
        ],
        "common_mistakes": [
            "Submitting vague feedback without enough detail for the admin to act on",
            "Not checking back for admin responses"
        ]
    },

    "user_change_password": {
        "purpose": "Change your MNR member account login password. Use this to update your password for security or if you want to set a new one.",
        "who_can_access": "All MNR Members",
        "main_sections": [
            {"name": "Password Change Form", "description": "Enter current password and new password to update"}
        ],
        "usage_flow": [
            "Open Change Password from your member dashboard",
            "Enter your current password for verification",
            "Enter your new password",
            "Confirm the new password",
            "Submit - you'll need to use the new password for next login"
        ],
        "fields": [
            {"name": "Current Password", "description": "Your existing login password for verification"},
            {"name": "New Password", "description": "The password you want to use going forward"},
            {"name": "Confirm Password", "description": "Re-enter new password to prevent typos"}
        ],
        "statuses": [],
        "tips": [
            "Choose a strong password with a mix of letters, numbers, and special characters",
            "Don't share your password with anyone",
            "Change your password periodically for security"
        ],
        "common_mistakes": [
            "Forgetting the new password immediately after changing",
            "Using simple passwords that are easy to guess"
        ]
    },

    "team": {
        "purpose": "View your complete network of connections in the MNR binary tree. See your upline, downline, and the overall structure of your team across both Left and Right legs.",
        "who_can_access": "All MNR Members",
        "main_sections": [
            {"name": "Binary Tree View", "description": "Visual tree showing your position and your Left/Right leg members"},
            {"name": "Team List", "description": "Flat list of all members in your downline with their details"},
            {"name": "Leg Statistics", "description": "Left leg count, Right leg count, and total team size"}
        ],
        "usage_flow": [
            "Open All Connections from your member dashboard",
            "View your binary tree structure visually",
            "Click on team members to see their details",
            "Check Left and Right leg statistics",
            "Monitor team growth over time"
        ],
        "fields": [
            {"name": "Member Name", "description": "Name of the team member"},
            {"name": "MNR ID", "description": "Their unique MNR identifier"},
            {"name": "Position", "description": "Left or Right leg placement"},
            {"name": "Package", "description": "Their activation package"},
            {"name": "Join Date", "description": "When they joined the network"}
        ],
        "statuses": [
            {"status": "Active", "color": "#059669", "meaning": "Member is activated and contributing to your tree"},
            {"status": "Inactive", "color": "#6b7280", "meaning": "Member is registered but not yet activated"}
        ],
        "tips": [
            "Balance your Left and Right legs for maximum matching referral income",
            "Active members contribute points to your legs for matching calculations",
            "Track your team growth to understand your network health"
        ],
        "common_mistakes": [
            "Confusing your direct referrals with your binary tree placement - they can differ",
            "Not balancing legs leading to poor matching referral income"
        ]
    },

    "earnings_overview": {
        "purpose": "Comprehensive overview of all your earnings across every income stream. Provides a single-page summary of your total income, wallet balances, and earning trends.",
        "who_can_access": "All Active MNR Members",
        "main_sections": [
            {"name": "Total Earnings", "description": "Lifetime earnings summary across all income types"},
            {"name": "Wallet Balances", "description": "Current Earning wallet and Withdrawable wallet amounts"},
            {"name": "Income Breakdown", "description": "Pie chart and table showing income distribution by type"},
            {"name": "Recent Activity", "description": "Latest income entries and wallet movements"}
        ],
        "usage_flow": [
            "Open Earnings Overview from your member dashboard",
            "Review your total lifetime earnings at the top",
            "Check your current wallet balances",
            "View the income breakdown by type to understand your earning patterns",
            "Review recent activity for the latest changes"
        ],
        "fields": [
            {"name": "Total Earned", "description": "Lifetime sum of all income before deductions"},
            {"name": "Earning Wallet", "description": "Income held before KYC/Bank approval (not yet withdrawable)"},
            {"name": "Withdrawable Wallet", "description": "Funds available for withdrawal (KYC and Bank approved)"},
            {"name": "Total Withdrawn", "description": "Lifetime sum of all completed withdrawals"}
        ],
        "statuses": [],
        "tips": [
            "Earning wallet funds move to Withdrawable wallet after KYC and Bank are approved",
            "Withdrawals are auto-generated for balances above Rs 2,000",
            "Check this page daily to track your earnings growth"
        ],
        "common_mistakes": [
            "Expecting Earning wallet funds to be withdrawable before KYC/Bank approval",
            "Not understanding the dual wallet system (Earning vs Withdrawable)"
        ]
    },

    "user_withdrawals": {
        "purpose": "View your withdrawal history and track the status of pending withdrawal requests. Withdrawals are automatically generated when your Withdrawable wallet balance exceeds Rs 2,000.",
        "who_can_access": "All MNR Members with approved KYC and Bank details",
        "main_sections": [
            {"name": "Pending Withdrawals", "description": "Auto-generated withdrawal requests currently in the approval pipeline"},
            {"name": "Completed Withdrawals", "description": "History of all completed payouts with deduction breakdowns"},
            {"name": "Withdrawal Summary", "description": "Total withdrawn, pending amount, and next eligible date"}
        ],
        "usage_flow": [
            "Open Withdrawals from your member dashboard",
            "View any pending withdrawal requests and their approval stage",
            "Check completed withdrawals with deduction details",
            "Verify net payout calculations (Gross - 8% Admin Charge - 2% TDS)"
        ],
        "fields": [
            {"name": "Withdrawal Amount", "description": "Gross amount of the withdrawal request"},
            {"name": "Admin Charge (8%)", "description": "Administrative deduction"},
            {"name": "TDS (2%)", "description": "Tax deducted at source"},
            {"name": "Net Payout", "description": "Amount you receive (Gross - 8% - 2%)"},
            {"name": "Status", "description": "Current stage in the approval pipeline"},
            {"name": "Payout Date", "description": "Date when the payout was processed to your bank"}
        ],
        "statuses": [
            {"status": "Pending", "color": "#f59e0b", "meaning": "Auto-generated, awaiting admin approval"},
            {"status": "Processing", "color": "#3b82f6", "meaning": "Being processed through approval chain"},
            {"status": "Completed", "color": "#059669", "meaning": "Payout sent to your bank account"},
            {"status": "Rejected", "color": "#dc2626", "meaning": "Withdrawal rejected - check reason"}
        ],
        "tips": [
            "Withdrawals are auto-generated Mon-Sat at 7 AM for balances above Rs 2,000",
            "A Rs 1,000 buffer is maintained in your wallet",
            "Both KYC AND Bank must be approved for withdrawals to be created",
            "Net payout = Gross - 8% Admin Charge - 2% TDS"
        ],
        "common_mistakes": [
            "Expecting manual withdrawal - the system auto-generates them now",
            "Not having KYC and Bank approved - withdrawals won't be created",
            "Confusing gross amount with net payout"
        ]
    },

    "user_awards": {
        "purpose": "View your award achievements and track award delivery status. See which milestones you've reached and the status of your earned awards.",
        "who_can_access": "All MNR Members",
        "main_sections": [
            {"name": "My Awards", "description": "List of awards you've earned based on achievements"},
            {"name": "Award Status", "description": "Track each award through the 6-stage delivery lifecycle"},
            {"name": "Eligible Awards", "description": "Awards you're close to qualifying for"}
        ],
        "usage_flow": [
            "Open Awards from your member dashboard",
            "View your earned awards list",
            "Check the current stage of each award (Nominated through Delivered)",
            "View eligible awards to know what to work towards"
        ],
        "fields": [
            {"name": "Award Name", "description": "Title of the award"},
            {"name": "Achievement", "description": "What you accomplished to earn this award"},
            {"name": "Stage", "description": "Current position in the 6-stage lifecycle"},
            {"name": "Earned Date", "description": "When you qualified for this award"}
        ],
        "statuses": [
            {"status": "Nominated", "color": "#8b5cf6", "meaning": "You've qualified, nomination created"},
            {"status": "Verified", "color": "#3b82f6", "meaning": "Your qualification verified"},
            {"status": "Approved", "color": "#059669", "meaning": "Award approved for processing"},
            {"status": "Ordered", "color": "#f59e0b", "meaning": "Physical award ordered"},
            {"status": "Dispatched", "color": "#06b6d4", "meaning": "Award shipped to you"},
            {"status": "Delivered", "color": "#059669", "meaning": "Award received"}
        ],
        "tips": [
            "Awards go through 6 stages - track progress in this page",
            "Contact support if an award is stuck at any stage for too long"
        ],
        "common_mistakes": [
            "Expecting instant delivery - awards follow a multi-stage processing lifecycle"
        ]
    },

    "user_coupon_benefits": {
        "purpose": "View and manage your MNR coupon benefits. See available coupons, their values, and how to use them for various benefits including EV purchases, training, and services.",
        "who_can_access": "All Active MNR Members",
        "main_sections": [
            {"name": "Available Coupons", "description": "Coupons you currently have with their values and expiry dates"},
            {"name": "Coupon History", "description": "Past coupon usage and redemptions"},
            {"name": "Benefit Categories", "description": "The 6 benefit categories available for coupon redemption"}
        ],
        "usage_flow": [
            "Open Coupon Benefits from your member dashboard",
            "Review your available coupons and their values",
            "Check the 6 benefit categories to see what you can redeem",
            "Select a benefit to initiate redemption",
            "Follow the redemption process (may require staff approval)"
        ],
        "fields": [
            {"name": "Coupon Code", "description": "Your unique coupon identifier"},
            {"name": "Value", "description": "Monetary value or benefit value of the coupon"},
            {"name": "Category", "description": "Which benefit category this coupon falls under"},
            {"name": "Expiry Date", "description": "When the coupon expires if unused"},
            {"name": "Redemption Status", "description": "Whether the coupon has been used"}
        ],
        "statuses": [
            {"status": "Active", "color": "#059669", "meaning": "Coupon is valid and available for use"},
            {"status": "Redeemed", "color": "#3b82f6", "meaning": "Coupon has been used"},
            {"status": "Expired", "color": "#6b7280", "meaning": "Coupon validity period has passed"}
        ],
        "tips": [
            "Check expiry dates regularly to avoid losing coupon benefits",
            "The 6-benefit redemption system offers diverse ways to use your coupons",
            "Some redemptions require staff approval - allow processing time"
        ],
        "common_mistakes": [
            "Letting coupons expire without using them",
            "Not understanding all 6 benefit categories available"
        ]
    },

    "user_points_utilisation": {
        "purpose": "Track your MNR Points balance, utilization history, and expiry timeline. MNR Points are allocated upon activation and can be used for various benefits. Points expire in 24 months.",
        "who_can_access": "All Active MNR Members",
        "main_sections": [
            {"name": "Points Balance", "description": "Current MNR Points balance and allocation breakdown"},
            {"name": "Utilization History", "description": "How you've used your points so far"},
            {"name": "Expiry Timeline", "description": "When your points expire (24-month validity)"}
        ],
        "usage_flow": [
            "Open Points Utilisation from your member dashboard",
            "View your current points balance",
            "Check the expiry timeline for upcoming expirations",
            "Review utilization history for past usage",
            "Plan point usage before expiry"
        ],
        "fields": [
            {"name": "Total Allocated", "description": "Points given upon activation (Platinum: 30K, Diamond: 15K, Star: 2K)"},
            {"name": "Used", "description": "Points already utilized"},
            {"name": "Available", "description": "Points remaining for use"},
            {"name": "Expiry Date", "description": "24 months from activation date"},
            {"name": "Receipt Number", "description": "Unique receipt generated for each point utilization"}
        ],
        "statuses": [],
        "tips": [
            "Points expire in 24 months from activation - plan usage accordingly",
            "Platinum gets 30K points, Diamond 15K, Star 2K",
            "Each utilization generates a unique receipt number for tracking"
        ],
        "common_mistakes": [
            "Letting points expire without utilization",
            "Not tracking the 24-month expiry deadline"
        ]
    },

    "user_zynova_real_estate": {
        "purpose": "Access the VGK4U Real Dreams real estate marketplace. Browse property listings, express interest in properties, and manage your real estate leads through the platform.",
        "who_can_access": "All MNR Members",
        "main_sections": [
            {"name": "Property Listings", "description": "Browse available properties with photos, details, and pricing"},
            {"name": "My Interests", "description": "Properties you've expressed interest in"},
            {"name": "Deals", "description": "Active deals and negotiations in progress"}
        ],
        "usage_flow": [
            "Open VGK Real Dreams from your member dashboard",
            "Browse available property listings",
            "Filter by location, price range, property type",
            "Express interest in a property to initiate contact",
            "Track your interests and active deals"
        ],
        "fields": [
            {"name": "Property Type", "description": "Residential, Commercial, Plot, etc."},
            {"name": "Location", "description": "Property location details"},
            {"name": "Price", "description": "Listed price or price range"},
            {"name": "Status", "description": "Available, Under Negotiation, Sold"}
        ],
        "statuses": [
            {"status": "Available", "color": "#059669", "meaning": "Property is open for interest"},
            {"status": "Under Negotiation", "color": "#f59e0b", "meaning": "Active deal discussions ongoing"},
            {"status": "Sold", "color": "#6b7280", "meaning": "Property has been sold"}
        ],
        "tips": [
            "Express interest early for high-demand properties",
            "Real Dreams operates with company-wise data segregation"
        ],
        "common_mistakes": [
            "Not following up on expressed interests",
            "Missing property details in the listing before expressing interest"
        ]
    },

    "user_zynova_insurance": {
        "purpose": "Access VGK Care insurance services. View available insurance products, manage your policies, and earn referral commissions on insurance purchases through the VGK4U insurance program.",
        "who_can_access": "All MNR Members",
        "main_sections": [
            {"name": "Insurance Products", "description": "Available insurance plans and their benefits"},
            {"name": "My Policies", "description": "Your active insurance policies"},
            {"name": "Referral Commissions", "description": "Commissions earned from insurance referrals"}
        ],
        "usage_flow": [
            "Open VGK Care from your member dashboard",
            "Browse available insurance products",
            "Select a product to view detailed benefits and pricing",
            "Apply for a policy through the platform",
            "Track your policies and referral commissions"
        ],
        "fields": [
            {"name": "Plan Name", "description": "Name of the insurance plan"},
            {"name": "Premium", "description": "Cost of the insurance policy"},
            {"name": "Coverage", "description": "What the policy covers"},
            {"name": "Referral Commission", "description": "Commission earned for referring someone to this plan"}
        ],
        "statuses": [
            {"status": "Active", "color": "#059669", "meaning": "Policy is active and coverage is in effect"},
            {"status": "Pending", "color": "#f59e0b", "meaning": "Application submitted, awaiting processing"},
            {"status": "Expired", "color": "#6b7280", "meaning": "Policy term has ended"}
        ],
        "tips": [
            "Insurance referrals can generate additional income through commissions",
            "Review policy terms carefully before applying"
        ],
        "common_mistakes": [
            "Not understanding the difference between personal policy and referral commission",
            "Missing policy renewal deadlines"
        ]
    },

    "user_zynova_training": {
        "purpose": "Access the EVolution Training Center (ETC) for educational resources, training courses, and certification programs related to EV technology and business development.",
        "who_can_access": "All MNR Members",
        "main_sections": [
            {"name": "Available Courses", "description": "Training programs and courses available through ETC"},
            {"name": "My Enrollments", "description": "Courses you're enrolled in or have completed"},
            {"name": "Certifications", "description": "Certificates earned from completed training"}
        ],
        "usage_flow": [
            "Open EVolution Training Center from your member dashboard",
            "Browse available training courses",
            "Enroll in courses relevant to your development",
            "Complete training modules and assessments",
            "Download certificates upon completion"
        ],
        "fields": [
            {"name": "Course Name", "description": "Title of the training program"},
            {"name": "Duration", "description": "Expected time to complete the course"},
            {"name": "Status", "description": "Not Started, In Progress, Completed"},
            {"name": "Certificate", "description": "Available upon successful completion"}
        ],
        "statuses": [
            {"status": "Available", "color": "#3b82f6", "meaning": "Course open for enrollment"},
            {"status": "In Progress", "color": "#f59e0b", "meaning": "Currently enrolled and studying"},
            {"status": "Completed", "color": "#059669", "meaning": "Course finished, certificate available"}
        ],
        "tips": [
            "Complete EV training courses to enhance your business knowledge",
            "Certificates can be shared to build credibility with prospects"
        ],
        "common_mistakes": [
            "Not completing enrolled courses",
            "Not downloading certificates after completion"
        ]
    },

    "user_franchise_purchases": {
        "purpose": "Track your franchise earnings and purchase transactions within the MNR franchise network. View commissions from franchise referrals and product purchases.",
        "who_can_access": "Eligible MNR Members with franchise participation",
        "main_sections": [
            {"name": "Franchise Earnings", "description": "Commissions from franchise-related activities"},
            {"name": "Purchase History", "description": "Record of franchise product purchases"},
            {"name": "Referral Tracking", "description": "Track franchise referrals and their status"}
        ],
        "usage_flow": [
            "Open Franchise Earnings from your member dashboard",
            "View your franchise commission earnings",
            "Check purchase history for franchise products",
            "Track franchise referral status and commissions"
        ],
        "fields": [
            {"name": "Transaction Type", "description": "Purchase, Commission, or Referral Bonus"},
            {"name": "Amount", "description": "Transaction amount"},
            {"name": "Date", "description": "Transaction date"},
            {"name": "Status", "description": "Transaction status"}
        ],
        "statuses": [],
        "tips": [
            "Franchise commissions are separate from the main MNR income streams",
            "Track your referrals to maximize franchise earnings"
        ],
        "common_mistakes": [
            "Confusing franchise earnings with regular MNR income",
            "Not tracking franchise referral progress"
        ]
    },

    "user_field_allowances": {
        "purpose": "View and submit field allowance claims for field activities. Members can request allowances based on Group A (metro) or Group B (other) classification.",
        "who_can_access": "MNR Members eligible for field allowances",
        "main_sections": [
            {"name": "My Claims", "description": "Field allowance claims you've submitted"},
            {"name": "Submit Claim", "description": "Form to submit a new field allowance request"},
            {"name": "Rate Card", "description": "Current allowance rates for Group A and Group B"}
        ],
        "usage_flow": [
            "Open Field Allowances from your member dashboard",
            "Check current allowance rates for your group",
            "Submit a claim for field activity with required details",
            "Track claim status (Pending, Approved, Rejected)",
            "View approved claims and disbursement status"
        ],
        "fields": [
            {"name": "Activity Date", "description": "Date of the field activity"},
            {"name": "Location", "description": "Where the field activity took place"},
            {"name": "Group", "description": "A (metro/tier-1) or B (other) - determines rate"},
            {"name": "Amount", "description": "Calculated allowance based on group and activity"}
        ],
        "statuses": [
            {"status": "Pending", "color": "#f59e0b", "meaning": "Claim submitted, awaiting approval"},
            {"status": "Approved", "color": "#059669", "meaning": "Claim approved for disbursement"},
            {"status": "Rejected", "color": "#dc2626", "meaning": "Claim rejected with reason"}
        ],
        "tips": [
            "Submit claims promptly after field activities",
            "Ensure you select the correct group (A or B) for your location"
        ],
        "common_mistakes": [
            "Submitting claims for the wrong group classification",
            "Delayed submission reducing approval chances"
        ]
    },

    "earnings_direct_referral": {
        "purpose": "Detailed view of your Direct Facilitation (Direct Referral) income. See exactly which referrals generated income and how much you earned from each.",
        "who_can_access": "All Active MNR Members",
        "main_sections": [
            {"name": "Referral Income List", "description": "Each direct referral and the income generated from their activation"},
            {"name": "Income Summary", "description": "Total Direct Referral income earned to date"}
        ],
        "usage_flow": [
            "Open Direct Facilitation from the Earnings section",
            "View income from each direct referral",
            "Check which referrals have generated income vs those still inactive"
        ],
        "fields": [
            {"name": "Referral Name", "description": "Name of your direct referral"},
            {"name": "Package", "description": "Package they activated with"},
            {"name": "Income Amount", "description": "Income you earned from their activation"},
            {"name": "Credit Date", "description": "When the income was credited to your wallet"}
        ],
        "statuses": [],
        "tips": [
            "Income is generated only when referrals ACTIVATE (use a PIN), not just when they register",
            "Higher package activations generate higher direct referral income"
        ],
        "common_mistakes": [
            "Expecting income from inactive referrals - they must activate first"
        ]
    },

    "earnings_matching_referral": {
        "purpose": "Detailed view of your Group Performance Recognition (Matching Referral) income. Shows the Left-Right leg matching calculations that generated your binary pair income.",
        "who_can_access": "All Active MNR Members",
        "main_sections": [
            {"name": "Matching Calculations", "description": "Day-by-day matching calculations with Left/Right point details"},
            {"name": "Income Summary", "description": "Total Matching Referral income earned"}
        ],
        "usage_flow": [
            "Open Group Performance Recognition from the Earnings section",
            "View daily matching calculations",
            "Check Left vs Right leg point balances",
            "See carry-forward points from unmatched legs"
        ],
        "fields": [
            {"name": "Left Points", "description": "Points from your left binary tree leg"},
            {"name": "Right Points", "description": "Points from your right binary tree leg"},
            {"name": "Matched", "description": "Points paired (minimum of left and right)"},
            {"name": "Income", "description": "Income from matched points"},
            {"name": "Carry Forward", "description": "Excess points on the stronger side"}
        ],
        "statuses": [],
        "tips": [
            "Matching income is based on the WEAKER leg - balance both legs for maximum income",
            "Carry forward points accumulate until the other leg catches up"
        ],
        "common_mistakes": [
            "Building only one leg while neglecting the other",
            "Not understanding that matching uses the weaker leg's points"
        ]
    },

    "earnings_ved_income": {
        "purpose": "Detailed view of your VED Income - the multi-level ownership income triggered when you have 3 or more direct referrals. Your 3rd direct referral becomes your Ved Head.",
        "who_can_access": "MNR Members with 3+ direct referrals",
        "main_sections": [
            {"name": "Ved Structure", "description": "Your Ved ownership chain showing Ved Head and downstream members"},
            {"name": "Ved Income Details", "description": "Income generated from your Ved chain"}
        ],
        "usage_flow": [
            "Open VED Income from the Earnings section",
            "View your Ved structure (only visible after getting 3rd direct referral)",
            "See who your Ved Head is (your 3rd direct referral)",
            "Track income from the Ved chain"
        ],
        "fields": [
            {"name": "Ved Head", "description": "Your 3rd direct referral who heads your Ved team"},
            {"name": "Ved Team Size", "description": "Number of members in your Ved chain"},
            {"name": "Ved Income", "description": "Total income earned from Ved ownership"},
            {"name": "No Cascading", "description": "Downstream Ved Owners disconnect from your Ved team"}
        ],
        "statuses": [],
        "tips": [
            "You become a Ved Owner when you get your 3rd direct referral",
            "The 'No Cascading' rule means: when someone in your Ved team gets their own 3rd referral, they form their own Ved team and their downstream leaves yours",
            "Focus on getting quality 3rd referrals who will build active networks"
        ],
        "common_mistakes": [
            "Not understanding the 'No Cascading' rule - it naturally reduces your Ved team size as members grow",
            "Confusing Ved Income with matching referral - they are completely different calculations"
        ]
    },

    "earnings_guru_dakshina": {
        "purpose": "Detailed breakdown of your Guru Dakshina contributions - the mandatory 2% deduction from all gross earnings that goes towards the system's sustainability fund.",
        "who_can_access": "All Active MNR Members",
        "main_sections": [
            {"name": "Contribution Summary", "description": "Total Guru Dakshina contributed to date"},
            {"name": "Daily Breakdown", "description": "Day-wise deduction details showing gross income and 2% calculation"}
        ],
        "usage_flow": [
            "Open Guru Dakshina Income from the Earnings section",
            "View your total lifetime Guru Dakshina contributions",
            "Check daily breakdowns to verify the 2% calculation",
            "Cross-reference with your daywise income page"
        ],
        "fields": [
            {"name": "Date", "description": "Deduction date"},
            {"name": "Gross Income", "description": "Your income before deduction"},
            {"name": "Guru Dakshina (2%)", "description": "Deducted amount"},
            {"name": "Net Income", "description": "Income after deduction"}
        ],
        "statuses": [],
        "tips": [
            "Guru Dakshina is a fixed 2% - it applies to all income types equally",
            "This is different from TDS which is deducted at withdrawal, not at earning"
        ],
        "common_mistakes": [
            "Confusing Guru Dakshina (2% at earning) with TDS (2% at withdrawal) - both are 2% but applied at different stages"
        ]
    },

    "user_my_leads": {
        "purpose": "Manage your personal leads within the CRM system. Track prospects, follow up on opportunities, and convert leads into active MNR members.",
        "who_can_access": "All MNR Members",
        "main_sections": [
            {"name": "My Leads List", "description": "All leads you've created or been assigned"},
            {"name": "Lead Pipeline", "description": "Visual pipeline showing leads at different stages"},
            {"name": "Follow-up Tasks", "description": "Upcoming follow-up actions for your leads"}
        ],
        "usage_flow": [
            "Open My Leads from your member dashboard",
            "View your active leads and their stages",
            "Add new leads from your contacts",
            "Log follow-up activities and notes",
            "Move leads through the pipeline as they progress"
        ],
        "fields": [
            {"name": "Lead Name", "description": "Name of the prospect"},
            {"name": "Contact", "description": "Phone number or email"},
            {"name": "Stage", "description": "Current position in the lead pipeline"},
            {"name": "Last Activity", "description": "Date of the most recent follow-up"},
            {"name": "Next Follow-up", "description": "Scheduled next follow-up date"}
        ],
        "statuses": [
            {"status": "New", "color": "#3b82f6", "meaning": "Fresh lead, not yet contacted"},
            {"status": "Contacted", "color": "#f59e0b", "meaning": "Initial contact made"},
            {"status": "Interested", "color": "#8b5cf6", "meaning": "Prospect showed interest"},
            {"status": "Converted", "color": "#059669", "meaning": "Lead became an MNR member"},
            {"status": "Lost", "color": "#dc2626", "meaning": "Lead declined or went cold"}
        ],
        "tips": [
            "Follow up consistently - most conversions happen after 3-5 contacts",
            "Log every interaction to maintain a clear history",
            "Set realistic follow-up dates and honor them"
        ],
        "common_mistakes": [
            "Not following up on leads regularly",
            "Not logging interactions, losing context for future conversations"
        ]
    },

    "team_picture": {
        "purpose": "Visual gallery view of your network connections. See profile photos and visual representation of your team/downline in a gallery format.",
        "who_can_access": "All MNR Members",
        "main_sections": [
            {"name": "Connections Gallery", "description": "Visual grid of team member photos with basic details"}
        ],
        "usage_flow": [
            "Open Connections Gallery from your member dashboard",
            "Browse team member photos in gallery view",
            "Click on a photo to see member details"
        ],
        "fields": [
            {"name": "Photo", "description": "Member's profile photo"},
            {"name": "Name", "description": "Member's full name"},
            {"name": "MNR ID", "description": "Member's unique identifier"},
            {"name": "Package", "description": "Member's activation package"}
        ],
        "statuses": [],
        "tips": [
            "Use the gallery to familiarize yourself with your team members",
            "Members without profile photos show a default avatar"
        ],
        "common_mistakes": []
    },

    "profile_view": {
        "purpose": "View and manage your member profile including personal information, KYC documents, and bank details. This is the central place to maintain your account information.",
        "who_can_access": "All MNR Members",
        "main_sections": [
            {"name": "Personal Information", "description": "Name, phone, email, DOB, and address"},
            {"name": "KYC Documents", "description": "Upload and view Aadhaar (front/back), PAN Card, and Passport Photo"},
            {"name": "Bank Details", "description": "Bank account information for withdrawal payouts"},
            {"name": "Profile Photo", "description": "Upload and manage your profile picture"}
        ],
        "usage_flow": [
            "Open your profile from the member dashboard",
            "Review your personal information for accuracy",
            "Upload KYC documents (Aadhaar Front, Aadhaar Back, PAN Card, Passport Photo)",
            "Submit bank details (Account Number, IFSC, Holder Name)",
            "Wait for staff to validate and approve your KYC and Bank details",
            "Once both are approved, your Earning wallet funds become Withdrawable"
        ],
        "fields": [
            {"name": "Full Name", "description": "Your registered name as per documents"},
            {"name": "Phone Number", "description": "Registered mobile number"},
            {"name": "Aadhaar Front/Back", "description": "Government ID front and back images"},
            {"name": "PAN Card", "description": "Income tax PAN card image"},
            {"name": "Passport Photo", "description": "Recent passport-size photograph"},
            {"name": "Account Number", "description": "Bank account number for payouts"},
            {"name": "IFSC Code", "description": "Bank branch IFSC for transfers"},
            {"name": "Account Holder", "description": "Name on the bank account"}
        ],
        "statuses": [
            {"status": "Pending", "color": "#f59e0b", "meaning": "Documents submitted, awaiting validation"},
            {"status": "Validated", "color": "#3b82f6", "meaning": "First check passed, awaiting final approval"},
            {"status": "Approved", "color": "#059669", "meaning": "Documents verified and approved"},
            {"status": "Rejected", "color": "#dc2626", "meaning": "Documents rejected - check reason and resubmit"}
        ],
        "tips": [
            "Complete KYC and Bank details early - they're required for withdrawals",
            "Ensure your bank account holder name matches your registered name exactly",
            "Upload clear, readable images of all documents",
            "Both KYC AND Bank must be approved before withdrawals can be processed"
        ],
        "common_mistakes": [
            "Uploading blurry or unclear document images",
            "Bank holder name not matching registered name",
            "Expecting withdrawals before both KYC and Bank are approved"
        ]
    },
}
