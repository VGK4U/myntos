import { routerService, PageRoute } from '../services/router.service';
import { portalService } from '../services/portal.service';
import { authService } from '../services/auth.service';
import { apiService } from '../services/api.service';
import { MENU_MASTER as CANONICAL_MENU_MASTER, SidebarSection, SidebarSubSection, SidebarItem } from '../constants/menu-master';

const ROUTE_PATH_MAP: Record<string, string> = {
  '/staff/dashboard': 'dashboard',
  '/staff/my-attendance': 'attendance',
  '/staff/my-leaves': 'leaves',
  '/staff/leave-approvals': 'staff-leave-approvals',
  '/staff/attendance-records': 'team-attendance',
  '/staff/attendance-sheet': 'staff-attendance-sheet',
  '/staff/attendance-reports': 'staff-attendance-reports',
  '/staff/attendance-exceptions': 'staff-attendance-exceptions',
  '/staff/attendance-computation': 'staff-attendance-computation',
  
  '/staff/tasks/assigned-by-me': 'tasks-assigned',
  '/staff/tasks/assigned-by-me-v2': 'tasks-assigned',
  '/staff/tasks/assigned-to-me': 'tasks-received',
  '/staff/tasks/team-activities': 'staff-team-activities',
  '/staff/tasks/task-tracker': 'staff-task-tracker',
  '/staff/tasks/task-reviews': 'staff-task-reviews',
  '/staff/task-review': 'staff-task-reviews',
  
  '/staff/my-kras': 'kras',
  '/staff/kra-templates': 'staff-kra-templates',
  '/staff/kra-tracking-sheet': 'staff-kra-tracking',
  '/staff/kra-review': 'staff-kra-review',
  
  '/staff/my-timesheet': 'timesheet',
  '/staff/timesheet-approval': 'staff-timesheet-approval',
  
  '/staff/my-journeys': 'journeys',
  '/staff/team-journeys': 'team-journeys',
  '/staff/all-journeys': 'staff-all-journeys',
  '/staff/vgk4u-journeys': 'staff-vgk4u-journeys',
  '/staff/vgk/members': 'staff-vgk-members',
  '/staff_vgk_members.html': 'staff-vgk-members',
  '/staff/incentives/vgk4u': 'staff-incentives-vgk4u',
  '/staff/vgk4u/real-estate': 'staff-vgk4u-real-estate',
  '/staff/vgk4u/insurance': 'staff-vgk4u-insurance',
  '/staff/vgk4u/etc-students': 'staff-vgk4u-real-estate',
  '/staff/incentives/points': 'staff-incentives-points',
  '/staff/incentives/approvals': 'staff-incentives-approvals',
  '/staff/vgk/income': 'staff-vgk-income',
  '/staff/vgk/income-unified': 'vgk-income-unified',
  '/staff/vgk/coupons/available': 'staff-vgk-coupons',
  '/staff/vgk/promo-codes': 'staff-vgk-promo-codes',
  '/staff/vgk/bonanza-management': 'vgk-bonanza-rewards',
  '/staff/vgk/bonanza-claims': 'vgk-bonanza-rewards',
  '/staff/vgk/vendors': 'staff-vgk-vendors',
  '/staff/vgk/vendor-categories': 'staff-vgk-vendors',
  '/staff/vgk/vendor-products': 'staff-vgk-vendors',
  '/staff/vgk/vendor-transactions': 'staff-vgk-vendors',
  '/staff/vgk/cash-income/sales': 'staff-vgk-income',
  '/staff/vgk/cash-income/accounts': 'staff-vgk-income',
  '/staff/vgk/wallet': 'vgk-points-balance',
  '/staff/vgk/config': 'staff-vgk-members',
  '/staff/vgk/partner-kyc-review': 'staff-kyc-approvals',
  '/staff/vgk/my-registrations': 'vgk-my-registrations',
  '/staff/vgk/media': 'vgk-member-hub',
  '/staff/vgk4u/purchase-orders': 'staff-service-procurement',
  '/rvz/real-dreams/marketplace': 'real-dreams-marketplace',
  '/rvz/real-dreams': 'real-dreams-marketplace',
  '/rvz/real-dreams/partners': 'real-dreams-marketplace',
  '/rvz/real-dreams-partners': 'real-dreams-marketplace',
  '/rvz/real-dreams/properties': 'real-dreams-marketplace',
  '/rvz/real-dreams-properties': 'real-dreams-marketplace',
  '/rvz/real-dreams-dashboard': 'real-dreams-marketplace',
  '/staff/mnr/real-dreams/marketplace': 'real-dreams-marketplace',
  '/staff/mnr/real-dreams': 'real-dreams-marketplace',
  '/staff/mnr/real-dreams/partners': 'real-dreams-marketplace',
  '/staff/mnr/real-dreams/properties': 'real-dreams-marketplace',
  '/staff/mnr/real-dreams-dashboard': 'real-dreams-marketplace',
  '/real-dreams/marketplace': 'real-dreams-marketplace',
  '/real-dreams/compare': 'real-dreams-marketplace',
  '/real-dreams/property': 'real-dreams-marketplace',
  '/staff/zynova/direct': 'vgk-direct-summary',
  '/staff/zynova/matching': 'vgk-matching-summary',
  '/staff/zynova/guru': 'vgk-guru-summary',
  '/staff/zynova/ved': 'vgk-ved-summary',
  '/staff/zynova/wallet': 'vgk-points-balance',
  '/staff/zynova/withdrawals': 'vgk-points-balance',
  '/staff/zynova/points': 'vgk-points-balance',
  '/staff/kra-status': 'kras',
  '/staff/timesheet': 'timesheet',
  '/staff/progress': 'progress',

  // VGK Member module routes
  '/vgk/birthdays': 'vgk-birthdays',
  '/vgk/top-earners': 'vgk-top-earners',
  '/vgk/awards': 'vgk-awards',
  '/vgk/my-registrations': 'vgk-my-registrations',
  '/vgk/bonanza-rewards': 'vgk-bonanza-rewards',
  '/vgk/points-balance': 'vgk-points-balance',
  '/vgk/member-hub': 'vgk-member-hub',
  '/vgk/settings': 'vgk-settings',
  '/vgk/bank-details': 'vgk-bank-details',
  '/vgk/profile-edit': 'vgk-profile-edit',
  '/vgk/kyc': 'vgk-kyc',
  '/vgk/feedback': 'vgk-feedback',
  '/vgk/announcements': 'vgk-announcements',
  '/vgk/my-announcements': 'vgk-my-announcements',
  '/vgk/coupon-activate': 'vgk-coupon-activate',
  '/vgk/coupon-progress': 'vgk-coupon-progress',
  '/vgk/coupon-transfer': 'vgk-coupon-transfer',
  '/vgk/income-unified': 'vgk-income-unified',
  '/vgk/daywise-income': 'vgk-daywise-income',
  '/vgk/income-types': 'vgk-income-types',
  '/vgk/direct-summary': 'vgk-direct-summary',
  '/vgk/matching-summary': 'vgk-matching-summary',
  '/vgk/guru-summary': 'vgk-guru-summary',
  '/vgk/ved-summary': 'vgk-ved-summary',
  '/vgk/ev-benefits': 'vgk-ev-benefits',
  '/vgk/ev-discount': 'vgk-ev-discount',
  '/vgk/franchise-earnings': 'vgk-franchise-earnings',
  '/vgk/insurance': 'vgk-insurance',
  '/vgk/training': 'vgk-training',
  '/vgk/coupon-benefits': 'vgk-coupon-benefits',
  '/vgk/my-submissions': 'vgk-my-submissions',
  
  '/staff/my-reimbursement-claims': 'reimbursements',
  '/staff/reimbursement-approvals': 'staff-reimbursement-approvals',
  '/staff/accounts/my-reimbursements': 'reimbursements',
  '/staff/accounts/reimbursement-approvals': 'staff-reimbursement-approvals',
  '/staff/accounts/expense-entries': 'staff-expense-entries',
  
  '/staff/my-earnings': 'staff-my-earnings',
  '/staff/payroll-profile': 'staff-payroll-profile',
  '/staff/salary-slips': 'staff-salary-slips',
  
  '/staff/my-leads': 'staff-my-leads',
  '/staff/leads': 'staff-leads',
  '/staff/team-leads': 'staff-team-leads',
  '/staff/lead-sources': 'staff-lead-sources',
  '/staff/bank-wise-leads': 'staff-bank-wise-leads',
  '/staff/crm/bank-wise-leads': 'staff-bank-wise-leads',
  '/staff/field-sales': 'staff-bank-wise-leads',
  '/field-sales': 'staff-bank-wise-leads',
  'field-sales': 'staff-bank-wise-leads',
  'bank-wise-leads': 'staff-bank-wise-leads',
  '/staff/solar-leads': 'category-leads-master',
  '/staff/real-dreams-leads': 'category-leads-master',
  '/staff/insurance-leads': 'category-leads-master',
  '/staff/ev-b2b-leads': 'category-leads-master',
  '/staff/ev-b2c-leads': 'category-leads-master',
  '/staff/ev-spares-leads': 'category-leads-master',
  '/staff/etc-leads': 'category-leads-master',
  '/staff/mnr-leads': 'category-leads-master',
  '/staff/mnr-leads-master': 'category-leads-master',
  '/staff/executive-dashboard': 'executive-dashboard',
  '/staff/crm/whatsapp-inbox': 'staff-whatsapp',
  '/staff/crm/wa-inbox': 'staff-whatsapp',
  '/staff/whatsapp': 'staff-whatsapp',
  '/staff/whatsapp-inbox': 'staff-whatsapp',
  '/staff/whatsapp-center': 'staff-whatsapp',
  '/staff/crm/whatsapp-center': 'staff-whatsapp',
  '/staff/crm/whatsapp': 'staff-whatsapp',
  '/staff/configuration/catalog': 'digital-catalog',
  '/staff/catalog-library': 'digital-catalog',
  '/staff/catalog': 'digital-catalog',
  '/catalog-library': 'digital-catalog',
  'catalog-library': 'digital-catalog',
  '/staff/catalog-library.html': 'digital-catalog',
  '/catalog-library.html': 'digital-catalog',
  '/catalog': 'digital-catalog',
  'catalog': 'digital-catalog',
  
  '/staff/call-tracking': 'staff-call-tracking',
  '/staff/vendors': 'staff-vendors',
  '/staff/zynova-real-estate': 'staff-zynova-real-estate',
  '/staff/zynova': 'staff-zynova',
  '/staff/zynova-insurance': 'staff-zynova-insurance',
  '/staff/settings': 'settings',
  '/staff/change-password': 'change-password',
  '/staff/employees': 'staff-employees',
  '/staff/training-videos': 'staff-training-videos',
  '/staff/employee-directory': 'staff-directory',
  '/staff/kyc-approvals': 'staff-kyc-approvals',
  '/staff/manager-review': 'staff-review',
  '/staff/auto-dialer': 'auto-dialer',
  '/staff/call-history': 'call-history',
  '/staff/operator-calls': 'operator-calls',
  '/staff/day-planner': 'day-planner',
  '/staff/tasks/day-planner': 'day-planner',
  '/staff/service': 'staff-service',
  '/staff/crm': 'staff-crm',
  '/staff/crm/dashboard': 'staff-crm',
  '/staff/crm/team-leads': 'staff-team-leads',
  '/staff/crm/lead-sources': 'staff-lead-sources',
  '/staff/call-management': 'staff-call-tracking',
  '/staff/dialer': 'auto-dialer',
  '/staff/softphone': 'softphone',
  '/staff/calling-page': 'softphone',
  '/staff/calling': 'softphone',
  '/staff/phone-dialpad': 'softphone',
  '/staff/softphone-hub': 'softphone',
  '/staff/tasks/tracker': 'staff-task-tracker',
  '/staff/service-tickets/dashboard': 'staff-service',
  '/staff/service-tickets/performance': 'staff-service-performance',
  '/staff/service-tickets/procurement': 'staff-service-procurement',
  '/staff/service-tickets/procurement-queue': 'staff-service-procurement-queue',
  '/staff/service-tickets/raise': 'staff-tickets',
  '/staff/service-tickets/reports': 'staff-service-reports',
  '/staff/service-tickets/queue': 'staff-service-queue',
  '/staff/service-center-revenue': 'staff-service-revenue',
};

