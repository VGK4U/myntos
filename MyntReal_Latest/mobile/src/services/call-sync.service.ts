/**
 * Call Sync Service for MNR Mobile App
 * DC Protocol: DC_MOBILE_CALL_SYNC_001
 * 
 * Scans native Android call logs and recording folders,
 * syncs call data to the server, and uploads recordings.
 * Uses Capacitor plugins for native access.
 * 
 * Supports ALL major Android manufacturers with auto-detection
 * and custom folder selection for unknown models.
 */

import { Preferences } from '@capacitor/preferences';
import { apiService } from './api.service';
import { API_ENDPOINTS } from '../constants/api-endpoints';
import { permissionsRuntime } from '../runtime/permissions';
import { APP_CONFIG } from '../config/app.config';

const LAST_SYNC_KEY = 'call_sync_last_timestamp';
const SYNC_ENABLED_KEY = 'call_sync_enabled';
const DETECTED_FOLDERS_KEY = 'call_sync_detected_folders';
const CUSTOM_FOLDERS_KEY = 'call_sync_custom_folders';
const LAST_FOLDER_SCAN_KEY = 'call_sync_last_folder_scan';

interface NativeCallLog {
  id: string;
  number: string;
  type: string;
  date: number;
  duration: number;
  name?: string;
  cachedName?: string;
}

interface RecordingFile {
  path: string;
  name: string;
  size: number;
  lastModified: number;
  phoneNumber?: string;
  folderSource?: string;
}

interface DetectedFolder {
  path: string;
  brand: string;
  fileCount: number;
  detectedAt: number;
}

const RECORDING_FOLDERS_BY_BRAND: Record<string, string[]> = {
  'Samsung': [
    'Recordings',
    'Recordings/Call',
    'Call',
    'Call/Recordings',
    'PhoneRecording',
    'Sounds/CallRecord',
    'Recordings/Voice Recorder',
    'DCIM/.voice_call',
    'Music/Call',
    'Samsung/CallRecording',
    'Voice Recorder',
    'Voice Recorder/Call',
  ],
  'Xiaomi / Redmi / Poco': [
    'MIUI/sound_recorder/call_rec',
    'MIUI/sound_recorder',
    'sound_recorder/call_rec',
    'Recordings/Call Recordings',
    'Music/Recordings/Call Recordings',
    'CallRecordings',
    'MIUI/Gallery/CallRecorder',
    'Record/PhoneRecord',
    'Recorder/Call',
  ],
  'OnePlus': [
    'Recorder',
    'Recorder/Call',
    'Record/Call',
    'Record/PhoneRecord',
    'Recordings/Call Recordings',
    'Music/Recordings/Call Recordings',
    'CallRecordings',
  ],
  'Oppo / Realme': [
    'Music/Recordings/Call Recordings',
    'Recordings/Call Recordings',
    'Record/Call',
    'Record/PhoneRecord',
    'CallRecorder',
    'DCIM/CallRecorder',
    'ColorOS/CallRecorder',
    'Phone/CallRecordings',
  ],
  'Vivo / iQOO': [
    'Record/Call',
    'Record/PhoneRecord',
    'Recordings/Record/Call',
    'Music/record/call',
    'VivoRecorder',
    'Recordings',
    'CallRecord',
    'Music/Recordings/Call Recordings',
  ],
  'Huawei / Honor': [
    'Sounds/CallRecord',
    'record',
    'Record',
    'Sounds',
    'HuaweiRecorder',
    'Recorder',
    'Recordings/CallRecordings',
    'Phone/CallRecordings',
  ],
  'Google Pixel': [
    'CallRecordings',
    'Recordings',
    'Call Recordings',
    'Pixel/CallRecordings',
    'PhoneCallRecordings',
  ],
  'Motorola / Lenovo': [
    'CallRecordings',
    'Recordings/CallRecordings',
    'Phone/CallRecordings',
    'MotoRecorder',
    'Record/Call',
    'Recordings',
  ],
  'LG': [
    'Recordings',
    'CallRecordings',
    'LGRecorder',
    'Recording/Call',
    'Phone/CallRecordings',
  ],
  'Nokia': [
    'Recordings',
    'CallRecordings',
    'Phone/CallRecordings',
    'Record/Call',
    'Music/Recordings/Call Recordings',
  ],
  'Asus / ROG': [
    'Recorder',
    'CallRecording',
    'Recordings/CallRecordings',
    'AsusRecorder',
    'ZenRecorder',
    'Record/Call',
  ],
  'Infinix / Tecno / itel': [
    'CallRecording',
    'Record/Call',
    'Record/PhoneRecord',
    'Recordings',
    'Music/Recordings/Call Recordings',
    'Phone/CallRecordings',
    'TranssionRecorder',
  ],
  'Nothing': [
    'Recordings',
    'CallRecordings',
    'Phone/CallRecordings',
    'Record/Call',
    'Music/Recordings/Call Recordings',
  ],
  'Sony': [
    'Recordings',
    'CallRecordings',
    'SonyRecorder',
    'Phone/CallRecordings',
    'Record/Call',
  ],
  'ZTE / Nubia': [
    'Recordings',
    'CallRecording',
    'Record/Call',
    'Phone/CallRecordings',
    'NubiaRecorder',
  ],
  'Generic / Other': [
    'Recordings',
    'CallRecording',
    'CallRecordings',
    'Call',
    'Record',
    'Record/Call',
    'Record/PhoneRecord',
    'Phone/CallRecordings',
    'Music/Recordings',
    'Music/Recordings/Call Recordings',
    'Recorder',
    'Recorder/Call',
    'Voice Recorder',
    'DCIM/CallRecorder',
    'PhoneCallRecordings',
    'call_recording',
    'callrecord',
  ],
};

