/**
 * Staff Change Password Page
 * DC Protocol: DC_MOBILE_STAFF_PWD_001
 * Secure password change form
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';

export class ChangePasswordPage {
  private container: HTMLElement;
  private submitting: boolean = false;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: 'Change Password', showBack: true })}
        
        <div class="password-form-container">
          <div class="security-notice card info">
            <h4>🔒 Password Requirements</h4>
            <ul>
              <li>Minimum 8 characters</li>
              <li>At least one uppercase letter</li>
              <li>At least one number</li>
              <li>At least one special character</li>
            </ul>
          </div>

          <form id="passwordForm" class="password-form card">
            <div class="form-group">
              <label for="currentPassword">Current Password</label>
              <input type="password" id="currentPassword" class="form-input" required 
                     placeholder="Enter current password" autocomplete="current-password">
            </div>

            <div class="form-group">
              <label for="newPassword">New Password</label>
              <input type="password" id="newPassword" class="form-input" required 
                     placeholder="Enter new password" autocomplete="new-password">
              <div id="strengthIndicator" class="password-strength"></div>
            </div>

            <div class="form-group">
              <label for="confirmPassword">Confirm New Password</label>
              <input type="password" id="confirmPassword" class="form-input" required 
                     placeholder="Confirm new password" autocomplete="new-password">
              <div id="matchIndicator" class="password-match"></div>
            </div>

            <button type="submit" id="submitBtn" class="btn btn-primary btn-block">
              Update Password
            </button>
          </form>
        </div>
      </div>
    `;

    PageHeader.attachListeners({ title: 'Change Password', showBack: true });
    this.attachListeners();
  }

  private attachListeners(): void {
    const form = document.getElementById('passwordForm');
    const newPassword = document.getElementById('newPassword') as HTMLInputElement;
    const confirmPassword = document.getElementById('confirmPassword') as HTMLInputElement;

    newPassword?.addEventListener('input', () => this.updateStrength(newPassword.value));
    confirmPassword?.addEventListener('input', () => this.checkMatch(newPassword.value, confirmPassword.value));

    form?.addEventListener('submit', async (e) => {
      e.preventDefault();
      await this.handleSubmit();
    });
  }

  private updateStrength(password: string): void {
    const indicator = document.getElementById('strengthIndicator');
    if (!indicator) return;

    let strength = 0;
    if (password.length >= 8) strength++;
    if (/[A-Z]/.test(password)) strength++;
    if (/[0-9]/.test(password)) strength++;
    if (/[^A-Za-z0-9]/.test(password)) strength++;

    const labels = ['Weak', 'Fair', 'Good', 'Strong'];
    const classes = ['weak', 'fair', 'good', 'strong'];

    if (password.length === 0) {
      indicator.innerHTML = '';
    } else {
      indicator.innerHTML = `
        <div class="strength-bar ${classes[strength - 1] || 'weak'}">
          <div class="strength-fill" style="width: ${strength * 25}%"></div>
        </div>
        <span class="strength-label">${labels[strength - 1] || 'Very Weak'}</span>
      `;
    }
  }

  private checkMatch(password: string, confirm: string): void {
    const indicator = document.getElementById('matchIndicator');
    if (!indicator || confirm.length === 0) {
      if (indicator) indicator.innerHTML = '';
      return;
    }

    if (password === confirm) {
      indicator.innerHTML = '<span class="match-success">✓ Passwords match</span>';
    } else {
      indicator.innerHTML = '<span class="match-error">✗ Passwords do not match</span>';
    }
  }

  private async handleSubmit(): Promise<void> {
    if (this.submitting) return;

    const currentPassword = (document.getElementById('currentPassword') as HTMLInputElement)?.value;
    const newPassword = (document.getElementById('newPassword') as HTMLInputElement)?.value;
    const confirmPassword = (document.getElementById('confirmPassword') as HTMLInputElement)?.value;

    if (!currentPassword || !newPassword || !confirmPassword) {
      alert('Please fill in all fields');
      return;
    }

    if (newPassword !== confirmPassword) {
      alert('New passwords do not match');
      return;
    }

    if (newPassword.length < 8) {
      alert('Password must be at least 8 characters');
      return;
    }

    this.submitting = true;
    const submitBtn = document.getElementById('submitBtn') as HTMLButtonElement;
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = 'Updating...';
    }

    try {
      const response = await apiService.post<any>('/staff/auth/change-password', {
        current_password: currentPassword,
        new_password: newPassword
      });

      if (response.success) {
        alert('Password updated successfully!');
        (document.getElementById('passwordForm') as HTMLFormElement)?.reset();
        document.getElementById('strengthIndicator')!.innerHTML = '';
        document.getElementById('matchIndicator')!.innerHTML = '';
      } else {
        alert(response.error || 'Failed to update password');
      }
    } catch (error) {
      console.error('[ChangePassword] Error:', error);
      alert('Failed to update password. Please try again.');
    } finally {
      this.submitting = false;
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Update Password';
      }
    }
  }
}