const TAB_MAP: Record<string, string> = {
  '/staff/solar-leads': 'solar',
  '/staff/ev-b2b-leads': 'ev-b2b',
  '/staff/ev-b2c-leads': 'ev-b2c',
  '/staff/ev-spares-leads': 'ev-spares',
  '/staff/real-dreams-leads': 'real-dreams',
  '/staff/insurance-leads': 'insurance',
  '/staff/etc-leads': 'etc',
  '/staff/mnr-leads': 'mnr',
};

interface MenuItem {
  menu_code: string;
  label: string;
  route: string;
  tab?: string;
}

interface SubSection {
  sub_section_code: string;
  sub_section_label: string;
  items: MenuItem[];
}

interface MenuSection {
  section_code: string;
  section_label: string;
  order: number;
  items?: MenuItem[];
  subSections?: SubSection[];
}

// Top-level menu items (no section header)
const TOP_MENU_ITEMS: MenuItem[] = [
  { menu_code: "HOME", label: "Home", route: "dashboard" },
  { menu_code: "PROGRESS_DASHBOARD", label: "Progress Dashboard", route: "progress" },
  { menu_code: "DAY_PLANNER", label: "Day Planner", route: "day-planner" }
];

const VGK_TOP_MENU_ITEMS: MenuItem[] = [
  { menu_code: "VGK_DASHBOARD", label: `<i class="fas fa-home" style="margin-right: 8px; width: 18px; text-align: center;"></i> Dashboard`, route: "vgk-member-hub", tab: "earnings" },
  { menu_code: "VGK_PROFILE", label: `<i class="fas fa-user" style="margin-right: 8px; width: 18px; text-align: center;"></i> Profile`, route: "vgk-member-hub", tab: "profile" },
  { menu_code: "VGK_MYCARD", label: `<i class="fas fa-id-card" style="margin-right: 8px; width: 18px; text-align: center;"></i> My Card &amp; Progress`, route: "vgk-member-hub", tab: "mycard" },
  { menu_code: "VGK_ADDMEMBER", label: `<i class="fas fa-user-plus" style="margin-right: 8px; width: 18px; text-align: center;"></i> Add Channel Partner`, route: "vgk-member-hub", tab: "addmember" },
  { menu_code: "VGK_COUPONS", label: `<i class="fas fa-ticket-alt" style="margin-right: 8px; width: 18px; text-align: center;"></i> Coupons`, route: "vgk-member-hub", tab: "coupons" },
  { menu_code: "VGK_NETWORK", label: `<i class="fas fa-sitemap" style="margin-right: 8px; width: 18px; text-align: center;"></i> Team`, route: "vgk-member-hub", tab: "network" },
  { menu_code: "VGK_POINTS", label: `<i class="fas fa-coins" style="margin-right: 8px; width: 18px; text-align: center;"></i> Points Balance`, route: "vgk-member-hub", tab: "points" },
  { menu_code: "VGK_LEDGER", label: `<i class="fas fa-rupee-sign" style="margin-right: 8px; width: 18px; text-align: center;"></i> My Earnings`, route: "vgk-member-hub", tab: "ledger" },
  { menu_code: "VGK_LEADS", label: `<i class="fas fa-user-tag" style="margin-right: 8px; width: 18px; text-align: center;"></i> My Leads`, route: "vgk-member-hub", tab: "leads" },
  { menu_code: "VGK_TICKETS", label: `<i class="fas fa-tools" style="margin-right: 8px; width: 18px; text-align: center;"></i> Service Tickets`, route: "vgk-member-hub", tab: "tickets" },
  { menu_code: "VGK_BONANZA", label: `<i class="fas fa-trophy" style="margin-right: 8px; width: 18px; text-align: center;"></i> Bonanza Rewards`, route: "vgk-member-hub", tab: "bonanza" },
  { menu_code: "VGK_VENDORS", label: `<i class="fas fa-store" style="margin-right: 8px; width: 18px; text-align: center;"></i> Vendor Shops`, route: "vgk-member-hub", tab: "vendors" },
  { menu_code: "VGK_MEDIA", label: `<i class="fas fa-photo-video" style="margin-right: 8px; width: 18px; text-align: center;"></i> Media Hub`, route: "vgk-member-hub", tab: "media" },
  { menu_code: "VGK_ORDERS", label: `<i class="fas fa-box" style="margin-right: 8px; width: 18px; text-align: center;"></i> Orders`, route: "vgk-member-hub", tab: "orders" }
];

