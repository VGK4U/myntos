import{a as A,d as b,b as d,r as f}from"./services-AEce4KDH.js";import{m as I,M as m,P as l}from"./components-9q5I9H7Z.js";import{P as _,S as z,c as N,C as G,b as O,a as Y}from"./vendor-capacitor-plugins-CPV63GsB.js";const W=A.MEDIA_BASE_URL,P="mnr_terms_accepted";class ee{container;user=null;data=null;loading=!0;banners=[];latestEarners=[];showTermsPopup=!1;isBirthday=!1;insuranceStatus=null;bannerDismissed=!1;constructor(e){this.container=e}async init(){const e=b.getAuthState();this.user=e.user,I.setUser(this.user),await this.checkTermsAcceptance(),this.render(),await this.loadDashboard(),this.showTermsPopup&&this.renderTermsPopup()}async checkTermsAcceptance(){try{const t=(await d.get("/auth/me"))?.data?.accepted_terms_version||null,a=await d.get("/auth/public/terms-and-conditions"),i=a?.data?.version||"1.0";if(this.currentTCVersion=i,t&&t===i){this.showTermsPopup=!1;return}const n=this.user?.mnr_id||this.user?.id||"",s=`${P}_${n}_v${i}`,{value:r}=await _.get({key:s}),o=`terms_shown_count_${n}_v${i}`,{value:c}=await _.get({key:o}),p=parseInt(c||"0"),g=a?.data?.max_displays||3;!r&&p<g?(this.showTermsPopup=!0,await _.set({key:o,value:(p+1).toString()})):this.showTermsPopup=!1}catch{this.showTermsPopup=!0}}currentTCVersion="1.0";async acceptTerms(){try{const e=this.user?.mnr_id||this.user?.id||"",t=this.currentTCVersion;await d.post("/users/accept-terms",{version:t});const a=`${P}_${e}_v${t}`;await _.set({key:a,value:new Date().toISOString()}),this.showTermsPopup=!1,this.closeTermsPopup()}catch(e){console.error("[MNRDashboard] Failed to save terms acceptance:",e)}}checkBirthday(){const e=this.data?.profile?.date_of_birth||this.user?.date_of_birth;if(!e){this.isBirthday=!1;return}try{const t=new Date,a=new Date(e);this.isBirthday=t.getMonth()===a.getMonth()&&t.getDate()===a.getDate()}catch{this.isBirthday=!1}}async loadDashboard(){this.loading=!0,this.updateContent();const{value:e}=await _.get({key:"mnr_banner_dismissed"});this.bannerDismissed=e==="true";try{const[t,a,i,n]=await Promise.all([d.get("/users/dashboard-data-fast"),d.get("/banners/dashboard-data").catch(()=>({success:!1,data:null})),d.get("/banners/top-performers?limit=7").catch(()=>({success:!1,data:null})),this.bannerDismissed?Promise.resolve({success:!1,data:null}):d.get("/users/my-insurance-status").catch(()=>({success:!1,data:null}))]);if(t.success&&t.data&&(this.data=t.data,this.checkBirthday()),a.success&&a.data){const r=a.data.image_banners||[];this.banners=r.map(o=>({id:o.id,title:o.title||"Banner",image_content:o.image_content,text_content:o.text_content}))}if(i.success&&i.data){const s=i.data.top_performers||i.data||[];this.latestEarners=Array.isArray(s)?s.map(r=>({name:r.name||"",mnr_id:r.user_id||r.mnr_id||"",amount:r.total_earnings||r.amount||0})):[]}n.success&&n.data&&(this.insuranceStatus=n.data)}catch(t){console.error("[MNRDashboard] Failed to load:",t)}this.loading=!1,this.updateContent(),this.setupBannerDismiss()}render(){const e=this.user?.name||this.user?.mnr_id||"Member",t=this.user?.mnr_id||"";this.container.innerHTML=`
      <style>
        .mnr-dashboard { background: linear-gradient(135deg, #0a1929 0%, #0d2137 100%); min-height: 100vh; }
        .mnr-dashboard-header {
          background: linear-gradient(135deg, #7c3aed 0%, #5b21b6 100%);
          padding: 16px;
          display: flex;
          align-items: center;
          justify-content: space-between;
        }
        .mnr-header-left { display: flex; align-items: center; gap: 12px; }
        .mnr-hamburger-btn {
          background: rgba(255, 255, 255, 0.15);
          border: none;
          border-radius: 8px;
          padding: 10px;
          color: white;
          cursor: pointer;
        }
        .mnr-header-user { display: flex; align-items: center; gap: 10px; }
        .mnr-header-avatar {
          width: 40px;
          height: 40px;
          border-radius: 50%;
          background: rgba(255, 255, 255, 0.2);
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: 600;
          font-size: 14px;
          color: white;
        }
        .mnr-header-info { display: flex; flex-direction: column; }
        .mnr-header-name { font-size: 14px; font-weight: 600; color: white; }
        .mnr-header-id { font-size: 11px; color: rgba(255, 255, 255, 0.8); }
        .mnr-share-btn {
          display: flex;
          align-items: center;
          gap: 6px;
          background: rgba(255, 255, 255, 0.15);
          border: none;
          border-radius: 8px;
          padding: 8px 12px;
          color: white;
          font-size: 12px;
          cursor: pointer;
        }
        .dashboard-content { padding: 16px; }
        .loading-state { text-align: center; padding: 40px; color: #8892b0; }

        /* Birthday Banner */
        .birthday-banner {
          background: linear-gradient(135deg, #ec4899 0%, #f472b6 50%, #fbbf24 100%);
          border-radius: 12px;
          padding: 20px;
          margin-bottom: 16px;
          text-align: center;
          animation: celebrate 2s ease-in-out infinite;
        }
        @keyframes celebrate {
          0%, 100% { transform: scale(1); }
          50% { transform: scale(1.02); }
        }
        .birthday-banner h3 { margin: 0 0 8px; font-size: 20px; color: white; }
        .birthday-banner p { margin: 0; font-size: 14px; color: rgba(255, 255, 255, 0.9); }

        /* Insurance Banner - DC Protocol Feb 2026 */
        .insurance-banner {
          border-radius: 12px;
          padding: 20px;
          margin-bottom: 16px;
          text-align: center;
        }
        .insurance-banner.insured {
          background: linear-gradient(135deg, #059669 0%, #047857 100%);
        }
        .insurance-banner.eligible {
          background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
        }
        .insurance-banner.service-required {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        .insurance-banner .insurance-icon { font-size: 32px; margin-bottom: 8px; }
        .insurance-banner h4 { margin: 0 0 6px; font-size: 16px; color: white; font-weight: 600; }
        .insurance-banner p { margin: 0; font-size: 13px; color: rgba(255, 255, 255, 0.9); line-height: 1.4; }
        .insurance-banner .policy-details { margin-top: 8px; font-size: 11px; color: rgba(255, 255, 255, 0.8); }

        /* Active Banners - Web Style */
        .mnr-banner-section { margin-bottom: 16px; }
        .mnr-banner-slide {
          background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
          border-radius: 10px;
          padding: 16px 20px;
          text-align: center;
          margin-bottom: 8px;
        }
        .mnr-banner-slide h4 { margin: 0; font-size: 15px; color: #451a03; font-weight: 600; }

        /* Latest Earners - Web Parity */
        .latest-earners-section {
          background: linear-gradient(135deg, #1e3a5f 0%, #0f2744 100%);
          border-radius: 12px;
          padding: 16px;
          margin-bottom: 16px;
        }
        .latest-earners-header {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 16px;
          justify-content: center;
        }
        .latest-earners-header h3 { margin: 0; font-size: 14px; color: #fbbf24; }
        .earners-carousel {
          display: flex;
          gap: 12px;
          overflow-x: auto;
          padding-bottom: 8px;
          scroll-snap-type: x mandatory;
        }
        .earners-carousel::-webkit-scrollbar { height: 4px; }
        .earners-carousel::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.2); border-radius: 2px; }
        .earner-card {
          flex: 0 0 auto;
          min-width: 140px;
          background: linear-gradient(135deg, #16213e 0%, #1a1a2e 100%);
          border: 2px solid #fbbf24;
          border-radius: 12px;
          padding: 16px;
          text-align: center;
          position: relative;
          scroll-snap-align: start;
        }
        .earner-medal {
          position: absolute;
          top: -12px;
          left: 50%;
          transform: translateX(-50%);
          font-size: 28px;
        }
        .earner-avatar {
          width: 56px;
          height: 56px;
          border-radius: 50%;
          background: linear-gradient(135deg, #7c3aed 0%, #a855f7 100%);
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: 700;
          font-size: 18px;
          color: white;
          margin: 8px auto 10px;
          border: 3px solid #fbbf24;
        }
        .earner-name { font-size: 13px; font-weight: 600; color: white; margin-bottom: 2px; }
        .earner-id { font-size: 10px; color: #8892b0; margin-bottom: 6px; }
        .earner-amount { font-size: 15px; font-weight: 700; color: #10b981; }

        /* Section Cards */
        .mnr-section-card { background: #ffffff;
          background: rgba(22, 33, 62, 0.95);
          border-radius: 10px;
          margin-bottom: 16px;
          overflow: hidden;
          border: 1px solid rgba(255, 255, 255, 0.1);
        }
        .section-header-bar {
          padding: 12px 16px;
          color: white;
        }
        .section-header-bar.green { background: linear-gradient(135deg, #16a34a 0%, #15803d 100%); }
        .section-header-bar.orange { background: linear-gradient(135deg, #ea580c 0%, #c2410c 100%); }
        .section-header-bar.purple { background: linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%); }
        .section-header-bar.blue { background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%); }
        .section-header-bar h3 { margin: 0; font-size: 13px; font-weight: 600; text-transform: uppercase; }
        .section-content { padding: 14px 16px; background: #ffffff; }
        .summary-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 8px 0;
          border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }
        .summary-row:last-child { border-bottom: none; }
        .summary-row .label { font-size: 12px; color: #4b5563; font-weight: 500; }
        .summary-row .value { font-size: 13px; color: #1f2937; font-weight: 600; }
        .badge-rank {
          background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
          color: white;
          padding: 4px 10px;
          border-radius: 4px;
          font-size: 11px;
          font-weight: 600;
        }
        .badge-rank.secondary {
          background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
        }
        .badge-status {
          padding: 4px 10px;
          border-radius: 4px;
          font-size: 11px;
          font-weight: 600;
        }
        .badge-status.active { background: #10b981; color: white; }
        .badge-status.inactive { background: #6b7280; color: white; }
        .counts-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 10px;
        }
        .count-item {
          display: flex;
          justify-content: space-between;
          background: #f3f4f6;
          padding: 10px 12px;
          border-radius: 6px;
        }
        .count-label { font-size: 11px; color: #4b5563; font-weight: 500; }
        .count-value { font-size: 13px; font-weight: 600; color: #10b981; }

        /* Quick Actions */
        .quick-actions { margin-top: 8px; }
        .section-title { font-size: 14px; color: #1f2937; margin: 0 0 12px; }
        .action-grid {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 10px;
        }
        .action-btn {
          background: rgba(22, 33, 62, 0.9);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 10px;
          padding: 14px 8px;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 6px;
          color: #e6f1ff;
          font-size: 11px;
          cursor: pointer;
        }
        .action-btn:active { background: rgba(124, 58, 237, 0.3); }
        .action-btn svg { color: #a855f7; }

        /* Terms Popup */
        .terms-overlay {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0, 0, 0, 0.8);
          z-index: 9999;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 20px;
        }
        .terms-modal {
          background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
          border-radius: 16px;
          max-width: 400px;
          width: 100%;
          max-height: 80vh;
          overflow: hidden;
          display: flex;
          flex-direction: column;
        }
        .terms-header {
          background: linear-gradient(135deg, #7c3aed 0%, #5b21b6 100%);
          padding: 24px 20px;
          text-align: center;
        }
        .terms-header h2 {
          margin: 0 0 6px;
          font-size: 18px;
          color: white;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
        }
        .terms-header p { margin: 0; font-size: 13px; color: rgba(255, 255, 255, 0.8); }
        .terms-body {
          padding: 20px;
          overflow-y: auto;
          flex: 1;
        }
        .terms-section-title {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 15px;
          color: #10b981;
          margin: 0 0 10px;
          font-weight: 600;
        }
        .terms-text {
          font-size: 13px;
          color: #9ca3af;
          line-height: 1.6;
          margin-bottom: 16px;
        }
        .terms-important {
          background: rgba(239, 68, 68, 0.1);
          border: 1px solid rgba(239, 68, 68, 0.3);
          border-radius: 8px;
          padding: 12px;
          margin-bottom: 16px;
        }
        .terms-important-title {
          display: flex;
          align-items: center;
          gap: 6px;
          font-size: 13px;
          color: #f59e0b;
          margin: 0 0 8px;
          font-weight: 600;
        }
        .terms-notice {
          background: rgba(239, 68, 68, 0.2);
          border-left: 4px solid #ef4444;
          padding: 10px 12px;
          margin-bottom: 8px;
        }
        .terms-notice-title { font-size: 13px; font-weight: 600; color: white; margin: 0 0 6px; }
        .terms-notice-list {
          margin: 0;
          padding-left: 16px;
          font-size: 12px;
          color: #d1d5db;
          line-height: 1.6;
        }
        .terms-warning {
          background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
          border-radius: 8px;
          padding: 12px;
          margin-top: 16px;
        }
        .terms-warning p {
          margin: 0;
          font-size: 12px;
          color: #78350f;
          line-height: 1.5;
        }
        .terms-warning strong { color: #dc2626; }
        .terms-footer {
          padding: 16px 20px;
          background: rgba(0, 0, 0, 0.2);
        }
        .terms-accept-btn {
          width: 100%;
          padding: 14px;
          background: linear-gradient(135deg, #10b981 0%, #059669 100%);
          border: none;
          border-radius: 8px;
          color: white;
          font-size: 15px;
          font-weight: 600;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
        }
        .terms-accept-btn:active { opacity: 0.9; }
      </style>

      <div class="page-container mnr-dashboard">
        <header class="mnr-dashboard-header">
          <div class="mnr-header-left">
            <button class="mnr-hamburger-btn" id="mnrHamburgerBtn">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/>
              </svg>
            </button>
            <div class="mnr-header-user">
              <div class="mnr-header-avatar">${this.getInitials(e)}</div>
              <div class="mnr-header-info">
                <span class="mnr-header-name">${e}</span>
                <span class="mnr-header-id">${t}</span>
              </div>
            </div>
          </div>
          <div class="mnr-header-actions">
            <button class="mnr-share-btn" id="shareBtn">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/>
                <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>
              </svg>
              Share
            </button>
          </div>
        </header>

        <div class="dashboard-content" id="dashboardContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>

      <div id="termsPopupContainer"></div>
    `,this.attachListeners()}renderTermsPopup(){const e=document.getElementById("termsPopupContainer");e&&(e.innerHTML=`
      <div class="terms-overlay" id="termsOverlay">
        <div class="terms-modal">
          <div class="terms-header">
            <h2>🎉 Welcome to MyntReal Platform!</h2>
            <p>Your journey to success begins here</p>
          </div>
          <div class="terms-body">
            <h3 class="terms-section-title">📋 Terms and Conditions</h3>
            <p class="terms-text">Please read and accept our terms and conditions to continue using the platform.</p>

            <h4 class="terms-section-title">📜 Terms & Conditions</h4>
            <p class="terms-text">Welcome to MNR Business Access Program! We are glad to have you as part of our community. Please take a moment to review these terms to understand how our platform operates.</p>

            <div class="terms-important">
              <h5 class="terms-important-title">⚠️ Important System Information</h5>
              <div class="terms-notice">
                <p class="terms-notice-title">MNR Independence Notice:</p>
                <ul class="terms-notice-list">
                  <li>MNR operates as an independent platform and is not related to any previous systems such as BeV or similar programs.</li>
                  <li>While we maintain legacy data from prior systems for record-keeping purposes, MNR is a completely new and separate entity.</li>
                  <li>All operations, policies, and procedures are governed solely by MNR guidelines.</li>
                </ul>
              </div>
            </div>

            <div class="terms-warning">
              <p><strong>⚠️ Important:</strong> By clicking "I Accept", you acknowledge that you have read, understood, and agree to these terms and conditions.</p>
            </div>
          </div>
          <div class="terms-footer">
            <button class="terms-accept-btn" id="acceptTermsBtn">
              ✓ I Accept
            </button>
          </div>
        </div>
      </div>
    `,document.getElementById("acceptTermsBtn")?.addEventListener("click",()=>{this.acceptTerms()}))}closeTermsPopup(){const e=document.getElementById("termsOverlay");e&&e.remove()}attachListeners(){document.getElementById("mnrHamburgerBtn")?.addEventListener("click",()=>{I.open()}),document.getElementById("shareBtn")?.addEventListener("click",()=>{this.handleShare()})}async handleShare(){const e=this.data?.profile?.mnr_id||this.user?.id||"",t=`${W}/signup?ref=${e}`,a=`Join MNR Business Access Program using my referral link: ${t}`;try{await z.share({title:"Join MNR Business Access Program",text:a,url:t,dialogTitle:"Share Referral Link"})}catch{console.log("[MNRDashboard] Share failed, copying to clipboard");try{await N.write({string:a}),alert("Referral link copied to clipboard!")}catch(n){console.error("[MNRDashboard] Clipboard write failed:",n),alert("Could not share or copy link")}}}calculateDirectReferralRank(e){return e>=50?"Future Elite Master":e>=25?"Super Platinum Star":e>=15?"Super Elite Star":e>=10?"Super Gold Star":e>=8?"Super Silver Star":e>=5?"Super Prime Star":e>=1?"Super Star":"Yet to achieve"}calculateMatchingReferralRank(e){const t=Math.round(e||0);return t>=25e4?"Crown Ambassador":t>=5e4?"Diamond":t>=1e4?"Emerald":t>=5e3?"Sapphire":t>=300?"Ruby":t>=250?"Pearl":t>=120?"Platinum Star":t>=50?"Super Star":t>=35?"Gold Star":t>=25?"Silver Star":t>=3?"Prime Star":t>=1?"Star":"Yet to achieve"}updateContent(){const e=document.getElementById("dashboardContent");if(!e)return;if(this.loading){e.innerHTML='<div class="loading-state">Loading...</div>';return}const t=this.data?.profile||{},a=this.data?.team||{direct_referrals:0,matching_referrals_count:0,binary_tree:{left_count:0,right_count:0,total_count:0},binary_tree_active:{left_count:0,right_count:0}},i=this.data?.activated||{direct_activated:0},n=this.data?.ved||{ved_team_total:0,ved_team_activated:0},s=this.data?.previous_counts||{direct_referrals:0,direct_activated:0,my_team:0,matching:0,left_team:0,left_active:0,right_team:0,right_active:0,ved_overall:0,ved_activated:0};e.innerHTML=`
      <!-- Birthday Banner -->
      ${this.renderBirthdayBanner()}

      <!-- Insurance Banner - DC Protocol Feb 2026 -->
      ${this.renderInsuranceBanner()}

      <!-- Active Banners Section -->
      ${this.renderBanners()}

      <!-- Latest Earners Section -->
      ${this.renderLatestEarners()}

      <!-- Personal Summary Section -->
      <div class="mnr-section-card personal-summary">
        <div class="section-header-bar green">
          <h3>PERSONAL SUMMARY</h3>
        </div>
        <div class="section-content">
          <div class="summary-row">
            <span class="label">Name:</span>
            <span class="value">${t.name||this.user?.name||"-"}</span>
          </div>
          <div class="summary-row">
            <span class="label">Member Id:</span>
            <span class="value">${t.mnr_id||this.user?.mnr_id||"-"}</span>
          </div>
          <div class="summary-row">
            <span class="label">Direct Connections Rank:</span>
            <span class="value badge-rank">${t.direct_referral_rank||this.calculateDirectReferralRank(a.direct_referrals||0)}</span>
          </div>
          <div class="summary-row">
            <span class="label">Group Performance Recognition Rank:</span>
            <span class="value badge-rank secondary">${t.matching_referral_rank||this.calculateMatchingReferralRank(a.matching_referrals_count||0)}</span>
          </div>
        </div>
      </div>

      <!-- My Summary Section -->
      <div class="mnr-section-card my-summary">
        <div class="section-header-bar orange">
          <h3>MY SUMMARY</h3>
        </div>
        <div class="section-content">
          <div class="summary-row">
            <span class="label">Registration Date:</span>
            <span class="value">${this.formatDate(t.registration_date)}</span>
          </div>
          <div class="summary-row">
            <span class="label">Active Status:</span>
            <span class="value badge-status ${t.active_status?"active":"inactive"}">${t.active_status?"Activated":"Pending"}</span>
          </div>
          <div class="summary-row">
            <span class="label">Active Date:</span>
            <span class="value">${this.formatDate(t.active_date)}</span>
          </div>
          <div class="summary-row">
            <span class="label">Package:</span>
            <span class="value">${t.package||"-"}</span>
          </div>
        </div>
      </div>

      <!-- Overall Counts Section -->
      <div class="mnr-section-card overall-counts">
        <div class="section-header-bar purple">
          <h3>📊 Overall - Counts</h3>
        </div>
        <div class="section-content counts-grid">
          <div class="count-item">
            <span class="count-label">My Direct Connections:</span>
            <span class="count-value">${a.direct_referrals||0}</span>
          </div>
          <div class="count-item">
            <span class="count-label">Active Direct:</span>
            <span class="count-value">${i.direct_activated||0}</span>
          </div>
          <div class="count-item">
            <span class="count-label">My Team:</span>
            <span class="count-value">${a.binary_tree?.total_count||0}</span>
          </div>
          <div class="count-item">
            <span class="count-label">Group Performance Recognition:</span>
            <span class="count-value">${a.matching_referrals_count||0}</span>
          </div>
          <div class="count-item">
            <span class="count-label">Group A Team:</span>
            <span class="count-value">${a.binary_tree?.left_count||0}</span>
          </div>
          <div class="count-item">
            <span class="count-label">Group A Active:</span>
            <span class="count-value">${a.binary_tree_active?.left_count||0}</span>
          </div>
          <div class="count-item">
            <span class="count-label">Group B Team:</span>
            <span class="count-value">${a.binary_tree?.right_count||0}</span>
          </div>
          <div class="count-item">
            <span class="count-label">Group B Active:</span>
            <span class="count-value">${a.binary_tree_active?.right_count||0}</span>
          </div>
          <div class="count-item">
            <span class="count-label">Ved Overall:</span>
            <span class="count-value">${n.ved_team_total||0}</span>
          </div>
          <div class="count-item">
            <span class="count-label">Ved Activated:</span>
            <span class="count-value">${n.ved_team_activated||0}</span>
          </div>
        </div>
      </div>

      <!-- Previous Counts Section -->
      <div class="mnr-section-card previous-counts">
        <div class="section-header-bar blue">
          <h3>📈 Previous - Counts</h3>
        </div>
        <div class="section-content counts-grid">
          <div class="count-item">
            <span class="count-label">My Direct Connections:</span>
            <span class="count-value">${s.direct_referrals||0}</span>
          </div>
          <div class="count-item">
            <span class="count-label">Active Direct:</span>
            <span class="count-value">${s.direct_activated||0}</span>
          </div>
          <div class="count-item">
            <span class="count-label">My Team:</span>
            <span class="count-value">${s.my_team||0}</span>
          </div>
          <div class="count-item">
            <span class="count-label">Group Performance Recognition:</span>
            <span class="count-value">${s.matching||0}</span>
          </div>
          <div class="count-item">
            <span class="count-label">Group A Team:</span>
            <span class="count-value">${s.left_team||0}</span>
          </div>
          <div class="count-item">
            <span class="count-label">Group A Active:</span>
            <span class="count-value">${s.left_active||0}</span>
          </div>
          <div class="count-item">
            <span class="count-label">Group B Team:</span>
            <span class="count-value">${s.right_team||0}</span>
          </div>
          <div class="count-item">
            <span class="count-label">Group B Active:</span>
            <span class="count-value">${s.right_active||0}</span>
          </div>
          <div class="count-item">
            <span class="count-label">Ved Overall:</span>
            <span class="count-value">${s.ved_overall||0}</span>
          </div>
          <div class="count-item">
            <span class="count-label">Ved Activated:</span>
            <span class="count-value">${s.ved_activated||0}</span>
          </div>
        </div>
      </div>

      <!-- Quick Actions -->
      <div class="quick-actions">
        <h3 class="section-title">Quick Actions</h3>
        <div class="action-grid">
          <button class="action-btn" data-page="mnr-income">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
            </svg>
            <span>Income</span>
          </button>
          <button class="action-btn" data-page="mnr-withdrawals">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="1" y="4" width="22" height="16" rx="2" ry="2"/><line x1="1" y1="10" x2="23" y2="10"/>
            </svg>
            <span>Withdraw</span>
          </button>
          <button class="action-btn" data-page="mnr-benefits">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="8" r="7"/><polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"/>
            </svg>
            <span>Benefits</span>
          </button>
          <button class="action-btn" data-page="mnr-announcements">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/>
            </svg>
            <span>News</span>
          </button>
        </div>
      </div>
    `,e.querySelectorAll("[data-page]").forEach(r=>{r.addEventListener("click",()=>{const o=r.getAttribute("data-page");o&&f.navigate(o)})})}renderBirthdayBanner(){return this.isBirthday?`
      <div class="birthday-banner">
        <h3>🎂 Happy Birthday, ${this.data?.profile?.name||this.user?.name||"Member"}! 🎉</h3>
        <p>Wishing you a wonderful day filled with joy and success!</p>
      </div>
    `:""}renderInsuranceBanner(){if(!this.insuranceStatus||!this.insuranceStatus.show_banner||this.bannerDismissed)return"";const e=this.insuranceStatus,t=e.kyc_approved?'<span style="background:#059669;padding:2px 8px;border-radius:8px;font-size:10px;font-weight:600;color:white;">KYC Approved</span>':'<span style="background:#dc2626;padding:2px 8px;border-radius:8px;font-size:10px;font-weight:600;color:white;">KYC: '+(e.kyc_status||"Pending")+"</span>",a=e.kyc_approved?"":'<div style="margin-top:10px;padding:8px 12px;background:rgba(255,255,255,0.15);border-radius:8px;border:1px solid rgba(255,255,255,0.3);font-size:12px;">⚠️ <strong>Complete your KYC</strong> to get your insurance processed.</div>',i=`<div style="position:absolute;top:8px;right:8px;"><button class="ins-banner-close" style="background:rgba(255,255,255,0.2);border:none;color:white;width:24px;height:24px;border-radius:50%;font-size:12px;cursor:pointer;">✕</button></div><div style="text-align:right;margin-top:6px;"><a href="javascript:void(0)" class="ins-banner-dismiss-permanent" style="color:rgba(255,255,255,0.6);font-size:10px;text-decoration:underline;">Don't show again</a></div>`;let n="",s="";if(e.banner_type==="insured")s="insured",n='<div class="insurance-icon">🛡️</div><h4>You are Insured! '+t+'</h4><p>Rs. 5,00,000 Accidental Insurance Coverage</p><p class="policy-details"><strong>Policy:</strong> '+(e.policy_number||"N/A")+" | <strong>Valid until:</strong> "+(e.expiry_date||"N/A")+" ("+(e.days_remaining||0)+" days remaining)</p>";else if(e.banner_type==="eligible")s="eligible",n='<div class="insurance-icon">✓</div><h4>You are Eligible for Insurance! '+t+"</h4><p>Rs. 5,00,000 Accidental Insurance - Your insurance is being processed</p>"+a;else if(e.banner_type==="referral_required"){s="service-required";const r=e.group_a_referrals||0,o=e.group_b_referrals||0,c=e.referrals_count||0,p=e.referrals_needed||2;n='<div class="insurance-icon">👥</div><h4>Unlock Free Insurance! '+t+'</h4><p>Get Rs. 5,00,000 Accidental Insurance by referring 2 members who activate after Feb 3, 2026</p><div style="display:flex;justify-content:center;gap:16px;margin:10px 0;"><div style="background:rgba(255,255,255,0.15);padding:8px 16px;border-radius:8px;min-width:90px;"><div style="font-size:20px;font-weight:700;">'+r+'</div><div style="font-size:10px;opacity:0.85;">Group A</div></div><div style="background:rgba(255,255,255,0.15);padding:8px 16px;border-radius:8px;min-width:90px;"><div style="font-size:20px;font-weight:700;">'+o+'</div><div style="font-size:10px;opacity:0.85;">Group B</div></div></div><p style="font-size:12px;"><strong>Total:</strong> '+c+" / "+p+' referrals</p><div style="background:rgba(255,255,255,0.3);border-radius:20px;height:8px;margin:6px auto;max-width:200px;"><div style="background:white;border-radius:20px;height:100%;width:'+Math.min(100,c/p*100)+'%;"></div></div>'+a}else if(e.banner_type==="not_activated")s="service-required",n='<div class="insurance-icon">ℹ️</div><h4>Activate Your Membership '+t+"</h4><p>Activate your membership to unlock Rs. 5,00,000 Accidental Insurance and other benefits</p>"+a;else if(e.banner_type==="service_required")s="service-required",n='<div class="insurance-icon">⚡</div><h4>Unlock Free Insurance! '+t+"</h4><p>Get Rs. 5,00,000 Accidental Insurance by using your points for Solar, EV, Real Dreams, or Care services</p>"+a;else return"";return'<div class="insurance-banner '+s+'" style="position:relative;" id="mobileInsuranceBanner">'+i+n+"</div>"}setupBannerDismiss(){const e=this.container.querySelector(".ins-banner-close");e&&e.addEventListener("click",()=>{const a=document.getElementById("mobileInsuranceBanner");a&&(a.style.display="none")});const t=this.container.querySelector(".ins-banner-dismiss-permanent");t&&t.addEventListener("click",async()=>{await _.set({key:"mnr_banner_dismissed",value:"true"}),this.bannerDismissed=!0;const a=document.getElementById("mobileInsuranceBanner");a&&(a.style.display="none")})}renderBanners(){return!this.banners||this.banners.length===0?"":`
      <div class="mnr-banner-section">
        ${this.banners.map(e=>{let t="";return e.image_content?t=e.image_content.startsWith("data:")||e.image_content.startsWith("/")?e.image_content:"/storage/"+e.image_content:e.image_url&&(t=e.image_url),`
            <div class="mnr-banner-slide">
              ${t?`<img src="${t}" alt="${e.title||"Banner"}" style="max-width: 100%; max-height: 300px; border-radius: 8px; object-fit: contain;" />`:""}
              ${e.text_content?`<div style="padding: 8px; color: white; font-weight: 500; font-size: 13px;">${e.text_content}</div>`:""}
              ${!t&&!e.text_content?`<h4>${e.title}</h4>`:""}
            </div>
          `}).join("")}
      </div>
    `}renderLatestEarners(){return!this.latestEarners||this.latestEarners.length===0?"":`
      <div class="latest-earners-section">
        <div class="latest-earners-header">
          <span>🏆</span>
          <h3>Top Performers - Recognition Achievers</h3>
        </div>
        <div class="earners-carousel">
          ${this.latestEarners.slice(0,10).map((e,t)=>`
            <div class="earner-card">
              <div class="earner-medal">${t===0?"🥇":t===1?"🥈":t===2?"🥉":"🏅"}</div>
              <div class="earner-avatar">${this.getInitials(e.name)}</div>
              <div class="earner-name">${e.name}</div>
              <div class="earner-id">${e.mnr_id}</div>
              <div class="earner-amount">₹${e.amount.toLocaleString()}</div>
            </div>
          `).join("")}
        </div>
      </div>
    `}formatDate(e){if(!e)return"-";try{return new Date(e).toLocaleDateString("en-IN",{day:"2-digit",month:"2-digit",year:"numeric",hour:"2-digit",minute:"2-digit"})}catch{return e}}getInitials(e){return e.split(" ").map(t=>t[0]).join("").toUpperCase().slice(0,2)}}class te{container;records=[];summary=null;loading=!0;activeTab="all";constructor(e){this.container=e}async init(){this.render(),await this.loadIncome()}async loadIncome(){this.loading=!0,this.updateContent();try{const e=await d.get("/users/earnings-summary");if(e.success&&e.data){const a=e.data;this.summary={direct_referral:a.direct_referral_total||a.direct_referral||0,matching_referral:a.matching_referral_total||a.matching_referral||0,ved_income:a.ved_income_total||a.ved_income||0,guru_dakshina:a.guru_dakshina_total||a.guru_dakshina||0,total:a.total_gross_earnings||a.total||(a.direct_referral_total||0)+(a.matching_referral_total||0)+(a.ved_income_total||0)+(a.guru_dakshina_total||0)}}const t={direct:"/financial-operations/income/me/direct-referral-transactions",matching:"/financial-operations/income/me/matching-referral-transactions",ved:"/financial-operations/income/me/ved-income-transactions",guru:"/financial-operations/income/me/guru-dakshina-transactions"};if(this.activeTab==="all"){const[a,i,n,s]=await Promise.all([d.get(t.direct),d.get(t.matching),d.get(t.ved),d.get(t.guru)]),r=[];a.success&&a.data&&(a.data.transactions||a.data.records||[]).forEach(c=>r.push(this.normalizeRecord(c,"Direct Business Facilitation"))),i.success&&i.data&&(i.data.transactions||i.data.records||[]).forEach(c=>r.push(this.normalizeRecord(c,"Group Performance Recognition"))),n.success&&n.data&&(n.data.transactions||n.data.records||[]).forEach(c=>r.push(this.normalizeRecord(c,"VED Leadership Recognition"))),s.success&&s.data&&(s.data.transactions||s.data.records||[]).forEach(c=>r.push(this.normalizeRecord(c,"Mentorship Contribution Benefit"))),this.records=r.sort((o,c)=>new Date(c.date).getTime()-new Date(o.date).getTime())}else{const a=t[this.activeTab];if(a){const i=await d.get(a);if(i.success&&i.data){const n=i.data.transactions||i.data.records||[];this.records=n.map(s=>this.normalizeRecord(s,this.getTypeLabel(this.activeTab)))}}}}catch(e){console.error("[MNRIncome] Failed to load:",e)}this.loading=!1,this.updateContent()}render(){this.container.innerHTML=`
      <style>
        ${m.getStyles()}
        .mnr-income-page { padding: 16px; }
        .income-summary {
          display: grid;
          grid-template-columns: 1fr;
          gap: 12px;
          margin-bottom: 16px;
        }
        .total-card {
          background: linear-gradient(135deg, #10b981 0%, #059669 100%);
          border-radius: 12px;
          padding: 20px;
          text-align: center;
          color: white;
        }
        .total-card .label { font-size: 12px; opacity: 0.9; margin-bottom: 4px; }
        .total-card .value { font-size: 32px; font-weight: 700; }
        .income-breakdown {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 8px;
        }
        .income-type-card {
          background: rgba(22, 33, 62, 0.8);
          border-radius: 8px;
          padding: 12px;
          text-align: center;
        }
        .income-type-card .label { font-size: 11px; color: #8892b0; text-transform: uppercase; }
        .income-type-card .value { font-size: 16px; font-weight: 600; color: #e6f1ff; }
        .tab-bar {
          display: flex;
          gap: 8px;
          margin-bottom: 16px;
          overflow-x: auto;
          padding-bottom: 8px;
        }
        .tab-btn {
          padding: 8px 16px;
          background: rgba(22, 33, 62, 0.8);
          border: 1px solid rgba(255,255,255,0.1);
          border-radius: 20px;
          color: #8892b0;
          font-size: 13px;
          white-space: nowrap;
          cursor: pointer;
        }
        .tab-btn.active {
          background: #64d2ff;
          border-color: #64d2ff;
          color: #0d1b2a;
          font-weight: 600;
        }
        .section-title {
          font-size: 16px;
          font-weight: 600;
          color: #e6f1ff;
          margin: 20px 0 12px;
        }
      </style>
      ${l.render({title:"Income",showBack:!0})}
      <div class="mnr-income-page">
        <div id="summarySection"></div>
        
        <h3 class="section-title">Transactions</h3>
        <div class="tab-bar" id="tabBar">
          <button class="tab-btn ${this.activeTab==="all"?"active":""}" data-tab="all">All</button>
          <button class="tab-btn ${this.activeTab==="direct"?"active":""}" data-tab="direct">Direct</button>
          <button class="tab-btn ${this.activeTab==="matching"?"active":""}" data-tab="matching">Matching</button>
          <button class="tab-btn ${this.activeTab==="ved"?"active":""}" data-tab="ved">Ved</button>
          <button class="tab-btn ${this.activeTab==="guru"?"active":""}" data-tab="guru">Guru</button>
        </div>
        
        <div id="pageContent"></div>
      </div>
    `,this.attachListeners()}attachListeners(){l.attachListeners({title:"Income",showBack:!0}),document.querySelectorAll(".tab-btn").forEach(e=>{e.addEventListener("click",()=>{this.activeTab=e.getAttribute("data-tab")||"all",document.querySelectorAll(".tab-btn").forEach(t=>t.classList.remove("active")),e.classList.add("active"),this.loadIncome()})})}updateContent(){const e=document.getElementById("summarySection");e&&this.summary&&(e.innerHTML=`
        <div class="income-summary">
          <div class="total-card">
            <div class="label">Total Earnings</div>
            <div class="value">₹${this.summary.total.toLocaleString()}</div>
          </div>
          <div class="income-breakdown">
            <div class="income-type-card">
              <div class="label">Direct Business Facilitation</div>
              <div class="value">₹${this.summary.direct_referral.toLocaleString()}</div>
            </div>
            <div class="income-type-card">
              <div class="label">Group Performance Recognition</div>
              <div class="value">₹${this.summary.matching_referral.toLocaleString()}</div>
            </div>
            <div class="income-type-card">
              <div class="label">VED Leadership Recognition</div>
              <div class="value">₹${this.summary.ved_income.toLocaleString()}</div>
            </div>
            <div class="income-type-card">
              <div class="label">Mentorship Contribution Benefit</div>
              <div class="value">₹${this.summary.guru_dakshina.toLocaleString()}</div>
            </div>
          </div>
        </div>
      `);const t=document.getElementById("pageContent");if(!t)return;const a=new m({columns:[{key:"type",label:"Type",render:i=>this.getTypeBadge(i)},{key:"from_user",label:"From User"},{key:"amount",label:"Amount",render:i=>`<span style="color: #10b981; font-weight: 600;">+₹${i.toLocaleString()}</span>`},{key:"date",label:"Date",render:i=>this.formatDate(i)},{key:"status",label:"Status",render:i=>this.getStatusBadge(i)}],data:this.records,loading:this.loading,emptyMessage:"No income transactions yet"});t.innerHTML=`
      <div class="table-summary-bar">
        <span>Total <span class="count">${this.records.length}</span> transactions</span>
      </div>
      ${a.render()}
    `}getTypeBadge(e){return`<span class="badge ${{"Direct Business Facilitation":"badge-info","Group Performance Recognition":"badge-primary","VED Leadership Recognition":"badge-warning","Mentorship Contribution Benefit":"badge-platinum"}[e]||"badge-secondary"}">${e}</span>`}getStatusBadge(e){const t=e.toLowerCase();return t==="completed"||t==="approved"?'<span class="badge badge-success">Completed</span>':t==="staff validated"||t==="staff_validated"?'<span class="badge badge-info">Staff Validated</span>':t==="cleared"?'<span class="badge badge-info">Cleared</span>':t==="pending"?'<span class="badge badge-warning">Pending Validation</span>':t==="rejected"?'<span class="badge badge-danger">Rejected</span>':`<span class="badge badge-secondary">${e}</span>`}formatDate(e){if(!e)return"-";try{return new Date(e).toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"numeric"})}catch{return e}}normalizeRecord(e,t){return{id:e.id||0,type:t,amount:e.total_amount||e.net_amount||e.amount||0,from_user:e.referred_user_name||e.for_member_name||e.from_member||e.name||"System",date:e.from_date||e.date||e.created_at||"",status:e.verification_status||e.status||"Completed"}}getTypeLabel(e){return{direct:"Direct Business Facilitation",matching:"Group Performance Recognition",ved:"VED Leadership Recognition",guru:"Mentorship Contribution Benefit"}[e]||e}}class T{container;dayRows=[];summary={total_earned:0,completed:0,pending_validation:0,staff_validated:0,rejected:0};loading=!0;startDate="";endDate="";statusFilter="";kycStatus="Approved";bankStatus="Approved";showKycWarning=!1;kycWarningMessage="";static STAFF_WORKFLOW_CUTOFF="2026-02-12";static INCOME_REBRAND_MAP={"Direct Referral":"Direct Business Facilitation","Matching Referral":"Group Performance Recognition","Ved Income":"VED Leadership Recognition","Guru Dakshina":"Mentorship Contribution Benefit"};constructor(e){this.container=e}async init(){this.render(),await Promise.all([this.checkKYCStatus(),this.loadTransactions()])}async checkKYCStatus(){try{const e=await d.get("/auth/me");if(e){const t=e.data||e,a=t.kyc_status||"Pending",i=t.bank_details_status||"Not Submitted";this.kycStatus=a,this.bankStatus=i,(a!=="Approved"||i!=="Approved")&&(this.showKycWarning=!0,a!=="Approved"&&i!=="Approved"?this.kycWarningMessage=`<strong>KYC Status:</strong> ${a} | <strong>Bank Status:</strong> ${i}<br>You cannot process withdrawals until both KYC and bank details are approved.`:a!=="Approved"?this.kycWarningMessage=`<strong>KYC Status:</strong> ${a}<br>Complete your KYC verification to enable withdrawals.`:this.kycWarningMessage=`<strong>Bank Status:</strong> ${i}<br>Submit your bank details for approval to enable withdrawals.`)}}catch(e){console.error("[MNRWithdrawals] Error checking KYC status:",e)}this.updateContent()}async loadTransactions(){this.loading=!0,this.updateContent();try{const e=new URLSearchParams;this.startDate&&e.append("start_date",this.startDate),this.endDate&&e.append("end_date",this.endDate),this.statusFilter&&e.append("verification_status",this.statusFilter);const t=e.toString()?`?${e}`:"",a=await d.get(`/withdrawals/income-transactions${t}`);if(a&&a.success&&a.data){const i=a.data,n=i.summary||{};this.summary={total_earned:n.total_earned||0,completed:n.completed||0,pending_validation:n.pending_validation||0,staff_validated:n.staff_validated||0,rejected:n.rejected||0};const s=i.segments||[],r={};s.forEach(o=>{(o.transactions||[]).forEach(p=>{const g=p.business_date||"unknown";r[g]||(r[g]={business_date:g,gross_amount:0,admin_deduction:0,tds_deduction:0,gurudakshina_deduction:0,net_amount:0,statuses:new Set}),r[g].gross_amount+=p.gross_amount||0,r[g].admin_deduction+=p.admin_deduction||0,r[g].tds_deduction+=p.tds_deduction||0,r[g].gurudakshina_deduction+=p.gurudakshina_deduction||0,r[g].net_amount+=p.net_amount||0,p.verification_status&&r[g].statuses.add(p.verification_status)})}),this.dayRows=Object.values(r).sort((o,c)=>c.business_date.localeCompare(o.business_date))}}catch(e){console.error("[MNRWithdrawals] Failed to load:",e)}this.loading=!1,this.updateContent()}render(){this.container.innerHTML=`
      <style>
        ${m.getStyles()}
        .withdrawals-page { padding: 16px; }
        
        .page-banner {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          border-radius: 12px;
          padding: 20px;
          margin-bottom: 16px;
          color: white;
        }
        .page-banner h2 { margin: 0 0 4px; font-size: 18px; }
        .page-banner p { margin: 0; font-size: 12px; opacity: 0.9; }
        
        .kyc-warning {
          background: rgba(251, 191, 36, 0.15);
          border: 1px solid rgba(251, 191, 36, 0.4);
          border-radius: 10px;
          padding: 14px;
          margin-bottom: 16px;
        }
        .kyc-warning h5 { color: #fbbf24; margin: 0 0 8px; font-size: 14px; }
        .kyc-warning .kyc-msg { color: #fcd34d; margin: 0 0 10px; font-size: 12px; line-height: 1.5; }
        .kyc-warning .btn-kyc {
          background: #fbbf24;
          color: #451a03;
          border: none;
          padding: 8px 14px;
          border-radius: 6px;
          font-size: 12px;
          font-weight: 600;
          cursor: pointer;
          margin-right: 8px;
        }
        .kyc-warning .btn-bank {
          background: transparent;
          color: #fbbf24;
          border: 1px solid #fbbf24;
          padding: 8px 14px;
          border-radius: 6px;
          font-size: 12px;
          font-weight: 600;
          cursor: pointer;
        }
        
        .summary-row {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 8px;
          margin-bottom: 12px;
        }
        .summary-card {
          background: rgba(22, 33, 62, 0.8);
          border-radius: 10px;
          padding: 14px 8px;
          text-align: center;
        }
        .summary-card.green { background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }
        .summary-card.purple { background: linear-gradient(135deg, #8e2de2 0%, #4a00e0 100%); }
        .summary-card.pink { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
        .summary-card .label { font-size: 9px; color: rgba(255,255,255,0.8); text-transform: uppercase; margin-bottom: 4px; }
        .summary-card .value { font-size: 18px; font-weight: 700; color: white; }
        .summary-card .sub { font-size: 9px; color: rgba(255,255,255,0.7); margin-top: 2px; }
        
        .pending-grid {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 8px;
          margin-bottom: 16px;
        }
        .pending-card {
          border-radius: 10px;
          padding: 12px;
          text-align: center;
        }
        .pending-card.admin { background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); color: #451a03; }
        .pending-card.super { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
        .pending-card.finance { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color: white; }
        .pending-card.rejected { background: linear-gradient(135deg, #fc5c7d 0%, #6a82fb 100%); color: white; }
        .pending-card .label { font-size: 10px; opacity: 0.9; margin-bottom: 4px; }
        .pending-card .value { font-size: 16px; font-weight: 700; }
        .pending-card .sub { font-size: 9px; opacity: 0.8; margin-top: 2px; }
        
        .lifecycle-section {
          background: rgba(22, 33, 62, 0.8);
          border-radius: 10px;
          padding: 14px;
          margin-bottom: 16px;
        }
        .lifecycle-section h5 { color: #e6f1ff; margin: 0 0 12px; font-size: 13px; }
        .lifecycle-steps {
          display: flex;
          justify-content: space-between;
          position: relative;
        }
        .lifecycle-steps::before {
          content: '';
          position: absolute;
          top: 18px;
          left: 20px;
          right: 20px;
          height: 2px;
          background: rgba(255,255,255,0.2);
        }
        .lifecycle-step {
          text-align: center;
          position: relative;
          z-index: 1;
        }
        .lifecycle-step .icon {
          width: 36px;
          height: 36px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          margin: 0 auto 6px;
          font-size: 14px;
        }
        .lifecycle-step.green .icon { background: linear-gradient(135deg, #10b981, #059669); }
        .lifecycle-step.yellow .icon { background: linear-gradient(135deg, #fbbf24, #f59e0b); }
        .lifecycle-step.purple .icon { background: linear-gradient(135deg, #8b5cf6, #7c3aed); }
        .lifecycle-step.blue .icon { background: linear-gradient(135deg, #3b82f6, #2563eb); }
        .lifecycle-step .label { font-size: 9px; color: #8892b0; }
        
        .filters-section {
          background: rgba(22, 33, 62, 0.8);
          border-radius: 10px;
          padding: 14px;
          margin-bottom: 16px;
        }
        .filters-section h5 { color: #e6f1ff; margin: 0 0 12px; font-size: 13px; }
        .filter-row {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 8px;
          margin-bottom: 10px;
        }
        .filter-group label {
          display: block;
          font-size: 10px;
          color: #8892b0;
          text-transform: uppercase;
          margin-bottom: 4px;
        }
        .filter-group input, .filter-group select {
          width: 100%;
          padding: 10px;
          border-radius: 6px;
          border: 1px solid rgba(255,255,255,0.1);
          background: rgba(13, 27, 42, 0.8);
          color: #e6f1ff;
          font-size: 13px;
        }
        .btn-apply {
          width: 48%;
          padding: 12px;
          border-radius: 6px;
          border: none;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          font-size: 13px;
          font-weight: 600;
          cursor: pointer;
        }
        .btn-clear {
          width: 48%;
          padding: 12px;
          border-radius: 6px;
          border: none;
          background: linear-gradient(135deg, #10b981 0%, #059669 100%);
          color: white;
          font-size: 13px;
          font-weight: 600;
          cursor: pointer;
        }
        .filter-buttons {
          display: flex;
          gap: 8px;
          justify-content: space-between;
        }
        
        .section-header {
          background: linear-gradient(135deg, #1f2937 0%, #374151 100%);
          padding: 12px 14px;
          border-radius: 8px 8px 0 0;
        }
        .section-header h5 { margin: 0; color: white; font-size: 13px; }

        .day-table {
          width: 100%;
          border-collapse: collapse;
          margin-bottom: 16px;
          background: rgba(22, 33, 62, 0.8);
          border-radius: 0 0 8px 8px;
          overflow: hidden;
        }
        .day-table thead th {
          padding: 8px 6px;
          font-size: 9px;
          color: #8892b0;
          text-transform: uppercase;
          border-bottom: 1px solid rgba(255,255,255,0.1);
          text-align: right;
        }
        .day-table thead th:first-child { text-align: left; }
        .day-table thead th:last-child { text-align: center; }
        .day-table tbody td {
          padding: 10px 6px;
          font-size: 12px;
          color: #e6f1ff;
          border-bottom: 1px solid rgba(255,255,255,0.05);
          text-align: right;
        }
        .day-table tbody td:first-child { text-align: left; font-weight: 600; }
        .day-table tbody td:last-child { text-align: center; }
        .day-table tfoot td {
          padding: 10px 6px;
          font-size: 12px;
          font-weight: 700;
          color: #e6f1ff;
          border-top: 2px solid rgba(102, 126, 234, 0.3);
          background: rgba(102, 126, 234, 0.08);
          text-align: right;
        }
        .day-table tfoot td:first-child { text-align: left; }
        .day-table tfoot td:last-child { text-align: center; }
        .text-danger { color: #ef4444 !important; }
        .text-warning-deduction { color: #f59e0b !important; }
        .text-success { color: #10b981 !important; }

        .day-summary-bar {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 8px 14px;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          border-radius: 8px 8px 0 0;
          color: white;
          font-size: 11px;
        }
        .day-summary-bar .badge-light {
          background: rgba(255,255,255,0.2);
          padding: 3px 8px;
          border-radius: 4px;
          font-size: 10px;
          margin-left: 6px;
        }
      </style>
      ${l.render({title:"💸 Earnings & Payments",showBack:!0})}
      <div class="withdrawals-page" id="pageContent">
        <div class="loading-state" style="text-align: center; padding: 40px; color: #8892b0;">Loading...</div>
      </div>
    `,l.attachListeners({title:"💸 Earnings & Payments",showBack:!0})}updateContent(){const e=document.getElementById("pageContent");if(!e)return;if(this.loading){e.innerHTML='<div class="loading-state" style="text-align: center; padding: 40px; color: #8892b0;">Loading withdrawals...</div>';return}const t=this.dayRows.reduce((o,c)=>o+c.gross_amount,0),a=this.dayRows.reduce((o,c)=>o+c.admin_deduction,0),i=this.dayRows.reduce((o,c)=>o+c.tds_deduction,0),n=this.dayRows.reduce((o,c)=>o+c.gurudakshina_deduction,0),s=this.dayRows.reduce((o,c)=>o+c.net_amount,0);let r="";this.dayRows.forEach(o=>{const c=Array.from(o.statuses),p=o.business_date<T.STAFF_WORKFLOW_CUTOFF,v=c.map(h=>p&&h==="Completed"?"Cleared":h).map(h=>this.getStatusBadge(h)).join(" ");r+=`<tr>
        <td>${this.formatDate(o.business_date)}</td>
        <td>₹${o.gross_amount.toLocaleString("en-IN")}</td>
        <td class="text-danger">-₹${o.admin_deduction.toLocaleString("en-IN")}</td>
        <td class="text-danger">-₹${o.tds_deduction.toLocaleString("en-IN")}</td>
        <td class="text-warning-deduction">-₹${o.gurudakshina_deduction.toLocaleString("en-IN")}</td>
        <td class="text-success" style="font-weight:600;">₹${o.net_amount.toLocaleString("en-IN")}</td>
        <td>${v}</td>
      </tr>`}),e.innerHTML=`
      <div class="page-banner">
        <h2>💰 Earnings & Payment Tracking</h2>
        <p>Track your earnings journey from income generation to bank payment</p>
      </div>

      ${this.showKycWarning?`
        <div class="kyc-warning">
          <h5>⚠️ KYC Verification Required</h5>
          <div class="kyc-msg">${this.kycWarningMessage}</div>
          <button class="btn-kyc">Complete KYC Now</button>
          <button class="btn-bank">Update Bank Details</button>
        </div>
      `:""}

      <div class="summary-row">
        <div class="summary-card green">
          <div class="label">💰 Total Income Generated</div>
          <div class="value">₹${this.summary.total_earned.toLocaleString("en-IN")}</div>
          <div class="sub">NET (After Deductions)</div>
        </div>
        <div class="summary-card pink">
          <div class="label">🏦 Paid to Bank</div>
          <div class="value">₹${this.summary.completed.toLocaleString("en-IN")}</div>
          <div class="sub">Payment Completed</div>
        </div>
      </div>

      <div class="pending-grid">
        <div class="pending-card admin">
          <div class="label">⏰ Pending Validation</div>
          <div class="value">₹${this.summary.pending_validation.toLocaleString("en-IN")}</div>
          <div class="sub">Awaiting Staff Review</div>
        </div>
        <div class="pending-card finance">
          <div class="label">✅ Staff Validated</div>
          <div class="value">₹${this.summary.staff_validated.toLocaleString("en-IN")}</div>
          <div class="sub">Awaiting Payment</div>
        </div>
        <div class="pending-card rejected">
          <div class="label">❌ Rejected</div>
          <div class="value">₹${this.summary.rejected.toLocaleString("en-IN")}</div>
          <div class="sub">Not Approved</div>
        </div>
      </div>

      <div class="lifecycle-section">
        <h5>📋 Payment Lifecycle Journey</h5>
        <p style="color: #8892b0; font-size: 11px; margin: 0 0 12px;">Your income is calculated daily, then goes through validation before payment</p>
        <div class="lifecycle-steps">
          <div class="lifecycle-step green">
            <div class="icon">💰</div>
            <div class="label">Income<br>Generated</div>
          </div>
          <div class="lifecycle-step yellow">
            <div class="icon">⏳</div>
            <div class="label">Pending<br>Validation</div>
          </div>
          <div class="lifecycle-step purple">
            <div class="icon">✅</div>
            <div class="label">Staff<br>Validated</div>
          </div>
          <div class="lifecycle-step blue">
            <div class="icon">🏦</div>
            <div class="label">Completed<br>(Paid)</div>
          </div>
        </div>
        <p style="color: #64748b; font-size: 10px; margin: 12px 0 0; background: rgba(59,130,246,0.1); padding: 8px; border-radius: 6px;">
          ℹ️ <strong>Pending Validation</strong> → <strong>Staff Validated</strong> → <strong>Completed</strong>. 
          Records before 12 Feb 2026 are shown as <strong>Cleared</strong> (auto-approved).
        </p>
      </div>

      <div class="filters-section">
        <h5>🔍 Filter Transactions</h5>
        <div class="filter-row">
          <div class="filter-group">
            <label>📅 Start Date</label>
            <input type="date" id="filterStartDate" value="${this.startDate}" />
          </div>
          <div class="filter-group">
            <label>📅 End Date</label>
            <input type="date" id="filterEndDate" value="${this.endDate}" />
          </div>
        </div>
        <div class="filter-row" style="grid-template-columns: 1fr;">
          <div class="filter-group">
            <label>🏷️ Payment Status</label>
            <select id="filterStatus">
              <option value="">All Status</option>
              <option value="Pending" ${this.statusFilter==="Pending"?"selected":""}>⏳ Pending Validation</option>
              <option value="Staff Validated" ${this.statusFilter==="Staff Validated"?"selected":""}>✅ Staff Validated</option>
              <option value="Completed" ${this.statusFilter==="Completed"?"selected":""}>💰 Completed (Paid)</option>
              <option value="Rejected" ${this.statusFilter==="Rejected"?"selected":""}>❌ Rejected</option>
            </select>
          </div>
        </div>
        <div class="filter-buttons">
          <button class="btn-apply" id="btnApplyFilters">🔍 Apply</button>
          <button class="btn-clear" id="btnClearFilters">🔄 Show All</button>
        </div>
      </div>

      ${this.dayRows.length>0?`
        <div class="day-summary-bar">
          <span>📋 Day-Wise Cumulative Income</span>
          <span>
            <span class="badge-light">Gross: ₹${t.toLocaleString("en-IN")}</span>
            <span class="badge-light">NET: ₹${s.toLocaleString("en-IN")}</span>
          </span>
        </div>
        <table class="day-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Gross</th>
              <th>Adm 8%</th>
              <th>TDS 2%</th>
              <th>Ctb 2%</th>
              <th>NET</th>
              <th>Sts</th>
            </tr>
          </thead>
          <tbody>${r}</tbody>
          <tfoot>
            <tr>
              <td>TOTAL (${this.dayRows.length} days)</td>
              <td>₹${t.toLocaleString("en-IN")}</td>
              <td class="text-danger">-₹${a.toLocaleString("en-IN")}</td>
              <td class="text-danger">-₹${i.toLocaleString("en-IN")}</td>
              <td class="text-warning-deduction">-₹${n.toLocaleString("en-IN")}</td>
              <td class="text-success">₹${s.toLocaleString("en-IN")}</td>
              <td>-</td>
            </tr>
          </tfoot>
        </table>
      `:`
        <div style="text-align: center; padding: 40px; color: #8892b0;">
          <div style="font-size: 40px; margin-bottom: 12px;">📭</div>
          <h4 style="color: #e6f1ff; margin: 0 0 8px;">No Income Records Found</h4>
          <p style="margin: 0; font-size: 12px;">No income has been generated yet. Income is calculated daily at midnight.</p>
        </div>
      `}
    `,this.attachListeners()}attachListeners(){document.getElementById("btnApplyFilters")?.addEventListener("click",()=>{this.startDate=document.getElementById("filterStartDate")?.value||"",this.endDate=document.getElementById("filterEndDate")?.value||"",this.statusFilter=document.getElementById("filterStatus")?.value||"",this.loadTransactions()}),document.getElementById("btnClearFilters")?.addEventListener("click",()=>{this.startDate="",this.endDate="",this.statusFilter="",this.loadTransactions()})}getStatusBadge(e){const t=e.toLowerCase();return t==="paid"||t==="completed"?'<span class="badge badge-success">Completed</span>':t==="cleared"?'<span class="badge badge-info">Cleared</span>':t==="staff validated"||t==="staff_validated"?'<span class="badge badge-info">Staff Validated</span>':t.includes("pending")||t==="pending"?'<span class="badge badge-warning">Pending Validation</span>':t==="rejected"?'<span class="badge badge-danger">Rejected</span>':`<span class="badge badge-secondary">${e}</span>`}formatDate(e){if(!e)return"-";try{return new Date(e).toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"numeric"})}catch{return e}}}const K=[{id:1,title:"Points Redemption – Manthra EV Vehicles",description:["Redeem points only on Manthra EV vehicles","Capping: 7,500 points per vehicle","Maximum: 2 redemptions allowed","Exclusive M99 Users: Maximum withdrawal up to 15,000 points","Graphene or 1 year LFP battery: 1,000 points redemption"],icon:"🛵",color:"#10b981",actionLabel:"Add EV Lead",actionRoute:"mnr-add-ev-lead"},{id:2,title:"Solar Benefit (Points Claim)",description:["Claim 15,000 points","Applicable on minimum 3 KW Solar installation"],icon:"☀️",color:"#f59e0b",actionLabel:"Add Solar Lead",actionRoute:"mnr-add-solar-lead"},{id:3,title:"Franchise Setup Benefit",description:["2% commission on initial franchise income","1% commission on subsequent invoices"],icon:"🏪",color:"#8b5cf6"},{id:4,title:"Insurance Referral Benefit",description:["Earn commission on insurance policy referrals","Life, Health, and Vehicle insurance covered"],icon:"🛡️",color:"#3b82f6"},{id:5,title:"Fleet Order Referral",description:["Commission on fleet vehicle orders","Applicable for bulk EV orders"],icon:"🚚",color:"#ec4899"},{id:6,title:"Training Cashback",description:["Cashback on training program enrollments","Valid for certified training sessions"],icon:"📚",color:"#06b6d4"},{id:7,title:"RoyalEV Bonus",description:["Premium bonus on Royal EV vehicle purchases","Up to 15% bonus based on package tier"],icon:"👑",color:"#eab308"}];class ae{container;summary=null;loading=!0;constructor(e){this.container=e}async init(){this.render(),await this.loadBenefits()}async loadBenefits(){this.loading=!0,this.updateContent();try{const[e,t]=await Promise.all([d.get("/ev-discount/my-benefits"),d.get("/ev-discount/my-referral-income")]);e.success&&e.data&&(this.summary={total_benefits_count:e.data.total_benefits_count||0,total_discount_received:e.data.total_discount_received||0,total_cashback_received:e.data.total_cashback_received||0,total_referral_incomes_count:e.data.total_referral_incomes_count||0,total_referral_income:e.data.total_referral_income||0,benefit_breakdown:e.data.benefit_breakdown||{},referral_breakdown:e.data.referral_breakdown||{}}),t.success&&t.data&&this.summary&&(this.summary.total_referral_incomes_count=t.data.total_count||this.summary.total_referral_incomes_count,this.summary.total_referral_income=t.data.total_amount||this.summary.total_referral_income,this.summary.referral_breakdown=t.data.breakdown||this.summary.referral_breakdown)}catch(e){console.error("[MNRBenefits] Failed to load:",e)}this.loading=!1,this.updateContent()}render(){this.container.innerHTML=`
      <style>
        .benefits-page { padding: 16px; }
        
        .header-card {
          background: linear-gradient(135deg, #065f46 0%, #047857 100%);
          border-radius: 12px;
          padding: 16px;
          margin-bottom: 16px;
          color: white;
        }
        .header-card h3 { margin: 0 0 4px; font-size: 16px; }
        .header-card p { margin: 0; font-size: 13px; opacity: 0.9; }
        
        .feedback-notice {
          background: linear-gradient(135deg, #78350f 0%, #92400e 100%);
          border-radius: 12px;
          padding: 14px;
          margin-bottom: 16px;
          color: white;
        }
        .feedback-notice h4 {
          color: #fcd34d;
          margin: 0 0 8px;
          font-size: 14px;
          display: flex;
          align-items: center;
          gap: 6px;
        }
        .feedback-notice p {
          margin: 0 0 8px;
          font-size: 12px;
          line-height: 1.5;
        }
        .feedback-notice ul {
          margin: 8px 0;
          padding-left: 18px;
          font-size: 12px;
          line-height: 1.6;
        }
        .feedback-notice .note {
          font-size: 11px;
          opacity: 0.8;
          margin-top: 8px;
          padding-top: 8px;
          border-top: 1px solid rgba(255,255,255,0.2);
        }
        
        .stats-grid {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 12px;
          margin-bottom: 20px;
        }
        .stat-card {
          background: rgba(22, 33, 62, 0.8);
          border-radius: 12px;
          padding: 16px;
          text-align: center;
        }
        .stat-icon {
          width: 40px;
          height: 40px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          margin: 0 auto 8px;
          font-size: 18px;
        }
        .stat-value {
          font-size: 20px;
          font-weight: 700;
          color: #e6f1ff;
          margin-bottom: 4px;
        }
        .stat-label {
          font-size: 11px;
          color: #8892b0;
          text-transform: uppercase;
        }
        
        .section-title {
          font-size: 15px;
          font-weight: 600;
          color: #e6f1ff;
          margin: 20px 0 12px;
          display: flex;
          align-items: center;
          gap: 8px;
        }
        
        .benefit-types-list {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        
        .benefit-type-card {
          background: rgba(22, 33, 62, 0.8);
          border-radius: 12px;
          padding: 16px;
          border-left: 4px solid;
        }
        .benefit-type-header {
          display: flex;
          align-items: center;
          gap: 12px;
          margin-bottom: 10px;
        }
        .benefit-type-number {
          width: 28px;
          height: 28px;
          border-radius: 50%;
          background: rgba(16, 185, 129, 0.2);
          color: #10b981;
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: 700;
          font-size: 14px;
        }
        .benefit-type-title {
          font-size: 14px;
          font-weight: 600;
          color: #e6f1ff;
          flex: 1;
        }
        .benefit-type-icon {
          font-size: 20px;
        }
        .benefit-type-desc {
          margin: 0;
          padding-left: 40px;
        }
        .benefit-type-desc li {
          font-size: 12px;
          color: #8892b0;
          margin-bottom: 4px;
          line-height: 1.4;
        }
        .benefit-action-btn {
          margin-top: 12px;
          margin-left: 40px;
          padding: 8px 16px;
          background: linear-gradient(135deg, #10b981 0%, #059669 100%);
          color: white;
          border: none;
          border-radius: 6px;
          font-size: 12px;
          font-weight: 600;
          cursor: pointer;
        }
      </style>
      ${l.render({title:"🎁 Coupon Utilisation Benefits",showBack:!0})}
      <div class="benefits-page" id="pageContent">
        <div class="loading-state">Loading...</div>
      </div>
    `,l.attachListeners({title:"🎁 Coupon Utilisation Benefits",showBack:!0})}updateContent(){const e=document.getElementById("pageContent");if(!e)return;if(this.loading){e.innerHTML='<div class="loading-state" style="text-align: center; padding: 40px; color: #8892b0;">Loading...</div>';return}const t=this.summary||{total_discount_received:0,total_cashback_received:0,total_referral_income:0};e.innerHTML=`
      <div class="header-card">
        <h3>MNR Coupon Benefits</h3>
        <p>Maximize your MNR Discount Coupon value with 7 benefit types</p>
      </div>

      <div class="feedback-notice">
        <h4>📹 Feedback Video and Photos Requirement</h4>
        <p><strong>After points utilization for additional referral bonus or earnings:</strong> It is mandatory to share feedback videos and photos.</p>
        <p><strong>Eligible Engagement Activities:</strong></p>
        <ul>
          <li>Reels (video content)</li>
          <li>WhatsApp Status sharing</li>
          <li>Social Media posts</li>
          <li>Sharing & Ratings in Announcement sections</li>
          <li>Engaging with teams</li>
          <li>Attending Zoom calls</li>
        </ul>
        <p class="note">ℹ️ Please note: Submitted feedback videos and photos may be publicly displayed on our platforms for promotional and community engagement purposes.</p>
      </div>

      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-icon" style="background: rgba(16, 185, 129, 0.2);">✓</div>
          <div class="stat-value">${(t.total_discount_received+t.total_cashback_received).toLocaleString()} pts</div>
          <div class="stat-label">Total Benefits Used</div>
        </div>
        <div class="stat-card">
          <div class="stat-icon" style="background: rgba(6, 182, 212, 0.2);">💎</div>
          <div class="stat-value">${t.total_discount_received.toLocaleString()} pts</div>
          <div class="stat-label">Total Discounts</div>
        </div>
        <div class="stat-card">
          <div class="stat-icon" style="background: rgba(245, 158, 11, 0.2);">💰</div>
          <div class="stat-value">${t.total_cashback_received.toLocaleString()} pts</div>
          <div class="stat-label">Total Cashback</div>
        </div>
        <div class="stat-card">
          <div class="stat-icon" style="background: rgba(139, 92, 246, 0.2);">👥</div>
          <div class="stat-value">${t.total_referral_income.toLocaleString()} pts</div>
          <div class="stat-label">Referral Income</div>
        </div>
      </div>

      <div class="section-title">
        <span>📋</span> Available Benefit Types
      </div>

      <div class="benefit-types-list">
        ${K.map(a=>`
          <div class="benefit-type-card" style="border-left-color: ${a.color};">
            <div class="benefit-type-header">
              <div class="benefit-type-number" style="background: ${a.color}20; color: ${a.color};">${a.id}</div>
              <div class="benefit-type-title">${a.title}</div>
              <span class="benefit-type-icon">${a.icon}</span>
            </div>
            <ul class="benefit-type-desc">
              ${a.description.map(i=>`<li>${i}</li>`).join("")}
            </ul>
            ${a.actionLabel?`<button class="benefit-action-btn" data-route="${a.actionRoute}">➕ ${a.actionLabel}</button>`:""}
          </div>
        `).join("")}
      </div>
    `,this.attachListeners()}attachListeners(){document.querySelectorAll(".benefit-action-btn").forEach(e=>{e.addEventListener("click",()=>{const t=e.getAttribute("data-route");t&&window.dispatchEvent(new CustomEvent("navigate",{detail:{route:t}}))})})}}class ie{container;user=null;profile=null;loading=!0;constructor(e){this.container=e}async init(){const e=b.getAuthState();this.user=e.user,this.render(),await this.loadProfile()}async loadProfile(){this.loading=!0;try{const e=await d.get("/users/profile");e.success&&e.data&&(this.profile=e.data)}catch(e){console.error("[MNRProfile] Failed to load:",e)}this.loading=!1,this.updateContent()}render(){const e=this.user?.name||this.user?.mnr_id||"Member",t=this.getInitials(e);this.container.innerHTML=`
      <div class="page-container">
        ${l.render({title:"👤 My Profile",showBack:!0})}
        
        <div class="profile-header card">
          <div class="profile-avatar">${t}</div>
          <h2 class="profile-name">${e}</h2>
          <p class="profile-id">${this.user?.mnr_id||""}</p>
          <p class="profile-package">${this.user?.package_name||"Standard"}</p>
        </div>

        <div id="profileContent">
          <div class="loading-state">Loading...</div>
        </div>

        <div class="menu-list">
          <button class="menu-item" data-page="mnr-referrals">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
              <circle cx="9" cy="7" r="4"/>
              <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
              <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
            </svg>
            <span>My Referrals</span>
            <svg class="chevron" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="9 18 15 12 9 6"/>
            </svg>
          </button>
          <button class="menu-item" data-page="mnr-kyc">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="4" width="18" height="16" rx="2"/>
              <path d="M7 8h10"/>
              <path d="M7 12h10"/>
              <path d="M7 16h6"/>
            </svg>
            <span>KYC Documents</span>
            <svg class="chevron" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="9 18 15 12 9 6"/>
            </svg>
          </button>
          <button class="menu-item" data-page="mnr-bank">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="1" y="4" width="22" height="16" rx="2" ry="2"/>
              <line x1="1" y1="10" x2="23" y2="10"/>
            </svg>
            <span>Bank Details</span>
            <svg class="chevron" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="9 18 15 12 9 6"/>
            </svg>
          </button>
          <button class="menu-item" data-page="settings">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="3"/>
              <path d="M12 1v6m0 6v10"/>
            </svg>
            <span>Settings</span>
            <svg class="chevron" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="9 18 15 12 9 6"/>
            </svg>
          </button>
        </div>
      </div>
    `,this.attachListeners()}attachListeners(){l.attachListeners({title:"👤 My Profile",showBack:!0}),this.container.querySelectorAll(".menu-item[data-page]").forEach(e=>{e.addEventListener("click",()=>{const t=e.getAttribute("data-page");t&&f.navigate(t)})})}updateContent(){const e=document.getElementById("profileContent");if(!e)return;if(this.loading){e.innerHTML='<div class="loading-state">Loading...</div>';return}const t=this.profile||this.user||{};e.innerHTML=`
      <!-- Personal Information Section - Web Parity -->
      <div class="mnr-section-card personal-info">
        <div class="section-header-bar green">
          <h3>Personal Information</h3>
          <button class="edit-btn" id="editPersonalBtn">Edit</button>
        </div>
        <div class="section-content">
          <div class="info-grid">
            <div class="info-row">
              <span class="info-label">Name:</span>
              <span class="info-value">${t.name||"Not provided"}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Email:</span>
              <span class="info-value">${t.email||"Not provided"}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Mobile:</span>
              <span class="info-value">${t.mobile||"Not provided"}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Gender:</span>
              <span class="info-value">${t.gender||"Not provided"}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Actual DOB:</span>
              <span class="info-value">${t.actual_dob?this.formatDate(t.actual_dob):"Not provided"}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Certificate DOB:</span>
              <span class="info-value">${t.certificate_dob?this.formatDate(t.certificate_dob):"Not provided"}</span>
            </div>
          </div>
          <div class="address-section">
            <span class="info-label">Address:</span>
            <span class="info-value">${this.formatAddress(t)}</span>
          </div>
        </div>
      </div>

      <!-- KYC Documents Section - Web Parity -->
      <div class="mnr-section-card kyc-section">
        <div class="section-header-bar orange">
          <h3>KYC Documents</h3>
          <span class="status-badge ${t.kyc_status==="Verified"?"verified":"pending"}">${t.kyc_status||"Pending"}</span>
          <button class="edit-btn" id="editKycBtn">Edit</button>
        </div>
        <div class="section-content">
          <div class="info-grid">
            <div class="info-row">
              <span class="info-label">Aadhaar Number:</span>
              <span class="info-value">${t.aadhaar_number||"Not provided"}</span>
            </div>
            <div class="info-row">
              <span class="info-label">PAN Number:</span>
              <span class="info-value">${t.pan_number||"Not provided"}</span>
            </div>
          </div>
          <div class="doc-upload-grid">
            <div class="doc-item">
              <span class="doc-label">Aadhaar Front:</span>
              <span class="doc-status ${t.aadhaar_front_url?"uploaded":"not-uploaded"}">${t.aadhaar_front_url?"Uploaded":"Not Uploaded"}</span>
            </div>
            <div class="doc-item">
              <span class="doc-label">Aadhaar Back:</span>
              <span class="doc-status ${t.aadhaar_back_url?"uploaded":"not-uploaded"}">${t.aadhaar_back_url?"Uploaded":"Not Uploaded"}</span>
            </div>
            <div class="doc-item">
              <span class="doc-label">PAN Card:</span>
              <span class="doc-status ${t.pan_url?"uploaded":"not-uploaded"}">${t.pan_url?"Uploaded":"Not Uploaded"}</span>
            </div>
            <div class="doc-item">
              <span class="doc-label">Passport Photo:</span>
              <span class="doc-status ${t.passport_photo_url?"uploaded":"not-uploaded"}">${t.passport_photo_url?"Uploaded":"Not Uploaded"}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Bank Details Section - Web Parity -->
      <div class="mnr-section-card bank-section">
        <div class="section-header-bar purple">
          <h3>Bank Details</h3>
          <span class="status-badge ${t.bank_name?"submitted":"not-submitted"}">${t.bank_name?"Submitted":"Not Submitted"}</span>
          <button class="edit-btn" id="editBankBtn">Edit</button>
        </div>
        <div class="section-content">
          <div class="info-grid">
            <div class="info-row">
              <span class="info-label">Bank Name:</span>
              <span class="info-value">${t.bank_name||"Not provided"}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Account Holder:</span>
              <span class="info-value">${t.account_holder_name||"Not provided"}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Account Number:</span>
              <span class="info-value">${t.account_number?this.maskNumber(t.account_number):"Not provided"}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Branch:</span>
              <span class="info-value">${t.branch||"Not provided"}</span>
            </div>
            <div class="info-row">
              <span class="info-label">IFSC Code:</span>
              <span class="info-value">${t.ifsc_code||"Not provided"}</span>
            </div>
            <div class="info-row">
              <span class="info-label">UPI ID:</span>
              <span class="info-value">${t.upi_id||"Not provided"}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Back to Dashboard Button -->
      <button class="btn btn-secondary btn-full" id="backToDashboard">
        ← Back to Dashboard
      </button>
    `,this.attachContentListeners()}attachContentListeners(){document.getElementById("editPersonalBtn")?.addEventListener("click",()=>{f.navigate("mnr-profile-edit")}),document.getElementById("editKycBtn")?.addEventListener("click",()=>{f.navigate("mnr-kyc")}),document.getElementById("editBankBtn")?.addEventListener("click",()=>{f.navigate("mnr-bank")}),document.getElementById("backToDashboard")?.addEventListener("click",()=>{f.navigate("mnr-dashboard")})}showToast(e){const t=document.createElement("div");t.className="toast-message",t.textContent=e,document.body.appendChild(t),setTimeout(()=>t.remove(),3e3)}formatAddress(e){const t=[e.address,e.city,e.state,e.pincode].filter(Boolean);return t.length>0?t.join(", "):"Not provided"}maskNumber(e){return!e||e.length<=4?e||"N/A":"XXXXXXXX"+e.slice(-4)}getInitials(e){return e.split(" ").map(t=>t[0]).join("").toUpperCase().slice(0,2)}formatDate(e){return e?new Date(e).toLocaleDateString("en-IN",{day:"2-digit",month:"2-digit",year:"numeric",hour:"2-digit",minute:"2-digit"}):"Not provided"}}class ne{container;profile=null;loading=!0;saving=!1;uploadingPhoto=null;constructor(e){this.container=e}async init(){this.render(),await this.loadProfile()}async loadProfile(){this.loading=!0,this.updateContent();try{const e=await d.get("/users/profile");e.success&&e.data&&(this.profile=e.data)}catch(e){console.error("[MNRProfileEdit] Failed to load:",e)}this.loading=!1,this.updateContent()}render(){this.container.innerHTML=`
      <style>
        .profile-edit-page .form-group { margin-bottom: 16px; }
        .profile-edit-page .form-group label {
          display: block; color: #8892b0; font-size: 13px;
          margin-bottom: 6px; font-weight: 500;
        }
        .profile-edit-page .form-input {
          width: 100%; padding: 12px 16px; background: #1a2744;
          border: 1px solid #2d3b4f; border-radius: 8px;
          color: #e6f1ff; font-size: 15px;
        }
        .profile-edit-page .form-input:focus {
          outline: none; border-color: #64ffda;
        }
        .profile-edit-page .form-row {
          display: flex; gap: 12px;
        }
        .profile-edit-page .form-row .form-group { flex: 1; }
        .profile-edit-page .section-title {
          color: #64ffda; font-size: 16px; font-weight: 600;
          margin: 20px 0 12px; padding-bottom: 8px;
          border-bottom: 1px solid #2d3b4f;
        }
        .profile-edit-page .form-actions {
          display: flex; gap: 12px; margin-top: 24px;
        }
        .profile-edit-page .form-actions .btn { flex: 1; padding: 14px; border-radius: 8px; font-weight: 600; }
        .profile-edit-page .btn-secondary { background: #2d3b4f; color: #e6f1ff; border: none; }
        .profile-edit-page .btn-primary { background: #64ffda; color: #0a192f; border: none; }
        .profile-edit-page .btn:disabled { opacity: 0.6; }
        .profile-edit-page select.form-input { appearance: none; }
        .profile-edit-page .photo-upload-section {
          display: flex; gap: 16px; margin-bottom: 20px;
        }
        .profile-edit-page .photo-box {
          flex: 1; text-align: center; padding: 16px;
          background: #1a2744; border-radius: 12px; border: 1px dashed #2d3b4f;
        }
        .profile-edit-page .photo-box.has-photo { border: 2px solid #64ffda; }
        .profile-edit-page .photo-preview {
          width: 80px; height: 80px; border-radius: 50%;
          margin: 0 auto 10px; background: #2d3b4f;
          display: flex; align-items: center; justify-content: center;
          overflow: hidden; font-size: 24px;
        }
        .profile-edit-page .photo-preview img {
          width: 100%; height: 100%; object-fit: cover;
        }
        .profile-edit-page .photo-label { color: #8892b0; font-size: 12px; margin-bottom: 8px; }
        .profile-edit-page .photo-btn {
          padding: 8px 16px; font-size: 12px; border-radius: 6px;
          border: none; cursor: pointer;
        }
        .profile-edit-page .photo-btn.primary { background: #64ffda; color: #0a192f; }
        .profile-edit-page .photo-btn.secondary { background: #2d3b4f; color: #e6f1ff; }
      </style>
      <div class="page-container profile-edit-page">
        ${l.render({title:"✏️ Edit Profile",showBack:!0})}
        
        <div id="pageContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
    `,l.attachListeners({title:"✏️ Edit Profile",showBack:!0})}updateContent(){const e=document.getElementById("pageContent");if(!e)return;if(this.loading){e.innerHTML='<div class="loading-state">Loading...</div>';return}const t=this.profile||{},a=this.uploadingPhoto==="profile_photo",i=this.uploadingPhoto==="passport_photo";e.innerHTML=`
      <div class="card">
        <h3 class="section-title">Photos</h3>
        <div class="photo-upload-section">
          <div class="photo-box ${t.profile_photo_url?"has-photo":""}">
            <div class="photo-preview">
              ${t.profile_photo_url?`<img src="${t.profile_photo_url}" alt="Profile">`:"📷"}
            </div>
            <div class="photo-label">Profile Photo</div>
            <button class="photo-btn ${t.profile_photo_url?"secondary":"primary"}" 
              id="uploadProfileBtn" ${a?"disabled":""}>
              ${a?"Uploading...":t.profile_photo_url?"Change":"Upload"}
            </button>
          </div>
          <div class="photo-box ${t.passport_photo_url?"has-photo":""}">
            <div class="photo-preview">
              ${t.passport_photo_url?`<img src="${t.passport_photo_url}" alt="Passport">`:"🖼️"}
            </div>
            <div class="photo-label">Passport Photo</div>
            <button class="photo-btn ${t.passport_photo_url?"secondary":"primary"}" 
              id="uploadPassportBtn" ${i?"disabled":""}>
              ${i?"Uploading...":t.passport_photo_url?"Change":"Upload"}
            </button>
          </div>
        </div>
        <input type="file" id="photoInput" accept="image/*" style="display: none;">
        
        <h3 class="section-title">Personal Information</h3>
        
        <div class="form-group">
          <label>Full Name</label>
          <input type="text" id="fullName" class="form-input" 
            value="${t.name||""}" placeholder="Contact admin to change" 
            readonly disabled style="opacity: 0.6; cursor: not-allowed;">
          <small style="color: #6b7280; font-size: 11px;">Name cannot be changed. Contact admin for updates.</small>
        </div>
        
        <div class="form-row">
          <div class="form-group">
            <label>Email</label>
            <input type="email" id="email" class="form-input" 
              value="${t.email||""}" placeholder="your@email.com">
          </div>
          <div class="form-group">
            <label>Mobile</label>
            <input type="tel" id="mobile" class="form-input" 
              value="${t.mobile||""}" placeholder="Contact admin to change"
              readonly disabled style="opacity: 0.6; cursor: not-allowed;">
            <small style="color: #6b7280; font-size: 11px;">Mobile cannot be changed.</small>
          </div>
        </div>
        
        <div class="form-row">
          <div class="form-group">
            <label>Gender</label>
            <select id="gender" class="form-input">
              <option value="">Select</option>
              <option value="Male" ${t.gender==="Male"?"selected":""}>Male</option>
              <option value="Female" ${t.gender==="Female"?"selected":""}>Female</option>
              <option value="Other" ${t.gender==="Other"?"selected":""}>Other</option>
            </select>
          </div>
          <div class="form-group">
            <label>Actual DOB</label>
            <input type="date" id="actualDob" class="form-input" 
              value="${t.actual_dob?t.actual_dob.split("T")[0]:""}">
          </div>
        </div>
        
        <h3 class="section-title">Address</h3>
        
        <div class="form-group">
          <label>Street Address</label>
          <input type="text" id="address" class="form-input" 
            value="${t.address||""}" placeholder="Street address">
        </div>
        
        <div class="form-row">
          <div class="form-group">
            <label>City</label>
            <input type="text" id="city" class="form-input" 
              value="${t.city||""}" placeholder="City">
          </div>
          <div class="form-group">
            <label>State</label>
            <input type="text" id="state" class="form-input" 
              value="${t.state||""}" placeholder="State">
          </div>
        </div>
        
        <div class="form-group">
          <label>Pincode</label>
          <input type="text" id="pincode" class="form-input" 
            value="${t.pincode||""}" placeholder="6-digit pincode" maxlength="6">
        </div>
        
        <h3 class="section-title">KYC Details</h3>
        
        <div class="form-row">
          <div class="form-group">
            <label>Aadhaar Number</label>
            <input type="text" id="aadhaarNumber" class="form-input" 
              value="${t.aadhaar_number||""}" placeholder="12-digit Aadhaar" maxlength="12">
          </div>
          <div class="form-group">
            <label>PAN Number</label>
            <input type="text" id="panNumber" class="form-input" 
              value="${t.pan_number||""}" placeholder="e.g., ABCDE1234F" maxlength="10">
          </div>
        </div>
        
        <div class="form-actions">
          <button class="btn btn-secondary" id="cancelBtn" ${this.saving?"disabled":""}>
            Cancel
          </button>
          <button class="btn btn-primary" id="saveBtn" ${this.saving?"disabled":""}>
            ${this.saving?"Saving...":"Save Changes"}
          </button>
        </div>
      </div>
    `,this.attachListeners()}attachListeners(){document.getElementById("cancelBtn")?.addEventListener("click",()=>{f.navigate("mnr-profile")}),document.getElementById("saveBtn")?.addEventListener("click",()=>{this.saveProfile()});const e=document.getElementById("photoInput");document.getElementById("uploadProfileBtn")?.addEventListener("click",()=>{this.uploadingPhoto="profile_photo",e?.click()}),document.getElementById("uploadPassportBtn")?.addEventListener("click",()=>{this.uploadingPhoto="passport_photo",e?.click()}),e?.addEventListener("change",async()=>{const t=e.files?.[0];t&&this.uploadingPhoto&&await this.uploadPhoto(this.uploadingPhoto,t),e.value=""})}async uploadPhoto(e,t){this.updateContent();try{const a=new FormData;a.append("file",t),a.append("document_type",e);const i=await d.uploadFile("/profile/upload-kyc-document",a);i.success?(alert("Photo uploaded successfully!"),await this.loadProfile()):alert(i.error||"Failed to upload photo")}catch(a){console.error("[MNRProfileEdit] Photo upload failed:",a),alert("Failed to upload photo. Please try again.")}finally{this.uploadingPhoto=null,this.updateContent()}}async saveProfile(){const e=a=>document.getElementById(a)?.value?.trim()||null,t={name:e("fullName"),email:e("email"),mobile:e("mobile"),gender:e("gender"),actual_dob:e("actualDob"),address:e("address"),city:e("city"),state:e("state"),pincode:e("pincode"),aadhaar_number:e("aadhaarNumber"),pan_number:e("panNumber")};if(!t.name){alert("Please enter your full name");return}this.saving=!0,this.updateContent();try{const a=await d.put("/users/profile",t);a.success?(alert("Profile updated successfully!"),f.navigate("mnr-profile")):alert(a.error||"Failed to update profile")}catch(a){console.error("[MNRProfileEdit] Save failed:",a),alert("Failed to update profile. Please try again.")}finally{this.saving=!1}}}class se{container;awards=[];stats={achieved:0,received:0,pending:0};loading=!0;activeTab="all";eligibility=null;constructor(e){this.container=e}async init(){this.render(),await this.loadAwards()}async loadAwards(){this.loading=!0,this.updateContent();try{const e=b.getAuthState(),t=e.user?.id||e.user?.mnr_id||"";if(!t){console.error("[MNRAwards] No user ID found"),this.loading=!1,this.updateContent();return}const[a,i,n]=await Promise.all([d.get(`/awards-fast/user/${t}/direct`),d.get(`/awards-fast/user/${t}/matching`),d.get("/auth/me-hybrid?role=mnr")]),s=a.success&&a.data?.direct_awards?a.data.direct_awards:a.data?.direct_awards||[],r=i.success&&i.data?.matching_awards?i.data.matching_awards:i.data?.matching_awards||[];this.awards=[...s.map(c=>this.mapAward(c,"direct")),...r.map(c=>this.mapAward(c,"matching"))],this.calculateStats();const o=n?.data?.eligibility_status||n?.eligibility_status;o&&(this.eligibility={is_activated:o.is_activated||!1,kyc_status:o.kyc_status||"pending",program_utilisation_completed:o.program_utilisation_completed||!1,group_a_points:o.group_a_points||0,group_b_points:o.group_b_points||0,is_eligible:o.is_eligible||!1})}catch(e){console.error("[MNRAwards] Failed to load:",e)}this.loading=!1,this.updateContent()}mapAward(e,t){const a=e.tier_info||e,i=a.referral_count||a.cumulative_required||e.requirement||0,n=e.current_direct_count||e.current_matching_pairs||e.current_progress||0,s=e.bonanza_deductions||0,r=e.achieved||!1;return{id:a.id||e.id||0,award_rank:a.rank_name||a.award_name||e.rank_name||e.award_name||"",award_item:a.award_item||e.award_item||a.award_description||"",requirement:i,current_progress:n,bonanza_claimed:s,remaining:Math.max(0,i-n+s),achievement_status:r?"Achieved":e.achievement_status||"Pending",processed_status:e.processed_status||e.simplified_status||"Pending",last_updated:e.last_updated||e.achievement_date||e.process_date||null,category:t}}calculateStats(){this.stats={achieved:this.awards.filter(e=>e.achievement_status.toLowerCase()==="achieved"||e.achievement_status.toLowerCase()==="completed").length,received:this.awards.filter(e=>e.processed_status.toLowerCase()==="delivered"||e.processed_status.toLowerCase()==="delivered - completed").length,pending:this.awards.filter(e=>e.achievement_status.toLowerCase()==="pending"||e.achievement_status.toLowerCase()==="achieved"&&e.processed_status.toLowerCase()!=="delivered").length}}renderEligibilityBanner(){if(!this.eligibility)return"";const e=this.eligibility,t=e.is_activated,a=(e.kyc_status||"pending").toLowerCase()==="approved",i=e.program_utilisation_completed,n=(e.group_a_points||0)>=1,s=(e.group_b_points||0)>=1;return t&&a&&i&&n&&s?"":`
      <div class="eligibility-banner">
        <div class="banner-title">📋 Eligibility Checklist</div>
        <div class="banner-desc">Awards and bonanza benefits are unlocked after successful utilisation of an eligible product or service through the MNR Business Access Program.</div>
        <ul class="checklist">${[{done:t,label:"Account Activated"},{done:a,label:"KYC Approved"},{done:i,label:"Program Utilisation Completed"},{done:n,label:"Group A – Minimum 1 active & utilised business facilitation"},{done:s,label:"Group B – Minimum 1 active & utilised business facilitation"}].map(c=>`<li>${c.done?'<span class="done">✅</span>':'<span class="pending">⏳</span>'}<span>${c.label}</span></li>`).join("")}</ul>
      </div>
    `}render(){this.container.innerHTML=`
      <style>
        ${m.getStyles()}
        .mnr-awards-page { padding: 16px; background: #0d1b2a; min-height: 100vh; }
        .requirements-card {
          background: #fff3cd;
          border-radius: 12px;
          padding: 16px;
          margin-bottom: 16px;
          color: #664d03;
        }
        .requirements-card .req-header {
          display: flex;
          align-items: center;
          gap: 8px;
          font-weight: 600;
          font-size: 14px;
          margin-bottom: 10px;
        }
        .requirements-card .req-text {
          font-size: 13px;
          margin-bottom: 12px;
          line-height: 1.5;
        }
        .requirements-card .activities-header {
          font-weight: 600;
          font-size: 13px;
          margin-bottom: 8px;
        }
        .requirements-card .activities-list {
          list-style: none;
          padding: 0;
          margin: 0 0 12px 0;
        }
        .requirements-card .activities-list li {
          font-size: 12px;
          padding: 3px 0 3px 16px;
          position: relative;
        }
        .requirements-card .activities-list li::before {
          content: "•";
          position: absolute;
          left: 4px;
        }
        .requirements-card .note-text {
          font-size: 11px;
          padding: 10px;
          background: rgba(0,0,0,0.05);
          border-radius: 8px;
        }
        .stats-row {
          display: flex;
          gap: 12px;
          margin-bottom: 16px;
          overflow-x: auto;
        }
        .stat-card {
          flex: 1;
          min-width: 100px;
          padding: 16px 12px;
          border-radius: 12px;
          text-align: center;
        }
        .stat-card.achieved { background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; }
        .stat-card.received { background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); color: white; }
        .stat-card.pending { background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); color: white; }
        .stat-card .stat-icon { font-size: 24px; margin-bottom: 6px; }
        .stat-card .stat-value { font-size: 24px; font-weight: 700; }
        .stat-card .stat-label { font-size: 11px; opacity: 0.9; }
        .tabs-container {
          display: flex;
          gap: 8px;
          margin-bottom: 16px;
          background: #1a2744;
          padding: 8px;
          border-radius: 12px;
          overflow-x: auto;
        }
        .tab-btn {
          flex: 1;
          padding: 10px 12px;
          background: transparent;
          border: none;
          border-radius: 8px;
          color: #8892b0;
          font-size: 13px;
          font-weight: 500;
          white-space: nowrap;
          cursor: pointer;
          transition: all 0.2s;
        }
        .tab-btn.active {
          background: #64d2ff;
          color: #0d1b2a;
          font-weight: 600;
        }
        .eligibility-banner {
          background: linear-gradient(135deg, #1a3a5c 0%, #1e3a5f 100%);
          border: 1px solid #2d5f8a;
          border-radius: 12px;
          padding: 16px;
          margin-bottom: 16px;
          color: #c5ddf0;
        }
        .eligibility-banner .banner-title { font-size: 14px; font-weight: 600; margin: 0 0 6px 0; color: #64d2ff; }
        .eligibility-banner .banner-desc { font-size: 12px; margin: 0 0 12px 0; color: #8892b0; line-height: 1.5; }
        .eligibility-banner .checklist { list-style: none; padding: 0; margin: 0; }
        .eligibility-banner .checklist li { font-size: 13px; padding: 4px 0; display: flex; align-items: center; gap: 8px; }
        .eligibility-banner .checklist li .done { color: #10b981; }
        .eligibility-banner .checklist li .pending { color: #f59e0b; }
        .table-container { margin-top: 8px; }
        .badge { padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
        .badge-success { background: #10b981; color: white; }
        .badge-warning { background: #f59e0b; color: white; }
        .badge-pending { background: #6b7280; color: white; }
        .badge-info { background: #3b82f6; color: white; }
        .badge-danger { background: #ef4444; color: white; }
        .badge-primary { background: #8b5cf6; color: white; }
      </style>
      ${l.render({title:"🏆 Awards Summary",showBack:!0})}
      <div class="mnr-awards-page">
        <div id="pageContent"></div>
      </div>
    `,l.attachListeners({title:"🏆 Awards Summary",showBack:!0})}updateContent(){const e=document.getElementById("pageContent");if(!e)return;if(this.loading){e.innerHTML=`
        <div class="loading-state" style="text-align: center; padding: 40px; color: #8892b0;">
          <div class="spinner" style="width: 40px; height: 40px; border: 3px solid rgba(100,210,255,0.2); border-top-color: #64d2ff; border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto 16px;"></div>
          <p>Loading...</p>
        </div>
        <style>@keyframes spin { to { transform: rotate(360deg); } }</style>
      `;return}const t=this.getFilteredAwards();e.innerHTML=`
      ${this.renderEligibilityBanner()}

      <div class="requirements-card">
        <div class="req-header">
          <span>📹</span>
          <span>Feedback Video and Photos Requirement</span>
        </div>
        <p class="req-text">
          <strong>To claim net achieved level awards:</strong> Sharing feedback videos and photos is important.
        </p>
        <div class="activities-header">Eligible Engagement Activities:</div>
        <ul class="activities-list">
          <li>Reels (video content)</li>
          <li>WhatsApp Status sharing</li>
          <li>Social Media posts</li>
          <li>Sharing & Ratings in Announcement sections</li>
          <li>Engaging with teams</li>
          <li>Attending Zoom calls</li>
        </ul>
        <div class="note-text">
          ℹ️ Please note: Submitted feedback videos and photos may be publicly displayed on our platforms for promotional and community engagement purposes.
        </div>
      </div>

      <div class="stats-row">
        <div class="stat-card achieved">
          <div class="stat-icon">✓</div>
          <div class="stat-value">${this.stats.achieved}</div>
          <div class="stat-label">Achieved Awards<br><small>Awards you've qualified for</small></div>
        </div>
        <div class="stat-card received">
          <div class="stat-icon">🎁</div>
          <div class="stat-value">${this.stats.received}</div>
          <div class="stat-label">Received Awards<br><small>Awards already processed</small></div>
        </div>
        <div class="stat-card pending">
          <div class="stat-icon">⏳</div>
          <div class="stat-value">${this.stats.pending}</div>
          <div class="stat-label">Pending Awards<br><small>Awards awaiting processing</small></div>
        </div>
      </div>

      <div class="tabs-container">
        <button class="tab-btn ${this.activeTab==="all"?"active":""}" data-tab="all">All Awards</button>
        <button class="tab-btn ${this.activeTab==="direct"?"active":""}" data-tab="direct">Direct Business Facilitations</button>
        <button class="tab-btn ${this.activeTab==="matching"?"active":""}" data-tab="matching">Group Performance Recognitions</button>
      </div>

      <div class="table-container">
        ${this.renderAwardsTable(t)}
      </div>
    `,this.attachListeners()}getFilteredAwards(){return this.activeTab==="all"?this.awards:this.activeTab==="direct"?this.awards.filter(e=>e.category==="direct"):this.awards.filter(e=>e.category==="matching")}renderAwardsTable(e){return e.length===0?`<div class="empty-state" style="text-align: center; padding: 40px; color: #8892b0;">
        <div style="font-size: 48px; margin-bottom: 16px;">🏆</div>
        <p>No awards found</p>
      </div>`:new m({columns:[{key:"award_rank",label:"Award Rank",render:a=>`<strong style="color: #f59e0b;">${a}</strong>`},{key:"award_item",label:"Award Item"},{key:"requirement",label:"Requirement",render:a=>`<span style="color: #3b82f6;">${a}</span>`},{key:"current_progress",label:"Current Progress",render:a=>`<span style="color: #10b981;">${a}</span>`},{key:"bonanza_claimed",label:"Bonanza Claimed"},{key:"remaining",label:"Remaining",render:(a,i)=>i.achievement_status.toLowerCase()==="achieved"?'<span style="color: #10b981;">Complete</span>':`<span style="color: #ef4444;">${a}</span>`},{key:"achievement_status",label:"Achievement Status",render:a=>this.getAchievementBadge(a)},{key:"processed_status",label:"Status",render:a=>this.getProcessedBadge(a)},{key:"last_updated",label:"Last Updated",render:a=>this.formatDate(a)}],data:e,loading:!1,emptyMessage:"No awards found"}).render()}attachListeners(){document.querySelectorAll(".tab-btn").forEach(e=>{e.addEventListener("click",()=>{this.activeTab=e.getAttribute("data-tab")||"all",document.querySelectorAll(".tab-btn").forEach(t=>t.classList.remove("active")),e.classList.add("active"),this.updateContent()})})}getAchievementBadge(e){const t=e.toLowerCase();return t==="achieved"||t==="completed"?'<span class="badge badge-success">✓ Achieved</span>':'<span class="badge badge-warning">⊙ Pending</span>'}getProcessedBadge(e){const t=(e||"").toLowerCase(),a=this.getSimplifiedStatus(t);return a==="Pending"?'<span class="badge badge-warning">⊙ Pending</span>':a==="Approved"?'<span class="badge badge-info">✓ Approved</span>':a==="Processed"?'<span class="badge badge-primary">⊞ Processed</span>':a==="Completed"?'<span class="badge badge-success">✓ Completed</span>':a==="Rejected"?'<span class="badge badge-danger">✗ Rejected</span>':`<span class="badge badge-pending">${a}</span>`}getSimplifiedStatus(e){return e==="pending approval"||e==="pending"?"Pending":e==="admin approved"?"Approved":e==="procurement pending"||e==="processed for dispatch"||e==="dispatched"||e==="ordered"?"Processed":e==="delivered"||e==="delivered - completed"?"Completed":e==="rejected"?"Rejected":e||"Pending"}formatDate(e){if(!e)return'<span style="color: #6b7280;">Not Received Yet</span>';try{return new Date(e).toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"numeric"})}catch{return e}}}class re{container;referrals=[];loading=!0;showFilters=!1;sortColumn="registration_date";sortDirection="desc";filters={name:"",status_filter:"",package:"",position:"",start_date:"",end_date:""};constructor(e){this.container=e}async init(){this.render(),await this.loadReferrals()}async loadReferrals(){this.loading=!0,this.updateContent();try{const e=new URLSearchParams;this.filters.name&&e.append("name",this.filters.name),this.filters.status_filter&&e.append("status_filter",this.filters.status_filter),this.filters.package&&e.append("package",this.filters.package),this.filters.position&&e.append("position",this.filters.position),this.filters.start_date&&e.append("start_date",this.filters.start_date),this.filters.end_date&&e.append("end_date",this.filters.end_date);const t=await d.get(`/users/team/direct-referrals-filtered?${e}`);if(t.success&&t.data){const a=t.data.referrals||t.data.members||[];this.referrals=a.map(i=>({mnr_id:i.mnr_id||i.user_id||"",name:i.name||"",package:i.package||i.package_type||"None",position:i.side||i.position||"",registration_date:i.registration_date,activation_date:i.activation_date,status:i.activation_date?"Active":"Inactive"}))}}catch(e){console.error("[MNRReferrals] Failed to load:",e)}this.loading=!1,this.updateContent()}render(){this.container.innerHTML=`
      <style>
        ${m.getStyles()}
        .mnr-referrals-page { padding: 16px; }
        .filter-toggle-btn {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 10px 16px;
          background: rgba(100, 210, 255, 0.1);
          border: 1px solid rgba(100, 210, 255, 0.3);
          border-radius: 8px;
          color: #64d2ff;
          font-size: 14px;
          cursor: pointer;
          margin-bottom: 12px;
        }
        .filter-count {
          background: #ef4444;
          color: white;
          padding: 2px 8px;
          border-radius: 10px;
          font-size: 11px;
          display: none;
        }
        .filters-panel {
          display: none;
          background: rgba(22, 33, 62, 0.8);
          border-radius: 8px;
          padding: 16px;
          margin-bottom: 16px;
        }
        .filters-panel.show { display: block; }
        .filter-grid {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 12px;
        }
        .filter-group label {
          display: block;
          font-size: 11px;
          color: #8892b0;
          text-transform: uppercase;
          margin-bottom: 4px;
        }
        .filter-group input, .filter-group select {
          width: 100%;
          padding: 8px 12px;
          background: rgba(13, 27, 42, 0.8);
          border: 1px solid rgba(255,255,255,0.1);
          border-radius: 6px;
          color: #e6f1ff;
          font-size: 13px;
        }
        .filter-actions {
          display: flex;
          gap: 12px;
          margin-top: 16px;
        }
        .filter-actions button {
          flex: 1;
          padding: 10px;
          border-radius: 6px;
          font-size: 13px;
          cursor: pointer;
        }
        .btn-apply {
          background: #64d2ff;
          border: none;
          color: #0d1b2a;
          font-weight: 600;
        }
        .btn-clear {
          background: transparent;
          border: 1px solid rgba(255,255,255,0.2);
          color: #8892b0;
        }
      </style>
      ${l.render({title:"🔗 Direct Connections",showBack:!0})}
      <div class="mnr-referrals-page">
        <button class="filter-toggle-btn" id="toggleFiltersBtn">
          <span>🔍 Filter Options</span>
          <span class="filter-count" id="filterCount">0</span>
        </button>
        
        <div class="filters-panel" id="filtersPanel">
          <div class="filter-grid">
            <div class="filter-group">
              <label>Name</label>
              <input type="text" id="filterName" placeholder="Search name" value="${this.filters.name}">
            </div>
            <div class="filter-group">
              <label>Status</label>
              <select id="filterStatus">
                <option value="">All Status</option>
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
              </select>
            </div>
            <div class="filter-group">
              <label>Package</label>
              <select id="filterPackage">
                <option value="">All Packages</option>
                <option value="Platinum">Platinum</option>
                <option value="Diamond">Diamond</option>
                <option value="Star">Star</option>
                <option value="Loyal">Loyal</option>
                <option value="Blue">Blue</option>
              </select>
            </div>
            <div class="filter-group">
              <label>Group</label>
              <select id="filterPosition">
                <option value="">All Groups</option>
                <option value="left">Group A</option>
                <option value="right">Group B</option>
              </select>
            </div>
            <div class="filter-group">
              <label>Start Date</label>
              <input type="date" id="filterStartDate" value="${this.filters.start_date}">
            </div>
            <div class="filter-group">
              <label>End Date</label>
              <input type="date" id="filterEndDate" value="${this.filters.end_date}">
            </div>
          </div>
          <div class="filter-actions">
            <button class="btn-apply" id="applyFiltersBtn">Apply Filters</button>
            <button class="btn-clear" id="clearFiltersBtn">Clear</button>
          </div>
        </div>

        <div id="pageContent"></div>
      </div>
    `,this.attachListeners()}attachListeners(){l.attachListeners({title:"🔗 Direct Connections",showBack:!0}),document.getElementById("toggleFiltersBtn")?.addEventListener("click",()=>{this.showFilters=!this.showFilters,document.getElementById("filtersPanel")?.classList.toggle("show",this.showFilters)}),document.getElementById("applyFiltersBtn")?.addEventListener("click",()=>{this.collectFilters(),this.loadReferrals()}),document.getElementById("clearFiltersBtn")?.addEventListener("click",()=>{this.filters={name:"",status_filter:"",package:"",position:"",start_date:"",end_date:""},this.render(),this.loadReferrals()})}collectFilters(){this.filters.name=document.getElementById("filterName")?.value||"",this.filters.status_filter=document.getElementById("filterStatus")?.value||"",this.filters.package=document.getElementById("filterPackage")?.value||"",this.filters.position=document.getElementById("filterPosition")?.value||"",this.filters.start_date=document.getElementById("filterStartDate")?.value||"",this.filters.end_date=document.getElementById("filterEndDate")?.value||"";const e=Object.values(this.filters).filter(a=>a).length,t=document.getElementById("filterCount");t&&(t.textContent=e.toString(),t.style.display=e>0?"inline-flex":"none")}handleSort(e){this.sortColumn===e?this.sortDirection=this.sortDirection==="asc"?"desc":"asc":(this.sortColumn=e,this.sortDirection="asc"),this.sortReferrals(),this.updateContent()}sortReferrals(){this.referrals.sort((e,t)=>{let a,i;switch(this.sortColumn){case"name":a=e.name.toLowerCase(),i=t.name.toLowerCase();break;case"mnr_id":a=e.mnr_id,i=t.mnr_id;break;case"registration_date":a=e.registration_date?new Date(e.registration_date).getTime():0,i=t.registration_date?new Date(t.registration_date).getTime():0;break;case"activation_date":a=e.activation_date?new Date(e.activation_date).getTime():0,i=t.activation_date?new Date(t.activation_date).getTime():0;break;case"status":a=e.status==="Active"?1:0,i=t.status==="Active"?1:0;break;default:return 0}return a<i?this.sortDirection==="asc"?-1:1:a>i?this.sortDirection==="asc"?1:-1:0})}updateContent(){const e=document.getElementById("pageContent");if(!e)return;const t=new m({columns:[{key:"name",label:"Name",sortable:!0,render:a=>`<strong>${a}</strong>`},{key:"mnr_id",label:"MNR ID",sortable:!0},{key:"package",label:"Package",sortable:!0,render:a=>this.getPackageBadge(a)},{key:"position",label:"Group",sortable:!0,render:a=>{const i=(a||"").toLowerCase();return i==="left"?"Group A":i==="right"?"Group B":a||"-"}},{key:"registration_date",label:"Reg Date",sortable:!0,render:a=>this.formatDate(a)},{key:"activation_date",label:"Act Date",sortable:!0,render:a=>this.formatDate(a)},{key:"status",label:"Status",sortable:!0,render:a=>this.getStatusBadge(a)}],data:this.referrals,sortColumn:this.sortColumn,sortDirection:this.sortDirection,loading:this.loading,emptyMessage:"No Direct Business Facilitations yet"});e.innerHTML=`
      <div class="table-summary-bar">
        <span>Total <span class="count">${this.referrals.length}</span> Direct Business Facilitations</span>
      </div>
      ${t.render()}
    `,m.attachSortListeners(e,a=>this.handleSort(a))}getPackageBadge(e){return`<span class="badge ${{Platinum:"badge-platinum",Diamond:"badge-diamond",Star:"badge-warning",Loyal:"badge-info",Blue:"badge-primary"}[e]||"badge-secondary"}">${e}</span>`}getStatusBadge(e){return e==="Active"?'<span class="badge badge-success">Active</span>':'<span class="badge badge-secondary">Inactive</span>'}formatDate(e){if(!e)return"-";try{return new Date(e).toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"numeric"})}catch{return e}}}const D=A.MEDIA_BASE_URL;class oe{container;announcements=[];loading=!0;currentMedia=[];currentMediaIndex=0;currentRotation=0;constructor(e){this.container=e}async init(){this.render(),await this.loadAnnouncements()}async loadAnnouncements(){this.loading=!0,this.updateContent();try{const e=await d.get("/feedback/announcements");e.success&&e.data&&(this.announcements=Array.isArray(e.data)?e.data:[])}catch(e){console.error("[MNRAnnouncements] Failed to load:",e)}this.loading=!1,this.updateContent()}render(){this.container.innerHTML=`
      <div class="page-container">
        ${l.render({title:"📢 Community Updates",showBack:!0})}
        
        <div id="pageContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
      ${this.renderLightbox()}
    `,l.attachListeners({title:"📢 Community Updates",showBack:!0}),this.attachLightboxListeners()}updateContent(){const e=document.getElementById("pageContent");if(e){if(this.loading){e.innerHTML='<div class="loading-state">Loading...</div>';return}if(this.announcements.length===0){e.innerHTML=`
        <div class="empty-state card">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
            <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
          </svg>
          <h3>No Updates</h3>
          <p>Check back later for updates</p>
        </div>
      `;return}e.innerHTML=`
      <div class="announcement-count">${this.announcements.length} announcement${this.announcements.length!==1?"s":""}</div>
      <div class="announcements-list">
        ${this.announcements.map(t=>this.renderAnnouncementCard(t)).join("")}
      </div>
    `,this.attachCardListeners()}}renderAnnouncementCard(e){const t=e.category?.name||e.category?.category_name||"General",a=t.toLowerCase().replace(/\s+/g,"-");return`
      <div class="announcement-card card" data-id="${e.id}">
        <div class="announcement-header">
          <h4 class="announcement-title">${e.title}</h4>
          <span class="category-badge ${a}">${t}</span>
        </div>
        
        <p class="announcement-description">${e.description||""}</p>
        
        ${this.renderMediaGallery(e.media,e.id)}
        
        <div class="announcement-meta">
          <div class="meta-row">
            <span class="meta-item">
              <span class="meta-icon">👤</span>
              <span class="meta-label">Posted By:</span>
              <span class="meta-value">${e.user_name||"Unknown"}</span>
            </span>
            <span class="meta-item">
              <span class="meta-icon">🆔</span>
              <span class="meta-label">User ID:</span>
              <span class="meta-value">${e.user_id||"N/A"}</span>
            </span>
          </div>
          <div class="meta-row">
            <span class="meta-item">
              <span class="meta-icon">📍</span>
              <span class="meta-label">Location:</span>
              <span class="meta-value">${e.city||"N/A"}</span>
            </span>
            <span class="meta-item">
              <span class="meta-icon">⭐</span>
              <span class="meta-value">${e.average_rating?.toFixed(1)||"0.0"} (${e.total_ratings||0})</span>
            </span>
          </div>
        </div>
        
        <div class="announcement-footer">
          <span class="announcement-date">
            📅 ${this.formatDate(e.approved_at||e.updated_at)}
          </span>
          <span class="shares-count">${e.shares_count||0} shares</span>
        </div>
        
        <div class="announcement-actions">
          <button class="action-btn copy-link-btn" data-id="${e.id}">
            📋 Copy Link
          </button>
          <button class="action-btn share-whatsapp-btn" data-id="${e.id}" data-title="${e.title}">
            💬 Share on WhatsApp
          </button>
        </div>
      </div>
    `}renderMediaGallery(e,t){if(!e||e.length===0)return"";const a=e.slice(0,6),i=e.length>6?e.length-6:0,n=encodeURIComponent(JSON.stringify(e));return`
      <div class="media-gallery" data-announcement-id="${t}" data-media='${n}'>
        ${a.map((s,r)=>{const o=d.getMediaUrl(s.file_path);return`
          <div class="media-thumb ${s.media_type==="video"?"video-thumb":""}" data-index="${r}">
            ${s.media_type==="video"?`<video src="${o}" preload="metadata"></video><span class="play-icon">▶</span>`:`<img src="${o}" alt="Media ${r+1}" loading="lazy" onerror="this.style.display='none'" />`}
          </div>
        `}).join("")}
        ${i>0?`<div class="media-more" data-index="6">+${i} more</div>`:""}
      </div>
      <div class="file-count">📁 ${e.length} file(s)</div>
    `}renderLightbox(){return`
      <div id="mediaLightbox" class="media-lightbox hidden">
        <div class="lightbox-overlay"></div>
        <div class="lightbox-content">
          <button class="lightbox-close" id="lightboxClose">✕</button>
          <button class="lightbox-nav lightbox-prev" id="lightboxPrev">❮</button>
          <div class="lightbox-media-container" id="lightboxMediaContainer">
            <img id="lightboxImage" class="lightbox-image" src="" alt="Media" />
            <video id="lightboxVideo" class="lightbox-video hidden" controls></video>
          </div>
          <button class="lightbox-nav lightbox-next" id="lightboxNext">❯</button>
          <div class="lightbox-controls">
            <button class="lightbox-rotate" id="lightboxRotate">🔄 Rotate</button>
            <span class="lightbox-counter" id="lightboxCounter">1 / 1</span>
          </div>
        </div>
      </div>
    `}openLightbox(e,t=0){this.currentMedia=e,this.currentMediaIndex=t,this.currentRotation=0,this.updateLightboxMedia();const a=document.getElementById("mediaLightbox");a&&(a.classList.remove("hidden"),document.body.style.overflow="hidden")}closeLightbox(){const e=document.getElementById("mediaLightbox");e&&(e.classList.add("hidden"),document.body.style.overflow=""),this.currentRotation=0}updateLightboxMedia(){if(this.currentMedia.length===0)return;const e=this.currentMedia[this.currentMediaIndex],t=d.getMediaUrl(e.file_path),a=document.getElementById("lightboxImage"),i=document.getElementById("lightboxVideo"),n=document.getElementById("lightboxCounter");e.media_type==="video"?(a?.classList.add("hidden"),i?.classList.remove("hidden"),i&&(i.src=t,i.style.transform=`rotate(${this.currentRotation}deg)`)):(i?.classList.add("hidden"),a?.classList.remove("hidden"),a&&(a.src=t,a.style.transform=`rotate(${this.currentRotation}deg)`)),n&&(n.textContent=`${this.currentMediaIndex+1} / ${this.currentMedia.length}`);const s=document.getElementById("lightboxPrev"),r=document.getElementById("lightboxNext");s&&(s.style.visibility=this.currentMediaIndex>0?"visible":"hidden"),r&&(r.style.visibility=this.currentMediaIndex<this.currentMedia.length-1?"visible":"hidden")}navigateLightbox(e){const t=this.currentMediaIndex+e;t>=0&&t<this.currentMedia.length&&(this.currentMediaIndex=t,this.currentRotation=0,this.updateLightboxMedia())}rotateLightbox(){this.currentRotation=(this.currentRotation+90)%360;const e=document.getElementById("lightboxImage"),t=document.getElementById("lightboxVideo");e&&!e.classList.contains("hidden")&&(e.style.transform=`rotate(${this.currentRotation}deg)`),t&&!t.classList.contains("hidden")&&(t.style.transform=`rotate(${this.currentRotation}deg)`)}attachLightboxListeners(){document.getElementById("lightboxClose")?.addEventListener("click",()=>this.closeLightbox()),document.getElementById("lightboxPrev")?.addEventListener("click",()=>this.navigateLightbox(-1)),document.getElementById("lightboxNext")?.addEventListener("click",()=>this.navigateLightbox(1)),document.getElementById("lightboxRotate")?.addEventListener("click",()=>this.rotateLightbox()),document.querySelector(".lightbox-overlay")?.addEventListener("click",()=>this.closeLightbox()),document.querySelectorAll(".media-gallery").forEach(e=>{e.addEventListener("click",t=>{const i=t.target.closest(".media-thumb, .media-more");if(i){const n=e.getAttribute("data-media");if(n)try{const s=JSON.parse(decodeURIComponent(n)),r=parseInt(i.getAttribute("data-index")||"0",10);this.openLightbox(s,Math.min(r,s.length-1))}catch(s){console.error("[MNRAnnouncements] Failed to parse media:",s)}}})})}attachCardListeners(){document.querySelectorAll(".copy-link-btn").forEach(e=>{e.addEventListener("click",t=>{t.stopPropagation();const a=t.target.closest(".action-btn")?.getAttribute("data-id");a&&this.copyLink(a)})}),document.querySelectorAll(".share-whatsapp-btn").forEach(e=>{e.addEventListener("click",t=>{t.stopPropagation();const a=t.target.closest(".action-btn"),i=a?.getAttribute("data-id"),n=a?.getAttribute("data-title");i&&n&&this.shareOnWhatsApp(i,n)})}),document.querySelectorAll(".media-gallery").forEach(e=>{e.addEventListener("click",t=>{const i=t.target.closest(".media-thumb, .media-more");if(i){const n=e.getAttribute("data-media");if(n)try{const s=JSON.parse(decodeURIComponent(n)),r=parseInt(i.getAttribute("data-index")||"0",10);this.openLightbox(s,Math.min(r,s.length-1))}catch(s){console.error("[MNRAnnouncements] Failed to parse media:",s)}}})})}async copyLink(e){const t=`${D}/public/announcement?id=${e}&shared=true`;try{await N.write({string:t}),this.showToast("Link copied to clipboard!")}catch(a){console.error("[MNRAnnouncements] Clipboard write failed:",a),this.showToast("Failed to copy link")}}async shareOnWhatsApp(e,t){const a=`${D}/public/announcement?id=${e}&shared=true`,i=`Check out this announcement: ${t}
${a}`;try{await z.share({title:t,text:i,url:a,dialogTitle:"Share Announcement"})}catch(n){console.error("[MNRAnnouncements] Share failed:",n),window.open(`https://wa.me/?text=${encodeURIComponent(i)}`,"_blank")}}showToast(e){const t=document.createElement("div");t.className="toast-message",t.textContent=e,document.body.appendChild(t),setTimeout(()=>t.remove(),3e3)}formatDate(e){if(!e)return"N/A";try{return new Date(e).toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"numeric",hour:"2-digit",minute:"2-digit"})}catch{return e}}}class de{container;kycStatus=null;loading=!0;uploading=null;constructor(e){this.container=e}async init(){this.render(),await this.loadKYC()}async loadKYC(){this.loading=!0,this.updateContent();try{const e=await d.get("/users/profile");if(e.success&&e.data){const t=e.data;this.kycStatus={overall_status:t.kyc_status||"Pending",profile_photo:{type:"Profile Photo",key:"profile_photo",status:t.profile_photo_url?"Uploaded":"Required",number:t.profile_photo_url?"Photo uploaded":"Please upload",verified_on:null,canUpload:!0,url:t.profile_photo_url},passport_photo:{type:"Passport Size Photo",key:"passport_photo",status:t.passport_photo_url?"Uploaded":"Required",number:t.passport_photo_url?"Photo uploaded":"Please upload",verified_on:null,canUpload:!0,url:t.passport_photo_url},aadhaar:{type:"Aadhaar Card",key:"aadhaar",status:t.aadhaar_number?"Verified":"Pending",number:t.aadhaar_number?this.maskNumber(t.aadhaar_number):"Not provided",verified_on:null,canUpload:!t.aadhaar_number,url:t.aadhaar_front_url},pan:{type:"PAN Card",key:"pan",status:t.pan_number?"Verified":"Pending",number:t.pan_number?this.maskNumber(t.pan_number):"Not provided",verified_on:null,canUpload:!t.pan_number,url:t.pan_url},bank:{type:"Bank Passbook",key:"bank",status:t.bank_name?"Verified":"Pending",number:t.bank_name||"Not linked",verified_on:null,canUpload:!t.bank_name}}}}catch(e){console.error("[MNRKYC] Failed to load:",e)}this.loading=!1,this.updateContent()}render(){this.container.innerHTML=`
      <div class="page-container">
        ${l.render({title:"📄 KYC Documents",showBack:!0})}
        
        <div id="pageContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
      
      <input type="file" id="kycFileInput" accept="image/*,.pdf" style="display:none">
    `,l.attachListeners({title:"📄 KYC Documents",showBack:!0})}updateContent(){const e=document.getElementById("pageContent");if(!e)return;if(this.loading){e.innerHTML='<div class="loading-state">Loading...</div>';return}const t=this.kycStatus,a=t?.overall_status||"Pending",i=a.toLowerCase().replace(" ","-");e.innerHTML=`
      <div class="kyc-status-banner card ${i}">
        <div class="status-icon">
          ${a==="Verified"?"✓":a==="Rejected"?"✗":"⏳"}
        </div>
        <div class="status-info">
          <h3>KYC Status: ${a}</h3>
          <p>${this.getStatusMessage(a)}</p>
        </div>
      </div>

      <h3 class="section-title">Photo Documents</h3>
      <div class="kyc-documents photo-docs">
        ${this.renderDocument(t?.profile_photo)}
        ${this.renderDocument(t?.passport_photo)}
      </div>

      <h3 class="section-title">Identity Documents</h3>
      <div class="kyc-documents">
        ${this.renderDocument(t?.aadhaar)}
        ${this.renderDocument(t?.pan)}
        ${this.renderDocument(t?.bank)}
      </div>

      <div class="notice-card card info">
        <h4>📋 Upload Guidelines</h4>
        <ul>
          <li>Documents must be clear and readable</li>
          <li>Accepted formats: JPG, PNG, PDF</li>
          <li>Maximum file size: 5 MB</li>
          <li>Ensure all details are visible</li>
        </ul>
      </div>

      <div class="kyc-info card">
        <h4>Important Notes</h4>
        <ul class="info-list">
          <li>KYC verification is mandatory for withdrawals</li>
          <li>Documents are verified within 24-48 hours</li>
          <li>Ensure all details match your bank records</li>
          <li>Contact support if verification is delayed</li>
        </ul>
      </div>
    `,this.attachUploadListeners()}attachUploadListeners(){document.querySelectorAll(".upload-btn").forEach(t=>{t.addEventListener("click",a=>{const i=a.currentTarget.dataset.doc;i&&this.initiateUpload(i)})}),document.querySelectorAll(".view-btn").forEach(t=>{t.addEventListener("click",a=>{const i=a.currentTarget.dataset.url;i&&window.open(i,"_blank")})});const e=document.getElementById("kycFileInput");e&&e.addEventListener("change",async t=>{const a=t.target.files?.[0];a&&this.uploading&&await this.uploadDocument(this.uploading,a),e.value=""})}initiateUpload(e){this.uploading=e;const t=document.getElementById("kycFileInput");t&&t.click()}async uploadDocument(e,t){const a=document.querySelector(`[data-doc="${e}"]`);a&&(a.textContent="Uploading...",a.disabled=!0);try{const i=new FormData;i.append("file",t),i.append("document_type",e);const n=await d.uploadFile("/profile/upload-kyc-document",i);n.success?(alert(`${e.toUpperCase()} document uploaded successfully! It will be reviewed within 24-48 hours.`),await this.loadKYC()):alert(n.error||"Failed to upload document. Please try again.")}catch(i){console.error("[MNRKYC] Upload failed:",i),alert("Failed to upload document. Please try again later.")}finally{this.uploading=null,a&&(a.textContent="Upload",a.disabled=!1)}}renderDocument(e){if(!e)return"";const t=e.status.toLowerCase().replace(" ","-"),a=this.uploading===e.key,i=e.key==="profile_photo"||e.key==="passport_photo";return`
      <div class="kyc-doc card ${t}">
        <div class="doc-header">
          <div class="doc-icon">
            ${{profile_photo:"📷",passport_photo:"🖼️",aadhaar:"🪪",pan:"📄",bank:"🏦"}[e.key]||"📄"}
          </div>
          <div class="doc-info">
            <h4>${e.type}</h4>
            <p class="doc-number">${e.number}</p>
          </div>
          <div class="doc-status ${t}">
            ${e.status}
          </div>
        </div>
        ${e.url&&i?`
          <div class="photo-preview">
            <img src="${e.url}" alt="${e.type}" class="preview-img">
          </div>
        `:""}
        ${e.canUpload||i?`
          <div class="doc-actions">
            <button class="btn ${e.url?"btn-secondary":"btn-primary"} upload-btn" data-doc="${e.key}" ${a?"disabled":""}>
              ${a?"Uploading...":e.url?"Change Photo":"Upload"}
            </button>
            ${e.url?`<button class="btn btn-outline view-btn" data-url="${e.url}">View</button>`:""}
          </div>
        `:`
          <div class="doc-verified">
            <span class="verified-badge">✓ Submitted</span>
          </div>
        `}
      </div>

      <style>
        .photo-preview { margin: 12px 0; text-align: center; }
        .preview-img { max-width: 120px; max-height: 120px; border-radius: 8px; border: 2px solid #64ffda; }
        .doc-actions { display: flex; gap: 8px; margin-top: 8px; }
        .doc-actions .btn { flex: 1; }
        .btn-outline { background: transparent; border: 1px solid #64ffda; color: #64ffda; }
        .photo-docs { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
        @media (max-width: 400px) { .photo-docs { grid-template-columns: 1fr; } }
      </style>
    `}getStatusMessage(e){switch(e){case"Verified":return"All documents verified successfully";case"Rejected":return"Some documents were rejected. Please re-upload.";case"Pending":return"Documents are under review";default:return"Please complete your KYC"}}maskNumber(e){return e.length<=4?e:"XXXX"+e.slice(-4)}}class le{container;bankDetails=null;loading=!0;editMode=!1;saving=!1;constructor(e){this.container=e}async init(){this.render(),await this.loadBankDetails()}async loadBankDetails(){this.loading=!0,this.updateContent();try{const e=await d.get("/users/profile/banking");e.success&&e.data&&(this.bankDetails=e.data)}catch(e){console.error("[MNRBankDetails] Failed to load:",e)}this.loading=!1,this.updateContent()}render(){this.container.innerHTML=`
      <div class="page-container">
        ${l.render({title:"🏦 Bank Details",showBack:!0})}
        
        <div id="pageContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
    `,l.attachListeners({title:"🏦 Bank Details",showBack:!0})}updateContent(){const e=document.getElementById("pageContent");if(!e)return;if(this.loading){e.innerHTML='<div class="loading-state">Loading...</div>';return}const t=this.bankDetails;if(this.editMode||!t||!t.bank_name){e.innerHTML=this.renderEditForm(t),this.attachEditListeners();return}e.innerHTML=`
      <div class="bank-card card">
        <div class="bank-header">
          <div class="bank-logo">🏦</div>
          <div class="bank-name-section">
            <h3>${t.bank_name}</h3>
            <span class="verify-badge ${t.is_verified?"verified":"pending"}">
              ${t.is_verified?"✓ Verified":"⏳ Pending"}
            </span>
          </div>
        </div>
        
        <div class="bank-details-grid">
          <div class="detail-row">
            <span class="detail-label">Account Holder</span>
            <span class="detail-value">${t.account_holder_name||"N/A"}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">Account Number</span>
            <span class="detail-value">${this.maskAccount(t.account_number)}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">IFSC Code</span>
            <span class="detail-value">${t.ifsc_code||"N/A"}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">Branch</span>
            <span class="detail-value">${t.branch||"N/A"}</span>
          </div>
        </div>
        
        <button class="btn btn-primary btn-full" id="editBankBtn">
          ✏️ Edit Bank Details
        </button>
      </div>

      <div class="bank-info card">
        <h4>Important Notes</h4>
        <ul class="info-list">
          <li>Bank verification takes 24-48 hours</li>
          <li>Withdrawals will be credited to this account</li>
          <li>Contact support to update bank details</li>
          <li>Account name must match your registered name</li>
        </ul>
      </div>
    `,document.getElementById("editBankBtn")?.addEventListener("click",()=>{this.editMode=!0,this.updateContent()})}renderEditForm(e){return`
      <div class="edit-form card">
        <h3 class="form-title">💳 ${e?.bank_name?"Edit":"Add"} Bank Details</h3>
        
        <div class="form-group">
          <label>Bank Name *</label>
          <input type="text" id="bankName" class="form-input" 
            value="${e?.bank_name||""}" placeholder="Enter bank name" required>
        </div>
        
        <div class="form-group">
          <label>Account Holder Name *</label>
          <input type="text" id="accountHolder" class="form-input" 
            value="${e?.account_holder_name||""}" placeholder="Name as per bank account" required>
        </div>
        
        <div class="form-group">
          <label>Account Number *</label>
          <input type="text" id="accountNumber" class="form-input" 
            value="${e?.account_number||""}" placeholder="Enter account number" required>
        </div>
        
        <div class="form-group">
          <label>IFSC Code *</label>
          <input type="text" id="ifscCode" class="form-input" 
            value="${e?.ifsc_code||""}" placeholder="e.g., SBIN0001234" required>
        </div>
        
        <div class="form-group">
          <label>Branch</label>
          <input type="text" id="branchName" class="form-input" 
            value="${e?.branch||""}" placeholder="Branch name">
        </div>
        
        <div class="form-actions">
          <button class="btn btn-secondary" id="cancelEditBtn" ${this.saving?"disabled":""}>
            Cancel
          </button>
          <button class="btn btn-primary" id="saveBankBtn" ${this.saving?"disabled":""}>
            ${this.saving?"Saving...":"Save Details"}
          </button>
        </div>
      </div>
    `}attachEditListeners(){document.getElementById("cancelEditBtn")?.addEventListener("click",()=>{this.bankDetails?.bank_name&&(this.editMode=!1,this.updateContent())}),document.getElementById("saveBankBtn")?.addEventListener("click",()=>{this.saveBankDetails()})}async saveBankDetails(){const e=document.getElementById("bankName")?.value?.trim(),t=document.getElementById("accountHolder")?.value?.trim(),a=document.getElementById("accountNumber")?.value?.trim(),i=document.getElementById("ifscCode")?.value?.trim(),n=document.getElementById("branchName")?.value?.trim();if(!e||!t||!a||!i){alert("Please fill in all required fields");return}this.saving=!0,this.updateContent();try{const s=await d.put("/users/profile/banking",{bank_name:e,account_holder_name:t,account_number:a,ifsc_code:i,branch:n||null});s.success?(alert("Bank details saved successfully!"),this.editMode=!1,await this.loadBankDetails()):alert(s.error||"Failed to save bank details")}catch(s){console.error("[MNRBankDetails] Save failed:",s),alert("Failed to save bank details. Please try again.")}finally{this.saving=!1}}maskAccount(e){return!e||e.length<=4?e||"N/A":"XXXXXXXX"+e.slice(-4)}}class ce{container;loading=!1;error="";success="";constructor(e){this.container=e}async init(){this.render()}render(){this.container.innerHTML=`
      <div class="page-container">
        ${l.render({title:"🔐 Change Password",showBack:!0})}
        
        <div class="form-container">
          <div class="password-form card">
            <div id="formMessages"></div>
            
            <div class="form-group">
              <label for="currentPassword">Current Password</label>
              <div class="password-input-wrapper">
                <input type="password" id="currentPassword" placeholder="Enter current password">
                <button type="button" class="toggle-password" data-target="currentPassword">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                    <circle cx="12" cy="12" r="3"/>
                  </svg>
                </button>
              </div>
            </div>

            <div class="form-group">
              <label for="newPassword">New Password</label>
              <div class="password-input-wrapper">
                <input type="password" id="newPassword" placeholder="Enter new password">
                <button type="button" class="toggle-password" data-target="newPassword">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                    <circle cx="12" cy="12" r="3"/>
                  </svg>
                </button>
              </div>
            </div>

            <div class="form-group">
              <label for="confirmPassword">Confirm New Password</label>
              <div class="password-input-wrapper">
                <input type="password" id="confirmPassword" placeholder="Confirm new password">
                <button type="button" class="toggle-password" data-target="confirmPassword">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                    <circle cx="12" cy="12" r="3"/>
                  </svg>
                </button>
              </div>
            </div>

            <button id="changePasswordBtn" class="btn-primary" ${this.loading?"disabled":""}>
              ${this.loading?"Changing...":"Change Password"}
            </button>
          </div>

          <div class="password-tips card">
            <h4>Password Requirements</h4>
            <ul class="tips-list">
              <li>At least 8 characters long</li>
              <li>Include uppercase and lowercase letters</li>
              <li>Include at least one number</li>
              <li>Include at least one special character</li>
            </ul>
          </div>
        </div>
      </div>
    `,this.attachListeners()}attachListeners(){l.attachListeners({title:"🔐 Change Password",showBack:!0}),this.container.querySelectorAll(".toggle-password").forEach(e=>{e.addEventListener("click",()=>{const t=e.getAttribute("data-target");if(t){const a=document.getElementById(t);a&&(a.type=a.type==="password"?"text":"password")}})}),document.getElementById("changePasswordBtn")?.addEventListener("click",()=>{this.handleChangePassword()})}async handleChangePassword(){const e=document.getElementById("currentPassword").value,t=document.getElementById("newPassword").value,a=document.getElementById("confirmPassword").value;if(this.error="",this.success="",!e||!t||!a){this.showMessage("Please fill in all fields","error");return}if(t!==a){this.showMessage("New passwords do not match","error");return}if(t.length<8){this.showMessage("Password must be at least 8 characters","error");return}this.loading=!0,this.render();try{const i=await d.post("/users/profile/change-password",{current_password:e,new_password:t,confirm_password:a});i.success?(this.showMessage("Password changed successfully!","success"),setTimeout(()=>{f.navigate("mnr-profile")},2e3)):this.showMessage(i.error||"Failed to change password","error")}catch(i){this.showMessage(i.message||"An error occurred","error")}this.loading=!1}showMessage(e,t){const a=document.getElementById("formMessages");a&&(a.innerHTML=`<div class="message ${t}">${e}</div>`)}}class pe{container;balance=null;transactions=[];loading=!0;constructor(e){this.container=e}async init(){this.render(),await this.loadPoints()}async loadPoints(){this.loading=!0,this.updateContent();try{const[e,t]=await Promise.all([d.get("/myntreal/points/me"),d.get("/myntreal/points/me/history")]);if(e.success&&e.data){const a=e.data,i=a.member||null,n=i?.activation_date||a.activation_date||null,s=new Date("2025-12-01"),r=n?new Date(n)<s:!1,o=a.is_coupon_paid||i&&i.is_coupon_paid||!1;this.balance={current_balance:a.current_balance||0,initial_points:a.initial_points||0,total_credited:a.total_credited||0,total_consumed:a.total_consumed||0,receipt_no:a.receipt_no||null,package_name:a.package_name||"None",expiry_date:a.expiry_date||null,activation_date:n,is_exception:r,is_coupon_paid:o,member:i?{name:i.name||"",mnr_id:i.mnr_id||"",activation_date:i.activation_date||null,coupon_purchase_date:i.coupon_purchase_date||null,coupon_status:i.coupon_status||null}:null}}if(t.success&&t.data){const a=t.data.transactions||t.data||[];this.transactions=a.map(i=>({id:i.id||0,transaction_type:i.transaction_type||i.type||"Credit",amount:i.amount||0,balance_after:i.balance_after||0,category_name:i.category_name||"",lead_id:i.lead_id||null,description:i.description||i.remarks||"",created_at:i.created_at||i.date||""}))}}catch(e){console.error("[MNRPoints] Failed to load:",e)}this.loading=!1,this.updateContent()}render(){this.container.innerHTML=`
      <style>
        ${m.getStyles()}
        .mnr-points-page { padding: 16px; }
        .points-summary {
          display: grid;
          grid-template-columns: 1fr;
          gap: 12px;
          margin-bottom: 16px;
        }
        .balance-card {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          border-radius: 12px;
          padding: 20px;
          text-align: center;
          color: white;
        }
        .balance-card .label { font-size: 12px; opacity: 0.9; margin-bottom: 4px; }
        .balance-card .value { font-size: 36px; font-weight: 700; }
        .balance-card .package { font-size: 13px; margin-top: 8px; opacity: 0.8; }
        .points-breakdown {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 8px;
        }
        .points-stat {
          background: rgba(22, 33, 62, 0.8);
          border-radius: 8px;
          padding: 12px;
          text-align: center;
        }
        .points-stat .label { font-size: 11px; color: #8892b0; text-transform: uppercase; }
        .points-stat .value { font-size: 18px; font-weight: 600; color: #e6f1ff; }
        .section-title {
          font-size: 16px;
          font-weight: 600;
          color: #e6f1ff;
          margin: 20px 0 12px;
        }
        .validity-section {
          background: rgba(22, 33, 62, 0.8);
          border-radius: 10px;
          padding: 16px;
          margin-bottom: 16px;
          text-align: center;
        }
        .validity-section .title { color: #8892b0; font-size: 12px; margin-bottom: 4px; }
        .validity-section .expiry { color: #f59e0b; font-size: 14px; font-weight: 600; }
        .validity-section .remaining { color: #10b981; font-size: 16px; font-weight: 700; margin-top: 4px; }
        .exception-banner {
          background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
          border-radius: 10px;
          padding: 14px;
          margin-bottom: 16px;
          color: white;
          font-size: 12px;
          text-align: center;
        }
        .exception-banner .icon { font-size: 16px; margin-right: 6px; }
        .receipt-banner {
          background: linear-gradient(135deg, #10b981 0%, #059669 100%);
          border-radius: 10px;
          padding: 14px;
          margin-bottom: 16px;
          color: white;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        .receipt-banner .info { font-size: 13px; }
        .receipt-banner .receipt-no { font-weight: 700; font-size: 14px; }
        .btn-download {
          background: white;
          color: #059669;
          border: none;
          padding: 8px 14px;
          border-radius: 6px;
          font-size: 12px;
          font-weight: 600;
          cursor: pointer;
          display: flex;
          align-items: center;
          gap: 4px;
        }
        .available-points {
          background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
          border-radius: 12px;
          padding: 20px;
          text-align: center;
          color: white;
          margin-bottom: 16px;
        }
        .available-points .label { font-size: 12px; opacity: 0.9; margin-bottom: 4px; }
        .available-points .value { font-size: 36px; font-weight: 700; }
        .available-points .note { font-size: 11px; opacity: 0.8; margin-top: 8px; }
        .important-notice {
          background: rgba(220, 38, 38, 0.15);
          border-left: 4px solid #dc2626;
          padding: 14px 16px;
          border-radius: 8px;
          margin-bottom: 16px;
        }
        .important-notice h6 {
          color: #fca5a5;
          margin: 0 0 8px 0;
          font-weight: 600;
          font-size: 13px;
          display: flex;
          align-items: center;
          gap: 6px;
        }
        .important-notice ul {
          margin: 0;
          padding-left: 18px;
          color: #fca5a5;
          font-size: 12px;
        }
        .important-notice li { margin-bottom: 4px; }
        .important-notice strong { color: #fecaca; }
        .feedback-notice {
          background: rgba(234, 179, 8, 0.15);
          border-left: 4px solid #eab308;
          padding: 14px 16px;
          border-radius: 8px;
          margin-bottom: 16px;
        }
        .feedback-notice h6 {
          color: #fde68a;
          margin: 0 0 8px 0;
          font-weight: 600;
          font-size: 13px;
          display: flex;
          align-items: center;
          gap: 6px;
        }
        .feedback-notice p {
          color: #fde68a;
          font-size: 12px;
          margin: 0 0 8px 0;
        }
        .feedback-notice ul {
          margin: 0;
          padding-left: 18px;
          color: #fde68a;
          font-size: 12px;
        }
        .feedback-notice li { margin-bottom: 3px; }
        .feedback-notice .consent-note {
          color: #fbbf24;
          font-size: 11px;
          font-style: italic;
          margin-top: 10px;
          margin-bottom: 0;
        }
        .feedback-notice strong { color: #fef3c7; }
        .zynova-roles {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 10px;
          margin-bottom: 16px;
        }
        .zynova-role-card {
          background: rgba(22, 33, 62, 0.8);
          border-radius: 10px;
          padding: 16px;
          text-align: center;
        }
        .zynova-role-card.real-estate { border-left: 3px solid #3b82f6; }
        .zynova-role-card.insurance { border-left: 3px solid #ef4444; }
        .zynova-role-card .segment-icon { font-size: 22px; margin-bottom: 6px; }
        .zynova-role-card .segment-name { font-size: 11px; color: #8892b0; margin-bottom: 4px; }
        .zynova-role-card .role-name { font-size: 14px; font-weight: 700; color: #e6f1ff; }
        .utilisation-chart {
          display: flex;
          align-items: center;
          gap: 16px;
          padding: 16px;
          background: rgba(22, 33, 62, 0.8);
          border-radius: 12px;
          margin-bottom: 16px;
        }
        .chart-circle {
          width: 100px;
          height: 100px;
          border-radius: 50%;
          background: conic-gradient(#059669 0deg, #059669 var(--used-deg), rgba(255,255,255,0.15) var(--used-deg), rgba(255,255,255,0.15) 360deg);
          display: flex;
          align-items: center;
          justify-content: center;
          position: relative;
          flex-shrink: 0;
        }
        .chart-circle::before {
          content: '';
          position: absolute;
          width: 68px;
          height: 68px;
          background: rgba(10, 25, 47, 0.95);
          border-radius: 50%;
        }
        .chart-circle .percent {
          position: relative;
          z-index: 1;
          font-size: 16px;
          font-weight: 700;
          color: #e6f1ff;
        }
        .chart-legend { flex: 1; }
        .legend-item {
          display: flex;
          align-items: center;
          margin-bottom: 10px;
        }
        .legend-dot {
          width: 10px;
          height: 10px;
          border-radius: 50%;
          margin-right: 8px;
          flex-shrink: 0;
        }
        .legend-dot.used { background: #059669; }
        .legend-dot.available { background: rgba(255,255,255,0.15); }
        .legend-text { flex: 1; color: #8892b0; font-size: 12px; }
        .legend-value { font-weight: 600; color: #e6f1ff; font-size: 13px; }
        .payment-slip-section {
          margin-top: 12px;
        }
        .payment-slip-buttons {
          display: flex;
          gap: 8px;
          justify-content: center;
          flex-wrap: wrap;
        }
        .btn-receipt-pdf {
          background: linear-gradient(135deg, #059669, #047857);
          border: none;
          color: white;
          border-radius: 8px;
          padding: 10px 18px;
          font-weight: 600;
          font-size: 12px;
          cursor: pointer;
          display: inline-flex;
          align-items: center;
          gap: 6px;
        }
        .btn-receipt-print {
          background: linear-gradient(135deg, #2563eb, #1d4ed8);
          border: none;
          color: white;
          border-radius: 8px;
          padding: 10px 18px;
          font-weight: 600;
          font-size: 12px;
          cursor: pointer;
          display: inline-flex;
          align-items: center;
          gap: 6px;
        }
        .exemption-msg {
          background: rgba(16, 185, 129, 0.15);
          color: #6ee7b7;
          padding: 10px 16px;
          border-radius: 8px;
          font-weight: 500;
          font-size: 12px;
          text-align: center;
        }
        .motivational-msg {
          background: linear-gradient(135deg, rgba(245, 158, 11, 0.2), rgba(217, 119, 6, 0.2));
          color: #fde68a;
          padding: 16px;
          border-radius: 10px;
          font-weight: 600;
          text-align: center;
          font-size: 14px;
        }
        .motivational-msg .sub {
          font-size: 11px;
          font-weight: 400;
          margin-top: 6px;
          opacity: 0.8;
        }
        .page-subtitle {
          font-size: 12px;
          color: #8892b0;
          margin-top: 2px;
          text-align: center;
        }
      </style>
      ${l.render({title:"💰 Points Balance and Utilisation",showBack:!0})}
      <div class="mnr-points-page">
        <p class="page-subtitle">Track your MNR Points across all systems</p>
        <div id="importantNotices"></div>
        <div id="summarySection"></div>
        <h3 class="section-title">Transactions History</h3>
        <div id="pageContent"></div>
      </div>
    `,l.attachListeners({title:"💰 Points Balance and Utilisation",showBack:!0})}updateContent(){const e=document.getElementById("importantNotices");e&&(e.innerHTML=`
        <div class="important-notice">
          <h6>⚠️ Important Information</h6>
          <ul>
            <li>Points are <strong>non-refundable</strong> and <strong>non-transferable</strong></li>
            <li>Validity: <strong>24 months</strong> from the activation date</li>
            <li>Unused credits expire automatically without refund</li>
          </ul>
        </div>
        <div class="feedback-notice">
          <h6>📹 Feedback Video and Photos Requirement</h6>
          <p><strong>For members activated before 1st Dec 2025 who received exemption:</strong> Sharing feedback videos and photos is mandatory to be eligible for incentives or points benefits.</p>
          <p style="margin-bottom: 6px;"><strong>Eligible Engagement Activities:</strong></p>
          <ul>
            <li>Reels (video content)</li>
            <li>WhatsApp Status sharing</li>
            <li>Social Media posts</li>
            <li>Sharing & Ratings in Announcement sections</li>
            <li>Engaging with teams</li>
            <li>Attending Zoom calls</li>
          </ul>
          <p class="consent-note">ℹ️ Please note: Submitted feedback videos and photos may be publicly displayed on our platforms for promotional and community engagement purposes. By sharing your content, you acknowledge and consent to this use.</p>
        </div>
      `);const t=document.getElementById("summarySection");if(t&&this.balance){const n=this.getExpiryInfo(),s=this.balance.initial_points+this.balance.total_credited,r=this.balance.total_consumed,o=s>0?Math.round(r/s*100):0,c=o/100*360;let p="";this.balance.is_exception?p=`
          <div class="payment-slip-section">
            <div class="exemption-msg">
              ℹ️ Exception Coupon (Activated before Dec 1, 2025) - Payment receipt not available
            </div>
          </div>
        `:this.balance.is_coupon_paid?p=`
          <div class="payment-slip-section">
            <div class="payment-slip-buttons">
              <button class="btn-receipt-pdf" id="btnDownloadPdf">📄 Download Receipt (PDF)</button>
              <button class="btn-receipt-print" id="btnPrintReceipt">🖨️ Print Receipt</button>
            </div>
          </div>
        `:p=`
          <div class="payment-slip-section">
            <div class="motivational-msg">
              🚀 Your take an opportunity for a great Journey
              <div class="sub">Apply a coupon to unlock full benefits and download your payment receipt</div>
            </div>
          </div>
        `,t.innerHTML=`
        <div class="points-summary">
          <div class="balance-card">
            <div class="label">Current Balance</div>
            <div class="value">${this.balance.current_balance.toLocaleString()}</div>
            <div class="package">${this.balance.package_name} Package</div>
          </div>
          
          ${this.balance.expiry_date?`
            <div class="validity-section">
              <div class="title">Points Validity Status</div>
              <div class="expiry">Expires: ${n.formatted}</div>
              <div class="remaining">${n.remaining}</div>
            </div>
          `:""}

          <div class="zynova-roles">
            <div class="zynova-role-card real-estate">
              <div class="segment-icon">🏢</div>
              <div class="segment-name">VGK Real Dreams</div>
              <div class="role-name">-</div>
            </div>
            <div class="zynova-role-card insurance">
              <div class="segment-icon">🛡️</div>
              <div class="segment-name">VGK Care</div>
              <div class="role-name">-</div>
            </div>
          </div>
          
          <div class="available-points">
            <div class="label">Available MNR Points</div>
            <div class="value">${this.balance.current_balance.toLocaleString()}</div>
            <div class="note">Points can be used for incentives across all MyntReal systems</div>
            ${p}
          </div>
          
          ${this.balance.receipt_no?`
            <div class="receipt-banner">
              <div class="info">
                <div>Payment Receipt Available</div>
                <div class="receipt-no">Receipt: ${this.balance.receipt_no}</div>
              </div>
              <button class="btn-download" id="btnDownloadReceipt">
                📄 Download
              </button>
            </div>
          `:""}
          
          <div class="points-breakdown">
            <div class="points-stat">
              <div class="label">Initial</div>
              <div class="value">${this.balance.initial_points.toLocaleString()}</div>
            </div>
            <div class="points-stat">
              <div class="label">Credited</div>
              <div class="value" style="color: #10b981;">+${this.balance.total_credited.toLocaleString()}</div>
            </div>
            <div class="points-stat">
              <div class="label">Consumed</div>
              <div class="value" style="color: #ef4444;">-${this.balance.total_consumed.toLocaleString()}</div>
            </div>
          </div>

          <div class="section-title" style="margin-top: 16px;">📊 Points Utilisation</div>
          <div class="utilisation-chart" style="--used-deg: ${c}deg;">
            <div class="chart-circle" style="--used-deg: ${c}deg;">
              <span class="percent">${o}%</span>
            </div>
            <div class="chart-legend">
              <div class="legend-item">
                <div class="legend-dot used"></div>
                <span class="legend-text">Points Used</span>
                <span class="legend-value">${r.toLocaleString()}</span>
              </div>
              <div class="legend-item">
                <div class="legend-dot available"></div>
                <span class="legend-text">Points Available</span>
                <span class="legend-value">${this.balance.current_balance.toLocaleString()}</span>
              </div>
            </div>
          </div>
        </div>
      `;const g=document.getElementById("btnDownloadReceipt");g&&g.addEventListener("click",()=>this.downloadReceipt());const v=document.getElementById("btnDownloadPdf");v&&v.addEventListener("click",()=>this.downloadReceipt());const h=document.getElementById("btnPrintReceipt");h&&h.addEventListener("click",()=>this.printReceipt())}const a=document.getElementById("pageContent");if(!a)return;const i=new m({columns:[{key:"transaction_type",label:"Type",render:n=>this.getTypeBadge(n)},{key:"amount",label:"Amount",render:(n,s)=>{const r=s.transaction_type.toLowerCase(),o=r.includes("debit")||r.includes("consume")||r.includes("redeem")||r.includes("used")||r.includes("consumption"),c=r.includes("credit")||r.includes("allocation")||r.includes("bonus")||r.includes("reward")||r.includes("initial");let p="#e6f1ff",g="";return o||n<0?(p="#ef4444",g=n>0?"-":""):(c||n>=0)&&(p="#10b981",g=n<0?"":"+"),`<span style="color: ${p}; font-weight: 600;">${g}${Math.abs(n).toLocaleString()}</span>`}},{key:"balance_after",label:"Balance",render:n=>`<span style="color: #e6f1ff;">${(n||0).toLocaleString()}</span>`},{key:"description",label:"Description"},{key:"created_at",label:"Date",render:n=>this.formatDate(n)}],data:this.transactions,loading:this.loading,emptyMessage:"No transactions yet"});a.innerHTML=`
      <div class="table-summary-bar">
        <span>Total <span class="count">${this.transactions.length}</span> transactions</span>
      </div>
      ${i.render()}
    `}getTypeBadge(e){const t=e.toLowerCase();return t.includes("credit")||t.includes("allocation")||t.includes("bonus")||t.includes("reward")||t.includes("initial")?'<span class="badge badge-success">Credit</span>':t.includes("debit")||t.includes("consume")||t.includes("redeem")||t.includes("used")?'<span class="badge badge-danger">Debit</span>':t.includes("consumption")?'<span class="badge badge-warning" style="background: rgba(245, 158, 11, 0.2); color: #fbbf24;">Consumption</span>':`<span class="badge badge-secondary">${e}</span>`}formatDate(e){if(!e)return"-";try{return new Date(e).toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"numeric"})}catch{return e}}getExpiryInfo(){if(!this.balance?.expiry_date)return{formatted:"Not set",remaining:""};try{const e=new Date(this.balance.expiry_date),t=new Date,a=e.getTime()-t.getTime();if(a<=0)return{formatted:e.toLocaleDateString("en-IN",{day:"numeric",month:"long",year:"numeric"}),remaining:"Expired"};const i=Math.floor(a/(1e3*60*60*24)),n=Math.floor(i/30),s=i%30;let r="";return n>0&&(r+=`${n} month${n>1?"s":""} `),s>0&&(r+=`${s} day${s>1?"s":""} `),r+="remaining",{formatted:e.toLocaleDateString("en-IN",{day:"numeric",month:"long",year:"numeric"}),remaining:r}}catch{return{formatted:"Invalid",remaining:""}}}async downloadReceipt(){if(!this.balance?.receipt_no&&!this.balance?.is_coupon_paid){alert("No receipt available");return}try{const e=d.getBaseUrl(),t=d.getToken(),a=`${e}/receipt/membership-receipt`,i=document.createElement("a");i.href=a,i.target="_blank",i.click()}catch{const t=this.balance?.receipt_no?`Receipt: ${this.balance.receipt_no}

`:"";alert(t+"PDF download will be available soon.")}}async printReceipt(){try{const t=`${d.getBaseUrl()}/receipt/membership-receipt`,a=window.open(t,"_blank");a&&(a.onload=()=>a.print())}catch{alert("Print receipt will be available soon.")}}}class ue{container;coupons=[];stats=null;loading=!0;activeTab="all";constructor(e){this.container=e}async init(){this.render(),await this.loadCoupons()}async loadCoupons(){this.loading=!0,this.updateContent();try{const[e,t]=await Promise.all([d.get("/ev-discount/my-coupons"),d.get("/users/dashboard-data-fast")]);if(e.success&&e.data){const a=e.data.coupons||e.data||[];this.coupons=a.map(i=>({id:i.id||0,coupon_code:i.coupon_code||i.code||"",benefit_type:i.benefit_type||i.type||"EV Discount",value:i.value||i.discount_value||0,status:i.status||"Available",created_at:i.created_at||i.issue_date||"",redeemed_at:i.redeemed_at||i.used_at||null})),this.stats={total_coupons:a.length,redeemed_coupons:a.filter(i=>i.status?.toLowerCase()==="redeemed"||i.status?.toLowerCase()==="used").length,available_coupons:a.filter(i=>i.status?.toLowerCase()==="available"||i.status?.toLowerCase()==="active").length,total_value_redeemed:a.filter(i=>i.status?.toLowerCase()==="redeemed"||i.status?.toLowerCase()==="used").reduce((i,n)=>i+(n.value||0),0)}}}catch(e){console.error("[MNRCoupons] Failed to load:",e)}this.loading=!1,this.updateContent()}render(){this.container.innerHTML=`
      <style>
        ${m.getStyles()}
        .mnr-coupons-page { padding: 16px; }
        .coupons-summary {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 12px;
          margin-bottom: 16px;
        }
        .stat-card {
          background: rgba(22, 33, 62, 0.8);
          border-radius: 12px;
          padding: 16px;
          text-align: center;
        }
        .stat-card.primary {
          background: linear-gradient(135deg, #10b981 0%, #059669 100%);
          grid-column: span 2;
        }
        .stat-card .label {
          font-size: 11px;
          color: #8892b0;
          text-transform: uppercase;
          margin-bottom: 4px;
        }
        .stat-card.primary .label { color: rgba(255,255,255,0.8); }
        .stat-card .value {
          font-size: 24px;
          font-weight: 700;
          color: #e6f1ff;
        }
        .stat-card.primary .value { color: white; }
        .tab-bar {
          display: flex;
          gap: 8px;
          margin-bottom: 16px;
          overflow-x: auto;
          padding-bottom: 8px;
        }
        .tab-btn {
          padding: 8px 16px;
          background: rgba(22, 33, 62, 0.8);
          border: 1px solid rgba(255,255,255,0.1);
          border-radius: 20px;
          color: #8892b0;
          font-size: 13px;
          white-space: nowrap;
          cursor: pointer;
        }
        .tab-btn.active {
          background: #64d2ff;
          border-color: #64d2ff;
          color: #0d1b2a;
          font-weight: 600;
        }
        .section-title {
          font-size: 16px;
          font-weight: 600;
          color: #e6f1ff;
          margin: 20px 0 12px;
        }
      </style>
      ${l.render({title:"EV Coupons",showBack:!0})}
      <div class="mnr-coupons-page">
        <div id="summarySection"></div>
        
        <h3 class="section-title">Coupons</h3>
        <div class="tab-bar" id="tabBar">
          <button class="tab-btn ${this.activeTab==="all"?"active":""}" data-tab="all">All</button>
          <button class="tab-btn ${this.activeTab==="available"?"active":""}" data-tab="available">Available</button>
          <button class="tab-btn ${this.activeTab==="redeemed"?"active":""}" data-tab="redeemed">Redeemed</button>
        </div>
        
        <div id="pageContent"></div>
      </div>
    `,this.attachListeners()}attachListeners(){l.attachListeners({title:"EV Coupons",showBack:!0}),document.querySelectorAll(".tab-btn").forEach(e=>{e.addEventListener("click",()=>{this.activeTab=e.getAttribute("data-tab")||"all",document.querySelectorAll(".tab-btn").forEach(t=>t.classList.remove("active")),e.classList.add("active"),this.updateContent()})})}getFilteredCoupons(){return this.activeTab==="all"?this.coupons:this.activeTab==="available"?this.coupons.filter(e=>e.status.toLowerCase()==="available"||e.status.toLowerCase()==="active"):this.coupons.filter(e=>e.status.toLowerCase()==="redeemed"||e.status.toLowerCase()==="used")}updateContent(){const e=document.getElementById("summarySection");e&&this.stats&&(e.innerHTML=`
        <div class="coupons-summary">
          <div class="stat-card primary">
            <div class="label">Available Coupons</div>
            <div class="value">${this.stats.available_coupons}</div>
          </div>
          <div class="stat-card">
            <div class="label">Total Coupons</div>
            <div class="value">${this.stats.total_coupons}</div>
          </div>
          <div class="stat-card">
            <div class="label">Redeemed</div>
            <div class="value">${this.stats.redeemed_coupons}</div>
          </div>
        </div>
      `);const t=document.getElementById("pageContent");if(!t)return;const a=this.getFilteredCoupons(),i=new m({columns:[{key:"coupon_code",label:"Coupon Code",render:n=>`<strong>${n}</strong>`},{key:"benefit_type",label:"Benefit Type"},{key:"value",label:"Value",render:n=>n>0?`₹${n.toLocaleString()}`:"-"},{key:"status",label:"Status",render:n=>this.getStatusBadge(n)},{key:"created_at",label:"Created",render:n=>this.formatDate(n)},{key:"redeemed_at",label:"Redeemed",render:n=>this.formatDate(n)}],data:a,loading:this.loading,emptyMessage:"No coupons found"});t.innerHTML=i.render()}getStatusBadge(e){const t=e.toLowerCase();return t==="available"||t==="active"?'<span class="badge badge-success">Available</span>':t==="redeemed"||t==="used"?'<span class="badge badge-info">Redeemed</span>':t==="expired"?'<span class="badge badge-danger">Expired</span>':`<span class="badge badge-secondary">${e}</span>`}formatDate(e){if(!e)return"-";try{return new Date(e).toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"numeric"})}catch{return e}}}class ge{container;incomeData=[];loading=!0;selectedMonth="";constructor(e){this.container=e;const t=new Date;this.selectedMonth=`${t.getFullYear()}-${String(t.getMonth()+1).padStart(2,"0")}`}async init(){this.render(),await this.loadIncome()}async loadIncome(){this.loading=!0,this.updateContent();try{const[e,t]=this.selectedMonth.split("-"),a=await d.get(`/users/daywise-income?year=${e}&month=${t}`);a.success&&a.data&&(this.incomeData=a.data.income||a.data||[])}catch(e){console.error("[MNRDaywiseIncome] Failed to load:",e)}this.loading=!1,this.updateContent()}render(){this.container.innerHTML=`
      <div class="page-container">
        ${l.render({title:"📊 Facilitation Summary",showBack:!0})}
        
        <div id="pageContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
    `,l.attachListeners({title:"📊 Facilitation Summary",showBack:!0})}updateContent(){const e=document.getElementById("pageContent");if(!e)return;if(this.loading){e.innerHTML='<div class="loading-state">Loading...</div>';return}const t=this.incomeData.reduce((a,i)=>a+(i.total||0),0);e.innerHTML=`
      <div class="month-selector card">
        <input type="month" id="monthPicker" value="${this.selectedMonth}" class="form-input">
      </div>

      <div class="income-summary card">
        <h3>Total for ${this.getMonthName()}</h3>
        <div class="summary-value">₹${t.toLocaleString()}</div>
      </div>

      <h4 class="section-title">Daily Breakdown</h4>
      ${this.incomeData.length>0?`
        <div class="daywise-list">
          ${this.incomeData.map(a=>this.renderDayCard(a)).join("")}
        </div>
      `:`
        <div class="empty-state card">
          <div class="empty-icon">📊</div>
          <p>No income records for this month</p>
        </div>
      `}
    `,document.getElementById("monthPicker")?.addEventListener("change",a=>{this.selectedMonth=a.target.value,this.loadIncome()})}renderDayCard(e){const t=new Date(e.date),a=t.getDate(),i=t.toLocaleDateString("en",{weekday:"short"});return`
      <div class="day-card card">
        <div class="day-date">
          <span class="day-num">${a}</span>
          <span class="day-name">${i}</span>
        </div>
        <div class="day-breakdown">
          ${e.direct>0?`<div class="income-type"><span>Direct</span><span>₹${e.direct.toLocaleString()}</span></div>`:""}
          ${e.matching>0?`<div class="income-type"><span>Matching</span><span>₹${e.matching.toLocaleString()}</span></div>`:""}
          ${e.ved>0?`<div class="income-type"><span>Ved</span><span>₹${e.ved.toLocaleString()}</span></div>`:""}
          ${e.guru_dakshina>0?`<div class="income-type"><span>Guru</span><span>₹${e.guru_dakshina.toLocaleString()}</span></div>`:""}
        </div>
        <div class="day-total">₹${(e.total||0).toLocaleString()}</div>
      </div>
    `}getMonthName(){const[e,t]=this.selectedMonth.split("-");return new Date(parseInt(e),parseInt(t)-1).toLocaleDateString("en",{month:"long",year:"numeric"})}}class me{container;evModels=[];stats=null;loading=!0;constructor(e){this.container=e}async init(){this.render(),await this.loadData()}async loadData(){this.loading=!0,this.updateContent();try{const[e,t]=await Promise.all([d.get("/ev-discount/ev-models"),d.get("/ev-discount/my-stats")]);e.success&&e.data&&(this.evModels=e.data||[]),t.success&&t.data&&(this.stats={available_discount:t.data.available_discount||0,used_discount:t.data.used_discount||0,pending_redemptions:t.data.pending_redemptions||0})}catch(e){console.error("[MNREVDiscount] Failed to load:",e)}this.loading=!1,this.updateContent()}render(){this.container.innerHTML=`
      <div class="page-container">
        ${l.render({title:"EV Purchase Discount",showBack:!0})}
        
        <div id="pageContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
    `,l.attachListeners({title:"EV Purchase Discount",showBack:!0})}updateContent(){const e=document.getElementById("pageContent");if(e){if(this.loading){e.innerHTML='<div class="loading-state">Loading...</div>';return}e.innerHTML=`
      <div class="ev-hero card">
        <div class="hero-icon">🛵</div>
        <h3>MNR Business Access Program</h3>
        <p>Get up to ₹13,100 discount on EV purchases</p>
      </div>

      <div class="stats-grid">
        <div class="stat-card card">
          <div class="stat-value">₹${(this.stats?.available_discount||0).toLocaleString()}</div>
          <div class="stat-label">Available Discount</div>
        </div>
        <div class="stat-card card">
          <div class="stat-value">${this.stats?.pending_redemptions||0}</div>
          <div class="stat-label">Pending</div>
        </div>
      </div>

      <h4 class="section-title">Available EV Models</h4>
      ${this.evModels.length>0?`
        <div class="ev-models-list">
          ${this.evModels.map(t=>this.renderEVModel(t)).join("")}
        </div>
      `:`
        <div class="empty-state card">
          <div class="empty-icon">🛵</div>
          <p>No EV models available currently</p>
        </div>
      `}

      <div class="notice-card card info">
        <h4>📋 How to Avail</h4>
        <ul>
          <li>Select your preferred EV model</li>
          <li>Visit authorized dealer with MNR ID</li>
          <li>Submit purchase request for approval</li>
          <li>Discount applied at delivery</li>
        </ul>
      </div>

      <div class="notice-card card warning">
        <h4>⚠️ Terms & Conditions</h4>
        <ul>
          <li>Discount valid for activated members only</li>
          <li>One discount per member per category</li>
          <li>Subject to availability and eligibility</li>
          <li>Dealer verification required</li>
        </ul>
      </div>
    `}}renderEVModel(e){return`
      <div class="ev-model-card card ${e.available?"":"unavailable"}">
        <div class="model-image">
          ${e.image_url?`<img src="${e.image_url}" alt="${e.name}">`:"🛵"}
        </div>
        <div class="model-info">
          <h4>${e.name}</h4>
          <p class="model-name">${e.model||""}</p>
          <div class="model-pricing">
            <span class="original-price">₹${e.price.toLocaleString()}</span>
            <span class="discount-badge">-₹${e.discount.toLocaleString()}</span>
          </div>
          <div class="final-price">₹${(e.price-e.discount).toLocaleString()}</div>
        </div>
        ${e.available?`
          <button class="btn btn-primary" onclick="alert('Please visit web portal or contact support to initiate purchase')">
            Enquire
          </button>
        `:`
          <span class="unavailable-badge">Not Available</span>
        `}
      </div>
    `}}class he{container;announcements=[];loading=!0;activeTab="all";constructor(e){this.container=e}async init(){this.render(),await this.loadAnnouncements()}async loadAnnouncements(){this.loading=!0,this.updateContent();try{const e=await d.get("/feedback/my-submissions");e.success&&e.data&&(this.announcements=Array.isArray(e.data)?e.data:[])}catch(e){console.error("[MNRMyAnnouncements] Failed to load:",e)}this.loading=!1,this.updateContent()}getFilteredAnnouncements(){return this.activeTab==="all"?this.announcements:this.announcements.filter(e=>e.status.toLowerCase()===this.activeTab)}render(){this.container.innerHTML=`
      <div class="page-container">
        ${l.render({title:"📋 My Submissions",showBack:!0})}
        
        <div id="pageContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
    `,l.attachListeners({title:"📋 My Submissions",showBack:!0})}updateContent(){const e=document.getElementById("pageContent");if(!e)return;if(this.loading){e.innerHTML='<div class="loading-state">Loading...</div>';return}const t=this.getFilteredAnnouncements(),a={all:this.announcements.length,pending:this.announcements.filter(i=>i.status.toLowerCase()==="pending").length,approved:this.announcements.filter(i=>i.status.toLowerCase()==="approved").length,rejected:this.announcements.filter(i=>i.status.toLowerCase()==="rejected").length};e.innerHTML=`
      <button class="btn btn-primary submit-btn" id="submitNewBtn">
        + Submit New Announcement
      </button>

      <div class="announcement-tabs">
        <button class="tab ${this.activeTab==="all"?"active":""}" data-tab="all">All (${a.all})</button>
        <button class="tab ${this.activeTab==="pending"?"active":""}" data-tab="pending">Pending (${a.pending})</button>
        <button class="tab ${this.activeTab==="approved"?"active":""}" data-tab="approved">Approved (${a.approved})</button>
        <button class="tab ${this.activeTab==="rejected"?"active":""}" data-tab="rejected">Rejected (${a.rejected})</button>
      </div>

      ${t.length>0?`
        <div class="announcements-list">
          ${t.map(i=>this.renderSubmissionCard(i)).join("")}
        </div>
      `:`
        <div class="empty-state card">
          <div class="empty-icon">📢</div>
          <p>No ${this.activeTab==="all"?"":this.activeTab} announcements</p>
        </div>
      `}
    `,this.attachListeners()}renderSubmissionCard(e){const t=e.status.toLowerCase(),a=e.category?.name||e.category?.category_name||"General",i=e.media?.length||0;return`
      <div class="announcement-card card ${t}">
        <div class="ann-header">
          <h4>${e.title}</h4>
          <span class="status-badge ${t}">${this.formatStatus(e.status)}</span>
        </div>
        
        <div class="ann-category">
          <span class="category-tag">${a}</span>
        </div>
        
        <p class="ann-description">${e.description||""}</p>
        
        ${this.renderMediaThumbnails(e.media)}
        
        <div class="ann-meta">
          <span>📅 ${this.formatDate(e.submitted_at)}</span>
          <span>📁 ${i} file(s)</span>
        </div>
        
        ${e.status.toLowerCase()==="approved"&&e.approved_at?`
          <div class="approval-info">
            ✅ Approved: ${this.formatDate(e.approved_at)}
          </div>
        `:""}
      </div>
    `}renderMediaThumbnails(e){if(!e||e.length===0)return"";const t=e.slice(0,4),a=e.length>4?e.length-4:0;return`
      <div class="media-thumbnails">
        ${t.map((i,n)=>`
          <div class="thumb ${i.media_type==="video"?"video":"image"}">
            ${i.media_type==="video"?'<span class="play-icon">▶</span>':`<img src="${d.getMediaUrl(i.file_path)}" alt="Media ${n+1}" loading="lazy" onerror="this.style.display='none'" />`}
            ${i.media_status!=="approved"?`<span class="media-status ${i.media_status}">${i.media_status}</span>`:""}
          </div>
        `).join("")}
        ${a>0?`<div class="thumb more">+${a}</div>`:""}
      </div>
    `}formatStatus(e){return{pending:"Pending Review",under_review:"Under Review",approved:"Approved",rejected:"Rejected",partially_approved:"Partially Approved"}[e.toLowerCase()]||e}attachListeners(){document.getElementById("submitNewBtn")?.addEventListener("click",()=>{f.navigate("mnr-create-announcement")}),document.querySelectorAll(".announcement-tabs .tab").forEach(e=>{e.addEventListener("click",()=>{this.activeTab=e.getAttribute("data-tab"),this.updateContent()})})}formatDate(e){if(!e)return"N/A";try{return new Date(e).toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"numeric",hour:"2-digit",minute:"2-digit"})}catch{return e}}}class be{container;leads=[];stats={my_leads:0,assigned_leads:0,fresh_leads:0,won_deals:0};loading=!0;activeTab="my";searchQuery="";statusFilter="";priorityFilter="";dateFilter="";roleFilter="";searchTimeout=null;companies=[];selectedCompanyId=null;constructor(e){this.container=e}async init(){this.render(),await this.loadCompanies(),await this.loadData()}async loadCompanies(){try{const e=await d.get("/crm/my-companies");e.success&&e.data?this.companies=e.data:this.companies=[{id:1,name:"MNR"},{id:2,name:"MyntReal"},{id:3,name:"VGK Care"}]}catch(e){console.error("[MNRMyLeads] Failed to load companies:",e),this.companies=[{id:1,name:"MNR"},{id:2,name:"MyntReal"},{id:3,name:"VGK Care"}]}}async lookupPincode(e){const t=e.value.trim();if(!(!t||t.length!==6))try{const i=await(await fetch(`https://api.postalpincode.in/pincode/${t}`)).json();if(i[0]?.Status==="Success"&&i[0]?.PostOffice?.length>0){const n=i[0].PostOffice[0],s=document.getElementById("leadArea"),r=document.getElementById("leadCity"),o=document.getElementById("leadState");s&&(s.value=n.Name||""),r&&(r.value=n.District||""),o&&(o.value=n.State||"")}}catch(a){console.error("[MNRMyLeads] Pincode lookup failed:",a)}}async loadData(){this.loading=!0,this.updateContent();try{await Promise.all([this.loadStats(),this.loadLeads()])}catch(e){console.error("[MNRMyLeads] Failed to load:",e)}this.loading=!1,this.updateContent()}async loadStats(){try{const[e,t]=await Promise.all([d.get("/crm/unified-my-leads?segment=my&role=mnr"),d.get("/crm/unified-my-leads?segment=assigned&role=mnr")]),a=e.success?e.data?.leads||e.data||[]:[],i=t.success?t.data?.leads||t.data||[]:[];this.stats={my_leads:a.length,assigned_leads:i.length,fresh_leads:0,won_deals:a.filter(n=>n.status?.toLowerCase()==="won").length}}catch(e){console.error("[MNRMyLeads] Stats load failed:",e)}}async loadLeads(){try{const e=new URLSearchParams;e.append("segment",this.activeTab),e.append("role","mnr"),this.selectedCompanyId&&e.append("company_id",this.selectedCompanyId.toString()),this.searchQuery&&e.append("search",this.searchQuery),this.statusFilter&&e.append("status",this.statusFilter),this.priorityFilter&&e.append("priority",this.priorityFilter),this.dateFilter&&e.append("quick_filter",this.dateFilter),this.roleFilter&&e.append("role_filter",this.roleFilter);const t=await d.get(`/crm/unified-my-leads?${e.toString()}`);if(t.success&&t.data){const a=t.data.leads||t.data||[];this.leads=a.map(i=>({id:i.id,name:i.name||i.lead_name||"",phone:i.phone||i.mobile||"",phone_primary_whatsapp:i.phone_primary_whatsapp||!1,alternate_phone:i.alternate_phone||"",email:i.email||"",category:i.category||i.category_id||"",category_name:i.category_name||i.category||"General",company:i.company||i.company_name||"",status:i.status||"new",priority:i.priority||"medium",created_at:i.created_at||"",updated_at:i.updated_at||i.last_updated||"",last_activity:i.last_activity||i.last_followup_date||null,next_followup_date:i.next_followup_date||null,notes:i.notes||i.description||i.remarks||null,source:i.source||"Direct",requirements:i.requirements||"",looking_for:i.looking_for||"",budget_min:i.budget_min||null,budget_max:i.budget_max||null,address:i.address||"",area:i.area||"",city:i.city||"",state:i.state||"",pincode:i.pincode||""}))}}catch(e){console.error("[MNRMyLeads] Leads load failed:",e)}}render(){this.container.innerHTML=`
      <style>
        .leads-page .lead-card { background: rgba(30, 58, 95, 0.5); border-radius: 12px; padding: 14px; margin-bottom: 12px; cursor: pointer; }
        .leads-page .lead-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px; }
        .leads-page .lead-info { flex: 1; }
        .leads-page .lead-name { font-size: 16px; font-weight: 600; color: #e6f1ff; margin: 0 0 4px 0; }
        .leads-page .lead-contact-row { display: flex; align-items: center; gap: 8px; }
        .leads-page .lead-phone-link { color: #10b981; font-size: 14px; text-decoration: none; }
        .leads-page .lead-phone-link:hover { text-decoration: underline; }
        .leads-page .whatsapp-link { color: #25d366; font-size: 16px; text-decoration: none; }
        .leads-page .lead-meta { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-bottom: 12px; font-size: 12px; color: #a8c0d8; }
        .leads-page .meta-item { background: rgba(255,255,255,0.05); padding: 3px 8px; border-radius: 6px; }
        .leads-page .meta-item.category { color: #60a5fa; }
        .leads-page .meta-item.date { color: #9ca3af; }
        .leads-page .lead-actions { display: flex; gap: 8px; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 12px; }
        .leads-page .action-btn { flex: 1; display: flex; align-items: center; justify-content: center; gap: 4px; padding: 10px 8px; border-radius: 8px; font-size: 14px; font-weight: 500; text-decoration: none; border: none; cursor: pointer; }
        .leads-page .action-btn.call { background: rgba(16, 185, 129, 0.15); color: #10b981; }
        .leads-page .action-btn.whatsapp { background: rgba(37, 211, 102, 0.15); color: #25d366; }
        .leads-page .action-btn.view { background: rgba(96, 165, 250, 0.15); color: #60a5fa; }
        .leads-page .action-btn.edit { background: rgba(251, 191, 36, 0.15); color: #fbbf24; }
        .leads-page .status-badge { padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; text-transform: capitalize; }
        .leads-page .status-badge.new { background: rgba(96, 165, 250, 0.2); color: #60a5fa; }
        .leads-page .status-badge.contacted { background: rgba(251, 191, 36, 0.2); color: #fbbf24; }
        .leads-page .status-badge.interested { background: rgba(16, 185, 129, 0.2); color: #10b981; }
        .leads-page .status-badge.negotiation { background: rgba(168, 85, 247, 0.2); color: #a855f7; }
        .leads-page .status-badge.won { background: rgba(34, 197, 94, 0.2); color: #22c55e; }
        .leads-page .status-badge.lost { background: rgba(239, 68, 68, 0.2); color: #ef4444; }
        .leads-page .priority-badge { padding: 2px 8px; border-radius: 6px; font-size: 11px; font-weight: 600; text-transform: capitalize; }
        .leads-page .priority-badge.high { background: rgba(239, 68, 68, 0.2); color: #ef4444; }
        .leads-page .priority-badge.medium { background: rgba(251, 191, 36, 0.2); color: #fbbf24; }
        .leads-page .priority-badge.low { background: rgba(107, 114, 128, 0.2); color: #9ca3af; }
        .leads-page .filter-row { display: flex; gap: 8px; margin-top: 10px; }
        .leads-page .filter-select { flex: 1; padding: 10px 12px; background: rgba(30, 58, 95, 0.6); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; color: #e6f1ff; font-size: 13px; }
      </style>
      <div class="page-container leads-page">
        ${l.render({title:"My Leads",showBack:!0})}
        
        <div id="pageContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
    `,l.attachListeners({title:"My Leads",showBack:!0});const e=document.getElementById("btnAddLead");e&&e.addEventListener("click",()=>this.showAddLeadModal())}updateContent(){const e=document.getElementById("pageContent");if(e){if(this.loading){e.innerHTML='<div class="loading-state">Loading...</div>';return}e.innerHTML=`
      <style>
        .stats-row { display: flex; gap: 8px; margin-bottom: 16px; padding: 0 4px; }
        .stats-row .stat-item { flex: 1; display: flex; align-items: center; gap: 8px; background: linear-gradient(135deg, rgba(30, 58, 95, 0.8) 0%, rgba(13, 27, 42, 0.9) 100%); padding: 12px 14px; border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.08); }
        .stats-row .stat-item .stat-value { font-size: 22px; font-weight: 700; color: #10b981; min-width: 24px; }
        .stats-row .stat-item .stat-label { font-size: 11px; color: #a8c0d8; text-transform: uppercase; letter-spacing: 0.5px; }
        .stats-row .stat-item.active { border-color: #10b981; background: linear-gradient(135deg, rgba(16, 185, 129, 0.15) 0%, rgba(4, 120, 87, 0.15) 100%); }
        .company-filter-row { margin-bottom: 12px; }
        .company-filter-row select { width: 100%; padding: 12px 14px; background: rgba(30, 58, 95, 0.6); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 10px; color: #e6f1ff; font-size: 14px; }
      </style>
      
      <div class="stats-row">
        <div class="stat-item ${this.activeTab==="my"?"active":""}" data-tab="my">
          <span class="stat-value">${this.stats.my_leads}</span>
          <span class="stat-label">Total</span>
        </div>
        <div class="stat-item" style="cursor: default;">
          <span class="stat-value" style="color: #22c55e;">${this.stats.won_deals}</span>
          <span class="stat-label">Converted</span>
        </div>
        <div class="stat-item ${this.activeTab==="assigned"?"active":""}" data-tab="assigned">
          <span class="stat-value" style="color: #60a5fa;">${this.stats.assigned_leads}</span>
          <span class="stat-label">Active</span>
        </div>
      </div>

      <div class="company-filter-row">
        <select id="companyFilter" class="filter-select">
          <option value="">All Companies</option>
          ${this.companies.map(t=>`<option value="${t.id}" ${this.selectedCompanyId===t.id?"selected":""}>${t.name}</option>`).join("")}
        </select>
      </div>

      <div class="tabs-container">
        <button class="tab-btn ${this.activeTab==="my"?"active":""}" data-tab="my">
          <span class="tab-icon">📋</span> My Leads
        </button>
        <button class="tab-btn ${this.activeTab==="assigned"?"active":""}" data-tab="assigned">
          <span class="tab-icon">👤</span> Assigned
        </button>
      </div>

      <div class="filters-section">
        <div class="search-box">
          <span class="search-icon">🔍</span>
          <input type="text" id="leadSearch" placeholder="Search leads..." value="${this.searchQuery}">
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
        <div class="filter-row">
          <select id="statusFilter" class="filter-select">
            <option value="">All Status</option>
            <option value="new" ${this.statusFilter==="new"?"selected":""}>New</option>
            <option value="contacted" ${this.statusFilter==="contacted"?"selected":""}>Contacted</option>
            <option value="interested" ${this.statusFilter==="interested"?"selected":""}>Interested</option>
            <option value="negotiation" ${this.statusFilter==="negotiation"?"selected":""}>Negotiation</option>
            <option value="won" ${this.statusFilter==="won"?"selected":""}>Won</option>
            <option value="lost" ${this.statusFilter==="lost"?"selected":""}>Lost</option>
          </select>
        </div>
      </div>

      <div class="leads-list">
        ${this.leads.length===0?`
          <div class="empty-state card">
            <div class="empty-icon">👥</div>
            <h3>No leads found</h3>
            <p>${this.getEmptyMessage()}</p>
            ${this.activeTab==="my"?`
              <button class="btn-primary" id="btnAddLeadEmpty">+ Add Lead</button>
            `:""}
          </div>
        `:this.leads.map(t=>this.renderLeadCard(t)).join("")}
      </div>
    `,this.attachEventListeners()}}renderLeadCard(e){const t=e.status.toLowerCase().replace(/\s+/g,"-"),a=e.priority.toLowerCase(),i=this.formatDate(e.updated_at||e.created_at),n=e.phone||"",s=n.replace(/\D/g,"");return`
      <div class="lead-card card" data-lead-id="${e.id}">
        <div class="lead-header" data-action="view" data-id="${e.id}">
          <div class="lead-info">
            <h4 class="lead-name">${e.name}</h4>
            <div class="lead-contact-row">
              <a href="tel:${n}" class="lead-phone-link" onclick="event.stopPropagation()">${n||"No phone"}</a>
              ${n?`<a href="https://wa.me/91${s}" class="whatsapp-link" target="_blank" onclick="event.stopPropagation()">💬</a>`:""}
            </div>
          </div>
          <span class="status-badge ${t}">${e.status}</span>
        </div>
        <div class="lead-meta" data-action="view" data-id="${e.id}">
          <span class="meta-item category">${e.category_name||"General"}</span>
          <span class="priority-badge ${a}">${e.priority}</span>
          <span class="meta-item date">${i}</span>
          ${e.submit_date?`<span class="meta-item" style="font-size:10px;color:#6b7280">📤 ${this.formatDate(e.submit_date)}</span>`:""}
          ${e.complete_date?`<span class="meta-item" style="font-size:10px;color:#059669">✅ ${this.formatDate(e.complete_date)}</span>`:""}
        </div>
        <div class="lead-actions">
          <a href="tel:${n}" class="action-btn call" onclick="event.stopPropagation()">
            <span>📞</span>
          </a>
          <a href="https://wa.me/91${s}" class="action-btn whatsapp" target="_blank" onclick="event.stopPropagation()">
            <span>💬</span>
          </a>
          <button class="action-btn view" data-action="view" data-id="${e.id}">
            <span>👁</span>
          </button>
          <button class="action-btn edit" data-action="edit" data-id="${e.id}">
            <span>✏️</span>
          </button>
        </div>
      </div>
    `}attachEventListeners(){document.querySelectorAll(".tab-btn").forEach(o=>{o.addEventListener("click",()=>{this.activeTab=o.getAttribute("data-tab"),this.loadLeads().then(()=>this.updateContent())})}),document.querySelectorAll(".stat-item[data-tab]").forEach(o=>{o.addEventListener("click",()=>{const c=o.getAttribute("data-tab");c&&(this.activeTab=c,this.loadLeads().then(()=>this.updateContent()))})});const e=document.getElementById("companyFilter");e&&e.addEventListener("change",()=>{this.selectedCompanyId=e.value?parseInt(e.value):null,this.loadLeads().then(()=>this.updateContent())});const t=document.getElementById("leadSearch");t&&t.addEventListener("input",()=>{this.searchTimeout&&clearTimeout(this.searchTimeout),this.searchTimeout=window.setTimeout(()=>{this.searchQuery=t.value,this.loadLeads().then(()=>this.updateContent())},300)});const a=document.getElementById("statusFilter");a&&a.addEventListener("change",()=>{this.statusFilter=a.value,this.loadLeads().then(()=>this.updateContent())});const i=document.getElementById("priorityFilter");i&&i.addEventListener("change",()=>{this.priorityFilter=i.value,this.loadLeads().then(()=>this.updateContent())});const n=document.getElementById("dateFilter");n&&n.addEventListener("change",()=>{this.dateFilter=n.value,this.loadLeads().then(()=>this.updateContent())});const s=document.getElementById("roleFilter");s&&s.addEventListener("change",()=>{this.roleFilter=s.value,this.loadLeads().then(()=>this.updateContent())}),document.querySelectorAll(".lead-card").forEach(o=>{o.addEventListener("click",c=>{const p=c.target;if(p.closest("a")||p.closest(".action-btn"))return;const g=o.getAttribute("data-lead-id");g&&this.viewLeadDetails(parseInt(g))})}),document.querySelectorAll(".action-btn").forEach(o=>{o.addEventListener("click",c=>{c.stopPropagation();const p=o.getAttribute("data-action"),g=o.getAttribute("data-id");p==="view"&&g?this.viewLeadDetails(parseInt(g)):p==="edit"&&g&&this.showEditLeadModal(parseInt(g))})});const r=document.getElementById("btnAddLeadEmpty");r&&r.addEventListener("click",()=>this.showAddLeadModal())}getEmptyMessage(){switch(this.activeTab){case"my":return"Add your first lead to get started";case"assigned":return"No leads have been assigned to you";default:return"No leads found"}}async showAddLeadModal(){const e=document.createElement("div");e.className="modal-overlay",e.id="addLeadModal",e.innerHTML=`
      <style>
        #addLeadModal {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0, 0, 0, 0.7);
          backdrop-filter: blur(4px);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 9999;
          padding: 16px;
        }
        #addLeadModal .modal-content {
          max-height: 90vh;
          width: 100%;
          max-width: 420px;
          background: linear-gradient(180deg, #1e3a5f 0%, #0d1b2a 100%);
          border-radius: 20px;
          display: flex;
          flex-direction: column;
          box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(255, 255, 255, 0.1);
          animation: slideUp 0.3s ease-out;
        }
        @keyframes slideUp {
          from { transform: translateY(30px); opacity: 0; }
          to { transform: translateY(0); opacity: 1; }
        }
        #addLeadModal .modal-header {
          background: linear-gradient(135deg, #10b981 0%, #047857 100%);
          padding: 20px 24px;
          border-radius: 20px 20px 0 0;
          display: flex;
          justify-content: space-between;
          align-items: center;
          position: relative;
          overflow: hidden;
        }
        #addLeadModal .modal-header::before {
          content: '';
          position: absolute;
          top: -50%;
          right: -20%;
          width: 100px;
          height: 100px;
          background: rgba(255, 255, 255, 0.1);
          border-radius: 50%;
        }
        #addLeadModal .modal-header h3 {
          margin: 0;
          color: white;
          font-size: 20px;
          font-weight: 700;
          display: flex;
          align-items: center;
          gap: 10px;
          position: relative;
          z-index: 1;
        }
        #addLeadModal .modal-header h3 .icon {
          width: 36px;
          height: 36px;
          background: rgba(255, 255, 255, 0.2);
          border-radius: 10px;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 18px;
        }
        #addLeadModal .modal-close {
          background: rgba(255, 255, 255, 0.2);
          border: none;
          color: white;
          width: 36px;
          height: 36px;
          border-radius: 10px;
          font-size: 22px;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all 0.2s;
          position: relative;
          z-index: 1;
        }
        #addLeadModal .modal-close:hover {
          background: rgba(255, 255, 255, 0.3);
          transform: scale(1.05);
        }
        #addLeadModal .modal-body {
          padding: 24px;
          overflow-y: auto;
          flex: 1;
          max-height: calc(90vh - 180px);
        }
        #addLeadModal .modal-body::-webkit-scrollbar {
          width: 6px;
        }
        #addLeadModal .modal-body::-webkit-scrollbar-track {
          background: rgba(255, 255, 255, 0.05);
          border-radius: 3px;
        }
        #addLeadModal .modal-body::-webkit-scrollbar-thumb {
          background: rgba(16, 185, 129, 0.5);
          border-radius: 3px;
        }
        #addLeadModal .form-section {
          margin-bottom: 20px;
        }
        #addLeadModal .section-title {
          font-size: 12px;
          font-weight: 600;
          color: #10b981;
          text-transform: uppercase;
          letter-spacing: 1px;
          margin-bottom: 12px;
          padding-bottom: 8px;
          border-bottom: 1px solid rgba(16, 185, 129, 0.2);
          display: flex;
          align-items: center;
          gap: 8px;
        }
        #addLeadModal .form-row {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 14px;
        }
        #addLeadModal .form-group {
          margin-bottom: 16px;
        }
        #addLeadModal .form-group.full-width {
          grid-column: 1 / -1;
        }
        #addLeadModal .form-group label {
          display: flex;
          align-items: center;
          gap: 6px;
          color: #a8c0d8;
          font-size: 13px;
          font-weight: 500;
          margin-bottom: 8px;
        }
        #addLeadModal .form-group label .field-icon {
          font-size: 14px;
          opacity: 0.8;
        }
        #addLeadModal .form-group label .required {
          color: #f87171;
          font-weight: bold;
        }
        #addLeadModal .input-wrapper {
          position: relative;
        }
        #addLeadModal .form-group input,
        #addLeadModal .form-group select,
        #addLeadModal .form-group textarea {
          width: 100%;
          padding: 14px 16px;
          border-radius: 12px;
          border: 2px solid rgba(255, 255, 255, 0.08);
          background: rgba(13, 27, 42, 0.6);
          color: #e6f1ff;
          font-size: 15px;
          transition: all 0.2s;
          box-sizing: border-box;
        }
        #addLeadModal .form-group input::placeholder,
        #addLeadModal .form-group textarea::placeholder {
          color: rgba(168, 192, 216, 0.5);
        }
        #addLeadModal .form-group input:focus,
        #addLeadModal .form-group select:focus,
        #addLeadModal .form-group textarea:focus {
          outline: none;
          border-color: #10b981;
          background: rgba(16, 185, 129, 0.08);
          box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.15);
        }
        #addLeadModal .form-group select {
          appearance: none;
          background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%2310b981' d='M6 8L1 3h10z'/%3E%3C/svg%3E");
          background-repeat: no-repeat;
          background-position: right 14px center;
          padding-right: 40px;
          cursor: pointer;
        }
        #addLeadModal .form-group select option {
          background: #1e3a5f;
          color: #e6f1ff;
          padding: 10px;
        }
        #addLeadModal .checkbox-row {
          display: flex;
          align-items: center;
          gap: 10px;
          margin-top: 10px;
          padding: 10px 14px;
          background: rgba(16, 185, 129, 0.08);
          border-radius: 8px;
          border: 1px solid rgba(16, 185, 129, 0.2);
        }
        #addLeadModal .checkbox-row input[type="checkbox"] {
          width: 20px;
          height: 20px;
          accent-color: #10b981;
          cursor: pointer;
        }
        #addLeadModal .checkbox-row label {
          color: #a8c0d8;
          font-size: 13px;
          margin: 0;
          cursor: pointer;
          display: flex;
          align-items: center;
          gap: 6px;
        }
        #addLeadModal .checkbox-row label .whatsapp-icon {
          color: #25D366;
        }
        #addLeadModal .form-group textarea {
          resize: vertical;
          min-height: 80px;
        }
        #addLeadModal .modal-footer {
          padding: 20px 24px;
          border-top: 1px solid rgba(255, 255, 255, 0.08);
          display: flex;
          gap: 12px;
          justify-content: stretch;
          flex-shrink: 0;
          background: rgba(13, 27, 42, 0.5);
          border-radius: 0 0 20px 20px;
        }
        #addLeadModal .btn-cancel {
          flex: 1;
          padding: 16px 20px;
          background: rgba(255, 255, 255, 0.08);
          border: 2px solid rgba(255, 255, 255, 0.15);
          color: #a8c0d8;
          border-radius: 12px;
          font-size: 15px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s;
        }
        #addLeadModal .btn-cancel:hover {
          background: rgba(255, 255, 255, 0.12);
          border-color: rgba(255, 255, 255, 0.25);
        }
        #addLeadModal .btn-submit {
          flex: 1.5;
          padding: 16px 20px;
          background: linear-gradient(135deg, #10b981 0%, #047857 100%);
          border: none;
          color: white;
          border-radius: 12px;
          font-size: 15px;
          font-weight: 700;
          cursor: pointer;
          transition: all 0.2s;
          box-shadow: 0 4px 15px rgba(16, 185, 129, 0.35);
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
        }
        #addLeadModal .btn-submit:hover {
          transform: translateY(-2px);
          box-shadow: 0 6px 20px rgba(16, 185, 129, 0.45);
        }
        #addLeadModal .btn-submit:disabled {
          opacity: 0.6;
          cursor: not-allowed;
          transform: none;
          box-shadow: none;
        }
        #addLeadModal .priority-options {
          display: flex;
          gap: 10px;
        }
        #addLeadModal .priority-option {
          flex: 1;
          padding: 12px;
          border-radius: 10px;
          border: 2px solid rgba(255, 255, 255, 0.1);
          background: rgba(13, 27, 42, 0.4);
          cursor: pointer;
          text-align: center;
          transition: all 0.2s;
        }
        #addLeadModal .priority-option:hover {
          border-color: rgba(255, 255, 255, 0.2);
        }
        #addLeadModal .priority-option.selected {
          border-color: var(--priority-color);
          background: var(--priority-bg);
        }
        #addLeadModal .priority-option.high { --priority-color: #ef4444; --priority-bg: rgba(239, 68, 68, 0.15); }
        #addLeadModal .priority-option.medium { --priority-color: #f59e0b; --priority-bg: rgba(245, 158, 11, 0.15); }
        #addLeadModal .priority-option.low { --priority-color: #10b981; --priority-bg: rgba(16, 185, 129, 0.15); }
        #addLeadModal .priority-option .priority-dot {
          width: 10px;
          height: 10px;
          border-radius: 50%;
          margin: 0 auto 6px;
        }
        #addLeadModal .priority-option.high .priority-dot { background: #ef4444; }
        #addLeadModal .priority-option.medium .priority-dot { background: #f59e0b; }
        #addLeadModal .priority-option.low .priority-dot { background: #10b981; }
        #addLeadModal .priority-option .priority-label {
          font-size: 13px;
          font-weight: 600;
          color: #a8c0d8;
        }
        #addLeadModal .priority-option.selected .priority-label {
          color: var(--priority-color);
        }
      </style>
      <div class="modal-content">
        <div class="modal-header">
          <h3><span class="icon">+</span> Add New Lead</h3>
          <button class="modal-close">&times;</button>
        </div>
        <div class="modal-body">
          <div class="form-section">
            <div class="section-title"><span>1</span> Basic Information</div>
            <div class="form-row">
              <div class="form-group">
                <label><span class="field-icon">*</span> Name <span class="required">*</span></label>
                <input type="text" id="leadName" placeholder="Full name" required>
              </div>
              <div class="form-group">
                <label><span class="field-icon">@</span> Email</label>
                <input type="email" id="leadEmail" placeholder="email@example.com">
              </div>
            </div>
          </div>

          <div class="form-section">
            <div class="section-title"><span>2</span> Contact Details</div>
            <div class="form-group">
              <label><span class="field-icon">#</span> Mobile Number <span class="required">*</span></label>
              <input type="tel" id="leadMobile" placeholder="10-digit mobile number" required maxlength="10" inputmode="numeric">
              <div class="checkbox-row">
                <input type="checkbox" id="leadPhoneWhatsapp" checked>
                <label for="leadPhoneWhatsapp"><span class="whatsapp-icon">W</span> WhatsApp Available</label>
              </div>
            </div>
            <div class="form-group">
              <label><span class="field-icon">#</span> Alternate Mobile</label>
              <input type="tel" id="leadMobileSecondary" placeholder="Alternate number (optional)" maxlength="10" inputmode="numeric">
              <div class="checkbox-row">
                <input type="checkbox" id="leadPhoneSecondaryWhatsapp">
                <label for="leadPhoneSecondaryWhatsapp"><span class="whatsapp-icon">W</span> WhatsApp Available</label>
              </div>
            </div>
          </div>

          <div class="form-section">
            <div class="section-title"><span>3</span> Lead Classification</div>
            <div class="form-row">
              <div class="form-group">
                <label><span class="field-icon">B</span> Company <span class="required">*</span></label>
                <select id="leadCompany" required>
                  <option value="">Select company...</option>
                  ${this.companies.map(i=>`<option value="${i.id}">${i.name}</option>`).join("")}
                </select>
              </div>
              <div class="form-group">
                <label><span class="field-icon">T</span> Category</label>
                <select id="leadCategory">
                  <option value="">Select category...</option>
                  <option value="ev">EV</option>
                  <option value="real_estate">Real Estate</option>
                  <option value="insurance">Insurance</option>
                  <option value="franchise">Franchise</option>
                  <option value="solar">Solar</option>
                  <option value="general">General</option>
                </select>
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label><span class="field-icon">S</span> Lead Source</label>
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
              <div class="form-group">
                <label><span class="field-icon">!</span> Priority</label>
                <select id="leadPriority">
                  <option value="medium">Normal</option>
                  <option value="high">High</option>
                  <option value="low">Low</option>
                </select>
              </div>
            </div>
          </div>

          <div class="form-section">
            <div class="section-title"><span>4</span> Requirements & Budget</div>
            <div class="form-group">
              <label><span class="field-icon">L</span> Looking For</label>
              <input type="text" id="leadLookingFor" placeholder="What is the lead looking for?">
            </div>
            <div class="form-group">
              <label><span class="field-icon">R</span> Requirements</label>
              <textarea id="leadRequirements" placeholder="Detailed requirements..." rows="2"></textarea>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label><span class="field-icon">₹</span> Budget Min</label>
                <input type="number" id="leadBudgetMin" placeholder="Min budget" inputmode="numeric">
              </div>
              <div class="form-group">
                <label><span class="field-icon">₹</span> Budget Max</label>
                <input type="number" id="leadBudgetMax" placeholder="Max budget" inputmode="numeric">
              </div>
            </div>
          </div>

          <div class="form-section">
            <div class="section-title"><span>5</span> Location Details</div>
            <div class="form-group">
              <label><span class="field-icon">#</span> Pincode <span style="font-size:10px;color:#10b981;">(Auto-detect)</span></label>
              <div style="display:flex;gap:8px;">
                <input type="text" id="leadPincode" placeholder="6-digit PIN" maxlength="6" inputmode="numeric" style="flex:1;">
                <button type="button" id="btnLookupPincode" style="padding:10px 14px;background:rgba(16,185,129,0.2);border:1px solid #10b981;color:#10b981;border-radius:10px;font-size:12px;cursor:pointer;">Lookup</button>
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label><span class="field-icon">A</span> Area</label>
                <input type="text" id="leadArea" placeholder="Area/Locality">
              </div>
              <div class="form-group">
                <label><span class="field-icon">C</span> City</label>
                <input type="text" id="leadCity" placeholder="City">
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label><span class="field-icon">S</span> State</label>
                <input type="text" id="leadState" placeholder="State">
              </div>
              <div class="form-group">
                <label><span class="field-icon">P</span> Address</label>
                <input type="text" id="leadAddress" placeholder="Street address">
              </div>
            </div>
          </div>

          <div class="form-section">
            <div class="section-title"><span>6</span> Follow-up & Notes</div>
            <div class="form-row">
              <div class="form-group">
                <label><span class="field-icon">D</span> Expected Close Date</label>
                <input type="date" id="leadExpectedCloseDate">
              </div>
              <div class="form-group">
                <label><span class="field-icon">F</span> Next Follow-up</label>
                <input type="date" id="leadNextFollowupDate">
              </div>
            </div>
            <div class="form-group">
              <label><span class="field-icon">T</span> Tags</label>
              <input type="text" id="leadTags" placeholder="Comma separated tags">
            </div>
            <div class="form-group">
              <label><span class="field-icon">N</span> Notes</label>
              <textarea id="leadNotes" placeholder="Additional notes or requirements..." rows="3"></textarea>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-cancel" id="btnCancelLead">Cancel</button>
          <button class="btn-submit" id="btnSaveLead"><span>+</span> Create Lead</button>
        </div>
      </div>
    `,document.body.appendChild(e),this.applyModalStyles(e),e.querySelector(".modal-close")?.addEventListener("click",()=>e.remove()),e.querySelector("#btnCancelLead")?.addEventListener("click",()=>e.remove()),e.querySelector("#btnSaveLead")?.addEventListener("click",()=>this.saveLead(e)),e.addEventListener("click",i=>{i.target===e&&e.remove()});const t=e.querySelector("#leadPincode"),a=e.querySelector("#btnLookupPincode");t&&(a&&a.addEventListener("click",()=>this.lookupPincode(t)),t.addEventListener("input",()=>{t.value.length===6&&this.lookupPincode(t)}))}applyModalStyles(e){Object.assign(e.style,{position:"fixed",top:"0",left:"0",right:"0",bottom:"0",background:"rgba(0, 0, 0, 0.7)",backdropFilter:"blur(4px)",display:"flex",alignItems:"center",justifyContent:"center",zIndex:"9999",padding:"16px"});const t=e.querySelector(".modal-content");t&&Object.assign(t.style,{maxHeight:"90vh",width:"100%",maxWidth:"420px",background:"linear-gradient(180deg, #1e3a5f 0%, #0d1b2a 100%)",borderRadius:"20px",padding:"0",display:"flex",flexDirection:"column",boxShadow:"0 20px 60px rgba(0, 0, 0, 0.5)"});const a=e.querySelector(".modal-header");a&&Object.assign(a.style,{background:"linear-gradient(135deg, #10b981 0%, #047857 100%)",padding:"20px 24px",borderRadius:"20px 20px 0 0",display:"flex",justifyContent:"space-between",alignItems:"center"});const i=e.querySelector(".modal-header h3");i&&Object.assign(i.style,{margin:"0",color:"white",fontSize:"20px",fontWeight:"700",display:"flex",alignItems:"center",gap:"10px"});const n=e.querySelector(".modal-close");n&&Object.assign(n.style,{background:"rgba(255, 255, 255, 0.2)",border:"none",color:"white",width:"36px",height:"36px",borderRadius:"10px",fontSize:"22px",cursor:"pointer",display:"flex",alignItems:"center",justifyContent:"center"});const s=e.querySelector(".modal-body");s&&Object.assign(s.style,{padding:"24px",overflowY:"auto",flex:"1",maxHeight:"calc(90vh - 180px)"}),e.querySelectorAll(".section-title").forEach(p=>{Object.assign(p.style,{fontSize:"12px",fontWeight:"600",color:"#10b981",textTransform:"uppercase",letterSpacing:"1px",marginBottom:"12px",paddingBottom:"8px",borderBottom:"1px solid rgba(16, 185, 129, 0.2)"})}),e.querySelectorAll(".form-group").forEach(p=>{Object.assign(p.style,{marginBottom:"16px"})}),e.querySelectorAll(".form-group label").forEach(p=>{Object.assign(p.style,{display:"flex",alignItems:"center",gap:"6px",color:"#a8c0d8",fontSize:"13px",fontWeight:"500",marginBottom:"8px"})}),e.querySelectorAll("input, select, textarea").forEach(p=>{Object.assign(p.style,{width:"100%",padding:"14px 16px",borderRadius:"12px",border:"2px solid rgba(255, 255, 255, 0.08)",background:"rgba(13, 27, 42, 0.6)",color:"#e6f1ff",fontSize:"15px",boxSizing:"border-box"})}),e.querySelectorAll(".form-row").forEach(p=>{Object.assign(p.style,{display:"grid",gridTemplateColumns:"1fr 1fr",gap:"14px"})});const r=e.querySelector(".modal-footer");r&&Object.assign(r.style,{padding:"20px 24px",borderTop:"1px solid rgba(255, 255, 255, 0.08)",display:"flex",gap:"12px",background:"rgba(13, 27, 42, 0.5)",borderRadius:"0 0 20px 20px"});const o=e.querySelector(".btn-cancel");o&&Object.assign(o.style,{flex:"1",padding:"16px 20px",background:"rgba(255, 255, 255, 0.08)",border:"2px solid rgba(255, 255, 255, 0.15)",color:"#a8c0d8",borderRadius:"12px",fontSize:"15px",fontWeight:"600",cursor:"pointer"});const c=e.querySelector(".btn-submit");c&&Object.assign(c.style,{flex:"1.5",padding:"16px 20px",background:"linear-gradient(135deg, #10b981 0%, #047857 100%)",border:"none",color:"white",borderRadius:"12px",fontSize:"15px",fontWeight:"700",cursor:"pointer",boxShadow:"0 4px 15px rgba(16, 185, 129, 0.35)"})}async saveLead(e){const t=document.getElementById("leadName")?.value?.trim(),a=document.getElementById("leadMobile")?.value?.trim(),i=document.getElementById("leadEmail")?.value?.trim(),n=document.getElementById("leadCategory")?.value,s=document.getElementById("leadPriority")?.value,r=document.getElementById("leadNotes")?.value?.trim(),o=document.getElementById("leadCompany")?.value,c=document.getElementById("leadSource")?.value,p=document.getElementById("leadMobileSecondary")?.value?.trim(),g=document.getElementById("leadAddress")?.value?.trim(),v=document.getElementById("leadPhoneWhatsapp")?.checked,h=document.getElementById("leadPhoneSecondaryWhatsapp")?.checked,B=document.getElementById("leadRequirements")?.value?.trim(),x=document.getElementById("leadLookingFor")?.value?.trim(),L=document.getElementById("leadBudgetMin")?.value,S=document.getElementById("leadBudgetMax")?.value,R=document.getElementById("leadArea")?.value?.trim(),F=document.getElementById("leadCity")?.value?.trim(),q=document.getElementById("leadState")?.value?.trim(),H=document.getElementById("leadPincode")?.value?.trim(),j=document.getElementById("leadExpectedCloseDate")?.value,U=document.getElementById("leadNextFollowupDate")?.value,V=document.getElementById("leadTags")?.value?.trim();if(!t||!a){alert("Please enter name and mobile number");return}if(a.length!==10||!/^\d{10}$/.test(a)){alert("Please enter a valid 10-digit mobile number");return}const w=document.getElementById("btnSaveLead");w&&(w.disabled=!0,w.textContent="Creating...");try{const k={name:t,phone:a,email:i||null,category_id:n?parseInt(n):null,priority:s||"medium",status:"new",description:r||null,source:c||"mobile_app",phone_primary_whatsapp:v||!1,alternate_phone:p||null,phone_secondary_whatsapp:h||!1,address:g||null,requirements:B||null,looking_for:x||null,budget_min:L?parseFloat(L):null,budget_max:S?parseFloat(S):null,area:R||null,city:F||null,state:q||null,pincode:H||null,expected_close_date:j||null,next_followup_date:U||null,tags:V||null};o&&parseInt(o)>0&&(k.company_id=parseInt(o));const E=await d.post("/crm/unified-my-leads?role=mnr",k);E.success?(e.remove(),alert("Lead added successfully!"),await this.loadData()):alert(E.error||"Failed to add lead")}catch(k){console.error("[MNRMyLeads] Add lead failed:",k),alert(k.message||"Failed to add lead. Please try again.")}finally{w&&(w.disabled=!1,w.textContent="Create Lead")}}async viewLeadDetails(e){try{const t=await d.get(`/crm/unified-my-leads/${e}/details?role=mnr`);if(t.success&&t.data){const a=t.data,i=document.createElement("div");i.className="modal-overlay",i.innerHTML=`
          <div class="modal-content lead-details-modal">
            <div class="modal-header">
              <h3>Lead Details</h3>
              <button class="modal-close">&times;</button>
            </div>
            <div class="modal-body">
              <div class="lead-detail-section">
                <h4>${a.name}</h4>
                <p class="lead-status-large ${a.status?.toLowerCase()}">${a.status}</p>
              </div>
              <div class="detail-grid">
                <div class="detail-item">
                  <span class="label">Mobile</span>
                  <span class="value">${a.phone||"N/A"}</span>
                </div>
                <div class="detail-item">
                  <span class="label">Email</span>
                  <span class="value">${a.email||"N/A"}</span>
                </div>
                <div class="detail-item">
                  <span class="label">Category</span>
                  <span class="value">${a.category_name||a.category||"General"}</span>
                </div>
                <div class="detail-item">
                  <span class="label">Priority</span>
                  <span class="value priority-${a.priority?.toLowerCase()}">${a.priority||"Medium"}</span>
                </div>
                <div class="detail-item">
                  <span class="label">Source</span>
                  <span class="value">${a.source||"Direct"}</span>
                </div>
                <div class="detail-item">
                  <span class="label">Created</span>
                  <span class="value">${this.formatDate(a.created_at)}</span>
                </div>
              </div>
              ${a.notes?`
                <div class="notes-section">
                  <h5>Notes</h5>
                  <p>${a.notes}</p>
                </div>
              `:""}
            </div>
            <div class="modal-footer">
              <a href="tel:${a.phone}" class="btn-primary">📞 Call</a>
              <button class="btn-warning" id="btnEditLead" data-id="${a.id}">✏️ Edit</button>
              <button class="btn-secondary modal-close-btn">Close</button>
            </div>
          </div>
        `,document.body.appendChild(i),i.querySelector(".modal-close")?.addEventListener("click",()=>i.remove()),i.querySelector(".modal-close-btn")?.addEventListener("click",()=>i.remove()),i.querySelector("#btnEditLead")?.addEventListener("click",()=>{i.remove(),this.showEditLeadModal(a)}),i.addEventListener("click",n=>{n.target===i&&i.remove()})}}catch(t){console.error("[MNRMyLeads] View details failed:",t)}}async showEditLeadModal(e){const t=document.createElement("div");t.className="modal-overlay",t.innerHTML=`
      <div class="modal-content">
        <div class="modal-header">
          <h3>Update Lead Status</h3>
          <button class="modal-close">&times;</button>
        </div>
        <div class="modal-body">
          <div class="lead-info-summary">
            <strong>${e.name}</strong>
            <p>${e.phone||"No mobile"}</p>
          </div>
          <div class="form-group">
            <label>Status</label>
            <select id="editLeadStatus">
              <option value="new" ${e.status==="new"?"selected":""}>New</option>
              <option value="contacted" ${e.status==="contacted"?"selected":""}>Contacted</option>
              <option value="interested" ${e.status==="interested"?"selected":""}>Interested</option>
              <option value="negotiation" ${e.status==="negotiation"?"selected":""}>Negotiation</option>
              <option value="won" ${e.status==="won"?"selected":""}>Won</option>
              <option value="lost" ${e.status==="lost"?"selected":""}>Lost</option>
            </select>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" id="btnCancelEdit">Cancel</button>
          <button class="btn-primary" id="btnSaveEdit">Update Status</button>
        </div>
      </div>
    `,document.body.appendChild(t),t.querySelector(".modal-close")?.addEventListener("click",()=>t.remove()),t.querySelector("#btnCancelEdit")?.addEventListener("click",()=>t.remove()),t.querySelector("#btnSaveEdit")?.addEventListener("click",()=>this.updateLead(e.id,t)),t.addEventListener("click",a=>{a.target===t&&t.remove()})}async updateLead(e,t){const a=document.getElementById("editLeadStatus")?.value;try{const i=await d.put(`/crm/unified-my-leads/${e}/mnr-assignment?role=mnr`,{status:a});i.success?(t.remove(),await this.loadData()):alert(i.error||"Failed to update lead")}catch(i){console.error("[MNRMyLeads] Update lead failed:",i),alert("Failed to update lead. Please try again.")}}maskMobile(e){return!e||e.length<6?e||"N/A":e.slice(0,2)+"XXXX"+e.slice(-4)}formatDate(e){if(!e)return"N/A";try{return new Date(e).toLocaleDateString("en-IN",{day:"numeric",month:"short",year:"numeric"})}catch{return e}}}class fe{container;submissions=[];loading=!0;constructor(e){this.container=e}async init(){this.render(),await this.loadSubmissions()}async loadSubmissions(){this.loading=!0,this.updateContent();try{const e=await d.get("/feedback/my-submissions");e.success&&e.data&&(this.submissions=e.data.submissions||e.data||[])}catch(e){console.error("[MNRFeedback] Failed to load:",e)}this.loading=!1,this.updateContent()}render(){this.container.innerHTML=`
      <div class="page-container">
        ${l.render({title:"Feedback & Submissions",showBack:!0})}
        
        <div id="pageContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
    `,l.attachListeners({title:"Feedback & Submissions",showBack:!0})}updateContent(){const e=document.getElementById("pageContent");if(e){if(this.loading){e.innerHTML='<div class="loading-state">Loading...</div>';return}e.innerHTML=`
      <div class="feedback-hero card">
        <div class="hero-icon">📝</div>
        <h3>Share Your Experience</h3>
        <p>Submit feedback videos, photos, and testimonials</p>
      </div>

      <div class="submit-options">
        <button class="submit-option card" id="submitVideoBtn">
          <div class="option-icon">🎥</div>
          <div class="option-info">
            <h4>Video Testimonial</h4>
            <p>Share your success story</p>
          </div>
        </button>
        <button class="submit-option card" id="submitPhotoBtn">
          <div class="option-icon">📷</div>
          <div class="option-info">
            <h4>Photo Feedback</h4>
            <p>Share photos with team</p>
          </div>
        </button>
        <button class="submit-option card" id="submitReviewBtn">
          <div class="option-icon">⭐</div>
          <div class="option-info">
            <h4>Written Review</h4>
            <p>Write about your experience</p>
          </div>
        </button>
      </div>

      <h4 class="section-title">My Submissions</h4>
      ${this.submissions.length>0?`
        <div class="submissions-list">
          ${this.submissions.map(t=>this.renderSubmission(t)).join("")}
        </div>
      `:`
        <div class="empty-state card">
          <div class="empty-icon">📝</div>
          <p>No submissions yet</p>
        </div>
      `}

      <div class="notice-card card warning">
        <h4>⚠️ Guidelines</h4>
        <ul>
          <li>Feedback may be publicly displayed</li>
          <li>Videos should be under 2 minutes</li>
          <li>Photos must be clear and relevant</li>
          <li>Review within 24-48 hours</li>
        </ul>
      </div>
    `,this.attachListeners()}}attachListeners(){document.getElementById("submitVideoBtn")?.addEventListener("click",()=>{alert("Please use the web portal for video submissions")}),document.getElementById("submitPhotoBtn")?.addEventListener("click",()=>{alert("Please use the web portal for photo submissions")}),document.getElementById("submitReviewBtn")?.addEventListener("click",()=>{alert("Please use the web portal for written reviews")})}renderSubmission(e){const t=e.status.toLowerCase(),a=new Date(e.created_at).toLocaleDateString("en",{day:"numeric",month:"short",year:"numeric"});return`
      <div class="submission-card card ${t}">
        <div class="sub-header">
          <span class="sub-type">${e.type}</span>
          <span class="status-badge ${t}">${e.status}</span>
        </div>
        <h4>${e.title}</h4>
        <span class="sub-date">${a}</span>
      </div>
    `}}class ve{container;announcements=[];loading=!0;constructor(e){this.container=e}async init(){this.render(),await this.loadAnnouncements()}async loadAnnouncements(){this.loading=!0,this.updateContent();try{const e=await d.get("/feedback/my-submissions");if(e.success&&e.data){const t=Array.isArray(e.data)?e.data:[];this.announcements=t.filter(a=>a.status.toLowerCase()==="pending"||a.status.toLowerCase()==="under_review")}}catch(e){console.error("[MNRAnnouncementsPending] Failed to load:",e)}this.loading=!1,this.updateContent()}render(){this.container.innerHTML=`
      <div class="page-container">
        ${l.render({title:"⏳ Under Review",showBack:!0})}
        
        <div id="pageContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
    `,l.attachListeners({title:"⏳ Under Review",showBack:!0})}updateContent(){const e=document.getElementById("pageContent");if(e){if(this.loading){e.innerHTML='<div class="loading-state">Loading...</div>';return}if(this.announcements.length===0){e.innerHTML=`
        <div class="empty-state card">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
          </svg>
          <h3>No Pending Announcements</h3>
          <p>Your submitted announcements that are awaiting approval will appear here</p>
        </div>
      `;return}e.innerHTML=`
      <div class="announcements-list">
        ${this.announcements.map(t=>this.renderCard(t)).join("")}
      </div>
    `}}renderCard(e){const t=e.category?.name||e.category?.category_name||"General",a=e.media?.length||0;return`
      <div class="announcement-card card pending">
        <div class="status-badge pending">Pending Review</div>
        <div class="announcement-header">
          <span class="category-badge">${t}</span>
          <span class="announcement-date">${this.formatDate(e.submitted_at)}</span>
        </div>
        <h4 class="announcement-title">${e.title}</h4>
        <p class="announcement-description">${e.description||""}</p>
        ${this.renderMediaThumbs(e.media)}
        <div class="file-count">📁 ${a} file(s)</div>
      </div>
    `}renderMediaThumbs(e){return!e||e.length===0?"":`
      <div class="media-thumbnails">
        ${e.slice(0,4).map((a,i)=>`
          <div class="thumb ${a.media_type}">
            ${a.media_type==="video"?'<span class="play-icon">▶</span>':`<img src="${d.getMediaUrl(a.file_path)}" alt="Media ${i+1}" loading="lazy" onerror="this.style.display='none'" />`}
          </div>
        `).join("")}
        ${e.length>4?`<div class="thumb more">+${e.length-4}</div>`:""}
      </div>
    `}formatDate(e){if(!e)return"N/A";try{return new Date(e).toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"numeric",hour:"2-digit",minute:"2-digit"})}catch{return e}}}class ye{container;announcements=[];loading=!0;constructor(e){this.container=e}async init(){this.render(),await this.loadAnnouncements()}async loadAnnouncements(){this.loading=!0,this.updateContent();try{const e=await d.get("/feedback/my-submissions");if(e.success&&e.data){const t=Array.isArray(e.data)?e.data:[];this.announcements=t.filter(a=>a.status.toLowerCase()==="approved"||a.status.toLowerCase()==="partially_approved")}}catch(e){console.error("[MNRAnnouncementsApproved] Failed to load:",e)}this.loading=!1,this.updateContent()}render(){this.container.innerHTML=`
      <div class="page-container">
        ${l.render({title:"✅ Published",showBack:!0})}
        
        <div id="pageContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
    `,l.attachListeners({title:"✅ Published",showBack:!0})}updateContent(){const e=document.getElementById("pageContent");if(e){if(this.loading){e.innerHTML='<div class="loading-state">Loading...</div>';return}if(this.announcements.length===0){e.innerHTML=`
        <div class="empty-state card">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
            <polyline points="22 4 12 14.01 9 11.01"/>
          </svg>
          <h3>No Approved Announcements</h3>
          <p>Your approved announcements will appear here</p>
        </div>
      `;return}e.innerHTML=`
      <div class="announcements-list">
        ${this.announcements.map(t=>this.renderCard(t)).join("")}
      </div>
    `}}renderCard(e){const t=e.category?.name||e.category?.category_name||"General",a=e.media?.length||0;return`
      <div class="announcement-card card approved">
        <div class="status-badge approved">Approved</div>
        <div class="announcement-header">
          <span class="category-badge">${t}</span>
          <span class="announcement-date">${this.formatDate(e.submitted_at)}</span>
        </div>
        <h4 class="announcement-title">${e.title}</h4>
        <p class="announcement-description">${e.description||""}</p>
        ${this.renderMediaThumbs(e.media)}
        <div class="file-count">📁 ${a} file(s)</div>
        ${e.approved_at?`
          <div class="approval-info">
            ✅ Approved: ${this.formatDate(e.approved_at)}
          </div>
        `:""}
      </div>
    `}renderMediaThumbs(e){return!e||e.length===0?"":`
      <div class="media-thumbnails">
        ${e.slice(0,4).map((a,i)=>`
          <div class="thumb ${a.media_type}">
            ${a.media_type==="video"?'<span class="play-icon">▶</span>':`<img src="${d.getMediaUrl(a.file_path)}" alt="Media ${i+1}" loading="lazy" onerror="this.style.display='none'" />`}
          </div>
        `).join("")}
        ${e.length>4?`<div class="thumb more">+${e.length-4}</div>`:""}
      </div>
    `}formatDate(e){if(!e)return"N/A";try{return new Date(e).toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"numeric",hour:"2-digit",minute:"2-digit"})}catch{return e}}}class xe{container;announcements=[];loading=!0;constructor(e){this.container=e}async init(){this.render(),await this.loadAnnouncements()}async loadAnnouncements(){this.loading=!0,this.updateContent();try{const e=await d.get("/feedback/my-submissions");if(e.success&&e.data){const t=Array.isArray(e.data)?e.data:[];this.announcements=t.filter(a=>a.status.toLowerCase()==="rejected")}}catch(e){console.error("[MNRAnnouncementsRejected] Failed to load:",e)}this.loading=!1,this.updateContent()}render(){this.container.innerHTML=`
      <div class="page-container">
        ${l.render({title:"❌ Not Approved",showBack:!0})}
        
        <div id="pageContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
    `,l.attachListeners({title:"❌ Not Approved",showBack:!0})}updateContent(){const e=document.getElementById("pageContent");if(e){if(this.loading){e.innerHTML='<div class="loading-state">Loading...</div>';return}if(this.announcements.length===0){e.innerHTML=`
        <div class="empty-state card">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <line x1="15" y1="9" x2="9" y2="15"/>
            <line x1="9" y1="9" x2="15" y2="15"/>
          </svg>
          <h3>No Rejected Announcements</h3>
          <p>Your rejected announcements will appear here</p>
        </div>
      `;return}e.innerHTML=`
      <div class="announcements-list">
        ${this.announcements.map(t=>this.renderCard(t)).join("")}
      </div>
    `}}renderCard(e){const t=e.category?.name||e.category?.category_name||"General",a=e.media?.length||0,i=e.media?.filter(n=>n.decision_comment).map(n=>n.decision_comment).filter((n,s,r)=>r.indexOf(n)===s);return`
      <div class="announcement-card card rejected">
        <div class="status-badge rejected">Rejected</div>
        <div class="announcement-header">
          <span class="category-badge">${t}</span>
          <span class="announcement-date">${this.formatDate(e.submitted_at)}</span>
        </div>
        <h4 class="announcement-title">${e.title}</h4>
        <p class="announcement-description">${e.description||""}</p>
        ${this.renderMediaThumbs(e.media)}
        <div class="file-count">📁 ${a} file(s)</div>
        ${i&&i.length>0?`
          <div class="rejection-reason">
            <strong>Reason:</strong> ${i.join("; ")}
          </div>
        `:""}
      </div>
    `}renderMediaThumbs(e){return!e||e.length===0?"":`
      <div class="media-thumbnails">
        ${e.slice(0,4).map((a,i)=>`
          <div class="thumb ${a.media_type} ${a.media_status==="rejected"?"rejected":""}">
            ${a.media_type==="video"?'<span class="play-icon">▶</span>':`<img src="${d.getMediaUrl(a.file_path)}" alt="Media ${i+1}" loading="lazy" onerror="this.style.display='none'" />`}
            ${a.media_status==="rejected"?'<span class="rejected-x">✕</span>':""}
          </div>
        `).join("")}
        ${e.length>4?`<div class="thumb more">+${e.length-4}</div>`:""}
      </div>
    `}formatDate(e){if(!e)return"N/A";try{return new Date(e).toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"numeric",hour:"2-digit",minute:"2-digit"})}catch{return e}}}const $=[{type:"Platinum",price:15e3,name:"Platinum Package",description:"Maximum benefits, best value",directBonus:"₹3,000 direct referral bonus",icon:"👑",color:"#f59e0b"},{type:"Diamond",price:7500,name:"Diamond Package",description:"Great value, excellent benefits",directBonus:"₹1,500 direct referral bonus (up to 2x)",icon:"💎",color:"#06b6d4"}],X=["Google Pay","PhonePe","Paytm","Bank Transfer (NEFT/RTGS/IMPS)","UPI","Cash Deposit","Other"];class we{container;purchaseRequests=[];loading=!0;submitting=!1;selectedPackage=null;quantity=1;transactionId="";transactionDate=new Date().toISOString().split("T")[0];paymentMode="";screenshotFile=null;screenshotPreview="";constructor(e){this.container=e}async init(){this.render(),await this.loadPurchaseHistory()}async loadPurchaseHistory(){this.loading=!0,this.updateContent();try{const e=await d.get("/users/pins/purchase-requests");e.success&&e.data&&(this.purchaseRequests=(e.data.requests||e.data||[]).map(t=>({id:t.id||0,package_type:t.package_type||t.type||"",quantity:t.quantity||1,amount_paid:t.amount_paid||t.amount||0,status:t.status||"Pending",created_at:t.created_at||"",transaction_id:t.transaction_id||""})))}catch(e){console.error("[MNRCouponBuy] Failed to load history:",e)}this.loading=!1,this.updateContent()}render(){this.container.innerHTML=`
      <style>
        ${m.getStyles()}
        .coupon-buy-page { padding: 16px; }
        
        .info-banner {
          background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
          border-radius: 12px;
          padding: 16px;
          margin-bottom: 16px;
          color: white;
        }
        .info-banner h4 { margin: 0 0 8px; font-size: 15px; }
        .info-banner p { margin: 0; font-size: 13px; opacity: 0.9; line-height: 1.5; }
        
        .payment-scanner-card {
          background: linear-gradient(135deg, #f8fff8 0%, #d1fae5 100%);
          border: 2px solid #10b981;
          border-radius: 12px;
          padding: 16px;
          margin-bottom: 16px;
          text-align: center;
        }
        .payment-scanner-card h5 {
          color: #059669;
          margin: 0 0 12px;
          font-size: 14px;
        }
        .scanner-notice {
          background: #fef3c7;
          border-radius: 8px;
          padding: 10px;
          margin-top: 12px;
          font-size: 12px;
          color: #92400e;
        }
        
        .section-header {
          display: flex;
          align-items: center;
          gap: 8px;
          margin: 20px 0 12px;
          font-size: 15px;
          font-weight: 600;
          color: #e6f1ff;
        }
        
        .packages-grid {
          display: grid;
          gap: 12px;
        }
        
        .package-card {
          background: rgba(22, 33, 62, 0.8);
          border: 2px solid rgba(255,255,255,0.1);
          border-radius: 12px;
          padding: 16px;
          cursor: pointer;
          transition: all 0.2s;
        }
        .package-card:hover {
          border-color: rgba(100, 210, 255, 0.5);
          transform: translateY(-2px);
        }
        .package-card.selected {
          border-color: #64d2ff;
          background: rgba(100, 210, 255, 0.1);
        }
        .package-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 8px;
        }
        .package-icon { font-size: 24px; }
        .package-name {
          font-size: 16px;
          font-weight: 600;
          color: #e6f1ff;
        }
        .package-price {
          font-size: 20px;
          font-weight: 700;
          color: #10b981;
        }
        .package-desc {
          font-size: 13px;
          color: #8892b0;
          margin: 0 0 8px;
        }
        .package-bonus {
          display: inline-block;
          background: rgba(16, 185, 129, 0.2);
          color: #10b981;
          padding: 4px 10px;
          border-radius: 20px;
          font-size: 12px;
          font-weight: 500;
        }
        
        .purchase-form {
          background: rgba(22, 33, 62, 0.8);
          border-radius: 12px;
          padding: 16px;
          margin-top: 16px;
        }
        .purchase-form h4 {
          color: #e6f1ff;
          margin: 0 0 16px;
          font-size: 15px;
        }
        .form-group {
          margin-bottom: 16px;
        }
        .form-group label {
          display: block;
          font-size: 12px;
          color: #8892b0;
          text-transform: uppercase;
          margin-bottom: 8px;
        }
        .quantity-selector {
          display: flex;
          align-items: center;
          gap: 12px;
        }
        .qty-btn {
          width: 40px;
          height: 40px;
          border-radius: 8px;
          border: 1px solid rgba(100, 210, 255, 0.3);
          background: rgba(100, 210, 255, 0.1);
          color: #64d2ff;
          font-size: 20px;
          cursor: pointer;
        }
        .qty-btn:active {
          background: rgba(100, 210, 255, 0.2);
        }
        .quantity-selector input {
          width: 60px;
          text-align: center;
          padding: 8px;
          border-radius: 8px;
          border: 1px solid rgba(255,255,255,0.1);
          background: rgba(13, 27, 42, 0.8);
          color: #e6f1ff;
          font-size: 16px;
        }
        .total-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 12px 0;
          border-top: 1px solid rgba(255,255,255,0.1);
        }
        .total-label { color: #8892b0; font-size: 14px; }
        .total-amount { color: #10b981; font-size: 24px; font-weight: 700; }
        
        .payment-notice {
          background: rgba(251, 191, 36, 0.1);
          border: 1px solid rgba(251, 191, 36, 0.3);
          border-radius: 8px;
          padding: 12px;
          margin-top: 16px;
          font-size: 13px;
          color: #fbbf24;
        }
        
        .history-section { margin-top: 24px; }
        
        .form-input, .form-select {
          width: 100%;
          padding: 12px;
          border-radius: 8px;
          border: 1px solid rgba(255,255,255,0.15);
          background: rgba(13, 27, 42, 0.8);
          color: #e6f1ff;
          font-size: 14px;
        }
        .form-input:focus, .form-select:focus {
          outline: none;
          border-color: #64d2ff;
        }
        .form-row {
          display: flex;
          gap: 12px;
        }
        .form-group.half {
          flex: 1;
        }
        
        .screenshot-upload {
          background: rgba(13, 27, 42, 0.8);
          border: 2px dashed rgba(255,255,255,0.2);
          border-radius: 12px;
          padding: 20px;
          cursor: pointer;
          text-align: center;
          transition: border-color 0.2s;
        }
        .screenshot-upload:hover {
          border-color: #64d2ff;
        }
        .upload-placeholder span {
          font-size: 32px;
          display: block;
          margin-bottom: 8px;
        }
        .upload-placeholder p {
          color: #8892b0;
          margin: 0 0 4px;
          font-size: 14px;
        }
        .upload-placeholder small {
          color: #5a6a8a;
          font-size: 12px;
        }
        .screenshot-preview {
          position: relative;
        }
        .screenshot-preview img {
          max-width: 100%;
          max-height: 200px;
          border-radius: 8px;
        }
        .remove-screenshot {
          position: absolute;
          top: 8px;
          right: 8px;
          width: 28px;
          height: 28px;
          border-radius: 50%;
          background: rgba(239, 68, 68, 0.9);
          color: white;
          border: none;
          font-size: 16px;
          cursor: pointer;
        }
        
        .approval-workflow {
          background: rgba(251, 191, 36, 0.1);
          border: 1px solid rgba(251, 191, 36, 0.3);
          border-radius: 8px;
          padding: 12px;
          margin: 16px 0;
        }
        .approval-workflow h5 {
          color: #fbbf24;
          margin: 0 0 8px;
          font-size: 14px;
        }
        .approval-workflow ol {
          margin: 0;
          padding-left: 20px;
          color: #d1d5db;
          font-size: 12px;
          line-height: 1.6;
        }
        
        .submit-btn {
          width: 100%;
          padding: 14px;
          font-size: 16px;
          font-weight: 600;
          background: linear-gradient(135deg, #10b981 0%, #059669 100%);
          color: white;
          border: none;
          border-radius: 10px;
          cursor: pointer;
          margin-top: 8px;
        }
        .submit-btn:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }
      </style>
      ${l.render({title:"🛒 Purchase Coupon",showBack:!0})}
      <div class="coupon-buy-page" id="pageContent">
        <div class="loading-state">Loading...</div>
      </div>
    `,l.attachListeners({title:"🛒 Purchase Coupon",showBack:!0})}updateContent(){const e=document.getElementById("pageContent");if(e){if(this.loading){e.innerHTML='<div class="loading-state" style="text-align: center; padding: 40px; color: #8892b0;">Loading...</div>';return}e.innerHTML=`
      <div class="info-banner">
        <h4>Package Information</h4>
        <p>
          • <strong>Platinum (₹15,000)</strong>: Maximum benefits, ₹3,000 direct referral bonus<br>
          • <strong>Diamond (₹7,500)</strong>: Great value, ₹1,500 direct referral bonus (up to 2x)
        </p>
      </div>

      <div class="payment-scanner-card">
        <h5>🔒 Payment Scanner - Verify Before Payment</h5>
        <p style="font-size: 13px; color: #374151; margin: 0;">
          Please verify the company name <strong>"MNR MEGA NATURAL RESOURCES"</strong> before making payment
        </p>
        <div class="scanner-notice">
          ⚠️ Make payment to the company bank account and upload payment screenshot as proof
        </div>
      </div>

      <div class="section-header">
        <span>📦</span> Select Package
      </div>
      
      <div class="packages-grid">
        ${$.map(t=>`
          <div class="package-card ${this.selectedPackage===t.type?"selected":""}" data-type="${t.type}">
            <div class="package-header">
              <div>
                <span class="package-icon">${t.icon}</span>
                <span class="package-name">${t.name}</span>
              </div>
              <span class="package-price">₹${t.price.toLocaleString()}</span>
            </div>
            <p class="package-desc">${t.description}</p>
            <span class="package-bonus">${t.directBonus}</span>
          </div>
        `).join("")}
      </div>

      ${this.selectedPackage?this.renderPurchaseForm():""}

      ${this.purchaseRequests.length>0?this.renderHistory():""}
    `,this.attachListeners()}}renderPurchaseForm(){const e=$.find(a=>a.type===this.selectedPackage);if(!e)return"";const t=e.price*this.quantity;return`
      <div class="purchase-form">
        <h4>Purchase Details</h4>
        
        <div class="form-row">
          <div class="form-group">
            <label>Quantity</label>
            <div class="quantity-selector">
              <button class="qty-btn" id="decreaseQty">-</button>
              <input type="number" id="quantityInput" value="${this.quantity}" min="1" max="10" readonly />
              <button class="qty-btn" id="increaseQty">+</button>
            </div>
          </div>
        </div>
        
        <h4 style="margin-top: 20px;">Payment Details</h4>
        
        <div class="form-group">
          <label>Transaction ID *</label>
          <input type="text" class="form-input" id="transactionId" placeholder="Enter transaction/UTR number" value="${this.transactionId}" />
        </div>
        
        <div class="form-row">
          <div class="form-group half">
            <label>Transaction Date *</label>
            <input type="date" class="form-input" id="transactionDate" value="${this.transactionDate}" />
          </div>
          <div class="form-group half">
            <label>Amount Paid *</label>
            <input type="number" class="form-input" id="amountPaid" value="${t}" readonly />
          </div>
        </div>
        
        <div class="form-group">
          <label>Payment Mode *</label>
          <select class="form-select" id="paymentMode">
            <option value="">Select Payment Mode</option>
            ${X.map(a=>`<option value="${a}" ${this.paymentMode===a?"selected":""}>${a}</option>`).join("")}
          </select>
        </div>
        
        <div class="form-group">
          <label>Payment Screenshot *</label>
          <div class="screenshot-upload" id="screenshotUpload">
            ${this.screenshotPreview?`
              <div class="screenshot-preview">
                <img src="${this.screenshotPreview}" alt="Screenshot" />
                <button class="remove-screenshot" id="removeScreenshot">✕</button>
              </div>
            `:`
              <div class="upload-placeholder">
                <span>📷</span>
                <p>Tap to upload payment screenshot</p>
                <small>Max 500 KB, jpg/png/pdf</small>
              </div>
            `}
          </div>
        </div>
        
        <div class="total-row">
          <span class="total-label">Total Amount</span>
          <span class="total-amount">₹${t.toLocaleString()}</span>
        </div>
        
        <div class="approval-workflow">
          <h5>⚠️ Approval Workflow:</h5>
          <ol>
            <li>Admin/Super Admin will verify your payment details</li>
            <li>Finance Admin will approve the transaction</li>
            <li>Upon approval, coupon will be assigned to your account</li>
          </ol>
        </div>
        
        <button class="btn btn-primary submit-btn" id="submitPurchaseBtn" ${this.submitting?"disabled":""}>
          ${this.submitting?"Submitting...":"Submit Purchase Request"}
        </button>
      </div>
    `}renderHistory(){return`
      <div class="history-section">
        <div class="section-header">
          <span>📋</span> Recent Purchase Requests
        </div>
        ${new m({columns:[{key:"package_type",label:"Package",render:t=>`<strong>${t}</strong>`},{key:"quantity",label:"Qty"},{key:"amount_paid",label:"Amount",render:t=>`₹${t.toLocaleString()}`},{key:"status",label:"Status",render:t=>this.getStatusBadge(t)},{key:"created_at",label:"Date",render:t=>this.formatDate(t)}],data:this.purchaseRequests.slice(0,5),emptyMessage:"No purchase history"}).render()}
      </div>
    `}getStatusBadge(e){const t=e.toLowerCase();return t==="approved"||t==="completed"?'<span class="badge badge-success">Approved</span>':t==="pending"?'<span class="badge badge-warning">Pending</span>':t==="rejected"?'<span class="badge badge-danger">Rejected</span>':`<span class="badge badge-secondary">${e}</span>`}attachListeners(){document.querySelectorAll(".package-card").forEach(e=>{e.addEventListener("click",()=>{const t=e.getAttribute("data-type");t&&(this.selectedPackage=t,this.quantity=1,this.updateContent())})}),document.getElementById("decreaseQty")?.addEventListener("click",()=>{this.quantity>1&&(this.quantity--,this.updateTotalOnly())}),document.getElementById("increaseQty")?.addEventListener("click",()=>{this.quantity<10&&(this.quantity++,this.updateTotalOnly())}),document.getElementById("transactionId")?.addEventListener("input",e=>{this.transactionId=e.target.value}),document.getElementById("transactionDate")?.addEventListener("change",e=>{this.transactionDate=e.target.value}),document.getElementById("paymentMode")?.addEventListener("change",e=>{this.paymentMode=e.target.value}),document.getElementById("screenshotUpload")?.addEventListener("click",()=>{this.screenshotPreview||this.captureScreenshot()}),document.getElementById("removeScreenshot")?.addEventListener("click",e=>{e.stopPropagation(),this.screenshotFile=null,this.screenshotPreview="",this.updateContent()}),document.getElementById("submitPurchaseBtn")?.addEventListener("click",()=>{this.submitPurchaseRequest()})}updateTotalOnly(){const e=$.find(s=>s.type===this.selectedPackage);if(!e)return;const t=e.price*this.quantity,a=document.getElementById("quantityInput"),i=document.getElementById("amountPaid"),n=document.querySelector(".total-amount");a&&(a.value=String(this.quantity)),i&&(i.value=String(t)),n&&(n.textContent=`₹${t.toLocaleString()}`)}async captureScreenshot(){try{const e=await G.getPhoto({quality:80,allowEditing:!1,resultType:Y.DataUrl,source:O.Prompt});if(e.dataUrl){this.screenshotPreview=e.dataUrl;const t=await fetch(e.dataUrl).then(a=>a.blob());this.screenshotFile=new File([t],`payment_screenshot.${e.format||"jpg"}`,{type:`image/${e.format||"jpeg"}`}),this.updateContent()}}catch(e){console.error("[MNRCouponBuy] Camera error:",e)}}async submitPurchaseRequest(){if(this.submitting)return;if(!this.selectedPackage){alert("Please select a package");return}if(!this.transactionId.trim()){alert("Please enter Transaction ID");return}if(!this.transactionDate){alert("Please enter Transaction Date");return}if(!this.paymentMode){alert("Please select Payment Mode");return}if(!this.screenshotFile){alert("Please upload Payment Screenshot");return}const e=$.find(t=>t.type===this.selectedPackage);if(e){this.submitting=!0,this.updateContent();try{const t=new FormData;t.append("package_type",e.type),t.append("quantity",String(this.quantity)),t.append("transaction_id",this.transactionId),t.append("transaction_date",this.transactionDate),t.append("amount_paid",String(e.price*this.quantity)),t.append("payment_mode",this.paymentMode),t.append("screenshot",this.screenshotFile);const a=await d.postFormData("/users/pins/purchase-request",t);a.success?(alert("Purchase request submitted successfully! Awaiting admin approval."),this.resetForm(),await this.loadPurchaseHistory()):alert(a.error||"Failed to submit purchase request")}catch(t){console.error("[MNRCouponBuy] Submit error:",t),alert(t.message||"Failed to submit purchase request")}finally{this.submitting=!1,this.updateContent()}}}resetForm(){this.selectedPackage=null,this.quantity=1,this.transactionId="",this.transactionDate=new Date().toISOString().split("T")[0],this.paymentMode="",this.screenshotFile=null,this.screenshotPreview=""}formatDate(e){try{return new Date(e).toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"numeric"})}catch{return e||"-"}}}class _e{container;activePins=[];loading=!0;selectedPin=null;targetUserId="";targetUserName="";searchResults=[];isSearching=!1;searchQuery="";constructor(e){this.container=e}async init(){this.render(),await this.loadActivePins()}async loadActivePins(){this.loading=!0,this.updateContent();try{const e=await d.get("/users/pins");if(e.success&&e.data){const t=e.data.pins||[];this.activePins=t.filter(a=>a.status==="Active")}}catch(e){console.error("[MNRCouponActivate] Failed to load:",e)}this.loading=!1,this.updateContent()}render(){this.container.innerHTML=`
      <style>
        .search-input-container { position: relative; }
        .search-spinner {
          position: absolute; right: 12px; top: 50%; transform: translateY(-50%);
          width: 16px; height: 16px; border: 2px solid #8892b0;
          border-top-color: #64ffda; border-radius: 50%; animation: spin 0.8s linear infinite;
        }
        @keyframes spin { to { transform: translateY(-50%) rotate(360deg); } }
        .selected-user {
          display: flex; align-items: center; justify-content: space-between;
          background: rgba(100, 255, 218, 0.1); border: 1px solid rgba(100, 255, 218, 0.3);
          border-radius: 8px; padding: 12px 16px; margin-top: 12px;
        }
        .selected-user-info { display: flex; flex-direction: column; gap: 4px; }
        .selected-user-id { color: #64ffda; font-weight: 600; font-size: 14px; }
        .selected-user-name { color: #e6f1ff; font-size: 15px; font-weight: 500; }
        .clear-selection {
          background: rgba(255,100,100,0.2); border: none; color: #ff6b6b;
          width: 28px; height: 28px; border-radius: 50%; cursor: pointer;
          font-size: 14px; display: flex; align-items: center; justify-content: center;
        }
        .search-results {
          background: #1a2744; border: 1px solid #2d3b4f; border-radius: 8px;
          margin-top: 8px; max-height: 200px; overflow-y: auto;
        }
        .search-result-item {
          display: flex; flex-direction: column; gap: 2px;
          padding: 12px 16px; border-bottom: 1px solid #2d3b4f; cursor: pointer;
        }
        .search-result-item:last-child { border-bottom: none; }
        .search-result-item:active { background: rgba(100, 255, 218, 0.1); }
        .search-result-item .user-id { color: #64ffda; font-size: 13px; font-weight: 600; }
        .search-result-item .user-name { color: #e6f1ff; font-size: 14px; }
      </style>
      <div class="page-container">
        ${l.render({title:"✅ Activate Coupon",showBack:!0})}
        
        <div id="pageContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
    `,l.attachListeners({title:"✅ Activate Coupon",showBack:!0})}updateContent(){const e=document.getElementById("pageContent");if(e){if(this.loading){e.innerHTML='<div class="loading-state">Loading...</div>';return}if(this.activePins.length===0){e.innerHTML=`
        <div class="empty-state card">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
          </svg>
          <h3>No Coupons to Activate</h3>
          <p>Purchase a coupon first to activate it</p>
        </div>
      `;return}e.innerHTML=`
      <div class="activate-card card">
        <div class="card-header">Activate PIN/Coupon</div>
        
        <div class="info-box">
          <h4>How to Activate:</h4>
          <ul>
            <li>Select an available PIN from your inventory</li>
            <li>Search and select the user/member who will use this PIN</li>
            <li>Activation will upgrade the member's package</li>
          </ul>
        </div>

        <div class="form-group">
          <label>Select PIN Code</label>
          <select id="pinSelect" class="form-select">
            <option value="">-- Select a PIN --</option>
            ${this.activePins.map(t=>`
              <option value="${t.id}" ${this.selectedPin===t.id?"selected":""}>
                ${t.coupon_code} - ${t.coupon_type} Package
              </option>
            `).join("")}
          </select>
          <small>Select from your available/unused PINs</small>
        </div>

        <div class="form-group">
          <label>Activate For (User ID)</label>
          <div class="search-input-container">
            <input type="text" id="userIdInput" class="form-input" 
              placeholder="Search by MNR ID or Name..."
              value="${this.searchQuery}" />
            ${this.isSearching?'<div class="search-spinner"></div>':""}
          </div>
          <small>Leave blank to activate for yourself. Type to search inactive users.</small>
          
          ${this.targetUserId&&this.targetUserName?`
            <div class="selected-user">
              <div class="selected-user-info">
                <span class="selected-user-id">${this.targetUserId}</span>
                <span class="selected-user-name">${this.targetUserName}</span>
              </div>
              <button class="clear-selection" id="clearUserBtn">✕</button>
            </div>
          `:""}
          
          ${this.searchResults.length>0&&!this.targetUserId?`
            <div class="search-results">
              ${this.searchResults.map(t=>`
                <div class="search-result-item" data-user-id="${t.id}" data-user-name="${t.name||t.full_name||"Unknown"}">
                  <span class="user-id">${t.id}</span>
                  <span class="user-name">${t.name||t.full_name||"Unknown"}</span>
                </div>
              `).join("")}
            </div>
          `:""}
        </div>

        <button class="btn-primary activate-btn" id="activateBtn" ${this.selectedPin?"":"disabled"}>
          Activate PIN
        </button>
      </div>
    `,this.attachListeners()}}attachListeners(){document.getElementById("pinSelect")?.addEventListener("change",a=>{const i=a.target;this.selectedPin=i.value||null,this.updateContent()});const e=document.getElementById("userIdInput");let t;e?.addEventListener("input",a=>{const i=a.target;this.searchQuery=i.value,this.targetUserId||(clearTimeout(t),i.value.length>=2?t=setTimeout(()=>this.searchUsers(i.value),400):(this.searchResults=[],this.updateContent()))}),document.getElementById("clearUserBtn")?.addEventListener("click",()=>{this.targetUserId="",this.targetUserName="",this.searchQuery="",this.searchResults=[],this.updateContent()}),document.querySelectorAll(".search-result-item").forEach(a=>{a.addEventListener("click",()=>{const i=a.getAttribute("data-user-id"),n=a.getAttribute("data-user-name");i&&(this.targetUserId=i,this.targetUserName=n||"Unknown",this.searchQuery="",this.searchResults=[],this.updateContent())})}),document.getElementById("activateBtn")?.addEventListener("click",()=>{this.handleActivate()})}async searchUsers(e){if(!this.isSearching){this.isSearching=!0;try{const t=await d.get(`/team/search-inactive?q=${encodeURIComponent(e)}`);t.success&&t.data&&(this.searchResults=t.data.users||t.data||[],this.updateContent())}catch(t){console.error("[MNRCouponActivate] Search failed:",t)}this.isSearching=!1}}async handleActivate(){if(!this.selectedPin){alert("Please select a PIN to activate");return}const e=this.targetUserId?`Activate PIN for ${this.targetUserName} (${this.targetUserId})?`:"Activate PIN for yourself?";if(confirm(e))try{const t=await d.post("/users/pins/activate",{pin_code:this.selectedPin,user_id:this.targetUserId||null});t.success?(alert("PIN activated successfully!"),this.selectedPin=null,this.targetUserId="",await this.loadActivePins()):alert(t.error||"Failed to activate PIN")}catch(t){console.error("[MNRCouponActivate] Activation failed:",t),alert("Failed to activate PIN. Please try again.")}}}class ke{container;pins=[];summary={total_pins:0,active_pins:0,used_pins:0};loading=!0;activeTab="all";constructor(e){this.container=e}async init(){this.render(),await this.loadPins()}async loadPins(){this.loading=!0,this.updateContent();try{const e=await d.get("/users/pins");if(e.success&&e.data){const t=e.data.pins||e.data||[];this.pins=t.map(a=>({id:a.id||"",coupon_code:a.coupon_code||a.code||a.pin_code||"",coupon_type:a.coupon_type||a.package_type||a.type||"Standard",status:a.status||"Active",amount:a.amount||a.value||0,created_at:a.created_at||"",activated_at:a.activated_at||a.used_at||null,used_by:a.used_by||a.activated_by||"-",activated_for:a.activated_for||a.used_for||"-"})),this.calculateSummary()}}catch(e){console.error("[MNRCouponStatus] Failed to load:",e)}this.loading=!1,this.updateContent()}calculateSummary(){this.summary={total_pins:this.pins.length,active_pins:this.pins.filter(e=>e.status.toLowerCase()==="active"||e.status.toLowerCase()==="available").length,used_pins:this.pins.filter(e=>e.status.toLowerCase()==="used"||e.status.toLowerCase()==="activated").length}}getFilteredPins(){return this.activeTab==="all"?this.pins:this.activeTab==="active"?this.pins.filter(e=>e.status.toLowerCase()==="active"||e.status.toLowerCase()==="available"):this.pins.filter(e=>e.status.toLowerCase()==="used"||e.status.toLowerCase()==="activated")}render(){this.container.innerHTML=`
      <style>
        ${m.getStyles()}
        .coupon-status-page { padding: 16px; }
        
        .summary-row {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 10px;
          margin-bottom: 16px;
        }
        .summary-card {
          background: rgba(22, 33, 62, 0.8);
          border-radius: 10px;
          padding: 14px;
          text-align: center;
        }
        .summary-card .label {
          font-size: 10px;
          color: #8892b0;
          text-transform: uppercase;
          margin-bottom: 4px;
        }
        .summary-card .value {
          font-size: 22px;
          font-weight: 700;
          color: #e6f1ff;
        }
        .summary-card:nth-child(2) .value { color: #10b981; }
        .summary-card:nth-child(3) .value { color: #3b82f6; }
        
        .tab-bar {
          display: flex;
          gap: 8px;
          margin-bottom: 16px;
        }
        .tab-btn {
          flex: 1;
          padding: 10px;
          background: rgba(22, 33, 62, 0.8);
          border: 1px solid rgba(255,255,255,0.1);
          border-radius: 8px;
          color: #8892b0;
          font-size: 13px;
          cursor: pointer;
          text-align: center;
        }
        .tab-btn.active {
          background: #64d2ff;
          border-color: #64d2ff;
          color: #0d1b2a;
          font-weight: 600;
        }
      </style>
      ${l.render({title:"🎫 My Coupons",showBack:!0})}
      <div class="coupon-status-page" id="pageContent">
        <div class="loading-state" style="text-align: center; padding: 40px; color: #8892b0;">Loading...</div>
      </div>
    `,l.attachListeners({title:"🎫 My Coupons",showBack:!0})}updateContent(){const e=document.getElementById("pageContent");if(!e)return;if(this.loading){e.innerHTML='<div class="loading-state" style="text-align: center; padding: 40px; color: #8892b0;">Loading...</div>';return}const t=this.getFilteredPins(),a=new m({columns:[{key:"coupon_code",label:"Coupon Code",render:i=>`<strong>${i}</strong>`},{key:"coupon_type",label:"Type"},{key:"amount",label:"Amount",render:i=>i>0?`₹${i.toLocaleString()}`:"-"},{key:"status",label:"Status",render:i=>this.getStatusBadge(i)},{key:"activated_for",label:"Used For"},{key:"created_at",label:"Created",render:i=>this.formatDate(i)},{key:"activated_at",label:"Activated",render:i=>this.formatDate(i)}],data:t,emptyMessage:"No coupons found"});e.innerHTML=`
      <div class="summary-row">
        <div class="summary-card">
          <div class="label">Total</div>
          <div class="value">${this.summary.total_pins}</div>
        </div>
        <div class="summary-card">
          <div class="label">Active</div>
          <div class="value">${this.summary.active_pins}</div>
        </div>
        <div class="summary-card">
          <div class="label">Used</div>
          <div class="value">${this.summary.used_pins}</div>
        </div>
      </div>

      <div class="tab-bar">
        <button class="tab-btn ${this.activeTab==="all"?"active":""}" data-tab="all">All</button>
        <button class="tab-btn ${this.activeTab==="active"?"active":""}" data-tab="active">Active</button>
        <button class="tab-btn ${this.activeTab==="used"?"active":""}" data-tab="used">Used</button>
      </div>

      <div class="table-summary-bar">
        <span>Showing <span class="count">${t.length}</span> coupons</span>
      </div>
      ${a.render()}
    `,this.attachListeners()}attachListeners(){document.querySelectorAll(".tab-btn").forEach(e=>{e.addEventListener("click",()=>{this.activeTab=e.getAttribute("data-tab")||"all",document.querySelectorAll(".tab-btn").forEach(t=>t.classList.remove("active")),e.classList.add("active"),this.updateContent()})})}getStatusBadge(e){const t=e.toLowerCase();return t==="active"||t==="available"?'<span class="badge badge-success">Active</span>':t==="used"||t==="activated"?'<span class="badge badge-info">Used</span>':t==="expired"?'<span class="badge badge-danger">Expired</span>':`<span class="badge badge-secondary">${e}</span>`}formatDate(e){if(!e)return"-";try{return new Date(e).toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"numeric"})}catch{return e}}}class Le{container;transferablePins=[];transferHistory=[];loading=!0;selectedPin=null;recipientId="";constructor(e){this.container=e}async init(){this.render(),await this.loadData()}async loadData(){this.loading=!0,this.updateContent();try{const[e,t]=await Promise.all([d.get("/users/pins"),d.get("/coupon-transfers/my-transfer-history")]);if(e.success&&e.data){const a=e.data.pins||[];this.transferablePins=a.filter(i=>i.status==="Active"||i.status==="Available").map(i=>({id:i.id||"",coupon_code:i.coupon_code||i.code||"",coupon_type:i.coupon_type||i.package_type||"Standard",status:i.status||"Active",amount:i.amount||i.value||0}))}if(t.success&&t.data){const a=t.data.transfers||t.data||[];this.transferHistory=a.map(i=>({id:i.id||0,coupon_code:i.coupon_code||i.code||"",from_user:i.from_user_name||i.from_user_id||"-",to_user:i.to_user_name||i.to_user_id||"-",status:i.status||"Pending",created_at:i.created_at||"",approved_at:i.approved_at||null}))}}catch(e){console.error("[MNRCouponTransfer] Failed to load:",e)}this.loading=!1,this.updateContent()}render(){this.container.innerHTML=`
      <style>
        ${m.getStyles()}
        .coupon-transfer-page { padding: 16px; }
        
        .transfer-form {
          background: rgba(22, 33, 62, 0.8);
          border-radius: 12px;
          padding: 16px;
          margin-bottom: 20px;
        }
        .transfer-form h4 {
          color: #e6f1ff;
          margin: 0 0 16px;
          font-size: 15px;
        }
        .form-group {
          margin-bottom: 16px;
        }
        .form-group label {
          display: block;
          font-size: 12px;
          color: #8892b0;
          text-transform: uppercase;
          margin-bottom: 8px;
        }
        .form-group select, .form-group input {
          width: 100%;
          padding: 12px;
          border-radius: 8px;
          border: 1px solid rgba(255,255,255,0.1);
          background: rgba(13, 27, 42, 0.8);
          color: #e6f1ff;
          font-size: 14px;
        }
        .form-group select:focus, .form-group input:focus {
          outline: none;
          border-color: #64d2ff;
        }
        .btn-transfer {
          width: 100%;
          padding: 14px;
          border-radius: 8px;
          border: none;
          background: linear-gradient(135deg, #10b981 0%, #059669 100%);
          color: white;
          font-size: 15px;
          font-weight: 600;
          cursor: pointer;
        }
        .btn-transfer:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
        
        .available-pins {
          background: rgba(16, 185, 129, 0.1);
          border: 1px solid rgba(16, 185, 129, 0.3);
          border-radius: 10px;
          padding: 14px;
          margin-bottom: 20px;
          text-align: center;
        }
        .available-pins .count {
          font-size: 28px;
          font-weight: 700;
          color: #10b981;
        }
        .available-pins .label {
          font-size: 12px;
          color: #8892b0;
        }
        
        .section-title {
          font-size: 15px;
          font-weight: 600;
          color: #e6f1ff;
          margin: 20px 0 12px;
          display: flex;
          align-items: center;
          gap: 8px;
        }
        
        .notice {
          background: rgba(251, 191, 36, 0.1);
          border: 1px solid rgba(251, 191, 36, 0.3);
          border-radius: 8px;
          padding: 12px;
          margin-bottom: 16px;
          font-size: 12px;
          color: #fbbf24;
        }
      </style>
      ${l.render({title:"🔄 Transfer Coupon",showBack:!0})}
      <div class="coupon-transfer-page" id="pageContent">
        <div class="loading-state" style="text-align: center; padding: 40px; color: #8892b0;">Loading...</div>
      </div>
    `,l.attachListeners({title:"🔄 Transfer Coupon",showBack:!0})}updateContent(){const e=document.getElementById("pageContent");if(!e)return;if(this.loading){e.innerHTML='<div class="loading-state" style="text-align: center; padding: 40px; color: #8892b0;">Loading...</div>';return}const t=new m({columns:[{key:"coupon_code",label:"Coupon",render:a=>`<strong>${a}</strong>`},{key:"to_user",label:"To User"},{key:"status",label:"Status",render:a=>this.getStatusBadge(a)},{key:"created_at",label:"Requested",render:a=>this.formatDate(a)},{key:"approved_at",label:"Approved",render:a=>this.formatDate(a)}],data:this.transferHistory,emptyMessage:"No transfer history"});e.innerHTML=`
      <div class="available-pins">
        <div class="count">${this.transferablePins.length}</div>
        <div class="label">Available Coupons for Transfer</div>
      </div>

      ${this.transferablePins.length>0?`
        <div class="transfer-form">
          <h4>🔄 Transfer a Coupon</h4>
          <div class="notice">
            ⚠️ Transfer requests require admin approval. The coupon will be transferred after approval.
          </div>
          <div class="form-group">
            <label>Select Coupon</label>
            <select id="pinSelect">
              <option value="">-- Select a coupon --</option>
              ${this.transferablePins.map(a=>`
                <option value="${a.id}">${a.coupon_code} (${a.coupon_type})</option>
              `).join("")}
            </select>
          </div>
          <div class="form-group">
            <label>Recipient MNR ID</label>
            <input type="text" id="recipientInput" placeholder="Enter recipient's MNR ID" value="${this.recipientId}" />
          </div>
          <button class="btn-transfer" id="transferBtn" ${!this.selectedPin||!this.recipientId?"disabled":""}>
            Request Transfer
          </button>
        </div>
      `:`
        <div class="notice">
          You don't have any active coupons available for transfer.
        </div>
      `}

      <div class="section-title">📋 Transfer History</div>
      
      <div class="table-summary-bar">
        <span>Total <span class="count">${this.transferHistory.length}</span> transfers</span>
      </div>
      ${t.render()}
    `,this.attachListeners()}attachListeners(){const e=document.getElementById("pinSelect"),t=document.getElementById("recipientInput"),a=document.getElementById("transferBtn");e?.addEventListener("change",()=>{this.selectedPin=e.value||null,this.updateButtonState()}),t?.addEventListener("input",()=>{this.recipientId=t.value.trim(),this.updateButtonState()}),a?.addEventListener("click",()=>this.requestTransfer())}updateButtonState(){const e=document.getElementById("transferBtn");e&&(e.disabled=!this.selectedPin||!this.recipientId)}async requestTransfer(){if(!(!this.selectedPin||!this.recipientId))try{const e=await d.post("/coupon-transfers/user-to-user",{coupon_id:this.selectedPin,to_user_id:this.recipientId});e.success?(alert("Transfer request submitted successfully!"),this.selectedPin=null,this.recipientId="",await this.loadData()):alert(e.error||"Failed to submit transfer request")}catch(e){console.error("[MNRCouponTransfer] Transfer failed:",e),alert("Failed to submit transfer request")}}getStatusBadge(e){const t=e.toLowerCase();return t==="approved"||t==="completed"?'<span class="badge badge-success">Approved</span>':t==="pending"?'<span class="badge badge-warning">Pending</span>':t==="rejected"?'<span class="badge badge-danger">Rejected</span>':`<span class="badge badge-secondary">${e}</span>`}formatDate(e){if(!e)return"-";try{return new Date(e).toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"numeric"})}catch{return e}}}class $e{container;members=[];loading=!0;showFilters=!1;page=1;totalPages=1;totalCount=0;sortColumn="registration_date";sortDirection="desc";filters={name:"",status_filter:"",package:"",position:"",level:"",coupon_status:"",start_date:"",end_date:""};constructor(e){this.container=e}async init(){this.render(),await this.loadMembers()}async loadMembers(){this.loading=!0,this.updateContent();try{const e=new URLSearchParams;e.append("page",this.page.toString()),e.append("page_size","50"),this.filters.name&&e.append("name",this.filters.name),this.filters.status_filter&&e.append("status_filter",this.filters.status_filter),this.filters.package&&e.append("package",this.filters.package),this.filters.position&&e.append("position",this.filters.position),this.filters.level&&e.append("level",this.filters.level),this.filters.coupon_status&&e.append("coupon_status",this.filters.coupon_status),this.filters.start_date&&e.append("start_date",this.filters.start_date),this.filters.end_date&&e.append("end_date",this.filters.end_date);const t=await d.get(`/users/team/all-members?${e}`);t.success&&t.data&&(this.members=(t.data.members||[]).map(a=>({mnr_id:a.mnr_id||a.user_id||"",name:a.name||"",package:a.package||a.package_type||this.getPackageFromPoints(a.package_points),position:a.side||a.position||"",level:a.level||0,registration_date:a.registration_date,activation_date:a.activation_date,status:a.activation_date?"Active":"Inactive",coupon_status:a.coupon_status||"N/A"})),this.totalCount=t.data.total||this.members.length,this.totalPages=t.data.total_pages||1)}catch(e){console.error("[MNRMembersAll] Failed to load:",e)}this.loading=!1,this.updateContent()}getPackageFromPoints(e){return e?e>=1e5?"Platinum":e>=5e4?"Diamond":e>=25e3?"Star":e>=1e4?"Loyal":"Blue":"None"}render(){this.container.innerHTML=`
      <style>
        ${m.getStyles()}
        .mnr-members-page { padding: 16px; }
        .filter-toggle-btn {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 10px 16px;
          background: rgba(100, 210, 255, 0.1);
          border: 1px solid rgba(100, 210, 255, 0.3);
          border-radius: 8px;
          color: #64d2ff;
          font-size: 14px;
          cursor: pointer;
          margin-bottom: 12px;
        }
        .filter-count {
          background: #ef4444;
          color: white;
          padding: 2px 8px;
          border-radius: 10px;
          font-size: 11px;
          display: none;
        }
        .filters-panel {
          display: none;
          background: rgba(22, 33, 62, 0.8);
          border-radius: 8px;
          padding: 16px;
          margin-bottom: 16px;
        }
        .filters-panel.show { display: block; }
        .filter-grid {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 12px;
        }
        .filter-group label {
          display: block;
          font-size: 11px;
          color: #8892b0;
          text-transform: uppercase;
          margin-bottom: 4px;
        }
        .filter-group input, .filter-group select {
          width: 100%;
          padding: 8px 12px;
          background: rgba(13, 27, 42, 0.8);
          border: 1px solid rgba(255,255,255,0.1);
          border-radius: 6px;
          color: #e6f1ff;
          font-size: 13px;
        }
        .filter-actions {
          display: flex;
          gap: 12px;
          margin-top: 16px;
        }
        .filter-actions button {
          flex: 1;
          padding: 10px;
          border-radius: 6px;
          font-size: 13px;
          cursor: pointer;
        }
        .btn-apply {
          background: #64d2ff;
          border: none;
          color: #0d1b2a;
          font-weight: 600;
        }
        .btn-clear {
          background: transparent;
          border: 1px solid rgba(255,255,255,0.2);
          color: #8892b0;
        }
      </style>
      ${l.render({title:"👥 All Connections",showBack:!0})}
      <div class="mnr-members-page">
        <button class="filter-toggle-btn" id="toggleFiltersBtn">
          <span>🔍 Filter Options</span>
          <span class="filter-count" id="filterCount">0</span>
        </button>
        
        <div class="filters-panel" id="filtersPanel">
          <div class="filter-grid">
            <div class="filter-group">
              <label>Name</label>
              <input type="text" id="filterName" placeholder="Search name" value="${this.filters.name}">
            </div>
            <div class="filter-group">
              <label>Status</label>
              <select id="filterStatus">
                <option value="">All Status</option>
                <option value="active" ${this.filters.status_filter==="active"?"selected":""}>Active</option>
                <option value="inactive" ${this.filters.status_filter==="inactive"?"selected":""}>Inactive</option>
              </select>
            </div>
            <div class="filter-group">
              <label>Package</label>
              <select id="filterPackage">
                <option value="">All Packages</option>
                <option value="Platinum" ${this.filters.package==="Platinum"?"selected":""}>Platinum</option>
                <option value="Diamond" ${this.filters.package==="Diamond"?"selected":""}>Diamond</option>
                <option value="Star" ${this.filters.package==="Star"?"selected":""}>Star</option>
                <option value="Loyal" ${this.filters.package==="Loyal"?"selected":""}>Loyal</option>
                <option value="Blue" ${this.filters.package==="Blue"?"selected":""}>Blue</option>
              </select>
            </div>
            <div class="filter-group">
              <label>Group</label>
              <select id="filterPosition">
                <option value="">All Groups</option>
                <option value="left" ${this.filters.position==="left"?"selected":""}>Group A</option>
                <option value="right" ${this.filters.position==="right"?"selected":""}>Group B</option>
              </select>
            </div>
            <div class="filter-group">
              <label>Level</label>
              <select id="filterLevel">
                <option value="">All Levels</option>
                ${[1,2,3,4,5,6,7,8,9,10].map(e=>`<option value="${e}" ${this.filters.level===e.toString()?"selected":""}>Level ${e}</option>`).join("")}
              </select>
            </div>
            <div class="filter-group">
              <label>Coupon Status</label>
              <select id="filterCouponStatus">
                <option value="">All</option>
                <option value="active" ${this.filters.coupon_status==="active"?"selected":""}>Active</option>
                <option value="used" ${this.filters.coupon_status==="used"?"selected":""}>Used</option>
              </select>
            </div>
            <div class="filter-group">
              <label>Start Date</label>
              <input type="date" id="filterStartDate" value="${this.filters.start_date}">
            </div>
            <div class="filter-group">
              <label>End Date</label>
              <input type="date" id="filterEndDate" value="${this.filters.end_date}">
            </div>
          </div>
          <div class="filter-actions">
            <button class="btn-apply" id="applyFiltersBtn">Apply Filters</button>
            <button class="btn-clear" id="clearFiltersBtn">Clear</button>
          </div>
        </div>

        <div id="pageContent"></div>
      </div>
    `,this.attachListeners()}attachListeners(){l.attachListeners({title:"👥 All Connections",showBack:!0}),document.getElementById("toggleFiltersBtn")?.addEventListener("click",()=>{this.showFilters=!this.showFilters,document.getElementById("filtersPanel")?.classList.toggle("show",this.showFilters)}),document.getElementById("applyFiltersBtn")?.addEventListener("click",()=>{this.collectFilters(),this.page=1,this.loadMembers()}),document.getElementById("clearFiltersBtn")?.addEventListener("click",()=>{this.filters={name:"",status_filter:"",package:"",position:"",level:"",coupon_status:"",start_date:"",end_date:""},this.page=1,this.render(),this.loadMembers()})}collectFilters(){this.filters.name=document.getElementById("filterName")?.value||"",this.filters.status_filter=document.getElementById("filterStatus")?.value||"",this.filters.package=document.getElementById("filterPackage")?.value||"",this.filters.position=document.getElementById("filterPosition")?.value||"",this.filters.level=document.getElementById("filterLevel")?.value||"",this.filters.coupon_status=document.getElementById("filterCouponStatus")?.value||"",this.filters.start_date=document.getElementById("filterStartDate")?.value||"",this.filters.end_date=document.getElementById("filterEndDate")?.value||"";const e=Object.values(this.filters).filter(a=>a).length,t=document.getElementById("filterCount");t&&(t.textContent=e.toString(),t.style.display=e>0?"inline-flex":"none")}handleSort(e){this.sortColumn===e?this.sortDirection=this.sortDirection==="asc"?"desc":"asc":(this.sortColumn=e,this.sortDirection="asc"),this.sortMembers(),this.updateContent()}sortMembers(){this.members.sort((e,t)=>{let a,i;switch(this.sortColumn){case"name":a=e.name.toLowerCase(),i=t.name.toLowerCase();break;case"mnr_id":a=e.mnr_id,i=t.mnr_id;break;case"package":const n={Platinum:5,Diamond:4,Star:3,Loyal:2,Blue:1,None:0};a=n[e.package]||0,i=n[t.package]||0;break;case"position":a=e.position,i=t.position;break;case"level":a=e.level,i=t.level;break;case"registration_date":a=e.registration_date?new Date(e.registration_date).getTime():0,i=t.registration_date?new Date(t.registration_date).getTime():0;break;case"activation_date":a=e.activation_date?new Date(e.activation_date).getTime():0,i=t.activation_date?new Date(t.activation_date).getTime():0;break;case"status":a=e.status==="Active"?1:0,i=t.status==="Active"?1:0;break;default:return 0}return a<i?this.sortDirection==="asc"?-1:1:a>i?this.sortDirection==="asc"?1:-1:0})}updateContent(){const e=document.getElementById("pageContent");if(!e)return;const t=new m({columns:[{key:"name",label:"Name",sortable:!0,render:a=>`<strong>${a}</strong>`},{key:"mnr_id",label:"MNR ID",sortable:!0},{key:"package",label:"Package",sortable:!0,render:a=>this.getPackageBadge(a)},{key:"position",label:"Group",sortable:!0,render:a=>{const i=(a||"").toLowerCase();return i==="left"?"Group A":i==="right"?"Group B":a||"-"}},{key:"level",label:"Level",sortable:!0,render:a=>`L${a}`},{key:"registration_date",label:"Reg Date",sortable:!0,render:a=>this.formatDate(a)},{key:"activation_date",label:"Act Date",sortable:!0,render:a=>this.formatDate(a)},{key:"status",label:"Status",sortable:!0,render:a=>this.getStatusBadge(a)}],data:this.members,sortColumn:this.sortColumn,sortDirection:this.sortDirection,loading:this.loading,emptyMessage:Object.values(this.filters).some(a=>a)?"No members match your filters":"Your team members will appear here"});e.innerHTML=`
      <div class="table-summary-bar">
        <span>Showing <span class="count">${this.members.length}</span> of <span class="count">${this.totalCount}</span> members</span>
        ${this.totalPages>1?`<span>Page ${this.page}/${this.totalPages}</span>`:""}
      </div>
      ${t.render()}
      ${this.totalPages>1?`
        <div class="table-pagination">
          <button id="prevPageBtn" ${this.page===1?"disabled":""}>Previous</button>
          <span class="page-info">${this.page} / ${this.totalPages}</span>
          <button id="nextPageBtn" ${this.page===this.totalPages?"disabled":""}>Next</button>
        </div>
      `:""}
    `,m.attachSortListeners(e,a=>this.handleSort(a)),document.getElementById("prevPageBtn")?.addEventListener("click",()=>{this.page>1&&(this.page--,this.loadMembers())}),document.getElementById("nextPageBtn")?.addEventListener("click",()=>{this.page<this.totalPages&&(this.page++,this.loadMembers())})}getPackageBadge(e){return`<span class="badge ${{Platinum:"badge-platinum",Diamond:"badge-diamond",Star:"badge-warning",Loyal:"badge-info",Blue:"badge-primary"}[e]||"badge-secondary"}">${e}</span>`}getStatusBadge(e){return e==="Active"?'<span class="badge badge-success">Active</span>':'<span class="badge badge-secondary">Inactive</span>'}formatDate(e){if(!e)return"-";try{return new Date(e).toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"numeric"})}catch{return e}}}class Ce{container;treeData=null;loading=!0;currentUserId="";initialUserId="";totalMembers=0;navigationHistory=[];currentDepth=0;MAX_NAVIGATION_DEPTH=7;constructor(e){this.container=e}async init(){this.render(),await this.loadTree(),this.initialUserId=this.currentUserId,this.currentDepth=0}async loadTree(e){this.loading=!0,this.updateContent();try{const t=e?`/users/team/binary-tree?user_id=${encodeURIComponent(e)}`:"/users/team/binary-tree",a=await d.get(t);a.success&&a.data&&(this.treeData=a.data,this.currentUserId=a.data.root?.mnr_id||"",this.totalMembers=this.countAllNodes(a.data))}catch(t){console.error("[MNRMembersPicture] Failed to load:",t)}this.loading=!1,this.updateContent()}countAllNodes(e){let t=0;return e.root&&t++,e.left_child&&t++,e.right_child&&t++,e.left_child?.left_child&&t++,e.left_child?.right_child&&t++,e.right_child?.left_child&&t++,e.right_child?.right_child&&t++,t}render(){this.container.innerHTML=`
      <style>
        .picture-page { padding: 16px; min-height: 100vh; background: #0d1b2a; }
        
        .page-banner {
          background: linear-gradient(135deg, #0891b2 0%, #06b6d4 100%);
          border-radius: 12px;
          padding: 16px;
          margin-bottom: 16px;
          color: white;
        }
        .page-banner h2 { margin: 0 0 4px; font-size: 16px; }
        .page-banner p { margin: 0; font-size: 11px; opacity: 0.9; }
        
        .nav-card {
          background: rgba(22, 33, 62, 0.9);
          border-radius: 12px;
          padding: 12px 16px;
          margin-bottom: 16px;
          display: flex;
          align-items: center;
          gap: 12px;
        }
        .btn-back {
          padding: 8px 16px;
          border-radius: 8px;
          border: none;
          background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
          color: white;
          font-size: 12px;
          font-weight: 600;
          cursor: pointer;
        }
        .nav-info {
          color: #93c5fd;
          font-size: 12px;
        }
        
        .count-badges {
          display: flex;
          gap: 8px;
        }
        .count-badge {
          padding: 4px 10px;
          border-radius: 12px;
          font-size: 11px;
          font-weight: 600;
        }
        .count-badge.left {
          background: rgba(147, 51, 234, 0.3);
          color: #c4b5fd;
        }
        .count-badge.right {
          background: rgba(236, 72, 153, 0.3);
          color: #fbcfe8;
        }
        
        .tree-card {
          background: rgba(22, 33, 62, 0.9);
          border-radius: 12px;
          overflow: hidden;
        }
        .tree-header {
          background: linear-gradient(135deg, #0891b2 0%, #06b6d4 100%);
          padding: 14px 16px;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        .tree-header h5 { margin: 0; color: white; font-size: 14px; }
        .tree-header .badge {
          background: rgba(255,255,255,0.2);
          color: white;
          padding: 4px 10px;
          border-radius: 12px;
          font-size: 11px;
        }
        
        .tree-container {
          padding: 30px 16px;
          overflow-x: auto;
          background: linear-gradient(180deg, rgba(13,27,42,0.5) 0%, rgba(22,33,62,0.3) 100%);
        }
        .tree-wrapper {
          min-width: 620px;
          display: flex;
          flex-direction: column;
          align-items: center;
        }
        
        /* ========== TREE STRUCTURE ========== */
        
        /* ROOT LEVEL */
        .level-root {
          display: flex;
          justify-content: center;
          margin-bottom: 0;
        }
        
        /* Vertical line from root */
        .connector-root-down {
          width: 4px;
          height: 35px;
          background: linear-gradient(to bottom, #10b981, #059669);
          margin: 0 auto;
          border-radius: 2px;
        }
        
        /* Horizontal split bar */
        .connector-split {
          width: 280px;
          height: 4px;
          background: linear-gradient(to right, #9333ea 0%, #10b981 50%, #ec4899 100%);
          margin: 0 auto;
          border-radius: 2px;
          position: relative;
        }
        .connector-split::before,
        .connector-split::after {
          content: '';
          position: absolute;
          width: 4px;
          height: 35px;
          top: 4px;
          border-radius: 2px;
        }
        .connector-split::before {
          left: 0;
          background: linear-gradient(to bottom, #9333ea, #7c3aed);
        }
        .connector-split::after {
          right: 0;
          background: linear-gradient(to bottom, #ec4899, #db2777);
        }
        
        /* LEVEL 1: Children */
        .level-children {
          display: flex;
          justify-content: center;
          gap: 160px;
          margin-top: 35px;
        }
        
        /* Connectors from Level 1 to Level 2 */
        .level-1-connectors {
          display: flex;
          justify-content: center;
          gap: 160px;
          margin-top: 20px;
        }
        .branch-connector {
          display: flex;
          flex-direction: column;
          align-items: center;
        }
        .connector-down-small {
          width: 4px;
          height: 25px;
          border-radius: 2px;
        }
        .connector-down-small.left { background: linear-gradient(to bottom, #9333ea, #7c3aed); }
        .connector-down-small.right { background: linear-gradient(to bottom, #ec4899, #db2777); }
        
        .connector-branch-split {
          width: 120px;
          height: 4px;
          border-radius: 2px;
          position: relative;
        }
        .connector-branch-split.left { background: linear-gradient(to right, #a855f7, #9333ea, #a855f7); }
        .connector-branch-split.right { background: linear-gradient(to right, #f472b6, #ec4899, #f472b6); }
        .connector-branch-split::before,
        .connector-branch-split::after {
          content: '';
          position: absolute;
          width: 4px;
          height: 25px;
          top: 4px;
          border-radius: 2px;
        }
        .connector-branch-split.left::before,
        .connector-branch-split.left::after { background: #9333ea; }
        .connector-branch-split.right::before,
        .connector-branch-split.right::after { background: #ec4899; }
        .connector-branch-split::before { left: 0; }
        .connector-branch-split::after { right: 0; }
        
        /* LEVEL 2: Grandchildren */
        .level-grandchildren {
          display: flex;
          justify-content: center;
          gap: 40px;
          margin-top: 25px;
        }
        .grandchild-group {
          display: flex;
          gap: 16px;
        }
        .grandchild-spacer {
          width: 90px;
        }
        
        /* ========== NODE STYLES ========== */
        .tree-node {
          width: 125px;
          background: white;
          border-radius: 14px;
          padding: 14px 10px 12px;
          text-align: center;
          box-shadow: 0 6px 20px rgba(0,0,0,0.25);
          cursor: pointer;
          transition: transform 0.2s, box-shadow 0.2s;
          border: 3px solid transparent;
          position: relative;
        }
        .tree-node:active { transform: scale(0.96); box-shadow: 0 3px 10px rgba(0,0,0,0.2); }
        .tree-node.active {
          background: linear-gradient(135deg, #059669 0%, #10b981 100%);
        }
        .tree-node.inactive { background: #f3f4f6; }
        .tree-node.root { border-color: #10b981; box-shadow: 0 6px 25px rgba(16,185,129,0.35); }
        .tree-node.left { border-color: #9333ea; box-shadow: 0 6px 20px rgba(147,51,234,0.3); }
        .tree-node.right { border-color: #ec4899; box-shadow: 0 6px 20px rgba(236,72,153,0.3); }
        
        .node-name {
          font-weight: 700;
          font-size: 11px;
          margin-bottom: 3px;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        .tree-node.active .node-name { color: white; }
        .tree-node:not(.active) .node-name { color: #1f2937; }
        
        .node-id { font-size: 9px; margin-bottom: 6px; font-weight: 600; }
        .tree-node.root .node-id { color: #059669; }
        .tree-node.left .node-id { color: #9333ea; }
        .tree-node.right .node-id { color: #ec4899; }
        .tree-node.active .node-id { color: rgba(255,255,255,0.9); }
        
        .status-badge {
          display: inline-block;
          padding: 2px 8px;
          border-radius: 10px;
          font-size: 8px;
          font-weight: 700;
          margin-bottom: 6px;
          text-transform: uppercase;
        }
        .status-badge.active { background: #10b981; color: white; }
        .status-badge.inactive { background: #9ca3af; color: white; }
        
        .node-package {
          padding: 4px 8px;
          border-radius: 6px;
          font-size: 8px;
          font-weight: 700;
          color: white;
          text-transform: uppercase;
        }
        .tree-node.root .node-package { background: #059669; }
        .tree-node.left .node-package { background: #9333ea; }
        .tree-node.right .node-package { background: #ec4899; }
        
        .node-position {
          margin-top: 5px;
          font-size: 8px;
          font-weight: 800;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }
        .tree-node.root .node-position { color: #059669; }
        .tree-node.left .node-position { color: #9333ea; }
        .tree-node.right .node-position { color: #ec4899; }
        .tree-node.active .node-position { color: rgba(255,255,255,0.8); }
        
        /* Empty Slot */
        .empty-slot {
          width: 125px;
          border: 3px dashed #4b5563;
          border-radius: 14px;
          padding: 18px 10px;
          text-align: center;
          background: rgba(75, 85, 99, 0.15);
        }
        .empty-slot .icon { font-size: 20px; margin-bottom: 4px; }
        .empty-slot .label { font-size: 9px; color: #9ca3af; font-weight: 500; }
        .empty-slot .position { font-size: 8px; font-weight: 700; margin-top: 3px; }
        .empty-slot.left { border-color: rgba(147,51,234,0.4); }
        .empty-slot.right { border-color: rgba(236,72,153,0.4); }
        .empty-slot.left .position { color: #a855f7; }
        .empty-slot.right .position { color: #f472b6; }
        
        /* Legend */
        .tree-legend {
          display: flex;
          justify-content: center;
          gap: 20px;
          margin-top: 30px;
          padding: 16px;
          background: rgba(13,27,42,0.5);
          border-radius: 10px;
        }
        .legend-item {
          display: flex;
          align-items: center;
          gap: 6px;
          font-size: 10px;
          color: #94a3b8;
          font-weight: 500;
        }
        .legend-dot {
          width: 14px;
          height: 14px;
          border-radius: 50%;
          border: 2px solid;
        }
        .legend-dot.root { background: #10b981; border-color: #059669; }
        .legend-dot.left { background: #9333ea; border-color: #7c3aed; }
        .legend-dot.right { background: #ec4899; border-color: #db2777; }
        
        .loading-state, .empty-state {
          text-align: center;
          padding: 60px 20px;
          color: #8892b0;
        }
        .empty-state .icon { font-size: 48px; margin-bottom: 16px; opacity: 0.5; }
        .empty-state h3 { color: #e6f1ff; margin: 0 0 8px; font-size: 16px; }
        .empty-state p { margin: 0; font-size: 13px; }
      </style>
      ${l.render({title:"🌳 Connections Gallery",showBack:!0})}
      <div class="picture-page" id="pageContent">
        <div class="loading-state">Loading tree structure...</div>
      </div>
    `,l.attachListeners({title:"🌳 Connections Gallery",showBack:!0})}updateContent(){const e=document.getElementById("pageContent");if(!e)return;if(this.loading){e.innerHTML='<div class="loading-state">Loading tree structure...</div>';return}const t=this.navigationHistory.length>0;e.innerHTML=`
      <div class="page-banner">
        <h2>🌳 Connections Gallery</h2>
        <p>Tap any team member to navigate their tree</p>
      </div>

      ${t?`
        <div class="nav-card">
          <button class="btn-back" id="btnGoBack">⬅ Go Back</button>
          <span class="nav-info">Viewing: ${this.currentUserId}</span>
        </div>
      `:""}

      ${this.treeData&&this.treeData.root?this.renderTreeView():this.renderEmptyState()}
    `,this.attachListeners()}renderTreeView(){if(!this.treeData)return"";const e=this.treeData.root,t=this.treeData.left_child,a=this.treeData.right_child,i=t||a,n=t?.left_child||t?.right_child||a?.left_child||a?.right_child,s=this.treeData.left_count||0,r=this.treeData.right_count||0,o=this.treeData.left_active_count||0,c=this.treeData.right_active_count||0;return`
      <div class="tree-card">
        <div class="tree-header">
          <h5>📊 Binary Tree Structure</h5>
          <div class="count-badges">
            <span class="count-badge left">L: ${s} (${o})</span>
            <span class="count-badge right">R: ${r} (${c})</span>
          </div>
        </div>
        <div class="tree-container">
          <div class="tree-wrapper">
            
            <!-- LEVEL 0: ROOT -->
            <div class="level-root">
              ${this.renderNode(e,"root")}
            </div>
            
            ${i?`
              <!-- Connector: Root to Children -->
              <div class="connector-root-down"></div>
              <div class="connector-split"></div>
              
              <!-- LEVEL 1: LEFT & RIGHT CHILDREN -->
              <div class="level-children">
                ${t?this.renderNode(t,"left"):this.renderEmptySlot("Left","left")}
                ${a?this.renderNode(a,"right"):this.renderEmptySlot("Right","right")}
              </div>
            `:""}
            
            ${n?`
              <!-- Connectors: Children to Grandchildren -->
              <div class="level-1-connectors">
                <div class="branch-connector">
                  <div class="connector-down-small left"></div>
                  <div class="connector-branch-split left"></div>
                </div>
                <div class="branch-connector">
                  <div class="connector-down-small right"></div>
                  <div class="connector-branch-split right"></div>
                </div>
              </div>
              
              <!-- LEVEL 2: GRANDCHILDREN -->
              <div class="level-grandchildren">
                <div class="grandchild-group">
                  ${t?.left_child?this.renderNode(t.left_child,"left"):this.renderEmptySlot("LL","left")}
                  ${t?.right_child?this.renderNode(t.right_child,"left"):this.renderEmptySlot("LR","left")}
                </div>
                <div class="grandchild-spacer"></div>
                <div class="grandchild-group">
                  ${a?.left_child?this.renderNode(a.left_child,"right"):this.renderEmptySlot("RL","right")}
                  ${a?.right_child?this.renderNode(a.right_child,"right"):this.renderEmptySlot("RR","right")}
                </div>
              </div>
            `:""}
            
            <!-- Legend -->
            <div class="tree-legend">
              <div class="legend-item"><div class="legend-dot root"></div> Root</div>
              <div class="legend-item"><div class="legend-dot left"></div> Left Branch</div>
              <div class="legend-item"><div class="legend-dot right"></div> Right Branch</div>
            </div>
            
          </div>
        </div>
      </div>
    `}renderNode(e,t){const a=e.status==="Active",i=a?"active":"inactive",n=t==="left"?"LEFT":t==="right"?"RIGHT":"ROOT",s=e.name.length>11?e.name.substring(0,9)+"..":e.name;return`
      <div class="tree-node ${i} ${t}" data-mnr-id="${this.escapeHtml(e.mnr_id)}" onclick="window.viewUserTree && window.viewUserTree('${this.escapeHtml(e.mnr_id)}')">
        <div class="node-name">${this.escapeHtml(s)}</div>
        <div class="node-id">${this.escapeHtml(e.mnr_id)}</div>
        <span class="status-badge ${i}">${a?"Active":"Inactive"}</span>
        <div class="node-package">${this.escapeHtml(e.package||"N/A")}</div>
        <div class="node-position">${n}</div>
      </div>
    `}renderEmptySlot(e,t){return`
      <div class="empty-slot ${t}">
        <div class="icon">➕</div>
        <div class="label">Empty Slot</div>
        <div class="position">${e}</div>
      </div>
    `}renderEmptyState(){return`
      <div class="tree-card">
        <div class="tree-header">
          <h5>📊 Binary Tree Structure</h5>
          <span class="badge">0 members</span>
        </div>
        <div class="empty-state">
          <div class="icon">🌳</div>
          <h3>No Team Structure Found</h3>
          <p>This user has no team members yet.</p>
        </div>
      </div>
    `}attachListeners(){window.viewUserTree=e=>{if(e&&e!==this.currentUserId){if(this.currentDepth>=this.MAX_NAVIGATION_DEPTH){alert(`Maximum navigation depth (${this.MAX_NAVIGATION_DEPTH} levels) reached. Cannot navigate further.`);return}this.navigationHistory.push(this.currentUserId),this.currentDepth++,this.loadTree(e)}},document.getElementById("btnGoBack")?.addEventListener("click",()=>{const e=this.navigationHistory.pop();e&&(this.currentDepth=Math.max(0,this.currentDepth-1),this.loadTree(e))})}escapeHtml(e){return e?e.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#039;"):""}}class Me{container;members=[];vedHead=null;loading=!0;showFilters=!1;sortColumn="level";sortDirection="asc";filters={name:"",status_filter:"",package:"",position:"",level:"",start_date:"",end_date:""};constructor(e){this.container=e}async init(){this.render(),await this.loadMembers()}async loadMembers(){this.loading=!0,this.updateContent();try{const e=new URLSearchParams;this.filters.name&&e.append("name",this.filters.name),this.filters.status_filter&&e.append("status_filter",this.filters.status_filter),this.filters.package&&e.append("package",this.filters.package),this.filters.position&&e.append("position",this.filters.position),this.filters.level&&e.append("level",this.filters.level),this.filters.start_date&&e.append("start_date",this.filters.start_date),this.filters.end_date&&e.append("end_date",this.filters.end_date);const t=await d.get(`/users/team/ved-members?${e}`);if(t.success&&t.data){t.data.ved_head&&(this.vedHead={mnr_id:t.data.ved_head.mnr_id||t.data.ved_head.user_id||"",name:t.data.ved_head.name||"",package:t.data.ved_head.package||t.data.ved_head.package_type||"None",status:t.data.ved_head.is_active?"Active":"Inactive",activation_date:t.data.ved_head.activation_date});const a=t.data.all_ved_members||t.data.ved_members||[];this.members=a.map(i=>({mnr_id:i.mnr_id||i.user_id||"",name:i.name||"",package:i.package||i.package_type||"None",position:i.side||i.position||"",level:i.level||0,registration_date:i.registration_date,activation_date:i.activation_date,status:i.activation_date?"Active":"Inactive"}))}}catch(e){console.error("[MNRMembersVed] Failed to load:",e)}this.loading=!1,this.updateContent()}render(){this.container.innerHTML=`
      <style>
        ${m.getStyles()}
        .mnr-ved-page { padding: 16px; }
        .ved-head-card {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          border-radius: 12px;
          padding: 16px;
          margin-bottom: 16px;
          color: white;
        }
        .ved-head-card h4 { margin: 0 0 8px; font-size: 14px; opacity: 0.9; }
        .ved-head-card .name { font-size: 18px; font-weight: 600; margin-bottom: 8px; }
        .ved-head-card .details { display: flex; gap: 16px; font-size: 13px; opacity: 0.9; }
        .filter-toggle-btn {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 10px 16px;
          background: rgba(100, 210, 255, 0.1);
          border: 1px solid rgba(100, 210, 255, 0.3);
          border-radius: 8px;
          color: #64d2ff;
          font-size: 14px;
          cursor: pointer;
          margin-bottom: 12px;
        }
        .filter-count {
          background: #ef4444;
          color: white;
          padding: 2px 8px;
          border-radius: 10px;
          font-size: 11px;
          display: none;
        }
        .filters-panel {
          display: none;
          background: rgba(22, 33, 62, 0.8);
          border-radius: 8px;
          padding: 16px;
          margin-bottom: 16px;
        }
        .filters-panel.show { display: block; }
        .filter-grid {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 12px;
        }
        .filter-group label {
          display: block;
          font-size: 11px;
          color: #8892b0;
          text-transform: uppercase;
          margin-bottom: 4px;
        }
        .filter-group input, .filter-group select {
          width: 100%;
          padding: 8px 12px;
          background: rgba(13, 27, 42, 0.8);
          border: 1px solid rgba(255,255,255,0.1);
          border-radius: 6px;
          color: #e6f1ff;
          font-size: 13px;
        }
        .filter-actions {
          display: flex;
          gap: 12px;
          margin-top: 16px;
        }
        .filter-actions button {
          flex: 1;
          padding: 10px;
          border-radius: 6px;
          font-size: 13px;
          cursor: pointer;
        }
        .btn-apply {
          background: #64d2ff;
          border: none;
          color: #0d1b2a;
          font-weight: 600;
        }
        .btn-clear {
          background: transparent;
          border: 1px solid rgba(255,255,255,0.2);
          color: #8892b0;
        }
      </style>
      ${l.render({title:"👑 Leadership Group (VED)",showBack:!0})}
      <div class="mnr-ved-page">
        <div id="vedHeadSection"></div>
        
        <button class="filter-toggle-btn" id="toggleFiltersBtn">
          <span>🔍 Filter Options</span>
          <span class="filter-count" id="filterCount">0</span>
        </button>
        
        <div class="filters-panel" id="filtersPanel">
          <div class="filter-grid">
            <div class="filter-group">
              <label>Name</label>
              <input type="text" id="filterName" placeholder="Search name" value="${this.filters.name}">
            </div>
            <div class="filter-group">
              <label>Status</label>
              <select id="filterStatus">
                <option value="">All Status</option>
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
              </select>
            </div>
            <div class="filter-group">
              <label>Package</label>
              <select id="filterPackage">
                <option value="">All Packages</option>
                <option value="Platinum">Platinum</option>
                <option value="Diamond">Diamond</option>
                <option value="Star">Star</option>
                <option value="Loyal">Loyal</option>
                <option value="Blue">Blue</option>
              </select>
            </div>
            <div class="filter-group">
              <label>Group</label>
              <select id="filterPosition">
                <option value="">All Groups</option>
                <option value="left">Group A</option>
                <option value="right">Group B</option>
              </select>
            </div>
            <div class="filter-group">
              <label>Level</label>
              <select id="filterLevel">
                <option value="">All Levels</option>
                ${[1,2,3,4,5,6,7,8,9,10].map(e=>`<option value="${e}">Level ${e}</option>`).join("")}
              </select>
            </div>
            <div class="filter-group">
              <label>Start Date</label>
              <input type="date" id="filterStartDate" value="${this.filters.start_date}">
            </div>
          </div>
          <div class="filter-actions">
            <button class="btn-apply" id="applyFiltersBtn">Apply Filters</button>
            <button class="btn-clear" id="clearFiltersBtn">Clear</button>
          </div>
        </div>

        <div id="pageContent"></div>
      </div>
    `,this.attachListeners()}attachListeners(){l.attachListeners({title:"👑 Leadership Group (VED)",showBack:!0}),document.getElementById("toggleFiltersBtn")?.addEventListener("click",()=>{this.showFilters=!this.showFilters,document.getElementById("filtersPanel")?.classList.toggle("show",this.showFilters)}),document.getElementById("applyFiltersBtn")?.addEventListener("click",()=>{this.collectFilters(),this.loadMembers()}),document.getElementById("clearFiltersBtn")?.addEventListener("click",()=>{this.filters={name:"",status_filter:"",package:"",position:"",level:"",start_date:"",end_date:""},this.render(),this.loadMembers()})}collectFilters(){this.filters.name=document.getElementById("filterName")?.value||"",this.filters.status_filter=document.getElementById("filterStatus")?.value||"",this.filters.package=document.getElementById("filterPackage")?.value||"",this.filters.position=document.getElementById("filterPosition")?.value||"",this.filters.level=document.getElementById("filterLevel")?.value||"",this.filters.start_date=document.getElementById("filterStartDate")?.value||"";const e=Object.values(this.filters).filter(a=>a).length,t=document.getElementById("filterCount");t&&(t.textContent=e.toString(),t.style.display=e>0?"inline-flex":"none")}handleSort(e){this.sortColumn===e?this.sortDirection=this.sortDirection==="asc"?"desc":"asc":(this.sortColumn=e,this.sortDirection="asc"),this.sortMembers(),this.updateContent()}sortMembers(){this.members.sort((e,t)=>{let a,i;switch(this.sortColumn){case"name":a=e.name.toLowerCase(),i=t.name.toLowerCase();break;case"mnr_id":a=e.mnr_id,i=t.mnr_id;break;case"level":a=e.level,i=t.level;break;case"registration_date":a=e.registration_date?new Date(e.registration_date).getTime():0,i=t.registration_date?new Date(t.registration_date).getTime():0;break;case"activation_date":a=e.activation_date?new Date(e.activation_date).getTime():0,i=t.activation_date?new Date(t.activation_date).getTime():0;break;case"status":a=e.status==="Active"?1:0,i=t.status==="Active"?1:0;break;default:return 0}return a<i?this.sortDirection==="asc"?-1:1:a>i?this.sortDirection==="asc"?1:-1:0})}updateContent(){const e=document.getElementById("vedHeadSection");e&&this.vedHead&&(e.innerHTML=`
        <div class="ved-head-card">
          <h4>Ved Head</h4>
          <div class="name">${this.vedHead.name}</div>
          <div class="details">
            <span>${this.vedHead.mnr_id}</span>
            <span>${this.vedHead.package}</span>
            <span>${this.vedHead.status}</span>
          </div>
        </div>
      `);const t=document.getElementById("pageContent");if(!t)return;const a=new m({columns:[{key:"name",label:"Name",sortable:!0,render:i=>`<strong>${i}</strong>`},{key:"mnr_id",label:"MNR ID",sortable:!0},{key:"package",label:"Package",sortable:!0,render:i=>this.getPackageBadge(i)},{key:"position",label:"Group",sortable:!0,render:i=>{const n=(i||"").toLowerCase();return n==="left"?"Group A":n==="right"?"Group B":i||"-"}},{key:"level",label:"Level",sortable:!0,render:i=>`L${i}`},{key:"registration_date",label:"Reg Date",sortable:!0,render:i=>this.formatDate(i)},{key:"activation_date",label:"Act Date",sortable:!0,render:i=>this.formatDate(i)},{key:"status",label:"Status",sortable:!0,render:i=>this.getStatusBadge(i)}],data:this.members,sortColumn:this.sortColumn,sortDirection:this.sortDirection,loading:this.loading,emptyMessage:"No Ved members found"});t.innerHTML=`
      <div class="table-summary-bar">
        <span>Total <span class="count">${this.members.length}</span> Ved members</span>
      </div>
      ${a.render()}
    `,m.attachSortListeners(t,i=>this.handleSort(i))}getPackageBadge(e){return`<span class="badge ${{Platinum:"badge-platinum",Diamond:"badge-diamond",Star:"badge-warning",Loyal:"badge-info",Blue:"badge-primary"}[e]||"badge-secondary"}">${e}</span>`}getStatusBadge(e){return e==="Active"?'<span class="badge badge-success">Active</span>':'<span class="badge badge-secondary">Inactive</span>'}formatDate(e){if(!e)return"-";try{return new Date(e).toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"numeric"})}catch{return e}}}class Be{container;points={current_balance:0,total_allocated:0,total_consumed:0};summary={total_earnings:0,myntreal_count:0,zynova_count:0,pending_count:0};incentives=[];pointsHistory=[];loading=!0;activeTab="incentives";constructor(e){this.container=e}async init(){this.render(),await this.loadData()}async loadData(){this.loading=!0,this.updateContent();try{const[e,t,a]=await Promise.all([d.get("/myntreal/points/me"),d.get("/myntreal/earnings-summary"),d.get("/myntreal/my-incentives")]);if(e.success&&e.data&&(this.points={current_balance:e.data.current_balance||0,total_allocated:e.data.total_allocated||0,total_consumed:e.data.total_consumed||0}),t.success&&t.data&&(this.summary={total_earnings:t.data.total_earnings||0,myntreal_count:t.data.myntreal_count||0,zynova_count:t.data.zynova_count||0,pending_count:t.data.pending_count||0}),a.success&&a.data){const i=a.data.data||a.data||[];this.incentives=Array.isArray(i)?i:[]}}catch(e){console.error("[MNREarningsSummary] Failed to load:",e)}this.loading=!1,this.updateContent()}async loadPointsHistory(){try{const e=await d.get("/myntreal/points/my-history");if(e.success&&e.data){const t=e.data.data||e.data||[];this.pointsHistory=Array.isArray(t)?t:[]}}catch(e){console.error("[MNREarningsSummary] Failed to load points history:",e)}this.updateTabContent()}render(){this.container.innerHTML=`
      <style>
        .earnings-page {
          background: linear-gradient(135deg, #0a1929 0%, #0d2137 100%);
          min-height: 100vh;
        }
        .earnings-content { padding: 16px; }

        .points-display {
          background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
          border-radius: 12px;
          padding: 24px;
          text-align: center;
          margin-bottom: 16px;
        }
        .points-value {
          font-size: 36px;
          font-weight: 700;
          color: #92400e;
        }
        .points-label {
          color: #b45309;
          font-size: 14px;
          margin-top: 4px;
        }
        .points-breakdown {
          margin-top: 16px;
          display: flex;
          justify-content: center;
          gap: 32px;
        }
        .breakdown-item { text-align: center; }
        .breakdown-value {
          font-size: 18px;
          font-weight: 600;
          color: #92400e;
        }
        .breakdown-label {
          font-size: 11px;
          color: #b45309;
        }

        .summary-cards {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 12px;
          margin-bottom: 16px;
        }
        @media (min-width: 480px) {
          .summary-cards { grid-template-columns: repeat(4, 1fr); }
        }
        .summary-card {
          background: rgba(255, 255, 255, 0.08);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 12px;
          padding: 16px;
          text-align: center;
        }
        .summary-card .card-icon {
          font-size: 20px;
          margin-bottom: 8px;
        }
        .summary-card .card-value {
          font-size: 20px;
          font-weight: 700;
          color: #ffffff;
        }
        .summary-card .card-value.green { color: #10b981; }
        .summary-card .card-value.gold { color: #f59e0b; }
        .summary-card .card-value.blue { color: #3b82f6; }
        .summary-card .card-value.purple { color: #8b5cf6; }
        .summary-card .card-label {
          font-size: 11px;
          color: #94a3b8;
          margin-top: 4px;
        }

        .tabs-container {
          margin-bottom: 16px;
        }
        .tabs-row {
          display: flex;
          background: rgba(255, 255, 255, 0.08);
          border-radius: 10px;
          padding: 4px;
          gap: 4px;
        }
        .tab-btn {
          flex: 1;
          padding: 10px 16px;
          border: none;
          border-radius: 8px;
          font-size: 13px;
          font-weight: 500;
          color: #94a3b8;
          background: transparent;
          cursor: pointer;
          transition: all 0.2s;
        }
        .tab-btn.active {
          background: rgba(255, 255, 255, 0.15);
          color: #ffffff;
          font-weight: 600;
        }

        .data-card {
          background: rgba(255, 255, 255, 0.06);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 12px;
          overflow: hidden;
        }
        .data-card-header {
          padding: 14px 16px;
          border-bottom: 1px solid rgba(255, 255, 255, 0.08);
          color: #e2e8f0;
          font-size: 14px;
          font-weight: 600;
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .table-container {
          overflow-x: auto;
          -webkit-overflow-scrolling: touch;
        }
        .earnings-table {
          width: 100%;
          min-width: 500px;
          border-collapse: collapse;
          font-size: 13px;
        }
        .earnings-table th {
          padding: 10px 12px;
          text-align: left;
          font-weight: 600;
          color: #94a3b8;
          font-size: 11px;
          text-transform: uppercase;
          border-bottom: 1px solid rgba(255, 255, 255, 0.08);
          background: rgba(255, 255, 255, 0.03);
        }
        .earnings-table th.text-end { text-align: right; }
        .earnings-table th.text-center { text-align: center; }
        .earnings-table td {
          padding: 12px;
          border-bottom: 1px solid rgba(255, 255, 255, 0.05);
          color: #e2e8f0;
          vertical-align: middle;
        }
        .earnings-table td.text-end { text-align: right; }
        .earnings-table td.text-center { text-align: center; }
        .earnings-table tbody tr:hover {
          background: rgba(255, 255, 255, 0.03);
        }

        .system-badge {
          display: inline-block;
          padding: 3px 8px;
          border-radius: 4px;
          font-size: 10px;
          font-weight: 600;
          text-transform: uppercase;
        }
        .system-myntreal { background: rgba(245, 158, 11, 0.2); color: #f59e0b; }
        .system-zynova { background: rgba(59, 130, 246, 0.2); color: #60a5fa; }

        .status-badge {
          display: inline-block;
          padding: 3px 10px;
          border-radius: 12px;
          font-size: 11px;
          font-weight: 500;
        }
        .status-pending { background: rgba(245, 158, 11, 0.15); color: #fbbf24; }
        .status-approved { background: rgba(16, 185, 129, 0.15); color: #34d399; }
        .status-rejected { background: rgba(239, 68, 68, 0.15); color: #f87171; }

        .amount-positive { color: #10b981; font-weight: 700; }
        .amount-credit { color: #10b981; }
        .amount-debit { color: #f87171; }

        .type-badge {
          display: inline-block;
          padding: 3px 8px;
          border-radius: 4px;
          font-size: 11px;
          font-weight: 500;
          background: rgba(148, 163, 184, 0.15);
          color: #94a3b8;
        }

        .empty-state {
          text-align: center;
          padding: 40px 20px;
          color: #64748b;
        }
        .empty-state svg { margin-bottom: 12px; opacity: 0.5; }

        .loading-state {
          text-align: center;
          padding: 60px 20px;
          color: #8892b0;
        }

        .back-btn {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          margin-top: 16px;
          padding: 10px 16px;
          background: rgba(255, 255, 255, 0.1);
          border: 1px solid rgba(255, 255, 255, 0.2);
          border-radius: 8px;
          color: #94a3b8;
          font-size: 13px;
          cursor: pointer;
        }
      </style>

      ${l.render({title:"📊 Facilitation Summary",showBack:!0})}
      <div class="earnings-page">
        <div class="earnings-content" id="pageContent">
          <div class="loading-state">Loading earnings data...</div>
        </div>
      </div>
    `,l.attachListeners({title:"📊 Facilitation Summary",showBack:!0})}updateContent(){const e=document.getElementById("pageContent");if(e){if(this.loading){e.innerHTML='<div class="loading-state">Loading earnings data...</div>';return}e.innerHTML=`
      <!-- Points Display -->
      <div class="points-display">
        <div class="points-value">${this.formatIndian(this.points.current_balance)}</div>
        <div class="points-label">Available MNR Points</div>
        <div class="points-breakdown">
          <div class="breakdown-item">
            <div class="breakdown-value">${this.formatIndian(this.points.total_allocated)}</div>
            <div class="breakdown-label">Total Allocated</div>
          </div>
          <div class="breakdown-item">
            <div class="breakdown-value">${this.formatIndian(this.points.total_consumed)}</div>
            <div class="breakdown-label">Used</div>
          </div>
        </div>
      </div>

      <!-- Summary Cards -->
      <div class="summary-cards">
        <div class="summary-card">
          <div class="card-icon">💰</div>
          <div class="card-value green">₹${this.formatIndian(this.summary.total_earnings)}</div>
          <div class="card-label">Total Earnings</div>
        </div>
        <div class="summary-card">
          <div class="card-icon">⭐</div>
          <div class="card-value gold">${this.summary.myntreal_count}</div>
          <div class="card-label">MyntReal Incentives</div>
        </div>
        <div class="summary-card">
          <div class="card-icon">🔗</div>
          <div class="card-value blue">${this.summary.zynova_count}</div>
          <div class="card-label">Zynova Incentives</div>
        </div>
        <div class="summary-card">
          <div class="card-icon">⏳</div>
          <div class="card-value purple">${this.summary.pending_count}</div>
          <div class="card-label">Pending Approval</div>
        </div>
      </div>

      <!-- Tabs -->
      <div class="tabs-container">
        <div class="tabs-row">
          <button class="tab-btn ${this.activeTab==="incentives"?"active":""}" id="tabIncentives">My Incentives</button>
          <button class="tab-btn ${this.activeTab==="points"?"active":""}" id="tabPoints">Points History</button>
        </div>
      </div>

      <!-- Data Table -->
      <div class="data-card">
        <div class="data-card-header" id="tableTitle">
          ${this.activeTab==="incentives"?"📋 My Incentives":"📜 Points History"}
        </div>
        <div id="tabContent">
          ${this.activeTab==="incentives"?this.renderIncentivesTable():this.renderPointsTable()}
        </div>
      </div>

      <button class="back-btn" id="backToDashboard">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="19" y1="12" x2="5" y2="12"></line>
          <polyline points="12 19 5 12 12 5"></polyline>
        </svg>
        Back to Dashboard
      </button>
    `,this.attachListeners()}}renderIncentivesTable(){return this.incentives.length?`
      <div class="table-container">
        <table class="earnings-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>System</th>
              <th>Category</th>
              <th class="text-end">Amount</th>
              <th class="text-center">Status</th>
            </tr>
          </thead>
          <tbody>
            ${this.incentives.map(e=>{const t=e.created_at?new Date(e.created_at).toLocaleDateString("en-IN"):"N/A",a=e.system==="zynova"?"system-zynova":"system-myntreal",i=e.system==="zynova"?"Zynova":"MyntReal",n=(e.category||"-").replace(/_/g," "),s=e.incentive_amount||e.amount||0,r=e.status||"pending",o=r==="approved"?"status-approved":r==="rejected"?"status-rejected":"status-pending";return`
                <tr>
                  <td>${t}</td>
                  <td><span class="system-badge ${a}">${i}</span></td>
                  <td style="text-transform: capitalize;">${n}</td>
                  <td class="text-end amount-positive">₹${this.formatIndian(s)}</td>
                  <td class="text-center">
                    <span class="status-badge ${o}">${r.charAt(0).toUpperCase()+r.slice(1)}</span>
                  </td>
                </tr>`}).join("")}
          </tbody>
        </table>
      </div>`:`
        <div class="empty-state">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="8" x2="12" y2="12"></line>
            <line x1="12" y1="16" x2="12.01" y2="16"></line>
          </svg>
          <p>No incentives yet</p>
        </div>`}renderPointsTable(){return this.pointsHistory.length?`
      <div class="table-container">
        <table class="earnings-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Type</th>
              <th class="text-end">Amount</th>
              <th>Reference</th>
            </tr>
          </thead>
          <tbody>
            ${this.pointsHistory.map(e=>{const t=e.created_at?new Date(e.created_at).toLocaleDateString("en-IN"):"N/A",a=e.transaction_type==="allocation"||e.transaction_type==="refund",i=a?"amount-credit":"amount-debit",n=a?"+":"-";return`
                <tr>
                  <td>${t}</td>
                  <td><span class="type-badge">${e.transaction_type||"-"}</span></td>
                  <td class="text-end ${i}">${n}${this.formatIndian(e.amount||0)}</td>
                  <td>${e.reference_type||"-"}</td>
                </tr>`}).join("")}
          </tbody>
        </table>
      </div>`:`
        <div class="empty-state">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="8" x2="12" y2="12"></line>
            <line x1="12" y1="16" x2="12.01" y2="16"></line>
          </svg>
          <p>No points transactions yet</p>
        </div>`}updateTabContent(){const e=document.getElementById("tabContent"),t=document.getElementById("tableTitle");e&&(this.activeTab==="incentives"?(t&&(t.textContent="📋 My Incentives"),e.innerHTML=this.renderIncentivesTable()):(t&&(t.textContent="📜 Points History"),e.innerHTML=this.renderPointsTable()))}attachListeners(){document.getElementById("tabIncentives")?.addEventListener("click",()=>{this.activeTab="incentives",document.getElementById("tabIncentives")?.classList.add("active"),document.getElementById("tabPoints")?.classList.remove("active"),this.updateTabContent()}),document.getElementById("tabPoints")?.addEventListener("click",()=>{if(this.activeTab="points",document.getElementById("tabPoints")?.classList.add("active"),document.getElementById("tabIncentives")?.classList.remove("active"),this.pointsHistory.length===0){const e=document.getElementById("tabContent");e&&(e.innerHTML='<div class="loading-state">Loading points history...</div>'),this.loadPointsHistory()}else this.updateTabContent()}),document.getElementById("backToDashboard")?.addEventListener("click",()=>{f.navigate("mnr-dashboard")})}formatIndian(e){return(e||0).toLocaleString("en-IN")}}const y=u=>{if(!u)return"-";try{return new Date(u).toLocaleDateString("en-IN",{day:"2-digit",month:"2-digit",year:"numeric"})}catch{return u}},C=u=>`₹${u.toLocaleString("en-IN")}`,M=()=>`
  ${m.getStyles()}
  .income-page { padding: 16px; background: #0d1b2a; min-height: 100vh; }
  .filter-section {
    background: linear-gradient(135deg, #10b981 0%, #059669 100%);
    border-radius: 12px;
    padding: 14px;
    margin-bottom: 16px;
  }
  .filter-section h5 { color: white; margin: 0 0 10px; font-size: 13px; }
  .filter-row { display: grid; grid-template-columns: 1fr; gap: 10px; }
  .filter-group label { display: block; font-size: 10px; color: rgba(255,255,255,0.8); margin-bottom: 4px; }
  .filter-group input {
    width: 100%; padding: 10px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.3);
    background: rgba(255,255,255,0.95); color: #1a1a1a; font-size: 13px;
  }
  .filter-row-dates { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 10px; }
  .btn-submit {
    width: 100%; padding: 12px; border-radius: 6px; border: none;
    background: #3b82f6; color: white; font-size: 13px; font-weight: 600; cursor: pointer;
  }
  .filter-indicator {
    background: linear-gradient(135deg, #1f2937 0%, #374151 100%);
    padding: 10px 14px; border-radius: 8px; margin-bottom: 12px;
    font-size: 12px; color: white;
  }
  .table-header {
    background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
    padding: 10px 14px; border-radius: 8px 8px 0 0; margin-bottom: 0;
  }
  .table-header h5 { margin: 0; color: white; font-size: 13px; }
  .loading-state { text-align: center; padding: 40px; color: #8892b0; }
  .empty-state { text-align: center; padding: 40px; color: #8892b0; }
  .badge { padding: 3px 8px; border-radius: 4px; font-size: 10px; font-weight: 600; }
  .badge-yes { background: #10b981; color: white; }
  .badge-no { background: #ef4444; color: white; }
`;class Se{container;records=[];loading=!0;startDate="";endDate="";constructor(e){this.container=e}async init(){this.render(),await this.loadRecords()}async loadRecords(){this.loading=!0,this.updateContent();try{const e=b.getAuthState(),t=e.user?.mnr_id||e.user?.id||"",a=new URLSearchParams;t&&a.append("mnr_id",t),this.startDate&&a.append("start_date",this.startDate),this.endDate&&a.append("end_date",this.endDate);const i=await d.get(`/financial-operations/income/me/direct-referral-transactions?${a}`);i.success&&i.data&&(this.records=(i.data.transactions||i.data||[]).map((n,s)=>({sno:s+1,member_id:n.member_id||n.mnr_id||t,name:n.member_name||n.name||"Y.VASUDHA",referred_user_id:n.referred_user_id||n.for_member_id||"-",referred_user_name:n.referred_user_name||n.for_member_name||"-",from_date:n.from_date||n.activation_date||n.date||"",to_date:n.to_date||n.activation_date||n.date||"",total_amount:n.total_amount||n.amount||n.gross_amount||0,is_paid:n.is_paid===!0})))}catch(e){console.error("[MNRIncomeDirect] Failed to load:",e)}this.loading=!1,this.updateContent()}render(){const e=b.getAuthState(),t=e.user?.mnr_id||e.user?.id||"";this.container.innerHTML=`
      <style>${M()}</style>
      ${l.render({title:"💰 Direct Business Facilitation",showBack:!0})}
      <div class="income-page">
        <div class="filter-section">
          <h5>🔍 Filter Options</h5>
          <div class="filter-row">
            <div class="filter-group">
              <label>Member ID</label>
              <input type="text" id="filterMnrId" value="${t}" readonly style="background: #e5e7eb;" />
            </div>
          </div>
          <div class="filter-row-dates">
            <div class="filter-group">
              <label>Date From</label>
              <input type="date" id="filterStartDate" value="${this.startDate}" />
            </div>
            <div class="filter-group">
              <label>To</label>
              <input type="date" id="filterEndDate" value="${this.endDate}" />
            </div>
          </div>
          <button class="btn-submit" id="btnSubmit">Submit</button>
        </div>
        <div id="pageContent"></div>
      </div>
    `,l.attachListeners({title:"💰 Direct Business Facilitation",showBack:!0}),this.attachListeners()}updateContent(){const e=document.getElementById("pageContent");if(!e)return;if(this.loading){e.innerHTML='<div class="loading-state">Loading...</div>';return}const t=b.getAuthState(),a=t.user?.mnr_id||t.user?.id||"",i=new m({columns:[{key:"sno",label:"SNo"},{key:"member_id",label:"MemberId"},{key:"name",label:"Name"},{key:"referred_user_id",label:"Referred User ID"},{key:"referred_user_name",label:"Referred User Name"},{key:"from_date",label:"FromDate",render:n=>y(n)},{key:"to_date",label:"ToDate",render:n=>y(n)},{key:"total_amount",label:"Total Amount",render:n=>`<span style="color: #10b981; font-weight: 600;">${C(n)}</span>`},{key:"is_paid",label:"Status",render:n=>n?'<span class="badge" style="background: #10b981; color: white;">Paid</span>':'<span class="badge" style="background: #eab308; color: #1a1a1a;">Pending</span>'}],data:this.records,emptyMessage:"No Direct Business Facilitation transactions found"});e.innerHTML=`
      <div class="filter-indicator">Filter By | Member Id is ${a}</div>
      <div class="table-header"><h5>Direct Business Facilitation History</h5></div>
      ${i.render()}
    `}attachListeners(){document.getElementById("btnSubmit")?.addEventListener("click",()=>{this.startDate=document.getElementById("filterStartDate")?.value||"",this.endDate=document.getElementById("filterEndDate")?.value||"",this.loadRecords()})}}class Ee{container;records=[];loading=!0;startDate="";endDate="";constructor(e){this.container=e}async init(){this.render(),await this.loadRecords()}async loadRecords(){this.loading=!0,this.updateContent();try{const e=b.getAuthState(),t=e.user?.mnr_id||e.user?.id||"",a=new URLSearchParams;t&&a.append("mnr_id",t),this.startDate&&a.append("start_date",this.startDate),this.endDate&&a.append("end_date",this.endDate);const i=await d.get(`/financial-operations/income/me/matching-referral-transactions?${a}`);i.success&&i.data&&(this.records=(i.data.transactions||i.data||[]).map((n,s)=>({sno:s+1,pair_no:n.pair_number||n.pair_no||s+1,member_id:n.member_id||n.mnr_id||t,name:n.member_name||n.name||"-",left_contributor_id:n.left_contributor_id||n.left_mnr_id||"-",left_contributor_name:n.left_contributor_name||n.left_name||"-",left_points:n.left_points||n.left_bv||0,right_contributor_id:n.right_contributor_id||n.right_mnr_id||"-",right_contributor_name:n.right_contributor_name||n.right_name||"-",right_points:n.right_points||n.right_bv||0,date:n.date||n.created_at||"",amount:n.amount||n.total_amount||0,max_applied:n.max_applied||n.ceiling_applied||!1,is_paid:n.is_paid===!0})))}catch(e){console.error("[MNRIncomeMatching] Failed to load:",e)}this.loading=!1,this.updateContent()}render(){const e=b.getAuthState(),t=e.user?.mnr_id||e.user?.id||"";this.container.innerHTML=`
      <style>${M()}</style>
      ${l.render({title:"🤝 Group Performance Recognition",showBack:!0})}
      <div class="income-page">
        <div class="filter-section">
          <h5>🔍 Filter Options</h5>
          <div class="filter-row">
            <div class="filter-group">
              <label>Member ID</label>
              <input type="text" id="filterMnrId" value="${t}" readonly style="background: #e5e7eb;" />
            </div>
          </div>
          <div class="filter-row-dates">
            <div class="filter-group">
              <label>Date From</label>
              <input type="date" id="filterStartDate" value="${this.startDate}" />
            </div>
            <div class="filter-group">
              <label>To</label>
              <input type="date" id="filterEndDate" value="${this.endDate}" />
            </div>
          </div>
          <button class="btn-submit" id="btnSubmit">Submit</button>
        </div>
        <div id="pageContent"></div>
      </div>
    `,l.attachListeners({title:"🤝 Group Performance Recognition",showBack:!0}),this.attachListeners()}updateContent(){const e=document.getElementById("pageContent");if(!e)return;if(this.loading){e.innerHTML='<div class="loading-state">Loading...</div>';return}const t=b.getAuthState(),a=t.user?.mnr_id||t.user?.id||"",i=new m({columns:[{key:"sno",label:"SNo"},{key:"pair_no",label:"Pair#"},{key:"member_id",label:"MemberId"},{key:"name",label:"Name"},{key:"left_contributor_id",label:"Group A Contributor ID"},{key:"left_contributor_name",label:"Group A Contributor Name"},{key:"left_points",label:"Group A Points",render:n=>`<span class="badge" style="background: #3b82f6; color: white;">${n}</span>`},{key:"right_contributor_id",label:"Group B Contributor ID"},{key:"right_contributor_name",label:"Group B Contributor Name"},{key:"right_points",label:"Group B Points",render:n=>`<span class="badge" style="background: #8b5cf6; color: white;">${n}</span>`},{key:"date",label:"Date",render:n=>y(n)},{key:"amount",label:"Amount",render:n=>`<span style="color: #10b981; font-weight: 600;">${C(n)}</span>`},{key:"max_applied",label:"Max Applied",render:n=>n?'<span class="badge badge-yes">Yes</span>':'<span class="badge badge-no">No</span>'},{key:"is_paid",label:"Status",render:n=>n?'<span class="badge" style="background: #10b981; color: white;">Paid</span>':'<span class="badge" style="background: #eab308; color: #1a1a1a;">Pending</span>'}],data:this.records,emptyMessage:"No Group Performance Recognition transactions found"});e.innerHTML=`
      <div class="filter-indicator">Filter By | Member Id is ${a}</div>
      <div class="table-header"><h5>Group Performance Recognition History</h5></div>
      ${i.render()}
    `}attachListeners(){document.getElementById("btnSubmit")?.addEventListener("click",()=>{this.startDate=document.getElementById("filterStartDate")?.value||"",this.endDate=document.getElementById("filterEndDate")?.value||"",this.loadRecords()})}}class Ie{container;records=[];loading=!0;startDate="";endDate="";constructor(e){this.container=e}async init(){this.render(),await this.loadRecords()}async loadRecords(){this.loading=!0,this.updateContent();try{const e=b.getAuthState(),t=e.user?.mnr_id||e.user?.id||"",a=new URLSearchParams;t&&a.append("mnr_id",t),this.startDate&&a.append("start_date",this.startDate),this.endDate&&a.append("end_date",this.endDate);const i=await d.get(`/financial-operations/income/me/ved-income-transactions?${a}`);i.success&&i.data&&(this.records=(i.data.transactions||i.data||[]).map((n,s)=>({sno:s+1,for_member_id:n.for_member_id||n.from_mnr_id||"-",for_member_name:n.for_member_name||n.from_name||"-",from_date:n.from_date||n.date||"",to_date:n.to_date||n.date||"",total_amount:n.total_amount||n.amount||0,max_applied:n.max_applied||n.ceiling_applied||!1,is_paid:n.is_paid===!0})))}catch(e){console.error("[MNRIncomeVed] Failed to load:",e)}this.loading=!1,this.updateContent()}render(){const e=b.getAuthState(),t=e.user?.mnr_id||e.user?.id||"";this.container.innerHTML=`
      <style>${M()}</style>
      ${l.render({title:"👑 VED Leadership Recognition",showBack:!0})}
      <div class="income-page">
        <div class="filter-section">
          <h5>🔍 Filter Options</h5>
          <div class="filter-row">
            <div class="filter-group">
              <label>Member ID</label>
              <input type="text" id="filterMnrId" value="${t}" readonly style="background: #e5e7eb;" />
            </div>
          </div>
          <div class="filter-row-dates">
            <div class="filter-group">
              <label>Date From</label>
              <input type="date" id="filterStartDate" value="${this.startDate}" />
            </div>
            <div class="filter-group">
              <label>To</label>
              <input type="date" id="filterEndDate" value="${this.endDate}" />
            </div>
          </div>
          <button class="btn-submit" id="btnSubmit">Submit</button>
        </div>
        <div id="pageContent"></div>
      </div>
    `,l.attachListeners({title:"👑 VED Leadership Recognition",showBack:!0}),this.attachListeners()}updateContent(){const e=document.getElementById("pageContent");if(!e)return;if(this.loading){e.innerHTML='<div class="loading-state">Loading...</div>';return}const t=b.getAuthState(),a=t.user?.mnr_id||t.user?.id||"",i=new m({columns:[{key:"sno",label:"SNo"},{key:"for_member_id",label:"For Member ID"},{key:"for_member_name",label:"For Member Name"},{key:"from_date",label:"FromDate",render:n=>y(n)},{key:"to_date",label:"ToDate",render:n=>y(n)},{key:"total_amount",label:"Total Amount",render:n=>`<span style="color: #10b981; font-weight: 600;">${C(n)}</span>`},{key:"max_applied",label:"Max Applied",render:n=>n?'<span class="badge badge-yes">Yes</span>':'<span class="badge badge-no">No</span>'},{key:"is_paid",label:"Status",render:n=>n?'<span class="badge" style="background: #10b981; color: white;">Paid</span>':'<span class="badge" style="background: #eab308; color: #1a1a1a;">Pending</span>'}],data:this.records,emptyMessage:"No Ved income transactions found"});e.innerHTML=`
      <div class="filter-indicator">Filter By | Member Id is ${a}</div>
      <div class="table-header"><h5>VED Leadership Recognition History</h5></div>
      ${i.render()}
    `}attachListeners(){document.getElementById("btnSubmit")?.addEventListener("click",()=>{this.startDate=document.getElementById("filterStartDate")?.value||"",this.endDate=document.getElementById("filterEndDate")?.value||"",this.loadRecords()})}}class Pe{container;records=[];loading=!0;startDate="";endDate="";constructor(e){this.container=e}async init(){this.render(),await this.loadRecords()}async loadRecords(){this.loading=!0,this.updateContent();try{const e=b.getAuthState(),t=e.user?.mnr_id||e.user?.id||"",a=new URLSearchParams;t&&a.append("mnr_id",t),this.startDate&&a.append("start_date",this.startDate),this.endDate&&a.append("end_date",this.endDate);const i=await d.get(`/financial-operations/income/me/guru-dakshina-transactions?${a}`);i.success&&i.data&&(this.records=(i.data.transactions||i.data||[]).map((n,s)=>({sno:s+1,member_id:n.member_id||n.mnr_id||t,name:n.member_name||n.name||"-",for_member_id:n.for_member_id||n.from_mnr_id||"-",for_name:n.for_member_name||n.from_name||"-",from_date:n.from_date||n.date||"",to_date:n.to_date||n.date||"",total_amount:n.total_amount||n.amount||0,is_paid:n.is_paid===!0})))}catch(e){console.error("[MNRIncomeGuru] Failed to load:",e)}this.loading=!1,this.updateContent()}render(){const e=b.getAuthState(),t=e.user?.mnr_id||e.user?.id||"";this.container.innerHTML=`
      <style>${M()}</style>
      ${l.render({title:"🙏 Mentorship Contribution Benefit",showBack:!0})}
      <div class="income-page">
        <div class="filter-section">
          <h5>🔍 Filter Options</h5>
          <div class="filter-row">
            <div class="filter-group">
              <label>Member ID</label>
              <input type="text" id="filterMnrId" value="${t}" readonly style="background: #e5e7eb;" />
            </div>
          </div>
          <div class="filter-row-dates">
            <div class="filter-group">
              <label>Date From</label>
              <input type="date" id="filterStartDate" value="${this.startDate}" />
            </div>
            <div class="filter-group">
              <label>To</label>
              <input type="date" id="filterEndDate" value="${this.endDate}" />
            </div>
          </div>
          <button class="btn-submit" id="btnSubmit">Submit</button>
        </div>
        <div id="pageContent"></div>
      </div>
    `,l.attachListeners({title:"🙏 Mentorship Contribution Benefit",showBack:!0}),this.attachListeners()}updateContent(){const e=document.getElementById("pageContent");if(!e)return;if(this.loading){e.innerHTML='<div class="loading-state">Loading...</div>';return}const t=b.getAuthState(),a=t.user?.mnr_id||t.user?.id||"",i=new m({columns:[{key:"sno",label:"SNo"},{key:"member_id",label:"MemberId"},{key:"name",label:"Name"},{key:"for_member_id",label:"ForMemberId"},{key:"for_name",label:"ForName"},{key:"from_date",label:"FromDate",render:n=>y(n)},{key:"to_date",label:"ToDate",render:n=>y(n)},{key:"total_amount",label:"Total Amount",render:n=>`<span style="color: #10b981; font-weight: 600;">${C(n)}</span>`},{key:"is_paid",label:"Status",render:n=>n?'<span class="badge" style="background: #10b981; color: white;">Paid</span>':'<span class="badge" style="background: #eab308; color: #1a1a1a;">Pending</span>'}],data:this.records,emptyMessage:"No Mentorship Contribution Benefit transactions found"});e.innerHTML=`
      <div class="filter-indicator">Filter By | Member Id is ${a}</div>
      <div class="table-header"><h5>Mentorship Contribution Benefit History</h5></div>
      ${i.render()}
    `}attachListeners(){document.getElementById("btnSubmit")?.addEventListener("click",()=>{this.startDate=document.getElementById("filterStartDate")?.value||"",this.endDate=document.getElementById("filterEndDate")?.value||"",this.loadRecords()})}}class De{container;standardAllowance=null;carAllowance=null;currentActive=null;paymentHistory=[];loading=!0;constructor(e){this.container=e}async init(){this.render(),await this.loadData()}async loadData(){this.loading=!0,this.updateContent();try{const[e,t]=await Promise.all([d.get("/users/field-allowances-status"),d.get("/users/field-allowances")]);if(e.success&&e.data){const a=e.data.standard_allowance||{},i=e.data.car_allowance||{};this.currentActive=e.data.current_active||null,this.standardAllowance={status:a.status?.overall_status||"Not Started",total_paid:a.status?.total_paid||0,months_completed:a.status?.months_completed||0,months_remaining:a.status?.months_remaining||18,opportunity_missed:a.status?.opportunity_missed||!1,initial_eligibility:{required:a.initial_requirements?.direct_referrals?.required||7,current:a.initial_requirements?.direct_referrals?.current||0,remaining:a.initial_requirements?.direct_referrals?.remaining||7,progress_percentage:a.initial_requirements?.direct_referrals?.progress_percentage||0,is_frozen:a.initial_requirements?.direct_referrals?.is_frozen||!1,deadline:a.target_dates?.initial_eligibility_deadline||null},monthly_requirement:{required:a.monthly_requirements?.matching_pairs?.required||20,current:a.monthly_requirements?.matching_pairs?.current||0,progress_percentage:a.monthly_requirements?.matching_pairs?.progress_percentage||0,months_completed:a.status?.months_completed||0},target_dates:a.target_dates||{}},this.carAllowance={status:i.status?.overall_status||"Not Eligible",total_paid:i.status?.total_paid||0,months_completed:i.status?.months_completed||0,months_remaining:i.status?.months_remaining||72,opportunity_missed:i.status?.opportunity_missed||!1,initial_eligibility:{required:i.initial_requirements?.matching_points?.required||250,current:i.initial_requirements?.matching_points?.current||0,remaining:i.initial_requirements?.matching_points?.remaining||250,progress_percentage:i.initial_requirements?.matching_points?.progress_percentage||0,is_frozen:i.initial_requirements?.matching_points?.is_frozen||!1,qualification_status:i.initial_requirements?.matching_points?.qualification_status||null,deadline:i.target_dates?.initial_eligibility_deadline||null},monthly_requirement:{required:i.monthly_requirements?.matching_pairs?.required||40,current:i.monthly_requirements?.matching_pairs?.current||0,progress_percentage:i.monthly_requirements?.matching_pairs?.progress_percentage||0,months_completed:i.status?.months_completed||0},target_dates:i.target_dates||{}}}if(t.success&&t.data){const a=t.data.allowances||t.data.payment_history||[];this.paymentHistory=a.map(i=>({date:i.date||i.timestamp||"",type:i.type||i.description||"Field Allowance",amount:i.amount||0,status:i.status||"Completed"}))}}catch(e){console.error("[MNRIncomeField] Failed to load:",e)}this.loading=!1,this.updateContent()}render(){this.container.innerHTML=`
      <style>
        ${m.getStyles()}
        .field-page { padding: 16px; background: #0d1b2a; min-height: 100vh; }
        .about-section {
          background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
          border-radius: 12px; padding: 14px; margin-bottom: 16px; color: #451a03;
        }
        .about-section p { margin: 0; font-size: 12px; line-height: 1.5; }
        .allowance-cards { display: flex; flex-direction: column; gap: 16px; margin-bottom: 16px; }
        .allowance-card {
          border-radius: 12px; overflow: hidden;
          background: rgba(22, 33, 62, 0.9); border: 1px solid rgba(255,255,255,0.1);
        }
        .card-header { padding: 14px; color: white; }
        .card-header.standard { background: linear-gradient(135deg, #10b981 0%, #059669 100%); }
        .card-header.car { background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); }
        .card-header h4 { margin: 0 0 4px; font-size: 15px; }
        .card-header p { margin: 0; font-size: 11px; opacity: 0.9; }
        .card-body { padding: 14px; }
        .status-row { display: flex; justify-content: space-between; margin-bottom: 12px; }
        .status-item { text-align: center; }
        .status-item .label { font-size: 10px; color: #8892b0; margin-bottom: 4px; }
        .status-item .value { font-size: 14px; font-weight: 600; color: #e6f1ff; }
        .status-badge { padding: 4px 10px; border-radius: 4px; font-size: 11px; font-weight: 600; }
        .badge-not-started { background: #6b7280; color: white; }
        .badge-not-eligible { background: #ef4444; color: white; }
        .badge-active { background: #10b981; color: white; }
        .eligibility-section { margin-bottom: 12px; }
        .eligibility-section h5 { font-size: 12px; color: #8892b0; margin: 0 0 8px; }
        .progress-row { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
        .progress-label { font-size: 11px; color: #e6f1ff; flex: 1; }
        .progress-bar { flex: 2; height: 8px; background: rgba(255,255,255,0.1); border-radius: 4px; overflow: hidden; }
        .progress-fill { height: 100%; background: linear-gradient(90deg, #3b82f6, #8b5cf6); border-radius: 4px; }
        .progress-value { font-size: 11px; color: #64d2ff; font-weight: 600; min-width: 50px; text-align: right; }
        .deadline-row { display: flex; justify-content: space-between; font-size: 11px; color: #8892b0; margin-top: 6px; }
        .history-section { margin-top: 16px; }
        .history-header {
          background: linear-gradient(135deg, #374151 0%, #1f2937 100%);
          padding: 12px; border-radius: 8px 8px 0 0;
        }
        .history-header h5 { margin: 0; color: white; font-size: 13px; }
        .loading-state { text-align: center; padding: 40px; color: #8892b0; }
      </style>
      ${l.render({title:"🚗 Field Activity Support",showBack:!0})}
      <div class="field-page" id="pageContent">
        <div class="loading-state">Loading...</div>
      </div>
    `,l.attachListeners({title:"🚗 Field Activity Support",showBack:!0})}formatDeadline(e){if(!e)return"-";try{return new Date(e).toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"numeric"})}catch{return"-"}}updateContent(){const e=document.getElementById("pageContent");if(!e)return;if(this.loading){e.innerHTML='<div class="loading-state">Loading...</div>';return}const t=this.standardAllowance,a=this.carAllowance,i=t?.initial_eligibility?.progress_percentage||0,n=a?.initial_eligibility?.progress_percentage||0,s=t?.monthly_requirement?.progress_percentage||0,r=a?.monthly_requirement?.progress_percentage||0,o=this.currentActive?`
      <div style="background: linear-gradient(135deg, #10b981, #059669); border-radius: 10px; padding: 12px; margin-bottom: 16px; color: white; font-size: 13px;">
        <strong>Active Allowance:</strong> ${this.currentActive==="car"?"Car Allowance (₹25,000/month)":"Standard Field Allowance (₹10,000/month)"}
      </div>`:"",c=t?.opportunity_missed?`
      <div style="background: rgba(239,68,68,0.15); border: 1px solid rgba(239,68,68,0.3); border-radius: 6px; padding: 8px; margin-top: 8px; font-size: 11px; color: #fca5a5;">
        <strong>Missed Opportunity!</strong> Deadline passed.
      </div>`:"",p=a?.opportunity_missed?`
      <div style="background: rgba(239,68,68,0.15); border: 1px solid rgba(239,68,68,0.3); border-radius: 6px; padding: 8px; margin-top: 8px; font-size: 11px; color: #fca5a5;">
        <strong>Missed Opportunity!</strong> Deadline passed.
      </div>`:"",g=a?.initial_eligibility?.qualification_status&&!a.initial_eligibility.qualification_status.qualified&&!a.opportunity_missed?`
      <div style="background: rgba(251,191,36,0.15); border: 1px solid rgba(251,191,36,0.3); border-radius: 6px; padding: 8px; margin-top: 8px; font-size: 11px; color: #fde68a;">
        <strong>Qualification Required:</strong> ${a.initial_eligibility.qualification_status.message||""}
      </div>`:"";e.innerHTML=`
      <div class="about-section">
        <p><strong>About Field Allowances:</strong> Performance-based fixed monthly payments for active MNR members. Two tiers available: Standard (₹10,000/month x 18 months) and Car Allowance (₹25,000/month x 72 months).</p>
      </div>

      ${o}

      <div class="allowance-cards">
        <div class="allowance-card">
          <div class="card-header standard">
            <h4>Standard Field Allowance</h4>
            <p>₹10,000/month x 18 months</p>
          </div>
          <div class="card-body">
            <div class="status-row">
              <div class="status-item">
                <div class="label">Status</div>
                <div class="value"><span class="status-badge ${t?.status==="Active"?"badge-active":t?.opportunity_missed?"badge-not-eligible":"badge-not-started"}">${t?.status||"Not Started"}</span></div>
              </div>
              <div class="status-item">
                <div class="label">Total Paid</div>
                <div class="value" style="color: #10b981;">₹${(t?.total_paid||0).toLocaleString("en-IN")}</div>
              </div>
            </div>
            
            <div class="eligibility-section">
              <h5>Initial Eligibility:</h5>
              <div class="progress-row">
                <div class="progress-label">7 Direct Business Facilitations (45 days)</div>
                <div class="progress-bar"><div class="progress-fill" style="width: ${i}%; background: ${i>=100?"#10b981":"linear-gradient(90deg, #3b82f6, #8b5cf6)"};"></div></div>
                <div class="progress-value">${t?.initial_eligibility?.current||0}/${t?.initial_eligibility?.required||7}</div>
              </div>
              <div class="deadline-row">
                <span>Remaining: ${t?.initial_eligibility?.remaining??7}</span>
                <span>Deadline: ${this.formatDeadline(t?.initial_eligibility?.deadline)}</span>
              </div>
              ${c}
            </div>

            <div class="eligibility-section">
              <h5>Monthly Requirement:</h5>
              <div class="progress-row">
                <div class="progress-label">20 Matching Pairs/month</div>
                <div class="progress-bar"><div class="progress-fill" style="width: ${s}%;"></div></div>
                <div class="progress-value">${t?.monthly_requirement?.current||0}/${t?.monthly_requirement?.required||20}</div>
              </div>
              <div class="deadline-row">
                <span>Months: ${t?.monthly_requirement?.months_completed||0}/18</span>
                <span>Next: ${this.formatDeadline(t?.target_dates?.next_payment_date)}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="allowance-card">
          <div class="card-header car">
            <h4>Car Allowance (Premium)</h4>
            <p>₹25,000/month x 72 months</p>
          </div>
          <div class="card-body">
            <div class="status-row">
              <div class="status-item">
                <div class="label">Status</div>
                <div class="value"><span class="status-badge ${a?.status==="Active"?"badge-active":(a?.opportunity_missed,"badge-not-eligible")}">${a?.status||"Not Eligible"}</span></div>
              </div>
              <div class="status-item">
                <div class="label">Total Paid</div>
                <div class="value" style="color: #10b981;">₹${(a?.total_paid||0).toLocaleString("en-IN")}</div>
              </div>
            </div>
            
            <div class="eligibility-section">
              <h5>Initial Eligibility:</h5>
              <div class="progress-row">
                <div class="progress-label">250 Matching Points (90 days)</div>
                <div class="progress-bar"><div class="progress-fill" style="width: ${n}%; background: ${n>=100?"#10b981":"linear-gradient(90deg, #f59e0b, #ef4444)"};"></div></div>
                <div class="progress-value">${a?.initial_eligibility?.current||0}/${a?.initial_eligibility?.required||250}</div>
              </div>
              <div class="deadline-row">
                <span>Remaining: ${a?.initial_eligibility?.remaining??250}</span>
                <span>Deadline: ${this.formatDeadline(a?.initial_eligibility?.deadline)}</span>
              </div>
              ${p}
              ${g}
            </div>

            <div class="eligibility-section">
              <h5>Monthly Requirement:</h5>
              <div class="progress-row">
                <div class="progress-label">40 Matching Pairs/month</div>
                <div class="progress-bar"><div class="progress-fill" style="width: ${r}%;"></div></div>
                <div class="progress-value">${a?.monthly_requirement?.current||0}/${a?.monthly_requirement?.required||40}</div>
              </div>
              <div class="deadline-row">
                <span>Months: ${a?.monthly_requirement?.months_completed||0}/72</span>
                <span>Next: ${this.formatDeadline(a?.target_dates?.next_payment_date)}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="history-section">
        <div class="history-header"><h5>Payment History</h5></div>
        ${this.paymentHistory.length>0?this.renderHistoryTable():'<div class="empty-state" style="background: rgba(22,33,62,0.8); padding: 20px; text-align: center; color: #8892b0; border-radius: 0 0 8px 8px;">No payment history yet</div>'}
      </div>
    `}renderHistoryTable(){return new m({columns:[{key:"date",label:"Date",render:t=>y(t)},{key:"type",label:"Type"},{key:"amount",label:"Amount",render:t=>`₹${t.toLocaleString()}`},{key:"status",label:"Status"}],data:this.paymentHistory,emptyMessage:"No payments found"}).render()}}class Ae{container;packages=[];loading=!0;currentUser=null;referrerInfo=null;referrerLoading=!1;referrerError="";constructor(e){this.container=e}async init(){const e=b.getAuthState();this.currentUser=e.user,this.render(),await this.loadPackages(),this.setDefaultReferrer()}async loadPackages(){try{const e=await d.get("/users/packages");e.success&&e.data&&(this.packages=e.data.packages||e.data||[])}catch(e){console.error("[MNRAddMember] Failed to load packages:",e)}this.loading=!1,this.updateContent()}setDefaultReferrer(){const e=document.getElementById("referrerId");e&&this.currentUser?.mnr_id&&(e.value=this.currentUser.mnr_id,this.referrerInfo={name:this.currentUser.name||"You",mnr_id:this.currentUser.mnr_id,active_status:!0},this.updateReferrerDisplay())}render(){this.container.innerHTML=`
      <style>
        .add-member-page {
          background: linear-gradient(135deg, #0a1929 0%, #0d2137 100%);
          min-height: 100vh;
        }
        .add-member-content {
          padding: 16px;
        }
        .form-card {
          background: #ffffff;
          border-radius: 16px;
          overflow: hidden;
          box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
        }
        .form-header {
          background: linear-gradient(135deg, #10b981 0%, #059669 100%);
          padding: 20px;
          text-align: center;
        }
        .form-header h2 {
          margin: 0;
          color: white;
          font-size: 18px;
          font-weight: 600;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 10px;
        }
        .form-header p {
          margin: 8px 0 0;
          color: rgba(255, 255, 255, 0.9);
          font-size: 13px;
        }
        .form-body {
          padding: 20px;
        }
        .form-section {
          margin-bottom: 24px;
        }
        .form-section-title {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 14px;
          font-weight: 600;
          color: #1f2937;
          margin-bottom: 16px;
          padding-bottom: 8px;
          border-bottom: 2px solid #e5e7eb;
        }
        .form-section-title .icon {
          width: 24px;
          height: 24px;
          background: linear-gradient(135deg, #7c3aed 0%, #5b21b6 100%);
          border-radius: 6px;
          display: flex;
          align-items: center;
          justify-content: center;
          color: white;
          font-size: 12px;
        }
        .form-row {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 12px;
          margin-bottom: 16px;
        }
        .form-row.three-col {
          grid-template-columns: 1fr 1fr 1fr;
        }
        .form-group {
          margin-bottom: 16px;
        }
        .form-row .form-group {
          margin-bottom: 0;
        }
        .form-group label {
          display: block;
          font-size: 12px;
          font-weight: 600;
          color: #374151;
          margin-bottom: 6px;
        }
        .form-group label .required {
          color: #ef4444;
        }
        .form-group input,
        .form-group select,
        .form-group textarea {
          width: 100%;
          padding: 12px 14px;
          border: 2px solid #e5e7eb;
          border-radius: 10px;
          font-size: 14px;
          color: #1f2937;
          background: #f9fafb;
          transition: all 0.2s ease;
          box-sizing: border-box;
        }
        .form-group input:focus,
        .form-group select:focus,
        .form-group textarea:focus {
          outline: none;
          border-color: #7c3aed;
          background: #ffffff;
          box-shadow: 0 0 0 3px rgba(124, 58, 237, 0.1);
        }
        .form-group input::placeholder,
        .form-group textarea::placeholder {
          color: #9ca3af;
        }
        .form-hint {
          display: block;
          font-size: 11px;
          color: #6b7280;
          margin-top: 4px;
        }

        /* Referrer Section */
        .referrer-section {
          background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
          border-radius: 12px;
          padding: 16px;
          margin-bottom: 20px;
        }
        .referrer-title {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 14px;
          font-weight: 600;
          color: #92400e;
          margin-bottom: 12px;
        }
        .referrer-input-row {
          display: flex;
          gap: 10px;
          margin-bottom: 8px;
        }
        .referrer-input-row input {
          flex: 1;
          padding: 12px 14px;
          border: 2px solid #d97706;
          border-radius: 10px;
          font-size: 14px;
          color: #1f2937;
          background: #ffffff;
        }
        .referrer-input-row input:focus {
          outline: none;
          border-color: #b45309;
          box-shadow: 0 0 0 3px rgba(217, 119, 6, 0.2);
        }
        .lookup-btn {
          padding: 12px 16px;
          background: linear-gradient(135deg, #d97706 0%, #b45309 100%);
          border: none;
          border-radius: 10px;
          color: white;
          font-size: 13px;
          font-weight: 600;
          cursor: pointer;
          white-space: nowrap;
        }
        .lookup-btn:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }
        .referrer-info {
          display: flex;
          align-items: center;
          gap: 12px;
          background: #ffffff;
          border-radius: 10px;
          padding: 12px;
          margin-top: 10px;
        }
        .referrer-avatar {
          width: 44px;
          height: 44px;
          background: linear-gradient(135deg, #7c3aed 0%, #5b21b6 100%);
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          color: white;
          font-weight: 700;
          font-size: 16px;
        }
        .referrer-details {
          flex: 1;
        }
        .referrer-name {
          font-size: 14px;
          font-weight: 600;
          color: #1f2937;
        }
        .referrer-id {
          font-size: 12px;
          color: #6b7280;
        }
        .referrer-status {
          padding: 4px 10px;
          border-radius: 20px;
          font-size: 11px;
          font-weight: 600;
        }
        .referrer-status.active {
          background: #d1fae5;
          color: #047857;
        }
        .referrer-status.pending {
          background: #fee2e2;
          color: #b91c1c;
        }
        .referrer-error {
          color: #b91c1c;
          font-size: 12px;
          margin-top: 8px;
          display: flex;
          align-items: center;
          gap: 6px;
        }
        .referrer-loading {
          color: #92400e;
          font-size: 12px;
          margin-top: 8px;
          display: flex;
          align-items: center;
          gap: 6px;
        }

        /* Position Selection */
        .position-cards {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 10px;
          margin-top: 8px;
        }
        .position-card {
          padding: 16px 12px;
          border: 2px solid #e5e7eb;
          border-radius: 12px;
          text-align: center;
          cursor: pointer;
          transition: all 0.2s ease;
          background: #f9fafb;
        }
        .position-card:hover {
          border-color: #7c3aed;
          background: #faf5ff;
        }
        .position-card.selected {
          border-color: #7c3aed;
          background: linear-gradient(135deg, #7c3aed 0%, #5b21b6 100%);
          color: white;
        }
        .position-card .icon {
          font-size: 24px;
          margin-bottom: 6px;
        }
        .position-card .label {
          font-size: 13px;
          font-weight: 600;
        }

        /* Submit Button */
        .submit-section {
          margin-top: 24px;
        }
        .submit-btn {
          width: 100%;
          padding: 16px;
          background: linear-gradient(135deg, #10b981 0%, #059669 100%);
          border: none;
          border-radius: 12px;
          color: white;
          font-size: 16px;
          font-weight: 600;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 10px;
          box-shadow: 0 4px 14px rgba(16, 185, 129, 0.4);
          transition: all 0.2s ease;
        }
        .submit-btn:hover {
          transform: translateY(-2px);
          box-shadow: 0 6px 20px rgba(16, 185, 129, 0.5);
        }
        .submit-btn:disabled {
          opacity: 0.6;
          cursor: not-allowed;
          transform: none;
        }
        .submit-btn svg {
          width: 20px;
          height: 20px;
        }

        .loading-state {
          text-align: center;
          padding: 40px;
          color: #6b7280;
        }
      </style>

      <div class="page-container add-member-page">
        ${l.render({title:"➕ Add Member",showBack:!0})}
        
        <div class="add-member-content" id="pageContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
    `,l.attachListeners({title:"➕ Add Member",showBack:!0})}updateContent(){const e=document.getElementById("pageContent");if(!e)return;const t=this.currentUser?.mnr_id||"",a=this.currentUser?.name||"You";e.innerHTML=`
      <div class="form-card">
        <div class="form-header">
          <h2>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
              <circle cx="8.5" cy="7" r="4"></circle>
              <line x1="20" y1="8" x2="20" y2="14"></line>
              <line x1="23" y1="11" x2="17" y2="11"></line>
            </svg>
            Member Registration
          </h2>
          <p>Add a new member to your referral network</p>
        </div>

        <div class="form-body">
          <form id="addMemberForm">
            <!-- Referrer Section -->
            <div class="referrer-section">
              <div class="referrer-title">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                  <circle cx="9" cy="7" r="4"></circle>
                  <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
                  <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
                </svg>
                Referrer Information
              </div>
              <div class="referrer-input-row">
                <input type="text" id="referrerId" value="${t}" placeholder="Enter MNR ID" />
                <button type="button" class="lookup-btn" id="lookupBtn">
                  Verify
                </button>
              </div>
              <span class="form-hint">Your MNR ID is pre-filled. Enter different ID to refer under someone else.</span>
              
              <div id="referrerDisplay">
                ${this.currentUser?`
                  <div class="referrer-info">
                    <div class="referrer-avatar">${this.getInitials(a)}</div>
                    <div class="referrer-details">
                      <div class="referrer-name">${a}</div>
                      <div class="referrer-id">MNR ID: ${t}</div>
                    </div>
                    <span class="referrer-status active">Active</span>
                  </div>
                `:""}
              </div>
            </div>

            <!-- Personal Details Section -->
            <div class="form-section">
              <div class="form-section-title">
                <div class="icon">1</div>
                Personal Details
              </div>

              <div class="form-row">
                <div class="form-group">
                  <label>First Name <span class="required">*</span></label>
                  <input type="text" id="firstName" required placeholder="First name" />
                </div>
                <div class="form-group">
                  <label>Last Name <span class="required">*</span></label>
                  <input type="text" id="lastName" required placeholder="Last name" />
                </div>
              </div>

              <div class="form-row">
                <div class="form-group">
                  <label>Salutation <span class="required">*</span></label>
                  <select id="salutation" required>
                    <option value="">Select</option>
                    <option value="Mr">Mr</option>
                    <option value="Mrs">Mrs</option>
                    <option value="Ms">Ms</option>
                    <option value="Dr">Dr</option>
                  </select>
                </div>
                <div class="form-group">
                  <label>Mobile <span class="required">*</span></label>
                  <input type="tel" id="mobile" required placeholder="10 digits" maxlength="10" oninput="document.getElementById('mnrMobileOtpSection').style.display='none';document.getElementById('mnrMobileVerifiedBadge').style.display='none';document.getElementById('mnrMobilePhoneToken').value='';" />
                </div>
              </div>

              <!-- [DC-PHONE-OTP-001] WhatsApp OTP verification for MNR member add (mobile) -->
              <div class="form-group">
                <button type="button" id="mnrMobileSendOtpBtn" onclick="mnrMobileSendOTP()" style="width:100%;padding:11px;background:linear-gradient(135deg,#7c3aed,#5b21b6);border:none;border-radius:10px;color:#fff;font-size:14px;font-weight:600;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:8px;">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.69 12a19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 3.6 1.17h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L7.91 8.7A16 16 0 0 0 13.3 14.09l.95-.95a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 21.02 15.5z"/></svg>
                  Send OTP to WhatsApp
                </button>
                <div style="font-size:11px;color:#ef4444;margin-top:5px;text-align:center"><i>WhatsApp OTP verification is required before registering</i></div>
              </div>
              <div id="mnrMobileOtpSection" style="display:none;background:#f0fdf4;border:2px solid #86efac;border-radius:12px;padding:14px;margin-bottom:16px;">
                <div style="font-size:12.5px;color:#166534;margin-bottom:10px;display:flex;align-items:center;gap:6px;">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="#25D366"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/><path d="M12 0C5.373 0 0 5.373 0 12c0 2.125.558 4.126 1.535 5.856L0 24l6.335-1.652A11.954 11.954 0 0 0 12 24c6.627 0 12-5.373 12-12S18.627 0 12 0zm0 21.818a9.818 9.818 0 0 1-5.006-1.371l-.36-.214-3.727.972.997-3.639-.235-.373A9.818 9.818 0 1 1 12 21.818z"/></svg>
                  OTP sent! Enter the 6-digit code from WhatsApp:
                </div>
                <div style="display:flex;gap:8px;">
                  <input type="text" id="mnrMobileOtpInput" maxlength="6" placeholder="● ● ● ● ● ●" style="flex:1;padding:12px;border:2px solid #22c55e;border-radius:10px;font-size:20px;font-weight:700;letter-spacing:6px;text-align:center;background:#fff;color:#166534;" />
                  <button type="button" id="mnrMobileVerifyBtn" onclick="mnrMobileVerifyOTP()" style="padding:12px 16px;background:#22c55e;border:none;border-radius:10px;color:#fff;font-size:14px;font-weight:600;cursor:pointer;">Verify</button>
                </div>
                <div style="margin-top:8px;font-size:11.5px;color:#6b7280;text-align:center">Didn't receive? <a href="#" onclick="mnrMobileSendOTP();return false;" style="color:#7c3aed;font-weight:600;">Resend OTP</a></div>
              </div>
              <div id="mnrMobileVerifiedBadge" style="display:none;background:#f0fdf4;border:2px solid #22c55e;border-radius:10px;padding:10px 14px;margin-bottom:16px;color:#166534;font-size:13px;font-weight:600;display:none;align-items:center;gap:8px;">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#22c55e" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg>
                WhatsApp number verified
              </div>
              <input type="hidden" id="mnrMobilePhoneToken" value="" />

              <div class="form-group">
                <label>Password <span class="required">*</span></label>
                <input type="password" id="password" required placeholder="Create password (min 6 chars)" />
              </div>
            </div>

            <!-- Address Section -->
            <div class="form-section">
              <div class="form-section-title">
                <div class="icon">2</div>
                Address Details
              </div>

              <div class="form-group">
                <label>Address</label>
                <textarea id="address" rows="2" placeholder="Street address"></textarea>
              </div>

              <div class="form-row three-col">
                <div class="form-group">
                  <label>City</label>
                  <input type="text" id="city" placeholder="City" />
                </div>
                <div class="form-group">
                  <label>State</label>
                  <input type="text" id="state" placeholder="State" />
                </div>
                <div class="form-group">
                  <label>Pincode</label>
                  <input type="text" id="pincode" maxlength="6" placeholder="6 digits" />
                </div>
              </div>
            </div>

            <!-- Position Section -->
            <div class="form-section">
              <div class="form-section-title">
                <div class="icon">3</div>
                Placement Position
              </div>
              <span class="form-hint" style="margin-top: -10px; margin-bottom: 12px; display: block;">Choose where to place this member in your tree</span>
              
              <div class="position-cards">
                <div class="position-card" data-position="left">
                  <div class="icon">⬅️</div>
                  <div class="label">Group A</div>
                </div>
                <div class="position-card" data-position="right">
                  <div class="icon">➡️</div>
                  <div class="label">Group B</div>
                </div>
                <div class="position-card selected" data-position="auto">
                  <div class="icon">⚡</div>
                  <div class="label">Auto</div>
                </div>
              </div>
              <input type="hidden" id="position" value="auto" />
            </div>

            <!-- Submit -->
            <div class="submit-section">
              <button type="submit" class="submit-btn" id="submitBtn">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                  <circle cx="8.5" cy="7" r="4"></circle>
                  <line x1="20" y1="8" x2="20" y2="14"></line>
                  <line x1="23" y1="11" x2="17" y2="11"></line>
                </svg>
                Add Member
              </button>
            </div>
          </form>
        </div>
      </div>
    `,this.attachFormListeners()}updateReferrerDisplay(){const e=document.getElementById("referrerDisplay");if(e){if(this.referrerLoading){e.innerHTML=`
        <div class="referrer-loading">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="spin">
            <circle cx="12" cy="12" r="10"></circle>
            <path d="M12 6v6l4 2"></path>
          </svg>
          Verifying MNR ID...
        </div>
      `;return}if(this.referrerError){e.innerHTML=`
        <div class="referrer-error">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="15" y1="9" x2="9" y2="15"></line>
            <line x1="9" y1="9" x2="15" y2="15"></line>
          </svg>
          ${this.referrerError}
        </div>
      `;return}this.referrerInfo?e.innerHTML=`
        <div class="referrer-info">
          <div class="referrer-avatar">${this.getInitials(this.referrerInfo.name)}</div>
          <div class="referrer-details">
            <div class="referrer-name">${this.referrerInfo.name}</div>
            <div class="referrer-id">MNR ID: ${this.referrerInfo.mnr_id}</div>
          </div>
          <span class="referrer-status ${this.referrerInfo.active_status?"active":"pending"}">
            ${this.referrerInfo.active_status?"Active":"Pending"}
          </span>
        </div>
      `:e.innerHTML=""}}async lookupReferrer(e){if(!e.trim()){this.referrerError="Please enter an MNR ID",this.referrerInfo=null,this.updateReferrerDisplay();return}this.referrerLoading=!0,this.referrerError="",this.updateReferrerDisplay();try{const t=await d.get(`/users/${e}/basic-info`);t.success&&t.data?(this.referrerInfo={name:t.data.name||"Unknown",mnr_id:t.data.mnr_id||e,active_status:t.data.active_status||!1},this.referrerError=""):(this.referrerError=t.error||"Member not found",this.referrerInfo=null)}catch(t){console.error("[MNRAddMember] Referrer lookup failed:",t),this.referrerError="Failed to verify MNR ID",this.referrerInfo=null}this.referrerLoading=!1,this.updateReferrerDisplay()}getInitials(e){return e?e.split(" ").map(t=>t[0]).join("").toUpperCase().slice(0,2):"?"}attachFormListeners(){document.getElementById("addMemberForm")?.addEventListener("submit",n=>{n.preventDefault(),this.handleSubmit()}),window.mnrMobileSendOTP=async()=>{const n=document.getElementById("mobile")?.value.replace(/[^0-9]/g,"");if(!n||n.length<10){alert("Please enter a valid 10-digit mobile number first.");return}const s=document.getElementById("mnrMobileSendOtpBtn");s&&(s.disabled=!0,s.textContent="Sending…"),document.getElementById("mnrMobileOtpSection").style.display="none",document.getElementById("mnrMobileVerifiedBadge").style.display="none",document.getElementById("mnrMobilePhoneToken").setAttribute("value","");try{const r=await fetch("/api/v1/users/send-otp",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({phone:n})}),o=await r.json();r.ok&&o.success?(document.getElementById("mnrMobileOtpSection").style.display="block",document.getElementById("mnrMobileOtpInput").value="",document.getElementById("mnrMobileOtpInput").focus()):alert(o.detail||o.message||"Failed to send OTP. Please try again.")}catch{alert("Network error. Please try again.")}finally{s&&(s.disabled=!1,s.innerHTML='<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.69 12a19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 3.6 1.17h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L7.91 8.7A16 16 0 0 0 13.3 14.09l.95-.95a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 21.02 15.5z"/></svg> Send OTP to WhatsApp')}},window.mnrMobileVerifyOTP=async()=>{const n=document.getElementById("mobile")?.value.replace(/[^0-9]/g,""),s=document.getElementById("mnrMobileOtpInput")?.value.trim();if(!s||s.length!==6){alert("Please enter the 6-digit OTP from WhatsApp.");return}const r=document.getElementById("mnrMobileVerifyBtn");r&&(r.disabled=!0,r.textContent="Verifying…");try{const o=await fetch("/api/v1/users/verify-otp",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({phone:n,otp_code:s})}),c=await o.json();if(o.ok&&c.success){document.getElementById("mnrMobilePhoneToken").value=c.phone_verified_token,document.getElementById("mnrMobileOtpSection").style.display="none";const p=document.getElementById("mnrMobileVerifiedBadge");p.style.display="flex"}else alert(c.detail||c.message||"Invalid OTP. Please try again.")}catch{alert("Network error. Please try again.")}finally{r&&(r.disabled=!1,r.textContent="Verify")}},document.getElementById("lookupBtn")?.addEventListener("click",()=>{const n=document.getElementById("referrerId")?.value.trim();this.lookupReferrer(n)});const a=document.getElementById("referrerId");a?.addEventListener("blur",()=>{const n=a.value.trim();n&&n!==this.currentUser?.mnr_id?this.lookupReferrer(n):n===this.currentUser?.mnr_id&&(this.referrerInfo={name:this.currentUser.name||"You",mnr_id:this.currentUser.mnr_id,active_status:!0},this.referrerError="",this.updateReferrerDisplay())});const i=document.querySelectorAll(".position-card");i.forEach(n=>{n.addEventListener("click",()=>{i.forEach(r=>r.classList.remove("selected")),n.classList.add("selected");const s=document.getElementById("position");s&&(s.value=n.dataset.position||"auto")})})}async handleSubmit(){const e=document.getElementById("firstName")?.value.trim(),t=document.getElementById("lastName")?.value.trim(),a=document.getElementById("salutation")?.value,i=document.getElementById("mobile")?.value.trim(),n=document.getElementById("password")?.value,s=document.getElementById("address")?.value.trim(),r=document.getElementById("city")?.value.trim(),o=document.getElementById("state")?.value.trim(),c=document.getElementById("pincode")?.value.trim(),p=document.getElementById("referrerId")?.value.trim(),g=document.getElementById("position")?.value;if(!e||!t||!a||!i||!n){alert("Please fill all required fields");return}if(i.length!==10){alert("Please enter a valid 10-digit mobile number");return}const v=document.getElementById("mnrMobilePhoneToken")?.value.trim();if(!v){alert('Phone verification required. Please tap "Send OTP to WhatsApp", enter the code, and tap Verify before adding the member.');return}if(n.length<6){alert("Password must be at least 6 characters");return}const h=document.getElementById("submitBtn");h&&(h.disabled=!0,h.innerHTML=`
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="spin">
          <circle cx="12" cy="12" r="10"></circle>
          <path d="M12 6v6l4 2"></path>
        </svg>
        Adding Member...
      `);const B=`${a}. ${e} ${t}`.trim();try{const x=await d.post("/users/register",{name:B,first_name:e,last_name:t,salutation:a,mobile:i,password:n,address:s||null,city:r||null,state:o||null,pincode:c||null,sponsor_id:p||null,position:g==="auto"?"Left":g,phone_verified_token:v});if(x.success){const L=x.data?.mnr_id||"Generated";alert(`Member added successfully!

MNR ID: ${L}`),f.navigate("mnr-dashboard")}else alert(x.error||"Failed to add member"),h&&(h.disabled=!1,h.innerHTML=`
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
              <circle cx="8.5" cy="7" r="4"></circle>
              <line x1="20" y1="8" x2="20" y2="14"></line>
              <line x1="23" y1="11" x2="17" y2="11"></line>
            </svg>
            Add Member
          `)}catch(x){console.error("[MNRAddMember] Submit failed:",x),alert("Failed to add member. Please try again."),h&&(h.disabled=!1,h.innerHTML=`
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
            <circle cx="8.5" cy="7" r="4"></circle>
            <line x1="20" y1="8" x2="20" y2="14"></line>
            <line x1="23" y1="11" x2="17" y2="11"></line>
          </svg>
          Add Member
        `)}}}class ze{container;leads=[];stats={total_leads:0,active_franchises:0,total_earnings:0};loading=!0;constructor(e){this.container=e}async init(){this.render(),await this.loadData()}async loadData(){this.loading=!0,this.updateContent();try{const e=await d.get("/crm/unified-my-leads?segment=my&role=mnr&category=franchise");if(e.success&&e.data){const a=e.data.leads||e.data||[];this.leads=a.map(s=>({id:s.id,name:s.name||"",status:s.status||"new",created_at:s.created_at||""}));const i=["converted","active","won"],n=this.leads.filter(s=>i.includes(s.status.toLowerCase()));this.stats={total_leads:this.leads.length,active_franchises:n.length,total_earnings:n.length*0}}const t=await d.get("/users/earnings-summary");if(t.success&&t.data){const a=t.data;this.stats.total_earnings=typeof a.franchise_earnings=="number"?a.franchise_earnings:0}}catch(e){console.error("[MNRFranchiseEarnings] Failed to load:",e)}this.loading=!1,this.updateContent()}render(){this.container.innerHTML=`
      <div class="page-container franchise-page">
        ${l.render({title:"🏪 Franchise Earnings",showBack:!0})}
        
        <div id="pageContent">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
    `,l.attachListeners({title:"🏪 Franchise Earnings",showBack:!0})}updateContent(){const e=document.getElementById("pageContent");if(e){if(this.loading){e.innerHTML='<div class="loading-state">Loading...</div>';return}e.innerHTML=`
      <style>
        .mentorial-hub-hero {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
          border-radius: 20px;
          padding: 24px 20px;
          margin-bottom: 20px;
          text-align: center;
          color: white;
          position: relative;
          overflow: hidden;
        }
        .mentorial-hub-hero::before {
          content: '';
          position: absolute;
          top: -50%;
          left: -50%;
          width: 200%;
          height: 200%;
          background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 60%);
          animation: pulse 4s ease-in-out infinite;
        }
        @keyframes pulse {
          0%, 100% { transform: scale(1); opacity: 0.5; }
          50% { transform: scale(1.1); opacity: 0.8; }
        }
        .mentorial-hub-hero .hero-badge {
          display: inline-block;
          background: rgba(255,255,255,0.25);
          padding: 6px 16px;
          border-radius: 20px;
          font-size: 11px;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 1px;
          margin-bottom: 12px;
        }
        .mentorial-hub-hero h1 {
          font-size: 28px;
          font-weight: 800;
          margin: 0 0 8px;
          text-shadow: 0 2px 10px rgba(0,0,0,0.2);
        }
        .mentorial-hub-hero .hero-subtitle {
          font-size: 15px;
          opacity: 0.95;
          margin: 0 0 16px;
        }
        .mentorial-hub-hero .hero-tagline {
          background: rgba(255,255,255,0.2);
          border-radius: 12px;
          padding: 12px 16px;
          font-size: 14px;
          font-weight: 600;
          backdrop-filter: blur(10px);
        }
        .mentorial-hub-hero .hero-tagline .number {
          font-size: 24px;
          font-weight: 800;
          color: #fbbf24;
        }
        
        .income-streams-title {
          text-align: center;
          color: #e6f1ff;
          font-size: 16px;
          font-weight: 700;
          margin: 24px 0 16px;
        }
        .income-streams-title span { color: #fbbf24; }
        
        .income-streams-grid {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 10px;
          margin-bottom: 10px;
        }
        .income-streams-grid.row-2 {
          grid-template-columns: repeat(2, 1fr);
          max-width: 70%;
          margin: 0 auto 20px;
        }
        .income-stream-card {
          background: rgba(22, 33, 62, 0.9);
          border-radius: 14px;
          padding: 16px 10px;
          text-align: center;
          border: 1px solid rgba(255,255,255,0.1);
          transition: all 0.3s;
        }
        .income-stream-card:hover {
          transform: translateY(-2px);
          border-color: rgba(102, 126, 234, 0.5);
        }
        .income-stream-card .stream-icon {
          width: 44px;
          height: 44px;
          border-radius: 12px;
          display: flex;
          align-items: center;
          justify-content: center;
          margin: 0 auto 10px;
          font-size: 22px;
        }
        .income-stream-card.ev .stream-icon { background: linear-gradient(135deg, #10b981, #059669); }
        .income-stream-card.solar .stream-icon { background: linear-gradient(135deg, #f59e0b, #d97706); }
        .income-stream-card.insurance .stream-icon { background: linear-gradient(135deg, #3b82f6, #2563eb); }
        .income-stream-card.training .stream-icon { background: linear-gradient(135deg, #8b5cf6, #7c3aed); }
        .income-stream-card.realestate .stream-icon { background: linear-gradient(135deg, #ec4899, #db2777); }
        .income-stream-card .stream-name {
          color: #e6f1ff;
          font-size: 11px;
          font-weight: 600;
          line-height: 1.3;
        }
        
        .lifetime-income-section {
          background: linear-gradient(135deg, #0d1b2a 0%, #1b2838 100%);
          border: 2px solid;
          border-image: linear-gradient(135deg, #fbbf24, #f59e0b) 1;
          border-radius: 16px;
          padding: 20px;
          margin-bottom: 20px;
          text-align: center;
        }
        .lifetime-income-section h3 {
          color: #fbbf24;
          font-size: 18px;
          font-weight: 700;
          margin: 0 0 16px;
        }
        .lifetime-income-section h3 span { color: #e6f1ff; font-weight: 500; }
        
        .earning-rates {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 12px;
          margin-bottom: 16px;
        }
        .earning-rate-card {
          background: rgba(255,255,255,0.05);
          border-radius: 12px;
          padding: 16px;
        }
        .earning-rate-card .rate-label {
          color: #8892b0;
          font-size: 11px;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          margin-bottom: 6px;
        }
        .earning-rate-card .rate-value {
          font-size: 36px;
          font-weight: 800;
          background: linear-gradient(135deg, #10b981, #34d399);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
        }
        .earning-rate-card .rate-desc {
          color: #8892b0;
          font-size: 11px;
          margin-top: 4px;
        }
        .earning-rate-card.lifetime .rate-value {
          background: linear-gradient(135deg, #fbbf24, #f59e0b);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
        }
        
        .lifetime-badge {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          background: linear-gradient(135deg, #fbbf24, #f59e0b);
          color: #451a03;
          padding: 10px 20px;
          border-radius: 30px;
          font-size: 13px;
          font-weight: 700;
        }
        
        .terms-card {
          background: rgba(22, 33, 62, 0.8);
          border-radius: 14px;
          padding: 18px;
          margin-bottom: 20px;
        }
        .terms-card h4 {
          color: #e6f1ff;
          font-size: 14px;
          margin: 0 0 14px;
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .terms-card ul {
          margin: 0;
          padding: 0;
          list-style: none;
        }
        .terms-card li {
          display: flex;
          align-items: flex-start;
          gap: 10px;
          color: #8892b0;
          font-size: 12px;
          margin-bottom: 10px;
          line-height: 1.5;
        }
        .terms-card li .check { color: #10b981; font-size: 14px; flex-shrink: 0; }
        
        .charges-card {
          background: linear-gradient(135deg, rgba(251, 191, 36, 0.1) 0%, rgba(245, 158, 11, 0.1) 100%);
          border: 1px solid rgba(251, 191, 36, 0.3);
          border-radius: 14px;
          padding: 18px;
          margin-bottom: 20px;
        }
        .charges-card h4 {
          color: #fbbf24;
          font-size: 14px;
          margin: 0 0 12px;
        }
        .charges-card ul {
          margin: 0;
          padding: 0;
          list-style: none;
        }
        .charges-card li {
          color: #fcd34d;
          font-size: 12px;
          margin-bottom: 8px;
          padding-left: 18px;
          position: relative;
        }
        .charges-card li::before {
          content: '•';
          position: absolute;
          left: 0;
          color: #f59e0b;
        }
        .charges-card .terms-note {
          margin: 14px 0 6px;
          font-size: 10px;
          color: rgba(156, 163, 175, 0.85);
          line-height: 1.5;
          font-style: italic;
        }
        .charges-card .terms-apply {
          margin: 0;
          font-size: 10px;
          color: rgba(156, 163, 175, 0.7);
          font-style: italic;
        }
        
        .stats-section {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 10px;
          margin-bottom: 20px;
        }
        .stat-box {
          background: rgba(22, 33, 62, 0.8);
          border-radius: 12px;
          padding: 16px 10px;
          text-align: center;
        }
        .stat-box .value {
          font-size: 22px;
          font-weight: 700;
          color: #10b981;
        }
        .stat-box .label {
          color: #8892b0;
          font-size: 10px;
          margin-top: 4px;
          text-transform: uppercase;
        }
        
        .cta-card {
          background: linear-gradient(135deg, #10b981 0%, #059669 100%);
          border-radius: 16px;
          padding: 24px 20px;
          text-align: center;
          color: white;
          margin-bottom: 20px;
        }
        .cta-card h4 {
          margin: 0 0 8px;
          font-size: 18px;
        }
        .cta-card p {
          margin: 0 0 16px;
          font-size: 13px;
          opacity: 0.9;
        }
        .cta-card .btn-cta {
          background: white;
          color: #059669;
          border: none;
          padding: 12px 28px;
          border-radius: 30px;
          font-size: 14px;
          font-weight: 700;
          cursor: pointer;
          display: inline-flex;
          align-items: center;
          gap: 8px;
        }
        
        .leads-section h3 {
          color: #e6f1ff;
          font-size: 15px;
          margin: 24px 0 12px;
        }
        .lead-row {
          background: rgba(22, 33, 62, 0.8);
          border-radius: 10px;
          padding: 14px;
          margin-bottom: 10px;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        .lead-row .name { color: #e6f1ff; font-weight: 600; font-size: 14px; }
        .lead-row .date { color: #8892b0; font-size: 11px; margin-top: 2px; }
        .lead-row .status {
          padding: 4px 10px;
          border-radius: 12px;
          font-size: 10px;
          font-weight: 600;
          text-transform: uppercase;
        }
        .lead-row .status.new { background: #3b82f6; color: white; }
        .lead-row .status.contacted { background: #f59e0b; color: white; }
        .lead-row .status.won, .lead-row .status.active { background: #10b981; color: white; }
      </style>
      
      <div class="mentorial-hub-hero">
        <div class="hero-badge">🏆 Premium Opportunity</div>
        <h1>Mentorial Hub</h1>
        <p class="hero-subtitle">One Franchise. Five Income Streams. Unlimited Potential.</p>
        <div class="hero-tagline">
          <span class="number">5</span> Business Verticals in <span class="number">1</span> Franchise
        </div>
      </div>
      
      <h4 class="income-streams-title">🔥 <span>Five Income Streams</span> Under One Roof</h4>
      
      <div class="income-streams-grid">
        <div class="income-stream-card ev">
          <div class="stream-icon">⚡</div>
          <div class="stream-name">EV Franchise</div>
        </div>
        <div class="income-stream-card solar">
          <div class="stream-icon">☀️</div>
          <div class="stream-name">Solar Franchise</div>
        </div>
        <div class="income-stream-card insurance">
          <div class="stream-icon">🛡️</div>
          <div class="stream-name">Insurance</div>
        </div>
      </div>
      <div class="income-streams-grid row-2">
        <div class="income-stream-card training">
          <div class="stream-icon">📚</div>
          <div class="stream-name">Training Academy</div>
        </div>
        <div class="income-stream-card realestate">
          <div class="stream-icon">🏠</div>
          <div class="stream-name">Real Estate</div>
        </div>
      </div>
      
      <div class="lifetime-income-section">
        <h3>💰 <span>Your Earning Potential</span></h3>
        <div class="earning-rates">
          <div class="earning-rate-card">
            <div class="rate-label">Setup Bonus</div>
            <div class="rate-value">2%</div>
            <div class="rate-desc">On initial franchise setup</div>
          </div>
          <div class="earning-rate-card lifetime">
            <div class="rate-label">Lifetime Revenue</div>
            <div class="rate-value">1%</div>
            <div class="rate-desc">On all future invoices</div>
          </div>
        </div>
        <div class="lifetime-badge">
          ♾️ Lifetime Passive Income Opportunity
        </div>
      </div>
      
      <div class="terms-card">
        <h4>📋 Eligibility for Lifetime Income</h4>
        <ul>
          <li><span class="check">✅</span> Franchise orders minimum <strong>5 units</strong> in any consecutive 2 months</li>
          <li><span class="check">✅</span> Maintain <strong>regular coordination</strong> with your franchise partner</li>
          <li><span class="check">✅</span> <strong>Showroom engagement</strong> - participate in customer interactions</li>
          <li><span class="check">✅</span> <strong>Support promotions</strong> and business initiatives</li>
          <li><span class="check">✅</span> Keep your <strong>MNR membership active</strong></li>
        </ul>
      </div>
      
      <div class="charges-card">
        <h4>⚠️ Applicable Charges</h4>
        <ul>
          <li><strong>1 Point = ₹1</strong> (Direct INR value)</li>
          <li><strong>2% TDS</strong> on all earnings</li>
          <li><strong>8% Admin Charges</strong> as per policy</li>
          <li>Subject to franchise compliance & order fulfillment</li>
        </ul>
        <p class="terms-note">*Above-mentioned percentage earnings are applicable on EV models and vehicles only. For other segments (Solar, Insurance, Real Estate, Training Academy), the earning structure will be decided from time to time.</p>
        <p class="terms-apply">Terms and conditions apply.</p>
      </div>
      
      <div class="stats-section">
        <div class="stat-box">
          <div class="value">${this.stats.total_leads}</div>
          <div class="label">Your Leads</div>
        </div>
        <div class="stat-box">
          <div class="value">${this.stats.active_franchises}</div>
          <div class="label">Active</div>
        </div>
        <div class="stat-box">
          <div class="value">₹${this.stats.total_earnings.toLocaleString()}</div>
          <div class="label">Earnings</div>
        </div>
      </div>
      
      <div class="cta-card">
        <h4>🚀 Start Earning Today</h4>
        <p>Refer a Mentorial Hub franchise partner and unlock lifetime passive income!</p>
        <button class="btn-cta" id="btnAddFranchiseLead">
          ➕ Add Franchise Lead
        </button>
      </div>
      
      ${this.leads.length>0?`
        <div class="leads-section">
          <h3>📋 Your Franchise Leads</h3>
          ${this.leads.map(t=>`
            <div class="lead-row">
              <div>
                <div class="name">${t.name}</div>
                <div class="date">${this.formatDate(t.created_at)}</div>
              </div>
              <span class="status ${t.status.toLowerCase()}">${t.status}</span>
            </div>
          `).join("")}
        </div>
      `:""}
    `,this.attachEventListeners()}}attachEventListeners(){const e=document.getElementById("btnAddFranchiseLead");e&&e.addEventListener("click",()=>this.showAddLeadModal())}async showAddLeadModal(){const e=document.createElement("div");e.className="modal-overlay",e.innerHTML=`
      <div class="modal-content">
        <div class="modal-header">
          <h3>Add Franchise Lead</h3>
          <button class="modal-close">&times;</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>Name *</label>
            <input type="text" id="franchiseLeadName" placeholder="Lead name" required>
          </div>
          <div class="form-group">
            <label>Mobile *</label>
            <input type="tel" id="franchiseLeadMobile" placeholder="Mobile number" required>
          </div>
          <div class="form-group">
            <label>Email</label>
            <input type="email" id="franchiseLeadEmail" placeholder="Email address">
          </div>
          <div class="form-group">
            <label>City/Location</label>
            <input type="text" id="franchiseLeadCity" placeholder="City or location">
          </div>
          <div class="form-group">
            <label>Notes</label>
            <textarea id="franchiseLeadNotes" placeholder="Additional notes about the franchise interest..." rows="3"></textarea>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" id="btnCancelFranchiseLead">Cancel</button>
          <button class="btn-primary" id="btnSaveFranchiseLead">Add Lead</button>
        </div>
      </div>
    `,document.body.appendChild(e),e.querySelector(".modal-close")?.addEventListener("click",()=>e.remove()),e.querySelector("#btnCancelFranchiseLead")?.addEventListener("click",()=>e.remove()),e.querySelector("#btnSaveFranchiseLead")?.addEventListener("click",()=>this.saveFranchiseLead(e)),e.addEventListener("click",t=>{t.target===e&&e.remove()})}async saveFranchiseLead(e){const t=document.getElementById("franchiseLeadName")?.value?.trim(),a=document.getElementById("franchiseLeadMobile")?.value?.trim(),i=document.getElementById("franchiseLeadEmail")?.value?.trim(),n=document.getElementById("franchiseLeadCity")?.value?.trim(),s=document.getElementById("franchiseLeadNotes")?.value?.trim();if(!t||!a){alert("Please enter name and mobile number");return}try{const r=await d.post("/crm/unified-my-leads?role=mnr",{name:t,mobile:a,email:i,category:"franchise",priority:"high",notes:s?`Location: ${n||"N/A"}
${s}`:n?`Location: ${n}`:"",source:"mobile_app"});r.success?(e.remove(),await this.loadData()):alert(r.error||"Failed to add franchise lead")}catch(r){console.error("[MNRFranchiseEarnings] Add lead failed:",r),alert("Failed to add franchise lead. Please try again.")}}formatDate(e){if(!e)return"";try{return new Date(e).toLocaleDateString("en-IN",{day:"numeric",month:"short",year:"numeric"})}catch{return e}}}class Ne{container;activeCampaigns=[];claimedBonanzas=[];loading=!0;filters={search:"",status:"all",date:"all",type:"all"};eligibility=null;constructor(e){this.container=e}async init(){this.render(),await this.loadData()}async loadData(){this.loading=!0,this.updateContent();try{const[e,t,a]=await Promise.all([d.get("/bonanza/my-bonanzas"),d.get("/bonanza/my-claimed"),d.get("/auth/me-hybrid?role=mnr")]);if(e.success&&e.data){const n=e.data.bonanzas||e.data||[];this.activeCampaigns=n.map(s=>this.mapCampaign(s))}if(t.success&&t.data){const n=t.data.claimed_bonanzas||t.data||[];this.claimedBonanzas=n.map(s=>this.mapClaimed(s))}const i=a?.data?.eligibility_status||a?.eligibility_status;i&&(this.eligibility={is_activated:i.is_activated||!1,kyc_status:i.kyc_status||"pending",program_utilisation_completed:i.program_utilisation_completed||!1,group_a_points:i.group_a_points||0,group_b_points:i.group_b_points||0,is_eligible:i.is_eligible||!1})}catch(e){console.error("[MNRBonanza] Failed to load:",e)}this.loading=!1,this.updateContent()}mapCampaign(e){const t=e.start_date?new Date(e.start_date).toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"numeric"}):"",a=e.end_date?new Date(e.end_date).toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"numeric"}):"";return{id:e.id||0,name:e.bonanza_name||e.name||"",campaign_period:`${t} - ${a}`,start_date:e.start_date,end_date:e.end_date,criteria:e.criteria_description||e.criteria||`${e.target_type||"Direct"} Activations`,target:e.target_value||e.target_requirement||e.target||0,your_progress:e.current_progress||e.current_value||e.progress||0,reward:e.is_monetary?`₹${(e.reward_amount||0).toLocaleString()} Cash`:e.award_name||e.reward||"",status:e.achievement_status||e.status||"In Progress",can_claim:e.can_claim||!1,type:e.target_type||e.bonanza_type||"Direct"}}mapClaimed(e){return{id:e.id||0,bonanza_name:e.bonanza_name||e.name||"",target_achieved:e.target_achieved||e.current_progress||0,target_required:e.target_required||e.target_value||0,reward:e.is_monetary?`₹${(e.reward_amount||0).toLocaleString()}`:e.award_name||e.reward||"",claimed_date:e.claimed_date||e.claimed_at||null,processed_status:e.processed_status||"Processing",dispatch_date:e.dispatch_date||null,received_date:e.received_date||null}}renderEligibilityBanner(){if(!this.eligibility)return"";const e=this.eligibility,t=e.is_activated,a=(e.kyc_status||"pending").toLowerCase()==="approved",i=e.program_utilisation_completed,n=(e.group_a_points||0)>=1,s=(e.group_b_points||0)>=1;return t&&a&&i&&n&&s?"":`
      <div class="eligibility-banner">
        <div class="banner-title">📋 Eligibility Checklist</div>
        <div class="banner-desc">Awards and bonanza benefits are unlocked after successful utilisation of an eligible product or service through the MNR Business Access Program.</div>
        <ul class="checklist">${[{done:t,label:"Account Activated"},{done:a,label:"KYC Approved"},{done:i,label:"Program Utilisation Completed"},{done:n,label:"Group A – Minimum 1 active & utilised business facilitation"},{done:s,label:"Group B – Minimum 1 active & utilised business facilitation"}].map(c=>`<li>${c.done?'<span class="done">✅</span>':'<span class="pending">⏳</span>'}<span>${c.label}</span></li>`).join("")}</ul>
      </div>
    `}render(){this.container.innerHTML=`
      <style>
        ${m.getStyles()}
        .mnr-bonanza-page { padding: 16px; background: #0d1b2a; min-height: 100vh; }
        .requirements-card {
          background: #fff3cd;
          border-radius: 12px;
          padding: 16px;
          margin-bottom: 16px;
          color: #664d03;
        }
        .requirements-card .req-header {
          display: flex;
          align-items: center;
          gap: 8px;
          font-weight: 600;
          font-size: 14px;
          margin-bottom: 10px;
        }
        .requirements-card .req-text {
          font-size: 13px;
          margin-bottom: 12px;
          line-height: 1.5;
        }
        .requirements-card .activities-header {
          font-weight: 600;
          font-size: 13px;
          margin-bottom: 8px;
        }
        .requirements-card .activities-list {
          list-style: none;
          padding: 0;
          margin: 0 0 12px 0;
        }
        .requirements-card .activities-list li {
          font-size: 12px;
          padding: 3px 0 3px 16px;
          position: relative;
        }
        .requirements-card .activities-list li::before {
          content: "•";
          position: absolute;
          left: 4px;
        }
        .requirements-card .note-text {
          font-size: 11px;
          padding: 10px;
          background: rgba(0,0,0,0.05);
          border-radius: 8px;
        }
        .campaign-info {
          background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
          border-radius: 12px;
          padding: 16px;
          margin-bottom: 16px;
          color: white;
        }
        .campaign-info strong { font-size: 14px; }
        .campaign-info .alert-text { color: #fecaca; font-weight: 600; }
        .filters-section {
          background: #1a2744;
          border-radius: 12px;
          padding: 16px;
          margin-bottom: 16px;
        }
        .filters-section .filter-row {
          display: flex;
          flex-wrap: wrap;
          gap: 12px;
        }
        .filters-section .filter-group {
          flex: 1;
          min-width: 140px;
        }
        .filters-section label {
          display: block;
          font-size: 11px;
          color: #8892b0;
          margin-bottom: 4px;
        }
        .filters-section input,
        .filters-section select {
          width: 100%;
          padding: 10px 12px;
          background: #0d1b2a;
          border: 1px solid #2d3a4f;
          border-radius: 8px;
          color: #e6f1ff;
          font-size: 13px;
        }
        .eligibility-banner {
          background: linear-gradient(135deg, #1a3a5c 0%, #1e3a5f 100%);
          border: 1px solid #2d5f8a;
          border-radius: 12px;
          padding: 16px;
          margin-bottom: 16px;
          color: #c5ddf0;
        }
        .eligibility-banner .banner-title { font-size: 14px; font-weight: 600; margin: 0 0 6px 0; color: #64d2ff; }
        .eligibility-banner .banner-desc { font-size: 12px; margin: 0 0 12px 0; color: #8892b0; line-height: 1.5; }
        .eligibility-banner .checklist { list-style: none; padding: 0; margin: 0; }
        .eligibility-banner .checklist li { font-size: 13px; padding: 4px 0; display: flex; align-items: center; gap: 8px; }
        .eligibility-banner .checklist li .done { color: #10b981; }
        .eligibility-banner .checklist li .pending { color: #f59e0b; }
        .section-title {
          color: #64d2ff;
          font-size: 16px;
          font-weight: 600;
          margin: 24px 0 16px 0;
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .table-container { margin-top: 8px; }
        .badge { padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; display: inline-block; }
        .badge-success { background: #10b981; color: white; }
        .badge-warning { background: #f59e0b; color: white; }
        .badge-pending { background: #6b7280; color: white; }
        .badge-info { background: #3b82f6; color: white; }
        .badge-danger { background: #ef4444; color: white; }
        .badge-primary { background: #8b5cf6; color: white; }
        .claim-btn {
          padding: 6px 12px;
          background: #10b981;
          color: white;
          border: none;
          border-radius: 6px;
          font-size: 12px;
          cursor: pointer;
        }
        .claim-btn:disabled {
          background: #4b5563;
          cursor: not-allowed;
        }
        .progress-bar-container {
          width: 100%;
          height: 8px;
          background: #374151;
          border-radius: 4px;
          overflow: hidden;
        }
        .progress-bar-fill {
          height: 100%;
          background: linear-gradient(90deg, #10b981, #34d399);
          border-radius: 4px;
          transition: width 0.3s;
        }
      </style>
      ${l.render({title:"🎉 Bonanza Awards",showBack:!0})}
      <div class="mnr-bonanza-page">
        <div id="pageContent"></div>
      </div>
    `,l.attachListeners({title:"🎉 Bonanza Awards",showBack:!0})}updateContent(){const e=document.getElementById("pageContent");if(!e)return;if(this.loading){e.innerHTML=`
        <div class="loading-state" style="text-align: center; padding: 40px; color: #8892b0;">
          <div class="spinner" style="width: 40px; height: 40px; border: 3px solid rgba(100,210,255,0.2); border-top-color: #64d2ff; border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto 16px;"></div>
          <p>Loading...</p>
        </div>
        <style>@keyframes spin { to { transform: rotate(360deg); } }</style>
      `;return}const t=this.getFilteredCampaigns();e.innerHTML=`
      ${this.renderEligibilityBanner()}

      <div class="requirements-card">
        <div class="req-header">
          <span>📹</span>
          <span>Feedback Video and Photos Requirement</span>
        </div>
        <p class="req-text">
          <strong>To claim Bonanza rewards:</strong> Sharing feedback videos and photos is important.
        </p>
        <div class="activities-header">Eligible Engagement Activities:</div>
        <ul class="activities-list">
          <li>Reels (video content)</li>
          <li>WhatsApp Status sharing</li>
          <li>Social Media posts</li>
          <li>Sharing & Ratings in Announcement sections</li>
          <li>Engaging with teams</li>
          <li>Attending Zoom calls</li>
        </ul>
        <div class="note-text">
          ℹ️ Submitted feedback may be publicly displayed for promotional purposes.
        </div>
      </div>

      <div class="campaign-info">
        <strong>🎁 Bonanza Campaigns:</strong> Time-limited special reward campaigns. 
        <span class="alert-text">Bonanzas must be claimed within 5 days after the campaign end date!</span>
      </div>

      <div class="filters-section">
        <div class="filter-row">
          <div class="filter-group">
            <label>Search</label>
            <input type="text" id="searchFilter" placeholder="Search bonanzas..." value="${this.filters.search}">
          </div>
          <div class="filter-group">
            <label>Status</label>
            <select id="statusFilter">
              <option value="all" ${this.filters.status==="all"?"selected":""}>All Status</option>
              <option value="achieved" ${this.filters.status==="achieved"?"selected":""}>Achieved</option>
              <option value="in_progress" ${this.filters.status==="in_progress"?"selected":""}>In Progress</option>
            </select>
          </div>
          <div class="filter-group">
            <label>Date</label>
            <select id="dateFilter">
              <option value="active" ${this.filters.date==="active"?"selected":""}>Active</option>
              <option value="all" ${this.filters.date==="all"?"selected":""}>All Time</option>
              <option value="ended" ${this.filters.date==="ended"?"selected":""}>Ended</option>
            </select>
          </div>
          <div class="filter-group">
            <label>Type</label>
            <select id="typeFilter">
              <option value="all" ${this.filters.type==="all"?"selected":""}>All Types</option>
              <option value="direct" ${this.filters.type==="direct"?"selected":""}>Direct Business Facilitation</option>
              <option value="matching" ${this.filters.type==="matching"?"selected":""}>Group Performance</option>
            </select>
          </div>
        </div>
      </div>

      <h3 class="section-title">🎯 Bonanza Campaigns</h3>
      <div class="table-container">
        ${this.renderCampaignsTable(t)}
      </div>

      <h3 class="section-title">✅ My Claimed Bonanzas</h3>
      <div class="table-container">
        ${this.renderClaimedTable()}
      </div>
    `,this.attachListeners()}getFilteredCampaigns(){return this.activeCampaigns.filter(e=>!(this.filters.search&&!e.name.toLowerCase().includes(this.filters.search.toLowerCase())||this.filters.status==="achieved"&&e.status.toLowerCase()!=="achieved"||this.filters.status==="in_progress"&&e.status.toLowerCase()==="achieved"||this.filters.type!=="all"&&e.type.toLowerCase()!==this.filters.type.toLowerCase()||this.filters.date==="active"&&e.end_date&&new Date(e.end_date)<new Date||this.filters.date==="ended"&&e.end_date&&new Date(e.end_date)>=new Date))}renderCampaignsTable(e){return e.length===0?`<div class="empty-state" style="text-align: center; padding: 40px; color: #8892b0;">
        <div style="font-size: 48px; margin-bottom: 16px;">🎯</div>
        <p>No active bonanza campaigns</p>
      </div>`:new m({columns:[{key:"name",label:"Bonanza Name",render:a=>`<strong style="color: #f59e0b;">${a}</strong>`},{key:"campaign_period",label:"Campaign Period"},{key:"criteria",label:"Criteria"},{key:"target",label:"Target",render:a=>`<span style="color: #3b82f6; font-weight: 600;">${a}</span>`},{key:"your_progress",label:"Your Progress",render:(a,i)=>{const n=Math.min(100,Math.round(a/i.target*100));return`
            <div style="min-width: 80px;">
              <div style="font-size: 12px; margin-bottom: 4px;">${a}/${i.target}</div>
              <div class="progress-bar-container">
                <div class="progress-bar-fill" style="width: ${n}%"></div>
              </div>
            </div>
          `}},{key:"reward",label:"Reward",render:a=>`<strong style="color: #10b981;">${a}</strong>`},{key:"status",label:"Status",render:a=>this.getStatusBadge(a)},{key:"id",label:"Action",render:(a,i)=>i.can_claim?`<button class="claim-btn" data-id="${a}">🎁 Claim</button>`:i.status.toLowerCase()==="achieved"?'<span class="badge badge-success">Claimed</span>':'<span style="color: #6b7280; font-size: 11px;">Keep Going!</span>'}],data:e,loading:!1,emptyMessage:"No campaigns found"}).render()}renderClaimedTable(){return this.claimedBonanzas.length===0?`<div class="empty-state" style="text-align: center; padding: 40px; color: #8892b0;">
        <div style="font-size: 48px; margin-bottom: 16px;">📦</div>
        <p>No claimed bonanzas yet</p>
      </div>`:new m({columns:[{key:"bonanza_name",label:"Bonanza"},{key:"target_achieved",label:"Target Achieved",render:(t,a)=>`${t} / ${a.target_required}`},{key:"reward",label:"Reward",render:t=>`<strong style="color: #10b981;">${t}</strong>`},{key:"claimed_date",label:"Claimed Date",render:t=>this.formatDate(t)},{key:"processed_status",label:"Status",render:t=>this.getProcessedBadge(t)},{key:"dispatch_date",label:"Dispatch Date",render:t=>this.formatDate(t)},{key:"received_date",label:"Received Date",render:t=>this.formatDate(t)}],data:this.claimedBonanzas,loading:!1,emptyMessage:"No claimed bonanzas"}).render()}attachListeners(){const e=document.getElementById("searchFilter"),t=document.getElementById("statusFilter"),a=document.getElementById("dateFilter"),i=document.getElementById("typeFilter");e&&e.addEventListener("input",n=>{this.filters.search=n.target.value,this.updateContent()}),t&&t.addEventListener("change",n=>{this.filters.status=n.target.value,this.updateContent()}),a&&a.addEventListener("change",n=>{this.filters.date=n.target.value,this.updateContent()}),i&&i.addEventListener("change",n=>{this.filters.type=n.target.value,this.updateContent()}),document.querySelectorAll(".claim-btn").forEach(n=>{n.addEventListener("click",async()=>{const s=n.getAttribute("data-id");s&&await this.claimBonanza(parseInt(s))})})}async claimBonanza(e){try{const t=await d.post(`/bonanza/claim/${e}`,{});t.success?(alert("Bonanza claimed successfully!"),await this.loadData()):alert(t.error||"Failed to claim bonanza")}catch(t){console.error("[MNRBonanza] Claim failed:",t),alert("Failed to claim bonanza. Please try again.")}}getStatusBadge(e){const t=e.toLowerCase();return t==="achieved"?'<span class="badge badge-success">✓ Achieved</span>':t==="in progress"?'<span class="badge badge-warning">⊙ In Progress</span>':`<span class="badge badge-pending">${e}</span>`}getProcessedBadge(e){const t=(e||"").toLowerCase(),a=this.getSimplifiedStatus(t);return a==="Pending"||a==="Claimed"?'<span class="badge badge-warning">⊙ '+a+"</span>":a==="Approved"?'<span class="badge badge-info">✓ Approved</span>':a==="Processed"?'<span class="badge badge-primary">⊞ Processed</span>':a==="Completed"?'<span class="badge badge-success">✓ Completed</span>':a==="Rejected"?'<span class="badge badge-danger">✗ Rejected</span>':`<span class="badge badge-pending">${a}</span>`}getSimplifiedStatus(e){return e==="pending approval"||e==="pending"?"Claimed":e==="admin approved"?"Approved":e==="procurement pending"||e==="processed for dispatch"||e==="dispatched"||e==="ordered"?"Processed":e==="delivered"||e==="delivered - completed"?"Completed":e==="rejected"?"Rejected":e||"Pending"}formatDate(e){if(!e)return'<span style="color: #6b7280;">-</span>';try{return new Date(e).toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"numeric"})}catch{return e}}}class Te{container;progress={total_purchased:0,total_activated:0,total_transferred:0,total_available:0,total_amount:0};pins=[];loading=!0;constructor(e){this.container=e}async init(){this.render(),await this.loadProgress()}async loadProgress(){this.loading=!0,this.updateContent();try{const e=await d.get("/users/pins");if(e.success&&e.data){const t=e.data.pins||e.data||[];this.pins=t,this.progress={total_purchased:t.length,total_activated:t.filter(a=>(a.status||"").toLowerCase()==="used"||(a.status||"").toLowerCase()==="activated").length,total_transferred:t.filter(a=>(a.status||"").toLowerCase()==="transferred").length,total_available:t.filter(a=>(a.status||"").toLowerCase()==="active"||(a.status||"").toLowerCase()==="available").length,total_amount:t.reduce((a,i)=>a+(i.amount||i.value||0),0)}}}catch(e){console.error("[MNRCouponProgress] Failed to load:",e)}this.loading=!1,this.updateContent()}render(){this.container.innerHTML=l.render({title:"Coupon Progress",showBack:!0});const e=document.createElement("div");e.id="coupon-progress-content",e.className="page-content",this.container.appendChild(e),this.updateContent()}updateContent(){const e=document.getElementById("coupon-progress-content");if(!e)return;if(this.loading){e.innerHTML=`
        <div style="display:flex;justify-content:center;align-items:center;padding:60px 20px;">
          <div style="width:36px;height:36px;border:3px solid #e2e8f0;border-top-color:#667eea;border-radius:50%;animation:spin 1s linear infinite;"></div>
        </div>
        <style>@keyframes spin{to{transform:rotate(360deg)}}</style>
      `;return}const t=this.progress,a=t.total_purchased>0?Math.round(t.total_activated/t.total_purchased*100):0;e.innerHTML=`
      <div style="padding:16px;">
        <div style="background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);border-radius:16px;padding:20px;color:#fff;margin-bottom:16px;">
          <div style="font-size:13px;opacity:0.9;">Total Coupons Purchased</div>
          <div style="font-size:32px;font-weight:700;margin:4px 0;">${t.total_purchased}</div>
          <div style="font-size:13px;opacity:0.8;">Total Value: ₹${t.total_amount.toLocaleString("en-IN")}</div>
        </div>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px;">
          <div style="background:#fff;border-radius:12px;padding:16px;box-shadow:0 2px 8px rgba(0,0,0,0.06);">
            <div style="font-size:12px;color:#64748b;">Activated</div>
            <div style="font-size:24px;font-weight:700;color:#10b981;">${t.total_activated}</div>
          </div>
          <div style="background:#fff;border-radius:12px;padding:16px;box-shadow:0 2px 8px rgba(0,0,0,0.06);">
            <div style="font-size:12px;color:#64748b;">Available</div>
            <div style="font-size:24px;font-weight:700;color:#3b82f6;">${t.total_available}</div>
          </div>
          <div style="background:#fff;border-radius:12px;padding:16px;box-shadow:0 2px 8px rgba(0,0,0,0.06);">
            <div style="font-size:12px;color:#64748b;">Transferred</div>
            <div style="font-size:24px;font-weight:700;color:#f59e0b;">${t.total_transferred}</div>
          </div>
          <div style="background:#fff;border-radius:12px;padding:16px;box-shadow:0 2px 8px rgba(0,0,0,0.06);">
            <div style="font-size:12px;color:#64748b;">Activation Rate</div>
            <div style="font-size:24px;font-weight:700;color:#8b5cf6;">${a}%</div>
          </div>
        </div>

        <div style="background:#fff;border-radius:12px;padding:16px;box-shadow:0 2px 8px rgba(0,0,0,0.06);margin-bottom:16px;">
          <div style="font-size:14px;font-weight:600;color:#1e293b;margin-bottom:12px;">Progress</div>
          <div style="background:#e2e8f0;border-radius:8px;height:12px;overflow:hidden;">
            <div style="background:linear-gradient(90deg,#10b981,#3b82f6);height:100%;width:${a}%;border-radius:8px;transition:width 0.5s ease;"></div>
          </div>
          <div style="display:flex;justify-content:space-between;margin-top:8px;font-size:12px;color:#64748b;">
            <span>${t.total_activated} activated</span>
            <span>${t.total_purchased} total</span>
          </div>
        </div>

        ${this.pins.length===0?`
          <div style="text-align:center;padding:40px 20px;color:#94a3b8;">
            <div style="font-size:48px;margin-bottom:12px;">🎫</div>
            <div style="font-size:16px;font-weight:500;">No Coupons Yet</div>
            <div style="font-size:13px;margin-top:4px;">Purchase coupons to see your progress here</div>
          </div>
        `:`
          <div style="font-size:14px;font-weight:600;color:#1e293b;margin-bottom:8px;">Recent Activity</div>
          ${this.pins.slice(0,10).map(i=>`
            <div style="background:#fff;border-radius:10px;padding:12px 14px;margin-bottom:8px;box-shadow:0 1px 4px rgba(0,0,0,0.05);display:flex;justify-content:space-between;align-items:center;">
              <div>
                <div style="font-size:13px;font-weight:600;color:#1e293b;">${i.coupon_code||i.code||i.pin_code||"PIN"}</div>
                <div style="font-size:11px;color:#94a3b8;">${i.coupon_type||i.package_type||i.type||"Standard"}</div>
              </div>
              <div style="text-align:right;">
                <div style="font-size:12px;font-weight:600;padding:2px 10px;border-radius:20px;background:${this.getStatusColor(i.status)};color:#fff;">
                  ${(i.status||"Unknown").toUpperCase()}
                </div>
                <div style="font-size:11px;color:#94a3b8;margin-top:4px;">₹${(i.amount||i.value||0).toLocaleString("en-IN")}</div>
              </div>
            </div>
          `).join("")}
        `}
      </div>
    `}getStatusColor(e){switch((e||"").toLowerCase()){case"active":case"available":return"#3b82f6";case"used":case"activated":return"#10b981";case"transferred":return"#f59e0b";case"expired":return"#ef4444";default:return"#94a3b8"}}}class Re{container;constructor(e){this.container=e}async init(){this.render()}render(){this.container.innerHTML=l.render({title:"Settings",showBack:!0});const e=document.createElement("div");e.className="page-content",e.innerHTML=`
      <div style="padding:16px;">
        <div style="font-size:14px;font-weight:600;color:#94a3b8;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:12px;padding:0 4px;">Account</div>
        
        ${this.menuItem("Edit Profile","user","mnr-profile-edit")}
        ${this.menuItem("KYC Verification","file-text","mnr-kyc")}
        ${this.menuItem("Bank Details","credit-card","mnr-bank")}
        ${this.menuItem("Change Password","lock","mnr-change-password")}

        <div style="font-size:14px;font-weight:600;color:#94a3b8;text-transform:uppercase;letter-spacing:0.5px;margin:24px 0 12px;padding:0 4px;">Support</div>
        
        ${this.menuItem("Feedback","message-circle","mnr-feedback")}
        ${this.menuItem("Announcements","bell","mnr-announcements")}
      </div>
    `,this.container.appendChild(e),e.querySelectorAll("[data-route]").forEach(t=>{t.addEventListener("click",()=>{const a=t.dataset.route;a&&f.navigate(a)})})}menuItem(e,t,a){return`
      <div data-route="${a}" style="background:#fff;border-radius:12px;padding:14px 16px;margin-bottom:8px;box-shadow:0 1px 4px rgba(0,0,0,0.05);display:flex;align-items:center;justify-content:space-between;cursor:pointer;">
        <div style="display:flex;align-items:center;gap:12px;">
          <div style="width:36px;height:36px;border-radius:10px;background:#f1f5f9;display:flex;align-items:center;justify-content:center;">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#667eea" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${this.getIcon(t)}</svg>
          </div>
          <span style="font-size:14px;font-weight:500;color:#1e293b;">${e}</span>
        </div>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#cbd5e1" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
      </div>
    `}getIcon(e){return{user:'<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',"file-text":'<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>',"credit-card":'<rect x="1" y="4" width="22" height="16" rx="2" ry="2"/><line x1="1" y1="10" x2="23" y2="10"/>',lock:'<rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',"message-circle":'<path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>',bell:'<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/>'}[e]||""}}export{Ie as A,de as B,$e as C,Ce as D,Me as E,he as F,be as G,pe as H,ie as I,ne as J,re as K,Re as L,Ae as M,T as N,oe as a,ye as b,ve as c,xe as d,se as e,le as f,ae as g,Ne as h,ce as i,_e as j,we as k,Te as l,ke as m,Le as n,ue as o,ee as p,ge as q,me as r,Be as s,fe as t,ze as u,te as v,Se as w,De as x,Pe as y,Ee as z};
