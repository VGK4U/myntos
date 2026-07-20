/**
 * Authentication Service with Biometric Support
 * DC Protocol: DC_MOBILE_AUTH_001
 * Updated: Uses mobileScheduler for background-safe session monitoring
 */

import { NativeBiometric, BiometryType } from 'capacitor-native-biometric';
import { Preferences } from '@capacitor/preferences';
import { apiService } from './api.service';
import { mobileScheduler, authLifecycle } from '../runtime';

const SCHEDULER_SESSION_ID = 'auth-session-monitor';

interface AuthState {
  isLoggedIn: boolean;
  isClockedIn: boolean;
  hasActiveJourney: boolean;
  user: any;
  lastActivity: number;
  tokenExpiresAt: number;
}

const SESSION_TIMEOUT_MS = 24 * 60 * 60 * 1000; // 24 hours (no 15-min expiry)
const TOKEN_EXPIRY_KEY = 'mnr_token_expires_at';
const CREDENTIALS_KEY = 'mnr_biometric_credentials';
const BIOMETRIC_PORTAL_KEY = 'mnr_biometric_portal';
const BIOMETRIC_CREDENTIALS_BY_PORTAL = 'mnr_biometric_by_portal';
const AUTH_STATE_KEY = 'mnr_auth_state';
const MENU_SETTINGS_KEY = 'mnr_menu_settings';
const OFFLINE_START_KEY = 'mnr_offline_start';

class AuthService {
  private authState: AuthState = {
    isLoggedIn: false,
    isClockedIn: false,
    hasActiveJourney: false,
    user: null,
    lastActivity: Date.now(),
    tokenExpiresAt: 0
  };

  private sessionTimer: any = null;

  async init(): Promise<void> {
    await apiService.init();
    await this.loadAuthState();
    this.startSessionMonitor();
  }

  private async loadAuthState(): Promise<void> {
    try {
      // DC_BRIDGE_READY_001: Read from localStorage first (synchronous, never hangs).
      // Background sync from Preferences handles Preferences-only stored sessions.
      const localValue = localStorage.getItem(AUTH_STATE_KEY);
      let value = localValue;

      if (!value) {
        // No localStorage value — try Preferences (may hang briefly on first cold start)
        try {
          const prefResult = await Promise.race([
            Preferences.get({ key: AUTH_STATE_KEY }),
            new Promise<{ value: null }>(r => setTimeout(() => r({ value: null }), 3000))
          ]);
          value = prefResult.value;
          if (value) localStorage.setItem(AUTH_STATE_KEY, value);
        } catch {
          value = null;
        }
      } else {
        // Has localStorage value — sync Preferences in background
        Preferences.get({ key: AUTH_STATE_KEY }).then(({ value: pv }) => {
          if (pv && !localValue) localStorage.setItem(AUTH_STATE_KEY, pv);
        }).catch(() => {});
      }

      if (value) {
        const restored = JSON.parse(value);
        if (restored.isLoggedIn && restored.tokenExpiresAt > 0 && Date.now() >= restored.tokenExpiresAt) {
          console.log('[DC_AUTH] Restored session has expired token, clearing stale state');
          restored.isLoggedIn = false;
          restored.user = null;
          restored.tokenExpiresAt = 0;
          this.authState = restored;
          await this.saveAuthState();
          await apiService.clearToken();
          return;
        }
        if (restored.isLoggedIn) {
          restored.lastActivity = Date.now();
        }
        this.authState = restored;
      }
    } catch (error) {
      console.error('[DC_AUTH] Failed to load auth state:', error);
    }
  }

  private async saveAuthState(): Promise<void> {
    const serialized = JSON.stringify(this.authState);
    localStorage.setItem(AUTH_STATE_KEY, serialized);
    Preferences.set({ key: AUTH_STATE_KEY, value: serialized }).catch(() => {});
  }

  async checkBiometricAvailability(): Promise<{ available: boolean; type: string }> {
    try {
      const result = await NativeBiometric.isAvailable();
      let biometricName = 'Biometric';
      if (result.biometryType === BiometryType.FACE_ID) {
        biometricName = 'Face ID';
      } else if (result.biometryType === BiometryType.FINGERPRINT) {
        biometricName = 'Fingerprint';
      }
      return {
        available: result.isAvailable,
        type: biometricName
      };
    } catch {
      return { available: false, type: 'None' };
    }
  }