const ALL_KNOWN_FOLDERS: string[] = [];
for (const brand of Object.keys(RECORDING_FOLDERS_BY_BRAND)) {
  for (const folder of RECORDING_FOLDERS_BY_BRAND[brand]) {
    if (!ALL_KNOWN_FOLDERS.includes(folder)) {
      ALL_KNOWN_FOLDERS.push(folder);
    }
  }
}

const AUDIO_EXTENSIONS = ['.mp3', '.m4a', '.amr', '.wav', '.3gp', '.ogg', '.aac', '.wma', '.opus', '.flac'];

export interface SyncProgress {
  stage: 'reading' | 'uploading' | 'recordings' | 'done' | 'error';
  detail: string;
  callsFound?: number;
  callsSynced?: number;
  callsMatched?: number;
  startedAt: number;
}

class CallSyncService {
  private isSyncing: boolean = false;
  private syncEnabled: boolean = false;
  private detectedFolders: DetectedFolder[] = [];
  private customFolders: string[] = [];
  private autoSyncTimer: ReturnType<typeof setInterval> | null = null;
  private static AUTO_SYNC_INTERVAL_MS = 15 * 60 * 1000;
  public _lastSyncError: string | null = null;
  private _syncProgress: SyncProgress | null = null;
  private _consecutiveAuthFailures = 0;  // DC_CALL_SYNC_AUTH: auto-disable after 3 consecutive 401s

  getLastSyncError(): string | null {
    return this._lastSyncError;
  }

  getSyncProgress(): SyncProgress | null {
    return this._syncProgress;
  }

  isSyncInProgress(): boolean {
    return this.isSyncing;
  }

  private setProgress(stage: SyncProgress['stage'], detail: string, extra?: Partial<SyncProgress>): void {
    this._syncProgress = {
      stage,
      detail,
      startedAt: this._syncProgress?.startedAt ?? Date.now(),
      ...extra,
    };
  }

  async init(): Promise<void> {
    try {
      const { value: enabled } = await Preferences.get({ key: SYNC_ENABLED_KEY });
      this.syncEnabled = enabled === 'true';

      const { value: detected } = await Preferences.get({ key: DETECTED_FOLDERS_KEY });
      if (detected) {
        try { this.detectedFolders = JSON.parse(detected); } catch (_) { this.detectedFolders = []; }
      }

      const { value: custom } = await Preferences.get({ key: CUSTOM_FOLDERS_KEY });
      if (custom) {
        try { this.customFolders = JSON.parse(custom); } catch (_) { this.customFolders = []; }
      }

      console.log(`[DC_CALL_SYNC] Initialized, enabled: ${this.syncEnabled}, detected folders: ${this.detectedFolders.length}, custom folders: ${this.customFolders.length}`);

      if (this.syncEnabled) {
        this.startAutoSync();
      }
    } catch (e) {
      console.warn('[DC_CALL_SYNC] Init error (safe):', e);
    }
  }

  private startAutoSync(): void {
    this.stopAutoSync();
    console.log(`[DC_CALL_SYNC] Auto-sync started (every ${CallSyncService.AUTO_SYNC_INTERVAL_MS / 60000} min)`);
    this.autoSyncTimer = setInterval(async () => {
      if (!this.syncEnabled || this.isSyncing) return;
      try {
        console.log('[DC_CALL_SYNC] Auto-sync triggered');
        await this.syncCallLogs(false);
        await this.scanAndUploadRecordings();
      } catch (e) {
        console.warn('[DC_CALL_SYNC] Auto-sync error (safe):', e);
      }
    }, CallSyncService.AUTO_SYNC_INTERVAL_MS);
  }

  private stopAutoSync(): void {
    if (this.autoSyncTimer) {
      clearInterval(this.autoSyncTimer);
      this.autoSyncTimer = null;
      console.log('[DC_CALL_SYNC] Auto-sync stopped');
    }
  }

