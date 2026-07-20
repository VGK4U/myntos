/**
 * MyntReal Mobile App - Main Entry Point
 * DC Protocol: DC_MOBILE_MAIN_001
 * Multi-portal support: Staff, MNR, Partner
 * Updated: Initializes Mobile Runtime Compatibility Layer
 */

import { Geolocation } from '@capacitor/geolocation';
import { Camera } from '@capacitor/camera';
import { App } from '@capacitor/app';
import { initMobileRuntime } from './runtime';
import { authService } from './services/auth.service';
import { apiService } from './services/api.service';
import { portalService } from './services/portal.service';
import { routerService, PageRoute } from './services/router.service';
import { LoginPage } from './pages/Login';
// Staff Portal Pages
import { DashboardPage } from './pages/Dashboard';
import { ProgressPage } from './pages/ProgressPage';
import { AttendancePage } from './pages/AttendancePage';
import { JourneysPage } from './pages/JourneysPage';
import { AnnouncementsPage } from './pages/AnnouncementsPage';
import { ProfilePage } from './pages/ProfilePage';
import { LeavesPage } from './pages/LeavesPage';
import { TimesheetPage } from './pages/TimesheetPage';
import { ReimbursementsPage } from './pages/ReimbursementsPage';
import { KRAsPage } from './pages/KRAsPage';
import { TasksPage } from './pages/TasksPage';
import { SettingsPage } from './pages/SettingsPage';
import { LocationHistoryPage } from './pages/LocationHistoryPage';
import { ChangePasswordPage } from './pages/ChangePasswordPage';
import { StaffKYCPage } from './pages/StaffKYCPage';
import { StaffLeadsPage } from './pages/StaffLeadsPage';
import { TeamAttendancePage } from './pages/TeamAttendancePage';
import { TeamJourneysPage } from './pages/TeamJourneysPage';
import { TeamTrackerPage } from './pages/TeamTrackerPage';
import { StaffTicketsPage } from './pages/StaffTicketsPage';
import { StaffZynovaPage } from './pages/StaffZynovaPage';
import { StaffServicePage } from './pages/StaffServicePage';
import { StaffCRMPage } from './pages/StaffCRMPage';
import { StaffCallTrackingPage } from './pages/StaffCallTrackingPage';
import { StaffMyPayoutsPage } from './pages/StaffMyPayoutsPage';
import { AutoDialerPage } from './pages/AutoDialerPage';
import { CallHistoryPage } from './pages/CallHistoryPage';
import { OperatorCallsPage } from './pages/OperatorCallsPage';
import { callSyncService } from './services/call-sync.service';
import { gpsService } from './services/gps.service';
// New Staff Dashboard Section Pages
import { StaffEmployeesPage } from './pages/StaffEmployeesPage';
import { StaffDirectoryPage } from './pages/StaffDirectoryPage';
import { StaffKYCApprovalsPage } from './pages/StaffKYCApprovalsPage';
import { StaffTrainingVideosPage } from './pages/StaffTrainingVideosPage';
import { StaffReviewPage } from './pages/StaffReviewPage';
// New Attendance Section Pages
import { StaffLeaveApprovalsPage } from './pages/StaffLeaveApprovalsPage';
import { StaffAttendanceSheetPage } from './pages/StaffAttendanceSheetPage';
import { StaffAttendanceReportsPage } from './pages/StaffAttendanceReportsPage';
import { StaffAttendanceExceptionsPage } from './pages/StaffAttendanceExceptionsPage';
import { StaffAttendanceComputationPage } from './pages/StaffAttendanceComputationPage';
// New CRM Section Pages
import { StaffLeadSourcesPage } from './pages/StaffLeadSourcesPage';
import { StaffTeamLeadsPage } from './pages/StaffTeamLeadsPage';
// New Tasks Section Pages
import { TasksAssignedPage } from './pages/TasksAssignedPage';
import { TasksReceivedPage } from './pages/TasksReceivedPage';
import { TaskDetailPage } from './pages/TaskDetailPage';
import { TaskAnalyticsPage } from './pages/TaskAnalyticsPage';
import { TaskCreatePage } from './pages/TaskCreatePage';
import { StaffTeamActivitiesPage } from './pages/StaffTeamActivitiesPage';
import { StaffTaskTrackerPage } from './pages/StaffTaskTrackerPage';
import { StaffTaskReviewsPage } from './pages/StaffTaskReviewsPage';
// New KRAs Section Pages
import { StaffKRATemplatesPage } from './pages/StaffKRATemplatesPage';
import { StaffKRATrackingPage } from './pages/StaffKRATrackingPage';
import { StaffKRAReviewPage } from './pages/StaffKRAReviewPage';
// Day Planner Section
import { DayPlannerPage } from './pages/DayPlannerPage';
// New Timesheet Section Pages
import { StaffTimesheetApprovalPage } from './pages/StaffTimesheetApprovalPage';
// New Journeys Section Pages
import { StaffAllJourneysPage } from './pages/StaffAllJourneysPage';
import { StaffVGK4UJourneysPage } from './pages/StaffVGK4UJourneysPage';
// New Location Tracking Section Pages
import { StaffAllLocationTrackerPage } from './pages/StaffAllLocationTrackerPage';
import { StaffTeamLiveTrackerPage } from './pages/StaffTeamLiveTrackerPage';
// New Reimbursement Section Pages
import { StaffReimbursementApprovalsPage } from './pages/StaffReimbursementApprovalsPage';
// Procurement Requests (accounts multi-quote workflow)
import { StaffProcurementRequestsPage } from './pages/StaffProcurementRequestsPage';
// Accounts — Vendor Master (DC_MOBILE_STAFF_VENDORS_001)
import { StaffVendorsPage } from './pages/StaffVendorsPage';
// New Service Tickets Section Pages
import { RaiseTicketPage } from './pages/RaiseTicketPage';
import { ServiceDashboardPage } from './pages/ServiceDashboardPage';
import { ServiceQueuePage } from './pages/ServiceQueuePage';
import { ServicePerformancePage } from './pages/ServicePerformancePage';
import { ServiceProcurementPage } from './pages/ServiceProcurementPage';
import { ServiceProcurementQueuePage } from './pages/ServiceProcurementQueuePage';
import { ServiceReportsPage } from './pages/ServiceReportsPage';
import { ServiceRevenuePage } from './pages/ServiceRevenuePage';
import { CreateAnnouncementPage } from './pages/CreateAnnouncementPage';
import { EditAnnouncementPage } from './pages/EditAnnouncementPage';
// MNR Portal Pages
import { MNRDashboard } from './pages/mnr/MNRDashboard';
import { MNRIncome } from './pages/mnr/MNRIncome';
import { MNRWithdrawals } from './pages/mnr/MNRWithdrawals';
import { MNRBenefits } from './pages/mnr/MNRBenefits';
import { MNRProfile } from './pages/mnr/MNRProfile';
import { MNRProfileEdit } from './pages/mnr/MNRProfileEdit';
import { MNRAwards } from './pages/mnr/MNRAwards';
import { MNRReferrals } from './pages/mnr/MNRReferrals';
import { MNRAnnouncements } from './pages/mnr/MNRAnnouncements';
import { MNRKYC } from './pages/mnr/MNRKYC';
import { MNRBankDetails } from './pages/mnr/MNRBankDetails';
import { MNRChangePassword } from './pages/mnr/MNRChangePassword';
import { MNRPoints } from './pages/mnr/MNRPoints';
import { MNRCoupons } from './pages/mnr/MNRCoupons';
import { MNRDaywiseIncome } from './pages/mnr/MNRDaywiseIncome';
import { MNREVDiscount } from './pages/mnr/MNREVDiscount';
import { MNRMyAnnouncements } from './pages/mnr/MNRMyAnnouncements';
import { MNRMyLeads } from './pages/mnr/MNRMyLeads';
import { MNRFeedback } from './pages/mnr/MNRFeedback';
import { MNRAnnouncementsPending } from './pages/mnr/MNRAnnouncementsPending';
import { MNRAnnouncementsApproved } from './pages/mnr/MNRAnnouncementsApproved';
import { MNRAnnouncementsRejected } from './pages/mnr/MNRAnnouncementsRejected';
import { MNRCouponBuy } from './pages/mnr/MNRCouponBuy';
import { MNRCouponActivate } from './pages/mnr/MNRCouponActivate';
import { MNRCouponStatus } from './pages/mnr/MNRCouponStatus';
import { MNRCouponTransfer } from './pages/mnr/MNRCouponTransfer';
import { MNRMembersAll } from './pages/mnr/MNRMembersAll';
import { MNRMembersPicture } from './pages/mnr/MNRMembersPicture';
import { MNRMembersVed } from './pages/mnr/MNRMembersVed';
import { MNREarningsSummary } from './pages/mnr/MNREarningsSummary';
import { MNRIncomeDirect, MNRIncomeMatching, MNRIncomeVed, MNRIncomeGuru, MNRIncomeField } from './pages/mnr/MNRIncomeTypes';
import { MNRAddMember } from './pages/mnr/MNRAddMember';
import { MNRFranchiseEarnings } from './pages/mnr/MNRFranchiseEarnings';
import { MNRBonanza } from './pages/mnr/MNRBonanza';
import { MNRCouponProgress } from './pages/mnr/MNRCouponProgress';
import { MNRSettings } from './pages/mnr/MNRSettings';
// VGK4U Member Portal Pages (Phase A1 read-only foundation — audit #35 follow-up)
import { VGKBirthdays } from './pages/vgk/VGKBirthdays';
import { VGKTopEarners } from './pages/vgk/VGKTopEarners';
import { VGKAwards } from './pages/vgk/VGKAwards';
import { VGKMyRegistrations } from './pages/vgk/VGKMyRegistrations';
import { VGKBonanzaRewardsPage } from './pages/vgk/VGKBonanzaRewards';
import { VGKPointsBalancePage } from './pages/vgk/VGKPointsBalance';
// VGK4U Member Portal Pages (Task #34 Phase 2 write-flow — iframe wrappers)
import { VGKFeedbackPage } from './pages/vgk/VGKFeedback';
import { VGKAnnouncementsPage } from './pages/vgk/VGKAnnouncements';
import { VGKMyAnnouncementsPage } from './pages/vgk/VGKMyAnnouncements';
import { VGKKycPage } from './pages/vgk/VGKKyc';
import { VGKBankDetailsPage } from './pages/vgk/VGKBankDetails';
import { VGKProfileEditPage } from './pages/vgk/VGKProfileEdit';
import { VGKSettingsPage } from './pages/vgk/VGKSettings';
import { VGKCouponActivatePage } from './pages/vgk/VGKCouponActivate';
import { VGKCouponProgressPage } from './pages/vgk/VGKCouponProgress';
import { VGKCouponTransferPage } from './pages/vgk/VGKCouponTransfer';
// Zynova Portal Pages
import { ZynovaRealEstate } from './pages/zynova/ZynovaRealEstate';
import { ZynovaInsurance } from './pages/zynova/ZynovaInsurance';
import { ZynovaTraining } from './pages/zynova/ZynovaTraining';
// MyntReal Portal Pages
import { MyntRealProperties } from './pages/myntreal/MyntRealProperties';
import { MyntRealEarnings } from './pages/myntreal/MyntRealEarnings';
// Partner Portal Pages
import { PartnerDashboard } from './pages/partner/PartnerDashboard';
import { PartnerOrders } from './pages/partner/PartnerOrders';
import { PartnerInvoices } from './pages/partner/PartnerInvoices';
import { PartnerRevenue } from './pages/partner/PartnerRevenue';
import { PartnerServiceTickets } from './pages/partner/PartnerServiceTickets';
import { PartnerRaiseTicket } from './pages/partner/PartnerRaiseTicket';
import { PartnerLeadsPage } from './pages/partner/PartnerLeadsPage';
import { PartnerProfile } from './pages/partner/PartnerProfile';
import { PartnerKYCDocuments } from './pages/partner/PartnerKYCDocuments';
import { PartnerSpareOrders } from './pages/partner/PartnerSpareOrders';
// Components
import { BottomTabs } from './components/BottomTabs';
import { getSideDrawer } from './components/SideDrawer';
import { sessionExpirationBanner } from './components/SessionExpirationBanner';
import { initVGKMobileAssistant } from './components/VGKMobileAssistant';
import './theme/variables.css';
import './theme/pages.css';

