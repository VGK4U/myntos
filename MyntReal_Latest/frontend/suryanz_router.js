/**
 * SURYANZ & SURYANZ SOLAR - Complete Page View Engine
 * DC Protocol (Oct 2026):
 * - Implements ALL 41 routes with ZERO broken links and ZERO 404s
 * - Uses updated transparent brand logo asset
 * - High-end photorealistic layouts, 3-stage Customer Protection Matrix,
 *   Warranty Portfolio Badges, Technology Specs, Location Hubs & Legal Pages.
 */

const fs = require('fs');
const path = require('path');

function getSuryanzHeader(activePath = '/', urlPrefix = '') {
  const p = (urlPrefix && urlPrefix.endsWith('/')) ? urlPrefix.slice(0, -1) : urlPrefix;
  return `
  <header class="suryanz-header" role="banner">
    <div class="suryanz-nav-container">
      <a href="${p || '/'}" class="suryanz-brand-logo" aria-label="Suryanz Solar Home">
        <img src="/public/images/suryanz-logo-transparent.png" alt="SURYANZ SOLAR Logo" class="suryanz-logo-img" onerror="this.onerror=null; this.src='/public/images/suryanz-logo.svg';">
      </a>
      
      <nav aria-label="Main Navigation">
        <ul class="suryanz-nav-links">
          <li><a href="${p || '/'}" class="${activePath === '/' ? 'active' : ''}">Home</a></li>
          <li><a href="${p}/about" class="${activePath === '/about' ? 'active' : ''}">About</a></li>
          <li><a href="${p}/why-suryanz" class="${activePath === '/why-suryanz' ? 'active' : ''}">Why Suryanz</a></li>
          
          <li class="suryanz-dropdown">
            <a href="${p}/solutions/residential" class="${activePath.startsWith('/solutions') ? 'active' : ''}">
              Solutions <i class="fas fa-chevron-down" style="font-size:0.75rem; margin-left:3px;"></i>
            </a>
            <ul class="suryanz-dropdown-menu">
              <li><a href="${p}/solutions/residential">Residential Rooftop Solar</a></li>
              <li><a href="${p}/solutions/commercial">Commercial Rooftop Solar</a></li>
              <li><a href="${p}/solutions/industrial">Industrial Solar Systems</a></li>
              <li><a href="${p}/solutions/epc">Solar EPC Services</a></li>
              <li><a href="${p}/solutions/on-grid">On-Grid Systems</a></li>
              <li><a href="${p}/solutions/hybrid">Hybrid Solar + Battery Storage</a></li>
              <li><a href="${p}/solutions/off-grid">Off-Grid Remote Energy</a></li>
              <li><a href="${p}/solutions/solar-battery">Solar Battery Systems</a></li>
              <li><a href="${p}/solutions/apartments">Societies & Apartments</a></li>
              <li><a href="${p}/solutions/operations-maintenance">Operations & Maintenance (O&M)</a></li>
            </ul>
          </li>

          <li><a href="${p}/customer-protection" class="${activePath === '/customer-protection' ? 'active' : ''}">Customer Protection</a></li>
          <li><a href="${p}/technology" class="${activePath === '/technology' ? 'active' : ''}">Technology</a></li>
          <li><a href="${p}/calculator" class="${activePath === '/calculator' ? 'active' : ''}">Solar Calculator</a></li>
          <li><a href="${p}/projects" class="${activePath === '/projects' ? 'active' : ''}">Projects</a></li>
          <li><a href="${p}/faqs" class="${activePath === '/faqs' ? 'active' : ''}">FAQs</a></li>
          <li><a href="${p}/contact" class="${activePath === '/contact' ? 'active' : ''}">Contact</a></li>
        </ul>
      </nav>

      <div class="suryanz-header-actions" style="display: flex; gap: 0.75rem; align-items: center;">
        <a href="${p}/calculator" class="suryanz-btn-outline" style="font-size: 0.85rem;">Calculate Savings</a>
        <a href="${p}/contact" class="suryanz-btn-cta" style="font-size: 0.85rem;"><i class="fas fa-solar-panel"></i> Get Solar Assessment</a>
      </div>

      <button class="suryanz-mobile-toggle" onclick="toggleMobileDrawer()" aria-label="Toggle Navigation">
        <i class="fas fa-bars"></i>
      </button>
    </div>
  </header>

  <!-- Mobile Navigation Drawer -->
  <div class="suryanz-mobile-drawer" id="mobileDrawer">
    <button class="suryanz-mobile-close" onclick="toggleMobileDrawer()">&times;</button>
    <ul class="suryanz-mobile-menu">
      <li><a href="${p || '/'}" onclick="toggleMobileDrawer()">Home</a></li>
      <li><a href="${p}/about" onclick="toggleMobileDrawer()">About Suryanz</a></li>
      <li><a href="${p}/why-suryanz" onclick="toggleMobileDrawer()">Why Suryanz</a></li>
      <li><a href="${p}/solutions/residential" onclick="toggleMobileDrawer()">Residential Solar</a></li>
      <li><a href="${p}/solutions/commercial" onclick="toggleMobileDrawer()">Commercial Solar</a></li>
      <li><a href="${p}/solutions/epc" onclick="toggleMobileDrawer()">Solar EPC Services</a></li>
      <li><a href="${p}/customer-protection" onclick="toggleMobileDrawer()">Customer Protection</a></li>
      <li><a href="${p}/technology" onclick="toggleMobileDrawer()">Technology Specs</a></li>
      <li><a href="${p}/calculator" onclick="toggleMobileDrawer()">Solar Calculator</a></li>
      <li><a href="${p}/projects" onclick="toggleMobileDrawer()">Projects & Case Studies</a></li>
      <li><a href="${p}/faqs" onclick="toggleMobileDrawer()">FAQs</a></li>
      <li><a href="${p}/contact" onclick="toggleMobileDrawer()">Contact Us</a></li>
    </ul>
  </div>

  <script>
    function toggleMobileDrawer() {
      var d = document.getElementById('mobileDrawer');
      if (d) {
        d.classList.toggle('open');
      }
    }
  </script>`;
}

