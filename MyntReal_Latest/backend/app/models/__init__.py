"""
Models package for FastAPI Backend
Preserves exact Flask app database schema
"""

# Import all models to ensure they are registered with SQLAlchemy
from app.models.base import Base, BaseModel, TimestampMixin, AuditMixin, get_indian_time
from app.models.user import User
from app.models.placement import Placement, PlacementRequest, PlacementLog
from app.models.transaction import Transaction, CompanyEarnings, VedIncome, DailyCostCalculation, TDSPayable, PendingIncome
from app.models.ved_team import VedTeamMember
from app.models.coupon import Coupon, EnhancedCoupon, CouponActivationTracker, PINPurchaseRequest
from app.models.coupon_transfer import CouponTransfer
from app.models.awards import DirectAwardTier, UserAwardProgress, MatchingAwardTier, UserMatchingAwardProgress, AwardAuditLog
from app.models.award_price_change import AwardPriceChangeRequest
from app.models.bonanza import DynamicBonanza, DynamicBonanzaReward, DynamicBonanzaHistory, Bonanza, BonanzaBrandFilter  # DC Protocol: BonanzaProgress deprecated
from app.models.field_allowance import FieldAllowanceEligibility, FieldAllowanceProgress, AllowanceSchemeSelector, AllowanceTierDefinition
from app.models.system_control import SystemControl, AppSettings, CustomRole, TermsAndConditionsVersion
from app.models.system import SystemCheckpoint
from app.models.user_leg_metrics import UserLegMetrics
from app.models.kyc_document import KYCDocument, BankDetailsApproval
from app.models.kyc_blocking_log import KYCBlockingLog, WalletSyncLog
from app.models.banner import (
    Banner, CustomBanner, BannerSkippedUser, PopupMessage,
    UserCouponAcceptance, EmailTemplate, BirthdayMessage, BirthdaySkippedUser,
    BannerMetrics, BannerEventLog
)
from app.models.super_admin_session import SuperAdminSession
from app.models.withdrawal import WithdrawalRequest, BulkWithdrawalBatch
from app.models.ev_model import EVModel
from app.models.ev_coupon_claim import EVCouponClaim
from app.models.training_course import TrainingCourse
from app.models.training_claim import TrainingClaim
from app.models.feedback import FeedbackCategory, FeedbackSubmission, FeedbackMedia, FeedbackApproval, SubmissionType, SubmissionStatus, ApprovalAction, AnnouncementRating
# Compliance tracking removed - following DC Protocol: query from source tables directly (pending_income, company_earnings)

# Expense Category Models (DC Protocol Compliant - Required for Staff Accounts)
from app.models.expense_category import ExpenseMainCategory, ExpenseSubCategory

# Staff System Models (DC Protocol Compliant)
from app.models.staff import StaffRole, StaffDepartment, StaffEmployee, StaffSetting, StaffAuditLog, log_staff_audit

# Staff Task Management Models (DC Protocol Compliant)
from app.models.staff_tasks import (
    StaffTask, StaffTaskAssignee, StaffTaskComment, 
    StaffTaskActivityLog, StaffTaskTimeEntry, StaffTaskPhase,
    generate_task_code, log_task_activity
)

# Staff Attendance & Time Tracker Models (DC Protocol Compliant)
from app.models.staff_attendance import (
    StaffAttendance, StaffAttendanceBreak, StaffAttendanceLog,
    StaffBreakType, StaffAttendanceEvidence, StaffLocationDriftEvent,
    StaffActivityTimeLog,
    DEFAULT_BREAK_TYPES, generate_drift_dc_code, log_attendance_activity
)

# Staff KRA Performance Management Models (DC Protocol Compliant)
from app.models.staff_kra import (
    StaffKRATemplate, StaffKRAAssignment, StaffKRADailyInstance,
    StaffKRAPerformanceSummary, StaffKRAAuditLog, StaffConfigurableStatus
)

# Staff Journey Tracking Models (DC Protocol Compliant)
from app.models.staff_journey import (
    StaffJourney, StaffJourneyTrackPoint, StaffJourneyApproval,
    JourneyStatus, JourneyApprovalStatus, JourneyPurpose
)

# Staff Timesheet Entry Models (DC Protocol Compliant)
from app.models.staff_timesheet import (
    StaffTimesheetEntry, StaffTimesheetApprovalHistory,
    log_timesheet_activity, compute_attendance_status,
    ATTENDANCE_RULES, generate_timesheet_audit_id
)

