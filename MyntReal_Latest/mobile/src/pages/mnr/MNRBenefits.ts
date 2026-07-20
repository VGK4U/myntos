/**
 * MNR Coupon Benefits Page - Web Parity
 * DC Protocol: DC_MOBILE_MNR_BENEFITS_002
 * Matches web layout with benefit types and summary stats
 */

import { apiService } from '../../services/api.service';
import { PageHeader } from '../../components/PageHeader';

interface BenefitSummary {
  total_benefits_count: number;
  total_discount_received: number;
  total_cashback_received: number;
  total_referral_incomes_count: number;
  total_referral_income: number;
  benefit_breakdown: Record<string, {
    count: number;
    total_discount: number;
    total_cashback: number;
  }>;
  referral_breakdown: Record<string, {
    count: number;
    total_commission: number;
    pending: number;
    approved: number;
    paid: number;
  }>;
}

interface BenefitType {
  id: number;
  title: string;
  description: string[];
  icon: string;
  color: string;
  actionLabel?: string;
  actionRoute?: string;
}

const BENEFIT_TYPES: BenefitType[] = [
  {
    id: 1,
    title: 'Points Redemption – Manthra EV Vehicles',
    description: [
      'Redeem points only on Manthra EV vehicles',
      'Capping: 7,500 points per vehicle',
      'Maximum: 2 redemptions allowed',
      'Exclusive M99 Users: Maximum withdrawal up to 15,000 points',
      'Graphene or 1 year LFP battery: 1,000 points redemption'
    ],
    icon: '🛵',
    color: '#10b981',
    actionLabel: 'Add EV Lead',
    actionRoute: 'mnr-add-ev-lead'
  },
  {
    id: 2,
    title: 'Solar Benefit (Points Claim)',
    description: [
      'Claim 15,000 points',
      'Applicable on minimum 3 KW Solar installation'
    ],
    icon: '☀️',
    color: '#f59e0b',
    actionLabel: 'Add Solar Lead',
    actionRoute: 'mnr-add-solar-lead'
  },
  {
    id: 3,
    title: 'Franchise Setup Benefit',
    description: [
      '2% commission on initial franchise income',
      '1% commission on subsequent invoices'
    ],
    icon: '🏪',
    color: '#8b5cf6'
  },
  {
    id: 4,
    title: 'Insurance Referral Benefit',
    description: [
      'Earn commission on insurance policy referrals',
      'Life, Health, and Vehicle insurance covered'
    ],
    icon: '🛡️',
    color: '#3b82f6'
  },
  {
    id: 5,
    title: 'Fleet Order Referral',
    description: [
      'Commission on fleet vehicle orders',
      'Applicable for bulk EV orders'
    ],
    icon: '🚚',
    color: '#ec4899'
  },
  {
    id: 6,
    title: 'Training Cashback',
    description: [
      'Cashback on training program enrollments',
      'Valid for certified training sessions'
    ],
    icon: '📚',
    color: '#06b6d4'
  },
  {
    id: 7,
    title: 'RoyalEV Bonus',
    description: [
      'Premium bonus on Royal EV vehicle purchases',
      'Up to 15% bonus based on package tier'
    ],
    icon: '👑',
    color: '#eab308'
  }
];