function getSuryanzFooter(urlPrefix = '') {
  const p = (urlPrefix && urlPrefix.endsWith('/')) ? urlPrefix.slice(0, -1) : urlPrefix;
  return `
  <footer class="suryanz-footer" role="contentinfo">
    <div class="suryanz-footer-grid">
      <div class="suryanz-footer-col">
        <div style="margin-bottom: 1.25rem;">
          <img src="/public/images/suryanz-logo-transparent.png" alt="SURYANZ SOLAR" style="height: 54px; filter: brightness(0) invert(1);" onerror="this.onerror=null; this.src='/public/images/suryanz-logo.svg';">
        </div>
        <p style="color: rgba(255,255,255,0.75); line-height: 1.7; margin-bottom: 1.25rem;">
          Powering a Brighter Tomorrow with high-efficiency rooftop solar systems, transparent quotations, and 3-stage customer protection.
        </p>
        <p style="font-size: 0.85rem; color: var(--suryanz-amber); font-weight: 700;">
          <i class="fas fa-award me-1"></i> Backed by 20+ years of team experience in the energy sector.
        </p>
      </div>

      <div class="suryanz-footer-col">
        <h4>Solar Solutions</h4>
        <ul>
          <li><a href="${p}/solutions/residential">Residential Rooftop Solar</a></li>
          <li><a href="${p}/solutions/commercial">Commercial Rooftop Solar</a></li>
          <li><a href="${p}/solutions/industrial">Industrial Solar Systems</a></li>
          <li><a href="${p}/solutions/epc">Solar EPC Services</a></li>
          <li><a href="${p}/solutions/on-grid">On-Grid Systems</a></li>
          <li><a href="${p}/solutions/hybrid">Hybrid Solar + Battery</a></li>
          <li><a href="${p}/solutions/off-grid">Off-Grid Remote Energy</a></li>
          <li><a href="${p}/solutions/solar-battery">Solar Battery Systems</a></li>
          <li><a href="${p}/solutions/apartments">Housing Societies</a></li>
          <li><a href="${p}/solutions/operations-maintenance">Solar O&M / AMC</a></li>
        </ul>
      </div>

      <div class="suryanz-footer-col">
        <h4>Knowledge & Guides</h4>
        <ul>
          <li><a href="${p}/solar-guide">Solar Buyer's Guide</a></li>
          <li><a href="${p}/solar-pricing">Rooftop Solar Cost Guide</a></li>
          <li><a href="${p}/solar-roi">Solar ROI & Financial Guide</a></li>
          <li><a href="${p}/solar-calculator-guide">Capacity Sizing Guide</a></li>
          <li><a href="${p}/solar-warranty-guide">Warranty Portfolio Guide</a></li>
          <li><a href="${p}/solar-maintenance">Solar Maintenance Guide</a></li>
          <li><a href="${p}/solar-buying-guide">Solar System Comparison</a></li>
        </ul>
      </div>

      <div class="suryanz-footer-col">
        <h4>Regional Service Hubs</h4>
        <ul>
          <li><a href="${p}/location/andhra-pradesh">Andhra Pradesh Solar Hub</a></li>
          <li><a href="${p}/location/telangana">Telangana Solar Hub</a></li>
          <li><a href="${p}/location/karnataka">Karnataka Solar Hub</a></li>
          <li><a href="${p}/location/visakhapatnam">Visakhapatnam Solar EPC</a></li>
          <li><a href="${p}/location/vijayawada">Vijayawada Rooftop Solar</a></li>
          <li><a href="${p}/location/hyderabad">Hyderabad Commercial Solar</a></li>
          <li><a href="${p}/location/bengaluru">Bengaluru Residential Solar</a></li>
          <li><a href="${p}/location/mangalore">Mangalore Solar Solutions</a></li>
        </ul>
      </div>

      <div class="suryanz-footer-col">
        <h4>Company & Trust</h4>
        <ul>
          <li><a href="${p}/about">About SURYANZ</a></li>
          <li><a href="${p}/why-suryanz">Why Suryanz Solar</a></li>
          <li><a href="${p}/customer-protection">Customer Protection</a></li>
          <li><a href="${p}/technology">Technology Specifications</a></li>
          <li><a href="${p}/calculator">Solar Calculator</a></li>
          <li><a href="${p}/projects">Case Studies & Projects</a></li>
          <li><a href="${p}/customer-stories">Customer Stories</a></li>
          <li><a href="${p}/faqs">FAQs</a></li>
          <li><a href="${p}/contact">Contact & Consult</a></li>
        </ul>
      </div>
    </div>

    <div class="suryanz-footer-bottom">
      <div>
        &copy; ${new Date().getFullYear()} SURYANZ / SURYANZ SOLAR. All Rights Reserved.
      </div>
      <div style="display: flex; gap: 1.5rem;">
        <a href="${p}/legal/privacy-policy" style="color: rgba(255,255,255,0.75); text-decoration: none;">Privacy Policy</a>
        <a href="${p}/legal/terms-and-conditions" style="color: rgba(255,255,255,0.75); text-decoration: none;">Terms & Conditions</a>
        <a href="${p}/legal/warranty-terms" style="color: rgba(255,255,255,0.75); text-decoration: none;">Warranty Terms</a>
      </div>
    </div>
  </footer>`;
}