  async setSyncEnabled(enabled: boolean): Promise<void> {
    this.syncEnabled = enabled;
    await Preferences.set({ key: SYNC_ENABLED_KEY, value: String(enabled) });
    if (enabled && this.detectedFolders.length === 0) {
      await this.autoDetectFolders();
    }
    if (enabled) {
      this.startAutoSync();
    } else {
      this.stopAutoSync();
    }
    console.log(`[DC_CALL_SYNC] Sync ${enabled ? 'enabled' : 'disabled'}`);
  }

  isSyncEnabled(): boolean {
    return this.syncEnabled;
  }

  getDetectedFolders(): DetectedFolder[] {
    return [...this.detectedFolders];
  }

  getCustomFolders(): string[] {
    return [...this.customFolders];
  }

  getActiveFolderPaths(): string[] {
    const paths: string[] = [];
    for (const d of this.detectedFolders) {
      if (!paths.includes(d.path)) paths.push(d.path);
    }
    for (const c of this.customFolders) {
      if (!paths.includes(c)) paths.push(c);
    }
    return paths;
  }

  getKnownFoldersByBrand(): Record<string, string[]> {
    return RECORDING_FOLDERS_BY_BRAND;
  }

  async addCustomFolder(folderPath: string): Promise<boolean> {
    const cleaned = folderPath.trim().replace(/^\/+|\/+$/g, '');
    if (!cleaned) return false;
    if (this.customFolders.includes(cleaned)) return false;

    const hasFiles = await this.checkFolderHasRecordings(cleaned);
    this.customFolders.push(cleaned);
    await Preferences.set({ key: CUSTOM_FOLDERS_KEY, value: JSON.stringify(this.customFolders) });
    console.log(`[DC_CALL_SYNC] Added custom folder: ${cleaned} (has recordings: ${hasFiles})`);
    return true;
  }

  async removeCustomFolder(folderPath: string): Promise<void> {
    this.customFolders = this.customFolders.filter(f => f !== folderPath);
    await Preferences.set({ key: CUSTOM_FOLDERS_KEY, value: JSON.stringify(this.customFolders) });
  }

  async autoDetectFolders(): Promise<DetectedFolder[]> {
    console.log(`[DC_CALL_SYNC] Auto-detecting recording folders (${ALL_KNOWN_FOLDERS.length} known paths)...`);
    const detected: DetectedFolder[] = [];

    try {
      const Filesystem = this.getFilesystemPlugin();
      if (!Filesystem) {
        console.log('[DC_CALL_SYNC] Filesystem not available (web mode)');
        return detected;
      }

      for (const folder of ALL_KNOWN_FOLDERS) {
        try {
          const result = await Filesystem.readdir({
            path: folder,
            directory: 'EXTERNAL_STORAGE',
          });

          if (result && result.files) {
            const audioFiles = (result.files as any[]).filter((f: any) => {
              const ext = '.' + (f.name || '').split('.').pop()?.toLowerCase();
              return AUDIO_EXTENSIONS.includes(ext);
            });

            if (audioFiles.length > 0) {
              const brand = this.identifyBrand(folder);
              detected.push({
                path: folder,
                brand,
                fileCount: audioFiles.length,
                detectedAt: Date.now(),
              });
              console.log(`[DC_CALL_SYNC] Found ${audioFiles.length} recordings in ${folder} (${brand})`);
            }
          }
        } catch (_e) {
          // folder doesn't exist on this device
        }
      }

      this.detectedFolders = detected;
      await Preferences.set({ key: DETECTED_FOLDERS_KEY, value: JSON.stringify(detected) });
      await Preferences.set({ key: LAST_FOLDER_SCAN_KEY, value: String(Date.now()) });

      console.log(`[DC_CALL_SYNC] Auto-detection complete: ${detected.length} folders with recordings found`);
    } catch (e) {
      console.error('[DC_CALL_SYNC] Auto-detection error:', e);
    }

    return detected;
  }

  private identifyBrand(folderPath: string): string {
    for (const [brand, folders] of Object.entries(RECORDING_FOLDERS_BY_BRAND)) {
      if (brand === 'Generic / Other') continue;
      if (folders.includes(folderPath)) return brand;
    }
    return 'Unknown';
  }

  private async checkFolderHasRecordings(folderPath: string): Promise<boolean> {
    try {
      const Filesystem = this.getFilesystemPlugin();
      if (!Filesystem) return false;

      const result = await Filesystem.readdir({
        path: folderPath,
        directory: 'EXTERNAL_STORAGE',
      });

      if (result && result.files) {
        return (result.files as any[]).some((f: any) => {
          const ext = '.' + (f.name || '').split('.').pop()?.toLowerCase();
          return AUDIO_EXTENSIONS.includes(ext);
        });
      }
    } catch (_e) {}
    return false;
  }

