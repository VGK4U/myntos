/**
 * Staff Training Videos Page — DC_TRAINING_VIDEOS_001
 * Mobile parity for web /staff/training-videos
 * Mandatory training gate: staff must complete all videos to unlock full access.
 * Completion is detected via YouTube player postMessage (Shorts get manual button).
 */

import { apiService } from '../services/api.service';
import { PageHeader } from '../components/PageHeader';

interface TrainingVideo {
  id: number;
  order_num: number;
  title: string;
  youtube_url: string;
  youtube_video_id: string;
  is_short: boolean;
  is_completed: boolean;
  completed_at: string | null;
}

interface TrainingStatusResponse {
  success: boolean;
  is_gated: boolean;
  is_exempt: boolean;
  grace_active: boolean;
  grace_until: string | null;
  is_complete: boolean;
  completed_count: number;
  total_count: number;
  percent_done: number;
  pending_videos: Array<{ order_num: number; title: string }>;
}

interface VideosResponse {
  success: boolean;
  videos: TrainingVideo[];
  total: number;
  completed: number;
  percent_done: number;
}

export class StaffTrainingVideosPage {
  private container: HTMLElement;
  private videos: TrainingVideo[] = [];
  private status: TrainingStatusResponse | null = null;
  private completedIds: Set<number> = new Set();
  private loading = true;
  private activeIframeListeners: Array<() => void> = [];

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.render();
    await this.loadAll();
    this.attachMessageListener();
  }

  destroy(): void {
    this.activeIframeListeners.forEach(fn => window.removeEventListener('message', fn as any));
    this.activeIframeListeners = [];
  }

  private async loadAll(): Promise<void> {
    try {
      const [statusRes, videosRes] = await Promise.all([
        apiService.get<TrainingStatusResponse>('/staff/training/status'),
        apiService.get<VideosResponse>('/staff/training/videos'),
      ]);
      if (statusRes.success) this.status = (statusRes as unknown) as TrainingStatusResponse;
      if (videosRes.success) {
        this.videos = (videosRes as any).videos || [];
        this.completedIds = new Set(this.videos.filter(v => v.is_completed).map(v => v.id));
      }
    } catch (e) {
      console.error('[StaffTrainingVideos] Load failed:', e);
    }
    this.loading = false;
    this.updateContent();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="page-container training-page">
        ${PageHeader.render({ title: 'Training Videos', showBack: true })}
        <div id="trainingContent" class="training-content">
          <div class="tv-loading"><div class="tv-spinner"></div><span>Loading…</span></div>
        </div>
      </div>
      <style>
        .training-page { background: #f3f4f6; min-height: 100vh; }
        .training-content { padding: 16px; }

        /* Progress banner */
        .tv-progress-card { background: white; border-radius: 14px; padding: 16px 18px; margin-bottom: 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.1); }
        .tv-progress-card h3 { font-size: 15px; font-weight: 700; color: #1f2937; margin: 0 0 12px; }
        .tv-stats { display: flex; gap: 16px; margin-bottom: 12px; }
        .tv-stat { text-align: center; }
        .tv-stat .tv-sv { font-size: 22px; font-weight: 700; color: #1f2937; }
        .tv-stat .tv-sl { font-size: 11px; color: #9ca3af; }
        .tv-stat .tv-sv.done { color: #10b981; }
        .tv-stat .tv-sv.total { color: #3b82f6; }
        .tv-bar-label { display: flex; justify-content: space-between; font-size: 12px; color: #6b7280; margin-bottom: 5px; }
        .tv-bar { height: 8px; border-radius: 4px; background: #e5e7eb; overflow: hidden; }
        .tv-bar-fill { height: 100%; border-radius: 4px; background: #10b981; transition: width 0.4s ease; }
        .tv-badge { display: inline-flex; align-items: center; gap: 6px; border-radius: 20px; padding: 4px 12px; font-size: 12px; font-weight: 600; margin-top: 10px; }
        .tv-badge.grace { background: #fef3c7; color: #92400e; }
        .tv-badge.exempt { background: #d1fae5; color: #065f46; }
        .tv-complete-banner { background: #d1fae5; border: 1px solid #6ee7b7; border-radius: 14px; padding: 16px; margin-bottom: 16px; display: flex; align-items: center; gap: 10px; color: #065f46; font-weight: 600; font-size: 14px; }

        /* Video cards */
        .tv-card { background: white; border-radius: 14px; margin-bottom: 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.1); overflow: hidden; border: 2px solid transparent; }
        .tv-card.done { border-color: #10b981; }
        .tv-card-head { padding: 12px 14px 8px; display: flex; align-items: center; justify-content: space-between; }
        .tv-card-num { background: #eff6ff; color: #2563eb; border-radius: 6px; padding: 2px 8px; font-size: 11px; font-weight: 700; }
        .tv-card-num.done { background: #d1fae5; color: #065f46; }
        .tv-card-status { font-size: 12px; font-weight: 600; display: flex; align-items: center; gap: 5px; }
        .tv-card-status.done { color: #10b981; }
        .tv-card-status.pending { color: #9ca3af; }
        .tv-card-title { padding: 0 14px 10px; font-size: 14px; font-weight: 600; color: #1f2937; line-height: 1.4; }
        .tv-embed-wrap { position: relative; width: 100%; overflow: hidden; background: #000; }
        .tv-embed-wrap.landscape { padding-bottom: 56.25%; }
        .tv-embed-wrap.portrait { padding-bottom: 177.78%; }
        .tv-embed-wrap iframe { position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: none; }
        .tv-card-foot { padding: 10px 14px; border-top: 1px solid #f3f4f6; display: flex; align-items: center; justify-content: space-between; }
        .tv-note { font-size: 11px; color: #9ca3af; display: flex; align-items: center; gap: 4px; }
        .tv-btn-done { padding: 7px 14px; border-radius: 8px; border: none; background: #10b981; color: white; font-size: 12px; font-weight: 600; cursor: pointer; display: flex; align-items: center; gap: 5px; }
        .tv-btn-done:disabled { background: #6ee7b7; }
        .tv-done-label { font-size: 12px; font-weight: 600; color: #10b981; display: flex; align-items: center; gap: 5px; }

        /* Loading */
        .tv-loading { display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 160px; gap: 10px; color: #9ca3af; font-size: 13px; }
        .tv-spinner { width: 28px; height: 28px; border: 3px solid #e5e7eb; border-top-color: #3b82f6; border-radius: 50%; animation: tvSpin 0.8s linear infinite; }
        @keyframes tvSpin { to { transform: rotate(360deg); } }
        .tv-empty { text-align: center; padding: 40px 20px; color: #9ca3af; font-size: 13px; }

        /* Toast */
        .tv-toast { position: fixed; bottom: 90px; left: 50%; transform: translateX(-50%); background: #065f46; color: white; border-radius: 10px; padding: 10px 18px; font-size: 13px; font-weight: 500; z-index: 9999; white-space: nowrap; box-shadow: 0 4px 12px rgba(0,0,0,0.25); animation: tvToastIn 0.3s ease; }
        @keyframes tvToastIn { from { opacity: 0; transform: translateX(-50%) translateY(12px); } to { opacity: 1; transform: translateX(-50%) translateY(0); } }
      </style>
    `;
    PageHeader.attachListeners({ title: 'Training Videos', showBack: true });
  }

  private updateContent(): void {
    const content = this.container.querySelector('#trainingContent') as HTMLElement;
    if (!content) return;
    if (this.loading) {
      content.innerHTML = `<div class="tv-loading"><div class="tv-spinner"></div><span>Loading…</span></div>`;
      return;
    }
    content.innerHTML = this.buildContent();
    this.bindButtons();
  }

  private buildContent(): string {
    const s = this.status;
    let bannerHtml = '';

    if (s?.is_exempt) {
      bannerHtml = `<div class="tv-complete-banner">✅ Training Exempt — full access granted</div>`;
    } else if (s?.is_complete) {
      bannerHtml = `<div class="tv-complete-banner">🎉 All training complete! Full access unlocked.</div>`;
    } else if (s) {
      const color = (s.percent_done >= 80) ? '#10b981' : (s.percent_done >= 40) ? '#f59e0b' : '#3b82f6';
      const graceBadge = s.grace_active
        ? `<div class="tv-badge grace">⏳ Grace period active until ${s.grace_until ? s.grace_until.split('T')[0] : ''}</div>` : '';
      bannerHtml = `
        <div class="tv-progress-card">
          <h3>My Training Progress</h3>
          <div class="tv-stats">
            <div class="tv-stat"><div class="tv-sv done">${s.completed_count}</div><div class="tv-sl">Done</div></div>
            <div class="tv-stat"><div class="tv-sv total">${s.total_count}</div><div class="tv-sl">Total</div></div>
            <div class="tv-stat"><div class="tv-sv">${s.percent_done}%</div><div class="tv-sl">Complete</div></div>
          </div>
          <div class="tv-bar-label"><span>Progress</span><span>${s.percent_done}%</span></div>
          <div class="tv-bar"><div class="tv-bar-fill" style="width:${s.percent_done}%;background:${color};"></div></div>
          ${graceBadge}
        </div>`;
    }

    if (!this.videos.length) {
      return `${bannerHtml}<div class="tv-empty">No training videos found.</div>`;
    }

    const cards = this.videos.map(v => this.buildVideoCard(v)).join('');
    return `${bannerHtml}${cards}`;
  }

  private buildVideoCard(v: TrainingVideo): string {
    const done = this.completedIds.has(v.id);
    const ratio = v.is_short ? 'portrait' : 'landscape';

    // enablejsapi=1 enables postMessage events for completion detection
    const embedSrc = `https://www.youtube.com/embed/${v.youtube_video_id}?rel=0&modestbranding=1&enablejsapi=1&origin=${encodeURIComponent(window.location.origin)}`;

    const footer = done
      ? `<span class="tv-done-label">✅ Completed</span><span></span>`
      : v.is_short
        ? `<span class="tv-note">👆 Watch, then tap done</span>
           <button class="tv-btn-done" id="tvBtn_${v.id}" data-vid="${v.id}">✓ Mark Done</button>`
        : `<span class="tv-note">✨ Also auto-marks on finish</span>
           <button class="tv-btn-done" id="tvBtn_${v.id}" data-vid="${v.id}">✓ Mark Done</button>`;

    return `
      <div class="tv-card ${done ? 'done' : ''}" id="tvCard_${v.id}">
        <div class="tv-card-head">
          <span class="tv-card-num ${done ? 'done' : ''}">#${v.order_num}</span>
          <span class="tv-card-status ${done ? 'done' : 'pending'}">
            ${done ? '✅ Completed' : '⏳ Pending'}
          </span>
        </div>
        <div class="tv-card-title">${this.escHtml(v.title)}</div>
        <div class="tv-embed-wrap ${ratio}">
          <iframe src="${embedSrc}" id="tvIframe_${v.id}"
            data-video-id="${v.id}"
            allowfullscreen
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture">
          </iframe>
        </div>
        <div class="tv-card-foot" id="tvFoot_${v.id}">${footer}</div>
      </div>`;
  }

  private bindButtons(): void {
    this.container.querySelectorAll('.tv-btn-done').forEach(btn => {
      btn.addEventListener('click', () => {
        const vid = parseInt((btn as HTMLElement).dataset.vid || '0');
        if (vid) this.markComplete(vid, true);
      });
    });
  }

  // Listen for YouTube postMessage events (auto-completion for regular videos)
  private attachMessageListener(): void {
    const handler = (event: MessageEvent) => {
      if (!event.data || typeof event.data !== 'string') return;
      try {
        const data = JSON.parse(event.data);
        // YouTube sends {event: "onStateChange", info: 0} when ENDED
        if (data.event === 'onStateChange' && data.info === 0) {
          // Find which iframe sent this message
          const iframes = this.container.querySelectorAll('iframe[data-video-id]');
          iframes.forEach(iframe => {
            if ((iframe as HTMLIFrameElement).contentWindow === event.source) {
              const vid = parseInt((iframe as HTMLElement).dataset.videoId || '0');
              if (vid && !this.completedIds.has(vid)) {
                // Find non-short video (Shorts use manual button)
                const video = this.videos.find(v => v.id === vid);
                if (video && !video.is_short) this.markComplete(vid, false);
              }
            }
          });
        }
      } catch (_) { /* ignore non-JSON messages */ }
    };
    window.addEventListener('message', handler);
    this.activeIframeListeners.push(() => window.removeEventListener('message', handler));
  }

  private async markComplete(videoId: number, isManual: boolean): Promise<void> {
    if (this.completedIds.has(videoId)) return;

    const btn = this.container.querySelector(`#tvBtn_${videoId}`) as HTMLButtonElement | null;
    if (btn) { btn.disabled = true; btn.textContent = '…'; }

    try {
      const res = await apiService.post<any>(`/staff/training/videos/${videoId}/complete`, {});
      if (!res.success) throw new Error((res as any).detail || 'Failed');

      this.completedIds.add(videoId);
      const video = this.videos.find(v => v.id === videoId);
      if (video) video.is_completed = true;

      this.showToast(`✅ "${video?.title || 'Video'}" marked complete!`);

      // Update card visually without full re-render
      const card = this.container.querySelector(`#tvCard_${videoId}`);
      if (card) {
        card.classList.add('done');
        const numBadge = card.querySelector('.tv-card-num');
        if (numBadge) numBadge.classList.add('done');
        const statusEl = card.querySelector('.tv-card-status');
        if (statusEl) { statusEl.className = 'tv-card-status done'; statusEl.textContent = '✅ Completed'; }
        const foot = card.querySelector(`#tvFoot_${videoId}`);
        if (foot) foot.innerHTML = `<span class="tv-done-label">✅ Completed</span><span></span>`;
      }

      // Refresh status
      try {
        const sr = await apiService.get<TrainingStatusResponse>('/staff/training/status');
        if (sr.success) {
          this.status = (sr as unknown) as TrainingStatusResponse;
          // Update progress banner
          const progCard = this.container.querySelector('.tv-progress-card') as HTMLElement;
          if (progCard && this.status) {
            const pct = this.status.percent_done;
            const color = pct >= 80 ? '#10b981' : pct >= 40 ? '#f59e0b' : '#3b82f6';
            const fill = progCard.querySelector('.tv-bar-fill') as HTMLElement;
            if (fill) { fill.style.width = `${pct}%`; fill.style.background = color; }
            const doneEl = progCard.querySelector('.tv-sv.done') as HTMLElement;
            if (doneEl) doneEl.textContent = String(this.status.completed_count);
          }
          if (this.status.is_complete) {
            this.showToast('🎉 All training complete! Unlocking full access…');
            setTimeout(() => (window as any).app?.navigate('dashboard'), 2500);
          }
        }
      } catch (_) { /* status refresh non-critical */ }
    } catch (e) {
      this.showToast('Could not save. Please try again.', true);
      if (btn) { btn.disabled = false; btn.textContent = '✓ Mark Done'; }
    }
  }

  private showToast(msg: string, isError = false): void {
    const existing = document.querySelector('.tv-toast');
    if (existing) existing.remove();
    const el = document.createElement('div');
    el.className = 'tv-toast';
    el.style.background = isError ? '#7f1d1d' : '#065f46';
    el.textContent = msg;
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 3500);
  }

  private escHtml(s: string): string {
    return String(s || '')
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
}
