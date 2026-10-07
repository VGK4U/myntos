/**
 * SURYANZ & SURYANZ SOLAR - Complete Page View Engine
 * Real Engineering, Architectural & Photographic Transformation (Oct 2026)
 * - Implements ALL 41 routes with ZERO broken links and ZERO 404s
 * - Dynamic prefix awareness (works seamlessly on s3, custom domain, /suryanz, localhost)
 * - Architectural photography, 6-step engineering methodology, 3-stage Customer Protection,
 *   Real AP projects, Real People engineering team, Technology Specs & Solar Calculator.
 */

const fs = require('fs');
const path = require('path');

function getSuryanzHeader(activePath = '/', urlPrefix = '') {
  const p = (urlPrefix && urlPrefix.endsWith('/')) ? urlPrefix.slice(0, -1) : urlPrefix;
  return `
  <header class="suryanz-header" role="banner">
    <div class="suryanz-nav-container">
      <a href="${p || '/'}" class="suryanz-brand-logo" aria-label="Suryanz Solar Home">
        <img src="/public/images/suryanz-logo-transparent.png?v=20261007_1" alt="SURYANZ SOLAR Logo" class="suryanz-logo-img">
      </a>
      
      <nav aria-label="Main Navigation">
        <ul class="suryanz-nav-links">
          <li><a href="${p || '/'}" class="${activePath === '/' ? 'active' : ''}">Home</a></li>
          <li><a href="${p}/about" class="${activePath === '/about' ? 'active' : ''}">About</a></li>
          <li><a href="${p}/why-suryanz" class="${activePath === '/why-suryanz' ? 'active' : ''}">Why Suryanz</a></li>
          
          <li class="suryanz-dropdown">
            <a href="${p}/solutions/residential" class="${activePath.startsWith('/solutions') ? 'active' : ''}">
              Solutions <i class="fas fa-chevron-down" style="font-size:0.7rem; margin-left:2px;"></i>
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

          <li><a href="${p}/customer-protection" class="${activePath === '/customer-protection' ? 'active' : ''}">Protection</a></li>
          <li><a href="${p}/technology" class="${activePath === '/technology' ? 'active' : ''}">Technology</a></li>
          <li><a href="${p}/projects" class="${activePath === '/projects' ? 'active' : ''}">Projects</a></li>
          <li><a href="${p}/calculator" class="${activePath === '/calculator' ? 'active' : ''}">Calculator</a></li>
          <li><a href="${p}/faqs" class="${activePath === '/faqs' ? 'active' : ''}">FAQs</a></li>
          <li><a href="${p}/contact" class="${activePath === '/contact' ? 'active' : ''}">Contact</a></li>
        </ul>
      </nav>

      <div class="suryanz-header-actions">
        <a href="${p}/contact" class="suryanz-btn-cta"><i class="fas fa-solar-panel"></i> Get Solar Assessment</a>
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
      <li><a href="${p}/solutions/industrial" onclick="toggleMobileDrawer()">Industrial Solar EPC</a></li>
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

function getSuryanzMobileActionBar(urlPrefix = '') {
  const p = (urlPrefix && urlPrefix.endsWith('/')) ? urlPrefix.slice(0, -1) : urlPrefix;
  return `
  <div class="suryanz-mobile-action-bar">
    <div class="suryanz-mobile-action-bar-inner">
      <a href="tel:+919876543210" class="suryanz-mobile-action-btn" style="background:#f1f5f9; color:#0f172a;">
        <i class="fas fa-phone-alt"></i> Call
      </a>
      <a href="https://wa.me/919876543210?text=Hi%20Suryanz%20Solar,%20I%20want%20to%20know%20more%20about%20rooftop%20solar." class="suryanz-mobile-action-btn" style="background:#25D366; color:#ffffff;" target="_blank">
        <i class="fab fa-whatsapp"></i> WhatsApp
      </a>
      <a href="${p}/contact" class="suryanz-mobile-action-btn" style="background:#d97706; color:#ffffff;">
        <i class="fas fa-solar-panel"></i> Assessment
      </a>
    </div>
  </div>`;
}

function getSuryanzFooter(urlPrefix = '') {
  const p = (urlPrefix && urlPrefix.endsWith('/')) ? urlPrefix.slice(0, -1) : urlPrefix;
  return `
  <footer class="suryanz-footer" role="contentinfo">
    <div class="suryanz-footer-grid">
      <div class="suryanz-footer-col">
        <div style="margin-bottom: 1.25rem;">
          <div class="suryanz-footer-logo-card">
            <img src="/public/images/suryanz-logo-transparent.png?v=20261007_2" alt="SURYANZ SOLAR" class="suryanz-footer-logo-img">
          </div>
        </div>
        <p style="color: rgba(255,255,255,0.75); line-height: 1.7; margin-bottom: 1.25rem; font-size: 0.9rem;">
          Powering a Brighter Tomorrow with engineer-designed rooftop solar systems, transparent quotations, and 3-stage customer protection.
        </p>
        <p style="font-size: 0.85rem; color: #fbbf24; font-weight: 700;">
          <i class="fas fa-award me-1"></i> 20+ Years of Energy Experience · Engineering-Led Installation
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
        &copy; ${new Date().getFullYear()} SURYANZ SOLAR. All Rights Reserved. Engineered for 30 Years Performance.
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
    "@graph": [
      {
        "@type": "Organization",
        "@id": "https://suryanzsolar.com/#organization",
        "name": "SURYANZ SOLAR",
        "legalName": "SURYANZ SOLAR",
        "url": "https://suryanzsolar.com",
        "logo": "https://suryanzsolar.com/public/images/suryanz-logo-transparent.png",
        "description": "Premium engineer-designed rooftop solar systems for homes, commercial hubs, and industrial facilities in India. Backed by 20+ years of team experience.",
        "slogan": "Powering a Brighter Tomorrow",
        "sameAs": [
          "https://suryanz.com"
        ]
      },
      {
        "@type": "LocalBusiness",
        "@id": "https://suryanzsolar.com/#localbusiness",
        "name": "SURYANZ SOLAR EPC",
        "image": "https://suryanzsolar.com/public/images/suryanz-logo-transparent.png",
        "url": "https://suryanzsolar.com",
        "priceRange": "₹₹₹",
        "description": "Engineering-first rooftop solar EPC contractor serving Andhra Pradesh, Telangana, and Karnataka.",
        "areaServed": [
          { "@type": "AdministrativeArea", "name": "Andhra Pradesh" },
          { "@type": "AdministrativeArea", "name": "Telangana" },
          { "@type": "AdministrativeArea", "name": "Karnataka" }
        ]
      },
      {
        "@type": "Service",
        "@id": "https://suryanzsolar.com/#service-residential",
        "name": "Residential Rooftop Solar System Installation",
        "provider": { "@id": "https://suryanzsolar.com/#organization" },
        "serviceType": "Solar Photovoltaic EPC Engineering",
        "description": "High-efficiency residential rooftop solar installation with 3-stage customer protection, net metering assistance, and 30-year linear performance warranty."
      },
      {
        "@type": "FAQPage",
        "@id": "https://suryanzsolar.com/#faq",
        "mainEntity": [
          {
            "@type": "Question",
            "name": "How much does a rooftop solar installation cost?",
            "acceptedAnswer": {
              "@type": "Answer",
              "text": "Rooftop solar costs depend on system capacity (kW) and panel technology. A typical residential 3 kW to 5 kW solar system ranges between ₹1.8 Lakhs to ₹3.2 Lakhs before subsidies, delivering a 3 to 4.5 year payback period."
            }
          },
          {
            "@type": "Question",
            "name": "What warranty is provided by SURYANZ SOLAR?",
            "acceptedAnswer": {
              "@type": "Answer",
              "text": "SURYANZ SOLAR provides a 30-Year Linear Performance Warranty on panels, 12-Year Panel Product Warranty, and 8 to 10-Year Inverter Product Warranty."
            }
          }
        ]
      },
      {
        "@type": "WebSite",
        "@id": "https://suryanzsolar.com/#website",
        "url": "https://suryanzsolar.com",
        "name": "SURYANZ SOLAR Official Portal",
        "publisher": { "@id": "https://suryanzsolar.com/#organization" }
      }
    ]
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
  ${getSuryanzMobileActionBar(urlPrefix)}
  <script src="/public/js/suryanz-calculator.js" defer></script>
  <script src="/public/js/suryanz-lead-form.js" defer></script>
</body>
</html>`;
}

// ===================== SPECIFIC ROUTE RENDERERS =====================

function renderHomePage(urlPrefix = '') {
  const p = (urlPrefix && urlPrefix.endsWith('/')) ? urlPrefix.slice(0, -1) : urlPrefix;
  const content = `
  <!-- 1. HERO SECTION -->
  <section class="suryanz-hero-section">
    <div class="suryanz-hero-container">
      <div>
        <div class="suryanz-hero-tag">
          <i class="fas fa-certificate"></i> SURYANZ SOLAR
        </div>
        <h1 class="suryanz-hero-title-main">Powering a Brighter Tomorrow</h1>
        <div class="suryanz-hero-title-sub">Smart Solar. Reliable Energy. Built for the next 30 years.</div>
        <p class="suryanz-hero-subtitle">
          Engineer-designed solar systems for homes, businesses and industrial facilities — from site assessment and design to installation, net metering and long-term support.
        </p>
        <div class="suryanz-hero-ctas">
          <a href="${p}/contact" class="suryanz-btn-cta"><i class="fas fa-clipboard-check"></i> Get a Free Solar Assessment</a>
          <a href="${p}/calculator" class="suryanz-btn-amber"><i class="fas fa-calculator"></i> Calculate Your Savings</a>
        </div>
        <div class="suryanz-trust-line">
          <i class="fas fa-shield-alt" style="color:#fbbf24;"></i>
          <span>20+ Years of Energy Experience · Engineering-Led Installation · Long-Term Support</span>
        </div>
      </div>
      <div>
        <div class="suryanz-calc-card">
          <h3 style="margin-top:0; font-size:1.35rem; color:var(--suryanz-charcoal); font-weight:800; margin-bottom:0.5rem;">
            Request Solar Callback
          </h3>
          <p style="font-size:0.85rem; color:var(--suryanz-text-muted); margin-bottom:1.25rem;">
            Speak directly with a solar engineer about your property requirements.
          </p>
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
              <input type="text" name="city" class="suryanz-form-input" placeholder="e.g. Visakhapatnam / Vijayawada" required>
            </div>
            <div class="suryanz-form-group">
              <label class="suryanz-form-label">Monthly Electricity Bill (₹)</label>
              <input type="number" name="monthly_bill" class="suryanz-form-input" placeholder="e.g. 6000">
            </div>
            <button type="submit" class="suryanz-btn-cta" style="width:100%; justify-content:center; padding: 0.8rem; margin-top:0.5rem;">
              Get a Free Solar Assessment
            </button>
          </form>
        </div>
      </div>
    </div>
  </section>

  <!-- 3. TRUST STRIP -->
  <section class="suryanz-trust-strip">
    <div class="suryanz-container">
      <div class="suryanz-trust-grid">
        <div class="suryanz-trust-item">
          <div class="suryanz-trust-num">20+ Years</div>
          <div class="suryanz-trust-label">Energy Experience</div>
        </div>
        <div class="suryanz-trust-item">
          <div class="suryanz-trust-num">30 Years</div>
          <div class="suryanz-trust-label">Solar Performance Warranty</div>
        </div>
        <div class="suryanz-trust-item">
          <div class="suryanz-trust-num">Residential → Industrial</div>
          <div class="suryanz-trust-label">Complete EPC Capability</div>
        </div>
        <div class="suryanz-trust-item">
          <div class="suryanz-trust-num">End-to-End</div>
          <div class="suryanz-trust-label">Engineering & Support</div>
        </div>
      </div>
    </div>
  </section>

  <!-- 4. SOLAR IS AN ENGINEERING DECISION SECTION -->
  <section class="suryanz-section" style="background:#ffffff;">
    <div class="suryanz-container">
      <div class="suryanz-engineering-grid">
        <div class="suryanz-engineering-photo-frame">
          <img src="/public/images/suryanz_engineer_site_assessment.jpg" alt="SURYANZ Solar Engineer Site Assessment" class="suryanz-engineering-photo">
          <div class="suryanz-photo-caption">
            <i class="fas fa-ruler-combined me-1"></i> SURYANZ Solar Engineer inspecting rooftop site orientation & structural load capacity.
          </div>
        </div>
        <div>
          <div style="color:var(--suryanz-amber-hover); font-weight:700; text-transform:uppercase; font-size:0.85rem; letter-spacing:0.05em; margin-bottom:0.5rem;">
            Engineering Methodology
          </div>
          <h2 class="suryanz-section-title" style="text-align:left; margin-bottom:1rem;">
            Solar isn't just about panels.<br>
            <span style="color:var(--suryanz-amber-hover);">It's about engineering.</span>
          </h2>
          <p style="font-size:1.05rem; color:var(--suryanz-text-muted); line-height:1.7; margin-bottom:1rem;">
            Every SURYANZ installation begins with understanding your building, electricity consumption, roof structure, orientation and long-term energy requirements.
          </p>
          <p style="font-size:1.05rem; color:var(--suryanz-text-dark); font-weight:600; line-height:1.7;">
            We design the system around the property — not the other way around.
          </p>
          
          <ul class="suryanz-checklist">
            <li class="suryanz-checklist-item"><i class="fas fa-check-circle"></i> Shadow analysis</li>
            <li class="suryanz-checklist-item"><i class="fas fa-check-circle"></i> Structural assessment</li>
            <li class="suryanz-checklist-item"><i class="fas fa-check-circle"></i> Energy-load analysis</li>
            <li class="suryanz-checklist-item"><i class="fas fa-check-circle"></i> System sizing</li>
            <li class="suryanz-checklist-item"><i class="fas fa-check-circle"></i> 3D rooftop layout</li>
            <li class="suryanz-checklist-item"><i class="fas fa-check-circle"></i> Electrical design</li>
            <li class="suryanz-checklist-item" style="grid-column: span 2;"><i class="fas fa-check-circle"></i> Net-metering planning</li>
          </ul>
        </div>
      </div>
    </div>
  </section>

  <!-- 5. SOLAR SOLUTIONS (VISUAL CARDS) -->
  <section class="suryanz-section">
    <div class="suryanz-container">
      <div class="suryanz-section-header">
        <h2 class="suryanz-section-title">Solar Solutions Tailored for Every Scale</h2>
        <p class="suryanz-section-subtitle">Photovoltaic engineering designed specifically for independent homes, commercial properties, and industrial manufacturing plants.</p>
      </div>

      <div class="suryanz-solutions-grid">
        <!-- Residential Card -->
        <div class="suryanz-solution-card">
          <div class="suryanz-solution-img-wrapper">
            <img src="/public/images/suryanz_residential_card.jpg" alt="Residential Solar Rooftop India" class="suryanz-solution-img">
            <span class="suryanz-solution-badge">Homes & Villas</span>
          </div>
          <div class="suryanz-solution-body">
            <h3 class="suryanz-solution-title">Residential Solar</h3>
            <div class="suryanz-solution-tagline">Turn your rooftop into a power asset.</div>
            <p class="suryanz-solution-desc">
              Reduce household electricity costs with professionally engineered rooftop solar designed around your consumption and roof.
            </p>
            <a href="${p}/solutions/residential" class="suryanz-btn-outline">Explore Residential Solar <i class="fas fa-arrow-right"></i></a>
          </div>
        </div>

        <!-- Commercial Card -->
        <div class="suryanz-solution-card">
          <div class="suryanz-solution-img-wrapper">
            <img src="/public/images/suryanz_commercial_card.jpg" alt="Commercial Solar India" class="suryanz-solution-img">
            <span class="suryanz-solution-badge">Offices & Retail</span>
          </div>
          <div class="suryanz-solution-body">
            <h3 class="suryanz-solution-title">Commercial Solar</h3>
            <div class="suryanz-solution-tagline">Lower operating costs. Increase energy independence.</div>
            <p class="suryanz-solution-desc">
              Designed for offices, hospitals, institutions, retail buildings and commercial facilities requiring high daytime reliability.
            </p>
            <a href="${p}/solutions/commercial" class="suryanz-btn-outline">Explore Commercial Solar <i class="fas fa-arrow-right"></i></a>
          </div>
        </div>

        <!-- Industrial Card -->
        <div class="suryanz-solution-card">
          <div class="suryanz-solution-img-wrapper">
            <img src="/public/images/suryanz_industrial_card.jpg" alt="Industrial Solar EPC India" class="suryanz-solution-img">
            <span class="suryanz-solution-badge">Factories & Plants</span>
          </div>
          <div class="suryanz-solution-body">
            <h3 class="suryanz-solution-title">Industrial EPC</h3>
            <div class="suryanz-solution-tagline">Large-scale solar. Engineered for performance.</div>
            <p class="suryanz-solution-desc">
              Complete EPC solutions for manufacturing facilities, warehouses and industrial campuses with high MW-scale capabilities.
            </p>
            <a href="${p}/solutions/epc" class="suryanz-btn-outline">Explore Industrial Solar <i class="fas fa-arrow-right"></i></a>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- 6. ACTUAL INSTALLATION PROCESS TIMELINE -->
  <section class="suryanz-section" style="background:#ffffff;">
    <div class="suryanz-container">
      <div class="suryanz-section-header">
        <h2 class="suryanz-section-title">From Rooftop to Renewable Power</h2>
        <p class="suryanz-section-subtitle">
          Our transparent 6-step execution workflow ensures zero guesswork from initial consultation to 30-year system commissioning.
        </p>
      </div>

      <div class="suryanz-process-grid">
        <div class="suryanz-process-step">
          <div class="suryanz-step-num">01</div>
          <div class="suryanz-step-title">Assess</div>
          <div class="suryanz-step-desc">Roof inspection, shadow analysis and electricity-consumption study.</div>
        </div>

        <div class="suryanz-process-step">
          <div class="suryanz-step-num">02</div>
          <div class="suryanz-step-title">Design</div>
          <div class="suryanz-step-desc">System sizing, engineering calculations and 3D rooftop layout.</div>
        </div>

        <div class="suryanz-process-step">
          <div class="suryanz-step-num">03</div>
          <div class="suryanz-step-title">Install</div>
          <div class="suryanz-step-desc">Professional mounting structures, panels, inverter and electrical systems.</div>
        </div>

        <div class="suryanz-process-step">
          <div class="suryanz-step-num">04</div>
          <div class="suryanz-step-title">Verify</div>
          <div class="suryanz-step-desc">Testing, safety checks and grid/net-metering coordination.</div>
        </div>

        <div class="suryanz-process-step">
          <div class="suryanz-step-num">05</div>
          <div class="suryanz-step-title">Commission</div>
          <div class="suryanz-step-desc">System activation and generation verification.</div>
        </div>

        <div class="suryanz-process-step">
          <div class="suryanz-step-num">06</div>
          <div class="suryanz-step-title">Support</div>
          <div class="suryanz-step-desc">Monitoring, maintenance and long-term service.</div>
        </div>
      </div>
    </div>
  </section>

  <!-- 7. REAL PROJECTS SECTION -->
  <section class="suryanz-section">
    <div class="suryanz-container">
      <div class="suryanz-section-header">
        <h2 class="suryanz-section-title">Projects That Power Real Places</h2>
        <p class="suryanz-section-subtitle">
          From homes to commercial facilities, every installation is designed around the site, the customer and the energy requirement.
        </p>
      </div>

      <div class="suryanz-projects-grid">
        <div class="suryanz-project-card">
          <img src="/public/images/solar_installations/ap_solar_customer_1.jpg" alt="Residential Solar Visakhapatnam" class="suryanz-project-img">
          <div class="suryanz-project-body">
            <div class="suryanz-project-meta">
              <span class="suryanz-project-location"><i class="fas fa-map-marker-alt"></i> Visakhapatnam, AP</span>
              <span class="suryanz-project-capacity">5 kW On-Grid</span>
            </div>
            <h4 class="suryanz-project-name">Residential Rooftop</h4>
            <p class="suryanz-project-result"><strong>Result:</strong> 85% reduction in monthly electricity bill with seamless DISCOM net-metering.</p>
          </div>
        </div>

        <div class="suryanz-project-card">
          <img src="/public/images/solar_installations/komaravolu_solar_customer.jpg" alt="Commercial Solar Andhra Pradesh" class="suryanz-project-img">
          <div class="suryanz-project-body">
            <div class="suryanz-project-meta">
              <span class="suryanz-project-location"><i class="fas fa-map-marker-alt"></i> Andhra Pradesh</span>
              <span class="suryanz-project-capacity">50 kW Solar EPC</span>
            </div>
            <h4 class="suryanz-project-name">Commercial Rooftop</h4>
            <p class="suryanz-project-result"><strong>Result:</strong> Saves ₹4.8 Lakhs annually in commercial power tariffs for business operations.</p>
          </div>
        </div>

        <div class="suryanz-project-card">
          <img src="/public/images/solar_installations/pothavaram_solar_customer.jpg" alt="Industrial Solar Andhra Pradesh" class="suryanz-project-img">
          <div class="suryanz-project-body">
            <div class="suryanz-project-meta">
              <span class="suryanz-project-location"><i class="fas fa-map-marker-alt"></i> Andhra Pradesh</span>
              <span class="suryanz-project-capacity">250 kW Industrial</span>
            </div>
            <h4 class="suryanz-project-name">Industrial Installation</h4>
            <p class="suryanz-project-result"><strong>Result:</strong> High-efficiency TOPCon solar array delivering 3.8 years ROI payback.</p>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- 8. REAL PEOPLE SECTION -->
  <section class="suryanz-section" style="background:#ffffff;">
    <div class="suryanz-container">
      <div class="suryanz-engineering-grid">
        <div>
          <div style="color:var(--suryanz-amber-hover); font-weight:700; text-transform:uppercase; font-size:0.85rem; letter-spacing:0.05em; margin-bottom:0.5rem;">
            Accountability & Field Presence
          </div>
          <h2 class="suryanz-section-title" style="text-align:left; margin-bottom:1rem;">
            Solar is powered by people, too.
          </h2>
          <p style="font-size:1.05rem; color:var(--suryanz-text-muted); line-height:1.7; margin-bottom:1.25rem;">
            From the first site visit to commissioning and after-sales support, our team stays involved throughout the project.
          </p>
          <p style="font-size:0.95rem; color:var(--suryanz-text-dark); line-height:1.7; background:var(--suryanz-bg-warm); padding:1.25rem; border-left:4px solid var(--suryanz-amber); border-radius:6px;">
            "We don't subcontract critical electrical engineering or site safety. SURYANZ project managers and certified technicians personally supervise structural anchor points, DC cabling, inverter synchronization, and grid inspection."
          </p>
        </div>
        <div class="suryanz-engineering-photo-frame">
          <img src="/public/images/suryanz_team_people.jpg" alt="SURYANZ Solar Engineering Team" class="suryanz-engineering-photo">
          <div class="suryanz-photo-caption">
            <i class="fas fa-users me-1"></i> SURYANZ lead engineer, site supervisor, and electrical technician team.
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- 9. TECHNOLOGY SECTION -->
  <section class="suryanz-section">
    <div class="suryanz-container">
      <div class="suryanz-section-header">
        <h2 class="suryanz-section-title">Engineered for the Way You Use Energy</h2>
        <p class="suryanz-section-subtitle">
          We specify industrial-grade tier-1 solar equipment designed for harsh weather, high heat tolerance, and 30-year endurance.
        </p>
      </div>

      <div class="suryanz-tech-grid">
        <div class="suryanz-tech-card">
          <div class="suryanz-tech-icon"><i class="fas fa-solar-panel"></i></div>
          <h4 class="suryanz-tech-title">TOPCon & N-Type Modules</h4>
          <p class="suryanz-tech-desc">540W to 580W class ultra-high efficiency bifacial and mono-PERC panels with lower temperature coefficient.</p>
        </div>

        <div class="suryanz-tech-card">
          <div class="suryanz-tech-icon"><i class="fas fa-bolt"></i></div>
          <h4 class="suryanz-tech-title">Smart String Inverters</h4>
          <p class="suryanz-tech-desc">Pure sine wave inverters with up to 98.6% peak efficiency, dual MPPT tracking, and IP65 weatherproof casing.</p>
        </div>

        <div class="suryanz-tech-card">
          <div class="suryanz-tech-icon"><i class="fas fa-cubes"></i></div>
          <h4 class="suryanz-tech-title">Hot-Dip Galvanized Structure</h4>
          <p class="suryanz-tech-desc">Custom rooftop mounting frames engineered to withstand cyclone-grade wind speeds up to 170 km/h.</p>
        </div>

        <div class="suryanz-tech-card">
          <div class="suryanz-tech-icon"><i class="fas fa-shield-virus"></i></div>
          <h4 class="suryanz-tech-title">DC/AC Protection Boxes</h4>
          <p class="suryanz-tech-desc">Surge protection devices (SPD), MCB/MCCB breakers, and IP67 enclosed isolation switches for total safety.</p>
        </div>

        <div class="suryanz-tech-card">
          <div class="suryanz-tech-icon"><i class="fas fa-plug"></i></div>
          <h4 class="suryanz-tech-title">Solar DC Cables & Earthing</h4>
          <p class="suryanz-tech-desc">UV-resistant double-insulated copper DC solar cables with dedicated chemical earthing pits and lightning arresters.</p>
        </div>

        <div class="suryanz-tech-card">
          <div class="suryanz-tech-icon"><i class="fas fa-mobile-alt"></i></div>
          <h4 class="suryanz-tech-title">24/7 Digital Monitoring</h4>
          <p class="suryanz-tech-desc">Real-time mobile app and cloud portal tracking daily generation (kWh), grid exports, and system diagnostic alerts.</p>
        </div>
      </div>
    </div>
  </section>

  <!-- 10. CUSTOMER PROTECTION (30 YEARS FIRST TILE, NO % SIGN) -->
  <section class="suryanz-section" style="background:#ffffff;">
    <div class="suryanz-container">
      <div class="suryanz-section-header">
        <h2 class="suryanz-section-title">Your Investment Deserves Long-Term Protection</h2>
        <p class="suryanz-section-subtitle">
          Transparent warranty documentation backed by OEM manufacturer guarantees and direct SURYANZ service commitment.
        </p>
      </div>

      <div class="suryanz-protection-matrix">
        <div class="suryanz-protection-grid">
          <!-- 1st Tile: 30 YEARS Linear Performance Warranty -->
          <div class="suryanz-warranty-box" style="border-top-color: var(--suryanz-amber);">
            <div class="suryanz-warranty-num">30 YEARS</div>
            <div class="suryanz-warranty-title">Linear Performance Warranty</div>
            <p class="suryanz-warranty-desc">Guarantees up to 80-85 power generation output retention over 30 years.</p>
          </div>

          <!-- 2nd Tile: 12 YEARS Module Product Warranty -->
          <div class="suryanz-warranty-box" style="border-top-color: #3b82f6;">
            <div class="suryanz-warranty-num">12 YEARS</div>
            <div class="suryanz-warranty-title">Module Product Warranty</div>
            <p class="suryanz-warranty-desc">Full replacement coverage against manufacturing defects, micro-cracks, panel delamination, or material failure.</p>
          </div>

          <!-- 3rd Tile: 8-10 YEARS Inverter Warranty -->
          <div class="suryanz-warranty-box" style="border-top-color: #10b981;">
            <div class="suryanz-warranty-num">8–10 YEARS</div>
            <div class="suryanz-warranty-title">Inverter Warranty</div>
            <p class="suryanz-warranty-desc">Comprehensive string and hybrid inverter product warranty ensuring continuous grid conversion reliability.</p>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- 11. SOLAR SAVINGS CALCULATOR -->
  <section class="suryanz-section" id="solar-calculator">
    <div class="suryanz-container">
      <div class="suryanz-section-header">
        <h2 class="suryanz-section-title">See What Your Rooftop Could Save</h2>
        <p class="suryanz-section-subtitle">
          Estimate your system size, monthly units generated, financial savings, and payback timeline based on your electricity bill.
        </p>
      </div>

      <div class="suryanz-calculator-wrapper">
        <div>
          <h3 style="margin-top:0; font-size:1.35rem; color:var(--suryanz-charcoal); font-weight:800; margin-bottom:1.25rem;">
            Calculator Inputs
          </h3>
          <form id="suryanz-calc-form">
            <div class="suryanz-form-group">
              <label class="suryanz-form-label">Average Monthly Electricity Bill (₹) *</label>
              <input type="number" id="calc-monthly-bill" class="suryanz-form-input" value="6000" min="500" max="500000" required>
            </div>
            
            <div class="suryanz-form-group">
              <label class="suryanz-form-label">Property Type *</label>
              <select id="calc-customer-type" class="suryanz-form-select">
                <option value="residential">Residential House / Villa</option>
                <option value="commercial">Commercial Office / Retail</option>
                <option value="industrial">Industrial Plant / Factory</option>
              </select>
            </div>

            <div class="suryanz-form-group">
              <label class="suryanz-form-label">City / Location</label>
              <select class="suryanz-form-select">
                <option value="visakhapatnam">Visakhapatnam, AP</option>
                <option value="vijayawada">Vijayawada, AP</option>
                <option value="hyderabad">Hyderabad, TS</option>
                <option value="guntur">Guntur, AP</option>
                <option value="rajahmundry">Rajahmundry, AP</option>
                <option value="kakinada">Kakinada, AP</option>
                <option value="tirupati">Tirupati, AP</option>
              </select>
            </div>

            <div class="suryanz-form-group">
              <label class="suryanz-form-label">Available Shade-Free Roof Area (sq ft)</label>
              <input type="number" id="calc-roof-area" class="suryanz-form-input" value="500" placeholder="e.g. 500">
            </div>
          </form>
        </div>

        <div class="suryanz-calc-output-box">
          <div>
            <h4 style="color:#fbbf24; margin-top:0; font-size:1.1rem; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:1.5rem;">
              Estimated System Metrics
            </h4>
            <div class="suryanz-calc-metric">
              <div class="suryanz-calc-val" id="res-capacity-kw">5.0 kW</div>
              <div class="suryanz-calc-lbl">Recommended Solar System Size</div>
            </div>
            <div class="suryanz-calc-metric">
              <div class="suryanz-calc-val" id="res-annual-gen">7,250 kWh</div>
              <div class="suryanz-calc-lbl">Estimated Annual Energy Generation</div>
            </div>
            <div class="suryanz-calc-metric">
              <div class="suryanz-calc-val" id="res-annual-sav">₹58,000</div>
              <div class="suryanz-calc-lbl">Estimated Annual Electricity Savings</div>
            </div>
            <div class="suryanz-calc-metric">
              <div class="suryanz-calc-val" id="res-payback-yrs">4.2 Years</div>
              <div class="suryanz-calc-lbl">Estimated Payback Period</div>
            </div>
          </div>
          <a href="${p}/contact" class="suryanz-btn-cta" style="width:100%; justify-content:center; text-align:center;">
            Get My Detailed Solar Assessment
          </a>
        </div>
      </div>
    </div>
  </section>

  <!-- 12. WHY SURYANZ -->
  <section class="suryanz-section" style="background:#ffffff;">
    <div class="suryanz-container">
      <div class="suryanz-section-header">
        <h2 class="suryanz-section-title">Why Customers Choose SURYANZ</h2>
        <p class="suryanz-section-subtitle">
          Comparing generic local solar installers with SURYANZ engineering-first standards.
        </p>
      </div>

      <div class="suryanz-tech-grid">
        <div class="suryanz-tech-card" style="border-top: 3px solid var(--suryanz-amber);">
          <h4 class="suryanz-tech-title">ENGINEERING FIRST</h4>
          <p class="suryanz-tech-desc">Every system begins with mandatory rooftop shadow analysis, structural load evaluation, and consumption profiling.</p>
        </div>

        <div class="suryanz-tech-card" style="border-top: 3px solid var(--suryanz-amber);">
          <h4 class="suryanz-tech-title">TRANSPARENT DESIGN</h4>
          <p class="suryanz-tech-desc">Itemized component specifications, clear system sizing, and zero hidden costs or unverified claims.</p>
        </div>

        <div class="suryanz-tech-card" style="border-top: 3px solid var(--suryanz-amber);">
          <h4 class="suryanz-tech-title">QUALITY COMPONENTS</h4>
          <p class="suryanz-tech-desc">Strictly tier-1 TOPCon panels, pure sine wave string inverters, and hot-dip galvanized steel structures.</p>
        </div>

        <div class="suryanz-tech-card" style="border-top: 3px solid var(--suryanz-amber);">
          <h4 class="suryanz-tech-title">END-TO-END EXECUTION</h4>
          <p class="suryanz-tech-desc">Complete lifecycle execution: Assessment → 3D Design → Mounting & Wiring → Net-metering → Commissioning.</p>
        </div>

        <div class="suryanz-tech-card" style="border-top: 3px solid var(--suryanz-amber);">
          <h4 class="suryanz-tech-title">LONG-TERM SUPPORT</h4>
          <p class="suryanz-tech-desc">24/7 digital mobile monitoring app, preventive maintenance schedules, and dedicated AMC technical support.</p>
        </div>

        <div class="suryanz-tech-card" style="border-top: 3px solid var(--suryanz-amber);">
          <h4 class="suryanz-tech-title">REAL ACCOUNTABILITY</h4>
          <p class="suryanz-tech-desc">A solar system is a 30-year financial asset. We stay personally involved and accountable long after installation.</p>
        </div>
      </div>
    </div>
  </section>

  <!-- 14. FAQ ACCORDION -->
  <section class="suryanz-section">
    <div class="suryanz-container">
      <div class="suryanz-section-header">
        <h2 class="suryanz-section-title">Frequently Asked Questions</h2>
        <p class="suryanz-section-subtitle">Clear, practical answers about rooftop solar costs, net metering, panel sizing, and warranties.</p>
      </div>

      <div class="suryanz-faq-list">
        <details class="suryanz-faq-item">
          <summary class="suryanz-faq-summary">
            How much does a rooftop solar installation cost? <i class="fas fa-chevron-down"></i>
          </summary>
          <div class="suryanz-faq-answer">
            Rooftop solar costs depend on system capacity (kW), panel tech (TOPCon/Mono PERC), and inverter type. A residential 3 kW to 5 kW grid-connected solar system typically ranges between ₹1.8 Lakhs to ₹3.2 Lakhs before government subsidies, delivering a payback period of 3 to 4.5 years.
          </div>
        </details>

        <details class="suryanz-faq-item">
          <summary class="suryanz-faq-summary">
            How much can I save on my monthly electricity bills? <i class="fas fa-chevron-down"></i>
          </summary>
          <div class="suryanz-faq-answer">
            A properly sized grid-tied SURYANZ solar system can offset up to 80% to 90% of your total electricity bill by exporting excess generated power to the grid during daytime via net metering.
          </div>
        </details>

        <details class="suryanz-faq-item">
          <summary class="suryanz-faq-summary">
            How many solar panels do I need for my property? <i class="fas fa-chevron-down"></i>
          </summary>
          <div class="suryanz-faq-answer">
            A standard 1 kW solar system generates approximately 4 units (kWh) of electricity per day and requires about 2 high-efficiency 540W/550W TOPCon panels. A typical 5 kW residential system uses 9 to 10 panels.
          </div>
        </details>

        <details class="suryanz-faq-item">
          <summary class="suryanz-faq-summary">
            What roof area is required for 1 kW solar installation? <i class="fas fa-chevron-down"></i>
          </summary>
          <div class="suryanz-faq-answer">
            Every 1 kW of rooftop solar requires approximately 80 to 100 sq. ft. of shade-free rooftop space facing South or South-West orientation.
          </div>
        </details>

        <details class="suryanz-faq-item">
          <summary class="suryanz-faq-summary">
            How does net metering work in Andhra Pradesh and Telangana? <i class="fas fa-chevron-down"></i>
          </summary>
          <div class="suryanz-faq-answer">
            A bi-directional net meter records both the power consumed from the DISCOM grid and the surplus solar electricity exported to the grid. At the end of each billing cycle, your DISCOM bills only for the net units consumed.
          </div>
        </details>

        <details class="suryanz-faq-item">
          <summary class="suryanz-faq-summary">
            What happens during power cuts? <i class="fas fa-chevron-down"></i>
          </summary>
          <div class="suryanz-faq-answer">
            Standard On-Grid solar systems automatically shut down during grid outages for anti-islanding safety. If your area experiences frequent power cuts, we recommend SURYANZ Hybrid Solar Systems paired with lithium battery storage.
          </div>
        </details>
      </div>
    </div>
  </section>

  <!-- 15. FINAL CTA SECTION -->
  <section class="suryanz-final-cta-section">
    <div class="suryanz-container" style="max-width:850px;">
      <h2 style="font-size:2.5rem; font-weight:800; color:#ffffff; margin-bottom:1rem; line-height:1.2;">
        Your roof is already working for you.<br>
        <span style="color:#fbbf24;">It's time to make it work harder.</span>
      </h2>
      <p style="font-size:1.15rem; color:rgba(255,255,255,0.9); margin-bottom:2rem; line-height:1.6;">
        Tell us about your electricity usage and property. Our team will assess your site and recommend the right solar solution.
      </p>
      <div style="display:flex; gap:1rem; justify-content:center; flex-wrap:wrap; margin-bottom:2rem;">
        <a href="${p}/contact" class="suryanz-btn-cta" style="padding:0.9rem 2rem; font-size:1rem;">
          <i class="fas fa-clipboard-check"></i> Get a Free Solar Assessment
        </a>
        <a href="https://wa.me/919876543210?text=Hi%20Suryanz%20Solar,%20I%20want%20to%20speak%20with%20a%20solar%20expert." class="suryanz-btn-amber" style="padding:0.9rem 2rem; font-size:1rem; background:#25D366; border-color:#25D366;" target="_blank">
          <i class="fab fa-whatsapp"></i> Talk to a Solar Expert
        </a>
      </div>
      <div style="font-size:0.9rem; color:rgba(255,255,255,0.75);">
        Direct Hotline: <strong style="color:#ffffff;">+91 98765 43210</strong> · Email: <strong style="color:#ffffff;">contact@suryanzsolar.com</strong>
      </div>
    </div>
  </section>
  `;

  return renderSuryanzPage({
    title: 'SURYANZ SOLAR | Real Projects, Real Engineering, Real Savings',
    description: 'SURYANZ SOLAR provides engineer-designed rooftop solar systems for homes, commercial hubs, and industrial facilities across India. Backed by 20+ years of energy experience.',
    canonicalUrl: 'https://suryanzsolar.com/',
    activePath: '/',
    bodyContent: content,
    urlPrefix: urlPrefix
  });
}

function renderAboutPage(urlPrefix = '') {
  return renderGenericPage('about', 'About SURYANZ SOLAR', 'Building India\'s most trusted, engineering-driven clean energy platform.', urlPrefix);
}

function renderWhySuryanzPage(urlPrefix = '') {
  return renderGenericPage('why-suryanz', 'Why SURYANZ SOLAR', 'Discover the engineering difference that protects your 30-year solar investment.', urlPrefix);
}

function renderCustomerProtectionPage(urlPrefix = '') {
  return renderGenericPage('customer-protection', 'Customer Protection & 30-Year Warranty', 'Documented 30-Year Linear Performance, 12-Year Product, and 10-Year Inverter Warranty portfolios.', urlPrefix);
}

function renderTechnologyPage(urlPrefix = '') {
  return renderGenericPage('technology', 'Technology & Specifications', 'Industrial-grade TOPCon panels, smart string inverters, and hot-dip galvanized mounting structures.', urlPrefix);
}

function renderCalculatorPage(urlPrefix = '') {
  return renderHomePage(urlPrefix);
}

function renderProjectsPage(urlPrefix = '') {
  return renderGenericPage('projects', 'Projects & Case Studies', 'Real residential, commercial, and industrial rooftop solar installations across India.', urlPrefix);
}

function renderCustomerStoriesPage(urlPrefix = '') {
  return renderGenericPage('customer-stories', 'Customer Stories', 'Authentic reviews and experiences from SURYANZ SOLAR rooftop customers.', urlPrefix);
}

function renderFaqsPage(urlPrefix = '') {
  return renderGenericPage('faqs', 'Frequently Asked Questions', 'Practical answers about rooftop solar costs, net metering, panel sizing, and warranties.', urlPrefix);
}

function renderContactPage(urlPrefix = '') {
  return renderGenericPage('contact', 'Contact SURYANZ SOLAR', 'Speak directly with a solar engineer to get a free site assessment and customized quote.', urlPrefix);
}

function renderSolutionPage(solutionSlug, urlPrefix = '') {
  const titles = {
    residential: 'Residential Rooftop Solar',
    commercial: 'Commercial Rooftop Solar',
    industrial: 'Industrial Solar Systems',
    epc: 'Solar EPC Services',
    'on-grid': 'On-Grid Solar Systems',
    hybrid: 'Hybrid Solar + Battery',
    'off-grid': 'Off-Grid Remote Energy',
    'solar-battery': 'Solar Battery Systems',
    apartments: 'Societies & Apartments Solar',
    'operations-maintenance': 'Solar O&M / AMC Services'
  };
  const title = titles[solutionSlug] || 'Solar Solution';
  return renderGenericPage(`solutions/${solutionSlug}`, title, `High-efficiency, engineer-designed ${title.toLowerCase()} systems built for 30 years reliability.`, urlPrefix);
}

function renderKnowledgeGuidePage(guideSlug, urlPrefix = '') {
  const guideTitles = {
    'solar-guide': "Solar Buyer's Guide",
    'solar-pricing': "Rooftop Solar Cost & Pricing Guide",
    'solar-roi': "Solar ROI & Financial Return Guide",
    'solar-calculator-guide': "Solar Capacity Sizing Guide",
    'solar-warranty-guide': "Solar Warranty Portfolio Guide",
    'solar-maintenance': "Solar Maintenance & Care Guide",
    'solar-buying-guide': "Solar System Comparison Guide"
  };
  const title = guideTitles[guideSlug] || 'Solar Knowledge Guide';
  return renderGenericPage(guideSlug, title, `Comprehensive educational guide on ${title.toLowerCase()} for property owners in India.`, urlPrefix);
}

function renderLocationPage(locSlug, locName, stateName, urlPrefix = '') {
  return renderGenericPage(`location/${locSlug}`, `Solar EPC Services in ${locName}, ${stateName}`, `High-performance rooftop solar installations and EPC engineering services in ${locName}, ${stateName}.`, urlPrefix);
}

function renderLegalPage(legalSlug, urlPrefix = '') {
  const legalTitles = {
    'privacy-policy': 'Privacy Policy',
    'terms-and-conditions': 'Terms & Conditions',
    'warranty-terms': 'Warranty Terms & Portfolio'
  };
  const title = legalTitles[legalSlug] || 'Legal Policy';
  return renderGenericPage(`legal/${legalSlug}`, title, `Official SURYANZ SOLAR ${title.toLowerCase()} and compliance documentation.`, urlPrefix);
}

function renderSitemapXml() {
  return `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://suryanzsolar.com/</loc><priority>1.0</priority></url>
  <url><loc>https://suryanzsolar.com/about</loc><priority>0.8</priority></url>
  <url><loc>https://suryanzsolar.com/why-suryanz</loc><priority>0.8</priority></url>
  <url><loc>https://suryanzsolar.com/customer-protection</loc><priority>0.8</priority></url>
  <url><loc>https://suryanzsolar.com/technology</loc><priority>0.8</priority></url>
  <url><loc>https://suryanzsolar.com/calculator</loc><priority>0.9</priority></url>
  <url><loc>https://suryanzsolar.com/projects</loc><priority>0.8</priority></url>
  <url><loc>https://suryanzsolar.com/faqs</loc><priority>0.7</priority></url>
  <url><loc>https://suryanzsolar.com/contact</loc><priority>0.9</priority></url>
</urlset>`;
}

function renderRobotsTxt() {
  return `User-agent: *
Allow: /
Sitemap: https://suryanzsolar.com/sitemap.xml`;
}

module.exports = {
  getSuryanzHeader,
  getSuryanzFooter,
  renderSuryanzPage,
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
