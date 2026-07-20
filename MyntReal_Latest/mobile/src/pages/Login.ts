/**
 * Login Page Component
 * DC Protocol: DC_MOBILE_LOGIN_001
 * Multi-portal support: Staff (MyntReal), MNR, Partner
 * Announcements tab with public announcements - full features
 */

import { authService } from '../services/auth.service';
import { portalService, PortalType } from '../services/portal.service';
import { apiService } from '../services/api.service';
import { APP_CONFIG } from '../config/app.config';

interface Announcement {
  id: number;
  title: string;
  description: string;
  category?: { name: string };
  media?: Array<{
    file_path: string;
    file_type: string;
    media_type: string;
    thumbnail_url?: string;
  }>;
  submission_type: string;
  approved_at?: string;
  updated_at?: string;
  created_at?: string;
  user_name?: string;
  city?: string;
  average_rating?: number;
  total_ratings?: number;
  shares_count?: number;
}

type ActiveTab = 'login' | 'announcements';

export class LoginPage {
  private container: HTMLElement;
  private hasBiometric: boolean = false;
  private biometricType: string = 'Biometric';
  private hasStoredCredentials: boolean = false;
  private selectedPortal: PortalType = 'staff';
  private activeTab: ActiveTab = 'login';
  private announcements: Announcement[] = [];
  private currentAnnouncementIndex: number = 0;
  private announcementInterval: ReturnType<typeof setInterval> | null = null;
  private selectedAnnouncementForDetail: Announcement | null = null;
  private devModeTapCount: number = 0;
  private devModeTapTimer: ReturnType<typeof setTimeout> | null = null;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  cleanup(): void {
    this.stopAnnouncementRotation();
    if (this.devModeTapTimer) {
      clearTimeout(this.devModeTapTimer);
      this.devModeTapTimer = null;
    }
  }

  async init(): Promise<void> {
    await portalService.init();
    this.selectedPortal = portalService.getPortal();
    
    const biometric = await authService.checkBiometricAvailability();
    this.hasBiometric = biometric.available;
    this.biometricType = biometric.type;
    this.hasStoredCredentials = await authService.hasStoredCredentialsForPortal(this.selectedPortal);
    
    this.injectStyles();
    this.render();
    this.attachEventListeners();
    
    this.loadAnnouncements();
  }

