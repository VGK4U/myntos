(async function() {
    const API_BASE = '/api/v1';
    const documentsBody = document.getElementById('documentsBody');
    const companyFilter = document.getElementById('companyFilter');
    const documentTypeFilter = document.getElementById('documentTypeFilter');
    const totalDocs = document.getElementById('totalDocs');
    const payslipCount = document.getElementById('payslipCount');
    const offerLetterCount = document.getElementById('offerLetterCount');
    const otherDocsCount = document.getElementById('otherDocsCount');

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

    async function loadEmployees() {
        const employeeFilter = document.getElementById('employeeFilter');
        if (!employeeFilter) return;
        
        try {
            const response = await fetchWithAuth(`${API_BASE}/staff/employees?limit=100`);
            if (response.ok) {
                const data = await response.json();
                const employees = data.employees || data.data || [];
                employees.forEach(emp => {
                    const option = document.createElement('option');
                    option.value = emp.id;
                    option.textContent = `${emp.full_name || emp.first_name} (${emp.emp_code})`;
                    employeeFilter.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Error loading employees:', error);
        }
    }

    async function loadDocuments() {
        documentsBody.innerHTML = '<tr><td colspan="8" class="text-center"><i class="fas fa-spinner fa-spin"></i> Loading...</td></tr>';
        
        try {
            let url = `${API_BASE}/staff/payroll/documents?limit=100`;
            
            if (companyFilter && companyFilter.value) {
                url += `&company_id=${companyFilter.value}`;
            }
            if (documentTypeFilter && documentTypeFilter.value) {
                url += `&document_type=${documentTypeFilter.value}`;
            }
            
            const employeeFilter = document.getElementById('employeeFilter');
            if (employeeFilter && employeeFilter.value) {
                url += `&employee_id=${employeeFilter.value}`;
            }
            
            const searchInput = document.getElementById('searchInput');
            if (searchInput && searchInput.value.trim()) {
                url += `&search=${encodeURIComponent(searchInput.value.trim())}`;
            }
            
            const monthFilter = document.getElementById('monthFilter');
            if (monthFilter && monthFilter.value) {
                url += `&month=${monthFilter.value}`;
            }
            
            const yearFilter = document.getElementById('yearFilter');
            if (yearFilter && yearFilter.value) {
                url += `&year=${yearFilter.value}`;
            }
            
            const dateFromFilter = document.getElementById('dateFromFilter');
            if (dateFromFilter && dateFromFilter.value) {
                url += `&date_from=${dateFromFilter.value}`;
            }
            
            const dateToFilter = document.getElementById('dateToFilter');
            if (dateToFilter && dateToFilter.value) {
                url += `&date_to=${dateToFilter.value}`;
            }
            
            const response = await fetchWithAuth(url);
            if (!response.ok) throw new Error('Failed to load documents');
            
            const data = await response.json();
            const documents = data.data || [];
            
            let payslips = 0, offers = 0, others = 0;
            documents.forEach(doc => {
                if (doc.document_type === 'PAYSLIP') payslips++;
                else if (doc.document_type === 'OFFER_LETTER') offers++;
                else others++;
            });
            
            if (totalDocs) totalDocs.textContent = documents.length;
            if (payslipCount) payslipCount.textContent = payslips;
            if (offerLetterCount) offerLetterCount.textContent = offers;
            if (otherDocsCount) otherDocsCount.textContent = others;
            
            if (documents.length === 0) {
                documentsBody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">No documents found</td></tr>';
                return;
            }
            
            documentsBody.innerHTML = documents.map(doc => `
                <tr>
                    <td><code class="text-primary">${doc.document_code}</code></td>
                    <td><span class="badge ${getTypeBadgeClass(doc.document_type)}">${formatDocType(doc.document_type)}</span></td>
                    <td>
                        <strong>${doc.employee_name || 'N/A'}</strong>
                        <br><small class="text-muted">${doc.employee_code || ''}</small>
                        ${doc.department ? `<br><small class="text-info">${doc.department}</small>` : ''}
                    </td>
                    <td>${doc.company_name || 'N/A'}</td>
                    <td>${doc.document_title || 'N/A'}</td>
                    <td>${doc.document_date || 'N/A'}</td>
                    <td class="text-center">${doc.download_count || 0}</td>
                    <td>
                        <button class="btn btn-sm btn-primary me-1" onclick="viewDocument(${doc.id})" title="View">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button class="btn btn-sm btn-success" onclick="downloadDocument(${doc.id})" title="Download PDF">
                            <i class="fas fa-download"></i>
                        </button>
                    </td>
                </tr>
            `).join('');
        } catch (error) {
            console.error('Error loading documents:', error);
            documentsBody.innerHTML = `<tr><td colspan="8" class="text-center text-danger">Error: ${error.message}</td></tr>`;
        }
    }

    function getTypeBadgeClass(type) {
        const classes = {
            'PAYSLIP': 'bg-success',
            'OFFER_LETTER': 'bg-info',
            'SALARY_CERTIFICATE': 'bg-primary',
            'FORM_16': 'bg-warning text-dark'
        };
        return classes[type] || 'bg-secondary';
    }

    function formatDocType(type) {
        const labels = {
            'PAYSLIP': 'Payslip',
            'OFFER_LETTER': 'Offer Letter',
            'SALARY_CERTIFICATE': 'Salary Certificate',
            'FORM_16': 'Form 16'
        };
        return labels[type] || type;
    }

    function formatCurrency(amount) {
        if (amount === null || amount === undefined) return '0.00';
        return parseFloat(amount).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    function formatDate(dateStr) {
        if (!dateStr) return 'N/A';
        const date = new Date(dateStr);
        return date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
    }

    function getMonthName(monthNum) {
        const months = ['', 'January', 'February', 'March', 'April', 'May', 'June', 
                       'July', 'August', 'September', 'October', 'November', 'December'];
        return months[monthNum] || '';
    }

    window.viewDocument = async function(id) {
        try {
            const response = await fetchWithAuth(`${API_BASE}/staff/payroll/documents/${id}`);
            if (!response.ok) throw new Error('Failed to load document');
            
            const result = await response.json();
            const doc = result.data;
            
            let detailsHtml = '';
            
            if (doc.document_type === 'PAYSLIP') {
                detailsHtml = buildPayslipHtml(doc);
            } else if (doc.document_type === 'OFFER_LETTER') {
                detailsHtml = buildOfferLetterHtml(doc);
            } else {
                detailsHtml = `<p class="text-muted">Document preview not available for this type.</p>`;
            }
            
            const modalHtml = `
                <div class="modal fade" id="docViewModal" tabindex="-1">
                    <div class="modal-dialog modal-xl">
                        <div class="modal-content">
                            <div class="modal-header bg-primary text-white">
                                <h5 class="modal-title"><i class="fas fa-file-alt me-2"></i>${doc.document_title}</h5>
                                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body p-0">
                                ${detailsHtml}
                            </div>
                            <div class="modal-footer bg-light">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                                    <i class="fas fa-times me-1"></i> Close
                                </button>
                                <button type="button" class="btn btn-success" onclick="downloadDocument(${doc.id})" data-bs-dismiss="modal">
                                    <i class="fas fa-download me-1"></i> Download PDF
                                </button>
                                <button type="button" class="btn btn-primary" onclick="printPayslip()">
                                    <i class="fas fa-print me-1"></i> Print
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            const existingModal = document.getElementById('docViewModal');
            if (existingModal) existingModal.remove();
            
            document.body.insertAdjacentHTML('beforeend', modalHtml);
            const modal = new bootstrap.Modal(document.getElementById('docViewModal'));
            modal.show();
        } catch (error) {
            alert('Error: ' + error.message);
        }
    };

    function buildPayslipHtml(doc) {
        const company = doc.company || {};
        const employee = doc.employee || {};
        const payroll = doc.payroll || {};
        const period = payroll.period || {};
        const attendance = payroll.attendance || {};
        const earnings = payroll.earnings || {};
        const deductions = payroll.deductions || {};
        const summary = payroll.summary || {};
        const templateData = doc.template_data || {};

        const periodMonth = period.month || templateData.month_num || '';
        const periodYear = period.year || templateData.year || '';
        const monthName = getMonthName(periodMonth);

        const logoHtml = company.logo_url 
            ? `<img src="${company.logo_url}" alt="${company.name}" style="max-height: 60px; max-width: 150px;" onerror="this.style.display='none'">`
            : '';

        const companyAddress = [company.address, company.city, company.state, company.pincode]
            .filter(Boolean).join(', ');

        const basicPay = earnings.basic || templateData.basic_pay || 0;
        const hra = earnings.hra || templateData.hra || 0;
        const specialAllowance = earnings.special_allowance || templateData.special_allowance || 0;
        const otherEarnings = earnings.other_earnings || {};
        const grossPay = earnings.gross || templateData.gross_earnings || 0;

        const pfDeduction = deductions.pf || templateData.pf_deduction || 0;
        const esiDeduction = deductions.esi || templateData.esi_deduction || 0;
        const ptDeduction = deductions.pt || templateData.pt_deduction || 0;
        const tdsDeduction = deductions.tds || templateData.tds_deduction || 0;
        const totalDeductions = deductions.total || templateData.total_deductions || 0;

        const netPay = summary.net_pay || templateData.net_pay || 0;
        const netPayFormatted = summary.net_pay_formatted || formatCurrency(netPay);
        const netPayWords = summary.net_pay_words || `Rupees ${netPay} Only`;

        const eligibleDays = attendance.eligible_days || templateData.days_in_month || 0;
        const presentDays = attendance.present_days || templateData.days_worked || 0;
        const lopDays = attendance.lop_days || 0;
        const leaveDays = attendance.leave_days || 0;
        const paidDays = attendance.paid_days || presentDays;

        let otherEarningsHtml = '';
        if (typeof otherEarnings === 'object') {
            for (const [key, value] of Object.entries(otherEarnings)) {
                if (value && parseFloat(value) > 0) {
                    otherEarningsHtml += `<tr><td>${key}</td><td class="text-end">${formatCurrency(value)}</td></tr>`;
                }
            }
        }

        return `
            <div id="payslipContent" class="payslip-container" style="padding: 30px; background: #fff;">
                <!-- Company Header -->
                <div class="payslip-header" style="border-bottom: 3px solid #667eea; padding-bottom: 20px; margin-bottom: 20px;">
                    <div class="row align-items-center">
                        <div class="col-md-2 text-center">
                            ${logoHtml}
                        </div>
                        <div class="col-md-7">
                            <h3 class="mb-1" style="color: #667eea; font-weight: 700;">${company.name || 'Company Name'}</h3>
                            ${companyAddress ? `<p class="mb-0 text-muted small">${companyAddress}</p>` : ''}
                            ${company.gst_number ? `<small class="text-muted">GSTIN: ${company.gst_number}</small>` : ''}
                        </div>
                        <div class="col-md-3 text-end">
                            <div class="bg-primary text-white px-3 py-2 rounded">
                                <h5 class="mb-0">PAYSLIP</h5>
                                <small>${monthName} ${periodYear}</small>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Employee & Period Details -->
                <div class="row mb-4">
                    <div class="col-md-6">
                        <div class="card border-0 bg-light">
                            <div class="card-body py-2">
                                <h6 class="card-title text-primary mb-2"><i class="fas fa-user me-1"></i> Employee Details</h6>
                                <table class="table table-sm table-borderless mb-0">
                                    <tr><td class="text-muted" style="width:40%">Name</td><td><strong>${employee.name || doc.employee_name || 'N/A'}</strong></td></tr>
                                    <tr><td class="text-muted">Employee Code</td><td>${employee.code || doc.employee_code || 'N/A'}</td></tr>
                                    <tr><td class="text-muted">Department</td><td>${employee.department || 'N/A'}</td></tr>
                                    <tr><td class="text-muted">Designation</td><td>${employee.designation || 'N/A'}</td></tr>
                                    ${employee.pan_number ? `<tr><td class="text-muted">PAN</td><td>${employee.pan_number}</td></tr>` : ''}
                                    ${employee.uan_number ? `<tr><td class="text-muted">UAN</td><td>${employee.uan_number}</td></tr>` : ''}
                                </table>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="card border-0 bg-light">
                            <div class="card-body py-2">
                                <h6 class="card-title text-primary mb-2"><i class="fas fa-calendar me-1"></i> Pay Period & Attendance</h6>
                                <table class="table table-sm table-borderless mb-0">
                                    <tr><td class="text-muted" style="width:40%">Pay Period</td><td>${formatDate(period.start_date)} - ${formatDate(period.end_date)}</td></tr>
                                    <tr><td class="text-muted">Pay Date</td><td>${formatDate(period.pay_date)}</td></tr>
                                    <tr><td class="text-muted">Days in Month</td><td>${eligibleDays}</td></tr>
                                    <tr><td class="text-muted">Days Present</td><td><span class="badge bg-success">${presentDays}</span></td></tr>
                                    ${leaveDays > 0 ? `<tr><td class="text-muted">Leave Days</td><td><span class="badge bg-info">${leaveDays}</span></td></tr>` : ''}
                                    ${lopDays > 0 ? `<tr><td class="text-muted">LOP Days</td><td><span class="badge bg-danger">${lopDays}</span></td></tr>` : ''}
                                    <tr><td class="text-muted">Paid Days</td><td><strong>${paidDays}</strong></td></tr>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Earnings & Deductions -->
                <div class="row mb-4">
                    <div class="col-md-6">
                        <div class="card border-success">
                            <div class="card-header bg-success text-white py-2">
                                <h6 class="mb-0"><i class="fas fa-plus-circle me-1"></i> Earnings</h6>
                            </div>
                            <div class="card-body p-0">
                                <table class="table table-sm mb-0">
                                    <thead class="table-light">
                                        <tr><th>Component</th><th class="text-end">Amount (₹)</th></tr>
                                    </thead>
                                    <tbody>
                                        <tr><td>Basic Pay</td><td class="text-end">${formatCurrency(basicPay)}</td></tr>
                                        <tr><td>House Rent Allowance (HRA)</td><td class="text-end">${formatCurrency(hra)}</td></tr>
                                        <tr><td>Special Allowance</td><td class="text-end">${formatCurrency(specialAllowance)}</td></tr>
                                        ${otherEarningsHtml}
                                    </tbody>
                                    <tfoot class="table-success">
                                        <tr><th>Gross Earnings</th><th class="text-end">₹ ${formatCurrency(grossPay)}</th></tr>
                                    </tfoot>
                                </table>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="card border-danger">
                            <div class="card-header bg-danger text-white py-2">
                                <h6 class="mb-0"><i class="fas fa-minus-circle me-1"></i> Deductions</h6>
                            </div>
                            <div class="card-body p-0">
                                <table class="table table-sm mb-0">
                                    <thead class="table-light">
                                        <tr><th>Component</th><th class="text-end">Amount (₹)</th></tr>
                                    </thead>
                                    <tbody>
                                        <tr><td>Provident Fund (PF)</td><td class="text-end">${formatCurrency(pfDeduction)}</td></tr>
                                        <tr><td>Employee State Insurance (ESI)</td><td class="text-end">${formatCurrency(esiDeduction)}</td></tr>
                                        <tr><td>Professional Tax (PT)</td><td class="text-end">${formatCurrency(ptDeduction)}</td></tr>
                                        <tr><td>Tax Deducted at Source (TDS)</td><td class="text-end">${formatCurrency(tdsDeduction)}</td></tr>
                                    </tbody>
                                    <tfoot class="table-danger">
                                        <tr><th>Total Deductions</th><th class="text-end">₹ ${formatCurrency(totalDeductions)}</th></tr>
                                    </tfoot>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Net Pay Section -->
                <div class="card mb-4" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
                    <div class="card-body text-white text-center py-4">
                        <h5 class="mb-2">NET PAY</h5>
                        <h2 class="mb-2" style="font-size: 2.5rem; font-weight: 700;">₹ ${netPayFormatted}</h2>
                        <p class="mb-0 small" style="opacity: 0.9;">${netPayWords}</p>
                    </div>
                </div>

                <!-- Bank Details -->
                ${employee.bank_name ? `
                <div class="row mb-4">
                    <div class="col-12">
                        <div class="card bg-light border-0">
                            <div class="card-body py-2">
                                <h6 class="text-muted mb-2"><i class="fas fa-university me-1"></i> Payment Details</h6>
                                <div class="row">
                                    <div class="col-md-4"><small class="text-muted">Bank Name:</small> <strong>${employee.bank_name}</strong></div>
                                    ${employee.account_number ? `<div class="col-md-4"><small class="text-muted">Account No:</small> <strong>XXXX${employee.account_number}</strong></div>` : ''}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                ` : ''}

                <!-- Footer / Disclaimer -->
                <div class="text-center mt-4 pt-3" style="border-top: 1px solid #dee2e6;">
                    <p class="text-muted small mb-1">
                        <i class="fas fa-info-circle me-1"></i>
                        This is a computer-generated document and does not require a signature.
                    </p>
                    <p class="text-muted small mb-0">
                        Document Code: ${doc.document_code} | Generated on: ${doc.generated_at || new Date().toISOString()}
                    </p>
                </div>
            </div>
        `;
    }

    function buildOfferLetterHtml(doc) {
        const templateData = doc.template_data || {};
        const company = doc.company || {};
        
        return `
            <div class="p-4">
                <div class="text-center mb-4">
                    ${company.logo_url ? `<img src="${company.logo_url}" alt="${company.name}" style="max-height: 80px;" onerror="this.style.display='none'">` : ''}
                    <h3 class="mt-3">${templateData.company_name || company.name || 'Company'}</h3>
                    <h5 class="text-muted">OFFER LETTER</h5>
                </div>
                <table class="table table-bordered">
                    <tr><td class="bg-light" width="30%">Company</td><td>${templateData.company_name || 'N/A'}</td></tr>
                    <tr><td class="bg-light">Designation</td><td>${templateData.designation || 'N/A'}</td></tr>
                    <tr><td class="bg-light">Department</td><td>${templateData.department || 'N/A'}</td></tr>
                    <tr><td class="bg-light">Joining Date</td><td>${templateData.joining_date || 'N/A'}</td></tr>
                    <tr><td class="bg-light">Employment Type</td><td>${templateData.employment_type || 'N/A'}</td></tr>
                    <tr><td class="bg-light">CTC</td><td>₹ ${formatCurrency(templateData.ctc || 0)}</td></tr>
                </table>
            </div>
        `;
    }

    window.printPayslip = function() {
        const content = document.getElementById('payslipContent');
        if (!content) return;
        
        const printWindow = window.open('', '_blank');
        printWindow.document.write(`
            <!DOCTYPE html>
            <html>
            <head>
                <title>Payslip</title>
                <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
                <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
                <style>
                    body { padding: 20px; }
                    @media print { .no-print { display: none; } }
                </style>
            </head>
            <body>
                ${content.outerHTML}
                <script>window.onload = function() { window.print(); window.close(); }</script>
            </body>
            </html>
        `);
        printWindow.document.close();
    };

    window.downloadDocument = async function(id) {
        try {
            const pdfUrl = `${API_BASE}/staff/payroll/documents/${id}/pdf`;
            
            const response = await fetch(pdfUrl, {
                credentials: 'include'
            });
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || 'Failed to download PDF');
            }
            
            const blob = await response.blob();
            const contentDisposition = response.headers.get('Content-Disposition');
            let filename = 'document.pdf';
            if (contentDisposition) {
                const match = contentDisposition.match(/filename=([^;]+)/);
                if (match) filename = match[1].replace(/"/g, '');
            }
            
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            
            loadDocuments();
        } catch (error) {
            alert('Error: ' + error.message);
        }
    };

    window.clearFilters = function() {
        if (companyFilter) companyFilter.value = '';
        if (documentTypeFilter) documentTypeFilter.value = '';
        
        const employeeFilter = document.getElementById('employeeFilter');
        if (employeeFilter) employeeFilter.value = '';
        
        const searchInput = document.getElementById('searchInput');
        if (searchInput) searchInput.value = '';
        
        const monthFilter = document.getElementById('monthFilter');
        if (monthFilter) monthFilter.value = '';
        
        const yearFilter = document.getElementById('yearFilter');
        if (yearFilter) yearFilter.value = '';
        
        const dateFromFilter = document.getElementById('dateFromFilter');
        if (dateFromFilter) dateFromFilter.value = '';
        
        const dateToFilter = document.getElementById('dateToFilter');
        if (dateToFilter) dateToFilter.value = '';
        
        loadDocuments();
    };

    if (companyFilter) {
        companyFilter.addEventListener('change', loadDocuments);
    }
    if (documentTypeFilter) {
        documentTypeFilter.addEventListener('change', loadDocuments);
    }
    
    const employeeFilter = document.getElementById('employeeFilter');
    if (employeeFilter) {
        employeeFilter.addEventListener('change', loadDocuments);
    }
    
    const monthFilter = document.getElementById('monthFilter');
    if (monthFilter) {
        monthFilter.addEventListener('change', loadDocuments);
    }
    
    const yearFilter = document.getElementById('yearFilter');
    if (yearFilter) {
        yearFilter.addEventListener('change', loadDocuments);
    }
    
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        let searchTimeout;
        searchInput.addEventListener('input', () => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(loadDocuments, 500);
        });
    }
    
    const dateFromFilter = document.getElementById('dateFromFilter');
    if (dateFromFilter) {
        dateFromFilter.addEventListener('change', loadDocuments);
    }
    
    const dateToFilter = document.getElementById('dateToFilter');
    if (dateToFilter) {
        dateToFilter.addEventListener('change', loadDocuments);
    }

    await loadCompanies();
    await loadEmployees();
    await loadDocuments();
})();
