(async function() {
    const API_BASE = '/api/v1';
    const runsBody = document.getElementById('runsBody');
    const companyFilter = document.getElementById('companyFilter');

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

    async function loadRuns() {
        runsBody.innerHTML = '<tr><td colspan="9" class="text-center"><i class="fas fa-spinner fa-spin"></i> Loading...</td></tr>';
        
        try {
            let url = `${API_BASE}/staff/payroll/runs`;
            if (companyFilter.value) {
                url += `?company_id=${companyFilter.value}`;
            }
            
            const response = await fetchWithAuth(url);
            if (!response.ok) throw new Error('Failed to load runs');
            
            const data = await response.json();
            const runs = data.data || [];
            
            if (runs.length === 0) {
                runsBody.innerHTML = '<tr><td colspan="9" class="text-center text-muted">No payroll runs found</td></tr>';
                return;
            }
            
            const statusBadges = {
                'PENDING': 'bg-warning text-dark',
                'CALCULATED': 'bg-info',
                'VALIDATED': 'bg-info',
                'APPROVED': 'bg-success',
                'REJECTED': 'bg-danger',
                'PAID': 'bg-primary',
                'ON_HOLD': 'bg-warning text-dark',
                'CANCELLED': 'bg-danger'
            };
            
            runsBody.innerHTML = runs.map(run => `
                <tr>
                    <td><code>${run.run_code || `RUN-${run.id}`}</code></td>
                    <td>${run.cycle_name || 'N/A'}</td>
                    <td>${run.employee_name || 'N/A'}</td>
                    <td>₹${(run.basic_amount || 0).toLocaleString('en-IN')}</td>
                    <td>₹${(run.hra_amount || 0).toLocaleString('en-IN')}</td>
                    <td>₹${(run.total_deductions || 0).toLocaleString('en-IN')}</td>
                    <td class="fw-bold text-success">₹${(run.net_salary || 0).toLocaleString('en-IN')}</td>
                    <td><span class="badge ${statusBadges[run.status] || 'bg-secondary'}">${run.status}</span></td>
                    <td>
                        ${!run.sfms_posted && run.status !== 'PAID' ? `
                            <button class="btn btn-sm btn-outline-warning me-1" onclick="recalculateRun(${run.id})" title="Re-run calculation with latest attendance">
                                <i class="fas fa-sync-alt me-1"></i> Re-run
                            </button>
                        ` : ''}
                        ${run.status === 'APPROVED' ? (run.sfms_posted ? `
                            <span class="badge bg-success" title="Posted Ref: ${run.sfms_reference || 'SFMS'}">
                                <i class="fas fa-check-double me-1"></i> Posted to SFMS
                            </span>
                        ` : `
                            <button class="btn btn-sm btn-primary" onclick="postRunToSfms(${run.id})">
                                <i class="fas fa-file-invoice-dollar me-1"></i> Post to SFMS
                            </button>
                        `) : (run.status === 'PENDING' ? `
                            <span class="badge bg-secondary">Pending Approval</span>
                        ` : `
                            <span class="text-muted small">-</span>
                        `)}
                    </td>
                </tr>
            `).join('');
        } catch (error) {
            console.error('Error loading runs:', error);
            runsBody.innerHTML = `<tr><td colspan="9" class="text-center text-danger">Error: ${error.message}</td></tr>`;
        }
    }

    window.recalculateRun = async function(id) {
        if (!confirm('Re-run payroll calculation for this employee using latest approved attendance?')) return;
        try {
            const response = await fetchWithAuth(`${API_BASE}/staff/payroll/runs/${id}/recalculate`, {
                method: 'POST'
            });
            const data = await response.json();
            if (response.ok && data.success) {
                alert('Payroll run recalculated successfully with latest attendance!');
                loadRuns();
            } else {
                alert('Error: ' + (data.detail || data.message || 'Failed to recalculate'));
            }
        } catch (error) {
            alert('Error: ' + error.message);
        }
    };

    window.postRunToSfms = async function(id) {
        if (!confirm('Post this approved payroll run to SFMS General Ledger?')) return;
        try {
            const response = await fetchWithAuth(`${API_BASE}/staff/payroll/runs/${id}/post-sfms`, {
                method: 'POST'
            });
            const data = await response.json();
            if (response.ok && data.success) {
                alert('Successfully posted payroll run to SFMS General Ledger! Reference: ' + (data.sfms_reference || 'SAL-' + id));
                loadRuns();
            } else {
                alert('Error: ' + (data.detail || data.message || 'Failed to post to SFMS'));
            }
        } catch (error) {
            alert('Error: ' + error.message);
        }
    };

    if (companyFilter) {
        companyFilter.addEventListener('change', loadRuns);
    }

    await loadCompanies();
    await loadRuns();
})();