  private injectStyles(): void {
    if (document.getElementById('login-page-styles')) return;
    
    const styles = document.createElement('style');
    styles.id = 'login-page-styles';
    styles.textContent = `
      .login-container {
        min-height: 100vh;
        padding: 20px;
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
      }
      
      .login-header {
        text-align: center;
        padding: 20px 0;
      }
      
      .login-header .logo {
        margin-bottom: 12px;
      }
      
      .header-logo {
        border-radius: 16px;
        box-shadow: 0 4px 20px rgba(46, 204, 113, 0.3);
        background: transparent;
      }
      
      .app-title {
        font-size: 1.75rem;
        font-weight: 700;
        color: #ffffff;
        margin: 0 0 4px 0;
      }
      
      .app-subtitle {
        font-size: 0.9rem;
        color: rgba(255, 255, 255, 0.7);
        margin: 0;
      }
      
      .main-tabs {
        display: flex;
        gap: 8px;
        margin-bottom: 20px;
        background: rgba(255, 255, 255, 0.05);
        padding: 6px;
        border-radius: 12px;
      }
      
      .main-tab {
        flex: 1;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
        padding: 12px;
        border: none;
        background: transparent;
        color: rgba(255, 255, 255, 0.6);
        font-size: 0.9rem;
        font-weight: 500;
        border-radius: 8px;
        cursor: pointer;
        transition: all 0.3s ease;
      }
      
      .main-tab.active {
        background: linear-gradient(135deg, #2ECC71 0%, #27ae60 100%);
        color: white;
        box-shadow: 0 4px 15px rgba(46, 204, 113, 0.4);
      }
      
      .main-tab svg {
        width: 18px;
        height: 18px;
      }
      
      .portal-tabs {
        display: flex;
        gap: 10px;
        margin-bottom: 20px;
      }
      
      .portal-tab {
        flex: 1;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 8px;
        padding: 16px 8px;
        border: 2px solid rgba(255, 255, 255, 0.1);
        background: rgba(255, 255, 255, 0.05);
        color: rgba(255, 255, 255, 0.7);
        font-size: 0.8rem;
        font-weight: 500;
        border-radius: 12px;
        cursor: pointer;
        transition: all 0.3s ease;
      }
      
      .portal-tab:hover {
        border-color: rgba(46, 204, 113, 0.5);
        background: rgba(46, 204, 113, 0.1);
      }
      
      .portal-tab.active {
        border-color: #2ECC71;
        background: rgba(46, 204, 113, 0.15);
        color: #2ECC71;
      }
      
      .portal-logo {
        width: 40px;
        height: 40px;
        object-fit: contain;
        border-radius: 8px;
        background: transparent;
      }
      
      .login-form.card, .announcements-container.card {
        background: rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 24px;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
      }
      
      .announcements-container {
        max-height: calc(100vh - 280px);
        overflow-y: auto;
      }
      
      .announcements-loading, .announcements-empty {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 40px 20px;
        color: rgba(255, 255, 255, 0.6);
        text-align: center;
      }
      
      .announcements-loading .spinner {
        animation: spin 1s linear infinite;
        margin-bottom: 12px;
      }
      
      @keyframes spin {
        to { transform: rotate(360deg); }
      }
      
      .announcement-slide {
        animation: fadeIn 0.3s ease;
      }
      
      @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
      }
      
      .announcement-media {
        position: relative;
        margin-bottom: 16px;
        border-radius: 12px;
        overflow: hidden;
        background: rgba(0, 0, 0, 0.3);
      }
      
      .announcement-media img, .announcement-media video {
        width: 100%;
        max-height: 220px;
        object-fit: cover;
        display: block;
      }
      
      .announcement-text-badge {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 30px;
        background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
        border: 2px dashed #f59e0b;
        color: #92400e;
      }
      
      .announcement-text-badge svg {
        margin-bottom: 8px;
        stroke: #f97316;
      }
      
      .announcement-text-badge span {
        font-weight: 600;
        font-size: 0.85rem;
      }
      
      .media-count {
        position: absolute;
        top: 8px;
        right: 8px;
        background: rgba(0, 0, 0, 0.7);
        color: white;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.75rem;
        display: flex;
        align-items: center;
        gap: 4px;
      }
      
      .announcement-details {
        color: white;
      }
      
      .announcement-header-row {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 8px;
      }
      
      .announcement-title {
        font-size: 1.1rem;
        font-weight: 600;
        margin: 0;
        color: white;
        flex: 1;
      }
      
      .announcement-date {
        font-size: 0.75rem;
        color: rgba(255, 255, 255, 0.5);
        white-space: nowrap;
        margin-left: 12px;
      }
      
      .announcement-author {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 0.8rem;
        color: rgba(255, 255, 255, 0.6);
        margin: 0 0 10px 0;
      }
      
      .announcement-author svg {
        width: 14px;
        height: 14px;
        opacity: 0.7;
      }
      
      .announcement-description {
        font-size: 0.9rem;
        color: rgba(255, 255, 255, 0.8);
        line-height: 1.5;
        margin: 0 0 12px 0;
      }
      
      .announcement-category {
        display: inline-block;
        background: rgba(245, 158, 11, 0.2);
        color: #fbbf24;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 500;
        margin-bottom: 12px;
      }
      
      .announcement-rating {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 12px;
      }
      
      .announcement-rating .stars {
        color: #fbbf24;
        font-size: 1rem;
        letter-spacing: 2px;
      }
      
      .announcement-rating .rating-count {
        font-size: 0.75rem;
        color: rgba(255, 255, 255, 0.5);
      }
      
      .rate-section {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 16px;
        padding: 12px;
        background: rgba(255, 255, 255, 0.05);
        border-radius: 8px;
      }
      
      .rate-label {
        font-size: 0.8rem;
        color: rgba(255, 255, 255, 0.6);
      }
      
      .rate-stars {
        display: flex;
        gap: 4px;
      }
      
      .rate-star {
        font-size: 1.5rem;
        color: rgba(255, 255, 255, 0.3);
        cursor: pointer;
        transition: all 0.2s ease;
        padding: 0;
        background: none;
        border: none;
      }
      
      .rate-star:hover, .rate-star.highlighted {
        color: #fbbf24;
        transform: scale(1.2);
      }
      
      .announcement-actions {
        display: flex;
        gap: 10px;
        margin-top: 12px;
      }
      
      .action-btn {
        flex: 1;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
        padding: 10px 16px;
        border: 1px solid rgba(255, 255, 255, 0.2);
        background: rgba(255, 255, 255, 0.05);
        color: white;
        font-size: 0.85rem;
        font-weight: 500;
        border-radius: 8px;
        cursor: pointer;
        transition: all 0.3s ease;
      }
      
      .action-btn:hover {
        background: rgba(46, 204, 113, 0.2);
        border-color: #2ECC71;
      }
      
      .action-btn svg {
        width: 16px;
        height: 16px;
      }
      
      .announcement-nav {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 16px;
        margin-top: 20px;
        padding-top: 16px;
        border-top: 1px solid rgba(255, 255, 255, 0.1);
      }
      
      .nav-btn {
        width: 40px;
        height: 40px;
        display: flex;
        align-items: center;
        justify-content: center;
        border: none;
        background: rgba(255, 255, 255, 0.1);
        color: white;
        border-radius: 50%;
        cursor: pointer;
        transition: all 0.3s ease;
      }
      
      .nav-btn:hover {
        background: #2ECC71;
      }
      
      .announcement-dots {
        display: flex;
        gap: 8px;
      }
      
      .dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.3);
        cursor: pointer;
        transition: all 0.3s ease;
      }
      
      .dot.active {
        background: #2ECC71;
        width: 24px;
        border-radius: 4px;
      }
      
      .login-footer {
        text-align: center;
        padding: 20px;
      }
      
      .login-footer .version {
        font-size: 0.85rem;
        color: rgba(100, 255, 218, 0.8);
        margin: 0;
        font-weight: 600;
      }
      .login-footer .build-date {
        font-size: 0.7rem;
        color: rgba(255, 255, 255, 0.4);
        margin: 4px 0 0 0;
      }
      .login-footer .dev-mode-badge {
        font-size: 0.7rem;
        color: #ff6b6b;
        background: rgba(255, 107, 107, 0.2);
        padding: 4px 12px;
        border-radius: 12px;
        margin: 8px auto 0;
        display: inline-block;
        font-weight: 600;
      }
      
      .detail-modal {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.9);
        z-index: 1000;
        display: flex;
        flex-direction: column;
        overflow-y: auto;
      }
      
      .detail-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 16px 20px;
        background: rgba(255, 255, 255, 0.05);
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
      }
      
      .detail-header h2 {
        font-size: 1.1rem;
        font-weight: 600;
        color: white;
        margin: 0;
      }
      
      .close-btn {
        width: 36px;
        height: 36px;
        display: flex;
        align-items: center;
        justify-content: center;
        border: none;
        background: rgba(255, 255, 255, 0.1);
        color: white;
        border-radius: 50%;
        cursor: pointer;
      }
      
      .detail-content {
        flex: 1;
        padding: 20px;
      }
      
      .detail-media-carousel {
        margin-bottom: 20px;
      }
      
      .detail-media-item {
        border-radius: 12px;
        overflow: hidden;
        background: #000;
      }
      
      .detail-media-item img, .detail-media-item video {
        width: 100%;
        max-height: 300px;
        object-fit: contain;
      }
      
      .media-nav {
        display: flex;
        justify-content: center;
        gap: 8px;
        margin-top: 12px;
      }
      
      .media-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.3);
        cursor: pointer;
      }
      
      .media-dot.active {
        background: #2ECC71;
      }
      
      .share-modal {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.8);
        z-index: 1100;
        display: flex;
        align-items: flex-end;
        justify-content: center;
      }
      
      .share-content {
        background: #1a1a2e;
        border-radius: 20px 20px 0 0;
        padding: 24px;
        width: 100%;
        max-width: 400px;
      }
      
      .share-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: white;
        margin: 0 0 20px 0;
        text-align: center;
      }
      
      .share-options {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 16px;
      }
      
      .share-option {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 8px;
        padding: 16px 8px;
        border: none;
        background: rgba(255, 255, 255, 0.05);
        color: white;
        border-radius: 12px;
        cursor: pointer;
        transition: all 0.3s ease;
      }
      
      .share-option:hover {
        background: rgba(46, 204, 113, 0.2);
      }
      
      .share-option svg {
        width: 24px;
        height: 24px;
      }
      
      .share-option span {
        font-size: 0.7rem;
      }
      
      .share-cancel {
        width: 100%;
        padding: 14px;
        margin-top: 16px;
        border: none;
        background: rgba(255, 255, 255, 0.1);
        color: white;
        font-size: 0.95rem;
        font-weight: 500;
        border-radius: 12px;
        cursor: pointer;
      }
    `;
    document.head.appendChild(styles);
  }

