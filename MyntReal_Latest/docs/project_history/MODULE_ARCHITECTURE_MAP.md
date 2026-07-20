# BeV 2.0 Reference Program - Complete Module Architecture Map

## DC Protocol Compliance
**Single Source of Truth**: This document maps ALL modules, their backend endpoints, frontend pages, database models, and service layers. Use this as the authoritative reference for understanding system architecture before restructuring.

---

## 1. AUTHENTICATION & USER MANAGEMENT MODULE

### Backend Endpoints
- `backend/app/api/v1/endpoints/auth.py`
  - `/login` - User authentication with JWT
  - `/public/terms-and-conditions` - T&C retrieval
  - `/refresh` - Token refresh

- `backend/app/api/v1/endpoints/user_management_comprehensive.py`
  - `/{user_id}/basic-info` - User lookup
  - `/register` - User registration
  - `/profile` - Profile management
  - `/password/change` - Password updates
  - `/lock-account`, `/unlock-account` - Account status

- `backend/app/api/v1/endpoints/password_reset.py`
  - `/forgot-password` - WhatsApp OTP flow
  - `/verify-reset-code` - OTP verification

- `backend/app/api/v1/endpoints/profile.py`
  - `/profile` - User profile CRUD
  - `/kyc-documents` - KYC uploads
  - `/bank-details` - Bank info submission

### Frontend Pages
- `frontend/login.html` (standalone)
- `frontend/user_change_password.html`
- Frontend templates: `user.js`, `admin.js`, `superadmin.js`, `finance.js`, `vgk.js`

### Database Models
- `User` (`backend/app/models/user.py`)
- `SuperAdminSession` (`backend/app/models/super_admin_session.py`)
- `CustomRole` (`backend/app/models/system_control.py`)

### Services
- `SecurityManager` (`backend/app/core/security.py`)
- `UserService` (`backend/app/services/user_service.py`)

---

## 2. TEAM & BINARY TREE MODULE

### Backend Endpoints
- `backend/app/api/v1/endpoints/team_management.py`
  - `/user/{user_id}/binary-tree` - Tree visualization
  - `/user/{user_id}/team-stats` - Team metrics
  - `/admin/placement/manual` - Manual placement

### Frontend Pages
- `frontend/admin_members_picture.html` - Visual tree view
- `frontend/user_direct_referral.html` - Direct team
- `frontend/user_matching_referral.html` - Binary team

### Database Models
- `Placement` (`backend/app/models/placement.py`)
- `PlacementRequest`, `PlacementLog`
- `UserLegMetrics` (`backend/app/models/user_leg_metrics.py`) - Cached metrics

### Services
- `ReferenceService` (`backend/app/services/reference_service.py`)
- `LegMetricsCacheService` (`backend/app/services/leg_metrics_cache_service.py`)

---

## 3. INCOME CALCULATION MODULE

### Backend Endpoints
- `backend/app/api/v1/endpoints/income_verification.py`
  - `/admin/pending-incomes` - Admin income approval
  - `/super-admin/pending-incomes` - Super Admin verification
  - `/finance-admin/verified-incomes` - Finance payment queue
  - `/finance-admin/transfer-queue` - Transfer queue management

### Frontend Pages
- `frontend/admin_income_pending.html` - Admin income approval
- `frontend/admin_income_verified.html` - Super Admin & Finance workflows
- `frontend/admin_earnings_summary_new.html` - Income overview
- `frontend/admin_earnings_direct.html` - Direct referral income
- `frontend/admin_earnings_matching.html` - Matching income
- `frontend/admin_earnings_ved.html` - Ved income
- `frontend/admin_earnings_gurudakshina.html` - Guru Dakshina
- `frontend/admin_earnings_field_allowance.html` - Field allowances
- `frontend/user_daywise_income.html` - User income view

### Database Models
- `PendingIncome` (`backend/app/models/transaction.py`) - **Single source of truth for earnings**
- `Transaction` - Payment history
- `VedIncome` - Ved Team earnings
- `CompanyEarnings` - Company revenue tracking

