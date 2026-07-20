/**
 * Portal Service - Multi-Portal Support
 * DC Protocol: DC_MOBILE_PORTAL_001
 * Manages Staff, MNR, and Partner portal contexts
 */

import { Preferences } from '@capacitor/preferences';

export type PortalType = 'staff' | 'mnr' | 'partner';

interface PortalConfig {
  id: PortalType;
  name: string;
  loginEndpoint: string;
  apiPrefix: string;
  idLabel: string;
  idPlaceholder: string;
  icon: string;
}

class PortalService {
  private currentPortal: PortalType = 'staff';

  readonly portals: Record<PortalType, PortalConfig> = {
    staff: {
      id: 'staff',
      name: 'Staff Portal',
      loginEndpoint: '/staff/auth/login',
      apiPrefix: '/staff',
      idLabel: 'Employee ID',
      idPlaceholder: 'E.G., MR10001',
      icon: 'briefcase'
    },
    mnr: {
      id: 'mnr',
      name: 'MNR Member',
      loginEndpoint: '/auth/login',
      apiPrefix: '/users',
      idLabel: 'MNR ID',
      idPlaceholder: 'E.G., MNR1800001',
      icon: 'users'
    },
    partner: {
      id: 'partner',
      name: 'Partner Portal',
      loginEndpoint: '/partner/auth/login',
      apiPrefix: '/partner',
      idLabel: 'Partner ID',
      idPlaceholder: 'E.G., PT10001',
      icon: 'handshake'
    }
  };

  async init(): Promise<void> {
    // DC_BRIDGE_READY_001: Read from localStorage first (synchronous, never hangs).
    const localVal = localStorage.getItem('current_portal');
    if (localVal && (localVal === 'staff' || localVal === 'mnr' || localVal === 'partner')) {
      this.currentPortal = localVal as PortalType;
      // Sync Preferences in background
      Preferences.get({ key: 'current_portal' }).then(({ value }) => {
        if (value && !localVal) localStorage.setItem('current_portal', value);
      }).catch(() => {});
      return;
    }
    // No localStorage value — try Preferences with 3s timeout
    try {
      const result = await Promise.race([
        Preferences.get({ key: 'current_portal' }),
        new Promise<{ value: null }>(r => setTimeout(() => r({ value: null }), 3000))
      ]);
      if (result.value && (result.value === 'staff' || result.value === 'mnr' || result.value === 'partner')) {
        this.currentPortal = result.value as PortalType;
        localStorage.setItem('current_portal', result.value);
      }
    } catch {
      // Default 'staff' portal is already set
    }
  }

  async setPortal(portal: PortalType): Promise<void> {
    this.currentPortal = portal;
    localStorage.setItem('current_portal', portal);
    Preferences.set({ key: 'current_portal', value: portal }).catch(() => {});
  }

  getPortal(): PortalType {
    return this.currentPortal;
  }

  getConfig(): PortalConfig {
    return this.portals[this.currentPortal];
  }

  getLoginEndpoint(): string {
    return this.portals[this.currentPortal].loginEndpoint;
  }

  getApiPrefix(): string {
    return this.portals[this.currentPortal].apiPrefix;
  }
}

export const portalService = new PortalService();
