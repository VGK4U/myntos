import{d as w,b as l,r as $}from"./services-AEce4KDH.js";import{p as k,P as h,M as L}from"./components-9q5I9H7Z.js";class R{container;user=null;data=null;loading=!0;constructor(e){this.container=e}async init(){const e=w.getAuthState();this.user=e.user,k.setUser(this.user),this.render(),await this.loadDashboard()}async loadDashboard(){this.loading=!0,this.updateContent();try{const e=await l.get("/partner/dashboard/stats");e.success&&e.data&&(this.data=e.data)}catch(e){console.error("[PartnerDashboard] Failed to load:",e)}this.loading=!1,this.updateContent()}render(){const e=this.user?.name||this.user?.partner_name||"Partner",t=this.user?.partner_code||this.user?.partner_id||"PARTNER",a=this.user?.partner_type||this.user?.type||"Official Partner",i=e.split(" ").map(o=>o[0]).join("").toUpperCase().slice(0,2);this.container.innerHTML=`
      <style>
        .partner-page { background: linear-gradient(135deg, #0a1929 0%, #0d2137 100%); min-height: 100vh; }
        .partner-header {
          background: linear-gradient(135deg, #1e88e5 0%, #1565c0 100%);
          padding: 16px;
          display: flex;
          align-items: center;
          gap: 12px;
        }
        .partner-hamburger {
          background: rgba(255, 255, 255, 0.15);
          border: none;
          border-radius: 8px;
          padding: 10px;
          color: white;
          cursor: pointer;
        }
        .partner-hamburger:active { background: rgba(255, 255, 255, 0.25); }
        .partner-header-info { flex: 1; display: flex; align-items: center; gap: 12px; }
        .partner-header-avatar {
          width: 44px;
          height: 44px;
          border-radius: 50%;
          background: rgba(255, 255, 255, 0.2);
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: 600;
          font-size: 16px;
          color: white;
          border: 2px solid rgba(255, 255, 255, 0.3);
        }
        .partner-header-text { display: flex; flex-direction: column; }
        .partner-header-name { font-size: 16px; font-weight: 600; color: white; }
        .partner-header-code {
          font-size: 11px;
          color: rgba(255, 255, 255, 0.9);
          background: rgba(255, 255, 255, 0.15);
          padding: 2px 8px;
          border-radius: 4px;
          margin-top: 2px;
          display: inline-block;
        }
        .partner-header-type { font-size: 10px; color: rgba(255, 255, 255, 0.7); margin-top: 2px; }
        .partner-logout-btn {
          background: rgba(255, 255, 255, 0.15);
          border: none;
          border-radius: 8px;
          padding: 10px;
          color: white;
          cursor: pointer;
        }
        .partner-content { padding: 16px; }
        .partner-service-banner {
          background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
          border-radius: 12px;
          padding: 16px;
          margin-bottom: 16px;
          color: white;
          display: flex;
          align-items: center;
          gap: 12px;
          cursor: pointer;
        }
        .partner-service-banner:active { opacity: 0.9; }
        .partner-service-icon {
          width: 48px;
          height: 48px;
          border-radius: 12px;
          background: rgba(255, 255, 255, 0.2);
          display: flex;
          align-items: center;
          justify-content: center;
        }
        .partner-service-text { flex: 1; }
        .partner-service-text h3 { margin: 0 0 4px; font-size: 16px; }
        .partner-service-text p { margin: 0; font-size: 12px; opacity: 0.9; }
        .partner-revenue-card {
          background: linear-gradient(135deg, #1f2937 0%, #374151 100%);
          border-radius: 12px;
          padding: 20px;
          margin-bottom: 16px;
          border: 1px solid rgba(255, 255, 255, 0.1);
        }
        .partner-revenue-row { display: flex; justify-content: space-between; align-items: center; }
        .partner-revenue-label { font-size: 12px; color: #9ca3af; margin-bottom: 4px; }
        .partner-revenue-amount { font-size: 28px; font-weight: 700; color: #10b981; }
        .partner-revenue-pending { font-size: 13px; color: #fbbf24; }
        .partner-stats-grid {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 12px;
          margin-bottom: 16px;
        }
        .partner-stat-card {
          background: linear-gradient(135deg, #1f2937 0%, #374151 100%);
          border-radius: 12px;
          padding: 16px;
          text-align: center;
          border: 1px solid rgba(255, 255, 255, 0.1);
          cursor: pointer;
        }
        .partner-stat-card:active { opacity: 0.9; }
        .partner-stat-value { font-size: 32px; font-weight: 700; color: #10b981; }
        .partner-stat-label { font-size: 12px; color: #9ca3af; margin-top: 4px; }
        .partner-quick-title { font-size: 14px; font-weight: 600; color: #e0e0e0; margin: 0 0 12px; }
        .partner-quick-grid {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 10px;
          margin-bottom: 16px;
        }
        .partner-quick-btn {
          background: #1f2937;
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 10px;
          padding: 14px;
          display: flex;
          align-items: center;
          gap: 10px;
          color: #e0e0e0;
          font-size: 13px;
          cursor: pointer;
        }
        .partner-quick-btn:active { background: #374151; }
        .partner-quick-btn svg { color: #64b5f6; }
        .partner-menu-list { display: flex; flex-direction: column; gap: 8px; }
        .partner-menu-item {
          background: #1f2937;
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 10px;
          padding: 14px 16px;
          display: flex;
          align-items: center;
          gap: 12px;
          color: #e0e0e0;
          font-size: 14px;
          cursor: pointer;
        }
        .partner-menu-item:active { background: #374151; }
        .partner-menu-item svg { color: #64b5f6; }
        .partner-menu-item .chevron { margin-left: auto; color: #6b7280; }
        .loading-state { text-align: center; padding: 40px; color: #8892b0; }
      </style>

      <div class="partner-page">
        <header class="partner-header">
          <button class="partner-hamburger" id="partnerHamburgerBtn">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/>
            </svg>
          </button>
          <div class="partner-header-info">
            <div class="partner-header-avatar">${i}</div>
            <div class="partner-header-text">
              <span class="partner-header-name">${e}</span>
              <span class="partner-header-code">${t}</span>
              <span class="partner-header-type">${a}</span>
            </div>
          </div>
          <button class="partner-logout-btn" id="partnerLogoutBtn">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
              <polyline points="16 17 21 12 16 7"/>
              <line x1="21" y1="12" x2="9" y2="12"/>
            </svg>
          </button>
        </header>

        <div class="partner-content" id="dashboardContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
    `,this.attachListeners()}attachListeners(){document.getElementById("partnerHamburgerBtn")?.addEventListener("click",()=>{k.open()}),document.getElementById("partnerLogoutBtn")?.addEventListener("click",async()=>{confirm("Are you sure you want to logout?")&&(await w.logout(),window.dispatchEvent(new CustomEvent("logout")))})}updateContent(){const e=document.getElementById("dashboardContent");if(!e)return;if(this.loading){e.innerHTML='<div class="loading-state">Loading...</div>';return}const t=this.data||{total_orders:0,pending_orders:0,completed_orders:0,total_revenue:0,pending_payments:0,total_leads:0};e.innerHTML=`
      <div class="partner-service-banner" data-page="partner-service">
        <div class="partner-service-icon">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2">
            <path d="M3 18v-6a9 9 0 0 1 18 0v6"/><path d="M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3zM3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3z"/>
          </svg>
        </div>
        <div class="partner-service-text">
          <h3>Service Request</h3>
          <p>Raise a new ticket or view existing requests</p>
        </div>
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2">
          <polyline points="9 18 15 12 9 6"/>
        </svg>
      </div>

      <div class="partner-revenue-card">
        <div class="partner-revenue-row">
          <div>
            <div class="partner-revenue-label">Total Revenue</div>
            <div class="partner-revenue-amount">₹${t.total_revenue.toLocaleString()}</div>
          </div>
          <div style="text-align: right;">
            <div class="partner-revenue-pending">Pending: ₹${t.pending_payments.toLocaleString()}</div>
          </div>
        </div>
      </div>

      <div class="partner-stats-grid">
        <div class="partner-stat-card" data-page="partner-orders">
          <div class="partner-stat-value">${t.total_orders}</div>
          <div class="partner-stat-label">Total Orders</div>
        </div>
        <div class="partner-stat-card" data-page="partner-orders">
          <div class="partner-stat-value">${t.pending_orders}</div>
          <div class="partner-stat-label">Pending</div>
        </div>
        <div class="partner-stat-card" data-page="partner-orders">
          <div class="partner-stat-value">${t.completed_orders}</div>
          <div class="partner-stat-label">Completed</div>
        </div>
        <div class="partner-stat-card" data-page="partner-leads">
          <div class="partner-stat-value">${t.total_leads}</div>
          <div class="partner-stat-label">Leads</div>
        </div>
      </div>

      <h4 class="partner-quick-title">Quick Actions</h4>
      <div class="partner-quick-grid">
        <button class="partner-quick-btn" data-page="partner-orders">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="16.5" y1="9.4" x2="7.5" y2="4.21"/><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
          </svg>
          Orders
        </button>
        <button class="partner-quick-btn" data-page="partner-invoices">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>
          </svg>
          Invoices
        </button>
        <button class="partner-quick-btn" data-page="partner-payments">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
          </svg>
          Payments
        </button>
        <button class="partner-quick-btn" data-page="partner-leads">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
          </svg>
          Leads
        </button>
      </div>

      <div class="partner-menu-list">
        <button class="partner-menu-item" data-page="partner-raise-ticket">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/>
          </svg>
          <span>Raise New Ticket</span>
          <svg class="chevron" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="9 18 15 12 9 6"/>
          </svg>
        </button>
        <button class="partner-menu-item" data-page="partner-revenue">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>
          </svg>
          <span>Revenue Dashboard</span>
          <svg class="chevron" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="9 18 15 12 9 6"/>
          </svg>
        </button>
        <button class="partner-menu-item" data-page="partner-kyc-documents">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>
          </svg>
          <span>KYC &amp; Documents</span>
          <svg class="chevron" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="9 18 15 12 9 6"/>
          </svg>
        </button>
        <button class="partner-menu-item" data-page="partner-profile">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
          </svg>
          <span>My Profile</span>
          <svg class="chevron" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="9 18 15 12 9 6"/>
          </svg>
        </button>
      </div>
    `,e.querySelectorAll("[data-page]").forEach(a=>{a.addEventListener("click",()=>{const i=a.getAttribute("data-page");i&&$.navigate(i)})})}}class F{container;orders=[];pendingInvoices=[];loading=!0;pendingLoading=!1;pendingLoaded=!1;filter="all";activeTab="orders";constructor(e){this.container=e}async init(){this.render(),await this.loadOrders()}async loadOrders(){this.loading=!0,this.updateContent();try{const e=await l.get("/partner/orders");e.success&&e.data&&(this.orders=e.data.orders||[])}catch(e){console.error("[PartnerOrders] Failed to load:",e)}this.loading=!1,this.updateContent()}async loadPendingDelivery(){this.pendingLoading=!0,this.updateContent();try{const e=await l.get("/partner/pending-dispatch");e.success&&e.data&&(this.pendingInvoices=e.data.invoices||[])}catch(e){console.error("[PartnerOrders] Pending delivery load failed:",e)}this.pendingLoading=!1,this.pendingLoaded=!0,this.updateContent()}render(){this.container.innerHTML=`
      <div class="page-container">
        ${h.render({title:"My Orders",showBack:!0})}
        <div id="pageContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
    `,h.attachListeners({title:"My Orders",showBack:!0})}updateContent(){const e=document.getElementById("pageContent");if(!e)return;const t=`
      <div style="display:flex;border-bottom:2px solid rgba(255,255,255,0.1);margin-bottom:14px">
        <button id="tabOrders" style="flex:1;padding:10px;background:none;border:none;border-bottom:3px solid ${this.activeTab==="orders"?"#10b981":"transparent"};color:${this.activeTab==="orders"?"#10b981":"#8892b0"};font-size:13px;font-weight:600;cursor:pointer;margin-bottom:-2px"><i class="fas fa-file-alt" style="margin-right:4px"></i>My Orders</button>
        <button id="tabPending" style="flex:1;padding:10px;background:none;border:none;border-bottom:3px solid ${this.activeTab==="pending"?"#10b981":"transparent"};color:${this.activeTab==="pending"?"#10b981":"#8892b0"};font-size:13px;font-weight:600;cursor:pointer;margin-bottom:-2px"><i class="fas fa-truck" style="margin-right:4px"></i>Pending Delivery</button>
      </div>`;if(this.activeTab==="orders")if(this.loading)e.innerHTML=t+'<div class="loading-state">Loading orders...</div>';else{const a=`
          <div style="display:flex;gap:8px;margin-bottom:12px;padding:0 2px">
            ${["all","pending","completed"].map(r=>`
              <button data-filter="${r}" style="flex:1;padding:6px 4px;border-radius:8px;border:1px solid ${this.filter===r?"#10b981":"rgba(255,255,255,0.12)"};background:${this.filter===r?"rgba(16,185,129,0.15)":"transparent"};color:${this.filter===r?"#10b981":"#8892b0"};font-size:12px;font-weight:600;cursor:pointer;text-transform:capitalize">${r}</button>`).join("")}
          </div>`;let i=this.orders;this.filter==="pending"?i=this.orders.filter(r=>r.status.toLowerCase()!=="completed"):this.filter==="completed"&&(i=this.orders.filter(r=>r.status.toLowerCase()==="completed"));const o=i.length===0?'<div class="empty-state">No orders found</div>':`<div class="list-container">${i.map(r=>`
              <div class="list-item card order-card">
                <div class="item-header">
                  <span class="order-number">${r.order_number}</span>
                  <span class="status-badge ${r.status.toLowerCase()}">${r.status}</span>
                </div>
                <div class="order-details">
                  <h4 class="customer-name">${r.customer_name}</h4>
                  <p class="product-info">${r.product} x ${r.quantity}</p>
                </div>
                <div class="order-footer">
                  <span class="order-amount">₹${r.amount.toLocaleString()}</span>
                  <span class="order-date">${this.formatDate(r.order_date)}</span>
                </div>
              </div>`).join("")}
            </div>`;e.innerHTML=t+a+o,e.querySelectorAll("[data-filter]").forEach(r=>{r.addEventListener("click",()=>{this.filter=r.getAttribute("data-filter"),this.updateContent()})})}else if(this.pendingLoading)e.innerHTML=t+'<div class="loading-state">Loading pending deliveries...</div>';else if(this.pendingInvoices.length===0)e.innerHTML=t+`
          <div class="empty-state">
            <div style="font-size:2rem;margin-bottom:12px">🚚</div>
            <strong>No Pending Deliveries</strong>
            <p style="margin-top:8px;font-size:13px;color:#8892b0">All dispatches are up to date.</p>
          </div>`;else{const a=this.pendingInvoices.map(i=>`
          <div style="background:rgba(22,33,62,0.9);border-radius:10px;padding:14px;margin-bottom:12px;border:1px solid rgba(255,255,255,0.08)">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;flex-wrap:wrap;gap:6px">
              <span style="font-weight:700;color:#64d2ff">${i.invoice_number}</span>
              <span style="font-size:10px;padding:2px 8px;border-radius:10px;background:rgba(245,158,11,0.15);color:#f59e0b">${(i.dispatch_status||"").replace(/_/g," ")}</span>
            </div>
            <div style="font-size:11px;color:#8892b0;margin-bottom:10px">${i.company_code||i.company_name||"—"}${i.invoice_date?" · "+this.formatDate(i.invoice_date):""}</div>
            <table style="width:100%;border-collapse:collapse;font-size:11px">
              <thead>
                <tr style="color:#6b7280;text-transform:uppercase">
                  <th style="padding:4px 6px;text-align:left;font-weight:600;border-bottom:1px solid rgba(255,255,255,0.08)">Item</th>
                  <th style="padding:4px 6px;text-align:right;font-weight:600;border-bottom:1px solid rgba(255,255,255,0.08)">Invoiced</th>
                  <th style="padding:4px 6px;text-align:right;font-weight:600;border-bottom:1px solid rgba(255,255,255,0.08)">Done</th>
                  <th style="padding:4px 6px;text-align:right;color:#ef4444;font-weight:600;border-bottom:1px solid rgba(255,255,255,0.08)">Pending</th>
                </tr>
              </thead>
              <tbody>
                ${i.items.map(o=>`
                  <tr>
                    <td style="padding:5px 6px;color:#e6f1ff;border-bottom:1px solid rgba(255,255,255,0.04)">${o.item_description}<br><small style="color:#8892b0">${o.item_code||""} ${o.unit_of_measure||""}</small></td>
                    <td style="padding:5px 6px;text-align:right;color:#8892b0;border-bottom:1px solid rgba(255,255,255,0.04)">${o.invoiced_qty}</td>
                    <td style="padding:5px 6px;text-align:right;color:#10b981;border-bottom:1px solid rgba(255,255,255,0.04)">${o.dispatched_qty}</td>
                    <td style="padding:5px 6px;text-align:right;font-weight:700;color:#ef4444;border-bottom:1px solid rgba(255,255,255,0.04)">${o.remaining_qty}</td>
                  </tr>`).join("")}
              </tbody>
            </table>
          </div>`).join("");e.innerHTML=t+`
          <div style="margin-bottom:10px;font-size:12px;color:#8892b0">${this.pendingInvoices.length} invoice${this.pendingInvoices.length===1?"":"s"} with pending items</div>
          ${a}`}e.querySelector("#tabOrders")?.addEventListener("click",()=>{this.activeTab="orders",this.updateContent()}),e.querySelector("#tabPending")?.addEventListener("click",()=>{this.activeTab="pending",!this.pendingLoaded&&!this.pendingLoading?this.loadPendingDelivery():this.updateContent()})}formatDate(e){return e?new Date(e).toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"numeric"}):"—"}}class H{container;invoices=[];sfmsInvoices=[];loading=!0;sfmsLoading=!1;sfmsLoaded=!1;activeTab="invoices";constructor(e){this.container=e}async init(){this.render(),await this.loadInvoices()}async loadInvoices(){this.loading=!0,this.updateContent();try{const e=await l.get("/partner/invoices");e.success&&e.data&&(this.invoices=e.data.invoices||[])}catch(e){console.error("[PartnerInvoices] Failed to load:",e)}this.loading=!1,this.updateContent()}async loadSfmsInvoices(){this.sfmsLoading=!0,this.updateContent();try{const e=await l.get("/partner/sfms-invoices?per_page=50");e.success&&e.data&&(this.sfmsInvoices=e.data.data||[])}catch(e){console.error("[PartnerInvoices] SFMS load failed:",e)}this.sfmsLoading=!1,this.sfmsLoaded=!0,this.updateContent()}render(){this.container.innerHTML=`
      <div class="page-container">
        ${h.render({title:"Invoices",showBack:!0})}
        <div id="pageContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
    `,h.attachListeners({title:"Invoices",showBack:!0})}updateContent(){const e=document.getElementById("pageContent");if(!e)return;if(this.loading){e.innerHTML='<div class="loading-state">Loading...</div>';return}const t=`
      <div style="display:flex;border-bottom:2px solid rgba(255,255,255,0.1);margin-bottom:14px">
        <button id="tabInvoices" style="flex:1;padding:10px;background:none;border:none;border-bottom:3px solid ${this.activeTab==="invoices"?"#10b981":"transparent"};color:${this.activeTab==="invoices"?"#10b981":"#8892b0"};font-size:13px;font-weight:600;cursor:pointer;margin-bottom:-2px">Order Invoices</button>
        <button id="tabSfms" style="flex:1;padding:10px;background:none;border:none;border-bottom:3px solid ${this.activeTab==="sfms"?"#10b981":"transparent"};color:${this.activeTab==="sfms"?"#10b981":"#8892b0"};font-size:13px;font-weight:600;cursor:pointer;margin-bottom:-2px">Company Invoices</button>
      </div>`;if(this.activeTab==="invoices"){const a=this.invoices.reduce((o,r)=>o+r.total_amount,0),i=this.invoices.filter(o=>o.status!=="Paid").reduce((o,r)=>o+r.total_amount,0);e.innerHTML=t+(this.invoices.length===0?'<div class="empty-state">No invoices found</div>':`
        <div class="invoice-summary card">
          <div class="summary-row">
            <div class="summary-item"><span class="value">₹${a.toLocaleString()}</span><span class="label">Total Invoiced</span></div>
            <div class="summary-item"><span class="value">₹${i.toLocaleString()}</span><span class="label">Pending</span></div>
          </div>
        </div>
        <div class="list-container">
          ${this.invoices.map(o=>`
            <div class="list-item card invoice-card">
              <div class="item-header">
                <span class="invoice-number">${o.invoice_number}</span>
                <span class="status-badge ${o.status.toLowerCase()}">${o.status}</span>
              </div>
              <div class="invoice-details">
                <p class="customer-name">${o.customer_name}</p>
                <div class="amount-breakdown"><span>Amount: ₹${o.amount.toLocaleString()}</span><span>GST: ₹${o.gst_amount.toLocaleString()}</span></div>
              </div>
              <div class="invoice-footer">
                <span class="total-amount">Total: ₹${o.total_amount.toLocaleString()}</span>
                <span class="invoice-date">${this.formatDate(o.invoice_date)}</span>
              </div>
            </div>`).join("")}
        </div>`)}else this.sfmsLoading?e.innerHTML=t+'<div class="loading-state">Loading company invoices...</div>':this.sfmsInvoices.length===0?e.innerHTML=t+'<div class="empty-state">No company invoices linked to your account.</div>':e.innerHTML=t+`
          <div class="list-container">
            ${this.sfmsInvoices.map(a=>`
              <div class="list-item card" style="background:rgba(22,33,62,0.9);border-radius:10px;padding:14px;margin-bottom:10px;border:1px solid rgba(255,255,255,0.08)">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
                  <span style="font-weight:700;color:#64d2ff">${a.invoice_number}</span>
                  <span style="font-size:10px;padding:2px 8px;border-radius:10px;background:rgba(16,185,129,0.15);color:#10b981">${a.payment_status}</span>
                </div>
                <div style="font-size:12px;color:#8892b0;margin-bottom:6px">${a.company_name||a.company_code||"—"} · ${this.formatDate(a.invoice_date)}</div>
                <div style="display:flex;justify-content:space-between;font-size:13px">
                  <span style="color:#e6f1ff">Total: ₹${a.grand_total.toLocaleString()}</span>
                  <span style="color:${a.balance_due>0?"#ef4444":"#10b981"}">Due: ₹${a.balance_due.toLocaleString()}</span>
                </div>
                <div style="font-size:11px;color:#8892b0;margin-top:6px">${(a.dispatch_status||"").replace(/_/g," ")}</div>
              </div>`).join("")}
          </div>`;document.getElementById("tabInvoices")?.addEventListener("click",()=>{this.activeTab="invoices",this.updateContent()}),document.getElementById("tabSfms")?.addEventListener("click",()=>{this.activeTab="sfms",!this.sfmsLoaded&&!this.sfmsLoading?this.loadSfmsInvoices():this.updateContent()})}formatDate(e){return e?new Date(e).toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"numeric"}):"—"}}class j{container;data=null;loading=!0;constructor(e){this.container=e}async init(){this.render(),await this.loadRevenue()}async loadRevenue(){this.loading=!0,this.updateContent();try{const e=await l.get("/partner/revenue-dashboard");e.success&&e.data&&(this.data=e.data)}catch(e){console.error("[PartnerRevenue] Failed to load:",e)}this.loading=!1,this.updateContent()}render(){this.container.innerHTML=`
      <div class="page-container">
        ${h.render({title:"Revenue Dashboard",showBack:!0})}
        
        <div id="pageContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
    `,h.attachListeners({title:"Revenue Dashboard",showBack:!0})}updateContent(){const e=document.getElementById("pageContent");if(!e)return;if(this.loading){e.innerHTML='<div class="loading-state">Loading...</div>';return}const t=this.data||{total_revenue:0,this_month:0,last_month:0,growth_percentage:0,pending_payments:0,received_payments:0,monthly_breakdown:[]},a=t.growth_percentage>=0?"var(--success)":"var(--danger)",i=t.growth_percentage>=0?"↑":"↓";e.innerHTML=`
      <div class="revenue-overview card">
        <div class="total-revenue">
          <span class="label">Total Revenue</span>
          <span class="amount">₹${t.total_revenue.toLocaleString()}</span>
        </div>
        <div class="growth-indicator" style="color: ${a}">
          ${i} ${Math.abs(t.growth_percentage)}% vs last month
        </div>
      </div>

      <div class="stats-grid">
        <div class="card stat-card">
          <p class="stat-value">₹${t.this_month.toLocaleString()}</p>
          <p class="stat-label">This Month</p>
        </div>
        <div class="card stat-card">
          <p class="stat-value">₹${t.last_month.toLocaleString()}</p>
          <p class="stat-label">Last Month</p>
        </div>
        <div class="card stat-card success">
          <p class="stat-value">₹${t.received_payments.toLocaleString()}</p>
          <p class="stat-label">Received</p>
        </div>
        <div class="card stat-card warning">
          <p class="stat-value">₹${t.pending_payments.toLocaleString()}</p>
          <p class="stat-label">Pending</p>
        </div>
      </div>

      <div class="monthly-breakdown card">
        <h3 class="card-title">Monthly Breakdown</h3>
        <div class="breakdown-list">
          ${t.monthly_breakdown.length===0?'<p class="empty-text">No data available</p>':t.monthly_breakdown.map(o=>`
              <div class="breakdown-item">
                <span class="month">${o.month}</span>
                <span class="amount">₹${o.amount.toLocaleString()}</span>
              </div>
            `).join("")}
        </div>
      </div>
    `}}class O{container;tickets=[];customerSpares=[];loading=!0;sparesLoading=!1;sparesLoaded=!1;statusFilter="";activeTab="tickets";constructor(e){this.container=e}async init(){this.render(),await this.loadTickets()}async loadTickets(){this.loading=!0,this.updateContent();try{const e=new URLSearchParams;this.statusFilter&&e.append("status",this.statusFilter);const t=await l.get(`/tickets/my-tickets?${e}`);t.success&&t.data&&(this.tickets=(t.data.tickets||t.data||[]).map(a=>({id:a.id,ticket_number:a.ticket_number||`TKT-${a.id}`,subject:a.subject||a.title||"-",category:a.category||"General",priority:a.priority||"Normal",status:a.status||"Open",created_at:a.created_at||"",updated_at:a.updated_at||""})))}catch(e){console.error("[PartnerServiceTickets] Failed to load:",e)}this.loading=!1,this.updateContent()}render(){this.container.innerHTML=`
      <style>
        ${L.getStyles()}
        .service-page { padding: 16px; background: #0d1b2a; min-height: 100vh; }
        .raise-ticket-btn {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 10px;
          width: 100%;
          padding: 16px;
          background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
          border: none;
          border-radius: 12px;
          color: white;
          font-size: 15px;
          font-weight: 600;
          cursor: pointer;
          margin-bottom: 16px;
        }
        .raise-ticket-btn:active { opacity: 0.9; }
        .stats-row {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 10px;
          margin-bottom: 16px;
        }
        .stat-card {
          background: rgba(22, 33, 62, 0.9);
          border-radius: 10px;
          padding: 14px;
          text-align: center;
          border: 1px solid rgba(255, 255, 255, 0.1);
        }
        .stat-value { font-size: 24px; font-weight: 700; color: #10b981; }
        .stat-label { font-size: 11px; color: #8892b0; margin-top: 4px; }
        .stat-card.open .stat-value { color: #fbbf24; }
        .stat-card.closed .stat-value { color: #10b981; }
        .filter-section {
          background: rgba(22, 33, 62, 0.8);
          border-radius: 10px;
          padding: 14px;
          margin-bottom: 16px;
        }
        .filter-section label { display: block; font-size: 11px; color: #8892b0; margin-bottom: 6px; }
        .filter-section select {
          width: 100%;
          padding: 10px;
          border-radius: 6px;
          border: 1px solid rgba(255, 255, 255, 0.1);
          background: rgba(13, 27, 42, 0.8);
          color: #e6f1ff;
          font-size: 13px;
        }
        .table-header {
          background: linear-gradient(135deg, #1e88e5 0%, #1565c0 100%);
          padding: 12px 14px;
          border-radius: 8px 8px 0 0;
        }
        .table-header h5 { margin: 0; color: white; font-size: 13px; }
        .badge { padding: 4px 8px; border-radius: 4px; font-size: 10px; font-weight: 600; }
        .badge-open { background: #fbbf24; color: #451a03; }
        .badge-in-progress { background: #3b82f6; color: white; }
        .badge-resolved { background: #10b981; color: white; }
        .badge-closed { background: #6b7280; color: white; }
        .badge-high { background: #ef4444; color: white; }
        .badge-normal { background: #3b82f6; color: white; }
        .badge-low { background: #6b7280; color: white; }
        .loading-state { text-align: center; padding: 40px; color: #8892b0; }
        .empty-state { text-align: center; padding: 40px; color: #8892b0; }
      </style>
      ${h.render({title:"Service Tickets",showBack:!0})}
      <div class="service-page" id="pageContent">
        <div class="loading-state">Loading...</div>
      </div>
    `,h.attachListeners({title:"Service Tickets",showBack:!0})}updateContent(){const e=document.getElementById("pageContent");if(!e)return;if(this.loading){e.innerHTML='<div class="loading-state">Loading tickets...</div>';return}const t=`
      <div style="display:flex;border-bottom:2px solid rgba(255,255,255,0.1);margin-bottom:14px">
        <button id="tabTickets" style="flex:1;padding:10px;background:none;border:none;border-bottom:3px solid ${this.activeTab==="tickets"?"#10b981":"transparent"};color:${this.activeTab==="tickets"?"#10b981":"#8892b0"};font-size:13px;font-weight:600;cursor:pointer;margin-bottom:-2px">My Tickets</button>
        <button id="tabSpares" style="flex:1;padding:10px;background:none;border:none;border-bottom:3px solid ${this.activeTab==="spares"?"#10b981":"transparent"};color:${this.activeTab==="spares"?"#10b981":"#8892b0"};font-size:13px;font-weight:600;cursor:pointer;margin-bottom:-2px">Customer Spares</button>
      </div>`;if(this.activeTab==="tickets"){const a=this.tickets.filter(n=>n.status.toLowerCase()==="open").length,i=this.tickets.filter(n=>n.status.toLowerCase()==="in progress"||n.status.toLowerCase()==="in-progress").length,o=this.tickets.filter(n=>n.status.toLowerCase()==="closed"||n.status.toLowerCase()==="resolved").length,r=new L({columns:[{key:"ticket_number",label:"Ticket #",render:n=>`<span style="color: #64d2ff; font-weight: 600;">${n}</span>`},{key:"subject",label:"Subject"},{key:"category",label:"Category"},{key:"priority",label:"Priority",render:n=>this.getPriorityBadge(n)},{key:"status",label:"Status",render:n=>this.getStatusBadge(n)},{key:"created_at",label:"Created",render:n=>this.formatDate(n)}],data:this.tickets,emptyMessage:"No tickets found. Raise a new ticket to get started."});e.innerHTML=t+`
        <button class="raise-ticket-btn" id="raiseTicketBtn">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/>
          </svg>
          Raise New Ticket
        </button>

        <div class="stats-row">
          <div class="stat-card open"><div class="stat-value">${a}</div><div class="stat-label">Open</div></div>
          <div class="stat-card"><div class="stat-value" style="color:#3b82f6">${i}</div><div class="stat-label">In Progress</div></div>
          <div class="stat-card closed"><div class="stat-value">${o}</div><div class="stat-label">Closed</div></div>
        </div>

        <div class="filter-section">
          <label>Filter by Status</label>
          <select id="statusFilter">
            <option value="">All Tickets</option>
            <option value="open" ${this.statusFilter==="open"?"selected":""}>Open</option>
            <option value="in-progress" ${this.statusFilter==="in-progress"?"selected":""}>In Progress</option>
            <option value="resolved" ${this.statusFilter==="resolved"?"selected":""}>Resolved</option>
            <option value="closed" ${this.statusFilter==="closed"?"selected":""}>Closed</option>
          </select>
        </div>

        <div class="table-header"><h5>My Tickets</h5></div>
        ${r.render()}
      `}else if(this.sparesLoading)e.innerHTML=t+'<div class="loading-state">Loading customer spares...</div>';else if(this.customerSpares.length===0)e.innerHTML=t+'<div class="empty-state">No customer spare requests linked to your account.</div>';else{const a=new L({columns:[{key:"sub_ticket_number",label:"Sub-Ticket",render:i=>`<span style="color:#64d2ff;font-weight:600">${i||"—"}</span>`},{key:"spare_item_name",label:"Item"},{key:"spare_item_code",label:"Code"},{key:"quantity_required",label:"Qty"},{key:"customer_name",label:"Customer"},{key:"vehicle_model",label:"Vehicle"},{key:"status_label",label:"Status",render:i=>`<span style="font-size:10px;padding:2px 6px;border-radius:8px;background:rgba(16,185,129,0.15);color:#10b981">${i||"—"}</span>`},{key:"requested_at",label:"Date",render:i=>this.formatDate(i)}],data:this.customerSpares,emptyMessage:"No customer spare requests found."});e.innerHTML=t+`
          <div class="table-header"><h5>Customer Spare Requests</h5></div>
          ${a.render()}`}this.attachListeners()}async loadCustomerSpares(){this.sparesLoading=!0,this.updateContent();try{const e=await l.get("/partner/customer-spares?limit=50");e.success&&e.data&&(this.customerSpares=e.data.data||[])}catch(e){console.error("[PartnerServiceTickets] Customer spares load failed:",e)}this.sparesLoading=!1,this.sparesLoaded=!0,this.updateContent()}attachListeners(){document.getElementById("raiseTicketBtn")?.addEventListener("click",()=>{$.navigate("partner-raise-ticket")}),document.getElementById("statusFilter")?.addEventListener("change",e=>{this.statusFilter=e.target.value,this.loadTickets()}),document.getElementById("tabTickets")?.addEventListener("click",()=>{this.activeTab="tickets",this.updateContent()}),document.getElementById("tabSpares")?.addEventListener("click",()=>{this.activeTab="spares",!this.sparesLoaded&&!this.sparesLoading?this.loadCustomerSpares():this.updateContent()})}getStatusBadge(e){const t=e.toLowerCase();return t==="open"?'<span class="badge badge-open">Open</span>':t==="in progress"||t==="in-progress"?'<span class="badge badge-in-progress">In Progress</span>':t==="resolved"?'<span class="badge badge-resolved">Resolved</span>':t==="closed"?'<span class="badge badge-closed">Closed</span>':`<span class="badge">${e}</span>`}getPriorityBadge(e){const t=e.toLowerCase();return t==="high"||t==="urgent"?'<span class="badge badge-high">High</span>':t==="normal"||t==="medium"?'<span class="badge badge-normal">Normal</span>':t==="low"?'<span class="badge badge-low">Low</span>':`<span class="badge">${e}</span>`}formatDate(e){if(!e)return"-";try{return new Date(e).toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"numeric"})}catch{return e}}}class U{container;submitting=!1;user=null;constructor(e){this.container=e}async init(){const e=w.getAuthState();this.user=e.user,this.render()}render(){const e=this.user?.partner_name||this.user?.name||"Partner",t=this.user?.partner_code||"";this.container.innerHTML=`
      <style>
        .ticket-page {
          padding: 16px;
          padding-bottom: 100px;
          background: #0d1b2a;
          min-height: 100vh;
        }
        .section-card {
          background: rgba(22, 33, 62, 0.95);
          border-radius: 12px;
          margin-bottom: 16px;
          border: 1px solid rgba(255, 255, 255, 0.08);
          overflow: hidden;
        }
        .section-header {
          background: linear-gradient(135deg, rgba(30, 136, 229, 0.2) 0%, rgba(21, 101, 192, 0.15) 100%);
          padding: 14px 16px;
          display: flex;
          align-items: center;
          gap: 10px;
          border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        }
        .section-header svg { color: #64b5f6; }
        .section-header h3 {
          font-size: 14px;
          font-weight: 600;
          color: white;
          margin: 0;
        }
        .section-body { padding: 16px; }
        .form-group { margin-bottom: 16px; }
        .form-group:last-child { margin-bottom: 0; }
        .form-group label {
          display: block;
          font-size: 12px;
          color: #8892b0;
          margin-bottom: 6px;
          font-weight: 500;
        }
        .form-group label .required { color: #ef4444; }
        .form-group input, .form-group select, .form-group textarea {
          width: 100%;
          padding: 12px 14px;
          border-radius: 8px;
          border: 1px solid rgba(255, 255, 255, 0.12);
          background: rgba(13, 27, 42, 0.9);
          color: #e6f1ff;
          font-size: 14px;
          transition: border-color 0.2s;
        }
        .form-group input:focus, .form-group select:focus, .form-group textarea:focus {
          outline: none;
          border-color: #1e88e5;
        }
        .form-group input::placeholder, .form-group textarea::placeholder {
          color: rgba(255, 255, 255, 0.35);
        }
        .form-group textarea { min-height: 100px; resize: vertical; }
        .form-group input[readonly] {
          background: rgba(255, 255, 255, 0.05);
          color: #64b5f6;
          cursor: not-allowed;
        }
        .form-row {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 12px;
        }
        .ticket-type-selector {
          display: flex;
          gap: 12px;
        }
        .ticket-type-option {
          flex: 1;
          padding: 14px 12px;
          border: 2px solid rgba(255, 255, 255, 0.15);
          border-radius: 10px;
          text-align: center;
          cursor: pointer;
          transition: all 0.2s;
        }
        .ticket-type-option.selected {
          border-color: #1e88e5;
          background: rgba(30, 136, 229, 0.15);
        }
        .ticket-type-option .type-icon { font-size: 24px; margin-bottom: 6px; }
        .ticket-type-option .type-label {
          font-weight: 600;
          color: white;
          font-size: 13px;
        }
        .submit-btn {
          width: 100%;
          padding: 16px;
          background: linear-gradient(135deg, #10b981 0%, #059669 100%);
          border: none;
          border-radius: 10px;
          color: white;
          font-size: 16px;
          font-weight: 600;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 10px;
          margin-top: 8px;
          transition: all 0.2s;
        }
        .submit-btn:disabled { opacity: 0.6; cursor: not-allowed; }
        .submit-btn:active:not(:disabled) { transform: scale(0.98); }
        .partner-info-banner {
          background: linear-gradient(135deg, #1e88e5 0%, #1565c0 100%);
          border-radius: 10px;
          padding: 14px 16px;
          margin-bottom: 16px;
          display: flex;
          align-items: center;
          gap: 12px;
        }
        .partner-avatar {
          width: 44px;
          height: 44px;
          border-radius: 50%;
          background: rgba(255, 255, 255, 0.2);
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: 600;
          font-size: 16px;
          color: white;
        }
        .partner-details h4 {
          color: white;
          font-size: 15px;
          font-weight: 600;
          margin: 0 0 4px;
        }
        .partner-details span {
          font-size: 12px;
          color: rgba(255, 255, 255, 0.8);
          background: rgba(255, 255, 255, 0.15);
          padding: 2px 8px;
          border-radius: 4px;
        }
        .toast {
          position: fixed;
          bottom: 100px;
          left: 50%;
          transform: translateX(-50%);
          background: #10b981;
          color: white;
          padding: 14px 24px;
          border-radius: 10px;
          font-size: 14px;
          font-weight: 500;
          z-index: 9999;
          animation: fadeInOut 3s ease;
          box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        }
        .toast.error { background: #ef4444; }
        @keyframes fadeInOut {
          0%, 100% { opacity: 0; transform: translateX(-50%) translateY(10px); }
          10%, 90% { opacity: 1; transform: translateX(-50%) translateY(0); }
        }
      </style>
      ${h.render({title:"Create Service Ticket",showBack:!0})}
      <div class="ticket-page">
        <!-- Partner Info Banner -->
        <div class="partner-info-banner">
          <div class="partner-avatar">${e.charAt(0).toUpperCase()}</div>
          <div class="partner-details">
            <h4>${e}</h4>
            <span>${t}</span>
          </div>
        </div>

        <!-- Customer Information -->
        <div class="section-card">
          <div class="section-header">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
              <circle cx="12" cy="7" r="4"/>
            </svg>
            <h3>Customer Information</h3>
          </div>
          <div class="section-body">
            <div class="form-row">
              <div class="form-group">
                <label>Customer Name <span class="required">*</span></label>
                <input type="text" id="customerName" placeholder="Full name" required />
              </div>
              <div class="form-group">
                <label>Phone <span class="required">*</span></label>
                <input type="tel" id="customerPhone" placeholder="10-digit number" required />
              </div>
            </div>
            <div class="form-group">
              <label>Email</label>
              <input type="email" id="customerEmail" placeholder="email@example.com" />
            </div>
            <div class="form-group">
              <label>Address</label>
              <textarea id="customerAddress" rows="2" placeholder="Customer address (optional)"></textarea>
            </div>
          </div>
        </div>

        <!-- Request Type -->
        <div class="section-card">
          <div class="section-header">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>
            </svg>
            <h3>Request Type</h3>
          </div>
          <div class="section-body">
            <div class="ticket-type-selector">
              <div class="ticket-type-option selected" data-type="technical">
                <div class="type-icon">🔧</div>
                <div class="type-label">Technical</div>
              </div>
              <div class="ticket-type-option" data-type="spares">
                <div class="type-icon">🔩</div>
                <div class="type-label">Spare Parts</div>
              </div>
            </div>
          </div>
        </div>

        <!-- Issue Details -->
        <div class="section-card">
          <div class="section-header">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="8" x2="12" y2="12"/>
              <line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            <h3>Issue Details</h3>
          </div>
          <div class="section-body">
            <div class="form-row">
              <div class="form-group">
                <label>Category <span class="required">*</span></label>
                <select id="issueCategory" required>
                  <option value="">Select Category</option>
                  <option value="EV Battery Issue">EV Battery Issue</option>
                  <option value="Motor/Controller Problem">Motor/Controller</option>
                  <option value="Charging Issue">Charging Issue</option>
                  <option value="Display/Electronics">Display/Electronics</option>
                  <option value="Brake/Suspension">Brake/Suspension</option>
                  <option value="Body/Frame Damage">Body/Frame Damage</option>
                  <option value="Warranty Claim">Warranty Claim</option>
                  <option value="General Service">General Service</option>
                  <option value="Other">Other</option>
                </select>
              </div>
              <div class="form-group">
                <label>Priority <span class="required">*</span></label>
                <select id="priority" required>
                  <option value="Medium">Medium</option>
                  <option value="Low">Low</option>
                  <option value="High">High</option>
                  <option value="Critical">Critical</option>
                </select>
              </div>
            </div>
            <div class="form-group">
              <label>Issue Description <span class="required">*</span></label>
              <textarea id="issueDescription" rows="4" placeholder="Describe the issue in detail..." required></textarea>
            </div>
          </div>
        </div>

        <!-- Product Information (Optional) -->
        <div class="section-card">
          <div class="section-header">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="1" y="3" width="15" height="13"/>
              <polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/>
              <circle cx="5.5" cy="18.5" r="2.5"/>
              <circle cx="18.5" cy="18.5" r="2.5"/>
            </svg>
            <h3>Product Information (Optional)</h3>
          </div>
          <div class="section-body">
            <div class="form-group">
              <label>Product Name</label>
              <input type="text" id="productName" placeholder="e.g., Electric Scooter Pro" />
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>Serial Number</label>
                <input type="text" id="productSerial" placeholder="EV2024001234" />
              </div>
              <div class="form-group">
                <label>Model</label>
                <input type="text" id="productModel" placeholder="Model name" />
              </div>
            </div>
            <div class="form-group">
              <label>Warranty Status</label>
              <select id="warrantyStatus">
                <option value="">Select...</option>
                <option value="under_warranty">Under Warranty</option>
                <option value="out_of_warranty">Out of Warranty</option>
                <option value="amc">AMC</option>
              </select>
            </div>
          </div>
        </div>

        <button class="submit-btn" id="submitTicketBtn">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="22" y1="2" x2="11" y2="13"/>
            <polygon points="22 2 15 22 11 13 2 9 22 2"/>
          </svg>
          Submit Service Ticket
        </button>
      </div>
    `,h.attachListeners({title:"Create Service Ticket",showBack:!0}),this.attachListeners()}attachListeners(){document.querySelectorAll(".ticket-type-option").forEach(e=>{e.addEventListener("click",()=>{document.querySelectorAll(".ticket-type-option").forEach(t=>t.classList.remove("selected")),e.classList.add("selected")})}),document.getElementById("submitTicketBtn")?.addEventListener("click",()=>this.submitTicket())}async submitTicket(){if(this.submitting)return;const e=document.getElementById("customerName")?.value.trim(),t=document.getElementById("customerPhone")?.value.trim(),a=document.getElementById("customerEmail")?.value.trim(),i=document.getElementById("customerAddress")?.value.trim(),o=document.getElementById("issueCategory")?.value,r=document.getElementById("priority")?.value,n=document.getElementById("issueDescription")?.value.trim(),s=document.getElementById("productName")?.value.trim(),d=document.getElementById("productSerial")?.value.trim(),b=document.getElementById("productModel")?.value.trim(),u=document.getElementById("warrantyStatus")?.value,v=document.querySelector(".ticket-type-option.selected")?.dataset.type||"technical";if(!e||e.length<2){this.showToast("Please enter customer name (min 2 characters)",!0);return}if(!t||t.length<10){this.showToast("Please enter a valid phone number",!0);return}if(!o){this.showToast("Please select an issue category",!0);return}if(!n||n.length<10){this.showToast("Please describe the issue (min 10 characters)",!0);return}this.submitting=!0;const g=document.getElementById("submitTicketBtn");g&&(g.disabled=!0,g.innerHTML=`
        <svg class="spinner" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10" stroke-dasharray="60" stroke-dashoffset="20"/>
        </svg>
        Submitting...
      `);try{const p=await l.post("/tickets/service/partner/create",{customer_name:e,customer_phone:t,customer_email:a||null,customer_address:i||null,issue_category:o,issue_description:n,ticket_type:v,priority:r,product_name:s||null,product_serial:d||null,product_model:b||null,warranty_status:u||null});if(p.success||p.data?.success){const f=p.data?.ticket_id||"Created";this.showToast(`Ticket ${f} created successfully!`),setTimeout(()=>{$.navigate("partner-service")},1500)}else this.showToast(p.error||p.data?.detail||"Failed to create ticket",!0)}catch(p){console.error("[PartnerRaiseTicket] Submit error:",p),this.showToast(p.message||"Failed to create ticket",!0)}this.submitting=!1,g&&(g.disabled=!1,g.innerHTML=`
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="22" y1="2" x2="11" y2="13"/>
          <polygon points="22 2 15 22 11 13 2 9 22 2"/>
        </svg>
        Submit Service Ticket
      `)}showToast(e,t=!1){const a=document.querySelector(".toast");a&&a.remove();const i=document.createElement("div");i.className=`toast ${t?"error":""}`,i.textContent=e,document.body.appendChild(i),setTimeout(()=>i.remove(),3e3)}}const P=["new","contacted","qualified","converted","lost"];class W{container;user=null;leads=[];loading=!0;selectedStatus="all";dateFilter="";roleFilter="";constructor(e){this.container=e}async init(){const e=w.getAuthState();this.user=e.user,k.setUser(this.user),this.render(),await this.loadLeads()}async loadLeads(){this.loading=!0,this.updateContent();try{const e=new URLSearchParams;e.append("role","partner"),this.dateFilter&&e.append("quick_filter",this.dateFilter),this.roleFilter&&e.append("role_filter",this.roleFilter);const t=await l.get(`/crm/unified-my-leads?${e.toString()}`);t.success&&t.data&&(this.leads=t.data.leads||t.data||[])}catch(e){console.error("[PartnerLeads] Failed to load:",e)}this.loading=!1,this.updateContent()}async lookupPincode(e){const t=e.value.trim();if(!(!t||t.length!==6))try{const i=await(await fetch(`https://api.postalpincode.in/pincode/${t}`)).json();if(i[0]?.Status==="Success"&&i[0]?.PostOffice?.length>0){const o=i[0].PostOffice[0],r=document.getElementById("leadArea"),n=document.getElementById("leadCity"),s=document.getElementById("leadState");r&&(r.value=o.Name||""),n&&(n.value=o.District||""),s&&(s.value=o.State||"")}}catch(a){console.error("[PartnerLeads] Pincode lookup failed:",a)}}render(){const e=this.user?.name||this.user?.partner_name||"Partner",t=e.split(" ").map(a=>a[0]).join("").toUpperCase().slice(0,2);this.container.innerHTML=`
      <style>
        .partner-leads-page { background: linear-gradient(135deg, #0a1929 0%, #0d2137 100%); min-height: 100vh; }
        .partner-header {
          background: linear-gradient(135deg, #1e88e5 0%, #1565c0 100%);
          padding: 16px;
          display: flex;
          align-items: center;
          gap: 12px;
        }
        .partner-hamburger {
          background: rgba(255, 255, 255, 0.15);
          border: none;
          border-radius: 8px;
          padding: 10px;
          color: white;
          cursor: pointer;
        }
        .partner-header-info { flex: 1; display: flex; align-items: center; gap: 12px; }
        .partner-header-avatar {
          width: 44px; height: 44px; border-radius: 50%;
          background: rgba(255, 255, 255, 0.2);
          display: flex; align-items: center; justify-content: center;
          font-weight: 600; font-size: 16px; color: white;
          border: 2px solid rgba(255, 255, 255, 0.3);
        }
        .partner-header-text { display: flex; flex-direction: column; }
        .partner-header-name { font-size: 16px; font-weight: 600; color: white; }
        .partner-header-role { font-size: 12px; color: rgba(255, 255, 255, 0.8); }
        .add-lead-btn {
          background: rgba(255, 255, 255, 0.2);
          border: none; border-radius: 10px;
          padding: 10px 16px; color: white;
          font-weight: 600; cursor: pointer;
          display: flex; align-items: center; gap: 6px;
        }
        .leads-content { padding: 16px; }
        .status-tabs {
          display: flex; gap: 8px; overflow-x: auto;
          padding-bottom: 16px; margin-bottom: 16px;
          -webkit-overflow-scrolling: touch;
        }
        .status-tab {
          padding: 10px 16px; border-radius: 20px;
          background: rgba(255, 255, 255, 0.08);
          color: #a8c0d8; font-size: 13px; font-weight: 500;
          border: none; cursor: pointer; white-space: nowrap;
          transition: all 0.2s;
        }
        .status-tab.active {
          background: linear-gradient(135deg, #10b981 0%, #047857 100%);
          color: white;
        }
        .leads-list { display: flex; flex-direction: column; gap: 12px; }
        .lead-card {
          background: rgba(255, 255, 255, 0.06);
          border-radius: 16px; padding: 16px;
          border: 1px solid rgba(255, 255, 255, 0.08);
          cursor: pointer;
        }
        .lead-card-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }
        .lead-name { font-size: 16px; font-weight: 600; color: #e6f1ff; }
        .lead-contact-row { display: flex; align-items: center; gap: 8px; margin-top: 4px; }
        .lead-phone-link { color: #1e88e5; font-size: 14px; text-decoration: none; }
        .lead-phone-link:hover { text-decoration: underline; }
        .whatsapp-link { color: #25d366; font-size: 16px; text-decoration: none; }
        .lead-status {
          padding: 4px 10px; border-radius: 12px;
          font-size: 11px; font-weight: 600; text-transform: uppercase;
        }
        .lead-status.new { background: rgba(59, 130, 246, 0.2); color: #60a5fa; }
        .lead-status.contacted { background: rgba(245, 158, 11, 0.2); color: #fbbf24; }
        .lead-status.qualified { background: rgba(16, 185, 129, 0.2); color: #34d399; }
        .lead-status.converted { background: rgba(139, 92, 246, 0.2); color: #a78bfa; }
        .lead-status.lost { background: rgba(239, 68, 68, 0.2); color: #f87171; }
        .lead-meta { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; font-size: 12px; color: #7a9cc6; margin-bottom: 12px; }
        .meta-item { background: rgba(255,255,255,0.05); padding: 3px 8px; border-radius: 6px; }
        .priority-badge { padding: 2px 8px; border-radius: 6px; font-size: 11px; font-weight: 600; }
        .priority-badge.high { background: rgba(239, 68, 68, 0.2); color: #ef4444; }
        .priority-badge.medium { background: rgba(251, 191, 36, 0.2); color: #fbbf24; }
        .priority-badge.low { background: rgba(107, 114, 128, 0.2); color: #9ca3af; }
        .lead-actions { display: flex; gap: 8px; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 12px; }
        .action-btn { flex: 1; display: flex; align-items: center; justify-content: center; padding: 10px 8px; border-radius: 8px; font-size: 16px; text-decoration: none; border: none; cursor: pointer; background: rgba(255,255,255,0.05); }
        .action-btn.call { color: #10b981; }
        .action-btn.whatsapp { color: #25d366; }
        .action-btn.view { color: #60a5fa; }
        .action-btn.edit { color: #fbbf24; }
        .filter-row { display: flex; gap: 8px; margin: 12px 0; }
        .filter-select { flex: 1; padding: 10px 12px; background: rgba(30, 58, 95, 0.6); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; color: #e6f1ff; font-size: 13px; }
        .filter-select option { background: #1a2744; color: #e6f1ff; }
        .empty-state {
          text-align: center; padding: 60px 20px;
          color: #7a9cc6;
        }
        .empty-icon { font-size: 48px; margin-bottom: 16px; opacity: 0.5; }
        .loading-state { text-align: center; padding: 60px 20px; color: #7a9cc6; }
      </style>

      <div class="partner-leads-page">
        <div class="partner-header">
          <button class="partner-hamburger" id="menuBtn">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M3 12h18M3 6h18M3 18h18"/>
            </svg>
          </button>
          <div class="partner-header-info">
            <div class="partner-header-avatar">${t}</div>
            <div class="partner-header-text">
              <div class="partner-header-name">My Leads</div>
              <div class="partner-header-role">${e}</div>
            </div>
          </div>
          <button class="add-lead-btn" id="addLeadBtn">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 5v14M5 12h14"/>
            </svg>
            Add
          </button>
        </div>

        <div class="leads-content">
          <div class="status-tabs">
            <button class="status-tab active" data-status="all">All</button>
            ${P.map(a=>`<button class="status-tab" data-status="${a}">${a.charAt(0).toUpperCase()+a.slice(1)}</button>`).join("")}
          </div>
          <div class="filter-row">
            <select id="dateFilter" class="filter-select">
              <option value="">All Leads</option>
              <option value="today" ${this.dateFilter==="today"?"selected":""}>Today's Leads</option>
              <option value="overdue" ${this.dateFilter==="overdue"?"selected":""}>Overdue</option>
              <option value="followup_today" ${this.dateFilter==="followup_today"?"selected":""}>Follow-up Today</option>
              <option value="this_week" ${this.dateFilter==="this_week"?"selected":""}>This Week</option>
              <option value="future" ${this.dateFilter==="future"?"selected":""}>Future Leads</option>
            </select>
            <select id="roleFilter" class="filter-select">
              <option value="">All Roles</option>
              <option value="primary_holder" ${this.roleFilter==="primary_holder"?"selected":""}>As Primary Holder</option>
              <option value="handler" ${this.roleFilter==="handler"?"selected":""}>As Handler</option>
            </select>
          </div>
          <div class="leads-list" id="leadsList"></div>
        </div>
      </div>
    `,this.attachEventListeners(),this.updateContent()}attachEventListeners(){document.getElementById("menuBtn")?.addEventListener("click",()=>k.toggle()),document.getElementById("addLeadBtn")?.addEventListener("click",()=>this.showAddLeadModal()),document.querySelectorAll(".status-tab").forEach(a=>{a.addEventListener("click",i=>{document.querySelectorAll(".status-tab").forEach(o=>o.classList.remove("active")),i.target.classList.add("active"),this.selectedStatus=i.target.dataset.status||"all",this.updateContent()})});const e=document.getElementById("dateFilter");e&&e.addEventListener("change",()=>{this.dateFilter=e.value,this.loadLeads()});const t=document.getElementById("roleFilter");t&&t.addEventListener("change",()=>{this.roleFilter=t.value,this.loadLeads()})}updateContent(){const e=document.getElementById("leadsList");if(!e)return;if(this.loading){e.innerHTML='<div class="loading-state">Loading leads...</div>';return}const t=this.selectedStatus==="all"?this.leads:this.leads.filter(a=>a.status===this.selectedStatus);if(t.length===0){e.innerHTML=`
        <div class="empty-state">
          <div class="empty-icon">📋</div>
          <div>No leads found</div>
          <button class="add-lead-btn" id="addLeadEmpty" style="margin-top: 16px;">+ Add Lead</button>
        </div>
      `,document.getElementById("addLeadEmpty")?.addEventListener("click",()=>this.showAddLeadModal());return}e.innerHTML=t.map(a=>`
      <div class="lead-card" data-id="${a.id}">
        <div class="lead-card-header">
          <div>
            <div class="lead-name">${a.name}</div>
            <div class="lead-contact-row">
              <a href="tel:${a.phone||""}" class="lead-phone-link" onclick="event.stopPropagation()">${a.phone||"No phone"}</a>
              ${a.phone?`<a href="https://wa.me/91${(a.phone||"").replace(/\D/g,"")}" class="whatsapp-link" target="_blank" onclick="event.stopPropagation()">💬</a>`:""}
            </div>
          </div>
          <span class="lead-status ${a.status}">${a.status}</span>
        </div>
        <div class="lead-meta">
          <span class="meta-item">${a.category_name||"General"}</span>
          <span class="priority-badge ${a.priority?.toLowerCase()||"medium"}">${a.priority||"Medium"}</span>
          <span class="meta-item">${new Date(a.created_at).toLocaleDateString()}</span>
          ${a.submit_date?`<span class="meta-item" style="font-size:10px;color:#6b7280">📤 ${new Date(a.submit_date).toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"numeric"})}</span>`:""}
          ${a.complete_date?`<span class="meta-item" style="font-size:10px;color:#059669">✅ ${new Date(a.complete_date).toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"numeric"})}</span>`:""}
        </div>
        <div class="lead-actions">
          <a href="tel:${a.phone||""}" class="action-btn call" onclick="event.stopPropagation()">📞</a>
          <a href="https://wa.me/91${(a.phone||"").replace(/\D/g,"")}" class="action-btn whatsapp" target="_blank" onclick="event.stopPropagation()">💬</a>
          <button class="action-btn view" data-action="view" data-id="${a.id}">👁</button>
          <button class="action-btn edit" data-action="edit" data-id="${a.id}">✏️</button>
        </div>
      </div>
    `).join("")}showAddLeadModal(){const e=document.createElement("div");e.id="addLeadModal",e.innerHTML=`
      <style>
        #addLeadModal {
          position: fixed; top: 0; left: 0; right: 0; bottom: 0;
          background: rgba(0, 0, 0, 0.7); backdrop-filter: blur(4px);
          display: flex; align-items: center; justify-content: center;
          z-index: 9999; padding: 16px;
        }
        #addLeadModal .modal-content {
          max-height: 90vh; width: 100%; max-width: 420px;
          background: linear-gradient(180deg, #1e3a5f 0%, #0d1b2a 100%);
          border-radius: 20px; padding: 0; display: flex; flex-direction: column;
          box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
        }
        #addLeadModal .modal-header {
          background: linear-gradient(135deg, #1e88e5 0%, #1565c0 100%);
          padding: 20px 24px; border-radius: 20px 20px 0 0;
          display: flex; justify-content: space-between; align-items: center;
        }
        #addLeadModal .modal-header h3 { margin: 0; color: white; font-size: 20px; font-weight: 700; }
        #addLeadModal .modal-close {
          background: rgba(255, 255, 255, 0.2); border: none; color: white;
          width: 36px; height: 36px; border-radius: 10px; font-size: 22px; cursor: pointer;
        }
        #addLeadModal .modal-body { padding: 24px; overflow-y: auto; flex: 1; max-height: calc(90vh - 180px); }
        #addLeadModal .form-section { margin-bottom: 20px; }
        #addLeadModal .section-title {
          font-size: 12px; font-weight: 600; color: #1e88e5;
          text-transform: uppercase; letter-spacing: 1px;
          margin-bottom: 12px; padding-bottom: 8px;
          border-bottom: 1px solid rgba(30, 136, 229, 0.2);
        }
        #addLeadModal .form-group { margin-bottom: 16px; }
        #addLeadModal .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
        #addLeadModal label {
          display: block; color: #a8c0d8; font-size: 13px;
          font-weight: 500; margin-bottom: 8px;
        }
        #addLeadModal .required { color: #f87171; }
        #addLeadModal input, #addLeadModal select, #addLeadModal textarea {
          width: 100%; padding: 14px 16px; border-radius: 12px;
          border: 2px solid rgba(255, 255, 255, 0.08);
          background: rgba(13, 27, 42, 0.6); color: #e6f1ff;
          font-size: 15px; box-sizing: border-box;
        }
        #addLeadModal input:focus, #addLeadModal select:focus, #addLeadModal textarea:focus {
          border-color: #1e88e5; outline: none;
        }
        #addLeadModal .checkbox-row { display: flex; align-items: center; gap: 8px; margin-top: 8px; }
        #addLeadModal .checkbox-row input[type="checkbox"] { width: 18px; height: 18px; accent-color: #1e88e5; }
        #addLeadModal .checkbox-row label { margin-bottom: 0; font-size: 13px; }
        #addLeadModal .modal-footer {
          padding: 20px 24px; border-top: 1px solid rgba(255, 255, 255, 0.08);
          display: flex; gap: 12px; background: rgba(13, 27, 42, 0.5);
          border-radius: 0 0 20px 20px;
        }
        #addLeadModal .btn-cancel {
          flex: 1; padding: 16px 20px; background: rgba(255, 255, 255, 0.08);
          border: 2px solid rgba(255, 255, 255, 0.15); color: #a8c0d8;
          border-radius: 12px; font-size: 15px; font-weight: 600; cursor: pointer;
        }
        #addLeadModal .btn-submit {
          flex: 1.5; padding: 16px 20px;
          background: linear-gradient(135deg, #1e88e5 0%, #1565c0 100%);
          border: none; color: white; border-radius: 12px;
          font-size: 15px; font-weight: 700; cursor: pointer;
          box-shadow: 0 4px 15px rgba(30, 136, 229, 0.35);
        }
      </style>
      <div class="modal-content">
        <div class="modal-header">
          <h3>Add New Lead</h3>
          <button class="modal-close">&times;</button>
        </div>
        <div class="modal-body">
          <div class="form-section">
            <div class="section-title">Basic Information</div>
            <div class="form-group">
              <label>Name <span class="required">*</span></label>
              <input type="text" id="leadName" placeholder="Full name" required>
            </div>
            <div class="form-group">
              <label>Email</label>
              <input type="email" id="leadEmail" placeholder="email@example.com">
            </div>
          </div>

          <div class="form-section">
            <div class="section-title">Contact Details</div>
            <div class="form-group">
              <label>Mobile Number <span class="required">*</span></label>
              <input type="tel" id="leadMobile" placeholder="10-digit mobile number" required maxlength="10" inputmode="numeric">
              <div class="checkbox-row">
                <input type="checkbox" id="leadPhoneWhatsapp" checked>
                <label for="leadPhoneWhatsapp">WhatsApp Available</label>
              </div>
            </div>
            <div class="form-group">
              <label>Alternate Mobile</label>
              <input type="tel" id="leadMobileSecondary" placeholder="Alternate number" maxlength="10" inputmode="numeric">
              <div class="checkbox-row">
                <input type="checkbox" id="leadPhoneSecondaryWhatsapp">
                <label for="leadPhoneSecondaryWhatsapp">WhatsApp Available</label>
              </div>
            </div>
          </div>

          <div class="form-section">
            <div class="section-title">Lead Classification</div>
            <div class="form-row">
              <div class="form-group">
                <label>Category</label>
                <select id="leadCategory">
                  <option value="">Select category...</option>
                  <option value="1">EV</option>
                  <option value="2">Real Estate</option>
                  <option value="3">Insurance</option>
                  <option value="4">Franchise</option>
                  <option value="5">Solar</option>
                  <option value="6">General</option>
                </select>
              </div>
              <div class="form-group">
                <label>Priority</label>
                <select id="leadPriority">
                  <option value="medium">Normal</option>
                  <option value="high">High</option>
                  <option value="low">Low</option>
                </select>
              </div>
            </div>
            <div class="form-group">
              <label>Lead Source</label>
              <select id="leadSource">
                <option value="">Select source...</option>
                <option value="referral">Referral</option>
                <option value="website">Website</option>
                <option value="social_media">Social Media</option>
                <option value="whatsapp">WhatsApp</option>
                <option value="direct">Direct</option>
                <option value="event">Event</option>
                <option value="other">Other</option>
              </select>
            </div>
          </div>

          <div class="form-section">
            <div class="section-title">Requirements & Budget</div>
            <div class="form-group">
              <label>Looking For</label>
              <input type="text" id="leadLookingFor" placeholder="What is the lead looking for?">
            </div>
            <div class="form-group">
              <label>Requirements</label>
              <textarea id="leadRequirements" placeholder="Detailed requirements..." rows="2"></textarea>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>Budget Min</label>
                <input type="number" id="leadBudgetMin" placeholder="Min budget" inputmode="numeric">
              </div>
              <div class="form-group">
                <label>Budget Max</label>
                <input type="number" id="leadBudgetMax" placeholder="Max budget" inputmode="numeric">
              </div>
            </div>
          </div>

          <div class="form-section">
            <div class="section-title">Location Details</div>
            <div class="form-group">
              <label>Address</label>
              <input type="text" id="leadAddress" placeholder="Street address">
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>Area</label>
                <input type="text" id="leadArea" placeholder="Area/Locality">
              </div>
              <div class="form-group">
                <label>City</label>
                <input type="text" id="leadCity" placeholder="City">
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>State</label>
                <input type="text" id="leadState" placeholder="State">
              </div>
              <div class="form-group">
                <label>Pincode</label>
                <input type="text" id="leadPincode" placeholder="PIN code" maxlength="6" inputmode="numeric">
              </div>
            </div>
          </div>

          <div class="form-section">
            <div class="section-title">Follow-up & Notes</div>
            <div class="form-row">
              <div class="form-group">
                <label>Expected Close Date</label>
                <input type="date" id="leadExpectedCloseDate">
              </div>
              <div class="form-group">
                <label>Next Follow-up</label>
                <input type="date" id="leadNextFollowupDate">
              </div>
            </div>
            <div class="form-group">
              <label>Tags</label>
              <input type="text" id="leadTags" placeholder="Comma separated tags">
            </div>
            <div class="form-group">
              <label>Notes</label>
              <textarea id="leadNotes" placeholder="Additional notes..." rows="3"></textarea>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-cancel" id="btnCancelLead">Cancel</button>
          <button class="btn-submit" id="btnSaveLead">Create Lead</button>
        </div>
      </div>
    `,document.body.appendChild(e),e.querySelector(".modal-close")?.addEventListener("click",()=>e.remove()),e.querySelector("#btnCancelLead")?.addEventListener("click",()=>e.remove()),e.querySelector("#btnSaveLead")?.addEventListener("click",()=>this.saveLead(e)),e.addEventListener("click",a=>{a.target===e&&e.remove()});const t=document.getElementById("leadPincode");t&&t.addEventListener("input",()=>{t.value.length===6&&this.lookupPincode(t)})}async saveLead(e){const t=document.getElementById("leadName")?.value?.trim(),a=document.getElementById("leadMobile")?.value?.trim(),i=document.getElementById("leadEmail")?.value?.trim(),o=document.getElementById("leadCategory")?.value,r=document.getElementById("leadPriority")?.value,n=document.getElementById("leadNotes")?.value?.trim(),s=document.getElementById("leadSource")?.value,d=document.getElementById("leadMobileSecondary")?.value?.trim(),b=document.getElementById("leadAddress")?.value?.trim(),u=document.getElementById("leadPhoneWhatsapp")?.checked,m=document.getElementById("leadPhoneSecondaryWhatsapp")?.checked,v=document.getElementById("leadRequirements")?.value?.trim(),g=document.getElementById("leadLookingFor")?.value?.trim(),p=document.getElementById("leadBudgetMin")?.value,f=document.getElementById("leadBudgetMax")?.value,S=document.getElementById("leadArea")?.value?.trim(),B=document.getElementById("leadCity")?.value?.trim(),E=document.getElementById("leadState")?.value?.trim(),I=document.getElementById("leadPincode")?.value?.trim(),T=document.getElementById("leadExpectedCloseDate")?.value,z=document.getElementById("leadNextFollowupDate")?.value,M=document.getElementById("leadTags")?.value?.trim();if(!t||!a){alert("Please enter name and mobile number");return}if(a.length!==10||!/^\d{10}$/.test(a)){alert("Please enter a valid 10-digit mobile number");return}const x=document.getElementById("btnSaveLead");x&&(x.disabled=!0,x.textContent="Creating...");try{const y={name:t,phone:a,email:i||null,category_id:o?parseInt(o):null,priority:r||"medium",status:"new",description:n||null,source:s||"partner_app",phone_primary_whatsapp:u||!1,alternate_phone:d||null,phone_secondary_whatsapp:m||!1,address:b||null,requirements:v||null,looking_for:g||null,budget_min:p?parseFloat(p):null,budget_max:f?parseFloat(f):null,area:S||null,city:B||null,state:E||null,pincode:I||null,expected_close_date:T||null,next_followup_date:z||null,tags:M||null},C=await l.post("/crm/unified-my-leads?role=partner",y);C.success?(e.remove(),alert("Lead added successfully!"),await this.loadLeads()):alert(C.error||"Failed to add lead")}catch(y){console.error("[PartnerLeads] Add lead failed:",y),alert(y.message||"Failed to add lead. Please try again.")}finally{x&&(x.disabled=!1,x.textContent="Create Lead")}}}class K{container;constructor(e){this.container=e}async init(){this.container.innerHTML=this.renderSkeleton();try{const e=localStorage.getItem("partner_token"),t=localStorage.getItem("partner_company_id")||"",a=l.getBaseUrl(),o=await(await fetch(`${a}/api/v1/partner/auth/me?company_id=${t}`,{headers:{Authorization:`Bearer ${e}`}})).json();o.success||o.partner_code?this.render(o.partner||o):this.renderError("Failed to load profile")}catch{this.renderError("Network error. Please try again.")}}renderSkeleton(){return`
      <div style="padding:20px">
        <div style="height:24px;background:#e5e7eb;border-radius:6px;width:40%;margin-bottom:20px"></div>
        ${Array(5).fill('<div style="height:16px;background:#f3f4f6;border-radius:4px;margin-bottom:12px"></div>').join("")}
      </div>`}render(e){const t=(a,i)=>i?`<div style="display:flex;gap:12px;padding:10px 0;border-bottom:1px solid #f3f4f6">
        <span style="font-size:12px;color:#6b7280;min-width:130px;font-weight:600">${a}</span>
        <span style="font-size:13px;color:#111827;font-weight:500">${i}</span>
      </div>`:"";this.container.innerHTML=`
      <div style="padding:20px;max-width:480px;margin:0 auto">
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:20px">
          <button onclick="window.routerService?.navigate('partner-dashboard')"
            style="background:none;border:none;color:#6b7280;cursor:pointer;padding:4px">
            <svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <polyline points="15 18 9 12 15 6"/>
            </svg>
          </button>
          <h2 style="margin:0;font-size:18px;font-weight:700;color:#111827">My Profile</h2>
        </div>

        <div style="background:#fff;border-radius:14px;padding:18px 20px;box-shadow:0 2px 8px rgba(0,0,0,.07);margin-bottom:16px">
          <div style="display:flex;align-items:center;gap:14px;margin-bottom:16px;padding-bottom:14px;border-bottom:2px solid #f3f4f6">
            <div style="width:52px;height:52px;border-radius:50%;background:linear-gradient(135deg,#1d4ed8,#7c3aed);display:flex;align-items:center;justify-content:center;color:#fff;font-size:20px;font-weight:800">
              ${(e.partner_name||e.contact_person||"P").charAt(0).toUpperCase()}
            </div>
            <div>
              <div style="font-size:16px;font-weight:700;color:#111827">${e.partner_name||"—"}</div>
              <div style="font-size:12px;color:#7c3aed;font-weight:600">${e.partner_code||""}</div>
            </div>
          </div>
          ${t("Contact Person",e.contact_person)}
          ${t("Phone",e.phone)}
          ${t("Email",e.email)}
          ${t("WhatsApp",e.whatsapp_number)}
          ${t("Category",e.category)}
          ${t("GST Number",e.gst_number)}
          ${t("PAN Number",e.pan_number)}
        </div>

        <div style="background:#fff;border-radius:14px;padding:18px 20px;box-shadow:0 2px 8px rgba(0,0,0,.07);margin-bottom:16px">
          <div style="font-size:13px;font-weight:700;color:#374151;margin-bottom:12px">Address</div>
          ${t("Address",e.address)}
          ${t("City",e.city)}
          ${t("State",e.state)}
          ${t("Pincode",e.pincode)}
        </div>

        <div style="background:#fff;border-radius:14px;padding:18px 20px;box-shadow:0 2px 8px rgba(0,0,0,.07)">
          <div style="font-size:13px;font-weight:700;color:#374151;margin-bottom:12px">Account</div>
          ${t("Status",e.login_status?e.login_status.toUpperCase():null)}
          ${t("Last Login",e.last_login?new Date(e.last_login).toLocaleString("en-IN"):null)}
          ${t("KYC Status",e.kyc_status)}
        </div>

        <div style="margin-top:20px;text-align:center">
          <button onclick="window.routerService?.navigate('partner-dashboard')"
            style="background:#1d4ed8;color:#fff;border:none;border-radius:10px;padding:12px 28px;font-size:14px;font-weight:600;cursor:pointer">
            Back to Dashboard
          </button>
        </div>
      </div>`}renderError(e){this.container.innerHTML=`
      <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:50vh;padding:24px;text-align:center">
        <svg width="48" height="48" fill="none" stroke="#ef4444" stroke-width="2" viewBox="0 0 24 24" style="margin-bottom:16px">
          <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>
        <p style="color:#6b7280;margin:0 0 16px">${e}</p>
        <button onclick="window.routerService?.navigate('partner-dashboard')"
          style="background:#1d4ed8;color:#fff;border:none;border-radius:8px;padding:10px 20px;font-size:13px;cursor:pointer">
          Back to Dashboard
        </button>
      </div>`}}const q={aadhar_front:{label:"Aadhaar — Front",icon:"🪪",color:"#3b82f6",bg:"rgba(59,130,246,.12)"},aadhar_back:{label:"Aadhaar — Back",icon:"🪪",color:"#8b5cf6",bg:"rgba(139,92,246,.12)"},pan_card:{label:"PAN Card",icon:"💳",color:"#f59e0b",bg:"rgba(245,158,11,.12)"},passport_photo:{label:"Passport Photo",icon:"📷",color:"#10b981",bg:"rgba(16,185,129,.12)"}};function _(c){return!c||c==="Not Submitted"?'<span style="background:#1f2937;color:#9ca3af;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:700">Not Submitted</span>':c==="Approved"?'<span style="background:#064e3b;color:#10b981;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:700">✓ Approved</span>':c==="Rejected"?'<span style="background:#450a0a;color:#ef4444;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:700">✗ Rejected</span>':`<span style="background:#451a03;color:#f59e0b;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:700">⏳ ${c}</span>`}class Y{container;constructor(e){this.container=e}async init(){this.container.innerHTML=this.renderSkeleton();try{const e=localStorage.getItem("partner_token")||"",t=localStorage.getItem("partner_company_id")||"",a=l.getBaseUrl(),i={Authorization:`Bearer ${e}`},[o,r,n]=await Promise.all([fetch(`${a}/api/v1/partner/auth/me?company_id=${t}`,{headers:i}),fetch(`${a}/api/v1/partner/auth/my-partnership`,{headers:i}),fetch(`${a}/api/v1/partner/kyc/status`,{headers:i})]);if(!o.ok)throw new Error("Unauthorized");const s=await o.json(),d=s.partner||s,b=r.ok?await r.json():{},u=b.partnership||{},v=(n.ok?await n.json():{}).kyc_documents||{},g=b.kyc_status||"Not Submitted";this.render(d,u,v,g)}catch{this.container.innerHTML=`
        <div style="padding:40px;text-align:center;color:#ef4444">
          <div style="font-size:32px;margin-bottom:12px">⚠️</div>
          <div style="font-size:14px">Failed to load. Please try again.</div>
          <button onclick="window.routerService?.navigate('partner-dashboard')"
            style="margin-top:16px;background:#1d4ed8;color:#fff;border:none;padding:10px 20px;border-radius:8px;font-size:13px;cursor:pointer">
            Back to Dashboard
          </button>
        </div>`}}renderSkeleton(){const e=(t,a="14px")=>`<div style="height:${a};background:#1e293b;border-radius:6px;width:${t};margin-bottom:10px"></div>`;return`<div style="padding:20px">${e("50%","24px")}${e("30%")}${Array(6).fill(e("100%","48px")).join("")}</div>`}render(e,t,a,i){const o=t.days_to_expiry;let r="";if(t.partner_end_date){let s="#064e3b",d="#10b981",b="✅";o!==null&&o<=0?(s="#450a0a",d="#ef4444",b="🔴"):o!==null&&o<=(t.reminder_days_before||90)&&(s="#451a03",d="#f59e0b",b="⚠️");const u=o===null?"":o<=0?`Expired ${Math.abs(o)} day(s) ago`:`${o} day(s) remaining`;r=`
        <div style="background:${s};border-radius:12px;padding:14px 16px;margin-bottom:14px;display:flex;align-items:center;gap:12px">
          <span style="font-size:22px">${b}</span>
          <div>
            <div style="font-size:13px;font-weight:700;color:#e2e8f0">Agreement ${o!==null&&o<=0?"Expired":"Expiry"}</div>
            <div style="font-size:12px;color:${d};margin-top:2px">${t.partner_end_date} · ${u}</div>
          </div>
        </div>`}const n=Object.entries(q).map(([s,d])=>{const b=s.replace("aadhar_","aadhaar_"),u=a[b]||a[s]||null,m=u?u.status:"Not Submitted",v=m!=="Approved",g=u?.uploaded_at?new Date(u.uploaded_at).toLocaleDateString("en-IN"):"",p=u?.rejection_reason?`<div style="font-size:10px;color:#ef4444;margin-top:4px;background:#450a0a;padding:3px 8px;border-radius:6px">${u.rejection_reason}</div>`:"";return`
        <div style="display:flex;align-items:center;gap:12px;padding:14px 0;border-bottom:1px solid #1e293b">
          <div style="width:40px;height:40px;border-radius:10px;background:${d.bg};display:flex;align-items:center;justify-content:center;font-size:18px;flex-shrink:0">${d.icon}</div>
          <div style="flex:1;min-width:0">
            <div style="font-size:13px;font-weight:600;color:#e2e8f0">${d.label}</div>
            <div style="font-size:11px;color:#64748b;margin-top:2px">${g?"Uploaded: "+g:"Not yet uploaded"}</div>
            ${p}
          </div>
          <div style="display:flex;flex-direction:column;align-items:flex-end;gap:6px;flex-shrink:0">
            ${_(m)}
            ${v?`<button onclick="partnerKYCUpload('${s}')" style="background:#1d4ed8;color:#fff;border:none;padding:5px 10px;border-radius:7px;font-size:11px;font-weight:600;cursor:pointer">Upload</button>`:""}
          </div>
        </div>`}).join("");this.container.innerHTML=`
      <div style="padding:20px;max-width:480px;margin:0 auto">
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:20px">
          <button onclick="window.routerService?.navigate('partner-dashboard')"
            style="background:none;border:none;color:#6b7280;cursor:pointer;padding:4px">
            <svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <polyline points="15 18 9 12 15 6"/>
            </svg>
          </button>
          <div>
            <h2 style="margin:0;font-size:18px;font-weight:700;color:#111827">KYC &amp; Documents</h2>
            <div style="font-size:12px;color:#6b7280;margin-top:2px">${e.partner_name||""}</div>
          </div>
        </div>

        ${r}

        <!-- Partnership Terms -->
        <div style="background:#fff;border-radius:14px;padding:18px 20px;box-shadow:0 2px 8px rgba(0,0,0,.07);margin-bottom:14px">
          <div style="font-size:12px;font-weight:700;color:#374151;margin-bottom:12px;text-transform:uppercase;letter-spacing:.5px">Partnership Terms</div>
          ${this.kv("Start Date",t.partner_start_date||"—")}
          ${this.kv("End Date",t.partner_end_date||"—")}
          ${this.kv("Security Deposit",t.security_deposit>0?"₹"+Number(t.security_deposit).toLocaleString("en-IN"):"—")}
          ${this.kv("Agreement Doc",t.agreement_submitted?"✅ Submitted":"⬜ Not Submitted")}
          ${this.kv("Application Doc",t.application_submitted?"✅ Submitted":"⬜ Not Submitted")}
        </div>

        <!-- KYC Documents -->
        <div style="background:#fff;border-radius:14px;padding:18px 20px;box-shadow:0 2px 8px rgba(0,0,0,.07);margin-bottom:14px">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px">
            <div style="font-size:12px;font-weight:700;color:#374151;text-transform:uppercase;letter-spacing:.5px">KYC Documents</div>
            ${_(i)}
          </div>
          <div style="font-size:11px;color:#9ca3af;margin-bottom:12px">Upload clear photos. Aadhaar (front &amp; back) and PAN card are required for verification.</div>
          ${n}
        </div>
      </div>

      <input type="file" id="kycUploadInput" accept="image/png,image/jpeg,application/pdf" style="display:none" onchange="handleKYCFileChange(this)">
    `,window.partnerKYCUpload=s=>{window._currentKYCType=s;const d=document.getElementById("kycUploadInput");d&&d.click()},window.handleKYCFileChange=async s=>{const d=s.files?.[0],b=window._currentKYCType;if(!d||!b)return;if(d.size>5*1024*1024){alert("File too large. Max 5MB.");return}const u=localStorage.getItem("partner_token")||"",m=new FormData;m.append("file",d),m.append("document_type",b);try{const v=l.getBaseUrl(),g=await fetch(`${v}/api/v1/partner/kyc/upload`,{method:"POST",headers:{Authorization:`Bearer ${u}`},body:m}),p=await g.json();p.success||g.ok?(alert("Uploaded successfully! Pending staff review."),this.init()):alert("Upload failed: "+(p.detail||p.message||"Please try again."))}catch{alert("Network error. Please try again.")}s.value=""}}kv(e,t){return`<div style="display:flex;gap:12px;padding:8px 0;border-bottom:1px solid #f3f4f6">
      <span style="font-size:12px;color:#6b7280;min-width:130px;font-weight:600">${e}</span>
      <span style="font-size:13px;color:#111827;font-weight:500">${t}</span>
    </div>`}}function D(c){const e={SUBMITTED:["#451a03","#f59e0b"],ACKNOWLEDGED:["#1e3a5f","#60a5fa"],FULFILLED:["#064e3b","#10b981"],CANCELLED:["#1f2937","#9ca3af"]},[t,a]=e[c]||["#1f2937","#9ca3af"];return`<span style="background:${t};color:${a};padding:3px 10px;border-radius:12px;font-size:11px;font-weight:700">${c}</span>`}class G{container;cart=new Map;companies=[];activeTab="catalog";searchTimer=null;allItems=[];requests=[];constructor(e){this.container=e}async init(){this.render(),await this.loadCompanies(),await this.loadCatalog()}render(){this.container.innerHTML=`
      <div style="display:flex;flex-direction:column;height:100%;background:#0f172a;">
        <!-- Header -->
        <div style="background:linear-gradient(135deg,#1e3a5f,#2563eb);padding:16px 20px 14px;flex-shrink:0;">
          <div style="font-size:18px;font-weight:700;color:#fff;margin-bottom:2px;">
            🔧 Spare Parts Orders
          </div>
          <div style="font-size:12px;color:rgba(255,255,255,.7);">Request spare parts from the catalog</div>
        </div>

        <!-- Tab Pills -->
        <div style="display:flex;gap:0;background:#1e293b;border-bottom:1px solid #334155;flex-shrink:0;">
          <button id="spTabCatalog" onclick="spTab('catalog')"
            style="flex:1;padding:12px;background:#2563eb;color:#fff;border:none;font-size:13px;font-weight:700;cursor:pointer;">
            📦 Catalog
          </button>
          <button id="spTabRequests" onclick="spTab('requests')"
            style="flex:1;padding:12px;background:transparent;color:#94a3b8;border:none;font-size:13px;font-weight:600;cursor:pointer;">
            📋 My Requests
          </button>
        </div>

        <!-- Catalog Panel -->
        <div id="spCatalogPanel" style="flex:1;overflow-y:auto;padding:0 16px 16px;">
          <!-- Search -->
          <div style="position:sticky;top:0;background:#0f172a;padding:12px 0 8px;z-index:10;">
            <input id="spSearch" type="text" placeholder="Search spare parts…"
              style="width:100%;padding:10px 14px;background:#1e293b;border:1px solid #334155;border-radius:10px;color:#e2e8f0;font-size:14px;outline:none;box-sizing:border-box;"
              oninput="spSearchDebounce()">
          </div>

          <!-- Cart Bar -->
          <div id="spCartBar" style="display:none;background:#1e40af;border-radius:10px;padding:12px 14px;margin-bottom:12px;display:flex;justify-content:space-between;align-items:center;">
            <span id="spCartCount" style="color:#fff;font-size:13px;font-weight:700;"></span>
            <button onclick="spSubmitSheet()"
              style="background:#fff;color:#1e40af;border:none;padding:8px 16px;border-radius:8px;font-size:13px;font-weight:700;cursor:pointer;">
              Submit Request
            </button>
          </div>

          <div id="spCatalogLoading" style="padding:40px;text-align:center;color:#64748b;">
            <div style="font-size:32px;margin-bottom:12px">⏳</div>
            <div style="font-size:13px">Loading catalog…</div>
          </div>
          <div id="spCatalogList"></div>
          <div id="spCatalogEmpty" style="display:none;padding:40px;text-align:center;color:#64748b;">
            <div style="font-size:40px;margin-bottom:12px">📦</div>
            <div style="font-size:14px;font-weight:600;color:#94a3b8">No spare parts found</div>
          </div>
        </div>

        <!-- Requests Panel -->
        <div id="spRequestsPanel" style="display:none;flex:1;overflow-y:auto;padding:16px;">
          <div id="spReqLoading" style="padding:40px;text-align:center;color:#64748b;">
            <div style="font-size:32px;margin-bottom:12px">⏳</div>
          </div>
          <div id="spReqList"></div>
          <div id="spReqEmpty" style="display:none;padding:40px;text-align:center;color:#64748b;">
            <div style="font-size:40px;margin-bottom:12px">📋</div>
            <div style="font-size:14px;font-weight:600;color:#94a3b8">No requests yet</div>
            <div style="font-size:12px;color:#64748b;margin-top:4px">Browse the catalog and submit a request</div>
          </div>
        </div>

        <!-- Submit Sheet (hidden) -->
        <div id="spSubmitSheet" style="display:none;position:fixed;bottom:0;left:0;right:0;background:#1e293b;border-radius:16px 16px 0 0;padding:20px;z-index:200;max-height:80vh;overflow-y:auto;box-shadow:0 -8px 32px rgba(0,0,0,.4);">
          <div style="width:40px;height:4px;background:#475569;border-radius:2px;margin:0 auto 16px;"></div>
          <div style="font-size:16px;font-weight:700;color:#e2e8f0;margin-bottom:14px;">Submit Spare Request</div>
          <div id="spSubmitItems" style="margin-bottom:14px;"></div>
          <select id="spSubmitCompany" style="width:100%;padding:12px;background:#0f172a;border:1px solid #334155;border-radius:10px;color:#e2e8f0;font-size:14px;margin-bottom:12px;box-sizing:border-box;">
            <option value="">Select Company…</option>
          </select>
          <textarea id="spSubmitNotes" placeholder="Notes (optional)…" rows="2"
            style="width:100%;padding:12px;background:#0f172a;border:1px solid #334155;border-radius:10px;color:#e2e8f0;font-size:14px;resize:none;margin-bottom:14px;box-sizing:border-box;"></textarea>
          <div style="display:flex;gap:10px;">
            <button onclick="document.getElementById('spSubmitSheet').style.display='none'"
              style="flex:1;padding:14px;background:#334155;color:#e2e8f0;border:none;border-radius:10px;font-size:14px;font-weight:600;cursor:pointer;">Cancel</button>
            <button onclick="spDoSubmit()"
              style="flex:2;padding:14px;background:#2563eb;color:#fff;border:none;border-radius:10px;font-size:15px;font-weight:700;cursor:pointer;">
              Submit Request
            </button>
          </div>
        </div>
        <div id="spSubmitOverlay" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:199;" onclick="document.getElementById('spSubmitSheet').style.display='none';this.style.display='none';"></div>
      </div>`;const e=this;window.spTab=t=>e.switchTab(t),window.spSearchDebounce=()=>{e.searchTimer&&clearTimeout(e.searchTimer),e.searchTimer=setTimeout(()=>e.loadCatalog(),350)},window.spToggleCart=t=>e.toggleCart(t),window.spUpdateQty=(t,a)=>e.updateQty(t,parseFloat(a)||1),window.spSubmitSheet=()=>e.openSubmitSheet(),window.spDoSubmit=()=>e.doSubmit(),window.spCancelReq=t=>e.cancelRequest(t)}switchTab(e){this.activeTab=e;const t=document.getElementById("spCatalogPanel"),a=document.getElementById("spRequestsPanel"),i=document.getElementById("spTabCatalog"),o=document.getElementById("spTabRequests");!t||!a||(e==="catalog"?(t.style.display="",a.style.display="none",i.style.background="#2563eb",i.style.color="#fff",o.style.background="transparent",o.style.color="#94a3b8"):(t.style.display="none",a.style.display="",i.style.background="transparent",i.style.color="#94a3b8",o.style.background="#2563eb",o.style.color="#fff",this.loadRequests()))}async loadCompanies(){try{const e=localStorage.getItem("partner_token")||"",t=l.getBaseUrl(),a=await fetch(`${t}/api/v1/staff/accounts/companies`,{headers:{Authorization:`Bearer ${e}`}});if(!a.ok)return;const i=await a.json();this.companies=i.companies||i.data||[]}catch{}}async loadCatalog(){const e=localStorage.getItem("partner_token")||"",t=l.getBaseUrl(),a=document.getElementById("spSearch")?.value?.trim()||"",i=document.getElementById("spCatalogLoading"),o=document.getElementById("spCatalogList"),r=document.getElementById("spCatalogEmpty");i&&(i.style.display=""),o&&(o.innerHTML=""),r&&(r.style.display="none");try{let n=`${t}/api/v1/partner/auth/spare-catalog?limit=200`;a&&(n+=`&search=${encodeURIComponent(a)}`);const s=await fetch(n,{headers:{Authorization:`Bearer ${e}`}});if(!s.ok)throw new Error("Auth error");const d=await s.json();if(this.allItems=d.items||[],i&&(i.style.display="none"),!this.allItems.length){r&&(r.style.display="");return}this.renderCatalog()}catch{i&&(i.style.display="none"),r&&(r.style.display="")}}renderCatalog(){const e=document.getElementById("spCatalogList");e&&(e.innerHTML=this.allItems.map(t=>{const a=this.cart.has(t.item_id),i=this.cart.get(t.item_id),o=t.current_stock>10?"#10b981":t.current_stock>0?"#f59e0b":"#ef4444",r=t.current_stock>0?`${t.current_stock} in stock`:"Out of stock";return`
        <div style="background:#1e293b;border-radius:12px;padding:14px 16px;margin-bottom:10px;border:1.5px solid ${a?"#2563eb":"#334155"};">
          <div style="font-size:10px;font-weight:700;color:#64748b;text-transform:uppercase;margin-bottom:2px;">${t.item_code}</div>
          <div style="font-size:15px;font-weight:700;color:#e2e8f0;margin-bottom:6px;line-height:1.3;">${t.item_name}</div>
          <div style="font-size:12px;margin-bottom:10px;">
            <span style="color:${o};font-weight:600;">${r}</span>
            <span style="color:#64748b;margin-left:8px;">· ${t.unit_of_measure}</span>
          </div>
          ${a?`
            <div style="display:flex;align-items:center;gap:10px;">
              <span style="font-size:12px;color:#60a5fa;font-weight:600;">✓ In Request</span>
              <input type="number" value="${i.qty}" min="1"
                style="width:70px;padding:6px 10px;background:#0f172a;border:1px solid #2563eb;border-radius:8px;color:#e2e8f0;font-size:14px;text-align:center;"
                onchange="spUpdateQty(${t.item_id}, this.value)">
              <span style="font-size:12px;color:#64748b;">${t.unit_of_measure}</span>
              <button onclick="spToggleCart(${t.item_id})"
                style="margin-left:auto;background:#450a0a;color:#ef4444;border:none;padding:6px 12px;border-radius:8px;font-size:12px;font-weight:600;cursor:pointer;">Remove</button>
            </div>`:`
            <button onclick="spToggleCart(${t.item_id})"
              style="width:100%;padding:10px;background:#1d4ed8;color:#fff;border:none;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;">
              + Add to Request
            </button>`}
        </div>`}).join(""),this.updateCartBar())}toggleCart(e){const t=this.allItems.find(a=>a.item_id===e);t&&(this.cart.has(e)?this.cart.delete(e):this.cart.set(e,{item:t,qty:1}),this.renderCatalog())}updateQty(e,t){const a=this.cart.get(e);a&&(a.qty=Math.max(1,t))}updateCartBar(){const e=document.getElementById("spCartBar"),t=document.getElementById("spCartCount");if(!e||!t)return;const a=this.cart.size;if(a===0){e.style.display="none";return}e.style.display="flex",t.textContent=`${a} item${a>1?"s":""} in request`}openSubmitSheet(){if(!this.cart.size)return;const e=document.getElementById("spSubmitSheet"),t=document.getElementById("spSubmitOverlay"),a=document.getElementById("spSubmitItems"),i=document.getElementById("spSubmitCompany");!e||!t||!a||!i||(a.innerHTML=Array.from(this.cart.values()).map(o=>`<div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #334155;">
        <span style="font-size:13px;color:#e2e8f0;">${o.item.item_name}</span>
        <span style="font-size:13px;font-weight:700;color:#60a5fa;">${o.qty} ${o.item.unit_of_measure}</span>
      </div>`).join(""),i.innerHTML='<option value="">Select Company…</option>'+this.companies.map(o=>`<option value="${o.id}">${o.company_name}</option>`).join(""),e.style.display="",t.style.display="")}async doSubmit(){const e=localStorage.getItem("partner_token")||"",t=l.getBaseUrl(),a=document.getElementById("spSubmitCompany")?.value,i=document.getElementById("spSubmitNotes")?.value?.trim()||"";if(!a){alert("Please select a company");return}const o=Array.from(this.cart.values()).map(r=>({item_id:r.item.item_id,quantity:r.qty,uom:r.item.unit_of_measure}));try{const n=await(await fetch(`${t}/api/v1/partner/auth/spare-requests`,{method:"POST",headers:{Authorization:`Bearer ${e}`,"Content-Type":"application/json"},body:JSON.stringify({items:o,notes:i,company_id:parseInt(a)})})).json();n.success?(document.getElementById("spSubmitSheet").style.display="none",document.getElementById("spSubmitOverlay").style.display="none",this.cart.clear(),alert(`✅ Request ${n.request?.request_number} submitted!`),this.switchTab("requests")):alert("Error: "+(n.detail||n.message||"Submission failed"))}catch{alert("Network error. Please try again.")}}async loadRequests(){const e=localStorage.getItem("partner_token")||"",t=l.getBaseUrl(),a=document.getElementById("spReqLoading"),i=document.getElementById("spReqList"),o=document.getElementById("spReqEmpty");a&&(a.style.display=""),i&&(i.innerHTML=""),o&&(o.style.display="none");try{const n=await(await fetch(`${t}/api/v1/partner/auth/spare-requests?limit=100`,{headers:{Authorization:`Bearer ${e}`}})).json();if(this.requests=n.requests||[],a&&(a.style.display="none"),!this.requests.length){o&&(o.style.display="");return}this.renderRequests()}catch{a&&(a.style.display="none"),o&&(o.style.display="")}}renderRequests(){const e=document.getElementById("spReqList");e&&(e.innerHTML=this.requests.map(t=>{const a=new Date(t.created_at).toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"numeric"}),i=(t.lines||[]).slice(0,2).map(r=>r.item_name||r.item_code).join(", "),o=(t.lines||[]).length>2?` +${(t.lines||[]).length-2} more`:"";return`
        <div style="background:#1e293b;border-radius:12px;padding:14px 16px;margin-bottom:10px;border:1px solid #334155;">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;">
            <div style="font-size:14px;font-weight:700;color:#60a5fa;">${t.request_number}</div>
            ${D(t.status)}
          </div>
          <div style="font-size:12px;color:#94a3b8;margin-bottom:4px;">${i}${o}</div>
          <div style="font-size:11px;color:#64748b;margin-bottom:10px;">${t.line_count} item(s) · ${a}</div>
          ${t.notes?`<div style="font-size:12px;color:#94a3b8;margin-bottom:8px;">📝 ${t.notes}</div>`:""}
          ${t.status==="SUBMITTED"?`
            <button onclick="spCancelReq(${t.id})"
              style="padding:8px 16px;background:#450a0a;color:#ef4444;border:1px solid #7f1d1d;border-radius:8px;font-size:12px;font-weight:600;cursor:pointer;">
              Cancel Request
            </button>`:""}
        </div>`}).join(""))}async cancelRequest(e){if(!confirm("Cancel this spare parts request?"))return;const t=localStorage.getItem("partner_token")||"",a=l.getBaseUrl();try{const o=await(await fetch(`${a}/api/v1/partner/auth/spare-requests/${e}/cancel`,{method:"PUT",headers:{Authorization:`Bearer ${t}`}})).json();o.success?(alert("Request cancelled"),this.loadRequests()):alert("Error: "+(o.detail||"Could not cancel"))}catch{alert("Network error")}}}export{R as P,H as a,Y as b,W as c,F as d,K as e,U as f,j as g,O as h,G as i};
