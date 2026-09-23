/**
 * Category Leads Master Page (Mobile View)
 * DC Protocol: DC_MOBILE_STAFF_CATEGORY_MASTER_001
 * Comprehensive mobile interface for Category Lead Master & All Vertical Leads
 * Full parity with web staff_mnr_leads_master.html:
 * - Tabs for Solar, EV B2B, EV B2C, EV Spares, Real Dreams, Insurance, ETC Training, MNR Leads, All
 * - Respects active tab from route params (e.g. from SideDrawer workflow links)
 * - Supreme Admin MR10001 full access & phone eye unmasking
 * - One-tap Calling via Softphone & Unified WhatsApp Modal
 */

import { apiService } from '../services/api.service';
import { authService } from '../services/auth.service';
import { PageHeader } from '../components/PageHeader';
import { routerService } from '../services/router.service';
import { callController } from '../services/call-controller';
import { unifiedWAModal } from '../components/UnifiedWAModal';
import { UniversalLeadHistoryModal } from '../components/UniversalLeadHistoryModal';

interface LeadItem {
  id: number;
  customer_name?: string;
  name?: string;
  phone_number?: string;
  customer_phone?: string;
  phone?: string;
  category?: string;
  status?: string;
  solar_pipeline_status?: string;
  ev_b2b_stage?: string;
  subsidy_status?: string;
  deal_value?: number;
  city?: string;
  district?: string;
  area?: string;
  address?: string;
  telecaller_name?: string;
  field_staff_name?: string;
  ground_source_name?: string;
  created_at?: string;
  [key: string]: any;
}

interface CategoryTab {
  key: string;
  label: string;
  category: string;
  icon: string;
  badgeColor: string;
}

export class CategoryLeadsMasterPage {
  private container: HTMLElement;
  private leads: LeadItem[] = [];
  private loading: boolean = true;
  private currentTab: string = 'solar';
  private searchQuery: string = '';
  private selectedStatus: string = 'ALL';
  private currentPage: number = 1;
  private totalPages: number = 1;
  private totalCount: number = 0;
  private revealedPhones: Set<string> = new Set();

  private tabs: CategoryTab[] = [
    { key: 'solar', label: 'Solar', category: 'Solar', icon: 'fa-solar-panel', badgeColor: '#f59e0b' },
    { key: 'ev-b2b', label: 'EV B2B', category: 'EV B2B', icon: 'fa-truck', badgeColor: '#3b82f6' },
    { key: 'ev-b2c', label: 'EV B2C', category: 'EV B2C', icon: 'fa-car', badgeColor: '#10b981' },
    { key: 'ev-spares', label: 'EV Spares', category: 'EV Spares', icon: 'fa-cogs', badgeColor: '#8b5cf6' },
    { key: 'real-dreams', label: 'Real Dreams', category: 'Real Dreams', icon: 'fa-home', badgeColor: '#ef4444' },
    { key: 'insurance', label: 'Insurance', category: 'Insurance', icon: 'fa-shield-alt', badgeColor: '#0ea5e9' },
    { key: 'etc', label: 'ETC Training', category: 'ETC Training', icon: 'fa-graduation-cap', badgeColor: '#059669' },
    { key: 'mnr', label: 'MNR Leads', category: 'MNR Leads', icon: 'fa-users', badgeColor: '#6366f1' },
    { key: 'all', label: 'All Leads', category: '', icon: 'fa-layer-group', badgeColor: '#64748b' }
  ];

  constructor(container: HTMLElement) {
    this.container = container;
    this.init();
  }

  private init(): void {
    const params = routerService.getRouteParams();
    if (params && params.tab) {
      const matched = this.tabs.find(t => t.key.toLowerCase() === params.tab.toLowerCase());
      if (matched) {
        this.currentTab = matched.key;
      }
    }
    this.loadLeads();
  }

  private fmtNum(n: number | undefined | null): string {
    return Number(n || 0).toLocaleString('en-IN');
  }

  private fmtVal(n: number | undefined | null): string {
    const val = parseFloat(String(n || 0));
    if (isNaN(val) || val === 0) return '₹0';
    if (val >= 100000) return '₹' + (val / 100000).toFixed(2) + ' L';
    return '₹' + val.toLocaleString('en-IN');
  }

  private getActiveTab(): CategoryTab {
    return this.tabs.find(t => t.key === this.currentTab) || this.tabs[0];
  }

  private getLeadPhone(lead: LeadItem): string {
    return lead.phone_number || lead.customer_phone || lead.phone || '';
  }