const VGK_MENU_MASTER: MenuSection[] = [
  {
    section_code: "EARNINGS",
    section_label: "EARNINGS & INCOME",
    order: 1,
    items: [
      { menu_code: "VGK_INCOME_UNIFIED", label: `<i class="fas fa-chart-line" style="margin-right: 8px; width: 18px; text-align: center; color: #10b981;"></i>Income Dashboard`, route: "vgk-income-unified" },
      { menu_code: "VGK_DAYWISE_INCOME", label: `<i class="fas fa-calendar-day" style="margin-right: 8px; width: 18px; text-align: center; color: #3b82f6;"></i>Daywise Income`, route: "vgk-daywise-income" },
      { menu_code: "VGK_DIRECT_SUMMARY", label: `<i class="fas fa-users" style="margin-right: 8px; width: 18px; text-align: center; color: #6366f1;"></i>Direct (L1)`, route: "vgk-direct-summary" },
      { menu_code: "VGK_MATCHING_SUMMARY", label: `<i class="fas fa-sitemap" style="margin-right: 8px; width: 18px; text-align: center; color: #8b5cf6;"></i>Matching (L2)`, route: "vgk-matching-summary" },
      { menu_code: "VGK_GURU_SUMMARY", label: `<i class="fas fa-graduation-cap" style="margin-right: 8px; width: 18px; text-align: center; color: #ec4899;"></i>Guru Summary`, route: "vgk-guru-summary" },
      { menu_code: "VGK_VED_SUMMARY", label: `<i class="fas fa-brain" style="margin-right: 8px; width: 18px; text-align: center; color: #f59e0b;"></i>Ved Summary`, route: "vgk-ved-summary" },
      { menu_code: "VGK_FRANCHISE_EARNINGS", label: `<i class="fas fa-store" style="margin-right: 8px; width: 18px; text-align: center; color: #14b8a6;"></i>Franchise Earnings`, route: "vgk-franchise-earnings" }
    ]
  },
  {
    section_code: "PROGRAMS",
    section_label: "PROGRAMS & BENEFITS",
    order: 2,
    items: [
      { menu_code: "VGK_EV_BENEFITS", label: `<i class="fas fa-charging-station" style="margin-right: 8px; width: 18px; text-align: center; color: #10b981;"></i>EV Benefits`, route: "vgk-ev-benefits" },
      { menu_code: "VGK_EV_DISCOUNT", label: `<i class="fas fa-percent" style="margin-right: 8px; width: 18px; text-align: center; color: #06b6d4;"></i>EV Discount`, route: "vgk-ev-discount" },
      { menu_code: "VGK_INSURANCE", label: `<i class="fas fa-shield-alt" style="margin-right: 8px; width: 18px; text-align: center; color: #3b82f6;"></i>Insurance Policy`, route: "vgk-insurance" },
      { menu_code: "VGK_TRAINING", label: `<i class="fas fa-chalkboard-teacher" style="margin-right: 8px; width: 18px; text-align: center; color: #8b5cf6;"></i>Training Program`, route: "vgk-training" },
      { menu_code: "VGK_BONANZA_REWARDS", label: `<i class="fas fa-trophy" style="margin-right: 8px; width: 18px; text-align: center; color: #f59e0b;"></i>Bonanza Rewards`, route: "vgk-bonanza-rewards" },
      { menu_code: "VGK_AWARDS", label: `<i class="fas fa-award" style="margin-right: 8px; width: 18px; text-align: center; color: #eab308;"></i>Awards & Milestones`, route: "vgk-awards" }
    ]
  },
  {
    section_code: "COUPONS_PINS",
    section_label: "COUPONS & PINS",
    order: 3,
    items: [
      { menu_code: "VGK_COUPON_ACTIVATE", label: `<i class="fas fa-key" style="margin-right: 8px; width: 18px; text-align: center; color: #6366f1;"></i>PIN Activation`, route: "vgk-coupon-activate" },
      { menu_code: "VGK_COUPON_PROGRESS", label: `<i class="fas fa-tasks" style="margin-right: 8px; width: 18px; text-align: center; color: #3b82f6;"></i>Coupon Progress`, route: "vgk-coupon-progress" },
      { menu_code: "VGK_COUPON_TRANSFER", label: `<i class="fas fa-exchange-alt" style="margin-right: 8px; width: 18px; text-align: center; color: #10b981;"></i>Coupon Transfer`, route: "vgk-coupon-transfer" },
      { menu_code: "VGK_COUPON_BENEFITS", label: `<i class="fas fa-gift" style="margin-right: 8px; width: 18px; text-align: center; color: #ec4899;"></i>Coupon Benefits`, route: "vgk-coupon-benefits" }
    ]
  },
  {
    section_code: "PROFILE_SECURITY",
    section_label: "MY ACCOUNT",
    order: 4,
    items: [
      { menu_code: "VGK_PROFILE_EDIT", label: `<i class="fas fa-user-edit" style="margin-right: 8px; width: 18px; text-align: center; color: #3b82f6;"></i>Edit Profile`, route: "vgk-profile-edit" },
      { menu_code: "VGK_KYC", label: `<i class="fas fa-id-card" style="margin-right: 8px; width: 18px; text-align: center; color: #10b981;"></i>KYC Verification`, route: "vgk-kyc" },
      { menu_code: "VGK_BANK_DETAILS", label: `<i class="fas fa-university" style="margin-right: 8px; width: 18px; text-align: center; color: #f59e0b;"></i>Bank Details`, route: "vgk-bank-details" },
      { menu_code: "VGK_POINTS_BALANCE", label: `<i class="fas fa-coins" style="margin-right: 8px; width: 18px; text-align: center; color: #eab308;"></i>Points Balance`, route: "vgk-points-balance" },
      { menu_code: "VGK_FEEDBACK", label: `<i class="fas fa-comment-dots" style="margin-right: 8px; width: 18px; text-align: center; color: #06b6d4;"></i>Feedback`, route: "vgk-feedback" },
      { menu_code: "VGK_SETTINGS", label: `<i class="fas fa-cog" style="margin-right: 8px; width: 18px; text-align: center; color: #64748b;"></i>Settings`, route: "vgk-settings" }
    ]
  },
  {
    section_code: "COMMUNITY",
    section_label: "COMMUNITY & TEAM",
    order: 5,
    items: [
      { menu_code: "VGK_TOP_EARNERS", label: `<i class="fas fa-medal" style="margin-right: 8px; width: 18px; text-align: center; color: #f59e0b;"></i>Top Earners`, route: "vgk-top-earners" },
      { menu_code: "VGK_BIRTHDAYS", label: `<i class="fas fa-birthday-cake" style="margin-right: 8px; width: 18px; text-align: center; color: #ec4899;"></i>Birthdays`, route: "vgk-birthdays" },
      { menu_code: "VGK_ANNOUNCEMENTS", label: `<i class="fas fa-bullhorn" style="margin-right: 8px; width: 18px; text-align: center; color: #3b82f6;"></i>Announcements`, route: "vgk-announcements" },
      { menu_code: "VGK_MY_REGISTRATIONS", label: `<i class="fas fa-user-plus" style="margin-right: 8px; width: 18px; text-align: center; color: #10b981;"></i>My Registrations`, route: "vgk-my-registrations" },
      { menu_code: "VGK_MY_SUBMISSIONS", label: `<i class="fas fa-file-invoice" style="margin-right: 8px; width: 18px; text-align: center; color: #8b5cf6;"></i>My Submissions`, route: "vgk-my-submissions" }
    ]
  }
];

