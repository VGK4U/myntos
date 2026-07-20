/**
 * App Configuration
 * DC Protocol: DC_MOBILE_APP_CONFIG_001
 * Central configuration for app version, build info, and API endpoints
 * SINGLE SOURCE OF TRUTH for all domain/URL configurations
 *
 * DC Protocol Feb 2026 - Browser Parity Fix:
 * When the mobile SPA is served from a browser (not native Capacitor),
 * use RELATIVE paths so API calls hit the SAME server that served the page.
 * This ensures mobile-in-browser always matches web data.
 */

const PRODUCTION_DOMAIN = 'mnrteam.com';
const DEVELOPMENT_DOMAIN = '5305e65f-c4f9-487a-b990-7fdd5e743de1-00-2fjho41r6u5wb.worf.replit.dev';

function isDevMode(): boolean {
  // Dev mode is ONLY controlled by the in-app Settings toggle (localStorage).
  // Never auto-enable based on build mode — fresh install must always default to production.
  try {
    return localStorage.getItem('MNR_DEV_MODE') === 'true';
  } catch {
    return false;
  }
}

function isNativeApp(): boolean {
  try {
    return !!(window as any).Capacitor?.isNativePlatform?.() ||
           (typeof (window as any).Capacitor !== 'undefined' && (window as any).Capacitor?.getPlatform?.() !== 'web');
  } catch {
    return false;
  }
}

function isBrowserServed(): boolean {
  return !isNativeApp();
}

function getCurrentDomain(): string {
  if (isBrowserServed()) {
    return window.location.host;
  }
  return isDevMode() ? DEVELOPMENT_DOMAIN : PRODUCTION_DOMAIN;
}

function getProtocol(): string {
  if (isBrowserServed()) {
    return window.location.protocol.replace(':', '');
  }
  return 'https';
}

function getApiBaseUrl(): string {
  if (isBrowserServed()) {
    return '/api/v1';
  }
  return `${getProtocol()}://${getCurrentDomain()}/api/v1`;
}

function getMediaBaseUrl(): string {
  if (isBrowserServed()) {
    return '';
  }
  return `${getProtocol()}://${getCurrentDomain()}`;
}

function getWsBaseUrl(): string {
  if (isBrowserServed()) {
    const wsProto = window.location.protocol === 'https:' ? 'wss' : 'ws';
    return `${wsProto}://${window.location.host}/ws/v1`;
  }
  return `wss://${getCurrentDomain()}/ws/v1`;
}

export const APP_CONFIG = {
  VERSION: '1.0.1',
  BUILD_NUMBER: 4,
  BUILD_DATE: '2026-04-05',
  MIN_SUPPORTED_VERSION: '1.0.0',
  
  get DOMAIN() { return getCurrentDomain(); },
  get API_BASE_URL() { return getApiBaseUrl(); },
  get MEDIA_BASE_URL() { return getMediaBaseUrl(); },
  get WS_BASE_URL() { return getWsBaseUrl(); },
  
  isDevMode,
  isNativeApp,
  isBrowserServed,
  
  enableDevMode(): void {
    try {
      localStorage.setItem('MNR_DEV_MODE', 'true');
      console.log('[APP_CONFIG] Dev mode ENABLED - using:', DEVELOPMENT_DOMAIN);
      window.location.reload();
    } catch (e) {
      console.error('[APP_CONFIG] Failed to enable dev mode:', e);
    }
  },
  
  disableDevMode(): void {
    try {
      localStorage.removeItem('MNR_DEV_MODE');
      console.log('[APP_CONFIG] Dev mode DISABLED - using:', PRODUCTION_DOMAIN);
      window.location.reload();
    } catch (e) {
      console.error('[APP_CONFIG] Failed to disable dev mode:', e);
    }
  },
  
  toggleDevMode(): void {
    if (isDevMode()) {
      this.disableDevMode();
    } else {
      this.enableDevMode();
    }
  },
  
  getServerInfo(): { mode: string; domain: string; native: boolean } {
    return {
      mode: isBrowserServed() ? 'BROWSER' : (isDevMode() ? 'DEVELOPMENT' : 'PRODUCTION'),
      domain: getCurrentDomain(),
      native: isNativeApp()
    };
  },
  
  getVersionString(): string {
    const modeTag = isBrowserServed() ? ' [BROWSER]' : (isDevMode() ? ' [DEV]' : '');
    return `v${this.VERSION} (Build ${this.BUILD_NUMBER})${modeTag}`;
  },
  
  getFullVersion(): string {
    return `${this.VERSION}+${this.BUILD_NUMBER}`;
  }
};

console.log(`[APP_CONFIG] Mode: ${APP_CONFIG.getServerInfo().mode}, Domain: ${getCurrentDomain()}, Native: ${isNativeApp()}, API: ${APP_CONFIG.API_BASE_URL}`);
