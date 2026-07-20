/**
 * MNR Dashboard Page
 * DC Protocol: DC_MOBILE_MNR_DASHBOARD_001
 * Main dashboard for MNR members - Web Parity Version
 * Includes Terms popup, Birthday banner, Top Earners
 */

import { apiService } from '../../services/api.service';
import { authService } from '../../services/auth.service';
import { routerService } from '../../services/router.service';
import { mnrSideDrawer } from '../../components/MNRSideDrawer';
import { Clipboard } from '@capacitor/clipboard';
import { Share } from '@capacitor/share';
import { Preferences } from '@capacitor/preferences';
import { APP_CONFIG } from '../../config/app.config';

// DC Protocol: Use centralized configuration from APP_CONFIG
const PUBLIC_DOMAIN = APP_CONFIG.MEDIA_BASE_URL;
const TERMS_ACCEPTED_KEY_PREFIX = 'mnr_terms_accepted';

interface WalletBalance {
  earning_wallet: number;
  withdrawable_wallet: number;
  upgrade_wallet: number;
}

interface WalletSummary {
  overall_earning: number;
  withdrawn: number;
  total_pending: number;
}

interface BinaryTree {
  left_count: number;
  right_count: number;
  total_count: number;
}

interface TeamData {
  direct_referrals: number;
  matching_referrals_count: number;
  binary_tree: BinaryTree;
  binary_tree_active: BinaryTree;
  team_activated: number;
}

interface ActivatedData {
  direct_activated: number;
  self_team_activated: number;
}

interface VedData {
  total_ved_ids: number;
  eligible_ved_count: number;
  non_eligible_ved_count: number;
  is_ved_eligible: boolean;
  ved_team_total: number;
  ved_team_activated: number;
}

interface PreviousCounts {
  direct_referrals: number;
  direct_activated: number;
  my_team: number;
  matching: number;
  left_team: number;
  left_active: number;
  right_team: number;
  right_active: number;
  ved_overall: number;
  ved_activated: number;
}

interface ProfileData {
  name: string;
  mnr_id: string;
  direct_referral_rank: string;
  matching_referral_rank: string;
  wallet: WalletBalance;
  registration_date: string;
  active_status: boolean;
  active_date: string;
  package: string;
  date_of_birth?: string;
}

interface Banner {
  id: number;
  title: string;
  image_url?: string;
  image_content?: string;
  text_content?: string;
}

interface LatestEarner {
  name: string;
  mnr_id: string;
  user_id?: string;
  amount: number;
  total_earnings?: number;
}

interface DashboardData {
  profile: ProfileData;
  team: TeamData;
  activated: ActivatedData;
  ved: VedData;
  previous_counts: PreviousCounts;
  wallet_summary: WalletSummary;
  yesterday_earnings: number;
  banners?: Banner[];
  latest_earners?: LatestEarner[];
}

interface InsuranceStatus {
  has_insurance: boolean;
  is_eligible: boolean;
  show_banner: boolean;
  banner_type: 'insured' | 'eligible' | 'service_required' | 'referral_required' | 'not_activated';
  policy_number?: string;
  expiry_date?: string;
  days_remaining?: number;
  message?: string;
  kyc_status?: string;
  kyc_approved?: boolean;
  referrals_count?: number;
  referrals_needed?: number;
  group_a_referrals?: number;
  group_b_referrals?: number;
}

export class MNRDashboard {
  private container: HTMLElement;
  private user: any = null;
  private data: DashboardData | null = null;
  private loading: boolean = true;
  private banners: Banner[] = [];
  private latestEarners: LatestEarner[] = [];
  private showTermsPopup: boolean = false;
  private isBirthday: boolean = false;
  private insuranceStatus: InsuranceStatus | null = null;
  private bannerDismissed: boolean = false;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    const authState = authService.getAuthState();
    this.user = authState.user;
    mnrSideDrawer.setUser(this.user);
    
    await this.checkTermsAcceptance();
    this.render();
    await this.loadDashboard();
    