### Services
- `IncomeCalculationService` (`backend/app/services/income_calculation_service.py`)
- `WalletService` (`backend/app/services/wallet_service.py`)

---

## 4. WITHDRAWAL & PAYMENT MODULE

### Backend Endpoints
- `backend/app/api/v1/endpoints/withdrawal.py`
  - `/user/withdrawal-request` - User withdrawal submission
  - `/admin/withdrawal-report` - Admin withdrawal queue
  - `/admin/withdrawal-income-breakdown/{id}` - Date-wise breakdown (Transfer History modal)
  - `/admin/date-wise-income-breakdown` - Grouped daily breakdown (Income Verification pages)
  - `/finance/process-payment` - Finance payment processing

### Frontend Pages
- `frontend/user_withdrawals.html` - User withdrawal interface
- `frontend/admin_earnings_withdrawals.html` - Admin withdrawal management
- Transfer History embedded in Income Verification pages

### Database Models
- `WithdrawalRequest` (`backend/app/models/withdrawal.py`)
- `BulkWithdrawalBatch`
- `transfer_queue` (bridge table for WVV workflow)

### Services
- `WithdrawalService` (`backend/app/services/withdrawal_service.py`)
- `WalletService` (dual-wallet system with daily sync)

---

## 5. AWARDS & BONANZA MODULE

### Backend Endpoints
- `backend/app/api/v1/endpoints/award_management.py`
  - `/user/{user_id}/direct-awards` - Direct award progress
  - `/user/{user_id}/matching-awards` - Matching award progress
  - `/admin/awards/tiers` - Award tier configuration

- `backend/app/api/v1/endpoints/award_processing.py`
  - `/admin/awards/pending` - Admin approval queue
  - `/superadmin/awards/verify` - Super Admin verification
  - `/finance/awards/process` - Finance payment processing

- `backend/app/api/v1/endpoints/bonanza.py`
  - `/bonanza/active` - Active campaigns
  - `/bonanza/user-progress` - User bonanza progress

- `backend/app/api/v1/endpoints/award_price_management.py`
  - `/rvz/award-prices` - VGK price configuration

- `backend/app/api/v1/endpoints/finance_awards_procurement.py`
  - `/finance/awards/procurement` - Physical award procurement tracking

### Frontend Pages
- `frontend/admin_awards.html` - Award management dashboard
- `frontend/admin_awards_all.html` - All awards view
- `frontend/admin_awards_userwise.html` - User-wise progress
- `frontend/admin_awards_awardwise.html` - Award-wise analytics
- `frontend/admin_awards_bonanza.html` - Bonanza campaigns
- `frontend/admin_awards_simple.html` - Simplified view
- `frontend/admin_bonanza_claims.html` - Bonanza claim management
- `frontend/super_admin_awards_approval.html` - Super Admin approval
- `frontend/finance_awards_payment_processing.html` - Finance procurement
- `frontend/vgk_awards_oversight.html` - VGK supreme oversight

### Database Models
- `DirectAwardTier`, `MatchingAwardTier` (`backend/app/models/awards.py`)
- `UserAwardProgress`, `UserMatchingAwardProgress`
- `DynamicBonanza` (`backend/app/models/bonanza.py`)
- `BonanzaProgress`, `DynamicBonanzaReward`
- `AwardAuditLog` - Audit trail
- `AwardPriceChangeRequest` - Price change tracking

### Services
- `AwardService` (`backend/app/services/award_service.py`)
- `AwardProcurementService` (physical award logistics)

---

## 6. COUPON & PIN MODULE

### Backend Endpoints
- `backend/app/api/v1/endpoints/admin_pins.py`
  - `/admin/pins/purchase-requests` - PIN purchase approval
  - `/admin/pins/assign` - PIN assignment
  - `/admin/pins/system-overview` - PIN inventory

- `backend/app/api/v1/endpoints/coupon_transfers.py`
  - `/coupons/transfer` - User-to-user transfer
  - `/admin/coupon-transfer` - Admin-initiated transfer
  - `/admin/coupon-transfers/pending` - Transfer approval queue

