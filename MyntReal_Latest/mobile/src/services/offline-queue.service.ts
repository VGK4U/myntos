/**
 * Enhanced Offline Queue Service
 * DC Protocol: DC_MOBILE_OFFLINE_001
 * Queues API requests when offline and syncs when connection resumes
 */

import { Preferences } from '@capacitor/preferences';
import { Network } from '@capacitor/network';
import { apiService } from './api.service';

interface QueuedRequest {
  id: string;
  timestamp: number;
  endpoint: string;
  method: 'GET' | 'POST' | 'PUT' | 'DELETE';
  body?: any;
  priority: 'high' | 'medium' | 'low';
  retryCount: number;
  maxRetries: number;
  category: 'location' | 'journey' | 'attendance' | 'general';
}

interface SyncStatus {
  isOnline: boolean;
  isSyncing: boolean;
  pendingCount: number;
  lastSyncTime: number | null;
  failedCount: number;
}

const QUEUE_STORAGE_KEY = 'offline_queue';
const MAX_QUEUE_SIZE = 500;
const SYNC_BATCH_SIZE = 10;
const RETRY_DELAY_MS = 2000;

class OfflineQueueService {
  private queue: QueuedRequest[] = [];
  private isOnline: boolean = true;
  private isSyncing: boolean = false;
  private syncTimer: any = null;
  private statusListeners: Set<(status: SyncStatus) => void> = new Set();
  private networkListenerHandle: any = null;

  async init(): Promise<void> {
    await this.loadQueue();
    await this.setupNetworkListener();
    
    const status = await Network.getStatus();
    this.isOnline = status.connected;
    
    if (this.isOnline && this.queue.length > 0) {
      this.startSync();
    }
    
    console.log(`[DC_OFFLINE] Initialized. Online: ${this.isOnline}, Pending: ${this.queue.length}`);
  }

  private async setupNetworkListener(): Promise<void> {
    this.networkListenerHandle = Network.addListener('networkStatusChange', (status) => {
      const wasOffline = !this.isOnline;
      this.isOnline = status.connected;
      
      console.log(`[DC_OFFLINE] Network status: ${status.connected ? 'online' : 'offline'}`);
      
      if (wasOffline && this.isOnline) {
        console.log('[DC_OFFLINE] Back online, starting sync...');
        this.startSync();
      }
      
      this.notifyStatusChange();
    });
  }

