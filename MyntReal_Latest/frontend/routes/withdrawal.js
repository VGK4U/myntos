// Withdrawal Routes Module
// Handles all withdrawal workflow pages across all roles

const { createHTML } = require('../templates/user.js');
const { createAdminHTML } = require('../templates/admin.js');
const { createSuperAdminHTML } = require('../templates/superadmin.js');
const { createFinanceAdminHTML } = require('../templates/finance.js');
const { createRVZHTML } = require('../templates/rvz.js');

// Helper to create simple HTML content without complex escaping
function createWithdrawalPage(role, page) {
  // Simple pages with data-* attributes instead of onclick handlers
  const pages = {
    'user-summary': `<div class="container-fluid px-4">
      <h2 class="mb-4">Withdrawal Summary</h2>
      <div class="card"><div class="card-body"><div id="withdrawalData">Loading...</div></div></div>
      <script src="/js/withdrawal-user-summary.js"></script>
    </div>`,
    
    'user-history': `<div class="container-fluid px-4">
      <h2 class="mb-4">Withdrawal History</h2>
      <div class="card"><div class="card-body"><table class="table" id="historyTable"></table></div></div>
      <script src="/js/withdrawal-user-history.js"></script>
    </div>`,
    
    'admin-queue': `<div class="container-fluid px-4">
      <h2 class="mb-4">Pending Withdrawals</h2>
      <div class="card"><div class="card-body"><div id="queueData">Loading...</div></div></div>
      <script>
        fetch("/api/v1/withdrawals/admin/withdrawal-report?status=PENDING", {credentials: "include"})
          .then(r => r.json()).then(d => {
            const div = document.getElementById("queueData");
            div.innerHTML = d.withdrawals && d.withdrawals.length > 0 ? 
              "Found " + d.withdrawals.length + " pending withdrawal(s)" : "No pending withdrawals";
          });
      </script>
    </div>`,
    
    'admin-history': `<div class="container-fluid px-4">
      <h2 class="mb-4">Withdrawal History</h2>
      <div class="card"><div class="card-body"><div id="historyData">Loading...</div></div></div>
    </div>`,
    
    'superadmin-approvals': `<div class="container-fluid px-4">
      <h2 class="mb-4">Approval Queue</h2>
      <div class="card"><div class="card-body"><div id="approvalData">Loading...</div></div></div>
    </div>`,
    
    'superadmin-history': `<div class="container-fluid px-4">
      <h2 class="mb-4">Approval History</h2>
      <div class="card"><div class="card-body"><div id="historyData">Loading...</div></div></div>
    </div>`,
    
    'finance-transfers': `<div class="container-fluid px-4">
      <h2 class="mb-4">Bank Transfer Queue</h2>
      <div class="card"><div class="card-body"><div id="transferData">Loading...</div></div></div>
    </div>`,
    
    'finance-history': `<div class="container-fluid px-4">
      <h2 class="mb-4">Transfer History</h2>
      <div class="card"><div class="card-body"><div id="historyData">Loading...</div></div></div>
    </div>`,
    
    'rvz-dashboard': `<div class="container-fluid px-4">
      <h2 class="mb-4">RVZ Withdrawal Dashboard</h2>
      <div class="card"><div class="card-body"><div id="vgkData">Loading RVZ withdrawal overview...</div></div></div>
    </div>`
  };
  
  return pages[role + '-' + page] || '<div>Page not found</div>';
}

module.exports = { createWithdrawalPage };
