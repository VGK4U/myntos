/**
 * VGK4U Bonanza Rewards — Mobile Offers Page
 * DC Protocol: DC_MOBILE_VGK4U_PARITY_001 (May 2026)
 *
 * Web-Mobile Parity: matches the redesigned web Bonanza Rewards sidebar tab.
 * Shows ALL bonanzas (cash + gift) as large offer cards with filter chips,
 * prominent reward badges, status overlays and inline claim support.
 */

import { apiService } from '../../services/api.service';
import { PageHeader } from '../../components/PageHeader';

interface BonanzaItem {
  id: number;
  name: string;
  reward_type: string;
  is_monetary: boolean;
  reward_amount?: number;
  slab_extra_amount?: number;
  image_url?: string;
  status: string;
  processed_status?: string;
  achievement_percentage?: number;
  current_progress?: number;
  target_requirement?: number;
  registered_target?: number;
  activated_target?: number;
  registered_target_bonus?: boolean;
  partner_is_activated?: boolean;
  segment_name?: string;
  start_date?: string;
  end_date?: string;
  grace_days?: number;
  max_winners?: number;
  current_winners?: number;
  slots_remaining?: number;
  slots_full?: boolean;
  claimed_date?: string;
  award_name?: string;
  reward_text?: string;
  criteria_type?: string;
}

type FilterKey = 'all' | 'active' | 'claim' | 'won' | 'claimed_proc' | 'upcoming' | 'missed' | 'inactive';

const FILTERS: { key: FilterKey; label: string; icon: string }[] = [
  { key: 'all',         label: 'All',       icon: 'fas fa-th-large' },
  { key: 'active',      label: 'Active',    icon: 'fas fa-fire' },
  { key: 'claim',       label: 'Claim Now', icon: 'fas fa-gift' },
  { key: 'won',         label: 'Won',       icon: 'fas fa-trophy' },
  { key: 'claimed_proc',label: 'Claimed',   icon: 'fas fa-check-circle' },
  { key: 'upcoming',    label: 'Upcoming',  icon: 'fas fa-calendar-alt' },
  { key: 'missed',      label: 'Missed',    icon: 'fas fa-times-circle' },
  { key: 'inactive',    label: 'Inactive',  icon: 'fas fa-pause-circle' },
];

const WON_STATUSES = ['Claimed','Achieved - Claimed','Processing','Staff Verified',
                      'Procurement In Progress','Dispatched','Delivered','Completed',
                      'Payment Released','Paid'];

const BG_GRADIENTS: Record<string, string> = {
  completed_deals: 'linear-gradient(135deg,#4c1d95,#7c3aed)',
  solar:           'linear-gradient(135deg,#92400e,#d97706)',
  direct_referral: 'linear-gradient(135deg,#1e3a5f,#2563eb)',
  matching_points: 'linear-gradient(135deg,#065f46,#059669)',
  team_size:       'linear-gradient(135deg,#7c2d12,#ea580c)',
};
const ICON_MAP: Record<string, string> = {
  completed_deals: 'fas fa-handshake',
  solar:           'fas fa-solar-panel',
  direct_referral: 'fas fa-user-plus',
  matching_points: 'fas fa-sync',
  team_size:       'fas fa-users',
};