export class SideDrawer {
  private container: HTMLElement | null = null;
  private overlay: HTMLElement | null = null;
  private isOpen = false;
  private expandedSections: Set<string> = new Set();
  private allowedPaths: Set<string> | '*' = '*';
  private isSupremeStaff: boolean = false;
  private isStaffMenuLoaded = false;

  constructor() {
    try {
      const cachedSupreme = localStorage.getItem('mnr_staff_is_supreme_cache');
      if (cachedSupreme === 'true') {
        this.isSupremeStaff = true;
        this.allowedPaths = '*';
        this.isStaffMenuLoaded = true;
      } else {
        const cachedPaths = localStorage.getItem('mnr_staff_allowed_paths_cache');
        if (cachedPaths) {
          const parsed = JSON.parse(cachedPaths);
          if (Array.isArray(parsed)) {
            this.allowedPaths = new Set(parsed);
            this.isStaffMenuLoaded = true;
          }
        }
      }
    } catch (e) {}

    this.createElements();
    this.loadStaffMenus();
    
    window.addEventListener('logout', () => {
      this.allowedPaths = '*';
      this.isSupremeStaff = false;
      this.isStaffMenuLoaded = false;
      try {
        localStorage.removeItem('mnr_staff_allowed_paths_cache');
        localStorage.removeItem('mnr_staff_is_supreme_cache');
        localStorage.removeItem('mnr_staff_menu_tree_cache');
      } catch (e) {}
      this.updateUI();
    });

    window.addEventListener('auth-changed', () => {
      this.isStaffMenuLoaded = false;
      this.loadStaffMenus();
    });
  }

  private createElements(): void {
    this.overlay = document.createElement('div');
    this.overlay.className = 'drawer-overlay';
    this.overlay.addEventListener('click', () => this.close());
    document.body.appendChild(this.overlay);

    this.container = document.createElement('div');
    this.container.className = 'side-drawer';
    this.container.innerHTML = this.render();
    document.body.appendChild(this.container);

    if (!document.getElementById('myntos-drawer-styles')) {
      const style = document.createElement('style');
      style.id = 'myntos-drawer-styles';
      style.textContent = `
        .side-drawer { position: fixed; top: 0; left: 0; width: 290px; height: 100vh; background: #0f172a; color: #fff; z-index: 9999; transform: translateX(-100%); transition: transform 0.25s ease-in-out; will-change: transform; overflow-y: auto; box-shadow: 2px 0 16px rgba(0,0,0,0.5); }
        .side-drawer.open { transform: translateX(0); }
        .drawer-overlay { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(0,0,0,0.6); z-index: 9998; opacity: 0; pointer-events: none; transition: opacity 0.25s ease-in-out; will-change: opacity; }
        .drawer-overlay.visible { opacity: 1; pointer-events: auto; }
        .drawer-header { display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; border-bottom: 1px solid rgba(255,255,255,0.08); }
        .drawer-logo .logo-text { font-size: 1.1rem; font-weight: 700; color: #38bdf8; }
        .drawer-close { background: none; border: none; color: #94a3b8; cursor: pointer; padding: 4px; }
        .drawer-content { padding: 10px 0 40px; }
        .top-menu-items { border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 8px; margin-bottom: 8px; }
        .menu-item.top-item { display: flex; align-items: center; padding: 10px 20px; font-size: 13.5px; font-weight: 600; color: #f1f5f9; cursor: pointer; transition: background 0.15s; }
        .menu-item.top-item:active { background: rgba(59,130,246,0.2); color: #38bdf8; }
        .drawer-section { border-bottom: 1px solid rgba(255,255,255,0.05); }
        .section-header { display: flex; justify-content: space-between; align-items: center; padding: 13px 20px; font-size: 12.5px; font-weight: 700; color: #94a3b8; letter-spacing: 0.5px; cursor: pointer; user-select: none; }
        .section-header:active { background: rgba(255,255,255,0.05); color: #fff; }
        .section-arrow { transition: transform 0.2s; }
        .drawer-subsection { padding-left: 8px; border-left: 2px solid rgba(255,255,255,0.05); margin-left: 16px; margin-bottom: 4px; }
        .subsection-header { display: flex; justify-content: space-between; align-items: center; padding: 9px 16px; font-size: 12px; font-weight: 600; color: #cbd5e1; cursor: pointer; }
        .drawer-menu-item { display: flex; align-items: center; padding: 9px 24px; font-size: 13px; color: #e2e8f0; text-decoration: none; cursor: pointer; transition: background 0.15s; }
        .drawer-menu-item:active { background: rgba(59,130,246,0.2); color: #38bdf8; }
        .drawer-menu-item .menu-label { display: flex; align-items: center; }
        .drawer-menu-item .menu-label i { font-size: 14px; margin-right: 10px; width: 18px; text-align: center; color: #38bdf8; }
      `;
      document.head.appendChild(style);
    }

    this.attachEventListeners();
  }

