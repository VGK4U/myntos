/**
 * Staff Call Tracking Page
 * DC Protocol: DC_MOBILE_CALL_TRACKING_001
 *
 * Two-tab layout:
 *   Tab 1 – My Calls  : logged-in user's own call data + last-synced banner
 *   Tab 2 – Team Calls: management overview with per-staff last-synced time
 *
 * Sync bar & progress rendered OUTSIDE the scrollable content zone
 * so they are never wiped by content re-renders.
 */

import { apiService } from '../services/api.service';
import { authService } from '../services/auth.service';
import { PageHeader } from '../components/PageHeader';
import { callSyncService } from '../services/call-sync.service';
import { APP_CONFIG } from '../config/app.config';

interface CallRecord {
  id: number;
  phone_number: string;
  contact_name?: string;
  call_type: string;
  call_datetime: string;
  duration_seconds: number;
  matched_lead_id: number | null;
  matched_lead_name?: string;
  has_recording: boolean;
  recording_id: number | null;
}

interface StaffCallSummary {
  staff_id: number;
  staff_name: string;
  emp_code: string;
  total_calls: number;
  outgoing: number;
  incoming: number;
  missed: number;
  total_duration: number;
  crm_matched: number;
  last_synced_at: string | null;
  call_tracking_enabled: boolean;
}

export class StaffCallTrackingPage {
  private container: HTMLElement;

  private activeTab: 'my' | 'team' = 'my';

  private myRange: string = 'last_7';
  private myDateFrom: string = '';
  private myDateTo: string = '';
  private myPhoneFilter: string = '';
  private myCallType: string = '';
  private myPage: number = 1;
  private myStatsData: any = null;

  private teamRange: string = 'last_7';
  private teamDateFrom: string = '';
  private teamDateTo: string = '';
  private teamPhoneFilter: string = '';
  private teamCallType: string = '';
  private teamStaffId: string = '';
  private teamDashData: any = null;

  private detailStaffId: number | null = null;
  private detailStaffName: string = '';
  private detailPage: number = 1;