function esc(s: unknown): string {
  return String(s ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function fmtDate(d?: string): string {
  if (!d) return '—';
  const ist = (d.endsWith('Z') || d.includes('+')) ? d : d + '+05:30';
  return new Date(ist).toLocaleDateString('en-IN',{day:'2-digit',month:'short',year:'2-digit',timeZone:'Asia/Kolkata'});
}
function bgGrad(criteriaType?: string, missed?: boolean): string {
  if (missed) return 'linear-gradient(135deg,#374151,#6b7280)';
  return BG_GRADIENTS[criteriaType ?? ''] ?? 'linear-gradient(135deg,#312e81,#6d28d9)';
}

interface RewardFile {
  advance_id: number;
  entry_number: string;
  advance_status: string;
  file_date?: string;
  lead_name: string;
  bonanza_id: number;
  bonanza_name: string;
  slab_extra_amount?: number;
  bonanza_start?: string;
  bonanza_end?: string;
  slab_bonus_paid: boolean;
  processed_status?: string;
  achieved_date?: string;
}

export class VGKBonanzaRewardsPage {
  private container: HTMLElement;
  private all: BonanzaItem[] = [];
  private rewardFiles: RewardFile[] = [];
  private filter: FilterKey = 'all';
  private loading = true;
  private error = '';

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.load();
  }

  private async load(force = false): Promise<void> {
    this.loading = true;
    this.error = '';
    this.refreshContent();
    try {
      const [res, filesRes] = await Promise.all([
        apiService.get<{ success: boolean; bonanzas?: BonanzaItem[] }>('/bonanza/my-bonanzas'),
        apiService.get<{ success: boolean; files?: RewardFile[] }>('/bonanza/my-reward-files'),
      ]);
      if (res.success && res.data) {
        this.all = (res.data.bonanzas || []) as BonanzaItem[];
      } else {
        this.all = [];
      }
      this.rewardFiles = (filesRes.data?.files || []) as RewardFile[];
    } catch {
      this.error = 'Could not load bonanza rewards. Please try again.';
      this.all = [];
      this.rewardFiles = [];
    }
    this.loading = false;
    this.refreshContent();
  }

  private render(): void {
    this.container.innerHTML = `
      <style>
        .bnz-filter-bar{display:flex;gap:8px;flex-wrap:nowrap;overflow-x:auto;padding:0 12px 6px;-webkit-overflow-scrolling:touch;scrollbar-width:none}
        .bnz-filter-bar::-webkit-scrollbar{display:none}
        .bnz-fc{flex-shrink:0;background:#f5f3ff;border:1.5px solid #ddd6fe;color:#6d28d9;border-radius:20px;padding:6px 14px;font-size:12px;font-weight:700;cursor:pointer;white-space:nowrap}
        .bnz-fc.active{background:linear-gradient(135deg,#7c3aed,#6d28d9);border-color:#7c3aed;color:#fff;box-shadow:0 2px 8px rgba(124,58,237,.4)}
        /* Dark offer card */
        .bnz-card{background:#111827;border-radius:18px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,.25);margin:0 12px 18px}
        .bnz-card.bnz-missed{opacity:.72}
        /* Image: full image, no crop */
        .bnz-img{position:relative;background:#0f0f1a;display:flex;align-items:center;justify-content:center;overflow:hidden;min-height:180px}
        .bnz-img::after{content:'';position:absolute;bottom:0;left:0;right:0;height:60px;background:linear-gradient(to top,rgba(0,0,0,.75),transparent);pointer-events:none}
        .bnz-img img{width:100%;height:auto;max-height:260px;object-fit:contain;display:block}
        .bnz-img-ph{width:100%;min-height:180px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10px;color:rgba(255,255,255,.8);font-size:13px;font-weight:800;padding:28px 16px}
        .bnz-img-ph i{font-size:42px;opacity:.85}
        /* Overlays: bottom of image above the gradient */
        .bnz-sov{position:absolute;bottom:10px;left:10px;z-index:2}
        .bnz-rov{position:absolute;bottom:10px;right:10px;z-index:2;text-align:right}
        /* Status chips */
        .bnz-chip{display:inline-flex;align-items:center;gap:5px;padding:5px 12px;border-radius:20px;font-size:11px;font-weight:800}
        .bnz-chip-prog{background:#2563eb;color:#fff}
        .bnz-chip-claim{background:linear-gradient(135deg,#7c3aed,#a855f7);color:#fff;box-shadow:0 0 10px rgba(124,58,237,.6)}
        .bnz-chip-ach{background:#16a34a;color:#fff}
        .bnz-chip-up{background:#d97706;color:#fff}
        .bnz-chip-miss{background:#dc2626;color:#fff}
        .bnz-chip-clmd{background:#6d28d9;color:#fff}
        .bnz-chip-dlv{background:#059669;color:#fff}
        /* Reward badge */
        .bnz-rbadge{padding:6px 12px;border-radius:11px;font-weight:900;line-height:1.25;text-align:right}
        .bnz-rb-amt{font-size:17px}
        .bnz-rb-lbl{font-size:9px;opacity:.85;text-transform:uppercase;letter-spacing:.04em}
        .bnz-rbadge-cash{background:linear-gradient(135deg,#065f46,#059669);color:#fff;box-shadow:0 2px 8px rgba(5,150,105,.4)}
        .bnz-rbadge-free{background:linear-gradient(135deg,#92400e,#f59e0b);color:#fff;box-shadow:0 2px 8px rgba(245,158,11,.35)}
        /* Dark body */
        .bnz-body{padding:13px 14px 16px;background:#1a1a2e}
        .bnz-name{font-size:16px;font-weight:900;color:#fff;margin-bottom:5px;line-height:1.3}
        .bnz-meta{display:flex;flex-wrap:wrap;gap:6px;font-size:11px;color:#9ca3af;margin-bottom:10px;align-items:center}
        .bnz-seg{background:rgba(124,58,237,.3);color:#c4b5fd;border-radius:6px;padding:2px 7px;font-weight:700;font-size:10px;border:1px solid rgba(124,58,237,.35)}
        .bnz-pb-bg{background:rgba(255,255,255,.1);border-radius:99px;height:8px;overflow:hidden;margin:5px 0 4px}
        .bnz-pb-fill{height:100%;border-radius:99px;transition:width .4s}
        .bnz-footer{display:flex;gap:10px;flex-wrap:wrap;font-size:11px;color:#6b7280;margin-top:10px;padding-top:10px;border-top:1px solid rgba(255,255,255,.07)}
        .bnz-tier-row{border-radius:9px;overflow:hidden;margin-bottom:6px;border:1px solid rgba(255,255,255,.08)}
        .bnz-tier-row.active{border-color:rgba(124,58,237,.55);background:rgba(124,58,237,.1)}
        .bnz-tier-h{padding:7px 10px;display:flex;justify-content:space-between;align-items:center}
        .bnz-tier-bar{height:5px;background:rgba(255,255,255,.07)}
      </style>
      <div class="page-container">
        ${PageHeader.render({ title: 'Bonanza Rewards', showBack: true })}
        <div style="margin-bottom:12px">
          <div class="bnz-filter-bar" id="bnzFilterBar">
            ${FILTERS.map(f => `<button class="bnz-fc${f.key==='all'?' active':''}" data-filter="${f.key}"><i class="${f.icon} me-1"></i>${f.label}</button>`).join('')}
          </div>
        </div>
        <div id="bnzContent">
          <div style="padding:40px;text-align:center;color:#9ca3af"><i class="fas fa-spinner fa-spin fa-2x"></i></div>
        </div>
        <div style="height:24px"></div>
      </div>
    `;
    PageHeader.attachListeners({ title: 'Bonanza Rewards', showBack: true });

    // filter chips
    document.getElementById('bnzFilterBar')?.addEventListener('click', (e) => {
      const btn = (e.target as HTMLElement).closest('[data-filter]') as HTMLElement | null;
      if (!btn) return;
      document.querySelectorAll('.bnz-fc').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      btn.scrollIntoView({ behavior:'smooth', block:'nearest', inline:'center' });
      this.filter = (btn.dataset['filter'] as FilterKey) || 'all';
      this.refreshContent();
    });
  }

  private statusChip(b: BonanzaItem): string {
    const s  = (b.status || '').toLowerCase();
    const ps = (b.processed_status || '').toLowerCase();
    if (ps === 'delivered')  return `<span class="bnz-chip bnz-chip-dlv"><i class="fas fa-check-circle me-1"></i>Delivered</span>`;
    if (ps === 'dispatched') return `<span class="bnz-chip bnz-chip-dlv"><i class="fas fa-truck me-1"></i>Dispatched</span>`;
    if (ps && ps !== 'pending' && !s.includes('progress') && !s.includes('claim') && !s.includes('upcoming') && !s.includes('missed'))
      return `<span class="bnz-chip bnz-chip-clmd"><i class="fas fa-hourglass-half me-1"></i>${esc(b.processed_status)}</span>`;
    if (s.includes('claim now')) return `<span class="bnz-chip bnz-chip-claim"><i class="fas fa-gift me-1"></i>Claim Now!</span>`;
    if (s.includes('achieved')) return `<span class="bnz-chip bnz-chip-ach"><i class="fas fa-trophy me-1"></i>Achieved</span>`;
    if (s.includes('progress')) return `<span class="bnz-chip bnz-chip-prog"><i class="fas fa-spinner fa-spin me-1"></i>In Progress</span>`;
    if (s.includes('upcoming')) return `<span class="bnz-chip bnz-chip-up"><i class="fas fa-calendar me-1"></i>Upcoming</span>`;
    if (s.includes('missed'))   return `<span class="bnz-chip bnz-chip-miss"><i class="fas fa-times-circle me-1"></i>Missed</span>`;
    return `<span class="bnz-chip bnz-chip-prog">${esc(b.status)}</span>`;
  }

  private rewardBadge(b: BonanzaItem): string {
    if (b.reward_type === 'slab_wise' && b.slab_extra_amount) {
      const files = b.current_progress || 1;
      const total = Number(b.slab_extra_amount) * files;
      const perFile = Number(b.slab_extra_amount).toLocaleString('en-IN');
      const lbl = files > 1 ? `${files} files × ₹${perFile}` : 'per deal';
      return `<div class="bnz-rbadge bnz-rbadge-cash"><div class="bnz-rb-amt">+₹${total.toLocaleString('en-IN')}</div><div class="bnz-rb-lbl">${lbl}</div></div>`;
    }
    if (b.is_monetary && b.reward_amount)
      return `<div class="bnz-rbadge bnz-rbadge-cash"><div class="bnz-rb-amt">₹${Number(b.reward_amount).toLocaleString('en-IN')}</div><div class="bnz-rb-lbl">Cash Prize</div></div>`;
    const aName = b.award_name || b.reward_text || 'Free Award';
    const short = aName.length > 16 ? aName.substring(0, 14) + '…' : aName;
    return `<div class="bnz-rbadge bnz-rbadge-free"><div class="bnz-rb-lbl" style="font-size:11px;font-weight:900">FREE</div><div class="bnz-rb-amt" style="font-size:13px">${esc(short)}</div></div>`;
  }

  private filtered(): BonanzaItem[] {
    if (this.filter === 'all') return this.all;
    return this.all.filter(b => {
      const s = b.status || '';
      if (this.filter === 'active')       return s === 'In Progress';
      if (this.filter === 'claim')        return s === 'Achieved - Claim Now';
      if (this.filter === 'won')          return s === 'Achieved - Claim Now' || WON_STATUSES.some(w => s.includes(w));
      if (this.filter === 'claimed_proc') return WON_STATUSES.some(w => s.includes(w));
      if (this.filter === 'upcoming')     return s === 'Upcoming';
      if (this.filter === 'missed')       return s === 'Missed Opportunity';
      if (this.filter === 'inactive')     return s === 'Upcoming' || s === 'Missed Opportunity';
      return false;
    });
  }

  private cardHtml(b: BonanzaItem): string {
    const pct      = b.achievement_percentage || 0;
    const pctColor = pct >= 100 ? '#22c55e' : pct >= 60 ? '#f59e0b' : '#7c3aed';
    const icon     = ICON_MAP[b.criteria_type ?? ''] ?? 'fas fa-trophy';
    const isMissed = (b.status || '').includes('Missed');
    const grad     = bgGrad(b.criteria_type, isMissed);
    const canClaim = b.status === 'Achieved - Claim Now' && !b.slots_full;

    // image banner
    const imgHtml = b.image_url
      ? `<img src="${esc(b.image_url)}" alt="${esc(b.name)}" onerror="this.outerHTML='<div class=\\'bnz-img-ph\\' style=\\'${grad.replace(/'/g,"\\'")}\\'>'+
         '<i class=\\'${icon}\\'></i><span>${esc(b.name)}</span></div>'">`
      : `<div class="bnz-img-ph" style="${grad}"><i class="${icon}"></i><span>${esc(b.name)}</span></div>`;

    // progress — dark bg aware
    const hasTwoTier = b.registered_target_bonus && b.registered_target && b.activated_target;
    let progressHtml = '';
    if (hasTwoTier) {
      const isAct = !!b.partner_is_activated;
      const regPct = !isAct ? pct : Math.min(100, Math.round(((b.current_progress ?? 0) / b.registered_target!) * 100));
      const actPct = isAct ? pct : 0;
      progressHtml = `
        <div class="bnz-tier-row${!isAct?' active':''}">
          <div class="bnz-tier-h">
            <span style="font-size:10px;font-weight:700;color:${!isAct?'#c4b5fd':'#6b7280'}"><i class="fas fa-id-card me-1"></i>Registered${!isAct?' <span style="background:#7c3aed;color:#fff;border-radius:7px;padding:1px 5px;font-size:8px">CURRENT</span>':''}</span>
            <span style="font-size:11px;font-weight:800;color:${!isAct?pctColor:'#6b7280'}">${b.current_progress??0}/${b.registered_target} (${regPct}%)</span>
          </div>
          <div class="bnz-tier-bar"><div style="height:100%;width:${!isAct?pct:regPct}%;background:${pctColor};transition:width .4s"></div></div>
        </div>
        <div class="bnz-tier-row${isAct?' active':''}">
          <div class="bnz-tier-h">
            <span style="font-size:10px;font-weight:700;color:${isAct?'#c4b5fd':'#6b7280'}"><i class="fas fa-bolt me-1"></i>Activated${isAct?' <span style="background:#7c3aed;color:#fff;border-radius:7px;padding:1px 5px;font-size:8px">CURRENT</span>':'<span style="font-size:8px;color:#6b7280"> (activate to unlock)</span>'}</span>
            <span style="font-size:11px;font-weight:800;color:${isAct?pctColor:'#6b7280'}">${isAct?(b.current_progress??0)+'/'+b.activated_target+' ('+actPct+'%)':b.activated_target+' deals'}</span>
          </div>
          ${isAct?`<div class="bnz-tier-bar"><div style="height:100%;width:${pct}%;background:${pctColor};transition:width .4s"></div></div>`:''}
        </div>
        ${!isAct?`<div style="background:rgba(245,158,11,.15);border:1px solid rgba(245,158,11,.3);border-radius:8px;padding:6px 10px;font-size:10px;color:#fcd34d;margin-top:4px"><i class="fas fa-lightbulb me-1"></i>Activate to cut target <strong>${b.registered_target}</strong> → <strong>${b.activated_target}</strong> deals</div>`:''}`;
    } else {
      progressHtml = `
        <div style="display:flex;justify-content:space-between;align-items:center;font-size:12px;font-weight:700;margin-bottom:5px">
          <span style="color:#d1d5db"><i class="fas fa-handshake me-1" style="color:${pctColor}"></i>${b.current_progress??0} / ${b.target_requirement??'—'} deals</span>
          <span style="color:${pctColor};font-size:14px;font-weight:900">${pct}%</span>
        </div>
        <div class="bnz-pb-bg"><div class="bnz-pb-fill" style="width:${pct}%;background:${pctColor}"></div></div>`;
    }

    // DC_BONANZA_AUTOCLAIM_001: rewards are auto-claimed — no manual button needed
    const claimBtn = (b.slots_full && b.status === 'Achieved - Claim Now')
      ? `<div style="text-align:center;background:rgba(220,38,38,.2);border:1px solid rgba(220,38,38,.35);border-radius:9px;padding:10px;font-size:12px;color:#fca5a5;margin-top:10px;font-weight:700"><i class="fas fa-times-circle me-1"></i>All slots filled — contact support</div>`
      : '';

    return `
      <div class="bnz-card${isMissed?' bnz-missed':''}" data-status="${esc(b.status)}">
        <div class="bnz-img">
          ${imgHtml}
          <div class="bnz-sov">${this.statusChip(b)}</div>
          <div class="bnz-rov">${this.rewardBadge(b)}</div>
        </div>
        <div class="bnz-body">
          <div class="bnz-name">${esc(b.name)}</div>
          <div class="bnz-meta">
            ${b.segment_name?`<span class="bnz-seg"><i class="fas fa-tag me-1"></i>${esc(b.segment_name)}</span>`:''}
            <span><i class="fas fa-calendar me-1"></i>${fmtDate(b.start_date)} → ${fmtDate(b.end_date)}</span>
            ${b.grace_days?`<span><i class="fas fa-clock me-1"></i>${b.grace_days}d grace</span>`:''}
          </div>
          <div style="margin-bottom:8px">${progressHtml}</div>
          <div class="bnz-footer">
            <span><i class="fas fa-users me-1"></i>${b.current_winners??0}/${b.max_winners??'—'} winners</span>
            <span><i class="fas fa-ticket-alt me-1"></i>${b.slots_remaining??0} slots left</span>
            ${b.claimed_date?`<span style="color:#34d399"><i class="fas fa-check me-1"></i>Claimed ${fmtDate(b.claimed_date)}</span>`:''}
          </div>
          ${claimBtn}
        </div>
      </div>`;
  }

  private refreshContent(): void {
    const el = document.getElementById('bnzContent');
    if (!el) return;

    if (this.loading) {
      el.innerHTML = `<div style="padding:48px;text-align:center;color:#9ca3af"><i class="fas fa-spinner fa-spin fa-2x"></i></div>`;
      return;
    }
    if (this.error) {
      el.innerHTML = `
        <div style="margin:0 12px;background:#fee2e2;border-radius:12px;padding:14px;color:#991b1b;font-size:13px;display:flex;align-items:center;gap:10px">
          <i class="fas fa-exclamation-circle" style="font-size:18px"></i>
          <div style="flex:1">${this.error}</div>
          <button id="bnzRetry" style="background:#ef4444;color:#fff;border:none;border-radius:8px;padding:6px 12px;font-size:12px;font-weight:700;cursor:pointer">Retry</button>
        </div>`;
      document.getElementById('bnzRetry')?.addEventListener('click', () => this.load(true));
      return;
    }

    const items = this.filtered();
    const filterLabels: Record<string, string> = {
      active:'No active bonanzas right now.', claim:'No bonanzas ready to claim.',
      won:'No won bonanzas yet.', claimed_proc:'No claimed/processed bonanzas yet.',
      upcoming:'No upcoming bonanzas.', missed:'No missed bonanzas.', inactive:'No inactive bonanzas.',
    };

    if (items.length === 0) {
      el.innerHTML = `
        <div style="padding:56px 20px;text-align:center;color:#9ca3af">
          <i class="fas fa-trophy" style="font-size:44px;opacity:.2;display:block;margin-bottom:14px"></i>
          <div style="font-size:15px;font-weight:700;margin-bottom:4px">No bonanzas found</div>
          <div style="font-size:12px">${filterLabels[this.filter] ?? 'No bonanza campaigns match this filter.'}</div>
        </div>`;
      return;
    }

    const refreshBtn = `
      <div style="display:flex;justify-content:flex-end;padding:0 12px 8px">
        <button id="bnzRefresh" style="background:none;border:1.5px solid #ddd6fe;border-radius:8px;padding:6px 12px;font-size:12px;font-weight:700;color:#7c3aed;cursor:pointer">
          <i class="fas fa-sync me-1"></i>Refresh
        </button>
      </div>`;

    // DC_BONANZA_REWARDFILES_001: per-file breakdown table
    let fileSection = '';
    if (this.rewardFiles.length) {
      const ADV_COLORS: Record<string, string> = {
        RELEASED:  'color:#065f46;background:#d1fae5',
        ADJUSTED:  'color:#1e40af;background:#dbeafe',
        RECOVERED: 'color:#991b1b;background:#fee2e2',
        DEFICIT:   'color:#991b1b;background:#fee2e2',
        PENDING:   'color:#854d0e;background:#fef9c3',
      };
      const fileRows = this.rewardFiles.map((f, i) => {
        const adv = ADV_COLORS[f.advance_status] ?? 'color:#374151;background:#f3f4f6';
        const claimBadge = f.processed_status === 'Paid'
          ? `<span style="background:#d1fae5;color:#065f46;border-radius:20px;padding:2px 8px;font-size:10px;font-weight:700"><i class="fas fa-check-circle" style="margin-right:3px"></i>&#x20B9; Paid</span>`
          : f.processed_status === 'Payment Released'
          ? `<span style="background:#dbeafe;color:#1d4ed8;border-radius:20px;padding:2px 8px;font-size:10px;font-weight:700"><i class="fas fa-clock" style="margin-right:3px"></i>Payment Approved</span>`
          : f.processed_status === 'Pending' || !f.processed_status
          ? `<span style="background:#ede9fe;color:#5b21b6;border-radius:20px;padding:2px 8px;font-size:10px;font-weight:700">Pending Approval</span>`
          : `<span style="background:#f3f4f6;color:#374151;border-radius:20px;padding:2px 8px;font-size:10px;font-weight:700">${esc(f.processed_status)}</span>`;
        const reward = f.slab_extra_amount
          ? `<strong style="color:#7c3aed">+&#x20B9;${Number(f.slab_extra_amount).toLocaleString('en-IN')}</strong>`
          : '—';
        const rowBg = i % 2 === 0 ? '#fff' : '#fafaf9';
        return `<div style="background:${rowBg};border-bottom:1px solid #f0f0f0;padding:12px 14px">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px">
            <div style="flex:1;min-width:0">
              <div style="font-size:11px;font-weight:800;color:#4c1d95;margin-bottom:1px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(f.bonanza_name)}</div>
              <div style="font-size:10px;color:#6b7280">${fmtDate(f.bonanza_start)} – ${fmtDate(f.bonanza_end)}</div>
            </div>
            <div style="text-align:right;flex-shrink:0;margin-left:10px">${reward}</div>
          </div>
          <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px">
            <div>
              <div style="font-size:13px;font-weight:600;color:#111">${esc(f.lead_name)}</div>
              <div style="font-size:10px;font-family:monospace;color:#6b7280">${esc(f.entry_number)} &nbsp;·&nbsp; ${fmtDate(f.file_date)}</div>
            </div>
            <div style="display:flex;flex-direction:column;align-items:flex-end;gap:3px">
              <span style="${adv};border-radius:20px;padding:2px 8px;font-size:10px;font-weight:700">${esc(f.advance_status)}</span>
              ${claimBadge}
            </div>
          </div>
          ${f.achieved_date ? `<div style="font-size:10px;color:#16a34a;margin-top:6px"><i class="fas fa-check-circle" style="margin-right:3px"></i>Achieved: ${fmtDate(f.achieved_date)}</div>` : ''}
        </div>`;
      }).join('');

      fileSection = `
        <div style="margin:16px 12px 0;background:#fff;border-radius:14px;border:1.5px solid #ddd6fe;overflow:hidden">
          <div style="padding:12px 14px;background:#faf5ff;border-bottom:1px solid #ede9fe">
            <div style="font-size:13px;font-weight:800;color:#5b21b6"><i class="fas fa-solar-panel" style="margin-right:6px"></i>Solar File Breakdown</div>
            <div style="font-size:11px;color:#7c3aed;margin-top:2px">Each file that qualified for your bonanza reward</div>
          </div>
          ${fileRows}
        </div>`;
    }

    el.innerHTML = refreshBtn + items.map(b => this.cardHtml(b)).join('') + fileSection;
    document.getElementById('bnzRefresh')?.addEventListener('click', () => this.load(true));
  }

  reload(): void { this.load(true); }
}

export default VGKBonanzaRewardsPage;
