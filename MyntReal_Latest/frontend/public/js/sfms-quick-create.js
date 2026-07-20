/**
 * SFMS Quick Create Component Library
 * DC Protocol Compliant - Reusable modal templates for Stock Items, HSN Codes, and Vendors
 * WVV Protocol: Full template parity with dedicated master pages - ALL fields included
 * Version: 2.0.0 - Complete 5-tab Vendor modal with full field coverage
 */

const SFMSQuickCreate = (function() {
    'use strict';
    
    const API_BASE = '/api/v1/staff/accounts';
    let companies = [];
    let hsnCodes = [];
    let stockItems = [];
    let callbacks = {};
    let currentContext = null;
    let vendorSelectedProducts = [];
    
    function getToken() {
        return localStorage.getItem('staff_token');
    }
    
    async function loadCompanies() {
        try {
            const response = await fetch(`${API_BASE}/companies`, {
                headers: { 'Authorization': `Bearer ${getToken()}` }
            });
            if (response.ok) {
                const data = await response.json();
                companies = (data.companies || []).filter(c => c.is_active !== false);
            }
        } catch (e) { console.error('[SFMS-QC] Failed to load companies:', e); }
        return companies;
    }
    
    async function loadHsnCodes() {
        try {
            const response = await fetch(`${API_BASE}/hsn`, {
                headers: { 'Authorization': `Bearer ${getToken()}` }
            });
            if (response.ok) {
                const data = await response.json();
                hsnCodes = data.hsn_codes || [];
            }
        } catch (e) { console.error('[SFMS-QC] Failed to load HSN codes:', e); }
        return hsnCodes;
    }
    
    async function loadStockItems() {
        try {
            const response = await fetch(`${API_BASE}/stock-items?limit=1000`, {
                headers: { 'Authorization': `Bearer ${getToken()}` }
            });
            if (response.ok) {
                const data = await response.json();
                stockItems = data.stock_items || [];
            }
        } catch (e) { console.error('[SFMS-QC] Failed to load stock items:', e); }
        return stockItems;
    }
    
    async function init() {
        await Promise.all([loadCompanies(), loadHsnCodes()]);
        injectModalContainer();
        console.log('[SFMS-QC] Quick Create Component v2.0 initialized (DC+WVV Protocol Compliant)');
    }
    
    function injectModalContainer() {
        if (document.getElementById('sfmsQuickCreateModal')) return;
        
        const style = document.createElement('style');
        style.textContent = `
            .sfms-qc-tabs { display: flex; gap: 0; border-bottom: 2px solid #e5e7eb; margin-bottom: 20px; }
            .sfms-qc-tab { padding: 10px 16px; cursor: pointer; border: none; background: none; color: #6b7280; font-weight: 500; transition: all 0.2s; border-bottom: 2px solid transparent; margin-bottom: -2px; }
            .sfms-qc-tab:hover { color: #374151; background: #f3f4f6; }
            .sfms-qc-tab.active { color: #2563eb; border-bottom-color: #2563eb; background: #eff6ff; }
            .sfms-qc-tab-content { display: none; }
            .sfms-qc-tab-content.active { display: block; }
            .sfms-qc-section { font-weight: 600; margin: 16px 0 12px 0; padding-bottom: 8px; border-bottom: 2px solid #e5e7eb; color: #374151; }
            .sfms-qc-section i { margin-right: 8px; color: #6b7280; }
            .sfms-qc-grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }
            .sfms-qc-grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; margin-bottom: 16px; }
            .sfms-qc-grid-4 { display: grid; grid-template-columns: 1fr 1fr 1fr auto; gap: 16px; align-items: end; margin-bottom: 16px; }
            .sfms-qc-badge { display: inline-flex; align-items: center; gap: 6px; padding: 6px 10px; background: #2563eb; color: white; border-radius: 6px; font-size: 12px; margin: 4px; }
            .sfms-qc-badge .remove { cursor: pointer; font-weight: bold; opacity: 0.8; }
            .sfms-qc-badge .remove:hover { opacity: 1; }
            .sfms-qc-product-list { max-height: 150px; overflow-y: auto; border: 1px solid #ddd; border-radius: 8px; padding: 8px; background: #fafafa; }
            .sfms-qc-product-item { padding: 8px; border-radius: 4px; margin-bottom: 4px; cursor: pointer; display: flex; justify-content: space-between; align-items: center; }
            .sfms-qc-product-item:hover { background: #e5e7eb; }
            .sfms-qc-product-item.selected { background: #dbeafe; border-left: 3px solid #2563eb; }
            .sfms-qc-pin-btn { padding: 8px 12px; background: #6b7280; color: white; border: none; border-radius: 6px; cursor: pointer; white-space: nowrap; }
            .sfms-qc-pin-btn:hover { background: #4b5563; }
            .sfms-qc-info-box { background: #f0f9ff; padding: 12px; border-radius: 8px; margin-top: 12px; border: 1px solid #bae6fd; }
            .sfms-qc-info-box i { margin-right: 6px; color: #0369a1; }
            #sfmsQuickCreateModal .modal-content { max-width: 800px; max-height: 90vh; overflow-y: auto; }
        `;
        document.head.appendChild(style);
        
        const modalHtml = `
            <div class="modal-overlay" id="sfmsQuickCreateModal" style="display: none;">
                <div class="modal-content">
                    <div class="modal-header">
                        <h3 id="sfmsQcTitle"><i class="fas fa-plus-circle me-2"></i>Quick Create</h3>
                        <button class="modal-close" onclick="SFMSQuickCreate.close()">&times;</button>
                    </div>
                    <div class="modal-body" id="sfmsQcBody"></div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" onclick="SFMSQuickCreate.close()">Cancel</button>
                        <button type="button" class="btn btn-success" id="sfmsQcSubmitBtn" onclick="SFMSQuickCreate.submit()">
                            <i class="fas fa-save me-1"></i>Create
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        const container = document.createElement('div');
        container.innerHTML = modalHtml;
        document.body.appendChild(container.firstElementChild);
    }
    
    let stockItemColors = [];
    
    function getStockItemFormHtml(prefill = {}) {
        const companyOptions = companies.map(c => 
            `<option value="${c.id}">${c.company_name}</option>`
        ).join('');
        
        stockItemColors = [];
        
        return `
            <div class="sfms-qc-section"><i class="fas fa-info-circle"></i>Basic Information</div>
            <div class="sfms-qc-grid-2">
                <div class="form-group">
                    <label for="sfmsQcItemName">Item Name *</label>
                    <input type="text" id="sfmsQcItemName" required placeholder="Enter item name" value="${prefill.name || ''}">
                </div>
                <div class="form-group">
                    <label for="sfmsQcItemCode">Item Code *</label>
                    <input type="text" id="sfmsQcItemCode" placeholder="Auto-generated..." style="font-family:monospace;font-weight:600;color:#4c1d95;" title="Auto-generated from category. You may type a custom code if needed." value="${prefill.code || ''}">
                </div>
            </div>
            <div class="sfms-qc-grid-2">
                <div class="form-group">
                    <label for="sfmsQcItemCategory">Category</label>
                    <select id="sfmsQcItemCategory" onchange="SFMSQuickCreate.generateItemCode()">
                        <option value="PRODUCT">Product</option>
                        <option value="RAW_MATERIAL">Raw Material</option>
                        <option value="CONSUMABLE">Consumable</option>
                        <option value="SPARE_PART">Spare Part</option>
                        <option value="ACCESSORY">Accessory</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="sfmsQcItemUnit">Unit of Measure</label>
                    <select id="sfmsQcItemUnit">
                        <option value="PCS">Pieces</option>
                        <option value="KG">Kilograms</option>
                        <option value="LTR">Liters</option>
                        <option value="MTR">Meters</option>
                        <option value="SET">Set</option>
                        <option value="BOX">Boxes</option>
                        <option value="PACK">Pack</option>
                        <option value="PAIR">Pair</option>
                        <option value="UNIT">Unit</option>
                    </select>
                </div>
            </div>
            
            <div class="sfms-qc-section"><i class="fas fa-building"></i>Applicable Companies *</div>
            <div class="form-group" style="margin-bottom: 16px;">
                <label for="sfmsQcCompanySelect">Select Company</label>
                <select id="sfmsQcCompanySelect" onchange="SFMSQuickCreate.addCompany()">
                    <option value="">-- Select Company to Add --</option>
                    ${companyOptions}
                </select>
                <div id="sfmsQcCompanyBadges" class="company-badges" style="display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px;"></div>
                <input type="hidden" id="sfmsQcCompanies" value="[]">
            </div>
            
            <div class="sfms-qc-section"><i class="fas fa-tags"></i>Specifications</div>
            <div class="form-group" style="margin-bottom: 16px;">
                <label for="sfmsQcItemDescription">Description</label>
                <textarea id="sfmsQcItemDescription" placeholder="Item description" rows="2">${prefill.description || ''}</textarea>
            </div>
            <div class="form-group" style="margin-bottom: 16px;">
                <label for="sfmsQcItemSpec">Specification</label>
                <textarea id="sfmsQcItemSpec" placeholder="Technical specifications (e.g., dimensions, material, features)" rows="2">${prefill.specification || ''}</textarea>
            </div>
            <div class="sfms-qc-grid-2">
                <div class="form-group">
                    <label for="sfmsQcItemSize">Size</label>
                    <input type="text" id="sfmsQcItemSize" placeholder="e.g., Large, 10x20cm, XL" value="${prefill.size || ''}">
                </div>
                <div class="form-group">
                    <label for="sfmsQcItemColorInput">Colors (press Enter to add)</label>
                    <input type="text" id="sfmsQcItemColorInput" placeholder="Type color and press Enter" onkeydown="if(event.key==='Enter'){event.preventDefault();SFMSQuickCreate.addStockItemColor();}">
                    <div class="color-input-container" id="sfmsQcItemColors" style="display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px;"></div>
                    <input type="hidden" id="sfmsQcItemColorsData" value="[]">
                </div>
            </div>
            
            <div class="sfms-qc-section"><i class="fas fa-rupee-sign"></i>Pricing & Inventory</div>
            <div class="sfms-qc-grid-2">
                <div class="form-group">
                    <label for="sfmsQcItemPurchaseRate">Purchase Rate</label>
                    <input type="number" id="sfmsQcItemPurchaseRate" step="0.01" min="0" placeholder="Purchase price" value="${prefill.purchaseRate || ''}">
                </div>
                <div class="form-group">
                    <label for="sfmsQcItemSellingRate">Selling Rate</label>
                    <input type="number" id="sfmsQcItemSellingRate" step="0.01" min="0" placeholder="Selling price" value="${prefill.sellingRate || ''}">
                </div>
            </div>
            <div class="sfms-qc-grid-2">
                <div class="form-group">
                    <label for="sfmsQcItemReorder">Reorder Level</label>
                    <input type="number" id="sfmsQcItemReorder" min="0" value="10" placeholder="Low stock alert level">
                </div>
                <div class="form-group">
                    <label for="sfmsQcHsnSearch">HSN Code <small class="text-muted">(Search or create new)</small></label>
                    <div class="hsn-search-container" style="position: relative;">
                        <input type="text" id="sfmsQcHsnSearch" class="hsn-search-input" placeholder="Type to search HSN codes..." autocomplete="off" 
                            onfocus="SFMSQuickCreate.showHsnDropdown()" oninput="SFMSQuickCreate.filterHsn()">
                        <div id="sfmsQcHsnDropdown" class="hsn-dropdown" style="display: none; position: absolute; top: 100%; left: 0; right: 0; max-height: 250px; overflow-y: auto; background: white; border: 1px solid #ddd; border-radius: 6px; z-index: 1000; box-shadow: 0 4px 12px rgba(0,0,0,0.15);"></div>
                        <input type="hidden" id="sfmsQcItemHsnId" value="${prefill.hsnId || ''}">
                        <div id="sfmsQcHsnSelected" style="margin-top: 6px;"></div>
                    </div>
                </div>
            </div>
            <div class="form-group">
                <label for="sfmsQcItemGstRate">GST Rate</label>
                <input type="text" id="sfmsQcItemGstRate" readonly placeholder="Auto-calculated from HSN" style="background-color: #f5f5f5; cursor: not-allowed;">
            </div>
        `;
    }
    
    function addStockItemColor() {
        const input = document.getElementById('sfmsQcItemColorInput');
        const color = input.value.trim();
        if (!color) return;
        
        if (!stockItemColors.includes(color)) {
            stockItemColors.push(color);
            document.getElementById('sfmsQcItemColorsData').value = JSON.stringify(stockItemColors);
            renderStockItemColors();
        }
        
        input.value = '';
    }
    
    function removeStockItemColor(color) {
        stockItemColors = stockItemColors.filter(c => c !== color);
        document.getElementById('sfmsQcItemColorsData').value = JSON.stringify(stockItemColors);
        renderStockItemColors();
    }
    
    function renderStockItemColors() {
        const container = document.getElementById('sfmsQcItemColors');
        container.innerHTML = stockItemColors.map(color => 
            `<span class="color-tag" style="display: inline-flex; align-items: center; gap: 4px; background: #f3f4f6; padding: 4px 8px; border-radius: 4px; font-size: 12px;">
                ${color} 
                <span class="remove-color" onclick="SFMSQuickCreate.removeStockItemColor('${color.replace(/'/g, "\\'")}')" style="cursor: pointer; color: #9ca3af;">&times;</span>
            </span>`
        ).join('');
    }
    
    function getHsnFormHtml(prefill = {}) {
        const today = new Date().toISOString().split('T')[0];
        return `
            <div class="sfms-qc-section"><i class="fas fa-hashtag"></i>HSN/SAC Code Details</div>
            <div class="sfms-qc-grid-2">
                <div class="form-group">
                    <label>HSN/SAC Code *</label>
                    <input type="text" id="sfmsQcHsnCode" required placeholder="e.g., 8507, 9403" maxlength="20" value="${prefill.code || ''}">
                </div>
                <div class="form-group">
                    <label>Effective From *</label>
                    <input type="date" id="sfmsQcHsnEffectiveFrom" required value="${prefill.effectiveFrom || today}">
                </div>
            </div>
            <div class="form-group" style="margin-bottom: 16px;">
                <label>Description *</label>
                <input type="text" id="sfmsQcHsnDescription" required placeholder="e.g., Electric Batteries" value="${prefill.description || ''}">
            </div>
            
            <div class="sfms-qc-section"><i class="fas fa-percent"></i>GST Rates</div>
            <div class="sfms-qc-grid-2">
                <div class="form-group">
                    <label>CGST Rate (%)</label>
                    <input type="number" id="sfmsQcHsnCgst" step="0.01" min="0" max="50" value="${prefill.cgst || '9'}" placeholder="e.g., 9" oninput="SFMSQuickCreate.calcHsnIgst()">
                </div>
                <div class="form-group">
                    <label>SGST Rate (%)</label>
                    <input type="number" id="sfmsQcHsnSgst" step="0.01" min="0" max="50" value="${prefill.sgst || '9'}" placeholder="e.g., 9" oninput="SFMSQuickCreate.calcHsnIgst()">
                </div>
            </div>
            <div class="sfms-qc-grid-2">
                <div class="form-group">
                    <label>IGST Rate (%) <small class="text-muted">(Auto = CGST + SGST)</small></label>
                    <input type="number" id="sfmsQcHsnIgst" step="0.01" min="0" max="50" value="${prefill.igst || '18'}" placeholder="e.g., 18" style="background: #f5f5f5;">
                </div>
                <div class="form-group">
                    <label>Cess Rate (%)</label>
                    <input type="number" id="sfmsQcHsnCess" step="0.01" min="0" value="${prefill.cess || '0'}" placeholder="0">
                </div>
            </div>
            <div class="form-group">
                <label>Effective To <small class="text-muted">(Leave blank for ongoing)</small></label>
                <input type="date" id="sfmsQcHsnEffectiveTo" value="${prefill.effectiveTo || ''}">
            </div>
            <div class="sfms-qc-info-box">
                <small><i class="fas fa-info-circle"></i>Total GST: <strong id="sfmsQcHsnTotalGst">18%</strong> (CGST + SGST for intra-state, IGST for inter-state)</small>
            </div>
        `;
    }
    
    function getVendorFormHtml(prefill = {}) {
        const companyOptions = companies.map(c => 
            `<option value="${c.id}">${c.company_name}</option>`
        ).join('');
        
        vendorSelectedProducts = [];
        
        return `
            <div class="sfms-qc-tabs">
                <button class="sfms-qc-tab active" onclick="SFMSQuickCreate.switchVendorTab('basic')">Basic Info</button>
                <button class="sfms-qc-tab" onclick="SFMSQuickCreate.switchVendorTab('contacts')">Contacts</button>
                <button class="sfms-qc-tab" onclick="SFMSQuickCreate.switchVendorTab('address')">Address</button>
                <button class="sfms-qc-tab" onclick="SFMSQuickCreate.switchVendorTab('bank')">Bank & Payment</button>
                <button class="sfms-qc-tab" onclick="SFMSQuickCreate.switchVendorTab('products')">Products</button>
            </div>
            
            <!-- Basic Info Tab -->
            <div class="sfms-qc-tab-content active" id="sfmsQcVendorTabBasic">
                <div class="sfms-qc-grid-2">
                    <div class="form-group">
                        <label>Vendor Name *</label>
                        <input type="text" id="sfmsQcVendorName" required placeholder="Enter vendor name" value="${prefill.name || ''}">
                    </div>
                    <div class="form-group">
                        <label>Vendor Code *</label>
                        <input type="text" id="sfmsQcVendorCode" required placeholder="e.g., VND001" maxlength="20" value="${prefill.code || ''}">
                    </div>
                </div>
                <div class="sfms-qc-grid-2">
                    <div class="form-group">
                        <label>Vendor Type</label>
                        <select id="sfmsQcVendorType">
                            <option value="BOTH">Both (Product & Service)</option>
                            <option value="PRODUCT">Product Only</option>
                            <option value="SERVICE">Service Only</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Email</label>
                        <input type="email" id="sfmsQcVendorEmail" placeholder="Email address" value="${prefill.email || ''}">
                    </div>
                </div>
                <div class="sfms-qc-grid-2">
                    <div class="form-group">
                        <label>GST Number</label>
                        <input type="text" id="sfmsQcVendorGst" placeholder="15-character GSTIN" maxlength="15" value="${prefill.gst || ''}">
                    </div>
                    <div class="form-group">
                        <label>PAN Number</label>
                        <input type="text" id="sfmsQcVendorPan" placeholder="10-character PAN" maxlength="10" value="${prefill.pan || ''}">
                    </div>
                </div>
                <div class="sfms-qc-section"><i class="fas fa-building"></i>Applicable Companies *</div>
                <div class="form-group">
                    <select id="sfmsQcVendorCompanySelect" onchange="SFMSQuickCreate.addVendorCompany()">
                        <option value="">-- Select Company to Add --</option>
                        ${companyOptions}
                    </select>
                    <div id="sfmsQcVendorCompanyBadges" style="display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px;"></div>
                    <input type="hidden" id="sfmsQcVendorApplicableCompanies" value="[]">
                </div>
                <div class="form-group mt-3">
                    <label class="d-flex align-items-center gap-2">
                        <input type="checkbox" id="sfmsQcVendorIsActive" checked>
                        <span>Active</span>
                    </label>
                </div>
            </div>
            
            <!-- Contacts Tab -->
            <div class="sfms-qc-tab-content" id="sfmsQcVendorTabContacts">
                <div class="sfms-qc-section"><i class="fas fa-user"></i>Contact Person 1 (Primary)</div>
                <div class="sfms-qc-grid-3">
                    <div class="form-group">
                        <label>Name</label>
                        <input type="text" id="sfmsQcVendorContact1Name" placeholder="Contact name">
                    </div>
                    <div class="form-group">
                        <label>Phone</label>
                        <input type="text" id="sfmsQcVendorContact1Phone" placeholder="Phone number">
                    </div>
                    <div class="form-group">
                        <label>Designation</label>
                        <input type="text" id="sfmsQcVendorContact1Designation" placeholder="e.g., Sales Manager">
                    </div>
                </div>
                <div class="sfms-qc-section"><i class="fas fa-user-friends"></i>Contact Person 2 (Secondary)</div>
                <div class="sfms-qc-grid-3">
                    <div class="form-group">
                        <label>Name</label>
                        <input type="text" id="sfmsQcVendorContact2Name" placeholder="Contact name">
                    </div>
                    <div class="form-group">
                        <label>Phone</label>
                        <input type="text" id="sfmsQcVendorContact2Phone" placeholder="Phone number">
                    </div>
                    <div class="form-group">
                        <label>Designation</label>
                        <input type="text" id="sfmsQcVendorContact2Designation" placeholder="e.g., Accounts Manager">
                    </div>
                </div>
                <div class="sfms-qc-section"><i class="fas fa-globe"></i>Website</div>
                <div class="form-group">
                    <input type="url" id="sfmsQcVendorWebsite" placeholder="https://www.example.com">
                </div>
            </div>
            
            <!-- Address Tab -->
            <div class="sfms-qc-tab-content" id="sfmsQcVendorTabAddress">
                <div class="sfms-qc-section"><i class="fas fa-map-marker-alt"></i>Primary Address</div>
                <div class="form-group">
                    <label>Address</label>
                    <textarea id="sfmsQcVendorAddress" placeholder="Full address" rows="2"></textarea>
                </div>
                <div class="sfms-qc-grid-4">
                    <div class="form-group">
                        <label>Pincode</label>
                        <input type="text" id="sfmsQcVendorPincode" placeholder="6-digit PIN" maxlength="6" oninput="SFMSQuickCreate.lookupPincode(this.value, 'primary')">
                    </div>
                    <div class="form-group">
                        <label>City</label>
                        <input type="text" id="sfmsQcVendorCity" placeholder="City">
                    </div>
                    <div class="form-group">
                        <label>State</label>
                        <input type="text" id="sfmsQcVendorState" placeholder="State">
                    </div>
                    <button type="button" class="sfms-qc-pin-btn" onclick="SFMSQuickCreate.lookupPincode(document.getElementById('sfmsQcVendorPincode').value, 'primary')">
                        <i class="fas fa-search"></i> Lookup
                    </button>
                </div>
                <div class="sfms-qc-grid-2">
                    <div class="form-group">
                        <label>Map Link 1 (Office)</label>
                        <input type="text" id="sfmsQcVendorMapLink1Label" placeholder="Label (e.g., Head Office)" style="margin-bottom: 8px;">
                        <input type="url" id="sfmsQcVendorMapLink1" placeholder="Google Maps URL">
                    </div>
                    <div class="form-group">
                        <label>Map Link 2 (Warehouse)</label>
                        <input type="text" id="sfmsQcVendorMapLink2Label" placeholder="Label (e.g., Warehouse)" style="margin-bottom: 8px;">
                        <input type="url" id="sfmsQcVendorMapLink2" placeholder="Google Maps URL">
                    </div>
                </div>
                <div class="sfms-qc-section"><i class="fas fa-shipping-fast"></i>Shipping Address (if different)</div>
                <div class="form-group">
                    <textarea id="sfmsQcVendorShipAddress" placeholder="Shipping address" rows="2"></textarea>
                </div>
                <div class="sfms-qc-grid-4">
                    <div class="form-group">
                        <label>Pincode</label>
                        <input type="text" id="sfmsQcVendorShipPincode" placeholder="6-digit PIN" maxlength="6" oninput="SFMSQuickCreate.lookupPincode(this.value, 'ship')">
                    </div>
                    <div class="form-group">
                        <label>City</label>
                        <input type="text" id="sfmsQcVendorShipCity" placeholder="City">
                    </div>
                    <div class="form-group">
                        <label>State</label>
                        <input type="text" id="sfmsQcVendorShipState" placeholder="State">
                    </div>
                    <button type="button" class="sfms-qc-pin-btn" onclick="SFMSQuickCreate.lookupPincode(document.getElementById('sfmsQcVendorShipPincode').value, 'ship')">
                        <i class="fas fa-search"></i> Lookup
                    </button>
                </div>
            </div>
            
            <!-- Bank & Payment Tab -->
            <div class="sfms-qc-tab-content" id="sfmsQcVendorTabBank">
                <div class="sfms-qc-section"><i class="fas fa-university"></i>Bank Details</div>
                <div class="sfms-qc-grid-2">
                    <div class="form-group">
                        <label>Bank Name</label>
                        <input type="text" id="sfmsQcVendorBankName" placeholder="Bank name">
                    </div>
                    <div class="form-group">
                        <label>Branch</label>
                        <input type="text" id="sfmsQcVendorBankBranch" placeholder="Branch name">
                    </div>
                </div>
                <div class="sfms-qc-grid-2">
                    <div class="form-group">
                        <label>Account Number</label>
                        <input type="text" id="sfmsQcVendorAccountNo" placeholder="Account number">
                    </div>
                    <div class="form-group">
                        <label>IFSC Code</label>
                        <input type="text" id="sfmsQcVendorIfsc" placeholder="11-character IFSC" maxlength="11">
                    </div>
                </div>
                <div class="sfms-qc-grid-2">
                    <div class="form-group">
                        <label>Account Holder Name</label>
                        <input type="text" id="sfmsQcVendorAccountHolder" placeholder="Account holder name">
                    </div>
                    <div class="form-group">
                        <label>UPI ID</label>
                        <input type="text" id="sfmsQcVendorUpiId" placeholder="e.g., vendor@upi">
                    </div>
                </div>
                <div class="sfms-qc-section"><i class="fas fa-credit-card"></i>Payment Terms</div>
                <div class="sfms-qc-grid-3">
                    <div class="form-group">
                        <label>Payment Terms</label>
                        <select id="sfmsQcVendorPaymentTerms">
                            <option value="COD">Cash on Delivery</option>
                            <option value="ADVANCE">Advance</option>
                            <option value="CREDIT_15">Credit 15 Days</option>
                            <option value="CREDIT_30">Credit 30 Days</option>
                            <option value="CREDIT_45">Credit 45 Days</option>
                            <option value="CREDIT_60">Credit 60 Days</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Credit Limit (Rs.)</label>
                        <input type="number" id="sfmsQcVendorCreditLimit" placeholder="0.00" min="0" step="0.01" value="0">
                    </div>
                    <div class="form-group">
                        <label>Credit Days</label>
                        <input type="number" id="sfmsQcVendorCreditDays" placeholder="0" min="0" max="365" value="0">
                    </div>
                </div>
                <div class="form-group">
                    <label>Terms & Conditions</label>
                    <textarea id="sfmsQcVendorTerms" placeholder="Custom terms and conditions" rows="2"></textarea>
                </div>
            </div>
            
            <!-- Products Tab -->
            <div class="sfms-qc-tab-content" id="sfmsQcVendorTabProducts">
                <div class="sfms-qc-section"><i class="fas fa-boxes"></i>Associated Products</div>
                <p class="text-muted mb-3">Search and select products this vendor supplies:</p>
                <div class="form-group mb-3">
                    <input type="text" id="sfmsQcVendorProductSearch" class="form-control" placeholder="Search products by name or code..." oninput="SFMSQuickCreate.searchVendorProducts()">
                </div>
                <div class="mb-2" id="sfmsQcVendorSelectedContainer" style="display: none;">
                    <label class="text-success fw-bold"><i class="fas fa-check-circle me-1"></i>Selected Products (<span id="sfmsQcVendorSelectedCount">0</span>)</label>
                    <div class="sfms-qc-product-list" id="sfmsQcVendorSelectedProducts" style="background: #f0fdf4; border-color: #22c55e; max-height: 100px;"></div>
                </div>
                <label class="text-muted small">Available Products</label>
                <div class="sfms-qc-product-list" id="sfmsQcVendorProductList" style="max-height: 200px;">
                    <p class="text-muted p-2">Type to search products...</p>
                </div>
            </div>
        `;
    }
    
    function switchVendorTab(tabId) {
        document.querySelectorAll('.sfms-qc-tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.sfms-qc-tab-content').forEach(c => c.classList.remove('active'));
        
        const tabMap = { basic: 'Basic', contacts: 'Contacts', address: 'Address', bank: 'Bank', products: 'Products' };
        document.querySelector(`.sfms-qc-tab:nth-child(${Object.keys(tabMap).indexOf(tabId) + 1})`).classList.add('active');
        document.getElementById(`sfmsQcVendorTab${tabMap[tabId]}`).classList.add('active');
        
        if (tabId === 'products' && stockItems.length === 0) {
            loadStockItems().then(() => searchVendorProducts());
        }
    }
    
    function open(type, prefill = {}, callback = null) {
        currentContext = { type, prefill };
        if (callback) callbacks[type] = callback;
        
        const modal = document.getElementById('sfmsQuickCreateModal');
        const title = document.getElementById('sfmsQcTitle');
        const body = document.getElementById('sfmsQcBody');
        
        let formHtml = '';
        let iconClass = '';
        let titleText = '';
        
        switch (type) {
            case 'stockitem':
                formHtml = getStockItemFormHtml(prefill);
                iconClass = 'fas fa-box';
                titleText = 'Create New Stock Item';
                break;

            case 'hsn':
                formHtml = getHsnFormHtml(prefill);
                iconClass = 'fas fa-hashtag';
                titleText = 'Create New HSN Code';
                break;
            case 'vendor':
                formHtml = getVendorFormHtml(prefill);
                iconClass = 'fas fa-truck';
                titleText = 'Create New Vendor';
                break;
            default:
                console.error('[SFMS-QC] Unknown type:', type);
                return;
        }
        
        title.innerHTML = `<i class="${iconClass} me-2"></i>${titleText}`;
        body.innerHTML = formHtml;
        modal.style.display = 'flex';
        
        if (type === 'hsn') {
            calcHsnIgst();
        }
        if (type === 'stockitem' && !prefill.code) {
            generateItemCode();
        }
        
        document.addEventListener('click', handleOutsideClick);
    }
    
    function close() {
        const modal = document.getElementById('sfmsQuickCreateModal');
        modal.style.display = 'none';
        document.removeEventListener('click', handleOutsideClick);
        vendorSelectedProducts = [];
        stockItemColors = [];
        closeHsnSubModal();
    }
    
    function handleOutsideClick(e) {
        if (!e.target.closest('#sfmsQcHsnDropdown') && !e.target.closest('#sfmsQcHsnSearch')) {
            const dropdown = document.getElementById('sfmsQcHsnDropdown');
            if (dropdown) dropdown.style.display = 'none';
        }
    }
    
    async function submit() {
        const btn = document.getElementById('sfmsQcSubmitBtn');
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Creating...';
        
        try {
            let result;
            switch (currentContext.type) {
                case 'stockitem':
                    result = await submitStockItem();
                    break;
                case 'hsn':
                    result = await submitHsn();
                    break;
                case 'vendor':
                    result = await submitVendor();
                    break;
            }
            
            if (result.success) {
                showSuccess(result.message || `${currentContext.type} created successfully!`);
                close();
                
                if (callbacks[currentContext.type]) {
                    callbacks[currentContext.type](result.data);
                }
                
                if (currentContext.type === 'hsn') await loadHsnCodes();
            } else {
                showError(result.error || 'Failed to create record');
            }
        } catch (e) {
            console.error('[SFMS-QC] Submit error:', e);
            showError('An error occurred: ' + e.message);
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-save me-1"></i>Create';
        }
    }
    
    async function submitStockItem() {
        const itemName = document.getElementById('sfmsQcItemName').value.trim();
        const itemCode = document.getElementById('sfmsQcItemCode').value.trim();
        const companies = JSON.parse(document.getElementById('sfmsQcCompanies').value || '[]');
        
        if (!itemName) return { success: false, error: 'Item name is required' };
        if (!itemCode) return { success: false, error: 'Item code is required' };
        if (companies.length === 0) return { success: false, error: 'At least one company must be selected' };
        
        const colorsData = JSON.parse(document.getElementById('sfmsQcItemColorsData').value || '[]');
        const colors = colorsData.length > 0 ? colorsData : null;
        
        const data = {
            item_name: itemName,
            item_code: itemCode.toUpperCase(),
            item_category: document.getElementById('sfmsQcItemCategory').value || 'PRODUCT',
            unit_of_measure: document.getElementById('sfmsQcItemUnit').value || 'PCS',
            applicable_companies: companies,
            description: document.getElementById('sfmsQcItemDescription').value.trim() || null,
            specification: document.getElementById('sfmsQcItemSpec').value.trim() || null,
            size: document.getElementById('sfmsQcItemSize').value.trim() || null,
            colors: colors,
            purchase_rate: parseFloat(document.getElementById('sfmsQcItemPurchaseRate').value) || 0,
            selling_rate: parseFloat(document.getElementById('sfmsQcItemSellingRate').value) || 0,
            reorder_level: parseInt(document.getElementById('sfmsQcItemReorder').value) || 10,
            hsn_id: document.getElementById('sfmsQcItemHsnId').value ? parseInt(document.getElementById('sfmsQcItemHsnId').value) : null
        };
        
        const response = await fetch(`${API_BASE}/stock-items`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${getToken()}`, 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        if (response.ok) {
            const result = await response.json();
            return { success: true, message: `Stock item "${itemName}" created`, data: result.stock_item || result };
        } else {
            const error = await response.json();
            return { success: false, error: error.detail || 'Failed to create stock item' };
        }
    }
    
    async function submitHsn() {
        const hsnCode = document.getElementById('sfmsQcHsnCode').value.trim();
        const description = document.getElementById('sfmsQcHsnDescription').value.trim();
        const effectiveFrom = document.getElementById('sfmsQcHsnEffectiveFrom').value;
        
        if (!hsnCode) return { success: false, error: 'HSN code is required' };
        if (!description) return { success: false, error: 'Description is required' };
        if (!effectiveFrom) return { success: false, error: 'Effective from date is required' };
        
        const cgstRate = parseFloat(document.getElementById('sfmsQcHsnCgst').value) || 0;
        const sgstRate = parseFloat(document.getElementById('sfmsQcHsnSgst').value) || 0;
        const igstRate = parseFloat(document.getElementById('sfmsQcHsnIgst').value) || (cgstRate + sgstRate);
        const cessRate = parseFloat(document.getElementById('sfmsQcHsnCess').value) || 0;
        const effectiveTo = document.getElementById('sfmsQcHsnEffectiveTo').value || null;
        
        const data = {
            hsn_code: hsnCode,
            description: description,
            cgst_rate: cgstRate,
            sgst_rate: sgstRate,
            igst_rate: igstRate,
            cess_rate: cessRate,
            effective_from: effectiveFrom
        };
        
        if (effectiveTo) {
            data.effective_to = effectiveTo;
        }
        
        const response = await fetch(`${API_BASE}/hsn`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${getToken()}`, 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        if (response.ok) {
            const result = await response.json();
            return { success: true, message: `HSN code "${hsnCode}" created`, data: result.hsn || result };
        } else {
            const error = await response.json();
            return { success: false, error: error.message || error.detail || 'Failed to create HSN code' };
        }
    }
    
    async function submitVendor() {
        const vendorName = document.getElementById('sfmsQcVendorName').value.trim();
        const vendorCode = document.getElementById('sfmsQcVendorCode').value.trim();
        const applicableCompanies = JSON.parse(document.getElementById('sfmsQcVendorApplicableCompanies').value || '[]');
        
        if (!vendorName) return { success: false, error: 'Vendor name is required' };
        if (!vendorCode) return { success: false, error: 'Vendor code is required' };
        if (applicableCompanies.length === 0) return { success: false, error: 'At least one company must be selected' };
        
        const data = {
            vendor_name: vendorName,
            vendor_code: vendorCode.toUpperCase(),
            vendor_type: document.getElementById('sfmsQcVendorType').value || 'BOTH',
            email: document.getElementById('sfmsQcVendorEmail').value.trim() || null,
            gst_number: document.getElementById('sfmsQcVendorGst').value.trim().toUpperCase() || null,
            pan_number: document.getElementById('sfmsQcVendorPan').value.trim().toUpperCase() || null,
            applicable_companies: applicableCompanies,
            is_active: document.getElementById('sfmsQcVendorIsActive').checked,
            
            contact_person_1_name: document.getElementById('sfmsQcVendorContact1Name').value.trim() || null,
            contact_person_1_phone: document.getElementById('sfmsQcVendorContact1Phone').value.trim() || null,
            contact_person_1_designation: document.getElementById('sfmsQcVendorContact1Designation').value.trim() || null,
            
            contact_person_2_name: document.getElementById('sfmsQcVendorContact2Name').value.trim() || null,
            contact_person_2_phone: document.getElementById('sfmsQcVendorContact2Phone').value.trim() || null,
            contact_person_2_designation: document.getElementById('sfmsQcVendorContact2Designation').value.trim() || null,
            
            website_url: document.getElementById('sfmsQcVendorWebsite').value.trim() || null,
            
            address: document.getElementById('sfmsQcVendorAddress').value.trim() || null,
            pincode: document.getElementById('sfmsQcVendorPincode').value.trim() || null,
            city: document.getElementById('sfmsQcVendorCity').value.trim() || null,
            state: document.getElementById('sfmsQcVendorState').value.trim() || null,
            
            map_link_1: document.getElementById('sfmsQcVendorMapLink1').value.trim() || null,
            map_link_1_label: document.getElementById('sfmsQcVendorMapLink1Label').value.trim() || null,
            map_link_2: document.getElementById('sfmsQcVendorMapLink2').value.trim() || null,
            map_link_2_label: document.getElementById('sfmsQcVendorMapLink2Label').value.trim() || null,
            
            ship_to_address: document.getElementById('sfmsQcVendorShipAddress').value.trim() || null,
            ship_to_pincode: document.getElementById('sfmsQcVendorShipPincode').value.trim() || null,
            ship_to_city: document.getElementById('sfmsQcVendorShipCity').value.trim() || null,
            ship_to_state: document.getElementById('sfmsQcVendorShipState').value.trim() || null,
            
            bank_name: document.getElementById('sfmsQcVendorBankName').value.trim() || null,
            bank_branch: document.getElementById('sfmsQcVendorBankBranch').value.trim() || null,
            account_number: document.getElementById('sfmsQcVendorAccountNo').value.trim() || null,
            ifsc_code: document.getElementById('sfmsQcVendorIfsc').value.trim().toUpperCase() || null,
            account_holder_name: document.getElementById('sfmsQcVendorAccountHolder').value.trim() || null,
            upi_id: document.getElementById('sfmsQcVendorUpiId').value.trim() || null,
            
            payment_terms: document.getElementById('sfmsQcVendorPaymentTerms').value || 'COD',
            credit_limit: parseFloat(document.getElementById('sfmsQcVendorCreditLimit').value) || 0,
            credit_days: parseInt(document.getElementById('sfmsQcVendorCreditDays').value) || 0,
            terms_conditions: document.getElementById('sfmsQcVendorTerms').value.trim() || null,
            
            product_ids: vendorSelectedProducts.length > 0 ? vendorSelectedProducts : null
        };
        
        const response = await fetch(`${API_BASE}/vendors`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${getToken()}`, 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        if (response.ok) {
            const result = await response.json();
            return { success: true, message: `Vendor "${vendorName}" created`, data: result.vendor || result };
        } else {
            const error = await response.json();
            return { success: false, error: error.detail || 'Failed to create vendor' };
        }
    }
    
    function addCompany() {
        const select = document.getElementById('sfmsQcCompanySelect');
        const companyId = parseInt(select.value);
        if (!companyId) return;
        
        const companiesField = document.getElementById('sfmsQcCompanies');
        const currentCompanies = JSON.parse(companiesField.value || '[]');
        
        if (currentCompanies.includes(companyId)) {
            select.value = '';
            return;
        }
        
        currentCompanies.push(companyId);
        companiesField.value = JSON.stringify(currentCompanies);
        
        const company = companies.find(c => c.id === companyId);
        if (company) {
            const badgesContainer = document.getElementById('sfmsQcCompanyBadges');
            const badge = document.createElement('span');
            badge.className = 'sfms-qc-badge';
            badge.innerHTML = `${company.company_name} <span class="remove" onclick="SFMSQuickCreate.removeCompany(${companyId})">&times;</span>`;
            badge.dataset.companyId = companyId;
            badgesContainer.appendChild(badge);
        }
        
        select.value = '';
    }
    
    function removeCompany(companyId) {
        const companiesField = document.getElementById('sfmsQcCompanies');
        let currentCompanies = JSON.parse(companiesField.value || '[]');
        currentCompanies = currentCompanies.filter(id => id !== companyId);
        companiesField.value = JSON.stringify(currentCompanies);
        
        const badge = document.querySelector(`#sfmsQcCompanyBadges span[data-company-id="${companyId}"]`);
        if (badge) badge.remove();
    }
    
    function addVendorCompany() {
        const select = document.getElementById('sfmsQcVendorCompanySelect');
        const companyId = parseInt(select.value);
        if (!companyId) return;
        
        const companiesField = document.getElementById('sfmsQcVendorApplicableCompanies');
        const currentCompanies = JSON.parse(companiesField.value || '[]');
        
        if (currentCompanies.includes(companyId)) {
            select.value = '';
            return;
        }
        
        currentCompanies.push(companyId);
        companiesField.value = JSON.stringify(currentCompanies);
        
        const company = companies.find(c => c.id === companyId);
        if (company) {
            const badgesContainer = document.getElementById('sfmsQcVendorCompanyBadges');
            const badge = document.createElement('span');
            badge.className = 'sfms-qc-badge';
            badge.innerHTML = `${company.company_name} <span class="remove" onclick="SFMSQuickCreate.removeVendorCompany(${companyId})">&times;</span>`;
            badge.dataset.companyId = companyId;
            badgesContainer.appendChild(badge);
        }
        
        select.value = '';
    }
    
    function removeVendorCompany(companyId) {
        const companiesField = document.getElementById('sfmsQcVendorApplicableCompanies');
        let currentCompanies = JSON.parse(companiesField.value || '[]');
        currentCompanies = currentCompanies.filter(id => id !== companyId);
        companiesField.value = JSON.stringify(currentCompanies);
        
        const badge = document.querySelector(`#sfmsQcVendorCompanyBadges span[data-company-id="${companyId}"]`);
        if (badge) badge.remove();
    }
    
    function searchVendorProducts() {
        const searchTerm = document.getElementById('sfmsQcVendorProductSearch').value.toLowerCase().trim();
        const listContainer = document.getElementById('sfmsQcVendorProductList');
        
        if (!searchTerm) {
            listContainer.innerHTML = '<p class="text-muted p-2">Type to search products...</p>';
            return;
        }
        
        const filtered = stockItems.filter(item => 
            (item.item_name || '').toLowerCase().includes(searchTerm) ||
            (item.item_code || '').toLowerCase().includes(searchTerm)
        ).slice(0, 20);
        
        if (filtered.length === 0) {
            listContainer.innerHTML = '<p class="text-muted p-2">No products found</p>';
            return;
        }
        
        listContainer.innerHTML = filtered.map(item => {
            const isSelected = vendorSelectedProducts.includes(item.id);
            return `
                <div class="sfms-qc-product-item ${isSelected ? 'selected' : ''}" onclick="SFMSQuickCreate.toggleVendorProduct(${item.id}, '${(item.item_name || '').replace(/'/g, "\\'")}', '${item.item_code || ''}')">
                    <span><strong>${item.item_code}</strong> - ${item.item_name}</span>
                    <i class="fas ${isSelected ? 'fa-check-circle text-success' : 'fa-plus-circle text-primary'}"></i>
                </div>
            `;
        }).join('');
    }
    
    function toggleVendorProduct(productId, name, code) {
        const index = vendorSelectedProducts.indexOf(productId);
        if (index > -1) {
            vendorSelectedProducts.splice(index, 1);
        } else {
            vendorSelectedProducts.push(productId);
        }
        
        updateVendorSelectedProducts();
        searchVendorProducts();
    }
    
    function updateVendorSelectedProducts() {
        const container = document.getElementById('sfmsQcVendorSelectedContainer');
        const listContainer = document.getElementById('sfmsQcVendorSelectedProducts');
        const countSpan = document.getElementById('sfmsQcVendorSelectedCount');
        
        if (vendorSelectedProducts.length === 0) {
            container.style.display = 'none';
            return;
        }
        
        container.style.display = 'block';
        countSpan.textContent = vendorSelectedProducts.length;
        
        const selectedItems = stockItems.filter(item => vendorSelectedProducts.includes(item.id));
        listContainer.innerHTML = selectedItems.map(item => `
            <div class="sfms-qc-product-item selected" onclick="SFMSQuickCreate.toggleVendorProduct(${item.id}, '', '')">
                <span><strong>${item.item_code}</strong> - ${item.item_name}</span>
                <i class="fas fa-times-circle text-danger"></i>
            </div>
        `).join('');
    }
    
    function showHsnDropdown() {
        const dropdown = document.getElementById('sfmsQcHsnDropdown');
        renderHsnOptions(hsnCodes);
        dropdown.style.display = 'block';
    }
    
    function filterHsn() {
        const search = document.getElementById('sfmsQcHsnSearch').value.toLowerCase().trim();
        if (search.length < 1) {
            renderHsnOptions(hsnCodes, '');
            return;
        }
        
        const filtered = hsnCodes.filter(h => 
            (h.hsn_code || '').toLowerCase().includes(search) ||
            (h.description || '').toLowerCase().includes(search)
        );
        renderHsnOptions(filtered, search);
    }
    
    function renderHsnOptions(list, searchVal = '') {
        const dropdown = document.getElementById('sfmsQcHsnDropdown');
        const selectedId = document.getElementById('sfmsQcItemHsnId').value;
        
        let html = list.slice(0, 20).map(h => {
            const gstRate = h.gst_rate || ((h.cgst_rate || 0) + (h.sgst_rate || 0));
            return `
                <div class="hsn-option ${h.id == selectedId ? 'selected' : ''}" 
                     onclick="SFMSQuickCreate.selectHsn(${h.id}, '${h.hsn_code}', '${(h.description || '').replace(/'/g, "\\'")}', ${gstRate})" 
                     style="padding: 10px 12px; cursor: pointer; border-bottom: 1px solid #f3f4f6; ${h.id == selectedId ? 'background: #ede9fe;' : ''}"
                     onmouseover="this.style.background='#f3f4f6'" onmouseout="this.style.background='${h.id == selectedId ? '#ede9fe' : ''}'">
                    <span style="font-size: 11px; color: #8b5cf6; float: right;">${gstRate}%</span>
                    <div style="font-weight: 600; color: #1f2937;">${h.hsn_code}</div>
                    <div style="font-size: 12px; color: #6b7280; margin-top: 2px;">${h.description || ''}</div>
                </div>
            `;
        }).join('');
        
        html += `
            <div class="hsn-option create-new" onclick="SFMSQuickCreate.openHsnSubModal('${searchVal}')"
                 style="padding: 10px 12px; cursor: pointer; background: #f0fdf4; color: #059669; font-weight: 600; border-top: 2px solid #d1fae5;"
                 onmouseover="this.style.background='#dcfce7'" onmouseout="this.style.background='#f0fdf4'">
                <i class="fas fa-plus-circle me-2"></i>Create New HSN Code${searchVal ? `: "${searchVal}"` : ''}
            </div>
        `;
        
        dropdown.innerHTML = html;
        dropdown.style.display = 'block';
    }
    
    function openHsnSubModal(prefillCode = '') {
        document.getElementById('sfmsQcHsnDropdown').style.display = 'none';
        
        let subModal = document.getElementById('sfmsQcHsnSubModal');
        if (!subModal) {
            const subModalHtml = `
                <div class="sub-modal" id="sfmsQcHsnSubModal" style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.6); display: none; align-items: center; justify-content: center; z-index: 1100;">
                    <div class="sub-modal-content" style="background: white; border-radius: 12px; max-width: 500px; width: 90%; max-height: 80vh; overflow-y: auto;">
                        <div class="sub-modal-header" style="padding: 16px 20px; border-bottom: 1px solid #e5e7eb; display: flex; justify-content: space-between; align-items: center; background: #f0fdf4; border-radius: 12px 12px 0 0;">
                            <h4 style="font-size: 16px; font-weight: 600; color: #059669; margin: 0;"><i class="fas fa-plus-circle me-2"></i>Create New HSN Code</h4>
                            <button class="modal-close" onclick="SFMSQuickCreate.closeHsnSubModal()" style="background: none; border: none; font-size: 20px; cursor: pointer;">&times;</button>
                        </div>
                        <div class="sub-modal-body" style="padding: 20px;">
                            <div class="form-group" style="margin-bottom: 16px;">
                                <label for="sfmsQcSubHsnCode" style="display: block; font-size: 13px; font-weight: 600; color: #374151; margin-bottom: 6px;">HSN/SAC Code *</label>
                                <input type="text" id="sfmsQcSubHsnCode" placeholder="e.g., 8507, 9403" maxlength="20" style="width: 100%; padding: 10px 12px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 14px;">
                            </div>
                            <div class="form-group" style="margin-bottom: 16px;">
                                <label for="sfmsQcSubHsnDescription" style="display: block; font-size: 13px; font-weight: 600; color: #374151; margin-bottom: 6px;">Description *</label>
                                <input type="text" id="sfmsQcSubHsnDescription" placeholder="e.g., Electric Batteries" style="width: 100%; padding: 10px 12px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 14px;">
                            </div>
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                                <div class="form-group" style="margin-bottom: 16px;">
                                    <label for="sfmsQcSubHsnGstRate" style="display: block; font-size: 13px; font-weight: 600; color: #374151; margin-bottom: 6px;">GST Rate (%)</label>
                                    <select id="sfmsQcSubHsnGstRate" style="width: 100%; padding: 10px 12px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 14px;">
                                        <option value="0">0%</option>
                                        <option value="5">5%</option>
                                        <option value="12">12%</option>
                                        <option value="18" selected>18%</option>
                                        <option value="28">28%</option>
                                    </select>
                                </div>
                                <div class="form-group" style="margin-bottom: 16px;">
                                    <label for="sfmsQcSubHsnType" style="display: block; font-size: 13px; font-weight: 600; color: #374151; margin-bottom: 6px;">Type</label>
                                    <select id="sfmsQcSubHsnType" style="width: 100%; padding: 10px 12px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 14px;">
                                        <option value="HSN" selected>HSN (Goods)</option>
                                        <option value="SAC">SAC (Services)</option>
                                    </select>
                                </div>
                            </div>
                            <div class="form-group" style="margin-bottom: 16px;">
                                <label for="sfmsQcSubHsnCess" style="display: block; font-size: 13px; font-weight: 600; color: #374151; margin-bottom: 6px;">Cess Rate (%) <small style="color: #9ca3af;">Optional</small></label>
                                <input type="number" id="sfmsQcSubHsnCess" step="0.01" min="0" value="0" placeholder="0" style="width: 100%; padding: 10px 12px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 14px;">
                            </div>
                        </div>
                        <div class="sub-modal-footer" style="padding: 12px 20px; border-top: 1px solid #e5e7eb; display: flex; justify-content: flex-end; gap: 10px;">
                            <button type="button" class="btn btn-secondary btn-sm" onclick="SFMSQuickCreate.closeHsnSubModal()">Cancel</button>
                            <button type="button" class="btn btn-success btn-sm" onclick="SFMSQuickCreate.quickCreateHsnFromSubModal()"><i class="fas fa-check me-1"></i>Create & Select</button>
                        </div>
                    </div>
                </div>
            `;
            const container = document.createElement('div');
            container.innerHTML = subModalHtml;
            document.body.appendChild(container.firstElementChild);
            subModal = document.getElementById('sfmsQcHsnSubModal');
        }
        
        document.getElementById('sfmsQcSubHsnCode').value = prefillCode;
        document.getElementById('sfmsQcSubHsnDescription').value = '';
        document.getElementById('sfmsQcSubHsnGstRate').value = '18';
        document.getElementById('sfmsQcSubHsnType').value = 'HSN';
        document.getElementById('sfmsQcSubHsnCess').value = '0';
        subModal.style.display = 'flex';
    }
    
    function closeHsnSubModal() {
        const subModal = document.getElementById('sfmsQcHsnSubModal');
        if (subModal) subModal.style.display = 'none';
    }
    
    async function quickCreateHsnFromSubModal() {
        const code = document.getElementById('sfmsQcSubHsnCode').value.trim();
        const description = document.getElementById('sfmsQcSubHsnDescription').value.trim();
        const gstRate = parseFloat(document.getElementById('sfmsQcSubHsnGstRate').value) || 18;
        const hsnType = document.getElementById('sfmsQcSubHsnType').value || 'HSN';
        const cessRate = parseFloat(document.getElementById('sfmsQcSubHsnCess').value) || 0;
        
        if (!code || !description) {
            alert('HSN code and description are required');
            return;
        }
        
        try {
            const response = await fetch(`${API_BASE}/hsn`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${getToken()}`, 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    hsn_code: code,
                    description: description,
                    cgst_rate: gstRate / 2,
                    sgst_rate: gstRate / 2,
                    igst_rate: gstRate,
                    cess_rate: cessRate,
                    effective_from: new Date().toISOString().split('T')[0]
                })
            });
            
            if (response.ok) {
                const result = await response.json();
                const newHsn = result.hsn || result;
                
                await loadHsnCodes();
                
                if (newHsn.id) {
                    selectHsn(newHsn.id, newHsn.hsn_code, newHsn.description, gstRate);
                }
                
                closeHsnSubModal();
                showSuccess('HSN code created successfully!');
            } else {
                const error = await response.json();
                alert(error.message || error.detail || 'Failed to create HSN code');
            }
        } catch (e) {
            console.error('[SFMS-QC] HSN create error:', e);
            alert('Failed to create HSN code: ' + e.message);
        }
    }
    
    function selectHsn(id, code, description, gstRate) {
        document.getElementById('sfmsQcItemHsnId').value = id;
        document.getElementById('sfmsQcHsnSearch').value = '';
        document.getElementById('sfmsQcHsnDropdown').style.display = 'none';
        
        const gstRateField = document.getElementById('sfmsQcItemGstRate');
        if (gstRateField) {
            gstRateField.value = gstRate + '%';
        }
        
        document.getElementById('sfmsQcHsnSelected').innerHTML = `
            <span style="background: #dbeafe; padding: 4px 8px; border-radius: 4px; font-size: 13px;">
                <strong>${code}</strong> - ${description} (${gstRate}%)
                <span onclick="SFMSQuickCreate.clearHsn()" style="cursor: pointer; margin-left: 6px;">&times;</span>
            </span>
        `;
    }
    
    function clearHsn() {
        document.getElementById('sfmsQcItemHsnId').value = '';
        document.getElementById('sfmsQcHsnSelected').innerHTML = '';
        const gstRateField = document.getElementById('sfmsQcItemGstRate');
        if (gstRateField) gstRateField.value = '';
    }
    
    function calcHsnIgst() {
        const cgst = parseFloat(document.getElementById('sfmsQcHsnCgst').value) || 0;
        const sgst = parseFloat(document.getElementById('sfmsQcHsnSgst').value) || 0;
        const igstField = document.getElementById('sfmsQcHsnIgst');
        const totalGstSpan = document.getElementById('sfmsQcHsnTotalGst');
        
        const total = cgst + sgst;
        igstField.value = total;
        if (totalGstSpan) {
            totalGstSpan.textContent = total + '%';
        }
    }
    
    async function lookupPincode(pincode, addressType) {
        if (!pincode || pincode.length !== 6) return;
        
        try {
            const response = await fetch(`${API_BASE}/pincode-lookup/${pincode}`, {
                headers: { 'Authorization': `Bearer ${getToken()}` }
            });
            if (response.ok) {
                const data = await response.json();
                if (addressType === 'primary') {
                    if (data.city) document.getElementById('sfmsQcVendorCity').value = data.city;
                    if (data.state) document.getElementById('sfmsQcVendorState').value = data.state;
                } else if (addressType === 'ship') {
                    if (data.city) document.getElementById('sfmsQcVendorShipCity').value = data.city;
                    if (data.state) document.getElementById('sfmsQcVendorShipState').value = data.state;
                }
            }
        } catch (e) { console.log('[SFMS-QC] Pincode lookup failed:', e); }
    }
    
    function showSuccess(msg) {
        const toast = document.createElement('div');
        toast.className = 'position-fixed top-0 end-0 p-3';
        toast.style.zIndex = '10000';
        toast.innerHTML = `<div class="alert alert-success alert-dismissible fade show" role="alert">${msg}<button type="button" class="btn-close" data-bs-dismiss="alert"></button></div>`;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 4000);
    }
    
    function showError(msg) {
        const toast = document.createElement('div');
        toast.className = 'position-fixed top-0 end-0 p-3';
        toast.style.zIndex = '10000';
        toast.innerHTML = `<div class="alert alert-danger alert-dismissible fade show" role="alert">${msg}<button type="button" class="btn-close" data-bs-dismiss="alert"></button></div>`;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 5000);
    }
    
    function setCallback(type, callback) {
        callbacks[type] = callback;
    }
    
    function getCompanies() { return companies; }
    function getHsnCodes() { return hsnCodes; }
    function getStockItems() { return stockItems; }
    async function refreshHsnCodes() { return await loadHsnCodes(); }
    async function refreshCompanies() { return await loadCompanies(); }
    async function refreshStockItems() { return await loadStockItems(); }

    async function generateItemCode() {
        const catEl = document.getElementById('sfmsQcItemCategory');
        const codeEl = document.getElementById('sfmsQcItemCode');
        if (!catEl || !codeEl) return;
        const cat = catEl.value || 'PRODUCT';
        const prev = codeEl.placeholder;
        codeEl.placeholder = 'Generating...';
        try {
            const res = await fetch(`${API_BASE}/stock-items/generate-code?category=${encodeURIComponent(cat)}`, {
                headers: { 'Authorization': `Bearer ${getToken()}` }
            });
            if (res.ok) {
                const d = await res.json();
                if (d.item_code) codeEl.value = d.item_code;
            }
        } catch (_) {}
        codeEl.placeholder = prev || 'Auto-generated...';
    }
    
    return {
        init,
        open,
        close,
        submit,
        generateItemCode,
        addCompany,
        removeCompany,
        addVendorCompany,
        removeVendorCompany,
        addStockItemColor,
        removeStockItemColor,
        switchVendorTab,
        searchVendorProducts,
        toggleVendorProduct,
        showHsnDropdown,
        filterHsn,
        selectHsn,
        clearHsn,
        openHsnSubModal,
        closeHsnSubModal,
        quickCreateHsnFromSubModal,
        calcHsnIgst,
        lookupPincode,
        setCallback,
        getCompanies,
        getHsnCodes,
        getStockItems,
        refreshHsnCodes,
        refreshCompanies,
        refreshStockItems
    };
})();

if (typeof module !== 'undefined' && module.exports) {
    module.exports = SFMSQuickCreate;
}
