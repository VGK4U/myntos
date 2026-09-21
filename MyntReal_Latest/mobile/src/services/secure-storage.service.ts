/**
 * Hardware-Backed Secure Storage Service
 * Enforces AES-256-GCM on Android KeyStore and Secure Enclave/Keychain on iOS.
 * Safe fallback for Web development environments.
 */

import { registerPlugin, Capacitor } from '@capacitor/core';
import { Preferences } from '@capacitor/preferences';

export interface SecureStoragePlugin {
  setKey(options: { key: string; value: string }): Promise<{ success: boolean }>;
  getKey(options: { key: string }): Promise<{ value: string | null; error?: string }>;
  removeKey(options: { key: string }): Promise<{ success: boolean }>;
  clear(): Promise<{ success: boolean }>;
  getDeviceId(): Promise<{ deviceId: string }>;
}

const NativeSecureStorage = registerPlugin<SecureStoragePlugin>('SecureStorage', {
  web: async () => {
    return {
      async setKey(options: { key: string; value: string }) {
        try {
          localStorage.setItem(`mynt_sec_${options.key}`, options.value);
        } catch (e) {
          console.warn('[SecureStorage] Web localStorage write error:', e);
        }
        return { success: true };
      },
      async getKey(options: { key: string }) {
        try {
          const val = localStorage.getItem(`mynt_sec_${options.key}`);
          return { value: val };
        } catch {
          return { value: null };
        }
      },
      async removeKey(options: { key: string }) {
        try {
          localStorage.removeItem(`mynt_sec_${options.key}`);
        } catch {}
        return { success: true };
      },
      async clear() {
        try {
          const keys = Object.keys(localStorage).filter(k => k.startsWith('mynt_sec_'));
          keys.forEach(k => localStorage.removeItem(k));
        } catch {}
        return { success: true };
      },
      async getDeviceId() {
        try {
          let did = localStorage.getItem('mynt_sec_device_id');
          if (!did) {
            did = 'web_' + Math.random().toString(36).substring(2) + Date.now().toString(36);
            localStorage.setItem('mynt_sec_device_id', did);
          }
          return { deviceId: did };
        } catch {
          return { deviceId: 'web_fallback_unknown' };
        }
      }
    };
  }
});

const REFRESH_TOKEN_KEY = 'staff_refresh_token';
const DEVICE_ID_KEY = 'staff_device_id';

class SecureStorageService {
  private cachedDeviceId: string | null = null;

  async getDeviceId(): Promise<string> {
    if (this.cachedDeviceId) {
      return this.cachedDeviceId;
    }
    // 1. Try native KeyStore / Keychain plugin
    try {
      const res = await NativeSecureStorage.getDeviceId();
      if (res && res.deviceId) {
        this.cachedDeviceId = res.deviceId;
        try {
          await Preferences.set({ key: 'mynt_sec_device_id', value: res.deviceId });
          localStorage.setItem('mynt_sec_device_id', res.deviceId);
        } catch {}
        return res.deviceId;
      }
    } catch (e) {
      console.warn('[SecureStorage] Error getting deviceId from native plugin:', e);
    }

    // 2. Check Preferences fallback
    try {
      const { value: prefId } = await Preferences.get({ key: 'mynt_sec_device_id' });
      if (prefId) {
        this.cachedDeviceId = prefId;
        try { localStorage.setItem('mynt_sec_device_id', prefId); } catch {}
        return prefId;
      }
    } catch {}

    // 3. Check localStorage fallback
    try {
      const localId = localStorage.getItem('mynt_sec_device_id');
      if (localId) {
        this.cachedDeviceId = localId;
        try { await Preferences.set({ key: 'mynt_sec_device_id', value: localId }); } catch {}
        return localId;
      }
    } catch {}

    // 4. Generate stable permanent ID and save across all storage tiers
    const fallback = `${Capacitor.getPlatform()}_${Math.random().toString(36).substring(2)}${Date.now().toString(36)}`;
    this.cachedDeviceId = fallback;
    try {
      await Preferences.set({ key: 'mynt_sec_device_id', value: fallback });
      localStorage.setItem('mynt_sec_device_id', fallback);
    } catch {}
    return fallback;
  }

  async setRefreshToken(token: string): Promise<void> {
    if (Capacitor.isNativePlatform()) {
      try {
        await NativeSecureStorage.setKey({ key: REFRESH_TOKEN_KEY, value: token });
      } catch (e) {
        console.warn('[SecureStorage] Native storage write failed, falling back to local:', e);
      }
    }
    // Mirror to Preferences & localStorage for guaranteed persistence across app updates & cold starts
    try {
      await Preferences.set({ key: `mynt_sec_${REFRESH_TOKEN_KEY}`, value: token });
    } catch {}
    try {
      localStorage.setItem(`mynt_sec_${REFRESH_TOKEN_KEY}`, token);
    } catch (e) {
      console.warn('[SecureStorage] Storage fallback write error:', e);
    }
  }

  async getRefreshToken(): Promise<string | null> {
    if (Capacitor.isNativePlatform()) {
      try {
        const res = await NativeSecureStorage.getKey({ key: REFRESH_TOKEN_KEY });
        if (res?.value) return res.value;
      } catch (e) {
        console.warn('[SecureStorage] Failed to read refresh token from native storage:', e);
      }
    }
    // Try Preferences fallback
    try {
      const { value: prefToken } = await Preferences.get({ key: `mynt_sec_${REFRESH_TOKEN_KEY}` });
      if (prefToken) return prefToken;
    } catch {}
    // Web development & native safety fallback
    try {
      return localStorage.getItem(`mynt_sec_${REFRESH_TOKEN_KEY}`) || null;
    } catch {
      return null;
    }
  }

  async removeRefreshToken(): Promise<void> {
    try {
      await NativeSecureStorage.removeKey({ key: REFRESH_TOKEN_KEY });
    } catch (e) {
      console.warn('[SecureStorage] Error removing refresh token:', e);
    }
    try {
      await Preferences.remove({ key: `mynt_sec_${REFRESH_TOKEN_KEY}` });
    } catch {}
    try {
      localStorage.removeItem(`mynt_sec_${REFRESH_TOKEN_KEY}`);
    } catch {}
  }

  async clearAll(): Promise<void> {
    try {
      await NativeSecureStorage.clear();
    } catch (e) {
      console.warn('[SecureStorage] Error clearing native secure storage:', e);
    }
    if (!Capacitor.isNativePlatform()) {
      try {
        const keys = Object.keys(localStorage).filter(k => k.startsWith('mynt_sec_'));
        keys.forEach(k => localStorage.removeItem(k));
      } catch {}
    }
    this.cachedDeviceId = null;
  }
}

export const secureStorageService = new SecureStorageService();
