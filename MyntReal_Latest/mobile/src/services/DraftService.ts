// DC Draft Manager — Mobile (DC-DRAFT-001)
// Mirrors web draft-manager: localStorage + backend sync every 30s + beforeunload.

const STORAGE_PREFIX = 'dc_draft_v1_';
const SYNC_INTERVAL_MS = 30000;
const DEBOUNCE_MS = 1500;
const TTL_DAYS = 7;
const API_BASE = '/api/v1/drafts';

interface DraftEntry {
  data: Record<string, unknown>;
  ts: number;
  key: string;
  url: string;
}

class DraftServiceClass {
  private _key: string | null = null;
  private _getDataFn: (() => Record<string, unknown>) | null = null;
  private _setDataFn: ((data: Record<string, unknown>) => void) | null = null;
  private _syncTimer: ReturnType<typeof setInterval> | null = null;
  private _debounceTimer: ReturnType<typeof setTimeout> | null = null;
  private _initialized = false;

  private _getToken(): string | null {
    return (
      localStorage.getItem('staff_token') ||
      localStorage.getItem('token') ||
      localStorage.getItem('partner_token') ||
      localStorage.getItem('member_token') ||
      null
    );
  }

  private _saveLocal(data: Record<string, unknown>): void {
    if (!this._key || !data || Object.keys(data).length === 0) return;
    try {
      const entry: DraftEntry = { data, ts: Date.now(), key: this._key, url: window.location.pathname };
      localStorage.setItem(STORAGE_PREFIX + this._key, JSON.stringify(entry));
    } catch (_) {}
  }

  loadLocal(): DraftEntry | null {
    if (!this._key) return null;
    try {
      const raw = localStorage.getItem(STORAGE_PREFIX + this._key);
      if (!raw) return null;
      const entry: DraftEntry = JSON.parse(raw);
      if (Date.now() - entry.ts > TTL_DAYS * 86400000) {
        localStorage.removeItem(STORAGE_PREFIX + this._key);
        return null;
      }
      return entry;
    } catch (_) { return null; }
  }

  async syncToBackend(): Promise<void> {
    const token = this._getToken();
    if (!token || !this._key || !this._getDataFn) return;
    try {
      const data = this._getDataFn();
      if (!data || Object.keys(data).length === 0) return;
      await fetch(`${API_BASE}/${encodeURIComponent(this._key)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ draft_data: JSON.stringify(data), page_url: window.location.pathname }),
        keepalive: true,
      });
    } catch (_) {}
  }

  async loadFromBackend(): Promise<Record<string, unknown> | null> {
    const token = this._getToken();
    if (!token || !this._key) return null;
    try {
      const r = await fetch(`${API_BASE}/${encodeURIComponent(this._key)}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!r.ok) return null;
      const d = await r.json();
      return d.draft_data ? JSON.parse(d.draft_data) : null;
    } catch (_) { return null; }
  }

  clear(): void {
    if (!this._key) return;
    try { localStorage.removeItem(STORAGE_PREFIX + this._key); } catch (_) {}
    const token = this._getToken();
    if (token) {
      fetch(`${API_BASE}/${encodeURIComponent(this._key)}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
        keepalive: true,
      }).catch(() => {});
    }
  }

  onInput(): void {
    if (this._debounceTimer) clearTimeout(this._debounceTimer);
    this._debounceTimer = setTimeout(() => {
      if (this._getDataFn) {
        const data = this._getDataFn();
        if (data && Object.keys(data).length > 0) this._saveLocal(data);
      }
    }, DEBOUNCE_MS);
  }

  init(key: string, getDataFn: () => Record<string, unknown>, setDataFn: (d: Record<string, unknown>) => void): void {
    if (this._initialized && this._key === key) return;
    this._key = key;
    this._getDataFn = getDataFn;
    this._setDataFn = setDataFn;
    this._initialized = true;

    if (this._syncTimer) clearInterval(this._syncTimer);
    this._syncTimer = setInterval(() => { this.syncToBackend(); }, SYNC_INTERVAL_MS);

    window.addEventListener('pagehide', () => {
      if (this._getDataFn) {
        const data = this._getDataFn();
        if (data && Object.keys(data).length > 0) this._saveLocal(data);
      }
      this.syncToBackend();
    });
  }

  async checkAndPromptRestore(
    promptFn: (ago: string) => Promise<boolean>
  ): Promise<Record<string, unknown> | null> {
    const local = this.loadLocal();
    let entry: DraftEntry | null = local;
    if (!entry) {
      const backendData = await this.loadFromBackend();
      if (backendData && Object.keys(backendData).length > 0) {
        entry = { data: backendData, ts: Date.now() - 300000, key: this._key!, url: '' };
      }
    }
    if (!entry) return null;
    const ago = this._timeAgo(entry.ts);
    const shouldRestore = await promptFn(ago);
    if (shouldRestore) {
      if (this._setDataFn) this._setDataFn(entry.data);
      return entry.data;
    } else {
      this.clear();
      return null;
    }
  }

  private _timeAgo(ts: number): string {
    const diff = Math.floor((Date.now() - ts) / 1000);
    if (diff < 120) return 'just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
  }
}

export const DraftService = new DraftServiceClass();
export default DraftService;