### Frontend Pages
- `frontend/admin_coupons_buy.html` - PIN purchase management
- `frontend/admin_coupons_activate.html` - Activation tracking
- `frontend/admin_coupons_transfer.html` - Transfer management
- `frontend/admin_coupons_status.html` - Coupon status overview
- `frontend/admin_coupons_progress.html` - Activation progress
- `frontend/finance_admin_pins.html` - Finance PIN overview

### Database Models
- `Coupon`, `EnhancedCoupon` (`backend/app/models/coupon.py`)
- `CouponActivationTracker` - Activation tracking
- `PINPurchaseRequest` - Purchase requests
- `CouponTransfer` (`backend/app/models/coupon_transfer.py`)

### Services
- `CouponService` (`backend/app/services/coupon_service.py`)

---

## 7. KYC & BANK APPROVAL MODULE

### Backend Endpoints
- `backend/app/api/v1/endpoints/bank_kyc_admin.py`
  - `/admin/kyc/pending` - KYC approval queue
  - `/admin/kyc/approve` - KYC approval
  - `/superadmin/bank-details/pending` - Bank details queue
  - `/superadmin/bank-details/approve` - Bank approval

### Frontend Pages
- `frontend/admin_kyc_management.html` - KYC document review
- `frontend/admin_bank_pending.html` - Pending bank approvals
- `frontend/admin_bank_all.html` - All bank details

### Database Models
- `KYCDocument` (`backend/app/models/kyc_document.py`)
- `BankDetailsApproval` - Bank approval workflow
- `KYCBlockingLog` (`backend/app/models/kyc_blocking_log.py`)
- `WalletSyncLog` - Real-time sync tracking

### Services
- `KYCService` (`backend/app/services/kyc_service.py`)
- `WalletService` (real-time sync on approval)

---

## 8. EV & TRAINING CLAIMS MODULE

### Backend Endpoints
- `backend/app/api/v1/endpoints/ev_scooter_claims.py`
  - `/ev/models` - EV model configuration
  - `/ev/claims` - EV coupon redemption
  - `/admin/ev/claims/pending` - EV claim approval

- `backend/app/api/v1/endpoints/training_claims.py`
  - `/training/courses` - Course configuration
  - `/training/claims` - Training claims
  - `/admin/training/claims/pending` - Claim approval

- `backend/app/api/v1/endpoints/ev_discount.py`
  - `/rvz/ev-benefits` - VGK EV analytics

### Frontend Pages
- `frontend/user_ev_benefits.html` - User EV benefits
- `frontend/user_ev_discount.html` - EV discount claims
- `frontend/admin_vgk_all-benefits.html` - All EV benefits
- `frontend/admin_vgk_ev-discount-training.html` - Discount & training
- `frontend/admin_vgk_fleet-orders.html` - Fleet management
- `frontend/admin_vgk_franchise-earnings.html` - Franchise income
- `frontend/admin_vgk_insurance-earnings.html` - Insurance earnings
- `frontend/admin_vgk_referral-income.html` - Referral income
- `frontend/admin_ev_benefit_analytics.html` - Analytics dashboard

### Database Models
- `EVModel` (`backend/app/models/ev_model.py`)
- `EVCouponClaim` (`backend/app/models/ev_coupon_claim.py`)
- `TrainingCourse` (`backend/app/models/training_course.py`)
- `TrainingClaim` (`backend/app/models/training_claim.py`)
- `EV`, `Purchase`, `CouponBenefit` (`backend/app/models/ev_discount.py`)
- `FranchisePurchase`, `InsurancePolicy`, `FleetOrder`

### Services
- `EVClaimService` (`backend/app/services/ev_claim_service.py`)
- `TrainingClaimService` (`backend/app/services/training_claim_service.py`)

---

## 9. FIELD ALLOWANCE MODULE

### Backend Endpoints
- `backend/app/api/v1/endpoints/field_allowance.py` (if exists)
  - Field allowance eligibility tracking
  - Scheme selection (Bronze/Silver/Gold)

