// RVZ Awards Configuration - Master Data Management
// DC Protocol Compliant: Single source of truth for award/bonanza definitions
// Three sections: Direct Facilitations, Group Performance Recognitions, Bonanzas

console.log('🏆 RVZ Awards Configuration JS loaded');

// ============================================================================
// STATE MANAGEMENT
// ============================================================================

const state = {
    currentTab: 'direct',
    directAwards: {
        data: [],
        page: 1,
        pageSize: 50,
        totalPages: 1,
        filters: {
            search: '',
            priceMin: '',
            priceMax: '',
            sortBy: 'referral_count',
            sortOrder: 'asc'
        }
    },
    matchingAwards: {
        data: [],
        page: 1,
        pageSize: 50,
        totalPages: 1,
        filters: {
            search: '',
            priceMin: '',
            priceMax: '',
            sortBy: 'match_count',
            sortOrder: 'asc'
        }
    },
    bonanzas: {
        data: [],
        page: 1,
        pageSize: 50,
        totalPages: 1,
        filters: {
            search: '',
            status: '',
            rewardType: '',
            startDateFrom: '',
            startDateTo: '',
            priceMin: '',
            priceMax: '',
            sortBy: 'created_at',
            sortOrder: 'desc'
        }
    },
    awardsDropdown: {
        direct: [],
        matching: []
    },
    summary: null
};

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

function getUserId() {
    if (!window.sessionToken) {
        console.error('No session token found');
        return null;
    }
    const userId = window.sessionToken.split(':')[0];
    return userId;
}

async function fetchDirectAwards() {
    try {
        const userId = getUserId();
        if (!userId) {
            showError('Session expired. Please login again.');
            return;
        }
        
        const filters = state.directAwards.filters;
        const queryParams = new URLSearchParams({
            user_id: userId,
            page: state.directAwards.page,
            page_size: state.directAwards.pageSize,
            sort_by: filters.sortBy,
            sort_order: filters.sortOrder
        });
        
        if (filters.search) queryParams.append('search', filters.search);
        if (filters.priceMin) queryParams.append('price_min', filters.priceMin);
        if (filters.priceMax) queryParams.append('price_max', filters.priceMax);
        
        const response = await fetch(`/api/v1/rvz/awards-config/direct-tiers?${queryParams}`);
        const result = await response.json();
        
        if (result.success) {
            state.directAwards.data = result.data;
            state.directAwards.totalPages = result.pagination.total_pages;
            renderDirectAwardsTable();
        } else {
            showError('Failed to load direct awards');
        }
    } catch (error) {
        console.error('Error fetching direct awards:', error);
        showError('Error loading direct awards');
    }
}

async function fetchMatchingAwards() {
    try {
        const userId = getUserId();
        if (!userId) {
            showError('Session expired. Please login again.');
            return;
        }
        
        const filters = state.matchingAwards.filters;
        const queryParams = new URLSearchParams({
            user_id: userId,
            page: state.matchingAwards.page,
            page_size: state.matchingAwards.pageSize,
            sort_by: filters.sortBy,
            sort_order: filters.sortOrder
        });
        
        if (filters.search) queryParams.append('search', filters.search);
        if (filters.priceMin) queryParams.append('price_min', filters.priceMin);
        if (filters.priceMax) queryParams.append('price_max', filters.priceMax);
        
        const response = await fetch(`/api/v1/rvz/awards-config/matching-tiers?${queryParams}`);
        const result = await response.json();
        
        if (result.success) {
            state.matchingAwards.data = result.data;
            state.matchingAwards.totalPages = result.pagination.total_pages;
            renderMatchingAwardsTable();
        } else {
            showError('Failed to load matching awards');
        }
    } catch (error) {
        console.error('Error fetching matching awards:', error);
        showError('Error loading matching awards');
    }
}

async function fetchBonanzas() {
    try {
        const userId = getUserId();
        if (!userId) {
            showError('Session expired. Please login again.');
            return;
        }
        
        const filters = state.bonanzas.filters;
        const queryParams = new URLSearchParams({
            user_id: userId,
            page: state.bonanzas.page,
            page_size: state.bonanzas.pageSize,
            sort_by: filters.sortBy,
            sort_order: filters.sortOrder
        });
        
        if (filters.search) queryParams.append('search', filters.search);
        if (filters.status) queryParams.append('status', filters.status);
        if (filters.rewardType) queryParams.append('reward_type', filters.rewardType);
        if (filters.startDateFrom) queryParams.append('start_date_from', filters.startDateFrom);
        if (filters.startDateTo) queryParams.append('start_date_to', filters.startDateTo);
        if (filters.priceMin) queryParams.append('price_min', filters.priceMin);
        if (filters.priceMax) queryParams.append('price_max', filters.priceMax);
        
        const response = await fetch(`/api/v1/rvz/awards-config/bonanzas?${queryParams}`);
        const result = await response.json();
        
        if (result.success) {
            state.bonanzas.data = result.data;
            state.bonanzas.totalPages = result.pagination.total_pages;
            renderBonanzasTable();
        } else {
            showError('Failed to load bonanzas');
        }
    } catch (error) {
        console.error('Error fetching bonanzas:', error);
        showError('Error loading bonanzas');
    }
}

async function fetchAwardsDropdown() {
    try {
        const userId = getUserId();
        if (!userId) return;
        
        const response = await fetch(`/api/v1/rvz/awards-config/awards-dropdown?user_id=${userId}`);
        const result = await response.json();
        
        if (result.success) {
            // Map API response (direct_awards, matching_awards) to state (direct, matching)
            state.awardsDropdown.direct = result.data.direct_awards || [];
            state.awardsDropdown.matching = result.data.matching_awards || [];
        }
    } catch (error) {
        console.error('Error fetching awards dropdown:', error);
        // Ensure arrays exist even on error
        state.awardsDropdown.direct = state.awardsDropdown.direct || [];
        state.awardsDropdown.matching = state.awardsDropdown.matching || [];
    }
}

