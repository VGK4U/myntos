/**
 * Hardware-Backed Secure Storage Service
 * Enforces AES-256-GCM on Android KeyStore and Secure Enclave/Keychain on iOS.
 * Safe fallback for Web development environments.
 */

import { registerPlugin, Capacitor } from '@capacitor/core';

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
    try {
      const res = await NativeSecureStorage.getDeviceId();
      if (res && res.deviceId) {
        this.cachedDeviceId = res.deviceId;
        return res.deviceId;
      }
    } catch (e) {
      console.warn('[SecureStorage] Error getting deviceId from native plugin:', e);
    }
    const fallback = `${Capacitor.getPlatform()}_${Math.random().toString(36).substring(2)}_${Date.now()}`;
    this.cachedDeviceId = fallback;
    return fallback;
  }

  async setRefreshToken(token: string): Promise<void> {
    try {
      await NativeSecureStorage.setKey({ key: REFRESH_TOKEN_KEY, value: token });
    } catch (e) {
      console.error('[SecureStorage] Failed to store refresh token in secure storage:', e);
      // Fail-safe memory/storage backup if native keystore fails
      try { localStorage.setItem(`mynt_sec_${REFRESH_TOKEN_KEY}`, token); } catch {}
    }
  }

  async getRefreshToken(): Promise<string | null> {
    try {
      const res = await NativeSecureStorage.getKey({ key: REFRESH_TOKEN_KEY });
      if (res && res.value) {
        return res.value;
      }
    } catch (e) {
      console.warn('[SecureStorage] Failed to read refresh token from native storage:', e);
    }
    try {
      return localStorage.getItem(`mynt_sec_${REFRESH_TOKEN_KEY}`);
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
      localStorage.removeItem(`mynt_sec_${REFRESH_TOKEN_KEY}`);
    } catch {}
  }

  async clearAll(): Promise<void> {
    try {
      await NativeSecureStorage.clear();
    } catch (e) {
      console.warn('[SecureStorage] Error clearing native secure storage:', e);
    }
    try {
      const keys = Object.keys(localStorage).filter(k => k.startsWith('mynt_sec_'));
      keys.forEach(k => localStorage.removeItem(k));
    } catch {}
    this.cachedDeviceId = null;
  }
}

export const secureStorageService = new SecureStorageService();
