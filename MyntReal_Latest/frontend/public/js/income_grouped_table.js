/**
 * Income Grouped Table Component - DC Protocol Compliant
 * 
 * Provides date-wise + user-wise grouping for income approval pages
 * with expandable transaction details and bulk approve/reject
 * 
 * Usage:
 *   const table = new IncomeGroupedTable(config);
 *   table.render(incomes);
 */

// DC Protocol Feb 2026: Map database income types to rebranded display names
function getIncomeDisplayName(dbIncomeType) {
    const rebrandMap = {
        'Direct Referral': 'Direct Facilitation',
        'Matching Referral': 'Group Performance Recognition',
        'Ved Income': 'VED Leadership Recognition',
        'Guru Dakshina': 'Mentorship Contribution Benefit'
    };
    return rebrandMap[dbIncomeType] || dbIncomeType;
}

class IncomeGroupedTable {
    constructor(config) {
        this.config = {
            containerId: config.containerId || 'tableContent',
            allowSelection: config.allowSelection !== false, // default true
            statusFilter: config.statusFilter || null, // e.g., 'Pending', 'Super Admin Verified'
            onSelectionChange: config.onSelectionChange || function() {},
            onApprove: config.onApprove || null,
            onReject: config.onReject || null,
            enableUngroup: config.enableUngroup !== false, // default true
            columns: config.columns || ['user_id', 'name', 'date', 'package', 'gross', 'deductions', 'net', 'status']
        };
        
        this.allIncomes = [];
        this.selectedIncomeIds = new Set();
        this.isGroupedView = true; // default to grouped view
    }

    /**
     * Aggregate incomes by user_id + business_date
     * DC Protocol: One transaction per user per day
     * CRITICAL: Use API-provided deductions, NOT hard-coded percentages
     */
    aggregateUserWise(incomes) {
        const aggregated = {};
        
        incomes.forEach(income => {
            const key = `${income.user_id}_${income.business_date}`;
            
            if (!aggregated[key]) {
                aggregated[key] = {
                    user_id: income.user_id,
                    user_name: income.user_name,
                    business_date: income.business_date,
                    package_type: income.package_type,
                    verification_status: income.verification_status,
                    gross_amount: 0,
                    total_deductions: 0,  // DC Protocol: Use actual deductions from API
                    net_amount: 0,
                    details: [],
                    income_ids: []
                };
            }
            
            const grossAmt = parseFloat(income.gross_amount || 0);
            const netAmt = parseFloat(income.net_amount || 0);
            const deductions = grossAmt - netAmt;  // DC Protocol: Calculate from API values
            
            aggregated[key].gross_amount += grossAmt;
            aggregated[key].total_deductions += deductions;
            aggregated[key].net_amount += netAmt;
            aggregated[key].details.push({
                id: income.id,
                income_type: income.income_type,
                gross_amount: grossAmt,
                deductions: deductions,  // DC Protocol: Actual deduction from API
                net_amount: netAmt,
                admin_notes: income.admin_notes || ''
            });
            aggregated[key].income_ids.push(income.id);
        });
        
        return Object.values(aggregated);
    }

    /**
     * Render table with current view mode (grouped or ungrouped)
     */
    render(incomes) {
        this.allIncomes = incomes;
        
        if (this.isGroupedView) {
            this.renderGroupedView();
        } else {
            this.renderUngroupedView();
        }
    }