  private render(): string {
    const portal = portalService.getPortal();
    const isVgk = portal === 'vgk';
    const authState = authService.getAuthState();
    const user = (authState.user || {}) as any;
    const roleCode = (user.role_code || user.role?.role_code || user.user_type || '').toString().toLowerCase().trim();
    const roleName = (user.role_name || user.role?.role_name || '').toString().toUpperCase().trim();
    const staffType = (user.staff_type || '').toString().toUpperCase().trim();
    const isManagerOrEa = (
      ['vgk4u', 'vgk4u_supreme', 'key_leadership', 'ea', 'executive_admin', 'manager', 'director', 'admin'].includes(roleCode) ||
      roleCode.includes('vgk') || roleCode.includes('manager') || roleCode.includes('lead') ||
      ['VGK4U', 'VGK4U SUPREME', 'VGK MENTOR', 'KEY LEADERSHIP', 'EA', 'EXECUTIVE ADMIN', 'MANAGER'].includes(roleName) ||
      roleName.includes('VGK') || roleName.includes('MANAGER') ||
      ['VGK4U', 'VGK4U SUPREME'].includes(staffType) ||
      Boolean(user.is_manager || user.is_admin || user.is_super_admin)
    );
    
    let topItems = TOP_MENU_ITEMS;
    if (isVgk) {
      topItems = VGK_TOP_MENU_ITEMS;
    } else if (portal === 'staff') {
      const showOverview = (
        ['vgk4u', 'vgk4u_supreme', 'key_leadership', 'ea', 'executive_admin'].includes(roleCode) ||
        roleCode.includes('vgk') ||
        ['VGK4U', 'VGK4U SUPREME', 'VGK MENTOR', 'KEY LEADERSHIP', 'EA', 'EXECUTIVE ADMIN'].includes(roleName) ||
        roleName.includes('VGK') ||
        ['VGK4U', 'VGK4U SUPREME'].includes(staffType)
      );

      const isRestrictedFreelancer = user.staff_type === 'FREELANCER' && user.freelancer_access_mode === 'only_leads';

      if (isRestrictedFreelancer) {
        topItems = [];
      } else {
        topItems = [
          { menu_code: "PROGRESS", label: `<i class="fas fa-chart-line" style="margin-right: 8px; width: 18px; text-align: center;"></i> Progress`, route: "progress" },
          ...(showOverview ? [{ menu_code: "OVERVIEW", label: `<i class="fas fa-th" style="margin-right: 8px; width: 18px; text-align: center;"></i> Overview`, route: "dashboard" }] : []),
          { menu_code: "TASK_PLANNER", label: `<i class="fas fa-calendar-day" style="margin-right: 8px; width: 18px; text-align: center;"></i> Task Planner`, route: "day-planner" },
          { menu_code: "KRA_STATUS", label: `<i class="fas fa-chart-bar" style="margin-right: 8px; width: 18px; text-align: center;"></i> KRA Status`, route: "kras" },
          { menu_code: "TIME_SHEET", label: `<i class="fas fa-clock" style="margin-right: 8px; width: 18px; text-align: center;"></i> Time Sheet`, route: "timesheet" },
          { menu_code: "WHATSAPP_CENTER", label: `<i class="fab fa-whatsapp" style="margin-right: 8px; width: 18px; text-align: center; color: #25d366;"></i> WhatsApp Center`, route: "staff-whatsapp" },
          { menu_code: "AUTO_DIALER", label: `<i class="fas fa-phone-volume" style="margin-right: 8px; width: 18px; text-align: center; color: #38bdf8;"></i> Auto Dialer`, route: "auto-dialer" },
          { menu_code: "CALLING_PAGE", label: `<i class="fas fa-headset" style="margin-right: 8px; width: 18px; text-align: center; color: #3b82f6;"></i> Calling & Softphone`, route: "softphone" }
        ];
      }
    }

    const isAccountsStaff = (
      ['account', 'accounts', 'finance', 'payroll', 'billing', 'bookkeeper', 'auditor'].some(r => roleCode.includes(r)) ||
      ['ACCOUNT', 'ACCOUNTS', 'FINANCE', 'PAYROLL', 'BILLING', 'BOOKKEEPER', 'AUDITOR'].some(r => roleName.includes(r)) ||
      ['ACCOUNT', 'ACCOUNTS', 'FINANCE', 'PAYROLL', 'BILLING', 'BOOKKEEPER', 'AUDITOR'].some(r => staffType.includes(r)) ||
      ['ACCOUNT', 'ACCOUNTS', 'FINANCE', 'PAYROLL'].some(r => (user.department || user.department_name || '').toString().toUpperCase().includes(r))
    );

    const isAllowedAccounts = isManagerOrEa || isAccountsStaff;

    const menuMaster = isVgk ? VGK_MENU_MASTER : this.getStaffMenuMaster();

    return `
      <div class="drawer-header">
        <div class="drawer-logo">
          <span class="logo-text">WORKFLOWS</span>
        </div>
        <button class="drawer-close" id="drawerClose">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"/>
            <line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>
      <div class="drawer-content">
        <!-- Top menu items (Home, Progress) without section header -->
        <div class="top-menu-items">
          ${topItems.map(item => `
            <div class="menu-item top-item" data-route="${item.route}" ${item.tab ? `data-tab="${item.tab}"` : ''}>
              <span class="menu-label">${item.label}</span>
            </div>
          `).join('')}
        </div>
        <!-- Section menus -->
        ${menuMaster.map(section => this.renderSection(section)).join('')}
        
        ${isVgk ? `
          <div class="drawer-divider" style="height: 1px; background: rgba(255,255,255,0.1); margin: 12px 16px;"></div>
          <div class="menu-item top-item logout-item" id="drawerLogout" style="color: #ef4444; cursor: pointer; display: flex; align-items: center; padding: 12px 24px;">
            <span class="menu-label" style="display: flex; align-items: center; gap: 8px; font-weight: 500; font-size: 1rem;">
              <i class="fas fa-sign-out-alt" style="width: 18px; text-align: center;"></i> Logout
            </span>
          </div>
        ` : ''}
      </div>
    `;
  }

  private renderSection(section: MenuSection): string {
    const isExpanded = this.expandedSections.has(section.section_code);
    const hasSubSections = section.subSections && section.subSections.length > 0;
    const hasItems = section.items && section.items.length > 0;

    if (!hasSubSections && !hasItems) {
      return '';
    }

    return `
      <div class="drawer-section" data-section="${section.section_code}">
        <div class="section-header" data-toggle="${section.section_code}">
          <span class="section-title">${section.section_label}</span>
          <svg class="section-arrow" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">${isExpanded ? '<polyline points="6 9 12 15 18 9"/>' : '<polyline points="9 18 15 12 9 6"/>'}</svg>
        </div>
        <div class="section-items ${isExpanded ? 'expanded' : ''}" style="display: ${isExpanded ? 'block' : 'none'};">
          ${hasItems ? section.items!.map(item => this.renderMenuItem(item)).join('') : ''}
          ${hasSubSections ? section.subSections!.map(sub => this.renderSubSection(sub)).join('') : ''}
        </div>
      </div>
    `;
  }

  private renderSubSection(sub: SubSection): string {
    const isExpanded = this.expandedSections.has(sub.sub_section_code);
    return `
      <div class="drawer-subsection">
        <div class="subsection-header" data-toggle="${sub.sub_section_code}">
          <span class="subsection-title">${sub.sub_section_label}</span>
          <svg class="section-arrow" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">${isExpanded ? '<polyline points="6 9 12 15 18 9"/>' : '<polyline points="9 18 15 12 9 6"/>'}</svg>
        </div>
        <div class="subsection-items ${isExpanded ? 'expanded' : ''}" style="display: ${isExpanded ? 'block' : 'none'};">
          ${sub.items.map(item => this.renderMenuItem(item)).join('')}
        </div>
      </div>
    `;
  }

  private renderMenuItem(item: MenuItem): string {
    return `
      <a class="drawer-menu-item" data-route="${item.route}"${item.tab ? ` data-tab="${item.tab}"` : ''}>
        <span class="menu-label">${item.label}</span>
      </a>
    `;
  }

