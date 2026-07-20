/**
 * Mobile Runtime Compatibility Layer - Permissions & Lifecycle Guards
 * DC Protocol: DC_RUNTIME_PERMISSIONS_001
 * 
 * Centralized permission checking with graceful fallbacks
 * and proper lifecycle state management.
 * 
 * One-time permission request at startup for ALL permissions:
 * Camera, Location, Storage/Audio, Call Log, Phone State
 */

import { Camera, CameraPermissionType } from '@capacitor/camera';
import { Geolocation } from '@capacitor/geolocation';
import { App, AppState } from '@capacitor/app';

type PermissionType = 'camera' | 'location' | 'photos' | 'callLog' | 'storage' | 'phoneState' | 'contacts';
type PermissionStatus = 'granted' | 'denied' | 'prompt' | 'unknown';

interface PermissionState {
  camera: PermissionStatus;
  location: PermissionStatus;
  photos: PermissionStatus;
  callLog: PermissionStatus;
  storage: PermissionStatus;
  phoneState: PermissionStatus;
  contacts: PermissionStatus;
  lastChecked: number;
}

interface LifecycleState {
  isActive: boolean;
  lastActiveTime: number;
  lastBackgroundTime: number;
  resumeCount: number;
}

type LifecycleCallback = (isActive: boolean, timeSinceLastState: number) => void;

class PermissionsRuntime {
  private permissions: PermissionState = {
    camera: 'unknown',
    location: 'unknown',
    photos: 'unknown',
    callLog: 'unknown',
    storage: 'unknown',
    phoneState: 'unknown',
    contacts: 'unknown',
    lastChecked: 0
  };

  private lifecycle: LifecycleState = {
    isActive: true,
    lastActiveTime: Date.now(),
    lastBackgroundTime: 0,
    resumeCount: 0
  };

  private appStateListenerHandle: any = null;
  private lifecycleCallbacks: Set<LifecycleCallback> = new Set();
  private initialized: boolean = false;

  async init(): Promise<void> {
    if (this.initialized) return;

    this.appStateListenerHandle = await App.addListener('appStateChange', (state: AppState) => {
      this.handleAppStateChange(state.isActive);
    });

    await this.checkAllPermissions();

    this.initialized = true;
    console.log('[DC_PERMISSIONS] Initialized');
  }

  private handleAppStateChange(isActive: boolean): void {
    const now = Date.now();
    let timeSinceLastState: number;

    if (isActive) {
      timeSinceLastState = now - this.lifecycle.lastBackgroundTime;
      this.lifecycle.lastActiveTime = now;
      this.lifecycle.resumeCount++;
    } else {
      timeSinceLastState = now - this.lifecycle.lastActiveTime;
      this.lifecycle.lastBackgroundTime = now;
    }

    this.lifecycle.isActive = isActive;

    this.lifecycleCallbacks.forEach(callback => {
      try {
        callback(isActive, timeSinceLastState);
      } catch (e) {
        console.error('[DC_PERMISSIONS] Lifecycle callback error:', e);
      }
    });
  }

  onLifecycleChange(callback: LifecycleCallback): () => void {
    this.lifecycleCallbacks.add(callback);
    return () => this.lifecycleCallbacks.delete(callback);
  }

  isAppActive(): boolean {
    return this.lifecycle.isActive;
  }

  getTimeSinceLastActive(): number {
    if (this.lifecycle.isActive) return 0;
    return Date.now() - this.lifecycle.lastActiveTime;
  }

  getResumeCount(): number {
    return this.lifecycle.resumeCount;
  }

  async checkAllPermissions(): Promise<PermissionState> {
    const [cameraStatus, locationStatus] = await Promise.all([
      this.checkCameraPermission(),
      this.checkLocationPermission()
    ]);

    const nativeStatus = await this.checkNativePermissions();

    this.permissions = {
      camera: cameraStatus,
      location: locationStatus,
      photos: cameraStatus,
      callLog: nativeStatus.callLog,
      storage: nativeStatus.storage,
      phoneState: nativeStatus.phoneState,
      contacts: nativeStatus.contacts,
      lastChecked: Date.now()
    };

    return this.permissions;
  }