  private async loadAnnouncements(): Promise<void> {
    try {
      // DC Protocol: Use apiService for proper API base URL handling in mobile context
      const response = await apiService.getPublic<any>('/feedback/public/announcements?limit=10');
      if (response.success && response.data) {
        this.announcements = response.data.items || response.data || [];
        if (this.activeTab === 'announcements') {
          this.renderAnnouncementsContent();
        }
      }
    } catch (error) {
      console.error('Failed to load announcements:', error);
    }
  }

  private getPortalConfig() {
    return portalService.portals[this.selectedPortal];
  }

  private getPortalLogo(portal: PortalType): string {
    if (portal === 'mnr') {
      return `<img src="/assets/mnr-logo.png" alt="MNR" class="portal-logo">`;
    }
    return `<img src="/assets/myntreal-logo.png" alt="MyntReal" class="portal-logo">`;
  }

  private getHeaderLogo(): string {
    if (this.activeTab === 'announcements' || this.selectedPortal === 'mnr') {
      return `<img src="/assets/mnr-logo.png" alt="MNR" class="header-logo" style="width: 80px; height: 80px; object-fit: contain;">`;
    }
    return `<img src="/assets/myntreal-logo.png" alt="MyntReal" class="header-logo" style="width: 80px; height: 80px; object-fit: contain;">`;
  }

  private getHeaderTitle(): string {
    if (this.activeTab === 'announcements') {
      return 'MNR Announcements';
    }
    if (this.selectedPortal === 'mnr') {
      return 'MNR Business Access';
    }
    return 'MyntReal';
  }

  private render(): void {
    const config = this.getPortalConfig();
    
    this.container.innerHTML = `
      <div class="login-container">
        <div class="login-header">
          <div class="logo">
            ${this.getHeaderLogo()}
          </div>
          <h1 class="app-title">${this.getHeaderTitle()}</h1>
          <p class="app-subtitle">${this.activeTab === 'login' ? 'Select Portal' : 'Recent Updates'}</p>
        </div>

        <div class="main-tabs">
          <button class="main-tab ${this.activeTab === 'login' ? 'active' : ''}" data-main-tab="login">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/>
              <polyline points="10 17 15 12 10 7"/>
              <line x1="15" y1="12" x2="3" y2="12"/>
            </svg>
            <span>Login</span>
          </button>
          <button class="main-tab ${this.activeTab === 'announcements' ? 'active' : ''}" data-main-tab="announcements">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M22 17H2a3 3 0 0 0 3-3V9a7 7 0 0 1 14 0v5a3 3 0 0 0 3 3zm-8.27 4a2 2 0 0 1-3.46 0"/>
            </svg>
            <span>Announcements</span>
          </button>
        </div>

        ${this.activeTab === 'login' ? this.renderLoginContent(config) : this.renderAnnouncementsTab()}

        <div class="login-footer">
          <p class="version" id="versionTap">${APP_CONFIG.getVersionString()}</p>
          <p class="build-date">Build: ${APP_CONFIG.BUILD_DATE}</p>
          ${APP_CONFIG.isDevMode() ? '<p class="dev-mode-badge">DEV SERVER</p>' : ''}
        </div>
      </div>
    `;
  }