  private getFilesystemPlugin(): any {
    if (typeof (window as any).Capacitor === 'undefined') return null;
    return (window as any).Capacitor?.Plugins?.Filesystem || null;
  }

  async getLastSyncTimestamp(): Promise<number> {
    const { value } = await Preferences.get({ key: LAST_SYNC_KEY });
    return value ? parseInt(value, 10) : 0;
  }

  private async setLastSyncTimestamp(ts: number): Promise<void> {
    await Preferences.set({ key: LAST_SYNC_KEY, value: String(ts) });
  }

  async getLastFolderScanTimestamp(): Promise<number> {
    const { value } = await Preferences.get({ key: LAST_FOLDER_SCAN_KEY });
    return value ? parseInt(value, 10) : 0;
  }

  private isNativePlatform(): boolean {
    try {
      return typeof (window as any).Capacitor !== 'undefined' &&
             (window as any).Capacitor.isNativePlatform?.() === true;
    } catch (_) {
      return false;
    }
  }

  async checkPermissions(): Promise<{ callLog: boolean; storage: boolean; phoneState: boolean }> {
    if (!this.isNativePlatform()) {
      console.log('[DC_CALL_SYNC] Web mode - permissions not applicable');
      return { callLog: true, storage: true, phoneState: true };
    }
    try {
      return await permissionsRuntime.ensureCallTrackingPermissions();
    } catch (e) {
      console.warn('[DC_CALL_SYNC] Permission check failed (safe):', e);
      return { callLog: false, storage: false, phoneState: false };
    }
  }

  async getPermissionStatuses(): Promise<{ callLog: string; storage: string; phoneState: string }> {
    if (!this.isNativePlatform()) {
      return { callLog: 'granted', storage: 'granted', phoneState: 'granted' };
    }
    try {
      const all = permissionsRuntime.getAllPermissionStatuses();
      return {
        callLog: all.callLog,
        storage: all.storage,
        phoneState: all.phoneState,
      };
    } catch (_) {
      return { callLog: 'unknown', storage: 'unknown', phoneState: 'unknown' };
    }
  }