function renderSuryanzPage({
  title,
  description,
  canonicalUrl = 'https://suryanzsolar.com/',
  activePath = '/',
  bodyContent,
  jsonLd = null,
  urlPrefix = ''
}) {
  const defaultSchema = {
    "@context": "https://schema.org",
    "@type": "Organization",
    "name": "SURYANZ SOLAR",
    "legalName": "SURYANZ SOLAR",
    "url": "https://suryanzsolar.com",
    "logo": "https://suryanzsolar.com/public/images/suryanz-logo-transparent.png",
    "description": "Premium Solar Energy Solutions for Homes and Businesses in India. Backed by 20+ years of team experience.",
    "slogan": "Powering a Brighter Tomorrow",
    "sameAs": []
  };

  const schemaJson = jsonLd ? JSON.stringify(jsonLd) : JSON.stringify(defaultSchema);

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${title} | SURYANZ SOLAR</title>
  <meta name="description" content="${description}">
  <link rel="canonical" href="${canonicalUrl}">
  <meta property="og:title" content="${title} | SURYANZ SOLAR">
  <meta property="og:description" content="${description}">
  <meta property="og:type" content="website">
  <meta property="og:url" content="${canonicalUrl}">
  <meta name="twitter:card" content="summary_large_image">
  <link rel="icon" type="image/svg+xml" href="/public/images/suryanz-logo.svg">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <link rel="stylesheet" href="/public/css/suryanz-brand.css">
  <script type="application/ld+json">${schemaJson}</script>
</head>
<body class="suryanz-body">
  ${getSuryanzHeader(activePath, urlPrefix)}
  <main role="main">
    ${bodyContent}
  </main>
  ${getSuryanzFooter(urlPrefix)}
  <script src="/public/js/suryanz-calculator.js" defer></script>
  <script src="/public/js/suryanz-lead-form.js" defer></script>
</body>
</html>`;
}

// ===================== SPECIFIC ROUTE RENDERERS =====================

function renderHomePage(urlPrefix = '') {
  const p = (urlPrefix && urlPrefix.endsWith('/')) ? urlPrefix.slice(0, -1) : urlPrefix;
  const content = `
  <!-- Section 1: Hero -->
  <section class="suryanz-hero-section">
    <div class="suryanz-hero-container">
      <div>
        <div class="suryanz-badge-tag">
          <i class="fas fa-award"></i> Backed by 20+ Years of Team Energy Experience
        </div>
        <h1 class="suryanz-hero-title">
          SURYANZ SOLAR <br>
          <span>Powering a Brighter Tomorrow</span>
        </h1>
        <p class="suryanz-hero-subtitle">
          Smart Solar. Reliable Energy. A Better Future. High-efficiency rooftop solar systems for residential homes, commercial hubs, and industrial plants engineered with total transparency.
        </p>
        <div class="suryanz-hero-ctas">
          <a href="${p}/contact" class="suryanz-btn-cta"><i class="fas fa-file-invoice"></i> Get a Free Solar Assessment</a>
          <a href="${p}/calculator" class="suryanz-btn-amber"><i class="fas fa-calculator"></i> Calculate Solar Savings</a>
          <a href="${p}/technology" class="suryanz-btn-outline" style="border-color:#fff; color:#fff!important;"><i class="fas fa-microchip"></i> View Technology Specs</a>
        </div>
      </div>
      <div>
        <div class="suryanz-calc-card">
          <h3 style="margin-top:0; font-size:1.35rem; color:var(--suryanz-navy-dark); font-weight:800; margin-bottom:1rem;">
            Request Solar Callback
          </h3>
          <form class="suryanz-lead-form">
            <div class="suryanz-form-group">
              <label class="suryanz-form-label">Full Name *</label>
              <input type="text" name="name" class="suryanz-form-input" placeholder="e.g. Rajesh Kumar" required>
            </div>
            <div class="suryanz-form-group">
              <label class="suryanz-form-label">Mobile Number *</label>
              <input type="tel" name="phone" class="suryanz-form-input" placeholder="10-digit mobile number" required>
            </div>
            <div class="suryanz-form-group">
              <label class="suryanz-form-label">City / Location *</label>
              <input type="text" name="city" class="suryanz-form-input" placeholder="e.g. Visakhapatnam / Hyderabad" required>
            </div>
            <div class="suryanz-form-group">
              <label class="suryanz-form-label">Monthly Electricity Bill (₹)</label>
              <input type="number" name="monthly_bill" class="suryanz-form-input" placeholder="e.g. 6000">
            </div>
            <button type="submit" class="suryanz-btn-cta" style="width:100%; justify-content:center; padding: 0.8rem;">
              Get a Free Solar Assessment
            </button>
          </form>
        </div>
      </div>
    </div>
  </section>

  <!-- Section 2: Visual Process Journey (01 ASSESS → 06 SUPPORT) -->
  <section class="suryanz-section" style="background:#ffffff;">
    <div class="suryanz-container">
      <div class="suryanz-section-header">
        <h2 class="suryanz-section-title">Solar, Engineered Around Your Future</h2>
        <p class="suryanz-section-subtitle">
          From shadow analysis to net-metering and 25 years of monitoring, every SURYANZ SOLAR installation follows an uncompromised 6-step engineering methodology.
        </p>
      </div>

      <div class="suryanz-process-grid">
        <div class="suryanz-process-step">
          <div class="suryanz-step-num">01</div>
          <div class="suryanz-step-title">ASSESS</div>
          <div class="suryanz-step-desc">Shadow analysis & structural roof evaluation.</div>
        </div>
        <div class="suryanz-process-step">
          <div class="suryanz-step-num">02</div>
          <div class="suryanz-step-title">DESIGN</div>
          <div class="suryanz-step-desc">Load profiling & precision 3D module layout.</div>
        </div>
        <div class="suryanz-process-step">
          <div class="suryanz-step-num">03</div>
          <div class="suryanz-step-title">INSTALL</div>
          <div class="suryanz-step-desc">Weather-proof mounting & safety-certified wiring.</div>
        </div>
        <div class="suryanz-process-step">
          <div class="suryanz-step-num">04</div>
          <div class="suryanz-step-title">VERIFY</div>
          <div class="suryanz-step-desc">Multi-point electrical inspection & net-metering.</div>
        </div>
        <div class="suryanz-process-step">
          <div class="suryanz-step-num">05</div>
          <div class="suryanz-step-title">PROTECT</div>
          <div class="suryanz-step-desc">Product & 20-30 year performance warranty documentation.</div>
        </div>
        <div class="suryanz-process-step">
          <div class="suryanz-step-num">06</div>
          <div class="suryanz-step-title">SUPPORT</div>
          <div class="suryanz-step-desc">24/7 digital monitoring & ticketed AMC support.</div>
        </div>
      </div>
    </div>
  </section>

  <!-- Section 3: Solar For Every Scale -->
  <section class="suryanz-section">
    <div class="suryanz-container">
      <div class="suryanz-section-header">
        <h2 class="suryanz-section-title">Solar Energy Solutions for Every Scale</h2>
        <p class="suryanz-section-subtitle">Tailored solar energy architecture designed for residential homes, commercial properties, and large industrial facilities.</p>
      </div>

      <div class="suryanz-grid-3">
        <div class="suryanz-card">
          <div class="suryanz-card-icon"><i class="fas fa-home"></i></div>
          <h3 class="suryanz-card-title">Residential Rooftop Solar</h3>
          <p class="suryanz-card-text">Slash monthly home power bills by up to 80-90% with clean grid-tied or hybrid battery systems built for 25+ year durability.</p>
          <a href="${p}/solutions/residential" class="suryanz-btn-outline" style="font-size:0.85rem;">Explore Residential Solar</a>
        </div>

        <div class="suryanz-card">
          <div class="suryanz-card-icon"><i class="fas fa-building"></i></div>
          <h3 class="suryanz-card-title">Commercial & Business Solar</h3>
          <p class="suryanz-card-text">Reduce operational expenditure for offices, hospitals, institutions, and commercial complexes with accelerated depreciation and tax savings.</p>
          <a href="${p}/solutions/commercial" class="suryanz-btn-outline" style="font-size:0.85rem;">Explore Commercial Solar</a>
        </div>

        <div class="suryanz-card">
          <div class="suryanz-card-icon"><i class="fas fa-industry"></i></div>
          <h3 class="suryanz-card-title">Industrial Solar & Turnkey EPC</h3>
          <p class="suryanz-card-text">High-capacity MW-scale rooftop and ground-mounted solar installations engineered for manufacturing plants and heavy industry.</p>
          <a href="${p}/solutions/epc" class="suryanz-btn-outline" style="font-size:0.85rem;">Explore Solar EPC</a>
        </div>
      </div>
    </div>
  </section>

  <!-- Section 4: Customer Protection & Warranty Portfolio -->
  <section class="suryanz-section" style="background:#ffffff;">
    <div class="suryanz-container">
      <div class="suryanz-section-header">
        <h2 class="suryanz-section-title">Verified Warranty & Customer Protection</h2>
        <p class="suryanz-section-subtitle">Transparent, documented warranty portfolios backed by rigorous quality checks.</p>
      </div>

      <div class="suryanz-grid-3" style="margin-bottom:3rem;">
        <div class="suryanz-warranty-badge">
          <div class="suryanz-warranty-num">12 Years</div>
          <div class="suryanz-warranty-label">Module Product Warranty</div>
          <p style="font-size:0.85rem; color:rgba(255,255,255,0.75);">Guarantees zero manufacturing or material defects on solar panels.</p>
        </div>

        <div class="suryanz-warranty-badge" style="border-top-color: var(--suryanz-green);">
          <div class="suryanz-warranty-num">8–10 Yrs</div>
          <div class="suryanz-warranty-label">Inverter System Warranty</div>
          <p style="font-size:0.85rem; color:rgba(255,255,255,0.75);">Category-dependent warranty coverage for string & hybrid inverters.</p>
        </div>

        <div class="suryanz-warranty-badge" style="border-top-color: #3b82f6;">
          <div class="suryanz-warranty-num">20–30 Yrs</div>
          <div class="suryanz-warranty-label">Linear Performance Warranty</div>
          <p style="font-size:0.85rem; color:rgba(255,255,255,0.75);">Guarantees up to 80-85% power generation output over 20-30 years.</p>
        </div>
      </div>
    </div>
  </section>
  `;

  return renderSuryanzPage({
    title: 'SURYANZ SOLAR | Premium Solar Energy Solutions for Homes & Businesses',
    description: 'SURYANZ SOLAR provides high-efficiency residential, commercial, and EPC solar rooftop systems. Backed by 20+ years of team experience and 3-stage customer protection.',
    canonicalUrl: 'https://suryanzsolar.com/',
    activePath: '/',
    bodyContent: content,
    urlPrefix: urlPrefix
  });
}

function renderAboutPage(urlPrefix = '') {
  const content = `
  <section class="suryanz-hero-section" style="padding: 3.5rem 1.5rem;">
    <div class="suryanz-container">
      <h1 class="suryanz-hero-title">About SURYANZ & SURYANZ SOLAR</h1>
      <p class="suryanz-hero-subtitle">
        Building India's most trusted, engineering-driven clean energy platform.
      </p>
    </div>
  </section>

  <section class="suryanz-section">
    <div class="suryanz-container">
      <div class="suryanz-grid-3">
        <div class="suryanz-card" style="grid-column: span 2;">
          <h2 style="font-size:1.8rem; font-weight:800; color:var(--suryanz-navy-dark); margin-bottom:1rem;">
            Our Master Energy Vision & Brand Mandate
          </h2>
          <p style="font-size:1.05rem; color:var(--suryanz-text-dark); line-height:1.7;">
            SURYANZ is established as a master corporate energy brand dedicated to sustainable power solutions across India. SURYANZ SOLAR is our specialized solar division delivering turnkey rooftop solar systems for residential homes, commercial complexes, industrial units, and housing societies.
          </p>
          <p style="font-size:1.05rem; color:var(--suryanz-text-dark); line-height:1.7;">
            We believe adopting solar energy must be transparent, financially intelligent, and protective of the customer's long-term investment. Every SURYANZ SOLAR system utilizes 540W to 580W class TOPCon and N-type module configurations backed by our 3-stage Customer Protection Framework.
          </p>
          <div style="background: rgba(245, 158, 11, 0.1); border-left: 4px solid var(--suryanz-amber); padding: 1.25rem; margin-top: 1.5rem; border-radius: 6px;">
            <strong style="color:var(--suryanz-navy-dark);">Verified Experience Positioning:</strong><br>
            <em>"Combining decades of collective team experience with modern solar engineering, Suryanz Solar is built around quality, transparency, and long-term customer value."</em>
          </div>
        </div>

        <div class="suryanz-card" style="background: var(--suryanz-navy-dark); color: #ffffff;">
          <h3 style="color:var(--suryanz-amber); font-size:1.4rem; font-weight:700; margin-top:0;">Core Pillars</h3>
          <ul style="padding-left:1.2rem; line-height:2; color:rgba(255,255,255,0.85);">
            <li><strong>Engineering First:</strong> Structural safety & shadow audits.</li>
            <li><strong>Total Transparency:</strong> Itemized quotations & zero hidden costs.</li>
            <li><strong>Customer Protection:</strong> Documented warranty portfolios.</li>
            <li><strong>Long-Term Support:</strong> Service escalation & preventive AMC.</li>
          </ul>
        </div>
      </div>
    </div>
  </section>`;

  return renderSuryanzPage({
    title: 'About SURYANZ SOLAR | Engineering Excellence & Clean Energy Vision',
    description: 'Learn about SURYANZ and SURYANZ SOLAR. Backed by 20+ years of collective team energy experience, high-efficiency TOPCon modules, and customer protection.',
    canonicalUrl: 'https://suryanzsolar.com/about',
    activePath: '/about',
    bodyContent: content,
    urlPrefix: urlPrefix
  });
}

function renderWhySuryanzPage(urlPrefix = '') {
  const content = `
  <section class="suryanz-hero-section" style="padding: 3.5rem 1.5rem;">
    <div class="suryanz-container">
      <h1 class="suryanz-hero-title">Why Choose Suryanz Solar</h1>
      <p class="suryanz-hero-subtitle">
        Discover how our engineering excellence, customer protection, and transparent pricing set us apart from generic local dealers.
      </p>
    </div>
  </section>

  <section class="suryanz-section">
    <div class="suryanz-container">
      <div class="suryanz-grid-3">
        <div class="suryanz-card">
          <div class="suryanz-card-icon"><i class="fas fa-calculator"></i></div>
          <h3 class="suryanz-card-title">Transparent Itemized Quotations</h3>
          <p class="suryanz-card-text">Every proposal clearly itemizes module specs, inverter class, AC/DC protection, mounting structure gauge, and installation scope. Zero surprise fees.</p>
        </div>

        <div class="suryanz-card">
          <div class="suryanz-card-icon"><i class="fas fa-shield-alt"></i></div>
          <h3 class="suryanz-card-title">3-Stage Customer Protection</h3>
          <p class="suryanz-card-text">Before, during, and after installation checks ensure structural safety, safety-certified wiring, net-metering assistance, and long-term AMC support.</p>
        </div>

        <div class="suryanz-card">
          <div class="suryanz-card-icon"><i class="fas fa-microchip"></i></div>
          <h3 class="suryanz-card-title">540W–580W TOPCon Tech</h3>
          <p class="suryanz-card-text">High-efficiency solar module configurations maximizing daily generation per square foot, even under high ambient temperatures.</p>
        </div>
      </div>
    </div>
  </section>`;

  return renderSuryanzPage({
    title: 'Why Choose Suryanz Solar | Engineering & Transparency',
    description: 'Discover why homeowners and commercial businesses choose SURYANZ SOLAR for transparent quotations, TOPCon tech, and 3-stage customer protection.',
    canonicalUrl: 'https://suryanzsolar.com/why-suryanz',
    activePath: '/why-suryanz',
    bodyContent: content,
    urlPrefix: urlPrefix
  });
}

function renderCustomerProtectionPage(urlPrefix = '') {
  const content = `
  <section class="suryanz-hero-section" style="padding: 3.5rem 1.5rem;">
    <div class="suryanz-container">
      <h1 class="suryanz-hero-title">Suryanz Solar Customer Protection Framework</h1>
      <p class="suryanz-hero-subtitle">
        Our structured 3-phase framework ensures total peace of mind from initial site evaluation to 25 years of clean energy generation.
      </p>
    </div>
  </section>

  <section class="suryanz-section">
    <div class="suryanz-container">
      <table class="suryanz-protection-table">
        <thead>
          <tr>
            <th>Phase 1: Before Installation</th>
            <th>Phase 2: During Installation</th>
            <th>Phase 3: After Installation</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>
              <strong>• Shadow & Roof Assessment:</strong> 3D solar irradiance audit.<br>
              <strong>• Accurate Sizing:</strong> Based on 12-month bill analysis.<br>
              <strong>• Scope Transparency:</strong> Itemized components & ROI model.
            </td>
            <td>
              <strong>• Structural Safety:</strong> Weather-proof mounting & wind rating.<br>
              <strong>• Quality Inspection:</strong> Multi-point electrical checklist.<br>
              <strong>• Commissioning:</strong> Net-metering & grid connectivity.
            </td>
            <td>
              <strong>• Document Retention:</strong> Complete product & linear warranties.<br>
              <strong>• Monitoring:</strong> Digital power generation tracking.<br>
              <strong>• Service Support:</strong> Ticketed escalation & AMC options.
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>`;

  return renderSuryanzPage({
    title: 'Customer Protection Framework | SURYANZ SOLAR',
    description: 'Explore the Suryanz Solar 3-Stage Customer Protection Framework ensuring site assessment transparency, structural safety, and long-term warranty support.',
    canonicalUrl: 'https://suryanzsolar.com/customer-protection',
    activePath: '/customer-protection',
    bodyContent: content,
    urlPrefix: urlPrefix
  });
}

function renderTechnologyPage(urlPrefix = '') {
  const content = `
  <section class="suryanz-hero-section" style="padding: 3.5rem 1.5rem;">
    <div class="suryanz-container">
      <h1 class="suryanz-hero-title">Solar Module & Inverter Technology</h1>
      <p class="suryanz-hero-subtitle">
        High-efficiency 540W, 550W, and 580W class TOPCon and N-type module configurations engineered for maximum solar energy yield.
      </p>
    </div>
  </section>

  <section class="suryanz-section">
    <div class="suryanz-container">
      <div class="suryanz-grid-3">
        <div class="suryanz-card">
          <div class="suryanz-card-icon"><i class="fas fa-sun"></i></div>
          <h3 class="suryanz-card-title">TOPCon Module Technology</h3>
          <p class="suryanz-card-text">Tunnel Oxide Passivated Contact cells providing up to 22.5%+ module efficiency, lower degradation, and superior high-temperature performance.</p>
        </div>

        <div class="suryanz-card">
          <div class="suryanz-card-icon"><i class="fas fa-bolt"></i></div>
          <h3 class="suryanz-card-title">Advanced String & Hybrid Inverters</h3>
          <p class="suryanz-card-text">High-efficiency MPPT string inverters and hybrid storage inverters with up to 98.6% conversion efficiency and mobile monitoring app integration.</p>
        </div>

        <div class="suryanz-card">
          <div class="suryanz-card-icon"><i class="fas fa-layer-group"></i></div>
          <h3 class="suryanz-card-title">Weather-Proof Structure Engineering</h3>
          <p class="suryanz-card-text">Galvanized iron (GI) and aluminum mounting structures engineered to withstand wind speeds up to 150-170 km/h with corrosion resistance.</p>
        </div>
      </div>
    </div>
  </section>`;

  return renderSuryanzPage({
    title: 'Technology & Specifications | SURYANZ SOLAR',
    description: 'Explore SURYANZ SOLAR technology: 540W to 580W TOPCon modules, N-type cells, advanced MPPT string inverters, and GI mounting structures.',
    canonicalUrl: 'https://suryanzsolar.com/technology',
    activePath: '/technology',
    bodyContent: content,
    urlPrefix: urlPrefix
  });
}

function renderCalculatorPage(urlPrefix = '') {
  const p = (urlPrefix && urlPrefix.endsWith('/')) ? urlPrefix.slice(0, -1) : urlPrefix;
  const content = `
  <section class="suryanz-hero-section" style="padding: 3.5rem 1.5rem;">
    <div class="suryanz-container">
      <h1 class="suryanz-hero-title">Interactive Solar Savings Calculator</h1>
      <p class="suryanz-hero-subtitle">
        Estimate your recommended solar capacity, annual electricity savings, payback period, and 25-year generation.
      </p>
    </div>
  </section>

  <section class="suryanz-section">
    <div class="suryanz-container">
      <div class="suryanz-grid-3">
        <div class="suryanz-calc-card">
          <h3 style="margin-top:0; font-size:1.35rem; color:var(--suryanz-navy-dark); font-weight:800; margin-bottom:1.25rem;">Calculator Inputs</h3>
          <form id="suryanz-calc-form">
            <div class="suryanz-form-group">
              <label class="suryanz-form-label">Monthly Electricity Bill (₹)</label>
              <input type="number" id="calc-monthly-bill" class="suryanz-form-input" value="6000" step="500">
            </div>
            <div class="suryanz-form-group">
              <label class="suryanz-form-label">Customer Type</label>
              <select id="calc-customer-type" class="suryanz-form-select">
                <option value="residential">Residential Home</option>
                <option value="commercial">Commercial / Factory</option>
              </select>
            </div>
            <div class="suryanz-form-group">
              <label class="suryanz-form-label">Available Shade-Free Roof Area (sq. ft.)</label>
              <input type="number" id="calc-roof-area" class="suryanz-form-input" value="600" step="50">
            </div>
          </form>
        </div>

        <div class="suryanz-calc-results" style="grid-column: span 2;">
          <h3 style="color:#ffffff; margin-top:0; font-size:1.35rem; font-weight:800; margin-bottom:1.5rem;">Indicative Financial & Generation Output</h3>

          <div class="suryanz-grid-3" style="gap:1.25rem; margin-bottom:1.5rem;">
            <div style="background:rgba(255,255,255,0.06); padding:1.25rem; border-radius:8px;">
              <div class="suryanz-stat-lbl">Recommended System Size</div>
              <div class="suryanz-stat-val" id="res-capacity-kw">5.0 kW</div>
            </div>
            <div style="background:rgba(255,255,255,0.06); padding:1.25rem; border-radius:8px;">
              <div class="suryanz-stat-lbl">Estimated Annual Generation</div>
              <div class="suryanz-stat-val" id="res-annual-gen">7,250 kWh</div>
            </div>
            <div style="background:rgba(255,255,255,0.06); padding:1.25rem; border-radius:8px;">
              <div class="suryanz-stat-lbl">Estimated Annual Savings</div>
              <div class="suryanz-stat-val" id="res-annual-sav">₹58,000</div>
            </div>
          </div>

          <div style="display:grid; grid-template-columns:1fr 1fr; gap:1.25rem; margin-bottom:1.5rem;">
            <div style="background:rgba(255,255,255,0.06); padding:1.25rem; border-radius:8px;">
              <div class="suryanz-stat-lbl">Estimated Payback Period</div>
              <div class="suryanz-stat-val" id="res-payback-yrs">4.8 Years</div>
            </div>
            <div style="background:rgba(255,255,255,0.06); padding:1.25rem; border-radius:8px;">
              <div class="suryanz-stat-lbl">25-Yr CO₂ Reduction Offset</div>
              <div class="suryanz-stat-val" id="res-co2-tons">133.8 Tons</div>
            </div>
          </div>

          <p style="font-size:0.85rem; color:rgba(255,255,255,0.65); font-style:italic;">
            * Note: All values are indicative estimates. Final system design, component configuration, net-metering eligibility, and financial payback require a physical site assessment.
          </p>

          <div style="margin-top:1.5rem;">
            <a href="${p}/contact" class="suryanz-btn-cta"><i class="fas fa-calendar-check"></i> Book Site Assessment For This System</a>
          </div>
        </div>
      </div>
    </div>
  </section>`;

  return renderSuryanzPage({
    title: 'Solar Savings Calculator | SURYANZ SOLAR',
    description: 'Calculate your rooftop solar capacity, annual electricity savings, payback period, and 25-year solar generation with Suryanz Solar.',
    canonicalUrl: 'https://suryanzsolar.com/calculator',
    activePath: '/calculator',
    bodyContent: content,
    urlPrefix: urlPrefix
  });
}

function renderProjectsPage(urlPrefix = '') {
  const content = `
  <section class="suryanz-hero-section" style="padding: 3.5rem 1.5rem;">
    <div class="suryanz-container">
      <h1 class="suryanz-hero-title">Solar Projects & Case Studies</h1>
      <p class="suryanz-hero-subtitle">
        Explore representative rooftop solar installations across residential, commercial, and industrial engineering categories.
      </p>
    </div>
  </section>

  <section class="suryanz-section">
    <div class="suryanz-container">
      <div class="suryanz-grid-3">
        <div class="suryanz-card">
          <div class="suryanz-badge-tag">Residential</div>
          <h3 class="suryanz-card-title">10 kW Residential Rooftop System</h3>
          <p class="suryanz-card-text">High-efficiency TOPCon solar module installation with net-metering integration providing 100% power bill offset.</p>
        </div>

        <div class="suryanz-card">
          <div class="suryanz-badge-tag" style="background:rgba(5,150,105,0.15); color:var(--suryanz-green);">Commercial</div>
          <h3 class="suryanz-card-title">50 kW Commercial Rooftop Project</h3>
          <p class="suryanz-card-text">Grid-tied solar installation for a commercial office complex reducing operational peak energy tariffs by 65%.</p>
        </div>

        <div class="suryanz-card">
          <div class="suryanz-badge-tag" style="background:rgba(59,130,246,0.15); color:#3b82f6;">Industrial</div>
          <h3 class="suryanz-card-title">250 kW Industrial Solar EPC</h3>
          <p class="suryanz-card-text">Turnkey industrial rooftop solar project engineered for a manufacturing facility with high-temperature resistance GI structures.</p>
        </div>
      </div>
    </div>
  </section>`;

  return renderSuryanzPage({
    title: 'Solar Case Studies & Projects | SURYANZ SOLAR',
    description: 'Explore SURYANZ SOLAR case studies and project installation categories across residential homes, commercial complexes, and industrial plants.',
    canonicalUrl: 'https://suryanzsolar.com/projects',
    activePath: '/projects',
    bodyContent: content,
    urlPrefix: urlPrefix
  });
}

function renderCustomerStoriesPage(urlPrefix = '') {
  const p = (urlPrefix && urlPrefix.endsWith('/')) ? urlPrefix.slice(0, -1) : urlPrefix;
  const content = `
  <section class="suryanz-hero-section" style="padding: 3.5rem 1.5rem;">
    <div class="suryanz-container">
      <h1 class="suryanz-hero-title">Customer Stories & Reviews</h1>
      <p class="suryanz-hero-subtitle">
        Genuine feedback from homeowners and businesses powered by Suryanz Solar energy systems.
      </p>
    </div>
  </section>

  <section class="suryanz-section">
    <div class="suryanz-container">
      <div style="background:#ffffff; border:1px solid var(--suryanz-border-color); padding:3rem; text-align:center; border-radius:10px;">
        <i class="fas fa-folder-open" style="font-size:3rem; color:var(--suryanz-amber); margin-bottom:1rem;"></i>
        <h2 style="font-size:1.8rem; font-weight:800; color:var(--suryanz-navy-dark);">Verified Customer Reviews Pending Publication</h2>
        <p style="font-size:1.05rem; color:var(--suryanz-text-muted); max-width:600px; margin:0.75rem auto 1.5rem auto;">
          In strict compliance with our zero-fabrication policy, customer testimonials and project photos are published only after third-party verification and customer authorization.
        </p>
        <a href="${p}/contact" class="suryanz-btn-cta"><i class="fas fa-paper-plane"></i> Submit Customer Review</a>
      </div>
    </div>
  </section>`;

  return renderSuryanzPage({
    title: 'Customer Stories & Reviews | SURYANZ SOLAR',
    description: 'Verified customer feedback and testimonials for SURYANZ SOLAR rooftop systems in India.',
    canonicalUrl: 'https://suryanzsolar.com/customer-stories',
    activePath: '/customer-stories',
    bodyContent: content,
    urlPrefix: urlPrefix
  });
}

function renderFaqsPage(urlPrefix = '') {
  const content = `
  <section class="suryanz-hero-section" style="padding: 3.5rem 1.5rem;">
    <div class="suryanz-container">
      <h1 class="suryanz-hero-title">Frequently Asked Questions (FAQs)</h1>
      <p class="suryanz-hero-subtitle">
        Everything you need to know about rooftop solar, net-metering, ROI calculations, and warranties.
      </p>
    </div>
  </section>

  <section class="suryanz-section">
    <div class="suryanz-container" style="max-width:900px;">
      <div class="suryanz-card" style="margin-bottom:1.25rem;">
        <h3 class="suryanz-card-title">How much can I save on electricity bills with rooftop solar?</h3>
        <p class="suryanz-card-text">Depending on your monthly power consumption and tariff rates, a properly sized Suryanz Solar system can reduce monthly electricity bills by up to 80% to 90% through net-metering.</p>
      </div>

      <div class="suryanz-card" style="margin-bottom:1.25rem;">
        <h3 class="suryanz-card-title">What warranties are included with Suryanz Solar systems?</h3>
        <p class="suryanz-card-text">Suryanz Solar provides a 12-Year Module Product Warranty, Inverter coverage up to 8–10 years (category-dependent), and a 20–30 Year Linear Performance Warranty on solar modules.</p>
      </div>

      <div class="suryanz-card" style="margin-bottom:1.25rem;">
        <h3 class="suryanz-card-title">What is net-metering and how does it work?</h3>
        <p class="suryanz-card-text">Net-metering is a bi-directional electricity meter mechanism that credits solar energy system owners for the excess electricity fed back into the DISCOM power grid.</p>
      </div>

      <div class="suryanz-card">
        <h3 class="suryanz-card-title">What is the typical financial payback period?</h3>
        <p class="suryanz-card-text">The average payback period for residential and commercial rooftop solar systems in India ranges between 3.5 to 5.5 years, depending on local DISCOM electricity tariffs.</p>
      </div>
    </div>
  </section>`;

  return renderSuryanzPage({
    title: 'Rooftop Solar FAQs | SURYANZ SOLAR',
    description: 'Find answers to common questions about rooftop solar installation, net-metering, ROI payback, and warranty coverage with Suryanz Solar.',
    canonicalUrl: 'https://suryanzsolar.com/faqs',
    activePath: '/faqs',
    bodyContent: content,
    urlPrefix: urlPrefix
  });
}

function renderContactPage(urlPrefix = '') {
  const content = `
  <section class="suryanz-hero-section" style="padding: 3.5rem 1.5rem;">
    <div class="suryanz-container">
      <h1 class="suryanz-hero-title">Contact SURYANZ SOLAR</h1>
      <p class="suryanz-hero-subtitle">
        Request a free solar site assessment, schedule a callback, or consult our engineering team.
      </p>
    </div>
  </section>

  <section class="suryanz-section">
    <div class="suryanz-container">
      <div class="suryanz-grid-3">
        <div class="suryanz-card" style="grid-column: span 2;">
          <h3 style="margin-top:0; font-size:1.5rem; color:var(--suryanz-navy-dark); font-weight:800; margin-bottom:1.25rem;">
            Request a Free Solar Assessment & Consultation
          </h3>
          <form class="suryanz-lead-form">
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:1rem;">
              <div class="suryanz-form-group">
                <label class="suryanz-form-label">Full Name *</label>
                <input type="text" name="name" class="suryanz-form-input" placeholder="Your name" required>
              </div>
              <div class="suryanz-form-group">
                <label class="suryanz-form-label">Mobile Number *</label>
                <input type="tel" name="phone" class="suryanz-form-input" placeholder="10-digit mobile" required>
              </div>
            </div>

            <div style="display:grid; grid-template-columns:1fr 1fr; gap:1rem;">
              <div class="suryanz-form-group">
                <label class="suryanz-form-label">Email Address</label>
                <input type="email" name="email" class="suryanz-form-input" placeholder="name@domain.com">
              </div>
              <div class="suryanz-form-group">
                <label class="suryanz-form-label">City / Region *</label>
                <input type="text" name="city" class="suryanz-form-input" placeholder="City name" required>
              </div>
            </div>

            <div style="display:grid; grid-template-columns:1fr 1fr; gap:1rem;">
              <div class="suryanz-form-group">
                <label class="suryanz-form-label">Customer Type</label>
                <select name="customer_type" class="suryanz-form-select">
                  <option value="residential">Residential Home</option>
                  <option value="commercial">Commercial / Factory</option>
                  <option value="society">Apartment / Society</option>
                </select>
              </div>
              <div class="suryanz-form-group">
                <label class="suryanz-form-label">Monthly Electricity Bill (₹)</label>
                <input type="number" name="monthly_bill" class="suryanz-form-input" placeholder="e.g. 8000">
              </div>
            </div>

            <button type="submit" class="suryanz-btn-cta" style="padding:0.85rem 2rem;">
              Submit Solar Assessment Request
            </button>
          </form>
        </div>

        <div class="suryanz-card" style="background:var(--suryanz-navy-dark); color:#ffffff;">
          <h3 style="color:var(--suryanz-amber); margin-top:0; font-size:1.3rem; font-weight:700;">Corporate Office Information</h3>
          <p style="margin-top:1rem; color:rgba(255,255,255,0.85); line-height:1.7;">
            <strong>Registered Business Address:</strong><br>
            [VERIFIED SURYANZ BUSINESS ADDRESS]
          </p>
          <p style="margin-top:1.25rem; color:rgba(255,255,255,0.85); line-height:1.7;">
            <strong>Digital Support Hub:</strong><br>
            Website: <a href="https://suryanzsolar.com" style="color:var(--suryanz-amber);">suryanzsolar.com</a><br>
            Corporate: <a href="https://suryanz.com" style="color:var(--suryanz-amber);">suryanz.com</a>
          </p>
        </div>
      </div>
    </div>
  </section>`;

  return renderSuryanzPage({
    title: 'Contact Us | SURYANZ SOLAR',
    description: 'Get in touch with SURYANZ SOLAR for a free rooftop solar site assessment, project quotation, or engineering consultation.',
    canonicalUrl: 'https://suryanzsolar.com/contact',
    activePath: '/contact',
    bodyContent: content,
    urlPrefix: urlPrefix
  });
}

function renderSolutionPage(solutionSlug, urlPrefix = '') {
  const solTitles = {
    'residential': 'Residential Rooftop Solar Systems',
    'commercial': 'Commercial Solar Energy Systems',
    'industrial': 'Industrial Solar & Utility EPC',
    'epc': 'Turnkey Solar EPC Services',
    'on-grid': 'On-Grid (Grid-Tied) Solar Systems',
    'hybrid': 'Hybrid Solar + Battery Energy Storage',
    'off-grid': 'Off-Grid Remote Energy Systems',
    'solar-battery': 'Solar Battery Storage Systems',
    'apartments': 'Solar Solutions for Housing Societies',
    'operations-maintenance': 'Solar Operations & Maintenance (O&M / AMC)'
  };

  const title = solTitles[solutionSlug] || 'Solar Energy Solution';

  const content = `
  <section class="suryanz-hero-section" style="padding: 3.5rem 1.5rem;">
    <div class="suryanz-container">
      <div class="suryanz-badge-tag"><i class="fas fa-lightbulb"></i> Solution Spec</div>
      <h1 class="suryanz-hero-title">${title}</h1>
      <p class="suryanz-hero-subtitle">
        Custom engineered ${title.toLowerCase()} utilizing 540W–580W TOPCon technology, 3-stage customer protection, and linear performance warranties.
      </p>
    </div>
  </section>

  <section class="suryanz-section">
    <div class="suryanz-container">
      <div class="suryanz-grid-3">
        <div class="suryanz-card" style="grid-column: span 2;">
          <h2 style="font-size:1.6rem; font-weight:800; color:var(--suryanz-navy-dark); margin-bottom:1rem;">
            Engineering Overview for ${title}
          </h2>
          <p style="font-size:1.05rem; color:var(--suryanz-text-dark); line-height:1.7;">
            SURYANZ SOLAR provides end-to-end engineering execution for ${title.toLowerCase()}. Our engineering team conducts comprehensive site audits, structural roof load evaluations, and shadow profiling to ensure optimal daily energy yield.
          </p>
          <h3 style="font-size:1.25rem; font-weight:700; color:var(--suryanz-navy-dark); margin-top:1.5rem; margin-bottom:0.75rem;">Key Benefits & Inclusions:</h3>
          <ul style="line-height:1.8; color:var(--suryanz-text-dark); padding-left:1.25rem;">
            <li>High-efficiency TOPCon solar modules (540W to 580W class).</li>
            <li>Category-dependent string & hybrid inverters with warranties up to 8–10 years.</li>
            <li>12-Year Product Warranty & 20–30 Year Linear Performance Warranty.</li>
            <li>Heavy-duty GI mounting structures rated for high wind loads.</li>
            <li>Complete DISCOM net-metering & grid connectivity documentation support.</li>
          </ul>
        </div>

        <div>
          <div class="suryanz-calc-card">
            <h3 style="margin-top:0; font-size:1.25rem; font-weight:800; color:var(--suryanz-navy-dark);">Get Quote for ${title}</h3>
            <form class="suryanz-lead-form">
              <div class="suryanz-form-group">
                <label class="suryanz-form-label">Full Name</label>
                <input type="text" name="name" class="suryanz-form-input" required>
              </div>
              <div class="suryanz-form-group">
                <label class="suryanz-form-label">Mobile Number</label>
                <input type="tel" name="phone" class="suryanz-form-input" required>
              </div>
              <input type="hidden" name="interested_solution" value="${title}">
              <button type="submit" class="suryanz-btn-cta" style="width:100%; justify-content:center;">Request Proposal</button>
            </form>
          </div>
        </div>
      </div>
    </div>
  </section>`;

  return renderSuryanzPage({
    title: `${title} | SURYANZ SOLAR`,
    description: `High-efficiency ${title.toLowerCase()} by SURYANZ SOLAR. Engineered with TOPCon module technology, transparent pricing, and 3-stage customer protection.`,
    canonicalUrl: `https://suryanzsolar.com/solutions/${solutionSlug}`,
    activePath: `/solutions/${solutionSlug}`,
    bodyContent: content,
    urlPrefix: urlPrefix
  });
}

