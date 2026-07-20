/**
 * Settings Page
 * DC Protocol: DC_MOBILE_SETTINGS_001
 * App settings and change password
 */

import { authService } from '../services/auth.service';
import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';

const THEME_STORAGE_KEY = 'mnr_theme_preference';

export class SettingsPage {
  private container: HTMLElement;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    this.attachListeners();
  }

  private getCurrentTheme(): string {
    return localStorage.getItem(THEME_STORAGE_KEY) || 'dark';
  }

  private setTheme(theme: string): void {
    localStorage.setItem(THEME_STORAGE_KEY, theme);
    document.body.classList.remove('dark-theme', 'light-theme');
    document.body.classList.add(`${theme}-theme`);
    console.log('[DC_THEME_001] Mobile theme set to:', theme);
  }

  private render(): void {
    const hasBiometric = false; // Will be updated after async check

    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: 'Settings', showBack: true })}
        
        <div class="settings-section card">
          <h3 class="section-title">Security</h3>
          
          <div class="setting-item">
            <div class="setting-info">
              <span class="setting-label">Biometric Login</span>
              <span class="setting-desc">Use Face ID or Fingerprint to login</span>
            </div>
            <label class="switch">
              <input type="checkbox" id="biometricToggle" ${hasBiometric ? 'checked' : ''}>
              <span class="slider"></span>
            </label>
          </div>

          <button class="menu-item" id="changePasswordBtn">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
              <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
            </svg>
            <span>Change Password</span>
            <svg class="chevron" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="9 18 15 12 9 6"/>
            </svg>
          </button>
        </div>

        <div class="settings-section card">
          <h3 class="section-title">Appearance</h3>
          
          <div class="setting-item">
            <div class="setting-info">
              <span class="setting-label">Dark Mode</span>
              <span class="setting-desc">Use dark theme for the app</span>
            </div>
            <label class="switch">
              <input type="checkbox" id="themeToggle" ${this.getCurrentTheme() === 'dark' ? 'checked' : ''}>
              <span class="slider"></span>
            </label>
          </div>
        </div>

        <div class="settings-section card">
          <h3 class="section-title">App</h3>
          
          <div class="setting-item">
            <div class="setting-info">
              <span class="setting-label">Version</span>
            </div>
            <span class="setting-value">1.0.0</span>
          </div>

          <div class="setting-item">
            <div class="setting-info">
              <span class="setting-label">Build</span>
            </div>
            <span class="setting-value">2026.01.30</span>
          </div>
        </div>

        <div class="settings-section card">
          <h3 class="section-title">Account</h3>
          
          <button class="menu-item danger" id="logoutBtn">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
              <polyline points="16 17 21 12 16 7"/>
              <line x1="21" y1="12" x2="9" y2="12"/>
            </svg>
            <span>Logout</span>
          </button>
        </div>

        <div id="passwordModal" class="modal" style="display: none;">
          <div class="modal-content">
            <h3 class="modal-title">Change Password</h3>
            <form id="passwordForm">
              <div class="input-group">
                <label class="input-label">Current Password</label>
                <input type="password" id="currentPassword" class="input" required />
              </div>
              <div class="input-group">
                <label class="input-label">New Password</label>
                <input type="password" id="newPassword" class="input" required minlength="8" />
              </div>
              <div class="input-group">
                <label class="input-label">Confirm Password</label>
                <input type="password" id="confirmPassword" class="input" required />
              </div>
              <div class="modal-actions">
                <button type="submit" class="btn btn-primary btn-full">Update Password</button>
                <button type="button" class="btn btn-outline btn-full" id="cancelPassword">Cancel</button>
              </div>
            </form>
          </div>
        </div>
      </div>
    `;
  }

  private attachListeners(): void {
    PageHeader.attachListeners({ title: 'Settings', showBack: true });

    // DC_THEME_001: Theme toggle listener
    document.getElementById('themeToggle')?.addEventListener('change', (e) => {
      const isDark = (e.target as HTMLInputElement).checked;
      this.setTheme(isDark ? 'dark' : 'light');
    });

    document.getElementById('biometricToggle')?.addEventListener('change', async (e) => {
      const enabled = (e.target as HTMLInputElement).checked;
      if (enabled) {
        alert('Biometric login will be enabled after your next manual login');
      } else {
        alert('Biometric login disabled');
      }
    });

    document.getElementById('changePasswordBtn')?.addEventListener('click', () => {
      document.getElementById('passwordModal')!.style.display = 'flex';
    });

    document.getElementById('cancelPassword')?.addEventListener('click', () => {
      document.getElementById('passwordModal')!.style.display = 'none';
    });

    document.getElementById('passwordForm')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      await this.handlePasswordChange();
    });

    document.getElementById('logoutBtn')?.addEventListener('click', async () => {
      if (confirm('Are you sure you want to logout?')) {
        await authService.logout();
        window.dispatchEvent(new CustomEvent('logout'));
      }
    });
  }

  private async handlePasswordChange(): Promise<void> {
    const currentPassword = (document.getElementById('currentPassword') as HTMLInputElement).value;
    const newPassword = (document.getElementById('newPassword') as HTMLInputElement).value;
    const confirmPassword = (document.getElementById('confirmPassword') as HTMLInputElement).value;

    if (newPassword !== confirmPassword) {
      alert('Passwords do not match');
      return;
    }

    try {
      const response = await apiService.fetch('/staff/auth/change-password', {
        method: 'POST',
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword
        })
      });

      if (response.success) {
        alert('Password changed successfully');
        document.getElementById('passwordModal')!.style.display = 'none';
        (document.getElementById('passwordForm') as HTMLFormElement).reset();
      } else {
        alert(response.error || 'Failed to change password');
      }
    } catch (error: any) {
      alert(error.message || 'Failed to change password');
    }
  }
}