  async hasStoredCredentials(portal?: 'staff' | 'mnr' | 'partner'): Promise<boolean> {
    try {
      const { value } = await Preferences.get({ key: BIOMETRIC_CREDENTIALS_BY_PORTAL });
      if (!value) return false;
      const credentials = JSON.parse(value);
      if (portal) {
        return !!credentials[portal];
      }
      return Object.keys(credentials).length > 0;
    } catch {
      return false;
    }
  }

  async hasStoredCredentialsForPortal(portal: 'staff' | 'mnr' | 'partner'): Promise<boolean> {
    return this.hasStoredCredentials(portal);
  }

  async saveCredentialsForBiometric(userId: string, password: string, portal: 'staff' | 'mnr' | 'partner' = 'staff'): Promise<boolean> {
    try {
      // DC Protocol: Store credentials per portal for multi-login biometric support
      const { value } = await Preferences.get({ key: BIOMETRIC_CREDENTIALS_BY_PORTAL });
      const credentials = value ? JSON.parse(value) : {};
      credentials[portal] = {
        userId,
        password,
        lastUsed: Date.now()
      };
      await Preferences.set({ 
        key: BIOMETRIC_CREDENTIALS_BY_PORTAL, 
        value: JSON.stringify(credentials) 
      });
      
      // Also store in native biometric for current portal
      await NativeBiometric.setCredentials({
        username: userId,
        password: password,
        server: `myntreal-app-${portal}`
      });
      await Preferences.set({ key: CREDENTIALS_KEY, value: 'true' });
      await Preferences.set({ key: BIOMETRIC_PORTAL_KEY, value: portal });
      return true;
    } catch (error) {
      console.error('[DC_AUTH] Failed to save credentials:', error);
      return false;
    }
  }

  async getStoredCredentialsForPortal(portal: 'staff' | 'mnr' | 'partner'): Promise<{ userId: string; password: string } | null> {
    try {
      const { value } = await Preferences.get({ key: BIOMETRIC_CREDENTIALS_BY_PORTAL });
      if (!value) return null;
      const credentials = JSON.parse(value);
      return credentials[portal] || null;
    } catch {
      return null;
    }
  }

  async loginWithBiometricForPortal(portal: 'staff' | 'mnr' | 'partner'): Promise<{ success: boolean; error?: string }> {
    try {
      // DC Protocol: Portal-specific biometric login
      // Verify biometric - throws on failure, returns void on success
      await NativeBiometric.verifyIdentity({
        reason: `Login to MyntReal ${portal.toUpperCase()}`,
        title: 'Biometric Login',
        subtitle: 'Use your fingerprint or face to login',
        description: 'Touch the sensor or look at the camera'
      });

      // Get stored credentials for specific portal
      const storedCreds = await this.getStoredCredentialsForPortal(portal);
      if (!storedCreds) {
        return { success: false, error: `No credentials stored for ${portal} portal. Please login with password first.` };
      }

      // Login with portal-specific credentials
      const result = await this.loginWithPassword(storedCreds.userId, storedCreds.password, portal);
      
      // Ensure menu settings are fetched for staff portal biometric login too
      if (result.success && portal === 'staff') {
        await this.fetchAndSaveMenuSettings();
      }
      
      // DC_SESSION_EXPIRY_001: Reset session expired state after biometric login
      if (result.success) {
        apiService.resetSessionExpiredFlag();
        const { gpsService } = await import('./gps.service');
        gpsService.resetSessionExpiredState();
      }
      
      return result;
    } catch (error: any) {
      console.error('[DC_AUTH] Biometric login failed:', error);
      return { success: false, error: error.message || 'Biometric login failed' };
    }
  }

  async loginWithBiometric(): Promise<{ success: boolean; error?: string }> {
    // Legacy method - uses last used portal
    const { value: portalValue } = await Preferences.get({ key: BIOMETRIC_PORTAL_KEY });
    const portal = (portalValue === 'mnr' || portalValue === 'partner' || portalValue === 'staff') 
      ? portalValue as 'staff' | 'mnr' | 'partner' 
      : 'staff';
    return this.loginWithBiometricForPortal(portal);
  }

