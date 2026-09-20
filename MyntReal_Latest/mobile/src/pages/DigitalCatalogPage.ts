/**
 * Digital Catalog Page — Mobile Web, Android & iOS Parity
 * DC Protocol: DC_MOBILE_DIGITAL_CATALOG_001
 * Full parity with desktop CRM:
 * - 8 Business Vertical Horizontal Chips (Solar, Industrial Hub, EV 2W, Hub Commercials, EV Spares, ETC Training, Real Dreams, Insurance)
 * - Redesigned Hero Card with 4-KPI Counters & Direct Routing Shortcuts
 * - 4 Interactive Tabs: Packages & Plans, Modular Sections, Gallery & Videos, About & PDF
 * - Luxury Commercial Product Cards with Net Cost, Subsidy Breakdown & "Send Plan" CTA
 * - Multilingual WhatsApp dispatch bottom sheet
 * - Real-time Dispatch History & Telemetry bottom sheet
 */

import { apiService } from "../services/api.service";
import { PageHeader } from "../components/PageHeader";
import { APP_CONFIG } from "../config/app.config";

interface CatalogItem {
  id: number;
  item_type: string;
  item_code?: string;
  title: string;
  subtitle?: string;
  description?: string;
  pricing?: {
    currency?: string;
    base_price?: number;
    price_text?: string;
    subsidy_amount?: number;
    net_cost?: number;
    tax_benefit?: string;
  };
  specifications?: Array<{ label: string; value: string }>;
  badges?: string[];
  media_urls?: string[];
  video_url?: string;
  is_featured?: boolean;
}

interface CatalogSection {
  id: number;
  section_type: string;
  section_key: string;
  title?: string;
  subtitle?: string;
  localized_content?: {
    title?: string;
    subtitle?: string;
    description?: string;
  };
  media_gallery?: any[];
  configuration?: any;
  sort_order?: number;
}

interface Catalog {
  id: number;
  segment_code: string;
  slug: string;
  title: string;
  subtitle?: string;
  summary?: string;
  hero_media_url?: string;
  pdf_brochure_url?: string;
  sections_count?: number;
  items_count?: number;
  sections?: CatalogSection[];
  items?: CatalogItem[];
}

export class DigitalCatalogPage {
  private container: HTMLElement;
  private catalogs: Catalog[] = [];
  private activeSegment: string = "SOLAR";
  private activeCatalog: Catalog | null = null;
  private activeTab: "packages" | "sections" | "media" | "overview" = "packages";
  private isLoading = true;

