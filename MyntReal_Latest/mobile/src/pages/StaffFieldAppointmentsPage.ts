/**
 * Staff Field Appointments & Supporting Staff Page (Mobile View)
 * DC Protocol: Field Appointments & Supporting Staff Workflow
 * Parity across Web, Mobile SPA, Android, and iOS.
 * 
 * Supports:
 * - Bank Visits (Option 1)
 * - Customer Location Visits (Option 2)
 * - Other Official Visits (Option 3)
 * - GPS Verification & On-time performance
 * - Rear-camera photo capture proof
 * - Live status transitions: Assigned -> Accepted -> In Progress -> Reached -> Completed
 */

import { apiService } from '../services/api.service';
import { authService } from '../services/auth.service';
import { PageHeader } from '../components/PageHeader';
import { routerService } from '../services/router.service';
import { cameraService } from '../services/camera.service';
import { Geolocation } from '@capacitor/geolocation';
import { unifiedWAModal } from '../components/UnifiedWAModal';

export interface FieldAppointmentItem {
  id: number;
  appointment_code: string;
  lead_id: number;
  visit_type: 'visit_bank' | 'visit_customer' | 'others';
  purpose?: string;
  status: 'assigned' | 'accepted' | 'in_progress' | 'reached' | 'completed' | 'rescheduled' | 'unable_to_visit' | 'cancelled';
  appointment_date: string;
  preferred_time?: string;
  scheduled_start_time?: string;
  assigned_to_id: number;
  assigned_to?: {
    id: number;
    emp_code?: string;
    full_name?: string;
    phone?: string;
    department?: string;
  };
  lead?: {
    id: number;
    name?: string;
    phone?: string;
    city?: string;
    area?: string;
    address?: string;
    category?: string;
  };
  bank_name?: string;
  bank_branch?: string;
  bank_address?: string;
  bank_contact_person?: string;
  bank_contact_phone?: string;
  bank_google_maps_url?: string;
  customer_address?: string;
  customer_city?: string;
  customer_area?: string;
  customer_pincode?: string;
  customer_google_maps_url?: string;
  other_location_title?: string;
  other_location_address?: string;
  other_contact_person?: string;
  other_contact_phone?: string;
  other_google_maps_url?: string;
  telecaller_instructions?: string;
  reached_at?: string;
  reached_latitude?: number;
  reached_longitude?: number;
  reached_accuracy_meters?: number;
  started_at?: string;
  completed_at?: string;
  outcome_status?: string;
  outcome_summary?: string;
  photo_path?: string;
  photo_url?: string;
  is_gps_verified?: boolean;
  visited_on_time?: boolean;
}