### Frontend Pages
- `frontend/admin_field_allowances.html` - Field allowance management

### Database Models
- `FieldAllowanceEligibility` (`backend/app/models/field_allowance.py`)
- `FieldAllowanceProgress`
- `AllowanceSchemeSelector` - Scheme selection
- `AllowanceTierDefinition` - Tier configuration

### Services
- `FieldAllowanceService` (eligibility calculation)

---

## 10. FINANCE & REPORTING MODULE

### Backend Endpoints
- `backend/app/api/v1/endpoints/finance_admin.py`
  - `/finance/cost-calculations/daily` - Daily cost breakdown
  - `/finance/company-revenue` - Revenue analysis
  - `/finance/tds-management` - TDS tracking
  - `/finance/payout-processing` - Payout management

- `backend/app/api/v1/endpoints/financial_reports.py`
  - `/finance/reports/comprehensive` - All financial reports

### Frontend Pages
- `frontend/finance_company_earnings.html` - Company earnings
- `frontend/finance_cost_analysis.html` - Cost analysis
- `frontend/finance_tds_management.html` - TDS management
- `frontend/vgk_company_earnings.html` - VGK earnings oversight

### Database Models
- `CompanyEarnings` (`backend/app/models/transaction.py`)
- `DailyCostCalculation` - Daily cost tracking
- `TDSPayable` - TDS payable tracking

### Services
- `FinanceReportingService` (`backend/app/services/finance_reporting_service.py`)

---

## 11. BANNERS & COMMUNICATION MODULE

### Backend Endpoints
- `backend/app/api/v1/endpoints/banners.py`
  - `/banners/active` - Active banners
  - `/admin/banners/manage` - Banner management
  - `/admin/popups/manage` - Popup management
  - `/admin/top-performers` - Top performers display

### Frontend Pages
- `frontend/admin_banners_management.html` - Banner management
- `frontend/admin_popups.html` - Popup management
- `frontend/admin_birthdays.html` - Birthday management
- `frontend/vgk_popup_control.html` - VGK popup control

### Database Models
- `Banner`, `CustomBanner` (`backend/app/models/banner.py`)
- `PopupMessage` - Popup messages
- `BirthdayMessage` - Birthday greetings
- `UserCouponAcceptance` - User acceptance tracking
- `EmailTemplate` - Email templates

### Services
- `BannerService` (`backend/app/services/banner_service.py`)

---

## 12. SYSTEM CONTROL & CONFIGURATION MODULE

### Backend Endpoints
- `backend/app/api/v1/endpoints/system_controls.py`
  - `/rvz/system-controls` - VGK system toggles
  - `/rvz/toggle-kyc-processing` - KYC on/off
  - `/rvz/toggle-income-calculation` - Income calc on/off

- `backend/app/api/v1/endpoints/system_configuration.py`
  - `/rvz/system-config` - System constants
  - `/rvz/update-config` - Configuration updates

- `backend/app/api/v1/endpoints/rate_configuration.py`
  - `/rvz/rate-configuration` - Income rate configuration

- `backend/app/api/v1/endpoints/daily_ceiling.py`
  - `/rvz/daily-ceiling` - Daily income ceiling management

### Frontend Pages
- `frontend/superadmin_global_config.html` - Global configuration
- `frontend/superadmin_system_health.html` - System health monitoring

### Database Models
- `SystemControl` (`backend/app/models/system_control.py`)
- `AppSettings` - Application settings
- VGK-exclusive configuration tables

### Services
- `SystemControlService` (`backend/app/services/system_control_service.py`)

---

## 13. WHATSAPP MESSAGING MODULE

### Backend Endpoints
- `backend/app/api/v1/endpoints/whatsapp.py`
  - `/whatsapp/send-otp` - OTP via WhatsApp
  - `/whatsapp/message-status` - Delivery tracking
  - `/admin/whatsapp/pause` - Pause messaging (VGK)

### Frontend Pages
- Integrated into login and password reset flows

