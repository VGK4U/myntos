import { routerService, PageRoute } from '../services/router.service';
import { portalService } from '../services/portal.service';
import { authService } from '../services/auth.service';
import { apiService } from '../services/api.service';

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
  '/staff/solar-leads': 'staff-leads',
  '/staff/real-dreams-leads': 'zynova-real-estate',
  '/staff/insurance-leads': 'zynova-insurance',
  '/staff/ev-b2b-leads': 'staff-leads',
  '/staff/ev-b2c-leads': 'staff-leads',
  '/staff/ev-spares-leads': 'staff-leads',
  '/staff/etc-leads': 'staff-training-videos',
  '/staff/mnr-leads': 'staff-leads',
  '/staff/mnr-leads-master': 'staff-leads',
  '/staff/executive-dashboard': 'dashboard',
  '/staff/crm/whatsapp-inbox': 'staff-whatsapp',
  '/staff/crm/wa-inbox': 'staff-whatsapp',
  '/staff/whatsapp': 'staff-whatsapp',
  '/staff/whatsapp-inbox': 'staff-whatsapp',
  '/staff/whatsapp-center': 'staff-whatsapp',
  '/staff/crm/whatsapp-center': 'staff-whatsapp',
  '/staff/crm/whatsapp': 'staff-whatsapp',
  
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
  '/staff/dialer': 'softphone',
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

