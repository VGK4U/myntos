/**
 * MintOS / ZynovaOS Social Media Manager Engine
 * Complete frontend controller for multi-tenant AI content calendar,
 * multi-platform publishing, channel connections, and performance analytics.
 */

(function() {
    'use strict';

    const API_BASE = '/api/v1/social';

    const SocialMediaManager = {
        state: {
            companyId: null,
            companyName: 'MintOS Workspace',
            accounts: [],
            calendarMonth: new Date().getMonth() + 1,
            calendarYear: new Date().getFullYear(),
            posts: [],
            analytics: null,
            settings: null,
            activeEditingPost: null
        },

        // ─────────────────────────────────────────────────────────────────────
        // 1. Initialization & Bootstrapping
        // ─────────────────────────────────────────────────────────────────────
        init: async function() {
            console.log('[SOCIAL-MEDIA] Initializing Social Media Manager module...');
            await this._setupCompanyContext();
            this._populateDateDropdowns();
            this._setupEventListeners();

            // Load initial view data
            try {
                await Promise.all([
                    this.loadOverview(),
                    this.loadAccounts(),
                    this.loadCalendar(),
                    this.loadAnalytics(),
                    this.loadSettings()
                ]);
            } catch (err) {
                console.warn('[SOCIAL-MEDIA] Background data load encountered errors:', err);
            }
        },

        _setupCompanyContext: async function() {
            try {
                const userRaw = localStorage.getItem('staff_user');
                if (userRaw) {
                    const user = JSON.parse(userRaw);
                    this.state.companyId = user.active_company_id || user.company_id || localStorage.getItem('staff_company_id') || 2;
                    this.state.companyName = user.company_name || (this.state.companyId == 1 ? 'Mynt Real LLP' : 'Zynova Mobility');
                } else {
                    this.state.companyId = 2;
                    this.state.companyName = 'Zynova Mobility';
                }
            } catch (e) {
                console.warn('[SOCIAL-MEDIA] Error parsing user context:', e);
                this.state.companyId = 2;
                this.state.companyName = 'Zynova Mobility';
            }

            await this.loadCompanies();
            this._updateCompanyLabels();
        },

        loadCompanies: async function() {
            try {
                const res = await this._apiCall('/companies');
                if (res && res.companies && res.companies.length > 0) {
                    const select = document.getElementById('socialCompanySelect');
                    if (select) {
                        select.innerHTML = res.companies.map(c => 
                            `<option value="${c.id}" ${c.id == this.state.companyId ? 'selected' : ''}>${c.name}</option>`
                        ).join('');
                    }
                    const activeComp = res.companies.find(c => c.id == this.state.companyId);
                    if (activeComp) {
                        this.state.companyName = activeComp.name;
                    }
                }
            } catch (e) {
                console.warn('[SOCIAL-MEDIA] Could not load accessible companies list:', e);
            }
        },

        switchCompany: async function(companyId) {
            this.state.companyId = parseInt(companyId, 10);
            const select = document.getElementById('socialCompanySelect');
            if (select && select.selectedOptions && select.selectedOptions[0]) {
                this.state.companyName = select.selectedOptions[0].text;
            }
            this._updateCompanyLabels();

            console.log(`[SOCIAL-MEDIA] Switched active company to ID ${this.state.companyId} (${this.state.companyName})`);

            // Reload all data for the newly selected company
            try {
                await Promise.all([
                    this.loadOverview(),
                    this.loadAccounts(),
                    this.loadCalendar(),
                    this.loadAnalytics(),
                    this.loadSettings()
                ]);
            } catch (err) {
                console.warn('[SOCIAL-MEDIA] Reload on company switch encountered errors:', err);
            }
        },

        _updateCompanyLabels: function() {
            const companyBadge = document.getElementById('companyBadge');
            if (companyBadge) {
                companyBadge.innerHTML = `<i class="fas fa-building"></i> ${this.state.companyName}`;
            }
            document.querySelectorAll('.active-tenant-name').forEach(el => {
                el.innerText = this.state.companyName;
            });
        },

        _showMigrationNotice: function(msg) {
            const noticeContainer = document.getElementById('migrationNoticeContainer');
            if (noticeContainer) {
                noticeContainer.innerHTML = `
                    <div class="alert alert-warning border-0 shadow-sm d-flex align-items-center gap-3 mb-4" style="border-radius: 12px;">
                        <i class="fas fa-database fa-2x text-warning"></i>
                        <div class="flex-grow-1">
                            <div class="fw-bold">Database Setup Notice (Alembic Migration Pending)</div>
                            <div class="small">
                                ${msg || 'The 6 Social Media Manager database tables have not been created yet in the connected database. Run <code>python -m alembic upgrade head</code> to initialize the schema.'}
                            </div>
                        </div>
                    </div>
                `;
            }
        },

        _populateDateDropdowns: function() {
            const mSelect = document.getElementById('calMonthSelect');
            const ySelect = document.getElementById('calYearSelect');
            const months = [
                'January', 'February', 'March', 'April', 'May', 'June',
                'July', 'August', 'September', 'October', 'November', 'December'
            ];

            if (mSelect) {
                mSelect.innerHTML = months.map((m, idx) => 
                    `<option value="${idx + 1}" ${idx + 1 === this.state.calendarMonth ? 'selected' : ''}>${m}</option>`
                ).join('');
            }

            if (ySelect) {
                const curY = new Date().getFullYear();
                ySelect.innerHTML = [curY, curY + 1].map(y => 
                    `<option value="${y}" ${y === this.state.calendarYear ? 'selected' : ''}>${y}</option>`
                ).join('');
            }

            const genM = document.getElementById('genMonth');
            const genY = document.getElementById('genYear');
            if (genM) genM.value = this.state.calendarMonth;
            if (genY) genY.value = this.state.calendarYear;
        },

        _setupEventListeners: function() {
            const captionX = document.getElementById('editCaptionX');
            const charCountX = document.getElementById('charCountX');
            if (captionX && charCountX) {
                captionX.addEventListener('input', function() {
                    charCountX.innerText = captionX.value.length;
                    if (captionX.value.length > 280) {
                        charCountX.classList.add('text-danger');
                    } else {
                        charCountX.classList.remove('text-danger');
                    }
                });
            }
        },

        // Helper API Fetcher wrapping staffFetchJson
        _apiCall: async function(endpoint, method = 'GET', body = null) {
            let sep = endpoint.includes('?') ? '&' : '?';
            let urlWithCompany = endpoint;
            if (this.state.companyId && !endpoint.includes('company_id=')) {
                urlWithCompany = `${endpoint}${sep}company_id=${this.state.companyId}`;
            }

            const options = {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                    'X-Company-ID': String(this.state.companyId || 1)
                }
            };
            if (body && (method === 'POST' || method === 'PUT')) {
                options.body = JSON.stringify(body);
            }

            if (typeof window.staffFetchJson === 'function') {
                return await window.staffFetchJson(API_BASE + urlWithCompany, options);
            } else {
                const token = localStorage.getItem('staff_token') || '';
                options.headers['Authorization'] = `Bearer ${token}`;
                const res = await fetch(API_BASE + urlWithCompany, options);
                if (!res.ok) {
                    const err = await res.json().catch(() => ({ detail: 'API Request failed' }));
                    throw new Error(err.detail || 'Request failed with status ' + res.status);
                }
                return await res.json();
            }
        },

        // ─────────────────────────────────────────────────────────────────────
        // 2. Overview Dashboard
        // ─────────────────────────────────────────────────────────────────────
        loadOverview: async function() {
            try {
                const data = await this._apiCall('/overview');
                if (data.status === 'migration_pending') {
                    this._showMigrationNotice(data.message);
                }
                const counts = data.posts_summary || data.counts || {};
                const engagement = data.engagement_summary || {};

                // Update metric counters
                this._setElText('statConnectedChannels', `${data.connected_accounts_count || data.active_accounts_count || 0} / 4`);
                this._setElText('statActiveCount', data.connected_accounts_count || data.active_accounts_count || 0);
                this._setElText('statTotalPosts', counts.total_planned || counts.total_posts || 0);
                this._setElText('statScheduledPosts', counts.scheduled || 0);
                this._setElText('statPublishedPosts', counts.published || 0);
                this._setElText('statTotalImpressions', engagement.total_impressions || 0);

                // Update provider badge
                const providerBadge = document.getElementById('providerBadge');
                if (providerBadge && data.provider) {
                    providerBadge.innerHTML = `<i class="fas fa-plug-circle-check"></i> Gateway: ${data.provider.toUpperCase()}`;
                }

                // Render upcoming scheduled posts
                this._renderOverviewUpcoming(data.upcoming_posts || []);
            } catch (err) {
                console.error('[SOCIAL-MEDIA] loadOverview error:', err);
                if (err.message && (err.message.includes('500') || err.message.includes('503'))) {
                    this._showMigrationNotice();
                }
            }
        },

        _renderOverviewUpcoming: function(posts) {
            const tbody = document.getElementById('overviewUpcomingPostsBody');
            if (!tbody) return;

            if (!posts || posts.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="5" class="text-center py-4 text-muted">
                            <i class="fas fa-calendar-xmark me-2 text-secondary"></i>
                            No upcoming scheduled posts. Click <strong>AI 30-Day Calendar</strong> to generate.
                        </td>
                    </tr>
                `;
                return;
            }

            tbody.innerHTML = posts.map(p => {
                const schedDate = p.scheduled_at ? new Date(p.scheduled_at).toLocaleString('en-IN', {
                    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
                }) : 'Not Scheduled';

                const statusClass = (p.status || 'DRAFT').toLowerCase();
                const channelsHtml = this._getChannelsHtml(p.dispatches || []);

                return `
                    <tr>
                        <td style="white-space: nowrap;">
                            <div class="fw-bold small">${schedDate}</div>
                            <span class="text-muted" style="font-size: 11px;">Day ${p.day_offset || 1}</span>
                        </td>
                        <td>
                            <div class="fw-bold small text-truncate" style="max-width: 280px;">${this._escapeHtml(p.topic_theme || 'Social Post')}</div>
                            <div class="text-muted text-truncate" style="max-width: 320px; font-size: 11.5px;">${this._escapeHtml(p.master_caption || '')}</div>
                        </td>
                        <td>${channelsHtml}</td>
                        <td><span class="status-badge ${statusClass}">${p.status}</span></td>
                        <td class="text-end">
                            <button class="btn btn-sm btn-outline-primary" style="padding: 3px 8px; font-size: 11.5px;" onclick="SocialMediaManager.openPostEditorById(${p.id})">
                                <i class="fas fa-pen-to-square"></i> Edit
                            </button>
                        </td>
                    </tr>
                `;
            }).join('');
        },

        // ─────────────────────────────────────────────────────────────────────
        // 3. Accounts & Provider Integration
        // ─────────────────────────────────────────────────────────────────────
        loadAccounts: async function() {
            try {
                const data = await this._apiCall('/accounts');
                this.state.accounts = data.accounts || [];
                this._renderAccountsGrid(this.state.accounts);
                this._updateChannelPills(this.state.accounts);
            } catch (err) {
                console.error('[SOCIAL-MEDIA] loadAccounts error:', err);
            }
        },

        _renderAccountsGrid: function(accounts) {
            const grid = document.getElementById('accountsGrid');
            if (!grid) return;

            const platforms = [
                { id: 'facebook', name: 'Facebook Page', icon: 'fab fa-facebook-f', class: 'icon-facebook' },
                { id: 'instagram', name: 'Instagram Business', icon: 'fab fa-instagram', class: 'icon-instagram' },
                { id: 'linkedin', name: 'LinkedIn Company', icon: 'fab fa-linkedin-in', class: 'icon-linkedin' },
                { id: 'x', name: 'X (Twitter)', icon: 'fab fa-x-twitter', class: 'icon-twitter' }
            ];

            grid.innerHTML = platforms.map(p => {
                const conn = accounts.find(a => a.platform === p.id && a.is_active);
                const isConnected = !!conn;

                let actionBtn = '';
                if (isConnected) {
                    actionBtn = `
                        <button class="btn btn-sm btn-outline-danger" onclick="SocialMediaManager.disconnectAccount(${conn.id})">
                            <i class="fas fa-link-slash"></i> Disconnect
                        </button>
                    `;
                } else {
                    actionBtn = `
                        <button class="btn btn-sm btn-outline-primary" onclick="SocialMediaManager.openConnectModal('${p.id}', '${p.name}')">
                            <i class="fas fa-plug"></i> Connect Channel
                        </button>
                    `;
                }

                return `
                    <div class="col-md-6 col-xl-3">
                        <div class="account-card">
                            <div class="d-flex align-items-center gap-3">
                                <div class="account-brand-icon ${p.class}">
                                    <i class="${p.icon}"></i>
                                </div>
                                <div>
                                    <div class="fw-bold small">${p.name}</div>
                                    <div class="small ${isConnected ? 'text-success fw-bold' : 'text-muted'}">
                                        <i class="fas fa-circle" style="font-size: 8px;"></i>
                                        ${isConnected ? (conn.account_handle || 'Connected') : 'Disconnected'}
                                    </div>
                                    ${isConnected && conn.connected_at ? `
                                        <div class="text-muted" style="font-size: 10px;">Since: ${new Date(conn.connected_at).toLocaleDateString()}</div>
                                    ` : ''}
                                </div>
                            </div>
                            <div>${actionBtn}</div>
                        </div>
                    </div>
                `;
            }).join('');
        },

        _updateChannelPills: function(accounts) {
            const map = {
                'facebook': 'pillFacebook',
                'instagram': 'pillInstagram',
                'linkedin': 'pillLinkedin',
                'x': 'pillTwitter'
            };

            for (const [platform, pillId] of Object.entries(map)) {
                const el = document.getElementById(pillId);
                if (el) {
                    const hasActive = accounts.some(a => a.platform === platform && a.is_active);
                    if (hasActive) {
                        el.classList.add('active');
                    } else {
                        el.classList.remove('active');
                    }
                }
            }
        },

        openConnectModal: function(platform, platformName) {
            document.getElementById('connectPlatform').value = platform;
            document.getElementById('connectModalTitle').innerHTML = `<i class="fas fa-plug text-primary me-2"></i> Connect ${platformName}`;
            document.getElementById('mockAccountHandle').value = `@${platform}_${this.state.companyName.toLowerCase().replace(/[^a-z0-9]/g, '')}`;

            const modal = new bootstrap.Modal(document.getElementById('connectAccountModal'));
            modal.show();
        },

        startOAuthConnect: async function() {
            const platform = document.getElementById('connectPlatform').value;
            try {
                const res = await this._apiCall('/accounts/connect-url', 'POST', { platform: platform });
                if (res.auth_url) {
                    window.open(res.auth_url, '_blank', 'width=600,height=700');
                } else {
                    alert('Hosted OAuth link generated: ' + (res.message || 'Authorization ready.'));
                }
            } catch (err) {
                alert('OAuth Initiation Error: ' + err.message);
            }
        },

        submitMockConnect: async function() {
            const platform = document.getElementById('connectPlatform').value;
            const handle = document.getElementById('mockAccountHandle').value || ('@' + platform + '_page');

            try {
                const res = await this._apiCall('/accounts/mock-connect', 'POST', {
                    platform: platform,
                    account_handle: handle
                });

                bootstrap.Modal.getInstance(document.getElementById('connectAccountModal')).hide();
                await this.loadAccounts();
                await this.loadOverview();
                alert(`Channel ${platform.toUpperCase()} connected successfully in Local Sandbox Mode!`);
            } catch (err) {
                alert('Mock Connect Error: ' + err.message);
            }
        },

        disconnectAccount: async function(accountId) {
            if (!confirm('Are you sure you want to disconnect this channel? Scheduled dispatches to this channel will pause.')) {
                return;
            }

            try {
                await this._apiCall(`/accounts/${accountId}`, 'DELETE');
                await this.loadAccounts();
                await this.loadOverview();
            } catch (err) {
                alert('Disconnect Error: ' + err.message);
            }
        },

        // ─────────────────────────────────────────────────────────────────────
        // 4. Content Calendar & AI Generator
        // ─────────────────────────────────────────────────────────────────────
        loadCalendar: async function() {
            const mSelect = document.getElementById('calMonthSelect');
            const ySelect = document.getElementById('calYearSelect');
            if (mSelect) this.state.calendarMonth = parseInt(mSelect.value, 10);
            if (ySelect) this.state.calendarYear = parseInt(ySelect.value, 10);

            try {
                const data = await this._apiCall(`/calendar?month=${this.state.calendarMonth}&year=${this.state.calendarYear}`);
                if (data.status === 'migration_pending') {
                    this._showMigrationNotice(data.message);
                    const grid = document.getElementById('calendarGridContainer');
                    if (grid) {
                        grid.innerHTML = `
                            <div class="col-12 text-center py-5 text-muted" style="grid-column: 1 / -1;">
                                <i class="fas fa-database fa-3x mb-3 text-warning"></i>
                                <h5>Database Initialization Required</h5>
                                <p class="small text-muted mb-3">The social media tables have not been created in the database yet.<br>Run <code>python -m alembic upgrade head</code> to initialize the schema.</p>
                            </div>
                        `;
                    }
                    return;
                }
                this.state.posts = data.posts || [];
                this.renderCalendarGrid();
            } catch (err) {
                console.error('[SOCIAL-MEDIA] loadCalendar error:', err);
                const grid = document.getElementById('calendarGridContainer');
                if (grid) {
                    if (err.message && (err.message.includes('500') || err.message.includes('503'))) {
                        this._showMigrationNotice();
                        grid.innerHTML = `
                            <div class="col-12 text-center py-5 text-muted" style="grid-column: 1 / -1;">
                                <i class="fas fa-database fa-3x mb-3 text-warning"></i>
                                <h5>Database Tables Not Found</h5>
                                <p class="small text-muted mb-3">The target database is missing the social media tables. Run <code>python -m alembic upgrade head</code> to initialize the schema.</p>
                            </div>
                        `;
                    } else {
                        grid.innerHTML = `<div class="col-12 text-center py-4 text-danger">Error loading calendar: ${err.message}</div>`;
                    }
                }
            }
        },

        renderCalendarGrid: function() {
            const grid = document.getElementById('calendarGridContainer');
            if (!grid) return;

            const platformFilter = document.getElementById('calPlatformFilter')?.value || '';
            const statusFilter = document.getElementById('calStatusFilter')?.value || '';

            let filtered = this.state.posts;
            if (statusFilter) {
                filtered = filtered.filter(p => p.status === statusFilter);
            }
            if (platformFilter) {
                filtered = filtered.filter(p => {
                    const dispatches = p.dispatches || [];
                    const caps = p.platform_captions || {};
                    return dispatches.some(d => d.platform === platformFilter) || caps[platformFilter];
                });
            }

            if (!filtered || filtered.length === 0) {
                grid.innerHTML = `
                    <div class="col-12 text-center py-5 text-muted" style="grid-column: 1 / -1;">
                        <i class="fas fa-calendar-xmark fa-3x mb-3 text-secondary"></i>
                        <h5>No Posts Scheduled For This Month</h5>
                        <p class="small text-muted mb-3">Generate a complete 30-day AI calendar with 15 bi-daily strategic posts.</p>
                        <button class="btn btn-brand" onclick="SocialMediaManager.openAIGeneratorModal()">
                            <i class="fas fa-wand-magic-sparkles"></i> Generate AI Calendar
                        </button>
                    </div>
                `;
                return;
            }

            grid.innerHTML = filtered.map(p => {
                const status = (p.status || 'DRAFT').toLowerCase();
                const schedDate = p.scheduled_at ? new Date(p.scheduled_at).toLocaleDateString('en-IN', {
                    day: 'numeric', month: 'short'
                }) : `Day ${p.day_offset || 1}`;

                const hasImg = p.media_urls && p.media_urls.length > 0;
                const thumbImg = hasImg ? `<img src="${p.media_urls[0]}" style="width: 100%; height: 90px; object-fit: cover; border-radius: 8px; margin-bottom: 8px;" alt="media">` : '';

                const channelsHtml = this._getChannelsHtml(p.dispatches || []);

                return `
                    <div class="calendar-day-card status-${status}" onclick="SocialMediaManager.openPostEditorById(${p.id})">
                        <div>
                            <div class="day-header">
                                <span class="day-date"><i class="fas fa-calendar-day me-1"></i> ${schedDate}</span>
                                <span class="status-badge ${status}">${p.status}</span>
                            </div>
                            ${thumbImg}
                            <div class="card-post-title">${this._escapeHtml(p.topic_theme || 'Strategic Post')}</div>
                            <div class="card-post-caption">${this._escapeHtml(p.master_caption || '')}</div>
                        </div>
                        <div class="card-post-footer">
                            <div class="channel-icons">${channelsHtml}</div>
                            <span class="small text-primary fw-bold" style="font-size: 11px;">Edit <i class="fas fa-chevron-right ms-1"></i></span>
                        </div>
                    </div>
                `;
            }).join('');
        },

        openAIGeneratorModal: function() {
            const genM = document.getElementById('genMonth');
            const genY = document.getElementById('genYear');
            if (genM) genM.value = this.state.calendarMonth;
            if (genY) genY.value = this.state.calendarYear;

            const modal = new bootstrap.Modal(document.getElementById('generateCalendarModal'));
            modal.show();
        },

        submitAIGenerateCalendar: async function() {
            const overlay = document.getElementById('aiGenLoading');
            if (overlay) overlay.style.display = 'flex';

            const m = parseInt(document.getElementById('genMonth').value, 10);
            const y = parseInt(document.getElementById('genYear').value, 10);
            const startDateStr = `${y}-${String(m).padStart(2, '0')}-01`;

            const payload = {
                start_date: startDateStr,
                custom_instructions: document.getElementById('genFocus').value.trim()
            };

            try {
                const res = await this._apiCall('/calendar/generate-ai', 'POST', payload);
                if (overlay) overlay.style.display = 'none';

                bootstrap.Modal.getInstance(document.getElementById('generateCalendarModal')).hide();
                await this.loadCalendar();
                await this.loadOverview();
                alert(`Success! Generated ${res.count || 15} strategic posts for ${startDateStr.slice(0,7)}.`);
            } catch (err) {
                if (overlay) overlay.style.display = 'none';
                alert('AI Generation Error: ' + err.message);
            }
        },

        // ─────────────────────────────────────────────────────────────────────
        // 5. Post Editor & Platform Customization
        // ─────────────────────────────────────────────────────────────────────
        openPostEditorById: async function(postId) {
            try {
                const data = await this._apiCall(`/posts/${postId}`);
                this.openPostEditor(data.post);
            } catch (err) {
                alert('Could not load post details: ' + err.message);
            }
        },

        openPostEditor: function(post = null) {
            this.state.activeEditingPost = post;

            const titleEl = document.getElementById('postEditorTitle');
            const idInput = document.getElementById('editPostId');
            const delBtn = document.getElementById('btnDeletePost');

            if (post) {
                titleEl.innerHTML = `<i class="fas fa-edit text-primary me-2"></i> Edit Post #${post.id}`;
                idInput.value = post.id;
                delBtn.style.display = 'inline-block';

                document.getElementById('editTitle').value = post.topic_theme || '';
                document.getElementById('editStatus').value = post.status || 'DRAFT';
                
                // Format datetime-local string
                if (post.scheduled_at) {
                    const d = new Date(post.scheduled_at);
                    const pad = num => String(num).padStart(2, '0');
                    const localIso = `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
                    document.getElementById('editScheduledAt').value = localIso;
                } else {
                    document.getElementById('editScheduledAt').value = '';
                }

                // Captions
                document.getElementById('editCaptionBase').value = post.master_caption || '';
                const caps = post.platform_captions || {};
                document.getElementById('editCaptionFB').value = caps.facebook || '';
                document.getElementById('editCaptionIG').value = caps.instagram || '';
                document.getElementById('editCaptionLI').value = caps.linkedin || '';
                document.getElementById('editCaptionX').value = caps.x || '';
                document.getElementById('charCountX').innerText = (caps.x || '').length;

                // Channels checkboxes
                const dispatches = post.dispatches || [];
                const hasFB = dispatches.some(d => d.platform === 'facebook') || caps.facebook;
                const hasIG = dispatches.some(d => d.platform === 'instagram') || caps.instagram;
                const hasLI = dispatches.some(d => d.platform === 'linkedin') || caps.linkedin;
                const hasX = dispatches.some(d => d.platform === 'x') || caps.x;

                document.getElementById('editChanFB').checked = Boolean(hasFB);
                document.getElementById('editChanIG').checked = Boolean(hasIG);
                document.getElementById('editChanLI').checked = Boolean(hasLI);
                document.getElementById('editChanX').checked = Boolean(hasX);

                // Media URL & preview
                const mediaUrl = (post.media_urls && post.media_urls.length > 0) ? post.media_urls[0] : '';
                document.getElementById('editMediaUrl').value = mediaUrl;
                this._setMediaPreview(mediaUrl);

            } else {
                titleEl.innerHTML = `<i class="fas fa-plus text-success me-2"></i> New Ad-hoc Social Post`;
                idInput.value = '';
                delBtn.style.display = 'none';

                document.getElementById('editTitle').value = '';
                document.getElementById('editStatus').value = 'DRAFT';

                const now = new Date();
                now.setHours(now.getHours() + 2);
                const pad = num => String(num).padStart(2, '0');
                document.getElementById('editScheduledAt').value = `${now.getFullYear()}-${pad(now.getMonth()+1)}-${pad(now.getDate())}T${pad(now.getHours())}:00`;

                document.getElementById('editCaptionBase').value = '';
                document.getElementById('editCaptionFB').value = '';
                document.getElementById('editCaptionIG').value = '';
                document.getElementById('editCaptionLI').value = '';
                document.getElementById('editCaptionX').value = '';
                document.getElementById('charCountX').innerText = '0';

                document.getElementById('editChanFB').checked = true;
                document.getElementById('editChanIG').checked = true;
                document.getElementById('editChanLI').checked = true;
                document.getElementById('editChanX').checked = true;

                document.getElementById('editMediaUrl').value = '';
                this._setMediaPreview('');
            }

            const modal = new bootstrap.Modal(document.getElementById('postEditorModal'));
            modal.show();
        },

        _setMediaPreview: function(url) {
            const img = document.getElementById('editMediaImg');
            const placeholder = document.getElementById('mediaPlaceholderText');
            if (url && url.trim().length > 0) {
                img.src = url.trim();
                img.style.display = 'block';
                if (placeholder) placeholder.style.display = 'none';
            } else {
                img.src = '';
                img.style.display = 'none';
                if (placeholder) placeholder.style.display = 'block';
            }
        },

        updateMediaPreviewFromInput: function() {
            const url = document.getElementById('editMediaUrl').value;
            this._setMediaPreview(url);
        },

        removeMedia: function() {
            document.getElementById('editMediaUrl').value = '';
            this._setMediaPreview('');
        },

        savePost: async function(shouldApprove = false) {
            const postId = document.getElementById('editPostId').value;
            const title = document.getElementById('editTitle').value.trim();
            const sched = document.getElementById('editScheduledAt').value;
            const baseCaption = document.getElementById('editCaptionBase').value.trim();

            if (!title) { alert('Please enter a post title.'); return; }
            if (!sched) { alert('Please select a scheduled date and time.'); return; }
            if (!baseCaption) { alert('Please enter base caption text.'); return; }

            const mediaUrl = document.getElementById('editMediaUrl').value.trim();
            const mediaUrls = mediaUrl ? [mediaUrl] : [];

            const platformCaptions = {};
            const capFB = document.getElementById('editCaptionFB').value.trim();
            const capIG = document.getElementById('editCaptionIG').value.trim();
            const capLI = document.getElementById('editCaptionLI').value.trim();
            const capX = document.getElementById('editCaptionX').value.trim();

            if (capFB) platformCaptions.facebook = capFB;
            if (capIG) platformCaptions.instagram = capIG;
            if (capLI) platformCaptions.linkedin = capLI;
            if (capX) platformCaptions.x = capX;

            const payload = {
                topic_theme: title,
                master_caption: baseCaption,
                scheduled_at: new Date(sched).toISOString(),
                media_urls: mediaUrls,
                media_type: mediaUrls.length > 0 ? 'image' : null,
                platform_captions: platformCaptions
            };

            const overlay = document.getElementById('postEditorLoading');
            if (overlay) overlay.style.display = 'flex';

            try {
                let savedId = postId;
                if (postId) {
                    await this._apiCall(`/posts/${postId}`, 'PUT', payload);
                } else {
                    const res = await this._apiCall('/posts', 'POST', payload);
                    savedId = res.post?.id;
                }

                if (shouldApprove && savedId) {
                    await this._apiCall(`/posts/${savedId}/approve`, 'POST');
                }

                if (overlay) overlay.style.display = 'none';
                bootstrap.Modal.getInstance(document.getElementById('postEditorModal')).hide();
                await this.loadCalendar();
                await this.loadOverview();
            } catch (err) {
                if (overlay) overlay.style.display = 'none';
                alert('Save Post Error: ' + err.message);
            }
        },

        approveAndSchedulePost: async function() {
            await this.savePost(true);
        },

        publishPostNow: async function() {
            const postId = document.getElementById('editPostId').value;
            if (!postId) {
                alert('Please save the post first before publishing.');
                return;
            }

            if (!confirm('Are you sure you want to publish this post immediately across all connected channels?')) {
                return;
            }

            const overlay = document.getElementById('postEditorLoading');
            const overlayText = document.getElementById('postEditorLoadingText');
            if (overlay) {
                overlayText.innerText = 'Publishing to active channels...';
                overlay.style.display = 'flex';
            }

            try {
                // Save latest edits first
                await this.savePost(false);
                const res = await this._apiCall(`/posts/${postId}/publish-now`, 'POST');
                if (overlay) overlay.style.display = 'none';

                bootstrap.Modal.getInstance(document.getElementById('postEditorModal')).hide();
                await this.loadCalendar();
                await this.loadOverview();
                alert(`Publication dispatches triggered! Success: ${res.successful_channels?.length || 0} channels.`);
            } catch (err) {
                if (overlay) overlay.style.display = 'none';
                alert('Publish Now Error: ' + err.message);
            }
        },

        deletePost: async function() {
            const postId = document.getElementById('editPostId').value;
            if (!postId) return;

            if (!confirm('Are you sure you want to permanently delete this post and cancel its schedule?')) {
                return;
            }

            try {
                await this._apiCall(`/posts/${postId}`, 'DELETE');
                bootstrap.Modal.getInstance(document.getElementById('postEditorModal')).hide();
                await this.loadCalendar();
                await this.loadOverview();
            } catch (err) {
                alert('Delete Error: ' + err.message);
            }
        },

        generatePostImage: async function() {
            const postId = document.getElementById('editPostId').value;
            if (!postId) {
                alert('Please save draft post first before generating AI image.');
                return;
            }

            const overlay = document.getElementById('postEditorLoading');
            const overlayText = document.getElementById('postEditorLoadingText');
            if (overlay) {
                overlayText.innerText = 'Generating high-resolution AI visual...';
                overlay.style.display = 'flex';
            }

            try {
                const res = await this._apiCall(`/posts/${postId}/generate-image`, 'POST');
                if (overlay) overlay.style.display = 'none';

                if (res.image_url) {
                    document.getElementById('editMediaUrl').value = res.image_url;
                    this._setMediaPreview(res.image_url);
                }
            } catch (err) {
                if (overlay) overlay.style.display = 'none';
                alert('AI Image Generation: ' + err.message);
            }
        },

        regeneratePostCaption: async function() {
            const postId = document.getElementById('editPostId').value;
            if (!postId) {
                alert('Please save draft post first before regenerating copy.');
                return;
            }

            const overlay = document.getElementById('postEditorLoading');
            const overlayText = document.getElementById('postEditorLoadingText');
            if (overlay) {
                overlayText.innerText = 'Re-crafting multi-platform copy...';
                overlay.style.display = 'flex';
            }

            try {
                const res = await this._apiCall(`/posts/${postId}/regenerate-caption`, 'POST');
                if (overlay) overlay.style.display = 'none';

                const post = res.post;
                if (post) {
                    document.getElementById('editCaptionBase').value = post.master_caption || '';
                    const caps = post.platform_captions || {};
                    document.getElementById('editCaptionFB').value = caps.facebook || '';
                    document.getElementById('editCaptionIG').value = caps.instagram || '';
                    document.getElementById('editCaptionLI').value = caps.linkedin || '';
                    document.getElementById('editCaptionX').value = caps.x || '';
                    document.getElementById('charCountX').innerText = (caps.x || '').length;
                }
            } catch (err) {
                if (overlay) overlay.style.display = 'none';
                alert('Copy Regeneration Error: ' + err.message);
            }
        },

        // ─────────────────────────────────────────────────────────────────────
        // 6. Analytics & Performance
        // ─────────────────────────────────────────────────────────────────────
        loadAnalytics: async function(refresh = false) {
            try {
                const daysSelect = document.getElementById('analyticsDaysFilter');
                const days = daysSelect ? daysSelect.value : 30;
                const url = refresh ? `/analytics?days=${days}&refresh=true` : `/analytics?days=${days}`;
                const data = await this._apiCall(url);
                if (data.status === 'migration_pending') {
                    this._showMigrationNotice(data.message);
                }
                this.state.analytics = data;

                const totals = data.aggregate_metrics || {};
                this._setElText('anTotalViews', totals.views || 0);
                this._setElText('anTotalImpressions', totals.impressions || 0);
                this._setElText('statTotalImpressions', totals.impressions || 0);
                this._setElText('anTotalReach', totals.reach || 0);
                this._setElText('anTotalLikes', totals.likes || 0);
                this._setElText('anTotalComments', totals.comments || 0);
                this._setElText('anAvgEngagement', (totals.engagement_rate || 0).toFixed(1) + '%');

                this._renderAnalyticsTable(data.recent_published_posts || data.post_metrics || []);
            } catch (err) {
                console.error('[SOCIAL-MEDIA] loadAnalytics error:', err);
                if (err.message && (err.message.includes('500') || err.message.includes('503'))) {
                    this._showMigrationNotice();
                }
            }
        },

        syncAnalyticsNow: async function() {
            await this.loadAnalytics(true);
            alert('Analytics sync requested! Real-time metrics updated.');
        },

        _formatMetric: function(val, availability) {
            if (val !== null && val !== undefined) {
                return Number(val).toLocaleString();
            }
            if (availability === 'PENDING_PLATFORM_DATA' || availability === 'PENDING') {
                return '<span class="text-muted fst-italic" style="font-size: 11px;">(Pending)</span>';
            }
            if (availability === 'UNSUPPORTED') {
                return '<span class="text-muted" style="font-size: 11px;">N/A</span>';
            }
            return '<span class="text-muted">—</span>';
        },

        _renderAnalyticsTable: function(items) {
            const tbody = document.getElementById('analyticsTableBody');
            if (!tbody) return;

            if (!items || items.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="10" class="text-center py-4 text-muted">
                            No published post metrics recorded yet. Metrics sync automatically every 6 hours.
                        </td>
                    </tr>
                `;
                return;
            }

            tbody.innerHTML = items.map(item => {
                const pubDate = item.published_at ? new Date(item.published_at).toLocaleDateString() : '—';
                const channelsHtml = (item.platforms || (item.platform ? [item.platform] : [])).map(p => {
                    const icon = p === 'facebook' ? 'fa-facebook text-primary' :
                                 p === 'instagram' ? 'fa-instagram text-danger' :
                                 p === 'linkedin' ? 'fa-linkedin text-info' : 'fa-x-twitter';
                    return `<i class="fab ${icon} me-1"></i>`;
                }).join('');

                const m = item.metrics || item;
                const availability = m.data_availability || (m.impressions !== null || m.likes !== null ? 'AVAILABLE' : 'PENDING_PLATFORM_DATA');
                const sourceBadge = availability === 'AVAILABLE'
                    ? `<span class="badge bg-success-subtle text-success border border-success-subtle">Real-time Verified</span>`
                    : availability === 'ZERO_METRICS'
                    ? `<span class="badge bg-info-subtle text-info border border-info-subtle">0 Verified</span>`
                    : availability === 'UNSUPPORTED'
                    ? `<span class="badge bg-secondary-subtle text-secondary border">Platform Unsupported</span>`
                    : `<span class="badge bg-warning-subtle text-warning border border-warning-subtle">Pending Sync</span>`;

                const impr = m.impressions !== undefined ? m.impressions : null;
                const reach = m.reach !== undefined ? m.reach : null;
                const likes = m.likes !== undefined ? m.likes : null;
                const comments = m.comments !== undefined ? m.comments : null;
                const engRate = m.engagement_rate !== undefined ? m.engagement_rate : null;

                return `
                    <tr>
                        <td class="small fw-bold">${pubDate}</td>
                        <td class="small text-truncate" style="max-width: 200px;">${this._escapeHtml(item.topic_theme || 'Post #' + (item.post_id || item.dispatch_id))}</td>
                        <td>${channelsHtml}</td>
                        <td class="fw-bold">${this._formatMetric(m.video_views || m.views, availability)}</td>
                        <td>${this._formatMetric(impr, availability)}</td>
                        <td>${this._formatMetric(reach, availability)}</td>
                        <td class="text-danger fw-bold">${this._formatMetric(likes, availability)}</td>
                        <td class="text-info fw-bold">${this._formatMetric(comments, availability)}</td>
                        <td class="text-warning fw-bold">${engRate !== null && engRate !== undefined ? engRate.toFixed(1) + '%' : '—'}</td>
                        <td>${sourceBadge}</td>
                    </tr>
                `;
            }).join('');
        },

        // ─────────────────────────────────────────────────────────────────────
        // 7. Preferences & Settings
        // ─────────────────────────────────────────────────────────────────────
        loadSettings: async function() {
            try {
                const data = await this._apiCall('/settings');
                if (data.status === 'migration_pending') {
                    this._showMigrationNotice(data.message);
                }
                const s = data.settings || {};
                this.state.settings = s;

                const time1 = document.getElementById('prefTime1');
                if (time1) time1.value = s.preferred_time_ist || '10:00';

                const voice = document.getElementById('prefBrandVoice');
                if (voice) voice.value = s.brand_voice || '';

                const tags = document.getElementById('prefDefaultHashtags');
                if (tags) tags.value = (s.default_hashtags || []).join(' ');

                const autoApprove = document.getElementById('prefAutoApprove');
                if (autoApprove && s.require_admin_approval !== undefined) {
                    autoApprove.checked = !s.require_admin_approval;
                }
            } catch (err) {
                console.warn('[SOCIAL-MEDIA] loadSettings error:', err);
                if (err.message && (err.message.includes('500') || err.message.includes('503'))) {
                    this._showMigrationNotice();
                }
            }
        },

        saveSettings: async function() {
            const time1 = document.getElementById('prefTime1').value;
            const brandVoice = document.getElementById('prefBrandVoice').value.trim();
            const tagsRaw = document.getElementById('prefDefaultHashtags').value.trim();
            const autoApprove = document.getElementById('prefAutoApprove').checked;

            const tagsList = tagsRaw.split(/[\s,]+/).filter(t => t.startsWith('#') || t.length > 0).map(t => t.startsWith('#') ? t : '#' + t);

            const payload = {
                preferred_time_ist: time1 || '10:30',
                brand_voice: brandVoice,
                default_hashtags: tagsList,
                require_admin_approval: !autoApprove
            };

            try {
                await this._apiCall('/settings', 'PUT', payload);
                alert('Calendar schedule settings updated successfully!');
            } catch (err) {
                alert('Save Settings Error: ' + err.message);
            }
        },

        // ─────────────────────────────────────────────────────────────────────
        // 8. Navigation & Tab Switch Utilities
        // ─────────────────────────────────────────────────────────────────────
        switchToCalendarTab: function() {
            const tabBtn = document.querySelector('button[data-bs-target="#tabCalendar"]');
            if (tabBtn) tabBtn.click();
        },

        switchToAccountsTab: function() {
            const tabBtn = document.querySelector('button[data-bs-target="#tabAccounts"]');
            if (tabBtn) tabBtn.click();
        },

        // Helper rendering utilities
        _setElText: function(id, text) {
            const el = document.getElementById(id);
            if (el) el.innerText = text;
        },

        _escapeHtml: function(str) {
            if (!str) return '';
            return str.replace(/&/g, '&amp;')
                      .replace(/</g, '&lt;')
                      .replace(/>/g, '&gt;')
                      .replace(/"/g, '&quot;')
                      .replace(/'/g, '&#039;');
        },

        _getChannelsHtml: function(dispatches) {
            const platforms = dispatches.map(d => d.platform) || [];
            if (platforms.length === 0) {
                return `<i class="fab fa-facebook me-1"></i><i class="fab fa-instagram me-1"></i><i class="fab fa-linkedin me-1"></i><i class="fab fa-x-twitter"></i>`;
            }
            return platforms.map(p => {
                if (p === 'facebook') return `<i class="fab fa-facebook text-primary me-1" title="Facebook"></i>`;
                if (p === 'instagram') return `<i class="fab fa-instagram text-danger me-1" title="Instagram"></i>`;
                if (p === 'linkedin') return `<i class="fab fa-linkedin text-info me-1" title="LinkedIn"></i>`;
                if (p === 'x') return `<i class="fab fa-x-twitter text-dark me-1" title="X"></i>`;
                return '';
            }).join('');
        }
    };

    window.SocialMediaManager = SocialMediaManager;
})();
