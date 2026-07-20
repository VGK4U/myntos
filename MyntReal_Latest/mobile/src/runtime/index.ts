/**
 * Mobile Runtime Compatibility Layer
 * DC Protocol: DC_RUNTIME_001
 * 
 * Central export for all mobile-safe runtime utilities.
 * Replaces web-only behaviors with mobile-compatible equivalents.
 */

export { mobileScheduler } from './scheduler';
export { networkRuntime } from './network';
export { authLifecycle } from './auth-lifecycle';
export { mediaRuntime } from './media';
export { permissionsRuntime } from './permissions';

import { mobileScheduler } from './scheduler';
import { networkRuntime } from './network';
import { authLifecycle } from './auth-lifecycle';
import { mediaRuntime } from './media';
import { permissionsRuntime } from './permissions';

// DC_RUNTIME_TIMEOUT_001: Wraps any init promise with a hard timeout.
// If the Capacitor bridge hangs (native plugin not ready, WebView init race),
// we log a warning and proceed rather than blocking the entire app startup.
// DC_RUNTIME_THROW_001: Also catches thrown errors (not just hangs) so a
// single failing plugin cannot break the entire init chain via Promise.all.
function withTimeout<T>(promise: Promise<T>, ms: number, label: string): Promise<T | void> {
  const safePromise = promise.catch((err: unknown) => {
    console.warn(`[DC_RUNTIME] ${label} threw (non-fatal):`, err);
  });
  const timeout = new Promise<void>((resolve) => {
    setTimeout(() => {
      console.warn(`[DC_RUNTIME] ${label} timed out after ${ms}ms — proceeding without it`);
      resolve();
    }, ms);
  });
  return Promise.race([safePromise, timeout]);
}

export async function initMobileRuntime(): Promise<void> {
  console.log('[DC_RUNTIME] Initializing Mobile Runtime Compatibility Layer...');

  // DC_RUNTIME_TIMEOUT_001: Each init is individually time-boxed at 5s.
  // A hung Capacitor bridge call on any one of these must NEVER block the login page.
  await Promise.all([
    withTimeout(mobileScheduler.init(), 5000, 'mobileScheduler.init'),
    withTimeout(networkRuntime.init(), 5000, 'networkRuntime.init'),
    withTimeout(permissionsRuntime.init(), 5000, 'permissionsRuntime.init')
  ]);

  try {
    mediaRuntime.init();
  } catch (e) {
    console.warn('[DC_RUNTIME] mediaRuntime.init failed (non-fatal):', e);
  }

  await withTimeout(
    authLifecycle.init({
      onTokenExpired: () => {
        console.log('[DC_RUNTIME] Token expired, dispatching event');
        window.dispatchEvent(new CustomEvent('auth-token-expired'));
      },
      onAuthError: (error) => {
        console.error('[DC_RUNTIME] Auth error:', error);
      }
    }),
    5000,
    'authLifecycle.init'
  );

  console.log('[DC_RUNTIME] Mobile Runtime Compatibility Layer initialized');
}

export async function cleanupMobileRuntime(): Promise<void> {
  console.log('[DC_RUNTIME] Cleaning up Mobile Runtime Compatibility Layer...');
  
  await Promise.all([
    mobileScheduler.cleanup(),
    networkRuntime.cleanup(),
    authLifecycle.cleanup(),
    permissionsRuntime.cleanup()
  ]);
  
  mediaRuntime.cleanup();
  
  console.log('[DC_RUNTIME] Mobile Runtime Compatibility Layer cleanup complete');
}
