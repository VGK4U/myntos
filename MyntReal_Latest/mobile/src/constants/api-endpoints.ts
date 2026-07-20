/**
 * API Endpoints Constants
 * DC Protocol: DC_MOBILE_API_ENDPOINTS_001
 * Single source of truth for all API endpoints matching web program
 */

export const API_PREFIX = '/api/v1';

export const API_ENDPOINTS = {
  // ==================== PROGRESS ====================
  PROGRESS: {
    SUMMARY: `${API_PREFIX}/staff/progress/summary`,
    EXPORT: `${API_PREFIX}/staff/progress/export`,
  },

  // ==================== ATTENDANCE ====================
  ATTENDANCE: {
    TODAY: `${API_PREFIX}/staff/attendance/today`,
    CLOCK_IN: `${API_PREFIX}/staff/attendance/clock-in`,
    CLOCK_OUT: `${API_PREFIX}/staff/attendance/clock-out`,
    MY_HISTORY: `${API_PREFIX}/staff/attendance/my-history`,
    TIMELINE: `${API_PREFIX}/staff/attendance/timeline`,
    SUMMARY: `${API_PREFIX}/staff/attendance/summary`,
    TEAM: `${API_PREFIX}/staff/attendance/team`,
    REPORTS: `${API_PREFIX}/staff/attendance/reports`,
    BREAK_START: `${API_PREFIX}/staff/attendance/break/start`,
    BREAK_END: `${API_PREFIX}/staff/attendance/break/end`,
    BREAK_TYPES: `${API_PREFIX}/staff/attendance/break-types`,
    CHECK_ACTIVE_SESSION: `${API_PREFIX}/staff/attendance/check-active-session`,
    LOCATION_UPDATE: `${API_PREFIX}/staff/attendance/location/update`,
  },

  // ==================== ATTENDANCE SHEET (Admin) ====================
  ATTENDANCE_SHEET: {
    MONTHLY: (monthYear: string) => `${API_PREFIX}/staff/attendance-sheet/monthly/${monthYear}`,
    MARK: `${API_PREFIX}/staff/attendance-sheet/mark`,
    APPROVE: (sheetId: number) => `${API_PREFIX}/staff/attendance-sheet/${sheetId}/approve`,
    EXCEPTIONS: `${API_PREFIX}/staff/attendance-sheet/exceptions`,
    SUMMARY: (monthYear: string) => `${API_PREFIX}/staff/attendance-sheet/summary/${monthYear}`,
  },

  // ==================== LEAVES ====================
  LEAVES: {
    MY_BALANCE: `${API_PREFIX}/staff/leaves/my-balance`,
    MY_REQUESTS: `${API_PREFIX}/staff/leaves/my-requests`,
    LEAVE_TYPES: `${API_PREFIX}/staff/leaves/leave-types`,
    CHECK_CONFLICTS: (dates: string) => `${API_PREFIX}/staff/leaves/check-conflicts?dates=${dates}`,
    APPLY: `${API_PREFIX}/staff/leaves/apply`,
    CANCEL: (id: number) => `${API_PREFIX}/staff/leaves/cancel/${id}`,
    REQUEST_DETAIL: (id: number) => `${API_PREFIX}/staff/leaves/request/${id}`,
    APPROVAL_QUEUE_MANAGER: `${API_PREFIX}/staff/leaves/pending-approvals/manager`,
    APPROVAL_QUEUE_HR: `${API_PREFIX}/staff/leaves/pending-approvals/hr`,
    APPROVE_MANAGER: (id: number) => `${API_PREFIX}/staff/leaves/approve/manager/${id}`,
    APPROVE_HR: (id: number) => `${API_PREFIX}/staff/leaves/approve/hr/${id}`,
  },

  // ==================== TASKS ====================
  TASKS: {
    ASSIGNED_TO_ME: `${API_PREFIX}/staff/tasks/assigned-to-me`,
    ASSIGNED_BY_ME: `${API_PREFIX}/staff/tasks/assigned-by-me`,
    ASSIGNABLE_EMPLOYEES: `${API_PREFIX}/staff/tasks/assignable-employees`,
    CREATE: `${API_PREFIX}/staff/tasks`,
    UPDATE: (id: number) => `${API_PREFIX}/staff/tasks/${id}`,
    COMPLETE: (id: number) => `${API_PREFIX}/staff/tasks/${id}/complete`,
    PROGRESS: (id: number) => `${API_PREFIX}/staff/tasks/${id}/progress`,
    STATUS: (id: number) => `${API_PREFIX}/staff/tasks/${id}/status`,
    REVIEW_QUEUE: `${API_PREFIX}/staff/tasks/review-queue`,
    REVIEW: (id: number) => `${API_PREFIX}/staff/tasks/${id}/review`,
    TRACKER: `${API_PREFIX}/staff/tasks/tracker`,
  },

  // ==================== KRA ====================
  KRA: {
    INSTANCES: `${API_PREFIX}/staff/kra/instances`,
    INSTANCE_DETAIL: (id: number) => `${API_PREFIX}/staff/kra/instances/${id}`,
    TEMPLATES: `${API_PREFIX}/staff/kra/templates`,
    TEMPLATE_DETAIL: (id: number) => `${API_PREFIX}/staff/kra/templates/${id}`,
    TEMPLATE_ASSIGN: (id: number) => `${API_PREFIX}/staff/kra/templates/${id}/assign`,
    MY_KRAS: `${API_PREFIX}/staff/kra/my-kras`,
    MY_KRA_DETAIL: (id: number) => `${API_PREFIX}/staff/kra/my-kras/${id}`,
    SUBMIT: (id: number) => `${API_PREFIX}/staff/kra/my-kras/${id}/submit`,
    MANAGER_REVIEW_PENDING: `${API_PREFIX}/staff/kra/manager-review/pending`,
    MANAGER_REVIEW_APPROVE: `${API_PREFIX}/staff/kra/manager-review/approve`,
    MANAGER_REVIEW_REJECT: `${API_PREFIX}/staff/kra/manager-review/reject`,
    TEAM_SUMMARY: `${API_PREFIX}/staff/kra/team-summary`,
  },

  // ==================== DAY PLANNER ====================
  DAY_PLANNER: {
    TODAY: `${API_PREFIX}/staff/day-plans/today`,
    BY_DATE: `${API_PREFIX}/staff/day-plans/by-date`,
    AVAILABLE_TASKS: `${API_PREFIX}/staff/day-plans/available-tasks`,
    CREATE_OR_UPDATE: `${API_PREFIX}/staff/day-plans`,
    UPDATE_ITEM: (id: number) => `${API_PREFIX}/staff/day-plans/items/${id}`,
    DELETE_ITEM: (id: number) => `${API_PREFIX}/staff/day-plans/items/${id}`,
    FINALIZE: `${API_PREFIX}/staff/day-plans/finalize`,
    TEAM: `${API_PREFIX}/staff/day-plans/team`,
    TEAM_MEMBERS: `${API_PREFIX}/staff/day-plans/team/members`,
    CARRIED_FORWARD: `${API_PREFIX}/staff/day-plans/carried-forward`,
    DAY_PROGRESS: `${API_PREFIX}/staff/day-plans/day-progress`,
  },

  // ==================== TIMESHEET ====================
  TIMESHEET: {
    MY_ENTRIES: (date: string) => `${API_PREFIX}/staff/timesheet/my-entries/${date}`,
    MY_HISTORY: `${API_PREFIX}/staff/timesheet/my-history`,
    TIMELINE: (date: string) => `${API_PREFIX}/staff/timesheet/timeline/${date}`,
    CREATE: `${API_PREFIX}/staff/timesheet/entries`,
    UPDATE: (id: number) => `${API_PREFIX}/staff/timesheet/entries/${id}`,
    DELETE: (id: number) => `${API_PREFIX}/staff/timesheet/${id}`,
    APPROVAL_QUEUE: `${API_PREFIX}/staff/timesheet/approval-queue`,
    APPROVE: (id: number) => `${API_PREFIX}/staff/timesheet/entries/${id}/approve`,
    REJECT: (id: number) => `${API_PREFIX}/staff/timesheet/entries/${id}/reject`,
    COMPUTATION: `${API_PREFIX}/staff/timesheet/computation`,
    TEAM_SUMMARY: `${API_PREFIX}/staff/timesheet/team-summary`,
    TEAM_ENTRIES: `${API_PREFIX}/staff/timesheet/team-entries`,
    REPORTING_MANAGERS: `${API_PREFIX}/staff/timesheet/reporting-managers`,
    MY_TASKS: `${API_PREFIX}/staff/timesheet/my-tasks`,
    MY_KRAS: `${API_PREFIX}/staff/timesheet/my-kras`,
    MY_LEADS: `${API_PREFIX}/staff/timesheet/my-leads`,
    SAVE: `${API_PREFIX}/staff/timesheet`,
  },

  // ==================== JOURNEYS ====================
  JOURNEYS: {
    MY: `${API_PREFIX}/staff/journeys/my`,
    ACTIVE: `${API_PREFIX}/staff/journeys/active`,
    ACTIVE_ALL: `${API_PREFIX}/staff/journeys/active/all`,
    START: `${API_PREFIX}/staff/journeys/start`,
    END: (id: number) => `${API_PREFIX}/staff/journeys/${id}/end`,
    PHOTO: (id: number) => `${API_PREFIX}/staff/journeys/${id}/photo`,
    HEARTBEAT: (id: number) => `${API_PREFIX}/staff/journeys/${id}/heartbeat`,
    TRACK_POINTS: (id: number) => `${API_PREFIX}/staff/journeys/${id}/track-points`,
    APPROVE: (id: number) => `${API_PREFIX}/staff/journeys/${id}/approve`,
    BULK_APPROVE: `${API_PREFIX}/staff/journeys/bulk-approve`,
    COMPANIES: `${API_PREFIX}/staff/journeys/companies`,
    TRANSPORT_RATES: `${API_PREFIX}/staff/journeys/transport-rates`,
    STATS: `${API_PREFIX}/staff/journeys/stats`,
    TEAM: `${API_PREFIX}/staff/journeys/team`,
    ALL: `${API_PREFIX}/staff/journeys/all`,
    HR: `${API_PREFIX}/staff/journeys/hr`,
    VGK4U_DASHBOARD: `${API_PREFIX}/staff/journeys/vgk4u/dashboard`,
    FORCE_STOP: (id: number) => `${API_PREFIX}/staff/journeys/${id}/force-stop`,
  },

  // ==================== REIMBURSEMENTS ====================
  REIMBURSEMENTS: {
    MY_CLAIMS: `${API_PREFIX}/staff/reimbursements/my-claims`,
    MY_ASSIGNED_COMPANIES: `${API_PREFIX}/staff/reimbursements/my-assigned-companies`,
    EXPENSE_CATEGORIES: `${API_PREFIX}/staff/reimbursements/expense-categories`,
    CREATE_CLAIM: `${API_PREFIX}/staff/reimbursements/claims`,
    CLAIM_DETAIL: (id: number) => `${API_PREFIX}/staff/reimbursements/claims/${id}`,
    CLAIM_ITEMS: (id: number) => `${API_PREFIX}/staff/reimbursements/claims/${id}/items`,
    SUBMIT_CLAIM: (id: number) => `${API_PREFIX}/staff/reimbursements/claims/${id}/submit`,
    WITHDRAW_CLAIM: (id: number) => `${API_PREFIX}/staff/reimbursements/claims/${id}/withdraw`,
    UPLOAD_BILL: (claimId: number, itemId: number) => `${API_PREFIX}/staff/reimbursements/claims/${claimId}/items/${itemId}/upload-bill`,
    APPROVAL_QUEUE: `${API_PREFIX}/staff/reimbursements/approval-queue`,
    MANAGER_APPROVE: (id: number) => `${API_PREFIX}/staff/reimbursements/claims/${id}/manager-approve`,
    FINANCE_APPROVE: (id: number) => `${API_PREFIX}/staff/reimbursements/claims/${id}/finance-approve`,
    REJECT: (id: number) => `${API_PREFIX}/staff/reimbursements/claims/${id}/reject`,
    FUND_ALLOCATIONS: `${API_PREFIX}/staff/reimbursements/fund-allocations`,
  },

  // ==================== SERVICE TICKETS ====================
  SERVICE_TICKETS: {
    DASHBOARD_STATS: `${API_PREFIX}/tickets/service/dashboard-stats`,
    QUEUE: `${API_PREFIX}/tickets/service/queue`,
    CREATE: `${API_PREFIX}/tickets/service/create`,
    PUBLIC_CREATE: `${API_PREFIX}/tickets/service/public/create`,
    DETAIL: (id: number) => `${API_PREFIX}/tickets/service/${id}`,
    ACKNOWLEDGE: (id: number) => `${API_PREFIX}/tickets/service/${id}/acknowledge`,
    DIAGNOSE: (id: number) => `${API_PREFIX}/tickets/service/${id}/diagnose`,
    COMPLETE: (id: number) => `${API_PREFIX}/tickets/service/${id}/complete`,
    CLOSE: (id: number) => `${API_PREFIX}/tickets/service/${id}/close`,
    BILLING: (id: number) => `${API_PREFIX}/tickets/service/${id}/billing`,
    CREATE_BILLING: (id: number) => `${API_PREFIX}/tickets/service/${id}/billing/create`,
    PROCUREMENT_QUEUE: `${API_PREFIX}/tickets/service/procurement-queue`,
    SPARE_ACKNOWLEDGE: (id: number) => `${API_PREFIX}/tickets/service/spares/${id}/acknowledge`,
    SPARE_RELEASE: (id: number) => `${API_PREFIX}/tickets/service/spares/${id}/release`,
    SPARE_PRICING: (id: number) => `${API_PREFIX}/tickets/service/spares/${id}/pricing`,
    REPORTS: `${API_PREFIX}/tickets/service/reports`,
    REPORTS_REVENUE: `${API_PREFIX}/tickets/service/reports/revenue-by-partner`,
    REPORTS_MY_REVENUE: `${API_PREFIX}/tickets/service/reports/my-revenue`,
    SERVICE_CENTERS: `${API_PREFIX}/tickets/service-centers`,
    EXPORT: `${API_PREFIX}/tickets/service/export`,
  },

  // ==================== SUPPORT TICKETS ====================
  SUPPORT_TICKETS: {
    MY_TICKETS: `${API_PREFIX}/tickets/my-tickets`,
    CREATE: `${API_PREFIX}/tickets`,
    DETAIL: (id: number) => `${API_PREFIX}/tickets/${id}`,
  },

  // ==================== EMPLOYEES ====================
  EMPLOYEES: {
    LIST: `${API_PREFIX}/staff/employees`,
    DETAIL: (id: number) => `${API_PREFIX}/staff/employees/${id}`,
    DIRECTORY: `${API_PREFIX}/staff/employees`,
    MANAGERS: `${API_PREFIX}/staff/employees/managers`,
    TEAM: `${API_PREFIX}/staff/employees/team`,
    KYC_MY: `${API_PREFIX}/staff/employees/kyc/my`,
    KYC_PENDING: `${API_PREFIX}/staff/employees/kyc/pending`,
    MODULES: (id: number) => `${API_PREFIX}/staff/employees/${id}/modules`,
  },

  // ==================== CRM / LEADS ====================
  CRM: {
    MY_DASHBOARD: `${API_PREFIX}/crm/my-dashboard`,
    MY_LEADS: `${API_PREFIX}/crm/my-leads`,
    LEAD_DETAIL: (id: number) => `${API_PREFIX}/crm/leads/${id}`,
    SOURCES: `${API_PREFIX}/crm/sources`,
    MY_COMPANIES: `${API_PREFIX}/crm/my-companies`,
  },

  // ==================== CALL TRACKING ====================
  CALL_TRACKING: {
    SYNC_CALLS: '/call-tracking/sync',
    MY_CALLS: '/call-tracking/my-calls',
    MY_STATS: '/call-tracking/my-stats',
    MANAGEMENT_OVERVIEW: '/call-tracking/management/overview',
    STAFF_CALLS: (staffId: number) => `/call-tracking/staff/${staffId}/calls`,
    RECORDING_UPLOAD: '/call-tracking/recordings/upload',
    RECORDING_STREAM: (recordingId: number) => `/call-tracking/recordings/${recordingId}/stream`,
    RECORDING_METADATA: (recordingId: number) => `/call-tracking/recordings/${recordingId}/metadata`,
    RECORDINGS_BULK_CHECK: '/call-tracking/recordings/bulk-upload',
    REMATCH_LEADS: '/call-tracking/rematch-leads',
    TOGGLE_TRACKING: (staffId: number) => `/call-tracking/staff/${staffId}/toggle-tracking`,
  },

  // ==================== AUTH ====================
  AUTH: {
    LOGIN: `${API_PREFIX}/staff/auth/login`,
    LOGOUT: `${API_PREFIX}/staff/auth/logout`,
    ME: `${API_PREFIX}/auth/me-hybrid`,
    CHANGE_PASSWORD: `${API_PREFIX}/staff/auth/change-password`,
    REFRESH: `${API_PREFIX}/staff/auth/refresh`,
  },
};

export default API_ENDPOINTS;
