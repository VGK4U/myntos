const __vite__mapDeps=(i,m=__vite__mapDeps,d=(m.f||(m.f=["./services-D8IBt05T.js","./vendor-capacitor-plugins-DTPsYLMi.js","./vendor-capacitor-core-zwN_Y1fq.js","./vendor-B1GRRwIS.js"])))=>i.map(i=>d[i]);
import{t as y,j as L,b as _,n as M,d as v,r as w}from"./services-D8IBt05T.js";import{L as x}from"./vendor-B1GRRwIS.js";import{_ as N}from"./vendor-capacitor-plugins-DTPsYLMi.js";import{gpsService as O}from"./services-gps-Drz8whbb.js";class ${modalEl=null;uiState="CLOSED";currentOptions=null;enteredNumber="";isDtmfOpen=!1;unsubscribeTelephony=null;currentSession=null;floatingPos={x:0,y:0};pillPos={x:0,y:0};isDraggingWindow=!1;isDraggingPill=!1;dragStartPointer={x:0,y:0};dragStartPos={x:0,y:0};hasInitializedPosition=!1;lastNotifiedLeadId=null;constructor(){typeof window<"u"&&(window.addEventListener("keydown",e=>{e.key==="Escape"&&this.isOpen()&&(this.uiState==="ACTIVE_FLOATING"?this.minimize():this.uiState==="DIALER"&&this.close())}),window.addEventListener("resize",()=>{this.isOpen()&&(this.clampPositions(),this.applyPositions())}))}isOpen(){return this.modalEl!==null&&document.body.contains(this.modalEl)&&this.uiState!=="CLOSED"}getUIState(){return this.uiState}open(e){this.currentOptions=e,this.enteredNumber=(e.phoneNumber||"").replace(/[^\d+]/g,""),this.isDtmfOpen=!1,this.hasInitializedPosition=!1,this.unsubscribeTelephony&&this.unsubscribeTelephony(),this.unsubscribeTelephony=y.subscribe(a=>{this.currentSession=a,this.handleTelephonyStateUpdate(a)});const t=y.isCallActive();this.uiState=t?"ACTIVE_FLOATING":"DIALER",this.render(),this.loadLeadContext(e.entityId),e.autoStart&&this.enteredNumber&&this.startCall()}minimize(){this.uiState!=="CLOSED"&&(this.uiState="MINIMIZED",this.updateVisibility())}restore(){this.uiState!=="CLOSED"&&(this.uiState="ACTIVE_FLOATING",this.updateVisibility(),this.updateSessionUI())}close(){if(this.currentSession&&(y.isCallActive()||["connecting","ringing","connected","held"].includes(this.currentSession.state))){this.minimize();return}this.teardown()}forceCloseAndHangup(){this.currentSession&&y.isCallActive()&&y.endCall(),this.teardown()}teardown(){this.unsubscribeTelephony&&(this.unsubscribeTelephony(),this.unsubscribeTelephony=null),this.modalEl&&(this.modalEl.remove(),this.modalEl=null),this.uiState="CLOSED",this.currentOptions=null,this.currentSession=null,this.hasInitializedPosition=!1,this.lastNotifiedLeadId=null}handleTelephonyStateUpdate(e){if(!this.modalEl||!document.body.contains(this.modalEl))if(e.state!=="idle")this.render();else return;if(y.isCallActive()){this.uiState==="DIALER"&&(this.uiState="ACTIVE_FLOATING");const a=Number(this.currentOptions?.entityId);a&&(this.currentOptions?.entityType==="lead"||!this.currentOptions?.entityType)&&this.lastNotifiedLeadId!==a&&(this.lastNotifiedLeadId=a,L.notifyCallActive(a))}else if(this.lastNotifiedLeadId=null,e.state==="ended"){this.uiState="ENDED_SUMMARY";const a=this.currentOptions,n=e.durationSeconds||0;L.clearCallActive(),a?.entityId&&window.dispatchEvent(new CustomEvent("myntos:lead-call-ended",{detail:{leadId:a.entityId,name:a.name,phoneNumber:a.phoneNumber,durationSeconds:n,categoryName:a.categoryName,status:a.status}})),setTimeout(()=>{this.uiState==="ENDED_SUMMARY"&&this.teardown()},1600)}else if(e.state==="idle"&&this.uiState!=="DIALER"){L.clearCallActive(),this.teardown();return}this.updateVisibility(),this.updateSessionUI()}maskPhone(e){if(!e)return"—";const t=e.replace(/\D/g,"");if(t.length<6)return e;const a=t.slice(-10);return`+91 ${a.slice(0,2)}••••${a.slice(-4)}`}formatDuration(e){const t=Math.floor(e/60).toString().padStart(2,"0"),a=(e%60).toString().padStart(2,"0");return`${t}:${a}`}initPositions(){if(this.hasInitializedPosition||typeof window>"u")return;const e=window.innerWidth,t=window.innerHeight,a=Math.min(400,e-24),n=440,i=Math.max(12,Math.round((e-a)/2)),o=Math.max(20,Math.round((t-n)/2));this.floatingPos={x:i,y:o},this.pillPos={x:Math.max(12,e-260),y:Math.max(20,t-100)},this.hasInitializedPosition=!0}clampPositions(){if(typeof window>"u")return;const e=window.innerWidth,t=window.innerHeight,a=Math.min(400,e-24),n=440,i=12,o=Math.max(12,e-a-12),p=12,s=Math.max(12,t-n-12);this.floatingPos.x=Math.min(Math.max(this.floatingPos.x,i),o),this.floatingPos.y=Math.min(Math.max(this.floatingPos.y,p),s);const r=240,d=54,l=12,c=Math.max(12,e-r-12),f=12,u=Math.max(12,t-d-12);this.pillPos.x=Math.min(Math.max(this.pillPos.x,l),c),this.pillPos.y=Math.min(Math.max(this.pillPos.y,f),u)}applyPositions(){const e=this.modalEl?.querySelector("#spModalDialog");e&&(this.uiState==="ACTIVE_FLOATING"||this.uiState==="DIALER")&&(e.style.transform=`translate3d(${this.floatingPos.x}px, ${this.floatingPos.y}px, 0)`);const t=this.modalEl?.querySelector("#spMinimizedPill");t&&this.uiState==="MINIMIZED"&&(t.style.transform=`translate3d(${this.pillPos.x}px, ${this.pillPos.y}px, 0)`)}render(){this.modalEl&&this.modalEl.remove(),this.initPositions(),this.clampPositions();const{name:e,entityType:t}=this.currentOptions||{},a=e||"Customer Lead",n=t?t.toUpperCase():"LEAD";this.modalEl=document.createElement("div"),this.modalEl.id="myntosCentralSoftphoneModal",this.modalEl.style.cssText=`
      position: fixed !important; top: 0 !important; left: 0 !important; right: 0 !important; bottom: 0 !important;
      width: 100vw !important; height: 100vh !important; z-index: 2147483647 !important;
      pointer-events: none !important;
      isolation: isolate !important; filter: none !important; -webkit-filter: none !important;
      background: transparent !important; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif !important;
    `,this.modalEl.innerHTML=`
      <!-- 1. Dedicated Backdrop (Active only during initial DIALER entry; hidden during active call) -->
      <div id="spModalBackdrop" style="position: absolute !important; inset: 0 !important; width: 100% !important; height: 100% !important; background: rgba(15, 23, 42, 0.7) !important; backdrop-filter: blur(6px) !important; -webkit-backdrop-filter: blur(6px) !important; z-index: 1 !important; pointer-events: auto !important; display: ${this.uiState==="DIALER"?"block":"none"} !important;"></div>

      <!-- 2. Floating Modal Dialog Box (Pointer-events auto, Draggable) -->
      <div id="spModalDialog" class="sp-dialog-box" style="position: absolute !important; top: 0 !important; left: 0 !important; z-index: 10 !important; width: calc(100% - 24px) !important; max-width: 400px !important; background: #ffffff !important; border-radius: 20px !important; box-shadow: 0 25px 60px -15px rgba(0,0,0,0.6), 0 0 0 1px rgba(226, 232, 240, 0.9) !important; overflow: hidden !important; pointer-events: auto !important; transform: translate3d(${this.floatingPos.x}px, ${this.floatingPos.y}px, 0) !important; -webkit-transform: translate3d(${this.floatingPos.x}px, ${this.floatingPos.y}px, 0) !important; will-change: transform, opacity !important; isolation: isolate !important; touch-action: none !important;">
        
        <!-- Draggable Floating Header -->
        <div id="spFloatingHeader" style="background: linear-gradient(135deg, #1e293b, #0f172a) !important; padding: 12px 16px !important; color: #ffffff !important; display: flex !important; align-items: center !important; justify-content: space-between !important; border-bottom: 1px solid rgba(255,255,255,0.1) !important; cursor: move !important; user-select: none !important; -webkit-user-select: none !important;">
          <div style="display: flex !important; align-items: center !important; gap: 10px !important; pointer-events: none !important;">
            <div style="width: 30px !important; height: 30px !important; border-radius: 8px !important; background: rgba(56,189,248,0.2) !important; color: #38bdf8 !important; display: flex !important; align-items: center !important; justify-content: center !important; font-size: 13px !important;">
              📞
            </div>
            <div>
              <div style="font-weight: 700 !important; font-size: 14px !important; line-height: 1.2 !important; color: #ffffff !important;">Softphone Call</div>
              <div style="font-size: 10px !important; color: #94a3b8 !important;" id="spHeaderStatusText">🟢 Cloud Telephony Trunk</div>
            </div>
          </div>
          <div style="display: flex !important; align-items: center !important; gap: 8px !important;">
            <!-- Minimize Button (—) -->
            <button id="spMinimizeBtn" style="background: rgba(255,255,255,0.15) !important; border: none !important; color: #cbd5e1 !important; width: 28px !important; height: 28px !important; border-radius: 50% !important; cursor: pointer !important; font-size: 13px !important; font-weight: bold !important; display: flex !important; align-items: center !important; justify-content: center !important;" title="Minimize Call Window">⚊</button>
            <!-- Close / Minimize Button (✕) -->
            <button id="spCloseBtn" style="background: rgba(255,255,255,0.15) !important; border: none !important; color: #cbd5e1 !important; width: 28px !important; height: 28px !important; border-radius: 50% !important; cursor: pointer !important; font-size: 13px !important; display: flex !important; align-items: center !important; justify-content: center !important;" title="Minimize or Close">✕</button>
          </div>
        </div>

        <!-- Caller Context Banner -->
        <div style="background: #f8fafc !important; padding: 10px 16px !important; border-bottom: 1px solid #e2e8f0 !important; display: flex !important; align-items: center !important; justify-content: space-between !important;">
          <div style="min-width: 0 !important; flex: 1 !important;">
            <div style="display: flex !important; align-items: center !important; gap: 6px !important;">
              <span style="font-weight: 700 !important; font-size: 14px !important; color: #0f172a !important; white-space: nowrap !important; overflow: hidden !important; text-overflow: ellipsis !important;" id="spCallerName">${a}</span>
              <span style="background: #e0f2fe !important; color: #0369a1 !important; font-size: 10px !important; font-weight: 700 !important; padding: 1px 6px !important; border-radius: 4px !important;">${n}</span>
            </div>
            <div style="font-size: 12px !important; color: #64748b !important; margin-top: 1px !important;" id="spCallerPhoneDisplay">${this.maskPhone(this.enteredNumber)}</div>
          </div>
        </div>

        <!-- Body: Dialer & In-Call Views -->
        <div style="position: relative !important; min-height: 340px !important; background: #ffffff !important;">
          
          <!-- DIALER VIEW (Shown pre-call) -->
          <div id="spDialerView" style="padding: 14px 16px !important; display: ${this.uiState==="DIALER"?"block":"none"} !important;">
            
            <!-- Number Display -->
            <div style="background: #f1f5f9 !important; border-radius: 12px !important; padding: 8px 12px !important; display: flex !important; align-items: center !important; justify-content: space-between !important; margin-bottom: 12px !important; border: 1px solid #cbd5e1 !important;">
              <input type="text" id="spDialInput" value="${this.enteredNumber}" placeholder="Enter phone number..." style="background: transparent !important; border: none !important; outline: none !important; font-size: 17px !important; font-weight: 700 !important; color: #0f172a !important; width: 100% !important; letter-spacing: 0.5px !important;" />
              <button id="spBackspaceBtn" style="background: transparent !important; border: none !important; color: #64748b !important; font-size: 16px !important; cursor: pointer !important; padding: 4px 6px !important;" title="Backspace">⌫</button>
            </div>

            <!-- 3x4 Keypad Grid -->
            <div style="display: grid !important; grid-template-columns: repeat(3, 1fr) !important; gap: 6px !important; margin-bottom: 12px !important;">
              ${[{k:"1",s:"&nbsp;"},{k:"2",s:"ABC"},{k:"3",s:"DEF"},{k:"4",s:"GHI"},{k:"5",s:"JKL"},{k:"6",s:"MNO"},{k:"7",s:"PQRS"},{k:"8",s:"TUV"},{k:"9",s:"WXYZ"},{k:"*",s:"&nbsp;"},{k:"0",s:"+"},{k:"#",s:"&nbsp;"}].map(i=>`
                <button class="sp-num-btn" data-key="${i.k}" style="background: #f8fafc !important; border: 1px solid #e2e8f0 !important; border-radius: 8px !important; padding: 6px 4px !important; cursor: pointer !important; display: flex !important; flex-direction: column !important; align-items: center !important; justify-content: center !important; user-select: none !important;">
                  <div style="font-size: 17px !important; font-weight: 700 !important; color: #0f172a !important; line-height: 1.1 !important;">${i.k}</div>
                  <div style="font-size: 8px !important; font-weight: 600 !important; color: #64748b !important; letter-spacing: 1px !important; line-height: 1 !important; margin-top: 1px !important;">${i.s}</div>
                </button>
              `).join("")}
            </div>

            <!-- Action Controls -->
            <div style="display: flex !important; align-items: center !important; justify-content: space-between !important; gap: 8px !important; margin-top: 4px !important;">
              <button id="spDirectSimBtn" style="flex: 1 !important; padding: 8px 6px !important; border-radius: 8px !important; background: #ecfdf5 !important; border: 1px solid #a7f3d0 !important; color: #059669 !important; font-size: 11px !important; font-weight: 700 !important; cursor: pointer !important; display: flex !important; align-items: center !important; justify-content: center !important; gap: 4px !important;">
                📱 Direct SIM
              </button>

              <button id="spMainDialBtn" style="width: 50px !important; height: 50px !important; border-radius: 50% !important; background: linear-gradient(135deg, #10b981, #059669) !important; border: none !important; color: #ffffff !important; font-size: 20px !important; cursor: pointer !important; box-shadow: 0 6px 16px rgba(16,185,129,0.35) !important; display: flex !important; align-items: center !important; justify-content: center !important;" title="Place Call">
                📞
              </button>

              <button id="spMyOperatorBtn" style="flex: 1 !important; padding: 8px 6px !important; border-radius: 8px !important; background: #f5f3ff !important; border: 1px solid #ddd6fe !important; color: #7c3aed !important; font-size: 11px !important; font-weight: 700 !important; cursor: pointer !important; display: flex !important; align-items: center !important; justify-content: center !important; gap: 4px !important;">
                🏢 MyOperator
              </button>
            </div>

            <div id="spErrorBanner" style="display: none; margin-top: 10px !important; padding: 6px 10px !important; background: #fef2f2 !important; border: 1px solid #fecaca !important; border-radius: 6px !important; color: #dc2626 !important; font-size: 11px !important; text-align: center !important;"></div>
          </div>

          <!-- IN-CALL ACTIVE OVERLAY VIEW (Shown during active call) -->
          <div id="spInCallView" style="display: ${this.uiState==="ACTIVE_FLOATING"||this.uiState==="ENDED_SUMMARY"?"flex":"none"} !important; position: absolute !important; inset: 0 !important; background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%) !important; color: #ffffff !important; padding: 18px 16px !important; z-index: 20 !important; flex-direction: column !important; justify-content: space-between !important; align-items: center !important;">
            
            <div style="text-align: center !important; margin-top: 4px !important; width: 100% !important;">
              <div style="width: 54px !important; height: 54px !important; border-radius: 50% !important; background: linear-gradient(135deg, #3b82f6, #1d4ed8) !important; color: white !important; display: flex !important; align-items: center !important; justify-content: center !important; font-size: 22px !important; margin: 0 auto 8px auto !important; box-shadow: 0 0 20px rgba(59,130,246,0.5) !important;">
                👤
              </div>
              <div id="spActiveCallerName" style="font-weight: 700 !important; font-size: 16px !important; color: #ffffff !important; white-space: nowrap !important; overflow: hidden !important; text-overflow: ellipsis !important;">${a}</div>
              <div id="spActiveCallerPhone" style="font-size: 12px !important; color: #94a3b8 !important; margin-top: 2px !important;">${this.maskPhone(this.enteredNumber)}</div>
              
              <div id="spActiveLeadPills" style="margin-top: 6px !important; display: flex !important; align-items: center !important; justify-content: center !important; gap: 6px !important; flex-wrap: wrap !important;">
                <span id="spHeaderCatBadge" style="${this.currentOptions?.categoryName?"":"display:none;"} background: rgba(14, 165, 233, 0.2) !important; color: #38bdf8 !important; border: 1px solid rgba(56, 189, 248, 0.4) !important; font-size: 10px !important; font-weight: 600 !important; padding: 2px 7px !important; border-radius: 4px !important;">🏷️ ${this.currentOptions?.categoryName||""}</span>
                <span id="spHeaderStatusBadge" style="${this.currentOptions?.status?"":"display:none;"} background: rgba(255, 255, 255, 0.1) !important; color: #f1f5f9 !important; border: 1px solid rgba(255, 255, 255, 0.2) !important; font-size: 10px !important; font-weight: 600 !important; padding: 2px 7px !important; border-radius: 4px !important;">📌 ${this.currentOptions?.status||""}</span>
                <span id="spHeaderTempBadge" style="${this.currentOptions?.isHotLead||this.currentOptions?.isFreshLead?"":"display:none;"} ${this.currentOptions?.isHotLead?"background: rgba(239, 68, 68, 0.2) !important; color: #ef4444 !important; border: 1px solid rgba(239, 68, 68, 0.4) !important;":"background: rgba(16, 185, 129, 0.2) !important; color: #10b981 !important; border: 1px solid rgba(16, 185, 129, 0.4) !important;"} font-size: 10px !important; font-weight: 700 !important; padding: 2px 7px !important; border-radius: 4px !important;">${this.currentOptions?.isHotLead?"🔥 HOT LEAD":this.currentOptions?.isFreshLead?"🌱 FRESH LEAD":""}</span>
              </div>

              <div style="margin-top: 8px !important; display: flex !important; align-items: center !important; justify-content: center !important; gap: 8px !important;">
                <span id="spCallStateBadge" style="background: #f59e0b !important; color: #000000 !important; font-size: 11px !important; font-weight: 700 !important; padding: 2px 8px !important; border-radius: 12px !important;">Connecting...</span>
                <span id="spCallTimerDisplay" style="font-size: 14px !important; font-weight: 700 !important; color: #38bdf8 !important;">00:00</span>
              </div>
            </div>

            <!-- Comprehensive In-Call Lead Context Card (17 Canonical Fields) -->
            <div id="spLeadContextBox" style="display: none; width: 100% !important; max-height: 150px !important; overflow-y: auto !important; background: rgba(15, 23, 42, 0.75) !important; border: 1px solid rgba(56, 189, 248, 0.25) !important; border-radius: 12px !important; padding: 8px 10px !important; margin: 6px 0 !important; font-size: 11px !important; box-sizing: border-box !important; text-align: left !important; -webkit-overflow-scrolling: touch !important;">
              <div style="display: flex !important; align-items: center !important; justify-content: space-between !important; border-bottom: 1px solid rgba(255,255,255,0.1) !important; padding-bottom: 4px !important; margin-bottom: 6px !important;">
                <span style="font-size: 10px !important; font-weight: 800 !important; letter-spacing: 0.5px !important; color: #38bdf8 !important; text-transform: uppercase !important;">📋 Lead Context</span>
                <span id="spMobileCatBadge" style="background: #0284c7 !important; color: white !important; font-size: 9px !important; font-weight: 700 !important; padding: 1px 6px !important; border-radius: 4px !important;">General</span>
              </div>
              <div style="display: grid !important; grid-template-columns: 1fr 1fr !important; gap: 4px 8px !important; font-size: 10px !important;">
                <div><span style="color: #94a3b8 !important;">Source:</span> <span id="spMobileSource" style="color: #f1f5f9 !important; font-weight: 600 !important;">—</span></div>
                <div><span style="color: #94a3b8 !important;">Company:</span> <span id="spMobileCompany" style="color: #f1f5f9 !important; font-weight: 600 !important;">—</span></div>
                <div><span style="color: #94a3b8 !important;">Status:</span> <span id="spMobileStatus" style="color: #38bdf8 !important; font-weight: 600 !important;">—</span></div>
                <div><span style="color: #94a3b8 !important;">Updated:</span> <span id="spMobileStatusUpdated" style="color: #cbd5e1 !important;">—</span></div>
                <div><span style="color: #94a3b8 !important;">Budget:</span> <span id="spMobileBudget" style="color: #34d399 !important; font-weight: 600 !important;">—</span></div>
                <div><span style="color: #94a3b8 !important;">Last Contact:</span> <span id="spMobileLastInteraction" style="color: #cbd5e1 !important;">—</span></div>
                <div style="grid-column: span 2 !important;"><span style="color: #94a3b8 !important;">Called By:</span> <span id="spMobileInteractedBy" style="color: #cbd5e1 !important;">—</span></div>
                <div style="grid-column: span 2 !important;"><span style="color: #94a3b8 !important;">Last Dialed:</span> <span id="spMobileLastDialed" style="color: #cbd5e1 !important;">—</span></div>
                <div id="spMobileReqRow" style="grid-column: span 2 !important; display: none !important;"><span style="color: #94a3b8 !important;">Requirements:</span> <span id="spMobileRequirements" style="color: #f8fafc !important;">—</span></div>
              </div>
              <div id="spMobileNotesSection" style="margin-top: 6px !important; border-top: 1px dashed rgba(255,255,255,0.1) !important; padding-top: 4px !important; display: none !important;">
                <div style="font-size: 9px !important; font-weight: 700 !important; color: #94a3b8 !important; text-transform: uppercase !important;">Recent Notes</div>
                <div id="spMobileRecentNotes" style="font-size: 10px !important; color: #cbd5e1 !important; margin-top: 2px !important;"></div>
              </div>
            </div>

            <!-- In-Call DTMF Pad -->
            <div id="spDtmfGrid" style="display: none; width: 100% !important; max-width: 200px !important; grid-template-columns: repeat(3, 1fr) !important; gap: 4px !important; margin: 6px auto !important;">
              ${["1","2","3","4","5","6","7","8","9","*","0","#"].map(i=>`
                <button class="sp-dtmf-btn" data-dtmf="${i}" style="background: rgba(255,255,255,0.15) !important; border: 1px solid rgba(255,255,255,0.2) !important; color: white !important; border-radius: 6px !important; font-weight: bold !important; padding: 5px !important; font-size: 12px !important; cursor: pointer !important;">${i}</button>
              `).join("")}
            </div>

            <!-- In-Call 4 Control Buttons (Mute, Speaker, Hold, DTMF) -->
            <div style="display: flex !important; flex-direction: column !important; align-items: center !important; gap: 12px !important; width: 100% !important;">
              <div style="display: flex !important; justify-content: center !important; gap: 10px !important; width: 100% !important;">
                <button id="spBtnMute" style="width: 44px !important; height: 44px !important; border-radius: 50% !important; background: rgba(255,255,255,0.1) !important; border: 1px solid rgba(255,255,255,0.2) !important; color: white !important; display: flex !important; flex-direction: column !important; align-items: center !important; justify-content: center !important; font-size: 13px !important; cursor: pointer !important;">
                  🎤
                  <span style="font-size: 8px !important; margin-top: 1px !important;">Mute</span>
                </button>

                <button id="spBtnSpeaker" style="width: 44px !important; height: 44px !important; border-radius: 50% !important; background: rgba(255,255,255,0.1) !important; border: 1px solid rgba(255,255,255,0.2) !important; color: white !important; display: flex !important; flex-direction: column !important; align-items: center !important; justify-content: center !important; font-size: 13px !important; cursor: pointer !important;">
                  🔊
                  <span style="font-size: 8px !important; margin-top: 1px !important;">Speaker</span>
                </button>

                <button id="spBtnHold" style="width: 44px !important; height: 44px !important; border-radius: 50% !important; background: rgba(255,255,255,0.1) !important; border: 1px solid rgba(255,255,255,0.2) !important; color: white !important; display: flex !important; flex-direction: column !important; align-items: center !important; justify-content: center !important; font-size: 13px !important; cursor: pointer !important;">
                  ⏸
                  <span style="font-size: 8px !important; margin-top: 1px !important;">Hold</span>
                </button>

                <button id="spBtnKeypad" style="width: 44px !important; height: 44px !important; border-radius: 50% !important; background: rgba(255,255,255,0.1) !important; border: 1px solid rgba(255,255,255,0.2) !important; color: white !important; display: flex !important; flex-direction: column !important; align-items: center !important; justify-content: center !important; font-size: 13px !important; cursor: pointer !important;">
                  🔢
                  <span style="font-size: 8px !important; margin-top: 1px !important;">Keypad</span>
                </button>
              </div>

              <!-- End Call (Hangup) Red Button -->
              <button id="spBtnHangup" style="width: 52px !important; height: 52px !important; border-radius: 50% !important; background: linear-gradient(135deg, #ef4444, #dc2626) !important; border: none !important; color: white !important; font-size: 20px !important; cursor: pointer !important; box-shadow: 0 8px 20px rgba(239,68,68,0.4) !important; display: flex !important; align-items: center !important; justify-content: center !important;" title="End Call">
                🛑
              </button>
            </div>

          </div>

        </div>
      </div>

      <!-- 3. Minimized Floating Pill (Compact Draggable Widget) -->
      <div id="spMinimizedPill" style="position: absolute !important; top: 0 !important; left: 0 !important; z-index: 20 !important; display: ${this.uiState==="MINIMIZED"?"flex":"none"} !important; align-items: center !important; gap: 8px !important; background: linear-gradient(135deg, #0f172a, #1e293b) !important; color: #ffffff !important; border: 1px solid #38bdf8 !important; border-radius: 9999px !important; padding: 8px 14px !important; box-shadow: 0 10px 25px rgba(0,0,0,0.5), 0 0 15px rgba(56,189,248,0.3) !important; cursor: move !important; pointer-events: auto !important; transform: translate3d(${this.pillPos.x}px, ${this.pillPos.y}px, 0) !important; -webkit-transform: translate3d(${this.pillPos.x}px, ${this.pillPos.y}px, 0) !important; touch-action: none !important; user-select: none !important; -webkit-user-select: none !important;">
        <div style="width: 10px !important; height: 10px !important; border-radius: 50% !important; background: #22c55e !important; box-shadow: 0 0 8px #22c55e !important; animation: spPulse 1.5s infinite !important;"></div>
        <div style="min-width: 0 !important; max-width: 110px !important; overflow: hidden !important; text-overflow: ellipsis !important; white-space: nowrap !important; font-weight: 700 !important; font-size: 12px !important;" id="spPillCallerName">${a}</div>
        <div style="color: #38bdf8 !important; font-weight: 700 !important; font-size: 12px !important;" id="spPillTimerDisplay">00:00</div>
        <button id="spPillRestoreBtn" style="background: rgba(56,189,248,0.2) !important; border: 1px solid rgba(56,189,248,0.4) !important; color: #38bdf8 !important; border-radius: 50% !important; width: 24px !important; height: 24px !important; font-size: 11px !important; font-weight: bold !important; cursor: pointer !important; display: flex !important; align-items: center !important; justify-content: center !important; margin-left: 2px !important;" title="Restore Softphone Window">▲</button>
      </div>
    `,document.body.appendChild(this.modalEl),this.attachEventListeners(),this.attachDragListeners(),this.updateVisibility(),this.updateSessionUI()}attachDragListeners(){if(!this.modalEl)return;const e=this.modalEl.querySelector("#spFloatingHeader"),t=this.modalEl.querySelector("#spModalDialog");if(e&&t){e.addEventListener("pointerdown",i=>{const o=i.target;if(!(o&&o.closest("button, input, a"))){this.isDraggingWindow=!0,this.dragStartPointer={x:i.clientX,y:i.clientY},this.dragStartPos={x:this.floatingPos.x,y:this.floatingPos.y};try{e.setPointerCapture(i.pointerId)}catch{}i.preventDefault(),i.stopPropagation()}}),e.addEventListener("pointermove",i=>{if(!this.isDraggingWindow)return;const o=i.clientX-this.dragStartPointer.x,p=i.clientY-this.dragStartPointer.y;this.floatingPos={x:this.dragStartPos.x+o,y:this.dragStartPos.y+p},this.clampPositions(),t.style.transform=`translate3d(${this.floatingPos.x}px, ${this.floatingPos.y}px, 0)`});const n=i=>{if(this.isDraggingWindow){this.isDraggingWindow=!1;try{e.releasePointerCapture(i.pointerId)}catch{}this.clampPositions(),t.style.transform=`translate3d(${this.floatingPos.x}px, ${this.floatingPos.y}px, 0)`}};e.addEventListener("pointerup",n),e.addEventListener("pointercancel",n)}const a=this.modalEl.querySelector("#spMinimizedPill");if(a){let n=!1;a.addEventListener("pointerdown",o=>{const p=o.target;if(!(p&&p.closest("#spPillRestoreBtn"))){this.isDraggingPill=!0,n=!1,this.dragStartPointer={x:o.clientX,y:o.clientY},this.dragStartPos={x:this.pillPos.x,y:this.pillPos.y};try{a.setPointerCapture(o.pointerId)}catch{}o.preventDefault(),o.stopPropagation()}}),a.addEventListener("pointermove",o=>{if(!this.isDraggingPill)return;const p=o.clientX-this.dragStartPointer.x,s=o.clientY-this.dragStartPointer.y;(Math.abs(p)>3||Math.abs(s)>3)&&(n=!0),this.pillPos={x:this.dragStartPos.x+p,y:this.dragStartPos.y+s},this.clampPositions(),a.style.transform=`translate3d(${this.pillPos.x}px, ${this.pillPos.y}px, 0)`});const i=o=>{if(this.isDraggingPill){this.isDraggingPill=!1;try{a.releasePointerCapture(o.pointerId)}catch{}this.clampPositions(),a.style.transform=`translate3d(${this.pillPos.x}px, ${this.pillPos.y}px, 0)`,n||this.restore()}};a.addEventListener("pointerup",i),a.addEventListener("pointercancel",i)}}attachEventListeners(){if(!this.modalEl)return;this.modalEl.querySelector("#spModalBackdrop")?.addEventListener("click",()=>{this.uiState==="DIALER"&&this.close()}),this.modalEl.querySelector("#spMinimizeBtn")?.addEventListener("click",t=>{t.stopPropagation(),this.minimize()}),this.modalEl.querySelector("#spCloseBtn")?.addEventListener("click",t=>{t.stopPropagation(),this.close()}),this.modalEl.querySelector("#spPillRestoreBtn")?.addEventListener("click",t=>{t.stopPropagation(),this.restore()});const e=this.modalEl.querySelector("#spDialInput");e?.addEventListener("input",t=>{this.enteredNumber=t.target.value,this.updateCallerPhoneDisplay()}),this.modalEl.querySelector("#spBackspaceBtn")?.addEventListener("click",()=>{this.enteredNumber.length>0&&(this.enteredNumber=this.enteredNumber.slice(0,-1),e&&(e.value=this.enteredNumber),this.updateCallerPhoneDisplay(),y.playKeyTone())}),this.modalEl.querySelectorAll(".sp-num-btn").forEach(t=>{t.addEventListener("click",a=>{const n=a.currentTarget.getAttribute("data-key");n&&this.enteredNumber.length<15&&(this.enteredNumber+=n,e&&(e.value=this.enteredNumber),this.updateCallerPhoneDisplay(),y.playKeyTone())})}),this.modalEl.querySelector("#spMainDialBtn")?.addEventListener("click",()=>{this.startCall()}),this.modalEl.querySelector("#spDirectSimBtn")?.addEventListener("click",()=>{if(!this.enteredNumber){this.showError("Please enter a phone number.");return}y.triggerDirectSimCall(this.enteredNumber)}),this.modalEl.querySelector("#spMyOperatorBtn")?.addEventListener("click",async()=>{if(!this.enteredNumber){this.showError("Please enter a phone number.");return}try{const t=this.currentOptions?.entityId?parseInt(String(this.currentOptions.entityId)):null;await y.triggerMyOperatorCall(this.enteredNumber,t),alert(`MyOperator call dispatched to ${this.enteredNumber}! Your office line will ring shortly.`)}catch(t){this.showError(`MyOperator error: ${t.message}`)}}),this.modalEl.querySelector("#spBtnMute")?.addEventListener("click",()=>{y.toggleMute()}),this.modalEl.querySelector("#spBtnSpeaker")?.addEventListener("click",()=>{y.toggleSpeaker()}),this.modalEl.querySelector("#spBtnHold")?.addEventListener("click",()=>{y.toggleHold()}),this.modalEl.querySelector("#spBtnKeypad")?.addEventListener("click",()=>{this.isDtmfOpen=!this.isDtmfOpen;const t=this.modalEl?.querySelector("#spDtmfGrid");t&&(t.style.display=this.isDtmfOpen?"grid":"none")}),this.modalEl.querySelectorAll(".sp-dtmf-btn").forEach(t=>{t.addEventListener("click",a=>{const n=a.currentTarget.getAttribute("data-dtmf");n&&y.sendDTMF(n)})}),this.modalEl.querySelector("#spBtnHangup")?.addEventListener("click",()=>{y.endCall()})}updateVisibility(){if(!this.modalEl)return;const e=this.modalEl.querySelector("#spModalBackdrop"),t=this.modalEl.querySelector("#spModalDialog"),a=this.modalEl.querySelector("#spMinimizedPill"),n=this.modalEl.querySelector("#spInCallView"),i=this.modalEl.querySelector("#spDialerView");this.uiState==="DIALER"?(e&&(e.style.display="block"),t&&(t.style.display="block"),a&&(a.style.display="none"),i&&(i.style.display="block"),n&&(n.style.display="none")):this.uiState==="ACTIVE_FLOATING"?(e&&(e.style.display="none"),t&&(t.style.display="block"),a&&(a.style.display="none"),i&&(i.style.display="none"),n&&(n.style.display="flex")):this.uiState==="MINIMIZED"?(e&&(e.style.display="none"),t&&(t.style.display="none"),a&&(a.style.display="flex")):this.uiState==="ENDED_SUMMARY"&&(e&&(e.style.display="none"),t&&(t.style.display="block"),a&&(a.style.display="none"),i&&(i.style.display="none"),n&&(n.style.display="flex"))}updateCallerPhoneDisplay(){const e=this.modalEl?.querySelector("#spCallerPhoneDisplay");e&&(e.textContent=this.maskPhone(this.enteredNumber))}showError(e){const t=this.modalEl?.querySelector("#spErrorBanner");t&&(t.textContent=e,t.style.display="block")}hideError(){const e=this.modalEl?.querySelector("#spErrorBanner");e&&(e.style.display="none")}async startCall(){if(y.prepareAudioOnUserGesture(),this.hideError(),!this.enteredNumber){this.showError("Please enter a destination phone number.");return}const e=this.currentOptions?.name||"Contact Lead",t=this.currentOptions?.entityId||null;this.uiState="ACTIVE_FLOATING",this.updateVisibility();const a=await y.startCall(this.enteredNumber,e,t);!a.success&&a.error&&(a.error==="A call is already in progress."?console.warn("[SoftphoneModal] Duplicate dial prevented; ignoring duplicate error toast"):this.showError(a.error))}updateSessionUI(){if(!this.modalEl||!this.currentSession)return;const e=this.currentSession.contactName||this.currentOptions?.name||"Contact Lead",t=this.currentSession.destinationPhone||this.enteredNumber,a=this.formatDuration(this.currentSession.durationSeconds),n=this.modalEl.querySelector("#spActiveCallerName");n&&(n.textContent=e);const i=this.modalEl.querySelector("#spActiveCallerPhone");i&&(i.textContent=this.maskPhone(t));const o=this.modalEl.querySelector("#spCallTimerDisplay");o&&(o.textContent=a);const p=this.modalEl.querySelector("#spPillCallerName");p&&(p.textContent=e);const s=this.modalEl.querySelector("#spPillTimerDisplay");s&&(s.textContent=a);const r=this.modalEl.querySelector("#spCallStateBadge");r&&(this.currentSession.state==="connected"?(r.textContent="🟢 Connected",r.style.background="#22c55e",r.style.color="#ffffff"):this.currentSession.state==="ringing"?(r.textContent="📞 Ringing...",r.style.background="#38bdf8",r.style.color="#000000"):this.currentSession.state==="connecting"?(r.textContent="⏳ Connecting...",r.style.background="#f59e0b",r.style.color="#000000"):this.currentSession.state==="ended"&&(r.textContent="🛑 Call Ended",r.style.background="#ef4444",r.style.color="#ffffff"));const d=this.modalEl.querySelector("#spBtnMute");d&&(d.style.background=this.currentSession.isMuted?"rgba(239,68,68,0.6)":"rgba(255,255,255,0.1)",d.style.borderColor=this.currentSession.isMuted?"#ef4444":"rgba(255,255,255,0.2)");const l=this.modalEl.querySelector("#spBtnSpeaker");l&&(l.style.background=this.currentSession.isSpeaker?"rgba(56,189,248,0.6)":"rgba(255,255,255,0.1)",l.style.borderColor=this.currentSession.isSpeaker?"#38bdf8":"rgba(255,255,255,0.2)");const c=this.modalEl.querySelector("#spBtnHold");c&&(c.style.background=this.currentSession.isHeld?"rgba(245,158,11,0.6)":"rgba(255,255,255,0.1)",c.style.borderColor=this.currentSession.isHeld?"#f59e0b":"rgba(255,255,255,0.2)")}async loadLeadContext(e){const t=this.modalEl?.querySelector("#spLeadContextBox");if(t){if(!e){t.style.display="none";return}try{const a=await _.get(`/crm/dialer/lead/${e}/detail`),n=a.data??a;if(!n||!n.lead)return;const i=n.lead;t.style.display="block";const o=this.modalEl?.querySelector("#spMobileCatBadge");o&&(o.textContent=i.category_name||"General");const p=this.modalEl?.querySelector("#spHeaderCatBadge");p&&(p.textContent=`🏷️ ${i.category_name||"General"}`,p.style.display="inline-block");const s=this.modalEl?.querySelector("#spMobileSource");s&&(s.textContent=i.source||"—");const r=this.modalEl?.querySelector("#spMobileCompany");r&&(r.textContent=i.company_name||"—");const d=this.modalEl?.querySelector("#spMobileStatus");d&&(d.textContent=(i.status||"—").toUpperCase(),d.style.color=i.status==="won"?"#22c55e":i.status==="lost"?"#ef4444":"#38bdf8");const l=this.modalEl?.querySelector("#spHeaderStatusBadge");l&&(l.textContent=`📌 ${i.status||"New"}`,l.style.display="inline-block");const c=this.modalEl?.querySelector("#spHeaderTempBadge");c&&(i.is_hot_lead?(c.textContent="🔥 HOT LEAD",c.style.background="rgba(239, 68, 68, 0.2)",c.style.color="#ef4444",c.style.border="1px solid rgba(239, 68, 68, 0.4)",c.style.display="inline-block"):i.is_fresh_lead?(c.textContent="🌱 FRESH LEAD",c.style.background="rgba(16, 185, 129, 0.2)",c.style.color="#10b981",c.style.border="1px solid rgba(16, 185, 129, 0.4)",c.style.display="inline-block"):c.style.display="none");const f=this.modalEl?.querySelector("#spMobileStatusUpdated");f&&(f.textContent=i.status_updated_at?new Date(i.status_updated_at).toLocaleDateString("en-IN",{day:"numeric",month:"short"}):"—");const u=this.modalEl?.querySelector("#spMobileBudget");u&&(u.textContent=i.budget_display||"—");const h=this.modalEl?.querySelector("#spMobileLastInteraction");h&&(h.textContent=i.last_interaction_date?new Date(i.last_interaction_date).toLocaleDateString("en-IN",{day:"numeric",month:"short"}):"Never");const m=this.modalEl?.querySelector("#spMobileInteractedBy");m&&(m.textContent=i.last_interacted_by||"—");const g=this.modalEl?.querySelector("#spMobileLastDialed");g&&(g.textContent=i.last_dialed_at?new Date(i.last_dialed_at).toLocaleDateString("en-IN",{day:"numeric",month:"short"}):"Never");const b=this.modalEl?.querySelector("#spMobileReqRow"),S=this.modalEl?.querySelector("#spMobileRequirements");b&&S&&(i.requirements?(S.textContent=i.requirements,b.style.display="block"):b.style.display="none");const k=this.modalEl?.querySelector("#spMobileNotesSection"),A=this.modalEl?.querySelector("#spMobileRecentNotes");if(k&&A){const C=(n.notes||[]).slice(0,2);C.length>0?(A.innerHTML=C.map(D=>`<div>• ${D.note}</div>`).join(""),k.style.display="block"):k.style.display="none"}}catch(a){console.warn("[SoftphoneModal] Could not fetch lead context:",a)}}}}const ie=new $,P={"/staff/dashboard":"dashboard","/staff/my-attendance":"attendance","/staff/my-leaves":"leaves","/staff/leave-approvals":"staff-leave-approvals","/staff/attendance-records":"team-attendance","/staff/attendance-sheet":"staff-attendance-sheet","/staff/attendance-reports":"staff-attendance-reports","/staff/attendance-exceptions":"staff-attendance-exceptions","/staff/attendance-computation":"staff-attendance-computation","/staff/tasks/assigned-by-me":"tasks-assigned","/staff/tasks/assigned-by-me-v2":"tasks-assigned","/staff/tasks/assigned-to-me":"tasks-received","/staff/tasks/team-activities":"staff-team-activities","/staff/tasks/task-tracker":"staff-task-tracker","/staff/tasks/task-reviews":"staff-task-reviews","/staff/task-review":"staff-task-reviews","/staff/my-kras":"kras","/staff/kra-templates":"staff-kra-templates","/staff/kra-tracking-sheet":"staff-kra-tracking","/staff/kra-review":"staff-kra-review","/staff/my-timesheet":"timesheet","/staff/timesheet-approval":"staff-timesheet-approval","/staff/my-journeys":"journeys","/staff/team-journeys":"team-journeys","/staff/all-journeys":"staff-all-journeys","/staff/vgk4u-journeys":"staff-vgk4u-journeys","/staff/vgk/members":"staff-vgk-members","/staff_vgk_members.html":"staff-vgk-members","/staff/my-reimbursement-claims":"reimbursements","/staff/reimbursement-approvals":"staff-reimbursement-approvals","/staff/accounts/my-reimbursements":"reimbursements","/staff/accounts/reimbursement-approvals":"staff-reimbursement-approvals","/staff/accounts/expense-entries":"staff-expense-entries","/staff/my-earnings":"staff-my-earnings","/staff/payroll-profile":"staff-payroll-profile","/staff/salary-slips":"staff-salary-slips","/staff/my-leads":"staff-my-leads","/staff/leads":"staff-leads","/staff/team-leads":"staff-team-leads","/staff/lead-sources":"staff-lead-sources","/staff/bank-wise-leads":"staff-bank-wise-leads","/staff/crm/bank-wise-leads":"staff-bank-wise-leads","/staff/solar-leads":"staff-leads","/staff/real-dreams-leads":"zynova-real-estate","/staff/insurance-leads":"zynova-insurance","/staff/ev-b2b-leads":"staff-leads","/staff/ev-b2c-leads":"staff-leads","/staff/ev-spares-leads":"staff-leads","/staff/etc-leads":"staff-training-videos","/staff/mnr-leads":"staff-leads","/staff/mnr-leads-master":"staff-leads","/staff/executive-dashboard":"dashboard","/staff/crm/whatsapp-inbox":"staff-whatsapp","/staff/crm/wa-inbox":"staff-whatsapp","/staff/whatsapp":"staff-whatsapp","/staff/whatsapp-inbox":"staff-whatsapp","/staff/whatsapp-center":"staff-whatsapp","/staff/crm/whatsapp-center":"staff-whatsapp","/staff/crm/whatsapp":"staff-whatsapp","/staff/call-tracking":"staff-call-tracking","/staff/vendors":"staff-vendors","/staff/zynova-real-estate":"staff-zynova-real-estate","/staff/zynova":"staff-zynova","/staff/zynova-insurance":"staff-zynova-insurance","/staff/settings":"settings","/staff/change-password":"change-password","/staff/employees":"staff-employees","/staff/training-videos":"staff-training-videos","/staff/employee-directory":"staff-directory","/staff/kyc-approvals":"staff-kyc-approvals","/staff/manager-review":"staff-review","/staff/auto-dialer":"auto-dialer","/staff/call-history":"call-history","/staff/operator-calls":"operator-calls","/staff/day-planner":"day-planner","/staff/tasks/day-planner":"day-planner","/staff/service":"staff-service","/staff/crm":"staff-crm","/staff/crm/dashboard":"staff-crm","/staff/crm/team-leads":"staff-team-leads","/staff/crm/lead-sources":"staff-lead-sources","/staff/call-management":"staff-call-tracking","/staff/dialer":"auto-dialer","/staff/softphone":"softphone","/staff/calling-page":"softphone","/staff/calling":"softphone","/staff/phone-dialpad":"softphone","/staff/softphone-hub":"softphone","/staff/tasks/tracker":"staff-task-tracker","/staff/service-tickets/dashboard":"staff-service","/staff/service-tickets/performance":"staff-service-performance","/staff/service-tickets/procurement":"staff-service-procurement","/staff/service-tickets/procurement-queue":"staff-service-procurement-queue","/staff/service-tickets/raise":"staff-tickets","/staff/service-tickets/reports":"staff-service-reports","/staff/service-tickets/queue":"staff-service-queue","/staff/service-center-revenue":"staff-service-revenue"},U=[{menu_code:"HOME",label:"Home",route:"dashboard"},{menu_code:"PROGRESS_DASHBOARD",label:"Progress Dashboard",route:"progress"},{menu_code:"DAY_PLANNER",label:"Day Planner",route:"day-planner"}],V=[{menu_code:"VGK_DASHBOARD",label:'<i class="fas fa-home" style="margin-right: 8px; width: 18px; text-align: center;"></i> Dashboard',route:"vgk-member-hub",tab:"earnings"},{menu_code:"VGK_PROFILE",label:'<i class="fas fa-user" style="margin-right: 8px; width: 18px; text-align: center;"></i> Profile',route:"vgk-member-hub",tab:"profile"},{menu_code:"VGK_MYCARD",label:'<i class="fas fa-id-card" style="margin-right: 8px; width: 18px; text-align: center;"></i> My Card &amp; Progress',route:"vgk-member-hub",tab:"mycard"},{menu_code:"VGK_ADDMEMBER",label:'<i class="fas fa-user-plus" style="margin-right: 8px; width: 18px; text-align: center;"></i> Add Channel Partner',route:"vgk-member-hub",tab:"addmember"},{menu_code:"VGK_COUPONS",label:'<i class="fas fa-ticket-alt" style="margin-right: 8px; width: 18px; text-align: center;"></i> Coupons',route:"vgk-member-hub",tab:"coupons"},{menu_code:"VGK_NETWORK",label:'<i class="fas fa-sitemap" style="margin-right: 8px; width: 18px; text-align: center;"></i> Team',route:"vgk-member-hub",tab:"network"},{menu_code:"VGK_POINTS",label:'<i class="fas fa-coins" style="margin-right: 8px; width: 18px; text-align: center;"></i> Points Balance',route:"vgk-member-hub",tab:"points"},{menu_code:"VGK_LEDGER",label:'<i class="fas fa-rupee-sign" style="margin-right: 8px; width: 18px; text-align: center;"></i> My Earnings',route:"vgk-member-hub",tab:"ledger"},{menu_code:"VGK_LEADS",label:'<i class="fas fa-user-tag" style="margin-right: 8px; width: 18px; text-align: center;"></i> My Leads',route:"vgk-member-hub",tab:"leads"},{menu_code:"VGK_TICKETS",label:'<i class="fas fa-tools" style="margin-right: 8px; width: 18px; text-align: center;"></i> Service Tickets',route:"vgk-member-hub",tab:"tickets"},{menu_code:"VGK_BONANZA",label:'<i class="fas fa-trophy" style="margin-right: 8px; width: 18px; text-align: center;"></i> Bonanza Rewards',route:"vgk-member-hub",tab:"bonanza"},{menu_code:"VGK_VENDORS",label:'<i class="fas fa-store" style="margin-right: 8px; width: 18px; text-align: center;"></i> Vendor Shops',route:"vgk-member-hub",tab:"vendors"},{menu_code:"VGK_MEDIA",label:'<i class="fas fa-photo-video" style="margin-right: 8px; width: 18px; text-align: center;"></i> Media Hub',route:"vgk-member-hub",tab:"media"},{menu_code:"VGK_ORDERS",label:'<i class="fas fa-box" style="margin-right: 8px; width: 18px; text-align: center;"></i> Orders',route:"vgk-member-hub",tab:"orders"}],B=[{section_code:"ATTENDANCE",section_label:"ATTENDANCE",order:1,items:[{menu_code:"IN_OUT_TIME",label:"In/Out Time",route:"attendance"},{menu_code:"MY_LEAVES",label:"My Leaves",route:"leaves"},{menu_code:"LEAVE_APPROVALS",label:"Leave Approvals",route:"staff-leave-approvals"},{menu_code:"IN_OUT_RECORDS_ADMIN",label:"In/Out Records - Admin",route:"team-attendance"},{menu_code:"ATTENDANCE_RECORDS",label:"Attendance Records",route:"staff-attendance-sheet"},{menu_code:"ATTENDANCE_DASHBOARD",label:"Attendance Dashboard",route:"staff-attendance-reports"},{menu_code:"EXCEPTION_APPROVALS",label:"Exception Approvals",route:"staff-attendance-exceptions"},{menu_code:"ATTENDANCE_COMPUTATION",label:"Attendance Computation",route:"staff-attendance-computation"}]},{section_code:"TASK_MANAGEMENT",section_label:"TASK MANAGEMENT",order:3,items:[{menu_code:"ASSIGNED_BY_ME",label:"Assigned By Me",route:"tasks-assigned"},{menu_code:"ASSIGNED_TO_ME",label:"Assigned To Me",route:"tasks-received"},{menu_code:"TEAM_ACTIVITIES",label:"Team Activities",route:"staff-team-activities"},{menu_code:"TASK_TRACKER",label:"Task Dashboard",route:"staff-task-tracker"},{menu_code:"TASK_REVIEWS",label:"Task Reviews",route:"staff-task-reviews"}]},{section_code:"KRA_MANAGEMENT",section_label:"KRA MANAGEMENT",order:4,items:[{menu_code:"MY_KRAS",label:"My KRAs",route:"kras"},{menu_code:"KRA_TEMPLATES",label:"KRA Templates",route:"staff-kra-templates"},{menu_code:"KRA_TRACKING_SHEET",label:"KRA Tracking Sheet",route:"staff-kra-tracking"},{menu_code:"KRA_REVIEW",label:"KRA Review",route:"staff-kra-review"}]},{section_code:"TIMESHEET",section_label:"TIMESHEET",order:5,items:[{menu_code:"MY_TIMESHEET",label:"My Timesheet",route:"timesheet"},{menu_code:"TIMESHEET_APPROVAL",label:"Timesheet Approval",route:"staff-timesheet-approval"}]},{section_code:"JOURNEY_TRACKING",section_label:"JOURNEY TRACKING",order:6,items:[{menu_code:"MY_JOURNEYS",label:"My Journeys",route:"journeys"},{menu_code:"TEAM_JOURNEYS",label:"Team Journeys",route:"team-journeys"},{menu_code:"ALL_JOURNEYS",label:"All Journeys",route:"staff-all-journeys"},{menu_code:"VGK4U_JOURNEYS",label:"VGK4U Journeys",route:"staff-vgk4u-journeys"}]},{section_code:"REIMBURSEMENT",section_label:"REIMBURSEMENT",order:7,items:[{menu_code:"MY_REIMBURSEMENT_CLAIMS",label:"My Reimbursement Claims",route:"reimbursements"},{menu_code:"REIMBURSEMENT_APPROVALS",label:"Reimbursement Approvals",route:"staff-reimbursement-approvals"}]},{section_code:"ACCOUNTS_EARNINGS",section_label:"FINANCE & EARNINGS",order:8,items:[{menu_code:"MY_EARNINGS",label:"My Earnings",route:"staff-my-incentives"},{menu_code:"PAYROLL_PROFILE",label:"Payroll Profile",route:"staff-payroll-profile"},{menu_code:"SALARY_SLIPS",label:"Salary Slips",route:"staff-salary-slips"}]},{section_code:"CRM_MODULE",section_label:"CRM & LEADS",order:4,items:[{menu_code:"MY_CRM_DASHBOARD",label:"CRM Dashboard",route:"staff-crm"},{menu_code:"MY_LEADS",label:"My Leads",route:"staff-my-leads"},{menu_code:"AUTO_DIALER",label:"Auto Dialer",route:"auto-dialer"},{menu_code:"BANK_WISE_LEADS",label:"Field staff leads",route:"staff-bank-wise-leads"},{menu_code:"TEAM_LEADS",label:"Team Leads",route:"staff-team-leads"},{menu_code:"LEADS_MASTER",label:"Staff Leads",route:"staff-leads"},{menu_code:"VGK_TEAM_MEMBERS",label:"VGK Channel Partners",route:"staff-vgk-members"}]},{section_code:"WORKFLOWS",section_label:"WORK FLOWS",order:10,items:[{menu_code:"MNR_BANK_WISE_LEADS",label:"Field Sales",route:"staff-bank-wise-leads"},{menu_code:"SOLAR_LEADS",label:"Solar Leads",route:"staff-leads"},{menu_code:"ZYN_REAL_ESTATE",label:"Real Dreams Leads",route:"zynova-real-estate"},{menu_code:"EV_B2B_LEADS",label:"EV B2B Leads",route:"staff-leads"},{menu_code:"EV_B2C_LEADS",label:"EV B2C Leads",route:"staff-leads"},{menu_code:"EV_SPARES_LEADS",label:"EV Spares Leads",route:"staff-leads"},{menu_code:"ZYN_INSURANCE",label:"Insurance Leads",route:"zynova-insurance"},{menu_code:"ETC_LEADS",label:"ETC Leads",route:"staff-training-videos"},{menu_code:"MNR_LEADS",label:"MNR Leads",route:"staff-leads"},{menu_code:"EXECUTIVE_DASHBOARD",label:"Executive Dashboard",route:"dashboard"},{menu_code:"CATEGORY_LEADS_MASTER",label:"Category Leads Master",route:"staff-leads"}]},{section_code:"OPERATIONS",section_label:"OPERATIONS",order:11,items:[{menu_code:"CALL_TRACKING",label:"Call Tracking",route:"staff-call-tracking"},{menu_code:"VENDORS",label:"Vendors",route:"staff-vendors"},{menu_code:"ZYN",label:"Zynova Real Estate",route:"zynova-real-estate"},{menu_code:"ZYNOVA",label:"VGK4U",route:"staff-zynova"},{menu_code:"ZYN_INSURANCE",label:"Zynova Insurance",route:"zynova-insurance"}]}],z=[];class H{container=null;overlay=null;isOpen=!1;expandedSections=new Set;staffMenuTree=null;isStaffMenuLoaded=!1;constructor(){try{const e=localStorage.getItem("mnr_staff_menu_tree_cache");e&&(this.staffMenuTree=JSON.parse(e),this.isStaffMenuLoaded=!0)}catch{}this.createElements(),this.loadStaffMenus(),window.addEventListener("logout",()=>{this.staffMenuTree=null,this.isStaffMenuLoaded=!1;try{localStorage.removeItem("mnr_staff_menu_tree_cache")}catch{}this.updateUI()}),window.addEventListener("auth-changed",()=>{this.isStaffMenuLoaded=!1,this.loadStaffMenus()})}createElements(){if(this.overlay=document.createElement("div"),this.overlay.className="drawer-overlay",this.overlay.addEventListener("click",()=>this.close()),document.body.appendChild(this.overlay),this.container=document.createElement("div"),this.container.className="side-drawer",this.container.innerHTML=this.render(),document.body.appendChild(this.container),!document.getElementById("myntos-drawer-styles")){const e=document.createElement("style");e.id="myntos-drawer-styles",e.textContent=`
        .side-drawer { position: fixed; top: 0; left: 0; width: 290px; height: 100vh; background: #0f172a; color: #fff; z-index: 9999; transform: translateX(-100%); transition: transform 0.25s ease-in-out; will-change: transform; overflow-y: auto; box-shadow: 2px 0 16px rgba(0,0,0,0.5); }
        .side-drawer.open { transform: translateX(0); }
        .drawer-overlay { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(0,0,0,0.6); z-index: 9998; opacity: 0; pointer-events: none; transition: opacity 0.25s ease-in-out; will-change: opacity; }
        .drawer-overlay.visible { opacity: 1; pointer-events: auto; }
        .drawer-header { display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; border-bottom: 1px solid rgba(255,255,255,0.08); }
        .drawer-logo .logo-text { font-size: 1.1rem; font-weight: 700; color: #38bdf8; }
        .drawer-close { background: none; border: none; color: #94a3b8; cursor: pointer; padding: 4px; }
        .drawer-content { padding: 10px 0 40px; }
        .top-menu-items { border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 8px; margin-bottom: 8px; }
        .menu-item.top-item { display: flex; align-items: center; padding: 10px 20px; font-size: 13.5px; font-weight: 600; color: #f1f5f9; cursor: pointer; transition: background 0.15s; }
        .menu-item.top-item:active { background: rgba(59,130,246,0.2); color: #38bdf8; }
        .drawer-section { border-bottom: 1px solid rgba(255,255,255,0.05); }
        .section-header { display: flex; justify-content: space-between; align-items: center; padding: 13px 20px; font-size: 12.5px; font-weight: 700; color: #94a3b8; letter-spacing: 0.5px; cursor: pointer; user-select: none; }
        .section-header:active { background: rgba(255,255,255,0.05); color: #fff; }
        .section-arrow { transition: transform 0.2s; }
        .drawer-subsection { padding-left: 8px; border-left: 2px solid rgba(255,255,255,0.05); margin-left: 16px; margin-bottom: 4px; }
        .subsection-header { display: flex; justify-content: space-between; align-items: center; padding: 9px 16px; font-size: 12px; font-weight: 600; color: #cbd5e1; cursor: pointer; }
        .drawer-menu-item { display: flex; align-items: center; padding: 9px 24px; font-size: 13px; color: #e2e8f0; text-decoration: none; cursor: pointer; transition: background 0.15s; }
        .drawer-menu-item:active { background: rgba(59,130,246,0.2); color: #38bdf8; }
        .drawer-menu-item .menu-label { display: flex; align-items: center; }
        .drawer-menu-item .menu-label i { font-size: 14px; margin-right: 10px; width: 18px; text-align: center; color: #38bdf8; }
      `,document.head.appendChild(e)}this.attachEventListeners()}render(){const e=M.getPortal(),t=e==="vgk",n=v.getAuthState().user||{},i=(n.role_code||n.role?.role_code||n.user_type||"").toString().toLowerCase().trim(),o=(n.role_name||n.role?.role_name||"").toString().toUpperCase().trim(),p=(n.staff_type||"").toString().toUpperCase().trim(),s=["vgk4u","vgk4u_supreme","key_leadership","ea","executive_admin","manager","director","admin"].includes(i)||i.includes("vgk")||i.includes("manager")||i.includes("lead")||["VGK4U","VGK4U SUPREME","VGK MENTOR","KEY LEADERSHIP","EA","EXECUTIVE ADMIN","MANAGER"].includes(o)||o.includes("VGK")||o.includes("MANAGER")||["VGK4U","VGK4U SUPREME"].includes(p)||!!(n.is_manager||n.is_admin||n.is_super_admin);let r=U;if(t)r=V;else if(e==="staff"){const u=["vgk4u","vgk4u_supreme","key_leadership","ea","executive_admin"].includes(i)||i.includes("vgk")||["VGK4U","VGK4U SUPREME","VGK MENTOR","KEY LEADERSHIP","EA","EXECUTIVE ADMIN"].includes(o)||o.includes("VGK")||["VGK4U","VGK4U SUPREME"].includes(p);n.staff_type==="FREELANCER"&&n.freelancer_access_mode==="only_leads"?r=[]:r=[{menu_code:"PROGRESS",label:'<i class="fas fa-chart-line" style="margin-right: 8px; width: 18px; text-align: center;"></i> Progress',route:"progress"},...u?[{menu_code:"OVERVIEW",label:'<i class="fas fa-th" style="margin-right: 8px; width: 18px; text-align: center;"></i> Overview',route:"dashboard"}]:[],{menu_code:"TASK_PLANNER",label:'<i class="fas fa-calendar-day" style="margin-right: 8px; width: 18px; text-align: center;"></i> Task Planner',route:"day-planner"},{menu_code:"KRA_STATUS",label:'<i class="fas fa-chart-bar" style="margin-right: 8px; width: 18px; text-align: center;"></i> KRA Status',route:"kras"},{menu_code:"TIME_SHEET",label:'<i class="fas fa-clock" style="margin-right: 8px; width: 18px; text-align: center;"></i> Time Sheet',route:"timesheet"},{menu_code:"WHATSAPP_CENTER",label:'<i class="fab fa-whatsapp" style="margin-right: 8px; width: 18px; text-align: center; color: #25d366;"></i> WhatsApp Center',route:"staff-whatsapp"},{menu_code:"CALLING_PAGE",label:'<i class="fas fa-phone-alt" style="margin-right: 8px; width: 18px; text-align: center; color: #3b82f6;"></i> Calling Page',route:"softphone"},{menu_code:"AUTO_DIALER",label:'<i class="fas fa-phone-volume" style="margin-right: 8px; width: 18px; text-align: center; color: #38bdf8;"></i> Auto Dialer',route:"auto-dialer"}]}const d=["account","accounts","finance","payroll","billing","bookkeeper","auditor"].some(u=>i.includes(u))||["ACCOUNT","ACCOUNTS","FINANCE","PAYROLL","BILLING","BOOKKEEPER","AUDITOR"].some(u=>o.includes(u))||["ACCOUNT","ACCOUNTS","FINANCE","PAYROLL","BILLING","BOOKKEEPER","AUDITOR"].some(u=>p.includes(u))||["ACCOUNT","ACCOUNTS","FINANCE","PAYROLL"].some(u=>(n.department||n.department_name||"").toString().toUpperCase().includes(u)),l=s||d,c=t?z:e==="staff"?this.getStaffMenuMaster():B,f=e==="staff"?this.filterMenusForRole(c,s,l):c;return`
      <div class="drawer-header">
        <div class="drawer-logo">
          <span class="logo-text">WORKFLOWS</span>
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
          ${r.map(u=>`
            <div class="menu-item top-item" data-route="${u.route}" ${u.tab?`data-tab="${u.tab}"`:""}>
              <span class="menu-label">${u.label}</span>
            </div>
          `).join("")}
        </div>
        <!-- Section menus -->
        ${f.map(u=>this.renderSection(u)).join("")}
        
        ${t?`
          <div class="drawer-divider" style="height: 1px; background: rgba(255,255,255,0.1); margin: 12px 16px;"></div>
          <div class="menu-item top-item logout-item" id="drawerLogout" style="color: #ef4444; cursor: pointer; display: flex; align-items: center; padding: 12px 24px;">
            <span class="menu-label" style="display: flex; align-items: center; gap: 8px; font-weight: 500; font-size: 1rem;">
              <i class="fas fa-sign-out-alt" style="width: 18px; text-align: center;"></i> Logout
            </span>
          </div>
        `:""}
      </div>
    `}renderSection(e){const t=this.expandedSections.has(e.section_code),a=e.subSections&&e.subSections.length>0,n=e.items&&e.items.length>0;return!a&&!n?"":`
      <div class="drawer-section" data-section="${e.section_code}">
        <div class="section-header" data-toggle="${e.section_code}">
          <span class="section-title">${e.section_label}</span>
          <svg class="section-arrow" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">${t?'<polyline points="6 9 12 15 18 9"/>':'<polyline points="9 18 15 12 9 6"/>'}</svg>
        </div>
        <div class="section-items ${t?"expanded":""}" style="display: ${t?"block":"none"};">
          ${n?e.items.map(i=>this.renderMenuItem(i)).join(""):""}
          ${a?e.subSections.map(i=>this.renderSubSection(i)).join(""):""}
        </div>
      </div>
    `}renderSubSection(e){const t=this.expandedSections.has(e.sub_section_code);return`
      <div class="drawer-subsection">
        <div class="subsection-header" data-toggle="${e.sub_section_code}">
          <span class="subsection-title">${e.sub_section_label}</span>
          <svg class="section-arrow" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">${t?'<polyline points="6 9 12 15 18 9"/>':'<polyline points="9 18 15 12 9 6"/>'}</svg>
        </div>
        <div class="subsection-items ${t?"expanded":""}" style="display: ${t?"block":"none"};">
          ${e.items.map(a=>this.renderMenuItem(a)).join("")}
        </div>
      </div>
    `}renderMenuItem(e){return`
      <a class="drawer-menu-item" data-route="${e.route}">
        <span class="menu-label">${e.label}</span>
      </a>
    `}attachEventListeners(){this.container&&(document.getElementById("drawerClose")?.addEventListener("click",()=>this.close()),this.container.querySelectorAll("[data-toggle]").forEach(e=>{e.addEventListener("click",t=>{const a=e.dataset.toggle;this.toggleSection(a),t.stopPropagation()})}),this.container.querySelectorAll("[data-route]").forEach(e=>{e.addEventListener("click",()=>{const t=e.dataset.route,a=e.dataset.tab;a?w.navigate(t,{tab:a}):w.navigate(t),this.close()})}),document.getElementById("drawerLogout")?.addEventListener("click",async()=>{this.close(),confirm("Are you sure you want to logout?")&&await v.logout()}))}toggleSection(e){this.expandedSections.has(e)?this.expandedSections.delete(e):this.expandedSections.add(e),this.updateUI()}updateUI(){this.container&&(this.container.innerHTML=this.render(),this.attachEventListeners())}async loadStaffMenus(){try{const e=await _.get("/staff/menu-settings/my-menus?unified=true");if(e.success&&e.data&&e.data.sidebar_tree){this.staffMenuTree=e.data.sidebar_tree,this.isStaffMenuLoaded=!0;try{localStorage.setItem("mnr_staff_menu_tree_cache",JSON.stringify(this.staffMenuTree))}catch{}this.updateUI()}}catch(e){console.error("Failed to load dynamic staff menus:",e)}}filterMenusForRole(e,t,a=!1){const i=v.getAuthState().user||{},o=(i.emp_code||i.employee_code||"").toString().toUpperCase().trim(),p=["MN10009","MR10022","MR10036","MR10027","MN10017","MN10016"].includes(o);if(t&&!p)return e;const s=new Set(["SAAS","SAAS_MANAGEMENT","SAAS CONFIGURATION","CONFIGURATION","SYSTEM_CONFIGURATION","SYSTEM CONFIG","META_ADS","META ADS","VENDOR_MANAGEMENT","VENDOR MANAGEMENT","VENDORS","HR","HR_MANAGEMENT","ZYNOVA","ZYNOVA_REAL_ESTATE","MNR","MNR_USER_SIDEBAR","MNR USER SIDEBAR","MNR_USER","MNR USER"]);a||(s.add("ACCOUNTS"),s.add("ACCOUNTS_EARNINGS"),s.add("ACCOUNTS & EARNINGS"),s.add("FINANCE"),s.add("FINANCE & EARNINGS"),s.add("FINANCE_EARNINGS"),s.add("ACCOUNTS_MANAGEMENT"));const r=new Set(["EXECUTIVE_DASHBOARD","CATEGORY_LEADS_MASTER","SAAS_CONFIG","SYSTEM_CONFIG"]);(!t||p)&&(r.add("LEADS_MASTER"),r.add("STAFF_LEADS"),r.add("staff_leads")),a||(r.add("PAYROLL_PROFILE"),r.add("SALARY_SLIPS"),r.add("EXPENSE_ENTRIES"));const d=[];for(const l of e){const c=(l.section_code||"").toUpperCase().trim(),f=(l.section_label||"").toUpperCase().trim();if(s.has(c)||s.has(f))continue;let u=l.items;u&&u.length>0&&(u=u.filter(b=>{const S=(b.menu_code||"").toUpperCase().trim();return!r.has(S)}));let h=l.subSections;h&&h.length>0&&(h=h.map(b=>({...b,items:b.items.filter(S=>{const k=(S.menu_code||"").toUpperCase().trim();return!r.has(k)})})).filter(b=>b.items.length>0));const m=u&&u.length>0,g=h&&h.length>0;(m||g)&&d.push({...l,items:m?u:void 0,subSections:g?h:void 0})}return d}getStaffMenuMaster(){if(!this.staffMenuTree)return B;const e={EXECUTIVE_DASHBOARD:1,staff_executive_dashboard:1,mnr_executive_dashboard:1,MNR_BANK_WISE_LEADS:2,BANK_WISE_LEADS:2,staff_bank_wise_leads:2,CATEGORY_LEADS_MASTER:3,mnr_leads_master:3,staff_mnr_leads_master:3,SOLAR_LEADS:4,staff_solar_leads:4,mnr_solar_leads:4,EV_B2B_LEADS:5,staff_ev_b2b_leads:5,mnr_ev_b2b_leads:5,EV_B2C_LEADS:6,staff_ev_b2c_leads:6,mnr_ev_b2c_leads:6,EV_SPARES_LEADS:7,staff_ev_spares_leads:7,mnr_ev_spares_leads:7,ZYN_REAL_ESTATE:8,staff_real_dreams_leads:8,mnr_real_dreams_leads:8,ZYN_INSURANCE:9,staff_insurance_leads:9,mnr_insurance_leads:9,ETC_LEADS:10,staff_etc_leads:10,mnr_etc_leads:10,MNR_LEADS:11,staff_mnr_leads:11,mnr_category_leads:11,AUTO_DIALER:12,staff_auto_dialer:12,"auto-dialer":12},t={MY_CRM_DASHBOARD:1,staff_crm_dashboard:1,"staff-crm":1,MY_LEADS:2,staff_my_leads:2,"staff-my-leads":2,AUTO_DIALER:3,staff_auto_dialer:3,"auto-dialer":3,BANK_WISE_LEADS:4,staff_bank_wise_leads:4,"staff-bank-wise-leads":4,TEAM_LEADS:5,staff_team_leads:5,"staff-team-leads":5,WHATSAPP_CENTER:6,staff_crm_whatsapp_inbox:6,"staff-whatsapp":6,CALL_TRACKING:7,call_tracking_dashboard:7,"staff-call-tracking":7,OPERATOR_CALLS:8,staff_operator_calls:8,"operator-calls":8,VGK_TEAM_MEMBERS:9,staff_vgk_members:9,"staff-vgk-members":9,STAFF_LEADS:10,staff_leads:10,LEADS_MASTER:10,leads_master:10},a=new Map,n=[],i=(s,r,d,l)=>{const c=P[d]||P[d?.replace(/\/$/,"")]||(d?d.replace(/^\/staff\//,"").replace(/\//g,"-"):null);if(!c)return null;const u=v.getAuthState().user||{},h=(u.emp_code||u.employee_code||"").toString().toUpperCase().trim();if(["MN10009","MR10022","MR10036","MR10027","MN10017","MN10016"].includes(h)&&(c==="staff-leads"||d&&d.toLowerCase()==="/staff/leads"||s&&["staff_leads","STAFF_LEADS","LEADS_MASTER","staff_leads_master"].includes(s)))return null;let m=r;(!m||m==="None"||m.trim()==="")&&(m=(s||"").replace(/^staff_|^_staff_|^mnr_/i,"").replace(/_/g," ").replace(/\b\w/g,C=>C.toUpperCase()));const g=(s||"").toUpperCase(),b=(d||"").toLowerCase();g.includes("AUTO_DIALER")||b.includes("auto-dialer")||b==="/staff/dialer"||g==="STAFF_AUTO_DIALER"||g==="AUTO_DIALER"?m="Auto Dialer":g.includes("BANK_WISE_LEADS")||b.includes("bank-wise-leads")?m="Field staff leads":g.includes("REAL_DREAMS")||b.includes("real-dreams-leads")?m="Real Dreams Leads":g.includes("ETC_LEADS")||b.includes("etc-leads")?m="ETC Training Students":g.includes("CATEGORY_LEADS_MASTER")||g.includes("MNR_LEADS_MASTER")||b.includes("mnr-leads-master")?m="Category Lead Master":g.includes("WHATSAPP")||b.includes("whatsapp")?m="WhatsApp Center":g.includes("SOFTPHONE")||g==="PHONE_DIALPAD"||b.includes("softphone")||b.includes("calling")||b.includes("phone-dialpad")?m="Calling & Softphone":(g.includes("VGK_TEAM_MEMBERS")||g==="STAFF_VGK_MEMBERS"||b.includes("vgk/members"))&&(m="VGK Channel Partners");const S=l||(m.includes("WhatsApp")?"fab fa-whatsapp":m.includes("Auto Dialer")?"fas fa-phone-volume":m.includes("Softphone")||m.includes("Calling")?"fas fa-headset":m.includes("VGK")||m.includes("Channel")?"fas fa-users":m.includes("Field")?"fas fa-users-gear":"fas fa-file-alt"),k=m.includes("WhatsApp")?"color: #25d366;":m.includes("Auto Dialer")||m.includes("Softphone")||m.includes("Calling")?"color: #38bdf8;":m.includes("VGK")||m.includes("Channel")?"color: #7c3aed;":"",A=`<i class="${S}" style="margin-right: 8px; width: 18px; text-align: center; ${k}"></i>`;return{menu_code:s,label:`${A}${m}`,route:c}};for(const s of this.staffMenuTree){if(s.id==="progress"||s.section_id==="progress"||(s.title||"").toUpperCase()==="PROGRESS")continue;const r=[],d=[];if(s.items)for(const l of s.items){const c=i(l.menu_code,l.menu_name||l.label||l.name||l.title,l.route_path,l.menu_icon);c&&r.push(c)}if(s.subSections)for(const l of s.subSections){const c=[];if(l.items)for(const u of l.items){const h=i(u.menu_code,u.menu_name||u.label||u.name||u.title,u.route_path,u.menu_icon);h&&c.push(h)}let f=l.title||l.name||l.id||"Subsection";(f==="None"||!f)&&(f=(l.id||"").replace(/^staff_|^vm_/i,"").replace(/_/g," ").replace(/\b\w/g,u=>u.toUpperCase())),c.length>0&&d.push({sub_section_code:l.id||l.section_id||"sub",sub_section_label:f,items:c})}if(r.length>0||d.length>0){let l=(s.id||s.section_id||"other").toString().trim(),c=(s.title||s.name||"Other").toString().trim();(c==="None"||!c)&&(c=l.replace(/_/g," ").replace(/\b\w/g,h=>h.toUpperCase()));const f=l.toLowerCase(),u=c.toUpperCase();if((f==="mynt_real"||f==="myntreal"||f==="workflows"||u==="MYNT REAL"||u==="MYNTREAL"||u==="WORK FLOWS"||u==="WORKFLOWS")&&(l="WORKFLOWS",c="WORK FLOWS"),(f==="crm"||f==="crm_module"||f==="crm_leads"||f==="crm & leads"||u.includes("CRM"))&&(l="CRM_MODULE",c="CRM & LEADS"),a.has(l)){const h=a.get(l);if(r.length>0){h.items=h.items||[];const m=new Set(h.items.map(g=>g.menu_code));for(const g of r)m.has(g.menu_code)||(h.items.push(g),m.add(g.menu_code))}d.length>0&&(h.subSections=h.subSections||[],h.subSections.push(...d))}else n.push(l),a.set(l,{section_code:l,section_label:c,order:l==="CRM_MODULE"?4:s.order!==void 0?s.order:999,items:r.length>0?r:void 0,subSections:d.length>0?d:void 0})}}let o=a.get("CRM_MODULE")||a.get("CRM_LEADS")||a.get("crm")||a.get("CRM");o||(o={section_code:"CRM_MODULE",section_label:"CRM & LEADS",order:4,items:[]},a.set("CRM_MODULE",o),n.push("CRM_MODULE")),o&&(o.items=o.items||[],o.items.some(r=>r.route==="auto-dialer"||r.menu_code&&r.menu_code.toUpperCase().includes("AUTO_DIALER"))||o.items.push({menu_code:"AUTO_DIALER",label:'<i class="fas fa-phone-volume" style="margin-right: 8px; width: 18px; text-align: center; color: #38bdf8;"></i>Auto Dialer',route:"auto-dialer"}));const p=n.map(s=>a.get(s));p.sort((s,r)=>s.order-r.order);for(const s of p)s.section_code==="WORKFLOWS"&&s.items&&s.items.sort((r,d)=>(e[r.menu_code]||99)-(e[d.menu_code]||99)),s.section_code==="CRM_MODULE"&&s.items&&s.items.sort((r,d)=>(t[r.menu_code]||t[r.route]||99)-(t[d.menu_code]||t[d.route]||99));return p}open(){if(this.isOpen)return;M.getPortal()==="staff"&&!this.isStaffMenuLoaded&&this.loadStaffMenus(),this.updateUI(),this.isOpen=!0,this.container?.classList.add("open"),this.overlay?.classList.add("visible"),document.body.style.overflow="hidden"}close(){this.isOpen&&(this.isOpen=!1,this.container?.classList.remove("open"),this.overlay?.classList.remove("visible"),document.body.style.overflow="")}toggle(){this.isOpen?this.close():this.open()}}let I=null;function G(){return I||(I=new H),I}class T{static render(e){let{title:t,showBack:a=!1,showLogout:n=!1,rightAction:i,subtitle:o,showMenu:p}=e;const s=M.getPortal(),r=w.getCurrentRoute(),d=["progress","dashboard","attendance","journeys","announcements","profile","mnr-dashboard","partner-dashboard","vgk-member-hub"].includes(r);if(p===void 0&&(p=d||!a),s==="vgk"&&(n=!0,!o)){const c=v.getAuthState().user||{},f=c.name||c.partner_name||"",u=c.partner_code||"";(f||u)&&(o=u?`${f} (${u})`:f)}return`
      <header class="page-header" style="display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; background: #0f172a; border-bottom: 1px solid #1e293b; position: sticky; top: 0; z-index: 100;">
        <div class="header-left" style="display: flex; align-items: center; gap: 10px;">
          ${p?`
            <button class="header-btn hamburger-btn" id="hamburgerBtn" title="Open Navigation Menu" style="width: 36px; height: 36px; display: flex; align-items: center; justify-content: center; background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.15); color: #fff; border-radius: 8px; cursor: pointer; flex-shrink: 0; touch-action: manipulation; -webkit-tap-highlight-color: transparent;">
              <svg style="pointer-events: none;" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="3" y1="12" x2="21" y2="12"/>
                <line x1="3" y1="6" x2="21" y2="6"/>
                <line x1="3" y1="18" x2="21" y2="18"/>
              </svg>
            </button>
          `:""}
          ${a?`
            <button class="header-btn back-btn" id="backBtn" title="Back" style="width: 36px; height: 36px; display: flex; align-items: center; justify-content: center; background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.15); color: #fff; border-radius: 8px; cursor: pointer; flex-shrink: 0; touch-action: manipulation; -webkit-tap-highlight-color: transparent;">
              <svg style="pointer-events: none;" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="15 18 9 12 15 6"/>
              </svg>
            </button>
          `:""}
          <div class="header-title-wrapper" style="display:flex; flex-direction:column; gap:2px">
            <h1 class="header-title" style="margin:0; font-size:16px; font-weight:700; color:#fff;">${t}</h1>
            ${o?`<span class="header-subtitle" style="font-size:11px; color:rgba(255,255,255,0.65); font-weight:500">${o}</span>`:""}
          </div>
        </div>
        <div class="header-right">
          ${i?`
            <button class="header-btn action-btn" id="headerActionBtn">
              ${i.icon}
            </button>
          `:""}
          ${n?`
            <button class="header-btn logout-btn" id="logoutBtn" style="padding: 6px; display: flex; align-items: center; justify-content: center;">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
                <polyline points="16 17 21 12 16 7"/>
                <line x1="21" y1="12" x2="9" y2="12"/>
              </svg>
            </button>
          `:""}
        </div>
      </header>
    `}static getPortalDashboard(){const e=M.getPortal();return e==="mnr"?"mnr-dashboard":e==="partner"?"partner-dashboard":e==="vgk"?"vgk-member-hub":"progress"}static attachListeners(e){let{showMenu:t,showBack:a=!1,rightAction:n,showLogout:i=!1}=e;t===void 0&&(t=!!document.getElementById("hamburgerBtn")),M.getPortal()==="vgk"&&(i=!0),t&&document.getElementById("hamburgerBtn")?.addEventListener("click",()=>{G().open()}),a&&document.getElementById("backBtn")?.addEventListener("click",()=>{w.goBack()||w.navigate(T.getPortalDashboard())}),n&&document.getElementById("headerActionBtn")?.addEventListener("click",n.onClick),i&&document.getElementById("logoutBtn")?.addEventListener("click",async()=>{confirm("Are you sure you want to logout?")&&await v.logout()})}static attachBackHandler(){document.getElementById("backBtn")?.addEventListener("click",()=>{w.goBack()||w.navigate(T.getPortalDashboard())})}}class se{constructor(e){this.options=e,this.trackPoints=e.trackPoints,this.stops=e.stops||[],this.onViewChange=e.onViewChange}options;map=null;container=null;trackPoints=[];stops=[];routeLine=null;progressLine=null;currentMarker=null;startMarker=null;endMarker=null;stopMarkers=[];currentView="street";tileLayers={};playbackIndex=0;isPlaying=!1;playbackInterval=null;playbackSpeed=2;onViewChange;addressCache=new Map;mount(){if(this.container=document.getElementById(this.options.containerId),!this.container){console.error("[LeafletMap] Container not found:",this.options.containerId);return}this.render(),this.initMap()}render(){this.container&&(this.container.innerHTML=`
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
    `,this.addStyles(),this.attachEventListeners())}initMap(){if(this.trackPoints.length===0||!document.getElementById("leafletMapView"))return;const t=this.trackPoints[0];this.map=x.map("leafletMapView",{zoomControl:!1,attributionControl:!1}).setView([t.latitude,t.longitude],14),x.control.zoom({position:"topright"}).addTo(this.map),this.tileLayers={street:x.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",{maxZoom:19}),satellite:x.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",{maxZoom:19}),terrain:x.tileLayer("https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",{maxZoom:17})},this.tileLayers.street.addTo(this.map),this.drawRoute(),this.fitBounds()}drawRoute(){if(!this.map||this.trackPoints.length<2)return;const e=this.trackPoints.map(s=>[s.latitude,s.longitude]);this.routeLine=x.polyline(e,{color:"rgba(255,255,255,0.3)",weight:4,dashArray:"8, 8"}).addTo(this.map),this.progressLine=x.polyline([],{color:"#00d09c",weight:5,lineCap:"round",lineJoin:"round"}).addTo(this.map);const t=x.divIcon({className:"custom-marker start-marker",html:'<div class="marker-inner">S</div>',iconSize:[28,28],iconAnchor:[14,14]}),a=x.divIcon({className:"custom-marker end-marker",html:'<div class="marker-inner">E</div>',iconSize:[28,28],iconAnchor:[14,14]}),n=this.trackPoints[0],i=n.battery_percentage!==void 0?`<br>🔋 ${n.battery_percentage}%`:"";this.startMarker=x.marker([n.latitude,n.longitude],{icon:t}).bindPopup(`<b>Start Point</b><br>${n.address||"Journey Start"}${i}`).addTo(this.map);const o=this.trackPoints[this.trackPoints.length-1],p=o.battery_percentage!==void 0?`<br>🔋 ${o.battery_percentage}%`:"";this.endMarker=x.marker([o.latitude,o.longitude],{icon:a}).bindPopup(`<b>End Point</b><br>${o.address||"Journey End"}${p}`).addTo(this.map),this.stops.forEach((s,r)=>{const d=this.trackPoints[s.startIndex];if(d){const l=x.divIcon({className:"custom-marker stop-marker",html:`<div class="marker-inner">${r+1}</div>`,iconSize:[24,24],iconAnchor:[12,12]}),c=x.marker([d.latitude,d.longitude],{icon:l}).bindPopup(`<b>Stop ${r+1}</b><br>${s.address||"Unknown location"}<br>Duration: ${this.formatDuration(s.durationMinutes)}`).addTo(this.map);this.stopMarkers.push(c)}}),this.currentMarker=x.circleMarker([n.latitude,n.longitude],{radius:10,color:"#fff",weight:3,fillColor:"#ffc107",fillOpacity:1}).addTo(this.map)}fitBounds(){!this.map||!this.routeLine||this.map.fitBounds(this.routeLine.getBounds(),{padding:[30,30]})}switchView(e){!this.map||this.currentView===e||(this.tileLayers[this.currentView].remove(),this.tileLayers[e].addTo(this.map),this.currentView=e,document.querySelectorAll(".view-btn").forEach(t=>{t.classList.toggle("active",t.getAttribute("data-view")===e)}),this.onViewChange&&this.onViewChange(e))}attachEventListeners(){document.querySelectorAll(".view-btn").forEach(t=>{t.addEventListener("click",()=>{const a=t.getAttribute("data-view");this.switchView(a)})}),document.getElementById("playPauseBtn")?.addEventListener("click",()=>this.togglePlayback()),document.getElementById("resetPlayback")?.addEventListener("click",()=>this.resetPlayback());const e=document.getElementById("playbackSlider");e?.addEventListener("input",()=>{this.playbackIndex=parseInt(e.value),this.updatePlaybackUI()}),document.getElementById("speedBtn")?.addEventListener("click",()=>this.cycleSpeed())}togglePlayback(){const e=document.getElementById("playPauseBtn");this.isPlaying?(this.stopPlayback(),e&&(e.innerHTML='<svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>',e.classList.remove("pause"),e.classList.add("play"))):(this.startPlayback(),e&&(e.innerHTML='<svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg>',e.classList.remove("play"),e.classList.add("pause"))),this.isPlaying=!this.isPlaying}startPlayback(){const e=500/this.playbackSpeed;this.playbackInterval=setInterval(()=>{if(this.playbackIndex<this.trackPoints.length-1)this.playbackIndex++,this.updatePlaybackUI();else{this.stopPlayback(),this.isPlaying=!1;const t=document.getElementById("playPauseBtn");t&&(t.innerHTML='<svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>',t.classList.remove("pause"),t.classList.add("play"))}},e)}stopPlayback(){this.playbackInterval&&(clearInterval(this.playbackInterval),this.playbackInterval=null)}resetPlayback(){this.stopPlayback(),this.playbackIndex=0,this.isPlaying=!1;const e=document.getElementById("playPauseBtn");e&&(e.innerHTML='<svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>',e.classList.remove("pause"),e.classList.add("play")),this.updatePlaybackUI()}cycleSpeed(){const e=[1,2,4,8],t=e.indexOf(this.playbackSpeed);this.playbackSpeed=e[(t+1)%e.length];const a=document.getElementById("speedBtn");a&&(a.textContent=`${this.playbackSpeed}x`),this.isPlaying&&(this.stopPlayback(),this.startPlayback())}updatePlaybackUI(){const e=document.getElementById("playbackSlider"),t=document.getElementById("playbackCounter"),a=document.getElementById("currentLocation"),n=document.getElementById("sliderProgress");e&&(e.value=String(this.playbackIndex)),t&&(t.textContent=`${this.playbackIndex+1} / ${this.trackPoints.length}`);const i=this.trackPoints[this.playbackIndex];a&&i&&(i.address?a.textContent=i.address:(a.textContent="Loading...",this.reverseGeocodeForPlayback(i.latitude,i.longitude,a)));const o=this.playbackIndex/(this.trackPoints.length-1)*100;if(n&&(n.style.width=`${o}%`),this.currentMarker&&i&&this.currentMarker.setLatLng([i.latitude,i.longitude]),this.progressLine){const p=this.trackPoints.slice(0,this.playbackIndex+1).map(s=>[s.latitude,s.longitude]);this.progressLine.setLatLngs(p)}this.map&&i&&this.map.panTo([i.latitude,i.longitude],{animate:!0,duration:.3})}async reverseGeocodeForPlayback(e,t,a){const n=`${e.toFixed(4)},${t.toFixed(4)}`;if(this.addressCache.has(n)){a.textContent=this.addressCache.get(n);return}try{const i=`https://nominatim.openstreetmap.org/reverse?format=json&lat=${e}&lon=${t}&zoom=18`,o=await fetch(i,{headers:{"User-Agent":"MyntReal-Mobile/1.0"}});if(o.ok){const s=(await o.json()).address||{},r=[];for(const l of["road","neighbourhood","suburb","city","town","village"])if(s[l]&&(r.push(s[l]),r.length>=2))break;const d=r.length>0?r.join(", "):`${e.toFixed(4)}, ${t.toFixed(4)}`;this.addressCache.set(n,d),a.textContent==="Loading..."&&(a.textContent=d)}}catch(i){console.warn("[DC_GEOCODE] Playback geocode failed:",i),a.textContent==="Loading..."&&(a.textContent=`${e.toFixed(4)}, ${t.toFixed(4)}`)}}formatDuration(e){if(e<60)return`${Math.round(e)}m`;const t=Math.floor(e/60),a=Math.round(e%60);return a>0?`${t}h ${a}m`:`${t}h`}addStyles(){if(document.getElementById("leaflet-journey-map-styles"))return;const e=document.createElement("style");e.id="leaflet-journey-map-styles",e.textContent=`
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
    `,document.head.appendChild(e)}setPlaybackIndex(e){e<0||e>=this.trackPoints.length||(this.playbackIndex=e,this.updatePlaybackUI())}getPlaybackState(){return{index:this.playbackIndex,total:this.trackPoints.length,isPlaying:this.isPlaying}}destroy(){this.stopPlayback(),this.map&&(this.map.remove(),this.map=null)}}const R={greeting:{label:"👋 Welcome & Introduction",text:"Namaskaram! Thank you for connecting with MyntReal. I am your dedicated relationship manager. Please let me know how I may assist you with your project today."},bank_update:{label:"🏦 Bank Loan Update",text:"Dear Customer, your bank file is currently under active processing. Our team is following up with the branch for swift approval and sanction."},net_meter:{label:"⚡ Net Meter & EB",text:"Dear Customer, your DISCOM Net Metering and EB service documentation is progressing as scheduled. We will update you once the inspection is cleared."},payment:{label:"💰 Payment / Balance Follow-up",text:"Dear Customer, this is a gentle reminder regarding the pending balance for your project. Kindly arrange the clearance at your earliest convenience."},site_visit:{label:"📍 Location & Site Visit",text:"Dear Customer, our technical field staff is scheduled to visit your site. Kindly let us know if you need to coordinate the visit time."}};class F{modalEl=null;currentOptions=null;activeMode="scanned";canonicalTemplates=[];selectedCanonicalBody="";getSenderSignature(){const t=v.getAuthState().user||{},a=t.full_name||t.name||`${t.first_name||""} ${t.last_name||""}`.trim()||"Staff",n=t.extension||t.ext||(typeof window<"u"?window.__STAFF_EXTENSION__:null);return n&&String(n).trim()&&!["none","null","undefined","n/a"].includes(String(n).trim().toLowerCase())?`

Regards,
${a}
📞 +91 85858 52738 | +91 8897797667
Ext: ${String(n).trim()}`:`

Regards,
${a}
📞 +91 85858 52738 | +91 8897797667`}getVerticalQuickMessage(e){const t=(this.currentOptions?.name||"Customer").trim(),a=(this.currentOptions?.context||"").toLowerCase();let n="general";if(a.includes("solar")?n="solar":a.includes("real")||a.includes("property")||a.includes("estate")?n="real_estate":a.includes("insur")||a.includes("care")?n="insurance":a.includes("ev")||a.includes("spare")||a.includes("zynova")||a.includes("vehicle")?n="ev":(a.includes("etc")||a.includes("train")||a.includes("skill"))&&(n="etc"),e==="thanks_connecting")switch(n){case"solar":return`నమస్కారం ${t} గారు! 🙏 MyntReal Solar Rooftop గురించి మాతో మాట్లాడినందుకు ధన్యవాదాలు. మీ ఇంటి లేదా కమర్షియల్ కరెంట్ బిల్లును 90% వరకు తగ్గించుకుంటూ, Government Subsidy పొందే పూర్తి వివరాలు & Customized Solar Quotation త్వరలోనే మా సోలార్ ఎక్స్‌పర్ట్ మీకు షేర్ చేస్తారు. ఏవైనా డౌట్స్ ఉంటే దయచేసి ఇక్కడ మెసేజ్ చేయండి.`;case"real_estate":return`నమస్కారం ${t} గారు! 🙏 MyntReal Properties తో కనెక్ట్ అయినందుకు ధన్యవాదాలు. మీ బడ్జెట్ మరియు రిక్వైర్‌మెంట్‌కు తగినట్లుగా బెస్ట్ వెరిఫైడ్ ఓపెన్ ప్లాట్స్, గేటెడ్ కమ్యూనిటీ విల్లాస్ మరియు అపార్ట్‌మెంట్స్ వివరాలను మా ప్రాపర్టీ స్పెషలిస్ట్ త్వరలోనే మీకు షేర్ చేస్తారు. సైట్ విజిట్ కోసం ఎప్పుడైనా సంప్రదించవచ్చు.`;case"insurance":return`నమస్కారం ${t} గారు! 🙏 MyntReal Insurance & Protection తో మాట్లాడినందుకు ధన్యవాదాలు. మీకు మరియు మీ కుటుంబానికి సరిపోయే బెస్ట్ Health, Life మరియు General Insurance పాలసీ కొటేషన్లను మా ఇన్సూరెన్స్ అడ్వైజర్ మీకు పంపిస్తారు. పూర్తి క్లెయిమ్ సపోర్ట్ మా బాధ్యత.`;case"ev":return`నమస్కారం ${t} గారు! 🙏 MyntReal EV & Spares గురించి మాతో కనెక్ట్ అయినందుకు ధన్యవాదాలు. లేటెస్ట్ ఎలక్ట్రిక్ వెహికల్ మోడల్స్, రేంజ్, బ్యాటరీ వారంటీ, ఫైనాన్స్ ఆప్షన్స్ మరియు టెస్ట్ రైడ్ వివరాలను మా ఈవీ స్పెషలిస్ట్ మీకు త్వరలోనే అందిస్తారు.`;case"etc":return`నమస్కారం ${t} గారు! 🙏 MyntReal ETC Skill Training ప్రోగ్రామ్స్ గురించి మాట్లాడినందుకు ధన్యవాదాలు. మీ కెరీర్ గ్రోత్‌కు అవసరమైన సర్టిఫైడ్ ట్రైనింగ్ కోర్సులు, బ్యాచ్ టైమింగ్స్ మరియు జాబ్ అసిస్టెన్స్ వివరాలు మా కోఆర్డినేటర్ మీకు పంపిస్తారు.`;default:return`నమస్కారం ${t} గారు! 🙏 MyntReal తో కనెక్ట్ అయినందుకు చాలా ధన్యవాదాలు. మా అన్ని ప్రీమియర్ సర్వీసెస్ మీ సేవలో అందుబాటులో ఉన్నాయి:
☀️ Solar Rooftop & Renewable Energy (కరెంట్ బిల్లు 90% వరకు ఆదా & Govt సబ్సిడీ)
🏡 Real Estate & Premier Properties (ఓపెన్ ప్లాట్స్, విల్లాస్ & అపార్ట్‌మెంట్స్)
🛡️ Insurance & Protection Solutions (హెల్త్, లైఫ్ & జనరల్ పాలసీలు)
🛵 EV Vehicles & Genuine Spares (ఎకో-ఫ్రెండ్లీ ఎలక్ట్రిక్ బైక్స్ & సర్వీస్)
🎓 ETC Skill Training & Career Certifications (ఉద్యోగ నైపుణ్య శిక్షణ)

మా Relationship Manager మీకు పూర్తి వివరాలు అందిస్తారు. మీకు ఏ సమాచారం కావాలన్నా దయచేసి ఇక్కడ మెసేజ్ చేయగలరు!`}else switch(n){case"solar":return`నమస్కారం ${t} గారు! 📞 మీ Solar Rooftop ఎంక్వైరీ కోసం MyntReal నుండి ఇప్పుడే కాల్ చేశాము, కానీ కాల్ కలవలేదు. మీరు ఫ్రీగా ఉన్నప్పుడు దయచేసి ఈ మెసేజ్‌కి రిప్లై ఇవ్వండి లేదా కాల్ బ్యాక్ చేయండి. సోలార్ సబ్సిడీ మరియు సేవింగ్స్ వివరాలు తెలియజేస్తాము.`;case"real_estate":return`నమస్కారం ${t} గారు! 📞 మీ Real Estate ప్రాపర్టీ ఎంక్వైరీ గురించి MyntReal నుండి కాల్ చేశాము, మాట్లాడటం కుదరలేదు. మీకు అనుకూలమైన టైమ్‌లో దయచేసి రిప్లై ఇవ్వండి లేదా కాల్ చేయండి. మీ రిక్వైర్‌మెంట్‌కు సరిపడే బెస్ట్ ప్రాపర్టీ ఆప్షన్స్ మీకు పంపిస్తాము.`;case"insurance":return`నమస్కారం ${t} గారు! 📞 మీ Insurance ఎంక్వైరీ గురించి MyntReal నుండి కాల్ చేశాము, కాల్ కలవలేదు. మీకు ఫ్రీ టైమ్ ఉన్నప్పుడు దయచేసి ఇక్కడ రిప్లై ఇవ్వండి. మీకు అనువైన బెస్ట్ ఇన్సూరెన్స్ ప్లాన్స్ వివరాలు చర్చిద్దాం.`;case"ev":return`నమస్కారం ${t} గారు! 📞 మీ EV Vehicle & Spares ఎంక్వైరీ కోసం MyntReal నుండి కాల్ చేశాము, మాట్లాడటం వీలుపడలేదు. మీరు వీలైనప్పుడు రిప్లై ఇవ్వండి లేదా కాల్ చేయండి. టెస్ట్ రైడ్ మరియు మోడల్స్ వివరాలు మీకు తెలియజేస్తాము.`;case"etc":return`నమస్కారం ${t} గారు! 📞 మీ ETC Skill Training కోర్సు వివరాల కోసం MyntReal నుండి కాల్ చేశాము, కాల్ కనెక్ట్ అవ్వలేదు. మీరు ఫ్రీగా ఉన్నప్పుడు దయచేసి మెసేజ్ చేయండి. అప్‌కమింగ్ బ్యాచ్ టైమింగ్స్ మరియు ఫీజు వివరాలు చర్చిద్దాం.`;default:return`నమస్కారం ${t} గారు! 📞 MyntReal నుండి మీతో మాట్లాడటానికి ఇప్పుడే కాల్ చేశాము, కానీ కాల్ కలవలేదు / మీరు బిజీగా ఉన్నట్లున్నారు. మేము మీకు క్రింది సర్వీసెస్‌లో ఉత్తమ సేవలు అందిస్తున్నాము:
☀️ Solar Energy (సోలార్ రూఫ్‌టాప్ & సబ్సిడీ)
🏡 Real Estate (వెరిఫైడ్ ప్రాపర్టీస్ & సైట్ విజిట్స్)
🛡️ Insurance (హెల్త్ & లైఫ్ ఇన్సూరెన్స్)
🛵 EV Vehicles & Spares (ఎలక్ట్రిక్ స్కూటర్లు & స్పేర్స్)
🎓 ETC Skill Training (నైపుణ్య శిక్షణ & కెరీర్)

మీకు అనుకూలమైన సమయంలో దయచేసి ఇక్కడ మెసేజ్ చేయండి లేదా కాల్ బ్యాక్ చేయగలరు!`}}applyVerticalQuick(e){const t=this.getVerticalQuickMessage(e),a=this.getSenderSignature(),n=document.getElementById("uwaMessageText");n&&(n.value=t+a,n.focus())}async loadCanonicalTemplates(){const e=document.getElementById("uwaCanonicalTpl"),t=document.getElementById("uwaNoTplNotice");if(!e)return;e.innerHTML='<option value="">— Loading templates… —</option>',t&&(t.style.display="none");const a=document.getElementById("uwaCanonicalSeg"),n=document.getElementById("uwaCanonicalCat"),i=a?.value||"",o=n?.value||"",p=this.activeMode==="scanned"?"scanned":"company";let s=`/whatsapp-config/templates?mode=${encodeURIComponent(p)}`;i&&(s+=`&segment=${encodeURIComponent(i)}`),o&&(s+=`&category=${encodeURIComponent(o)}`);try{const r=await _.get(s),d=r?.templates||r?.data||r||[];if(this.canonicalTemplates=Array.isArray(d)?d:[],!this.canonicalTemplates.length){e.innerHTML='<option value="">— No approved templates found —</option>',t&&(t.style.display="block");return}let l=`<option value="">— Select template (${this.canonicalTemplates.length} available) —</option>`;this.canonicalTemplates.forEach(c=>{l+=`<option value="${c.id}">${this.escapeHtml(c.template_name||c.name||"Template #"+c.id)} (${c.category||"MARKETING"})</option>`}),e.innerHTML=l}catch{e.innerHTML='<option value="">— Error loading templates —</option>'}}onCanonicalTplChange(){const e=document.getElementById("uwaCanonicalTpl"),t=document.getElementById("uwaCanonicalVarsWrap"),a=document.getElementById("uwaCanonicalVarsBox"),n=e?.value;if(!n){t&&(t.style.display="none"),a&&(a.innerHTML="");return}const i=this.canonicalTemplates.find(s=>String(s.id)===String(n));if(!i)return;this.selectedCanonicalBody=i.body_text||i.content||i.body||"";const o=this.selectedCanonicalBody.match(/\{\{(\d+)\}\}/g)||[],p=[];if(o.forEach(s=>{const r=s.replace(/[\{\}]/g,"");p.includes(r)||p.push(r)}),p.sort((s,r)=>Number(s)-Number(r)),p.length&&a&&t){t.style.display="block";let s="";p.forEach(r=>{const d=r==="1"&&this.currentOptions?.name||"";s+=`
          <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px;">
            <label style="font-size:11px; font-weight:700; width:28px; color:#475569;">#${r}</label>
            <input type="text" class="uwa-canonical-var-inp" data-var-idx="${r}" value="${this.escapeHtml(d)}" placeholder="Value for {{${r}}}" style="flex:1; font-size:12px; border:1px solid #cbd5e1; border-radius:6px; padding:4px 8px;" />
          </div>
        `}),a.innerHTML=s,a.querySelectorAll(".uwa-canonical-var-inp").forEach(r=>{r.addEventListener("input",()=>this.buildCanonicalPreview())})}else t&&(t.style.display="none"),a&&(a.innerHTML="");this.buildCanonicalPreview()}buildCanonicalPreview(){let e=this.selectedCanonicalBody||"";(e.match(/\{\{(\d+)\}\}/g)||[]).forEach(i=>{const o=i.replace(/[\{\}]/g,""),s=document.querySelector(`.uwa-canonical-var-inp[data-var-idx="${o}"]`)?.value||`{{${o}}}`;e=e.replace(new RegExp(`\\{\\{${o}\\}\\}`,"g"),s)});const a=this.getSenderSignature(),n=document.getElementById("uwaMessageText");n&&e&&(n.value=e+a)}open(e){this.currentOptions=e,this.activeMode="scanned",this.render()}close(){this.modalEl&&(this.modalEl.remove(),this.modalEl=null)}render(){if(this.close(),!this.currentOptions)return;const{phone:e,name:t,context:a,defaultMessage:n}=this.currentOptions,i=(e||"").replace(/\D/g,"").slice(-10),o=this.getSenderSignature(),p=(n||this.getVerticalQuickMessage("thanks_connecting"))+o;this.modalEl=document.createElement("div"),this.modalEl.id="unifiedWAModal",this.modalEl.className="uwa-modal-backdrop",this.modalEl.innerHTML=`
      <div class="uwa-modal-sheet">
        <!-- Header -->
        <div class="uwa-header">
          <div class="uwa-header-info">
            <div class="uwa-badge-online">
              <span class="uwa-dot"></span> Common Number Connected
            </div>
            <h3 class="uwa-title"><i class="fab fa-whatsapp me-1"></i> Send WhatsApp</h3>
            <div class="uwa-recipient-sub">
              <strong>${this.escapeHtml(t||"Customer")}</strong> · +91 ${i}
              ${a?`<span class="uwa-ctx-tag ms-1">${this.escapeHtml(a)}</span>`:""}
            </div>
          </div>
          <button class="uwa-close-btn" id="uwaCloseBtn">&times;</button>
        </div>

        <!-- Mode Selector (Scanned WA vs Meta Cloud API) -->
        <div class="uwa-mode-bar">
          <button class="uwa-mode-btn ${this.activeMode==="scanned"?"active":""}" id="uwaModeScannedBtn">
            <i class="fas fa-qrcode"></i>
            <div>
              <strong>📱 Scanned WhatsApp</strong>
              <small>Employee Account · Scanned</small>
            </div>
          </button>
          <button class="uwa-mode-btn ${this.activeMode==="meta_api"?"active":""}" id="uwaModeMetaBtn">
            <i class="fas fa-building"></i>
            <div>
              <strong>🏢 Official WhatsApp</strong>
              <small>Meta Cloud API · Verified</small>
            </div>
          </button>
        </div>

        <!-- 1-Tap Vertical Quick Responses -->
        <div class="uwa-section-label">⚡ 1-Tap Quick Responses</div>
        <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 12px;">
          <button id="uwaQuickThanksBtn" type="button" style="background:#ecfdf5; border:1.5px solid #a7f3d0; color:#065f46; border-radius:10px; padding:8px 10px; font-size:12px; font-weight:700; cursor:pointer; text-align:left; display:flex; align-items:center; gap:6px;">
            <span style="font-size:16px;">🙏</span>
            <div>
              <div>Thanks for Connecting</div>
              <small style="font-size:9.5px; font-weight:normal; opacity:.8;">Service tailored</small>
            </div>
          </button>
          <button id="uwaQuickReachBtn" type="button" style="background:#fef3c7; border:1.5px solid #fde68a; color:#92400e; border-radius:10px; padding:8px 10px; font-size:12px; font-weight:700; cursor:pointer; text-align:left; display:flex; align-items:center; gap:6px;">
            <span style="font-size:16px;">📞</span>
            <div>
              <div>Trying to Reach</div>
              <small style="font-size:9.5px; font-weight:normal; opacity:.8;">Call missed / inquiry</small>
            </div>
          </button>
        </div>

        <!-- Official Meta / Database Templates -->
        <div class="uwa-section-label">📑 Select Official Template</div>
        <div style="display:flex; gap:6px; margin-bottom:8px;">
          <select id="uwaCanonicalSeg" style="flex:1; font-size:11.5px; padding:6px; border:1px solid #cbd5e1; border-radius:8px; background:#fff;">
            <option value="">All Segments</option>
            <option value="general">MNR General</option>
            <option value="solar">Solar</option>
            <option value="myntreal_real">Myntreal Real</option>
            <option value="ev_b2c">EV B2C</option>
            <option value="ev_b2b">EV B2B</option>
            <option value="real_estate">Real Estate</option>
            <option value="etc_training">ETC Training</option>
            <option value="vgk">VGK Members</option>
            <option value="system">System</option>
          </select>
          <select id="uwaCanonicalCat" style="flex:1; font-size:11.5px; padding:6px; border:1px solid #cbd5e1; border-radius:8px; background:#fff;">
            <option value="">All Categories</option>
            <option value="MARKETING">Marketing</option>
            <option value="UTILITY">Utility</option>
            <option value="AUTHENTICATION">Authentication</option>
          </select>
        </div>
        <div style="margin-bottom:10px;">
          <select id="uwaCanonicalTpl" style="width:100%; font-size:12px; border:1px solid #cbd5e1; border-radius:8px; padding:7px 10px; background:#fff;">
            <option value="">— Loading templates… —</option>
          </select>
          <div id="uwaNoTplNotice" style="display:none; font-size:11px; color:#b45309; background:#fef3c7; border:1px solid #fde68a; border-radius:6px; padding:6px 8px; margin-top:4px;">
            No approved templates found for this filter.
          </div>
        </div>

        <!-- Dynamic Variable Inputs -->
        <div id="uwaCanonicalVarsWrap" style="display:none; margin-bottom:10px; background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:8px 10px;">
          <div style="font-size:10px; font-weight:700; color:#64748b; text-transform:uppercase; margin-bottom:6px;">Fill Variables</div>
          <div id="uwaCanonicalVarsBox"></div>
        </div>

        <!-- Quick Template Chips -->
        <div class="uwa-section-label">Contextual Quick Chips</div>
        <div class="uwa-chips-row">
          ${Object.entries(R).map(([s,r])=>`
            <button class="uwa-chip-btn" data-tpl-key="${s}">
              ${r.label}
            </button>
          `).join("")}
        </div>

        <!-- Message Composer -->
        <div class="uwa-section-label mt-2">
          Message
          <small class="text-muted" style="float:right; font-weight:normal; text-transform:none;">
            ✍️ Auto-signed with your staff identity
          </small>
        </div>
        <textarea id="uwaMessageText" class="uwa-textarea" rows="7" placeholder="Type your WhatsApp message...">${this.escapeHtml(p)}</textarea>

        <!-- Status & Result feedback -->
        <div id="uwaFeedbackBox" class="uwa-feedback-box" style="display:none;"></div>

        <!-- Action Footer -->
        <div class="uwa-footer">
          <button class="btn btn-outline uwa-cancel-btn" id="uwaCancelBtn">Cancel</button>
          <button class="btn btn-primary uwa-send-btn" id="uwaSendBtn">
            <i class="fas fa-paper-plane me-1"></i>
            <span id="uwaSendBtnLabel">Send via 📱 Scanned WhatsApp</span>
          </button>
        </div>
      </div>
    `,document.body.appendChild(this.modalEl),this.attachEvents(),this.loadCanonicalTemplates()}attachEvents(){this.modalEl&&(document.getElementById("uwaCloseBtn")?.addEventListener("click",()=>this.close()),document.getElementById("uwaCancelBtn")?.addEventListener("click",()=>this.close()),document.getElementById("uwaQuickThanksBtn")?.addEventListener("click",()=>this.applyVerticalQuick("thanks_connecting")),document.getElementById("uwaQuickReachBtn")?.addEventListener("click",()=>this.applyVerticalQuick("trying_to_reach")),document.getElementById("uwaCanonicalSeg")?.addEventListener("change",()=>this.loadCanonicalTemplates()),document.getElementById("uwaCanonicalCat")?.addEventListener("change",()=>this.loadCanonicalTemplates()),document.getElementById("uwaCanonicalTpl")?.addEventListener("change",()=>this.onCanonicalTplChange()),document.getElementById("uwaModeScannedBtn")?.addEventListener("click",()=>{this.activeMode="scanned",this.updateModeUI(),this.loadCanonicalTemplates()}),document.getElementById("uwaModeMetaBtn")?.addEventListener("click",()=>{this.activeMode="meta_api",this.updateModeUI(),this.loadCanonicalTemplates()}),this.modalEl.querySelectorAll(".uwa-chip-btn").forEach(e=>{e.addEventListener("click",t=>{const a=t.currentTarget.dataset.tplKey;if(a&&R[a]){const n=this.getSenderSignature(),i=document.getElementById("uwaMessageText");i&&(i.value=R[a].text+n,i.focus())}})}),document.getElementById("uwaSendBtn")?.addEventListener("click",()=>this.handleSend()))}updateModeUI(){const e=document.getElementById("uwaModeScannedBtn"),t=document.getElementById("uwaModeMetaBtn"),a=document.getElementById("uwaSendBtnLabel"),n=document.getElementById("uwaSendBtn");this.activeMode==="scanned"?(e?.classList.add("active"),t?.classList.remove("active"),a&&(a.textContent="Send via 📱 Scanned WhatsApp"),n&&(n.style.background="#16a34a")):(e?.classList.remove("active"),t?.classList.add("active"),a&&(a.textContent="Send via 🏢 Official WhatsApp"),n&&(n.style.background="#2563eb"))}async handleSend(){if(!this.currentOptions)return;const e=document.getElementById("uwaMessageText"),t=document.getElementById("uwaSendBtn"),a=document.getElementById("uwaSendBtnLabel");let n=(e?.value||"").trim();if(!n){this.showFeedback("Please enter a message to send.","error");return}const i=this.getSenderSignature();n.toLowerCase().includes("regards,")||(n=n+i);const{phone:o,name:p,leadId:s}=this.currentOptions,r=(o||"").replace(/\D/g,"").slice(-10);if(!r||r.length<10){this.showFeedback("Invalid recipient phone number.","error");return}if(t&&(t.disabled=!0),this.activeMode==="meta_api"){a&&(a.innerHTML='<i class="fas fa-spinner fa-spin me-1"></i> Sending via Meta API...'),this.showFeedback("Dispatching via WhatsApp Cloud API...","info");try{const d=s&&s!=="new"&&!isNaN(Number(s))?Number(s):0,l=await _.post(`/whatsapp-config/crm-lead-send/${d}`,{phone:r,custom_message:n,send_mode:"company"});if(l.success)a&&(a.innerHTML='<i class="fas fa-check me-1"></i> Sent Successfully ✓'),this.showFeedback("✅ Dispatched via WhatsApp Meta Cloud API (Official Business)","success"),setTimeout(()=>this.close(),2500);else{const c=l.error||l.data?.reason||"Meta API not available.";this.showFeedback(`❌ Meta API Error: ${c}`,"error"),t&&(t.disabled=!1),a&&(a.textContent="Retry Send")}}catch(d){console.warn("[UnifiedWAModal] Meta API failed:",d),this.showFeedback(`❌ Meta API Network error: ${d.message||"Server unreachable"}`,"error"),t&&(t.disabled=!1),a&&(a.textContent="Retry Send")}return}a&&(a.innerHTML='<i class="fas fa-spinner fa-spin me-1"></i> Sending via Personal WA...'),this.showFeedback("Connecting to WhatsApp Bot Gateway...","info");try{const d=await _.post("/whatsapp/send-message",{recipient:r,message:n,recipient_type:"individual",recipient_name:p||"Customer",lead_id:s||null});if(d.success)a&&(a.innerHTML='<i class="fas fa-check me-1"></i> Sent Successfully ✓'),this.showFeedback(`✅ Dispatched via Personal Scanned WhatsApp! Sender: ${this.escapeHtml(v.getAuthState().user?.full_name||"Staff")}`,"success"),setTimeout(()=>this.close(),2500);else{const l=d.error||"Personal WhatsApp Web is disconnected or unlinked.";this.showFeedback(`❌ Personal WA: ${l}. You can switch to "WhatsApp API" mode above to send via Official Meta Business.`,"error"),t&&(t.disabled=!1),a&&(a.textContent="Retry Send")}}catch(d){console.error("[UnifiedWAModal] Send error:",d),this.showFeedback('❌ Personal WhatsApp Gateway offline. You can switch to "WhatsApp API" above to send via Meta Cloud.',"error"),t&&(t.disabled=!1),a&&(a.textContent="Retry Send")}}showFeedback(e,t){const a=document.getElementById("uwaFeedbackBox");a&&(a.style.display="block",a.className=`uwa-feedback-box ${t}`,a.innerHTML=e)}escapeHtml(e){const t={"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"};return(e||"").replace(/[&<>"']/g,a=>t[a])}}const oe=new F,K=[{menu_code:"HOME_DASHBOARD",label:"Home Dashboard",route:"mnr-dashboard",icon:"home"},{menu_code:"VIEW_PROFILE",label:"View Profile",route:"mnr-profile",icon:"user"},{menu_code:"ADD_MEMBER",label:"Add Member",route:"mnr-add-member",icon:"user-plus"}],j=[{section_code:"ANNOUNCEMENTS",section_label:"📢 Community Updates",icon:"bullhorn",order:1,items:[{menu_code:"PUBLIC_ANNOUNCEMENTS",label:"📢 Official Updates",route:"mnr-announcements"},{menu_code:"MY_SUBMISSIONS",label:"📋 My Submissions",route:"mnr-my-announcements"},{menu_code:"PENDING",label:"⏳ Pending",route:"mnr-announcements-pending"},{menu_code:"APPROVED",label:"✅ Approved",route:"mnr-announcements-approved"},{menu_code:"REJECTED",label:"❌ Rejected",route:"mnr-announcements-rejected"}]},{section_code:"COUPON_MODULES",section_label:"🎫 Coupon Modules",icon:"ticket",order:2,items:[{menu_code:"BUY_COUPON",label:"🛒 Buy Coupon",route:"mnr-coupon-buy"},{menu_code:"ACTIVATE_COUPON",label:"✅ Activate Coupon",route:"mnr-coupon-activate"},{menu_code:"COUPON_STATUS",label:"🎫 Coupon Status",route:"mnr-coupon-status"},{menu_code:"COUPON_PROGRESS",label:"📊 Coupon Progress",route:"mnr-coupon-progress"},{menu_code:"COUPON_TRANSFER",label:"🔄 Coupon Transfer",route:"mnr-coupon-transfer"}]},{section_code:"MEMBERS",section_label:"👥 My Connections",icon:"users",order:3,items:[{menu_code:"ALL_MEMBERS",label:"👥 All Connections",route:"mnr-members-all"},{menu_code:"DIRECT_REFERRALS",label:"🔗 Direct Connections",route:"mnr-referrals"},{menu_code:"PICTURE_VIEW",label:"🌳 Connections Gallery",route:"mnr-members-picture"},{menu_code:"VED_TEAM",label:"👑 Leadership Group (VED)",route:"mnr-members-ved"}]},{section_code:"MNR",section_label:"💰 Facilitation & Recognition",icon:"coins",order:4,items:[{menu_code:"EARNINGS_SUMMARY",label:"📊 Earnings Overview",route:"mnr-earnings-summary"},{menu_code:"DIRECT_REFERRAL",label:"💰 Direct Business Facilitation",route:"mnr-income-direct"},{menu_code:"MATCHING_REFERRAL",label:"🤝 Group Performance Recognition",route:"mnr-income-matching"},{menu_code:"VED_INCOME",label:"👑 VED Leadership Recognition",route:"mnr-income-ved"},{menu_code:"GURUDAKSHINA",label:"🙏 Mentorship Contribution Benefit",route:"mnr-income-guru"},{menu_code:"FIELD_ALLOWANCE",label:"🚗 Field Allowances",route:"mnr-income-field"},{menu_code:"WITHDRAWALS",label:"💸 Withdrawals",route:"mnr-withdrawals"},{menu_code:"COUPON_BENEFITS",label:"🎁 Coupon Benefits",route:"mnr-benefits"},{menu_code:"MNR_POINTS",label:"🎯 Points Utilisation",route:"mnr-points"}]},{section_code:"MYNTREAL",section_label:"💎 MyntReal",icon:"gem",order:5,items:[{menu_code:"MY_LEADS",label:"📋 My Leads",route:"mnr-my-leads"},{menu_code:"FRANCHISE_EARNINGS",label:"🏪 Franchise Earnings",route:"mnr-franchise-earnings"}]},{section_code:"ZYNOVA",section_label:"⭐ Zynova",icon:"crown",order:6,items:[{menu_code:"VGK_REAL_DREAMS",label:"🏠 VGK Real Dreams (Real Estate)",route:"zynova-real-estate"},{menu_code:"VGK_CARE",label:"🛡️ VGK Care (Insurance)",route:"zynova-insurance"},{menu_code:"ETC",label:"🎓 EVolution Training Center (ETC)",route:"zynova-training"}]},{section_code:"AWARDS_BONANZA",section_label:"🏆 Awards & Bonanza",icon:"trophy",order:7,items:[{menu_code:"AWARDS",label:"🏆 Awards",route:"mnr-awards"},{menu_code:"BONANZA_AWARDS",label:"🎉 Bonanza Awards",route:"mnr-bonanza"}]}],q=[{menu_code:"THEME_MODE",label:"Theme Mode",route:"mnr-settings",icon:"headset"},{menu_code:"SECURITY_SETTINGS",label:"Security Settings",route:"mnr-change-password",icon:"headset"}];class W{container=null;overlay=null;isOpen=!1;expandedSections=new Set;user=null;constructor(){this.createElements()}createElements(){this.overlay=document.createElement("div"),this.overlay.className="mnr-drawer-overlay",this.overlay.addEventListener("click",()=>this.close()),document.body.appendChild(this.overlay),this.container=document.createElement("div"),this.container.className="mnr-side-drawer",this.container.innerHTML=this.render(),document.body.appendChild(this.container),this.attachEventListeners()}setUser(e){this.user=e,this.updateUI()}getIcon(e){return`<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${{home:'<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>',user:'<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',"user-plus":'<path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="8.5" cy="7" r="4"/><line x1="20" y1="8" x2="20" y2="14"/><line x1="23" y1="11" x2="17" y2="11"/>',bullhorn:'<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/>',ticket:'<path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/>',users:'<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',coins:'<circle cx="8" cy="8" r="6"/><path d="M18.09 10.37A6 6 0 1 1 10.34 18"/><path d="M7 6h1v4"/><path d="m16.71 13.88.7.71-2.82 2.82"/>',gem:'<polygon points="12 2 2 12 12 22 22 12 12 2"/><polyline points="12 2 12 22"/>',crown:'<path d="m2 4 3 12h14l3-12-6 7-4-7-4 7-6-7zm3 16h14"/>',trophy:'<path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/><path d="M4 22h16"/><path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"/><path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"/><path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"/>',headset:'<path d="M3 18v-6a9 9 0 0 1 18 0v6"/><path d="M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3zM3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3z"/>',logout:'<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>'}[e]||""}</svg>`}render(){const e=this.user?.name||"MNR Member",t=this.user?.mnr_id||"";return`
      <div class="mnr-drawer-header">
        <div class="mnr-drawer-user">
          <div class="mnr-user-avatar">${e.split(" ").map(n=>n[0]).join("").toUpperCase().slice(0,2)}</div>
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
          ${K.map(n=>`
            <div class="mnr-menu-item top-item" data-route="${n.route}">
              ${this.getIcon(n.icon||"home")}
              <span>${n.label}</span>
            </div>
          `).join("")}
        </div>

        <!-- Section menus -->
        ${j.map(n=>this.renderSection(n)).join("")}

        <!-- Bottom items -->
        <div class="mnr-bottom-menu">
          ${q.map(n=>`
            <div class="mnr-menu-item bottom-item" data-route="${n.route}">
              ${this.getIcon(n.icon||"help-circle")}
              <span>${n.label}</span>
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
          ${e.items.map(a=>`
            <a class="mnr-drawer-menu-item" data-route="${a.route}">
              <span class="mnr-menu-label">${a.label}</span>
            </a>
          `).join("")}
        </div>
      </div>
    `}attachEventListeners(){this.container&&(document.getElementById("mnrDrawerClose")?.addEventListener("click",()=>this.close()),this.container.querySelectorAll("[data-toggle]").forEach(e=>{e.addEventListener("click",t=>{const a=e.dataset.toggle;this.toggleSection(a),t.stopPropagation()})}),this.container.querySelectorAll("[data-route]").forEach(e=>{e.addEventListener("click",()=>{const t=e.dataset.route;w.navigate(t),this.close()})}),document.getElementById("mnrLogoutBtn")?.addEventListener("click",async()=>{confirm("Are you sure you want to logout?")&&(await v.logout(),window.dispatchEvent(new CustomEvent("logout")),this.close())}))}toggleSection(e){this.expandedSections.has(e)?this.expandedSections.delete(e):this.expandedSections.add(e),this.updateUI()}updateUI(){this.container&&(this.container.innerHTML=this.render(),this.attachEventListeners())}open(){this.isOpen||(this.isOpen=!0,this.container?.classList.add("open"),this.overlay?.classList.add("visible"),document.body.style.overflow="hidden")}close(){this.isOpen&&(this.isOpen=!1,this.container?.classList.remove("open"),this.overlay?.classList.remove("visible"),document.body.style.overflow="")}toggle(){this.isOpen?this.close():this.open()}destroy(){this.container?.remove(),this.overlay?.remove()}}const re=new W;class le{config;constructor(e){this.config=e}render(){if(this.config.loading)return`
        <div class="table-loading">
          <div class="spinner"></div>
          <p>Loading...</p>
        </div>
      `;if(!this.config.data||this.config.data.length===0)return`
        <div class="table-empty">
          <p>${this.config.emptyMessage||"No data found"}</p>
        </div>
      `;const e=n=>this.config.sortColumn===n?this.config.sortDirection==="asc"?" ↑":" ↓":"",t=this.config.columns.map(n=>{const i=n.sortable!==!1,o=e(n.key),p=n.width?`width: ${n.width};`:"",s=i?`data-sort-column="${n.key}"`:"";return`<th style="${p}${i?"cursor: pointer;":""}" ${s}>${n.label}${o}</th>`}).join(""),a=this.config.data.map(n=>`<tr>${this.config.columns.map(o=>{const p=n[o.key];return`<td>${o.render?o.render(p,n):p??"-"}</td>`}).join("")}</tr>`).join("");return`
      <div class="table-responsive-wrapper">
        <table class="mobile-data-table">
          <thead>
            <tr>${t}</tr>
          </thead>
          <tbody>
            ${a}
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
    `}static attachSortListeners(e,t){e.querySelectorAll("[data-sort-column]").forEach(a=>{a.addEventListener("click",()=>{const n=a.getAttribute("data-sort-column");n&&t(n)})})}}const Y=[{menu_code:"SERVICE_REQUEST",label:"Service Request",route:"partner-service",icon:"headset",highlight:!0},{menu_code:"HOME_DASHBOARD",label:"Home Dashboard",route:"partner-dashboard",icon:"home"},{menu_code:"VIEW_PROFILE",label:"View Profile",route:"partner-profile",icon:"user"}],Z=[{section_code:"ORDERS",section_label:"Orders",icon:"package",order:1,items:[{menu_code:"ALL_ORDERS",label:"All Orders",route:"partner-orders"},{menu_code:"NEW_ORDER",label:"Create New Order",route:"partner-new-order"}]},{section_code:"SERVICE",section_label:"Service Center",icon:"tool",order:2,items:[{menu_code:"RAISE_TICKET",label:"Raise New Ticket",route:"partner-raise-ticket"},{menu_code:"MY_TICKETS",label:"My Tickets",route:"partner-service"},{menu_code:"TICKET_HISTORY",label:"Ticket History",route:"partner-ticket-history"}]},{section_code:"FINANCE",section_label:"Finance",icon:"coins",order:3,items:[{menu_code:"INVOICES",label:"Invoices",route:"partner-invoices"},{menu_code:"PAYMENTS",label:"Payments",route:"partner-payments"},{menu_code:"REVENUE",label:"Revenue Dashboard",route:"partner-revenue"}]},{section_code:"LEADS",section_label:"Leads & CRM",icon:"users",order:4,items:[{menu_code:"MY_LEADS",label:"My Leads",route:"partner-leads"}]}];class X{container=null;overlay=null;isOpen=!1;expandedSections=new Set;user=null;constructor(){this.createElements()}createElements(){this.overlay=document.createElement("div"),this.overlay.className="partner-drawer-overlay",this.overlay.addEventListener("click",()=>this.close()),document.body.appendChild(this.overlay),this.container=document.createElement("div"),this.container.className="partner-side-drawer",this.container.innerHTML=this.render(),document.body.appendChild(this.container),this.injectStyles(),this.attachEventListeners()}injectStyles(){if(document.getElementById("partner-drawer-styles"))return;const e=document.createElement("style");e.id="partner-drawer-styles",e.textContent=`
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
    `,document.head.appendChild(e)}setUser(e){this.user=e,this.updateUI()}getIcon(e){return`<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${{home:'<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>',user:'<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',package:'<line x1="16.5" y1="9.4" x2="7.5" y2="4.21"/><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/>',tool:'<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>',coins:'<circle cx="8" cy="8" r="6"/><path d="M18.09 10.37A6 6 0 1 1 10.34 18"/><path d="M7 6h1v4"/><path d="m16.71 13.88.7.71-2.82 2.82"/>',users:'<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',headset:'<path d="M3 18v-6a9 9 0 0 1 18 0v6"/><path d="M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3zM3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3z"/>',logout:'<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>'}[e]||""}</svg>`}render(){const e=this.user?.name||this.user?.partner_name||"Partner",t=this.user?.partner_id||this.user?.partner_code||"PARTNER",a=this.user?.partner_type||this.user?.type||"Partner";return`
      <div class="partner-drawer-header">
        <div class="partner-drawer-user">
          <div class="partner-user-avatar">${e.split(" ").map(i=>i[0]).join("").toUpperCase().slice(0,2)}</div>
          <div class="partner-user-info">
            <span class="partner-user-name">${e}</span>
            <span class="partner-user-code">${t}</span>
            <span class="partner-user-type">${a}</span>
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
          ${Y.map(i=>`
            <div class="partner-menu-item ${i.highlight?"highlight":""}" data-route="${i.route}">
              ${this.getIcon(i.icon||"home")}
              <span>${i.label}</span>
            </div>
          `).join("")}
        </div>

        ${Z.map(i=>this.renderSection(i)).join("")}

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
          ${e.items.map(a=>`
            <a class="partner-drawer-menu-item" data-route="${a.route}">
              ${a.label}
            </a>
          `).join("")}
        </div>
      </div>
    `}attachEventListeners(){this.container&&(document.getElementById("partnerDrawerClose")?.addEventListener("click",()=>this.close()),this.container.querySelectorAll("[data-toggle]").forEach(e=>{e.addEventListener("click",t=>{const a=e.dataset.toggle;this.toggleSection(a),t.stopPropagation()})}),this.container.querySelectorAll("[data-route]").forEach(e=>{e.addEventListener("click",()=>{const t=e.dataset.route;w.navigate(t),this.close()})}),document.getElementById("partnerLogoutBtn")?.addEventListener("click",async()=>{confirm("Are you sure you want to logout?")&&(await v.logout(),window.dispatchEvent(new CustomEvent("logout")),this.close())}))}toggleSection(e){this.expandedSections.has(e)?this.expandedSections.delete(e):this.expandedSections.add(e),this.updateUI()}updateUI(){this.container&&(this.container.innerHTML=this.render(),this.attachEventListeners())}open(){this.isOpen||(this.isOpen=!0,this.container?.classList.add("open"),this.overlay?.classList.add("visible"),document.body.style.overflow="hidden")}close(){this.isOpen&&(this.isOpen=!1,this.container?.classList.remove("open"),this.overlay?.classList.remove("visible"),document.body.style.overflow="")}toggle(){this.isOpen?this.close():this.open()}destroy(){this.container?.remove(),this.overlay?.remove()}}const de=new X;class ce{container;constructor(e){this.container=e}render(){const t=v.getAuthState().user?.portal||"staff",a=w.getTabRoutes(t),n=w.getCurrentRoute();this.container.innerHTML=`
      <nav class="bottom-tabs">
        ${a.map(i=>`
          <button 
            class="tab-item ${n===i.id?"active":""}" 
            data-route="${i.id}"
          >
            ${this.getIcon(i.icon)}
            <span class="tab-label">${i.title}</span>
          </button>
        `).join("")}
      </nav>
    `,this.attachListeners()}attachListeners(){this.container.querySelectorAll(".tab-item").forEach(e=>{e.addEventListener("click",()=>{const t=e.getAttribute("data-route");t&&w.navigate(t)})})}getIcon(e){const t={home:`<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
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
      </svg>`};return t[e]||t.home}}class Q{isShowing=!1;unsubscribe=null;checkInterval=null;init(){this.unsubscribe&&this.unsubscribe(),this.checkInterval&&clearInterval(this.checkInterval),this.unsubscribe=_.onSessionExpired(e=>{console.log("[SessionBanner] Session expired detected, endpoint:",e),v.getAuthState().isLoggedIn&&this.show()}),this.checkInterval=setInterval(()=>{if(!v.getAuthState().isLoggedIn){this.isShowing&&this.hide();return}const t=O.getTrackingStatus();t.isSessionExpired&&!this.isShowing?this.show():!t.isSessionExpired&&this.isShowing&&this.hide()},2e3)}cleanup(){this.unsubscribe&&(this.unsubscribe(),this.unsubscribe=null),this.checkInterval&&(clearInterval(this.checkInterval),this.checkInterval=null),this.hide()}show(){if(!v.getAuthState().isLoggedIn||this.isShowing||document.getElementById("globalSessionBanner"))return;this.isShowing=!0;const e=document.createElement("div");e.id="globalSessionBanner",e.className="global-session-banner",e.innerHTML=`
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
    `,document.body.appendChild(e),document.getElementById("globalReAuthBtn")?.addEventListener("click",t=>{t.stopPropagation(),this.showReAuthModal()}),e.addEventListener("click",()=>this.showReAuthModal())}hide(){const e=document.getElementById("globalSessionBanner");e&&e.remove(),this.isShowing=!1}showReAuthModal(){if(document.getElementById("globalReAuthModal"))return;const t=v.getAuthState().user,a=document.createElement("div");a.id="globalReAuthModal",a.className="modal",a.style.display="flex",a.style.zIndex="10001",a.innerHTML=`
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
    `,document.body.appendChild(a),setTimeout(()=>{document.getElementById("globalReAuthPassword")?.focus()},100),document.getElementById("closeGlobalReAuthModal")?.addEventListener("click",()=>a.remove()),document.getElementById("cancelGlobalReAuth")?.addEventListener("click",()=>a.remove()),document.getElementById("submitGlobalReAuth")?.addEventListener("click",()=>this.submitReAuth()),document.getElementById("globalReAuthPassword")?.addEventListener("keypress",n=>{n.key==="Enter"&&this.submitReAuth()})}async submitReAuth(){const e=document.getElementById("globalReAuthUserId"),t=document.getElementById("globalReAuthPassword"),a=document.getElementById("globalReAuthError"),n=document.getElementById("submitGlobalReAuth");if(!t)return;const i=e?.value||"",o=t.value;if(!o){a&&(a.textContent="Please enter your password",a.style.display="block");return}n&&(n.disabled=!0,n.textContent="Logging in...");try{const s=v.getAuthState().user?.portal||"staff",r=await v.loginWithPassword(i,o,s);if(r.success){document.getElementById("globalReAuthModal")?.remove(),this.hide();const{offlineQueueService:d}=await N(async()=>{const{offlineQueueService:u}=await import("./services-D8IBt05T.js").then(h=>h.l);return{offlineQueueService:u}},__vite__mapDeps([0,1,2,3]),import.meta.url);d.getStatus().pendingCount>0&&console.log("[SessionBanner] Re-auth successful, queued data will sync automatically"),console.log("[SessionBanner] Refreshing current page after successful re-auth");const{routerService:c}=await N(async()=>{const{routerService:u}=await import("./services-D8IBt05T.js").then(h=>h.q);return{routerService:u}},__vite__mapDeps([0,1,2,3]),import.meta.url),f=c.getCurrentRoute();c.navigate(f,!1)}else a&&(a.textContent=r.error||"Login failed. Please try again.",a.style.display="block")}catch(p){a&&(a.textContent=p.message||"An error occurred",a.style.display="block")}finally{n&&(n.disabled=!1,n.textContent="Login")}}}const pe=new Q;class J{container;fab=null;modal=null;messages=[];conversationHistory=[];isOpen=!1;isLoading=!1;constructor(){this.container=document.createElement("div"),this.container.id="vgk-mobile-root",document.body.appendChild(this.container),this.render()}getEndpoint(){const e=M.getPortal();return"/api/v1/ai/command/process"}render(){if(!this.getEndpoint())return;this.container.innerHTML=`
      <style>
        #vgk-mobile-fab {
          position: fixed; bottom: 140px; right: 12px; z-index: 9999;
          width: 46px; height: 46px; border-radius: 50%;
          background: linear-gradient(135deg, #6c3de8, #a855f7);
          border: none; box-shadow: 0 4px 16px rgba(108,61,232,.5);
          cursor: pointer; display: flex; align-items: center; justify-content: center;
          font-size: 20px; transition: transform .15s, box-shadow .2s;
          touch-action: none; user-select: none;
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
        <img src="/public/vgk-assistant-logo.png" onerror="this.style.display='none';this.parentElement.textContent='🤖'" style="width:26px;height:26px;border-radius:50%;">
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
    `,this.fab=this.container.querySelector("#vgk-mobile-fab"),this.modal=this.container.querySelector("#vgk-mobile-modal"),this.attachFabDrag(),this.container.querySelector("#vgk-close-btn")?.addEventListener("click",()=>this.close());const t=this.container.querySelector("#vgk-text-input");this.container.querySelector("#vgk-send-btn")?.addEventListener("click",()=>{t.value.trim()&&(this.send(t.value.trim()),t.value="")}),t?.addEventListener("keypress",a=>{a.key==="Enter"&&t.value.trim()&&(this.send(t.value.trim()),t.value="")}),this.container.querySelector("#vgk-mic-btn")?.addEventListener("click",()=>this.startVoice(t)),this.pushMessage("assistant","Hi! I'm VGK Assistant. How can I help you today?")}attachFabDrag(){if(!this.fab)return;let e=!1,t=0,a=0,n=0,i=0,o=!1;const p=d=>{const l=d.touches[0];t=l.clientX,a=l.clientY;const c=this.fab.getBoundingClientRect();n=c.left,i=c.top,e=!0,o=!1},s=d=>{if(!e)return;const l=d.touches[0],c=l.clientX-t,f=l.clientY-a;if(Math.abs(c)>5||Math.abs(f)>5){o=!0;const u=Math.max(10,Math.min(window.innerWidth-60,n+c)),h=Math.max(60,Math.min(window.innerHeight-100,i+f));this.fab.style.left=`${u}px`,this.fab.style.top=`${h}px`,this.fab.style.right="auto",this.fab.style.bottom="auto"}},r=()=>{e=!1,o||this.open()};this.fab.addEventListener("touchstart",p,{passive:!0}),this.fab.addEventListener("touchmove",s,{passive:!0}),this.fab.addEventListener("touchend",r),this.fab.addEventListener("click",d=>{o?(d.preventDefault(),d.stopPropagation()):this.open()})}open(){this.modal?.classList.add("open"),this.isOpen=!0,this.scrollToBottom()}close(){this.modal?.classList.remove("open"),this.isOpen=!1}pushMessage(e,t){this.messages.push({role:e,text:t}),this.renderMessages()}renderMessages(){const e=this.container.querySelector("#vgk-messages");e&&(e.innerHTML=this.messages.map(t=>`<div class="vgk-bubble ${t.role}">${t.text.replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/\n/g,"<br>")}</div>`).join(""),this.isLoading&&(e.innerHTML+='<div class="vgk-typing"><div class="vgk-dot"></div><div class="vgk-dot"></div><div class="vgk-dot"></div></div>'),this.scrollToBottom())}scrollToBottom(){const e=this.container.querySelector("#vgk-messages");e&&(e.scrollTop=e.scrollHeight)}async send(e){if(this.isLoading)return;this.pushMessage("user",e),this.isLoading=!0,this.renderMessages();const t=this.getEndpoint();if(!t){this.pushMessage("assistant","Not available for this portal."),this.isLoading=!1;return}try{const a=await _.getToken(),i=await(await fetch(t,{method:"POST",headers:{"Content-Type":"application/json",...a?{Authorization:`Bearer ${a}`}:{}},body:JSON.stringify({user_message:e,conversation_history:this.conversationHistory.slice(-20),language:"en",company_id:null,allowed_intents:null})})).json();if(i.reply_text){if(this.conversationHistory.push({role:"user",text:e}),this.conversationHistory.push({role:"assistant",text:i.reply_text}),this.conversationHistory.length>20&&(this.conversationHistory=this.conversationHistory.slice(-20)),this.pushMessage("assistant",i.reply_text),i.speak_text&&"speechSynthesis"in window){const o=new SpeechSynthesisUtterance(i.speak_text);o.lang="en-IN",o.rate=1,window.speechSynthesis.speak(o)}}else this.pushMessage("assistant",i.detail||"Something went wrong.")}catch{this.pushMessage("assistant","Could not reach VGK server. Please try again.")}this.isLoading=!1,this.renderMessages()}startVoice(e){const t=window.SpeechRecognition||window.webkitSpeechRecognition;if(!t){alert("Voice input not supported on this device.");return}const a=this.container.querySelector("#vgk-mic-btn"),n=new t;n.lang="en-IN",n.continuous=!1,n.interimResults=!1,n.onstart=()=>a.classList.add("recording"),n.onresult=i=>{const o=i.results[0][0].transcript;e.value=o},n.onend=()=>a.classList.remove("recording"),n.onerror=()=>a.classList.remove("recording"),n.start()}}function ue(){const E=M.getPortal();(E==="staff"||E==="partner")&&new J}export{ce as B,se as L,le as M,T as P,ie as a,G as g,ue as i,re as m,de as p,pe as s,oe as u};