  private readonly verticals = [
    { code: "SOLAR", label: "Solar", icon: "☀️" },
    { code: "INDUSTRIAL_HUB", label: "MyntReal Hub", icon: "🏢" },
    { code: "EV_B2C", label: "EV 2W Pricing", icon: "⚡" },
    { code: "HUB_PRICING", label: "Hub Commercials (24h)", icon: "💼" },
    { code: "EV_SPARES", label: "EV Spares", icon: "🔧" },
    { code: "ETC_TRAINING", label: "ETC Training", icon: "🎓" },
    { code: "REAL_DREAMS", label: "Real Dreams", icon: "🌟" },
    { code: "INSURANCE", label: "Insurance", icon: "🛡️" }
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
        ${PageHeader.render({ title: "Digital Catalog", showBack: true })}
        
        <div class="dc-inner">
          <!-- Top Action Bar -->
          <div class="dc-top-bar">
            <div class="dc-status-pill">
              <span class="dc-status-dot"></span>
              <span>Official & Verified</span>
            </div>
            <button class="dc-history-btn" id="btnOpenMobileDispatchHistory">
              <i class="fas fa-chart-line"></i>
              <span>Dispatch History</span>
              <span class="badge bg-info bg-opacity-25 text-info rounded-pill ms-1" id="topHistBadge" style="font-size: 10px; display: none;">0</span>
            </button>
          </div>

          <!-- Horizontal Scrolling Segment Chip Bar -->
          <div class="dc-chip-bar" id="mobileSegmentTabs">
            ${this.verticals.map(v => `
              <div class="dc-chip ${v.code === this.activeSegment ? "active" : ""}" data-code="${v.code}" id="dcChip_${v.code}">
                <span>${v.icon}</span>
                <span>${v.label}</span>
              </div>
            `).join("")}
          </div>

          <!-- Catalog Main Content Area -->
          <div id="catalogContentArea">
            <div class="text-center py-5">
              <div class="spinner-border text-success" role="status"></div>
              <p class="text-muted small mt-2">Loading interactive catalogs...</p>
            </div>
          </div>
        </div>
      </div>
    `;

    PageHeader.attachListeners({
      title: "Digital Catalog",
      showBack: true
    });

    this.bindEvents();
    await this.loadCatalogs();
    this.fetchQuickDispatchCount();
  }

  private bindEvents(): void {
    const historyBtn = this.container.querySelector("#btnOpenMobileDispatchHistory");
    if (historyBtn) {
      historyBtn.addEventListener("click", () => {
        this.openMobileDispatchHistoryModal();
      });
    }

    this.container.addEventListener("click", (e) => {
      const target = e.target as HTMLElement;
      const chip = target.closest(".dc-chip") as HTMLElement;
      if (chip) {
        const code = chip.dataset.code;
        if (code && code !== this.activeSegment) {
          this.activeSegment = code;
          this.updateSegmentUI();
          this.renderActiveCatalog();
        }
      }
    });
  }

  private updateSegmentUI(): void {
    const chips = this.container.querySelectorAll(".dc-chip");
    chips.forEach(c => {
      const chip = c as HTMLElement;
      if (chip.dataset.code === this.activeSegment) {
        chip.classList.add("active");
        chip.scrollIntoView({ behavior: "smooth", inline: "center", block: "nearest" });
      } else {
        chip.classList.remove("active");
      }
    });
  }

  private async fetchQuickDispatchCount(): Promise<void> {
    try {
      const res = await apiService.get<any>("/api/v1/digital-catalogs/dispatches/history?scope=my&limit=1");
      const payload = res?.data || res || {};
      const total = payload?.total ?? res?.total ?? 0;
      const badge = this.container.querySelector("#topHistBadge") as HTMLElement;
      if (badge && total > 0) {
        badge.textContent = String(total);
        badge.style.display = "inline-block";
      }
    } catch {}
  }

  private async loadCatalogs(): Promise<void> {
    try {
      this.isLoading = true;
      const res = await apiService.get<any>("/api/v1/digital-catalogs/library");
      const data = res?.data || res || {};
      const catalogs = data.catalogs || res?.catalogs || (Array.isArray(data) ? data : []);
      if (catalogs && catalogs.length > 0) {
        this.catalogs = catalogs;
        await this.renderActiveCatalog();
      } else {
        const area = this.container.querySelector("#catalogContentArea");
        if (area) {
          area.innerHTML = `
            <div class="alert alert-dark text-center py-4 rounded-4 border-secondary border-opacity-25 shadow-sm">
              <i class="fas fa-book-open text-muted mb-2" style="font-size: 32px;"></i>
              <p class="mb-2 text-white fw-bold">No catalogs found</p>
              <button class="btn btn-sm btn-outline-success rounded-pill px-3" id="btnRetryCatalogs">
                <i class="fas fa-sync-alt me-1"></i> Retry
              </button>
            </div>
          `;
          area.querySelector("#btnRetryCatalogs")?.addEventListener("click", () => this.loadCatalogs());
        }
      }
    } catch (err) {
      console.error("Mobile catalog load error:", err);
      const area = this.container.querySelector("#catalogContentArea");
      if (area) {
        area.innerHTML = `
          <div class="alert alert-dark text-center py-4 rounded-4 border-secondary border-opacity-25 shadow-sm">
            <i class="fas fa-exclamation-circle text-danger mb-2" style="font-size: 32px;"></i>
            <p class="mb-2 text-white fw-bold">Unable to load catalog</p>
            <p class="text-muted small mb-3">Please check your connection and try again.</p>
            <button class="btn btn-sm btn-outline-success rounded-pill px-3" id="btnRetryCatalogs">
              <i class="fas fa-sync-alt me-1"></i> Retry
            </button>
          </div>
        `;
        area.querySelector("#btnRetryCatalogs")?.addEventListener("click", () => this.loadCatalogs());
      }
    } finally {
      this.isLoading = false;
    }
  }

  private async renderActiveCatalog(): Promise<void> {
    const area = this.container.querySelector("#catalogContentArea");
    if (!area) return;

    const catSummary = this.catalogs.find(c => c.segment_code === this.activeSegment) || this.catalogs[0];
    if (!catSummary) {
      area.innerHTML = `<div class="p-4 text-center text-muted">No catalog found for ${this.activeSegment}</div>`;
      return;
    }

    // Show inline loading skeleton while fetching full details
    area.innerHTML = `
      <div class="text-center py-5">
        <div class="spinner-border spinner-border-sm text-success" role="status"></div>
        <p class="text-muted small mt-2">Loading ${catSummary.title || "details"}...</p>
      </div>
    `;

    // Fetch full details
    try {
      const fullRes = await apiService.get<any>(`/api/v1/digital-catalogs/${catSummary.id}`);
      const fullData = fullRes?.data || fullRes || {};
      this.activeCatalog = fullData.catalog || (fullRes as any)?.catalog || catSummary;
    } catch {
      this.activeCatalog = catSummary;
    }

    const cat = this.activeCatalog!;
    let publicUrl = `/catalog/${cat.segment_code.toLowerCase().replace(/_/g, "-")}/${cat.slug}`;
    if (cat.segment_code === "HUB_PRICING" || cat.slug === "hub-ev-pricing") {
      publicUrl = "/catalog/hub-ev-pricing";
    } else if (cat.segment_code === "EV_B2C" || cat.slug === "ev-b2c-pricing") {
      publicUrl = "/catalog/ev-b2c-pricing";
    }

    // Extra route shortcuts
    let shortcutBtnHtml = "";
    if (cat.segment_code === "SOLAR") {
      shortcutBtnHtml = `<a href="/hub/hgs" target="_blank" class="dc-btn-glass highlight-link"><i class="fas fa-sun text-warning"></i> /hub/hgs</a>`;
    } else if (cat.segment_code === "ETC_TRAINING") {
      shortcutBtnHtml = `<a href="/hub/etc" target="_blank" class="dc-btn-glass highlight-link"><i class="fas fa-graduation-cap text-info"></i> /hub/etc</a>`;
    } else if (cat.segment_code === "HUB_PRICING") {
      shortcutBtnHtml = `<a href="/catalog/hub-ev-pricing" target="_blank" class="dc-btn-glass highlight-link"><i class="fas fa-tags text-warning"></i> 24h Commercials</a>`;
    } else if (cat.segment_code === "EV_B2C") {
      shortcutBtnHtml = `<a href="/catalog/ev-b2c-pricing" target="_blank" class="dc-btn-glass highlight-link"><i class="fas fa-motorcycle text-success"></i> Customer EV 2W</a>`;
    }

    const sectionsCount = cat.sections_count || (cat.sections ? cat.sections.length : 0);
    const itemsCount = cat.items_count || (cat.items ? cat.items.length : 0);

    area.innerHTML = `
      <!-- Redesigned Hero Catalog Card -->
      <div class="dc-hero-card">
        <div class="dc-hero-tag-row">
          <span class="dc-tag dc-tag-primary">${cat.segment_code.replace(/_/g, " ")}</span>
          <span class="dc-tag dc-tag-info">Interactive Web Catalog</span>
          <span class="dc-tag dc-tag-gold">EN • TE • HI • TA</span>
        </div>

        <h2 class="dc-hero-title">${cat.title}</h2>
        <p class="dc-hero-subtitle">${cat.subtitle || cat.summary || "Official MyntOS Digital Solution & Commercial Proposal"}</p>

        <!-- 4-Column KPI Grid -->
        <div class="dc-kpi-grid">
          <div class="dc-kpi-box">
            <div class="dc-kpi-val text-white">${sectionsCount}</div>
            <div class="dc-kpi-label">Sections</div>
          </div>
          <div class="dc-kpi-box">
            <div class="dc-kpi-val text-success">${itemsCount}</div>
            <div class="dc-kpi-label">Packages</div>
          </div>
          <div class="dc-kpi-box">
            <div class="dc-kpi-val text-info" id="heroDispatchesCount">—</div>
            <div class="dc-kpi-label">Dispatches</div>
          </div>
          <div class="dc-kpi-box">
            <div class="dc-kpi-val text-warning" id="heroViewsCount">—</div>
            <div class="dc-kpi-label">Views</div>
          </div>
        </div>

        <!-- Primary CTA: WhatsApp Dispatch -->
        <button class="dc-btn-wa" id="btnMobileDispatchWhatsApp">
          <i class="fab fa-whatsapp" style="font-size: 18px;"></i>
          <span>Send Catalog on WhatsApp</span>
        </button>

        <!-- Secondary Action Row -->
        <div class="dc-hero-actions-row">
          <a href="${publicUrl}" target="_blank" class="dc-btn-glass" title="Open Public Web View">
            <i class="fas fa-external-link-alt"></i>
            <span>Open Web View</span>
          </a>
          ${cat.pdf_brochure_url ? `
            <a href="${cat.pdf_brochure_url}" target="_blank" class="dc-btn-glass" title="Download PDF Brochure">
              <i class="fas fa-file-pdf text-danger"></i>
              <span>PDF Brochure</span>
            </a>
          ` : ""}
          ${shortcutBtnHtml}
        </div>
      </div>

      <!-- Segmented Sub-Navigation Tabs: All 4 Options -->
      <div class="dc-tabs-nav" id="dcSubTabsNav">
        <button class="dc-tab-btn ${this.activeTab === "packages" ? "active" : ""}" data-tab="packages">
          <i class="fas fa-boxes-stacked"></i>
          <span>Packages (${itemsCount})</span>
        </button>
        <button class="dc-tab-btn ${this.activeTab === "sections" ? "active" : ""}" data-tab="sections">
          <i class="fas fa-layer-group"></i>
          <span>Sections (${sectionsCount})</span>
        </button>
        <button class="dc-tab-btn ${this.activeTab === "media" ? "active" : ""}" data-tab="media">
          <i class="fas fa-photo-film"></i>
          <span>Gallery & Video</span>
        </button>
        <button class="dc-tab-btn ${this.activeTab === "overview" ? "active" : ""}" data-tab="overview">
          <i class="fas fa-circle-info"></i>
          <span>About & PDF</span>
        </button>
      </div>

      <!-- Tab Content Area -->
      <div id="dcTabContentPane"></div>
    `;

    // Bind Hero Actions
    const dispatchBtn = area.querySelector("#btnMobileDispatchWhatsApp");
    if (dispatchBtn) {
      dispatchBtn.addEventListener("click", () => this.openMobileDispatchModal(cat));
    }

    // Bind Sub-Tabs
    const subTabBtns = area.querySelectorAll("#dcSubTabsNav .dc-tab-btn");
    subTabBtns.forEach(btn => {
      btn.addEventListener("click", (e) => {
        const target = (e.currentTarget as HTMLElement).dataset.tab as any;
        if (target && target !== this.activeTab) {
          this.activeTab = target;
          subTabBtns.forEach(b => b.classList.remove("active"));
          (e.currentTarget as HTMLElement).classList.add("active");
          this.renderTabPane(cat);
        }
      });
    });

    // Render active tab pane
    this.renderTabPane(cat);

    // Fetch live telemetry for this specific catalog segment in background
    this.fetchSegmentTelemetry(cat.segment_code);
  }

  private async fetchSegmentTelemetry(segmentCode: string): Promise<void> {
    try {
      const res = await apiService.get<any>(`/api/v1/digital-catalogs/dispatches/history?scope=my&segment_code=${segmentCode}&limit=1`);
      const payload = res?.data || res || {};
      const stats = payload?.stats || res?.stats || {};
      const dispEl = this.container.querySelector("#heroDispatchesCount");
      const viewsEl = this.container.querySelector("#heroViewsCount");
      if (dispEl) dispEl.textContent = String(stats.total_dispatches ?? payload?.total ?? 0);
      if (viewsEl) viewsEl.textContent = String(stats.total_views ?? 0);
    } catch {}
  }

  private renderTabPane(cat: Catalog): void {
    const pane = this.container.querySelector("#dcTabContentPane") as HTMLElement | null;
    if (!pane) return;

    switch (this.activeTab) {
      case "packages":
        this.renderPackagesTab(cat, pane);
        break;
      case "sections":
        this.renderSectionsTab(cat, pane);
        break;
      case "media":
        this.renderMediaTab(cat, pane);
        break;
      case "overview":
        this.renderOverviewTab(cat, pane);
        break;
    }
  }

  // ── Tab 1: Packages & Offerings ─────────────────────────────────────
  private renderPackagesTab(cat: Catalog, pane: HTMLElement): void {
    const items = cat.items || [];
    if (items.length === 0) {
      pane.innerHTML = `
        <div class="p-4 text-center text-muted rounded-4" style="background: #182234; border: 1px dashed rgba(255,255,255,0.1);">
          <i class="fas fa-boxes-stacked fa-2x mb-2 d-block opacity-40"></i>
          <div class="fw-bold text-light">No separate package items listed</div>
          <small class="text-muted">This catalog is presented as an integrated single-page solution. Explore the Modular Sections tab to review all components.</small>
        </div>
      `;
      return;
    }

    pane.innerHTML = `
      <div class="d-flex flex-column gap-1">
        ${items.map((it, idx) => {
          const pricing = it.pricing || {};
          const netCost = pricing.net_cost;
          const basePrice = pricing.base_price;
          const subsidy = pricing.subsidy_amount;
          const priceText = pricing.price_text;

          let formattedNet = "Enquire for Price";
          if (netCost) {
            formattedNet = `₹${Number(netCost).toLocaleString("en-IN")}`;
          } else if (basePrice) {
            formattedNet = `₹${Number(basePrice).toLocaleString("en-IN")}`;
          } else if (priceText) {
            formattedNet = priceText;
          }

          const subsidyBadge = (subsidy && subsidy > 0)
            ? `<span class="dc-subsidy-chip"><i class="fas fa-shield-halved me-1"></i>₹${Number(subsidy).toLocaleString("en-IN")} Govt Subsidy</span>`
            : (pricing.tax_benefit ? `<span class="dc-subsidy-chip text-info border-info border-opacity-50">${pricing.tax_benefit}</span>` : "");

          const baseStrikethrough = (basePrice && netCost && basePrice > netCost)
            ? `<span class="dc-base-mrp">MRP ₹${Number(basePrice).toLocaleString("en-IN")}</span>`
            : "";

          const specsList = it.specifications || [];
          const badgesList = it.badges || [];
          const isFeatured = it.is_featured || idx === 0;

          return `
            <div class="dc-product-card ${isFeatured ? "featured-plan" : ""}">
              ${isFeatured ? `<div class="dc-plan-badge"><i class="fas fa-crown me-1"></i>Recommended</div>` : ""}

              <h4 class="dc-product-title">${it.title}</h4>
              <p class="dc-product-subtitle">${it.subtitle || it.description || "Turnkey implementation with complete warranty & support"}</p>

              <!-- Pricing Box -->
              <div class="dc-pricing-box">
                <div>
                  <span class="dc-net-cost">${formattedNet}</span>
                  ${baseStrikethrough}
                </div>
                <div>${subsidyBadge}</div>
              </div>

              <!-- Specs Chips -->
              ${specsList.length > 0 ? `
                <div class="dc-specs-row">
                  ${specsList.slice(0, 4).map(sp => `
                    <span class="dc-spec-chip"><strong>${sp.label}:</strong> ${sp.value}</span>
                  `).join("")}
                </div>
              ` : ""}

              <!-- Badges Row -->
              ${badgesList.length > 0 ? `
                <div class="d-flex flex-wrap gap-1 mb-3">
                  ${badgesList.map(b => `
                    <span class="badge bg-secondary bg-opacity-25 text-light border border-secondary border-opacity-25" style="font-size: 10px;">
                      ${b}
                    </span>
                  `).join("")}
                </div>
              ` : ""}

              <!-- Action Row -->
              <div class="dc-plan-actions">
                <button class="dc-btn-send-plan" data-item-idx="${idx}">
                  <i class="fab fa-whatsapp"></i>
                  <span>Send This Plan on WhatsApp</span>
                </button>
              </div>
            </div>
          `;
        }).join("")}
      </div>
    `;

    // Bind Plan Send Buttons
    pane.querySelectorAll(".dc-btn-send-plan").forEach(btn => {
      btn.addEventListener("click", (e) => {
        const idx = parseInt((e.currentTarget as HTMLElement).dataset.itemIdx || "0", 10);
        const item = items[idx];
        const pricing = item.pricing || {};
        const priceStr = pricing.net_cost ? `₹${Number(pricing.net_cost).toLocaleString("en-IN")}` : (pricing.price_text || "");
        const prefillNote = `Special Recommendation: ${item.title} (${priceStr}). Turnkey package with end-to-end execution.`;
        this.openMobileDispatchModal(cat, prefillNote);
      });
    });
  }

  // ── Tab 2: Modular Sections ─────────────────────────────────────────
  private renderSectionsTab(cat: Catalog, pane: HTMLElement): void {
    const sections = cat.sections || [];
    if (sections.length === 0) {
      pane.innerHTML = `
        <div class="p-4 text-center text-muted rounded-4" style="background: #182234; border: 1px dashed rgba(255,255,255,0.1);">
          <i class="fas fa-layer-group fa-2x mb-2 d-block opacity-40"></i>
          <div class="fw-bold text-light">No modular sections defined</div>
        </div>
      `;
      return;
    }

    const typeLabels: Record<string, { label: string; icon: string }> = {
      hero: { label: "Hero Banner", icon: "fa-flag" },
      roi_calculator: { label: "ROI & Subsidy Calculator", icon: "fa-calculator" },
      comparison_table: { label: "Pricing & Capacity Matrix", icon: "fa-table-columns" },
      packages_pricing: { label: "Commercial Packages", icon: "fa-cubes" },
      specifications_table: { label: "Technical Specifications", icon: "fa-list-check" },
      process_workflow: { label: "4-Step Journey", icon: "fa-diagram-project" },
      highlights_grid: { label: "Value Propositions", icon: "fa-star" },
      media_gallery: { label: "Installation Gallery", icon: "fa-photo-film" },
      faqs: { label: "FAQ & Warranty Policy", icon: "fa-circle-question" },
      contact_cta: { label: "Consultation & Booking CTA", icon: "fa-phone-volume" }
    };

    pane.innerHTML = `
      <div class="d-flex flex-column gap-1">
        <div class="d-flex justify-content-between align-items-center mb-2 px-1">
          <small class="text-muted fw-bold text-uppercase" style="font-size: 11px; letter-spacing: 0.5px;">
            <i class="fas fa-list-ol text-success me-1"></i> ${sections.length} Ordered Sections
          </small>
          <span class="badge bg-success bg-opacity-15 text-success border border-success border-opacity-25" style="font-size: 10px;">
            Single-Page Flow
          </span>
        </div>

        ${sections.map((sec, idx) => {
          const typeMeta = typeLabels[sec.section_type] || { label: sec.section_type.replace(/_/g, " "), icon: "fa-layer-group" };
          const title = sec.localized_content?.title || sec.title || `Section ${idx + 1}`;
          const subtitle = sec.localized_content?.subtitle || sec.subtitle || "";

          return `
            <div class="dc-section-card">
              <div class="dc-section-header">
                <div>
                  <div class="d-flex align-items-center gap-2 mb-1">
                    <span class="badge bg-dark text-muted border border-secondary border-opacity-25" style="font-size: 10px; font-weight: 700;">#${idx + 1}</span>
                    <span class="dc-section-type-pill">
                      <i class="fas ${typeMeta.icon} me-1"></i>${typeMeta.label}
                    </span>
                  </div>
                  <h5 class="dc-section-title">${title}</h5>
                  ${subtitle ? `<p class="dc-section-desc">${subtitle}</p>` : ""}
                </div>
              </div>
            </div>
          `;
        }).join("")}
      </div>
    `;
  }

  // ── Tab 3: Gallery & Videos ─────────────────────────────────────────
  private renderMediaTab(cat: Catalog, pane: HTMLElement): void {
    // Collect photos from sections or catalog items
    const photos: Array<{ url: string; caption: string }> = [];
    (cat.sections || []).forEach(s => {
      if (s.media_gallery && Array.isArray(s.media_gallery)) {
        s.media_gallery.forEach(m => {
          if (typeof m === "string") photos.push({ url: m, caption: s.title || "Project Showcase" });
          else if (m && m.url) photos.push({ url: m.url, caption: m.caption || s.title || "Project Showcase" });
        });
      }
    });
    (cat.items || []).forEach(it => {
      if (it.media_urls && Array.isArray(it.media_urls)) {
        it.media_urls.forEach(u => photos.push({ url: u, caption: it.title }));
      }
    });

    // Default sample showcases if catalog has no direct attachments
    if (photos.length === 0) {
      photos.push(
        { url: "https://images.unsplash.com/photo-1509391365360-2e959784a276?auto=format&fit=crop&w=600&q=80", caption: "Rooftop Solar Installation" },
        { url: "https://images.unsplash.com/photo-1508873696983-2df5703bc69d?auto=format&fit=crop&w=600&q=80", caption: "CleanTech Micro-Inverters & Commissioning" },
        { url: "https://images.unsplash.com/photo-1558441719-8b489c63f7d1?auto=format&fit=crop&w=600&q=80", caption: "Commercial Net-Metering Array" },
        { url: "https://images.unsplash.com/photo-1593941707882-a5bba14938c7?auto=format&fit=crop&w=600&q=80", caption: "EV Fast Charging Infrastructure" }
      );
    }

    // Video Showcase list
    const videos = [
      {
        title: "Customer Site Walkthrough & Net-Metering Commissioning",
        duration: "3:45 min",
        url: "https://www.youtube.com/results?search_query=myntreal+har+ghar+solar",
        badge: "Walkthrough"
      },
      {
        title: "PM Surya Ghar Muft Bijli Subsidy & Bank Loan Application",
        duration: "4:20 min",
        url: "https://www.youtube.com/results?search_query=pm+surya+ghar+muft+bijli+yojana+subsidy",
        badge: "Subsidy Guide"
      }
    ];

    pane.innerHTML = `
      <div class="mb-3">
        <h6 class="fw-bold text-white mb-1"><i class="fas fa-camera text-success me-2"></i>Installation & Project Photos</h6>
        <small class="text-muted d-block mb-3">Real project deployment and site execution photos.</small>
        
        <div class="dc-media-grid">
          ${photos.slice(0, 6).map((p, idx) => `
            <div class="dc-photo-item" data-img-idx="${idx}" title="${p.caption}">
              <img src="${p.url}" alt="${p.caption}" loading="lazy" />
              <div style="position: absolute; bottom: 0; left: 0; right: 0; background: linear-gradient(to top, rgba(0,0,0,0.85), transparent); padding: 6px 8px; font-size: 10px; color: #fff; font-weight: 600; text-truncate;">
                ${p.caption}
              </div>
            </div>
          `).join("")}
        </div>
      </div>

      <div class="mt-4 mb-2">
        <h6 class="fw-bold text-white mb-1"><i class="fab fa-youtube text-danger me-2"></i>Video Walkthroughs & Customer Proof</h6>
        <small class="text-muted d-block mb-3">Customer testimonials, technical tours and commissioning proof.</small>

        ${videos.map(v => `
          <div class="dc-video-item">
            <div class="dc-video-play-btn">
              <i class="fas fa-play"></i>
            </div>
            <div style="flex: 1;">
              <span class="badge bg-danger bg-opacity-20 text-danger border border-danger border-opacity-30 mb-1" style="font-size: 9px; font-weight: 700;">
                ${v.badge} • ${v.duration}
              </span>
              <div class="fw-bold text-white" style="font-size: 13px;">${v.title}</div>
            </div>
            <a href="${v.url}" target="_blank" class="btn btn-sm btn-outline-light rounded-pill px-3" style="font-size: 11px;">
              Watch
            </a>
          </div>
        `).join("")}
      </div>
    `;
  }

  // ── Tab 4: About, Specs & PDF Brochure ──────────────────────────────
  private renderOverviewTab(cat: Catalog, pane: HTMLElement): void {
    let origin = APP_CONFIG.BASE_SERVER_URL;
    if (typeof window !== "undefined" && window.location?.origin && !window.location.origin.includes("localhost") && !window.location.origin.includes("capacitor")) {
      origin = window.location.origin;
    }
    const publicUrl = `${origin}/catalog/${cat.segment_code.toLowerCase().replace(/_/g, "-")}/${cat.slug}`;

    pane.innerHTML = `
      <!-- Overview Card -->
      <div class="dc-info-card">
        <h6 class="fw-bold text-white mb-2"><i class="fas fa-bullseye text-success me-2"></i>Solution Overview</h6>
        <p class="text-light small mb-3" style="line-height: 1.55;">
          ${cat.summary || cat.subtitle || "End-to-end clean-tech and infrastructure solutions engineered for high operational reliability, government subsidies, and maximum return on investment."}
        </p>

        <h6 class="fw-bold text-white mb-2"><i class="fas fa-language text-warning me-2"></i>Multilingual Copy Support</h6>
        <div class="d-flex flex-wrap gap-2 mb-3">
          <span class="badge bg-dark text-success border border-success border-opacity-30 p-2">English (Default)</span>
          <span class="badge bg-dark text-warning border border-warning border-opacity-30 p-2">తెలుగు (Telugu)</span>
          <span class="badge bg-dark text-info border border-info border-opacity-30 p-2">हिन्दी (Hindi)</span>
          <span class="badge bg-dark text-light border border-secondary border-opacity-30 p-2">தமிழ் (Tamil)</span>
        </div>
      </div>

      <!-- PDF Brochure Card -->
      <div class="dc-info-card">
        <h6 class="fw-bold text-white mb-1"><i class="fas fa-file-pdf text-danger me-2"></i>Official PDF Brochure Attachment</h6>
        <p class="text-muted small mb-2">
          High-resolution product specification brochure suitable for printing or sending alongside the interactive single-page link.
        </p>

        ${cat.pdf_brochure_url ? `
          <a href="${cat.pdf_brochure_url}" target="_blank" class="dc-brochure-download-btn">
            <i class="fas fa-download me-1"></i> Download Official PDF Brochure
          </a>
        ` : `
          <div class="alert alert-dark text-muted small p-2 mt-2 mb-0 border-secondary border-opacity-25 text-center">
            Standard web catalog brochure is bundled directly inside the interactive proposal link.
          </div>
        `}
      </div>

      <!-- Tracked Referral Link Card -->
      <div class="dc-info-card">
        <h6 class="fw-bold text-white mb-1"><i class="fas fa-link text-info me-2"></i>Shareable Single-Page Link</h6>
        <p class="text-muted small mb-2">Each dispatch generated via WhatsApp includes an intelligent click tracker that notifies you when the recipient opens the catalog.</p>
        
        <div class="p-2 rounded bg-dark border border-secondary border-opacity-25 font-monospace text-info small text-truncate mb-2">
          ${publicUrl}
        </div>

        <button type="button" class="dc-copy-link-btn" id="btnCopyPublicCatalogLink" data-link="${publicUrl}">
          <i class="fas fa-copy me-1"></i> Copy Web Catalog Link
        </button>
      </div>
    `;

    const copyBtn = pane.querySelector("#btnCopyPublicCatalogLink") as HTMLButtonElement;
    if (copyBtn) {
      copyBtn.addEventListener("click", async () => {
        const link = copyBtn.getAttribute("data-link") || publicUrl;
        try {
          await navigator.clipboard.writeText(link);
          const orig = copyBtn.innerHTML;
          copyBtn.innerHTML = '<i class="fas fa-check text-success me-1"></i> Copied to Clipboard!';
          setTimeout(() => { copyBtn.innerHTML = orig; }, 2000);
        } catch {
          alert("Catalog link: " + link);
        }
      });
    }
  }

  // ── WhatsApp Dispatch Modal ─────────────────────────────────────────
  private selectedLeadId: number | null = null;
  private selectedPartnerId: number | null = null;
  private searchDebounceTimer: any = null;

  private openMobileDispatchModal(cat: Catalog, prefillNote?: string): void {
    let modalEl = document.getElementById("mobileCatalogDispatchModal");
    if (modalEl) modalEl.remove();

    this.selectedLeadId = null;
    this.selectedPartnerId = null;

    modalEl = document.createElement("div");
    modalEl.id = "mobileCatalogDispatchModal";
    modalEl.style.cssText = `
      position: fixed; inset: 0; z-index: 10050;
      background: rgba(0, 0, 0, 0.78); backdrop-filter: blur(4px);
      display: flex; align-items: flex-end; justify-content: center;
      padding: 0; animation: fadeIn 0.15s ease-out;
    `;

    modalEl.innerHTML = `
      <div class="dispatch-sheet" style="
        background: #0f172a; width: 100%; max-width: 540px;
        max-height: 90vh; overflow-y: auto;
        border-top-left-radius: 24px; border-top-right-radius: 24px;
        border: 1px solid rgba(16, 185, 129, 0.3); border-bottom: none;
        box-shadow: 0 -12px 30px rgba(0,0,0,0.6);
        color: #f8fafc; padding: 20px 16px 28px 16px;
      ">
        <!-- Drag Handle Indicator -->
        <div style="width: 44px; height: 4px; background: rgba(255,255,255,0.25); border-radius: 2px; margin: 0 auto 14px auto;"></div>

        <!-- Header -->
        <div class="d-flex justify-content-between align-items-center mb-3 pb-2 border-bottom border-secondary border-opacity-25">
          <div class="d-flex align-items-center gap-2">
            <div style="width: 38px; height: 38px; border-radius: 50%; background: linear-gradient(135deg, #25d366, #128c7e); display: flex; align-items: center; justify-content: center; color: #fff; font-size: 20px; box-shadow: 0 2px 8px rgba(37,211,102,0.4);">
              <i class="fab fa-whatsapp"></i>
            </div>
            <div>
              <h6 class="fw-bold mb-0 text-white" style="font-size: 15px;">Send via WhatsApp</h6>
              <div class="text-muted" style="font-size: 11px;">${cat.title}</div>
            </div>
          </div>
          <button id="closeDispatchModalBtn" class="btn btn-sm btn-dark text-muted rounded-circle" style="width: 32px; height: 32px; padding: 0; font-size: 18px;">
            &times;
          </button>
        </div>

        <!-- Recipient Autocomplete Search -->
        <div class="mb-3">
          <label class="form-label fw-bold small text-light mb-1" style="font-size: 12px;">
            <i class="fas fa-search me-1 text-info"></i> Search Contact, Lead or Partner:
          </label>
          <div class="input-group input-group-sm">
            <input type="text" id="modalRecipientSearchInput" class="form-control" 
                   placeholder="Type name or phone number..."
                   style="background: #1e293b; color: #fff; border-color: #334155; font-size: 13px; padding: 8px 12px;" />
            <button class="btn btn-outline-secondary" type="button" id="modalClearSearchBtn">Clear</button>
          </div>
          <div id="modalSearchDropdown" style="display: none; background: #1e293b; border: 1px solid #334155; border-radius: 10px; max-height: 180px; overflow-y: auto; margin-top: 4px; box-shadow: 0 4px 14px rgba(0,0,0,0.5);">
            <!-- Dynamic search results -->
          </div>
        </div>

        <!-- Active Selected Recipient Pill -->
        <div id="modalSelectedCard" style="display: none; background: #13243d; border: 1px solid #0284c7; border-radius: 10px; padding: 10px 12px; margin-bottom: 12px;">
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
                   style="background: #1e293b; color: #fff; border-color: #334155; padding: 8px 12px;" />
          </div>
          <div class="col-5">
            <label class="form-label fw-bold text-light mb-1" style="font-size: 12px;">Name (optional)</label>
            <input type="text" id="modalRecipientName" class="form-control form-control-sm" 
                   placeholder="Recipient name"
                   style="background: #1e293b; color: #fff; border-color: #334155; padding: 8px 12px;" />
          </div>
        </div>

        <!-- Language Selector -->
        <div class="mb-3">
          <label class="form-label fw-bold text-light mb-1" style="font-size: 12px;">
            <i class="fas fa-language me-1 text-warning"></i> Catalog Language
          </label>
          <select id="modalCatalogLang" class="form-select form-select-sm" style="background: #1e293b; color: #fff; border-color: #334155; padding: 8px 12px;">
            <option value="en" selected>English</option>
            <option value="te">తెలుగు (Telugu)</option>
            <option value="hi">हिन्दी (Hindi)</option>
            <option value="ta">தமிழ் (Tamil)</option>
          </select>
        </div>

        <!-- Delivery Method -->
        <div class="mb-3">
          <label class="form-label fw-bold text-light mb-1" style="font-size: 12px;">Delivery Method</label>
          <div class="d-flex gap-3 p-2 rounded bg-dark border border-secondary border-opacity-25">
            <div class="form-check form-check-inline m-0">
              <input class="form-check-input" type="radio" name="modalDeliveryMethod" id="methodLink" value="web_link" checked>
              <label class="form-check-label text-light small" for="methodLink">Interactive Web Link</label>
            </div>
            <div class="form-check form-check-inline m-0">
              <input class="form-check-input" type="radio" name="modalDeliveryMethod" id="methodPdf" value="pdf_document">
              <label class="form-check-label text-light small" for="methodPdf">PDF Brochure</label>
            </div>
            <div class="form-check form-check-inline m-0">
              <input class="form-check-input" type="radio" name="modalDeliveryMethod" id="methodBoth" value="both">
              <label class="form-check-label text-light small" for="methodBoth">Both</label>
            </div>
          </div>
        </div>

        <!-- Custom Note -->
        <div class="mb-3">
          <label class="form-label fw-bold text-light mb-1" style="font-size: 12px;">Specialist Note / Custom Message</label>
          <textarea id="modalCustomNote" class="form-control form-control-sm" rows="2" 
                    placeholder="E.g., Based on our site visit discussion today..."
                    style="background: #1e293b; color: #fff; border-color: #334155; font-size: 12px;">${prefillNote || ""}</textarea>
        </div>

        <!-- Action Button -->
        <div class="d-grid gap-2 pt-2">
          <button id="modalSubmitDispatchBtn" class="dc-btn-wa">
            <i class="fab fa-whatsapp"></i>
            <span>Send Catalog Now</span>
          </button>
        </div>
      </div>
    `;

    document.body.appendChild(modalEl);

    // Event listeners
    const closeBtn = modalEl.querySelector("#closeDispatchModalBtn");
    if (closeBtn) closeBtn.addEventListener("click", () => modalEl?.remove());

    modalEl.addEventListener("click", (e) => {
      if (e.target === modalEl) modalEl?.remove();
    });

    const searchInput = modalEl.querySelector("#modalRecipientSearchInput") as HTMLInputElement;
    const dropdown = modalEl.querySelector("#modalSearchDropdown") as HTMLElement;
    const clearSearchBtn = modalEl.querySelector("#modalClearSearchBtn");

    if (clearSearchBtn && searchInput) {
      clearSearchBtn.addEventListener("click", () => {
        searchInput.value = "";
        if (dropdown) dropdown.style.display = "none";
      });
    }

    if (searchInput) {
      searchInput.addEventListener("focus", () => {
        this.performMobileRecipientSearch(searchInput.value.trim(), dropdown);
      });

      searchInput.addEventListener("input", () => {
        clearTimeout(this.searchDebounceTimer);
        const query = searchInput.value.trim();
        this.searchDebounceTimer = setTimeout(() => {
          this.performMobileRecipientSearch(query, dropdown);
        }, 220);
      });
    }

    const removeBtn = modalEl.querySelector("#modalRemoveSelectedBtn");
    if (removeBtn) {
      removeBtn.addEventListener("click", () => {
        this.selectedLeadId = null;
        this.selectedPartnerId = null;
        const card = modalEl?.querySelector("#modalSelectedCard") as HTMLElement;
        if (card) card.style.display = "none";
      });
    }

    const submitBtn = modalEl.querySelector("#modalSubmitDispatchBtn") as HTMLButtonElement;
    if (submitBtn) {
      submitBtn.addEventListener("click", async () => {
        const phoneInput = modalEl?.querySelector("#modalRecipientPhone") as HTMLInputElement;
        const nameInput = modalEl?.querySelector("#modalRecipientName") as HTMLInputElement;
        const langSelect = modalEl?.querySelector("#modalCatalogLang") as HTMLSelectElement;
        const noteText = modalEl?.querySelector("#modalCustomNote") as HTMLTextAreaElement;
        const methodEl = modalEl?.querySelector('input[name="modalDeliveryMethod"]:checked') as HTMLInputElement;

        const phone = (phoneInput?.value || "").trim().replace(/\D/g, "");
        if (phone.length < 10) {
          alert("Please enter a valid 10-digit mobile number.");
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
            language_code: langSelect?.value || "en",
            delivery_method: methodEl?.value || "web_link",
            custom_note: noteText?.value?.trim() || undefined
          });

          modalEl?.remove();

          if (res && res.success) {
            this.fetchSegmentTelemetry(cat.segment_code);
            this.fetchQuickDispatchCount();
            if (res.wa_me_url) {
              window.open(res.wa_me_url, "_blank");
            } else {
              alert("Catalog proposal queued successfully for WhatsApp delivery!");
            }
          } else {
            alert("Notice: " + (res?.message || "Dispatch completed"));
          }
        } catch (err: any) {
          submitBtn.disabled = false;
          submitBtn.innerHTML = '<i class="fab fa-whatsapp me-1"></i> Send Catalog Now';
          alert("Dispatch error: " + (err.message || "Unknown error"));
        }
      });
    }
  }

  private async performMobileRecipientSearch(query: string, dropdown: HTMLElement): Promise<void> {
    if (!dropdown) return;

    try {
      const q = encodeURIComponent(query);
      const res = await apiService.get<any>(`/api/v1/digital-catalogs/recipients/search?q=${q}&limit=12`);
      const data = res?.data || res || {};
      const results = data.results || res?.results || [];

      if (results.length === 0) {
        dropdown.innerHTML = '<div class="p-2 text-muted small text-center">No matching contacts found</div>';
        dropdown.style.display = "block";
        return;
      }

      dropdown.innerHTML = results.map((item: any, idx: number) => {
        const badgeBg = item.badge_color || "#0284c7";
        return `
          <div class="mobile-recipient-item p-2 border-bottom border-secondary border-opacity-25" 
               data-idx="${idx}"
               style="cursor: pointer; display: flex; justify-content: space-between; align-items: center; background: transparent;">
            <div>
              <div class="fw-bold text-white small">${item.name || "Unknown"}</div>
              <div class="text-muted" style="font-size: 11px;">${item.formatted_phone || item.phone} • ${item.subtitle || ""}</div>
            </div>
            <span class="badge rounded-pill" style="background: ${badgeBg}; color: #ffffff; font-size: 10px;">
              ${item.source}
            </span>
          </div>
        `;
      }).join("");
      dropdown.style.display = "block";

      dropdown.querySelectorAll(".mobile-recipient-item").forEach((el) => {
        el.addEventListener("click", () => {
          const idx = parseInt(el.getAttribute("data-idx") || "0", 10);
          const item = results[idx];
          if (item) {
            this.selectMobileRecipient(item);
            dropdown.style.display = "none";
          }
        });
      });
    } catch (err) {
      console.warn("Recipient search error:", err);
      dropdown.style.display = "none";
    }
  }

  private selectMobileRecipient(item: any): void {
    const modalEl = document.getElementById("mobileCatalogDispatchModal");
    if (!modalEl) return;

    this.selectedLeadId = item.lead_id || null;
    this.selectedPartnerId = item.partner_id || null;

    const phoneInput = modalEl.querySelector("#modalRecipientPhone") as HTMLInputElement;
    const nameInput = modalEl.querySelector("#modalRecipientName") as HTMLInputElement;
    if (phoneInput) phoneInput.value = item.phone || "";
    if (nameInput) nameInput.value = item.name || "";

    const card = modalEl.querySelector("#modalSelectedCard") as HTMLElement;
    const cardName = modalEl.querySelector("#modalSelectedName");
    const cardPhone = modalEl.querySelector("#modalSelectedPhone");

    if (card && cardName && cardPhone) {
      cardName.textContent = `${item.name} (${item.source})`;
      cardPhone.textContent = `${item.formatted_phone || item.phone} ${item.subtitle ? "• " + item.subtitle : ""}`;
      card.style.display = "block";
    }
  }

  // ── Dispatch History & Telemetry Modal ──────────────────────────────
  private currentMobileHistoryScope: "my" | "team" = "my";
  private mobileHistoryDebounceTimer: any = null;

  private openMobileDispatchHistoryModal(): void {
    let modalEl = document.getElementById("mobileCatalogHistoryModal");
    if (modalEl) modalEl.remove();

    this.currentMobileHistoryScope = "my";

    modalEl = document.createElement("div");
    modalEl.id = "mobileCatalogHistoryModal";
    modalEl.style.cssText = `
      position: fixed; inset: 0; z-index: 10050;
      background: rgba(0, 0, 0, 0.85); backdrop-filter: blur(5px);
      display: flex; align-items: flex-end; justify-content: center;
      padding: 0; animation: fadeIn 0.15s ease-out;
    `;

    modalEl.innerHTML = `
      <div class="history-sheet" style="
        background: #0f172a; width: 100%; max-width: 560px;
        height: 92vh; display: flex; flex-direction: column;
        border-top-left-radius: 24px; border-top-right-radius: 24px;
        border: 1px solid rgba(56, 189, 248, 0.3); border-bottom: none;
        box-shadow: 0 -12px 30px rgba(0,0,0,0.6);
        color: #f8fafc; padding: 18px 16px 16px 16px;
      ">
        <!-- Drag Handle -->
        <div style="width: 44px; height: 4px; background: rgba(255,255,255,0.25); border-radius: 2px; margin: 0 auto 12px auto;"></div>

        <!-- Header -->
        <div class="d-flex justify-content-between align-items-center mb-2 pb-2 border-bottom border-secondary border-opacity-25">
          <div class="d-flex align-items-center gap-2">
            <div style="width: 36px; height: 36px; border-radius: 50%; background: #0284c7; display: flex; align-items: center; justify-content: center; color: #fff; font-size: 16px;">
              <i class="fas fa-chart-line"></i>
            </div>
            <div>
              <h6 class="fw-bold mb-0 text-white" style="font-size: 15px;">Dispatch History & Telemetry</h6>
              <div class="text-muted" style="font-size: 11px;">Real-time link views & engagement tracking</div>
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
              <input type="text" id="mobileHistSearchInput" placeholder="Search recipient, phone, staff..." style="width: 100%; background: #1e293b; color: #fff; border: 1px solid #334155; border-radius: 8px; font-size: 12px; padding: 7px 10px 7px 30px; outline: none;">
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
            <p class="text-muted small mt-2">Loading dispatch telemetry...</p>
          </div>
        </div>
      </div>
    `;

    document.body.appendChild(modalEl);

    // Event listeners
    const closeBtn = modalEl.querySelector("#closeMobileHistModalBtn");
    if (closeBtn) closeBtn.addEventListener("click", () => modalEl?.remove());
    modalEl.addEventListener("click", (e) => {
      if (e.target === modalEl) modalEl?.remove();
    });

    const btnScopeMy = modalEl.querySelector("#btnMobileScopeMy") as HTMLElement;
    const btnScopeTeam = modalEl.querySelector("#btnMobileScopeTeam") as HTMLElement;

    if (btnScopeMy && btnScopeTeam) {
      btnScopeMy.addEventListener("click", () => {
        this.currentMobileHistoryScope = "my";
        btnScopeMy.className = "btn btn-sm btn-success rounded-pill flex-fill fw-bold py-1";
        btnScopeTeam.className = "btn btn-sm btn-outline-secondary text-light rounded-pill flex-fill fw-bold py-1";
        this.fetchAndRenderMobileHistory();
      });

      btnScopeTeam.addEventListener("click", () => {
        this.currentMobileHistoryScope = "team";
        btnScopeTeam.className = "btn btn-sm btn-success rounded-pill flex-fill fw-bold py-1";
        btnScopeMy.className = "btn btn-sm btn-outline-secondary text-light rounded-pill flex-fill fw-bold py-1";
        this.fetchAndRenderMobileHistory();
      });
    }

    const resetBtn = modalEl.querySelector("#btnMobileHistReset");
    if (resetBtn) {
      resetBtn.addEventListener("click", () => {
        const s = modalEl?.querySelector("#mobileHistSearchInput") as HTMLInputElement;
        const m = modalEl?.querySelector("#mobileHistModelFilter") as HTMLSelectElement;
        const e = modalEl?.querySelector("#mobileHistEngagementFilter") as HTMLSelectElement;
        const tf = modalEl?.querySelector("#mobileHistTimeframeFilter") as HTMLSelectElement;
        if (s) s.value = "";
        if (m) m.value = "ALL";
        if (e) e.value = "all";
        if (tf) tf.value = "all";
        this.fetchAndRenderMobileHistory();
      });
    }

    // Preload opposite scope count for team badge
    apiService.get<any>("/api/v1/digital-catalogs/dispatches/history?scope=team&limit=1").then(teamRes => {
      const p = teamRes?.data || teamRes || {};
      const t = p?.total ?? teamRes?.total ?? 0;
      const b = modalEl?.querySelector("#mobileBadgeTeam");
      if (b && t) b.textContent = String(t);
    }).catch(() => {});

    const searchInput = modalEl.querySelector("#mobileHistSearchInput") as HTMLInputElement;
    if (searchInput) {
      searchInput.addEventListener("input", () => {
        clearTimeout(this.mobileHistoryDebounceTimer);
        this.mobileHistoryDebounceTimer = setTimeout(() => {
          this.fetchAndRenderMobileHistory();
        }, 300);
      });
    }

    ["mobileHistModelFilter", "mobileHistEngagementFilter", "mobileHistTimeframeFilter"].forEach(id => {
      const el = modalEl?.querySelector(`#${id}`);
      if (el) {
        el.addEventListener("change", () => this.fetchAndRenderMobileHistory());
      }
    });

    this.fetchAndRenderMobileHistory();
  }

  private async fetchAndRenderMobileHistory(): Promise<void> {
    const modalEl = document.getElementById("mobileCatalogHistoryModal");
    if (!modalEl) return;

    const listContainer = modalEl.querySelector("#mobileHistListContainer");
    if (listContainer) {
      listContainer.innerHTML = `
        <div class="text-center py-4">
          <div class="spinner-border spinner-border-sm text-info" role="status"></div>
          <p class="text-muted small mt-2">Loading dispatch telemetry...</p>
        </div>
      `;
    }

    try {
      const q = ((modalEl.querySelector("#mobileHistSearchInput") as HTMLInputElement)?.value || "").trim();
      const segment_code = (modalEl.querySelector("#mobileHistModelFilter") as HTMLSelectElement)?.value || "ALL";
      const engagement = (modalEl.querySelector("#mobileHistEngagementFilter") as HTMLSelectElement)?.value || "all";
      const timeframe = (modalEl.querySelector("#mobileHistTimeframeFilter") as HTMLSelectElement)?.value || "all";

      const params = new URLSearchParams();
      params.set("scope", this.currentMobileHistoryScope);
      if (q) params.set("q", q);
      if (segment_code && segment_code !== "ALL") params.set("segment_code", segment_code);
      if (engagement && engagement !== "all") params.set("engagement", engagement);
      if (timeframe && timeframe !== "all") params.set("timeframe", timeframe);
      params.set("limit", "100");

      const res = await apiService.get<any>("/api/v1/digital-catalogs/dispatches/history?" + params.toString());
      const payload = res?.data || res || {};
      const dispatches = payload?.dispatches || res?.dispatches || [];
      const stats = payload?.stats || res?.stats || {};
      const total = payload?.total ?? res?.total ?? 0;

      // Update KPIs
      const kpiDisp = modalEl.querySelector("#mobileHistKpiDispatches");
      const kpiClicks = modalEl.querySelector("#mobileHistKpiClicks");
      const kpiRate = modalEl.querySelector("#mobileHistKpiRate");
      const kpiModel = modalEl.querySelector("#mobileHistKpiModel");

      if (kpiDisp) kpiDisp.textContent = stats.total_dispatches || 0;
      if (kpiClicks) kpiClicks.textContent = stats.total_views || 0;
      if (kpiRate) kpiRate.textContent = `${stats.view_rate_percent || 0}%`;
      if (kpiModel) kpiModel.textContent = (stats.top_model || "SOLAR").replace(/_/g, " ");

      const badgeMy = modalEl.querySelector("#mobileBadgeMy");
      const badgeTeam = modalEl.querySelector("#mobileBadgeTeam");
      if (this.currentMobileHistoryScope === "my" && badgeMy) {
        badgeMy.textContent = String(total);
      } else if (this.currentMobileHistoryScope === "team" && badgeTeam) {
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

      const isTeam = (this.currentMobileHistoryScope === "team");

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
              ${(d.staff_name || "U").charAt(0)}
            </div>
            <div class="small text-muted" style="font-size: 11px;">
              Dispatched by <strong class="text-white">${d.staff_name || "Staff"}</strong> (${d.staff_code || ""})
            </div>
          </div>
        ` : "";

        const origin = (!window.location.origin || window.location.origin.includes("localhost") || window.location.origin.includes("capacitor")) ? APP_CONFIG.BASE_SERVER_URL : window.location.origin;
        const fullTracked = origin + (d.tracked_url || "");
        const waUrl = `https://wa.me/91${d.recipient_phone}?text=${encodeURIComponent("Hello " + (d.recipient_name || "") + ", here is the catalog proposal: " + fullTracked)}`;

        const dateStr = d.sent_at ? new Date(d.sent_at).toLocaleDateString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) : "N/A";

        return `
          <div class="card bg-dark border-secondary border-opacity-25 rounded-3 p-3 mb-2 shadow-sm">
            ${staffHeader}
            <div class="d-flex justify-content-between align-items-start mb-1">
              <div>
                <div class="fw-bold text-white small">${d.recipient_name || "Customer"}</div>
                <div class="text-muted" style="font-size: 11px;"><i class="fas fa-phone-alt me-1 text-secondary"></i>+91 ${d.recipient_phone}</div>
              </div>
              <span class="badge bg-dark text-info border border-info border-opacity-25 font-monospace" style="font-size: 10px;">
                #${d.share_ref_code || ""}
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
      }).join("");

      listContainer.querySelectorAll(".mobile-copy-btn").forEach(btn => {
        btn.addEventListener("click", async (e) => {
          const target = (e.currentTarget as HTMLElement);
          const link = target.getAttribute("data-url") || "";
          try {
            await navigator.clipboard.writeText(link);
            const orig = target.innerHTML;
            target.innerHTML = '<i class="fas fa-check text-success"></i>';
            setTimeout(() => { target.innerHTML = orig; }, 2000);
          } catch {
            alert("Catalog link: " + link);
          }
        });
      });

    } catch (err: any) {
      console.error("Mobile history error:", err);
      if (listContainer) {
        listContainer.innerHTML = `
          <div class="alert alert-dark text-center text-danger small">
            Failed to load dispatch history: ${err.message || "Error"}
          </div>
        `;
      }
    }
  }
}
