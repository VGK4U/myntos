(async function() {
    const API_BASE = '/api/v1';
    const invoicesBody = document.getElementById('invoicesBody');
    const companyFilter = document.getElementById('companyFilter');
    const createInvoiceBtn = document.getElementById('createInvoiceBtn');

    async function fetchWithAuth(url, options = {}) {
        const response = await fetch(url, {
            ...options,
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        });
        return response;
    }

    async function loadCompanies() {
        try {
            const response = await fetchWithAuth(`${API_BASE}/staff/payroll/companies`);
            if (response.ok) {
                const data = await response.json();
                const companies = data.companies || [];
                companies.forEach(company => {
                    const option = document.createElement('option');
                    option.value = company.id;
                    option.textContent = company.name;
                    companyFilter.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Error loading companies:', error);
        }
    }

    async function loadInvoices() {
        invoicesBody.innerHTML = '<tr><td colspan="9" class="text-center"><i class="fas fa-spinner fa-spin"></i> Loading...</td></tr>';
        
        try {
            let url = `${API_BASE}/staff/payroll/consultant-invoices`;
            if (companyFilter.value) {
                url += `?company_id=${companyFilter.value}`;
            }
            
            const response = await fetchWithAuth(url);
            if (!response.ok) throw new Error('Failed to load invoices');
            
            const data = await response.json();
            const invoices = data.data || [];
            
            if (invoices.length === 0) {
                invoicesBody.innerHTML = '<tr><td colspan="9" class="text-center text-muted">No consultant invoices found</td></tr>';
                return;
            }
            
            const statusBadges = {
                'DRAFT': 'bg-secondary',
                'SUBMITTED': 'bg-warning text-dark',
                'VALIDATED': 'bg-info',
                'APPROVED': 'bg-success',
                'REJECTED': 'bg-danger',
                'PAID': 'bg-primary',
                'CANCELLED': 'bg-danger'
            };
            
            invoicesBody.innerHTML = invoices.map(inv => `
                <tr>
                    <td><code>${inv.invoice_number}</code></td>
                    <td>${inv.employee_name || 'N/A'}</td>
                    <td>${inv.service_period_from} to ${inv.service_period_to}</td>
                    <td>₹${(inv.invoice_amount || 0).toLocaleString('en-IN')}</td>
                    <td>₹${(inv.gst_amount || 0).toLocaleString('en-IN')}</td>
                    <td>₹${(inv.tds_amount || 0).toLocaleString('en-IN')}</td>
                    <td class="fw-bold">₹${(inv.net_payable || 0).toLocaleString('en-IN')}</td>
                    <td><span class="badge ${statusBadges[inv.status] || 'bg-secondary'}">${inv.status}</span></td>
                    <td>
                        <button class="btn btn-sm btn-outline-primary" onclick="viewInvoice(${inv.id})">
                            <i class="fas fa-eye"></i>
                        </button>
                        ${inv.status === 'DRAFT' ? `
                            <button class="btn btn-sm btn-outline-success" onclick="submitInvoice(${inv.id})">
                                <i class="fas fa-paper-plane"></i>
                            </button>
                        ` : ''}
                        ${inv.status === 'SUBMITTED' ? `
                            <button class="btn btn-sm btn-success" onclick="approveInvoice(${inv.id})">
                                <i class="fas fa-check"></i>
                            </button>
                        ` : ''}
                    </td>
                </tr>
            `).join('');
        } catch (error) {
            console.error('Error loading invoices:', error);
            invoicesBody.innerHTML = `<tr><td colspan="9" class="text-center text-danger">Error: ${error.message}</td></tr>`;
        }
    }

    window.viewInvoice = async function(id) {
        try {
            const response = await fetchWithAuth(`${API_BASE}/staff/payroll/consultant-invoices/${id}`);
            if (!response.ok) throw new Error('Failed to load invoice');
            
            const result = await response.json();
            const inv = result.data;
            
            const statusBadges = {
                'DRAFT': 'bg-secondary',
                'SUBMITTED': 'bg-warning text-dark',
                'VALIDATED': 'bg-info',
                'APPROVED': 'bg-success',
                'REJECTED': 'bg-danger',
                'PAID': 'bg-primary',
                'CANCELLED': 'bg-danger'
            };
            
            const modalHtml = `
                <div class="modal fade" id="invoiceViewModal" tabindex="-1">
                    <div class="modal-dialog modal-lg">
                        <div class="modal-content">
                            <div class="modal-header bg-primary text-white">
                                <h5 class="modal-title"><i class="fas fa-file-invoice me-2"></i>Consultant Invoice Details</h5>
                                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body">
                                <div class="row mb-3">
                                    <div class="col-md-4">
                                        <small class="text-muted">Invoice Number</small><br>
                                        <strong><code>${inv.invoice_number}</code></strong>
                                    </div>
                                    <div class="col-md-4">
                                        <small class="text-muted">Consultant</small><br>
                                        <strong>${inv.employee_name || 'N/A'}</strong>
                                    </div>
                                    <div class="col-md-4">
                                        <small class="text-muted">Status</small><br>
                                        <span class="badge ${statusBadges[inv.status] || 'bg-secondary'}">${inv.status}</span>
                                    </div>
                                </div>
                                <div class="row mb-3">
                                    <div class="col-md-6">
                                        <small class="text-muted">Service Period</small><br>
                                        <strong>${inv.service_period_from || 'N/A'} to ${inv.service_period_to || 'N/A'}</strong>
                                    </div>
                                    <div class="col-md-6">
                                        <small class="text-muted">Invoice Date</small><br>
                                        <strong>${inv.invoice_date || 'N/A'}</strong>
                                    </div>
                                </div>
                                <hr>
                                <h6>Financial Details</h6>
                                <table class="table table-sm">
                                    <tr><td>Invoice Amount</td><td class="text-end">₹${(inv.invoice_amount || 0).toLocaleString('en-IN')}</td></tr>
                                    <tr><td>GST Amount</td><td class="text-end">₹${(inv.gst_amount || 0).toLocaleString('en-IN')}</td></tr>
                                    <tr class="text-danger"><td>TDS Deduction</td><td class="text-end">-₹${(inv.tds_amount || 0).toLocaleString('en-IN')}</td></tr>
                                    <tr class="table-success"><td><strong>Net Payable</strong></td><td class="text-end"><strong>₹${(inv.net_payable || 0).toLocaleString('en-IN')}</strong></td></tr>
                                </table>
                                ${inv.remarks ? `<div class="alert alert-info mt-2"><strong>Remarks:</strong> ${inv.remarks}</div>` : ''}
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            const existingModal = document.getElementById('invoiceViewModal');
            if (existingModal) existingModal.remove();
            
            document.body.insertAdjacentHTML('beforeend', modalHtml);
            const modal = new bootstrap.Modal(document.getElementById('invoiceViewModal'));
            modal.show();
        } catch (error) {
            alert('Error: ' + error.message);
        }
    };

    window.submitInvoice = async function(id) {
        if (!confirm('Submit this invoice for approval?')) return;
        try {
            const response = await fetchWithAuth(`${API_BASE}/staff/payroll/consultant-invoices/${id}/submit`, {
                method: 'POST'
            });
            if (response.ok) {
                alert('Invoice submitted successfully');
                loadInvoices();
            } else {
                const data = await response.json();
                alert('Error: ' + (data.detail || 'Failed to submit'));
            }
        } catch (error) {
            alert('Error: ' + error.message);
        }
    };

    window.approveInvoice = async function(id) {
        if (!confirm('Approve this invoice?')) return;
        try {
            const response = await fetchWithAuth(`${API_BASE}/staff/payroll/consultant-invoices/${id}/approve`, {
                method: 'POST'
            });
            if (response.ok) {
                alert('Invoice approved successfully');
                loadInvoices();
            } else {
                const data = await response.json();
                alert('Error: ' + (data.detail || 'Failed to approve'));
            }
        } catch (error) {
            alert('Error: ' + error.message);
        }
    };

    window.createInvoice = async function() {
        try {
            const [companiesRes, employeesRes] = await Promise.all([
                fetchWithAuth(`${API_BASE}/staff/payroll/companies`),
                fetchWithAuth(`${API_BASE}/staff/employees/list?employment_type=OFFROLE`)
            ]);
            
            const companies = companiesRes.ok ? (await companiesRes.json()).companies || [] : [];
            const employees = employeesRes.ok ? (await employeesRes.json()).data || [] : [];
            
            const companyOptions = companies.map(c => `<option value="${c.id}">${c.name}</option>`).join('');
            const employeeOptions = employees.map(e => `<option value="${e.id}">${e.full_name} (${e.emp_code || 'N/A'})</option>`).join('');
            
            const today = new Date().toISOString().split('T')[0];
            
            const modalHtml = `
                <div class="modal fade" id="invoiceCreateModal" tabindex="-1">
                    <div class="modal-dialog modal-lg">
                        <div class="modal-content">
                            <div class="modal-header bg-success text-white">
                                <h5 class="modal-title"><i class="fas fa-plus me-2"></i>Create Consultant Invoice</h5>
                                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                            </div>
                            <form id="createInvoiceForm">
                                <div class="modal-body">
                                    <div class="row mb-3">
                                        <div class="col-md-6">
                                            <label class="form-label">Consultant <span class="text-danger">*</span></label>
                                            <select class="form-select" name="employee_id" required>
                                                <option value="">Select Consultant</option>
                                                ${employeeOptions}
                                            </select>
                                        </div>
                                        <div class="col-md-6">
                                            <label class="form-label">Company <span class="text-danger">*</span></label>
                                            <select class="form-select" name="company_id" required>
                                                <option value="">Select Company</option>
                                                ${companyOptions}
                                            </select>
                                        </div>
                                    </div>
                                    <div class="row mb-3">
                                        <div class="col-md-4">
                                            <label class="form-label">Invoice Date <span class="text-danger">*</span></label>
                                            <input type="date" class="form-control" name="invoice_date" value="${today}" required>
                                        </div>
                                        <div class="col-md-4">
                                            <label class="form-label">Service Period From <span class="text-danger">*</span></label>
                                            <input type="date" class="form-control" name="service_period_from" required>
                                        </div>
                                        <div class="col-md-4">
                                            <label class="form-label">Service Period To <span class="text-danger">*</span></label>
                                            <input type="date" class="form-control" name="service_period_to" required>
                                        </div>
                                    </div>
                                    <div class="row mb-3">
                                        <div class="col-md-4">
                                            <label class="form-label">Invoice Amount (₹) <span class="text-danger">*</span></label>
                                            <input type="number" class="form-control" name="invoice_amount" required min="0" step="0.01">
                                        </div>
                                        <div class="col-md-4">
                                            <label class="form-label">GST Rate (%)</label>
                                            <input type="number" class="form-control" name="gst_rate" value="18" min="0" max="28" step="0.01">
                                        </div>
                                        <div class="col-md-4">
                                            <label class="form-label">TDS Rate (%)</label>
                                            <input type="number" class="form-control" name="tds_rate" value="10" min="0" max="30" step="0.01">
                                        </div>
                                    </div>
                                    <div class="mb-3">
                                        <label class="form-label">Remarks</label>
                                        <textarea class="form-control" name="remarks" rows="2"></textarea>
                                    </div>
                                </div>
                                <div class="modal-footer">
                                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                                    <button type="submit" class="btn btn-success"><i class="fas fa-plus me-1"></i> Create Invoice</button>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
            `;
            
            const existingModal = document.getElementById('invoiceCreateModal');
            if (existingModal) existingModal.remove();
            
            document.body.insertAdjacentHTML('beforeend', modalHtml);
            
            document.getElementById('createInvoiceForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                const formData = new FormData(e.target);
                const payload = {
                    employee_id: parseInt(formData.get('employee_id')),
                    company_id: parseInt(formData.get('company_id')),
                    invoice_date: formData.get('invoice_date'),
                    service_period_from: formData.get('service_period_from'),
                    service_period_to: formData.get('service_period_to'),
                    invoice_amount: parseFloat(formData.get('invoice_amount')) || 0,
                    gst_rate: parseFloat(formData.get('gst_rate')) || 0,
                    tds_rate: parseFloat(formData.get('tds_rate')) || 0,
                    remarks: formData.get('remarks') || null
                };
                
                try {
                    const res = await fetchWithAuth(`${API_BASE}/staff/payroll/consultant-invoices`, {
                        method: 'POST',
                        body: JSON.stringify(payload)
                    });
                    
                    if (res.ok) {
                        bootstrap.Modal.getInstance(document.getElementById('invoiceCreateModal')).hide();
                        alert('Invoice created successfully');
                        loadInvoices();
                    } else {
                        const err = await res.json();
                        alert('Error: ' + (err.detail || 'Failed to create invoice'));
                    }
                } catch (err) {
                    alert('Error: ' + err.message);
                }
            });
            
            const modal = new bootstrap.Modal(document.getElementById('invoiceCreateModal'));
            modal.show();
        } catch (error) {
            alert('Error: ' + error.message);
        }
    };

    if (createInvoiceBtn) {
        createInvoiceBtn.addEventListener('click', createInvoice);
    }

    if (companyFilter) {
        companyFilter.addEventListener('change', loadInvoices);
    }

    await loadCompanies();
    await loadInvoices();
})();
