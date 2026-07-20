/**
 * Task Detail Page - Full Task Management
 * DC Protocol: DC_MOBILE_TASK_DETAIL_001
 * Progress updates, comments, time logging, phases
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';
import { routerService } from '../services/router.service';

interface TaskComment {
  id: number;
  content: string;
  author_name: string;
  author_emp_code: string;
  created_at: string;
  attachments?: { filename: string; url: string }[];
}

interface TaskPhase {
  id: number;
  name: string;
  description: string;
  status: string;
  order_index: number;
  start_date: string | null;
  end_date: string | null;
  phase_number?: number;
  phase_title?: string;
  phase_description?: string;
  phase_status?: string;
  phase_assignee_id?: number;
  assignee_name?: string;
  assignee_code?: string;
  target_date?: string | null;
  completion_notes?: string;
  completed_at?: string | null;
  is_overdue?: boolean;
  child_task?: { id: number; task_code: string; title: string; status: string; progress: number } | null;
}

interface TimeEntry {
  id: number;
  hours: number;
  description: string;
  entry_date: string;
  created_at: string;
}

interface Task {
  id: number;
  title: string;
  description: string;
  priority: string;
  status: string;
  progress: number;
  due_date: string;
  created_at: string;
  completed_at: string | null;
  estimated_hours: number | null;
  actual_hours: number;
  creator: { id: number; full_name: string; emp_code: string } | null;
  primary_assignee: { id: number; full_name: string; emp_code: string } | null;
  secondary_assignees: { id: number; full_name: string; emp_code: string }[];
  category: string;
  comments?: TaskComment[];
  phases?: TaskPhase[];
  time_entries?: TimeEntry[];
}

export class TaskDetailPage {
  private container: HTMLElement;
  private taskId: number;
  private task: Task | null = null;
  private taskPhases: TaskPhase[] = [];
  private loading: boolean = true;
  private activeTab: 'details' | 'comments' | 'time' | 'phases' = 'details';

  constructor(container: HTMLElement, params?: { id?: string }) {
    this.container = container;
    this.taskId = parseInt(params?.id || '0');
  }

  async init(): Promise<void> {
    this.render();
    await this.loadTask();
  }

  private async loadTask(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      const [taskResponse, phasesResponse] = await Promise.all([
        apiService.get<any>(`/staff/tasks/${this.taskId}?include_comments=true&include_activity=true&include_time_entries=true`),
        apiService.get<any>(`/staff/tasks/${this.taskId}/phases?include_child_tasks=true`).catch(() => null)
      ]);

      const data = taskResponse.data as any;
      if (taskResponse.success !== false && data) {
        this.task = data.task || data;
      } else {
        this.task = null;
      }

      if (phasesResponse?.success !== false && phasesResponse?.data) {
        const phaseData = phasesResponse.data as any;
        this.taskPhases = (phaseData.phases || []).map((p: any) => ({
          id: p.id,
          name: p.phase_title,
          description: p.phase_description || '',
          status: p.phase_status,
          order_index: p.phase_number,
          start_date: p.created_at,
          end_date: p.completed_at,
          phase_number: p.phase_number,
          phase_title: p.phase_title,
          phase_description: p.phase_description,
          phase_status: p.phase_status,
          phase_assignee_id: p.phase_assignee_id,
          assignee_name: p.assignee_name,
          assignee_code: p.assignee_code,
          target_date: p.target_date,
          completion_notes: p.completion_notes,
          completed_at: p.completed_at,
          is_overdue: p.is_overdue,
          child_task: p.child_task || null
        }));
      }
    } catch (error) {
      console.error('[TaskDetailPage] Failed to load:', error);
      this.task = null;
    }

    this.loading = false;
    this.updateContent();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: 'Task Details', showBack: true })}
        
        <div class="tabs-nav">
          <button class="tab-btn ${this.activeTab === 'details' ? 'active' : ''}" data-tab="details">Details</button>
          <button class="tab-btn ${this.activeTab === 'comments' ? 'active' : ''}" data-tab="comments">Comments</button>
          <button class="tab-btn ${this.activeTab === 'time' ? 'active' : ''}" data-tab="time">Time</button>
          <button class="tab-btn ${this.activeTab === 'phases' ? 'active' : ''}" data-tab="phases">Phases</button>
        </div>

        <div id="taskContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>

      <!-- Progress Modal -->
      <div class="modal-overlay" id="progressModal" style="display: none;">
        <div class="modal-content">
          <div class="modal-header">
            <h4>Update Progress</h4>
            <button class="modal-close" id="closeProgressModal">&times;</button>
          </div>
          <div class="modal-body">
            <div class="form-group">
              <label>Progress: <span id="progressValue">0</span>%</label>
              <input type="range" id="progressSlider" class="progress-slider" min="0" max="100" value="0">
            </div>
            <div class="form-group">
              <label>Status</label>
              <select id="statusSelect" class="form-select">
                <option value="pending">Pending</option>
                <option value="in_progress">In Progress</option>
                <option value="completed">Completed</option>
              </select>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" id="cancelProgressBtn">Cancel</button>
            <button class="btn btn-primary" id="saveProgressBtn">Save</button>
          </div>
        </div>
      </div>

      <!-- Comment Modal -->
      <div class="modal-overlay" id="commentModal" style="display: none;">
        <div class="modal-content">
          <div class="modal-header">
            <h4>Add Comment</h4>
            <button class="modal-close" id="closeCommentModal">&times;</button>
          </div>
          <div class="modal-body">
            <div class="form-group">
              <label>Comment <span class="required">*</span></label>
              <textarea id="commentText" class="form-textarea" rows="4" placeholder="Enter your comment..."></textarea>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" id="cancelCommentBtn">Cancel</button>
            <button class="btn btn-primary" id="saveCommentBtn">Add Comment</button>
          </div>
        </div>
      </div>

      <!-- Time Entry Modal -->
      <div class="modal-overlay" id="timeModal" style="display: none;">
        <div class="modal-content">
          <div class="modal-header">
            <h4>Log Time</h4>
            <button class="modal-close" id="closeTimeModal">&times;</button>
          </div>
          <div class="modal-body">
            <div class="form-group">
              <label>Hours <span class="required">*</span></label>
              <input type="number" id="timeHours" class="form-input" min="0.25" max="24" step="0.25" placeholder="e.g., 2.5">
            </div>
            <div class="form-group">
              <label>Date</label>
              <input type="date" id="timeDate" class="form-input">
            </div>
            <div class="form-group">
              <label>Description</label>
              <textarea id="timeDescription" class="form-textarea" rows="2" placeholder="What did you work on?"></textarea>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" id="cancelTimeBtn">Cancel</button>
            <button class="btn btn-primary" id="saveTimeBtn">Log Time</button>
          </div>
        </div>
      </div>

      <!-- Reassign Modal -->
      <div class="modal-overlay" id="reassignModal" style="display: none;">
        <div class="modal-content">
          <div class="modal-header">
            <h4>Reassign Task</h4>
            <button class="modal-close" id="closeReassignModal">&times;</button>
          </div>
          <div class="modal-body">
            <div class="form-group">
              <label>New Assignee <span class="required">*</span></label>
              <select id="newAssignee" class="form-select">
                <option value="">Select employee...</option>
              </select>
            </div>
            <div class="form-group">
              <label>Reason for Reassignment</label>
              <textarea id="reassignReason" class="form-textarea" rows="2" placeholder="Optional reason"></textarea>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" id="cancelReassignBtn">Cancel</button>
            <button class="btn btn-primary" id="saveReassignBtn">Reassign</button>
          </div>
        </div>
      </div>

      <!-- Invite Team Modal -->
      <div class="modal-overlay" id="inviteModal" style="display: none;">
        <div class="modal-content">
          <div class="modal-header">
            <h4>Add Team Member</h4>
            <button class="modal-close" id="closeInviteModal">&times;</button>
          </div>
          <div class="modal-body">
            <div class="form-group">
              <label>Select Team Member <span class="required">*</span></label>
              <select id="inviteEmployee" class="form-select">
                <option value="">Select employee...</option>
              </select>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" id="cancelInviteBtn">Cancel</button>
            <button class="btn btn-primary" id="saveInviteBtn">Add to Task</button>
          </div>
        </div>
      </div>

      <!-- Add Sub-Task Modal -->
      <div class="modal-overlay" id="addPhaseModal" style="display: none;">
        <div class="modal-content">
          <div class="modal-header">
            <h4>Add Sub-Task</h4>
            <button class="modal-close" id="closeAddPhaseModal">&times;</button>
          </div>
          <div class="modal-body">
            <div class="form-group">
              <label>Title <span class="required">*</span></label>
              <input type="text" id="phaseTitle" class="form-input" placeholder="Enter sub-task title" maxlength="256">
            </div>
            <div class="form-group">
              <label>Description</label>
              <textarea id="phaseDescription" class="form-textarea" rows="3" placeholder="Describe the sub-task..."></textarea>
            </div>
            <div class="form-group">
              <label>Assign To <span class="required">*</span></label>
              <select id="phaseAssignee" class="form-select">
                <option value="">Select employee...</option>
              </select>
            </div>
            <div class="form-group">
              <label>Target Date</label>
              <input type="date" id="phaseTargetDate" class="form-input">
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" id="cancelAddPhaseBtn">Cancel</button>
            <button class="btn btn-primary" id="saveAddPhaseBtn">Add Sub-Task</button>
          </div>
        </div>
      </div>

      <!-- Update Phase Status Modal -->
      <div class="modal-overlay" id="updatePhaseModal" style="display: none;">
        <div class="modal-content">
          <div class="modal-header">
            <h4>Update Sub-Task Status</h4>
            <button class="modal-close" id="closeUpdatePhaseModal">&times;</button>
          </div>
          <div class="modal-body">
            <div class="form-group">
              <label>Sub-Task</label>
              <p id="updatePhaseName" style="font-weight: 600; margin: 0;"></p>
            </div>
            <div class="form-group">
              <label>Status <span class="required">*</span></label>
              <select id="phaseStatusSelect" class="form-select">
                <option value="pending">Pending</option>
                <option value="in_progress">In Progress</option>
                <option value="on_hold">On Hold</option>
                <option value="completed">Completed</option>
                <option value="cancelled">Cancelled</option>
              </select>
            </div>
            <div class="form-group" id="phaseNotesGroup" style="display: none;">
              <label>Completion Notes</label>
              <textarea id="phaseCompletionNotes" class="form-textarea" rows="2" placeholder="Add notes..."></textarea>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" id="cancelUpdatePhaseBtn">Cancel</button>
            <button class="btn btn-primary" id="saveUpdatePhaseBtn">Update Status</button>
          </div>
        </div>
      </div>
    `;

    this.attachListeners();
    this.loadEmployees();
  }

  private employees: { id: number; full_name: string; emp_code: string }[] = [];

  private async loadEmployees(): Promise<void> {
    try {
      const response = await apiService.get<any>('/staff/tasks/assignable-employees');
      if (response.success && response.data) {
        this.employees = (response.data.employees || response.data || []).map((e: any) => ({
          id: e.id,
          emp_code: e.employee_code || e.emp_code,
          full_name: e.full_name
        }));
        this.updateEmployeeSelects();
      }
    } catch (error) {
      console.error('[TaskDetailPage] Failed to load employees:', error);
    }
  }

  private updateEmployeeSelects(): void {
    const options = this.employees.map(e => 
      `<option value="${e.id}">${e.full_name} (${e.emp_code})</option>`
    ).join('');

    const selects = ['newAssignee', 'inviteEmployee', 'phaseAssignee'];
    selects.forEach(id => {
      const el = document.getElementById(id);
      if (el) el.innerHTML = `<option value="">Select employee...</option>${options}`;
    });
  }

  private attachListeners(): void {
    PageHeader.attachListeners({ title: 'Task Details', showBack: true });

    this.container.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        this.activeTab = btn.getAttribute('data-tab') as any;
        this.container.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.updateContent();
      });
    });

    document.getElementById('closeProgressModal')?.addEventListener('click', () => this.hideModal('progressModal'));
    document.getElementById('cancelProgressBtn')?.addEventListener('click', () => this.hideModal('progressModal'));
    document.getElementById('saveProgressBtn')?.addEventListener('click', () => this.saveProgress());

    document.getElementById('closeCommentModal')?.addEventListener('click', () => this.hideModal('commentModal'));
    document.getElementById('cancelCommentBtn')?.addEventListener('click', () => this.hideModal('commentModal'));
    document.getElementById('saveCommentBtn')?.addEventListener('click', () => this.saveComment());

    document.getElementById('closeTimeModal')?.addEventListener('click', () => this.hideModal('timeModal'));
    document.getElementById('cancelTimeBtn')?.addEventListener('click', () => this.hideModal('timeModal'));
    document.getElementById('saveTimeBtn')?.addEventListener('click', () => this.saveTimeEntry());

    document.getElementById('closeReassignModal')?.addEventListener('click', () => this.hideModal('reassignModal'));
    document.getElementById('cancelReassignBtn')?.addEventListener('click', () => this.hideModal('reassignModal'));
    document.getElementById('saveReassignBtn')?.addEventListener('click', () => this.saveReassignment());

    document.getElementById('closeInviteModal')?.addEventListener('click', () => this.hideModal('inviteModal'));
    document.getElementById('cancelInviteBtn')?.addEventListener('click', () => this.hideModal('inviteModal'));
    document.getElementById('saveInviteBtn')?.addEventListener('click', () => this.saveInvite());

    document.getElementById('closeAddPhaseModal')?.addEventListener('click', () => this.hideModal('addPhaseModal'));
    document.getElementById('cancelAddPhaseBtn')?.addEventListener('click', () => this.hideModal('addPhaseModal'));
    document.getElementById('saveAddPhaseBtn')?.addEventListener('click', () => this.saveNewPhase());

    document.getElementById('closeUpdatePhaseModal')?.addEventListener('click', () => this.hideModal('updatePhaseModal'));
    document.getElementById('cancelUpdatePhaseBtn')?.addEventListener('click', () => this.hideModal('updatePhaseModal'));
    document.getElementById('saveUpdatePhaseBtn')?.addEventListener('click', () => this.savePhaseStatus());

    const phaseStatusSelect = document.getElementById('phaseStatusSelect') as HTMLSelectElement;
    phaseStatusSelect?.addEventListener('change', () => {
      const notesGroup = document.getElementById('phaseNotesGroup');
      if (notesGroup) {
        notesGroup.style.display = phaseStatusSelect.value === 'completed' ? 'block' : 'none';
      }
    });

    const progressSlider = document.getElementById('progressSlider') as HTMLInputElement;
    const progressValue = document.getElementById('progressValue');
    progressSlider?.addEventListener('input', () => {
      if (progressValue) progressValue.textContent = progressSlider.value;
    });
  }

  private updateContent(): void {
    const content = document.getElementById('taskContent');
    if (!content) return;

    if (this.loading) {
      content.innerHTML = '<div class="loading-state">Loading...</div>';
      return;
    }

    if (!this.task) {
      content.innerHTML = '<div class="empty-state">Task not found</div>';
      return;
    }

    switch (this.activeTab) {
      case 'details':
        this.renderDetails(content);
        break;
      case 'comments':
        this.renderComments(content);
        break;
      case 'time':
        this.renderTimeEntries(content);
        break;
      case 'phases':
        this.renderPhases(content);
        break;
    }
  }

  private renderDetails(content: HTMLElement): void {
    const task = this.task!;
    const progressColor = task.progress >= 75 ? '#10b981' : (task.progress >= 50 ? '#3b82f6' : (task.progress >= 25 ? '#f59e0b' : '#ef4444'));

    content.innerHTML = `
      <div class="task-detail-content">
        <div class="task-header card">
          <div class="task-title-row">
            <h3>${task.title}</h3>
            <span class="priority-badge ${task.priority?.toLowerCase()}">${task.priority}</span>
          </div>
          <p class="task-description">${task.description || 'No description'}</p>
        </div>

        <div class="progress-section card">
          <div class="progress-header">
            <span>Progress</span>
            <span class="progress-value" style="color: ${progressColor}">${task.progress || 0}%</span>
          </div>
          <div class="progress-bar-lg">
            <div class="progress-fill" style="width: ${task.progress || 0}%; background: ${progressColor}"></div>
          </div>
          <button class="btn btn-outline btn-sm update-progress-btn" id="updateProgressBtn">
            Update Progress
          </button>
        </div>

        <div class="detail-cards">
          <div class="detail-card">
            <span class="label">Status</span>
            <span class="status-badge ${task.status?.toLowerCase().replace(' ', '-')}">${task.status}</span>
          </div>
          <div class="detail-card">
            <span class="label">Due Date</span>
            <span class="value ${this.isOverdue(task.due_date) ? 'overdue' : ''}">${this.formatDate(task.due_date)}</span>
          </div>
          <div class="detail-card">
            <span class="label">Category</span>
            <span class="value">${task.category || 'General'}</span>
          </div>
          <div class="detail-card">
            <span class="label">Time Logged</span>
            <span class="value">${task.actual_hours || 0}h${task.estimated_hours ? ` / ${task.estimated_hours}h est.` : ''}</span>
          </div>
        </div>

        <div class="people-section card">
          <div class="people-header">
            <h4>People</h4>
            ${task.status !== 'completed' ? `
              <div class="people-actions">
                <button class="btn btn-sm btn-outline" id="reassignBtn">Reassign</button>
                <button class="btn btn-sm btn-outline" id="inviteBtn">Add Team</button>
              </div>
            ` : ''}
          </div>
          <div class="person-row">
            <span class="label">Created By</span>
            <span class="value">${task.creator?.full_name || 'Unknown'}</span>
          </div>
          <div class="person-row">
            <span class="label">Assigned To</span>
            <span class="value">${task.primary_assignee?.full_name || 'Unassigned'}</span>
          </div>
          ${task.secondary_assignees?.length ? `
            <div class="person-row">
              <span class="label">Team</span>
              <span class="value">${task.secondary_assignees.map(a => a.full_name).join(', ')}</span>
            </div>
          ` : ''}
        </div>

        <!-- Sub-Tasks Summary on Details Tab -->
        <div class="subtasks-summary card">
          <div class="subtasks-header">
            <h4>Sub-Tasks</h4>
            <button class="btn btn-sm btn-primary" id="addSubTaskBtnDetails">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
              Add
            </button>
          </div>
          ${this.taskPhases.length === 0 ? `
            <p class="empty-hint">No sub-tasks yet. Break this task into smaller steps.</p>
          ` : `
            <div class="subtask-progress-row">
              <span>${this.taskPhases.filter(p => (p.phase_status || p.status) === 'completed').length} of ${this.taskPhases.length} completed</span>
              <div class="progress-bar-sm">
                <div class="progress-fill" style="width: ${this.taskPhases.length > 0 ? Math.round((this.taskPhases.filter(p => (p.phase_status || p.status) === 'completed').length / this.taskPhases.length) * 100) : 0}%; background: #10b981;"></div>
              </div>
            </div>
            <div class="subtask-mini-list">
              ${this.taskPhases.slice(0, 5).map(p => {
                const st = p.phase_status || p.status || 'pending';
                return `
                  <div class="subtask-mini-item">
                    <span class="subtask-check ${st === 'completed' ? 'done' : ''}">${st === 'completed' ? '&#10003;' : '&#9675;'}</span>
                    <span class="subtask-mini-title ${st === 'completed' ? 'done' : ''}">${p.phase_title || p.name}</span>
                    <button class="btn-icon-sm update-phase-status-btn" data-phase-id="${p.id}" data-phase-name="${(p.phase_title || p.name || '').replace(/"/g, '&quot;')}" data-phase-status="${st}" title="Update status">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                    </button>
                  </div>
                `;
              }).join('')}
              ${this.taskPhases.length > 5 ? `<p class="view-all-hint">+ ${this.taskPhases.length - 5} more — switch to Phases tab</p>` : ''}
            </div>
          `}
        </div>

        ${task.status !== 'completed' ? `
          <div class="action-buttons">
            <button class="btn btn-success btn-lg" id="markCompleteBtn">Mark Complete</button>
          </div>
        ` : ''}
      </div>
    `;

    document.getElementById('updateProgressBtn')?.addEventListener('click', () => this.showProgressModal());
    document.getElementById('markCompleteBtn')?.addEventListener('click', () => this.markComplete());
    document.getElementById('reassignBtn')?.addEventListener('click', () => this.showModal('reassignModal'));
    document.getElementById('inviteBtn')?.addEventListener('click', () => this.showModal('inviteModal'));
    document.getElementById('addSubTaskBtnDetails')?.addEventListener('click', () => this.showAddPhaseModal());
    
    content.querySelectorAll('.update-phase-status-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const el = (e.currentTarget as HTMLElement);
        this.showUpdatePhaseModal(
          parseInt(el.dataset.phaseId || '0'),
          el.dataset.phaseName || '',
          el.dataset.phaseStatus || 'pending'
        );
      });
    });
  }

  private renderComments(content: HTMLElement): void {
    const comments = this.task?.comments || [];

    content.innerHTML = `
      <div class="comments-section">
        <button class="btn btn-primary add-comment-btn" id="addCommentBtn">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="5" x2="12" y2="19"/>
            <line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
          Add Comment
        </button>

        ${comments.length === 0 ? `
          <div class="empty-state">No comments yet</div>
        ` : `
          <div class="comments-list">
            ${comments.map(c => `
              <div class="comment-item card">
                <div class="comment-header">
                  <span class="author">${c.author_name || c.author_emp_code}</span>
                  <span class="time">${this.formatDateTime(c.created_at)}</span>
                </div>
                <p class="comment-content">${c.content}</p>
                ${c.attachments?.length ? `
                  <div class="attachments">
                    ${c.attachments.map(a => `
                      <a href="${a.url}" class="attachment-link" target="_blank">${a.filename}</a>
                    `).join('')}
                  </div>
                ` : ''}
              </div>
            `).join('')}
          </div>
        `}
      </div>
    `;

    document.getElementById('addCommentBtn')?.addEventListener('click', () => this.showModal('commentModal'));
  }

  private renderTimeEntries(content: HTMLElement): void {
    const entries = this.task?.time_entries || [];
    const totalHours = entries.reduce((sum, e) => sum + (e.hours || 0), 0);

    content.innerHTML = `
      <div class="time-section">
        <div class="time-summary card">
          <div class="summary-row">
            <span>Total Logged</span>
            <span class="value">${totalHours.toFixed(1)} hours</span>
          </div>
          ${this.task?.estimated_hours ? `
            <div class="summary-row">
              <span>Estimated</span>
              <span class="value">${this.task.estimated_hours} hours</span>
            </div>
            <div class="progress-bar">
              <div class="progress-fill" style="width: ${Math.min(100, (totalHours / this.task.estimated_hours) * 100)}%"></div>
            </div>
          ` : ''}
        </div>

        <button class="btn btn-primary log-time-btn" id="logTimeBtn">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <polyline points="12 6 12 12 16 14"/>
          </svg>
          Log Time
        </button>

        ${entries.length === 0 ? `
          <div class="empty-state">No time entries yet</div>
        ` : `
          <div class="time-entries-list">
            ${entries.map(e => `
              <div class="time-entry-item card">
                <div class="entry-header">
                  <span class="hours">${e.hours}h</span>
                  <span class="date">${this.formatDate(e.entry_date || e.created_at)}</span>
                </div>
                ${e.description ? `<p class="entry-description">${e.description}</p>` : ''}
              </div>
            `).join('')}
          </div>
        `}
      </div>
    `;

    document.getElementById('logTimeBtn')?.addEventListener('click', () => this.showTimeModal());
  }

  private renderPhases(content: HTMLElement): void {
    const phases = this.taskPhases;
    const completedCount = phases.filter(p => (p.phase_status || p.status) === 'completed').length;
    const progressPct = phases.length > 0 ? Math.round((completedCount / phases.length) * 100) : 0;

    content.innerHTML = `
      <div class="phases-section">
        <div class="phases-actions-bar">
          <div class="phases-summary-info">
            <span class="phases-count">${phases.length} sub-task${phases.length !== 1 ? 's' : ''}</span>
            ${phases.length > 0 ? `<span class="phases-progress">${completedCount}/${phases.length} done (${progressPct}%)</span>` : ''}
          </div>
          <button class="btn btn-primary btn-sm" id="addSubTaskBtnPhases">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
            Add Sub-Task
          </button>
        </div>

        ${phases.length > 0 ? `
          <div class="phases-progress-bar">
            <div class="progress-bar-lg">
              <div class="progress-fill" style="width: ${progressPct}%; background: ${progressPct >= 75 ? '#10b981' : progressPct >= 50 ? '#3b82f6' : progressPct >= 25 ? '#f59e0b' : '#ef4444'};"></div>
            </div>
          </div>
        ` : ''}

        ${phases.length === 0 ? `
          <div class="empty-state">
            <p>No sub-tasks yet</p>
            <p class="empty-hint">Break this task into smaller, manageable steps.</p>
          </div>
        ` : `
          <div class="phases-timeline">
            ${phases.sort((a, b) => (a.phase_number || a.order_index) - (b.phase_number || b.order_index)).map((p, idx) => {
              const st = p.phase_status || p.status || 'pending';
              const statusLabel = st.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase());
              const isOverdue = p.is_overdue || (p.target_date && new Date(p.target_date) < new Date() && st !== 'completed' && st !== 'cancelled');
              return `
              <div class="phase-item ${st}${isOverdue ? ' overdue' : ''}">
                <div class="phase-indicator">
                  <span class="phase-number ${st === 'completed' ? 'done' : ''}">${st === 'completed' ? '&#10003;' : idx + 1}</span>
                </div>
                <div class="phase-content card">
                  <div class="phase-header">
                    <span class="phase-name">${p.phase_title || p.name}</span>
                    <span class="status-badge ${st}">${statusLabel}</span>
                  </div>
                  ${(p.phase_description || p.description) ? `<p class="phase-description">${p.phase_description || p.description}</p>` : ''}
                  <div class="phase-meta">
                    ${p.assignee_name ? `<span class="phase-assignee"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg> ${p.assignee_name}</span>` : ''}
                    ${p.target_date ? `<span class="phase-date${isOverdue ? ' overdue-text' : ''}"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg> ${this.formatDate(p.target_date)}${isOverdue ? ' (Overdue)' : ''}</span>` : ''}
                  </div>
                  ${p.child_task ? `
                    <div class="phase-child-progress">
                      <div class="progress-bar-xs"><div class="progress-fill" style="width: ${p.child_task.progress || 0}%; background: #3b82f6;"></div></div>
                      <span class="child-progress-label">${p.child_task.progress || 0}%</span>
                    </div>
                  ` : ''}
                  <div class="phase-actions">
                    <button class="btn btn-sm btn-outline update-phase-btn" data-phase-id="${p.id}" data-phase-name="${(p.phase_title || p.name || '').replace(/"/g, '&quot;')}" data-phase-status="${st}">Update Status</button>
                  </div>
                </div>
              </div>
            `;}).join('')}
          </div>
        `}
      </div>
    `;

    document.getElementById('addSubTaskBtnPhases')?.addEventListener('click', () => this.showAddPhaseModal());
    
    content.querySelectorAll('.update-phase-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const el = (e.currentTarget as HTMLElement);
        this.showUpdatePhaseModal(
          parseInt(el.dataset.phaseId || '0'),
          el.dataset.phaseName || '',
          el.dataset.phaseStatus || 'pending'
        );
      });
    });
  }

  private selectedPhaseId: number = 0;

  private showAddPhaseModal(): void {
    (document.getElementById('phaseTitle') as HTMLInputElement).value = '';
    (document.getElementById('phaseDescription') as HTMLTextAreaElement).value = '';
    (document.getElementById('phaseTargetDate') as HTMLInputElement).value = '';
    const assigneeSelect = document.getElementById('phaseAssignee') as HTMLSelectElement;
    if (assigneeSelect) assigneeSelect.selectedIndex = 0;
    this.showModal('addPhaseModal');
  }

  private showUpdatePhaseModal(phaseId: number, phaseName: string, currentStatus: string): void {
    this.selectedPhaseId = phaseId;
    const nameEl = document.getElementById('updatePhaseName');
    const statusSelect = document.getElementById('phaseStatusSelect') as HTMLSelectElement;
    const notesGroup = document.getElementById('phaseNotesGroup');
    const notesInput = document.getElementById('phaseCompletionNotes') as HTMLTextAreaElement;
    
    if (nameEl) nameEl.textContent = phaseName;
    if (statusSelect) statusSelect.value = currentStatus;
    if (notesGroup) notesGroup.style.display = currentStatus === 'completed' ? 'block' : 'none';
    if (notesInput) notesInput.value = '';
    
    this.showModal('updatePhaseModal');
  }

  private async saveNewPhase(): Promise<void> {
    const title = (document.getElementById('phaseTitle') as HTMLInputElement)?.value?.trim();
    const description = (document.getElementById('phaseDescription') as HTMLTextAreaElement)?.value?.trim();
    const assigneeId = (document.getElementById('phaseAssignee') as HTMLSelectElement)?.value;
    const targetDate = (document.getElementById('phaseTargetDate') as HTMLInputElement)?.value;

    if (!title) { alert('Please enter a sub-task title'); return; }
    if (!assigneeId) { alert('Please select an assignee'); return; }

    const btn = document.getElementById('saveAddPhaseBtn') as HTMLButtonElement;
    if (btn) { btn.disabled = true; btn.textContent = 'Adding...'; }

    try {
      const response = await apiService.post(`/staff/tasks/${this.taskId}/phases`, {
        phase_title: title,
        phase_description: description || undefined,
        phase_assignee_id: parseInt(assigneeId),
        target_date: targetDate || undefined
      });

      if (response.success) {
        this.hideModal('addPhaseModal');
        await this.loadTask();
        alert('Sub-task added successfully!');
      } else {
        alert((response as any).error || 'Failed to add sub-task');
      }
    } catch (error: any) {
      alert(error.message || 'Failed to add sub-task');
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = 'Add Sub-Task'; }
    }
  }

  private async savePhaseStatus(): Promise<void> {
    const statusSelect = document.getElementById('phaseStatusSelect') as HTMLSelectElement;
    const notesInput = document.getElementById('phaseCompletionNotes') as HTMLTextAreaElement;
    const newStatus = statusSelect?.value;
    const notes = notesInput?.value?.trim();

    if (!newStatus) { alert('Please select a status'); return; }

    const btn = document.getElementById('saveUpdatePhaseBtn') as HTMLButtonElement;
    if (btn) { btn.disabled = true; btn.textContent = 'Updating...'; }

    try {
      const payload: any = { phase_status: newStatus };
      if (notes) payload.completion_notes = notes;

      const response = await apiService.patch(`/staff/tasks/${this.taskId}/phases/${this.selectedPhaseId}`, payload);

      if (response.success) {
        this.hideModal('updatePhaseModal');
        await this.loadTask();
        alert('Sub-task status updated!');
      } else {
        alert((response as any).error || 'Failed to update status');
      }
    } catch (error: any) {
      alert(error.message || 'Failed to update status');
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = 'Update Status'; }
    }
  }

  private showProgressModal(): void {
    const modal = document.getElementById('progressModal');
    const slider = document.getElementById('progressSlider') as HTMLInputElement;
    const value = document.getElementById('progressValue');
    const status = document.getElementById('statusSelect') as HTMLSelectElement;

    if (slider && this.task) slider.value = String(this.task.progress || 0);
    if (value && this.task) value.textContent = String(this.task.progress || 0);
    if (status && this.task) status.value = this.task.status?.toLowerCase().replace(' ', '_') || 'pending';

    if (modal) modal.style.display = 'flex';
  }

  private showTimeModal(): void {
    const modal = document.getElementById('timeModal');
    const dateInput = document.getElementById('timeDate') as HTMLInputElement;
    
    if (dateInput) {
      dateInput.value = new Date().toISOString().split('T')[0];
    }
    
    (document.getElementById('timeHours') as HTMLInputElement).value = '';
    (document.getElementById('timeDescription') as HTMLTextAreaElement).value = '';
    
    if (modal) modal.style.display = 'flex';
  }

  private showModal(modalId: string): void {
    const modal = document.getElementById(modalId);
    if (modal) modal.style.display = 'flex';
  }

  private hideModal(modalId: string): void {
    const modal = document.getElementById(modalId);
    if (modal) modal.style.display = 'none';
  }

  private async saveProgress(): Promise<void> {
    const slider = document.getElementById('progressSlider') as HTMLInputElement;
    const statusSelect = document.getElementById('statusSelect') as HTMLSelectElement;
    
    const progress = parseInt(slider?.value || '0');
    const status = statusSelect?.value || 'pending';

    const btn = document.getElementById('saveProgressBtn') as HTMLButtonElement;
    if (btn) { btn.disabled = true; btn.textContent = 'Saving...'; }

    try {
      const response = await apiService.put(`/staff/tasks/${this.taskId}`, {
        progress,
        status
      });

      if (response.success) {
        this.hideModal('progressModal');
        await this.loadTask();
      } else {
        alert(response.error || 'Failed to update progress');
      }
    } catch (error: any) {
      alert(error.message || 'Failed to update progress');
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = 'Save'; }
    }
  }

  private async saveComment(): Promise<void> {
    const commentText = (document.getElementById('commentText') as HTMLTextAreaElement)?.value?.trim();

    if (!commentText) {
      alert('Please enter a comment');
      return;
    }

    const btn = document.getElementById('saveCommentBtn') as HTMLButtonElement;
    if (btn) { btn.disabled = true; btn.textContent = 'Adding...'; }

    try {
      const formData = new FormData();
      formData.append('content', commentText);
      const response = await apiService.postFormData(`/staff/tasks/${this.taskId}/comments`, formData);

      if (response.success) {
        (document.getElementById('commentText') as HTMLTextAreaElement).value = '';
        this.hideModal('commentModal');
        await this.loadTask();
      } else {
        alert(response.error || 'Failed to add comment');
      }
    } catch (error: any) {
      alert(error.message || 'Failed to add comment');
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = 'Add Comment'; }
    }
  }

  private async saveTimeEntry(): Promise<void> {
    const hours = parseFloat((document.getElementById('timeHours') as HTMLInputElement)?.value || '0');
    const date = (document.getElementById('timeDate') as HTMLInputElement)?.value;
    const description = (document.getElementById('timeDescription') as HTMLTextAreaElement)?.value?.trim();

    if (!hours || hours <= 0) {
      alert('Please enter valid hours');
      return;
    }

    const btn = document.getElementById('saveTimeBtn') as HTMLButtonElement;
    if (btn) { btn.disabled = true; btn.textContent = 'Logging...'; }

    try {
      const response = await apiService.post(`/staff/tasks/${this.taskId}/time-entry`, {
        hours,
        entry_date: date,
        description
      });

      if (response.success) {
        this.hideModal('timeModal');
        await this.loadTask();
        alert('Time logged successfully!');
      } else {
        alert(response.error || 'Failed to log time');
      }
    } catch (error: any) {
      alert(error.message || 'Failed to log time');
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = 'Log Time'; }
    }
  }

  private async markComplete(): Promise<void> {
    if (!confirm('Mark this task as complete?')) return;

    try {
      const response = await apiService.put(`/staff/tasks/${this.taskId}`, {
        status: 'completed',
        progress: 100
      });

      if (response.success) {
        await this.loadTask();
        alert('Task marked as complete!');
      } else {
        alert(response.error || 'Failed to complete task');
      }
    } catch (error: any) {
      alert(error.message || 'Failed to complete task');
    }
  }

  private async saveReassignment(): Promise<void> {
    const newAssigneeId = (document.getElementById('newAssignee') as HTMLSelectElement)?.value;
    const reason = (document.getElementById('reassignReason') as HTMLTextAreaElement)?.value?.trim();

    if (!newAssigneeId) {
      alert('Please select a new assignee');
      return;
    }

    const btn = document.getElementById('saveReassignBtn') as HTMLButtonElement;
    if (btn) { btn.disabled = true; btn.textContent = 'Reassigning...'; }

    try {
      const response = await apiService.post(`/staff/tasks/${this.taskId}/reassign`, {
        new_primary_assignee_id: parseInt(newAssigneeId),
        reason
      });

      if (response.success) {
        this.hideModal('reassignModal');
        await this.loadTask();
        alert('Task reassigned successfully!');
      } else {
        alert(response.error || 'Failed to reassign task');
      }
    } catch (error: any) {
      alert(error.message || 'Failed to reassign task');
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = 'Reassign'; }
    }
  }

  private async saveInvite(): Promise<void> {
    const employeeId = (document.getElementById('inviteEmployee') as HTMLSelectElement)?.value;

    if (!employeeId) {
      alert('Please select an employee');
      return;
    }

    const btn = document.getElementById('saveInviteBtn') as HTMLButtonElement;
    if (btn) { btn.disabled = true; btn.textContent = 'Adding...'; }

    try {
      const response = await apiService.post(`/staff/tasks/${this.taskId}/invite`, {
        employee_id: parseInt(employeeId)
      });

      if (response.success) {
        this.hideModal('inviteModal');
        await this.loadTask();
        alert('Team member added successfully!');
      } else {
        alert(response.error || 'Failed to add team member');
      }
    } catch (error: any) {
      alert(error.message || 'Failed to add team member');
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = 'Add to Task'; }
    }
  }

  private isOverdue(dateStr: string): boolean {
    if (!dateStr) return false;
    return new Date(dateStr) < new Date();
  }

  private formatDate(dateStr: string): string {
    if (!dateStr) return 'Not set';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { day: 'numeric', month: 'short', year: 'numeric' });
  }

  private formatDateTime(dateStr: string): string {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { 
      day: 'numeric', 
      month: 'short',
      hour: '2-digit',
      minute: '2-digit'
    });
  }
}