  async syncCallLogs(forceManual: boolean = false): Promise<{ synced: number; matched: number; skipped: number } | null> {
    if (this.isSyncing) {
      console.log('[DC_CALL_SYNC] Sync skipped (already syncing)');
      this._lastSyncError = 'Sync already in progress. Please wait a moment and try again.';
      return null;
    }
    if (!forceManual && !this.syncEnabled) {
      console.log('[DC_CALL_SYNC] Auto-sync disabled, skipping');
      this._lastSyncError = 'Auto-sync is disabled. Enable it using the toggle above.';
      return null;
    }

    this._lastSyncError = null;

    const perms = await this.checkPermissions();
    if (!perms.callLog) {
      console.warn('[DC_CALL_SYNC] Call log permission not granted - cannot sync call logs');
      this._lastSyncError = 'Call log permission not granted. Please allow the permission in device settings.';
      return null;
    }

    this.isSyncing = true;
    this._syncProgress = { stage: 'reading', detail: 'Reading call logs from device...', startedAt: Date.now() };
    console.log('[DC_CALL_SYNC] Starting call log sync...');

    try {
      const lastSync = await this.getLastSyncTimestamp();
      const callLogs = await this.readNativeCallLogs(lastSync);

      if (callLogs === null) {
        console.warn('[DC_CALL_SYNC] Could not read native call logs — plugin error or permission denied');
        this._lastSyncError = 'Could not read call logs from your device. Please ensure the Call Log permission is granted in device Settings > Apps > MyntReal > Permissions.';
        this.setProgress('error', this._lastSyncError);
        return null;
      }

      if (callLogs.length === 0) {
        console.log('[DC_CALL_SYNC] No new call logs to sync');
        this.setProgress('done', 'No new calls to sync. All up to date.', { callsFound: 0, callsSynced: 0, callsMatched: 0 });
        return { synced: 0, matched: 0, skipped: 0 };
      }

      console.log(`[DC_CALL_SYNC] Found ${callLogs.length} new call logs`);
      this.setProgress('uploading', `Found ${callLogs.length} call${callLogs.length !== 1 ? 's' : ''}. Uploading to server...`, { callsFound: callLogs.length });

      const validLogs = callLogs.filter(log => {
        const hasDate = log.date != null && !isNaN(Number(log.date));
        const hasNumber = log.number != null && String(log.number).trim().length > 0;
        return hasDate && hasNumber;
      });

      if (validLogs.length === 0) {
        console.log('[DC_CALL_SYNC] All call logs were filtered out (missing date/number)');
        this.setProgress('done', 'No valid call data found to upload.', { callsFound: callLogs.length, callsSynced: 0, callsMatched: 0 });
        return { synced: 0, matched: 0, skipped: callLogs.length };
      }

      console.log(`[DC_CALL_SYNC] ${validLogs.length} valid logs after filter (${callLogs.length - validLogs.length} skipped)`);

      const contactNameMap = await this.lookupContactNames(validLogs);

      const payload = validLogs.map(log => ({
        phone_number: String(log.number),
        call_type: this.mapCallType(String(log.type || '')),
        call_datetime: new Date(Number(log.date)).toISOString(),
        duration_seconds: Number(log.duration) || 0,
        // DC_DEDUP_001: Preserve id=0 as '0' (not empty string) so backend dedup works
        device_call_id: (log.id != null) ? String(log.id) : '',
        source: 'native',
        contact_name: log.name || log.cachedName || contactNameMap.get(String(log.number)) || null,
      }));

      // DC Protocol Mar 2026: Batch syncing — backend max is 500 per request.
      // Split payload into chunks of 500 and send sequentially.
      const BATCH_SIZE = 500;
      const totalBatches = Math.ceil(payload.length / BATCH_SIZE);
      const maxDate = Math.max(...callLogs.map(c => c.date));
      let totalSynced = 0, totalMatched = 0, totalSkipped = 0;

      console.log(`[DC_CALL_SYNC] Splitting ${payload.length} calls into ${totalBatches} batch(es) of up to ${BATCH_SIZE}`);

      for (let batchIdx = 0; batchIdx < totalBatches; batchIdx++) {
        const batch = payload.slice(batchIdx * BATCH_SIZE, (batchIdx + 1) * BATCH_SIZE);
        const batchNum = batchIdx + 1;
        const progressDetail = totalBatches > 1
          ? `Uploading batch ${batchNum}/${totalBatches} (${batch.length} calls)...`
          : `Uploading ${batch.length} call${batch.length !== 1 ? 's' : ''} to server...`;

        this.setProgress('uploading', progressDetail, {
          callsFound: callLogs.length,
          callsSynced: totalSynced,
          callsMatched: totalMatched,
        });

        const response = await apiService.post(API_ENDPOINTS.CALL_TRACKING.SYNC_CALLS, batch);

        if (response.success && response.data) {
          const result = response.data as any;
          totalSynced  += result.records_synced  ?? result.synced   ?? 0;
          totalMatched += result.records_matched  ?? result.matched  ?? 0;
          totalSkipped += result.records_skipped  ?? result.records_duplicates_skipped ?? result.skipped ?? 0;
          console.log(`[DC_CALL_SYNC] Batch ${batchNum}/${totalBatches} OK — running totals: synced=${totalSynced} matched=${totalMatched}`);
        } else {
          const errMsg = response.error || 'Sync failed';
          const isNetworkResponse = /failed to fetch|network request failed|networkerror|timed out|abort/i.test(errMsg) || response.status === 0;
          const isAuthError = response.status === 401 || errMsg.toLowerCase() === 'not authenticated';
          if (isNetworkResponse) {
            const devHint = this._isDevMode()
              ? ' App is in DEV mode — go to Settings and switch to Production to use mnrteam.com.'
              : ' Check your internet connection and try again.';
            console.warn('[DC_CALL_SYNC] Network unreachable during sync:', errMsg);
            this._lastSyncError = `Cannot reach server.${devHint}`;
          } else if (isAuthError) {
            // DC_CALL_SYNC_AUTH: Give actionable message; track failures; auto-disable after 3
            this._consecutiveAuthFailures++;
            console.warn(`[DC_CALL_SYNC] Auth failure #${this._consecutiveAuthFailures}:`, errMsg);
            if (this._isDevMode()) {
              this._lastSyncError = 'App is in DEV mode — go to Profile → Settings, switch to Production, then log out and log back in.';
            } else {
              this._lastSyncError = 'Session expired — please log out and log in again.';
            }
            if (this._consecutiveAuthFailures >= 3) {
              await this.setSyncEnabled(false);
              this._lastSyncError += ' Auto-sync disabled after 3 failed attempts.';
              console.warn('[DC_CALL_SYNC] Auto-sync disabled after 3 consecutive auth failures');
            }
          } else if (errMsg.toLowerCase().includes('not enabled')) {
            console.warn('[DC_CALL_SYNC] Call tracking not enabled for this account:', errMsg);
            this._lastSyncError = 'Call tracking is not enabled for your account. Ask your manager to enable it.';
          } else {
            console.warn(`[DC_CALL_SYNC] Batch ${batchNum}/${totalBatches} failed:`, errMsg);
            this._lastSyncError = errMsg;
          }
          this.setProgress('error', this._lastSyncError!);
          return null;
        }
      }

      // All batches succeeded — commit the last-sync timestamp; reset auth failure counter
      this._consecutiveAuthFailures = 0;
      await this.setLastSyncTimestamp(maxDate);
      console.log(`[DC_CALL_SYNC] All ${totalBatches} batch(es) complete: ${totalSynced} synced, ${totalMatched} matched`);
      this.setProgress('done', `Sync complete. ${totalSynced} uploaded, ${totalMatched} matched to CRM.`, {
        callsFound: callLogs.length,
        callsSynced: totalSynced,
        callsMatched: totalMatched,
      });
      return { synced: totalSynced, matched: totalMatched, skipped: totalSkipped };
    } catch (error: any) {
      const msg = error?.message || String(error) || 'Unknown error';
      console.error('[DC_CALL_SYNC] Sync error:', msg, error);
      // DC_CALL_SYNC_NET_ERR: Provide actionable messages for network-level failures
      const isNetworkErr = /failed to fetch|network request failed|networkerror|timed out|abort/i.test(msg);
      if (isNetworkErr) {
        const devHint = this._isDevMode()
          ? ' App is in DEV mode — go to Settings → switch to Production to use mnrteam.com.'
          : ' Check your internet connection and try again.';
        this._lastSyncError = `Cannot reach server.${devHint}`;
      } else {
        this._lastSyncError = `Sync error: ${msg}`;
      }
      this.setProgress('error', this._lastSyncError);
      return null;
    } finally {
      this.isSyncing = false;
    }
  }