# Staff Attendance Sheet Models (DC Protocol Compliant - Bulk Marking)
from app.models.staff_attendance_sheet import (
    StaffAttendanceSheet, StaffAttendanceSheetAudit,
    AttendanceStatus, ApprovalStatus, ReconciliationStatus,
    StaffAttendanceException, ExceptionBypassType,
    # Leave Management System (Jan 2026)
    StaffLeaveType, StaffLeaveBalance, StaffLeaveRequest,
    StaffLeaveRequestDay, StaffLeaveApproval,
    LeaveRequestStatus, HalfDayType
)

# Staff Financial Management System Models (DC Protocol Compliant - Dec 06, 2025)
from app.models.staff_accounts import (
    AssociatedCompany, CompanySegment, VendorMaster, StockItemMaster, StockItemImage,
    PricingConfiguration, IncomeSourceType, IncomeEntry,
    VendorTransactionHeader, VendorTransactionLineItem, ServiceItemsUsed,
    VendorReturn, StockLedger, StockTransfer, InterCompanyMarginConfig,
    PartyLedger, EmployeeFundLedger, EmployeeFundTransfer, EmployeeIncentive,
    PaymentReceipt, GeneratedInvoice, InvoiceLineItem,
    BalanceSheetSummary, ApprovalConfiguration, ApprovalHistory,
    FundAllocation, ExpenseEntry,
    BOMMaster, BOMLineItem, ManufacturingOrder, ManufacturingOrderLine,
    StaffReimbursementClaim, StaffReimbursementClaimItem,
    # Stock Validation Models (DC Protocol Compliant - Jan 2026)
    StockValidationSession, StockValidationEntry, StockValidationAuditLog,
    # Purchase Intake & Lifecycle Tracking Models (DC Protocol Compliant - Jan 2026)
    PurchaseIntakeBatch, PurchaseIntakeItem, InventoryLifecycleEvent,
    VendorReturnRequest, VendorReturnItem,
    ServiceCenterReceipt, ServiceCenterDispatch,
    # VGK Team Models (DC Protocol Mar 2026)
    VGKTeamCommissionConfig, VGKTeamIncomeEntry, VGKPINPurchaseRequest
)
from app.models.vgk_cash_income import VGKCashIncomeEntry
from app.models.vgk_incentive_brands import VGKIncentiveBrand
from app.models.vgk_wallet_transaction import VGKWalletTransaction
from app.models.vgk_vendor import (
    VGKVendorCategory, VGKVendor, VGKVendorKYC, VGKVendorAgreement,
    VGKVendorProductCategory, VGKVendorLogin, VGKVendorTransaction,
    VGKVendorMarketplaceProduct
)

# Real Dreams - Real Estate Marketplace Models (DC Protocol Compliant - Dec 08, 2025)
from app.models.real_dreams import (
    RDCompanyConfig, RDPropertyType, RDAmenity, RDBannerConfig,
    RDPartnerProfile, RDProperty, RDPropertyAmenity,
    RDLead, RDLeadFollowup, RDDeal
)

# Signup Categories - Configurable business categories (DC Protocol Compliant - Dec 08, 2025)
from app.models.signup_category import (
    SignupCategory, DEFAULT_SIGNUP_CATEGORIES
)

# Universal Engagement System - Ratings, Comments, Shares, Saves (DC Protocol Compliant - Dec 08, 2025)
from app.models.universal_engagement import (
    UniversalRating, UniversalComment, UniversalShare, UniversalSave
)

# MyntReal & Zynova Incentive System (DC Protocol Compliant - Dec 28, 2025)
from app.models.myntreal_incentive import (
    MNRPointsBalance, MNRPointsTransaction, MyntRealIncentive,
    ZynovaMember, ZynovaIncentive, MyntRealIncentiveRate,
    PointsTransactionType, IncentiveCalculationMode, IncentiveStatus, ZynovaRole,
    DEFAULT_INCENTIVE_RATES, ZYNOVA_PROMOTION_TARGETS
)

# Member Lifecycle Tracker (DC Protocol Compliant - Feb 17, 2026)
from app.models.member_lifecycle import MemberLifecycleTracker
from app.models.solar import CRMSolarLeadTech

# MNR E-Com Lite — Marketplace (DC Protocol - Feb 2026)
from app.models.marketplace import MarketspareItem, MarketplaceSyncLog, MarketplaceCategoryConfig

# Staff Payroll System Models (DC Protocol Compliant - Jan 07, 2026)
from app.models.staff_payroll import (
    StaffPayrollProfile, StaffPayrollStatutoryConfig, StaffPayrollCycle,
    StaffPayrollRun, StaffPayrollDeduction, StaffConsultantInvoice,
    StaffPayrollDocument, StaffPayrollAuditLog, StaffPayrollAllowanceCatalog,
    EmploymentType, TaxRegime, PayrollCycleStatus, PayrollRunStatus,
    PaymentStatus, ConsultantInvoiceStatus, ConsultantInvoiceSource,
    PayrollDocumentType, DeductionType, StatutoryConfigType,
    generate_payroll_cycle_code, generate_payroll_run_code,
    generate_consultant_invoice_number, generate_payroll_document_code,
    TDS_SLABS_NEW_REGIME, TDS_SLABS_OLD_REGIME, DEFAULT_STATUTORY_CONFIG
)

