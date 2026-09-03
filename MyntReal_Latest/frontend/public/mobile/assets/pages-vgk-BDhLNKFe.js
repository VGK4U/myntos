import{b as m,r as $,d as S,a as g}from"./services-9VcN4JBG.js";import{P as c}from"./components-DCtxME7j.js";class V{container;users=[];loading=!0;mode="today";constructor(e){this.container=e}async init(){this.render(),await this.loadBirthdays()}async loadBirthdays(){this.loading=!0,this.updateContent();try{const e=await m.get(`/banners/admin/birthdays/${this.mode}?audience=vgk4u`);e.success&&e.data?this.users=e.data.users||[]:this.users=[]}catch(e){console.error("[VGKBirthdays] Failed to load:",e),this.users=[]}this.loading=!1,this.updateContent()}render(){this.container.innerHTML=`
      <div class="page-container">
        ${c.render({title:"🎂 VGK4U Birthdays",showBack:!0})}
        <div id="pageContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
    `,c.attachListeners({title:"🎂 VGK4U Birthdays",showBack:!0})}updateContent(){const e=document.getElementById("pageContent");if(e){if(this.loading){e.innerHTML='<div class="loading-state">Loading...</div>';return}e.innerHTML=`
      <div class="filter-tabs card" style="display:flex;gap:8px;padding:8px;">
        <button data-mode="today"        class="filter-tab ${this.mode==="today"?"active":""}">Today</button>
        <button data-mode="tomorrow"     class="filter-tab ${this.mode==="tomorrow"?"active":""}">Tomorrow</button>
        <button data-mode="next-7-days"  class="filter-tab ${this.mode==="next-7-days"?"active":""}">Next 7 Days</button>
      </div>

      <div class="audience-pill" style="margin:8px 16px;font-size:12px;color:#6366f1;">
        Audience: VGK4U Members
      </div>

      ${this.users.length>0?`
        <div class="birthday-list">
          ${this.users.map(t=>this.renderUserCard(t)).join("")}
        </div>
      `:`
        <div class="empty-state card">
          <div class="empty-icon">🎂</div>
          <p>No VGK4U birthdays for ${this.modeLabel()}</p>
        </div>
      `}
    `,e.querySelectorAll(".filter-tab").forEach(t=>{t.addEventListener("click",()=>{const i=t.getAttribute("data-mode");i&&i!==this.mode&&(this.mode=i,this.loadBirthdays())})})}}renderUserCard(e){const t=new Date(e.birthday_date),i=t.getDate(),a=t.toLocaleDateString("en",{month:"short"});return`
      <div class="day-card card" style="display:flex;align-items:center;gap:12px;padding:12px;">
        <div class="day-date" style="text-align:center;min-width:48px;">
          <div class="day-num" style="font-size:20px;font-weight:700;">${i}</div>
          <div class="day-name" style="font-size:11px;color:#888;">${a}</div>
        </div>
        <div style="flex:1;">
          <div style="font-weight:600;">${this.escape(e.name)}</div>
          <div style="font-size:12px;color:#666;">${this.escape(e.location)}</div>
          <div style="font-size:11px;color:#888;margin-top:2px;">VGK4U · ${this.escape(e.user_id)}</div>
        </div>
      </div>
    `}modeLabel(){return this.mode==="today"?"today":this.mode==="tomorrow"?"tomorrow":"the next 7 days"}escape(e){return String(e??"").replace(/[&<>"']/g,t=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"})[t])}}class U{container;constructor(e){this.container=e}async init(){const t=$.getRouteParams().tab||"earnings",a={earnings:"VGK4U Member Hub",profile:"Profile",mycard:"My Card & Progress",addmember:"Add Channel Partner",coupons:"Coupons",network:"Team",points:"Points Balance",ledger:"My Earnings",leads:"My Leads",tickets:"Service Tickets",bonanza:"Bonanza Rewards",vendors:"Vendor Shops",media:"Media Hub",orders:"Orders"}[t]||"VGK4U Member Hub",r=S.getAuthState().user||{},o=r.name||r.partner_name||"Member",s=r.partner_code||"",l=s?`${o} (${s})`:o,p=document.getElementById("vgk4u-dashboard-frame");if(p&&p.contentWindow){p.contentWindow.postMessage({type:"vgk_switch_tab",tab:t},"*");const f=document.querySelector(".header-title");f&&(f.textContent=a);const u=document.querySelector(".header-subtitle");u&&(u.textContent=l),localStorage.setItem("vgk_active_tab",t)}else this.container.innerHTML=await this.render(),await this.afterRender()}async render(){const t=S.getAuthState().user||{},i=t.name||t.partner_name||"Member",a=t.partner_code||"",n=a?`${i} (${a})`:i,o=$.getRouteParams().tab||"earnings",l={earnings:"VGK4U Member Hub",profile:"Profile",mycard:"My Card & Progress",addmember:"Add Channel Partner",coupons:"Coupons",network:"Team",points:"Points Balance",ledger:"My Earnings",leads:"My Leads",tickets:"Service Tickets",bonanza:"Bonanza Rewards",vendors:"Vendor Shops",media:"Media Hub",orders:"Orders"}[o]||"VGK4U Member Hub";return`
      ${c.render({title:l,showBack:!1,showLogout:!0,subtitle:n,showMenu:!0})}
      <div style="background:#f6f9fc;min-height:calc(100vh - 64px)">
        <iframe
          id="vgk4u-dashboard-frame"
          src="${g.MEDIA_BASE_URL}/vgk/dashboard?embed=true&tab=${o}&token=${encodeURIComponent(localStorage.getItem("auth_token")||"")}"
          style="width:100%;height:calc(100vh - 64px);border:0;background:#f6f9fc;"
          loading="lazy"
          title="VGK4U Dashboard"
        ></iframe>
      </div>
    `}async afterRender(){const t=S.getAuthState().user||{},i=t.name||t.partner_name||"Member",a=t.partner_code||"",n=a?`${i} (${a})`:i,o=$.getRouteParams().tab||"earnings",l={earnings:"VGK4U Member Hub",profile:"Profile",mycard:"My Card & Progress",addmember:"Add Channel Partner",coupons:"Coupons",network:"Team",points:"Points Balance",ledger:"My Earnings",leads:"My Leads",tickets:"Service Tickets",bonanza:"Bonanza Rewards",vendors:"Vendor Shops",media:"Media Hub",orders:"Orders"}[o]||"VGK4U Member Hub";c.attachListeners({title:l,showBack:!1,showLogout:!0,subtitle:n,showMenu:!0})}}class N{container;constructor(e){this.container=e}async init(){this.container.innerHTML=await this.render(),await this.afterRender()}static slug="coupon-benefits";static label="Coupon Benefits";static icon="🎟️";static color="#e11d48";static endpoint="/api/v1/admin/coupon-benefits?audience=vgk4u";async render(){return`
        ${c.render({title:"Coupon Benefits",showBack:!0})}
        <div style="padding:14px 12px;background:#f6f9fc;min-height:100vh">
          <div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #e11d48;border-radius:12px;padding:14px 16px;margin-bottom:12px">
            <div style="display:flex;align-items:center;gap:10px;font-weight:700;color:#0f172a;font-size:15px">
              <span style="font-size:22px">🎟️</span> Coupon Benefits
            </div>
            <div style="margin-top:6px;color:#64748b;font-size:12px">VGK4U Members · Read-Only · Phase 1</div>
          </div>
          <iframe
            id="vgk4u-coupon-benefits-frame"
            src="${g.MEDIA_BASE_URL}/vgk/coupon-benefits?token=${encodeURIComponent(localStorage.getItem("auth_token")||"")}"
            style="width:100%;height:calc(100vh - 180px);border:0;background:#fff;border-radius:12px;border:1px solid #e2e8f0"
            loading="lazy"
            title="Coupon Benefits (VGK4U)"
          ></iframe>
        </div>
      `}async afterRender(){}}class K{container;constructor(e){this.container=e}async init(){this.container.innerHTML=await this.render(),await this.afterRender()}static slug="daywise-income";static label="Daywise Income";static icon="📅";static color="#059669";static endpoint="/api/v1/admin/daywise-income?audience=vgk4u";async render(){return`
        ${c.render({title:"Daywise Income",showBack:!0})}
        <div style="padding:14px 12px;background:#f6f9fc;min-height:100vh">
          <div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #059669;border-radius:12px;padding:14px 16px;margin-bottom:12px">
            <div style="display:flex;align-items:center;gap:10px;font-weight:700;color:#0f172a;font-size:15px">
              <span style="font-size:22px">📅</span> Daywise Income
            </div>
            <div style="margin-top:6px;color:#64748b;font-size:12px">VGK4U Members · Read-Only · Phase 1</div>
          </div>
          <iframe
            id="vgk4u-daywise-income-frame"
            src="${g.MEDIA_BASE_URL}/vgk/daywise-income?token=${encodeURIComponent(localStorage.getItem("auth_token")||"")}"
            style="width:100%;height:calc(100vh - 180px);border:0;background:#fff;border-radius:12px;border:1px solid #e2e8f0"
            loading="lazy"
            title="Daywise Income (VGK4U)"
          ></iframe>
        </div>
      `}async afterRender(){}}class G{container;constructor(e){this.container=e}async init(){this.container.innerHTML=await this.render(),await this.afterRender()}static slug="direct-summary";static label="Direct (L1)";static icon="①";static color="#475569";static endpoint="/api/v1/admin/direct-summary?audience=vgk4u";async render(){return`
        ${c.render({title:"Direct (L1)",showBack:!0})}
        <div style="padding:14px 12px;background:#f6f9fc;min-height:100vh">
          <div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #475569;border-radius:12px;padding:14px 16px;margin-bottom:12px">
            <div style="display:flex;align-items:center;gap:10px;font-weight:700;color:#0f172a;font-size:15px">
              <span style="font-size:22px">①</span> Direct (L1)
            </div>
            <div style="margin-top:6px;color:#64748b;font-size:12px">VGK4U Members · Read-Only · Phase 1</div>
          </div>
          <iframe
            id="vgk4u-direct-summary-frame"
            src="${g.MEDIA_BASE_URL}/vgk/direct-summary?token=${encodeURIComponent(localStorage.getItem("auth_token")||"")}"
            style="width:100%;height:calc(100vh - 180px);border:0;background:#fff;border-radius:12px;border:1px solid #e2e8f0"
            loading="lazy"
            title="Direct (L1) (VGK4U)"
          ></iframe>
        </div>
      `}async afterRender(){}}class O{container;constructor(e){this.container=e}async init(){this.container.innerHTML=await this.render(),await this.afterRender()}static slug="ev-benefits";static label="EV Benefits";static icon="⚡";static color="#16a34a";static endpoint="/api/v1/ev-discount/admin/ev-discount-stats?audience=vgk4u";async render(){return`
        ${c.render({title:"EV Benefits",showBack:!0})}
        <div style="padding:14px 12px;background:#f6f9fc;min-height:100vh">
          <div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #16a34a;border-radius:12px;padding:14px 16px;margin-bottom:12px">
            <div style="display:flex;align-items:center;gap:10px;font-weight:700;color:#0f172a;font-size:15px">
              <span style="font-size:22px">⚡</span> EV Benefits
            </div>
            <div style="margin-top:6px;color:#64748b;font-size:12px">VGK4U Members · Read-Only · Phase 1</div>
          </div>
          <iframe
            id="vgk4u-ev-benefits-frame"
            src="${g.MEDIA_BASE_URL}/vgk/ev-benefits?token=${encodeURIComponent(localStorage.getItem("auth_token")||"")}"
            style="width:100%;height:calc(100vh - 180px);border:0;background:#fff;border-radius:12px;border:1px solid #e2e8f0"
            loading="lazy"
            title="EV Benefits (VGK4U)"
          ></iframe>
        </div>
      `}async afterRender(){}}class F{container;constructor(e){this.container=e}async init(){this.container.innerHTML=await this.render(),await this.afterRender()}static slug="ev-discount";static label="EV Discount";static icon="🏷️";static color="#16a34a";static endpoint="/api/v1/ev-discount/admin/ev-discount-stats?audience=vgk4u";async render(){return`
        ${c.render({title:"EV Discount",showBack:!0})}
        <div style="padding:14px 12px;background:#f6f9fc;min-height:100vh">
          <div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #16a34a;border-radius:12px;padding:14px 16px;margin-bottom:12px">
            <div style="display:flex;align-items:center;gap:10px;font-weight:700;color:#0f172a;font-size:15px">
              <span style="font-size:22px">🏷️</span> EV Discount
            </div>
            <div style="margin-top:6px;color:#64748b;font-size:12px">VGK4U Members · Read-Only · Phase 1</div>
          </div>
          <iframe
            id="vgk4u-ev-discount-frame"
            src="${g.MEDIA_BASE_URL}/vgk/ev-discount?token=${encodeURIComponent(localStorage.getItem("auth_token")||"")}"
            style="width:100%;height:calc(100vh - 180px);border:0;background:#fff;border-radius:12px;border:1px solid #e2e8f0"
            loading="lazy"
            title="EV Discount (VGK4U)"
          ></iframe>
        </div>
      `}async afterRender(){}}class q{container;constructor(e){this.container=e}async init(){this.container.innerHTML=await this.render(),await this.afterRender()}static slug="franchise-earnings";static label="Franchise";static icon="🏪";static color="#ea580c";static endpoint="/api/v1/ev-discount/admin/franchise-purchases?audience=vgk4u";async render(){return`
        ${c.render({title:"Franchise",showBack:!0})}
        <div style="padding:14px 12px;background:#f6f9fc;min-height:100vh">
          <div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #ea580c;border-radius:12px;padding:14px 16px;margin-bottom:12px">
            <div style="display:flex;align-items:center;gap:10px;font-weight:700;color:#0f172a;font-size:15px">
              <span style="font-size:22px">🏪</span> Franchise
            </div>
            <div style="margin-top:6px;color:#64748b;font-size:12px">VGK4U Members · Read-Only · Phase 1</div>
          </div>
          <iframe
            id="vgk4u-franchise-earnings-frame"
            src="${g.MEDIA_BASE_URL}/vgk/franchise-earnings?token=${encodeURIComponent(localStorage.getItem("auth_token")||"")}"
            style="width:100%;height:calc(100vh - 180px);border:0;background:#fff;border-radius:12px;border:1px solid #e2e8f0"
            loading="lazy"
            title="Franchise (VGK4U)"
          ></iframe>
        </div>
      `}async afterRender(){}}class H{container;constructor(e){this.container=e}async init(){this.container.innerHTML=await this.render(),await this.afterRender()}static slug="guru-summary";static label="Senior (L3)";static icon="③";static color="#475569";static endpoint="/api/v1/admin/guru-summary?audience=vgk4u";async render(){return`
        ${c.render({title:"Senior (L3)",showBack:!0})}
        <div style="padding:14px 12px;background:#f6f9fc;min-height:100vh">
          <div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #475569;border-radius:12px;padding:14px 16px;margin-bottom:12px">
            <div style="display:flex;align-items:center;gap:10px;font-weight:700;color:#0f172a;font-size:15px">
              <span style="font-size:22px">③</span> Senior (L3)
            </div>
            <div style="margin-top:6px;color:#64748b;font-size:12px">VGK4U Members · Read-Only · Phase 1</div>
          </div>
          <iframe
            id="vgk4u-guru-summary-frame"
            src="${g.MEDIA_BASE_URL}/vgk/guru-summary?token=${encodeURIComponent(localStorage.getItem("auth_token")||"")}"
            style="width:100%;height:calc(100vh - 180px);border:0;background:#fff;border-radius:12px;border:1px solid #e2e8f0"
            loading="lazy"
            title="Senior (L3) (VGK4U)"
          ></iframe>
        </div>
      `}async afterRender(){}}class j{container;constructor(e){this.container=e}async init(){this.container.innerHTML=await this.render(),await this.afterRender()}static slug="income-types";static label="Income Types";static icon="📊";static color="#2563eb";static endpoint="/api/v1/admin/income-types?audience=vgk4u";async render(){return`
        ${c.render({title:"Income Types",showBack:!0})}
        <div style="padding:14px 12px;background:#f6f9fc;min-height:100vh">
          <div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #2563eb;border-radius:12px;padding:14px 16px;margin-bottom:12px">
            <div style="display:flex;align-items:center;gap:10px;font-weight:700;color:#0f172a;font-size:15px">
              <span style="font-size:22px">📊</span> Income Types
            </div>
            <div style="margin-top:6px;color:#64748b;font-size:12px">VGK4U Members · Read-Only · Phase 1</div>
          </div>
          <iframe
            id="vgk4u-income-types-frame"
            src="${g.MEDIA_BASE_URL}/vgk/income-types?token=${encodeURIComponent(localStorage.getItem("auth_token")||"")}"
            style="width:100%;height:calc(100vh - 180px);border:0;background:#fff;border-radius:12px;border:1px solid #e2e8f0"
            loading="lazy"
            title="Income Types (VGK4U)"
          ></iframe>
        </div>
      `}async afterRender(){}}class W{container;constructor(e){this.container=e}async init(){this.container.innerHTML=await this.render(),await this.afterRender()}static slug="insurance";static label="Insurance";static icon="🛡️";static color="#4f46e5";static endpoint="/api/v1/admin/insurance?audience=vgk4u";async render(){return`
        ${c.render({title:"Insurance",showBack:!0})}
        <div style="padding:14px 12px;background:#f6f9fc;min-height:100vh">
          <div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #4f46e5;border-radius:12px;padding:14px 16px;margin-bottom:12px">
            <div style="display:flex;align-items:center;gap:10px;font-weight:700;color:#0f172a;font-size:15px">
              <span style="font-size:22px">🛡️</span> Insurance
            </div>
            <div style="margin-top:6px;color:#64748b;font-size:12px">VGK4U Members · Read-Only · Phase 1</div>
          </div>
          <iframe
            id="vgk4u-insurance-frame"
            src="${g.MEDIA_BASE_URL}/vgk/insurance?token=${encodeURIComponent(localStorage.getItem("auth_token")||"")}"
            style="width:100%;height:calc(100vh - 180px);border:0;background:#fff;border-radius:12px;border:1px solid #e2e8f0"
            loading="lazy"
            title="Insurance (VGK4U)"
          ></iframe>
        </div>
      `}async afterRender(){}}class Y{container;constructor(e){this.container=e}async init(){this.container.innerHTML=await this.render(),await this.afterRender()}static slug="matching-summary";static label="Matching (L2)";static icon="②";static color="#475569";static endpoint="/api/v1/admin/matching-summary?audience=vgk4u";async render(){return`
        ${c.render({title:"Matching (L2)",showBack:!0})}
        <div style="padding:14px 12px;background:#f6f9fc;min-height:100vh">
          <div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #475569;border-radius:12px;padding:14px 16px;margin-bottom:12px">
            <div style="display:flex;align-items:center;gap:10px;font-weight:700;color:#0f172a;font-size:15px">
              <span style="font-size:22px">②</span> Matching (L2)
            </div>
            <div style="margin-top:6px;color:#64748b;font-size:12px">VGK4U Members · Read-Only · Phase 1</div>
          </div>
          <iframe
            id="vgk4u-matching-summary-frame"
            src="${g.MEDIA_BASE_URL}/vgk/matching-summary?token=${encodeURIComponent(localStorage.getItem("auth_token")||"")}"
            style="width:100%;height:calc(100vh - 180px);border:0;background:#fff;border-radius:12px;border:1px solid #e2e8f0"
            loading="lazy"
            title="Matching (L2) (VGK4U)"
          ></iframe>
        </div>
      `}async afterRender(){}}class Z{container;constructor(e){this.container=e}async init(){this.container.innerHTML=await this.render(),await this.afterRender()}static slug="my-submissions";static label="My Submissions";static icon="📄";static color="#7c3aed";static endpoint="/api/v1/admin/my-submissions?audience=vgk4u";async render(){return`
        ${c.render({title:"My Submissions",showBack:!0})}
        <div style="padding:14px 12px;background:#f6f9fc;min-height:100vh">
          <div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #7c3aed;border-radius:12px;padding:14px 16px;margin-bottom:12px">
            <div style="display:flex;align-items:center;gap:10px;font-weight:700;color:#0f172a;font-size:15px">
              <span style="font-size:22px">📄</span> My Submissions
            </div>
            <div style="margin-top:6px;color:#64748b;font-size:12px">VGK4U Members · Read-Only · Phase 1</div>
          </div>
          <iframe
            id="vgk4u-my-submissions-frame"
            src="${g.MEDIA_BASE_URL}/vgk/my-submissions?token=${encodeURIComponent(localStorage.getItem("auth_token")||"")}"
            style="width:100%;height:calc(100vh - 180px);border:0;background:#fff;border-radius:12px;border:1px solid #e2e8f0"
            loading="lazy"
            title="My Submissions (VGK4U)"
          ></iframe>
        </div>
      `}async afterRender(){}}class J{container;constructor(e){this.container=e}async init(){this.container.innerHTML=await this.render(),await this.afterRender()}static slug="training";static label="Training";static icon="🎓";static color="#db2777";static endpoint="/api/v1/admin/training?audience=vgk4u";async render(){return`
        ${c.render({title:"Training",showBack:!0})}
        <div style="padding:14px 12px;background:#f6f9fc;min-height:100vh">
          <div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #db2777;border-radius:12px;padding:14px 16px;margin-bottom:12px">
            <div style="display:flex;align-items:center;gap:10px;font-weight:700;color:#0f172a;font-size:15px">
              <span style="font-size:22px">🎓</span> Training
            </div>
            <div style="margin-top:6px;color:#64748b;font-size:12px">VGK4U Members · Read-Only · Phase 1</div>
          </div>
          <iframe
            id="vgk4u-training-frame"
            src="${g.MEDIA_BASE_URL}/vgk/training?token=${encodeURIComponent(localStorage.getItem("auth_token")||"")}"
            style="width:100%;height:calc(100vh - 180px);border:0;background:#fff;border-radius:12px;border:1px solid #e2e8f0"
            loading="lazy"
            title="Training (VGK4U)"
          ></iframe>
        </div>
      `}async afterRender(){}}class Q{container;constructor(e){this.container=e}async init(){this.container.innerHTML=await this.render(),await this.afterRender()}static slug="ved-summary";static label="VED (L5)";static icon="⑤";static color="#475569";static endpoint="/api/v1/admin/ved-summary?audience=vgk4u";async render(){return`
        ${c.render({title:"VED (L5)",showBack:!0})}
        <div style="padding:14px 12px;background:#f6f9fc;min-height:100vh">
          <div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #475569;border-radius:12px;padding:14px 16px;margin-bottom:12px">
            <div style="display:flex;align-items:center;gap:10px;font-weight:700;color:#0f172a;font-size:15px">
              <span style="font-size:22px">⑤</span> VED (L5)
            </div>
            <div style="margin-top:6px;color:#64748b;font-size:12px">VGK4U Members · Read-Only · Phase 1</div>
          </div>
          <iframe
            id="vgk4u-ved-summary-frame"
            src="${g.MEDIA_BASE_URL}/vgk/ved-summary?token=${encodeURIComponent(localStorage.getItem("auth_token")||"")}"
            style="width:100%;height:calc(100vh - 180px);border:0;background:#fff;border-radius:12px;border:1px solid #e2e8f0"
            loading="lazy"
            title="VED (L5) (VGK4U)"
          ></iframe>
        </div>
      `}async afterRender(){}}class X{container;earners=[];latestDate=null;loading=!0;constructor(e){this.container=e}async init(){this.render(),await this.loadEarners()}async loadEarners(){this.loading=!0,this.updateContent();try{const e=await m.get("/banners/top-performers?limit=10&audience=vgk4u");e.success&&e.data?(this.earners=e.data.top_performers||[],this.latestDate=e.data.latest_earning_date||null):this.earners=[]}catch(e){console.error("[VGKTopEarners] Failed to load:",e),this.earners=[]}this.loading=!1,this.updateContent()}render(){this.container.innerHTML=`
      <div class="page-container">
        ${c.render({title:"🏆 VGK4U Top Earners",showBack:!0})}
        <div id="pageContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
    `,c.attachListeners({title:"🏆 VGK4U Top Earners",showBack:!0})}updateContent(){const e=document.getElementById("pageContent");if(!e)return;if(this.loading){e.innerHTML='<div class="loading-state">Loading...</div>';return}const t=this.latestDate?`Latest earning day: ${this.latestDate}`:"No qualifying earnings yet";e.innerHTML=`
      <div class="audience-pill" style="margin:8px 16px;font-size:12px;color:#6366f1;">
        Audience: VGK4U Members · ${this.escape(t)}
      </div>

      ${this.earners.length>0?`
        <div class="leaderboard">
          ${this.earners.map(i=>this.renderEarnerCard(i)).join("")}
        </div>
      `:`
        <div class="empty-state card">
          <div class="empty-icon">🏆</div>
          <p>No VGK4U top earners yet</p>
          <p style="font-size:12px;color:#888;">Top performers appear once VGK income entries cross ₹1,000 in a single day.</p>
        </div>
      `}
    `}renderEarnerCard(e){return`
      <div class="day-card card" style="display:flex;align-items:center;gap:12px;padding:12px;">
        <div style="font-size:20px;font-weight:700;min-width:40px;text-align:center;">${e.rank===1?"🥇":e.rank===2?"🥈":e.rank===3?"🥉":`#${e.rank}`}</div>
        <div style="flex:1;">
          <div style="font-weight:600;">${this.escape(e.name)}</div>
          <div style="font-size:11px;color:#888;">VGK4U · ${this.escape(e.user_id)}</div>
          ${e.badge?`<div style="font-size:11px;margin-top:2px;">${this.escape(e.badge)}</div>`:""}
        </div>
        <div style="font-weight:700;color:#10b981;">
          ₹${(e.total_earnings||0).toLocaleString("en-IN")}
        </div>
      </div>
    `}escape(e){return String(e??"").replace(/[&<>"']/g,t=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"})[t])}}class ee{container;awards=[];loading=!0;vgk4uEnabled=!0;note="";audienceLabel="VGK4U Members";constructor(e){this.container=e}async init(){this.render(),await this.loadAwards()}async loadAwards(){this.loading=!0,this.updateContent();try{const e=await m.get("/unified-awards/list?audience=vgk4u");e.success&&e.data?(this.awards=e.data.awards||[],this.vgk4uEnabled=e.data.vgk4u_enabled!==!1,this.note=e.data.note||"",this.audienceLabel=e.data.audience_label||"VGK4U Members"):this.awards=[]}catch(e){console.error("[VGKAwards] Failed to load:",e),this.awards=[]}this.loading=!1,this.updateContent()}render(){this.container.innerHTML=`
      <div class="page-container">
        ${c.render({title:"🏆 VGK4U Awards",showBack:!0})}
        <div id="pageContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
    `,c.attachListeners({title:"🏆 VGK4U Awards",showBack:!0})}updateContent(){const e=document.getElementById("pageContent");if(!e)return;if(this.loading){e.innerHTML='<div class="loading-state">Loading...</div>';return}const t=`
      <div style="display:flex;justify-content:space-between;align-items:center;margin:8px 16px;">
        <div style="font-size:12px;color:#6366f1;">Audience: ${this.escape(this.audienceLabel)}</div>
        <span style="
          padding:2px 10px;border-radius:999px;font-size:11px;font-weight:600;
          background:${this.vgk4uEnabled?"#dcfce7":"#fef3c7"};
          color:${this.vgk4uEnabled?"#166534":"#92400e"};
        ">
          Master switch ${this.vgk4uEnabled?"ON":"OFF"}
        </span>
      </div>
    `;if(this.awards.length===0){e.innerHTML=`
        ${t}
        <div class="empty-state card" style="padding:24px;text-align:center;">
          <div class="empty-icon" style="font-size:48px;">🏆</div>
          <p style="font-weight:600;margin:8px 0 4px;">No VGK4U awards yet</p>
          <p style="font-size:12px;color:#666;">
            ${this.escape(this.note||"The VGK4U award programme is on a separate roadmap.")}
          </p>
        </div>
      `;return}e.innerHTML=`
      ${t}
      <div class="awards-list">
        ${this.awards.map(i=>this.renderAwardCard(i)).join("")}
      </div>
    `}renderAwardCard(e){const t=e.award_name||e.gift_name||"Award",i=e.user_name||e.partner_name||e.user_id||"",a=e.status||"";return`
      <div class="day-card card" style="padding:12px;margin:8px 16px;">
        <div style="font-weight:600;">${this.escape(t)}</div>
        <div style="font-size:12px;color:#666;margin-top:2px;">
          ${this.escape(i)}${a?` · ${this.escape(a)}`:""}
        </div>
      </div>
    `}escape(e){return String(e??"").replace(/[&<>"']/g,t=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"})[t])}}class te{container;members=[];total=0;thisMonth=0;loading=!0;page=1;pageSize=25;regOtpSent=!1;regPhoneVerifiedToken="";lastRegData=null;refLookupTimer=null;constructor(e){this.container=e}async init(){this.render(),this.attachEvents(),await this.loadData()}async loadData(){this.loading=!0,this.updateList();try{const e=`/vgk/my-registrations?page=${this.page}&page_size=${this.pageSize}`,t=await m.get(e);t.success?(this.members=t.data||[],this.total=t.total||0,this.thisMonth=t.this_month||0):this.members=[]}catch(e){console.error("[VGKMyRegistrations] load error:",e),this.members=[]}finally{this.loading=!1,this.updateList(),this.updateStats()}}fmtDate(e){return e?new Date(e).toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"2-digit"}):"—"}render(){const t=JSON.parse(localStorage.getItem("vgk_partner")||"{}").partner_code||"";this.container.innerHTML=`
      <div style="background:#f8f5ff;min-height:100vh;padding-bottom:80px">
        ${c.render({title:"My VGK Registrations",showBack:!0})}

        <!-- Stats + Register button strip -->
        <div style="display:flex;gap:10px;padding:12px 16px;flex-wrap:wrap;align-items:stretch" id="myRegStats">
          <div style="flex:1;min-width:90px;background:white;border-radius:10px;padding:12px;text-align:center;box-shadow:0 1px 4px rgba(0,0,0,.07)">
            <div style="font-size:10px;color:#6b7280;font-weight:700;text-transform:uppercase;margin-bottom:4px">Total</div>
            <div style="font-size:22px;font-weight:800;color:#7c3aed" id="statTotal">—</div>
          </div>
          <div style="flex:1;min-width:90px;background:white;border-radius:10px;padding:12px;text-align:center;box-shadow:0 1px 4px rgba(0,0,0,.07)">
            <div style="font-size:10px;color:#6b7280;font-weight:700;text-transform:uppercase;margin-bottom:4px">This Month</div>
            <div style="font-size:22px;font-weight:800;color:#059669" id="statThisMonth">—</div>
          </div>
          <button id="regOpenBtn" style="flex:0 0 auto;background:linear-gradient(135deg,#4c1d95,#7c3aed);color:#fff;border:none;border-radius:10px;padding:12px 16px;font-size:13px;font-weight:700;cursor:pointer;display:flex;align-items:center;gap:6px;box-shadow:0 2px 8px rgba(124,58,237,.35)">
            <i class="fas fa-user-plus"></i> Register
          </button>
        </div>

        <!-- Registration form card (hidden by default) -->
        <div id="regFormCard" style="display:none;margin:0 12px 16px;background:white;border-radius:14px;box-shadow:0 2px 12px rgba(124,58,237,.12);border:1.5px solid #ede9fe;overflow:hidden">
          <div style="background:linear-gradient(135deg,#4c1d95,#7c3aed);padding:14px 16px;display:flex;justify-content:space-between;align-items:center">
            <div style="font-size:14px;font-weight:800;color:#fff"><i class="fas fa-user-plus me-2"></i>Register a New Channel Partner</div>
            <button id="regCloseBtn" style="background:rgba(255,255,255,.2);border:none;color:#fff;border-radius:8px;padding:4px 10px;font-size:12px;cursor:pointer">✕ Close</button>
          </div>
          <div style="padding:16px">
            <p style="font-size:12.5px;color:#6b7280;margin:0 0 14px">Refer someone to join VGK. They will be placed under you as referrer.</p>

            <!-- Success panel -->
            <div id="regSuccess" style="display:none;background:#f0fdf4;border:1.5px solid #22c55e;border-radius:12px;padding:18px;text-align:center;margin-bottom:12px">
              <i class="fas fa-check-circle" style="font-size:28px;color:#22c55e"></i>
              <p style="font-weight:700;margin:8px 0 4px;color:#166534">Channel Partner Registered!</p>
              <div style="font-size:20px;font-weight:800;color:#7c3aed;letter-spacing:1px" id="regNewId"></div>
              <p style="font-size:12px;color:#6b7280;margin-top:6px">Account is <strong>pending activation</strong>. Pay ₹5,000 to activate and receive <strong>50,000 bonus points</strong>.</p>
              <div style="display:flex;flex-direction:column;gap:8px;margin-top:12px">
                <button id="regShareBtn" style="background:#25D366;border:none;color:#fff;font-weight:700;padding:10px 18px;border-radius:9px;cursor:pointer;font-size:13px;display:flex;align-items:center;justify-content:center;gap:6px">
                  <i class="fab fa-whatsapp"></i>Share Login Details via WhatsApp
                </button>
                <button id="regAnotherBtn" style="background:#7c3aed;border:none;color:#fff;font-weight:700;padding:9px 22px;border-radius:9px;cursor:pointer;font-size:13px"><i class="fas fa-plus me-1"></i>Add Another</button>
              </div>
            </div>

            <!-- Error -->
            <div id="regError" style="display:none;background:#fef2f2;border:1.5px solid #fca5a5;border-radius:9px;padding:10px 14px;font-size:12.5px;color:#dc2626;margin-bottom:12px"></div>

            <!-- Form -->
            <form id="regForm" novalidate autocomplete="off">
              <!-- Name -->
              <div style="margin-bottom:12px">
                <label style="font-size:11px;font-weight:700;color:#6b7280;text-transform:uppercase;display:block;margin-bottom:5px">Title &amp; Name <span style="color:#e11d48">*</span></label>
                <div style="display:flex;gap:6px;flex-wrap:wrap">
                  <select id="regTitle" style="flex:0 0 80px;padding:8px 6px;border:1.5px solid #e5e7eb;border-radius:8px;font-size:13px">
                    <option value="">Title</option>
                    <option value="Mr.">Mr.</option>
                    <option value="Ms.">Ms.</option>
                    <option value="Mrs.">Mrs.</option>
                  </select>
                  <input type="text" id="regFirstName" placeholder="First name" required style="flex:1;min-width:90px;padding:8px 10px;border:1.5px solid #e5e7eb;border-radius:8px;font-size:13px">
                  <input type="text" id="regLastName"  placeholder="Last name"  required style="flex:1;min-width:90px;padding:8px 10px;border:1.5px solid #e5e7eb;border-radius:8px;font-size:13px">
                </div>
              </div>

              <!-- Gender -->
              <div style="margin-bottom:12px">
                <label style="font-size:11px;font-weight:700;color:#6b7280;text-transform:uppercase;display:block;margin-bottom:5px">Gender <span style="font-size:10px;color:#9ca3af;text-transform:none">(optional)</span></label>
                <select id="regGender" style="width:100%;padding:8px 10px;border:1.5px solid #e5e7eb;border-radius:8px;font-size:13px">
                  <option value="">-- Select --</option>
                  <option value="Male">Male</option>
                  <option value="Female">Female</option>
                  <option value="Other">Other</option>
                </select>
              </div>

              <!-- Phone + OTP (DC-PHONE-OTP-001) -->
              <div style="margin-bottom:12px">
                <label style="font-size:11px;font-weight:700;color:#6b7280;text-transform:uppercase;display:block;margin-bottom:5px">Phone <span style="color:#e11d48">*</span></label>
                <div style="display:flex;gap:6px">
                  <input type="tel" id="regPhone" placeholder="10-digit mobile" required maxlength="10"
                    style="flex:1;padding:8px 10px;border:1.5px solid #e5e7eb;border-radius:8px;font-size:13px">
                  <button type="button" id="regSendOtpBtn"
                    style="background:#7c3aed;color:#fff;border:none;padding:8px 12px;border-radius:8px;font-size:12px;font-weight:700;white-space:nowrap;cursor:pointer;flex-shrink:0">
                    Send OTP
                  </button>
                </div>
                <div style="font-size:11px;color:#f87171;margin-top:4px"><i class="fas fa-shield-alt" style="margin-right:3px"></i>WhatsApp OTP verification required.</div>

                <!-- OTP input block (hidden until Send OTP clicked) -->
                <div id="regOtpBlock" style="display:none;margin-top:10px;background:#f0fdf4;border:1.5px solid #86efac;border-radius:9px;padding:10px 12px">
                  <div style="font-size:12px;color:#166534;margin-bottom:7px"><i class="fab fa-whatsapp" style="margin-right:4px"></i>OTP sent to WhatsApp. Enter below:</div>
                  <div style="display:flex;gap:6px">
                    <input type="text" id="regOtpInput" maxlength="6" placeholder="6-digit OTP"
                      style="flex:1;padding:8px 10px;border-radius:8px;border:1.5px solid #86efac;font-size:16px;font-weight:700;letter-spacing:4px;text-align:center">
                    <button type="button" id="regVerifyBtn"
                      style="background:#16a34a;color:#fff;border:none;padding:8px 12px;border-radius:8px;font-size:12px;font-weight:700;cursor:pointer;flex-shrink:0">
                      Verify
                    </button>
                  </div>
                  <div style="margin-top:5px;font-size:11px;color:#6b7280">
                    Didn't receive? <span id="regResendLink" style="color:#7c3aed;cursor:pointer;text-decoration:underline">Resend OTP</span>
                  </div>
                </div>
                <div id="regOtpVerifiedBadge" style="display:none;margin-top:8px;background:#f0fdf4;border:1.5px solid #16a34a;border-radius:8px;padding:7px 10px;color:#166534;font-size:12px;font-weight:700">
                  <i class="fas fa-check-circle" style="margin-right:4px"></i>Phone verified ✓
                </div>
              </div>

              <!-- Email -->
              <div style="margin-bottom:12px">
                <label style="font-size:11px;font-weight:700;color:#6b7280;text-transform:uppercase;display:block;margin-bottom:5px">Email <span style="font-size:10px;color:#9ca3af;text-transform:none">(optional)</span></label>
                <input type="email" id="regEmail" placeholder="email@example.com"
                  style="width:100%;padding:8px 10px;border:1.5px solid #e5e7eb;border-radius:8px;font-size:13px;box-sizing:border-box">
              </div>

              <!-- Password -->
              <div style="margin-bottom:12px">
                <label style="font-size:11px;font-weight:700;color:#6b7280;text-transform:uppercase;display:block;margin-bottom:5px">Password <span style="color:#e11d48">*</span></label>
                <input type="text" id="regPassword" placeholder="Set initial password" required
                  style="width:100%;padding:8px 10px;border:1.5px solid #e5e7eb;border-radius:8px;font-size:13px;box-sizing:border-box">
              </div>

              <!-- Referrer -->
              <div style="margin-bottom:16px">
                <label style="font-size:11px;font-weight:700;color:#6b7280;text-transform:uppercase;display:block;margin-bottom:5px">Referrer Channel Partner ID</label>
                <input type="text" id="regReferrer" placeholder="Pre-filled with your ID" value="${t}"
                  style="width:100%;padding:8px 10px;border:1.5px solid #e5e7eb;border-radius:8px;font-size:13px;box-sizing:border-box" autocomplete="off">
                <div id="regReferrerName" style="font-size:12px;margin-top:5px;min-height:16px"></div>
                <div style="font-size:11px;color:#9ca3af;margin-top:2px">By default you are the referrer. Change to place under someone else.</div>
              </div>

              <!-- Submit -->
              <button type="submit" id="regSubmitBtn"
                style="width:100%;background:linear-gradient(135deg,#4c1d95,#7c3aed);border:none;color:#fff;font-weight:700;font-size:14px;padding:12px;border-radius:10px;cursor:pointer">
                <span id="regSubmitText"><i class="fas fa-user-plus" style="margin-right:6px"></i>Register Channel Partner</span>
                <span id="regSubmitSpinner" style="display:none"><i class="fas fa-spinner fa-spin" style="margin-right:6px"></i>Registering…</span>
              </button>
            </form>
          </div>
        </div>

        <!-- List -->
        <div style="padding:0 12px" id="myRegList">
          <div style="text-align:center;padding:40px;color:#9ca3af">
            <i class="fas fa-spinner fa-spin" style="font-size:22px"></i>
          </div>
        </div>
      </div>`,c.attachListeners({title:"My VGK Registrations",showBack:!0})}attachEvents(){this.container.querySelector("#regOpenBtn")?.addEventListener("click",()=>{const e=this.container.querySelector("#regFormCard");e&&(e.style.display="block",e.scrollIntoView({behavior:"smooth",block:"start"}))}),this.container.querySelector("#regCloseBtn")?.addEventListener("click",()=>{this.closeRegForm()}),this.container.querySelector("#regAnotherBtn")?.addEventListener("click",()=>{this.resetRegForm()}),this.container.querySelector("#regShareBtn")?.addEventListener("click",()=>{this.lastRegData&&this.showShareOverlay(this.lastRegData)}),this.container.querySelector("#regReferrer")?.addEventListener("input",()=>this.lookupReferrer()),this.container.querySelector("#regReferrer")?.value&&this.lookupReferrer(),this.container.querySelector("#regPhone")?.addEventListener("input",()=>this.resetOtpState()),this.container.querySelector("#regSendOtpBtn")?.addEventListener("click",()=>this.sendOTP()),this.container.querySelector("#regVerifyBtn")?.addEventListener("click",()=>this.verifyOTP()),this.container.querySelector("#regResendLink")?.addEventListener("click",()=>this.sendOTP()),this.container.querySelector("#regForm")?.addEventListener("submit",e=>{e.preventDefault(),this.submitRegistration()})}lookupReferrer(){const e=this.container.querySelector("#regReferrer"),t=this.container.querySelector("#regReferrerName");if(!t)return;const i=(e?.value||"").trim().toUpperCase();if(this.refLookupTimer&&clearTimeout(this.refLookupTimer),i.length<3){t.innerHTML="";return}t.innerHTML='<span style="color:#9ca3af"><i class="fas fa-spinner fa-spin" style="margin-right:4px"></i>Looking up…</span>',this.refLookupTimer=setTimeout(async()=>{try{const a=await m.get(`/vgk/public/member-lookup?q=${encodeURIComponent(i)}`);if(a.results&&a.results.length>0){const n=a.results.find(r=>r.partner_code.toUpperCase()===i)||a.results[0];t.innerHTML=`<span style="color:#16a34a;font-weight:700"><i class="fas fa-check-circle" style="margin-right:4px"></i>${n.partner_name} <span style="color:#9ca3af;font-weight:400">(${n.partner_code})</span></span>`}else t.innerHTML='<span style="color:#dc2626"><i class="fas fa-times-circle" style="margin-right:4px"></i>VGK ID not found</span>'}catch{t.innerHTML='<span style="color:#dc2626"><i class="fas fa-times-circle" style="margin-right:4px"></i>VGK ID not found</span>'}},500)}resetOtpState(){this.regOtpSent=!1,this.regPhoneVerifiedToken="";const e=a=>this.container.querySelector(`#${a}`),t=this.container.querySelector("#regOtpInput"),i=this.container.querySelector("#regSendOtpBtn");e("regOtpBlock")&&(e("regOtpBlock").style.display="none"),e("regOtpVerifiedBadge")&&(e("regOtpVerifiedBadge").style.display="none"),t&&(t.value=""),i&&(i.textContent="Send OTP")}async sendOTP(){const e=this.container.querySelector("#regPhone"),t=this.container.querySelector("#regError"),i=(e?.value||"").trim();if(!i||!/^\d{10}$/.test(i)){t.textContent="Please enter a valid 10-digit phone number before sending OTP.",t.style.display="block";return}t.style.display="none";const a=this.container.querySelector("#regSendOtpBtn");a.disabled=!0,a.textContent="Sending…";try{const n=await m.post("/vgk/auth/signup/send-otp",{phone:i});if(n.success){this.regOtpSent=!0;const r=this.container.querySelector("#regOtpBlock"),o=this.container.querySelector("#regOtpVerifiedBadge"),s=this.container.querySelector("#regOtpInput");r&&(r.style.display="block"),o&&(o.style.display="none"),s&&(s.value="",s.focus()),this.regPhoneVerifiedToken="",a.textContent="Resend OTP"}else t.textContent=n.message||"Failed to send OTP. Please try again.",t.style.display="block",a.textContent="Send OTP"}catch(n){t.textContent=n?.detail||n?.message||"Failed to send OTP. Please try again.",t.style.display="block",a.textContent="Send OTP"}finally{a.disabled=!1}}async verifyOTP(){const e=this.container.querySelector("#regPhone"),t=this.container.querySelector("#regOtpInput"),i=this.container.querySelector("#regError"),a=(e?.value||"").trim(),n=(t?.value||"").trim();if(!n||n.length!==6){i.textContent="Please enter the 6-digit OTP from WhatsApp.",i.style.display="block";return}i.style.display="none";const r=this.container.querySelector("#regVerifyBtn");r.disabled=!0,r.textContent="Verifying…";try{const o=await m.post("/vgk/auth/signup/verify-otp",{phone:a,otp_code:n});if(o.success&&o.phone_verified_token){this.regPhoneVerifiedToken=o.phone_verified_token;const s=this.container.querySelector("#regOtpBlock"),l=this.container.querySelector("#regOtpVerifiedBadge");s&&(s.style.display="none"),l&&(l.style.display="block")}else i.textContent=o.message||"Invalid OTP. Please try again.",i.style.display="block"}catch(o){i.textContent=o?.detail||o?.message||"Invalid OTP. Please try again.",i.style.display="block"}finally{r.disabled=!1,r.textContent="Verify"}}async submitRegistration(){const e=h=>this.container.querySelector(`#${h}`)?.value?.trim()||"",t=this.container.querySelector("#regError");t.style.display="none";const i=e("regFirstName"),a=e("regLastName"),n=e("regPhone"),r=e("regPassword"),o=e("regTitle"),s=e("regGender"),l=e("regEmail"),p=e("regReferrer"),f=[o,i,a].filter(Boolean).join(" ");if(!i||!a){t.textContent="Please enter both first name and last name.",t.style.display="block";return}if(!n||n.length<10){t.textContent="Please enter a valid 10-digit phone number.",t.style.display="block";return}if(!this.regPhoneVerifiedToken){t.textContent='Phone verification required — enter the phone number, tap "Send OTP", enter the code from WhatsApp, then tap "Verify".',t.style.display="block";return}if(!r||r.length<6){t.textContent="Password must be at least 6 characters.",t.style.display="block";return}const u=this.container.querySelector("#regSubmitBtn"),x=this.container.querySelector("#regSubmitText"),w=this.container.querySelector("#regSubmitSpinner");u.disabled=!0,x.style.display="none",w.style.display="";try{const h={partner_name:f,phone:n,password:r,name_title:o||null,first_name:i||null,last_name:a||null,gender:s||null,phone_verified_token:this.regPhoneVerifiedToken};l&&(h.email=l),p&&(h.referrer_code=p);const _=await m.post("/vgk/auth/signup",h);if(_.success){const L=this.container.querySelector("#regForm"),A=this.container.querySelector("#regSuccess"),R=this.container.querySelector("#regNewId");L&&(L.style.display="none"),R&&(R.textContent=_.partner_code||""),A&&(A.style.display="block"),this.lastRegData={partner_code:_.partner_code||"",partner_name:f,phone:n,password:r},this.showShareOverlay(this.lastRegData),await this.loadData()}else t.textContent=_.message||"Registration failed. Please try again.",t.style.display="block"}catch(h){t.textContent=h?.detail||h?.message||"Registration failed. Please try again.",t.style.display="block"}finally{u.disabled=!1,x.style.display="",w.style.display="none"}}buildShareMsg(e,t){const i=t.partner_code,a=t.partner_name,n=t.password,r=`https://vgk4u.com/vgk/login?tab=signup&ref=${encodeURIComponent(i)}`,o="https://www.youtube.com/@VGK4YOU";return e==="hindi"?`🎉 बधाई हो ${a} जी! 🎉

VGK4U में आपका स्वागत है! आपके खाते में कुल 15,000 रिवॉर्ड पॉइंट्स जमा हो गए हैं:
🎁 10,000 पॉइंट्स — वेलकम बोनस
🤝 5,000 पॉइंट्स — रेफरल बोनस

इन पॉइंट्स को इन सेवाओं पर उपयोग करें:
⚡ Solar Solutions
🛵 EV (इलेक्ट्रिक वाहन)
🛡 Insurance
🏡 Real Estate और अन्य VGK सेवाएं

लॉगिन विवरण:
🌐 Website: www.vgk4u.com
👤 Username: ${i}
🔐 Password: ${n}
🔗 आपका Referral Link:
${r}

▶️ पूरी कमाई प्रक्रिया समझने के लिए हमारा YouTube channel देखें:
${o}

👉 नियमित अपडेट और training के लिए subscribe करें।

अपना dashboard explore करें और अपने rewards का पूरा लाभ उठाएं!`:e==="telugu"?`🎉 అభినందనలు ${a} గారు! 🎉

VGK4U లో స్వాగతం! మీ ఖాతాలో మొత్తం 15,000 రివార్డ్ పాయింట్లు జమ అయ్యాయి:
🎁 10,000 పాయింట్లు — వెల్కమ్ బోనస్
🤝 5,000 పాయింట్లు — రెఫెరల్ బోనస్

ఈ పాయింట్లను ఉపయోగించవచ్చు:
⚡ Solar Solutions
🛵 EV (ఎలక్ట్రిక్ వాహనాలు)
🛡 Insurance
🏡 Real Estate మరియు ఇతర VGK సేవలు

లాగిన్ వివరాలు:
🌐 Website: www.vgk4u.com
👤 Username: ${i}
🔐 Password: ${n}
🔗 మీ Referral Link:
${r}

▶️ పూర్తి ఆదాయ ప్రక్రియ తెలుసుకోవడానికి మా YouTube చానల్ చూడండి:
${o}

👉 రెగ్యులర్ అప్డేట్స్, ట్రైనింగ్ కోసం సబ్స్క్రైబ్ చేయండి.

మీ డాష్బోర్డ్ అన్వేషించండి మరియు మీ రివార్డ్స్ ను సద్వినియోగం చేసుకోండి!`:e==="tamil"?`🎉 வாழ்த்துகள் ${a}! 🎉

VGK4U-வில் உங்களை வரவேற்கிறோம்! உங்கள் கணக்கில் மொத்தம் 15,000 வெகுமதி புள்ளிகள் சேர்க்கப்பட்டுள்ளன:
🎁 10,000 புள்ளிகள் — வரவேற்பு போனஸ்
🤝 5,000 புள்ளிகள் — பரிந்துரை போனஸ்

இந்த புள்ளிகளை பயன்படுத்தலாம்:
⚡ Solar Solutions
🛵 EV (மின்சார வாகனங்கள்)
🛡 Insurance
🏡 Real Estate மற்றும் மற்ற VGK சேவைகள்

உள்நுழைவு விவரங்கள்:
🌐 Website: www.vgk4u.com
👤 Username: ${i}
🔐 Password: ${n}
🔗 உங்கள் Referral Link:
${r}

▶️ முழு வருமான செயல்முறையை புரிந்துகொள்ள எங்கள் YouTube சேனலை பாருங்கள்:
${o}

👉 தொடர் புதுப்பிப்புகள் மற்றும் பயிற்சிக்கு subscribe செய்யுங்கள்.

உங்கள் dashboard-ஐ ஆராய்ந்து உங்கள் வெகுமதிகளை சரியாக பயன்படுத்துங்கள்!`:e==="kannada"?`🎉 ಅಭಿನಂದನೆಗಳು ${a}! 🎉

VGK4U ಗೆ ಸ್ವಾಗತ! ನಿಮ್ಮ ಖಾತೆಗೆ ಒಟ್ಟು 15,000 ರಿವಾರ್ಡ್ ಪಾಯಿಂಟ್‌ಗಳು ಸೇರ್ಪಡೆಯಾಗಿವೆ:
🎁 10,000 ಪಾಯಿಂಟ್‌ಗಳು — ವೆಲ್ಕಮ್ ಬೋನಸ್
🤝 5,000 ಪಾಯಿಂಟ್‌ಗಳು — ರೆಫೆರಲ್ ಬೋನಸ್

ಈ ಪಾಯಿಂಟ್‌ಗಳನ್ನು ಬಳಸಬಹುದು:
⚡ Solar Solutions
🛵 EV (ಎಲೆಕ್ಟ್ರಿಕ್ ವಾಹನಗಳು)
🛡 Insurance
🏡 Real Estate ಮತ್ತು ಇತರ VGK ಸೇವೆಗಳು

ಲಾಗಿನ್ ವಿವರಗಳು:
🌐 Website: www.vgk4u.com
👤 Username: ${i}
🔐 Password: ${n}
🔗 ನಿಮ್ಮ Referral Link:
${r}

▶️ ಸಂಪೂರ್ಣ ಗಳಿಕೆ ಪ್ರಕ್ರಿಯೆ ಅರ್ಥಮಾಡಿಕೊಳ್ಳಲು ನಮ್ಮ YouTube ಚಾನೆಲ್ ನೋಡಿ:
${o}

👉 ನಿಯಮಿತ ಅಪ್‌ಡೇಟ್‌ಗಳು ಮತ್ತು ತರಬೇತಿಗಾಗಿ subscribe ಮಾಡಿ.

ನಿಮ್ಮ dashboard ಅನ್ವೇಷಿಸಿ ಮತ್ತು ನಿಮ್ಮ ರಿವಾರ್ಡ್‌ಗಳನ್ನು ಉತ್ತಮವಾಗಿ ಬಳಸಿ!`:`🎉 Congratulations ${a}! 🎉

Welcome to VGK4U! A total of 15,000 reward points have been credited to your account:
🎁 10,000 pts — Welcome Bonus
🤝 5,000 pts — Referral Bonus (joined via a member's referral)

Use your points on:
⚡ Solar Solutions
🛵 EV (Electric Vehicles)
🛡 Insurance
🏡 Real Estate and other VGK services

Your login details:
🌐 Website: www.vgk4u.com
👤 Username: ${i}
🔐 Password: ${n}
🔗 Your Referral Link:
${r}

▶️ To understand the full earning process and how to use your benefits, watch our official YouTube channel:
${o}

👉 Make sure to subscribe for regular updates, training, and income strategies.

Start exploring your dashboard and make the most out of your rewards and opportunities!`}showShareOverlay(e){const t=document.getElementById("vgkMobShareOverlay");t&&t.remove();const i=s=>s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;"),a=e.phone.replace(/\D/g,""),n=a.length===10?"91"+a:a,r=document.createElement("div");r.id="vgkMobShareOverlay",r.style.cssText="position:fixed;inset:0;background:rgba(0,0,0,.65);z-index:99999;display:flex;align-items:flex-end;justify-content:center",r.innerHTML=`
      <div style="background:#fff;border-radius:20px 20px 0 0;width:100%;max-height:92vh;overflow-y:auto;padding:20px 16px 32px">
        <div style="text-align:center;margin-bottom:14px">
          <div style="width:40px;height:4px;background:#e5e7eb;border-radius:4px;margin:0 auto 14px"></div>
          <div style="font-size:26px">🎉</div>
          <h5 style="font-weight:800;color:#4c1d95;margin:6px 0 2px;font-size:17px">VGK4U Account Created!</h5>
          <p style="font-size:12px;color:#6b7280;margin:0">Share login details with the new member</p>
        </div>

        <!-- Details card -->
        <div style="background:#f5f3ff;border:1.5px solid #ddd6fe;border-radius:12px;padding:12px 14px;margin-bottom:14px">
          <div style="display:flex;justify-content:space-between;margin-bottom:6px">
            <span style="font-size:12px;color:#6b7280">Name</span>
            <strong style="font-size:13px;color:#1f2937">${i(e.partner_name)}</strong>
          </div>
          <div style="display:flex;justify-content:space-between;margin-bottom:6px">
            <span style="font-size:12px;color:#6b7280">VGK4U ID</span>
            <strong style="font-size:13px;color:#7c3aed">${i(e.partner_code)}</strong>
          </div>
          <div style="display:flex;justify-content:space-between;margin-bottom:6px">
            <span style="font-size:12px;color:#6b7280">Phone</span>
            <strong style="font-size:13px;color:#1f2937">${i(e.phone)}</strong>
          </div>
          <div style="display:flex;justify-content:space-between">
            <span style="font-size:12px;color:#6b7280">Password</span>
            <strong style="font-size:13px;color:#059669;font-family:monospace">${i(e.password)}</strong>
          </div>
        </div>

        <!-- Language + message -->
        <div style="margin-bottom:12px">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
            <label style="font-size:12px;font-weight:700;color:#374151">Share Message</label>
            <select id="vgkMobShareLang" style="font-size:12px;border:1px solid #ddd;border-radius:6px;padding:4px 8px">
              <option value="english">English</option>
              <option value="hindi">हिंदी</option>
              <option value="telugu">తెలుగు</option>
              <option value="tamil">தமிழ்</option>
              <option value="kannada">ಕನ್ನಡ</option>
            </select>
          </div>
          <textarea id="vgkMobShareMsg" rows="8" style="width:100%;font-size:12.5px;border:1.5px solid #ddd6fe;border-radius:8px;padding:10px;resize:vertical;font-family:inherit;line-height:1.55;box-sizing:border-box"></textarea>
        </div>

        <!-- Action buttons -->
        <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px">
          <button id="vgkMobShareCopyBtn" style="flex:1;min-width:80px;padding:11px 8px;border:1.5px solid #7c3aed;background:#fff;color:#7c3aed;border-radius:10px;font-weight:700;font-size:13px;cursor:pointer">
            <i class="fas fa-copy me-1"></i>Copy
          </button>
          <button id="vgkMobShareWABtn" style="flex:2;min-width:140px;padding:11px 8px;background:#25D366;color:#fff;border:none;border-radius:10px;font-weight:700;font-size:13px;cursor:pointer">
            <i class="fab fa-whatsapp me-1"></i>Share on WhatsApp
          </button>
        </div>
        <button id="vgkMobShareCloseBtn" style="width:100%;padding:10px;background:#f3f4f6;color:#374151;border:none;border-radius:10px;font-weight:700;font-size:13px;cursor:pointer">
          Close
        </button>
      </div>`,document.body.appendChild(r);const o=document.getElementById("vgkMobShareMsg");o.value=this.buildShareMsg("english",e),document.getElementById("vgkMobShareLang")?.addEventListener("change",s=>{o.value=this.buildShareMsg(s.target.value,e)}),document.getElementById("vgkMobShareCopyBtn")?.addEventListener("click",()=>{const s=o.value,l=document.getElementById("vgkMobShareCopyBtn");navigator.clipboard?navigator.clipboard.writeText(s).then(()=>{const p=l.innerHTML;l.innerHTML='<i class="fas fa-check me-1"></i>Copied!',l.style.background="#ede9fe",setTimeout(()=>{l.innerHTML=p,l.style.background="#fff"},2e3)}):prompt("Copy this message:",s)}),document.getElementById("vgkMobShareWABtn")?.addEventListener("click",()=>{const s=o.value,l=n?`https://wa.me/${n}?text=${encodeURIComponent(s)}`:`https://wa.me/?text=${encodeURIComponent(s)}`;window.open(l,"_blank")}),document.getElementById("vgkMobShareCloseBtn")?.addEventListener("click",()=>r.remove()),r.addEventListener("click",s=>{s.target===r&&r.remove()})}closeRegForm(){const e=this.container.querySelector("#regFormCard");e&&(e.style.display="none"),this.resetRegForm()}resetRegForm(){const e=this.container.querySelector("#regForm"),t=this.container.querySelector("#regSuccess"),i=this.container.querySelector("#regError");e&&(e.reset(),e.style.display=""),t&&(t.style.display="none"),i&&(i.style.display="none"),this.resetOtpState();const a=JSON.parse(localStorage.getItem("vgk_partner")||"{}"),n=this.container.querySelector("#regReferrer");n&&a.partner_code&&(n.value=a.partner_code)}updateStats(){const e=this.container.querySelector("#statTotal"),t=this.container.querySelector("#statThisMonth");e&&(e.textContent=String(this.total)),t&&(t.textContent=String(this.thisMonth))}updateList(){const e=this.container.querySelector("#myRegList");if(e){if(this.loading){e.innerHTML='<div style="text-align:center;padding:40px;color:#9ca3af"><i class="fas fa-spinner fa-spin" style="font-size:22px"></i></div>';return}if(this.members.length===0){e.innerHTML=`<div style="text-align:center;padding:40px;color:#9ca3af">
        <i class="fas fa-user-plus" style="font-size:28px;margin-bottom:8px;display:block"></i>
        <div style="font-size:14px">No registrations yet.<br>Tap <b>Register</b> above to add a new Channel Partner.</div>
      </div>`;return}e.innerHTML=this.members.map(t=>`
      <div style="background:white;border-radius:12px;padding:14px 16px;margin-bottom:10px;box-shadow:0 1px 4px rgba(0,0,0,.07)">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px">
          <div>
            <span style="font-family:monospace;font-size:11px;font-weight:700;color:#7c3aed;background:#ede9fe;padding:2px 7px;border-radius:5px">${t.partner_code||"—"}</span>
            <span style="margin-left:8px;font-size:13px;font-weight:700;color:#111827">${t.partner_name||"—"}</span>
          </div>
          <span style="font-size:11px;font-weight:700;padding:2px 8px;border-radius:20px;${t.is_active?"background:#d1fae5;color:#065f46":"background:#fee2e2;color:#991b1b"}">${t.is_active?"Active":"Inactive"}</span>
        </div>
        <div style="display:flex;gap:16px;font-size:11.5px;color:#6b7280">
          <span><i class="fas fa-phone" style="margin-right:4px;color:#9ca3af"></i>${t.phone||"—"}</span>
          <span><i class="fas fa-calendar-alt" style="margin-right:4px;color:#9ca3af"></i>Reg: ${this.fmtDate(t.created_at)}</span>
        </div>
      </div>`).join("")}}}const M=[{key:"all",label:"All",icon:"fas fa-th-large"},{key:"active",label:"Active",icon:"fas fa-fire"},{key:"claim",label:"Claim Now",icon:"fas fa-gift"},{key:"won",label:"Won",icon:"fas fa-trophy"},{key:"claimed_proc",label:"Claimed",icon:"fas fa-check-circle"},{key:"upcoming",label:"Upcoming",icon:"fas fa-calendar-alt"},{key:"missed",label:"Missed",icon:"fas fa-times-circle"},{key:"inactive",label:"Inactive",icon:"fas fa-pause-circle"}],P=["Claimed","Achieved - Claimed","Processing","Staff Verified","Procurement In Progress","Dispatched","Delivered","Completed","Payment Released","Paid"],I={completed_deals:"linear-gradient(135deg,#4c1d95,#7c3aed)",solar:"linear-gradient(135deg,#92400e,#d97706)",direct_referral:"linear-gradient(135deg,#1e3a5f,#2563eb)",matching_points:"linear-gradient(135deg,#065f46,#059669)",team_size:"linear-gradient(135deg,#7c2d12,#ea580c)"},C={completed_deals:"fas fa-handshake",solar:"fas fa-solar-panel",direct_referral:"fas fa-user-plus",matching_points:"fas fa-sync",team_size:"fas fa-users"};function b(d){return String(d??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;")}function k(d){if(!d)return"—";const e=d.endsWith("Z")||d.includes("+")?d:d+"+05:30";return new Date(e).toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"2-digit",timeZone:"Asia/Kolkata"})}function D(d,e){return e?"linear-gradient(135deg,#374151,#6b7280)":I[d??""]??"linear-gradient(135deg,#312e81,#6d28d9)"}class ie{container;all=[];rewardFiles=[];filter="active";loading=!0;error="";constructor(e){this.container=e}async init(){this.render(),await this.load()}async load(e=!1){this.loading=!0,this.error="",this.refreshContent();try{const[t,i]=await Promise.all([m.get("/bonanza/my-bonanzas"),m.get("/bonanza/my-reward-files")]);t.success&&t.data?this.all=t.data.bonanzas||[]:this.all=[],this.rewardFiles=i.data?.files||[]}catch{this.error="Could not load bonanza rewards. Please try again.",this.all=[],this.rewardFiles=[]}this.loading=!1,this.refreshContent()}render(){this.container.innerHTML=`
      <style>
        .bnz-filter-bar{display:flex;gap:8px;flex-wrap:nowrap;overflow-x:auto;padding:0 12px 6px;-webkit-overflow-scrolling:touch;scrollbar-width:none}
        .bnz-filter-bar::-webkit-scrollbar{display:none}
        .bnz-fc{flex-shrink:0;background:#f5f3ff;border:1.5px solid #ddd6fe;color:#6d28d9;border-radius:20px;padding:6px 14px;font-size:12px;font-weight:700;cursor:pointer;white-space:nowrap}
        .bnz-fc.active{background:linear-gradient(135deg,#7c3aed,#6d28d9);border-color:#7c3aed;color:#fff;box-shadow:0 2px 8px rgba(124,58,237,.4)}
        /* Dark offer card */
        .bnz-card{background:#111827;border-radius:18px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,.25);margin:0 12px 18px}
        .bnz-card.bnz-missed{opacity:.72}
        /* Image: full image, no crop */
        .bnz-img{position:relative;background:#0f0f1a;display:flex;align-items:center;justify-content:center;overflow:hidden;min-height:180px}
        .bnz-img::after{content:'';position:absolute;bottom:0;left:0;right:0;height:60px;background:linear-gradient(to top,rgba(0,0,0,.75),transparent);pointer-events:none}
        .bnz-img img{width:100%;height:auto;max-height:260px;object-fit:contain;display:block}
        .bnz-img-ph{width:100%;min-height:180px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10px;color:rgba(255,255,255,.8);font-size:13px;font-weight:800;padding:28px 16px}
        .bnz-img-ph i{font-size:42px;opacity:.85}
        /* Overlays: bottom of image above the gradient */
        .bnz-sov{position:absolute;bottom:10px;left:10px;z-index:2}
        .bnz-rov{position:absolute;bottom:10px;right:10px;z-index:2;text-align:right}
        /* Status chips */
        .bnz-chip{display:inline-flex;align-items:center;gap:5px;padding:5px 12px;border-radius:20px;font-size:11px;font-weight:800}
        .bnz-chip-prog{background:#2563eb;color:#fff}
        .bnz-chip-claim{background:linear-gradient(135deg,#7c3aed,#a855f7);color:#fff;box-shadow:0 0 10px rgba(124,58,237,.6)}
        .bnz-chip-ach{background:#16a34a;color:#fff}
        .bnz-chip-up{background:#d97706;color:#fff}
        .bnz-chip-miss{background:#dc2626;color:#fff}
        .bnz-chip-clmd{background:#6d28d9;color:#fff}
        .bnz-chip-dlv{background:#059669;color:#fff}
        /* Reward badge */
        .bnz-rbadge{padding:6px 12px;border-radius:11px;font-weight:900;line-height:1.25;text-align:right}
        .bnz-rb-amt{font-size:17px}
        .bnz-rb-lbl{font-size:9px;opacity:.85;text-transform:uppercase;letter-spacing:.04em}
        .bnz-rbadge-cash{background:linear-gradient(135deg,#065f46,#059669);color:#fff;box-shadow:0 2px 8px rgba(5,150,105,.4)}
        .bnz-rbadge-free{background:linear-gradient(135deg,#92400e,#f59e0b);color:#fff;box-shadow:0 2px 8px rgba(245,158,11,.35)}
        /* Dark body */
        .bnz-body{padding:13px 14px 16px;background:#1a1a2e}
        .bnz-name{font-size:16px;font-weight:900;color:#fff;margin-bottom:5px;line-height:1.3}
        .bnz-meta{display:flex;flex-wrap:wrap;gap:6px;font-size:11px;color:#9ca3af;margin-bottom:10px;align-items:center}
        .bnz-seg{background:rgba(124,58,237,.3);color:#c4b5fd;border-radius:6px;padding:2px 7px;font-weight:700;font-size:10px;border:1px solid rgba(124,58,237,.35)}
        .bnz-pb-bg{background:rgba(255,255,255,.1);border-radius:99px;height:8px;overflow:hidden;margin:5px 0 4px}
        .bnz-pb-fill{height:100%;border-radius:99px;transition:width .4s}
        .bnz-footer{display:flex;gap:10px;flex-wrap:wrap;font-size:11px;color:#6b7280;margin-top:10px;padding-top:10px;border-top:1px solid rgba(255,255,255,.07)}
        .bnz-tier-row{border-radius:9px;overflow:hidden;margin-bottom:6px;border:1px solid rgba(255,255,255,.08)}
        .bnz-tier-row.active{border-color:rgba(124,58,237,.55);background:rgba(124,58,237,.1)}
        .bnz-tier-h{padding:7px 10px;display:flex;justify-content:space-between;align-items:center}
        .bnz-tier-bar{height:5px;background:rgba(255,255,255,.07)}
      </style>
      <div class="page-container">
        ${c.render({title:"Bonanza Rewards",showBack:!0})}
        <div style="margin-bottom:12px">
          <div class="bnz-filter-bar" id="bnzFilterBar">
            ${M.map(e=>`<button class="bnz-fc${e.key==="all"?" active":""}" data-filter="${e.key}"><i class="${e.icon} me-1"></i>${e.label}</button>`).join("")}
          </div>
        </div>
        <div id="bnzContent">
          <div style="padding:40px;text-align:center;color:#9ca3af"><i class="fas fa-spinner fa-spin fa-2x"></i></div>
        </div>
        <div style="height:24px"></div>
      </div>
    `,c.attachListeners({title:"Bonanza Rewards",showBack:!0}),document.getElementById("bnzFilterBar")?.addEventListener("click",e=>{const t=e.target.closest("[data-filter]");t&&(document.querySelectorAll(".bnz-fc").forEach(i=>i.classList.remove("active")),t.classList.add("active"),t.scrollIntoView({behavior:"smooth",block:"nearest",inline:"center"}),this.filter=t.dataset.filter||"all",this.refreshContent())})}statusChip(e){const t=(e.status||"").toLowerCase(),i=(e.processed_status||"").toLowerCase();return i==="delivered"?'<span class="bnz-chip bnz-chip-dlv"><i class="fas fa-check-circle me-1"></i>Delivered</span>':i==="dispatched"?'<span class="bnz-chip bnz-chip-dlv"><i class="fas fa-truck me-1"></i>Dispatched</span>':i&&i!=="pending"&&!t.includes("progress")&&!t.includes("claim")&&!t.includes("upcoming")&&!t.includes("missed")?`<span class="bnz-chip bnz-chip-clmd"><i class="fas fa-hourglass-half me-1"></i>${b(e.processed_status)}</span>`:t.includes("claim now")?'<span class="bnz-chip bnz-chip-claim"><i class="fas fa-gift me-1"></i>Claim Now!</span>':t.includes("achieved")?'<span class="bnz-chip bnz-chip-ach"><i class="fas fa-trophy me-1"></i>Achieved</span>':t.includes("progress")?'<span class="bnz-chip bnz-chip-prog"><i class="fas fa-spinner fa-spin me-1"></i>In Progress</span>':t.includes("upcoming")?'<span class="bnz-chip bnz-chip-up"><i class="fas fa-calendar me-1"></i>Upcoming</span>':t.includes("missed")?'<span class="bnz-chip bnz-chip-miss"><i class="fas fa-times-circle me-1"></i>Missed</span>':`<span class="bnz-chip bnz-chip-prog">${b(e.status)}</span>`}rewardBadge(e){if(e.reward_type==="slab_wise"&&e.slab_extra_amount){const a=e.current_progress||1,n=Number(e.slab_extra_amount)*a,r=Number(e.slab_extra_amount).toLocaleString("en-IN"),o=a>1?`${a} files × ₹${r}`:"per deal";return`<div class="bnz-rbadge bnz-rbadge-cash"><div class="bnz-rb-amt">+₹${n.toLocaleString("en-IN")}</div><div class="bnz-rb-lbl">${o}</div></div>`}if(e.is_monetary&&e.reward_amount)return`<div class="bnz-rbadge bnz-rbadge-cash"><div class="bnz-rb-amt">₹${Number(e.reward_amount).toLocaleString("en-IN")}</div><div class="bnz-rb-lbl">Cash Prize</div></div>`;const t=e.award_name||e.reward_text||"Free Award",i=t.length>16?t.substring(0,14)+"…":t;return`<div class="bnz-rbadge bnz-rbadge-free"><div class="bnz-rb-lbl" style="font-size:11px;font-weight:900">FREE</div><div class="bnz-rb-amt" style="font-size:13px">${b(i)}</div></div>`}filtered(){return this.filter==="all"?this.all:this.all.filter(e=>{const t=e.status||"";return this.filter==="active"?t==="In Progress":this.filter==="claim"?t==="Achieved - Claim Now":this.filter==="won"?t==="Achieved - Claim Now"||P.some(i=>t.includes(i)):this.filter==="claimed_proc"?P.some(i=>t.includes(i)):this.filter==="upcoming"?t==="Upcoming":this.filter==="missed"?t==="Missed Opportunity":this.filter==="inactive"?t==="Upcoming"||t==="Missed Opportunity":!1})}cardHtml(e){const t=e.achievement_percentage||0,i=t>=100?"#22c55e":t>=60?"#f59e0b":"#7c3aed",a=C[e.criteria_type??""]??"fas fa-trophy",n=(e.status||"").includes("Missed"),r=D(e.criteria_type,n);e.status==="Achieved - Claim Now"&&e.slots_full;const o=e.image_url?`<img src="${b(e.image_url)}" alt="${b(e.name)}" onerror="this.outerHTML='<div class=\\'bnz-img-ph\\' style=\\'${r.replace(/'/g,"\\'")}\\'>'+
         '<i class=\\'${a}\\'></i><span>${b(e.name)}</span></div>'">`:`<div class="bnz-img-ph" style="${r}"><i class="${a}"></i><span>${b(e.name)}</span></div>`,s=e.registered_target_bonus&&e.registered_target&&e.activated_target;let l="";if(s){const f=!!e.partner_is_activated,u=f?Math.min(100,Math.round((e.current_progress??0)/e.registered_target*100)):t,x=f?t:0;l=`
        <div class="bnz-tier-row${f?"":" active"}">
          <div class="bnz-tier-h">
            <span style="font-size:10px;font-weight:700;color:${f?"#6b7280":"#c4b5fd"}"><i class="fas fa-id-card me-1"></i>Registered${f?"":' <span style="background:#7c3aed;color:#fff;border-radius:7px;padding:1px 5px;font-size:8px">CURRENT</span>'}</span>
            <span style="font-size:11px;font-weight:800;color:${f?"#6b7280":i}">${e.current_progress??0}/${e.registered_target} (${u}%)</span>
          </div>
          <div class="bnz-tier-bar"><div style="height:100%;width:${f?u:t}%;background:${i};transition:width .4s"></div></div>
        </div>
        <div class="bnz-tier-row${f?" active":""}">
          <div class="bnz-tier-h">
            <span style="font-size:10px;font-weight:700;color:${f?"#c4b5fd":"#6b7280"}"><i class="fas fa-bolt me-1"></i>Activated${f?' <span style="background:#7c3aed;color:#fff;border-radius:7px;padding:1px 5px;font-size:8px">CURRENT</span>':'<span style="font-size:8px;color:#6b7280"> (activate to unlock)</span>'}</span>
            <span style="font-size:11px;font-weight:800;color:${f?i:"#6b7280"}">${f?(e.current_progress??0)+"/"+e.activated_target+" ("+x+"%)":e.activated_target+" deals"}</span>
          </div>
          ${f?`<div class="bnz-tier-bar"><div style="height:100%;width:${t}%;background:${i};transition:width .4s"></div></div>`:""}
        </div>
        ${f?"":`<div style="background:rgba(245,158,11,.15);border:1px solid rgba(245,158,11,.3);border-radius:8px;padding:6px 10px;font-size:10px;color:#fcd34d;margin-top:4px"><i class="fas fa-lightbulb me-1"></i>Activate to cut target <strong>${e.registered_target}</strong> → <strong>${e.activated_target}</strong> deals</div>`}`}else l=`
        <div style="display:flex;justify-content:space-between;align-items:center;font-size:12px;font-weight:700;margin-bottom:5px">
          <span style="color:#d1d5db"><i class="fas fa-handshake me-1" style="color:${i}"></i>${e.current_progress??0} / ${e.target_requirement??"—"} deals</span>
          <span style="color:${i};font-size:14px;font-weight:900">${t}%</span>
        </div>
        <div class="bnz-pb-bg"><div class="bnz-pb-fill" style="width:${t}%;background:${i}"></div></div>`;const p=e.slots_full&&e.status==="Achieved - Claim Now"?'<div style="text-align:center;background:rgba(220,38,38,.2);border:1px solid rgba(220,38,38,.35);border-radius:9px;padding:10px;font-size:12px;color:#fca5a5;margin-top:10px;font-weight:700"><i class="fas fa-times-circle me-1"></i>All slots filled — contact support</div>':"";return`
      <div class="bnz-card${n?" bnz-missed":""}" data-status="${b(e.status)}">
        <div class="bnz-img">
          ${o}
          <div class="bnz-sov">${this.statusChip(e)}</div>
          <div class="bnz-rov">${this.rewardBadge(e)}</div>
        </div>
        <div class="bnz-body">
          <div class="bnz-name">${b(e.name)}</div>
          <div class="bnz-meta">
            ${e.segment_name?`<span class="bnz-seg"><i class="fas fa-tag me-1"></i>${b(e.segment_name)}</span>`:""}
            <span><i class="fas fa-calendar me-1"></i>${k(e.start_date)} → ${k(e.end_date)}</span>
            ${e.grace_days?`<span><i class="fas fa-clock me-1"></i>${e.grace_days}d grace</span>`:""}
          </div>
          <div style="margin-bottom:8px">${l}</div>
          <div class="bnz-footer">
            <span><i class="fas fa-users me-1"></i>${e.current_winners??0}/${e.max_winners??"—"} winners</span>
            <span><i class="fas fa-ticket-alt me-1"></i>${e.slots_remaining??0} slots left</span>
            ${e.claimed_date?`<span style="color:#34d399"><i class="fas fa-check me-1"></i>Claimed ${k(e.claimed_date)}</span>`:""}
          </div>
          ${p}
        </div>
      </div>`}refreshContent(){const e=document.getElementById("bnzContent");if(!e)return;if(this.loading){e.innerHTML='<div style="padding:48px;text-align:center;color:#9ca3af"><i class="fas fa-spinner fa-spin fa-2x"></i></div>';return}if(this.error){e.innerHTML=`
        <div style="margin:0 12px;background:#fee2e2;border-radius:12px;padding:14px;color:#991b1b;font-size:13px;display:flex;align-items:center;gap:10px">
          <i class="fas fa-exclamation-circle" style="font-size:18px"></i>
          <div style="flex:1">${this.error}</div>
          <button id="bnzRetry" style="background:#ef4444;color:#fff;border:none;border-radius:8px;padding:6px 12px;font-size:12px;font-weight:700;cursor:pointer">Retry</button>
        </div>`,document.getElementById("bnzRetry")?.addEventListener("click",()=>this.load(!0));return}const t=this.filtered(),i={active:"No active bonanzas right now.",claim:"No bonanzas ready to claim.",won:"No won bonanzas yet.",claimed_proc:"No claimed/processed bonanzas yet.",upcoming:"No upcoming bonanzas.",missed:"No missed bonanzas.",inactive:"No inactive bonanzas."};if(t.length===0){e.innerHTML=`
        <div style="padding:56px 20px;text-align:center;color:#9ca3af">
          <i class="fas fa-trophy" style="font-size:44px;opacity:.2;display:block;margin-bottom:14px"></i>
          <div style="font-size:15px;font-weight:700;margin-bottom:4px">No bonanzas found</div>
          <div style="font-size:12px">${i[this.filter]??"No bonanza campaigns match this filter."}</div>
        </div>`;return}const a=`
      <div style="display:flex;justify-content:flex-end;padding:0 12px 8px">
        <button id="bnzRefresh" style="background:none;border:1.5px solid #ddd6fe;border-radius:8px;padding:6px 12px;font-size:12px;font-weight:700;color:#7c3aed;cursor:pointer">
          <i class="fas fa-sync me-1"></i>Refresh
        </button>
      </div>`;let n="";if(this.rewardFiles.length){const r={RELEASED:"color:#065f46;background:#d1fae5",ADJUSTED:"color:#1e40af;background:#dbeafe",RECOVERED:"color:#991b1b;background:#fee2e2",DEFICIT:"color:#991b1b;background:#fee2e2",PENDING:"color:#854d0e;background:#fef9c3"};n=`
        <div style="margin:16px 12px 0;background:#fff;border-radius:14px;border:1.5px solid #ddd6fe;overflow:hidden">
          <div style="padding:12px 14px;background:#faf5ff;border-bottom:1px solid #ede9fe">
            <div style="font-size:13px;font-weight:800;color:#5b21b6"><i class="fas fa-solar-panel" style="margin-right:6px"></i>Solar File Breakdown</div>
            <div style="font-size:11px;color:#7c3aed;margin-top:2px">Each file that qualified for your bonanza reward</div>
          </div>
          ${this.rewardFiles.map((s,l)=>{const p=r[s.advance_status]??"color:#374151;background:#f3f4f6",f=s.processed_status==="Paid"?'<span style="background:#d1fae5;color:#065f46;border-radius:20px;padding:2px 8px;font-size:10px;font-weight:700"><i class="fas fa-check-circle" style="margin-right:3px"></i>&#x20B9; Paid</span>':s.processed_status==="Payment Released"?'<span style="background:#dbeafe;color:#1d4ed8;border-radius:20px;padding:2px 8px;font-size:10px;font-weight:700"><i class="fas fa-clock" style="margin-right:3px"></i>Payment Approved</span>':s.processed_status==="Pending"||!s.processed_status?'<span style="background:#ede9fe;color:#5b21b6;border-radius:20px;padding:2px 8px;font-size:10px;font-weight:700">Pending Approval</span>':`<span style="background:#f3f4f6;color:#374151;border-radius:20px;padding:2px 8px;font-size:10px;font-weight:700">${b(s.processed_status)}</span>`,u=s.slab_extra_amount?`<strong style="color:#7c3aed">+&#x20B9;${Number(s.slab_extra_amount).toLocaleString("en-IN")}</strong>`:"—";return`<div style="background:${l%2===0?"#fff":"#fafaf9"};border-bottom:1px solid #f0f0f0;padding:12px 14px">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px">
            <div style="flex:1;min-width:0">
              <div style="font-size:11px;font-weight:800;color:#4c1d95;margin-bottom:1px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${b(s.bonanza_name)}</div>
              <div style="font-size:10px;color:#6b7280">${k(s.bonanza_start)} – ${k(s.bonanza_end)}</div>
            </div>
            <div style="text-align:right;flex-shrink:0;margin-left:10px">${u}</div>
          </div>
          <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px">
            <div>
              <div style="font-size:13px;font-weight:600;color:#111">${b(s.lead_name)}</div>
              <div style="font-size:10px;font-family:monospace;color:#6b7280">${b(s.entry_number)} &nbsp;·&nbsp; ${k(s.file_date)}</div>
            </div>
            <div style="display:flex;flex-direction:column;align-items:flex-end;gap:3px">
              <span style="${p};border-radius:20px;padding:2px 8px;font-size:10px;font-weight:700">${b(s.advance_status)}</span>
              ${f}
            </div>
          </div>
          ${s.achieved_date?`<div style="font-size:10px;color:#16a34a;margin-top:6px"><i class="fas fa-check-circle" style="margin-right:3px"></i>Achieved: ${k(s.achieved_date)}</div>`:""}
        </div>`}).join("")}
        </div>`}e.innerHTML=a+t.map(r=>this.cardHtml(r)).join("")+n,document.getElementById("bnzRefresh")?.addEventListener("click",()=>this.load(!0))}reload(){this.load(!0)}}function y(d){return String(d??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;")}function E(d){if(!d)return"—";try{return new Date(d).toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"numeric"})}catch{return d}}function v(d){return d.toLocaleString("en-IN")}function z(d){return d.toLocaleString("en-IN",{minimumFractionDigits:2})}class ae{container;rows=[];summary={total_credits:0,total_debits:0,income_debits:0,available_balance:0};page=1;pageSize=30;totalEntries=0;loading=!1;currentFilter="all";constructor(e){this.container=e}async render(){return`
      ${c.render({title:"Points Balance",showBack:!0})}
      <div id="vgk-pts-root" style="padding:12px;background:#f6f9fc;min-height:100vh">
        <div id="vgk-pts-summary" style="margin-bottom:14px">
          <div style="display:flex;gap:8px">
            ${["","",""].map(()=>'<div style="flex:1;height:70px;background:#e2e8f0;border-radius:10px;animation:shimmer 1.2s infinite"></div>').join("")}
          </div>
        </div>
        <div id="vgk-pts-filter" style="display:flex;gap:6px;margin-bottom:12px;overflow-x:auto;padding-bottom:4px"></div>
        <div id="vgk-pts-list" style="display:flex;flex-direction:column;gap:8px">
          ${[1,2,3,4,5].map(()=>'<div style="height:56px;background:#e2e8f0;border-radius:10px;animation:shimmer 1.2s infinite"></div>').join("")}
        </div>
        <div id="vgk-pts-loadmore" style="text-align:center;margin-top:12px;display:none">
          <button id="vgk-pts-more-btn" style="background:#7c3aed;color:#fff;border:none;border-radius:8px;padding:10px 24px;font-size:13px;font-weight:700;cursor:pointer">
            Load More
          </button>
        </div>
      </div>

      <!-- View Detail Bottom Sheet -->
      <div id="vgk-pts-sheet" style="display:none;position:fixed;inset:0;z-index:9999">
        <div id="vgk-pts-overlay" style="position:absolute;inset:0;background:rgba(0,0,0,.5)"></div>
        <div id="vgk-pts-panel" style="position:absolute;bottom:0;left:0;right:0;background:#fff;border-radius:20px 20px 0 0;max-height:90vh;overflow-y:auto;padding:0 0 env(safe-area-inset-bottom,16px)">
          <div style="padding:12px 20px 0;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #f1f5f9;margin-bottom:0">
            <div style="font-size:15px;font-weight:800;color:#1e1b4b">Transaction Detail</div>
            <button id="vgk-pts-close" style="background:none;border:none;font-size:22px;color:#6b7280;cursor:pointer;padding:4px">×</button>
          </div>
          <div id="vgk-pts-sheet-body" style="padding:16px 16px 20px"></div>
        </div>
      </div>

      <style>
        @keyframes shimmer { 0%{opacity:1} 50%{opacity:.5} 100%{opacity:1} }
      </style>
    `}async afterRender(){await this._load(!0),document.getElementById("vgk-pts-overlay")?.addEventListener("click",()=>this._closeSheet()),document.getElementById("vgk-pts-close")?.addEventListener("click",()=>this._closeSheet()),document.getElementById("vgk-pts-more-btn")?.addEventListener("click",()=>this._loadMore())}async _load(e){if(!this.loading){this.loading=!0,e&&(this.page=1,this.rows=[]);try{const t=await m.get(`/vgk/dashboard/points?page=${this.page}&page_size=${this.pageSize}`);if(!t.success)throw new Error("API error");this.summary=t.summary,this.totalEntries=t.total_entries??t.total??0;const i=t.entries??t.data??[];this.rows=e?i:[...this.rows,...i],this._renderSummary(),this._renderFilters(),this._renderList(),this._toggleLoadMore()}catch{document.getElementById("vgk-pts-list").innerHTML=`
        <div style="text-align:center;padding:32px;color:#dc2626;font-size:13px">
          Failed to load points history. Please try again.
        </div>`}finally{this.loading=!1}}}async _loadMore(){this.page++,await this._load(!1)}_renderSummary(){const e=this.summary,t=e.pending_points||0,i=t>0?`<div style="background:#fff;border:1.5px solid #fde68a;border-radius:12px;padding:12px 10px;text-align:center">
          <div style="font-size:9px;color:#92400e;font-weight:700;text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px">Pending Points</div>
          <div style="font-size:15px;font-weight:800;color:#d97706">${v(t)}</div>
          <div style="font-size:9px;color:#6b7280">pts · awaiting payment</div>
        </div>`:"";document.getElementById("vgk-pts-summary").innerHTML=`
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:8px">
        <div style="background:#fff;border:1.5px solid #d1fae5;border-radius:12px;padding:12px 10px;text-align:center">
          <div style="font-size:9px;color:#4c1d95;font-weight:700;text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px">Points In Total</div>
          <div style="font-size:15px;font-weight:800;color:#7c3aed">${v(e.total_credits)}</div>
          <div style="font-size:9px;color:#7c3aed;opacity:.8">pts</div>
        </div>
        <div style="background:#fff;border:1.5px solid #fee2e2;border-radius:12px;padding:12px 10px;text-align:center">
          <div style="font-size:9px;color:#991b1b;font-weight:700;text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px">Points Used Total</div>
          <div style="font-size:15px;font-weight:800;color:#dc2626">${v(e.income_debits||0)}</div>
          <div style="font-size:9px;color:#dc2626;opacity:.8">pts</div>
        </div>
        <div style="background:linear-gradient(135deg,#5b21b6,#7c3aed);border-radius:12px;padding:12px 10px;text-align:center;box-shadow:0 2px 8px rgba(124,58,237,.25);grid-column:1/-1">
          <div style="font-size:9px;color:#e9d5ff;font-weight:700;text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px">Points Final Balance</div>
          <div style="font-size:22px;font-weight:900;color:#fff">${v(e.available_balance)}</div>
          <div style="font-size:9px;color:#c4b5fd">pts &nbsp;(1 pt = ₹1 discount)</div>
        </div>
        ${i}
      </div>
      <div style="background:#faf5ff;border:1px solid #e9d5ff;border-radius:10px;padding:8px 12px;font-size:11px;color:#5b21b6;text-align:center;font-weight:600">
        <i class="fas fa-info-circle me-1"></i>1 VGK Point = ₹1 · Points debited only at payment confirmation
      </div>
    `}_renderFilters(){const e=[{key:"all",label:"All",icon:"fa-th-large"},{key:"credit",label:"Credits",icon:"fa-arrow-up"},{key:"debit",label:"Debits",icon:"fa-arrow-down"}],t=document.getElementById("vgk-pts-filter");t&&(t.innerHTML=e.map(i=>`
      <button data-filter="${i.key}"
        style="flex-shrink:0;border:1.5px solid ${this.currentFilter===i.key?"#7c3aed":"#e2e8f0"};
               background:${this.currentFilter===i.key?"#7c3aed":"#fff"};
               color:${this.currentFilter===i.key?"#fff":"#374151"};
               border-radius:20px;padding:6px 14px;font-size:12px;font-weight:600;cursor:pointer;white-space:nowrap">
        <i class="fas ${i.icon} me-1"></i>${i.label}
      </button>
    `).join(""),t.querySelectorAll("button[data-filter]").forEach(i=>{i.addEventListener("click",()=>{this.currentFilter=i.dataset.filter,this._renderFilters(),this._renderList()})}))}_filtered(){return this.currentFilter==="credit"?this.rows.filter(e=>e.points_credit>0):this.currentFilter==="debit"?this.rows.filter(e=>e.points_debit>0):this.rows}_renderList(){const e=document.getElementById("vgk-pts-list");if(!e)return;const t=this._filtered();if(!t.length){e.innerHTML='<div style="text-align:center;padding:32px;color:#6b7280;font-size:13px">No entries found.</div>';return}e.innerHTML=t.map((i,a)=>{const n=i.points_debit>0,r=n?i.points_debit:i.points_credit;return i.income_entry,`
        <div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid ${n?"#dc2626":"#059669"};
                    border-radius:10px;padding:10px 12px;display:flex;align-items:center;gap:10px">
          <div style="width:34px;height:34px;border-radius:50%;background:${n?"#fee2e2":"#d1fae5"};
                      display:flex;align-items:center;justify-content:center;flex-shrink:0">
            <i class="fas ${n?"fa-minus":"fa-plus"}" style="font-size:13px;color:${n?"#dc2626":"#059669"}"></i>
          </div>
          <div style="flex:1;min-width:0">
            <div style="font-size:12px;font-weight:700;color:#1f2937;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">
              ${y(i.description||"—")}
            </div>
            <div style="font-size:10px;color:#6b7280;margin-top:1px">
              ${E(i.date)}
              ${i.used_at?`· <span style="color:#7c3aed">${y(i.used_at)}</span>`:""}
            </div>
          </div>
          <div style="text-align:right;flex-shrink:0">
            <div style="font-size:14px;font-weight:900;color:${n?"#dc2626":"#059669"}">
              ${n?"−":"+"}${v(r)}
            </div>
            <div style="font-size:10px;color:#7c3aed;font-weight:700">
              Bal: ${v(i.running_balance)}
            </div>
          </div>
          <button data-row="${a}"
            style="background:#f5f3ff;border:1px solid #c4b5fd;color:#7c3aed;border-radius:8px;
                   padding:5px 8px;font-size:10px;font-weight:700;cursor:pointer;flex-shrink:0;
                   white-space:nowrap">
            <i class="fas fa-eye"></i> View
          </button>
        </div>
      `}).join(""),e.querySelectorAll("button[data-row]").forEach(i=>{i.addEventListener("click",()=>{const a=parseInt(i.dataset.row??"0",10);this._openSheet(t[a])})})}_toggleLoadMore(){const e=document.getElementById("vgk-pts-loadmore");if(!e)return;const t=this.page*this.pageSize;e.style.display=t<this.totalEntries?"block":"none"}_openSheet(e){const t=e.points_debit>0,i=t?e.points_debit:e.points_credit,a=e.income_entry,n=t&&a?(()=>{const r=Number(a.commission_amount??0),o=Number(a.admin_charges??0),s=Number(a.tds_amount??0),l=Number(a.net_payout??0),p=a.paid_at?E(a.paid_at):"—",f=a.payment_mode==="BANK"?"🏦 Bank Transfer":a.payment_mode==="CASH"?"💵 Cash":a.payment_mode??"—";return`
        <div style="background:#faf5ff;border:1.5px solid #e9d5ff;border-radius:10px;padding:14px;margin-bottom:12px">
          <div style="font-size:10px;font-weight:800;color:#5b21b6;text-transform:uppercase;letter-spacing:.07em;margin-bottom:8px">
            <i class="fas fa-solar-panel me-1"></i>Solar Advance Income Breakdown
          </div>
          <div style="font-size:10px;color:#6b7280;font-weight:600;margin-bottom:2px">Entry No.</div>
          <div style="font-size:12px;font-weight:700;color:#111827;margin-bottom:10px;font-family:monospace">${y(a.entry_number??"—")}</div>

          <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:8px">
            <div style="background:#fff;border-radius:8px;padding:8px;border:1px solid #e9d5ff">
              <div style="font-size:9px;color:#6b7280;font-weight:700;text-transform:uppercase;margin-bottom:2px">Gross Income</div>
              <div style="font-size:14px;font-weight:900;color:#111827">₹${z(r)}</div>
            </div>
            <div style="background:#fff;border-radius:8px;padding:8px;border:1px solid #e9d5ff">
              <div style="font-size:9px;color:#6b7280;font-weight:700;text-transform:uppercase;margin-bottom:2px">Pts Debited</div>
              <div style="font-size:14px;font-weight:900;color:#dc2626">−${v(i)}</div>
            </div>
          </div>

          <div style="background:#fff;border-radius:8px;padding:10px;border:1px solid #e9d5ff;margin-bottom:8px">
            <div style="font-size:9px;color:#6b7280;font-weight:700;text-transform:uppercase;margin-bottom:6px">Deduction Breakup</div>
            ${[["Gross Income",`₹${z(r)}`,"#111827"],["Admin Charges (8%)",`−₹${z(o)}`,"#dc2626"],["TDS (2%)",`−₹${z(s)}`,"#dc2626"]].map(([u,x,w],h)=>`
              <div style="display:flex;justify-content:space-between;font-size:11px;padding:3px 0;${h<2?"border-bottom:1px dashed #e9d5ff":""}">
                <span style="color:#374151">${u}</span>
                <span style="font-weight:700;color:${w}">${x}</span>
              </div>
            `).join("")}
            <div style="display:flex;justify-content:space-between;font-size:12px;padding:6px 0 0;font-weight:900">
              <span style="color:#059669">Net Paid Out</span>
              <span style="color:#059669">₹${z(l)}</span>
            </div>
          </div>

          <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
            <div style="background:#fff;border-radius:8px;padding:8px;border:1px solid #e9d5ff">
              <div style="font-size:9px;color:#6b7280;font-weight:700;text-transform:uppercase;margin-bottom:2px">Payment Mode</div>
              <div style="font-size:11px;font-weight:700;color:#1f2937">${y(f)}</div>
            </div>
            <div style="background:#fff;border-radius:8px;padding:8px;border:1px solid #e9d5ff">
              <div style="font-size:9px;color:#6b7280;font-weight:700;text-transform:uppercase;margin-bottom:2px">Paid Date</div>
              <div style="font-size:11px;font-weight:700;color:#1f2937">${y(p)}</div>
            </div>
            ${a.payment_utr?`
            <div style="background:#fff;border-radius:8px;padding:8px;border:1px solid #e9d5ff;grid-column:1/-1">
              <div style="font-size:9px;color:#6b7280;font-weight:700;text-transform:uppercase;margin-bottom:2px">UTR / Reference</div>
              <div style="font-size:11px;font-weight:700;color:#1f2937;font-family:monospace;word-break:break-all">${y(a.payment_utr)}</div>
            </div>`:""}
          </div>
        </div>`})():"";document.getElementById("vgk-pts-sheet-body").innerHTML=`
      ${n}
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:10px">
        <div style="background:#f9fafb;border-radius:8px;padding:10px">
          <div style="font-size:9px;color:#6b7280;font-weight:700;text-transform:uppercase;margin-bottom:3px">Date</div>
          <div style="font-size:13px;font-weight:700;color:#111827">${E(e.date)}</div>
        </div>
        <div style="background:#f9fafb;border-radius:8px;padding:10px">
          <div style="font-size:9px;color:#6b7280;font-weight:700;text-transform:uppercase;margin-bottom:3px">Type</div>
          <div style="font-size:12px;font-weight:700;color:${t?"#dc2626":"#059669"}">${t?"Points Used":"Points Credited"}</div>
        </div>
        <div style="background:#f9fafb;border-radius:8px;padding:10px">
          <div style="font-size:9px;color:#6b7280;font-weight:700;text-transform:uppercase;margin-bottom:3px">Amount</div>
          <div style="font-size:18px;font-weight:900;color:${t?"#dc2626":"#059669"}">${t?"−":"+"}${v(i)} pts</div>
        </div>
        <div style="background:#f9fafb;border-radius:8px;padding:10px">
          <div style="font-size:9px;color:#6b7280;font-weight:700;text-transform:uppercase;margin-bottom:3px">Balance After</div>
          <div style="font-size:18px;font-weight:900;color:#7c3aed">${v(e.running_balance)} pts</div>
        </div>
      </div>
      <div style="margin-bottom:8px">
        <div style="font-size:9px;color:#6b7280;font-weight:700;text-transform:uppercase;margin-bottom:3px">Description</div>
        <div style="font-size:13px;color:#1f2937;font-weight:500">${y(e.description??"—")}</div>
      </div>
      ${e.used_at?`<div style="margin-bottom:8px">
        <div style="font-size:9px;color:#6b7280;font-weight:700;text-transform:uppercase;margin-bottom:3px">Used At</div>
        <div style="font-size:13px;color:#5b21b6;font-weight:600">${y(e.used_at)}</div>
      </div>`:""}
      ${e.notes?`<div style="background:#f5f3ff;border-radius:8px;padding:10px;font-size:11px;color:#374151;line-height:1.6">
        <i class="fas fa-sticky-note me-1" style="color:#7c3aed"></i>${y(e.notes)}
      </div>`:""}
    `,document.getElementById("vgk-pts-sheet").style.display="block",document.body.style.overflow="hidden"}_closeSheet(){document.getElementById("vgk-pts-sheet").style.display="none",document.body.style.overflow=""}}class ne{container;static slug="feedback";static label="Submit Feedback";static icon="fas fa-comment-dots";static color="#7c3aed";static endpoint="/vgk/feedback";constructor(e){this.container=e}async init(){this.container.innerHTML=await this.render(),await this.afterRender()}async render(){return`
      ${c.render({title:"Submit Feedback",showBack:!0})}
      <div style="padding:14px 12px;background:#f6f9fc;min-height:100vh">
        <div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #7c3aed;border-radius:12px;padding:14px 16px;margin-bottom:12px">
          <div style="display:flex;align-items:center;gap:10px;font-weight:700;color:#0f172a;font-size:15px">
            <i class="fas fa-comment-dots" style="color:#7c3aed;font-size:20px"></i> Submit Feedback
          </div>
          <div style="margin-top:6px;color:#64748b;font-size:12px">VGK4U Members · Write-Flow · Phase 2</div>
        </div>
        <iframe
          id="vgk4u-feedback-frame"
          src="${g.MEDIA_BASE_URL}/vgk/feedback?token=${encodeURIComponent(localStorage.getItem("auth_token")||"")}"
          style="width:100%;height:calc(100vh - 200px);border:0;background:#fff;border-radius:12px;border:1px solid #e2e8f0"
          loading="lazy"
          title="Submit Feedback (VGK4U)"
        ></iframe>
      </div>
    `}async afterRender(){}}class re{container;static slug="announcements";static label="Create Announcement";static icon="fas fa-bullhorn";static color="#0d9488";static endpoint="/vgk/announcements";constructor(e){this.container=e}async init(){this.container.innerHTML=await this.render(),await this.afterRender()}async render(){return`
      ${c.render({title:"Create Announcement",showBack:!0})}
      <div style="padding:14px 12px;background:#f6f9fc;min-height:100vh">
        <div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #0d9488;border-radius:12px;padding:14px 16px;margin-bottom:12px">
          <div style="display:flex;align-items:center;gap:10px;font-weight:700;color:#0f172a;font-size:15px">
            <i class="fas fa-bullhorn" style="color:#0d9488;font-size:20px"></i> Create Announcement
          </div>
          <div style="margin-top:6px;color:#64748b;font-size:12px">VGK4U Members · Write-Flow · Phase 2</div>
        </div>
        <iframe
          id="vgk4u-announcements-frame"
          src="${g.MEDIA_BASE_URL}/vgk/announcements?token=${encodeURIComponent(localStorage.getItem("auth_token")||"")}"
          style="width:100%;height:calc(100vh - 200px);border:0;background:#fff;border-radius:12px;border:1px solid #e2e8f0"
          loading="lazy"
          title="Create Announcement (VGK4U)"
        ></iframe>
      </div>
    `}async afterRender(){}}class se{container;static slug="my-announcements";static label="My Announcements";static icon="fas fa-list";static color="#0d9488";static endpoint="/vgk/my-announcements";constructor(e){this.container=e}async init(){this.container.innerHTML=await this.render(),await this.afterRender()}async render(){return`
      ${c.render({title:"My Announcements",showBack:!0})}
      <div style="padding:14px 12px;background:#f6f9fc;min-height:100vh">
        <div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #0d9488;border-radius:12px;padding:14px 16px;margin-bottom:12px">
          <div style="display:flex;align-items:center;gap:10px;font-weight:700;color:#0f172a;font-size:15px">
            <i class="fas fa-list" style="color:#0d9488;font-size:20px"></i> My Announcements
          </div>
          <div style="margin-top:6px;color:#64748b;font-size:12px">VGK4U Members · Write-Flow · Phase 2</div>
        </div>
        <iframe
          id="vgk4u-my-announcements-frame"
          src="${g.MEDIA_BASE_URL}/vgk/my-announcements?token=${encodeURIComponent(localStorage.getItem("auth_token")||"")}"
          style="width:100%;height:calc(100vh - 200px);border:0;background:#fff;border-radius:12px;border:1px solid #e2e8f0"
          loading="lazy"
          title="My Announcements (VGK4U)"
        ></iframe>
      </div>
    `}async afterRender(){}}class oe{container;static slug="kyc";static label="KYC Documents";static icon="fas fa-id-card";static color="#dc2626";static endpoint="/vgk/kyc";constructor(e){this.container=e}async init(){this.container.innerHTML=await this.render(),await this.afterRender()}async render(){return`
      ${c.render({title:"KYC Documents",showBack:!0})}
      <div style="padding:14px 12px;background:#f6f9fc;min-height:100vh">
        <div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #dc2626;border-radius:12px;padding:14px 16px;margin-bottom:12px">
          <div style="display:flex;align-items:center;gap:10px;font-weight:700;color:#0f172a;font-size:15px">
            <i class="fas fa-id-card" style="color:#dc2626;font-size:20px"></i> KYC Documents
          </div>
          <div style="margin-top:6px;color:#64748b;font-size:12px">VGK4U Members · Write-Flow · Phase 2</div>
        </div>
        <iframe
          id="vgk4u-kyc-frame"
          src="${g.MEDIA_BASE_URL}/vgk/kyc?token=${encodeURIComponent(localStorage.getItem("auth_token")||"")}"
          style="width:100%;height:calc(100vh - 200px);border:0;background:#fff;border-radius:12px;border:1px solid #e2e8f0"
          loading="lazy"
          title="KYC Documents (VGK4U)"
        ></iframe>
      </div>
    `}async afterRender(){}}class de{container;static slug="bank-details";static label="Bank Details";static icon="fas fa-university";static color="#2563eb";static endpoint="/vgk/bank-details";constructor(e){this.container=e}async init(){this.container.innerHTML=await this.render(),await this.afterRender()}async render(){return`
      ${c.render({title:"Bank Details",showBack:!0})}
      <div style="padding:14px 12px;background:#f6f9fc;min-height:100vh">
        <div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #2563eb;border-radius:12px;padding:14px 16px;margin-bottom:12px">
          <div style="display:flex;align-items:center;gap:10px;font-weight:700;color:#0f172a;font-size:15px">
            <i class="fas fa-university" style="color:#2563eb;font-size:20px"></i> Bank Details
          </div>
          <div style="margin-top:6px;color:#64748b;font-size:12px">VGK4U Members · Write-Flow · Phase 2</div>
        </div>
        <iframe
          id="vgk4u-bank-details-frame"
          src="${g.MEDIA_BASE_URL}/vgk/bank-details?token=${encodeURIComponent(localStorage.getItem("auth_token")||"")}"
          style="width:100%;height:calc(100vh - 200px);border:0;background:#fff;border-radius:12px;border:1px solid #e2e8f0"
          loading="lazy"
          title="Bank Details (VGK4U)"
        ></iframe>
      </div>
    `}async afterRender(){}}class le{container;static slug="profile-edit";static label="Edit Profile";static icon="fas fa-user-edit";static color="#7c3aed";static endpoint="/vgk/profile-edit";constructor(e){this.container=e}async init(){this.container.innerHTML=await this.render(),await this.afterRender()}async render(){return`
      ${c.render({title:"Edit Profile",showBack:!0})}
      <div style="padding:14px 12px;background:#f6f9fc;min-height:100vh">
        <div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #7c3aed;border-radius:12px;padding:14px 16px;margin-bottom:12px">
          <div style="display:flex;align-items:center;gap:10px;font-weight:700;color:#0f172a;font-size:15px">
            <i class="fas fa-user-edit" style="color:#7c3aed;font-size:20px"></i> Edit Profile
          </div>
          <div style="margin-top:6px;color:#64748b;font-size:12px">VGK4U Members · Write-Flow · Phase 2</div>
        </div>
        <iframe
          id="vgk4u-profile-edit-frame"
          src="${g.MEDIA_BASE_URL}/vgk/profile-edit?token=${encodeURIComponent(localStorage.getItem("auth_token")||"")}"
          style="width:100%;height:calc(100vh - 200px);border:0;background:#fff;border-radius:12px;border:1px solid #e2e8f0"
          loading="lazy"
          title="Edit Profile (VGK4U)"
        ></iframe>
      </div>
    `}async afterRender(){}}class ce{container;static slug="settings";static label="Notification Settings";static icon="fas fa-cog";static color="#6b7280";static endpoint="/vgk/settings";constructor(e){this.container=e}async init(){this.container.innerHTML=await this.render(),await this.afterRender()}async render(){return`
      ${c.render({title:"Notification Settings",showBack:!0})}
      <div style="padding:14px 12px;background:#f6f9fc;min-height:100vh">
        <div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #6b7280;border-radius:12px;padding:14px 16px;margin-bottom:12px">
          <div style="display:flex;align-items:center;gap:10px;font-weight:700;color:#0f172a;font-size:15px">
            <i class="fas fa-cog" style="color:#6b7280;font-size:20px"></i> Notification Settings
          </div>
          <div style="margin-top:6px;color:#64748b;font-size:12px">VGK4U Members · Write-Flow · Phase 2</div>
        </div>
        <iframe
          id="vgk4u-settings-frame"
          src="${g.MEDIA_BASE_URL}/vgk/settings?token=${encodeURIComponent(localStorage.getItem("auth_token")||"")}"
          style="width:100%;height:calc(100vh - 200px);border:0;background:#fff;border-radius:12px;border:1px solid #e2e8f0"
          loading="lazy"
          title="Notification Settings (VGK4U)"
        ></iframe>
      </div>
    `}async afterRender(){}}class pe{container;static slug="coupon-activate";static label="Activate Coupon";static icon="fas fa-ticket-alt";static color="#d97706";static endpoint="/vgk/coupon-activate";constructor(e){this.container=e}async init(){this.container.innerHTML=await this.render(),await this.afterRender()}async render(){return`
      ${c.render({title:"Activate Coupon",showBack:!0})}
      <div style="padding:14px 12px;background:#f6f9fc;min-height:100vh">
        <div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #d97706;border-radius:12px;padding:14px 16px;margin-bottom:12px">
          <div style="display:flex;align-items:center;gap:10px;font-weight:700;color:#0f172a;font-size:15px">
            <i class="fas fa-ticket-alt" style="color:#d97706;font-size:20px"></i> Activate Coupon
          </div>
          <div style="margin-top:6px;color:#64748b;font-size:12px">VGK4U Members · Write-Flow · Phase 2</div>
        </div>
        <iframe
          id="vgk4u-coupon-activate-frame"
          src="${g.MEDIA_BASE_URL}/vgk/coupon-activate?token=${encodeURIComponent(localStorage.getItem("auth_token")||"")}"
          style="width:100%;height:calc(100vh - 200px);border:0;background:#fff;border-radius:12px;border:1px solid #e2e8f0"
          loading="lazy"
          title="Activate Coupon (VGK4U)"
        ></iframe>
      </div>
    `}async afterRender(){}}class fe{container;static slug="coupon-progress";static label="Coupon Progress";static icon="fas fa-chart-line";static color="#10b981";static endpoint="/vgk/coupon-progress";constructor(e){this.container=e}async init(){this.container.innerHTML=await this.render(),await this.afterRender()}async render(){return`
      ${c.render({title:"Coupon Progress",showBack:!0})}
      <div style="padding:14px 12px;background:#f6f9fc;min-height:100vh">
        <div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #10b981;border-radius:12px;padding:14px 16px;margin-bottom:12px">
          <div style="display:flex;align-items:center;gap:10px;font-weight:700;color:#0f172a;font-size:15px">
            <i class="fas fa-chart-line" style="color:#10b981;font-size:20px"></i> Coupon Progress
          </div>
          <div style="margin-top:6px;color:#64748b;font-size:12px">VGK4U Members · Write-Flow · Phase 2</div>
        </div>
        <iframe
          id="vgk4u-coupon-progress-frame"
          src="${g.MEDIA_BASE_URL}/vgk/coupon-progress?token=${encodeURIComponent(localStorage.getItem("auth_token")||"")}"
          style="width:100%;height:calc(100vh - 200px);border:0;background:#fff;border-radius:12px;border:1px solid #e2e8f0"
          loading="lazy"
          title="Coupon Progress (VGK4U)"
        ></iframe>
      </div>
    `}async afterRender(){}}class ge{container;static slug="coupon-transfer";static label="Transfer Coupons";static icon="fas fa-exchange-alt";static color="#8b5cf6";static endpoint="/vgk/coupon-transfer";constructor(e){this.container=e}async init(){this.container.innerHTML=await this.render(),await this.afterRender()}async render(){return`
      ${c.render({title:"Transfer Coupons",showBack:!0})}
      <div style="padding:14px 12px;background:#f6f9fc;min-height:100vh">
        <div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid #8b5cf6;border-radius:12px;padding:14px 16px;margin-bottom:12px">
          <div style="display:flex;align-items:center;gap:10px;font-weight:700;color:#0f172a;font-size:15px">
            <i class="fas fa-exchange-alt" style="color:#8b5cf6;font-size:20px"></i> Transfer Coupons
          </div>
          <div style="margin-top:6px;color:#64748b;font-size:12px">VGK4U Members · Write-Flow · Phase 2</div>
        </div>
        <iframe
          id="vgk4u-coupon-transfer-frame"
          src="${g.MEDIA_BASE_URL}/vgk/coupon-transfer?token=${encodeURIComponent(localStorage.getItem("auth_token")||"")}"
          style="width:100%;height:calc(100vh - 200px);border:0;background:#fff;border-radius:12px;border:1px solid #e2e8f0"
          loading="lazy"
          title="Transfer Coupons (VGK4U)"
        ></iframe>
      </div>
    `}async afterRender(){}}class ue{static slug="vgk-income-unified";static label="VGK Income — Unified";static icon="💹";container;rows=[];fullRows=[];loading=!0;filterStatus="";filterKind="";filterMonth="";filterDateFrom="";filterDateTo="";filterSearch="";filterPoints="";expandedDates=new Set;expandedPartners=new Set;activeModalRow=null;activeModalAction="";paymentMode="BANK";constructor(e){this.container=e}async init(){this.renderContainer(),await this.loadData()}renderContainer(){this.container.innerHTML=`
      <div class="page-container" style="background:#f0fdf4;min-height:100vh;padding-bottom:30px">
        ${c.render({title:"VGK Income — Unified",showBack:!0})}
        <div id="pageContent" style="padding:12px">
          <div style="text-align:center;padding:40px 10px;color:#059669">
            <i class="fas fa-spinner fa-spin fa-2x"></i>
            <div style="margin-top:10px;font-size:14px;font-weight:600">Loading Unified Income Data...</div>
          </div>
        </div>
      </div>
      <div id="actModalOverlay" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.6);z-index:9999;align-items:center;justify-content:center;padding:16px"></div>
    `,c.attachListeners({title:"VGK Income — Unified",showBack:!0})}async loadData(){this.loading=!0;try{const e=new URLSearchParams({vgk_mode:"true",per_page:"200"});this.filterStatus&&!["Stage1Approved","Payout Completed"].includes(this.filterStatus)&&e.set("status",this.filterStatus),this.filterKind&&!["BONANZA","FIELD_ALLOWANCE"].includes(this.filterKind)&&e.set("kind",this.filterKind),this.filterPoints&&e.set("points_filter",this.filterPoints);const t=!this.filterKind||!["BONANZA","FIELD_ALLOWANCE"].includes(this.filterKind),i=!this.filterStatus||["RELEASED","PAID","PENDING"].includes(this.filterStatus),a=(!this.filterKind||this.filterKind==="BONANZA")&&i,n=!this.filterKind||this.filterKind==="FIELD_ALLOWANCE",r=new URLSearchParams({per_page:"200"});this.filterStatus&&["Pending","Stage1Approved","Payout Completed"].includes(this.filterStatus)&&r.set("status",this.filterStatus),this.filterMonth&&r.set("month_year",this.filterMonth.replace("-","").substring(2)),this.filterSearch&&r.set("search",this.filterSearch);const[o,s,l]=await Promise.all([t?m.get(`/vgk/staff/vgk/cash-income/unified-list?${e.toString()}`):Promise.resolve(null),a?m.get("/bonanza/vgk/pending-payments?stage=all"):Promise.resolve(null),n?m.get(`/vgk/staff/vgk/field-allowances?${r.toString()}`):Promise.resolve(null)]);let p=[];if(o&&o.success&&(p=[...Array.isArray(o.data)?o.data:o.data?.data||[]]),s&&s.success){const u=(s.data?.claims||s.claims||[]).map(x=>this.normalizeBonanzaRow(x));p=[...p,...u]}if(l&&l.success){const u=(Array.isArray(l.data)?l.data:l.data?.data||[]).map(x=>this.normalizeFaRow(x));p=[...p,...u]}this.fullRows=[...p],this.applyFilters()}catch(e){console.error("[VGKIncomeUnified] Error loading data:",e);const t=document.getElementById("pageContent");t&&(t.innerHTML=`
          <div style="background:#fee2e2;color:#991b1b;padding:16px;border-radius:12px;text-align:center">
            <i class="fas fa-exclamation-triangle fa-2x"></i>
            <div style="font-weight:700;margin-top:8px">Failed to load VGK Income records</div>
            <div style="font-size:12px;margin-top:4px">${e?.message||"Please check network connection"}</div>
            <button id="retryBtn" style="margin-top:12px;background:#dc2626;color:#fff;border:none;padding:8px 16px;border-radius:8px;font-size:13px;font-weight:600">Retry</button>
          </div>
        `,document.getElementById("retryBtn")?.addEventListener("click",()=>this.loadData()))}finally{this.loading=!1}}normalizeBonanzaRow(e){const t=e.amount||0,i=Math.round(t*.1*100)/100,a=Math.round((t-i)*100)/100;let n="PENDING";e.processed_status==="Paid"?n="PAID":e.processed_status==="Payment Released"&&(n="RELEASED");const r=e.deal_count>1?` (${e.deal_count} files × ₹${Number(e.slab_extra_amount||0).toLocaleString("en-IN")})`:"",o=[];return n==="PENDING"&&o.push("approve_bnz"),n==="RELEASED"&&o.push("pay_bnz"),{id:e.claim_id,entry_number:"BNZ-"+e.claim_id,kind:"BONANZA",level:null,partner_name:e.partner_name||"Partner",partner_code:e.partner_code||"",client_name:(e.bonanza_name||"Bonanza")+r,commission_amount:t,admin_charges:i,tds_amount:0,net_payout:a,status:n,available_actions:o,company_id:e.is_solar?4:e.partner_company_id||2,income_date:e.created_at||e.released_at||null,_is_bonanza:!0,_raw_bnz:e}}normalizeFaRow(e){const t=e.gross||e.amount_paid||0,i=[],a=e.status||"Pending";return(a==="Pending"||a==="")&&i.push("fa_stage1"),a==="Stage1Approved"&&i.push("fa_stage2"),{id:e.id,entry_number:`FA-${e.allowance_type||"STD"}-${e.month_year||""}`.toUpperCase().replace(/\s/g,"-"),kind:"FIELD_ALLOWANCE",level:null,partner_name:e.user_name||e.user_emp_code||String(e.user_id),partner_code:e.user_emp_code||"",client_name:(e.allowance_type||"").replace(/_/g," ")+(e.month_year?" · "+e.month_year:""),commission_amount:t,admin_charges:0,tds_amount:0,net_payout:t,status:a==="Payout Completed"?"PAID":a,available_actions:i,company_id:e.company_id||2,income_date:e.created_at||null,_is_field_allowance:!0,_raw_fa:e}}applyFilters(){let e=[...this.fullRows];if(this.filterStatus&&(e=e.filter(t=>(t.status==="Payout Completed"?"PAID":t.status==="Stage1Approved"?"STAGE1_APPROVED":t.status)===this.filterStatus)),this.filterKind&&(e=e.filter(t=>t.kind===this.filterKind)),this.filterSearch){const t=this.filterSearch.toLowerCase();e=e.filter(i=>(i.entry_number||"").toLowerCase().includes(t)||(i.partner_code||"").toLowerCase().includes(t)||(i.partner_name||"").toLowerCase().includes(t)||(i.client_name||"").toLowerCase().includes(t))}if((this.filterDateFrom||this.filterDateTo)&&(e=e.filter(t=>{const i=t.income_date||t.created_at||null;if(!i)return!this.filterDateFrom;const a=this.parseIsoDate(i);if(!a)return!1;const n=a.getFullYear()+"-"+String(a.getMonth()+1).padStart(2,"0")+"-"+String(a.getDate()).padStart(2,"0");return!(this.filterDateFrom&&n<this.filterDateFrom||this.filterDateTo&&n>this.filterDateTo)})),this.filterMonth){const t=this.filterMonth.replace("-","").substring(2);e=e.filter(i=>i._is_field_allowance||(i.entry_number||"").includes(t))}this.rows=e,this.updateUI()}updateUI(){const e=document.getElementById("pageContent");e&&(e.innerHTML=`
      <!-- Summary Cards Row -->
      ${this.renderSummaryCards()}

      <!-- Filters Panel (Mobile Stacked) -->
      ${this.renderFilters()}

      <!-- 3-Level Accordion List -->
      ${this.render3LevelList()}
    `,this.attachEventListeners())}renderSummaryCards(){const e=["DRAFT","PENDING","RELEASED","STAGE1_APPROVED","PAID","CANCELLED"],t={};let i=0,a=0;for(const o of this.rows){const s=o.status==="Payout Completed"?"PAID":o.status==="Stage1Approved"?"STAGE1_APPROVED":o.status||"DRAFT";t[s]||(t[s]={count:0,gross:0,net:0}),t[s].count++,t[s].gross+=Number(o.commission_amount||0),t[s].net+=Number(o.net_payout||0),s!=="CANCELLED"&&(i+=Number(o.commission_amount||0),a+=Number(o.net_payout||0))}const n=e.map(o=>{const s=t[o]||{count:0,gross:0},l=this.filterStatus===o,p={DRAFT:"#92400e",PENDING:"#1e40af",RELEASED:"#0d9488",STAGE1_APPROVED:"#5b21b6",PAID:"#15803d",CANCELLED:"#991b1b"},f=l?p[o]:"#d1fae5",u=l?p[o]:"#ffffff",x=l?"#ffffff":"#374151",w=l?"#ffffff":p[o];return`
        <div class="sum-card-mb" data-status="${o}" style="flex:0 0 110px;background:${u};border:1.5px solid ${f};border-radius:10px;padding:8px 10px;cursor:pointer;scroll-snap-align:start">
          <div style="font-size:10px;font-weight:700;color:${x};text-transform:uppercase;letter-spacing:.05em">${o.replace("_"," ")}</div>
          <div style="font-size:18px;font-weight:800;color:${w};margin-top:2px">${s.count}</div>
          <div style="font-size:10.5px;font-weight:600;color:${l?"#e2e8f0":"#6b7280"};margin-top:2px">${this.fmt(s.gross)}</div>
        </div>
      `}).join(""),r=`
      <div class="sum-card-mb" data-status="" style="flex:0 0 140px;background:#064e3b;border:1.5px solid #064e3b;border-radius:10px;padding:8px 10px;cursor:pointer;scroll-snap-align:start">
        <div style="font-size:10px;font-weight:700;color:#a7f3d0;text-transform:uppercase;letter-spacing:.05em">TOTAL NET</div>
        <div style="font-size:18px;font-weight:800;color:#ffffff;margin-top:2px">${this.fmt(a)}</div>
        <div style="font-size:10.5px;font-weight:600;color:#a7f3d0;margin-top:2px">Gross ${this.fmt(i)}</div>
      </div>
    `;return`
      <div style="display:flex;gap:8px;overflow-x:auto;padding-bottom:6px;margin-bottom:12px;scroll-snap-type:x mandatory;-webkit-overflow-scrolling:touch">
        ${n}
        ${r}
      </div>
    `}renderFilters(){return`
      <div style="background:#fff;border-radius:12px;border:1.5px solid #d1fae5;padding:12px;margin-bottom:12px">
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:8px">
          <div>
            <label style="font-size:11px;font-weight:700;color:#374151;display:block;margin-bottom:3px">STATUS</label>
            <select id="mbStatusSel" style="width:100%;padding:7px 8px;border:1.5px solid #d1fae5;border-radius:8px;font-size:12px;background:#fff">
              <option value="" ${this.filterStatus===""?"selected":""}>All Statuses</option>
              <option value="DRAFT" ${this.filterStatus==="DRAFT"?"selected":""}>DRAFT</option>
              <option value="PENDING" ${this.filterStatus==="PENDING"?"selected":""}>PENDING</option>
              <option value="STAGE1_APPROVED" ${this.filterStatus==="STAGE1_APPROVED"?"selected":""}>STAGE1 APPROVED</option>
              <option value="PAID" ${this.filterStatus==="PAID"?"selected":""}>PAID</option>
              <option value="CANCELLED" ${this.filterStatus==="CANCELLED"?"selected":""}>CANCELLED</option>
            </select>
          </div>
          <div>
            <label style="font-size:11px;font-weight:700;color:#374151;display:block;margin-bottom:3px">TYPE</label>
            <select id="mbKindSel" style="width:100%;padding:7px 8px;border:1.5px solid #d1fae5;border-radius:8px;font-size:12px;background:#fff">
              <option value="" ${this.filterKind===""?"selected":""}>All Types</option>
              <option value="COMMISSION" ${this.filterKind==="COMMISSION"?"selected":""}>Commission</option>
              <option value="ADVANCE" ${this.filterKind==="ADVANCE"?"selected":""}>Solar Advance</option>
              <option value="SENIOR_COMM" ${this.filterKind==="SENIOR_COMM"?"selected":""}>Senior Comm</option>
              <option value="BONANZA" ${this.filterKind==="BONANZA"?"selected":""}>Bonanza</option>
              <option value="FIELD_ALLOWANCE" ${this.filterKind==="FIELD_ALLOWANCE"?"selected":""}>Field Allowance</option>
            </select>
          </div>
        </div>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:8px">
          <div>
            <label style="font-size:11px;font-weight:700;color:#374151;display:block;margin-bottom:3px">FROM DATE</label>
            <input type="date" id="mbDateFromInp" value="${this.filterDateFrom}" style="width:100%;padding:6px 8px;border:1.5px solid #d1fae5;border-radius:8px;font-size:12px">
          </div>
          <div>
            <label style="font-size:11px;font-weight:700;color:#374151;display:block;margin-bottom:3px">TO DATE</label>
            <input type="date" id="mbDateToInp" value="${this.filterDateTo}" style="width:100%;padding:6px 8px;border:1.5px solid #d1fae5;border-radius:8px;font-size:12px">
          </div>
        </div>

        <div style="display:flex;gap:6px;align-items:center">
          <input type="text" id="mbSearchInp" placeholder="Search partner, code, entry #..." value="${this.filterSearch}" style="flex:1;padding:7px 10px;border:1.5px solid #d1fae5;border-radius:8px;font-size:12px">
          <button id="mbRefreshBtn" style="background:#059669;color:#fff;border:none;padding:7px 12px;border-radius:8px;font-size:12px;font-weight:700;display:flex;align-items:center;gap:4px">
            <i class="fas fa-sync-alt"></i>
          </button>
        </div>
      </div>
    `}render3LevelList(){if(!this.rows.length)return`
        <div style="background:#fff;border-radius:12px;border:1.5px solid #d1fae5;padding:40px 16px;text-align:center;color:#6b7280">
          <i class="fas fa-inbox fa-3x" style="color:#d1fae5;margin-bottom:12px"></i>
          <div style="font-weight:700;font-size:15px;color:#374151">No income entries found</div>
          <div style="font-size:12px;margin-top:4px">Try clearing filters or search query</div>
        </div>
      `;const e={};for(const a of this.rows){const n=a.income_date||a.created_at||null,r=this.getDateKey(n),o=this.fmtDate(n);e[r]||(e[r]={dateDisplay:o,count:0,net:0,gross:0,partners:{}}),e[r].count++,e[r].net+=Number(a.net_payout||0),e[r].gross+=Number(a.commission_amount||0);const s=a.partner_code||"",l=a.partner_name||s||"Unassigned",p=(s||l).replace(/[^a-zA-Z0-9]/g,"_");e[r].partners[p]||(e[r].partners[p]={name:l,code:s,count:0,net:0,gross:0,entries:[]}),e[r].partners[p].count++,e[r].partners[p].net+=Number(a.net_payout||0),e[r].partners[p].gross+=Number(a.commission_amount||0),e[r].partners[p].entries.push(a)}const t=Object.keys(e).sort().reverse();if(this.expandedDates.size===0&&t.length>0){this.expandedDates.add(t[0]);const a=Object.keys(e[t[0]].partners)[0];a&&this.expandedPartners.add(`${t[0]}_${a}`)}let i='<div style="display:flex;flex-direction:column;gap:10px">';for(const a of t){const n=e[a],r=this.expandedDates.has(a);i+=`
        <div style="background:#fff;border-radius:12px;border:1.5px solid #d1fae5;overflow:hidden">
          <!-- Level 1 Date Header -->
          <div class="lvl1-date-hdr" data-dkey="${a}" style="background:#064e3b;color:#fff;padding:12px 14px;display:flex;justify-content:space-between;align-items:center;cursor:pointer">
            <div>
              <div style="display:flex;align-items:center;gap:8px;font-weight:800;font-size:14px">
                <i class="fas fa-chevron-${r?"down":"right"}" style="font-size:11px;color:#a7f3d0"></i>
                <span>${n.dateDisplay}</span>
                <span style="background:#047857;color:#a7f3d0;font-size:10px;padding:2px 8px;border-radius:12px;font-weight:700">${n.count} items</span>
              </div>
            </div>
            <div style="text-align:right">
              <div style="font-weight:800;font-size:14px;color:#a7f3d0">${this.fmt(n.net)}</div>
              <div style="font-size:10.5px;opacity:.8">Gross ${this.fmt(n.gross)}</div>
            </div>
          </div>

          <!-- Level 2 Partner Rows -->
          ${r?`
            <div style="padding:8px 10px;background:#f0fdf4;display:flex;flex-direction:column;gap:8px">
              ${Object.keys(n.partners).map(o=>{const s=n.partners[o],l=`${a}_${o}`,p=this.expandedPartners.has(l);return`
                  <div style="background:#ffffff;border:1.5px solid #bbf7d0;border-radius:10px;overflow:hidden">
                    <div class="lvl2-partner-hdr" data-pkey="${l}" style="background:#ecfdf5;padding:10px 12px;display:flex;justify-content:space-between;align-items:center;cursor:pointer">
                      <div style="display:flex;align-items:center;gap:8px">
                        <i class="fas fa-chevron-${p?"down":"right"}" style="font-size:10px;color:#059669"></i>
                        <div>
                          <div style="font-weight:700;font-size:13px;color:#065f46">${this.escape(s.name)}</div>
                          ${s.code?`<div style="font-family:monospace;font-size:11px;color:#6b7280">${this.escape(s.code)}</div>`:""}
                        </div>
                      </div>
                      <div style="text-align:right">
                        <div style="font-weight:700;font-size:13px;color:#059669">${this.fmt(s.net)}</div>
                        <div style="font-size:10.5px;color:#6b7280">${s.count} entries</div>
                      </div>
                    </div>

                    <!-- Level 3 Entries -->
                    ${p?`
                      <div style="padding:8px;display:flex;flex-direction:column;gap:8px;background:#f9fafb">
                        ${s.entries.map(f=>this.renderLevel3Card(f)).join("")}
                      </div>
                    `:""}
                  </div>
                `}).join("")}
            </div>
          `:""}
        </div>
      `}return i+="</div>",i}renderLevel3Card(e){const i={ADVANCE:"background:#fef3c7;color:#92400e",SLAB_BONUS:"background:#d1fae5;color:#065f46",BONANZA:"background:#ede9fe;color:#5b21b6",SENIOR_COMM:"background:#fce7f3;color:#9d174d",FIELD_ALLOWANCE:"background:#dbeafe;color:#1e40af"}[e.kind]||"background:#f3f4f6;color:#374151",n={DRAFT:"background:#fef3c7;color:#92400e",PENDING:"background:#dbeafe;color:#1e40af",RELEASED:"background:#ccfbf1;color:#0f766e",STAGE1_APPROVED:"background:#ede9fe;color:#5b21b6",PAID:"background:#dcfce7;color:#166534",CANCELLED:"background:#fee2e2;color:#991b1b"}[e.status]||"background:#f3f4f6;color:#374151",r=(e.available_actions||[]).map(o=>this.renderActionBtn(e,o)).join("");return`
      <div style="background:#fff;border-radius:8px;border:1px solid #e5e7eb;border-left:4px solid #059669;padding:10px 12px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
          <div style="font-family:monospace;font-weight:700;font-size:12px;color:#111827">${this.escape(e.entry_number)}</div>
          <span style="border-radius:12px;padding:2px 8px;font-size:10px;font-weight:700;${i}">
            ${this.escape(e.kind)} ${e.level?"L"+e.level:""}
          </span>
        </div>

        <div style="font-size:12px;color:#4b5563;margin-bottom:8px">
          <i class="fas fa-user-tag me-1" style="color:#9ca3af;font-size:10px"></i>
          <span>${this.escape(e.client_name||"—")}</span>
        </div>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;background:#f9fafb;padding:8px;border-radius:6px;margin-bottom:8px;font-size:11.5px">
          <div>
            <span style="color:#6b7280">Gross:</span>
            <strong style="color:#059669">${this.fmt(e.commission_amount)}</strong>
          </div>
          <div>
            <span style="color:#6b7280">Net Payout:</span>
            <strong style="color:#15803d">${this.fmt(e.net_payout)}</strong>
          </div>
          <div>
            <span style="color:#6b7280">Admin:</span>
            <span style="color:#d97706">${e.admin_charges?this.fmt(e.admin_charges):"—"}</span>
          </div>
          <div>
            <span style="color:#6b7280">TDS:</span>
            <span style="color:#dc2626">${e.tds_amount?this.fmt(e.tds_amount):"—"}</span>
          </div>
        </div>

        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
          <span style="border-radius:12px;padding:2px 8px;font-size:10.5px;font-weight:700;${n}">
            ${e.status}
          </span>
          <div style="font-size:11px;color:#6b7280">
            ${e.partner_points_balance!==void 0&&e.partner_points_balance!==null?`Points: <strong>${Number(e.partner_points_balance).toLocaleString("en-IN")}</strong>`:""}
          </div>
        </div>

        ${r?`
          <div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:8px;padding-top:8px;border-top:1px dashed #e5e7eb">
            ${r}
          </div>
        `:""}
      </div>
    `}renderActionBtn(e,t){const i="border:none;border-radius:6px;padding:6px 12px;font-size:11.5px;font-weight:700;cursor:pointer;display:inline-flex;align-items:center;gap:4px;color:#fff;";return t==="confirm"?`<button class="act-btn" data-id="${e.id}" data-act="confirm" style="${i}background:#3b82f6"><i class="fas fa-check"></i> Confirm</button>`:t==="stage1_approve"?`<button class="act-btn" data-id="${e.id}" data-act="stage1_approve" style="${i}background:#7c3aed"><i class="fas fa-user-check"></i> Stage 1 Approve</button>`:t==="mark_paid"?`<button class="act-btn" data-id="${e.id}" data-act="mark_paid" style="${i}background:#15803d"><i class="fas fa-rupee-sign"></i> Mark Paid</button>`:t==="reject"?`<button class="act-btn" data-id="${e.id}" data-act="reject" style="${i}background:#fff;color:#dc2626;border:1.5px solid #fca5a5"><i class="fas fa-times"></i> Reject</button>`:t==="approve_bnz"?`<button class="act-btn-bnz-app" data-claimid="${e.id}" style="${i}background:#059669"><i class="fas fa-paper-plane"></i> Stage 1 Release</button>`:t==="pay_bnz"?`<button class="act-btn-bnz-pay" data-claimid="${e.id}" data-gross="${e.commission_amount}" style="${i}background:#15803d"><i class="fas fa-rupee-sign"></i> Stage 2 Pay</button>`:t==="fa_stage1"?`<button class="act-btn-fa-1" data-faid="${e.id}" style="${i}background:#7c3aed"><i class="fas fa-check"></i> Stage 1 Approve</button>`:t==="fa_stage2"?`<button class="act-btn-fa-2" data-faid="${e.id}" style="${i}background:#15803d"><i class="fas fa-rupee-sign"></i> Stage 2 Mark Paid</button>`:""}attachEventListeners(){const e=document.getElementById("pageContent");e&&(e.querySelector("#mbStatusSel")?.addEventListener("change",t=>{this.filterStatus=t.target.value,this.applyFilters()}),e.querySelector("#mbKindSel")?.addEventListener("change",t=>{this.filterKind=t.target.value,this.applyFilters()}),e.querySelector("#mbDateFromInp")?.addEventListener("change",t=>{this.filterDateFrom=t.target.value,this.applyFilters()}),e.querySelector("#mbDateToInp")?.addEventListener("change",t=>{this.filterDateTo=t.target.value,this.applyFilters()}),e.querySelector("#mbSearchInp")?.addEventListener("input",t=>{this.filterSearch=t.target.value,this.applyFilters()}),e.querySelector("#mbRefreshBtn")?.addEventListener("click",()=>{this.loadData()}),e.querySelectorAll(".sum-card-mb").forEach(t=>{t.addEventListener("click",()=>{const i=t.getAttribute("data-status")||"";this.filterStatus=this.filterStatus===i?"":i,this.applyFilters()})}),e.querySelectorAll(".lvl1-date-hdr").forEach(t=>{t.addEventListener("click",()=>{const i=t.getAttribute("data-dkey");i&&(this.expandedDates.has(i)?this.expandedDates.delete(i):this.expandedDates.add(i),this.updateUI())})}),e.querySelectorAll(".lvl2-partner-hdr").forEach(t=>{t.addEventListener("click",i=>{i.stopPropagation();const a=t.getAttribute("data-pkey");a&&(this.expandedPartners.has(a)?this.expandedPartners.delete(a):this.expandedPartners.add(a),this.updateUI())})}),e.querySelectorAll(".act-btn").forEach(t=>{t.addEventListener("click",()=>{const i=Number(t.getAttribute("data-id")),a=t.getAttribute("data-act")||"",n=this.rows.find(r=>r.id===i);n&&this.openActionModal(n,a)})}),e.querySelectorAll(".act-btn-bnz-app").forEach(t=>{t.addEventListener("click",()=>{const i=Number(t.getAttribute("data-claimid"));this.approveBonanza(i)})}),e.querySelectorAll(".act-btn-fa-1").forEach(t=>{t.addEventListener("click",()=>{const i=Number(t.getAttribute("data-faid"));this.faStage1(i)})}),e.querySelectorAll(".act-btn-fa-2").forEach(t=>{t.addEventListener("click",()=>{const i=Number(t.getAttribute("data-faid"));this.faStage2(i)})}))}openActionModal(e,t){this.activeModalRow=e,this.activeModalAction=t,this.paymentMode="BANK";const i=document.getElementById("actModalOverlay");if(!i)return;const a={confirm:"Confirm Income Entry",stage1_approve:"Stage 1 Approve",mark_paid:"Mark as Paid (Stage 2)",reject:"Reject Entry"};i.innerHTML=`
      <div style="background:#fff;border-radius:14px;padding:20px;width:100%;max-width:440px;box-shadow:0 20px 60px rgba(0,0,0,0.3)">
        <div style="font-size:16px;font-weight:800;color:#111827;margin-bottom:12px">
          ${a[t]||t}
        </div>
        <div style="font-size:12px;color:#6b7280;margin-bottom:12px">
          Entry: <strong style="color:#111827">${this.escape(e.entry_number)}</strong> · Partner: <strong>${this.escape(e.partner_name)}</strong>
        </div>

        ${t==="mark_paid"?`
          <div style="margin-bottom:12px">
            <label style="font-size:11px;font-weight:700;color:#374151;display:block;margin-bottom:4px">PAYMENT MODE</label>
            <div style="display:flex;gap:6px">
              <button type="button" id="modeBankBtn" style="flex:1;padding:8px;border:1.5px solid #059669;border-radius:8px;background:#059669;color:#fff;font-size:12px;font-weight:700">Bank Transfer</button>
              <button type="button" id="modeCashBtn" style="flex:1;padding:8px;border:1.5px solid #d1d5db;border-radius:8px;background:#fff;color:#374151;font-size:12px;font-weight:700">Cash</button>
            </div>
          </div>
          <div id="bankFields">
            <label style="font-size:11px;font-weight:700;color:#374151;display:block;margin-bottom:4px">UTR / REFERENCE NUMBER *</label>
            <input type="text" id="modalUtrInp" placeholder="e.g. UTR123456789" style="width:100%;padding:8px;border:1.5px solid #d1d5db;border-radius:8px;font-size:12px;margin-bottom:12px">
          </div>
        `:""}

        ${t==="reject"?`
          <div style="margin-bottom:12px">
            <label style="font-size:11px;font-weight:700;color:#374151;display:block;margin-bottom:4px">REJECTION REASON *</label>
            <textarea id="modalRejReason" rows="3" placeholder="Provide reason for rejection" style="width:100%;padding:8px;border:1.5px solid #d1d5db;border-radius:8px;font-size:12px"></textarea>
          </div>
        `:""}

        <div style="margin-bottom:14px">
          <label style="font-size:11px;font-weight:700;color:#374151;display:block;margin-bottom:4px">NOTES (OPTIONAL)</label>
          <input type="text" id="modalNotesInp" placeholder="Optional notes" style="width:100%;padding:8px;border:1.5px solid #d1d5db;border-radius:8px;font-size:12px">
        </div>

        <div style="display:flex;gap:8px;justify-content:flex-end">
          <button id="modalCancelBtn" style="background:#fff;border:1.5px solid #d1d5db;padding:8px 16px;border-radius:8px;font-size:13px;font-weight:600;color:#374151">Cancel</button>
          <button id="modalSubmitBtn" style="background:${t==="reject"?"#dc2626":"#059669"};color:#fff;border:none;padding:8px 20px;border-radius:8px;font-size:13px;font-weight:700">Submit</button>
        </div>
      </div>
    `,i.style.display="flex",document.getElementById("modalCancelBtn")?.addEventListener("click",()=>{i.style.display="none"}),document.getElementById("modalSubmitBtn")?.addEventListener("click",()=>{this.submitModalAction()})}async submitModalAction(){if(!this.activeModalRow)return;const e=this.activeModalRow,t=this.activeModalAction,i=document.getElementById("modalNotesInp")?.value.trim(),a={entry_id:e.id,action:t};if(i&&(a.notes=i),t==="reject"){const n=document.getElementById("modalRejReason")?.value.trim();if(!n){alert("Rejection reason is required");return}a.rejection_reason=n}else if(t==="mark_paid"&&(a.payment_mode=this.paymentMode,this.paymentMode==="BANK")){const n=document.getElementById("modalUtrInp")?.value.trim();if(!n){alert("UTR reference number is required");return}a.payment_utr=n,a.bank_ledger_id=1}try{const n=await m.post(`/vgk/staff/vgk/cash-income/unified-action?company_id=${e.company_id||2}`,a);n.success?(document.getElementById("actModalOverlay").style.display="none",this.loadData()):alert("Action failed: "+(n.error||"Unknown error"))}catch(n){alert("Action error: "+n?.message)}}async approveBonanza(e){if(confirm("Release this bonanza payment? Wallet will be credited."))try{const t=await m.post(`/bonanza/vgk/claims/${e}/status`,{status:"Payment Released"});t.success?this.loadData():alert("Release failed: "+(t.error||"Error"))}catch(t){alert("Release error: "+t?.message)}}async faStage1(e){if(confirm("Approve this field allowance (Stage 1)?"))try{const t=await m.post(`/vgk/staff/vgk/field-allowances/${e}/stage1-approve`,{});t.success?this.loadData():alert("Approval failed: "+(t.error||"Error"))}catch(t){alert("Approval error: "+t?.message)}}async faStage2(e){if(confirm("Mark this field allowance as Paid (Stage 2)?"))try{const t=await m.post(`/vgk/staff/vgk/field-allowances/${e}/stage2-mark-paid`,{});t.success?this.loadData():alert("Mark paid failed: "+(t.error||"Error"))}catch(t){alert("Mark paid error: "+t?.message)}}parseIsoDate(e){if(!e||e==="null"||e==="undefined")return null;const t=String(e).trim();if(!t)return null;if(/^\d{4}-\d{2}-\d{2}$/.test(t))return new Date(t+"T00:00:00+05:30");const i=t.endsWith("Z")||t.includes("+")?t:t+"+05:30",a=new Date(i);if(!isNaN(a.getTime()))return a;const n=new Date(t);return isNaN(n.getTime())?null:n}fmtDate(e){const t=this.parseIsoDate(e);return t?t.toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"numeric"}):"—"}getDateKey(e){const t=this.parseIsoDate(e);return t?t.getFullYear()+"-"+String(t.getMonth()+1).padStart(2,"0")+"-"+String(t.getDate()).padStart(2,"0"):"NO_DATE"}fmt(e){return"₹"+Number(e||0).toLocaleString("en-IN",{minimumFractionDigits:0,maximumFractionDigits:2})}escape(e){return String(e??"").replace(/[&<>"']/g,t=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"})[t]||t)}}export{ce as A,X as B,J as C,Q as D,re as V,ee as a,de as b,V as c,ie as d,pe as e,N as f,fe as g,ge as h,K as i,G as j,O as k,F as l,ne as m,q as n,H as o,j as p,ue as q,W as r,oe as s,Y as t,U as u,se as v,te as w,Z as x,ae as y,le as z};