  private _isDevMode(): boolean {
    try {
      return APP_CONFIG.isDevMode();
    } catch {
      return false;
    }
  }

  private waitForCordova(timeoutMs: number = 4000): Promise<any> {
    return new Promise((resolve) => {
      const cordova = (window as any).cordova;
      if (cordova && typeof cordova.exec === 'function') {
        resolve(cordova);
        return;
      }
      const timer = setTimeout(() => {
        document.removeEventListener('deviceready', handler);
        console.warn('[DC_CALL_SYNC] Cordova bridge not available after timeout — running in web mode');
        resolve(null);
      }, timeoutMs);
      const handler = () => {
        clearTimeout(timer);
        const c = (window as any).cordova;
        // DC_CALLSYNC_FIX: Mirror the initial exec check — resolve null if exec not yet attached.
        // Without this guard, a partial Cordova object (truthy but missing .exec) passes the
        // null check in readNativeCallLogs and throws "t.exec is not a function" inside the
        // Promise executor, crashing every sync attempt on affected Android devices.
        if (c && typeof c.exec === 'function') {
          console.log('[DC_CALL_SYNC] deviceready fired — cordova.exec ready');
          resolve(c);
        } else {
          console.warn('[DC_CALL_SYNC] deviceready fired but cordova.exec not attached — returning null (graceful fallback)');
          resolve(null);
        }
      };
      document.addEventListener('deviceready', handler, { once: true });
    });
  }

  private async lookupContactNames(logs: NativeCallLog[]): Promise<Map<string, string>> {
    const map = new Map<string, string>();
    try {
      const phonesWithoutName = [...new Set(
        logs
          .filter(l => !l.name && !l.cachedName && l.number)
          .map(l => String(l.number))
      )];

      if (phonesWithoutName.length === 0) return map;

      const Capacitor = (window as any).Capacitor;
      if (!Capacitor || !Capacitor.isNativePlatform?.()) return map;

      const contactsPlugin = Capacitor.Plugins?.MyntContacts;
      if (!contactsPlugin) {
        console.log('[DC_CALL_SYNC] MyntContacts plugin not available — skipping contact lookup');
        return map;
      }

      const batchSize = 50;
      for (let i = 0; i < phonesWithoutName.length; i += batchSize) {
        const batch = phonesWithoutName.slice(i, i + batchSize);
        try {
          const result = await contactsPlugin.getContactNames({ phoneNumbers: batch });
          if (result?.contacts) {
            const contacts = result.contacts;
            for (const phone of batch) {
              if (contacts[phone]) {
                map.set(phone, contacts[phone]);
              }
            }
          }
        } catch (e) {
          console.warn('[DC_CALL_SYNC] Contact batch lookup failed:', e);
        }
      }

      console.log(`[DC_CALL_SYNC] Contact lookup: ${map.size} names found for ${phonesWithoutName.length} numbers`);
    } catch (e) {
      console.warn('[DC_CALL_SYNC] Contact lookup failed:', e);
    }
    return map;
  }