### Database Models
- `WhatsAppControl` (`backend/app/models/whatsapp.py`)
- `MessageLog` - Message delivery tracking

### Services
- `WhatsAppService` (Twilio integration)

---

## 14. VGK SUPREME ADMIN MODULE

### Backend Endpoints
- `backend/app/api/v1/endpoints/vgk.py`
  - `/rvz/dashboard` - Supreme admin dashboard
  - `/rvz/user-management` - User activation/deletion
  - `/rvz/data-recovery` - Deleted data recovery
  - `/rvz/production-reset` - Production data reset

- `backend/app/api/v1/endpoints/vgk_password_change.py`
  - `/rvz/change-user-password` - Force password change

- `backend/app/api/v1/endpoints/emergency_wallet.py`
  - `/rvz/emergency-wallet-adjustment` - Manual wallet adjustments

### Frontend Pages
- `frontend/vgk_password_change.html` - VGK password management
- `frontend/vgk_secondary_password_setup.html` - Secondary password
- `frontend/admin_data_recovery.html` - Data recovery interface
- `frontend/admin_emergency_wallet.html` - Emergency wallet adjustments

### Database Models
- All models (VGK has supreme access)
- Audit logs for all VGK actions

### Services
- All services (VGK supreme access)
- `AuditLogger` (`backend/app/core/audit.py`)

---

## 15. AUDIT & LOGGING MODULE

### Backend Endpoints
- `backend/app/api/v1/endpoints/log_reports.py`
  - `/admin/logs/scheduler` - Scheduler logs
  - `/admin/logs/data-changes` - Data change logs
  - `/admin/logs/system` - System logs

### Frontend Pages
- `frontend/admin_reports.html` - Report dashboard

### Database Models
- `SystemLog` (`backend/app/models/system_log.py`)
- `SchedulerLog` - Scheduler execution logs
- `DataChangeLog` - Data modification tracking
- `AuditMixin` (`backend/app/models/base.py`) - Audit trail mixin

### Services
- `AuditLogger` (`backend/app/core/audit.py`)

---

## 16. SCHEDULER & AUTOMATION MODULE

### Backend Components
- `backend/app/core/scheduler.py` - APScheduler configuration
- `backend/app/services/income_calculation_service.py` - Daily income calculation
- `backend/app/services/wallet_service.py` - Daily wallet synchronization
- `backend/app/services/withdrawal_service.py` - Auto-withdrawal generation

### Jobs Schedule (IST Timezone)
- **3:00 AM** - Daily income calculation
- **3:15 AM** - Wallet synchronization (earning → withdrawable)
- **3:30 AM** - Auto-withdrawal generation
- **Real-time** - KYC approval wallet sync

### Database Models
- `SchedulerLog` (`backend/app/models/system_log.py`)

---

## 17. RED COUPON VOTING MODULE

### Backend Endpoints
- `backend/app/api/v1/endpoints/red_coupon_voting.py`
  - `/red-coupon/submit-request` - Account reactivation request
  - `/admin/red-coupon/pending` - Admin voting
  - `/superadmin/red-coupon/review` - Super Admin review
  - `/finance/red-coupon/final-approval` - Finance final approval

### Frontend Pages
- `frontend/superadmin_red_id_oversight.html` - Red ID oversight

### Database Models
- `RedCouponApproval` (`backend/app/models/red_coupon.py`)

---

## 18. SUPPORT TICKETS MODULE

### Backend Endpoints
- `backend/app/api/v1/endpoints/tickets.py`
  - `/tickets/create` - User ticket creation
  - `/admin/tickets/all` - All tickets
  - `/admin/tickets/assign` - Ticket assignment

### Frontend Pages
- `frontend/user_tickets.html` - User ticket interface
- `frontend/admin_tickets_management.html` - Admin ticket management
- `frontend/admin_tickets_assigned.html` - Assigned tickets

### Database Models
- `Ticket` (`backend/app/models/ticket.py`)

---

## 19. EXPENSE MANAGEMENT MODULE

