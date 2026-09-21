/**
 * Universal Authenticated Web Embed Page for Staff Modules
 * DC Protocol: DC_MOBILE_STAFF_EMBED_001
 * Enables 100% feature and page parity across Web, Mobile, Android, and iOS.
 */
import { PageHeader } from '../components/PageHeader';
import { APP_CONFIG } from '../config/app.config';
import { getStoredToken } from '../utils/token';

export interface EmbedPageParams {
  url?: string;
  title?: string;
  tab?: string;
}

export class StaffEmbedPage {
  private container: HTMLElement;
  private url: string;
  private title: string;
  private tab?: string;

  constructor(container: HTMLElement, params?: EmbedPageParams) {
    this.container = container;
    this.url = params?.url || '/staff/dashboard';
    this.title = params?.title || 'Staff Portal';
    this.tab = params?.tab;
  }

  async init(params?: EmbedPageParams): Promise<void> {
    if (params?.url) this.url = params.url;
    if (params?.title) this.title = params.title;
    if (params?.tab) this.tab = params.tab;

    this.container.innerHTML = await this.render();
    PageHeader.attachBackHandler();
    this.attachFrameEvents();
  }

  async render(): Promise<string> {
    const token = getStoredToken();
    const separator = this.url.includes('?') ? '&' : '?';
    let fullUrl = `${APP_CONFIG.MEDIA_BASE_URL}${this.url}${separator}embed=true&token=${encodeURIComponent(token)}`;
    if (this.tab) {
      fullUrl += `&tab=${encodeURIComponent(this.tab)}`;
    }

    return `
      <div class="embed-page-wrapper" style="background:#f8fafc;min-height:100vh;display:flex;flex-direction:column;">
        ${PageHeader.render({ title: this.title, showBack: true })}
        <div class="embed-frame-container" style="flex:1;position:relative;width:100%;height:calc(100vh - 64px);overflow:hidden;-webkit-overflow-scrolling:touch;">
          <div id="embed-loading-spinner" style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px;color:#64748b;z-index:1;">
            <div class="spinner" style="width:36px;height:36px;border:3px solid #e2e8f0;border-top-color:#3b82f6;border-radius:50%;animation:spin 0.8s linear infinite;"></div>
            <span style="font-size:13px;font-weight:500;">Loading ${this.title}...</span>
          </div>
          <iframe
            id="staff-embed-frame"
            src="${fullUrl}"
            allow="microphone; camera; autoplay; clipboard-write; geolocation"
            style="width:100%;height:100%;border:0;background:#fff;position:relative;z-index:2;opacity:0;transition:opacity 0.2s ease-in-out;touch-action:auto;"
            loading="lazy"
            title="${this.title}"
          ></iframe>
        </div>
      </div>
      <style>
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      </style>
    `;
  }

  private attachFrameEvents(): void {
    const frame = this.container.querySelector('#staff-embed-frame') as HTMLIFrameElement;
    const spinner = this.container.querySelector('#embed-loading-spinner') as HTMLElement;

    if (frame) {
      frame.onload = () => {
        if (spinner) spinner.style.display = 'none';
        frame.style.opacity = '1';
      };

      frame.onerror = () => {
        if (spinner) {
          spinner.innerHTML = `
            <div style="text-align:center;padding:20px;">
              <i class="fas fa-exclamation-triangle" style="font-size:32px;color:#ef4444;margin-bottom:10px;"></i>
              <div style="font-weight:600;color:#0f172a;margin-bottom:6px;">Unable to load page</div>
              <div style="font-size:12px;color:#64748b;margin-bottom:16px;">Please check your connection and try again.</div>
              <button onclick="const f = document.getElementById('staff-embed-frame'); if(f) f.src = f.src;" style="background:#3b82f6;color:#fff;border:none;padding:8px 16px;border-radius:6px;font-size:13px;cursor:pointer;">Retry</button>
            </div>
          `;
        }
      };
    }
  }
}

export default StaffEmbedPage;
