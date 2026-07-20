// DC PROTOCOL: Unified Status Badge Mapping
// ALL admin pages MUST use this single source of truth for status labels

window.getDCProtocolStatusBadge = function(status) {
  const statusMap = {
    // APPROVAL WORKFLOW
    'Pending Approval': { 
      text: 'Pending Approval', 
      class: 'bg-warning text-dark', 
      icon: 'fa-clock' 
    },
    'Admin Approved': { 
      text: 'Admin Approved', 
      class: 'bg-secondary text-white', 
      icon: 'fa-check' 
    },
    
    // PROCUREMENT WORKFLOW (DC Protocol - Show EXACT database status values)
    'Procurement Pending': { 
      text: 'Procurement Pending', 
      class: 'bg-primary text-white', 
      icon: 'fa-check-double' 
    },
    'Processed for Dispatch': { 
      text: 'Processed for Dispatch', 
      class: 'bg-info text-white', 
      icon: 'fa-shopping-cart' 
    },
    'Dispatched': { 
      text: 'Dispatched', 
      class: 'bg-purple text-white', 
      icon: 'fa-shipping-fast' 
    },
    'Delivered': { 
      text: 'Delivered', 
      class: 'bg-success text-white', 
      icon: 'fa-check-circle' 
    },
    
    // REJECTION
    'Rejected': { 
      text: 'Rejected', 
      class: 'bg-danger text-white', 
      icon: 'fa-times-circle' 
    },
    
    // LEGACY STATUS VALUES (Backwards Compatibility - Map to DC Protocol)
    'Super Admin Approved': { 
      text: 'Ready for Procurement', 
      class: 'bg-primary text-white', 
      icon: 'fa-check-double' 
    },
    'Ready for Procurement': { 
      text: 'Ready for Procurement', 
      class: 'bg-primary text-white', 
      icon: 'fa-check-double' 
    },
    'Pending RVZ Approval': { 
      text: 'Pending Approval', 
      class: 'bg-warning text-dark', 
      icon: 'fa-clock' 
    },
    'Purchased - Pending Delivery': { 
      text: 'Ordered', 
      class: 'bg-info text-white', 
      icon: 'fa-shopping-cart' 
    },
    'Finance Processed': { 
      text: 'Ordered', 
      class: 'bg-info text-white', 
      icon: 'fa-shopping-cart' 
    },
    'Delivered - Completed': { 
      text: 'Delivered', 
      class: 'bg-success text-white', 
      icon: 'fa-check-circle' 
    },
    'RVZ Rejected': { 
      text: 'Rejected', 
      class: 'bg-danger text-white', 
      icon: 'fa-times-circle' 
    }
  };
  
  const badge = statusMap[status] || { 
    text: status || 'Unknown', 
    class: 'bg-secondary text-white', 
    icon: 'fa-question' 
  };
  
  return `<span class="badge ${badge.class}"><i class="fas ${badge.icon} me-1"></i>${badge.text}</span>`;
};

// DC PROTOCOL: Normalize legacy status values to DC Protocol equivalents
window.normalizeDCProtocolStatus = function(status) {
  const statusNormalization = {
    'Super Admin Approved': 'Procurement Pending',
    'Ready for Procurement': 'Procurement Pending',
    'Pending RVZ Approval': 'Pending Approval',
    'Purchased - Pending Delivery': 'Processed for Dispatch',
    'Finance Processed': 'Processed for Dispatch',
    'Delivered - Completed': 'Delivered',
    'RVZ Rejected': 'Rejected'
  };
  
  return statusNormalization[status] || status;
};

// Export for backwards compatibility
window.getStatusBadge = window.getDCProtocolStatusBadge;

console.log('✅ DC Protocol Unified Status Badges loaded');