    if (this.showTermsPopup) {
      this.renderTermsPopup();
    }
  }

  private async checkTermsAcceptance(): Promise<void> {
    try {
      const meRes = await apiService.get<any>('/auth/me');
      const userAcceptedVersion = meRes?.data?.accepted_terms_version || null;
      
      const tcRes = await apiService.get<any>('/auth/public/terms-and-conditions');
      const currentVersion = tcRes?.data?.version || '1.0';
      this.currentTCVersion = currentVersion;
      
      if (userAcceptedVersion && userAcceptedVersion === currentVersion) {
        this.showTermsPopup = false;
        return;
      }
      
      const userId = this.user?.mnr_id || this.user?.id || '';
      const key = `${TERMS_ACCEPTED_KEY_PREFIX}_${userId}_v${currentVersion}`;
      const { value } = await Preferences.get({ key });
      const shownCountKey = `terms_shown_count_${userId}_v${currentVersion}`;
      const { value: countVal } = await Preferences.get({ key: shownCountKey });
      const shownCount = parseInt(countVal || '0');
      const maxDisplays = tcRes?.data?.max_displays || 3;
      
      if (!value && shownCount < maxDisplays) {
        this.showTermsPopup = true;
        await Preferences.set({ key: shownCountKey, value: (shownCount + 1).toString() });
      } else {
        this.showTermsPopup = false;
      }
    } catch {
      this.showTermsPopup = true;
    }
  }

  private currentTCVersion: string = '1.0';

  private async acceptTerms(): Promise<void> {
    try {
      const userId = this.user?.mnr_id || this.user?.id || '';
      const version = this.currentTCVersion;
      
      await apiService.post('/users/accept-terms', { version });
      
      const key = `${TERMS_ACCEPTED_KEY_PREFIX}_${userId}_v${version}`;
      await Preferences.set({ key, value: new Date().toISOString() });
      this.showTermsPopup = false;
      this.closeTermsPopup();
    } catch (error) {
      console.error('[MNRDashboard] Failed to save terms acceptance:', error);
    }
  }

  private checkBirthday(): void {
    const dob = this.data?.profile?.date_of_birth || this.user?.date_of_birth;
    if (!dob) {
      this.isBirthday = false;
      return;
    }
    try {
      const today = new Date();
      const birthDate = new Date(dob);
      this.isBirthday = today.getMonth() === birthDate.getMonth() && 
                         today.getDate() === birthDate.getDate();
    } catch {
      this.isBirthday = false;
    }
  }

  private async loadDashboard(): Promise<void> {
    this.loading = true;
    this.updateContent();

    const { value: dismissed } = await Preferences.get({ key: 'mnr_banner_dismissed' });
    this.bannerDismissed = dismissed === 'true';

    try {
      const [dashboardRes, bannerDataRes, earnersRes, insuranceRes] = await Promise.all([
        apiService.get<DashboardData>('/users/dashboard-data-fast'),
        apiService.get<any>('/banners/dashboard-data').catch(() => ({ success: false, data: null })),
        apiService.get<any>('/banners/top-performers?limit=7').catch(() => ({ success: false, data: null })),
        this.bannerDismissed ? Promise.resolve({ success: false, data: null }) : apiService.get<InsuranceStatus>('/users/my-insurance-status').catch(() => ({ success: false, data: null }))
      ]);

      if (dashboardRes.success && dashboardRes.data) {
        this.data = dashboardRes.data;
        this.checkBirthday();
      }
      if (bannerDataRes.success && bannerDataRes.data) {
        const bd = bannerDataRes.data;
        const imageBanners = bd.image_banners || [];
        this.banners = imageBanners.map((b: any) => ({
          id: b.id,
          title: b.title || 'Banner',
          image_content: b.image_content,
          text_content: b.text_content
        }));
      }
      if (earnersRes.success && earnersRes.data) {
        const performers = earnersRes.data.top_performers || earnersRes.data || [];
        this.latestEarners = Array.isArray(performers) ? performers.map((p: any) => ({
          name: p.name || '',
          mnr_id: p.user_id || p.mnr_id || '',
          amount: p.total_earnings || p.amount || 0
        })) : [];
      }
      if (insuranceRes.success && insuranceRes.data) {
        this.insuranceStatus = insuranceRes.data;
      }
    } catch (error) {
      console.error('[MNRDashboard] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
    this.setupBannerDismiss();
  }

  private render(): void {
    const username = this.user?.name || this.user?.mnr_id || 'Member';
    const mnrId = this.user?.mnr_id || '';

    this.container.innerHTML = `
      <style>
        .mnr-dashboard { background: linear-gradient(135deg, #0a1929 0%, #0d2137 100%); min-height: 100vh; }
        .mnr-dashboard-header {
          background: linear-gradient(135deg, #7c3aed 0%, #5b21b6 100%);
          padding: 16px;
          display: flex;
          align-items: center;
          justify-content: space-between;
        }
        .mnr-header-left { display: flex; align-items: center; gap: 12px; }
        .mnr-hamburger-btn {
          background: rgba(255, 255, 255, 0.15);
          border: none;
          border-radius: 8px;
          padding: 10px;
          color: white;
          cursor: pointer;
        }
        .mnr-header-user { display: flex; align-items: center; gap: 10px; }
        .mnr-header-avatar {
          width: 40px;
          height: 40px;
          border-radius: 50%;
          background: rgba(255, 255, 255, 0.2);
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: 600;
          font-size: 14px;
          color: white;
        }
        .mnr-header-info { display: flex; flex-direction: column; }
        .mnr-header-name { font-size: 14px; font-weight: 600; color: white; }
        .mnr-header-id { font-size: 11px; color: rgba(255, 255, 255, 0.8); }
        .mnr-share-btn {
          display: flex;
          align-items: center;
          gap: 6px;
          background: rgba(255, 255, 255, 0.15);
          border: none;
          border-radius: 8px;
          padding: 8px 12px;
          color: white;
          font-size: 12px;
          cursor: pointer;
        }
        .dashboard-content { padding: 16px; }
        .loading-state { text-align: center; padding: 40px; color: #8892b0; }

        /* Birthday Banner */
        .birthday-banner {
          background: linear-gradient(135deg, #ec4899 0%, #f472b6 50%, #fbbf24 100%);
          border-radius: 12px;
          padding: 20px;
          margin-bottom: 16px;
          text-align: center;
          animation: celebrate 2s ease-in-out infinite;
        }
        @keyframes celebrate {
          0%, 100% { transform: scale(1); }
          50% { transform: scale(1.02); }
        }
        .birthday-banner h3 { margin: 0 0 8px; font-size: 20px; color: white; }
        .birthday-banner p { margin: 0; font-size: 14px; color: rgba(255, 255, 255, 0.9); }

        /* Insurance Banner - DC Protocol Feb 2026 */
        .insurance-banner {
          border-radius: 12px;
          padding: 20px;
          margin-bottom: 16px;
          text-align: center;
        }
        .insurance-banner.insured {
          background: linear-gradient(135deg, #059669 0%, #047857 100%);
        }
        .insurance-banner.eligible {
          background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
        }
        .insurance-banner.service-required {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        .insurance-banner .insurance-icon { font-size: 32px; margin-bottom: 8px; }
        .insurance-banner h4 { margin: 0 0 6px; font-size: 16px; color: white; font-weight: 600; }
        .insurance-banner p { margin: 0; font-size: 13px; color: rgba(255, 255, 255, 0.9); line-height: 1.4; }
        .insurance-banner .policy-details { margin-top: 8px; font-size: 11px; color: rgba(255, 255, 255, 0.8); }

        /* Active Banners - Web Style */
        .mnr-banner-section { margin-bottom: 16px; }
        .mnr-banner-slide {
          background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
          border-radius: 10px;
          padding: 16px 20px;
          text-align: center;
          margin-bottom: 8px;
        }
        .mnr-banner-slide h4 { margin: 0; font-size: 15px; color: #451a03; font-weight: 600; }

        /* Latest Earners - Web Parity */
        .latest-earners-section {
          background: linear-gradient(135deg, #1e3a5f 0%, #0f2744 100%);
          border-radius: 12px;
          padding: 16px;
          margin-bottom: 16px;
        }
        .latest-earners-header {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 16px;
          justify-content: center;
        }
        .latest-earners-header h3 { margin: 0; font-size: 14px; color: #fbbf24; }
        .earners-carousel {
          display: flex;
          gap: 12px;
          overflow-x: auto;
          padding-bottom: 8px;
          scroll-snap-type: x mandatory;
        }
        .earners-carousel::-webkit-scrollbar { height: 4px; }
        .earners-carousel::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.2); border-radius: 2px; }
        .earner-card {
          flex: 0 0 auto;
          min-width: 140px;
          background: linear-gradient(135deg, #16213e 0%, #1a1a2e 100%);
          border: 2px solid #fbbf24;
          border-radius: 12px;
          padding: 16px;
          text-align: center;
          position: relative;
          scroll-snap-align: start;
        }
        .earner-medal {
          position: absolute;
          top: -12px;
          left: 50%;
          transform: translateX(-50%);
          font-size: 28px;
        }
        .earner-avatar {
          width: 56px;
          height: 56px;
          border-radius: 50%;
          background: linear-gradient(135deg, #7c3aed 0%, #a855f7 100%);
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: 700;
          font-size: 18px;
          color: white;
          margin: 8px auto 10px;
          border: 3px solid #fbbf24;
        }
        .earner-name { font-size: 13px; font-weight: 600; color: white; margin-bottom: 2px; }
        .earner-id { font-size: 10px; color: #8892b0; margin-bottom: 6px; }
        .earner-amount { font-size: 15px; font-weight: 700; color: #10b981; }

        /* Section Cards */
        .mnr-section-card { background: #ffffff;
          background: rgba(22, 33, 62, 0.95);
          border-radius: 10px;
          margin-bottom: 16px;
          overflow: hidden;
          border: 1px solid rgba(255, 255, 255, 0.1);
        }
        .section-header-bar {
          padding: 12px 16px;
          color: white;
        }
        .section-header-bar.green { background: linear-gradient(135deg, #16a34a 0%, #15803d 100%); }
        .section-header-bar.orange { background: linear-gradient(135deg, #ea580c 0%, #c2410c 100%); }
        .section-header-bar.purple { background: linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%); }
        .section-header-bar.blue { background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%); }
        .section-header-bar h3 { margin: 0; font-size: 13px; font-weight: 600; text-transform: uppercase; }
        .section-content { padding: 14px 16px; background: #ffffff; }
        .summary-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 8px 0;
          border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }
        .summary-row:last-child { border-bottom: none; }
        .summary-row .label { font-size: 12px; color: #4b5563; font-weight: 500; }
        .summary-row .value { font-size: 13px; color: #1f2937; font-weight: 600; }
        .badge-rank {
          background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
          color: white;
          padding: 4px 10px;
          border-radius: 4px;
          font-size: 11px;
          font-weight: 600;
        }
        .badge-rank.secondary {
          background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
        }
        .badge-status {
          padding: 4px 10px;
          border-radius: 4px;
          font-size: 11px;
          font-weight: 600;
        }
        .badge-status.active { background: #10b981; color: white; }
        .badge-status.inactive { background: #6b7280; color: white; }
        .counts-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 10px;
        }
        .count-item {
          display: flex;
          justify-content: space-between;
          background: #f3f4f6;
          padding: 10px 12px;
          border-radius: 6px;
        }
        .count-label { font-size: 11px; color: #4b5563; font-weight: 500; }
        .count-value { font-size: 13px; font-weight: 600; color: #10b981; }

        /* Quick Actions */
        .quick-actions { margin-top: 8px; }
        .section-title { font-size: 14px; color: #1f2937; margin: 0 0 12px; }
        .action-grid {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 10px;
        }
        .action-btn {
          background: rgba(22, 33, 62, 0.9);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 10px;
          padding: 14px 8px;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 6px;
          color: #e6f1ff;
          font-size: 11px;
          cursor: pointer;
        }
        .action-btn:active { background: rgba(124, 58, 237, 0.3); }
        .action-btn svg { color: #a855f7; }

        /* Terms Popup */
        .terms-overlay {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0, 0, 0, 0.8);
          z-index: 9999;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 20px;
        }
        .terms-modal {
          background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
          border-radius: 16px;
          max-width: 400px;
          width: 100%;
          max-height: 80vh;
          overflow: hidden;
          display: flex;
          flex-direction: column;
        }
        .terms-header {
          background: linear-gradient(135deg, #7c3aed 0%, #5b21b6 100%);
          padding: 24px 20px;
          text-align: center;
        }
        .terms-header h2 {
          margin: 0 0 6px;
          font-size: 18px;
          color: white;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
        }
        .terms-header p { margin: 0; font-size: 13px; color: rgba(255, 255, 255, 0.8); }
        .terms-body {
          padding: 20px;
          overflow-y: auto;
          flex: 1;
        }
        .terms-section-title {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 15px;
          color: #10b981;
          margin: 0 0 10px;
          font-weight: 600;
        }
        .terms-text {
          font-size: 13px;
          color: #9ca3af;
          line-height: 1.6;
          margin-bottom: 16px;
        }
        .terms-important {
          background: rgba(239, 68, 68, 0.1);
          border: 1px solid rgba(239, 68, 68, 0.3);
          border-radius: 8px;
          padding: 12px;
          margin-bottom: 16px;
        }
        .terms-important-title {
          display: flex;
          align-items: center;
          gap: 6px;
          font-size: 13px;
          color: #f59e0b;
          margin: 0 0 8px;
          font-weight: 600;
        }
        .terms-notice {
          background: rgba(239, 68, 68, 0.2);
          border-left: 4px solid #ef4444;
          padding: 10px 12px;
          margin-bottom: 8px;
        }
        .terms-notice-title { font-size: 13px; font-weight: 600; color: white; margin: 0 0 6px; }
        .terms-notice-list {
          margin: 0;
          padding-left: 16px;
          font-size: 12px;
          color: #d1d5db;
          line-height: 1.6;
        }
        .terms-warning {
          background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
          border-radius: 8px;
          padding: 12px;
          margin-top: 16px;
        }
        .terms-warning p {
          margin: 0;
          font-size: 12px;
          color: #78350f;
          line-height: 1.5;
        }
        .terms-warning strong { color: #dc2626; }
        .terms-footer {
          padding: 16px 20px;
          background: rgba(0, 0, 0, 0.2);
        }
        .terms-accept-btn {
          width: 100%;
          padding: 14px;
          background: linear-gradient(135deg, #10b981 0%, #059669 100%);
          border: none;
          border-radius: 8px;
          color: white;
          font-size: 15px;
          font-weight: 600;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
        }
        .terms-accept-btn:active { opacity: 0.9; }
      </style>

      <div class="page-container mnr-dashboard">
        <header class="mnr-dashboard-header">
          <div class="mnr-header-left">
            <button class="mnr-hamburger-btn" id="mnrHamburgerBtn">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/>
              </svg>
            </button>
            <div class="mnr-header-user">
              <div class="mnr-header-avatar">${this.getInitials(username)}</div>
              <div class="mnr-header-info">
                <span class="mnr-header-name">${username}</span>
                <span class="mnr-header-id">${mnrId}</span>
              </div>
            </div>
          </div>
          <div class="mnr-header-actions">
            <button class="mnr-share-btn" id="shareBtn">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/>
                <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>
              </svg>
              Share
            </button>
          </div>
        </header>

        <div class="dashboard-content" id="dashboardContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>

      <div id="termsPopupContainer"></div>
    `;

    this.attachListeners();
  }

  private renderTermsPopup(): void {
    const container = document.getElementById('termsPopupContainer');
    if (!container) return;

    container.innerHTML = `
      <div class="terms-overlay" id="termsOverlay">
        <div class="terms-modal">
          <div class="terms-header">
            <h2>🎉 Welcome to MyntReal Platform!</h2>
            <p>Your journey to success begins here</p>
          </div>
          <div class="terms-body">
            <h3 class="terms-section-title">📋 Terms and Conditions</h3>
            <p class="terms-text">Please read and accept our terms and conditions to continue using the platform.</p>

            <h4 class="terms-section-title">📜 Terms & Conditions</h4>
            <p class="terms-text">Welcome to MNR Business Access Program! We are glad to have you as part of our community. Please take a moment to review these terms to understand how our platform operates.</p>

            <div class="terms-important">
              <h5 class="terms-important-title">⚠️ Important System Information</h5>
              <div class="terms-notice">
                <p class="terms-notice-title">MNR Independence Notice:</p>
                <ul class="terms-notice-list">
                  <li>MNR operates as an independent platform and is not related to any previous systems such as BeV or similar programs.</li>
                  <li>While we maintain legacy data from prior systems for record-keeping purposes, MNR is a completely new and separate entity.</li>
                  <li>All operations, policies, and procedures are governed solely by MNR guidelines.</li>
                </ul>
              </div>
            </div>

            <div class="terms-warning">
              <p><strong>⚠️ Important:</strong> By clicking "I Accept", you acknowledge that you have read, understood, and agree to these terms and conditions.</p>
            </div>
          </div>
          <div class="terms-footer">
            <button class="terms-accept-btn" id="acceptTermsBtn">
              ✓ I Accept
            </button>
          </div>
        </div>
      </div>
    `;

    document.getElementById('acceptTermsBtn')?.addEventListener('click', () => {
      this.acceptTerms();
    });
  }

  private closeTermsPopup(): void {
    const overlay = document.getElementById('termsOverlay');
    if (overlay) overlay.remove();
  }

  private attachListeners(): void {
    document.getElementById('mnrHamburgerBtn')?.addEventListener('click', () => {
      mnrSideDrawer.open();
    });

    document.getElementById('shareBtn')?.addEventListener('click', () => {
      this.handleShare();
    });
  }

  private async handleShare(): Promise<void> {
    const mnrId = this.data?.profile?.mnr_id || this.user?.id || '';
    const referralLink = `${PUBLIC_DOMAIN}/signup?ref=${mnrId}`;
    const message = `Join MNR Business Access Program using my referral link: ${referralLink}`;
    try {
      await Share.share({
        title: 'Join MNR Business Access Program',
        text: message,
        url: referralLink,
        dialogTitle: 'Share Referral Link'
      });
    } catch (error) {
      console.log('[MNRDashboard] Share failed, copying to clipboard');
      try {
        await Clipboard.write({ string: message });
        alert('Referral link copied to clipboard!');
      } catch (clipError) {
        console.error('[MNRDashboard] Clipboard write failed:', clipError);
        alert('Could not share or copy link');
      }
    }
  }

  private calculateDirectReferralRank(directCount: number): string {
    if (directCount >= 50) return 'Future Elite Master';
    if (directCount >= 25) return 'Super Platinum Star';
    if (directCount >= 15) return 'Super Elite Star';
    if (directCount >= 10) return 'Super Gold Star';
    if (directCount >= 8) return 'Super Silver Star';
    if (directCount >= 5) return 'Super Prime Star';
    if (directCount >= 1) return 'Super Star';
    return 'Yet to achieve';
  }

  private calculateMatchingReferralRank(matchingCount: number): string {
    const count = Math.round(matchingCount || 0);
    if (count >= 250000) return 'Crown Ambassador';
    if (count >= 50000) return 'Diamond';
    if (count >= 10000) return 'Emerald';
    if (count >= 5000) return 'Sapphire';
    if (count >= 300) return 'Ruby';
    if (count >= 250) return 'Pearl';
    if (count >= 120) return 'Platinum Star';
    if (count >= 50) return 'Super Star';
    if (count >= 35) return 'Gold Star';
    if (count >= 25) return 'Silver Star';
    if (count >= 3) return 'Prime Star';
    if (count >= 1) return 'Star';
    return 'Yet to achieve';
  }

  private updateContent(): void {
    const content = document.getElementById('dashboardContent');
    if (!content) return;

    if (this.loading) {
      content.innerHTML = '<div class="loading-state">Loading...</div>';
      return;
    }

    const profile = this.data?.profile || {} as ProfileData;
    const teamData = this.data?.team || { direct_referrals: 0, matching_referrals_count: 0, binary_tree: { left_count: 0, right_count: 0, total_count: 0 }, binary_tree_active: { left_count: 0, right_count: 0, total_count: 0 } } as TeamData;
    const activated = this.data?.activated || { direct_activated: 0, self_team_activated: 0 };
    const ved = this.data?.ved || { ved_team_total: 0, ved_team_activated: 0 };
    const previous = this.data?.previous_counts || { direct_referrals: 0, direct_activated: 0, my_team: 0, matching: 0, left_team: 0, left_active: 0, right_team: 0, right_active: 0, ved_overall: 0, ved_activated: 0 };

    content.innerHTML = `
      <!-- Birthday Banner -->
      ${this.renderBirthdayBanner()}

      <!-- Insurance Banner - DC Protocol Feb 2026 -->
      ${this.renderInsuranceBanner()}

      <!-- Active Banners Section -->
      ${this.renderBanners()}

      <!-- Latest Earners Section -->
      ${this.renderLatestEarners()}

      <!-- Personal Summary Section -->
      <div class="mnr-section-card personal-summary">
        <div class="section-header-bar green">
          <h3>PERSONAL SUMMARY</h3>
        </div>
        <div class="section-content">
          <div class="summary-row">
            <span class="label">Name:</span>
            <span class="value">${profile.name || this.user?.name || '-'}</span>
          </div>
          <div class="summary-row">
            <span class="label">Member Id:</span>
            <span class="value">${profile.mnr_id || this.user?.mnr_id || '-'}</span>
          </div>
          <div class="summary-row">
            <span class="label">Direct Connections Rank:</span>
            <span class="value badge-rank">${profile.direct_referral_rank || this.calculateDirectReferralRank(teamData.direct_referrals || 0)}</span>
          </div>
          <div class="summary-row">
            <span class="label">Group Performance Recognition Rank:</span>
            <span class="value badge-rank secondary">${profile.matching_referral_rank || this.calculateMatchingReferralRank(teamData.matching_referrals_count || 0)}</span>
          </div>
        </div>
      </div>

      <!-- My Summary Section -->
      <div class="mnr-section-card my-summary">
        <div class="section-header-bar orange">
          <h3>MY SUMMARY</h3>
        </div>
        <div class="section-content">
          <div class="summary-row">
            <span class="label">Registration Date:</span>
            <span class="value">${this.formatDate(profile.registration_date)}</span>
          </div>
          <div class="summary-row">
            <span class="label">Active Status:</span>
            <span class="value badge-status ${profile.active_status ? 'active' : 'inactive'}">${profile.active_status ? 'Activated' : 'Pending'}</span>
          </div>
          <div class="summary-row">
            <span class="label">Active Date:</span>
            <span class="value">${this.formatDate(profile.active_date)}</span>
          </div>
          <div class="summary-row">
            <span class="label">Package:</span>
            <span class="value">${profile.package || '-'}</span>
          </div>
        </div>
      </div>

      <!-- Overall Counts Section -->
      <div class="mnr-section-card overall-counts">
        <div class="section-header-bar purple">
          <h3>📊 Overall - Counts</h3>
        </div>
        <div class="section-content counts-grid">
          <div class="count-item">
            <span class="count-label">My Direct Connections:</span>
            <span class="count-value">${teamData.direct_referrals || 0}</span>
          </div>
          <div class="count-item">
            <span class="count-label">Active Direct:</span>
            <span class="count-value">${activated.direct_activated || 0}</span>
          </div>
          <div class="count-item">
            <span class="count-label">My Team:</span>
            <span class="count-value">${teamData.binary_tree?.total_count || 0}</span>
          </div>
          <div class="count-item">
            <span class="count-label">Group Performance Recognition:</span>
            <span class="count-value">${teamData.matching_referrals_count || 0}</span>
          </div>
          <div class="count-item">
            <span class="count-label">Group A Team:</span>
            <span class="count-value">${teamData.binary_tree?.left_count || 0}</span>
          </div>
          <div class="count-item">
            <span class="count-label">Group A Active:</span>
            <span class="count-value">${teamData.binary_tree_active?.left_count || 0}</span>
          </div>
          <div class="count-item">
            <span class="count-label">Group B Team:</span>
            <span class="count-value">${teamData.binary_tree?.right_count || 0}</span>
          </div>
          <div class="count-item">
            <span class="count-label">Group B Active:</span>
            <span class="count-value">${teamData.binary_tree_active?.right_count || 0}</span>
          </div>
          <div class="count-item">
            <span class="count-label">Ved Overall:</span>
            <span class="count-value">${ved.ved_team_total || 0}</span>
          </div>
          <div class="count-item">
            <span class="count-label">Ved Activated:</span>
            <span class="count-value">${ved.ved_team_activated || 0}</span>
          </div>
        </div>
      </div>

      <!-- Previous Counts Section -->
      <div class="mnr-section-card previous-counts">
        <div class="section-header-bar blue">
          <h3>📈 Previous - Counts</h3>
        </div>
        <div class="section-content counts-grid">
          <div class="count-item">
            <span class="count-label">My Direct Connections:</span>
            <span class="count-value">${previous.direct_referrals || 0}</span>
          </div>
          <div class="count-item">
            <span class="count-label">Active Direct:</span>
            <span class="count-value">${previous.direct_activated || 0}</span>
          </div>
          <div class="count-item">
            <span class="count-label">My Team:</span>
            <span class="count-value">${previous.my_team || 0}</span>
          </div>
          <div class="count-item">
            <span class="count-label">Group Performance Recognition:</span>
            <span class="count-value">${previous.matching || 0}</span>
          </div>
          <div class="count-item">
            <span class="count-label">Group A Team:</span>
            <span class="count-value">${previous.left_team || 0}</span>
          </div>
          <div class="count-item">
            <span class="count-label">Group A Active:</span>
            <span class="count-value">${previous.left_active || 0}</span>
          </div>
          <div class="count-item">
            <span class="count-label">Group B Team:</span>
            <span class="count-value">${previous.right_team || 0}</span>
          </div>
          <div class="count-item">
            <span class="count-label">Group B Active:</span>
            <span class="count-value">${previous.right_active || 0}</span>
          </div>
          <div class="count-item">
            <span class="count-label">Ved Overall:</span>
            <span class="count-value">${previous.ved_overall || 0}</span>
          </div>
          <div class="count-item">
            <span class="count-label">Ved Activated:</span>
            <span class="count-value">${previous.ved_activated || 0}</span>
          </div>
        </div>
      </div>

      <!-- Quick Actions -->
      <div class="quick-actions">
        <h3 class="section-title">Quick Actions</h3>
        <div class="action-grid">
          <button class="action-btn" data-page="mnr-income">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
            </svg>
            <span>Income</span>
          </button>
          <button class="action-btn" data-page="mnr-withdrawals">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="1" y="4" width="22" height="16" rx="2" ry="2"/><line x1="1" y1="10" x2="23" y2="10"/>
            </svg>
            <span>Withdraw</span>
          </button>
          <button class="action-btn" data-page="mnr-benefits">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="8" r="7"/><polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"/>
            </svg>
            <span>Benefits</span>
          </button>
          <button class="action-btn" data-page="mnr-announcements">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/>
            </svg>
            <span>News</span>
          </button>
        </div>
      </div>
    `;

    content.querySelectorAll('[data-page]').forEach(btn => {
      btn.addEventListener('click', () => {
        const page = btn.getAttribute('data-page');
        if (page) routerService.navigate(page as any);
      });
    });
  }

  private renderBirthdayBanner(): string {
    if (!this.isBirthday) return '';
    const name = this.data?.profile?.name || this.user?.name || 'Member';
    return `
      <div class="birthday-banner">
        <h3>🎂 Happy Birthday, ${name}! 🎉</h3>
        <p>Wishing you a wonderful day filled with joy and success!</p>
      </div>
    `;
  }

  private renderInsuranceBanner(): string {
    if (!this.insuranceStatus || !this.insuranceStatus.show_banner || this.bannerDismissed) return '';
    
    const s = this.insuranceStatus;
    const kycBadge = s.kyc_approved
      ? '<span style="background:#059669;padding:2px 8px;border-radius:8px;font-size:10px;font-weight:600;color:white;">KYC Approved</span>'
      : '<span style="background:#dc2626;padding:2px 8px;border-radius:8px;font-size:10px;font-weight:600;color:white;">KYC: ' + (s.kyc_status || 'Pending') + '</span>';
    
    const kycAction = s.kyc_approved ? '' :
      '<div style="margin-top:10px;padding:8px 12px;background:rgba(255,255,255,0.15);border-radius:8px;border:1px solid rgba(255,255,255,0.3);font-size:12px;">' +
      '⚠️ <strong>Complete your KYC</strong> to get your insurance processed.' +
      '</div>';
    
    const dismissBtns = '<div style="position:absolute;top:8px;right:8px;">' +
      '<button class="ins-banner-close" style="background:rgba(255,255,255,0.2);border:none;color:white;width:24px;height:24px;border-radius:50%;font-size:12px;cursor:pointer;">✕</button>' +
      '</div>' +
      '<div style="text-align:right;margin-top:6px;">' +
      '<a href="javascript:void(0)" class="ins-banner-dismiss-permanent" style="color:rgba(255,255,255,0.6);font-size:10px;text-decoration:underline;">Don\'t show again</a>' +
      '</div>';
    
    let body = '';
    let cls = '';
    
    if (s.banner_type === 'insured') {
      cls = 'insured';
      body = '<div class="insurance-icon">🛡️</div>' +
        '<h4>You are Insured! ' + kycBadge + '</h4>' +
        '<p>Rs. 5,00,000 Accidental Insurance Coverage</p>' +
        '<p class="policy-details"><strong>Policy:</strong> ' + (s.policy_number || 'N/A') + ' | <strong>Valid until:</strong> ' + (s.expiry_date || 'N/A') + ' (' + (s.days_remaining || 0) + ' days remaining)</p>';
    } else if (s.banner_type === 'eligible') {
      cls = 'eligible';
      body = '<div class="insurance-icon">✓</div>' +
        '<h4>You are Eligible for Insurance! ' + kycBadge + '</h4>' +
        '<p>Rs. 5,00,000 Accidental Insurance - Your insurance is being processed</p>' +
        kycAction;
    } else if (s.banner_type === 'referral_required') {
      cls = 'service-required';
      const ga = s.group_a_referrals || 0;
      const gb = s.group_b_referrals || 0;
      const progress = s.referrals_count || 0;
      const needed = s.referrals_needed || 2;
      body = '<div class="insurance-icon">👥</div>' +
        '<h4>Unlock Free Insurance! ' + kycBadge + '</h4>' +
        '<p>Get Rs. 5,00,000 Accidental Insurance by referring 2 members who activate after Feb 3, 2026</p>' +
        '<div style="display:flex;justify-content:center;gap:16px;margin:10px 0;">' +
          '<div style="background:rgba(255,255,255,0.15);padding:8px 16px;border-radius:8px;min-width:90px;">' +
            '<div style="font-size:20px;font-weight:700;">' + ga + '</div>' +
            '<div style="font-size:10px;opacity:0.85;">Group A</div>' +
          '</div>' +
          '<div style="background:rgba(255,255,255,0.15);padding:8px 16px;border-radius:8px;min-width:90px;">' +
            '<div style="font-size:20px;font-weight:700;">' + gb + '</div>' +
            '<div style="font-size:10px;opacity:0.85;">Group B</div>' +
          '</div>' +
        '</div>' +
        '<p style="font-size:12px;"><strong>Total:</strong> ' + progress + ' / ' + needed + ' referrals</p>' +
        '<div style="background:rgba(255,255,255,0.3);border-radius:20px;height:8px;margin:6px auto;max-width:200px;">' +
          '<div style="background:white;border-radius:20px;height:100%;width:' + Math.min(100, (progress / needed * 100)) + '%;"></div>' +
        '</div>' +
        kycAction;
    } else if (s.banner_type === 'not_activated') {
      cls = 'service-required';
      body = '<div class="insurance-icon">ℹ️</div>' +
        '<h4>Activate Your Membership ' + kycBadge + '</h4>' +
        '<p>Activate your membership to unlock Rs. 5,00,000 Accidental Insurance and other benefits</p>' +
        kycAction;
    } else if (s.banner_type === 'service_required') {
      cls = 'service-required';
      body = '<div class="insurance-icon">⚡</div>' +
        '<h4>Unlock Free Insurance! ' + kycBadge + '</h4>' +
        '<p>Get Rs. 5,00,000 Accidental Insurance by using your points for Solar, EV, Real Dreams, or Care services</p>' +
        kycAction;
    } else {
      return '';
    }
    
    return '<div class="insurance-banner ' + cls + '" style="position:relative;" id="mobileInsuranceBanner">' + dismissBtns + body + '</div>';
  }
  
  private setupBannerDismiss(): void {
    const closeBtn = this.container.querySelector('.ins-banner-close');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => {
        const banner = document.getElementById('mobileInsuranceBanner');
        if (banner) banner.style.display = 'none';
      });
    }
    const permBtn = this.container.querySelector('.ins-banner-dismiss-permanent');
    if (permBtn) {
      permBtn.addEventListener('click', async () => {
        await Preferences.set({ key: 'mnr_banner_dismissed', value: 'true' });
        this.bannerDismissed = true;
        const banner = document.getElementById('mobileInsuranceBanner');
        if (banner) banner.style.display = 'none';
      });
    }
  }

  private renderBanners(): string {
    if (!this.banners || this.banners.length === 0) return '';

    return `
      <div class="mnr-banner-section">
        ${this.banners.map(banner => {
          let imgSrc = '';
          if (banner.image_content) {
            imgSrc = banner.image_content.startsWith('data:') ? banner.image_content :
              (banner.image_content.startsWith('/') ? banner.image_content : '/storage/' + banner.image_content);
          } else if (banner.image_url) {
            imgSrc = banner.image_url;
          }
          return `
            <div class="mnr-banner-slide">
              ${imgSrc
                ? `<img src="${imgSrc}" alt="${banner.title || 'Banner'}" style="max-width: 100%; max-height: 300px; border-radius: 8px; object-fit: contain;" />`
                : ''
              }
              ${banner.text_content ? `<div style="padding: 8px; color: white; font-weight: 500; font-size: 13px;">${banner.text_content}</div>` : ''}
              ${!imgSrc && !banner.text_content ? `<h4>${banner.title}</h4>` : ''}
            </div>
          `;
        }).join('')}
      </div>
    `;
  }

  private renderLatestEarners(): string {
    if (!this.latestEarners || this.latestEarners.length === 0) return '';

    return `
      <div class="latest-earners-section">
        <div class="latest-earners-header">
          <span>🏆</span>
          <h3>Top Performers - Recognition Achievers</h3>
        </div>
        <div class="earners-carousel">
          ${this.latestEarners.slice(0, 10).map((earner, index) => `
            <div class="earner-card">
              <div class="earner-medal">${index === 0 ? '🥇' : index === 1 ? '🥈' : index === 2 ? '🥉' : '🏅'}</div>
              <div class="earner-avatar">${this.getInitials(earner.name)}</div>
              <div class="earner-name">${earner.name}</div>
              <div class="earner-id">${earner.mnr_id}</div>
              <div class="earner-amount">₹${earner.amount.toLocaleString()}</div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  private formatDate(dateStr: string | undefined): string {
    if (!dateStr) return '-';
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString('en-IN', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return dateStr;
    }
  }

  private getInitials(name: string): string {
    return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
  }
}
