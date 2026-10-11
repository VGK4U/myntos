/**
 * Suryanz Solar - Client Lead Submission Engine
 * Submits to /api/v1/public/suryanz/lead
 * Features: Form validation, loading state, accessible feedback, network error handling
 */
document.addEventListener('DOMContentLoaded', function() {
  const forms = document.querySelectorAll('.suryanz-lead-form');
  if (!forms || forms.length === 0) return;

  forms.forEach(form => {
    form.addEventListener('submit', async function(e) {
      e.preventDefault();
      
      const submitBtn = form.querySelector('button[type="submit"]');
      let msgBox = form.querySelector('.suryanz-form-response');
      if (!msgBox) {
        msgBox = document.createElement('div');
        msgBox.className = 'suryanz-form-response';
        msgBox.style.marginTop = '1rem';
        msgBox.style.padding = '0.75rem 1rem';
        msgBox.style.borderRadius = '6px';
        msgBox.style.fontSize = '0.9rem';
        msgBox.style.fontWeight = '500';
        form.appendChild(msgBox);
      }

      // Reset message state
      msgBox.style.display = 'block';
      msgBox.className = 'suryanz-form-response';
      msgBox.innerText = '';
      msgBox.removeAttribute('role');

      const nameEl = form.querySelector('[name="name"]');
      const phoneEl = form.querySelector('[name="phone"]');
      const emailEl = form.querySelector('[name="email"]');
      const cityEl = form.querySelector('[name="city"]');
      const stateEl = form.querySelector('[name="state"]');
      const typeEl = form.querySelector('[name="customer_type"]');
      const billEl = form.querySelector('[name="monthly_bill"]');
      const roofEl = form.querySelector('[name="roof_area"]');
      const solEl = form.querySelector('[name="interested_solution"]');

      const name = nameEl ? nameEl.value.trim() : '';
      const phone = phoneEl ? phoneEl.value.trim() : '';
      
      if (!name || name.length < 2) {
        msgBox.setAttribute('role', 'alert');
        msgBox.style.color = '#dc2626';
        msgBox.style.background = '#fef2f2';
        msgBox.style.border = '1px solid #fca5a5';
        msgBox.innerHTML = '<i class="fas fa-exclamation-circle me-1"></i> Please enter your full name.';
        if (nameEl) nameEl.focus();
        return;
      }

      const cleanPhone = phone.replace(/\D/g, '');
      const phoneRegex = /^[6-9]\d{9}$/;
      if (!cleanPhone || !phoneRegex.test(cleanPhone)) {
        msgBox.setAttribute('role', 'alert');
        msgBox.style.color = '#dc2626';
        msgBox.style.background = '#fef2f2';
        msgBox.style.border = '1px solid #fca5a5';
        msgBox.innerHTML = '<i class="fas fa-exclamation-circle me-1"></i> Please enter a valid 10-digit mobile number.';
        if (phoneEl) phoneEl.focus();
        return;
      }

      let originalBtnHtml = 'Get a Free Solar Assessment';
      if (submitBtn) {
        originalBtnHtml = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Submitting...';
      }

      // Collect UTM parameters
      const urlParams = new URLSearchParams(window.location.search);
      const payload = {
        name: name,
        phone: cleanPhone,
        email: emailEl ? emailEl.value.trim() : '',
        city: cityEl ? cityEl.value.trim() : '',
        state: stateEl ? stateEl.value.trim() : '',
        customer_type: typeEl ? typeEl.value : 'residential',
        monthly_bill: billEl ? parseFloat(billEl.value) || 0 : 0,
        roof_area: roofEl ? parseFloat(roofEl.value) || 0 : 0,
        interested_solution: solEl ? solEl.value : 'Rooftop Solar System',
        utm_source: urlParams.get('utm_source') || '',
        utm_medium: urlParams.get('utm_medium') || '',
        utm_campaign: urlParams.get('utm_campaign') || '',
        landing_url: window.location.href
      };

      try {
        const resp = await fetch('/api/v1/public/suryanz/lead', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        const resData = await resp.json().catch(() => ({}));

        if (resp.ok && resData && resData.success) {
          msgBox.setAttribute('role', 'status');
          msgBox.setAttribute('aria-live', 'polite');
          msgBox.style.color = '#15803d';
          msgBox.style.background = '#f0fdf4';
          msgBox.style.border = '1px solid #86efac';
          msgBox.innerHTML = '<i class="fas fa-check-circle me-1"></i> ' + (resData.message || 'Thank you! Your solar assessment request has been submitted.');
          form.reset();
        } else {
          msgBox.setAttribute('role', 'alert');
          msgBox.style.color = '#dc2626';
          msgBox.style.background = '#fef2f2';
          msgBox.style.border = '1px solid #fca5a5';
          msgBox.innerHTML = '<i class="fas fa-exclamation-triangle me-1"></i> ' + ((resData && (resData.message || resData.detail)) ? (resData.message || resData.detail) : 'Submission error. Please try again.');
        }
      } catch (err) {
        console.warn('[SURYANZ-LEAD] Lead submission network issue:', err);
        msgBox.setAttribute('role', 'alert');
        msgBox.style.color = '#dc2626';
        msgBox.style.background = '#fef2f2';
        msgBox.style.border = '1px solid #fca5a5';
        msgBox.innerHTML = '<i class="fas fa-wifi me-1"></i> Network error. Please check your connection and try again.';
      } finally {
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.innerHTML = originalBtnHtml;
        }
      }
    });
  });
});