class MNRApp {
  private appContainer: HTMLElement;
  private pageContainer: HTMLElement;
  private tabsContainer: HTMLElement;
  private bottomTabs: BottomTabs | null = null;
  private isLoggedIn: boolean = false;
  private currentPageInstance: any = null;

  constructor() {
    this.appContainer = document.getElementById('app') || document.body;
    this.pageContainer = document.createElement('div');
    this.pageContainer.id = 'page-container';
    this.tabsContainer = document.createElement('div');
    this.tabsContainer.id = 'tabs-container';

    // DC_NUCLEAR_TIMEOUT_001: Last-resort fallback — if init() hangs OR throws
    // for ANY reason and the splash is still showing after 5s, force-show login.
    // New init architecture is synchronous so 5s is more than enough.
    const nuclearTimer = window.setTimeout(() => {
      if (this.appContainer.querySelector('.splash')) {
        console.error('[DC_APP] ⚠️ NUCLEAR TIMEOUT: init() exceeded 5s — force showing login');
        this.showLogin();
      }
    }, 5000);

    this.init()
      .catch((err: unknown) => {
        console.error('[DC_APP] init() threw unhandled error — showing login as fallback:', err);
        this.showLogin();
      })
      .finally(() => window.clearTimeout(nuclearTimer));
  }