  private async checkCameraPermission(): Promise<PermissionStatus> {
    try {
      const result = await Camera.checkPermissions();
      return this.normalizeStatus(result.camera);
    } catch (e) {
      console.error('[DC_PERMISSIONS] Camera check failed:', e);
      return 'unknown';
    }
  }

  private async checkLocationPermission(): Promise<PermissionStatus> {
    try {
      const result = await Geolocation.checkPermissions();
      return this.normalizeStatus(result.location);
    } catch (e) {
      console.error('[DC_PERMISSIONS] Location check failed:', e);
      return 'unknown';
    }
  }

  private async checkNativePermissions(): Promise<{ callLog: PermissionStatus; storage: PermissionStatus; phoneState: PermissionStatus; contacts: PermissionStatus }> {
    const result = { callLog: 'unknown' as PermissionStatus, storage: 'unknown' as PermissionStatus, phoneState: 'unknown' as PermissionStatus, contacts: 'unknown' as PermissionStatus };
    try {
      const Capacitor = (window as any).Capacitor;
      if (Capacitor && Capacitor.isNativePlatform?.()) {
        const nativePerms = Capacitor.Plugins?.MyntPermissions;
        if (nativePerms) {
          try {
            const status = await nativePerms.checkPermissions();
            result.callLog = status.callLog === true ? 'granted' : (status.callLog === false ? 'denied' : 'prompt');
            result.storage = status.storage === true ? 'granted' : (status.storage === false ? 'denied' : 'prompt');
            result.phoneState = status.phoneState === true ? 'granted' : (status.phoneState === false ? 'denied' : 'prompt');
            result.contacts = status.contacts === true ? 'granted' : (status.contacts === false ? 'denied' : 'prompt');
            return result;
          } catch (_) {}
        }

        const contactsPlugin = Capacitor.Plugins?.MyntContacts;
        if (contactsPlugin) {
          try {
            const cStatus = await contactsPlugin.checkPermissions();
            result.contacts = cStatus?.contacts === 'granted' ? 'granted' : (cStatus?.contacts === 'denied' ? 'denied' : 'prompt');
          } catch (_) {
            result.contacts = 'unknown';
          }
        }
      }

      if (typeof (window as any).cordova !== 'undefined') {
        const permissions = (window as any).cordova.plugins?.permissions;
        if (permissions) {
          result.callLog = await this.checkCordovaPermission(permissions, 'READ_CALL_LOG');
          result.phoneState = await this.checkCordovaPermission(permissions, 'READ_PHONE_STATE');
          result.contacts = await this.checkCordovaPermission(permissions, 'READ_CONTACTS');

          const androidVersion = this.getAndroidVersion();
          if (androidVersion >= 13) {
            const audioStatus = await this.checkCordovaPermission(permissions, 'READ_MEDIA_AUDIO');
            const imagesStatus = await this.checkCordovaPermission(permissions, 'READ_MEDIA_IMAGES');
            result.storage = (audioStatus === 'granted' || imagesStatus === 'granted') ? 'granted' : audioStatus;
          } else {
            result.storage = await this.checkCordovaPermission(permissions, 'READ_EXTERNAL_STORAGE');
          }
          return result;
        }
      }

      if (typeof (window as any).Capacitor !== 'undefined' && (window as any).Capacitor.isNativePlatform?.()) {
        result.callLog = 'granted';
        result.storage = 'granted';
        result.phoneState = 'granted';
        result.contacts = 'granted';
        console.log('[DC_PERMISSIONS] Native platform detected but no permission plugin — assuming granted (OS-level permissions apply)');
      }
    } catch (e) {
      console.warn('[DC_PERMISSIONS] Native permission check skipped:', e);
    }
    return result;
  }

  private checkCordovaPermission(permissions: any, permission: string): Promise<PermissionStatus> {
    return new Promise((resolve) => {
      permissions.checkPermission(
        permissions[permission],
        (status: any) => resolve(status.hasPermission ? 'granted' : 'prompt'),
        () => resolve('unknown')
      );
    });
  }

  private normalizeStatus(status: string): PermissionStatus {
    switch (status) {
      case 'granted':
        return 'granted';
      case 'denied':
        return 'denied';
      case 'prompt':
      case 'prompt-with-rationale':
        return 'prompt';
      default:
        return 'unknown';
    }
  }

