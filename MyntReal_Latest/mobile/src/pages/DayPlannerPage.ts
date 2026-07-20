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
  eod_status?: string;
  eod_progress?: number;
  eod_notes?: string;
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
  private pendingTimers: ReturnType<typeof setTimeout>[] = [];

  constructor(container: HTMLElement) {
    this.container = container;
    this.selectedDate = this.getISTToday();
  }

  async init(): Promise<void> {
    this.render();
    await this.loadPlan();
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
    });

    document.getElementById('dpTodayBtn')?.addEventListener('click', () => {
      this.selectedDate = this.getISTToday();
      const input = document.getElementById('dpDateInput') as HTMLInputElement;
      if (input) input.value = this.selectedDate;
      this.loadPlan();
    });
  }

  private async loadPlan(): Promise<void> {
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
        const resp = response.data;
        if (resp.plan) {
          this.currentPlan = resp.plan;
          this.planItems = resp.plan.items || resp.items || [];
        } else if (resp.items) {
          this.currentPlan = resp;
          this.planItems = resp.items || [];
        } else if (Array.isArray(resp)) {
          this.currentPlan = null;
          this.planItems = resp;
        } else {
          this.currentPlan = resp || null;
          this.planItems = resp.items || [];
        }
      } else {
        this.currentPlan = null;
        this.planItems = [];
      }

      const membersResp = await apiService.get<any>(API_ENDPOINTS.DAY_PLANNER.TEAM_MEMBERS);
      if (membersResp.success && membersResp.data) {
        const members = Array.isArray(membersResp.data) ? membersResp.data : (membersResp.data.members || []);
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
    if (teamTab) teamTab.style.display = this.hasTeam ? '' : 'none';
    this.updateContent();
  }

  private async loadAvailableTasks(): Promise<void> {
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

    return `
      <div class="dp-stats-row">
        <div class="dp-stat"><span class="dp-stat-value">${stats.total}</span><span class="dp-stat-label">Total</span></div>
        <div class="dp-stat completed"><span class="dp-stat-value">${stats.completed}</span><span class="dp-stat-label">Done</span></div>
        <div class="dp-stat in-progress"><span class="dp-stat-value">${stats.inProgress}</span><span class="dp-stat-label">Active</span></div>
        <div class="dp-stat pending"><span class="dp-stat-value">${stats.pending}</span><span class="dp-stat-label">Pending</span></div>
        <div class="dp-stat carried"><span class="dp-stat-value">${stats.carried}</span><span class="dp-stat-label">Carried</span></div>
      </div>

      <div class="dp-section">
        <div class="dp-section-header" id="toggleAvailableBtn">
          <span>📋 Available Tasks</span>
          <span class="dp-toggle-icon">${this.showAvailable ? '▲' : '▼'}</span>
        </div>
        ${this.showAvailable ? this.renderAvailableTasks() : ''}
      </div>

      <div class="dp-section">
        <div class="dp-section-header-static">
          <span>📌 Today's Plan (${this.planItems.length} items)</span>
        </div>
        ${this.renderPlanItems(isFinalized)}
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

  private renderPlanItems(isFinalized: boolean): string {
    if (!this.planItems.length) {
      return '<div class="dp-empty">No items in today\'s plan. Add tasks from Available Tasks above.</div>';
    }

    const sorted = [...this.planItems].sort((a, b) => (a.priority_order || 999) - (b.priority_order || 999));
    return `<div class="dp-plan-list">
      ${sorted.map((item, idx) => {
        const title = item.task_title || item.title || '';
        const isPhase = item.item_type === 'phase';
        const priority = item.task_priority || item.priority || '';
        const status = item.eod_status || item.task_status || item.status || 'pending';
        const progress = item.eod_progress || item.progress || 0;
        const dueDate = item.task_due_date || item.due_date || '';
        const daysPending = item.days_pending || 0;
        const timesPlanned = item.times_planned || 0;
        const isCarried = item.carried_forward;

        return `
          <div class="dp-plan-card ${isCarried ? 'carried-forward' : ''}">
            <div class="dp-plan-header">
              <span class="dp-priority-num">${item.priority_order || (idx + 1)}</span>
              <span class="dp-plan-title">${this.escapeHtml(title)}</span>
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
            ${!isFinalized ? `
              <div class="dp-plan-actions">
                <button class="dp-action-btn dp-action-update" data-item-id="${item.id}">Update</button>
                <button class="dp-action-btn dp-action-remove" data-item-id="${item.id}">Remove</button>
              </div>
            ` : ''}
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
    let items: string[] = [];

    this.availableTasks.forEach(task => {
      const matchSearch = !sq || (task.title || '').toLowerCase().includes(sq);
      const matchStatus = sf === 'all' || (task.status || '').toLowerCase() === sf;
      const matchPriority = pf === 'all' || (task.priority || '').toLowerCase() === pf;
      const inPlan = planTaskIds.has(task.id);

      if (matchSearch && matchStatus && matchPriority) {
        items.push(`
          <div class="dp-avail-item ${inPlan ? 'in-plan' : ''}">
            <label class="dp-avail-check">
              <input type="checkbox" class="avail-checkbox" data-type="task" data-id="${task.id}" ${inPlan ? 'checked disabled' : ''}>
              <span class="dp-avail-title">${this.escapeHtml(task.title)}</span>
            </label>
            <div class="dp-avail-meta">
              <span class="dp-badge dp-badge-priority-${(task.priority || '').toLowerCase()}">${this.formatStatus(task.priority)}</span>
              <span class="dp-badge dp-badge-status-${(task.status || '').toLowerCase()}">${this.formatStatus(task.status)}</span>
              ${task.due_date ? `<span class="dp-due ${this.getDueDateClass(task.due_date, task.status)}">${this.formatDate(task.due_date)}</span>` : ''}
            </div>
          </div>
        `);
      }

      const phases = task.phases || task.sub_tasks || [];
      phases.forEach((phase, pIdx) => {
        const phaseMatchSearch = !sq || (phase.title || '').toLowerCase().includes(sq) || (task.title || '').toLowerCase().includes(sq);
        const phaseMatchStatus = sf === 'all' || (phase.status || '').toLowerCase() === sf;
        const phaseInPlan = planPhaseIds.has(phase.id);

        if (phaseMatchSearch && phaseMatchStatus && (pf === 'all' || (task.priority || '').toLowerCase() === pf)) {
          items.push(`
            <div class="dp-avail-item dp-avail-phase ${phaseInPlan ? 'in-plan' : ''}">
              <label class="dp-avail-check">
                <input type="checkbox" class="avail-checkbox" data-type="phase" data-id="${phase.id}" data-task-id="${task.id}" ${phaseInPlan ? 'checked disabled' : ''}>
                <span class="dp-avail-title">↳ P${pIdx + 1}: ${this.escapeHtml(phase.title)}</span>
              </label>
              <div class="dp-avail-meta">
                <span class="dp-badge dp-badge-status-${(phase.status || '').toLowerCase()}">${this.formatStatus(phase.status)}</span>
              </div>
            </div>
          `);
        }
      });
    });

    return `
      <div class="dp-avail-panel">
        <div class="dp-avail-filters">
          <input type="text" class="dp-search-input" id="availSearch" placeholder="Search tasks..." value="${this.searchQuery}">
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
        <div class="dp-avail-list">
          ${items.length > 0 ? items.join('') : '<div class="dp-empty">No available tasks found</div>'}
        </div>
        ${items.length > 0 ? '<button class="dp-add-to-plan-btn" id="addToPlanBtn">➕ Add Selected to Plan</button>' : ''}
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

    document.getElementById('finalizeBtn')?.addEventListener('click', () => {
      this.showFinalizeModal();
    });
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
    const checkboxes = document.querySelectorAll('.avail-checkbox:checked:not(:disabled)');
    if (checkboxes.length === 0) {
      this.showToast('Please select at least one task or phase');
      return;
    }

    const items: any[] = [];
    let order = this.planItems.length + 1;
    checkboxes.forEach(cb => {
      const el = cb as HTMLInputElement;
      const type = el.dataset.type;
      const id = parseInt(el.dataset.id || '0');
      const entry: any = { item_type: type, priority_order: order++ };
      if (type === 'task') {
        entry.task_id = id;
      } else {
        entry.phase_id = id;
        entry.task_id = parseInt(el.dataset.taskId || '0') || null;
      }
      items.push(entry);
    });

    try {
      const response = await apiService.post<any>(API_ENDPOINTS.DAY_PLANNER.CREATE_OR_UPDATE, {
        plan_date: this.selectedDate,
        items
      });
      if (response.success) {
        this.showToast('Items added to plan');
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
        this.showToast('Failed to remove item');
      }
    } catch (error) {
      this.showToast('Failed to remove item');
    }
  }

  private showUpdateModal(itemId: number): void {
    const item = this.planItems.find(i => i.id === itemId);
    if (!item) return;

    const status = item.eod_status || item.status || 'pending';
    const progress = item.eod_progress || item.progress || 0;
    const notes = item.eod_notes || '';

    const modal = document.createElement('div');
    modal.className = 'dp-modal-overlay';
    modal.innerHTML = `
      <div class="dp-modal">
        <div class="dp-modal-header">
          <span>Update Status</span>
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
            <label>Notes</label>
            <textarea id="eodNotesInput" class="dp-form-input dp-textarea" rows="3" placeholder="Add notes...">${notes}</textarea>
          </div>
        </div>
        <div class="dp-modal-footer">
          <button class="dp-btn dp-btn-secondary" id="cancelUpdateBtn">Cancel</button>
          <button class="dp-btn dp-btn-primary" id="saveUpdateBtn">Save</button>
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
          this.showToast('Status updated');
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

    const modal = document.createElement('div');
    modal.className = 'dp-modal-overlay';
    modal.innerHTML = `
      <div class="dp-modal">
        <div class="dp-modal-header">
          <span>Finalize Day Plan</span>
          <button class="dp-modal-close" id="closeFinalizeModal">✕</button>
        </div>
        <div class="dp-modal-body">
          <p>This will lock today's plan and apply all status updates to the original tasks.</p>
          <div class="dp-finalize-summary">
            <div class="dp-summary-row"><span>Total Items</span><strong>${stats.total}</strong></div>
            <div class="dp-summary-row"><span>Completed</span><strong class="done">${stats.completed}</strong></div>
            <div class="dp-summary-row"><span>In Progress</span><strong class="active">${stats.inProgress}</strong></div>
            <div class="dp-summary-row"><span>Pending</span><strong class="pend">${stats.pending}</strong></div>
          </div>
        </div>
        <div class="dp-modal-footer">
          <button class="dp-btn dp-btn-secondary" id="cancelFinalizeBtn">Cancel</button>
          <button class="dp-btn dp-btn-primary" id="confirmFinalizeBtn">Finalize</button>
        </div>
      </div>
    `;

    document.body.appendChild(modal);

    const closeModal = () => modal.remove();
    document.getElementById('closeFinalizeModal')?.addEventListener('click', closeModal);
    document.getElementById('cancelFinalizeBtn')?.addEventListener('click', closeModal);
    modal.addEventListener('click', (e) => { if (e.target === modal) closeModal(); });

    document.getElementById('confirmFinalizeBtn')?.addEventListener('click', async () => {
      const itemUpdates = (this.planItems || []).map(item => ({
        id: item.id,
        eod_status: item.eod_status || item.status || 'pending',
        eod_progress: item.eod_progress || item.progress || 0,
        eod_notes: item.eod_notes || ''
      }));

      try {
        const response = await apiService.post<any>(API_ENDPOINTS.DAY_PLANNER.FINALIZE, { items: itemUpdates });
        if (response.success) {
          this.showToast('Day plan finalized!');
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