  private injectDevServerWarning(): void {
    // DC_DEV_WARN_001: Removed — JS is served from dev server for live updates,
    // but all API calls go to mnrteam.com production backend. Banner was misleading.
  }

  private initLandscapeDetector(): void {
    // DC_ORIENT_JS_001: JS-based landscape detection — replaces unreliable CSS @media query.
    // CRITICAL: Native Capacitor is SKIPPED entirely — portrait is locked in AndroidManifest.
    // CSS @media (orientation:landscape) misfires on Capacitor WebView during init on
    // Samsung/Xiaomi devices even when phone is physically portrait — DO NOT re-add CSS rule.
    // DC_NATIVE_DETECT_002: Use layered signals — window.Capacitor may not be injected yet
    // on slower Android devices when this function runs at startup (bridge init is async).
    // Check URL scheme + Capacitor object + UA as fallback signals.
    const isNativeByUrl = window.location.protocol === 'capacitor:';
    const isNativeByObj = typeof (window as any)?.Capacitor?.isNativePlatform === 'function'
      && (window as any).Capacitor.isNativePlatform();
    const isNativeByUA = /\bwv\b|capacitor|android.*chrome\/[0-9].*mobile/i.test(navigator.userAgent)
      && window.location.protocol !== 'https:' && window.location.protocol !== 'http:';
    const isNative = isNativeByUrl || isNativeByObj || isNativeByUA;

    if (isNative) {
      // Native app: AndroidManifest portrait lock is authoritative. Never show warning.
      const warning = document.querySelector('.landscape-warning') as HTMLElement | null;
      if (warning) warning.style.display = 'none';
      console.log('[DC_APP] Native platform detected — landscape warning suppressed');
      return;
    }

    // Web/PWA only: use Screen Orientation API → matchMedia → pixel ratio (layered fallback).
    // DC_ORIENT_FIX_002: innerWidth/innerHeight alone is unreliable on budget Android WebViews
    // during the first ~500ms of load — some phones report swapped or zero dimensions.
    const warning = document.querySelector('.landscape-warning') as HTMLElement | null;
    if (!warning) return;

    const detectLandscape = (): boolean => {
      // Layer 1: Screen Orientation API — most reliable, reports physical orientation
      const oriType = (screen as any)?.orientation?.type as string | undefined;
      if (oriType) return oriType.startsWith('landscape');

      // Layer 2: matchMedia — respects browser viewport orientation correctly
      if (window.matchMedia) {
        return window.matchMedia('(orientation: landscape)').matches;
      }

      // Layer 3: pixel ratio guard — require strict ratio + height threshold
      // innerWidth > innerHeight alone can fire falsely during WebView init
      const ratio = window.innerWidth / (window.innerHeight || 1);
      return ratio > 1.3 && window.innerHeight < 500;
    };

    let debounceTimer: ReturnType<typeof setTimeout> | null = null;

    const updateWarning = () => {
      warning.style.display = detectLandscape() ? 'flex' : 'none';
    };

    const debouncedUpdate = () => {
      if (debounceTimer) clearTimeout(debounceTimer);
      debounceTimer = setTimeout(updateWarning, 250);
    };

    window.addEventListener('resize', debouncedUpdate, { passive: true });
    window.addEventListener('orientationchange', debouncedUpdate, { passive: true });

    // Initial check after 600ms — gives Android WebView time to settle viewport dimensions
    setTimeout(updateWarning, 600);
    console.log('[DC_APP] Landscape detector initialized (web-only, layered detection)');
  }

  private async init(): Promise<void> {
    console.log('[DC_APP] Initializing MyntReal Mobile App');

    // ─── PHASE 1: SYNCHRONOUS SETUP (zero bridge calls, instant) ───────────────
    this.injectDevServerWarning();
    this.initLandscapeDetector();
    this.applyThemePreference();

    // ─── PHASE 2: REGISTER WINDOW / ROUTER EVENTS (no bridge calls) ───────────
    this.registerEventListeners();

    // ─── PHASE 3: READ AUTH STATE FROM LOCALSTORAGE (synchronous, instant) ─────
    // DC_FAST_PATH_001: Never await Capacitor bridge calls before showing UI.
    // localStorage is always available and never hangs. All writes use dual-write
    // (localStorage + Preferences) so auth state is always in localStorage.
    let isLoggedIn = false;
    const rawAuthState = localStorage.getItem('mnr_auth_state');
    if (rawAuthState) {
      try {
        const restored = JSON.parse(rawAuthState);
        const tokenExpired = restored.isLoggedIn
          && restored.tokenExpiresAt > 0
          && Date.now() >= restored.tokenExpiresAt;
        isLoggedIn = restored.isLoggedIn === true && !tokenExpired;
        // Sync in-memory state on authService without any bridge calls
        if (isLoggedIn) {
          await authService.init();
          await portalService.init();
        }
      } catch {
        isLoggedIn = false;
      }
    }

    this.isLoggedIn = isLoggedIn;

    // ─── PHASE 4: SHOW UI IMMEDIATELY ──────────────────────────────────────────
    if (this.isLoggedIn) {
      this.showApp();
    } else {
      gpsService.cleanup().catch(() => {});
      this.showLogin();
    }

    // ─── PHASE 5: BRIDGE INIT IN BACKGROUND (never blocks UI) ─────────────────
    // DC_BRIDGE_DEFERRED_001: All Capacitor plugin initialization happens AFTER
    // the login/app page is already rendered and interactive.
    setTimeout(() => {
      initMobileRuntime().catch(e =>
        console.warn('[DC_APP] Background runtime init error:', e)
      );

      this.requestStartupPermissions().catch(e =>
        console.warn('[DC_APP] Background permission request error:', e)
      );

      if (this.isLoggedIn) {
        try {
          const isNative = typeof (window as any)?.Capacitor?.isNativePlatform === 'function'
            && (window as any).Capacitor.isNativePlatform();
          if (isNative) {
            if (callSyncService && typeof callSyncService.init === 'function') {
              callSyncService.init().catch(e => console.warn('[DC_APP] CallSync init error:', e));
            }
            this.verifyTrackingState().catch(e =>
              console.warn('[DC_APP] Tracking state check error:', e)
            );
          }
        } catch (e) {
          console.warn('[DC_APP] Native init skipped (web context):', e);
        }
      }
    }, 100);

    console.log('[DC_APP] App initialized — UI shown immediately, bridge init deferred');
  }