  async requestPermission(type: PermissionType): Promise<PermissionStatus> {
    try {
      let status: PermissionStatus;

      switch (type) {
        case 'camera':
        case 'photos':
          const cameraResult = await Camera.requestPermissions({ permissions: ['camera', 'photos'] });
          status = this.normalizeStatus(type === 'camera' ? cameraResult.camera : cameraResult.photos);
          this.permissions.camera = this.normalizeStatus(cameraResult.camera);
          this.permissions.photos = this.normalizeStatus(cameraResult.photos);
          break;

        case 'location':
          const locationResult = await Geolocation.requestPermissions();
          status = this.normalizeStatus(locationResult.location);
          this.permissions.location = status;
          break;

        case 'callLog':
          status = await this.requestNativePermission('READ_CALL_LOG');
          this.permissions.callLog = status;
          break;

        case 'storage':
          status = await this.requestStoragePermissions();
          this.permissions.storage = status;
          break;

        case 'phoneState':
          status = await this.requestNativePermission('READ_PHONE_STATE');
          this.permissions.phoneState = status;
          break;

        case 'contacts':
          status = await this.requestContactsPermission();
          this.permissions.contacts = status;
          break;

        default:
          status = 'unknown';
      }

      this.permissions.lastChecked = Date.now();
      console.log(`[DC_PERMISSIONS] ${type} permission: ${status}`);
      return status;
    } catch (e) {
      console.error(`[DC_PERMISSIONS] ${type} request failed:`, e);
      return 'unknown';
    }
  }

  private requestNativePermission(permission: string): Promise<PermissionStatus> {
    return new Promise((resolve) => {
      try {
        const Capacitor = (window as any).Capacitor;
        if (Capacitor && Capacitor.isNativePlatform?.()) {
          const nativePerms = Capacitor.Plugins?.MyntPermissions;
          if (nativePerms) {
            nativePerms.requestPermission({ permission }).then((res: any) => {
              resolve(res.granted ? 'granted' : 'denied');
            }).catch(() => {
              if (typeof (window as any).cordova !== 'undefined') {
                this.requestViaCordova(permission).then(resolve);
              } else {
                resolve('granted');
              }
            });
            return;
          }
        }

        if (typeof (window as any).cordova !== 'undefined') {
          const permissions = (window as any).cordova.plugins?.permissions;
          if (permissions) {
            permissions.requestPermission(
              permissions[permission],
              (status: any) => resolve(status.hasPermission ? 'granted' : 'denied'),
              () => resolve('unknown')
            );
            return;
          }
        }

        if (Capacitor && Capacitor.isNativePlatform?.()) {
          resolve('granted');
          return;
        }

        resolve('unknown');
      } catch (e) {
        resolve('unknown');
      }
    });
  }

  private requestViaCordova(permission: string): Promise<PermissionStatus> {
    return new Promise((resolve) => {
      const permissions = (window as any).cordova?.plugins?.permissions;
      if (permissions) {
        permissions.requestPermission(
          permissions[permission],
          (status: any) => resolve(status.hasPermission ? 'granted' : 'denied'),
          () => resolve('unknown')
        );
      } else {
        resolve('unknown');
      }
    });
  }

  private async requestContactsPermission(): Promise<PermissionStatus> {
    try {
      const Capacitor = (window as any).Capacitor;
      if (Capacitor && Capacitor.isNativePlatform?.()) {
        const contactsPlugin = Capacitor.Plugins?.MyntContacts;
        if (contactsPlugin) {
          try {
            const result = await contactsPlugin.requestPermissions();
            return result?.contacts === 'granted' ? 'granted' : 'denied';
          } catch (_) {}
        }
      }
      return this.requestNativePermission('READ_CONTACTS');
    } catch (e) {
      console.warn('[DC_PERMISSIONS] Contacts permission request failed:', e);
      return 'unknown';
    }
  }

  private async requestStoragePermissions(): Promise<PermissionStatus> {
    const androidVersion = this.getAndroidVersion();

    if (androidVersion >= 13) {
      const audioStatus = await this.requestNativePermission('READ_MEDIA_AUDIO');
      const imagesStatus = await this.requestNativePermission('READ_MEDIA_IMAGES');
      return (audioStatus === 'granted' || imagesStatus === 'granted') ? 'granted' : audioStatus;
    } else {
      return this.requestNativePermission('READ_EXTERNAL_STORAGE');
    }
  }

