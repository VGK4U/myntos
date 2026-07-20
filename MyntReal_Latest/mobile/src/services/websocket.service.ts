/**
 * WebSocket Service for Real-Time Location Updates
 * DC Protocol: DC_MOBILE_WS_001
 * Provides instant location broadcasting and team tracking
 */

import { Preferences } from '@capacitor/preferences';
import { APP_CONFIG } from '../config/app.config';

interface LocationUpdate {
  employee_id: number;
  latitude: number;
  longitude: number;
  accuracy_m: number;
  timestamp: string;
  source: 'mobile' | 'web';
  battery_percentage?: number;
}

interface JourneyUpdate {
  journey_id: number;
  employee_id: number;
  status: 'started' | 'paused' | 'resumed' | 'ended';
  latitude?: number;
  longitude?: number;
  timestamp: string;
}

type MessageHandler = (data: any) => void;

const WS_RECONNECT_INTERVAL = 5000;
const WS_PING_INTERVAL = 30000;
// DC Protocol: Use centralized configuration from APP_CONFIG
const WS_BASE_URL = APP_CONFIG.WS_BASE_URL;

class WebSocketService {
  private socket: WebSocket | null = null;
  private reconnectTimer: any = null;
  private pingTimer: any = null;
  private isConnected: boolean = false;
  private handlers: Map<string, Set<MessageHandler>> = new Map();
  private pendingMessages: any[] = [];
  private employeeId: number | null = null;

  async connect(employeeId: number): Promise<boolean> {
    this.employeeId = employeeId;
    
    try {
      const { value: token } = await Preferences.get({ key: 'auth_token' });
      if (!token) {
        console.warn('[DC_WS] No auth token, cannot connect');
        return false;
      }

      const wsUrl = `${WS_BASE_URL}/locations?token=${encodeURIComponent(token)}`;
      
      return new Promise((resolve) => {
        this.socket = new WebSocket(wsUrl);

        this.socket.onopen = () => {
          console.log('[DC_WS] Connected to location server');
          this.isConnected = true;
          this.startPingTimer();
          this.flushPendingMessages();
          this.emit('connected', { employeeId });
          resolve(true);
        };

        this.socket.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
          } catch (error) {
            console.error('[DC_WS] Failed to parse message:', error);
          }
        };

        this.socket.onclose = (event) => {
          console.log('[DC_WS] Disconnected:', event.code, event.reason);
          this.isConnected = false;
          this.stopPingTimer();
          this.emit('disconnected', { code: event.code });
          this.scheduleReconnect();
        };

        this.socket.onerror = (error) => {
          console.error('[DC_WS] Connection error:', error);
          this.emit('error', { error });
          resolve(false);
        };

        setTimeout(() => {
          if (!this.isConnected) {
            console.warn('[DC_WS] Connection timeout');
            resolve(false);
          }
        }, 10000);
      });
    } catch (error) {
      console.error('[DC_WS] Failed to connect:', error);
      return false;
    }
  }

  disconnect(): void {
    this.stopReconnect();
    this.stopPingTimer();
    
    if (this.socket) {
      this.socket.close(1000, 'User disconnected');
      this.socket = null;
    }
    
    this.isConnected = false;
    this.employeeId = null;
    console.log('[DC_WS] Disconnected');
  }

  sendLocationUpdate(location: Omit<LocationUpdate, 'employee_id' | 'source'>): void {
    if (!this.employeeId) return;

    const message = {
      type: 'location_update',
      payload: {
        ...location,
        employee_id: this.employeeId,
        source: 'mobile'
      }
    };

    this.send(message);
  }

  sendJourneyUpdate(update: Omit<JourneyUpdate, 'employee_id'>): void {
    if (!this.employeeId) return;

    const message = {
      type: 'journey_update',
      payload: {
        ...update,
        employee_id: this.employeeId
      }
    };

    this.send(message);
  }

  subscribeToTeamLocations(): void {
    this.send({
      type: 'subscribe',
      channel: 'team_locations'
    });
  }

  subscribeToJourneyUpdates(journeyId: number): void {
    this.send({
      type: 'subscribe',
      channel: `journey_${journeyId}`
    });
  }

  on(event: string, handler: MessageHandler): void {
    if (!this.handlers.has(event)) {
      this.handlers.set(event, new Set());
    }
    this.handlers.get(event)!.add(handler);
  }

  off(event: string, handler: MessageHandler): void {
    const handlers = this.handlers.get(event);
    if (handlers) {
      handlers.delete(handler);
    }
  }

  private emit(event: string, data: any): void {
    const handlers = this.handlers.get(event);
    if (handlers) {
      handlers.forEach(handler => {
        try {
          handler(data);
        } catch (error) {
          console.error(`[DC_WS] Handler error for ${event}:`, error);
        }
      });
    }
  }

  private handleMessage(data: any): void {
    const { type, payload } = data;

    switch (type) {
      case 'location_update':
        this.emit('location_update', payload as LocationUpdate);
        break;
      case 'journey_update':
        this.emit('journey_update', payload as JourneyUpdate);
        break;
      case 'team_locations':
        this.emit('team_locations', payload);
        break;
      case 'pong':
        break;
      default:
        console.log('[DC_WS] Unknown message type:', type);
    }
  }

  private send(message: any): void {
    if (this.isConnected && this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(message));
    } else {
      this.pendingMessages.push(message);
      console.log('[DC_WS] Queued message for later:', message.type);
    }
  }

  private flushPendingMessages(): void {
    while (this.pendingMessages.length > 0) {
      const message = this.pendingMessages.shift();
      this.send(message);
    }
  }

  private startPingTimer(): void {
    this.pingTimer = setInterval(() => {
      this.send({ type: 'ping', timestamp: new Date().toISOString() });
    }, WS_PING_INTERVAL);
  }

  private stopPingTimer(): void {
    if (this.pingTimer) {
      clearInterval(this.pingTimer);
      this.pingTimer = null;
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer) return;
    if (!this.employeeId) return;

    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      console.log('[DC_WS] Attempting reconnect...');
      this.connect(this.employeeId!);
    }, WS_RECONNECT_INTERVAL);
  }

  private stopReconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  getConnectionStatus(): boolean {
    return this.isConnected;
  }
}

export const websocketService = new WebSocketService();