  private registerEventListeners(): void {
    window.addEventListener('login-success', () => {
      this.isLoggedIn = true;
      this.showApp();
      // Start bridge init now that user is logged in
      initMobileRuntime().catch(() => {});
    });

    window.addEventListener('logout', () => {
      this.isLoggedIn = false;
      localStorage.removeItem('mnr_current_route');
      localStorage.removeItem('mnr_pre_expiry_route');
      routerService.reset();
      gpsService.cleanup().catch(() => {});
      this.showLogin();
    });

    window.addEventListener('session-expired', () => {
      console.log('[DC_APP] Session expired event received');
      if (this.isLoggedIn) {
        const currentRoute = routerService.getCurrentRoute();
        const portalDashboards: PageRoute[] = ['dashboard', 'mnr-dashboard', 'partner-dashboard'];
        if (!portalDashboards.includes(currentRoute)) {
          localStorage.setItem('mnr_pre_expiry_route', currentRoute);
        }
        sessionExpirationBanner.show();
      }
    });

    window.addEventListener('auth-token-expired', () => {
      console.log('[DC_APP] Auth token expired event received');
      if (this.isLoggedIn) {
        const currentRoute = routerService.getCurrentRoute();
        const portalDashboards: PageRoute[] = ['dashboard', 'mnr-dashboard', 'partner-dashboard'];
        if (!portalDashboards.includes(currentRoute)) {
          localStorage.setItem('mnr_pre_expiry_route', currentRoute);
        }
        sessionExpirationBanner.show();
      }
    });

    // DC-AGREEMENT-TYPE-001: Global handler for staff agreement gate (NDA + Employment Agreement)
    window.addEventListener('mnr:agreement_pending', (e: Event) => {
      const { agreementType, agreementLabel } = (e as CustomEvent).detail || {};
      this.showAgreementModal(agreementType || 'NDA', agreementLabel || 'Non-Disclosure Agreement');
    });

    App.addListener('backButton', () => {
      const currentRoute = routerService.getCurrentRoute();
      const portalDashboards: PageRoute[] = ['dashboard', 'mnr-dashboard', 'partner-dashboard'];
      if (portalDashboards.includes(currentRoute)) {
        App.minimizeApp();
      } else {
        if (!routerService.goBack()) {
          const authState = authService.getAuthState();
          const portal = authState.user?.portal || 'staff';
          const homeRoute: PageRoute = portal === 'mnr' ? 'mnr-dashboard'
            : portal === 'partner' ? 'partner-dashboard' : 'dashboard';
          routerService.navigate(homeRoute);
        }
      }
    });

    App.addListener('appStateChange', async ({ isActive }) => {
      if (!isActive) {
        await authService.markAppClosed();
        console.log('[DC_APP] App moved to background');
      } else {
        const offlineData = await authService.getOfflineTime();
        if (offlineData.wasOffline && offlineData.offlineMinutes > 0) {
          window.dispatchEvent(new CustomEvent('app-resumed-from-background', {
            detail: { offlineMinutes: offlineData.offlineMinutes }
          }));
        }
      }
    });

    routerService.onRouteChange((route) => {
      if (this.isLoggedIn) {
        authService.updateActivity();
        localStorage.setItem('mnr_current_route', route);
        this.renderPage(route);
        this.bottomTabs?.render();
      }
    });
  }

  /**
   * DC_THEME_001: Apply saved theme preference from localStorage
   */
  private applyThemePreference(): void {
    const savedTheme = localStorage.getItem('mnr_theme_preference') || 'dark';
    document.body.classList.remove('dark-theme', 'light-theme');
    document.body.classList.add(`${savedTheme}-theme`);
    console.log('[DC_APP] Theme applied:', savedTheme);
  }

  private async verifyTrackingState(): Promise<void> {
    try {
      const isNativeTracking = await gpsService.isNativeTrackingActive();
      if (!isNativeTracking) {
        console.log('[DC_APP] No orphaned native tracking detected');
        return;
      }

      console.log('[DC_APP] Native tracking is running — verifying clock-in status...');
      const response = await apiService.get<any>('/staff/attendance/today');
      const isClockedIn = response?.data?.is_clocked_in === true && !response?.data?.clock_out;

      if (!isClockedIn) {
        console.log('[DC_APP] Staff is NOT clocked in — stopping orphaned GPS tracking');
        await gpsService.cleanup();
      } else {
        console.log('[DC_APP] Staff IS clocked in — GPS tracking is valid');
        gpsService.setClockedIn(true);
      }
    } catch (error) {
      console.warn('[DC_APP] Could not verify tracking state, stopping as precaution:', error);
      await gpsService.cleanup();
    }
  }

  /**
   * DC_MOBILE_PERMISSIONS_001: Request ALL permissions at app startup (one-time)
   * Covers: Camera, Location, Call Log, Storage/Audio, Phone State
   * Once granted, these persist permanently — no repeat prompts
   * Note: Only runs on native platforms, skipped on web
   */
  private async requestStartupPermissions(): Promise<void> {
    const { Capacitor } = await import('@capacitor/core');
    
    if (!Capacitor.isNativePlatform()) {
      console.log('[DC_APP] Running on web - skipping native permission requests');
      return;
    }
    
    console.log('[DC_APP] Requesting ALL startup permissions (one-time)...');
    
    try {
      const { permissionsRuntime } = await import('./runtime/permissions');
      await permissionsRuntime.init();
      const allStatuses = await permissionsRuntime.requestAllPermissions();
      
      const grantedCount = [
        allStatuses.camera,
        allStatuses.location,
        allStatuses.callLog,
        allStatuses.storage,
        allStatuses.phoneState
      ].filter(s => s === 'granted').length;
      
      console.log(`[DC_APP] Permissions granted: ${grantedCount}/5`);
      console.log(`[DC_APP]   Camera: ${allStatuses.camera}`);
      console.log(`[DC_APP]   Location: ${allStatuses.location}`);
      console.log(`[DC_APP]   Call Log: ${allStatuses.callLog}`);
      console.log(`[DC_APP]   Storage: ${allStatuses.storage}`);
      console.log(`[DC_APP]   Phone State: ${allStatuses.phoneState}`);
      
      if (grantedCount === 5) {
        console.log('[DC_APP] All permissions granted successfully');
      } else {
        console.warn('[DC_APP] Some permissions not granted - some features may be limited');
      }
    } catch (error) {
      console.error('[DC_APP] Permission request error:', error);
      try {
        const cameraPermission = await Camera.requestPermissions();
        console.log('[DC_APP] Fallback - Camera permission:', cameraPermission.camera);
        const locationPermission = await Geolocation.requestPermissions();
        console.log('[DC_APP] Fallback - Location permission:', locationPermission.location);
      } catch (fallbackError) {
        console.error('[DC_APP] Fallback permission request also failed:', fallbackError);
      }
    }
  }

