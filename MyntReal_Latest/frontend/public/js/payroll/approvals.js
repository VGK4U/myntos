(async function() {
    const API_BASE = '/api/v1';
    const approvalsBody = document.getElementById('approvalsBody');
    const companyFilter = document.getElementById('companyFilter');
    const searchFilter = document.getElementById('searchFilter');
    const cycleFilter = document.getElementById('cycleFilter');
    const statusFilter = document.getElementById('statusFilter');
    const monthFilter = document.getElementById('monthFilter');
    const yearFilter = document.getElementById('yearFilter');
    const resetFiltersBtn = document.getElementById('resetFiltersBtn');
    const resultsCount = document.getElementById('resultsCount');
    const pendingCount = document.getElementById('pendingCount');
    const approvedCount = document.getElementById('approvedCount');
    const rejectedCount = document.getElementById('rejectedCount');
    const totalNetPay = document.getElementById('totalNetPay');

    let allRuns = [];
    let allCycles = [];

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

    async function loadCycles() {
        try {
            const response = await fetchWithAuth(`${API_BASE}/staff/payroll/cycles`);
            if (response.ok) {
                const data = await response.json();
                allCycles = data.data || [];
                allCycles.forEach(cycle => {
                    const option = document.createElement('option');
                    option.value = cycle.id;
                    option.textContent = cycle.cycle_code || `${cycle.cycle_month}/${cycle.cycle_year}`;
                    cycleFilter.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Error loading cycles:', error);
        }
    }

    function applyFilters() {
        const search = (searchFilter?.value || '').toLowerCase().trim();
        const company = companyFilter?.value || '';
        const cycle = cycleFilter?.value || '';
        const status = statusFilter?.value || '';
        const month = monthFilter?.value || '';
        const year = yearFilter?.value || '';

        let filtered = allRuns.filter(run => {
            if (search && !(run.employee_name || '').toLowerCase().includes(search)) {
                return false;
            }
            if (company && String(run.company_id) !== company) {
                return false;
            }
            if (cycle && String(run.cycle_id) !== cycle) {
                return false;
            }
            if (status && run.status !== status) {
                return false;
            }
            if (month || year) {
                const matchedCycle = allCycles.find(c => c.id === run.cycle_id);
                if (matchedCycle) {
                    if (month && String(matchedCycle.cycle_month) !== month) return false;
                    if (year && String(matchedCycle.cycle_year) !== year) return false;
                }
            }
            return true;
        });

        renderApprovals(filtered);
    }

    function renderApprovals(runs) {
        let pending = 0, approved = 0, rejected = 0, totalNet = 0;
        runs.forEach(run => {
            if (run.status === 'PENDING') pending++;
            else if (run.status === 'APPROVED' || run.status === 'PAID') approved++;
            else if (run.status === 'REJECTED') rejected++;
            totalNet += parseFloat(run.net_salary || 0);
        });

        if (pendingCount) pendingCount.textContent = pending;
        if (approvedCount) approvedCount.textContent = approved;
        if (rejectedCount) rejectedCount.textContent = rejected;
        if (totalNetPay) totalNetPay.textContent = `₹${totalNet.toLocaleString('en-IN')}`;
        if (resultsCount) resultsCount.textContent = `Showing ${runs.length} of ${allRuns.length} records`;

        if (runs.length === 0) {
            approvalsBody.innerHTML = '<tr><td colspan="14" class="text-center text-muted">No payroll runs found</td></tr>';
            return;
        }

        const statusBadges = {
            'PENDING': 'bg-warning text-dark',
            'CALCULATED': 'bg-info',
            'VALIDATED': 'bg-info',
            'APPROVED': 'bg-success',
            'PAID': 'bg-primary',
            'REJECTED': 'bg-danger',
            'ON_HOLD': 'bg-secondary',
            'CANCELLED': 'bg-dark'
        };

        approvalsBody.innerHTML = runs.map((run, index) => {
            const basic = parseFloat(run.basic_amount || 0);
            const hra = parseFloat(run.hra_amount || 0);
            const gross = parseFloat(run.gross_salary || 0);
            const pf = parseFloat(run.pf_employee || 0);
            const esi = parseFloat(run.esi_employee || 0);
            const pt = parseFloat(run.pt_amount || 0);
            const tds = parseFloat(run.tds_amount || 0);
            const totalDed = parseFloat(run.total_deductions || 0);
            const netPay = parseFloat(run.net_salary || 0);

            const deductionsBreakup = [];
            if (pf > 0) deductionsBreakup.push(`PF: ₹${pf.toLocaleString('en-IN')}`);
            if (esi > 0) deductionsBreakup.push(`ESI: ₹${esi.toLocaleString('en-IN')}`);
            if (pt > 0) deductionsBreakup.push(`PT: ₹${pt.toLocaleString('en-IN')}`);
            if (tds > 0) deductionsBreakup.push(`TDS: ₹${tds.toLocaleString('en-IN')}`);
            const deductionsTooltip = deductionsBreakup.length > 0 ? deductionsBreakup.join(', ') : 'No deductions';

            const canApprove = run.status === 'PENDING' || run.status === 'CALCULATED' || run.status === 'VALIDATED';

            const totalDays = parseInt(run.eligible_days || 0);
            const paidDays = parseInt(run.days_present || run.days_worked || 0);
            const nonPaidDays = Math.max(0, totalDays - paidDays);
            const grossPay = parseFloat(run.ctc_monthly || 0);

            return `
                <tr>
                    <td class="text-muted">${index + 1}</td>
                    <td>${run.cycle_name || 'N/A'}</td>
                    <td>${run.employee_name || 'N/A'}</td>
                    <td>${totalDays}</td>
                    <td>${paidDays}</td>
                    <td>${nonPaidDays}</td>
                    <td>₹${grossPay.toLocaleString('en-IN')}</td>
                    <td>₹${basic.toLocaleString('en-IN')}</td>
                    <td>₹${hra.toLocaleString('en-IN')}</td>
                    <td>₹${gross.toLocaleString('en-IN')}</td>
                    <td title="${deductionsTooltip}" style="cursor: help;">₹${totalDed.toLocaleString('en-IN')}</td>
                    <td class="fw-bold text-success">₹${netPay.toLocaleString('en-IN')}</td>
                    <td><span class="badge ${statusBadges[run.status] || 'bg-secondary'}">${run.status}</span></td>
                    <td>
                        ${canApprove ? `
                            <button class="btn btn-sm btn-success" onclick="approveRun(${run.id})">
                                <i class="fas fa-check"></i> Approve
                            </button>
                            <button class="btn btn-sm btn-danger" onclick="rejectRun(${run.id})">
                                <i class="fas fa-times"></i> Reject
                            </button>
                        ` : `
                            <button class="btn btn-sm btn-outline-primary" onclick="viewRun(${run.id})">
                                <i class="fas fa-eye"></i>
                            </button>
                        `}
                    </td>
                </tr>
            `;
        }).join('');
    }

    async function loadApprovals() {
        approvalsBody.innerHTML = '<tr><td colspan="14" class="text-center"><i class="fas fa-spinner fa-spin"></i> Loading...</td></tr>';
        
        try {
            let url = `${API_BASE}/staff/payroll/runs`;
            const params = [];
            if (companyFilter?.value) params.push(`company_id=${companyFilter.value}`);
            if (params.length > 0) url += '?' + params.join('&');
            
            const response = await fetchWithAuth(url);
            if (!response.ok) throw new Error('Failed to load approvals');
            
            const data = await response.json();
            allRuns = data.data || [];
            
            applyFilters();
        } catch (error) {
            console.error('Error loading approvals:', error);
            approvalsBody.innerHTML = `<tr><td colspan="14" class="text-center text-danger">Error: ${error.message}</td></tr>`;
        }
    }

    function resetFilters() {
        if (searchFilter) searchFilter.value = '';
        if (companyFilter) companyFilter.value = '';
        if (cycleFilter) cycleFilter.value = '';
        if (statusFilter) statusFilter.value = '';
        if (monthFilter) monthFilter.value = '';
        if (yearFilter) yearFilter.value = '';
        applyFilters();
    }

    window.viewRun = async function(id) {
        const run = allRuns.find(r => r.id === id);
        if (!run) return alert('Run not found');

        const basic = parseFloat(run.basic_amount || 0);
        const hra = parseFloat(run.hra_amount || 0);
        const special = parseFloat(run.special_allowance || 0);
        const gross = parseFloat(run.gross_salary || 0);
        const pf = parseFloat(run.pf_employee || 0);
        const esi = parseFloat(run.esi_employee || 0);
        const pt = parseFloat(run.pt_amount || 0);
        const tds = parseFloat(run.tds_amount || 0);
        const totalDed = parseFloat(run.total_deductions || 0);
        const netPay = parseFloat(run.net_salary || 0);

        const modalHtml = `
            <div class="modal fade" id="runViewModal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header bg-primary text-white">
                            <h5 class="modal-title"><i class="fas fa-file-invoice-dollar me-2"></i>Payroll Details</h5>
                            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="mb-3">
                                <strong>Employee:</strong> ${run.employee_name || 'N/A'}<br>
                                <strong>Cycle:</strong> ${run.cycle_name || 'N/A'}<br>
                                <strong>Status:</strong> <span class="badge bg-info">${run.status}</span>
                            </div>
                            <hr>
                            <h6 class="text-success">Earnings</h6>
                            <table class="table table-sm">
                                <tr><td>Basic</td><td class="text-end">₹${basic.toLocaleString('en-IN')}</td></tr>
                                <tr><td>HRA</td><td class="text-end">₹${hra.toLocaleString('en-IN')}</td></tr>
                                <tr><td>Special Allowance</td><td class="text-end">₹${special.toLocaleString('en-IN')}</td></tr>
                                <tr class="table-success"><td><strong>Gross Salary</strong></td><td class="text-end"><strong>₹${gross.toLocaleString('en-IN')}</strong></td></tr>
                            </table>
                            <h6 class="text-danger">Deductions</h6>
                            <table class="table table-sm">
                                <tr><td>PF (Employee)</td><td class="text-end">₹${pf.toLocaleString('en-IN')}</td></tr>
                                <tr><td>ESI (Employee)</td><td class="text-end">₹${esi.toLocaleString('en-IN')}</td></tr>
                                <tr><td>Professional Tax</td><td class="text-end">₹${pt.toLocaleString('en-IN')}</td></tr>
                                <tr><td>TDS</td><td class="text-end">₹${tds.toLocaleString('en-IN')}</td></tr>
                                <tr class="table-danger"><td><strong>Total Deductions</strong></td><td class="text-end"><strong>₹${totalDed.toLocaleString('en-IN')}</strong></td></tr>
                            </table>
                            <hr>
                            <div class="text-center">
                                <h4 class="text-primary">Net Salary: ₹${netPay.toLocaleString('en-IN')}</h4>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        const existingModal = document.getElementById('runViewModal');
        if (existingModal) existingModal.remove();

        document.body.insertAdjacentHTML('beforeend', modalHtml);
        const modal = new bootstrap.Modal(document.getElementById('runViewModal'));
        modal.show();
    };

    window.approveRun = async function(id) {
        if (!confirm('Approve this payroll run?')) return;
        try {
            const response = await fetchWithAuth(`${API_BASE}/staff/payroll/runs/${id}/approve`, {
                method: 'POST',
                body: JSON.stringify({ action: 'approve' })
            });
            if (response.ok) {
                alert('Payroll run approved successfully');
                loadApprovals();
            } else {
                const data = await response.json();
                alert('Error: ' + (data.detail || 'Failed to approve'));
            }
        } catch (error) {
            alert('Error: ' + error.message);
        }
    };

    window.rejectRun = async function(id) {
        const reason = prompt('Please provide rejection reason:');
        if (!reason) return;
        try {
            const response = await fetchWithAuth(`${API_BASE}/staff/payroll/runs/${id}/approve`, {
                method: 'POST',
                body: JSON.stringify({ action: 'reject', remarks: reason })
            });
            if (response.ok) {
                alert('Payroll run rejected');
                loadApprovals();
            } else {
                const data = await response.json();
                alert('Error: ' + (data.detail || 'Failed to reject'));
            }
        } catch (error) {
            alert('Error: ' + error.message);
        }
    };

    if (searchFilter) searchFilter.addEventListener('input', applyFilters);
    if (companyFilter) companyFilter.addEventListener('change', applyFilters);
    if (cycleFilter) cycleFilter.addEventListener('change', applyFilters);
    if (statusFilter) statusFilter.addEventListener('change', applyFilters);
    if (monthFilter) monthFilter.addEventListener('change', applyFilters);
    if (yearFilter) yearFilter.addEventListener('change', applyFilters);
    if (resetFiltersBtn) resetFiltersBtn.addEventListener('click', resetFilters);

    await loadCompanies();
    await loadCycles();
    await loadApprovals();
})();