  private renderLoginContent(config: any): string {
    return `
      <div class="portal-tabs">
        <button class="portal-tab ${this.selectedPortal === 'staff' ? 'active' : ''}" data-portal="staff">
          ${this.getPortalLogo('staff')}
          <span>MyntReal</span>
        </button>
        <button class="portal-tab ${this.selectedPortal === 'mnr' ? 'active' : ''}" data-portal="mnr">
          ${this.getPortalLogo('mnr')}
          <span>MNR</span>
        </button>
        <button class="portal-tab ${this.selectedPortal === 'partner' ? 'active' : ''}" data-portal="partner">
          ${this.getPortalLogo('partner')}
          <span>Partner</span>
        </button>
      </div>

      <div class="login-form card">
        <div class="input-group">
          <label class="input-label">${config.idLabel}</label>
          <input 
            type="text" 
            id="userId" 
            class="input" 
            placeholder="${config.idPlaceholder}"
            autocapitalize="characters"
            autocomplete="username"
          />
        </div>

        <div class="input-group">
          <label class="input-label">Password</label>
          <div class="password-wrapper">
            <input 
              type="password" 
              id="password" 
              class="input" 
              placeholder="Enter your password"
              autocomplete="current-password"
            />
            <button type="button" id="togglePassword" class="password-toggle">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                <circle cx="12" cy="12" r="3"/>
              </svg>
            </button>
          </div>
        </div>

        <div id="errorMessage" class="error-message" style="display: none;"></div>

        <button id="loginBtn" class="btn btn-primary btn-full btn-lg">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/>
            <polyline points="10 17 15 12 10 7"/>
            <line x1="15" y1="12" x2="3" y2="12"/>
          </svg>
          Login to ${config.name}
        </button>

        ${this.hasBiometric && this.hasStoredCredentials ? `
          <div class="divider">
            <span>or</span>
          </div>
          
          <button id="biometricBtn" class="btn btn-outline btn-full">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z"/>
              <path d="M12 6v6l4 2"/>
            </svg>
            Login with ${this.biometricType}
          </button>
        ` : ''}

        ${this.hasBiometric && !this.hasStoredCredentials ? `
          <div class="biometric-setup">
            <label class="checkbox-label">
              <input type="checkbox" id="enableBiometric" checked />
              <span>Enable ${this.biometricType} for future logins</span>
            </label>
          </div>
        ` : ''}
      </div>
    `;
  }

  private renderAnnouncementsTab(): string {
    return `
      <div class="announcements-container card">
        <div id="announcementsContent" class="announcements-content">
          <div class="announcements-loading">
            <svg class="spinner" width="32" height="32" viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="3" stroke-dasharray="30 70"/>
            </svg>
            <p>Loading announcements...</p>
          </div>
        </div>
      </div>
    `;
  }

  private renderAnnouncementsContent(): void {
    const container = document.getElementById('announcementsContent');
    if (!container) return;

    if (this.announcements.length === 0) {
      container.innerHTML = `
        <div class="announcements-empty">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M22 17H2a3 3 0 0 0 3-3V9a7 7 0 0 1 14 0v5a3 3 0 0 0 3 3zm-8.27 4a2 2 0 0 1-3.46 0"/>
          </svg>
          <p>No announcements at this time</p>
        </div>
      `;
      return;
    }

    const announcement = this.announcements[this.currentAnnouncementIndex];
    const mediaHtml = this.renderAnnouncementMedia(announcement);
    const date = new Date(announcement.approved_at || announcement.updated_at || announcement.created_at || '').toLocaleDateString('en-US', {
      month: 'short', day: 'numeric', year: 'numeric'
    });

    container.innerHTML = `
      <div class="announcement-slide">
        ${mediaHtml}
        <div class="announcement-details">
          <div class="announcement-header-row">
            <h3 class="announcement-title">${this.escapeHtml(announcement.title || 'Announcement')}</h3>
            <span class="announcement-date">${date}</span>
          </div>
          ${announcement.user_name ? `
            <p class="announcement-author">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                <circle cx="12" cy="7" r="4"/>
              </svg>
              ${this.escapeHtml(announcement.user_name)}
              ${announcement.city ? ` - ${this.escapeHtml(announcement.city)}` : ''}
            </p>
          ` : ''}
          <p class="announcement-description">${this.escapeHtml((announcement.description || '').substring(0, 150))}${(announcement.description || '').length > 150 ? '...' : ''}</p>
          ${announcement.category?.name ? `
            <span class="announcement-category">${this.escapeHtml(announcement.category.name)}</span>
          ` : ''}
          ${announcement.average_rating ? `
            <div class="announcement-rating">
              <span class="stars">${'★'.repeat(Math.round(announcement.average_rating))}${'☆'.repeat(5 - Math.round(announcement.average_rating))}</span>
              <span class="rating-count">(${announcement.total_ratings || 0} ratings)</span>
            </div>
          ` : ''}
          
          <div class="rate-section">
            <span class="rate-label">Rate:</span>
            <div class="rate-stars">
              ${[1,2,3,4,5].map(i => `
                <button class="rate-star" data-rating="${i}" data-announcement-id="${announcement.id}">☆</button>
              `).join('')}
            </div>
          </div>
          
          <div class="announcement-actions">
            <button class="action-btn" id="viewBtn" data-id="${announcement.id}">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                <circle cx="12" cy="12" r="3"/>
              </svg>
              View
            </button>
            <button class="action-btn" id="shareBtn" data-id="${announcement.id}" data-title="${this.escapeHtml(announcement.title || '')}">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="18" cy="5" r="3"/>
                <circle cx="6" cy="12" r="3"/>
                <circle cx="18" cy="19" r="3"/>
                <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/>
                <line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>
              </svg>
              Share${announcement.shares_count ? ` (${announcement.shares_count})` : ''}
            </button>
          </div>
        </div>
      </div>

      ${this.announcements.length > 1 ? `
        <div class="announcement-nav">
          <button class="nav-btn nav-prev" id="prevAnnouncement">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="15 18 9 12 15 6"/>
            </svg>
          </button>
          <div class="announcement-dots">
            ${this.announcements.map((_, i) => `
              <span class="dot ${i === this.currentAnnouncementIndex ? 'active' : ''}" data-index="${i}"></span>
            `).join('')}
          </div>
          <button class="nav-btn nav-next" id="nextAnnouncement">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="9 18 15 12 9 6"/>
            </svg>
          </button>
        </div>
      ` : ''}
    `;

    this.attachAnnouncementListeners();
    this.startAnnouncementRotation();
  }