  async loginWithPassword(userId: string, password: string, portal: 'staff' | 'mnr' | 'partner' = 'staff'): Promise<{ success: boolean; error?: string }> {
    try {
      let response;
      
      switch (portal) {
        case 'mnr':
          response = await apiService.mnrLogin(userId, password);
          break;
        case 'partner':
          response = await apiService.partnerLogin(userId, password);
          break;
        default:
          response = await apiService.staffLogin(userId, password);
      }
      
      if (!response.success) {
        return { success: false, error: response.error || 'Login failed' };
      }

      // Store token
      await apiService.setToken(response.data.access_token);

      // DC Protocol: Extract user data based on portal type
      // Staff uses 'employee', MNR uses 'user', Partner uses 'partner'
      const userData = response.data.employee || response.data.user || response.data.partner;
      
      // DC Protocol: Extract company_id for X-Company-ID header
      const companyId = userData?.base_company_id || userData?.company_id || userData?.primary_company_id || null;
      if (companyId) {
        await apiService.setCompanyId(companyId);
      }

      // Normalize user data with common fields for Partner portal
      let normalizedUser = { ...userData, portal, company_id: companyId };
      if (portal === 'partner' && response.data.partner) {
        // Partner-specific: ensure name field is set from partner_name
        normalizedUser.name = response.data.partner.partner_name;
        normalizedUser.partner_id = response.data.partner.id;
        normalizedUser.partner_code = response.data.partner.partner_code;
        normalizedUser.partner_name = response.data.partner.partner_name;
        normalizedUser.partner_type = response.data.partner.category;
      }

      const tokenExpiresIn = response.data.expires_in || response.data.token_expires_in || 1800;
      const tokenExpiresAt = Date.now() + (tokenExpiresIn * 1000);

      this.authState = {
        isLoggedIn: true,
        isClockedIn: response.data.is_clocked_in || false,
        hasActiveJourney: response.data.has_active_journey || false,
        user: normalizedUser,
        lastActivity: Date.now(),
        tokenExpiresAt
      };
      await this.saveAuthState();

      // Fetch and store menu settings for Staff portal
      if (portal === 'staff') {
        await this.fetchAndSaveMenuSettings();
      }

      // DC_SESSION_EXPIRY_001: Reset session expired state after successful login
      apiService.resetSessionExpiredFlag();
      
      // Also reset GPS service session expired state
      const { gpsService } = await import('./gps.service');
      gpsService.resetSessionExpiredState();

      return { success: true };
    } catch (error: any) {
      console.error('[DC_AUTH] Password login failed:', error);
      return { success: false, error: error.message || 'Login failed' };
    }
  }

  async logout(): Promise<void> {
    await apiService.clearToken();
    await apiService.clearCompanyId();
    
    try {
      const { Capacitor } = await import('@capacitor/core');
      if (Capacitor.isNativePlatform()) {
        await NativeBiometric.deleteCredentials({ server: 'myntreal-app' });
      }
    } catch (e) {
      // Ignore - biometric not available on web
    }
    
    await Preferences.remove({ key: CREDENTIALS_KEY });
    
    this.authState = {
      isLoggedIn: false,
      isClockedIn: false,
      hasActiveJourney: false,
      user: null,
      lastActivity: Date.now(),
      tokenExpiresAt: 0
    };
    await this.saveAuthState();
  }

  updateActivity(): void {
    this.authState.lastActivity = Date.now();
    this.saveAuthState();
  }

  setClockedIn(value: boolean): void {
    this.authState.isClockedIn = value;
    this.saveAuthState();
  }

  setActiveJourney(value: boolean): void {
    this.authState.hasActiveJourney = value;
    this.saveAuthState();
  }

  getAuthState(): AuthState {
    return this.authState;
  }

  private async fetchAndSaveMenuSettings(): Promise<void> {
    try {
      const response = await apiService.get<any>('/staff/menu-settings/my-menus');
      if (response.success && response.data) {
        const menus = response.data.menus || response.data || [];
        const allowedMenus = menus
          .filter((m: any) => m.is_enabled)
          .map((m: any) => m.menu_key || m.route);
        await Preferences.set({ 
          key: MENU_SETTINGS_KEY, 
          value: JSON.stringify(allowedMenus) 
        });
      }
    } catch (error) {
      console.error('[DC_AUTH] Failed to fetch menu settings:', error);
    }
  }

  async getMenuSettings(): Promise<string[]> {
    try {
      const { value } = await Preferences.get({ key: MENU_SETTINGS_KEY });
      return value ? JSON.parse(value) : [];
    } catch {
      return [];
    }
  }

  async hasMenuAccess(menuKey: string): Promise<boolean> {
    const menus = await this.getMenuSettings();
    // If no menus are set, allow all (default for backwards compatibility)
    if (menus.length === 0) return true;
    return menus.includes(menuKey);
  }

