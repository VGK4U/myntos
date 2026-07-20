/**
 * MNR Franchise Earnings Page
 * DC Protocol: DC_MOBILE_MNR_FRANCHISE_EARNINGS_001
 * Full franchise earnings display matching web parity
 */

import { apiService } from '../../services/api.service';
import { PageHeader } from '../../components/PageHeader';

interface FranchiseLead {
  id: number;
  name: string;
  status: string;
  created_at: string;
}

interface FranchiseStats {
  total_leads: number;
  active_franchises: number;
  total_earnings: number;
}

export class MNRFranchiseEarnings {
  private container: HTMLElement;
  private leads: FranchiseLead[] = [];
  private stats: FranchiseStats = { total_leads: 0, active_franchises: 0, total_earnings: 0 };
  private loading: boolean = true;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadData();
  }

  private async loadData(): Promise<void> {
    this.loading = true;
    this.updateContent();

    try {
      const response = await apiService.get<any>('/crm/unified-my-leads?segment=my&role=mnr&category=franchise');
      
      if (response.success && response.data) {
        const rawLeads = response.data.leads || response.data || [];
        this.leads = rawLeads.map((l: any) => ({
          id: l.id,
          name: l.name || '',
          status: l.status || 'new',
          created_at: l.created_at || ''
        }));

        const activeStatuses = ['converted', 'active', 'won'];
        const activeFranchises = this.leads.filter(l => activeStatuses.includes(l.status.toLowerCase()));
        
        this.stats = {
          total_leads: this.leads.length,
          active_franchises: activeFranchises.length,
          total_earnings: activeFranchises.length * 0
        };
      }

      const earningsRes = await apiService.get<any>('/users/earnings-summary');
      if (earningsRes.success && earningsRes.data) {
        const d = earningsRes.data;
        this.stats.total_earnings = typeof d.franchise_earnings === 'number' ? d.franchise_earnings : 0;
      }
    } catch (error) {
      console.error('[MNRFranchiseEarnings] Failed to load:', error);
    }

    this.loading = false;
    this.updateContent();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container franchise-page">
        ${PageHeader.render({ title: '🏪 Franchise Earnings', showBack: true })}
        
        <div id="pageContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
    `;

    PageHeader.attachListeners({ title: '🏪 Franchise Earnings', showBack: true });
  }

  private updateContent(): void {
    const content = document.getElementById('pageContent');
    if (!content) return;

    if (this.loading) {
      content.innerHTML = '<div class="loading-state">Loading...</div>';
      return;
    }

    content.innerHTML = `
      <style>
        .mentorial-hub-hero {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
          border-radius: 20px;
          padding: 24px 20px;
          margin-bottom: 20px;
          text-align: center;
          color: white;
          position: relative;
          overflow: hidden;
        }
        .mentorial-hub-hero::before {
          content: '';
          position: absolute;
          top: -50%;
          left: -50%;
          width: 200%;
          height: 200%;
          background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 60%);
          animation: pulse 4s ease-in-out infinite;
        }
        @keyframes pulse {
          0%, 100% { transform: scale(1); opacity: 0.5; }
          50% { transform: scale(1.1); opacity: 0.8; }
        }
        .mentorial-hub-hero .hero-badge {
          display: inline-block;
          background: rgba(255,255,255,0.25);
          padding: 6px 16px;
          border-radius: 20px;
          font-size: 11px;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 1px;
          margin-bottom: 12px;
        }
        .mentorial-hub-hero h1 {
          font-size: 28px;
          font-weight: 800;
          margin: 0 0 8px;
          text-shadow: 0 2px 10px rgba(0,0,0,0.2);
        }
        .mentorial-hub-hero .hero-subtitle {
          font-size: 15px;
          opacity: 0.95;
          margin: 0 0 16px;
        }
        .mentorial-hub-hero .hero-tagline {
          background: rgba(255,255,255,0.2);
          border-radius: 12px;
          padding: 12px 16px;
          font-size: 14px;
          font-weight: 600;
          backdrop-filter: blur(10px);
        }
        .mentorial-hub-hero .hero-tagline .number {
          font-size: 24px;
          font-weight: 800;
          color: #fbbf24;
        }
        
        .income-streams-title {
          text-align: center;
          color: #e6f1ff;
          font-size: 16px;
          font-weight: 700;
          margin: 24px 0 16px;
        }
        .income-streams-title span { color: #fbbf24; }
        
        .income-streams-grid {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 10px;
          margin-bottom: 10px;
        }
        .income-streams-grid.row-2 {
          grid-template-columns: repeat(2, 1fr);
          max-width: 70%;
          margin: 0 auto 20px;
        }
        .income-stream-card {
          background: rgba(22, 33, 62, 0.9);
          border-radius: 14px;
          padding: 16px 10px;
          text-align: center;
          border: 1px solid rgba(255,255,255,0.1);
          transition: all 0.3s;
        }
        .income-stream-card:hover {
          transform: translateY(-2px);
          border-color: rgba(102, 126, 234, 0.5);
        }
        .income-stream-card .stream-icon {
          width: 44px;
          height: 44px;
          border-radius: 12px;
          display: flex;
          align-items: center;
          justify-content: center;
          margin: 0 auto 10px;
          font-size: 22px;
        }
        .income-stream-card.ev .stream-icon { background: linear-gradient(135deg, #10b981, #059669); }
        .income-stream-card.solar .stream-icon { background: linear-gradient(135deg, #f59e0b, #d97706); }
        .income-stream-card.insurance .stream-icon { background: linear-gradient(135deg, #3b82f6, #2563eb); }
        .income-stream-card.training .stream-icon { background: linear-gradient(135deg, #8b5cf6, #7c3aed); }
        .income-stream-card.realestate .stream-icon { background: linear-gradient(135deg, #ec4899, #db2777); }
        .income-stream-card .stream-name {
          color: #e6f1ff;
          font-size: 11px;
          font-weight: 600;
          line-height: 1.3;
        }
        
        .lifetime-income-section {
          background: linear-gradient(135deg, #0d1b2a 0%, #1b2838 100%);
          border: 2px solid;
          border-image: linear-gradient(135deg, #fbbf24, #f59e0b) 1;
          border-radius: 16px;
          padding: 20px;
          margin-bottom: 20px;
          text-align: center;
        }
        .lifetime-income-section h3 {
          color: #fbbf24;
          font-size: 18px;
          font-weight: 700;
          margin: 0 0 16px;
        }
        .lifetime-income-section h3 span { color: #e6f1ff; font-weight: 500; }
        
        .earning-rates {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 12px;
          margin-bottom: 16px;
        }
        .earning-rate-card {
          background: rgba(255,255,255,0.05);
          border-radius: 12px;
          padding: 16px;
        }
        .earning-rate-card .rate-label {
          color: #8892b0;
          font-size: 11px;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          margin-bottom: 6px;
        }
        .earning-rate-card .rate-value {
          font-size: 36px;
          font-weight: 800;
          background: linear-gradient(135deg, #10b981, #34d399);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
        }
        .earning-rate-card .rate-desc {
          color: #8892b0;
          font-size: 11px;
          margin-top: 4px;
        }
        .earning-rate-card.lifetime .rate-value {
          background: linear-gradient(135deg, #fbbf24, #f59e0b);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
        }
        
        .lifetime-badge {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          background: linear-gradient(135deg, #fbbf24, #f59e0b);
          color: #451a03;
          padding: 10px 20px;
          border-radius: 30px;
          font-size: 13px;
          font-weight: 700;
        }
        
        .terms-card {
          background: rgba(22, 33, 62, 0.8);
          border-radius: 14px;
          padding: 18px;
          margin-bottom: 20px;
        }
        .terms-card h4 {
          color: #e6f1ff;
          font-size: 14px;
          margin: 0 0 14px;
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .terms-card ul {
          margin: 0;
          padding: 0;
          list-style: none;
        }
        .terms-card li {
          display: flex;
          align-items: flex-start;
          gap: 10px;
          color: #8892b0;
          font-size: 12px;
          margin-bottom: 10px;
          line-height: 1.5;
        }
        .terms-card li .check { color: #10b981; font-size: 14px; flex-shrink: 0; }
        
        .charges-card {
          background: linear-gradient(135deg, rgba(251, 191, 36, 0.1) 0%, rgba(245, 158, 11, 0.1) 100%);
          border: 1px solid rgba(251, 191, 36, 0.3);
          border-radius: 14px;
          padding: 18px;
          margin-bottom: 20px;
        }
        .charges-card h4 {
          color: #fbbf24;
          font-size: 14px;
          margin: 0 0 12px;
        }
        .charges-card ul {
          margin: 0;
          padding: 0;
          list-style: none;
        }
        .charges-card li {
          color: #fcd34d;
          font-size: 12px;
          margin-bottom: 8px;
          padding-left: 18px;
          position: relative;
        }
        .charges-card li::before {
          content: '•';
          position: absolute;
          left: 0;
          color: #f59e0b;
        }
        .charges-card .terms-note {
          margin: 14px 0 6px;
          font-size: 10px;
          color: rgba(156, 163, 175, 0.85);
          line-height: 1.5;
          font-style: italic;
        }
        .charges-card .terms-apply {
          margin: 0;
          font-size: 10px;
          color: rgba(156, 163, 175, 0.7);
          font-style: italic;
        }
        
        .stats-section {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 10px;
          margin-bottom: 20px;
        }
        .stat-box {
          background: rgba(22, 33, 62, 0.8);
          border-radius: 12px;
          padding: 16px 10px;
          text-align: center;
        }
        .stat-box .value {
          font-size: 22px;
          font-weight: 700;
          color: #10b981;
        }
        .stat-box .label {
          color: #8892b0;
          font-size: 10px;
          margin-top: 4px;
          text-transform: uppercase;
        }
        
        .cta-card {
          background: linear-gradient(135deg, #10b981 0%, #059669 100%);
          border-radius: 16px;
          padding: 24px 20px;
          text-align: center;
          color: white;
          margin-bottom: 20px;
        }
        .cta-card h4 {
          margin: 0 0 8px;
          font-size: 18px;
        }
        .cta-card p {
          margin: 0 0 16px;
          font-size: 13px;
          opacity: 0.9;
        }
        .cta-card .btn-cta {
          background: white;
          color: #059669;
          border: none;
          padding: 12px 28px;
          border-radius: 30px;
          font-size: 14px;
          font-weight: 700;
          cursor: pointer;
          display: inline-flex;
          align-items: center;
          gap: 8px;
        }
        
        .leads-section h3 {
          color: #e6f1ff;
          font-size: 15px;
          margin: 24px 0 12px;
        }
        .lead-row {
          background: rgba(22, 33, 62, 0.8);
          border-radius: 10px;
          padding: 14px;
          margin-bottom: 10px;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        .lead-row .name { color: #e6f1ff; font-weight: 600; font-size: 14px; }
        .lead-row .date { color: #8892b0; font-size: 11px; margin-top: 2px; }
        .lead-row .status {
          padding: 4px 10px;
          border-radius: 12px;
          font-size: 10px;
          font-weight: 600;
          text-transform: uppercase;
        }
        .lead-row .status.new { background: #3b82f6; color: white; }
        .lead-row .status.contacted { background: #f59e0b; color: white; }
        .lead-row .status.won, .lead-row .status.active { background: #10b981; color: white; }
      </style>
      
      <div class="mentorial-hub-hero">
        <div class="hero-badge">🏆 Premium Opportunity</div>
        <h1>Mentorial Hub</h1>
        <p class="hero-subtitle">One Franchise. Five Income Streams. Unlimited Potential.</p>
        <div class="hero-tagline">
          <span class="number">5</span> Business Verticals in <span class="number">1</span> Franchise
        </div>
      </div>
      
      <h4 class="income-streams-title">🔥 <span>Five Income Streams</span> Under One Roof</h4>
      
      <div class="income-streams-grid">
        <div class="income-stream-card ev">
          <div class="stream-icon">⚡</div>
          <div class="stream-name">EV Franchise</div>
        </div>
        <div class="income-stream-card solar">
          <div class="stream-icon">☀️</div>
          <div class="stream-name">Solar Franchise</div>
        </div>
        <div class="income-stream-card insurance">
          <div class="stream-icon">🛡️</div>
          <div class="stream-name">Insurance</div>
        </div>
      </div>
      <div class="income-streams-grid row-2">
        <div class="income-stream-card training">
          <div class="stream-icon">📚</div>
          <div class="stream-name">Training Academy</div>
        </div>
        <div class="income-stream-card realestate">
          <div class="stream-icon">🏠</div>
          <div class="stream-name">Real Estate</div>
        </div>
      </div>
      
      <div class="lifetime-income-section">
        <h3>💰 <span>Your Earning Potential</span></h3>
        <div class="earning-rates">
          <div class="earning-rate-card">
            <div class="rate-label">Setup Bonus</div>
            <div class="rate-value">2%</div>
            <div class="rate-desc">On initial franchise setup</div>
          </div>
          <div class="earning-rate-card lifetime">
            <div class="rate-label">Lifetime Revenue</div>
            <div class="rate-value">1%</div>
            <div class="rate-desc">On all future invoices</div>
          </div>
        </div>
        <div class="lifetime-badge">
          ♾️ Lifetime Passive Income Opportunity
        </div>
      </div>
      
      <div class="terms-card">
        <h4>📋 Eligibility for Lifetime Income</h4>
        <ul>
          <li><span class="check">✅</span> Franchise orders minimum <strong>5 units</strong> in any consecutive 2 months</li>
          <li><span class="check">✅</span> Maintain <strong>regular coordination</strong> with your franchise partner</li>
          <li><span class="check">✅</span> <strong>Showroom engagement</strong> - participate in customer interactions</li>
          <li><span class="check">✅</span> <strong>Support promotions</strong> and business initiatives</li>
          <li><span class="check">✅</span> Keep your <strong>MNR membership active</strong></li>
        </ul>
      </div>
      
      <div class="charges-card">
        <h4>⚠️ Applicable Charges</h4>
        <ul>
          <li><strong>1 Point = ₹1</strong> (Direct INR value)</li>
          <li><strong>2% TDS</strong> on all earnings</li>
          <li><strong>8% Admin Charges</strong> as per policy</li>
          <li>Subject to franchise compliance & order fulfillment</li>
        </ul>
        <p class="terms-note">*Above-mentioned percentage earnings are applicable on EV models and vehicles only. For other segments (Solar, Insurance, Real Estate, Training Academy), the earning structure will be decided from time to time.</p>
        <p class="terms-apply">Terms and conditions apply.</p>
      </div>
      
      <div class="stats-section">
        <div class="stat-box">
          <div class="value">${this.stats.total_leads}</div>
          <div class="label">Your Leads</div>
        </div>
        <div class="stat-box">
          <div class="value">${this.stats.active_franchises}</div>
          <div class="label">Active</div>
        </div>
        <div class="stat-box">
          <div class="value">₹${this.stats.total_earnings.toLocaleString()}</div>
          <div class="label">Earnings</div>
        </div>
      </div>
      
      <div class="cta-card">
        <h4>🚀 Start Earning Today</h4>
        <p>Refer a Mentorial Hub franchise partner and unlock lifetime passive income!</p>
        <button class="btn-cta" id="btnAddFranchiseLead">
          ➕ Add Franchise Lead
        </button>
      </div>
      
      ${this.leads.length > 0 ? `
        <div class="leads-section">
          <h3>📋 Your Franchise Leads</h3>
          ${this.leads.map(lead => `
            <div class="lead-row">
              <div>
                <div class="name">${lead.name}</div>
                <div class="date">${this.formatDate(lead.created_at)}</div>
              </div>
              <span class="status ${lead.status.toLowerCase()}">${lead.status}</span>
            </div>
          `).join('')}
        </div>
      ` : ''}
    `;

    this.attachEventListeners();
  }

  private attachEventListeners(): void {
    const addLeadBtn = document.getElementById('btnAddFranchiseLead');
    if (addLeadBtn) {
      addLeadBtn.addEventListener('click', () => this.showAddLeadModal());
    }
  }

  private async showAddLeadModal(): Promise<void> {
    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.innerHTML = `
      <div class="modal-content">
        <div class="modal-header">
          <h3>Add Franchise Lead</h3>
          <button class="modal-close">&times;</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>Name *</label>
            <input type="text" id="franchiseLeadName" placeholder="Lead name" required>
          </div>
          <div class="form-group">
            <label>Mobile *</label>
            <input type="tel" id="franchiseLeadMobile" placeholder="Mobile number" required>
          </div>
          <div class="form-group">
            <label>Email</label>
            <input type="email" id="franchiseLeadEmail" placeholder="Email address">
          </div>
          <div class="form-group">
            <label>City/Location</label>
            <input type="text" id="franchiseLeadCity" placeholder="City or location">
          </div>
          <div class="form-group">
            <label>Notes</label>
            <textarea id="franchiseLeadNotes" placeholder="Additional notes about the franchise interest..." rows="3"></textarea>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" id="btnCancelFranchiseLead">Cancel</button>
          <button class="btn-primary" id="btnSaveFranchiseLead">Add Lead</button>
        </div>
      </div>
    `;

    document.body.appendChild(modal);

    modal.querySelector('.modal-close')?.addEventListener('click', () => modal.remove());
    modal.querySelector('#btnCancelFranchiseLead')?.addEventListener('click', () => modal.remove());
    modal.querySelector('#btnSaveFranchiseLead')?.addEventListener('click', () => this.saveFranchiseLead(modal));
    modal.addEventListener('click', (e) => {
      if (e.target === modal) modal.remove();
    });
  }

  private async saveFranchiseLead(modal: HTMLElement): Promise<void> {
    const name = (document.getElementById('franchiseLeadName') as HTMLInputElement)?.value?.trim();
    const mobile = (document.getElementById('franchiseLeadMobile') as HTMLInputElement)?.value?.trim();
    const email = (document.getElementById('franchiseLeadEmail') as HTMLInputElement)?.value?.trim();
    const city = (document.getElementById('franchiseLeadCity') as HTMLInputElement)?.value?.trim();
    const notes = (document.getElementById('franchiseLeadNotes') as HTMLTextAreaElement)?.value?.trim();

    if (!name || !mobile) {
      alert('Please enter name and mobile number');
      return;
    }

    try {
      const response = await apiService.post<any>('/crm/unified-my-leads?role=mnr', {
        name,
        mobile,
        email,
        category: 'franchise',
        priority: 'high',
        notes: notes ? `Location: ${city || 'N/A'}\n${notes}` : (city ? `Location: ${city}` : ''),
        source: 'mobile_app'
      });

      if (response.success) {
        modal.remove();
        await this.loadData();
      } else {
        alert(response.error || 'Failed to add franchise lead');
      }
    } catch (error) {
      console.error('[MNRFranchiseEarnings] Add lead failed:', error);
      alert('Failed to add franchise lead. Please try again.');
    }
  }

  private formatDate(dateStr: string): string {
    if (!dateStr) return '';
    try {
      return new Date(dateStr).toLocaleDateString('en-IN', {
        day: 'numeric',
        month: 'short',
        year: 'numeric'
      });
    } catch {
      return dateStr;
    }
  }
}
