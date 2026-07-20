/**
 * API Service for MNR Mobile App
 * Handles all communication with the FastAPI backend
 * DC Protocol: DC_MOBILE_API_001
 * Updated: Uses networkRuntime for retry logic and offline detection
 */

import { Preferences } from '@capacitor/preferences';
import { networkRuntime } from '../runtime';
import { APP_CONFIG } from '../config/app.config';

// DC Protocol: Use centralized configuration from APP_CONFIG
const API_BASE = APP_CONFIG.API_BASE_URL;
const MEDIA_BASE = APP_CONFIG.MEDIA_BASE_URL;

const RETRY_STATUS_CODES = [408, 429, 500, 502, 503, 504];
const MAX_RETRIES = 3;
const BASE_DELAY_MS = 1000;

const STORAGE_KEY_COMPANY_ID = 'company_id';

interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  status: number;
  [key: string]: any;
}

// DC_SESSION_EXPIRY_001: Session expiration event system
type SessionExpiredListener = (endpoint: string) => void;

class ApiService {
  private token: string | null = null;
  private companyId: string | null = null;
  private sessionExpiredListeners: Set<SessionExpiredListener> = new Set();
  private sessionExpiredNotified: boolean = false;

  async init(): Promise<void> {
    // DC_BRIDGE_READY_001: Read from localStorage first (synchronous, never hangs).
    // Capacitor Preferences bridge may not be ready at startup on some Android devices.
    // All writes go to BOTH localStorage and Preferences (dual-write pattern).
    // Background sync from Preferences handles fresh installs / cleared browser storage.
    this.token = localStorage.getItem('auth_token');
    this.companyId = localStorage.getItem(STORAGE_KEY_COMPANY_ID);

    // Background sync: pull from Preferences once bridge is ready
    Promise.all([
      Preferences.get({ key: 'auth_token' }),
      Preferences.get({ key: STORAGE_KEY_COMPANY_ID })
    ]).then(([tokenResult, companyResult]) => {
      if (tokenResult.value && !this.token) {
        this.token = tokenResult.value;
        localStorage.setItem('auth_token', tokenResult.value);
      }
      if (companyResult.value && !this.companyId) {
        this.companyId = companyResult.value;
        localStorage.setItem(STORAGE_KEY_COMPANY_ID, companyResult.value);
      }
    }).catch(() => {});
  }

  async setToken(token: string): Promise<void> {
    this.token = token;
    localStorage.setItem('auth_token', token);
    Preferences.set({ key: 'auth_token', value: token }).catch(() => {});
  }

  async clearToken(): Promise<void> {
    this.token = null;
    localStorage.removeItem('auth_token');
    Preferences.remove({ key: 'auth_token' }).catch(() => {});
  }

  async getToken(): Promise<string | null> {
    if (!this.token) {
      this.token = localStorage.getItem('auth_token');
    }
    return this.token;
  }

  async setCompanyId(companyId: number | string): Promise<void> {
    this.companyId = String(companyId);
    localStorage.setItem(STORAGE_KEY_COMPANY_ID, this.companyId);
    Preferences.set({ key: STORAGE_KEY_COMPANY_ID, value: this.companyId }).catch(() => {});
  }

  async getCompanyId(): Promise<string | null> {
    if (!this.companyId) {
      this.companyId = localStorage.getItem(STORAGE_KEY_COMPANY_ID);
    }
    return this.companyId;
  }

  async clearCompanyId(): Promise<void> {
    this.companyId = null;
    localStorage.removeItem(STORAGE_KEY_COMPANY_ID);
    Preferences.remove({ key: STORAGE_KEY_COMPANY_ID }).catch(() => {});
  }

  getBaseUrl(): string {
    return API_BASE;
  }

  getMediaUrl(path: string | null | undefined): string {
    if (!path) return '';
    if (path.startsWith('http://') || path.startsWith('https://')) {
      return path;
    }
    if (path.startsWith('/')) {
      return MEDIA_BASE + path;
    }
    return MEDIA_BASE + '/' + path;
  }

