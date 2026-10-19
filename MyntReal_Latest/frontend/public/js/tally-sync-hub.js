/**
 * MyntOS End-to-End Tally Integration Hub (DC_TALLY_SYNC_001)
 * ============================================================
 * Provides a unified One-Click Tally XML Download & Daybook Upload Reconciliation Modal
 * across Purchase Orders, Purchase Invoices, Sales Invoices, Cash/Income/Expense Entries,
 * Journal Vouchers, and Ledgers (Masters + Transactions).
 *
 * Features:
 *  - Selectable Tally Version: TallyPrime (3.0/4.0+), TallyPrime (1.x/2.x), Tally.ERP 9, Universal
 *  - Period Presets (Today, This Week, This Month, Last Month, This Quarter, This FY, All Time) + Custom Date Range
 *  - Segment-wise Filtering (Company Segments) + Multi-Module Selection
 *  - Exact MyntOS Voucher / Invoice Number preservation in Tally (<VOUCHERNUMBER> & <REFERENCE>)
 *  - WVV Hash Change Detection (automatically highlights records modified after previous export)
 *  - Bi-Directional Tally Daybook XML / CSV Upload & Auto-Reconciliation
 */
(function () {
    if (typeof window === 'undefined' || typeof document === 'undefined') return;
    if (window.__MYNTOS_TALLY_HUB_INITIALIZED__) return;
    window.__MYNTOS_TALLY_HUB_INITIALIZED__ = true;

    const API_BASE = '/api/v1/staff/accounts';

    let _hubState = {
        companyId: null,
        defaultModule: null,
        activeTab: 'export', // 'export' | 'import' | 'batches'
        summaryData: null,
        selectedVouchers: new Set(),
        loading: false,
    };

    function _getCookieToken() {
        try {
            const m = document.cookie.match(/(?:^|;\s*)staff_token=([^;]+)/);
            return m ? decodeURIComponent(m[1]) : '';
        } catch (_) {
            return '';
        }
    }

    function _getAuthHeaders() {
        const token =
            localStorage.getItem('staff_token') ||
            localStorage.getItem('auth_token') ||
            localStorage.getItem('token') ||
            sessionStorage.getItem('staff_token') ||
            sessionStorage.getItem('auth_token') ||
            _getCookieToken() ||
            '';
        return token ? { Authorization: `Bearer ${token}` } : {};
    }

    async function _apiFetch(url, options = {}) {
        if (typeof window.staffFetch === 'function') {
            return window.staffFetch(url, options);
        }
        const headers = Object.assign({}, _getAuthHeaders(), options.headers || {});
        return fetch(url, Object.assign({}, options, { headers, credentials: 'same-origin' }));
    }

    function _detectPageCompanyId() {
        const selectors = [
            '#companySelect',
            '#filterCompany',
            '#companyFilter',
            '#company_id',
            '#selCompany',
            'select[name="company_id"]',
        ];
        for (const sel of selectors) {
            const el = document.querySelector(sel);
            if (el && el.value && el.value !== '0' && el.value !== 'all' && !isNaN(parseInt(el.value, 10))) {
                return parseInt(el.value, 10);
            }
        }
        if (typeof window.selectedCompanyId !== 'undefined' && window.selectedCompanyId) {
            return parseInt(window.selectedCompanyId, 10);
        }
        return null;
    }

    function _detectDefaultModule() {
        const path = (window.location.pathname || '').toLowerCase();
        if (path.includes('ledger_masters') || path.includes('ledger-masters')) return 'MASTERS';
        if (path.includes('procurement')) return 'PURCHASE_ORDERS';
        if (path.includes('purchase_invoices') || path.includes('purchase-invoices')) return 'PURCHASE_INVOICES';
        if (path.includes('sales_invoices') || path.includes('sales-invoices')) return 'SALES_INVOICES';
        if (
            path.includes('cash_in_hand') ||
            path.includes('cash-in-hand') ||
            path.includes('income_entries') ||
            path.includes('income-entries') ||
            path.includes('expense_entries') ||
            path.includes('expense-entries')
        ) {
            return 'CASH_ENTRIES';
        }
        if (
            path.includes('journal_voucher') ||
            path.includes('journal-voucher') ||
            path.includes('general_ledger') ||
            path.includes('general-ledger') ||
            path.includes('party_ledger') ||
            path.includes('party-ledger')
        ) {
            return 'LEDGERS_JV';
        }
        return 'ALL';
    }

    function _injectStyles() {
        if (document.getElementById('myntos-tally-hub-styles')) return;
        const style = document.createElement('style');
        style.id = 'myntos-tally-hub-styles';
        style.textContent = `
            .tally-hub-btn {
                background: linear-gradient(135deg, #0f766e 0%, #0d9488 100%);
                color: #ffffff !important;
                border: none;
                padding: 8px 15px;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 600;
                cursor: pointer;
                display: inline-flex;
                align-items: center;
                gap: 7px;
                box-shadow: 0 2px 8px rgba(13, 148, 136, 0.28);
                transition: all 0.18s ease;
                text-decoration: none;
                white-space: nowrap;
            }
            .tally-hub-btn:hover {
                transform: translateY(-1px);
                box-shadow: 0 4px 12px rgba(13, 148, 136, 0.38);
                filter: brightness(1.05);
            }
            .tally-hub-overlay {
                position: fixed;
                inset: 0;
                background: rgba(15, 23, 42, 0.65);
                backdrop-filter: blur(3px);
                z-index: 99999;
                display: none;
                align-items: center;
                justify-content: center;
                padding: 16px;
            }
            .tally-hub-overlay.active {
                display: flex;
            }
            .tally-hub-modal {
                background: #ffffff;
                width: 100%;
                max-width: 1060px;
                max-height: 92vh;
                border-radius: 14px;
                box-shadow: 0 24px 48px rgba(0, 0, 0, 0.25);
                display: flex;
                flex-direction: column;
                overflow: hidden;
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
                color: #1e293b;
            }
            .tally-hub-header {
                background: linear-gradient(135deg, #0f172a 0%, #134e4a 100%);
                color: #fff;
                padding: 16px 22px;
                display: flex;
                align-items: center;
                justify-content: space-between;
            }
            .tally-hub-header h3 {
                margin: 0;
                font-size: 17px;
                font-weight: 700;
                display: flex;
                align-items: center;
                gap: 10px;
                color: #fff;
            }
            .tally-hub-sub {
                font-size: 12px;
                color: #99f6e4;
                margin-top: 2px;
            }
            .tally-hub-close {
                background: rgba(255,255,255,0.12);
                border: none;
                color: #fff;
                width: 32px;
                height: 32px;
                border-radius: 8px;
                font-size: 18px;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .tally-hub-tabs {
                display: flex;
                gap: 4px;
                padding: 10px 22px 0;
                background: #f8fafc;
                border-bottom: 1px solid #e2e8f0;
            }
            .tally-hub-tab {
                padding: 9px 16px;
                font-size: 13px;
                font-weight: 600;
                color: #64748b;
                background: transparent;
                border: none;
                border-bottom: 2px solid transparent;
                cursor: pointer;
                display: inline-flex;
                align-items: center;
                gap: 7px;
            }
            .tally-hub-tab.active {
                color: #0f766e;
                border-bottom-color: #0f766e;
                background: #ffffff;
                border-radius: 8px 8px 0 0;
            }
            .tally-hub-body {
                padding: 18px 22px;
                overflow-y: auto;
                flex: 1;
            }
            .tally-hub-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
                gap: 12px;
                margin-bottom: 14px;
                background: #f8fafc;
                padding: 14px;
                border-radius: 10px;
                border: 1px solid #e2e8f0;
            }
            .tally-hub-field label {
                display: block;
                font-size: 11px;
                font-weight: 700;
                text-transform: uppercase;
                color: #475569;
                margin-bottom: 5px;
                letter-spacing: 0.03em;
            }
            .tally-hub-field select,
            .tally-hub-field input[type="date"],
            .tally-hub-field input[type="text"] {
                width: 100%;
                padding: 8px 10px;
                border: 1px solid #cbd5e1;
                border-radius: 7px;
                font-size: 13px;
                background: #fff;
                color: #0f172a;
            }
            .tally-mod-chips {
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
                margin-bottom: 14px;
            }
            .tally-mod-chip {
                display: inline-flex;
                align-items: center;
                gap: 6px;
                padding: 6px 12px;
                border-radius: 20px;
                border: 1px solid #cbd5e1;
                background: #fff;
                font-size: 12px;
                font-weight: 600;
                color: #334155;
                cursor: pointer;
                user-select: none;
            }
            .tally-mod-chip input {
                accent-color: #0f766e;
                margin: 0;
            }
            .tally-kpi-row {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                gap: 10px;
                margin-bottom: 14px;
            }
            .tally-kpi-card {
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 10px;
                padding: 10px 13px;
            }
            .tally-kpi-card .k-title {
                font-size: 11px;
                font-weight: 600;
                color: #64748b;
                text-transform: uppercase;
            }
            .tally-kpi-card .k-val {
                font-size: 18px;
                font-weight: 700;
                color: #0f172a;
                margin-top: 2px;
            }
            .tally-kpi-card .k-sub {
                font-size: 11px;
                color: #0f766e;
                margin-top: 2px;
            }
            .tally-table-wrap {
                border: 1px solid #e2e8f0;
                border-radius: 10px;
                overflow: hidden;
                max-height: 290px;
                overflow-y: auto;
            }
            .tally-table {
                width: 100%;
                border-collapse: collapse;
                font-size: 12px;
            }
            .tally-table th {
                position: sticky;
                top: 0;
                background: #f1f5f9;
                color: #475569;
                font-weight: 700;
                text-transform: uppercase;
                font-size: 10.5px;
                padding: 9px 10px;
                text-align: left;
                border-bottom: 1px solid #cbd5e1;
                z-index: 1;
            }
            .tally-table td {
                padding: 8px 10px;
                border-bottom: 1px solid #f1f5f9;
                color: #1e293b;
            }
            .tally-badge {
                display: inline-block;
                padding: 2px 8px;
                border-radius: 12px;
                font-size: 10px;
                font-weight: 700;
            }
            .tally-badge.NOT_SYNCED { background: #fef3c7; color: #b45309; }
            .tally-badge.EXPORTED { background: #e0f2fe; color: #0369a1; }
            .tally-badge.SYNCED { background: #d1fae5; color: #047857; }
            .tally-badge.MODIFIED_PENDING_SYNC { background: #fae8ff; color: #a21caf; }
            .tally-badge.CANCELLED_PENDING_SYNC { background: #ffedd5; color: #c2410c; }
            .tally-badge.CANCELLED_EXPORTED { background: #e2e8f0; color: #475569; }
            .tally-badge.CANCELLED_SYNCED { background: #cbd5e1; color: #334155; }
            .tally-badge.AMBIGUOUS { background: #fef08a; color: #854d0e; }
            .tally-badge.MISMATCH { background: #fee2e2; color: #b91c1c; }
            .tally-badge.EXCLUDED { background: #f1f5f9; color: #64748b; }
            .tally-hub-footer {
                padding: 13px 22px;
                background: #f8fafc;
                border-top: 1px solid #e2e8f0;
                display: flex;
                align-items: center;
                justify-content: space-between;
                flex-wrap: wrap;
                gap: 10px;
            }
            .tally-btn-primary {
                background: linear-gradient(135deg, #0f766e 0%, #0d9488 100%);
                color: #fff;
                border: none;
                padding: 9px 18px;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 600;
                cursor: pointer;
                display: inline-flex;
                align-items: center;
                gap: 7px;
            }
            .tally-btn-secondary {
                background: #fff;
                color: #334155;
                border: 1px solid #cbd5e1;
                padding: 8px 14px;
                border-radius: 8px;
                font-size: 12.5px;
                font-weight: 600;
                cursor: pointer;
                display: inline-flex;
                align-items: center;
                gap: 6px;
            }
        `;
        document.head.appendChild(style);
    }

    function _ensureModalDOM() {
        _injectStyles();
        let overlay = document.getElementById('myntosTallyHubOverlay');
        if (overlay) return overlay;

        overlay = document.createElement('div');
        overlay.id = 'myntosTallyHubOverlay';
        overlay.className = 'tally-hub-overlay';
        overlay.innerHTML = `
            <div class="tally-hub-modal" onclick="event.stopPropagation()">
                <div class="tally-hub-header">
                    <div>
                        <h3><i class="fas fa-sync-alt"></i> TallyPrime & Tally.ERP 9 Integration Hub</h3>
                        <div class="tally-hub-sub">
                            One-Click Tally XML Download & Daybook Reconciliation • Same MyntOS Voucher Numbers • WVV Verified (Dr = Cr)
                        </div>
                    </div>
                    <button class="tally-hub-close" onclick="window.closeMyntosTallyHub()" title="Close">&times;</button>
                </div>

                <div class="tally-hub-tabs">
                    <button class="tally-hub-tab active" id="thTabBtnExport" onclick="window.switchTallyHubTab('export')">
                        <i class="fas fa-file-download"></i> 1. Download Tally XML (Masters + Vouchers)
                    </button>
                    <button class="tally-hub-tab" id="thTabBtnImport" onclick="window.switchTallyHubTab('import')">
                        <i class="fas fa-file-upload"></i> 2. Upload Tally Daybook / Reconcile
                    </button>
                    <button class="tally-hub-tab" id="thTabBtnBatches" onclick="window.switchTallyHubTab('batches')">
                        <i class="fas fa-history"></i> 3. Sync & WVV Audit History
                    </button>
                </div>

                <div class="tally-hub-body" id="thModalBody">
                    <!-- Export Tab -->
                    <div id="thPaneExport">
                        <div class="tally-hub-grid">
                            <div class="tally-hub-field">
                                <label><i class="fas fa-building"></i> Company</label>
                                <select id="thCompanySelect" onchange="window.onTallyHubCompanyChange()"></select>
                            </div>
                            <div class="tally-hub-field">
                                <label><i class="fas fa-layer-group"></i> Segment Filter</label>
                                <select id="thSegmentSelect" onchange="window.refreshTallyHubSummary()">
                                    <option value="">All Segments (Consolidated)</option>
                                </select>
                            </div>
                            <div class="tally-hub-field">
                                <label><i class="fas fa-code-branch"></i> Tally Version</label>
                                <select id="thVersionSelect">
                                    <option value="TALLY_PRIME_4">TallyPrime (Release 3.0 / 4.0+ — Latest GST)</option>
                                    <option value="TALLY_PRIME_2">TallyPrime (Release 1.x / 2.x)</option>
                                    <option value="TALLY_ERP9">Tally.ERP 9 (Series A Release 6.x GST)</option>
                                    <option value="UNIVERSAL">Universal Compatible (TallyPrime + ERP 9)</option>
                                </select>
                            </div>
                            <div class="tally-hub-field">
                                <label><i class="fas fa-calendar-alt"></i> Period</label>
                                <select id="thPeriodSelect" onchange="window.onTallyHubPeriodChange()">
                                    <option value="TODAY">Today</option>
                                    <option value="YESTERDAY">Yesterday</option>
                                    <option value="THIS_WEEK">This Week</option>
                                    <option value="THIS_MONTH" selected>This Month</option>
                                    <option value="LAST_MONTH">Last Month</option>
                                    <option value="THIS_QUARTER">This Quarter</option>
                                    <option value="THIS_FY">This Financial Year (Apr–Mar)</option>
                                    <option value="LAST_FY">Previous Financial Year</option>
                                    <option value="ALL_TIME">All Time</option>
                                    <option value="CUSTOM">Custom Date Range</option>
                                </select>
                            </div>
                            <div class="tally-hub-field" id="thCustomDateFromWrap" style="display:none;">
                                <label>From Date</label>
                                <input type="date" id="thDateFrom" onchange="window.refreshTallyHubSummary()">
                            </div>
                            <div class="tally-hub-field" id="thCustomDateToWrap" style="display:none;">
                                <label>To Date</label>
                                <input type="date" id="thDateTo" onchange="window.refreshTallyHubSummary()">
                            </div>
                            <div class="tally-hub-field">
                                <label><i class="fas fa-file-invoice"></i> Voucher Mode</label>
                                <select id="thVoucherModeSelect">
                                    <option value="AUTO" selected>Auto (Item Invoice + Accounting Fallback)</option>
                                    <option value="ACCOUNTING_INVOICE">Accounting Voucher Only (Ledger-wise)</option>
                                </select>
                            </div>
                            <div class="tally-hub-field">
                                <label><i class="fas fa-filter"></i> Sync Status Filter</label>
                                <select id="thSyncStatusSelect" onchange="window.refreshTallyHubSummary()">
                                    <option value="ALL" selected>All Confirmed/Approved Records</option>
                                    <option value="UNSYNCED_OR_MODIFIED">Unsynced & Modified Only (Updates)</option>
                                    <option value="MODIFIED_ONLY">Modified After Sync Only</option>
                                    <option value="SYNCED_ONLY">Already Synced / Exported Only</option>
                                </select>
                            </div>
                        </div>

                        <div style="margin-bottom:8px;font-size:11px;font-weight:700;text-transform:uppercase;color:#475569;">
                            Modules Included in Export:
                        </div>
                        <div class="tally-mod-chips">
                            <label class="tally-mod-chip"><input type="checkbox" class="th-mod-chk" value="MASTERS" checked onchange="window.refreshTallyHubSummary()"> Masters (Ledgers, Parties, Stock, HSN)</label>
                            <label class="tally-mod-chip"><input type="checkbox" class="th-mod-chk" value="PURCHASE_ORDERS" checked onchange="window.refreshTallyHubSummary()"> Purchase Orders</label>
                            <label class="tally-mod-chip"><input type="checkbox" class="th-mod-chk" value="PURCHASE_INVOICES" checked onchange="window.refreshTallyHubSummary()"> Purchase Invoices</label>
                            <label class="tally-mod-chip"><input type="checkbox" class="th-mod-chk" value="SALES_INVOICES" checked onchange="window.refreshTallyHubSummary()"> Sales Invoices</label>
                            <label class="tally-mod-chip"><input type="checkbox" class="th-mod-chk" value="CASH_ENTRIES" checked onchange="window.refreshTallyHubSummary()"> Cash / Income / Expense Entries</label>
                            <label class="tally-mod-chip"><input type="checkbox" class="th-mod-chk" value="LEDGERS_JV" checked onchange="window.refreshTallyHubSummary()"> Journal Vouchers & Ledgers</label>
                        </div>

                        <div id="thNoticeBanner" style="display:none;margin-bottom:12px;"></div>

                        <div class="tally-kpi-row" id="thKpiRow"></div>

                        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">
                            <div style="font-size:12px;font-weight:700;color:#334155;" id="thPreviewCountLabel">
                                Matching Vouchers Preview
                            </div>
                            <div style="display:flex;gap:8px;">
                                <button class="tally-btn-secondary" onclick="window.markSelectedTallyStatus('SYNCED')" title="Mark selected rows as Synced in Tally">
                                    <i class="fas fa-check-double" style="color:#059669;"></i> Mark Selected Synced
                                </button>
                                <button class="tally-btn-secondary" onclick="window.refreshTallyHubSummary()">
                                    <i class="fas fa-sync"></i> Refresh
                                </button>
                            </div>
                        </div>

                        <div class="tally-table-wrap">
                            <table class="tally-table">
                                <thead>
                                    <tr>
                                        <th style="width:32px;"><input type="checkbox" id="thSelectAllChk" onchange="window.toggleAllTallyRows(this.checked)"></th>
                                        <th>MyntOS / Tally Vch No.</th>
                                        <th>Tally Type</th>
                                        <th>Date</th>
                                        <th>Party / Ledger</th>
                                        <th>Segment</th>
                                        <th style="text-align:right;">Amount (₹)</th>
                                        <th>WVV Hash</th>
                                        <th>Tally Status</th>
                                    </tr>
                                </thead>
                                <tbody id="thPreviewTableBody">
                                    <tr><td colspan="9" style="text-align:center;padding:24px;color:#64748b;">Loading Tally sync summary...</td></tr>
                                </tbody>
                            </table>
                        </div>
                    </div>

                    <!-- Import / Reconcile Tab -->
                    <div id="thPaneImport" style="display:none;">
                        <div style="background:#f0fdfa;border:1px solid #99f6e4;border-radius:10px;padding:16px;margin-bottom:16px;">
                            <h4 style="margin:0 0 6px;font-size:14px;color:#0f766e;"><i class="fas fa-check-circle"></i> Bi-Directional Tally Daybook & Voucher Reconciliation</h4>
                            <p style="margin:0;font-size:12.5px;color:#334155;line-height:1.5;">
                                Upload a Tally Daybook / Voucher export file (<b>.xml</b> or <b>.csv</b>) from TallyPrime or Tally.ERP 9.
                                MyntOS will match vouchers using the preserved <b>MyntOS Voucher Number</b>, <b>Reference</b>, or <b>GUID</b> across Purchase Orders, Purchases, Sales, Cash/Income/Expenses, and Journal Vouchers, automatically marking matched entries as <b>SYNCED</b> and flagging any amount discrepancies as <b>MISMATCH</b>.
                            </p>
                        </div>
                        <div style="border:2px dashed #94a3b8;border-radius:12px;padding:28px;text-align:center;background:#f8fafc;margin-bottom:16px;">
                            <i class="fas fa-cloud-upload-alt" style="font-size:34px;color:#0f766e;margin-bottom:10px;"></i>
                            <div style="font-size:14px;font-weight:600;margin-bottom:6px;">Select Tally Daybook XML or CSV File</div>
                            <input type="file" id="thImportFileInput" accept=".xml,.csv" style="margin:10px auto;display:block;">
                            <button class="tally-btn-primary" onclick="window.uploadAndReconcileTallyFile()" id="thBtnRunImport" style="margin-top:10px;">
                                <i class="fas fa-bolt"></i> Upload & Reconcile with MyntOS
                            </button>
                        </div>
                        <div id="thImportResultBox" style="display:none;"></div>
                    </div>

                    <!-- Batches History Tab -->
                    <div id="thPaneBatches" style="display:none;">
                        <div class="tally-table-wrap" style="max-height:380px;">
                            <table class="tally-table">
                                <thead>
                                    <tr>
                                        <th>Batch Code</th>
                                        <th>Direction</th>
                                        <th>Tally Version</th>
                                        <th>Period</th>
                                        <th>Masters</th>
                                        <th>Vouchers</th>
                                        <th style="text-align:right;">Total Debit (₹)</th>
                                        <th style="text-align:right;">Total Credit (₹)</th>
                                        <th>WVV Batch Hash</th>
                                        <th>Timestamp</th>
                                    </tr>
                                </thead>
                                <tbody id="thBatchesTableBody">
                                    <tr><td colspan="10" style="text-align:center;padding:24px;color:#64748b;">No batch history yet.</td></tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

                <div class="tally-hub-footer">
                    <div style="font-size:12px;color:#475569;" id="thFooterInfo">
                        <i class="fas fa-shield-alt" style="color:#0f766e;"></i> WVV Protocol Enforced: Same MyntOS Voucher Numbers & Deterministic GUIDs prevent duplicates in Tally.
                    </div>
                    <div style="display:flex;gap:10px;">
                        <button class="tally-btn-secondary" onclick="window.closeMyntosTallyHub()">Close</button>
                        <button class="tally-btn-primary" id="thBtnDownloadXml" onclick="window.downloadMyntosTallyXml()">
                            <i class="fas fa-download"></i> Download Tally XML File
                        </button>
                    </div>
                </div>
            </div>
        `;
        overlay.addEventListener('click', function () {
            window.closeMyntosTallyHub();
        });
        document.body.appendChild(overlay);
        return overlay;
    }

    async function _populateCompaniesDropdown(selectedCid) {
        const sel = document.getElementById('thCompanySelect');
        if (!sel) return;
        try {
            const res = await _apiFetch(`${API_BASE}/companies`);
            const data = await res.json();
            const companies = Array.isArray(data) ? data : data.companies || data.data || [];
            sel.innerHTML = '';
            companies.forEach((c) => {
                const opt = document.createElement('option');
                opt.value = c.id;
                opt.textContent = `${c.company_name} (${c.company_code || 'ID:' + c.id})`;
                sel.appendChild(opt);
            });
            if (selectedCid && companies.some((c) => Number(c.id) === Number(selectedCid))) {
                sel.value = String(selectedCid);
            } else if (companies.length > 0) {
                sel.value = String(companies[0].id);
            }
            _hubState.companyId = parseInt(sel.value, 10) || selectedCid || 1;
        } catch (err) {
            console.warn('[TallyHub] Failed to load companies list:', err);
            if (selectedCid) {
                sel.innerHTML = `<option value="${selectedCid}">Company #${selectedCid}</option>`;
                _hubState.companyId = selectedCid;
            }
        }
    }

    function _getSelectedModules() {
        const chks = document.querySelectorAll('.th-mod-chk:checked');
        const mods = Array.from(chks).map((c) => c.value);
        return mods.length ? mods : ['MASTERS', 'PURCHASE_ORDERS', 'PURCHASE_INVOICES', 'SALES_INVOICES', 'CASH_ENTRIES', 'LEDGERS_JV'];
    }

    window.openMyntosTallyHub = async function (options = {}) {
        _ensureModalDOM();
        const detectedCid = options.companyId || _detectPageCompanyId();
        const detectedMod = options.module || _detectDefaultModule();

        const overlay = document.getElementById('myntosTallyHubOverlay');
        overlay.classList.add('active');

        await _populateCompaniesDropdown(detectedCid);

        // If opened from a specific module page and options.focusModuleOnly is true, keep all checked by default
        // or highlight the current module
        await window.refreshTallyHubSummary();
    };

    window.closeMyntosTallyHub = function () {
        const overlay = document.getElementById('myntosTallyHubOverlay');
        if (overlay) overlay.classList.remove('active');
    };

    window.switchTallyHubTab = function (tab) {
        _hubState.activeTab = tab;
        document.getElementById('thTabBtnExport').classList.toggle('active', tab === 'export');
        document.getElementById('thTabBtnImport').classList.toggle('active', tab === 'import');
        document.getElementById('thTabBtnBatches').classList.toggle('active', tab === 'batches');

        document.getElementById('thPaneExport').style.display = tab === 'export' ? 'block' : 'none';
        document.getElementById('thPaneImport').style.display = tab === 'import' ? 'block' : 'none';
        document.getElementById('thPaneBatches').style.display = tab === 'batches' ? 'block' : 'none';
        document.getElementById('thBtnDownloadXml').style.display = tab === 'export' ? 'inline-flex' : 'none';
    };

    window.onTallyHubPeriodChange = function () {
        const p = document.getElementById('thPeriodSelect').value;
        const isCustom = p === 'CUSTOM';
        document.getElementById('thCustomDateFromWrap').style.display = isCustom ? 'block' : 'none';
        document.getElementById('thCustomDateToWrap').style.display = isCustom ? 'block' : 'none';
        if (!isCustom) {
            window.refreshTallyHubSummary();
        }
    };

    window.onTallyHubCompanyChange = function () {
        const sel = document.getElementById('thCompanySelect');
        _hubState.companyId = parseInt(sel.value, 10) || 1;
        const segSel = document.getElementById('thSegmentSelect');
        if (segSel) segSel.value = '';
        window.refreshTallyHubSummary();
    };

    window.refreshTallyHubSummary = async function () {
        const cid = parseInt(document.getElementById('thCompanySelect')?.value || _hubState.companyId || 1, 10);
        const segId = document.getElementById('thSegmentSelect')?.value || '';
        const period = document.getElementById('thPeriodSelect')?.value || 'THIS_MONTH';
        const dFrom = document.getElementById('thDateFrom')?.value || '';
        const dTo = document.getElementById('thDateTo')?.value || '';
        const syncStat = document.getElementById('thSyncStatusSelect')?.value || 'ALL';
        const mods = _getSelectedModules().join(',');

        const tbody = document.getElementById('thPreviewTableBody');
        if (tbody) {
            tbody.innerHTML = `<tr><td colspan="9" style="text-align:center;padding:24px;color:#64748b;"><i class="fas fa-spinner fa-spin"></i> Loading WVV Tally summary...</td></tr>`;
        }

        const params = new URLSearchParams({
            company_id: String(cid),
            period: period,
            sync_status: syncStat,
            modules: mods,
        });
        if (segId) params.set('segment_id', segId);
        if (dFrom) params.set('date_from', dFrom);
        if (dTo) params.set('date_to', dTo);

        try {
            const res = await _apiFetch(`${API_BASE}/tally/sync-summary?${params.toString()}`);
            const data = await res.json();
            if (!data || !data.success) {
                if (tbody) {
                    tbody.innerHTML = `<tr><td colspan="9" style="text-align:center;padding:20px;color:#dc2626;">${(data && (data.message || data.detail)) || 'Failed to load Tally summary'}</td></tr>`;
                }
                return;
            }
            _hubState.summaryData = data;
            _hubState.selectedVouchers.clear();

            // Populate Segment selector preserving current selection
            const segSel = document.getElementById('thSegmentSelect');
            if (segSel && Array.isArray(data.segments)) {
                const prevSeg = segSel.value;
                segSel.innerHTML = `<option value="">All Segments (Consolidated)</option>`;
                data.segments.forEach((s) => {
                    const opt = document.createElement('option');
                    opt.value = String(s.id);
                    opt.textContent = `${s.segment_name} (${s.segment_code})`;
                    segSel.appendChild(opt);
                });
                if (prevSeg) segSel.value = prevSeg;
            }

            // Render Notice Banner (Segment exclusions, Cancellations pending sync, Validation warnings)
            const noticeEl = document.getElementById('thNoticeBanner');
            if (noticeEl) {
                const notices = [];
                if (Array.isArray(data.company_wide_excluded_modules) && data.company_wide_excluded_modules.length) {
                    notices.push(`<div><i class="fas fa-info-circle" style="color:#0369a1;"></i> <b>Segment Filter Active:</b> Company-wide modules without a segment attribute (<code>${data.company_wide_excluded_modules.join(', ')}</code>) are excluded to keep this segment export pure.</div>`);
                }
                if (data.kpi && data.kpi.cancelled_pending_sync > 0) {
                    notices.push(`<div><i class="fas fa-exclamation-triangle" style="color:#c2410c;"></i> <b>${data.kpi.cancelled_pending_sync} Previously Synced Voucher(s) Cancelled/Deleted:</b> Exporting will emit Tally cancellation instructions (<code>ACTION="Cancel"</code>) to reverse them in Tally.</div>`);
                }
                if (Array.isArray(data.validation_warnings) && data.validation_warnings.length) {
                    notices.push(`<div><i class="fas fa-exclamation-circle" style="color:#b45309;"></i> <b>Accounting Validation Warnings (${data.validation_warnings.length}):</b> ${data.validation_warnings.slice(0, 2).join(' | ')}</div>`);
                }
                if (notices.length) {
                    noticeEl.style.display = 'block';
                    noticeEl.innerHTML = `<div style="background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:10px 14px;font-size:12px;color:#78350f;line-height:1.5;display:flex;flex-direction:column;gap:4px;">${notices.join('')}</div>`;
                } else {
                    noticeEl.style.display = 'none';
                    noticeEl.innerHTML = '';
                }
            }

            // Render KPI Cards
            const kpiRow = document.getElementById('thKpiRow');
            const ms = data.module_stats || {};
            const cardDefs = [
                { key: 'PURCHASE_ORDERS', label: 'Purchase Orders' },
                { key: 'PURCHASE_INVOICES', label: 'Purchase Invoices' },
                { key: 'SALES_INVOICES', label: 'Sales Invoices' },
                { key: 'CASH_ENTRIES', label: 'Cash / Inc / Exp' },
                { key: 'LEDGERS_JV', label: 'Journal & Ledgers' },
            ];
            if (kpiRow) {
                kpiRow.innerHTML = cardDefs
                    .map((cd) => {
                        const s = ms[cd.key] || { total: 0, not_synced: 0, modified: 0, cancelled_pending_sync: 0, synced: 0, exported: 0, total_amount: 0 };
                        const pendingCnt = (s.not_synced || 0) + (s.modified || 0) + (s.cancelled_pending_sync || 0);
                        const doneCnt = (s.synced || 0) + (s.exported || 0);
                        return `
                            <div class="tally-kpi-card">
                                <div class="k-title">${cd.label}</div>
                                <div class="k-val">${s.total} <span style="font-size:12px;font-weight:500;color:#64748b;">vouchers</span></div>
                                <div class="k-sub">
                                    ₹${Number(s.total_amount || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                                    • <span style="color:#d97706;">${pendingCnt} pending</span>
                                    • <span style="color:#059669;">${doneCnt} synced</span>
                                </div>
                            </div>
                        `;
                    })
                    .join('');
            }

            // Render Vouchers Preview Table
            const vouchers = data.vouchers_preview || [];
            const cntLbl = document.getElementById('thPreviewCountLabel');
            if (cntLbl) {
                const pInfo = data.period || {};
                const rangeTxt = pInfo.date_from ? `${pInfo.date_from} to ${pInfo.date_to}` : 'All Dates';
                cntLbl.textContent = `Matching Vouchers (${ data.total_matching_vouchers || 0 } total • Period: ${rangeTxt})`;
            }

            if (tbody) {
                if (!vouchers.length) {
                    tbody.innerHTML = `<tr><td colspan="9" style="text-align:center;padding:24px;color:#64748b;">No vouchers match the selected period/segment/filter. (Masters can still be downloaded).</td></tr>`;
                } else {
                    tbody.innerHTML = vouchers
                        .map((v) => {
                            const key = `${v.entity_type}:${v.entity_id}`;
                            return `
                                <tr>
                                    <td><input type="checkbox" class="th-row-chk" data-etype="${v.entity_type}" data-eid="${v.entity_id}" data-vno="${v.myntos_voucher_no}" value="${key}"></td>
                                    <td style="font-weight:700;color:#0f172a;">${v.myntos_voucher_no}</td>
                                    <td><span style="font-weight:600;color:#0f766e;">${v.tally_voucher_type}</span></td>
                                    <td>${v.transaction_date || '-'}</td>
                                    <td>${v.party_name || '-'}</td>
                                    <td>${v.segment_name || 'General'}</td>
                                    <td style="text-align:right;font-weight:600;">₹${Number(v.amount || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                                    <td><code style="font-size:10px;color:#64748b;">${v.wvv_hash || '-'}</code></td>
                                    <td><span class="tally-badge ${v.tally_status}">${v.tally_status.replace(/_/g, ' ')}</span></td>
                                </tr>
                            `;
                        })
                        .join('');
                }
            }

            // Render Recent Batches Table
            const bBody = document.getElementById('thBatchesTableBody');
            const batches = data.recent_batches || [];
            if (bBody) {
                if (!batches.length) {
                    bBody.innerHTML = `<tr><td colspan="10" style="text-align:center;padding:24px;color:#64748b;">No Tally XML export/import batches recorded yet.</td></tr>`;
                } else {
                    bBody.innerHTML = batches
                        .map(
                            (b) => `
                            <tr>
                                <td style="font-weight:700;">${b.batch_code}</td>
                                <td><span class="tally-badge ${b.direction === 'IMPORT' ? 'SYNCED' : 'EXPORTED'}">${b.direction}</span></td>
                                <td>${b.tally_version}</td>
                                <td>${b.period_preset || '-'} ${b.date_from ? '(' + b.date_from + ' → ' + b.date_to + ')' : ''}</td>
                                <td>${b.masters_count}</td>
                                <td>${b.vouchers_count}</td>
                                <td style="text-align:right;">₹${Number(b.total_debit || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                                <td style="text-align:right;">₹${Number(b.total_credit || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                                <td><code style="font-size:10px;">${(b.wvv_batch_hash || '').slice(0, 12)}</code></td>
                                <td>${(b.created_at || '').replace('T', ' ').slice(0, 16)}</td>
                            </tr>
                        `
                        )
                        .join('');
                }
            }
        } catch (err) {
            console.error('[TallyHub] Summary error:', err);
            if (tbody) {
                tbody.innerHTML = `<tr><td colspan="9" style="text-align:center;padding:20px;color:#dc2626;">Error loading summary: ${err.message}</td></tr>`;
            }
        }
    };

    window.toggleAllTallyRows = function (checked) {
        document.querySelectorAll('.th-row-chk').forEach((chk) => {
            chk.checked = checked;
        });
    };

    window.markSelectedTallyStatus = async function (targetStatus) {
        const cid = parseInt(document.getElementById('thCompanySelect')?.value || _hubState.companyId || 1, 10);
        const chks = Array.from(document.querySelectorAll('.th-row-chk:checked'));
        if (!chks.length) {
            alert('Please select at least one voucher row first.');
            return;
        }
        const items = chks.map((c) => ({
            entity_type: c.getAttribute('data-etype'),
            entity_id: parseInt(c.getAttribute('data-eid'), 10),
            myntos_voucher_no: c.getAttribute('data-vno'),
        }));

        try {
            const res = await _apiFetch(`${API_BASE}/tally/mark-status`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ company_id: cid, status: targetStatus, items }),
            });
            const data = await res.json();
            if (data && data.success) {
                await window.refreshTallyHubSummary();
            } else {
                alert((data && (data.message || data.detail)) || 'Failed to update status');
            }
        } catch (err) {
            alert('Error updating status: ' + err.message);
        }
    };

    window.downloadMyntosTallyXml = async function () {
        const btn = document.getElementById('thBtnDownloadXml');
        const cid = parseInt(document.getElementById('thCompanySelect')?.value || _hubState.companyId || 1, 10);
        const segId = document.getElementById('thSegmentSelect')?.value || '';
        const tallyVersion = document.getElementById('thVersionSelect')?.value || 'TALLY_PRIME_4';
        const period = document.getElementById('thPeriodSelect')?.value || 'THIS_MONTH';
        const dFrom = document.getElementById('thDateFrom')?.value || '';
        const dTo = document.getElementById('thDateTo')?.value || '';
        const voucherMode = document.getElementById('thVoucherModeSelect')?.value || 'AUTO';
        const syncStat = document.getElementById('thSyncStatusSelect')?.value || 'ALL';
        const mods = _getSelectedModules();

        if (btn) {
            btn.disabled = true;
            btn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Generating WVV Tally XML...`;
        }

        try {
            const res = await _apiFetch(`${API_BASE}/tally/export-xml`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    company_id: cid,
                    segment_id: segId ? parseInt(segId, 10) : null,
                    tally_version: tallyVersion,
                    voucher_mode: voucherMode,
                    period: period,
                    date_from: dFrom || null,
                    date_to: dTo || null,
                    sync_status: syncStat,
                    modules: mods,
                    include_masters: mods.includes('MASTERS'),
                }),
            });
            const data = await res.json();
            if (!data || !data.success) {
                alert((data && (data.message || data.detail)) || 'Failed to generate Tally XML');
                return;
            }

            // Trigger browser download of XML file
            const blob = new Blob([data.xml_content], { type: 'application/xml;charset=utf-8' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = data.filename || 'MyntOS_Tally_Export.xml';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            const footerInfo = document.getElementById('thFooterInfo');
            if (footerInfo) {
                const unresolvedWarn = Array.isArray(data.unresolved_ledgers) && data.unresolved_ledgers.length
                    ? ` • <span style="color:#d97706;">${data.unresolved_ledgers.length} unresolved ledger(s) placed in Suspense A/c</span>`
                    : '';
                footerInfo.innerHTML = `<span style="color:#059669;font-weight:700;"><i class="fas fa-check-circle"></i> Downloaded ${data.filename}: ${data.masters_count} Masters + ${data.vouchers_count} Vouchers (Dr ₹${Number(data.total_debit).toLocaleString('en-IN')} = Cr ₹${Number(data.total_credit).toLocaleString('en-IN')})${unresolvedWarn}</span>`;
            }

            await window.refreshTallyHubSummary();
        } catch (err) {
            console.error('[TallyHub] Export failed:', err);
            alert('Failed to download Tally XML: ' + err.message);
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = `<i class="fas fa-download"></i> Download Tally XML File`;
            }
        }
    };

    window.uploadAndReconcileTallyFile = async function () {
        const fileInp = document.getElementById('thImportFileInput');
        const cid = parseInt(document.getElementById('thCompanySelect')?.value || _hubState.companyId || 1, 10);
        const btn = document.getElementById('thBtnRunImport');
        const resBox = document.getElementById('thImportResultBox');

        if (!fileInp || !fileInp.files || !fileInp.files[0]) {
            alert('Please choose a Tally XML or CSV file to upload.');
            return;
        }

        const formData = new FormData();
        formData.append('file', fileInp.files[0]);
        formData.append('company_id', String(cid));

        if (btn) {
            btn.disabled = true;
            btn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Reconciling with MyntOS...`;
        }

        try {
            const res = await _apiFetch(`${API_BASE}/tally/import-reconcile`, {
                method: 'POST',
                body: formData,
            });
            const data = await res.json();
            if (!data || !data.success) {
                alert((data && (data.message || data.detail)) || 'Reconciliation failed');
                return;
            }
            if (resBox) {
                resBox.style.display = 'block';
                resBox.innerHTML = `
                    <div style="padding:14px;border-radius:10px;background:#ecfdf5;border:1px solid #6ee7b7;font-size:13px;">
                        <div style="font-weight:700;color:#065f46;margin-bottom:6px;">
                            <i class="fas fa-check-circle"></i> Reconciliation Complete (Batch: ${data.batch?.batch_code || '-'})
                        </div>
                        <div style="display:flex;gap:18px;flex-wrap:wrap;color:#1e293b;">
                            <span>Parsed Vouchers in File: <b>${data.parsed_vouchers_count}</b></span>
                            <span style="color:#059669;">Matched & Marked SYNCED: <b>${data.synced_count}</b></span>
                            <span style="color:#dc2626;">Mismatches (Amount/Date/Type): <b>${data.mismatch_count}</b></span>
                            <span style="color:#b45309;">Ambiguous (Skipped): <b>${data.ambiguous_count || 0}</b></span>
                            <span style="color:#64748b;">Unmatched in File: <b>${data.unmatched_count}</b></span>
                        </div>
                    </div>
                `;
            }
            await window.refreshTallyHubSummary();
        } catch (err) {
            alert('Error uploading Tally file: ' + err.message);
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = `<i class="fas fa-bolt"></i> Upload & Reconcile with MyntOS`;
            }
        }
    };

    // Auto-mount floating / header Tally Sync Hub button on SFMS Accounting pages
    function _autoMountHeaderButton() {
        const path = (window.location.pathname || '').toLowerCase();
        const isTargetPage =
            path.includes('staff_accounts') ||
            path.includes('/staff/accounts') ||
            document.querySelector('script[src*="tally-sync-hub.js"]');
        if (!isTargetPage) return;
        if (document.getElementById('myntosTallyHubTriggerBtn')) return;

        _injectStyles();
        const btn = document.createElement('button');
        btn.id = 'myntosTallyHubTriggerBtn';
        btn.type = 'button';
        btn.className = 'tally-hub-btn';
        btn.innerHTML = `<i class="fas fa-sync-alt"></i> Tally XML Sync & Download`;
        btn.onclick = function () {
            window.openMyntosTallyHub();
        };

        // Find primary page header action bar
        const actionContainers = [
            '.header-actions',
            '.page-header-actions',
            '.top-actions',
            '.action-buttons',
            '.page-header .d-flex',
            '.header-right',
            '.toolbar-right',
        ];
        for (const sel of actionContainers) {
            const container = document.querySelector(sel);
            if (container) {
                container.prepend(btn);
                return;
            }
        }

        // Fallback: attach to page-header or fixed bottom-right pill
        const pageHeader = document.querySelector('.page-header, .content-header, .top-bar');
        if (pageHeader) {
            pageHeader.appendChild(btn);
        } else {
            btn.style.position = 'fixed';
            btn.style.bottom = '22px';
            btn.style.right = '22px';
            btn.style.zIndex = '9990';
            document.body.appendChild(btn);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', _autoMountHeaderButton);
    } else {
        setTimeout(_autoMountHeaderButton, 150);
    }
})();
