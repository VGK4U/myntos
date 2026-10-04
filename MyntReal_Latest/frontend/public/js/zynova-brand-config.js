/**
 * ZYNOVA OS — Canonical Brand Configuration (P0 Single Source of Truth)
 * Authoritative SaaS Product Identity definitions for Web, Mobile, and Native representations.
 */
(function () {
    if (window.ZYNOVA_BRAND) return;

    window.ZYNOVA_BRAND = {
        productName: "ZYNOVA OS",
        companyBrand: "ZYNOVA OS",
        poweredBy: "Zynova Mobility Private Limited",
        tagline: "Next-Gen SaaS Mobility & Operations Platform",
        logoUrl: "/public/zynova-os-logo.png",
        logoOriginalUrl: "/public/zynova-os-logo-original.png",
        iconUrl: "/public/zynova-os-icon.png",
        faviconUrl: "/public/favicon.ico",
        themeColors: {
            primary: "#6c3de8",
            primaryDark: "#0f172a",
            secondary: "#10b981",
            accent: "#38bdf8",
            background: "#f8fafc",
            surface: "#ffffff",
            border: "#cbd5e1"
        },
        socialLinks: {
            facebook: "https://www.facebook.com/ZynovaOS/",
            instagram: "https://www.instagram.com/zynovaos/?hl=en"
        }
    };
})();
