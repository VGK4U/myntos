/**
 * MyntOS SaaS — Module Entitlement & Feature Spotlight Component
 * Replaces harsh 403 errors with a positive, professional module preview & upgrade experience.
 */
(function() {
    'use strict';

    const MODULE_DEFINITIONS = {
        CRM_LEADS: {
            code: 'CRM_LEADS',
            name: 'CRM & Telecalling Suite',
            icon: 'fas fa-funnel-dollar',
            color: '#4f46e5',
            gradient: 'linear-gradient(135deg, #6366f1 0%, #4338ca 100%)',
            tagline: 'Supercharge your sales pipeline with automated lead capture & VoIP telecalling.',
            perks: [
                'Instant lead capture from Meta Ads, website forms & campaigns',
                'Built-in VoIP telecalling dialer with live call notes & recording logs',
                'Automated WhatsApp follow-up sequences & smart lead assignments',
                'Visual deal stages, quotation builder & sales forecasting'
            ]
        },
        ACCOUNTS_FINANCE: {
            code: 'ACCOUNTS_FINANCE',
            name: 'Accounts, GST Invoicing & Ledgers',
            icon: 'fas fa-file-invoice-dollar',
            color: '#059669',
            gradient: 'linear-gradient(135deg, #10b981 0%, #047857 100%)',
            tagline: 'Comprehensive Indian GST compliant invoicing, multi-company ledgers & cashflow tracking.',
            perks: [
                'GST-ready sales invoices, credit notes & payment vouchers',
                'Real-time cashflow registers & automated bank reconciliations',
                'Interactive Profit & Loss, Balance Sheet & Trial Balance analytics',
                'Automated customer payment reminders and accounts receivable aging'
            ]
        },
        INVENTORY_STOCK: {
            code: 'INVENTORY_STOCK',
            name: 'Stock, Inventory & Warehouse Hub',
            icon: 'fas fa-boxes',
            color: '#d97706',
            gradient: 'linear-gradient(135deg, #f59e0b 0%, #b45309 100%)',
            tagline: 'Full visibility over multi-warehouse stock, purchase orders & spare part movements.',
            perks: [
                'Multi-location warehouse stock tracking & low-stock alerts',
                'Purchase orders, Goods Receipt Notes (GRN) & intake QC validation',
                'Bill of Materials (BOM) & manufacturing consumption orders',
                'Live spare parts inventory & inter-company stock transfers'
            ]
        },
        STAFF_HRMS: {
            code: 'STAFF_HRMS',
            name: 'Staff HRMS, Attendance & Field GPS',
            icon: 'fas fa-user-check',
            color: '#2563eb',
            gradient: 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)',
            tagline: 'Empower your workforce with GPS attendance, daily work planning & automated payroll.',
            perks: [
                'Geofenced biometric & selfie clock-in / clock-out tracking',
                'Live GPS route tracking & field journey verification',
                'Daily work planner, timesheets & task phase management',
                'Automated monthly payroll, claim reimbursements & KRA appraisals'
            ]
        },
        SERVICE_TICKETS: {
            code: 'SERVICE_TICKETS',
            name: 'Service Tickets & Support Operations',
            icon: 'fas fa-tools',
            color: '#0891b2',
            gradient: 'linear-gradient(135deg, #06b6d4 0%, #0e7490 100%)',
            tagline: 'Deliver world-class field support with SLA tracking, technician dispatch & spare requests.',
            perks: [
                'Smart ticket triage, prioritization & technician dispatch',
                'Warranty claim validation & spare replacement workflows',
                'Automated customer WhatsApp status alerts & resolution reports',
                'SLA compliance monitoring & field technician rating metrics'
            ]
        },
        SOLAR_EV: {
            code: 'SOLAR_EV',
            name: 'Solar & EV Specialized Workflows',
            icon: 'fas fa-solar-panel',
            color: '#10b981',
            gradient: 'linear-gradient(135deg, #34d399 0%, #059669 100%)',
            tagline: 'Tailored workflows for solar installation feasibility, subsidies & EV vehicle tracking.',
            perks: [
                'Solar feasibility site survey & electrical load estimation forms',
                'Government subsidy documentation & DISCOM approval tracking',
                'EV scooter serial & battery warranty registration',
                'Milestone-based project billing & vendor commissioning logs'
            ]
        },
        MARKETPLACE: {
            code: 'MARKETPLACE',
            name: 'B2B / B2C Marketplace Store',
            icon: 'fas fa-store',
            color: '#8b5cf6',
            gradient: 'linear-gradient(135deg, #a855f7 0%, #6d28d9 100%)',
            tagline: 'Open digital storefronts, showcase catalogs to customers & manage vendor commissions.',
            perks: [
                'Digital catalog showcase with high-res product galleries',
                'Direct customer purchase orders & coupon redemptions',
                'Automated inter-company margins & merchant settlements',
                'Integrated payment gateways & order delivery tracking'
            ]
        }
    };

    function renderSpotlightCard(moduleKey, options = {}) {
        const mod = MODULE_DEFINITIONS[moduleKey] || {
            code: moduleKey || 'PREMIUM_MODULE',
            name: options.moduleName || 'Advanced Module',
            icon: 'fas fa-star',
            color: '#4f46e5',
            gradient: 'linear-gradient(135deg, #6366f1 0%, #4338ca 100%)',
            tagline: 'This feature is part of our advanced business modules.',
            perks: [
                'Streamlined workflows & automations tailored for your team',
                'Real-time analytics, reporting & data exports',
                'Role-based permissions & multi-user collaboration',
                'Direct priority support and continuous platform updates'
            ]
        };

        return `
        <div style="max-width: 680px; margin: 40px auto; background: white; border-radius: 16px; box-shadow: 0 10px 30px rgba(0,0,0,0.08); border: 1px solid #e2e8f0; overflow: hidden; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
            <!-- Header Gradient Banner -->
            <div style="background: ${mod.gradient}; padding: 32px 28px; color: white; text-align: center; position: relative;">
                <div style="display: inline-flex; align-items: center; justify-content: center; width: 64px; height: 64px; border-radius: 50%; background: rgba(255,255,255,0.2); backdrop-filter: blur(8px); margin-bottom: 14px; font-size: 28px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
                    <i class="${mod.icon}"></i>
                </div>
                <div style="font-size: 11.5px; font-weight: 800; text-transform: uppercase; letter-spacing: 1px; background: rgba(255,255,255,0.25); display: inline-block; padding: 3px 12px; border-radius: 20px; margin-bottom: 8px;">
                    ✨ Module Spotlight
                </div>
                <h2 style="margin: 0 0 6px 0; font-size: 24px; font-weight: 800; letter-spacing: -0.3px;">${mod.name}</h2>
                <p style="margin: 0 auto; max-width: 520px; font-size: 13.5px; opacity: 0.95; line-height: 1.4;">${mod.tagline}</p>
            </div>

            <!-- Body Perks -->
            <div style="padding: 26px 28px;">
                <div style="font-size: 12px; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.6px; margin-bottom: 14px;">
                    What you can achieve with this module:
                </div>
                <div style="display: flex; flex-direction: column; gap: 10px; margin-bottom: 24px;">
                    ${mod.perks.map(p => `
                        <div style="display: flex; align-items: flex-start; gap: 10px; font-size: 13.5px; color: #334155;">
                            <i class="fas fa-check-circle" style="color: ${mod.color}; margin-top: 3px; font-size: 15px; flex-shrink: 0;"></i>
                            <span>${p}</span>
                        </div>
                    `).join('')}
                </div>

                <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 14px 16px; margin-bottom: 24px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px;">
                    <div>
                        <div style="font-weight: 700; font-size: 13px; color: #0f172a;">Ready to add this to your workspace?</div>
                        <div style="font-size: 12px; color: #64748b;">Contact your platform account administrator to activate this module instantly.</div>
                    </div>
                    <button type="button" onclick="window.ModuleSpotlight.requestActivation('${mod.code}', '${mod.name.replace(/'/g, "\'")}')" style="background: ${mod.color}; color: white; border: none; font-weight: 700; font-size: 12.5px; padding: 8px 16px; border-radius: 6px; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; box-shadow: 0 2px 6px rgba(0,0,0,0.1);">
                        <i class="fas fa-rocket"></i> Request Activation
                    </button>
                </div>

                <!-- Footer Navigation -->
                <div style="display: flex; justify-content: center; gap: 12px;">
                    <a href="/staff/progress" style="display: inline-flex; align-items: center; gap: 6px; padding: 8px 20px; font-size: 13px; font-weight: 600; color: #475569; text-decoration: none; border-radius: 6px; border: 1px solid #cbd5e1; background: white;">
                        <i class="fas fa-arrow-left"></i> Return to Dashboard
                    </a>
                </div>
            </div>
        </div>
        `;
    }

    async function requestActivation(moduleCode, moduleName) {
        if (!confirm(`Would you like to request activation for the "${moduleName}" module? Our team will be notified immediately.`)) {
            return;
        }

        try {
            if (window.staffFetch) {
                await window.staffFetch('/api/v1/staff/accounts/request-module-upgrade', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ module_code: moduleCode, module_name: moduleName })
                }).catch(() => {});
            }
            alert(`🎉 Thank you!

Your activation request for "${moduleName}" has been submitted to your platform administrator.`);
        } catch (e) {
            alert(`🎉 Thank you! Your request for "${moduleName}" has been recorded.`);
        }
    }

    function mountToContainer(containerSelector, moduleKey, options = {}) {
        const container = document.querySelector(containerSelector);
        if (container) {
            container.innerHTML = renderSpotlightCard(moduleKey, options);
        }
    }

    window.ModuleSpotlight = {
        DEFINITIONS: MODULE_DEFINITIONS,
        render: renderSpotlightCard,
        mount: mountToContainer,
        requestActivation: requestActivation
    };
})();
