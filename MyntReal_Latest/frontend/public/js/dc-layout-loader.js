/**
 * DC Protocol (Jan 22, 2026): Common Layout Loader
 * Single source of truth for header and sidebar injection
 * 
 * This script:
 * 1. Removes any existing .top-header elements
 * 2. Injects the common header from /public/layouts/staff-header.html
 * 3. Ensures sidebar container exists for StaffSidebar.init()
 * 
 * Usage: Include this script BEFORE staff_sidebar.js in any staff/admin/partner page
 */

(function() {
    'use strict';

    const DC_LAYOUT = {
        HEADER_URL: '/public/layouts/staff-header.html',
        HEADER_CACHE_KEY: 'dc_header_html',
        HEADER_CACHE_VERSION: 'v1.0.0',
        DEBUG: false,

        log: function(...args) {
            if (this.DEBUG) console.log('[DC-LAYOUT]', ...args);
        },

        init: async function() {
            this.log('Initializing layout loader...');
            
            await this.injectHeader();
            this.ensureSidebarContainer();
            this.log('Layout initialization complete');
        },

        injectHeader: async function() {
            const existingHeader = document.querySelector('.dc-top-header, #dc-top-header');
            if (existingHeader) {
                this.log('Common header already exists, skipping injection');
                return;
            }

            const legacyHeader = document.querySelector('.top-header, header.top-header');
            if (legacyHeader) {
                this.log('Removing legacy inline header');
                legacyHeader.remove();
            }

            let headerHtml = null;
            
            try {
                headerHtml = sessionStorage.getItem(this.HEADER_CACHE_KEY);
                const cachedVersion = sessionStorage.getItem(this.HEADER_CACHE_KEY + '_version');
                
                if (!headerHtml || cachedVersion !== this.HEADER_CACHE_VERSION) {
                    this.log('Fetching header from server...');
                    const response = await fetch(this.HEADER_URL);
                    if (!response.ok) throw new Error('Failed to fetch header');
                    headerHtml = await response.text();
                    sessionStorage.setItem(this.HEADER_CACHE_KEY, headerHtml);
                    sessionStorage.setItem(this.HEADER_CACHE_KEY + '_version', this.HEADER_CACHE_VERSION);
                }
            } catch (err) {
                console.error('[DC-LAYOUT] Error loading header:', err);
                return;
            }

            const body = document.body;
            const headerContainer = document.createElement('div');
            headerContainer.id = 'dc-header-container';
            headerContainer.innerHTML = headerHtml;
            
            body.insertBefore(headerContainer, body.firstChild);
            this.log('Header injected successfully');

            const scriptContent = headerContainer.querySelector('script');
            if (scriptContent) {
                const newScript = document.createElement('script');
                newScript.textContent = scriptContent.textContent;
                document.body.appendChild(newScript);
                scriptContent.remove();
            }
        },

        ensureSidebarContainer: function() {
            if (document.getElementById('staffSidebar')) {
                this.log('Sidebar container already exists');
                return;
            }

            const sidebar = document.createElement('nav');
            sidebar.id = 'staffSidebar';
            sidebar.className = 'sidebar';
            
            const headerContainer = document.getElementById('dc-header-container');
            if (headerContainer && headerContainer.nextSibling) {
                headerContainer.parentNode.insertBefore(sidebar, headerContainer.nextSibling);
            } else {
                const body = document.body;
                const firstChild = body.firstChild;
                if (firstChild) {
                    body.insertBefore(sidebar, firstChild.nextSibling);
                } else {
                    body.appendChild(sidebar);
                }
            }
            this.log('Sidebar container created');
        },

        removeInlineHeaderCSS: function() {
            const style = document.createElement('style');
            style.textContent = `
                .top-header:not(.dc-top-header) { display: none !important; }
                header.top-header:not(.dc-top-header) { display: none !important; }
            `;
            document.head.appendChild(style);
        }
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => DC_LAYOUT.init());
    } else {
        DC_LAYOUT.init();
    }

    window.DC_LAYOUT = DC_LAYOUT;
})();
