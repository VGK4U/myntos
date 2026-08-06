import { PageHeader } from '../components/PageHeader';
import { APP_CONFIG } from '../config/app.config';

export class StaffExpenseEntriesPage {
  private container: HTMLElement;
  static readonly slug = 'staff-expense-entries';
  static readonly label = 'Expense Entries';
  static readonly icon = 'fas fa-credit-card';
  static readonly color = '#6366f1';

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.container.innerHTML = await this.render();
    PageHeader.attachBackHandler();
  }

  async render(): Promise<string> {
    const srcUrl = `${APP_CONFIG.MEDIA_BASE_URL}/staff/accounts/expense-entries?embed=true&token=${encodeURIComponent(localStorage.getItem("auth_token") || "")}`;
    return `
      <div style="background:#f3f4f6;min-height:100vh;padding-bottom:80px">
        ${PageHeader.render({ title: 'Expense Entries', showBack: true })}
        <div style="padding:12px;min-height:calc(100vh - 120px)">
          <iframe
            id="staff-expense-frame"
            src="${srcUrl}"
            style="width:100%;height:calc(100vh - 140px);border:0;background:#fff;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,0.05)"
            loading="lazy"
            title="Expense Entries"
          ></iframe>
        </div>
      </div>
    `;
  }
}

export default StaffExpenseEntriesPage;
