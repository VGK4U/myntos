/**
 * Mobile Runtime Compatibility Layer - Background-Safe Scheduler
 * DC Protocol: DC_RUNTIME_SCHEDULER_001
 * 
 * Replaces setInterval/setTimeout with app lifecycle-aware timers
 * that properly handle iOS/Android background suspension.
 */

import { App, AppState } from '@capacitor/app';

interface ScheduledTask {
  id: string;
  callback: () => void | Promise<void>;
  intervalMs: number;
  lastRun: number;
  isActive: boolean;
  runInBackground: boolean;
  immediateOnResume: boolean;
  timerId: any;
}

interface SchedulerOptions {
  runInBackground?: boolean;
  immediateOnResume?: boolean;
  runImmediately?: boolean;
}

class MobileScheduler {
  private tasks: Map<string, ScheduledTask> = new Map();
  private isInBackground: boolean = false;
  private appStateListenerHandle: any = null;
  private initialized: boolean = false;

  async init(): Promise<void> {
    if (this.initialized) return;
    
    this.appStateListenerHandle = await App.addListener('appStateChange', (state: AppState) => {
      this.handleAppStateChange(state.isActive);
    });
    
    this.initialized = true;
    console.log('[DC_SCHEDULER] Initialized with app lifecycle awareness');
  }

  private handleAppStateChange(isActive: boolean): void {
    const wasBackground = this.isInBackground;
    this.isInBackground = !isActive;

    if (isActive && wasBackground) {
      console.log('[DC_SCHEDULER] App resumed from background, processing tasks');
      this.handleAppResume();
    } else if (!isActive) {
      console.log('[DC_SCHEDULER] App entering background, pausing non-background tasks');
      this.handleAppBackground();
    }
  }

  private handleAppResume(): void {
    this.tasks.forEach((task) => {
      if (!task.isActive) return;

      if (task.immediateOnResume) {
        const elapsed = Date.now() - task.lastRun;
        if (elapsed >= task.intervalMs) {
          console.log(`[DC_SCHEDULER] Running missed task: ${task.id}`);
          this.executeTask(task);
        }
      }

      if (!task.runInBackground) {
        this.startTaskTimer(task);
      }
    });
  }

  private handleAppBackground(): void {
    this.tasks.forEach((task) => {
      if (!task.runInBackground && task.timerId) {
        clearInterval(task.timerId);
        task.timerId = null;
        console.log(`[DC_SCHEDULER] Paused task for background: ${task.id}`);
      }
    });
  }

  private async executeTask(task: ScheduledTask): Promise<void> {
    try {
      task.lastRun = Date.now();
      await task.callback();
    } catch (error) {
      console.error(`[DC_SCHEDULER] Task ${task.id} failed:`, error);
    }
  }

  private startTaskTimer(task: ScheduledTask): void {
    if (task.timerId) {
      clearInterval(task.timerId);
    }

    task.timerId = setInterval(() => {
      if (this.isInBackground && !task.runInBackground) {
        return;
      }
      this.executeTask(task);
    }, task.intervalMs);
  }

  schedule(
    id: string,
    callback: () => void | Promise<void>,
    intervalMs: number,
    options: SchedulerOptions = {}
  ): string {
    if (this.tasks.has(id)) {
      this.cancel(id);
    }

    const task: ScheduledTask = {
      id,
      callback,
      intervalMs,
      lastRun: Date.now(),
      isActive: true,
      runInBackground: options.runInBackground ?? false,
      immediateOnResume: options.immediateOnResume ?? true,
      timerId: null
    };

    this.tasks.set(id, task);

    if (options.runImmediately) {
      this.executeTask(task);
    }

    if (!this.isInBackground || task.runInBackground) {
      this.startTaskTimer(task);
    }

    console.log(`[DC_SCHEDULER] Scheduled task: ${id} (interval: ${intervalMs}ms, background: ${task.runInBackground})`);
    return id;
  }

  cancel(id: string): boolean {
    const task = this.tasks.get(id);
    if (!task) return false;

    if (task.timerId) {
      clearInterval(task.timerId);
    }

    task.isActive = false;
    this.tasks.delete(id);
    console.log(`[DC_SCHEDULER] Cancelled task: ${id}`);
    return true;
  }

  pause(id: string): boolean {
    const task = this.tasks.get(id);
    if (!task) return false;

    if (task.timerId) {
      clearInterval(task.timerId);
      task.timerId = null;
    }
    task.isActive = false;
    console.log(`[DC_SCHEDULER] Paused task: ${id}`);
    return true;
  }

  resume(id: string): boolean {
    const task = this.tasks.get(id);
    if (!task) return false;

    task.isActive = true;
    if (!this.isInBackground || task.runInBackground) {
      this.startTaskTimer(task);
    }
    console.log(`[DC_SCHEDULER] Resumed task: ${id}`);
    return true;
  }

  updateInterval(id: string, newIntervalMs: number): boolean {
    const task = this.tasks.get(id);
    if (!task || !task.isActive) return false;

    if (task.intervalMs === newIntervalMs) return true;

    task.intervalMs = newIntervalMs;
    
    if (!this.isInBackground || task.runInBackground) {
      this.startTaskTimer(task);
    }
    
    console.log(`[DC_SCHEDULER] Updated interval for ${id}: ${newIntervalMs}ms`);
    return true;
  }

  isScheduled(id: string): boolean {
    return this.tasks.has(id) && this.tasks.get(id)!.isActive;
  }

  getActiveTaskCount(): number {
    return Array.from(this.tasks.values()).filter(t => t.isActive).length;
  }

  cancelAll(): void {
    this.tasks.forEach((task) => {
      if (task.timerId) {
        clearInterval(task.timerId);
      }
    });
    this.tasks.clear();
    console.log('[DC_SCHEDULER] Cancelled all tasks');
  }

  async cleanup(): Promise<void> {
    this.cancelAll();
    if (this.appStateListenerHandle) {
      await this.appStateListenerHandle.remove();
      this.appStateListenerHandle = null;
    }
    this.initialized = false;
    console.log('[DC_SCHEDULER] Cleanup complete');
  }

  isAppInBackground(): boolean {
    return this.isInBackground;
  }
}

export const mobileScheduler = new MobileScheduler();
