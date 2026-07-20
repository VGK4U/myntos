/**
 * Agreement Enforcement Interceptor - DC Protocol Compliant
 * DC-AGREEMENT-TYPE-001 (Jun 2026): Supports NDA + Employment Agreement
 * Intercepts 403 NDA_PENDING responses and forces agreement modal display.
 * Sequential gate: NDA first → Employment Agreement second.
 */

class NDAEnforcementService {
  constructor() {
    this.isNdaModalShowing = false;
    this.pendingNdaData = null;
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
            // DC-AGREEMENT-TYPE-001: Read agreement type from response headers
            const agreementType = response.headers.get('X-Agreement-Type') || 'NDA';
            const agreementLabel = response.headers.get('X-Agreement-Label') || 'Non-Disclosure Agreement';
            console.warn(`[DC-NDA-ENFORCEMENT] ${agreementLabel} acceptance required - blocking access`);
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
    
    console.log('[DC-NDA-ENFORCEMENT] Fetch interceptor installed (multi-agreement mode)');
  }

  async handleAgreementPending(agreementType, agreementLabel) {
    if (this.isNdaModalShowing) return;
    this.isNdaModalShowing = true;
    
    console.log(`[DC-NDA-ENFORCEMENT] Fetching ${agreementLabel} for display`);
    
    try {
      const token = localStorage.getItem('staff_token');
      if (!token) {
        console.error('[DC-NDA-ENFORCEMENT] No token found, redirecting to login');
        window.location.href = '/staff/login';
        return;
      }

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
        throw new Error('Failed to fetch agreement');
      }

      const ndaData = await response.json();
      
      if (ndaData.success && ndaData.nda) {
        this.pendingNdaData = ndaData.nda;
        this.showNdaModal(ndaData.nda);
      } else {
        console.error('[DC-NDA-ENFORCEMENT] No agreement data received');
        this.showErrorModal(`Unable to load ${agreementLabel}. Please try logging in again.`, agreementLabel);
      }
    } catch (error) {
      console.error('[DC-NDA-ENFORCEMENT] Error fetching agreement:', error);
      this.showErrorModal(`Error loading agreement. Please try logging in again.`, agreementType === 'EMPLOYMENT' ? 'Employment Agreement' : 'NDA');
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

    const staffUser = JSON.parse(localStorage.getItem('staff_user') || '{}');
    const today = new Date().toLocaleDateString('en-IN', { day: '2-digit', month: 'long', year: 'numeric' });
    
    // Agreement-type-aware display strings
    const agreementLabel = ndaData.agreement_label || 'Non-Disclosure Agreement';
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
              <p>Version: ${ndaData.version_number || 'N/A'} — Please review and accept to continue</p>
            </div>
          </div>
          <div class="nda-enforcement-body">
            <div class="nda-enforcement-content">
              ${content || 'Loading agreement content...'}
            </div>
          </div>
          <div class="nda-enforcement-footer">
            <div class="nda-enforcement-warning">
              <i class="fas fa-exclamation-triangle"></i>
              <span>You must accept the ${agreementLabel} to access the system. All features are blocked until acceptance.</span>
            </div>
            <div class="nda-enforcement-buttons">
              <button class="btn-nda-enforcement btn-nda-cancel" id="ndaCancelBtn">
                <i class="fas fa-sign-out-alt me-2"></i>Logout
              </button>
              <button class="btn-nda-enforcement btn-nda-accept" id="ndaAcceptBtn">
                <i class="fas fa-check me-2"></i>I Accept
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
          background: rgba(0, 0, 0, 0.9);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 999999;
          backdrop-filter: blur(5px);
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
          padding: 25px;
          border-radius: 15px 15px 0 0;
          display: flex;
          align-items: center;
          gap: 15px;
        }
        .nda-enforcement-header i {
          font-size: 2.5rem;
          opacity: 0.9;
        }
        .nda-enforcement-header h4 {
          margin: 0 0 5px 0;
          font-size: 1.4rem;
        }
        .nda-enforcement-header p {
          margin: 0;
          opacity: 0.9;
          font-size: 0.9rem;
        }
        .nda-enforcement-body {
          flex: 1;
          overflow-y: auto;
          padding: 25px;
          background: #f8f9fa;
        }
        .nda-enforcement-content {
          background: white;
          border-radius: 10px;
          padding: 25px;
          border: 1px solid #e0e0e0;
          font-size: 0.95rem;
          line-height: 1.7;
        }
        .nda-enforcement-footer {
          padding: 20px 25px;
          background: #fff;
          border-top: 1px solid #e0e0e0;
          border-radius: 0 0 15px 15px;
        }
        .nda-enforcement-warning {
          background: #fff3e0;
          color: #e65100;
          padding: 12px 15px;
          border-radius: 8px;
          display: flex;
          align-items: center;
          gap: 10px;
          margin-bottom: 15px;
          font-size: 0.9rem;
        }
        .nda-enforcement-buttons {
          display: flex;
          gap: 12px;
          justify-content: flex-end;
        }
        .btn-nda-enforcement {
          padding: 12px 25px;
          border: none;
          border-radius: 8px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.3s;
          font-size: 1rem;
        }
        .btn-nda-cancel {
          background: #f5f5f5;
          color: #333;
        }
        .btn-nda-cancel:hover {
          background: #e0e0e0;
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

    document.getElementById('ndaCancelBtn').onclick = () => this.handleCancel();
    document.getElementById('ndaAcceptBtn').onclick = () => this.handleAccept();
  }

