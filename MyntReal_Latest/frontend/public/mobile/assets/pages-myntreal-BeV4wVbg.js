import{b as i}from"./services-AEce4KDH.js";import{P as s}from"./components-9q5I9H7Z.js";class l{container;properties=[];loading=!0;filter="all";constructor(t){this.container=t}async init(){this.render(),await this.loadProperties()}async loadProperties(){this.loading=!0,this.updateContent();try{const t=await i.get("/real-dreams/public/listings");t.success&&t.data&&(this.properties=t.data.properties||t.data||[])}catch(t){console.error("[MyntRealProperties] Failed to load:",t)}this.loading=!1,this.updateContent()}render(){this.container.innerHTML=`
      <div class="page-container myntreal-page">
        ${s.render({title:"Properties",showBack:!0})}
        
        <div class="filter-tabs">
          <button class="tab ${this.filter==="all"?"active":""}" data-filter="all">All</button>
          <button class="tab ${this.filter==="residential"?"active":""}" data-filter="residential">Residential</button>
          <button class="tab ${this.filter==="commercial"?"active":""}" data-filter="commercial">Commercial</button>
          <button class="tab ${this.filter==="plots"?"active":""}" data-filter="plots">Plots</button>
        </div>

        <div id="pageContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
    `,this.attachListeners()}attachListeners(){s.attachListeners({title:"Properties",showBack:!0}),this.container.querySelectorAll(".filter-tabs .tab").forEach(t=>{t.addEventListener("click",()=>{this.filter=t.getAttribute("data-filter")||"all",this.render(),this.updateContent()})})}updateContent(){const t=document.getElementById("pageContent");if(!t)return;if(this.loading){t.innerHTML='<div class="loading-state">Loading properties...</div>';return}const a=this.getFilteredProperties();if(a.length===0){t.innerHTML=`
        <div class="empty-state card">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
            <polyline points="9 22 9 12 15 12 15 22"/>
          </svg>
          <h3>No Properties Found</h3>
          <p>Check back later for new listings</p>
        </div>
      `;return}t.innerHTML=`
      <div class="properties-grid">
        ${a.map(e=>`
          <div class="property-card card" data-id="${e.id}">
            <div class="property-image">
              ${e.image_url?`<img src="${e.image_url}" alt="${e.title}">`:'<div class="no-image">🏠</div>'}
              <span class="property-type-badge">${e.type}</span>
            </div>
            <div class="property-info">
              <h4 class="property-title">${e.title}</h4>
              <p class="property-location">📍 ${e.location}</p>
              <div class="property-meta">
                ${e.bedrooms?`<span>🛏️ ${e.bedrooms} BHK</span>`:""}
                ${e.area_sqft?`<span>📐 ${e.area_sqft} sqft</span>`:""}
              </div>
              <div class="property-price">₹${this.formatPrice(e.price)}</div>
            </div>
          </div>
        `).join("")}
      </div>
    `}getFilteredProperties(){return this.filter==="all"?this.properties:this.properties.filter(t=>t.type?.toLowerCase().includes(this.filter.toLowerCase()))}formatPrice(t){return t>=1e7?(t/1e7).toFixed(2)+" Cr":t>=1e5?(t/1e5).toFixed(2)+" L":t.toLocaleString()}}class d{container;earnings=[];summary=null;loading=!0;constructor(t){this.container=t}async init(){this.render(),await this.loadEarnings()}async loadEarnings(){this.loading=!0,this.updateContent();try{const t=await i.get("/myntreal/my-zynova-incentives");t.success&&t.data&&(this.earnings=t.data.earnings||[],this.summary=t.data.summary||null)}catch(t){console.error("[MyntRealEarnings] Failed to load:",t)}this.loading=!1,this.updateContent()}render(){this.container.innerHTML=`
      <div class="page-container myntreal-page">
        ${s.render({title:"MyntReal Earnings",showBack:!0})}
        
        <div id="pageContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
    `,s.attachListeners({title:"MyntReal Earnings",showBack:!0})}updateContent(){const t=document.getElementById("pageContent");if(!t)return;if(this.loading){t.innerHTML='<div class="loading-state">Loading...</div>';return}const a=this.summary||{total_earnings:0,pending_amount:0,approved_amount:0,disbursed_amount:0,properties_count:0};t.innerHTML=`
      <div class="myntreal-banner card">
        <div class="banner-icon">💰</div>
        <h2>MyntReal Earnings</h2>
        <p>Your property referral income</p>
      </div>

      <div class="earnings-summary card">
        <div class="total-section">
          <span class="total-label">Total Earnings</span>
          <span class="total-value">₹${a.total_earnings.toLocaleString()}</span>
        </div>
        <div class="summary-grid">
          <div class="summary-item pending">
            <span class="item-value">₹${a.pending_amount.toLocaleString()}</span>
            <span class="item-label">Pending</span>
          </div>
          <div class="summary-item approved">
            <span class="item-value">₹${a.approved_amount.toLocaleString()}</span>
            <span class="item-label">Approved</span>
          </div>
          <div class="summary-item disbursed">
            <span class="item-value">₹${a.disbursed_amount.toLocaleString()}</span>
            <span class="item-label">Paid</span>
          </div>
          <div class="summary-item properties">
            <span class="item-value">${a.properties_count}</span>
            <span class="item-label">Properties</span>
          </div>
        </div>
      </div>

      <h3 class="section-title">Recent Transactions</h3>
      <div class="earnings-list">
        ${this.earnings.length===0?'<div class="empty-state">No earnings yet. Start referring properties!</div>':this.earnings.map(e=>`
            <div class="earning-card card">
              <div class="earning-icon">🏠</div>
              <div class="earning-info">
                <h4>${e.property_title||"Property Referral"}</h4>
                <p class="earning-type">${e.type}</p>
                <span class="earning-date">${this.formatDate(e.created_at)}</span>
              </div>
              <div class="earning-amount-section">
                <span class="earning-amount">₹${e.amount.toLocaleString()}</span>
                <span class="earning-status ${e.status.toLowerCase()}">${e.status}</span>
              </div>
            </div>
          `).join("")}
      </div>
    `}formatDate(t){return new Date(t).toLocaleDateString("en-US",{day:"numeric",month:"short",year:"numeric"})}}export{d as M,l as a};
