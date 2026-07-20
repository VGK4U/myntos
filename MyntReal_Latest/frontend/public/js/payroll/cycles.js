(async function() {
    const API_BASE = '/api/v1';
    const cyclesBody = document.getElementById('cyclesBody');
    const companyFilter = document.getElementById('companyFilter');
    const searchFilter = document.getElementById('searchFilter');
    const monthFilter = document.getElementById('monthFilter');
    const yearFilter = document.getElementById('yearFilter');
    const statusFilter = document.getElementById('statusFilter');
    const periodStartFilter = document.getElementById('periodStartFilter');
    const periodEndFilter = document.getElementById('periodEndFilter');
    const resetFiltersBtn = document.getElementById('resetFiltersBtn');
    const resultsCount = document.getElementById('resultsCount');
    const createCycleBtn = document.getElementById('createCycleBtn');

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

    function applyFilters() {
        const search = (searchFilter?.value || '').toLowerCase().trim();
        const company = companyFilter?.value || '';
        const month = monthFilter?.value || '';
        const year = yearFilter?.value || '';
        const status = statusFilter?.value || '';
        const periodStart = periodStartFilter?.value || '';
        const periodEnd = periodEndFilter?.value || '';

        let filtered = allCycles.filter(cycle => {
            if (search && !(cycle.cycle_code || '').toLowerCase().includes(search)) {
                return false;
            }
            if (company && String(cycle.company_id) !== company) {
                return false;
            }
            if (month && String(cycle.cycle_month) !== month) {
                return false;
            }
            if (year && String(cycle.cycle_year) !== year) {
                return false;
            }
            if (status && cycle.status !== status) {
                return false;
            }
            if (periodStart && cycle.period_start && cycle.period_start < periodStart) {
                return false;
            }
            if (periodEnd && cycle.period_end && cycle.period_end > periodEnd) {
                return false;
            }
            return true;
        });

        renderCycles(filtered);
    }

    function renderCycles(cycles) {
        if (resultsCount) {
            resultsCount.textContent = `Showing ${cycles.length} of ${allCycles.length} cycles`;
        }

        if (cycles.length === 0) {
            cyclesBody.innerHTML = '<tr><td colspan="11" class="text-center text-muted">No payroll cycles found</td></tr>';
            return;
        }
        
        const statusBadges = {
            'DRAFT': 'bg-secondary',
            'ATTENDANCE_LOCKED': 'bg-warning text-dark',
            'GENERATED': 'bg-info',
            'VALIDATED': 'bg-info',
            'APPROVED': 'bg-success',
            'PAID': 'bg-primary',
            'CANCELLED': 'bg-danger'
        };

        const formatDate = (dateStr) => {
            if (!dateStr) return '-';
            const d = new Date(dateStr);
            return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
        };
        
        cyclesBody.innerHTML = cycles.map((cycle, index) => `
            <tr>
                <td class="text-muted">${index + 1}</td>
                <td><code>${cycle.cycle_code || `CYC-${cycle.id}`}</code></td>
                <td>${cycle.company_name || 'N/A'}</td>
                <td>${cycle.cycle_month || 'N/A'}/${cycle.cycle_year || 'N/A'}</td>
                <td>${formatDate(cycle.period_start)}</td>
                <td>${formatDate(cycle.period_end)}</td>
                <td>${cycle.payment_date || 'Not set'}</td>
                <td><span class="badge ${statusBadges[cycle.status] || 'bg-secondary'}">${cycle.status}</span></td>
                <td>${cycle.runs_count || 0}</td>
                <td>₹${(cycle.total_net_salary || 0).toLocaleString('en-IN')}</td>
                <td>
                    <button class="btn btn-sm btn-outline-primary" onclick="viewCycle(${cycle.id})">
                        <i class="fas fa-eye"></i>
                    </button>
                    ${cycle.status === 'DRAFT' ? `
                        <button class="btn btn-sm btn-outline-success" onclick="processCycle(${cycle.id})">
                            <i class="fas fa-play"></i> Process
                        </button>
                    ` : ''}
                </td>
            </tr>
        `).join('');
    }

    async function loadCycles() {
        cyclesBody.innerHTML = '<tr><td colspan="11" class="text-center"><i class="fas fa-spinner fa-spin"></i> Loading...</td></tr>';
        
        try {
            const response = await fetchWithAuth(`${API_BASE}/staff/payroll/cycles`);
            if (!response.ok) throw new Error('Failed to load cycles');
            
            const data = await response.json();
            allCycles = data.data || [];
            
            applyFilters();
        } catch (error) {
            console.error('Error loading cycles:', error);
            cyclesBody.innerHTML = `<tr><td colspan="11" class="text-center text-danger">Error: ${error.message}</td></tr>`;
        }
    }

    function resetFilters() {
        if (searchFilter) searchFilter.value = '';
        if (companyFilter) companyFilter.value = '';
        if (monthFilter) monthFilter.value = '';
        if (yearFilter) yearFilter.value = '';
        if (statusFilter) statusFilter.value = '';
        if (periodStartFilter) periodStartFilter.value = '';
        if (periodEndFilter) periodEndFilter.value = '';
        applyFilters();
    }

    window.viewCycle = async function(id) {
        try {
            const response = await fetchWithAuth(`${API_BASE}/staff/payroll/cycles/${id}`);
            if (!response.ok) throw new Error('Failed to load cycle');
            
            const result = await response.json();
            const cycle = result.data;
            
            const statusBadges = {
                'DRAFT': 'bg-secondary',
                'ATTENDANCE_LOCKED': 'bg-warning text-dark',
                'GENERATED': 'bg-info',
                'VALIDATED': 'bg-info',
                'APPROVED': 'bg-success',
                'PAID': 'bg-primary',
                'CANCELLED': 'bg-danger'
            };
            
            const modalHtml = `
                <div class="modal fade" id="cycleViewModal" tabindex="-1">
                    <div class="modal-dialog modal-lg">
                        <div class="modal-content">
                            <div class="modal-header bg-primary text-white">
                                <h5 class="modal-title"><i class="fas fa-calendar-alt me-2"></i>Payroll Cycle Details</h5>
                                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body">
                                <div class="row mb-3">
                                    <div class="col-md-4">
                                        <small class="text-muted">Cycle Code</small><br>
                                        <strong><code>${cycle.cycle_code || 'N/A'}</code></strong>
                                    </div>
                                    <div class="col-md-4">
                                        <small class="text-muted">Company</small><br>
                                        <strong>${cycle.company_name || 'N/A'}</strong>
                                    </div>
                                    <div class="col-md-4">
                                        <small class="text-muted">Status</small><br>
                                        <span class="badge ${statusBadges[cycle.status] || 'bg-secondary'}">${cycle.status}</span>
                                    </div>
                                </div>
                                <div class="row mb-3">
                                    <div class="col-md-4">
                                        <small class="text-muted">Pay Period</small><br>
                                        <strong>${cycle.cycle_name || 'N/A'}</strong>
                                    </div>
                                    <div class="col-md-4">
                                        <small class="text-muted">Period Start</small><br>
                                        <strong>${cycle.period_start || 'N/A'}</strong>
                                    </div>
                                    <div class="col-md-4">
                                        <small class="text-muted">Period End</small><br>
                                        <strong>${cycle.period_end || 'N/A'}</strong>
                                    </div>
                                </div>
                                <hr>
                                <div class="row">
                                    <div class="col-md-4 text-center">
                                        <div class="h3 text-primary">${cycle.runs_summary?.total || cycle.runs_count || 0}</div>
                                        <small class="text-muted">Employees</small>
                                    </div>
                                    <div class="col-md-4 text-center">
                                        <div class="h3 text-success">₹${(cycle.financials?.total_net || cycle.total_net_salary || 0).toLocaleString('en-IN')}</div>
                                        <small class="text-muted">Total Net Salary</small>
                                    </div>
                                    <div class="col-md-4 text-center">
                                        <div class="h3 text-info">${cycle.payment_date || 'Not set'}</div>
                                        <small class="text-muted">Payment Date</small>
                                    </div>
                                </div>
                                ${cycle.locked_at ? `
                                    <div class="alert alert-info mt-3">
                                        <i class="fas fa-lock me-2"></i>Attendance locked at: ${cycle.locked_at}
                                    </div>
                                ` : ''}
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                                ${cycle.status === 'DRAFT' ? `
                                    <button type="button" class="btn btn-success" onclick="processCycle(${cycle.id})" data-bs-dismiss="modal">
                                        <i class="fas fa-play me-1"></i> Process
                                    </button>
                                ` : ''}
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            const existingModal = document.getElementById('cycleViewModal');
            if (existingModal) existingModal.remove();
            
            document.body.insertAdjacentHTML('beforeend', modalHtml);
            const modal = new bootstrap.Modal(document.getElementById('cycleViewModal'));
            modal.show();
        } catch (error) {
            alert('Error: ' + error.message);
        }
    };

    window.processCycle = async function(id) {
        if (!confirm('Process this payroll cycle? This will calculate salaries for all employees.')) return;
        
        try {
            const response = await fetchWithAuth(`${API_BASE}/staff/payroll/cycles/${id}/process`, {
                method: 'POST'
            });
            
            if (response.ok) {
                alert('Payroll cycle processed successfully');
                loadCycles();
            } else {
                const err = await response.json();
                alert('Error: ' + (err.detail || 'Failed to process cycle'));
            }
        } catch (error) {
            alert('Error: ' + error.message);
        }
    };

    window.createCycle = async function() {
        try {
            const companiesRes = await fetchWithAuth(`${API_BASE}/staff/payroll/companies`);
            const companies = companiesRes.ok ? (await companiesRes.json()).companies || [] : [];
            
            const companyOptions = companies.map(c => `<option value="${c.id}">${c.name}</option>`).join('');
            const currentDate = new Date();
            const currentMonth = currentDate.getMonth() + 1;
            const currentYear = currentDate.getFullYear();
            
            const monthOptions = Array.from({length: 12}, (_, i) => {
                const monthNum = i + 1;
                const monthName = new Date(2000, i).toLocaleString('default', {month: 'long'});
                return `<option value="${monthNum}" ${monthNum === currentMonth ? 'selected' : ''}>${monthName}</option>`;
            }).join('');
            
            const modalHtml = `
                <div class="modal fade" id="cycleCreateModal" tabindex="-1">
                    <div class="modal-dialog">
                        <div class="modal-content">
                            <div class="modal-header bg-success text-white">
                                <h5 class="modal-title"><i class="fas fa-plus me-2"></i>Create Payroll Cycle</h5>
                                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                            </div>
                            <form id="createCycleForm">
                                <div class="modal-body">
                                    <div class="mb-3">
                                        <label class="form-label">Company <span class="text-danger">*</span></label>
                                        <select class="form-select" name="company_id" required>
                                            <option value="">Select Company</option>
                                            ${companyOptions}
                                        </select>
                                    </div>
                                    <div class="row mb-3">
                                        <div class="col-md-6">
                                            <label class="form-label">Month <span class="text-danger">*</span></label>
                                            <select class="form-select" name="cycle_month" required>
                                                ${monthOptions}
                                            </select>
                                        </div>
                                        <div class="col-md-6">
                                            <label class="form-label">Year <span class="text-danger">*</span></label>
                                            <input type="number" class="form-control" name="cycle_year" value="${currentYear}" min="2020" max="2030" required>
                                        </div>
                                    </div>
                                    <div class="row mb-3">
                                        <div class="col-md-6">
                                            <label class="form-label">Period Start</label>
                                            <input type="date" class="form-control" name="period_start">
                                        </div>
                                        <div class="col-md-6">
                                            <label class="form-label">Period End</label>
                                            <input type="date" class="form-control" name="period_end">
                                        </div>
                                    </div>
                                </div>
                                <div class="modal-footer">
                                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                                    <button type="submit" class="btn btn-success"><i class="fas fa-plus me-1"></i> Create Cycle</button>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
            `;
            
            const existingModal = document.getElementById('cycleCreateModal');
            if (existingModal) existingModal.remove();
            
            document.body.insertAdjacentHTML('beforeend', modalHtml);
            
            document.getElementById('createCycleForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                const formData = new FormData(e.target);
                const payload = {
                    company_id: parseInt(formData.get('company_id')),
                    cycle_month: parseInt(formData.get('cycle_month')),
                    cycle_year: parseInt(formData.get('cycle_year')),
                    period_start: formData.get('period_start') || null,
                    period_end: formData.get('period_end') || null
                };
                
                try {
                    const res = await fetchWithAuth(`${API_BASE}/staff/payroll/cycles`, {
                        method: 'POST',
                        body: JSON.stringify(payload)
                    });
                    
                    if (res.ok) {
                        bootstrap.Modal.getInstance(document.getElementById('cycleCreateModal')).hide();
                        alert('Payroll cycle created successfully');
                        loadCycles();
                    } else {
                        const err = await res.json();
                        alert('Error: ' + (err.detail || 'Failed to create cycle'));
                    }
                } catch (err) {
                    alert('Error: ' + err.message);
                }
            });
            
            const modal = new bootstrap.Modal(document.getElementById('cycleCreateModal'));
            modal.show();
        } catch (error) {
            alert('Error: ' + error.message);
        }
    };

    if (createCycleBtn) {
        createCycleBtn.addEventListener('click', createCycle);
    }

    if (searchFilter) searchFilter.addEventListener('input', applyFilters);
    if (companyFilter) companyFilter.addEventListener('change', applyFilters);
    if (monthFilter) monthFilter.addEventListener('change', applyFilters);
    if (yearFilter) yearFilter.addEventListener('change', applyFilters);
    if (statusFilter) statusFilter.addEventListener('change', applyFilters);
    if (periodStartFilter) periodStartFilter.addEventListener('change', applyFilters);
    if (periodEndFilter) periodEndFilter.addEventListener('change', applyFilters);
    if (resetFiltersBtn) resetFiltersBtn.addEventListener('click', resetFilters);

    await loadCompanies();
    await loadCycles();
})();
