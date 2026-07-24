import re

with open('C:/Desktop/VGK4U/MyntReal_Latest/frontend/public/hub/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the start of the footer
footer_start = content.find('<!-- ══ FOOTER ══ -->')
if footer_start == -1:
    # Try another anchor
    footer_start = content.find('<footer class="footer">')

correct_footer_and_scripts = '''<!-- ══ FOOTER ══ -->
<footer class="footer">
  <div class="container footer-top">
    <div class="footer-col">
      <img src="/hub/Assets/Myntreal.logo.png" alt="MyntReal Logo" style="width:180px; margin-bottom:20px;">
      <p style="color:#cbd5e1">Empowering individuals and businesses across India through unified digital services.</p>
      <div class="footer-social">
        <div id="sm-hub"></div>
      </div>
    </div>
    
    <div class="footer-col">
      <h4>Our Verticals</h4>
      <div class="footer-links">
        <a href="/hub/manthra">Manthra EV</a>
        <a href="/hub/hgs">Har Ghar Solar</a>
        <a href="/hub/etc">EVolution Training</a>
        <a href="/hub/realestate">VGK Real Dreams</a>
        <a href="/hub/care">VGK Care</a>
      </div>
    </div>

    <div class="footer-col">
      <h4>Quick Links</h4>
      <div class="footer-links">
        <a href="/hub/about">About Us</a>
        <a href="/hub/contact">Contact</a>
        <a href="/careers">Careers</a>
      </div>
    </div>

    <div class="footer-col">
      <h4>Stay Updated</h4>
      <p style="color:#cbd5e1; margin-bottom:15px">Join our newsletter for the latest updates.</p>
      <form class="newsletter-box">
        <input type="email" placeholder="Email Address" required>
        <button type="submit"><i class="fas fa-paper-plane"></i></button>
      </form>
    </div>
  </div>

  <div class="footer-divider"></div>
  <div class="footer-bottom">
    <div class="container footer-bottom-inner">
      <p>© 2026 MyntReal. All rights reserved.</p>
      <div class="footer-policy">
        <a href="/privacy">Privacy Policy</a>
        <a href="#">Terms</a>
      </div>
    </div>
  </div>
</footer>

<script>
/* ── Mobile menu ── */
const menuToggle = document.getElementById("menuToggle");
const navMenu    = document.getElementById("navMenu");
const overlay    = document.getElementById("navOverlay");

if(menuToggle) {
    menuToggle.addEventListener("click", () => {
      menuToggle.classList.toggle("active");
      navMenu.classList.toggle("active");
      overlay.classList.toggle("active");
    });
}
if(overlay) {
    overlay.addEventListener("click", () => {
      menuToggle.classList.remove("active");
      navMenu.classList.remove("active");
      overlay.classList.remove("active");
    });
}

/* ── Header scroll shadow ── */
window.addEventListener("scroll", () => {
  let header = document.getElementById("header");
  if(header) header.classList.toggle("scrolled", window.scrollY > 50);
});

/* ── Section reveal (IntersectionObserver — no GSAP needed) ── */
const revealEls = document.querySelectorAll(".section, .why-section, .cta-dark");
const io = new IntersectionObserver(entries => {
  entries.forEach(e => { if (e.isIntersecting) { e.target.classList.add("active"); io.unobserve(e.target); } });
}, { threshold: 0.12 });
revealEls.forEach(el => io.observe(el));

/* Vertical cards reveal */
const vcards = document.querySelectorAll(".vertical-card");
const vcIO = new IntersectionObserver(entries => {
  entries.forEach(e => { if (e.isIntersecting) e.target.classList.add("show"); });
}, { threshold: 0.1 });
vcards.forEach(c => vcIO.observe(c));

/* Hero reveal on load */
window.addEventListener("load", () => {
  const hero = document.querySelector(".hero");
  if (hero) hero.classList.add("active");
});

/* ── Testimonial slider ── */
let whyIndex = 0;
const track = document.getElementById("whyTrack");
const dots  = document.querySelectorAll(".dot");

function updateWhy() {
  if(!track) return;
  track.style.transform = `translateX(-${whyIndex * 100}%)`;
  dots.forEach(d => d.classList.remove("active"));
  if (dots[whyIndex]) dots[whyIndex].classList.add("active");
}
function nextWhy() { whyIndex = (whyIndex + 1) % 3; updateWhy(); }
function prevWhy() { whyIndex = (whyIndex - 1 + 3) % 3; updateWhy(); }
function goWhy(i)  { whyIndex = i; updateWhy(); }

setInterval(nextWhy, 4500);
</script>

<style>
/* Foolproof override against cached styles */
.dropdown .dropdown-menu {
    display: none !important;
}
.dropdown.active .dropdown-menu {
    display: flex !important;
}

.custom-modal-overlay {
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0,0,0,0.5);
    display: none;
    align-items: center;
    justify-content: center;
    z-index: 99999;
}
.custom-modal-overlay.show {
    display: flex;
}
.custom-modal {
    background: #f8fafc;
    border-radius: 20px;
    width: 90%;
    max-width: 500px;
    box-shadow: 0 20px 50px rgba(0,0,0,0.3);
    overflow: hidden;
    font-family: 'Inter', sans-serif;
}
.custom-modal-header {
    background: linear-gradient(135deg, #10b981, #047857);
    color: white;
    padding: 20px 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.custom-modal-title {
    margin: 0;
    font-weight: 800;
    font-size: 1.25rem;
}
.custom-modal-close {
    background: transparent;
    border: none;
    color: white;
    font-size: 1.7rem;
    cursor: pointer;
    line-height: 1;
}
.custom-modal-body {
    padding: 24px;
}
.custom-modal-body label {
    display: block;
    font-size: 0.85rem;
    font-weight: 600;
    color: #475569;
    margin-bottom: 5px;
}
.custom-modal-body input, .custom-modal-body select {
    width: 100%;
    border-radius: 10px;
    padding: 10px 12px;
    border: 1px solid #cbd5e1;
    margin-bottom: 15px;
    box-sizing: border-box;
}
.custom-modal-row {
    display: flex;
    gap: 15px;
}
.custom-modal-col {
    flex: 1;
}
.btn-pay {
    background: linear-gradient(135deg, #10b981, #059669);
    color: white;
    border-radius: 10px;
    padding: 12px;
    font-weight: 700;
    width: 100%;
    border: none;
    cursor: pointer;
    box-shadow: 0 4px 15px rgba(16,185,129,0.3);
    margin-top: 10px;
}
.btn-pay:disabled {
    opacity: 0.7;
    cursor: not-allowed;
}
</style>

<div class="custom-modal-overlay" id="hubRechargeModal">
  <div class="custom-modal">
    <div class="custom-modal-header">
      <h3 class="custom-modal-title">📱 Instant Mobile Recharge</h3>
      <button class="custom-modal-close" onclick="closeRechargeModal()">&times;</button>
    </div>
    <div class="custom-modal-body">
      <form id="hubRechargeForm">
        <label>Mobile Number</label>
        <input type="tel" id="hubRechargeMobile" required pattern="[0-9]{10}" placeholder="Enter 10-digit number">
        
        <div class="custom-modal-row">
            <div class="custom-modal-col">
              <label>Operator</label>
              <select id="hubRechargeOperator" required>
                <option value="">Select Operator</option>
                <option value="Airtel">Airtel</option>
                <option value="Jio">Jio</option>
                <option value="VI">VI</option>
                <option value="BSNL">BSNL</option>
              </select>
            </div>
            <div class="custom-modal-col">
              <label>Circle (Optional)</label>
              <select id="hubRechargeCircle">
                <option value="">Select Circle</option>
                <option value="Andhra Pradesh">Andhra Pradesh</option>
                <option value="Delhi">Delhi</option>
                <option value="Karnataka">Karnataka</option>
                <option value="Maharashtra">Maharashtra</option>
                <option value="Tamil Nadu">Tamil Nadu</option>
              </select>
            </div>
        </div>
        
        <label>Amount (₹)</label>
        <input type="number" id="hubRechargeAmount" required min="10" placeholder="e.g. 299">
        
        <label>Guest Details (For receipt)</label>
        <div class="custom-modal-row">
            <div class="custom-modal-col">
                <input type="text" id="hubRechargeGuestName" placeholder="Name (Optional)">
            </div>
            <div class="custom-modal-col">
                <input type="email" id="hubRechargeGuestEmail" placeholder="Email (Optional)">
            </div>
        </div>

        <button type="submit" class="btn-pay" id="hubRechargeSubmitBtn">Proceed to Pay</button>
      </form>
    </div>
  </div>
</div>

<script src="https://checkout.razorpay.com/v1/checkout.js"></script>
<script>
/* Recharge Modal Logic */
function openRechargeModal(e) {
    if(e) e.preventDefault();
    document.getElementById('hubRechargeModal').classList.add('show');
    // close dropdown menu just in case
    document.querySelectorAll('.dropdown').forEach(dd => dd.classList.remove('active'));
}
function closeRechargeModal() {
    document.getElementById('hubRechargeModal').classList.remove('show');
}

// Close on outside click
document.getElementById('hubRechargeModal').addEventListener('click', function(e) {
    if(e.target === this) closeRechargeModal();
});

document.getElementById('hubRechargeForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    const btn = document.getElementById('hubRechargeSubmitBtn');
    btn.innerHTML = 'Processing...';
    btn.disabled = true;

    const data = {
        mobile_number: document.getElementById('hubRechargeMobile').value,
        operator: document.getElementById('hubRechargeOperator').value,
        circle: document.getElementById('hubRechargeCircle').value || null,
        amount: parseFloat(document.getElementById('hubRechargeAmount').value),
        guest_name: document.getElementById('hubRechargeGuestName').value || null,
        guest_email: document.getElementById('hubRechargeGuestEmail').value || null
    };

    try {
        const res = await fetch('http://127.0.0.1:8000/api/v1/recharge/create-order', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const orderData = await res.json();

        if(!res.ok) {
            alert(orderData.detail || "Failed to create order");
            btn.innerHTML = 'Proceed to Pay';
            btn.disabled = false;
            return;
        }

        const options = {
            "key": orderData.key_id,
            "amount": orderData.amount,
            "currency": orderData.currency,
            "name": "VGK4U Mobile Recharge",
            "description": `Recharge for ${data.mobile_number} (${data.operator})`,
            "order_id": orderData.order_id,
            "handler": async function (response) {
                try {
                    const verifyRes = await fetch('http://127.0.0.1:8000/api/v1/recharge/verify-payment', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            razorpay_order_id: response.razorpay_order_id,
                            razorpay_payment_id: response.razorpay_payment_id,
                            razorpay_signature: response.razorpay_signature
                        })
                    });
                    const verifyData = await verifyRes.json();
                    if(verifyRes.ok) {
                        alert("Payment successful! Recharge initiated.");
                        closeRechargeModal();
                        document.getElementById('hubRechargeForm').reset();
                    } else {
                        alert(verifyData.detail || "Payment verification failed");
                    }
                } catch(err) {
                    alert("Error verifying payment.");
                }
            },
            "prefill": {
                "name": data.guest_name || "",
                "email": data.guest_email || "",
                "contact": data.mobile_number
            },
            "theme": {
                "color": "#10b981"
            }
        };
        const rzp1 = new Razorpay(options);
        rzp1.on('payment.failed', function (response){
            alert("Payment Failed: " + response.error.description);
        });
        rzp1.open();

    } catch(err) {
        alert("An error occurred. Please try again.");
    } finally {
        btn.innerHTML = 'Proceed to Pay';
        btn.disabled = false;
    }
});
</script>

</body>
</html>
'''

if footer_start != -1:
    new_content = content[:footer_start] + correct_footer_and_scripts
    with open('C:/Desktop/VGK4U/MyntReal_Latest/frontend/public/hub/index.html', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print('HTML restored completely and safely!')
else:
    print('Could not find footer start marker.')