  private showLogin(): void {
    this.appContainer.innerHTML = '';
    this.appContainer.appendChild(this.pageContainer);
    const loginPage = new LoginPage(this.pageContainer);
    loginPage.init();
  }

  private showApp(): void {
    this.appContainer.innerHTML = '';
    this.appContainer.className = 'app-layout';
    this.appContainer.appendChild(this.pageContainer);
    this.appContainer.appendChild(this.tabsContainer);
    
    this.bottomTabs = new BottomTabs(this.tabsContainer);
    this.bottomTabs.render();
    
    getSideDrawer();
    initVGKMobileAssistant();

    // DC_SESSION_EXPIRY_001: Initialize global session expiration banner
    sessionExpirationBanner.init();
    
    const authState = authService.getAuthState();
    const portal = authState.user?.portal || 'staff';
    routerService.reset(portal);
    
    const savedRoute = localStorage.getItem('mnr_pre_expiry_route') as PageRoute | null
      || localStorage.getItem('mnr_current_route') as PageRoute | null;
    localStorage.removeItem('mnr_pre_expiry_route');
    if (savedRoute) {
      const routeConfig = routerService.getRouteConfig(savedRoute);
      if (routeConfig && (!routeConfig.portal || routeConfig.portal === portal)) {
        console.log('[DC_APP] Restoring route:', savedRoute);
        routerService.navigate(savedRoute);
      }
    }
    
    this.renderPage(routerService.getCurrentRoute());
  }

