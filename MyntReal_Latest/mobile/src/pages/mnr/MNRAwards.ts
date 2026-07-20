/**
 * MNR Awards Summary Page - Complete Web Parity
 * DC Protocol: DC_MOBILE_MNR_AWARDS_003
 * Matches web: Stats cards, 3 tabs (All/Direct/Matching), Full table with all columns
 */

import { apiService } from '../../services/api.service';
import { authService } from '../../services/auth.service';
import { PageHeader } from '../../components/PageHeader';
import { MobileTable } from '../../components/MobileTable';

interface Award {
  id: number;
  award_rank: string;
  award_item: string;
  requirement: number;
  current_progress: number;
  bonanza_claimed: number;
  remaining: number;
  achievement_status: string;
  processed_status: string;
  last_updated: string | null;
  category: 'direct' | 'matching';
}

interface AwardStats {
  achieved: number;
  received: number;
  pending: number;
}

interface EligibilityStatus {
  is_activated: boolean;
  kyc_status: string;
  program_utilisation_completed: boolean;
  group_a_points: number;
  group_b_points: number;
  is_eligible: boolean;
}

export class MNRAwards {
  private container: HTMLElement;
  private awards: Award[] = [];
  private stats: AwardStats = { achieved: 0, received: 0, pending: 0 };
  private loading: boolean = true;
  private activeTab: string = 'all';
  private eligibility: EligibilityStatus | null = null;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadAwards();
  }

  private async loadAwards(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      const authState = authService.getAuthState();
      const userId = authState.user?.id || authState.user?.mnr_id || '';
      
      if (!userId) {
        console.error('[MNRAwards] No user ID found');
        this.loading = false;
        this.updateContent();
        return;
      }
      
      const [directRes, matchingRes, eligibilityRes] = await Promise.all([
        apiService.get<any>(`/awards-fast/user/${userId}/direct`),
        apiService.get<any>(`/awards-fast/user/${userId}/matching`),
        apiService.get<any>('/auth/me-hybrid?role=mnr')
      ]);

      const directAwards = (directRes.success && directRes.data?.direct_awards) 
        ? directRes.data.direct_awards 
        : (directRes.data?.direct_awards || []);
      
      const matchingAwards = (matchingRes.success && matchingRes.data?.matching_awards)
        ? matchingRes.data.matching_awards
        : (matchingRes.data?.matching_awards || []);

      this.awards = [
        ...directAwards.map((a: any) => this.mapAward(a, 'direct')),
        ...matchingAwards.map((a: any) => this.mapAward(a, 'matching'))
      ];

      this.calculateStats();

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
      console.error('[MNRAwards] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private mapAward(a: any, category: 'direct' | 'matching'): Award {
    const tierInfo = a.tier_info || a;
    const requirement = tierInfo.referral_count || tierInfo.cumulative_required || a.requirement || 0;
    const currentProgress = a.current_direct_count || a.current_matching_pairs || a.current_progress || 0;
    const bonanzaDeduct = a.bonanza_deductions || 0;
    const achieved = a.achieved || false;
    
    return {
      id: tierInfo.id || a.id || 0,
      award_rank: tierInfo.rank_name || tierInfo.award_name || a.rank_name || a.award_name || '',
      award_item: tierInfo.award_item || a.award_item || tierInfo.award_description || '',
      requirement: requirement,
      current_progress: currentProgress,
      bonanza_claimed: bonanzaDeduct,
      remaining: Math.max(0, requirement - currentProgress + bonanzaDeduct),
      achievement_status: achieved ? 'Achieved' : (a.achievement_status || 'Pending'),
      processed_status: a.processed_status || a.simplified_status || 'Pending',
      last_updated: a.last_updated || a.achievement_date || a.process_date || null,
      category: category
    };
  }

  private calculateStats(): void {
    this.stats = {
      achieved: this.awards.filter(a => 
        a.achievement_status.toLowerCase() === 'achieved' || 
        a.achievement_status.toLowerCase() === 'completed'
      ).length,
      received: this.awards.filter(a => 
        a.processed_status.toLowerCase() === 'delivered' || 
        a.processed_status.toLowerCase() === 'delivered - completed'
      ).length,
      pending: this.awards.filter(a => 
        a.achievement_status.toLowerCase() === 'pending' ||
        (a.achievement_status.toLowerCase() === 'achieved' && 
         a.processed_status.toLowerCase() !== 'delivered')
      ).length
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
        .mnr-awards-page { padding: 16px; background: #0d1b2a; min-height: 100vh; }
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
        .stats-row {
          display: flex;
          gap: 12px;
          margin-bottom: 16px;
          overflow-x: auto;
        }
        .stat-card {
          flex: 1;
          min-width: 100px;
          padding: 16px 12px;
          border-radius: 12px;
          text-align: center;
        }
        .stat-card.achieved { background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; }
        .stat-card.received { background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); color: white; }
        .stat-card.pending { background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); color: white; }
        .stat-card .stat-icon { font-size: 24px; margin-bottom: 6px; }
        .stat-card .stat-value { font-size: 24px; font-weight: 700; }
        .stat-card .stat-label { font-size: 11px; opacity: 0.9; }
        .tabs-container {
          display: flex;
          gap: 8px;
          margin-bottom: 16px;
          background: #1a2744;
          padding: 8px;
          border-radius: 12px;
          overflow-x: auto;
        }
        .tab-btn {
          flex: 1;
          padding: 10px 12px;
          background: transparent;
          border: none;
          border-radius: 8px;
          color: #8892b0;
          font-size: 13px;
          font-weight: 500;
          white-space: nowrap;
          cursor: pointer;
          transition: all 0.2s;
        }
        .tab-btn.active {
          background: #64d2ff;
          color: #0d1b2a;
          font-weight: 600;
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
        .table-container { margin-top: 8px; }
        .badge { padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
        .badge-success { background: #10b981; color: white; }
        .badge-warning { background: #f59e0b; color: white; }
        .badge-pending { background: #6b7280; color: white; }
        .badge-info { background: #3b82f6; color: white; }
        .badge-danger { background: #ef4444; color: white; }
        .badge-primary { background: #8b5cf6; color: white; }
      </style>
      ${PageHeader.render({ title: '🏆 Awards Summary', showBack: true })}
      <div class="mnr-awards-page">
        <div id="pageContent"></div>
      </div>
    `;
    PageHeader.attachListeners({ title: '🏆 Awards Summary', showBack: true });
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

    const filteredAwards = this.getFilteredAwards();

    content.innerHTML = `
      ${this.renderEligibilityBanner()}

      <div class="requirements-card">
        <div class="req-header">
          <span>📹</span>
          <span>Feedback Video and Photos Requirement</span>
        </div>
        <p class="req-text">
          <strong>To claim net achieved level awards:</strong> Sharing feedback videos and photos is important.
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
          ℹ️ Please note: Submitted feedback videos and photos may be publicly displayed on our platforms for promotional and community engagement purposes.
        </div>
      </div>

      <div class="stats-row">
        <div class="stat-card achieved">
          <div class="stat-icon">✓</div>
          <div class="stat-value">${this.stats.achieved}</div>
          <div class="stat-label">Achieved Awards<br><small>Awards you've qualified for</small></div>
        </div>
        <div class="stat-card received">
          <div class="stat-icon">🎁</div>
          <div class="stat-value">${this.stats.received}</div>
          <div class="stat-label">Received Awards<br><small>Awards already processed</small></div>
        </div>
        <div class="stat-card pending">
          <div class="stat-icon">⏳</div>
          <div class="stat-value">${this.stats.pending}</div>
          <div class="stat-label">Pending Awards<br><small>Awards awaiting processing</small></div>
        </div>
      </div>

      <div class="tabs-container">
        <button class="tab-btn ${this.activeTab === 'all' ? 'active' : ''}" data-tab="all">All Awards</button>
        <button class="tab-btn ${this.activeTab === 'direct' ? 'active' : ''}" data-tab="direct">Direct Business Facilitations</button>
        <button class="tab-btn ${this.activeTab === 'matching' ? 'active' : ''}" data-tab="matching">Group Performance Recognitions</button>
      </div>

      <div class="table-container">
        ${this.renderAwardsTable(filteredAwards)}
      </div>
    `;

    this.attachListeners();
  }

  private getFilteredAwards(): Award[] {
    if (this.activeTab === 'all') return this.awards;
    if (this.activeTab === 'direct') return this.awards.filter(a => a.category === 'direct');
    return this.awards.filter(a => a.category === 'matching');
  }

  private renderAwardsTable(awards: Award[]): string {
    if (awards.length === 0) {
      return `<div class="empty-state" style="text-align: center; padding: 40px; color: #8892b0;">
        <div style="font-size: 48px; margin-bottom: 16px;">🏆</div>
        <p>No awards found</p>
      </div>`;
    }

    const table = new MobileTable({
      columns: [
        { key: 'award_rank', label: 'Award Rank', render: (v) => `<strong style="color: #f59e0b;">${v}</strong>` },
        { key: 'award_item', label: 'Award Item' },
        { key: 'requirement', label: 'Requirement', render: (v) => `<span style="color: #3b82f6;">${v}</span>` },
        { key: 'current_progress', label: 'Current Progress', render: (v) => `<span style="color: #10b981;">${v}</span>` },
        { key: 'bonanza_claimed', label: 'Bonanza Claimed' },
        { key: 'remaining', label: 'Remaining', render: (v, row) => {
          if (row.achievement_status.toLowerCase() === 'achieved') return '<span style="color: #10b981;">Complete</span>';
          return `<span style="color: #ef4444;">${v}</span>`;
        }},
        { key: 'achievement_status', label: 'Achievement Status', render: (v) => this.getAchievementBadge(v) },
        { key: 'processed_status', label: 'Status', render: (v) => this.getProcessedBadge(v) },
        { key: 'last_updated', label: 'Last Updated', render: (v) => this.formatDate(v) }
      ],
      data: awards,
      loading: false,
      emptyMessage: 'No awards found'
    });

    return table.render();
  }

  private attachListeners(): void {
    document.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        this.activeTab = btn.getAttribute('data-tab') || 'all';
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.updateContent();
      });
    });
  }

  private getAchievementBadge(status: string): string {
    const s = status.toLowerCase();
    if (s === 'achieved' || s === 'completed') return '<span class="badge badge-success">✓ Achieved</span>';
    return '<span class="badge badge-warning">⊙ Pending</span>';
  }

  private getProcessedBadge(status: string): string {
    const s = (status || '').toLowerCase();
    const display = this.getSimplifiedStatus(s);
    if (display === 'Pending') return '<span class="badge badge-warning">⊙ Pending</span>';
    if (display === 'Approved') return '<span class="badge badge-info">✓ Approved</span>';
    if (display === 'Processed') return '<span class="badge badge-primary">⊞ Processed</span>';
    if (display === 'Completed') return '<span class="badge badge-success">✓ Completed</span>';
    if (display === 'Rejected') return '<span class="badge badge-danger">✗ Rejected</span>';
    return `<span class="badge badge-pending">${display}</span>`;
  }

  private getSimplifiedStatus(s: string): string {
    if (s === 'pending approval' || s === 'pending') return 'Pending';
    if (s === 'admin approved') return 'Approved';
    if (s === 'procurement pending' || s === 'processed for dispatch' || s === 'dispatched' || s === 'ordered') return 'Processed';
    if (s === 'delivered' || s === 'delivered - completed') return 'Completed';
    if (s === 'rejected') return 'Rejected';
    return s || 'Pending';
  }

  private formatDate(dateStr: string | null): string {
    if (!dateStr) return '<span style="color: #6b7280;">Not Received Yet</span>';
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
    } catch {
      return dateStr;
    }
  }
}
