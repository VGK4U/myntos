/**
 * Mobile Runtime Compatibility Layer - Auth Lifecycle
 * DC Protocol: DC_RUNTIME_AUTH_001
 * 
 * Handles token refresh on app resume, expiry detection,
 * and proper auth state management across app lifecycle.
 */

import { App, AppState } from '@capacitor/app';
import { Preferences } from '@capacitor/preferences';

interface AuthToken {
  token: string;
  expiresAt: number;
  refreshToken?: string;
}

interface AuthLifecycleOptions {
  tokenKey?: string;
  refreshThresholdMs?: number;
  onTokenExpired?: () => void;
  onTokenRefreshed?: (token: string) => void;
  onAuthError?: (error: Error) => void;
  refreshEndpoint?: string;
}

const DEFAULT_OPTIONS: Required<Omit<AuthLifecycleOptions, 'onTokenExpired' | 'onTokenRefreshed' | 'onAuthError'>> = {
  tokenKey: 'auth_token',
  refreshThresholdMs: 5 * 60 * 1000,
  refreshEndpoint: '/auth/refresh'
};

class AuthLifecycle {
  private options: Required<Omit<AuthLifecycleOptions, 'onTokenExpired' | 'onTokenRefreshed' | 'onAuthError'>> & 
                   Pick<AuthLifecycleOptions, 'onTokenExpired' | 'onTokenRefreshed' | 'onAuthError'>;
  private appStateListenerHandle: any = null;
  private tokenCheckTimer: any = null;
  private lastResumeTime: number = 0;
  private initialized: boolean = false;
  private tokenExpiresAt: number = 0;

  constructor() {
    this.options = { ...DEFAULT_OPTIONS };
  }

  async init(options: AuthLifecycleOptions = {}): Promise<void> {
    if (this.initialized) return;

    this.options = { ...DEFAULT_OPTIONS, ...options };

    this.appStateListenerHandle = await App.addListener('appStateChange', (state: AppState) => {
      if (state.isActive) {
        this.handleAppResume();
      }
    });

    await this.loadTokenExpiry();

    this.initialized = true;
    console.log('[DC_AUTH_LIFECYCLE] Initialized');
  }

  private async loadTokenExpiry(): Promise<void> {
    try {
      const { value } = await Preferences.get({ key: `${this.options.tokenKey}_expires_at` });
      if (value) {
        this.tokenExpiresAt = parseInt(value, 10);
      }
    } catch (e) {
      console.error('[DC_AUTH_LIFECYCLE] Failed to load token expiry:', e);
    }
  }

  async setTokenExpiry(expiresAt: number): Promise<void> {
    this.tokenExpiresAt = expiresAt;
    await Preferences.set({ 
      key: `${this.options.tokenKey}_expires_at`, 
      value: expiresAt.toString() 
    });
  }

  async setTokenFromResponse(token: string, expiresInSeconds?: number): Promise<void> {
    await Preferences.set({ key: this.options.tokenKey, value: token });
    
    if (expiresInSeconds) {
      const expiresAt = Date.now() + (expiresInSeconds * 1000);
      await this.setTokenExpiry(expiresAt);
    }

    if (this.options.onTokenRefreshed) {
      this.options.onTokenRefreshed(token);
    }
  }

  private async handleAppResume(): Promise<void> {
    const now = Date.now();
    const timeSinceLastResume = now - this.lastResumeTime;
    this.lastResumeTime = now;

    if (timeSinceLastResume < 1000) return;

    console.log('[DC_AUTH_LIFECYCLE] App resumed, checking auth state');

    const tokenStatus = await this.checkTokenStatus();

    if (tokenStatus === 'expired') {
      console.log('[DC_AUTH_LIFECYCLE] Token expired during background');
      if (this.options.onTokenExpired) {
        this.options.onTokenExpired();
      }
      window.dispatchEvent(new CustomEvent('auth-token-expired'));
    } else if (tokenStatus === 'expiring_soon') {
      console.log('[DC_AUTH_LIFECYCLE] Token expiring soon, attempting refresh');
      await this.attemptTokenRefresh();
    }
  }

  async checkTokenStatus(): Promise<'valid' | 'expiring_soon' | 'expired' | 'no_token'> {
    const { value: token } = await Preferences.get({ key: this.options.tokenKey });
    
    if (!token) {
      return 'no_token';
    }

    if (this.tokenExpiresAt === 0) {
      return 'valid';
    }

    const now = Date.now();
    
    if (now >= this.tokenExpiresAt) {
      return 'expired';
    }

    if (now >= this.tokenExpiresAt - this.options.refreshThresholdMs) {
      return 'expiring_soon';
    }

    return 'valid';
  }

  async attemptTokenRefresh(): Promise<boolean> {
    try {
      const { value: token } = await Preferences.get({ key: this.options.tokenKey });
      if (!token) return false;

      const response = await fetch(this.options.refreshEndpoint, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error(`Refresh failed: ${response.status}`);
      }

      const data = await response.json();
      
      if (data.token || data.access_token) {
        const newToken = data.token || data.access_token;
        const expiresIn = data.expires_in || 3600;
        await this.setTokenFromResponse(newToken, expiresIn);
        console.log('[DC_AUTH_LIFECYCLE] Token refreshed successfully');
        return true;
      }

      return false;
    } catch (error) {
      console.error('[DC_AUTH_LIFECYCLE] Token refresh failed:', error);
      if (this.options.onAuthError) {
        this.options.onAuthError(error as Error);
      }
      return false;
    }
  }

  getTimeUntilExpiry(): number {
    if (this.tokenExpiresAt === 0) return Infinity;
    return Math.max(0, this.tokenExpiresAt - Date.now());
  }

  isTokenExpiringSoon(): boolean {
    if (this.tokenExpiresAt === 0) return false;
    return Date.now() >= this.tokenExpiresAt - this.options.refreshThresholdMs;
  }

  async clearAuth(): Promise<void> {
    await Preferences.remove({ key: this.options.tokenKey });
    await Preferences.remove({ key: `${this.options.tokenKey}_expires_at` });
    this.tokenExpiresAt = 0;
    console.log('[DC_AUTH_LIFECYCLE] Auth cleared');
  }

  async cleanup(): Promise<void> {
    if (this.appStateListenerHandle) {
      await this.appStateListenerHandle.remove();
      this.appStateListenerHandle = null;
    }
    if (this.tokenCheckTimer) {
      clearInterval(this.tokenCheckTimer);
      this.tokenCheckTimer = null;
    }
    this.initialized = false;
    console.log('[DC_AUTH_LIFECYCLE] Cleanup complete');
  }
}

export const authLifecycle = new AuthLifecycle();