# Export all models for easy import
__all__ = [
    # Base models
    "Base",
    "BaseModel", 
    "TimestampMixin",
    "AuditMixin",
    "get_indian_time",
    
    # Core models
    "User",
    "Placement",
    "PlacementRequest", 
    "PlacementLog",
    "Transaction",
    "CompanyEarnings",
    "VedIncome",
    "DailyCostCalculation",
    "TDSPayable",
    "PendingIncome",
    "VedTeamMember",
    
    # Coupon system models
    "Coupon",
    "EnhancedCoupon",
    "CouponActivationTracker",
    "PINPurchaseRequest",
    "CouponTransfer",
    
    # Award system models
    "DirectAwardTier",
    "UserAwardProgress",
    "MatchingAwardTier",
    "UserMatchingAwardProgress",
    "AwardAuditLog",
    "AwardPriceChangeRequest",
    
    # Bonanza system models (DC Protocol: BonanzaProgress deprecated)
    "DynamicBonanza",
    "DynamicBonanzaReward",
    "DynamicBonanzaHistory",
    
    # Field allowance system models
    "FieldAllowanceEligibility",
    "FieldAllowanceProgress",
    "AllowanceSchemeSelector",
    "AllowanceTierDefinition",
    
    # RVZ ID system control models
    "SystemControl",
    "AppSettings",
    "CustomRole",
    "TermsAndConditionsVersion",
    
    # System configuration models
    "SystemCheckpoint",
    
    # Performance optimization models
    "UserLegMetrics",
    
    # KYC & Bank approval models
    "KYCDocument",
    "BankDetailsApproval",
    "KYCBlockingLog",
    "WalletSyncLog",
    
    # Banner & Communication system models
    "Banner",
    "CustomBanner",
    "BannerSkippedUser",
    "PopupMessage",
    "UserCouponAcceptance",
    "EmailTemplate",
    "BirthdayMessage",
    "BirthdaySkippedUser",
    "BannerMetrics",
    "BannerEventLog",
    
    # Security models
    "SuperAdminSession",
    
    # Withdrawal & Payout models
    "WithdrawalRequest",
    "BulkWithdrawalBatch",
    
    # EV Coupon Claim System models
    "EVModel",
    "EVCouponClaim",
    
    # Training Course Claim System models
    "TrainingCourse",
    "TrainingClaim",
    
    # User Feedback & Announcements System models (DC Protocol: approved submissions = announcements)
    "FeedbackCategory",
    "FeedbackSubmission",
    "FeedbackMedia",
    "FeedbackApproval",
    "SubmissionType",
    "SubmissionStatus",
    "ApprovalAction",
    
    # Expense Category models (DC Protocol Compliant - Required for Staff Accounts)
    "ExpenseMainCategory",
    "ExpenseSubCategory",
    
    # Staff System models (DC Protocol Compliant)
    "StaffRole",
    "StaffDepartment",
    "StaffEmployee",
    "StaffSetting",
    "StaffAuditLog",
    "log_staff_audit",
    
    # Staff Task Management models (DC Protocol Compliant)
    "StaffTask",
    "StaffTaskAssignee",
    "StaffTaskComment",
    "StaffTaskActivityLog",
    "StaffTaskTimeEntry",
    "generate_task_code",
    "log_task_activity",
    
    # Staff Attendance & Time Tracker models (DC Protocol Compliant)
    "StaffAttendance",
    "StaffAttendanceBreak",
    "StaffAttendanceLog",
    "StaffActivityTimeLog",
    "StaffBreakType",
    "StaffAttendanceEvidence",
    "StaffLocationDriftEvent",
    "DEFAULT_BREAK_TYPES",
    "generate_drift_dc_code",
    "log_attendance_activity",
    
    # Staff KRA Performance Management models (DC Protocol Compliant)
    "StaffKRATemplate",
    "StaffKRAAssignment",
    "StaffKRADailyInstance",
    "StaffKRAPerformanceSummary",
    "StaffKRAAuditLog",
    
    # Staff Journey Tracking models (DC Protocol Compliant)
    "StaffJourney",
    "StaffJourneyTrackPoint",
    "StaffJourneyApproval",
    "JourneyStatus",
    "JourneyApprovalStatus",
    "JourneyPurpose",
    
    # Staff Timesheet Entry models (DC Protocol Compliant)
    "StaffTimesheetEntry",
    "StaffTimesheetApprovalHistory",
    "log_timesheet_activity",
    "compute_attendance_status",
    "ATTENDANCE_RULES",
    "generate_timesheet_audit_id",
    
    # Staff Attendance Sheet models (DC Protocol Compliant - Bulk Marking)
    "StaffAttendanceSheet",
    "StaffAttendanceSheetAudit",
    "AttendanceStatus",
    "ApprovalStatus",
    "ReconciliationStatus",
    
    # Staff Financial Management System models (DC Protocol Compliant - Dec 06, 2025)
    "AssociatedCompany",
    "CompanySegment",
    "VendorMaster",
    "StockItemMaster",
    "StockItemImage",
    "PricingConfiguration",
    "IncomeSourceType",
    "IncomeEntry",
    "VendorTransactionHeader",
    "VendorTransactionLineItem",
    "ServiceItemsUsed",
    "VendorReturn",
    "StockLedger",
    "StockTransfer",
    "InterCompanyMarginConfig",
    "PartyLedger",
    "EmployeeFundLedger",
    "EmployeeFundTransfer",
    "EmployeeIncentive",
    "PaymentReceipt",
    "GeneratedInvoice",
    "InvoiceLineItem",
    "BalanceSheetSummary",
    "ApprovalConfiguration",
    "ApprovalHistory",
    "FundAllocation",
    "ExpenseEntry",
    
    # BOM and Manufacturing models (DC_BOM_001 - Dec 06, 2025)
    "BOMMaster",
    "BOMLineItem",
    "ManufacturingOrder",
    "ManufacturingOrderLine",
    
    # Stock Validation models (DC Protocol Compliant - Jan 2026)
    "StockValidationSession",
    "StockValidationEntry",
    "StockValidationAuditLog",
    
    # Purchase Intake & Lifecycle Tracking models (DC Protocol Compliant - Jan 2026)
    "PurchaseIntakeBatch",
    "PurchaseIntakeItem",
    "InventoryLifecycleEvent",
    "VendorReturnRequest",
    "VendorReturnItem",
    "ServiceCenterReceipt",
    "ServiceCenterDispatch",
    
    # Real Dreams - Real Estate Marketplace models (DC Protocol Compliant - Dec 08, 2025)
    "RDCompanyConfig",
    "RDPropertyType",
    "RDAmenity",
    "RDBannerConfig",
    "RDPartnerProfile",
    "RDProperty",
    "RDPropertyAmenity",
    "RDLead",
    "RDLeadFollowup",
    "RDDeal",
    
    # Signup Categories (DC Protocol Compliant - Dec 08, 2025)
    "SignupCategory",
    "DEFAULT_SIGNUP_CATEGORIES",
    
    # Universal Engagement System (DC Protocol Compliant - Dec 08, 2025)
    "UniversalRating",
    "UniversalComment",
    "UniversalShare",
    "UniversalSave",
    
    # MyntReal & Zynova Incentive System (DC Protocol Compliant - Dec 28, 2025)
    "MNRPointsBalance",
    "MNRPointsTransaction",
    "MyntRealIncentive",
    "ZynovaMember",
    "ZynovaIncentive",
    "MyntRealIncentiveRate",
    "PointsTransactionType",
    "IncentiveCalculationMode",
    "IncentiveStatus",
    "ZynovaRole",
    "DEFAULT_INCENTIVE_RATES",
    "ZYNOVA_PROMOTION_TARGETS",
    
    # Staff Payroll System (DC Protocol Compliant - Jan 07, 2026)
    "StaffPayrollProfile",
    "StaffPayrollStatutoryConfig",
    "StaffPayrollCycle",
    "StaffPayrollRun",
    "StaffPayrollDeduction",
    "StaffConsultantInvoice",
    "StaffPayrollDocument",
    "StaffPayrollAuditLog",
    "EmploymentType",
    "TaxRegime",
    "PayrollCycleStatus",
    "PayrollRunStatus",
    "PaymentStatus",
    "ConsultantInvoiceStatus",
    "ConsultantInvoiceSource",
    "PayrollDocumentType",
    "DeductionType",
    "StatutoryConfigType",
    "generate_payroll_cycle_code",
    "generate_payroll_run_code",
    "generate_consultant_invoice_number",
    "generate_payroll_document_code",
    "TDS_SLABS_NEW_REGIME",
    "TDS_SLABS_OLD_REGIME",
    "DEFAULT_STATUTORY_CONFIG",
    "MemberLifecycleTracker",
    "CRMSolarLeadTech",
]