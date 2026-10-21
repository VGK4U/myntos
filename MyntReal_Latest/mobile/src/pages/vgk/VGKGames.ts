/**
 * VGK4U Arcade & Games Page — Mobile App View (DC Protocol Oct 2026)
 * Single application parity: provides native mobile web view for
 * Neon Snake, Block Drop, and Configurable Endless Runner.
 */

import { apiService } from '../../services/api.service';
import { PageHeader } from '../../components/PageHeader';

interface PointsSummary {
  available_balance: number;
}

export class VGKGames {
  private container: HTMLElement;
  private availableBalance: number = 0;
  private loading: boolean = true;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  async init(): Promise<void> {
    this.container.innerHTML = await this.render();
    await this.afterRender();
  }

  async render(): Promise<string> {
    return `
      ${PageHeader.render({ title: 'Arcade & Games', showBack: true })}
      <div class="vgk-arcade-mobile" style="padding: 16px; background: #0c0a1a; min-height: 100vh; color: #fff;">
        
        <!-- POINTS BANNER -->
        <div style="background: linear-gradient(135deg, #1e1b40 0%, #15122b 100%); border: 1px solid rgba(245, 158, 11, 0.3); border-radius: 16px; padding: 16px; margin-bottom: 20px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px;">
          <div>
            <div style="font-size: 11px; font-weight: 700; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px;">VGK Points Balance</div>
            <div id="vgk-pts-val" style="font-size: 22px; font-weight: 900; color: #f59e0b;">${this.availableBalance.toLocaleString()} Pts</div>
            <div style="font-size: 11px; color: #cbd5e1; margin-top: 2px;">1 Point for every 1,000 Score</div>
          </div>
          <a href="/vgk_games.html" style="background: #f59e0b; color: #000; font-weight: 800; font-size: 12px; padding: 8px 16px; border-radius: 50px; text-decoration: none; display: inline-flex; align-items: center; gap: 6px; white-space: nowrap;">
            <i class="fa-solid fa-gamepad"></i> Play Arcade
          </a>
        </div>

        <!-- 3 GAMES PREVIEW CARDS -->
        <div style="display: flex; flex-direction: column; gap: 14px;">
          <!-- 1. Snake -->
          <a href="/vgk_games.html?game=SNAKE" style="text-decoration: none; color: inherit;">
            <div style="background: #15122b; border: 1px solid rgba(168, 85, 247, 0.2); border-radius: 16px; padding: 16px; display: flex; align-items: center; gap: 14px;">
              <div style="width: 48px; height: 48px; border-radius: 12px; background: rgba(245, 158, 11, 0.15); color: #f59e0b; display: flex; align-items: center; justify-content: center; font-size: 22px;">
                <i class="fa-solid fa-worm"></i>
              </div>
              <div style="flex: 1;">
                <div style="font-weight: 800; font-size: 15px; color: #fff;">Golden Snake</div>
                <div style="font-size: 12px; color: #94a3b8;">Eat glowing energy orbs and beat your partner record.</div>
              </div>
              <i class="fa-solid fa-chevron-right" style="color: #64748b; font-size: 12px;"></i>
            </div>
          </a>

          <!-- 2. Block Drop -->
          <a href="/vgk_games.html?game=BLOCK_DROP" style="text-decoration: none; color: inherit;">
            <div style="background: #15122b; border: 1px solid rgba(168, 85, 247, 0.2); border-radius: 16px; padding: 16px; display: flex; align-items: center; gap: 14px;">
              <div style="width: 48px; height: 48px; border-radius: 12px; background: rgba(139, 92, 246, 0.15); color: #c084fc; display: flex; align-items: center; justify-content: center; font-size: 22px;">
                <i class="fa-solid fa-cubes"></i>
              </div>
              <div style="flex: 1;">
                <div style="font-weight: 800; font-size: 15px; color: #fff;">Block Drop</div>
                <div style="font-size: 12px; color: #94a3b8;">Rotate falling blocks, clear full lines, and level up.</div>
              </div>
              <i class="fa-solid fa-chevron-right" style="color: #64748b; font-size: 12px;"></i>
            </div>
          </a>

          <!-- 3. Endless Runner -->
          <a href="/vgk_games.html?game=ENDLESS_RUNNER" style="text-decoration: none; color: inherit;">
            <div style="background: #15122b; border: 1px solid rgba(168, 85, 247, 0.2); border-radius: 16px; padding: 16px; display: flex; align-items: center; gap: 14px;">
              <div style="width: 48px; height: 48px; border-radius: 12px; background: rgba(6, 182, 212, 0.15); color: #06b6d4; display: flex; align-items: center; justify-content: center; font-size: 22px;">
                <i class="fa-solid fa-person-running"></i>
              </div>
              <div style="flex: 1;">
                <div style="font-weight: 800; font-size: 15px; color: #fff;">Endless Runner</div>
                <div style="font-size: 12px; color: #94a3b8;">Choose your hero, double jump obstacles & collect bonanza stars.</div>
              </div>
              <i class="fa-solid fa-chevron-right" style="color: #64748b; font-size: 12px;"></i>
            </div>
          </a>

          <!-- 4. EV Racer -->
          <a href="/vgk_games.html?game=EV_RACER" style="text-decoration: none; color: inherit;">
            <div style="background: #15122b; border: 1px solid rgba(16, 185, 129, 0.28); border-radius: 16px; padding: 16px; display: flex; align-items: center; gap: 14px;">
              <div style="width: 48px; height: 48px; border-radius: 12px; background: rgba(16, 185, 129, 0.15); color: #10b981; display: flex; align-items: center; justify-content: center; font-size: 22px;">
                <i class="fa-solid fa-bolt-lightning"></i>
              </div>
              <div style="flex: 1;">
                <div style="font-weight: 800; font-size: 15px; color: #fff;">EV Racer 3D</div>
                <div style="font-size: 12px; color: #94a3b8;">Drive electric supercar, collect energy cells & hit turbo boost.</div>
              </div>
              <i class="fa-solid fa-chevron-right" style="color: #64748b; font-size: 12px;"></i>
            </div>
          </a>
        </div>

      </div>
    `;
  }

  async afterRender(): Promise<void> {
    try {
      const resp = await apiService.get<any>('/vgk/dashboard/points');
      if (resp && resp.summary) {
        this.availableBalance = resp.summary.available_balance || 0;
        const el = document.getElementById('vgk-pts-val');
        if (el) el.textContent = `${this.availableBalance.toLocaleString()} Pts`;
      }
    } catch (e) {
      console.warn('[VGKGames] Could not fetch points balance:', e);
    }
  }
}
