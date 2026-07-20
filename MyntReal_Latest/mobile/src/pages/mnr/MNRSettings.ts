import { PageHeader } from '../../components/PageHeader';
import { routerService } from '../../services/router.service';

export class MNRSettings {
  private container: HTMLElement;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
  }

  private render(): void {
    this.container.innerHTML = PageHeader.render({
      title: 'Settings',
      showBack: true
    });

    const content = document.createElement('div');
    content.className = 'page-content';
    content.innerHTML = `
      <div style="padding:16px;">
        <div style="font-size:14px;font-weight:600;color:#94a3b8;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:12px;padding:0 4px;">Account</div>
        
        ${this.menuItem('Edit Profile', 'user', 'mnr-profile-edit')}
        ${this.menuItem('KYC Verification', 'file-text', 'mnr-kyc')}
        ${this.menuItem('Bank Details', 'credit-card', 'mnr-bank')}
        ${this.menuItem('Change Password', 'lock', 'mnr-change-password')}

        <div style="font-size:14px;font-weight:600;color:#94a3b8;text-transform:uppercase;letter-spacing:0.5px;margin:24px 0 12px;padding:0 4px;">Support</div>
        
        ${this.menuItem('Feedback', 'message-circle', 'mnr-feedback')}
        ${this.menuItem('Announcements', 'bell', 'mnr-announcements')}
      </div>
    `;

    this.container.appendChild(content);

    content.querySelectorAll('[data-route]').forEach(el => {
      el.addEventListener('click', () => {
        const route = (el as HTMLElement).dataset.route;
        if (route) {
          routerService.navigate(route as any);
        }
      });
    });
  }

  private menuItem(label: string, icon: string, route: string): string {
    return `
      <div data-route="${route}" style="background:#fff;border-radius:12px;padding:14px 16px;margin-bottom:8px;box-shadow:0 1px 4px rgba(0,0,0,0.05);display:flex;align-items:center;justify-content:space-between;cursor:pointer;">
        <div style="display:flex;align-items:center;gap:12px;">
          <div style="width:36px;height:36px;border-radius:10px;background:#f1f5f9;display:flex;align-items:center;justify-content:center;">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#667eea" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${this.getIcon(icon)}</svg>
          </div>
          <span style="font-size:14px;font-weight:500;color:#1e293b;">${label}</span>
        </div>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#cbd5e1" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
      </div>
    `;
  }

  private getIcon(name: string): string {
    const icons: Record<string, string> = {
      'user': '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
      'file-text': '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>',
      'credit-card': '<rect x="1" y="4" width="22" height="16" rx="2" ry="2"/><line x1="1" y1="10" x2="23" y2="10"/>',
      'lock': '<rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
      'message-circle': '<path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>',
      'bell': '<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/>'
    };
    return icons[name] || '';
  }
}
