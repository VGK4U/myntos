// RVZ Award Approval Queue JavaScript  
// Build ID: 1762620500000 - FIX 1: Moved Amount column to end (before Actions) | FIX 2: Added Subtotals to all tables | FIX 3: Refactored event listeners with toggleBreakdown function

window.initAwardApprovalQueue = function() {
  console.log('🎯 Award Approval Queue initialized');
  
  const sessionToken = window.sessionToken;
  if (!sessionToken) {
    console.error('❌ Session token not found!');
    document.getElementById('awardsContent').innerHTML = 
      '<div class="alert alert-danger">Authentication error. Please refresh the page.</div>';
    return;
  }
  
  console.log('✅ Session token found, length:', sessionToken.length);
  
  let allDirectAwards = [];
  let allMatchingAwards = [];
  let allBonanzaAwards = [];
  
  // Sorting state
  let sortColumn = 'achieved_at';  // Default sort by date
  let sortDirection = 'desc';  // Newest first
  
  // Sorting function
  function sortAwards(awards, column, direction) {
    return awards.slice().sort((a, b) => {
      let valA, valB;
      
      if (column === 'user_id') {
        valA = a.user_id || '';
        valB = b.user_id || '';
      } else if (column === 'user_name') {
        valA = (a.user_name || '').toLowerCase();
        valB = (b.user_name || '').toLowerCase();
      } else if (column === 'achieved_at') {
        valA = new Date(a.achieved_at || 0);
        valB = new Date(b.achieved_at || 0);
      } else if (column === 'award_amount') {
        valA = a.award_amount || 0;
        valB = b.award_amount || 0;
      } else if (column === 'processed_status') {
        valA = a.processed_status || '';
        valB = b.processed_status || '';
      } else {
        return 0;
      }
      
      if (valA < valB) return direction === 'asc' ? -1 : 1;
      if (valA > valB) return direction === 'asc' ? 1 : -1;
      return 0;
    });
  }
  
  // Handle column header click for sorting
  window.handleSort = function(column) {
    if (sortColumn === column) {
      sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
      sortColumn = column;
      sortDirection = 'asc';
    }
    console.log(`📊 Sorting by ${sortColumn} ${sortDirection}`);
    renderFilteredAwards();
  };
  
  // Helper to create sortable column header
  function getSortableHeader(column, label) {
    const isActive = sortColumn === column;
    const icon = isActive 
      ? (sortDirection === 'asc' ? '▲' : '▼')
      : '⇅';
    const cursorStyle = 'cursor: pointer; user-select: none;';
    const colorStyle = isActive ? 'color: #0d6efd; font-weight: bold;' : '';
    
    return `<th onclick="handleSort('${column}')" style="${cursorStyle}${colorStyle}" title="Click to sort">
      ${label} <small>${icon}</small>
    </th>`;
  }
  
  // DC PROTOCOL: Dynamic status filtering with CHECKBOXES (multi-select)
  async function loadDynamicStatuses() {
    try {
      const res = await fetch('/api/v1/super-admin/awards/statuses', {
        headers: { 'Authorization': 'Bearer ' + sessionToken }
      });
      
      if (!res.ok) {
        console.warn('⚠️ Could not load dynamic statuses, using defaults');
        return;
      }
      
      const data = await res.json();
      if (data.success && data.statuses) {
        console.log(`✅ Loaded ${data.statuses.length} dynamic statuses:`, data.statuses);
        
        // Replace dropdown with checkbox system
        const statusFilterParent = document.getElementById('filterStatus')?.parentElement;
        if (!statusFilterParent) return;
        
        // Create new checkbox container
        const newHTML = `
          <div class="col-md-3">
            <label class="form-label d-flex justify-content-between align-items-center">
              <span>Status Filters</span>
              <div class="btn-group btn-group-sm">
                <button type="button" class="btn btn-outline-primary btn-sm" onclick="selectAllStatuses()">All</button>
                <button type="button" class="btn btn-outline-secondary btn-sm" onclick="deselectAllStatuses()">None</button>
              </div>
            </label>
            <div id="statusCheckboxContainer" class="border rounded p-2" style="max-height: 200px; overflow-y: auto; background-color: #f8f9fa;">
              ${data.statuses.map(status => {
                // Default: Check all EXCEPT "Delivered" and "Rejected"
                const isDefaultChecked = (status !== 'Delivered' && status !== 'Rejected');
                return `
                  <div class="form-check">
                    <input class="form-check-input status-checkbox" type="checkbox" value="${status}" id="status_${status.replace(/\s+/g, '_')}" ${isDefaultChecked ? 'checked' : ''} onchange="loadPendingAwards()">
                    <label class="form-check-label" for="status_${status.replace(/\s+/g, '_')}">
                      ${status}
                    </label>
                  </div>
                `;
              }).join('')}
            </div>
          </div>
        `;
        
        // Replace the old dropdown column
        statusFilterParent.outerHTML = newHTML;
        console.log('✅ Status filter replaced with checkbox system (auto-excluded: Delivered, Rejected)');
      }
    } catch (error) {
      console.error('❌ Error loading statuses:', error);
    }
  }
  
  // Helper: Select all status checkboxes
  window.selectAllStatuses = function() {
    document.querySelectorAll('.status-checkbox').forEach(cb => {
      cb.checked = true;
    });
    loadPendingAwards();
  };
  
  // Helper: Deselect all status checkboxes
  window.deselectAllStatuses = function() {
    document.querySelectorAll('.status-checkbox').forEach(cb => {
      cb.checked = false;
    });
    loadPendingAwards();
  };
  
  async function loadPendingAwards() {
    console.log('📡 Fetching awards from NEW UNIFIED API...');
    try {
      // DC PROTOCOL: Collect CHECKED status checkboxes (multi-select)
      const checkedStatuses = Array.from(document.querySelectorAll('.status-checkbox:checked'))
        .map(cb => cb.value);
      
      console.log(`🔍 Filtering by statuses: ${checkedStatuses.length > 0 ? checkedStatuses.join(', ') : 'ALL (no filter)'}`);
      
      // Build API URL for unified endpoint with CSV statuses
      let apiUrl = '/api/v1/unified-awards/list?limit=200';
      if (checkedStatuses.length > 0) {
        apiUrl += `&statuses=${checkedStatuses.map(s => encodeURIComponent(s)).join(',')}`;
      }
      
      const res = await fetch(apiUrl, {
        headers: { 'Authorization': 'Bearer ' + sessionToken }
      });
      console.log('📡 API Response status:', res.status);
      
      const data = await res.json();
      console.log('📡 API Response data:', data);
      
      if (!data.success) {
        throw new Error(data.detail || 'Failed to load awards');
      }
      
      // NEW: Split unified awards array by award_type
      const allAwards = data.awards || [];
      
      // DEBUG: Show all unique award_type values
      const uniqueTypes = [...new Set(allAwards.map(a => a.award_type))];
      console.log(`🔍 DEBUG: Unique award_type values in API response:`, uniqueTypes);
      console.log(`🔍 DEBUG: Total awards from API: ${allAwards.length}`);
      
      allDirectAwards = allAwards.filter(a => a.award_type === 'direct').map(mapUnifiedToLegacy);
      allMatchingAwards = allAwards.filter(a => a.award_type === 'matching').map(mapUnifiedToLegacy);
      allBonanzaAwards = allAwards.filter(a => a.award_type === 'bonanza').map(mapUnifiedToLegacy);
      
      console.log(`✅ Loaded ${allDirectAwards.length} direct, ${allMatchingAwards.length} matching, ${allBonanzaAwards.length} bonanza awards`);
      
      // DEBUG: Show first award of each type
      if (allDirectAwards.length > 0) console.log('📌 Sample direct award:', allDirectAwards[0]);
      if (allMatchingAwards.length > 0) console.log('📌 Sample matching award:', allMatchingAwards[0]);
      if (allBonanzaAwards.length > 0) console.log('📌 Sample bonanza award:', allBonanzaAwards[0]);
      
      // Populate gift name filter
      populateGiftNameFilter();
      
      renderFilteredAwards();
    } catch (error) {
      console.error('❌ Error loading awards:', error);
      document.getElementById('awardsContent').innerHTML = 
        '<div class="alert alert-danger">Error loading awards: ' + error.message + '</div>';
    }
  }
  
  // Map unified API response to legacy format for backward compatibility
  function mapUnifiedToLegacy(award) {
    return {
      id: award.award_id,
      award_type: award.award_type,
      user_id: award.user_id,
      user_name: award.user_name,
      award_name: award.rank_name || 'Unknown',
      award_description: award.gift_name,
      achieved_at: award.achievement_date,
      processed_status: award.processed_status,
      status_display: award.status_display,
      status_color: award.status_color,
      award_amount: award.budgeted_amount || 0,
      actual_cost_paid: award.actual_cost_paid,
      dispatch_date: award.dispatch_date,
      received_date: award.received_date,
      admin_approved_by: award.admin_approved_by,
      admin_name: award.admin_name,
      admin_approved_at: award.admin_approved_at,
      reward_text: award.gift_name,  // For bonanza compatibility
      available_actions: award.available_actions || []  // NEW: Dynamic actions
    };
  }
  
  // DC PROTOCOL: Expose to window scope for inline onchange handlers on checkboxes
  window.loadPendingAwards = loadPendingAwards;
  
  function populateGiftNameFilter() {
    const giftNames = new Set();
    
    // Collect unique gift names from all awards
    allDirectAwards.forEach(a => {
      if (a.award_description) giftNames.add(a.award_description);
    });
    allMatchingAwards.forEach(a => {
      if (a.award_description) giftNames.add(a.award_description);
    });
    allBonanzaAwards.forEach(a => {
      if (a.reward_text) giftNames.add(a.reward_text);
    });
    
    const filterSelect = document.getElementById('filterGiftName');
    filterSelect.innerHTML = '<option value="all">All Gifts</option>';
    
    Array.from(giftNames).sort().forEach(name => {
      const option = document.createElement('option');
      option.value = name;
      option.textContent = name;
      filterSelect.appendChild(option);
    });
  }
  
  window.applyFilters = function() {
    renderFilteredAwards();
  };
  
  // DC PROTOCOL: Use unified status badge mapping (single source of truth)
  function getStatusBadge(status) {
    // If unified-status-badges.js is loaded, use it
    if (typeof window.getDCProtocolStatusBadge === 'function') {
      return window.getDCProtocolStatusBadge(status);
    }
    
    // Fallback: Inline DC Protocol mapping
    const statusMap = {
      'Pending Approval': { text: 'Pending Approval', class: 'bg-warning text-dark', icon: 'fa-clock' },
      'Admin Approved': { text: 'Admin Approved', class: 'bg-secondary text-white', icon: 'fa-check' },
      'Procurement Pending': { text: 'Ready for Procurement', class: 'bg-primary text-white', icon: 'fa-check-double' },
      'Processed for Dispatch': { text: 'Ordered', class: 'bg-info text-white', icon: 'fa-shopping-cart' },
      'Dispatched': { text: 'Dispatched', class: 'bg-purple text-white', icon: 'fa-shipping-fast' },
      'Delivered': { text: 'Delivered', class: 'bg-success text-white', icon: 'fa-check-circle' },
      'Rejected': { text: 'Rejected', class: 'bg-danger text-white', icon: 'fa-times-circle' }
    };
    
    const badge = statusMap[status] || { text: status || 'Unknown', class: 'bg-secondary text-white', icon: 'fa-question' };
    return `<span class="badge ${badge.class}"><i class="fas ${badge.icon} me-1"></i>${badge.text}</span>`;
  }
  
  // DC PROTOCOL: Render action buttons from available_actions array
  function renderActionButtons(availableActions, awardId, awardType) {
    if (!availableActions || availableActions.length === 0) {
      return '<span class="text-muted"><i class="fas fa-lock"></i> No action available</span>';
    }
    
    const buttons = availableActions.map(action => {
      // Map action type to Bootstrap button class
      const btnClassMap = {
        'primary': 'btn-primary',
        'success': 'btn-success',
        'danger': 'btn-danger',
        'warning': 'btn-warning',
        'info': 'btn-info',
        'secondary': 'btn-secondary'
      };
      const btnClass = btnClassMap[action.type] || 'btn-secondary';
      
      // Determine if this action needs a modal or direct POST
      const requiresModal = action.requires_modal;
      const actionClass = requiresModal ? `award-action-modal-${action.action_id}` : `award-action-${action.action_id}`;
      
      return `
        <button class="btn btn-sm ${btnClass} ${actionClass}" 
                data-award-type="${awardType}" 
                data-award-id="${awardId}"
                data-action-id="${action.action_id}"
                data-action-endpoint="${action.api_endpoint || ''}"
                data-requires-modal="${requiresModal}">
          <i class="fas fa-${getIconForAction(action.action_id)}"></i> ${action.label}
        </button>`;
    }).join(' ');
    
    return buttons;
  }
  
  // Helper: Get icon for action type
  function getIconForAction(actionId) {
    const iconMap = {
      'finance_approve': 'check',
      'finance_reject': 'times',
      'vgk_direct_approve': 'bolt',
      'vgk_approve': 'check-circle',
      'vgk_reject': 'ban',
      'record_procurement': 'shopping-cart',
      'mark_dispatched': 'truck',
      'mark_delivered': 'check-double',
      'view_details': 'eye'
    };
    return iconMap[actionId] || 'cog';
  }
  
  function updateSummaryCards(filteredDirect, filteredMatching, filteredBonanza) {
    // Calculate totals
    const directCount = filteredDirect.length;
    const matchingCount = filteredMatching.length;
    const bonanzaCount = filteredBonanza.length;
    const totalCount = directCount + matchingCount + bonanzaCount;
    
    const directAmount = filteredDirect.reduce((sum, award) => sum + (award.award_amount || 0), 0);
    const matchingAmount = filteredMatching.reduce((sum, award) => sum + (award.award_amount || 0), 0);
    const bonanzaAmount = filteredBonanza.reduce((sum, award) => sum + (award.award_amount || 0), 0);
    const totalAmount = directAmount + matchingAmount + bonanzaAmount;
    
    // Update summary cards
    document.getElementById('totalAwardsCount').textContent = totalCount;
    document.getElementById('totalAwardsAmount').textContent = `₹${totalAmount.toLocaleString()}`;
    
    document.getElementById('directCount').textContent = directCount;
    document.getElementById('directAmount').textContent = `₹${directAmount.toLocaleString()}`;
    
    document.getElementById('matchingCount').textContent = matchingCount;
    document.getElementById('matchingAmount').textContent = `₹${matchingAmount.toLocaleString()}`;
    
    document.getElementById('bonanzaCount').textContent = bonanzaCount;
    document.getElementById('bonanzaAmount').textContent = `₹${bonanzaAmount.toLocaleString()}`;
  }
  
  function renderFilteredAwards() {
    const filterType = document.getElementById('filterAwardType').value;
    // DC PROTOCOL: Status filtering now handled by backend via checkboxes - removed client-side status filter
    const filterSearch = document.getElementById('filterUserId').value.toLowerCase().trim();
    const filterGiftName = document.getElementById('filterGiftName').value;
    const filterDateFrom = document.getElementById('filterDateFrom').value;
    const filterDateTo = document.getElementById('filterDateTo').value;
    
    let filteredDirect = allDirectAwards;
    let filteredMatching = allMatchingAwards;
    let filteredBonanza = allBonanzaAwards;
    
    if (filterType === 'matching') {
      filteredDirect = [];
      filteredBonanza = [];
    } else if (filterType === 'direct') {
      filteredMatching = [];
      filteredBonanza = [];
    } else if (filterType === 'bonanza') {
      filteredDirect = [];
      filteredMatching = [];
    }
    
    // Status filtering removed - now handled by backend based on checked checkboxes
    
    if (filterGiftName !== 'all') {
      filteredDirect = filteredDirect.filter(award => award.award_description === filterGiftName);
      filteredMatching = filteredMatching.filter(award => award.award_description === filterGiftName);
      filteredBonanza = filteredBonanza.filter(award => award.reward_text === filterGiftName);
    }
    
    if (filterSearch) {
      filteredDirect = filteredDirect.filter(award => 
        award.user_id.toLowerCase().includes(filterSearch) || 
        (award.user_name && award.user_name.toLowerCase().includes(filterSearch))
      );
      filteredMatching = filteredMatching.filter(award => 
        award.user_id.toLowerCase().includes(filterSearch) || 
        (award.user_name && award.user_name.toLowerCase().includes(filterSearch))
      );
      filteredBonanza = filteredBonanza.filter(award => 
        award.user_id.toLowerCase().includes(filterSearch) || 
        (award.user_name && award.user_name.toLowerCase().includes(filterSearch))
      );
    }
    
    if (filterDateFrom) {
      const fromDate = new Date(filterDateFrom);
      filteredDirect = filteredDirect.filter(award => new Date(award.achieved_at) >= fromDate);
      filteredMatching = filteredMatching.filter(award => new Date(award.achieved_at) >= fromDate);
      filteredBonanza = filteredBonanza.filter(award => new Date(award.achieved_at) >= fromDate);
    }
    
    if (filterDateTo) {
      const toDate = new Date(filterDateTo);
      toDate.setHours(23, 59, 59, 999);
      filteredDirect = filteredDirect.filter(award => new Date(award.achieved_at) <= toDate);
      filteredMatching = filteredMatching.filter(award => new Date(award.achieved_at) <= toDate);
      filteredBonanza = filteredBonanza.filter(award => new Date(award.achieved_at) <= toDate);
    }
    
    const totalFiltered = filteredDirect.length + filteredMatching.length + filteredBonanza.length;
    
    // Apply sorting to all filtered arrays
    filteredDirect = sortAwards(filteredDirect, sortColumn, sortDirection);
    filteredMatching = sortAwards(filteredMatching, sortColumn, sortDirection);
    filteredBonanza = sortAwards(filteredBonanza, sortColumn, sortDirection);
    
    // Update summary cards with filtered data
    updateSummaryCards(filteredDirect, filteredMatching, filteredBonanza);
    
    let html = '';
    
    if (filteredDirect.length > 0) {
      const totalDirectAmount = filteredDirect.reduce((sum, award) => sum + (award.award_amount || 0), 0);
      
      html += `
        <div class="mb-4">
          <h5 class="text-primary"><i class="fas fa-award"></i> Direct Facilitations (${filteredDirect.length})</h5>
          <div class="table-responsive">
            <table class="table table-hover">
              <thead>
                <tr>
                  <th width="30"></th>
                  ${getSortableHeader('user_id', 'User ID')}
                  ${getSortableHeader('user_name', 'Name')}
                  <th>Rank (Award Type)</th>
                  <th>Gift Name</th>
                  ${getSortableHeader('achieved_at', 'Achieved Date')}
                  ${getSortableHeader('processed_status', 'Status')}
                  <th>Dispatch Date</th>
                  <th>Received Date</th>
                  <th>Admin Info</th>
                  ${getSortableHeader('award_amount', 'Amount')}
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>`;
      
      filteredDirect.forEach(award => {
        // DC PROTOCOL: Show ACTUAL status from database, not hardcoded values
        const statusBadge = getStatusBadge(award.processed_status);
        
        const adminInfo = award.admin_approved_by 
          ? `<small>By: ${award.admin_name || award.admin_approved_by}<br>On: ${new Date(award.admin_approved_at).toLocaleString()}</small>`
          : '-';
        
        // DC PROTOCOL: Render action buttons from available_actions array
        const actionButtons = renderActionButtons(award.available_actions, award.id, 'direct');
        
        html += `
          <tr data-award-id="${award.id}" data-award-type="direct">
            <td>
              <button class="btn btn-sm btn-outline-primary expand-award-btn" 
                      data-award-id="${award.id}" 
                      data-award-type="direct"
                      title="Show achievement breakdown">
                <i class="fas fa-plus"></i>
              </button>
            </td>
            <td><strong>${award.user_id}</strong></td>
            <td>${award.user_name || 'Unknown'}</td>
            <td>${award.award_name || 'Unknown'}</td>
            <td><strong class="text-success">${award.award_description || 'N/A'}</strong></td>
            <td>${award.achieved_at ? new Date(award.achieved_at).toLocaleDateString() : 'N/A'}</td>
            <td>${statusBadge}</td>
            <td>${award.dispatch_date ? new Date(award.dispatch_date).toLocaleDateString('en-IN') : '–'}</td>
            <td>${award.received_date ? new Date(award.received_date).toLocaleDateString('en-IN') : '–'}</td>
            <td>${adminInfo}</td>
            <td><strong>₹${(award.award_amount || 0).toLocaleString()}</strong></td>
            <td>${actionButtons}</td>
          </tr>
          <tr class="breakdown-row breakdown-${award.id}" style="display: none;">
            <td colspan="12">
              <div class="p-3 bg-light">
                <div class="breakdown-content-${award.id}">
                  <div class="text-center text-muted">
                    <i class="fas fa-spinner fa-spin"></i> Loading breakdown...
                  </div>
                </div>
              </div>
            </td>
          </tr>`;
      });
      
      html += `
                <tr class="table-light fw-bold">
                  <td colspan="10" class="text-end">SUBTOTAL:</td>
                  <td>₹${totalDirectAmount.toLocaleString()}</td>
                  <td></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>`;
    }
    
    if (filteredMatching.length > 0) {
      const totalMatchingAmount = filteredMatching.reduce((sum, award) => sum + (award.award_amount || 0), 0);
      
      html += `
        <div class="mb-4">
          <h5 class="text-info"><i class="fas fa-trophy"></i> Group Performance Recognition Awards (${filteredMatching.length})</h5>
          <div class="table-responsive">
            <table class="table table-hover">
              <thead>
                <tr>
                  <th width="30"></th>
                  ${getSortableHeader('user_id', 'User ID')}
                  ${getSortableHeader('user_name', 'Name')}
                  <th>Rank (Award Type)</th>
                  <th>Gift Name</th>
                  ${getSortableHeader('achieved_at', 'Achieved Date')}
                  ${getSortableHeader('processed_status', 'Status')}
                  <th>Dispatch Date</th>
                  <th>Received Date</th>
                  <th>Admin Info</th>
                  ${getSortableHeader('award_amount', 'Amount')}
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>`;
      
      filteredMatching.forEach(award => {
        // DC PROTOCOL: Show ACTUAL status from database, not hardcoded values
        const statusBadge = getStatusBadge(award.processed_status);
        
        const adminInfo = award.admin_approved_by 
          ? `<small>By: ${award.admin_name || award.admin_approved_by}<br>On: ${new Date(award.admin_approved_at).toLocaleString()}</small>`
          : '-';
        
        // DC PROTOCOL: Render action buttons from available_actions array
        const actionButtons = renderActionButtons(award.available_actions, award.id, 'matching');
        
        html += `
          <tr data-award-id="${award.id}" data-award-type="matching">
            <td>
              <button class="btn btn-sm btn-outline-primary expand-award-btn" 
                      data-award-id="${award.id}" 
                      data-award-type="matching"
                      title="Show achievement breakdown">
                <i class="fas fa-plus"></i>
              </button>
            </td>
            <td><strong>${award.user_id}</strong></td>
            <td>${award.user_name || 'Unknown'}</td>
            <td>${award.award_name || 'Unknown'}</td>
            <td><strong class="text-success">${award.award_description || 'N/A'}</strong></td>
            <td>${award.achieved_at ? new Date(award.achieved_at).toLocaleDateString() : 'N/A'}</td>
            <td>${statusBadge}</td>
            <td>${award.dispatch_date ? new Date(award.dispatch_date).toLocaleDateString('en-IN') : '–'}</td>
            <td>${award.received_date ? new Date(award.received_date).toLocaleDateString('en-IN') : '–'}</td>
            <td>${adminInfo}</td>
            <td><strong>₹${(award.award_amount || 0).toLocaleString()}</strong></td>
            <td>${actionButtons}</td>
          </tr>
          <tr class="breakdown-row breakdown-${award.id}" style="display: none;">
            <td colspan="12">
              <div class="p-3 bg-light">
                <div class="breakdown-content-${award.id}">
                  <div class="text-center text-muted">
                    <i class="fas fa-spinner fa-spin"></i> Loading breakdown...
                  </div>
                </div>
              </div>
            </td>
          </tr>`;
      });
      
      html += `
                <tr class="table-light fw-bold">
                  <td colspan="10" class="text-end">SUBTOTAL:</td>
                  <td>₹${totalMatchingAmount.toLocaleString()}</td>
                  <td></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>`;
    }
    
    if (filteredBonanza.length > 0) {
      const totalBonanzaAmount = filteredBonanza.reduce((sum, award) => sum + (award.award_amount || 0), 0);
      
      html += `
        <div class="mb-4">
          <h5 class="text-success"><i class="fas fa-gift"></i> Bonanza Awards (${filteredBonanza.length})</h5>
          <div class="table-responsive">
            <table class="table table-hover">
              <thead>
                <tr>
                  <th style="width: 30px;"></th>
                  ${getSortableHeader('user_id', 'User ID')}
                  ${getSortableHeader('user_name', 'Name')}
                  <th>Bonanza Name</th>
                  <th>Gift Name</th>
                  ${getSortableHeader('achieved_at', 'Achieved Date')}
                  ${getSortableHeader('processed_status', 'Status')}
                  <th>Dispatch Date</th>
                  <th>Received Date</th>
                  <th>Admin Info</th>
                  ${getSortableHeader('award_amount', 'Amount')}
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>`;
      
      filteredBonanza.forEach(award => {
        // DC PROTOCOL: Show ACTUAL status from database, not hardcoded values
        const statusBadge = getStatusBadge(award.processed_status);
        
        const adminInfo = award.admin_approved_by 
          ? `<small>By: ${award.admin_name || award.admin_approved_by}<br>On: ${new Date(award.admin_approved_at).toLocaleString()}</small>`
          : '-';
        
        // DC PROTOCOL: Render action buttons from available_actions array
        const actionButtons = renderActionButtons(award.available_actions, award.id, 'bonanza');
        
        html += `
          <tr>
            <td>
              <button class="btn btn-sm btn-outline-primary expand-award-btn" data-award-type="bonanza" data-award-id="${award.id}" title="View Achievement Breakdown">
                <i class="fas fa-plus"></i>
              </button>
            </td>
            <td><strong>${award.user_id}</strong></td>
            <td>${award.user_name || 'Unknown'}</td>
            <td>${award.award_name || 'Unknown'}</td>
            <td><strong class="text-success">${award.reward_text || 'N/A'}</strong></td>
            <td>${award.achieved_at ? new Date(award.achieved_at).toLocaleDateString() : 'N/A'}</td>
            <td>${statusBadge}</td>
            <td>${award.dispatch_date ? new Date(award.dispatch_date).toLocaleDateString('en-IN') : '–'}</td>
            <td>${award.received_date ? new Date(award.received_date).toLocaleDateString('en-IN') : '–'}</td>
            <td>${adminInfo}</td>
            <td><strong>₹${(award.award_amount || 0).toLocaleString()}</strong></td>
            <td>${actionButtons}</td>
          </tr>
          <tr class="breakdown-row breakdown-${award.id}" style="display: none;">
            <td colspan="12">
              <div class="p-3 bg-light">
                <div class="breakdown-content-${award.id}">
                  <div class="text-center text-muted">
                    <i class="fas fa-spinner fa-spin"></i> Loading breakdown...
                  </div>
                </div>
              </div>
            </td>
          </tr>`;
      });
      
      html += `
                <tr class="table-light fw-bold">
                  <td colspan="10" class="text-end">SUBTOTAL:</td>
                  <td>₹${totalBonanzaAmount.toLocaleString()}</td>
                  <td></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>`;
    }
    
    if (totalFiltered === 0) {
      html = '<div class="alert alert-info"><i class="fas fa-info-circle"></i> No awards match your current filters.</div>';
    }
    
    document.getElementById('awardsContent').innerHTML = html;
    
    // Attach expand button event listeners
    document.querySelectorAll('.expand-award-btn').forEach(btn => {
      btn.addEventListener('click', function() {
        const awardId = this.dataset.awardId;
        const awardType = this.dataset.awardType;
        toggleBreakdown(awardId, awardType, this);
      });
    });
  }
  
  async function toggleBreakdown(awardId, awardType, btnElement) {
    const icon = btnElement.querySelector('i');
    const breakdownRow = document.querySelector(`.breakdown-${awardId}`);
    const breakdownContent = document.querySelector(`.breakdown-content-${awardId}`);
    
    if (!breakdownRow) {
      console.error('Breakdown row not found for award:', awardId);
      return;
    }
    
    // Toggle visibility
    if (breakdownRow.style.display === 'none') {
      // Expand - fetch and show breakdown
      breakdownRow.style.display = '';
      icon.classList.remove('fa-plus');
      icon.classList.add('fa-minus');
      
      try {
        console.log(`🔍 Fetching breakdown: ${awardType}/${awardId}`);
        const res = await fetch(`/api/v1/awards/breakdown/${awardType}/${awardId}`, {
          headers: { 'Authorization': 'Bearer ' + sessionToken }
        });
        
        console.log(`📡 API Response status: ${res.status}`);
        const data = await res.json();
        console.log('📊 API Response data:', data);
        
        if (!data.success) {
          throw new Error(data.detail || 'Failed to load breakdown');
        }
        
        // Render breakdown based on award type
        let html = '';
        
        if (awardType === 'direct') {
          html = renderDirectAwardBreakdown(data);
        } else if (awardType === 'matching') {
          html = renderMatchingAwardBreakdown(data);
        } else if (awardType === 'bonanza') {
          console.log('✅ Rendering bonanza breakdown with data:', {
            award_type: data.award_type,
            has_direct_members: !!data.direct_members_consumed,
            direct_count: data.direct_members_consumed ? data.direct_members_consumed.length : 0
          });
          html = renderBonanzaAwardBreakdown(data);
        }
        
        console.log('🎨 Rendered HTML length:', html.length);
        breakdownContent.innerHTML = html;
      } catch (error) {
        console.error('❌ Error loading breakdown:', error);
        breakdownContent.innerHTML = `
          <div class="alert alert-danger">
            <i class="fas fa-exclamation-triangle"></i> Error loading breakdown: ${error.message}
          </div>`;
      }
    } else {
      // Collapse
      breakdownRow.style.display = 'none';
      icon.classList.remove('fa-minus');
      icon.classList.add('fa-plus');
    }
  }
  
  function renderDirectAwardBreakdown(data) {
    let html = `
      <div class="row">
        <div class="col-md-12">
          <h6 class="text-primary mb-3">
            <i class="fas fa-users"></i> Direct Facilitation Achievement - ${data.award_name}
          </h6>
          <p class="mb-3">
            <strong>User:</strong> ${data.user_id} | 
            <strong>Incremental Requirement:</strong> <span class="badge bg-info">${data.incremental_requirement || data.requirement} referral members</span>
            ${data.previous_cumulative > 0 ? `<span class="text-muted small">(${data.previous_cumulative} already consumed by lower tiers)</span>` : ''} | 
            <strong>Current Achievement:</strong> <span class="badge bg-success">${data.current_achievement} points</span> | 
            <strong>Total Members:</strong> ${data.total_members}
          </p>
          
          <h6 class="text-success mb-2">
            <i class="fas fa-check-circle"></i> Contributing to This Award (${data.allocated_members.length} members)
          </h6>
          <table class="table table-sm table-bordered mb-3">
            <thead class="table-success">
              <tr>
                <th>#</th>
                <th>User ID</th>
                <th>Name</th>
                <th>Package</th>
                <th>Points</th>
                <th>Activation Date</th>
              </tr>
            </thead>
            <tbody>`;
    
    data.allocated_members.forEach((member, idx) => {
      const isPartial = member.partial && member.original_points;
      const pointsDisplay = isPartial 
        ? `<strong>${member.points}</strong> <span class="badge bg-warning text-dark" title="Partial: ${member.points} of ${member.original_points} pts">Partial</span>`
        : `<strong>${member.points}</strong>`;
      
      html += `
              <tr class="table-success">
                <td>${idx + 1}</td>
                <td><strong>${member.user_id}</strong></td>
                <td>${member.name}${isPartial ? ' <i class="fas fa-cut text-warning" title="Partially consumed"></i>' : ''}</td>
                <td><span class="badge ${member.package === 'Platinum' ? 'bg-primary' : 'bg-secondary'}">${member.package}</span></td>
                <td>${pointsDisplay}</td>
                <td>${member.activation_date ? new Date(member.activation_date).toLocaleDateString() : 'N/A'}</td>
              </tr>`;
    });
    
    html += `
            </tbody>
          </table>
        </div>
      </div>`;
    
    return html;
  }
  
  function renderMatchingAwardBreakdown(data) {
    let html = `
      <div class="row">
        <div class="col-md-12">
          <h6 class="text-info mb-3">
            <i class="fas fa-handshake"></i> Group Performance Achievement - ${data.award_name}
          </h6>
          <p class="mb-3">
            <strong>User:</strong> ${data.user_id} | 
            <strong>Incremental Requirement:</strong> <span class="badge bg-info">${data.incremental_requirement || data.requirement} pair matching</span>
            ${data.previous_cumulative > 0 ? `<span class="text-muted small">(${data.previous_cumulative} already consumed by lower tiers)</span>` : ''} | 
            <strong>Current Achievement:</strong> <span class="badge bg-success">${data.current_achievement} pairs</span>
          </p>
        </div>
      </div>
      <div class="row">
        <div class="col-md-6">
          <h6 class="text-success"><i class="fas fa-users"></i> Group A (${data.left_leg.points} points)</h6>
          <p class="text-muted small mb-2">Total Members: ${data.left_leg.total_members}</p>
          
          <strong class="text-success d-block mb-1">Contributing to This Award:</strong>
          <table class="table table-sm table-bordered mb-2">
            <thead class="table-success">
              <tr>
                <th>#</th>
                <th>User ID</th>
                <th>Name</th>
                <th>Package</th>
                <th>Points</th>
              </tr>
            </thead>
            <tbody>`;
    
    data.left_leg.allocated_members.forEach((member, idx) => {
      const isPartial = member.partial && member.original_points;
      const pointsDisplay = isPartial 
        ? `<strong>${member.points}</strong> <span class="badge bg-warning text-dark" title="Partial: ${member.points} of ${member.original_points} pts">Partial</span>`
        : `<strong>${member.points}</strong>`;
      
      html += `
              <tr class="table-success">
                <td>${idx + 1}</td>
                <td><strong>${member.user_id}</strong></td>
                <td>${member.name}${isPartial ? ' <i class="fas fa-cut text-warning" title="Partially consumed"></i>' : ''}</td>
                <td><span class="badge ${member.package === 'Platinum' ? 'bg-primary' : 'bg-secondary'}">${member.package}</span></td>
                <td>${pointsDisplay}</td>
              </tr>`;
    });
    
    html += `
            </tbody>
          </table>
        </div>
        <div class="col-md-6">
          <h6 class="text-warning"><i class="fas fa-users"></i> Group B (${data.right_leg.points} points)</h6>
          <p class="text-muted small mb-2">Total Members: ${data.right_leg.total_members}</p>
          
          <strong class="text-success d-block mb-1">Contributing to This Award:</strong>
          <table class="table table-sm table-bordered mb-2">
            <thead class="table-success">
              <tr>
                <th>#</th>
                <th>User ID</th>
                <th>Name</th>
                <th>Package</th>
                <th>Points</th>
              </tr>
            </thead>
            <tbody>`;
    
    data.right_leg.allocated_members.forEach((member, idx) => {
      const isPartial = member.partial && member.original_points;
      const pointsDisplay = isPartial 
        ? `<strong>${member.points}</strong> <span class="badge bg-warning text-dark" title="Partial: ${member.points} of ${member.original_points} pts">Partial</span>`
        : `<strong>${member.points}</strong>`;
      
      html += `
              <tr class="table-success">
                <td>${idx + 1}</td>
                <td><strong>${member.user_id}</strong></td>
                <td>${member.name}${isPartial ? ' <i class="fas fa-cut text-warning" title="Partially consumed"></i>' : ''}</td>
                <td><span class="badge ${member.package === 'Platinum' ? 'bg-primary' : 'bg-secondary'}">${member.package}</span></td>
                <td>${pointsDisplay}</td>
              </tr>`;
    });
    
    html += `
            </tbody>
          </table>
        </div>
      </div>`;
    
    return html;
  }
  
  function renderBonanzaAwardBreakdown(data) {
    let html = `
      <div class="row">
        <div class="col-md-12">
          <h6 class="text-success mb-3">
            <i class="fas fa-gift"></i> Bonanza Achievement Breakdown - ${data.bonanza_name}
          </h6>
          <p class="mb-3">
            <strong>User:</strong> ${data.user_id} | 
            <strong>Reward:</strong> ${data.reward_name} | 
            <strong>Amount:</strong> <span class="badge bg-success">₹${data.reward_amount.toLocaleString()}</span>
          </p>
        </div>
      </div>`;
    
    // MNR 2.0 Bonanza - Show individual contributors who were consumed
    if (data.award_type === 'bonanza_mnr2' || data.direct_members_consumed) {
      if (data.direct_members_consumed && data.direct_members_consumed.length > 0) {
        html += `
      <div class="row mb-4">
        <div class="col-md-12">
          <h6 class="text-primary mb-2">
            <i class="fas fa-users"></i> Direct Facilitations Consumed for This Bonanza
          </h6>
          <p class="mb-2">
            <strong>Points Deducted:</strong> <span class="badge bg-warning">${data.points_deducted_direct || 0} referral points</span>
            ${data.points_deducted_matching > 0 ? ` | <span class="badge bg-info">${data.points_deducted_matching} pair matching</span>` : ''}
          </p>
          
          <h6 class="text-success mb-2">
            <i class="fas fa-check-circle"></i> Individual Contributors (${data.direct_members_consumed.length} members)
          </h6>
          <table class="table table-sm table-bordered mb-3">
            <thead class="table-success">
              <tr>
                <th>#</th>
                <th>User ID</th>
                <th>Name</th>
                <th>Package</th>
                <th>Points</th>
                <th>Activation Date</th>
              </tr>
            </thead>
            <tbody>`;
        
        data.direct_members_consumed.forEach((member, idx) => {
          html += `
                <tr class="table-success">
                  <td>${idx + 1}</td>
                  <td><strong>${member.user_id}</strong></td>
                  <td>${member.name}</td>
                  <td><span class="badge ${member.package === 'Platinum' ? 'bg-primary' : 'bg-secondary'}">${member.package}</span></td>
                  <td><strong>${member.points}</strong></td>
                  <td>${member.activation_date ? new Date(member.activation_date).toLocaleDateString() : 'N/A'}</td>
                </tr>`;
        });
        
        html += `
            </tbody>
          </table>
        </div>
      </div>`;
      }
      
      // BONANZA: Show matching leg breakdown (follows matching awards pattern)
      if (data.matching_breakdown) {
        const mb = data.matching_breakdown;
        html += `
      <div class="row mb-4">
        <div class="col-md-12">
          <h6 class="text-info mb-2">
            <i class="fas fa-balance-scale"></i> Group Performance Consumed for This Bonanza
          </h6>
          <p class="mb-2">
            <strong>Pairs Consumed:</strong> <span class="badge bg-info">${mb.pairs_consumed || 0} pairs</span> | 
            <strong>Total Available:</strong> ${mb.total_pairs_available || 0} pairs
          </p>
        </div>
      </div>
      
      <div class="row">
        <!-- GROUP A -->
        <div class="col-md-6">
          <h6 class="text-primary mb-2">
            <i class="fas fa-users"></i> Group A (${mb.left_leg.total_members} members, ${mb.left_leg.points} points)
          </h6>
          <table class="table table-sm table-bordered">
            <thead class="table-primary">
              <tr>
                <th>#</th>
                <th>User ID</th>
                <th>Name</th>
                <th>Package</th>
                <th>Points</th>
              </tr>
            </thead>
            <tbody>`;
        
        if (mb.left_leg.members && mb.left_leg.members.length > 0) {
          mb.left_leg.members.forEach((member, idx) => {
            html += `
              <tr class="table-primary">
                <td>${idx + 1}</td>
                <td><strong>${member.user_id}</strong></td>
                <td>${member.name}</td>
                <td><span class="badge ${member.package === 'Platinum' ? 'bg-primary' : 'bg-secondary'}">${member.package}</span></td>
                <td><strong>${member.points}</strong></td>
              </tr>`;
          });
        } else {
          html += `
              <tr>
                <td colspan="5" class="text-center text-muted">No members in Group A</td>
              </tr>`;
        }
        
        html += `
            </tbody>
          </table>
        </div>
        
        <!-- GROUP B -->
        <div class="col-md-6">
          <h6 class="text-success mb-2">
            <i class="fas fa-users"></i> Group B (${mb.right_leg.total_members} members, ${mb.right_leg.points} points)
          </h6>
          <table class="table table-sm table-bordered">
            <thead class="table-success">
              <tr>
                <th>#</th>
                <th>User ID</th>
                <th>Name</th>
                <th>Package</th>
                <th>Points</th>
              </tr>
            </thead>
            <tbody>`;
        
        if (mb.right_leg.members && mb.right_leg.members.length > 0) {
          mb.right_leg.members.forEach((member, idx) => {
            html += `
              <tr class="table-success">
                <td>${idx + 1}</td>
                <td><strong>${member.user_id}</strong></td>
                <td>${member.name}</td>
                <td><span class="badge ${member.package === 'Platinum' ? 'bg-primary' : 'bg-secondary'}">${member.package}</span></td>
                <td><strong>${member.points}</strong></td>
              </tr>`;
          });
        } else {
          html += `
              <tr>
                <td colspan="5" class="text-center text-muted">No members in Group B</td>
              </tr>`;
        }
        
        html += `
            </tbody>
          </table>
        </div>
      </div>`;
      }
      
      if (data.matching_note) {
        html += `
      <div class="alert alert-info">
        <i class="fas fa-info-circle"></i> ${data.matching_note}
      </div>`;
      }
    }
    
    // OLD bonanza system - Show direct target breakdown if exists
    if (data.has_direct_target && data.direct_target) {
      html += `
      <div class="row mb-4">
        <div class="col-md-12">
          <h6 class="text-primary mb-2">
            <i class="fas fa-users"></i> Direct Facilitations Target
          </h6>
          <p class="mb-2">
            <strong>Requirement:</strong> ${data.direct_target.requirement} referrals | 
            <strong>Current Achievement:</strong> <span class="badge bg-success">${data.direct_target.current_achievement} points</span> | 
            <strong>Total Members:</strong> ${data.direct_target.total_members}
          </p>
          
          <h6 class="text-success mb-2">
            <i class="fas fa-check-circle"></i> Contributing to This Award (${data.direct_target.allocated_members.length} members)
          </h6>
          <table class="table table-sm table-bordered mb-3">
            <thead class="table-success">
              <tr>
                <th>#</th>
                <th>User ID</th>
                <th>Name</th>
                <th>Package</th>
                <th>Points</th>
                <th>Activation Date</th>
              </tr>
            </thead>
            <tbody>`;
      
      data.direct_target.allocated_members.forEach((member, idx) => {
        html += `
                <tr class="table-success">
                  <td>${idx + 1}</td>
                  <td><strong>${member.user_id}</strong></td>
                  <td>${member.name}</td>
                  <td><span class="badge ${member.package === 'Platinum' ? 'bg-primary' : 'bg-secondary'}">${member.package}</span></td>
                  <td><strong>${member.points}</strong></td>
                  <td>${member.activation_date ? new Date(member.activation_date).toLocaleDateString() : 'N/A'}</td>
                </tr>`;
      });
      
      html += `
            </tbody>
          </table>`;
      
      if (data.direct_target.surplus_members && data.direct_target.surplus_members.length > 0) {
        html += `
          <h6 class="text-muted mb-2">
            <i class="fas fa-plus-circle"></i> Additional Progress - ${data.direct_target.surplus_members.length} members
          </h6>
          <table class="table table-sm table-bordered">
            <thead class="table-light">
              <tr>
                <th>#</th>
                <th>User ID</th>
                <th>Name</th>
                <th>Package</th>
                <th>Points</th>
                <th>Activation Date</th>
              </tr>
            </thead>
            <tbody>`;
        
        data.direct_target.surplus_members.forEach((member, idx) => {
          html += `
                  <tr class="text-muted">
                    <td>${idx + 1}</td>
                    <td>${member.user_id}</td>
                    <td>${member.name}</td>
                    <td><span class="badge ${member.package === 'Platinum' ? 'bg-primary' : 'bg-secondary'}">${member.package}</span></td>
                    <td>${member.points}</td>
                    <td>${member.activation_date ? new Date(member.activation_date).toLocaleDateString() : 'N/A'}</td>
                  </tr>`;
        });
        
        html += `
                </tbody>
              </table>`;
      }
      
      html += `
        </div>
      </div>`;
    }
    
    // Show matching target breakdown if exists
    if (data.has_matching_target && data.matching_target) {
      html += `
      <div class="row">
        <div class="col-md-12">
          <h6 class="text-info mb-2">
            <i class="fas fa-handshake"></i> Group Performance Target
          </h6>
          <p class="mb-3">
            <strong>Requirement:</strong> ${data.matching_target.requirement} pair matching | 
            <strong>Current Achievement:</strong> <span class="badge bg-success">${data.matching_target.current_achievement} pairs</span>
          </p>
        </div>
      </div>
      <div class="row">
        <div class="col-md-6">
          <h6 class="text-success"><i class="fas fa-users"></i> Group A (${data.matching_target.left_leg.points} points)</h6>
          <p class="text-muted small mb-2">Total Members: ${data.matching_target.left_leg.total_members}</p>
          
          <strong class="text-success d-block mb-1">Contributing to This Award:</strong>
          <table class="table table-sm table-bordered mb-2">
            <thead class="table-success">
              <tr>
                <th>#</th>
                <th>User ID</th>
                <th>Name</th>
                <th>Package</th>
                <th>Points</th>
              </tr>
            </thead>
            <tbody>`;
      
      data.matching_target.left_leg.allocated_members.forEach((member, idx) => {
        html += `
                <tr class="table-success">
                  <td>${idx + 1}</td>
                  <td><strong>${member.user_id}</strong></td>
                  <td>${member.name}</td>
                  <td><span class="badge ${member.package === 'Platinum' ? 'bg-primary' : 'bg-secondary'}">${member.package}</span></td>
                  <td><strong>${member.points}</strong></td>
                </tr>`;
      });
      
      html += `
            </tbody>
          </table>
        </div>
        <div class="col-md-6">
          <h6 class="text-warning"><i class="fas fa-users"></i> Group B (${data.matching_target.right_leg.points} points)</h6>
          <p class="text-muted small mb-2">Total Members: ${data.matching_target.right_leg.total_members}</p>
          
          <strong class="text-success d-block mb-1">Contributing to This Award:</strong>
          <table class="table table-sm table-bordered mb-2">
            <thead class="table-success">
              <tr>
                <th>#</th>
                <th>User ID</th>
                <th>Name</th>
                <th>Package</th>
                <th>Points</th>
              </tr>
            </thead>
            <tbody>`;
      
      data.matching_target.right_leg.allocated_members.forEach((member, idx) => {
        html += `
                <tr class="table-success">
                  <td>${idx + 1}</td>
                  <td><strong>${member.user_id}</strong></td>
                  <td>${member.name}</td>
                  <td><span class="badge ${member.package === 'Platinum' ? 'bg-primary' : 'bg-secondary'}">${member.package}</span></td>
                  <td><strong>${member.points}</strong></td>
                </tr>`;
      });
      
      html += `
            </tbody>
          </table>
        </div>
      </div>`;
    }
    
    return html;
  }
  
  window.approveAward = async function(type, id) {
    if (!confirm('Approve this award with RVZ Supreme Authority?')) return;
    
    try {
      const res = await fetch(`/api/v1/super-admin/awards/${type}/${id}/decision`, {
        method: 'POST',
        headers: {
          'Authorization': 'Bearer ' + sessionToken,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ 
          decision: 'approve',
          notes: 'RVZ Supreme Authority Approval'
        })
      });
      
      const data = await res.json();
      if (!data.success && !res.ok) {
        throw new Error(data.detail || 'Failed to approve');
      }
      
      alert('✅ Award approved successfully!');
      loadPendingAwards();
    } catch (error) {
      alert('Error: ' + error.message);
    }
  };
  
  window.rejectAward = async function(type, id) {
    const rejectionReason = prompt('Enter rejection reason:');
    if (!rejectionReason) {
      alert('Rejection cancelled - reason required');
      return;
    }
    
    if (!confirm('Reject this award? This action cannot be undone.')) return;
    
    try {
      const res = await fetch(`/api/v1/super-admin/awards/${type}/${id}/decision`, {
        method: 'POST',
        headers: {
          'Authorization': 'Bearer ' + sessionToken,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ 
          decision: 'reject',
          notes: rejectionReason
        })
      });
      
      const data = await res.json();
      if (!data.success && !res.ok) {
        throw new Error(data.detail || 'Failed to reject');
      }
      
      alert('❌ Award rejected');
      loadPendingAwards();
    } catch (error) {
      alert('Error: ' + error.message);
    }
  };
  
  // DC PROTOCOL: Dynamic action button handler
  document.addEventListener('click', async function(e) {
    // Check if clicked element or parent button has an action-id
    const button = e.target.closest('button[data-action-id]');
    if (!button) return;
    
    const actionId = button.dataset.actionId;
    const awardType = button.dataset.awardType;
    const awardId = Number(button.dataset.awardId);
    const apiEndpoint = button.dataset.actionEndpoint;
    const requiresModal = button.dataset.requiresModal === 'true';
    
    console.log(`🎯 Action clicked: ${actionId} for ${awardType} award #${awardId}`);
    
    // Handle modal-based actions (reject, procurement, dispatch, delivery)
    if (requiresModal) {
      if (actionId === 'finance_reject' || actionId === 'vgk_reject') {
        const reason = prompt('Enter rejection reason:');
        if (!reason) return;
        
        try {
          const res = await fetch(apiEndpoint, {
            method: 'POST',
            headers: {
              'Authorization': 'Bearer ' + sessionToken,
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({
              award_type: awardType,
              award_id: awardId,
              rejection_reason: reason
            })
          });
          
          const data = await res.json();
          if (!res.ok) throw new Error(data.detail || 'Rejection failed');
          
          alert('✅ Award rejected successfully');
          loadPendingAwards();
        } catch (error) {
          alert('❌ Error: ' + error.message);
        }
      } else {
        alert(`⚠️ Modal for ${actionId} not yet implemented. Endpoint: ${apiEndpoint}`);
      }
    } else {
      // Handle direct actions (approve actions)
      if (actionId === 'finance_approve' || actionId === 'vgk_approve' || actionId === 'vgk_direct_approve') {
        if (!confirm(`Approve this ${awardType} award?`)) return;
        
        try {
          const res = await fetch(apiEndpoint, {
            method: 'POST',
            headers: {
              'Authorization': 'Bearer ' + sessionToken,
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({
              award_type: awardType,
              award_id: awardId
            })
          });
          
          const data = await res.json();
          if (!res.ok) throw new Error(data.detail || 'Approval failed');
          
          alert('✅ Award approved successfully');
          loadPendingAwards();
        } catch (error) {
          alert('❌ Error: ' + error.message);
        }
      }
    }
  });
  
  // Add auto-apply event listeners to all filters
  // This ensures ALL data tables and summary cards update when filters change
  ['filterAwardType', 'filterStatus', 'filterGiftName'].forEach(id => {
    const elem = document.getElementById(id);
    if (elem) {
      elem.addEventListener('change', function() {
        console.log(`🔄 Filter changed: ${id} = ${this.value}`);
        renderFilteredAwards();
      });
    }
  });
  
  // Search filter - auto-apply on input with debounce
  const searchInput = document.getElementById('filterUserId');
  if (searchInput) {
    let searchTimeout;
    searchInput.addEventListener('input', function() {
      clearTimeout(searchTimeout);
      searchTimeout = setTimeout(() => {
        console.log('🔍 Search filter applied:', this.value);
        renderFilteredAwards();
      }, 300); // 300ms debounce
    });
  }
  
  // Date filters - auto-apply on change
  ['filterDateFrom', 'filterDateTo'].forEach(id => {
    const elem = document.getElementById(id);
    if (elem) {
      elem.addEventListener('change', function() {
        console.log(`📅 Date filter changed: ${id} = ${this.value}`);
        renderFilteredAwards();
      });
    }
  });

  // DC PROTOCOL: Initialize dynamic status filtering system
  async function initialize() {
    await loadDynamicStatuses();  // Load statuses first
    await loadPendingAwards();    // Then load awards
  }
  
  initialize();
};

console.log('✅ rvz-award-approval.js loaded');
