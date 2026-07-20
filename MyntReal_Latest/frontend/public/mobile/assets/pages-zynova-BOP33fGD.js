import{b as n,r as o}from"./services-AEce4KDH.js";import{P as a}from"./components-9q5I9H7Z.js";class g{container;data=null;loading=!0;constructor(e){this.container=e}async init(){this.render(),await this.loadData()}async loadData(){this.loading=!0,this.updateContent();try{const e=await n.get("/users/zynova/real-estate");e.success&&e.data&&(this.data=e.data)}catch(e){console.error("[ZynovaRealEstate] Failed to load:",e)}this.loading=!1,this.updateContent()}render(){this.container.innerHTML=`
      <style>
        .zynova-realestate-page {
          background: #0d1b2a;
          min-height: 100vh;
        }
        .zynova-realestate-page .page-content {
          padding: 16px;
        }
        .zynova-header-card {
          background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
          border-radius: 12px;
          padding: 16px;
          margin-bottom: 16px;
          color: white;
        }
        .zynova-header-card .header-title {
          display: flex;
          align-items: center;
          gap: 10px;
          margin-bottom: 6px;
        }
        .zynova-header-card .header-title h2 {
          font-size: 18px;
          margin: 0;
          font-weight: 600;
        }
        .zynova-header-card .segment-badge {
          background: rgba(0,0,0,0.2);
          padding: 4px 10px;
          border-radius: 12px;
          font-size: 11px;
          font-weight: 600;
        }
        .zynova-header-card .header-subtitle {
          font-size: 13px;
          opacity: 0.9;
          margin: 0;
        }
        .requirements-card {
          background: #1a2744;
          border-radius: 12px;
          padding: 16px;
          margin-bottom: 16px;
        }
        .requirements-card .req-header {
          display: flex;
          align-items: center;
          gap: 8px;
          color: #f59e0b;
          font-weight: 600;
          font-size: 14px;
          margin-bottom: 12px;
        }
        .requirements-card .req-text {
          color: #8892b0;
          font-size: 13px;
          margin-bottom: 16px;
          line-height: 1.5;
        }
        .requirements-card .activities-header {
          color: #e6f1ff;
          font-weight: 600;
          font-size: 13px;
          margin-bottom: 10px;
        }
        .requirements-card .activities-list {
          list-style: none;
          padding: 0;
          margin: 0 0 16px 0;
        }
        .requirements-card .activities-list li {
          color: #8892b0;
          font-size: 13px;
          padding: 4px 0 4px 20px;
          position: relative;
        }
        .requirements-card .activities-list li::before {
          content: "•";
          position: absolute;
          left: 6px;
          color: #64ffda;
        }
        .requirements-card .note-text {
          display: flex;
          align-items: flex-start;
          gap: 8px;
          color: #8892b0;
          font-size: 12px;
          padding: 12px;
          background: rgba(100, 255, 218, 0.05);
          border-radius: 8px;
          line-height: 1.4;
        }
        .requirements-card .note-text .note-icon {
          color: #64ffda;
          flex-shrink: 0;
        }
        .welcome-section {
          background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
          border-radius: 16px;
          padding: 32px 20px;
          text-align: center;
          color: white;
        }
        .welcome-section .welcome-icon {
          font-size: 48px;
          margin-bottom: 16px;
        }
        .welcome-section h3 {
          font-size: 20px;
          font-weight: 700;
          margin: 0 0 12px 0;
        }
        .welcome-section .quote {
          font-style: italic;
          font-size: 13px;
          opacity: 0.9;
          margin-bottom: 20px;
          line-height: 1.5;
        }
        .welcome-section .membership-status {
          font-size: 14px;
          margin-bottom: 8px;
        }
        .welcome-section .sub-text {
          font-size: 13px;
          opacity: 0.9;
          margin-bottom: 20px;
          line-height: 1.5;
        }
        .welcome-section .cta-btn {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          background: white;
          color: #2563eb;
          padding: 12px 24px;
          border-radius: 8px;
          font-weight: 600;
          font-size: 14px;
          border: none;
          cursor: pointer;
        }
        .welcome-section .progress-note {
          margin-top: 16px;
          font-size: 12px;
          opacity: 0.8;
        }
        .progress-card {
          background: #1a2744;
          border-radius: 12px;
          padding: 16px;
          margin-bottom: 16px;
        }
        .progress-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 12px;
        }
        .progress-title {
          color: #e6f1ff;
          font-weight: 600;
          font-size: 14px;
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .current-role {
          background: linear-gradient(135deg, #f59e0b, #d97706);
          color: white;
          padding: 4px 10px;
          border-radius: 12px;
          font-size: 11px;
          font-weight: 600;
        }
        .progress-stats {
          display: flex;
          gap: 16px;
          margin-bottom: 12px;
        }
        .progress-stat {
          flex: 1;
          text-align: center;
          background: rgba(100, 255, 218, 0.05);
          border-radius: 8px;
          padding: 10px;
        }
        .progress-stat-value {
          color: #64ffda;
          font-size: 16px;
          font-weight: 700;
        }
        .progress-stat-label {
          color: #8892b0;
          font-size: 11px;
          margin-top: 2px;
        }
        .progress-bar-container {
          background: rgba(255,255,255,0.1);
          border-radius: 8px;
          height: 12px;
          overflow: hidden;
          margin-bottom: 8px;
        }
        .progress-bar-fill {
          height: 100%;
          background: linear-gradient(90deg, #f59e0b, #fbbf24);
          border-radius: 8px;
          transition: width 0.5s ease;
        }
        .progress-target-info {
          display: flex;
          justify-content: space-between;
          align-items: center;
          color: #8892b0;
          font-size: 12px;
        }
        .progress-percent {
          color: #64ffda;
          font-weight: 600;
        }
        .next-role-badge {
          color: #fbbf24;
          font-weight: 600;
        }
        .highest-rank-badge {
          background: linear-gradient(135deg, #10b981, #059669);
          color: white;
          padding: 8px 16px;
          border-radius: 8px;
          font-size: 13px;
          font-weight: 600;
          text-align: center;
          margin-top: 8px;
        }
        .role-display-card {
          background: linear-gradient(135deg, #f59e0b, #d97706);
          color: white;
        }
        .role-display {
          text-align: center;
          padding: 8px 0;
        }
        .role-display .role-label {
          font-size: 12px;
          opacity: 0.9;
          margin-bottom: 4px;
        }
        .role-display .role-name {
          font-size: 24px;
          font-weight: 700;
          margin-bottom: 8px;
        }
        .role-display .next-role-info {
          font-size: 13px;
          opacity: 0.9;
        }
        .progress-target-info strong {
          color: #64ffda;
        }
        .journey-preview {
          background: #1a2744;
          border-radius: 16px;
          padding: 20px;
          margin-top: 16px;
        }
        .journey-header {
          text-align: center;
          margin-bottom: 20px;
        }
        .journey-header span {
          font-size: 28px;
          display: block;
          margin-bottom: 8px;
        }
        .journey-header h4 {
          color: #f59e0b;
          font-size: 18px;
          font-weight: 700;
          margin: 0 0 6px 0;
        }
        .journey-header p {
          color: #8892b0;
          font-size: 13px;
          margin: 0;
        }
        .journey-steps {
          display: flex;
          flex-direction: column;
          gap: 12px;
          margin-bottom: 16px;
        }
        .journey-step {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 12px 16px;
          border-radius: 12px;
          background: rgba(255,255,255,0.05);
        }
        .journey-step .step-icon {
          font-size: 24px;
          width: 44px;
          height: 44px;
          display: flex;
          align-items: center;
          justify-content: center;
          border-radius: 50%;
        }
        .step-promoter .step-icon { background: linear-gradient(135deg, #10b981, #059669); }
        .step-team-leader .step-icon { background: linear-gradient(135deg, #3b82f6, #2563eb); }
        .step-zonal-manager .step-icon { background: linear-gradient(135deg, #8b5cf6, #7c3aed); }
        .step-director .step-icon { background: linear-gradient(135deg, #f59e0b, #d97706); }
        .journey-step .step-info { flex: 1; }
        .journey-step .step-title {
          color: #e6f1ff;
          font-weight: 600;
          font-size: 14px;
          margin-bottom: 2px;
        }
        .journey-step .step-desc {
          color: #8892b0;
          font-size: 12px;
        }
        .step-arrow {
          text-align: center;
          color: #4a5568;
          font-size: 16px;
          display: none;
        }
        .journey-motivation {
          background: rgba(245, 158, 11, 0.1);
          border: 1px solid rgba(245, 158, 11, 0.3);
          border-radius: 10px;
          padding: 12px 16px;
          display: flex;
          align-items: center;
          gap: 10px;
          color: #fbbf24;
          font-size: 13px;
          font-weight: 500;
        }
      </style>
      <div class="page-container zynova-realestate-page">
        ${a.render({title:"VGK Real Dreams",showBack:!0})}
        
        <div id="pageContent" class="page-content">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
    `,a.attachListeners({title:"VGK Real Dreams",showBack:!0})}updateContent(){const e=document.getElementById("pageContent");if(!e)return;if(this.loading){e.innerHTML='<div class="loading-state">Loading...</div>';return}const t=this.data?.is_member||!1;e.innerHTML=`
      <div class="zynova-header-card">
        <div class="header-title">
          <span>🏠</span>
          <h2>VGK Real Dreams</h2>
          <span class="segment-badge">Real Estate</span>
        </div>
        <p class="header-subtitle">Your Real Estate Zynova Program - Build your team and grow your income</p>
      </div>

      <div class="requirements-card">
        <div class="req-header">
          <span>📹</span>
          <span>Feedback Video and Photos Requirement</span>
        </div>
        <p class="req-text">
          <strong>For Zynova incentive eligibility:</strong> Sharing feedback videos and photos is mandatory for members activated before 1st Dec 2025.
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
          <span class="note-icon">ℹ️</span>
          <span>Please note: Submitted feedback videos and photos may be publicly displayed on our platforms for promotional and community engagement purposes. By sharing your content, you acknowledge and consent to this use.</span>
        </div>
      </div>

      ${t?this.renderMemberContent():this.renderNonMemberContent()}
    `,this.attachEventListeners()}formatCurrency(e){return"₹"+(e||0).toLocaleString("en-IN")}renderMemberContent(){const e=this.data,t=e.promotion_progress||{progress:0,remaining:0},r=e.current_role_display||"Promoter",s=e.next_role_display,i=(e.current_role||"promoter")==="director"||!s||s==="Top Level";return`
      <div class="progress-card role-display-card">
        <div class="role-display">
          <div class="role-label">Your Current Role</div>
          <div class="role-name">${r}</div>
          <div class="next-role-info">${i?"🏆 Highest Level Achieved!":`Next: ${s}`}</div>
        </div>
      </div>

      <div class="progress-card">
        <div class="progress-header">
          <div class="progress-title">
            <span>📊</span>
            <span>Progress to Next Promotion</span>
          </div>
        </div>
        
        <div class="progress-stats">
          <div class="progress-stat">
            <div class="progress-stat-value">${this.formatCurrency(e.self_revenue||0)}</div>
            <div class="progress-stat-label">Self Revenue</div>
          </div>
          <div class="progress-stat">
            <div class="progress-stat-value">${this.formatCurrency(e.team_revenue||0)}</div>
            <div class="progress-stat-label">Team Revenue</div>
          </div>
        </div>

        ${i?`
          <div class="highest-rank-badge">
            🏆 You have reached the highest level!
          </div>
        `:`
          <div class="progress-bar-container">
            <div class="progress-bar-fill" style="width: ${t.progress||0}%"></div>
          </div>
          <div class="progress-target-info">
            <span>Current: <strong>${this.formatCurrency(e.total_revenue||0)}</strong></span>
            <span>Target: <strong>${this.formatCurrency(e.promotion_target||0)}</strong></span>
          </div>
          <div class="progress-target-info" style="margin-top: 6px;">
            <span class="progress-percent">${t.progress||0}% complete</span>
            <span>${t.remaining>0?this.formatCurrency(t.remaining)+" more needed":"Ready for promotion!"}</span>
          </div>
        `}
      </div>

      <div class="progress-card">
        <div class="progress-header">
          <div class="progress-title">
            <span>💰</span>
            <span>Earnings Summary</span>
          </div>
        </div>
        <div class="progress-stats">
          <div class="progress-stat">
            <div class="progress-stat-value">${this.formatCurrency(e.earnings?.pending||0)}</div>
            <div class="progress-stat-label">Pending</div>
          </div>
          <div class="progress-stat">
            <div class="progress-stat-value">${this.formatCurrency(e.earnings?.approved||0)}</div>
            <div class="progress-stat-label">Approved</div>
          </div>
        </div>
        <div class="progress-stats" style="margin-top: 8px;">
          <div class="progress-stat">
            <div class="progress-stat-value">${this.formatCurrency(e.earnings?.disbursed||0)}</div>
            <div class="progress-stat-label">Disbursed</div>
          </div>
          <div class="progress-stat">
            <div class="progress-stat-value">${this.formatCurrency(e.earnings?.total||0)}</div>
            <div class="progress-stat-label">Total</div>
          </div>
        </div>
      </div>

      <div class="welcome-section">
        <div class="welcome-icon">🌳</div>
        <h3>Keep Growing!</h3>
        <p class="sub-text">Add more leads and work with your team to unlock amazing rewards!</p>
        <button class="cta-btn" id="btnMyLeads">
          <span>👤</span>
          <span>My Leads</span>
        </button>
      </div>
    `}renderNonMemberContent(){return`
      <div class="journey-preview">
        <div class="journey-header">
          <span>🚀</span>
          <h4>Your Growth Journey</h4>
          <p>Unlock your potential and rise through the ranks</p>
        </div>
        <div class="journey-steps">
          <div class="journey-step step-promoter">
            <div class="step-icon">🌱</div>
            <div class="step-info">
              <div class="step-title">Promoter</div>
              <div class="step-desc">Plant the seeds of success</div>
            </div>
          </div>
          <div class="step-arrow">→</div>
          <div class="journey-step step-team-leader">
            <div class="step-icon">👥</div>
            <div class="step-info">
              <div class="step-title">Team Leader</div>
              <div class="step-desc">Build your winning team</div>
            </div>
          </div>
          <div class="step-arrow">→</div>
          <div class="journey-step step-zonal-manager">
            <div class="step-icon">🗺️</div>
            <div class="step-info">
              <div class="step-title">Zonal Manager</div>
              <div class="step-desc">Expand your territory</div>
            </div>
          </div>
          <div class="step-arrow">→</div>
          <div class="journey-step step-director">
            <div class="step-icon">👑</div>
            <div class="step-info">
              <div class="step-title">Director</div>
              <div class="step-desc">Lead the empire</div>
            </div>
          </div>
        </div>
        <div class="journey-motivation">
          <span>💡</span>
          <span>Every expert was once a beginner. Start your journey today!</span>
        </div>
      </div>

      <div class="welcome-section">
        <div class="welcome-icon">🌳</div>
        <h3>Welcome to VGK Real Dreams</h3>
        <p class="quote">"The best time to plant a tree was 20 years ago. The second best time is now."</p>
        <p class="membership-status">You are not yet a member of the Real Estate Zynova program.</p>
        <p class="sub-text">Add leads and work with your team to unlock amazing rewards!</p>
        <button class="cta-btn" id="btnMyLeads">
          <span>👤</span>
          <span>My Leads</span>
        </button>
        <p class="progress-note">Start adding leads to begin your progress</p>
      </div>
    `}attachEventListeners(){const e=document.getElementById("btnMyLeads");e&&e.addEventListener("click",()=>{o.navigate("mnr-my-leads")})}}class v{container;data=null;loading=!0;constructor(e){this.container=e}async init(){this.render(),await this.loadData()}async loadData(){this.loading=!0,this.updateContent();try{const e=await n.get("/users/zynova/insurance");e.success&&e.data&&(this.data=e.data)}catch(e){console.error("[ZynovaInsurance] Failed to load:",e)}this.loading=!1,this.updateContent()}render(){this.container.innerHTML=`
      <style>
        .zynova-insurance-page {
          background: #0d1b2a;
          min-height: 100vh;
        }
        .zynova-insurance-page .page-content {
          padding: 16px;
        }
        .zynova-header-card {
          background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
          border-radius: 12px;
          padding: 16px;
          margin-bottom: 16px;
          color: white;
        }
        .zynova-header-card .header-title {
          display: flex;
          align-items: center;
          gap: 10px;
          margin-bottom: 6px;
        }
        .zynova-header-card .header-title h2 {
          font-size: 18px;
          margin: 0;
          font-weight: 600;
        }
        .zynova-header-card .segment-badge {
          background: rgba(0,0,0,0.2);
          padding: 4px 10px;
          border-radius: 12px;
          font-size: 11px;
          font-weight: 600;
        }
        .zynova-header-card .header-subtitle {
          font-size: 13px;
          opacity: 0.9;
          margin: 0;
        }
        .requirements-card {
          background: #1a2744;
          border-radius: 12px;
          padding: 16px;
          margin-bottom: 16px;
        }
        .requirements-card .req-header {
          display: flex;
          align-items: center;
          gap: 8px;
          color: #ef4444;
          font-weight: 600;
          font-size: 14px;
          margin-bottom: 12px;
        }
        .requirements-card .req-text {
          color: #8892b0;
          font-size: 13px;
          margin-bottom: 16px;
          line-height: 1.5;
        }
        .requirements-card .activities-header {
          color: #e6f1ff;
          font-weight: 600;
          font-size: 13px;
          margin-bottom: 10px;
        }
        .requirements-card .activities-list {
          list-style: none;
          padding: 0;
          margin: 0 0 16px 0;
        }
        .requirements-card .activities-list li {
          color: #8892b0;
          font-size: 13px;
          padding: 4px 0 4px 20px;
          position: relative;
        }
        .requirements-card .activities-list li::before {
          content: "•";
          position: absolute;
          left: 6px;
          color: #64ffda;
        }
        .requirements-card .note-text {
          display: flex;
          align-items: flex-start;
          gap: 8px;
          color: #8892b0;
          font-size: 12px;
          padding: 12px;
          background: rgba(100, 255, 218, 0.05);
          border-radius: 8px;
          line-height: 1.4;
        }
        .requirements-card .note-text .note-icon {
          color: #64ffda;
          flex-shrink: 0;
        }
        .welcome-section {
          background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
          border-radius: 16px;
          padding: 32px 20px;
          text-align: center;
          color: white;
        }
        .welcome-section .welcome-icon {
          font-size: 48px;
          margin-bottom: 16px;
        }
        .welcome-section h3 {
          font-size: 20px;
          font-weight: 700;
          margin: 0 0 12px 0;
        }
        .welcome-section .quote {
          font-style: italic;
          font-size: 13px;
          opacity: 0.9;
          margin-bottom: 20px;
          line-height: 1.5;
        }
        .welcome-section .membership-status {
          font-size: 14px;
          margin-bottom: 8px;
        }
        .welcome-section .sub-text {
          font-size: 13px;
          opacity: 0.9;
          margin-bottom: 20px;
          line-height: 1.5;
        }
        .welcome-section .cta-btn {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          background: white;
          color: #dc2626;
          padding: 12px 24px;
          border-radius: 8px;
          font-weight: 600;
          font-size: 14px;
          border: none;
          cursor: pointer;
        }
        .welcome-section .progress-note {
          margin-top: 16px;
          font-size: 12px;
          opacity: 0.8;
        }
        .progress-card {
          background: #1a2744;
          border-radius: 12px;
          padding: 16px;
          margin-bottom: 16px;
        }
        .progress-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 12px;
        }
        .progress-title {
          color: #e6f1ff;
          font-weight: 600;
          font-size: 14px;
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .current-role {
          background: linear-gradient(135deg, #ef4444, #dc2626);
          color: white;
          padding: 4px 10px;
          border-radius: 12px;
          font-size: 11px;
          font-weight: 600;
        }
        .progress-stats {
          display: flex;
          gap: 16px;
          margin-bottom: 12px;
        }
        .progress-stat {
          flex: 1;
          text-align: center;
          background: rgba(100, 255, 218, 0.05);
          border-radius: 8px;
          padding: 10px;
        }
        .progress-stat-value {
          color: #64ffda;
          font-size: 16px;
          font-weight: 700;
        }
        .progress-stat-label {
          color: #8892b0;
          font-size: 11px;
          margin-top: 2px;
        }
        .progress-bar-container {
          background: rgba(255,255,255,0.1);
          border-radius: 8px;
          height: 12px;
          overflow: hidden;
          margin-bottom: 8px;
        }
        .progress-bar-fill {
          height: 100%;
          background: linear-gradient(90deg, #ef4444, #f87171);
          border-radius: 8px;
          transition: width 0.5s ease;
        }
        .progress-target-info {
          display: flex;
          justify-content: space-between;
          align-items: center;
          color: #8892b0;
          font-size: 12px;
        }
        .progress-percent {
          color: #64ffda;
          font-weight: 600;
        }
        .next-role-badge {
          color: #f87171;
          font-weight: 600;
        }
        .highest-rank-badge {
          background: linear-gradient(135deg, #10b981, #059669);
          color: white;
          padding: 8px 16px;
          border-radius: 8px;
          font-size: 13px;
          font-weight: 600;
          text-align: center;
          margin-top: 8px;
        }
        .role-display-card {
          background: linear-gradient(135deg, #ef4444, #dc2626);
          color: white;
        }
        .role-display {
          text-align: center;
          padding: 8px 0;
        }
        .role-display .role-label {
          font-size: 12px;
          opacity: 0.9;
          margin-bottom: 4px;
        }
        .role-display .role-name {
          font-size: 24px;
          font-weight: 700;
          margin-bottom: 8px;
        }
        .role-display .next-role-info {
          font-size: 13px;
          opacity: 0.9;
        }
        .progress-target-info strong {
          color: #64ffda;
        }
        .journey-preview {
          background: #1a2744;
          border-radius: 16px;
          padding: 20px;
          margin-top: 16px;
        }
        .journey-header {
          text-align: center;
          margin-bottom: 20px;
        }
        .journey-header span {
          font-size: 28px;
          display: block;
          margin-bottom: 8px;
        }
        .journey-header h4 {
          color: #ef4444;
          font-size: 18px;
          font-weight: 700;
          margin: 0 0 6px 0;
        }
        .journey-header p {
          color: #8892b0;
          font-size: 13px;
          margin: 0;
        }
        .journey-steps {
          display: flex;
          flex-direction: column;
          gap: 12px;
          margin-bottom: 16px;
        }
        .journey-step {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 12px 16px;
          border-radius: 12px;
          background: rgba(255,255,255,0.05);
        }
        .journey-step .step-icon {
          font-size: 24px;
          width: 44px;
          height: 44px;
          display: flex;
          align-items: center;
          justify-content: center;
          border-radius: 50%;
        }
        .step-promoter .step-icon { background: linear-gradient(135deg, #f87171, #ef4444); }
        .step-team-leader .step-icon { background: linear-gradient(135deg, #fb923c, #f97316); }
        .step-zonal-manager .step-icon { background: linear-gradient(135deg, #a855f7, #9333ea); }
        .step-director .step-icon { background: linear-gradient(135deg, #fbbf24, #f59e0b); }
        .journey-step .step-info { flex: 1; }
        .journey-step .step-title {
          color: #e6f1ff;
          font-weight: 600;
          font-size: 14px;
          margin-bottom: 2px;
        }
        .journey-step .step-desc {
          color: #8892b0;
          font-size: 12px;
        }
        .step-arrow {
          text-align: center;
          color: #4a5568;
          font-size: 16px;
          display: none;
        }
        .journey-motivation {
          background: rgba(239, 68, 68, 0.1);
          border: 1px solid rgba(239, 68, 68, 0.3);
          border-radius: 10px;
          padding: 12px 16px;
          display: flex;
          align-items: center;
          gap: 10px;
          color: #f87171;
          font-size: 13px;
          font-weight: 500;
        }
      </style>
      <div class="page-container zynova-insurance-page">
        ${a.render({title:"VGK Care - Insurance",showBack:!0})}
        
        <div id="pageContent" class="page-content">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
    `,a.attachListeners({title:"VGK Care - Insurance",showBack:!0})}updateContent(){const e=document.getElementById("pageContent");if(!e)return;if(this.loading){e.innerHTML='<div class="loading-state">Loading...</div>';return}const t=this.data?.is_member||!1;e.innerHTML=`
      <div class="zynova-header-card">
        <div class="header-title">
          <span>❤️</span>
          <h2>VGK Care</h2>
          <span class="segment-badge">Insurance</span>
        </div>
        <p class="header-subtitle">Your Insurance Zynova Program - Build your team and grow your income</p>
      </div>

      <div class="requirements-card">
        <div class="req-header">
          <span>📹</span>
          <span>Feedback Video and Photos Requirement</span>
        </div>
        <p class="req-text">
          <strong>For Zynova incentive eligibility:</strong> Sharing feedback videos and photos is mandatory for members activated before 1st Dec 2025.
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
          <span class="note-icon">ℹ️</span>
          <span>Please note: Submitted feedback videos and photos may be publicly displayed on our platforms for promotional and community engagement purposes. By sharing your content, you acknowledge and consent to this use.</span>
        </div>
      </div>

      ${t?this.renderMemberContent():this.renderNonMemberContent()}
    `,this.attachEventListeners()}formatCurrency(e){return"₹"+(e||0).toLocaleString("en-IN")}renderMemberContent(){const e=this.data,t=e.promotion_progress||{progress:0,remaining:0},r=e.current_role_display||"Promoter",s=e.next_role_display,i=(e.current_role||"promoter")==="director"||!s||s==="Top Level";return`
      <div class="progress-card role-display-card">
        <div class="role-display">
          <div class="role-label">Your Current Role</div>
          <div class="role-name">${r}</div>
          <div class="next-role-info">${i?"🏆 Highest Level Achieved!":`Next: ${s}`}</div>
        </div>
      </div>

      <div class="progress-card">
        <div class="progress-header">
          <div class="progress-title">
            <span>📊</span>
            <span>Progress to Next Promotion</span>
          </div>
        </div>
        
        <div class="progress-stats">
          <div class="progress-stat">
            <div class="progress-stat-value">${this.formatCurrency(e.self_revenue||0)}</div>
            <div class="progress-stat-label">Self Revenue</div>
          </div>
          <div class="progress-stat">
            <div class="progress-stat-value">${this.formatCurrency(e.team_revenue||0)}</div>
            <div class="progress-stat-label">Team Revenue</div>
          </div>
        </div>

        ${i?`
          <div class="highest-rank-badge">
            🏆 You have reached the highest level!
          </div>
        `:`
          <div class="progress-bar-container">
            <div class="progress-bar-fill" style="width: ${t.progress||0}%"></div>
          </div>
          <div class="progress-target-info">
            <span>Current: <strong>${this.formatCurrency(e.total_revenue||0)}</strong></span>
            <span>Target: <strong>${this.formatCurrency(e.promotion_target||0)}</strong></span>
          </div>
          <div class="progress-target-info" style="margin-top: 6px;">
            <span class="progress-percent">${t.progress||0}% complete</span>
            <span>${t.remaining>0?this.formatCurrency(t.remaining)+" more needed":"Ready for promotion!"}</span>
          </div>
        `}
      </div>

      <div class="progress-card">
        <div class="progress-header">
          <div class="progress-title">
            <span>💰</span>
            <span>Earnings Summary</span>
          </div>
        </div>
        <div class="progress-stats">
          <div class="progress-stat">
            <div class="progress-stat-value">${this.formatCurrency(e.earnings?.pending||0)}</div>
            <div class="progress-stat-label">Pending</div>
          </div>
          <div class="progress-stat">
            <div class="progress-stat-value">${this.formatCurrency(e.earnings?.approved||0)}</div>
            <div class="progress-stat-label">Approved</div>
          </div>
        </div>
        <div class="progress-stats" style="margin-top: 8px;">
          <div class="progress-stat">
            <div class="progress-stat-value">${this.formatCurrency(e.earnings?.disbursed||0)}</div>
            <div class="progress-stat-label">Disbursed</div>
          </div>
          <div class="progress-stat">
            <div class="progress-stat-value">${this.formatCurrency(e.earnings?.total||0)}</div>
            <div class="progress-stat-label">Total</div>
          </div>
        </div>
      </div>

      <div class="welcome-section">
        <div class="welcome-icon">☂️</div>
        <h3>Keep Growing!</h3>
        <p class="sub-text">Add more leads and work with your team to unlock amazing rewards!</p>
        <button class="cta-btn" id="btnMyLeads">
          <span>👤</span>
          <span>My Leads</span>
        </button>
      </div>
    `}renderNonMemberContent(){return`
      <div class="journey-preview">
        <div class="journey-header">
          <span>🚀</span>
          <h4>Your Growth Journey</h4>
          <p>Protect families and grow your success</p>
        </div>
        <div class="journey-steps">
          <div class="journey-step step-promoter">
            <div class="step-icon">❤️</div>
            <div class="step-info">
              <div class="step-title">Promoter</div>
              <div class="step-desc">Start protecting families</div>
            </div>
          </div>
          <div class="step-arrow">→</div>
          <div class="journey-step step-team-leader">
            <div class="step-icon">🤝</div>
            <div class="step-info">
              <div class="step-title">Team Leader</div>
              <div class="step-desc">Guide your caring team</div>
            </div>
          </div>
          <div class="step-arrow">→</div>
          <div class="journey-step step-zonal-manager">
            <div class="step-icon">🛡️</div>
            <div class="step-info">
              <div class="step-title">Zonal Manager</div>
              <div class="step-desc">Expand your protection zone</div>
            </div>
          </div>
          <div class="step-arrow">→</div>
          <div class="journey-step step-director">
            <div class="step-icon">👑</div>
            <div class="step-info">
              <div class="step-title">Director</div>
              <div class="step-desc">Lead with compassion</div>
            </div>
          </div>
        </div>
        <div class="journey-motivation">
          <span>💡</span>
          <span>Be the reason someone sleeps peacefully. Start your journey today!</span>
        </div>
      </div>

      <div class="welcome-section">
        <div class="welcome-icon">☂️</div>
        <h3>Welcome to VGK Care</h3>
        <p class="quote">"Be the reason someone sleeps peacefully knowing their family is protected."</p>
        <p class="membership-status">You are not yet a member of the Insurance Zynova program.</p>
        <p class="sub-text">Add leads and work with your team to unlock amazing rewards!</p>
        <button class="cta-btn" id="btnMyLeads">
          <span>👤</span>
          <span>My Leads</span>
        </button>
        <p class="progress-note">Start adding leads to begin your progress</p>
      </div>
    `}attachEventListeners(){const e=document.getElementById("btnMyLeads");e&&e.addEventListener("click",()=>{o.navigate("mnr-my-leads")})}}class m{container;data=null;loading=!0;constructor(e){this.container=e}async init(){this.render(),await this.loadData()}async loadData(){this.loading=!0,this.updateContent();try{const e=await n.get("/users/zynova/training");e.success&&e.data&&(this.data=e.data)}catch(e){console.error("[ZynovaTraining] Failed to load:",e)}this.loading=!1,this.updateContent()}render(){this.container.innerHTML=`
      <style>
        .zynova-training-page {
          background: #0d1b2a;
          min-height: 100vh;
        }
        .zynova-training-page .page-content {
          padding: 16px;
        }
        .zynova-header-card {
          background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
          border-radius: 12px;
          padding: 16px;
          margin-bottom: 16px;
          color: white;
        }
        .zynova-header-card .header-title {
          display: flex;
          align-items: center;
          gap: 10px;
          margin-bottom: 6px;
        }
        .zynova-header-card .header-title h2 {
          font-size: 18px;
          margin: 0;
          font-weight: 600;
        }
        .zynova-header-card .segment-badge {
          background: rgba(0,0,0,0.2);
          padding: 4px 10px;
          border-radius: 12px;
          font-size: 11px;
          font-weight: 600;
        }
        .zynova-header-card .header-subtitle {
          font-size: 13px;
          opacity: 0.9;
          margin: 0;
        }
        .requirements-card {
          background: #1a2744;
          border-radius: 12px;
          padding: 16px;
          margin-bottom: 16px;
        }
        .requirements-card .req-header {
          display: flex;
          align-items: center;
          gap: 8px;
          color: #f59e0b;
          font-weight: 600;
          font-size: 14px;
          margin-bottom: 12px;
        }
        .requirements-card .req-text {
          color: #8892b0;
          font-size: 13px;
          margin-bottom: 16px;
          line-height: 1.5;
        }
        .requirements-card .activities-header {
          color: #e6f1ff;
          font-weight: 600;
          font-size: 13px;
          margin-bottom: 10px;
        }
        .requirements-card .activities-list {
          list-style: none;
          padding: 0;
          margin: 0 0 16px 0;
        }
        .requirements-card .activities-list li {
          color: #8892b0;
          font-size: 13px;
          padding: 4px 0 4px 20px;
          position: relative;
        }
        .requirements-card .activities-list li::before {
          content: "•";
          position: absolute;
          left: 6px;
          color: #64ffda;
        }
        .requirements-card .note-text {
          display: flex;
          align-items: flex-start;
          gap: 8px;
          color: #8892b0;
          font-size: 12px;
          padding: 12px;
          background: rgba(100, 255, 218, 0.05);
          border-radius: 8px;
          line-height: 1.4;
        }
        .requirements-card .note-text .note-icon {
          color: #64ffda;
          flex-shrink: 0;
        }
        .welcome-section {
          background: linear-gradient(135deg, #10b981 0%, #059669 100%);
          border-radius: 16px;
          padding: 32px 20px;
          text-align: center;
          color: white;
        }
        .welcome-section .welcome-icon {
          font-size: 48px;
          margin-bottom: 16px;
        }
        .welcome-section h3 {
          font-size: 20px;
          font-weight: 700;
          margin: 0 0 12px 0;
        }
        .welcome-section .quote {
          font-style: italic;
          font-size: 13px;
          opacity: 0.9;
          margin-bottom: 20px;
          line-height: 1.5;
        }
        .welcome-section .sub-header {
          font-weight: 600;
          font-size: 15px;
          margin-bottom: 8px;
        }
        .welcome-section .sub-text {
          font-size: 13px;
          opacity: 0.9;
          margin-bottom: 20px;
          line-height: 1.5;
        }
        .welcome-section .cta-btn {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          background: white;
          color: #059669;
          padding: 12px 24px;
          border-radius: 8px;
          font-weight: 600;
          font-size: 14px;
          border: none;
          cursor: pointer;
        }
        .welcome-section .progress-note {
          margin-top: 16px;
          font-size: 12px;
          opacity: 0.8;
        }
      </style>
      <div class="page-container zynova-training-page">
        ${a.render({title:"EVolution Training Center",showBack:!0})}
        
        <div id="pageContent" class="page-content">
          <div class="loading-state">Loading...</div>
        </div>
      </div>
    `,a.attachListeners({title:"EVolution Training Center",showBack:!0})}updateContent(){const e=document.getElementById("pageContent");if(e){if(this.loading){e.innerHTML='<div class="loading-state">Loading...</div>';return}e.innerHTML=`
      <div class="zynova-header-card">
        <div class="header-title">
          <span>🎓</span>
          <h2>EVolution Training Center (ETC)</h2>
          <span class="segment-badge">Training</span>
        </div>
        <p class="header-subtitle">Track your training leads, won deals, and earnings from the ETC program</p>
      </div>

      <div class="requirements-card">
        <div class="req-header">
          <span>📹</span>
          <span>Feedback Video and Photos Requirement</span>
        </div>
        <p class="req-text">
          <strong>For Zynova incentive eligibility:</strong> Sharing feedback videos and photos is mandatory for members activated before 1st Dec 2025.
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
          <span class="note-icon">ℹ️</span>
          <span>Please note: Submitted feedback videos and photos may be publicly displayed on our platforms for promotional and community engagement purposes. By sharing your content, you acknowledge and consent to this use.</span>
        </div>
      </div>

      <div class="welcome-section">
        <div class="welcome-icon">🎓</div>
        <h3>Transform Lives Through Knowledge</h3>
        <p class="quote">"An investment in knowledge pays the best interest." - Benjamin Franklin</p>
        <div class="sub-header">Create Self-Empowerment in Society</div>
        <p class="sub-text">Transform lives through education. Every student you refer is a step towards building a better future. Join the EVolution Training Center and be part of the change!</p>
        <button class="cta-btn" id="btnAddTrainingLead">
          <span>👤</span>
          <span>Add Training Lead</span>
        </button>
        <p class="progress-note">Start your journey by adding your first training lead</p>
      </div>
    `,this.attachEventListeners()}}attachEventListeners(){const e=document.getElementById("btnAddTrainingLead");e&&e.addEventListener("click",()=>{o.navigate("mnr-my-leads")})}}export{v as Z,g as a,m as b};