const MENU_MASTER: MenuSection[] = [
  {
    section_code: "ATTENDANCE",
    section_label: "ATTENDANCE",
    order: 1,
    items: [
      { menu_code: "IN_OUT_TIME", label: "In/Out Time", route: "attendance" },
      { menu_code: "MY_LEAVES", label: "My Leaves", route: "leaves" },
      { menu_code: "LEAVE_APPROVALS", label: "Leave Approvals", route: "staff-leave-approvals" },
      { menu_code: "IN_OUT_RECORDS_ADMIN", label: "In/Out Records - Admin", route: "team-attendance" },
      { menu_code: "ATTENDANCE_RECORDS", label: "Attendance Records", route: "staff-attendance-sheet" },
      { menu_code: "ATTENDANCE_DASHBOARD", label: "Attendance Dashboard", route: "staff-attendance-reports" },
      { menu_code: "EXCEPTION_APPROVALS", label: "Exception Approvals", route: "staff-attendance-exceptions" },
      { menu_code: "ATTENDANCE_COMPUTATION", label: "Attendance Computation", route: "staff-attendance-computation" }
    ]
  },
  {
    section_code: "TASK_MANAGEMENT",
    section_label: "TASK MANAGEMENT",
    order: 3,
    items: [
      { menu_code: "ASSIGNED_BY_ME", label: "Assigned By Me", route: "tasks-assigned" },
      { menu_code: "ASSIGNED_TO_ME", label: "Assigned To Me", route: "tasks-received" },
      { menu_code: "TEAM_ACTIVITIES", label: "Team Activities", route: "staff-team-activities" },
      { menu_code: "TASK_TRACKER", label: "Task Dashboard", route: "staff-task-tracker" },
      { menu_code: "TASK_REVIEWS", label: "Task Reviews", route: "staff-task-reviews" }
    ]
  },
  {
    section_code: "KRA_MANAGEMENT",
    section_label: "KRA MANAGEMENT",
    order: 4,
    items: [
      { menu_code: "MY_KRAS", label: "My KRAs", route: "kras" },
      { menu_code: "KRA_TEMPLATES", label: "KRA Templates", route: "staff-kra-templates" },
      { menu_code: "KRA_TRACKING_SHEET", label: "KRA Tracking Sheet", route: "staff-kra-tracking" },
      { menu_code: "KRA_REVIEW", label: "KRA Review", route: "staff-kra-review" }
    ]
  },
  {
    section_code: "TIMESHEET",
    section_label: "TIMESHEET",
    order: 5,
    items: [
      { menu_code: "MY_TIMESHEET", label: "My Timesheet", route: "timesheet" },
      { menu_code: "TIMESHEET_APPROVAL", label: "Timesheet Approval", route: "staff-timesheet-approval" }
    ]
  },
  {
    section_code: "JOURNEY_TRACKING",
    section_label: "JOURNEY TRACKING",
    order: 6,
    items: [
      { menu_code: "MY_JOURNEYS", label: "My Journeys", route: "journeys" },
      { menu_code: "TEAM_JOURNEYS", label: "Team Journeys", route: "team-journeys" },
      { menu_code: "ALL_JOURNEYS", label: "All Journeys", route: "staff-all-journeys" },
      { menu_code: "VGK4U_JOURNEYS", label: "VGK4U Journeys", route: "staff-vgk4u-journeys" }
    ]
  },
  {
    section_code: "REIMBURSEMENT",
    section_label: "REIMBURSEMENT",
    order: 7,
    items: [
      { menu_code: "MY_REIMBURSEMENT_CLAIMS", label: "My Reimbursement Claims", route: "reimbursements" },
      { menu_code: "REIMBURSEMENT_APPROVALS", label: "Reimbursement Approvals", route: "staff-reimbursement-approvals" }
    ]
  },
  {
    section_code: "ACCOUNTS_EARNINGS",
    section_label: "FINANCE & EARNINGS",
    order: 8,
    items: [
      { menu_code: "MY_EARNINGS", label: "My Earnings", route: "staff-my-incentives" },
      { menu_code: "PAYROLL_PROFILE", label: "Payroll Profile", route: "staff-payroll-profile" },
      { menu_code: "SALARY_SLIPS", label: "Salary Slips", route: "staff-salary-slips" }
    ]
  },
  {
    section_code: "CRM_MODULE",
    section_label: "CRM & LEADS",
    order: 9,
    items: [
      { menu_code: "MY_CRM_DASHBOARD", label: "CRM Dashboard", route: "staff-crm" },
      { menu_code: "MY_LEADS", label: "My Leads", route: "staff-my-leads" },
      { menu_code: "LEADS_MASTER", label: "Staff Leads", route: "staff-leads" },
      { menu_code: "BANK_WISE_LEADS", label: "Field staff leads", route: "staff-bank-wise-leads" },
      { menu_code: "TEAM_LEADS", label: "Team Leads", route: "staff-team-leads" },
      { menu_code: "AUTO_DIALER", label: "Auto Dialer", route: "auto-dialer" }
    ]
  },
  {
    section_code: "WORKFLOWS",
    section_label: "WORK FLOWS",
    order: 10,
    items: [
      { menu_code: "MNR_BANK_WISE_LEADS", label: "Field Sales", route: "staff-bank-wise-leads" },
      { menu_code: "SOLAR_LEADS", label: "Solar Leads", route: "staff-leads" },
      { menu_code: "ZYN_REAL_ESTATE", label: "Real Dreams Leads", route: "zynova-real-estate" },
      { menu_code: "EV_B2B_LEADS", label: "EV B2B Leads", route: "staff-leads" },
      { menu_code: "EV_B2C_LEADS", label: "EV B2C Leads", route: "staff-leads" },
      { menu_code: "EV_SPARES_LEADS", label: "EV Spares Leads", route: "staff-leads" },
      { menu_code: "ZYN_INSURANCE", label: "Insurance Leads", route: "zynova-insurance" },
      { menu_code: "ETC_LEADS", label: "ETC Leads", route: "staff-training-videos" },
      { menu_code: "MNR_LEADS", label: "MNR Leads", route: "staff-leads" },
      { menu_code: "EXECUTIVE_DASHBOARD", label: "Executive Dashboard", route: "dashboard" },
      { menu_code: "CATEGORY_LEADS_MASTER", label: "Category Leads Master", route: "staff-leads" }
    ]
  },
  {
    section_code: "OPERATIONS",
    section_label: "OPERATIONS",
    order: 11,
    items: [
      { menu_code: "CALL_TRACKING", label: "Call Tracking", route: "staff-call-tracking" },
      { menu_code: "VENDORS", label: "Vendors", route: "staff-vendors" },
      { menu_code: "ZYN", label: "Zynova Real Estate", route: "zynova-real-estate" },
      { menu_code: "ZYNOVA", label: "VGK4U", route: "staff-zynova" },
      { menu_code: "ZYN_INSURANCE", label: "Zynova Insurance", route: "zynova-insurance" }
    ]
  }
];

const VGK_MENU_MASTER: MenuSection[] = [];

export class SideDrawer {
  private container: HTMLElement | null = null;
  private overlay: HTMLElement | null = null;
  private isOpen = false;
  private expandedSections: Set<string> = new Set();
  private staffMenuTree: any[] | null = null;
  private isStaffMenuLoaded = false;

