/**
 * MNR Change Password Page
 * DC Protocol: DC_MOBILE_MNR_CHANGEPWD_001
 * Change account password
 */

import { apiService } from '../../services/api.service';
import { PageHeader } from '../../components/PageHeader';
import { routerService } from '../../services/router.service';

export class MNRChangePassword {
  private container: HTMLElement;
  private loading: boolean = false;
  private error: string = '';
  private success: string = '';

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: '🔐 Change Password', showBack: true })}
        
        <div class="form-container">
          <div class="password-form card">
            <div id="formMessages"></div>
            
            <div class="form-group">
              <label for="currentPassword">Current Password</label>
              <div class="password-input-wrapper">
                <input type="password" id="currentPassword" placeholder="Enter current password">
                <button type="button" class="toggle-password" data-target="currentPassword">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                    <circle cx="12" cy="12" r="3"/>
                  </svg>
                </button>
              </div>
            </div>

            <div class="form-group">
              <label for="newPassword">New Password</label>
              <div class="password-input-wrapper">
                <input type="password" id="newPassword" placeholder="Enter new password">
                <button type="button" class="toggle-password" data-target="newPassword">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                    <circle cx="12" cy="12" r="3"/>
                  </svg>
                </button>
              </div>
            </div>

            <div class="form-group">
              <label for="confirmPassword">Confirm New Password</label>
              <div class="password-input-wrapper">
                <input type="password" id="confirmPassword" placeholder="Confirm new password">
                <button type="button" class="toggle-password" data-target="confirmPassword">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                    <circle cx="12" cy="12" r="3"/>
                  </svg>
                </button>
              </div>
            </div>

            <button id="changePasswordBtn" class="btn-primary" ${this.loading ? 'disabled' : ''}>
              ${this.loading ? 'Changing...' : 'Change Password'}
            </button>
          </div>

          <div class="password-tips card">
            <h4>Password Requirements</h4>
            <ul class="tips-list">
              <li>At least 8 characters long</li>
              <li>Include uppercase and lowercase letters</li>
              <li>Include at least one number</li>
              <li>Include at least one special character</li>
            </ul>
          </div>
        </div>
      </div>
    `;

    this.attachListeners();
  }

  private attachListeners(): void {
    PageHeader.attachListeners({ title: '🔐 Change Password', showBack: true });

    this.container.querySelectorAll('.toggle-password').forEach(btn => {
      btn.addEventListener('click', () => {
        const targetId = btn.getAttribute('data-target');
        if (targetId) {
          const input = document.getElementById(targetId) as HTMLInputElement;
          if (input) {
            input.type = input.type === 'password' ? 'text' : 'password';
          }
        }
      });
    });

    document.getElementById('changePasswordBtn')?.addEventListener('click', () => {
      this.handleChangePassword();
    });
  }

  private async handleChangePassword(): Promise<void> {
    const currentPassword = (document.getElementById('currentPassword') as HTMLInputElement).value;
    const newPassword = (document.getElementById('newPassword') as HTMLInputElement).value;
    const confirmPassword = (document.getElementById('confirmPassword') as HTMLInputElement).value;

    this.error = '';
    this.success = '';

    if (!currentPassword || !newPassword || !confirmPassword) {
      this.showMessage('Please fill in all fields', 'error');
      return;
    }

    if (newPassword !== confirmPassword) {
      this.showMessage('New passwords do not match', 'error');
      return;
    }

    if (newPassword.length < 8) {
      this.showMessage('Password must be at least 8 characters', 'error');
      return;
    }

    this.loading = true;
    this.render();

    try {
      const response = await apiService.post('/users/profile/change-password', {
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: confirmPassword
      });

      if (response.success) {
        this.showMessage('Password changed successfully!', 'success');
        setTimeout(() => {
          routerService.navigate('mnr-profile');
        }, 2000);
      } else {
        this.showMessage(response.error || 'Failed to change password', 'error');
      }
    } catch (error: any) {
      this.showMessage(error.message || 'An error occurred', 'error');
    }

    this.loading = false;
  }

  private showMessage(message: string, type: 'error' | 'success'): void {
    const messagesDiv = document.getElementById('formMessages');
    if (messagesDiv) {
      messagesDiv.innerHTML = `<div class="message ${type}">${message}</div>`;
    }
  }
}
