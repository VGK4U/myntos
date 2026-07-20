/**
 * Battery Service for Mobile App
 * DC Protocol: DC_MOBILE_BATTERY_001
 * Monitors battery level and charging status
 */

import { Device, DeviceInfo, BatteryInfo } from '@capacitor/device';

interface BatteryStatus {
  level: number;
  isCharging: boolean;
  timestamp: number;
}

class BatteryService {
  private currentStatus: BatteryStatus | null = null;
  private monitorInterval: any = null;
  private onStatusChange: ((status: BatteryStatus) => void) | null = null;

  async getBatteryInfo(): Promise<BatteryStatus | null> {
    try {
      const info: BatteryInfo = await Device.getBatteryInfo();
      
      this.currentStatus = {
        level: Math.round((info.batteryLevel || 0) * 100),
        isCharging: info.isCharging || false,
        timestamp: Date.now()
      };
      
      console.log(`[DC_BATTERY] Level: ${this.currentStatus.level}%, Charging: ${this.currentStatus.isCharging}`);
      return this.currentStatus;
    } catch (error) {
      console.error('[DC_BATTERY] Failed to get battery info:', error);
      return null;
    }
  }

  async getDeviceInfo(): Promise<DeviceInfo | null> {
    try {
      return await Device.getInfo();
    } catch (error) {
      console.error('[DC_BATTERY] Failed to get device info:', error);
      return null;
    }
  }

  startMonitoring(callback?: (status: BatteryStatus) => void): void {
    if (this.monitorInterval) {
      console.log('[DC_BATTERY] Already monitoring');
      return;
    }

    this.onStatusChange = callback || null;
    
    this.getBatteryInfo().then(status => {
      if (status && this.onStatusChange) {
        this.onStatusChange(status);
      }
    });

    this.monitorInterval = setInterval(async () => {
      const status = await this.getBatteryInfo();
      if (status && this.onStatusChange) {
        this.onStatusChange(status);
      }
    }, 60000);

    console.log('[DC_BATTERY] Monitoring started');
  }

  stopMonitoring(): void {
    if (this.monitorInterval) {
      clearInterval(this.monitorInterval);
      this.monitorInterval = null;
    }
    this.onStatusChange = null;
    console.log('[DC_BATTERY] Monitoring stopped');
  }

  getCurrentStatus(): BatteryStatus | null {
    return this.currentStatus;
  }

  isLowBattery(): boolean {
    return this.currentStatus ? this.currentStatus.level < 20 : false;
  }

  isCriticalBattery(): boolean {
    return this.currentStatus ? this.currentStatus.level < 10 : false;
  }

  getBatteryIcon(): string {
    if (!this.currentStatus) return 'battery-unknown';
    
    const level = this.currentStatus.level;
    const charging = this.currentStatus.isCharging;
    
    if (charging) return 'battery-charging';
    if (level >= 80) return 'battery-full';
    if (level >= 50) return 'battery-three-quarters';
    if (level >= 25) return 'battery-half';
    if (level >= 10) return 'battery-quarter';
    return 'battery-empty';
  }

  getBatteryColor(): string {
    if (!this.currentStatus) return '#6b7280';
    
    const level = this.currentStatus.level;
    
    if (level >= 50) return '#10b981';
    if (level >= 25) return '#f59e0b';
    return '#ef4444';
  }
}

export const batteryService = new BatteryService();