    /**
     * Render grouped view (date + user aggregation)
     */
    renderGroupedView() {
        const container = document.getElementById(this.config.containerId);
        
        if (this.allIncomes.length === 0) {
            container.innerHTML = `
                <div style="text-align: center; padding: 40px;">
                    <i class="fas fa-inbox" style="font-size: 48px; color: #d97706;"></i>
                    <h5 class="mt-3">No Income Records Found</h5>
                    <p>No incomes match your current filters.</p>
                </div>
            `;
            return;
        }

        const aggregatedRecords = this.aggregateUserWise(this.allIncomes);
        console.log('📊 Aggregated records:', aggregatedRecords.length, 'user-day transactions');

        let tableHTML = `
            <div style="margin-bottom: 15px; display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <span style="color: #666;">Showing ${aggregatedRecords.length} grouped transactions</span>
                </div>
                ${this.config.enableUngroup ? `
                <button class="btn btn-sm btn-outline-secondary" onclick="incomeTable.toggleGrouping()">
                    <i class="fas fa-list"></i> Show Individual Records
                </button>
                ` : ''}
            </div>
            <table class="table table-hover" id="incomeTable">
                <thead style="background: #fffbeb;">
                    <tr>
                        ${this.config.allowSelection ? '<th style="width: 50px;"><input type="checkbox" class="form-check-input" id="selectAll" onchange="incomeTable.toggleSelectAll()"></th>' : ''}
                        <th style="width: 50px;"></th>
                        <th>User ID</th>
                        <th>Name</th>
                        <th>Income Date</th>
                        <th>Package</th>
                        <th>Gross Amount</th>
                        <th>Deductions (12%)</th>
                        <th>Net Amount</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
        `;

        aggregatedRecords.forEach((record, index) => {
            const grossAmount = record.gross_amount;
            const deductions = record.total_deductions;  // DC Protocol: Use actual deductions from API
            const netAmount = record.net_amount;
            const status = record.verification_status || 'Unknown';
            const rowId = `row_${index}`;
            
            const allSelected = record.income_ids.every(id => this.selectedIncomeIds.has(id));
            const isProcessed = status === 'Completed' || status === 'Rejected';
            
            const statusBadge = this.getStatusBadge(status);

            tableHTML += `
                <tr id="${rowId}" style="${isProcessed ? 'background: #f0fdf4;' : ''}" class="user-row">
                    ${this.config.allowSelection ? `
                    <td>
                        <input type="checkbox" class="form-check-input user-checkbox" 
                            data-income-ids='${JSON.stringify(record.income_ids)}'
                            ${allSelected ? 'checked' : ''}
                            ${isProcessed ? 'disabled title="Already processed"' : ''}
                            onchange="incomeTable.toggleUserSelection(this)">
                    </td>
                    ` : ''}
                    <td>
                        <button class="btn btn-sm btn-link expand-btn" onclick="incomeTable.toggleDetails('${rowId}')" title="View breakdown by type">
                            <i class="fas fa-plus-circle" style="color: #d97706; font-size: 18px;"></i>
                        </button>
                    </td>
                    <td><strong>${record.user_id || 'N/A'}</strong></td>
                    <td>${record.user_name || 'N/A'}</td>
                    <td>${this.formatDate(record.business_date)}</td>
                    <td>${record.package_type || 'N/A'}</td>
                    <td>₹${grossAmount.toFixed(2)}</td>
                    <td>₹${deductions.toFixed(2)}</td>
                    <td><strong style="color: #d97706;">₹${netAmount.toFixed(2)}</strong></td>
                    <td>${statusBadge}</td>
                </tr>
            `;

            // Details row (hidden by default)
            tableHTML += `
                <tr id="${rowId}_details" class="details-row" style="display: none; background: #fffbeb;">
                    <td colspan="${this.config.allowSelection ? 10 : 9}" style="padding: 20px;">
                        <div style="margin-left: 40px;">
                            <h6 style="color: #d97706; margin-bottom: 15px;"><i class="fas fa-list"></i> Income Type Breakdown</h6>
                            <table class="table table-sm table-bordered" style="max-width: 700px;">
                                <thead style="background: #fef3c7;">
                                    <tr>
                                        <th>Income Type</th>
                                        <th>Gross Amount</th>
                                        <th>Deductions</th>
                                        <th>Net Amount</th>
                                        <th>Notes</th>
                                    </tr>
                                </thead>
                                <tbody>
            `;

            // DC Protocol: Use actual deductions from API, not hard-coded 12%
            record.details.forEach(detail => {
                tableHTML += `
                    <tr>
                        <td><strong>${getIncomeDisplayName(detail.income_type)}</strong></td>
                        <td>₹${detail.gross_amount.toFixed(2)}</td>
                        <td>₹${detail.deductions.toFixed(2)}</td>
                        <td>₹${detail.net_amount.toFixed(2)}</td>
                        <td>${detail.admin_notes || '-'}</td>
                    </tr>
                `;
            });

            tableHTML += `
                                </tbody>
                            </table>
                        </div>
                    </td>
                </tr>
            `;
        });

        tableHTML += `
                </tbody>
            </table>
        `;

        container.innerHTML = tableHTML;
    }