  private getLeadName(lead: LeadItem): string {
    return lead.customer_name || lead.name || 'Customer Lead';
  }

  private isPhoneRevealed(phone: string): boolean {
    if (authService.isMR10001()) return true;
    const clean = phone.replace(/\D/g, '').slice(-10);
    return this.revealedPhones.has(clean);
  }

  private formatPhone(phone: string): string {
    if (!phone) return '—';
    const clean = phone.replace(/\D/g, '');
    if (clean.length < 6) return phone;
    const clean10 = clean.slice(-10);

    if (this.isPhoneRevealed(phone)) {
      return clean10.length === 10 ? `+91 ${clean10.slice(0, 5)} ${clean10.slice(5)}` : phone;
    }
    return `+91 ${clean10.slice(0, 2)}••••${clean10.slice(-4)}`;
  }

  private async loadLeads(): Promise<void> {
    this.loading = true;
    this.render();

    try {
      const activeTab = this.getActiveTab();
      const p = new URLSearchParams();
      if (activeTab.category) {
        p.set('category', activeTab.category);
      }
      if (this.searchQuery.trim()) {
        p.set('search', this.searchQuery.trim());
      }
      if (this.selectedStatus && this.selectedStatus !== 'ALL') {
        p.set('status', this.selectedStatus);
      }
      p.set('page', String(this.currentPage));
      p.set('per_page', '20');

      const resp = await apiService.get<any>(`/crm/master-leads?${p.toString()}`);
      if (resp && resp.success !== false) {
        const d = resp.data || resp;
        this.leads = Array.isArray(d.data) ? d.data : Array.isArray(d) ? d : [];
        const pg = d.pagination || {};
        this.totalCount = pg.total || this.leads.length;
        this.totalPages = pg.total_pages || Math.ceil(this.totalCount / 20) || 1;
      } else {
        this.leads = [];
        this.totalCount = 0;
        this.totalPages = 1;
      }
    } catch (e) {
      console.error('[CategoryLeadsMasterPage] Error loading leads:', e);
      this.leads = [];
    } finally {
      this.loading = false;
      this.render();
    }
  }