const FA_STYLES = `
<style id="fa-page-styles">
  .fa-page-container {
    background: #0f172a;
    color: #f1f5f9;
    min-height: 100vh;
    padding-bottom: 80px;
    display: flex;
    flex-direction: column;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    box-sizing: border-box;
  }
  .fa-page-container * {
    box-sizing: border-box;
  }

  /* Metric Strip */
  .fa-metrics-strip {
    padding: 10px 14px;
    background: #1e293b;
    border-bottom: 1px solid #334155;
  }
  .fa-metrics-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 8px;
  }
  .fa-metric-card {
    padding: 8px 4px;
    border-radius: 10px;
    text-align: center;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    min-height: 52px;
  }
  .fa-metric-card.total {
    background: #0f172a;
    border: 1px solid #334155;
  }
  .fa-metric-card.visited {
    background: rgba(6, 78, 59, 0.45);
    border: 1px solid rgba(16, 185, 129, 0.4);
  }
  .fa-metric-card.ontime {
    background: rgba(14, 116, 144, 0.45);
    border: 1px solid rgba(14, 165, 233, 0.4);
  }
  .fa-metric-card.pct {
    background: rgba(88, 28, 135, 0.45);
    border: 1px solid rgba(168, 85, 247, 0.4);
  }
  .fa-metric-label {
    font-size: 9.5px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-bottom: 3px;
  }
  .fa-metric-card.total .fa-metric-label { color: #94a3b8; }
  .fa-metric-card.visited .fa-metric-label { color: #34d399; }
  .fa-metric-card.ontime .fa-metric-label { color: #38bdf8; }
  .fa-metric-card.pct .fa-metric-label { color: #c084fc; }

  .fa-metric-val {
    font-size: 16px;
    font-weight: 800;
    line-height: 1.1;
  }
  .fa-metric-card.total .fa-metric-val { color: #ffffff; }
  .fa-metric-card.visited .fa-metric-val { color: #10b981; }
  .fa-metric-card.ontime .fa-metric-val { color: #38bdf8; }
  .fa-metric-card.pct .fa-metric-val { color: #c084fc; }

  /* Period Pills Scroll */
  .fa-period-bar {
    padding: 10px 14px;
    background: rgba(15, 23, 42, 0.95);
    border-bottom: 1px solid #1e293b;
    display: flex;
    align-items: center;
    gap: 8px;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
  }
  .fa-period-bar::-webkit-scrollbar { display: none; }
  .fa-period-pill {
    padding: 6px 14px;
    border-radius: 9999px;
    font-size: 12px;
    font-weight: 600;
    white-space: nowrap;
    border: 1px solid #334155;
    background: #1e293b;
    color: #94a3b8;
    cursor: pointer;
    transition: all 0.2s ease;
  }
  .fa-period-pill.active {
    background: #059669;
    border-color: #10b981;
    color: #ffffff;
    box-shadow: 0 2px 8px rgba(5, 150, 105, 0.4);
  }

  /* Search & Filter Bar */
  .fa-filter-bar {
    padding: 12px 14px;
    background: #1e293b;
    border-bottom: 1px solid #334155;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .fa-search-box {
    position: relative;
    width: 100%;
  }
  .fa-search-icon {
    position: absolute;
    left: 12px;
    top: 50%;
    transform: translateY(-50%);
    font-size: 13px;
    color: #64748b;
    pointer-events: none;
  }
  .fa-search-input {
    width: 100%;
    background: #0f172a;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 9px 12px 9px 34px;
    font-size: 13px;
    color: #f1f5f9;
    outline: none;
    transition: border-color 0.2s, box-shadow 0.2s;
  }
  .fa-search-input:focus {
    border-color: #10b981;
    box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.25);
  }
  .fa-search-input::placeholder {
    color: #64748b;
  }

  .fa-controls-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    flex-wrap: wrap;
  }
  .fa-status-tabs {
    display: flex;
    background: #0f172a;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 3px;
    gap: 3px;
  }
  .fa-status-tab {
    padding: 5px 12px;
    border-radius: 7px;
    font-size: 11.5px;
    font-weight: 700;
    border: none;
    background: transparent;
    color: #94a3b8;
    cursor: pointer;
    transition: all 0.2s;
  }
  .fa-status-tab.active {
    background: #334155;
    color: #ffffff;
    box-shadow: 0 1px 4px rgba(0,0,0,0.3);
  }

  .fa-team-view-label {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 11.5px;
    font-weight: 600;
    color: #94a3b8;
    cursor: pointer;
    white-space: nowrap;
    user-select: none;
  }
  .fa-team-view-checkbox {
    width: 16px;
    height: 16px;
    accent-color: #10b981;
    cursor: pointer;
  }

  /* Feed & Cards */
  .fa-feed {
    flex: 1;
    padding: 12px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .fa-card {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 14px;
    padding: 14px;
    box-shadow: 0 3px 12px rgba(0,0,0,0.22);
    display: flex;
    flex-direction: column;
    gap: 10px;
    transition: transform 0.15s, border-color 0.15s;
  }
  .fa-card:active {
    transform: scale(0.99);
  }

  .fa-card-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 6px;
    padding-bottom: 8px;
    border-bottom: 1px solid rgba(51, 65, 85, 0.7);
  }
  .fa-badge-code-wrap {
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .fa-type-badge {
    padding: 3px 8px;
    border-radius: 6px;
    font-size: 10.5px;
    font-weight: 700;
    display: inline-flex;
    align-items: center;
    gap: 4px;
  }
  .fa-type-badge.bank {
    background: rgba(6, 95, 70, 0.55);
    color: #6ee7b7;
    border: 1px solid rgba(16, 185, 129, 0.45);
  }
  .fa-type-badge.customer {
    background: rgba(3, 105, 161, 0.55);
    color: #7dd3fc;
    border: 1px solid rgba(14, 165, 233, 0.45);
  }
  .fa-type-badge.other {
    background: rgba(180, 83, 9, 0.55);
    color: #fde68a;
    border: 1px solid rgba(245, 158, 11, 0.45);
  }

  .fa-code {
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 11.5px;
    font-weight: 700;
    color: #cbd5e1;
  }

  .fa-status-pill {
    padding: 3px 9px;
    border-radius: 6px;
    font-size: 10.5px;
    font-weight: 700;
    border: 1px solid transparent;
  }
  .fa-status-pill.assigned { background: rgba(30, 58, 138, 0.6); color: #93c5fd; border-color: rgba(59, 130, 246, 0.4); }
  .fa-status-pill.accepted { background: rgba(22, 78, 99, 0.6); color: #67e8f9; border-color: rgba(6, 182, 212, 0.4); }
  .fa-status-pill.in_progress { background: rgba(49, 46, 129, 0.6); color: #a5b4fc; border-color: rgba(99, 102, 241, 0.4); }
  .fa-status-pill.reached { background: rgba(88, 28, 135, 0.6); color: #d8b4fe; border-color: rgba(168, 85, 247, 0.4); }
  .fa-status-pill.completed { background: rgba(6, 78, 59, 0.6); color: #6ee7b7; border-color: rgba(16, 185, 129, 0.4); }
  .fa-status-pill.rescheduled { background: rgba(120, 53, 15, 0.6); color: #fde68a; border-color: rgba(245, 158, 11, 0.4); }
  .fa-status-pill.unable_to_visit { background: rgba(136, 19, 55, 0.6); color: #fda4af; border-color: rgba(244, 63, 94, 0.4); }
  .fa-status-pill.cancelled { background: #334155; color: #94a3b8; border-color: #475569; }

  .fa-card-lead {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 10px;
  }
  .fa-lead-name {
    font-size: 15px;
    font-weight: 700;
    color: #ffffff;
    line-height: 1.25;
  }
  .fa-lead-phone {
    font-size: 12px;
    color: #94a3b8;
    font-family: monospace;
    margin-top: 3px;
  }
  .fa-lead-actions {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-shrink: 0;
  }
  .fa-action-btn-circle {
    width: 34px;
    height: 34px;
    border-radius: 9px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
    border: 1px solid transparent;
    text-decoration: none;
    cursor: pointer;
    transition: all 0.15s;
  }
  .fa-action-btn-circle:active {
    transform: scale(0.92);
  }
  .fa-action-btn-circle.call {
    background: rgba(6, 78, 59, 0.55);
    border-color: rgba(16, 185, 129, 0.45);
    color: #34d399;
  }
  .fa-action-btn-circle.wa {
    background: rgba(6, 78, 59, 0.55);
    border-color: rgba(16, 185, 129, 0.45);
    color: #34d399;
  }
  .fa-action-btn-circle.maps {
    background: rgba(14, 116, 144, 0.55);
    border-color: rgba(14, 165, 233, 0.45);
    color: #38bdf8;
  }

  .fa-dest-box {
    background: #0f172a;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 10px 12px;
    font-size: 12px;
    display: flex;
    flex-direction: column;
    gap: 3px;
  }
  .fa-dest-title {
    font-weight: 700;
    color: #e2e8f0;
    font-size: 12.5px;
  }
  .fa-dest-sub {
    color: #94a3b8;
    font-size: 11px;
    line-height: 1.35;
  }
  .fa-dest-purpose {
    color: #cbd5e1;
    font-size: 11px;
    margin-top: 4px;
    padding-top: 4px;
    border-top: 1px solid rgba(51, 65, 85, 0.6);
  }
  .fa-dest-instructions {
    color: #f59e0b;
    font-size: 11px;
    margin-top: 2px;
  }

  .fa-meta-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 11.5px;
    color: #94a3b8;
    flex-wrap: wrap;
    gap: 4px;
  }

  .fa-workflow-actions {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 4px;
    padding-top: 8px;
    border-top: 1px solid rgba(51, 65, 85, 0.7);
  }
  .fa-wf-btn {
    flex: 1;
    padding: 10px 12px;
    border-radius: 10px;
    font-size: 12px;
    font-weight: 700;
    border: none;
    color: #ffffff;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.25);
    transition: all 0.15s;
  }
  .fa-wf-btn:active {
    transform: scale(0.97);
  }
  .fa-wf-btn.accept { background: linear-gradient(135deg, #0891b2, #06b6d4); }
  .fa-wf-btn.start { background: linear-gradient(135deg, #4f46e5, #6366f1); }
  .fa-wf-btn.reached { background: linear-gradient(135deg, #7e22ce, #9333ea); }
  .fa-wf-btn.complete { background: linear-gradient(135deg, #059669, #10b981); }

  /* Proof & Badges */
  .fa-proof-row {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-top: 2px;
  }
  .fa-proof-tag {
    padding: 2.5px 7px;
    border-radius: 5px;
    font-size: 10px;
    font-weight: 700;
  }
  .fa-proof-tag.ok { background: rgba(6, 78, 59, 0.75); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.4); }
  .fa-proof-tag.warn { background: rgba(120, 53, 15, 0.75); color: #fde68a; border: 1px solid rgba(245, 158, 11, 0.4); }
  .fa-proof-tag.muted { background: #334155; color: #94a3b8; border: 1px solid #475569; }

  .fa-photo-preview-strip {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-top: 8px;
    border-top: 1px solid rgba(51, 65, 85, 0.6);
  }
  .fa-photo-thumb {
    width: 42px;
    height: 42px;
    border-radius: 8px;
    object-fit: cover;
    border: 1px solid #475569;
    cursor: pointer;
  }

  /* Modals */
  .fa-modal-overlay {
    position: fixed;
    inset: 0;
    z-index: 9999;
    background: rgba(0, 0, 0, 0.75);
    backdrop-filter: blur(4px);
    display: flex;
    align-items: flex-end;
    justify-content: center;
    padding: 0;
  }
  .fa-modal-card {
    background: #1e293b;
    border: 1px solid #334155;
    border-top-left-radius: 20px;
    border-top-right-radius: 20px;
    width: 100%;
    max-width: 500px;
    max-height: 90vh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    box-shadow: 0 -8px 30px rgba(0,0,0,0.5);
    animation: faSlideUp 0.25s ease-out;
  }
  @keyframes faSlideUp {
    from { transform: translateY(100%); }
    to { transform: translateY(0); }
  }

  .fa-modal-header {
    padding: 14px 16px;
    background: #064e3b;
    border-bottom: 1px solid #047857;
    display: flex;
    align-items: center;
    justify-content: space-between;
    color: #ffffff;
  }
  .fa-modal-title { font-size: 15px; font-weight: 700; display: flex; align-items: center; gap: 6px; }
  .fa-modal-subtitle { font-size: 11px; color: #6ee7b7; font-family: monospace; margin-top: 2px; }
  .fa-modal-close {
    width: 30px;
    height: 30px;
    border-radius: 50%;
    background: rgba(6, 95, 70, 0.6);
    color: #6ee7b7;
    border: none;
    font-size: 18px;
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
  }

  .fa-modal-body {
    padding: 16px;
    flex: 1;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .fa-modal-label {
    display: block;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    font-weight: 700;
    color: #94a3b8;
    margin-bottom: 6px;
  }

  .fa-photo-capture-box {
    width: 100%;
    height: 160px;
    border-radius: 12px;
    border: 2px dashed #475569;
    background: #0f172a;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 6px;
    cursor: pointer;
    overflow: hidden;
    position: relative;
    transition: border-color 0.2s;
  }
  .fa-photo-capture-box:active {
    border-color: #10b981;
  }

  .fa-select, .fa-textarea {
    width: 100%;
    background: #0f172a;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 10px 12px;
    font-size: 13px;
    color: #ffffff;
    outline: none;
  }
  .fa-select:focus, .fa-textarea:focus {
    border-color: #10b981;
  }

  .fa-modal-footer {
    padding: 12px 16px;
    background: #0f172a;
    border-top: 1px solid #334155;
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 10px;
  }
  .fa-cancel-btn {
    padding: 9px 16px;
    border-radius: 9px;
    background: #334155;
    color: #cbd5e1;
    font-size: 12px;
    font-weight: 600;
    border: none;
    cursor: pointer;
  }
  .fa-submit-btn {
    padding: 9px 18px;
    border-radius: 9px;
    background: linear-gradient(135deg, #059669, #10b981);
    color: #ffffff;
    font-size: 12px;
    font-weight: 700;
    border: none;
    cursor: pointer;
    box-shadow: 0 2px 8px rgba(5, 150, 105, 0.4);
  }

  /* Status and Feed States */
  .fa-loading-box, .fa-empty-box {
    padding: 44px 20px;
    text-align: center;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 10px;
    color: #94a3b8;
  }
  .fa-spinner {
    width: 30px;
    height: 30px;
    border: 3px solid rgba(16, 185, 129, 0.2);
    border-top-color: #10b981;
    border-radius: 50%;
    animation: faSpin 0.7s linear infinite;
  }
  @keyframes faSpin {
    to { transform: rotate(360deg); }
  }

  .fa-error-card {
    padding: 20px;
    border-radius: 14px;
    background: rgba(136, 19, 55, 0.35);
    border: 1px solid rgba(244, 63, 94, 0.45);
    text-align: center;
    color: #fda4af;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    margin: 20px auto;
    max-width: 340px;
  }
  .fa-retry-btn {
    padding: 8px 20px;
    background: #be123c;
    color: white;
    border: none;
    border-radius: 9px;
    font-size: 12px;
    font-weight: 700;
    cursor: pointer;
    margin-top: 4px;
    transition: background 0.15s;
  }
  .fa-retry-btn:active {
    background: #9f1239;
  }
</style>
`;

