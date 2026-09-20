/**
 * Authentication Service with Biometric Support
 * DC Protocol: DC_MOBILE_AUTH_001
 * Updated: Uses mobileScheduler for background-safe session monitoring
 */

import { NativeBiometric, BiometryType } from 'capacitor-native-biometric';
import { Preferences } from '@capacitor/preferences';
import { Capacitor } from '@capacitor/core';
import { apiService } from './api.service';
import { PortalType } from './portal.service';
import { mobileScheduler, authLifecycle } from '../runtime';
import { secureStorageService } from './secure-storage.service';
import { APP_CONFIG } from '../config/app.config';

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
          console.log('[DC_AUTH] Restored session access token expired. Checking persistent refresh token...');
          const refreshToken = await secureStorageService.getRefreshToken();
          if (refreshToken) {
            this.authState = restored;
            const refreshed = await this.refreshMobileSession();
            if (refreshed) {
              console.log('[DC_AUTH] Persistent session refreshed successfully on startup');
              return;
            }
            // If refreshMobileSession() already logged out due to 401/403 rejection, state is cleared
            if (!this.authState.isLoggedIn) {
              console.log('[DC_AUTH] Refresh token invalidated by server on cold start');
              return;
            }
            // If failed due to offline/network issue, retain session in offline mode
            console.log('[DC_AUTH] Network offline on startup; retaining session in offline mode');
            return;
          }
          console.log('[DC_AUTH] No valid persistent session, clearing state');
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

  async hasStoredCredentials(portal?: PortalType): Promise<boolean> {
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

  async hasStoredCredentialsForPortal(portal: PortalType): Promise<boolean> {
    return this.hasStoredCredentials(portal);
  }

  async saveCredentialsForBiometric(userId: string, password: string, portal: PortalType = 'staff'): Promise<boolean> {
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

  async getStoredCredentialsForPortal(portal: PortalType): Promise<{ userId: string; password: string } | null> {
    try {
      const { value } = await Preferences.get({ key: BIOMETRIC_CREDENTIALS_BY_PORTAL });
      if (!value) return null;
      const credentials = JSON.parse(value);
      return credentials[portal] || null;
    } catch {
      return null;
    }
  }

  async loginWithBiometricForPortal(portal: PortalType): Promise<{ success: boolean; error?: string }> {
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
    const portal = (portalValue === 'mnr' || portalValue === 'partner' || portalValue === 'staff' || portalValue === 'vgk') 
      ? portalValue as PortalType 
      : 'staff';
    return this.loginWithBiometricForPortal(portal);
  }

  async loginWithPassword(userId: string, password: string, portal: PortalType = 'staff'): Promise<{ success: boolean; error?: string }> {
    try {
      let response;
      
      switch (portal) {
        case 'mnr':
          response = await apiService.mnrLogin(userId, password);
          break;
        case 'partner':
          response = await apiService.partnerLogin(userId, password);
          break;
        case 'vgk':
          response = await apiService.vgkLogin(userId, password);
          break;
        default: {
          let deviceMeta: any = undefined;
          try {
            const deviceId = await secureStorageService.getDeviceId();
            const platform = Capacitor.getPlatform();
            let deviceName = platform;
            try {
              const { Device } = await import('@capacitor/device');
              const info = await Device.getInfo();
              deviceName = `${info.manufacturer || ''} ${info.model || ''}`.trim() || platform;
            } catch {}
            deviceMeta = {
              device_id: deviceId,
              platform,
              device_name: deviceName,
              app_version: APP_CONFIG.getFullVersion()
            };
          } catch (devErr) {
            console.warn('[DC_AUTH] Device metadata extraction error:', devErr);
          }
          response = await apiService.staffLogin(userId, password, deviceMeta);
        }
      }
      
      if (!response.success) {
        return { success: false, error: response.error || 'Login failed' };
      }

      // Store token
      await apiService.setToken(response.data.access_token);

      // Store rotating refresh token in hardware Keystore/Keychain if provided
      if (response.data.refresh_token) {
        await secureStorageService.setRefreshToken(response.data.refresh_token);
      }

      // DC Protocol: Extract user data based on portal type
      // Staff uses 'employee', MNR uses 'user', Partner uses 'partner'
      const userData = response.data.employee || response.data.user || response.data.partner;
      
      // DC Protocol: Extract company_id for X-Company-ID header
      const companyId = userData?.base_company_id || userData?.company_id || userData?.primary_company_id || null;
      if (companyId) {
        await apiService.setCompanyId(companyId);
      }

      // Normalize user data with common fields for Partner and VGK portals
      let normalizedUser = { ...userData, portal, company_id: companyId };
      if ((portal === 'partner' || portal === 'vgk') && response.data.partner) {
        // Partner/VGK-specific: ensure name field is set from partner_name
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

      // Fetch and store menu settings for Staff portal in background
      if (portal === 'staff') {
        this.fetchAndSaveMenuSettings().catch(err => console.warn('[DC_AUTH] Menu settings background fetch error:', err));
      }

      // DC_SESSION_EXPIRY_001: Reset session expired state after successful login
      apiService.resetSessionExpiredFlag();
      
      // Also reset GPS service session expired state
      const { gpsService } = await import('./gps.service');
      gpsService.resetSessionExpiredState();

      // Notify components like SideDrawer that authentication has updated
      window.dispatchEvent(new CustomEvent('auth-changed'));

      return { success: true };
    } catch (error: any) {
      console.error('[DC_AUTH] Password login failed:', error);
      return { success: false, error: error.message || 'Login failed' };
    }
  }

  /**
   * DC_QUICK_LEAD_DIAL: Instantly stores authenticated staff identity from quick lead verification
   * Supports 'always' (persistent Preferences + localStorage) vs 'one_time' (session-only).
   */
  async quickStaffLogin(accessToken: string, employee: any, persistence: string = 'always'): Promise<void> {
    await apiService.setToken(accessToken);
    const companyId = employee?.base_company_id || employee?.company_id || 1;
    await apiService.setCompanyId(companyId);
    const normalizedUser = { ...employee, portal: 'staff', company_id: companyId };
    const sessionHours = persistence === 'always' ? 8760 : 12;
    const tokenExpiresAt = Date.now() + (sessionHours * 3600 * 1000);
    this.authState = {
      isLoggedIn: true,
      isClockedIn: false,
      hasActiveJourney: false,
      user: normalizedUser,
      lastActivity: Date.now(),
      tokenExpiresAt
    };
    if (persistence === 'always') {
      await this.saveAuthState();
      localStorage.setItem('staff_token', accessToken);
      localStorage.setItem('token', accessToken);
      localStorage.setItem('staff_user', JSON.stringify(employee));
    } else {
      sessionStorage.setItem('mnr_auth_state', JSON.stringify(this.authState));
      sessionStorage.setItem('staff_token', accessToken);
      sessionStorage.setItem('token', accessToken);
      sessionStorage.setItem('staff_user', JSON.stringify(employee));
    }
    apiService.resetSessionExpiredFlag();
    window.dispatchEvent(new CustomEvent('auth-changed'));
    window.dispatchEvent(new CustomEvent('login-success'));
  }

  async refreshMobileSession(): Promise<boolean> {
    try {
      const refreshToken = await secureStorageService.getRefreshToken();
      const deviceId = await secureStorageService.getDeviceId();

      if (!refreshToken) {
        console.log('[DC_AUTH] No refresh token available in secure storage, checking biometric fallback');
        return await this.attemptSilentReAuth();
      }

      console.log('[DC_AUTH] Calling /staff/auth/mobile/refresh to rotate token...');
      const response = await apiService.refreshMobileToken(refreshToken, deviceId);

      if (response && response.success && response.data) {
        const { access_token, refresh_token: new_refresh_token, expires_in } = response.data;
        
        // 1. Store rotated one-time refresh token in hardware Keystore / Keychain
        await secureStorageService.setRefreshToken(new_refresh_token);
        
        // 2. Set new short-lived JWT access token
        await apiService.setToken(access_token);
        
        // 3. Update authState
        const tokenExpiresIn = expires_in || 1800;
        this.authState.tokenExpiresAt = Date.now() + (tokenExpiresIn * 1000);
        this.authState.lastActivity = Date.now();
        this.authState.isLoggedIn = true;
        await this.saveAuthState();
        
        // 4. Reset session expired flags
        apiService.resetSessionExpiredFlag();
        
        console.log('[DC_AUTH] Successfully refreshed mobile session and rotated token');
        window.dispatchEvent(new CustomEvent('auth-changed'));
        return true;
      } else {
        const status = response?.status;
        if (status === 401 || status === 403) {
          console.warn(`[DC_AUTH] Refresh token rejected or expired on server (HTTP ${status}):`, response?.error);
          await this.logout();
        } else {
          console.warn(`[DC_AUTH] Mobile session refresh failed due to network/server condition (HTTP ${status || 0}). Session preserved for retry when online.`);
        }
        return false;
      }
    } catch (e) {
      console.error('[DC_AUTH] Exception during mobile session refresh:', e);
      return false;
    }
  }

  async logout(): Promise<void> {
    try {
      const refreshToken = await secureStorageService.getRefreshToken();
      const deviceId = await secureStorageService.getDeviceId();
      if (refreshToken || deviceId) {
        await apiService.revokeMobileToken(refreshToken || undefined, deviceId, false);
      }
      if (deviceId && Capacitor.isNativePlatform()) {
        await apiService.post('/telephony/mobile/push-token/revoke', { device_id: deviceId });
      }
    } catch (e) {
      console.warn('[DC_AUTH] Revoke mobile/push token failed during logout:', e);
    }

    await apiService.clearToken();
    await apiService.clearCompanyId();
    await secureStorageService.clearAll();

    try { localStorage.removeItem('mnr_staff_menu_tree_cache'); } catch (e) {}
    try { localStorage.removeItem('staff_token'); } catch (e) {}
    try { localStorage.removeItem('token'); } catch (e) {}
    try { localStorage.removeItem('staff_user'); } catch (e) {}
    try { sessionStorage.clear(); } catch (e) {}
    
    try {
      if (Capacitor.isNativePlatform()) {
        await NativeBiometric.deleteCredentials({ server: 'myntreal-app' });
        await NativeBiometric.deleteCredentials({ server: 'myntreal-app-staff' });
        await NativeBiometric.deleteCredentials({ server: 'myntreal-app-mnr' });
        await NativeBiometric.deleteCredentials({ server: 'myntreal-app-partner' });
        await NativeBiometric.deleteCredentials({ server: 'myntreal-app-vgk' });
      }
    } catch (e) {
      // Ignore - biometric not available on web
    }
    
    await Preferences.remove({ key: CREDENTIALS_KEY });
    await Preferences.remove({ key: BIOMETRIC_CREDENTIALS_BY_PORTAL });
    await Preferences.remove({ key: BIOMETRIC_PORTAL_KEY });
    await Preferences.remove({ key: AUTH_STATE_KEY });
    
    this.authState = {
      isLoggedIn: false,
      isClockedIn: false,
      hasActiveJourney: false,
      user: null,
      lastActivity: Date.now(),
      tokenExpiresAt: 0
    };
    await this.saveAuthState();
    window.dispatchEvent(new CustomEvent('logout'));
    window.dispatchEvent(new CustomEvent('auth-changed'));
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
        try {
          localStorage.setItem(MENU_SETTINGS_KEY, JSON.stringify(allowedMenus));
          Preferences.set({ 
            key: MENU_SETTINGS_KEY, 
            value: JSON.stringify(allowedMenus) 
          }).catch(() => {});
        } catch (_) {}
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
    if (!this.authState.isLoggedIn) {
      return false;
    }
    if (this.authState.isClockedIn || this.authState.hasActiveJourney) {
      return true;
    }
    // Mobile persistent authentication: session remains valid and short-lived access tokens
    // are automatically renewed via rotating refresh tokens stored in native Keystore/Keychain.
    return true;
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
      const creds = await this.getStoredCredentialsForPortal(portal as PortalType);
      if (!creds) {
        console.log('[DC_AUTH] No stored credentials for silent re-auth');
        return false;
      }
      console.log('[DC_AUTH] Attempting silent re-auth for portal:', portal);
      const result = await this.loginWithPassword(creds.userId, creds.password, portal as PortalType);
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

        // Proactively refresh access token if expired or expiring within 5 minutes (300,000 ms)
        const needsRefresh = this.isTokenExpired() || (this.authState.tokenExpiresAt > 0 && Date.now() >= this.authState.tokenExpiresAt - 300000);
        if (needsRefresh) {
          console.log('[DC_AUTH] Access token needs refresh, attempting proactive refresh...');
          const reAuthed = await this.refreshMobileSession();
          if (!reAuthed && this.isTokenExpired() && !this.authState.isLoggedIn) {
            console.log('[DC_AUTH] Mobile session refresh failed and access token is expired, emitting session-expired');
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

  /**
   * DC Protocol: Checks if current authenticated staff is MR10001 (VGK Mentor / Supreme Admin)
   * MR10001 has unmasked contact visibility across all CRM views and pipelines.
   */
  isMR10001(): boolean {
    try {
      const u = this.authState.user;
      if (u) {
        const code = (u.emp_code || u.employee_code || u.username || '').toString().trim().toUpperCase();
        if (code === 'MR10001' || code.includes('MR10001')) return true;
      }
      const raw = localStorage.getItem('staff_user') || sessionStorage.getItem('staff_user');
      if (raw) {
        const parsed = JSON.parse(raw);
        const code = (parsed.emp_code || parsed.employee_code || parsed.username || '').toString().trim().toUpperCase();
        if (code === 'MR10001' || code.includes('MR10001')) return true;
      }
      const token = localStorage.getItem('staff_token') || sessionStorage.getItem('staff_token');
      if (token && token.includes('.')) {
        const payload = JSON.parse(atob(token.split('.')[1]));
        const code = (payload.emp_code || payload.employee_code || payload.sub || '').toString().trim().toUpperCase();
        if (code === 'MR10001' || code.includes('MR10001')) return true;
      }
    } catch {}
    return false;
  }
}

export const authService = new AuthService();

export function isMR10001Staff(): boolean {
  return authService.isMR10001();
}

export function formatPhoneWithPrivacy(phone?: string | null): string {
  if (!phone || phone.trim() === '' || phone === '—' || phone === 'null') return '—';
  const clean = phone.replace(/[^0-9+]/g, '');
  if (isMR10001Staff()) {
    const digits = clean.replace(/\D/g, '');
    return digits.length === 10 ? `+91 ${digits.slice(0, 5)} ${digits.slice(5)}` : phone;
  }
  if (clean.length <= 4) return '••••';
  const last4 = clean.slice(-4);
  const prefix = clean.length > 8 ? clean.slice(0, 2) : '';
  return `${prefix}••••••${last4}`;
}