  private render(): void {
    const activeTab = this.getActiveTab();

    this.container.innerHTML = `
      <div class="category-leads-container" style="background:#0b1329; min-height:100vh; padding-bottom:80px; color:#f1f5f9; font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;">
        ${PageHeader.render({
          title: 'Category Lead Master',
          subtitle: `${activeTab.label} • ${this.fmtNum(this.totalCount)} Leads`,
          showMenu: true,
          showBack: true
        })}

        <div style="padding:12px 14px;">
          <!-- Horizontal Scrollable Tabs Bar -->
          <div style="display:flex; gap:6px; overflow-x:auto; padding-bottom:6px; margin-bottom:12px; -webkit-overflow-scrolling:touch;">
            ${this.tabs.map(t => {
              const active = t.key === this.currentTab;
              const bg = active ? t.badgeColor : '#1e293b';
              const color = active ? '#ffffff' : '#94a3b8';
              const border = active ? `1px solid ${t.badgeColor}` : '1px solid #334155';
              return `
                <button class="cat-tab-btn ${active ? 'active' : ''}" data-tab="${t.key}" style="background:${bg}; color:${color}; border:${border}; border-radius:20px; padding:6px 14px; font-size:12px; font-weight:700; white-space:nowrap; cursor:pointer; display:flex; align-items:center; gap:6px; transition:all 0.15s ease;">
                  <i class="fas ${t.icon}"></i> ${t.label}
                </button>
              `;
            }).join('')}
          </div>

          <!-- Search & Filter Bar -->
          <div style="background:#1e293b; border:1px solid #334155; border-radius:12px; padding:10px 12px; margin-bottom:14px; display:flex; flex-direction:column; gap:8px;">
            <div style="display:flex; gap:8px; align-items:center;">
              <div style="flex:1; position:relative;">
                <input type="text" id="catSearchInput" placeholder="Search name, phone, city, handler..." value="${this.searchQuery}" style="width:100%; background:#0f172a; border:1px solid #334155; color:#f1f5f9; border-radius:8px; padding:8px 12px 8px 32px; font-size:12px;">
                <i class="fas fa-search" style="position:absolute; left:10px; top:11px; color:#64748b; font-size:12px;"></i>
              </div>
              <button id="catSearchBtn" style="background:#2563eb; color:white; border:none; border-radius:8px; padding:8px 14px; font-size:12px; font-weight:700; cursor:pointer;">
                Search
              </button>
            </div>

            <!-- Quick Status Filter Row -->
            <div style="display:flex; gap:6px; overflow-x:auto; padding-bottom:2px; -webkit-overflow-scrolling:touch;">
              ${['ALL', 'won', 'contacted', 'interested', 'new', 'proposal', 'lost'].map(st => {
                const active = this.selectedStatus.toLowerCase() === st.toLowerCase();
                const label = st === 'ALL' ? 'All Status' : st.charAt(0).toUpperCase() + st.slice(1);
                return `
                  <button class="status-chip ${active ? 'active' : ''}" data-status="${st}" style="background:${active ? '#38bdf8' : '#0f172a'}; color:${active ? '#0b1329' : '#94a3b8'}; border:1px solid ${active ? '#38bdf8' : '#334155'}; border-radius:14px; padding:3px 10px; font-size:11px; font-weight:600; white-space:nowrap; cursor:pointer;">
                    ${label}
                  </button>
                `;
              }).join('')}
            </div>
          </div>

          <!-- Leads Count & Meta Line -->
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; font-size:12px; color:#94a3b8; padding:0 2px;">
            <div>Showing <span style="color:#ffffff; font-weight:700;">${this.leads.length}</span> of <span style="color:#38bdf8; font-weight:700;">${this.fmtNum(this.totalCount)}</span> leads</div>
            <button id="catRefreshListBtn" style="background:transparent; border:none; color:#38bdf8; font-size:12px; cursor:pointer; font-weight:600; display:flex; align-items:center; gap:4px;">
              <i class="fas fa-sync-alt ${this.loading ? 'fa-spin' : ''}"></i> Refresh
            </button>
          </div>

          ${this.loading ? `
            <div style="text-align:center; padding:48px 16px;">
              <i class="fas fa-circle-notch fa-spin" style="font-size:28px; color:#38bdf8; margin-bottom:12px;"></i>
              <div style="color:#94a3b8; font-size:13px; font-weight:500;">Loading ${activeTab.label} master leads...</div>
            </div>
          ` : this.leads.length === 0 ? `
            <div style="background:#1e293b; border:1px solid #334155; border-radius:12px; padding:36px 16px; text-align:center;">
              <i class="fas fa-folder-open" style="font-size:36px; color:#64748b; margin-bottom:12px;"></i>
              <div style="font-size:14px; font-weight:700; color:#ffffff; margin-bottom:4px;">No leads found</div>
              <div style="font-size:12px; color:#94a3b8;">Try changing your search keywords or switching category tabs.</div>
            </div>
          ` : `
            <!-- Leads List -->
            <div style="display:flex; flex-direction:column; gap:10px;">
              ${this.leads.map(lead => this.renderLeadCard(lead)).join('')}
            </div>

            <!-- Pagination Bar -->
            <div style="display:flex; justify-content:space-between; align-items:center; margin-top:16px; background:#1e293b; border:1px solid #334155; border-radius:10px; padding:8px 14px;">
              <button id="catPrevPageBtn" ${this.currentPage <= 1 ? 'disabled' : ''} style="background:${this.currentPage <= 1 ? '#0f172a' : '#2563eb'}; color:${this.currentPage <= 1 ? '#475569' : '#ffffff'}; border:none; border-radius:6px; padding:6px 14px; font-size:12px; font-weight:700; cursor:${this.currentPage <= 1 ? 'not-allowed' : 'pointer'};">
                <i class="fas fa-chevron-left"></i> Prev
              </button>
              <div style="font-size:12px; color:#94a3b8; font-weight:600;">
                Page <span style="color:#ffffff;">${this.currentPage}</span> of <span style="color:#ffffff;">${this.totalPages}</span>
              </div>
              <button id="catNextPageBtn" ${this.currentPage >= this.totalPages ? 'disabled' : ''} style="background:${this.currentPage >= this.totalPages ? '#0f172a' : '#2563eb'}; color:${this.currentPage >= this.totalPages ? '#475569' : '#ffffff'}; border:none; border-radius:6px; padding:6px 14px; font-size:12px; font-weight:700; cursor:${this.currentPage >= this.totalPages ? 'not-allowed' : 'pointer'};">
                Next <i class="fas fa-chevron-right"></i>
              </button>
            </div>
          `}
        </div>
      </div>
    `;

    PageHeader.attachListeners({
      title: 'Category Lead Master',
      showMenu: true,
      showBack: true
    });

    this.attachEventListeners();
  }