  private attachEventListeners(): void {
    if (!this.container) return;

    document.getElementById('drawerClose')?.addEventListener('click', () => this.close());

    this.container.querySelectorAll('[data-toggle]').forEach(el => {
      el.addEventListener('click', (e) => {
        const code = (el as HTMLElement).dataset.toggle!;
        this.toggleSection(code);
        e.stopPropagation();
      });
    });

    this.container.querySelectorAll('[data-route]').forEach(el => {
      el.addEventListener('click', () => {
        const rawRoute = (el as HTMLElement).dataset.route!;
        const tab = (el as HTMLElement).dataset.tab;
        const rawLabel = (el.querySelector('.menu-label')?.textContent || '').trim();
        
        let targetRoute = ROUTE_PATH_MAP[rawRoute] || ROUTE_PATH_MAP[rawRoute.replace(/\/$/, '')];
        if (!targetRoute && !rawRoute.startsWith('/')) {
          targetRoute = rawRoute;
        }

        if (targetRoute) {
          if (tab) {
            routerService.navigate(targetRoute as PageRoute, { tab });
          } else {
            routerService.navigate(targetRoute as PageRoute);
          }
        } else {
          routerService.navigate('embed-view' as PageRoute, {
            url: rawRoute,
            title: rawLabel || 'Staff Portal',
            tab: tab || ''
          });
        }
        this.close();
      });
    });

    document.getElementById('drawerLogout')?.addEventListener('click', async () => {
      this.close();
      if (confirm('Are you sure you want to logout?')) {
        await authService.logout();
      }
    });
  }

  private toggleSection(code: string): void {
    if (this.expandedSections.has(code)) {
      this.expandedSections.delete(code);
    } else {
      this.expandedSections.add(code);
    }
    this.updateUI();
  }

  private updateUI(): void {
    if (!this.container) return;
    this.container.innerHTML = this.render();
    this.attachEventListeners();
  }

  private async loadStaffMenus(): Promise<void> {
    const authState = authService.getAuthState();
    const user = (authState.user || {}) as any;
    const staffType = (user.staff_type || '').toString().toUpperCase().trim();
    const empCode = (user.emp_code || user.employee_code || '').toString().toUpperCase().trim();
    const roleCode = (user.role_code || user.role?.role_code || user.user_type || '').toString().toLowerCase().trim();
    const roleName = (user.role_name || user.role?.role_name || '').toString().toUpperCase().trim();

    const supremeVariants = [
      "VGK4U_SUPREME", "RVZ_SUPREME", "VGK4U", "VGK4U SUPREME", "VGK4U_EA", 
      "KEY_LEADERSHIP", "KEY LEADERSHIP", "EA", "EXECUTIVE ADMIN", "MANAGER", 
      "DIRECTOR", "SUPER_ADMIN", "ADMIN"
    ];
    
    if (
      supremeVariants.includes(staffType) ||
      ['MR10018', 'MR10001', 'MR10016', 'MR10025'].includes(empCode) ||
      ['key_leadership', 'vgk4u', 'ea', 'vgk4u_supreme', 'executive_admin', 'manager', 'director', 'admin', 'super_admin'].includes(roleCode) ||
      supremeVariants.includes(roleName) ||
      Boolean(user.is_manager || user.is_admin || user.is_super_admin)
    ) {
      this.isSupremeStaff = true;
      this.allowedPaths = '*';
      this.isStaffMenuLoaded = true;
      try {
        localStorage.setItem('mnr_staff_is_supreme_cache', 'true');
      } catch (e) {}
      this.updateUI();
      return;
    }

    try {
      const response = await apiService.get<any>('/staff/menu-settings/my-menus?unified=true');
      if (response.success && response.data) {
        const menus: any[] = response.data.menus || [];
        const paths = new Set<string>(menus.map(m => m.route_path).filter(p => Boolean(p)));
        // Default permitted system/communication routes
        paths.add('/staff/whatsapp-center');
        paths.add('/staff/crm/whatsapp-inbox');
        paths.add('/staff/crm/whatsapp-bot');
        paths.add('/staff/softphone-center');
        paths.add('/staff/softphone-hub');
        paths.add('/staff/softphone');
        paths.add('/staff/dialer');
        paths.add('/staff/auto-dialer');
        paths.add('/staff/my-leads');
        paths.add('/staff/configuration/catalog');
        paths.add('/staff/catalog-library');
        paths.add('/staff/catalog');

        this.allowedPaths = paths;
        this.isSupremeStaff = false;
        this.isStaffMenuLoaded = true;
        try {
          localStorage.setItem('mnr_staff_is_supreme_cache', 'false');
          localStorage.setItem('mnr_staff_allowed_paths_cache', JSON.stringify(Array.from(paths)));
        } catch (e) {}
        this.updateUI();
      }
    } catch (e) {
      console.error('Failed to load dynamic staff menus:', e);
      this.allowedPaths = '*';
      this.updateUI();
    }
  }

  private getItemIcon(code: string, label: string): string {
    const c = (code || '').toUpperCase();
    const l = (label || '').toLowerCase();

    if (c.includes('WHATSAPP') || l.includes('whatsapp')) return 'fab fa-whatsapp';
    if (c.includes('AUTO_DIALER') || l.includes('auto dialer')) return 'fas fa-phone-volume';
    if (c.includes('SOFTPHONE') || l.includes('calling') || l.includes('softphone')) return 'fas fa-headset';
    if (c.includes('CATALOG') || l.includes('catalog')) return 'fas fa-book-open';
    if (c.includes('FIELD_SALES') || l.includes('field sales') || c.includes('BANK_WISE_LEADS')) return 'fas fa-users-gear';
    if (c.includes('SOLAR') || l.includes('solar')) return 'fas fa-solar-panel';
    if (c.includes('EV_') || l.includes('ev ')) return 'fas fa-car';
    if (c.includes('INSURANCE') || l.includes('care') || l.includes('insurance')) return 'fas fa-shield-alt';
    if (c.includes('REAL_DREAMS') || c.includes('REAL_ESTATE') || l.includes('real dreams') || l.includes('real estate') || l.includes('property')) return 'fas fa-building';
    if (c.includes('ETC') || l.includes('training') || l.includes('student')) return 'fas fa-graduation-cap';
    if (c.includes('BONANZA') || l.includes('bonanza')) return 'fas fa-trophy';
    if (c.includes('COUPON') || c.includes('PIN') || l.includes('coupon') || l.includes('pin')) return 'fas fa-ticket-alt';
    if (c.includes('PROMO') || l.includes('promo')) return 'fas fa-tags';
    if (c.includes('VENDOR') || l.includes('vendor')) return 'fas fa-store';
    if (c.includes('WALLET') || l.includes('wallet')) return 'fas fa-wallet';
    if (c.includes('INCOME') || l.includes('earnings') || l.includes('income')) return 'fas fa-hand-holding-usd';
    if (c.includes('POINTS') || l.includes('points')) return 'fas fa-coins';
    if (c.includes('APPROVAL') || l.includes('approval')) return 'fas fa-clipboard-check';
    if (c.includes('KYC') || l.includes('kyc')) return 'fas fa-id-card';
    if (c.includes('TRANSACTION') || l.includes('transaction')) return 'fas fa-receipt';
    if (c.includes('MEMBER') || c.includes('TEAM') || l.includes('member') || l.includes('team')) return 'fas fa-users';
    if (c.includes('ATTENDANCE') || l.includes('attendance')) return 'fas fa-clock';
    if (c.includes('LEAVE') || l.includes('leave')) return 'fas fa-calendar-times';
    if (c.includes('TASK') || l.includes('task')) return 'fas fa-tasks';
    if (c.includes('KRA') || l.includes('kra')) return 'fas fa-chart-line';
    if (c.includes('JOURNEY') || l.includes('journey')) return 'fas fa-route';
    if (c.includes('TICKET') || l.includes('ticket') || l.includes('service')) return 'fas fa-tools';
    return 'fas fa-circle';
  }

