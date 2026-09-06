/**
 * App Configuration
 * DC Protocol: DC_MOBILE_APP_CONFIG_001
 * Central configuration for app version, build info, and API endpoints
 * SINGLE SOURCE OF TRUTH for all domain/URL configurations
 */

const PRODUCTION_DOMAIN = 'www.myntreal.com';
const DEFAULT_LAN_DEV_URL = 'http://192.168.1.10:5001';

const STORAGE_KEY_DEV_MODE = 'MNR_DEV_MODE';
const STORAGE_KEY_API_OVERRIDE = 'MNR_API_SERVER_OVERRIDE';

function isDevMode(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY_DEV_MODE) === 'true';
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

function getApiServerOverride(): string | null {
  try {
    const override = localStorage.getItem(STORAGE_KEY_API_OVERRIDE);
    return override ? override.trim() : null;
  } catch {
    return null;
  }
}

function getBaseServerUrl(): string {
  // 1. Browser-served mode uses current origin
  if (isBrowserServed()) {
    return window.location.origin;
  }

  // 2. Explicit custom API server override (e.g. set in developer settings)
  const override = getApiServerOverride();
  if (override) {
    return override.replace(/\/+$/, '');
  }

  // 3. In-app Developer/LAN Mode
  if (isDevMode()) {
    const viteEnvUrl = (import.meta as any)?.env?.VITE_API_URL;
    if (viteEnvUrl) return viteEnvUrl.replace(/\/+$/, '');
    return DEFAULT_LAN_DEV_URL;
  }

  // 4. Default Production
  return `https://${PRODUCTION_DOMAIN}`;
}

function getCurrentDomain(): string {
  if (isBrowserServed()) {
    return window.location.host;
  }
  try {
    const url = new URL(getBaseServerUrl());
    return url.host;
  } catch {
    return PRODUCTION_DOMAIN;
  }
}

function getProtocol(): string {
  if (isBrowserServed()) {
    return window.location.protocol.replace(':', '');
  }
  try {
    const url = new URL(getBaseServerUrl());
    return url.protocol.replace(':', '');
  } catch {
    return 'https';
  }
}

function getApiBaseUrl(): string {
  if (isBrowserServed()) {
    return '/api/v1';
  }
  const base = getBaseServerUrl();
  return `${base}/api/v1`;
}

function getMediaBaseUrl(): string {
  if (isBrowserServed()) {
    return '';
  }
  return getBaseServerUrl();
}

function getWsBaseUrl(): string {
  if (isBrowserServed()) {
    const wsProto = window.location.protocol === 'https:' ? 'wss' : 'ws';
    return `${wsProto}://${window.location.host}/ws/v1`;
  }
  const proto = getProtocol() === 'https' ? 'wss' : 'ws';
  return `${proto}://${getCurrentDomain()}/ws/v1`;
}

export const APP_CONFIG = {
  VERSION: '1.0.1',
  BUILD_NUMBER: 1,
  BUILD_DATE: '2026-08-30',
  MIN_SUPPORTED_VERSION: '1.0.0',
  
  get DOMAIN() { return getCurrentDomain(); },
  get BASE_SERVER_URL() { return getBaseServerUrl(); },
  get API_BASE_URL() { return getApiBaseUrl(); },
  get MEDIA_BASE_URL() { return getMediaBaseUrl(); },
  get WS_BASE_URL() { return getWsBaseUrl(); },
  
  isDevMode,
  isNativeApp,
  isBrowserServed,
  getApiServerOverride,
  
  setApiServerOverride(url: string): void {
    try {
      if (!url || !url.trim()) {
        localStorage.removeItem(STORAGE_KEY_API_OVERRIDE);
      } else {
        localStorage.setItem(STORAGE_KEY_API_OVERRIDE, url.trim());
      }
      console.log('[APP_CONFIG] API Server Override set to:', url);
    } catch (e) {
      console.error('[APP_CONFIG] Failed to save API override:', e);
    }
  },

  clearApiServerOverride(): void {
    try {
      localStorage.removeItem(STORAGE_KEY_API_OVERRIDE);
      console.log('[APP_CONFIG] API Server Override cleared.');
    } catch (e) {
      console.error('[APP_CONFIG] Failed to clear API override:', e);
    }
  },
  
  enableDevMode(): void {
    try {
      localStorage.setItem(STORAGE_KEY_DEV_MODE, 'true');
      console.log('[APP_CONFIG] Dev mode ENABLED - Base URL:', getBaseServerUrl());
      window.location.reload();
    } catch (e) {
      console.error('[APP_CONFIG] Failed to enable dev mode:', e);
    }
  },
  
  disableDevMode(): void {
    try {
      localStorage.removeItem(STORAGE_KEY_DEV_MODE);
      console.log('[APP_CONFIG] Dev mode DISABLED - Base URL:', getBaseServerUrl());
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
  
  getServerInfo(): { mode: string; domain: string; baseServerUrl: string; native: boolean; apiBase: string } {
    return {
      mode: isBrowserServed() ? 'BROWSER' : (isDevMode() ? 'LAN_DEV' : 'PRODUCTION'),
      domain: getCurrentDomain(),
      baseServerUrl: getBaseServerUrl(),
      native: isNativeApp(),
      apiBase: getApiBaseUrl()
    };
  },
  
  getVersionString(): string {
    const modeTag = isBrowserServed() ? ' [BROWSER]' : (isDevMode() ? ' [LAN_DEV]' : '');
    return `v${this.VERSION} (Build ${this.BUILD_NUMBER})${modeTag}`;
  },
  
  getFullVersion(): string {
    return `${this.VERSION}+${this.BUILD_NUMBER}`;
  }
};

console.log(`[APP_CONFIG] Mode: ${APP_CONFIG.getServerInfo().mode}, Base Server: ${APP_CONFIG.BASE_SERVER_URL}, Native: ${isNativeApp()}, API: ${APP_CONFIG.API_BASE_URL}`);
