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
    (function() {
      window.toggleMobileDrawer = function() {
        var d = document.getElementById('mobileDrawer');
        var btn = document.querySelector('.suryanz-mobile-toggle');
        if (d) {
          var isOpen = d.classList.toggle('open');
          if (btn) {
            btn.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
          }
          d.setAttribute('aria-hidden', isOpen ? 'false' : 'true');
        }
      };

      document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
          var d = document.getElementById('mobileDrawer');
          if (d && d.classList.contains('open')) {
            window.toggleMobileDrawer();
          }
        }
      });
    })();
  </script>`;
}

function getSuryanzMobileActionBar(urlPrefix = '') {
  const p = (urlPrefix && urlPrefix.endsWith('/')) ? urlPrefix.slice(0, -1) : urlPrefix;
  return `
  <div class="suryanz-mobile-action-bar">
    <div class="suryanz-mobile-action-bar-inner">
      <a href="tel:+918585852738" class="suryanz-mobile-action-btn" style="background:#f1f5f9; color:#0f172a;">
        <i class="fas fa-phone-alt"></i> Call
      </a>
      <a href="https://wa.me/918585852738?text=Hi%20Suryanz%20Solar,%20I%20want%20to%20know%20more%20about%20rooftop%20solar." class="suryanz-mobile-action-btn" style="background:#25D366; color:#ffffff;" target="_blank">
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
  canonicalUrl = null,
  activePath = '/',
  bodyContent,
  jsonLd = null,
  urlPrefix = '',
  requestHost = 'suryanz.com',
  requestProto = 'https'
}) {
  const hostClean = (requestHost || 'suryanz.com').split(':')[0].trim() || 'suryanz.com';
  const protoClean = (requestProto || 'https').trim();
  const domainUrl = `${protoClean}://${requestHost}`;
  const normalizedPath = activePath.startsWith('/') ? activePath : '/' + activePath;
  const resolvedCanonicalUrl = canonicalUrl || `${domainUrl}${normalizedPath}`;
  const resolvedOgImage = `${domainUrl}/public/images/suryanz-og-preview.png`;

  const defaultSchema = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "Organization",
        "@id": `${domainUrl}/#organization`,
        "name": "SURYANZ SOLAR",
        "legalName": "SURYANZ SOLAR",
        "alternateName": [
          "Suryanz",
          "Suryanz Solar",
          "Suryanz Energy",
          "Suryanz Solar EPC",
          "Suryanz Rooftop Solar",
          "sunryanz"
        ],
        "url": domainUrl,
        "logo": `${domainUrl}/public/images/suryanz-logo-transparent.png`,
        "description": "Premium engineer-designed rooftop solar systems for homes, commercial hubs, and industrial facilities in India. Backed by 20+ years of team experience.",
        "disambiguatingDescription": "Suryanz Solar (also known as Suryanz) is an Indian clean-energy engineering and solar EPC company providing residential, commercial, and industrial rooftop solar power solutions across Andhra Pradesh, Telangana, and Karnataka. It is distinct from Suryan Energy Systems, Suryansh Solar, or Surya Solar.",
        "slogan": "Powering a Brighter Tomorrow",
        "telephone": "+91-85858-52738",
        "email": "contact@suryanzsolar.com",
        "address": {
          "@type": "PostalAddress",
          "streetAddress": "Rama Talkies Road, CBM Compound",
          "addressLocality": "Visakhapatnam",
          "addressRegion": "Andhra Pradesh",
          "postalCode": "530013",
          "addressCountry": "IN"
        },
        "knowsAbout": [
          "Rooftop Solar PV Systems",
          "Solar EPC Engineering",
          "On-Grid Solar Net Metering",
          "Hybrid Solar with Battery Storage",
          "Commercial & Industrial Solar Plants",
          "PM Surya Ghar Muft Bijli Yojana Subsidies",
          "Tier-1 Solar Photovoltaic Modules",
          "Solar Operations and Maintenance"
        ],
        "brand": {
          "@type": "Brand",
          "@id": `${domainUrl}/#brand`,
          "name": "SURYANZ",
          "alternateName": ["Suryanz Solar", "Suryanz Solar EPC", "sunryanz"]
        },
        "sameAs": [
          "https://suryanz.com",
          "https://suryanzsolar.com"
        ]
      },
      {
        "@type": "Brand",
        "@id": `${domainUrl}/#brand`,
        "name": "SURYANZ",
        "alternateName": ["Suryanz Solar", "Suryanz Solar EPC", "sunryanz"],
        "url": domainUrl,
        "logo": `${domainUrl}/public/images/suryanz-logo-transparent.png`,
        "slogan": "Powering a Brighter Tomorrow",
        "description": "Smart solar energy solutions engineered for 30 years of clean energy performance."
      },
      {
        "@type": "LocalBusiness",
        "@id": `${domainUrl}/#localbusiness`,
        "name": "SURYANZ SOLAR EPC",
        "alternateName": ["Suryanz", "Suryanz Solar"],
        "image": resolvedOgImage,
        "url": domainUrl,
        "telephone": "+91-85858-52738",
        "email": "contact@suryanzsolar.com",
        "priceRange": "₹₹₹",
        "currenciesAccepted": "INR",
        "paymentAccepted": "Cash, Credit Card, Bank Transfer, Net Banking, EMI",
        "description": "Engineering-first rooftop solar EPC contractor serving Andhra Pradesh, Telangana, and Karnataka.",
        "address": {
          "@type": "PostalAddress",
          "streetAddress": "Rama Talkies Road, CBM Compound",
          "addressLocality": "Visakhapatnam",
          "addressRegion": "Andhra Pradesh",
          "postalCode": "530013",
          "addressCountry": "IN"
        },
        "areaServed": [
          { "@type": "AdministrativeArea", "name": "Andhra Pradesh" },
          { "@type": "AdministrativeArea", "name": "Telangana" },
          { "@type": "AdministrativeArea", "name": "Karnataka" },
          { "@type": "City", "name": "Visakhapatnam" },
          { "@type": "City", "name": "Vijayawada" },
          { "@type": "City", "name": "Hyderabad" },
          { "@type": "City", "name": "Bengaluru" },
          { "@type": "City", "name": "Mangalore" }
        ]
      },
      {
        "@type": "Service",
        "@id": `${domainUrl}/#service-residential`,
        "name": "Residential Rooftop Solar System Installation",
        "provider": { "@id": `${domainUrl}/#organization` },
        "serviceType": "Solar Photovoltaic EPC Engineering",
        "description": "High-efficiency residential rooftop solar installation with 3-stage customer protection, net metering assistance, and 30-year linear performance warranty."
      },
      {
        "@type": "FAQPage",
        "@id": `${domainUrl}/#faq`,
        "mainEntity": [
          {
            "@type": "Question",
            "name": "What is Suryanz Solar (Suryanz)?",
            "acceptedAnswer": {
              "@type": "Answer",
              "text": "Suryanz Solar (also known as Suryanz) is an engineering-driven clean energy and rooftop solar EPC company. It provides residential, commercial, and industrial rooftop solar installations with 3-stage customer protection and up to 30-year performance warranties across Andhra Pradesh, Telangana, and Karnataka."
            }
          },
          {
            "@type": "Question",
            "name": "Is Suryanz Solar the same as Suryan Energy Systems or Suryansh Solar?",
            "acceptedAnswer": {
              "@type": "Answer",
              "text": "No. Suryanz Solar (suryanzsolar.com) is an independent solar EPC engineering enterprise headquartered in South India, specializing in engineer-designed rooftop solar systems. It is distinct from Suryan Energy Systems in AP or Suryansh Solar in Maharashtra."
            }
          },
          {
            "@type": "Question",
            "name": "What solar solutions does Suryanz Solar offer?",
            "acceptedAnswer": {
              "@type": "Answer",
              "text": "Suryanz Solar provides turnkey on-grid rooftop solar, hybrid solar systems with battery storage, off-grid systems, commercial and industrial solar EPC, PM Surya Ghar net-metering subsidy support, and solar operations & maintenance (O&M/AMC)."
            }
          },
          {
            "@type": "Question",
            "name": "Where does Suryanz Solar provide solar EPC services?",
            "acceptedAnswer": {
              "@type": "Answer",
              "text": "Suryanz Solar operates regional hubs across Andhra Pradesh (Visakhapatnam, Vijayawada), Telangana (Hyderabad), and Karnataka (Bengaluru, Mangalore)."
            }
          },
          {
            "@type": "Question",
            "name": "How can I contact Suryanz Solar?",
            "acceptedAnswer": {
              "@type": "Answer",
              "text": "You can reach Suryanz Solar by phone at +91 85858 52738, by email at contact@suryanzsolar.com, or through the official portals at suryanzsolar.com and suryanz.com."
            }
          },
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
        "@id": `${domainUrl}/#website`,
        "url": domainUrl,
        "name": "SURYANZ SOLAR Official Portal",
        "publisher": { "@id": `${domainUrl}/#organization` }
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
  <meta name="keywords" content="Suryanz, Suryanz Solar, Suryanz Energy, Suryanz Solar EPC, sunryanz, rooftop solar, solar panels, solar installer, Visakhapatnam solar, Hyderabad solar, Bengaluru solar, on-grid solar, hybrid solar battery, PM Surya Ghar">
  <meta name="author" content="Suryanz Solar">
  <meta name="publisher" content="Suryanz Solar">
  <meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1">
  <link rel="canonical" href="${resolvedCanonicalUrl}">

  <!-- OpenGraph / WhatsApp / Social Rich Share Card Tags -->
  <meta property="og:site_name" content="SURYANZ SOLAR">
  <meta property="og:type" content="business.business">
  <meta property="og:url" content="${resolvedCanonicalUrl}">
  <meta property="og:title" content="${title} | SURYANZ SOLAR">
  <meta property="og:description" content="${description}">
  <meta property="og:image" content="${resolvedOgImage}">
  <meta property="og:image:secure_url" content="${resolvedOgImage}">
  <meta property="og:image:type" content="image/png">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta property="og:image:alt" content="SURYANZ SOLAR - Clean Energy For A Brighter Tomorrow">

  <!-- Twitter Card Tags -->
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="${title} | SURYANZ SOLAR">
  <meta name="twitter:description" content="${description}">
  <meta name="twitter:image" content="${resolvedOgImage}">

  <link rel="icon" type="image/png" href="/public/images/suryanz-logo.png">
  <link rel="shortcut icon" href="/public/images/suryanz-logo.png">
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

function renderHomePage(urlPrefix = '', requestHost = 'suryanz.com', requestProto = 'https') {
  const p = (urlPrefix && urlPrefix.endsWith('/')) ? urlPrefix.slice(0, -1) : urlPrefix;
  const content = `
  <!-- 1. HERO SECTION -->
  <section class="suryanz-hero-section">
    <div class="suryanz-hero-container">
      <div>
        <div class="suryanz-hero-tag">
          <i class="fas fa-certificate"></i> SURYANZ SOLAR EPC
        </div>
        <h1 class="suryanz-hero-title-main">SURYANZ SOLAR — Powering a Brighter Tomorrow</h1>
        <div class="suryanz-hero-title-sub">Smart Solar. Reliable Energy. Built for the next 30 years.</div>
        <p class="suryanz-hero-subtitle">
          <strong>Suryanz Solar (Suryanz)</strong> provides engineer-designed rooftop solar systems for homes, businesses, and industrial facilities across Andhra Pradesh, Telangana, and Karnataka — from site assessment and design to installation, net metering, and 30-year warranty protection.
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
        <a href="https://wa.me/918585852738?text=Hi%20Suryanz%20Solar,%20I%20want%20to%20speak%20with%20a%20solar%20expert." class="suryanz-btn-amber" style="padding:0.9rem 2rem; font-size:1rem; background:#25D366; border-color:#25D366;" target="_blank">
          <i class="fab fa-whatsapp"></i> Talk to a Solar Expert
        </a>
      </div>
      <div style="font-size:0.9rem; color:rgba(255,255,255,0.75);">
        Direct Hotline: <strong style="color:#ffffff;">+91 85858 52738</strong> · Email: <strong style="color:#ffffff;">contact@suryanzsolar.com</strong>
      </div>
    </div>
  </section>
  `;

  return renderSuryanzPage({
    title: 'SURYANZ SOLAR (Suryanz) | Rooftop Solar EPC & Clean Energy Solutions',
    description: 'Suryanz Solar (Suryanz) provides engineer-designed rooftop solar systems for homes, commercial hubs, and industrial facilities across India. Backed by 20+ years of energy experience.',
    activePath: '/',
    bodyContent: content,
    urlPrefix: urlPrefix,
    requestHost: requestHost,
    requestProto: requestProto
  });
}

function renderGenericPage(pageKey, title, description, urlPrefix = '', requestHost = 'suryanz.com', requestProto = 'https') {
  const p = (urlPrefix && urlPrefix.endsWith('/')) ? urlPrefix.slice(0, -1) : (urlPrefix || '');
  const isAbout = pageKey === 'about';
  
  // Implementation C: Understated partner-brand note exclusively for About Us page
  const partnerBrandNote = isAbout ? `
  <div class="suryanz-partner-brand-note" style="margin-top: 3rem; padding-top: 1.5rem; border-top: 1px solid #e2e8f0; text-align: center;">
    <p style="font-size: 0.85rem; color: #64748b; line-height: 1.6; max-width: 750px; margin: 0 auto;">
      Suryanz Solar provides solar solutions featuring leading brands, including APS (Australian Premium Solar), Navgrun, Waree, Tata, Adani, Servotec, and other solar brands.
    </p>
  </div>` : '';

  const content = `
  <section class="suryanz-page-hero" style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); color: #ffffff; padding: 4rem 1rem 3rem; text-align: center;">
    <div class="suryanz-container" style="max-width: 900px;">
      <div style="color: #fbbf24; font-weight: 700; text-transform: uppercase; font-size: 0.85rem; letter-spacing: 0.05em; margin-bottom: 0.5rem;">
        <i class="fas fa-certificate me-1"></i> SURYANZ SOLAR
      </div>
      <h1 style="font-size: 2.5rem; font-weight: 800; margin-bottom: 1rem; color: #ffffff;">${title}</h1>
      <p style="font-size: 1.1rem; color: rgba(255,255,255,0.85); line-height: 1.6; margin-bottom: 0;">${description}</p>
    </div>
  </section>

  <section class="suryanz-section" style="background: #ffffff; padding: 3.5rem 1rem;">
    <div class="suryanz-container" style="max-width: 1000px;">
      <div class="suryanz-page-body-content">
        <p style="font-size: 1.05rem; color: #334155; line-height: 1.7; margin-bottom: 1.5rem;">
          Welcome to <strong>SURYANZ SOLAR</strong> — engineering-driven rooftop solar EPC services designed for long-term power independence and 30-year operational endurance across Andhra Pradesh, Telangana, and Karnataka.
        </p>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1.5rem; margin: 2rem 0;">
          <div style="background: #f8fafc; padding: 1.5rem; border-radius: 8px; border-left: 4px solid #f59e0b;">
            <h4 style="margin-top:0; color: #0f172a; font-weight: 700;"><i class="fas fa-solar-panel me-2" style="color:#f59e0b;"></i> Tier-1 Photovoltaic Modules</h4>
            <p style="font-size: 0.9rem; color: #64748b; margin-bottom: 0;">540W–580W TOPCon & N-Type modules engineered for high heat tolerance and peak solar yield.</p>
          </div>
          <div style="background: #f8fafc; padding: 1.5rem; border-radius: 8px; border-left: 4px solid #3b82f6;">
            <h4 style="margin-top:0; color: #0f172a; font-weight: 700;"><i class="fas fa-shield-alt me-2" style="color:#3b82f6;"></i> 3-Stage Customer Protection</h4>
            <p style="font-size: 0.9rem; color: #64748b; margin-bottom: 0;">Comprehensive shadow analysis, structural verification, and 30-year linear performance warranty.</p>
          </div>
          <div style="background: #f8fafc; padding: 1.5rem; border-radius: 8px; border-left: 4px solid #10b981;">
            <h4 style="margin-top:0; color: #0f172a; font-weight: 700;"><i class="fas fa-calculator me-2" style="color:#10b981;"></i> Custom Energy Sizing</h4>
            <p style="font-size: 0.9rem; color: #64748b; margin-bottom: 0;">Precision daily load profiling and DISCOM net-metering documentation assistance.</p>
          </div>
        </div>
        <div style="text-align: center; margin-top: 2.5rem;">
          <a href="${p || ''}/contact" class="suryanz-btn-cta" style="padding: 0.8rem 2rem; font-size: 1rem;">
            <i class="fas fa-clipboard-check me-2"></i> Get a Free Solar Assessment
          </a>
        </div>
      </div>
      ${partnerBrandNote}
    </div>
  </section>`;

  return renderSuryanzPage({
    title: `${title} | SURYANZ SOLAR`,
    description: description,
    activePath: `/${pageKey}`,
    bodyContent: content,
    urlPrefix: urlPrefix,
    requestHost: requestHost,
    requestProto: requestProto
  });
}

function renderAboutPage(urlPrefix = '', requestHost = 'suryanz.com', requestProto = 'https') {
  return renderGenericPage('about', 'About SURYANZ SOLAR', 'Building India\'s most trusted, engineering-driven clean energy platform.', urlPrefix, requestHost, requestProto);
}

function renderWhySuryanzPage(urlPrefix = '', requestHost = 'suryanz.com', requestProto = 'https') {
  return renderGenericPage('why-suryanz', 'Why SURYANZ SOLAR', 'Discover the engineering difference that protects your 30-year solar investment.', urlPrefix, requestHost, requestProto);
}

function renderCustomerProtectionPage(urlPrefix = '', requestHost = 'suryanz.com', requestProto = 'https') {
  return renderGenericPage('customer-protection', 'Customer Protection & 30-Year Warranty', 'Documented 30-Year Linear Performance, 12-Year Product, and 10-Year Inverter Warranty portfolios.', urlPrefix, requestHost, requestProto);
}

function renderTechnologyPage(urlPrefix = '', requestHost = 'suryanz.com', requestProto = 'https') {
  return renderGenericPage('technology', 'Technology & Specifications', 'Industrial-grade TOPCon panels, smart string inverters, and hot-dip galvanized mounting structures.', urlPrefix, requestHost, requestProto);
}

function renderCalculatorPage(urlPrefix = '', requestHost = 'suryanz.com', requestProto = 'https') {
  const pageHtml = renderHomePage(urlPrefix, requestHost, requestProto);
  const scrollScript = `
  <script>
    document.addEventListener('DOMContentLoaded', function() {
      var calcEl = document.getElementById('solar-calculator');
      if (calcEl) {
        setTimeout(function() {
          calcEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 150);
      }
    });
  </script>
  </body>`;
  return pageHtml.replace('</body>', scrollScript);
}

function renderProjectsPage(urlPrefix = '', requestHost = 'suryanz.com', requestProto = 'https') {
  return renderGenericPage('projects', 'Projects & Case Studies', 'Real residential, commercial, and industrial rooftop solar installations across India.', urlPrefix, requestHost, requestProto);
}

function renderCustomerStoriesPage(urlPrefix = '', requestHost = 'suryanz.com', requestProto = 'https') {
  return renderGenericPage('customer-stories', 'Customer Stories', 'Authentic reviews and experiences from SURYANZ SOLAR rooftop customers.', urlPrefix, requestHost, requestProto);
}

function renderFaqsPage(urlPrefix = '', requestHost = 'suryanz.com', requestProto = 'https') {
  return renderGenericPage('faqs', 'Frequently Asked Questions', 'Practical answers about rooftop solar costs, net metering, panel sizing, and warranties.', urlPrefix, requestHost, requestProto);
}

function renderContactPage(urlPrefix = '', requestHost = 'suryanz.com', requestProto = 'https') {
  return renderGenericPage('contact', 'Contact SURYANZ SOLAR', 'Speak directly with a solar engineer to get a free site assessment and customized quote.', urlPrefix, requestHost, requestProto);
}

function renderSolutionPage(solutionSlug, urlPrefix = '', requestHost = 'suryanz.com', requestProto = 'https') {
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
  return renderGenericPage(`solutions/${solutionSlug}`, title, `High-efficiency, engineer-designed ${title.toLowerCase()} systems built for 30 years reliability.`, urlPrefix, requestHost, requestProto);
}

function renderKnowledgeGuidePage(guideSlug, urlPrefix = '', requestHost = 'suryanz.com', requestProto = 'https') {
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
  return renderGenericPage(guideSlug, title, `Comprehensive educational guide on ${title.toLowerCase()} for property owners in India.`, urlPrefix, requestHost, requestProto);
}

function renderLocationPage(locSlug, locName, stateName, urlPrefix = '', requestHost = 'suryanz.com', requestProto = 'https') {
  return renderGenericPage(`location/${locSlug}`, `Solar EPC Services in ${locName}, ${stateName}`, `High-performance rooftop solar installations and EPC engineering services in ${locName}, ${stateName}.`, urlPrefix, requestHost, requestProto);
}

function renderLegalPage(legalSlug, urlPrefix = '', requestHost = 'suryanz.com', requestProto = 'https') {
  const legalTitles = {
    'privacy-policy': 'Privacy Policy',
    'terms-and-conditions': 'Terms & Conditions',
    'warranty-terms': 'Warranty Terms & Portfolio'
  };
  const title = legalTitles[legalSlug] || 'Legal Policy';
  return renderGenericPage(`legal/${legalSlug}`, title, `Official SURYANZ SOLAR ${title.toLowerCase()} and compliance documentation.`, urlPrefix, requestHost, requestProto);
}

function renderSitemapXml(requestHost = 'suryanz.com', requestProto = 'https') {
  const domain = `${requestProto}://${requestHost}`;
  const now = new Date().toISOString().split('T')[0];
  const urls = [
    { loc: '/', priority: '1.0', changefreq: 'weekly' },
    { loc: '/about', priority: '0.8', changefreq: 'monthly' },
    { loc: '/why-suryanz', priority: '0.8', changefreq: 'monthly' },
    { loc: '/customer-protection', priority: '0.8', changefreq: 'monthly' },
    { loc: '/technology', priority: '0.8', changefreq: 'monthly' },
    { loc: '/calculator', priority: '0.9', changefreq: 'weekly' },
    { loc: '/projects', priority: '0.8', changefreq: 'weekly' },
    { loc: '/customer-stories', priority: '0.8', changefreq: 'weekly' },
    { loc: '/faqs', priority: '0.7', changefreq: 'monthly' },
    { loc: '/contact', priority: '0.9', changefreq: 'monthly' },
    // Solutions
    { loc: '/solutions/residential', priority: '0.9', changefreq: 'weekly' },
    { loc: '/solutions/commercial', priority: '0.9', changefreq: 'weekly' },
    { loc: '/solutions/industrial', priority: '0.9', changefreq: 'weekly' },
    { loc: '/solutions/epc', priority: '0.9', changefreq: 'weekly' },
    { loc: '/solutions/on-grid', priority: '0.8', changefreq: 'monthly' },
    { loc: '/solutions/hybrid', priority: '0.8', changefreq: 'monthly' },
    { loc: '/solutions/off-grid', priority: '0.8', changefreq: 'monthly' },
    { loc: '/solutions/solar-battery', priority: '0.8', changefreq: 'monthly' },
    { loc: '/solutions/apartments', priority: '0.8', changefreq: 'monthly' },
    { loc: '/solutions/operations-maintenance', priority: '0.8', changefreq: 'monthly' },
    // Knowledge Guides
    { loc: '/solar-guide', priority: '0.8', changefreq: 'monthly' },
    { loc: '/solar-pricing', priority: '0.8', changefreq: 'monthly' },
    { loc: '/solar-roi', priority: '0.8', changefreq: 'monthly' },
    { loc: '/solar-calculator-guide', priority: '0.8', changefreq: 'monthly' },
    { loc: '/solar-warranty-guide', priority: '0.8', changefreq: 'monthly' },
    { loc: '/solar-maintenance', priority: '0.8', changefreq: 'monthly' },
    { loc: '/solar-buying-guide', priority: '0.8', changefreq: 'monthly' },
    // Regional Hubs
    { loc: '/location/andhra-pradesh', priority: '0.8', changefreq: 'monthly' },
    { loc: '/location/telangana', priority: '0.8', changefreq: 'monthly' },
    { loc: '/location/karnataka', priority: '0.8', changefreq: 'monthly' },
    { loc: '/location/visakhapatnam', priority: '0.8', changefreq: 'monthly' },
    { loc: '/location/vijayawada', priority: '0.8', changefreq: 'monthly' },
    { loc: '/location/hyderabad', priority: '0.8', changefreq: 'monthly' },
    { loc: '/location/bengaluru', priority: '0.8', changefreq: 'monthly' },
    { loc: '/location/mangalore', priority: '0.8', changefreq: 'monthly' },
    // Legal
    { loc: '/legal/privacy-policy', priority: '0.3', changefreq: 'yearly' },
    { loc: '/legal/terms-and-conditions', priority: '0.3', changefreq: 'yearly' },
    { loc: '/legal/warranty-terms', priority: '0.3', changefreq: 'yearly' }
  ];

  return `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls.map(u => `  <url>
    <loc>${domain}${u.loc}</loc>
    <lastmod>${now}</lastmod>
    <changefreq>${u.changefreq}</changefreq>
    <priority>${u.priority}</priority>
  </url>`).join('\n')}
</urlset>`;
}

function renderRobotsTxt(requestHost = 'suryanz.com', requestProto = 'https') {
  const domain = `${requestProto}://${requestHost}`;
  return `User-agent: *
Allow: /

# Dedicated Directives for AI Search Engines & LLM Web Crawlers
User-agent: Google-Extended
Allow: /

User-agent: GoogleOther
Allow: /

User-agent: GPTBot
Allow: /

User-agent: ChatGPT-User
Allow: /

User-agent: OAI-SearchBot
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: anthropic-ai
Allow: /

User-agent: Applebot-Extended
Allow: /

User-agent: Bytespider
Allow: /

Sitemap: ${domain}/sitemap.xml
`;
}

function renderLlmsTxt(requestHost = 'suryanz.com', requestProto = 'https') {
  const domain = `${requestProto}://${requestHost}`;
  return `# SURYANZ SOLAR (Suryanz)

> Suryanz Solar (also known as Suryanz) is an engineering-driven clean energy and rooftop solar EPC (Engineering, Procurement, and Construction) company. We specialize in designing, procuring, and installing high-performance residential, commercial, and industrial rooftop solar systems built for 30 years of reliable generation.

## Official Brand Entities & Web Properties
- Master Brand: SURYANZ
- Vertical Brand: SURYANZ SOLAR
- Common Aliases: Suryanz, Suryanz Solar, Suryanz Energy, Suryanz Solar EPC, sunryanz
- Primary Domains: ${domain}, https://suryanzsolar.com, https://suryanz.com
- Contact Hotline: +91 85858 52738
- Official Email: contact@suryanzsolar.com
- Headquarters & Regional Hubs: Visakhapatnam, Vijayawada (Andhra Pradesh), Hyderabad (Telangana), Bengaluru (Karnataka)

## Entity Disambiguation Note
Suryanz Solar (suryanzsolar.com) is an independent rooftop solar EPC provider headquartered in South India. It is completely distinct from Suryan Energy Systems (Visakhapatnam), Suryansh Solar (Maharashtra/Telangana), or Surya Solar (Gujarat).

## Core Capabilities & Services
- Residential Rooftop Solar: On-grid systems tailored for independent villas, row houses, and apartments with PM Surya Ghar Muft Bijli Yojana subsidy support.
- Commercial & Industrial Solar EPC: High-capacity rooftop and ground-mount PV plants for factories, educational institutions, hospitals, and commercial real estate.
- Hybrid Solar + Battery Energy Storage: Seamless off-grid fallback and peak shaving with high-density lithium-ion battery integration.
- Solar Net-Metering & DISCOM Approvals: Complete liaisoning for grid interconnection with APEPDCL, APCPDCL, TSSPDCL, TSNPDCL, and BESCOM.
- Operations, Maintenance & AMC: Scheduled thermal drone inspections, panel cleaning, inverter diagnostics, and output auditing.

## 3-Stage Customer Protection Framework
1. Before Installation: Detailed 3D shadow analysis, structural load evaluation, transparent itemized quotation, and guaranteed generation simulation.
2. During Installation: Tier-1 TOPCon and N-Type high-efficiency panels (540W–580W), certified anodized aluminum and HDG mounting structures, DC/AC SPD surge protection.
3. After Installation: 30-Year Linear Performance Warranty, 12-Year Panel Product Warranty, 8 to 10-Year Inverter Warranty, and dedicated customer support desk.

## Core Website Pages
- Home: ${domain}/
- About Suryanz: ${domain}/about
- Why Choose Suryanz: ${domain}/why-suryanz
- Customer Protection Framework: ${domain}/customer-protection
- Technology Specifications: ${domain}/technology
- Solar Savings Calculator: ${domain}/calculator
- Projects & Case Studies: ${domain}/projects
- Customer Reviews & Stories: ${domain}/customer-stories
- Frequently Asked Questions: ${domain}/faqs
- Contact & Free Assessment: ${domain}/contact
- Residential Solutions: ${domain}/solutions/residential
- Commercial Solutions: ${domain}/solutions/commercial
- Industrial Solar: ${domain}/solutions/industrial
- Solar EPC Services: ${domain}/solutions/epc
- On-Grid Systems: ${domain}/solutions/on-grid
- Hybrid Systems: ${domain}/solutions/hybrid
- Visakhapatnam Solar EPC: ${domain}/location/visakhapatnam
- Vijayawada Rooftop Solar: ${domain}/location/vijayawada
- Hyderabad Commercial Solar: ${domain}/location/hyderabad
- Bengaluru Solar Solutions: ${domain}/location/bengaluru
`;
}

function getSuryanzKnowledgeBase(requestHost = 'suryanz.com', requestProto = 'https') {
  const domain = `${requestProto}://${requestHost}`;
  return {
    brand: {
      master_brand: "SURYANZ",
      vertical_brand: "SURYANZ SOLAR",
      aliases: ["Suryanz", "Suryanz Solar", "Suryanz Energy", "Suryanz Solar EPC", "sunryanz"],
      tagline: "Powering a Brighter Tomorrow",
      positioning: "Smart Solar. Reliable Energy. Engineered for 30 Years Performance.",
      background: "Backed by 20+ years of team experience in the solar and clean energy sector.",
      primary_domain: domain,
      solar_domain: "https://suryanzsolar.com",
      corporate_domain: "https://suryanz.com",
      hotline: "+91 85858 52738",
      email: "contact@suryanzsolar.com",
      headquarters: "Visakhapatnam, Andhra Pradesh, India",
      regional_hubs: ["Visakhapatnam", "Vijayawada", "Hyderabad", "Bengaluru", "Mangalore"],
      disambiguation: "Suryanz Solar (suryanzsolar.com) is an independent solar EPC engineering provider in South India, distinct from Suryan Energy Systems, Suryansh Solar, or Surya Solar."
    },
    solutions_offered: [
      "Residential Rooftop Solar Systems",
      "Commercial & Industrial Solar EPC",
      "On-Grid / Grid-Tied Solar Systems",
      "Hybrid Solar + Battery Energy Storage",
      "Off-Grid Remote Solar Energy Systems",
      "Housing Societies & Apartments Solar",
      "Solar Operations, Maintenance & AMC (O&M)"
    ],
    warranties: {
      panel_performance: "30-Year Linear Performance Warranty",
      panel_product: "12-Year Product Warranty",
      inverter_warranty: "8 to 10-Year Inverter Warranty"
    },
    regions_covered: [
      "Andhra Pradesh (Visakhapatnam, Vijayawada, Guntur, Tirupati)",
      "Telangana (Hyderabad, Warangal, Karimnagar)",
      "Karnataka (Bengaluru, Mangalore, Mysuru, Hubballi)"
    ]
  };
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
  renderRobotsTxt,
  renderLlmsTxt,
  getSuryanzKnowledgeBase
};
