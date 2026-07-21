/**
 * Router Service - Mobile App Navigation
 * DC Protocol: DC_MOBILE_ROUTER_001
 * Handles page navigation with bottom tab support for all portals
 */

export type PageRoute = 
  // Staff Portal Routes
  | 'dashboard'
  | 'progress'
  | 'attendance'
  | 'journeys'
  | 'location-history'
  | 'timesheet'
  | 'announcements'
  | 'leaves'
  | 'reimbursements'
  | 'kras'
  | 'tasks'
  | 'tickets'
  | 'profile'
  | 'settings'
  | 'team-attendance'
  | 'team-journeys'
  | 'team-tracker'
  | 'staff-leads'
  | 'staff-kyc'
  | 'staff-zynova'
  | 'staff-zynova-real-estate'
  | 'staff-zynova-insurance'
  | 'staff-service'
  | 'staff-crm'
  | 'staff-team-leads'
  | 'change-password'
  // Staff Dashboard Section - New
  | 'staff-training-videos'
  | 'staff-employees'
  | 'staff-directory'
  | 'staff-kyc-approvals'
  | 'staff-review'
  // Attendance Section - New
  | 'staff-leave-approvals'
  | 'staff-attendance-sheet'
  | 'staff-attendance-reports'
  | 'staff-attendance-exceptions'
  | 'staff-attendance-computation'
  // CRM Section - New
  | 'staff-lead-sources'
  // Day Planner Section
  | 'day-planner'
  // Tasks Section - New
  | 'tasks-assigned'
  | 'tasks-received'
  | 'task-detail'
  | 'task-create'
  | 'task-analytics'
  | 'staff-team-activities'
  | 'staff-task-tracker'
  | 'staff-task-reviews'
  // KRAs Section - New
  | 'staff-kra-templates'
  | 'staff-kra-tracking'
  | 'staff-kra-review'
  // Timesheet Section - New
  | 'staff-timesheet-approval'
  // Journeys Section - New
  | 'staff-all-journeys'
  | 'staff-vgk4u-journeys'
  // Location Tracking Section - New
  | 'staff-all-location-tracker'
  | 'staff-team-live-tracker'
  // Reimbursement Section - New
  | 'staff-reimbursement-approvals'
  | 'staff-procurement-requests'
  // Call Tracking Section - New
  | 'staff-call-tracking'
  // Auto Dialer
  | 'auto-dialer'
  // Call History
  | 'call-history'
  // Operator Calls
  | 'operator-calls'
  // Service Tickets Section - New
  | 'staff-tickets'
  | 'staff-service-performance'
  | 'staff-service-procurement'
  | 'staff-service-procurement-queue'
  | 'staff-service-reports'
  | 'staff-service-queue'
  | 'staff-service-revenue'
  // Announcements Section - New
  | 'create-announcement'
  | 'edit-announcement'
  // MNR Portal Routes
  | 'mnr-dashboard'
  | 'mnr-income'
  | 'mnr-earnings'
  | 'mnr-withdrawals'
  | 'mnr-benefits'
  | 'mnr-referrals'
  | 'mnr-team'
  | 'mnr-awards'
  | 'mnr-announcements'
  | 'mnr-profile'
  | 'mnr-profile-edit'
  | 'mnr-kyc'
  | 'mnr-bank'
  | 'mnr-change-password'
  | 'mnr-points'
  | 'mnr-coupons'
  | 'mnr-daywise'
  | 'mnr-ev-discount'
  | 'mnr-my-announcements'
  | 'mnr-my-leads'
  | 'mnr-feedback'
  | 'mnr-add-member'
  | 'mnr-announcements-pending'
  | 'mnr-announcements-approved'
  | 'mnr-announcements-rejected'
  | 'mnr-create-announcement'
  | 'mnr-coupon-buy'
  | 'mnr-coupon-activate'
  | 'mnr-coupon-status'
  | 'mnr-coupon-transfer'
  | 'mnr-coupon-progress'
  | 'mnr-settings'
  | 'mnr-members-all'
  | 'mnr-members-picture'
  | 'mnr-members-ved'
  | 'mnr-earnings-summary'
  | 'mnr-income-direct'
  | 'mnr-income-matching'
  | 'mnr-income-ved'
  | 'mnr-income-guru'
  | 'mnr-income-field'
  | 'mnr-franchise-earnings'
  | 'mnr-bonanza'
  // VGK4U Member Portal Routes
  | 'vgk-birthdays'
  | 'vgk-top-earners'
  | 'vgk-awards'
  | 'vgk-my-registrations'
  | 'vgk-bonanza-rewards'
  | 'vgk-points-balance'
  | 'vgk-member-hub'
  | 'vgk-settings'
  | 'vgk-bank-details'
  | 'vgk-profile-edit'
  | 'vgk-kyc'
  | 'vgk-feedback'
  | 'vgk-announcements'
  | 'vgk-my-announcements'
  | 'vgk-coupon-activate'
  | 'vgk-coupon-progress'
  | 'vgk-coupon-transfer'
  | 'vgk-income-unified'
  // Zynova Portal Routes
  | 'zynova-real-estate'
  | 'zynova-insurance'
  | 'zynova-training'
  // MyntReal Portal Routes
  | 'myntreal-properties'
  | 'myntreal-earnings'
  // Partner Portal Routes
  | 'partner-dashboard'
  | 'partner-orders'
  | 'partner-invoices'
  | 'partner-payments'
  | 'partner-revenue'
  | 'partner-leads'
  | 'partner-profile'
  | 'partner-service'
  | 'partner-raise-ticket'
  | 'partner-new-order'
  | 'partner-ticket-history'
  | 'partner-kyc-documents'
  | 'partner-spare-orders'
  // Staff Payouts & Incentives
  | 'staff-my-payouts'
  | 'staff-my-lead-incentives'
  // Accounts
  | 'staff-vendors';