### Backend Endpoints
- `backend/app/api/v1/endpoints/expense_management.py`
  - `/expenses/categories` - Expense categories
  - `/expenses/record` - Expense recording

### Frontend Pages
- `frontend/admin_expense_categories.html` - Category management

### Database Models
- `ExpenseCategory` (`backend/app/models/expense_category.py`)

---

## 20. ADMIN PASSWORD RESET MODULE

### Backend Endpoints
- `backend/app/api/v1/endpoints/admin_password_reset.py`
  - `/admin/reset-user-password` - Admin-initiated password reset

### Frontend Pages
- `frontend/admin_password_reset.html` - Admin password reset
- `frontend/superadmin_password_reset.html` - Super Admin password reset

---

## CORE INFRASTRUCTURE

### Security & Authentication
- `backend/app/core/security.py` - JWT, password hashing, RBAC
- `backend/app/core/rbac.py` - Role-based access control
- `backend/app/core/user_update_guard.py` - User update protection

### Database
- `backend/app/core/database.py` - PostgreSQL connection
- `backend/app/core/config.py` - Environment configuration
- **DATABASE_URL** - Development database (ep-bitter-heart)
- **PROD_DATABASE_URL** - Production database

### Services
- `backend/app/services/` - All business logic services
  - `user_service.py`
  - `reference_service.py`
  - `income_calculation_service.py`
  - `wallet_service.py`
  - `withdrawal_service.py`
  - `award_service.py`
  - `kyc_service.py`
  - And many more...

### Templates
- `frontend/templates/user.js` - User template
- `frontend/templates/admin.js` - Admin template
- `frontend/templates/superadmin.js` - Super Admin template
- `frontend/templates/finance.js` - Finance Admin template
- `frontend/templates/vgk.js` - VGK template

---

## ROLE-BASED ACCESS SUMMARY

### User (Regular)
- View income, team, awards
- Request withdrawals
- Submit KYC/Bank details
- Create support tickets

### Admin
- Approve KYC documents
- Verify income (Admin Verified status)
- Manage users, coupons, PINs
- Award processing (initial approval)

### Super Admin
- Verify Admin-approved income (Admin Verified → Transfer Queue)
- Approve bank details
- Award verification
- Placement approvals
- Red Coupon voting

### Finance Admin
- Process Transfer Queue → Payment
- TDS management
- Award procurement
- Financial reporting

### RVZ ID (Supreme Admin)
- **FULL ACCESS** to all modules
- System configuration
- Rate configuration
- Emergency wallet adjustments
- Data recovery
- Production resets
- User deletion/activation
- All admin workflows (can act as any role)

---

## WVV PROTOCOL WORKFLOW

**Income Approval (3-Stage)**:
1. **Admin** → Approves income (Pending → Admin Verified)
2. **Super Admin** → Verifies income (Admin Verified → Transfer Queue)
3. **Finance** → Processes payment (Transfer Queue → Bank Sent → Accounts Paid)

**Award Approval (Multi-Role)**:
1. Admin → Initial approval
2. Super Admin → Verification
3. Finance → Payment processing / Procurement
4. VGK → Final oversight

---

## DC PROTOCOL KEY TABLES

**Single Source of Truth**:
- `pending_income` - **ALL earnings history** (NEVER delete)
- `users` - User identity and authentication
- `transactions` - Payment history
- `withdrawals` - Withdrawal records
- `user_leg_metrics` - Cached team metrics

**Formula**:
- **Pending Balance** = Total Earned - Total Paid
- **PAID_STATUSES** = ['Finance Paid', 'Accounts Paid']

---

## TOTAL COUNTS

- **Backend Endpoints**: 50+ files, 500+ API routes
- **Frontend Pages**: 70+ HTML files
- **Database Models**: 40+ models
- **Services**: 25+ service files
- **Roles**: 5 (User, Admin, Super Admin, Finance Admin, RVZ ID)

---

**Last Updated**: November 2, 2025
**Status**: Complete module map ready for DC Protocol restructuring
