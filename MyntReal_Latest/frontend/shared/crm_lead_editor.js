/**
 * Unified CRM Lead Editor Component
 * DC Protocol Compliant - Single source of truth for lead editing across all portals
 * Created: Dec 31, 2025
 * 
 * Features:
 * - Status-based field visibility (won shows deal values/transactions)
 * - MNR Assignment (Handler, Guru, Adi Guru)
 * - Staff Assignment (Tele Caller, Field Staff, Partner) with pre-population
 * - Deal Value tracking for won deals
 * - Transaction management
 * - Task creation
 * - Role-based access control
 */

class CRMLeadEditor {
    constructor(options = {}) {
        this.containerId = options.containerId || 'crmLeadEditorContainer';
        this.modalId = options.modalId || 'unifiedLeadEditModal';
        this.onSave = options.onSave || (() => {});
        this.onClose = options.onClose || (() => {});
        this.userRole = options.userRole || 'staff';
        this.companyId = options.companyId || null;
        this.apiBasePath = options.apiBasePath || '/api/v1/crm';
        this.authOptions = options.authOptions || { credentials: 'include' };
        
        this.currentLead = null;
        this.searchTimeouts = {};
        this.initialized = false;
        this.leadDeals = [];
        this.leadTransactions = [];
        this.dealCategoriesCache = {};
        
        console.log('[DC-CRM-EDITOR] Initializing CRM Lead Editor v1.0');
    }
    
    init() {
        if (this.initialized) return;
        this.createModal();
        this.bindEvents();
        this.initialized = true;
        console.log('[DC-CRM-EDITOR] Initialized successfully');
    }
    
    createModal() {
        const container = document.getElementById(this.containerId) || document.body;
        
        const modalHtml = `
        <div class="modal fade" id="${this.modalId}" tabindex="-1" data-bs-backdrop="static">
            <div class="modal-dialog modal-xl">
                <div class="modal-content">
                    <div class="modal-header bg-success text-white">
                        <h5 class="modal-title"><i class="fas fa-edit me-2"></i>Edit Lead</h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <input type="hidden" id="ule_leadId">
                        <input type="hidden" id="ule_companyId">

                        <!-- DC Protocol N001: VGK Member Status Banner (lazy-loaded) -->
                        <div id="ule_vgkBanner" style="margin-bottom:12px"></div>

                        <!-- Basic Info Section -->
                        <div class="row g-3 mb-4">
                            <div class="col-12">
                                <h6 class="text-primary border-bottom pb-2"><i class="fas fa-info-circle me-2"></i>Lead Information</h6>
                            </div>
                            <div class="col-md-3">
                                <label class="form-label fw-bold">Lead Name</label>
                                <input type="text" class="form-control" id="ule_leadName">
                            </div>
                            <div class="col-md-3">
                                <label class="form-label fw-bold">Phone</label>
                                <input type="text" class="form-control" id="ule_phone">
                            </div>
                            <div class="col-md-3">
                                <label class="form-label fw-bold">Email</label>
                                <input type="email" class="form-control" id="ule_email">
                            </div>
                            <div class="col-md-3">
                                <label class="form-label fw-bold">Status</label>
                                <select class="form-select" id="ule_status">
                                    <option value="new">New</option>
                                    <option value="contacted">Contacted</option>
                                    <option value="interested">Interested</option>
                                    <option value="qualified">Qualified</option>
                                    <option value="proposal">Proposal</option>
                                    <option value="loan_process">Loan Process</option>
                                    <option value="won">Won</option>
                                    <option value="completed">Completed</option>
                                    <option value="lost">Lost</option>
                                    <option value="on_hold">On Hold</option>
                                </select>
                            </div>
                            <div class="col-md-3">
                                <label class="form-label fw-bold">Priority</label>
                                <select class="form-select" id="ule_priority">
                                    <option value="low">Low</option>
                                    <option value="medium">Medium</option>
                                    <option value="high">High</option>
                                    <option value="urgent">Urgent</option>
                                </select>
                            </div>
                            <div class="col-md-3">
                                <label class="form-label fw-bold">Next Follow-up</label>
                                <input type="datetime-local" class="form-control" id="ule_nextFollowupDate">
                            </div>
                            <div class="col-md-3">
                                <label class="form-label fw-bold">Category</label>
                                <input type="text" class="form-control" id="ule_category" readonly>
                            </div>
                            <div class="col-md-3">
                                <label class="form-label fw-bold">Source</label>
                                <input type="text" class="form-control" id="ule_source">
                            </div>
                            <div class="col-md-6">
                                <label class="form-label fw-bold">Looking For</label>
                                <input type="text" class="form-control" id="ule_lookingFor">
                            </div>
                            <div class="col-md-6">
                                <label class="form-label fw-bold">Description</label>
                                <input type="text" class="form-control" id="ule_description">
                            </div>
                            <div class="col-12">
                                <a class="text-muted small" data-bs-toggle="collapse" href="#ule_locationSection" role="button">
                                    <i class="fas fa-map-marker-alt me-1"></i>Location & Budget Details <i class="fas fa-chevron-down ms-1"></i>
                                </a>
                            </div>
                            <div class="collapse" id="ule_locationSection">
                                <div class="row g-3 mt-1">
                                    <div class="col-md-3">
                                        <label class="form-label">City</label>
                                        <input type="text" class="form-control form-control-sm" id="ule_city">
                                    </div>
                                    <div class="col-md-3">
                                        <label class="form-label">Area</label>
                                        <input type="text" class="form-control form-control-sm" id="ule_area">
                                    </div>
                                    <div class="col-md-3">
                                        <label class="form-label">State</label>
                                        <input type="text" class="form-control form-control-sm" id="ule_state">
                                    </div>
                                    <div class="col-md-3">
                                        <label class="form-label">Pincode</label>
                                        <input type="text" class="form-control form-control-sm" id="ule_pincode" maxlength="10">
                                    </div>
                                    <div class="col-md-3">
                                        <label class="form-label">Budget Min</label>
                                        <input type="number" class="form-control form-control-sm" id="ule_budgetMin" min="0" step="0.01">
                                    </div>
                                    <div class="col-md-3">
                                        <label class="form-label">Budget Max</label>
                                        <input type="number" class="form-control form-control-sm" id="ule_budgetMax" min="0" step="0.01">
                                    </div>
                                    <div class="col-md-6">
                                        <label class="form-label">Recent Comments</label>
                                        <input type="text" class="form-control form-control-sm" id="ule_recentComments">
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Team Assignment Section -->
                        <div class="row g-3 mb-4">
                            <div class="col-12">
                                <h6 class="text-info border-bottom pb-2"><i class="fas fa-network-wired me-2"></i>Team Assignment</h6>
                            </div>
                            <!-- Source -->
                            <div class="col-md-4" style="position:relative;">
                                <label class="form-label">Source <span class="text-muted">(Search all)</span></label>
                                <div class="input-group mb-1">
                                    <input type="text" class="form-control" id="ule_sourceRefSearch" placeholder="Search MNR / Partner / Staff...">
                                    <button class="btn btn-outline-secondary" type="button" onclick="window.crmLeadEditor.clearSource()">
                                        <i class="fas fa-times"></i>
                                    </button>
                                </div>
                                <input type="hidden" id="ule_sourceRefType">
                                <input type="hidden" id="ule_sourceRefId">
                                <input type="hidden" id="ule_sourceRefName">
                                <div id="ule_sourceRefResults" class="list-group mt-1" style="max-height:150px;overflow-y:auto;display:none;position:absolute;z-index:1060;width:calc(100% - 24px);"></div>
                                <div id="ule_sourceRefSelected" class="mt-1"></div>
                            </div>
                            <!-- Senior (search/auto — DC-TEAM-ASSIGN-001) -->
                            <div class="col-md-2" id="ule_guruRow" style="display:none;">
                                <label class="form-label">Senior <span class="text-muted">(Search/Auto)</span></label>
                                <div class="input-group mb-1">
                                    <input type="text" class="form-control" id="ule_guruSearch" placeholder="Search or auto...">
                                    <button class="btn btn-outline-secondary" type="button" onclick="window.crmLeadEditor.clearLeadGuru()"><i class="fas fa-times"></i></button>
                                </div>
                                <input type="hidden" id="ule_guruId">
                                <input type="hidden" id="ule_guruType">
                                <input type="hidden" id="ule_guruName">
                                <div id="ule_guruSelected"></div>
                            </div>
                            <!-- Extended (search/auto — DC-TEAM-ASSIGN-001) -->
                            <div class="col-md-2" id="ule_zGuruRow" style="display:none;">
                                <label class="form-label">Extended <span class="text-muted">(Search/Auto)</span></label>
                                <div class="input-group mb-1">
                                    <input type="text" class="form-control" id="ule_zGuruSearch" placeholder="Search or auto...">
                                    <button class="btn btn-outline-secondary" type="button" onclick="window.crmLeadEditor.clearLeadZGuru()"><i class="fas fa-times"></i></button>
                                </div>
                                <input type="hidden" id="ule_zGuruId">
                                <input type="hidden" id="ule_zGuruType">
                                <input type="hidden" id="ule_zGuruName">
                                <div id="ule_zGuruSelected"></div>
                            </div>
                            <!-- Core (search/auto — DC-TEAM-ASSIGN-001) -->
                            <div class="col-md-2" id="ule_coreRow" style="display:none;">
                                <label class="form-label">Core <span class="text-muted">(Search/Auto)</span></label>
                                <div class="input-group mb-1">
                                    <input type="text" class="form-control" id="ule_coreSearch" placeholder="Search or auto...">
                                    <button class="btn btn-outline-secondary" type="button" onclick="window.crmLeadEditor.clearLeadCore()"><i class="fas fa-times"></i></button>
                                </div>
                                <input type="hidden" id="ule_corePartnerId">
                                <input type="hidden" id="ule_coreType">
                                <input type="hidden" id="ule_coreName">
                                <div id="ule_coreSelected"></div>
                            </div>
                            <!-- Field Support -->
                            <div class="col-md-4" style="position:relative;">
                                <label class="form-label">Field Support <span class="text-muted">(Search all)</span></label>
                                <div class="input-group mb-1">
                                    <input type="text" class="form-control" id="ule_fieldSupportRefSearch" placeholder="Search MNR / Partner / Staff...">
                                    <button class="btn btn-outline-secondary" type="button" onclick="window.crmLeadEditor.clearFieldSupport()">
                                        <i class="fas fa-times"></i>
                                    </button>
                                </div>
                                <input type="hidden" id="ule_fieldSupportRefType">
                                <input type="hidden" id="ule_fieldSupportRefId">
                                <input type="hidden" id="ule_fieldSupportRefName">
                                <div id="ule_fieldSupportRefResults" class="list-group mt-1" style="max-height:150px;overflow-y:auto;display:none;position:absolute;z-index:1060;width:calc(100% - 24px);"></div>
                                <div id="ule_fieldSupportRefSelected" class="mt-1"></div>
                            </div>
                            <!-- Technical (Staff only) -->
                            <div class="col-md-4">
                                <label class="form-label">Technical <span class="text-muted">(Staff search)</span></label>
                                <div class="input-group mb-1">
                                    <input type="text" class="form-control" id="ule_technicalSearch" placeholder="Search staff...">
                                    <button class="btn btn-outline-secondary" type="button" onclick="window.crmLeadEditor.clearTechnical()">
                                        <i class="fas fa-times"></i>
                                    </button>
                                </div>
                                <input type="hidden" id="ule_technicalId">
                                <div id="ule_technicalResults" class="list-group mt-1" style="max-height:150px;overflow-y:auto;display:none;position:absolute;z-index:1060;width:calc(100% - 24px);"></div>
                                <div id="ule_technicalSelected" class="mt-1"></div>
                            </div>
                            <!-- Hidden legacy fields preserved for backward compat -->
                            <input type="hidden" id="ule_mnrHandlerId">
                            <input type="hidden" id="ule_guruDisplay_legacy">
                            <input type="hidden" id="ule_adiGuruId">
                            <!-- DC-TEAM-ASSIGN-001: hidden override FKs -->
                            <input type="hidden" id="ule_teamSeniorPid">
                            <input type="hidden" id="ule_teamExtendedPid">
                        </div>
                        
                        <!-- Staff Assignment Section -->
                        <div class="row g-3 mb-4">
                            <div class="col-12">
                                <h6 class="text-success border-bottom pb-2"><i class="fas fa-headset me-2"></i>Staff Assignment</h6>
                            </div>
                            <div class="col-md-4">
                                <label class="form-label">Tele Caller</label>
                                <div class="input-group">
                                    <input type="text" class="form-control" id="ule_telecallerSearch" placeholder="Search staff...">
                                    <button class="btn btn-outline-secondary" type="button" onclick="window.crmLeadEditor.clearTelecaller()">
                                        <i class="fas fa-times"></i>
                                    </button>
                                </div>
                                <input type="hidden" id="ule_telecallerId">
                                <div id="ule_telecallerResults" class="list-group mt-1" style="max-height: 150px; overflow-y: auto; display: none; position: absolute; z-index: 1050; width: calc(100% - 24px);"></div>
                                <div id="ule_telecallerSelected" class="mt-2"></div>
                            </div>
                            <div class="col-md-4">
                                <label class="form-label">Field Staff</label>
                                <div class="input-group">
                                    <input type="text" class="form-control" id="ule_fieldStaffSearch" placeholder="Search staff...">
                                    <button class="btn btn-outline-secondary" type="button" onclick="window.crmLeadEditor.clearFieldStaff()">
                                        <i class="fas fa-times"></i>
                                    </button>
                                </div>
                                <input type="hidden" id="ule_fieldStaffId">
                                <div id="ule_fieldStaffResults" class="list-group mt-1" style="max-height: 150px; overflow-y: auto; display: none; position: absolute; z-index: 1050; width: calc(100% - 24px);"></div>
                                <div id="ule_fieldStaffSelected" class="mt-2"></div>
                            </div>
                            <div class="col-md-4">
                                <label class="form-label">Business Partner</label>
                                <div class="input-group">
                                    <input type="text" class="form-control" id="ule_partnerSearch" placeholder="Search partner...">
                                    <button class="btn btn-outline-secondary" type="button" onclick="window.crmLeadEditor.clearPartner()">
                                        <i class="fas fa-times"></i>
                                    </button>
                                </div>
                                <input type="hidden" id="ule_partnerId">
                                <div id="ule_partnerResults" class="list-group mt-1" style="max-height: 150px; overflow-y: auto; display: none; position: absolute; z-index: 1050; width: calc(100% - 24px);"></div>
                                <div id="ule_partnerSelected" class="mt-2"></div>
                            </div>
                        </div>
                        
                        <div id="ule_revenueSection" class="mb-4" style="display: none;">
                            <div class="row g-3">
                                <div class="col-12">
                                    <h6 class="text-warning border-bottom pb-2">
                                        <i class="fas fa-rupee-sign me-2"></i>Revenue & Payments 
                                        <span class="badge bg-warning text-dark ms-2">Won Deal</span>
                                    </h6>
                                </div>
                            </div>
                            <div class="row g-3 mt-2">
                                <div class="col-12">
                                    <div class="card border">
                                        <div class="card-header py-2 bg-light d-flex justify-content-between align-items-center">
                                            <span class="fw-medium"><i class="fas fa-handshake me-2"></i>Deals</span>
                                            <div class="d-flex align-items-center gap-2">
                                                <span class="badge bg-primary" title="Aggregate Total">Total: ₹<span id="ule_dealAggregateTotal">0</span></span>
                                                <span class="badge bg-success" title="Aggregate Received">Received: ₹<span id="ule_dealAggregateReceived">0</span></span>
                                                <span class="badge bg-secondary" title="Aggregate Balance">Balance: ₹<span id="ule_dealAggregateBalance">0</span></span>
                                                <button class="btn btn-primary btn-sm" type="button" onclick="window.crmLeadEditor.toggleAddDealForm()">
                                                    <i class="fas fa-plus me-1"></i>Add Deal
                                                </button>
                                            </div>
                                        </div>
                                        <div id="ule_addDealFormSection" style="display: none;" class="p-3 border-bottom bg-light">
                                            <input type="hidden" id="ule_editDealId" value="">
                                            <div class="row g-2 align-items-end">
                                                <div class="col-md-3">
                                                    <label class="form-label small mb-1">Company <span class="text-danger">*</span></label>
                                                    <select class="form-select form-select-sm" id="ule_dealCompanySelect" onchange="window.crmLeadEditor.onDealCompanyChange()">
                                                        <option value="">Select Company</option>
                                                    </select>
                                                </div>
                                                <div class="col-md-3">
                                                    <label class="form-label small mb-1">Category <span class="text-danger">*</span></label>
                                                    <select class="form-select form-select-sm" id="ule_dealCategorySelect">
                                                        <option value="">Select Category</option>
                                                    </select>
                                                </div>
                                                <div class="col-md-3">
                                                    <label class="form-label small mb-1">Deal Date</label>
                                                    <input type="date" class="form-control form-control-sm" id="ule_dealDateInput">
                                                </div>
                                                <div class="col-md-3">
                                                    <label class="form-label small mb-1">Deal Value (₹) <span class="text-danger">*</span></label>
                                                    <input type="number" class="form-control form-control-sm" id="ule_dealValueInput" placeholder="Enter value" min="1" step="0.01">
                                                </div>
                                            </div>
                                            <div class="row g-2 mt-1 align-items-end">
                                                <div class="col-md-9">
                                                    <label class="form-label small mb-1">Notes</label>
                                                    <input type="text" class="form-control form-control-sm" id="ule_dealNotesInput" placeholder="Optional notes">
                                                </div>
                                                <div class="col-md-3 d-flex gap-1">
                                                    <button class="btn btn-success btn-sm flex-grow-1" onclick="window.crmLeadEditor.saveDeal()"><i class="fas fa-check me-1"></i>Save</button>
                                                    <button class="btn btn-outline-secondary btn-sm" onclick="window.crmLeadEditor.toggleAddDealForm()"><i class="fas fa-times"></i></button>
                                                </div>
                                            </div>
                                        </div>
                                        <div class="card-body p-0">
                                            <div class="table-responsive" style="max-height: 180px; overflow-y: auto;">
                                                <table class="table table-sm table-hover mb-0" style="font-size: 11px;">
                                                    <thead class="table-light sticky-top">
                                                        <tr>
                                                            <th>#</th>
                                                            <th>Date</th>
                                                            <th>Company</th>
                                                            <th>Category</th>
                                                            <th>Total (₹)</th>
                                                            <th>Received (₹)</th>
                                                            <th>Balance (₹)</th>
                                                            <th>Status</th>
                                                            <th>Actions</th>
                                                        </tr>
                                                    </thead>
                                                    <tbody id="ule_dealsBody">
                                                        <tr><td colspan="9" class="text-center text-muted py-2">No deals yet. Click "Add Deal" to create one.</td></tr>
                                                    </tbody>
                                                </table>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <input type="hidden" id="ule_dealValueTotal" value="0">
                            <input type="hidden" id="ule_dealValueReceived" value="0">
                            <input type="hidden" id="ule_dealValueBalance" value="0">
                            <div class="row g-3 mt-3" id="ule_transactionsSection">
                                <div class="col-12">
                                    <div class="card border">
                                        <div class="card-header py-2 bg-light d-flex justify-content-between align-items-center">
                                            <span class="fw-medium"><i class="fas fa-receipt me-2"></i>Payment Transactions</span>
                                            <div class="d-flex align-items-center gap-2">
                                                <span class="badge bg-success" title="Validated Amount">
                                                    <i class="fas fa-check-circle me-1"></i>Validated: ₹<span id="ule_financeApproved">0</span>
                                                </span>
                                                <span class="badge bg-warning text-dark" title="Pending Validation">
                                                    <i class="fas fa-clock me-1"></i>Pending: ₹<span id="ule_financePending">0</span>
                                                </span>
                                                <button class="btn btn-primary btn-sm" type="button" onclick="window.crmLeadEditor.openAddTransactionModal()">
                                                    <i class="fas fa-plus me-1"></i>Add
                                                </button>
                                            </div>
                                        </div>
                                        <div class="card-body p-0">
                                            <div class="table-responsive" style="max-height: 150px; overflow-y: auto;">
                                                <table class="table table-sm table-hover mb-0" style="font-size: 11px;">
                                                    <thead class="table-light sticky-top">
                                                        <tr>
                                                            <th>Date</th>
                                                            <th>Amount</th>
                                                            <th>Type</th>
                                                            <th>Mode</th>
                                                            <th>Deal</th>
                                                            <th>Status</th>
                                                            <th>Actions</th>
                                                        </tr>
                                                    </thead>
                                                    <tbody id="ule_transactionsBody">
                                                        <tr><td colspan="7" class="text-center text-muted py-2">No transactions</td></tr>
                                                    </tbody>
                                                </table>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Call History Section (DC Protocol - Feb 2026) -->
                        <div class="mb-4">
                            <div class="card border-info">
                                <div class="card-header bg-info text-white py-2 d-flex justify-content-between align-items-center" style="cursor:pointer;" onclick="window.crmLeadEditor.toggleCallHistory()">
                                    <h6 class="mb-0"><i class="fas fa-phone-alt me-2"></i>Call History</h6>
                                    <span id="ule_callHistoryBadge" class="badge bg-light text-dark">Loading...</span>
                                </div>
                                <div id="ule_callHistorySection" class="card-body" style="display: none;">
                                    <div id="ule_callHistorySummary" class="row g-2 mb-3"></div>
                                    
                                    <!-- Per-Staff Breakdown (shown when 2+ handlers called) -->
                                    <div id="ule_callStaffBreakdown" class="mb-3" style="display:none;">
                                        <h6 class="text-muted mb-2" style="font-size:12px;"><i class="fas fa-users me-1"></i>Per-Handler Breakdown</h6>
                                        <div id="ule_callStaffCards" class="d-flex flex-wrap gap-2 mb-2"></div>
                                    </div>
                                    
                                    <!-- Filter Bar -->
                                    <div class="d-flex gap-2 mb-2 flex-wrap align-items-center" id="ule_callFilterBar" style="display:none !important;">
                                        <select id="ule_callStaffFilter" class="form-select form-select-sm" style="max-width:180px;" onchange="window.crmLeadEditor.filterCallHistory()">
                                            <option value="">All Handlers</option>
                                        </select>
                                        <select id="ule_callTypeFilter" class="form-select form-select-sm" style="max-width:140px;" onchange="window.crmLeadEditor.filterCallHistory()">
                                            <option value="">All Types</option>
                                            <option value="INCOMING">Incoming</option>
                                            <option value="OUTGOING">Outgoing</option>
                                            <option value="MISSED">Missed</option>
                                        </select>
                                        <button class="btn btn-sm btn-outline-secondary" onclick="window.crmLeadEditor.resetCallFilters()" title="Reset Filters">
                                            <i class="fas fa-undo"></i>
                                        </button>
                                    </div>
                                    
                                    <div class="table-responsive" style="max-height: 300px; overflow-y: auto;">
                                        <table class="table table-sm table-hover mb-0">
                                            <thead class="table-light sticky-top">
                                                <tr>
                                                    <th>Date & Time</th>
                                                    <th>Type</th>
                                                    <th>Duration</th>
                                                    <th>Staff</th>
                                                    <th>Recording</th>
                                                    <th>Phone</th>
                                                </tr>
                                            </thead>
                                            <tbody id="ule_callHistoryBody">
                                                <tr><td colspan="6" class="text-center text-muted py-3">Click header to load call history</td></tr>
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Task Creation Section (shown for won deals) -->
                        <div id="ule_taskSection" class="mb-4" style="display: none;">
                            <div class="card border-success">
                                <div class="card-header bg-success text-white py-2">
                                    <h6 class="mb-0"><i class="fas fa-tasks me-2"></i>Create Task (Optional)</h6>
                                </div>
                                <div class="card-body">
                                    <div class="row g-3">
                                        <div class="col-md-6">
                                            <label class="form-label">Task Assignee</label>
                                            <div class="input-group">
                                                <input type="text" class="form-control" id="ule_taskAssigneeSearch" placeholder="Search staff...">
                                                <button class="btn btn-outline-secondary" type="button" onclick="window.crmLeadEditor.clearTaskAssignee()">
                                                    <i class="fas fa-times"></i>
                                                </button>
                                            </div>
                                            <input type="hidden" id="ule_taskAssigneeId">
                                            <div id="ule_taskAssigneeResults" class="list-group mt-1" style="max-height: 150px; overflow-y: auto; display: none;"></div>
                                            <div id="ule_taskAssigneeSelected" class="mt-2"></div>
                                        </div>
                                        <div class="col-md-6">
                                            <label class="form-label">Task Title</label>
                                            <input type="text" class="form-control" id="ule_taskTitle" placeholder="Enter task title">
                                        </div>
                                        <div class="col-12">
                                            <label class="form-label">Task Details</label>
                                            <textarea class="form-control" id="ule_taskDetails" rows="2" placeholder="Task instructions..."></textarea>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="btn btn-success" onclick="window.crmLeadEditor.saveLead()">
                            <i class="fas fa-save me-2"></i>Save Changes
                        </button>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Add/Edit Transaction Modal -->
        <div class="modal fade" id="ule_addTransactionModal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header bg-primary text-white">
                        <h5 class="modal-title" id="ule_txnModalTitle"><i class="fas fa-receipt me-2"></i>Add Payment Transaction</h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <input type="hidden" id="ule_editTxnId" value="">
                        <div class="row g-3">
                            <div class="col-12">
                                <label class="form-label">Deal <span class="text-danger">*</span></label>
                                <select class="form-select" id="ule_txnDealSelect">
                                    <option value="">Select Deal</option>
                                </select>
                            </div>
                            <div class="col-md-6">
                                <label class="form-label">Transaction Date <span class="text-danger">*</span></label>
                                <input type="datetime-local" class="form-control" id="ule_txnDate" required>
                            </div>
                            <div class="col-md-6">
                                <label class="form-label">Amount <span class="text-danger">*</span></label>
                                <div class="input-group">
                                    <span class="input-group-text">₹</span>
                                    <input type="number" class="form-control" id="ule_txnAmount" placeholder="Amount" min="1" step="0.01" required>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <label class="form-label">Transaction Type</label>
                                <select class="form-select" id="ule_txnType">
                                    <option value="advance">Advance Payment</option>
                                    <option value="partial" selected>Partial Payment</option>
                                    <option value="final">Final Payment</option>
                                    <option value="refund">Refund</option>
                                </select>
                            </div>
                            <div class="col-md-6">
                                <label class="form-label">Payment Mode</label>
                                <select class="form-select" id="ule_txnMode">
                                    <option value="cash">Cash</option>
                                    <option value="upi" selected>UPI</option>
                                    <option value="neft">NEFT</option>
                                    <option value="rtgs">RTGS</option>
                                    <option value="cheque">Cheque</option>
                                    <option value="card">Card</option>
                                </select>
                            </div>
                            <div class="col-12">
                                <label class="form-label">Reference / Notes</label>
                                <input type="text" class="form-control" id="ule_txnReference" placeholder="Transaction reference or notes">
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="btn btn-primary" onclick="window.crmLeadEditor.saveTransaction()">
                            <i class="fas fa-save me-1"></i>Save Transaction
                        </button>
                    </div>
                </div>
            </div>
        </div>`;
        
        const wrapper = document.createElement('div');
        wrapper.innerHTML = modalHtml;
        container.appendChild(wrapper);
    }
    
