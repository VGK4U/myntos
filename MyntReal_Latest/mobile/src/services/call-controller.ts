/**
 * Central Call Controller — MyntOS Mobile
 * Unified intent dispatcher and orchestrator for all calling triggers across the mobile app.
 * Directs all contextual calls to the Central Softphone Dialer Modal without page navigation.
 */

import { softphoneModal, SoftphoneModalOptions } from '../components/SoftphoneModal';
import { telephonyService } from './telephony.service';

export interface CallIntent {
  phoneNumber: string;
  name?: string;
  entityType?: string;
  entityId?: string | number | null;
  source?: string;
  autoStart?: boolean;
  categoryName?: string;
  status?: string;
  isHotLead?: boolean;
  isFreshLead?: boolean;
}

class CallController {
  public openCallDialer(intent: CallIntent): void {
    // MANDATE 1: TRUE USER-GESTURE AUDIO UNLOCK BEFORE ANY ASYNC OPERATION
    if (intent?.autoStart !== false) {
      telephonyService.prepareAudioOnUserGesture();
    }

    if (!intent || !intent.phoneNumber) {
      console.warn('[CallController] Invalid call intent: phoneNumber is required', intent);
      return;
    }

    const cleanPhone = String(intent.phoneNumber).replace(/[^\d+]/g, '').trim();
    if (!cleanPhone) {
      console.warn('[CallController] Cleaned phone number is empty', intent.phoneNumber);
      return;
    }

    const rawDigits = cleanPhone.replace(/\D/g, '');
    if (rawDigits.length < 10) {
      console.warn('[CallController] Phone number is invalid (fewer than 10 digits):', cleanPhone);
      if (typeof window !== 'undefined') {
        const toastFn = (window as any).showToast;
        if (typeof toastFn === 'function') {
          toastFn(`Invalid phone number: ${cleanPhone}. At least 10 digits required.`, 'error');
        } else if (typeof alert === 'function') {
          alert(`Invalid phone number: ${cleanPhone}. At least 10 digits required.`);
        }
      }
      return;
    }

    console.log(
      `[CallController] Handling call intent for: ${cleanPhone} (${intent.name || 'Contact'}, entity: ${intent.entityType || 'lead'})`
    );

    // Pre-initialize telephony service in background
    telephonyService.initPlivoWebRTC().catch(() => {});

    // Open the centralized modal
    const modalOptions: SoftphoneModalOptions = {
      phoneNumber: cleanPhone,
      name: (intent.name || 'Contact Lead').trim(),
      entityType: intent.entityType || 'lead',
      entityId: intent.entityId || null,
      source: intent.source || 'contextual',
      autoStart: intent.autoStart ?? true,
      categoryName: intent.categoryName,
      status: intent.status,
      isHotLead: intent.isHotLead,
      isFreshLead: intent.isFreshLead
    };

    softphoneModal.open(modalOptions);
  }
}

export const callController = new CallController();

// Global registration
if (typeof window !== 'undefined') {
  (window as any).callController = callController;
  (window as any).openCallDialer = (intent: CallIntent) => callController.openCallDialer(intent);
  (window as any).triggerLeadCall = (phone: string, name?: string, leadId?: any) => {
    callController.openCallDialer({
      phoneNumber: phone,
      name: name || 'Contact Lead',
      entityId: leadId,
      entityType: 'lead'
    });
  };
}

if (typeof document !== 'undefined') {
  document.addEventListener('plivo:call-dialing', (e: any) => {
    try {
      const sessionId = e?.detail?.sessionId;
      if (!sessionId) return;
      const hash = (typeof window !== 'undefined' ? window.location.hash : '') || '';
      let pageName = 'Mobile CRM';
      if (typeof window !== 'undefined' && (window as any).__currentDialedPage) {
        pageName = (window as any).__currentDialedPage;
      } else if (hash.includes('leads') || hash.includes('staff-leads')) {
        pageName = 'Staff Leads';
      } else if (hash.includes('auto-dialer') || hash.includes('dialer')) {
        pageName = 'Auto Dialer';
      } else if (hash.includes('crm')) {
        pageName = 'CRM Dashboard';
      } else if (hash.includes('whatsapp')) {
        pageName = 'WhatsApp Center';
      } else if (hash.includes('executive')) {
        pageName = 'Executive Dashboard';
      }
      const token = (typeof localStorage !== 'undefined') ? (localStorage.getItem('staff_token') || localStorage.getItem('token') || '') : '';
      if (token) {
        fetch('/api/v1/call-tracking/record-dial-page', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + token
          },
          body: JSON.stringify({
            call_session_id: sessionId,
            dialed_page: pageName,
            page_url: (typeof window !== 'undefined') ? (window.location.hash || window.location.pathname || '') : ''
          }),
          keepalive: true
        }).catch(() => {});
      }
    } catch (_) {}
  });
}
