(async function() {
    const API_BASE = '/api/v1';
    const profilesBody = document.getElementById('profilesBody');
    const companyFilter = document.getElementById('companyFilter');
    const employmentTypeFilter = document.getElementById('employmentTypeFilter');
    const statusFilter = document.getElementById('statusFilter');
    const searchFilter = document.getElementById('searchFilter');
    const resetFiltersBtn = document.getElementById('resetFiltersBtn');
    const resultsCount = document.getElementById('resultsCount');
    const addProfileBtn = document.getElementById('addProfileBtn');

    let searchTimeout = null;

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
                    option.textContent = company.name || company.company_name;
                    companyFilter.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Error loading companies:', error);
        }
    }

    async function loadProfiles() {
        profilesBody.innerHTML = '<tr><td colspan="8" class="text-center"><i class="fas fa-spinner fa-spin"></i> Loading...</td></tr>';
        
        try {
            const params = new URLSearchParams();
            if (companyFilter && companyFilter.value) params.append('company_id', companyFilter.value);
            if (employmentTypeFilter && employmentTypeFilter.value) params.append('employment_type', employmentTypeFilter.value);
            if (statusFilter && statusFilter.value !== '') params.append('is_active', statusFilter.value);
            if (searchFilter && searchFilter.value.trim()) params.append('search', searchFilter.value.trim());
            
            let url = `${API_BASE}/staff/payroll/profiles`;
            if (params.toString()) url += `?${params.toString()}`;
            
            const response = await fetchWithAuth(url);
            if (!response.ok) throw new Error('Failed to load profiles');
            
            const data = await response.json();
            const profiles = data.data || [];
            const total = data.total || profiles.length;
            
            if (resultsCount) {
                resultsCount.textContent = `${profiles.length} of ${total} profiles`;
            }
            
            if (profiles.length === 0) {
                profilesBody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">No payroll profiles found</td></tr>';
                return;
            }
            
            profilesBody.innerHTML = profiles.map((profile, index) => `
                <tr>
                    <td class="text-muted">${index + 1}</td>
                    <td>${profile.employee_name || 'N/A'}</td>
                    <td>${profile.company_name || 'N/A'}</td>
                    <td><span class="badge ${profile.employment_type === 'ONROLE' ? 'bg-success' : 'bg-info'}">${profile.employment_type}</span></td>
                    <td>₹${(profile.ctc_monthly || 0).toLocaleString('en-IN')}</td>
                    <td>${profile.tax_regime || 'NEW'}</td>
                    <td><span class="badge ${profile.is_active ? 'bg-success' : 'bg-secondary'}">${profile.is_active ? 'Active' : 'Inactive'}</span></td>
                    <td>
                        <button class="btn btn-sm btn-outline-primary" onclick="viewProfile(${profile.id})" title="View">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-warning" onclick="editProfile(${profile.id})" title="Edit">
                            <i class="fas fa-edit"></i>
                        </button>
                    </td>
                </tr>
            `).join('');
        } catch (error) {
            console.error('Error loading profiles:', error);
            profilesBody.innerHTML = `<tr><td colspan="8" class="text-center text-danger">Error: ${error.message}</td></tr>`;
        }
    }

    window.viewProfile = async function(id) {
        try {
            const response = await fetchWithAuth(`${API_BASE}/staff/payroll/profiles/${id}`);
            if (!response.ok) throw new Error('Failed to load profile');
            
            const result = await response.json();
            const profile = result.data;
            
            const modalHtml = `
                <div class="modal fade" id="profileViewModal" tabindex="-1">
                    <div class="modal-dialog modal-lg">
                        <div class="modal-content">
                            <div class="modal-header bg-primary text-white">
                                <h5 class="modal-title"><i class="fas fa-user me-2"></i>Salary Profile Details</h5>
                                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body">
                                <div class="row mb-3">
                                    <div class="col-md-6">
                                        <small class="text-muted">Employee Name</small><br>
                                        <strong>${profile.employee_name || 'N/A'}</strong>
                                    </div>
                                    <div class="col-md-6">
                                        <small class="text-muted">Company</small><br>
                                        <strong>${profile.company_name || 'N/A'}</strong>
                                    </div>
                                </div>
                                <div class="row mb-3">
                                    <div class="col-md-4">
                                        <small class="text-muted">Employment Type</small><br>
                                        <span class="badge ${profile.employment_type === 'ONROLE' ? 'bg-success' : 'bg-info'}">${profile.employment_type}</span>
                                    </div>
                                    <div class="col-md-4">
                                        <small class="text-muted">Tax Regime</small><br>
                                        <strong>${profile.tax_regime || 'NEW'}</strong>
                                    </div>
                                    <div class="col-md-4">
                                        <small class="text-muted">Status</small><br>
                                        <span class="badge ${profile.is_active ? 'bg-success' : 'bg-secondary'}">${profile.is_active ? 'Active' : 'Inactive'}</span>
                                    </div>
                                </div>
                                <hr>
                                <h6>Salary Components</h6>
                                <div class="row">
                                    <div class="col-md-6">
                                        <table class="table table-sm">
                                            <tr><td>Monthly CTC</td><td class="text-end"><strong>₹${(profile.ctc_monthly || 0).toLocaleString('en-IN')}</strong></td></tr>
                                            <tr><td>Basic (${profile.basic_pct || 40}%)</td><td class="text-end">₹${(profile.basic_amount || 0).toLocaleString('en-IN')}</td></tr>
                                            <tr><td>HRA (${profile.hra_pct || 20}%)</td><td class="text-end">₹${(profile.hra_amount || 0).toLocaleString('en-IN')}</td></tr>
                                            <tr><td>Special Allowance</td><td class="text-end">₹${(profile.special_allowance || 0).toLocaleString('en-IN')}</td></tr>
                                        </table>
                                    </div>
                                    <div class="col-md-6">
                                        <table class="table table-sm">
                                            <tr><td>PF Applicable</td><td class="text-end">${profile.pf_applicable ? '<i class="fas fa-check text-success"></i>' : '<i class="fas fa-times text-muted"></i>'}</td></tr>
                                            <tr><td>ESI Applicable</td><td class="text-end">${profile.esi_applicable ? '<i class="fas fa-check text-success"></i>' : '<i class="fas fa-times text-muted"></i>'}</td></tr>
                                            <tr><td>PT Applicable</td><td class="text-end">${profile.pt_applicable ? '<i class="fas fa-check text-success"></i>' : '<i class="fas fa-times text-muted"></i>'}</td></tr>
                                        </table>
                                    </div>
                                </div>
                                <small class="text-muted">Effective Date: ${profile.effective_from || 'N/A'}</small>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                                <button type="button" class="btn btn-warning" onclick="editProfile(${profile.id})" data-bs-dismiss="modal">
                                    <i class="fas fa-edit me-1"></i> Edit
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            const existingModal = document.getElementById('profileViewModal');
            if (existingModal) existingModal.remove();
            
            document.body.insertAdjacentHTML('beforeend', modalHtml);
            const modal = new bootstrap.Modal(document.getElementById('profileViewModal'));
            modal.show();
        } catch (error) {
            alert('Error: ' + error.message);
        }
    };

    window.editProfile = async function(id) {
        try {
            const [profileRes, companiesRes] = await Promise.all([
                fetchWithAuth(`${API_BASE}/staff/payroll/profiles/${id}`),
                fetchWithAuth(`${API_BASE}/staff/payroll/companies`)
            ]);
            
            if (!profileRes.ok) throw new Error('Failed to load profile');
            
            const profile = (await profileRes.json()).data;
            const companies = companiesRes.ok ? (await companiesRes.json()).companies || [] : [];
            
            const modalHtml = `
                <div class="modal fade" id="profileEditModal" tabindex="-1">
                    <div class="modal-dialog modal-lg">
                        <div class="modal-content">
                            <div class="modal-header bg-warning">
                                <h5 class="modal-title"><i class="fas fa-edit me-2"></i>Edit Salary Profile</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                            </div>
                            <form id="editProfileForm">
                                <div class="modal-body">
                                    <div class="row mb-3">
                                        <div class="col-md-6">
                                            <label class="form-label">Employee</label>
                                            <input type="text" class="form-control" value="${profile.employee_name || ''}" readonly>
                                        </div>
                                        <div class="col-md-6">
                                            <label class="form-label">Company</label>
                                            <input type="text" class="form-control" value="${profile.company_name || ''}" readonly>
                                        </div>
                                    </div>
                                    <div class="row mb-3">
                                        <div class="col-md-4">
                                            <label class="form-label">Employment Type</label>
                                            <select class="form-select" name="employment_type" required>
                                                <option value="ONROLE" ${profile.employment_type === 'ONROLE' ? 'selected' : ''}>On-Role</option>
                                                <option value="OFFROLE" ${profile.employment_type === 'OFFROLE' ? 'selected' : ''}>Off-Role</option>
                                            </select>
                                        </div>
                                        <div class="col-md-4">
                                            <label class="form-label">Monthly CTC (₹)</label>
                                            <input type="number" class="form-control" name="ctc_monthly" value="${profile.ctc_monthly || 0}" required min="0">
                                        </div>
                                        <div class="col-md-4">
                                            <label class="form-label">Tax Regime</label>
                                            <select class="form-select" name="tax_regime">
                                                <option value="NEW" ${profile.tax_regime === 'NEW' ? 'selected' : ''}>New</option>
                                                <option value="OLD" ${profile.tax_regime === 'OLD' ? 'selected' : ''}>Old</option>
                                            </select>
                                        </div>
                                    </div>
                                    <div class="row mb-3">
                                        <div class="col-md-4">
                                            <div class="form-check">
                                                <input class="form-check-input" type="checkbox" name="pf_applicable" ${profile.pf_applicable ? 'checked' : ''}>
                                                <label class="form-check-label">PF Applicable</label>
                                            </div>
                                        </div>
                                        <div class="col-md-4">
                                            <div class="form-check">
                                                <input class="form-check-input" type="checkbox" name="esi_applicable" ${profile.esi_applicable ? 'checked' : ''}>
                                                <label class="form-check-label">ESI Applicable</label>
                                            </div>
                                        </div>
                                        <div class="col-md-4">
                                            <div class="form-check">
                                                <input class="form-check-input" type="checkbox" name="pt_applicable" ${profile.pt_applicable ? 'checked' : ''}>
                                                <label class="form-check-label">PT Applicable</label>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="row mb-3">
                                        <div class="col-md-6">
                                            <label class="form-label">Effective From</label>
                                            <input type="date" class="form-control" name="effective_from" value="${profile.effective_from || ''}">
                                        </div>
                                        <div class="col-md-6">
                                            <div class="form-check mt-4">
                                                <input class="form-check-input" type="checkbox" name="is_active" ${profile.is_active ? 'checked' : ''}>
                                                <label class="form-check-label">Active</label>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                <div class="modal-footer">
                                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                                    <button type="submit" class="btn btn-primary"><i class="fas fa-save me-1"></i> Save Changes</button>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
            `;
            
            const existingModal = document.getElementById('profileEditModal');
            if (existingModal) existingModal.remove();
            
            document.body.insertAdjacentHTML('beforeend', modalHtml);
            
            document.getElementById('editProfileForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                const formData = new FormData(e.target);
                const payload = {
                    employment_type: formData.get('employment_type'),
                    ctc_monthly: parseFloat(formData.get('ctc_monthly')) || 0,
                    tax_regime: formData.get('tax_regime'),
                    pf_applicable: formData.has('pf_applicable'),
                    esi_applicable: formData.has('esi_applicable'),
                    pt_applicable: formData.has('pt_applicable'),
                    effective_from: formData.get('effective_from') || null,
                    is_active: formData.has('is_active')
                };
                
                try {
                    const res = await fetchWithAuth(`${API_BASE}/staff/payroll/profiles/${id}`, {
                        method: 'PUT',
                        body: JSON.stringify(payload)
                    });
                    
                    if (res.ok) {
                        bootstrap.Modal.getInstance(document.getElementById('profileEditModal')).hide();
                        alert('Profile updated successfully');
                        loadProfiles();
                    } else {
                        const err = await res.json();
                        alert('Error: ' + (err.detail || 'Failed to update'));
                    }
                } catch (err) {
                    alert('Error: ' + err.message);
                }
            });
            
            const modal = new bootstrap.Modal(document.getElementById('profileEditModal'));
            modal.show();
        } catch (error) {
            alert('Error: ' + error.message);
        }
    };

    window.addProfile = async function() {
        try {
            const [companiesRes, employeesRes] = await Promise.all([
                fetchWithAuth(`${API_BASE}/staff/payroll/companies`),
                fetchWithAuth(`${API_BASE}/staff/payroll/employees/list`)
            ]);
            
            const companies = companiesRes.ok ? (await companiesRes.json()).companies || [] : [];
            const employees = employeesRes.ok ? (await employeesRes.json()).data || [] : [];
            
            const companyOptions = companies.map(c => `<option value="${c.id}">${c.name || c.company_name}</option>`).join('');
            const employeeOptions = employees.map(e => `<option value="${e.id}">${e.full_name} (${e.emp_code || e.employee_code || 'N/A'})</option>`).join('');
            
            const modalHtml = `
                <div class="modal fade" id="profileAddModal" tabindex="-1">
                    <div class="modal-dialog modal-lg">
                        <div class="modal-content">
                            <div class="modal-header bg-success text-white">
                                <h5 class="modal-title"><i class="fas fa-plus me-2"></i>Add Salary Profile</h5>
                                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                            </div>
                            <form id="addProfileForm">
                                <div class="modal-body">
                                    <div class="row mb-3">
                                        <div class="col-md-6">
                                            <label class="form-label">Employee <span class="text-danger">*</span></label>
                                            <select class="form-select" name="employee_id" required>
                                                <option value="">Select Employee</option>
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
                                            <label class="form-label">Employment Type <span class="text-danger">*</span></label>
                                            <select class="form-select" name="employment_type" required>
                                                <option value="ONROLE">On-Role</option>
                                                <option value="OFFROLE">Off-Role</option>
                                            </select>
                                        </div>
                                        <div class="col-md-4">
                                            <label class="form-label">Monthly CTC (₹) <span class="text-danger">*</span></label>
                                            <input type="number" class="form-control" name="ctc_monthly" required min="0" value="0">
                                        </div>
                                        <div class="col-md-4">
                                            <label class="form-label">Tax Regime</label>
                                            <select class="form-select" name="tax_regime">
                                                <option value="NEW" selected>New</option>
                                                <option value="OLD">Old</option>
                                            </select>
                                        </div>
                                    </div>
                                    <div class="row mb-3">
                                        <div class="col-md-4">
                                            <div class="form-check">
                                                <input class="form-check-input" type="checkbox" name="pf_applicable" checked>
                                                <label class="form-check-label">PF Applicable</label>
                                            </div>
                                        </div>
                                        <div class="col-md-4">
                                            <div class="form-check">
                                                <input class="form-check-input" type="checkbox" name="esi_applicable">
                                                <label class="form-check-label">ESI Applicable</label>
                                            </div>
                                        </div>
                                        <div class="col-md-4">
                                            <div class="form-check">
                                                <input class="form-check-input" type="checkbox" name="pt_applicable" checked>
                                                <label class="form-check-label">PT Applicable</label>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="row mb-3">
                                        <div class="col-md-6">
                                            <label class="form-label">Effective From</label>
                                            <input type="date" class="form-control" name="effective_from">
                                        </div>
                                    </div>
                                </div>
                                <div class="modal-footer">
                                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                                    <button type="submit" class="btn btn-success"><i class="fas fa-plus me-1"></i> Create Profile</button>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
            `;
            
            const existingModal = document.getElementById('profileAddModal');
            if (existingModal) existingModal.remove();
            
            document.body.insertAdjacentHTML('beforeend', modalHtml);
            
            document.getElementById('addProfileForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                const formData = new FormData(e.target);
                const payload = {
                    employee_id: parseInt(formData.get('employee_id')),
                    company_id: parseInt(formData.get('company_id')),
                    employment_type: formData.get('employment_type'),
                    ctc_monthly: parseFloat(formData.get('ctc_monthly')) || 0,
                    tax_regime: formData.get('tax_regime'),
                    pf_applicable: formData.has('pf_applicable'),
                    esi_applicable: formData.has('esi_applicable'),
                    pt_applicable: formData.has('pt_applicable'),
                    effective_from: formData.get('effective_from') || null
                };
                
                try {
                    const res = await fetchWithAuth(`${API_BASE}/staff/payroll/profiles`, {
                        method: 'POST',
                        body: JSON.stringify(payload)
                    });
                    
                    if (res.ok) {
                        bootstrap.Modal.getInstance(document.getElementById('profileAddModal')).hide();
                        alert('Profile created successfully');
                        loadProfiles();
                    } else {
                        const err = await res.json();
                        alert('Error: ' + (err.detail || 'Failed to create profile'));
                    }
                } catch (err) {
                    alert('Error: ' + err.message);
                }
            });
            
            const modal = new bootstrap.Modal(document.getElementById('profileAddModal'));
            modal.show();
        } catch (error) {
            alert('Error: ' + error.message);
        }
    };

    function resetFilters() {
        if (companyFilter) companyFilter.value = '';
        if (employmentTypeFilter) employmentTypeFilter.value = '';
        if (statusFilter) statusFilter.value = 'true';
        if (searchFilter) searchFilter.value = '';
        loadProfiles();
    }

    if (addProfileBtn) {
        addProfileBtn.addEventListener('click', addProfile);
    }

    if (companyFilter) {
        companyFilter.addEventListener('change', loadProfiles);
    }

    if (employmentTypeFilter) {
        employmentTypeFilter.addEventListener('change', loadProfiles);
    }

    if (statusFilter) {
        statusFilter.addEventListener('change', loadProfiles);
    }

    if (searchFilter) {
        searchFilter.addEventListener('input', () => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(loadProfiles, 300);
        });
    }

    if (resetFiltersBtn) {
        resetFiltersBtn.addEventListener('click', resetFilters);
    }

    await loadCompanies();
    await loadProfiles();
})();
