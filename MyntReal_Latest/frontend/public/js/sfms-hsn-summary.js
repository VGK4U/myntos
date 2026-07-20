/**
 * SFMS HSN Summary Component
 * DC Protocol Compliant - HSN-wise tax breakdown for Purchase and Sales Invoices
 * Displays: HSN/SAC, Taxable Value, CGST (Rate + Amount), SGST (Rate + Amount), Total Tax Amount
 * Version: 1.0.0
 */

const SFMSHsnSummary = (function() {
    'use strict';
    
    function calculateHsnSummary(lineItems, isIgst = false) {
        const hsnMap = {};
        
        lineItems.forEach(item => {
            const hsnCode = item.hsn_code || item.hsnCode || 'N/A';
            const taxableValue = parseFloat(item.taxable_value || item.taxableValue || item.amount || 0);
            const gstRate = parseFloat(item.gst_rate || item.gstRate || 18);
            const taxAmount = parseFloat(item.tax_amount || item.taxAmount || (taxableValue * gstRate / 100));
            
            if (!hsnMap[hsnCode]) {
                hsnMap[hsnCode] = {
                    hsn_code: hsnCode,
                    taxable_value: 0,
                    gst_rate: gstRate,
                    cgst_rate: gstRate / 2,
                    sgst_rate: gstRate / 2,
                    igst_rate: gstRate,
                    cgst_amount: 0,
                    sgst_amount: 0,
                    igst_amount: 0,
                    total_tax: 0
                };
            }
            
            hsnMap[hsnCode].taxable_value += taxableValue;
            
            if (isIgst) {
                hsnMap[hsnCode].igst_amount += taxAmount;
            } else {
                hsnMap[hsnCode].cgst_amount += taxAmount / 2;
                hsnMap[hsnCode].sgst_amount += taxAmount / 2;
            }
            hsnMap[hsnCode].total_tax += taxAmount;
        });
        
        return Object.values(hsnMap).sort((a, b) => a.hsn_code.localeCompare(b.hsn_code));
    }
    
    function formatCurrency(amount) {
        return new Intl.NumberFormat('en-IN', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(amount || 0);
    }
    
    function renderTable(containerId, lineItems, isIgst = false) {
        const container = document.getElementById(containerId);
        if (!container) {
            console.error('[SFMS-HSN] Container not found:', containerId);
            return;
        }
        
        const summary = calculateHsnSummary(lineItems, isIgst);
        
        if (summary.length === 0) {
            container.innerHTML = `
                <div style="padding: 20px; text-align: center; color: #6b7280;">
                    <i class="fas fa-info-circle me-2"></i>No HSN data available
                </div>
            `;
            return;
        }
        
        let totalTaxable = 0, totalCgst = 0, totalSgst = 0, totalIgst = 0, grandTotalTax = 0;
        
        let tableHtml = `
            <table class="table table-bordered table-sm" style="font-size: 13px; margin-bottom: 0;">
                <thead style="background: #f8fafc;">
                    <tr>
                        <th style="text-align: left; padding: 10px;">HSN/SAC</th>
                        <th style="text-align: right; padding: 10px;">Taxable Value</th>
                        ${isIgst ? `
                            <th style="text-align: center; padding: 10px;" colspan="2">IGST</th>
                        ` : `
                            <th style="text-align: center; padding: 10px;" colspan="2">CGST</th>
                            <th style="text-align: center; padding: 10px;" colspan="2">SGST</th>
                        `}
                        <th style="text-align: right; padding: 10px;">Total Tax Amount</th>
                    </tr>
                    <tr style="background: #f1f5f9; font-size: 11px;">
                        <th></th>
                        <th></th>
                        ${isIgst ? `
                            <th style="text-align: center; padding: 6px;">Rate</th>
                            <th style="text-align: right; padding: 6px;">Amount</th>
                        ` : `
                            <th style="text-align: center; padding: 6px;">Rate</th>
                            <th style="text-align: right; padding: 6px;">Amount</th>
                            <th style="text-align: center; padding: 6px;">Rate</th>
                            <th style="text-align: right; padding: 6px;">Amount</th>
                        `}
                        <th></th>
                    </tr>
                </thead>
                <tbody>
        `;
        
        summary.forEach(row => {
            totalTaxable += row.taxable_value;
            totalCgst += row.cgst_amount;
            totalSgst += row.sgst_amount;
            totalIgst += row.igst_amount;
            grandTotalTax += row.total_tax;
            
            tableHtml += `
                <tr>
                    <td style="padding: 8px; font-weight: 500;">${row.hsn_code}</td>
                    <td style="text-align: right; padding: 8px;">${formatCurrency(row.taxable_value)}</td>
                    ${isIgst ? `
                        <td style="text-align: center; padding: 8px;">${row.igst_rate}%</td>
                        <td style="text-align: right; padding: 8px;">${formatCurrency(row.igst_amount)}</td>
                    ` : `
                        <td style="text-align: center; padding: 8px;">${row.cgst_rate}%</td>
                        <td style="text-align: right; padding: 8px;">${formatCurrency(row.cgst_amount)}</td>
                        <td style="text-align: center; padding: 8px;">${row.sgst_rate}%</td>
                        <td style="text-align: right; padding: 8px;">${formatCurrency(row.sgst_amount)}</td>
                    `}
                    <td style="text-align: right; padding: 8px; font-weight: 600;">₹ ${formatCurrency(row.total_tax)}</td>
                </tr>
            `;
        });
        
        tableHtml += `
                </tbody>
                <tfoot style="background: #e2e8f0; font-weight: 600;">
                    <tr>
                        <td style="padding: 10px;">Total</td>
                        <td style="text-align: right; padding: 10px;">${formatCurrency(totalTaxable)}</td>
                        ${isIgst ? `
                            <td style="text-align: center; padding: 10px;">-</td>
                            <td style="text-align: right; padding: 10px;">${formatCurrency(totalIgst)}</td>
                        ` : `
                            <td style="text-align: center; padding: 10px;">-</td>
                            <td style="text-align: right; padding: 10px;">${formatCurrency(totalCgst)}</td>
                            <td style="text-align: center; padding: 10px;">-</td>
                            <td style="text-align: right; padding: 10px;">${formatCurrency(totalSgst)}</td>
                        `}
                        <td style="text-align: right; padding: 10px;">₹ ${formatCurrency(grandTotalTax)}</td>
                    </tr>
                </tfoot>
            </table>
        `;
        
        container.innerHTML = tableHtml;
    }
    
    function createSummarySection(title = 'HSN Code-wise Tax Summary') {
        return `
            <div class="hsn-summary-section" style="margin-top: 24px; border: 1px solid #e5e7eb; border-radius: 8px; overflow: hidden;">
                <div style="background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%); color: white; padding: 12px 16px; font-weight: 600;">
                    <i class="fas fa-file-invoice-dollar me-2"></i>${title}
                </div>
                <div id="hsnSummaryContent" style="padding: 0;"></div>
            </div>
        `;
    }
    
    function injectSummarySection(parentId, title) {
        const parent = document.getElementById(parentId);
        if (!parent) return null;
        
        const section = document.createElement('div');
        section.innerHTML = createSummarySection(title);
        parent.appendChild(section);
        
        return 'hsnSummaryContent';
    }
    
    function extractLineItemsFromDOM(tableBodyId) {
        const tbody = document.getElementById(tableBodyId);
        if (!tbody) return [];
        
        const rows = tbody.querySelectorAll('tr');
        const items = [];
        
        rows.forEach(row => {
            const hsnSelect = row.querySelector('.hsn-select, .hsn-code, [class*="hsn"]');
            const amountCell = row.querySelector('.amount, .taxable-amount, [class*="amount"]');
            const gstInput = row.querySelector('.gst-rate, .gst-input, [class*="gst"]');
            const taxCell = row.querySelector('.tax-amount, [class*="tax"]');
            
            let hsnCode = 'N/A';
            if (hsnSelect) {
                if (hsnSelect.tagName === 'SELECT') {
                    const selectedOption = hsnSelect.options[hsnSelect.selectedIndex];
                    hsnCode = selectedOption?.dataset?.code || selectedOption?.textContent?.split(' ')[0] || 'N/A';
                } else {
                    hsnCode = hsnSelect.value || hsnSelect.textContent || 'N/A';
                }
            }
            
            const taxableValue = parseFloat(amountCell?.value || amountCell?.textContent?.replace(/[₹,]/g, '') || 0);
            const gstRate = parseFloat(gstInput?.value || 18);
            const taxAmount = parseFloat(taxCell?.value || taxCell?.textContent?.replace(/[₹,]/g, '') || (taxableValue * gstRate / 100));
            
            if (taxableValue > 0) {
                items.push({
                    hsn_code: hsnCode,
                    taxable_value: taxableValue,
                    gst_rate: gstRate,
                    tax_amount: taxAmount
                });
            }
        });
        
        return items;
    }
    
    function getDataForExport(lineItems, isIgst = false) {
        return calculateHsnSummary(lineItems, isIgst);
    }
    
    return {
        calculateHsnSummary,
        renderTable,
        createSummarySection,
        injectSummarySection,
        extractLineItemsFromDOM,
        getDataForExport,
        formatCurrency
    };
})();

if (typeof module !== 'undefined' && module.exports) {
    module.exports = SFMSHsnSummary;
}