  private showSettings: boolean = false;
  private activeAudio: HTMLAudioElement | null = null;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.setupStyles();
    this.render();
    PageHeader.attachListeners({
      title: 'Call Tracking',
      showBack: true,
      rightAction: {
        icon: '<ion-icon name="sync" style="font-size:22px;color:#0ea5e9;"></ion-icon>',
        onClick: () => this.manualSync()
      }
    });
    this.setupTopListeners();
    this.switchTab('my');
  }

  private render(): void {
    this.container.innerHTML = `
      ${PageHeader.render({
        title: 'Call Tracking',
        showBack: true,
        rightAction: {
          icon: '<ion-icon name="sync" style="font-size:22px;color:#0ea5e9;"></ion-icon>',
          onClick: () => this.manualSync()
        }
      })}

      <!-- ===== TOP FIXED SECTION (never overwritten) ===== -->
      <div id="ctTopSection">
        <div id="ctSyncBar" style="margin:8px 12px 0;padding:10px 12px;background:white;border-radius:10px;box-shadow:0 1px 3px rgba(0,0,0,0.08);">
          <div style="display:flex;align-items:center;justify-content:space-between;">
            <div style="display:flex;align-items:center;gap:8px;">
              <ion-icon name="sync-circle" style="font-size:22px;color:#0ea5e9;"></ion-icon>
              <div>
                <div style="font-size:13px;font-weight:600;color:#1f2937;">Auto-Sync</div>
                <div id="ctSyncStatusText" style="font-size:11px;color:#6b7280;">Syncs calls & recordings every 15 min</div>
              </div>
            </div>
            <label style="position:relative;display:inline-block;width:44px;height:24px;cursor:pointer;">
              <input type="checkbox" id="ctMainSyncToggle" style="opacity:0;width:0;height:0;">
              <span id="ctMainToggleSlider" style="position:absolute;inset:0;background:#d1d5db;border-radius:24px;transition:0.3s;"></span>
            </label>
          </div>
        </div>


        <div style="display:flex;margin:8px 12px 0;background:white;border-radius:10px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.08);">
          <button id="tabMyBtn" class="ct-tab-btn ct-tab-active" data-tab="my">
            <ion-icon name="person" style="font-size:14px;"></ion-icon> My Calls
          </button>
          <button id="tabTeamBtn" class="ct-tab-btn" data-tab="team">
            <ion-icon name="people" style="font-size:14px;"></ion-icon> Team Calls
          </button>
        </div>
      </div>

      <!-- ===== SCROLLABLE CONTENT ===== -->
      <div class="page-content" style="overflow-y:auto;">

        <!-- ====== MY CALLS TAB ====== -->
        <div id="ctMyCallsTab">

          <div style="display:flex;gap:8px;margin:10px 12px 0;">
            <button id="ctSettingsToggle" style="flex:1;padding:6px 10px;background:white;border:1px solid #e5e7eb;border-radius:8px;font-size:12px;color:#374151;display:flex;align-items:center;justify-content:center;gap:4px;">
              <ion-icon name="folder-open" style="color:#0ea5e9;"></ion-icon> Recording Folder Settings
            </button>
          </div>

          <div id="ctFolderSettings" style="display:none;margin:10px 12px 0;background:white;border-radius:10px;box-shadow:0 1px 3px rgba(0,0,0,0.08);overflow:hidden;">
            <div style="padding:12px;border-bottom:1px solid #f3f4f6;">
              <div style="display:flex;justify-content:space-between;align-items:center;">
                <div style="font-weight:600;font-size:14px;color:#1f2937;"><ion-icon name="folder-open" style="margin-right:6px;color:#0ea5e9;"></ion-icon>Recording Folders</div>
                <button id="ctCloseSettings" style="background:none;border:none;font-size:18px;color:#6b7280;">&times;</button>
              </div>
              <div style="font-size:11px;color:#9ca3af;margin-top:4px;">Auto-detected and custom folders where call recordings are saved</div>
            </div>
            <div style="padding:12px;">
              <div style="display:flex;gap:8px;margin-bottom:12px;">
                <button id="ctAutoDetectBtn" style="flex:1;padding:8px;background:linear-gradient(135deg,#0ea5e9,#0284c7);color:white;border:none;border-radius:8px;font-size:12px;font-weight:600;display:flex;align-items:center;justify-content:center;gap:6px;">
                  <ion-icon name="search"></ion-icon> Auto-Detect Folders
                </button>
                <button id="ctAddFolderBtn" style="flex:1;padding:8px;background:white;color:#0ea5e9;border:1px solid #0ea5e9;border-radius:8px;font-size:12px;font-weight:600;display:flex;align-items:center;justify-content:center;gap:6px;">
                  <ion-icon name="add-circle"></ion-icon> Add Custom Folder
                </button>
              </div>
              <div id="ctSyncToggle" style="display:flex;align-items:center;justify-content:space-between;padding:10px;background:#f0f9ff;border-radius:8px;margin-bottom:12px;">
                <div>
                  <div style="font-size:13px;font-weight:600;color:#1f2937;">Auto-Sync Recordings</div>
                  <div style="font-size:11px;color:#6b7280;">Automatically upload recordings to server</div>
                </div>
                <label style="position:relative;display:inline-block;width:44px;height:24px;cursor:pointer;">
                  <input type="checkbox" id="ctSyncEnabledToggle" style="opacity:0;width:0;height:0;">
                  <span id="ctToggleSlider" style="position:absolute;inset:0;background:#d1d5db;border-radius:24px;transition:0.3s;"></span>
                </label>
              </div>
              <div id="ctPermissionStatus" style="margin-bottom:12px;"></div>
              <div id="ctDeviceInfoChip"></div>
              <div id="ctDetectedFoldersList"></div>
              <div id="ctCustomFoldersList" style="margin-top:8px;"></div>
            </div>
            <div id="ctFolderScanStatus" style="padding:8px 12px;border-top:1px solid #f3f4f6;font-size:11px;color:#9ca3af;"></div>
          </div>

          <div id="ctMyLastSync" style="display:none;margin:10px 12px 0;padding:8px 12px;background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;display:flex;align-items:center;gap:6px;">
            <ion-icon name="cloud-done" style="color:#059669;font-size:16px;flex-shrink:0;"></ion-icon>
            <div>
              <span id="ctMyLastSyncLabel" style="font-size:12px;font-weight:600;color:#059669;"></span>
            </div>
          </div>

          <div class="ct-filters" style="padding:12px;background:white;border-radius:10px;margin:10px 12px 0;box-shadow:0 1px 3px rgba(0,0,0,0.08);">
            <div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px;" id="ctMyRangeBtns">
              <button class="ct-range-btn" data-range="last_3">Last 3 Days</button>
              <button class="ct-range-btn" data-range="today">Today</button>
              <button class="ct-range-btn" data-range="yesterday">Yesterday</button>
              <button class="ct-range-btn active" data-range="last_7">Last 7 Days</button>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:4px;">
              <input type="date" id="ctMyDateFrom" style="padding:6px 8px;border:1px solid #e5e7eb;border-radius:6px;font-size:13px;">
              <input type="date" id="ctMyDateTo" style="padding:6px 8px;border:1px solid #e5e7eb;border-radius:6px;font-size:13px;">
            </div>
            <div id="ctMyRangeWarn" style="display:none;font-size:11px;color:#d97706;background:#fef3c7;border-radius:4px;padding:3px 8px;margin-bottom:4px;"></div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:8px;">
              <select id="ctMyCallTypeFilter" style="padding:6px 8px;border:1px solid #e5e7eb;border-radius:6px;font-size:13px;">
                <option value="">All Types</option>
                <option value="INCOMING">Incoming</option>
                <option value="OUTGOING">Outgoing</option>
                <option value="MISSED">Missed</option>
              </select>
              <input type="text" id="ctMyPhoneFilter" placeholder="Search phone..." style="padding:6px 8px;border:1px solid #e5e7eb;border-radius:6px;font-size:13px;">
            </div>
            <button id="ctMyApplyBtn" style="width:100%;padding:7px;background:#0ea5e9;color:white;border:none;border-radius:6px;font-size:13px;font-weight:600;">Apply Filter</button>
          </div>

          <div id="ctTrackingSetupBanner" style="display:none;margin:10px 12px 0;padding:12px 14px;background:#f0fdfa;border:1px solid #99f6e4;border-radius:10px;">
            <div style="display:flex;align-items:flex-start;gap:10px;">
              <ion-icon name="shield-checkmark" style="color:#0d9488;font-size:22px;flex-shrink:0;margin-top:1px;"></ion-icon>
              <div>
                <div style="font-size:13px;font-weight:700;color:#0f766e;margin-bottom:3px;">Call Sync Ready to Activate</div>
                <div style="font-size:12px;color:#115e59;line-height:1.5;">Your call activity profile is all set. Once your manager activates call tracking for your account, your calls will auto-sync every 15 minutes.</div>
              </div>
            </div>
          </div>

          <div id="ctMySummaryCards" style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:10px 12px 0;"></div>

          <div id="ctMyCallList" style="background:white;border-radius:10px;margin:10px 12px 12px;box-shadow:0 1px 3px rgba(0,0,0,0.08);overflow:hidden;"></div>

        </div>

        <!-- ====== TEAM CALLS TAB ====== -->
        <div id="ctTeamCallsTab" style="display:none;">

          <div class="ct-filters" style="padding:12px;background:white;border-radius:10px;margin:10px 12px 0;box-shadow:0 1px 3px rgba(0,0,0,0.08);">
            <div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px;" id="ctTeamRangeBtns">
              <button class="ct-range-btn" data-range="last_3">Last 3 Days</button>
              <button class="ct-range-btn" data-range="today">Today</button>
              <button class="ct-range-btn" data-range="yesterday">Yesterday</button>
              <button class="ct-range-btn active" data-range="last_7">Last 7 Days</button>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:8px;">
              <input type="date" id="ctTeamDateFrom" style="padding:6px 8px;border:1px solid #e5e7eb;border-radius:6px;font-size:13px;">
              <input type="date" id="ctTeamDateTo" style="padding:6px 8px;border:1px solid #e5e7eb;border-radius:6px;font-size:13px;">
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:8px;">
              <select id="ctTeamStaffFilter" style="padding:6px 8px;border:1px solid #e5e7eb;border-radius:6px;font-size:13px;">
                <option value="">All Staff</option>
              </select>
              <select id="ctTeamCallTypeFilter" style="padding:6px 8px;border:1px solid #e5e7eb;border-radius:6px;font-size:13px;">
                <option value="">All Types</option>
                <option value="INCOMING">Incoming</option>
                <option value="OUTGOING">Outgoing</option>
                <option value="MISSED">Missed</option>
              </select>
            </div>
            <div style="display:flex;gap:8px;">
              <input type="text" id="ctTeamPhoneFilter" placeholder="Search phone number..." style="flex:1;padding:6px 8px;border:1px solid #e5e7eb;border-radius:6px;font-size:13px;">
              <button id="ctTeamApplyBtn" style="padding:6px 14px;background:#0ea5e9;color:white;border:none;border-radius:6px;font-size:13px;font-weight:600;">Apply</button>
            </div>
          </div>

          <div id="ctTeamSummaryCards" style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:10px 12px 0;"></div>

          <div id="ctStaffTable" style="background:white;border-radius:10px;margin:10px 12px 0;box-shadow:0 1px 3px rgba(0,0,0,0.08);overflow:hidden;"></div>

          <div id="ctCallDetails" style="display:none;background:white;border-radius:10px;margin:10px 12px 12px;box-shadow:0 1px 3px rgba(0,0,0,0.08);overflow:hidden;"></div>

        </div>

      </div>

      <div id="ctAudioPlayer" style="display:none;position:fixed;bottom:60px;left:0;right:0;background:#f0f9ff;padding:8px 12px;border-top:1px solid #e5e7eb;z-index:100;">
        <div style="display:flex;align-items:center;gap:8px;">
          <ion-icon name="headset" style="font-size:20px;color:#0ea5e9;"></ion-icon>
          <audio controls id="ctAudioElement" style="flex:1;height:32px;"></audio>
          <button id="ctCloseAudio" style="background:none;border:none;font-size:18px;color:#6b7280;">&times;</button>
        </div>
      </div>

      <!-- ===== FLOATING SYNC TOAST (always on top, fixed position) ===== -->
      <div id="ctSyncToast" style="display:none;position:fixed;top:64px;left:12px;right:12px;z-index:500;border-radius:12px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.18);">
        <div id="ctToastInner" style="padding:10px 14px;background:#1e293b;display:flex;align-items:center;gap:10px;">
          <div id="ctToastSpinner" style="width:18px;height:18px;border:2px solid rgba(255,255,255,0.3);border-top-color:white;border-radius:50%;animation:ct-spin 0.7s linear infinite;flex-shrink:0;"></div>
          <div style="flex:1;min-width:0;">
            <div id="ctToastTitle" style="font-size:12px;font-weight:700;color:white;line-height:1.3;">Syncing calls...</div>
            <div id="ctToastSub" style="font-size:11px;color:rgba(255,255,255,0.65);margin-top:1px;"></div>
          </div>
          <div id="ctToastElapsed" style="font-size:10px;color:rgba(255,255,255,0.45);flex-shrink:0;"></div>
        </div>
        <div id="ctToastBar" style="height:8px;background:rgba(255,255,255,0.12);position:relative;">
          <div id="ctToastBarFill" style="height:100%;width:0%;background:#38bdf8;transition:width 0.4s ease;border-radius:0 3px 3px 0;"></div>
          <div id="ctToastBarPct" style="position:absolute;right:6px;top:50%;transform:translateY(-50%);font-size:9px;color:rgba(255,255,255,0.55);font-weight:700;line-height:1;">0%</div>
        </div>
      </div>
    `;
  }

  private setupTopListeners(): void {
    const mainToggle = document.getElementById('ctMainSyncToggle') as HTMLInputElement;
    const syncStatusText = document.getElementById('ctSyncStatusText');

    const updateSyncUI = (enabled: boolean) => {
      if (mainToggle) mainToggle.checked = enabled;
      const folderToggle = document.getElementById('ctSyncEnabledToggle') as HTMLInputElement;
      if (folderToggle) folderToggle.checked = enabled;
      if (syncStatusText) {
        syncStatusText.textContent = enabled
          ? 'Active — syncs calls & recordings every 15 min'
          : 'Disabled — tap to enable auto-sync';
        syncStatusText.style.color = enabled ? '#059669' : '#6b7280';
      }
    };
    updateSyncUI(callSyncService.isSyncEnabled());

    if (mainToggle) {
      mainToggle.addEventListener('change', async () => {
        await callSyncService.setSyncEnabled(mainToggle.checked);
        updateSyncUI(mainToggle.checked);
      });
    }

    document.getElementById('tabMyBtn')?.addEventListener('click', () => this.switchTab('my'));
    document.getElementById('tabTeamBtn')?.addEventListener('click', () => this.switchTab('team'));
    document.getElementById('ctCloseAudio')?.addEventListener('click', () => this.closeAudioPlayer());

    document.getElementById('ctSettingsToggle')?.addEventListener('click', () => this.toggleSettings());

    document.getElementById('ctCloseSettings')?.addEventListener('click', () => {
      const panel = document.getElementById('ctFolderSettings');
      if (panel) panel.style.display = 'none';
      this.showSettings = false;
    });

    document.getElementById('ctAutoDetectBtn')?.addEventListener('click', () => this.runAutoDetect());
    document.getElementById('ctAddFolderBtn')?.addEventListener('click', () => this.showAddFolderModal());

    const folderToggle = document.getElementById('ctSyncEnabledToggle') as HTMLInputElement;
    if (folderToggle) {
      folderToggle.addEventListener('change', async () => {
        await callSyncService.setSyncEnabled(folderToggle.checked);
        updateSyncUI(folderToggle.checked);
      });
    }

    document.querySelectorAll('#ctMyRangeBtns .ct-range-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('#ctMyRangeBtns .ct-range-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.myRange = (btn as HTMLElement).dataset.range || 'today';
        const df = document.getElementById('ctMyDateFrom') as HTMLInputElement;
        const dt = document.getElementById('ctMyDateTo') as HTMLInputElement;
        if (df) df.value = '';
        if (dt) dt.value = '';
        this.loadMyCallsTab();
      });
    });

    document.getElementById('ctMyApplyBtn')?.addEventListener('click', () => {
      this.myPage = 1;
      this.loadMyCallsTab();
    });
    document.getElementById('ctMyPhoneFilter')?.addEventListener('keypress', (e: any) => {
      if (e.key === 'Enter') { this.myPage = 1; this.loadMyCallsTab(); }
    });

    document.querySelectorAll('#ctTeamRangeBtns .ct-range-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('#ctTeamRangeBtns .ct-range-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.teamRange = (btn as HTMLElement).dataset.range || 'today';
        const df = document.getElementById('ctTeamDateFrom') as HTMLInputElement;
        const dt = document.getElementById('ctTeamDateTo') as HTMLInputElement;
        if (df) df.value = '';
        if (dt) dt.value = '';
        this.loadTeamCallsTab();
      });
    });

    document.getElementById('ctTeamApplyBtn')?.addEventListener('click', () => this.loadTeamCallsTab());
    document.getElementById('ctTeamPhoneFilter')?.addEventListener('keypress', (e: any) => {
      if (e.key === 'Enter') this.loadTeamCallsTab();
    });
    document.getElementById('ctTeamStaffFilter')?.addEventListener('change', () => this.loadTeamCallsTab());
    document.getElementById('ctTeamCallTypeFilter')?.addEventListener('change', () => this.loadTeamCallsTab());

    (window as any).ctReload = () => {
      if (this.activeTab === 'my') this.loadMyCallsTab();
      else this.loadTeamCallsTab();
    };
  }

  private switchTab(tab: 'my' | 'team'): void {
    this.activeTab = tab;

    const myTab = document.getElementById('ctMyCallsTab');
    const teamTab = document.getElementById('ctTeamCallsTab');
    const myBtn = document.getElementById('tabMyBtn');
    const teamBtn = document.getElementById('tabTeamBtn');

    if (tab === 'my') {
      if (myTab) myTab.style.display = 'block';
      if (teamTab) teamTab.style.display = 'none';
      myBtn?.classList.add('ct-tab-active');
      teamBtn?.classList.remove('ct-tab-active');
      this.loadMyCallsTab();
    } else {
      if (myTab) myTab.style.display = 'none';
      if (teamTab) teamTab.style.display = 'block';
      myBtn?.classList.remove('ct-tab-active');
      teamBtn?.classList.add('ct-tab-active');
      this.loadTeamCallsTab();
    }
  }

  private async loadMyCallsTab(): Promise<void> {
    this.myDateFrom = (document.getElementById('ctMyDateFrom') as HTMLInputElement)?.value || '';
    this.myDateTo = (document.getElementById('ctMyDateTo') as HTMLInputElement)?.value || '';
    this.myPhoneFilter = (document.getElementById('ctMyPhoneFilter') as HTMLInputElement)?.value?.trim() || '';
    this.myCallType = (document.getElementById('ctMyCallTypeFilter') as HTMLSelectElement)?.value || '';

    if (this.myDateFrom && this.myDateTo) {
      const diffMs = new Date(this.myDateTo).getTime() - new Date(this.myDateFrom).getTime();
      const diffDays = Math.round(diffMs / 86400000);
      if (diffDays > 7) {
        const capDate = new Date(new Date(this.myDateFrom).getTime() + 7 * 86400000);
        this.myDateTo = capDate.toISOString().split('T')[0];
        const toInput = document.getElementById('ctMyDateTo') as HTMLInputElement;
        if (toInput) toInput.value = this.myDateTo;
        const warn = document.getElementById('ctMyRangeWarn');
        if (warn) { warn.textContent = 'Max range is 7 days. End date adjusted.'; warn.style.display = 'block'; }
      } else {
        const warn = document.getElementById('ctMyRangeWarn');
        if (warn) warn.style.display = 'none';
      }
    }

    const statsEl = document.getElementById('ctMySummaryCards');
    const listEl = document.getElementById('ctMyCallList');
    const lastSyncEl = document.getElementById('ctMyLastSync');

    if (statsEl) statsEl.innerHTML = '';
    if (lastSyncEl) lastSyncEl.style.display = 'none';
    if (listEl) listEl.innerHTML = this.spinner('Loading your calls...');

    let statsUrl = `/call-tracking/my-stats?`;
    if (this.myDateFrom) statsUrl += `&date_from=${this.myDateFrom}`;
    if (this.myDateTo) statsUrl += `&date_to=${this.myDateTo}`;
    if (!this.myDateFrom && !this.myDateTo && this.myRange) statsUrl += `&quick_range=${this.myRange}`;

    try {
      const statsResp = await apiService.get(statsUrl);
      if (statsResp.success && statsResp.data) {
        this.myStatsData = statsResp.data;
        this.renderMyStats((statsResp.data as any)?.stats);
        this.renderMyLastSync((statsResp.data as any)?.last_sync);
      }
    } catch (_) {}

    await this.loadMyCalls();
  }

  private renderMyLastSync(lastSync: any): void {
    const el = document.getElementById('ctMyLastSync');
    const label = document.getElementById('ctMyLastSyncLabel');
    if (!el || !label) return;

    if (!lastSync || !lastSync.sync_completed_at) {
      el.style.display = 'flex';
      el.style.background = '#fef3c7';
      el.style.borderColor = '#fde68a';
      const icon = el.querySelector('ion-icon');
      if (icon) { icon.setAttribute('name', 'warning'); icon.setAttribute('style', 'color:#d97706;font-size:16px;flex-shrink:0;'); }
      label.style.color = '#d97706';
      label.textContent = 'Never synced — tap the sync icon to upload your calls';
      return;
    }

    el.style.display = 'flex';
    el.style.background = '#f0fdf4';
    el.style.borderColor = '#bbf7d0';
    const icon = el.querySelector('ion-icon');
    if (icon) { icon.setAttribute('name', 'cloud-done'); icon.setAttribute('style', 'color:#059669;font-size:16px;flex-shrink:0;'); }
    label.style.color = '#059669';
    const dt = new Date(lastSync.sync_completed_at);
    label.textContent = `Last Synced: ${this.fmtFullDT(dt)}  ·  ${lastSync.records_synced || 0} calls uploaded`;
  }

  private renderMyStats(stats: any): void {
    const el = document.getElementById('ctMySummaryCards');
    if (!el || !stats) return;
    const dr   = this.myStatsData?.date_range;
    const days = dr ? this.calcDays(dr.from, dr.to) : 1;
    const totalCalls = stats.total_calls || 0;
    const totalSecs  = stats.total_duration_seconds || 0;
    const avgCalls   = (totalCalls / days).toFixed(1);
    const avgSecs    = Math.floor(totalSecs / days);
    el.innerHTML = `
      <div class="ct-stat-card"><div class="ct-stat-val">${totalCalls}</div><div class="ct-stat-lbl">Total Calls</div></div>
      <div class="ct-stat-card"><div class="ct-stat-val ct-stat-val-sm">${this.fmtHoursMin(totalSecs)}</div><div class="ct-stat-lbl">Talk Time</div></div>
      <div class="ct-stat-card"><div class="ct-stat-val">${stats.crm_matched || 0}</div><div class="ct-stat-lbl">CRM Matched</div></div>
      <div class="ct-stat-card"><div class="ct-stat-val">${stats.outgoing || 0}</div><div class="ct-stat-lbl">Outgoing</div></div>
      <div class="ct-stat-card"><div class="ct-stat-val">${stats.incoming || 0}</div><div class="ct-stat-lbl">Incoming</div></div>
      <div class="ct-stat-card"><div class="ct-stat-val" style="color:#dc2626;">${stats.missed || 0}</div><div class="ct-stat-lbl">Missed</div></div>
      <div class="ct-stat-card"><div class="ct-stat-val ct-stat-val-sm">${avgCalls}</div><div class="ct-stat-lbl">Avg Calls/Day</div></div>
      <div class="ct-stat-card"><div class="ct-stat-val ct-stat-val-sm">${this.fmtHoursMin(avgSecs)}</div><div class="ct-stat-lbl">Avg Talk/Day</div></div>
      <div class="ct-stat-card"><div class="ct-stat-val" style="color:#059669;">${stats.vgk_created || 0}</div><div class="ct-stat-lbl">VGK Registered</div></div>
      <div class="ct-stat-card"><div class="ct-stat-val" style="color:#0ea5e9;">${stats.wa_sent || 0}</div><div class="ct-stat-lbl">WA Msgs Sent</div></div>
    `;
  }

  private async loadMyCalls(): Promise<void> {
    const listEl = document.getElementById('ctMyCallList');
    if (!listEl) return;

    const user = authService.getAuthState().user;
    const userId = user?.id || user?.staff_id;
    if (!userId) {
      listEl.innerHTML = '<div style="padding:20px;text-align:center;color:#9ca3af;font-size:13px;">Could not identify current user</div>';
      return;
    }

    listEl.innerHTML = this.spinner('Loading calls...');

    let url = `/call-tracking/staff/${userId}/calls?page=${this.myPage}&per_page=50`;
    if (this.myDateFrom) url += `&date_from=${this.myDateFrom}`;
    if (this.myDateTo) url += `&date_to=${this.myDateTo}`;
    if (!this.myDateFrom && !this.myDateTo && this.myRange) url += `&quick_range=${this.myRange}`;
    if (this.myCallType) url += `&call_type=${this.myCallType}`;
    if (this.myPhoneFilter) url += `&phone_number=${encodeURIComponent(this.myPhoneFilter)}`;

    try {
      const resp = await apiService.get(url);
      if (!resp.success || !resp.data) {
        // DC_CALL_SYNC_AUTH: Auth failure gets actionable fix buttons, not generic retry
        const isAuthErr = resp.error === 'Not authenticated' || (resp as any).status === 401;
        if (isAuthErr) {
          listEl.innerHTML = this._authErrorState();
          this._attachAuthErrorListeners(listEl);
        } else {
          listEl.innerHTML = this.emptyState('Could not load calls', resp.error || 'Please try again');
        }
        return;
      }

      const data = resp.data as any;
      const calls: CallRecord[] = data.calls || [];
      const pagination = data.pagination || { page: 1, pages: 0, total: 0 };

      if (calls.length === 0) {
        listEl.innerHTML = '<div style="padding:30px;text-align:center;color:#9ca3af;"><div style="font-size:36px;margin-bottom:8px;">📞</div><div style="font-size:14px;font-weight:500;">No calls in this period</div><div style="font-size:12px;margin-top:4px;">Try a different date range or sync your calls first</div></div>';
        return;
      }

      const header = `<div style="padding:10px 12px;border-bottom:1px solid #f3f4f6;display:flex;justify-content:space-between;align-items:center;">
        <div style="font-weight:600;font-size:13px;color:#1f2937;"><ion-icon name="call" style="margin-right:4px;color:#0ea5e9;"></ion-icon>My Calls</div>
        <div style="font-size:11px;color:#9ca3af;">${pagination.total} total</div>
      </div>`;

      const rows = calls.map((call, idx) => this.renderCallRow(call, ((this.myPage - 1) * 50) + idx + 1)).join('');

      const paginationBar = pagination.pages > 1 ? `
        <div style="padding:8px 12px;display:flex;justify-content:space-between;align-items:center;border-top:1px solid #f3f4f6;">
          <span style="font-size:11px;color:#9ca3af;">Page ${pagination.page} of ${pagination.pages}</span>
          <div style="display:flex;gap:6px;">
            <button id="ctMyPrev" style="padding:4px 10px;border:1px solid #e5e7eb;border-radius:4px;background:white;font-size:12px;" ${pagination.page <= 1 ? 'disabled' : ''}>&lt; Prev</button>
            <button id="ctMyNext" style="padding:4px 10px;border:1px solid #e5e7eb;border-radius:4px;background:white;font-size:12px;" ${pagination.page >= pagination.pages ? 'disabled' : ''}>Next &gt;</button>
          </div>
        </div>` : '';

      listEl.innerHTML = header + rows + paginationBar;

      listEl.querySelector('#ctMyPrev')?.addEventListener('click', () => {
        if (this.myPage > 1) { this.myPage--; this.loadMyCalls(); }
      });
      listEl.querySelector('#ctMyNext')?.addEventListener('click', () => {
        this.myPage++;
        this.loadMyCalls();
      });

      listEl.querySelectorAll('.ct-play-btn').forEach(btn => {
        btn.addEventListener('click', () => {
          const recId = parseInt((btn as HTMLElement).dataset.recId || '0');
          if (recId) this.playRecording(recId);
        });
      });

      const user2 = authService.getAuthState().user;
      const myId = user2?.id || user2?.staff_id;
      listEl.querySelectorAll('.ct-phone-btn').forEach(btn => {
        btn.addEventListener('click', () => {
          const phone = (btn as HTMLElement).dataset.phone || '';
          if (phone && myId) this.showPhoneCallsModal(phone, myId);
        });
      });

    } catch (err: any) {
      listEl.innerHTML = this.emptyState('Network error', err?.message || 'Check your connection');
    }
  }

  private renderCallRow(call: CallRecord, sno: number): string {
    const dt = new Date(call.call_datetime);
    const isToday = new Date().toDateString() === dt.toDateString();
    const dateStr = isToday ? 'Today' : dt.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' });
    const timeStr = dt.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true });

    let typeBg = '', typeColor = '', typeLabel = '', typeIcon = '';
    switch (call.call_type) {
      case 'OUTGOING': typeBg = '#d1fae5'; typeColor = '#059669'; typeLabel = 'Outgoing'; typeIcon = 'arrow-up-circle'; break;
      case 'INCOMING': typeBg = '#dbeafe'; typeColor = '#2563eb'; typeLabel = 'Incoming'; typeIcon = 'arrow-down-circle'; break;
      case 'MISSED':   typeBg = '#fee2e2'; typeColor = '#dc2626'; typeLabel = 'Missed';   typeIcon = 'close-circle';    break;
      case 'REJECTED': typeBg = '#fef3c7'; typeColor = '#d97706'; typeLabel = 'Rejected'; typeIcon = 'ban';             break;
      default:         typeBg = '#f3f4f6'; typeColor = '#6b7280'; typeLabel = call.call_type; typeIcon = 'call-outline';
    }

    const durationStr = call.duration_seconds > 0 ? this.fmtDuration(call.duration_seconds) : '';

    const listenBtn = (call.has_recording && call.recording_id)
      ? `<button class="ct-play-btn" data-rec-id="${call.recording_id}" style="display:inline-flex;align-items:center;gap:3px;margin-top:5px;padding:3px 8px;background:#f0f9ff;border:1px solid #bae6fd;border-radius:6px;color:#0369a1;font-size:11px;font-weight:600;cursor:pointer;">
          <ion-icon name="play-circle" style="font-size:14px;color:#0369a1;"></ion-icon>Listen
         </button>`
      : '';

    const deviceName = call.contact_name || '';
    const crmName = (call as any).contact_name_crm || (call as any).matched_lead_name || '';
    const displayName = crmName || deviceName;
    const contactNameHtml = displayName
      ? `<div style="font-size:12px;font-weight:600;color:#1f2937;margin-bottom:1px;">${displayName}</div>`
      : '';

    const leadStatus = (call as any).contact_lead_status || (call as any).matched_lead_status || '';
    const isLinkedLead = !!(crmName || (call as any).contact_lead_id || (call as any).matched_lead_id);
    const leadBadge = isLinkedLead
      ? `<span style="font-size:9px;color:#7c3aed;background:#f5f3ff;padding:1px 5px;border-radius:4px;border:1px solid #ddd6fe;display:inline-flex;align-items:center;gap:2px;"><ion-icon name="briefcase" style="font-size:8px;"></ion-icon>Lead${leadStatus ? ' · ' + leadStatus : ''}</span>`
      : (deviceName && !crmName ? `<span style="font-size:9px;color:#6b7280;background:#f3f4f6;padding:1px 5px;border-radius:4px;display:inline-flex;align-items:center;gap:2px;"><ion-icon name="phone-portrait" style="font-size:8px;"></ion-icon>Phone Contact</span>` : '');

    return `<div class="ct-call-row" style="display:flex;align-items:flex-start;padding:10px 12px;border-bottom:1px solid #f3f4f6;gap:10px;">
      <div style="width:38px;height:38px;border-radius:50%;background:${typeBg};display:flex;align-items:center;justify-content:center;flex-shrink:0;margin-top:1px;">
        <ion-icon name="${typeIcon}" style="font-size:20px;color:${typeColor};"></ion-icon>
      </div>
      <div style="flex:1;min-width:0;">
        ${contactNameHtml}
        <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
          <button class="ct-phone-btn" data-phone="${call.phone_number}" style="font-weight:700;font-size:${displayName ? '12' : '14'}px;color:#0ea5e9;background:none;border:none;padding:0;cursor:pointer;text-align:left;text-decoration:underline;text-underline-offset:2px;">${call.phone_number || '-'}</button>
          <span style="font-size:10px;font-weight:600;padding:1px 7px;border-radius:10px;background:${typeBg};color:${typeColor};">${typeLabel}</span>
          ${leadBadge}
        </div>
        <div style="font-size:11px;color:#6b7280;margin-top:3px;display:flex;align-items:center;gap:8px;">
          <span>${dateStr} · ${timeStr}</span>
          ${durationStr ? `<span style="color:#374151;font-weight:600;">${durationStr}</span>` : ''}
        </div>
        ${listenBtn}
      </div>
    </div>`;
  }

  private async showPhoneCallsModal(phone: string, staffId: number): Promise<void> {
    document.getElementById('ctPhoneModal')?.remove();

    const backdrop = document.createElement('div');
    backdrop.id = 'ctPhoneModal';
    backdrop.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.5);z-index:999;display:flex;align-items:flex-end;';

    backdrop.innerHTML = `
      <div style="background:white;border-radius:16px 16px 0 0;width:100%;max-height:82vh;display:flex;flex-direction:column;animation:ct-slide-up 0.25s ease;">
        <div style="padding:12px 16px 10px;border-bottom:1px solid #f3f4f6;display:flex;align-items:center;gap:10px;flex-shrink:0;">
          <div style="width:36px;height:36px;border-radius:50%;background:#dbeafe;display:flex;align-items:center;justify-content:center;flex-shrink:0;">
            <ion-icon name="call" style="font-size:18px;color:#2563eb;"></ion-icon>
          </div>
          <div style="flex:1;min-width:0;">
            <div style="font-weight:700;font-size:15px;color:#1f2937;">${phone}</div>
            <div style="font-size:11px;color:#9ca3af;">All calls from this number</div>
          </div>
          <button id="ctPhoneModalClose" style="width:30px;height:30px;background:#f3f4f6;border:none;border-radius:8px;font-size:16px;color:#6b7280;cursor:pointer;display:flex;align-items:center;justify-content:center;">✕</button>
        </div>
        <div id="ctPhoneModalSummary"></div>
        <div id="ctPhoneModalList" style="overflow-y:auto;flex:1;">
          <div style="padding:24px;text-align:center;color:#9ca3af;">
            <div style="width:24px;height:24px;border:3px solid #e5e7eb;border-top-color:#0ea5e9;border-radius:50%;animation:ct-spin 0.8s linear infinite;margin:0 auto 10px;"></div>
            Loading calls...
          </div>
        </div>
      </div>`;

    document.body.appendChild(backdrop);
    backdrop.addEventListener('click', (e) => { if (e.target === backdrop) backdrop.remove(); });
    document.getElementById('ctPhoneModalClose')?.addEventListener('click', () => backdrop.remove());

    const listDiv = document.getElementById('ctPhoneModalList')!;
    const summaryDiv = document.getElementById('ctPhoneModalSummary')!;

    try {
      const allTimeFrom = new Date();
      allTimeFrom.setFullYear(allTimeFrom.getFullYear() - 3);
      const allTimeDateFrom = allTimeFrom.toISOString().split('T')[0];
      const allTimeDateTo = new Date().toISOString().split('T')[0];
      const url = `/call-tracking/staff/${staffId}/calls?per_page=200&date_from=${allTimeDateFrom}&date_to=${allTimeDateTo}&phone_number=${encodeURIComponent(phone)}`;
      const resp = await apiService.get(url);
      const calls: CallRecord[] = (resp.data as any)?.calls || [];

      if (calls.length === 0) {
        listDiv.innerHTML = '<div style="padding:24px;text-align:center;color:#9ca3af;font-size:13px;">No calls found for this number</div>';
        return;
      }

      const total = (resp.data as any)?.pagination?.total || calls.length;
      const totalDur = calls.reduce((s: number, c: CallRecord) => s + (c.duration_seconds || 0), 0);
      const missed = calls.filter((c: CallRecord) => c.call_type === 'MISSED').length;
      const out    = calls.filter((c: CallRecord) => c.call_type === 'OUTGOING').length;
      const inc    = calls.filter((c: CallRecord) => c.call_type === 'INCOMING').length;

      const crmContactName = calls[0] ? ((calls[0] as any).contact_name_crm || (calls[0] as any).matched_lead_name || '') : '';
      const deviceContactName = calls[0] ? (calls[0].contact_name || '') : '';
      const contactName = crmContactName || deviceContactName;
      const leadLinked = calls.some((c: any) => c.contact_lead_id || c.matched_lead_id);
      const leadStatus = calls[0] ? ((calls[0] as any).contact_lead_status || (calls[0] as any).matched_lead_status || '') : '';
      const nameSource = crmContactName ? 'CRM Lead' : (deviceContactName ? 'Phone Contact' : '');

      summaryDiv.innerHTML = `
        ${contactName ? `<div style="padding:8px 14px;background:#f0f9ff;border-bottom:1px solid #bae6fd;display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
          <ion-icon name="person-circle" style="font-size:18px;color:#0ea5e9;"></ion-icon>
          <span style="font-size:13px;font-weight:700;color:#1f2937;">${contactName}</span>
          ${nameSource ? `<span style="font-size:9px;padding:1px 6px;border-radius:4px;background:${crmContactName ? '#f5f3ff' : '#f3f4f6'};color:${crmContactName ? '#7c3aed' : '#6b7280'};border:1px solid ${crmContactName ? '#ddd6fe' : '#e5e7eb'};font-weight:600;">${nameSource}${leadStatus ? ' · ' + leadStatus : ''}</span>` : ''}
        </div>` : ''}
        ${leadLinked && !contactName ? `<div style="padding:6px 14px;background:#f5f3ff;border-bottom:1px solid #ddd6fe;display:flex;align-items:center;gap:4px;">
          <ion-icon name="briefcase" style="font-size:12px;color:#7c3aed;"></ion-icon>
          <span style="font-size:11px;color:#7c3aed;font-weight:600;">Linked to CRM Lead${leadStatus ? ' · ' + leadStatus : ''}</span>
        </div>` : ''}
        <div style="display:flex;gap:10px;padding:8px 14px;background:#f8fafc;border-bottom:1px solid #f3f4f6;flex-wrap:wrap;flex-shrink:0;">
          <span style="font-size:11px;color:#1f2937;font-weight:700;">${total} calls</span>
          <span style="font-size:11px;color:#059669;font-weight:600;">↑ ${out} Out</span>
          <span style="font-size:11px;color:#2563eb;font-weight:600;">↓ ${inc} In</span>
          <span style="font-size:11px;color:#dc2626;font-weight:600;">${missed} Missed</span>
          ${totalDur > 0 ? `<span style="font-size:11px;color:#374151;font-weight:600;">${this.fmtDuration(totalDur)} talk</span>` : ''}
        </div>`;

      listDiv.innerHTML = calls.map((c, i) => this.renderModalCallRow(c, i + 1)).join('');

      listDiv.querySelectorAll('.ct-play-btn').forEach(btn => {
        btn.addEventListener('click', () => {
          const recId = parseInt((btn as HTMLElement).dataset.recId || '0');
          if (recId) { backdrop.remove(); this.playRecording(recId); }
        });
      });

      listDiv.querySelectorAll('.ct-phone-btn').forEach(btn => {
        (btn as HTMLElement).style.cssText += ';pointer-events:none;text-decoration:none;color:#374151;';
      });

    } catch (e: any) {
      listDiv.innerHTML = `<div style="padding:24px;text-align:center;color:#dc2626;font-size:13px;">Error loading calls: ${e?.message || 'Unknown error'}</div>`;
    }
  }

  private renderModalCallRow(call: CallRecord, sno: number): string {
    const dt = new Date(call.call_datetime);
    const dateStr = dt.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: '2-digit' });
    const timeStr = dt.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true });

    let typeColor = '', typeLabel = '', typeIcon = '';
    switch (call.call_type) {
      case 'OUTGOING': typeColor = '#059669'; typeLabel = 'Outgoing'; typeIcon = 'arrow-up-circle'; break;
      case 'INCOMING': typeColor = '#2563eb'; typeLabel = 'Incoming'; typeIcon = 'arrow-down-circle'; break;
      case 'MISSED':   typeColor = '#dc2626'; typeLabel = 'Missed';   typeIcon = 'close-circle';    break;
      case 'REJECTED': typeColor = '#d97706'; typeLabel = 'Rejected'; typeIcon = 'ban';             break;
      default:         typeColor = '#6b7280'; typeLabel = call.call_type; typeIcon = 'call-outline';
    }

    const durationStr = call.duration_seconds > 0 ? this.fmtDuration(call.duration_seconds) : '-';

    const listenBtn = (call.has_recording && call.recording_id)
      ? `<button class="ct-play-btn" data-rec-id="${call.recording_id}" style="display:inline-flex;align-items:center;gap:2px;padding:2px 6px;background:#f0f9ff;border:1px solid #bae6fd;border-radius:4px;color:#0369a1;font-size:10px;font-weight:600;cursor:pointer;">
          <ion-icon name="play-circle" style="font-size:12px;"></ion-icon>Play
         </button>`
      : '';

    return `<div style="display:flex;align-items:center;padding:8px 14px;border-bottom:1px solid #f3f4f6;gap:8px;">
      <ion-icon name="${typeIcon}" style="font-size:18px;color:${typeColor};flex-shrink:0;"></ion-icon>
      <div style="flex:1;min-width:0;">
        <div style="display:flex;align-items:center;gap:6px;">
          <span style="font-size:11px;font-weight:600;color:${typeColor};">${typeLabel}</span>
          <span style="font-size:10px;color:#6b7280;">${dateStr} · ${timeStr}</span>
        </div>
      </div>
      <div style="text-align:right;flex-shrink:0;">
        <span style="font-size:11px;font-weight:700;color:${call.duration_seconds > 0 ? '#1f2937' : '#9ca3af'};">${durationStr}</span>
        ${listenBtn ? `<div style="margin-top:2px;">${listenBtn}</div>` : ''}
      </div>
    </div>`;
  }

  private async loadTeamCallsTab(): Promise<void> {
    this.teamDateFrom = (document.getElementById('ctTeamDateFrom') as HTMLInputElement)?.value || '';
    this.teamDateTo = (document.getElementById('ctTeamDateTo') as HTMLInputElement)?.value || '';
    this.teamStaffId = (document.getElementById('ctTeamStaffFilter') as HTMLSelectElement)?.value || '';
    this.teamCallType = (document.getElementById('ctTeamCallTypeFilter') as HTMLSelectElement)?.value || '';
    this.teamPhoneFilter = (document.getElementById('ctTeamPhoneFilter') as HTMLInputElement)?.value?.trim() || '';

    const tableDiv = document.getElementById('ctStaffTable');
    const summaryDiv = document.getElementById('ctTeamSummaryCards');
    if (tableDiv) tableDiv.innerHTML = this.spinner('Loading team data...');
    if (summaryDiv) summaryDiv.innerHTML = '';

    let url = `/call-tracking/management/overview?`;
    if (this.teamDateFrom) url += `&date_from=${this.teamDateFrom}`;
    if (this.teamDateTo) url += `&date_to=${this.teamDateTo}`;
    if (!this.teamDateFrom && !this.teamDateTo && this.teamRange) url += `&quick_range=${this.teamRange}`;
    if (this.teamStaffId) url += `&staff_id=${this.teamStaffId}`;
    if (this.teamCallType) url += `&call_type=${this.teamCallType}`;
    if (this.teamPhoneFilter) url += `&phone_number=${encodeURIComponent(this.teamPhoneFilter)}`;

    try {
      const response = await apiService.get(url);
      if (response.success && response.data) {
        this.teamDashData = response.data;
        this.renderTeamSummary();
        this.renderStaffTable();
        this.populateTeamStaffFilter();
      } else {
        // DC_CALL_SYNC_AUTH: Auth failure on team tab also gets actionable fix buttons
        const isAuthErr = response.error === 'Not authenticated' || (response as any).status === 401;
        if (tableDiv) {
          if (isAuthErr) {
            tableDiv.innerHTML = this._authErrorState();
            this._attachAuthErrorListeners(tableDiv);
          } else {
            tableDiv.innerHTML = this.emptyState('Could not load team data', response.error || 'Please try again');
          }
        }
      }
    } catch (err: any) {
      if (tableDiv) tableDiv.innerHTML = this.emptyState('Network error', err?.message || 'Check your connection');
    }
  }

  private renderTeamSummary(): void {
    const o  = this.teamDashData?.overview;
    const el = document.getElementById('ctTeamSummaryCards');
    if (!el || !o) return;
    const dr      = this.teamDashData?.date_range;
    const days    = dr ? this.calcDays(dr.from, dr.to) : 1;
    const totalCalls = o.total_calls || 0;
    const totalSecs  = o.total_duration_seconds || 0;
    const avgCalls   = (totalCalls / days).toFixed(1);
    const avgSecs    = o.avg_daily_talk_time || Math.floor(totalSecs / days);
    el.innerHTML = `
      <div class="ct-stat-card"><div class="ct-stat-val">${totalCalls}</div><div class="ct-stat-lbl">Total Calls</div></div>
      <div class="ct-stat-card"><div class="ct-stat-val ct-stat-val-sm">${this.fmtHoursMin(totalSecs)}</div><div class="ct-stat-lbl">Talk Time</div></div>
      <div class="ct-stat-card"><div class="ct-stat-val">${o.crm_matched || 0}</div><div class="ct-stat-lbl">CRM Matched</div></div>
      <div class="ct-stat-card"><div class="ct-stat-val">${o.outgoing || 0}</div><div class="ct-stat-lbl">Outgoing</div></div>
      <div class="ct-stat-card"><div class="ct-stat-val">${o.incoming || 0}</div><div class="ct-stat-lbl">Incoming</div></div>
      <div class="ct-stat-card"><div class="ct-stat-val" style="color:#dc2626;">${o.missed || 0}</div><div class="ct-stat-lbl">Missed</div></div>
      <div class="ct-stat-card"><div class="ct-stat-val ct-stat-val-sm">${avgCalls}</div><div class="ct-stat-lbl">Avg Calls/Day</div></div>
      <div class="ct-stat-card"><div class="ct-stat-val ct-stat-val-sm">${this.fmtHoursMin(avgSecs)}</div><div class="ct-stat-lbl">Avg Talk/Day</div></div>
    `;
  }

  private renderStaffTable(): void {
    const staff: StaffCallSummary[] = this.teamDashData?.per_staff || [];
    const tableDiv = document.getElementById('ctStaffTable');
    if (!tableDiv) return;

    if (staff.length === 0) {
      tableDiv.innerHTML = '<div style="padding:30px;text-align:center;color:#9ca3af;"><div style="font-size:36px;margin-bottom:8px;">📞</div><div style="font-size:14px;font-weight:500;">No team call data for this period</div><div style="font-size:12px;margin-top:4px;">Try switching to "Last 30 Days" or sync calls first</div></div>';
      return;
    }

    const header = `<div style="padding:12px 12px 8px;border-bottom:1px solid #f3f4f6;display:flex;justify-content:space-between;align-items:center;">
      <div style="font-weight:600;font-size:14px;color:#1f2937;"><ion-icon name="people" style="margin-right:6px;color:#0ea5e9;"></ion-icon>Staff Call Activity</div>
      <div style="font-size:12px;color:#9ca3af;">${staff.length} staff</div>
    </div>`;

    const rows = staff.map(s => {
      const initials = (s.staff_name || '?').split(' ').map((w: string) => w[0]).join('').substring(0, 2).toUpperCase();
      const enabled = s.call_tracking_enabled;

      const syncBadge = s.last_synced_at
        ? `<div style="font-size:10px;color:#059669;margin-top:2px;display:flex;align-items:center;gap:3px;">
            <ion-icon name="cloud-done" style="font-size:10px;"></ion-icon>
            Synced ${this.fmtFullDT(new Date(s.last_synced_at))}
          </div>`
        : `<div style="font-size:10px;color:#9ca3af;margin-top:2px;display:flex;align-items:center;gap:3px;">
            <ion-icon name="cloud-offline" style="font-size:10px;"></ion-icon>
            Never synced
          </div>`;

      const trackingStatus = `
        <div style="display:flex;align-items:center;gap:4px;margin-top:4px;">
          <span style="font-size:10px;color:${enabled ? '#059669' : '#9ca3af'};font-weight:500;">
            <ion-icon name="${enabled ? 'radio-button-on' : 'radio-button-off'}" style="font-size:10px;vertical-align:middle;"></ion-icon>
            Tracking ${enabled ? 'ON' : 'OFF'}
          </span>
        </div>`;

      return `<div class="ct-staff-row">
        <div class="ct-staff-avatar" style="background:${enabled ? '#dbeafe' : '#f3f4f6'};color:${enabled ? '#1d4ed8' : '#9ca3af'};">${initials}</div>
        <div class="ct-staff-info">
          <div class="ct-staff-name">${s.staff_name || '-'}</div>
          <div class="ct-staff-code">${s.emp_code || ''}</div>
          <div class="ct-staff-stats">
            <span class="ct-badge ct-badge-out">${s.outgoing} Out</span>
            <span class="ct-badge ct-badge-in">${s.incoming} In</span>
            <span class="ct-badge ct-badge-miss">${s.missed} Miss</span>
            <span style="color:#6b7280;">${this.fmtHoursMin(s.total_duration)}</span>
          </div>
          ${syncBadge}
          ${trackingStatus}
        </div>
        <div style="text-align:right;flex-shrink:0;">
          <div style="font-weight:700;font-size:16px;color:#1f2937;">${s.total_calls}</div>
          <button class="ct-detail-btn" data-staff-id="${s.staff_id}" data-staff-name="${s.staff_name}" data-emp-code="${s.emp_code}" data-last-synced="${s.last_synced_at || ''}">Details</button>
        </div>
      </div>`;
    }).join('');

    tableDiv.innerHTML = header + rows;

    tableDiv.querySelectorAll('.ct-detail-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const staffId = parseInt((btn as HTMLElement).dataset.staffId || '0');
        const staffName = (btn as HTMLElement).dataset.staffName || '';
        const empCode = (btn as HTMLElement).dataset.empCode || '';
        const lastSynced = (btn as HTMLElement).dataset.lastSynced || '';
        this.openCallDetails(staffId, staffName, empCode, lastSynced);
      });
    });

  }

  private populateTeamStaffFilter(): void {
    const select = document.getElementById('ctTeamStaffFilter') as HTMLSelectElement;
    if (!select || !this.teamDashData?.staff_list) return;
    if (select.options.length > 1) return;
    for (const s of this.teamDashData.staff_list) {
      const opt = document.createElement('option');
      opt.value = s.id;
      opt.textContent = `${s.name} (${s.emp_code})`;
      select.appendChild(opt);
    }
    if (this.teamStaffId) select.value = this.teamStaffId;
  }

  private openCallDetails(staffId: number, staffName: string, empCode: string, lastSyncedAt: string): void {
    this.detailStaffId = staffId;
    this.detailStaffName = `${staffName} (${empCode})`;
    this.detailPage = 1;
    this.loadCallDetails(lastSyncedAt);
  }

  private async loadCallDetails(lastSyncedAt: string = ''): Promise<void> {
    if (!this.detailStaffId) return;

    const section = document.getElementById('ctCallDetails');
    if (!section) return;
    section.style.display = 'block';
    section.innerHTML = this.spinner('Loading calls...');

    const dateFrom = this.teamDateFrom;
    const dateTo = this.teamDateTo;

    let url = `/call-tracking/staff/${this.detailStaffId}/calls?page=${this.detailPage}&per_page=50`;
    if (dateFrom) url += `&date_from=${dateFrom}`;
    if (dateTo) url += `&date_to=${dateTo}`;
    if (!dateFrom && !dateTo && this.teamRange) url += `&quick_range=${this.teamRange}`;

    const response = await apiService.get(url);
    if (!response.success || !response.data) {
      section.innerHTML = '<div style="padding:20px;text-align:center;color:#dc2626;">Error loading call details</div>';
      return;
    }

    const data = response.data as any;
    const calls: CallRecord[] = data.calls || [];
    const pagination = data.pagination || { page: 1, pages: 0, total: 0 };

    const syncBanner = lastSyncedAt
      ? `<div style="display:flex;align-items:center;gap:6px;padding:6px 12px;background:#f0fdf4;border-bottom:1px solid #bbf7d0;">
          <ion-icon name="cloud-done" style="color:#059669;font-size:13px;"></ion-icon>
          <span style="font-size:11px;color:#059669;font-weight:600;">Last Synced: ${this.fmtFullDT(new Date(lastSyncedAt))}</span>
        </div>`
      : `<div style="display:flex;align-items:center;gap:6px;padding:6px 12px;background:#fef3c7;border-bottom:1px solid #fde68a;">
          <ion-icon name="warning" style="color:#d97706;font-size:13px;"></ion-icon>
          <span style="font-size:11px;color:#d97706;font-weight:600;">This staff member has never synced their calls</span>
        </div>`;

    const header = `<div style="padding:10px 12px;border-bottom:1px solid #f3f4f6;display:flex;justify-content:space-between;align-items:center;">
      <div style="font-weight:600;font-size:13px;color:#1f2937;"><ion-icon name="list" style="margin-right:4px;"></ion-icon>${this.detailStaffName}</div>
      <button id="ctCloseDetails" style="background:none;border:none;font-size:18px;color:#6b7280;">&times;</button>
    </div>
    ${syncBanner}`;

    if (calls.length === 0) {
      section.innerHTML = header + '<div style="padding:20px;text-align:center;color:#9ca3af;">No call records found</div>';
    } else {
      const rows = calls.map((call, idx) => this.renderCallRow(call, ((this.detailPage - 1) * 50) + idx + 1)).join('');

      const paginationBar = `<div style="padding:8px 12px;display:flex;justify-content:space-between;align-items:center;border-top:1px solid #f3f4f6;">
        <span style="font-size:11px;color:#9ca3af;">Page ${pagination.page} of ${pagination.pages} (${pagination.total})</span>
        <div style="display:flex;gap:6px;">
          <button id="ctDetailPrev" style="padding:4px 10px;border:1px solid #e5e7eb;border-radius:4px;background:white;font-size:12px;" ${pagination.page <= 1 ? 'disabled' : ''}>&lt; Prev</button>
          <button id="ctDetailNext" style="padding:4px 10px;border:1px solid #e5e7eb;border-radius:4px;background:white;font-size:12px;" ${pagination.page >= pagination.pages ? 'disabled' : ''}>Next &gt;</button>
        </div>
      </div>`;

      section.innerHTML = header + rows + paginationBar;
    }

    section.querySelector('#ctCloseDetails')?.addEventListener('click', () => {
      section.style.display = 'none';
      this.detailStaffId = null;
      this.closeAudioPlayer();
    });
    section.querySelector('#ctDetailPrev')?.addEventListener('click', () => {
      if (this.detailPage > 1) { this.detailPage--; this.loadCallDetails(lastSyncedAt); }
    });
    section.querySelector('#ctDetailNext')?.addEventListener('click', () => {
      this.detailPage++;
      this.loadCallDetails(lastSyncedAt);
    });
    section.querySelectorAll('.ct-play-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const recId = parseInt((btn as HTMLElement).dataset.recId || '0');
        if (recId) this.playRecording(recId);
      });
    });

    const detailId = this.detailStaffId;
    if (detailId) {
      section.querySelectorAll('.ct-phone-btn').forEach(btn => {
        btn.addEventListener('click', () => {
          const phone = (btn as HTMLElement).dataset.phone || '';
          if (phone) this.showPhoneCallsModal(phone, detailId);
        });
      });
    }

    section.scrollIntoView({ behavior: 'smooth' });
  }

  private toggleSettings(): void {
    const panel = document.getElementById('ctFolderSettings');
    if (!panel) return;
    this.showSettings = !this.showSettings;
    panel.style.display = this.showSettings ? 'block' : 'none';
    if (this.showSettings) {
      this.renderPermissionStatus();
      this.renderFoldersList();
      this.renderFolderStatus();
      this.renderDeviceInfo();
    }
  }

  private async renderDeviceInfo(): Promise<void> {
    const chip = document.getElementById('ctDeviceInfoChip');
    if (!chip) return;
    chip.innerHTML = '<div style="font-size:11px;color:#9ca3af;margin-bottom:8px;">Detecting device...</div>';
    try {
      const { Device } = await import('@capacitor/device');
      const info = await Device.getInfo();
      const mfr = info.manufacturer || 'Unknown';
      const model = info.model || '';
      const osVer = info.osVersion || '';
      chip.innerHTML = `
        <div style="display:flex;align-items:center;gap:6px;padding:7px 10px;background:#f0f9ff;border:1px solid #bae6fd;border-radius:7px;margin-bottom:10px;">
          <span style="font-size:15px;">📱</span>
          <div>
            <div style="font-size:12px;font-weight:600;color:#0369a1;">${mfr} ${model}</div>
            <div style="font-size:10px;color:#7dd3fc;">Android ${osVer} &bull; Paths for <strong>${mfr}</strong> are shown first</div>
          </div>
        </div>`;
    } catch (_) {
      chip.innerHTML = '';
    }
  }

  private async renderPermissionStatus(): Promise<void> {
    const container = document.getElementById('ctPermissionStatus');
    if (!container) return;
    const perms = await callSyncService.getPermissionStatuses();
    const permItem = (label: string, status: string) => {
      const isGranted = status === 'granted';
      const icon = isGranted ? 'checkmark-circle' : (status === 'denied' ? 'close-circle' : 'help-circle');
      const color = isGranted ? '#059669' : (status === 'denied' ? '#dc2626' : '#f59e0b');
      const statusText = isGranted ? 'Granted' : (status === 'denied' ? 'Denied' : 'Not Set');
      return `<div style="display:flex;align-items:center;justify-content:space-between;padding:6px 0;">
        <span style="font-size:12px;color:#374151;">${label}</span>
        <span style="display:flex;align-items:center;gap:4px;font-size:11px;font-weight:600;color:${color};">
          <ion-icon name="${icon}" style="font-size:14px;"></ion-icon>${statusText}
        </span>
      </div>`;
    };
    const allGranted = perms.callLog === 'granted' && perms.storage === 'granted' && perms.phoneState === 'granted';
    container.innerHTML = `
      <div style="background:${allGranted ? '#f0fdf4' : '#fef3c7'};border:1px solid ${allGranted ? '#bbf7d0' : '#fde68a'};border-radius:8px;padding:10px;">
        <div style="font-size:12px;font-weight:600;color:${allGranted ? '#059669' : '#d97706'};margin-bottom:6px;">
          <ion-icon name="${allGranted ? 'shield-checkmark' : 'warning'}" style="margin-right:4px;"></ion-icon>
          ${allGranted ? 'All Permissions Granted' : 'Some Permissions Missing'}
        </div>
        ${permItem('Call Log Access', perms.callLog)}
        ${permItem('Storage / Audio Files', perms.storage)}
        ${permItem('Phone State', perms.phoneState)}
        ${!allGranted ? `<div style="margin-top:8px;"><button id="ctRequestPermsBtn" style="width:100%;padding:8px;background:#f59e0b;color:white;border:none;border-radius:6px;font-size:12px;font-weight:600;">Grant Permissions</button></div>` : ''}
      </div>`;
    if (!allGranted) {
      container.querySelector('#ctRequestPermsBtn')?.addEventListener('click', async () => {
        const btn = document.getElementById('ctRequestPermsBtn') as HTMLButtonElement;
        if (btn) { btn.textContent = 'Requesting...'; btn.disabled = true; }
        await callSyncService.checkPermissions();
        this.renderPermissionStatus();
      });
    }
  }

  private renderFoldersList(): void {
    const detectedList = document.getElementById('ctDetectedFoldersList');
    const customList = document.getElementById('ctCustomFoldersList');
    if (!detectedList || !customList) return;
    const detected = callSyncService.getDetectedFolders();
    const custom = callSyncService.getCustomFolders();
    if (detected.length === 0 && custom.length === 0) {
      detectedList.innerHTML = `<div style="padding:16px;text-align:center;color:#9ca3af;background:#f9fafb;border-radius:8px;">
        <ion-icon name="folder-open-outline" style="font-size:28px;display:block;margin:0 auto 8px;"></ion-icon>
        <div style="font-size:12px;font-weight:500;">No recording folders detected</div>
        <div style="font-size:11px;margin-top:4px;">Tap "Auto-Detect" to scan or add manually</div>
      </div>`;
      customList.innerHTML = '';
      return;
    }
    if (detected.length > 0) {
      detectedList.innerHTML = `
        <div style="font-size:11px;font-weight:600;color:#059669;text-transform:uppercase;margin-bottom:6px;"><ion-icon name="checkmark-circle" style="margin-right:4px;"></ion-icon>Auto-Detected (${detected.length})</div>
        ${detected.map((f: any) => `<div class="ct-folder-item ct-folder-detected">
          <div class="ct-folder-icon"><ion-icon name="folder"></ion-icon></div>
          <div class="ct-folder-info">
            <div class="ct-folder-path">${f.path}</div>
            <div class="ct-folder-meta">${f.brand} &bull; ${f.fileCount} recording${f.fileCount !== 1 ? 's' : ''}</div>
          </div>
          <ion-icon name="checkmark-circle" style="color:#059669;font-size:18px;flex-shrink:0;"></ion-icon>
        </div>`).join('')}`;
    } else {
      detectedList.innerHTML = '';
    }
    if (custom.length > 0) {
      customList.innerHTML = `
        <div style="font-size:11px;font-weight:600;color:#2563eb;text-transform:uppercase;margin-bottom:6px;"><ion-icon name="create" style="margin-right:4px;"></ion-icon>Custom Folders (${custom.length})</div>
        ${custom.map((f: string) => `<div class="ct-folder-item ct-folder-custom">
          <div class="ct-folder-icon"><ion-icon name="folder"></ion-icon></div>
          <div class="ct-folder-info">
            <div class="ct-folder-path">${f}</div>
            <div class="ct-folder-meta">Manually added</div>
          </div>
          <button class="ct-folder-remove" data-folder="${f}"><ion-icon name="trash"></ion-icon></button>
        </div>`).join('')}`;
      customList.querySelectorAll('.ct-folder-remove').forEach(btn => {
        btn.addEventListener('click', async () => {
          const folder = (btn as HTMLElement).dataset.folder || '';
          if (folder && confirm(`Remove folder "${folder}" from sync?`)) {
            await callSyncService.removeCustomFolder(folder);
            this.renderFoldersList();
          }
        });
      });
    } else {
      customList.innerHTML = '';
    }
  }

  private async renderFolderStatus(): Promise<void> {
    const statusDiv = document.getElementById('ctFolderScanStatus');
    if (!statusDiv) return;
    const lastScan = await callSyncService.getLastFolderScanTimestamp();
    const lastSync = await callSyncService.getLastSyncTimestamp();
    const totalFolders = callSyncService.getActiveFolderPaths().length;
    const enabled = callSyncService.isSyncEnabled();
    const parts: string[] = [];
    if (totalFolders > 0) parts.push(`${totalFolders} folder${totalFolders !== 1 ? 's' : ''} active`);
    if (lastScan > 0) parts.push(`Last scan: ${this.fmtFullDT(new Date(lastScan))}`);
    if (lastSync > 0) parts.push(`Last sync: ${this.fmtFullDT(new Date(lastSync))}`);
    parts.push(enabled ? '<span style="color:#059669;">Sync ON</span>' : '<span style="color:#dc2626;">Sync OFF</span>');
    statusDiv.innerHTML = parts.join(' &bull; ');
  }

  private async runAutoDetect(): Promise<void> {
    const btn = document.getElementById('ctAutoDetectBtn');
    if (btn) { btn.innerHTML = '<ion-spinner name="dots" style="width:14px;height:14px;"></ion-spinner> Scanning...'; (btn as HTMLButtonElement).disabled = true; }
    try {
      const detected = await callSyncService.autoDetectFolders();
      this.renderFoldersList();
      this.renderFolderStatus();
      if (detected.length === 0) {
        alert('No recording folders found. Try adding the folder path manually using "Add Custom Folder".');
      } else {
        const brands = [...new Set(detected.map((d: any) => d.brand))].join(', ');
        const totalFiles = detected.reduce((sum: number, d: any) => sum + d.fileCount, 0);
        alert(`Found ${detected.length} folder${detected.length !== 1 ? 's' : ''} with ${totalFiles} recording${totalFiles !== 1 ? 's' : ''}!\n\nDetected: ${brands}`);
      }
    } catch (_) { alert('Could not scan device folders. Make sure storage permission is granted.'); }
    if (btn) { btn.innerHTML = '<ion-icon name="search"></ion-icon> Auto-Detect Folders'; (btn as HTMLButtonElement).disabled = false; }
  }

  private async showAddFolderModal(): Promise<void> {
    document.getElementById('ctFolderPickerModal')?.remove();

    let deviceBrand = '';
    let deviceLabel = '';
    try {
      const { Device } = await import('@capacitor/device');
      const info = await Device.getInfo();
      const mfr = (info.manufacturer || '').toLowerCase();
      if (mfr.includes('samsung')) { deviceBrand = 'Samsung'; deviceLabel = 'Samsung'; }
      else if (mfr.includes('xiaomi') || mfr.includes('redmi') || mfr.includes('poco')) { deviceBrand = 'Xiaomi / Redmi / Poco'; deviceLabel = info.manufacturer || 'Xiaomi'; }
      else if (mfr.includes('oneplus')) { deviceBrand = 'OnePlus'; deviceLabel = 'OnePlus'; }
      else if (mfr.includes('oppo') || mfr.includes('realme')) { deviceBrand = 'Oppo / Realme'; deviceLabel = info.manufacturer || 'Oppo'; }
      else if (mfr.includes('vivo')) { deviceBrand = 'Vivo / iQOO'; deviceLabel = 'Vivo'; }
      else if (mfr.includes('huawei') || mfr.includes('honor')) { deviceBrand = 'Huawei / Honor'; deviceLabel = info.manufacturer || 'Huawei'; }
      else if (mfr.includes('google')) { deviceBrand = 'Google Pixel'; deviceLabel = 'Pixel'; }
      else if (mfr.includes('motorola') || mfr.includes('lenovo')) { deviceBrand = 'Motorola / Lenovo'; deviceLabel = info.manufacturer || 'Motorola'; }
      else if (mfr.includes('asus')) { deviceBrand = 'Asus / ROG'; deviceLabel = 'Asus'; }
      else if (mfr.includes('nokia')) { deviceBrand = 'Nokia'; deviceLabel = 'Nokia'; }
      else if (mfr.includes('infinix') || mfr.includes('tecno') || mfr.includes('itel')) { deviceBrand = 'Infinix / Tecno / itel'; deviceLabel = info.manufacturer || 'Infinix'; }
    } catch (_) {}

    const allBrandPaths = callSyncService.getKnownFoldersByBrand();
    const suggestedPaths: string[] = deviceBrand ? (allBrandPaths[deviceBrand] || []) : [];
    const otherEntries: { brand: string; path: string }[] = [];
    for (const [brand, paths] of Object.entries(allBrandPaths)) {
      if (brand === deviceBrand) continue;
      for (const p of paths) otherEntries.push({ brand, path: p });
    }

    const suggestedHtml = suggestedPaths.length > 0 ? `
      <div style="font-size:11px;font-weight:700;color:#059669;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:8px;">
        Paths for ${deviceLabel}
      </div>
      ${suggestedPaths.map(p => `
        <div class="ct-path-row" data-path="${p}" style="padding:10px 12px;background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;margin-bottom:6px;cursor:pointer;display:flex;align-items:center;justify-content:space-between;">
          <span style="font-size:13px;color:#1f2937;font-family:monospace;">${p}</span>
          <span style="font-size:11px;color:#059669;font-weight:600;flex-shrink:0;margin-left:8px;">Tap to add</span>
        </div>`).join('')}
      <div style="height:1px;background:#f3f4f6;margin:14px 0;"></div>
    ` : '';

    const otherHtml = otherEntries.slice(0, 40).map(({ brand, path: p }) => `
      <div class="ct-path-row" data-path="${p}" style="padding:8px 12px;background:#f9fafb;border:1px solid #f3f4f6;border-radius:6px;margin-bottom:5px;cursor:pointer;">
        <div style="font-size:10px;color:#9ca3af;margin-bottom:1px;">${brand}</div>
        <div style="font-size:12px;color:#374151;font-family:monospace;">${p}</div>
      </div>`).join('');

    const modal = document.createElement('div');
    modal.id = 'ctFolderPickerModal';
    modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.55);z-index:1000;display:flex;align-items:flex-end;';
    modal.innerHTML = `
      <div style="background:white;width:100%;border-radius:16px 16px 0 0;max-height:82vh;display:flex;flex-direction:column;box-shadow:0 -4px 24px rgba(0,0,0,0.18);">
        <div style="padding:14px 16px;border-bottom:1px solid #f3f4f6;display:flex;justify-content:space-between;align-items:center;flex-shrink:0;">
          <div>
            <div style="font-size:15px;font-weight:700;color:#1f2937;">Add Recording Folder</div>
            <div style="font-size:11px;color:#6b7280;margin-top:1px;">${deviceBrand ? `${deviceLabel} paths shown first` : 'Select a path or type a custom one'}</div>
          </div>
          <button id="ctFolderModalClose" style="background:none;border:none;font-size:24px;color:#9ca3af;line-height:1;cursor:pointer;">&times;</button>
        </div>
        <div style="flex:1;overflow-y:auto;padding:12px;">
          ${suggestedHtml}
          ${otherEntries.length > 0 ? `<div style="font-size:11px;font-weight:700;color:#9ca3af;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:8px;">All Other Known Paths</div>` : ''}
          ${otherHtml}
        </div>
        <div style="padding:12px 12px 20px;border-top:1px solid #f3f4f6;flex-shrink:0;">
          <button id="ctBrowseStorageBtn" style="width:100%;padding:10px;background:#f0f9ff;border:1.5px dashed #0ea5e9;border-radius:8px;color:#0369a1;font-size:13px;font-weight:600;cursor:pointer;margin-bottom:10px;">
            📂 Browse Device Storage
          </button>
          <div style="font-size:11px;color:#6b7280;margin-bottom:6px;">Or type a custom path (relative to internal storage root):</div>
          <div style="display:flex;gap:8px;">
            <input id="ctCustomPathInput" type="text" placeholder="e.g. Recordings/Call" autocomplete="off" autocorrect="off" spellcheck="false"
              style="flex:1;padding:9px 12px;border:1.5px solid #d1d5db;border-radius:8px;font-size:13px;font-family:monospace;outline:none;">
            <button id="ctCustomPathAdd" style="padding:9px 18px;background:#0ea5e9;color:white;border:none;border-radius:8px;font-size:13px;font-weight:600;white-space:nowrap;">Add</button>
          </div>
        </div>
      </div>
    `;
    document.body.appendChild(modal);

    const addPath = async (path: string) => {
      const cleaned = path.trim();
      if (!cleaned) return;
      modal.remove();
      await this.addCustomFolder(cleaned);
    };

    document.getElementById('ctFolderModalClose')?.addEventListener('click', () => modal.remove());
    modal.addEventListener('click', (e) => { if (e.target === modal) modal.remove(); });
    modal.querySelectorAll('.ct-path-row').forEach(row => {
      row.addEventListener('click', () => addPath((row as HTMLElement).dataset.path || ''));
    });
    document.getElementById('ctCustomPathAdd')?.addEventListener('click', () => {
      const input = document.getElementById('ctCustomPathInput') as HTMLInputElement;
      addPath(input?.value || '');
    });
    document.getElementById('ctCustomPathInput')?.addEventListener('keydown', (e) => {
      if ((e as KeyboardEvent).key === 'Enter') {
        const input = document.getElementById('ctCustomPathInput') as HTMLInputElement;
        addPath(input?.value || '');
      }
    });
    document.getElementById('ctBrowseStorageBtn')?.addEventListener('click', () => {
      modal.remove();
      this.showFolderBrowser('', addPath);
    });
  }

  private async showFolderBrowser(currentPath: string, onSelect: (path: string) => void): Promise<void> {
    document.getElementById('ctFolderBrowserModal')?.remove();

    const browserModal = document.createElement('div');
    browserModal.id = 'ctFolderBrowserModal';
    browserModal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.6);z-index:1001;display:flex;align-items:flex-end;';

    const renderBrowser = async (path: string) => {
      let items: { name: string; isDir: boolean }[] = [];
      let errorMsg = '';

      try {
        const Filesystem = (window as any).Capacitor?.Plugins?.Filesystem;
        if (!Filesystem) throw new Error('Filesystem plugin not available');
        const result = await Filesystem.readdir({ path: path || '', directory: 'EXTERNAL_STORAGE' });
        const AUDIO_EXTS = ['.m4a', '.mp3', '.aac', '.ogg', '.wav', '.3gp', '.amr'];
        items = (result.files as any[]).map((f: any) => {
          const name = typeof f === 'string' ? f : (f.name || '');
          const isDir = f.type === 'directory' ||
            (!AUDIO_EXTS.some(ext => name.toLowerCase().endsWith(ext)) && !name.includes('.'));
          return { name, isDir };
        }).sort((a, b) => {
          if (a.isDir !== b.isDir) return a.isDir ? -1 : 1;
          return a.name.localeCompare(b.name);
        });
      } catch (e: any) {
        errorMsg = `Cannot read folder: ${e?.message || 'Permission denied or folder not accessible'}`;
      }

      const breadcrumb = path ? path : '/ (Storage root)';
      const parentPath = path.includes('/') ? path.substring(0, path.lastIndexOf('/')) : '';

      browserModal.innerHTML = `
        <div style="background:white;width:100%;border-radius:16px 16px 0 0;max-height:88vh;display:flex;flex-direction:column;box-shadow:0 -4px 24px rgba(0,0,0,0.2);">
          <div style="padding:12px 14px;border-bottom:1px solid #f3f4f6;flex-shrink:0;">
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px;">
              <div style="font-size:15px;font-weight:700;color:#1f2937;">📂 Browse Storage</div>
              <button id="ctBrowserClose" style="background:none;border:none;font-size:22px;color:#9ca3af;line-height:1;">&times;</button>
            </div>
            <div style="font-size:11px;font-family:monospace;color:#6b7280;word-break:break-all;">${breadcrumb}</div>
            <div style="display:flex;gap:8px;margin-top:8px;">
              ${path ? `<button id="ctBrowserUp" style="flex:1;padding:7px;background:#f9fafb;border:1px solid #e5e7eb;border-radius:6px;font-size:12px;color:#374151;cursor:pointer;">⬆ Up</button>` : ''}
              <button id="ctBrowserSelectBtn" style="flex:2;padding:7px;background:#0ea5e9;color:white;border:none;border-radius:6px;font-size:12px;font-weight:600;cursor:pointer;">✔ Use This Folder</button>
            </div>
          </div>
          <div id="ctBrowserList" style="flex:1;overflow-y:auto;padding:6px 10px;">
            ${errorMsg ? `<div style="padding:20px;text-align:center;color:#dc2626;font-size:13px;">${errorMsg}<br><br><span style="color:#6b7280;font-size:11px;">Try typing the path manually instead</span></div>` :
              items.length === 0 ? '<div style="padding:20px;text-align:center;color:#9ca3af;font-size:13px;">Empty folder</div>' :
              items.map(item => `
                <div class="ct-browser-item" data-name="${item.name}" data-is-dir="${item.isDir}"
                  style="padding:10px 12px;border-bottom:1px solid #f9fafb;cursor:pointer;display:flex;align-items:center;gap:10px;">
                  <span style="font-size:18px;flex-shrink:0;">${item.isDir ? '📁' : '🎵'}</span>
                  <div style="flex:1;min-width:0;">
                    <div style="font-size:13px;color:#1f2937;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${item.name}</div>
                    ${!item.isDir ? '<div style="font-size:10px;color:#0ea5e9;">Audio file</div>' : ''}
                  </div>
                  ${item.isDir ? '<span style="font-size:14px;color:#9ca3af;">›</span>' : ''}
                </div>`).join('')}
          </div>
        </div>`;

      document.getElementById('ctBrowserClose')?.addEventListener('click', () => browserModal.remove());
      document.getElementById('ctBrowserSelectBtn')?.addEventListener('click', () => {
        browserModal.remove();
        onSelect(path);
      });
      document.getElementById('ctBrowserUp')?.addEventListener('click', () => renderBrowser(parentPath));
      browserModal.querySelectorAll('.ct-browser-item').forEach(el => {
        el.addEventListener('click', () => {
          const name = (el as HTMLElement).dataset.name || '';
          const isDir = (el as HTMLElement).dataset.isDir === 'true';
          if (isDir) {
            const newPath = path ? `${path}/${name}` : name;
            renderBrowser(newPath);
          }
        });
      });
    };

    document.body.appendChild(browserModal);
    browserModal.innerHTML = '<div style="background:white;width:100%;border-radius:16px 16px 0 0;padding:30px;text-align:center;color:#6b7280;">Loading storage...</div>';
    await renderBrowser(currentPath);
  }

  private async addCustomFolder(path: string): Promise<void> {
    const added = await callSyncService.addCustomFolder(path);
    if (added) { this.renderFoldersList(); this.renderFolderStatus(); alert(`Folder added: ${path}\n\nRecordings will be synced on next sync.`); }
    else alert('This folder is already in the list.');
  }

  private async manualSync(): Promise<void> {
    const toast     = document.getElementById('ctSyncToast') as HTMLElement | null;
    const toastInner= document.getElementById('ctToastInner') as HTMLElement | null;
    const spinner   = document.getElementById('ctToastSpinner') as HTMLElement | null;
    const title     = document.getElementById('ctToastTitle') as HTMLElement | null;
    const sub       = document.getElementById('ctToastSub') as HTMLElement | null;
    const elapsed   = document.getElementById('ctToastElapsed') as HTMLElement | null;
    const barFill   = document.getElementById('ctToastBarFill') as HTMLElement | null;
    const barPct    = document.getElementById('ctToastBarPct')  as HTMLElement | null;

    const stageWidths: Record<string, number> = { reading: 25, uploading: 60, recordings: 80, done: 100, error: 100 };
    const stageSubs:   Record<string, string>  = { reading: 'Reading call logs from device...', uploading: 'Uploading to server...', recordings: 'Syncing recordings...', done: '', error: '' };

    const setPct = (pct: number) => {
      if (barFill) barFill.style.width = `${pct}%`;
      if (barPct)  barPct.textContent  = `${pct}%`;
    };

    const setToast = (bg: string, barColor: string, spinnerVisible: boolean) => {
      if (toastInner) toastInner.style.background = bg;
      if (barFill)    barFill.style.background = barColor;
      if (spinner)    spinner.style.display = spinnerVisible ? 'block' : 'none';
    };

    const updatePoll = () => {
      const p = callSyncService.getSyncProgress();
      if (!p) return;
      if (title) title.textContent = `Syncing — ${p.detail || 'Please wait...'}`;
      if (sub) {
        const parts: string[] = [];
        if (p.callsFound  !== undefined) parts.push(`Found: ${p.callsFound}`);
        if (p.callsSynced !== undefined) parts.push(`Uploaded: ${p.callsSynced}`);
        if (p.callsMatched!== undefined) parts.push(`CRM: ${p.callsMatched}`);
        sub.textContent = parts.length ? parts.join('  ·  ') : (stageSubs[p.stage] || '');
      }
      setPct(stageWidths[p.stage] || 10);
      const sec = Math.floor((Date.now() - p.startedAt) / 1000);
      if (elapsed) elapsed.textContent = sec > 0 ? `${sec}s` : '';
    };

    if (toast) toast.style.display = 'block';
    setToast('#1e293b', '#38bdf8', true);
    if (title) title.textContent = 'Syncing calls...';
    if (sub)   sub.textContent   = 'Reading call logs from device...';
    setPct(5);

    const pollInterval = setInterval(updatePoll, 350);

    const dismiss = (delay: number) => {
      setTimeout(() => {
        if (toast) {
          toast.style.transition = 'opacity 0.4s';
          toast.style.opacity = '0';
          setTimeout(() => { if (toast) { toast.style.display = 'none'; toast.style.opacity = '1'; toast.style.transition = ''; } }, 420);
        }
      }, delay);
    };

    try {
      const result = await callSyncService.fullSync(true);
      clearInterval(pollInterval);
      updatePoll();

      const calls = result?.calls;
      const recordings = result?.recordings;

      if (calls !== null && calls !== undefined) {
        const recPart = recordings && recordings.uploaded > 0 ? ` · ${recordings.uploaded} rec` : '';
        const summary = calls.synced === 0
          ? 'All up to date — no new calls'
          : `${calls.synced} call${calls.synced !== 1 ? 's' : ''} uploaded · ${calls.matched} CRM${recPart}`;

        setToast('#064e3b', '#34d399', false);
        if (spinner) { spinner.style.display = 'block'; spinner.textContent = '✅'; spinner.style.border = 'none'; spinner.style.animation = 'none'; spinner.style.fontSize = '16px'; spinner.style.width = 'auto'; spinner.style.height = 'auto'; }
        if (title) title.textContent = 'Sync complete';
        if (sub)   sub.textContent   = summary;
        setPct(100);

        this.myPage = 1;
        this.detailPage = 1;
        if (this.activeTab === 'my') this.loadMyCallsTab();
        else this.loadTeamCallsTab();
        dismiss(5000);
      } else {
        const err = callSyncService.getLastSyncError() || 'Sync failed — check permissions';
        setToast('#7f1d1d', '#f87171', false);
        if (spinner) { spinner.style.display = 'block'; spinner.textContent = '❌'; spinner.style.border = 'none'; spinner.style.animation = 'none'; spinner.style.fontSize = '16px'; spinner.style.width = 'auto'; spinner.style.height = 'auto'; }
        if (title) title.textContent = 'Sync failed';
        if (sub)   sub.textContent   = err;
        setPct(100);
        dismiss(7000);
      }
    } catch (e: any) {
      clearInterval(pollInterval);
      const msg = e?.message || 'Unknown error — check permissions';
      setToast('#7f1d1d', '#f87171', false);
      if (toast) toast.style.display = 'block';
      if (spinner) { spinner.style.display = 'block'; spinner.textContent = '❌'; spinner.style.border = 'none'; spinner.style.animation = 'none'; spinner.style.fontSize = '16px'; spinner.style.width = 'auto'; spinner.style.height = 'auto'; }
      if (title) title.textContent = 'Sync failed';
      if (sub)   sub.textContent   = msg;
      if (barFill) barFill.style.background = '#f87171';
      setPct(100);
      dismiss(7000);
    }
  }

  private currentBlobUrl: string | null = null;

  private async playRecording(recordingId: number): Promise<void> {
    const playerDiv = document.getElementById('ctAudioPlayer');
    const audioEl  = document.getElementById('ctAudioElement') as HTMLAudioElement;
    if (!playerDiv || !audioEl) return;

    // Show loading on play button
    const playBtn = document.querySelector(`[data-rec-id="${recordingId}"]`) as HTMLElement | null;
    if (playBtn) playBtn.innerHTML = '<ion-icon name="hourglass" style="font-size:14px;"></ion-icon>';

    // Revoke previous blob URL if any
    if (this.currentBlobUrl) { URL.revokeObjectURL(this.currentBlobUrl); this.currentBlobUrl = null; }

    try {
      const token = await apiService.getToken();
      const baseUrl = apiService.getBaseUrl();
      const url = `${baseUrl}/call-tracking/recordings/${recordingId}/stream`;

      const resp = await fetch(url, {
        headers: token ? { 'Authorization': `Bearer ${token}` } : {}
      });

      if (!resp.ok) {
        const msg = resp.status === 404 ? 'Recording file not found on server'
                  : resp.status === 403 ? 'You do not have access to this recording'
                  : `Could not load recording (${resp.status})`;
        alert(msg);
        if (playBtn) playBtn.innerHTML = '<ion-icon name="play" style="font-size:14px;"></ion-icon>';
        return;
      }

      const blob = await resp.blob();
      this.currentBlobUrl = URL.createObjectURL(blob);

      audioEl.src = this.currentBlobUrl;
      playerDiv.style.display = 'block';

      audioEl.onended = () => {
        if (this.currentBlobUrl) { URL.revokeObjectURL(this.currentBlobUrl); this.currentBlobUrl = null; }
      };

      audioEl.play().catch(() => {});
      this.activeAudio = audioEl;
    } catch (e: any) {
      alert(`Playback error: ${e?.message || 'Unknown error'}`);
    } finally {
      if (playBtn) playBtn.innerHTML = '<ion-icon name="play" style="font-size:14px;"></ion-icon>';
    }
  }

  private closeAudioPlayer(): void {
    const playerDiv = document.getElementById('ctAudioPlayer');
    const audioEl  = document.getElementById('ctAudioElement') as HTMLAudioElement;
    if (audioEl) { audioEl.pause(); audioEl.src = ''; }
    if (this.currentBlobUrl) { URL.revokeObjectURL(this.currentBlobUrl); this.currentBlobUrl = null; }
    if (playerDiv) playerDiv.style.display = 'none';
    this.activeAudio = null;
  }

  private spinner(msg: string): string {
    return `<div style="padding:24px;text-align:center;color:#9ca3af;">
      <div style="width:28px;height:28px;border:3px solid #e5e7eb;border-top-color:#0ea5e9;border-radius:50%;animation:ct-spin 0.8s linear infinite;margin:0 auto 10px;"></div>
      <div style="font-size:13px;">${msg}</div>
    </div>`;
  }

  private emptyState(title: string, sub: string): string {
    return `<div style="padding:24px;text-align:center;">
      <div style="font-size:28px;margin-bottom:8px;">⚠️</div>
      <div style="font-size:13px;color:#dc2626;font-weight:600;">${title}</div>
      <div style="font-size:11px;color:#9ca3af;margin-top:4px;">${sub}</div>
      <button onclick="window.ctReload&&window.ctReload()" style="margin-top:12px;padding:6px 16px;background:#0ea5e9;color:white;border:none;border-radius:6px;font-size:12px;">Retry</button>
    </div>`;
  }

  // DC_CALL_SYNC_AUTH: Actionable error state for auth failures (dev mode or session expired)
  private _authErrorState(): string {
    const isDevMode = APP_CONFIG.isDevMode();
    if (isDevMode) {
      return `<div style="padding:28px 20px;text-align:center;">
        <div style="font-size:32px;margin-bottom:10px;">⚙️</div>
        <div style="font-size:14px;color:#b45309;font-weight:700;">App is in Development Mode</div>
        <div style="font-size:12px;color:#6b7280;margin-top:6px;line-height:1.5;">Your call data is on the production server.<br>Switch to Production to view and sync calls.</div>
        <button id="ct-switch-prod-btn" style="margin-top:14px;padding:9px 22px;background:#059669;color:white;border:none;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;">Switch to Production</button>
      </div>`;
    }
    return `<div style="padding:28px 20px;text-align:center;">
      <div style="font-size:32px;margin-bottom:10px;">🔐</div>
      <div style="font-size:14px;color:#dc2626;font-weight:700;">Session Expired</div>
      <div style="font-size:12px;color:#6b7280;margin-top:6px;line-height:1.5;">Please log out and log in again to continue.</div>
      <button id="ct-relogin-btn" style="margin-top:14px;padding:9px 22px;background:#0ea5e9;color:white;border:none;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;">Log Out & Log In</button>
    </div>`;
  }

  private _attachAuthErrorListeners(container: Element): void {
    container.querySelector('#ct-switch-prod-btn')?.addEventListener('click', () => {
      // Disables dev mode flag and reloads — routes all API calls back to mnrteam.com
      APP_CONFIG.disableDevMode();
    });
    container.querySelector('#ct-relogin-btn')?.addEventListener('click', async () => {
      await authService.logout();
      window.location.reload();
    });
  }

  private fmtDuration(seconds: number): string {
    if (!seconds || seconds <= 0) return '0m';
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    if (h > 0) return `${h}h ${m}m`;
    if (m > 0) return `${m}m ${s}s`;
    return `${s}s`;
  }

  private fmtHoursMin(seconds: number): string {
    if (!seconds || seconds <= 0) return '0h (0m)';
    const totalMinutes = Math.floor(seconds / 60);
    const hours = Math.floor(totalMinutes / 60);
    return `${hours}h (${totalMinutes}m)`;
  }

  private calcDays(fromStr: string, toStr: string): number {
    try {
      const from = new Date(fromStr);
      const to   = new Date(toStr);
      const diff = Math.round((to.getTime() - from.getTime()) / 86400000);
      return Math.max(1, diff + 1);
    } catch { return 1; }
  }

  private fmtFullDT(dt: Date): string {
    const now = new Date();
    const isToday = dt.toDateString() === now.toDateString();
    const time = dt.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
    if (isToday) return `Today ${time}`;
    const date = dt.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: dt.getFullYear() !== now.getFullYear() ? 'numeric' : undefined });
    return `${date} ${time}`;
  }

  private setupStyles(): void {
    if (document.getElementById('ct-page-styles')) return;
    const style = document.createElement('style');
    style.id = 'ct-page-styles';
    style.textContent = `
      .ct-tab-btn {
        flex: 1; padding: 10px 8px; border: none; background: transparent;
        font-size: 13px; font-weight: 600; color: #9ca3af; cursor: pointer;
        display: flex; align-items: center; justify-content: center; gap: 5px;
        border-bottom: 2px solid transparent; transition: all 0.2s;
      }
      .ct-tab-active { color: #0ea5e9 !important; border-bottom-color: #0ea5e9 !important; }
      .ct-range-btn {
        padding: 4px 10px; border-radius: 12px; border: 1px solid #e5e7eb;
        background: white; color: #6b7280; font-size: 11px; font-weight: 500; cursor: pointer;
      }
      .ct-range-btn.active { background: #0ea5e9; border-color: #0ea5e9; color: white; }
      .ct-stat-card {
        background: white; border-radius: 8px; padding: 10px; text-align: center;
        box-shadow: 0 1px 2px rgba(0,0,0,0.06);
      }
      .ct-stat-val { font-size: 20px; font-weight: 700; color: #1f2937; }
      .ct-stat-val-sm { font-size: 14px !important; }
      .ct-stat-lbl { font-size: 10px; color: #9ca3af; text-transform: uppercase; font-weight: 600; margin-top: 2px; }
      .ct-staff-row {
        display: flex; align-items: flex-start; padding: 10px 12px;
        border-bottom: 1px solid #f3f4f6; gap: 10px;
      }
      .ct-staff-row:last-child { border-bottom: none; }
      .ct-staff-avatar {
        width: 32px; height: 32px; border-radius: 50%;
        background: linear-gradient(135deg, #0ea5e9, #0284c7);
        display: flex; align-items: center; justify-content: center;
        color: white; font-size: 11px; font-weight: 700; flex-shrink: 0; margin-top: 2px;
      }
      .ct-staff-info { flex: 1; min-width: 0; }
      .ct-staff-name { font-weight: 600; font-size: 13px; color: #1f2937; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
      .ct-staff-code { font-size: 11px; color: #9ca3af; }
      .ct-staff-stats { display: flex; gap: 6px; font-size: 11px; margin-top: 2px; flex-wrap: wrap; align-items: center; }
      .ct-badge { padding: 1px 6px; border-radius: 4px; font-size: 10px; font-weight: 600; }
      .ct-badge-out { background: #d1fae5; color: #059669; }
      .ct-badge-in { background: #dbeafe; color: #2563eb; }
      .ct-badge-miss { background: #fee2e2; color: #dc2626; }
      .ct-detail-btn {
        padding: 4px 8px; background: #eff6ff; border: 1px solid #bfdbfe;
        border-radius: 6px; color: #2563eb; font-size: 11px; font-weight: 600;
        cursor: pointer; white-space: nowrap; margin-top: 4px;
      }
      .ct-call-row {
        display: flex; align-items: center; padding: 8px 12px;
        border-bottom: 1px solid #f3f4f6; gap: 8px; font-size: 12px;
      }
      .ct-play-btn {
        width: 28px; height: 28px; border-radius: 50%; border: none;
        background: #eff6ff; color: #0ea5e9; display: flex;
        align-items: center; justify-content: center; cursor: pointer; flex-shrink: 0;
      }
      .ct-type-badge { padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: 600; }
      .ct-folder-item {
        display: flex; align-items: center; padding: 8px 10px; gap: 8px;
        background: #f9fafb; border-radius: 8px; margin-bottom: 6px;
      }
      .ct-folder-icon {
        width: 32px; height: 32px; border-radius: 8px;
        display: flex; align-items: center; justify-content: center; flex-shrink: 0; font-size: 16px;
      }
      .ct-folder-detected .ct-folder-icon { background: #d1fae5; color: #059669; }
      .ct-folder-custom .ct-folder-icon { background: #dbeafe; color: #2563eb; }
      .ct-folder-info { flex: 1; min-width: 0; }
      .ct-folder-path { font-size: 12px; font-weight: 600; color: #1f2937; word-break: break-all; }
      .ct-folder-meta { font-size: 10px; color: #9ca3af; margin-top: 2px; }
      .ct-folder-remove { background: none; border: none; color: #dc2626; font-size: 16px; cursor: pointer; padding: 4px; flex-shrink: 0; }
      @keyframes ct-spin { to { transform: rotate(360deg); } }
      @keyframes ct-slide-up { from { transform: translateY(100%); opacity:0; } to { transform: translateY(0); opacity:1; } }
      #ctToggleSlider::after {
        content: ''; position: absolute; width: 18px; height: 18px;
        background: white; border-radius: 50%; top: 3px; left: 3px; transition: 0.3s;
      }
      #ctSyncEnabledToggle:checked + #ctToggleSlider { background: #0ea5e9; }
      #ctSyncEnabledToggle:checked + #ctToggleSlider::after { left: 23px; }
      #ctMainSyncToggle:checked + #ctMainToggleSlider { background: #0ea5e9; }
      #ctMainSyncToggle:checked + #ctMainToggleSlider::after { left: 23px; }
      #ctMainToggleSlider::after {
        content: ''; position: absolute; width: 18px; height: 18px;
        background: white; border-radius: 50%; top: 3px; left: 3px; transition: 0.3s;
      }
    `;
    document.head.appendChild(style);
  }

  destroy(): void {
    this.closeAudioPlayer();
    const style = document.getElementById('ct-page-styles');
    if (style) style.remove();
  }
}