  isSessionValid(): boolean {
    if (this.authState.isClockedIn || this.authState.hasActiveJourney) {
      return true;
    }

    if (this.authState.tokenExpiresAt > 0 && Date.now() >= this.authState.tokenExpiresAt) {
      return false;
    }

    const elapsed = Date.now() - this.authState.lastActivity;
    return elapsed < SESSION_TIMEOUT_MS;
  }

  isTokenExpired(): boolean {
    if (this.authState.tokenExpiresAt <= 0) return false;
    return Date.now() >= this.authState.tokenExpiresAt;
  }

  // DC Protocol: Offline time tracking for attendance
  async markAppClosed(): Promise<void> {
    if (this.authState.isClockedIn) {
      await Preferences.set({
        key: OFFLINE_START_KEY,
        value: JSON.stringify({
          startTime: Date.now(),
          isClockedIn: true,
          hasActiveJourney: this.authState.hasActiveJourney
        })
      });
    }
  }

  async getOfflineTime(): Promise<{ offlineMinutes: number; wasOffline: boolean }> {
    try {
      const { value } = await Preferences.get({ key: OFFLINE_START_KEY });
      if (!value) return { offlineMinutes: 0, wasOffline: false };
      
      const offlineData = JSON.parse(value);
      const offlineMs = Date.now() - offlineData.startTime;
      const offlineMinutes = Math.floor(offlineMs / 60000);
      
      // Clear the offline tracking
      await Preferences.remove({ key: OFFLINE_START_KEY });
      
      return { offlineMinutes, wasOffline: true };
    } catch {
      return { offlineMinutes: 0, wasOffline: false };
    }
  }

  async clearOfflineTracking(): Promise<void> {
    await Preferences.remove({ key: OFFLINE_START_KEY });
  }

  private silentReAuthInProgress: boolean = false;
  private silentReAuthFailCount: number = 0;
  private silentReAuthBackoffUntil: number = 0;

  private async attemptSilentReAuth(): Promise<boolean> {
    if (this.silentReAuthInProgress) return false;
    if (Date.now() < this.silentReAuthBackoffUntil) return false;
    this.silentReAuthInProgress = true;
    try {
      const portal = this.authState.user?.portal || 'staff';
      const creds = await this.getStoredCredentialsForPortal(portal as 'staff' | 'mnr' | 'partner');
      if (!creds) {
        console.log('[DC_AUTH] No stored credentials for silent re-auth');
        return false;
      }
      console.log('[DC_AUTH] Attempting silent re-auth for portal:', portal);
      const result = await this.loginWithPassword(creds.userId, creds.password, portal as 'staff' | 'mnr' | 'partner');
      if (result.success) {
        console.log('[DC_AUTH] Silent re-auth successful');
        this.silentReAuthFailCount = 0;
        this.silentReAuthBackoffUntil = 0;
        apiService.resetSessionExpiredFlag();
        return true;
      }
      this.silentReAuthFailCount++;
      this.silentReAuthBackoffUntil = Date.now() + Math.min(this.silentReAuthFailCount * 60000, 300000);
      console.warn(`[DC_AUTH] Silent re-auth failed (attempt ${this.silentReAuthFailCount}), backoff ${Math.min(this.silentReAuthFailCount, 5)}min:`, result.error);
      return false;
    } catch (e) {
      this.silentReAuthFailCount++;
      this.silentReAuthBackoffUntil = Date.now() + Math.min(this.silentReAuthFailCount * 60000, 300000);
      console.error('[DC_AUTH] Silent re-auth error:', e);
      return false;
    } finally {
      this.silentReAuthInProgress = false;
    }
  }

  private startSessionMonitor(): void {
    mobileScheduler.cancel(SCHEDULER_SESSION_ID);

    mobileScheduler.schedule(
      SCHEDULER_SESSION_ID,
      async () => {
        if (!this.authState.isLoggedIn) return;

        const loginGrace = Date.now() - this.authState.lastActivity < 60000;
        if (loginGrace) return;

        if (this.isTokenExpired()) {
          console.log('[DC_AUTH] JWT token expired, attempting silent re-auth');
          const reAuthed = await this.attemptSilentReAuth();
          if (!reAuthed) {
            console.log('[DC_AUTH] Silent re-auth failed, showing re-auth banner');
            window.dispatchEvent(new CustomEvent('session-expired'));
          }
          return;
        }
      },
      30000,
      { runInBackground: false, immediateOnResume: true }
    );
  }

  stopSessionMonitor(): void {
    mobileScheduler.cancel(SCHEDULER_SESSION_ID);
    this.sessionTimer = null;
  }
}

export const authService = new AuthService();