function renderKnowledgeGuidePage(guideSlug, urlPrefix = '') {
  const p = (urlPrefix && urlPrefix.endsWith('/')) ? urlPrefix.slice(0, -1) : urlPrefix;
  const guideTitles = {
    'solar-guide': "Solar Energy Buyer's Guide",
    'solar-pricing': 'Rooftop Solar Cost & Pricing Breakdown',
    'solar-roi': 'Solar Financial ROI & Payback Guide',
    'solar-calculator-guide': 'Solar Capacity Sizing Guide',
    'solar-warranty-guide': 'Solar Warranty Portfolio Guide',
    'solar-maintenance': 'Solar Panel Maintenance & AMC Guide',
    'solar-buying-guide': 'How to Choose a Rooftop Solar Company'
  };

  const title = guideTitles[guideSlug] || 'Solar Knowledge Guide';

  const content = `
  <section class="suryanz-hero-section" style="padding: 3.5rem 1.5rem;">
    <div class="suryanz-container">
      <div class="suryanz-badge-tag"><i class="fas fa-book"></i> Educational Resource</div>
      <h1 class="suryanz-hero-title">${title}</h1>
      <p class="suryanz-hero-subtitle">
        Authoritative solar knowledge and financial engineering insights by SURYANZ SOLAR.
      </p>
    </div>
  </section>

  <section class="suryanz-section">
    <div class="suryanz-container" style="max-width:900px;">
      <div class="suryanz-card">
        <h2 style="font-size:1.6rem; font-weight:800; color:var(--suryanz-navy-dark); margin-bottom:1rem;">Understanding ${title}</h2>
        <p style="font-size:1.05rem; color:var(--suryanz-text-dark); line-height:1.7;">
          Investing in rooftop solar is one of the most effective long-term financial decisions for homeowners and commercial businesses in India. When comparing solar solutions, it is essential to look beyond basic kilowatt capacity and evaluate component efficiencies, inverter degradation rates, structural wind ratings, and documented warranty terms.
        </p>
        <h3 style="font-size:1.3rem; font-weight:700; color:var(--suryanz-navy-dark); margin-top:1.5rem; margin-bottom:0.75rem;">Key Evaluation Checklist:</h3>
        <ul style="line-height:1.8; color:var(--suryanz-text-dark); padding-left:1.25rem;">
          <li>Verify whether solar panels use modern TOPCon or N-type cell technology.</li>
          <li>Ensure inverter warranties are clearly category-documented (up to 8-10 years).</li>
          <li>Demand an itemized scope of work covering GI structures, AC/DC protection, and earthing.</li>
          <li>Check DISCOM net-metering eligibility and local solar policy rules.</li>
        </ul>
        <div style="margin-top:2rem;">
          <a href="${p}/calculator" class="suryanz-btn-cta"><i class="fas fa-calculator"></i> Calculate Your Solar ROI Now</a>
        </div>
      </div>
    </div>
  </section>`;

  return renderSuryanzPage({
    title: `${title} | SURYANZ SOLAR`,
    description: `Comprehensive educational guide on ${title.toLowerCase()} by SURYANZ SOLAR. Technical insights, pricing analysis, and warranty standards.`,
    canonicalUrl: `https://suryanzsolar.com/${guideSlug}`,
    activePath: `/${guideSlug}`,
    bodyContent: content,
    urlPrefix: urlPrefix
  });
}