  async enqueue(request: Omit<QueuedRequest, 'id' | 'timestamp' | 'retryCount'>): Promise<string> {
    const id = `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    
    const queuedRequest: QueuedRequest = {
      ...request,
      id,
      timestamp: Date.now(),
      retryCount: 0,
      maxRetries: request.maxRetries || 3
    };

    if (this.queue.length >= MAX_QUEUE_SIZE) {
      const lowPriorityIndex = this.queue.findIndex(r => r.priority === 'low');
      if (lowPriorityIndex !== -1) {
        this.queue.splice(lowPriorityIndex, 1);
      } else {
        this.queue.shift();
      }
      console.warn('[DC_OFFLINE] Queue full, removed oldest/lowest priority item');
    }

    this.queue.push(queuedRequest);
    this.sortQueue();
    await this.saveQueue();
    
    console.log(`[DC_OFFLINE] Enqueued: ${request.endpoint} (${request.category})`);
    this.notifyStatusChange();
    
    if (this.isOnline && !this.isSyncing) {
      this.startSync();
    }
    
    return id;
  }

  async enqueueLocation(
    latitude: number, 
    longitude: number, 
    accuracy_m: number, 
    journeyId?: number,
    battery_percentage?: number
  ): Promise<string> {
    return this.enqueue({
      endpoint: journeyId 
        ? `/staff/journeys/${journeyId}/track-point`
        : '/staff/time-tracker/heartbeat',
      method: 'POST',
      body: {
        latitude,
        longitude,
        accuracy_m,
        timestamp: new Date().toISOString(),
        source: 'mobile_offline_sync',
        battery_percentage
      },
      priority: 'high',
      maxRetries: 5,
      category: 'location'
    });
  }

  async enqueueJourneyAction(
    journeyId: number, 
    action: 'start' | 'pause' | 'resume' | 'end',
    data?: any
  ): Promise<string> {
    const endpoints: Record<string, string> = {
      start: '/staff/journeys/start',
      pause: `/staff/journeys/${journeyId}/pause`,
      resume: `/staff/journeys/${journeyId}/resume`,
      end: `/staff/journeys/${journeyId}/end`
    };

    return this.enqueue({
      endpoint: endpoints[action],
      method: 'POST',
      body: { ...data, timestamp: new Date().toISOString() },
      priority: 'high',
      maxRetries: 5,
      category: 'journey'
    });
  }

  async enqueueAttendanceAction(
    action: 'clock-in' | 'clock-out' | 'break-start' | 'break-end',
    data: any
  ): Promise<string> {
    const endpoints: Record<string, string> = {
      'clock-in': '/staff/time-tracker/clock-in',
      'clock-out': '/staff/time-tracker/clock-out',
      'break-start': '/staff/time-tracker/break/start',
      'break-end': '/staff/time-tracker/break/end'
    };

    return this.enqueue({
      endpoint: endpoints[action],
      method: 'POST',
      body: { ...data, timestamp: new Date().toISOString() },
      priority: 'high',
      maxRetries: 5,
      category: 'attendance'
    });
  }

  private async startSync(): Promise<void> {
    if (this.isSyncing || !this.isOnline || this.queue.length === 0) return;

    this.isSyncing = true;
    this.notifyStatusChange();
    console.log(`[DC_OFFLINE] Starting sync of ${this.queue.length} items`);

    let processedCount = 0;
    let failedCount = 0;

    while (this.queue.length > 0 && this.isOnline) {
      const batch = this.queue.slice(0, SYNC_BATCH_SIZE);
      
      for (const request of batch) {
        try {
          const response = await this.executeRequest(request);
          
          if (response.success) {
            this.removeFromQueue(request.id);
            processedCount++;
          } else if (response.status >= 400 && response.status < 500) {
            console.warn(`[DC_OFFLINE] Client error for ${request.endpoint}, removing`);
            this.removeFromQueue(request.id);
            failedCount++;
          } else {
            request.retryCount++;
            if (request.retryCount >= request.maxRetries) {
              console.error(`[DC_OFFLINE] Max retries reached for ${request.endpoint}`);
              this.removeFromQueue(request.id);
              failedCount++;
            }
          }
        } catch (error) {
          console.error(`[DC_OFFLINE] Sync error for ${request.endpoint}:`, error);
          request.retryCount++;
          
          if (request.retryCount >= request.maxRetries) {
            this.removeFromQueue(request.id);
            failedCount++;
          }
        }
        
        await this.delay(100);
      }
      
      await this.saveQueue();
      await this.delay(RETRY_DELAY_MS);
    }

    this.isSyncing = false;
    console.log(`[DC_OFFLINE] Sync complete. Processed: ${processedCount}, Failed: ${failedCount}`);
    this.notifyStatusChange();
  }

  private async executeRequest(request: QueuedRequest): Promise<any> {
    switch (request.method) {
      case 'GET':
        return apiService.get(request.endpoint);
      case 'POST':
        return apiService.post(request.endpoint, request.body);
      case 'PUT':
        return apiService.put(request.endpoint, request.body);
      case 'DELETE':
        return apiService.delete(request.endpoint);
      default:
        throw new Error(`Unknown method: ${request.method}`);
    }
  }

  private removeFromQueue(id: string): void {
    const index = this.queue.findIndex(r => r.id === id);
    if (index !== -1) {
      this.queue.splice(index, 1);
    }
  }

  private sortQueue(): void {
    const priorityOrder = { high: 0, medium: 1, low: 2 };
    this.queue.sort((a, b) => {
      const priorityDiff = priorityOrder[a.priority] - priorityOrder[b.priority];
      if (priorityDiff !== 0) return priorityDiff;
      return a.timestamp - b.timestamp;
    });
  }

  private async loadQueue(): Promise<void> {
    try {
      const { value } = await Preferences.get({ key: QUEUE_STORAGE_KEY });
      if (value) {
        this.queue = JSON.parse(value);
        console.log(`[DC_OFFLINE] Loaded ${this.queue.length} queued requests`);
      }
    } catch (error) {
      console.error('[DC_OFFLINE] Failed to load queue:', error);
      this.queue = [];
    }
  }

  private async saveQueue(): Promise<void> {
    try {
      await Preferences.set({
        key: QUEUE_STORAGE_KEY,
        value: JSON.stringify(this.queue)
      });
    } catch (error) {
      console.error('[DC_OFFLINE] Failed to save queue:', error);
    }
  }

  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  onStatusChange(listener: (status: SyncStatus) => void): () => void {
    this.statusListeners.add(listener);
    return () => this.statusListeners.delete(listener);
  }

  private notifyStatusChange(): void {
    const status = this.getStatus();
    this.statusListeners.forEach(listener => {
      try {
        listener(status);
      } catch (error) {
        console.error('[DC_OFFLINE] Status listener error:', error);
      }
    });
  }

  getStatus(): SyncStatus {
    return {
      isOnline: this.isOnline,
      isSyncing: this.isSyncing,
      pendingCount: this.queue.length,
      lastSyncTime: null,
      failedCount: this.queue.filter(r => r.retryCount >= r.maxRetries).length
    };
  }

  getPendingCount(): number {
    return this.queue.length;
  }

  async clearQueue(): Promise<void> {
    this.queue = [];
    await this.saveQueue();
    this.notifyStatusChange();
    console.log('[DC_OFFLINE] Queue cleared');
  }

  async cleanup(): Promise<void> {
    if (this.networkListenerHandle) {
      await this.networkListenerHandle.remove();
    }
    if (this.syncTimer) {
      clearInterval(this.syncTimer);
    }
  }
}

export const offlineQueueService = new OfflineQueueService();