  private async readNativeCallLogs(sinceTimestamp: number): Promise<NativeCallLog[] | null> {
    try {
      const cordova = await this.waitForCordova(4000);
      if (!cordova) {
        console.log('[DC_CALL_SYNC] No cordova bridge — returning empty log (web/non-native mode)');
        return [];
      }

      return new Promise((resolve) => {
        // DC_DEDUP_001: Use strict '>' (not '>=') so the last-synced call's timestamp
      // is not re-fetched on the next sync, preventing duplicate submissions.
      const filters = sinceTimestamp > 0
          ? [{ name: 'date', value: String(sinceTimestamp), operator: '>' }]
          : [{ name: 'date', value: String(Date.now() - 30 * 24 * 60 * 60 * 1000), operator: '>=' }];

        cordova.exec(
          (logs: any[]) => {
            console.log(`[DC_CALL_SYNC] Read ${(logs || []).length} call logs via cordova bridge`);
            resolve(logs || []);
          },
          (err: any) => {
            console.error('[DC_CALL_SYNC] CallLog plugin error:', err);
            resolve(null);
          },
          'CallLog',
          'getCallLog',
          [filters]
        );
      });
    } catch (e) {
      console.error('[DC_CALL_SYNC] Error reading native call logs:', e);
      return null;
    }
  }

  private mapCallType(nativeType: string): string {
    const type = (nativeType || '').toUpperCase();
    switch (type) {
      case '1':
      case 'INCOMING':
        return 'INCOMING';
      case '2':
      case 'OUTGOING':
        return 'OUTGOING';
      case '3':
      case 'MISSED':
        return 'MISSED';
      case '5':
      case 'REJECTED':
        return 'REJECTED';
      default:
        return 'OUTGOING';
    }
  }

  async scanAndUploadRecordings(): Promise<{ uploaded: number; skipped: number; errors: number; foldersScanned: number }> {
    if (!this.syncEnabled) {
      return { uploaded: 0, skipped: 0, errors: 0, foldersScanned: 0 };
    }

    const perms = await this.checkPermissions();
    if (!perms.storage) {
      console.warn('[DC_CALL_SYNC] Storage permission not granted - cannot scan recordings');
      return { uploaded: 0, skipped: 0, errors: 0, foldersScanned: 0 };
    }

    console.log('[DC_CALL_SYNC] Scanning for call recordings...');
    let uploaded = 0, skipped = 0, errors = 0;

    try {
      const Filesystem = this.getFilesystemPlugin();
      if (!Filesystem) {
        console.log('[DC_CALL_SYNC] Filesystem plugin not available (web mode)');
        return { uploaded, skipped, errors, foldersScanned: 0 };
      }

      if (this.detectedFolders.length === 0 && this.customFolders.length === 0) {
        await this.autoDetectFolders();
      }

      const foldersToScan = this.getActiveFolderPaths();

      if (foldersToScan.length === 0) {
        console.log('[DC_CALL_SYNC] No recording folders detected or configured');
        return { uploaded, skipped, errors, foldersScanned: 0 };
      }

      console.log(`[DC_CALL_SYNC] Scanning ${foldersToScan.length} folders: ${foldersToScan.join(', ')}`);

      const recordings: RecordingFile[] = [];

      for (const folder of foldersToScan) {
        try {
          const files = await this.scanFolderRecursive(Filesystem, folder, 0);
          for (const file of files) {
            file.folderSource = folder;
            recordings.push(file);
          }
        } catch (_e) {
          // folder may have been removed
        }
      }

      if (recordings.length === 0) {
        console.log('[DC_CALL_SYNC] No recordings found in any folder');
        return { uploaded, skipped, errors, foldersScanned: foldersToScan.length };
      }

      console.log(`[DC_CALL_SYNC] Found ${recordings.length} recording files across ${foldersToScan.length} folders`);

      const checkPayload = recordings.map(r => ({
        device_recording_id: `${r.path}_${r.lastModified}`,
        filename: r.name,
        file_size: r.size,
      }));

      const checkResponse = await apiService.post(
        API_ENDPOINTS.CALL_TRACKING.RECORDINGS_BULK_CHECK,
        checkPayload
      );

      if (!checkResponse.success || !checkResponse.data) {
        console.warn('[DC_CALL_SYNC] Bulk check failed');
        return { uploaded, skipped, errors, foldersScanned: foldersToScan.length };
      }

      const pending = (checkResponse.data as any).pending_uploads || [];
      skipped = (checkResponse.data as any).already_uploaded || 0;

      const pendingFilenames = new Set(pending.map((p: any) => p.filename));

      for (const recording of recordings) {
        if (!pendingFilenames.has(recording.name)) continue;

        try {
          const fileData = await Filesystem.readFile({
            path: recording.path,
            directory: 'EXTERNAL_STORAGE',
          });

          if (!fileData || !fileData.data) continue;

          const phoneNumber = this.extractPhoneFromFilename(recording.name);

          const formData = new FormData();
          const mimeType = this.getMimeType(recording.name);
          const blob = this.base64ToBlob(fileData.data, mimeType);
          formData.append('file', blob, recording.name);
          formData.append('device_recording_id', `${recording.path}_${recording.lastModified}`);
          formData.append('source_device', 'android');
          formData.append('recorded_at', new Date(recording.lastModified).toISOString());
          if (phoneNumber) formData.append('phone_number', phoneNumber);

          const uploadResponse = await apiService.postFormData(
            API_ENDPOINTS.CALL_TRACKING.RECORDING_UPLOAD,
            formData
          );

          if (uploadResponse.success) {
            uploaded++;
          } else {
            errors++;
          }
        } catch (e) {
          console.error(`[DC_CALL_SYNC] Upload error for ${recording.name}:`, e);
          errors++;
        }
      }

      console.log(`[DC_CALL_SYNC] Recording sync done: ${uploaded} uploaded, ${skipped} skipped, ${errors} errors`);
    } catch (e) {
      console.error('[DC_CALL_SYNC] Recording scan error:', e);
    }

    return { uploaded, skipped, errors, foldersScanned: this.getActiveFolderPaths().length };
  }