    /**
     * Render ungrouped view (individual records)
     */
    renderUngroupedView() {
        const container = document.getElementById(this.config.containerId);
        
        if (this.allIncomes.length === 0) {
            container.innerHTML = `
                <div style="text-align: center; padding: 40px;">
                    <i class="fas fa-inbox" style="font-size: 48px; color: #d97706;"></i>
                    <h5 class="mt-3">No Income Records Found</h5>
                    <p>No incomes match your current filters.</p>
                </div>
            `;
            return;
        }

        let tableHTML = `
            <div style="margin-bottom: 15px; display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <span style="color: #666;">Showing ${this.allIncomes.length} individual records</span>
                </div>
                <button class="btn btn-sm btn-outline-secondary" onclick="incomeTable.toggleGrouping()">
                    <i class="fas fa-layer-group"></i> Show Grouped View
                </button>
            </div>
            <table class="table table-hover" id="incomeTable">
                <thead style="background: #fffbeb;">
                    <tr>
                        ${this.config.allowSelection ? '<th style="width: 50px;"><input type="checkbox" class="form-check-input" id="selectAll" onchange="incomeTable.toggleSelectAll()"></th>' : ''}
                        <th>User ID</th>
                        <th>Name</th>
                        <th>Income Type</th>
                        <th>Income Date</th>
                        <th>Package</th>
                        <th>Gross Amount</th>
                        <th>Deductions (12%)</th>
                        <th>Net Amount</th>
                        <th>Status</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
        `;

        this.allIncomes.forEach((income) => {
            const grossAmount = parseFloat(income.gross_amount || 0);
            const deductions = grossAmount * 0.12;
            const netAmount = parseFloat(income.net_amount || 0);
            const status = income.verification_status || 'Unknown';
            
            const isSelected = this.selectedIncomeIds.has(income.id);
            const isProcessed = status === 'Completed' || status === 'Rejected';
            
            const statusBadge = this.getStatusBadge(status);

            tableHTML += `
                <tr style="${isProcessed ? 'background: #f0fdf4;' : ''}">
                    ${this.config.allowSelection ? `
                    <td>
                        <input type="checkbox" class="form-check-input income-checkbox" 
                            data-income-id="${income.id}"
                            ${isSelected ? 'checked' : ''}
                            ${isProcessed ? 'disabled' : ''}
                            onchange="incomeTable.toggleIndividualSelection(this)">
                    </td>
                    ` : ''}
                    <td><strong>${income.user_id || 'N/A'}</strong></td>
                    <td>${income.user_name || 'N/A'}</td>
                    <td>${getIncomeDisplayName(income.income_type) || 'N/A'}</td>
                    <td>${this.formatDate(income.business_date)}</td>
                    <td>${income.package_type || 'N/A'}</td>
                    <td>₹${grossAmount.toFixed(2)}</td>
                    <td>₹${deductions.toFixed(2)}</td>
                    <td><strong style="color: #d97706;">₹${netAmount.toFixed(2)}</strong></td>
                    <td>${statusBadge}</td>
                    <td>
                        <button class="btn btn-sm btn-info" onclick="incomeTable.viewDetails(${income.id})" title="View Details">
                            <i class="fas fa-eye"></i>
                        </button>
                    </td>
                </tr>
            `;
        });

        tableHTML += `
                </tbody>
            </table>
        `;

        container.innerHTML = tableHTML;
    }

    /**
     * Get status badge HTML
     */
    getStatusBadge(status) {
        const badges = {
            'Pending': '<span class="badge" style="background: #f59e0b; color: white;">⏳ Pending Admin</span>',
            'Admin Verified': '<span class="badge" style="background: #3b82f6; color: white;">👔 Admin Verified</span>',
            'Super Admin Verified': '<span class="badge" style="background: #f59e0b; color: white;">⏳ Pending Finance</span>',
            'Completed': '<span class="badge" style="background: #10b981; color: white;">✅ Completed</span>',
            'Rejected': '<span class="badge" style="background: #dc2626; color: white;">❌ Rejected</span>'
        };
        
        return badges[status] || `<span class="badge bg-secondary">${status}</span>`;
    }

    /**
     * Toggle grouped/ungrouped view
     */
    toggleGrouping() {
        this.isGroupedView = !this.isGroupedView;
        this.render(this.allIncomes);
    }

    /**
     * Toggle expand/collapse for grouped details
     */
    toggleDetails(rowId) {
        const detailsRow = document.getElementById(rowId + '_details');
        const btn = document.querySelector(`#${rowId} .expand-btn i`);
        
        if (detailsRow.style.display === 'none') {
            detailsRow.style.display = 'table-row';
            btn.classList.remove('fa-plus-circle');
            btn.classList.add('fa-minus-circle');
        } else {
            detailsRow.style.display = 'none';
            btn.classList.remove('fa-minus-circle');
            btn.classList.add('fa-plus-circle');
        }
    }

    /**
     * Toggle user selection (grouped view)
     */
    toggleUserSelection(checkbox) {
        const incomeIds = JSON.parse(checkbox.dataset.incomeIds);
        
        if (checkbox.checked) {
            incomeIds.forEach(id => this.selectedIncomeIds.add(id));
        } else {
            incomeIds.forEach(id => this.selectedIncomeIds.delete(id));
        }
        
        this.config.onSelectionChange(this.selectedIncomeIds);
    }