  private getMediaUrl(filePath: string): string {
    if (!filePath) return '';
    if (filePath.startsWith('http://') || filePath.startsWith('https://')) return filePath;
    // DC Protocol: Use centralized configuration from APP_CONFIG
    return `${APP_CONFIG.MEDIA_BASE_URL}${filePath.startsWith('/') ? '' : '/'}${filePath}`;
  }

  private renderAnnouncementMedia(announcement: Announcement): string {
    if (!announcement.media || announcement.media.length === 0) {
      if (announcement.submission_type === 'text') {
        return `
          <div class="announcement-media announcement-text-badge">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
              <line x1="16" y1="17" x2="8" y2="17"/>
            </svg>
            <span>Text Announcement</span>
          </div>
        `;
      }
      return '';
    }

    const media = announcement.media[0];
    const isVideo = media.file_type && media.file_type.startsWith('video/');
    const mediaCount = announcement.media.length;
    const countBadge = mediaCount > 1 ? `<span class="media-count"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg> ${mediaCount}</span>` : '';

    const mediaUrl = this.getMediaUrl(media.file_path);

    if (isVideo) {
      const videoUrl = mediaUrl + (mediaUrl.includes('#') ? '' : '#t=0.001');
      const posterAttr = media.thumbnail_url ? ` poster="${this.escapeHtml(media.thumbnail_url)}"` : '';
      const preloadVal = media.thumbnail_url ? 'none' : 'metadata';
      return `
        <div class="announcement-media">
          <video controls playsinline muted preload="${preloadVal}"${posterAttr}>
            <source src="${this.escapeHtml(videoUrl)}" type="${media.file_type || 'video/mp4'}">
          </video>
          ${countBadge}
        </div>
      `;
    }

    return `
      <div class="announcement-media">
        <img src="${this.escapeHtml(mediaUrl)}" alt="${this.escapeHtml(announcement.title || '')}" 
             loading="lazy" onerror="this.style.display='none'">
        ${countBadge}
      </div>
    `;
  }

  private attachAnnouncementListeners(): void {
    const prevBtn = document.getElementById('prevAnnouncement');
    const nextBtn = document.getElementById('nextAnnouncement');
    const viewBtn = document.getElementById('viewBtn');
    const shareBtn = document.getElementById('shareBtn');

    prevBtn?.addEventListener('click', () => {
      this.stopAnnouncementRotation();
      this.currentAnnouncementIndex = (this.currentAnnouncementIndex - 1 + this.announcements.length) % this.announcements.length;
      this.renderAnnouncementsContent();
    });

    nextBtn?.addEventListener('click', () => {
      this.stopAnnouncementRotation();
      this.currentAnnouncementIndex = (this.currentAnnouncementIndex + 1) % this.announcements.length;
      this.renderAnnouncementsContent();
    });

    document.querySelectorAll('.announcement-dots .dot').forEach(dot => {
      dot.addEventListener('click', () => {
        this.stopAnnouncementRotation();
        this.currentAnnouncementIndex = parseInt(dot.getAttribute('data-index') || '0');
        this.renderAnnouncementsContent();
      });
    });

    document.querySelectorAll('.rate-star').forEach(star => {
      star.addEventListener('mouseenter', () => {
        const rating = parseInt(star.getAttribute('data-rating') || '0');
        this.highlightStars(rating);
      });
      
      star.addEventListener('mouseleave', () => {
        this.resetStars();
      });
      
      star.addEventListener('click', () => {
        const rating = parseInt(star.getAttribute('data-rating') || '0');
        const announcementId = star.getAttribute('data-announcement-id');
        this.showRatingLoginPrompt(parseInt(announcementId || '0'), rating);
      });
    });

    viewBtn?.addEventListener('click', () => {
      const announcement = this.announcements[this.currentAnnouncementIndex];
      if (announcement) {
        this.showAnnouncementDetail(announcement);
      }
    });

    shareBtn?.addEventListener('click', () => {
      const announcement = this.announcements[this.currentAnnouncementIndex];
      if (announcement) {
        this.showShareModal(announcement);
      }
    });
  }

  private highlightStars(rating: number): void {
    document.querySelectorAll('.rate-star').forEach((star, index) => {
      if (index < rating) {
        star.textContent = '★';
        star.classList.add('highlighted');
      } else {
        star.textContent = '☆';
        star.classList.remove('highlighted');
      }
    });
  }

  private resetStars(): void {
    document.querySelectorAll('.rate-star').forEach(star => {
      star.textContent = '☆';
      star.classList.remove('highlighted');
    });
  }

  private pendingRating: { announcementId: number; rating: number } | null = null;

  private showRatingLoginPrompt(announcementId: number, rating: number): void {
    this.pendingRating = { announcementId, rating };
    this.stopAnnouncementRotation();
    this.activeTab = 'login';
    this.render();
    this.attachEventListeners();
    const errorEl = document.getElementById('errorMessage');
    if (errorEl) {
      errorEl.textContent = `Please login to submit your ${rating}-star rating`;
      errorEl.style.display = 'block';
      errorEl.style.color = '#2ECC71';
      errorEl.style.background = 'rgba(46, 204, 113, 0.1)';
    }
  }