  private renderLeadCard(lead: LeadItem): string {
    const name = this.getLeadName(lead);
    const phone = this.getLeadPhone(lead);
    const cleanPhone = phone.replace(/\D/g, '').slice(-10);
    const isRevealed = this.isPhoneRevealed(phone);
    const formattedPhone = this.formatPhone(phone);
    const cat = lead.category || 'General';
    const status = (lead.status || 'new').toUpperCase();
    const stage = lead.solar_pipeline_status || lead.ev_b2b_stage || lead.subsidy_status || '';
    const formattedStage = stage ? stage.replace(/_/g, ' ').toUpperCase() : '';
    const city = lead.city || lead.district || lead.area || '';
    const dealVal = lead.deal_value ? this.fmtVal(lead.deal_value) : '';
    const handler = lead.telecaller_name || lead.field_staff_name || lead.ground_source_name || '';

    const statusBg = status === 'WON' ? '#064e3b' : status === 'LOST' ? '#7f1d1d' : '#1e3a8a';
    const statusColor = status === 'WON' ? '#34d399' : status === 'LOST' ? '#f87171' : '#60a5fa';

    return `
      <div style="background:#1e293b; border:1px solid #334155; border-radius:12px; padding:14px; box-shadow:0 2px 8px rgba(0,0,0,0.2);">
        <!-- Top Row: Name, ID, Category Badge -->
        <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:6px;">
          <div>
            <div style="font-size:14px; font-weight:700; color:#ffffff; line-height:1.3;">${name}</div>
            <div style="display:flex; align-items:center; gap:6px; margin-top:2px;">
              <span style="font-size:10px; background:#0f172a; border:1px solid #334155; color:#94a3b8; border-radius:4px; padding:1px 5px; font-weight:700;">#${lead.id}</span>
              <span style="font-size:10px; color:#38bdf8; font-weight:600;"><i class="fas fa-tag"></i> ${cat}</span>
              ${city ? `<span style="font-size:10px; color:#94a3b8;"><i class="fas fa-map-marker-alt"></i> ${city}</span>` : ''}
            </div>
          </div>
          <span style="background:${statusBg}; color:${statusColor}; font-size:10px; font-weight:800; padding:2px 8px; border-radius:12px; letter-spacing:0.3px; border:1px solid ${statusColor}44;">
            ${status}
          </span>
        </div>

        <!-- Phone with Eye Toggle -->
        <div style="display:flex; align-items:center; gap:8px; margin:8px 0; background:#0f172a; border-radius:8px; padding:7px 10px;">
          <i class="fas fa-phone-alt" style="color:#38bdf8; font-size:11px;"></i>
          <span style="font-size:12px; font-weight:600; color:#e2e8f0; font-family:monospace; letter-spacing:0.5px;">${formattedPhone}</span>
          ${phone ? `
            <button class="eye-toggle-btn" data-phone="${cleanPhone}" title="${isRevealed ? 'Mask phone' : 'Reveal phone'}" style="background:transparent; border:none; color:#94a3b8; cursor:pointer; padding:0 4px; font-size:12px;">
              <i class="fas ${isRevealed ? 'fa-eye-slash' : 'fa-eye'}"></i>
            </button>
          ` : ''}
          ${dealVal ? `
            <span style="margin-left:auto; font-size:12px; font-weight:800; color:#34d399;">${dealVal}</span>
          ` : ''}
        </div>

        <!-- Meta Details: Stage, Handlers -->
        <div style="font-size:11px; color:#94a3b8; margin-bottom:10px; display:flex; flex-direction:column; gap:2px;">
          ${formattedStage ? `
            <div><strong style="color:#cbd5e1;">Stage:</strong> <span style="color:#fbbf24; font-weight:600;">${formattedStage}</span></div>
          ` : ''}
          ${handler ? `
            <div><strong style="color:#cbd5e1;">Handler:</strong> <span style="color:#e2e8f0;">${handler}</span></div>
          ` : ''}
        </div>

        <!-- Action Buttons: Softphone Call, WhatsApp, Universal History -->
        <div style="display:flex; gap:6px; border-top:1px solid #334155; padding-top:10px;">
          <button class="action-call-btn" data-phone="${cleanPhone}" data-name="${name.replace(/"/g, '&quot;')}" data-id="${lead.id}" style="flex:1; background:#0284c7; color:white; border:none; border-radius:8px; padding:8px 8px; font-size:11px; font-weight:700; cursor:pointer; display:flex; align-items:center; justify-content:center; gap:4px;">
            <i class="fas fa-headset"></i> Call
          </button>
          <button class="action-wa-btn" data-phone="${cleanPhone}" data-name="${name.replace(/"/g, '&quot;')}" data-id="${lead.id}" data-cat="${cat}" style="flex:1; background:#059669; color:white; border:none; border-radius:8px; padding:8px 8px; font-size:11px; font-weight:700; cursor:pointer; display:flex; align-items:center; justify-content:center; gap:4px;">
            <i class="fab fa-whatsapp"></i> WA
          </button>
          <button class="action-history-btn" data-phone="${cleanPhone}" data-name="${name.replace(/"/g, '&quot;')}" data-id="${lead.id}" data-cat="${cat}" style="background:#4f46e5; color:white; border:none; border-radius:8px; padding:8px 10px; font-size:11px; font-weight:700; cursor:pointer; display:flex; align-items:center; justify-content:center; gap:4px;" title="Universal History">
            <i class="fas fa-history"></i> History
          </button>
        </div>
      </div>
    `;
  }