function renderLocationPage(locationSlug, locationName, stateName, urlPrefix = '') {
  const content = `
  <section class="suryanz-hero-section" style="padding: 3.5rem 1.5rem;">
    <div class="suryanz-container">
      <div class="suryanz-badge-tag"><i class="fas fa-map-marker-alt"></i> ${locationName}, ${stateName}</div>
      <h1 class="suryanz-hero-title">SURYANZ SOLAR in ${locationName}</h1>
      <p class="suryanz-hero-subtitle">
        Premium residential, commercial, and industrial rooftop solar installation services in ${locationName}. Backed by 20+ years of team energy experience.
      </p>
    </div>
  </section>

  <section class="suryanz-section">
    <div class="suryanz-container">
      <div class="suryanz-grid-3">
        <div class="suryanz-card" style="grid-column: span 2;">
          <h2 style="font-size:1.6rem; font-weight:800; color:var(--suryanz-navy-dark); margin-bottom:1rem;">
            Rooftop Solar Solutions for ${locationName} Homes & Businesses
          </h2>
          <p style="font-size:1.05rem; color:var(--suryanz-text-dark); line-height:1.7;">
            SURYANZ SOLAR provides comprehensive, engineering-backed solar energy solutions in ${locationName} and surrounding regions. Our local site assessment teams analyze your specific solar irradiance, roof orientation, grid net-metering regulations, and daily load profiles to engineer optimal rooftop systems.
          </p>
          <h3 style="font-size:1.3rem; font-weight:700; color:var(--suryanz-navy-dark); margin-top:1.5rem; margin-bottom:0.75rem;">
            What You Get With Your SURYANZ Solar System in ${locationName}:
          </h3>
          <ul style="line-height:1.8; color:var(--suryanz-text-dark); padding-left:1.25rem;">
            <li>High-efficiency 540W–580W TOPCon & N-type solar modules.</li>
            <li>Category-dependent inverters with warranties up to 8–10 years.</li>
            <li>12-Year Module Product Warranty & up to 20–30 Year Performance Warranty.</li>
            <li>Professional structural weather-proofing & safety-certified wiring.</li>
            <li>Complete documentation assistance for state net-metering approval in ${stateName}.</li>
          </ul>
        </div>

        <div>
          <div class="suryanz-calc-card">
            <h3 style="margin-top:0; font-size:1.25rem; font-weight:800; color:var(--suryanz-navy-dark);">
              Get Solar Assessment in ${locationName}
            </h3>
            <form class="suryanz-lead-form">
              <div class="suryanz-form-group">
                <label class="suryanz-form-label">Your Name</label>
                <input type="text" name="name" class="suryanz-form-input" required>
              </div>
              <div class="suryanz-form-group">
                <label class="suryanz-form-label">Mobile Number</label>
                <input type="tel" name="phone" class="suryanz-form-input" required>
              </div>
              <input type="hidden" name="city" value="${locationName}">
              <button type="submit" class="suryanz-btn-cta" style="width:100%; justify-content:center;">
                Request Call in ${locationName}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  </section>`;

  return renderSuryanzPage({
    title: `Solar Company in ${locationName} | SURYANZ SOLAR`,
    description: `Top rooftop solar installation services in ${locationName}, ${stateName} by SURYANZ SOLAR. High-efficiency modules, net-metering assistance, and 3-stage customer protection.`,
    canonicalUrl: `https://suryanzsolar.com/location/${locationSlug}`,
    activePath: `/location/${locationSlug}`,
    bodyContent: content,
    urlPrefix: urlPrefix
  });
}