  private showAnnouncementDetail(announcement: Announcement): void {
    this.stopAnnouncementRotation();
    
    const modal = document.createElement('div');
    modal.className = 'detail-modal';
    modal.id = 'announcementDetailModal';
    
    const mediaHtml = this.renderDetailMedia(announcement);
    const date = new Date(announcement.approved_at || announcement.updated_at || announcement.created_at || '').toLocaleDateString('en-US', {
      weekday: 'long', month: 'long', day: 'numeric', year: 'numeric'
    });

    modal.innerHTML = `
      <div class="detail-header">
        <h2>Announcement</h2>
        <button class="close-btn" id="closeDetailModal">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"/>
            <line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>
      <div class="detail-content">
        ${mediaHtml}
        <h3 style="color: white; font-size: 1.3rem; margin: 0 0 8px 0;">${this.escapeHtml(announcement.title || 'Announcement')}</h3>
        <p style="color: rgba(255,255,255,0.5); font-size: 0.85rem; margin: 0 0 16px 0;">${date}</p>
        ${announcement.user_name ? `
          <p style="color: rgba(255,255,255,0.7); font-size: 0.9rem; margin: 0 0 16px 0;">
            By ${this.escapeHtml(announcement.user_name)}${announcement.city ? ` from ${this.escapeHtml(announcement.city)}` : ''}
          </p>
        ` : ''}
        <p style="color: rgba(255,255,255,0.9); font-size: 1rem; line-height: 1.6; margin: 0;">${this.escapeHtml(announcement.description || '')}</p>
        ${announcement.category?.name ? `
          <span class="announcement-category" style="margin-top: 16px;">${this.escapeHtml(announcement.category.name)}</span>
        ` : ''}
      </div>
    `;

    document.body.appendChild(modal);

    document.getElementById('closeDetailModal')?.addEventListener('click', () => {
      modal.remove();
      this.startAnnouncementRotation();
    });

    modal.querySelectorAll('[data-zoomable="true"]').forEach(item => {
      item.addEventListener('click', () => {
        const src = (item as HTMLElement).dataset.src;
        if (src) this.showFullscreenMedia(src);
      });
    });

    const mediaLength = announcement.media?.length || 0;
    
    modal.querySelectorAll('.media-dot').forEach(dot => {
      dot.addEventListener('click', () => {
        const idx = parseInt((dot as HTMLElement).dataset.mediaIndex || '0');
        this.navigateMedia(modal, idx, mediaLength);
      });
    });

    const prevBtn = modal.querySelector('#prevMediaBtn');
    const nextBtn = modal.querySelector('#nextMediaBtn');
    let currentIdx = 0;

    prevBtn?.addEventListener('click', () => {
      currentIdx = currentIdx > 0 ? currentIdx - 1 : mediaLength - 1;
      this.navigateMedia(modal, currentIdx, mediaLength);
    });

    nextBtn?.addEventListener('click', () => {
      currentIdx = currentIdx < mediaLength - 1 ? currentIdx + 1 : 0;
      this.navigateMedia(modal, currentIdx, mediaLength);
    });
  }

  private navigateMedia(modal: HTMLElement, idx: number, total: number): void {
    modal.querySelectorAll('.detail-media-item').forEach((item, i) => {
      (item as HTMLElement).style.display = i === idx ? 'flex' : 'none';
    });
    modal.querySelectorAll('.media-dot').forEach((d, i) => {
      (d as HTMLElement).style.background = i === idx ? '#2ECC71' : 'rgba(255,255,255,0.3)';
    });
    const counter = modal.querySelector('#mediaCounter');
    if (counter) counter.textContent = `${idx + 1} / ${total}`;
  }

  private renderDetailMedia(announcement: Announcement): string {
    if (!announcement.media || announcement.media.length === 0) {
      return '';
    }

    const mediaItems = announcement.media.map((media, index) => {
      const isVideo = media.file_type && media.file_type.startsWith('video/');
      const mediaUrl = this.getMediaUrl(media.file_path);
      if (isVideo) {
        const videoUrl = mediaUrl + (mediaUrl.includes('#') ? '' : '#t=0.001');
        return `
          <div class="detail-media-item" style="display: ${index === 0 ? 'flex' : 'none'}; justify-content: center; align-items: center; background: #000; border-radius: 12px; overflow: hidden; min-height: 200px;" data-index="${index}">
            <video controls playsinline preload="metadata" style="width: 100%; max-height: 400px; object-fit: contain;">
              <source src="${this.escapeHtml(videoUrl)}" type="${media.file_type || 'video/mp4'}">
            </video>
          </div>
        `;
      }
      return `
        <div class="detail-media-item" style="display: ${index === 0 ? 'flex' : 'none'}; justify-content: center; align-items: center; background: #000; border-radius: 12px; overflow: hidden; min-height: 200px; cursor: zoom-in;" data-index="${index}" data-zoomable="true" data-src="${this.escapeHtml(mediaUrl)}">
          <img src="${this.escapeHtml(mediaUrl)}" alt="${this.escapeHtml(announcement.title || '')}" style="max-width: 100%; max-height: 400px; object-fit: contain;">
        </div>
      `;
    }).join('');

    const navButtons = announcement.media.length > 1 ? `
      <button class="media-nav-btn prev-btn" id="prevMediaBtn" style="position: absolute; left: 8px; top: 50%; transform: translateY(-50%); background: rgba(0,0,0,0.6); border: none; border-radius: 50%; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; cursor: pointer; z-index: 10;">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
      </button>
      <button class="media-nav-btn next-btn" id="nextMediaBtn" style="position: absolute; right: 8px; top: 50%; transform: translateY(-50%); background: rgba(0,0,0,0.6); border: none; border-radius: 50%; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; cursor: pointer; z-index: 10;">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
      </button>
    ` : '';

    const dots = announcement.media.length > 1 ? `
      <div class="media-nav" style="display: flex; justify-content: center; gap: 8px; margin-top: 12px;">
        ${announcement.media.map((_, i) => `<span class="media-dot ${i === 0 ? 'active' : ''}" data-media-index="${i}" style="width: 10px; height: 10px; border-radius: 50%; background: ${i === 0 ? '#2ECC71' : 'rgba(255,255,255,0.3)'}; cursor: pointer;"></span>`).join('')}
      </div>
      <div style="text-align: center; color: rgba(255,255,255,0.5); font-size: 0.75rem; margin-top: 4px;">
        <span id="mediaCounter">1 / ${announcement.media.length}</span>
      </div>
    ` : '';

    return `
      <div class="detail-media-carousel" style="margin-bottom: 20px; position: relative;">
        ${navButtons}
        ${mediaItems}
        ${dots}
      </div>
    `;
  }

