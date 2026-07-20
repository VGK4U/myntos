const { createAdminHTML } = require('../templates/admin.js');

function createPayrollPage(page) {
  const pages = {
    'profiles': `<div class="container-fluid px-4">
      <div class="d-flex justify-content-between align-items-center mb-4">
        <h2><i class="fas fa-user-cog me-2"></i>Payroll Profiles</h2>
        <button class="btn btn-primary" id="addProfileBtn">
          <i class="fas fa-plus me-1"></i> Add Profile
        </button>
      </div>
      <div class="card mb-3">
        <div class="card-body py-2">
          <div class="row g-2 align-items-center">
            <div class="col-md-3">
              <div class="input-group input-group-sm">
                <span class="input-group-text"><i class="fas fa-search"></i></span>
                <input type="text" class="form-control" id="searchFilter" placeholder="Search employee name/code...">
              </div>
            </div>
            <div class="col-md-2">
              <select class="form-select form-select-sm" id="companyFilter">
                <option value="">All Companies</option>
              </select>
            </div>
            <div class="col-md-2">
              <select class="form-select form-select-sm" id="employmentTypeFilter">
                <option value="">All Types</option>
                <option value="ONROLE">On-Role</option>
                <option value="OFFROLE">Off-Role</option>
              </select>
            </div>
            <div class="col-md-2">
              <select class="form-select form-select-sm" id="statusFilter">
                <option value="true">Active Only</option>
                <option value="false">Inactive Only</option>
                <option value="">All Status</option>
              </select>
            </div>
            <div class="col-md-3 text-end">
              <button class="btn btn-sm btn-outline-secondary" id="resetFiltersBtn">
                <i class="fas fa-undo me-1"></i>Reset
              </button>
              <span class="ms-2 text-muted small" id="resultsCount"></span>
            </div>
          </div>
        </div>
      </div>
      <div class="card">
        <div class="card-body">
          <div class="table-responsive">
            <table class="table table-hover" id="profilesTable">
              <thead class="table-dark">
                <tr>
                  <th style="width: 50px;">S.No</th>
                  <th>Employee</th>
                  <th>Company</th>
                  <th>Employment Type</th>
                  <th>CTC</th>
                  <th>Tax Regime</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody id="profilesBody">
                <tr><td colspan="8" class="text-center">Loading...</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
      <script src="/public/js/payroll/profiles.js"></script>
    </div>`,

    'cycles': `<div class="container-fluid px-4">
      <div class="d-flex justify-content-between align-items-center mb-4">
        <h2><i class="fas fa-calendar-alt me-2"></i>Payroll Cycles</h2>
        <button class="btn btn-primary" id="createCycleBtn">
          <i class="fas fa-plus me-1"></i> Create Cycle
        </button>
      </div>
      <div class="card mb-3">
        <div class="card-body py-2">
          <div class="row g-2 align-items-center">
            <div class="col-md-2">
              <div class="input-group input-group-sm">
                <span class="input-group-text"><i class="fas fa-search"></i></span>
                <input type="text" class="form-control" id="searchFilter" placeholder="Search cycle code...">
              </div>
            </div>
            <div class="col-md-2">
              <select class="form-select form-select-sm" id="companyFilter">
                <option value="">All Companies</option>
              </select>
            </div>
            <div class="col-md-1">
              <select class="form-select form-select-sm" id="monthFilter">
                <option value="">All Months</option>
                <option value="1">January</option>
                <option value="2">February</option>
                <option value="3">March</option>
                <option value="4">April</option>
                <option value="5">May</option>
                <option value="6">June</option>
                <option value="7">July</option>
                <option value="8">August</option>
                <option value="9">September</option>
                <option value="10">October</option>
                <option value="11">November</option>
                <option value="12">December</option>
              </select>
            </div>
            <div class="col-md-1">
              <select class="form-select form-select-sm" id="yearFilter">
                <option value="">All Years</option>
                <option value="2026">2026</option>
                <option value="2025">2025</option>
                <option value="2024">2024</option>
              </select>
            </div>
            <div class="col-md-2">
              <select class="form-select form-select-sm" id="statusFilter">
                <option value="">All Status</option>
                <option value="DRAFT">Draft</option>
                <option value="ATTENDANCE_LOCKED">Attendance Locked</option>
                <option value="GENERATED">Generated</option>
                <option value="VALIDATED">Validated</option>
                <option value="APPROVED">Approved</option>
                <option value="PAID">Paid</option>
                <option value="CANCELLED">Cancelled</option>
              </select>
            </div>
            <div class="col-md-2">
              <input type="date" class="form-control form-control-sm" id="periodStartFilter" placeholder="Period Start">
            </div>
            <div class="col-md-2">
              <div class="d-flex align-items-center gap-1">
                <input type="date" class="form-control form-control-sm" id="periodEndFilter" placeholder="Period End">
                <button class="btn btn-sm btn-outline-secondary" id="resetFiltersBtn" title="Reset Filters">
                  <i class="fas fa-undo"></i>
                </button>
              </div>
            </div>
          </div>
          <div class="row mt-2">
            <div class="col-12 text-end">
              <span class="text-muted small" id="resultsCount"></span>
            </div>
          </div>
        </div>
      </div>
      <div class="card">
        <div class="card-body">
          <div class="table-responsive">
            <table class="table table-hover" id="cyclesTable">
              <thead class="table-dark">
                <tr>
                  <th style="width: 50px;">S.No</th>
                  <th>Cycle Code</th>
                  <th>Company</th>
                  <th>Month/Year</th>
                  <th>Period Start</th>
                  <th>Period End</th>
                  <th>Pay Date</th>
                  <th>Status</th>
                  <th>Employees</th>
                  <th>Total Payroll</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody id="cyclesBody">
                <tr><td colspan="11" class="text-center">Loading...</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
      <script src="/public/js/payroll/cycles.js"></script>
    </div>`,

    'runs': `<div class="container-fluid px-4">
      <div class="d-flex justify-content-between align-items-center mb-4">
        <h2><i class="fas fa-play-circle me-2"></i>Payroll Runs</h2>
        <select class="form-select d-inline-block w-auto" id="companyFilter">
          <option value="">All Companies</option>
        </select>
      </div>
      <div class="card">
        <div class="card-body">
          <div class="table-responsive">
            <table class="table table-hover" id="runsTable">
              <thead class="table-dark">
                <tr>
                  <th>Run Code</th>
                  <th>Cycle</th>
                  <th>Employee</th>
                  <th>Basic</th>
                  <th>HRA</th>
                  <th>Deductions</th>
                  <th>Net Pay</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody id="runsBody">
                <tr><td colspan="8" class="text-center">Loading...</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
      <script src="/public/js/payroll/runs.js"></script>
    </div>`,

    'approvals': `<div class="container-fluid px-4">
      <div class="d-flex justify-content-between align-items-center mb-4">
        <h2><i class="fas fa-check-circle me-2"></i>Payroll Approvals</h2>
      </div>
      <div class="card mb-3">
        <div class="card-body py-2">
          <div class="row g-2 align-items-center">
            <div class="col-md-2">
              <div class="input-group input-group-sm">
                <span class="input-group-text"><i class="fas fa-search"></i></span>
                <input type="text" class="form-control" id="searchFilter" placeholder="Search employee...">
              </div>
            </div>
            <div class="col-md-2">
              <select class="form-select form-select-sm" id="companyFilter">
                <option value="">All Companies</option>
              </select>
            </div>
            <div class="col-md-2">
              <select class="form-select form-select-sm" id="cycleFilter">
                <option value="">All Cycles</option>
              </select>
            </div>
            <div class="col-md-2">
              <select class="form-select form-select-sm" id="statusFilter">
                <option value="">All Status</option>
                <option value="PENDING">Pending</option>
                <option value="APPROVED">Approved</option>
                <option value="REJECTED">Rejected</option>
                <option value="PAID">Paid</option>
                <option value="CALCULATED">Calculated</option>
                <option value="VALIDATED">Validated</option>
              </select>
            </div>
            <div class="col-md-2">
              <select class="form-select form-select-sm" id="monthFilter">
                <option value="">All Months</option>
                <option value="1">January</option>
                <option value="2">February</option>
                <option value="3">March</option>
                <option value="4">April</option>
                <option value="5">May</option>
                <option value="6">June</option>
                <option value="7">July</option>
                <option value="8">August</option>
                <option value="9">September</option>
                <option value="10">October</option>
                <option value="11">November</option>
                <option value="12">December</option>
              </select>
            </div>
            <div class="col-md-2">
              <div class="d-flex align-items-center gap-1">
                <select class="form-select form-select-sm" id="yearFilter">
                  <option value="">All Years</option>
                  <option value="2026">2026</option>
                  <option value="2025">2025</option>
                  <option value="2024">2024</option>
                </select>
                <button class="btn btn-sm btn-outline-secondary" id="resetFiltersBtn" title="Reset Filters">
                  <i class="fas fa-undo"></i>
                </button>
              </div>
            </div>
          </div>
          <div class="row mt-2">
            <div class="col-12 text-end">
              <span class="text-muted small" id="resultsCount"></span>
            </div>
          </div>
        </div>
      </div>
      <div class="row mb-4">
        <div class="col-md-3">
          <div class="card bg-warning text-dark">
            <div class="card-body text-center py-2">
              <h4 id="pendingCount">0</h4>
              <small class="mb-0">Pending</small>
            </div>
          </div>
        </div>
        <div class="col-md-3">
          <div class="card bg-success text-white">
            <div class="card-body text-center py-2">
              <h4 id="approvedCount">0</h4>
              <small class="mb-0">Approved</small>
            </div>
          </div>
        </div>
        <div class="col-md-3">
          <div class="card bg-danger text-white">
            <div class="card-body text-center py-2">
              <h4 id="rejectedCount">0</h4>
              <small class="mb-0">Rejected</small>
            </div>
          </div>
        </div>
        <div class="col-md-3">
          <div class="card bg-primary text-white">
            <div class="card-body text-center py-2">
              <h4 id="totalNetPay">0</h4>
              <small class="mb-0">Total Net Pay</small>
            </div>
          </div>
        </div>
      </div>
      <div class="card">
        <div class="card-body">
          <div class="table-responsive">
            <table class="table table-hover" id="approvalsTable">
              <thead class="table-dark">
                <tr>
                  <th style="width: 50px;">S.No</th>
                  <th>Cycle</th>
                  <th>Employee</th>
                  <th>Total Days</th>
                  <th>Paid Days</th>
                  <th>Non Paid Days</th>
                  <th>Gross Pay</th>
                  <th>Basic</th>
                  <th>HRA</th>
                  <th>Gross</th>
                  <th>Deductions</th>
                  <th>Net Pay</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody id="approvalsBody">
                <tr><td colspan="14" class="text-center">Loading...</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
      <script src="/public/js/payroll/approvals.js"></script>
    </div>`,

    'consultant-invoices': `<div class="container-fluid px-4">
      <div class="d-flex justify-content-between align-items-center mb-4">
        <h2><i class="fas fa-file-invoice me-2"></i>Consultant Invoices</h2>
        <div>
          <select class="form-select d-inline-block w-auto me-2" id="companyFilter">
            <option value="">All Companies</option>
          </select>
          <button class="btn btn-primary" id="createInvoiceBtn">
            <i class="fas fa-plus me-1"></i> Create Invoice
          </button>
        </div>
      </div>
      <div class="card">
        <div class="card-body">
          <div class="table-responsive">
            <table class="table table-hover" id="invoicesTable">
              <thead class="table-dark">
                <tr>
                  <th>Invoice #</th>
                  <th>Employee</th>
                  <th>Service Period</th>
                  <th>Invoice Amount</th>
                  <th>GST</th>
                  <th>TDS</th>
                  <th>Net Payable</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody id="invoicesBody">
                <tr><td colspan="9" class="text-center">Loading...</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
      <script src="/public/js/payroll/consultant-invoices.js"></script>
    </div>`,

    'allowance-catalog': `<div class="container-fluid px-4">
      <div class="d-flex justify-content-between align-items-center mb-4">
        <h2><i class="fas fa-list-alt me-2"></i>Allowance Catalog</h2>
        <div>
          <select class="form-select d-inline-block w-auto me-2" id="companyFilter">
            <option value="">All Companies</option>
          </select>
          <button class="btn btn-primary" id="addAllowanceBtn">
            <i class="fas fa-plus me-1"></i> Add Custom Allowance
          </button>
        </div>
      </div>
      <div class="card">
        <div class="card-body">
          <div class="table-responsive">
            <table class="table table-hover" id="catalogTable">
              <thead class="table-dark">
                <tr>
                  <th>Code</th>
                  <th>Name</th>
                  <th>Company</th>
                  <th>Default Value</th>
                  <th>Taxable</th>
                  <th>Employment Types</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody id="catalogBody">
                <tr><td colspan="8" class="text-center">Loading...</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
      <script src="/public/js/payroll/allowance-catalog.js"></script>
    </div>`,

    'documents': `<div class="container-fluid px-4">
      <div class="d-flex justify-content-between align-items-center mb-4">
        <h2><i class="fas fa-file-pdf me-2"></i>Payroll Documents</h2>
      </div>
      
      <!-- Comprehensive Filters -->
      <div class="card mb-4">
        <div class="card-header bg-light py-2">
          <h6 class="mb-0"><i class="fas fa-filter me-1"></i> Filters</h6>
        </div>
        <div class="card-body">
          <div class="row g-3">
            <div class="col-md-3">
              <label class="form-label small text-muted">Search</label>
              <input type="text" class="form-control form-control-sm" id="searchInput" placeholder="Employee name, code, or document...">
            </div>
            <div class="col-md-2">
              <label class="form-label small text-muted">Company</label>
              <select class="form-select form-select-sm" id="companyFilter">
                <option value="">All Companies</option>
              </select>
            </div>
            <div class="col-md-2">
              <label class="form-label small text-muted">Document Type</label>
              <select class="form-select form-select-sm" id="documentTypeFilter">
                <option value="">All Types</option>
                <option value="PAYSLIP">Payslips</option>
                <option value="OFFER_LETTER">Offer Letters</option>
                <option value="SALARY_CERTIFICATE">Salary Certificates</option>
                <option value="FORM_16">Form 16</option>
              </select>
            </div>
            <div class="col-md-2">
              <label class="form-label small text-muted">Employee</label>
              <select class="form-select form-select-sm" id="employeeFilter">
                <option value="">All Employees</option>
              </select>
            </div>
            <div class="col-md-1">
              <label class="form-label small text-muted">Month</label>
              <select class="form-select form-select-sm" id="monthFilter">
                <option value="">All</option>
                <option value="1">Jan</option>
                <option value="2">Feb</option>
                <option value="3">Mar</option>
                <option value="4">Apr</option>
                <option value="5">May</option>
                <option value="6">Jun</option>
                <option value="7">Jul</option>
                <option value="8">Aug</option>
                <option value="9">Sep</option>
                <option value="10">Oct</option>
                <option value="11">Nov</option>
                <option value="12">Dec</option>
              </select>
            </div>
            <div class="col-md-1">
              <label class="form-label small text-muted">Year</label>
              <select class="form-select form-select-sm" id="yearFilter">
                <option value="">All</option>
                <option value="2026">2026</option>
                <option value="2025">2025</option>
                <option value="2024">2024</option>
              </select>
            </div>
            <div class="col-md-1 d-flex align-items-end">
              <button class="btn btn-outline-secondary btn-sm w-100" onclick="clearFilters()">
                <i class="fas fa-times"></i> Clear
              </button>
            </div>
          </div>
          <div class="row g-3 mt-1">
            <div class="col-md-2">
              <label class="form-label small text-muted">Date From</label>
              <input type="date" class="form-control form-control-sm" id="dateFromFilter">
            </div>
            <div class="col-md-2">
              <label class="form-label small text-muted">Date To</label>
              <input type="date" class="form-control form-control-sm" id="dateToFilter">
            </div>
          </div>
        </div>
      </div>
      
      <!-- Summary Cards -->
      <div class="row mb-4">
        <div class="col-md-3">
          <div class="card bg-primary text-white">
            <div class="card-body text-center py-3">
              <h3 id="totalDocs" class="mb-1">0</h3>
              <p class="mb-0 small">Total Documents</p>
            </div>
          </div>
        </div>
        <div class="col-md-3">
          <div class="card bg-success text-white">
            <div class="card-body text-center py-3">
              <h3 id="payslipCount" class="mb-1">0</h3>
              <p class="mb-0 small">Payslips</p>
            </div>
          </div>
        </div>
        <div class="col-md-3">
          <div class="card bg-info text-white">
            <div class="card-body text-center py-3">
              <h3 id="offerLetterCount" class="mb-1">0</h3>
              <p class="mb-0 small">Offer Letters</p>
            </div>
          </div>
        </div>
        <div class="col-md-3">
          <div class="card bg-warning text-dark">
            <div class="card-body text-center py-3">
              <h3 id="otherDocsCount" class="mb-1">0</h3>
              <p class="mb-0 small">Other Documents</p>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Documents Table -->
      <div class="card">
        <div class="card-body">
          <div class="table-responsive">
            <table class="table table-hover" id="documentsTable">
              <thead class="table-dark">
                <tr>
                  <th>Document Code</th>
                  <th>Type</th>
                  <th>Employee</th>
                  <th>Company</th>
                  <th>Title</th>
                  <th>Date</th>
                  <th class="text-center">Downloads</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody id="documentsBody">
                <tr><td colspan="8" class="text-center">Loading...</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
      <script src="/public/js/payroll/documents.js"></script>
    </div>`
  };

  return pages[page] || '<div class="container-fluid px-4"><div class="alert alert-danger">Page not found</div></div>';
}

function handlePayrollRoute(pathname) {
  const routes = {
    '/staff/payroll/profiles': 'profiles',
    '/staff/payroll/cycles': 'cycles',
    '/staff/payroll/runs': 'runs',
    '/staff/payroll/approvals': 'approvals',
    '/staff/payroll/consultant-invoices': 'consultant-invoices',
    '/staff/payroll/allowance-catalog': 'allowance-catalog',
    '/staff/payroll/documents': 'documents'
  };

  const page = routes[pathname];
  if (!page) return null;

  const titles = {
    'profiles': 'Payroll Profiles',
    'cycles': 'Payroll Cycles',
    'runs': 'Payroll Runs',
    'approvals': 'Payroll Approvals',
    'consultant-invoices': 'Consultant Invoices',
    'allowance-catalog': 'Allowance Catalog',
    'documents': 'Payroll Documents'
  };

  return {
    html: createAdminHTML(titles[page], createPayrollPage(page)),
    title: titles[page]
  };
}

module.exports = { handlePayrollRoute, createPayrollPage };