export class MNRBenefits {
  private container: HTMLElement;
  private summary: BenefitSummary | null = null;
  private loading: boolean = true;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadBenefits();
  }

  private async loadBenefits(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      const [benefitsRes, referralRes] = await Promise.all([
        apiService.get<any>('/ev-discount/my-benefits'),
        apiService.get<any>('/ev-discount/my-referral-income')
      ]);

      if (benefitsRes.success && benefitsRes.data) {
        this.summary = {
          total_benefits_count: benefitsRes.data.total_benefits_count || 0,
          total_discount_received: benefitsRes.data.total_discount_received || 0,
          total_cashback_received: benefitsRes.data.total_cashback_received || 0,
          total_referral_incomes_count: benefitsRes.data.total_referral_incomes_count || 0,
          total_referral_income: benefitsRes.data.total_referral_income || 0,
          benefit_breakdown: benefitsRes.data.benefit_breakdown || {},
          referral_breakdown: benefitsRes.data.referral_breakdown || {}
        };
      }

      if (referralRes.success && referralRes.data && this.summary) {
        this.summary.total_referral_incomes_count = referralRes.data.total_count || this.summary.total_referral_incomes_count;
        this.summary.total_referral_income = referralRes.data.total_amount || this.summary.total_referral_income;
        this.summary.referral_breakdown = referralRes.data.breakdown || this.summary.referral_breakdown;
      }
    } catch (error) {
      console.error('[MNRBenefits] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private render(): void {
    this.container.innerHTML = `
      <style>
        .benefits-page { padding: 16px; }
        
        .header-card {
          background: linear-gradient(135deg, #065f46 0%, #047857 100%);
          border-radius: 12px;
          padding: 16px;
          margin-bottom: 16px;
          color: white;
        }
        .header-card h3 { margin: 0 0 4px; font-size: 16px; }
        .header-card p { margin: 0; font-size: 13px; opacity: 0.9; }
        
        .feedback-notice {
          background: linear-gradient(135deg, #78350f 0%, #92400e 100%);
          border-radius: 12px;
          padding: 14px;
          margin-bottom: 16px;
          color: white;
        }
        .feedback-notice h4 {
          color: #fcd34d;
          margin: 0 0 8px;
          font-size: 14px;
          display: flex;
          align-items: center;
          gap: 6px;
        }
        .feedback-notice p {
          margin: 0 0 8px;
          font-size: 12px;
          line-height: 1.5;
        }
        .feedback-notice ul {
          margin: 8px 0;
          padding-left: 18px;
          font-size: 12px;
          line-height: 1.6;
        }
        .feedback-notice .note {
          font-size: 11px;
          opacity: 0.8;
          margin-top: 8px;
          padding-top: 8px;
          border-top: 1px solid rgba(255,255,255,0.2);
        }
        
        .stats-grid {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 12px;
          margin-bottom: 20px;
        }
        .stat-card {
          background: rgba(22, 33, 62, 0.8);
          border-radius: 12px;
          padding: 16px;
          text-align: center;
        }
        .stat-icon {
          width: 40px;
          height: 40px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          margin: 0 auto 8px;
          font-size: 18px;
        }
        .stat-value {
          font-size: 20px;
          font-weight: 700;
          color: #e6f1ff;
          margin-bottom: 4px;
        }
        .stat-label {
          font-size: 11px;
          color: #8892b0;
          text-transform: uppercase;
        }
        
        .section-title {
          font-size: 15px;
          font-weight: 600;
          color: #e6f1ff;
          margin: 20px 0 12px;
          display: flex;
          align-items: center;
          gap: 8px;
        }
        
        .benefit-types-list {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        
        .benefit-type-card {
          background: rgba(22, 33, 62, 0.8);
          border-radius: 12px;
          padding: 16px;
          border-left: 4px solid;
        }
        .benefit-type-header {
          display: flex;
          align-items: center;
          gap: 12px;
          margin-bottom: 10px;
        }
        .benefit-type-number {
          width: 28px;
          height: 28px;
          border-radius: 50%;
          background: rgba(16, 185, 129, 0.2);
          color: #10b981;
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: 700;
          font-size: 14px;
        }
        .benefit-type-title {
          font-size: 14px;
          font-weight: 600;
          color: #e6f1ff;
          flex: 1;
        }
        .benefit-type-icon {
          font-size: 20px;
        }
        .benefit-type-desc {
          margin: 0;
          padding-left: 40px;
        }
        .benefit-type-desc li {
          font-size: 12px;
          color: #8892b0;
          margin-bottom: 4px;
          line-height: 1.4;
        }
        .benefit-action-btn {
          margin-top: 12px;
          margin-left: 40px;
          padding: 8px 16px;
          background: linear-gradient(135deg, #10b981 0%, #059669 100%);
          color: white;
          border: none;
          border-radius: 6px;
          font-size: 12px;
          font-weight: 600;
          cursor: pointer;
        }
      </style>
      ${PageHeader.render({ title: '🎁 Coupon Utilisation Benefits', showBack: true })}
      <div class="benefits-page" id="pageContent">
        <div class="loading-state">Loading...</div>
      </div>
    `;

    PageHeader.attachListeners({ title: '🎁 Coupon Utilisation Benefits', showBack: true });
  }

  private updateContent(): void {
    const content = document.getElementById('pageContent');
    if (!content) return;

    if (this.loading) {
      content.innerHTML = '<div class="loading-state" style="text-align: center; padding: 40px; color: #8892b0;">Loading...</div>';
      return;
    }

    const s = this.summary || {
      total_benefits_count: 0,
      total_discount_received: 0,
      total_cashback_received: 0,
      total_referral_income: 0
    };

    content.innerHTML = `
      <div class="header-card">
        <h3>MNR Coupon Benefits</h3>
        <p>Maximize your MNR Discount Coupon value with 7 benefit types</p>
      </div>

      <div class="feedback-notice">
        <h4>📹 Feedback Video and Photos Requirement</h4>
        <p><strong>After points utilization for additional referral bonus or earnings:</strong> It is mandatory to share feedback videos and photos.</p>
        <p><strong>Eligible Engagement Activities:</strong></p>
        <ul>
          <li>Reels (video content)</li>
          <li>WhatsApp Status sharing</li>
          <li>Social Media posts</li>
          <li>Sharing & Ratings in Announcement sections</li>
          <li>Engaging with teams</li>
          <li>Attending Zoom calls</li>
        </ul>
        <p class="note">ℹ️ Please note: Submitted feedback videos and photos may be publicly displayed on our platforms for promotional and community engagement purposes.</p>
      </div>

      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-icon" style="background: rgba(16, 185, 129, 0.2);">✓</div>
          <div class="stat-value">${(s.total_discount_received + s.total_cashback_received).toLocaleString()} pts</div>
          <div class="stat-label">Total Benefits Used</div>
        </div>
        <div class="stat-card">
          <div class="stat-icon" style="background: rgba(6, 182, 212, 0.2);">💎</div>
          <div class="stat-value">${s.total_discount_received.toLocaleString()} pts</div>
          <div class="stat-label">Total Discounts</div>
        </div>
        <div class="stat-card">
          <div class="stat-icon" style="background: rgba(245, 158, 11, 0.2);">💰</div>
          <div class="stat-value">${s.total_cashback_received.toLocaleString()} pts</div>
          <div class="stat-label">Total Cashback</div>
        </div>
        <div class="stat-card">
          <div class="stat-icon" style="background: rgba(139, 92, 246, 0.2);">👥</div>
          <div class="stat-value">${s.total_referral_income.toLocaleString()} pts</div>
          <div class="stat-label">Referral Income</div>
        </div>
      </div>

      <div class="section-title">
        <span>📋</span> Available Benefit Types
      </div>

      <div class="benefit-types-list">
        ${BENEFIT_TYPES.map(bt => `
          <div class="benefit-type-card" style="border-left-color: ${bt.color};">
            <div class="benefit-type-header">
              <div class="benefit-type-number" style="background: ${bt.color}20; color: ${bt.color};">${bt.id}</div>
              <div class="benefit-type-title">${bt.title}</div>
              <span class="benefit-type-icon">${bt.icon}</span>
            </div>
            <ul class="benefit-type-desc">
              ${bt.description.map(d => `<li>${d}</li>`).join('')}
            </ul>
            ${bt.actionLabel ? `<button class="benefit-action-btn" data-route="${bt.actionRoute}">➕ ${bt.actionLabel}</button>` : ''}
          </div>
        `).join('')}
      </div>
    `;

    this.attachListeners();
  }

  private attachListeners(): void {
    document.querySelectorAll('.benefit-action-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const route = btn.getAttribute('data-route');
        if (route) {
          window.dispatchEvent(new CustomEvent('navigate', { detail: { route } }));
        }
      });
    });
  }
}
