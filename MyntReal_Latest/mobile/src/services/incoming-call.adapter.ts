/**
 * Canonical Incoming Call Adapter — MyntOS Mobile Telephony
 * Coordinates native lock-screen call events (Android fullScreenIntent & iOS CallKit)
 * with the Capacitor WebRTC softphone engine.
 * Handles push token registration, token rotation, and acceptance bridging.
 */

import { registerPlugin, Capacitor } from '@capacitor/core';
import { apiService } from './api.service';
import { authService } from './auth.service';
import { secureStorageService } from './secure-storage.service';
import { platformAudioAdapter } from './platform-audio.adapter';
import { telephonyService } from './telephony.service';
import { softphoneModal } from '../components/SoftphoneModal';
import { APP_CONFIG } from '../config/app.config';

export interface NativeIncomingCallPlugin {
  getPushToken(): Promise<{ pushToken: string | null; platform: string; tokenType: string; error?: string }>;
  getPendingCall(): Promise<{
    hasPendingCall: boolean;
    sessionId?: string;
    callerPhone?: string;
    callerName?: string;
    providerCallId?: string;
    category?: string;
    leadType?: string;
    city?: string;
    status?: string;
    dealValue?: string;
    leadId?: string;
  }>;
  clearPendingCall(): Promise<{ success: boolean }>;
  dismissCallNotification(): Promise<{ success: boolean }>;
  saveServerConfig(options: { baseUrl: string; authToken?: string }): Promise<{ success: boolean }>;
  triggerTestIncomingCall?(options: {
    callerPhone?: string;
    callerName?: string;
    delaySeconds?: number;
    category?: string;
    leadType?: string;
    city?: string;
    status?: string;
    dealValue?: string;
    leadId?: string;
  }): Promise<{ success: boolean; delay: number }>;
  addListener(
    eventName: 'callAnswered',
    listenerFunc: (data: {
      sessionId: string;
      callerPhone: string;
      callerName: string;
      providerCallId: string;
      category?: string;
      leadType?: string;
      city?: string;
      status?: string;
      dealValue?: string;
      leadId?: string;
    }) => void
  ): Promise<{ remove: () => Promise<void> }>;
  addListener(
    eventName: 'tokenReceived',
    listenerFunc: (data: { token: string }) => void
  ): Promise<{ remove: () => Promise<void> }>;
}

const NativeIncomingCall = registerPlugin<NativeIncomingCallPlugin>('IncomingCall', {
  web: {
    async getPushToken() {
      return { pushToken: null, platform: 'web', tokenType: 'none' };
    },
    async getPendingCall() {
      return { hasPendingCall: false };
    },
    async clearPendingCall() {
      return { success: true };
    },
    async dismissCallNotification() {
      return { success: true };
    },
    async saveServerConfig() {
      return { success: true };
    },
    async triggerTestIncomingCall() {
      return { success: true, delay: 0 };
    },
    async addListener() {
      return { remove: async () => {} };
    }
  }
});

class IncomingCallAdapter {
  private isInitialized: boolean = false;
  private currentPushToken: string | null = null;
  private isSyncInProgress: boolean = false;

  public async init(): Promise<void> {
    if (this.isInitialized) return;
    this.isInitialized = true;

    if (!Capacitor.isNativePlatform()) {
      console.log('[IncomingCallAdapter] Running in web browser; native push bridge disabled.');
      return;
    }

    console.log('[IncomingCallAdapter] Initializing Canonical Incoming Call Adapter...');

    try {
      // 1. Sync server config to native layer (for offline/background decline HTTP requests)
      const token = await apiService.getToken();
      await NativeIncomingCall.saveServerConfig({
        baseUrl: APP_CONFIG.BASE_SERVER_URL,
        authToken: token || undefined
      });

      // 2. Listen for native "callAnswered" event (when user answers from lock-screen or heads-up UI)
      await NativeIncomingCall.addListener('callAnswered', async (data) => {
        console.log('[IncomingCallAdapter] Native callAnswered event received:', data);
        await this.handleIncomingCallAccepted(data);
      });

      // 3. Listen for native "tokenReceived" event (when Firebase/APNs generates or rotates token)
      await NativeIncomingCall.addListener('tokenReceived', async (data) => {
        console.log('[IncomingCallAdapter] Push token received from native:', data?.token);
        if (data?.token) {
          this.currentPushToken = data.token;
          await this.syncPushToken();
        }
      });

      // 4. Check if app was cold-launched from user tapping "Accept" on incoming call screen
      const pending = await NativeIncomingCall.getPendingCall();
      if (pending && pending.hasPendingCall && pending.sessionId) {
        console.log('[IncomingCallAdapter] Found cold-start pending accepted call:', pending);
        await this.handleIncomingCallAccepted({
          sessionId: pending.sessionId,
          callerPhone: pending.callerPhone || '+91 ••••••••••',
          callerName: pending.callerName || 'Incoming Lead',
          providerCallId: pending.providerCallId || '',
          category: pending.category,
          leadType: pending.leadType,
          city: pending.city,
          status: pending.status,
          dealValue: pending.dealValue,
          leadId: pending.leadId
        });
      }

      // 5. If user is already authenticated, synchronize push token now
      if (authService.getAuthState().isLoggedIn) {
        await this.syncPushToken();
      }

      // 6. Bind lifecycle event listeners for login/logout token management
      if (typeof window !== 'undefined') {
        window.addEventListener('login-success', () => {
          this.syncPushToken().catch(err => console.warn('[IncomingCallAdapter] Token sync error on login:', err));
        });
        window.addEventListener('auth-changed', () => {
          if (authService.getAuthState().isLoggedIn) {
            this.syncPushToken().catch(err => console.warn('[IncomingCallAdapter] Token sync error on auth change:', err));
          }
        });
        window.addEventListener('logout', () => {
          this.revokePushToken().catch(err => console.warn('[IncomingCallAdapter] Token revoke error on logout:', err));
        });
      }

      console.log('[IncomingCallAdapter] Canonical Incoming Call Adapter successfully initialized.');
    } catch (err) {
      console.warn('[IncomingCallAdapter] Error during initialization:', err);
    }
  }

