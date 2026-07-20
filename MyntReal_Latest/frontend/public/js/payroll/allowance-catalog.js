(async function() {
    const API_BASE = '/api/v1';
    const catalogBody = document.getElementById('catalogBody');
    const companyFilter = document.getElementById('companyFilter');
    const addAllowanceBtn = document.getElementById('addAllowanceBtn');

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

    async function loadCatalog() {
        catalogBody.innerHTML = '<tr><td colspan="8" class="text-center"><i class="fas fa-spinner fa-spin"></i> Loading...</td></tr>';
        
        try {
            let url = `${API_BASE}/staff/payroll/allowance-catalog`;
            if (companyFilter.value) {
                url += `?company_id=${companyFilter.value}`;
            }
            
            const response = await fetchWithAuth(url);
            if (!response.ok) throw new Error('Failed to load catalog');
            
            const data = await response.json();
            const entries = data.data || [];
            
            if (entries.length === 0) {
                catalogBody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">No custom allowances found</td></tr>';
                return;
            }
            
            catalogBody.innerHTML = entries.map(entry => `
                <tr>
                    <td><code>${entry.allowance_code}</code></td>
                    <td>${entry.allowance_name}</td>
                    <td>${entry.company_name || 'N/A'}</td>
                    <td>${entry.is_percentage ? entry.default_value + '%' : '₹' + (entry.default_value || 0).toLocaleString('en-IN')}</td>
                    <td><span class="badge ${entry.is_taxable ? 'bg-warning' : 'bg-success'}">${entry.is_taxable ? 'Taxable' : 'Non-Taxable'}</span></td>
                    <td>${(entry.applicable_employment_types || ['ALL']).join(', ')}</td>
                    <td><span class="badge ${entry.is_active ? 'bg-success' : 'bg-secondary'}">${entry.is_active ? 'Active' : 'Inactive'}</span></td>
                    <td>
                        <button class="btn btn-sm btn-outline-warning" onclick="editAllowance(${entry.id})">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-danger" onclick="deleteAllowance(${entry.id})">
                            <i class="fas fa-trash"></i>
                        </button>
                    </td>
                </tr>
            `).join('');
        } catch (error) {
            console.error('Error loading catalog:', error);
            catalogBody.innerHTML = `<tr><td colspan="8" class="text-center text-danger">Error: ${error.message}</td></tr>`;
        }
    }

    window.editAllowance = async function(id) {
        try {
            const [allowanceRes, companiesRes] = await Promise.all([
                fetchWithAuth(`${API_BASE}/staff/payroll/allowance-catalog/${id}`),
                fetchWithAuth(`${API_BASE}/staff/payroll/companies`)
            ]);
            
            if (!allowanceRes.ok) throw new Error('Failed to load allowance');
            
            const allowance = (await allowanceRes.json()).data;
            const companies = companiesRes.ok ? (await companiesRes.json()).companies || [] : [];
            
            const companyOptions = companies.map(c => 
                `<option value="${c.id}" ${allowance.company_id === c.id ? 'selected' : ''}>${c.name}</option>`
            ).join('');
            
            const modalHtml = `
                <div class="modal fade" id="allowanceEditModal" tabindex="-1">
                    <div class="modal-dialog">
                        <div class="modal-content">
                            <div class="modal-header bg-warning">
                                <h5 class="modal-title"><i class="fas fa-edit me-2"></i>Edit Allowance</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                            </div>
                            <form id="editAllowanceForm">
                                <div class="modal-body">
                                    <div class="mb-3">
                                        <label class="form-label">Allowance Code</label>
                                        <input type="text" class="form-control" value="${allowance.allowance_code || ''}" readonly>
                                    </div>
                                    <div class="mb-3">
                                        <label class="form-label">Allowance Name <span class="text-danger">*</span></label>
                                        <input type="text" class="form-control" name="allowance_name" value="${allowance.allowance_name || ''}" required>
                                    </div>
                                    <div class="mb-3">
                                        <label class="form-label">Company</label>
                                        <select class="form-select" name="company_id">
                                            <option value="">All Companies</option>
                                            ${companyOptions}
                                        </select>
                                    </div>
                                    <div class="row mb-3">
                                        <div class="col-md-6">
                                            <label class="form-label">Default Value</label>
                                            <input type="number" class="form-control" name="default_value" value="${allowance.default_value || 0}" step="0.01" min="0">
                                        </div>
                                        <div class="col-md-6">
                                            <div class="form-check mt-4">
                                                <input class="form-check-input" type="checkbox" name="is_percentage" ${allowance.is_percentage ? 'checked' : ''}>
                                                <label class="form-check-label">Is Percentage</label>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="row mb-3">
                                        <div class="col-md-6">
                                            <div class="form-check">
                                                <input class="form-check-input" type="checkbox" name="is_taxable" ${allowance.is_taxable ? 'checked' : ''}>
                                                <label class="form-check-label">Taxable</label>
                                            </div>
                                        </div>
                                        <div class="col-md-6">
                                            <div class="form-check">
                                                <input class="form-check-input" type="checkbox" name="is_active" ${allowance.is_active ? 'checked' : ''}>
                                                <label class="form-check-label">Active</label>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="mb-3">
                                        <label class="form-label">Description</label>
                                        <textarea class="form-control" name="description" rows="2">${allowance.description || ''}</textarea>
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
            
            const existingModal = document.getElementById('allowanceEditModal');
            if (existingModal) existingModal.remove();
            
            document.body.insertAdjacentHTML('beforeend', modalHtml);
            
            document.getElementById('editAllowanceForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                const formData = new FormData(e.target);
                const payload = {
                    allowance_name: formData.get('allowance_name'),
                    company_id: formData.get('company_id') ? parseInt(formData.get('company_id')) : null,
                    default_value: parseFloat(formData.get('default_value')) || 0,
                    is_percentage: formData.has('is_percentage'),
                    is_taxable: formData.has('is_taxable'),
                    is_active: formData.has('is_active'),
                    description: formData.get('description') || null
                };
                
                try {
                    const res = await fetchWithAuth(`${API_BASE}/staff/payroll/allowance-catalog/${id}`, {
                        method: 'PUT',
                        body: JSON.stringify(payload)
                    });
                    
                    if (res.ok) {
                        bootstrap.Modal.getInstance(document.getElementById('allowanceEditModal')).hide();
                        alert('Allowance updated successfully');
                        loadCatalog();
                    } else {
                        const err = await res.json();
                        alert('Error: ' + (err.detail || 'Failed to update'));
                    }
                } catch (err) {
                    alert('Error: ' + err.message);
                }
            });
            
            const modal = new bootstrap.Modal(document.getElementById('allowanceEditModal'));
            modal.show();
        } catch (error) {
            alert('Error: ' + error.message);
        }
    };

    window.deleteAllowance = async function(id) {
        if (!confirm('Are you sure you want to delete this allowance?')) return;
        try {
            const response = await fetchWithAuth(`${API_BASE}/staff/payroll/allowance-catalog/${id}`, {
                method: 'DELETE'
            });
            if (response.ok) {
                alert('Allowance deleted successfully');
                loadCatalog();
            } else {
                const data = await response.json();
                alert('Error: ' + (data.detail || 'Failed to delete'));
            }
        } catch (error) {
            alert('Error: ' + error.message);
        }
    };

    window.addAllowance = async function() {
        try {
            const companiesRes = await fetchWithAuth(`${API_BASE}/staff/payroll/companies`);
            const companies = companiesRes.ok ? (await companiesRes.json()).companies || [] : [];
            
            const companyOptions = companies.map(c => `<option value="${c.id}">${c.name}</option>`).join('');
            
            const modalHtml = `
                <div class="modal fade" id="allowanceAddModal" tabindex="-1">
                    <div class="modal-dialog">
                        <div class="modal-content">
                            <div class="modal-header bg-success text-white">
                                <h5 class="modal-title"><i class="fas fa-plus me-2"></i>Add Custom Allowance</h5>
                                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                            </div>
                            <form id="addAllowanceForm">
                                <div class="modal-body">
                                    <div class="mb-3">
                                        <label class="form-label">Allowance Code <span class="text-danger">*</span></label>
                                        <input type="text" class="form-control" name="allowance_code" required placeholder="e.g., TRAVEL_ALLOW">
                                    </div>
                                    <div class="mb-3">
                                        <label class="form-label">Allowance Name <span class="text-danger">*</span></label>
                                        <input type="text" class="form-control" name="allowance_name" required placeholder="e.g., Travel Allowance">
                                    </div>
                                    <div class="mb-3">
                                        <label class="form-label">Company (leave blank for all)</label>
                                        <select class="form-select" name="company_id">
                                            <option value="">All Companies</option>
                                            ${companyOptions}
                                        </select>
                                    </div>
                                    <div class="row mb-3">
                                        <div class="col-md-6">
                                            <label class="form-label">Default Value</label>
                                            <input type="number" class="form-control" name="default_value" value="0" step="0.01" min="0">
                                        </div>
                                        <div class="col-md-6">
                                            <div class="form-check mt-4">
                                                <input class="form-check-input" type="checkbox" name="is_percentage">
                                                <label class="form-check-label">Is Percentage (of Basic)</label>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="row mb-3">
                                        <div class="col-md-6">
                                            <div class="form-check">
                                                <input class="form-check-input" type="checkbox" name="is_taxable" checked>
                                                <label class="form-check-label">Taxable</label>
                                            </div>
                                        </div>
                                        <div class="col-md-6">
                                            <label class="form-label">Employment Types</label>
                                            <select class="form-select" name="applicable_employment_types" multiple>
                                                <option value="ONROLE" selected>On-Role</option>
                                                <option value="OFFROLE" selected>Off-Role</option>
                                            </select>
                                        </div>
                                    </div>
                                    <div class="mb-3">
                                        <label class="form-label">Description</label>
                                        <textarea class="form-control" name="description" rows="2"></textarea>
                                    </div>
                                </div>
                                <div class="modal-footer">
                                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                                    <button type="submit" class="btn btn-success"><i class="fas fa-plus me-1"></i> Add Allowance</button>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
            `;
            
            const existingModal = document.getElementById('allowanceAddModal');
            if (existingModal) existingModal.remove();
            
            document.body.insertAdjacentHTML('beforeend', modalHtml);
            
            document.getElementById('addAllowanceForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                const formData = new FormData(e.target);
                const selectedTypes = Array.from(e.target.elements['applicable_employment_types'].selectedOptions).map(o => o.value);
                
                const payload = {
                    allowance_code: formData.get('allowance_code'),
                    allowance_name: formData.get('allowance_name'),
                    company_id: formData.get('company_id') ? parseInt(formData.get('company_id')) : null,
                    default_value: parseFloat(formData.get('default_value')) || 0,
                    is_percentage: formData.has('is_percentage'),
                    is_taxable: formData.has('is_taxable'),
                    applicable_employment_types: selectedTypes,
                    description: formData.get('description') || null
                };
                
                try {
                    const res = await fetchWithAuth(`${API_BASE}/staff/payroll/allowance-catalog`, {
                        method: 'POST',
                        body: JSON.stringify(payload)
                    });
                    
                    if (res.ok) {
                        bootstrap.Modal.getInstance(document.getElementById('allowanceAddModal')).hide();
                        alert('Allowance added successfully');
                        loadCatalog();
                    } else {
                        const err = await res.json();
                        alert('Error: ' + (err.detail || 'Failed to add allowance'));
                    }
                } catch (err) {
                    alert('Error: ' + err.message);
                }
            });
            
            const modal = new bootstrap.Modal(document.getElementById('allowanceAddModal'));
            modal.show();
        } catch (error) {
            alert('Error: ' + error.message);
        }
    };

    if (addAllowanceBtn) {
        addAllowanceBtn.addEventListener('click', addAllowance);
    }

    if (companyFilter) {
        companyFilter.addEventListener('change', loadCatalog);
    }

    await loadCompanies();
    await loadCatalog();
})();
