const __vite__mapDeps=(i,m=__vite__mapDeps,d=(m.f||(m.f=["./services-CQ7x3UT6.js","./vendor-capacitor-plugins-DTPsYLMi.js","./vendor-capacitor-core-zwN_Y1fq.js","./vendor-B1GRRwIS.js"])))=>i.map(i=>d[i]);
import{v as x,j as z,d as y,b as C,r as $,t as M,M as j,a as q}from"./services-CQ7x3UT6.js";import{L as S}from"./vendor-B1GRRwIS.js";import{_ as W}from"./vendor-capacitor-plugins-DTPsYLMi.js";import{gpsService as Y}from"./services-gps-DEeT69yR.js";class Z{modalEl=null;uiState="CLOSED";currentOptions=null;enteredNumber="";rawNumber="";isPresetNumber=!1;isDtmfOpen=!1;unsubscribeTelephony=null;currentSession=null;floatingPos={x:0,y:0};pillPos={x:0,y:0};isDraggingWindow=!1;isDraggingPill=!1;dragStartPointer={x:0,y:0};dragStartPos={x:0,y:0};hasInitializedPosition=!1;lastNotifiedLeadId=null;constructor(){typeof window<"u"&&(window.addEventListener("keydown",e=>{e.key==="Escape"&&this.isOpen()&&(this.uiState==="ACTIVE_FLOATING"?this.minimize():this.uiState==="DIALER"&&this.close())}),window.addEventListener("resize",()=>{this.isOpen()&&(this.clampPositions(),this.applyPositions())}))}isOpen(){return this.modalEl!==null&&document.body.contains(this.modalEl)&&this.uiState!=="CLOSED"}getUIState(){return this.uiState}open(e){this.currentOptions=e;const t=(e.phoneNumber||"").replace(/[^\d+]/g,"");this.enteredNumber=t,this.rawNumber=t,this.isPresetNumber=!!t,this.isDtmfOpen=!1,this.hasInitializedPosition=!1,this.unsubscribeTelephony&&this.unsubscribeTelephony(),this.unsubscribeTelephony=x.subscribe(i=>{this.currentSession=i,this.handleTelephonyStateUpdate(i)});const a=x.isCallActive();this.uiState=a?"ACTIVE_FLOATING":"DIALER",this.render(),this.loadLeadContext(e.entityId),e.autoStart&&this.enteredNumber&&this.startCall()}minimize(){this.uiState!=="CLOSED"&&(this.uiState="MINIMIZED",this.updateVisibility())}restore(){this.uiState!=="CLOSED"&&(this.uiState="ACTIVE_FLOATING",this.updateVisibility(),this.updateSessionUI())}close(){if(this.currentSession&&(x.isCallActive()||["connecting","ringing","connected","held"].includes(this.currentSession.state))){this.minimize();return}this.teardown()}forceCloseAndHangup(){this.currentSession&&x.isCallActive()&&x.endCall(),this.teardown()}teardown(){this.unsubscribeTelephony&&(this.unsubscribeTelephony(),this.unsubscribeTelephony=null),this.modalEl&&(this.modalEl.remove(),this.modalEl=null),this.uiState="CLOSED",this.currentOptions=null,this.currentSession=null,this.hasInitializedPosition=!1,this.lastNotifiedLeadId=null}handleTelephonyStateUpdate(e){if(!this.modalEl||!document.body.contains(this.modalEl))if(e.state!=="idle")this.render();else return;if(x.isCallActive()){this.uiState==="DIALER"&&(this.uiState="ACTIVE_FLOATING");const a=Number(this.currentOptions?.entityId);a&&(this.currentOptions?.entityType==="lead"||!this.currentOptions?.entityType)&&this.lastNotifiedLeadId!==a&&(this.lastNotifiedLeadId=a,z.notifyCallActive(a))}else if(this.lastNotifiedLeadId=null,e.state==="ended"){this.uiState="ENDED_SUMMARY";const a=this.currentOptions,i=e.durationSeconds||0;z.clearCallActive(),a?.entityId&&window.dispatchEvent(new CustomEvent("myntos:lead-call-ended",{detail:{leadId:a.entityId,name:a.name,phoneNumber:a.phoneNumber,durationSeconds:i,categoryName:a.categoryName,status:a.status}})),setTimeout(()=>{this.uiState==="ENDED_SUMMARY"&&this.teardown()},1600)}else if(e.state==="idle"&&this.uiState!=="DIALER"){z.clearCallActive(),this.teardown();return}this.updateVisibility(),this.updateSessionUI()}maskPhone(e){if(!e)return"—";const t=e.replace(/\D/g,"");if(t.length<6)return e;const a=t.slice(-10);return y.isMR10001()?a.length===10?`+91 ${a.slice(0,5)} ${a.slice(5)}`:e:`+91 ${a.slice(0,2)}••••${a.slice(-4)}`}getDialInputDisplay(){return!y.isMR10001()&&this.isPresetNumber&&this.enteredNumber?this.maskPhone(this.enteredNumber):this.enteredNumber}formatDuration(e){const t=Math.floor(e/60).toString().padStart(2,"0"),a=(e%60).toString().padStart(2,"0");return`${t}:${a}`}initPositions(){if(this.hasInitializedPosition||typeof window>"u")return;const e=window.innerWidth,t=window.innerHeight,a=Math.min(400,e-24),i=440,n=Math.max(12,Math.round((e-a)/2)),s=Math.max(20,Math.round((t-i)/2));this.floatingPos={x:n,y:s},this.pillPos={x:Math.max(12,e-260),y:Math.max(20,t-100)},this.hasInitializedPosition=!0}clampPositions(){if(typeof window>"u")return;const e=window.innerWidth,t=window.innerHeight,a=Math.min(400,e-24),i=440,n=12,s=Math.max(12,e-a-12),l=12,o=Math.max(12,t-i-12);this.floatingPos.x=Math.min(Math.max(this.floatingPos.x,n),s),this.floatingPos.y=Math.min(Math.max(this.floatingPos.y,l),o);const d=240,r=54,m=12,p=Math.max(12,e-d-12),g=12,h=Math.max(12,t-r-12);this.pillPos.x=Math.min(Math.max(this.pillPos.x,m),p),this.pillPos.y=Math.min(Math.max(this.pillPos.y,g),h)}applyPositions(){const e=this.modalEl?.querySelector("#spModalDialog");e&&(this.uiState==="ACTIVE_FLOATING"||this.uiState==="DIALER")&&(e.style.transform=`translate3d(${this.floatingPos.x}px, ${this.floatingPos.y}px, 0)`);const t=this.modalEl?.querySelector("#spMinimizedPill");t&&this.uiState==="MINIMIZED"&&(t.style.transform=`translate3d(${this.pillPos.x}px, ${this.pillPos.y}px, 0)`)}render(){this.modalEl&&this.modalEl.remove(),this.initPositions(),this.clampPositions();const{name:e,entityType:t}=this.currentOptions||{},a=e||"Customer Lead",i=t?t.toUpperCase():"LEAD";this.modalEl=document.createElement("div"),this.modalEl.id="myntosCentralSoftphoneModal",this.modalEl.style.cssText=`
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
              <span style="background: #e0f2fe !important; color: #0369a1 !important; font-size: 10px !important; font-weight: 700 !important; padding: 1px 6px !important; border-radius: 4px !important;">${i}</span>
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
              <input type="text" id="spDialInput" value="${this.getDialInputDisplay()}" placeholder="Enter phone number..." ${!y.isMR10001()&&this.isPresetNumber?"readonly":""} style="background: transparent !important; border: none !important; outline: none !important; font-size: 17px !important; font-weight: 700 !important; color: #0f172a !important; width: 100% !important; letter-spacing: 0.5px !important;" />
              <button id="spBackspaceBtn" style="background: transparent !important; border: none !important; color: #64748b !important; font-size: 16px !important; cursor: pointer !important; padding: 4px 6px !important;" title="Backspace">⌫</button>
            </div>

            <!-- 3x4 Keypad Grid -->
            <div style="display: grid !important; grid-template-columns: repeat(3, 1fr) !important; gap: 6px !important; margin-bottom: 12px !important;">
              ${[{k:"1",s:"&nbsp;"},{k:"2",s:"ABC"},{k:"3",s:"DEF"},{k:"4",s:"GHI"},{k:"5",s:"JKL"},{k:"6",s:"MNO"},{k:"7",s:"PQRS"},{k:"8",s:"TUV"},{k:"9",s:"WXYZ"},{k:"*",s:"&nbsp;"},{k:"0",s:"+"},{k:"#",s:"&nbsp;"}].map(n=>`
                <button class="sp-num-btn" data-key="${n.k}" style="background: #f8fafc !important; border: 1px solid #e2e8f0 !important; border-radius: 8px !important; padding: 6px 4px !important; cursor: pointer !important; display: flex !important; flex-direction: column !important; align-items: center !important; justify-content: center !important; user-select: none !important;">
                  <div style="font-size: 17px !important; font-weight: 700 !important; color: #0f172a !important; line-height: 1.1 !important;">${n.k}</div>
                  <div style="font-size: 8px !important; font-weight: 600 !important; color: #64748b !important; letter-spacing: 1px !important; line-height: 1 !important; margin-top: 1px !important;">${n.s}</div>
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
              ${["1","2","3","4","5","6","7","8","9","*","0","#"].map(n=>`
                <button class="sp-dtmf-btn" data-dtmf="${n}" style="background: rgba(255,255,255,0.15) !important; border: 1px solid rgba(255,255,255,0.2) !important; color: white !important; border-radius: 6px !important; font-weight: bold !important; padding: 5px !important; font-size: 12px !important; cursor: pointer !important;">${n}</button>
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

              <!-- In-Call Volume Control Slider -->
              <div id="spInCallVolumeWrap" style="display: flex !important; align-items: center !important; justify-content: center !important; gap: 8px !important; width: 100% !important; max-width: 220px !important; padding: 4px 10px !important; background: rgba(255,255,255,0.06) !important; border-radius: 12px !important; border: 1px solid rgba(255,255,255,0.1) !important; box-sizing: border-box !important;">
                <span style="color: #94a3b8 !important; font-size: 11px !important;">🔈</span>
                <input id="spInCallVolumeSlider" type="range" min="0" max="100" value="${Math.round(x.getVolume()*100)}" style="width: 100% !important; height: 4px !important; accent-color: #38bdf8 !important; cursor: pointer !important;" title="Adjust call volume" />
                <span style="color: #94a3b8 !important; font-size: 11px !important;">🔊</span>
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
    `,document.body.appendChild(this.modalEl),this.attachEventListeners(),this.attachDragListeners(),this.updateVisibility(),this.updateSessionUI()}attachDragListeners(){if(!this.modalEl)return;const e=this.modalEl.querySelector("#spFloatingHeader"),t=this.modalEl.querySelector("#spModalDialog");if(e&&t){e.addEventListener("pointerdown",n=>{const s=n.target;if(!(s&&s.closest("button, input, a"))){this.isDraggingWindow=!0,this.dragStartPointer={x:n.clientX,y:n.clientY},this.dragStartPos={x:this.floatingPos.x,y:this.floatingPos.y};try{e.setPointerCapture(n.pointerId)}catch{}n.preventDefault(),n.stopPropagation()}}),e.addEventListener("pointermove",n=>{if(!this.isDraggingWindow)return;const s=n.clientX-this.dragStartPointer.x,l=n.clientY-this.dragStartPointer.y;this.floatingPos={x:this.dragStartPos.x+s,y:this.dragStartPos.y+l},this.clampPositions(),t.style.transform=`translate3d(${this.floatingPos.x}px, ${this.floatingPos.y}px, 0)`});const i=n=>{if(this.isDraggingWindow){this.isDraggingWindow=!1;try{e.releasePointerCapture(n.pointerId)}catch{}this.clampPositions(),t.style.transform=`translate3d(${this.floatingPos.x}px, ${this.floatingPos.y}px, 0)`}};e.addEventListener("pointerup",i),e.addEventListener("pointercancel",i)}const a=this.modalEl.querySelector("#spMinimizedPill");if(a){let i=!1;a.addEventListener("pointerdown",s=>{const l=s.target;if(!(l&&l.closest("#spPillRestoreBtn"))){this.isDraggingPill=!0,i=!1,this.dragStartPointer={x:s.clientX,y:s.clientY},this.dragStartPos={x:this.pillPos.x,y:this.pillPos.y};try{a.setPointerCapture(s.pointerId)}catch{}s.preventDefault(),s.stopPropagation()}}),a.addEventListener("pointermove",s=>{if(!this.isDraggingPill)return;const l=s.clientX-this.dragStartPointer.x,o=s.clientY-this.dragStartPointer.y;(Math.abs(l)>3||Math.abs(o)>3)&&(i=!0),this.pillPos={x:this.dragStartPos.x+l,y:this.dragStartPos.y+o},this.clampPositions(),a.style.transform=`translate3d(${this.pillPos.x}px, ${this.pillPos.y}px, 0)`});const n=s=>{if(this.isDraggingPill){this.isDraggingPill=!1;try{a.releasePointerCapture(s.pointerId)}catch{}this.clampPositions(),a.style.transform=`translate3d(${this.pillPos.x}px, ${this.pillPos.y}px, 0)`,i||this.restore()}};a.addEventListener("pointerup",n),a.addEventListener("pointercancel",n)}}attachEventListeners(){if(!this.modalEl)return;this.modalEl.querySelector("#spModalBackdrop")?.addEventListener("click",()=>{this.uiState==="DIALER"&&this.close()}),this.modalEl.querySelector("#spMinimizeBtn")?.addEventListener("click",t=>{t.stopPropagation(),this.minimize()}),this.modalEl.querySelector("#spCloseBtn")?.addEventListener("click",t=>{t.stopPropagation(),this.close()}),this.modalEl.querySelector("#spPillRestoreBtn")?.addEventListener("click",t=>{t.stopPropagation(),this.restore()});const e=this.modalEl.querySelector("#spDialInput");e?.addEventListener("input",t=>{this.enteredNumber=t.target.value,this.rawNumber="",this.isPresetNumber=!1,this.updateCallerPhoneDisplay()}),this.modalEl.querySelector("#spBackspaceBtn")?.addEventListener("click",()=>{if(this.isPresetNumber){this.isPresetNumber=!1,this.rawNumber="",this.enteredNumber="",e&&(e.value="",e.readOnly=!1),this.updateCallerPhoneDisplay();return}this.enteredNumber.length>0&&(this.enteredNumber=this.enteredNumber.slice(0,-1),e&&(e.value=this.enteredNumber),this.updateCallerPhoneDisplay(),x.playKeyTone())}),this.modalEl.querySelectorAll(".sp-num-btn").forEach(t=>{t.addEventListener("click",a=>{const i=a.currentTarget.getAttribute("data-key");this.isPresetNumber&&(this.isPresetNumber=!1,this.rawNumber="",this.enteredNumber="",e&&(e.value="",e.readOnly=!1)),i&&this.enteredNumber.length<15&&(this.enteredNumber+=i,e&&(e.value=this.enteredNumber),this.updateCallerPhoneDisplay(),x.playKeyTone())})}),this.modalEl.querySelector("#spMainDialBtn")?.addEventListener("click",()=>{this.startCall()}),this.modalEl.querySelector("#spDirectSimBtn")?.addEventListener("click",()=>{if(!this.enteredNumber){this.showError("Please enter a phone number.");return}x.triggerDirectSimCall(this.enteredNumber)}),this.modalEl.querySelector("#spMyOperatorBtn")?.addEventListener("click",async()=>{if(!this.enteredNumber){this.showError("Please enter a phone number.");return}try{const t=this.currentOptions?.entityId?parseInt(String(this.currentOptions.entityId)):null;await x.triggerMyOperatorCall(this.enteredNumber,t),alert(`MyOperator call dispatched to ${this.enteredNumber}! Your office line will ring shortly.`)}catch(t){this.showError(`MyOperator error: ${t.message}`)}}),this.modalEl.querySelector("#spBtnMute")?.addEventListener("click",()=>{x.toggleMute()}),this.modalEl.querySelector("#spBtnSpeaker")?.addEventListener("click",()=>{x.toggleSpeaker()}),this.modalEl.querySelector("#spInCallVolumeSlider")?.addEventListener("input",t=>{const a=parseFloat(t.target.value)/100;x.setVolume(a)}),this.modalEl.querySelector("#spBtnHold")?.addEventListener("click",()=>{x.toggleHold()}),this.modalEl.querySelector("#spBtnKeypad")?.addEventListener("click",()=>{this.isDtmfOpen=!this.isDtmfOpen;const t=this.modalEl?.querySelector("#spDtmfGrid");t&&(t.style.display=this.isDtmfOpen?"grid":"none")}),this.modalEl.querySelectorAll(".sp-dtmf-btn").forEach(t=>{t.addEventListener("click",a=>{const i=a.currentTarget.getAttribute("data-dtmf");i&&x.sendDTMF(i)})}),this.modalEl.querySelector("#spBtnHangup")?.addEventListener("click",()=>{x.endCall()})}updateVisibility(){if(!this.modalEl)return;const e=this.modalEl.querySelector("#spModalBackdrop"),t=this.modalEl.querySelector("#spModalDialog"),a=this.modalEl.querySelector("#spMinimizedPill"),i=this.modalEl.querySelector("#spInCallView"),n=this.modalEl.querySelector("#spDialerView");this.uiState==="DIALER"?(e&&(e.style.display="block"),t&&(t.style.display="block"),a&&(a.style.display="none"),n&&(n.style.display="block"),i&&(i.style.display="none")):this.uiState==="ACTIVE_FLOATING"?(e&&(e.style.display="none"),t&&(t.style.display="block"),a&&(a.style.display="none"),n&&(n.style.display="none"),i&&(i.style.display="flex")):this.uiState==="MINIMIZED"?(e&&(e.style.display="none"),t&&(t.style.display="none"),a&&(a.style.display="flex")):this.uiState==="ENDED_SUMMARY"&&(e&&(e.style.display="none"),t&&(t.style.display="block"),a&&(a.style.display="none"),n&&(n.style.display="none"),i&&(i.style.display="flex"))}updateCallerPhoneDisplay(){const e=this.modalEl?.querySelector("#spCallerPhoneDisplay");e&&(e.textContent=this.maskPhone(this.enteredNumber))}showError(e){const t=this.modalEl?.querySelector("#spErrorBanner");t&&(t.textContent=e,t.style.display="block")}hideError(){const e=this.modalEl?.querySelector("#spErrorBanner");e&&(e.style.display="none")}async startCall(){x.prepareAudioOnUserGesture(),this.hideError();const e=this.rawNumber||this.enteredNumber;if(!e){this.showError("Please enter a destination phone number.");return}const t=this.currentOptions?.name||"Contact Lead",a=this.currentOptions?.entityId||null;this.uiState="ACTIVE_FLOATING",this.updateVisibility();const i=await x.startCall(e,t,a);!i.success&&i.error&&(i.error==="A call is already in progress."?console.warn("[SoftphoneModal] Duplicate dial prevented; ignoring duplicate error toast"):this.showError(i.error))}updateSessionUI(){if(!this.modalEl||!this.currentSession)return;const e=this.currentSession.contactName||this.currentOptions?.name||"Contact Lead",t=this.currentSession.destinationPhone||this.enteredNumber,a=this.formatDuration(this.currentSession.durationSeconds),i=this.modalEl.querySelector("#spActiveCallerName");i&&(i.textContent=e);const n=this.modalEl.querySelector("#spActiveCallerPhone");n&&(n.textContent=this.maskPhone(t));const s=this.modalEl.querySelector("#spCallTimerDisplay");s&&(s.textContent=a);const l=this.modalEl.querySelector("#spPillCallerName");l&&(l.textContent=e);const o=this.modalEl.querySelector("#spPillTimerDisplay");o&&(o.textContent=a);const d=this.modalEl.querySelector("#spCallStateBadge");d&&(this.currentSession.state==="connected"?(d.textContent="🟢 Connected",d.style.background="#22c55e",d.style.color="#ffffff"):this.currentSession.state==="ringing"?(d.textContent="📞 Ringing...",d.style.background="#38bdf8",d.style.color="#000000"):this.currentSession.state==="connecting"?(d.textContent="⏳ Connecting...",d.style.background="#f59e0b",d.style.color="#000000"):this.currentSession.state==="ended"&&(d.textContent="🛑 Call Ended",d.style.background="#ef4444",d.style.color="#ffffff"));const r=this.modalEl.querySelector("#spBtnMute");r&&(r.style.background=this.currentSession.isMuted?"rgba(239,68,68,0.6)":"rgba(255,255,255,0.1)",r.style.borderColor=this.currentSession.isMuted?"#ef4444":"rgba(255,255,255,0.2)");const m=this.modalEl.querySelector("#spBtnSpeaker");m&&(m.style.background=this.currentSession.isSpeaker?"rgba(56,189,248,0.6)":"rgba(255,255,255,0.1)",m.style.borderColor=this.currentSession.isSpeaker?"#38bdf8":"rgba(255,255,255,0.2)");const p=this.modalEl.querySelector("#spBtnHold");p&&(p.style.background=this.currentSession.isHeld?"rgba(245,158,11,0.6)":"rgba(255,255,255,0.1)",p.style.borderColor=this.currentSession.isHeld?"#f59e0b":"rgba(255,255,255,0.2)")}async loadLeadContext(e){const t=this.modalEl?.querySelector("#spLeadContextBox");if(!t)return;if(this.currentOptions?.categoryName){const i=this.modalEl?.querySelector("#spMobileCatBadge");i&&(i.textContent=this.currentOptions.categoryName);const n=this.modalEl?.querySelector("#spHeaderCatBadge");n&&(n.textContent=`🏷️ ${this.currentOptions.categoryName}`,n.style.display="inline-block")}if(this.currentOptions?.status){const i=this.modalEl?.querySelector("#spMobileStatus");i&&(i.textContent=this.currentOptions.status.toUpperCase());const n=this.modalEl?.querySelector("#spHeaderStatusBadge");n&&(n.textContent=`📌 ${this.currentOptions.status}`,n.style.display="inline-block")}let a=e;if(!a&&this.currentOptions?.phoneNumber)try{const i=this.currentOptions.phoneNumber.replace(/\D/g,"").slice(-10);if(i.length>=10){const n=await C.get(`/telephony/calls/${i}/customer-history`),s=n?.data??n;s?.lead?.id&&(a=s.lead.id)}}catch(i){console.warn("[SoftphoneModal] Lead lookup by phone notice:",i)}if(!a){this.currentOptions?.categoryName||this.currentOptions?.status?t.style.display="block":t.style.display="none";return}try{const i=await C.get(`/crm/dialer/lead/${a}/detail`),n=i.data??i;if(!n||!n.lead)return;const s=n.lead;t.style.display="block";const l=this.modalEl?.querySelector("#spMobileCatBadge");l&&(l.textContent=s.category_name||"General");const o=this.modalEl?.querySelector("#spHeaderCatBadge");o&&(o.textContent=`🏷️ ${s.category_name||"General"}`,o.style.display="inline-block");const d=this.modalEl?.querySelector("#spMobileSource");d&&(d.textContent=s.source||"—");const r=this.modalEl?.querySelector("#spMobileCompany");r&&(r.textContent=s.company_name||"—");const m=this.modalEl?.querySelector("#spMobileStatus");m&&(m.textContent=(s.status||"—").toUpperCase(),m.style.color=s.status==="won"?"#22c55e":s.status==="lost"?"#ef4444":"#38bdf8");const p=this.modalEl?.querySelector("#spHeaderStatusBadge");p&&(p.textContent=`📌 ${s.status||"New"}`,p.style.display="inline-block");const g=this.modalEl?.querySelector("#spHeaderTempBadge");g&&(s.is_hot_lead?(g.textContent="🔥 HOT LEAD",g.style.background="rgba(239, 68, 68, 0.2)",g.style.color="#ef4444",g.style.border="1px solid rgba(239, 68, 68, 0.4)",g.style.display="inline-block"):s.is_fresh_lead?(g.textContent="🌱 FRESH LEAD",g.style.background="rgba(16, 185, 129, 0.2)",g.style.color="#10b981",g.style.border="1px solid rgba(16, 185, 129, 0.4)",g.style.display="inline-block"):g.style.display="none");const h=this.modalEl?.querySelector("#spMobileStatusUpdated");h&&(h.textContent=s.status_updated_at?new Date(s.status_updated_at).toLocaleDateString("en-IN",{day:"numeric",month:"short"}):"—");const b=this.modalEl?.querySelector("#spMobileBudget");b&&(b.textContent=s.budget_display||"—");const k=this.modalEl?.querySelector("#spMobileLastInteraction");k&&(k.textContent=s.last_interaction_date?new Date(s.last_interaction_date).toLocaleDateString("en-IN",{day:"numeric",month:"short"}):"Never");const P=this.modalEl?.querySelector("#spMobileInteractedBy");P&&(P.textContent=s.last_interacted_by||"—");const _=this.modalEl?.querySelector("#spMobileLastDialed");_&&(_.textContent=s.last_dialed_at?new Date(s.last_dialed_at).toLocaleDateString("en-IN",{day:"numeric",month:"short"}):"Never");const I=this.modalEl?.querySelector("#spMobileReqRow"),R=this.modalEl?.querySelector("#spMobileRequirements");I&&R&&(s.requirements?(R.textContent=s.requirements,I.style.display="block"):I.style.display="none");const A=this.modalEl?.querySelector("#spMobileNotesSection"),D=this.modalEl?.querySelector("#spMobileRecentNotes");if(A&&D){const T=(n.notes||[]).slice(0,2);T.length>0?(D.innerHTML=T.map(L=>`<div>• ${L.note}</div>`).join(""),A.style.display="block"):A.style.display="none"}}catch(i){console.warn("[SoftphoneModal] Could not fetch lead context:",i)}}}const ye=new Z,O={"/staff/dashboard":"dashboard","/staff/my-attendance":"attendance","/staff/my-leaves":"leaves","/staff/leave-approvals":"staff-leave-approvals","/staff/attendance-records":"team-attendance","/staff/attendance-sheet":"staff-attendance-sheet","/staff/attendance-reports":"staff-attendance-reports","/staff/attendance-exceptions":"staff-attendance-exceptions","/staff/attendance-computation":"staff-attendance-computation","/staff/tasks/assigned-by-me":"tasks-assigned","/staff/tasks/assigned-by-me-v2":"tasks-assigned","/staff/tasks/assigned-to-me":"tasks-received","/staff/tasks/team-activities":"staff-team-activities","/staff/tasks/task-tracker":"staff-task-tracker","/staff/tasks/task-reviews":"staff-task-reviews","/staff/task-review":"staff-task-reviews","/staff/my-kras":"kras","/staff/kra-templates":"staff-kra-templates","/staff/kra-tracking-sheet":"staff-kra-tracking","/staff/kra-review":"staff-kra-review","/staff/my-timesheet":"timesheet","/staff/timesheet-approval":"staff-timesheet-approval","/staff/my-journeys":"journeys","/staff/team-journeys":"team-journeys","/staff/all-journeys":"staff-all-journeys","/staff/vgk4u-journeys":"staff-vgk4u-journeys","/staff/vgk/members":"staff-vgk-members","/staff_vgk_members.html":"staff-vgk-members","/staff/incentives/vgk4u":"staff-incentives-vgk4u","/staff/vgk4u/real-estate":"staff-vgk4u-real-estate","/staff/vgk4u/insurance":"staff-vgk4u-insurance","/staff/vgk4u/etc-students":"staff-vgk4u-real-estate","/staff/incentives/points":"staff-incentives-points","/staff/incentives/approvals":"staff-incentives-approvals","/staff/vgk/income":"staff-vgk-income","/staff/vgk/income-unified":"vgk-income-unified","/staff/vgk/coupons/available":"staff-vgk-coupons","/staff/vgk/promo-codes":"staff-vgk-promo-codes","/staff/vgk/bonanza-management":"vgk-bonanza-rewards","/staff/vgk/bonanza-claims":"vgk-bonanza-rewards","/staff/vgk/vendors":"staff-vgk-vendors","/staff/vgk/vendor-categories":"staff-vgk-vendors","/staff/vgk/vendor-products":"staff-vgk-vendors","/staff/vgk/vendor-transactions":"staff-vgk-vendors","/staff/vgk/cash-income/sales":"staff-vgk-income","/staff/vgk/cash-income/accounts":"staff-vgk-income","/staff/vgk/wallet":"vgk-points-balance","/staff/vgk/config":"staff-vgk-members","/staff/vgk/partner-kyc-review":"staff-kyc-approvals","/staff/vgk/my-registrations":"vgk-my-registrations","/staff/vgk/media":"vgk-member-hub","/staff/vgk4u/purchase-orders":"staff-service-procurement","/rvz/real-dreams/marketplace":"real-dreams-marketplace","/rvz/real-dreams":"real-dreams-marketplace","/rvz/real-dreams/partners":"real-dreams-marketplace","/rvz/real-dreams-partners":"real-dreams-marketplace","/rvz/real-dreams/properties":"real-dreams-marketplace","/rvz/real-dreams-properties":"real-dreams-marketplace","/rvz/real-dreams-dashboard":"real-dreams-marketplace","/staff/mnr/real-dreams/marketplace":"real-dreams-marketplace","/staff/mnr/real-dreams":"real-dreams-marketplace","/staff/mnr/real-dreams/partners":"real-dreams-marketplace","/staff/mnr/real-dreams/properties":"real-dreams-marketplace","/staff/mnr/real-dreams-dashboard":"real-dreams-marketplace","/real-dreams/marketplace":"real-dreams-marketplace","/real-dreams/compare":"real-dreams-marketplace","/real-dreams/property":"real-dreams-marketplace","/staff/zynova/direct":"vgk-direct-summary","/staff/zynova/matching":"vgk-matching-summary","/staff/zynova/guru":"vgk-guru-summary","/staff/zynova/ved":"vgk-ved-summary","/staff/zynova/wallet":"vgk-points-balance","/staff/zynova/withdrawals":"vgk-points-balance","/staff/zynova/points":"vgk-points-balance","/staff/kra-status":"kras","/staff/timesheet":"timesheet","/staff/progress":"progress","/vgk/birthdays":"vgk-birthdays","/vgk/top-earners":"vgk-top-earners","/vgk/awards":"vgk-awards","/vgk/my-registrations":"vgk-my-registrations","/vgk/bonanza-rewards":"vgk-bonanza-rewards","/vgk/points-balance":"vgk-points-balance","/vgk/member-hub":"vgk-member-hub","/vgk/settings":"vgk-settings","/vgk/bank-details":"vgk-bank-details","/vgk/profile-edit":"vgk-profile-edit","/vgk/kyc":"vgk-kyc","/vgk/feedback":"vgk-feedback","/vgk/announcements":"vgk-announcements","/vgk/my-announcements":"vgk-my-announcements","/vgk/coupon-activate":"vgk-coupon-activate","/vgk/coupon-progress":"vgk-coupon-progress","/vgk/coupon-transfer":"vgk-coupon-transfer","/vgk/income-unified":"vgk-income-unified","/vgk/daywise-income":"vgk-daywise-income","/vgk/income-types":"vgk-income-types","/vgk/direct-summary":"vgk-direct-summary","/vgk/matching-summary":"vgk-matching-summary","/vgk/guru-summary":"vgk-guru-summary","/vgk/ved-summary":"vgk-ved-summary","/vgk/ev-benefits":"vgk-ev-benefits","/vgk/ev-discount":"vgk-ev-discount","/vgk/franchise-earnings":"vgk-franchise-earnings","/vgk/insurance":"vgk-insurance","/vgk/training":"vgk-training","/vgk/coupon-benefits":"vgk-coupon-benefits","/vgk/my-submissions":"vgk-my-submissions","/staff/my-reimbursement-claims":"reimbursements","/staff/reimbursement-approvals":"staff-reimbursement-approvals","/staff/accounts/my-reimbursements":"reimbursements","/staff/accounts/reimbursement-approvals":"staff-reimbursement-approvals","/staff/accounts/expense-entries":"staff-expense-entries","/staff/my-earnings":"staff-my-earnings","/staff/payroll-profile":"staff-payroll-profile","/staff/salary-slips":"staff-salary-slips","/staff/my-leads":"staff-my-leads","/staff/leads":"staff-leads","/staff/team-leads":"staff-team-leads","/staff/lead-sources":"staff-lead-sources","/staff/bank-wise-leads":"staff-bank-wise-leads","/staff/crm/bank-wise-leads":"staff-bank-wise-leads","/staff/field-sales":"staff-bank-wise-leads","/field-sales":"staff-bank-wise-leads","field-sales":"staff-bank-wise-leads","bank-wise-leads":"staff-bank-wise-leads","/staff/solar-leads":"category-leads-master","/staff/real-dreams-leads":"category-leads-master","/staff/insurance-leads":"category-leads-master","/staff/ev-b2b-leads":"category-leads-master","/staff/ev-b2c-leads":"category-leads-master","/staff/ev-spares-leads":"category-leads-master","/staff/etc-leads":"category-leads-master","/staff/mnr-leads":"category-leads-master","/staff/mnr-leads-master":"category-leads-master","/staff/executive-dashboard":"executive-dashboard","/staff/crm/whatsapp-inbox":"staff-whatsapp","/staff/crm/wa-inbox":"staff-whatsapp","/staff/whatsapp":"staff-whatsapp","/staff/whatsapp-inbox":"staff-whatsapp","/staff/whatsapp-center":"staff-whatsapp","/staff/crm/whatsapp-center":"staff-whatsapp","/staff/crm/whatsapp":"staff-whatsapp","/staff/configuration/catalog":"digital-catalog","/staff/catalog-library":"digital-catalog","/staff/catalog":"digital-catalog","/catalog-library":"digital-catalog","catalog-library":"digital-catalog","/staff/catalog-library.html":"digital-catalog","/catalog-library.html":"digital-catalog","/catalog":"digital-catalog",catalog:"digital-catalog","/staff/call-tracking":"staff-call-tracking","/staff/vendors":"staff-vendors","/staff/zynova-real-estate":"staff-zynova-real-estate","/staff/zynova":"staff-zynova","/staff/zynova-insurance":"staff-zynova-insurance","/staff/settings":"settings","/staff/change-password":"change-password","/staff/employees":"staff-employees","/staff/training-videos":"staff-training-videos","/staff/employee-directory":"staff-directory","/staff/kyc-approvals":"staff-kyc-approvals","/staff/manager-review":"staff-review","/staff/auto-dialer":"auto-dialer","/staff/call-history":"call-history","/staff/operator-calls":"operator-calls","/staff/day-planner":"day-planner","/staff/tasks/day-planner":"day-planner","/staff/service":"staff-service","/staff/crm":"staff-crm","/staff/crm/dashboard":"staff-crm","/staff/crm/team-leads":"staff-team-leads","/staff/crm/lead-sources":"staff-lead-sources","/staff/call-management":"staff-call-tracking","/staff/dialer":"auto-dialer","/staff/softphone":"softphone","/staff/calling-page":"softphone","/staff/calling":"softphone","/staff/phone-dialpad":"softphone","/staff/softphone-hub":"softphone","/staff/tasks/tracker":"staff-task-tracker","/staff/service-tickets/dashboard":"staff-service","/staff/service-tickets/performance":"staff-service-performance","/staff/service-tickets/procurement":"staff-service-procurement","/staff/service-tickets/procurement-queue":"staff-service-procurement-queue","/staff/service-tickets/raise":"staff-tickets","/staff/service-tickets/reports":"staff-service-reports","/staff/service-tickets/queue":"staff-service-queue","/staff/service-center-revenue":"staff-service-revenue"},Q={"/staff/solar-leads":"solar","/staff/ev-b2b-leads":"ev-b2b","/staff/ev-b2c-leads":"ev-b2c","/staff/ev-spares-leads":"ev-spares","/staff/real-dreams-leads":"real-dreams","/staff/insurance-leads":"insurance","/staff/etc-leads":"etc","/staff/mnr-leads":"mnr"},X=[{menu_code:"HOME",label:"Home",route:"dashboard"},{menu_code:"PROGRESS_DASHBOARD",label:"Progress Dashboard",route:"progress"},{menu_code:"DAY_PLANNER",label:"Day Planner",route:"day-planner"}],J=[{menu_code:"VGK_DASHBOARD",label:'<i class="fas fa-home" style="margin-right: 8px; width: 18px; text-align: center;"></i> Dashboard',route:"vgk-member-hub",tab:"earnings"},{menu_code:"VGK_PROFILE",label:'<i class="fas fa-user" style="margin-right: 8px; width: 18px; text-align: center;"></i> Profile',route:"vgk-member-hub",tab:"profile"},{menu_code:"VGK_MYCARD",label:'<i class="fas fa-id-card" style="margin-right: 8px; width: 18px; text-align: center;"></i> My Card &amp; Progress',route:"vgk-member-hub",tab:"mycard"},{menu_code:"VGK_ADDMEMBER",label:'<i class="fas fa-user-plus" style="margin-right: 8px; width: 18px; text-align: center;"></i> Add Channel Partner',route:"vgk-member-hub",tab:"addmember"},{menu_code:"VGK_COUPONS",label:'<i class="fas fa-ticket-alt" style="margin-right: 8px; width: 18px; text-align: center;"></i> Coupons',route:"vgk-member-hub",tab:"coupons"},{menu_code:"VGK_NETWORK",label:'<i class="fas fa-sitemap" style="margin-right: 8px; width: 18px; text-align: center;"></i> Team',route:"vgk-member-hub",tab:"network"},{menu_code:"VGK_POINTS",label:'<i class="fas fa-coins" style="margin-right: 8px; width: 18px; text-align: center;"></i> Points Balance',route:"vgk-member-hub",tab:"points"},{menu_code:"VGK_LEDGER",label:'<i class="fas fa-rupee-sign" style="margin-right: 8px; width: 18px; text-align: center;"></i> My Earnings',route:"vgk-member-hub",tab:"ledger"},{menu_code:"VGK_LEADS",label:'<i class="fas fa-user-tag" style="margin-right: 8px; width: 18px; text-align: center;"></i> My Leads',route:"vgk-member-hub",tab:"leads"},{menu_code:"VGK_TICKETS",label:'<i class="fas fa-tools" style="margin-right: 8px; width: 18px; text-align: center;"></i> Service Tickets',route:"vgk-member-hub",tab:"tickets"},{menu_code:"VGK_BONANZA",label:'<i class="fas fa-trophy" style="margin-right: 8px; width: 18px; text-align: center;"></i> Bonanza Rewards',route:"vgk-member-hub",tab:"bonanza"},{menu_code:"VGK_VENDORS",label:'<i class="fas fa-store" style="margin-right: 8px; width: 18px; text-align: center;"></i> Vendor Shops',route:"vgk-member-hub",tab:"vendors"},{menu_code:"VGK_MEDIA",label:'<i class="fas fa-photo-video" style="margin-right: 8px; width: 18px; text-align: center;"></i> Media Hub',route:"vgk-member-hub",tab:"media"},{menu_code:"VGK_ORDERS",label:'<i class="fas fa-box" style="margin-right: 8px; width: 18px; text-align: center;"></i> Orders',route:"vgk-member-hub",tab:"orders"}],ee=[{section_code:"EARNINGS",section_label:"EARNINGS & INCOME",order:1,items:[{menu_code:"VGK_INCOME_UNIFIED",label:'<i class="fas fa-chart-line" style="margin-right: 8px; width: 18px; text-align: center; color: #10b981;"></i>Income Dashboard',route:"vgk-income-unified"},{menu_code:"VGK_DAYWISE_INCOME",label:'<i class="fas fa-calendar-day" style="margin-right: 8px; width: 18px; text-align: center; color: #3b82f6;"></i>Daywise Income',route:"vgk-daywise-income"},{menu_code:"VGK_DIRECT_SUMMARY",label:'<i class="fas fa-users" style="margin-right: 8px; width: 18px; text-align: center; color: #6366f1;"></i>Direct (L1)',route:"vgk-direct-summary"},{menu_code:"VGK_MATCHING_SUMMARY",label:'<i class="fas fa-sitemap" style="margin-right: 8px; width: 18px; text-align: center; color: #8b5cf6;"></i>Matching (L2)',route:"vgk-matching-summary"},{menu_code:"VGK_GURU_SUMMARY",label:'<i class="fas fa-graduation-cap" style="margin-right: 8px; width: 18px; text-align: center; color: #ec4899;"></i>Guru Summary',route:"vgk-guru-summary"},{menu_code:"VGK_VED_SUMMARY",label:'<i class="fas fa-brain" style="margin-right: 8px; width: 18px; text-align: center; color: #f59e0b;"></i>Ved Summary',route:"vgk-ved-summary"},{menu_code:"VGK_FRANCHISE_EARNINGS",label:'<i class="fas fa-store" style="margin-right: 8px; width: 18px; text-align: center; color: #14b8a6;"></i>Franchise Earnings',route:"vgk-franchise-earnings"}]},{section_code:"PROGRAMS",section_label:"PROGRAMS & BENEFITS",order:2,items:[{menu_code:"VGK_EV_BENEFITS",label:'<i class="fas fa-charging-station" style="margin-right: 8px; width: 18px; text-align: center; color: #10b981;"></i>EV Benefits',route:"vgk-ev-benefits"},{menu_code:"VGK_EV_DISCOUNT",label:'<i class="fas fa-percent" style="margin-right: 8px; width: 18px; text-align: center; color: #06b6d4;"></i>EV Discount',route:"vgk-ev-discount"},{menu_code:"VGK_INSURANCE",label:'<i class="fas fa-shield-alt" style="margin-right: 8px; width: 18px; text-align: center; color: #3b82f6;"></i>Insurance Policy',route:"vgk-insurance"},{menu_code:"VGK_TRAINING",label:'<i class="fas fa-chalkboard-teacher" style="margin-right: 8px; width: 18px; text-align: center; color: #8b5cf6;"></i>Training Program',route:"vgk-training"},{menu_code:"VGK_BONANZA_REWARDS",label:'<i class="fas fa-trophy" style="margin-right: 8px; width: 18px; text-align: center; color: #f59e0b;"></i>Bonanza Rewards',route:"vgk-bonanza-rewards"},{menu_code:"VGK_AWARDS",label:'<i class="fas fa-award" style="margin-right: 8px; width: 18px; text-align: center; color: #eab308;"></i>Awards & Milestones',route:"vgk-awards"}]},{section_code:"COUPONS_PINS",section_label:"COUPONS & PINS",order:3,items:[{menu_code:"VGK_COUPON_ACTIVATE",label:'<i class="fas fa-key" style="margin-right: 8px; width: 18px; text-align: center; color: #6366f1;"></i>PIN Activation',route:"vgk-coupon-activate"},{menu_code:"VGK_COUPON_PROGRESS",label:'<i class="fas fa-tasks" style="margin-right: 8px; width: 18px; text-align: center; color: #3b82f6;"></i>Coupon Progress',route:"vgk-coupon-progress"},{menu_code:"VGK_COUPON_TRANSFER",label:'<i class="fas fa-exchange-alt" style="margin-right: 8px; width: 18px; text-align: center; color: #10b981;"></i>Coupon Transfer',route:"vgk-coupon-transfer"},{menu_code:"VGK_COUPON_BENEFITS",label:'<i class="fas fa-gift" style="margin-right: 8px; width: 18px; text-align: center; color: #ec4899;"></i>Coupon Benefits',route:"vgk-coupon-benefits"}]},{section_code:"PROFILE_SECURITY",section_label:"MY ACCOUNT",order:4,items:[{menu_code:"VGK_PROFILE_EDIT",label:'<i class="fas fa-user-edit" style="margin-right: 8px; width: 18px; text-align: center; color: #3b82f6;"></i>Edit Profile',route:"vgk-profile-edit"},{menu_code:"VGK_KYC",label:'<i class="fas fa-id-card" style="margin-right: 8px; width: 18px; text-align: center; color: #10b981;"></i>KYC Verification',route:"vgk-kyc"},{menu_code:"VGK_BANK_DETAILS",label:'<i class="fas fa-university" style="margin-right: 8px; width: 18px; text-align: center; color: #f59e0b;"></i>Bank Details',route:"vgk-bank-details"},{menu_code:"VGK_POINTS_BALANCE",label:'<i class="fas fa-coins" style="margin-right: 8px; width: 18px; text-align: center; color: #eab308;"></i>Points Balance',route:"vgk-points-balance"},{menu_code:"VGK_FEEDBACK",label:'<i class="fas fa-comment-dots" style="margin-right: 8px; width: 18px; text-align: center; color: #06b6d4;"></i>Feedback',route:"vgk-feedback"},{menu_code:"VGK_SETTINGS",label:'<i class="fas fa-cog" style="margin-right: 8px; width: 18px; text-align: center; color: #64748b;"></i>Settings',route:"vgk-settings"}]},{section_code:"COMMUNITY",section_label:"COMMUNITY & TEAM",order:5,items:[{menu_code:"VGK_TOP_EARNERS",label:'<i class="fas fa-medal" style="margin-right: 8px; width: 18px; text-align: center; color: #f59e0b;"></i>Top Earners',route:"vgk-top-earners"},{menu_code:"VGK_BIRTHDAYS",label:'<i class="fas fa-birthday-cake" style="margin-right: 8px; width: 18px; text-align: center; color: #ec4899;"></i>Birthdays',route:"vgk-birthdays"},{menu_code:"VGK_ANNOUNCEMENTS",label:'<i class="fas fa-bullhorn" style="margin-right: 8px; width: 18px; text-align: center; color: #3b82f6;"></i>Announcements',route:"vgk-announcements"},{menu_code:"VGK_MY_REGISTRATIONS",label:'<i class="fas fa-user-plus" style="margin-right: 8px; width: 18px; text-align: center; color: #10b981;"></i>My Registrations',route:"vgk-my-registrations"},{menu_code:"VGK_MY_SUBMISSIONS",label:'<i class="fas fa-file-invoice" style="margin-right: 8px; width: 18px; text-align: center; color: #8b5cf6;"></i>My Submissions',route:"vgk-my-submissions"}]}];class te{container=null;overlay=null;isOpen=!1;expandedSections=new Set;allowedPaths="*";isSupremeStaff=!1;isStaffMenuLoaded=!1;constructor(){try{if(localStorage.getItem("mnr_staff_is_supreme_cache")==="true")this.isSupremeStaff=!0,this.allowedPaths="*",this.isStaffMenuLoaded=!0;else{const t=localStorage.getItem("mnr_staff_allowed_paths_cache");if(t){const a=JSON.parse(t);Array.isArray(a)&&(this.allowedPaths=new Set(a),this.isStaffMenuLoaded=!0)}}}catch{}this.createElements(),this.loadStaffMenus(),window.addEventListener("logout",()=>{this.allowedPaths="*",this.isSupremeStaff=!1,this.isStaffMenuLoaded=!1;try{localStorage.removeItem("mnr_staff_allowed_paths_cache"),localStorage.removeItem("mnr_staff_is_supreme_cache"),localStorage.removeItem("mnr_staff_menu_tree_cache")}catch{}this.updateUI()}),window.addEventListener("auth-changed",()=>{this.isStaffMenuLoaded=!1,this.loadStaffMenus()})}createElements(){if(this.overlay=document.createElement("div"),this.overlay.className="drawer-overlay",this.overlay.addEventListener("click",()=>this.close()),document.body.appendChild(this.overlay),this.container=document.createElement("div"),this.container.className="side-drawer",this.container.innerHTML=this.render(),document.body.appendChild(this.container),!document.getElementById("myntos-drawer-styles")){const e=document.createElement("style");e.id="myntos-drawer-styles",e.textContent=`
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
      `,document.head.appendChild(e)}this.attachEventListeners()}render(){const e=$.getPortal(),t=e==="vgk",i=y.getAuthState().user||{},n=(i.role_code||i.role?.role_code||i.user_type||"").toString().toLowerCase().trim(),s=(i.role_name||i.role?.role_name||"").toString().toUpperCase().trim(),l=(i.staff_type||"").toString().toUpperCase().trim();["vgk4u","vgk4u_supreme","key_leadership","ea","executive_admin","manager","director","admin"].includes(n)||n.includes("vgk")||n.includes("manager")||n.includes("lead")||["VGK4U","VGK4U SUPREME","VGK MENTOR","KEY LEADERSHIP","EA","EXECUTIVE ADMIN","MANAGER"].includes(s)||s.includes("VGK")||s.includes("MANAGER")||["VGK4U","VGK4U SUPREME"].includes(l)||(i.is_manager||i.is_admin||i.is_super_admin);let o=X;if(t)o=J;else if(e==="staff"){const r=["vgk4u","vgk4u_supreme","key_leadership","ea","executive_admin"].includes(n)||n.includes("vgk")||["VGK4U","VGK4U SUPREME","VGK MENTOR","KEY LEADERSHIP","EA","EXECUTIVE ADMIN"].includes(s)||s.includes("VGK")||["VGK4U","VGK4U SUPREME"].includes(l);i.staff_type==="FREELANCER"&&i.freelancer_access_mode==="only_leads"?o=[]:o=[{menu_code:"PROGRESS",label:'<i class="fas fa-chart-line" style="margin-right: 8px; width: 18px; text-align: center;"></i> Progress',route:"progress"},...r?[{menu_code:"OVERVIEW",label:'<i class="fas fa-th" style="margin-right: 8px; width: 18px; text-align: center;"></i> Overview',route:"dashboard"}]:[],{menu_code:"TASK_PLANNER",label:'<i class="fas fa-calendar-day" style="margin-right: 8px; width: 18px; text-align: center;"></i> Task Planner',route:"day-planner"},{menu_code:"KRA_STATUS",label:'<i class="fas fa-chart-bar" style="margin-right: 8px; width: 18px; text-align: center;"></i> KRA Status',route:"kras"},{menu_code:"TIME_SHEET",label:'<i class="fas fa-clock" style="margin-right: 8px; width: 18px; text-align: center;"></i> Time Sheet',route:"timesheet"},{menu_code:"WHATSAPP_CENTER",label:'<i class="fab fa-whatsapp" style="margin-right: 8px; width: 18px; text-align: center; color: #25d366;"></i> WhatsApp Center',route:"staff-whatsapp"},{menu_code:"AUTO_DIALER",label:'<i class="fas fa-phone-volume" style="margin-right: 8px; width: 18px; text-align: center; color: #38bdf8;"></i> Auto Dialer',route:"auto-dialer"},{menu_code:"CALLING_PAGE",label:'<i class="fas fa-headset" style="margin-right: 8px; width: 18px; text-align: center; color: #3b82f6;"></i> Calling & Softphone',route:"softphone"}]}["account","accounts","finance","payroll","billing","bookkeeper","auditor"].some(r=>n.includes(r))||["ACCOUNT","ACCOUNTS","FINANCE","PAYROLL","BILLING","BOOKKEEPER","AUDITOR"].some(r=>s.includes(r))||["ACCOUNT","ACCOUNTS","FINANCE","PAYROLL","BILLING","BOOKKEEPER","AUDITOR"].some(r=>l.includes(r))||["ACCOUNT","ACCOUNTS","FINANCE","PAYROLL"].some(r=>(i.department||i.department_name||"").toString().toUpperCase().includes(r));const d=t?ee:this.getStaffMenuMaster();return`
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
          ${o.map(r=>`
            <div class="menu-item top-item" data-route="${r.route}" ${r.tab?`data-tab="${r.tab}"`:""}>
              <span class="menu-label">${r.label}</span>
            </div>
          `).join("")}
        </div>
        <!-- Section menus -->
        ${d.map(r=>this.renderSection(r)).join("")}
        
        ${t?`
          <div class="drawer-divider" style="height: 1px; background: rgba(255,255,255,0.1); margin: 12px 16px;"></div>
          <div class="menu-item top-item logout-item" id="drawerLogout" style="color: #ef4444; cursor: pointer; display: flex; align-items: center; padding: 12px 24px;">
            <span class="menu-label" style="display: flex; align-items: center; gap: 8px; font-weight: 500; font-size: 1rem;">
              <i class="fas fa-sign-out-alt" style="width: 18px; text-align: center;"></i> Logout
            </span>
          </div>
        `:""}
      </div>
    `}renderSection(e){const t=this.expandedSections.has(e.section_code),a=e.subSections&&e.subSections.length>0,i=e.items&&e.items.length>0;return!a&&!i?"":`
      <div class="drawer-section" data-section="${e.section_code}">
        <div class="section-header" data-toggle="${e.section_code}">
          <span class="section-title">${e.section_label}</span>
          <svg class="section-arrow" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">${t?'<polyline points="6 9 12 15 18 9"/>':'<polyline points="9 18 15 12 9 6"/>'}</svg>
        </div>
        <div class="section-items ${t?"expanded":""}" style="display: ${t?"block":"none"};">
          ${i?e.items.map(n=>this.renderMenuItem(n)).join(""):""}
          ${a?e.subSections.map(n=>this.renderSubSection(n)).join(""):""}
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
      <a class="drawer-menu-item" data-route="${e.route}"${e.tab?` data-tab="${e.tab}"`:""}>
        <span class="menu-label">${e.label}</span>
      </a>
    `}attachEventListeners(){this.container&&(document.getElementById("drawerClose")?.addEventListener("click",()=>this.close()),this.container.querySelectorAll("[data-toggle]").forEach(e=>{e.addEventListener("click",t=>{const a=e.dataset.toggle;this.toggleSection(a),t.stopPropagation()})}),this.container.querySelectorAll("[data-route]").forEach(e=>{e.addEventListener("click",()=>{const t=e.dataset.route,a=e.dataset.tab;let i=O[t]||O[t.replace(/\/$/,"")];i||(t.startsWith("/staff/")?i=t.replace("/staff/","").replace(/\//g,"-"):i=t),a?M.navigate(i,{tab:a}):M.navigate(i),this.close()})}),document.getElementById("drawerLogout")?.addEventListener("click",async()=>{this.close(),confirm("Are you sure you want to logout?")&&await y.logout()}))}toggleSection(e){this.expandedSections.has(e)?this.expandedSections.delete(e):this.expandedSections.add(e),this.updateUI()}updateUI(){this.container&&(this.container.innerHTML=this.render(),this.attachEventListeners())}async loadStaffMenus(){const t=y.getAuthState().user||{},a=(t.staff_type||"").toString().toUpperCase().trim(),i=(t.emp_code||t.employee_code||"").toString().toUpperCase().trim(),n=(t.role_code||t.role?.role_code||t.user_type||"").toString().toLowerCase().trim(),s=(t.role_name||t.role?.role_name||"").toString().toUpperCase().trim(),l=["VGK4U_SUPREME","RVZ_SUPREME","VGK4U","VGK4U SUPREME","VGK4U_EA","KEY_LEADERSHIP","KEY LEADERSHIP","EA","EXECUTIVE ADMIN","MANAGER","DIRECTOR","SUPER_ADMIN","ADMIN"];if(l.includes(a)||["MR10018","MR10001","MR10016","MR10025"].includes(i)||["key_leadership","vgk4u","ea","vgk4u_supreme","executive_admin","manager","director","admin","super_admin"].includes(n)||l.includes(s)||(t.is_manager||t.is_admin||t.is_super_admin)){this.isSupremeStaff=!0,this.allowedPaths="*",this.isStaffMenuLoaded=!0;try{localStorage.setItem("mnr_staff_is_supreme_cache","true")}catch{}this.updateUI();return}try{const o=await C.get("/staff/menu-settings/my-menus?unified=true");if(o.success&&o.data){const d=o.data.menus||[],r=new Set(d.map(m=>m.route_path).filter(m=>!!m));r.add("/staff/whatsapp-center"),r.add("/staff/crm/whatsapp-inbox"),r.add("/staff/crm/whatsapp-bot"),r.add("/staff/softphone-center"),r.add("/staff/softphone-hub"),r.add("/staff/softphone"),r.add("/staff/dialer"),r.add("/staff/auto-dialer"),r.add("/staff/my-leads"),r.add("/staff/configuration/catalog"),r.add("/staff/catalog-library"),r.add("/staff/catalog"),this.allowedPaths=r,this.isSupremeStaff=!1,this.isStaffMenuLoaded=!0;try{localStorage.setItem("mnr_staff_is_supreme_cache","false"),localStorage.setItem("mnr_staff_allowed_paths_cache",JSON.stringify(Array.from(r)))}catch{}this.updateUI()}}catch(o){console.error("Failed to load dynamic staff menus:",o),this.allowedPaths="*",this.updateUI()}}getItemIcon(e,t){const a=(e||"").toUpperCase(),i=(t||"").toLowerCase();return a.includes("WHATSAPP")||i.includes("whatsapp")?"fab fa-whatsapp":a.includes("AUTO_DIALER")||i.includes("auto dialer")?"fas fa-phone-volume":a.includes("SOFTPHONE")||i.includes("calling")||i.includes("softphone")?"fas fa-headset":a.includes("CATALOG")||i.includes("catalog")?"fas fa-book-open":a.includes("FIELD_SALES")||i.includes("field sales")||a.includes("BANK_WISE_LEADS")?"fas fa-users-gear":a.includes("SOLAR")||i.includes("solar")?"fas fa-solar-panel":a.includes("EV_")||i.includes("ev ")?"fas fa-car":a.includes("INSURANCE")||i.includes("care")||i.includes("insurance")?"fas fa-shield-alt":a.includes("REAL_DREAMS")||a.includes("REAL_ESTATE")||i.includes("real dreams")||i.includes("real estate")||i.includes("property")?"fas fa-building":a.includes("ETC")||i.includes("training")||i.includes("student")?"fas fa-graduation-cap":a.includes("BONANZA")||i.includes("bonanza")?"fas fa-trophy":a.includes("COUPON")||a.includes("PIN")||i.includes("coupon")||i.includes("pin")?"fas fa-ticket-alt":a.includes("PROMO")||i.includes("promo")?"fas fa-tags":a.includes("VENDOR")||i.includes("vendor")?"fas fa-store":a.includes("WALLET")||i.includes("wallet")?"fas fa-wallet":a.includes("INCOME")||i.includes("earnings")||i.includes("income")?"fas fa-hand-holding-usd":a.includes("POINTS")||i.includes("points")?"fas fa-coins":a.includes("APPROVAL")||i.includes("approval")?"fas fa-clipboard-check":a.includes("KYC")||i.includes("kyc")?"fas fa-id-card":a.includes("TRANSACTION")||i.includes("transaction")?"fas fa-receipt":a.includes("MEMBER")||a.includes("TEAM")||i.includes("member")||i.includes("team")?"fas fa-users":a.includes("ATTENDANCE")||i.includes("attendance")?"fas fa-clock":a.includes("LEAVE")||i.includes("leave")?"fas fa-calendar-times":a.includes("TASK")||i.includes("task")?"fas fa-tasks":a.includes("KRA")||i.includes("kra")?"fas fa-chart-line":a.includes("JOURNEY")||i.includes("journey")?"fas fa-route":a.includes("TICKET")||i.includes("ticket")||i.includes("service")?"fas fa-tools":"fas fa-circle"}getItemIconColor(e,t){const a=(e||"").toUpperCase(),i=(t||"").toLowerCase();return a.includes("WHATSAPP")||i.includes("whatsapp")?"color: #25d366;":a.includes("AUTO_DIALER")||i.includes("auto dialer")||a.includes("SOFTPHONE")||i.includes("softphone")?"color: #38bdf8;":a.includes("CATALOG")||i.includes("catalog")?"color: #10b981;":a.includes("FIELD_SALES")||i.includes("field sales")||a.includes("BANK_WISE_LEADS")?"color: #38bdf8;":a.includes("SOLAR")||i.includes("solar")?"color: #f59e0b;":a.includes("EV_")||i.includes("ev ")?"color: #10b981;":a.includes("INSURANCE")||i.includes("care")||i.includes("insurance")?"color: #059669;":a.includes("REAL_DREAMS")||a.includes("REAL_ESTATE")||i.includes("real dreams")||i.includes("property")?"color: #2563eb;":a.includes("ETC")||i.includes("training")?"color: #8b5cf6;":a.includes("BONANZA")||i.includes("bonanza")?"color: #f59e0b;":a.includes("COUPON")||a.includes("PIN")||i.includes("coupon")||i.includes("pin")?"color: #6366f1;":a.includes("PROMO")||i.includes("promo")?"color: #ec4899;":a.includes("VENDOR")||i.includes("vendor")?"color: #0284c7;":a.includes("WALLET")||i.includes("wallet")||a.includes("INCOME")||i.includes("earnings")||i.includes("income")?"color: #10b981;":a.includes("POINTS")||i.includes("points")?"color: #f59e0b;":a.includes("APPROVAL")||i.includes("approval")?"color: #10b981;":a.includes("KYC")||i.includes("kyc")?"color: #3b82f6;":a.includes("TRANSACTION")||i.includes("transaction")?"color: #0284c7;":a.includes("MEMBER")||a.includes("TEAM")||i.includes("member")||i.includes("team")?"color: #7c3aed;":""}getStaffMenuMaster(){const t=y.getAuthState().user||{},a=(t.emp_code||t.employee_code||"").toString().toUpperCase().trim(),i=(t.role_code||t.role?.role_code||t.user_type||"").toString().toLowerCase().trim(),n=(t.role_name||t.role?.role_name||"").toString().toUpperCase().trim(),s=(t.staff_type||"").toString().toUpperCase().trim(),l=["VGK4U_SUPREME","RVZ_SUPREME","VGK4U","VGK4U SUPREME","VGK4U_EA","KEY_LEADERSHIP","KEY LEADERSHIP","EA","EXECUTIVE ADMIN","MANAGER","DIRECTOR","SUPER_ADMIN","ADMIN"],o=["MR10018","MR10001","MR10025","MR10016"].includes(a)||["SAAS_SEGMENT_ADMIN","SUPER_ADMIN","VGK4U_SUPREME"].includes(s)||["super_admin","saas_segment_admin","tenant_admin","key_leadership","vgk4u"].includes(i),d=this.isSupremeStaff||l.includes(s)||["MR10018","MR10001","MR10016","MR10025"].includes(a)||["key_leadership","vgk4u","ea","vgk4u_supreme"].includes(i)||!!(t.is_manager||t.is_admin||t.is_super_admin),r=["account","accounts","finance","payroll","billing","bookkeeper","auditor"].some(u=>i.includes(u))||["ACCOUNT","ACCOUNTS","FINANCE","PAYROLL","BILLING","BOOKKEEPER","AUDITOR"].some(u=>n.includes(u))||["ACCOUNT","ACCOUNTS","FINANCE","PAYROLL","BILLING","BOOKKEEPER","AUDITOR"].some(u=>s.includes(u))||["ACCOUNT","ACCOUNTS","FINANCE","PAYROLL"].some(u=>(t.department||t.department_name||"").toString().toUpperCase().includes(u)),m=d||r,p=["MN10009","MR10022","MR10036","MR10027","MN10017","MN10016"].includes(a),g=u=>{if(!d&&this.allowedPaths!=="*"){const E=u.route.replace(/\/$/,"");if(!(["/staff/dialer","/staff/auto-dialer","/staff/softphone","/staff/whatsapp-center","/staff/configuration/catalog","/staff/catalog-library","/staff/catalog","/staff/bank-wise-leads","/staff/field-sales","/staff/my-leads"].includes(u.route)||u.route.startsWith("/staff/vgk/"))&&!this.allowedPaths.has(u.route)&&!this.allowedPaths.has(E))return null}if(p&&(u.route==="/staff/leads"||u.menu_code==="STAFF_LEADS"||u.menu_code==="LEADS_MASTER"))return null;let f=O[u.route]||O[u.route.replace(/\/$/,"")];f||(u.route.startsWith("/staff/")?f=u.route.replace("/staff/","").replace(/\//g,"-"):f=u.route);let w=u.label,v=Q[u.route];if(!v){const E=(u.menu_code||"").toUpperCase();E.includes("SOLAR_LEADS")?v="solar":E.includes("EV_B2B")?v="ev-b2b":E.includes("EV_B2C")?v="ev-b2c":E.includes("EV_SPARES")?v="ev-spares":E.includes("REAL_DREAMS")||E.includes("ZYN_REAL_ESTATE")?v="real-dreams":E.includes("INSURANCE")||E.includes("ZYN_INSURANCE")?v="insurance":E.includes("ETC_LEADS")?v="etc":E.includes("MNR_LEADS")&&(v="mnr")}let B="";if(!w.startsWith("<i class=")){const E=u.icon||this.getItemIcon(u.menu_code,w),K=this.getItemIconColor(u.menu_code,w);B=`<i class="${E}" style="margin-right: 8px; width: 18px; text-align: center; ${K}"></i>`}return{menu_code:u.menu_code,label:`${B}${w}`,route:f,tab:v}},h=[],b=u=>j.find(f=>f.section_code===u),k=b("HR");if(k){const u=[];if(k.subSections)for(const f of k.subSections){const w=f.items.map(g).filter(v=>v!==null);w.length>0&&u.push({sub_section_code:f.sub_section_code,sub_section_label:f.sub_section_label,items:w})}u.length>0&&h.push({section_code:"HR",section_label:"HR",order:2,subSections:u})}const P=b("CRM_LEADS"),_=[];if(P&&P.items)for(const u of P.items){const f=g(u);f&&_.push(f)}_.some(u=>u.route==="auto-dialer")||_.push({menu_code:"AUTO_DIALER",label:'<i class="fas fa-phone-volume" style="margin-right: 8px; width: 18px; text-align: center; color: #38bdf8;"></i>Auto Dialer',route:"auto-dialer"}),_.some(u=>u.route==="softphone")||_.push({menu_code:"SOFTPHONE",label:'<i class="fas fa-headset" style="margin-right: 8px; width: 18px; text-align: center; color: #38bdf8;"></i>Calling & Softphone',route:"softphone"}),_.some(u=>u.route==="digital-catalog")||_.push({menu_code:"DIGITAL_CATALOG",label:'<i class="fas fa-book-open" style="margin-right: 8px; width: 18px; text-align: center; color: #10b981;"></i>Digital Catalog',route:"digital-catalog"}),_.length>0&&h.push({section_code:"CRM_MODULE",section_label:"CRM & LEADS",order:4,items:_});const I=b("TASK_MANAGEMENT");if(I&&I.items){const u=I.items.map(g).filter(f=>f!==null);u.length>0&&h.push({section_code:"TASK_MANAGEMENT",section_label:"TASK MANAGEMENT",order:5,items:u})}const R=b("KRA_MANAGEMENT");if(R&&R.items){const u=R.items.map(g).filter(f=>f!==null);u.length>0&&h.push({section_code:"KRA_MANAGEMENT",section_label:"KRA MANAGEMENT",order:6,items:u})}const A=b("FIELD_LOCATION_TRACKING");if(A&&A.items){const u=A.items.map(g).filter(f=>f!==null);u.length>0&&h.push({section_code:"JOURNEY_TRACKING",section_label:"JOURNEY TRACKING",order:7,items:u})}const D=[{menu_code:"MY_REIMBURSEMENT_CLAIMS",label:'<i class="fas fa-receipt" style="margin-right: 8px; width: 18px; text-align: center; color: #f59e0b;"></i>My Reimbursement Claims',route:"reimbursements"},{menu_code:"REIMBURSEMENT_APPROVALS",label:'<i class="fas fa-file-invoice-dollar" style="margin-right: 8px; width: 18px; text-align: center; color: #10b981;"></i>Reimbursement Approvals',route:"staff-reimbursement-approvals"}];h.push({section_code:"REIMBURSEMENT",section_label:"REIMBURSEMENT",order:8,items:D});const T=b("MYNT_REAL"),L=[];if(T&&T.items)for(const u of T.items){const f=g(u);f&&L.push(f)}L.some(u=>u.route==="staff-bank-wise-leads"||u.menu_code&&u.menu_code.includes("BANK_WISE_LEADS"))||L.splice(1,0,{menu_code:"MNR_BANK_WISE_LEADS",label:'<i class="fas fa-users-gear" style="margin-right: 8px; width: 18px; text-align: center; color: #38bdf8;"></i>Field Sales',route:"staff-bank-wise-leads"}),L.length>0&&h.push({section_code:"WORKFLOWS",section_label:"WORK FLOWS",order:9,items:L});const V=b("SERVICE_TICKETS");if(V&&V.items){const u=V.items.map(g).filter(f=>f!==null);u.length>0&&h.push({section_code:"SERVICE_TICKETS",section_label:"SERVICE TICKETS",order:10,items:u})}const U=b("VGK_TEAM");if(U&&U.subSections){const u=[];for(const f of U.subSections){const w=f.items.map(g).filter(v=>v!==null);w.length>0&&u.push({sub_section_code:f.sub_section_code,sub_section_label:f.sub_section_label,items:w})}u.length>0&&h.push({section_code:"VGK_TEAM",section_label:"VGK4U",order:18,subSections:u})}if(m){const u=b("ACCOUNTS");if(u&&u.subSections){const f=[];for(const w of u.subSections){const v=w.items.map(g).filter(B=>B!==null);v.length>0&&f.push({sub_section_code:w.sub_section_code,sub_section_label:w.sub_section_label,items:v})}f.length>0&&h.push({section_code:"ACCOUNTS_EARNINGS",section_label:"FINANCE & EARNINGS",order:25,subSections:f})}}if(o){const u=b("MYNTOS_SAAS");if(u&&u.subSections){const f=[];for(const w of u.subSections){const v=w.items.map(g).filter(B=>B!==null);v.length>0&&f.push({sub_section_code:w.sub_section_code,sub_section_label:w.sub_section_label,items:v})}f.length>0&&h.push({section_code:"MYNTOS_SAAS",section_label:"MYNTOS SAAS",order:99,subSections:f})}}return h}open(){if(this.isOpen)return;$.getPortal()==="staff"&&!this.isStaffMenuLoaded&&this.loadStaffMenus(),this.updateUI(),this.isOpen=!0,this.container?.classList.add("open"),this.overlay?.classList.add("visible"),document.body.style.overflow="hidden"}close(){this.isOpen&&(this.isOpen=!1,this.container?.classList.remove("open"),this.overlay?.classList.remove("visible"),document.body.style.overflow="")}toggle(){this.isOpen?this.close():this.open()}}let G=null;function ae(){return G||(G=new te),G}class F{static render(e){let{title:t,showBack:a=!1,showLogout:i=!1,rightAction:n,subtitle:s,showMenu:l}=e;const o=$.getPortal(),d=M.getCurrentRoute(),r=["progress","dashboard","attendance","journeys","announcements","profile","mnr-dashboard","partner-dashboard","vgk-member-hub"].includes(d);if(l===void 0&&(l=r||!a),o==="vgk"&&(i=!0,!s)){const p=y.getAuthState().user||{},g=p.name||p.partner_name||"",h=p.partner_code||"";(g||h)&&(s=h?`${g} (${h})`:g)}return`
      <header class="page-header" style="display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; background: #0f172a; border-bottom: 1px solid #1e293b; position: sticky; top: 0; z-index: 100;">
        <div class="header-left" style="display: flex; align-items: center; gap: 10px;">
          ${l?`
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
            ${s?`<span class="header-subtitle" style="font-size:11px; color:rgba(255,255,255,0.65); font-weight:500">${s}</span>`:""}
          </div>
        </div>
        <div class="header-right">
          ${n?`
            <button class="header-btn action-btn" id="headerActionBtn">
              ${n.icon}
            </button>
          `:""}
          ${i?`
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
    `}static getPortalDashboard(){const e=$.getPortal();return e==="mnr"?"mnr-dashboard":e==="partner"?"partner-dashboard":e==="vgk"?"vgk-member-hub":"progress"}static attachListeners(e){let{showMenu:t,showBack:a=!1,rightAction:i,showLogout:n=!1}=e;t===void 0&&(t=!!document.getElementById("hamburgerBtn")),$.getPortal()==="vgk"&&(n=!0),t&&document.getElementById("hamburgerBtn")?.addEventListener("click",()=>{ae().open()}),a&&document.getElementById("backBtn")?.addEventListener("click",()=>{M.goBack()||M.navigate(F.getPortalDashboard())}),i&&document.getElementById("headerActionBtn")?.addEventListener("click",i.onClick),n&&document.getElementById("logoutBtn")?.addEventListener("click",async()=>{confirm("Are you sure you want to logout?")&&await y.logout()})}static attachBackHandler(){document.getElementById("backBtn")?.addEventListener("click",()=>{M.goBack()||M.navigate(F.getPortalDashboard())})}}class ve{constructor(e){this.options=e,this.trackPoints=e.trackPoints,this.stops=e.stops||[],this.onViewChange=e.onViewChange}options;map=null;container=null;trackPoints=[];stops=[];routeLine=null;progressLine=null;currentMarker=null;startMarker=null;endMarker=null;stopMarkers=[];currentView="street";tileLayers={};playbackIndex=0;isPlaying=!1;playbackInterval=null;playbackSpeed=2;onViewChange;addressCache=new Map;mount(){if(this.container=document.getElementById(this.options.containerId),!this.container){console.error("[LeafletMap] Container not found:",this.options.containerId);return}this.render(),this.initMap()}render(){this.container&&(this.container.innerHTML=`
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
    `,this.addStyles(),this.attachEventListeners())}initMap(){if(this.trackPoints.length===0||!document.getElementById("leafletMapView"))return;const t=this.trackPoints[0];this.map=S.map("leafletMapView",{zoomControl:!1,attributionControl:!1}).setView([t.latitude,t.longitude],14),S.control.zoom({position:"topright"}).addTo(this.map),this.tileLayers={street:S.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",{maxZoom:19}),satellite:S.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",{maxZoom:19}),terrain:S.tileLayer("https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",{maxZoom:17})},this.tileLayers.street.addTo(this.map),this.drawRoute(),this.fitBounds()}drawRoute(){if(!this.map||this.trackPoints.length<2)return;const e=this.trackPoints.map(o=>[o.latitude,o.longitude]);this.routeLine=S.polyline(e,{color:"rgba(255,255,255,0.3)",weight:4,dashArray:"8, 8"}).addTo(this.map),this.progressLine=S.polyline([],{color:"#00d09c",weight:5,lineCap:"round",lineJoin:"round"}).addTo(this.map);const t=S.divIcon({className:"custom-marker start-marker",html:'<div class="marker-inner">S</div>',iconSize:[28,28],iconAnchor:[14,14]}),a=S.divIcon({className:"custom-marker end-marker",html:'<div class="marker-inner">E</div>',iconSize:[28,28],iconAnchor:[14,14]}),i=this.trackPoints[0],n=i.battery_percentage!==void 0?`<br>🔋 ${i.battery_percentage}%`:"";this.startMarker=S.marker([i.latitude,i.longitude],{icon:t}).bindPopup(`<b>Start Point</b><br>${i.address||"Journey Start"}${n}`).addTo(this.map);const s=this.trackPoints[this.trackPoints.length-1],l=s.battery_percentage!==void 0?`<br>🔋 ${s.battery_percentage}%`:"";this.endMarker=S.marker([s.latitude,s.longitude],{icon:a}).bindPopup(`<b>End Point</b><br>${s.address||"Journey End"}${l}`).addTo(this.map),this.stops.forEach((o,d)=>{const r=this.trackPoints[o.startIndex];if(r){const m=S.divIcon({className:"custom-marker stop-marker",html:`<div class="marker-inner">${d+1}</div>`,iconSize:[24,24],iconAnchor:[12,12]}),p=S.marker([r.latitude,r.longitude],{icon:m}).bindPopup(`<b>Stop ${d+1}</b><br>${o.address||"Unknown location"}<br>Duration: ${this.formatDuration(o.durationMinutes)}`).addTo(this.map);this.stopMarkers.push(p)}}),this.currentMarker=S.circleMarker([i.latitude,i.longitude],{radius:10,color:"#fff",weight:3,fillColor:"#ffc107",fillOpacity:1}).addTo(this.map)}fitBounds(){!this.map||!this.routeLine||this.map.fitBounds(this.routeLine.getBounds(),{padding:[30,30]})}switchView(e){!this.map||this.currentView===e||(this.tileLayers[this.currentView].remove(),this.tileLayers[e].addTo(this.map),this.currentView=e,document.querySelectorAll(".view-btn").forEach(t=>{t.classList.toggle("active",t.getAttribute("data-view")===e)}),this.onViewChange&&this.onViewChange(e))}attachEventListeners(){document.querySelectorAll(".view-btn").forEach(t=>{t.addEventListener("click",()=>{const a=t.getAttribute("data-view");this.switchView(a)})}),document.getElementById("playPauseBtn")?.addEventListener("click",()=>this.togglePlayback()),document.getElementById("resetPlayback")?.addEventListener("click",()=>this.resetPlayback());const e=document.getElementById("playbackSlider");e?.addEventListener("input",()=>{this.playbackIndex=parseInt(e.value),this.updatePlaybackUI()}),document.getElementById("speedBtn")?.addEventListener("click",()=>this.cycleSpeed())}togglePlayback(){const e=document.getElementById("playPauseBtn");this.isPlaying?(this.stopPlayback(),e&&(e.innerHTML='<svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>',e.classList.remove("pause"),e.classList.add("play"))):(this.startPlayback(),e&&(e.innerHTML='<svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg>',e.classList.remove("play"),e.classList.add("pause"))),this.isPlaying=!this.isPlaying}startPlayback(){const e=500/this.playbackSpeed;this.playbackInterval=setInterval(()=>{if(this.playbackIndex<this.trackPoints.length-1)this.playbackIndex++,this.updatePlaybackUI();else{this.stopPlayback(),this.isPlaying=!1;const t=document.getElementById("playPauseBtn");t&&(t.innerHTML='<svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>',t.classList.remove("pause"),t.classList.add("play"))}},e)}stopPlayback(){this.playbackInterval&&(clearInterval(this.playbackInterval),this.playbackInterval=null)}resetPlayback(){this.stopPlayback(),this.playbackIndex=0,this.isPlaying=!1;const e=document.getElementById("playPauseBtn");e&&(e.innerHTML='<svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>',e.classList.remove("pause"),e.classList.add("play")),this.updatePlaybackUI()}cycleSpeed(){const e=[1,2,4,8],t=e.indexOf(this.playbackSpeed);this.playbackSpeed=e[(t+1)%e.length];const a=document.getElementById("speedBtn");a&&(a.textContent=`${this.playbackSpeed}x`),this.isPlaying&&(this.stopPlayback(),this.startPlayback())}updatePlaybackUI(){const e=document.getElementById("playbackSlider"),t=document.getElementById("playbackCounter"),a=document.getElementById("currentLocation"),i=document.getElementById("sliderProgress");e&&(e.value=String(this.playbackIndex)),t&&(t.textContent=`${this.playbackIndex+1} / ${this.trackPoints.length}`);const n=this.trackPoints[this.playbackIndex];a&&n&&(n.address?a.textContent=n.address:(a.textContent="Loading...",this.reverseGeocodeForPlayback(n.latitude,n.longitude,a)));const s=this.playbackIndex/(this.trackPoints.length-1)*100;if(i&&(i.style.width=`${s}%`),this.currentMarker&&n&&this.currentMarker.setLatLng([n.latitude,n.longitude]),this.progressLine){const l=this.trackPoints.slice(0,this.playbackIndex+1).map(o=>[o.latitude,o.longitude]);this.progressLine.setLatLngs(l)}this.map&&n&&this.map.panTo([n.latitude,n.longitude],{animate:!0,duration:.3})}async reverseGeocodeForPlayback(e,t,a){const i=`${e.toFixed(4)},${t.toFixed(4)}`;if(this.addressCache.has(i)){a.textContent=this.addressCache.get(i);return}try{const n=`https://nominatim.openstreetmap.org/reverse?format=json&lat=${e}&lon=${t}&zoom=18`,s=await fetch(n,{headers:{"User-Agent":"MyntReal-Mobile/1.0"}});if(s.ok){const o=(await s.json()).address||{},d=[];for(const m of["road","neighbourhood","suburb","city","town","village"])if(o[m]&&(d.push(o[m]),d.length>=2))break;const r=d.length>0?d.join(", "):`${e.toFixed(4)}, ${t.toFixed(4)}`;this.addressCache.set(i,r),a.textContent==="Loading..."&&(a.textContent=r)}}catch(n){console.warn("[DC_GEOCODE] Playback geocode failed:",n),a.textContent==="Loading..."&&(a.textContent=`${e.toFixed(4)}, ${t.toFixed(4)}`)}}formatDuration(e){if(e<60)return`${Math.round(e)}m`;const t=Math.floor(e/60),a=Math.round(e%60);return a>0?`${t}h ${a}m`:`${t}h`}addStyles(){if(document.getElementById("leaflet-journey-map-styles"))return;const e=document.createElement("style");e.id="leaflet-journey-map-styles",e.textContent=`
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
    `,document.head.appendChild(e)}setPlaybackIndex(e){e<0||e>=this.trackPoints.length||(this.playbackIndex=e,this.updatePlaybackUI())}getPlaybackState(){return{index:this.playbackIndex,total:this.trackPoints.length,isPlaying:this.isPlaying}}destroy(){this.stopPlayback(),this.map&&(this.map.remove(),this.map=null)}}const H={greeting:{label:"👋 Welcome & Introduction",text:`Namaskaram! Thank you for connecting with MyntReal. I am your dedicated relationship manager. Please let me know how I may assist you with your project today.

☀️ Official Digital Catalog:
👉 https://www.myntreal.com/catalog/solar/commercial-residential-solar?lang=te`},bank_update:{label:"🏦 Bank Loan Update",text:"Dear Customer, your bank file is currently under active processing. Our team is following up with the branch for swift approval and sanction."},net_meter:{label:"⚡ Net Meter & EB",text:"Dear Customer, your DISCOM Net Metering and EB service documentation is progressing as scheduled. We will update you once the inspection is cleared."},payment:{label:"💰 Payment / Balance Follow-up",text:"Dear Customer, this is a gentle reminder regarding the pending balance for your project. Kindly arrange the clearance at your earliest convenience."},site_visit:{label:"📍 Location & Site Visit",text:"Dear Customer, our technical field staff is scheduled to visit your site. Kindly let us know if you need to coordinate the visit time."}},N={solar:{name:"Solar Rooftop & EPC",btnLabel:"Solar",segmentSlug:"solar",catalogSlug:"commercial-residential-solar",brochureUrl:"/catalog/mnr-catalog-web.pdf",desc:"Sends personalized Har Ghar Solar Digital Catalog link with 90% savings, ₹78,000 subsidy & ₹1 scheme details.",messages:{te:(c,e)=>`నమస్కారం ${c} గారు! 🙏

MyntReal Har Ghar Solar డిజిటల్ క్యాటలాగ్ & సబ్సిడీ కాలిక్యులేటర్ లింక్ ఇక్కడ చూడవచ్చు:
👉 ${e}

⚡ ముఖ్య వివరాలు:
• కరెంట్ బిల్లు 90% వరకు ఆదా
• ₹78,000 కేంద్ర ప్రభుత్వ సబ్సిడీ (PM Surya Ghar)
• ₹1 కే సోలార్ & సులభ బ్యాంక్ లోన్ EMI ఆప్షన్స్
• Tier-1 బ్రాండ్లు & 25 సంవత్సరాల వారంటీ

పై లింక్ ఓపెన్ చేసి మీ ఇంటి కరెంట్ బిల్లుకు సరిపోయే ప్లాన్ మరియు సేవింగ్స్ కాలిక్యులేట్ చేసుకోగలరు.`,en:(c,e)=>`Namaskaram ${c}! 🙏

Here is your official MyntReal Har Ghar Solar Digital Catalog & Subsidy Estimator link:
👉 ${e}

⚡ Highlights:
• Reduce your power bill by up to 90%
• Up to ₹78,000 Central Govt Subsidy (PM Surya Ghar)
• "Solar for ₹1" zero-collateral bank EMI plans
• Authorized Tier-1 Brands & 25-Year Performance Warranty

Click the link above to calculate your recommended capacity, savings & instant quotation.`,hi:(c,e)=>`नमस्ते ${c} जी! 🙏

MyntReal हर घर सोलर डिजिटल कैटलॉग और सब्सिडी कैलकुलेटर लिंक यहाँ देखें:
👉 ${e}

⚡ मुख्य लाभ:
• बिजली बिल में 90% तक बचत
• ₹78,000 तक केंद्र सरकारी सब्सिडी (PM सूर्य घर योजना)
• ₹1 में सोलर और आसान बैंक लोन ईएमआई
• टियर-1 सोलर ब्रांड्स और 25 साल की वारंटी

कृपया ऊपर दिए गए लिंक पर क्लिक करें और अपनी मासिक बचत की गणना करें।`,ta:(c,e)=>`வணக்கம் ${c}! 🙏

MyntReal ஹர் கர் சோலார் டிஜிட்டல் கேட்லாக் மற்றும் மானிய கால்குலேட்டர் லிங்க்:
👉 ${e}

⚡ முக்கிய சிறப்பம்சங்கள்:
• 90% வரை மின் கட்டண சேமிப்பு
• ₹78,000 மத்திய அரசு மானியம் (PM சூர்யா கர்)
• ₹1 சோலார் & எளிய வங்கி லோன் EMI தவணைகள்
• Tier-1 சோலார் பிராண்டுகள் & 25 வருட வாரண்டி

மேலே உள்ள இணைப்பைக் கிளிக் செய்து உங்கள் மின்சார சேமிப்பைக் கணக்கிடுங்கள்.`}},real_estate:{name:"Premium Real Estate & Townships",btnLabel:"Real Estate",segmentSlug:"real-dreams",catalogSlug:"real-dreams-premium-properties",brochureUrl:"/public/hub/Assets/myntreal_real_dreams_brochure.pdf",desc:"Sends Real Dreams catalog with RERA-approved luxury villas, gated open plots & prime commercial spaces.",messages:{te:(c,e)=>`నమస్కారం ${c} గారు! 🙏

🏡 *VGK Real Dreams — RERA & DTCP ఆమోదిత ప్రీమియం గేటెడ్ టౌన్‌షిప్స్*

మీ కోసం అధికారిక రియల్ డ్రీమ్స్ డిజిటల్ క్యాటలాగ్ లింక్:
👉 ${e}

🌟 *ప్రాజెక్ట్ విశేషాలు & చట్టబద్ధత:*
• 100% RERA & DTCP/VMRDA ఆమోదిత లేఅవుట్స్ & లగ్జరీ విల్లాస్
• తక్షణ స్పాట్ రిజిస్ట్రేషన్ గ్యారెంటీ & 30 సం. క్లియర్ టైటిల్
• SBI, HDFC, ICICI బ్యాంకుల ద్వారా 80% వరకు లోన్ సదుపాయం
• 40+ ఆధునిక వసతులు: 40ft BT రోడ్లు, భూగర్భ విద్యుత్, సోలార్ లైట్లు, క్లబ్‌హౌస్
• ప్లాట్ సైజులు: 167, 200, 267 & 500 చ.గ. (చ.గ. ₹18,500 నుండి)

🛒 *రియల్ డ్రీమ్స్ ఈ-కామ్ మార్కెట్‌ప్లేస్‌లో ప్లాట్స్ చూడండి:*
👉 https://www.myntreal.com/ecom?vertical=real-dreams

ఉచిత VIP సైట్ విజిట్ కోసం సంప్రదించండి.`,en:(c,e)=>`Namaskaram ${c}! 🙏

🏡 *VGK Real Dreams — Verified Gated Communities & Solar Townships*

Here is your official Real Dreams Premium Properties Digital Catalog:
👉 ${e}

🌟 *Project Highlights & Legal Genuineness:*
• 100% RERA & DTCP/VMRDA Approved Gated Villa Layouts
• Immediate Spot Registration Guarantee with 30-year clear legal title
• Bank Loan Approvals up to 80% from SBI, HDFC, and ICICI Bank
• 40+ Lifestyle Amenities: 40ft/33ft BT roads, underground power, solar lighting
• Plot Sizes: 167, 200, 267 & 500 Sq. Yards (from ₹18,500/yd)

🛒 *Browse Live Verified Listings on Real Dreams E-Com:*
👉 https://www.myntreal.com/ecom?vertical=real-dreams

Complimentary chauffeur AC cab pickup available for site visits!`,hi:(c,e)=>`नमस्ते ${c} जी! 🙏

VGK Real Dreams प्रीमियम प्रॉपर्टीज डिजिटल कैटलॉग लिंक:
👉 ${e}

🏡 100% RERA & टाउनशिप अनुमोदित प्लॉट्स एवं विला
• 80% तक बैंक लोन स्वीकृत (SBI, HDFC, ICICI)
• तत्काल रजिस्ट्री एवं स्पष्ट मालिकाना हक

ई-कॉमर्स पर प्लॉट्स देखें: https://www.myntreal.com/ecom?vertical=real-dreams`,ta:(c,e)=>`வணக்கம் ${c}! 🙏

VGK Real Dreams பிரீமியம் ரியல் எஸ்டேட் டிஜிட்டல் கேட்லாக் லிங்க்:
👉 ${e}

100% RERA அங்கீகரிக்கப்பட்ட சொத்துக்கள் & 80% வங்கி கடன் வசதி!
இ-காமர்ஸ் மூலம் பார்வையிட: https://www.myntreal.com/ecom?vertical=real-dreams`}},ev_b2c:{name:"Manthra EV 2-Wheelers & Customer Pricing",btnLabel:"EV 2W Pricing",segmentSlug:"ev-b2c",catalogSlug:"ev-b2c-pricing",brochureUrl:"/public/hub/Assets/myntreal_manthra_ev_brochure.pdf",desc:"Sends official Manthra EV Customer 2W Pricing with 5 models, Graphene (9M) & LFP (3Y) warranties, fuel savings calculator, Solar & Insurance benefits.",messages:{te:(c,e)=>`నమస్కారం ${c} గారు! 🙏

మాంత్రా EV (Manthra EV) అధికారిక 2-వీలర్ ఎలక్ట్రిక్ స్కూటర్లు & కస్టమర్ ధరల పట్టిక:
👉 ${e}

⚡ ప్రధాన ప్రయోజనాలు & 5 సర్టిఫైడ్ మోడల్స్:
• 5 మోడల్స్: Pro GT, Power Plus (200kg హెవీ కార్గో), M99 Flagship, Royal Sling, Beast Pro
• నాన్-RTO లో-స్పీడ్ (<25 km/h) — డ్రైవింగ్ లైసెన్స్ & రిజిస్ట్రేషన్ అవసరం లేదు!
• రన్నింగ్ ఖర్చు కేవలం ₹0.15/కి.మీ — నెలకు ₹3,000+ పెట్రోల్ ఆదా
• గ్రాఫేన్ 48V 30Ah: 9 నెలల బ్యాటరీ & 9 నెలల ఛార్జర్ వారంటీ
• స్మార్ట్ LFP బ్యాటరీలు: 3 సంవత్సరాల సమగ్ర రీప్లేస్‌మెంట్ వారంటీ
• హర్ ఘర్ సోలార్ (PM సూర్య ఘర్ సబ్సిడీ), ఇన్సూరెన్స్ & జెన్యూన్ స్పేర్స్ సదుపాయం

పై లింక్ క్లిక్ చేసి మోడల్-వైజ్ ధరలు, స్పెసిఫికేషన్లు & అధికారిక వీడియో చూడగలరు. ఉచిత టెస్ట్ డ్రైవ్ బుక్ చేసుకోండి!`,en:(c,e)=>`Namaskaram ${c}! 🙏

Here is your official Manthra EV 2-Wheeler Electric Scooters Customer Pricing & Specifications Catalog:
👉 ${e}

⚡ Customer Highlights & 5 Certified Models:
• Models: Pro GT, Power Plus (200kg Cargo), M99 Flagship, Royal Sling & Beast Pro
• Certified Non-RTO Low-Speed (<25 km/h) — Zero Driving License & Zero RTO Needed!
• Ultra-low running cost of ₹0.15 / km — Save ₹3,000+ every month vs petrol
• Graphene 48V 30Ah: 9 Months Battery Warranty & 9 Months Charger Warranty
• Smart LFP: 3 Years Comprehensive Replacement Warranty & Fast Charge
• Integrated Har Ghar Solar (PM Surya Ghar Subsidy), EV Insurance & Spares benefits

Click the link above to explore model-wise prices, interactive savings calculator & official video showcase. Book your free test ride today!`,hi:(c,e)=>`नमस्ते ${c} जी! 🙏

मंत्रा EV (Manthra EV) आधिकारिक 2-व्हीलर इलेक्ट्रिक स्कूटर्स एवं कस्टमर प्राइसिंग कैटलॉग लिंक यहाँ देखें:
👉 ${e}

⚡ मुख्य विशेषताएं एवं 5 मॉडल:
• 5 मॉडल्स: Pro GT, Power Plus (200kg कार्गो), M99 Flagship, Royal Sling और Beast Pro
• प्रमाणित नॉन-RTO (<25 km/h) — बिना ड्राइविंग लाइसेंस और बिना रजिस्ट्रेशन!
• मात्र ₹0.15 प्रति किमी खर्च — हर महीने ₹3,000+ पेट्रोल की बचत
• ग्रैफीन 48V 30Ah: 9 महीने की बैटरी एवं चार्జర్ वारंटी
• स्मार्ट LFP: 3 साल की व्यापक रिप्लेसमेंट वारंटी
• सोलर रूफटॉप सब्सिडी, जीरो-डेप इंश्योरेंस एवं स्पेयर पार्ट्स सपोर्ट

कृपया ऊपर दिए गए लिंक पर क्लिक करके मॉडल-वाइज कीमतें और वीडियो देखें। आज ही फ्री टेस्ट ड्राइव बुक करें!`,ta:(c,e)=>`வணக்கம் ${c}! 🙏

மாந்த்ரா EV (Manthra EV) அதிகாரப்பூர்வ இருசக்கர மின்சார வாகனங்கள் மற்றும் வாடிக்கையாளர் விலை பட்டியல்:
👉 ${e}

⚡ வாடிக்கையாளர் சிறப்பம்சங்கள்:
• 5 சிறந்த மாடல்கள்: Pro GT, Power Plus, M99 Flagship, Royal Sling, Beast Pro
• நான்-RTO குறைந்த வேகம் (<25 km/h) — ஓட்டுநர் உரிமம் அல்லது பதிவு தேவையில்லை!
• கி.மீக்கு 15 பைசா மட்டுமே — மாதம் ₹3,000+ பெட்ரோல் செலவு மிச்சம்
• கிராபீன் 48V 30Ah: 9 மாதங்கள் பேட்டரி மற்றும் சார்ஜர் உத்தரவாதம்
• ஸ்மார்ட் LFP: 3 ஆண்டுகள் முழுமையான உத்தரவாதம்
• சோலார் மானியம், இன்சூரன்ஸ் மற்றும் உதிரிபாகங்கள் ஆதரவு

மேலே உள்ள இணைப்பைக் கிளிக் செய்து மாடல் விலைகளை அறிந்து இலவச டெஸ்ட் டிரைவ் முன்பதிவு செய்யுங்கள்!`}},ev_b2b:{name:"Commercial EV Fleet & Cargo (B2B)",btnLabel:"EV Commercial Fleet",segmentSlug:"ev-b2b",catalogSlug:"ev-commercial-fleet",brochureUrl:"/public/hub/Assets/myntreal_manthra_ev_brochure.pdf",desc:"Sends Commercial Fleet catalog with 75% logistics savings, reinforced chassis & 2-min battery swap.",messages:{te:(c,e)=>`నమస్కారం ${c} గారు! 🙏

MyntReal Commercial EV Fleet & B2B Cargo డిజిటల్ క్యాటలాగ్ లింక్ ఇక్కడ చూడవచ్చు:
👉 ${e}

🚚 ముఖ్య ప్రయోజనాలు:
• లాజిస్టిక్స్ రన్నింగ్ ఖర్చుల్లో 75% భారీ ఆదా
• భారీ పేలోడ్ సామర్థ్యం కలిగిన హెవీ-డ్యూటీ చాసిస్
• 2 నిమిషాల క్విక్ బ్యాటరీ స్వాప్పింగ్ & స్మార్ట్ టెలిమాటిక్స్ ఫ్లీట్ ట్రాకింగ్
• డెలివరీ & బిజినెస్ ఫ్లీట్‌లకు ప్రత్యేక కార్పొరేట్ ఫైనాన్స్

పై లింక్ క్లిక్ చేసి B2B ఫ్లీట్ మోడల్స్ మరియు ROI కాలిక్యులేటర్ చూడండి.`,en:(c,e)=>`Namaskaram ${c}! 🙏

Here is your official MyntReal Commercial EV Fleet & B2B Cargo Digital Catalog link:
👉 ${e}

🚚 Commercial Fleet Highlights:
• Slash last-mile logistics operating expenses by 75%
• Heavy-duty reinforced chassis engineered for Indian cargo loads
• 2-Minute rapid battery swapping & real-time IoT fleet telematics
• Attractive commercial leasing & zero-downpayment corporate finance

Click the link above to review vehicle specifications & calculate fleet ROI.`,hi:(c,e)=>`नमस्ते ${c} जी! 🙏

MyntReal कमर्शियल ईवी फ्लीट और B2B कार्गो डिजिटल कैटलॉग लिंक यहाँ देखें:
👉 ${e}

🚚 प्रमुख लाभ:
• डिलीवरी और लॉजिस्टिक्स खर्च में 75% तक कटौती
• भारी माल वहन क्षमता एवं मजबूत चेसिस
• 2 मिनट की बैटरी स्वैपिंग और लाइव जीपीएस फ्लीट ट्रैकिंग
• आकर्षक कॉर्पोरेट फाइनेंस और लीजिंग विकल्प

कृपया ऊपर दिए गए लिंक पर क्लिक करके कमर्शियल वाहन विवरण देखें।`,ta:(c,e)=>`வணக்கம் ${c}! 🙏

MyntReal கமர்ஷியல் இ-வாகன கடற்படை (EV Cargo) டிஜிட்டல் கேட்லாக் லிங்க்:
👉 ${e}

🚚 முக்கிய நன்மைகள்:
• போக்குவரத்து செலவில் 75% பெரும் சேமிப்பு
• அதிக எடை சுமக்கும் திறன் மற்றும் நீண்ட ஆயுள்
• 2 நிமிட பேட்டரி ஸ்வாப் & லைவ் GPS டிராக்கிங்

மேலே உள்ள இணைப்பைக் கிளிக் செய்து விவரங்கள் மற்றும் கார்ப்பரேட் சலுகைகளைக் காண்க.`}},ev_spares:{name:"EV Spares, Chargers & Batteries",btnLabel:"EV Spares",segmentSlug:"ev-spares",catalogSlug:"ev-spares-and-chargers",brochureUrl:"/public/hub/Assets/myntreal_ev_spares_brochure.pdf",desc:"Sends EV Spares catalog with OEM components, DC fast chargers, smart BMS & replacement lithium packs.",messages:{te:(c,e)=>`నమస్కారం ${c} గారు! 🙏

⚡ *MyntReal & VGK4U — జెన్యూయిన్ EV స్పేర్స్, ఛార్జర్లు & బ్యాటరీలు*

మీ కోసం అఫీషియల్ డిజిటల్ క్యాటలాగ్ లింక్:
👉 ${e}

🏷️ *డైనమిక్ డిస్కౌంట్లు & ధరల విశ్లేషణ (హబ్ హోల్‌సేల్ vs కస్టమర్ రిటైల్):*
• గ్రాఫీన్ బ్యాటరీ 48V 32Ah (9 నెలల వారంటీ):
   - హబ్ హోల్‌సేల్: ₹12,000 (18% GST కలిపి)
   - కస్టమర్ రిటైల్: ₹14,100 → *ఆదా: ₹2,100 (15% తగ్గింపు)*
• LFP లిథియం బ్యాటరీ 48V 30Ah (2+1 సం. వారంటీ, AIS-156):
   - హబ్ హోల్‌సేల్: ₹18,800 (18% GST కలిపి)
   - కస్టమర్ రిటైల్: ₹22,100 → *ఆదా: ₹3,300 (15% తగ్గింపు)*
• ఫాస్ట్ ఛార్జర్ 48V (9 నెలల వారంటీ): హబ్ ₹1,500 | రిటైల్ ₹1,575
• కంట్రోలర్లు & BMS స్పేర్స్: 20% నుండి 29% వరకు డైనమిక్ మార్జిన్!

🛒 *EV స్పేర్స్ ఈ-కామ్ మార్కెట్‌ప్లేస్‌లో ఆర్డర్ చేయండి:*
👉 https://www.myntreal.com/ecom?vertical=ev&category=spares

24 గంటల్లో దేశవ్యాప్త డెలివరీ & అధికారిక GST ఇన్వాయిసింగ్.`,en:(c,e)=>`Namaskaram ${c}! 🙏

⚡ *MyntReal & VGK4U — Genuine EV Spares, Chargers & Batteries*

Here is your official EV Spares & Battery Systems Digital Catalog:
👉 ${e}

🏷️ *Dynamic Discount & Cost Breakdown (Hub Wholesale vs Customer Retail):*
• *Graphene Battery 48V 32Ah (9 Mo. Warranty):*
   - Hub Wholesale: ₹12,000 (Incl. 18% GST)
   - Customer Retail: ₹14,100 → *Save ₹2,100 (15% Margin)*
• *LFP Lithium Battery 48V 30Ah (2+1 Yr. Warranty, AIS-156):*
   - Hub Wholesale: ₹18,800 (Incl. 18% GST)
   - Customer Retail: ₹22,100 → *Save ₹3,300 (15% Margin)*
• *Smart Fast Charger 48V (9 Mo. Warranty):* Hub ₹1,500 | Retail ₹1,575
• *Controllers & BMS Spares:* 20% to 29% dynamic wholesale margin!

🛒 *Order Online on EV Spares E-Com Marketplace:*
👉 https://www.myntreal.com/ecom?vertical=ev&category=spares

Immediate 24-Hour Pan-India Dispatch | Full GST Invoicing.`,hi:(c,e)=>`नमस्ते ${c} जी! 🙏

MyntReal जेन्युइन ईवी स्पेयर पार्ट्स, चार्जर्स और बैटरी डिजिटल कैटलॉग लिंक यहाँ देखें:
👉 ${e}

⚙️ मुख्य उत्पाद एवं डायनामिक डिस्काउंट:
• 15% से 25% तक की थोक (B2B) छूट
• ग्रैफीन एवं LFP बैटरी पैक्स (9 माह से 3 साल वारंटी)
• स्मार्ट बीएमएस एवं फास्ट चार्जर्स

ई-कॉमर्स पर ऑर्डर करने के लिए: https://www.myntreal.com/ecom?vertical=ev&category=spares`,ta:(c,e)=>`வணக்கம் ${c}! 🙏

MyntReal ஈவி உதிரிபாகங்கள், சார்ஜர்கள் & பேட்டரி டிஜிட்டல் கேட்லாக் லிங்க்:
👉 ${e}

15% முதல் 25% வரை தள்ளுபடி விலையில் ஈவி உதிரிபாகங்கள்!
இ-காமர்ஸ் மூலம் ஆர்டர் செய்ய: https://www.myntreal.com/ecom?vertical=ev&category=spares`}},etc_training:{name:"ETC EV Technician Certifications",btnLabel:"ETC Training",segmentSlug:"etc",catalogSlug:"etc-renewable-certifications",brochureUrl:"/public/hub/Assets/myntreal_etc_training_brochure.pdf",desc:"Sends ETC Training catalog: 1-week EV certification at Govt. Poly Pendurthi, ₹10,000 scholarship discount.",messages:{te:(c,e)=>`నమస్కారం ${c} గారు! 🙏

EVolution Training Centre (ETC) ప్రొఫెషనల్ EV సర్టిఫికేషన్ డిజిటల్ క్యాటలాగ్ లింక్ ఇక్కడ చూడవచ్చు:
👉 ${e}

🎓 కోర్సు విశేషాలు:
• 1-వారం ప్రాక్టికల్ EV టెక్నీషియన్ & ఎంటర్‌ప్రెన్యూర్‌షిప్ ప్రోగ్రామ్
• Govt. Polytechnic College, Pendurthi లో ప్రత్యక్ష ప్రాక్టికల్ ల్యాబ్స్
• BLDC మోటార్లు, బ్యాటరీ ప్యాక్ అసెంబ్లీ & BMS డయాగ్నోస్టిక్స్ లో శిక్షణ
• ఫీజు ₹19,999 కి బదులుగా ₹10,000 స్కాలర్‌షిప్‌తో కేవలం ₹9,999 మాత్రమే!
• 100% ప్లేస్‌మెంట్ అసిస్టెన్స్ & సర్వీస్ సెంటర్ బిజినెస్ గైడెన్స్

పై లింక్ క్లిక్ చేసి సిలబస్ మరియు తదుపరి బ్యాచ్ వివరాలు చూడండి.`,en:(c,e)=>`Namaskaram ${c}! 🙏

Here is your official MyntReal EVolution Training Centre (ETC) Professional EV Certifications Digital Catalog link:
👉 ${e}

🎓 Certification Highlights:
• 1-Week Intensive Hands-on EV Technician & Entrepreneurship Certification
• Conducted at Govt. Polytechnic College, Pendurthi with live lab equipment
• Deep training on BLDC motors, Lithium battery pack assembly & BMS debugging
• Standard Fee ₹19,999 discounted by ₹10,000 Scholarship — Final Fee ₹9,999 only!
• 100% Career placement assistance & EV service franchise support

Click the link above to view curriculum, batch dates & reserve your seat.`,hi:(c,e)=>`नमस्ते ${c} जी! 🙏

EVolution Training Centre (ETC) प्रोफेशनल ईवी सर्टिफिकेशन डिजिटल कैटलॉग लिंक यहाँ देखें:
👉 ${e}

🎓 कोर्स की मुख्य विशेषताएं:
• 1-सप्ताह का हैंड्स-ऑन ईवी तकनीशियन एवं उद्यमिता प्रमाणन
• Govt. Polytechnic College, Pendurthi में व्यावहारिक प्रयोगशाला प्रशिक्षण
• BLDC मोटर्स, लिथियम बैटरी पैक असेंबली और BMS डायग्नोस्टिक्स में महारत
• ₹19,999 फीस पर ₹10,000 स्कॉलरशिप छूट — केवल ₹9,999!
• 100% जॉब प्लेसमेंट सहायता एवं ईवी सर्विस सेंटर शुरू करने हेतु मार्गदर्शन

कृपया ऊपर दिए गए लिंक पर क्लिक करके बैच डेट्स और सीट रिजर्व करें।`,ta:(c,e)=>`வணக்கம் ${c}! 🙏

EVolution Training Centre (ETC) தொழில்முறை ஈவி சான்றிதழ் டிஜிட்டல் கேட்லாக் லிங்க்:
👉 ${e}

🎓 பாடப்பிரிவின் சிறப்பம்சங்கள்:
• 1 வார தீவிர செய்முறை ஈவி தொழில்நுட்ப வல்லுநர் பயிற்சி
• அரசு பாலிடெக்னிக் கல்லூரி, பெந்துர்த்தியில் நேரடி பயிற்சி கூடங்கள்
• BLDC மோட்டார், லித்தியம் பேட்டரி மற்றும் BMS பழுதுபார்ப்பு பயிற்சி
• ₹19,999 கட்டணத்தில் ₹10,000 கல்வி உதவித்தொகை — கட்டணம் ₹9,999 மட்டுமே!
• 100% வேலைவாய்ப்பு உதவி & தொழில் தொடங்க ஆதரவு

மேலே உள்ள இணைப்பைக் கிளிக் செய்து பாடத்திட்டம் மற்றும் சேர்க்கை விவரங்களை அறிக.`}},insurance:{name:"Comprehensive Insurance Advisory",btnLabel:"Insurance",segmentSlug:"insurance",catalogSlug:"comprehensive-insurance-advisory",brochureUrl:"/public/hub/Assets/myntreal_insurance_guide.pdf",desc:"Sends Insurance catalog with complete risk protection for EV fleets, solar rooftop plants, health & life.",messages:{te:(c,e)=>`నమస్కారం ${c} గారు! 🙏

🛡️ *VGK Care — 360° సమగ్ర బీమా & రిస్క్ ప్రొటెక్షన్*

మీ కోసం అధికారిక ఇన్సూరెన్స్ అడ్వైజరీ డిజిటల్ క్యాటలాగ్ లింక్:
👉 ${e}

✨ *ముఖ్య బీమా రంగాలు & ప్రయోజనాలు:*
• *ఈవీ మోటార్ & బ్యాటరీ రీప్లేస్‌మెంట్ కవర్:* లిథియం బ్యాటరీ డ్యామేజ్, వాటర్ ఇన్‌గ్రెస్ & జీరో-డిప్రిసియేషన్ ప్రొటెక్షన్
• *సోలార్ రూఫ్‌టాప్ EPC ఆల్-రిస్క్ ఇన్సూరెన్స్:* తుఫాను, వర్షం, పిడుగుపాటు & జనరేషన్ లాస్ నష్టపరిహారం
• *ఫ్యామిలీ క్యాష్‌లెస్‌ హెల్త్ ఇన్సూరెన్స్:* 4,500+ నెట్‌వర్క్ హాస్పిటల్స్ & నో రూమ్ రెంట్ క్యాపింగ్
• *కమర్షియల్ & ఫ్యాక్టరీ లయబిలిటీ:* అగ్నిప్రమాదాలు, దొంగతనం & పబ్లిక్ లయబిలిటీ షీల్డ్
• *98.6% క్లెయిమ్ సెటిల్‌మెంట్ రేషియో* & తక్షణ డిజిటల్ స్పాట్ ఇన్సూరెన్స్ జారీ

పై లింక్ ద్వారా ప్రీమియం కాలిక్యులేట్ చేసుకోండి మరియు తక్షణ పాలసీ పొందండి.`,en:(c,e)=>`Namaskaram ${c}! 🙏

🛡️ *VGK Care — 360° Comprehensive Insurance & Risk Protection*

Here is your official VGK Care Insurance Advisory Digital Catalog link:
👉 ${e}

✨ *Core Advisory & Coverage Highlights:*
• *EV Motor & Battery Zero-Dep Cover:* Explicit protection for lithium battery replacement, water ingress & thermal runaway
• *Solar Rooftop EPC All-Risk Policy:* Protects against cyclones, storm damage & generation loss downtime
• *Family Cashless Health Plans:* 4,500+ cashless network hospitals with zero room-rent cap
• *Commercial & Factory Liability:* Comprehensive fire, burglary, stock & business interruption cover
• *98.6% Claim Settlement Ratio* with instant spot digital policy issuance

Click the link above to calculate customized premiums and issue policies on spot.`,hi:(c,e)=>`नमस्ते ${c} जी! 🙏

MyntReal व्यापक बीमा सलाहकार (Insurance Advisory) डिजिटल कैटलॉग लिंक यहाँ देखें:
👉 ${e}

🛡️ बीमा सुरक्षा के मुख्य लाभ:
• इलेक्ट्रिक वाहन (EV) और कमर्शियल फ्लीट विशेष बीमा
• सोलर रूफटॉप प्लांट ऑल-रिस्क कवरेज
• फैमिली हेल्थ एवं टर्म लाइफ इंश्योरेंस प्लान्स (कैशलेस सुविधा)
• व्यापार और कमर्शियल प्रॉपर्टी प्रोटेक्शन
• त्वरित क्लेम निपटान सहायता

कृपया ऊपर दिए गए लिंक पर क्लिक करके बीमा योजनाओं की तुलना करें और कोटेशन पाएं।`,ta:(c,e)=>`வணக்கம் ${c}! 🙏

MyntReal விரிவான காப்பீட்டு ஆலோசனை (Insurance Advisory) டிஜிட்டல் கேட்லாக் லிங்க்:
👉 ${e}

🛡️ காப்பீட்டு சிறப்பம்சங்கள்:
• எலக்ட்ரிக் வாகனங்கள் மற்றும் வணிக கடற்படைக்கான சிறப்பு காப்பீடு
• சோலார் ஆலைக்கான முழுமையான இடர் பாதுகாப்பு
• விரிவான மருத்துவ & ஆயுள் காப்பீட்டு திட்டங்கள்
• உடனடி க்ளைம் தீர்வு உதவி

மேலே உள்ள இணைப்பைக் கிளிக் செய்து பாலிசி விவரங்களை அறிந்து உடனடி கொட்டேஷன் பெறுங்கள்.`}},industrial_hub:{name:"MyntReal Hub (5-in-1 Franchise)",btnLabel:"MyntReal Hub",segmentSlug:"industrial-hub",catalogSlug:"industrial-hub-franchise",brochureUrl:"/public/hub/Assets/myntreal_investor_franchise_brochure.pdf",desc:"Sends MyntReal Hub catalog: 5-in-1 investor franchise (EV, Solar, Insurance, Real Estate & Training) with ₹12–15L investment & 140% ROI.",messages:{te:(c,e)=>`నమస్కారం ${c} గారు! 🙏

MyntReal Hub (5-in-1 ఇన్వెస్టర్ ఫ్రాంచైజ్) అధికారిక డిజిటల్ క్యాటలాగ్ లింక్:
👉 ${e}

🏢 ఒకే హబ్ — 5 లాభదాయక వ్యాపార మార్గాలు:
• మంత్ర ఈవీ షోరూమ్ & స్పేర్స్ డిపో (యూనిట్‌కు ₹7,000 మార్జిన్)
• హర్ ఘర్ సోలార్ రూఫ్‌టాప్ EPC (₹78,000 సబ్సిడీ & ప్రాజెక్ట్‌కు ₹20,000 మార్జిన్)
• VGK కేర్ ఇన్సూరెన్స్ అడ్వైజరీ (40+ ఇన్సూరర్లు, పాలసీకి ₹3,000 మార్జిన్)
• VGK రియల్ డ్రీమ్స్ టౌన్‌షిప్స్ & విల్లాస్ బ్రోకరేజ్
• EVolution ట్రైనింగ్ సెంటర్ (గవర్నమెంట్ పాలిటెక్నిక్ కాలేజ్ పార్టనర్)

💼 పెట్టుబడి: ₹12–15 లక్షలు | బ్రేక్-ఈవెన్: 6-9 నెలలు | వార్షిక నికర ఆదాయం: ₹19.8 లక్షలు+
🎁 ఫ్రాంచైజీతో పాటు కంప్యూటర్, 43" స్మార్ట్ టీవీ, కలర్ ప్రింటర్, షోరూమ్ బ్రాండింగ్ & 12 నెలల లీడ్ సపోర్ట్ ఉచితం!

పై లింక్ క్లిక్ చేసి పూర్తి ప్రాస్పెక్టస్, ROI మోడల్ & వివరాలు చూడగలరు.`,en:(c,e)=>`Namaskaram ${c}! 🙏

Here is your official MyntReal Hub (5-in-1 Investor Franchise) Digital Catalog link:
👉 ${e}

🏢 One Hub — 5 High-Demand Business Streams:
• Manthra EV Dealership & Spares (₹7,000 / unit margin)
• Har Ghar Solar EPC (₹78,000 DBT subsidy & ₹20,000 / system margin)
• VGK Care Insurance Advisory (40+ Insurers, ₹3,000 / policy margin)
• VGK Real Dreams Townships & Luxury Villas (High-ticket brokerage)
• EVolution Training Centre (Govt. Polytechnic College Campus)

💼 Investment: ₹12 – 15 Lakhs | Break-even: 6–9 Months | Base Net: ₹19.80 Lakhs / yr
🎁 Turnkey Setup: Business PC with MyntOS ERP, 43" Smart TV, Color Printer, Complete Showroom Branding & 12 Months Lead Support included!

Click the link above to review complete deliverables, financial models & territory rights.`,hi:(c,e)=>`नमस्ते ${c} जी! 🙏

MyntReal Hub (5-इन-1 इन्वेस्टर फ्रैंचाइज़) आधिकारिक डिजिटल कैटलॉग लिंक यहाँ देखें:
👉 ${e}

🏢 एक हब — 5 उच्च मुनाफे वाले व्यापार:
• मंत्रा ईवी डीलरशिप एवं स्पेयर पार्ट्स (₹7,000 प्रति वाहन मार्जिन)
• हर घर सोलर रूफटॉप ईपीसी (₹78,000 सब्सिडी एवं ₹20,000 प्रति सिस्टम मार्जिन)
• वीजीके केयर बीमा सलाहकार (40+ बीमा कंपनियाँ, ₹3,000 प्रति पॉलिसी मार्जिन)
• वीजीके रियल ड्रीम्स टाउनशिप एवं विला ब्रोकरेज
• ईवीोल्यूशन ट्रेनिंग सेंटर (गवर्नमेंट पॉलिटेक्निक कॉलेज पार्टनर)

💼 निवेश: ₹12–15 लाख | ब्रेक-ईवन: 6–9 महीने | अनुमानित शुद्ध वार्षिक आय: ₹19.8 लाख+
🎁 टर्नकी सेटअप: बिजनेस पीसी, 43" स्मार्ट टीवी, कलर प्रिंटर, शोरूम ब्रांडिंग और 12 महीने का लीड सपोर्ट शामिल!

कृपया ऊपर दिए गए लिंक पर क्लिक करके पूरी जानकारी और आरओआई मॉडल देखें।`,ta:(c,e)=>`வணக்கம் ${c}! 🙏

MyntReal Hub (5-இன்-1 முதலீட்டு ஃபிரான்சைஸ்) அதிகாரப்பூர்வ டிஜிட்டல் கேட்லாக் லிங்க்:
👉 ${e}

🏢 ஒரே மையம் — 5 லாபகரமான வணிக வழிகள்:
• மாந்த்ரா இ-வாகன விற்பனை & உதிரிபாகங்கள் மையம்
• ஹர் கர் சோலார் கூரை மின் உற்பத்தி EPC (₹78,000 மானியம்)
• VGK கேர் விரிவான காப்பீட்டு ஆலோசனை (40+ நிறுவனங்கள்)
• VGK ரியல் ட்ரீம்ஸ் நிலம் & சொத்து விற்பனை
• EVolution தொழில்முறை இ-வாகன பயிற்சி மையம்

💼 முதலீடு: ₹12–15 லட்சம் | முதலீடு மீட்பு: 6–9 மாதங்கள் | ஆண்டு நிகர வருமானம்: ₹19.80 லட்சம்+
🎁 கணினி, 43" ஸ்மார்ட் டிவி, கலர் பிரிண்டர், பிராண்டிங் மற்றும் 12 மாத லீட் ஆதரவு முற்றிலும் இலவசம்!

முழு விவரங்களையும் நிதி மாதிரியையும் காண மேலே உள்ள இணைப்பைக் கிளிக் செய்க.`}},hub_pricing:{name:"Hub Commercials & Pricing (24h)",btnLabel:"Hub Pricing (24h)",segmentSlug:"hub-pricing",catalogSlug:"hub-ev-pricing",brochureUrl:"/public/hub/Assets/myntreal_investor_franchise_brochure.pdf",desc:"Sends confidential MyntReal Hub EV & Solar Commercial Pricing catalog with wholesale costs, dealer margins & 24h auto-expiry security.",messages:{te:(c,e)=>`నమస్కారం ${c} గారు! 🙏

MyntReal Hub — గోప్యమైన EV & సోలార్ కమర్షియల్ ప్రైసింగ్ & డీలర్ మార్జిన్స్ క్యాటలాగ్ లింక్ (24 గంటలు మాత్రమే చెల్లుబాటు):
👉 ${e}

⚡ కమర్షియల్ ప్రైసింగ్ & మార్జిన్ వివరాలు:
• 5 మోడల్స్ EV వాహనాల హోల్‌సేల్ ధరలు & 12% హబ్ మార్జిన్ (~₹7,200/వాహనం)
• డైరెక్ట్ కస్టమర్ సేల్స్ పై +10.5% అదనపు VGK4U కమిషన్ (మొత్తం 22.5% మార్జిన్)
• గ్రాఫేన్ & LFP బ్యాటరీలు మరియు ఫాస్ట్ ఛార్జర్ల విడి భాగాల ధరల పట్టిక
• సోలార్ EPC 1kW–10kW మాతృక: ₹1,99,999 సిస్టమ్‌పై ₹7,000 షోరూమ్ + ₹13,000 డైరెక్ట్ మార్జిన్
• 3-దశల యూనిట్ ఎకనామిక్స్ & లైవ్ డైరెక్ట్ సేల్స్ ROI సిమ్యులేటర్

⚠️ గమనిక: ఈ లింక్ కేవలం 24 గంటలు మాత్రమే యాక్టివ్‌గా ఉంటుంది.

పై లింక్ క్లిక్ చేసి పూర్తి హోల్‌సేల్ కాస్ట్ షీట్ & ROI వివరాలు వెంటనే చూడగలరు.`,en:(c,e)=>`Namaskaram ${c}! 🙏

Here is your Confidential MyntReal Hub — EV & Solar Commercial Pricing & Dealer Margins Prospectus (Strictly Valid for 24 Hours):
👉 ${e}

⚡ Commercial Highlights:
• OEM Wholesale Central Pricing & 12% Hub Dealer Margin (~₹7,200 avg/vehicle)
• Direct Customer Sale: +10.5% VGK4U Bonus (Total 22.5% combined spread)
• Standalone Graphene & LFP Batteries + Smart Fast Chargers Cost Matrix
• Solar EPC 1kW–10kW: ₹1,99,999 Flagship gives ₹7,000 Showroom + ₹13,000 Direct Margin
• 3-Scenario Financial Viability & Interactive Investor ROI Simulator

⚠️ Note: This confidential link expires automatically in 24 hours.

Click the link above to review wholesale cost sheets & calculate your net returns.`,hi:(c,e)=>`नमस्ते ${c} जी! 🙏

MyntReal Hub — गोपनीय EV और सोलर कमर्शियल प्राइसिंग एवं डीलर मार्जिन कैटलॉग लिंक (केवल 24 घंटे मान्य):
👉 ${e}

⚡ मुख्य व्यावसायिक विवरण:
• 5 मॉडल्स EV वाहनों की थोक खरीद लागत और 12% हब डीलर मार्जिन
• डायरेक्ट सेल पर +10.5% अतिरिक्त VGK4U कमीशन (कुल 22.5% मार्जिन)
• ग्रैफीन एवं LFP बैटरियां और फास्ट चार्जर कंपोनेंट लागत सूची
• सोलर EPC 1kW–10kW: ₹1,99,999 प्लांट पर ₹7,000 शोरूम + ₹13,000 डायरेक्ट मार्जिन
• 3-सिनेरियो यूनिट इकोनॉमिक्स और लाइव ROI सिम्युलेटर

⚠️ ध्यान दें: यह लिंक केवल 24 घंटे के लिए सक्रिय है।

कृपया तुरंत ऊपर दिए गए लिंक पर क्लिक करके पूरी कॉस्ट शीट देखें।`,ta:(c,e)=>`வணக்கம் ${c}! 🙏

MyntReal Hub — ரகசியமான EV & சோலார் வணிக விலை & டீலர் மார்ஜின் கேட்லாக் லிங்க் (24 மணிநேரம் மட்டுமே செல்லுபடியாகும்):
👉 ${e}

⚡ வணிக சிறப்பம்சங்கள்:
• 5 மாடல் மின்சார வாகன மொத்த விலை & 12% ஹப் டீலர் மார்ஜின்
• நேரடி விற்பனையில் +10.5% கூடுதல் VGK4U கமிஷன் (மொத்தம் 22.5% லாபம்)
• கிராபீன் & LFP பேட்டரிகள் மற்றும் பாஸ்ட் சார்ஜர் உதிரிபாகங்கள் விலை பட்டியல்
• சோலார் EPC 1kW–10kW: ₹1,99,999 அமைப்பில் ₹7,000 ஷோரூம் + ₹13,000 நேரடி மார்ஜின்
• 3-நிலை நிதி சாத்தியக்கூறு ஆய்வு & நேரடி ROI கால்குலேட்டர்

⚠️ குறிப்பு: இந்த ரகசிய இணைப்பு 24 மணிநேரத்திற்கு மட்டுமே செல்லுபடியாகும்.

முழு விலை மற்றும் வருவாய் விவரங்களை அறிய மேலே உள்ள இணைப்பை கிளிக் செய்யவும்.`}}};class ie{modalEl=null;currentOptions=null;activeMode="meta_api";selectedCatalogKey="solar";selectedCatalogLang="te";allCanonicalTemplates=[];canonicalTemplates=[];selectedCanonicalBody="";getSenderSignature(){const t=y.getAuthState().user||{},a=t.full_name||t.name||`${t.first_name||""} ${t.last_name||""}`.trim()||"Staff";let i=t.extension||t.ext||(typeof window<"u"?window.__STAFF_EXTENSION__:null);if(!i&&t.emp_code){const n=String(t.emp_code).match(/(\d{2,4})$/);n&&(i=n[1].replace(/^0+/,"")||n[1])}return i&&String(i).trim()&&!["none","null","undefined","n/a"].includes(String(i).trim().toLowerCase())?`

Regards,
${a}
📞 +91 85858 52738 | +91 8897797667
Ext: ${String(i).trim()}`:`

Regards,
${a}
📞 +91 85858 52738 | +91 8897797667`}getVerticalQuickMessage(e){const t=(this.currentOptions?.name||"Customer").trim(),a=(this.currentOptions?.context||"").toLowerCase();let i="general";if(a.includes("solar")?i="solar":a.includes("real")||a.includes("property")||a.includes("estate")?i="real_estate":a.includes("insur")||a.includes("care")?i="insurance":a.includes("ev")||a.includes("spare")||a.includes("zynova")||a.includes("vehicle")?i="ev":(a.includes("etc")||a.includes("train")||a.includes("skill"))&&(i="etc"),e==="thanks_connecting")switch(i){case"solar":return`నమస్కారం ${t} గారు! 🙏 MyntReal Solar Rooftop గురించి మాతో మాట్లాడినందుకు ధన్యవాదాలు. మీ ఇంటి లేదా కమర్షియల్ కరెంట్ బిల్లును 90% వరకు తగ్గించుకుంటూ, Government Subsidy పొందే పూర్తి వివరాలు & Customized Solar Quotation త్వరలోనే మా సోలార్ ఎక్స్‌పర్ట్ మీకు షేర్ చేస్తారు. ఏవైనా డౌట్స్ ఉంటే దయచేసి ఇక్కడ మెసేజ్ చేయండి.

☀️ మా అధికారిక సోలార్ క్యాటలాగ్ & సబ్సిడీ వివరాలు:
👉 https://www.myntreal.com/catalog/solar/commercial-residential-solar?lang=te`;case"real_estate":return`నమస్కారం ${t} గారు! 🙏 MyntReal Properties తో కనెక్ట్ అయినందుకు ధన్యవాదాలు. మీ బడ్జెట్ మరియు రిక్వైర్‌మెంట్‌కు తగినట్లుగా బెస్ట్ వెరిఫైడ్ ఓపెన్ ప్లాట్స్, గేటెడ్ కమ్యూనిటీ విల్లాస్ మరియు అపార్ట్‌మెంట్స్ వివరాలను మా ప్రాపర్టీ స్పెషలిస్ట్ త్వరలోనే మీకు షేర్ చేస్తారు. సైట్ విజిట్ కోసం ఎప్పుడైనా సంప్రదించవచ్చు.

🏡 మా అధికారిక రియల్ ఎస్టేట్ క్యాటలాగ్:
👉 https://www.myntreal.com/catalog/real-dreams/real-dreams-premium-properties?lang=te`;case"insurance":return`నమస్కారం ${t} గారు! 🙏 MyntReal Insurance & Protection తో మాట్లాడినందుకు ధన్యవాదాలు. మీకు మరియు మీ కుటుంబానికి సరిపోయే బెస్ట్ Health, Life మరియు General Insurance పాలసీ కొటేషన్లను మా ఇన్సూరెన్స్ అడ్వైజర్ మీకు పంపిస్తారు. పూర్తి క్లెయిమ్ సపోర్ట్ మా బాధ్యత.

🛡️ మా అధికారిక ఇన్సూరెన్స్ గైడ్ & సేవలు:
👉 https://www.myntreal.com/catalog/insurance/comprehensive-insurance-advisory?lang=te`;case"ev":return`నమస్కారం ${t} గారు! 🙏 MyntReal EV & Spares గురించి మాతో కనెక్ట్ అయినందుకు ధన్యవాదాలు. లేటెస్ట్ ఎలక్ట్రిక్ వెహికల్ మోడల్స్, రేంజ్, బ్యాటరీ వారంటీ, ఫైనాన్స్ ఆప్షన్స్ మరియు టెస్ట్ రైడ్ వివరాలను మా ఈవీ స్పెషలిస్ట్ మీకు త్వరలోనే అందిస్తారు.

⚡ మా అధికారిక ఈవీ ప్రైసింగ్ & క్యాటలాగ్:
👉 https://www.myntreal.com/catalog/ev-b2c-pricing?lang=te`;case"etc":return`నమస్కారం ${t} గారు! 🙏 MyntReal ETC Skill Training ప్రోగ్రామ్స్ గురించి మాట్లాడినందుకు ధన్యవాదాలు. మీ కెరీర్ గ్రోత్‌కు అవసరమైన సర్టిఫైడ్ ట్రైనింగ్ కోర్సులు, బ్యాచ్ టైమింగ్స్ మరియు జాబ్ అసిస్టెన్స్ వివరాలు మా కోఆర్డినేటర్ మీకు పంపిస్తారు.

🎓 మా అధికారిక ఈటీసీ సర్టిఫికేషన్ ప్రోగ్రామ్స్:
👉 https://www.myntreal.com/catalog/etc/etc-renewable-certifications?lang=te`;default:return`నమస్కారం ${t} గారు! 🙏 MyntReal తో కనెక్ట్ అయినందుకు చాలా ధన్యవాదాలు. మా అన్ని ప్రీమియర్ సర్వీసెస్ మీ సేవలో అందుబాటులో ఉన్నాయి:
☀️ Solar Rooftop & Renewable Energy (కరెంట్ బిల్లు 90% వరకు ఆదా & Govt సబ్సిడీ)
🏡 Real Estate & Premier Properties (ఓపెన్ ప్లాట్స్, విల్లాస్ & అపార్ట్‌మెంట్స్)
🛡️ Insurance & Protection Solutions (హెల్త్, లైఫ్ & జనరల్ పాలసీలు)
🛵 EV Vehicles & Genuine Spares (ఎకో-ఫ్రెండ్లీ ఎలక్ట్రిక్ బైక్స్ & సర్వీస్)
🎓 ETC Skill Training & Career Certifications (ఉద్యోగ నైపుణ్య శిక్షణ)

👉 https://www.myntreal.com/catalog/industrial-hub/industrial-hub-franchise?lang=te

మా Relationship Manager మీకు పూర్తి వివరాలు అందిస్తారు. మీకు ఏ సమాచారం కావాలన్నా దయచేసి ఇక్కడ మెసేజ్ చేయగలరు!`}else switch(i){case"solar":return`నమస్కారం ${t} గారు! 📞 మీ Solar Rooftop ఎంక్వైరీ కోసం MyntReal నుండి ఇప్పుడే కాల్ చేశాము, కానీ కాల్ కలవలేదు. మీరు ఫ్రీగా ఉన్నప్పుడు దయచేసి ఈ మెసేజ్‌కి రిప్లై ఇవ్వండి లేదా కాల్ బ్యాక్ చేయండి. సోలార్ సబ్సిడీ మరియు సేవింగ్స్ వివరాలు తెలియజేస్తాము.

☀️ మా సోలార్ క్యాటలాగ్ ఇక్కడ చూడండి:
👉 https://www.myntreal.com/catalog/solar/commercial-residential-solar?lang=te`;case"real_estate":return`నమస్కారం ${t} గారు! 📞 మీ Real Estate ప్రాపర్టీ ఎంక్వైరీ గురించి MyntReal నుండి కాల్ చేశాము, మాట్లాడటం కుదరలేదు. మీకు అనుకూలమైన టైమ్‌లో దయచేసి రిప్లై ఇవ్వండి లేదా కాల్ చేయండి. మీ రిక్వైర్‌మెంట్‌కు సరిపడే బెస్ట్ ప్రాపర్టీ ఆప్షన్స్ మీకు పంపిస్తాము.

🏡 మా రియల్ ఎస్టేట్ క్యాటలాగ్:
👉 https://www.myntreal.com/catalog/real-dreams/real-dreams-premium-properties?lang=te`;case"insurance":return`నమస్కారం ${t} గారు! 📞 మీ Insurance ఎంక్వైరీ గురించి MyntReal నుండి కాల్ చేశాము, కాల్ కలవలేదు. మీకు ఫ్రీ టైమ్ ఉన్నప్పుడు దయచేసి ఇక్కడ రిప్లై ఇవ్వండి. మీకు అనువైన బెస్ట్ ఇన్సూరెన్స్ ప్లాన్స్ వివరాలు చర్చిద్దాం.

🛡️ ఇన్సూరెన్స్ వివరాలు:
👉 https://www.myntreal.com/catalog/insurance/comprehensive-insurance-advisory?lang=te`;case"ev":return`నమస్కారం ${t} గారు! 📞 మీ EV Vehicle & Spares ఎంక్వైరీ కోసం MyntReal నుండి కాల్ చేశాము, మాట్లాడటం వీలుపడలేదు. మీరు వీలైనప్పుడు రిప్లై ఇవ్వండి లేదా కాల్ చేయండి. టెస్ట్ రైడ్ మరియు మోడల్స్ వివరాలు మీకు తెలియజేస్తాము.

⚡ ఈవీ మోడల్స్ & ప్రైసింగ్:
👉 https://www.myntreal.com/catalog/ev-b2c-pricing?lang=te`;case"etc":return`నమస్కారం ${t} గారు! 📞 మీ ETC Skill Training కోర్సు వివరాల కోసం MyntReal నుండి కాల్ చేశాము, కాల్ కనెక్ట్ అవ్వలేదు. మీరు ఫ్రీగా ఉన్నప్పుడు దయచేసి మెసేజ్ చేయండి. అప్‌కమింగ్ బ్యాచ్ టైమింగ్స్ మరియు ఫీజు వివరాలు చర్చిద్దాం.

🎓 ట్రైనింగ్ కోర్సులు:
👉 https://www.myntreal.com/catalog/etc/etc-renewable-certifications?lang=te`;default:return`నమస్కారం ${t} గారు! 📞 MyntReal నుండి మీతో మాట్లాడటానికి ఇప్పుడే కాల్ చేశాము, కానీ కాల్ కలవలేదు / మీరు బిజీగా ఉన్నట్లున్నారు. మేము మీకు క్రింది సర్వీసెస్‌లో ఉత్తమ సేవలు అందిస్తున్నాము:
☀️ Solar Energy (సోలార్ రూఫ్‌టాప్ & సబ్సిడీ)
🏡 Real Estate (వెరిఫైడ్ ప్రాపర్టీస్ & సైట్ విజిట్స్)
🛡️ Insurance (హెల్త్ & లైఫ్ ఇన్సూరెన్స్)
🛵 EV Vehicles & Spares (ఎలక్ట్రిక్ స్కూటర్లు & స్పేర్స్)
🎓 ETC Skill Training (నైపుణ్య శిక్షణ & కెరీర్)

👉 https://www.myntreal.com/catalog/industrial-hub/industrial-hub-franchise?lang=te

మీకు అనుకూలమైన సమయంలో దయచేసి ఇక్కడ మెసేజ్ చేయండి లేదా కాల్ బ్యాక్ చేయగలరు!`}}applyVerticalQuick(e){const t=this.getVerticalQuickMessage(e),a=this.getSenderSignature(),i=document.getElementById("uwaMessageText");i&&(i.value=t+a,i.focus())}onDigitalCatalogSelect(e){e&&N[e]&&(this.selectedCatalogKey=e);const t=N[this.selectedCatalogKey]||N.solar,a=document.getElementById("uwaDigitalCatDesc");a&&(a.textContent=t.desc);const i=document.getElementById("uwaDigitalCatBtnLabel");i&&(i.textContent=`Insert Personalized ${t.btnLabel||t.name} Catalog Link`)}getDigitalCatalogMessage(e,t){const a=N[e]||N.solar,i=(this.currentOptions?.name||"Customer").trim();let n="https://www.myntreal.com";if(typeof window<"u"&&window.location&&window.location.origin){const r=window.location.origin;r.includes("localhost")||r.includes("127.0.0.1")||r.includes("0.0.0.0")||r.includes("192.168.")||r.includes("10.0.")||r.includes(":8000")||r.includes(":5000")||r.includes(":5173")||r.includes(":3000")||r.includes("capacitor")||(n=r)}let s=`${n}/catalog/${a.segmentSlug}/${a.catalogSlug}?lang=${encodeURIComponent(t||"te")}`;e==="hub_pricing"&&!s.includes("exp=")&&(s+=`&exp=${Math.floor(Date.now()/1e3)+86400}`);const l=(t||"te").toLowerCase(),o=a.messages&&a.messages[l]?a.messages[l]:a.messages&&a.messages.en;let d="";if(typeof o=="function"?d=o(i,s):d=`Namaskaram ${i}! Here is your catalog link:
👉 ${s}`,a.brochureUrl&&!d.includes(".pdf")){const r=a.brochureUrl.startsWith("http")?a.brochureUrl:n+(a.brochureUrl.startsWith("/")?"":"/")+a.brochureUrl;d+=`

${l==="te"?"📄 *అధికారిక PDF బ్రోచర్ (డైరెక్ట్ డౌన్‌లోడ్):*":l==="hi"?"📄 *आधिकारिक पीडीएफ ब्रोशर (डाउनलोड लिंक):*":l==="ta"?"📄 *அதிகாரப்பூர்வ PDF ப்ரோஷர் (பதிவிறக்கம்):*":"📄 *Official PDF Brochure (Direct Download):*"}
👉 ${r}`}return d}applyDigitalCatalog(e){e&&(this.selectedCatalogLang=e,this.modalEl?.querySelectorAll(".uwa-cat-lang-btn")?.forEach(l=>{const o=l.getAttribute("data-lang")===e;l.style.background=o?"#16a34a":"#fff",l.style.color=o?"#fff":"#334155",l.style.borderColor=o?"#16a34a":"#cbd5e1",l.style.fontWeight=o?"700":"600"}));const t=document.getElementById("uwaDigitalCatSel");t&&t.value&&(this.selectedCatalogKey=t.value);const a=this.getDigitalCatalogMessage(this.selectedCatalogKey,this.selectedCatalogLang),i=this.getSenderSignature(),n=document.getElementById("uwaMessageText");n&&(n.value=a+i,n.focus())}detectCatalogKey(){if(this.currentOptions?.catalogKey&&N[this.currentOptions.catalogKey])return this.currentOptions.catalogKey;const e=(this.currentOptions?.context||"").toLowerCase(),t=(this.currentOptions?.segment||"").toLowerCase();return e.includes("solar")||t==="solar"?"solar":e.includes("real")||e.includes("property")||e.includes("estate")||t==="myntreal_real"?"real_estate":e.includes("spare")||t==="ev_spares"?"ev_spares":e.includes("cargo")||e.includes("fleet")||e.includes("b2b")||t==="ev_b2b"?"ev_b2b":e.includes("ev")||e.includes("zynova")||e.includes("vehicle")||t==="ev_b2c"?"ev_b2c":e.includes("train")||e.includes("skill")||e.includes("etc")||t==="etc_training"?"etc_training":e.includes("insur")||e.includes("policy")||e.includes("care")?"insurance":e.includes("pricing")||e.includes("margin")||e.includes("commercial")||t==="hub_pricing"?"hub_pricing":e.includes("hub")||e.includes("franchise")?"industrial_hub":"solar"}async loadCanonicalTemplates(e){const t=document.getElementById("uwaCanonicalTpl"),a=document.getElementById("uwaNoTplNotice");if(!t)return;t.innerHTML='<option value="">— Loading templates… —</option>',a&&(a.style.display="none");const i=this.activeMode==="scanned"?"scanned":"company";let n=`/whatsapp-config/templates?mode=${encodeURIComponent(i)}`;try{const s=await C.get(n),l=s?.templates||s?.data||s||[];this.allCanonicalTemplates=Array.isArray(l)?l:[],this.filterCanonicalTemplates(e)}catch{t.innerHTML='<option value="">— Error loading templates —</option>'}}filterCanonicalTemplates(e){const t=document.getElementById("uwaCanonicalTpl"),a=document.getElementById("uwaNoTplNotice");if(!t)return;const i=document.getElementById("uwaCanonicalSeg"),n=document.getElementById("uwaCanonicalCat"),s=document.getElementById("uwaCanonicalSearch"),l=(i?.value||"").toLowerCase().trim(),o=(n?.value||"").toUpperCase().trim(),d=(s?.value||"").toLowerCase().trim();let r=this.allCanonicalTemplates||[];if(l&&(r=r.filter(p=>(p.segment||"").toLowerCase()===l)),o&&(r=r.filter(p=>(p.category||"").toUpperCase()===o)),d&&(r=r.filter(p=>{const g=(p.template_name||p.name||"").toLowerCase(),h=(p.body_text||p.content||p.body||"").toLowerCase(),b=(p.slug||"").toLowerCase();return g.includes(d)||h.includes(d)||b.includes(d)})),this.canonicalTemplates=r,!r.length){t.innerHTML=`
        <option value="">— No templates found for this filter —</option>
        <option value="__create_new__" style="color:#16a34a; font-weight:700;">➕ Create / Add Template for this Segment...</option>
      `,a&&(a.style.display="block"),this.onCanonicalTplChange();return}a&&(a.style.display="none");let m=`<option value="">— Select template (${r.length} available) —</option>`;m+='<option value="__create_new__" style="color:#16a34a; font-weight:700;">➕ Create / Add Template for this Segment...</option>',r.forEach(p=>{const g=p.segment?`[${p.segment}] `:"";m+=`<option value="${p.id}">${g}${this.escapeHtml(p.template_name||p.name||"Template #"+p.id)} (${p.category||"MARKETING"})</option>`}),t.innerHTML=m,e&&(t.value=String(e),this.onCanonicalTplChange())}toggleAddTemplateCard(e){const t=document.getElementById("uwaAddTplCard");if(!t)return;const a=t.style.display!=="none",i=e!==void 0?e:!a;if(t.style.display=i?"block":"none",i){const n=document.getElementById("uwaCanonicalSeg")?.value||this.detectSegment(),s=document.getElementById("uwaNewTplSeg");s&&n&&(s.value=n),document.getElementById("uwaNewTplName")?.focus()}}async saveNewTemplate(){const e=document.getElementById("uwaNewTplName"),t=document.getElementById("uwaNewTplSeg"),a=document.getElementById("uwaNewTplBody"),i=document.getElementById("uwaSaveNewTplBtn"),n=(e?.value||"").trim(),s=t?.value||"general",l=(a?.value||"").trim();if(!n){this.showFeedback("Please enter a template name.","error");return}if(!l){this.showFeedback("Please enter the template message body.","error");return}i&&(i.disabled=!0);const o=n.toLowerCase().replace(/[^a-z0-9]+/g,"_").replace(/^_+|_+$/g,"").slice(0,40);try{const d=await C.post("/whatsapp-config/templates",{name:n,slug:o,category:"MARKETING",segment:s,body_text:l,language:"en",usage_scope:"all"});if(d?.success){this.showFeedback(`✅ Template "${n}" created & approved for WhatsApp API!`,"success"),this.toggleAddTemplateCard(!1),e&&(e.value=""),a&&(a.value="");const r=document.getElementById("uwaCanonicalSeg");r&&(r.value=s);const m=d.template?.id||d.id||o;await this.loadCanonicalTemplates(m)}else this.showFeedback(d?.error||"Failed to create template","error")}catch(d){this.showFeedback(`Error creating template: ${d.message||"Server error"}`,"error")}finally{i&&(i.disabled=!1)}}detectSegment(){if(this.currentOptions?.segment)return this.currentOptions.segment;const e=(this.currentOptions?.context||"").toLowerCase();return e.includes("solar")?"solar":e.includes("real")||e.includes("property")||e.includes("estate")?"myntreal_real":e.includes("spare")?"EV_SPARES":e.includes("ev")||e.includes("vehicle")||e.includes("zynova")?"ev_b2c":e.includes("train")||e.includes("skill")||e.includes("etc")?"etc_training":e.includes("partner")?"partner":e.includes("staff")?"staff":e.includes("vgk")?"vgk":"general"}onCanonicalTplChange(){const e=document.getElementById("uwaCanonicalTpl"),t=document.getElementById("uwaCanonicalVarsWrap"),a=document.getElementById("uwaCanonicalVarsBox"),i=e?.value;if(i==="__create_new__"){this.toggleAddTemplateCard(!0),e.value="";return}if(!i){t&&(t.style.display="none"),a&&(a.innerHTML="");return}const n=this.canonicalTemplates.find(o=>String(o.id)===String(i)||String(o.slug)===String(i));if(!n)return;this.selectedCanonicalBody=n.body_text||n.content||n.body||"";const s=this.selectedCanonicalBody.match(/\{\{(\d+)\}\}/g)||[],l=[];if(s.forEach(o=>{const d=o.replace(/[\{\}]/g,"");l.includes(d)||l.push(d)}),l.sort((o,d)=>Number(o)-Number(d)),l.length&&a&&t){t.style.display="block";let o="";l.forEach(d=>{const r=d==="1"&&this.currentOptions?.name||"";o+=`
          <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px;">
            <label style="font-size:11px; font-weight:700; width:28px; color:#475569;">#${d}</label>
            <input type="text" class="uwa-canonical-var-inp" data-var-idx="${d}" value="${this.escapeHtml(r)}" placeholder="Value for {{${d}}}" style="flex:1; font-size:12px; border:1px solid #cbd5e1; border-radius:6px; padding:4px 8px;" />
          </div>
        `}),a.innerHTML=o,a.querySelectorAll(".uwa-canonical-var-inp").forEach(d=>{d.addEventListener("input",()=>this.buildCanonicalPreview())})}else t&&(t.style.display="none"),a&&(a.innerHTML="");this.buildCanonicalPreview()}buildCanonicalPreview(){let e=this.selectedCanonicalBody||"";(e.match(/\{\{(\d+)\}\}/g)||[]).forEach(n=>{const s=n.replace(/[\{\}]/g,""),o=document.querySelector(`.uwa-canonical-var-inp[data-var-idx="${s}"]`)?.value||`{{${s}}}`;e=e.replace(new RegExp(`\\{\\{${s}\\}\\}`,"g"),o)});const a=this.getSenderSignature(),i=document.getElementById("uwaMessageText");i&&e&&(i.value=e+a)}open(e){this.currentOptions=e,this.activeMode="meta_api",this.render()}close(){this.modalEl&&(this.modalEl.remove(),this.modalEl=null)}render(){if(this.close(),!this.currentOptions)return;const{phone:e,name:t,context:a,defaultMessage:i,catalogKey:n}=this.currentOptions,s=(e||"").replace(/\D/g,"").slice(-10),l=this.getSenderSignature(),o=(i||(n?this.getDigitalCatalogMessage(n,this.selectedCatalogLang):this.getVerticalQuickMessage("thanks_connecting")))+l;this.modalEl=document.createElement("div"),this.modalEl.id="unifiedWAModal",this.modalEl.className="uwa-modal-backdrop",this.modalEl.innerHTML=`
      <div class="uwa-modal-sheet">
        <!-- Header -->
        <div class="uwa-header">
          <div class="uwa-header-info">
            <div class="uwa-badge-online">
              <span class="uwa-dot"></span> Common Number Connected
            </div>
            <h3 class="uwa-title"><i class="fab fa-whatsapp me-1"></i> Send WhatsApp</h3>
            <div class="uwa-recipient-sub">
              <strong>${this.escapeHtml(t||"Customer")}</strong> · ${this.maskPhone(s)}
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

        <!-- 1-Tap Digital Catalog Share -->
        <div class="uwa-section-label">📖 Send Digital Catalog</div>
        <div style="background:#f0fdf4; border:1.5px solid #86efac; border-radius:10px; padding:10px; margin-bottom:12px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; gap:6px; flex-wrap:wrap;">
            <div style="display:flex; align-items:center; gap:6px; flex:1; min-width:160px;">
              <i class="fas fa-book-open" style="color:#15803d; font-size:13px;"></i>
              <select id="uwaDigitalCatSel" style="flex:1; font-size:11px; font-weight:700; color:#166534; background:#fff; border:1.5px solid #86efac; border-radius:6px; padding:4px 6px; cursor:pointer; outline:none;">
                <option value="solar">☀️ Solar Rooftop &amp; EPC</option>
                <option value="industrial_hub">🏢 MyntReal Hub (5-in-1 Franchise)</option>
                <option value="hub_pricing">🏷️ Hub Commercials &amp; Pricing (24h)</option>
                <option value="ev_b2b">🚚 Commercial EV Fleet &amp; Cargo (B2B)</option>
                <option value="ev_b2c">⚡ Smart Electric 2-Wheelers (B2C)</option>
                <option value="ev_spares">⚙️ EV Spares, Chargers &amp; Batteries</option>
                <option value="etc_training">🎓 ETC EV Technician Certifications</option>
                <option value="real_estate">🏡 Premium Real Estate &amp; Townships</option>
                <option value="insurance">🛡️ Comprehensive Insurance Advisory</option>
              </select>
            </div>
            <div style="display:flex; gap:3px;" id="uwaDigitalCatLangPills">
              <button type="button" class="uwa-cat-lang-btn" data-lang="te" style="padding:2px 7px; border-radius:5px; border:1px solid #16a34a; background:#16a34a; color:#fff; font-size:10.5px; font-weight:700; cursor:pointer;">తెలుగు</button>
              <button type="button" class="uwa-cat-lang-btn" data-lang="en" style="padding:2px 7px; border-radius:5px; border:1px solid #cbd5e1; background:#fff; color:#334155; font-size:10.5px; font-weight:600; cursor:pointer;">EN</button>
              <button type="button" class="uwa-cat-lang-btn" data-lang="hi" style="padding:2px 7px; border-radius:5px; border:1px solid #cbd5e1; background:#fff; color:#334155; font-size:10.5px; font-weight:600; cursor:pointer;">हिन्दी</button>
              <button type="button" class="uwa-cat-lang-btn" data-lang="ta" style="padding:2px 7px; border-radius:5px; border:1px solid #cbd5e1; background:#fff; color:#334155; font-size:10.5px; font-weight:600; cursor:pointer;">தமிழ்</button>
            </div>
          </div>
          <div id="uwaDigitalCatDesc" style="font-size:10.5px; color:#15803d; line-height:1.4; margin-bottom:8px;">
            Sends personalized Har Ghar Solar Digital Catalog link with 90% savings, ₹78,000 subsidy &amp; ₹1 scheme details.
          </div>
          <button type="button" id="uwaInsertDigitalCatBtn" style="width:100%; padding:6px 10px; background:#15803d; color:#fff; border:none; border-radius:7px; font-size:11.5px; font-weight:700; cursor:pointer; display:flex; align-items:center; justify-content:center; gap:6px;">
            <i class="fas fa-link"></i> <span id="uwaDigitalCatBtnLabel">Insert Personalized Solar Catalog Link</span>
          </button>
        </div>

        <!-- Official Meta / Database Templates -->
        <div class="uwa-section-label">📑 Select Official Template</div>
        <div style="display:flex; gap:6px; margin-bottom:8px;">
          <select id="uwaCanonicalSeg" style="flex:1; font-size:11.5px; padding:6px; border:1px solid #cbd5e1; border-radius:8px; background:#fff;">
            <option value="">🏢 All Segments</option>
            <option value="solar">☀️ Solar</option>
            <option value="general">💬 General</option>
            <option value="myntreal_real">🏡 Real Estate</option>
            <option value="ev_b2c">⚡ EV B2C</option>
            <option value="ev_b2b">⚡ EV B2B</option>
            <option value="EV_SPARES">🔧 EV Spares</option>
            <option value="etc_training">🎓 ETC Training</option>
            <option value="partner">🤝 Channel Partner</option>
            <option value="leads">🎯 CRM Leads</option>
            <option value="staff">👔 Internal Staff</option>
            <option value="vgk">💼 VGK Executive</option>
            <option value="system">⚙️ System</option>
          </select>
          <select id="uwaCanonicalCat" style="flex:1; font-size:11.5px; padding:6px; border:1px solid #cbd5e1; border-radius:8px; background:#fff;">
            <option value="">All Categories</option>
            <option value="MARKETING">Marketing</option>
            <option value="UTILITY">Utility</option>
            <option value="AUTHENTICATION">Authentication</option>
          </select>
        </div>

        <!-- Template Search and Add Row -->
        <div style="display:flex; gap:6px; margin-bottom:8px;">
          <div style="position:relative; flex:1;">
            <input type="text" id="uwaCanonicalSearch" placeholder="🔍 Search template content or name..." style="width:100%; font-size:11.5px; border:1px solid #cbd5e1; border-radius:8px; padding:6px 10px; background:#fff; outline:none;" />
          </div>
          <button type="button" id="uwaToggleAddTplBtn" style="padding:5px 9px; font-size:11px; font-weight:700; background:#f0fdf4; color:#15803d; border:1px solid #86efac; border-radius:8px; cursor:pointer; white-space:nowrap;">
            <i class="fas fa-plus"></i> Add
          </button>
        </div>

        <!-- Inline Add New Template Card (collapsible) -->
        <div id="uwaAddTplCard" style="display:none; background:#f8fafc; border:1.5px dashed #16a34a; border-radius:10px; padding:10px; margin-bottom:10px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
            <strong style="font-size:12px; color:#15803d;"><i class="fas fa-plus-circle me-1"></i>New Approved Template</strong>
            <button type="button" id="uwaCancelAddTplBtn" style="background:none; border:none; color:#64748b; font-size:16px; cursor:pointer;">&times;</button>
          </div>
          <div style="display:flex; gap:6px; margin-bottom:6px;">
            <input type="text" id="uwaNewTplName" placeholder="Template Name *" style="flex:2; font-size:11.5px; border:1px solid #cbd5e1; border-radius:6px; padding:5px 8px;" />
            <select id="uwaNewTplSeg" style="flex:1; font-size:11px; border:1px solid #cbd5e1; border-radius:6px; padding:5px 6px; background:#fff;">
              <option value="solar">☀️ Solar</option>
              <option value="general">💬 General</option>
              <option value="myntreal_real">🏡 Real Estate</option>
              <option value="ev_b2c">⚡ EV B2C</option>
              <option value="ev_b2b">⚡ EV B2B</option>
              <option value="EV_SPARES">🔧 EV Spares</option>
              <option value="etc_training">🎓 ETC Training</option>
              <option value="partner">🤝 Partner</option>
              <option value="leads">🎯 Leads</option>
              <option value="staff">👔 Staff</option>
              <option value="vgk">💼 VGK</option>
              <option value="system">⚙️ System</option>
            </select>
          </div>
          <textarea id="uwaNewTplBody" rows="3" placeholder="Template message content with {{1}} customer name, {{2}} details..." style="width:100%; font-size:11.5px; border:1px solid #cbd5e1; border-radius:6px; padding:6px 8px; margin-bottom:6px;"></textarea>
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <small style="font-size:10px; color:#15803d;"><i class="fas fa-check"></i> Auto-approved for API</small>
            <button type="button" id="uwaSaveNewTplBtn" style="padding:4px 10px; font-size:11.5px; font-weight:700; background:#16a34a; color:#fff; border:none; border-radius:6px; cursor:pointer;">
              Save &amp; Use
            </button>
          </div>
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
          ${Object.entries(H).map(([g,h])=>`
            <button class="uwa-chip-btn" data-tpl-key="${g}">
              ${h.label}
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
        <textarea id="uwaMessageText" class="uwa-textarea" rows="7" placeholder="Type your WhatsApp message...">${this.escapeHtml(o)}</textarea>

        <!-- Status & Result feedback -->
        <div id="uwaFeedbackBox" class="uwa-feedback-box" style="display:none;"></div>

        <!-- Action Footer -->
        <div class="uwa-footer">
          <button class="btn btn-outline uwa-cancel-btn" id="uwaCancelBtn">Cancel</button>
          <button class="btn btn-primary uwa-send-btn" id="uwaSendBtn">
            <i class="fas fa-paper-plane me-1"></i>
            <span id="uwaSendBtnLabel">Send via 🏢 Official WhatsApp</span>
          </button>
        </div>
      </div>
    `,document.body.appendChild(this.modalEl);const d=this.detectSegment(),r=document.getElementById("uwaCanonicalSeg");r&&d&&(r.value=d);const m=this.detectCatalogKey(),p=document.getElementById("uwaDigitalCatSel");p&&m&&(p.value=m),this.onDigitalCatalogSelect(m),this.attachEvents(),this.updateModeUI(),this.loadCanonicalTemplates()}attachEvents(){this.modalEl&&(document.getElementById("uwaCloseBtn")?.addEventListener("click",()=>this.close()),document.getElementById("uwaCancelBtn")?.addEventListener("click",()=>this.close()),document.getElementById("uwaQuickThanksBtn")?.addEventListener("click",()=>this.applyVerticalQuick("thanks_connecting")),document.getElementById("uwaQuickReachBtn")?.addEventListener("click",()=>this.applyVerticalQuick("trying_to_reach")),document.getElementById("uwaDigitalCatSel")?.addEventListener("change",e=>{this.onDigitalCatalogSelect(e.target.value)}),this.modalEl.querySelectorAll(".uwa-cat-lang-btn").forEach(e=>{e.addEventListener("click",t=>{const a=t.currentTarget.getAttribute("data-lang")||"te";this.applyDigitalCatalog(a)})}),document.getElementById("uwaInsertDigitalCatBtn")?.addEventListener("click",()=>{this.applyDigitalCatalog()}),document.getElementById("uwaCanonicalSeg")?.addEventListener("change",()=>this.filterCanonicalTemplates()),document.getElementById("uwaCanonicalCat")?.addEventListener("change",()=>this.filterCanonicalTemplates()),document.getElementById("uwaCanonicalSearch")?.addEventListener("input",()=>this.filterCanonicalTemplates()),document.getElementById("uwaCanonicalTpl")?.addEventListener("change",()=>this.onCanonicalTplChange()),document.getElementById("uwaToggleAddTplBtn")?.addEventListener("click",()=>this.toggleAddTemplateCard()),document.getElementById("uwaCancelAddTplBtn")?.addEventListener("click",()=>this.toggleAddTemplateCard(!1)),document.getElementById("uwaSaveNewTplBtn")?.addEventListener("click",()=>this.saveNewTemplate()),document.getElementById("uwaModeScannedBtn")?.addEventListener("click",()=>{this.activeMode="scanned",this.updateModeUI(),this.loadCanonicalTemplates()}),document.getElementById("uwaModeMetaBtn")?.addEventListener("click",()=>{this.activeMode="meta_api",this.updateModeUI(),this.loadCanonicalTemplates()}),this.modalEl.querySelectorAll(".uwa-chip-btn").forEach(e=>{e.addEventListener("click",t=>{const a=t.currentTarget.dataset.tplKey;if(a&&H[a]){const i=this.getSenderSignature(),n=document.getElementById("uwaMessageText");n&&(n.value=H[a].text+i,n.focus())}})}),document.getElementById("uwaSendBtn")?.addEventListener("click",()=>this.handleSend()))}updateModeUI(){const e=document.getElementById("uwaModeScannedBtn"),t=document.getElementById("uwaModeMetaBtn"),a=document.getElementById("uwaSendBtnLabel"),i=document.getElementById("uwaSendBtn");this.activeMode==="scanned"?(e?.classList.add("active"),t?.classList.remove("active"),a&&(a.textContent="Send via 📱 Scanned WhatsApp"),i&&(i.style.background="#16a34a")):(e?.classList.remove("active"),t?.classList.add("active"),a&&(a.textContent="Send via 🏢 Official WhatsApp"),i&&(i.style.background="#2563eb"))}async handleSend(){if(!this.currentOptions)return;const e=document.getElementById("uwaMessageText"),t=document.getElementById("uwaSendBtn"),a=document.getElementById("uwaSendBtnLabel");let i=(e?.value||"").trim();if(!i){this.showFeedback("Please enter a message to send.","error");return}const n=this.getSenderSignature();i.toLowerCase().includes("regards,")||(i=i+n);const{phone:s,name:l,leadId:o}=this.currentOptions,d=(s||"").replace(/\D/g,"").slice(-10),r=!!(o&&o!=="new"&&!isNaN(Number(o)));if((!d||d.length<10)&&!r){this.showFeedback("Invalid recipient phone number.","error");return}if(t&&(t.disabled=!0),this.activeMode==="meta_api"){a&&(a.innerHTML='<i class="fas fa-spinner fa-spin me-1"></i> Sending via Meta API...'),this.showFeedback("Dispatching via WhatsApp Cloud API...","info");try{const m=r?Number(o):0,p=await C.post(`/whatsapp-config/crm-lead-send/${m}`,{phone:d.length>=10?d:void 0,custom_message:i,send_mode:"company"});if(p.success)this.currentOptions.catalogId&&C.post(`/digital-catalogs/${this.currentOptions.catalogId}/log-dispatch`,{lead_id:r?Number(o):null,phone:d,name:l||null,channel:"whatsapp",mode:"company",send_status:"sent"}).catch(g=>console.warn("[UnifiedWAModal] log-dispatch error:",g)),a&&(a.innerHTML='<i class="fas fa-check me-1"></i> Sent Successfully ✓'),this.showFeedback("✅ Dispatched via WhatsApp Meta Cloud API (Official Business)","success"),setTimeout(()=>this.close(),2500);else{const g=p.error||p.data?.reason||"Meta API not available.";this.showFeedback(`❌ Meta API Error: ${g}`,"error"),t&&(t.disabled=!1),a&&(a.textContent="Retry Send")}}catch(m){console.warn("[UnifiedWAModal] Meta API failed:",m),this.showFeedback(`❌ Meta API Network error: ${m.message||"Server unreachable"}`,"error"),t&&(t.disabled=!1),a&&(a.textContent="Retry Send")}return}a&&(a.innerHTML='<i class="fas fa-spinner fa-spin me-1"></i> Sending via Personal WA...'),this.showFeedback("Connecting to WhatsApp Bot Gateway...","info");try{const m=await C.post("/whatsapp/send-message",{recipient:d.length>=10?d:"LEAD_RESOLVE",message:i,recipient_type:"individual",recipient_name:l||"Customer",lead_id:r?Number(o):o||null});if(m.success)this.currentOptions.catalogId&&C.post(`/digital-catalogs/${this.currentOptions.catalogId}/log-dispatch`,{lead_id:r?Number(o):null,phone:d,name:l||null,channel:"whatsapp",mode:"scanned",send_status:"sent"}).catch(p=>console.warn("[UnifiedWAModal] log-dispatch error:",p)),a&&(a.innerHTML='<i class="fas fa-check me-1"></i> Sent Successfully ✓'),this.showFeedback(`✅ Dispatched via Personal Scanned WhatsApp! Sender: ${this.escapeHtml(y.getAuthState().user?.full_name||"Staff")}`,"success"),setTimeout(()=>this.close(),2500);else{const p=m.error||"Personal WhatsApp Web is disconnected or unlinked.";this.showFeedback(`❌ Personal WA: ${p}. You can switch to "WhatsApp API" mode above to send via Official Meta Business.`,"error"),t&&(t.disabled=!1),a&&(a.textContent="Retry Send")}}catch(m){console.error("[UnifiedWAModal] Send error:",m),this.showFeedback('❌ Personal WhatsApp Gateway offline. You can switch to "WhatsApp API" above to send via Meta Cloud.',"error"),t&&(t.disabled=!1),a&&(a.textContent="Retry Send")}}showFeedback(e,t){const a=document.getElementById("uwaFeedbackBox");a&&(a.style.display="block",a.className=`uwa-feedback-box ${t}`,a.innerHTML=e)}maskPhone(e){if(!e)return"-";const t=String(e).replace(/\D/g,"");return t.length>=10?"+91 "+t.slice(-10,-8)+"••••"+t.slice(-4):t.length>=4?"••••"+t.slice(-4):"••••"}escapeHtml(e){const t={"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"};return(e||"").replace(/[&<>"']/g,a=>t[a])}}const xe=new ie;class ne{modalEl=null;currentOptions=null;staffList=[];isLoadingStaff=!1;async open(e){this.currentOptions=e,this.render(),await this.loadStaff()}close(){this.modalEl&&(this.modalEl.remove(),this.modalEl=null),this.currentOptions=null}escapeHtml(e){const t=document.createElement("div");return t.textContent=e||"",t.innerHTML}maskPhone(e){const t=(e||"").replace(/\D/g,"");return t.length<6?e||"":t.slice(0,2)+"••••"+t.slice(-4)}async loadStaff(){const e=document.getElementById("usmStaffSelect");if(e){e.innerHTML='<option value="">— Loading staff members… —</option>',this.isLoadingStaff=!0;try{const t=await C.get("/crm/leads/shareable-staff"),a=t?.staff||t?.data?.staff||[];this.staffList=a;const n=(y.getAuthState().user||{}).id;if(!a.length){e.innerHTML='<option value="">No active staff members found</option>';return}let s='<option value="">— Select Staff Member for Follow-up —</option>';a.forEach(l=>{const o=n&&l.id===n,d=[l.role,l.department].filter(Boolean).join(" · ");s+=`<option value="${l.id}" data-phone="${l.phone||""}">${this.escapeHtml(l.name)} (${l.emp_code})${d?" — "+this.escapeHtml(d):""}${o?" [You]":""}</option>`}),e.innerHTML=s}catch(t){console.error("[UnifiedShareLeadModal] Failed to load staff:",t),e.innerHTML='<option value="">Failed to load staff list</option>'}finally{this.isLoadingStaff=!1,this.updatePreview()}}}render(){this.modalEl&&this.modalEl.remove();const e=this.currentOptions;if(!e)return;const t=document.createElement("div");t.id="unifiedShareLeadModal",t.style.cssText=["position: fixed","inset: 0","z-index: 100000","background: rgba(0, 0, 0, 0.75)","display: flex","align-items: flex-end","justify-content: center",'font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'].join(";");const a=this.maskPhone(e.phone);t.innerHTML=`
      <div class="usm-content" style="
        background: #0f172a;
        width: 100%;
        max-width: 520px;
        max-height: 92vh;
        border-radius: 24px 24px 0 0;
        display: flex;
        flex-direction: column;
        overflow: hidden;
        color: #f8fafc;
        border: 1px solid rgba(255,255,255,0.12);
        box-shadow: 0 -10px 40px rgba(0,0,0,0.8);
        animation: usmSlideUp 0.25s ease-out;
      ">
        <style>
          @keyframes usmSlideUp { from { transform: translateY(100%); } to { transform: translateY(0); } }
          .usm-btn { border:none; border-radius:12px; font-weight:700; cursor:pointer; transition:all 0.15s ease; }
          .usm-btn:active { transform: scale(0.98); }
          .usm-input { width:100%; background:#1e293b; border:1px solid #334155; border-radius:10px; color:#f8fafc; padding:10px 12px; font-size:14px; box-sizing:border-box; }
          .usm-input:focus { outline:none; border-color:#0ea5e9; }
        </style>

        <!-- Header -->
        <div style="background:linear-gradient(135deg, #0284c7 0%, #0369a1 100%); padding:16px 20px; display:flex; align-items:center; justify-content:space-between;">
          <div style="display:flex; align-items:center; gap:10px;">
            <div style="background:rgba(255,255,255,0.2); width:36px; height:36px; border-radius:10px; display:flex; align-items:center; justify-content:center; font-size:18px;">
              📤
            </div>
            <div>
              <div style="font-size:16px; font-weight:800; color:white; line-height:1.2;">Share Lead Details</div>
              <div style="font-size:12px; color:rgba(255,255,255,0.85);">${this.escapeHtml(e.name)} · ${a}</div>
            </div>
          </div>
          <button id="usmCloseBtn" style="background:rgba(255,255,255,0.2); border:none; color:white; width:32px; height:32px; border-radius:8px; font-size:18px; cursor:pointer; display:flex; align-items:center; justify-content:center;">✕</button>
        </div>

        <!-- Body -->
        <div style="padding:16px 20px; overflow-y:auto; flex:1; display:flex; flex-direction:column; gap:14px;">
          
          <!-- Lead Summary Card -->
          <div style="background:#1e293b; border:1px solid #334155; border-radius:12px; padding:12px 14px; font-size:12px; line-height:1.5;">
            <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
              <span style="color:#94a3b8;">Lead ID:</span>
              <span style="font-weight:700; color:#38bdf8;">#${e.leadId}</span>
            </div>
            ${e.category?`
            <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
              <span style="color:#94a3b8;">Category:</span>
              <span style="font-weight:600; color:#cbd5e1;">${this.escapeHtml(e.category)}</span>
            </div>`:""}
            ${e.area||e.city?`
            <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
              <span style="color:#94a3b8;">Location:</span>
              <span style="font-weight:600; color:#cbd5e1;">${this.escapeHtml([e.area,e.city].filter(Boolean).join(", "))}</span>
            </div>`:""}
            ${e.requirements?`
            <div style="margin-top:6px; padding-top:6px; border-top:1px dashed #334155; color:#e2e8f0;">
              <b style="color:#94a3b8;">Needs:</b> ${this.escapeHtml(e.requirements)}
            </div>`:""}
          </div>

          <!-- Staff Selector -->
          <div>
            <label style="display:block; font-size:12px; font-weight:700; color:#94a3b8; margin-bottom:6px; text-transform:uppercase; letter-spacing:0.5px;">
              Select Staff Member for Follow-Up <span style="color:#ef4444;">*</span>
            </label>
            <select id="usmStaffSelect" class="usm-input" style="cursor:pointer;">
              <option value="">— Loading staff members… —</option>
            </select>
          </div>

          <!-- Follow-up Type -->
          <div>
            <label style="display:block; font-size:12px; font-weight:700; color:#94a3b8; margin-bottom:6px; text-transform:uppercase; letter-spacing:0.5px;">
              Follow-Up Purpose / Reason
            </label>
            <select id="usmFollowupType" class="usm-input" style="cursor:pointer;">
              <option value="site_visit">📍 Site Visit / Field Inspection</option>
              <option value="secondary_followup" selected>🔄 Secondary Follow-Up Call</option>
              <option value="quotation">📑 Quotation & Pricing Discussion</option>
              <option value="technical">⚡ Technical / Rooftop Feasibility</option>
              <option value="escalation">⚠️ Senior Escalation / Special Handling</option>
              <option value="general">💼 General Lead Follow-Up</option>
            </select>
          </div>

          <!-- Notes / Instructions -->
          <div>
            <label style="display:block; font-size:12px; font-weight:700; color:#94a3b8; margin-bottom:6px; text-transform:uppercase; letter-spacing:0.5px;">
              Instructions / Notes for Staff
            </label>
            <textarea id="usmNotes" class="usm-input" rows="2" placeholder="e.g., Customer is interested in 5kW On-grid solar. Please coordinate and visit tomorrow." style="resize:none;">${e.notes||""}</textarea>
          </div>

          <!-- Assign in CRM Checkbox -->
          <div style="display:flex; align-items:center; gap:8px; background:#1e293b; padding:10px 14px; border-radius:10px; border:1px solid #334155;">
            <input type="checkbox" id="usmAssignCheck" checked style="width:18px; height:18px; accent-color:#0ea5e9; cursor:pointer;">
            <label for="usmAssignCheck" style="font-size:13px; color:#e2e8f0; cursor:pointer; font-weight:600;">
              Assign as Secondary Follow-up in CRM
              <div style="font-size:11px; color:#94a3b8; font-weight:400;">Lead will appear in colleague's CRM & task queue</div>
            </label>
          </div>

          <!-- Message Preview Accordion -->
          <div style="background:#0b1329; border:1px solid #1e293b; border-radius:10px; padding:10px 12px;">
            <div style="font-size:11px; font-weight:700; color:#64748b; margin-bottom:4px; text-transform:uppercase;">
              WhatsApp Message Preview:
            </div>
            <div id="usmMessagePreview" style="font-size:11.5px; color:#94a3b8; white-space:pre-wrap; max-height:80px; overflow-y:auto; font-family:monospace; line-height:1.4;">
              Select a staff member to preview message...
            </div>
          </div>

        </div>

        <!-- Footer Actions -->
        <div style="padding:14px 20px; border-top:1px solid rgba(255,255,255,0.08); background:#0b1329; display:flex; flex-direction:column; gap:8px;">
          <div style="display:grid; grid-template-columns: 1fr 1fr; gap:10px;">
            <button id="usmWaOnlyBtn" class="usm-btn" style="background:#25D366; color:white; padding:12px; font-size:13px; display:flex; align-items:center; justify-content:center; gap:6px;">
              💬 WhatsApp Only
            </button>
            <button id="usmCrmOnlyBtn" class="usm-btn" style="background:#334155; color:#f8fafc; padding:12px; font-size:13px; display:flex; align-items:center; justify-content:center; gap:6px;">
              📋 Assign in CRM
            </button>
          </div>
          <button id="usmCombinedBtn" class="usm-btn" style="background:linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%); color:white; padding:14px; font-size:14px; box-shadow:0 4px 14px rgba(14,165,233,0.4); display:flex; align-items:center; justify-content:center; gap:8px;">
            🚀 Assign & WhatsApp Colleague
          </button>
        </div>
      </div>
    `,document.body.appendChild(t),this.modalEl=t,document.getElementById("usmCloseBtn")?.addEventListener("click",()=>this.close()),t.addEventListener("click",l=>{l.target===t&&this.close()}),document.getElementById("usmStaffSelect")?.addEventListener("change",()=>this.updatePreview()),document.getElementById("usmFollowupType")?.addEventListener("change",()=>this.updatePreview()),document.getElementById("usmNotes")?.addEventListener("input",()=>this.updatePreview()),document.getElementById("usmWaOnlyBtn")?.addEventListener("click",()=>this.executeShare("wa_only")),document.getElementById("usmCrmOnlyBtn")?.addEventListener("click",()=>this.executeShare("crm_only")),document.getElementById("usmCombinedBtn")?.addEventListener("click",()=>this.executeShare("combined"))}updatePreview(){const e=document.getElementById("usmMessagePreview");if(!e||!this.currentOptions)return;const a=document.getElementById("usmStaffSelect")?.value;this.staffList.find(h=>String(h.id)===String(a));const i=document.getElementById("usmFollowupType")?.value||"secondary_followup",n=document.getElementById("usmNotes")?.value||"",s=y.getAuthState().user||{},l=s.full_name||s.name||"Telecaller",o=this.currentOptions,d={site_visit:"Site Visit / Field Inspection",secondary_followup:"Secondary Follow-Up Call",quotation:"Quotation & Pricing Discussion",technical:"Technical / Rooftop Feasibility",escalation:"Senior Escalation / Special Handling",general:"General Lead Follow-Up"}[i]||"Secondary Follow-Up",r=o.budgetMin||o.budgetMax?`₹${((o.budgetMin||0)/1e5).toFixed(1)}L - ₹${((o.budgetMax||o.budgetMin||0)/1e5).toFixed(1)}L`:"",m=`https://www.myntreal.com/staff/softphone?lead_id=${o.leadId}&auto_dial=1`,p=`https://www.myntreal.com/staff/leads?lead_id=${o.leadId}`,g=["📢 *LEAD DETAILS FOR SECONDARY FOLLOW-UP*","",`👤 *Customer*: ${o.name}`,`📱 *Phone*: ${o.phone}`,o.area||o.city?`📍 *Location*: ${[o.area,o.city].filter(Boolean).join(", ")}`:null,o.category?`🏷️ *Category*: ${o.category}`:null,`🎯 *Purpose*: ${d}`,o.requirements?`📝 *Requirement*: ${o.requirements}`:null,r?`💰 *Budget*: ${r}`:null,n?`💬 *Notes*: ${n}`:null,`👉 *Shared by*: ${l}`,"",`📞 *Call via Softphone*: ${m}`,`🔗 *View Lead in CRM*: ${p}`].filter(Boolean).join(`
`);e.textContent=g}async executeShare(e){const t=document.getElementById("usmStaffSelect"),a=parseInt(t?.value||"0",10);if(!a){alert("Please select a staff member to share details with."),t?.focus();return}const i=this.staffList.find(p=>p.id===a);if(!i){alert("Selected staff member is invalid.");return}const n=document.getElementById("usmFollowupType")?.value||"secondary_followup",s=document.getElementById("usmNotes")?.value.trim()||"",l=document.getElementById("usmAssignCheck")?.checked||!1,o=this.currentOptions;if(!o)return;const d=document.getElementById("usmCombinedBtn"),r=document.getElementById("usmCrmOnlyBtn"),m=document.getElementById("usmWaOnlyBtn");[d,r,m].forEach(p=>{p&&(p.disabled=!0)});try{let p="",g="";if(e==="crm_only"||e==="combined"||l){const b={target_staff_id:a,followup_type:n,notes:s,assign_as_secondary:l},k=await C.post(`/crm/leads/${o.leadId}/share-details`,b);if(k&&k.success)p=k.wa_url||"",g=k.wa_message||"",o.onShared&&o.onShared(k);else throw new Error(k?.detail||k?.message||"Failed to assign lead in CRM")}if(e==="wa_only"||e==="combined"){if(!p){const b=(i.phone||"").replace(/\D/g,"").slice(-10);if(!b)alert(`Colleague ${i.name} does not have a valid mobile number for WhatsApp.`);else{const k=document.getElementById("usmMessagePreview")?.textContent||"";p=`https://wa.me/91${b}?text=${encodeURIComponent(k)}`}}p&&window.open(p,"_blank")}const h=e==="crm_only"?`Lead successfully assigned to ${i.name} in CRM!`:e==="wa_only"?`WhatsApp launched for ${i.name}!`:`Lead assigned in CRM and WhatsApp opened for ${i.name}!`;alert(`✅ ${h}`),this.close()}catch(p){console.error("[UnifiedShareLeadModal] Share failed:",p),alert(`⚠️ Could not complete lead share: ${p.message||p}`)}finally{[d,r,m].forEach(p=>{p&&(p.disabled=!1)})}}}const we=new ne,se=[{menu_code:"HOME_DASHBOARD",label:"Home Dashboard",route:"mnr-dashboard",icon:"home"},{menu_code:"VIEW_PROFILE",label:"View Profile",route:"mnr-profile",icon:"user"},{menu_code:"ADD_MEMBER",label:"Add Member",route:"mnr-add-member",icon:"user-plus"}],oe=[{section_code:"ANNOUNCEMENTS",section_label:"📢 Community Updates",icon:"bullhorn",order:1,items:[{menu_code:"PUBLIC_ANNOUNCEMENTS",label:"📢 Official Updates",route:"mnr-announcements"},{menu_code:"MY_SUBMISSIONS",label:"📋 My Submissions",route:"mnr-my-announcements"},{menu_code:"PENDING",label:"⏳ Pending",route:"mnr-announcements-pending"},{menu_code:"APPROVED",label:"✅ Approved",route:"mnr-announcements-approved"},{menu_code:"REJECTED",label:"❌ Rejected",route:"mnr-announcements-rejected"}]},{section_code:"COUPON_MODULES",section_label:"🎫 Coupon Modules",icon:"ticket",order:2,items:[{menu_code:"BUY_COUPON",label:"🛒 Buy Coupon",route:"mnr-coupon-buy"},{menu_code:"ACTIVATE_COUPON",label:"✅ Activate Coupon",route:"mnr-coupon-activate"},{menu_code:"COUPON_STATUS",label:"🎫 Coupon Status",route:"mnr-coupon-status"},{menu_code:"COUPON_PROGRESS",label:"📊 Coupon Progress",route:"mnr-coupon-progress"},{menu_code:"COUPON_TRANSFER",label:"🔄 Coupon Transfer",route:"mnr-coupon-transfer"}]},{section_code:"MEMBERS",section_label:"👥 My Connections",icon:"users",order:3,items:[{menu_code:"ALL_MEMBERS",label:"👥 All Connections",route:"mnr-members-all"},{menu_code:"DIRECT_REFERRALS",label:"🔗 Direct Connections",route:"mnr-referrals"},{menu_code:"PICTURE_VIEW",label:"🌳 Connections Gallery",route:"mnr-members-picture"},{menu_code:"VED_TEAM",label:"👑 Leadership Group (VED)",route:"mnr-members-ved"}]},{section_code:"MNR",section_label:"💰 Facilitation & Recognition",icon:"coins",order:4,items:[{menu_code:"EARNINGS_SUMMARY",label:"📊 Earnings Overview",route:"mnr-earnings-summary"},{menu_code:"DIRECT_REFERRAL",label:"💰 Direct Business Facilitation",route:"mnr-income-direct"},{menu_code:"MATCHING_REFERRAL",label:"🤝 Group Performance Recognition",route:"mnr-income-matching"},{menu_code:"VED_INCOME",label:"👑 VED Leadership Recognition",route:"mnr-income-ved"},{menu_code:"GURUDAKSHINA",label:"🙏 Mentorship Contribution Benefit",route:"mnr-income-guru"},{menu_code:"FIELD_ALLOWANCE",label:"🚗 Field Allowances",route:"mnr-income-field"},{menu_code:"WITHDRAWALS",label:"💸 Withdrawals",route:"mnr-withdrawals"},{menu_code:"COUPON_BENEFITS",label:"🎁 Coupon Benefits",route:"mnr-benefits"},{menu_code:"MNR_POINTS",label:"🎯 Points Utilisation",route:"mnr-points"}]},{section_code:"MYNTREAL",section_label:"💎 MyntReal",icon:"gem",order:5,items:[{menu_code:"MY_LEADS",label:"📋 My Leads",route:"mnr-my-leads"},{menu_code:"FRANCHISE_EARNINGS",label:"🏪 Franchise Earnings",route:"mnr-franchise-earnings"}]},{section_code:"ZYNOVA",section_label:"⭐ Zynova",icon:"crown",order:6,items:[{menu_code:"VGK_REAL_DREAMS",label:"🏠 VGK Real Dreams (Real Estate)",route:"zynova-real-estate"},{menu_code:"VGK_CARE",label:"🛡️ VGK Care (Insurance)",route:"zynova-insurance"},{menu_code:"ETC",label:"🎓 EVolution Training Center (ETC)",route:"zynova-training"}]},{section_code:"AWARDS_BONANZA",section_label:"🏆 Awards & Bonanza",icon:"trophy",order:7,items:[{menu_code:"AWARDS",label:"🏆 Awards",route:"mnr-awards"},{menu_code:"BONANZA_AWARDS",label:"🎉 Bonanza Awards",route:"mnr-bonanza"}]}],re=[{menu_code:"THEME_MODE",label:"Theme Mode",route:"mnr-settings",icon:"headset"},{menu_code:"SECURITY_SETTINGS",label:"Security Settings",route:"mnr-change-password",icon:"headset"}];class le{container=null;overlay=null;isOpen=!1;expandedSections=new Set;user=null;constructor(){this.createElements()}createElements(){this.overlay=document.createElement("div"),this.overlay.className="mnr-drawer-overlay",this.overlay.addEventListener("click",()=>this.close()),document.body.appendChild(this.overlay),this.container=document.createElement("div"),this.container.className="mnr-side-drawer",this.container.innerHTML=this.render(),document.body.appendChild(this.container),this.attachEventListeners()}setUser(e){this.user=e,this.updateUI()}getIcon(e){return`<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${{home:'<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>',user:'<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',"user-plus":'<path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="8.5" cy="7" r="4"/><line x1="20" y1="8" x2="20" y2="14"/><line x1="23" y1="11" x2="17" y2="11"/>',bullhorn:'<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/>',ticket:'<path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/>',users:'<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',coins:'<circle cx="8" cy="8" r="6"/><path d="M18.09 10.37A6 6 0 1 1 10.34 18"/><path d="M7 6h1v4"/><path d="m16.71 13.88.7.71-2.82 2.82"/>',gem:'<polygon points="12 2 2 12 12 22 22 12 12 2"/><polyline points="12 2 12 22"/>',crown:'<path d="m2 4 3 12h14l3-12-6 7-4-7-4 7-6-7zm3 16h14"/>',trophy:'<path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/><path d="M4 22h16"/><path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"/><path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"/><path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"/>',headset:'<path d="M3 18v-6a9 9 0 0 1 18 0v6"/><path d="M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3zM3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3z"/>',logout:'<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>'}[e]||""}</svg>`}render(){const e=this.user?.name||"MNR Member",t=this.user?.mnr_id||"";return`
      <div class="mnr-drawer-header">
        <div class="mnr-drawer-user">
          <div class="mnr-user-avatar">${e.split(" ").map(i=>i[0]).join("").toUpperCase().slice(0,2)}</div>
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
          ${se.map(i=>`
            <div class="mnr-menu-item top-item" data-route="${i.route}">
              ${this.getIcon(i.icon||"home")}
              <span>${i.label}</span>
            </div>
          `).join("")}
        </div>

        <!-- Section menus -->
        ${oe.map(i=>this.renderSection(i)).join("")}

        <!-- Bottom items -->
        <div class="mnr-bottom-menu">
          ${re.map(i=>`
            <div class="mnr-menu-item bottom-item" data-route="${i.route}">
              ${this.getIcon(i.icon||"help-circle")}
              <span>${i.label}</span>
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
    `}attachEventListeners(){this.container&&(document.getElementById("mnrDrawerClose")?.addEventListener("click",()=>this.close()),this.container.querySelectorAll("[data-toggle]").forEach(e=>{e.addEventListener("click",t=>{const a=e.dataset.toggle;this.toggleSection(a),t.stopPropagation()})}),this.container.querySelectorAll("[data-route]").forEach(e=>{e.addEventListener("click",()=>{const t=e.dataset.route;M.navigate(t),this.close()})}),document.getElementById("mnrLogoutBtn")?.addEventListener("click",async()=>{confirm("Are you sure you want to logout?")&&(await y.logout(),window.dispatchEvent(new CustomEvent("logout")),this.close())}))}toggleSection(e){this.expandedSections.has(e)?this.expandedSections.delete(e):this.expandedSections.add(e),this.updateUI()}updateUI(){this.container&&(this.container.innerHTML=this.render(),this.attachEventListeners())}open(){this.isOpen||(this.isOpen=!0,this.container?.classList.add("open"),this.overlay?.classList.add("visible"),document.body.style.overflow="hidden")}close(){this.isOpen&&(this.isOpen=!1,this.container?.classList.remove("open"),this.overlay?.classList.remove("visible"),document.body.style.overflow="")}toggle(){this.isOpen?this.close():this.open()}destroy(){this.container?.remove(),this.overlay?.remove()}}const ke=new le;class Ee{config;constructor(e){this.config=e}render(){if(this.config.loading)return`
        <div class="table-loading">
          <div class="spinner"></div>
          <p>Loading...</p>
        </div>
      `;if(!this.config.data||this.config.data.length===0)return`
        <div class="table-empty">
          <p>${this.config.emptyMessage||"No data found"}</p>
        </div>
      `;const e=i=>this.config.sortColumn===i?this.config.sortDirection==="asc"?" ↑":" ↓":"",t=this.config.columns.map(i=>{const n=i.sortable!==!1,s=e(i.key),l=i.width?`width: ${i.width};`:"",o=n?`data-sort-column="${i.key}"`:"";return`<th style="${l}${n?"cursor: pointer;":""}" ${o}>${i.label}${s}</th>`}).join(""),a=this.config.data.map(i=>`<tr>${this.config.columns.map(s=>{const l=i[s.key];return`<td>${s.render?s.render(l,i):l??"-"}</td>`}).join("")}</tr>`).join("");return`
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
    `}static attachSortListeners(e,t){e.querySelectorAll("[data-sort-column]").forEach(a=>{a.addEventListener("click",()=>{const i=a.getAttribute("data-sort-column");i&&t(i)})})}}const de=[{menu_code:"SERVICE_REQUEST",label:"Service Request",route:"partner-service",icon:"headset",highlight:!0},{menu_code:"HOME_DASHBOARD",label:"Home Dashboard",route:"partner-dashboard",icon:"home"},{menu_code:"VIEW_PROFILE",label:"View Profile",route:"partner-profile",icon:"user"}],ce=[{section_code:"ORDERS",section_label:"Orders",icon:"package",order:1,items:[{menu_code:"ALL_ORDERS",label:"All Orders",route:"partner-orders"},{menu_code:"NEW_ORDER",label:"Create New Order",route:"partner-new-order"}]},{section_code:"SERVICE",section_label:"Service Center",icon:"tool",order:2,items:[{menu_code:"RAISE_TICKET",label:"Raise New Ticket",route:"partner-raise-ticket"},{menu_code:"MY_TICKETS",label:"My Tickets",route:"partner-service"},{menu_code:"TICKET_HISTORY",label:"Ticket History",route:"partner-ticket-history"}]},{section_code:"FINANCE",section_label:"Finance",icon:"coins",order:3,items:[{menu_code:"INVOICES",label:"Invoices",route:"partner-invoices"},{menu_code:"PAYMENTS",label:"Payments",route:"partner-payments"},{menu_code:"REVENUE",label:"Revenue Dashboard",route:"partner-revenue"}]},{section_code:"LEADS",section_label:"Leads & CRM",icon:"users",order:4,items:[{menu_code:"MY_LEADS",label:"My Leads",route:"partner-leads"}]}];class pe{container=null;overlay=null;isOpen=!1;expandedSections=new Set;user=null;constructor(){this.createElements()}createElements(){this.overlay=document.createElement("div"),this.overlay.className="partner-drawer-overlay",this.overlay.addEventListener("click",()=>this.close()),document.body.appendChild(this.overlay),this.container=document.createElement("div"),this.container.className="partner-side-drawer",this.container.innerHTML=this.render(),document.body.appendChild(this.container),this.injectStyles(),this.attachEventListeners()}injectStyles(){if(document.getElementById("partner-drawer-styles"))return;const e=document.createElement("style");e.id="partner-drawer-styles",e.textContent=`
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
          <div class="partner-user-avatar">${e.split(" ").map(n=>n[0]).join("").toUpperCase().slice(0,2)}</div>
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
          ${de.map(n=>`
            <div class="partner-menu-item ${n.highlight?"highlight":""}" data-route="${n.route}">
              ${this.getIcon(n.icon||"home")}
              <span>${n.label}</span>
            </div>
          `).join("")}
        </div>

        ${ce.map(n=>this.renderSection(n)).join("")}

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
    `}attachEventListeners(){this.container&&(document.getElementById("partnerDrawerClose")?.addEventListener("click",()=>this.close()),this.container.querySelectorAll("[data-toggle]").forEach(e=>{e.addEventListener("click",t=>{const a=e.dataset.toggle;this.toggleSection(a),t.stopPropagation()})}),this.container.querySelectorAll("[data-route]").forEach(e=>{e.addEventListener("click",()=>{const t=e.dataset.route;M.navigate(t),this.close()})}),document.getElementById("partnerLogoutBtn")?.addEventListener("click",async()=>{confirm("Are you sure you want to logout?")&&(await y.logout(),window.dispatchEvent(new CustomEvent("logout")),this.close())}))}toggleSection(e){this.expandedSections.has(e)?this.expandedSections.delete(e):this.expandedSections.add(e),this.updateUI()}updateUI(){this.container&&(this.container.innerHTML=this.render(),this.attachEventListeners())}open(){this.isOpen||(this.isOpen=!0,this.container?.classList.add("open"),this.overlay?.classList.add("visible"),document.body.style.overflow="hidden")}close(){this.isOpen&&(this.isOpen=!1,this.container?.classList.remove("open"),this.overlay?.classList.remove("visible"),document.body.style.overflow="")}toggle(){this.isOpen?this.close():this.open()}destroy(){this.container?.remove(),this.overlay?.remove()}}const Se=new pe;class Ce{container;constructor(e){this.container=e}render(){const t=y.getAuthState().user?.portal||"staff",a=M.getTabRoutes(t),i=M.getCurrentRoute();this.container.innerHTML=`
      <nav class="bottom-tabs">
        ${a.map(n=>`
          <button 
            class="tab-item ${i===n.id?"active":""}" 
            data-route="${n.id}"
          >
            ${this.getIcon(n.icon)}
            <span class="tab-label">${n.title}</span>
          </button>
        `).join("")}
      </nav>
    `,this.attachListeners()}attachListeners(){this.container.querySelectorAll(".tab-item").forEach(e=>{e.addEventListener("click",()=>{const t=e.getAttribute("data-route");t&&M.navigate(t)})})}getIcon(e){const t={home:`<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
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
      </svg>`};return t[e]||t.home}}class ue{isShowing=!1;unsubscribe=null;checkInterval=null;init(){this.unsubscribe&&this.unsubscribe(),this.checkInterval&&clearInterval(this.checkInterval),this.unsubscribe=C.onSessionExpired(e=>{console.log("[SessionBanner] Session expired detected, endpoint:",e),y.getAuthState().isLoggedIn||this.show()}),this.checkInterval=setInterval(()=>{if(y.getAuthState().isLoggedIn){this.isShowing&&this.hide();return}const t=Y.getTrackingStatus();t.isSessionExpired&&!this.isShowing?this.show():!t.isSessionExpired&&this.isShowing&&this.hide()},5e3)}cleanup(){this.unsubscribe&&(this.unsubscribe(),this.unsubscribe=null),this.checkInterval&&(clearInterval(this.checkInterval),this.checkInterval=null),this.hide()}show(){if(!y.getAuthState().isLoggedIn||this.isShowing||document.getElementById("globalSessionBanner"))return;this.isShowing=!0;const e=document.createElement("div");e.id="globalSessionBanner",e.className="global-session-banner",e.innerHTML=`
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
    `,document.body.appendChild(e),document.getElementById("globalReAuthBtn")?.addEventListener("click",t=>{t.stopPropagation(),this.showReAuthModal()}),e.addEventListener("click",()=>this.showReAuthModal())}hide(){const e=document.getElementById("globalSessionBanner");e&&e.remove(),this.isShowing=!1}showReAuthModal(){if(document.getElementById("globalReAuthModal"))return;const t=y.getAuthState().user,a=document.createElement("div");a.id="globalReAuthModal",a.className="modal",a.style.display="flex",a.style.zIndex="10001",a.innerHTML=`
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
    `,document.body.appendChild(a),setTimeout(()=>{document.getElementById("globalReAuthPassword")?.focus()},100),document.getElementById("closeGlobalReAuthModal")?.addEventListener("click",()=>a.remove()),document.getElementById("cancelGlobalReAuth")?.addEventListener("click",()=>a.remove()),document.getElementById("submitGlobalReAuth")?.addEventListener("click",()=>this.submitReAuth()),document.getElementById("globalReAuthPassword")?.addEventListener("keypress",i=>{i.key==="Enter"&&this.submitReAuth()})}async submitReAuth(){const e=document.getElementById("globalReAuthUserId"),t=document.getElementById("globalReAuthPassword"),a=document.getElementById("globalReAuthError"),i=document.getElementById("submitGlobalReAuth");if(!t)return;const n=e?.value||"",s=t.value;if(!s){a&&(a.textContent="Please enter your password",a.style.display="block");return}i&&(i.disabled=!0,i.textContent="Logging in...");try{const o=y.getAuthState().user?.portal||"staff",d=await y.loginWithPassword(n,s,o);if(d.success){document.getElementById("globalReAuthModal")?.remove(),this.hide();const{offlineQueueService:r}=await W(async()=>{const{offlineQueueService:h}=await import("./services-CQ7x3UT6.js").then(b=>b.p);return{offlineQueueService:h}},__vite__mapDeps([0,1,2,3]),import.meta.url);r.getStatus().pendingCount>0&&console.log("[SessionBanner] Re-auth successful, queued data will sync automatically"),console.log("[SessionBanner] Refreshing current page after successful re-auth");const{routerService:p}=await W(async()=>{const{routerService:h}=await import("./services-CQ7x3UT6.js").then(b=>b.u);return{routerService:h}},__vite__mapDeps([0,1,2,3]),import.meta.url),g=p.getCurrentRoute();p.navigate(g,!1)}else a&&(a.textContent=d.error||"Login failed. Please try again.",a.style.display="block")}catch(l){a&&(a.textContent=l.message||"An error occurred",a.style.display="block")}finally{i&&(i.disabled=!1,i.textContent="Login")}}}const _e=new ue;class me{container;fab=null;modal=null;messages=[];conversationHistory=[];isOpen=!1;isLoading=!1;constructor(){this.container=document.createElement("div"),this.container.id="vgk-mobile-root",document.body.appendChild(this.container),this.render()}getEndpoint(){return`${q.BASE_SERVER_URL}/api/v1/ai/command/process`}render(){if(!this.getEndpoint())return;this.container.innerHTML=`
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
    `,this.fab=this.container.querySelector("#vgk-mobile-fab"),this.modal=this.container.querySelector("#vgk-mobile-modal"),this.attachFabDrag(),this.container.querySelector("#vgk-close-btn")?.addEventListener("click",()=>this.close());const t=this.container.querySelector("#vgk-text-input");this.container.querySelector("#vgk-send-btn")?.addEventListener("click",()=>{t.value.trim()&&(this.send(t.value.trim()),t.value="")}),t?.addEventListener("keypress",a=>{a.key==="Enter"&&t.value.trim()&&(this.send(t.value.trim()),t.value="")}),this.container.querySelector("#vgk-mic-btn")?.addEventListener("click",()=>this.startVoice(t)),this.pushMessage("assistant","Hi! I'm VGK Assistant. How can I help you today?")}attachFabDrag(){if(!this.fab)return;let e=!1,t=0,a=0,i=0,n=0,s=!1;const l=r=>{const m=r.touches[0];t=m.clientX,a=m.clientY;const p=this.fab.getBoundingClientRect();i=p.left,n=p.top,e=!0,s=!1},o=r=>{if(!e)return;const m=r.touches[0],p=m.clientX-t,g=m.clientY-a;if(Math.abs(p)>5||Math.abs(g)>5){s=!0;const h=Math.max(10,Math.min(window.innerWidth-60,i+p)),b=Math.max(60,Math.min(window.innerHeight-100,n+g));this.fab.style.left=`${h}px`,this.fab.style.top=`${b}px`,this.fab.style.right="auto",this.fab.style.bottom="auto"}},d=()=>{e=!1,s||this.open()};this.fab.addEventListener("touchstart",l,{passive:!0}),this.fab.addEventListener("touchmove",o,{passive:!0}),this.fab.addEventListener("touchend",d),this.fab.addEventListener("click",r=>{s?(r.preventDefault(),r.stopPropagation()):this.open()})}open(){this.modal?.classList.add("open"),this.isOpen=!0,this.scrollToBottom()}close(){this.modal?.classList.remove("open"),this.isOpen=!1}pushMessage(e,t){this.messages.push({role:e,text:t}),this.renderMessages()}renderMessages(){const e=this.container.querySelector("#vgk-messages");e&&(e.innerHTML=this.messages.map(t=>`<div class="vgk-bubble ${t.role}">${t.text.replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/\n/g,"<br>")}</div>`).join(""),this.isLoading&&(e.innerHTML+='<div class="vgk-typing"><div class="vgk-dot"></div><div class="vgk-dot"></div><div class="vgk-dot"></div></div>'),this.scrollToBottom())}scrollToBottom(){const e=this.container.querySelector("#vgk-messages");e&&(e.scrollTop=e.scrollHeight)}async send(e){if(this.isLoading)return;this.pushMessage("user",e),this.isLoading=!0,this.renderMessages();const t=this.getEndpoint();if(!t){this.pushMessage("assistant","Not available for this portal."),this.isLoading=!1;return}try{const a=await C.getToken(),n=await(await fetch(t,{method:"POST",headers:{"Content-Type":"application/json",...a?{Authorization:`Bearer ${a}`}:{}},body:JSON.stringify({user_message:e,conversation_history:this.conversationHistory.slice(-20),language:"en",company_id:null,allowed_intents:null})})).json();if(n.reply_text){if(this.conversationHistory.push({role:"user",text:e}),this.conversationHistory.push({role:"assistant",text:n.reply_text}),this.conversationHistory.length>20&&(this.conversationHistory=this.conversationHistory.slice(-20)),this.pushMessage("assistant",n.reply_text),n.speak_text&&"speechSynthesis"in window){const s=new SpeechSynthesisUtterance(n.speak_text);s.lang="en-IN",s.rate=1,window.speechSynthesis.speak(s)}}else this.pushMessage("assistant",n.detail||"Something went wrong.")}catch{this.pushMessage("assistant","Could not reach VGK server. Please try again.")}this.isLoading=!1,this.renderMessages()}startVoice(e){const t=window.SpeechRecognition||window.webkitSpeechRecognition;if(!t){alert("Voice input not supported on this device.");return}const a=this.container.querySelector("#vgk-mic-btn"),i=new t;i.lang="en-IN",i.continuous=!1,i.interimResults=!1,i.onstart=()=>a.classList.add("recording"),i.onresult=n=>{const s=n.results[0][0].transcript;e.value=s},i.onend=()=>a.classList.remove("recording"),i.onerror=()=>a.classList.remove("recording"),i.start()}}function Me(){const c=$.getPortal();(c==="staff"||c==="partner")&&new me}export{Ce as B,ve as L,Ee as M,F as P,ye as a,xe as b,ae as g,Me as i,ke as m,Se as p,_e as s,we as u};