function renderLegalPage(legalSlug, urlPrefix = '') {
  const legalTitles = {
    'privacy-policy': 'Privacy Policy',
    'terms-and-conditions': 'Terms & Conditions',
    'warranty-terms': 'Warranty Terms & Conditions'
  };

  const title = legalTitles[legalSlug] || 'Legal Document';

  const content = `
  <section class="suryanz-hero-section" style="padding: 3.5rem 1.5rem;">
    <div class="suryanz-container">
      <h1 class="suryanz-hero-title">${title}</h1>
      <p class="suryanz-hero-subtitle">SURYANZ / SURYANZ SOLAR Customer Privacy & Service Terms</p>
    </div>
  </section>

  <section class="suryanz-section">
    <div class="suryanz-container" style="max-width:900px;">
      <div class="suryanz-card">
        <h2 style="font-size:1.5rem; font-weight:800; color:var(--suryanz-navy-dark); margin-bottom:1rem;">${title}</h2>
        <p style="font-size:1.05rem; color:var(--suryanz-text-dark); line-height:1.7;">
          SURYANZ SOLAR is committed to protecting your privacy, data security, and consumer rights. Information collected via web consultation forms is strictly utilized for system sizing, site survey scheduling, and authorized project communications.
        </p>
        <p style="font-size:1.05rem; color:var(--suryanz-text-dark); line-height:1.7;">
          System warranties (12-Year Product Warranty, Category 8-10 Year Inverter Warranty, and 20-30 Year Linear Performance Warranty) are subject to final project scope documents issued upon commissioning.
        </p>
      </div>
    </div>
  </section>`;

  return renderSuryanzPage({
    title: `${title} | SURYANZ SOLAR`,
    description: `Official ${title.toLowerCase()} for SURYANZ and SURYANZ SOLAR digital platform.`,
    canonicalUrl: `https://suryanzsolar.com/legal/${legalSlug}`,
    activePath: `/legal/${legalSlug}`,
    bodyContent: content,
    urlPrefix: urlPrefix
  });
}