  // DC_SESSION_EXPIRY_001: Session expiration handling for journey resilience
  private handleSessionExpired(endpoint: string): void {
    // Only notify once per session expiration to avoid spam
    if (this.sessionExpiredNotified) return;
    this.sessionExpiredNotified = true;
    
    console.warn(`[DC_SESSION_EXPIRY] Session expired during request to: ${endpoint}`);
    
    // Notify all listeners (journey tracking, GPS service, etc.)
    this.sessionExpiredListeners.forEach(listener => {
      try {
        listener(endpoint);
      } catch (error) {
        console.error('[DC_SESSION_EXPIRY] Listener error:', error);
      }
    });
  }

  onSessionExpired(listener: SessionExpiredListener): () => void {
    this.sessionExpiredListeners.add(listener);
    return () => this.sessionExpiredListeners.delete(listener);
  }

  resetSessionExpiredFlag(): void {
    this.sessionExpiredNotified = false;
  }

  isSessionExpired(): boolean {
    return this.sessionExpiredNotified;
  }

  private async request<T>(
    method: string,
    endpoint: string,
    body?: any,
    isFormData: boolean = false,
    retryable: boolean = true,
    timeoutMs: number = 20000
  ): Promise<ApiResponse<T>> {
    const executeRequest = async (): Promise<ApiResponse<T>> => {
      const headers: Record<string, string> = {};
      
      if (!this.token) {
        const { value } = await Preferences.get({ key: 'auth_token' });
        this.token = value;
      }
      
      if (this.token) {
        headers['Authorization'] = `Bearer ${this.token}`;
      }
      
      if (!this.companyId) {
        const { value } = await Preferences.get({ key: STORAGE_KEY_COMPANY_ID });
        this.companyId = value;
      }
      
      if (this.companyId) {
        headers['X-Company-ID'] = this.companyId;
      }
      
      // DC_APP_VERSION_001: Send app version with every request
      headers['X-App-Version'] = APP_CONFIG.getFullVersion();
      headers['X-App-Platform'] = 'mobile';
      
      if (!isFormData) {
        headers['Content-Type'] = 'application/json';
      }

      // DC_API_TIMEOUT_001: AbortController timeout — prevents requests hanging for 90+ seconds
      // when the server is unreachable (dev server down, network loss, etc.)
      const controller = new AbortController();
      const timeoutId = setTimeout(() => {
        controller.abort(`Request timed out after ${timeoutMs / 1000}s`);
      }, timeoutMs);

      const config: RequestInit = {
        method,
        headers,
        signal: controller.signal,
      };

      if (body) {
        config.body = isFormData ? body : JSON.stringify(body);
      }

      let response: Response;
      try {
        response = await fetch(`${API_BASE}${endpoint}`, config);
      } finally {
        clearTimeout(timeoutId);
      }
      
      let data;
      try {
        data = await response.json();
      } catch {
        data = null;
      }

      if (!response.ok) {
        const error: any = new Error(data?.detail || `HTTP ${response.status}`);
        error.status = response.status;
        
        if (response.status === 401) {
          this.handleSessionExpired(endpoint);
        }
        
        // DC-AGREEMENT-TYPE-001: Agreement pending interceptor for mobile
        // Emits 'mnr:agreement_pending' event so the app can show an acceptance modal.
        if (response.status === 403 && data?.detail === 'NDA_PENDING') {
          const agreementType = response.headers.get('X-Agreement-Type') || 'NDA';
          const agreementLabel = response.headers.get('X-Agreement-Label') || 'Non-Disclosure Agreement';
          const versionId = response.headers.get('X-NDA-Version-Id') || '';
          console.warn(`[DC_AGREEMENT] ${agreementLabel} acceptance required`);
          window.dispatchEvent(new CustomEvent('mnr:agreement_pending', {
            detail: { agreementType, agreementLabel, versionId }
          }));
          return {
            success: false,
            error: 'NDA_PENDING',
            status: response.status,
            data: { agreement_type: agreementType, agreement_label: agreementLabel, version_id: versionId } as any
          };
        }
        
        if (retryable && RETRY_STATUS_CODES.includes(response.status)) {
          throw error;
        }
        
        return {
          success: false,
          error: data?.detail || `HTTP ${response.status}`,
          status: response.status
        };
      }

      let extractedData = data;
      
      // DC Protocol: Check if API response explicitly indicates failure
      // Some endpoints return HTTP 200 with {success: false, message: "..."} 
      if (data && typeof data === 'object' && 'success' in data) {
        if (data.success === false) {
          return {
            success: false,
            error: data.message || data.error || 'Operation failed',
            data: data,
            status: response.status
          };
        }
        if ('data' in data) {
          extractedData = data.data;
        }
      }

      return {
        success: true,
        data: extractedData,
        status: response.status
      };
    };

    try {
      if (retryable && networkRuntime.isOnline()) {
        return await networkRuntime.withRetry(executeRequest, {
          maxRetries: MAX_RETRIES,
          baseDelayMs: BASE_DELAY_MS,
          retryOn: RETRY_STATUS_CODES,
          onRetry: (attempt, error) => {
            console.log(`[DC_MOBILE_API] Retry ${attempt} for ${endpoint}: ${error.message}`);
          }
        });
      }
      return await executeRequest();
    } catch (error: any) {
      console.error('[DC_MOBILE_API] Request error:', error);
      return {
        success: false,
        error: error.message || 'Network error',
        status: 0
      };
    }
  }

