/**
 * Session Expiration Banner Component
 * DC Protocol: DC_SESSION_EXPIRY_001
 * Global component for handling session expiration across all pages
 */

import { apiService } from '../services/api.service';
import { gpsService } from '../services/gps.service';
import { authService } from '../services/auth.service';

class SessionExpirationBanner {
  private isShowing: boolean = false;
  private unsubscribe: (() => void) | null = null;
  private checkInterval: any = null;

  init(): void {
    // DC_REAUTH_REFRESH: Guard against duplicate init (called again after each login-success)
    if (this.unsubscribe) this.unsubscribe();
    if (this.checkInterval) clearInterval(this.checkInterval);

    this.unsubscribe = apiService.onSessionExpired((endpoint) => {
      console.log('[SessionBanner] Session expired detected, endpoint:', endpoint);
      this.show();
    });

    this.checkInterval = setInterval(() => {
      const trackingStatus = gpsService.getTrackingStatus();
      if (trackingStatus.isSessionExpired && !this.isShowing) {
        this.show();
      } else if (!trackingStatus.isSessionExpired && this.isShowing) {
        this.hide();
      }
    }, 2000);
  }

  cleanup(): void {
    if (this.unsubscribe) {
      this.unsubscribe();
      this.unsubscribe = null;
    }
    if (this.checkInterval) {
      clearInterval(this.checkInterval);
      this.checkInterval = null;
    }
    this.hide();
  }

  show(): void {
    if (this.isShowing) return;
    if (document.getElementById('globalSessionBanner')) return;

    this.isShowing = true;

    const banner = document.createElement('div');
    banner.id = 'globalSessionBanner';
    banner.className = 'global-session-banner';
    banner.innerHTML = `
      <div class="session-banner-content">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="8" x2="12" y2="12"/>
          <line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>
        <div class="session-banner-text">
          <strong>Session Expired</strong>
          <span>Data saved locally. Tap to login.</span>
        </div>
      </div>
      <button id="globalReAuthBtn" class="re-auth-btn">Login</button>
    `;

    document.body.appendChild(banner);

    document.getElementById('globalReAuthBtn')?.addEventListener('click', (e) => {
      e.stopPropagation();
      this.showReAuthModal();
    });

    banner.addEventListener('click', () => this.showReAuthModal());
  }

  hide(): void {
    const banner = document.getElementById('globalSessionBanner');
    if (banner) {
      banner.remove();
    }
    this.isShowing = false;
  }

  private showReAuthModal(): void {
    if (document.getElementById('globalReAuthModal')) return;

    const authState = authService.getAuthState();
    const user = authState.user;

    const modal = document.createElement('div');
    modal.id = 'globalReAuthModal';
    modal.className = 'modal';
    modal.style.display = 'flex';
    modal.style.zIndex = '10001';
    modal.innerHTML = `
      <div class="modal-content" style="max-width: 320px;">
        <div class="modal-header">
          <h3>Session Expired</h3>
          <button class="modal-close" id="closeGlobalReAuthModal">&times;</button>
        </div>
        <div class="modal-body">
          ${user ? `
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 16px; padding: 12px; background: var(--bg-tertiary); border-radius: 8px;">
              <div style="width: 40px; height: 40px; border-radius: 50%; background: var(--primary); display: flex; align-items: center; justify-content: center; color: white; font-weight: bold;">
                ${(user.full_name || user.name || user.partner_name || 'U').charAt(0).toUpperCase()}
              </div>
              <div>
                <div style="font-weight: 600; color: var(--text-primary);">${user.full_name || user.name || user.partner_name || 'User'}</div>
                <div style="font-size: 12px; color: var(--text-secondary);">${user.emp_code || user.partner_code || user.mnr_id || ''}</div>
              </div>
            </div>
          ` : ''}
          <p style="margin-bottom: 16px; color: var(--text-secondary);">
            Your session has expired. Please enter your password to continue.
          </p>
          <div class="form-group">
            <label>User ID</label>
            <input type="text" id="globalReAuthUserId" class="form-control" value="${user?.emp_code || user?.employee_id || user?.partner_code || user?.mnr_id || ''}" placeholder="Enter your User ID" autocomplete="username">
          </div>
          <div class="form-group">
            <label>Password</label>
            <input type="password" id="globalReAuthPassword" class="form-control" placeholder="Enter your password" autocomplete="current-password">
          </div>
          <p id="globalReAuthError" class="form-error" style="display: none; color: var(--danger); margin-top: 8px;"></p>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" id="cancelGlobalReAuth">Cancel</button>
          <button class="btn btn-primary" id="submitGlobalReAuth">Login</button>
        </div>
      </div>
    `;

    document.body.appendChild(modal);

    setTimeout(() => {
      const passwordInput = document.getElementById('globalReAuthPassword') as HTMLInputElement;
      passwordInput?.focus();
    }, 100);

    document.getElementById('closeGlobalReAuthModal')?.addEventListener('click', () => modal.remove());
    document.getElementById('cancelGlobalReAuth')?.addEventListener('click', () => modal.remove());
    document.getElementById('submitGlobalReAuth')?.addEventListener('click', () => this.submitReAuth());

    document.getElementById('globalReAuthPassword')?.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') this.submitReAuth();
    });
  }

  private async submitReAuth(): Promise<void> {
    const userIdInput = document.getElementById('globalReAuthUserId') as HTMLInputElement;
    const passwordInput = document.getElementById('globalReAuthPassword') as HTMLInputElement;
    const errorEl = document.getElementById('globalReAuthError');
    const submitBtn = document.getElementById('submitGlobalReAuth') as HTMLButtonElement;

    if (!passwordInput) return;

    const userId = userIdInput?.value || '';
    const password = passwordInput.value;

    if (!password) {
      if (errorEl) {
        errorEl.textContent = 'Please enter your password';
        errorEl.style.display = 'block';
      }
      return;
    }

    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = 'Logging in...';
    }

    try {
      const authState = authService.getAuthState();
      const portal = authState.user?.portal || 'staff';

      const result = await authService.loginWithPassword(userId, password, portal);

      if (result.success) {
        document.getElementById('globalReAuthModal')?.remove();
        this.hide();

        const { offlineQueueService } = await import('../services/offline-queue.service');
        const status = offlineQueueService.getStatus();
        if (status.pendingCount > 0) {
          console.log('[SessionBanner] Re-auth successful, queued data will sync automatically');
        }

        // DC_REAUTH_REFRESH: Reload the current page so it re-inits with a fresh token.
        // Without this, pages like AutoDialer remain in their stale error state after re-auth
        // and the user has to manually navigate away and back to recover.
        console.log('[SessionBanner] Refreshing current page after successful re-auth');
        window.dispatchEvent(new CustomEvent('login-success'));
      } else {
        if (errorEl) {
          errorEl.textContent = result.error || 'Login failed. Please try again.';
          errorEl.style.display = 'block';
        }
      }
    } catch (error: any) {
      if (errorEl) {
        errorEl.textContent = error.message || 'An error occurred';
        errorEl.style.display = 'block';
      }
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Login';
      }
    }
  }
}

export const sessionExpirationBanner = new SessionExpirationBanner();
