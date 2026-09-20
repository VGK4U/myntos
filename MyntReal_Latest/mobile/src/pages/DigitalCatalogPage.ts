/**
 * Digital Catalog Page — Mobile Web, Android & iOS Parity
 * DC Protocol: DC_MOBILE_DIGITAL_CATALOG_001
 * Full parity with desktop CRM:
 * - 8 Business Vertical Tabs (Solar, Industrial Hub, EV B2B, EV B2C, EV Spares, ETC Training, Real Dreams, Insurance)
 * - Single-page catalog details, sections count, offerings & pricing
 * - Multilingual WhatsApp dispatch modal (Option A: Web link + PDF)
 * - View personal dispatch history
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';
import { routerService } from '../services/router.service';
import { APP_CONFIG } from '../config/app.config';

interface CatalogItem {
  id: number;
  item_type: string;
  item_code?: string;
  title: string;
  subtitle?: string;
  pricing?: {
    base_price?: number;
    price_text?: string;
    subsidy_amount?: number;
    net_cost?: number;
  };
  badges?: string[];
  media_urls?: string[];
}

interface CatalogSection {
  id: number;
  section_type: string;
  section_key: string;
  title?: string;
  subtitle?: string;
}

interface Catalog {
  id: number;
  segment_code: string;
  slug: string;
  title: string;
  subtitle?: string;
  summary?: string;
  hero_media_url?: string;
  sections_count?: number;
  items_count?: number;
  sections?: CatalogSection[];
  items?: CatalogItem[];
}

export class DigitalCatalogPage {
  private container: HTMLElement;
  private catalogs: Catalog[] = [];
  private activeSegment: string = 'SOLAR';
  private activeCatalog: Catalog | null = null;
  private isLoading = true;

  private readonly verticals = [
    { code: 'SOLAR', label: 'Solar' },
    { code: 'INDUSTRIAL_HUB', label: 'MyntReal Hub' },
    { code: 'EV_B2C', label: 'EV 2W Pricing' },
    { code: 'HUB_PRICING', label: 'Hub Commercials (24h)' },
    { code: 'EV_SPARES', label: 'EV Spares' },
    { code: 'ETC_TRAINING', label: 'ETC Training' },
    { code: 'REAL_DREAMS', label: 'Real Dreams' },
    { code: 'INSURANCE', label: 'Insurance' }
  ];

  constructor(container: HTMLElement) {
    this.container = container;
  }

  public async init(params?: any): Promise<void> {
    await this.render();
  }

  public async render(): Promise<void> {
    this.container.innerHTML = `
      <div class="page-container digital-catalog-page">
        ${PageHeader.render({ title: 'Digital Catalog', showBack: true })}
        <div class="page-content p-3">
          <!-- Top Action Bar: Segment title & Dispatch History Button -->
          <div class="d-flex justify-content-between align-items-center mb-2 px-1">
            <span class="text-muted small fw-bold text-uppercase" style="letter-spacing: 0.5px; font-size: 11px;">
              <i class="fas fa-layer-group text-success me-1"></i> Catalog Models
            </span>
            <button class="btn btn-sm btn-outline-info rounded-pill px-3 fw-bold shadow-sm" id="btnOpenMobileDispatchHistory" style="font-size: 12px;">
              <i class="fas fa-history me-1"></i> Dispatch History
            </button>
          </div>

          <!-- Vertical Segments Slider -->
          <div class="d-flex gap-2 overflow-auto pb-2 mb-3 no-scrollbar" id="mobileSegmentTabs">
            ${this.verticals.map(v => `
              <button class="btn btn-sm ${v.code === this.activeSegment ? 'btn-success' : 'btn-outline-secondary'} text-nowrap rounded-pill px-3 fw-bold"
                      data-code="${v.code}" style="font-size: 13px;">
                ${v.label}
              </button>
            `).join('')}
          </div>

          <!-- Catalog Main Card -->
          <div id="catalogContentArea">
            <div class="text-center py-5">
              <div class="spinner-border text-success" role="status"></div>
              <p class="text-muted small mt-2">Loading catalogs...</p>
            </div>
          </div>
        </div>
      </div>
    `;

    PageHeader.attachListeners({
      title: 'Digital Catalog',
      showBack: true
    });

    this.bindEvents();
    await this.loadCatalogs();
  }

  private bindEvents(): void {
    const historyBtn = this.container.querySelector('#btnOpenMobileDispatchHistory');
    if (historyBtn) {
      historyBtn.addEventListener('click', () => {
        this.openMobileDispatchHistoryModal();
      });
    }

    this.container.addEventListener('click', (e) => {
      const target = e.target as HTMLElement;
      const tabBtn = target.closest('[data-code]') as HTMLElement;
      if (tabBtn) {
        const code = tabBtn.dataset.code;
        if (code && code !== this.activeSegment) {
          this.activeSegment = code;
          this.updateSegmentUI();
          this.renderActiveCatalog();
        }
      }
    });
  }

  private updateSegmentUI(): void {
    const btns = this.container.querySelectorAll('#mobileSegmentTabs button');
    btns.forEach(b => {
      const btn = b as HTMLElement;
      if (btn.dataset.code === this.activeSegment) {
        btn.className = 'btn btn-sm btn-success text-nowrap rounded-pill px-3 fw-bold';
      } else {
        btn.className = 'btn btn-sm btn-outline-secondary text-nowrap rounded-pill px-3 fw-bold';
      }
    });
  }

  private async loadCatalogs(): Promise<void> {
    try {
      this.isLoading = true;
      const res = await apiService.get<any>('/api/v1/digital-catalogs/library');
      if (res && res.catalogs) {
        this.catalogs = res.catalogs;
        this.renderActiveCatalog();
      }
    } catch (err) {
      console.error('Mobile catalog load error:', err);
      const area = this.container.querySelector('#catalogContentArea');
      if (area) {
        area.innerHTML = `
          <div class="alert alert-dark text-center">
            <p class="mb-0 text-muted">Unable to load catalog. Please check connection.</p>
          </div>
        `;
      }
    } finally {
      this.isLoading = false;
    }
  }

  private async renderActiveCatalog(): Promise<void> {
    const area = this.container.querySelector('#catalogContentArea');
    if (!area) return;

    const catSummary = this.catalogs.find(c => c.segment_code === this.activeSegment) || this.catalogs[0];
    if (!catSummary) {
      area.innerHTML = `<div class="p-4 text-center text-muted">No catalog found for ${this.activeSegment}</div>`;
      return;
    }

    // Fetch full details
    try {
      const fullRes = await apiService.get<any>(`/api/v1/digital-catalogs/${catSummary.id}`);
      this.activeCatalog = fullRes.catalog || catSummary;
    } catch {
      this.activeCatalog = catSummary;
    }

    const cat = this.activeCatalog!;
    let publicUrl = `/catalog/${cat.segment_code.toLowerCase().replace(/_/g, '-')}/${cat.slug}`;
    if (cat.segment_code === 'HUB_PRICING' || cat.slug === 'hub-ev-pricing') {
      publicUrl = '/catalog/hub-ev-pricing';
    } else if (cat.segment_code === 'EV_B2C' || cat.slug === 'ev-b2c-pricing') {
      publicUrl = '/catalog/ev-b2c-pricing';
    }

    area.innerHTML = `
      <div class="card bg-dark border-secondary border-opacity-25 rounded-4 shadow-sm mb-3">
        <div class="card-body p-3">
          <div class="d-flex justify-content-between align-items-start mb-2">
            <span class="badge bg-success bg-opacity-25 text-success rounded-pill px-2 py-1" style="font-size: 11px;">
              ${cat.segment_code}
            </span>
            <span class="badge bg-primary bg-opacity-25 text-primary rounded-pill px-2 py-1" style="font-size: 11px;">
              ${cat.sections_count || (cat.sections ? cat.sections.length : 0)} Sections
            </span>
          </div>

          <h5 class="fw-bold text-white mb-1">${cat.title}</h5>
          <p class="text-muted small mb-3">${cat.subtitle || cat.summary || ''}</p>

          <div class="d-grid gap-2">
            <button class="btn btn-success rounded-pill fw-bold py-2" id="btnMobileDispatchWhatsApp">
              <i class="fab fa-whatsapp me-1"></i> Send Catalog on WhatsApp
            </button>
            <a href="${publicUrl}" target="_blank" class="btn btn-outline-light rounded-pill fw-bold py-2" style="font-size: 13px;">
              <i class="fas fa-external-link-alt me-1"></i> Open Single-Page Web Catalog
            </a>
          </div>
        </div>
      </div>

      <!-- Offering / Products Preview -->
      <h6 class="fw-bold text-white mb-2 px-1">Offerings & Packages (${(cat.items || []).length})</h6>
      <div class="d-flex flex-column gap-2 mb-4">
        ${(cat.items && cat.items.length > 0) ? cat.items.map(it => `
          <div class="card bg-dark border-secondary border-opacity-25 rounded-3 p-2">
            <div class="d-flex justify-content-between align-items-center">
              <div>
                <div class="fw-bold text-white" style="font-size: 14px;">${it.title}</div>
                <div class="text-muted" style="font-size: 12px;">${it.subtitle || ''}</div>
              </div>
              <div class="text-end">
                <span class="fw-bold text-success" style="font-size: 14px;">
                  ${it.pricing?.price_text || (it.pricing?.base_price ? '₹' + it.pricing.base_price.toLocaleString('en-IN') : 'Enquire')}
                </span>
              </div>
            </div>
          </div>
        `).join('') : '<div class="text-muted small p-2">No items listed.</div>'}
      </div>
    `;

    const dispatchBtn = area.querySelector('#btnMobileDispatchWhatsApp');
    if (dispatchBtn) {
      dispatchBtn.addEventListener('click', () => this.openMobileDispatchModal(cat));
    }
  }

  private selectedLeadId: number | null = null;
  private selectedPartnerId: number | null = null;
  private searchDebounceTimer: any = null;

  private openMobileDispatchModal(cat: Catalog): void {
    let modalEl = document.getElementById('mobileCatalogDispatchModal');
    if (modalEl) modalEl.remove();

    this.selectedLeadId = null;
    this.selectedPartnerId = null;

    modalEl = document.createElement('div');
    modalEl.id = 'mobileCatalogDispatchModal';
    modalEl.style.cssText = `
      position: fixed; inset: 0; z-index: 10050;
      background: rgba(0, 0, 0, 0.75);
      display: flex; align-items: flex-end; justify-content: center;
      padding: 0; animation: fadeIn 0.15s ease-out;
    `;

    modalEl.innerHTML = `
      <div class="dispatch-sheet" style="
        background: #0f172a; width: 100%; max-width: 520px;
        max-height: 90vh; overflow-y: auto;
        border-top-left-radius: 20px; border-top-right-radius: 20px;
        border: 1px solid rgba(255,255,255,0.15); border-bottom: none;
        box-shadow: 0 -10px 25px rgba(0,0,0,0.5);
        color: #f8fafc; padding: 20px 16px 24px 16px;
      ">
        <!-- Header -->
        <div class="d-flex justify-content-between align-items-center mb-3 pb-2 border-bottom border-secondary border-opacity-25">
          <div class="d-flex align-items-center gap-2">
            <div style="width: 36px; height: 36px; border-radius: 50%; background: #25d366; display: flex; align-items: center; justify-content: center; color: #fff; font-size: 18px;">
              <i class="fab fa-whatsapp"></i>
            </div>
            <div>
              <h6 class="fw-bold mb-0 text-white" style="font-size: 15px;">Send via WhatsApp</h6>
              <div class="text-muted" style="font-size: 11px;">${cat.title}</div>
            </div>
          </div>
          <button id="closeDispatchModalBtn" class="btn btn-sm btn-dark text-muted rounded-circle" style="width: 32px; height: 32px; padding: 0; font-size: 16px;">
            &times;
          </button>
        </div>

        <!-- Recipient Autocomplete Search -->
        <div class="mb-3">
          <label class="form-label fw-bold small text-light mb-1">
            <i class="fas fa-search me-1 text-info"></i> Search Contact, Lead or Partner:
          </label>
          <div class="input-group input-group-sm">
            <input type="text" id="modalRecipientSearchInput" class="form-control" 
                   placeholder="Type name or 3+ digits of phone..."
                   style="background: #1e293b; color: #fff; border-color: #334155; font-size: 13px;" />
            <button class="btn btn-outline-secondary" type="button" id="modalClearSearchBtn">Clear</button>
          </div>
          <div id="modalSearchDropdown" style="display: none; background: #1e293b; border: 1px solid #334155; border-radius: 8px; max-height: 180px; overflow-y: auto; margin-top: 4px; box-shadow: 0 4px 12px rgba(0,0,0,0.4);">
            <!-- Dynamic search results -->
          </div>
        </div>

        <!-- Active Selected Recipient Pill -->
        <div id="modalSelectedCard" style="display: none; background: #13243d; border: 1px solid #0284c7; border-radius: 8px; padding: 8px 12px; margin-bottom: 12px;">
          <div class="d-flex justify-content-between align-items-center">
            <div>
              <div class="fw-bold text-white small" id="modalSelectedName">Name</div>
              <div class="text-info small" id="modalSelectedPhone" style="font-size: 11px;">+91 ...</div>
            </div>
            <button type="button" id="modalRemoveSelectedBtn" class="btn btn-sm btn-link text-danger p-0" style="font-size: 12px; text-decoration: none;">
              <i class="fas fa-times me-1"></i>Clear
            </button>
          </div>
        </div>

        <!-- Phone & Name Inputs -->
        <div class="row g-2 mb-3">
          <div class="col-7">
            <label class="form-label fw-bold text-light mb-1" style="font-size: 12px;">Mobile Number *</label>
            <input type="tel" id="modalRecipientPhone" class="form-control form-control-sm" 
                   placeholder="10-digit number"
                   style="background: #1e293b; color: #fff; border-color: #334155;" />
          </div>
          <div class="col-5">
            <label class="form-label fw-bold text-light mb-1" style="font-size: 12px;">Name (optional)</label>
            <input type="text" id="modalRecipientName" class="form-control form-control-sm" 
                   placeholder="Recipient name"
                   style="background: #1e293b; color: #fff; border-color: #334155;" />
          </div>
        </div>

        <!-- Language Selector -->
        <div class="mb-3">
          <label class="form-label fw-bold text-light mb-1" style="font-size: 12px;">
            <i class="fas fa-language me-1 text-warning"></i> Catalog Language
          </label>
          <select id="modalCatalogLang" class="form-select form-select-sm" style="background: #1e293b; color: #fff; border-color: #334155;">
            <option value="en" selected>English</option>
            <option value="te">తెలుగు (Telugu)</option>
            <option value="hi">हिन्दी (Hindi)</option>
            <option value="ta">தமிழ் (Tamil)</option>
          </select>
        </div>

        <!-- Delivery Method -->
        <div class="mb-3">
          <label class="form-label fw-bold text-light mb-1" style="font-size: 12px;">Delivery Method</label>
          <div class="d-flex gap-2">
            <div class="form-check form-check-inline">
              <input class="form-check-input" type="radio" name="modalDeliveryMethod" id="methodLink" value="web_link" checked>
              <label class="form-check-label text-light small" for="methodLink">Web Link</label>
            </div>
            <div class="form-check form-check-inline">
              <input class="form-check-input" type="radio" name="modalDeliveryMethod" id="methodPdf" value="pdf_document">
              <label class="form-check-label text-light small" for="methodPdf">PDF Brochure</label>
            </div>
            <div class="form-check form-check-inline">
              <input class="form-check-input" type="radio" name="modalDeliveryMethod" id="methodBoth" value="both">
              <label class="form-check-label text-light small" for="methodBoth">Both</label>
            </div>
          </div>
        </div>

        <!-- Custom Note -->
        <div class="mb-3">
          <label class="form-label fw-bold text-light mb-1" style="font-size: 12px;">Specialist Note (optional)</label>
          <textarea id="modalCustomNote" class="form-control form-control-sm" rows="2" 
                    placeholder="E.g., Based on our site visit discussion today..."
                    style="background: #1e293b; color: #fff; border-color: #334155; font-size: 12px;"></textarea>
        </div>

        <!-- Action Button -->
        <div class="d-grid gap-2 pt-2">
          <button id="modalSubmitDispatchBtn" class="btn btn-success fw-bold py-2 rounded-pill shadow" style="font-size: 14px;">
            <i class="fab fa-whatsapp me-1"></i> Send Catalog Now
          </button>
        </div>
      </div>
    `;

    document.body.appendChild(modalEl);

    // Event listeners for modal
    const closeBtn = modalEl.querySelector('#closeDispatchModalBtn');
    if (closeBtn) closeBtn.addEventListener('click', () => modalEl?.remove());

    modalEl.addEventListener('click', (e) => {
      if (e.target === modalEl) modalEl?.remove();
    });

    const searchInput = modalEl.querySelector('#modalRecipientSearchInput') as HTMLInputElement;
    const dropdown = modalEl.querySelector('#modalSearchDropdown') as HTMLElement;
    const clearSearchBtn = modalEl.querySelector('#modalClearSearchBtn');

    if (clearSearchBtn && searchInput) {
      clearSearchBtn.addEventListener('click', () => {
        searchInput.value = '';
        if (dropdown) dropdown.style.display = 'none';
      });
    }

    if (searchInput) {
      // Focus: trigger search with current or empty query
      searchInput.addEventListener('focus', () => {
        this.performMobileRecipientSearch(searchInput.value.trim(), dropdown);
      });

      searchInput.addEventListener('input', () => {
        clearTimeout(this.searchDebounceTimer);
        const query = searchInput.value.trim();
        this.searchDebounceTimer = setTimeout(() => {
          this.performMobileRecipientSearch(query, dropdown);
        }, 220);
      });
    }

    const removeBtn = modalEl.querySelector('#modalRemoveSelectedBtn');
    if (removeBtn) {
      removeBtn.addEventListener('click', () => {
        this.selectedLeadId = null;
        this.selectedPartnerId = null;
        const card = modalEl?.querySelector('#modalSelectedCard') as HTMLElement;
        if (card) card.style.display = 'none';
      });
    }

    const submitBtn = modalEl.querySelector('#modalSubmitDispatchBtn') as HTMLButtonElement;
    if (submitBtn) {
      submitBtn.addEventListener('click', async () => {
        const phoneInput = modalEl?.querySelector('#modalRecipientPhone') as HTMLInputElement;
        const nameInput = modalEl?.querySelector('#modalRecipientName') as HTMLInputElement;
        const langSelect = modalEl?.querySelector('#modalCatalogLang') as HTMLSelectElement;
        const noteText = modalEl?.querySelector('#modalCustomNote') as HTMLTextAreaElement;
        const methodEl = modalEl?.querySelector('input[name="modalDeliveryMethod"]:checked') as HTMLInputElement;

        const phone = (phoneInput?.value || '').trim().replace(/\D/g, '');
        if (phone.length < 10) {
          alert('Please enter a valid 10-digit mobile number.');
          phoneInput?.focus();
          return;
        }

        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Preparing dispatch...';

        try {
          const res = await apiService.post<any>(`/api/v1/digital-catalogs/${cat.id}/dispatch-whatsapp`, {
            lead_id: this.selectedLeadId,
            partner_id: this.selectedPartnerId,
            recipient_phone: phone,
            recipient_name: nameInput?.value?.trim() || undefined,
            language_code: langSelect?.value || 'en',
            delivery_method: methodEl?.value || 'web_link',
            custom_note: noteText?.value?.trim() || undefined
          });

          modalEl?.remove();

          if (res && res.success) {
            if (res.wa_me_url) {
              window.open(res.wa_me_url, '_blank');
            } else {
              alert('Catalog proposal queued successfully for WhatsApp delivery!');
            }
          } else {
            alert('Notice: ' + (res?.message || 'Dispatch completed'));
          }
        } catch (err: any) {
          submitBtn.disabled = false;
          submitBtn.innerHTML = '<i class="fab fa-whatsapp me-1"></i> Send Catalog Now';
          alert('Dispatch error: ' + (err.message || 'Unknown error'));
        }
      });
    }
  }

  private async performMobileRecipientSearch(query: string, dropdown: HTMLElement): Promise<void> {
    if (!dropdown) return;

    try {
      const q = encodeURIComponent(query);
      const res = await apiService.get<any>(`/api/v1/digital-catalogs/recipients/search?q=${q}&limit=12`);
      const results = res?.results || [];

      if (results.length === 0) {
        dropdown.innerHTML = '<div class="p-2 text-muted small text-center">No matching contacts found</div>';
        dropdown.style.display = 'block';
        return;
      }

      dropdown.innerHTML = results.map((item: any, idx: number) => {
        const badgeBg = item.badge_color || '#0284c7';
        return `
          <div class="mobile-recipient-item p-2 border-bottom border-secondary border-opacity-25" 
               data-idx="${idx}"
               style="cursor: pointer; display: flex; justify-content: space-between; align-items: center; background: transparent;">
            <div>
              <div class="fw-bold text-white small">${item.name || 'Unknown'}</div>
              <div class="text-muted" style="font-size: 11px;">${item.formatted_phone || item.phone} • ${item.subtitle || ''}</div>
            </div>
            <span class="badge rounded-pill" style="background: ${badgeBg}; color: #ffffff; font-size: 10px;">
              ${item.source}
            </span>
          </div>
        `;
      }).join('');
      dropdown.style.display = 'block';

      dropdown.querySelectorAll('.mobile-recipient-item').forEach((el) => {
        el.addEventListener('click', () => {
          const idx = parseInt(el.getAttribute('data-idx') || '0', 10);
          const item = results[idx];
          if (item) {
            this.selectMobileRecipient(item);
            dropdown.style.display = 'none';
          }
        });
      });
    } catch (err) {
      console.warn('Recipient search error:', err);
      dropdown.style.display = 'none';
    }
  }

  private selectMobileRecipient(item: any): void {
    const modalEl = document.getElementById('mobileCatalogDispatchModal');
    if (!modalEl) return;

    this.selectedLeadId = item.lead_id || null;
    this.selectedPartnerId = item.partner_id || null;

    const phoneInput = modalEl.querySelector('#modalRecipientPhone') as HTMLInputElement;
    const nameInput = modalEl.querySelector('#modalRecipientName') as HTMLInputElement;
    if (phoneInput) phoneInput.value = item.phone || '';
    if (nameInput) nameInput.value = item.name || '';

    const card = modalEl.querySelector('#modalSelectedCard') as HTMLElement;
    const cardName = modalEl.querySelector('#modalSelectedName');
    const cardPhone = modalEl.querySelector('#modalSelectedPhone');

    if (card && cardName && cardPhone) {
      cardName.textContent = `${item.name} (${item.source})`;
      cardPhone.textContent = `${item.formatted_phone || item.phone} ${item.subtitle ? '• ' + item.subtitle : ''}`;
      card.style.display = 'block';
    }
  }

  // ── Mobile Dispatch History & Click Telemetry Modal ───────────────
  private currentMobileHistoryScope: 'my' | 'team' = 'my';
  private mobileHistoryDebounceTimer: any = null;

  private openMobileDispatchHistoryModal(): void {
    let modalEl = document.getElementById('mobileCatalogHistoryModal');
    if (modalEl) modalEl.remove();

    this.currentMobileHistoryScope = 'my';

    modalEl = document.createElement('div');
    modalEl.id = 'mobileCatalogHistoryModal';
    modalEl.style.cssText = `
      position: fixed; inset: 0; z-index: 10050;
      background: rgba(0, 0, 0, 0.85);
      display: flex; align-items: flex-end; justify-content: center;
      padding: 0; animation: fadeIn 0.15s ease-out;
    `;

    modalEl.innerHTML = `
      <div class="history-sheet" style="
        background: #0f172a; width: 100%; max-width: 540px;
        height: 92vh; display: flex; flex-direction: column;
        border-top-left-radius: 20px; border-top-right-radius: 20px;
        border: 1px solid rgba(255,255,255,0.15); border-bottom: none;
        box-shadow: 0 -10px 25px rgba(0,0,0,0.5);
        color: #f8fafc; padding: 18px 16px 16px 16px;
      ">
        <!-- Header -->
        <div class="d-flex justify-content-between align-items-center mb-2 pb-2 border-bottom border-secondary border-opacity-25">
          <div class="d-flex align-items-center gap-2">
            <div style="width: 34px; height: 34px; border-radius: 50%; background: #0284c7; display: flex; align-items: center; justify-content: center; color: #fff; font-size: 16px;">
              <i class="fas fa-history"></i>
            </div>
            <div>
              <h6 class="fw-bold mb-0 text-white" style="font-size: 15px;">Dispatch History & Telemetry</h6>
              <div class="text-muted" style="font-size: 11px;">Tracked link dispatches & engagement</div>
            </div>
          </div>
          <button id="closeMobileHistModalBtn" class="btn btn-sm btn-dark text-muted rounded-circle" style="width: 32px; height: 32px; padding: 0; font-size: 18px;">
            &times;
          </button>
        </div>

        <!-- Scope Pills (My Dispatches vs Team Dispatches) -->
        <div class="d-flex gap-2 mb-2 p-1 bg-dark rounded-pill border border-secondary border-opacity-25">
          <button type="button" class="btn btn-sm btn-success rounded-pill flex-fill fw-bold py-1" id="btnMobileScopeMy" style="font-size: 12px;">
            <i class="fas fa-user me-1"></i> My Dispatches (<span id="mobileBadgeMy">0</span>)
          </button>
          <button type="button" class="btn btn-sm btn-outline-secondary text-light rounded-pill flex-fill fw-bold py-1" id="btnMobileScopeTeam" style="font-size: 12px;">
            <i class="fas fa-users me-1"></i> Team Dispatches (<span id="mobileBadgeTeam">0</span>)
          </button>
        </div>

        <!-- 4 KPI Summary Cards Grid -->
        <div class="row g-2 mb-2">
          <div class="col-6">
            <div class="p-2 rounded-3 text-center" style="background: #1e293b; border: 1px solid rgba(255,255,255,0.08);">
              <small class="text-muted d-block" style="font-size: 10px; font-weight: 700;">TOTAL DISPATCHES</small>
              <div class="fs-5 fw-bold text-white" id="mobileHistKpiDispatches">0</div>
            </div>
          </div>
          <div class="col-6">
            <div class="p-2 rounded-3 text-center" style="background: #1e293b; border: 1px solid rgba(255,255,255,0.08);">
              <small class="text-muted d-block" style="font-size: 10px; font-weight: 700;">TOTAL LINK CLICKS</small>
              <div class="fs-5 fw-bold text-success" id="mobileHistKpiClicks">0</div>
            </div>
          </div>
          <div class="col-6">
            <div class="p-2 rounded-3 text-center" style="background: #1e293b; border: 1px solid rgba(255,255,255,0.08);">
              <small class="text-muted d-block" style="font-size: 10px; font-weight: 700;">CLICK-THROUGH RATE</small>
              <div class="fs-5 fw-bold text-warning" id="mobileHistKpiRate">0%</div>
            </div>
          </div>
          <div class="col-6">
            <div class="p-2 rounded-3 text-center" style="background: #1e293b; border: 1px solid rgba(255,255,255,0.08);">
              <small class="text-muted d-block" style="font-size: 10px; font-weight: 700;">TOP MODEL</small>
              <div class="fs-5 fw-bold text-info text-truncate" id="mobileHistKpiModel">SOLAR</div>
            </div>
          </div>
        </div>

        <!-- Quick Filters Toolbar -->
        <div class="mb-2">
          <div class="d-flex align-items-center gap-2 mb-2">
            <div style="position: relative; flex: 1;">
              <input type="text" id="mobileHistSearchInput" placeholder="Search recipient, ref, staff..." style="width: 100%; background: #1e293b; color: #fff; border: 1px solid #334155; border-radius: 8px; font-size: 12px; padding: 7px 10px 7px 30px; outline: none;">
              <i class="fas fa-search text-muted" style="position: absolute; left: 10px; top: 9px; font-size: 11px;"></i>
            </div>
            <button type="button" class="btn btn-sm btn-outline-secondary" id="btnMobileHistReset" style="font-size: 11px; padding: 6px 10px; border-radius: 8px; color: #94a3b8; border-color: #334155;">
              <i class="fas fa-undo"></i>
            </button>
          </div>
          <div class="d-flex gap-1 overflow-auto no-scrollbar pb-1">
            <select id="mobileHistModelFilter" style="background: #1e293b; color: #fff; border: 1px solid #334155; border-radius: 8px; font-size: 11px; padding: 5px 8px; outline: none;">
              <option value="ALL">All Models</option>
              <option value="SOLAR">Solar</option>
              <option value="INDUSTRIAL_HUB">Hub 5-in-1</option>
              <option value="EV_B2C">EV 2W Pricing</option>
              <option value="HUB_PRICING">Hub Commercials</option>
              <option value="EV_B2B">EV Fleet</option>
              <option value="EV_SPARES">EV Spares</option>
              <option value="ETC_TRAINING">ETC Training</option>
              <option value="REAL_DREAMS">Real Dreams</option>
              <option value="INSURANCE">Insurance</option>
            </select>
            <select id="mobileHistEngagementFilter" style="background: #1e293b; color: #fff; border: 1px solid #334155; border-radius: 8px; font-size: 11px; padding: 5px 8px; outline: none;">
              <option value="all">All Activity</option>
              <option value="viewed">✓ Viewed (&gt;0 clicks)</option>
              <option value="high">🔥 High (2+ clicks)</option>
              <option value="unviewed">⚪ Unopened (0 clicks)</option>
            </select>
            <select id="mobileHistTimeframeFilter" style="background: #1e293b; color: #fff; border: 1px solid #334155; border-radius: 8px; font-size: 11px; padding: 5px 8px; outline: none;">
              <option value="all">All Time</option>
              <option value="today">Today</option>
              <option value="yesterday">Yesterday</option>
              <option value="7d">Last 7d</option>
              <option value="30d">Last 30d</option>
            </select>
          </div>
        </div>

        <!-- Scrollable List of Dispatches -->
        <div id="mobileHistListContainer" style="flex: 1; overflow-y: auto; padding-right: 2px;">
          <div class="text-center py-4">
            <div class="spinner-border spinner-border-sm text-info" role="status"></div>
            <p class="text-muted small mt-2">Loading dispatch history...</p>
          </div>
        </div>
      </div>
    `;

    document.body.appendChild(modalEl);

    // Event listeners
    const closeBtn = modalEl.querySelector('#closeMobileHistModalBtn');
    if (closeBtn) closeBtn.addEventListener('click', () => modalEl?.remove());
    modalEl.addEventListener('click', (e) => {
      if (e.target === modalEl) modalEl?.remove();
    });

    const btnScopeMy = modalEl.querySelector('#btnMobileScopeMy') as HTMLElement;
    const btnScopeTeam = modalEl.querySelector('#btnMobileScopeTeam') as HTMLElement;

    if (btnScopeMy && btnScopeTeam) {
      btnScopeMy.addEventListener('click', () => {
        this.currentMobileHistoryScope = 'my';
        btnScopeMy.className = 'btn btn-sm btn-success rounded-pill flex-fill fw-bold py-1';
        btnScopeTeam.className = 'btn btn-sm btn-outline-secondary text-light rounded-pill flex-fill fw-bold py-1';
        this.fetchAndRenderMobileHistory();
      });

      btnScopeTeam.addEventListener('click', () => {
        this.currentMobileHistoryScope = 'team';
        btnScopeTeam.className = 'btn btn-sm btn-success rounded-pill flex-fill fw-bold py-1';
        btnScopeMy.className = 'btn btn-sm btn-outline-secondary text-light rounded-pill flex-fill fw-bold py-1';
        this.fetchAndRenderMobileHistory();
      });
    }

    const resetBtn = modalEl.querySelector('#btnMobileHistReset');
    if (resetBtn) {
      resetBtn.addEventListener('click', () => {
        const s = modalEl?.querySelector('#mobileHistSearchInput') as HTMLInputElement;
        const m = modalEl?.querySelector('#mobileHistModelFilter') as HTMLSelectElement;
        const e = modalEl?.querySelector('#mobileHistEngagementFilter') as HTMLSelectElement;
        const tf = modalEl?.querySelector('#mobileHistTimeframeFilter') as HTMLSelectElement;
        if (s) s.value = '';
        if (m) m.value = 'ALL';
        if (e) e.value = 'all';
        if (tf) tf.value = 'all';
        this.fetchAndRenderMobileHistory();
      });
    }

    // Preload opposite scope count for team badge
    apiService.get<any>('/api/v1/digital-catalogs/dispatches/history?scope=team&limit=1').then(teamRes => {
      const p = teamRes?.data || teamRes || {};
      const t = p?.total ?? teamRes?.total ?? 0;
      const b = modalEl?.querySelector('#mobileBadgeTeam');
      if (b && t) b.textContent = String(t);
    }).catch(() => {});

    const searchInput = modalEl.querySelector('#mobileHistSearchInput') as HTMLInputElement;
    if (searchInput) {
      searchInput.addEventListener('input', () => {
        clearTimeout(this.mobileHistoryDebounceTimer);
        this.mobileHistoryDebounceTimer = setTimeout(() => {
          this.fetchAndRenderMobileHistory();
        }, 300);
      });
    }

    ['mobileHistModelFilter', 'mobileHistEngagementFilter', 'mobileHistTimeframeFilter'].forEach(id => {
      const el = modalEl?.querySelector(`#${id}`);
      if (el) {
        el.addEventListener('change', () => this.fetchAndRenderMobileHistory());
      }
    });

    this.fetchAndRenderMobileHistory();
  }

  private async fetchAndRenderMobileHistory(): Promise<void> {
    const modalEl = document.getElementById('mobileCatalogHistoryModal');
    if (!modalEl) return;

    const listContainer = modalEl.querySelector('#mobileHistListContainer');
    if (listContainer) {
      listContainer.innerHTML = `
        <div class="text-center py-4">
          <div class="spinner-border spinner-border-sm text-info" role="status"></div>
          <p class="text-muted small mt-2">Loading dispatch telemetry...</p>
        </div>
      `;
    }

    try {
      const q = ((modalEl.querySelector('#mobileHistSearchInput') as HTMLInputElement)?.value || '').trim();
      const segment_code = (modalEl.querySelector('#mobileHistModelFilter') as HTMLSelectElement)?.value || 'ALL';
      const engagement = (modalEl.querySelector('#mobileHistEngagementFilter') as HTMLSelectElement)?.value || 'all';
      const timeframe = (modalEl.querySelector('#mobileHistTimeframeFilter') as HTMLSelectElement)?.value || 'all';

      const params = new URLSearchParams();
      params.set('scope', this.currentMobileHistoryScope);
      if (q) params.set('q', q);
      if (segment_code && segment_code !== 'ALL') params.set('segment_code', segment_code);
      if (engagement && engagement !== 'all') params.set('engagement', engagement);
      if (timeframe && timeframe !== 'all') params.set('timeframe', timeframe);
      params.set('limit', '100');

      const res = await apiService.get<any>('/api/v1/digital-catalogs/dispatches/history?' + params.toString());
      const payload = res?.data || res || {};
      const dispatches = payload?.dispatches || res?.dispatches || [];
      const stats = payload?.stats || res?.stats || {};
      const total = payload?.total ?? res?.total ?? 0;

      // Update KPIs
      const kpiDisp = modalEl.querySelector('#mobileHistKpiDispatches');
      const kpiClicks = modalEl.querySelector('#mobileHistKpiClicks');
      const kpiRate = modalEl.querySelector('#mobileHistKpiRate');
      const kpiModel = modalEl.querySelector('#mobileHistKpiModel');

      if (kpiDisp) kpiDisp.textContent = stats.total_dispatches || 0;
      if (kpiClicks) kpiClicks.textContent = stats.total_views || 0;
      if (kpiRate) kpiRate.textContent = `${stats.view_rate_percent || 0}%`;
      if (kpiModel) kpiModel.textContent = (stats.top_model || 'SOLAR').replace(/_/g, ' ');

      const badgeMy = modalEl.querySelector('#mobileBadgeMy');
      const badgeTeam = modalEl.querySelector('#mobileBadgeTeam');
      if (this.currentMobileHistoryScope === 'my' && badgeMy) {
        badgeMy.textContent = String(total);
      } else if (this.currentMobileHistoryScope === 'team' && badgeTeam) {
        badgeTeam.textContent = String(total);
      }

      if (!listContainer) return;
      if (dispatches.length === 0) {
        listContainer.innerHTML = `
          <div class="text-center py-5 text-muted">
            <i class="fas fa-inbox fa-2x mb-2 d-block opacity-50"></i>
            <div>No dispatches found for current filters.</div>
          </div>
        `;
        return;
      }

      const isTeam = (this.currentMobileHistoryScope === 'team');

      listContainer.innerHTML = dispatches.map((d: any) => {
        const clicks = d.view_count || 0;
        let clickBadge = `<span class="badge bg-secondary bg-opacity-25 text-muted border border-secondary border-opacity-25 px-2 py-1" style="font-size: 11px;">0 clicks</span>`;
        if (clicks >= 2) {
          clickBadge = `<span class="badge bg-danger bg-opacity-25 text-danger border border-danger border-opacity-50 px-2 py-1" style="font-size: 11px;"><i class="fas fa-fire me-1"></i>${clicks} clicks</span>`;
        } else if (clicks === 1) {
          clickBadge = `<span class="badge bg-success bg-opacity-25 text-success border border-success border-opacity-50 px-2 py-1" style="font-size: 11px;"><i class="fas fa-check me-1"></i>1 click</span>`;
        }

        const staffHeader = isTeam ? `
          <div class="d-flex align-items-center gap-2 mb-2 pb-1 border-bottom border-secondary border-opacity-25">
            <div style="width: 22px; height: 22px; border-radius: 50%; background: #1e293b; border: 1px solid #3b82f6; display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: bold; color: #60a5fa;">
              ${(d.staff_name || 'U').charAt(0)}
            </div>
            <div class="small text-muted" style="font-size: 11px;">
              Dispatched by <strong class="text-white">${d.staff_name || 'Staff'}</strong> (${d.staff_code || ''})
            </div>
          </div>
        ` : '';

        const origin = (!window.location.origin || window.location.origin.includes('localhost') || window.location.origin.includes('capacitor')) ? APP_CONFIG.BASE_SERVER_URL : window.location.origin;
        const fullTracked = origin + (d.tracked_url || '');
        const waUrl = `https://wa.me/91${d.recipient_phone}?text=${encodeURIComponent('Hello ' + (d.recipient_name || '') + ', here is the catalog proposal: ' + fullTracked)}`;

        const dateStr = d.sent_at ? new Date(d.sent_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) : 'N/A';

        return `
          <div class="card bg-dark border-secondary border-opacity-25 rounded-3 p-3 mb-2 shadow-sm">
            ${staffHeader}
            <div class="d-flex justify-content-between align-items-start mb-1">
              <div>
                <div class="fw-bold text-white small">${d.recipient_name || 'Customer'}</div>
                <div class="text-muted" style="font-size: 11px;"><i class="fas fa-phone-alt me-1 text-secondary"></i>+91 ${d.recipient_phone}</div>
              </div>
              <span class="badge bg-dark text-info border border-info border-opacity-25 font-monospace" style="font-size: 10px;">
                #${d.share_ref_code || ''}
              </span>
            </div>

            <div class="d-flex justify-content-between align-items-center my-2">
              <div>
                <span class="badge bg-success bg-opacity-25 text-success rounded-pill px-2 py-0" style="font-size: 10px;">
                  ${d.segment_code}
                </span>
                <span class="text-light small ms-1">${d.catalog_title}</span>
              </div>
              <div>${clickBadge}</div>
            </div>

            <div class="d-flex justify-content-between align-items-center text-muted small mt-1 pt-2 border-top border-secondary border-opacity-25" style="font-size: 11px;">
              <span><i class="far fa-clock me-1 text-secondary"></i>${dateStr}</span>
              <div class="d-flex gap-2">
                <a href="${d.tracked_url}" target="_blank" class="btn btn-sm btn-outline-secondary py-0 px-2" style="font-size: 11px;" title="Open Link">
                  <i class="fas fa-external-link-alt"></i>
                </a>
                <a href="${waUrl}" target="_blank" class="btn btn-sm btn-outline-success py-0 px-2" style="font-size: 11px;" title="WhatsApp">
                  <i class="fab fa-whatsapp"></i>
                </a>
                <button type="button" class="btn btn-sm btn-outline-warning py-0 px-2 mobile-copy-btn" data-url="${fullTracked}" style="font-size: 11px;" title="Copy Link">
                  <i class="fas fa-copy"></i>
                </button>
              </div>
            </div>
          </div>
        `;
      }).join('');

      listContainer.querySelectorAll('.mobile-copy-btn').forEach(btn => {
        btn.addEventListener('click', async (e) => {
          const target = (e.currentTarget as HTMLElement);
          const link = target.getAttribute('data-url') || '';
          try {
            await navigator.clipboard.writeText(link);
            const orig = target.innerHTML;
            target.innerHTML = '<i class="fas fa-check text-success"></i>';
            setTimeout(() => { target.innerHTML = orig; }, 2000);
          } catch {
            alert('Catalog link: ' + link);
          }
        });
      });

    } catch (err: any) {
      console.error('Mobile history error:', err);
      if (listContainer) {
        listContainer.innerHTML = `
          <div class="alert alert-dark text-center text-danger small">
            Failed to load dispatch history: ${err.message || 'Error'}
          </div>
        `;
      }
    }
  }
}