interface RouteConfig {
  id: PageRoute;
  title: string;
  icon: string;
  showInTabs: boolean;
  tabOrder?: number;
  portal?: 'staff' | 'mnr' | 'partner';
}

class RouterService {
  private currentRoute: PageRoute = 'dashboard';
  private history: PageRoute[] = [];
  private listeners: ((route: PageRoute) => void)[] = [];

  readonly routes: Record<PageRoute, RouteConfig> = {
    // Staff Portal
    'dashboard': { id: 'dashboard', title: 'Home', icon: 'home', showInTabs: true, tabOrder: 1, portal: 'staff' },
    'progress': { id: 'progress', title: 'Progress Dashboard', icon: 'bar-chart', showInTabs: false, portal: 'staff' },
    'attendance': { id: 'attendance', title: 'Attendance', icon: 'clock', showInTabs: true, tabOrder: 2, portal: 'staff' },
    'journeys': { id: 'journeys', title: 'Journeys', icon: 'map', showInTabs: true, tabOrder: 3, portal: 'staff' },
    'announcements': { id: 'announcements', title: 'News', icon: 'bell', showInTabs: true, tabOrder: 4, portal: 'staff' },
    'profile': { id: 'profile', title: 'Profile', icon: 'user', showInTabs: true, tabOrder: 5, portal: 'staff' },
    'location-history': { id: 'location-history', title: 'Location History', icon: 'map-pin', showInTabs: false, portal: 'staff' },
    'timesheet': { id: 'timesheet', title: 'Timesheet', icon: 'calendar', showInTabs: false, portal: 'staff' },
    'leaves': { id: 'leaves', title: 'Leaves', icon: 'calendar-x', showInTabs: false, portal: 'staff' },
    'reimbursements': { id: 'reimbursements', title: 'Reimbursements', icon: 'credit-card', showInTabs: false, portal: 'staff' },
    'kras': { id: 'kras', title: 'KRAs', icon: 'target', showInTabs: false, portal: 'staff' },
    'tasks': { id: 'tasks', title: 'Tasks', icon: 'check-square', showInTabs: false, portal: 'staff' },
    'tickets': { id: 'tickets', title: 'Support', icon: 'help-circle', showInTabs: false, portal: 'staff' },
    'settings': { id: 'settings', title: 'Settings', icon: 'settings', showInTabs: false },
    'team-attendance': { id: 'team-attendance', title: 'Team Attendance', icon: 'users', showInTabs: false, portal: 'staff' },
    'team-journeys': { id: 'team-journeys', title: 'Team Journeys', icon: 'truck', showInTabs: false, portal: 'staff' },
    'team-tracker': { id: 'team-tracker', title: 'Live Tracker', icon: 'navigation', showInTabs: false, portal: 'staff' },
    'staff-leads': { id: 'staff-leads', title: 'My Leads', icon: 'users', showInTabs: false, portal: 'staff' },
    'staff-kyc': { id: 'staff-kyc', title: 'My KYC', icon: 'file-text', showInTabs: false, portal: 'staff' },
    'staff-zynova': { id: 'staff-zynova', title: 'VGK4U', icon: 'briefcase', showInTabs: false, portal: 'staff' },
    'staff-zynova-real-estate': { id: 'staff-zynova-real-estate', title: 'Real Estate', icon: 'home', showInTabs: false, portal: 'staff' },
    'staff-zynova-insurance': { id: 'staff-zynova-insurance', title: 'Insurance', icon: 'shield', showInTabs: false, portal: 'staff' },
    'staff-service': { id: 'staff-service', title: 'Service Center', icon: 'tool', showInTabs: false, portal: 'staff' },
    'staff-crm': { id: 'staff-crm', title: 'CRM Dashboard', icon: 'pie-chart', showInTabs: false, portal: 'staff' },
    'staff-team-leads': { id: 'staff-team-leads', title: 'Team Leads', icon: 'users', showInTabs: false, portal: 'staff' },
    'change-password': { id: 'change-password', title: 'Change Password', icon: 'lock', showInTabs: false, portal: 'staff' },
    // Staff Dashboard Section - New Routes
    'staff-employees': { id: 'staff-employees', title: 'Employees', icon: 'users', showInTabs: false, portal: 'staff' },
    'staff-training-videos': { id: 'staff-training-videos', title: 'Training Videos', icon: 'play-circle', showInTabs: false, portal: 'staff' },
    'staff-directory': { id: 'staff-directory', title: 'Employee Directory', icon: 'book', showInTabs: false, portal: 'staff' },
    'staff-kyc-approvals': { id: 'staff-kyc-approvals', title: 'KYC Approvals', icon: 'check-circle', showInTabs: false, portal: 'staff' },
    'staff-review': { id: 'staff-review', title: 'Review Dashboard', icon: 'clipboard', showInTabs: false, portal: 'staff' },
    // Attendance Section - New Routes
    'staff-leave-approvals': { id: 'staff-leave-approvals', title: 'Leave Approvals', icon: 'check-square', showInTabs: false, portal: 'staff' },
    'staff-attendance-sheet': { id: 'staff-attendance-sheet', title: 'Attendance Records', icon: 'grid', showInTabs: false, portal: 'staff' },
    'staff-attendance-reports': { id: 'staff-attendance-reports', title: 'Attendance Dashboard', icon: 'bar-chart-2', showInTabs: false, portal: 'staff' },
    'staff-attendance-exceptions': { id: 'staff-attendance-exceptions', title: 'Exception Approvals', icon: 'alert-triangle', showInTabs: false, portal: 'staff' },
    'staff-attendance-computation': { id: 'staff-attendance-computation', title: 'Attendance Computation', icon: 'cpu', showInTabs: false, portal: 'staff' },
    // CRM Section - New Routes
    'staff-lead-sources': { id: 'staff-lead-sources', title: 'Lead Sources', icon: 'list', showInTabs: false, portal: 'staff' },
    'staff-call-tracking': { id: 'staff-call-tracking', title: 'Call Tracking', icon: 'call', showInTabs: false, portal: 'staff' },
    'auto-dialer': { id: 'auto-dialer', title: 'Auto Dialer', icon: 'phone-call', showInTabs: false, portal: 'staff' },
    'call-history': { id: 'call-history', title: 'Call History', icon: 'phone', showInTabs: false, portal: 'staff' },
    'operator-calls': { id: 'operator-calls', title: 'Operator Calls', icon: 'headphones', showInTabs: false, portal: 'staff' },
    // Day Planner Section
    'day-planner': { id: 'day-planner', title: 'Day Planner', icon: 'calendar', showInTabs: false, portal: 'staff' },
    // Tasks Section - New Routes
    'tasks-assigned': { id: 'tasks-assigned', title: 'Assigned By Me', icon: 'send', showInTabs: false, portal: 'staff' },
    'tasks-received': { id: 'tasks-received', title: 'Assigned To Me', icon: 'inbox', showInTabs: false, portal: 'staff' },
    'task-detail': { id: 'task-detail', title: 'Task Details', icon: 'file-text', showInTabs: false, portal: 'staff' },
    'task-create': { id: 'task-create', title: 'Create Task', icon: 'plus', showInTabs: false, portal: 'staff' },
    'task-analytics': { id: 'task-analytics', title: 'Task Analytics', icon: 'pie-chart', showInTabs: false, portal: 'staff' },
    'staff-team-activities': { id: 'staff-team-activities', title: 'Team Activities', icon: 'activity', showInTabs: false, portal: 'staff' },
    'staff-task-tracker': { id: 'staff-task-tracker', title: 'Task Dashboard', icon: 'trending-up', showInTabs: false, portal: 'staff' },
    'staff-task-reviews': { id: 'staff-task-reviews', title: 'Task Reviews', icon: 'star', showInTabs: false, portal: 'staff' },
    // KRAs Section - New Routes
    'staff-kra-templates': { id: 'staff-kra-templates', title: 'KRA Templates', icon: 'file', showInTabs: false, portal: 'staff' },
    'staff-kra-tracking': { id: 'staff-kra-tracking', title: 'KRA Tracking Sheet', icon: 'grid', showInTabs: false, portal: 'staff' },
    'staff-kra-review': { id: 'staff-kra-review', title: 'KRA Review', icon: 'eye', showInTabs: false, portal: 'staff' },
    // Timesheet Section - New Routes
    'staff-timesheet-approval': { id: 'staff-timesheet-approval', title: 'Timesheet Approval', icon: 'check', showInTabs: false, portal: 'staff' },
    // Journeys Section - New Routes
    'staff-all-journeys': { id: 'staff-all-journeys', title: 'All Journeys', icon: 'map', showInTabs: false, portal: 'staff' },
    'staff-vgk4u-journeys': { id: 'staff-vgk4u-journeys', title: 'VGK4U Journeys', icon: 'truck', showInTabs: false, portal: 'staff' },
    // Location Tracking Section - New Routes
    'staff-all-location-tracker': { id: 'staff-all-location-tracker', title: 'All Location Tracker', icon: 'map-pin', showInTabs: false, portal: 'staff' },
    'staff-team-live-tracker': { id: 'staff-team-live-tracker', title: 'Team Live Tracker', icon: 'navigation', showInTabs: false, portal: 'staff' },
    // Reimbursement Section - New Routes
    'staff-reimbursement-approvals': { id: 'staff-reimbursement-approvals', title: 'Reimbursement Approvals', icon: 'check-circle', showInTabs: false, portal: 'staff' },
    'staff-procurement-requests': { id: 'staff-procurement-requests', title: 'Procurement Requests', icon: 'file-text', showInTabs: false, portal: 'staff' },
    // Service Tickets Section - New Routes
    'staff-tickets': { id: 'staff-tickets', title: 'Raise Ticket', icon: 'plus-circle', showInTabs: false, portal: 'staff' },
    'staff-service-performance': { id: 'staff-service-performance', title: 'Performance', icon: 'trending-up', showInTabs: false, portal: 'staff' },
    'staff-service-procurement': { id: 'staff-service-procurement', title: 'Procurement', icon: 'shopping-cart', showInTabs: false, portal: 'staff' },
    'staff-service-procurement-queue': { id: 'staff-service-procurement-queue', title: 'Procurement Queue', icon: 'list', showInTabs: false, portal: 'staff' },
    'staff-service-reports': { id: 'staff-service-reports', title: 'Reports', icon: 'file-text', showInTabs: false, portal: 'staff' },
    'staff-service-queue': { id: 'staff-service-queue', title: 'Service Queue', icon: 'layers', showInTabs: false, portal: 'staff' },
    'staff-service-revenue': { id: 'staff-service-revenue', title: 'Service Revenue', icon: 'dollar-sign', showInTabs: false, portal: 'staff' },
    // Announcements Section - New Routes
    'create-announcement': { id: 'create-announcement', title: 'Create Announcement', icon: 'plus-circle', showInTabs: false, portal: 'staff' },
    'edit-announcement': { id: 'edit-announcement', title: 'Edit Announcement', icon: 'edit', showInTabs: false, portal: 'staff' },
    // Accounts Section
    'staff-vendors': { id: 'staff-vendors', title: 'Vendors', icon: 'package', showInTabs: false, portal: 'staff' },
    
    // MNR Portal
    'mnr-dashboard': { id: 'mnr-dashboard', title: 'Home', icon: 'home', showInTabs: true, tabOrder: 1, portal: 'mnr' },
    'mnr-income': { id: 'mnr-income', title: 'Income', icon: 'dollar-sign', showInTabs: true, tabOrder: 2, portal: 'mnr' },
    'mnr-withdrawals': { id: 'mnr-withdrawals', title: 'Withdraw', icon: 'credit-card', showInTabs: true, tabOrder: 3, portal: 'mnr' },
    'mnr-benefits': { id: 'mnr-benefits', title: 'Benefits', icon: 'gift', showInTabs: true, tabOrder: 4, portal: 'mnr' },
    'mnr-profile': { id: 'mnr-profile', title: 'Profile', icon: 'user', showInTabs: true, tabOrder: 5, portal: 'mnr' },
    'mnr-profile-edit': { id: 'mnr-profile-edit', title: 'Edit Profile', icon: 'edit', showInTabs: false, portal: 'mnr' },
    'mnr-earnings': { id: 'mnr-earnings', title: 'Earnings', icon: 'trending-up', showInTabs: false, portal: 'mnr' },
    'mnr-referrals': { id: 'mnr-referrals', title: 'Referrals', icon: 'users', showInTabs: false, portal: 'mnr' },
    'mnr-team': { id: 'mnr-team', title: 'My Team', icon: 'users', showInTabs: false, portal: 'mnr' },
    'mnr-awards': { id: 'mnr-awards', title: 'Awards', icon: 'award', showInTabs: false, portal: 'mnr' },
    'mnr-announcements': { id: 'mnr-announcements', title: 'News', icon: 'bell', showInTabs: false, portal: 'mnr' },
    'mnr-kyc': { id: 'mnr-kyc', title: 'KYC', icon: 'file-text', showInTabs: false, portal: 'mnr' },
    'mnr-bank': { id: 'mnr-bank', title: 'Bank Details', icon: 'credit-card', showInTabs: false, portal: 'mnr' },
    'mnr-change-password': { id: 'mnr-change-password', title: 'Change Password', icon: 'lock', showInTabs: false, portal: 'mnr' },
    'mnr-points': { id: 'mnr-points', title: 'MNR Points', icon: 'star', showInTabs: false, portal: 'mnr' },
    'mnr-coupons': { id: 'mnr-coupons', title: 'EV Coupons', icon: 'tag', showInTabs: false, portal: 'mnr' },
    'mnr-daywise': { id: 'mnr-daywise', title: 'Daywise Income', icon: 'calendar', showInTabs: false, portal: 'mnr' },
    'mnr-ev-discount': { id: 'mnr-ev-discount', title: 'EV Discount', icon: 'zap', showInTabs: false, portal: 'mnr' },
    'mnr-my-announcements': { id: 'mnr-my-announcements', title: 'My Announcements', icon: 'edit', showInTabs: false, portal: 'mnr' },
    'mnr-announcements-pending': { id: 'mnr-announcements-pending', title: 'Pending', icon: 'clock', showInTabs: false, portal: 'mnr' },
    'mnr-announcements-approved': { id: 'mnr-announcements-approved', title: 'Approved', icon: 'check-circle', showInTabs: false, portal: 'mnr' },
    'mnr-announcements-rejected': { id: 'mnr-announcements-rejected', title: 'Rejected', icon: 'x-circle', showInTabs: false, portal: 'mnr' },
    'mnr-create-announcement': { id: 'mnr-create-announcement', title: 'Submit Announcement', icon: 'plus-circle', showInTabs: false, portal: 'mnr' },
    'mnr-my-leads': { id: 'mnr-my-leads', title: 'My Leads', icon: 'users', showInTabs: false, portal: 'mnr' },
    'mnr-feedback': { id: 'mnr-feedback', title: 'Feedback', icon: 'message-circle', showInTabs: false, portal: 'mnr' },
    'mnr-add-member': { id: 'mnr-add-member', title: 'Add Member', icon: 'user-plus', showInTabs: false, portal: 'mnr' },
    'mnr-coupon-buy': { id: 'mnr-coupon-buy', title: 'Buy Coupon', icon: 'shopping-cart', showInTabs: false, portal: 'mnr' },
    'mnr-coupon-activate': { id: 'mnr-coupon-activate', title: 'Activate Coupon', icon: 'zap', showInTabs: false, portal: 'mnr' },
    'mnr-coupon-status': { id: 'mnr-coupon-status', title: 'Coupon Status', icon: 'info', showInTabs: false, portal: 'mnr' },
    'mnr-coupon-transfer': { id: 'mnr-coupon-transfer', title: 'Coupon Transfer', icon: 'send', showInTabs: false, portal: 'mnr' },
    'mnr-coupon-progress': { id: 'mnr-coupon-progress', title: 'Coupon Progress', icon: 'bar-chart', showInTabs: false, portal: 'mnr' },
    'mnr-settings': { id: 'mnr-settings', title: 'Settings', icon: 'settings', showInTabs: false, portal: 'mnr' },
    'mnr-members-all': { id: 'mnr-members-all', title: 'All Members', icon: 'users', showInTabs: false, portal: 'mnr' },
    'mnr-members-picture': { id: 'mnr-members-picture', title: 'Picture View', icon: 'image', showInTabs: false, portal: 'mnr' },
    'mnr-members-ved': { id: 'mnr-members-ved', title: 'Ved Team', icon: 'users', showInTabs: false, portal: 'mnr' },
    'mnr-earnings-summary': { id: 'mnr-earnings-summary', title: 'Earnings Summary', icon: 'pie-chart', showInTabs: false, portal: 'mnr' },
    'mnr-income-direct': { id: 'mnr-income-direct', title: 'Direct Business Facilitation', icon: 'trending-up', showInTabs: false, portal: 'mnr' },
    'mnr-income-matching': { id: 'mnr-income-matching', title: 'Group Performance Recognition', icon: 'git-merge', showInTabs: false, portal: 'mnr' },
    'mnr-income-ved': { id: 'mnr-income-ved', title: 'VED Leadership Recognition', icon: 'layers', showInTabs: false, portal: 'mnr' },
    'mnr-income-guru': { id: 'mnr-income-guru', title: 'Gurudakshina', icon: 'award', showInTabs: false, portal: 'mnr' },
    'mnr-income-field': { id: 'mnr-income-field', title: 'Field Allowance', icon: 'briefcase', showInTabs: false, portal: 'mnr' },
    'mnr-franchise-earnings': { id: 'mnr-franchise-earnings', title: 'Franchise Earnings', icon: 'dollar-sign', showInTabs: false, portal: 'mnr' },
    'mnr-bonanza': { id: 'mnr-bonanza', title: 'Bonanza Awards', icon: 'gift', showInTabs: false, portal: 'mnr' },

    // VGK4U Routes (Phase A1 — read-only foundation, audit task #35 follow-up)
    // NOTE: VGKBirthdays consumes /banners/admin/birthdays/* (staff-only auth),
    //       so its portal is 'staff'. VGKTopEarners uses get_current_user_hybrid
    //       (any authenticated user) and ships under the MNR portal.
    'vgk-birthdays': { id: 'vgk-birthdays', title: 'VGK4U Birthdays', icon: 'cake', showInTabs: false, portal: 'staff' },
    'vgk-top-earners': { id: 'vgk-top-earners', title: 'VGK4U Top Earners', icon: 'trophy', showInTabs: false, portal: 'mnr' },
    'vgk-awards': { id: 'vgk-awards', title: 'VGK4U Awards', icon: 'award', showInTabs: false, portal: 'staff' },
    'vgk-my-registrations': { id: 'vgk-my-registrations', title: 'My VGK Registrations', icon: 'user-check', showInTabs: false, portal: 'staff' },
    'vgk-bonanza-rewards': { id: 'vgk-bonanza-rewards', title: 'Bonanza Cash Rewards', icon: 'trophy', showInTabs: false, portal: 'mnr' },
    'vgk-points-balance': { id: 'vgk-points-balance', title: 'VGK Points Balance', icon: 'star', showInTabs: false, portal: 'mnr' },
    'vgk-member-hub': { id: 'vgk-member-hub', title: 'VGK4U Member Hub', icon: 'grid', showInTabs: false, portal: 'mnr' },
    'vgk-settings': { id: 'vgk-settings', title: 'Notification Settings', icon: 'settings', showInTabs: false, portal: 'mnr' },
    'vgk-bank-details': { id: 'vgk-bank-details', title: 'Bank Details', icon: 'credit-card', showInTabs: false, portal: 'mnr' },
    'vgk-profile-edit': { id: 'vgk-profile-edit', title: 'Edit Profile', icon: 'edit', showInTabs: false, portal: 'mnr' },
    'vgk-kyc': { id: 'vgk-kyc', title: 'KYC Documents', icon: 'file-text', showInTabs: false, portal: 'mnr' },
    'vgk-feedback': { id: 'vgk-feedback', title: 'Submit Feedback', icon: 'message-circle', showInTabs: false, portal: 'mnr' },
    'vgk-announcements': { id: 'vgk-announcements', title: 'Create Announcement', icon: 'bullhorn', showInTabs: false, portal: 'mnr' },
    'vgk-my-announcements': { id: 'vgk-my-announcements', title: 'My Announcements', icon: 'list', showInTabs: false, portal: 'mnr' },
    'vgk-coupon-activate': { id: 'vgk-coupon-activate', title: 'Activate Coupon', icon: 'zap', showInTabs: false, portal: 'mnr' },
    'vgk-coupon-progress': { id: 'vgk-coupon-progress', title: 'Coupon Progress', icon: 'bar-chart-2', showInTabs: false, portal: 'mnr' },
    'vgk-coupon-transfer': { id: 'vgk-coupon-transfer', title: 'Transfer Coupons', icon: 'send', showInTabs: false, portal: 'mnr' },
    'vgk-income-unified': { id: 'vgk-income-unified', title: 'VGK Income — Unified', icon: 'trending-up', showInTabs: false, portal: 'staff' },



    // Zynova Portal
    'zynova-real-estate': { id: 'zynova-real-estate', title: 'Zynova Real Estate', icon: 'home', showInTabs: false, portal: 'mnr' },
    'zynova-insurance': { id: 'zynova-insurance', title: 'Zynova Insurance', icon: 'shield', showInTabs: false, portal: 'mnr' },
    'zynova-training': { id: 'zynova-training', title: 'Zynova Training', icon: 'book', showInTabs: false, portal: 'mnr' },
    
    // MyntReal Portal
    'myntreal-properties': { id: 'myntreal-properties', title: 'Properties', icon: 'building', showInTabs: false, portal: 'mnr' },
    'myntreal-earnings': { id: 'myntreal-earnings', title: 'MyntReal Earnings', icon: 'dollar-sign', showInTabs: false, portal: 'mnr' },
    
    // Partner Portal
    'partner-dashboard': { id: 'partner-dashboard', title: 'Home', icon: 'home', showInTabs: true, tabOrder: 1, portal: 'partner' },
    'partner-orders': { id: 'partner-orders', title: 'Orders', icon: 'package', showInTabs: true, tabOrder: 2, portal: 'partner' },
    'partner-invoices': { id: 'partner-invoices', title: 'Invoices', icon: 'file-text', showInTabs: true, tabOrder: 4, portal: 'partner' },
    'partner-revenue': { id: 'partner-revenue', title: 'Revenue', icon: 'bar-chart', showInTabs: true, tabOrder: 5, portal: 'partner' },
    'partner-profile': { id: 'partner-profile', title: 'Profile', icon: 'user', showInTabs: false, portal: 'partner' },
    'partner-payments': { id: 'partner-payments', title: 'Payments', icon: 'dollar-sign', showInTabs: false, portal: 'partner' },
    'partner-leads': { id: 'partner-leads', title: 'Leads', icon: 'users', showInTabs: false, portal: 'partner' },
    'partner-service': { id: 'partner-service', title: 'Service', icon: 'tool', showInTabs: true, tabOrder: 3, portal: 'partner' },
    'partner-raise-ticket': { id: 'partner-raise-ticket', title: 'Raise Ticket', icon: 'plus-circle', showInTabs: false, portal: 'partner' },
    'partner-new-order': { id: 'partner-new-order', title: 'New Order', icon: 'plus', showInTabs: false, portal: 'partner' },
    'partner-ticket-history': { id: 'partner-ticket-history', title: 'Ticket History', icon: 'clock', showInTabs: false, portal: 'partner' },
    'partner-kyc-documents': { id: 'partner-kyc-documents', title: 'KYC Documents', icon: 'file-text', showInTabs: false, portal: 'partner' },
    'partner-spare-orders': { id: 'partner-spare-orders', title: 'Spare Parts Orders', icon: 'package', showInTabs: false, portal: 'partner' },
    // Staff Payouts & Incentives
    'staff-my-payouts': { id: 'staff-my-payouts', title: 'Performance Payouts', icon: 'dollar-sign', showInTabs: false, portal: 'staff' },
    'staff-my-lead-incentives': { id: 'staff-my-lead-incentives', title: 'Lead Incentives', icon: 'trending-up', showInTabs: false, portal: 'staff' }
  };