  private async scanFolderRecursive(Filesystem: any, folder: string, depth: number): Promise<RecordingFile[]> {
    if (depth > 2) return [];

    const recordings: RecordingFile[] = [];
    try {
      const result = await Filesystem.readdir({
        path: folder,
        directory: 'EXTERNAL_STORAGE',
      });

      if (!result || !result.files) return recordings;

      for (const file of result.files as any[]) {
        if (file.type === 'directory' && depth < 2) {
          const subFiles = await this.scanFolderRecursive(Filesystem, `${folder}/${file.name}`, depth + 1);
          recordings.push(...subFiles);
        } else {
          const ext = '.' + (file.name || '').split('.').pop()?.toLowerCase();
          if (AUDIO_EXTENSIONS.includes(ext)) {
            recordings.push({
              path: `${folder}/${file.name}`,
              name: file.name,
              size: file.size || 0,
              lastModified: file.mtime || Date.now(),
            });
          }
        }
      }
    } catch (_e) {}

    return recordings;
  }

  private extractPhoneFromFilename(filename: string): string {
    const patterns = [
      /(\+?\d{10,15})/,
      /(\d{3}[\-\s]?\d{3}[\-\s]?\d{4})/,
      /Call[_ ]Recording[_ ](\d{10,})/i,
      /Recording[_ ](\d{10,})/i,
      /(\d{10,})[\._\-]/,
    ];

    for (const pattern of patterns) {
      const match = filename.match(pattern);
      if (match && match[1]) {
        return match[1].replace(/[\-\s]/g, '');
      }
    }
    return '';
  }

  private getMimeType(filename: string): string {
    const ext = (filename || '').split('.').pop()?.toLowerCase() || '';
    const mimeMap: Record<string, string> = {
      'mp3': 'audio/mpeg',
      'm4a': 'audio/mp4',
      'amr': 'audio/amr',
      'wav': 'audio/wav',
      '3gp': 'audio/3gpp',
      'ogg': 'audio/ogg',
      'aac': 'audio/aac',
      'wma': 'audio/x-ms-wma',
      'opus': 'audio/opus',
      'flac': 'audio/flac',
    };
    return mimeMap[ext] || 'audio/mpeg';
  }

  private base64ToBlob(base64: string, mimeType: string): Blob {
    const byteChars = atob(base64);
    const byteArrays = [];
    for (let offset = 0; offset < byteChars.length; offset += 512) {
      const slice = byteChars.slice(offset, offset + 512);
      const byteNumbers = new Array(slice.length);
      for (let i = 0; i < slice.length; i++) {
        byteNumbers[i] = slice.charCodeAt(i);
      }
      byteArrays.push(new Uint8Array(byteNumbers));
    }
    return new Blob(byteArrays, { type: mimeType });
  }

  async fullSync(manual: boolean = false): Promise<{ calls: any; recordings: any }> {
    console.log('[DC_CALL_SYNC] Starting full sync (calls + recordings)...');
    const calls = await this.syncCallLogs(manual);
    const recordings = manual ? await this.scanAndUploadRecordingsForce() : await this.scanAndUploadRecordings();
    console.log('[DC_CALL_SYNC] Full sync complete');
    return { calls, recordings };
  }

  async scanAndUploadRecordingsForce(): Promise<{ uploaded: number; skipped: number; errors: number; foldersScanned: number }> {
    const perms = await this.checkPermissions();
    if (!perms.storage) {
      console.warn('[DC_CALL_SYNC] Storage permission not granted - cannot scan recordings');
      return { uploaded: 0, skipped: 0, errors: 0, foldersScanned: 0 };
    }

    const savedEnabled = this.syncEnabled;
    this.syncEnabled = true;
    const result = await this.scanAndUploadRecordings();
    this.syncEnabled = savedEnabled;
    return result;
  }
}

export const callSyncService = new CallSyncService();
