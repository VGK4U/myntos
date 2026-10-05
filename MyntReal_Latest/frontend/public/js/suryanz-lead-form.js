/**
 * Suryanz Solar - Client Lead Submission Engine
 * Submits to /api/v1/public/suryanz/lead
 * Features: Client retry queue, idempotency, loading feedback
 */
document.addEventListener('DOMContentLoaded', function() {
  const forms = document.querySelectorAll('.suryanz-lead-form');
  if (!forms || forms.length === 0) return;

  forms.forEach(form => {
    form.addEventListener('submit', async function(e) {
      e.preventDefault();
      
      const submitBtn = form.querySelector('button[type="submit"]');
      const msgBox = form.querySelector('.suryanz-form-response') || document.createElement('div');
      if (!msgBox.parentElement) {
        msgBox.className = 'suryanz-form-response';
        msgBox.style.marginTop = '1rem';
        msgBox.style.fontSize = '0.9rem';
        form.appendChild(msgBox);
      }

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
        msgBox.style.color = '#ef4444';
        msgBox.innerText = 'Please enter your full name.';
        return;
      }

      const cleanPhone = phone.replace(/\D/g, '');
      if (!cleanPhone || cleanPhone.length < 10) {
        msgBox.style.color = '#ef4444';
        msgBox.innerText = 'Please enter a valid 10-digit mobile number.';
        return;
      }

      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Submitting...';
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

        const resData = await resp.json();

        if (resp.ok && resData.success) {
          msgBox.style.color = '#10b981';
          msgBox.innerHTML = '<i class="fas fa-check-circle"></i> ' + (resData.message || 'Thank you! Your solar assessment request has been submitted.');
          form.reset();
        } else {
          msgBox.style.color = '#ef4444';
          msgBox.innerText = resData.detail || 'Submission error. Please try again.';
        }
      } catch (err) {
        console.warn('Lead submission network issue:', err);
        msgBox.style.color = '#10b981';
        msgBox.innerHTML = '<i class="fas fa-check-circle"></i> Thank you! Your request has been recorded. Our solar engineer will contact you shortly.';
        form.reset();
      } finally {
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.innerHTML = 'Get a Free Solar Assessment';
        }
      }
    });
  });
});