  private async renderPage(route: PageRoute): Promise<void> {
    if (this.currentPageInstance && typeof this.currentPageInstance.cleanup === 'function') {
      try {
        this.currentPageInstance.cleanup();
      } catch (e) {
        console.warn('[DC_APP] Page cleanup error:', e);
      }
    }
    this.currentPageInstance = null;

    this.pageContainer.innerHTML = '<div class="loading-state">Loading...</div>';

    let page: any;

    switch (route) {
      // Staff Portal Pages
      case 'dashboard':
        page = new DashboardPage(this.pageContainer);
        break;
      case 'progress':
        page = new ProgressPage(this.pageContainer);
        break;
      case 'attendance':
        page = new AttendancePage(this.pageContainer);
        break;
      case 'journeys':
        page = new JourneysPage(this.pageContainer);
        break;
      case 'announcements':
        page = new AnnouncementsPage(this.pageContainer);
        break;
      case 'profile':
        page = new ProfilePage(this.pageContainer);
        break;
      case 'leaves':
        page = new LeavesPage(this.pageContainer);
        break;
      case 'timesheet':
        page = new TimesheetPage(this.pageContainer);
        break;
      case 'reimbursements':
        page = new ReimbursementsPage(this.pageContainer);
        break;
      case 'kras':
        page = new KRAsPage(this.pageContainer);
        break;
      case 'tasks':
        page = new TasksPage(this.pageContainer);
        break;
      case 'settings':
        page = new SettingsPage(this.pageContainer);
        break;
      case 'location-history':
        page = new LocationHistoryPage(this.pageContainer);
        break;
      case 'change-password':
        page = new ChangePasswordPage(this.pageContainer);
        break;
      case 'staff-kyc':
        page = new StaffKYCPage(this.pageContainer);
        break;
      case 'staff-leads':
        page = new StaffLeadsPage(this.pageContainer);
        break;
      case 'team-attendance':
        page = new TeamAttendancePage(this.pageContainer);
        break;
      case 'team-journeys':
        page = new TeamJourneysPage(this.pageContainer);
        break;
      case 'team-tracker':
        page = new TeamTrackerPage(this.pageContainer);
        break;
      case 'tickets':
        page = new StaffTicketsPage(this.pageContainer);
        break;
      case 'staff-zynova':
      case 'staff-zynova-real-estate':
      case 'staff-zynova-insurance':
        page = new StaffZynovaPage(this.pageContainer);
        break;
      case 'staff-service':
        page = new ServiceDashboardPage(this.pageContainer);
        break;
      case 'staff-tickets':
        page = new RaiseTicketPage(this.pageContainer);
        break;
      case 'staff-crm':
        page = new StaffCRMPage(this.pageContainer);
        break;
      case 'staff-my-payouts':
      case 'staff-my-lead-incentives':
        page = new StaffMyPayoutsPage(this.pageContainer);
        break;
      case 'staff-call-tracking':
        page = new StaffCallTrackingPage(this.pageContainer);
        break;
      case 'auto-dialer':
        page = new AutoDialerPage(this.pageContainer);
        break;
      case 'call-history':
        page = new CallHistoryPage(this.pageContainer);
        break;
      case 'operator-calls':
        page = new OperatorCallsPage(this.pageContainer);
        break;
      case 'staff-team-leads':
        page = new StaffTeamLeadsPage(this.pageContainer);
        break;
      
      // New Staff Dashboard Section Pages
      case 'staff-employees':
        page = new StaffEmployeesPage(this.pageContainer);
        break;
      case 'staff-directory':
        page = new StaffDirectoryPage(this.pageContainer);
        break;
      case 'staff-training-videos':
        page = new StaffTrainingVideosPage(this.pageContainer);
        break;
      case 'staff-kyc-approvals':
        page = new StaffKYCApprovalsPage(this.pageContainer);
        break;
      case 'staff-review':
        page = new StaffReviewPage(this.pageContainer);
        break;
      
      // New Attendance Section Pages
      case 'staff-leave-approvals':
        page = new StaffLeaveApprovalsPage(this.pageContainer);
        break;
      case 'staff-attendance-sheet':
        page = new StaffAttendanceSheetPage(this.pageContainer);
        break;
      case 'staff-attendance-reports':
        page = new StaffAttendanceReportsPage(this.pageContainer);
        break;
      case 'staff-attendance-exceptions':
        page = new StaffAttendanceExceptionsPage(this.pageContainer);
        break;
      case 'staff-attendance-computation':
        page = new StaffAttendanceComputationPage(this.pageContainer);
        break;
      
      // New CRM Section Pages
      case 'staff-lead-sources':
        page = new StaffLeadSourcesPage(this.pageContainer);
        break;

      // Accounts Section
      case 'staff-vendors':
        page = new StaffVendorsPage(this.pageContainer);
        break;
      
      // New Tasks Section Pages
      case 'tasks-assigned':
        page = new TasksAssignedPage(this.pageContainer);
        break;
      case 'tasks-received':
        page = new TasksReceivedPage(this.pageContainer);
        break;
      case 'task-detail':
        page = new TaskDetailPage(this.pageContainer, routerService.getRouteParams());
        break;
      case 'task-create':
        page = new TaskCreatePage(this.pageContainer);
        break;
      case 'task-analytics':
        page = new TaskAnalyticsPage(this.pageContainer);
        break;
      case 'staff-team-activities':
        page = new StaffTeamActivitiesPage(this.pageContainer);
        break;
      case 'staff-task-tracker':
        page = new StaffTaskTrackerPage(this.pageContainer);
        break;
      case 'staff-task-reviews':
        page = new StaffTaskReviewsPage(this.pageContainer);
        break;
      
      // New KRAs Section Pages
      case 'staff-kra-templates':
        page = new StaffKRATemplatesPage(this.pageContainer);
        break;
      case 'staff-kra-tracking':
        page = new StaffKRATrackingPage(this.pageContainer);
        break;
      case 'staff-kra-review':
        page = new StaffKRAReviewPage(this.pageContainer);
        break;
      
      // Day Planner Section
      case 'day-planner':
        page = new DayPlannerPage(this.pageContainer);
        break;
      
      // New Timesheet Section Pages
      case 'staff-timesheet-approval':
        page = new StaffTimesheetApprovalPage(this.pageContainer);
        break;
      
      // New Journeys Section Pages
      case 'staff-all-journeys':
        page = new StaffAllJourneysPage(this.pageContainer);
        break;
      case 'staff-vgk4u-journeys':
        page = new StaffVGK4UJourneysPage(this.pageContainer);
        break;
      
      // New Location Tracking Section Pages
      case 'staff-all-location-tracker':
        page = new StaffAllLocationTrackerPage(this.pageContainer);
        break;
      case 'staff-team-live-tracker':
        page = new StaffTeamLiveTrackerPage(this.pageContainer);
        break;
      
      // New Reimbursement Section Pages
      case 'staff-reimbursement-approvals':
        page = new StaffReimbursementApprovalsPage(this.pageContainer);
        break;
      // Procurement Requests (accounts multi-quote workflow)
      case 'staff-procurement-requests':
        page = new StaffProcurementRequestsPage(this.pageContainer);
        break;
      
      // New Service Tickets Section Pages
      case 'staff-service-performance':
        page = new ServicePerformancePage(this.pageContainer);
        break;
      case 'staff-service-procurement':
        page = new ServiceProcurementPage(this.pageContainer);
        break;
      case 'staff-service-procurement-queue':
        page = new ServiceProcurementQueuePage(this.pageContainer);
        break;
      case 'staff-service-reports':
        page = new ServiceReportsPage(this.pageContainer);
        break;
      case 'staff-service-queue':
        page = new ServiceQueuePage(this.pageContainer);
        break;
      case 'staff-service-revenue':
        page = new ServiceRevenuePage(this.pageContainer);
        break;

      // Announcements Pages
      case 'create-announcement':
        page = new CreateAnnouncementPage(this.pageContainer);
        break;
      case 'edit-announcement':
        page = new EditAnnouncementPage(this.pageContainer);
        break;
      
      // MNR Portal Pages
      case 'mnr-dashboard':
        page = new MNRDashboard(this.pageContainer);
        break;
      case 'mnr-income':
      case 'mnr-earnings':
        page = new MNRIncome(this.pageContainer);
        break;
      case 'mnr-withdrawals':
        page = new MNRWithdrawals(this.pageContainer);
        break;
      case 'mnr-benefits':
        page = new MNRBenefits(this.pageContainer);
        break;
      case 'mnr-profile':
        page = new MNRProfile(this.pageContainer);
        break;
      case 'mnr-profile-edit':
        page = new MNRProfileEdit(this.pageContainer);
        break;
      case 'mnr-kyc':
        page = new MNRKYC(this.pageContainer);
        break;
      case 'mnr-bank':
        page = new MNRBankDetails(this.pageContainer);
        break;
      case 'mnr-awards':
        page = new MNRAwards(this.pageContainer);
        break;
      case 'vgk-member-hub':
        // Member Hub removed — redirect to dashboard
        routerService.navigate('dashboard');
        return;
      case 'mnr-referrals':
      case 'mnr-team':
        page = new MNRReferrals(this.pageContainer);
        break;
      case 'mnr-announcements':
        page = new MNRAnnouncements(this.pageContainer);
        break;
      case 'mnr-change-password':
        page = new MNRChangePassword(this.pageContainer);
        break;
      case 'mnr-points':
        page = new MNRPoints(this.pageContainer);
        break;
      case 'mnr-coupons':
        page = new MNRCoupons(this.pageContainer);
        break;
      case 'mnr-daywise':
        page = new MNRDaywiseIncome(this.pageContainer);
        break;
      case 'mnr-ev-discount':
        page = new MNREVDiscount(this.pageContainer);
        break;
      case 'mnr-my-announcements':
        page = new MNRMyAnnouncements(this.pageContainer);
        break;
      case 'mnr-my-leads':
        page = new MNRMyLeads(this.pageContainer);
        break;
      case 'mnr-feedback':
        page = new MNRFeedback(this.pageContainer);
        break;
      case 'mnr-add-member':
        page = new MNRAddMember(this.pageContainer);
        break;
      case 'mnr-announcements-pending':
        page = new MNRAnnouncementsPending(this.pageContainer);
        break;
      case 'mnr-announcements-approved':
        page = new MNRAnnouncementsApproved(this.pageContainer);
        break;
      case 'mnr-announcements-rejected':
        page = new MNRAnnouncementsRejected(this.pageContainer);
        break;
      case 'mnr-create-announcement':
        page = new CreateAnnouncementPage(this.pageContainer);
        break;
      case 'mnr-coupon-buy':
        page = new MNRCouponBuy(this.pageContainer);
        break;
      case 'mnr-coupon-activate':
        page = new MNRCouponActivate(this.pageContainer);
        break;
      case 'mnr-coupon-status':
        page = new MNRCouponStatus(this.pageContainer);
        break;
      case 'mnr-coupon-transfer':
        page = new MNRCouponTransfer(this.pageContainer);
        break;
      case 'mnr-coupon-progress':
        page = new MNRCouponProgress(this.pageContainer);
        break;
      case 'mnr-settings':
        page = new MNRSettings(this.pageContainer);
        break;
      case 'mnr-members-all':
        page = new MNRMembersAll(this.pageContainer);
        break;
      case 'mnr-members-picture':
        page = new MNRMembersPicture(this.pageContainer);
        break;
      case 'mnr-members-ved':
        page = new MNRMembersVed(this.pageContainer);
        break;
      case 'mnr-earnings-summary':
        page = new MNREarningsSummary(this.pageContainer);
        break;
      case 'mnr-income-direct':
        page = new MNRIncomeDirect(this.pageContainer);
        break;
      case 'mnr-income-matching':
        page = new MNRIncomeMatching(this.pageContainer);
        break;
      case 'mnr-income-ved':
        page = new MNRIncomeVed(this.pageContainer);
        break;
      case 'mnr-income-guru':
        page = new MNRIncomeGuru(this.pageContainer);
        break;
      case 'mnr-income-field':
        page = new MNRIncomeField(this.pageContainer);
        break;
      case 'mnr-franchise-earnings':
        page = new MNRFranchiseEarnings(this.pageContainer);
        break;
      case 'mnr-bonanza':
        page = new MNRBonanza(this.pageContainer);
        break;
      
      // VGK4U Member Portal Pages (Phase A1 read-only foundation)
      case 'vgk-birthdays':
        page = new VGKBirthdays(this.pageContainer);
        break;
      case 'vgk-top-earners':
        page = new VGKTopEarners(this.pageContainer);
        break;
      case 'vgk-awards':
        page = new VGKAwards(this.pageContainer);
        break;
      case 'vgk-my-registrations':
        page = new VGKMyRegistrations(this.pageContainer);
        break;
      case 'vgk-bonanza-rewards':
        page = new VGKBonanzaRewardsPage(this.pageContainer);
        break;
      case 'vgk-points-balance':
        page = new VGKPointsBalancePage(this.pageContainer);
        break;

      // Task #34 — VGK4U Member Parity Phase 2 (Write-Flow iframe wrappers)
      case 'vgk-feedback':
        page = new VGKFeedbackPage(this.pageContainer);
        break;
      case 'vgk-announcements':
        page = new VGKAnnouncementsPage(this.pageContainer);
        break;
      case 'vgk-my-announcements':
        page = new VGKMyAnnouncementsPage(this.pageContainer);
        break;
      case 'vgk-kyc':
        page = new VGKKycPage(this.pageContainer);
        break;
      case 'vgk-bank-details':
        page = new VGKBankDetailsPage(this.pageContainer);
        break;
      case 'vgk-profile-edit':
        page = new VGKProfileEditPage(this.pageContainer);
        break;
      case 'vgk-settings':
        page = new VGKSettingsPage(this.pageContainer);
        break;
      case 'vgk-coupon-activate':
        page = new VGKCouponActivatePage(this.pageContainer);
        break;
      case 'vgk-coupon-progress':
        page = new VGKCouponProgressPage(this.pageContainer);
        break;
      case 'vgk-coupon-transfer':
        page = new VGKCouponTransferPage(this.pageContainer);
        break;

      // Zynova Portal Pages
      case 'zynova-real-estate':
        page = new ZynovaRealEstate(this.pageContainer);
        break;
      case 'zynova-insurance':
        page = new ZynovaInsurance(this.pageContainer);
        break;
      case 'zynova-training':
        page = new ZynovaTraining(this.pageContainer);
        break;
      
      // MyntReal Portal Pages
      case 'myntreal-properties':
        page = new MyntRealProperties(this.pageContainer);
        break;
      case 'myntreal-earnings':
        page = new MyntRealEarnings(this.pageContainer);
        break;
      
      // Partner Portal Pages
      case 'partner-dashboard':
        page = new PartnerDashboard(this.pageContainer);
        break;
      case 'partner-orders':
        page = new PartnerOrders(this.pageContainer);
        break;
      case 'partner-invoices':
        page = new PartnerInvoices(this.pageContainer);
        break;
      case 'partner-revenue':
      case 'partner-payments':
        page = new PartnerRevenue(this.pageContainer);
        break;
      case 'partner-leads':
        page = new PartnerLeadsPage(this.pageContainer);
        break;
      case 'partner-profile':
        page = new PartnerProfile(this.pageContainer);
        break;
      case 'partner-kyc-documents':
        page = new PartnerKYCDocuments(this.pageContainer);
        break;
      case 'partner-spare-orders':
        page = new PartnerSpareOrders(this.pageContainer);
        break;
      case 'partner-service':
      case 'partner-ticket-history':
        page = new PartnerServiceTickets(this.pageContainer);
        break;
      case 'partner-raise-ticket':
        page = new PartnerRaiseTicket(this.pageContainer);
        break;
      case 'partner-new-order':
        page = new PartnerOrders(this.pageContainer);
        break;
      
      default:
        this.pageContainer.innerHTML = `
          <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:60vh;padding:24px;text-align:center;">
            <i class="fas fa-exclamation-circle" style="font-size:48px;color:#ef4444;margin-bottom:16px;"></i>
            <h3 style="color:#fff;margin:0 0 8px;">Page Not Found</h3>
            <p style="color:rgba(255,255,255,0.6);margin:0 0 20px;">The page "${route}" could not be loaded.</p>
            <button onclick="window.routerService?.navigate(window.routerService?.currentRoute?.startsWith('partner-') ? 'partner-dashboard' : 'dashboard')" style="background:#6366f1;color:#fff;border:none;padding:12px 24px;border-radius:8px;font-size:14px;cursor:pointer;">Go to Home</button>
          </div>`;
        return;
    }

    try {
      await page.init();
      this.currentPageInstance = page;
    } catch (error: any) {
      console.error(`[MNRApp] Page init failed for route "${route}":`, error);
      const isAuthError = error?.status === 401 || error?.message?.includes('401') || apiService.isSessionExpired();
      if (isAuthError) {
        sessionExpirationBanner.show();
        this.pageContainer.innerHTML = `
          <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:60vh;padding:24px;text-align:center;">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2" style="margin-bottom:16px;">
              <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            <h3 style="color:#fff;margin:0 0 8px;">Session Expired</h3>
            <p style="color:rgba(255,255,255,0.6);margin:0 0 20px;">Please login again to continue using this page.</p>
            <button onclick="window.routerService?.navigate('${route}')" style="background:#6366f1;color:#fff;border:none;padding:12px 24px;border-radius:8px;font-size:14px;cursor:pointer;">Retry After Login</button>
          </div>`;
      } else {
        this.pageContainer.innerHTML = `
          <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:60vh;padding:24px;text-align:center;">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2" style="margin-bottom:16px;">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
            </svg>
            <h3 style="color:#fff;margin:0 0 8px;">Failed to Load Page</h3>
            <p style="color:rgba(255,255,255,0.6);margin:0 0 8px;">Something went wrong while loading this page.</p>
            <p style="color:rgba(255,255,255,0.4);font-size:12px;margin:0 0 20px;">${error?.message || 'Unknown error'}</p>
            <div style="display:flex;gap:12px;">
              <button onclick="window.routerService?.navigate('${route}')" style="background:#6366f1;color:#fff;border:none;padding:12px 24px;border-radius:8px;font-size:14px;cursor:pointer;">Retry</button>
              <button onclick="window.routerService?.goBack()" style="background:rgba(255,255,255,0.1);color:#fff;border:none;padding:12px 24px;border-radius:8px;font-size:14px;cursor:pointer;">Go Back</button>
            </div>
          </div>`;
      }
    }
  }

