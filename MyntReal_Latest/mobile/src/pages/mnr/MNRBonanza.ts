/**
 * MNR Bonanza Awards Page - Complete Web Parity
 * DC Protocol: DC_MOBILE_MNR_BONANZA_003
 * Matches web: Requirements section, filters, Active campaigns table, Claimed bonanzas
 */

import { apiService } from '../../services/api.service';
import { PageHeader } from '../../components/PageHeader';
import { MobileTable } from '../../components/MobileTable';

interface BonanzaCampaign {
  id: number;
  name: string;
  campaign_period: string;
  start_date: string | null;
  end_date: string | null;
  criteria: string;
  target: number;
  your_progress: number;
  reward: string;
  status: string;
  can_claim: boolean;
  type: string;
}

interface ClaimedBonanza {
  id: number;
  bonanza_name: string;
  target_achieved: number;
  target_required: number;
  reward: string;
  claimed_date: string | null;
  processed_status: string;
  dispatch_date: string | null;
  received_date: string | null;
}

interface EligibilityStatus {
  is_activated: boolean;
  kyc_status: string;
  program_utilisation_completed: boolean;
  group_a_points: number;
  group_b_points: number;
  is_eligible: boolean;
}

export class MNRBonanza {
  private container: HTMLElement;
  private activeCampaigns: BonanzaCampaign[] = [];
  private claimedBonanzas: ClaimedBonanza[] = [];
  private loading: boolean = true;
  private filters = { search: '', status: 'all', date: 'all', type: 'all' };
  private eligibility: EligibilityStatus | null = null;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadData();
  }

  private async loadData(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      const [bonanzaRes, claimedRes, eligibilityRes] = await Promise.all([
        apiService.get<any>('/bonanza/my-bonanzas'),
        apiService.get<any>('/bonanza/my-claimed'),
        apiService.get<any>('/auth/me-hybrid?role=mnr')
      ]);

      if (bonanzaRes.success && bonanzaRes.data) {
        const bonanzas = bonanzaRes.data.bonanzas || bonanzaRes.data || [];
        this.activeCampaigns = bonanzas.map((b: any) => this.mapCampaign(b));
      }

      if (claimedRes.success && claimedRes.data) {
        const claimed = claimedRes.data.claimed_bonanzas || claimedRes.data || [];
        this.claimedBonanzas = claimed.map((c: any) => this.mapClaimed(c));
      }

      const eligData = eligibilityRes?.data?.eligibility_status || (eligibilityRes as any)?.eligibility_status;
      if (eligData) {
        this.eligibility = {
          is_activated: eligData.is_activated || false,
          kyc_status: eligData.kyc_status || 'pending',
          program_utilisation_completed: eligData.program_utilisation_completed || false,
          group_a_points: eligData.group_a_points || 0,
          group_b_points: eligData.group_b_points || 0,
          is_eligible: eligData.is_eligible || false
        };
      }
    } catch (error) {
      console.error('[MNRBonanza] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private mapCampaign(b: any): BonanzaCampaign {
    const startDate = b.start_date ? new Date(b.start_date).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }) : '';
    const endDate = b.end_date ? new Date(b.end_date).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }) : '';
    
    return {
      id: b.id || 0,
      name: b.bonanza_name || b.name || '',
      campaign_period: `${startDate} - ${endDate}`,
      start_date: b.start_date,
      end_date: b.end_date,
      criteria: b.criteria_description || b.criteria || `${b.target_type || 'Direct'} Activations`,
      target: b.target_value || b.target_requirement || b.target || 0,
      your_progress: b.current_progress || b.current_value || b.progress || 0,
      reward: b.is_monetary ? `₹${(b.reward_amount || 0).toLocaleString()} Cash` : (b.award_name || b.reward || ''),
      status: b.achievement_status || b.status || 'In Progress',
      can_claim: b.can_claim || false,
      type: b.target_type || b.bonanza_type || 'Direct'
    };
  }

  private mapClaimed(c: any): ClaimedBonanza {
    return {
      id: c.id || 0,
      bonanza_name: c.bonanza_name || c.name || '',
      target_achieved: c.target_achieved || c.current_progress || 0,
      target_required: c.target_required || c.target_value || 0,
      reward: c.is_monetary ? `₹${(c.reward_amount || 0).toLocaleString()}` : (c.award_name || c.reward || ''),
      claimed_date: c.claimed_date || c.claimed_at || null,
      processed_status: c.processed_status || 'Processing',
      dispatch_date: c.dispatch_date || null,
      received_date: c.received_date || null
    };
  }

  private renderEligibilityBanner(): string {
    if (!this.eligibility) return '';
    
    const e = this.eligibility;
    const isActivated = e.is_activated;
    const kycApproved = (e.kyc_status || 'pending').toLowerCase() === 'approved';
    const utilisationDone = e.program_utilisation_completed;
    const groupA = (e.group_a_points || 0) >= 1;
    const groupB = (e.group_b_points || 0) >= 1;
    
    if (isActivated && kycApproved && utilisationDone && groupA && groupB) return '';
    
    const items = [
      { done: isActivated, label: 'Account Activated' },
      { done: kycApproved, label: 'KYC Approved' },
      { done: utilisationDone, label: 'Program Utilisation Completed' },
      { done: groupA, label: 'Group A \u2013 Minimum 1 active & utilised business facilitation' },
      { done: groupB, label: 'Group B \u2013 Minimum 1 active & utilised business facilitation' }
    ];
    
    const checklistHtml = items.map(item => {
      const icon = item.done ? '<span class="done">\u2705</span>' : '<span class="pending">\u23F3</span>';
      return `<li>${icon}<span>${item.label}</span></li>`;
    }).join('');
    
    return `
      <div class="eligibility-banner">
        <div class="banner-title">\u{1F4CB} Eligibility Checklist</div>
        <div class="banner-desc">Awards and bonanza benefits are unlocked after successful utilisation of an eligible product or service through the MNR Business Access Program.</div>
        <ul class="checklist">${checklistHtml}</ul>
      </div>
    `;
  }

  private render(): void {
    this.container.innerHTML = `
      <style>
        ${MobileTable.getStyles()}
        .mnr-bonanza-page { padding: 16px; background: #0d1b2a; min-height: 100vh; }
        .requirements-card {
          background: #fff3cd;
          border-radius: 12px;
          padding: 16px;
          margin-bottom: 16px;
          color: #664d03;
        }
        .requirements-card .req-header {
          display: flex;
          align-items: center;
          gap: 8px;
          font-weight: 600;
          font-size: 14px;
          margin-bottom: 10px;
        }
        .requirements-card .req-text {
          font-size: 13px;
          margin-bottom: 12px;
          line-height: 1.5;
        }
        .requirements-card .activities-header {
          font-weight: 600;
          font-size: 13px;
          margin-bottom: 8px;
        }
        .requirements-card .activities-list {
          list-style: none;
          padding: 0;
          margin: 0 0 12px 0;
        }
        .requirements-card .activities-list li {
          font-size: 12px;
          padding: 3px 0 3px 16px;
          position: relative;
        }
        .requirements-card .activities-list li::before {
          content: "•";
          position: absolute;
          left: 4px;
        }
        .requirements-card .note-text {
          font-size: 11px;
          padding: 10px;
          background: rgba(0,0,0,0.05);
          border-radius: 8px;
        }
        .campaign-info {
          background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
          border-radius: 12px;
          padding: 16px;
          margin-bottom: 16px;
          color: white;
        }
        .campaign-info strong { font-size: 14px; }
        .campaign-info .alert-text { color: #fecaca; font-weight: 600; }
        .filters-section {
          background: #1a2744;
          border-radius: 12px;
          padding: 16px;
          margin-bottom: 16px;
        }
        .filters-section .filter-row {
          display: flex;
          flex-wrap: wrap;
          gap: 12px;
        }
        .filters-section .filter-group {
          flex: 1;
          min-width: 140px;
        }
        .filters-section label {
          display: block;
          font-size: 11px;
          color: #8892b0;
          margin-bottom: 4px;
        }
        .filters-section input,
        .filters-section select {
          width: 100%;
          padding: 10px 12px;
          background: #0d1b2a;
          border: 1px solid #2d3a4f;
          border-radius: 8px;
          color: #e6f1ff;
          font-size: 13px;
        }
        .eligibility-banner {
          background: linear-gradient(135deg, #1a3a5c 0%, #1e3a5f 100%);
          border: 1px solid #2d5f8a;
          border-radius: 12px;
          padding: 16px;
          margin-bottom: 16px;
          color: #c5ddf0;
        }
        .eligibility-banner .banner-title { font-size: 14px; font-weight: 600; margin: 0 0 6px 0; color: #64d2ff; }
        .eligibility-banner .banner-desc { font-size: 12px; margin: 0 0 12px 0; color: #8892b0; line-height: 1.5; }
        .eligibility-banner .checklist { list-style: none; padding: 0; margin: 0; }
        .eligibility-banner .checklist li { font-size: 13px; padding: 4px 0; display: flex; align-items: center; gap: 8px; }
        .eligibility-banner .checklist li .done { color: #10b981; }
        .eligibility-banner .checklist li .pending { color: #f59e0b; }
        .section-title {
          color: #64d2ff;
          font-size: 16px;
          font-weight: 600;
          margin: 24px 0 16px 0;
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .table-container { margin-top: 8px; }
        .badge { padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; display: inline-block; }
        .badge-success { background: #10b981; color: white; }
        .badge-warning { background: #f59e0b; color: white; }
        .badge-pending { background: #6b7280; color: white; }
        .badge-info { background: #3b82f6; color: white; }
        .badge-danger { background: #ef4444; color: white; }
        .badge-primary { background: #8b5cf6; color: white; }
        .claim-btn {
          padding: 6px 12px;
          background: #10b981;
          color: white;
          border: none;
          border-radius: 6px;
          font-size: 12px;
          cursor: pointer;
        }
        .claim-btn:disabled {
          background: #4b5563;
          cursor: not-allowed;
        }
        .progress-bar-container {
          width: 100%;
          height: 8px;
          background: #374151;
          border-radius: 4px;
          overflow: hidden;
        }
        .progress-bar-fill {
          height: 100%;
          background: linear-gradient(90deg, #10b981, #34d399);
          border-radius: 4px;
          transition: width 0.3s;
        }
      </style>
      ${PageHeader.render({ title: '🎉 Bonanza Awards', showBack: true })}
      <div class="mnr-bonanza-page">
        <div id="pageContent"></div>
      </div>
    `;
    PageHeader.attachListeners({ title: '🎉 Bonanza Awards', showBack: true });
  }

  private updateContent(): void {
    const content = document.getElementById('pageContent');
    if (!content) return;

    if (this.loading) {
      content.innerHTML = `
        <div class="loading-state" style="text-align: center; padding: 40px; color: #8892b0;">
          <div class="spinner" style="width: 40px; height: 40px; border: 3px solid rgba(100,210,255,0.2); border-top-color: #64d2ff; border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto 16px;"></div>
          <p>Loading...</p>
        </div>
        <style>@keyframes spin { to { transform: rotate(360deg); } }</style>
      `;
      return;
    }

    const filteredCampaigns = this.getFilteredCampaigns();

    content.innerHTML = `
      ${this.renderEligibilityBanner()}

      <div class="requirements-card">
        <div class="req-header">
          <span>📹</span>
          <span>Feedback Video and Photos Requirement</span>
        </div>
        <p class="req-text">
          <strong>To claim Bonanza rewards:</strong> Sharing feedback videos and photos is important.
        </p>
        <div class="activities-header">Eligible Engagement Activities:</div>
        <ul class="activities-list">
          <li>Reels (video content)</li>
          <li>WhatsApp Status sharing</li>
          <li>Social Media posts</li>
          <li>Sharing & Ratings in Announcement sections</li>
          <li>Engaging with teams</li>
          <li>Attending Zoom calls</li>
        </ul>
        <div class="note-text">
          ℹ️ Submitted feedback may be publicly displayed for promotional purposes.
        </div>
      </div>

      <div class="campaign-info">
        <strong>🎁 Bonanza Campaigns:</strong> Time-limited special reward campaigns. 
        <span class="alert-text">Bonanzas must be claimed within 5 days after the campaign end date!</span>
      </div>

      <div class="filters-section">
        <div class="filter-row">
          <div class="filter-group">
            <label>Search</label>
            <input type="text" id="searchFilter" placeholder="Search bonanzas..." value="${this.filters.search}">
          </div>
          <div class="filter-group">
            <label>Status</label>
            <select id="statusFilter">
              <option value="all" ${this.filters.status === 'all' ? 'selected' : ''}>All Status</option>
              <option value="achieved" ${this.filters.status === 'achieved' ? 'selected' : ''}>Achieved</option>
              <option value="in_progress" ${this.filters.status === 'in_progress' ? 'selected' : ''}>In Progress</option>
            </select>
          </div>
          <div class="filter-group">
            <label>Date</label>
            <select id="dateFilter">
              <option value="active" ${this.filters.date === 'active' ? 'selected' : ''}>Active</option>
              <option value="all" ${this.filters.date === 'all' ? 'selected' : ''}>All Time</option>
              <option value="ended" ${this.filters.date === 'ended' ? 'selected' : ''}>Ended</option>
            </select>
          </div>
          <div class="filter-group">
            <label>Type</label>
            <select id="typeFilter">
              <option value="all" ${this.filters.type === 'all' ? 'selected' : ''}>All Types</option>
              <option value="direct" ${this.filters.type === 'direct' ? 'selected' : ''}>Direct Business Facilitation</option>
              <option value="matching" ${this.filters.type === 'matching' ? 'selected' : ''}>Group Performance</option>
            </select>
          </div>
        </div>
      </div>

      <h3 class="section-title">🎯 Bonanza Campaigns</h3>
      <div class="table-container">
        ${this.renderCampaignsTable(filteredCampaigns)}
      </div>

      <h3 class="section-title">✅ My Claimed Bonanzas</h3>
      <div class="table-container">
        ${this.renderClaimedTable()}
      </div>
    `;

    this.attachListeners();
  }

  private getFilteredCampaigns(): BonanzaCampaign[] {
    return this.activeCampaigns.filter(c => {
      if (this.filters.search && !c.name.toLowerCase().includes(this.filters.search.toLowerCase())) return false;
      if (this.filters.status === 'achieved' && c.status.toLowerCase() !== 'achieved') return false;
      if (this.filters.status === 'in_progress' && c.status.toLowerCase() === 'achieved') return false;
      if (this.filters.type !== 'all' && c.type.toLowerCase() !== this.filters.type.toLowerCase()) return false;
      
      if (this.filters.date === 'active' && c.end_date) {
        const endDate = new Date(c.end_date);
        if (endDate < new Date()) return false;
      }
      if (this.filters.date === 'ended' && c.end_date) {
        const endDate = new Date(c.end_date);
        if (endDate >= new Date()) return false;
      }
      
      return true;
    });
  }

  private renderCampaignsTable(campaigns: BonanzaCampaign[]): string {
    if (campaigns.length === 0) {
      return `<div class="empty-state" style="text-align: center; padding: 40px; color: #8892b0;">
        <div style="font-size: 48px; margin-bottom: 16px;">🎯</div>
        <p>No active bonanza campaigns</p>
      </div>`;
    }

    const table = new MobileTable({
      columns: [
        { key: 'name', label: 'Bonanza Name', render: (v) => `<strong style="color: #f59e0b;">${v}</strong>` },
        { key: 'campaign_period', label: 'Campaign Period' },
        { key: 'criteria', label: 'Criteria' },
        { key: 'target', label: 'Target', render: (v) => `<span style="color: #3b82f6; font-weight: 600;">${v}</span>` },
        { key: 'your_progress', label: 'Your Progress', render: (v, row) => {
          const percent = Math.min(100, Math.round((v / row.target) * 100));
          return `
            <div style="min-width: 80px;">
              <div style="font-size: 12px; margin-bottom: 4px;">${v}/${row.target}</div>
              <div class="progress-bar-container">
                <div class="progress-bar-fill" style="width: ${percent}%"></div>
              </div>
            </div>
          `;
        }},
        { key: 'reward', label: 'Reward', render: (v) => `<strong style="color: #10b981;">${v}</strong>` },
        { key: 'status', label: 'Status', render: (v) => this.getStatusBadge(v) },
        { key: 'id', label: 'Action', render: (v, row) => {
          if (row.can_claim) {
            return `<button class="claim-btn" data-id="${v}">🎁 Claim</button>`;
          }
          if (row.status.toLowerCase() === 'achieved') {
            return '<span class="badge badge-success">Claimed</span>';
          }
          return '<span style="color: #6b7280; font-size: 11px;">Keep Going!</span>';
        }}
      ],
      data: campaigns,
      loading: false,
      emptyMessage: 'No campaigns found'
    });

    return table.render();
  }

  private renderClaimedTable(): string {
    if (this.claimedBonanzas.length === 0) {
      return `<div class="empty-state" style="text-align: center; padding: 40px; color: #8892b0;">
        <div style="font-size: 48px; margin-bottom: 16px;">📦</div>
        <p>No claimed bonanzas yet</p>
      </div>`;
    }

    const table = new MobileTable({
      columns: [
        { key: 'bonanza_name', label: 'Bonanza' },
        { key: 'target_achieved', label: 'Target Achieved', render: (v, row) => `${v} / ${row.target_required}` },
        { key: 'reward', label: 'Reward', render: (v) => `<strong style="color: #10b981;">${v}</strong>` },
        { key: 'claimed_date', label: 'Claimed Date', render: (v) => this.formatDate(v) },
        { key: 'processed_status', label: 'Status', render: (v) => this.getProcessedBadge(v) },
        { key: 'dispatch_date', label: 'Dispatch Date', render: (v) => this.formatDate(v) },
        { key: 'received_date', label: 'Received Date', render: (v) => this.formatDate(v) }
      ],
      data: this.claimedBonanzas,
      loading: false,
      emptyMessage: 'No claimed bonanzas'
    });

    return table.render();
  }

  private attachListeners(): void {
    const searchInput = document.getElementById('searchFilter') as HTMLInputElement;
    const statusSelect = document.getElementById('statusFilter') as HTMLSelectElement;
    const dateSelect = document.getElementById('dateFilter') as HTMLSelectElement;
    const typeSelect = document.getElementById('typeFilter') as HTMLSelectElement;

    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        this.filters.search = (e.target as HTMLInputElement).value;
        this.updateContent();
      });
    }
    if (statusSelect) {
      statusSelect.addEventListener('change', (e) => {
        this.filters.status = (e.target as HTMLSelectElement).value;
        this.updateContent();
      });
    }
    if (dateSelect) {
      dateSelect.addEventListener('change', (e) => {
        this.filters.date = (e.target as HTMLSelectElement).value;
        this.updateContent();
      });
    }
    if (typeSelect) {
      typeSelect.addEventListener('change', (e) => {
        this.filters.type = (e.target as HTMLSelectElement).value;
        this.updateContent();
      });
    }

    document.querySelectorAll('.claim-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const bonanzaId = btn.getAttribute('data-id');
        if (bonanzaId) {
          await this.claimBonanza(parseInt(bonanzaId));
        }
      });
    });
  }

  private async claimBonanza(bonanzaId: number): Promise<void> {
    try {
      const response = await apiService.post<any>(`/bonanza/claim/${bonanzaId}`, {});
      if (response.success) {
        alert('Bonanza claimed successfully!');
        await this.loadData();
      } else {
        alert(response.error || 'Failed to claim bonanza');
      }
    } catch (error) {
      console.error('[MNRBonanza] Claim failed:', error);
      alert('Failed to claim bonanza. Please try again.');
    }
  }

  private getStatusBadge(status: string): string {
    const s = status.toLowerCase();
    if (s === 'achieved') return '<span class="badge badge-success">✓ Achieved</span>';
    if (s === 'in progress') return '<span class="badge badge-warning">⊙ In Progress</span>';
    return `<span class="badge badge-pending">${status}</span>`;
  }

  private getProcessedBadge(status: string): string {
    const s = (status || '').toLowerCase();
    const display = this.getSimplifiedStatus(s);
    if (display === 'Pending' || display === 'Claimed') return '<span class="badge badge-warning">⊙ ' + display + '</span>';
    if (display === 'Approved') return '<span class="badge badge-info">✓ Approved</span>';
    if (display === 'Processed') return '<span class="badge badge-primary">⊞ Processed</span>';
    if (display === 'Completed') return '<span class="badge badge-success">✓ Completed</span>';
    if (display === 'Rejected') return '<span class="badge badge-danger">✗ Rejected</span>';
    return `<span class="badge badge-pending">${display}</span>`;
  }

  private getSimplifiedStatus(s: string): string {
    if (s === 'pending approval' || s === 'pending') return 'Claimed';
    if (s === 'admin approved') return 'Approved';
    if (s === 'procurement pending' || s === 'processed for dispatch' || s === 'dispatched' || s === 'ordered') return 'Processed';
    if (s === 'delivered' || s === 'delivered - completed') return 'Completed';
    if (s === 'rejected') return 'Rejected';
    return s || 'Pending';
  }

  private formatDate(dateStr: string | null): string {
    if (!dateStr) return '<span style="color: #6b7280;">-</span>';
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
    } catch {
      return dateStr;
    }
  }
}