    bindEvents() {
        const statusSelect = document.getElementById('ule_status');
        if (statusSelect) {
            statusSelect.addEventListener('change', () => this.handleStatusChange());
        }
        
        this.bindNetworkSearchField('ule_sourceRefSearch', 'ule_sourceRefType', 'ule_sourceRefResults');
        this.bindNetworkSearchField('ule_fieldSupportRefSearch', 'ule_fieldSupportRefType', 'ule_fieldSupportRefResults');
        // DC-TEAM-ASSIGN-001: wire up Senior/Extended/Core search inputs
        ['guru','zGuru','core'].forEach(f => {
            const inp = document.getElementById(`ule_${f}Search`);
            if (!inp) return;
            inp.addEventListener('input', () => {
                clearTimeout(this.searchTimeouts[`ule_${f}Search`]);
                const q = inp.value.trim();
                if (q.length < 2) return;
                this.searchTimeouts[`ule_${f}Search`] = setTimeout(async () => {
                    try {
                        const r = await fetch(`${this.apiBasePath}/network-search?q=${encodeURIComponent(q)}&limit=10`, this.authOptions);
                        const data = await r.json();
                        if (!data.success || !data.results?.length) return;
                        const _fldKey = f==='guru'?'guru':f==='zGuru'?'z_guru':'core';
                        const _dd = document.createElement('div');
                        _dd.className='list-group mt-1 position-absolute';
                        _dd.style='z-index:1060;max-height:200px;overflow-y:auto;width:100%;';
                        _dd.id=`ule_${f}SearchDropdown`;
                        document.getElementById(`ule_${f}SearchDropdown`)?.remove();
                        data.results.forEach(res => {
                            const btn=document.createElement('button');
                            btn.type='button';
                            btn.className='list-group-item list-group-item-action py-2';
                            btn.innerHTML=`<span class="badge bg-secondary me-1" style="font-size:9px">${(res.type||'').toUpperCase()}</span><strong>${res.code||res.id}</strong> <span class="text-muted">${res.name||res.display||''}</span>`;
                            btn.onclick=()=>{
                                _dd.remove();
                                const _isUser=['mnr','vgk'].includes(res.type);
                                const _isPid=_fldKey==='core';
                                if (_isPid){
                                    document.getElementById('ule_corePartnerId').value=_isUser?'':(res.id||'');
                                    document.getElementById('ule_coreType').value=res.type||'';
                                    document.getElementById('ule_coreName').value=res.name||res.display||'';
                                    document.getElementById('ule_coreSearch').value='';
                                    this._renderTeamBadge('core',res.type,_isUser?'':(res.id||''),res.name||res.display||'');
                                } else {
                                    document.getElementById(`ule_${f}Id`).value=_isUser?(res.id||''):'';
                                    document.getElementById(`ule_${f}Type`).value=res.type||'';
                                    document.getElementById(`ule_${f}Name`).value=res.name||res.display||'';
                                    document.getElementById(`ule_${f}Search`).value='';
                                    if (_fldKey==='guru') document.getElementById('ule_teamSeniorPid').value=_isUser?'':(res.id||'');
                                    if (_fldKey==='z_guru') document.getElementById('ule_teamExtendedPid').value=_isUser?'':(res.id||'');
                                    this._renderTeamBadge(_fldKey,res.type,res.id||'',res.name||res.display||'');
                                }
                            };
                            _dd.appendChild(btn);
                        });
                        inp.parentNode.style.position='relative';
                        inp.parentNode.appendChild(_dd);
                        setTimeout(()=>{document.addEventListener('click',function c(e){if(!_dd.contains(e.target)&&e.target!==inp){_dd.remove();document.removeEventListener('click',c);}},{once:false});},100);
                    } catch(e){}
                }, 300);
            });
        });
        this.bindSearchField('ule_technicalSearch', 'staff', 'ule_technicalResults');
        this.bindSearchField('ule_telecallerSearch', 'staff', 'ule_telecallerResults');
        this.bindSearchField('ule_fieldStaffSearch', 'staff', 'ule_fieldStaffResults');
        this.bindSearchField('ule_partnerSearch', 'partner', 'ule_partnerResults');
        this.bindSearchField('ule_taskAssigneeSearch', 'staff', 'ule_taskAssigneeResults');

        document.addEventListener('click', (e) => {
            const searchContainers = ['ule_sourceRefResults', 'ule_fieldSupportRefResults', 'ule_technicalResults',
                                      'ule_telecallerResults', 'ule_fieldStaffResults', 'ule_partnerResults', 'ule_taskAssigneeResults'];
            searchContainers.forEach(id => {
                const container = document.getElementById(id);
                if (container && !container.contains(e.target) && !e.target.closest('.input-group')) {
                    container.style.display = 'none';
                }
            });
        });
    }
    
