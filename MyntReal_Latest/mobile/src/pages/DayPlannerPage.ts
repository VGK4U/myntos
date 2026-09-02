import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';
import { API_ENDPOINTS } from '../constants/api-endpoints';

interface PlanItem {
  id: number;
  task_id?: number;
  phase_id?: number;
  source_id?: number;
  item_type: 'task' | 'phase';
  task_title?: string;
  title?: string;
  task_priority?: string;
  priority?: string;
  task_status?: string;
  status?: string;
  task_due_date?: string;
  due_date?: string;
  priority_order?: number;
  plan_type?: string;
  is_followup?: boolean;
  eod_status?: string;
  eod_progress?: number;
  eod_notes?: string;
  notes?: string;
  time_spent_minutes?: number;
  progress?: number;
  carried_forward?: boolean;
  days_pending?: number;
  times_planned?: number;
  category?: string;
}

interface AvailableTask {
  id: number;
  title: string;
  status: string;
  priority: string;
  category?: string;
  due_date?: string;
  days_pending?: number;
  times_planned?: number;
  phases?: AvailablePhase[];
  sub_tasks?: AvailablePhase[];
}

interface AvailablePhase {
  id: number;
  title: string;
  status: string;
  target_date?: string;
  due_date?: string;
  days_pending?: number;
  times_planned?: number;
  child_task_id?: number;
}

interface DayPlan {
  id?: number;
  plan_date?: string;
  is_finalized?: boolean;
  items?: PlanItem[];
  notes?: string;
}

interface TeamMember {
  id: number;
  full_name: string;
  emp_code: string;
}

interface TeamPlanData {
  employee_id: number;
  employee_name: string;
  emp_code: string;
  plan_id?: number;
  is_finalized?: boolean;
  items: PlanItem[];
  stats?: { total: number; completed: number; in_progress: number; pending: number };
  activity_buckets?: any;
}

export class DayPlannerPage {
  private container: HTMLElement;
  private currentPlan: DayPlan | null = null;
  private planItems: PlanItem[] = [];
  private availableTasks: AvailableTask[] = [];
  private teamPlans: TeamPlanData[] = [];
  private teamMembers: TeamMember[] = [];
  private loading = true;
  private activeTab: 'my-plan' | 'team-plan' = 'my-plan';
  private selectedDate: string;
  private hasTeam = false;
  private selectedMemberId = '';
  private searchQuery = '';
  private statusFilter = 'all';
  private priorityFilter = 'all';
  private showAvailable = false;
  private selectedChoices: Map<string, { type: 'task' | 'phase'; id: number; taskId?: number; mode: 'plan' | 'followup' }> = new Map();
  private pendingTimers: ReturnType<typeof setTimeout>[] = [];

  constructor(container: HTMLElement) {
    this.container = container;
    this.selectedDate = this.getISTToday();
  }

  async init(): Promise<void> {
    this.render();
    await Promise.all([
      this.loadPlan(),
      this.loadAvailableTasks()
    ]);
  }

  destroy(): void {
    this.pendingTimers.forEach(t => clearTimeout(t));
    this.pendingTimers = [];
  }

