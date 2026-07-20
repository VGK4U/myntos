/**
 * Mobile Runtime Compatibility Layer - Network Retry
 * DC Protocol: DC_RUNTIME_NETWORK_001
 * 
 * Provides exponential backoff retry logic for API calls
 * with offline detection and request queuing.
 */

import { Network } from '@capacitor/network';

interface RetryOptions {
  maxRetries?: number;
  baseDelayMs?: number;
  maxDelayMs?: number;
  retryOn?: number[];
  onRetry?: (attempt: number, error: any) => void;
  timeout?: number;
}

interface NetworkStatus {
  isOnline: boolean;
  connectionType: string;
  lastCheck: number;
}

const DEFAULT_RETRY_OPTIONS: Required<Omit<RetryOptions, 'onRetry'>> = {
  maxRetries: 3,
  baseDelayMs: 1000,
  maxDelayMs: 30000,
  retryOn: [408, 429, 500, 502, 503, 504, 0],
  timeout: 30000
};

class NetworkRuntime {
  private networkStatus: NetworkStatus = {
    isOnline: true,
    connectionType: 'unknown',
    lastCheck: 0
  };
  private networkListenerHandle: any = null;
  private statusListeners: Set<(isOnline: boolean) => void> = new Set();
  private initialized: boolean = false;

  async init(): Promise<void> {
    if (this.initialized) return;

    const status = await Network.getStatus();
    this.networkStatus = {
      isOnline: status.connected,
      connectionType: status.connectionType,
      lastCheck: Date.now()
    };

    this.networkListenerHandle = await Network.addListener('networkStatusChange', (status) => {
      const wasOffline = !this.networkStatus.isOnline;
      this.networkStatus = {
        isOnline: status.connected,
        connectionType: status.connectionType,
        lastCheck: Date.now()
      };

      console.log(`[DC_NETWORK] Status changed: ${status.connected ? 'online' : 'offline'} (${status.connectionType})`);
      
      this.statusListeners.forEach(listener => {
        try {
          listener(status.connected);
        } catch (e) {
          console.error('[DC_NETWORK] Listener error:', e);
        }
      });

      if (wasOffline && status.connected) {
        window.dispatchEvent(new CustomEvent('network-restored'));
      }
    });

    this.initialized = true;
    console.log(`[DC_NETWORK] Initialized. Online: ${this.networkStatus.isOnline}`);
  }

  isOnline(): boolean {
    return this.networkStatus.isOnline;
  }

  getConnectionType(): string {
    return this.networkStatus.connectionType;
  }

  onStatusChange(listener: (isOnline: boolean) => void): () => void {
    this.statusListeners.add(listener);
    return () => this.statusListeners.delete(listener);
  }

  private calculateDelay(attempt: number, baseDelay: number, maxDelay: number): number {
    const exponentialDelay = baseDelay * Math.pow(2, attempt - 1);
    const jitter = Math.random() * 0.3 * exponentialDelay;
    return Math.min(exponentialDelay + jitter, maxDelay);
  }

  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  async withRetry<T>(
    operation: () => Promise<T>,
    options: RetryOptions = {}
  ): Promise<T> {
    const opts = { ...DEFAULT_RETRY_OPTIONS, ...options };
    let lastError: any;

    for (let attempt = 1; attempt <= opts.maxRetries + 1; attempt++) {
      try {
        if (!this.networkStatus.isOnline) {
          throw new Error('OFFLINE');
        }

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), opts.timeout);

        try {
          const result = await operation();
          clearTimeout(timeoutId);
          return result;
        } catch (error: any) {
          clearTimeout(timeoutId);
          throw error;
        }
      } catch (error: any) {
        lastError = error;

        const status = error.status || (error.message === 'OFFLINE' ? 0 : -1);
        const shouldRetry = opts.retryOn.includes(status) || error.name === 'AbortError';

        if (attempt <= opts.maxRetries && shouldRetry) {
          const delay = this.calculateDelay(attempt, opts.baseDelayMs, opts.maxDelayMs);
          console.log(`[DC_NETWORK] Retry ${attempt}/${opts.maxRetries} in ${Math.round(delay)}ms`);
          
          if (opts.onRetry) {
            opts.onRetry(attempt, error);
          }

          await this.sleep(delay);
        } else {
          break;
        }
      }
    }

    throw lastError;
  }

  async fetchWithRetry(
    url: string,
    init?: RequestInit,
    retryOptions?: RetryOptions
  ): Promise<Response> {
    return this.withRetry(async () => {
      const response = await fetch(url, init);
      
      if (!response.ok) {
        const error: any = new Error(`HTTP ${response.status}`);
        error.status = response.status;
        error.response = response;
        throw error;
      }
      
      return response;
    }, retryOptions);
  }

  async waitForOnline(timeoutMs: number = 30000): Promise<boolean> {
    if (this.networkStatus.isOnline) return true;

    return new Promise((resolve) => {
      const timeout = setTimeout(() => {
        cleanup();
        resolve(false);
      }, timeoutMs);

      const cleanup = this.onStatusChange((isOnline) => {
        if (isOnline) {
          clearTimeout(timeout);
          cleanup();
          resolve(true);
        }
      });
    });
  }

  async cleanup(): Promise<void> {
    if (this.networkListenerHandle) {
      await this.networkListenerHandle.remove();
      this.networkListenerHandle = null;
    }
    this.statusListeners.clear();
    this.initialized = false;
    console.log('[DC_NETWORK] Cleanup complete');
  }
}

export const networkRuntime = new NetworkRuntime();