  private getItemIconColor(code: string, label: string): string {
    const c = (code || '').toUpperCase();
    const l = (label || '').toLowerCase();

    if (c.includes('WHATSAPP') || l.includes('whatsapp')) return 'color: #25d366;';
    if (c.includes('AUTO_DIALER') || l.includes('auto dialer') || c.includes('SOFTPHONE') || l.includes('softphone')) return 'color: #38bdf8;';
    if (c.includes('CATALOG') || l.includes('catalog')) return 'color: #10b981;';
    if (c.includes('FIELD_SALES') || l.includes('field sales') || c.includes('BANK_WISE_LEADS')) return 'color: #38bdf8;';
    if (c.includes('SOLAR') || l.includes('solar')) return 'color: #f59e0b;';
    if (c.includes('EV_') || l.includes('ev ')) return 'color: #10b981;';
    if (c.includes('INSURANCE') || l.includes('care') || l.includes('insurance')) return 'color: #059669;';
    if (c.includes('REAL_DREAMS') || c.includes('REAL_ESTATE') || l.includes('real dreams') || l.includes('property')) return 'color: #2563eb;';
    if (c.includes('ETC') || l.includes('training')) return 'color: #8b5cf6;';
    if (c.includes('BONANZA') || l.includes('bonanza')) return 'color: #f59e0b;';
    if (c.includes('COUPON') || c.includes('PIN') || l.includes('coupon') || l.includes('pin')) return 'color: #6366f1;';
    if (c.includes('PROMO') || l.includes('promo')) return 'color: #ec4899;';
    if (c.includes('VENDOR') || l.includes('vendor')) return 'color: #0284c7;';
    if (c.includes('WALLET') || l.includes('wallet')) return 'color: #10b981;';
    if (c.includes('INCOME') || l.includes('earnings') || l.includes('income')) return 'color: #10b981;';
    if (c.includes('POINTS') || l.includes('points')) return 'color: #f59e0b;';
    if (c.includes('APPROVAL') || l.includes('approval')) return 'color: #10b981;';
    if (c.includes('KYC') || l.includes('kyc')) return 'color: #3b82f6;';
    if (c.includes('TRANSACTION') || l.includes('transaction')) return 'color: #0284c7;';
    if (c.includes('MEMBER') || c.includes('TEAM') || l.includes('member') || l.includes('team')) return 'color: #7c3aed;';
    return '';
  }