function renderSitemapXml() {
  const pages = [
    '', 'about', 'why-suryanz', 'customer-protection', 'technology', 'calculator', 'projects', 'customer-stories', 'reviews', 'faqs', 'contact',
    'solutions/residential', 'solutions/commercial', 'solutions/industrial', 'solutions/epc', 'solutions/on-grid', 'solutions/hybrid', 'solutions/off-grid', 'solutions/solar-battery', 'solutions/apartments', 'solutions/operations-maintenance',
    'solar-guide', 'solar-pricing', 'solar-roi', 'solar-calculator-guide', 'solar-warranty-guide', 'solar-maintenance', 'solar-buying-guide',
    'location/andhra-pradesh', 'location/telangana', 'location/karnataka', 'location/visakhapatnam', 'location/vijayawada', 'location/hyderabad', 'location/bengaluru', 'location/mangalore',
    'legal/privacy-policy', 'legal/terms-and-conditions', 'legal/warranty-terms'
  ];

  const urlBlocks = pages.map(p => `
  <url>
    <loc>https://suryanzsolar.com/${p}</loc>
    <lastmod>${new Date().toISOString().split('T')[0]}</lastmod>
    <changefreq>${p === '' ? 'daily' : 'weekly'}</changefreq>
    <priority>${p === '' ? '1.0' : '0.8'}</priority>
  </url>`).join('');

  return `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urlBlocks}
</urlset>`;
}

function renderRobotsTxt() {
  return `User-agent: *
Allow: /
Disallow: /api/
Disallow: /admin/
Disallow: /staff/

Sitemap: https://suryanzsolar.com/sitemap.xml
`;
}

module.exports = {
  renderHomePage,
  renderAboutPage,
  renderWhySuryanzPage,
  renderCustomerProtectionPage,
  renderTechnologyPage,
  renderCalculatorPage,
  renderProjectsPage,
  renderCustomerStoriesPage,
  renderFaqsPage,
  renderContactPage,
  renderSolutionPage,
  renderKnowledgeGuidePage,
  renderLocationPage,
  renderLegalPage,
  renderSitemapXml,
  renderRobotsTxt
};
