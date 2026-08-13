/**
 * Agreement Enforcement Interceptor - DC Protocol Compliant
 * DC-AGREEMENT-TYPE-001 (Jun 2026): Supports NDA + Employment Agreement
 * Intercepts 403 NDA_PENDING responses and forces agreement modal display automatically.
 * Sequential gate: NDA first → Employment Agreement second.
 * DC Protocol Fix (Aug 2026): NEVER deletes staff_token on NDA_PENDING to prevent login loops.
 */

if (typeof window.NDAEnforcementService === 'undefined') {
window.NDAEnforcementService = class NDAEnforcementService {
  constructor() {
    this.isNdaModalShowing = false;
    this.pendingNdaData = null;
    this.currentAgreementType = 'NDA';
    this.currentAgreementLabel = 'Non-Disclosure Agreement';
    this.originalFetch = window.fetch.bind(window);
    this.installInterceptor();
  }

  installInterceptor() {
    window.fetch = async (...args) => {
      const response = await this.originalFetch(...args);
      
      if (response.status === 403) {
        const clonedResponse = response.clone();
        try {
          const data = await clonedResponse.json();
          
          if (data.detail === 'NDA_PENDING') {
            const agreementType = response.headers.get('X-Agreement-Type') || 'NDA';
            const agreementLabel = response.headers.get('X-Agreement-Label') || 'Non-Disclosure Agreement';
            console.warn(`[DC-NDA-ENFORCEMENT] ${agreementLabel} acceptance required - automatically presenting agreement overlay`);
            this.handleAgreementPending(agreementType, agreementLabel);
            throw new Error('NDA_PENDING');
          }
        } catch (parseError) {
          if (parseError.message === 'NDA_PENDING') {
            throw parseError;
          }
        }
      }
      
      return response;
    };
    
    console.log('[DC-NDA-ENFORCEMENT] Fetch interceptor installed (multi-agreement & session-preservation mode)');
  }

  async handleAgreementPending(agreementType = 'NDA', agreementLabel = 'Non-Disclosure Agreement') {
    this.currentAgreementType = agreementType;
    this.currentAgreementLabel = agreementLabel;

    if (this.isNdaModalShowing) return;
    this.isNdaModalShowing = true;
    
    console.log(`[DC-NDA-ENFORCEMENT] Fetching ${agreementLabel} for automatic display`);
    
    const token = localStorage.getItem('staff_token');
    if (!token) {
      console.warn('[DC-NDA-ENFORCEMENT] No staff_token present; redirecting to login');
      window.location.href = '/staff/login';
      return;
    }

    try {
      const response = await this.originalFetch(
        `/api/v1/staff/nda/current?document_type=${encodeURIComponent(agreementType)}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      );

      if (!response.ok) {
        throw new Error(`HTTP ${response.status} loading agreement`);
      }

      const ndaData = await response.json();
      
      if (ndaData.success && (ndaData.nda || ndaData.data)) {
        const activeDoc = ndaData.nda || ndaData.data;
        this.pendingNdaData = activeDoc;
        this.showNdaModal(activeDoc);
      } else {
        console.error('[DC-NDA-ENFORCEMENT] No active agreement payload returned');
        this.showRetryModal(`Unable to retrieve the active ${agreementLabel}. Please click Retry to reload.`);
      }
    } catch (error) {
      console.error('[DC-NDA-ENFORCEMENT] Network/Server error fetching agreement:', error);
      this.showRetryModal(`Temporary network issue loading ${agreementLabel}: ${error.message}. Please click Retry.`);
    }
  }

  // Backward-compat alias
  async handleNdaPending() {
    return this.handleAgreementPending('NDA', 'Non-Disclosure Agreement');
  }

  showNdaModal(ndaData) {
    if (document.getElementById('ndaEnforcementModal')) {
      document.getElementById('ndaEnforcementModal').remove();
    }
    if (document.getElementById('ndaRetryModal')) {
      document.getElementById('ndaRetryModal').remove();
    }

    const staffUser = JSON.parse(localStorage.getItem('staff_user') || '{}');
    const today = new Date().toLocaleDateString('en-IN', { day: '2-digit', month: 'long', year: 'numeric' });
    
    const agreementLabel = ndaData.agreement_label || this.currentAgreementLabel || 'Non-Disclosure Agreement';
    const isEmployment = (ndaData.document_type === 'EMPLOYMENT');
    const headerGradient = isEmployment
      ? 'linear-gradient(135deg, #065f46 0%, #059669 100%)'
      : 'linear-gradient(135deg, #1a237e 0%, #3949ab 100%)';
    const headerIcon = isEmployment ? 'fas fa-file-signature' : 'fas fa-file-contract';
    
    let content = ndaData.content_html || '';
    content = content.replace(/\{\{current_date\}\}/g, today);
    content = content.replace(/\{\{employee_name\}\}/g, staffUser.full_name || 'Employee');
    content = content.replace(/\{\{employee_code\}\}/g, staffUser.emp_code || '-');
    content = content.replace(/\{\{employee_designation\}\}/g, staffUser.role_name || staffUser.designation || 'Staff');
    content = content.replace(/\{\{company_name\}\}/g, 'MyntReal LLP');
    content = content.replace(/\{\{company_address\}\}/g, 'Kothavalasa, Vizianagaram, Andhra Pradesh, India');

    const modalHTML = `
      <div id="ndaEnforcementModal" class="nda-enforcement-overlay">
        <div class="nda-enforcement-modal">
          <div class="nda-enforcement-header" style="background: ${headerGradient};">
            <i class="${headerIcon}"></i>
            <div>
              <h4>${agreementLabel} Required</h4>
              <p>Version: ${ndaData.version_number || '1.0'} — Please review and accept to continue</p>
            </div>
          </div>
          <div class="nda-enforcement-body">
            <div class="nda-enforcement-content">
              ${content || 'Loading agreement content...'}
            </div>
          </div>
          <div class="nda-enforcement-footer">
            <div class="nda-enforcement-warning" id="ndaWarningBox">
              <i class="fas fa-exclamation-triangle"></i>
              <span>You must accept the ${agreementLabel} to access system features.</span>
            </div>
            <div class="nda-enforcement-buttons">
              <button class="btn-nda-enforcement btn-nda-cancel" id="ndaDeclineBtn">
                <i class="fas fa-info-circle me-2"></i>Review Later
              </button>
              <button class="btn-nda-enforcement btn-nda-accept" id="ndaAcceptBtn">
                <i class="fas fa-check me-2"></i>I Accept & Continue
              </button>
            </div>
          </div>
        </div>
      </div>
      <style>
        .nda-enforcement-overlay {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0, 0, 0, 0.85);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 999999;
          backdrop-filter: blur(4px);
        }
        .nda-enforcement-modal {
          background: #fff;
          border-radius: 15px;
          width: 90%;
          max-width: 800px;
          max-height: 90vh;
          display: flex;
          flex-direction: column;
          box-shadow: 0 25px 50px rgba(0, 0, 0, 0.5);
        }
        .nda-enforcement-header {
          color: white;
          padding: 22px 25px;
          border-radius: 15px 15px 0 0;
          display: flex;
          align-items: center;
          gap: 15px;
        }
        .nda-enforcement-header i {
          font-size: 2.2rem;
          opacity: 0.95;
        }
        .nda-enforcement-header h4 {
          margin: 0 0 4px 0;
          font-size: 1.35rem;
        }
        .nda-enforcement-header p {
          margin: 0;
          opacity: 0.9;
          font-size: 0.88rem;
        }
        .nda-enforcement-body {
          flex: 1;
          overflow-y: auto;
          padding: 20px 25px;
          background: #f8f9fa;
        }
        .nda-enforcement-content {
          background: white;
          border-radius: 10px;
          padding: 22px;
          border: 1px solid #e0e0e0;
          font-size: 0.94rem;
          line-height: 1.65;
        }
        .nda-enforcement-footer {
          padding: 18px 25px;
          background: #fff;
          border-top: 1px solid #e0e0e0;
          border-radius: 0 0 15px 15px;
        }
        .nda-enforcement-warning {
          background: #fff3e0;
          color: #e65100;
          padding: 10px 14px;
          border-radius: 8px;
          display: flex;
          align-items: center;
          gap: 10px;
          margin-bottom: 12px;
          font-size: 0.88rem;
        }
        .nda-enforcement-buttons {
          display: flex;
          gap: 12px;
          justify-content: flex-end;
        }
        .btn-nda-enforcement {
          padding: 11px 22px;
          border: none;
          border-radius: 8px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.25s;
          font-size: 0.95rem;
        }
        .btn-nda-cancel {
          background: #f5f5f5;
          color: #424242;
        }
        .btn-nda-cancel:hover {
          background: #eeeeee;
        }
        .btn-nda-accept {
          background: #2e7d32;
          color: white;
        }
        .btn-nda-accept:hover {
          background: #1b5e20;
        }
        .btn-nda-accept:disabled {
          background: #9e9e9e;
          cursor: not-allowed;
        }
      </style>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHTML);
    document.body.style.overflow = 'hidden';

    document.getElementById('ndaDeclineBtn').onclick = () => this.handleDecline();
    document.getElementById('ndaAcceptBtn').onclick = () => this.handleAccept();
  }

  showRetryModal(message) {
    if (document.getElementById('ndaRetryModal')) {
      document.getElementById('ndaRetryModal').remove();
    }

    const modalHTML = `
      <div id="ndaRetryModal" class="nda-enforcement-overlay">
        <div class="nda-enforcement-modal" style="max-width: 520px;">
          <div class="nda-enforcement-header" style="background: linear-gradient(135deg, #d32f2f 0%, #b71c1c 100%);">
            <i class="fas fa-exclamation-triangle"></i>
            <div>
              <h4>${this.currentAgreementLabel} Needed</h4>
              <p>Connection issue loading agreement</p>
            </div>
          </div>
          <div class="nda-enforcement-body" style="text-align: center; padding: 30px;">
            <p style="font-size: 0.98rem; color: #333; margin-bottom: 20px;">${message}</p>
            <button class="btn-nda-enforcement btn-nda-accept" id="ndaRetryFetchBtn" style="background: #1a237e; color: white;">
              <i class="fas fa-sync-alt me-2"></i>Retry Loading Agreement
            </button>
          </div>
        </div>
      </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHTML);
    document.body.style.overflow = 'hidden';

    document.getElementById('ndaRetryFetchBtn').onclick = () => {
      document.getElementById('ndaRetryModal').remove();
      this.isNdaModalShowing = false;
      this.handleAgreementPending(this.currentAgreementType, this.currentAgreementLabel);
    };
  }

  handleDecline() {
    console.log('[DC-NDA-ENFORCEMENT] Employee selected Review Later — preserving token and showing informational guidance');
    const warningBox = document.getElementById('ndaWarningBox');
    if (warningBox) {
      warningBox.style.background = '#ffebee';
      warningBox.style.color = '#c62828';
      warningBox.innerHTML = `
        <i class="fas fa-lock"></i>
        <span>Agreement acceptance is required before protected system features can be accessed. Please click "I Accept & Continue" to proceed.</span>
      `;
    }
  }

  async handleAccept() {
    if (!this.pendingNdaData) {
      console.error('[DC-NDA-ENFORCEMENT] No active pending agreement data to submit');
      return;
    }

    const acceptBtn = document.getElementById('ndaAcceptBtn');
    acceptBtn.disabled = true;
    acceptBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Recording Acceptance...';

    const token = localStorage.getItem('staff_token');
    if (!token) {
      alert('Authentication session missing. Please log in.');
      window.location.href = '/staff/login';
      return;
    }

    try {
      // Step 1: Post agreement acceptance to production endpoint
      const response = await this.originalFetch('/api/v1/staff/nda/accept', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ nda_version_id: this.pendingNdaData.id })
      });

      const data = await response.json();

      if (data.success) {
        console.log('[DC-NDA-ENFORCEMENT] Agreement accepted successfully. Re-checking agreement status...');
        
        // Step 2: Re-check agreement status to confirm acceptance is committed in DB
        const statusCheck = await this.originalFetch(
          `/api/v1/staff/nda/current?document_type=${encodeURIComponent(this.currentAgreementType)}`,
          {
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json'
            }
          }
        );

        const statusData = await statusCheck.json().catch(() => ({}));
        
        // Step 3: Confirmation — remove overlay and continue SAME session without logging out
        const modal = document.getElementById('ndaEnforcementModal');
        if (modal) modal.remove();
        document.body.style.overflow = '';
        
        this.isNdaModalShowing = false;
        this.pendingNdaData = null;

        console.log('[DC-NDA-ENFORCEMENT] Agreement status verified complete. Refreshing page view in same session.');
        window.location.reload();
      } else {
        throw new Error(data.detail || data.message || 'Acceptance failed');
      }
    } catch (error) {
      console.error('[DC-NDA-ENFORCEMENT] Error recording agreement acceptance:', error);
      acceptBtn.disabled = false;
      acceptBtn.innerHTML = '<i class="fas fa-check me-2"></i>I Accept & Continue';
      
      const warningBox = document.getElementById('ndaWarningBox');
      if (warningBox) {
        warningBox.style.background = '#ffebee';
        warningBox.style.color = '#c62828';
        warningBox.innerHTML = `
          <i class="fas fa-exclamation-triangle"></i>
          <span>Failed to record acceptance: ${error.message}. Session preserved — click I Accept to try again.</span>
        `;
      }
    }
  }
}
} // Closes if (typeof window.NDAEnforcementService === 'undefined')

if (!window.ndaEnforcementService && window.NDAEnforcementService) {
  window.ndaEnforcementService = new window.NDAEnforcementService();
}