  private attachEventListeners(): void {
    // Tab switching
    this.container.querySelectorAll('.cat-tab-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const target = e.currentTarget as HTMLElement;
        const tab = target.dataset.tab;
        if (tab && tab !== this.currentTab) {
          this.currentTab = tab;
          this.currentPage = 1;
          this.loadLeads();
        }
      });
    });

    // Search button
    document.getElementById('catSearchBtn')?.addEventListener('click', () => {
      const input = document.getElementById('catSearchInput') as HTMLInputElement;
      this.searchQuery = input ? input.value : '';
      this.currentPage = 1;
      this.loadLeads();
    });

    // Search enter key
    document.getElementById('catSearchInput')?.addEventListener('keyup', (e: KeyboardEvent) => {
      if (e.key === 'Enter') {
        const input = e.target as HTMLInputElement;
        this.searchQuery = input.value;
        this.currentPage = 1;
        this.loadLeads();
      }
    });

    // Status filter chips
    this.container.querySelectorAll('.status-chip').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const target = e.currentTarget as HTMLElement;
        const status = target.dataset.status || 'ALL';
        this.selectedStatus = status;
        this.currentPage = 1;
        this.loadLeads();
      });
    });

    // Refresh list
    document.getElementById('catRefreshListBtn')?.addEventListener('click', () => {
      this.loadLeads();
    });

    // Pagination
    document.getElementById('catPrevPageBtn')?.addEventListener('click', () => {
      if (this.currentPage > 1) {
        this.currentPage--;
        this.loadLeads();
      }
    });

    document.getElementById('catNextPageBtn')?.addEventListener('click', () => {
      if (this.currentPage < this.totalPages) {
        this.currentPage++;
        this.loadLeads();
      }
    });

    // Eye toggle for unmasking
    this.container.querySelectorAll('.eye-toggle-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const target = e.currentTarget as HTMLElement;
        const phone = target.dataset.phone;
        if (phone) {
          if (this.revealedPhones.has(phone)) {
            this.revealedPhones.delete(phone);
          } else {
            this.revealedPhones.add(phone);
          }
          this.render();
        }
      });
    });

    // Softphone Call Trigger
    this.container.querySelectorAll('.action-call-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const target = e.currentTarget as HTMLElement;
        const phone = target.dataset.phone || '';
        const name = target.dataset.name || 'Lead Contact';
        const leadId = target.dataset.id || '';

        if (!phone) {
          alert('No valid phone number for this lead.');
          return;
        }

        if ((window as any).triggerLeadCall) {
          (window as any).triggerLeadCall(phone, name, leadId);
        } else if (callController && typeof callController.openCallDialer === 'function') {
          callController.openCallDialer({
            phoneNumber: phone,
            name: name,
            entityId: leadId,
            entityType: 'lead',
            autoStart: true
          });
        }
      });
    });

    // WhatsApp Trigger
    this.container.querySelectorAll('.action-wa-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const target = e.currentTarget as HTMLElement;
        const phone = target.dataset.phone || '';
        const name = target.dataset.name || 'Customer';
        const leadId = target.dataset.id || '';
        const context = target.dataset.cat || '';

        if (phone) {
          unifiedWAModal.open({
            phone,
            name,
            leadId,
            context
          });
        }
      });
    });

    // Universal Lead History Trigger
    this.container.querySelectorAll('.action-history-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const target = e.currentTarget as HTMLElement;
        const phone = target.dataset.phone || '';
        const name = target.dataset.name || 'Lead';
        const leadId = parseInt(target.dataset.id || '0');
        const cat = target.dataset.cat || 'Category Lead';

        if (leadId) {
          UniversalLeadHistoryModal.open({
            entityType: 'crm_lead',
            entityId: leadId,
            name,
            phone,
            category: cat
          });
        }
      });
    });
  }
}