  /**
   * Synchronizes hardware push token with backend /api/v1/telephony/mobile/push-token.
   */
  public async syncPushToken(): Promise<boolean> {
    if (!Capacitor.isNativePlatform()) return false;
    if (this.isSyncInProgress) return false;
    this.isSyncInProgress = true;

    try {
      if (!authService.getAuthState().isLoggedIn) {
        console.log('[IncomingCallAdapter] User not logged in, deferring push token registration.');
        this.isSyncInProgress = false;
        return false;
      }

      // 1. Resolve token if not cached
      if (!this.currentPushToken) {
        const tokenRes = await NativeIncomingCall.getPushToken();
        if (tokenRes && tokenRes.pushToken) {
          this.currentPushToken = tokenRes.pushToken;
        }
      }

      if (!this.currentPushToken) {
        console.log('[IncomingCallAdapter] No push token available from native system yet.');
        this.isSyncInProgress = false;
        return false;
      }

      // 2. Resolve persistent device ID
      const deviceId = await secureStorageService.getDeviceId();
      const platform = Capacitor.getPlatform(); // 'android' | 'ios'
      const tokenType = platform === 'ios' ? 'apns_voip' : 'fcm_data';

      console.log(`[IncomingCallAdapter] Registering push token with backend: device=${deviceId}, platform=${platform}, type=${tokenType}`);

      const resp = await apiService.post<any>('/telephony/mobile/push-token', {
        device_id: deviceId,
        platform: platform,
        push_token: this.currentPushToken,
        token_type: tokenType,
        app_version: APP_CONFIG.getFullVersion()
      });

      if (resp && resp.success) {
        console.log('[IncomingCallAdapter] Push token successfully registered on server.');
        this.isSyncInProgress = false;
        return true;
      } else {
        console.warn('[IncomingCallAdapter] Server rejected push token registration:', resp?.error);
        this.isSyncInProgress = false;
        return false;
      }
    } catch (err) {
      console.warn('[IncomingCallAdapter] Exception during push token registration:', err);
      this.isSyncInProgress = false;
      return false;
    }
  }

  /**
   * Revokes push token on server when user logs out.
   */
  public async revokePushToken(): Promise<boolean> {
    if (!Capacitor.isNativePlatform()) return false;
    try {
      const deviceId = await secureStorageService.getDeviceId();
      console.log(`[IncomingCallAdapter] Revoking push token for device: ${deviceId}`);
      const resp = await apiService.post<any>('/telephony/mobile/push-token/revoke', {
        device_id: deviceId
      });
      this.currentPushToken = null;
      return resp?.success === true;
    } catch (err) {
      console.warn('[IncomingCallAdapter] Error revoking push token:', err);
      return false;
    }
  }

  /**
   * Authoritative handler when incoming call is accepted from native screen.
   * Bridges into the frozen telephony engine without modifying frozen files.
   */
  public async handleIncomingCallAccepted(callData: {
    sessionId: string;
    callerPhone: string;
    callerName: string;
    providerCallId: string;
    category?: string;
    leadType?: string;
    city?: string;
    status?: string;
    dealValue?: string;
    leadId?: string;
  }): Promise<void> {
    console.log('[IncomingCallAdapter] Executing incoming call acceptance bridge:', callData);

    // 1. MANDATE 1: User-Gesture Audio Unlock
    platformAudioAdapter.unlockAudio();

    // 2. Pre-initialize Plivo WebRTC client
    try {
      await telephonyService.initPlivoWebRTC();
    } catch (err) {
      console.warn('[IncomingCallAdapter] WebRTC init notice during answer:', err);
    }

    // 3. Connect incoming call via frozen telephony service
    telephonyService.answerIncomingCall();

    // 4. Open Central Softphone Modal to display active floating call UI
    try {
      softphoneModal.open({
        phoneNumber: callData.callerPhone || '+91 ••••••••••',
        name: (callData.callerName || 'Incoming Lead').trim(),
        entityType: 'lead',
        entityId: callData.leadId,
        categoryName: callData.category,
        status: callData.status,
        source: 'incoming_lockscreen',
        autoStart: false
      });
    } catch (modalErr) {
      console.warn('[IncomingCallAdapter] Error opening softphone modal for incoming call:', modalErr);
    }
  }

  /**
   * Triggers a native CallKit / Android incoming call test with configurable countdown delay.
   * Enables the user to lock their screen and verify the incoming call UI presentation.
   */
  public async triggerTestCall(
    callerPhone: string = '+919876543210',
    callerName: string = 'Rajesh Sharma',
    delaySeconds: number = 3.0,
    category: string = 'Solar',
    leadType: string = '5kW Residential Rooftop',
    city: string = 'Hyderabad'
  ): Promise<boolean> {
    try {
      if (NativeIncomingCall.triggerTestIncomingCall) {
        await NativeIncomingCall.triggerTestIncomingCall({
          callerPhone,
          callerName,
          delaySeconds,
          category,
          leadType,
          city
        });
        return true;
      }
    } catch (e) {
      console.warn('[IncomingCallAdapter] Test call trigger error:', e);
    }
    return false;
  }
}

export const incomingCallAdapter = new IncomingCallAdapter();
