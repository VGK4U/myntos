import { RawGPSPosition } from '../types/track-point.js';

export interface GPSError {
  code: number;
  message: string;
}

export interface GPSAdapterCallbacks {
  onPositionUpdate: (position: RawGPSPosition) => void;
  onError: (error: GPSError) => void;
  onPermissionDenied: () => void;
}

export interface GPSAdapter {
  startWatching(callbacks: GPSAdapterCallbacks): Promise<boolean>;
  
  stopWatching(): void;
  
  getCurrentPosition(): Promise<RawGPSPosition | null>;
  
  isWatching(): boolean;
  
  checkPermission(): Promise<'granted' | 'denied' | 'prompt'>;
  
  requestPermission(): Promise<boolean>;
}