    /**
     * Toggle individual selection (ungrouped view)
     */
    toggleIndividualSelection(checkbox) {
        const incomeId = parseInt(checkbox.dataset.incomeId);
        
        if (checkbox.checked) {
            this.selectedIncomeIds.add(incomeId);
        } else {
            this.selectedIncomeIds.delete(incomeId);
        }
        
        this.config.onSelectionChange(this.selectedIncomeIds);
    }

    /**
     * Toggle select all
     */
    toggleSelectAll() {
        const selectAllCheckbox = document.getElementById('selectAll');
        const checkboxes = document.querySelectorAll('.user-checkbox, .income-checkbox');
        
        checkboxes.forEach(checkbox => {
            if (!checkbox.disabled) {
                checkbox.checked = selectAllCheckbox.checked;
                
                if (this.isGroupedView) {
                    this.toggleUserSelection(checkbox);
                } else {
                    this.toggleIndividualSelection(checkbox);
                }
            }
        });
    }

    /**
     * View income details in modal
     */
    viewDetails(incomeId) {
        const income = this.allIncomes.find(inc => inc.id == incomeId);
        if (!income) {
            alert('Income not found');
            return;
        }
        
        const statusBadge = this.getStatusBadge(income.verification_status);
        
        const detailsHTML = `
            <div style="padding: 20px;">
                <h5 style="color: #d97706; margin-bottom: 20px;">Income Details</h5>
                
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <strong>User ID:</strong><br>${income.user_id || 'N/A'}
                    </div>
                    <div class="col-md-6 mb-3">
                        <strong>User Name:</strong><br>${income.user_name || 'N/A'}
                    </div>
                </div>
                
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <strong>Income Type:</strong><br>${getIncomeDisplayName(income.income_type) || 'N/A'}
                    </div>
                    <div class="col-md-6 mb-3">
                        <strong>Package:</strong><br>${income.package_type || 'N/A'}
                    </div>
                </div>
                
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <strong>Business Date:</strong><br>${this.formatDate(income.business_date)}
                    </div>
                    <div class="col-md-6 mb-3">
                        <strong>Status:</strong><br>${statusBadge}
                    </div>
                </div>
                
                <hr>
                
                <div class="row">
                    <div class="col-md-4 mb-3">
                        <strong>Gross Amount:</strong><br>
                        <span style="font-size: 20px; color: #059669;">₹${parseFloat(income.gross_amount || 0).toFixed(2)}</span>
                    </div>
                    <div class="col-md-4 mb-3">
                        <strong>Deductions (12%):</strong><br>
                        <span style="font-size: 20px; color: #dc2626;">₹${(parseFloat(income.gross_amount || 0) * 0.12).toFixed(2)}</span>
                    </div>
                    <div class="col-md-4 mb-3">
                        <strong>Net Amount:</strong><br>
                        <span style="font-size: 24px; font-weight: bold; color: #d97706;">₹${parseFloat(income.net_amount || 0).toFixed(2)}</span>
                    </div>
                </div>
                
                ${income.admin_notes ? `<hr><div class="mb-3"><strong>Admin Notes:</strong><br>${income.admin_notes}</div>` : ''}
                ${income.notes ? `<div class="mb-3"><strong>Notes:</strong><br>${income.notes}</div>` : ''}
                
                <div style="margin-top: 20px; text-align: right;">
                    <button class="btn btn-secondary" onclick="incomeTable.closeModal()">Close</button>
                </div>
            </div>
        `;
        
        let modal = document.getElementById('incomeDetailsModal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'incomeDetailsModal';
            modal.style.cssText = 'position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 9999; display: flex; align-items: center; justify-content: center;';
            document.body.appendChild(modal);
        }
        
        modal.innerHTML = `
            <div style="background: white; border-radius: 12px; max-width: 800px; width: 90%; max-height: 90vh; overflow-y: auto; box-shadow: 0 10px 40px rgba(0,0,0,0.3);">
                ${detailsHTML}
            </div>
        `;
        modal.style.display = 'flex';
    }

    closeModal() {
        const modal = document.getElementById('incomeDetailsModal');
        if (modal) {
            modal.style.display = 'none';
        }
    }

    /**
     * Clear all selections
     */
    clearSelections() {
        this.selectedIncomeIds.clear();
        this.render(this.allIncomes);
    }

    /**
     * Get selected income IDs
     */
    getSelectedIds() {
        return Array.from(this.selectedIncomeIds);
    }

    /**
     * Format date helper
     */
    formatDate(dateStr) {
        if (!dateStr) return 'N/A';
        const date = new Date(dateStr);
        return date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
    }
}