  private routeParams: Record<string, string> = {};

  navigate(route: PageRoute, params?: Record<string, string> | boolean, addToHistory: boolean = true): void {
    if (typeof params === 'boolean') {
      addToHistory = params;
      params = undefined;
    }
    if (addToHistory && this.currentRoute !== route) {
      this.history.push(this.currentRoute);
    }
    this.currentRoute = route;
    this.routeParams = params || {};
    this.notifyListeners();
  }

  goBack(): boolean {
    if (this.history.length > 0) {
      const previousRoute = this.history.pop()!;
      this.currentRoute = previousRoute;
      this.notifyListeners();
      return true;
    }
    return false;
  }

  getCurrentRoute(): PageRoute {
    return this.currentRoute;
  }

  getRouteParams(): Record<string, string> {
    return this.routeParams;
  }

  getRouteConfig(route: PageRoute): RouteConfig {
    return this.routes[route];
  }

  getTabRoutes(portal: 'staff' | 'mnr' | 'partner' = 'staff'): RouteConfig[] {
    return Object.values(this.routes)
      .filter(r => r.showInTabs && r.portal === portal)
      .sort((a, b) => (a.tabOrder || 99) - (b.tabOrder || 99));
  }

  onRouteChange(callback: (route: PageRoute) => void): () => void {
    this.listeners.push(callback);
    return () => {
      this.listeners = this.listeners.filter(l => l !== callback);
    };
  }

  private notifyListeners(): void {
    this.listeners.forEach(cb => cb(this.currentRoute));
  }

  reset(portal: 'staff' | 'mnr' | 'partner' = 'staff'): void {
    switch (portal) {
      case 'mnr':
        this.currentRoute = 'mnr-dashboard';
        break;
      case 'partner':
        this.currentRoute = 'partner-dashboard';
        break;
      default:
        this.currentRoute = 'dashboard';
    }
    this.history = [];
  }
}

export const routerService = new RouterService();