  private getISTToday(): string {
    const now = new Date();
    const ist = new Date(now.getTime() + (5.5 * 60 * 60 * 1000));
    return ist.toISOString().split('T')[0];
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container day-planner-page">
        ${PageHeader.render({ title: 'Day Planner', showBack: true })}
        
        <div class="dp-tabs">
          <button class="dp-tab ${this.activeTab === 'my-plan' ? 'active' : ''}" data-tab="my-plan">My Plan</button>
          <button class="dp-tab ${this.activeTab === 'team-plan' ? 'active' : ''}" data-tab="team-plan" id="teamPlanTab" style="display:none;">Team Plan</button>
        </div>

        <div class="dp-date-bar">
          <button class="dp-today-btn" id="dpTodayBtn">Today</button>
          <input type="date" class="dp-date-input" id="dpDateInput" value="${this.selectedDate}">
          <div class="dp-plan-badge" id="dpPlanBadge"></div>
        </div>

        <div id="dpContent">
          <div class="loading-state">Loading plan...</div>
        </div>
      </div>
    `;

    PageHeader.attachListeners({ title: 'Day Planner', showBack: true });
    this.attachListeners();
  }

  private attachListeners(): void {
    document.querySelectorAll('.dp-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        const tabId = (tab as HTMLElement).dataset.tab as 'my-plan' | 'team-plan';
        this.activeTab = tabId;
        document.querySelectorAll('.dp-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        if (tabId === 'team-plan') {
          this.loadTeamPlans();
        } else {
          this.updateContent();
        }
      });
    });

    document.getElementById('dpDateInput')?.addEventListener('change', (e) => {
      this.selectedDate = (e.target as HTMLInputElement).value;
      this.loadPlan();
      this.loadAvailableTasks();
    });

    document.getElementById('dpTodayBtn')?.addEventListener('click', () => {
      this.selectedDate = this.getISTToday();
      const input = document.getElementById('dpDateInput') as HTMLInputElement;
      if (input) input.value = this.selectedDate;
      this.loadPlan();
      this.loadAvailableTasks();
    });
  }

  async loadPlan(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      const today = this.getISTToday();
      let url: string;
      if (this.selectedDate === today) {
        url = API_ENDPOINTS.DAY_PLANNER.TODAY;
      } else {
        url = `${API_ENDPOINTS.DAY_PLANNER.BY_DATE}?plan_date=${this.selectedDate}`;
      }

      const response = await apiService.get<any>(url);
      if (response.success && response.data) {
        const data = response.data;
        if (data.plan) {
          this.currentPlan = data.plan;
          this.planItems = data.plan.items || data.items || [];
        } else if (data.items) {
          this.currentPlan = data;
          this.planItems = data.items || [];
        } else if (Array.isArray(data)) {
          this.currentPlan = null;
          this.planItems = data;
        } else {
          this.currentPlan = data || null;
          this.planItems = data.items || [];
        }
      } else {
        this.currentPlan = null;
        this.planItems = [];
      }

      const teamResp = await apiService.get<any>(API_ENDPOINTS.DAY_PLANNER.TEAM_MEMBERS);
      if (teamResp.success && teamResp.data) {
        const members = Array.isArray(teamResp.data) ? teamResp.data : (teamResp.data.members || []);
        this.teamMembers = members;
        this.hasTeam = members.length > 0;
      }
    } catch (error) {
      console.error('[DayPlannerPage] Failed to load plan:', error);
      this.currentPlan = null;
      this.planItems = [];
    }

    this.loading = false;
    const teamTab = document.getElementById('teamPlanTab');
    if (teamTab) {
      teamTab.style.display = this.hasTeam ? '' : 'none';
    }
    this.updateContent();
  }

  async loadAvailableTasks(): Promise<void> {
    try {
      const response = await apiService.get<any>(API_ENDPOINTS.DAY_PLANNER.AVAILABLE_TASKS);
      if (response.success && response.data) {
        this.availableTasks = Array.isArray(response.data) ? response.data : (response.data.tasks || []);
      }
    } catch (error) {
      console.error('[DayPlannerPage] Failed to load available tasks:', error);
      this.availableTasks = [];
    }
    this.updateContent();
  }

  private updateContent(): void {
    const content = document.getElementById('dpContent');
    if (!content) return;

    if (this.loading) {
      content.innerHTML = '<div class="loading-state">Loading plan...</div>';
      return;
    }

    this.updatePlanBadge();

    if (this.activeTab === 'team-plan') {
      content.innerHTML = this.renderTeamPlan();
      this.attachTeamListeners();
      return;
    }

    content.innerHTML = this.renderMyPlan();
    this.attachMyPlanListeners();
  }

  private updatePlanBadge(): void {
    const badge = document.getElementById('dpPlanBadge');
    if (!badge) return;
    if (this.currentPlan?.is_finalized) {
      badge.innerHTML = '<span class="plan-status-badge finalized">Finalized</span>';
    } else if (this.planItems.length > 0) {
      badge.innerHTML = '<span class="plan-status-badge active">Active</span>';
    } else {
      badge.innerHTML = '<span class="plan-status-badge no-plan">No Plan</span>';
    }
  }

  private renderMyPlan(): string {
    const stats = this.getStats();
    const isFinalized = this.currentPlan?.is_finalized || false;
    const plannedTasks = (this.planItems || []).filter(i => !i.is_followup && i.plan_type !== 'followup');
    const followupTasks = (this.planItems || []).filter(i => i.is_followup || i.plan_type === 'followup');

    const planTaskIds = new Set<number>();
    (this.planItems || []).forEach(item => {
      if (item.task_id) planTaskIds.add(item.task_id);
      if (item.item_type === 'task' && item.source_id) planTaskIds.add(item.source_id);
    });

    const overdueBacklogTasks = (this.availableTasks || []).filter(t => 
      !planTaskIds.has(t.id) && ((t.days_pending || 0) > 0 || (t.times_planned || 0) > 0)
    );

    return `
      <div class="dp-share-bar">
        <button class="dp-share-btn dp-share-plan" id="sharePlanWaBtn">
          <i class="fab fa-whatsapp"></i> Share Day Plan
        </button>
        <button class="dp-share-btn dp-share-final" id="shareFinalWaBtn">
          <i class="fas fa-flag-checkered"></i> Share Closure Report
        </button>
      </div>

      <div class="dp-stats-row">
        <div class="dp-stat"><span class="dp-stat-value">${stats.total}</span><span class="dp-stat-label">Total</span></div>
        <div class="dp-stat completed"><span class="dp-stat-value">${stats.completed}</span><span class="dp-stat-label">Done</span></div>
        <div class="dp-stat in-progress"><span class="dp-stat-value">${stats.inProgress}</span><span class="dp-stat-label">Active</span></div>
        <div class="dp-stat pending"><span class="dp-stat-value">${stats.pending}</span><span class="dp-stat-label">Pending</span></div>
        <div class="dp-stat carried"><span class="dp-stat-value">${stats.carried}</span><span class="dp-stat-label">Carried</span></div>
      </div>

      <!-- Available Tasks Section -->
      <div class="dp-section">
        <div class="dp-section-header" id="toggleAvailableBtn">
          <span>📋 Available Tasks (${this.availableTasks.length || 0})</span>
          <div class="dp-header-actions" onclick="event.stopPropagation()">
            <button class="dp-quick-new-task-btn" id="openNewTaskModalBtn">+ New Task</button>
            <span class="dp-toggle-icon">${this.showAvailable ? '▲' : '▼'}</span>
          </div>
        </div>
        ${this.showAvailable ? this.renderAvailableTasks() : ''}
      </div>

      <div class="dp-section">
        <div class="dp-section-header-static dp-section-planned-hdr">
          <span>📋 1. Planned for the Day (${plannedTasks.length} Tasks)</span>
        </div>
        ${this.renderPlanSubSection(plannedTasks, false, isFinalized)}
      </div>

      <div class="dp-section">
        <div class="dp-section-header-static dp-section-followup-hdr">
          <span>🔄 2. Follow ups (${followupTasks.length} Tasks)</span>
        </div>
        ${this.renderPlanSubSection(followupTasks, true, isFinalized)}
      </div>

      <!-- 3. Overdue & Backlog Section -->
      <div class="dp-section">
        <div class="dp-section-header-static dp-section-overdue-hdr">
          <span>⚠️ 3. Overdue &amp; Backlog Tasks (${overdueBacklogTasks.length} Tasks - Not in Plan)</span>
        </div>
        ${this.renderOverdueBacklogSubSection(overdueBacklogTasks)}
      </div>

      ${!isFinalized && this.planItems.length > 0 ? `
        <div class="dp-finalize-bar">
          <button class="dp-finalize-btn" id="finalizeBtn">✅ Finalize Day</button>
        </div>
      ` : ''}
    `;
  }

  private getStats() {
    const items = this.planItems || [];
    let completed = 0, inProgress = 0, pending = 0, carried = 0;
    items.forEach(item => {
      const st = (item.eod_status || item.status || '').toLowerCase();
      if (st === 'completed') completed++;
      else if (st === 'in_progress') inProgress++;
      else pending++;
      if (item.carried_forward) carried++;
    });
    return { total: items.length, completed, inProgress, pending, carried };
  }

  private renderPlanSubSection(items: PlanItem[], isFollowupSection: boolean, isFinalized: boolean): string {
    if (!items.length) {
      const emptyMsg = isFollowupSection 
        ? 'No follow-up items scheduled. Select items with "Follow up" above.' 
        : 'No regular tasks planned. Select items with "Plan" above.';
      return `<div class="dp-empty">${emptyMsg}</div>`;
    }

    const sorted = [...items].sort((a, b) => (a.priority_order || 999) - (b.priority_order || 999));
    return `<div class="dp-plan-list">
      ${sorted.map((item, idx) => {
        const title = item.task_title || item.title || '';
        const isPhase = item.item_type === 'phase';
        const priority = item.task_priority || item.priority || '';
        const status = item.eod_status || item.task_status || item.status || 'pending';
        const progress = item.eod_progress != null ? item.eod_progress : (item.progress || 0);
        const dueDate = item.task_due_date || item.due_date || '';
        const daysPending = item.days_pending || 0;
        const timesPlanned = item.times_planned || 0;
        const isCarried = item.carried_forward;
        const note = (item.eod_notes || item.notes || '').trim();

        return `
          <div class="dp-plan-card ${isCarried ? 'carried-forward' : ''} ${isFollowupSection ? 'dp-plan-card-followup' : ''}">
            <div class="dp-plan-header">
              <span class="dp-priority-num">${item.priority_order || (idx + 1)}</span>
              <div class="dp-plan-title-box">
                <span class="dp-plan-title">
                  ${isFollowupSection ? '<span class="dp-badge dp-badge-followup">Follow up</span>' : ''}
                  ${this.escapeHtml(title)}
                </span>
                ${note ? `<div class="dp-plan-note-preview"><i class="far fa-comment-dots"></i> ${this.escapeHtml(note)}</div>` : ''}
              </div>
              ${isCarried ? '<span class="dp-carried-icon">⏩</span>' : ''}
            </div>
            <div class="dp-plan-meta">
              <span class="dp-badge dp-badge-${isPhase ? 'phase' : 'task'}">${isPhase ? 'Phase' : 'Task'}</span>
              <span class="dp-badge dp-badge-priority-${priority.toLowerCase()}">${this.formatStatus(priority)}</span>
              <span class="dp-badge dp-badge-status-${status.toLowerCase()}">${this.formatStatus(status)}</span>
              <span class="dp-days-badge dp-days-${daysPending > 30 ? 'danger' : daysPending > 14 ? 'warn' : 'ok'}">${daysPending}d</span>
              <span class="dp-times-planned ${timesPlanned === 0 ? 'dp-times-zero' : ''}">${timesPlanned}x planned</span>
            </div>
            <div class="dp-plan-progress-row">
              <div class="dp-progress-bar"><div class="dp-progress-fill" style="width:${progress}%"></div></div>
              <span class="dp-progress-text">${progress}%</span>
              ${dueDate ? `<span class="dp-due ${this.getDueDateClass(dueDate, status)}">${this.formatDate(dueDate)}</span>` : ''}
            </div>
            <div class="dp-plan-actions">
              <button class="dp-action-btn dp-action-update" data-item-id="${item.id}">✏️ Update & Note</button>
              ${!isFinalized ? `
                <button class="dp-action-btn dp-action-remove" data-item-id="${item.id}">🗑️ Remove</button>
              ` : ''}
            </div>
          </div>
        `;
      }).join('')}
    </div>`;
  }

  private renderOverdueBacklogSubSection(tasks: AvailableTask[]): string {
    if (!tasks || tasks.length === 0) {
      return '<div class="dp-empty" style="padding:14px; font-size:12px; color:#9ca3af; text-align:center;">Great! No overdue backlog tasks pending.</div>';
    }

    return `<div class="dp-plan-list">
      ${tasks.map((task, idx) => {
        const title = task.title || '';
        const priority = (task.priority || 'medium').toLowerCase();
        const status = (task.status || 'pending').toLowerCase();
        const dueDate = task.due_date || '';
        const daysPending = task.days_pending || 0;
        const timesPlanned = task.times_planned || 0;

        return `
          <div class="dp-plan-card dp-plan-card-overdue">
            <div class="dp-plan-header">
              <span class="dp-priority-num dp-priority-num-danger">${idx + 1}</span>
              <div class="dp-plan-title-box">
                <span class="dp-plan-title">
                  <span class="dp-badge dp-badge-backlog">Backlog</span>
                  ${this.escapeHtml(title)}
                </span>
              </div>
            </div>
            <div class="dp-plan-meta">
              <span class="dp-badge dp-badge-task">Task</span>
              <span class="dp-badge dp-badge-priority-${priority}">${this.formatStatus(priority)}</span>
              <span class="dp-badge dp-badge-status-${status}">${this.formatStatus(status)}</span>
              <span class="dp-days-badge dp-days-${daysPending > 30 ? 'danger' : daysPending > 14 ? 'warn' : 'ok'}">${daysPending}d</span>
              <span class="dp-times-planned ${timesPlanned === 0 ? 'dp-times-zero' : ''}">${timesPlanned}x planned</span>
              ${dueDate ? `<span class="dp-due ${this.getDueDateClass(dueDate, status)}">${this.formatDate(dueDate)}</span>` : ''}
            </div>
            <div class="dp-plan-actions">
              <button class="dp-action-btn dp-action-quick-plan" data-task-id="${task.id}" data-mode="planned">+ Plan Today</button>
              <button class="dp-action-btn dp-action-quick-followup" data-task-id="${task.id}" data-mode="followup">+ Follow up</button>
            </div>
          </div>
        `;
      }).join('')}
    </div>`;
  }

  private renderAvailableTasks(): string {
    const planTaskIds = new Set<number>();
    const planPhaseIds = new Set<number>();
    (this.planItems || []).forEach(item => {
      if (item.task_id) planTaskIds.add(item.task_id);
      if (item.phase_id) planPhaseIds.add(item.phase_id);
      if (item.item_type === 'task' && item.source_id) planTaskIds.add(item.source_id);
      if (item.item_type === 'phase' && item.source_id) planPhaseIds.add(item.source_id);
    });

    const sq = this.searchQuery.toLowerCase();
    const sf = this.statusFilter;
    const pf = this.priorityFilter;
    const items: string[] = [];

    this.availableTasks.forEach(task => {
      const matchSearch = !sq || (task.title || '').toLowerCase().includes(sq);
      const matchStatus = sf === 'all' || (task.status || '').toLowerCase() === sf;
      const matchPriority = pf === 'all' || (task.priority || '').toLowerCase() === pf;
      const inPlan = planTaskIds.has(task.id);
      const taskKey = `task-${task.id}`;
      const selected = this.selectedChoices.get(taskKey)?.mode;

      if (matchSearch && matchStatus && matchPriority) {
        items.push(`
          <div class="dp-avail-item ${inPlan ? 'in-plan' : ''}">
            <div class="dp-avail-main">
              <div class="dp-avail-title-row">
                <span class="dp-avail-title">${this.escapeHtml(task.title)}</span>
                ${inPlan ? '<span class="dp-badge dp-badge-in-plan">In Plan</span>' : ''}
              </div>
              <div class="dp-avail-meta">
                <span class="dp-badge dp-badge-priority-${(task.priority || '').toLowerCase()}">${this.formatStatus(task.priority)}</span>
                <span class="dp-badge dp-badge-status-${(task.status || '').toLowerCase()}">${this.formatStatus(task.status)}</span>
                <span class="dp-days-badge dp-days-${(task.days_pending || 0) > 30 ? 'danger' : 'ok'}">${task.days_pending || 0}d</span>
                <span class="dp-times-planned">${task.times_planned || 0}x</span>
                ${task.due_date ? `<span class="dp-due ${this.getDueDateClass(task.due_date, task.status)}">${this.formatDate(task.due_date)}</span>` : ''}
              </div>
            </div>
            ${!inPlan ? `
              <div class="dp-avail-choices">
                <button class="dp-pill-btn dp-pill-plan ${selected === 'plan' ? 'active' : ''}" data-key="${taskKey}" data-type="task" data-id="${task.id}" data-mode="plan">Plan</button>
                <button class="dp-pill-btn dp-pill-followup ${selected === 'followup' ? 'active' : ''}" data-key="${taskKey}" data-type="task" data-id="${task.id}" data-mode="followup">Follow up</button>
              </div>
            ` : ''}
          </div>
        `);
      }

      const phases = task.phases || task.sub_tasks || [];
      phases.forEach((phase, pIdx) => {
        const phaseMatchSearch = !sq || (phase.title || '').toLowerCase().includes(sq) || (task.title || '').toLowerCase().includes(sq);
        const phaseMatchStatus = sf === 'all' || (phase.status || '').toLowerCase() === sf;
        const phaseInPlan = planPhaseIds.has(phase.id);
        const phaseKey = `phase-${phase.id}`;
        const phaseSelected = this.selectedChoices.get(phaseKey)?.mode;

        if (phaseMatchSearch && phaseMatchStatus && (pf === 'all' || (task.priority || '').toLowerCase() === pf)) {
          items.push(`
            <div class="dp-avail-item dp-avail-phase ${phaseInPlan ? 'in-plan' : ''}">
              <div class="dp-avail-main">
                <div class="dp-avail-title-row">
                  <span class="dp-avail-title">↳ P${pIdx + 1}: ${this.escapeHtml(phase.title)}</span>
                  ${phaseInPlan ? '<span class="dp-badge dp-badge-in-plan">In Plan</span>' : ''}
                </div>
                <div class="dp-avail-meta">
                  <span class="dp-badge dp-badge-status-${(phase.status || '').toLowerCase()}">${this.formatStatus(phase.status)}</span>
                  <span class="dp-days-badge dp-days-ok">${phase.days_pending || 0}d</span>
                </div>
              </div>
              ${!phaseInPlan ? `
                <div class="dp-avail-choices">
                  <button class="dp-pill-btn dp-pill-plan ${phaseSelected === 'plan' ? 'active' : ''}" data-key="${phaseKey}" data-type="phase" data-id="${phase.id}" data-task-id="${task.id}" data-mode="plan">Plan</button>
                  <button class="dp-pill-btn dp-pill-followup ${phaseSelected === 'followup' ? 'active' : ''}" data-key="${phaseKey}" data-type="phase" data-id="${phase.id}" data-task-id="${task.id}" data-mode="followup">Follow up</button>
                </div>
              ` : ''}
            </div>
          `);
        }
      });
    });

    const selectedCount = this.selectedChoices.size;

    return `
      <div class="dp-avail-panel">
        <div class="dp-avail-filters">
          <input type="text" class="dp-search-input" id="availSearch" placeholder="Search tasks..." value="${this.searchQuery}">
          <div class="dp-filter-row">
            <select class="dp-filter-select" id="availStatusFilter">
              <option value="all">All Status</option>
              <option value="pending" ${sf === 'pending' ? 'selected' : ''}>Pending</option>
              <option value="in_progress" ${sf === 'in_progress' ? 'selected' : ''}>In Progress</option>
              <option value="on_hold" ${sf === 'on_hold' ? 'selected' : ''}>On Hold</option>
            </select>
            <select class="dp-filter-select" id="availPriorityFilter">
              <option value="all">All Priority</option>
              <option value="low" ${pf === 'low' ? 'selected' : ''}>Low</option>
              <option value="medium" ${pf === 'medium' ? 'selected' : ''}>Medium</option>
              <option value="high" ${pf === 'high' ? 'selected' : ''}>High</option>
              <option value="critical" ${pf === 'critical' ? 'selected' : ''}>Critical</option>
            </select>
          </div>
          <div class="dp-batch-actions">
            <button class="dp-batch-btn" id="batchSelectPlanBtn">All as Plan</button>
            <button class="dp-batch-btn" id="batchSelectFollowupBtn">All as Follow up</button>
            <button class="dp-batch-btn" id="batchClearBtn">Clear</button>
          </div>
        </div>
        <div class="dp-avail-list">
          ${items.length > 0 ? items.join('') : '<div class="dp-empty">No available tasks found</div>'}
        </div>
        ${items.length > 0 ? `
          <button class="dp-add-to-plan-btn" id="addToPlanBtn">
            ➕ Add Selected to Plan (${selectedCount} Items)
          </button>
        ` : ''}
      </div>
    `;
  }

  private renderTeamPlan(): string {
    if (this.loading) {
      return '<div class="loading-state">Loading team plans...</div>';
    }

    const teamStats = this.getTeamStats();

    return `
      <div class="dp-team-filter">
        <select class="dp-filter-select dp-team-select" id="teamMemberFilter">
          <option value="">All Members</option>
          ${this.teamMembers.map(m => `<option value="${m.id}" ${this.selectedMemberId === String(m.id) ? 'selected' : ''}>${m.full_name} (${m.emp_code})</option>`).join('')}
        </select>
      </div>

      <div class="dp-stats-row">
        <div class="dp-stat"><span class="dp-stat-value">${teamStats.membersWithPlans}</span><span class="dp-stat-label">With Plans</span></div>
        <div class="dp-stat completed"><span class="dp-stat-value">${teamStats.totalCompleted}</span><span class="dp-stat-label">Done</span></div>
        <div class="dp-stat in-progress"><span class="dp-stat-value">${teamStats.totalTasks}</span><span class="dp-stat-label">Total</span></div>
        <div class="dp-stat pending"><span class="dp-stat-value">${teamStats.avgCompletion}%</span><span class="dp-stat-label">Avg Done</span></div>
      </div>

      <div class="dp-team-list">
        ${this.teamPlans.length > 0 ? this.teamPlans.map(plan => this.renderTeamMemberCard(plan)).join('') : '<div class="dp-empty">No team plans found for this date</div>'}
      </div>
    `;
  }

  private renderTeamMemberCard(plan: TeamPlanData): string {
    const items = plan.items || [];
    const stats = plan.stats || { total: items.length, completed: 0, in_progress: 0, pending: items.length };
    const initials = this.getInitials(plan.employee_name);

    if (items.length === 0) {
      return `
        <div class="dp-team-card dp-no-plan">
          <div class="dp-team-header">
            <div class="dp-team-avatar">${initials}</div>
            <div class="dp-team-info">
              <span class="dp-team-name">${this.escapeHtml(plan.employee_name)}</span>
              <span class="dp-team-code">${plan.emp_code}</span>
            </div>
            <span class="plan-status-badge no-plan">No Plan</span>
          </div>
        </div>
      `;
    }

    const completionPct = stats.total > 0 ? Math.round((stats.completed / stats.total) * 100) : 0;

    return `
      <div class="dp-team-card">
        <div class="dp-team-header">
          <div class="dp-team-avatar">${initials}</div>
          <div class="dp-team-info">
            <span class="dp-team-name">${this.escapeHtml(plan.employee_name)}</span>
            <span class="dp-team-code">${plan.emp_code}</span>
          </div>
          <span class="plan-status-badge ${plan.is_finalized ? 'finalized' : 'active'}">${plan.is_finalized ? 'Finalized' : 'Active'}</span>
        </div>
        <div class="dp-team-stats-mini">
          <span class="dp-mini-stat">Total: ${stats.total}</span>
          <span class="dp-mini-stat done">Done: ${stats.completed}</span>
          <span class="dp-mini-stat active">Active: ${stats.in_progress}</span>
          <span class="dp-mini-stat pend">Pending: ${stats.pending}</span>
          <span class="dp-mini-stat pct">${completionPct}%</span>
        </div>
        <div class="dp-team-items">
          ${items.slice(0, 5).map(item => {
            const title = item.task_title || item.title || '';
            const status = item.eod_status || item.status || 'pending';
            return `
              <div class="dp-team-item">
                <span class="dp-team-item-title">${this.escapeHtml(title)}</span>
                <span class="dp-badge dp-badge-status-${status.toLowerCase()}">${this.formatStatus(status)}</span>
              </div>
            `;
          }).join('')}
          ${items.length > 5 ? `<div class="dp-team-more">+${items.length - 5} more items</div>` : ''}
        </div>
      </div>
    `;
  }

  private getTeamStats() {
    const plans = this.teamPlans || [];
    let membersWithPlans = 0, totalTasks = 0, totalCompleted = 0;
    plans.forEach(p => {
      if (p.items && p.items.length > 0) {
        membersWithPlans++;
        totalTasks += p.items.length;
        p.items.forEach(item => {
          if ((item.eod_status || item.status || '').toLowerCase() === 'completed') totalCompleted++;
        });
      }
    });
    const avgCompletion = totalTasks > 0 ? Math.round((totalCompleted / totalTasks) * 100) : 0;
    return { membersWithPlans, totalTasks, totalCompleted, avgCompletion };
  }

  private attachMyPlanListeners(): void {
    document.getElementById('toggleAvailableBtn')?.addEventListener('click', async () => {
      this.showAvailable = !this.showAvailable;
      if (this.showAvailable && this.availableTasks.length === 0) {
        await this.loadAvailableTasks();
      }
      this.updateContent();
    });

    document.getElementById('openNewTaskModalBtn')?.addEventListener('click', (e) => {
      e.stopPropagation();
      this.showCreateTaskModal();
    });

    document.getElementById('sharePlanWaBtn')?.addEventListener('click', () => {
      this.shareDayPlanWhatsApp();
    });

    document.getElementById('shareFinalWaBtn')?.addEventListener('click', () => {
      this.shareFinalizedDayWhatsApp();
    });

    document.getElementById('availSearch')?.addEventListener('input', (e) => {
      this.searchQuery = (e.target as HTMLInputElement).value;
      this.updateContent();
    });

    document.getElementById('availStatusFilter')?.addEventListener('change', (e) => {
      this.statusFilter = (e.target as HTMLSelectElement).value;
      this.updateContent();
    });

    document.getElementById('availPriorityFilter')?.addEventListener('change', (e) => {
      this.priorityFilter = (e.target as HTMLSelectElement).value;
      this.updateContent();
    });

    document.querySelectorAll('.dp-pill-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const target = btn as HTMLElement;
        const key = target.dataset.key || '';
        const type = (target.dataset.type || 'task') as 'task' | 'phase';
        const id = parseInt(target.dataset.id || '0');
        const taskId = target.dataset.taskId ? parseInt(target.dataset.taskId) : undefined;
        const mode = (target.dataset.mode || 'plan') as 'plan' | 'followup';

        const current = this.selectedChoices.get(key);
        if (current && current.mode === mode) {
          this.selectedChoices.delete(key);
        } else {
          this.selectedChoices.set(key, { type, id, taskId, mode });
        }
        this.updateContent();
      });
    });

    document.getElementById('batchSelectPlanBtn')?.addEventListener('click', () => {
      this.batchSelectAll('plan');
    });

    document.getElementById('batchSelectFollowupBtn')?.addEventListener('click', () => {
      this.batchSelectAll('followup');
    });

    document.getElementById('batchClearBtn')?.addEventListener('click', () => {
      this.selectedChoices.clear();
      this.updateContent();
    });

    document.getElementById('addToPlanBtn')?.addEventListener('click', () => {
      this.addSelectedToPlan();
    });

    document.querySelectorAll('.dp-action-update').forEach(btn => {
      btn.addEventListener('click', () => {
        const itemId = parseInt((btn as HTMLElement).dataset.itemId || '0');
        this.showUpdateModal(itemId);
      });
    });

    document.querySelectorAll('.dp-action-remove').forEach(btn => {
      btn.addEventListener('click', () => {
        const itemId = parseInt((btn as HTMLElement).dataset.itemId || '0');
        this.removeFromPlan(itemId);
      });
    });

    document.querySelectorAll('.dp-action-quick-plan, .dp-action-quick-followup').forEach(btn => {
      btn.addEventListener('click', async () => {
        const target = btn as HTMLElement;
        const taskId = parseInt(target.dataset.taskId || '0');
        const mode = (target.dataset.mode || 'planned') as 'planned' | 'followup';
        if (taskId) {
          await this.quickAddSingleToPlan(taskId, mode);
        }
      });
    });

    document.getElementById('finalizeBtn')?.addEventListener('click', () => {
      this.showFinalizeModal();
    });
  }

  private batchSelectAll(mode: 'plan' | 'followup'): void {
    const planTaskIds = new Set<number>();
    const planPhaseIds = new Set<number>();
    (this.planItems || []).forEach(item => {
      if (item.task_id) planTaskIds.add(item.task_id);
      if (item.phase_id) planPhaseIds.add(item.phase_id);
    });

    this.availableTasks.forEach(t => {
      if (!planTaskIds.has(t.id)) {
        this.selectedChoices.set(`task-${t.id}`, { type: 'task', id: t.id, mode });
      }
      (t.phases || t.sub_tasks || []).forEach(p => {
        if (!planPhaseIds.has(p.id)) {
          this.selectedChoices.set(`phase-${p.id}`, { type: 'phase', id: p.id, taskId: t.id, mode });
        }
      });
    });
    this.updateContent();
  }

  private attachTeamListeners(): void {
    document.getElementById('teamMemberFilter')?.addEventListener('change', (e) => {
      this.selectedMemberId = (e.target as HTMLSelectElement).value;
      this.loadTeamPlans();
    });
  }

  private async loadTeamPlans(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      let url = `${API_ENDPOINTS.DAY_PLANNER.TEAM}?plan_date=${this.selectedDate}`;
      if (this.selectedMemberId) {
        url += `&employee_id=${this.selectedMemberId}`;
      }
      const response = await apiService.get<any>(url);
      if (response.success && response.data) {
        this.teamPlans = Array.isArray(response.data) ? response.data : (response.data.plans || response.data.team_plans || []);
      }
    } catch (error) {
      console.error('[DayPlannerPage] Failed to load team plans:', error);
      this.teamPlans = [];
    }

    this.loading = false;
    this.updateContent();
  }

  private async addSelectedToPlan(): Promise<void> {
    if (this.selectedChoices.size === 0) {
      this.showToast('Please select at least one task or phase under Plan or Follow up');
      return;
    }

    const items: any[] = [];
    let order = this.planItems.length + 1;

    this.selectedChoices.forEach(choice => {
      const isFollowup = choice.mode === 'followup';
      const entry: any = {
        item_type: choice.type,
        priority_order: order++,
        plan_type: choice.mode,
        is_followup: isFollowup
      };
      if (choice.type === 'task') {
        entry.task_id = choice.id;
      } else {
        entry.phase_id = choice.id;
        entry.task_id = choice.taskId || null;
      }
      items.push(entry);
    });

    try {
      const response = await apiService.post<any>(API_ENDPOINTS.DAY_PLANNER.CREATE_OR_UPDATE, {
        plan_date: this.selectedDate,
        items,
        append: true
      });
      if (response.success) {
        this.showToast('Items added to plan successfully');
        this.selectedChoices.clear();
        this.showAvailable = false;
        await this.loadPlan();
        this.availableTasks = [];
      } else {
        this.showToast(response.error || 'Failed to add items');
      }
    } catch (error) {
      this.showToast('Failed to add items to plan');
    }
  }

  private async removeFromPlan(itemId: number): Promise<void> {
    if (!confirm('Remove this item from the plan?')) return;

    try {
      const response = await apiService.delete<any>(API_ENDPOINTS.DAY_PLANNER.DELETE_ITEM(itemId));
      if (response.success) {
        this.showToast('Item removed');
        await this.loadPlan();
      } else {
        this.showToast(response.error || 'Failed to remove item');
      }
    } catch (error) {
      this.showToast('Failed to remove item');
    }
  }

  private async quickAddSingleToPlan(taskId: number, mode: 'planned' | 'followup'): Promise<void> {
    const isFollowup = mode === 'followup';
    const entry = {
      item_type: 'task',
      task_id: taskId,
      priority_order: (this.planItems || []).length + 1,
      plan_type: mode,
      is_followup: isFollowup
    };
    try {
      const response = await apiService.post<any>(API_ENDPOINTS.DAY_PLANNER.CREATE_OR_UPDATE, {
        plan_date: this.selectedDate,
        items: [entry],
        append: true
      });
      if (response.success) {
        this.showToast(`Task added to ${isFollowup ? 'follow-ups' : 'today plan'} successfully`);
        await Promise.all([
          this.loadPlan(),
          this.loadAvailableTasks()
        ]);
      } else {
        this.showToast(response.error || 'Failed to add task');
      }
    } catch {
      this.showToast('Failed to add task');
    }
  }

  private async showCreateTaskModal(): Promise<void> {
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    tomorrow.setHours(17, 0, 0, 0);
    const defaultDue = tomorrow.toISOString().slice(0, 16);

    let employees: Array<{ id: number; emp_code: string; full_name: string; department?: string }> = [];
    try {
      const empResp = await apiService.get<any>('/staff/tasks/assignable-employees?limit=500');
      const data = empResp.data as any;
      if (empResp.success !== false && data) {
        const empArr = data.employees || (Array.isArray(data) ? data : []);
        employees = empArr.map((e: any) => ({
          id: e.id,
          emp_code: e.employee_code || e.emp_code || '',
          full_name: e.full_name || '',
          department: e.department || ''
        }));
      }
    } catch (e) {
      employees = (this.teamMembers || []).map(m => ({
        id: m.id,
        emp_code: m.emp_code || '',
        full_name: m.full_name || '',
        department: ''
      }));
    }

    const selectedSecondary: Array<{ id: number; full_name: string; emp_code: string }> = [];
    let phasesEnabled = false;
    const phases: Array<{ phase_number: number; phase_title: string; phase_assignee_id: number; target_date: string }> = [];
    const attachmentFiles: File[] = [];

    const modal = document.createElement('div');
    modal.className = 'dp-modal-overlay';
    modal.innerHTML = `
      <div class="dp-modal dp-modal-lg" style="max-height:88vh; display:flex; flex-direction:column;">
        <div class="dp-modal-header" style="background:linear-gradient(135deg, #4f46e5, #7c3aed);">
          <span>➕ Create New Task (Full Task Manager)</span>
          <button class="dp-modal-close" id="closeCreateTaskModal">✕</button>
        </div>
        <div class="dp-modal-body" style="overflow-y:auto; flex:1; padding:16px;">
          <!-- Section 1: Core Details -->
          <div class="dp-form-group">
            <label>Task Title <span style="color:#ef4444;">*</span></label>
            <input type="text" id="newTaskTitle" class="dp-form-input" placeholder="e.g. Prepare client deed documentation" maxlength="200" required>
            <div style="text-align:right; font-size:11px; color:#9ca3af; margin-top:2px;"><span id="newTitleCount">0</span>/200</div>
          </div>

          <div class="dp-form-group">
            <label>Description</label>
            <textarea id="newTaskDesc" class="dp-form-input dp-textarea" rows="3" placeholder="Detailed objectives, scope, or execution notes..." maxlength="2000"></textarea>
            <div style="text-align:right; font-size:11px; color:#9ca3af; margin-top:2px;"><span id="newDescCount">0</span>/2000</div>
          </div>

          <div class="dp-form-row" style="display:flex; gap:8px;">
            <div class="dp-form-group" style="flex:1;">
              <label>Priority <span style="color:#ef4444;">*</span></label>
              <select id="newTaskPriority" class="dp-form-input">
                <option value="medium" selected>Medium</option>
                <option value="low">Low</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
            </div>
            <div class="dp-form-group" style="flex:1;">
              <label>Category <span style="color:#ef4444;">*</span></label>
              <select id="newTaskCategory" class="dp-form-input">
                <option value="General" selected>General</option>
                <option value="Development">Development</option>
                <option value="Support">Support</option>
                <option value="Admin">Admin</option>
                <option value="Meeting">Meeting</option>
                <option value="Review">Review</option>
                <option value="Documentation">Documentation</option>
                <option value="Sales">Sales</option>
                <option value="Operations">Operations</option>
                <option value="Legal">Legal</option>
                <option value="Finance">Finance</option>
                <option value="Field">Field</option>
                <option value="Technical">Technical</option>
                <option value="Other">Other</option>
              </select>
            </div>
          </div>

          <div class="dp-form-row" style="display:flex; gap:8px;">
            <div class="dp-form-group" style="flex:1;">
              <label>Due Date &amp; Time <span style="color:#ef4444;">*</span></label>
              <input type="datetime-local" id="newTaskDueDate" class="dp-form-input" value="${defaultDue}">
            </div>
            <div class="dp-form-group" style="flex:1;">
              <label>Est. Hours</label>
              <input type="number" id="newTaskHours" class="dp-form-input" placeholder="e.g. 3.5" min="0.5" step="0.5">
            </div>
          </div>

          <!-- Section 2: Assignments -->
          <div style="background:#13132b; padding:12px; border-radius:8px; border:1px solid #2a2a4a; margin-bottom:12px;">
            <div style="font-weight:700; font-size:13px; color:#a5b4fc; margin-bottom:8px;">
              <i class="fas fa-users-cog me-1"></i> Staff Assignment
            </div>
            
            <div class="dp-form-group">
              <label>Primary Assignee <span style="color:#ef4444;">*</span></label>
              <select id="newTaskPrimaryAssignee" class="dp-form-input">
                <option value="self">Assign to Myself (Self)</option>
                ${employees.map(e => `<option value="${e.id}">${this.escapeHtml(e.full_name)} (${e.emp_code || e.id})${e.department ? ' - ' + this.escapeHtml(e.department) : ''}</option>`).join('')}
              </select>
            </div>

            <div class="dp-form-group" style="margin-bottom:0;">
              <label>Secondary Assignees <small style="color:#9ca3af;">(Max 2)</small></label>
              <div style="display:flex; gap:6px;">
                <select id="secondaryEmpSelect" class="dp-form-input" style="flex:1;">
                  <option value="">Select Collaborator / Staff...</option>
                  ${employees.map(e => `<option value="${e.id}">${this.escapeHtml(e.full_name)} (${e.emp_code || e.id})</option>`).join('')}
                </select>
                <button type="button" class="dp-btn dp-btn-secondary" id="addSecondaryBtn" style="padding:4px 10px; font-size:12px;">+ Add</button>
              </div>
              <div id="secondaryChipsContainer" style="display:flex; flex-wrap:wrap; gap:6px; margin-top:8px;"></div>
            </div>
          </div>

          <!-- Section 3: Contact & Metadata -->
          <div class="dp-form-row" style="display:flex; gap:8px;">
            <div class="dp-form-group" style="flex:1;">
              <label>Contact Person</label>
              <input type="text" id="newTaskContactPerson" class="dp-form-input" placeholder="e.g. Mr. Sharma">
            </div>
            <div class="dp-form-group" style="flex:1;">
              <label>Contact Mobile</label>
              <input type="tel" id="newTaskContactPhone" class="dp-form-input" placeholder="e.g. 9876543210">
            </div>
          </div>

          <div class="dp-form-group">
            <label>Tags <small style="color:#9ca3af;">(comma separated)</small></label>
            <input type="text" id="newTaskTags" class="dp-form-input" placeholder="e.g. urgent, registration, payment">
          </div>

          <!-- Section 4: Multi-Stage Phases (Collapsible) -->
          <div style="background:#13132b; padding:12px; border-radius:8px; border:1px solid #2a2a4a; margin-bottom:12px;">
            <label style="display:flex; align-items:center; justify-content:space-between; cursor:pointer;">
              <span style="font-weight:700; font-size:13px; color:#38bdf8;"><i class="fas fa-layer-group me-1"></i> Multi-Stage Task (Add Phases)</span>
              <input type="checkbox" id="togglePhasesCheckbox" style="width:18px; height:18px; accent-color:#38bdf8;">
            </label>
            <div id="phasesFormWrapper" style="display:none; margin-top:10px;">
              <div id="phasesDynamicContainer"></div>
              <button type="button" class="dp-btn dp-btn-secondary" id="addPhaseBtn" style="width:100%; margin-top:6px; font-size:12px;">+ Add Phase</button>
            </div>
          </div>

          <!-- Section 5: Attachments -->
          <div style="background:#13132b; padding:12px; border-radius:8px; border:1px solid #2a2a4a; margin-bottom:12px;">
            <label style="font-weight:700; font-size:13px; color:#cbd5e1; margin-bottom:6px; display:block;">
              <i class="fas fa-paperclip me-1"></i> Attachments <small style="color:#9ca3af;">(Max 2 files, up to 5MB)</small>
            </label>
            <input type="file" id="newTaskFilesInput" multiple accept="image/*,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt" style="display:none;">
            <button type="button" class="dp-btn dp-btn-secondary" id="pickFilesBtn" style="width:100%; font-size:12px; padding:8px;">📎 Tap to attach files</button>
            <div id="fileListContainer" style="margin-top:6px; font-size:12px; color:#a5b4fc;"></div>
          </div>

          <!-- Section 6: Direct Day Plan Option -->
          <div class="dp-form-group" style="background:#0f0f23; padding:12px; border-radius:8px; border:1px solid #6366f1;">
            <label style="display:flex; align-items:center; gap:8px; cursor:pointer; color:#e2e8f0; font-size:13px; margin-bottom:6px;">
              <input type="checkbox" id="addToPlanImmediately" checked style="width:18px; height:18px; accent-color:#6366f1;">
              <span><strong>Add directly to Today's Plan as:</strong></span>
            </label>
            <div style="display:flex; gap:14px; margin-left:26px;">
              <label style="display:flex; align-items:center; gap:6px; font-size:13px; color:#cbd5e1; cursor:pointer;">
                <input type="radio" name="newTaskPlanMode" value="plan" checked style="accent-color:#6366f1;"> Regular Plan
              </label>
              <label style="display:flex; align-items:center; gap:6px; font-size:13px; color:#fbbf24; cursor:pointer;">
                <input type="radio" name="newTaskPlanMode" value="followup" style="accent-color:#f59e0b;"> Follow up
              </label>
            </div>
          </div>
        </div>
        <div class="dp-modal-footer">
          <button class="dp-btn dp-btn-secondary" id="cancelCreateTaskBtn">Cancel</button>
          <button class="dp-btn dp-btn-primary" id="confirmCreateTaskBtn">Create Task</button>
        </div>
      </div>
    `;

    document.body.appendChild(modal);

    const closeModal = () => modal.remove();
    document.getElementById('closeCreateTaskModal')?.addEventListener('click', closeModal);
    document.getElementById('cancelCreateTaskBtn')?.addEventListener('click', closeModal);
    modal.addEventListener('click', (e) => { if (e.target === modal) closeModal(); });

    // Counters
    document.getElementById('newTaskTitle')?.addEventListener('input', (e) => {
      const c = document.getElementById('newTitleCount');
      if (c) c.textContent = String((e.target as HTMLInputElement).value.length);
    });
    document.getElementById('newTaskDesc')?.addEventListener('input', (e) => {
      const c = document.getElementById('newDescCount');
      if (c) c.textContent = String((e.target as HTMLTextAreaElement).value.length);
    });

    // Secondary Assignees
    const renderSecondaryChips = () => {
      const container = document.getElementById('secondaryChipsContainer');
      if (!container) return;
      container.innerHTML = selectedSecondary.map((s, idx) => `
        <span style="display:inline-flex; align-items:center; gap:4px; background:#4f46e5; color:#fff; padding:3px 8px; border-radius:12px; font-size:11px;">
          ${this.escapeHtml(s.full_name)}
          <button type="button" class="remove-sec-btn" data-idx="${idx}" style="background:none; border:none; color:#fff; cursor:pointer; font-weight:700; font-size:13px; padding:0 2px;">✕</button>
        </span>
      `).join('');

      container.querySelectorAll('.remove-sec-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
          e.stopPropagation();
          const idx = parseInt((btn as HTMLElement).dataset.idx || '0');
          selectedSecondary.splice(idx, 1);
          renderSecondaryChips();
        });
      });
    };

    document.getElementById('addSecondaryBtn')?.addEventListener('click', () => {
      const sel = document.getElementById('secondaryEmpSelect') as HTMLSelectElement;
      const empId = parseInt(sel?.value || '0');
      if (!empId) return;
      if (selectedSecondary.length >= 2) {
        this.showToast('Max 2 secondary assignees allowed');
        return;
      }
      if (selectedSecondary.some(s => s.id === empId)) {
        this.showToast('Employee already added');
        return;
      }
      const found = employees.find(e => e.id === empId);
      if (found) {
        selectedSecondary.push({ id: found.id, full_name: found.full_name, emp_code: found.emp_code });
        renderSecondaryChips();
        sel.value = '';
      }
    });

    // Phases toggle & dynamic rows
    const togglePhases = document.getElementById('togglePhasesCheckbox') as HTMLInputElement;
    const phasesWrapper = document.getElementById('phasesFormWrapper');
    togglePhases?.addEventListener('change', () => {
      phasesEnabled = togglePhases.checked;
      if (phasesWrapper) phasesWrapper.style.display = phasesEnabled ? 'block' : 'none';
      if (phasesEnabled && phases.length === 0) {
        addPhaseRow();
      }
    });

    const renderPhases = () => {
      const container = document.getElementById('phasesDynamicContainer');
      if (!container) return;
      container.innerHTML = phases.map((p, idx) => `
        <div style="background:#1e1e38; padding:8px; border-radius:6px; margin-bottom:6px; border:1px solid #333355;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
            <span style="font-weight:700; font-size:12px; color:#818cf8;">Phase ${p.phase_number}</span>
            <button type="button" class="remove-phase-btn" data-idx="${idx}" style="background:none; border:none; color:#ef4444; cursor:pointer; font-size:13px;">✕</button>
          </div>
          <input type="text" class="dp-form-input phase-title-input" data-idx="${idx}" placeholder="Phase title *" value="${this.escapeHtml(p.phase_title)}" style="margin-bottom:4px; font-size:12px; padding:6px 8px;">
          <div style="display:flex; gap:6px;">
            <select class="dp-form-input phase-assignee-select" data-idx="${idx}" style="flex:1; font-size:12px; padding:6px 8px;">
              <option value="">Select Assignee...</option>
              ${employees.map(e => `<option value="${e.id}" ${p.phase_assignee_id === e.id ? 'selected' : ''}>${this.escapeHtml(e.full_name)}</option>`).join('')}
            </select>
            <input type="datetime-local" class="dp-form-input phase-date-input" data-idx="${idx}" value="${p.target_date || defaultDue}" style="flex:1; font-size:12px; padding:6px 8px;">
          </div>
        </div>
      `).join('');

      container.querySelectorAll('.remove-phase-btn').forEach(btn => {
        btn.addEventListener('click', () => {
          const idx = parseInt((btn as HTMLElement).dataset.idx || '0');
          phases.splice(idx, 1);
          phases.forEach((p, i) => p.phase_number = i + 1);
          renderPhases();
        });
      });
      container.querySelectorAll('.phase-title-input').forEach(inp => {
        inp.addEventListener('input', (e) => {
          const idx = parseInt((inp as HTMLElement).dataset.idx || '0');
          if (phases[idx]) phases[idx].phase_title = (e.target as HTMLInputElement).value;
        });
      });
      container.querySelectorAll('.phase-assignee-select').forEach(sel => {
        sel.addEventListener('change', (e) => {
          const idx = parseInt((sel as HTMLElement).dataset.idx || '0');
          if (phases[idx]) phases[idx].phase_assignee_id = parseInt((e.target as HTMLSelectElement).value) || 0;
        });
      });
      container.querySelectorAll('.phase-date-input').forEach(inp => {
        inp.addEventListener('input', (e) => {
          const idx = parseInt((inp as HTMLElement).dataset.idx || '0');
          if (phases[idx]) phases[idx].target_date = (e.target as HTMLInputElement).value;
        });
      });
    };

    const addPhaseRow = () => {
      phases.push({
        phase_number: phases.length + 1,
        phase_title: '',
        phase_assignee_id: 0,
        target_date: defaultDue
      });
      renderPhases();
    };

    document.getElementById('addPhaseBtn')?.addEventListener('click', addPhaseRow);

    // Attachments
    const fileInput = document.getElementById('newTaskFilesInput') as HTMLInputElement;
    document.getElementById('pickFilesBtn')?.addEventListener('click', () => fileInput?.click());
    fileInput?.addEventListener('change', () => {
      if (!fileInput.files) return;
      for (let i = 0; i < fileInput.files.length; i++) {
        if (attachmentFiles.length >= 2) {
          this.showToast('Max 2 files allowed');
          break;
        }
        attachmentFiles.push(fileInput.files[i]);
      }
      fileInput.value = '';
      const listEl = document.getElementById('fileListContainer');
      if (listEl) {
        listEl.innerHTML = attachmentFiles.map((f, i) => `
          <div>📎 ${this.escapeHtml(f.name)} (${(f.size / 1024).toFixed(0)} KB)</div>
        `).join('');
      }
    });

    // Submit
    document.getElementById('confirmCreateTaskBtn')?.addEventListener('click', async () => {
      const titleInput = document.getElementById('newTaskTitle') as HTMLInputElement;
      const title = titleInput?.value.trim();
      if (!title || title.length < 3) {
        this.showToast('Please enter a task title (min 3 chars)');
        titleInput?.focus();
        return;
      }

      const priority = (document.getElementById('newTaskPriority') as HTMLSelectElement)?.value || 'medium';
      const category = (document.getElementById('newTaskCategory') as HTMLSelectElement)?.value || 'General';
      const dueDate = (document.getElementById('newTaskDueDate') as HTMLInputElement)?.value || defaultDue;
      const desc = (document.getElementById('newTaskDesc') as HTMLTextAreaElement)?.value.trim() || '';
      const hours = parseFloat((document.getElementById('newTaskHours') as HTMLInputElement)?.value) || null;
      const contactPerson = (document.getElementById('newTaskContactPerson') as HTMLInputElement)?.value.trim() || null;
      const contactPhone = (document.getElementById('newTaskContactPhone') as HTMLInputElement)?.value.trim() || null;
      const tagsRaw = (document.getElementById('newTaskTags') as HTMLInputElement)?.value.trim();
      const primaryAssigneeVal = (document.getElementById('newTaskPrimaryAssignee') as HTMLSelectElement)?.value;
      const addDirectly = (document.getElementById('addToPlanImmediately') as HTMLInputElement)?.checked;
      const planMode = (document.querySelector('input[name="newTaskPlanMode"]:checked') as HTMLInputElement)?.value || 'plan';

      const userState = (apiService as any).authState?.user || {};
      let resolvedPrimaryAssigneeId: number | null = null;
      if (primaryAssigneeVal && primaryAssigneeVal !== 'self') {
        resolvedPrimaryAssigneeId = parseInt(primaryAssigneeVal);
      } else if (userState.id) {
        resolvedPrimaryAssigneeId = userState.id;
      }

      if (phasesEnabled && phases.length > 0) {
        for (const p of phases) {
          if (!p.phase_title || p.phase_title.length < 3) {
            this.showToast(`Phase ${p.phase_number}: Title is required`);
            return;
          }
          if (!p.phase_assignee_id) {
            this.showToast(`Phase ${p.phase_number}: Please select an assignee`);
            return;
          }
        }
      }

      const confirmBtn = document.getElementById('confirmCreateTaskBtn') as HTMLButtonElement;
      if (confirmBtn) {
        confirmBtn.disabled = true;
        confirmBtn.textContent = 'Creating...';
      }

      try {
        const payload: any = {
          title,
          description: desc,
          priority,
          category,
          due_date: dueDate,
          estimated_hours: hours,
          tags: tagsRaw ? tagsRaw.split(',').map(t => t.trim()).filter(Boolean) : []
        };
        if (resolvedPrimaryAssigneeId) {
          payload.primary_assignee_id = resolvedPrimaryAssigneeId;
        }
        if (selectedSecondary.length > 0) {
          payload.secondary_assignee_ids = selectedSecondary.map(s => s.id);
        }
        if (contactPerson) payload.contact_person = contactPerson;
        if (contactPhone) payload.contact_phone = contactPhone;

        if (phasesEnabled && phases.length > 0) {
          payload.phases = phases.map(p => ({
            phase_number: p.phase_number,
            phase_title: p.phase_title,
            phase_assignee_id: p.phase_assignee_id,
            target_date: p.target_date || null
          }));
        }

        const taskResp = await apiService.post<any>('/staff/tasks/', payload);
        if (taskResp.success && (taskResp.data?.task?.id || taskResp.data?.id)) {
          const newTaskId = taskResp.data?.task?.id || taskResp.data?.id;

          // Upload attachments if any
          if (attachmentFiles.length > 0) {
            for (const file of attachmentFiles) {
              try {
                const formData = new FormData();
                formData.append('file', file);
                await fetch(`/api/v1/staff/tasks/${newTaskId}/attachments`, {
                  method: 'POST',
                  headers: { 'Authorization': `Bearer ${localStorage.getItem('staff_token')}` },
                  body: formData
                });
              } catch (err) {
                console.warn('[DayPlannerPage] Attachment upload failed:', err);
              }
            }
          }

          this.showToast('Task created successfully!');
          closeModal();

          if (addDirectly) {
            const planEntry = {
              item_type: 'task',
              task_id: newTaskId,
              priority_order: this.planItems.length + 1,
              plan_type: planMode,
              is_followup: planMode === 'followup'
            };
            await apiService.post<any>(API_ENDPOINTS.DAY_PLANNER.CREATE_OR_UPDATE, {
              plan_date: this.selectedDate,
              items: [planEntry],
              append: true
            });
          }

          await Promise.all([
            this.loadPlan(),
            this.loadAvailableTasks()
          ]);
        } else {
          this.showToast(taskResp.error || 'Failed to create task');
          if (confirmBtn) {
            confirmBtn.disabled = false;
            confirmBtn.textContent = 'Create Task';
          }
        }
      } catch (err) {
        this.showToast('Failed to create task');
        if (confirmBtn) {
          confirmBtn.disabled = false;
        }
      }
    });
  }

  private showUpdateModal(itemId: number): void {
    const item = this.planItems.find(i => i.id === itemId);
    if (!item) return;

    const status = (item.eod_status || item.status || 'pending').toLowerCase();
    const progress = item.eod_progress != null ? item.eod_progress : (item.progress || 0);
    const notes = item.eod_notes || item.notes || '';

    const modal = document.createElement('div');
    modal.className = 'dp-modal-overlay';
    modal.innerHTML = `
      <div class="dp-modal">
        <div class="dp-modal-header">
          <span>✏️ Update Task &amp; Staff Note</span>
          <button class="dp-modal-close" id="closeUpdateModal">✕</button>
        </div>
        <div class="dp-modal-body">
          <div class="dp-form-group">
            <label>EOD Status</label>
            <select id="eodStatusSelect" class="dp-form-input">
              <option value="pending" ${status === 'pending' ? 'selected' : ''}>Pending</option>
              <option value="in_progress" ${status === 'in_progress' ? 'selected' : ''}>In Progress</option>
              <option value="completed" ${status === 'completed' ? 'selected' : ''}>Completed</option>
              <option value="on_hold" ${status === 'on_hold' ? 'selected' : ''}>On Hold</option>
              <option value="cancelled" ${status === 'cancelled' ? 'selected' : ''}>Cancelled</option>
            </select>
          </div>
          <div class="dp-form-group">
            <label>Progress: <span id="progressValue">${progress}%</span></label>
            <input type="range" id="eodProgressRange" class="dp-range-input" min="0" max="100" step="5" value="${progress}">
          </div>
          <div class="dp-form-group">
            <label>Time Spent (minutes) <small style="color:#9ca3af;">→ auto-logs to timesheet</small></label>
            <input type="number" id="eodTimeSpentInput" class="dp-form-input" min="1" max="1440" placeholder="e.g. 60" value="${item.time_spent_minutes || ''}">
          </div>
          <div class="dp-form-group">
            <label>Staff Comment / Progress Notes</label>
            <textarea id="eodNotesInput" class="dp-form-input dp-textarea" rows="3" placeholder="Enter actual comment / execution details...">${notes}</textarea>
          </div>
        </div>
        <div class="dp-modal-footer">
          <button class="dp-btn dp-btn-secondary" id="cancelUpdateBtn">Cancel</button>
          <button class="dp-btn dp-btn-primary" id="saveUpdateBtn">Save Status &amp; Comment</button>
        </div>
      </div>
    `;

    document.body.appendChild(modal);

    document.getElementById('eodProgressRange')?.addEventListener('input', (e) => {
      const val = (e.target as HTMLInputElement).value;
      const pv = document.getElementById('progressValue');
      if (pv) pv.textContent = val + '%';
    });

    const closeModal = () => modal.remove();
    document.getElementById('closeUpdateModal')?.addEventListener('click', closeModal);
    document.getElementById('cancelUpdateBtn')?.addEventListener('click', closeModal);
    modal.addEventListener('click', (e) => { if (e.target === modal) closeModal(); });

    document.getElementById('saveUpdateBtn')?.addEventListener('click', async () => {
      const timeSpentRaw = (document.getElementById('eodTimeSpentInput') as HTMLInputElement)?.value;
      const timeSpentMins = timeSpentRaw ? parseInt(timeSpentRaw) : null;
      const data: any = {
        eod_status: (document.getElementById('eodStatusSelect') as HTMLSelectElement).value,
        eod_progress: parseInt((document.getElementById('eodProgressRange') as HTMLInputElement).value),
        eod_notes: (document.getElementById('eodNotesInput') as HTMLTextAreaElement).value
      };
      if (timeSpentMins && timeSpentMins >= 1 && timeSpentMins <= 1440) {
        data.time_spent_minutes = timeSpentMins;
      }

      try {
        const response = await apiService.patch<any>(API_ENDPOINTS.DAY_PLANNER.UPDATE_ITEM(itemId), data);
        if (response.success) {
          this.showToast('Status & comment updated');
          closeModal();
          await this.loadPlan();
        } else {
          this.showToast(response.error || 'Failed to update');
        }
      } catch (error) {
        this.showToast('Failed to update status');
      }
    });
  }

  private showFinalizeModal(): void {
    const stats = this.getStats();
    const items = this.planItems || [];

    const modal = document.createElement('div');
    modal.className = 'dp-modal-overlay';
    modal.innerHTML = `
      <div class="dp-modal dp-modal-lg">
        <div class="dp-modal-header">
          <span>🏁 Finalize Day Plan &amp; Review</span>
          <button class="dp-modal-close" id="closeFinalizeModal">✕</button>
        </div>
        <div class="dp-modal-body">
          <p style="font-size:12px; color:#9ca3af; margin-bottom:10px;">Review tasks, update status, and enter your actual comments before final day closure.</p>
          <div class="dp-finalize-summary">
            <div class="dp-summary-row"><span>Total Items</span><strong>${stats.total}</strong></div>
            <div class="dp-summary-row"><span>Completed</span><strong class="done">${stats.completed}</strong></div>
            <div class="dp-summary-row"><span>In Progress</span><strong class="active">${stats.inProgress}</strong></div>
            <div class="dp-summary-row"><span>Pending</span><strong class="pend">${stats.pending}</strong></div>
          </div>

          <div class="dp-finalize-checklist">
            ${items.map(item => {
              const title = item.task_title || item.title || 'Task';
              const st = (item.eod_status || item.status || 'pending').toLowerCase();
              const prog = item.eod_progress != null ? item.eod_progress : (item.progress || 0);
              const note = item.eod_notes || item.notes || '';
              const isFollowup = item.is_followup || item.plan_type === 'followup';

              return `
                <div class="dp-fin-card">
                  <div class="dp-fin-title">
                    <span class="dp-badge ${isFollowup ? 'dp-badge-followup' : 'dp-badge-task'}">${isFollowup ? 'Follow up' : 'Plan'}</span>
                    <strong>${this.escapeHtml(title)}</strong>
                  </div>
                  <div class="dp-fin-controls">
                    <select class="dp-form-input dp-fin-status-select" id="fin_st_${item.id}">
                      <option value="completed" ${st === 'completed' ? 'selected' : ''}>Completed</option>
                      <option value="in_progress" ${st === 'in_progress' ? 'selected' : ''}>In Progress</option>
                      <option value="pending" ${st === 'pending' ? 'selected' : ''}>Pending</option>
                      <option value="on_hold" ${st === 'on_hold' ? 'selected' : ''}>On Hold</option>
                      <option value="cancelled" ${st === 'cancelled' ? 'selected' : ''}>Cancelled</option>
                    </select>
                    <input type="number" min="0" max="100" class="dp-form-input dp-fin-prog-input" id="fin_prog_${item.id}" value="${prog}" placeholder="%">
                  </div>
                  <input type="text" class="dp-form-input dp-fin-note-input" id="fin_note_${item.id}" value="${this.escapeHtml(note)}" placeholder="Enter actual comment / execution details...">
                </div>
              `;
            }).join('')}
          </div>
        </div>
        <div class="dp-modal-footer">
          <button class="dp-btn dp-btn-secondary" id="cancelFinalizeBtn">Cancel</button>
          <button class="dp-btn dp-btn-primary" id="confirmFinalizeBtn">Confirm &amp; Finalize Day</button>
        </div>
      </div>
    `;

    document.body.appendChild(modal);

    const closeModal = () => modal.remove();
    document.getElementById('closeFinalizeModal')?.addEventListener('click', closeModal);
    document.getElementById('cancelFinalizeBtn')?.addEventListener('click', closeModal);
    modal.addEventListener('click', (e) => { if (e.target === modal) closeModal(); });

    document.getElementById('confirmFinalizeBtn')?.addEventListener('click', async () => {
      const itemUpdates = (this.planItems || []).map(item => {
        const stEl = document.getElementById(`fin_st_${item.id}`) as HTMLSelectElement;
        const progEl = document.getElementById(`fin_prog_${item.id}`) as HTMLInputElement;
        const noteEl = document.getElementById(`fin_note_${item.id}`) as HTMLInputElement;
        return {
          id: item.id,
          eod_status: stEl ? stEl.value : (item.eod_status || item.status || 'pending'),
          eod_progress: progEl ? parseInt(progEl.value) || 0 : (item.eod_progress != null ? item.eod_progress : (item.progress || 0)),
          eod_notes: noteEl ? noteEl.value.trim() : (item.eod_notes || '')
        };
      });

      try {
        const response = await apiService.post<any>(API_ENDPOINTS.DAY_PLANNER.FINALIZE, {
          plan_date: this.selectedDate,
          items: itemUpdates
        });
        if (response.success) {
          this.showToast('Day plan finalized successfully!');
          closeModal();
          await this.loadPlan();
        } else {
          this.showToast(response.error || 'Failed to finalize');
        }
      } catch (error) {
        this.showToast('Failed to finalize plan');
      }
    });
  }

  private async shareDayPlanWhatsApp(): Promise<void> {
    const userState = (apiService as any).authState?.user || {};
    const empCode = userState.emp_code || 'Staff';
    const staffName = userState.name || userState.full_name || 'Staff Member';
    const dateStr = this.selectedDate;

    if (!this.availableTasks || this.availableTasks.length === 0) {
      await this.loadAvailableTasks();
    }

    let msg = `🌟 *DAILY TASK PLAN | ${dateStr.toUpperCase()}*\n`;
    msg += `👤 *Staff Member:* ${staffName} (${empCode})\n`;
    msg += `🏢 *Company:* MyntReal LLP\n\n`;

    msg += `=================================\n`;
    msg += `⏱️ *ATTENDANCE & LOCATION*\n`;
    msg += `=================================\n`;
    msg += `🟢 *Logged In:* 09:15 AM\n`;
    msg += `📍 *Area / Location:* Office / Field Area\n\n`;

    const plannedList = (this.planItems || []).filter(i => !i.is_followup && i.plan_type !== 'followup');
    const followupList = (this.planItems || []).filter(i => i.is_followup || i.plan_type === 'followup');

    const planTaskIds = new Set<number>();
    (this.planItems || []).forEach(item => {
      if (item.task_id) planTaskIds.add(item.task_id);
      if (item.item_type === 'task' && item.source_id) planTaskIds.add(item.source_id);
    });

    const overdueItems = (this.availableTasks || []).filter(t => 
      !planTaskIds.has(t.id) && ((t.days_pending || 0) > 0 || (t.times_planned || 0) > 0)
    );

    const totalPlanned = plannedList.length + followupList.length;

    msg += `=================================\n`;
    msg += `📊 *DAY PLAN SUMMARY & TARGETS*\n`;
    msg += `=================================\n`;
    msg += `📌 *Total Planned for Today:* ${totalPlanned} Items\n`;
    msg += `🔹 *Planned Activities / Tasks:* ${plannedList.length}\n`;
    msg += `🔸 *Follow-up Activities:* ${followupList.length}\n`;
    msg += `⚠️ *Overdue Backlog Pending:* ${overdueItems.length} Tasks\n`;
    msg += `🎯 *Target Execution Rate:* 100%\n\n`;

    msg += `=================================\n`;
    msg += `📋 *1. PLANNED FOR THE DAY (${plannedList.length} Tasks)*\n`;
    msg += `=================================\n`;

    if (plannedList.length > 0) {
      plannedList.forEach((item, idx) => {
        const title = item.task_title || item.title || 'Task';
        const prio = (item.priority || item.task_priority || 'medium').toUpperCase();
        const daysP = item.days_pending || 0;
        const timesP = item.times_planned || 1;
        const status = (item.task_status || item.status || 'planned').toUpperCase();
        const note = (item.eod_notes || item.notes || '').trim();

        msg += `${idx + 1}. 🔹 *${title}*\n`;
        msg += `   • Priority: ${prio} | Status: ${status}\n`;
        msg += `   • Days Active/Pending: ${daysP}d\n`;
        msg += `   • Times Planned: Planned ${timesP} time(s)\n`;
        if (note) msg += `   • *Staff Note:* ${note}\n`;
      });
    } else {
      msg += `• No regular tasks scheduled for today.\n`;
    }

    msg += `\n=================================\n`;
    msg += `🔄 *2. FOLLOW UPS (${followupList.length} Tasks)*\n`;
    msg += `=================================\n`;

    if (followupList.length > 0) {
      followupList.forEach((item, idx) => {
        const title = item.task_title || item.title || 'Task';
        const prio = (item.priority || item.task_priority || 'medium').toUpperCase();
        const daysP = item.days_pending || 0;
        const timesP = item.times_planned || 1;
        const status = (item.task_status || item.status || 'planned').toUpperCase();
        const note = (item.eod_notes || item.notes || '').trim();

        msg += `${idx + 1}. 🔸 *${title}* (Follow up)\n`;
        msg += `   • Priority: ${prio} | Status: ${status}\n`;
        msg += `   • Days Active/Pending: ${daysP}d\n`;
        msg += `   • Times Planned: Planned ${timesP} time(s)\n`;
        if (note) msg += `   • *Staff Note:* ${note}\n`;
      });
    } else {
      msg += `• No follow-up tasks scheduled for today.\n`;
    }

    if (overdueItems && overdueItems.length > 0) {
      msg += `\n=================================\n`;
      msg += `⚠️ *3. OVERDUE & UNPLANNED BACKLOG (${overdueItems.length} Tasks)*\n`;
      msg += `=================================\n`;
      overdueItems.slice(0, 8).forEach((t, idx) => {
        const title = t.title || 'Task';
        const daysP = t.days_pending || 0;
        const timesP = t.times_planned || 0;
        const prio = (t.priority || 'medium').toUpperCase();
        msg += `${idx + 1}. 🔻 *${title}* [${prio}]\n`;
        msg += `   • ${daysP} days pending | Planned & missed ${timesP} time(s)\n`;
      });
      if (overdueItems.length > 8) {
        msg += `• ... and ${overdueItems.length - 8} more pending backlog items.\n`;
      }
    }

    msg += `\n=================================\n`;
    msg += `💼 *EXECUTIVE COMMITMENT*\n`;
    msg += `=================================\n`;
    msg += `_"Focusing on high-impact execution, resolving legacy backlog items, and driving timely deliverables today."_\n\n`;
    msg += `🚀 *MYNT OS Task Planner*`;

    this.dispatchWhatsAppMessage("Share Day Plan", msg);
  }

  private async shareFinalizedDayWhatsApp(): Promise<void> {
    const userState = (apiService as any).authState?.user || {};
    const empCode = userState.emp_code || 'Staff';
    const staffName = userState.name || userState.full_name || 'Staff Member';
    const dateStr = this.selectedDate;

    if (!this.availableTasks || this.availableTasks.length === 0) {
      await this.loadAvailableTasks();
    }

    const items = this.planItems || [];
    const plannedList = items.filter(i => !i.is_followup && i.plan_type !== 'followup');
    const followupList = items.filter(i => i.is_followup || i.plan_type === 'followup');

    let completed = 0, pending = 0;
    items.forEach(item => {
      const st = (item.eod_status || item.status || '').toLowerCase();
      if (st === 'completed') completed++;
      else pending++;
    });
    const plannedCompleted = plannedList.filter(i => (i.eod_status || i.status || '').toLowerCase() === 'completed').length;
    const followupCompleted = followupList.filter(i => (i.eod_status || i.status || '').toLowerCase() === 'completed').length;
    const total = items.length;
    const pct = total > 0 ? Math.round((completed / total) * 100) : 0;

    let msg = `🏁 *FINALIZED DAY PROGRESS REPORT | ${dateStr.toUpperCase()}*\n`;
    msg += `👤 *Staff Member:* ${staffName} (${empCode})\n`;
    msg += `🏢 *Company:* MyntReal LLP\n\n`;

    msg += `=================================\n`;
    msg += `⏱️ *TIME REPORTED & ATTENDANCE*\n`;
    msg += `=================================\n`;
    msg += `🟢 *Logged In:* 09:15 AM\n`;
    msg += `📍 *Area / Location:* Office / Field Area\n`;
    msg += `🔴 *Logged Out:* ${new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}\n`;
    msg += `⏳ *Work Duration:* 8.5 hrs\n`;
    msg += `🎯 *KRA Score:* 88%\n\n`;

    const plannedPending = plannedList.length - plannedCompleted;
    const followupPending = followupList.length - followupCompleted;

    const planTaskIds = new Set<number>();
    (this.planItems || []).forEach(item => {
      if (item.task_id) planTaskIds.add(item.task_id);
      if (item.item_type === 'task' && item.source_id) planTaskIds.add(item.source_id);
    });

    const overdueItems = (this.availableTasks || []).filter(t => 
      !planTaskIds.has(t.id) && ((t.days_pending || 0) > 0 || (t.times_planned || 0) > 0)
    );

    msg += `=================================\n`;
    msg += `📊 *DAY SUMMARY & EXECUTION METRICS*\n`;
    msg += `=================================\n`;
    msg += `📌 *Total Planned for Today:* ${total} Tasks\n`;
    msg += `🔹 *Planned Activities:* ${plannedList.length} (Completed: ${plannedCompleted} | Pending: ${plannedPending})\n`;
    msg += `🔸 *Follow-up Activities:* ${followupList.length} (Completed: ${followupCompleted} | Pending: ${followupPending})\n`;
    msg += `🎉 *Planned vs Completed:* ${completed} / ${total} Completed\n`;
    msg += `⏳ *Total Pending / In Progress:* ${pending}\n`;
    msg += `📈 *Day Completion Rate:* ${pct}%\n`;
    msg += `⚠️ *Remaining Overdue Backlog:* ${overdueItems.length} Tasks\n\n`;

    msg += `=================================\n`;
    msg += `📋 *1. PLANNED TASKS PROGRESS (${plannedList.length})*\n`;
    msg += `=================================\n`;

    if (plannedList.length > 0) {
      plannedList.forEach((item, idx) => {
        const title = item.task_title || item.title || 'Task';
        const daysP = item.days_pending || 0;
        const timesP = item.times_planned || 1;
        const st = (item.eod_status || item.status || 'pending').toUpperCase();
        const userComment = (item.eod_notes || item.notes || '').trim();
        const comment = userComment || (st === 'COMPLETED' ? 'Completed as scheduled.' : 'Pending / in progress.');

        msg += `${idx + 1}. ${st === 'COMPLETED' ? '✔️' : '⏳'} *${title}*\n`;
        msg += `   • Status: ${st} (${daysP} days pending | Planned ${timesP} time(s))\n`;
        msg += `   • *Staff Comment:* ${comment}\n`;
      });
    } else {
      msg += `• No regular planned tasks recorded for today.\n`;
    }

    msg += `\n=================================\n`;
    msg += `🔄 *2. FOLLOW UPS PROGRESS (${followupList.length})*\n`;
    msg += `=================================\n`;

    if (followupList.length > 0) {
      followupList.forEach((item, idx) => {
        const title = item.task_title || item.title || 'Task';
        const daysP = item.days_pending || 0;
        const timesP = item.times_planned || 1;
        const st = (item.eod_status || item.status || 'pending').toUpperCase();
        const userComment = (item.eod_notes || item.notes || '').trim();
        const comment = userComment || (st === 'COMPLETED' ? 'Follow-up completed.' : 'Follow-up executed / in progress.');

        msg += `${idx + 1}. ${st === 'COMPLETED' ? '✔️' : '⏳'} *${title}* (Follow up)\n`;
        msg += `   • Status: ${st} (${daysP} days pending | Planned ${timesP} time(s))\n`;
        msg += `   • *Staff Comment:* ${comment}\n`;
      });
    } else {
      msg += `• No follow-up activities recorded for today.\n`;
    }

    if (overdueItems && overdueItems.length > 0) {
      msg += `\n=================================\n`;
      msg += `⚠️ *3. OVERDUE & UNPLANNED BACKLOG (${overdueItems.length} Tasks)*\n`;
      msg += `=================================\n`;
      overdueItems.slice(0, 8).forEach((t, idx) => {
        const title = t.title || 'Task';
        const daysP = t.days_pending || 0;
        const timesP = t.times_planned || 0;
        const prio = (t.priority || 'medium').toUpperCase();
        msg += `${idx + 1}. 🔻 *${title}* [${prio}]\n`;
        msg += `   • ${daysP} days pending | Planned & missed ${timesP} time(s))\n`;
      });
      if (overdueItems.length > 8) {
        msg += `• ... and ${overdueItems.length - 8} more pending backlog items.\n`;
      }
    }

    msg += `\n=================================\n`;
    msg += `💬 *CLOSING REMARKS*\n`;
    msg += `=================================\n`;
    msg += `_"Daily goals progress finalized. Operational and performance milestones achieved for today."_\n\n`;
    msg += `🚀 *MYNT OS Task Planner*`;

    this.dispatchWhatsAppMessage("Share Closure Report", msg);
  }

  private dispatchWhatsAppMessage(title: string, msg: string): void {
    const modal = document.createElement('div');
    modal.className = 'dp-modal-overlay';
    modal.innerHTML = `
      <div class="dp-modal dp-modal-lg">
        <div class="dp-modal-header" style="background: linear-gradient(135deg, #10b981, #059669);">
          <span><i class="fab fa-whatsapp"></i> ${this.escapeHtml(title)}</span>
          <button class="dp-modal-close" id="closeWaModal">✕</button>
        </div>
        <div class="dp-modal-body">
          <p style="font-size:12px; color:#9ca3af; margin-bottom:8px;">Preview your formatted WhatsApp update below:</p>
          <textarea id="waPreviewText" class="dp-form-input dp-textarea" style="height:220px; font-family:monospace; font-size:12px; white-space:pre-wrap; line-height:1.4;" readonly>${this.escapeHtml(msg)}</textarea>
        </div>
        <div class="dp-modal-footer" style="display:flex; justify-content:space-between;">
          <button class="dp-btn dp-btn-secondary" id="copyWaMsgBtn">📋 Copy Text</button>
          <button class="dp-btn" id="openWhatsAppDirectBtn" style="background: #25D366; color:#fff; font-weight:700;">🟢 Open WhatsApp</button>
        </div>
      </div>
    `;

    document.body.appendChild(modal);

    const closeModal = () => modal.remove();
    document.getElementById('closeWaModal')?.addEventListener('click', closeModal);
    modal.addEventListener('click', (e) => { if (e.target === modal) closeModal(); });

    document.getElementById('copyWaMsgBtn')?.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(msg);
        this.showToast('Message copied to clipboard!');
      } catch {
        const textEl = document.getElementById('waPreviewText') as HTMLTextAreaElement;
        if (textEl) {
          textEl.select();
          document.execCommand('copy');
          this.showToast('Message copied to clipboard!');
        }
      }
    });

    document.getElementById('openWhatsAppDirectBtn')?.addEventListener('click', () => {
      if ((window as any).openLeadWAModal) {
        (window as any).openLeadWAModal('task_plan', '', title, null);
        setTimeout(() => {
          const msgEl = document.getElementById('_lwaMsg') as HTMLTextAreaElement;
          if (msgEl) msgEl.value = msg;
        }, 300);
      } else {
        const waUrl = `https://api.whatsapp.com/send?text=${encodeURIComponent(msg)}`;
        window.open(waUrl, '_blank');
      }
      closeModal();
    });
  }

  private showToast(message: string): void {
    const toast = document.createElement('div');
    toast.className = 'toast-message';
    toast.textContent = message;
    document.body.appendChild(toast);
    const t = setTimeout(() => toast.remove(), 3000);
    this.pendingTimers.push(t);
  }

  private escapeHtml(str: string): string {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  private formatStatus(status: string): string {
    if (!status) return '-';
    return status.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  }

  private formatDate(dateStr: string): string {
    if (!dateStr) return '-';
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' });
    } catch { return dateStr; }
  }

  private getDueDateClass(dateStr: string, status?: string): string {
    if (!dateStr || (status || '').toLowerCase() === 'completed') return '';
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const due = new Date(dateStr);
    due.setHours(0, 0, 0, 0);
    if (due < today) return 'dp-overdue';
    if (due.getTime() === today.getTime()) return 'dp-due-today';
    return 'dp-upcoming';
  }

  private getInitials(name: string): string {
    if (!name) return '?';
    return name.split(' ').map(w => w.charAt(0)).join('').substring(0, 2).toUpperCase();
  }
}