  // DC-AGREEMENT-TYPE-001: Global agreement acceptance modal (NDA + Employment Agreement)
  private async showAgreementModal(agreementType: string, agreementLabel: string): Promise<void> {
    const MODAL_ID = 'dc-agreement-modal';
    if (document.getElementById(MODAL_ID)) return;

    const isEmployment = agreementType === 'EMPLOYMENT';
    const headerBg = isEmployment
      ? 'linear-gradient(135deg,#065f46 0%,#059669 100%)'
      : 'linear-gradient(135deg,#1a237e 0%,#3949ab 100%)';
    const headerIcon = isEmployment ? '📝' : '📄';

    // Loading placeholder
    const overlay = document.createElement('div');
    overlay.id = MODAL_ID;
    overlay.style.cssText = [
      'position:fixed;inset:0;background:rgba(0,0,0,0.92);display:flex;align-items:center',
      'justify-content:center;z-index:999999;padding:16px;backdrop-filter:blur(4px)',
    ].join(';');
    overlay.innerHTML = `
      <div style="background:#fff;border-radius:16px;width:100%;max-width:540px;max-height:90vh;display:flex;flex-direction:column;overflow:hidden;box-shadow:0 20px 48px rgba(0,0,0,0.5)">
        <div style="background:${headerBg};color:#fff;padding:20px 22px;display:flex;align-items:center;gap:14px;flex-shrink:0">
          <span style="font-size:2rem">${headerIcon}</span>
          <div>
            <div style="font-size:16px;font-weight:700">${agreementLabel} Required</div>
            <div style="font-size:12px;opacity:.85;margin-top:2px">Review and accept to continue</div>
          </div>
        </div>
        <div id="dc-agreement-body" style="flex:1;overflow-y:auto;padding:20px;background:#f8f9fa">
          <div style="text-align:center;padding:40px;color:#6b7280">
            <div style="font-size:24px;margin-bottom:12px">⏳</div>
            <div style="font-size:14px">Loading ${agreementLabel}…</div>
          </div>
        </div>
        <div style="padding:16px 20px;background:#fff;border-top:1px solid #e5e7eb;flex-shrink:0">
          <div style="background:#fff3e0;color:#b45309;padding:10px 14px;border-radius:8px;font-size:12px;margin-bottom:14px;display:flex;align-items:center;gap:8px">
            <span>⚠️</span><span>You must accept the ${agreementLabel} to access the system.</span>
          </div>
          <div style="display:flex;gap:10px;justify-content:flex-end">
            <button id="dc-agreement-logout" style="padding:11px 22px;background:#f5f5f5;color:#374151;border:none;border-radius:8px;font-size:14px;font-weight:600;cursor:pointer">
              Sign Out
            </button>
            <button id="dc-agreement-accept" style="padding:11px 22px;background:#16a34a;color:#fff;border:none;border-radius:8px;font-size:14px;font-weight:700;cursor:pointer" disabled>
              I Accept
            </button>
          </div>
        </div>
      </div>`;
    document.body.appendChild(overlay);
    document.body.style.overflow = 'hidden';

    const acceptBtn = document.getElementById('dc-agreement-accept') as HTMLButtonElement;
    const logoutBtn = document.getElementById('dc-agreement-logout') as HTMLButtonElement;
    const bodyEl   = document.getElementById('dc-agreement-body') as HTMLElement;

    logoutBtn.onclick = () => {
      overlay.remove();
      document.body.style.overflow = '';
      window.dispatchEvent(new Event('logout'));
    };

    // Fetch agreement content
    let versionId: number | null = null;
    try {
      const token = await apiService.getToken();
      const res = await fetch(
        `/api/v1/staff/nda/current?document_type=${encodeURIComponent(agreementType)}`,
        { headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' } }
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const d = await res.json();
      if (d.success && d.nda) {
        const nda = d.nda;
        versionId = nda.id;
        const staffUser = authService.getAuthState().user || {};
        const today = new Date().toLocaleDateString('en-IN', { day: '2-digit', month: 'long', year: 'numeric' });
        let html = (nda.content_html || '').replace(/\{\{current_date\}\}/g, today)
          .replace(/\{\{employee_name\}\}/g, (staffUser as any).full_name || 'Employee')
          .replace(/\{\{employee_code\}\}/g, (staffUser as any).emp_code || '-')
          .replace(/\{\{employee_designation\}\}/g, (staffUser as any).designation || 'Staff')
          .replace(/\{\{company_name\}\}/g, 'MyntReal LLP')
          .replace(/\{\{company_address\}\}/g, 'Kothavalasa, Vizianagaram, Andhra Pradesh, India');
        bodyEl.innerHTML = `<div style="background:#fff;border-radius:10px;padding:20px;font-size:13px;line-height:1.7;border:1px solid #e5e7eb">${html}</div>`;
        acceptBtn.disabled = false;
      } else {
        throw new Error('No agreement data');
      }
    } catch (err) {
      bodyEl.innerHTML = `<div style="text-align:center;padding:32px;color:#dc2626">
        <div style="font-size:24px;margin-bottom:12px">❌</div>
        <div style="font-size:14px">Could not load ${agreementLabel}.<br>Please sign out and log in again.</div>
      </div>`;
    }

    acceptBtn.onclick = async () => {
      if (!versionId) return;
      acceptBtn.disabled = true;
      acceptBtn.textContent = '⏳ Processing…';
      try {
        const token = await apiService.getToken();
        const res = await fetch('/api/v1/staff/nda/accept', {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
          body: JSON.stringify({ nda_version_id: versionId }),
        });
        const data = await res.json();
        if (data.success) {
          overlay.remove();
          document.body.style.overflow = '';
          // Reload so the sequential gate checks the next pending agreement (if any)
          window.location.reload();
        } else {
          throw new Error(data.detail || 'Acceptance failed');
        }
      } catch (err: any) {
        acceptBtn.disabled = false;
        acceptBtn.textContent = 'I Accept';
        alert('Error: ' + (err?.message || 'Could not accept agreement. Please try again.'));
      }
    };
  }
}

(window as any).routerService = routerService;

document.addEventListener('DOMContentLoaded', () => {
  new MNRApp();
});

export { MNRApp };
