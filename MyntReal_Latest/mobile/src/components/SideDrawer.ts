import { routerService, PageRoute } from '../services/router.service';

interface MenuItem {
  menu_code: string;
  label: string;
  route: string;
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
    section_code: "SERVICE_TICKETS",
    section_label: "SERVICE TICKETS",
    order: 8,
    items: [
      { menu_code: "ST_SERVICE_QUEUE", label: "Service Queue", route: "staff-service-queue" },
      { menu_code: "ST_DASHBOARD", label: "Dashboard", route: "staff-service" },
      { menu_code: "ST_PERFORMANCE", label: "Performance", route: "staff-service-performance" },
      { menu_code: "ST_PROCUREMENT", label: "Procurement", route: "staff-service-procurement" },
      { menu_code: "ST_PROCUREMENT_QUEUE", label: "Procurement Queue", route: "staff-service-procurement-queue" },
      { menu_code: "ST_RAISE_TICKET", label: "Raise Ticket", route: "staff-tickets" },
      { menu_code: "ST_REPORTS", label: "Reports", route: "staff-service-reports" },
      { menu_code: "ST_SERVICE_CENTER_REVENUE", label: "Service Center Revenue", route: "staff-service-revenue" }
    ]
  },
  {
    section_code: "CRM",
    section_label: "CRM & LEADS",
    order: 9,
    items: [
      { menu_code: "CRM_DASHBOARD", label: "CRM Dashboard", route: "staff-crm" },
      { menu_code: "MY_LEADS", label: "My Leads", route: "staff-leads" },
      { menu_code: "TEAM_LEADS", label: "Team Leads", route: "staff-team-leads" },
      { menu_code: "LEAD_SOURCES", label: "Lead Sources", route: "staff-lead-sources" },
      { menu_code: "CALL_TRACKING_DASHBOARD", label: "Call Tracking", route: "staff-call-tracking" },
      { menu_code: "AUTO_DIALER", label: "Auto Dialer", route: "auto-dialer" },
      { menu_code: "OPERATOR_CALLS", label: "Operator Calls", route: "operator-calls" }
    ]
  },
  {
    section_code: "LOCATION_TRACKING",
    section_label: "LOCATION TRACKING",
    order: 10,
    items: [
      { menu_code: "LOCATION_HISTORY", label: "My Location History", route: "location-history" },
      { menu_code: "TEAM_LIVE_TRACKER", label: "Team Live Tracker", route: "staff-team-live-tracker" },
      { menu_code: "ALL_LOCATION_TRACKER", label: "All Locations", route: "staff-all-location-tracker" }
    ]
  },
  {
    section_code: "OTHER",
    section_label: "OTHER",
    order: 11,
    items: [
      { menu_code: "ANNOUNCEMENTS", label: "Announcements", route: "announcements" },
      { menu_code: "TRAINING_VIDEOS", label: "Training Videos", route: "staff-training-videos" },
      { menu_code: "MY_KYC", label: "My KYC", route: "staff-kyc" },
      { menu_code: "KYC_APPROVALS", label: "KYC Approvals", route: "staff-kyc-approvals" },
      { menu_code: "ZYNOVA", label: "VGK4U", route: "staff-zynova" },
      { menu_code: "SETTINGS", label: "Settings", route: "settings" }
    ]
  }
];

export class SideDrawer {
  private container: HTMLElement | null = null;
  private overlay: HTMLElement | null = null;
  private isOpen = false;
  private expandedSections: Set<string> = new Set();

  constructor() {
    this.createElements();
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

    this.attachEventListeners();
  }

  private render(): string {
    return `
      <div class="drawer-header">
        <div class="drawer-logo">
          <span class="logo-text">MNR</span>
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
          ${TOP_MENU_ITEMS.map(item => `
            <div class="menu-item top-item" data-route="${item.route}">
              <span class="menu-label">${item.label}</span>
            </div>
          `).join('')}
        </div>
        <!-- Section menus -->
        ${MENU_MASTER.map(section => this.renderSection(section)).join('')}
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
          <div class="section-items ${isExpanded ? 'expanded' : ''}">
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
          <div class="section-items ${isExpanded ? 'expanded' : ''}">
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
        <div class="subsection-items ${isExpanded ? 'expanded' : ''}">
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
        routerService.navigate(route as PageRoute);
        this.close();
      });
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

  open(): void {
    if (this.isOpen) return;
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
