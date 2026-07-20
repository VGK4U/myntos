const __vite__mapDeps=(i,m=__vite__mapDeps,d=(m.f||(m.f=["assets/services-AEce4KDH.js","assets/vendor-capacitor-plugins-CPV63GsB.js","assets/vendor-capacitor-core-zwN_Y1fq.js","assets/vendor-CWtoGTp2.js"])))=>i.map(i=>d[i]);
import{r as p,l as y,d as h,b as f}from"./services-AEce4KDH.js";import{L as r}from"./vendor-CWtoGTp2.js";import{_ as k}from"./vendor-capacitor-plugins-CPV63GsB.js";import{gpsService as w}from"./services-gps-BpnPk7uE.js";const E=[{menu_code:"HOME",label:"Home",route:"dashboard"},{menu_code:"PROGRESS_DASHBOARD",label:"Progress Dashboard",route:"progress"},{menu_code:"DAY_PLANNER",label:"Day Planner",route:"day-planner"}],_=[{section_code:"ATTENDANCE",section_label:"ATTENDANCE",order:1,items:[{menu_code:"IN_OUT_TIME",label:"In/Out Time",route:"attendance"},{menu_code:"MY_LEAVES",label:"My Leaves",route:"leaves"},{menu_code:"LEAVE_APPROVALS",label:"Leave Approvals",route:"staff-leave-approvals"},{menu_code:"IN_OUT_RECORDS_ADMIN",label:"In/Out Records - Admin",route:"team-attendance"},{menu_code:"ATTENDANCE_RECORDS",label:"Attendance Records",route:"staff-attendance-sheet"},{menu_code:"ATTENDANCE_DASHBOARD",label:"Attendance Dashboard",route:"staff-attendance-reports"},{menu_code:"EXCEPTION_APPROVALS",label:"Exception Approvals",route:"staff-attendance-exceptions"},{menu_code:"ATTENDANCE_COMPUTATION",label:"Attendance Computation",route:"staff-attendance-computation"}]},{section_code:"TASK_MANAGEMENT",section_label:"TASK MANAGEMENT",order:3,items:[{menu_code:"ASSIGNED_BY_ME",label:"Assigned By Me",route:"tasks-assigned"},{menu_code:"ASSIGNED_TO_ME",label:"Assigned To Me",route:"tasks-received"},{menu_code:"TEAM_ACTIVITIES",label:"Team Activities",route:"staff-team-activities"},{menu_code:"TASK_TRACKER",label:"Task Dashboard",route:"staff-task-tracker"},{menu_code:"TASK_REVIEWS",label:"Task Reviews",route:"staff-task-reviews"}]},{section_code:"KRA_MANAGEMENT",section_label:"KRA MANAGEMENT",order:4,items:[{menu_code:"MY_KRAS",label:"My KRAs",route:"kras"},{menu_code:"KRA_TEMPLATES",label:"KRA Templates",route:"staff-kra-templates"},{menu_code:"KRA_TRACKING_SHEET",label:"KRA Tracking Sheet",route:"staff-kra-tracking"},{menu_code:"KRA_REVIEW",label:"KRA Review",route:"staff-kra-review"}]},{section_code:"TIMESHEET",section_label:"TIMESHEET",order:5,items:[{menu_code:"MY_TIMESHEET",label:"My Timesheet",route:"timesheet"},{menu_code:"TIMESHEET_APPROVAL",label:"Timesheet Approval",route:"staff-timesheet-approval"}]},{section_code:"JOURNEY_TRACKING",section_label:"JOURNEY TRACKING",order:6,items:[{menu_code:"MY_JOURNEYS",label:"My Journeys",route:"journeys"},{menu_code:"TEAM_JOURNEYS",label:"Team Journeys",route:"team-journeys"},{menu_code:"ALL_JOURNEYS",label:"All Journeys",route:"staff-all-journeys"},{menu_code:"VGK4U_JOURNEYS",label:"VGK4U Journeys",route:"staff-vgk4u-journeys"}]},{section_code:"REIMBURSEMENT",section_label:"REIMBURSEMENT",order:7,items:[{menu_code:"MY_REIMBURSEMENT_CLAIMS",label:"My Reimbursement Claims",route:"reimbursements"},{menu_code:"REIMBURSEMENT_APPROVALS",label:"Reimbursement Approvals",route:"staff-reimbursement-approvals"}]},{section_code:"SERVICE_TICKETS",section_label:"SERVICE TICKETS",order:8,items:[{menu_code:"ST_SERVICE_QUEUE",label:"Service Queue",route:"staff-service-queue"},{menu_code:"ST_DASHBOARD",label:"Dashboard",route:"staff-service"},{menu_code:"ST_PERFORMANCE",label:"Performance",route:"staff-service-performance"},{menu_code:"ST_PROCUREMENT",label:"Procurement",route:"staff-service-procurement"},{menu_code:"ST_PROCUREMENT_QUEUE",label:"Procurement Queue",route:"staff-service-procurement-queue"},{menu_code:"ST_RAISE_TICKET",label:"Raise Ticket",route:"staff-tickets"},{menu_code:"ST_REPORTS",label:"Reports",route:"staff-service-reports"},{menu_code:"ST_SERVICE_CENTER_REVENUE",label:"Service Center Revenue",route:"staff-service-revenue"}]},{section_code:"CRM",section_label:"CRM & LEADS",order:9,items:[{menu_code:"CRM_DASHBOARD",label:"CRM Dashboard",route:"staff-crm"},{menu_code:"MY_LEADS",label:"My Leads",route:"staff-leads"},{menu_code:"TEAM_LEADS",label:"Team Leads",route:"staff-team-leads"},{menu_code:"LEAD_SOURCES",label:"Lead Sources",route:"staff-lead-sources"},{menu_code:"CALL_TRACKING_DASHBOARD",label:"Call Tracking",route:"staff-call-tracking"},{menu_code:"AUTO_DIALER",label:"Auto Dialer",route:"auto-dialer"},{menu_code:"OPERATOR_CALLS",label:"Operator Calls",route:"operator-calls"}]},{section_code:"LOCATION_TRACKING",section_label:"LOCATION TRACKING",order:10,items:[{menu_code:"LOCATION_HISTORY",label:"My Location History",route:"location-history"},{menu_code:"TEAM_LIVE_TRACKER",label:"Team Live Tracker",route:"staff-team-live-tracker"},{menu_code:"ALL_LOCATION_TRACKER",label:"All Locations",route:"staff-all-location-tracker"}]},{section_code:"OTHER",section_label:"OTHER",order:11,items:[{menu_code:"ANNOUNCEMENTS",label:"Announcements",route:"announcements"},{menu_code:"TRAINING_VIDEOS",label:"Training Videos",route:"staff-training-videos"},{menu_code:"MY_KYC",label:"My KYC",route:"staff-kyc"},{menu_code:"KYC_APPROVALS",label:"KYC Approvals",route:"staff-kyc-approvals"},{menu_code:"ZYNOVA",label:"VGK4U",route:"staff-zynova"},{menu_code:"SETTINGS",label:"Settings",route:"settings"}]}];class S{container=null;overlay=null;isOpen=!1;expandedSections=new Set;constructor(){this.createElements()}createElements(){this.overlay=document.createElement("div"),this.overlay.className="drawer-overlay",this.overlay.addEventListener("click",()=>this.close()),document.body.appendChild(this.overlay),this.container=document.createElement("div"),this.container.className="side-drawer",this.container.innerHTML=this.render(),document.body.appendChild(this.container),this.attachEventListeners()}render(){return`
      <div class="drawer-header">
        <div class="drawer-logo">
          <span class="logo-text">MNR</span>
        </div>
        <button class="drawer-close" id="drawerClose">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"/>
            <line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>
      <div class="drawer-content">
        <!-- Top menu items (Home, Progress) without section header -->
        <div class="top-menu-items">
          ${E.map(e=>`
            <div class="menu-item top-item" data-route="${e.route}">
              <span class="menu-label">${e.label}</span>
            </div>
          `).join("")}
        </div>
        <!-- Section menus -->
        ${_.map(e=>this.renderSection(e)).join("")}
      </div>
    `}renderSection(e){const t=this.expandedSections.has(e.section_code),n=e.subSections&&e.subSections.length>0,a=e.items&&e.items.length>0;return n?`
        <div class="drawer-section" data-section="${e.section_code}">
          <div class="section-header" data-toggle="${e.section_code}">
            <span class="section-title">${e.section_label}</span>
            <svg class="section-arrow" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">${t?'<polyline points="6 9 12 15 18 9"/>':'<polyline points="9 18 15 12 9 6"/>'}</svg>
          </div>
          <div class="section-items ${t?"expanded":""}">
            ${e.subSections.map(o=>this.renderSubSection(o)).join("")}
          </div>
        </div>
      `:a?`
        <div class="drawer-section" data-section="${e.section_code}">
          <div class="section-header" data-toggle="${e.section_code}">
            <span class="section-title">${e.section_label}</span>
            <svg class="section-arrow" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">${t?'<polyline points="6 9 12 15 18 9"/>':'<polyline points="9 18 15 12 9 6"/>'}</svg>
          </div>
          <div class="section-items ${t?"expanded":""}">
            ${e.items.map(o=>this.renderMenuItem(o)).join("")}
          </div>
        </div>
      `:""}renderSubSection(e){const t=this.expandedSections.has(e.sub_section_code);return`
      <div class="drawer-subsection">
        <div class="subsection-header" data-toggle="${e.sub_section_code}">
          <span class="subsection-title">${e.sub_section_label}</span>
          <svg class="section-arrow" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">${t?'<polyline points="6 9 12 15 18 9"/>':'<polyline points="9 18 15 12 9 6"/>'}</svg>
        </div>
        <div class="subsection-items ${t?"expanded":""}">
          ${e.items.map(n=>this.renderMenuItem(n)).join("")}
        </div>
      </div>
    `}renderMenuItem(e){return`
      <a class="drawer-menu-item" data-route="${e.route}">
        <span class="menu-label">${e.label}</span>
      </a>
    `}attachEventListeners(){this.container&&(document.getElementById("drawerClose")?.addEventListener("click",()=>this.close()),this.container.querySelectorAll("[data-toggle]").forEach(e=>{e.addEventListener("click",t=>{const n=e.dataset.toggle;this.toggleSection(n),t.stopPropagation()})}),this.container.querySelectorAll("[data-route]").forEach(e=>{e.addEventListener("click",()=>{const t=e.dataset.route;p.navigate(t),this.close()})}))}toggleSection(e){this.expandedSections.has(e)?this.expandedSections.delete(e):this.expandedSections.add(e),this.updateUI()}updateUI(){this.container&&(this.container.innerHTML=this.render(),this.attachEventListeners())}open(){this.isOpen||(this.isOpen=!0,this.container?.classList.add("open"),this.overlay?.classList.add("visible"),document.body.style.overflow="hidden")}close(){this.isOpen&&(this.isOpen=!1,this.container?.classList.remove("open"),this.overlay?.classList.remove("visible"),document.body.style.overflow="")}toggle(){this.isOpen?this.close():this.open()}}let b=null;function U(){return b||(b=new S),b}class v{static render(e){const{title:t,showBack:n=!1,showLogout:a=!1,rightAction:o}=e;return`
      <header class="page-header">
        <div class="header-left">
          ${n?`
            <button class="header-btn back-btn" id="backBtn">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="15 18 9 12 15 6"/>
              </svg>
            </button>
          `:""}
          <h1 class="header-title">${t}</h1>
        </div>
        <div class="header-right">
          ${o?`
            <button class="header-btn action-btn" id="headerActionBtn">
              ${o.icon}
            </button>
          `:""}
          ${a?`
            <button class="header-btn logout-btn" id="logoutBtn">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
                <polyline points="16 17 21 12 16 7"/>
                <line x1="21" y1="12" x2="9" y2="12"/>
              </svg>
            </button>
          `:""}
        </div>
      </header>
    `}static getPortalDashboard(){const e=y.getPortal();return e==="mnr"?"mnr-dashboard":e==="partner"?"partner-dashboard":"dashboard"}static attachListeners(e){e.showBack&&document.getElementById("backBtn")?.addEventListener("click",()=>{p.goBack()||p.navigate(v.getPortalDashboard())}),e.rightAction&&document.getElementById("headerActionBtn")?.addEventListener("click",e.rightAction.onClick)}static attachBackHandler(){document.getElementById("backBtn")?.addEventListener("click",()=>{p.goBack()||p.navigate(v.getPortalDashboard())})}}class V{constructor(e){this.options=e,this.trackPoints=e.trackPoints,this.stops=e.stops||[],this.onViewChange=e.onViewChange}options;map=null;container=null;trackPoints=[];stops=[];routeLine=null;progressLine=null;currentMarker=null;startMarker=null;endMarker=null;stopMarkers=[];currentView="street";tileLayers={};playbackIndex=0;isPlaying=!1;playbackInterval=null;playbackSpeed=2;onViewChange;addressCache=new Map;mount(){if(this.container=document.getElementById(this.options.containerId),!this.container){console.error("[LeafletMap] Container not found:",this.options.containerId);return}this.render(),this.initMap()}render(){this.container&&(this.container.innerHTML=`
      <div class="leaflet-journey-map">
        <div class="map-view-controls">
          <button class="view-btn active" data-view="street" title="Street View">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M3 12h18M3 6h18M3 18h18"/>
            </svg>
            <span>Street</span>
          </button>
          <button class="view-btn" data-view="satellite" title="Satellite View">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <path d="M2 12h20M12 2a10 10 0 0110 10"/>
            </svg>
            <span>Satellite</span>
          </button>
          <button class="view-btn" data-view="terrain" title="Terrain View">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M8 20L12 10l4 10M12 10l8-6M12 10L4 4"/>
            </svg>
            <span>Terrain</span>
          </button>
        </div>
        <div id="leafletMapView" class="leaflet-map-view"></div>
        <div class="map-legend-overlay">
          <span class="legend-item"><span class="dot start"></span>Start</span>
          <span class="legend-item"><span class="dot end"></span>End</span>
          <span class="legend-item"><span class="dot stop"></span>Stops</span>
        </div>
      </div>
      
      ${this.options.hidePlaybackControls?"":`
      <div class="playback-section">
        <h5 class="section-label">Route Playback</h5>
        <div class="playback-controls-enhanced">
          <button id="playPauseBtn" class="playback-btn-lg play" title="Play">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
              <polygon points="5 3 19 12 5 21 5 3"/>
            </svg>
          </button>
          <button id="resetPlayback" class="playback-btn-sm" title="Reset">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M3 12a9 9 0 019-9 9 9 0 016.36 2.64L21 3v6h-6l2.64-2.64A7 7 0 0012 5a7 7 0 00-7 7 7 7 0 007 7 7 7 0 005.66-2.88"/>
            </svg>
          </button>
          <div class="slider-container">
            <input type="range" id="playbackSlider" class="playback-slider-enhanced" min="0" max="${this.trackPoints.length-1}" value="0">
            <div class="slider-progress" id="sliderProgress"></div>
          </div>
          <div class="speed-selector">
            <button id="speedBtn" class="speed-btn">2x</button>
          </div>
        </div>
        <div class="playback-info-bar">
          <span id="currentLocation" class="current-loc">--</span>
          <span id="playbackCounter" class="counter">${this.playbackIndex+1} / ${this.trackPoints.length}</span>
        </div>
      </div>
      `}
    `,this.addStyles(),this.attachEventListeners())}initMap(){if(this.trackPoints.length===0||!document.getElementById("leafletMapView"))return;const t=this.trackPoints[0];this.map=r.map("leafletMapView",{zoomControl:!1,attributionControl:!1}).setView([t.latitude,t.longitude],14),r.control.zoom({position:"topright"}).addTo(this.map),this.tileLayers={street:r.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",{maxZoom:19}),satellite:r.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",{maxZoom:19}),terrain:r.tileLayer("https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",{maxZoom:17})},this.tileLayers.street.addTo(this.map),this.drawRoute(),this.fitBounds()}drawRoute(){if(!this.map||this.trackPoints.length<2)return;const e=this.trackPoints.map(i=>[i.latitude,i.longitude]);this.routeLine=r.polyline(e,{color:"rgba(255,255,255,0.3)",weight:4,dashArray:"8, 8"}).addTo(this.map),this.progressLine=r.polyline([],{color:"#00d09c",weight:5,lineCap:"round",lineJoin:"round"}).addTo(this.map);const t=r.divIcon({className:"custom-marker start-marker",html:'<div class="marker-inner">S</div>',iconSize:[28,28],iconAnchor:[14,14]}),n=r.divIcon({className:"custom-marker end-marker",html:'<div class="marker-inner">E</div>',iconSize:[28,28],iconAnchor:[14,14]}),a=this.trackPoints[0],o=a.battery_percentage!==void 0?`<br>🔋 ${a.battery_percentage}%`:"";this.startMarker=r.marker([a.latitude,a.longitude],{icon:t}).bindPopup(`<b>Start Point</b><br>${a.address||"Journey Start"}${o}`).addTo(this.map);const s=this.trackPoints[this.trackPoints.length-1],l=s.battery_percentage!==void 0?`<br>🔋 ${s.battery_percentage}%`:"";this.endMarker=r.marker([s.latitude,s.longitude],{icon:n}).bindPopup(`<b>End Point</b><br>${s.address||"Journey End"}${l}`).addTo(this.map),this.stops.forEach((i,d)=>{const u=this.trackPoints[i.startIndex];if(u){const g=r.divIcon({className:"custom-marker stop-marker",html:`<div class="marker-inner">${d+1}</div>`,iconSize:[24,24],iconAnchor:[12,12]}),m=r.marker([u.latitude,u.longitude],{icon:g}).bindPopup(`<b>Stop ${d+1}</b><br>${i.address||"Unknown location"}<br>Duration: ${this.formatDuration(i.durationMinutes)}`).addTo(this.map);this.stopMarkers.push(m)}}),this.currentMarker=r.circleMarker([a.latitude,a.longitude],{radius:10,color:"#fff",weight:3,fillColor:"#ffc107",fillOpacity:1}).addTo(this.map)}fitBounds(){!this.map||!this.routeLine||this.map.fitBounds(this.routeLine.getBounds(),{padding:[30,30]})}switchView(e){!this.map||this.currentView===e||(this.tileLayers[this.currentView].remove(),this.tileLayers[e].addTo(this.map),this.currentView=e,document.querySelectorAll(".view-btn").forEach(t=>{t.classList.toggle("active",t.getAttribute("data-view")===e)}),this.onViewChange&&this.onViewChange(e))}attachEventListeners(){document.querySelectorAll(".view-btn").forEach(t=>{t.addEventListener("click",()=>{const n=t.getAttribute("data-view");this.switchView(n)})}),document.getElementById("playPauseBtn")?.addEventListener("click",()=>this.togglePlayback()),document.getElementById("resetPlayback")?.addEventListener("click",()=>this.resetPlayback());const e=document.getElementById("playbackSlider");e?.addEventListener("input",()=>{this.playbackIndex=parseInt(e.value),this.updatePlaybackUI()}),document.getElementById("speedBtn")?.addEventListener("click",()=>this.cycleSpeed())}togglePlayback(){const e=document.getElementById("playPauseBtn");this.isPlaying?(this.stopPlayback(),e&&(e.innerHTML='<svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>',e.classList.remove("pause"),e.classList.add("play"))):(this.startPlayback(),e&&(e.innerHTML='<svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg>',e.classList.remove("play"),e.classList.add("pause"))),this.isPlaying=!this.isPlaying}startPlayback(){const e=500/this.playbackSpeed;this.playbackInterval=setInterval(()=>{if(this.playbackIndex<this.trackPoints.length-1)this.playbackIndex++,this.updatePlaybackUI();else{this.stopPlayback(),this.isPlaying=!1;const t=document.getElementById("playPauseBtn");t&&(t.innerHTML='<svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>',t.classList.remove("pause"),t.classList.add("play"))}},e)}stopPlayback(){this.playbackInterval&&(clearInterval(this.playbackInterval),this.playbackInterval=null)}resetPlayback(){this.stopPlayback(),this.playbackIndex=0,this.isPlaying=!1;const e=document.getElementById("playPauseBtn");e&&(e.innerHTML='<svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>',e.classList.remove("pause"),e.classList.add("play")),this.updatePlaybackUI()}cycleSpeed(){const e=[1,2,4,8],t=e.indexOf(this.playbackSpeed);this.playbackSpeed=e[(t+1)%e.length];const n=document.getElementById("speedBtn");n&&(n.textContent=`${this.playbackSpeed}x`),this.isPlaying&&(this.stopPlayback(),this.startPlayback())}updatePlaybackUI(){const e=document.getElementById("playbackSlider"),t=document.getElementById("playbackCounter"),n=document.getElementById("currentLocation"),a=document.getElementById("sliderProgress");e&&(e.value=String(this.playbackIndex)),t&&(t.textContent=`${this.playbackIndex+1} / ${this.trackPoints.length}`);const o=this.trackPoints[this.playbackIndex];n&&o&&(o.address?n.textContent=o.address:(n.textContent="Loading...",this.reverseGeocodeForPlayback(o.latitude,o.longitude,n)));const s=this.playbackIndex/(this.trackPoints.length-1)*100;if(a&&(a.style.width=`${s}%`),this.currentMarker&&o&&this.currentMarker.setLatLng([o.latitude,o.longitude]),this.progressLine){const l=this.trackPoints.slice(0,this.playbackIndex+1).map(i=>[i.latitude,i.longitude]);this.progressLine.setLatLngs(l)}this.map&&o&&this.map.panTo([o.latitude,o.longitude],{animate:!0,duration:.3})}async reverseGeocodeForPlayback(e,t,n){const a=`${e.toFixed(4)},${t.toFixed(4)}`;if(this.addressCache.has(a)){n.textContent=this.addressCache.get(a);return}try{const o=`https://nominatim.openstreetmap.org/reverse?format=json&lat=${e}&lon=${t}&zoom=18`,s=await fetch(o,{headers:{"User-Agent":"MyntReal-Mobile/1.0"}});if(s.ok){const i=(await s.json()).address||{},d=[];for(const g of["road","neighbourhood","suburb","city","town","village"])if(i[g]&&(d.push(i[g]),d.length>=2))break;const u=d.length>0?d.join(", "):`${e.toFixed(4)}, ${t.toFixed(4)}`;this.addressCache.set(a,u),n.textContent==="Loading..."&&(n.textContent=u)}}catch(o){console.warn("[DC_GEOCODE] Playback geocode failed:",o),n.textContent==="Loading..."&&(n.textContent=`${e.toFixed(4)}, ${t.toFixed(4)}`)}}formatDuration(e){if(e<60)return`${Math.round(e)}m`;const t=Math.floor(e/60),n=Math.round(e%60);return n>0?`${t}h ${n}m`:`${t}h`}addStyles(){if(document.getElementById("leaflet-journey-map-styles"))return;const e=document.createElement("style");e.id="leaflet-journey-map-styles",e.textContent=`
      .leaflet-journey-map {
        position: relative;
        border-radius: 12px;
        overflow: hidden;
        background: #1a1a2e;
      }

      .map-view-controls {
        display: flex;
        gap: 4px;
        padding: 8px 12px;
        background: linear-gradient(180deg, rgba(26,26,46,0.95) 0%, rgba(26,26,46,0.8) 100%);
        border-bottom: 1px solid rgba(255,255,255,0.1);
      }

      .view-btn {
        display: flex;
        align-items: center;
        gap: 6px;
        padding: 8px 12px;
        border: none;
        border-radius: 8px;
        background: rgba(255,255,255,0.1);
        color: rgba(255,255,255,0.7);
        font-size: 12px;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s;
      }

      .view-btn:hover {
        background: rgba(255,255,255,0.15);
      }

      .view-btn.active {
        background: linear-gradient(135deg, #00d09c 0%, #00b386 100%);
        color: white;
      }

      .leaflet-map-view {
        height: 280px;
        background: #16213e;
      }

      .map-legend-overlay {
        position: absolute;
        bottom: 10px;
        left: 10px;
        display: flex;
        gap: 12px;
        padding: 6px 10px;
        background: rgba(26,26,46,0.9);
        border-radius: 6px;
        font-size: 11px;
        color: rgba(255,255,255,0.8);
        z-index: 1000;
      }

      .legend-item {
        display: flex;
        align-items: center;
        gap: 4px;
      }

      .legend-item .dot {
        width: 10px;
        height: 10px;
        border-radius: 50%;
      }

      .dot.start { background: #4CAF50; }
      .dot.end { background: #f44336; }
      .dot.stop { background: #ff9800; }

      .custom-marker {
        display: flex;
        align-items: center;
        justify-content: center;
      }

      .custom-marker .marker-inner {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 100%;
        height: 100%;
        border-radius: 50%;
        font-weight: bold;
        font-size: 12px;
        color: white;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
      }

      .start-marker .marker-inner {
        background: #4CAF50;
      }

      .end-marker .marker-inner {
        background: #f44336;
      }

      .stop-marker .marker-inner {
        background: #ff9800;
        font-size: 10px;
      }

      .playback-section {
        padding: 16px;
        background: rgba(22, 33, 62, 0.5);
        border-top: 1px solid rgba(255,255,255,0.1);
      }

      .section-label {
        font-size: 13px;
        font-weight: 600;
        color: rgba(255,255,255,0.9);
        margin-bottom: 12px;
      }

      .playback-controls-enhanced {
        display: flex;
        align-items: center;
        gap: 12px;
      }

      .playback-btn-lg {
        width: 48px;
        height: 48px;
        border-radius: 50%;
        border: none;
        background: linear-gradient(135deg, #00d09c 0%, #00b386 100%);
        color: white;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        box-shadow: 0 4px 12px rgba(0, 208, 156, 0.3);
        transition: all 0.2s;
      }

      .playback-btn-lg:hover {
        transform: scale(1.05);
      }

      .playback-btn-lg.pause {
        background: linear-gradient(135deg, #ff9800 0%, #f57c00 100%);
        box-shadow: 0 4px 12px rgba(255, 152, 0, 0.3);
      }

      .playback-btn-sm {
        width: 36px;
        height: 36px;
        border-radius: 8px;
        border: none;
        background: rgba(255,255,255,0.1);
        color: rgba(255,255,255,0.8);
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        transition: background 0.2s;
      }

      .playback-btn-sm:hover {
        background: rgba(255,255,255,0.2);
      }

      .slider-container {
        flex: 1;
        position: relative;
        height: 6px;
        background: rgba(255,255,255,0.15);
        border-radius: 3px;
        overflow: hidden;
      }

      .playback-slider-enhanced {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        opacity: 0;
        cursor: pointer;
        z-index: 2;
      }

      .slider-progress {
        position: absolute;
        top: 0;
        left: 0;
        height: 100%;
        background: linear-gradient(90deg, #00d09c 0%, #00b386 100%);
        border-radius: 3px;
        transition: width 0.1s;
      }

      .speed-selector {
        display: flex;
        align-items: center;
      }

      .speed-btn {
        padding: 6px 12px;
        border-radius: 16px;
        border: 1px solid rgba(255,255,255,0.2);
        background: transparent;
        color: rgba(255,255,255,0.9);
        font-size: 12px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s;
      }

      .speed-btn:hover {
        background: rgba(255,255,255,0.1);
        border-color: rgba(255,255,255,0.3);
      }

      .playback-info-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 12px;
        padding-top: 12px;
        border-top: 1px solid rgba(255,255,255,0.1);
      }

      .current-loc {
        font-size: 12px;
        color: rgba(255,255,255,0.7);
        max-width: 70%;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }

      .counter {
        font-size: 12px;
        color: rgba(255,255,255,0.5);
        font-weight: 500;
      }
    `,document.head.appendChild(e)}setPlaybackIndex(e){e<0||e>=this.trackPoints.length||(this.playbackIndex=e,this.updatePlaybackUI())}getPlaybackState(){return{index:this.playbackIndex,total:this.trackPoints.length,isPlaying:this.isPlaying}}destroy(){this.stopPlayback(),this.map&&(this.map.remove(),this.map=null)}}const A=[{menu_code:"HOME_DASHBOARD",label:"Home Dashboard",route:"mnr-dashboard",icon:"home"},{menu_code:"VIEW_PROFILE",label:"View Profile",route:"mnr-profile",icon:"user"},{menu_code:"ADD_MEMBER",label:"Add Member",route:"mnr-add-member",icon:"user-plus"}],M=[{section_code:"ANNOUNCEMENTS",section_label:"📢 Community Updates",icon:"bullhorn",order:1,items:[{menu_code:"PUBLIC_ANNOUNCEMENTS",label:"📢 Official Updates",route:"mnr-announcements"},{menu_code:"MY_SUBMISSIONS",label:"📋 My Submissions",route:"mnr-my-announcements"},{menu_code:"PENDING",label:"⏳ Pending",route:"mnr-announcements-pending"},{menu_code:"APPROVED",label:"✅ Approved",route:"mnr-announcements-approved"},{menu_code:"REJECTED",label:"❌ Rejected",route:"mnr-announcements-rejected"}]},{section_code:"COUPON_MODULES",section_label:"🎫 Coupon Modules",icon:"ticket",order:2,items:[{menu_code:"BUY_COUPON",label:"🛒 Buy Coupon",route:"mnr-coupon-buy"},{menu_code:"ACTIVATE_COUPON",label:"✅ Activate Coupon",route:"mnr-coupon-activate"},{menu_code:"COUPON_STATUS",label:"🎫 Coupon Status",route:"mnr-coupon-status"},{menu_code:"COUPON_PROGRESS",label:"📊 Coupon Progress",route:"mnr-coupon-progress"},{menu_code:"COUPON_TRANSFER",label:"🔄 Coupon Transfer",route:"mnr-coupon-transfer"}]},{section_code:"MEMBERS",section_label:"👥 My Connections",icon:"users",order:3,items:[{menu_code:"ALL_MEMBERS",label:"👥 All Connections",route:"mnr-members-all"},{menu_code:"DIRECT_REFERRALS",label:"🔗 Direct Connections",route:"mnr-referrals"},{menu_code:"PICTURE_VIEW",label:"🌳 Connections Gallery",route:"mnr-members-picture"},{menu_code:"VED_TEAM",label:"👑 Leadership Group (VED)",route:"mnr-members-ved"}]},{section_code:"MNR",section_label:"💰 Facilitation & Recognition",icon:"coins",order:4,items:[{menu_code:"EARNINGS_SUMMARY",label:"📊 Earnings Overview",route:"mnr-earnings-summary"},{menu_code:"DIRECT_REFERRAL",label:"💰 Direct Business Facilitation",route:"mnr-income-direct"},{menu_code:"MATCHING_REFERRAL",label:"🤝 Group Performance Recognition",route:"mnr-income-matching"},{menu_code:"VED_INCOME",label:"👑 VED Leadership Recognition",route:"mnr-income-ved"},{menu_code:"GURUDAKSHINA",label:"🙏 Mentorship Contribution Benefit",route:"mnr-income-guru"},{menu_code:"FIELD_ALLOWANCE",label:"🚗 Field Allowances",route:"mnr-income-field"},{menu_code:"WITHDRAWALS",label:"💸 Withdrawals",route:"mnr-withdrawals"},{menu_code:"COUPON_BENEFITS",label:"🎁 Coupon Benefits",route:"mnr-benefits"},{menu_code:"MNR_POINTS",label:"🎯 Points Utilisation",route:"mnr-points"}]},{section_code:"MYNTREAL",section_label:"💎 MyntReal",icon:"gem",order:5,items:[{menu_code:"MY_LEADS",label:"📋 My Leads",route:"mnr-my-leads"},{menu_code:"FRANCHISE_EARNINGS",label:"🏪 Franchise Earnings",route:"mnr-franchise-earnings"}]},{section_code:"ZYNOVA",section_label:"⭐ Zynova",icon:"crown",order:6,items:[{menu_code:"VGK_REAL_DREAMS",label:"🏠 VGK Real Dreams (Real Estate)",route:"zynova-real-estate"},{menu_code:"VGK_CARE",label:"🛡️ VGK Care (Insurance)",route:"zynova-insurance"},{menu_code:"ETC",label:"🎓 EVolution Training Center (ETC)",route:"zynova-training"}]},{section_code:"AWARDS_BONANZA",section_label:"🏆 Awards & Bonanza",icon:"trophy",order:7,items:[{menu_code:"AWARDS",label:"🏆 Awards",route:"mnr-awards"},{menu_code:"BONANZA_AWARDS",label:"🎉 Bonanza Awards",route:"mnr-bonanza"}]}],I=[{menu_code:"THEME_MODE",label:"Theme Mode",route:"mnr-settings",icon:"headset"},{menu_code:"SECURITY_SETTINGS",label:"Security Settings",route:"mnr-change-password",icon:"headset"}];class L{container=null;overlay=null;isOpen=!1;expandedSections=new Set;user=null;constructor(){this.createElements()}createElements(){this.overlay=document.createElement("div"),this.overlay.className="mnr-drawer-overlay",this.overlay.addEventListener("click",()=>this.close()),document.body.appendChild(this.overlay),this.container=document.createElement("div"),this.container.className="mnr-side-drawer",this.container.innerHTML=this.render(),document.body.appendChild(this.container),this.attachEventListeners()}setUser(e){this.user=e,this.updateUI()}getIcon(e){return`<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${{home:'<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>',user:'<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',"user-plus":'<path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="8.5" cy="7" r="4"/><line x1="20" y1="8" x2="20" y2="14"/><line x1="23" y1="11" x2="17" y2="11"/>',bullhorn:'<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/>',ticket:'<path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/>',users:'<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',coins:'<circle cx="8" cy="8" r="6"/><path d="M18.09 10.37A6 6 0 1 1 10.34 18"/><path d="M7 6h1v4"/><path d="m16.71 13.88.7.71-2.82 2.82"/>',gem:'<polygon points="12 2 2 12 12 22 22 12 12 2"/><polyline points="12 2 12 22"/>',crown:'<path d="m2 4 3 12h14l3-12-6 7-4-7-4 7-6-7zm3 16h14"/>',trophy:'<path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/><path d="M4 22h16"/><path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"/><path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"/><path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"/>',headset:'<path d="M3 18v-6a9 9 0 0 1 18 0v6"/><path d="M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3zM3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3z"/>',logout:'<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>'}[e]||""}</svg>`}render(){const e=this.user?.name||"MNR Member",t=this.user?.mnr_id||"";return`
      <div class="mnr-drawer-header">
        <div class="mnr-drawer-user">
          <div class="mnr-user-avatar">${e.split(" ").map(a=>a[0]).join("").toUpperCase().slice(0,2)}</div>
          <div class="mnr-user-info">
            <span class="mnr-user-name">${e}</span>
            <span class="mnr-user-id">${t}</span>
          </div>
        </div>
        <button class="mnr-drawer-close" id="mnrDrawerClose">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>
      <div class="mnr-drawer-content">
        <!-- Top menu items -->
        <div class="mnr-top-menu">
          ${A.map(a=>`
            <div class="mnr-menu-item top-item" data-route="${a.route}">
              ${this.getIcon(a.icon||"home")}
              <span>${a.label}</span>
            </div>
          `).join("")}
        </div>

        <!-- Section menus -->
        ${M.map(a=>this.renderSection(a)).join("")}

        <!-- Bottom items -->
        <div class="mnr-bottom-menu">
          ${I.map(a=>`
            <div class="mnr-menu-item bottom-item" data-route="${a.route}">
              ${this.getIcon(a.icon||"help-circle")}
              <span>${a.label}</span>
            </div>
          `).join("")}
          <div class="mnr-menu-item logout-item" id="mnrLogoutBtn">
            ${this.getIcon("logout")}
            <span class="logout-text">Logout</span>
          </div>
        </div>
      </div>
    `}renderSection(e){const t=this.expandedSections.has(e.section_code);return`
      <div class="mnr-drawer-section" data-section="${e.section_code}">
        <div class="mnr-section-header" data-toggle="${e.section_code}">
          ${this.getIcon(e.icon)}
          <span class="mnr-section-title">${e.section_label}</span>
          <svg class="mnr-section-arrow ${t?"expanded":""}" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="6 9 12 15 18 9"/>
          </svg>
        </div>
        <div class="mnr-section-items ${t?"expanded":""}">
          ${e.items.map(n=>`
            <a class="mnr-drawer-menu-item" data-route="${n.route}">
              <span class="mnr-menu-label">${n.label}</span>
            </a>
          `).join("")}
        </div>
      </div>
    `}attachEventListeners(){this.container&&(document.getElementById("mnrDrawerClose")?.addEventListener("click",()=>this.close()),this.container.querySelectorAll("[data-toggle]").forEach(e=>{e.addEventListener("click",t=>{const n=e.dataset.toggle;this.toggleSection(n),t.stopPropagation()})}),this.container.querySelectorAll("[data-route]").forEach(e=>{e.addEventListener("click",()=>{const t=e.dataset.route;p.navigate(t),this.close()})}),document.getElementById("mnrLogoutBtn")?.addEventListener("click",async()=>{confirm("Are you sure you want to logout?")&&(await h.logout(),window.dispatchEvent(new CustomEvent("logout")),this.close())}))}toggleSection(e){this.expandedSections.has(e)?this.expandedSections.delete(e):this.expandedSections.add(e),this.updateUI()}updateUI(){this.container&&(this.container.innerHTML=this.render(),this.attachEventListeners())}open(){this.isOpen||(this.isOpen=!0,this.container?.classList.add("open"),this.overlay?.classList.add("visible"),document.body.style.overflow="hidden")}close(){this.isOpen&&(this.isOpen=!1,this.container?.classList.remove("open"),this.overlay?.classList.remove("visible"),document.body.style.overflow="")}toggle(){this.isOpen?this.close():this.open()}destroy(){this.container?.remove(),this.overlay?.remove()}}const H=new L;class z{config;constructor(e){this.config=e}render(){if(this.config.loading)return`
        <div class="table-loading">
          <div class="spinner"></div>
          <p>Loading...</p>
        </div>
      `;if(!this.config.data||this.config.data.length===0)return`
        <div class="table-empty">
          <p>${this.config.emptyMessage||"No data found"}</p>
        </div>
      `;const e=a=>this.config.sortColumn===a?this.config.sortDirection==="asc"?" ↑":" ↓":"",t=this.config.columns.map(a=>{const o=a.sortable!==!1,s=e(a.key),l=a.width?`width: ${a.width};`:"",i=o?`data-sort-column="${a.key}"`:"";return`<th style="${l}${o?"cursor: pointer;":""}" ${i}>${a.label}${s}</th>`}).join(""),n=this.config.data.map(a=>`<tr>${this.config.columns.map(s=>{const l=a[s.key];return`<td>${s.render?s.render(l,a):l??"-"}</td>`}).join("")}</tr>`).join("");return`
      <div class="table-responsive-wrapper">
        <table class="mobile-data-table">
          <thead>
            <tr>${t}</tr>
          </thead>
          <tbody>
            ${n}
          </tbody>
        </table>
      </div>
    `}static getStyles(){return`
      .table-responsive-wrapper {
        width: 100%;
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
        margin-bottom: 16px;
        background: #0d1b2a;
        border-radius: 8px;
        border: 1px solid rgba(255,255,255,0.1);
      }

      .mobile-data-table {
        width: 100%;
        min-width: 0;
        border-collapse: collapse;
        font-size: 11px;
        table-layout: auto;
      }

      .mobile-data-table thead {
        background: linear-gradient(135deg, #1b263b 0%, #0d1b2a 100%);
        position: sticky;
        top: 0;
        z-index: 10;
      }

      .mobile-data-table th {
        padding: 6px 4px;
        text-align: left;
        font-weight: 600;
        color: #8892b0;
        text-transform: uppercase;
        font-size: 9px;
        letter-spacing: 0.3px;
        border-bottom: 2px solid rgba(255,255,255,0.1);
        white-space: nowrap;
      }

      .mobile-data-table th[data-sort-column]:hover {
        color: #64d2ff;
        background: rgba(100, 210, 255, 0.1);
      }

      .mobile-data-table tbody tr {
        border-bottom: 1px solid rgba(255,255,255,0.05);
        transition: background 0.2s;
      }

      .mobile-data-table tbody tr:hover {
        background: rgba(255,255,255,0.03);
      }

      .mobile-data-table td {
        padding: 5px 4px;
        color: #e6f1ff;
        vertical-align: middle;
        white-space: nowrap;
        font-size: 11px;
      }

      .mobile-data-table .badge {
        display: inline-block;
        padding: 2px 5px;
        border-radius: 4px;
        font-size: 9px;
        font-weight: 500;
      }

      .mobile-data-table .badge-success {
        background: rgba(16, 185, 129, 0.2);
        color: #10b981;
      }

      .mobile-data-table .badge-warning {
        background: rgba(245, 158, 11, 0.2);
        color: #f59e0b;
      }

      .mobile-data-table .badge-danger {
        background: rgba(239, 68, 68, 0.2);
        color: #ef4444;
      }

      .mobile-data-table .badge-info {
        background: rgba(59, 130, 246, 0.2);
        color: #3b82f6;
      }

      .mobile-data-table .badge-secondary {
        background: rgba(107, 114, 128, 0.2);
        color: #9ca3af;
      }

      .mobile-data-table .badge-primary {
        background: rgba(99, 102, 241, 0.2);
        color: #818cf8;
      }

      .mobile-data-table .badge-platinum {
        background: rgba(217, 119, 6, 0.2);
        color: #fbbf24;
      }

      .mobile-data-table .badge-diamond {
        background: rgba(6, 182, 212, 0.2);
        color: #22d3ee;
      }

      .table-loading, .table-empty {
        padding: 40px 20px;
        text-align: center;
        color: #8892b0;
      }

      .table-loading .spinner {
        width: 32px;
        height: 32px;
        border: 3px solid rgba(100, 210, 255, 0.2);
        border-top-color: #64d2ff;
        border-radius: 50%;
        animation: spin 1s linear infinite;
        margin: 0 auto 12px;
      }

      @keyframes spin {
        to { transform: rotate(360deg); }
      }

      .table-summary-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 12px;
        background: rgba(22, 33, 62, 0.6);
        border-radius: 6px;
        margin-bottom: 8px;
        font-size: 11px;
        color: #8892b0;
      }

      .table-summary-bar .count {
        color: #64d2ff;
        font-weight: 600;
      }

      .table-pagination {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 8px;
        padding: 10px;
      }

      .table-pagination button {
        padding: 6px 12px;
        background: rgba(100, 210, 255, 0.1);
        border: 1px solid rgba(100, 210, 255, 0.3);
        border-radius: 6px;
        color: #64d2ff;
        font-size: 11px;
        cursor: pointer;
      }

      .table-pagination button:disabled {
        opacity: 0.4;
        cursor: not-allowed;
      }

      .table-pagination .page-info {
        color: #8892b0;
        font-size: 11px;
      }
    `}static attachSortListeners(e,t){e.querySelectorAll("[data-sort-column]").forEach(n=>{n.addEventListener("click",()=>{const a=n.getAttribute("data-sort-column");a&&t(a)})})}}const C=[{menu_code:"SERVICE_REQUEST",label:"Service Request",route:"partner-service",icon:"headset",highlight:!0},{menu_code:"HOME_DASHBOARD",label:"Home Dashboard",route:"partner-dashboard",icon:"home"},{menu_code:"VIEW_PROFILE",label:"View Profile",route:"partner-profile",icon:"user"}],R=[{section_code:"ORDERS",section_label:"Orders",icon:"package",order:1,items:[{menu_code:"ALL_ORDERS",label:"All Orders",route:"partner-orders"},{menu_code:"NEW_ORDER",label:"Create New Order",route:"partner-new-order"}]},{section_code:"SERVICE",section_label:"Service Center",icon:"tool",order:2,items:[{menu_code:"RAISE_TICKET",label:"Raise New Ticket",route:"partner-raise-ticket"},{menu_code:"MY_TICKETS",label:"My Tickets",route:"partner-service"},{menu_code:"TICKET_HISTORY",label:"Ticket History",route:"partner-ticket-history"}]},{section_code:"FINANCE",section_label:"Finance",icon:"coins",order:3,items:[{menu_code:"INVOICES",label:"Invoices",route:"partner-invoices"},{menu_code:"PAYMENTS",label:"Payments",route:"partner-payments"},{menu_code:"REVENUE",label:"Revenue Dashboard",route:"partner-revenue"}]},{section_code:"LEADS",section_label:"Leads & CRM",icon:"users",order:4,items:[{menu_code:"MY_LEADS",label:"My Leads",route:"partner-leads"}]}];class T{container=null;overlay=null;isOpen=!1;expandedSections=new Set;user=null;constructor(){this.createElements()}createElements(){this.overlay=document.createElement("div"),this.overlay.className="partner-drawer-overlay",this.overlay.addEventListener("click",()=>this.close()),document.body.appendChild(this.overlay),this.container=document.createElement("div"),this.container.className="partner-side-drawer",this.container.innerHTML=this.render(),document.body.appendChild(this.container),this.injectStyles(),this.attachEventListeners()}injectStyles(){if(document.getElementById("partner-drawer-styles"))return;const e=document.createElement("style");e.id="partner-drawer-styles",e.textContent=`
      .partner-drawer-overlay {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.6);
        z-index: 9998;
        opacity: 0;
        visibility: hidden;
        transition: all 0.3s ease;
      }
      .partner-drawer-overlay.visible {
        opacity: 1;
        visibility: visible;
      }
      .partner-side-drawer {
        position: fixed;
        top: 0;
        left: -300px;
        width: 280px;
        height: 100%;
        background: linear-gradient(180deg, #0a1929 0%, #0d2137 100%);
        z-index: 9999;
        transition: left 0.3s ease;
        display: flex;
        flex-direction: column;
        overflow: hidden;
      }
      .partner-side-drawer.open {
        left: 0;
      }
      .partner-drawer-header {
        background: linear-gradient(135deg, #1e88e5 0%, #1565c0 100%);
        padding: 20px 16px;
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
      }
      .partner-drawer-user {
        display: flex;
        align-items: center;
        gap: 12px;
      }
      .partner-user-avatar {
        width: 48px;
        height: 48px;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.2);
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 600;
        font-size: 18px;
        color: white;
        border: 2px solid rgba(255, 255, 255, 0.3);
      }
      .partner-user-info {
        display: flex;
        flex-direction: column;
      }
      .partner-user-name {
        font-size: 16px;
        font-weight: 600;
        color: white;
      }
      .partner-user-code {
        font-size: 12px;
        color: #ffffff;
        background: rgba(255, 255, 255, 0.28);
        border: 1px solid rgba(255, 255, 255, 0.35);
        padding: 2px 8px;
        border-radius: 4px;
        margin-top: 4px;
        font-weight: 600;
        letter-spacing: 0.5px;
      }
      .partner-user-type {
        font-size: 11px;
        color: rgba(255, 255, 255, 0.7);
        margin-top: 2px;
      }
      .partner-drawer-close {
        background: none;
        border: none;
        color: white;
        padding: 4px;
        cursor: pointer;
      }
      .partner-drawer-content {
        flex: 1;
        overflow-y: auto;
        padding: 12px 0;
        padding-bottom: calc(80px + env(safe-area-inset-bottom, 0px));
      }
      .partner-top-menu {
        padding: 0 12px 12px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        margin-bottom: 12px;
      }
      .partner-menu-item {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px 14px;
        border-radius: 8px;
        color: #e0e0e0;
        cursor: pointer;
        transition: all 0.2s;
        margin-bottom: 4px;
      }
      .partner-menu-item:hover, .partner-menu-item:active {
        background: rgba(30, 136, 229, 0.2);
      }
      .partner-menu-item.highlight {
        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
        color: white;
        font-weight: 600;
      }
      .partner-menu-item svg {
        flex-shrink: 0;
      }
      .partner-drawer-section {
        margin-bottom: 8px;
      }
      .partner-section-header {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px 16px;
        color: #a0aec0;
        cursor: pointer;
        transition: all 0.2s;
      }
      .partner-section-header:hover {
        background: rgba(255, 255, 255, 0.05);
      }
      .partner-section-title {
        flex: 1;
        font-size: 13px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
      }
      .partner-section-arrow {
        transition: transform 0.2s;
      }
      .partner-section-arrow.expanded {
        transform: rotate(180deg);
      }
      .partner-section-items {
        max-height: 0;
        overflow: hidden;
        transition: max-height 0.3s ease;
      }
      .partner-section-items.expanded {
        max-height: 500px;
      }
      .partner-drawer-menu-item {
        display: block;
        padding: 10px 16px 10px 48px;
        color: #b0bec5;
        font-size: 13px;
        text-decoration: none;
        cursor: pointer;
        transition: all 0.2s;
      }
      .partner-drawer-menu-item:hover, .partner-drawer-menu-item:active {
        background: rgba(30, 136, 229, 0.15);
        color: #64b5f6;
      }
      .partner-bottom-menu {
        padding: 12px;
        padding-bottom: calc(80px + env(safe-area-inset-bottom, 0px));
        border-top: 1px solid rgba(255, 255, 255, 0.1);
        margin-top: auto;
      }
      .partner-logout-item {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px 14px;
        border-radius: 8px;
        color: #ef5350;
        cursor: pointer;
        transition: all 0.2s;
      }
      .partner-logout-item:hover {
        background: rgba(239, 83, 80, 0.15);
      }
    `,document.head.appendChild(e)}setUser(e){this.user=e,this.updateUI()}getIcon(e){return`<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${{home:'<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>',user:'<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',package:'<line x1="16.5" y1="9.4" x2="7.5" y2="4.21"/><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/>',tool:'<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>',coins:'<circle cx="8" cy="8" r="6"/><path d="M18.09 10.37A6 6 0 1 1 10.34 18"/><path d="M7 6h1v4"/><path d="m16.71 13.88.7.71-2.82 2.82"/>',users:'<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',headset:'<path d="M3 18v-6a9 9 0 0 1 18 0v6"/><path d="M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3zM3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3z"/>',logout:'<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>'}[e]||""}</svg>`}render(){const e=this.user?.name||this.user?.partner_name||"Partner",t=this.user?.partner_id||this.user?.partner_code||"PARTNER",n=this.user?.partner_type||this.user?.type||"Partner";return`
      <div class="partner-drawer-header">
        <div class="partner-drawer-user">
          <div class="partner-user-avatar">${e.split(" ").map(o=>o[0]).join("").toUpperCase().slice(0,2)}</div>
          <div class="partner-user-info">
            <span class="partner-user-name">${e}</span>
            <span class="partner-user-code">${t}</span>
            <span class="partner-user-type">${n}</span>
          </div>
        </div>
        <button class="partner-drawer-close" id="partnerDrawerClose">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>
      <div class="partner-drawer-content">
        <div class="partner-top-menu">
          ${C.map(o=>`
            <div class="partner-menu-item ${o.highlight?"highlight":""}" data-route="${o.route}">
              ${this.getIcon(o.icon||"home")}
              <span>${o.label}</span>
            </div>
          `).join("")}
        </div>

        ${R.map(o=>this.renderSection(o)).join("")}

        <div class="partner-bottom-menu">
          <div class="partner-logout-item" id="partnerLogoutBtn">
            ${this.getIcon("logout")}
            <span>Logout</span>
          </div>
        </div>
      </div>
    `}renderSection(e){const t=this.expandedSections.has(e.section_code);return`
      <div class="partner-drawer-section" data-section="${e.section_code}">
        <div class="partner-section-header" data-toggle="${e.section_code}">
          ${this.getIcon(e.icon)}
          <span class="partner-section-title">${e.section_label}</span>
          <svg class="partner-section-arrow ${t?"expanded":""}" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="6 9 12 15 18 9"/>
          </svg>
        </div>
        <div class="partner-section-items ${t?"expanded":""}">
          ${e.items.map(n=>`
            <a class="partner-drawer-menu-item" data-route="${n.route}">
              ${n.label}
            </a>
          `).join("")}
        </div>
      </div>
    `}attachEventListeners(){this.container&&(document.getElementById("partnerDrawerClose")?.addEventListener("click",()=>this.close()),this.container.querySelectorAll("[data-toggle]").forEach(e=>{e.addEventListener("click",t=>{const n=e.dataset.toggle;this.toggleSection(n),t.stopPropagation()})}),this.container.querySelectorAll("[data-route]").forEach(e=>{e.addEventListener("click",()=>{const t=e.dataset.route;p.navigate(t),this.close()})}),document.getElementById("partnerLogoutBtn")?.addEventListener("click",async()=>{confirm("Are you sure you want to logout?")&&(await h.logout(),window.dispatchEvent(new CustomEvent("logout")),this.close())}))}toggleSection(e){this.expandedSections.has(e)?this.expandedSections.delete(e):this.expandedSections.add(e),this.updateUI()}updateUI(){this.container&&(this.container.innerHTML=this.render(),this.attachEventListeners())}open(){this.isOpen||(this.isOpen=!0,this.container?.classList.add("open"),this.overlay?.classList.add("visible"),document.body.style.overflow="hidden")}close(){this.isOpen&&(this.isOpen=!1,this.container?.classList.remove("open"),this.overlay?.classList.remove("visible"),document.body.style.overflow="")}toggle(){this.isOpen?this.close():this.open()}destroy(){this.container?.remove(),this.overlay?.remove()}}const j=new T;class G{container;constructor(e){this.container=e}render(){const t=h.getAuthState().user?.portal||"staff",n=p.getTabRoutes(t),a=p.getCurrentRoute();this.container.innerHTML=`
      <nav class="bottom-tabs">
        ${n.map(o=>`
          <button 
            class="tab-item ${a===o.id?"active":""}" 
            data-route="${o.id}"
          >
            ${this.getIcon(o.icon)}
            <span class="tab-label">${o.title}</span>
          </button>
        `).join("")}
      </nav>
    `,this.attachListeners()}attachListeners(){this.container.querySelectorAll(".tab-item").forEach(e=>{e.addEventListener("click",()=>{const t=e.getAttribute("data-route");t&&p.navigate(t)})})}getIcon(e){const t={home:`<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
        <polyline points="9 22 9 12 15 12 15 22"/>
      </svg>`,clock:`<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/>
        <polyline points="12 6 12 12 16 14"/>
      </svg>`,map:`<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"/>
        <line x1="8" y1="2" x2="8" y2="18"/>
        <line x1="16" y1="6" x2="16" y2="22"/>
      </svg>`,bell:`<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
        <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
      </svg>`,user:`<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
        <circle cx="12" cy="7" r="4"/>
      </svg>`,"dollar-sign":`<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <line x1="12" y1="1" x2="12" y2="23"/>
        <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
      </svg>`,"credit-card":`<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <rect x="1" y="4" width="22" height="16" rx="2" ry="2"/>
        <line x1="1" y1="10" x2="23" y2="10"/>
      </svg>`,gift:`<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <polyline points="20 12 20 22 4 22 4 12"/>
        <rect x="2" y="7" width="20" height="5"/>
        <line x1="12" y1="22" x2="12" y2="7"/>
        <path d="M12 7H7.5a2.5 2.5 0 0 1 0-5C11 2 12 7 12 7z"/>
        <path d="M12 7h4.5a2.5 2.5 0 0 0 0-5C13 2 12 7 12 7z"/>
      </svg>`,package:`<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <line x1="16.5" y1="9.4" x2="7.5" y2="4.21"/>
        <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
        <polyline points="3.27 6.96 12 12.01 20.73 6.96"/>
        <line x1="12" y1="22.08" x2="12" y2="12"/>
      </svg>`,"file-text":`<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
        <polyline points="14 2 14 8 20 8"/>
        <line x1="16" y1="13" x2="8" y2="13"/>
        <line x1="16" y1="17" x2="8" y2="17"/>
        <polyline points="10 9 9 9 8 9"/>
      </svg>`,"bar-chart":`<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <line x1="12" y1="20" x2="12" y2="10"/>
        <line x1="18" y1="20" x2="18" y2="4"/>
        <line x1="6" y1="20" x2="6" y2="16"/>
      </svg>`};return t[e]||t.home}}class P{isShowing=!1;unsubscribe=null;checkInterval=null;init(){this.unsubscribe&&this.unsubscribe(),this.checkInterval&&clearInterval(this.checkInterval),this.unsubscribe=f.onSessionExpired(e=>{console.log("[SessionBanner] Session expired detected, endpoint:",e),this.show()}),this.checkInterval=setInterval(()=>{const e=w.getTrackingStatus();e.isSessionExpired&&!this.isShowing?this.show():!e.isSessionExpired&&this.isShowing&&this.hide()},2e3)}cleanup(){this.unsubscribe&&(this.unsubscribe(),this.unsubscribe=null),this.checkInterval&&(clearInterval(this.checkInterval),this.checkInterval=null),this.hide()}show(){if(this.isShowing||document.getElementById("globalSessionBanner"))return;this.isShowing=!0;const e=document.createElement("div");e.id="globalSessionBanner",e.className="global-session-banner",e.innerHTML=`
      <div class="session-banner-content">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="8" x2="12" y2="12"/>
          <line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>
        <div class="session-banner-text">
          <strong>Session Expired</strong>
          <span>Data saved locally. Tap to login.</span>
        </div>
      </div>
      <button id="globalReAuthBtn" class="re-auth-btn">Login</button>
    `,document.body.appendChild(e),document.getElementById("globalReAuthBtn")?.addEventListener("click",t=>{t.stopPropagation(),this.showReAuthModal()}),e.addEventListener("click",()=>this.showReAuthModal())}hide(){const e=document.getElementById("globalSessionBanner");e&&e.remove(),this.isShowing=!1}showReAuthModal(){if(document.getElementById("globalReAuthModal"))return;const t=h.getAuthState().user,n=document.createElement("div");n.id="globalReAuthModal",n.className="modal",n.style.display="flex",n.style.zIndex="10001",n.innerHTML=`
      <div class="modal-content" style="max-width: 320px;">
        <div class="modal-header">
          <h3>Session Expired</h3>
          <button class="modal-close" id="closeGlobalReAuthModal">&times;</button>
        </div>
        <div class="modal-body">
          ${t?`
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 16px; padding: 12px; background: var(--bg-tertiary); border-radius: 8px;">
              <div style="width: 40px; height: 40px; border-radius: 50%; background: var(--primary); display: flex; align-items: center; justify-content: center; color: white; font-weight: bold;">
                ${(t.full_name||t.name||t.partner_name||"U").charAt(0).toUpperCase()}
              </div>
              <div>
                <div style="font-weight: 600; color: var(--text-primary);">${t.full_name||t.name||t.partner_name||"User"}</div>
                <div style="font-size: 12px; color: var(--text-secondary);">${t.emp_code||t.partner_code||t.mnr_id||""}</div>
              </div>
            </div>
          `:""}
          <p style="margin-bottom: 16px; color: var(--text-secondary);">
            Your session has expired. Please enter your password to continue.
          </p>
          <div class="form-group">
            <label>User ID</label>
            <input type="text" id="globalReAuthUserId" class="form-control" value="${t?.emp_code||t?.employee_id||t?.partner_code||t?.mnr_id||""}" placeholder="Enter your User ID" autocomplete="username">
          </div>
          <div class="form-group">
            <label>Password</label>
            <input type="password" id="globalReAuthPassword" class="form-control" placeholder="Enter your password" autocomplete="current-password">
          </div>
          <p id="globalReAuthError" class="form-error" style="display: none; color: var(--danger); margin-top: 8px;"></p>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" id="cancelGlobalReAuth">Cancel</button>
          <button class="btn btn-primary" id="submitGlobalReAuth">Login</button>
        </div>
      </div>
    `,document.body.appendChild(n),setTimeout(()=>{document.getElementById("globalReAuthPassword")?.focus()},100),document.getElementById("closeGlobalReAuthModal")?.addEventListener("click",()=>n.remove()),document.getElementById("cancelGlobalReAuth")?.addEventListener("click",()=>n.remove()),document.getElementById("submitGlobalReAuth")?.addEventListener("click",()=>this.submitReAuth()),document.getElementById("globalReAuthPassword")?.addEventListener("keypress",a=>{a.key==="Enter"&&this.submitReAuth()})}async submitReAuth(){const e=document.getElementById("globalReAuthUserId"),t=document.getElementById("globalReAuthPassword"),n=document.getElementById("globalReAuthError"),a=document.getElementById("submitGlobalReAuth");if(!t)return;const o=e?.value||"",s=t.value;if(!s){n&&(n.textContent="Please enter your password",n.style.display="block");return}a&&(a.disabled=!0,a.textContent="Logging in...");try{const i=h.getAuthState().user?.portal||"staff",d=await h.loginWithPassword(o,s,i);if(d.success){document.getElementById("globalReAuthModal")?.remove(),this.hide();const{offlineQueueService:u}=await k(async()=>{const{offlineQueueService:m}=await import("./services-AEce4KDH.js").then(x=>x.k);return{offlineQueueService:m}},__vite__mapDeps([0,1,2,3]));u.getStatus().pendingCount>0&&console.log("[SessionBanner] Re-auth successful, queued data will sync automatically"),console.log("[SessionBanner] Refreshing current page after successful re-auth"),window.dispatchEvent(new CustomEvent("login-success"))}else n&&(n.textContent=d.error||"Login failed. Please try again.",n.style.display="block")}catch(l){n&&(n.textContent=l.message||"An error occurred",n.style.display="block")}finally{a&&(a.disabled=!1,a.textContent="Login")}}}const K=new P;class B{container;fab=null;modal=null;messages=[];conversationHistory=[];isOpen=!1;isLoading=!1;constructor(){this.container=document.createElement("div"),this.container.id="vgk-mobile-root",document.body.appendChild(this.container),this.render()}getEndpoint(){const e=y.getPortal();return e==="staff"?"/api/v1/vgk/staff/process":e==="partner"?"/api/v1/vgk/partner/process":null}render(){if(!this.getEndpoint())return;this.container.innerHTML=`
      <style>
        #vgk-mobile-fab {
          position: fixed; bottom: 80px; right: 16px; z-index: 9999;
          width: 52px; height: 52px; border-radius: 50%;
          background: linear-gradient(135deg, #6c3de8, #a855f7);
          border: none; box-shadow: 0 4px 16px rgba(108,61,232,.5);
          cursor: pointer; display: flex; align-items: center; justify-content: center;
          font-size: 22px; transition: transform .2s;
        }
        #vgk-mobile-fab:active { transform: scale(.92); }
        #vgk-mobile-modal {
          position: fixed; bottom: 0; left: 0; right: 0; z-index: 10000;
          background: #1a1a2e; border-radius: 20px 20px 0 0;
          box-shadow: 0 -4px 32px rgba(0,0,0,.6);
          display: none; flex-direction: column; max-height: 75vh;
          transition: transform .3s;
        }
        #vgk-mobile-modal.open { display: flex; }
        #vgk-modal-header {
          display: flex; align-items: center; gap: 10px;
          padding: 14px 16px 10px; border-bottom: 1px solid #2d2d50;
        }
        #vgk-modal-header img { width: 28px; height: 28px; border-radius: 50%; }
        #vgk-modal-header span { font-weight: 600; color: #e2e8f0; font-size: 15px; flex: 1; }
        #vgk-close-btn {
          background: none; border: none; color: #94a3b8;
          font-size: 20px; cursor: pointer; padding: 4px 8px;
        }
        #vgk-messages {
          flex: 1; overflow-y: auto; padding: 12px 14px;
          display: flex; flex-direction: column; gap: 8px;
        }
        .vgk-bubble {
          max-width: 85%; padding: 9px 13px; border-radius: 16px;
          font-size: 13px; line-height: 1.45; word-break: break-word;
        }
        .vgk-bubble.user {
          background: #6c3de8; color: #fff;
          align-self: flex-end; border-bottom-right-radius: 4px;
        }
        .vgk-bubble.assistant {
          background: #2d2d50; color: #e2e8f0;
          align-self: flex-start; border-bottom-left-radius: 4px;
        }
        .vgk-typing { display: flex; gap: 4px; align-items: center; padding: 10px 14px; }
        .vgk-dot { width: 7px; height: 7px; border-radius: 50%; background: #6c3de8; animation: vgkDot 1.2s infinite; }
        .vgk-dot:nth-child(2) { animation-delay: .2s; }
        .vgk-dot:nth-child(3) { animation-delay: .4s; }
        @keyframes vgkDot { 0%,80%,100%{opacity:.3;transform:scale(.8)} 40%{opacity:1;transform:scale(1)} }
        #vgk-input-row {
          display: flex; align-items: center; gap: 8px;
          padding: 10px 14px; border-top: 1px solid #2d2d50;
        }
        #vgk-text-input {
          flex: 1; background: #2d2d50; border: 1px solid #3d3d70; border-radius: 20px;
          color: #e2e8f0; padding: 8px 14px; font-size: 13px; outline: none;
        }
        #vgk-text-input::placeholder { color: #64748b; }
        #vgk-send-btn, #vgk-mic-btn {
          background: none; border: none; font-size: 20px; cursor: pointer;
          padding: 4px 6px; color: #6c3de8;
        }
        #vgk-mic-btn.recording { color: #ef4444; animation: vgkPulse 1s infinite; }
        @keyframes vgkPulse { 0%,100%{opacity:1} 50%{opacity:.4} }
      </style>

      <button id="vgk-mobile-fab" aria-label="VGK Assistant">
        <img src="/public/vgk-assistant-logo.png" onerror="this.style.display='none';this.parentElement.textContent='🤖'" style="width:30px;height:30px;border-radius:50%;">
      </button>

      <div id="vgk-mobile-modal">
        <div id="vgk-modal-header">
          <img src="/public/vgk-assistant-logo.png" onerror="this.style.display='none'">
          <span>VGK Assistant</span>
          <button id="vgk-close-btn">✕</button>
        </div>
        <div id="vgk-messages"></div>
        <div id="vgk-input-row">
          <input id="vgk-text-input" type="text" placeholder="Ask me anything…" autocomplete="off">
          <button id="vgk-mic-btn" title="Voice input">🎤</button>
          <button id="vgk-send-btn" title="Send">➤</button>
        </div>
      </div>
    `,this.fab=this.container.querySelector("#vgk-mobile-fab"),this.modal=this.container.querySelector("#vgk-mobile-modal"),this.fab?.addEventListener("click",()=>this.open()),this.container.querySelector("#vgk-close-btn")?.addEventListener("click",()=>this.close());const t=this.container.querySelector("#vgk-text-input");this.container.querySelector("#vgk-send-btn")?.addEventListener("click",()=>{t.value.trim()&&(this.send(t.value.trim()),t.value="")}),t?.addEventListener("keypress",n=>{n.key==="Enter"&&t.value.trim()&&(this.send(t.value.trim()),t.value="")}),this.container.querySelector("#vgk-mic-btn")?.addEventListener("click",()=>this.startVoice(t)),this.pushMessage("assistant","Hi! I'm VGK Assistant. How can I help you today?")}open(){this.modal?.classList.add("open"),this.isOpen=!0,this.scrollToBottom()}close(){this.modal?.classList.remove("open"),this.isOpen=!1}pushMessage(e,t){this.messages.push({role:e,text:t}),this.renderMessages()}renderMessages(){const e=this.container.querySelector("#vgk-messages");e&&(e.innerHTML=this.messages.map(t=>`<div class="vgk-bubble ${t.role}">${t.text.replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/\n/g,"<br>")}</div>`).join(""),this.isLoading&&(e.innerHTML+='<div class="vgk-typing"><div class="vgk-dot"></div><div class="vgk-dot"></div><div class="vgk-dot"></div></div>'),this.scrollToBottom())}scrollToBottom(){const e=this.container.querySelector("#vgk-messages");e&&(e.scrollTop=e.scrollHeight)}async send(e){if(this.isLoading)return;this.pushMessage("user",e),this.isLoading=!0,this.renderMessages();const t=this.getEndpoint();if(!t){this.pushMessage("assistant","Not available for this portal."),this.isLoading=!1;return}try{const n=await f.getToken(),o=await(await fetch(t,{method:"POST",headers:{"Content-Type":"application/json",...n?{Authorization:`Bearer ${n}`}:{}},body:JSON.stringify({user_message:e,conversation_history:this.conversationHistory.slice(-20),language:"en",company_id:null,allowed_intents:null})})).json();if(o.reply_text){if(this.conversationHistory.push({role:"user",text:e}),this.conversationHistory.push({role:"assistant",text:o.reply_text}),this.conversationHistory.length>20&&(this.conversationHistory=this.conversationHistory.slice(-20)),this.pushMessage("assistant",o.reply_text),o.speak_text&&"speechSynthesis"in window){const s=new SpeechSynthesisUtterance(o.speak_text);s.lang="en-IN",s.rate=1,window.speechSynthesis.speak(s)}}else this.pushMessage("assistant",o.detail||"Something went wrong.")}catch{this.pushMessage("assistant","Could not reach VGK server. Please try again.")}this.isLoading=!1,this.renderMessages()}startVoice(e){const t=window.SpeechRecognition||window.webkitSpeechRecognition;if(!t){alert("Voice input not supported on this device.");return}const n=this.container.querySelector("#vgk-mic-btn"),a=new t;a.lang="en-IN",a.continuous=!1,a.interimResults=!1,a.onstart=()=>n.classList.add("recording"),a.onresult=o=>{const s=o.results[0][0].transcript;e.value=s},a.onend=()=>n.classList.remove("recording"),a.onerror=()=>n.classList.remove("recording"),a.start()}}function Y(){const c=y.getPortal();(c==="staff"||c==="partner")&&new B}export{G as B,V as L,z as M,v as P,U as g,Y as i,H as m,j as p,K as s};