async function fetchSummary() {
    try {
        const userId = getUserId();
        if (!userId) return;
        
        const response = await fetch(`/api/v1/rvz/awards-config/summary?user_id=${userId}`);
        const result = await response.json();
        
        if (result.success) {
            state.summary = result.data;
            renderSummary();
        }
    } catch (error) {
        console.error('Error fetching summary:', error);
    }
}

async function updateDirectAward(tierId, updateData) {
    try {
        const userId = getUserId();
        if (!userId) {
            showError('Session expired. Please login again.');
            return;
        }
        
        const response = await fetch(`/api/v1/rvz/awards-config/direct-tiers/${tierId}?user_id=${userId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(updateData)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showSuccess(result.message);
            if (result.price_changed) {
                showInfo(`Price changed from ₹${result.old_price?.toLocaleString() || 0} to ₹${result.new_price?.toLocaleString() || 0}`);
            }
            await fetchDirectAwards();
            await fetchSummary();
        } else {
            showError('Failed to update direct award');
        }
    } catch (error) {
        console.error('Error updating direct award:', error);
        showError('Error updating direct award');
    }
}

async function updateMatchingAward(tierId, updateData) {
    try {
        const userId = getUserId();
        if (!userId) {
            showError('Session expired. Please login again.');
            return;
        }
        
        const response = await fetch(`/api/v1/rvz/awards-config/matching-tiers/${tierId}?user_id=${userId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(updateData)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showSuccess(result.message);
            if (result.price_changed) {
                showInfo(`Price changed from ₹${result.old_price?.toLocaleString() || 0} to ₹${result.new_price?.toLocaleString() || 0}`);
            }
            await fetchMatchingAwards();
            await fetchSummary();
        } else {
            showError('Failed to update matching award');
        }
    } catch (error) {
        console.error('Error updating matching award:', error);
        showError('Error updating matching award');
    }
}

async function createBonanza(bonanzaData) {
    try {
        const userId = getUserId();
        if (!userId) {
            showError('Session expired. Please login again.');
            return;
        }
        
        const response = await fetch(`/api/v1/rvz/awards-config/bonanzas?user_id=${userId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(bonanzaData)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showSuccess(result.message);
            await fetchBonanzas();
            await fetchSummary();
        } else {
            showError('Failed to create bonanza');
        }
    } catch (error) {
        console.error('Error creating bonanza:', error);
        showError('Error creating bonanza');
    }
}

async function updateBonanza(bonanzaId, updateData) {
    try {
        const userId = getUserId();
        if (!userId) {
            showError('Session expired. Please login again.');
            return;
        }
        
        const response = await fetch(`/api/v1/rvz/awards-config/bonanzas/${bonanzaId}?user_id=${userId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(updateData)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showSuccess(result.message);
            if (result.price_changed) {
                showInfo(`Price changed from ₹${result.old_price?.toLocaleString() || 0} to ₹${result.new_price?.toLocaleString() || 0}`);
            }
            await fetchBonanzas();
            await fetchSummary();
        } else {
            showError('Failed to update bonanza');
        }
    } catch (error) {
        console.error('Error updating bonanza:', error);
        showError('Error updating bonanza');
    }
}

async function deleteBonanza(bonanzaId, reason) {
    try {
        const userId = getUserId();
        if (!userId) {
            showError('Session expired. Please login again.');
            return;
        }
        
        const response = await fetch(`/api/v1/rvz/awards-config/bonanzas/${bonanzaId}?user_id=${userId}&deletion_reason=${encodeURIComponent(reason)}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.success) {
            showSuccess(result.message);
            await fetchBonanzas();
            await fetchSummary();
        } else {
            showError('Failed to delete bonanza');
        }
    } catch (error) {
        console.error('Error deleting bonanza:', error);
        showError('Error deleting bonanza');
    }
}

// ============================================================================
// RENDERING FUNCTIONS
// ============================================================================

function renderSummary() {
    const summaryContainer = document.getElementById('summary-container');
    if (!summaryContainer || !state.summary) return;
    
    const summary = state.summary;
    
    summaryContainer.innerHTML = `
        <div class="row g-3">
            <div class="col-md-3">
                <div class="card bg-primary text-white">
                    <div class="card-body">
                        <h6 class="card-title">Direct Facilitations</h6>
                        <h3>${summary.direct_awards.total_tiers}</h3>
                        <small>Total Cost: ₹${summary.direct_awards.total_budgeted_cost?.toLocaleString() || 0}</small>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card bg-info text-white">
                    <div class="card-body">
                        <h6 class="card-title">Group Performance Recognitions</h6>
                        <h3>${summary.matching_awards.total_tiers}</h3>
                        <small>Total Cost: ₹${summary.matching_awards.total_budgeted_cost?.toLocaleString() || 0}</small>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card bg-success text-white">
                    <div class="card-body">
                        <h6 class="card-title">Bonanzas</h6>
                        <h3>${summary.bonanzas.active_campaigns} / ${summary.bonanzas.total_campaigns}</h3>
                        <small>Budget: ₹${summary.bonanzas.total_budget_allocated?.toLocaleString() || 0}</small>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card bg-warning text-dark">
                    <div class="card-body">
                        <h6 class="card-title">Total Budget</h6>
                        <h3>₹${summary.overall.total_budgeted_amount?.toLocaleString() || 0}</h3>
                        <small>All Awards & Bonanzas</small>
                    </div>
                </div>
            </div>
        </div>
    `;
}

function renderDirectAwardsTable() {
    const tableContainer = document.getElementById('direct-awards-table');
    if (!tableContainer) return;
    
    if (state.directAwards.data.length === 0) {
        tableContainer.innerHTML = '<div class="alert alert-info">No direct awards found</div>';
        return;
    }
    
    let html = `
        <div class="table-responsive">
            <table class="table table-hover">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Rank</th>
                        <th>Award Item</th>
                        <th>Referrals</th>
                        <th>Achievers</th>
                        <th>Price (₹)</th>
                        <th>Cumulative</th>
                        <th>Last Updated</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    state.directAwards.data.forEach(award => {
        html += `
            <tr>
                <td>${award.id}</td>
                <td><strong>${award.award_name}</strong></td>
                <td><small class="text-muted">${award.award_item_name || award.award_description || '-'}</small></td>
                <td>${award.referral_count}</td>
                <td><span class="badge bg-info">${award.achievers_count || 0}</span></td>
                <td><span class="badge bg-success">₹${award.actual_price?.toLocaleString() || 0}</span></td>
                <td>${award.cumulative_required}</td>
                <td><small>${award.last_updated_at ? new Date(award.last_updated_at).toLocaleDateString() : 'N/A'}</small></td>
                <td>
                    <button class="btn btn-sm btn-primary" onclick="editDirectAward(${award.id})">
                        <i class="fas fa-edit"></i> Edit
                    </button>
                </td>
            </tr>
        `;
    });
    
    html += `
                </tbody>
            </table>
        </div>
        ${renderPagination('direct')}
    `;
    
    tableContainer.innerHTML = html;
}

function renderMatchingAwardsTable() {
    const tableContainer = document.getElementById('matching-awards-table');
    if (!tableContainer) return;
    
    if (state.matchingAwards.data.length === 0) {
        tableContainer.innerHTML = '<div class="alert alert-info">No matching awards found</div>';
        return;
    }
    
    let html = `
        <div class="table-responsive">
            <table class="table table-hover">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Rank</th>
                        <th>Award Item</th>
                        <th>Matches</th>
                        <th>Achievers</th>
                        <th>Price (₹)</th>
                        <th>Cumulative</th>
                        <th>Last Updated</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    state.matchingAwards.data.forEach(award => {
        html += `
            <tr>
                <td>${award.id}</td>
                <td><strong>${award.award_name}</strong></td>
                <td><small class="text-muted">${award.award_item_name || award.award_description || '-'}</small></td>
                <td>${award.match_count}</td>
                <td><span class="badge bg-info">${award.achievers_count || 0}</span></td>
                <td><span class="badge bg-success">₹${award.actual_price?.toLocaleString() || 0}</span></td>
                <td>${award.cumulative_required}</td>
                <td><small>${award.last_updated_at ? new Date(award.last_updated_at).toLocaleDateString() : 'N/A'}</small></td>
                <td>
                    <button class="btn btn-sm btn-primary" onclick="editMatchingAward(${award.id})">
                        <i class="fas fa-edit"></i> Edit
                    </button>
                </td>
            </tr>
        `;
    });
    
    html += `
                </tbody>
            </table>
        </div>
        ${renderPagination('matching')}
    `;
    
    tableContainer.innerHTML = html;
}

function renderBonanzasTable() {
    const tableContainer = document.getElementById('bonanzas-table');
    if (!tableContainer) return;
    
    if (state.bonanzas.data.length === 0) {
        tableContainer.innerHTML = '<div class="alert alert-info">No bonanzas found</div>';
        return;
    }
    
    let html = `
        <div class="table-responsive">
            <table class="table table-hover">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Name</th>
                        <th>Period</th>
                        <th>Criteria</th>
                        <th>Reward</th>
                        <th>Price (₹)</th>
                        <th>Achievers</th>
                        <th>Status</th>
                        <th>Winners</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    state.bonanzas.data.forEach(bonanza => {
        // Date-based status badges (DC Protocol)
        const statusBadge = bonanza.status === 'In Progress' ? 'bg-success' : 
                          bonanza.status === 'Future' ? 'bg-info' : 
                          bonanza.status === 'Lapsed' ? 'bg-danger' : 'bg-secondary';
        
        // Display reward text if available, otherwise show reward amount or award name
        const rewardDisplay = bonanza.reward_text || 
                             (bonanza.is_monetary ? `₹${bonanza.reward_amount?.toLocaleString() || 0}` : 
                              (bonanza.award_name || 'Award'));
        
        html += `
            <tr>
                <td>${bonanza.id}</td>
                <td><strong>${bonanza.name}</strong></td>
                <td><small>${new Date(bonanza.start_date).toLocaleDateString()} - ${new Date(bonanza.end_date).toLocaleDateString()}</small></td>
                <td>${bonanza.target_requirement} ${bonanza.criteria_type === 'direct_referral' ? 'refs' : 'matches'}</td>
                <td>
                    ${bonanza.is_monetary ? 
                        `<span class="badge bg-success">${rewardDisplay}</span>` : 
                        `<span class="badge bg-info">${rewardDisplay}</span>`
                    }
                </td>
                <td><strong>₹${bonanza.actual_price?.toLocaleString() || 0}</strong></td>
                <td><span class="badge bg-primary">${bonanza.achievers_count || 0}</span></td>
                <td><span class="badge ${statusBadge}">${bonanza.status}</span></td>
                <td>${bonanza.current_winners} / ${bonanza.max_winners}</td>
                <td>
                    <button class="btn btn-sm btn-primary" onclick="editBonanza(${bonanza.id})">
                        <i class="fas fa-edit"></i> Edit
                    </button>
                    <button class="btn btn-sm btn-danger" onclick="confirmDeleteBonanza(${bonanza.id}, '${bonanza.name}')">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            </tr>
        `;
    });
    
    html += `
                </tbody>
            </table>
        </div>
        ${renderPagination('bonanzas')}
    `;
    
    tableContainer.innerHTML = html;
}

function renderPagination(type) {
    const stateObj = state[type === 'direct' ? 'directAwards' : type === 'matching' ? 'matchingAwards' : 'bonanzas'];
    
    if (stateObj.totalPages <= 1) return '';
    
    return `
        <nav>
            <ul class="pagination justify-content-center">
                <li class="page-item ${stateObj.page === 1 ? 'disabled' : ''}">
                    <a class="page-link" href="#" onclick="changePage('${type}', ${stateObj.page - 1})">Previous</a>
                </li>
                <li class="page-item active">
                    <span class="page-link">Page ${stateObj.page} of ${stateObj.totalPages}</span>
                </li>
                <li class="page-item ${stateObj.page === stateObj.totalPages ? 'disabled' : ''}">
                    <a class="page-link" href="#" onclick="changePage('${type}', ${stateObj.page + 1})">Next</a>
                </li>
            </ul>
        </nav>
    `;
}

// ============================================================================
// UI INTERACTION FUNCTIONS
// ============================================================================

function switchTab(tab) {
    state.currentTab = tab;
    
    // Update tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`[data-tab="${tab}"]`).classList.add('active');
    
    // Show/hide tab content
    document.querySelectorAll('.tab-content-section').forEach(section => {
        section.style.display = 'none';
    });
    document.getElementById(`${tab}-tab-content`).style.display = 'block';
    
    // Load data for tab
    if (tab === 'direct') {
        fetchDirectAwards();
    } else if (tab === 'matching') {
        fetchMatchingAwards();
    } else if (tab === 'bonanzas') {
        fetchBonanzas();
    }
}

function applyFilters(type) {
    if (type === 'direct') {
        state.directAwards.page = 1;
        fetchDirectAwards();
    } else if (type === 'matching') {
        state.matchingAwards.page = 1;
        fetchMatchingAwards();
    } else if (type === 'bonanzas') {
        state.bonanzas.page = 1;
        fetchBonanzas();
    }
}

function resetFilters(type) {
    if (type === 'direct') {
        state.directAwards.filters = {
            search: '',
            priceMin: '',
            priceMax: '',
            sortBy: 'referral_count',
            sortOrder: 'asc'
        };
        document.getElementById('direct-search').value = '';
        document.getElementById('direct-price-min').value = '';
        document.getElementById('direct-price-max').value = '';
        fetchDirectAwards();
    } else if (type === 'matching') {
        state.matchingAwards.filters = {
            search: '',
            priceMin: '',
            priceMax: '',
            sortBy: 'match_count',
            sortOrder: 'asc'
        };
        document.getElementById('matching-search').value = '';
        document.getElementById('matching-price-min').value = '';
        document.getElementById('matching-price-max').value = '';
        fetchMatchingAwards();
    } else if (type === 'bonanzas') {
        state.bonanzas.filters = {
            search: '',
            status: '',
            rewardType: '',
            startDateFrom: '',
            startDateTo: '',
            priceMin: '',
            priceMax: '',
            sortBy: 'created_at',
            sortOrder: 'desc'
        };
        document.getElementById('bonanza-search').value = '';
        document.getElementById('bonanza-status').value = '';
        document.getElementById('bonanza-reward-type').value = '';
        document.getElementById('bonanza-start-from').value = '';
        document.getElementById('bonanza-start-to').value = '';
        document.getElementById('bonanza-price-min').value = '';
        document.getElementById('bonanza-price-max').value = '';
        fetchBonanzas();
    }
}

function changePage(type, newPage) {
    if (type === 'direct') {
        state.directAwards.page = newPage;
        fetchDirectAwards();
    } else if (type === 'matching') {
        state.matchingAwards.page = newPage;
        fetchMatchingAwards();
    } else if (type === 'bonanzas') {
        state.bonanzas.page = newPage;
        fetchBonanzas();
    }
}

function editDirectAward(tierId) {
    const award = state.directAwards.data.find(a => a.id === tierId);
    if (!award) return;
    
    // Show edit modal (will implement modal HTML in frontend page)
    const modalHtml = `
        <div class="modal-header">
            <h5 class="modal-title">Edit Direct Facilitation Award - Rank: ${award.award_name}</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
            <form id="edit-direct-form">
                <div class="mb-3">
                    <label class="form-label">Rank</label>
                    <input type="text" class="form-control" id="edit-direct-name" value="${award.award_name}">
                </div>
                <div class="mb-3">
                    <label class="form-label">Award Item</label>
                    <textarea class="form-control" id="edit-direct-desc">${award.award_description || ''}</textarea>
                </div>
                <div class="row">
                    <div class="col-md-6">
                        <div class="mb-3">
                            <label class="form-label">Price Range From (₹)</label>
                            <input type="number" class="form-control" id="edit-direct-price-from" value="${award.price_range_from || ''}">
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="mb-3">
                            <label class="form-label">Price Range To (₹)</label>
                            <input type="number" class="form-control" id="edit-direct-price-to" value="${award.price_range_to || ''}">
                        </div>
                    </div>
                </div>
                <div class="mb-3">
                    <label class="form-label">Price (₹) <span class="text-danger">*Affects Company Earnings*</span></label>
                    <input type="number" class="form-control" id="edit-direct-actual-price" value="${award.actual_price || ''}">
                </div>
                <div class="mb-3">
                    <label class="form-label">Cumulative Required</label>
                    <input type="number" class="form-control" id="edit-direct-cumulative" value="${award.cumulative_required || 0}">
                </div>
                <div class="mb-3">
                    <label class="form-label">Update Reason (for audit)</label>
                    <input type="text" class="form-control" id="edit-direct-reason" placeholder="e.g., Price adjustment due to market changes">
                </div>
            </form>
        </div>
        <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
            <button type="button" class="btn btn-primary" onclick="saveDirectAward(${tierId})">Save Changes</button>
        </div>
    `;
    
    document.getElementById('edit-modal-content').innerHTML = modalHtml;
    const modalElement = document.getElementById('editModal');
    const modal = new bootstrap.Modal(modalElement);
    
    // Fix aria-hidden accessibility error (MPE Protocol)
    modalElement.addEventListener('shown.bs.modal', function() {
        modalElement.removeAttribute('aria-hidden');
    });
    
    modal.show();
}

function editMatchingAward(tierId) {
    const award = state.matchingAwards.data.find(a => a.id === tierId);
    if (!award) return;
    
    const modalHtml = `
        <div class="modal-header">
            <h5 class="modal-title">Edit Group Performance Award - Rank: ${award.award_name}</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
            <form id="edit-matching-form">
                <div class="mb-3">
                    <label class="form-label">Rank</label>
                    <input type="text" class="form-control" id="edit-matching-name" value="${award.award_name}">
                </div>
                <div class="mb-3">
                    <label class="form-label">Award Item</label>
                    <textarea class="form-control" id="edit-matching-desc">${award.award_description || ''}</textarea>
                </div>
                <div class="row">
                    <div class="col-md-6">
                        <div class="mb-3">
                            <label class="form-label">Price Range From (₹)</label>
                            <input type="number" class="form-control" id="edit-matching-price-from" value="${award.price_range_from || ''}">
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="mb-3">
                            <label class="form-label">Price Range To (₹)</label>
                            <input type="number" class="form-control" id="edit-matching-price-to" value="${award.price_range_to || ''}">
                        </div>
                    </div>
                </div>
                <div class="mb-3">
                    <label class="form-label">Price (₹) <span class="text-danger">*Affects Company Earnings*</span></label>
                    <input type="number" class="form-control" id="edit-matching-actual-price" value="${award.actual_price || ''}">
                </div>
                <div class="mb-3">
                    <label class="form-label">Cumulative Required</label>
                    <input type="number" class="form-control" id="edit-matching-cumulative" value="${award.cumulative_required || 0}">
                </div>
                <div class="mb-3">
                    <label class="form-label">Update Reason (for audit)</label>
                    <input type="text" class="form-control" id="edit-matching-reason" placeholder="e.g., Price adjustment due to market changes">
                </div>
            </form>
        </div>
        <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
            <button type="button" class="btn btn-primary" onclick="saveMatchingAward(${tierId})">Save Changes</button>
        </div>
    `;
    
    document.getElementById('edit-modal-content').innerHTML = modalHtml;
    const modalElement = document.getElementById('editModal');
    const modal = new bootstrap.Modal(modalElement);
    
    // Fix aria-hidden accessibility error (MPE Protocol)
    modalElement.addEventListener('shown.bs.modal', function() {
        modalElement.removeAttribute('aria-hidden');
    });
    
    modal.show();
}

function showCreateBonanzaModal() {
    const modalHtml = `
        <div class="modal-header">
            <h5 class="modal-title">Create New Bonanza</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
            <form id="create-bonanza-form">
                <div class="mb-3">
                    <label class="form-label">Bonanza Name *</label>
                    <input type="text" class="form-control" id="create-bonanza-name" required>
                </div>
                <div class="row">
                    <div class="col-md-6">
                        <div class="mb-3">
                            <label class="form-label">Start Date *</label>
                            <input type="date" class="form-control" id="create-bonanza-start" required>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="mb-3">
                            <label class="form-label">End Date *</label>
                            <input type="date" class="form-control" id="create-bonanza-end" required>
                        </div>
                    </div>
                </div>
                <div class="row">
                    <div class="col-md-6">
                        <div class="mb-3">
                            <label class="form-label">Criteria Type *</label>
                            <select class="form-select" id="create-bonanza-criteria" required>
                                <option value="">Select...</option>
                                <option value="direct_referral">Direct Facilitation</option>
                                <option value="matching_points">Group Performance</option>
                            </select>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="mb-3">
                            <label class="form-label">Target Requirement *</label>
                            <input type="number" class="form-control" id="create-bonanza-target" required min="1">
                        </div>
                    </div>
                </div>
                <div class="row">
                    <div class="col-md-6">
                        <div class="mb-3">
                            <label class="form-label">Reward Type *</label>
                            <select class="form-select" id="create-bonanza-reward-type" required>
                                <option value="">Select...</option>
                                <option value="cash">Cash</option>
                                <option value="bonus">Bonus</option>
                                <option value="award">Award</option>
                                <option value="gift">Gift</option>
                            </select>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="mb-3">
                            <label class="form-label">Reward Amount (₹)</label>
                            <input type="number" class="form-control" id="create-bonanza-reward-amount" step="0.01">
                        </div>
                    </div>
                </div>
                <div class="mb-3">
                    <label class="form-label">Award Name (for Award/Gift types)</label>
                    <input type="text" class="form-control" id="create-bonanza-award-name">
                </div>
                <div class="mb-3">
                    <label class="form-label">Reward Text</label>
                    <textarea class="form-control" id="create-bonanza-reward-text" rows="2"></textarea>
                </div>
                <div class="mb-3">
                    <label class="form-label">Link to Award Tier (Optional)</label>
                    <select class="form-select" id="create-bonanza-linked-award">
                        <option value="">No Award Link</option>
                        <optgroup label="Direct Facilitations">
                            ${state.awardsDropdown.direct.map(award => 
                                `<option value="direct-${award.id}">${award.name} (${award.referral_count} refs)</option>`
                            ).join('')}
                        </optgroup>
                        <optgroup label="Group Performance Recognitions">
                            ${state.awardsDropdown.matching.map(award => 
                                `<option value="matching-${award.id}">${award.name} (${award.match_count} matches)</option>`
                            ).join('')}
                        </optgroup>
                    </select>
                </div>
                <div class="row">
                    <div class="col-md-6">
                        <div class="mb-3">
                            <label class="form-label">Total Budget (₹)</label>
                            <input type="number" class="form-control" id="create-bonanza-budget" step="0.01">
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="mb-3">
                            <label class="form-label">Max Winners</label>
                            <input type="number" class="form-control" id="create-bonanza-max-winners" value="50" min="1">
                        </div>
                    </div>
                </div>
                <div class="row">
                    <div class="col-md-4">
                        <div class="mb-3">
                            <label class="form-label">Price Range From (₹)</label>
                            <input type="number" class="form-control" id="create-bonanza-price-from" step="0.01">
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="mb-3">
                            <label class="form-label">Price Range To (₹)</label>
                            <input type="number" class="form-control" id="create-bonanza-price-to" step="0.01">
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="mb-3">
                            <label class="form-label">Price (₹)</label>
                            <input type="number" class="form-control" id="create-bonanza-actual-price" step="0.01">
                        </div>
                    </div>
                </div>
                <div class="form-check mb-3">
                    <input class="form-check-input" type="checkbox" id="create-bonanza-monetary" checked>
                    <label class="form-check-label" for="create-bonanza-monetary">
                        Is Monetary Reward
                    </label>
                </div>
                <div class="form-check mb-3">
                    <input class="form-check-input" type="checkbox" id="create-bonanza-counts-regular">
                    <label class="form-check-label" for="create-bonanza-counts-regular">
                        Counts Towards Regular Awards
                    </label>
                </div>
                <div class="form-check mb-3">
                    <input class="form-check-input" type="checkbox" id="create-bonanza-consume">
                    <label class="form-check-label" for="create-bonanza-consume">
                        Consume Achievements
                    </label>
                </div>
            </form>
        </div>
        <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
            <button type="button" class="btn btn-success" onclick="saveNewBonanza()">Create Bonanza</button>
        </div>
    `;
    
    document.getElementById('edit-modal-content').innerHTML = modalHtml;
    const modalElement = document.getElementById('editModal');
    const modal = new bootstrap.Modal(modalElement);
    
    // Fix aria-hidden accessibility error (MPE Protocol)
    modalElement.addEventListener('shown.bs.modal', function() {
        modalElement.removeAttribute('aria-hidden');
    });
    
    modal.show();
}

function editBonanza(bonanzaId) {
    const bonanza = state.bonanzas.data.find(b => b.id === bonanzaId);
    if (!bonanza) return;
    
    const modalHtml = `
        <div class="modal-header">
            <h5 class="modal-title">Edit Bonanza: ${bonanza.name}</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
            <form id="edit-bonanza-form">
                <div class="mb-3">
                    <label class="form-label">Bonanza Name</label>
                    <input type="text" class="form-control" id="edit-bonanza-name" value="${bonanza.name}" required>
                </div>
                <div class="row">
                    <div class="col-md-6">
                        <div class="mb-3">
                            <label class="form-label">Start Date</label>
                            <input type="date" class="form-control" id="edit-bonanza-start" value="${bonanza.start_date ? bonanza.start_date.split('T')[0] : ''}" required>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="mb-3">
                            <label class="form-label">End Date</label>
                            <input type="date" class="form-control" id="edit-bonanza-end" value="${bonanza.end_date ? bonanza.end_date.split('T')[0] : ''}" required>
                        </div>
                    </div>
                </div>
                <div class="row">
                    <div class="col-md-6">
                        <div class="mb-3">
                            <label class="form-label">Criteria Type</label>
                            <select class="form-select" id="edit-bonanza-criteria" required>
                                <option value="direct_referral" ${bonanza.criteria_type === 'direct_referral' ? 'selected' : ''}>Direct Facilitation</option>
                                <option value="matching_points" ${bonanza.criteria_type === 'matching_points' ? 'selected' : ''}>Group Performance</option>
                            </select>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="mb-3">
                            <label class="form-label">Target Requirement</label>
                            <input type="number" class="form-control" id="edit-bonanza-target" value="${bonanza.target_requirement}" required min="1">
                        </div>
                    </div>
                </div>
                <div class="row">
                    <div class="col-md-6">
                        <div class="mb-3">
                            <label class="form-label">Reward Type</label>
                            <select class="form-select" id="edit-bonanza-reward-type" required>
                                <option value="cash" ${bonanza.reward_type === 'cash' ? 'selected' : ''}>Cash</option>
                                <option value="bonus" ${bonanza.reward_type === 'bonus' ? 'selected' : ''}>Bonus</option>
                                <option value="award" ${bonanza.reward_type === 'award' ? 'selected' : ''}>Award</option>
                                <option value="gift" ${bonanza.reward_type === 'gift' ? 'selected' : ''}>Gift</option>
                            </select>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="mb-3">
                            <label class="form-label">Reward Amount (₹)</label>
                            <input type="number" class="form-control" id="edit-bonanza-reward-amount" value="${bonanza.reward_amount || ''}" step="0.01">
                        </div>
                    </div>
                </div>
                <div class="mb-3">
                    <label class="form-label">Award Name (for Award/Gift types)</label>
                    <input type="text" class="form-control" id="edit-bonanza-award-name" value="${bonanza.award_name || ''}">
                </div>
                <div class="mb-3">
                    <label class="form-label">Reward Text</label>
                    <textarea class="form-control" id="edit-bonanza-reward-text">${bonanza.reward_text || ''}</textarea>
                </div>
                <div class="mb-3">
                    <label class="form-label">Link to Award Tier (Optional)</label>
                    <select class="form-select" id="edit-bonanza-linked-award">
                        <option value="">No Award Link</option>
                        <optgroup label="Direct Facilitations">
                            ${state.awardsDropdown.direct.map(award => {
                                const isSelected = bonanza.linked_award_type === 'direct' && bonanza.linked_award_tier_id === award.id;
                                return `<option value="direct-${award.id}" ${isSelected ? 'selected' : ''}>${award.name} (${award.referral_count} refs)</option>`;
                            }).join('')}
                        </optgroup>
                        <optgroup label="Group Performance Recognitions">
                            ${state.awardsDropdown.matching.map(award => {
                                const isSelected = bonanza.linked_award_type === 'matching' && bonanza.linked_award_tier_id === award.id;
                                return `<option value="matching-${award.id}" ${isSelected ? 'selected' : ''}>${award.name} (${award.match_count} matches)</option>`;
                            }).join('')}
                        </optgroup>
                    </select>
                </div>
                <div class="row">
                    <div class="col-md-6">
                        <div class="mb-3">
                            <label class="form-label">Total Budget (₹)</label>
                            <input type="number" class="form-control" id="edit-bonanza-budget" value="${bonanza.total_budget || ''}" step="0.01">
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="mb-3">
                            <label class="form-label">Max Winners</label>
                            <input type="number" class="form-control" id="edit-bonanza-max-winners" value="${bonanza.max_winners || 50}" min="1">
                        </div>
                    </div>
                </div>
                <div class="row">
                    <div class="col-md-4">
                        <div class="mb-3">
                            <label class="form-label">Price Range From (₹)</label>
                            <input type="number" class="form-control" id="edit-bonanza-price-from" value="${bonanza.price_range_from || ''}" step="0.01">
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="mb-3">
                            <label class="form-label">Price Range To (₹)</label>
                            <input type="number" class="form-control" id="edit-bonanza-price-to" value="${bonanza.price_range_to || ''}" step="0.01">
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="mb-3">
                            <label class="form-label">Price (₹)</label>
                            <input type="number" class="form-control" id="edit-bonanza-actual-price" value="${bonanza.actual_price || ''}" step="0.01">
                        </div>
                    </div>
                </div>
                <div class="mb-3">
                    <label class="form-label">Status</label>
                    <select class="form-select" id="edit-bonanza-status">
                        <option value="Pending" ${bonanza.status === 'Pending' ? 'selected' : ''}>Pending</option>
                        <option value="Active" ${bonanza.status === 'Active' ? 'selected' : ''}>Active</option>
                        <option value="Completed" ${bonanza.status === 'Completed' ? 'selected' : ''}>Completed</option>
                        <option value="Cancelled" ${bonanza.status === 'Cancelled' ? 'selected' : ''}>Cancelled</option>
                    </select>
                </div>
                <div class="form-check mb-3">
                    <input class="form-check-input" type="checkbox" id="edit-bonanza-monetary" ${bonanza.is_monetary ? 'checked' : ''}>
                    <label class="form-check-label" for="edit-bonanza-monetary">
                        Is Monetary Reward
                    </label>
                </div>
                <div class="form-check mb-3">
                    <input class="form-check-input" type="checkbox" id="edit-bonanza-counts-regular" ${bonanza.counts_towards_regular ? 'checked' : ''}>
                    <label class="form-check-label" for="edit-bonanza-counts-regular">
                        Counts Towards Regular Awards
                    </label>
                </div>
                <div class="form-check mb-3">
                    <input class="form-check-input" type="checkbox" id="edit-bonanza-consume" ${bonanza.consume_achievements ? 'checked' : ''}>
                    <label class="form-check-label" for="edit-bonanza-consume">
                        Consume Achievements
                    </label>
                </div>
                <div class="mb-3">
                    <label class="form-label">Update Reason (for audit)</label>
                    <input type="text" class="form-control" id="edit-bonanza-reason" placeholder="e.g., Adjusted budget based on response">
                </div>
            </form>
        </div>
        <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
            <button type="button" class="btn btn-primary" onclick="saveBonanzaEdit(${bonanzaId})">Save Changes</button>
        </div>
    `;
    
    document.getElementById('edit-modal-content').innerHTML = modalHtml;
    const modalElement = document.getElementById('editModal');
    const modal = new bootstrap.Modal(modalElement);
    
    // Fix aria-hidden accessibility error (MPE Protocol)
    modalElement.addEventListener('shown.bs.modal', function() {
        modalElement.removeAttribute('aria-hidden');
    });
    
    modal.show();
}

function confirmDeleteBonanza(bonanzaId, bonanzaName) {
    if (confirm(`Are you sure you want to delete bonanza "${bonanzaName}"? This action cannot be undone.`)) {
        const reason = prompt('Enter deletion reason (minimum 5 characters):');
        if (reason && reason.length >= 5) {
            deleteBonanza(bonanzaId, reason);
        } else {
            showError('Deletion reason is required (minimum 5 characters)');
        }
    }
}

async function saveDirectAward(tierId) {
    const updateData = {
        award_name: document.getElementById('edit-direct-name').value,
        award_description: document.getElementById('edit-direct-desc').value,
        price_range_from: document.getElementById('edit-direct-price-from').value || null,
        price_range_to: document.getElementById('edit-direct-price-to').value || null,
        actual_price: document.getElementById('edit-direct-actual-price').value || null,
        cumulative_required: parseInt(document.getElementById('edit-direct-cumulative').value) || 0,
        update_reason: document.getElementById('edit-direct-reason').value || null
    };
    
    await updateDirectAward(tierId, updateData);
    bootstrap.Modal.getInstance(document.getElementById('editModal')).hide();
}

async function saveMatchingAward(tierId) {
    const updateData = {
        award_name: document.getElementById('edit-matching-name').value,
        award_description: document.getElementById('edit-matching-desc').value,
        price_range_from: document.getElementById('edit-matching-price-from').value || null,
        price_range_to: document.getElementById('edit-matching-price-to').value || null,
        actual_price: document.getElementById('edit-matching-actual-price').value || null,
        cumulative_required: parseInt(document.getElementById('edit-matching-cumulative').value) || 0,
        update_reason: document.getElementById('edit-matching-reason').value || null
    };
    
    await updateMatchingAward(tierId, updateData);
    bootstrap.Modal.getInstance(document.getElementById('editModal')).hide();
}

async function saveBonanzaEdit(bonanzaId) {
    const startDate = document.getElementById('edit-bonanza-start').value;
    const endDate = document.getElementById('edit-bonanza-end').value;
    const linkedAward = document.getElementById('edit-bonanza-linked-award').value;
    
    let linkedAwardType = null;
    let linkedAwardTierId = null;
    
    if (linkedAward) {
        const [type, id] = linkedAward.split('-');
        linkedAwardType = type;
        linkedAwardTierId = parseInt(id);
    }
    
    const updateData = {
        name: document.getElementById('edit-bonanza-name').value,
        start_date: startDate ? `${startDate}T00:00:00` : null,
        end_date: endDate ? `${endDate}T23:59:59` : null,
        criteria_type: document.getElementById('edit-bonanza-criteria').value,
        target_requirement: parseInt(document.getElementById('edit-bonanza-target').value),
        reward_type: document.getElementById('edit-bonanza-reward-type').value,
        reward_amount: parseFloat(document.getElementById('edit-bonanza-reward-amount').value) || null,
        award_name: document.getElementById('edit-bonanza-award-name').value || null,
        reward_text: document.getElementById('edit-bonanza-reward-text').value || null,
        total_budget: parseFloat(document.getElementById('edit-bonanza-budget').value) || null,
        max_winners: parseInt(document.getElementById('edit-bonanza-max-winners').value),
        price_range_from: parseFloat(document.getElementById('edit-bonanza-price-from').value) || null,
        price_range_to: parseFloat(document.getElementById('edit-bonanza-price-to').value) || null,
        actual_price: parseFloat(document.getElementById('edit-bonanza-actual-price').value) || null,
        linked_award_type: linkedAwardType,
        linked_award_tier_id: linkedAwardTierId,
        status: document.getElementById('edit-bonanza-status').value,
        is_monetary: document.getElementById('edit-bonanza-monetary').checked,
        counts_towards_regular: document.getElementById('edit-bonanza-counts-regular').checked,
        consume_achievements: document.getElementById('edit-bonanza-consume').checked,
        update_reason: document.getElementById('edit-bonanza-reason').value || null
    };
    
    await updateBonanza(bonanzaId, updateData);
    bootstrap.Modal.getInstance(document.getElementById('editModal')).hide();
}

async function saveNewBonanza() {
    const startDate = document.getElementById('create-bonanza-start').value;
    const endDate = document.getElementById('create-bonanza-end').value;
    const linkedAward = document.getElementById('create-bonanza-linked-award').value;
    
    let linkedAwardType = null;
    let linkedAwardTierId = null;
    
    if (linkedAward) {
        const [type, id] = linkedAward.split('-');
        linkedAwardType = type;
        linkedAwardTierId = parseInt(id);
    }
    
    const bonanzaData = {
        name: document.getElementById('create-bonanza-name').value,
        start_date: startDate ? `${startDate}T00:00:00` : null,
        end_date: endDate ? `${endDate}T23:59:59` : null,
        criteria_type: document.getElementById('create-bonanza-criteria').value,
        target_requirement: parseInt(document.getElementById('create-bonanza-target').value),
        reward_type: document.getElementById('create-bonanza-reward-type').value,
        reward_amount: parseFloat(document.getElementById('create-bonanza-reward-amount').value) || null,
        award_name: document.getElementById('create-bonanza-award-name').value || null,
        reward_text: document.getElementById('create-bonanza-reward-text').value || null,
        is_monetary: document.getElementById('create-bonanza-monetary').checked,
        total_budget: parseFloat(document.getElementById('create-bonanza-budget').value) || null,
        max_winners: parseInt(document.getElementById('create-bonanza-max-winners').value) || 50,
        price_range_from: parseFloat(document.getElementById('create-bonanza-price-from').value) || null,
        price_range_to: parseFloat(document.getElementById('create-bonanza-price-to').value) || null,
        actual_price: parseFloat(document.getElementById('create-bonanza-actual-price').value) || null,
        linked_award_type: linkedAwardType,
        linked_award_tier_id: linkedAwardTierId,
        reduced_target: null,
        counts_towards_regular: document.getElementById('create-bonanza-counts-regular').checked,
        consume_achievements: document.getElementById('create-bonanza-consume').checked
    };
    
    await createBonanza(bonanzaData);
    bootstrap.Modal.getInstance(document.getElementById('editModal')).hide();
}

// ============================================================================
// NOTIFICATION FUNCTIONS
// ============================================================================

function showSuccess(message) {
    showNotification(message, 'success');
}

function showError(message) {
    showNotification(message, 'danger');
}

function showInfo(message) {
    showNotification(message, 'info');
}

function showNotification(message, type) {
    const alertsContainer = document.getElementById('alerts-container');
    if (!alertsContainer) return;
    
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    alertsContainer.appendChild(alertDiv);
    
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    console.log('🎯 Initializing Awards Configuration page');
    
    // Load initial data
    fetchSummary();
    fetchAwardsDropdown();
    fetchDirectAwards();
    
    // Set up filter event listeners
    const setupFilterListeners = (type, searchId, priceMinId, priceMaxId) => {
        const searchInput = document.getElementById(searchId);
        const priceMinInput = document.getElementById(priceMinId);
        const priceMaxInput = document.getElementById(priceMaxId);
        
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                if (type === 'direct') {
                    state.directAwards.filters.search = e.target.value;
                } else if (type === 'matching') {
                    state.matchingAwards.filters.search = e.target.value;
                } else if (type === 'bonanzas') {
                    state.bonanzas.filters.search = e.target.value;
                }
            });
        }
        
        if (priceMinInput) {
            priceMinInput.addEventListener('input', (e) => {
                if (type === 'direct') {
                    state.directAwards.filters.priceMin = e.target.value;
                } else if (type === 'matching') {
                    state.matchingAwards.filters.priceMin = e.target.value;
                } else if (type === 'bonanzas') {
                    state.bonanzas.filters.priceMin = e.target.value;
                }
            });
        }
        
        if (priceMaxInput) {
            priceMaxInput.addEventListener('input', (e) => {
                if (type === 'direct') {
                    state.directAwards.filters.priceMax = e.target.value;
                } else if (type === 'matching') {
                    state.matchingAwards.filters.priceMax = e.target.value;
                } else if (type === 'bonanzas') {
                    state.bonanzas.filters.priceMax = e.target.value;
                }
            });
        }
    };
    
    setupFilterListeners('direct', 'direct-search', 'direct-price-min', 'direct-price-max');
    setupFilterListeners('matching', 'matching-search', 'matching-price-min', 'matching-price-max');
    setupFilterListeners('bonanzas', 'bonanza-search', 'bonanza-price-min', 'bonanza-price-max');
    
    // Set up tab click listeners
    document.querySelectorAll('[data-tab]').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const tab = e.target.closest('[data-tab]').getAttribute('data-tab');
            switchTab(tab);
        });
    });
    
    console.log('✅ Awards Configuration initialized successfully');
});