  async get<T>(endpoint: string): Promise<ApiResponse<T>> {
    return this.request<T>('GET', endpoint);
  }

  async getPublic<T>(endpoint: string): Promise<ApiResponse<T>> {
    try {
      const url = `${API_BASE}${endpoint}`;
      const response = await fetch(url, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' }
      });
      const data = await response.json();
      return {
        success: response.ok,
        data: data,
        status: response.status
      };
    } catch (error: any) {
      console.error('[DC_API] Public GET failed:', error);
      return {
        success: false,
        error: error.message || 'Network error',
        status: 0
      };
    }
  }

  async post<T>(endpoint: string, body?: any): Promise<ApiResponse<T>> {
    return this.request<T>('POST', endpoint, body);
  }

  async put<T>(endpoint: string, body?: any): Promise<ApiResponse<T>> {
    return this.request<T>('PUT', endpoint, body);
  }

  async patch<T>(endpoint: string, body?: any): Promise<ApiResponse<T>> {
    return this.request<T>('PATCH', endpoint, body);
  }

  async delete<T>(endpoint: string): Promise<ApiResponse<T>> {
    return this.request<T>('DELETE', endpoint);
  }

  async uploadFile<T>(endpoint: string, formData: FormData): Promise<ApiResponse<T>> {
    return this.request<T>('POST', endpoint, formData, true);
  }

  async fetch<T>(endpoint: string, options?: RequestInit): Promise<ApiResponse<T>> {
    const method = options?.method || 'GET';
    let body = undefined;
    if (options?.body) {
      body = typeof options.body === 'string' ? JSON.parse(options.body) : options.body;
    }
    return this.request<T>(method, endpoint, body);
  }

  // Staff Authentication
  async staffLogin(employeeId: string, password: string): Promise<ApiResponse<any>> {
    return this.post('/staff/auth/login', { employee_id: employeeId, password });
  }

  // MNR Authentication
  async mnrLogin(username: string, password: string): Promise<ApiResponse<any>> {
    return this.post('/auth/login', { username: username, password });
  }

  // Partner Authentication
  async partnerLogin(partnerCode: string, password: string): Promise<ApiResponse<any>> {
    return this.post('/partner/auth/login', { partner_code: partnerCode, password });
  }

  // Format base64 to data URL (DC_PHOTO_VALIDATION_001)
  // Preserves existing data:image/* prefixes, only adds prefix if missing
  private formatBase64ForUpload(base64: string): string {
    if (!base64) return '';
    // If already has data URL prefix, preserve it as-is
    if (base64.startsWith('data:image/')) {
      return base64;
    }
    // If raw base64, add JPEG prefix (default for Capacitor Camera)
    return `data:image/jpeg;base64,${base64}`;
  }

  // Clock In with selfie (matches ClockInRequest schema)
  async clockIn(
    latitude: number,
    longitude: number,
    accuracy_m: number,
    selfieBase64: string,
    workMode: string = 'field'
  ): Promise<ApiResponse<any>> {
    const formattedPhoto = this.formatBase64ForUpload(selfieBase64);
    return this.post('/staff/attendance/clock-in', {
      work_mode: workMode,
      location: {
        latitude,
        longitude,
        accuracy: accuracy_m
      },
      evidence: {
        photo_base64: formattedPhoto,
        gps_latitude: latitude,
        gps_longitude: longitude,
        gps_accuracy_m: accuracy_m,
        gps_source: 'mobile_app'
      },
      notes: null
    });
  }

  // Clock Out with selfie (matches ClockOutRequest schema)
  async clockOut(
    latitude: number,
    longitude: number,
    accuracy_m: number,
    selfieBase64: string
  ): Promise<ApiResponse<any>> {
    const formattedPhoto = this.formatBase64ForUpload(selfieBase64);
    return this.post('/staff/attendance/clock-out', {
      location: {
        latitude,
        longitude,
        accuracy: accuracy_m
      },
      evidence: {
        photo_base64: formattedPhoto,
        gps_latitude: latitude,
        gps_longitude: longitude,
        gps_accuracy_m: accuracy_m,
        gps_source: 'mobile_app'
      },
      notes: null
    });
  }

  // Location heartbeat
  // DC_GPS_BODY_FIX_001: Send as JSON body instead of query params
  async sendLocationHeartbeat(
    latitude: number,
    longitude: number,
    accuracy_m: number,
    battery_percentage?: number
  ): Promise<ApiResponse<any>> {
    const bodyData: Record<string, any> = {
      latitude,
      longitude,
      accuracy_m,
      source: 'mobile_heartbeat'
    };
    
    if (battery_percentage !== undefined) {
      bodyData.battery_percentage = battery_percentage;
    }
    
    return this.post('/staff/attendance/location/update', bodyData);
  }

  // DC Protocol: Journey endpoint contracts (identical to web)
  // All fields match frontend/staff_my_journeys.html exactly
  
  async startJourney(params: {
    company_id: number;
    transport_mode: string;
    purpose: string;
    purpose_description?: string;
    client_name?: string;
    location: {
      latitude: number;
      longitude: number;
      accuracy: number;
      altitude?: number;
      speed?: number;
      heading?: number;
    };
    gps_enabled: boolean;
    gps_permission_denied: boolean;
    device_info?: { userAgent: string; platform: string };
    linked_kra_id?: number;
    linked_task_id?: number;
  }): Promise<ApiResponse<any>> {
    return this.post('/staff/journeys/start', params);
  }

  async endJourney(
    journeyId: number,
    params: {
      location: {
        latitude: number;
        longitude: number;
        accuracy: number;
        altitude?: number;
        speed?: number;
        heading?: number;
      };
      notes?: string;
    }
  ): Promise<ApiResponse<any>> {
    return this.post(`/staff/journeys/${journeyId}/end`, params);
  }

  async addJourneyTrackPoint(
    journeyId: number,
    params: {
      location: {
        latitude: number;
        longitude: number;
        accuracy: number;
        altitude?: number;
        speed?: number;
        heading?: number;
        battery_percentage?: number;
        address?: string;
      };
      speed_kmh?: number;
      battery_percentage?: number;
    }
  ): Promise<ApiResponse<any>> {
    return this.post(`/staff/journeys/${journeyId}/heartbeat`, params);
  }

  // Get attendance status
  async getAttendanceStatus(): Promise<ApiResponse<any>> {
    return this.get('/staff/attendance/status');
  }

  // Get active journey
  async getActiveJourney(): Promise<ApiResponse<any>> {
    return this.get('/staff/journeys/active');
  }

  // Get staff profile
  async getStaffProfile(): Promise<ApiResponse<any>> {
    return this.get('/staff/profile');
  }

  // ============================================
  // Approval Endpoints (DC Protocol: web parity)
  // ============================================

  // Leave Approvals
  async getLeaveApprovalQueue(): Promise<ApiResponse<any>> {
    return this.get('/staff/leaves/pending-approvals/manager');
  }

  async approveLeave(requestId: number, action: 'approve' | 'reject', comment?: string): Promise<ApiResponse<any>> {
    return this.post(`/staff/leaves/approve/manager/${requestId}`, {
      action,
      comment: comment || null
    });
  }

  // KRA Manager Review
  async getKRAReviewQueue(params?: {
    employee_id?: number;
    date_from?: string;
    date_to?: string;
    status?: string;
  }): Promise<ApiResponse<any>> {
    const queryParams = new URLSearchParams();
    if (params?.employee_id) queryParams.append('employee_id', params.employee_id.toString());
    if (params?.date_from) queryParams.append('date_from', params.date_from);
    if (params?.date_to) queryParams.append('date_to', params.date_to);
    if (params?.status) queryParams.append('status', params.status);
    const queryString = queryParams.toString();
    return this.get(`/staff/kra/manager-review/pending${queryString ? '?' + queryString : ''}`);
  }

  async approveKRA(instanceId: number, rating: number, remarks?: string): Promise<ApiResponse<any>> {
    return this.post('/staff/kra/manager-review/approve', {
      instance_id: instanceId,
      rating,
      remarks: remarks || null
    });
  }

  async rejectKRA(instanceId: number, reason: string): Promise<ApiResponse<any>> {
    return this.post('/staff/kra/manager-review/reject', {
      instance_id: instanceId,
      reason
    });
  }

  // Task Manager Review
  async getTaskReviewQueue(): Promise<ApiResponse<any>> {
    return this.get('/staff/tasks/review-queue');
  }

  async approveTask(taskId: number, rating?: number, remarks?: string): Promise<ApiResponse<any>> {
    return this.post('/staff/tasks/manager-review/approve', {
      task_id: taskId,
      rating,
      remarks: remarks || null
    });
  }

  async rejectTask(taskId: number, reason: string): Promise<ApiResponse<any>> {
    return this.post('/staff/tasks/manager-review/reject', {
      task_id: taskId,
      reason
    });
  }

  // Timesheet Approvals
  async getTimesheetApprovalQueue(): Promise<ApiResponse<any>> {
    return this.get('/staff/timesheet/approval-queue');
  }

  async approveTimesheet(entryId: number): Promise<ApiResponse<any>> {
    return this.post(`/staff/timesheet/entries/${entryId}/approve`, {});
  }

  async rejectTimesheet(entryId: number, reason: string): Promise<ApiResponse<any>> {
    return this.post(`/staff/timesheet/entries/${entryId}/reject`, { reason });
  }

  // Reimbursement Approvals
  async getReimbursementApprovalQueue(): Promise<ApiResponse<any>> {
    return this.get('/staff/reimbursements/approval-queue');
  }

  async approveReimbursement(claimId: number, level: 'manager' | 'finance'): Promise<ApiResponse<any>> {
    const endpoint = level === 'manager' 
      ? `/staff/reimbursements/claims/${claimId}/manager-approve`
      : `/staff/reimbursements/claims/${claimId}/finance-approve`;
    return this.post(endpoint, {});
  }

  async rejectReimbursement(claimId: number, reason: string): Promise<ApiResponse<any>> {
    return this.post(`/staff/reimbursements/claims/${claimId}/reject`, { reason });
  }

  // ============================================
  // MNR User Endpoints (for MNR members)
  // ============================================

  // Get MNR user profile
  async getMNRProfile(): Promise<ApiResponse<any>> {
    return this.get('/users/profile');
  }

  // Get MNR wallet balance
  async getMNRWallet(): Promise<ApiResponse<any>> {
    return this.get('/users/wallet');
  }

  // Get MNR wallet summary
  async getMNRWalletSummary(): Promise<ApiResponse<any>> {
    return this.get('/users/wallet-summary');
  }

  // Get MNR dashboard data (fast)
  async getMNRDashboard(): Promise<ApiResponse<any>> {
    return this.get('/users/dashboard-data-fast');
  }

  // Get MNR earnings summary
  async getMNREarnings(): Promise<ApiResponse<any>> {
    return this.get('/users/earnings-summary');
  }

  // Get MNR income by type
  async getMNRIncome(incomeType: 'direct' | 'matching' | 'ved' | 'guru'): Promise<ApiResponse<any>> {
    return this.get(`/users/income/${incomeType}`);
  }

  // Get MNR withdrawal requests
  async getMNRWithdrawals(): Promise<ApiResponse<any>> {
    return this.get('/users/withdrawal-requests');
  }

  // Create MNR withdrawal request
  async createMNRWithdrawal(amount: number): Promise<ApiResponse<any>> {
    return this.post('/users/withdrawal-request', { amount });
  }

  // Get MNR team data
  async getMNRTeam(): Promise<ApiResponse<any>> {
    return this.get('/users/team');
  }

  // Get MNR awards
  async getMNRAwards(): Promise<ApiResponse<any>> {
    return this.get('/users/awards');
  }

  // Get MNR coupon benefits
  async getMNRBenefits(): Promise<ApiResponse<any>> {
    return this.get('/users/field-allowances');
  }

  // ============================================
  // Partner Endpoints (for partners)
  // ============================================

  // Get partner dashboard
  async getPartnerDashboard(): Promise<ApiResponse<any>> {
    return this.get('/partner/dashboard');
  }

  // Get partner orders
  async getPartnerOrders(): Promise<ApiResponse<any>> {
    return this.get('/partner/orders');
  }

  // Get partner invoices
  async getPartnerInvoices(): Promise<ApiResponse<any>> {
    return this.get('/partner/invoices');
  }

  // Get partner revenue
  async getPartnerRevenue(): Promise<ApiResponse<any>> {
    return this.get('/partner/revenue');
  }

  // Get partner profile
  async getPartnerProfile(): Promise<ApiResponse<any>> {
    return this.get('/partner/profile');
  }

  // ============================================
  // Journey Token Management
  // ============================================
  
  private journeyToken: string | null = null;

  async setJourneyToken(token: string): Promise<void> {
    this.journeyToken = token;
    await Preferences.set({ key: 'journey_token', value: token });
  }

  async clearJourneyToken(): Promise<void> {
    this.journeyToken = null;
    await Preferences.remove({ key: 'journey_token' });
  }

  async getJourneyToken(): Promise<string | null> {
    if (!this.journeyToken) {
      const { value } = await Preferences.get({ key: 'journey_token' });
      this.journeyToken = value;
    }
    return this.journeyToken;
  }

  // ============================================
  // FormData Upload Support
  // ============================================
  
  async postFormData<T>(endpoint: string, formData: FormData): Promise<ApiResponse<T>> {
    return this.request<T>('POST', endpoint, formData, true);
  }

  async putFormData<T>(endpoint: string, formData: FormData): Promise<ApiResponse<T>> {
    return this.request<T>('PUT', endpoint, formData, true);
  }
}

export const apiService = new ApiService();