  constructor() {
    try {
      const cached = localStorage.getItem('mnr_staff_menu_tree_cache');
      if (cached) {
        this.staffMenuTree = JSON.parse(cached);
        this.isStaffMenuLoaded = true;
      }
    } catch (e) {}

    this.createElements();
    this.loadStaffMenus();
    
    window.addEventListener('logout', () => {
      this.staffMenuTree = null;
      this.isStaffMenuLoaded = false;
      try { localStorage.removeItem('mnr_staff_menu_tree_cache'); } catch (e) {}
    });

    window.addEventListener('auth-changed', () => {
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
        .side-drawer { position: fixed; top: 0; left: 0; width: 290px; height: 100vh; background: #0f172a; color: #fff; z-index: 9999; transform: translateX(-100%); transition: transform 0.25s ease-in-out; overflow-y: auto; box-shadow: 2px 0 16px rgba(0,0,0,0.5); }
        .side-drawer.open { transform: translateX(0); }
        .drawer-overlay { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(0,0,0,0.6); z-index: 9998; opacity: 0; pointer-events: none; transition: opacity 0.25s ease-in-out; }
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
          { menu_code: "CALLING_PAGE", label: `<i class="fas fa-phone-alt" style="margin-right: 8px; width: 18px; text-align: center; color: #3b82f6;"></i> Calling Page`, route: "softphone" }
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

    const rawMenuMaster = isVgk ? VGK_MENU_MASTER : (portal === 'staff' ? this.getStaffMenuMaster() : MENU_MASTER);
    const menuMaster = portal === 'staff' ? this.filterMenusForRole(rawMenuMaster, isManagerOrEa, isAllowedAccounts) : rawMenuMaster;

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

    if (hasSubSections) {
      return `
        <div class="drawer-section" data-section="${section.section_code}">
          <div class="section-header" data-toggle="${section.section_code}">
            <span class="section-title">${section.section_label}</span>
            <svg class="section-arrow" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">${isExpanded ? '<polyline points="6 9 12 15 18 9"/>' : '<polyline points="9 18 15 12 9 6"/>'}</svg>
          </div>
          <div class="section-items ${isExpanded ? 'expanded' : ''}" style="display: ${isExpanded ? 'block' : 'none'};">
            ${section.subSections!.map(sub => this.renderSubSection(sub)).join('')}
          </div>
        </div>
      `;
    }

    if (hasItems) {
      return `
        <div class="drawer-section" data-section="${section.section_code}">
          <div class="section-header" data-toggle="${section.section_code}">
            <span class="section-title">${section.section_label}</span>
            <svg class="section-arrow" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">${isExpanded ? '<polyline points="6 9 12 15 18 9"/>' : '<polyline points="9 18 15 12 9 6"/>'}</svg>
          </div>
          <div class="section-items ${isExpanded ? 'expanded' : ''}" style="display: ${isExpanded ? 'block' : 'none'};">
            ${section.items!.map(item => this.renderMenuItem(item)).join('')}
          </div>
        </div>
      `;
    }

    return '';
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
      <a class="drawer-menu-item" data-route="${item.route}">
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
        const route = (el as HTMLElement).dataset.route!;
        const tab = (el as HTMLElement).dataset.tab;
        
        if (tab) {
          routerService.navigate(route as PageRoute, { tab });
        } else {
          routerService.navigate(route as PageRoute);
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
    try {
      const response = await apiService.get<any>('/staff/menu-settings/my-menus?unified=true');
      if (response.success && response.data && response.data.sidebar_tree) {
        this.staffMenuTree = response.data.sidebar_tree;
        this.isStaffMenuLoaded = true;
        try {
          localStorage.setItem('mnr_staff_menu_tree_cache', JSON.stringify(this.staffMenuTree));
        } catch (e) {}
        this.updateUI();
      }
    } catch (e) {
      console.error('Failed to load dynamic staff menus:', e);
    }
  }

  private filterMenusForRole(sections: MenuSection[], isManagerOrEa: boolean, isAllowedAccounts: boolean = false): MenuSection[] {
    if (isManagerOrEa) {
      return sections; // Managers & EAs see ALL management, system, and accounts menus
    }

    // Management/System-only sections to hide from regular non-manager staff
    // Note: VGK4U and VGK Team are available to ALL staff members per user requirement.
    const RESTRICTED_SECTIONS = new Set([
      'SAAS',
      'SAAS_MANAGEMENT',
      'SAAS CONFIGURATION',
      'CONFIGURATION',
      'SYSTEM_CONFIGURATION',
      'SYSTEM CONFIG',
      'META_ADS',
      'META ADS',
      'VENDOR_MANAGEMENT',
      'VENDOR MANAGEMENT',
      'VENDORS',
      'HR',
      'HR_MANAGEMENT',
      'ZYNOVA',
      'ZYNOVA_REAL_ESTATE',
      'MNR',
      'MNR_USER_SIDEBAR',
      'MNR USER SIDEBAR',
      'MNR_USER',
      'MNR USER'
    ]);

    // Restrict Accounts & Finance section if user is NOT in Accounts Department and NOT Manager/EA
    if (!isAllowedAccounts) {
      RESTRICTED_SECTIONS.add('ACCOUNTS');
      RESTRICTED_SECTIONS.add('ACCOUNTS_EARNINGS');
      RESTRICTED_SECTIONS.add('ACCOUNTS & EARNINGS');
      RESTRICTED_SECTIONS.add('FINANCE');
      RESTRICTED_SECTIONS.add('FINANCE & EARNINGS');
      RESTRICTED_SECTIONS.add('FINANCE_EARNINGS');
      RESTRICTED_SECTIONS.add('ACCOUNTS_MANAGEMENT');
    }

    // Admin/Management-only items to hide from regular staff
    const RESTRICTED_ITEM_CODES = new Set([
      'EXECUTIVE_DASHBOARD',
      'CATEGORY_LEADS_MASTER',
      'SAAS_CONFIG',
      'SYSTEM_CONFIG'
    ]);

    if (!isAllowedAccounts) {
      RESTRICTED_ITEM_CODES.add('PAYROLL_PROFILE');
      RESTRICTED_ITEM_CODES.add('SALARY_SLIPS');
      RESTRICTED_ITEM_CODES.add('EXPENSE_ENTRIES');
    }

    const filtered: MenuSection[] = [];

    for (const section of sections) {
      const codeUpper = (section.section_code || '').toUpperCase().trim();
      const labelUpper = (section.section_label || '').toUpperCase().trim();

      // Skip restricted management sections for non-manager regular staff
      if (RESTRICTED_SECTIONS.has(codeUpper) || RESTRICTED_SECTIONS.has(labelUpper)) {
        continue;
      }

      let items = section.items;
      if (items && items.length > 0) {
        items = items.filter(item => {
          const itemCode = (item.menu_code || '').toUpperCase().trim();
          return !RESTRICTED_ITEM_CODES.has(itemCode);
        });
      }

      let subSections = section.subSections;
      if (subSections && subSections.length > 0) {
        subSections = subSections.map(sub => ({
          ...sub,
          items: sub.items.filter(item => {
            const itemCode = (item.menu_code || '').toUpperCase().trim();
            return !RESTRICTED_ITEM_CODES.has(itemCode);
          })
        })).filter(sub => sub.items.length > 0);
      }

      const hasItems = items && items.length > 0;
      const hasSubSections = subSections && subSections.length > 0;

      if (hasItems || hasSubSections) {
        filtered.push({
          ...section,
          items: hasItems ? items : undefined,
          subSections: hasSubSections ? subSections : undefined
        });
      }
    }

    return filtered;
  }

  private getStaffMenuMaster(): MenuSection[] {
    if (!this.staffMenuTree) {
      return MENU_MASTER;
    }

    const WORKFLOWS_ORDER: Record<string, number> = {
      'EXECUTIVE_DASHBOARD': 1,
      'staff_executive_dashboard': 1,
      'mnr_executive_dashboard': 1,

      'MNR_BANK_WISE_LEADS': 2,
      'BANK_WISE_LEADS': 2,
      'staff_bank_wise_leads': 2,

      'CATEGORY_LEADS_MASTER': 3,
      'mnr_leads_master': 3,
      'staff_mnr_leads_master': 3,

      'SOLAR_LEADS': 4,
      'staff_solar_leads': 4,
      'mnr_solar_leads': 4,

      'EV_B2B_LEADS': 5,
      'staff_ev_b2b_leads': 5,
      'mnr_ev_b2b_leads': 5,

      'EV_B2C_LEADS': 6,
      'staff_ev_b2c_leads': 6,
      'mnr_ev_b2c_leads': 6,

      'EV_SPARES_LEADS': 7,
      'staff_ev_spares_leads': 7,
      'mnr_ev_spares_leads': 7,

      'ZYN_REAL_ESTATE': 8,
      'staff_real_dreams_leads': 8,
      'mnr_real_dreams_leads': 8,

      'ZYN_INSURANCE': 9,
      'staff_insurance_leads': 9,
      'mnr_insurance_leads': 9,

      'ETC_LEADS': 10,
      'staff_etc_leads': 10,
      'mnr_etc_leads': 10,

      'MNR_LEADS': 11,
      'staff_mnr_leads': 11,
      'mnr_category_leads': 11,

      'AUTO_DIALER': 12,
      'staff_auto_dialer': 12,
      'auto-dialer': 12
    };

    const sectionMap = new Map<string, MenuSection>();
    const sectionOrderList: string[] = [];

    const formatMenuItem = (rawCode: string, rawName: string, rawRoutePath: string, rawIcon?: string): MenuItem | null => {
      const route = ROUTE_PATH_MAP[rawRoutePath] || ROUTE_PATH_MAP[rawRoutePath?.replace(/\/$/, '')] || (rawRoutePath ? rawRoutePath.replace(/^\/staff\//, '').replace(/\//g, '-') : null);
      if (!route) return null;

      let label = rawName;
      if (!label || label === 'None' || label.trim() === '') {
        label = (rawCode || '').replace(/^staff_|^_staff_|^mnr_/i, '').replace(/_/g, ' ').replace(/\b\w/g, ch => ch.toUpperCase());
      }
      const codeUpper = (rawCode || '').toUpperCase();
      const routeLower = (rawRoutePath || '').toLowerCase();

      if (codeUpper.includes('AUTO_DIALER') || routeLower.includes('auto-dialer') || codeUpper === 'AUTO_DIALER') {
        label = 'Auto Dialer';
      } else if (codeUpper.includes('BANK_WISE_LEADS') || routeLower.includes('bank-wise-leads')) {
        label = 'Field staff leads';
      } else if (codeUpper.includes('REAL_DREAMS') || routeLower.includes('real-dreams-leads')) {
        label = 'Real Dreams Leads';
      } else if (codeUpper.includes('ETC_LEADS') || routeLower.includes('etc-leads')) {
        label = 'ETC Training Students';
      } else if (codeUpper.includes('CATEGORY_LEADS_MASTER') || codeUpper.includes('MNR_LEADS_MASTER') || routeLower.includes('mnr-leads-master')) {
        label = 'Category Lead Master';
      } else if (codeUpper.includes('WHATSAPP') || routeLower.includes('whatsapp')) {
        label = 'WhatsApp Center';
      } else if (codeUpper.includes('SOFTPHONE') || codeUpper.includes('DIALER') || routeLower.includes('softphone') || routeLower.includes('dialer')) {
        label = 'Calling & Softphone';
      }

      const iconClass = rawIcon || (label.includes('WhatsApp') ? 'fab fa-whatsapp' : label.includes('Auto Dialer') ? 'fas fa-phone-volume' : label.includes('Softphone') || label.includes('Calling') ? 'fas fa-headset' : label.includes('Field') ? 'fas fa-users-gear' : 'fas fa-file-alt');
      const iconColor = label.includes('WhatsApp') ? 'color: #25d366;' : (label.includes('Auto Dialer') || label.includes('Softphone') || label.includes('Calling')) ? 'color: #38bdf8;' : '';
      const iconHtml = `<i class="${iconClass}" style="margin-right: 8px; width: 18px; text-align: center; ${iconColor}"></i>`;

      return {
        menu_code: rawCode,
        label: `${iconHtml}${label}`,
        route: route
      };
    };

    for (const sec of this.staffMenuTree) {
      if (sec.id === 'progress' || sec.section_id === 'progress' || (sec.title || '').toUpperCase() === 'PROGRESS') {
        continue;
      }
      const items: MenuItem[] = [];
      const subSections: SubSection[] = [];

      // Add items from direct section.items
      if (sec.items) {
        for (const item of sec.items) {
          const menuItem = formatMenuItem(item.menu_code, item.menu_name || item.label || item.name || item.title, item.route_path, item.menu_icon);
          if (menuItem) items.push(menuItem);
        }
      }

      // Add subSections
      if (sec.subSections) {
        for (const sub of sec.subSections) {
          const subItems: MenuItem[] = [];
          if (sub.items) {
            for (const item of sub.items) {
              const menuItem = formatMenuItem(item.menu_code, item.menu_name || item.label || item.name || item.title, item.route_path, item.menu_icon);
              if (menuItem) subItems.push(menuItem);
            }
          }
          let subTitle = sub.title || sub.name || sub.id || 'Subsection';
          if (subTitle === 'None' || !subTitle) {
            subTitle = (sub.id || '').replace(/^staff_|^vm_/i, '').replace(/_/g, ' ').replace(/\b\w/g, (p: string) => p.toUpperCase());
          }
          if (subItems.length > 0) {
            subSections.push({
              sub_section_code: sub.id || sub.section_id || 'sub',
              sub_section_label: subTitle,
              items: subItems
            });
          }
        }
      }

      if (items.length > 0 || subSections.length > 0) {
        let secCode = (sec.id || sec.section_id || 'other').toString().trim();
        let secTitle = (sec.title || sec.name || 'Other').toString().trim();
        if (secTitle === 'None' || !secTitle) {
          secTitle = secCode.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase());
        }
        const secIdLower = secCode.toLowerCase();
        const secTitleUpper = secTitle.toUpperCase();

        if (secIdLower === 'mynt_real' || secIdLower === 'myntreal' || secIdLower === 'workflows' || secTitleUpper === 'MYNT REAL' || secTitleUpper === 'MYNTREAL' || secTitleUpper === 'WORK FLOWS' || secTitleUpper === 'WORKFLOWS') {
          secCode = 'WORKFLOWS';
          secTitle = 'WORK FLOWS';
        }

        if (sectionMap.has(secCode)) {
          const existing = sectionMap.get(secCode)!;
          if (items.length > 0) {
            existing.items = existing.items || [];
            const existingCodes = new Set(existing.items.map(i => i.menu_code));
            for (const it of items) {
              if (!existingCodes.has(it.menu_code)) {
                existing.items.push(it);
                existingCodes.add(it.menu_code);
              }
            }
          }
          if (subSections.length > 0) {
            existing.subSections = existing.subSections || [];
            existing.subSections.push(...subSections);
          }
        } else {
          sectionOrderList.push(secCode);
          sectionMap.set(secCode, {
            section_code: secCode,
            section_label: secTitle,
            order: sec.order !== undefined ? sec.order : 999,
            items: items.length > 0 ? items : undefined,
            subSections: subSections.length > 0 ? subSections : undefined
          });
        }
      }
    }

    // Ensure Auto Dialer is guaranteed in CRM_MODULE or WORKFLOWS section
    let crmSec = sectionMap.get('CRM_MODULE') || sectionMap.get('CRM_LEADS') || sectionMap.get('WORKFLOWS');
    if (crmSec) {
      crmSec.items = crmSec.items || [];
      const hasAutoDialer = crmSec.items.some(i => i.route === 'auto-dialer' || i.menu_code === 'AUTO_DIALER');
      if (!hasAutoDialer) {
        crmSec.items.push({
          menu_code: "AUTO_DIALER",
          label: `<i class="fas fa-phone-volume" style="margin-right: 8px; width: 18px; text-align: center; color: #38bdf8;"></i>Auto Dialer`,
          route: "auto-dialer"
        });
      }
    }

    const result = sectionOrderList.map(code => sectionMap.get(code)!);
    result.sort((a, b) => a.order - b.order);

    // Apply strict web ordering for WORKFLOWS items
    for (const section of result) {
      if (section.section_code === 'WORKFLOWS' && section.items) {
        section.items.sort((a, b) => (WORKFLOWS_ORDER[a.menu_code] || 99) - (WORKFLOWS_ORDER[b.menu_code] || 99));
      }
    }

    return result;
  }

  open(): void {
    if (this.isOpen) return;
    this.updateUI();
    this.isOpen = true;
    this.container?.classList.add('open');
    this.overlay?.classList.add('visible');
    document.body.style.overflow = 'hidden';

    const portal = portalService.getPortal();
    if (portal === 'staff') {
      this.loadStaffMenus();
    }
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