export class StaffFieldAppointmentsPage {
  private container: HTMLElement;
  private appointments: FieldAppointmentItem[] = [];
  private metrics: any = {};
  private isLoading: boolean = false;
  private currentPeriod: string = 'all'; // 'all', 'today', 'yesterday', 'this_week', 'last_week', 'this_month'
  private currentStatusTab: string = 'all'; // 'all', 'pending', 'reached', 'completed'
  private searchQuery: string = '';
  private viewAllTeam: boolean = false;
  private isManagerOrLead: boolean = false;

  // Completion modal state
  private activeApptForCompletion: FieldAppointmentItem | null = null;
  private capturedPhotoBase64: string | null = null;
  private capturedCoords: { lat: number; lng: number; accuracy: number } | null = null;

  constructor(container: HTMLElement) {
    this.container = container;
    const user = authService.getAuthState().user;
    const hLevel = user?.hierarchy_level || user?.role?.hierarchy_level || 0;
    this.isManagerOrLead = user?.is_super_admin || hLevel >= 50;
    this.init();
  }

  private async init(): Promise<void> {
    this.renderSkeleton();
    await this.fetchAppointments();
  }

  private renderSkeleton(): void {
    this.container.innerHTML = `
      ${FA_STYLES}
      <div class="fa-page-container">
        ${PageHeader.render({
          title: 'Field Appointments',
          subtitle: 'Supporting Staff Visits',
          showBack: true
        })}

        <!-- Metric Badges Strip -->
        <div class="fa-metrics-strip">
          <div class="fa-metrics-grid" id="metrics-strip">
            <div class="fa-metric-card total">
              <div class="fa-metric-label">Total</div>
              <div class="fa-metric-val" id="m-total">—</div>
            </div>
            <div class="fa-metric-card visited">
              <div class="fa-metric-label">Visited</div>
              <div class="fa-metric-val" id="m-completed">—</div>
            </div>
            <div class="fa-metric-card ontime">
              <div class="fa-metric-label">On-Time</div>
              <div class="fa-metric-val" id="m-ontime">—</div>
            </div>
            <div class="fa-metric-card pct">
              <div class="fa-metric-label">On-Time %</div>
              <div class="fa-metric-val" id="m-ontime-pct">—</div>
            </div>
          </div>
        </div>

        <!-- Period Filter Pills -->
        <div class="fa-period-bar">
          <button class="fa-period-pill active" data-period="all">Overall</button>
          <button class="fa-period-pill" data-period="today">Today</button>
          <button class="fa-period-pill" data-period="yesterday">Yesterday</button>
          <button class="fa-period-pill" data-period="this_week">This Week</button>
          <button class="fa-period-pill" data-period="last_week">Last Week</button>
          <button class="fa-period-pill" data-period="this_month">This Month</button>
        </div>

        <!-- Search & Status Tabs -->
        <div class="fa-filter-bar">
          <div class="fa-search-box">
            <span class="fa-search-icon">🔍</span>
            <input type="text" id="fa-search-input" placeholder="Search by code, lead, phone, bank..." class="fa-search-input">
          </div>

          <div class="fa-controls-row">
            <div class="fa-status-tabs">
              <button class="fa-status-tab active" data-tab="all">All</button>
              <button class="fa-status-tab" data-tab="pending">Pending</button>
              <button class="fa-status-tab" data-tab="reached">Reached</button>
              <button class="fa-status-tab" data-tab="completed">Completed</button>
            </div>

            ${this.isManagerOrLead ? `
              <label class="fa-team-view-label">
                <input type="checkbox" id="fa-team-toggle" class="fa-team-view-checkbox">
                <span>Team View</span>
              </label>
            ` : ''}
          </div>
        </div>

        <!-- Appointments Feed Container -->
        <div class="fa-feed" id="appointments-feed">
          <div class="fa-loading-box">
            <div class="fa-spinner"></div>
            <span style="font-size: 12px;">Loading field appointments...</span>
          </div>
        </div>

        <!-- Completion Modal Mount -->
        <div id="completion-modal-mount"></div>
      </div>
    `;

    PageHeader.attachListeners({ title: 'Field Appointments', showBack: true });
    this.bindEvents();
  }