  showErrorModal(message, agreementLabel) {
    const label = agreementLabel || 'Agreement';
    const modalHTML = `
      <div id="ndaErrorModal" class="nda-enforcement-overlay">
        <div class="nda-enforcement-modal" style="max-width: 500px;">
          <div class="nda-enforcement-header" style="background: linear-gradient(135deg, #c62828 0%, #d32f2f 100%);">
            <i class="fas fa-exclamation-circle"></i>
            <div>
              <h4>${label} Required</h4>
              <p>Unable to proceed</p>
            </div>
          </div>
          <div class="nda-enforcement-body" style="text-align: center; padding: 40px;">
            <p style="font-size: 1.1rem; margin-bottom: 20px;">${message}</p>
            <button class="btn-nda-enforcement btn-nda-cancel" onclick="window.location.href='/staff/login'" style="background: #1a237e; color: white;">
              <i class="fas fa-sign-in-alt me-2"></i>Go to Login
            </button>
          </div>
        </div>
      </div>
    `;

    if (!document.getElementById('ndaErrorModal')) {
      document.body.insertAdjacentHTML('beforeend', modalHTML);
      document.body.style.overflow = 'hidden';
    }
  }

  handleCancel() {
    console.log('[DC-NDA-ENFORCEMENT] User cancelled agreement - logging out');
    localStorage.removeItem('staff_token');
    localStorage.removeItem('staff_user');
    sessionStorage.setItem('staff_logout_reason', 'NDA_DECLINED');
    window.location.href = '/staff/login';
  }

  async handleAccept() {
    if (!this.pendingNdaData) {
      console.error('[DC-NDA-ENFORCEMENT] No pending agreement data');
      return;
    }

    const acceptBtn = document.getElementById('ndaAcceptBtn');
    acceptBtn.disabled = true;
    acceptBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Processing...';

    const token = localStorage.getItem('staff_token');

    try {
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
        console.log('[DC-NDA-ENFORCEMENT] Agreement accepted successfully');
        
        const modal = document.getElementById('ndaEnforcementModal');
        if (modal) modal.remove();
        document.body.style.overflow = '';
        
        this.isNdaModalShowing = false;
        this.pendingNdaData = null;

        // Reload — the gate will now check for the next pending agreement (if any)
        window.location.reload();
      } else {
        throw new Error(data.detail || 'Failed to accept agreement');
      }
    } catch (error) {
      console.error('[DC-NDA-ENFORCEMENT] Error accepting agreement:', error);
      acceptBtn.disabled = false;
      acceptBtn.innerHTML = '<i class="fas fa-check me-2"></i>I Accept';
      alert('Error accepting agreement: ' + error.message);
    }
  }
}

if (!window.ndaEnforcementService) {
  window.ndaEnforcementService = new NDAEnforcementService();
}