  private getStaffMenuMaster(): MenuSection[] {
    const authState = authService.getAuthState();
    const user = (authState.user || {}) as any;
    const empCode = (user.emp_code || user.employee_code || '').toString().toUpperCase().trim();
    const roleCode = (user.role_code || user.role?.role_code || user.user_type || '').toString().toLowerCase().trim();
    const roleName = (user.role_name || user.role?.role_name || '').toString().toUpperCase().trim();
    const staffType = (user.staff_type || '').toString().toUpperCase().trim();

    const supremeVariants = [
      "VGK4U_SUPREME", "RVZ_SUPREME", "VGK4U", "VGK4U SUPREME", "VGK4U_EA", 
      "KEY_LEADERSHIP", "KEY LEADERSHIP", "EA", "EXECUTIVE ADMIN", "MANAGER", 
      "DIRECTOR", "SUPER_ADMIN", "ADMIN"
    ];
    const isSaaSAdmin = ['MR10018', 'MR10001', 'MR10025', 'MR10016'].includes(empCode) || 
                        ['SAAS_SEGMENT_ADMIN', 'SUPER_ADMIN', 'VGK4U_SUPREME'].includes(staffType) ||
                        ['super_admin', 'saas_segment_admin', 'tenant_admin', 'key_leadership', 'vgk4u'].includes(roleCode);
    const isSupreme = this.isSupremeStaff || 
                      supremeVariants.includes(staffType) ||
                      ['MR10018', 'MR10001', 'MR10016', 'MR10025'].includes(empCode) ||
                      ['key_leadership', 'vgk4u', 'ea', 'vgk4u_supreme'].includes(roleCode) ||
                      Boolean(user.is_manager || user.is_admin || user.is_super_admin);

    const isAccountsStaff = (
      ['account', 'accounts', 'finance', 'payroll', 'billing', 'bookkeeper', 'auditor'].some(r => roleCode.includes(r)) ||
      ['ACCOUNT', 'ACCOUNTS', 'FINANCE', 'PAYROLL', 'BILLING', 'BOOKKEEPER', 'AUDITOR'].some(r => roleName.includes(r)) ||
      ['ACCOUNT', 'ACCOUNTS', 'FINANCE', 'PAYROLL', 'BILLING', 'BOOKKEEPER', 'AUDITOR'].some(r => staffType.includes(r)) ||
      ['ACCOUNT', 'ACCOUNTS', 'FINANCE', 'PAYROLL'].some(r => (user.department || user.department_name || '').toString().toUpperCase().includes(r))
    );
    const isAllowedAccounts = isSupreme || isAccountsStaff;
    const isRestrictedSales = ['MN10009', 'MR10022', 'MR10036', 'MR10027', 'MN10017', 'MN10016'].includes(empCode);

    const internalTypes = ['MYNT_REAL', 'MN_STAFF', 'VGK4U', 'INTERNAL', 'STAFF', 'ADMIN', 'HR', 'MANAGER', 'EXECUTIVE', 'FIELD_EXECUTIVE', 'SUPER_ADMIN', 'FREELANCER'];
    const isInternalType = staffType && internalTypes.includes(staffType);
    const isInternalCompany = user?.base_company_id && [1, 2, 3, 4, 88].includes(Number(user.base_company_id));
    const isSaaSTenant = !isSaaSAdmin && !isInternalType && !isInternalCompany && (staffType === 'TENANT_ADMIN' || staffType === 'SAAS_CLIENT' || staffType === 'SAAS_TENANT' || user?.company_segment === 'SEGMENT_B_SAAS');

    const formatItem = (item: SidebarItem): MenuItem | null => {
      // Permission check (skip if not supreme and path not allowed)
      if (!isSupreme && this.allowedPaths !== '*') {
        const cleanPath = item.route.replace(/\/$/, '');
        const isAlwaysAllowed = [
          '/staff/dialer', '/staff/auto-dialer', '/staff/softphone', '/staff/whatsapp-center',
          '/staff/configuration/catalog', '/staff/catalog-library', '/staff/catalog',
          '/staff/bank-wise-leads', '/staff/field-sales', '/staff/my-leads'
        ].includes(item.route) || item.route.startsWith('/staff/vgk/');
        
        if (!isAlwaysAllowed && !this.allowedPaths.has(item.route) && !this.allowedPaths.has(cleanPath)) {
          return null;
        }
      }

      // Razorpay & A1Top dashboards only for MR10001 and Accounts department
      if (item.route === '/staff/configuration/razorpay' || item.route === '/staff/configuration/a1top') {
        const empId = user.emp_code || user.employee_code || user.employee_id || '';
        const deptName = (user.department || user.department_name || '').toLowerCase();
        const isAllowed = (empId === 'MR10001') || (deptName === 'accounts');
        if (!isAllowed) {
          return null;
        }
      }

      // Sales restriction
      if (isRestrictedSales && (item.route === '/staff/leads' || item.menu_code === 'STAFF_LEADS' || item.menu_code === 'LEADS_MASTER')) {
        return null;
      }

      const route = item.route;
      const label = item.label;
      let tab: string | undefined = TAB_MAP[item.route];
      if (!tab) {
        const cUpper = (item.menu_code || '').toUpperCase();
        if (cUpper.includes('SOLAR_LEADS')) tab = 'solar';
        else if (cUpper.includes('EV_B2B')) tab = 'ev-b2b';
        else if (cUpper.includes('EV_B2C')) tab = 'ev-b2c';
        else if (cUpper.includes('EV_SPARES')) tab = 'ev-spares';
        else if (cUpper.includes('REAL_DREAMS') || cUpper.includes('ZYN_REAL_ESTATE')) tab = 'real-dreams';
        else if (cUpper.includes('INSURANCE') || cUpper.includes('ZYN_INSURANCE')) tab = 'insurance';
        else if (cUpper.includes('ETC_LEADS')) tab = 'etc';
        else if (cUpper.includes('MNR_LEADS')) tab = 'mnr';
      }

      let iconHtml = '';
      if (!label.startsWith('<i class=')) {
        const iconClass = item.icon || this.getItemIcon(item.menu_code, label);
        const iconColor = this.getItemIconColor(item.menu_code, label);
        iconHtml = `<i class="${iconClass}" style="margin-right: 8px; width: 18px; text-align: center; ${iconColor}"></i>`;
      }

      return {
        menu_code: item.menu_code,
        label: `${iconHtml}${label}`,
        route: route,
        tab: tab
      };
    };

    const sections: MenuSection[] = [];

    for (const section of CANONICAL_MENU_MASTER) {
      // Skip PROGRESS section since its items are pinned in topItems
      if (section.section_code === 'PROGRESS') {
        continue;
      }

      const sCode = (section.section_code || '').toUpperCase();
      const sTitle = (section.section_label || '').toUpperCase();
      const isSaasSection = sCode === 'VGK_SAAS' || sCode === 'MYNTOS_SAAS' || sTitle.includes('MYNTOS SAAS') || sTitle.includes('SAAS');

      // For SaaS tenants, completely exclude internal platform and group company sections
      if (isSaaSTenant) {
        const saasRestricted = ['MNR', 'MYNT', 'VGK', 'META', 'CONFIG', 'NOT IN USE', 'NOT_IN_USE', 'PARTNER', 'INTERNAL'];
        if (saasRestricted.some(k => sCode.includes(k) || sTitle.includes(k))) {
          if (!isSaasSection) {
            continue;
          }
        }
      }

      // If user is not allowed Accounts, hide ACCOUNTS section
      if (!isAllowedAccounts && (sCode.includes('ACCOUNT') || sTitle.includes('ACCOUNT') || sCode.includes('FINANCE'))) {
        continue;
      }

      // Global Directive: Remove META ADS, CONFIGURATION, SAAS, INTERNAL for general staff unless granted or SaaS admin
      if (!isSaaSAdmin) {
        const globalRestrictedKeywords = ['META', 'CONFIG', 'SAAS', 'INTERNAL'];
        if (globalRestrictedKeywords.some(k => sCode.includes(k) || sTitle.includes(k))) {
          if (this.allowedPaths !== '*' && this.allowedPaths instanceof Set) {
            const allowedSet = this.allowedPaths as Set<string>;
            const allSecRoutes = [
              ...(section.items || []).map(i => i.route),
              ...(section.subSections || []).flatMap(sub => sub.items.map(i => i.route))
            ];
            const hasAnyRoute = allSecRoutes.some(r => allowedSet.has(r) || allowedSet.has(r.replace(/\/$/, '')));
            if (!hasAnyRoute) {
              continue;
            }
          } else if (!isSupreme) {
            continue;
          }
        }
      } else {
        // For SaaS Admins, only restrict non-applicable internal sections if not super user
        if (empCode !== 'MR10001' && empCode !== 'MR10025') {
          const nonSaasRestricted = ['META', 'INTERNAL'];
          if (nonSaasRestricted.some(k => sCode.includes(k) || sTitle.includes(k))) {
            continue;
          }
        }
      }

      // Additional Directive for MR10018: Remove NOT IN USE, MNR, NDA, ZYNOVA (preserves MYNTOS SAAS)
      if (empCode === 'MR10018') {
        const mr10018RestrictedKeywords = ['NOT IN USE', 'NOT_IN_USE', 'MNR', 'NDA', 'ZYNOVA', 'ZINOVA'];
        if (mr10018RestrictedKeywords.some(k => (sCode.includes(k) || sTitle.includes(k)) && !isSaasSection)) {
          continue;
        }
      }

      // Hide NOT_IN_USE
      if (sCode === 'NOT_IN_USE' || sTitle === 'NOT IN USE') {
        continue;
      }

      const sectionItems: MenuItem[] = [];
      const sectionSubSections: SubSection[] = [];

      // Process items
      if (section.items) {
        for (const item of section.items) {
          const formatted = formatItem(item);
          if (formatted) {
            sectionItems.push(formatted);
          }
        }
      }

      // Guarantee Softphone, Auto Dialer, Digital Catalog in CRM
      if (sCode === 'CRM_LEADS') {
        if (!sectionItems.some(i => i.route === 'auto-dialer' || i.route === '/staff/dialer')) {
          sectionItems.push({
            menu_code: 'AUTO_DIALER',
            label: `<i class="fas fa-phone-volume" style="margin-right: 8px; width: 18px; text-align: center; color: #38bdf8;"></i>Auto Dialer`,
            route: '/staff/dialer'
          });
        }
        if (!sectionItems.some(i => i.route === 'softphone' || i.route === '/staff/softphone')) {
          sectionItems.push({
            menu_code: 'SOFTPHONE',
            label: `<i class="fas fa-headset" style="margin-right: 8px; width: 18px; text-align: center; color: #38bdf8;"></i>Calling & Softphone`,
            route: '/staff/softphone'
          });
        }
        if (!sectionItems.some(i => i.route === 'digital-catalog' || i.route === '/staff/catalog-library' || i.route === '/staff/configuration/catalog')) {
          sectionItems.push({
            menu_code: 'DIGITAL_CATALOG',
            label: `<i class="fas fa-book-open" style="margin-right: 8px; width: 18px; text-align: center; color: #10b981;"></i>Digital Catalog`,
            route: '/staff/catalog-library'
          });
        }
      }

      // Process subSections
      if (section.subSections) {
        for (const sub of section.subSections) {
          const subItems: MenuItem[] = [];
          for (const item of sub.items) {
            const formatted = formatItem(item);
            if (formatted) {
              subItems.push(formatted);
            }
          }
          if (subItems.length > 0) {
            sectionSubSections.push({
              sub_section_code: sub.sub_section_code,
              sub_section_label: sub.sub_section_label,
              items: subItems
            });
          }
        }
      }

      if (sectionItems.length > 0 || sectionSubSections.length > 0) {
        sections.push({
          section_code: section.section_code,
          section_label: section.section_label,
          order: section.order,
          items: sectionItems.length > 0 ? sectionItems : undefined,
          subSections: sectionSubSections.length > 0 ? sectionSubSections : undefined
        });
      }
    }

    return sections;
  }

  open(): void {
    if (this.isOpen) return;
    const portal = portalService.getPortal();
    if (portal === 'staff' && !this.isStaffMenuLoaded) {
      this.loadStaffMenus();
    }
    this.updateUI();
    this.isOpen = true;
    this.container?.classList.add('open');
    this.overlay?.classList.add('visible');
    document.body.style.overflow = 'hidden';
  }

  close(): void {
    if (!this.isOpen) return;
    this.isOpen = false;
    this.container?.classList.remove('open');
    this.overlay?.classList.remove('visible');
    document.body.style.overflow = '';
  }

  toggle(): void {
    if (this.isOpen) {
      this.close();
    } else {
      this.open();
    }
  }
}

let drawerInstance: SideDrawer | null = null;

export function getSideDrawer(): SideDrawer {
  if (!drawerInstance) {
    drawerInstance = new SideDrawer();
  }
  return drawerInstance;
}