    bindSearchField(inputId, searchType, resultsId) {
        const input = document.getElementById(inputId);
        if (!input) return;
        
        input.addEventListener('input', () => {
            clearTimeout(this.searchTimeouts[inputId]);
            const query = input.value.trim();
            if (query.length < 2) {
                document.getElementById(resultsId).style.display = 'none';
                return;
            }
            this.searchTimeouts[inputId] = setTimeout(() => {
                this.performSearch(searchType, query, resultsId, inputId);
            }, 300);
        });
    }
    
    bindNetworkSearchField(inputId, typeSelectId, resultsId) {
        const input = document.getElementById(inputId);
        if (!input) return;
        input.addEventListener('input', () => {
            clearTimeout(this.searchTimeouts[inputId]);
            const query = input.value.trim();
            if (query.length < 2) {
                const rd = document.getElementById(resultsId);
                if (rd) rd.style.display = 'none';
                return;
            }
            this.searchTimeouts[inputId] = setTimeout(() => {
                this.performNetworkSearch('', query, resultsId, inputId);
            }, 300);
        });
    }

    async performNetworkSearch(type, query, resultsId, inputId) {
        try {
            const typeParam = type ? `&type=${encodeURIComponent(type)}` : '';
            const url = `/api/v1/crm/network-search?q=${encodeURIComponent(query)}${typeParam}&limit=20`;
            const response = await fetch(url, this.authOptions);
            const data = await response.json();
            const resultsDiv = document.getElementById(resultsId);
            if (!resultsDiv) return;
            const items = (data.success && (data.data || data.results)) ? (data.results || data.data) : [];
            if (items.length > 0) {
                const typeColors = { mnr:'bg-info', vgk:'bg-primary', partner:'bg-warning text-dark', vendor:'bg-secondary', staff:'bg-success' };
                resultsDiv.innerHTML = items.map(item => {
                    const itemType = item.type || type || '';
                    const tc = typeColors[itemType] || 'bg-secondary';
                    const safeCode = String(item.code || item.id || '').replace(/'/g, "\\'");
                    const safeName = String(item.name || item.display || '').replace(/'/g, "\\'");
                    const extra = item.phone || item.designation || '';
                    const jsonItem = JSON.stringify(item).replace(/'/g, "\\'");
                    return `<button type="button" class="list-group-item list-group-item-action py-2"
                        onclick='window.crmLeadEditor.selectNetworkResultFull(${JSON.stringify(inputId)}, ${JSON.stringify(item)})'>
                        <div class="d-flex justify-content-between align-items-center">
                            <div><span class="badge ${tc} me-1" style="font-size:9px">${itemType.toUpperCase()}</span><strong>${safeCode}</strong> <span class="text-muted ms-1">${safeName}</span></div>
                            <small class="text-muted">${extra}</small>
                        </div></button>`;
                }).join('');
                resultsDiv.style.display = 'block';
            } else {
                resultsDiv.innerHTML = '<div class="list-group-item text-muted py-2">No results found</div>';
                resultsDiv.style.display = 'block';
            }
        } catch (err) {
            console.error('[DC-NET-SEARCH] Error:', err);
        }
    }

    selectNetworkResultFull(inputId, item) {
        const id = item.id || '';
        const name = item.name || item.display || '';
        const code = item.code || item.id || '';
        const type = item.type || '';
        this.selectNetworkResult(inputId, id, name, code, type, item);
    }

    selectNetworkResult(inputId, id, name, code, type, fullItem) {
        const isSource = inputId === 'ule_sourceRefSearch';
        const isFieldSupport = inputId === 'ule_fieldSupportRefSearch';
        const typeColors = { mnr:'bg-info', vgk:'bg-primary', partner:'bg-warning text-dark', vendor:'bg-secondary', staff:'bg-success' };
        const tc = typeColors[type] || 'bg-secondary';
        const displayText = `${code || id} — ${name}`;

        if (isSource) {
            document.getElementById('ule_sourceRefType').value = type;
            document.getElementById('ule_sourceRefId').value = id;
            document.getElementById('ule_sourceRefName').value = name;
            document.getElementById('ule_sourceRefSearch').value = '';
            const res = document.getElementById('ule_sourceRefResults');
            if (res) res.style.display = 'none';
            document.getElementById('ule_sourceRefSelected').innerHTML =
                `<span class="badge ${tc} p-2"><i class="fas fa-user me-1"></i>${displayText}</span>`;
            // DC Protocol Fix (Apr 2026): For non-user-type sources (partner/vendor/staff),
            // clear the legacy mnr_handler_id FK field — it must not receive a non-user ID.
            const _isNonUserTypeSrc = ['partner', 'vgk', 'vgk_partner', 'vendor', 'staff', 'external'].includes(type);
            if (_isNonUserTypeSrc) {
                const _mnrHid = document.getElementById('ule_mnrHandlerId');
                if (_mnrHid) _mnrHid.value = '';
                const _adiHid = document.getElementById('ule_adiGuruId');
                if (_adiHid) _adiHid.value = '';
            }
            // Guru + Z Guru rows: show only for mnr/vgk; populate from network-search result or fetch upline
            const guruRow = document.getElementById('ule_guruRow');
            const zGuruRow = document.getElementById('ule_zGuruRow');
            if (type === 'mnr' || type === 'vgk') {
                if (guruRow) guruRow.style.display = '';
                if (zGuruRow) zGuruRow.style.display = '';
                if (fullItem && fullItem.sponsor_id) {
                    document.getElementById('ule_guruId').value = fullItem.sponsor_id;
                    document.getElementById('ule_guruType').value = type;
                    document.getElementById('ule_guruName').value = fullItem.sponsor_name || '';
                    document.getElementById('ule_guruSearch').value = '';
                    this._renderTeamBadge('guru', type, String(fullItem.sponsor_id), fullItem.sponsor_name || '');
                } else {
                    this.fetchUpline(id);
                }
                if (fullItem && fullItem.z_sponsor_id) {
                    document.getElementById('ule_zGuruId').value = fullItem.z_sponsor_id;
                    document.getElementById('ule_zGuruType').value = type;
                    document.getElementById('ule_zGuruName').value = fullItem.z_sponsor_name || '';
                    document.getElementById('ule_zGuruSearch').value = '';
                    this._renderTeamBadge('z_guru', type, String(fullItem.z_sponsor_id), fullItem.z_sponsor_name || '');
                } else {
                    document.getElementById('ule_zGuruId').value = '';
                    document.getElementById('ule_zGuruType').value = '';
                    document.getElementById('ule_zGuruName').value = '';
                    document.getElementById('ule_zGuruSelected').innerHTML = '';
                }
            } else if (type === 'partner' || type === 'vgk_partner') {
                // DC Protocol Fix (Apr 2026): VGK/partner sources — show parent_partner upline chain
                const _guruName = (fullItem && fullItem.parent_partner_name) || '';
                const _guruCode = (fullItem && fullItem.parent_partner_code) || '';
                const _guruId = (fullItem && fullItem.parent_partner_id) || '';
                const _zGuruName = (fullItem && fullItem.z_parent_partner_name) || '';
                const _zGuruCode = (fullItem && fullItem.z_parent_partner_code) || '';
                const _zGuruId = (fullItem && fullItem.z_parent_partner_id) || '';
                // DC-TEAM-ASSIGN-001: L4 Core from adi_parent_partner chain
                const _aName = (fullItem && fullItem.adi_parent_partner_name) || '';
                const _aCode = (fullItem && fullItem.adi_parent_partner_code) || '';
                const _aId   = (fullItem && fullItem.adi_parent_partner_id) || '';
                if (_guruId) {
                    if (guruRow) guruRow.style.display = '';
                    document.getElementById('ule_guruId').value = '';
                    document.getElementById('ule_guruType').value = 'partner';
                    document.getElementById('ule_guruName').value = _guruName;
                    document.getElementById('ule_guruSearch').value = '';
                    document.getElementById('ule_teamSeniorPid').value = _guruId;
                    this._renderTeamBadge('guru', 'partner', String(_guruId), `${_guruName}${_guruCode?' ('+_guruCode+')':''}`);
                } else {
                    if (guruRow) guruRow.style.display = 'none';
                    document.getElementById('ule_guruId').value = '';
                    document.getElementById('ule_guruType').value = '';
                    document.getElementById('ule_guruName').value = '';
                    document.getElementById('ule_guruSelected').innerHTML = '';
                    document.getElementById('ule_teamSeniorPid').value = '';
                }
                if (_zGuruId) {
                    if (zGuruRow) zGuruRow.style.display = '';
                    document.getElementById('ule_zGuruId').value = '';
                    document.getElementById('ule_zGuruType').value = 'partner';
                    document.getElementById('ule_zGuruName').value = _zGuruName;
                    document.getElementById('ule_zGuruSearch').value = '';
                    document.getElementById('ule_teamExtendedPid').value = _zGuruId;
                    this._renderTeamBadge('z_guru', 'partner', String(_zGuruId), `${_zGuruName}${_zGuruCode?' ('+_zGuruCode+')':''}`);
                } else {
                    if (zGuruRow) zGuruRow.style.display = 'none';
                    document.getElementById('ule_zGuruId').value = '';
                    document.getElementById('ule_zGuruType').value = '';
                    document.getElementById('ule_zGuruName').value = '';
                    document.getElementById('ule_zGuruSelected').innerHTML = '';
                    document.getElementById('ule_teamExtendedPid').value = '';
                }
                const coreRow = document.getElementById('ule_coreRow');
                if (_aId) {
                    if (coreRow) coreRow.style.display = '';
                    document.getElementById('ule_corePartnerId').value = _aId;
                    document.getElementById('ule_coreType').value = 'partner';
                    document.getElementById('ule_coreName').value = _aName;
                    document.getElementById('ule_coreSearch').value = '';
                    this._renderTeamBadge('core', 'partner', String(_aId), `${_aName}${_aCode?' ('+_aCode+')':''}`);
                } else {
                    if (coreRow) coreRow.style.display = 'none';
                    document.getElementById('ule_corePartnerId').value = '';
                    document.getElementById('ule_coreType').value = '';
                    document.getElementById('ule_coreName').value = '';
                    document.getElementById('ule_coreSelected').innerHTML = '';
                }
            } else {
                if (guruRow) guruRow.style.display = 'none';
                if (zGuruRow) zGuruRow.style.display = 'none';
                const coreRow2 = document.getElementById('ule_coreRow');
                if (coreRow2) coreRow2.style.display = 'none';
                document.getElementById('ule_guruId').value = '';
                document.getElementById('ule_guruType').value = '';
                document.getElementById('ule_guruName').value = '';
                document.getElementById('ule_guruSelected').innerHTML = '';
                document.getElementById('ule_zGuruId').value = '';
                document.getElementById('ule_zGuruType').value = '';
                document.getElementById('ule_zGuruName').value = '';
                document.getElementById('ule_zGuruSelected').innerHTML = '';
                document.getElementById('ule_corePartnerId').value = '';
                document.getElementById('ule_coreType').value = '';
                document.getElementById('ule_coreName').value = '';
                document.getElementById('ule_coreSelected').innerHTML = '';
                document.getElementById('ule_teamSeniorPid').value = '';
                document.getElementById('ule_teamExtendedPid').value = '';
            }
        } else if (isFieldSupport) {
            document.getElementById('ule_fieldSupportRefType').value = type;
            document.getElementById('ule_fieldSupportRefId').value = id;
            document.getElementById('ule_fieldSupportRefName').value = name;
            document.getElementById('ule_fieldSupportRefSearch').value = '';
            const res = document.getElementById('ule_fieldSupportRefResults');
            if (res) res.style.display = 'none';
            document.getElementById('ule_fieldSupportRefSelected').innerHTML =
                `<span class="badge ${tc} p-2"><i class="fas fa-user me-1"></i>${displayText}</span>`;
        }
    }

    onSourceTypeChange() {}
    onFieldSupportTypeChange() {}

    _renderTeamBadge(field, type, id, name) {
        const _sfx = {guru:'guru',z_guru:'zGuru',core:'core'}[field] || field;
        const el = document.getElementById(`ule_${_sfx}Selected`);
        if (!el) return;
        if (!id && !name) { el.innerHTML = ''; return; }
        const _colors = {mnr:'bg-info',vgk:'bg-primary',partner:'bg-warning text-dark'};
        const _tc = _colors[type] || 'bg-secondary';
        const _clear = field==='guru'?'clearLeadGuru':field==='z_guru'?'clearLeadZGuru':'clearLeadCore';
        el.innerHTML = `<div style="display:flex;align-items:center;gap:4px;flex-wrap:wrap;margin-top:3px"><span class="badge ${_tc} p-1" style="font-size:10px">${(type||'').toUpperCase()}</span><span style="font-size:12px;font-weight:500">${name||id}</span><span style="font-size:10px;color:#6b7280">${id}</span><button type="button" class="btn btn-link btn-sm p-0 ms-1 text-danger" style="font-size:10px" onclick="window.crmLeadEditor.${_clear}()">✕</button></div>`;
    }
    clearLeadGuru() {
        document.getElementById('ule_guruId').value = '';
        document.getElementById('ule_guruType').value = '';
        document.getElementById('ule_guruName').value = '';
        const s = document.getElementById('ule_guruSearch'); if (s) s.value = '';
        document.getElementById('ule_guruSelected').innerHTML = '';
        document.getElementById('ule_teamSeniorPid').value = '';
    }
    clearLeadZGuru() {
        document.getElementById('ule_zGuruId').value = '';
        document.getElementById('ule_zGuruType').value = '';
        document.getElementById('ule_zGuruName').value = '';
        const s = document.getElementById('ule_zGuruSearch'); if (s) s.value = '';
        document.getElementById('ule_zGuruSelected').innerHTML = '';
        document.getElementById('ule_teamExtendedPid').value = '';
    }
    clearLeadCore() {
        document.getElementById('ule_corePartnerId').value = '';
        document.getElementById('ule_coreType').value = '';
        document.getElementById('ule_coreName').value = '';
        const s = document.getElementById('ule_coreSearch'); if (s) s.value = '';
        document.getElementById('ule_coreSelected').innerHTML = '';
    }
    clearSource() {
        document.getElementById('ule_sourceRefType').value = '';
        document.getElementById('ule_sourceRefId').value = '';
        document.getElementById('ule_sourceRefName').value = '';
        document.getElementById('ule_sourceRefSearch').value = '';
        document.getElementById('ule_sourceRefSelected').innerHTML = '';
        const res = document.getElementById('ule_sourceRefResults');
        if (res) res.style.display = 'none';
        const guruRow = document.getElementById('ule_guruRow');
        if (guruRow) guruRow.style.display = 'none';
        this.clearLeadGuru();
        const zGuruRow = document.getElementById('ule_zGuruRow');
        if (zGuruRow) zGuruRow.style.display = 'none';
        this.clearLeadZGuru();
        // DC-TEAM-ASSIGN-001: clear Core row
        const coreRow = document.getElementById('ule_coreRow');
        if (coreRow) coreRow.style.display = 'none';
        this.clearLeadCore();
    }

    clearFieldSupport() {
        document.getElementById('ule_fieldSupportRefType').value = '';
        document.getElementById('ule_fieldSupportRefId').value = '';
        document.getElementById('ule_fieldSupportRefName').value = '';
        document.getElementById('ule_fieldSupportRefSearch').value = '';
        document.getElementById('ule_fieldSupportRefSelected').innerHTML = '';
        const res = document.getElementById('ule_fieldSupportRefResults');
        if (res) res.style.display = 'none';
    }

    clearTechnical() {
        document.getElementById('ule_technicalId').value = '';
        document.getElementById('ule_technicalSearch').value = '';
        document.getElementById('ule_technicalSelected').innerHTML = '';
        const res = document.getElementById('ule_technicalResults');
        if (res) res.style.display = 'none';
    }

    async performSearch(type, query, resultsId, inputId) {
        try {
            let url;
            switch(type) {
                case 'mnr':
                    url = `${this.apiBasePath}/unified-my-leads/search-mnr?q=${encodeURIComponent(query)}`;
                    break;
                case 'staff':
                    url = `/api/v1/staff/employees/search?q=${encodeURIComponent(query)}&active=true`;
                    break;
                case 'partner':
                    url = `${this.apiBasePath}/unified-my-leads/search-partner?q=${encodeURIComponent(query)}`;
                    break;
                default:
                    return;
            }
            
            const response = await fetch(url, this.authOptions);
            const data = await response.json();
            
            const resultsDiv = document.getElementById(resultsId);
            let items = [];
            
            if (data.success && data.data) {
                items = Array.isArray(data.data) ? data.data : (data.data.employees || data.data.items || []);
            } else if (Array.isArray(data)) {
                items = data;
            }
            
            if (items.length > 0) {
                resultsDiv.innerHTML = items.map(item => {
                    const id = item.id || item.emp_code || item.code;
                    const name = item.name || item.full_name || '';
                    const code = item.code || item.emp_code || item.id || '';
                    const extra = item.phone || item.designation || '';
                    
                    return `
                        <button type="button" class="list-group-item list-group-item-action py-2" 
                                onclick="window.crmLeadEditor.selectSearchResult('${inputId}', '${id}', '${name.replace(/'/g, "\\'")}', '${code}')">
                            <div class="d-flex justify-content-between align-items-center">
                                <div><strong>${code}</strong> <span class="text-muted ms-1">${name}</span></div>
                                <small class="text-muted">${extra}</small>
                            </div>
                        </button>`;
                }).join('');
                resultsDiv.style.display = 'block';
            } else {
                resultsDiv.innerHTML = '<div class="list-group-item text-muted py-2">No results found</div>';
                resultsDiv.style.display = 'block';
            }
        } catch (error) {
            console.error('[DC-CRM-EDITOR] Search error:', error);
        }
    }
    
    selectSearchResult(inputId, id, name, code) {
        const fieldMapping = {
            'ule_technicalSearch': { hiddenId: 'ule_technicalId', selectedId: 'ule_technicalSelected', resultsId: 'ule_technicalResults' },
            'ule_telecallerSearch': { hiddenId: 'ule_telecallerId', selectedId: 'ule_telecallerSelected', resultsId: 'ule_telecallerResults' },
            'ule_fieldStaffSearch': { hiddenId: 'ule_fieldStaffId', selectedId: 'ule_fieldStaffSelected', resultsId: 'ule_fieldStaffResults' },
            'ule_partnerSearch': { hiddenId: 'ule_partnerId', selectedId: 'ule_partnerSelected', resultsId: 'ule_partnerResults' },
            'ule_taskAssigneeSearch': { hiddenId: 'ule_taskAssigneeId', selectedId: 'ule_taskAssigneeSelected', resultsId: 'ule_taskAssigneeResults' }
        };

        const mapping = fieldMapping[inputId];
        if (!mapping) return;

        document.getElementById(mapping.hiddenId).value = id;
        document.getElementById(inputId).value = '';
        document.getElementById(mapping.resultsId).style.display = 'none';

        const badgeClass = inputId.includes('partner') ? 'bg-warning text-dark' : 'bg-success';
        document.getElementById(mapping.selectedId).innerHTML = `
            <span class="badge ${badgeClass} p-2">
                <i class="fas fa-user me-1"></i>${code || id} - ${name}
            </span>`;
    }
    
    async fetchUpline(mnrId) {
        try {
            const response = await fetch(`${this.apiBasePath}/unified-my-leads/upline/${mnrId}`, this.authOptions);
            const data = await response.json();
            if (data.success && data.data) {
                if (data.data.guru) {
                    document.getElementById('ule_guruId').value = data.data.guru.id;
                    document.getElementById('ule_guruType').value = 'mnr';
                    document.getElementById('ule_guruName').value = data.data.guru.name || '';
                    document.getElementById('ule_guruSearch').value = '';
                    this._renderTeamBadge('guru', 'mnr', String(data.data.guru.id), data.data.guru.name || '');
                }
                if (data.data.adi_guru) {
                    document.getElementById('ule_zGuruId').value = data.data.adi_guru.id;
                    document.getElementById('ule_zGuruType').value = 'mnr';
                    document.getElementById('ule_zGuruName').value = data.data.adi_guru.name || '';
                    document.getElementById('ule_zGuruSearch').value = '';
                    this._renderTeamBadge('z_guru', 'mnr', String(data.data.adi_guru.id), data.data.adi_guru.name || '');
                    const zr = document.getElementById('ule_zGuruRow'); if (zr) zr.style.display = '';
                }
                // DC-TEAM-ASSIGN-001: L4 Core from upline response
                const _cr = document.getElementById('ule_coreRow');
                if (data.data.core) {
                    document.getElementById('ule_corePartnerId').value = '';
                    document.getElementById('ule_coreType').value = 'mnr';
                    document.getElementById('ule_coreName').value = data.data.core.name || '';
                    document.getElementById('ule_coreSearch').value = '';
                    this._renderTeamBadge('core', 'mnr', String(data.data.core.id), data.data.core.name || '');
                    if (_cr) _cr.style.display = '';
                } else {
                    if (_cr) _cr.style.display = 'none';
                    document.getElementById('ule_corePartnerId').value = '';
                    document.getElementById('ule_coreType').value = '';
                    document.getElementById('ule_coreName').value = '';
                    document.getElementById('ule_coreSelected').innerHTML = '';
                }
            }
        } catch (error) {
            console.error('[DC-CRM-EDITOR] Upline fetch error:', error);
        }
    }
    
    clearMnrHandler() {
        const el = document.getElementById('ule_mnrHandlerId');
        if (el) el.value = '';
        const se = document.getElementById('ule_mnrHandlerSearch');
        if (se) se.value = '';
        const sl = document.getElementById('ule_mnrHandlerSelected');
        if (sl) sl.innerHTML = '';
        this.clearLeadGuru();
    }

    clearAdiGuru() {
        const el = document.getElementById('ule_adiGuruId');
        if (el) el.value = '';
        const se = document.getElementById('ule_adiGuruSearch');
        if (se) se.value = '';
        const sl = document.getElementById('ule_adiGuruSelected');
        if (sl) sl.innerHTML = '';
    }
    
    clearTelecaller() {
        document.getElementById('ule_telecallerId').value = '';
        document.getElementById('ule_telecallerSearch').value = '';
        document.getElementById('ule_telecallerSelected').innerHTML = '';
    }
    
    clearFieldStaff() {
        document.getElementById('ule_fieldStaffId').value = '';
        document.getElementById('ule_fieldStaffSearch').value = '';
        document.getElementById('ule_fieldStaffSelected').innerHTML = '';
    }
    
    clearPartner() {
        document.getElementById('ule_partnerId').value = '';
        document.getElementById('ule_partnerSearch').value = '';
        document.getElementById('ule_partnerSelected').innerHTML = '';
    }
    
    clearTaskAssignee() {
        document.getElementById('ule_taskAssigneeId').value = '';
        document.getElementById('ule_taskAssigneeSearch').value = '';
        document.getElementById('ule_taskAssigneeSelected').innerHTML = '';
    }
    
    handleStatusChange() {
        const status = document.getElementById('ule_status').value;
        const revenueSection = document.getElementById('ule_revenueSection');
        const taskSection = document.getElementById('ule_taskSection');
        const leadId = document.getElementById('ule_leadId').value;
        
        if (status === 'won') {
            revenueSection.style.display = 'block';
            if (leadId) {
                document.getElementById('ule_transactionsSection').style.display = 'block';
                taskSection.style.display = 'block';
            }
        } else {
            revenueSection.style.display = 'none';
            taskSection.style.display = 'none';
        }
    }
    
    calculateBalance() {
        const total = parseFloat(document.getElementById('ule_dealValueTotal').value) || 0;
        const received = parseFloat(document.getElementById('ule_dealValueReceived').value) || 0;
        document.getElementById('ule_dealValueBalance').value = (total - received).toFixed(2);
    }
    
    async openEditModal(leadId, companyId) {
        if (!this.initialized) this.init();
        
        this.clearAllFields();
        document.getElementById('ule_leadId').value = leadId;
        document.getElementById('ule_companyId').value = companyId;
        
        try {
            let detailUrl;
            if (this.userRole === 'partner' || this.userRole === 'mnr') {
                detailUrl = `${this.apiBasePath}/unified-my-leads/${leadId}/details?company_id=${companyId}`;
            } else {
                detailUrl = `${this.apiBasePath}/leads/${leadId}?company_id=${companyId}`;
            }
            const response = await fetch(detailUrl, this.authOptions);
            const data = await response.json();
            
            if (data.success && data.data) {
                this.currentLead = data.data;
                this.populateForm(data.data);
                this.loadCallHistoryBadge(leadId, companyId);

                // DC Protocol N001: clear banner then lazy-load VGK status after modal opens
                const bannerEl = document.getElementById('ule_vgkBanner');
                if (bannerEl) bannerEl.innerHTML = '';

                const modal = new bootstrap.Modal(document.getElementById(this.modalId));
                modal.show();

                // Lazy-load VGK banner after modal is visible (non-blocking)
                setTimeout(() => this.loadVgkBanner(leadId, companyId), 200);
            } else {
                alert('Error loading lead details');
            }
        } catch (error) {
            console.error('[DC-CRM-EDITOR] Load error:', error);
            alert('Error loading lead details');
        }
    }
    
    populateForm(lead) {
        document.getElementById('ule_leadName').value = lead.name || '';
        document.getElementById('ule_phone').value = lead.phone || '';
        document.getElementById('ule_email').value = lead.email || '';
        document.getElementById('ule_category').value = lead.category_name || lead.category || '';
        document.getElementById('ule_status').value = lead.status || 'new';
        document.getElementById('ule_priority').value = lead.priority || 'medium';
        document.getElementById('ule_source').value = lead.source || '';
        document.getElementById('ule_lookingFor').value = lead.looking_for || '';
        document.getElementById('ule_description').value = lead.description || '';
        document.getElementById('ule_city').value = lead.city || '';
        document.getElementById('ule_area').value = lead.area || '';
        document.getElementById('ule_state').value = lead.state || '';
        document.getElementById('ule_pincode').value = lead.pincode || '';
        document.getElementById('ule_budgetMin').value = lead.budget_min || '';
        document.getElementById('ule_budgetMax').value = lead.budget_max || '';
        document.getElementById('ule_recentComments').value = lead.recent_comments || '';
        
        if (lead.city || lead.area || lead.state || lead.pincode || lead.budget_min || lead.budget_max || lead.recent_comments) {
            const locSection = document.getElementById('ule_locationSection');
            if (locSection) locSection.classList.add('show');
        }
        
        if (lead.next_followup_date) {
            try {
                const d = new Date(lead.next_followup_date);
                if (!isNaN(d.getTime())) {
                    const yyyy = d.getFullYear();
                    const mm = String(d.getMonth() + 1).padStart(2, '0');
                    const dd = String(d.getDate()).padStart(2, '0');
                    const hh = String(d.getHours()).padStart(2, '0');
                    const min = String(d.getMinutes()).padStart(2, '0');
                    document.getElementById('ule_nextFollowupDate').value = `${yyyy}-${mm}-${dd}T${hh}:${min}`;
                }
            } catch(e) { }
        }
        
        // Legacy backward-compat hidden field
        const _mnrHidEl = document.getElementById('ule_mnrHandlerId');
        if (_mnrHidEl && lead.mnr_handler_id) _mnrHidEl.value = lead.mnr_handler_id;

        // Network Assignment — Source
        const _srcType = lead.source_ref_type || (lead.mnr_handler_id ? 'mnr' : '');
        const _srcId   = lead.source_ref_id   || lead.mnr_handler_id || '';
        const _srcName = lead.source_ref_name || lead.mnr_handler_name || '';
        if (_srcType && _srcId) {
            const typeEl = document.getElementById('ule_sourceRefType');
            const searchEl = document.getElementById('ule_sourceRefSearch');
            const idEl = document.getElementById('ule_sourceRefId');
            const nameEl = document.getElementById('ule_sourceRefName');
            const selEl = document.getElementById('ule_sourceRefSelected');
            if (typeEl) { typeEl.value = _srcType; }
            if (idEl) idEl.value = _srcId;
            if (nameEl) nameEl.value = _srcName;
            const typeColors = { mnr:'bg-info', vgk:'bg-primary', partner:'bg-warning text-dark', vendor:'bg-secondary', staff:'bg-success' };
            const tc = typeColors[_srcType] || 'bg-secondary';
            if (selEl) selEl.innerHTML = `<span class="badge ${tc} p-2"><i class="fas fa-user me-1"></i>${_srcId} — ${_srcName}</span>`;
            const _isUserSrc = (_srcType === 'mnr' || _srcType === 'vgk');
            const _isPartnerSrc = (_srcType === 'partner' || _srcType === 'vgk_partner');
            const guruRow = document.getElementById('ule_guruRow');
            if (guruRow) guruRow.style.display = (_isUserSrc || _isPartnerSrc) ? '' : 'none';
            const zGuruRow = document.getElementById('ule_zGuruRow');
            if (zGuruRow) zGuruRow.style.display = (_isUserSrc || _isPartnerSrc) ? '' : 'none';
        }

        // DC-TEAM-ASSIGN-001: Senior/Extended/Core badge rendering on load
        const _guruT = lead.guru_id ? ((lead.guru_id||'').startsWith('VGK')?'vgk':'mnr') : (lead.guru_name?'partner':'');
        const gi = document.getElementById('ule_guruId'); if (gi) gi.value = lead.guru_id || '';
        const gtype = document.getElementById('ule_guruType'); if (gtype) gtype.value = _guruT;
        const gname = document.getElementById('ule_guruName'); if (gname) gname.value = lead.guru_name || '';
        const gs = document.getElementById('ule_guruSearch'); if (gs) gs.value = '';
        this._renderTeamBadge('guru', _guruT, lead.guru_id || '', lead.guru_name || '');

        const _zGuruT = lead.z_guru_id ? ((lead.z_guru_id||'').startsWith('VGK')?'vgk':'mnr') : (lead.z_guru_name?'partner':'');
        const zgi = document.getElementById('ule_zGuruId'); if (zgi) zgi.value = lead.z_guru_id || '';
        const zgtype = document.getElementById('ule_zGuruType'); if (zgtype) zgtype.value = _zGuruT;
        const zgname = document.getElementById('ule_zGuruName'); if (zgname) zgname.value = lead.z_guru_name || '';
        const zgs = document.getElementById('ule_zGuruSearch'); if (zgs) zgs.value = '';
        this._renderTeamBadge('z_guru', _zGuruT, lead.z_guru_id || '', lead.z_guru_name || '');

        // DC-TEAM-ASSIGN-001: Core row load from existing lead
        const _coreRow = document.getElementById('ule_coreRow');
        const _corePid = document.getElementById('ule_corePartnerId');
        const _tspid = document.getElementById('ule_teamSeniorPid');
        const _tepid = document.getElementById('ule_teamExtendedPid');
        if (_corePid) _corePid.value = lead.team_core_partner_id || '';
        if (_tspid) _tspid.value = lead.team_senior_partner_id || '';
        if (_tepid) _tepid.value = lead.team_extended_partner_id || '';
        const _coreT = lead.team_core_partner_id ? 'partner' : (lead.core_name ? 'mnr' : '');
        const ctEl = document.getElementById('ule_coreType'); if (ctEl) ctEl.value = _coreT;
        const cnEl = document.getElementById('ule_coreName'); if (cnEl) cnEl.value = lead.core_name || '';
        const csEl = document.getElementById('ule_coreSearch'); if (csEl) csEl.value = '';
        if (lead.core_name || lead.team_core_partner_id) {
            this._renderTeamBadge('core', _coreT, lead.team_core_partner_id || '', lead.core_name || '');
            if (_coreRow) _coreRow.style.display = '';
        } else { const csel = document.getElementById('ule_coreSelected'); if (csel) csel.innerHTML = ''; if (_coreRow) _coreRow.style.display = 'none'; }
        // DC-TEAM-ASSIGN-001: For MNR/VGK sources, Core is L4 user upline — fetch from API on load
        const _uleLoadSrcType = lead.source_ref_type || (lead.mnr_handler_id ? 'mnr' : '');
        const _uleLoadSrcId   = lead.source_ref_id   || lead.mnr_handler_id || '';
        if (['mnr','vgk'].includes(_uleLoadSrcType) && _uleLoadSrcId) {
            this.fetchUpline(_uleLoadSrcId);
        }

        // Team Assignment — Field Support
        const _fsType = lead.field_support_ref_type || (lead.adi_guru_id ? 'mnr' : '');
        const _fsId   = lead.field_support_ref_id   || lead.adi_guru_id || '';
        const _fsName = lead.field_support_ref_name || lead.adi_guru_name || '';
        if (_fsType && _fsId) {
            const typeEl = document.getElementById('ule_fieldSupportRefType');
            const searchEl = document.getElementById('ule_fieldSupportRefSearch');
            const idEl = document.getElementById('ule_fieldSupportRefId');
            const nameEl = document.getElementById('ule_fieldSupportRefName');
            const selEl = document.getElementById('ule_fieldSupportRefSelected');
            if (typeEl) typeEl.value = _fsType;
            if (idEl) idEl.value = _fsId;
            if (nameEl) nameEl.value = _fsName;
            const typeColors = { mnr:'bg-info', vgk:'bg-primary', partner:'bg-warning text-dark', vendor:'bg-secondary', staff:'bg-success' };
            const tc = typeColors[_fsType] || 'bg-secondary';
            if (selEl) selEl.innerHTML = `<span class="badge ${tc} p-2"><i class="fas fa-user me-1"></i>${_fsId} — ${_fsName}</span>`;
        }

        // Technical
        if (lead.technical_id) {
            const techIdEl = document.getElementById('ule_technicalId');
            const techSelEl = document.getElementById('ule_technicalSelected');
            if (techIdEl) techIdEl.value = lead.technical_id;
            if (techSelEl) techSelEl.innerHTML = `<span class="badge bg-success p-2"><i class="fas fa-user me-1"></i>${lead.technical_code || lead.technical_id} — ${lead.technical_name || ''}</span>`;
        }
        
        if (lead.telecaller_id) {
            document.getElementById('ule_telecallerId').value = lead.telecaller_id;
            document.getElementById('ule_telecallerSelected').innerHTML = `
                <span class="badge bg-success p-2">
                    <i class="fas fa-user me-1"></i>${lead.telecaller_code || lead.telecaller_id} - ${lead.telecaller_name || ''}
                </span>`;
        }
        
        if (lead.field_staff_id) {
            document.getElementById('ule_fieldStaffId').value = lead.field_staff_id;
            document.getElementById('ule_fieldStaffSelected').innerHTML = `
                <span class="badge bg-success p-2">
                    <i class="fas fa-user me-1"></i>${lead.field_staff_code || lead.field_staff_id} - ${lead.field_staff_name || ''}
                </span>`;
        }
        
        if (lead.associated_partner_id) {
            document.getElementById('ule_partnerId').value = lead.associated_partner_id;
            document.getElementById('ule_partnerSelected').innerHTML = `
                <span class="badge bg-warning text-dark p-2">
                    <i class="fas fa-handshake me-1"></i>${lead.associated_partner_code || lead.associated_partner_id} - ${lead.associated_partner_name || ''}
                </span>`;
        }
        
        document.getElementById('ule_dealValueTotal').value = lead.deal_value_total || 0;
        document.getElementById('ule_dealValueReceived').value = lead.deal_value_received || 0;
        document.getElementById('ule_dealValueBalance').value = lead.deal_value_balance || 0;
        
        this.handleStatusChange();
        
        if (lead.status === 'won' && lead.id) {
            const companyId = document.getElementById('ule_companyId').value;
            this.loadTransactions(lead.id, companyId);
            this.loadLeadDeals(lead.id);
        }
    }
    
    clearAllFields() {
        this.currentLead = null;
        
        ['ule_leadId', 'ule_companyId', 'ule_leadName', 'ule_phone', 'ule_email',
         'ule_category', 'ule_source', 'ule_lookingFor', 'ule_description', 'ule_nextFollowupDate',
         'ule_city', 'ule_area', 'ule_state', 'ule_pincode', 'ule_budgetMin', 'ule_budgetMax', 'ule_recentComments',
         'ule_mnrHandlerId', 'ule_guruId', 'ule_guruType', 'ule_guruName', 'ule_zGuruId', 'ule_zGuruType', 'ule_zGuruName', 'ule_corePartnerId', 'ule_coreType', 'ule_coreName', 'ule_adiGuruId',
         'ule_sourceRefId', 'ule_sourceRefName', 'ule_fieldSupportRefId', 'ule_fieldSupportRefName',
         'ule_technicalId', 'ule_technicalSearch',
         'ule_telecallerId', 'ule_telecallerSearch',
         'ule_fieldStaffId', 'ule_fieldStaffSearch', 'ule_partnerId', 'ule_partnerSearch',
         'ule_dealValueTotal', 'ule_dealValueReceived', 'ule_dealValueBalance',
         'ule_taskAssigneeId', 'ule_taskAssigneeSearch', 'ule_taskTitle', 'ule_taskDetails'
        ].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.value = '';
        });

        // Reset type hidden fields and search inputs
        ['ule_sourceRefType', 'ule_fieldSupportRefType'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.value = '';
        });
        ['ule_sourceRefSearch', 'ule_fieldSupportRefSearch'].forEach(id => {
            const el = document.getElementById(id);
            if (el) { el.value = ''; el.disabled = false; }
        });
        // Hide guru/z_guru/core rows and clear their search inputs + badges
        ['ule_guruRow','ule_zGuruRow','ule_coreRow'].forEach(id => { const el = document.getElementById(id); if (el) el.style.display = 'none'; });
        ['ule_guruSearch','ule_zGuruSearch','ule_coreSearch'].forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });

        ['ule_sourceRefSelected', 'ule_fieldSupportRefSelected', 'ule_technicalSelected',
         'ule_telecallerSelected', 'ule_fieldStaffSelected', 'ule_partnerSelected', 'ule_taskAssigneeSelected',
         'ule_guruSelected', 'ule_zGuruSelected', 'ule_coreSelected'
        ].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.innerHTML = '';
        });
        
        document.getElementById('ule_status').value = 'new';
        document.getElementById('ule_revenueSection').style.display = 'none';
        document.getElementById('ule_taskSection').style.display = 'none';
        document.getElementById('ule_callHistorySection').style.display = 'none';
        document.getElementById('ule_callHistoryBadge').textContent = 'Loading...';
        document.getElementById('ule_callHistoryBody').innerHTML = '<tr><td colspan="6" class="text-center text-muted py-3">Click header to load call history</td></tr>';
        document.getElementById('ule_callHistorySummary').innerHTML = '';
        const breakdownEl = document.getElementById('ule_callStaffBreakdown');
        if (breakdownEl) breakdownEl.style.display = 'none';
        const staffCardsEl = document.getElementById('ule_callStaffCards');
        if (staffCardsEl) staffCardsEl.innerHTML = '';
        const filterBarEl = document.getElementById('ule_callFilterBar');
        if (filterBarEl) filterBarEl.style.cssText = 'display:none !important;';
        const staffFilterEl = document.getElementById('ule_callStaffFilter');
        if (staffFilterEl) staffFilterEl.value = '';
        const typeFilterEl = document.getElementById('ule_callTypeFilter');
        if (typeFilterEl) typeFilterEl.value = '';
        document.getElementById('ule_transactionsBody').innerHTML = 
            '<tr><td colspan="6" class="text-center text-muted py-2">No transactions</td></tr>';
        this.leadDeals = [];
        document.getElementById('ule_dealsBody').innerHTML = '<tr><td colspan="7" class="text-center text-muted py-2">No deals yet. Click "Add Deal" to create one.</td></tr>';
    }
    
    async loadTransactions(leadId, companyId = null) {
        try {
            const cid = companyId || document.getElementById('ule_companyId').value;
            const response = await fetch(`${this.apiBasePath}/leads/${leadId}/transactions?company_id=${cid}`, this.authOptions);
            const data = await response.json();
            
            const tbody = document.getElementById('ule_transactionsBody');
            let approvedSum = 0, pendingSum = 0;
            
            this.leadTransactions = [];
            if (data.success && data.data && data.data.length > 0) {
                this.leadTransactions = data.data;
                tbody.innerHTML = data.data.map(txn => {
                    const isValidated = (txn.finance_status === 'validated' || txn.validation_status === 'validated');
                    if (isValidated) approvedSum += parseFloat(txn.amount) || 0;
                    else pendingSum += parseFloat(txn.amount) || 0;
                    
                    const statusBadge = isValidated 
                        ? '<span class="badge bg-success">Validated</span>'
                        : '<span class="badge bg-warning text-dark">Pending</span>';

                    const editBtn = !isValidated
                        ? `<button class="btn btn-outline-primary btn-sm py-0 px-1" style="font-size:10px;" onclick="window.crmLeadEditor.editTransaction(${txn.id})" title="Edit Transaction"><i class="fas fa-edit"></i></button>`
                        : '<span class="text-muted" style="font-size:10px;" title="Cannot edit validated transaction"><i class="fas fa-lock"></i></span>';
                    
                    return `<tr>
                        <td>${this.formatDate(txn.transaction_date)}</td>
                        <td>₹${this.formatNumber(txn.amount)}</td>
                        <td>${txn.transaction_type || '-'}</td>
                        <td>${txn.payment_mode || '-'}</td>
                        <td>${txn.deal_info || '-'}</td>
                        <td>${statusBadge}</td>
                        <td>${editBtn}</td>
                    </tr>`;
                }).join('');
            } else {
                tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-2">No transactions</td></tr>';
            }
            
            document.getElementById('ule_financeApproved').textContent = this.formatNumber(approvedSum);
            document.getElementById('ule_financePending').textContent = this.formatNumber(pendingSum);
        } catch (error) {
            console.error('[DC-CRM-EDITOR] Transactions load error:', error);
        }
    }
    
    toggleAddDealForm() {
        const section = document.getElementById('ule_addDealFormSection');
        if (section.style.display === 'none') {
            section.style.display = 'block';
            document.getElementById('ule_editDealId').value = '';
            this.populateDealCompanyDropdown();
            document.getElementById('ule_dealCompanySelect').value = '';
            document.getElementById('ule_dealCategorySelect').innerHTML = '<option value="">Select Category</option>';
            document.getElementById('ule_dealValueInput').value = '';
            document.getElementById('ule_dealDateInput').value = '';
            document.getElementById('ule_dealNotesInput').value = '';
        } else {
            section.style.display = 'none';
            document.getElementById('ule_editDealId').value = '';
        }
    }
    
    populateDealCompanyDropdown() {
        const select = document.getElementById('ule_dealCompanySelect');
        select.innerHTML = '<option value="">Select Company</option>';
        if (this.companiesList) {
            this.companiesList.forEach(c => {
                const opt = document.createElement('option');
                opt.value = c.id;
                opt.textContent = `${c.company_name} (${c.company_code})`;
                select.appendChild(opt);
            });
        }
    }
    
    async onDealCompanyChange() {
        const dealCompanyId = document.getElementById('ule_dealCompanySelect').value;
        const catSelect = document.getElementById('ule_dealCategorySelect');
        catSelect.innerHTML = '<option value="">Loading...</option>';
        if (!dealCompanyId) { catSelect.innerHTML = '<option value="">Select Category</option>'; return; }
        try {
            const response = await fetch(`${this.apiBasePath}/revenue-categories?company_id=${dealCompanyId}&active_only=true`, this.authOptions);
            if (response.ok) {
                const data = await response.json();
                this.dealCategoriesCache[dealCompanyId] = data.categories || [];
                catSelect.innerHTML = '<option value="">Select Category</option>';
                (data.categories || []).forEach(cat => {
                    const opt = document.createElement('option');
                    opt.value = cat.id;
                    opt.textContent = cat.category_name;
                    catSelect.appendChild(opt);
                });
                if ((data.categories || []).length === 0) catSelect.innerHTML = '<option value="">No categories found</option>';
            } else { catSelect.innerHTML = '<option value="">Failed to load</option>'; }
        } catch (e) { console.error('Failed to load categories:', e); catSelect.innerHTML = '<option value="">Error loading</option>'; }
    }
    
    async saveDeal() {
        const editDealId = document.getElementById('ule_editDealId').value;
        const dealCompanyId = document.getElementById('ule_dealCompanySelect').value;
        const categoryId = document.getElementById('ule_dealCategorySelect').value;
        const dealValue = parseFloat(document.getElementById('ule_dealValueInput').value) || 0;
        const dealDate = document.getElementById('ule_dealDateInput').value || null;
        const dealNotes = document.getElementById('ule_dealNotesInput').value || null;
        if (!dealCompanyId) { alert('Please select a company'); return; }
        if (!categoryId) { alert('Please select a category'); return; }
        if (dealValue <= 0) { alert('Please enter a valid deal value'); return; }
        const leadId = document.getElementById('ule_leadId').value;
        const companyId = document.getElementById('ule_companyId').value;
        if (!leadId || !companyId) { alert('No lead selected'); return; }

        const payload = {
            company_id: parseInt(dealCompanyId),
            revenue_category_id: parseInt(categoryId),
            deal_value_total: dealValue,
            deal_date: dealDate,
            notes: dealNotes
        };

        try {
            let url, method;
            if (editDealId) {
                url = `${this.apiBasePath}/deals/${editDealId}?company_id=${companyId}`;
                method = 'PUT';
            } else {
                url = `${this.apiBasePath}/leads/${leadId}/deals?company_id=${companyId}`;
                method = 'POST';
                payload.deal_value_received = 0;
            }
            const response = await fetch(url, {
                method, ...this.authOptions,
                headers: { ...this.authOptions.headers, 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await response.json();
            if (data.success) {
                alert(editDealId ? 'Deal updated successfully' : 'Deal created successfully');
                document.getElementById('ule_addDealFormSection').style.display = 'none';
                document.getElementById('ule_editDealId').value = '';
                this.loadLeadDeals(leadId);
            } else { alert(data.detail || 'Failed to save deal'); }
        } catch (e) { console.error('Failed to save deal:', e); alert('Failed to save deal'); }
    }

    editDeal(dealId) {
        const deal = this.leadDeals.find(d => d.id === dealId);
        if (!deal) return;
        const section = document.getElementById('ule_addDealFormSection');
        section.style.display = 'block';
        document.getElementById('ule_editDealId').value = deal.id;
        this.populateDealCompanyDropdown();
        setTimeout(() => {
            document.getElementById('ule_dealCompanySelect').value = deal.company_id || '';
            this.onDealCompanyChange().then(() => {
                setTimeout(() => {
                    document.getElementById('ule_dealCategorySelect').value = deal.revenue_category_id || '';
                }, 300);
            });
            document.getElementById('ule_dealValueInput').value = deal.deal_value_total || '';
            const dateEl = document.getElementById('ule_dealDateInput');
            if (deal.deal_date) {
                dateEl.value = deal.deal_date.substring(0, 10);
            } else { dateEl.value = ''; }
            document.getElementById('ule_dealNotesInput').value = deal.notes || '';
        }, 100);
    }
    
    async loadLeadDeals(leadId) {
        const tbody = document.getElementById('ule_dealsBody');
        const companyId = document.getElementById('ule_companyId').value;
        if (!leadId || !companyId) { tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-2">No deals</td></tr>'; this.leadDeals = []; this.updateDealAggregates(); return; }
        try {
            const response = await fetch(`${this.apiBasePath}/leads/${leadId}/deals?company_id=${companyId}`, this.authOptions);
            if (!response.ok) throw new Error('Failed');
            const data = await response.json();
            this.leadDeals = data.deals || [];
            if (this.leadDeals.length === 0) { tbody.innerHTML = '<tr><td colspan="9" class="text-center text-muted py-2">No deals yet. Click "Add Deal" to create one.</td></tr>'; }
            else {
                tbody.innerHTML = this.leadDeals.map((deal, idx) => `<tr><td class="fw-medium"><code style="font-size:11px;color:#059669;">${deal.deal_code || ('Deal ' + (idx + 1))}</code></td><td>${this.formatDate(deal.deal_date)}</td><td>${deal.company_name || '-'}</td><td><span class="badge bg-info text-dark">${deal.category_name || '-'}</span></td><td class="fw-medium">₹${this.formatNumber(deal.deal_value_total)}</td><td class="text-success">₹${this.formatNumber(deal.deal_value_received)}</td><td class="text-danger">₹${this.formatNumber(deal.deal_value_balance)}</td><td><span class="badge bg-${deal.status === 'active' ? 'success' : 'secondary'}">${deal.status || 'active'}</span></td><td><button class="btn btn-outline-primary btn-sm py-0 px-1" style="font-size:10px;" onclick="window.crmLeadEditor.editDeal(${deal.id})" title="Edit Deal"><i class="fas fa-edit"></i></button></td></tr>`).join('');
            }
            this.updateDealAggregates();
        } catch (e) { console.error('Failed to load deals:', e); tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-2">Error loading deals</td></tr>'; this.leadDeals = []; this.updateDealAggregates(); }
    }
    
    updateDealAggregates() {
        const total = this.leadDeals.reduce((s, d) => s + (d.deal_value_total || 0), 0);
        const received = this.leadDeals.reduce((s, d) => s + (d.deal_value_received || 0), 0);
        const balance = this.leadDeals.reduce((s, d) => s + (d.deal_value_balance || 0), 0);
        const totalEl = document.getElementById('ule_dealAggregateTotal');
        const receivedEl = document.getElementById('ule_dealAggregateReceived');
        const balanceEl = document.getElementById('ule_dealAggregateBalance');
        if (totalEl) totalEl.textContent = this.formatNumber(total);
        if (receivedEl) receivedEl.textContent = this.formatNumber(received);
        if (balanceEl) balanceEl.textContent = this.formatNumber(balance);
        document.getElementById('ule_dealValueTotal').value = total;
        document.getElementById('ule_dealValueReceived').value = received;
        document.getElementById('ule_dealValueBalance').value = balance;
    }
    
    populateTxnDealDropdown() {
        const select = document.getElementById('ule_txnDealSelect');
        if (!select) return;
        select.innerHTML = '<option value="">Select Deal</option>';
        this.leadDeals.forEach((deal, idx) => {
            const opt = document.createElement('option');
            opt.value = deal.id;
            opt.textContent = `${deal.deal_code || ('Deal ' + (idx + 1))} - ${deal.category_name || ''} (₹${this.formatNumber(deal.deal_value_total)})`;
            select.appendChild(opt);
        });
    }
    
    setCompanies(list) {
        this.companiesList = list || [];
    }
    
    formatDate(dateStr) {
        if (!dateStr) return '-';
        try {
            return new Date(dateStr).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
        } catch { return dateStr; }
    }
    
    formatNumber(num) {
        return (parseFloat(num) || 0).toLocaleString('en-IN', { maximumFractionDigits: 2 });
    }
    
    openAddTransactionModal() {
        document.getElementById('ule_editTxnId').value = '';
        document.getElementById('ule_txnModalTitle').innerHTML = '<i class="fas fa-receipt me-2"></i>Add Payment Transaction';
        const now = new Date();
        now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
        document.getElementById('ule_txnDate').value = now.toISOString().slice(0, 16);
        document.getElementById('ule_txnAmount').value = '';
        document.getElementById('ule_txnType').value = 'partial';
        document.getElementById('ule_txnMode').value = 'upi';
        document.getElementById('ule_txnReference').value = '';
        
        this.populateTxnDealDropdown();
        const txnModal = new bootstrap.Modal(document.getElementById('ule_addTransactionModal'));
        txnModal.show();
    }

    editTransaction(txnId) {
        const txn = (this.leadTransactions || []).find(t => t.id === txnId);
        if (!txn) return;
        document.getElementById('ule_editTxnId').value = txn.id;
        document.getElementById('ule_txnModalTitle').innerHTML = '<i class="fas fa-edit me-2"></i>Edit Transaction';
        if (txn.transaction_date) {
            const d = new Date(txn.transaction_date);
            d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
            document.getElementById('ule_txnDate').value = d.toISOString().slice(0, 16);
        }
        document.getElementById('ule_txnAmount').value = txn.amount || '';
        document.getElementById('ule_txnType').value = txn.transaction_type || 'partial';
        document.getElementById('ule_txnMode').value = txn.payment_mode || 'upi';
        document.getElementById('ule_txnReference').value = txn.reference_number || txn.notes || '';
        this.populateTxnDealDropdown();
        setTimeout(() => {
            const dealSelect = document.getElementById('ule_txnDealSelect');
            if (txn.deal_id && dealSelect) dealSelect.value = txn.deal_id;
        }, 100);
        const txnModal = new bootstrap.Modal(document.getElementById('ule_addTransactionModal'));
        txnModal.show();
    }
    
    async saveTransaction() {
        const leadId = document.getElementById('ule_leadId').value;
        const companyId = document.getElementById('ule_companyId').value;
        const editTxnId = document.getElementById('ule_editTxnId').value;
        
        const payload = {
            lead_id: parseInt(leadId),
            company_id: parseInt(companyId),
            transaction_date: document.getElementById('ule_txnDate').value,
            amount: parseFloat(document.getElementById('ule_txnAmount').value),
            transaction_type: document.getElementById('ule_txnType').value,
            payment_mode: document.getElementById('ule_txnMode').value,
            reference_number: document.getElementById('ule_txnReference').value,
            deal_id: null,
            revenue_category_id: null
        };
        
        const txnDealEl = document.getElementById('ule_txnDealSelect');
        if (txnDealEl && txnDealEl.value) {
            payload.deal_id = parseInt(txnDealEl.value);
            const selectedDeal = this.leadDeals.find(d => d.id === payload.deal_id);
            if (selectedDeal) payload.revenue_category_id = selectedDeal.revenue_category_id;
        }
        
        if (!payload.amount || payload.amount <= 0) {
            alert('Please enter a valid amount');
            return;
        }
        
        try {
            let url, method;
            if (editTxnId) {
                url = `${this.apiBasePath}/transactions/${editTxnId}?company_id=${companyId}`;
                method = 'PUT';
            } else {
                url = `${this.apiBasePath}/leads/${leadId}/transactions?company_id=${companyId}`;
                method = 'POST';
            }
            const response = await fetch(url, {
                method,
                ...this.authOptions,
                headers: { ...this.authOptions.headers, 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await response.json();
            
            if (data.success) {
                bootstrap.Modal.getInstance(document.getElementById('ule_addTransactionModal')).hide();
                this.loadTransactions(leadId);
                alert(editTxnId ? 'Transaction updated successfully!' : 'Transaction added successfully!');
            } else {
                alert(data.detail || 'Error saving transaction');
            }
        } catch (error) {
            console.error('[DC-CRM-EDITOR] Transaction save error:', error);
            alert('Error saving transaction');
        }
    }
    
    async saveLead() {
        const leadId = document.getElementById('ule_leadId').value;
        const companyId = document.getElementById('ule_companyId').value;
        const status = document.getElementById('ule_status').value;
        
        const nextFollowup = document.getElementById('ule_nextFollowupDate').value;
        
        const payload = {
            status: status,
            name: document.getElementById('ule_leadName').value || null,
            phone: document.getElementById('ule_phone').value || null,
            email: document.getElementById('ule_email').value || null,
            priority: document.getElementById('ule_priority').value || null,
            source: document.getElementById('ule_source').value || null,
            next_followup_date: nextFollowup || null,
            looking_for: document.getElementById('ule_lookingFor').value || null,
            description: document.getElementById('ule_description').value || null,
            recent_comments: document.getElementById('ule_recentComments').value || null,
            city: document.getElementById('ule_city').value || null,
            area: document.getElementById('ule_area').value || null,
            state: document.getElementById('ule_state').value || null,
            pincode: document.getElementById('ule_pincode').value || null,
            budget_min: document.getElementById('ule_budgetMin').value !== '' ? parseFloat(document.getElementById('ule_budgetMin').value) : null,
            budget_max: document.getElementById('ule_budgetMax').value !== '' ? parseFloat(document.getElementById('ule_budgetMax').value) : null,
            // Network Assignment (new unified fields)
            source_ref_type: document.getElementById('ule_sourceRefType')?.value || null,
            source_ref_id: document.getElementById('ule_sourceRefId')?.value || null,
            source_ref_name: document.getElementById('ule_sourceRefName')?.value || null,
            field_support_ref_type: document.getElementById('ule_fieldSupportRefType')?.value || null,
            field_support_ref_id: document.getElementById('ule_fieldSupportRefId')?.value || null,
            field_support_ref_name: document.getElementById('ule_fieldSupportRefName')?.value || null,
            technical_id: document.getElementById('ule_technicalId')?.value ? parseInt(document.getElementById('ule_technicalId').value) : null,
            // DC Protocol Fix (Apr 2026): mnr_handler_id is FK to user.id — only send for
            // user-type sources (mnr/vgk). For partner/vendor/staff/external, the legacy
            // FK field must be null; attribution lives in source_ref_* exclusively.
            mnr_handler_id: (['mnr','vgk'].includes(document.getElementById('ule_sourceRefType')?.value || ''))
                ? (document.getElementById('ule_mnrHandlerId')?.value || null)
                : null,
            guru_id: document.getElementById('ule_guruId')?.value || null,
            z_guru_id: document.getElementById('ule_zGuruId')?.value || null,
            // DC Protocol Fix (Apr 2026): Extract partner-chain upline names for text storage
            guru_name: (() => { const _t = document.getElementById('ule_guruType')?.value || ''; return (['partner','vgk_partner'].includes(_t)) ? (document.getElementById('ule_guruName')?.value || null) : null; })(),
            z_guru_name: (() => { const _t = document.getElementById('ule_zGuruType')?.value || ''; return (['partner','vgk_partner'].includes(_t)) ? (document.getElementById('ule_zGuruName')?.value || null) : null; })(),
            // DC-TEAM-ASSIGN-001 (Jun 2026): Team Assignment override FKs
            team_senior_partner_id: (() => { const v = document.getElementById('ule_teamSeniorPid')?.value; return v ? parseInt(v) || null : null; })(),
            team_extended_partner_id: (() => { const v = document.getElementById('ule_teamExtendedPid')?.value; return v ? parseInt(v) || null : null; })(),
            team_core_partner_id: (() => { const v = document.getElementById('ule_corePartnerId')?.value; return v ? parseInt(v) || null : null; })(),
            core_name: document.getElementById('ule_coreName')?.value || null,
            adi_guru_id: (['mnr','vgk'].includes(document.getElementById('ule_fieldSupportRefType')?.value || ''))
                ? (document.getElementById('ule_adiGuruId')?.value || null)
                : null,
            telecaller_id: document.getElementById('ule_telecallerId').value ? parseInt(document.getElementById('ule_telecallerId').value) : null,
            field_staff_id: document.getElementById('ule_fieldStaffId').value ? parseInt(document.getElementById('ule_fieldStaffId').value) : null,
            associated_partner_id: document.getElementById('ule_partnerId').value ? parseInt(document.getElementById('ule_partnerId').value) : null
        };
        
        if (status === 'won') {
            payload.deal_value_total = parseFloat(document.getElementById('ule_dealValueTotal').value) || 0;
            payload.deal_value_received = parseFloat(document.getElementById('ule_dealValueReceived').value) || 0;
            payload.deal_value_balance = parseFloat(document.getElementById('ule_dealValueBalance').value) || 0;
        }
        
        try {
            const response = await fetch(`${this.apiBasePath}/unified-my-leads/${leadId}/full-update?company_id=${companyId}`, {
                method: 'PUT',
                ...this.authOptions,
                headers: { ...this.authOptions.headers, 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await response.json();
            
            if (data.success) {
                const taskAssigneeId = document.getElementById('ule_taskAssigneeId').value;
                const taskTitle = document.getElementById('ule_taskTitle').value.trim();
                
                if (status === 'won' && taskAssigneeId && taskTitle) {
                    await this.createTask(leadId, companyId, taskAssigneeId, taskTitle);
                }
                
                bootstrap.Modal.getInstance(document.getElementById(this.modalId)).hide();
                alert('Lead updated successfully!');
                this.onSave(data.data);
            } else {
                alert(data.detail || 'Error updating lead');
            }
        } catch (error) {
            console.error('[DC-CRM-EDITOR] Save error:', error);
            alert('Error updating lead');
        }
    }
    
    async createTask(leadId, companyId, assigneeId, title) {
        try {
            const payload = {
                lead_id: parseInt(leadId),
                company_id: parseInt(companyId),
                assigned_to: parseInt(assigneeId),
                title: title,
                details: document.getElementById('ule_taskDetails').value || ''
            };
            
            await fetch(`${this.apiBasePath}/leads/${leadId}/tasks`, {
                method: 'POST',
                ...this.authOptions,
                headers: { ...this.authOptions.headers, 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
        } catch (error) {
            console.error('[DC-CRM-EDITOR] Task creation error:', error);
        }
    }
    
    async loadCallHistoryBadge(leadId, companyId) {
        try {
            const response = await fetch(`/api/v1/call-tracking/lead/${leadId}/calls?company_id=${companyId}&per_page=1`, {
                ...this.authOptions,
                headers: { ...this.authOptions.headers }
            });
            const data = await response.json();
            const badge = document.getElementById('ule_callHistoryBadge');
            if (data.success) {
                const total = data.summary.total_calls || 0;
                badge.textContent = total > 0 ? `${total} calls` : 'No calls';
                badge.className = total > 0 ? 'badge bg-light text-dark' : 'badge bg-light text-muted';
            } else {
                badge.textContent = '0 calls';
            }
        } catch (e) {
            document.getElementById('ule_callHistoryBadge').textContent = '0 calls';
        }
    }
    
    toggleCallHistory() {
        const section = document.getElementById('ule_callHistorySection');
        if (section.style.display === 'none') {
            section.style.display = 'block';
            this.loadCallHistory();
        } else {
            section.style.display = 'none';
        }
    }
    
    async loadCallHistory(staffFilter, callTypeFilter) {
        const leadId = document.getElementById('ule_leadId').value;
        const companyId = document.getElementById('ule_companyId').value;
        if (!leadId) return;
        
        const tbody = document.getElementById('ule_callHistoryBody');
        tbody.innerHTML = '<tr><td colspan="6" class="text-center py-3"><div class="spinner-border spinner-border-sm text-info"></div> Loading...</td></tr>';
        
        try {
            let url = `/api/v1/call-tracking/lead/${leadId}/calls?company_id=${companyId}`;
            if (staffFilter) url += `&staff_id=${staffFilter}`;
            if (callTypeFilter) url += `&call_type=${callTypeFilter}`;
            
            const response = await fetch(url, {
                ...this.authOptions,
                headers: { ...this.authOptions.headers }
            });
            const data = await response.json();
            
            if (data.success) {
                const summary = data.summary;
                const badge = document.getElementById('ule_callHistoryBadge');
                badge.textContent = `${summary.total_calls} calls`;
                
                const summaryDiv = document.getElementById('ule_callHistorySummary');
                const totalMins = Math.floor((summary.total_duration_seconds || 0) / 60);
                const totalSecs = (summary.total_duration_seconds || 0) % 60;
                summaryDiv.innerHTML = `
                    <div class="col-auto"><span class="badge bg-success"><i class="fas fa-phone me-1"></i>${summary.outgoing || 0} Outgoing</span></div>
                    <div class="col-auto"><span class="badge bg-primary"><i class="fas fa-phone-volume me-1"></i>${summary.incoming || 0} Incoming</span></div>
                    <div class="col-auto"><span class="badge bg-danger"><i class="fas fa-phone-slash me-1"></i>${summary.missed || 0} Missed</span></div>
                    <div class="col-auto"><span class="badge bg-secondary"><i class="fas fa-clock me-1"></i>${totalMins}m ${totalSecs}s Total</span></div>
                    <div class="col-auto"><span class="badge bg-info"><i class="fas fa-user-tie me-1"></i>${summary.staff_involved || 0} Staff</span></div>
                `;
                
                const breakdownDiv = document.getElementById('ule_callStaffBreakdown');
                const cardsDiv = document.getElementById('ule_callStaffCards');
                const filterBar = document.getElementById('ule_callFilterBar');
                const staffSelect = document.getElementById('ule_callStaffFilter');
                
                if (data.staff_breakdown && data.staff_breakdown.length >= 2) {
                    breakdownDiv.style.display = 'block';
                    filterBar.style.cssText = 'display:flex !important;';
                    
                    cardsDiv.innerHTML = data.staff_breakdown.map(s => {
                        const dur = Math.floor((s.total_duration || 0) / 60);
                        const isActive = staffFilter && parseInt(staffFilter) === s.staff_id;
                        return `<div class="border rounded p-2 ${isActive ? 'border-info bg-light' : ''}" style="min-width:150px;font-size:12px;cursor:pointer;" onclick="document.getElementById('ule_callStaffFilter').value='${s.staff_id}';window.crmLeadEditor.filterCallHistory();">
                            <div class="fw-bold">${s.staff_name}</div>
                            <div class="text-muted">${s.emp_code}</div>
                            <div class="mt-1">
                                <span class="badge bg-success badge-sm">${s.outgoing} Out</span>
                                <span class="badge bg-primary badge-sm">${s.incoming} In</span>
                                <span class="badge bg-danger badge-sm">${s.missed} Miss</span>
                            </div>
                            <div class="text-muted mt-1">${s.total_calls} calls &middot; ${dur}m</div>
                        </div>`;
                    }).join('');
                    
                    if (!staffFilter && !callTypeFilter) {
                        staffSelect.innerHTML = '<option value="">All Handlers</option>' +
                            data.staff_list.map(s => `<option value="${s.id}">${s.name}</option>`).join('');
                    }
                } else if (data.staff_breakdown && data.staff_breakdown.length === 1) {
                    breakdownDiv.style.display = 'none';
                    filterBar.style.cssText = 'display:none !important;';
                } else {
                    breakdownDiv.style.display = 'none';
                    filterBar.style.cssText = 'display:none !important;';
                }
                
                if (data.data.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted py-3"><i class="fas fa-phone-slash me-2"></i>No call history found' + (staffFilter ? ' for this handler' : ' for this lead') + '</td></tr>';
                    return;
                }
                
                tbody.innerHTML = data.data.map(call => {
                    const dt = new Date(call.call_datetime);
                    const dateStr = dt.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: '2-digit' });
                    const timeStr = dt.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
                    const mins = Math.floor(call.duration_seconds / 60);
                    const secs = call.duration_seconds % 60;
                    const durationStr = call.duration_seconds > 0 ? `${mins}m ${secs}s` : '-';
                    
                    let typeBadge = '';
                    switch(call.call_type) {
                        case 'OUTGOING': typeBadge = '<span class="badge bg-success"><i class="fas fa-arrow-up me-1"></i>Out</span>'; break;
                        case 'INCOMING': typeBadge = '<span class="badge bg-primary"><i class="fas fa-arrow-down me-1"></i>In</span>'; break;
                        case 'MISSED': typeBadge = '<span class="badge bg-danger"><i class="fas fa-times me-1"></i>Missed</span>'; break;
                        case 'REJECTED': typeBadge = '<span class="badge bg-warning text-dark"><i class="fas fa-ban me-1"></i>Rejected</span>'; break;
                        default: typeBadge = `<span class="badge bg-secondary">${call.call_type}</span>`;
                    }

                    let recordingBtn = '';
                    let recordingStatus = '<span class="badge bg-secondary" style="font-size:10px;"><i class="fas fa-microphone-slash me-1"></i>No Rec</span>';
                    if (call.has_recording && call.recording_id) {
                        recordingBtn = `<button class="btn btn-sm btn-outline-info py-0 px-1" onclick="window.crmLeadEditor.playRecording(${call.recording_id}, this)" title="Play Recording"><i class="fas fa-play" style="font-size:10px;"></i></button>`;
                        recordingStatus = `<span class="badge bg-success" style="font-size:10px;"><i class="fas fa-microphone me-1"></i>Synced</span> ${recordingBtn}`;
                    }
                    
                    return `<tr>
                        <td><small>${dateStr}<br><span class="text-muted">${timeStr}</span></small></td>
                        <td>${typeBadge}</td>
                        <td><small>${durationStr}</small></td>
                        <td><small>${call.staff_name || '-'}</small></td>
                        <td>${recordingStatus}</td>
                        <td><small class="text-muted">${call.phone_number || '-'}</small></td>
                    </tr>`;
                }).join('');
            } else {
                tbody.innerHTML = '<tr><td colspan="6" class="text-center text-danger py-3">Error loading call history</td></tr>';
            }
        } catch (error) {
            console.error('[DC-CRM-EDITOR] Call history error:', error);
            tbody.innerHTML = '<tr><td colspan="6" class="text-center text-danger py-3">Error loading call history</td></tr>';
            document.getElementById('ule_callHistoryBadge').textContent = 'Error';
        }
    }
    
    filterCallHistory() {
        const staffId = document.getElementById('ule_callStaffFilter').value;
        const callType = document.getElementById('ule_callTypeFilter').value;
        this.loadCallHistory(staffId || null, callType || null);
    }
    
    resetCallFilters() {
        document.getElementById('ule_callStaffFilter').value = '';
        document.getElementById('ule_callTypeFilter').value = '';
        this.loadCallHistory();
    }

    playRecording(recordingId, btnEl) {
        const existingPlayer = document.getElementById('ule_audioPlayerRow');
        if (existingPlayer) existingPlayer.remove();

        const tr = btnEl.closest('tr');
        const playerRow = document.createElement('tr');
        playerRow.id = 'ule_audioPlayerRow';
        playerRow.innerHTML = `<td colspan="6" style="padding:8px 12px;background:#f0f9ff;">
            <div class="d-flex align-items-center gap-2">
                <audio controls autoplay style="flex:1;height:32px;" src="/api/v1/call-tracking/recordings/${recordingId}/stream">
                    Your browser does not support audio playback.
                </audio>
                <button class="btn btn-sm btn-outline-secondary py-0 px-1" onclick="document.getElementById('ule_audioPlayerRow').remove()" title="Close"><i class="fas fa-times" style="font-size:10px;"></i></button>
            </div>
        </td>`;
        tr.after(playerRow);
    }
    // ── DC Protocol N001: VGK Status Banner ──────────────────────────────────

    async loadVgkBanner(leadId, companyId) {
        const el = document.getElementById('ule_vgkBanner');
        if (!el) return;
        el.innerHTML = '<div style="font-size:12px;color:#9ca3af;padding:6px 0"><i class="fas fa-spinner fa-spin me-1"></i>Checking VGK member status…</div>';
        try {
            const res = await fetch(`/api/v1/crm/leads/${leadId}/vgk-status?company_id=${companyId}`, this.authOptions);
            const d = await res.json();
            if (!d.success) { el.innerHTML = ''; return; }
            if (d.is_vgk) {
                this._renderVgkMemberBanner(el, d, leadId, companyId);
            } else {
                this._renderVgkNonMemberBanner(el, leadId, companyId);
            }
        } catch (e) {
            el.innerHTML = '';
            console.warn('[DC-VGK-BANNER] Non-fatal:', e);
        }
    }

    _renderVgkMemberBanner(el, member, leadId, companyId) {
        const pts = (member.points_balance || 0).toLocaleString('en-IN');
        const activeLabel = member.is_active
            ? '<span style="background:#dcfce7;color:#166534;border-radius:12px;padding:2px 8px;font-size:11px;font-weight:700"><i class="fas fa-check-circle me-1"></i>Active</span>'
            : '<span style="background:#fef9c3;color:#713f12;border-radius:12px;padding:2px 8px;font-size:11px;font-weight:700"><i class="fas fa-clock me-1"></i>Pending Activation</span>';
        el.innerHTML = `
            <div style="background:linear-gradient(135deg,#f5f3ff,#ede9fe);border:1.5px solid #a78bfa;border-radius:10px;padding:10px 14px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px">
                <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
                    <div style="width:36px;height:36px;border-radius:50%;background:linear-gradient(135deg,#7c3aed,#4c1d95);display:flex;align-items:center;justify-content:center">
                        <i class="fas fa-sitemap" style="color:#fff;font-size:14px"></i>
                    </div>
                    <div>
                        <div style="font-weight:700;color:#4c1d95;font-size:13px"><i class="fas fa-user-check me-1"></i>VGK4U Member</div>
                        <div style="font-size:12px;color:#6d28d9">
                            <strong>${this._esc(member.partner_code)}</strong>
                            &nbsp;·&nbsp; <i class="fas fa-coins me-1"></i>${pts} pts
                            &nbsp;·&nbsp; ${activeLabel}
                        </div>
                    </div>
                </div>
                <div style="display:flex;gap:6px;flex-wrap:wrap">
                    <button class="btn btn-sm" style="background:#7c3aed;color:#fff;border:none;border-radius:8px;font-size:12px;padding:5px 12px"
                        onclick="window.crmLeadEditor._showVgkShareModal(${JSON.stringify(member)}, ${leadId}, ${companyId}, false)">
                        <i class="fab fa-whatsapp me-1"></i>Share Login Details
                    </button>
                </div>
            </div>`;
    }

    _renderVgkNonMemberBanner(el, leadId, companyId) {
        el.innerHTML = `
            <div style="background:linear-gradient(135deg,#fffbeb,#fef3c7);border:1.5px solid #f59e0b;border-radius:10px;padding:10px 14px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px">
                <div style="display:flex;align-items:center;gap:10px">
                    <div style="width:36px;height:36px;border-radius:50%;background:linear-gradient(135deg,#d97706,#f59e0b);display:flex;align-items:center;justify-content:center">
                        <i class="fas fa-user-plus" style="color:#fff;font-size:14px"></i>
                    </div>
                    <div>
                        <div style="font-weight:700;color:#92400e;font-size:13px">Not a VGK4U Member</div>
                        <div style="font-size:12px;color:#78350f">Register this lead as a VGK member to share login & earn commissions</div>
                    </div>
                </div>
                <button class="btn btn-sm" id="ule_vgkRegisterBtn" style="background:#d97706;color:#fff;border:none;border-radius:8px;font-size:12px;padding:5px 14px"
                    onclick="window.crmLeadEditor._registerAsVgk(${leadId}, ${companyId})">
                    <i class="fas fa-plus-circle me-1"></i>Register as VGK
                </button>
            </div>`;
    }

    async _registerAsVgk(leadId, companyId) {
        const btn = document.getElementById('ule_vgkRegisterBtn');
        if (btn) { btn.disabled = true; btn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Registering…'; }
        try {
            const res = await fetch(`/api/v1/crm/leads/${leadId}/register-as-vgk?company_id=${companyId}`, {
                method: 'POST', ...this.authOptions
            });
            const d = await res.json();
            if (d.success) {
                this._showVgkShareModal(d, leadId, companyId, true);
                this._renderVgkMemberBanner(document.getElementById('ule_vgkBanner'), {
                    is_vgk: true, partner_code: d.partner_code, partner_name: d.partner_name,
                    phone: d.phone, points_balance: d.points_balance || 10000, is_active: false
                }, leadId, companyId);
            } else {
                alert(d.detail || 'Registration failed');
                if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fas fa-plus-circle me-1"></i>Register as VGK'; }
            }
        } catch(e) {
            alert('Error registering member');
            if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fas fa-plus-circle me-1"></i>Register as VGK'; }
        }
    }

    _showVgkShareModal(member, leadId, companyId, isNew) {
        const existing = document.getElementById('ule_vgkShareOverlay');
        if (existing) existing.remove();

        const code    = member.partner_code || '';
        const name    = member.partner_name || (this.currentLead ? this.currentLead.name : '') || '';
        const phone   = (member.phone || (this.currentLead ? this.currentLead.phone : '') || '').replace(/\D/g, '');
        const pwd     = member.auto_password || null;
        const pts     = (member.points_balance || 0).toLocaleString('en-IN');
        const ref     = 'https://vgk4u.com/vgk/login?tab=signup&ref=' + encodeURIComponent(code);
        const yt      = 'https://www.youtube.com/@VGK4YOU';
        const lead    = this.currentLead || {};
        const tcName  = lead.telecaller_name || 'Our Team';
        const tcCode  = lead.telecaller_code || '';
        const regards = `— Team VGK4U | 📞 +91 858585 2738 | 🌐 vgk4u.com/hargharsolar${tcName && tcName !== 'Our Team' ? '\n👤 Your Advisor: ' + tcName + (tcCode ? ' (Ext: ' + tcCode + ')' : '') : ''}`;

        const _waChannels = `\n\n📢 *Stay Connected — Join our WhatsApp Channels:*\n💚 VGK4U: https://whatsapp.com/channel/0029Vb7Vb5f9cDDXf3zWtf0m\n🔵 Myntreal: https://whatsapp.com/channel/0029VbCmSCh2kNFiA0RsHZ2r\n☀️ Har Ghar Solar: https://whatsapp.com/channel/0029Vb7V0ImFCCoYg891FL3D`;
        const _about    = `\n\n📖 *About VGK4U:* https://vgk4u.com/voffers`;
        const _portal   = 'https://vgk4u.com/vgk/login';

        const buildMsg = (lang) => {
            if (lang === 'hindi') {
                if (isNew && pwd)
                    return `🎉 *बधाई हो ${name} जी! VGK4U में आपका स्वागत है!* 🎉\n\nआपका VGK4U Partner account बन गया है! 🚀\n\n🔐 *लॉगिन विवरण:*\n🌐 Portal: ${_portal}\n👤 Username: ${code}\n🔑 Password: ${pwd}\n📞 Phone: ${phone ? '0' + phone.slice(-10) : '-'}\n📌 आपका VGK4U ID: ${code}\n\n🎁 *10,000 Welcome Bonus Points* आपके खाते में जमा हो गए हैं!\n\n🔗 *आपका Referral Link:*\n${ref}${_about}\n\n▶️ YouTube:\n${yt}${_waChannels}\n\n${regards}`;
                return `🙏 नमस्ते ${name} जी!\n\n✅ आपका VGK4U खाता विवरण:\n🌐 Portal: ${_portal}\n👤 VGK ID: ${code}\n💰 Points Balance: ${pts} pts\n\n🔗 *आपका Referral Link:*\n${ref}${_about}\n\n▶️ YouTube:\n${yt}${_waChannels}\n\n${regards}`;
            }
            if (lang === 'telugu') {
                if (isNew && pwd)
                    return `🎉 *అభినందనలు ${name} గారు! VGK4U లో స్వాగతం!* 🎉\n\nమీ VGK4U Partner account సిద్ధంగా ఉంది! 🚀\n\n🔐 *లాగిన్ వివరాలు:*\n🌐 Portal: ${_portal}\n👤 Username: ${code}\n🔑 Password: ${pwd}\n📞 Phone: ${phone ? '0' + phone.slice(-10) : '-'}\n📌 మీ VGK4U ID: ${code}\n\n🎁 *10,000 Welcome Points* మీ ఖాతాలో జమ అయ్యాయి!\n\n🔗 *మీ Referral Link:*\n${ref}${_about}\n\n▶️ YouTube:\n${yt}${_waChannels}\n\n${regards}`;
                return `🙏 నమస్కారం ${name} గారు!\n\n✅ మీ VGK4U వివరాలు:\n🌐 Portal: ${_portal}\n👤 VGK ID: ${code}\n💰 Points: ${pts} pts\n\n🔗 *మీ Referral Link:*\n${ref}${_about}\n\n▶️ YouTube:\n${yt}${_waChannels}\n\n${regards}`;
            }
            // English (default)
            if (isNew && pwd)
                return `🎉 *Congratulations ${name}! Welcome to VGK4U!* 🎉\n\nYour VGK4U Partner account has been created! 🚀\n\n🔐 *Login Credentials:*\n🌐 Portal: ${_portal}\n👤 Username: ${code}\n🔑 Password: ${pwd}\n📞 Phone: ${phone ? '0' + phone.slice(-10) : '-'}\n📌 Your VGK4U ID: ${code}\n\n🎁 *10,000 Welcome Bonus Points* credited to your account!\n\n🔗 *Your Referral Link:*\n${ref}${_about}\n\n▶️ Watch how to earn (YouTube):\n${yt}${_waChannels}\n\n${regards}`;
            return `👋 Hello ${name}!\n\n✅ Your VGK4U account details:\n🌐 Portal: ${_portal}\n👤 VGK ID: ${code}\n💰 Points Balance: ${pts} pts\n\n🔗 *Your Referral Link:*\n${ref}${_about}\n\n▶️ Learn how to earn commissions:\n${yt}${_waChannels}\n\n${regards}`;
        };

        const overlay = document.createElement('div');
        overlay.id = 'ule_vgkShareOverlay';
        overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:199999;display:flex;align-items:center;justify-content:center;padding:1rem';
        overlay.innerHTML = `
            <div style="background:#fff;border-radius:16px;padding:22px;max-width:460px;width:100%;box-shadow:0 25px 50px rgba(0,0,0,.25);max-height:92vh;overflow-y:auto">
                <div style="text-align:center;margin-bottom:14px">
                    <div style="font-size:28px">${isNew ? '🎉' : '📋'}</div>
                    <h5 style="font-weight:800;color:#4c1d95;margin:6px 0 4px">${isNew ? 'VGK4U Account Created!' : 'VGK4U Member Details'}</h5>
                    <p style="font-size:12px;color:#6b7280;margin:0">Share credentials via WhatsApp</p>
                </div>
                <div style="background:#f5f3ff;border:1.5px solid #ddd6fe;border-radius:10px;padding:12px 16px;margin-bottom:12px">
                    <div style="display:flex;justify-content:space-between;margin-bottom:4px"><span style="font-size:12px;color:#6b7280">Name</span><strong style="font-size:13px">${this._esc(name)}</strong></div>
                    <div style="display:flex;justify-content:space-between;margin-bottom:4px"><span style="font-size:12px;color:#6b7280">VGK4U ID</span><strong style="font-size:13px;color:#7c3aed">${this._esc(code)}</strong></div>
                    ${pwd ? `<div style="display:flex;justify-content:space-between;margin-bottom:4px"><span style="font-size:12px;color:#6b7280">Password</span><strong style="font-size:13px;color:#059669;font-family:monospace">${this._esc(pwd)}</strong></div>` : ''}
                    <div style="display:flex;justify-content:space-between;margin-bottom:4px"><span style="font-size:12px;color:#6b7280">Points</span><strong style="font-size:13px;color:#7c3aed">${pts}</strong></div>
                </div>
                <div style="margin-bottom:10px">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;flex-wrap:wrap;gap:6px">
                        <label style="font-size:12px;font-weight:700;color:#374151">Share Message</label>
                        <select id="ule_vgkShareLang" onchange="window.crmLeadEditor._updateVgkShareMsg()" style="font-size:12px;border:1px solid #ddd;border-radius:6px;padding:3px 8px">
                            <option value="english">English</option>
                            <option value="hindi">हिंदी</option>
                            <option value="telugu">తెలుగు</option>
                        </select>
                    </div>
                    <textarea id="ule_vgkShareMsg" rows="9" style="width:100%;font-size:13px;border:1.5px solid #ddd6fe;border-radius:8px;padding:10px;resize:vertical;font-family:inherit;line-height:1.55"></textarea>
                </div>
                <div style="display:flex;gap:8px;flex-wrap:wrap">
                    <button onclick="window.crmLeadEditor._copyVgkShareMsg()" style="flex:1;min-width:90px;padding:10px;border:1.5px solid #7c3aed;background:#fff;color:#7c3aed;border-radius:10px;font-weight:700;font-size:13px;cursor:pointer"><i class="fas fa-copy me-1"></i>Copy</button>
                    <button onclick="window.crmLeadEditor._crmVgkWaShare('${phone}', ${leadId}, ${companyId})" style="flex:1;min-width:90px;padding:10px;background:#25D366;color:#fff;border:none;border-radius:10px;font-weight:700;font-size:13px;cursor:pointer"><i class="fab fa-whatsapp me-1"></i>WhatsApp</button>
                    <button onclick="document.getElementById('ule_vgkShareOverlay').remove()" style="padding:10px 16px;background:#f3f4f6;color:#374151;border:none;border-radius:10px;font-weight:700;font-size:13px;cursor:pointer">Close</button>
                </div>
            </div>`;
        document.body.appendChild(overlay);
        overlay._buildMsg = buildMsg;
        document.getElementById('ule_vgkShareMsg').value = buildMsg('english');
    }

    _updateVgkShareMsg() {
        const lang = document.getElementById('ule_vgkShareLang')?.value || 'english';
        const overlay = document.getElementById('ule_vgkShareOverlay');
        if (overlay && overlay._buildMsg) {
            const ta = document.getElementById('ule_vgkShareMsg');
            if (ta) ta.value = overlay._buildMsg(lang);
        }
    }

    _copyVgkShareMsg() {
        const msg = document.getElementById('ule_vgkShareMsg')?.value || '';
        if (navigator.clipboard) {
            navigator.clipboard.writeText(msg).then(() => {
                const btn = event.target.closest('button');
                const orig = btn.innerHTML;
                btn.innerHTML = '<i class="fas fa-check me-1"></i>Copied!';
                setTimeout(() => { btn.innerHTML = orig; }, 2000);
            });
        } else { prompt('Copy:', msg); }
    }

    async _crmVgkWaShare(phone, leadId, companyId) {
        const msg = document.getElementById('ule_vgkShareMsg')?.value || '';
        const ph = (phone || '').replace(/\D/g, '');
        const phoneFormatted = ph.length === 10 ? '91' + ph : ph;
        const url = phoneFormatted
            ? 'https://wa.me/' + phoneFormatted + '?text=' + encodeURIComponent(msg)
            : 'https://wa.me/?text=' + encodeURIComponent(msg);
        window.open(url, '_blank');
        // Log WA share click for dashboard tracking
        try {
            await fetch(`/api/v1/crm/leads/${leadId}/log-whatsapp-share?company_id=${companyId}&share_type=vgk_creds`, {
                method: 'POST', ...this.authOptions
            });
        } catch(e) {}
    }

    _esc(str) {
        return String(str || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
    }
}

window.CRMLeadEditor = CRMLeadEditor;
console.log('[DC-CRM-EDITOR] CRM Lead Editor component loaded');