  private showFullscreenMedia(mediaUrl: string): void {
    const overlay = document.createElement('div');
    overlay.id = 'fullscreenMediaOverlay';
    overlay.style.cssText = 'position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.95); z-index: 10000; display: flex; flex-direction: column; justify-content: center; align-items: center;';
    
    overlay.innerHTML = `
      <button id="closeFullscreen" style="position: absolute; top: 16px; right: 16px; background: rgba(255,255,255,0.2); border: none; border-radius: 50%; width: 44px; height: 44px; display: flex; align-items: center; justify-content: center; cursor: pointer; z-index: 10001;">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2">
          <line x1="18" y1="6" x2="6" y2="18"/>
          <line x1="6" y1="6" x2="18" y2="18"/>
        </svg>
      </button>
      <div id="zoomContainer" style="width: 100%; height: 100%; display: flex; justify-content: center; align-items: center; overflow: auto; touch-action: pinch-zoom;">
        <img src="${this.escapeHtml(mediaUrl)}" style="max-width: 100%; max-height: 100%; object-fit: contain; transform-origin: center center;" id="zoomableImg">
      </div>
    `;
    
    document.body.appendChild(overlay);
    
    const closeBtn = document.getElementById('closeFullscreen');
    closeBtn?.addEventListener('click', () => overlay.remove());
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay || e.target === document.getElementById('zoomContainer')) {
        overlay.remove();
      }
    });
  }

  private showShareModal(announcement: Announcement): void {
    const modal = document.createElement('div');
    modal.className = 'share-modal';
    modal.id = 'shareModal';

    const shareUrl = `${window.location.origin}/announcements/${announcement.id}`;
    const shareText = `Check out: ${announcement.title}`;

    modal.innerHTML = `
      <div class="share-content">
        <h3 class="share-title">Share Announcement</h3>
        <div class="share-options">
          <button class="share-option" data-platform="whatsapp">
            <svg viewBox="0 0 24 24" fill="#25D366">
              <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/>
            </svg>
            <span>WhatsApp</span>
          </button>
          <button class="share-option" data-platform="facebook">
            <svg viewBox="0 0 24 24" fill="#1877F2">
              <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
            </svg>
            <span>Facebook</span>
          </button>
          <button class="share-option" data-platform="twitter">
            <svg viewBox="0 0 24 24" fill="#1DA1F2">
              <path d="M23.953 4.57a10 10 0 01-2.825.775 4.958 4.958 0 002.163-2.723c-.951.555-2.005.959-3.127 1.184a4.92 4.92 0 00-8.384 4.482C7.69 8.095 4.067 6.13 1.64 3.162a4.822 4.822 0 00-.666 2.475c0 1.71.87 3.213 2.188 4.096a4.904 4.904 0 01-2.228-.616v.06a4.923 4.923 0 003.946 4.827 4.996 4.996 0 01-2.212.085 4.936 4.936 0 004.604 3.417 9.867 9.867 0 01-6.102 2.105c-.39 0-.779-.023-1.17-.067a13.995 13.995 0 007.557 2.209c9.053 0 13.998-7.496 13.998-13.985 0-.21 0-.42-.015-.63A9.935 9.935 0 0024 4.59z"/>
            </svg>
            <span>Twitter</span>
          </button>
          <button class="share-option" data-platform="copy">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
            </svg>
            <span>Copy Link</span>
          </button>
        </div>
        <button class="share-cancel" id="cancelShare">Cancel</button>
      </div>
    `;

    document.body.appendChild(modal);

    modal.querySelectorAll('.share-option').forEach(btn => {
      btn.addEventListener('click', async () => {
        const platform = btn.getAttribute('data-platform');
        switch (platform) {
          case 'whatsapp':
            window.open(`https://wa.me/?text=${encodeURIComponent(shareText + ' ' + shareUrl)}`, '_blank');
            break;
          case 'facebook':
            window.open(`https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(shareUrl)}`, '_blank');
            break;
          case 'twitter':
            window.open(`https://twitter.com/intent/tweet?text=${encodeURIComponent(shareText)}&url=${encodeURIComponent(shareUrl)}`, '_blank');
            break;
          case 'copy':
            try {
              await navigator.clipboard.writeText(shareUrl);
              alert('Link copied to clipboard!');
            } catch {
              alert('Failed to copy link');
            }
            break;
        }
        modal.remove();
      });
    });

    document.getElementById('cancelShare')?.addEventListener('click', () => {
      modal.remove();
    });

    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        modal.remove();
      }
    });
  }

  private startAnnouncementRotation(): void {
    this.stopAnnouncementRotation();
    if (this.announcements.length > 1) {
      this.announcementInterval = setInterval(() => {
        this.currentAnnouncementIndex = (this.currentAnnouncementIndex + 1) % this.announcements.length;
        this.renderAnnouncementsContent();
      }, 5000);
    }
  }

  private stopAnnouncementRotation(): void {
    if (this.announcementInterval) {
      clearInterval(this.announcementInterval);
      this.announcementInterval = null;
    }
  }

  private escapeHtml(str: string): string {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  private attachEventListeners(): void {
    const loginBtn = document.getElementById('loginBtn');
    const biometricBtn = document.getElementById('biometricBtn');
    const togglePassword = document.getElementById('togglePassword');
    const passwordInput = document.getElementById('password') as HTMLInputElement;

    this.container.querySelectorAll('.main-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        this.activeTab = tab.getAttribute('data-main-tab') as ActiveTab;
        this.stopAnnouncementRotation();
        this.render();
        this.attachEventListeners();
        if (this.activeTab === 'announcements') {
          this.renderAnnouncementsContent();
        }
      });
    });

    this.container.querySelectorAll('.portal-tab').forEach(tab => {
      tab.addEventListener('click', async () => {
        this.selectedPortal = tab.getAttribute('data-portal') as PortalType;
        await portalService.setPortal(this.selectedPortal);
        // DC Protocol: Check biometric credentials for selected portal
        this.hasStoredCredentials = await authService.hasStoredCredentialsForPortal(this.selectedPortal);
        this.render();
        this.attachEventListeners();
      });
    });

    loginBtn?.addEventListener('click', () => this.handlePasswordLogin());
    biometricBtn?.addEventListener('click', () => this.handleBiometricLogin());

    togglePassword?.addEventListener('click', () => {
      if (passwordInput) {
        passwordInput.type = passwordInput.type === 'password' ? 'text' : 'password';
      }
    });

    document.getElementById('password')?.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        this.handlePasswordLogin();
      }
    });

    // Dev mode toggle: tap version 5 times within 3 seconds
    document.getElementById('versionTap')?.addEventListener('click', () => {
      this.devModeTapCount++;
      
      if (this.devModeTapTimer) {
        clearTimeout(this.devModeTapTimer);
      }
      
      this.devModeTapTimer = setTimeout(() => {
        this.devModeTapCount = 0;
      }, 3000);
      
      if (this.devModeTapCount === 5) {
        this.devModeTapCount = 0;
        if (this.devModeTapTimer) clearTimeout(this.devModeTapTimer);
        
        const currentMode = APP_CONFIG.isDevMode() ? 'DEVELOPMENT' : 'PRODUCTION';
        const newMode = APP_CONFIG.isDevMode() ? 'PRODUCTION' : 'DEVELOPMENT';
        
        if (confirm(`Switch from ${currentMode} to ${newMode} server?`)) {
          APP_CONFIG.toggleDevMode();
        }
      }
    });
  }

  private async handlePasswordLogin(): Promise<void> {
    const userIdInput = document.getElementById('userId') as HTMLInputElement;
    const passwordInput = document.getElementById('password') as HTMLInputElement;
    const loginBtn = document.getElementById('loginBtn') as HTMLButtonElement;
    const enableBiometric = document.getElementById('enableBiometric') as HTMLInputElement;

    const userId = userIdInput?.value.trim().toUpperCase();
    const password = passwordInput?.value;

    if (!userId || !password) {
      this.showError(`Please enter ${this.getPortalConfig().idLabel} and Password`);
      return;
    }

    this.showLoading(loginBtn, true);
    this.hideError();

    const result = await authService.loginWithPassword(userId, password, this.selectedPortal);

    if (result.success) {
      if (enableBiometric?.checked && this.hasBiometric) {
        await authService.saveCredentialsForBiometric(userId, password, this.selectedPortal);
      }
      this.stopAnnouncementRotation();
      window.dispatchEvent(new CustomEvent('login-success'));
    } else {
      this.showError(result.error || 'Login failed');
      this.showLoading(loginBtn, false);
    }
  }

  private async handleBiometricLogin(): Promise<void> {
    const biometricBtn = document.getElementById('biometricBtn') as HTMLButtonElement;
    
    this.showLoading(biometricBtn, true);
    this.hideError();

    const result = await authService.loginWithBiometricForPortal(this.selectedPortal);

    if (result.success) {
      this.stopAnnouncementRotation();
      window.dispatchEvent(new CustomEvent('login-success'));
    } else {
      this.showError(result.error || 'Biometric login failed');
      this.showLoading(biometricBtn, false);
    }
  }

  private showError(message: string): void {
    const errorEl = document.getElementById('errorMessage');
    if (errorEl) {
      errorEl.textContent = message;
      errorEl.style.display = 'block';
    }
  }

  private hideError(): void {
    const errorEl = document.getElementById('errorMessage');
    if (errorEl) {
      errorEl.style.display = 'none';
    }
  }

  private showLoading(button: HTMLButtonElement, loading: boolean): void {
    if (!button) return;
    
    if (loading) {
      button.disabled = true;
      button.innerHTML = `
        <svg class="spinner" width="20" height="20" viewBox="0 0 24 24">
          <circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="3" stroke-dasharray="30 70"/>
        </svg>
        Please wait...
      `;
    } else {
      button.disabled = false;
      const config = this.getPortalConfig();
      button.innerHTML = `
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/>
          <polyline points="10 17 15 12 10 7"/>
          <line x1="15" y1="12" x2="3" y2="12"/>
        </svg>
        Login to ${config.name}
      `;
    }
  }
}