  private bindEvents(): void {
    // Period pill buttons
    this.container.querySelectorAll('.fa-period-pill').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const period = (e.currentTarget as HTMLElement).getAttribute('data-period') || 'all';
        this.currentPeriod = period;
        this.container.querySelectorAll('.fa-period-pill').forEach(b => b.classList.remove('active'));
        (e.currentTarget as HTMLElement).classList.add('active');
        this.fetchAppointments();
      });
    });

    // Status tab buttons
    this.container.querySelectorAll('.fa-status-tab').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const tab = (e.currentTarget as HTMLElement).getAttribute('data-tab') || 'all';
        this.currentStatusTab = tab;
        this.container.querySelectorAll('.fa-status-tab').forEach(b => b.classList.remove('active'));
        (e.currentTarget as HTMLElement).classList.add('active');
        this.renderAppointments();
      });
    });

    // Search input
    const searchInput = this.container.querySelector('#fa-search-input') as HTMLInputElement;
    if (searchInput) {
      let st: any = null;
      searchInput.addEventListener('input', () => {
        clearTimeout(st);
        st = setTimeout(() => {
          this.searchQuery = searchInput.value.trim().toLowerCase();
          this.renderAppointments();
        }, 300);
      });
    }

    // Team view toggle
    const teamToggle = this.container.querySelector('#fa-team-toggle') as HTMLInputElement;
    if (teamToggle) {
      teamToggle.addEventListener('change', () => {
        this.viewAllTeam = teamToggle.checked;
        this.fetchAppointments();
      });
    }
  }

  private async fetchAppointments(): Promise<void> {
    this.isLoading = true;
    const feed = this.container.querySelector('#appointments-feed');
    if (feed) {
      feed.innerHTML = `
        <div class="fa-loading-box">
          <div class="fa-spinner"></div>
          <span style="font-size: 12px;">Fetching appointments...</span>
        </div>
      `;
    }

    try {
      const params = new URLSearchParams();
      params.set('filter_period', this.currentPeriod);
      if (this.viewAllTeam) params.set('view_all', 'true');

      const res = await apiService.get<any>(`/crm/field-appointments/my-assigned?${params.toString()}`);
      if (res && res.success !== false) {
        const rawData = res.data;
        if (Array.isArray(rawData)) {
          this.appointments = rawData;
        } else if (rawData && Array.isArray(rawData.appointments)) {
          this.appointments = rawData.appointments;
          this.metrics = rawData.metrics || {};
        } else if (rawData && Array.isArray(rawData.data)) {
          this.appointments = rawData.data;
          this.metrics = rawData.metrics || {};
        } else {
          this.appointments = [];
        }

        if (res.metrics) {
          this.metrics = res.metrics;
        }
        if (rawData && rawData.metrics && (!this.metrics || Object.keys(this.metrics).length === 0)) {
          this.metrics = rawData.metrics;
        }

        this.updateMetricsDisplay();
        this.renderAppointments();
      } else {
        throw new Error(res?.error || res?.detail || 'Failed to load appointments');
      }
    } catch (err: any) {
      if (feed) {
        feed.innerHTML = `
          <div class="fa-error-card">
            <div style="font-size: 22px;">⚠️</div>
            <div style="font-weight: 700; font-size: 14px;">Failed to load appointments</div>
            <div style="font-size: 11.5px; opacity: 0.9; line-height: 1.3;">${err.message || 'Unable to fetch appointments. Please check connection.'}</div>
            <button class="fa-retry-btn" id="retry-btn">Retry</button>
          </div>
        `;
        feed.querySelector('#retry-btn')?.addEventListener('click', () => this.fetchAppointments());
      }
    } finally {
      this.isLoading = false;
    }
  }

  private updateMetricsDisplay(): void {
    const mTotal = this.container.querySelector('#m-total');
    const mComp = this.container.querySelector('#m-completed');
    const mOnTime = this.container.querySelector('#m-ontime');
    const mOnTimePct = this.container.querySelector('#m-ontime-pct');

    if (mTotal) mTotal.textContent = String(this.metrics.total_appointments || 0);
    if (mComp) mComp.textContent = String(this.metrics.visited_completed || 0);
    if (mOnTime) mOnTime.textContent = String(this.metrics.visited_on_time || 0);
    if (mOnTimePct) mOnTimePct.textContent = `${this.metrics.on_time_pct || 0}%`;
  }

  private renderAppointments(): void {
    const feed = this.container.querySelector('#appointments-feed');
    if (!feed) return;

    let filtered = this.appointments;

    // Filter by status tab
    if (this.currentStatusTab === 'pending') {
      filtered = filtered.filter(a => ['assigned', 'accepted', 'in_progress'].includes(a.status));
    } else if (this.currentStatusTab === 'reached') {
      filtered = filtered.filter(a => a.status === 'reached');
    } else if (this.currentStatusTab === 'completed') {
      filtered = filtered.filter(a => a.status === 'completed');
    }

    // Filter by search query
    if (this.searchQuery) {
      const q = this.searchQuery;
      filtered = filtered.filter(a => {
        return (
          a.appointment_code.toLowerCase().includes(q) ||
          (a.lead?.name || '').toLowerCase().includes(q) ||
          (a.lead?.phone || '').includes(q) ||
          (a.bank_name || '').toLowerCase().includes(q) ||
          (a.customer_address || '').toLowerCase().includes(q) ||
          (a.other_location_title || '').toLowerCase().includes(q) ||
          (a.assigned_to?.full_name || '').toLowerCase().includes(q)
        );
      });
    }

    if (filtered.length === 0) {
      feed.innerHTML = `
        <div class="fa-empty-box">
          <div style="font-size: 32px;">📋</div>
          <span style="font-weight: 700; color: #cbd5e1; font-size: 14px;">No field appointments found</span>
          <span style="font-size: 11.5px; color: #64748b;">Try switching period or status filters</span>
        </div>
      `;
      return;
    }

    feed.innerHTML = filtered.map(apt => this.renderAppointmentCard(apt)).join('');
    this.bindCardActions();
  }

  private renderAppointmentCard(apt: FieldAppointmentItem): string {
    // Visit type pill
    let typeBadge = '';
    let destTitle = '';
    let destSubtitle = '';
    let mapsUrl = '';

    if (apt.visit_type === 'visit_bank') {
      typeBadge = '<span class="fa-type-badge bank">🏦 Option 1: Bank</span>';
      destTitle = apt.bank_name || 'Bank Visit';
      destSubtitle = [apt.bank_branch, apt.bank_address, apt.bank_contact_person ? `Contact: ${apt.bank_contact_person}` : ''].filter(Boolean).join(' • ');
      mapsUrl = apt.bank_google_maps_url || '';
    } else if (apt.visit_type === 'visit_customer') {
      typeBadge = '<span class="fa-type-badge customer">👤 Option 2: Customer</span>';
      destTitle = apt.customer_address || 'Customer Location';
      destSubtitle = [apt.customer_area, apt.customer_city, apt.customer_pincode].filter(Boolean).join(', ');
      mapsUrl = apt.customer_google_maps_url || '';
    } else {
      typeBadge = '<span class="fa-type-badge other">🏢 Option 3: Other</span>';
      destTitle = apt.other_location_title || 'Other Official Visit';
      destSubtitle = [apt.other_location_address, apt.other_contact_person ? `Contact: ${apt.other_contact_person}` : ''].filter(Boolean).join(' • ');
      mapsUrl = apt.other_google_maps_url || '';
    }

    // Status pill
    const statusMap: Record<string, { label: string; cls: string }> = {
      assigned: { label: 'Assigned', cls: 'assigned' },
      accepted: { label: 'Accepted', cls: 'accepted' },
      in_progress: { label: 'In Progress', cls: 'in_progress' },
      reached: { label: 'Reached Location', cls: 'reached' },
      completed: { label: 'Completed', cls: 'completed' },
      rescheduled: { label: 'Rescheduled', cls: 'rescheduled' },
      unable_to_visit: { label: 'Unable to Visit', cls: 'unable_to_visit' },
      cancelled: { label: 'Cancelled', cls: 'cancelled' }
    };
    const sInfo = statusMap[apt.status] || { label: apt.status, cls: 'cancelled' };

    // Lead name & phone
    const leadName = apt.lead?.name || `Lead #${apt.lead_id}`;
    const rawPhone = apt.lead?.phone || '';
    const cleanPhone = rawPhone.replace(/\D/g, '').slice(-10);

    // Timing
    const apptDate = apt.appointment_date;
    const prefTime = apt.preferred_time || 'Anytime';

    // Verification badges for completed appointments
    let proofBadges = '';
    if (apt.status === 'completed') {
      const gpsBadge = apt.is_gps_verified 
        ? '<span class="fa-proof-tag ok">📡 GPS OK</span>'
        : '<span class="fa-proof-tag muted">No GPS</span>';

      const onTimeBadge = apt.visited_on_time === true
        ? '<span class="fa-proof-tag ok">⏱️ On-Time</span>'
        : '<span class="fa-proof-tag warn">⏱️ Delayed</span>';

      proofBadges = `<div class="fa-proof-row">${gpsBadge} ${onTimeBadge}</div>`;
    }

    // Reached badge
    let reachedLine = '';
    if (apt.reached_at) {
      const rTime = new Date(apt.reached_at).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
      reachedLine = `<div style="font-size: 11.5px; color: #d8b4fe; font-weight: 600;">📍 Reached at ${rTime} (GPS recorded)</div>`;
    }

    // Workflow action buttons based on status
    let actionButtons = '';
    if (apt.status === 'assigned') {
      actionButtons = `
        <button class="fa-wf-btn accept btn-accept" data-id="${apt.id}">
          ✓ Accept Appointment
        </button>
      `;
    } else if (apt.status === 'accepted') {
      actionButtons = `
        <button class="fa-wf-btn start btn-start" data-id="${apt.id}">
          🚀 Start Visit
        </button>
      `;
    } else if (apt.status === 'in_progress') {
      actionButtons = `
        <button class="fa-wf-btn reached btn-reached" data-id="${apt.id}">
          📍 Mark Reached (GPS)
        </button>
        <button class="fa-wf-btn complete btn-complete" data-id="${apt.id}">
          📸 Complete Visit
        </button>
      `;
    } else if (apt.status === 'reached') {
      actionButtons = `
        <button class="fa-wf-btn complete btn-complete" style="width: 100%;" data-id="${apt.id}">
          📸 Upload Photo &amp; Complete Visit
        </button>
      `;
    }

    // Photo proof preview if completed
    let photoBlock = '';
    const pUrl = apt.photo_url || apt.photo_path;
    if (pUrl && apt.status === 'completed') {
      photoBlock = `
        <div class="fa-photo-preview-strip">
          <div style="display: flex; align-items: center; gap: 8px;">
            <img src="${pUrl}" class="fa-photo-thumb btn-view-photo" data-url="${pUrl}" alt="Proof">
            <div style="font-size: 11px; color: #94a3b8;">
              <div style="font-weight: 700; color: #f1f5f9;">Visit Proof Captured</div>
              <div>${apt.outcome_status ? apt.outcome_status.toUpperCase() : 'Completed'}</div>
            </div>
          </div>
          <button style="background: none; border: none; font-size: 12px; color: #34d399; font-weight: 700; cursor: pointer;" class="btn-view-photo" data-url="${pUrl}">View ↗</button>
        </div>
      `;
    }

    return `
      <div class="fa-card">
        <!-- Top row: Type, Code & Status -->
        <div class="fa-card-top">
          <div class="fa-badge-code-wrap">
            ${typeBadge}
            <span class="fa-code">${apt.appointment_code}</span>
          </div>
          <span class="fa-status-pill ${sInfo.cls}">${sInfo.label}</span>
        </div>

        <!-- Lead & Contact -->
        <div class="fa-card-lead">
          <div>
            <div class="fa-lead-name">${leadName}</div>
            <div class="fa-lead-phone">${rawPhone ? '📞 ' + rawPhone : 'No phone'}</div>
          </div>
          <div class="fa-lead-actions">
            ${cleanPhone ? `
              <a href="tel:${cleanPhone}" class="fa-action-btn-circle call" title="Call">
                📞
              </a>
              <button class="fa-action-btn-circle wa btn-wa" data-phone="${cleanPhone}" data-name="${leadName.replace(/"/g, '&quot;')}" data-id="${apt.lead_id}" title="WhatsApp">
                💬
              </button>
            ` : ''}
            ${mapsUrl ? `
              <a href="${mapsUrl}" target="_system" class="fa-action-btn-circle maps" title="Google Maps">
                🗺️
              </a>
            ` : ''}
          </div>
        </div>

        <!-- Destination Details -->
        <div class="fa-dest-box">
          <div class="fa-dest-title">${destTitle}</div>
          <div class="fa-dest-sub">${destSubtitle}</div>
          ${apt.purpose ? `<div class="fa-dest-purpose"><b>Purpose:</b> ${apt.purpose}</div>` : ''}
          ${apt.telecaller_instructions ? `<div class="fa-dest-instructions"><b>Instructions:</b> ${apt.telecaller_instructions}</div>` : ''}
        </div>

        <!-- Schedule & Assignee -->
        <div class="fa-meta-row">
          <div>📅 <b>${apptDate}</b> (${prefTime})</div>
          <div>👤 ${apt.assigned_to ? apt.assigned_to.full_name : 'Staff #' + apt.assigned_to_id}</div>
        </div>

        ${reachedLine}
        ${proofBadges}
        ${photoBlock}

        <!-- Action Buttons -->
        ${actionButtons ? `<div class="fa-workflow-actions">${actionButtons}</div>` : ''}
      </div>
    `;
  }

  private bindCardActions(): void {
    const feed = this.container.querySelector('#appointments-feed');
    if (!feed) return;

    // Accept
    feed.querySelectorAll('.btn-accept').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        const id = parseInt((e.currentTarget as HTMLElement).getAttribute('data-id') || '0');
        await this.handleStatusUpdate(id, 'accept', btn as HTMLButtonElement);
      });
    });

    // Start visit
    feed.querySelectorAll('.btn-start').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        const id = parseInt((e.currentTarget as HTMLElement).getAttribute('data-id') || '0');
        await this.handleStatusUpdate(id, 'start_visit', btn as HTMLButtonElement);
      });
    });

    // Mark reached (captures GPS)
    feed.querySelectorAll('.btn-reached').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        const id = parseInt((e.currentTarget as HTMLElement).getAttribute('data-id') || '0');
        await this.handleMarkReached(id, btn as HTMLButtonElement);
      });
    });

    // Complete visit (opens modal)
    feed.querySelectorAll('.btn-complete').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const id = parseInt((e.currentTarget as HTMLElement).getAttribute('data-id') || '0');
        const apt = this.appointments.find(a => a.id === id);
        if (apt) {
          this.openCompletionModal(apt);
        }
      });
    });

    // WhatsApp modal trigger
    feed.querySelectorAll('.btn-wa').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const el = e.currentTarget as HTMLElement;
        const phone = el.getAttribute('data-phone') || '';
        const name = el.getAttribute('data-name') || '';
        const id = parseInt(el.getAttribute('data-id') || '0');
        unifiedWAModal.open({
          leadId: id,
          name: name,
          phone: phone
        });
      });
    });

    // View photo in browser / new tab
    feed.querySelectorAll('.btn-view-photo').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const url = (e.currentTarget as HTMLElement).getAttribute('data-url');
        if (url) window.open(url, '_blank');
      });
    });
  }

  private async handleStatusUpdate(aptId: number, action: string, btn: HTMLButtonElement): Promise<void> {
    const origText = btn.textContent || '';
    btn.disabled = true;
    btn.textContent = 'Updating...';

    try {
      const res = await apiService.post<any>(`/crm/field-appointments/${aptId}/status`, { action });
      if (res && res.success) {
        await this.fetchAppointments();
      } else {
        alert(res?.detail || 'Failed to update status');
      }
    } catch (e: any) {
      alert(e.message || 'Network error');
    } finally {
      btn.disabled = false;
      btn.textContent = origText;
    }
  }

  private async handleMarkReached(aptId: number, btn: HTMLButtonElement): Promise<void> {
    btn.disabled = true;
    btn.textContent = 'Acquiring GPS...';

    let lat: number | undefined;
    let lng: number | undefined;
    let acc: number | undefined;

    try {
      const pos = await Geolocation.getCurrentPosition({
        enableHighAccuracy: true,
        timeout: 10000
      });
      if (pos && pos.coords) {
        lat = pos.coords.latitude;
        lng = pos.coords.longitude;
        acc = pos.coords.accuracy;
      }
    } catch (gpsErr) {
      console.warn('[FieldAppointments] GPS fetch fallback:', gpsErr);
    }

    try {
      btn.textContent = 'Saving...';
      const res = await apiService.post<any>(`/crm/field-appointments/${aptId}/status`, {
        action: 'reached',
        reached_latitude: lat,
        reached_longitude: lng,
        reached_accuracy_meters: acc
      });

      if (res && res.success) {
        await this.fetchAppointments();
      } else {
        alert(res?.detail || 'Failed to record reached status');
      }
    } catch (err: any) {
      alert(err.message || 'Error recording reached status');
    } finally {
      btn.disabled = false;
      btn.textContent = '📍 Mark Reached (GPS)';
    }
  }

  // ===================== COMPLETION MODAL & PROOF =====================

  private openCompletionModal(apt: FieldAppointmentItem): void {
    this.activeApptForCompletion = apt;
    this.capturedPhotoBase64 = null;
    this.capturedCoords = null;

    const mount = this.container.querySelector('#completion-modal-mount');
    if (!mount) return;

    mount.innerHTML = `
      <div class="fa-modal-overlay" id="_famCompModal">
        <div class="fa-modal-card">
          <!-- Modal Header -->
          <div class="fa-modal-header">
            <div>
              <div class="fa-modal-title">
                <span>📸</span> Complete Visit Proof
              </div>
              <div class="fa-modal-subtitle">${apt.appointment_code}</div>
            </div>
            <button class="fa-modal-close close-comp-modal">&times;</button>
          </div>

          <!-- Modal Body -->
          <div class="fa-modal-body">
            <!-- Photo Capture Box -->
            <div>
              <label class="fa-modal-label">
                Take Visit Photo Proof <span style="color: #f43f5e;">*</span>
              </label>
              
              <div id="photo-preview-box" class="fa-photo-capture-box">
                <div style="font-size: 32px;">📷</div>
                <div style="font-size: 13px; font-weight: 700; color: #cbd5e1;">Tap to Capture Photo</div>
                <div style="font-size: 10.5px; color: #64748b;">Back camera with geotag proof</div>
              </div>

              <!-- Fallback file input -->
              <input type="file" id="comp-file-input" accept="image/*" capture="environment" style="display: none;">
            </div>

            <!-- GPS Status Indicator -->
            <div style="background: #0f172a; border: 1px solid #334155; border-radius: 10px; padding: 10px 12px; display: flex; align-items: center; justify-content: space-between;">
              <div style="display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 18px;">📡</span>
                <div>
                  <div style="font-weight: 700; color: #f1f5f9; font-size: 11.5px;">Device GPS Location</div>
                  <div style="font-size: 10.5px; color: #94a3b8;" id="gps-coords-text">Fetching device location...</div>
                </div>
              </div>
              <button style="padding: 5px 10px; background: #334155; border: none; border-radius: 6px; color: #cbd5e1; font-size: 11px; font-weight: 600; cursor: pointer;" id="reacquire-gps-btn">Retry</button>
            </div>

            <!-- Outcome Status Selector -->
            <div>
              <label class="fa-modal-label">
                Visit Outcome Status <span style="color: #f43f5e;">*</span>
              </label>
              <select id="comp-outcome-select" class="fa-select">
                <option value="successful">✅ Visit Successful / Docs Collected</option>
                <option value="follow_up_needed">🔄 Follow-Up Required</option>
                <option value="documents_collected">📑 Documents Collected</option>
                <option value="customer_not_available">⚠️ Customer / Manager Not Available</option>
                <option value="bank_manager_busy">🏦 Bank Manager Busy / Postponed</option>
                <option value="unsuccessful">❌ Unsuccessful</option>
              </select>
            </div>

            <!-- Remarks & Summary -->
            <div>
              <label class="fa-modal-label">
                Outcome Remarks / Notes <span style="color: #f43f5e;">*</span>
              </label>
              <textarea id="comp-summary-input" rows="3" placeholder="Describe the outcome of the visit, persons met, documents received, and next steps..." class="fa-textarea" style="resize: none;"></textarea>
            </div>
          </div>

          <!-- Modal Footer -->
          <div class="fa-modal-footer">
            <button class="fa-cancel-btn close-comp-modal">Cancel</button>
            <button class="fa-submit-btn" id="submit-comp-btn">
              ✓ Submit Completion
            </button>
          </div>
        </div>
      </div>
    `;

    this.bindCompletionModalEvents();
    this.acquireCurrentGps();
  }

  private bindCompletionModalEvents(): void {
    const mount = this.container.querySelector('#completion-modal-mount');
    if (!mount) return;

    // Close buttons
    mount.querySelectorAll('.close-comp-modal').forEach(btn => {
      btn.addEventListener('click', () => {
        mount.innerHTML = '';
      });
    });

    // Photo Box Click -> Camera Service
    const photoBox = mount.querySelector('#photo-preview-box') as HTMLElement;
    const fileInput = mount.querySelector('#comp-file-input') as HTMLInputElement;

    if (photoBox) {
      photoBox.addEventListener('click', async () => {
        try {
          const res = await cameraService.takeDocumentPhoto();
          if (res && res.success && res.base64) {
            this.setPhotoPreview(res.base64);
          } else if (fileInput) {
            // Fallback to web file selector
            fileInput.click();
          }
        } catch (e) {
          if (fileInput) fileInput.click();
        }
      });
    }

    if (fileInput) {
      fileInput.addEventListener('change', async () => {
        if (fileInput.files && fileInput.files[0]) {
          const file = fileInput.files[0];
          const reader = new FileReader();
          reader.onload = (e) => {
            const b64 = e.target?.result as string;
            this.setPhotoPreview(b64);
          };
          reader.readAsDataURL(file);
        }
      });
    }

    // GPS Retry
    const gpsRetry = mount.querySelector('#reacquire-gps-btn');
    if (gpsRetry) {
      gpsRetry.addEventListener('click', () => this.acquireCurrentGps());
    }

    // Submit Completion
    const submitBtn = mount.querySelector('#submit-comp-btn') as HTMLButtonElement;
    if (submitBtn) {
      submitBtn.addEventListener('click', () => this.submitCompletion(submitBtn));
    }
  }

  private setPhotoPreview(b64: string): void {
    this.capturedPhotoBase64 = b64;
    const photoBox = this.container.querySelector('#photo-preview-box');
    if (photoBox) {
      const src = b64.startsWith('data:') ? b64 : `data:image/webp;base64,${b64}`;
      photoBox.innerHTML = `
        <img src="${src}" style="width: 100%; height: 100%; object-fit: cover;">
        <div style="position: absolute; bottom: 8px; right: 8px; background: rgba(0,0,0,0.75); color: #fff; font-size: 10px; padding: 3px 8px; border-radius: 6px; font-weight: 600;">Change Photo</div>
      `;
    }
  }

  private async acquireCurrentGps(): Promise<void> {
    const coordsText = this.container.querySelector('#gps-coords-text') as HTMLElement | null;
    if (coordsText) coordsText.textContent = 'Locating device...';

    try {
      const pos = await Geolocation.getCurrentPosition({
        enableHighAccuracy: true,
        timeout: 10000
      });
      if (pos && pos.coords) {
        this.capturedCoords = {
          lat: pos.coords.latitude,
          lng: pos.coords.longitude,
          accuracy: pos.coords.accuracy
        };
        if (coordsText) {
          coordsText.textContent = `Lat: ${pos.coords.latitude.toFixed(4)}, Lng: ${pos.coords.longitude.toFixed(4)} (~${Math.round(pos.coords.accuracy)}m)`;
          coordsText.style.color = '#34d399';
        }
      }
    } catch (e: any) {
      if (coordsText) {
        coordsText.textContent = 'GPS unverified / Permission denied';
        coordsText.style.color = '#fda4af';
      }
    }
  }

  private async submitCompletion(btn: HTMLButtonElement): Promise<void> {
    if (!this.activeApptForCompletion) return;

    const outcomeSelect = this.container.querySelector('#comp-outcome-select') as HTMLSelectElement;
    const summaryInput = this.container.querySelector('#comp-summary-input') as HTMLTextAreaElement;

    const outcome = outcomeSelect?.value || 'successful';
    const summary = summaryInput?.value.trim() || '';

    if (!summary) {
      alert('Please enter outcome remarks / notes before completing.');
      return;
    }

    if (!this.capturedPhotoBase64) {
      const proceed = confirm('No visit photo was captured. Do you want to submit without a photo proof?');
      if (!proceed) return;
    }

    btn.disabled = true;
    btn.innerHTML = '<span>Uploading Proof...</span>';

    try {
      const formData = new FormData();
      formData.append('outcome_status', outcome);
      formData.append('outcome_summary', summary);

      if (this.capturedCoords) {
        formData.append('latitude', String(this.capturedCoords.lat));
        formData.append('longitude', String(this.capturedCoords.lng));
        formData.append('accuracy', String(this.capturedCoords.accuracy));
      }

      if (this.capturedPhotoBase64) {
        formData.append('photo_data', this.capturedPhotoBase64);
      }

      const res = await apiService.post<any>(
        `/crm/field-appointments/${this.activeApptForCompletion.id}/complete`,
        formData
      );

      if (res && res.success) {
        // Close modal
        const mount = this.container.querySelector('#completion-modal-mount');
        if (mount) mount.innerHTML = '';

        alert(`Appointment ${this.activeApptForCompletion.appointment_code} completed successfully!`);
        await this.fetchAppointments();
      } else {
        alert(res?.detail || 'Failed to complete appointment');
      }
    } catch (err: any) {
      alert(err.message || 'Network error submitting completion');
    } finally {
      btn.disabled = false;
      btn.innerHTML = '<span>✓ Submit Completion</span>';
    }
  }
}
