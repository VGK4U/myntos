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
}

class CallController {
  public openCallDialer(intent: CallIntent): void {
    if (!intent || !intent.phoneNumber) {
      console.warn('[CallController] Invalid call intent: phoneNumber is required', intent);
      return;
    }

    const cleanPhone = String(intent.phoneNumber).replace(/[^\d+]/g, '').trim();
    if (!cleanPhone) {
      console.warn('[CallController] Cleaned phone number is empty', intent.phoneNumber);
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
      autoStart: intent.autoStart ?? true
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
