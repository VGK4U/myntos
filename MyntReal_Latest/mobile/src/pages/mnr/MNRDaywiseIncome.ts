/**
 * MNR Daywise Income Page
 * DC Protocol: DC_MOBILE_MNR_DAYWISE_001
 * View day-by-day income breakdown
 */

import { apiService } from '../../services/api.service';
import { PageHeader } from '../../components/PageHeader';

interface DayIncome {
  date: string;
  direct: number;
  matching: number;
  ved: number;
  guru_dakshina: number;
  total: number;
}

export class MNRDaywiseIncome {
  private container: HTMLElement;
  private incomeData: DayIncome[] = [];
  private loading: boolean = true;
  private selectedMonth: string = '';

  constructor(container: HTMLElement) {
    this.container = container;
    const now = new Date();
    this.selectedMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadIncome();
  }

  private async loadIncome(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      const [year, month] = this.selectedMonth.split('-');
      const response = await apiService.get<any>(`/users/daywise-income?year=${year}&month=${month}`);
      if (response.success && response.data) {
        this.incomeData = response.data.income || response.data || [];
      }
    } catch (error) {
      console.error('[MNRDaywiseIncome] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container">
        ${PageHeader.render({ title: '📊 Facilitation Summary', showBack: true })}
        
        <div id="pageContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
    `;

    PageHeader.attachListeners({ title: '📊 Facilitation Summary', showBack: true });
  }

  private updateContent(): void {
    const content = document.getElementById('pageContent');
    if (!content) return;

    if (this.loading) {
      content.innerHTML = '<div class="loading-state">Loading...</div>';
      return;
    }

    const totalIncome = this.incomeData.reduce((sum, d) => sum + (d.total || 0), 0);

    content.innerHTML = `
      <div class="month-selector card">
        <input type="month" id="monthPicker" value="${this.selectedMonth}" class="form-input">
      </div>

      <div class="income-summary card">
        <h3>Total for ${this.getMonthName()}</h3>
        <div class="summary-value">₹${totalIncome.toLocaleString()}</div>
      </div>

      <h4 class="section-title">Daily Breakdown</h4>
      ${this.incomeData.length > 0 ? `
        <div class="daywise-list">
          ${this.incomeData.map(day => this.renderDayCard(day)).join('')}
        </div>
      ` : `
        <div class="empty-state card">
          <div class="empty-icon">📊</div>
          <p>No income records for this month</p>
        </div>
      `}
    `;

    document.getElementById('monthPicker')?.addEventListener('change', (e) => {
      this.selectedMonth = (e.target as HTMLInputElement).value;
      this.loadIncome();
    });
  }

  private renderDayCard(day: DayIncome): string {
    const date = new Date(day.date);
    const dayNum = date.getDate();
    const weekday = date.toLocaleDateString('en', { weekday: 'short' });

    return `
      <div class="day-card card">
        <div class="day-date">
          <span class="day-num">${dayNum}</span>
          <span class="day-name">${weekday}</span>
        </div>
        <div class="day-breakdown">
          ${day.direct > 0 ? `<div class="income-type"><span>Direct</span><span>₹${day.direct.toLocaleString()}</span></div>` : ''}
          ${day.matching > 0 ? `<div class="income-type"><span>Matching</span><span>₹${day.matching.toLocaleString()}</span></div>` : ''}
          ${day.ved > 0 ? `<div class="income-type"><span>Ved</span><span>₹${day.ved.toLocaleString()}</span></div>` : ''}
          ${day.guru_dakshina > 0 ? `<div class="income-type"><span>Guru</span><span>₹${day.guru_dakshina.toLocaleString()}</span></div>` : ''}
        </div>
        <div class="day-total">₹${(day.total || 0).toLocaleString()}</div>
      </div>
    `;
  }

  private getMonthName(): string {
    const [year, month] = this.selectedMonth.split('-');
    const date = new Date(parseInt(year), parseInt(month) - 1);
    return date.toLocaleDateString('en', { month: 'long', year: 'numeric' });
  }
}
