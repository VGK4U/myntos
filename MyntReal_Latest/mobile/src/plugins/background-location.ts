import { registerPlugin } from '@capacitor/core';

export interface LocationUpdate {
  latitude: number;
  longitude: number;
  accuracy: number;
  speed: number;
  batteryLevel: number;
  timestamp: number;
}

export interface ServiceStatus {
  isRunning: boolean;
  reason: string;
}

export interface StartTrackingOptions {
  intervalMs?: number;
  authToken: string;
  apiUrl: string;
  notificationTitle?: string;
  notificationText?: string;
}

export interface PermissionStatus {
  fineLocation: boolean;
  coarseLocation: boolean;
  backgroundLocation: boolean;
  allGranted: boolean;
}

export interface BackgroundLocationPlugin {
  startTracking(options: StartTrackingOptions): Promise<{ success: boolean; message: string }>;
  stopTracking(): Promise<{ success: boolean; message: string }>;
  isTracking(): Promise<{ isTracking: boolean }>;
  updateInterval(options: { intervalMs: number }): Promise<{ success: boolean; intervalMs: number }>;
  checkPermissions(): Promise<PermissionStatus>;
  requestPermissions(): Promise<{ granted: boolean }>;
  isIgnoringBatteryOptimizations(): Promise<{ isIgnoring: boolean }>;
  requestBatteryOptimizationExemption(): Promise<{ requested: boolean; alreadyExempt?: boolean }>;
  addListener(
    eventName: 'locationUpdate',
    listenerFunc: (data: LocationUpdate) => void
  ): Promise<{ remove: () => void }>;
  addListener(
    eventName: 'serviceStatus',
    listenerFunc: (data: ServiceStatus) => void
  ): Promise<{ remove: () => void }>;
  removeAllListeners(): Promise<void>;
}

const BackgroundLocation = registerPlugin<BackgroundLocationPlugin>('BackgroundLocation', {
  web: async () => {
    console.warn('BackgroundLocation plugin not available on web - GPS tracking will use JavaScript timers');
    return {
      async startTracking() {
        return { success: false, message: 'Not available on web' };
      },
      async stopTracking() {
        return { success: false, message: 'Not available on web' };
      },
      async isTracking() {
        return { isTracking: false };
      },
      async updateInterval() {
        return { success: false, intervalMs: 0 };
      },
      async checkPermissions() {
        return { fineLocation: false, coarseLocation: false, backgroundLocation: false, allGranted: false };
      },
      async requestPermissions() {
        return { granted: false };
      },
      async isIgnoringBatteryOptimizations() {
        return { isIgnoring: true };
      },
      async requestBatteryOptimizationExemption() {
        return { requested: false, alreadyExempt: true };
      },
      async addListener() {
        return { remove: () => {} };
      },
      async removeAllListeners() {}
    };
  }
});

export { BackgroundLocation };
