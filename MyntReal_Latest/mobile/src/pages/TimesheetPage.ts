import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';
import { API_ENDPOINTS } from '../constants/api-endpoints';

interface TimesheetEntry {
  id: number;
  date: string;
  start_time: string | null;
  end_time: string | null;
  hours: number;
  duration_minutes?: number;
  work_description: string;
  comments?: string;
  project_name?: string;
  task_id?: number;
  task_name?: string;
  kra_id?: number;
  kra_name?: string;
  lead_id?: number;
  lead_name?: string;
  lead_ids?: number[];
  journey_id?: number;
  entry_type?: string;
  auto_source?: string;
  status: string;
  approval_status?: string;
  employee_name?: string;
  employee_code?: string;
  employee_id?: number;
  clock_in?: string;
  clock_out?: string;
  worked_minutes?: number;
  attendance_status?: string;
}

interface TagOption {
  id: number;
  name: string;
}

interface HistoryEntry {
  date: string;
  total_hours: number;
  entries_count: number;
  status: string;
}

interface TeamManager {
  id: number;
  name: string;
  code: string;
}

export class TimesheetPage {
  private container: HTMLElement;
  private entries: TimesheetEntry[] = [];
  private historyEntries: HistoryEntry[] = [];
  private teamEntries: TimesheetEntry[] = [];
  private teamManagers: TeamManager[] = [];
  private loading = true;
  private loadingRecords = false;
  private loadingTeam = false;
  private activeTab: 'today' | 'records' | 'team' = 'today';
  private selectedDate: Date = new Date();
  private tasks: TagOption[] = [];
  private kras: TagOption[] = [];
  private leads: TagOption[] = [];
  private selectedEntry: TimesheetEntry | null = null;
  private hasTeam = false;
  private recordsFrom = '';
  private recordsTo = '';
  private recordsStatus = '';
  private recordsType = '';
  private teamFrom = '';
  private teamTo = '';
  private teamStatus = '';
  private teamManagerId = '';
  private pendingTimers: ReturnType<typeof setTimeout>[] = [];
  private activitySummary: any = null;
  private activityDeptType: string = 'other';
  private activityDetailOpen: Record<string, boolean> = {};
  private activityCardCollapsed: boolean = false;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await Promise.all([
      this.loadEntries(),
      this.loadTagOptions(),
      this.checkTeamAccess(),
      this.loadActivitySummaryData()
    ]);
  }

  destroy(): void {
    this.pendingTimers.forEach(t => clearTimeout(t));
    this.pendingTimers = [];
  }

  private async checkTeamAccess(): Promise<void> {
    try {
      const resp = await apiService.get<any>(`${API_ENDPOINTS.TIMESHEET.TEAM_ENTRIES}?limit=1`);
      if (resp.success) {
        this.hasTeam = true;
        const teamTab = document.getElementById('tsTeamTab');
        if (teamTab) teamTab.style.display = '';
      }
    } catch { }
    try {
      const resp = await apiService.get<any>(API_ENDPOINTS.TIMESHEET.REPORTING_MANAGERS);
      if (resp.success && resp.data) {
        this.teamManagers = resp.data.managers || resp.data || [];
      }
    } catch { }
  }

  private async loadEntries(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      const dateStr = this.fmtDate(this.selectedDate);
      const response = await apiService.get<any>(API_ENDPOINTS.TIMESHEET.MY_ENTRIES(dateStr));
      if (response.success && response.data) {
        this.entries = response.data.entries || response.data || [];
      }
    } catch (error) {
      console.error('[TimesheetPage] Failed to load entries:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private async loadRecords(): Promise<void> {
    if (!this.recordsFrom || !this.recordsTo) return;
    this.loadingRecords = true;
    this.updateContent();

    try {
      const params = new URLSearchParams();
      params.append('start_date', this.recordsFrom);
      params.append('end_date', this.recordsTo);
      if (this.recordsStatus) params.append('status', this.recordsStatus);
      if (this.recordsType) params.append('entry_type', this.recordsType);

      const response = await apiService.get<any>(`${API_ENDPOINTS.TIMESHEET.MY_HISTORY}?${params}`);
      if (response.success && response.data) {
        this.historyEntries = response.data.entries || response.data || [];
      }
    } catch (error) {
      console.error('[TimesheetPage] Failed to load records:', error);
    }

    this.loadingRecords = false;
    this.updateContent();
  }

  private async loadTeamEntries(): Promise<void> {
    this.loadingTeam = true;
    this.updateContent();

    try {
      const params = new URLSearchParams();
      if (this.teamFrom) params.append('from_date', this.teamFrom);
      if (this.teamTo) params.append('to_date', this.teamTo);
      if (this.teamStatus) params.append('status', this.teamStatus);
      if (this.teamManagerId) params.append('reporting_manager_id', this.teamManagerId);
      params.append('limit', '100');

      const response = await apiService.get<any>(`${API_ENDPOINTS.TIMESHEET.TEAM_ENTRIES}?${params}`);
      if (response.success && response.data) {
        this.teamEntries = response.data.entries || response.data || [];
      }
    } catch (error) {
      console.error('[TimesheetPage] Failed to load team entries:', error);
    }

    this.loadingTeam = false;
    this.updateContent();
  }

  private async loadTagOptions(): Promise<void> {
    try {
      const [tasksRes, krasRes, leadsRes] = await Promise.all([
        apiService.get<any>(API_ENDPOINTS.TIMESHEET.MY_TASKS),
        apiService.get<any>(API_ENDPOINTS.TIMESHEET.MY_KRAS),
        apiService.get<any>(API_ENDPOINTS.TIMESHEET.MY_LEADS)
      ]);

      if (tasksRes.success) {
        const raw = tasksRes.data?.tasks || tasksRes.data || [];
        this.tasks = raw.map((t: any) => ({ id: t.id, name: t.title || t.task_code || `Task #${t.id}` }));
      }
      if (krasRes.success) {
        const raw = krasRes.data?.kras || krasRes.data || [];
        this.kras = raw.map((k: any) => ({ id: k.id, name: k.title || k.kra_code || `KRA #${k.id}` }));
      }
      if (leadsRes.success) {
        const raw = leadsRes.data?.leads || leadsRes.data || [];
        this.leads = raw.map((l: any) => ({ id: l.id, name: l.name || `Lead #${l.id}` }));
      }
    } catch (error) {
      console.error('[TimesheetPage] Failed to load tag options:', error);
    }
  }

  private fmtDate(d: Date): string {
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  }

  private fmtDateDisplay(d: Date): string {
    return d.toLocaleDateString('en-US', { weekday: 'short', day: 'numeric', month: 'short' });
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container ts-page">
        ${PageHeader.render({ title: 'My Timesheet', showBack: true })}

        <div class="ts-tabs">
          <button class="ts-tab ${this.activeTab === 'today' ? 'active' : ''}" data-tab="today">Today's Entries</button>
          <button class="ts-tab ${this.activeTab === 'records' ? 'active' : ''}" data-tab="records">Records</button>
          <button class="ts-tab ${this.activeTab === 'team' ? 'active' : ''}" data-tab="team" id="tsTeamTab" style="display:none;">Team</button>
        </div>

        <div id="tsContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>

      <div class="dp-modal-overlay" id="tsEntryModal" style="display:none;">
        <div class="dp-modal">
          <div class="dp-modal-header">
            <span id="tsModalTitle">Add Entry</span>
            <button class="dp-modal-close" id="tsCloseModal">✕</button>
          </div>
          <div class="dp-modal-body">
            <div class="ts-form-row">
              <div class="ts-form-group">
                <label>Start Time *</label>
                <input type="time" id="tsStartTime" class="dp-form-input">
              </div>
              <div class="ts-form-group">
                <label>End Time *</label>
                <input type="time" id="tsEndTime" class="dp-form-input">
              </div>
            </div>
            <div class="ts-form-group">
              <label>Hours <small>(auto-calculated)</small></label>
              <input type="number" id="tsHours" class="dp-form-input" step="0.5" min="0.5" max="24" readonly>
            </div>
            <div class="ts-form-group">
              <label>Quick Activity <small style="color:#9ca3af;">(tap to fill)</small></label>
              <div class="ts-quick-chips" id="tsQuickChips">
                <span class="ts-chip" data-label="Team Meeting">👥 Team Meeting</span>
                <span class="ts-chip" data-label="Feedback Meeting">💬 Feedback Meeting</span>
                <span class="ts-chip" data-label="Training / Learning">🎓 Training</span>
                <span class="ts-chip" data-label="Client Call">📞 Client Call</span>
                <span class="ts-chip" data-label="Report Preparation">📄 Report Prep</span>
                <span class="ts-chip" data-label="Travel / Field Visit">🚗 Travel / Field</span>
                <span class="ts-chip" data-label="Internal Review">🔍 Internal Review</span>
                <span class="ts-chip" data-label="Admin / Documentation">📁 Admin / Docs</span>
              </div>
            </div>
            <div class="ts-form-group">
              <label>Description *</label>
              <textarea id="tsDescription" class="dp-form-input dp-textarea" rows="3" placeholder="Describe your work..."></textarea>
            </div>
            <div class="ts-form-group">
              <label>Tag Type</label>
              <select id="tsTagType" class="dp-form-input">
                <option value="">No Tag</option>
                <option value="task">Task</option>
                <option value="kra">KRA</option>
                <option value="lead">Lead</option>
              </select>
            </div>
            <div class="ts-form-group" id="tsTagSelectGroup" style="display:none;">
              <label id="tsTagLabel">Select</label>
              <select id="tsTagSelect" class="dp-form-input"><option value="">Select...</option></select>
            </div>
            <div class="ts-form-group" id="tsLeadMultiGroup" style="display:none;">
              <label>Select Leads</label>
              <div id="tsLeadCheckboxes" class="ts-checkbox-list"></div>
            </div>
          </div>
          <div class="dp-modal-footer">
            <button class="dp-btn dp-btn-secondary" id="tsCancelEntry">Cancel</button>
            <button class="dp-btn dp-btn-primary" id="tsSaveEntry">Save</button>
          </div>
        </div>
      </div>
    `;

    PageHeader.attachListeners({ title: 'My Timesheet', showBack: true });
    this.attachListeners();
  }

  private attachListeners(): void {
    document.querySelectorAll('.ts-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        const tabId = (tab as HTMLElement).dataset.tab as 'today' | 'records' | 'team';
        this.activeTab = tabId;
        document.querySelectorAll('.ts-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        if (tabId === 'team' && this.teamEntries.length === 0) {
          this.loadTeamEntries();
        } else {
          this.updateContent();
        }
      });
    });

    document.getElementById('tsCloseModal')?.addEventListener('click', () => this.hideModal());
    document.getElementById('tsCancelEntry')?.addEventListener('click', () => this.hideModal());
    document.getElementById('tsSaveEntry')?.addEventListener('click', () => this.saveEntry());

    // Quick activity chips
    document.querySelectorAll('#tsQuickChips .ts-chip').forEach(chip => {
      chip.addEventListener('click', () => {
        const label = (chip as HTMLElement).dataset.label || '';
        const isActive = chip.classList.contains('active');
        document.querySelectorAll('#tsQuickChips .ts-chip').forEach(c => c.classList.remove('active'));
        const desc = document.getElementById('tsDescription') as HTMLTextAreaElement;
        if (isActive) {
          if (desc && desc.value === label) desc.value = '';
        } else {
          chip.classList.add('active');
          if (desc) desc.value = label;
          const tagType = document.getElementById('tsTagType') as HTMLSelectElement;
          if (tagType && !tagType.value) { tagType.value = ''; }
        }
      });
    });

    document.getElementById('tsStartTime')?.addEventListener('change', () => this.calcHours());
    document.getElementById('tsEndTime')?.addEventListener('change', () => this.calcHours());

    document.getElementById('tsTagType')?.addEventListener('change', (e) => {
      this.updateTagOptions((e.target as HTMLSelectElement).value);
    });
  }

  private updateContent(): void {
    const content = document.getElementById('tsContent');
    if (!content) return;

    switch (this.activeTab) {
      case 'today':
        this.renderTodayTab(content);
        break;
      case 'records':
        this.renderRecordsTab(content);
        break;
      case 'team':
        this.renderTeamTab(content);
        break;
    }
  }

  private renderTodayTab(content: HTMLElement): void {
    if (this.loading) {
      content.innerHTML = '<div class="loading-state">Loading entries...</div>';
      return;
    }

    const totalHours = this.entries.reduce((s, e) => s + (e.hours || (e.duration_minutes || 0) / 60 || 0), 0);

    content.innerHTML = `
      <div class="ts-date-bar">
        <button class="ts-date-nav" id="tsPrevDay">◀</button>
        <div class="ts-date-display">
          <span class="ts-date-label" id="tsDateLabel">${this.fmtDateDisplay(this.selectedDate)}</span>
          <input type="date" id="tsDatePicker" class="ts-date-input" value="${this.fmtDate(this.selectedDate)}">
        </div>
        <button class="ts-date-nav" id="tsNextDay">▶</button>
      </div>

      <div class="ts-summary-row">
        <div class="ts-summary-card">
          <span class="ts-sv">${this.entries.length}</span>
          <span class="ts-sl">Entries</span>
        </div>
        <div class="ts-summary-card">
          <span class="ts-sv ts-sv-hours">${totalHours.toFixed(1)}h</span>
          <span class="ts-sl">Logged</span>
        </div>
      </div>

      ${this.renderActivitySummaryHtml()}

      ${this.entries.length === 0 ? `
        <div class="ts-empty">
          <span class="ts-empty-icon">📋</span>
          <p>No entries for this day</p>
          <button class="dp-btn dp-btn-primary" id="tsAddFirst">+ Add Entry</button>
        </div>
      ` : `
        <div class="ts-entries-list">
          ${this.entries.map(e => this.renderEntryCard(e)).join('')}
        </div>
      `}

      <button class="ts-fab" id="tsAddFab">+</button>
    `;

    this.attachTodayListeners();
    this.attachActivityListeners();
  }

  private renderEntryCard(entry: TimesheetEntry): string {
    const status = (entry.status || entry.approval_status || 'pending').toLowerCase();
    let tagHtml = '';
    if (entry.task_name) tagHtml = `<span class="ts-tag ts-tag-task">📋 ${this.esc(entry.task_name)}</span>`;
    else if (entry.kra_name) tagHtml = `<span class="ts-tag ts-tag-kra">🎯 ${this.esc(entry.kra_name)}</span>`;
    else if (entry.lead_name) tagHtml = `<span class="ts-tag ts-tag-lead">👤 ${this.esc(entry.lead_name)}</span>`;

    const hours = entry.hours || (entry.duration_minutes ? entry.duration_minutes / 60 : 0);
    const desc = entry.work_description || entry.comments || '';

    const isAuto = !!entry.auto_source;
    const autoLabel = entry.auto_source === 'kra' ? 'KRA' : entry.auto_source === 'day_plan' ? 'Day Plan' : entry.auto_source === 'journey' ? 'Journey' : entry.auto_source || '';
    const autoBadge = isAuto ? `<span class="ts-auto-badge">🤖 ${autoLabel}</span>` : '';

    return `
      <div class="ts-entry-card${isAuto ? ' ts-entry-auto' : ''}" data-id="${entry.id}">
        <div class="ts-entry-header">
          <span class="ts-entry-time">${entry.start_time ? entry.start_time.substring(0, 5) : '--:--'} – ${entry.end_time ? entry.end_time.substring(0, 5) : '--:--'}</span>
          <span class="ts-entry-hours">${hours.toFixed(1)}h</span>
          <span class="ts-status-badge ts-status-${status}">${status}</span>
        </div>
        <p class="ts-entry-desc">${this.esc(desc)}</p>
        ${tagHtml}${autoBadge}
        <div class="ts-entry-actions">
          ${isAuto
            ? `<span class="ts-lock-badge" title="Auto-captured from ${autoLabel}. Edit in source.">🔒 Auto</span>`
            : `<button class="ts-action-btn ts-action-edit" data-id="${entry.id}">Edit</button>
               <button class="ts-action-btn ts-action-delete" data-id="${entry.id}">Delete</button>`
          }
        </div>
      </div>
    `;
  }

  private attachTodayListeners(): void {
    document.getElementById('tsPrevDay')?.addEventListener('click', () => {
      this.selectedDate.setDate(this.selectedDate.getDate() - 1);
      this.loadEntries();
    });
    document.getElementById('tsNextDay')?.addEventListener('click', () => {
      this.selectedDate.setDate(this.selectedDate.getDate() + 1);
      this.loadEntries();
    });
    document.getElementById('tsDatePicker')?.addEventListener('change', (e) => {
      const val = (e.target as HTMLInputElement).value;
      if (val) { this.selectedDate = new Date(val + 'T00:00:00'); this.loadEntries(); }
    });
    document.getElementById('tsAddFab')?.addEventListener('click', () => this.showAddModal());
    document.getElementById('tsAddFirst')?.addEventListener('click', () => this.showAddModal());

    document.querySelectorAll('.ts-action-edit').forEach(btn => {
      btn.addEventListener('click', (ev) => {
        ev.stopPropagation();
        const id = parseInt((btn as HTMLElement).dataset.id || '0');
        const entry = this.entries.find(e => e.id === id);
        if (entry) this.showEditModal(entry);
      });
    });
    document.querySelectorAll('.ts-action-delete').forEach(btn => {
      btn.addEventListener('click', (ev) => {
        ev.stopPropagation();
        const id = parseInt((btn as HTMLElement).dataset.id || '0');
        const entry = this.entries.find(e => e.id === id);
        if (entry) this.confirmDelete(entry);
      });
    });
  }

  private renderRecordsTab(content: HTMLElement): void {
    const today = this.fmtDate(new Date());
    const monthAgo = this.fmtDate(new Date(Date.now() - 30 * 86400000));

    content.innerHTML = `
      <div class="ts-filters">
        <div class="ts-filter-row">
          <div class="ts-filter-field">
            <label>From</label>
            <input type="date" id="tsRecFrom" class="dp-form-input" value="${this.recordsFrom || monthAgo}">
          </div>
          <div class="ts-filter-field">
            <label>To</label>
            <input type="date" id="tsRecTo" class="dp-form-input" value="${this.recordsTo || today}">
          </div>
        </div>
        <div class="ts-filter-row">
          <select id="tsRecStatus" class="dp-form-input">
            <option value="">All Status</option>
            <option value="submitted" ${this.recordsStatus === 'submitted' ? 'selected' : ''}>Submitted</option>
            <option value="approved" ${this.recordsStatus === 'approved' ? 'selected' : ''}>Approved</option>
            <option value="rejected" ${this.recordsStatus === 'rejected' ? 'selected' : ''}>Rejected</option>
            <option value="resubmitted" ${this.recordsStatus === 'resubmitted' ? 'selected' : ''}>Resubmitted</option>
          </select>
          <select id="tsRecType" class="dp-form-input">
            <option value="">All Types</option>
            <option value="task" ${this.recordsType === 'task' ? 'selected' : ''}>Task</option>
            <option value="kra" ${this.recordsType === 'kra' ? 'selected' : ''}>KRA</option>
            <option value="others" ${this.recordsType === 'others' ? 'selected' : ''}>Others</option>
          </select>
          <button class="dp-btn dp-btn-primary ts-search-btn" id="tsRecSearch">Search</button>
        </div>
      </div>

      <div id="tsRecordsContent">
        ${this.loadingRecords ? '<div class="loading-state">Loading records...</div>' :
          this.historyEntries.length > 0 ? this.renderHistoryList() :
          '<div class="ts-empty"><span class="ts-empty-icon">📅</span><p>Select a date range and search</p></div>'
        }
      </div>
    `;

    document.getElementById('tsRecSearch')?.addEventListener('click', () => {
      this.recordsFrom = (document.getElementById('tsRecFrom') as HTMLInputElement)?.value || '';
      this.recordsTo = (document.getElementById('tsRecTo') as HTMLInputElement)?.value || '';
      this.recordsStatus = (document.getElementById('tsRecStatus') as HTMLSelectElement)?.value || '';
      this.recordsType = (document.getElementById('tsRecType') as HTMLSelectElement)?.value || '';
      this.loadRecords();
    });

    document.querySelectorAll('.ts-history-entry').forEach(card => {
      card.addEventListener('click', () => {
        const dateStr = (card as HTMLElement).dataset.date;
        if (dateStr) {
          this.selectedDate = new Date(dateStr + 'T00:00:00');
          this.activeTab = 'today';
          document.querySelectorAll('.ts-tab').forEach(t => t.classList.remove('active'));
          document.querySelector('.ts-tab[data-tab="today"]')?.classList.add('active');
          this.loadEntries();
        }
      });
    });
  }

  private renderHistoryList(): string {
    const totalHours = this.historyEntries.reduce((s, e) => s + (e.total_hours || 0), 0);
    const totalDays = this.historyEntries.length;
    const avg = totalDays > 0 ? totalHours / totalDays : 0;

    return `
      <div class="ts-summary-row" style="margin-bottom:12px;">
        <div class="ts-summary-card"><span class="ts-sv">${totalDays}</span><span class="ts-sl">Days</span></div>
        <div class="ts-summary-card"><span class="ts-sv ts-sv-hours">${totalHours.toFixed(1)}h</span><span class="ts-sl">Total</span></div>
        <div class="ts-summary-card"><span class="ts-sv">${avg.toFixed(1)}h</span><span class="ts-sl">Avg/Day</span></div>
      </div>
      <div class="ts-history-list">
        ${this.historyEntries.map(e => {
          const d = new Date(e.date);
          const day = d.toLocaleDateString('en-US', { weekday: 'short' });
          const date = d.toLocaleDateString('en-US', { day: 'numeric', month: 'short' });
          const st = (e.status || 'pending').toLowerCase();
          return `
            <div class="ts-history-entry" data-date="${e.date}">
              <div class="ts-hist-date">
                <span class="ts-hist-day">${day}</span>
                <span class="ts-hist-datestr">${date}</span>
              </div>
              <div class="ts-hist-info">
                <span class="ts-hist-hours">${(e.total_hours || 0).toFixed(1)}h</span>
                <span class="ts-hist-count">${e.entries_count || 0} entries</span>
              </div>
              <span class="ts-status-badge ts-status-${st}">${st}</span>
            </div>
          `;
        }).join('')}
      </div>
    `;
  }

  private renderTeamTab(content: HTMLElement): void {
    const today = this.fmtDate(new Date());
    const weekAgo = this.fmtDate(new Date(Date.now() - 7 * 86400000));

    content.innerHTML = `
      <div class="ts-filters">
        <div class="ts-filter-row">
          ${this.teamManagers.length > 0 ? `
            <select id="tsTeamMgr" class="dp-form-input">
              <option value="">All Managers</option>
              ${this.teamManagers.map(m => `<option value="${m.id}" ${this.teamManagerId === String(m.id) ? 'selected' : ''}>${this.esc(m.name)} (${m.code})</option>`).join('')}
            </select>
          ` : ''}
        </div>
        <div class="ts-team-status-row">
          <button class="ts-team-filter-btn ${this.teamStatus === '' ? 'active' : ''}" data-status="">All</button>
          <button class="ts-team-filter-btn ${this.teamStatus === 'submitted' ? 'active' : ''}" data-status="submitted">Pending</button>
          <button class="ts-team-filter-btn ${this.teamStatus === 'resubmitted' ? 'active' : ''}" data-status="resubmitted">Resubmit</button>
          <button class="ts-team-filter-btn ${this.teamStatus === 'approved' ? 'active' : ''}" data-status="approved">Approved</button>
          <button class="ts-team-filter-btn ${this.teamStatus === 'rejected' ? 'active' : ''}" data-status="rejected">Rejected</button>
        </div>
        <div class="ts-filter-row">
          <div class="ts-filter-field">
            <label>From</label>
            <input type="date" id="tsTeamFrom" class="dp-form-input" value="${this.teamFrom || weekAgo}">
          </div>
          <div class="ts-filter-field">
            <label>To</label>
            <input type="date" id="tsTeamTo" class="dp-form-input" value="${this.teamTo || today}">
          </div>
          <button class="dp-btn dp-btn-primary ts-search-btn" id="tsTeamSearch">🔍</button>
        </div>
      </div>

      <div id="tsTeamContent">
        ${this.loadingTeam ? '<div class="loading-state">Loading team entries...</div>' :
          this.teamEntries.length > 0 ? this.renderTeamEntries() :
          '<div class="ts-empty"><span class="ts-empty-icon">👥</span><p>Select dates and search to view team entries</p></div>'
        }
      </div>
    `;

    this.attachTeamListeners();
  }

  private renderTeamEntries(): string {
    const grouped: Record<string, { name: string; code: string; empId: number; dates: Record<string, { entries: TimesheetEntry[]; totalMins: number; clockIn?: string; clockOut?: string; workedMins?: number; approvalStatus?: string }>; totalMins: number }> = {};

    this.teamEntries.forEach(entry => {
      const key = String(entry.employee_id || entry.employee_code || 'unknown').replace(/[^a-zA-Z0-9]/g, '_');
      const dateKey = (entry.date || '').split('T')[0];
      if (!grouped[key]) {
        grouped[key] = { name: entry.employee_name || 'Unknown', code: entry.employee_code || '', empId: entry.employee_id || 0, dates: {}, totalMins: 0 };
      }
      if (!grouped[key].dates[dateKey]) {
        grouped[key].dates[dateKey] = { entries: [], totalMins: 0, clockIn: entry.clock_in || undefined, clockOut: entry.clock_out || undefined, workedMins: entry.worked_minutes || 0, approvalStatus: entry.approval_status || undefined };
      }
      grouped[key].dates[dateKey].entries.push(entry);
      const mins = entry.duration_minutes || (entry.hours ? entry.hours * 60 : 0);
      grouped[key].dates[dateKey].totalMins += mins;
      grouped[key].totalMins += mins;
    });

    const empKeys = Object.keys(grouped);
    if (empKeys.length === 0) return '<div class="ts-empty"><p>No entries found</p></div>';

    return empKeys.map(key => {
      const emp = grouped[key];
      const dateKeys = Object.keys(emp.dates).sort().reverse();
      const totalH = (emp.totalMins / 60).toFixed(1);
      const initials = emp.name.split(' ').map(w => w[0]).join('').substring(0, 2).toUpperCase();

      return `
        <div class="ts-team-card">
          <div class="ts-team-header">
            <div class="ts-team-avatar">${initials}</div>
            <div class="ts-team-info">
              <span class="ts-team-name">${this.esc(emp.name)}</span>
              <span class="ts-team-code">${emp.code} · ${totalH}h total</span>
            </div>
          </div>
          <div class="ts-team-dates">
            ${dateKeys.map(dk => {
              const dd = emp.dates[dk];
              const d = new Date(dk);
              const dateLabel = d.toLocaleDateString('en-US', { weekday: 'short', day: 'numeric', month: 'short' });
              const loggedH = (dd.totalMins / 60).toFixed(1);
              const workedH = dd.workedMins ? (dd.workedMins / 60).toFixed(1) : null;
              const approval = dd.approvalStatus || dd.entries[0]?.approval_status || dd.entries[0]?.status || 'pending';
              const approvalLc = approval.toLowerCase();

              return `
                <div class="ts-team-date-row">
                  <span class="ts-team-date-label">${dateLabel}</span>
                  <span class="ts-team-date-hours">${loggedH}h logged${workedH ? ` / ${workedH}h worked` : ''}</span>
                  <span class="ts-status-badge ts-status-${approvalLc}">${approvalLc}</span>
                  <div class="ts-team-approve-btns">
                    ${approvalLc === 'submitted' || approvalLc === 'resubmitted' || approvalLc === 'pending' ? `
                      <button class="ts-approve-btn" data-action="approve" data-entries='${JSON.stringify(dd.entries.map(e => e.id))}'>✅</button>
                      <button class="ts-reject-btn" data-action="reject" data-entries='${JSON.stringify(dd.entries.map(e => e.id))}'>❌</button>
                    ` : ''}
                  </div>
                </div>
                <div class="ts-team-entries-list">
                  ${dd.entries.map(e => {
                    const hrs = e.hours || (e.duration_minutes ? e.duration_minutes / 60 : 0);
                    return `<div class="ts-team-entry-mini"><span>${e.start_time ? e.start_time.substring(0, 5) : '--:--'} – ${e.end_time ? e.end_time.substring(0, 5) : '--:--'}</span><span>${hrs.toFixed(1)}h</span><span class="ts-mini-desc">${this.esc((e.work_description || e.comments || '').substring(0, 50))}</span></div>`;
                  }).join('')}
                </div>
              `;
            }).join('')}
          </div>
        </div>
      `;
    }).join('');
  }

  private attachTeamListeners(): void {
    document.getElementById('tsTeamSearch')?.addEventListener('click', () => {
      this.teamFrom = (document.getElementById('tsTeamFrom') as HTMLInputElement)?.value || '';
      this.teamTo = (document.getElementById('tsTeamTo') as HTMLInputElement)?.value || '';
      this.teamManagerId = (document.getElementById('tsTeamMgr') as HTMLSelectElement)?.value || '';
      this.loadTeamEntries();
    });

    document.querySelectorAll('.ts-team-filter-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        this.teamStatus = (btn as HTMLElement).dataset.status || '';
        document.querySelectorAll('.ts-team-filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
      });
    });

    document.querySelectorAll('.ts-approve-btn, .ts-reject-btn').forEach(btn => {
      btn.addEventListener('click', async (ev) => {
        ev.stopPropagation();
        const action = (btn as HTMLElement).dataset.action;
        const entryIds: number[] = JSON.parse((btn as HTMLElement).dataset.entries || '[]');
        if (entryIds.length === 0) return;

        const confirmed = confirm(`${action === 'approve' ? 'Approve' : 'Reject'} ${entryIds.length} entries?`);
        if (!confirmed) return;

        try {
          for (const id of entryIds) {
            const url = action === 'approve' ? API_ENDPOINTS.TIMESHEET.APPROVE(id) : API_ENDPOINTS.TIMESHEET.REJECT(id);
            await apiService.post<any>(url, {});
          }
          this.showToast(`${entryIds.length} entries ${action}d`);
          this.loadTeamEntries();
        } catch (error) {
          this.showToast(`Failed to ${action} entries`);
        }
      });
    });
  }

  private showAddModal(): void {
    this.selectedEntry = null;
    const titleEl = document.getElementById('tsModalTitle');
    if (titleEl) titleEl.textContent = 'Add Entry';
    (document.getElementById('tsStartTime') as HTMLInputElement).value = '';
    (document.getElementById('tsEndTime') as HTMLInputElement).value = '';
    (document.getElementById('tsHours') as HTMLInputElement).value = '';
    (document.getElementById('tsDescription') as HTMLTextAreaElement).value = '';
    (document.getElementById('tsTagType') as HTMLSelectElement).value = '';
    this.updateTagOptions('');
    document.querySelectorAll('#tsQuickChips .ts-chip').forEach(c => c.classList.remove('active'));
    const modal = document.getElementById('tsEntryModal');
    if (modal) modal.style.display = 'flex';
  }

  private showEditModal(entry: TimesheetEntry): void {
    this.selectedEntry = entry;
    const titleEl = document.getElementById('tsModalTitle');
    if (titleEl) titleEl.textContent = 'Edit Entry';
    (document.getElementById('tsStartTime') as HTMLInputElement).value = entry.start_time?.substring(0, 5) || '';
    (document.getElementById('tsEndTime') as HTMLInputElement).value = entry.end_time?.substring(0, 5) || '';
    (document.getElementById('tsHours') as HTMLInputElement).value = (entry.hours || '').toString();
    (document.getElementById('tsDescription') as HTMLTextAreaElement).value = entry.work_description || entry.comments || '';

    let tagType = '';
    let tagId = '';
    if (entry.task_id) { tagType = 'task'; tagId = entry.task_id.toString(); }
    else if (entry.kra_id) { tagType = 'kra'; tagId = entry.kra_id.toString(); }
    else if (entry.lead_id) { tagType = 'lead'; tagId = entry.lead_id.toString(); }

    (document.getElementById('tsTagType') as HTMLSelectElement).value = tagType;
    this.updateTagOptions(tagType);
    const t = setTimeout(() => {
      const sel = document.getElementById('tsTagSelect') as HTMLSelectElement;
      if (sel) sel.value = tagId;
    }, 100);
    this.pendingTimers.push(t);

    const modal = document.getElementById('tsEntryModal');
    if (modal) modal.style.display = 'flex';
  }

  private hideModal(): void {
    const modal = document.getElementById('tsEntryModal');
    if (modal) modal.style.display = 'none';
  }

  private calcHours(): void {
    const start = (document.getElementById('tsStartTime') as HTMLInputElement)?.value;
    const end = (document.getElementById('tsEndTime') as HTMLInputElement)?.value;
    const hoursEl = document.getElementById('tsHours') as HTMLInputElement;
    if (start && end && hoursEl) {
      const s = new Date(`2000-01-01T${start}`);
      const e = new Date(`2000-01-01T${end}`);
      let diff = (e.getTime() - s.getTime()) / 3600000;
      if (diff < 0) diff += 24;
      hoursEl.value = diff.toFixed(1);
    }
  }

  private updateTagOptions(tagType: string): void {
    const group = document.getElementById('tsTagSelectGroup');
    const multiGroup = document.getElementById('tsLeadMultiGroup');
    const select = document.getElementById('tsTagSelect') as HTMLSelectElement;
    const label = document.getElementById('tsTagLabel');
    const checkboxList = document.getElementById('tsLeadCheckboxes');

    if (group) group.style.display = 'none';
    if (multiGroup) multiGroup.style.display = 'none';

    if (!tagType) return;

    if (tagType === 'lead') {
      if (multiGroup) multiGroup.style.display = 'block';
      if (checkboxList) {
        checkboxList.innerHTML = this.leads.length === 0
          ? '<p class="ts-empty-mini">No leads assigned</p>'
          : this.leads.map(l => `<label class="ts-checkbox-item"><input type="checkbox" name="tsLeadIds" value="${l.id}"><span>${this.esc(l.name)}</span></label>`).join('');
      }
      return;
    }

    if (group) group.style.display = 'block';
    let options: TagOption[] = [];
    let labelText = 'Select';
    if (tagType === 'task') { options = this.tasks; labelText = 'Select Task'; }
    else if (tagType === 'kra') { options = this.kras; labelText = 'Select KRA'; }

    if (label) label.textContent = labelText;
    if (select) {
      select.innerHTML = options.length === 0
        ? `<option value="">No ${tagType}s available</option>`
        : `<option value="">Select...</option>` + options.map(o => `<option value="${o.id}">${this.esc(o.name)}</option>`).join('');
    }
  }

  private async saveEntry(): Promise<void> {
    const startTime = (document.getElementById('tsStartTime') as HTMLInputElement).value;
    const endTime = (document.getElementById('tsEndTime') as HTMLInputElement).value;
    const hours = parseFloat((document.getElementById('tsHours') as HTMLInputElement).value);
    const description = (document.getElementById('tsDescription') as HTMLTextAreaElement).value.trim();
    const tagType = (document.getElementById('tsTagType') as HTMLSelectElement).value;
    const tagId = (document.getElementById('tsTagSelect') as HTMLSelectElement)?.value;

    if (!startTime || !endTime) { this.showToast('Please set start and end times'); return; }
    if (!hours || hours <= 0) { this.showToast('Invalid hours'); return; }
    if (!description) { this.showToast('Please enter description'); return; }

    let selectedLeadIds: number[] = [];
    if (tagType === 'lead') {
      const cbs = document.querySelectorAll('input[name="tsLeadIds"]:checked');
      selectedLeadIds = Array.from(cbs).map(cb => parseInt((cb as HTMLInputElement).value));
      if (selectedLeadIds.length === 0) { this.showToast('Select at least one lead'); return; }
    }

    const btn = document.getElementById('tsSaveEntry') as HTMLButtonElement;
    if (btn) { btn.disabled = true; btn.textContent = 'Saving...'; }

    const fmtTime = (t: string) => t.length === 5 ? `${t}:00` : t;
    const payload: any = {
      date: this.fmtDate(this.selectedDate),
      start_time: fmtTime(startTime),
      end_time: fmtTime(endTime),
      entry_type: tagType || 'others',
      comments: description
    };

    if (tagType === 'task' && tagId) payload.task_id = parseInt(tagId);
    else if (tagType === 'kra' && tagId) payload.kra_id = parseInt(tagId);
    else if (tagType === 'lead' && selectedLeadIds.length > 0) {
      if (selectedLeadIds.length === 1) payload.lead_id = selectedLeadIds[0];
      else payload.lead_ids = selectedLeadIds;
    }

    try {
      let response;
      if (this.selectedEntry) {
        response = await apiService.put(`${API_ENDPOINTS.TIMESHEET.SAVE}/${this.selectedEntry.id}`, payload);
      } else {
        response = await apiService.post(API_ENDPOINTS.TIMESHEET.SAVE, payload);
      }

      if (response.success) {
        this.showToast(this.selectedEntry ? 'Entry updated' : 'Entry added');
        this.hideModal();
        await this.loadEntries();
      } else {
        this.showToast(response.error || 'Failed to save');
      }
    } catch (error: any) {
      this.showToast(error.message || 'Failed to save');
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = 'Save'; }
    }
  }

  private async confirmDelete(entry: TimesheetEntry): Promise<void> {
    if (!confirm('Delete this timesheet entry?')) return;
    this.selectedEntry = entry;

    try {
      const response = await apiService.delete(`${API_ENDPOINTS.TIMESHEET.SAVE}/${entry.id}`);
      if (response.success) {
        this.showToast('Entry deleted');
        await this.loadEntries();
      } else {
        this.showToast('Failed to delete');
      }
    } catch (error) {
      this.showToast('Failed to delete');
    }
  }

  private showToast(message: string): void {
    const toast = document.createElement('div');
    toast.className = 'toast-message';
    toast.textContent = message;
    document.body.appendChild(toast);
    const t = setTimeout(() => toast.remove(), 3000);
    this.pendingTimers.push(t);
  }

  private esc(str: string): string {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  private async loadActivitySummaryData(): Promise<void> {
    try {
      const dateStr = this.fmtDate(this.selectedDate);
      const resp = await apiService.get<any>(`/api/v1/staff/attendance/activity-summary?target_date=${dateStr}`);
      if (resp.success && resp.data) {
        this.activitySummary = resp.data;
        this.activityDeptType = resp.data.dept_type || 'other';
      }
    } catch (e) {
      console.error('[TimesheetPage] Activity summary error:', e);
    }
    if (this.activeTab === 'today') {
      const content = document.getElementById('tsContent');
      if (content) this.renderTodayTab(content);
    }
  }

  private renderActivitySummaryHtml(): string {
    const summary = this.activitySummary;
    const collapsed = this.activityCardCollapsed;
    const arrow = collapsed ? '▶' : '▼';

    const headerStyle = 'display:flex;align-items:center;justify-content:space-between;padding:10px 12px;cursor:pointer;background:#1e293b;border-radius:10px;margin:0 0 0 0;';
    const cardStyle = 'background:#0f172a;border:1px solid #334155;border-radius:12px;margin:12px 0;overflow:hidden;';

    if (!summary) {
      return `<div style="${cardStyle}">
        <div style="${headerStyle}" id="tsActToggle">
          <span style="color:#94a3b8;font-size:13px;font-weight:600;">📊 Activity Summary</span>
          <span style="color:#64748b;font-size:11px;">${arrow}</span>
        </div>
        ${!collapsed ? '<div style="padding:12px;text-align:center;color:#64748b;font-size:12px;">Loading...</div>' : ''}
      </div>`;
    }

    const categories: any[] = summary.categories || [];
    const totals = summary.totals || {};
    const activeCats = categories.filter((c: any) => {
      if (c.source_type === 'overdue_leads') return true;
      return c.total > 0 || c.completed_minutes > 0;
    });

    const fmtMin = (m: number): string => {
      if (!m) return '0m';
      const h = Math.floor(m / 60), min = m % 60;
      return h > 0 ? `${h}h${min > 0 ? ' ' + min + 'm' : ''}` : `${min}m`;
    };

    let rowsHtml = '';
    activeCats.forEach((cat: any) => {
      const isOverdue = cat.source_type === 'overdue_leads';
      const detailOpen = !!this.activityDetailOpen[cat.source_type];
      const rowBg = isOverdue ? 'background:rgba(251,191,36,0.06);border-left:2px solid #f59e0b;' : '';
      const labelColor = isOverdue ? 'color:#d97706;' : 'color:#cbd5e1;';
      const icon = isOverdue ? '⚠️' : (cat.source_type === 'kra' ? '🎯' : cat.source_type === 'task' ? '📋' : cat.source_type === 'lead' ? '👤' : cat.source_type === 'ticket' ? '🎫' : cat.source_type === 'journey' ? '🗺️' : '⏱️');
      const pending = (cat.pending || 0) + (cat.in_progress || 0);

      let detailHtml = '';
      if (detailOpen) {
        const items: any[] = cat.items || [];
        const isKra = cat.source_type === 'kra';
        const isTask = cat.source_type === 'task';
        const isLead = cat.source_type === 'lead' || isOverdue;
        const isTicket = cat.source_type === 'ticket';
        const canEdit = isKra || isTask || isLead || isTicket;

        const statusOpts = (opts: string[][], current: string) =>
          opts.map(([v, l]) => `<option value="${v}" ${v === current ? 'selected' : ''}>${l}</option>`).join('');

        if (items.length === 0) {
          detailHtml = '<div style="padding:8px 12px;color:#64748b;font-size:12px;">No items found</div>';
        } else {
          detailHtml = items.slice(0, 20).map((item: any, idx: number) => {
            const itemId = item.id || item.source_id;
            const st = item.sub_status || item.status || 'pending';
            const stColor = (st === 'completed' || st === 'won' || st === 'work_complete') ? '#10b981'
              : (st === 'in_progress' || st === 'hot' || st === 'diagnosing') ? '#f59e0b' : '#64748b';
            const companyId = item.company_id || '';
            const tatHtml = item.tat_due_at ? `<span style="color:#ef4444;font-size:10px;"> · TAT: ${item.tat_due_at}</span>` : '';

            let statusDropdown = '';
            if (canEdit) {
              let opts: string[][] = [];
              if (isKra) opts = [['pending','Pending'],['in_progress','In Progress'],['completed','Completed'],['skipped','Skipped'],['partial','Partial']];
              else if (isTask) opts = [['pending','Pending'],['in_progress','In Progress'],['on_hold','On Hold'],['completed','Completed']];
              else if (isLead) opts = [['new','New'],['contacted','Contacted'],['warm','Warm'],['hot','Hot'],['won','Won'],['lost','Lost'],['dropped','Dropped']];
              else if (isTicket) opts = [['new','New'],['acknowledged','Acknowledged'],['diagnosing','Diagnosing'],['ready_for_work','Ready for Work'],['work_complete','Work Complete']];

              statusDropdown = `
                <div style="margin-top:6px;display:flex;gap:6px;flex-wrap:wrap;align-items:center;">
                  <select id="mActSel_${cat.source_type}_${idx}"
                    style="font-size:11px;padding:3px 6px;border:1px solid #475569;border-radius:6px;background:#1e293b;color:#e2e8f0;flex:1;min-width:100px;">
                    ${statusOpts(opts, st)}
                  </select>
                  <button data-act="save-status"
                    data-src="${cat.source_type}" data-id="${itemId}"
                    data-sel="mActSel_${cat.source_type}_${idx}"
                    data-cid="${companyId}" data-idx="${idx}"
                    style="font-size:11px;padding:3px 10px;background:#4f46e5;color:#fff;border:none;border-radius:6px;cursor:pointer;">
                    Save
                  </button>
                  <button data-act="toggle-log"
                    data-logid="mLogForm_${cat.source_type}_${idx}"
                    style="font-size:11px;padding:3px 10px;background:#0ea5e9;color:#fff;border:none;border-radius:6px;cursor:pointer;">
                    ⏱ Log
                  </button>
                </div>
                <div id="mLogForm_${cat.source_type}_${idx}" style="display:none;margin-top:6px;padding:8px;background:#1e293b;border-radius:8px;border:1px solid #334155;">
                  <div style="display:flex;gap:6px;align-items:flex-end;flex-wrap:wrap;">
                    <div>
                      <div style="font-size:10px;color:#64748b;margin-bottom:2px;">Minutes *</div>
                      <input type="number" id="mLogMin_${cat.source_type}_${idx}"
                        min="1" max="480" value="30"
                        style="width:70px;font-size:12px;padding:3px 6px;border:1px solid #475569;border-radius:6px;background:#0f172a;color:#e2e8f0;">
                    </div>
                    <div style="flex:1;min-width:120px;">
                      <div style="font-size:10px;color:#64748b;margin-bottom:2px;">Comment</div>
                      <input type="text" id="mLogCmt_${cat.source_type}_${idx}"
                        placeholder="What did you do?"
                        style="width:100%;font-size:12px;padding:3px 6px;border:1px solid #475569;border-radius:6px;background:#0f172a;color:#e2e8f0;">
                    </div>
                    <button data-act="submit-log"
                      data-src="${isLead ? 'lead' : cat.source_type}"
                      data-id="${itemId}"
                      data-minid="mLogMin_${cat.source_type}_${idx}"
                      data-cmtid="mLogCmt_${cat.source_type}_${idx}"
                      data-date="${this.fmtDate(this.selectedDate)}"
                      ${isLead || isTicket ? 'data-realtime="1"' : ''}
                      style="font-size:11px;padding:4px 10px;background:#10b981;color:#fff;border:none;border-radius:6px;cursor:pointer;">
                      Save
                    </button>
                  </div>
                  ${(isLead || isTicket) ? `<div style="margin-top:4px;font-size:10px;color:#94a3b8;">⏰ Now: ${new Date().toLocaleTimeString('en-IN',{hour:'2-digit',minute:'2-digit'})}</div>` : ''}
                </div>
              `;
            }

            return `
              <div style="padding:8px 12px;border-top:1px solid #1e293b;">
                <div style="font-size:12px;font-weight:600;color:#e2e8f0;">${this.esc(item.title || item.code || '-')}${tatHtml}</div>
                <div style="margin-top:2px;">
                  <span style="font-size:10px;padding:1px 7px;border-radius:8px;background:${stColor}22;color:${stColor};">${st.replace(/_/g,' ')}</span>
                  ${item.priority ? `<span style="margin-left:6px;font-size:10px;color:#64748b;">${item.priority}</span>` : ''}
                  ${item.phone ? `<span style="margin-left:6px;font-size:10px;color:#64748b;">📞 ${item.phone}</span>` : ''}
                </div>
                ${statusDropdown}
              </div>
            `;
          }).join('');
        }
      }

      rowsHtml += `
        <div style="${rowBg}">
          <div style="display:flex;align-items:center;padding:10px 12px;cursor:pointer;"
            data-act="toggle-detail" data-src="${cat.source_type}">
            <span style="font-size:14px;margin-right:8px;">${icon}</span>
            <div style="flex:1;">
              <div style="${labelColor}font-size:12px;font-weight:600;">${this.esc(cat.label)}</div>
              <div style="font-size:11px;color:#475569;margin-top:1px;">
                ${cat.total} items · ${cat.completed} done · ${pending} pending
                ${!isOverdue ? `· ${fmtMin(cat.completed_minutes)}` : ''}
                ${isOverdue && cat.total > 0 ? `<span style="color:#d97706;font-weight:700;"> ⚠️ ${cat.total} overdue</span>` : ''}
              </div>
            </div>
            <span style="color:#475569;font-size:12px;margin-left:8px;">${detailOpen ? '▲' : '▼'}</span>
          </div>
          ${detailOpen ? `<div style="border-top:1px solid #1e293b;">${detailHtml}</div>` : ''}
        </div>
      `;
    });

    const totalsHtml = `
      <div style="display:flex;gap:10px;padding:8px 12px;background:#162032;font-size:11px;border-top:1px solid #1e293b;">
        <span style="color:#94a3b8;">Total: <strong style="color:#e2e8f0;">${totals.total || 0}</strong></span>
        <span style="color:#94a3b8;">Done: <strong style="color:#10b981;">${totals.completed || 0}</strong></span>
        <span style="color:#94a3b8;">Pending: <strong style="color:#f59e0b;">${(totals.pending || 0) + (totals.in_progress || 0)}</strong></span>
        <span style="color:#94a3b8;">Time: <strong style="color:#7dd3fc;">${fmtMin(totals.completed_minutes || 0)}</strong></span>
      </div>
    `;

    return `
      <div style="${cardStyle}">
        <div style="${headerStyle}" id="tsActToggle">
          <span style="color:#7dd3fc;font-size:13px;font-weight:600;">📊 Activity Summary</span>
          <span style="color:#64748b;font-size:11px;">${arrow}</span>
        </div>
        ${!collapsed ? `
          ${totalsHtml}
          ${activeCats.length === 0 ? '<div style="padding:12px;text-align:center;color:#64748b;font-size:12px;">No activities yet</div>' : rowsHtml}
          <button data-act="refresh-activity"
            style="width:100%;padding:8px;background:transparent;border:none;border-top:1px solid #1e293b;color:#475569;font-size:11px;cursor:pointer;">
            ↻ Refresh Activity
          </button>
        ` : ''}
      </div>
    `;
  }

  private attachActivityListeners(): void {
    const toggle = document.getElementById('tsActToggle');
    if (toggle) {
      toggle.addEventListener('click', () => {
        this.activityCardCollapsed = !this.activityCardCollapsed;
        const content = document.getElementById('tsContent');
        if (content) this.renderTodayTab(content);
      });
    }

    document.querySelectorAll('[data-act="toggle-detail"]').forEach(el => {
      el.addEventListener('click', () => {
        const src = (el as HTMLElement).dataset.src || '';
        this.activityDetailOpen[src] = !this.activityDetailOpen[src];
        const content = document.getElementById('tsContent');
        if (content) this.renderTodayTab(content);
      });
    });

    document.querySelectorAll('[data-act="toggle-log"]').forEach(el => {
      el.addEventListener('click', () => {
        const logId = (el as HTMLElement).dataset.logid || '';
        const form = document.getElementById(logId);
        if (form) form.style.display = form.style.display === 'none' ? 'block' : 'none';
      });
    });

    document.querySelectorAll('[data-act="save-status"]').forEach(el => {
      el.addEventListener('click', async () => {
        const btn = el as HTMLButtonElement;
        const src = btn.dataset.src || '';
        const id = parseInt(btn.dataset.id || '0');
        const selId = btn.dataset.sel || '';
        const cid = btn.dataset.cid || '';
        const sel = document.getElementById(selId) as HTMLSelectElement;
        if (!sel || !id) return;
        const newStatus = sel.value;
        const origText = btn.textContent || 'Save';
        btn.textContent = '…'; btn.disabled = true;
        const ok = await this.saveActivityStatusMobile(src, id, newStatus, cid);
        if (ok) {
          btn.textContent = '✓'; btn.style.background = '#10b981';
          this.showToast('Status updated');
          const t = setTimeout(async () => {
            await this.loadActivitySummaryData();
          }, 1500);
          this.pendingTimers.push(t);
        } else {
          btn.textContent = '!'; btn.style.background = '#ef4444';
          this.showToast('Update failed');
        }
        const t2 = setTimeout(() => {
          btn.textContent = origText; btn.style.background = '#4f46e5'; btn.disabled = false;
        }, 2000);
        this.pendingTimers.push(t2);
      });
    });

    document.querySelectorAll('[data-act="submit-log"]').forEach(el => {
      el.addEventListener('click', async () => {
        const btn = el as HTMLButtonElement;
        const src = btn.dataset.src || 'custom';
        const id = parseInt(btn.dataset.id || '0');
        const minId = btn.dataset.minid || '';
        const cmtId = btn.dataset.cmtid || '';
        const dateStr = btn.dataset.date || this.fmtDate(this.selectedDate);
        const isRealtime = btn.dataset.realtime === '1';
        const minEl = document.getElementById(minId) as HTMLInputElement;
        const cmtEl = document.getElementById(cmtId) as HTMLInputElement;

        let minutes = parseInt(minEl?.value || '0');
        if (isRealtime && (!minutes || minutes < 1)) minutes = 30;
        if (!minutes || minutes < 1) { this.showToast('Enter valid minutes'); return; }

        const comment = cmtEl?.value || (isRealtime ? `Logged at ${new Date().toLocaleTimeString('en-IN',{hour:'2-digit',minute:'2-digit'})}` : '');
        const origText = btn.textContent || 'Save';
        btn.textContent = '…'; btn.disabled = true;

        const ok = await this.submitActivityLogMobile(src, id, minutes, comment, dateStr);
        if (ok) {
          btn.textContent = '✓'; btn.style.background = '#0ea5e9';
          if (minEl) minEl.value = '30';
          if (cmtEl) cmtEl.value = '';
          this.showToast(`${minutes}m logged`);
          const t = setTimeout(async () => { await this.loadActivitySummaryData(); }, 1500);
          this.pendingTimers.push(t);
        } else {
          btn.textContent = '!'; btn.style.background = '#ef4444';
          this.showToast('Log failed');
        }
        const t2 = setTimeout(() => {
          btn.textContent = origText; btn.style.background = '#10b981'; btn.disabled = false;
        }, 2000);
        this.pendingTimers.push(t2);
      });
    });

    document.querySelectorAll('[data-act="refresh-activity"]').forEach(el => {
      el.addEventListener('click', async () => {
        this.activitySummary = null;
        const content = document.getElementById('tsContent');
        if (content) this.renderTodayTab(content);
        await this.loadActivitySummaryData();
      });
    });
  }

  private async saveActivityStatusMobile(sourceType: string, itemId: number, newStatus: string, companyId: string): Promise<boolean> {
    try {
      let resp: any;
      const token = localStorage.getItem('staff_token') || sessionStorage.getItem('staff_token') || '';
      const authHeader: Record<string, string> = token ? { 'Authorization': `Bearer ${token}` } : {};

      if (sourceType === 'kra') {
        resp = await apiService.put(`/api/v1/staff/kra/instances/${itemId}`, { completion_status: newStatus });
      } else if (sourceType === 'task') {
        resp = await apiService.put(`/api/v1/staff/tasks/${itemId}/status`, { status: newStatus, notes: '' });
      } else if (sourceType === 'lead' || sourceType === 'overdue_leads') {
        const qp = companyId ? `?company_id=${companyId}` : '';
        resp = await apiService.put(`/api/v1/crm/leads/${itemId}${qp}`, { status: newStatus });
      } else if (sourceType === 'ticket') {
        const actionMap: Record<string, string> = {
          acknowledged: 'acknowledge', diagnosing: 'diagnose',
          work_complete: 'complete', ready_for_work: 'complete'
        };
        const action = actionMap[newStatus];
        if (!action) return false;
        const r = await fetch(`/api/v1/tickets/service/${itemId}/${action}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', ...authHeader },
          body: JSON.stringify({})
        });
        return r.ok;
      }
      return resp && (resp.success !== false);
    } catch (e) {
      console.error('[saveActivityStatusMobile]', e);
      return false;
    }
  }

  private async submitActivityLogMobile(sourceType: string, sourceId: number, minutes: number, comment: string, dateStr: string): Promise<boolean> {
    try {
      const resp = await apiService.post('/api/v1/staff/attendance/activity-log', {
        source_type: sourceType,
        source_id: sourceId,
        completed_minutes: minutes,
        description: comment,
        date: dateStr
      });
      return resp && (resp.success !== false);
    } catch (e) {
      console.error('[submitActivityLogMobile]', e);
      return false;
    }
  }

  cleanup(): void {
    this.pendingTimers.forEach(t => clearTimeout(t));
    this.pendingTimers = [];
  }
}