  private getAndroidVersion(): number {
    try {
      const device = (window as any).device;
      if (device && device.version) {
        return parseInt(device.version.split('.')[0], 10) || 0;
      }

      const ua = navigator.userAgent;
      const match = ua.match(/Android\s+([\d.]+)/);
      if (match) {
        return parseInt(match[1].split('.')[0], 10) || 0;
      }
    } catch (_) {}
    return 0;
  }

  async requestAllPermissions(): Promise<PermissionState> {
    console.log('[DC_PERMISSIONS] Requesting ALL permissions (one-time)...');

    const cameraResult = await this.requestPermission('camera');
    const locationResult = await this.requestPermission('location');
    const callLogResult = await this.requestPermission('callLog');
    const storageResult = await this.requestPermission('storage');
    const phoneStateResult = await this.requestPermission('phoneState');
    const contactsResult = await this.requestPermission('contacts');

    console.log(`[DC_PERMISSIONS] All permissions requested:
      Camera: ${cameraResult}
      Location: ${locationResult}
      Call Log: ${callLogResult}
      Storage: ${storageResult}
      Phone State: ${phoneStateResult}
      Contacts: ${contactsResult}`);

    this.permissions.lastChecked = Date.now();
    return this.permissions;
  }

  async ensurePermission(type: PermissionType): Promise<boolean> {
    let status: PermissionStatus;

    if (type === 'callLog' || type === 'storage' || type === 'phoneState') {
      status = this.permissions[type];
    } else {
      status = this.permissions[type];
    }

    if (status === 'unknown' || Date.now() - this.permissions.lastChecked > 60000) {
      switch (type) {
        case 'camera':
        case 'photos':
          status = await this.checkCameraPermission();
          break;
        case 'location':
          status = await this.checkLocationPermission();
          break;
        case 'callLog':
        case 'storage':
        case 'phoneState':
          const nativeStatus = await this.checkNativePermissions();
          status = nativeStatus[type];
          break;
      }
    }

    if (status === 'granted') {
      return true;
    }

    if (status === 'denied') {
      console.warn(`[DC_PERMISSIONS] ${type} permission permanently denied`);
      return false;
    }

    const requestedStatus = await this.requestPermission(type);
    return requestedStatus === 'granted';
  }

  async ensureCallTrackingPermissions(): Promise<{ callLog: boolean; storage: boolean; phoneState: boolean; contacts: boolean }> {
    const callLog = await this.ensurePermission('callLog');
    const storage = await this.ensurePermission('storage');
    const phoneState = await this.ensurePermission('phoneState');
    const contacts = await this.ensurePermission('contacts');
    return { callLog, storage, phoneState, contacts };
  }

  async guardedOperation<T>(
    type: PermissionType,
    operation: () => Promise<T>,
    fallback?: T
  ): Promise<T | undefined> {
    const hasPermission = await this.ensurePermission(type);

    if (!hasPermission) {
      console.warn(`[DC_PERMISSIONS] Operation blocked: ${type} permission required`);
      return fallback;
    }

    try {
      return await operation();
    } catch (error) {
      console.error(`[DC_PERMISSIONS] Guarded operation failed:`, error);
      return fallback;
    }
  }

  getPermissionStatus(type: PermissionType): PermissionStatus {
    return this.permissions[type];
  }

  isPermissionGranted(type: PermissionType): boolean {
    return this.permissions[type] === 'granted';
  }

  isPermissionDenied(type: PermissionType): boolean {
    return this.permissions[type] === 'denied';
  }

  getAllPermissionStatuses(): PermissionState {
    return { ...this.permissions };
  }

  async cleanup(): Promise<void> {
    if (this.appStateListenerHandle) {
      await this.appStateListenerHandle.remove();
      this.appStateListenerHandle = null;
    }
    this.lifecycleCallbacks.clear();
    this.initialized = false;
    console.log('[DC_PERMISSIONS] Cleanup complete');
  }
}

export const permissionsRuntime = new PermissionsRuntime();
