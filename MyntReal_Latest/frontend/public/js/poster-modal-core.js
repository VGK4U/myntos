/**
 * poster-modal-core.js - Universal Standalone Achievement Poster Engine for Mynt OS
 * Guarantees poster modal availability and functionality across all pages.
 */

(function() {
  // 1. Ensure html2canvas is loaded
  if (typeof window.html2canvas === 'undefined') {
    const script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js';
    document.head.appendChild(script);
  }

  // 2. Ensure poster modal HTML exists in DOM
  function ensurePosterModalDOM() {
    if (document.getElementById('posterModal')) return;

    const modalHTML = `
<div id="posterModal" onclick="if(event.target===this)closePosterModal()" style="display:none;position:fixed;inset:0;z-index:99999;background:rgba(0,0,0,.75);align-items:center;justify-content:center;padding:16px;overflow-y:auto;box-sizing:border-box">
  <div style="background:#fff;border-radius:16px;width:100%;max-width:1100px;max-height:92vh;display:flex;flex-direction:column;overflow:hidden;box-shadow:0 25px 50px -12px rgba(0,0,0,.5);position:relative">
    <div style="background:linear-gradient(135deg,#064e3b,#059669);padding:14px 20px;display:flex;justify-content:space-between;align-items:center;color:white;flex-shrink:0">
      <div style="display:flex;align-items:center;gap:10px">
        <i class="fas fa-award fa-lg" style="color:#fbbf24"></i>
        <h5 style="margin:0;font-size:16px;font-weight:700">Achievement &amp; Earnings Celebration Poster</h5>
      </div>
      <button onclick="closePosterModal()" style="background:rgba(255,255,255,.2);border:none;border-radius:8px;color:white;width:32px;height:32px;cursor:pointer;font-size:16px;display:flex;align-items:center;justify-content:center"><i class="fas fa-times"></i></button>
    </div>
    
    <div style="display:flex;flex:1;overflow:hidden">
      <!-- Left Pane: Controls -->
      <div style="width:340px;background:#f9fafb;border-right:1px solid #e5e7eb;padding:16px;overflow-y:auto;flex-shrink:0;box-sizing:border-box">
        <h6 style="font-size:11px;font-weight:700;color:#6b7280;text-transform:uppercase;letter-spacing:.05em;margin-bottom:12px">Customize Poster Details</h6>
        
        <div style="display:flex;flex-direction:column;gap:10px">
          <div>
            <label style="font-size:10px;font-weight:600;color:#6b7280;display:block;margin-bottom:2px">THEME PRESET</label>
            <select id="postThemePreset" onchange="changeThemePreset()" style="width:100%;padding:7px 9px;font-size:11.5px;border:1.5px solid #d1d5db;border-radius:6px;background:#fff;font-weight:700;color:#065f46">
              <option value="celebration_graphic" selected>🎉 High-Impact Celebration Graphic</option>
              <option value="dark_navy">🌌 Midnight Navy &amp; Gold</option>
              <option value="emerald_success">✳️ Royal Emerald &amp; Gold</option>
              <option value="royal_blue">👑 Sapphire Royal Blue</option>
              <option value="light_cream">🍦 Clean Light Cream</option>
            </select>
          </div>
          
          <div style="border-top:1px solid #e5e7eb;margin-top:8px;padding-top:10px">
            <h6 style="font-size:12px;font-weight:700;color:#111827;margin-bottom:8px">MEMBER &amp; PHOTOS</h6>
            <div style="display:flex;flex-direction:column;gap:8px">
              <div>
                <label style="font-size:10px;font-weight:600;color:#6b7280;display:block;margin-bottom:2px">MEMBER PHOTO</label>
                <input type="file" id="postMemberPhotoFile" accept="image/*" onchange="handleMemberPhotoUpload(event)" style="font-size:11px;width:100%">
              </div>
              <div>
                <label style="font-size:10px;font-weight:600;color:#6b7280;display:block;margin-bottom:2px">DIRECT SPONSOR PHOTO</label>
                <input type="file" id="postSeniorPhotoFile" accept="image/*" onchange="handleSeniorPhotoUpload(event)" style="font-size:11px;width:100%">
              </div>
              <div>
                <label style="font-size:10px;font-weight:600;color:#6b7280;display:block;margin-bottom:2px">HEADER TITLE</label>
                <input type="text" id="postTitle" oninput="updatePoster()" style="width:100%;padding:7px 9px;font-size:11.5px;border:1.5px solid #d1d5db;border-radius:6px" placeholder="CONGRATULATIONS">
              </div>
              <div>
                <label style="font-size:10px;font-weight:600;color:#6b7280;display:block;margin-bottom:2px">MEMBER NAME</label>
                <input type="text" id="postSubtitle" oninput="updatePoster()" style="width:100%;padding:7px 9px;font-size:11.5px;border:1.5px solid #d1d5db;border-radius:6px" placeholder="Member Name">
              </div>
              <div>
                <label style="font-size:10px;font-weight:600;color:#6b7280;display:block;margin-bottom:2px">CAREER DESIGNATION</label>
                <input type="text" id="postRank" oninput="updatePoster()" style="width:100%;padding:7px 9px;font-size:11.5px;border:1.5px solid #d1d5db;border-radius:6px" placeholder="e.g. CHANNEL PARTNER">
              </div>
              <div>
                <label style="font-size:10px;font-weight:600;color:#6b7280;display:block;margin-bottom:2px">OVERALL EARNING (₹)</label>
                <input type="text" id="postHighlight" oninput="updatePoster()" style="width:100%;padding:7px 9px;font-size:11.5px;border:1.5px solid #d1d5db;border-radius:6px" placeholder="₹0/-">
              </div>
              <div>
                <label style="font-size:10px;font-weight:600;color:#6b7280;display:block;margin-bottom:2px">FILES STATUS</label>
                <input type="text" id="postFiles" oninput="updatePoster()" style="width:100%;padding:7px 9px;font-size:11.5px;border:1.5px solid #d1d5db;border-radius:6px" placeholder="e.g. 6/16 FILES">
              </div>
            </div>
          </div>
          
          <div style="border-top:1px solid #e5e7eb;margin-top:8px;padding-top:10px">
            <h6 style="font-size:12px;font-weight:700;color:#111827;margin-bottom:8px">TODAY'S PAYOUT &amp; COMPONENTS</h6>
            <div style="display:flex;flex-direction:column;gap:8px">
              <div style="background:#ecfdf5;border:1px solid #a7f3d0;border-radius:8px;padding:8px">
                <label style="font-size:10.5px;font-weight:700;color:#065f46;display:block;margin-bottom:4px">INCLUDE IN TODAY'S PAYOUT:</label>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px">
                  <label style="font-size:10.5px;color:#374151;display:flex;align-items:center;gap:6px;cursor:pointer;user-select:none">
                    <input type="checkbox" id="payTypeStage1" checked onchange="recalculateTodayPayout(true)" style="accent-color:#059669"> Stage 1 Adv
                  </label>
                  <label style="font-size:10.5px;color:#374151;display:flex;align-items:center;gap:6px;cursor:pointer;user-select:none">
                    <input type="checkbox" id="payTypeStage2Adv" checked onchange="recalculateTodayPayout(true)" style="accent-color:#059669"> Stage 2 Adv
                  </label>
                  <label style="font-size:10.5px;color:#374151;display:flex;align-items:center;gap:6px;cursor:pointer;user-select:none">
                    <input type="checkbox" id="payTypeFinalComm" checked onchange="recalculateTodayPayout(true)" style="accent-color:#059669"> Final Comm
                  </label>
                  <label style="font-size:10.5px;color:#374151;display:flex;align-items:center;gap:6px;cursor:pointer;user-select:none">
                    <input type="checkbox" id="payTypeSupport" checked onchange="recalculateTodayPayout(true)" style="accent-color:#059669"> Field Support
                  </label>
                  <label style="font-size:10.5px;color:#374151;display:flex;align-items:center;gap:6px;cursor:pointer;user-select:none">
                    <input type="checkbox" id="payTypeBrand" checked onchange="recalculateTodayPayout(true)" style="accent-color:#059669"> Brand Inc
                  </label>
                  <label style="font-size:10.5px;color:#374151;display:flex;align-items:center;gap:6px;cursor:pointer;user-select:none">
                    <input type="checkbox" id="payTypeBonanza" checked onchange="recalculateTodayPayout(true)" style="accent-color:#059669"> Bonanza
                  </label>
                  <label style="font-size:10.5px;color:#374151;display:flex;align-items:center;gap:6px;cursor:pointer;user-select:none">
                    <input type="checkbox" id="payTypeExtra" checked onchange="recalculateTodayPayout(true)" style="accent-color:#059669"> Extra Comm
                  </label>
                  <label style="font-size:10.5px;color:#374151;display:flex;align-items:center;gap:6px;cursor:pointer;user-select:none">
                    <input type="checkbox" id="payTypeAward" checked onchange="recalculateTodayPayout(true)" style="accent-color:#059669"> Award
                  </label>
                </div>
              </div>
              <div>
                <label style="font-size:10px;font-weight:700;color:#374151;display:block;margin-bottom:2px">EARNING PERIOD (DATE RANGE)</label>
                <div style="display:flex;align-items:center;gap:4px">
                  <input type="date" id="postPayoutDateFrom" onchange="changePayoutDateRange()" style="width:50%;padding:5px 7px;font-size:11px;border:1.5px solid #d1d5db;border-radius:6px;outline:none" title="Start Date">
                  <span style="font-size:11px;color:#9ca3af;font-weight:700">—</span>
                  <input type="date" id="postPayoutDateTo" onchange="changePayoutDateRange()" style="width:50%;padding:5px 7px;font-size:11px;border:1.5px solid #d1d5db;border-radius:6px;outline:none" title="End Date">
                </div>
                <div style="display:flex;gap:4px;margin-top:4px">
                  <button type="button" onclick="setPosterPresetPeriod('today')" style="flex:1;padding:3px;font-size:9.5px;font-weight:700;background:#ede9fe;color:#7c3aed;border:1px solid #c4b5fd;border-radius:4px;cursor:pointer">Today</button>
                  <button type="button" onclick="setPosterPresetPeriod('week')" style="flex:1;padding:3px;font-size:9.5px;font-weight:700;background:#ede9fe;color:#7c3aed;border:1px solid #c4b5fd;border-radius:4px;cursor:pointer">This Week</button>
                  <button type="button" onclick="setPosterPresetPeriod('month')" style="flex:1;padding:3px;font-size:9.5px;font-weight:700;background:#ede9fe;color:#7c3aed;border:1px solid #c4b5fd;border-radius:4px;cursor:pointer">This Month</button>
                  <button type="button" onclick="setPosterPresetPeriod('all')" style="flex:1;padding:3px;font-size:9.5px;font-weight:700;background:#f3f4f6;color:#374151;border:1px solid #d1d5db;border-radius:4px;cursor:pointer">All Time</button>
                </div>
              </div>
              <div>
                <label style="font-size:10px;font-weight:600;color:#6b7280;display:block;margin-bottom:2px">TOTAL TODAY PAYOUT (₹)</label>
                <input type="text" id="postTotalToday" oninput="updatePoster()" style="width:100%;padding:7px 9px;font-size:11.5px;border:1.5px solid #d1d5db;border-radius:6px" placeholder="₹0/-">
              </div>
            </div>
          </div>
          
          <div style="border-top:1px solid #e5e7eb;margin-top:8px;padding-top:10px">
            <h6 style="font-size:12px;font-weight:700;color:#111827;margin-bottom:8px">TEAM &amp; POTENTIAL</h6>
            <div style="display:flex;flex-direction:column;gap:8px">
              <div>
                <label style="font-size:10px;font-weight:600;color:#6b7280;display:block;margin-bottom:2px">TOTAL TEAM SIZE</label>
                <input type="text" id="postOverall" oninput="updatePoster()" style="width:100%;padding:7px 9px;font-size:11.5px;border:1.5px solid #d1d5db;border-radius:6px" placeholder="e.g. 8 MEMBERS">
              </div>
              <div>
                <label style="font-size:10px;font-weight:600;color:#6b7280;display:block;margin-bottom:2px">TEAM BREAKUP</label>
                <input type="text" id="postTeamBreakup" oninput="updatePoster()" style="width:100%;padding:7px 9px;font-size:11.5px;border:1.5px solid #d1d5db;border-radius:6px" placeholder="e.g. L2: 6 | L3: 2 | L4: 0">
              </div>
              <div>
                <label style="font-size:10px;font-weight:600;color:#6b7280;display:block;margin-bottom:2px">POTENTIAL EARNING (₹)</label>
                <input type="text" id="postPotential" oninput="updatePoster()" style="width:100%;padding:7px 9px;font-size:11.5px;border:1.5px solid #d1d5db;border-radius:6px" placeholder="₹0/-">
              </div>
            </div>
          </div>
          
          <div style="border-top:1px solid #e5e7eb;margin-top:8px;padding-top:10px">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
              <h6 style="font-size:12px;font-weight:700;color:#111827;margin:0">DIRECT SPONSOR DETAILS</h6>
              <label style="font-size:11px;font-weight:700;color:#059669;display:flex;align-items:center;gap:5px;cursor:pointer;user-select:none">
                <input type="checkbox" id="postShowSenior" checked onchange="updatePoster()" style="accent-color:#059669"> Show Direct Sponsor
              </label>
            </div>
            <div style="display:flex;flex-direction:column;gap:8px">
              <div>
                <label style="font-size:10px;font-weight:600;color:#6b7280;display:block;margin-bottom:2px">DIRECT SPONSOR NAME</label>
                <input type="text" id="postSeniorName" oninput="updatePoster()" style="width:100%;padding:7px 9px;font-size:11.5px;border:1.5px solid #d1d5db;border-radius:6px" placeholder="Direct Sponsor Name">
              </div>
              <div>
                <label style="font-size:10px;font-weight:600;color:#6b7280;display:block;margin-bottom:2px">DIRECT SPONSOR TODAY'S EARNING (₹)</label>
                <input type="text" id="postSeniorToday" oninput="updatePoster()" style="width:100%;padding:7px 9px;font-size:11.5px;border:1.5px solid #d1d5db;border-radius:6px" placeholder="e.g. ₹1,835/-">
              </div>
              <div>
                <label style="font-size:10px;font-weight:600;color:#6b7280;display:block;margin-bottom:2px">DIRECT SPONSOR OVERALL (₹)</label>
                <input type="text" id="postSeniorEarning" oninput="updatePoster()" style="width:100%;padding:7px 9px;font-size:11.5px;border:1.5px solid #d1d5db;border-radius:6px" placeholder="e.g. ₹49,875/-">
              </div>
              <div>
                <label style="font-size:10px;font-weight:600;color:#6b7280;display:block;margin-bottom:2px">DIRECT SPONSOR POTENTIAL (₹)</label>
                <input type="text" id="postSeniorPotential" oninput="updatePoster()" style="width:100%;padding:7px 9px;font-size:11.5px;border:1.5px solid #d1d5db;border-radius:6px" placeholder="e.g. ₹91,650/-">
              </div>
            </div>
          </div>

          <div style="border-top:1.5px solid #e5e7eb;margin-top:8px;padding-top:12px;background:#f0fdf4;margin:4px -20px -20px -20px;padding:16px 20px;border-bottom:1px solid #d1d5db">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
              <label style="font-size:11.5px;font-weight:800;color:#065f46;text-transform:uppercase;letter-spacing:0.3px;margin:0">
                <i class="fab fa-whatsapp me-1 text-success"></i>WhatsApp Message Template
              </label>
              <div style="display:flex;align-items:center;gap:8px">
                <button type="button" id="btnCopyPosterTextInline" onclick="copyPosterText(this)" style="background:#059669;color:#ffffff;border:none;border-radius:5px;font-size:10.5px;font-weight:700;cursor:pointer;padding:3px 9px;display:inline-flex;align-items:center;gap:4px">
                  <i class="fas fa-copy"></i> Copy Text
                </button>
                <button type="button" onclick="resetPosterCustomText()" style="background:none;border:none;color:#059669;font-size:11px;font-weight:700;cursor:pointer;padding:0">
                  <i class="fas fa-redo-alt me-1"></i>Reset Text
                </button>
              </div>
            </div>
            <div>
              <textarea id="postShareCustomText" rows="6" oninput="window._posterCustomTextEdited = true" style="width:100%;font-size:11.5px;font-family:'Segoe UI',system-ui,sans-serif;line-height:1.45;border:1.5px solid #a7f3d0;border-radius:7px;padding:8px 10px;box-sizing:border-box;resize:vertical;background:#ffffff;color:#111827;white-space:pre-wrap" placeholder="WhatsApp message will preview and update here…"></textarea>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Right Pane: Live Poster Preview -->
      <div style="flex:1;background:#131B2E;display:flex;align-items:center;justify-content:center;padding:24px;overflow:auto;position:relative">
        <div id="posterSpinner" style="display:none;position:absolute;inset:0;background:rgba(0,0,0,0.6);z-index:10;align-items:center;justify-content:center;color:white;font-size:14px">
          <div style="text-align:center"><i class="fas fa-circle-notch fa-spin fa-2x mb-2"></i><div>Analyzing and populating values…</div></div>
        </div>
        
        <div id="posterCanvasWrapper" style="width:480px;height:fit-content;background:radial-gradient(circle at 50% 20%, #1e1b4b 0%, #0f172a 50%, #020617 100%);border:5px double #fbbf24;border-radius:20px;box-shadow:0 25px 70px rgba(0,0,0,0.95), 0 0 50px rgba(251,191,36,0.4);position:relative;box-sizing:border-box;color:#ffffff;font-family:'Segoe UI',Roboto,Helvetica,sans-serif;user-select:none;flex-shrink:0;padding:14px 16px 20px 16px;display:flex;flex-direction:column;align-items:center;overflow:hidden">
          <div id="prevBonusDesc" style="display:none"></div>
          <div id="prevTitle" style="display:none">CONGRATULATIONS</div>
          <div id="prevTodayTitle" style="display:none">TODAY'S PAYOUT</div>
          <div id="prevImageInstructions" style="display:none"></div>

          <div style="position:absolute;inset:0;background-image:
            radial-gradient(3px 3px at 25px 35px, #fbbf24, transparent), 
            radial-gradient(3px 3px at 60px 85px, #ffffff, transparent), 
            radial-gradient(2px 2px at 110px 45px, #f472b6, transparent), 
            radial-gradient(3px 3px at 180px 140px, #38bdf8, transparent), 
            radial-gradient(2.5px 2.5px at 250px 90px, #fbbf24, transparent), 
            radial-gradient(3px 3px at 340px 60px, #ffffff, transparent), 
            radial-gradient(3px 3px at 410px 120px, #fbbf24, transparent), 
            radial-gradient(2px 2px at 450px 40px, #38bdf8, transparent), 
            radial-gradient(3px 3px at 55px 280px, #fbbf24, transparent), 
            radial-gradient(3px 3px at 430px 310px, #ffffff, transparent), 
            radial-gradient(2.5px 2.5px at 35px 550px, #f472b6, transparent), 
            radial-gradient(3px 3px at 440px 580px, #fbbf24, transparent);
            opacity:0.85;pointer-events:none;z-index:1"></div>

          <svg style="position:absolute;inset:0;width:100%;height:100%;pointer-events:none;z-index:1;opacity:0.45" viewBox="0 0 480 700" preserveAspectRatio="none">
            <path d="M-10,40 Q60,10 120,60 T240,40" fill="none" stroke="#fbbf24" stroke-width="2.5" stroke-dasharray="8,5"/>
            <path d="M360,30 Q420,80 490,40" fill="none" stroke="#f472b6" stroke-width="2.5" stroke-dasharray="6,4"/>
            <path d="M-20,200 Q70,160 140,220" fill="none" stroke="#38bdf8" stroke-width="2"/>
            <path d="M340,240 Q410,190 490,260" fill="none" stroke="#fbbf24" stroke-width="2.5"/>
            <polygon points="40,20 48,32 32,30" fill="#fbbf24"/>
            <polygon points="430,30 442,18 420,15" fill="#f472b6"/>
            <rect x="70" y="110" width="8" height="14" rx="2" fill="#38bdf8" transform="rotate(25 70 110)"/>
            <rect x="400" y="130" width="10" height="16" rx="2" fill="#fbbf24" transform="rotate(-35 400 130)"/>
            <circle cx="130" cy="180" r="4" fill="#fbbf24"/>
            <circle cx="350" cy="190" r="5" fill="#f472b6"/>
            <rect x="30" y="320" width="9" height="15" fill="#34d399" transform="rotate(45 30 320)"/>
            <rect x="430" y="340" width="11" height="18" fill="#fbbf24" transform="rotate(-20 430 340)"/>
          </svg>

          <div style="position:relative;z-index:2;width:100%;display:flex;flex-direction:column;align-items:center">
            <div style="width:100%;height:58px;background:linear-gradient(135deg, rgba(255,255,255,0.98), rgba(248,250,252,0.95));border:1.8px solid rgba(234,179,8,0.85);border-radius:14px;padding:3px 12px;display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;box-shadow:0 4px 18px rgba(0,0,0,0.4)">
              <img src="/assets/logos/myntreal_logo_new.png" style="height:28px;max-width:110px;object-fit:contain" alt="MYNTREAL">
              <div style="background:linear-gradient(135deg,#fffbeb,#fef08a);border:1.8px solid #f59e0b;border-radius:10px;padding:2px 10px;box-shadow:0 3px 12px rgba(245,158,11,0.5);display:flex;align-items:center;justify-content:center">
                <img src="/assets/logos/hgs-logo.png" style="height:40px;max-width:140px;object-fit:contain" alt="HAR GHAR SOLAR">
              </div>
              <img src="/assets/logos/vgk4u-logo.png" style="height:28px;max-width:100px;object-fit:contain" alt="VGK4U">
            </div>

            <div id="prevCelebrationTitle" style="background:linear-gradient(135deg, #854d0e 0%, #ca8a04 50%, #854d0e 100%);border:1.5px solid #fde047;color:#fffbeb;font-family:Georgia,serif;font-size:11px;font-weight:900;letter-spacing:1px;padding:4px 14px;border-radius:30px;box-shadow:0 4px 15px rgba(202,138,4,0.5);margin-bottom:5px;text-transform:uppercase;white-space:nowrap;max-width:100%;box-sizing:border-box">🎉 👑 CONGRATULATIONS 👑 🎉</div>

            <div style="width:100%;text-align:center;margin-bottom:6px">
              <div id="prevSubtitle" style="width:100%;background:#fbbf24;color:#000000 !important;-webkit-text-fill-color:#000000 !important;font-family:'Segoe UI',Roboto,Helvetica,sans-serif;text-transform:uppercase;padding:6px 12px;border:2.5px solid #ffffff;border-radius:12px;box-shadow:0 6px 20px rgba(251,191,36,0.75);box-sizing:border-box;display:flex;flex-direction:column;align-items:center;justify-content:center">
                <!-- Line 1: Member Name -->
                <div id="prevName" style="font-size:22px;font-weight:950;letter-spacing:1px;line-height:1.15;color:#000000">LOADING…</div>
                <!-- Line 2: Career Designation below Name -->
                <div id="prevRankContainer" style="font-size:12.5px;font-weight:900;letter-spacing:1.2px;color:#78350f;line-height:1.1;margin-top:3px;display:inline-flex;align-items:center;gap:6px">
                  <span style="font-size:10px;font-weight:800;letter-spacing:1px;opacity:0.85">CAREER DESIGNATION:</span><span id="prevRank">CHANNEL PARTNER</span>
                </div>
              </div>
            </div>

            <div style="position:relative;width:220px;height:220px;margin-bottom:12px">
              <div style="position:absolute;bottom:4px;left:-106px;font-size:82px;line-height:1;filter:drop-shadow(0 6px 16px rgba(251,191,36,0.9));z-index:10;user-select:none">🏆</div>

              <div style="width:220px;height:220px;border-radius:50%;border:5px solid #fde047;overflow:hidden;background:#001233;box-shadow:0 0 50px rgba(234,179,8,0.95);display:flex;align-items:center;justify-content:center">
                <img id="prevImg" src="" style="width:100%;height:100%;object-fit:cover;object-position:center 20%;display:none">
                <div id="prevAvatar" style="width:100%;height:100%;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#1d4ed8,#7c3aed);color:white;font-size:70px;font-weight:900">CP</div>
              </div>

              <div style="position:absolute;bottom:4px;right:-106px;font-size:82px;line-height:1;filter:drop-shadow(0 6px 16px rgba(251,191,36,0.9));z-index:10;user-select:none">🏆</div>
              <div id="prevChampionBadge" style="position:absolute;bottom:-8px;left:50%;transform:translateX(-50%);background:linear-gradient(135deg,#b45309,#f59e0b,#b45309);border:1.5px solid #fef08a;color:#ffffff;font-size:10.5px;font-weight:900;padding:4px 18px;border-radius:14px;letter-spacing:1.2px;white-space:nowrap;box-shadow:0 4px 12px rgba(0,0,0,0.6);z-index:11">🏆 TOP PERFORMER</div>
            </div>

            <div style="width:100%;background:linear-gradient(135deg, #ffffff 0%, #fffbeb 50%, #fef3c7 100%);border:2.5px solid #eab308;border-radius:16px;padding:7px 14px;text-align:center;margin-bottom:6px;box-shadow:0 8px 25px rgba(0,0,0,0.5), 0 0 20px rgba(251,191,36,0.3)">
              <div style="color:#92400e;font-size:11.5px;font-weight:900;letter-spacing:2px;text-transform:uppercase;margin-bottom:2px">OVERALL EARNING</div>
              <div id="prevHighlight" style="color:#b91c1c;font-size:34px;font-weight:950;line-height:1;font-family:'Segoe UI',Roboto,sans-serif;letter-spacing:-0.5px">₹0/-</div>
              <div id="prevHighlightInWords" style="font-size:9.5px;font-weight:850;color:#92400e;margin-top:3px;text-transform:uppercase;letter-spacing:0.3px;width:100%;line-height:1.2;text-align:center;word-break:break-word;overflow:visible">—</div>
            </div>

            <div style="width:100%;background:linear-gradient(135deg, #064e3b 0%, #047857 50%, #065f46 100%);border:1.5px solid #34d399;border-radius:14px;padding:8px 10px;text-align:center;margin-bottom:8px;box-shadow:0 4px 16px rgba(4,120,87,0.45);box-sizing:border-box">
              <div style="font-size:21px;font-weight:950;color:#ffffff;text-transform:uppercase;letter-spacing:0.5px;white-space:nowrap;max-width:100%;overflow:hidden"><span id="prevTodayLabelText">Today's Earning</span>: <span id="prevTotalToday" style="color:#fde047">₹0/-</span></div>
              <div id="prevPeriodDateRange" style="font-size:11.5px;font-weight:900;color:#fef08a;margin-top:2px;letter-spacing:0.8px;text-transform:uppercase;white-space:nowrap;overflow:hidden"></div>
              <div id="prevAlreadyPaidText" style="font-size:12px;font-weight:800;color:#fde047;margin-top:3px;letter-spacing:0.3px;display:none"></div>
            </div>

            <div id="prevTodayPayout" style="display:none"></div>

            <div style="width:100%;display:grid;grid-template-columns:1fr 1fr 1.05fr;gap:6px;margin-bottom:8px;align-items:stretch">
              <!-- Files Card -->
              <div style="background:rgba(15,23,42,0.88);border:1.5px solid rgba(234,179,8,0.5);border-radius:12px;padding:6px 2px;text-align:center;display:flex;flex-direction:column;justify-content:center;align-items:center;gap:4px;min-height:60px;box-sizing:border-box">
                <div style="font-size:8px;font-weight:900;color:#93c5fd;text-transform:uppercase;letter-spacing:0.2px;line-height:1;white-space:nowrap">📂 FILES</div>
                <div id="prevFiles" style="display:flex;align-items:center;justify-content:center;font-size:11.5px;font-weight:950;color:#ffffff;line-height:1"><span style="display:inline-flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#f59e0b,#eab308);color:#0f172a;font-weight:950;font-size:9.5px;padding:2px 6px;border-radius:4px;line-height:1;white-space:nowrap">0 INSTALLED</span></div>
                <div id="prevTeamBreakupFiles" style="font-size:8px;font-weight:900;color:#93c5fd;letter-spacing:0.2px;line-height:1;white-space:nowrap">0 SUBMITTED</div>
              </div>
              
              <!-- Members / Team Size Card -->
              <div style="background:rgba(15,23,42,0.88);border:1.5px solid rgba(234,179,8,0.5);border-radius:12px;padding:6px 2px;text-align:center;display:flex;flex-direction:column;justify-content:center;align-items:center;gap:4px;min-height:60px;box-sizing:border-box">
                <div id="prevOverallLabel" style="font-size:8px;font-weight:900;color:#a7f3d0;text-transform:uppercase;letter-spacing:0.2px;line-height:1;white-space:nowrap">👥 TEAM SIZE</div>
                <div id="prevOverall" style="display:flex;align-items:center;justify-content:center;font-size:12.5px;font-weight:950;color:#ffffff;line-height:1;white-space:nowrap">0 MEMBERS</div>
                <div id="prevTeamBreakup" style="font-size:8px;font-weight:800;color:#6ee7b7;line-height:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%">L2: 0 | L3: 0 | L4: 0</div>
              </div>

              <!-- Potential Pending Card -->
              <div style="background:linear-gradient(135deg, rgba(112,26,117,0.88), rgba(131,24,67,0.88));border:1.5px solid #f472b6;border-radius:12px;padding:6px 2px;text-align:center;display:flex;flex-direction:column;justify-content:center;align-items:center;gap:4px;min-height:60px;box-sizing:border-box">
                <div style="font-size:8px;font-weight:900;color:#fbcfe8;text-transform:uppercase;letter-spacing:0.2px;line-height:1;white-space:nowrap">💰 POTENTIAL PENDING</div>
                <div id="prevPotential" style="display:flex;align-items:center;justify-content:center;font-size:12.5px;font-weight:950;color:#ffffff;line-height:1;white-space:nowrap">₹0/-</div>
                <div style="font-size:8px;font-weight:800;color:#fbcfe8;letter-spacing:0.2px;line-height:1;white-space:nowrap">EXPECTED EARNING</div>
              </div>
            </div>

            <div id="prevSeniorRow" style="position:relative;width:100%;background:rgba(8,18,38,0.95);border:1.5px solid rgba(234,179,8,0.65);border-radius:16px;padding:8px 12px 8px 132px;display:flex;flex-direction:column;justify-content:center;margin-top:8px;margin-bottom:4px;min-height:96px;box-shadow:0 8px 25px rgba(0,0,0,0.6);box-sizing:border-box">
              <div style="position:absolute;top:-10px;left:10px;width:110px;height:110px;border-radius:50%;background:#1e3a8a;border:4.5px solid #fde047;box-shadow:0 6px 25px rgba(251,191,36,0.9);display:flex;align-items:center;justify-content:center;z-index:10;overflow:hidden">
                <img id="prevSeniorImg" src="" style="width:100%;height:100%;object-fit:cover;display:none">
                <div id="prevSeniorAvatar" style="width:100%;height:100%;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#1d4ed8,#7c3aed);color:white;font-size:36px;font-weight:900">SR</div>
              </div>

              <div id="prevSeniorName" style="font-size:13.5px;font-weight:950;color:#fde047;line-height:1.2;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-bottom:4px;letter-spacing:0.5px">Direct Sponsor : —</div>

              <div style="display:flex;justify-content:space-between;align-items:center;width:100%;padding-right:4px">
                <div style="text-align:left">
                  <div id="prevSeniorTodayLabel" style="font-size:7.5px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:0.4px">Today</div>
                  <div id="prevSeniorToday" style="font-size:13px;font-weight:950;color:#ffffff">₹0/-</div>
                </div>
                <div style="text-align:center">
                  <div style="font-size:7.5px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:0.4px">Overall</div>
                  <div id="prevSeniorEarning" style="font-size:13px;font-weight:950;color:#34d399">₹0/-</div>
                </div>
                <div style="text-align:right">
                  <div style="font-size:7.5px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:0.4px">Potential</div>
                  <div id="prevSeniorPotential" style="font-size:13px;font-weight:950;color:#fb923c">₹0/-</div>
                </div>
              </div>
            </div>

            <div style="font-size:7.8px;font-weight:700;color:#94a3b8;text-align:center;letter-spacing:0.2px;margin-top:6px;padding-bottom:2px;white-space:nowrap;width:100%;overflow:hidden">
              * POTENTIAL EARNING IS BASED ON FINAL COMPLETION OF PROJECTS AND SUBJECT TO COMPANY TERMS.
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <div style="background:#f3f4f6;padding:10px 20px;border-top:1px solid #e5e7eb;display:flex;justify-content:flex-end;align-items:center;gap:8px;flex-shrink:0;min-height:62px;flex-wrap:wrap;box-sizing:border-box;z-index:20">
      <button onclick="closePosterModal()" style="background:#fff;color:#374151;border:1.5px solid #d1d5db;border-radius:8px;height:38px;padding:0 16px;font-size:12.5px;font-weight:600;cursor:pointer;display:inline-flex;align-items:center">Cancel</button>
      <button onclick="testShareToNumber()" style="background:linear-gradient(135deg,#0284c7,#0369a1);color:white;border:none;border-radius:8px;height:38px;padding:0 16px;font-size:12.5px;font-weight:700;cursor:pointer;display:inline-flex;align-items:center"><i class="fas fa-vial me-2"></i>Test Share (Custom No)</button>
      <button onclick="shareOnWhatsApp()" style="background:linear-gradient(135deg,#25d366,#128c7e);color:white;border:none;border-radius:8px;height:38px;padding:0 18px;font-size:12.5px;font-weight:700;cursor:pointer;display:inline-flex;align-items:center"><i class="fab fa-whatsapp me-2"></i>Share on WhatsApp</button>
      <button onclick="sharePoster()" style="background:linear-gradient(135deg,#3b82f6,#2563eb);color:white;border:none;border-radius:8px;height:38px;padding:0 18px;font-size:12.5px;font-weight:700;cursor:pointer;display:inline-flex;align-items:center"><i class="fas fa-share-alt me-2"></i>Share Poster</button>
      <button onclick="shareDefaultChannel()" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9);color:white;border:none;border-radius:8px;height:38px;padding:0 18px;font-size:12.5px;font-weight:700;cursor:pointer;display:inline-flex;align-items:center"><i class="fas fa-bullhorn me-2"></i>Share Default</button>
      <button onclick="postPosterAnnouncement()" style="background:linear-gradient(135deg,#ec4899,#be185d);color:white;border:none;border-radius:8px;height:38px;padding:0 18px;font-size:12.5px;font-weight:700;cursor:pointer;display:inline-flex;align-items:center"><i class="fas fa-bullhorn me-2"></i>Post Announcement</button>
      <button onclick="copyPosterText(this)" id="btnCopyPosterTextFooter" style="background:linear-gradient(135deg,#4f46e5,#4338ca);color:white;border:none;border-radius:8px;height:38px;padding:0 16px;font-size:12.5px;font-weight:700;cursor:pointer;display:inline-flex;align-items:center"><i class="fas fa-align-left me-2"></i>Copy Text</button>
      <button onclick="copyPosterImage(this)" id="btnCopyPosterImageFooter" style="background:linear-gradient(135deg,#0d9488,#0f766e);color:white;border:none;border-radius:8px;height:38px;padding:0 16px;font-size:12.5px;font-weight:700;cursor:pointer;display:inline-flex;align-items:center"><i class="fas fa-copy me-2"></i>Copy Image</button>
      <button onclick="downloadPoster()" style="background:linear-gradient(135deg,#059669,#047857);color:white;border:none;border-radius:8px;height:38px;padding:0 18px;font-size:12.5px;font-weight:700;cursor:pointer;display:inline-flex;align-items:center"><i class="fas fa-download me-2"></i>Download Image</button>
    </div>
  </div>
</div>
    `;

    const div = document.createElement('div');
    div.innerHTML = modalHTML;
    document.body.appendChild(div.firstElementChild);
  }

  // Helper fetch function
  async function safeFetch(url, options = {}) {
    if (typeof window.staffFetch === 'function') {
      return await window.staffFetch(url, options);
    }
    const tok = localStorage.getItem('staff_token') || localStorage.getItem('access_token') || sessionStorage.getItem('staff_token') || sessionStorage.getItem('access_token');
    const headers = options.headers || {};
    if (tok) headers['Authorization'] = 'Bearer ' + tok;
    return await fetch(url, { ...options, headers });
  }

  function resolvePosterMediaUrl(path) {
    if (!path || path === 'None' || path === 'null' || path === 'undefined') return '';
    let p = String(path).trim();
    if (p.startsWith('http://') || p.startsWith('https://') || p.startsWith('data:')) {
      return p;
    }
    p = p.replace(/^\/+/, '');
    if (p.startsWith('private/')) {
      p = p.replace(/^private\//, '');
    }
    if (p.startsWith('storage/')) {
      return window.location.origin + '/' + p;
    }
    return window.location.origin + '/storage/' + p;
  }

  function loadPhotoWithFallback(imgEl, avatarEl, candidatePaths, initialsText) {
    if (!imgEl) return;
    const validPaths = (candidatePaths || [])
      .map(p => (p && p !== 'None' && p !== 'null' && p !== 'undefined') ? String(p).trim() : '')
      .filter(Boolean);
    const uniqueCandidates = [...new Set(validPaths)];
    let currentIndex = 0;

    function tryNextCandidate() {
      if (currentIndex >= uniqueCandidates.length) {
        imgEl.style.display = 'none';
        if (avatarEl) {
          if (initialsText) avatarEl.textContent = initialsText;
          avatarEl.style.display = 'flex';
        }
        return;
      }
      const currentPath = uniqueCandidates[currentIndex];
      const resolvedUrl = resolvePosterMediaUrl(currentPath);
      if (!resolvedUrl) {
        currentIndex++;
        tryNextCandidate();
        return;
      }
      let triedWithoutCors = false;
      if (resolvedUrl.startsWith('http') && !resolvedUrl.includes(window.location.host)) {
        imgEl.crossOrigin = "anonymous";
      } else {
        try { imgEl.removeAttribute('crossorigin'); } catch(e){}
      }
      imgEl.onload = () => {
        imgEl.style.display = 'block';
        if (avatarEl) avatarEl.style.display = 'none';
      };
      imgEl.onerror = () => {
        if (!triedWithoutCors) {
          triedWithoutCors = true;
          try { imgEl.removeAttribute('crossOrigin'); } catch(e){}
          imgEl.src = resolvedUrl;
          return;
        }
        currentIndex++;
        tryNextCandidate();
      };
      const finalSrc = resolvedUrl.includes('?') ? resolvedUrl : (resolvedUrl + '?t=' + Date.now());
      imgEl.src = finalSrc;
    }

    tryNextCandidate();
  }


  function closePosterModal() {
    const el = document.getElementById('posterModal');
    if (el) el.style.display = 'none';
  }
  window.closePosterModal = closePosterModal;

  async function generateMemberPoster(partnerId) {
    ensurePosterModalDOM();
    const reqSeq = (window._posterGenReqSeq = (window._posterGenReqSeq || 0) + 1);
    window._postTotalTodayUserEdited = false;
    window._posterCustomTextEdited = false;
    if (typeof window.clearCustomCreativeImage === 'function') {
      window.clearCustomCreativeImage();
    } else if (typeof clearCustomCreativeImage === 'function') {
      clearCustomCreativeImage();
    }
    const modal = document.getElementById('posterModal');
    if (!modal) return;
    modal.style.display = 'flex';

    const spinner = document.getElementById('posterSpinner');
    if (spinner) spinner.style.display = 'flex';

    if (document.getElementById('postThemePreset')) {
      document.getElementById('postThemePreset').value = 'celebration_graphic';
      changeThemePreset();
    }

    const prevImg = document.getElementById('prevImg');
    const prevAvatar = document.getElementById('prevAvatar');
    if (prevImg) prevImg.style.display = 'none';
    if (prevAvatar) prevAvatar.style.display = 'none';

    try {
      const pidStr = String(partnerId || '').trim();
      let m = (window._iedCurrentRows || []).find(x => String(x.id) === pidStr || String(x.partner_code) === pidStr)
           || (window._currentRows || []).find(x => String(x.id) === pidStr || String(x.partner_code) === pidStr)
           || (window._lvCurrentRows || []).find(x => String(x.id) === pidStr || String(x.partner_code) === pidStr)
           || (window._vgkMemberCache || {})[pidStr];

      // Immediately pre-populate modal badges & preview from cached member (or neutral loading state) BEFORE awaiting network calls
      const initName = (m && (m.partner_name || m.member_name)) ? String(m.partner_name || m.member_name).trim() : 'Loading…';
      const initInitials = (m && (m.partner_name || m.member_name))
        ? initName.split(/\s+/).map(p => p[0]).join('').slice(0, 2).toUpperCase()
        : 'CP';
      const nameBadgePre = document.getElementById('postMemberNameBadge');
      if (nameBadgePre) nameBadgePre.textContent = initName;
      const prevNamePre = document.getElementById('prevName');
      if (prevNamePre) prevNamePre.textContent = initName.toUpperCase();
      const postSubPre = document.getElementById('postSubtitle');
      if (postSubPre) postSubPre.value = initName.toUpperCase();
      if (prevAvatar) {
        prevAvatar.textContent = initInitials;
        prevAvatar.style.display = 'flex';
      }
      const thumbImgPre = document.getElementById('postImageThumb');
      const thumbAvatarPre = document.getElementById('postImageThumbAvatar');
      if (thumbImgPre) thumbImgPre.style.display = 'none';
      if (thumbAvatarPre) {
        thumbAvatarPre.textContent = initInitials;
        thumbAvatarPre.style.display = 'flex';
      }
      const prevHighlightPre = document.getElementById('prevHighlight');
      if (prevHighlightPre) prevHighlightPre.textContent = '₹0/-';
      const prevHighlightWordsPre = document.getElementById('prevHighlightInWords');
      if (prevHighlightWordsPre) prevHighlightWordsPre.textContent = '—';
      const prevTotalTodayPre = document.getElementById('prevTotalToday');
      if (prevTotalTodayPre) prevTotalTodayPre.textContent = '₹0/-';
      const prevSeniorNamePre = document.getElementById('prevSeniorName');
      if (prevSeniorNamePre) prevSeniorNamePre.textContent = 'Direct Sponsor : —';
      const prevSeniorTodayPre = document.getElementById('prevSeniorToday');
      if (prevSeniorTodayPre) prevSeniorTodayPre.textContent = '₹0/-';
      const prevSeniorEarningPre = document.getElementById('prevSeniorEarning');
      if (prevSeniorEarningPre) prevSeniorEarningPre.textContent = '₹0/-';
      const prevSeniorPotentialPre = document.getElementById('prevSeniorPotential');
      if (prevSeniorPotentialPre) prevSeniorPotentialPre.textContent = '₹0/-';

      const apiBase = (typeof API_BASE !== 'undefined') ? API_BASE : (typeof API !== 'undefined' ? API : '/api/v1');
      const paramStr = pidStr.startsWith('VGK') ? 'partner_code=' + encodeURIComponent(pidStr) : 'partner_id=' + encodeURIComponent(pidStr);
      const knownPid = (m && m.id) ? m.id : (!pidStr.startsWith('VGK') ? partnerId : null);
      const knownParentPid = (m && m.parent_partner_id) ? m.parent_partner_id : null;

      // Parallelize fresh member metadata + member income entries + senior income entries (when IDs are already known)
      const [freshOutcome, entriesOutcome, seniorOutcome] = await Promise.all([
        safeFetch(apiBase + '/vgk/dashboard/member-earnings?' + paramStr + '&earners_only=false&include_poster_meta=true&_cb=' + Date.now())
          .then(res => res.json()).catch(e => { console.warn("Failed to fetch fresh member data from API:", e); return null; }),
        knownPid
          ? safeFetch(apiBase + '/vgk/dashboard/member-income-entries?partner_id=' + knownPid)
              .then(res => res.json()).catch(() => null)
          : Promise.resolve(null),
        knownParentPid
          ? safeFetch(apiBase + '/vgk/dashboard/member-income-entries?partner_id=' + knownParentPid)
              .then(res => res.json()).catch(() => null)
          : Promise.resolve(null)
      ]);

      if (reqSeq !== window._posterGenReqSeq) return;

      if (freshOutcome && freshOutcome.success && freshOutcome.data && freshOutcome.data.length) {
        const found = freshOutcome.data.find(x => String(x.id) === pidStr || String(x.partner_code) === pidStr);
        if (found) m = Object.assign({}, m || {}, found);
      }

      if (!m) throw new Error('Member details could not be loaded for ID: ' + pidStr);
      window._currentPosterMember = m;

      const prevName = document.getElementById('prevName');
      if (prevName) prevName.textContent = (m.partner_name || '').toUpperCase();
      
      const initials = (m.partner_name || '').trim().split(/\s+/).map(p => p[0]).join('').slice(0, 2).toUpperCase();
      if (prevAvatar) prevAvatar.textContent = initials;

      const memberCandidates = [
        m.logo_path,
        m.passport_photo,
        m.profile_image,
        m.photo_url,
        m.avatar_url,
        m.id_card_photo,
        m.photo
      ];
      loadPhotoWithFallback(prevImg, prevAvatar, memberCandidates, initials);

      // Update left control pane member profile photo thumbnail & name badge
      const thumbImg = document.getElementById('postImageThumb');
      const thumbAvatar = document.getElementById('postImageThumbAvatar');
      const nameBadge = document.getElementById('postMemberNameBadge');
      if (nameBadge) nameBadge.textContent = m.partner_name || '—';
      if (thumbImg || thumbAvatar) {
        loadPhotoWithFallback(thumbImg, thumbAvatar, memberCandidates, initials);
      }

      const targetPid = m.id || partnerId;
      let entries = (entriesOutcome && entriesOutcome.success && entriesOutcome.data) ? entriesOutcome.data : null;
      let entriesSummary = (entriesOutcome && entriesOutcome.summary) ? entriesOutcome.summary : null;
      const needEntriesFetch = !entries;
      const needSeniorFetch = Boolean(m.parent_partner_id && (!seniorOutcome || String(m.parent_partner_id) !== String(knownParentPid)));

      if (needEntriesFetch || needSeniorFetch) {
        const [lateEntriesD, lateSeniorD] = await Promise.all([
          needEntriesFetch
            ? safeFetch(apiBase + '/vgk/dashboard/member-income-entries?partner_id=' + targetPid).then(r => r.json()).catch(() => null)
            : Promise.resolve(entriesOutcome),
          needSeniorFetch
            ? safeFetch(apiBase + '/vgk/dashboard/member-income-entries?partner_id=' + m.parent_partner_id).then(r => r.json()).catch(() => null)
            : Promise.resolve(seniorOutcome)
        ]);
        if (reqSeq !== window._posterGenReqSeq) return;
        entries = (lateEntriesD && lateEntriesD.success && lateEntriesD.data) ? lateEntriesD.data : [];
        if (lateEntriesD && lateEntriesD.summary) entriesSummary = lateEntriesD.summary;
        window._seniorEntries = (lateSeniorD && lateSeniorD.success && lateSeniorD.data) ? lateSeniorD.data : [];
      } else {
        window._seniorEntries = (seniorOutcome && seniorOutcome.success && seniorOutcome.data) ? seniorOutcome.data : [];
      }
      window._currentEntries = entries;
      window._currentEntriesSummary = entriesSummary;

      const uniqueL1Leads = new Set();
      entries.forEach(e => {
        if (e.level === 1 && e.status !== 'CANCELLED' && e.source_lead_id) {
          uniqueL1Leads.add(e.source_lead_id);
        }
      });
      const activeFiles = uniqueL1Leads.size;

      // Authoritative Potential Pending Calculation on Active In-Flight Leads
      // Formula: Deal Value * Rank Rate (5.0% Base) + Brand Allowance (APS/Navgrun = ₹2k) + Field Support (1.5%) - Advances Already Paid
      const memberRatePct = (m.commission_pct || (m.current_position === 'Regional Manager' ? 9.0 : (m.current_position === 'General Manager' ? 8.5 : (m.current_position === 'Manager' ? 7.5 : (m.current_position === 'Channel Partner' ? 5.0 : 5.0))))) / 100.0;
      const activeLeadPendingMap = {};

      entries.forEach(e => {
        if (e.status !== 'CANCELLED' && e.source_lead_id) {
          const lid = e.source_lead_id;
          if (!activeLeadPendingMap[lid]) {
            const dVal = parseFloat(e.deal_value_total || e.deal_value || e.solar_value || 200000);
            const brandAmt = (e.solar_brand_id === 2 || e.solar_brand_name === 'APS' || e.brand_commission_amount) ? 2000 : 0;
            const isSupp = (e.level === 5 || e.is_field_support === true || String(e.vgk_field_support_id) === String(targetPid) || String(e.vgk_field_support_id) === String(m.id));
            activeLeadPendingMap[lid] = { 
              dealValue: dVal, 
              brandAllowance: brandAmt,
              isSupport: isSupp,
              paid: 0, 
              hasFinalComm: false 
            };
          }
          if (e.level === 5 || e.is_field_support === true || String(e.vgk_field_support_id) === String(targetPid) || String(e.vgk_field_support_id) === String(m.id)) {
            activeLeadPendingMap[lid].isSupport = true;
          }
          const grossAmt = parseFloat(e.commission_amount || 0);
          const advAdj = parseFloat(e.advance_adjusted_amount || 0);
          const lostDed = parseFloat(e.lost_lead_deduction || 0);
          const balGross = (e.balance_gross !== undefined && e.balance_gross !== null)
            ? parseFloat(e.balance_gross)
            : Math.max(0, grossAmt - advAdj - lostDed);
          if (e.status === 'PAID' || e.status === 'RELEASED' || e.status === 'STAGE1_APPROVED' || e.status === 'STAGE2_APPROVED' || e.status === 'VERIFIED') {
            activeLeadPendingMap[lid].paid += balGross;
          }
          if (e.kind === 'COMMISSION' && (e.status === 'PAID' || e.status === 'RELEASED') && (e.level === 1 || e.level === 6)) {
            activeLeadPendingMap[lid].hasFinalComm = true;
          }
        }
      });

      let truePotentialPending = 0;
      Object.keys(activeLeadPendingMap).forEach(lid => {
        const item = activeLeadPendingMap[lid];
        if (!item.hasFinalComm) {
          let expectedTotal = item.dealValue * memberRatePct;
          if (item.brandAllowance > 0) expectedTotal += item.brandAllowance;
          if (item.isSupport) expectedTotal += (item.dealValue * 0.015);
          const remaining = Math.max(0, expectedTotal - item.paid);
          truePotentialPending += remaining;

          console.log(`[VGK POSTER DEBUG] Lead: ${lid} | Member: ${targetPid} | Deal: ${item.dealValue} | Sourcing Comm: ${item.dealValue * memberRatePct} | Is Support: ${item.isSupport} | Support Comm: ${item.isSupport ? item.dealValue * 0.015 : 0} | Brand: ${item.brandAllowance} | Paid: ${item.paid} | Remaining Potential Pending: ${remaining}`);
        }
      });

      window._postTotalTodayUserEdited = false;
      window._postCustomerUserEdited = false;

      const todayStr = new Date().toISOString().split('T')[0];
      const validDates = entries.filter(e => e.status !== 'CANCELLED' && e.income_date && e.income_date !== 'None').map(e => String(e.income_date).slice(0, 10)).sort();
      const lastEarningDate = (validDates.includes(todayStr))
        ? todayStr
        : (validDates.length > 0 ? validDates[validDates.length - 1] : todayStr);

      let initFrom = todayStr;
      let initTo   = todayStr;
      if (!validDates.includes(todayStr) && validDates.length > 0) {
        initFrom = lastEarningDate;
        initTo   = lastEarningDate;
      }

      const pDateFrom = document.getElementById('postPayoutDateFrom');
      const pDateTo = document.getElementById('postPayoutDateTo');
      if (pDateFrom) pDateFrom.value = initFrom;
      if (pDateTo) pDateTo.value = initTo;

      const seniorName = m.senior_name || '—';
      const seniorEarning = m.senior_earning !== null && m.senior_earning !== undefined ? '₹' + _meFormatInr(m.senior_earning) + '/-' : '—';

      let customerName = '—', location = '—';
      const targetEntries = entries.filter(e => e.status !== 'CANCELLED' && (!initFrom || e.income_date >= initFrom) && (!initTo || e.income_date <= initTo));
      if (targetEntries.length) {
        const l1Entry = targetEntries.find(e => e.level === 1 && (e.client_name || e.customer_name));
        const chosen = l1Entry || targetEntries[0];
        customerName = chosen.client_name || chosen.customer_name || '—';
        location = chosen.location || chosen.city || '—';
      } else if (entries.length) {
        customerName = entries[0].client_name || entries[0].customer_name || '—';
        location = entries[0].location || entries[0].city || '—';
      }

      const installedStages = ['completed', 'completed_paid', 'subsidy_pending', 'subsidy_received', 'net_meter_done', 'installed'];
      const installedSet = new Set();
      entries.forEach(e => {
        if (e.level === 1 && e.status !== 'CANCELLED' && e.source_lead_id) {
          const stageStr = (e.stage_name || e.solar_pipeline_status || e.lead_status || e.stage || '').toString().toLowerCase();
          const hasInstDate = !!(e.installation_date && e.installation_date !== 'None' && e.installation_date !== 'null') ||
                              !!(e.installed_at && e.installed_at !== 'None' && e.installed_at !== 'null') ||
                              !!(e.install_date && e.install_date !== 'None' && e.install_date !== 'null');
          const isCompletedStage = installedStages.some(s => stageStr === s || stageStr.startsWith(s));
          const hasFinalCommPaid = (e.kind === 'COMMISSION' && (e.status === 'PAID' || e.status === 'RELEASED') && (e.level === 1 || e.level === 6));
          
          if (hasInstDate || isCompletedStage || hasFinalCommPaid) {
            installedSet.add(e.source_lead_id);
          }
        }
      });
      let installedFiles = installedSet.size;
      const summaryObj = (typeof entriesSummary !== 'undefined' && entriesSummary) ? entriesSummary : (window._currentEntriesSummary || null);
      if (installedFiles === 0 && summaryObj && summaryObj.installed_files !== undefined) {
        installedFiles = summaryObj.installed_files;
      }
      const filesDisplay = `${installedFiles}/${activeFiles || m.ground_leads_count || 4} FILES`;

      const setVal = (id, val) => { const el = document.getElementById(id); if (el) el.value = val; };
      const setChecked = (id, val) => { const el = document.getElementById(id); if (el) el.checked = val; };

      let rankTitle = m.career_designation || m.current_designation || m.rank_display || 'Channel Partner';
      // Clean any residual star symbols or numeric prefixes
      rankTitle = rankTitle.replace(/^[0-9]+[★\*\s]*/g, '').replace(/[★\*⭐]/g, '').trim();
      if (rankTitle.toUpperCase().includes('SENIOR CHANNEL PARTNER') || rankTitle.toUpperCase().includes('LEAD CHANNEL PARTNER')) rankTitle = 'Channel Partner';
      else if (rankTitle.toUpperCase().includes('ZONAL MANAGER')) rankTitle = 'Manager';
      else if (rankTitle.toUpperCase().includes('DIRECTOR')) rankTitle = 'Regional Manager';
      if (!rankTitle || rankTitle.toLowerCase() === 'none') rankTitle = 'Channel Partner';

      setVal('postTitle', 'CONGRATULATIONS');
      setVal('postSubtitle', m.partner_name || '');
      setVal('postRank', rankTitle);

      const prevChampionBadgeEl = document.getElementById('prevChampionBadge');
      if (prevChampionBadgeEl) {
        prevChampionBadgeEl.textContent = `🏆 TOP PERFORMER`;
      }

      const prevCelebrationTitleEl = document.getElementById('prevCelebrationTitle');
      if (prevCelebrationTitleEl) {
        prevCelebrationTitleEl.textContent = `🎉 👑 CONGRATULATIONS 👑 🎉`;
      }

      // Overall Earning: Total cumulative earnings irrespective of level (Incomes total only - excludes direct cash advances)
      const allTimeSum = entries.reduce((sum, e) => {
        if (e.status === 'CANCELLED') return sum;
        if (e.entry_number && String(e.entry_number).startsWith('VSCA-')) return sum;
        if (e.id && String(e.id).startsWith('VSCA-')) return sum;
        const _k = String(e.kind || '').toUpperCase();
        const isDirAdv = (
          e.display_kind === 'Direct Advance' ||
          e.kind === 'DIRECT_ADVANCE' ||
          (!e.source_lead_id && ['ADVANCE', 'STAGE1_ADVANCE', 'DIRECT_ADVANCE', 'PARTNER_ADVANCE'].includes(_k)) ||
          e.level === 0
        );
        if (isDirAdv) return sum;

        const gross = parseFloat(e.commission_amount || e.amount || 0) || 0;
        return sum + gross;
      }, 0);
      const overallVal = (allTimeSum > 0) ? allTimeSum : ((m.all_time_gross_earned !== undefined && m.all_time_gross_earned !== null) ? m.all_time_gross_earned : ((m.gross_earned !== undefined && m.gross_earned !== null) ? m.gross_earned : (m.received || 0)));
      setVal('postHighlight', '₹' + _meFormatInr(overallVal) + '/-');
      setVal('postFiles', filesDisplay);

      if (m.total_team_size && m.total_team_size > 0) {
        setVal('postOverall', `${m.total_team_size} ${m.total_team_size === 1 ? 'MEMBER' : 'MEMBERS'}`);
        setVal('postTeamBreakup', `Direct Team: ${m.team_l2_count || m.total_team_size} Channel Partners`);
      } else {
        const directFiles = m.own_qualifying_files !== undefined ? m.own_qualifying_files : (m.total_files || (activeFiles || m.ground_leads_count || 0));
        setVal('postOverall', `${directFiles} FILES`);
        setVal('postTeamBreakup', `Direct Personal Production: ${directFiles} Files`);
      }
      // Member Gross Potential Valuation (calculated from active entries)
      const potVal = truePotentialPending;
      console.log(`[VGK POSTER DEBUG] Setting postPotential: ₹${_meFormatInr(potVal)}/-`);
      setVal('postPotential', '₹' + _meFormatInr(potVal) + '/-');
      const prevPotEl = document.getElementById('prevPotential');
      if (prevPotEl) prevPotEl.textContent = '₹' + _meFormatInr(potVal) + '/-';
      setVal('postCustomer', customerName);
      setVal('postLocation', location);
      setVal('postSeniorName', seniorName);
      // Senior Metrics: Overall Cumulative Earnings & Net Potential Pending
      const srEntries = window._seniorEntries || [];
      const srUniquePot = {};
      let srAdvPaidTotal = 0;
      srEntries.forEach(se => {
        if (se.status !== 'CANCELLED') {
          const lid = se.source_lead_id || 0;
          const lvl = se.level !== null && se.level !== undefined ? se.level : -1;
          const key = `${lid}_${lvl}`;
          const val = se.potential_overall_earning || se.commission_amount || 0;
          if (!srUniquePot[key] || val > srUniquePot[key]) srUniquePot[key] = val;
          const _sk = String(se.kind || '').toUpperCase();
          const sIsDirAdv = (
            se.display_kind === 'Direct Advance' ||
            se.kind === 'DIRECT_ADVANCE' ||
            (!se.source_lead_id && ['ADVANCE', 'STAGE1_ADVANCE', 'DIRECT_ADVANCE', 'PARTNER_ADVANCE'].includes(_sk)) ||
            se.level === 0
          );
          if (!sIsDirAdv && (se.kind === 'ADVANCE' || se.kind === 'DVR_ADVANCE')) {
            const sGross = parseFloat(se.commission_amount || 0);
            const sAdv = parseFloat(se.advance_adjusted_amount || 0);
            const sLost = parseFloat(se.lost_lead_deduction || 0);
            const sBal = (se.balance_gross !== undefined && se.balance_gross !== null) ? parseFloat(se.balance_gross) : Math.max(0, sGross - sAdv - sLost);
            srAdvPaidTotal += sBal;
          }
        }
      });
      // Senior Overall Earning: Total cumulative earnings across all valid commission entries (Incomes total only - excludes direct cash advances)
      const srAllTimeSum = srEntries.reduce((sum, e) => {
        if (e.status === 'CANCELLED') return sum;
        if (e.entry_number && String(e.entry_number).startsWith('VSCA-')) return sum;
        if (e.id && String(e.id).startsWith('VSCA-')) return sum;
        const _k = String(e.kind || '').toUpperCase();
        const isDirAdv = (
          e.display_kind === 'Direct Advance' ||
          e.kind === 'DIRECT_ADVANCE' ||
          (!e.source_lead_id && ['ADVANCE', 'STAGE1_ADVANCE', 'DIRECT_ADVANCE', 'PARTNER_ADVANCE'].includes(_k)) ||
          e.level === 0
        );
        if (isDirAdv) return sum;

        const gross = parseFloat(e.commission_amount || e.amount || 0) || 0;
        return sum + gross;
      }, 0);
      const srGrossPotTotal = Object.values(srUniquePot).reduce((a, b) => a + b, 0);
      const srNetPotTotal = Math.max(0, srGrossPotTotal - srAdvPaidTotal);
      const seniorPotentialVal = (srNetPotTotal > 0)
        ? '₹' + _meFormatInr(srNetPotTotal) + '/-'
        : ((m.senior_potential_earned !== undefined && m.senior_potential_earned !== null && m.senior_potential_earned > 0)
            ? '₹' + _meFormatInr(m.senior_potential_earned) + '/-'
            : '—');
      const seniorOverallRaw = (srAllTimeSum > 0)
        ? srAllTimeSum
        : ((m.senior_earning !== undefined && m.senior_earning !== null)
            ? m.senior_earning
            : srAdvPaidTotal);
      const seniorOverallVal = (seniorOverallRaw > 0) ? '₹' + _meFormatInr(seniorOverallRaw) + '/-' : '—';

      let srTodayAmt = 0;
      const todayIso = new Date().toISOString().split('T')[0];
      srEntries.forEach(se => {
        if (se.status !== 'CANCELLED') {
          const dStr = (se.income_date || se.created_at || '').slice(0, 10);
          if (dStr === todayIso) {
            const sGross = parseFloat(se.commission_amount || 0);
            const sAdv = parseFloat(se.advance_adjusted_amount || se.advance_paid || 0);
            const sLost = parseFloat(se.lost_lead_deduction || 0);
            const sBal = (se.balance_gross !== undefined && se.balance_gross !== null) ? parseFloat(se.balance_gross) : Math.max(0, sGross - sAdv - sLost);
            srTodayAmt += sBal;
          }
        }
      });
      if (srTodayAmt === 0) {
        entries.forEach(e => {
          if (e.status !== 'CANCELLED' && (e.level === 2 || (e.kind || '').toUpperCase() === 'SENIOR_COMM')) {
            const dStr = (e.income_date || e.created_at || '').slice(0, 10);
            if (dStr === todayIso) {
              const sGross = parseFloat(e.commission_amount || 0);
              const sAdv = parseFloat(e.advance_adjusted_amount || e.advance_paid || 0);
              const sLost = parseFloat(e.lost_lead_deduction || 0);
              const sBal = (e.balance_gross !== undefined && e.balance_gross !== null) ? parseFloat(e.balance_gross) : Math.max(0, sGross - sAdv - sLost);
              srTodayAmt += sBal;
            }
          }
        });
      }

      setVal('postSeniorToday', '₹' + _meFormatInr(srTodayAmt) + '/-');
      setVal('postSeniorPotential', seniorPotentialVal);
      setVal('postSeniorEarning', seniorOverallVal);

      const seniorNameUpper = (seniorName || '').toUpperCase().trim();
      const isVgkSupport = seniorNameUpper.includes('VGK SUPPORT') || seniorNameUpper.includes('SUPPORT') || seniorNameUpper === 'NONE' || seniorNameUpper === '—' || !seniorNameUpper;
      
      const postShowSeniorEl = document.getElementById('postShowSenior');
      if (postShowSeniorEl) {
        postShowSeniorEl.disabled = false;
        if (isVgkSupport) {
          postShowSeniorEl.checked = false;
          postShowSeniorEl.disabled = true;
        } else {
          postShowSeniorEl.checked = true;
        }
      }

      setChecked('payTypeStage1', true);
      setChecked('payTypeStage2Adv', true);
      setChecked('payTypeFinalComm', true);
      setChecked('payTypeSupport', true);
      setChecked('payTypeBrand', true);
      setChecked('payTypeBonanza', true);
      setChecked('payTypeExtra', true);
      setChecked('payTypeAward', true);

      const seniorImg = document.getElementById('prevSeniorImg');
      const seniorAvatar = document.getElementById('prevSeniorAvatar');
      if (seniorImg) {
        const seniorInitials = (seniorName || 'SR').trim().split(/\s+/).map(p => p[0]).join('').slice(0, 2).toUpperCase();
        const seniorCandidates = [
          m.senior_logo_path,
          m.senior_photo,
          m.senior_passport_photo,
          m.senior_profile_image,
          m.senior_photo_url,
          m.senior_avatar_url
        ];
        loadPhotoWithFallback(seniorImg, seniorAvatar, seniorCandidates, seniorInitials);
      }

      const tplSelect = document.getElementById('postShareTemplate');
      if (tplSelect) tplSelect.value = 'full';
      window._posterCustomTextEdited = false;

      if (document.getElementById('postThemePreset')) document.getElementById('postThemePreset').value = 'celebration_graphic';
      changeThemePreset();
      recalculateTodayPayout();
      if (typeof window.resetPosterCustomText === 'function') {
        window.resetPosterCustomText();
      }
    } catch (err) {
      alert('Failed to generate poster: ' + err.message);
      closePosterModal();
    } finally {
      if (spinner) spinner.style.display = 'none';
    }
  }

  function openPosterFromUnified(partnerId) {
    generateMemberPoster(partnerId);
  }

  function _meFormatInr(v) {
    if (isNaN(v)) return v;
    return new Intl.NumberFormat('en-IN').format(Math.round(v));
  }

  function changePayoutDateRange() {
    window._postTotalTodayUserEdited = false;
    recalculateTodayPayout();
  }

  function setPosterPresetPeriod(period) {
    window._postTotalTodayUserEdited = false;
    window._postCustomerUserEdited = false;
    const today = new Date();
    const todayStr = today.toISOString().split('T')[0];
    let fromStr = todayStr;
    let toStr = todayStr;

    if (period === 'today') {
      fromStr = todayStr;
      toStr = todayStr;
    } else if (period === 'week') {
      const d = new Date(today);
      const day = d.getDay();
      const diff = d.getDate() - day + (day === 0 ? -6 : 1);
      const monday = new Date(d.setDate(diff));
      fromStr = monday.toISOString().split('T')[0];
      toStr = todayStr;
    } else if (period === 'month') {
      const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
      fromStr = firstDay.toISOString().split('T')[0];
      toStr = todayStr;
    } else if (period === 'all') {
      const entries = window._currentEntries || [];
      const validDates = entries.filter(e => e.status !== 'CANCELLED' && e.income_date && e.income_date !== 'None').map(e => String(e.income_date).slice(0, 10)).sort();
      if (validDates.length > 0) {
        fromStr = validDates[0];
        toStr = validDates[validDates.length - 1];
      } else {
        fromStr = '2025-01-01';
        toStr = todayStr;
      }
    }

    const elFrom = document.getElementById('postPayoutDateFrom');
    const elTo = document.getElementById('postPayoutDateTo');
    if (elFrom) elFrom.value = fromStr;
    if (elTo) elTo.value = toStr;
    recalculateTodayPayout();
  }

  function recalculateTodayPayout(resetUserEdited = false) {
    if (resetUserEdited) {
      window._postTotalTodayUserEdited = false;
    }
    const showStage1    = document.getElementById('payTypeStage1')?.checked ?? true;
    const showStage2Adv = document.getElementById('payTypeStage2Adv')?.checked ?? true;
    const showFinalComm = document.getElementById('payTypeFinalComm')?.checked ?? true;
    const showSupport   = document.getElementById('payTypeSupport')?.checked ?? showFinalComm;
    const showBrand     = document.getElementById('payTypeBrand')?.checked ?? true;
    const showBonanza   = document.getElementById('payTypeBonanza')?.checked ?? true;
    const showExtra     = document.getElementById('payTypeExtra')?.checked ?? true;
    const showAward     = document.getElementById('payTypeAward')?.checked ?? true;

    const entries = window._currentEntries || [];
    const dateFrom = (document.getElementById('postPayoutDateFrom')?.value || '').trim();
    const dateTo = (document.getElementById('postPayoutDateTo')?.value || '').trim();

    const todayIsoStr = new Date().toISOString().split('T')[0];
    const isSingleDay = Boolean(dateFrom && dateTo && dateFrom === dateTo);
    const isToday = isSingleDay && (dateFrom === todayIsoStr);
    window._posterIsSingleDay = isSingleDay;
    window._posterIsToday = isToday;
    window._posterPeriodTitleText = isToday ? "Today's Earning" : (isSingleDay ? "Single Day Earning" : "This Period Earning");
    window._posterPeriodPayoutText = isToday ? "Today's Payout" : (isSingleDay ? "Single Day Payout" : "This Period Payout");

    const prevTodayLabelTextEl = document.getElementById('prevTodayLabelText');
    if (prevTodayLabelTextEl) {
      prevTodayLabelTextEl.textContent = window._posterPeriodTitleText;
    }

    let periodLabel = '';
    const fmtDate = dStr => {
      if (!dStr) return '';
      try {
        const [y, m, d] = dStr.split('-');
        return `${d}/${m}/${y}`;
      } catch (e) { return dStr; }
    };

    if (dateFrom && dateTo && dateFrom === dateTo) {
      periodLabel = fmtDate(dateFrom);
    } else if (dateFrom && dateTo) {
      periodLabel = `${fmtDate(dateFrom)} — ${fmtDate(dateTo)}`;
    } else if (dateFrom) {
      periodLabel = `From ${fmtDate(dateFrom)}`;
    } else if (dateTo) {
      periodLabel = `Up to ${fmtDate(dateTo)}`;
    } else {
      periodLabel = 'All Time';
    }

    const prevPeriodDateRangeEl = document.getElementById('prevPeriodDateRange');
    if (prevPeriodDateRangeEl) {
      prevPeriodDateRangeEl.textContent = periodLabel;
      prevPeriodDateRangeEl.style.display = periodLabel ? 'block' : 'none';
    }

    const prevSeniorTodayLabelEl = document.getElementById('prevSeniorTodayLabel');
    if (prevSeniorTodayLabelEl) {
      prevSeniorTodayLabelEl.textContent = isSingleDay ? (isToday ? 'Today' : 'Single Day') : 'This Period';
    }

    // Automatically update Customer Name & Location based on the selected date range if user hasn't typed custom customer
    if (!window._postCustomerUserEdited) {
      const matchingEntries = entries.filter(e => {
        if (e.status === 'CANCELLED') return false;
        const incD = (e.income_date && e.income_date !== 'None') ? String(e.income_date).slice(0, 10) : '';
        const trigD = (e.trigger_date && e.trigger_date !== 'None') ? String(e.trigger_date).slice(0, 10) : '';
        const createD = (e.created_at && e.created_at !== 'None') ? String(e.created_at).slice(0, 10) : '';
        const pmtD = (e.payment_date && e.payment_date !== 'None') ? String(e.payment_date).slice(0, 10) : '';
        if (dateFrom && dateTo) {
          return (incD && incD >= dateFrom && incD <= dateTo) ||
                 (trigD && trigD >= dateFrom && trigD <= dateTo) ||
                 (createD && createD >= dateFrom && createD <= dateTo) ||
                 (pmtD && pmtD >= dateFrom && pmtD <= dateTo);
        } else if (dateFrom) {
          return (incD >= dateFrom) || (trigD >= dateFrom) || (createD >= dateFrom) || (pmtD >= dateFrom);
        } else if (dateTo) {
          return (incD <= dateTo) || (trigD <= dateTo) || (createD <= dateTo) || (pmtD <= dateTo);
        }
        return true;
      });

      if (matchingEntries.length > 0) {
        // Sort descending so the latest lead in the period is selected
        matchingEntries.sort((a, b) => {
          const dateA = a.income_date || a.trigger_date || a.payment_date || a.created_at || '';
          const dateB = b.income_date || b.trigger_date || b.payment_date || b.created_at || '';
          if (dateA !== dateB) return dateB.localeCompare(dateA);
          return (b.id || 0) - (a.id || 0);
        });
        const l1 = matchingEntries.find(e => e.level === 1 && (e.client_name || e.customer_name));
        const chosen = l1 || matchingEntries[0];
        const postCustomerEl = document.getElementById('postCustomer');
        const postLocationEl = document.getElementById('postLocation');
        if (postCustomerEl && (chosen.client_name || chosen.customer_name)) {
          postCustomerEl.value = chosen.client_name || chosen.customer_name;
        }
        if (postLocationEl && (chosen.location || chosen.city)) {
          postLocationEl.value = chosen.location || chosen.city;
        }
      }
    }

    let stage1Amt = 0, stage2AdvAmt = 0;
    let supportAmt = 0;
    let brandAmt = 0, bonanzaAmt = 0, extraAmt = 0, awardAmt = 0, seniorTodayAmt = 0;
    let commByLevel = {};
    const finalCommLeadIds = new Set();

    // All partner income entries calculation for the selected date context
    entries.forEach(e => {
      if (e.status !== 'CANCELLED') {
        const incD = (e.income_date && e.income_date !== 'None') ? String(e.income_date).slice(0, 10) : '';
        const trigD = (e.trigger_date && e.trigger_date !== 'None') ? String(e.trigger_date).slice(0, 10) : '';
        const createD = (e.created_at && e.created_at !== 'None') ? String(e.created_at).slice(0, 10) : '';
        const pmtD = (e.payment_date && e.payment_date !== 'None') ? String(e.payment_date).slice(0, 10) : '';

        let inDateRange = true;
        if (dateFrom && dateTo) {
          inDateRange = (incD && incD >= dateFrom && incD <= dateTo) ||
                        (trigD && trigD >= dateFrom && trigD <= dateTo) ||
                        (createD && createD >= dateFrom && createD <= dateTo) ||
                        (pmtD && pmtD >= dateFrom && pmtD <= dateTo);
        } else if (dateFrom) {
          inDateRange = (incD && incD >= dateFrom) || (trigD && trigD >= dateFrom) || (createD && createD >= dateFrom) || (pmtD && pmtD >= dateFrom);
        } else if (dateTo) {
          inDateRange = (incD && incD <= dateTo) || (trigD && trigD <= dateTo) || (createD && createD <= dateTo) || (pmtD && pmtD <= dateTo);
        }

        if (!inDateRange) return;

        const grossAmt = parseFloat(e.commission_amount || e.amount || 0);
        const advAdj = parseFloat(e.advance_adjusted_amount || 0);
        const lostDed = parseFloat(e.lost_lead_deduction || 0);
        const balGross = (e.balance_gross !== undefined && e.balance_gross !== null)
          ? parseFloat(e.balance_gross)
          : Math.max(0, grossAmt - advAdj - lostDed);
        const k = (e.kind || '').toUpperCase();
        const typeStr = (e.income_type || '').toLowerCase();

        const isDirAdv = (
          e.display_kind === 'Direct Advance' ||
          e.kind === 'DIRECT_ADVANCE' ||
          (!e.source_lead_id && ['ADVANCE', 'STAGE1_ADVANCE', 'DIRECT_ADVANCE', 'PARTNER_ADVANCE'].includes(k)) ||
          e.level === 0
        );
        if (isDirAdv) return;

        if (k === 'ADVANCE' || typeStr.includes('stage 1 adv')) {
          stage1Amt += balGross;
        } else if (k === 'DVR_ADVANCE' || typeStr.includes('stage 2 adv')) {
          stage2AdvAmt += balGross;
        } else if (k === 'BRAND_COMMISSION' || typeStr.includes('brand')) {
          brandAmt += balGross;
        } else if (k === 'SLAB_BONUS' || typeStr.includes('bonanza') || typeStr.includes('slab')) {
          bonanzaAmt += balGross;
        } else if (k === 'EXTRA_COMMISSION' || typeStr.includes('extra')) {
          extraAmt += balGross;
        } else if (k === 'AWARD' || k === 'INCENTIVE' || k === 'ROYALTY' || typeStr.includes('award') || typeStr.includes('incentive')) {
          awardAmt += balGross;
        } else if (e.level === 5 || (e.level_label || '').toLowerCase().includes('support')) {
          supportAmt += balGross;
          if (e.source_lead_id) finalCommLeadIds.add(e.source_lead_id);
        } else if (k === 'COMMISSION' || k === 'SENIOR_COMM') {
          const lvl = e.level || 1;
          const lbl = e.level_label || (lvl === 1 ? 'L1 Ground Source Comm' : (lvl === 2 ? 'L2 Senior Referrer Comm' : `L${lvl} Commission`));
          if (!commByLevel[lbl]) commByLevel[lbl] = 0;
          commByLevel[lbl] += balGross;
          if (e.source_lead_id) finalCommLeadIds.add(e.source_lead_id);
        }
      }
    });

    let breakupItems = [];
    let total = 0;

    if (showStage1 && stage1Amt > 0) {
      breakupItems.push(`Stage 1 Advance: ₹${_meFormatInr(stage1Amt)}/-`);
      total += stage1Amt;
    }
    if (showStage2Adv && stage2AdvAmt > 0) {
      breakupItems.push(`Stage 2 Advance: ₹${_meFormatInr(stage2AdvAmt)}/-`);
      total += stage2AdvAmt;
    }
    if (showFinalComm && Object.keys(commByLevel).length > 0) {
      for (const [lbl, amt] of Object.entries(commByLevel)) {
        if (amt > 0) {
          breakupItems.push(`${lbl}: ₹${_meFormatInr(amt)}/-`);
          total += amt;
        }
      }
    }
    if (showSupport && supportAmt > 0) {
      breakupItems.push(`Field Support (L5): ₹${_meFormatInr(supportAmt)}/-`);
      total += supportAmt;
    }
    if (showBrand && brandAmt > 0) {
      breakupItems.push(`Brand Commission: ₹${_meFormatInr(brandAmt)}/-`);
      total += brandAmt;
    }
    if (showBonanza && bonanzaAmt > 0) {
      breakupItems.push(`Bonanza Bonus: ₹${_meFormatInr(bonanzaAmt)}/-`);
      total += bonanzaAmt;
    }
    if (showExtra && extraAmt > 0) {
      breakupItems.push(`Extra Comm: ₹${_meFormatInr(extraAmt)}/-`);
      total += extraAmt;
    }
    if (showAward && awardAmt > 0) {
      breakupItems.push(`Award Incentive: ₹${_meFormatInr(awardAmt)}/-`);
      total += awardAmt;
    }

    if (breakupItems.length === 0) {
      breakupItems.push("No Payouts for Selected Date");
    }

    // Calculate prior advances already paid on previous dates for the leads in this final payout
    let totalPriorAdvPaid = 0;
    if (finalCommLeadIds.size > 0) {
      entries.forEach(e => {
        if (e.status !== 'CANCELLED' && finalCommLeadIds.has(e.source_lead_id)) {
          const isPriorDate = !dateFrom || (e.income_date && e.income_date < dateFrom);
          const isAdvKind = (e.kind === 'ADVANCE' || e.kind === 'DVR_ADVANCE');
          if (isPriorDate && isAdvKind && (e.status === 'PAID' || Boolean(e.paid_at))) {
            const advBal = (e.balance_gross !== undefined && e.balance_gross !== null) ? parseFloat(e.balance_gross) : Math.max(0, (parseFloat(e.commission_amount || 0) || 0) - (parseFloat(e.advance_adjusted_amount || 0) || 0));
            totalPriorAdvPaid += advBal;
          }
        }
      });
    }

    const payingGross = total;

    const postTodayPayoutEl = document.getElementById('postTodayPayout');
    if (postTodayPayoutEl) postTodayPayoutEl.value = breakupItems.map(s => s.replace(/<[^>]*>/g, '')).join(' | ');

    const postTotalTodayEl = document.getElementById('postTotalToday');
    if (postTotalTodayEl && !window._postTotalTodayUserEdited) {
      postTotalTodayEl.value = '₹' + _meFormatInr(payingGross) + '/-';
    }

    // Senior Partner Today Earning calculation from window._seniorEntries for date range
    seniorTodayAmt = 0;
    if (window._seniorEntries && window._seniorEntries.length) {
      window._seniorEntries.forEach(se => {
        if (se.status !== 'CANCELLED') {
          const sd = (se.income_date || se.created_at || '').slice(0, 10);
          if (sd && sd !== 'None') {
            if (dateFrom && sd < dateFrom) return;
            if (dateTo && sd > dateTo) return;
          }
          const sGross = parseFloat(se.commission_amount || se.amount || 0);
          const sAdv = parseFloat(se.advance_adjusted_amount || se.advance_paid || 0);
          const sLost = parseFloat(se.lost_lead_deduction || 0);
          const sBal = (se.balance_gross !== undefined && se.balance_gross !== null) ? parseFloat(se.balance_gross) : Math.max(0, sGross - sAdv - sLost);
          seniorTodayAmt += sBal;
        }
      });
    }

    const postSeniorToday = document.getElementById('postSeniorToday');
    if (postSeniorToday) {
      postSeniorToday.value = '₹' + _meFormatInr(seniorTodayAmt) + '/-';
    }

    window._currentTotalAdvPaid = totalPriorAdvPaid;
    const prevTotalTodayEl = document.getElementById('prevTotalToday');
    if (prevTotalTodayEl) prevTotalTodayEl.textContent = '₹' + _meFormatInr(payingGross) + '/-';

    const prevAlreadyPaidEl = document.getElementById('prevAlreadyPaidText');
    if (prevAlreadyPaidEl) {
      if (totalPriorAdvPaid > 0) {
        prevAlreadyPaidEl.textContent = `(Already Paid: ₹${_meFormatInr(totalPriorAdvPaid)}/-)`;
        prevAlreadyPaidEl.style.display = 'block';
      } else {
        prevAlreadyPaidEl.style.display = 'none';
        prevAlreadyPaidEl.textContent = '';
      }
    }

    updatePoster();
  }

  function numberToWordsInr(num) {
    num = Math.floor(Math.abs(Number(num) || 0));
    if (num === 0) return "Rupees Zero Only";

    const a = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine', 'Ten', 
               'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen'];
    const b = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety'];

    function inWords(n) {
      if (n < 20) return a[n];
      if (n < 100) return b[Math.floor(n / 10)] + (n % 10 ? ' ' + a[n % 10] : '');
      if (n < 1000) return a[Math.floor(n / 100)] + ' Hundred' + (n % 100 ? ' ' + inWords(n % 100) : '');
      if (n < 100000) return inWords(Math.floor(n / 1000)) + ' Thousand' + (n % 1000 ? ' ' + inWords(n % 1000) : '');
      if (n < 10000000) return inWords(Math.floor(n / 100000)) + ' Lakh' + (n % 100000 ? ' ' + inWords(n % 100000) : '');
      return inWords(Math.floor(n / 10000000)) + ' Crore' + (n % 10000000 ? ' ' + inWords(n % 10000000) : '');
    }

    return 'Rupees ' + inWords(num) + ' Only';
  }

  function updatePoster() {
    const getVal = id => document.getElementById(id)?.value || '';
    const setTxt = (id, txt) => { const el = document.getElementById(id); if (el) el.textContent = txt; };

    setTxt('prevTitle', getVal('postTitle').toUpperCase());
    
    let rankVal = (getVal('postRank') || '').toUpperCase().trim();
    rankVal = rankVal.replace(/^[0-9]+[★\*\s]*/g, '').replace(/[★\*⭐]/g, '').trim();
    if (rankVal.includes('SENIOR CHANNEL PARTNER') || rankVal.includes('LEAD CHANNEL PARTNER')) rankVal = 'CHANNEL PARTNER';
    else if (rankVal.includes('ZONAL MANAGER')) rankVal = 'MANAGER';
    else if (rankVal.includes('DIRECTOR')) rankVal = 'REGIONAL MANAGER';
    if (!rankVal) rankVal = 'CHANNEL PARTNER';
    const nameVal = (getVal('postSubtitle') || '').toUpperCase().trim();

    const prevRankEl = document.getElementById('prevRank');
    const prevRankContainerEl = document.getElementById('prevRankContainer');
    if (prevRankEl) {
      prevRankEl.textContent = rankVal;
      if (prevRankContainerEl) prevRankContainerEl.style.display = rankVal ? 'inline-flex' : 'none';
    }
    const prevNameEl = document.getElementById('prevName');
    if (prevNameEl) {
      prevNameEl.textContent = nameVal || 'MEMBER NAME';
    }

    const rawHighlight = getVal('postHighlight');
    setTxt('prevHighlight', rawHighlight);
    const numOnly = rawHighlight.replace(/[^0-9]/g, '');
    const prevHighlightInWordsEl = document.getElementById('prevHighlightInWords');
    if (prevHighlightInWordsEl && numOnly) {
      const wordsStr = numberToWordsInr(numOnly);
      prevHighlightInWordsEl.textContent = wordsStr;
      if (wordsStr.length > 55) {
        prevHighlightInWordsEl.style.fontSize = '8px';
      } else if (wordsStr.length > 42) {
        prevHighlightInWordsEl.style.fontSize = '8.5px';
      } else {
        prevHighlightInWordsEl.style.fontSize = '9.5px';
      }
    }

    const filesVal = getVal('postFiles').toUpperCase().trim();
    const prevFilesEl = document.getElementById('prevFiles');
    const prevTeamBreakupFilesEl = document.getElementById('prevTeamBreakupFiles');
    if (prevFilesEl) {
      const match = filesVal.match(/^(\d+)\s*\/\s*(\d+)/);
      if (match) {
        prevFilesEl.innerHTML = `<span style="display:inline-flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#f59e0b,#eab308);color:#0f172a;font-weight:950;font-size:9.5px;padding:2px 6px;border-radius:4px;line-height:1;white-space:nowrap">${match[1]} INSTALLED</span>`;
        if (prevTeamBreakupFilesEl) prevTeamBreakupFilesEl.innerHTML = `<span style="font-size:8px;font-weight:900;color:#93c5fd;letter-spacing:0.2px;line-height:1;white-space:nowrap">${match[2]} SUBMITTED</span>`;
      } else {
        const singleMatch = filesVal.match(/^(\d+)/);
        if (singleMatch) {
          prevFilesEl.innerHTML = `<span style="display:inline-flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#f59e0b,#eab308);color:#0f172a;font-weight:950;font-size:9.5px;padding:2px 6px;border-radius:4px;line-height:1;white-space:nowrap">${singleMatch[1]} FILES</span>`;
          if (prevTeamBreakupFilesEl) prevTeamBreakupFilesEl.innerHTML = `<span style="font-size:8px;font-weight:900;color:#93c5fd;letter-spacing:0.2px;line-height:1;white-space:nowrap">${singleMatch[1]} SUBMITTED</span>`;
        } else {
          prevFilesEl.textContent = filesVal;
          if (prevTeamBreakupFilesEl) prevTeamBreakupFilesEl.innerHTML = '';
        }
      }
    }

    const prevTotalTodayEl = document.getElementById('prevTotalToday');
    if (prevTotalTodayEl) prevTotalTodayEl.textContent = getVal('postTotalToday');

    const overallValStr = getVal('postOverall').toUpperCase().trim();
    const prevOverallLabelEl = document.getElementById('prevOverallLabel');
    if (prevOverallLabelEl) {
      if (overallValStr.includes('LEAD')) {
        prevOverallLabelEl.textContent = '👥 DIRECT LEADS';
      } else {
        prevOverallLabelEl.textContent = '👥 TEAM SIZE';
      }
    }

    setTxt('prevOverall', getVal('postOverall'));
    setTxt('prevTeamBreakup', getVal('postTeamBreakup'));
    setTxt('prevPotential', getVal('postPotential'));
    setTxt('prevCustomer', getVal('postCustomer').toUpperCase());
    setTxt('prevLocation', getVal('postLocation').toUpperCase());

    let rawSeniorName = getVal('postSeniorName').trim().toUpperCase();
    if (rawSeniorName) {
      rawSeniorName = rawSeniorName.replace(/^SENIOR\s*:\s*/i, '').replace(/^DIRECT SPONSOR\s*:\s*/i, '').trim();
      rawSeniorName = 'Direct Sponsor : ' + rawSeniorName;
    }
    setTxt('prevSeniorName', rawSeniorName || 'Direct Sponsor : —');
    setTxt('prevSeniorToday', getVal('postSeniorToday'));
    setTxt('prevSeniorEarning', getVal('postSeniorEarning'));
    setTxt('prevSeniorPotential', getVal('postSeniorPotential'));

    const showSenior = document.getElementById('postShowSenior')?.checked ?? true;
    const prevSeniorRow = document.getElementById('prevSeniorRow');
    if (prevSeniorRow) prevSeniorRow.style.display = showSenior ? 'flex' : 'none';

    const postTotalTodayInput = document.getElementById('postTotalToday');
    if (postTotalTodayInput && !postTotalTodayInput._hasUserEditListener) {
      postTotalTodayInput._hasUserEditListener = true;
      postTotalTodayInput.addEventListener('input', () => {
        window._postTotalTodayUserEdited = true;
        updatePoster();
      });
    }

    const postCustomerInput = document.getElementById('postCustomer');
    if (postCustomerInput && !postCustomerInput._hasUserEditListener) {
      postCustomerInput._hasUserEditListener = true;
      postCustomerInput.addEventListener('input', () => {
        window._postCustomerUserEdited = true;
        updatePoster();
      });
    }

    const postLocationInput = document.getElementById('postLocation');
    if (postLocationInput && !postLocationInput._hasUserEditListener) {
      postLocationInput._hasUserEditListener = true;
      postLocationInput.addEventListener('input', () => {
        window._postLocationUserEdited = true;
        updatePoster();
      });
    }

    if (!window._posterCustomTextEdited) {
      const tpl = document.getElementById('postShareTemplate')?.value || 'full';
      const txt = buildPosterShareText(tpl);
      const customTextEl = document.getElementById('postShareCustomText');
      if (customTextEl) customTextEl.value = txt;
    }
  }

  function changeThemePreset() {
    const preset = document.getElementById('postThemePreset')?.value || 'celebration_graphic';
    const canvas = document.getElementById('posterCanvasWrapper');
    if (!canvas) return;

    if (preset === 'celebration_graphic' || preset === 'dark_navy' || !preset) {
      canvas.style.backgroundImage = "none";
      canvas.style.background = "radial-gradient(circle at 50% 25%, #0f2347 0%, #061126 60%, #020610 100%)";
      canvas.style.border = "5px double #eab308";
    } else if (preset === 'light_cream') {
      canvas.style.background = "#FAF9F6";
      canvas.style.border = "5px double #d4af37";
    } else if (preset === 'emerald_success') {
      canvas.style.background = "#064e3b";
      canvas.style.border = "5px double #34d399";
    } else if (preset === 'royal_blue') {
      canvas.style.background = "#0f172a";
      canvas.style.border = "5px double #fbbf24";
    }
  }

  async function convertPosterImagesToDataURLs(container) {
    if (!container) return;
    const imgs = Array.from(container.querySelectorAll('img'));
    const tok = localStorage.getItem('access_token') || sessionStorage.getItem('access_token') || localStorage.getItem('staff_token') || sessionStorage.getItem('staff_token');
    const apiBase = (typeof API_BASE !== 'undefined') ? API_BASE : (typeof API !== 'undefined' ? API : '/api/v1');

    await Promise.all(imgs.map(async (img) => {
      try {
        const src = img.getAttribute('src') || img.src;
        if (!src || src.startsWith('data:')) return;

        let dataUrl = null;

        // Extract relative path from src
        let relPath = src;
        if (relPath.includes('/storage/')) {
          relPath = relPath.split('/storage/')[1];
        } else if (relPath.startsWith('http://') || relPath.startsWith('https://')) {
          try {
            const u = new URL(relPath);
            relPath = u.pathname.replace(/^\/storage\//, '').replace(/^\//, '');
          } catch(e){}
        } else if (relPath.startsWith('/')) {
          relPath = relPath.replace(/^\/storage\//, '').replace(/^\//, '');
        }
        if (relPath.includes('?')) relPath = relPath.split('?')[0];

        // Strategy 1: Fetch Base64 Data URL via backend API /vgk/storage/dataurl (bypasses CORS/S3 redirects)
        if (relPath && relPath.length > 3) {
          try {
            const endpoint = `${apiBase}/vgk/storage/dataurl?path=${encodeURIComponent(relPath)}`;
            const headers = {};
            if (tok) headers['Authorization'] = 'Bearer ' + tok;
            const res = await fetch(endpoint, { headers });
            if (res.ok) {
              const json = await res.json();
              if (json && json.success && json.data_url) {
                dataUrl = json.data_url;
              }
            }
          } catch (apiErr) {
            console.warn("[Poster DataURL API] Endpoint fetch failed for:", relPath, apiErr);
          }
        }

        // Strategy 2: Direct fetch blob fallback
        if (!dataUrl) {
          try {
            const fetchUrl = (src.startsWith('/') && !src.startsWith('//')) ? (window.location.origin + src) : src;
            const headers = {};
            if (tok) headers['Authorization'] = 'Bearer ' + tok;
            const res = await fetch(fetchUrl, { headers, mode: 'cors', credentials: 'omit' });
            if (res.ok) {
              const blob = await res.blob();
              dataUrl = await new Promise((resolve) => {
                const reader = new FileReader();
                reader.onloadend = () => resolve(reader.result);
                reader.onerror = () => resolve(null);
                reader.readAsDataURL(blob);
              });
            }
          } catch (fErr) {
            console.warn("[Poster DataURL] Fetch blob failed for:", src, fErr);
          }
        }

        // Strategy 3: Offscreen canvas drawing if fetch blob failed & image loaded
        if (!dataUrl && img.complete && img.naturalWidth > 0) {
          try {
            const cvs = document.createElement('canvas');
            cvs.width = img.naturalWidth;
            cvs.height = img.naturalHeight;
            const ctx = cvs.getContext('2d');
            ctx.drawImage(img, 0, 0);
            dataUrl = cvs.toDataURL('image/png');
          } catch (cErr) {
            console.warn("[Poster DataURL] Canvas draw failed for:", src, cErr);
          }
        }

        if (dataUrl && dataUrl.startsWith('data:')) {
          img.src = dataUrl;
          img.removeAttribute('crossorigin');
        }
      } catch (err) {
        console.warn("[Poster DataURL] Failed to convert img:", err);
      }
    }));
  }

  function safeToDataURL(canvas) {
    if (!canvas) return null;
    try {
      return canvas.toDataURL('image/png');
    } catch (err) {
      console.warn("[Poster export] safeToDataURL primary failed:", err);
      try {
        const cvs = document.createElement('canvas');
        cvs.width = canvas.width;
        cvs.height = canvas.height;
        const ctx = cvs.getContext('2d');
        ctx.drawImage(canvas, 0, 0);
        return cvs.toDataURL('image/png');
      } catch (err2) {
        console.error("[Poster export] safeToDataURL fallback failed:", err2);
        return null;
      }
    }
  }

  function safeToBlob(canvas, callback, type = 'image/png') {
    if (!canvas) { callback(null); return; }
    try {
      canvas.toBlob((blob) => {
        if (blob) {
          callback(blob);
        } else {
          const dUrl = safeToDataURL(canvas);
          if (dUrl) {
            fetch(dUrl).then(r => r.blob()).then(b => callback(b)).catch(() => callback(null));
          } else {
            callback(null);
          }
        }
      }, type);
    } catch (err) {
      console.warn("[Poster export] safeToBlob primary failed:", err);
      const dUrl = safeToDataURL(canvas);
      if (dUrl) {
        fetch(dUrl).then(r => r.blob()).then(b => callback(b)).catch(() => callback(null));
      } else {
        callback(null);
      }
    }
  }

  async function capturePosterCanvas(container) {
    if (!container) container = document.getElementById('posterCanvasWrapper');
    if (!container) return null;

    // Convert all img tags in poster DOM to Base64 Data URLs before html2canvas
    await convertPosterImagesToDataURLs(container);

    const w = container.scrollWidth || 480;
    const h = container.scrollHeight || 780;

    try {
      return await window.html2canvas(container, {
        useCORS: true,
        allowTaint: true,
        scale: 2,
        width: w,
        height: h,
        windowWidth: document.documentElement.clientWidth || 1920,
        windowHeight: document.documentElement.clientHeight || 1080,
        scrollX: 0,
        scrollY: 0,
        backgroundColor: null,
        onclone: (clonedDoc) => {
          const clonedEl = clonedDoc.getElementById('posterCanvasWrapper');
          if (clonedEl) {
            clonedEl.style.transform = 'none';
            clonedEl.style.overflow = 'visible';
            clonedEl.style.maxHeight = 'none';
            clonedEl.style.height = 'auto';
            clonedEl.style.margin = '0';
            clonedEl.style.paddingBottom = '22px';
            clonedEl.style.boxSizing = 'border-box';
          }
        }
      });
    } catch (err) {
      console.warn("capturePosterCanvas html2canvas warning:", err);
      return null;
    }
  }

  function buildPosterShareText(templateKey) {
    if (typeof window.buildPosterShareText === 'function' && window.buildPosterShareText !== buildPosterShareText) {
      return window.buildPosterShareText(templateKey);
    }
    const rawName = (document.getElementById('postSubtitle')?.value || document.getElementById('prevName')?.textContent || '').trim();
    const rawRank = (document.getElementById('postRank')?.value || document.getElementById('prevRank')?.textContent || '').trim();
    const partnerName = rawName || 'Channel Partner';
    const partnerRank = rawRank ? rawRank.replace(/[★*]/g, '').trim().toUpperCase() : '';
    const partnerOverall = (document.getElementById('postHighlight')?.value || document.getElementById('prevHighlight')?.textContent || '').trim();
    const partnerToday = (document.getElementById('prevTotalToday')?.textContent || document.getElementById('postTodayPayout')?.value || '').trim();
    const partnerPotential = (document.getElementById('postPotential')?.value || document.getElementById('prevPotential')?.textContent || '').trim();
    const breakupText = (document.getElementById('postTodayPayout')?.value || '').trim();
    const filesVal = (document.getElementById('postFiles')?.value || document.getElementById('prevFiles')?.textContent || '').trim();
    const teamVal = (document.getElementById('postOverall')?.value || document.getElementById('prevOverall')?.textContent || '').trim();

    let seniorName = (document.getElementById('postSeniorName')?.value || document.getElementById('prevSeniorName')?.textContent || '').replace(/^Direct Sponsor\s*:\s*/i, '').replace(/^Senior\s*:\s*/i, '').trim();
    const seniorToday = (document.getElementById('postSeniorToday')?.value || document.getElementById('prevSeniorToday')?.textContent || '').trim();
    const seniorOverall = (document.getElementById('postSeniorEarning')?.value || document.getElementById('prevSeniorEarning')?.textContent || '').trim();
    const prevSeniorPot = document.getElementById('prevSeniorPotential');
    const seniorPotential = prevSeniorPot ? prevSeniorPot.textContent.trim() : (document.getElementById('postSeniorPotential')?.value || '₹0/-');

    const showSeniorInput = document.getElementById('postShowSenior');
    const isSeniorVisible = showSeniorInput ? showSeniorInput.checked : (document.getElementById('prevSeniorRow')?.style.display !== 'none');

    const periodPayoutLabel = window._posterPeriodPayoutText || "Today's Payout";
    const periodEarningLabel = window._posterPeriodTitleText || "Today's Earning";

    const tpl = templateKey || document.getElementById('postShareTemplate')?.value || 'full';

    if (tpl === 'payout') {
      let t = `💰 *${periodPayoutLabel.toUpperCase()} RELEASED!* 💰\n\n`;
      t += `🎉 Congratulations to *${partnerName}*${partnerRank ? ' (' + partnerRank + ')' : ''}!\n\n`;
      if (partnerRank) t += `🏆 *Career Designation:* ${partnerRank}\n`;
      if (partnerToday) t += `💵 *${periodEarningLabel}:* ${partnerToday}\n`;
      if (breakupText && breakupText !== 'No Payouts for Selected Date') t += `📋 *Breakup:* ${breakupText}\n`;
      if (filesVal) t += `📂 *Files Status:* ${filesVal}\n`;
      if (partnerOverall) t += `📈 *Overall Earned:* ${partnerOverall}\n`;
      t += `\n🌟 Keep shining and reaching new heights with VGK4U!\n`;
      t += `🌐 https://vgk4u.com`;
      return t;
    }

    if (tpl === 'milestone') {
      let t = `🏆 *NEW MILESTONE ACHIEVED!* 🏆\n\n`;
      t += `🏆 Proud to celebrate *${partnerName}* — ${partnerRank || 'Channel Partner'}!\n\n`;
      if (partnerRank) t += `🏆 *Career Designation:* ${partnerRank}\n`;
      if (partnerOverall) t += `📈 *Total Career Earnings:* ${partnerOverall}\n`;
      if (teamVal) t += `👥 *Total Team Size:* ${teamVal}\n`;
      if (partnerPotential) t += `🔮 *Expected Potential:* ${partnerPotential}\n`;
      if (partnerToday) t += `💰 *${periodPayoutLabel}:* ${partnerToday}\n`;
      t += `\n🚀 VGK4U is empowering partners across India!\n`;
      t += `🌐 https://vgk4u.com\n`;
      t += `📲 Join the revolution today!`;
      return t;
    }

    if (tpl === 'short') {
      return `🎉 Big congratulations to *${partnerName}* (${partnerRank || 'Channel Partner'}) for earning *${partnerToday}* with VGK4U! 🚀 Overall: ${partnerOverall}. Proud of your achievement! 👏 https://vgk4u.com`;
    }

    let text = `🎉 *CONGRATULATIONS TO ${partnerName}!* 🎉\n\n`;
    if (partnerRank) {
      text += `🏆 *Career Designation:* ${partnerRank}\n\n`;
    }
    text += `👤 *Member Name:* ${partnerName}\n`;
    if (partnerToday) {
      text += `💰 *${periodPayoutLabel}:* ${partnerToday}\n`;
    }
    if (partnerOverall) {
      text += `📈 *Overall Earning:* ${partnerOverall}\n`;
    }
    if (partnerPotential) {
      text += `🔮 *Potential Valuation:* ${partnerPotential}\n`;
    }
    text += `\n`;

    if (isSeniorVisible && seniorName && seniorName !== '—' && seniorName !== 'NONE' && !seniorName.endsWith('—')) {
      text += `🙌 *Direct Sponsor:* ${seniorName}\n`;
      text += `💰 *Sponsor Today:* ${seniorToday} | *Overall:* ${seniorOverall}\n`;
      if (seniorPotential && seniorPotential !== '₹0/-') {
        text += `🔮 *Sponsor Potential:* ${seniorPotential}\n`;
      }
      text += `\n`;
    }

    text += `🌐 *Official Website:* https://vgk4u.com\n\n`;
    text += `🚀 *Join VGK4U today & grow your earnings!*`;

    return text;
  }

  function getPosterShareDetails() {
    const rawName = (document.getElementById('postSubtitle')?.value || document.getElementById('prevName')?.textContent || '').trim();
    const rawRank = (document.getElementById('postRank')?.value || document.getElementById('prevRank')?.textContent || '').trim();
    const partnerName = rawName || 'Channel Partner';
    const partnerRank = rawRank ? rawRank.replace(/[★*]/g, '').trim().toUpperCase() : '';
    const partnerOverall = (document.getElementById('postHighlight')?.value || document.getElementById('prevHighlight')?.textContent || '').trim();
    const partnerToday = (document.getElementById('prevTotalToday')?.textContent || document.getElementById('postTodayPayout')?.value || '').trim();
    const partnerPotential = (document.getElementById('postPotential')?.value || document.getElementById('prevPotential')?.textContent || '').trim();

    let seniorName = (document.getElementById('postSeniorName')?.value || document.getElementById('prevSeniorName')?.textContent || '').replace(/^Direct Sponsor\s*:\s*/i, '').replace(/^Senior\s*:\s*/i, '').trim();
    const seniorToday = (document.getElementById('postSeniorToday')?.value || document.getElementById('prevSeniorToday')?.textContent || '').trim();
    const seniorOverall = (document.getElementById('postSeniorEarning')?.value || document.getElementById('prevSeniorEarning')?.textContent || '').trim();
    const prevSeniorPot = document.getElementById('prevSeniorPotential');
    const seniorPotential = prevSeniorPot ? prevSeniorPot.textContent.trim() : (document.getElementById('postSeniorPotential')?.value || '₹0/-');

    const showSeniorInput = document.getElementById('postShowSenior');
    const isSeniorVisible = showSeniorInput ? showSeniorInput.checked : (document.getElementById('prevSeniorRow')?.style.display !== 'none');

    const customTextEl = document.getElementById('postShareCustomText');
    let text = (customTextEl && customTextEl.value.trim()) ? customTextEl.value.trim() : buildPosterShareText();

    return { partnerName, partnerRank, partnerOverall, partnerToday, partnerPotential, seniorName, seniorToday, seniorOverall, seniorPotential, isSeniorVisible, text };
  }

  async function resolvePosterImagePayload(container) {
    // 1. Priority: Uploaded custom creative
    let customImg = window._customUploadedCreativeImage || window._customUploadedPosterImage || null;
    if (customImg) {
      let blob = window._customUploadedCreativeBlob || null;
      if (!blob) {
        try {
          blob = await (await fetch(customImg)).blob();
        } catch (e) {
          console.warn('[Poster export] Custom creative blob error:', e);
        }
      }
      return { dataUrl: customImg, blob: blob, source: 'uploaded' };
    }

    // 2. Fallback: Auto-generated canvas poster
    if (!container) container = document.getElementById('posterCanvasWrapper');
    if (container) {
      try {
        const canvas = await capturePosterCanvas(container);
        if (canvas) {
          const dataUrl = safeToDataURL(canvas);
          let blob = null;
          try {
            if (dataUrl) blob = await (await fetch(dataUrl)).blob();
          } catch (e) {
            console.warn('[Poster export] Canvas blob conversion error:', e);
          }
          return { dataUrl: dataUrl, blob: blob, source: 'generated' };
        }
      } catch (err) {
        console.error('[Poster export] Poster canvas capture error:', err);
      }
    }

    return { dataUrl: null, blob: null, source: 'none' };
  }
  window.resolvePosterImagePayload = resolvePosterImagePayload;

  async function testShareToNumber() {
    const container = document.getElementById('posterCanvasWrapper');
    if (!container) return;

    const savedPhone = localStorage.getItem('last_test_wa_phone') || '';
    const phoneInput = prompt('📲 ENTER TEST WHATSAPP NUMBER:\n----------------------------------------\nEnter the WhatsApp mobile number to test default broadcast & poster image before sending to all groups/members:', savedPhone || '91');

    if (!phoneInput) return;
    let cleanPhone = phoneInput.replace(/\D/g, '');
    if (cleanPhone.length === 10) cleanPhone = '91' + cleanPhone;
    if (cleanPhone.length < 10) {
      alert('Please enter a valid 10-digit or 12-digit mobile number.');
      return;
    }

    localStorage.setItem('last_test_wa_phone', cleanPhone);

    const shareDetails = getPosterShareDetails();
    const partnerName = shareDetails.partnerName;
    const shareText = shareDetails.text;

    const spinner = document.getElementById('posterSpinner');
    if (spinner) {
      spinner.style.display = 'flex';
      const spText = spinner.querySelector('div div');
      if (spText) spText.textContent = 'Rendering and preparing poster image for test send...';
    }

    // Two-Tier Fallback: 1. Uploaded Custom Creative -> 2. Auto-Generated Canvas Poster
    const { dataUrl, source } = await resolvePosterImagePayload(container);

    if (spinner) spinner.style.display = 'none';

    try {
      const json = await sendIndividualWhatsAppApiFirst({
        phone: cleanPhone,
        imageUrl: dataUrl,
        message: shareText,
        recipientName: partnerName
      });
      if (json && json.success) {
        const attachDesc = dataUrl ? (source === 'uploaded' ? 'Uploaded Custom Creative 🖼️' : 'Auto-Generated Celebration Poster 🖼️') : 'Text Only (Default Message)';
        const channelDesc = json.delivery_label || (json.channel === 'meta_api' ? 'Official Meta WhatsApp Cloud API ✅' : 'Scanned WhatsApp Session (API Fallback) ✅');
        alert(`✅ TEST SHARE SENT SUCCESSFULLY!\n----------------------------------------\nRecipient: +91 ${cleanPhone.slice(-10)}\nChannel: ${channelDesc}\nAttachment: ${attachDesc}\n\nPlease check your WhatsApp on +91 ${cleanPhone.slice(-10)} to verify!`);
      } else {
        const errNotice = (json && json.error) || 'Both Official API and Scanned WhatsApp bot are unavailable';
        const useFallback = confirm(`⚠️ Automated WhatsApp Notice:\n${errNotice}\n\nWould you like to send directly via WhatsApp Web/App to +91 ${cleanPhone.slice(-10)} instead?`);
        if (useFallback) {
          const directUrl = `https://api.whatsapp.com/send?phone=91${cleanPhone.slice(-10)}&text=${encodeURIComponent(shareText)}`;
          window.open(directUrl, '_blank');
        }
      }
    } catch (err) {
      const useFallback = confirm(`⚠️ Background WhatsApp Service Unavailable.\n\nWould you like to send directly via WhatsApp Web/App to +91 ${cleanPhone.slice(-10)} instead?`);
      if (useFallback) {
        const directUrl = `https://api.whatsapp.com/send?phone=91${cleanPhone.slice(-10)}&text=${encodeURIComponent(shareText)}`;
        window.open(directUrl, '_blank');
      }
    }
  }

  function resetPosterShareText() {
    window._posterCustomTextEdited = false;
    const tpl = document.getElementById('postShareTemplate')?.value || 'full';
    const txt = buildPosterShareText(tpl);
    const customTextEl = document.getElementById('postShareCustomText');
    if (customTextEl) customTextEl.value = txt;
  }

  async function _ensurePngBlobForClipboard(blob, dataUrl) {
    if (blob && blob.type === 'image/png') return blob;
    const srcUrl = dataUrl || (blob ? URL.createObjectURL(blob) : null);
    if (!srcUrl) return null;
    return await new Promise((resolve) => {
      const img = new Image();
      img.crossOrigin = 'anonymous';
      img.onload = () => {
        try {
          const cvs = document.createElement('canvas');
          cvs.width = img.naturalWidth || img.width || 800;
          cvs.height = img.naturalHeight || img.height || 1000;
          const ctx = cvs.getContext('2d');
          ctx.drawImage(img, 0, 0);
          cvs.toBlob((pngBlob) => resolve(pngBlob || blob), 'image/png');
        } catch (e) {
          resolve(blob);
        }
      };
      img.onerror = () => resolve(blob);
      img.src = srcUrl;
    });
  }

  function _flashCopyButtonState(btnEl, successText, origHtml) {
    if (!btnEl) return;
    const prevHtml = origHtml || btnEl.innerHTML;
    btnEl.innerHTML = successText;
    btnEl.dataset.copying = '1';
    setTimeout(() => {
      if (btnEl) {
        btnEl.innerHTML = prevHtml;
        delete btnEl.dataset.copying;
      }
    }, 2200);
  }

  async function copyPosterImage(btnEl) {
    const container = document.getElementById('posterCanvasWrapper');
    const origHtml = btnEl ? btnEl.innerHTML : '';
    if (btnEl) btnEl.innerHTML = '⏳ Copying...';
    const spinner = document.getElementById('posterSpinner');
    if (spinner) {
      spinner.style.display = 'flex';
      const spText = spinner.querySelector('div div');
      if (spText) spText.textContent = 'Preparing poster image for clipboard...';
    }
    try {
      const { dataUrl, blob } = await resolvePosterImagePayload(container);
      if (spinner) spinner.style.display = 'none';
      if (!dataUrl && !blob) {
        if (btnEl) btnEl.innerHTML = origHtml;
        alert('Failed to generate poster image to copy.');
        return;
      }
      const pngBlob = await _ensurePngBlobForClipboard(blob, dataUrl);
      if (pngBlob && navigator.clipboard && window.ClipboardItem) {
        await navigator.clipboard.write([new ClipboardItem({ 'image/png': pngBlob })]);
        _flashCopyButtonState(btnEl, '✅ Image Copied!', origHtml);
      } else {
        if (btnEl) btnEl.innerHTML = origHtml;
        alert('Your browser does not support direct image clipboard copy. Please use Download Image instead.');
      }
    } catch (err) {
      if (spinner) spinner.style.display = 'none';
      if (btnEl) btnEl.innerHTML = origHtml;
      console.error('[Poster Copy Image] Error:', err);
      alert('Could not copy image to clipboard: ' + (err.message || 'Clipboard permission denied'));
    }
  }

  async function copyPosterText(btnEl) {
    const origHtml = btnEl ? btnEl.innerHTML : '';
    try {
      const shareDetails = getPosterShareDetails();
      const textToCopy = (shareDetails && shareDetails.text) ? shareDetails.text : buildPosterShareText();
      if (!textToCopy) {
        alert('No share text available to copy.');
        return;
      }
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(textToCopy);
      } else {
        const ta = document.createElement('textarea');
        ta.value = textToCopy;
        ta.style.position = 'fixed';
        ta.style.opacity = '0';
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
      }
      _flashCopyButtonState(btnEl, '✅ Text Copied!', origHtml);
    } catch (err) {
      if (btnEl) btnEl.innerHTML = origHtml;
      alert('Failed to copy text: ' + (err.message || err));
    }
  }

  async function sendIndividualWhatsAppApiFirst({ phone, message, imageUrl, recipientName }) {
    const cleanPhone = String(phone || '').replace(/\D/g, '');
    if (!cleanPhone) {
      return { success: false, error: 'Missing phone number' };
    }
    const apiBase = (typeof API_BASE !== 'undefined') ? API_BASE : (typeof API !== 'undefined' ? API : '/api/v1');
    const tok = localStorage.getItem('staff_token') || localStorage.getItem('access_token') || sessionStorage.getItem('staff_token') || sessionStorage.getItem('access_token') || '';
    try {
      const controller = new AbortController();
      const tid = setTimeout(() => controller.abort(), 18000);
      const res = await fetch(`${apiBase}/whatsapp/send-individual-api-first`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(tok ? { 'Authorization': 'Bearer ' + tok } : {})
        },
        body: JSON.stringify({
          phone: cleanPhone,
          message: message || '',
          imageUrl: imageUrl || null,
          recipient_name: recipientName || null
        }),
        signal: controller.signal
      });
      clearTimeout(tid);
      const data = await res.json();
      if (data && (data.success || data.blocked)) {
        return data;
      }
      // Client-side safety fallback to Scanned WA if backend route returned unexpected error
      const fbRes = await fetch('/api/send-message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone: cleanPhone, imageUrl: imageUrl || null, message: message || '' })
      });
      const fbJson = await fbRes.json();
      if (fbJson && fbJson.success) {
        return {
          success: true,
          channel: 'scanned_fallback',
          delivery_label: 'Delivered via Scanned WA (API Fallback) ✅',
          api_attempted: true
        };
      }
      return data || fbJson || { success: false, error: 'Delivery failed' };
    } catch (err) {
      try {
        const fbRes = await fetch('/api/send-message', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ phone: cleanPhone, imageUrl: imageUrl || null, message: message || '' })
        });
        const fbJson = await fbRes.json();
        if (fbJson && fbJson.success) {
          return {
            success: true,
            channel: 'scanned_fallback',
            delivery_label: 'Delivered via Scanned WA (API Fallback) ✅',
            api_attempted: true
          };
        }
        return fbJson;
      } catch (fbErr) {
        return { success: false, error: fbErr.message || err.message || 'WhatsApp service unreachable' };
      }
    }
  }

  async function downloadPoster() {
    const container = document.getElementById('posterCanvasWrapper');
    const partnerName = (document.getElementById('postSubtitle')?.value || document.getElementById('prevName')?.textContent || 'Channel_Partner').trim();
    const spinner = document.getElementById('posterSpinner');
    if (spinner) spinner.style.display = 'flex';

    try {
      const { dataUrl, source } = await resolvePosterImagePayload(container);
      if (spinner) spinner.style.display = 'none';
      if (!dataUrl) { alert('Failed to generate poster download image.'); return; }
      const fileSuffix = (source === 'uploaded') ? 'Custom_Creative.png' : 'Achievement_Poster.png';
      const link = document.createElement('a');
      link.download = `${partnerName.replace(/\s+/g, '_')}_${fileSuffix}`;
      link.href = dataUrl;
      link.click();
    } catch (err) {
      if (spinner) spinner.style.display = 'none';
      alert('Failed to download image: ' + err.message);
    }
  }

  async function sharePoster() {
    const container = document.getElementById('posterCanvasWrapper');
    const partnerName = (document.getElementById('postSubtitle')?.value || document.getElementById('prevName')?.textContent || 'Partner').trim();
    const totalPayout = document.getElementById('prevTotalToday')?.textContent?.trim() || '';
    const spinner = document.getElementById('posterSpinner');
    if (spinner) spinner.style.display = 'flex';

    try {
      const { dataUrl, blob, source } = await resolvePosterImagePayload(container);
      if (spinner) spinner.style.display = 'none';
      if (!blob) { alert('Failed to generate image file.'); return; }
      const fileSuffix = (source === 'uploaded') ? 'Custom_Creative.png' : 'Achievement.png';
      const file = new File([blob], `${partnerName.replace(/\s+/g, '_')}_${fileSuffix}`, { type: blob.type || 'image/png' });
      if (navigator.canShare && navigator.canShare({ files: [file] })) {
        navigator.share({ title: 'VGK4U Celebration Poster', text: `Congratulations to ${partnerName} for earning ${totalPayout}!`, files: [file] }).catch(err => {
          if (err.name !== 'AbortError') alert('Sharing failed: ' + err.message);
        });
      } else {
        const a = document.createElement('a');
        a.download = `${partnerName.replace(/\s+/g, '_')}_${fileSuffix}`;
        a.href = URL.createObjectURL(blob);
        a.click();
      }
    } catch (err) {
      if (spinner) spinner.style.display = 'none';
      alert('Failed to generate sharing image: ' + err.message);
    }
  }

  async function shareOnWhatsApp() {
    const container = document.getElementById('posterCanvasWrapper');
    const shareDetails = getPosterShareDetails();
    const partnerName = shareDetails.partnerName;
    const text = shareDetails.text;

    // Open the window immediately to bypass browser popup blockers
    const shareWindow = window.open('', '_blank');
    if (shareWindow) {
      shareWindow.document.write('<html><head><title>Loading WhatsApp...</title><style>body{font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;background:#f3f4f6;color:#374151;} .loader{border:4px solid #e5e7eb;border-top:4px solid #25d366;border-radius:50%;width:40px;height:40px;animation:spin 1s linear infinite;margin-bottom:16px;} @keyframes spin{0%{transform:rotate(0deg);}100%{transform:rotate(360deg);}}</style></head><body><div style="text-align:center"><div class="loader" style="margin:0 auto 16px;"></div><div>Preparing your WhatsApp share & download... Please wait.</div></div></body></html>');
    }

    const spinner = document.getElementById('posterSpinner');
    if (spinner) {
      spinner.style.display = 'flex';
      const spText = spinner.querySelector('div div');
      if (spText) spText.textContent = 'Preparing WhatsApp share & poster...';
    }

    const { dataUrl, blob, source } = await resolvePosterImagePayload(container);

    if (spinner) spinner.style.display = 'none';

    if (dataUrl) {
      try {
        const link = document.createElement('a');
        link.download = `${partnerName.replace(/\s+/g, '_')}_Achievement_Poster.png`;
        link.href = dataUrl;
        link.click();
      } catch (e) {}
    }

    if (blob && navigator.clipboard && window.ClipboardItem) {
      try {
        await navigator.clipboard.write([new ClipboardItem({ [blob.type || 'image/png']: blob })]);
        alert('Poster image downloaded and copied to clipboard! You can paste (Cmd+V / Ctrl+V) the image directly inside the WhatsApp chat.');
      } catch (e) {}
    }

    const url = `https://api.whatsapp.com/send?text=${encodeURIComponent(text)}`;
    if (shareWindow) shareWindow.location.href = url;
    else window.open(url, '_blank');
  }

  async function shareDefaultChannel() {
    if (window._isDefaultSharingInProgress) {
      console.warn('[POSTER-SHARE] Share dispatch already in progress. Ignoring duplicate click.');
      return;
    }
    window._isDefaultSharingInProgress = true;
    console.log('[MYNTOS SHARE DEBUG] 1. shareDefaultChannel triggered');
    const container = document.getElementById('posterCanvasWrapper');
    if (!container) {
      window._isDefaultSharingInProgress = false;
      console.warn('[MYNTOS SHARE DEBUG] posterCanvasWrapper not found');
      return;
    }

    const shareDetails = getPosterShareDetails();
    const partnerName = shareDetails.partnerName;
    const shareText = shareDetails.text;
    const seniorName = shareDetails.seniorName;
    const isSeniorVisible = shareDetails.isSeniorVisible;

    const m = window._currentPosterMember || {};
    const isMemberBlocked = Boolean(m.is_blocked || m.member_status === 'BLOCKED');
    const isSeniorBlocked = Boolean(m.senior_is_blocked || m.senior_member_status === 'BLOCKED');
    const mPhone = (m.phone || '').replace(/\D/g, '');
    const sPhone = isSeniorVisible ? (m.senior_phone || '').replace(/\D/g, '') : '';

    console.log('[MYNTOS SHARE DEBUG] 2. Prepared share details:', { partnerName, seniorName, mPhone, sPhone, isSeniorVisible, isMemberBlocked, isSeniorBlocked });

    const dispatchTargets = [
      { id: 'member', type: 'member', label: `Member: ${partnerName}`, target: isMemberBlocked ? 'Blocked Partner (Excluded)' : (mPhone ? `+91 ${mPhone.slice(-10)}` : 'No Phone'), phone: mPhone, status: isMemberBlocked ? 'skipped' : (mPhone ? 'sending' : 'skipped'), msg: isMemberBlocked ? 'Suppressed (Blocked Partner)' : (mPhone ? 'Broadcasting...' : 'No Phone') },
      { id: 'senior', type: 'member', label: `Senior: ${seniorName || 'Referrer'}`, target: !isSeniorVisible ? 'Excluded (Show Senior unchecked)' : (isSeniorBlocked ? 'Blocked Senior (Excluded)' : (sPhone ? `+91 ${sPhone.slice(-10)}` : 'No Phone')), phone: sPhone, status: isSeniorVisible ? (isSeniorBlocked ? 'skipped' : (sPhone ? 'sending' : 'skipped')) : 'skipped', msg: !isSeniorVisible ? 'Excluded by toggle' : (isSeniorBlocked ? 'Suppressed (Blocked Senior)' : (sPhone ? 'Broadcasting...' : 'No Senior Phone')) },
      { id: 'admin_copy', type: 'member', label: 'Admin Copy (+91 8875551666)', target: '+91 8875551666', phone: '8875551666', status: 'sending', msg: 'Broadcasting Admin Copy...' },
      { id: 'channel_official', type: 'group', label: 'VGK4U Official Channel', target: 'whatsapp.com/channel/0029Vb7Vb5f9cDDXf3zWtf0m', inviteCode: '0029Vb7Vb5f9cDDXf3zWtf0m', status: 'sending', msg: 'Broadcasting to channel...' },
      { id: 'group_main', type: 'group', label: 'VGK Community Group', target: 'chat.whatsapp.com/HNQQoKXFfCm5PQngGdrlcY', inviteCode: 'HNQQoKXFfCm5PQngGdrlcY', status: 'sending', msg: 'Broadcasting to group...' },
      { id: 'group_exec', type: 'group', label: 'Executive Announcements', target: 'chat.whatsapp.com/LfX8mGootXa7SpwNIz7P5C', inviteCode: 'LfX8mGootXa7SpwNIz7P5C', status: 'sending', msg: 'Broadcasting to group...' },
      { id: 'group_ev_stars', type: 'group', label: 'Ev scooty. MNR (royal ev ) stars', target: 'Ev scooty. MNR (royal ev ) stars', groupName: 'Ev scooty. MNR (royal ev ) stars', status: 'sending', msg: 'Broadcasting to group...' },
      { id: 'group_mnr_gen', type: 'group', label: 'MNR General Group', target: 'MNR General Group', groupName: 'MNR General Group', status: 'sending', msg: 'Broadcasting to group...' },
      { id: 'group_vgk_vjd', type: 'group', label: 'VGK4U - Vijayawada', target: 'VGK4U - Vijayawada', groupName: 'VGK4U - Vijayawada', status: 'sending', msg: 'Broadcasting to group...' },
      { id: 'group_vgk_gen', type: 'group', label: 'VGK4U General', target: 'VGK4U General', groupName: 'VGK4U General', status: 'sending', msg: 'Broadcasting to group...' },
      { id: 'portal_shoutout', type: 'portal', label: 'VGK4U Login Page Shoutout', target: 'vgk4u.com (Login Banner)', status: 'sending', msg: 'Publishing shoutout...' }
    ];

    const spinner = document.getElementById('posterSpinner');
    if (spinner) {
      spinner.style.display = 'flex';
      const spText = spinner.querySelector('div div');
      if (spText) spText.textContent = 'Rendering and preparing poster broadcast...';
    }

    // Two-Tier Fallback: 1. Uploaded Custom Creative -> 2. Auto-Generated Canvas Poster
    const { dataUrl, blob, source } = await resolvePosterImagePayload(container);

    if (spinner) spinner.style.display = 'none';

    // Show Live Broadcast Status Modal IMMEDIATELY
    console.log('[MYNTOS SHARE DEBUG] 3. Opening Live Dispatch Status Modal immediately');
    showLiveDispatchStatusModal(dispatchTargets, partnerName);

    const fetchWithTimeout = async (url, opts = {}, ms = 10000) => {
      const controller = new AbortController();
      const tid = setTimeout(() => controller.abort(), ms);
      try {
        const r = await fetch(url, { ...opts, signal: controller.signal });
        clearTimeout(tid);
        return r;
      } catch (e) {
        clearTimeout(tid);
        throw e;
      }
    };

    try {
      // 1. Submit Portal Shoutout
      try {
        const formData = new FormData();
        formData.append('title', `🎉 Achievement Poster: ${partnerName}`);
        formData.append('description', shareText);
        formData.append('category_id', '1');
        formData.append('submission_type', 'photo');
        if (blob) {
          formData.append('files', blob, `${partnerName.replace(/\s+/g, '_')}_Achievement.png`);
        }

        const tok = localStorage.getItem('staff_token') || localStorage.getItem('access_token') || sessionStorage.getItem('staff_token') || sessionStorage.getItem('access_token');
        const apiBase = (typeof API_BASE !== 'undefined') ? API_BASE : (typeof API !== 'undefined' ? API : '/api/v1');
        
        const res = await fetch(`${apiBase}/feedback/submit-staff-announcement`, {
          method: 'POST',
          headers: { 'Authorization': 'Bearer ' + tok },
          body: formData
        });
        const d = await res.json();
        if (d && d.duplicate) {
          updateDispatchStatus('portal_shoutout', 'skipped', 'STOPPED ⏸️ Already Posted Today');
        } else {
          updateDispatchStatus('portal_shoutout', 'sent', 'Published on Login Page');
        }
      } catch (pErr) {
        updateDispatchStatus('portal_shoutout', 'error', pErr.message || 'Portal Submit Error');
      }

      // 2. Member Direct Send (Official API First -> Scanned WA Fallback)
      if (isMemberBlocked) {
        updateDispatchStatus('member', 'skipped', 'Suppressed (Blocked Channel Partner)');
      } else if (mPhone) {
        try {
          const json = await sendIndividualWhatsAppApiFirst({
            phone: mPhone,
            imageUrl: dataUrl,
            message: shareText,
            recipientName: partnerName
          });
          if (json && json.success) {
            updateDispatchStatus('member', 'sent', json.delivery_label || 'Delivered via Official API (Text) ✅');
          } else if (json && json.blocked) {
            updateDispatchStatus('member', 'skipped', 'Suppressed (Blocked Channel Partner)');
          } else {
            updateDispatchStatus('member', 'error', (json && json.error) || 'Delivery Failed');
          }
        } catch (mErr) {
          updateDispatchStatus('member', 'error', 'WhatsApp Service Unreachable');
        }
      } else {
        updateDispatchStatus('member', 'skipped', 'No Phone Number');
      }

      // 3. Senior Direct Send (Official API First -> Scanned WA Fallback)
      if (!isSeniorVisible) {
        updateDispatchStatus('senior', 'skipped', 'Excluded by toggle');
      } else if (isSeniorBlocked) {
        updateDispatchStatus('senior', 'skipped', 'Suppressed (Blocked Senior Partner)');
      } else if (sPhone) {
        try {
          const json = await sendIndividualWhatsAppApiFirst({
            phone: sPhone,
            imageUrl: dataUrl,
            message: shareText,
            recipientName: seniorName || 'Direct Sponsor'
          });
          if (json && json.success) {
            updateDispatchStatus('senior', 'sent', json.delivery_label || 'Delivered via Official API (Text) ✅');
          } else if (json && json.blocked) {
            updateDispatchStatus('senior', 'skipped', 'Suppressed (Blocked Senior Partner)');
          } else {
            updateDispatchStatus('senior', 'error', (json && json.error) || 'Delivery Failed');
          }
        } catch (sErr) {
          updateDispatchStatus('senior', 'error', 'WhatsApp Service Unreachable');
        }
      } else {
        updateDispatchStatus('senior', 'skipped', 'No Senior Phone');
      }

      // 3b. Mandatory Admin Copy (+91 8875551666) Direct Send (Official API First -> Scanned WA Fallback)
      try {
        const jsonAdmin = await sendIndividualWhatsAppApiFirst({
          phone: '8875551666',
          imageUrl: dataUrl,
          message: shareText,
          recipientName: 'Admin Copy (+91 8875551666)'
        });
        if (jsonAdmin && jsonAdmin.success) {
          updateDispatchStatus('admin_copy', 'sent', jsonAdmin.delivery_label || (jsonAdmin.channel === 'meta_api' ? 'Delivered via Official API (Text) ✅' : 'Delivered via Scanned WA (API Fallback) ✅'));
        } else {
          updateDispatchStatus('admin_copy', 'error', (jsonAdmin && jsonAdmin.error) || 'Admin Copy Send Error');
        }
      } catch (adErr) {
        updateDispatchStatus('admin_copy', 'error', 'WhatsApp Service Unreachable');
      }

      // 4. VGK4U Official Channel Send
      try {
        const res = await fetchWithTimeout('/api/send-group-message', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ imageUrl: dataUrl, message: shareText, inviteCode: '0029Vb7Vb5f9cDDXf3zWtf0m' })
        });
        const json = await res.json();
        if (json.success) {
          updateDispatchStatus('channel_official', 'sent', 'Delivered to Official Channel');
        } else {
          updateDispatchStatus('channel_official', 'error', json.error || 'Channel Send Error');
        }
      } catch (cErr) {
        updateDispatchStatus('channel_official', 'error', 'WhatsApp Bot Offline');
      }

      // 5. Main Community Group Send
      try {
        const res = await fetchWithTimeout('/api/send-group-message', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ imageUrl: dataUrl, message: shareText, inviteCode: 'HNQQoKXFfCm5PQngGdrlcY' })
        });
        const json = await res.json();
        if (json.success) {
          updateDispatchStatus('group_main', 'sent', 'Delivered to Group');
        } else {
          updateDispatchStatus('group_main', 'error', json.error || 'Group Send Error');
        }
      } catch (gErr) {
        updateDispatchStatus('group_main', 'error', 'WhatsApp Bot Offline');
      }

      // 6. Exec Group Send
      try {
        const res = await fetchWithTimeout('/api/send-group-message', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ imageUrl: dataUrl, message: shareText, inviteCode: 'LfX8mGootXa7SpwNIz7P5C' })
        });
        const json = await res.json();
        if (json.success) {
          updateDispatchStatus('group_exec', 'sent', 'Delivered to Group');
        } else {
          updateDispatchStatus('group_exec', 'error', json.error || 'Group Send Error');
        }
      } catch (gErr) {
        updateDispatchStatus('group_exec', 'error', 'WhatsApp Bot Offline');
      }

      // 7. EV Scooty MNR Stars Group Send
      try {
        const res = await fetchWithTimeout('/api/send-group-message', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ imageUrl: dataUrl, message: shareText, groupId: '120363405554009428@g.us', groupName: 'Ev scooty. MNR (royal ev ) stars' })
        });
        const json = await res.json();
        if (json.success) {
          updateDispatchStatus('group_ev_stars', 'sent', 'Delivered to EV Stars Group');
        } else {
          updateDispatchStatus('group_ev_stars', 'error', json.error || 'Group Send Error');
        }
      } catch (gErr) {
        updateDispatchStatus('group_ev_stars', 'error', 'WhatsApp Bot Offline');
      }

      // 8. MNR General Group Send
      try {
        const res = await fetchWithTimeout('/api/send-group-message', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ imageUrl: dataUrl, message: shareText, groupId: '120363423048458227@g.us', groupName: 'MNR General Group' })
        });
        const json = await res.json();
        if (json.success) {
          updateDispatchStatus('group_mnr_gen', 'sent', 'Delivered to MNR General Group');
        } else {
          updateDispatchStatus('group_mnr_gen', 'error', json.error || 'Group Send Error');
        }
      } catch (gErr) {
        updateDispatchStatus('group_mnr_gen', 'error', 'WhatsApp Bot Offline');
      }

      // 9. VGK4U - Vijayawada Group Send
      try {
        const res = await fetchWithTimeout('/api/send-group-message', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ imageUrl: dataUrl, message: shareText, groupName: 'VGK4U - Vijayawada' })
        });
        const json = await res.json();
        if (json.success) {
          updateDispatchStatus('group_vgk_vjd', 'sent', 'Delivered to Vijayawada Group');
        } else {
          updateDispatchStatus('group_vgk_vjd', 'error', json.error || 'Group Send Error');
        }
      } catch (gErr) {
        updateDispatchStatus('group_vgk_vjd', 'error', 'WhatsApp Bot Offline');
      }

      // 10. VGK4U General Group Send
      try {
        const res = await fetchWithTimeout('/api/send-group-message', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ imageUrl: dataUrl, message: shareText, groupName: 'VGK4U General' })
        });
        const json = await res.json();
        if (json.success) {
          updateDispatchStatus('group_vgk_gen', 'sent', 'Delivered to VGK4U General Group');
        } else {
          updateDispatchStatus('group_vgk_gen', 'error', json.error || 'Group Send Error');
        }
      } catch (genErr) {
        updateDispatchStatus('group_vgk_gen', 'error', 'WhatsApp Bot Offline');
      }

    } catch (err) {
      if (spinner) spinner.style.display = 'none';
      console.warn("Share default dispatch error:", err);
      dispatchTargets.forEach(t => updateDispatchStatus(t.id, 'error', 'Dispatch Error'));
    } finally {
      if (spinner) spinner.style.display = 'none';
      setTimeout(() => {
        window._isDefaultSharingInProgress = false;
      }, 3000);
    }
  }

  async function postPosterAnnouncement() {
    if (window._isPosterAnnouncementSubmitting) {
      console.warn('[POSTER-ANNOUNCEMENT] Already submitting announcement, ignoring duplicate click.');
      return;
    }
    window._isPosterAnnouncementSubmitting = true;
    const container = document.getElementById('posterCanvasWrapper');
    if (!container) {
      window._isPosterAnnouncementSubmitting = false;
      if (typeof toast === 'function') toast('Poster preview not ready', 'error');
      else alert('Poster preview not ready');
      return;
    }

    const shareDetails = getPosterShareDetails();
    const partnerName = shareDetails.partnerName;
    const partnerOverall = shareDetails.partnerOverall;
    const partnerToday = shareDetails.partnerToday;

    if (!confirm(`📣 POST ANNOUNCEMENT ON LOGIN SCREEN\n--------------------------------------------------\n• Member Name: ${partnerName}\n• Today's Earning: ${partnerToday}\n• Overall Earning: ${partnerOverall}\n\nDo you want to publish this Achievement Poster announcement to the Login Screen slideshow now?`)) {
      return;
    }

    const spinner = document.getElementById('posterSpinner');
    if (spinner) spinner.style.display = 'flex';

    try {
      const { dataUrl, blob, source } = await resolvePosterImagePayload(container);
      if (!blob) throw new Error('Failed to resolve poster image payload');

      const fileSuffix = (source === 'uploaded') ? 'Custom_Creative.png' : 'Achievement.png';
      const shareText = shareDetails.text;

      const formData = new FormData();
      formData.append('title', `🎉 Achievement Poster: ${partnerName}`);
      formData.append('description', shareText);
      formData.append('category_id', '1');
      formData.append('submission_type', 'photo');
      formData.append('files', blob, `${partnerName.replace(/\s+/g, '_')}_${fileSuffix}`);

      const tok = localStorage.getItem('staff_token') || localStorage.getItem('access_token') || sessionStorage.getItem('staff_token') || sessionStorage.getItem('access_token');
      const apiBase = (typeof API_BASE !== 'undefined') ? API_BASE : (typeof API !== 'undefined' ? API : '/api/v1');

      const r = await fetch(`${apiBase}/feedback/staff/submit`, {
        method: 'POST',
        headers: { 'Authorization': 'Bearer ' + tok },
        body: formData
      });
      const d = await r.json();

      if (spinner) spinner.style.display = 'none';

      if (!r.ok || (!d.success && d.status !== 'success')) {
        throw new Error(d.detail || d.message || 'Failed to submit announcement');
      }

      if (d && d.duplicate) {
        alert(`⏸️ ANNOUNCEMENT ALREADY POSTED TODAY!\n--------------------------------------------------\nMember: ${partnerName}\nAnnouncement is already published and live on the login screen slideshow!`);
        if (typeof toast === 'function') toast('⏸️ Announcement already live on login page today', 'info');
      } else {
        alert(`✅ ANNOUNCEMENT POSTED SUCCESSFULLY!\n--------------------------------------------------\nMember: ${partnerName}\nAchievement poster announcement is now live on the login screen slideshow!`);
        if (typeof toast === 'function') toast('✅ Announcement published to login screen!', 'success');
      }
    } catch (err) {
      if (spinner) spinner.style.display = 'none';
      console.error('Post Announcement error:', err);
      alert('Failed to post announcement: ' + err.message);
    } finally {
      if (spinner) spinner.style.display = 'none';
      setTimeout(() => {
        window._isPosterAnnouncementSubmitting = false;
      }, 3000);
    }
  }

  function showLiveDispatchStatusModal(targets, partnerName) {
    const existing = document.getElementById('liveDispatchModal');
    if (existing) existing.remove();

    window._dispatchTargets = targets;

    function renderRows(type) {
      return targets.filter(t => t.type === type).map(t => {
        let badgeStyle = 'background:#f3f4f6;color:#6b7280';
        let badgeText = 'PENDING';
        let icon = '<i class="fas fa-spinner fa-spin text-primary"></i>';

        if (t.status === 'sent') {
          badgeStyle = 'background:#d1fae5;color:#065f46';
          badgeText = 'SENT ✅';
          icon = '<i class="fas fa-check-circle text-success" style="font-size:16px"></i>';
        } else if (t.status === 'error') {
          badgeStyle = 'background:#fee2e2;color:#991b1b';
          badgeText = 'FAILED ❌';
          icon = '<i class="fas fa-times-circle text-danger" style="font-size:16px"></i>';
        } else if (t.status === 'skipped') {
          badgeStyle = 'background:#f3f4f6;color:#9ca3af';
          badgeText = 'SKIPPED';
          icon = '<i class="fas fa-minus-circle text-muted" style="font-size:16px"></i>';
        } else if (t.status === 'sending') {
          badgeStyle = 'background:#e0e7ff;color:#3730a3';
          badgeText = 'SENDING...';
        }

        return `
          <div id="dispRow_${t.id}" style="display:flex;align-items:center;justify-content:space-between;padding:10px 12px;background:#f9fafb;border-radius:10px;border:1px solid #e5e7eb;margin-bottom:8px">
            <div style="display:flex;align-items:center;gap:10px;min-width:0">
              <div style="flex-shrink:0">${icon}</div>
              <div style="min-width:0">
                <div style="font-size:13px;font-weight:700;color:#111827;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${t.label}</div>
                <div style="font-size:11px;color:#6b7280;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${t.target}</div>
              </div>
            </div>
            <div style="text-align:right;flex-shrink:0;margin-left:12px">
              <span style="font-size:10.5px;font-weight:800;padding:3px 8px;border-radius:12px;letter-spacing:0.3px;${badgeStyle}">${badgeText}</span>
              <div style="font-size:10px;color:#9ca3af;margin-top:2px">${t.msg || ''}</div>
            </div>
          </div>
        `;
      }).join('');
    }

    const html = `
<div id="liveDispatchModal" style="position:fixed;inset:0;z-index:100000;background:rgba(0,0,0,0.7);display:flex;align-items:center;justify-content:center;padding:16px">
  <div style="background:#fff;border-radius:18px;width:100%;max-width:480px;padding:24px;box-shadow:0 24px 60px rgba(0,0,0,0.35);position:relative">
    <button onclick="document.getElementById('liveDispatchModal').remove()" style="position:absolute;top:14px;right:14px;background:none;border:none;font-size:18px;color:#9ca3af;cursor:pointer">&times;</button>
    <div style="text-align:center;margin-bottom:18px">
      <div style="width:52px;height:52px;border-radius:50%;background:#d1fae5;color:#059669;display:inline-flex;align-items:center;justify-content:center;font-size:26px;margin-bottom:8px"><i class="fab fa-whatsapp"></i></div>
      <h5 style="margin:0;font-size:17.5px;font-weight:800;color:#111827">WhatsApp Dispatch Status</h5>
      <p style="margin:3px 0 0;font-size:12.5px;color:#6b7280">Broadcasting achievement poster to scanned WhatsApp & channels</p>
    </div>

    <div style="max-height:360px;overflow-y:auto;padding-right:4px">
      <div style="font-size:11px;font-weight:800;color:#4b5563;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:6px"><i class="fas fa-users me-1 text-primary"></i> Members & Direct Contacts</div>
      ${renderRows('member')}

      <div style="font-size:11px;font-weight:800;color:#4b5563;text-transform:uppercase;letter-spacing:0.5px;margin:12px 0 6px"><i class="fas fa-comments me-1 text-success"></i> Target WhatsApp Groups</div>
      ${renderRows('group')}

      <div style="font-size:11px;font-weight:800;color:#4b5563;text-transform:uppercase;letter-spacing:0.5px;margin:12px 0 6px"><i class="fas fa-globe me-1 text-info"></i> Website & Login Announcements</div>
      ${renderRows('portal')}
    </div>

    <div style="margin-top:18px;display:flex;gap:10px">
      <button onclick="document.getElementById('liveDispatchModal').remove()" style="flex:1;background:#4f46e5;color:#fff;border:none;padding:11px;border-radius:10px;font-size:13.5px;font-weight:700;cursor:pointer">Done</button>
    </div>
  </div>
</div>
    `;

    const div = document.createElement('div');
    div.innerHTML = html;
    document.body.appendChild(div.firstElementChild);
  }

  window.updateDispatchStatus = function(id, status, msg) {
    if (!window._dispatchTargets) return;
    const t = window._dispatchTargets.find(x => x.id === id);
    if (t) {
      t.status = status;
      t.msg = msg || '';
    }
    const modal = document.getElementById('liveDispatchModal');
    if (modal && window._dispatchTargets) {
      const partnerName = (document.getElementById('prevSubtitle')?.textContent || '').trim();
      showLiveDispatchStatusModal(window._dispatchTargets, partnerName);
    }
  };

  function handleMemberPhotoUpload(e) {
    let file = null;
    if (e && e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length) {
      file = e.dataTransfer.files[0];
    } else if (e && e.target && e.target.files && e.target.files.length) {
      file = e.target.files[0];
    } else if (e instanceof File) {
      file = e;
    }
    if (!file) return;
    const reader = new FileReader();
    reader.onload = function(evt) {
      const dataUrl = evt.target.result;
      const img = document.getElementById('prevImg');
      const avatar = document.getElementById('prevAvatar');
      if (img) {
        img.src = dataUrl;
        img.style.display = 'block';
        if (avatar) avatar.style.display = 'none';
      }
      const thumbImg = document.getElementById('postImageThumb');
      const thumbAvatar = document.getElementById('postImageThumbAvatar');
      if (thumbImg) {
        thumbImg.src = dataUrl;
        thumbImg.style.display = 'block';
        if (thumbAvatar) thumbAvatar.style.display = 'none';
      }
    };
    reader.readAsDataURL(file);
    if (e && e.target && 'value' in e.target) {
      e.target.value = '';
    }
  }

  function handleSeniorPhotoUpload(e) {
    const file = e && e.target && e.target.files && e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = function(evt) {
      const img = document.getElementById('prevSeniorImg');
      const avatar = document.getElementById('prevSeniorAvatar');
      if (img) {
        img.src = evt.target.result;
        img.style.display = 'block';
        if (avatar) avatar.style.display = 'none';
      }
    };
    reader.readAsDataURL(file);
    if (e && e.target && 'value' in e.target) {
      e.target.value = '';
    }
  }

  function _applyCoreCustomCreativeDataUrl(dataUrl, blob) {
    window._customUploadedCreativeImage = dataUrl;
    window._customUploadedPosterImage = dataUrl;
    window._customUploadedCreativeBlob = blob || null;

    const card = document.getElementById('customCreativeImgCard');
    const placeholder = document.getElementById('customCreativeEmptyPlaceholder');
    const previewImg = document.getElementById('customCreativeImg');
    const topBadge = document.getElementById('customCreativeTopBadge');
    const statusBadge = document.getElementById('customCreativeStatusBadge');
    const notice = document.getElementById('customCreativeNotice');

    if (previewImg) previewImg.src = dataUrl;
    if (card) card.style.display = 'block';
    if (placeholder) placeholder.style.display = 'none';
    if (topBadge) {
      topBadge.textContent = 'Ready for WhatsApp';
      topBadge.style.background = '#065f46';
      topBadge.style.color = '#34d399';
      topBadge.style.borderColor = '#059669';
    }
    if (statusBadge) {
      statusBadge.textContent = 'Creative Attached ✅';
      statusBadge.style.background = '#d1fae5';
      statusBadge.style.color = '#065f46';
    }
    if (notice) {
      notice.innerHTML = '✅ <strong>Custom creative attached!</strong> It will be sent on WhatsApp along with the message.';
      notice.style.color = '#065f46';
    }
  }

  function handleCustomCreativeUpload(e) {
    let file = null;
    if (e && e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length) {
      file = e.dataTransfer.files[0];
    } else if (e && e.target && e.target.files && e.target.files.length) {
      file = e.target.files[0];
    } else if (e instanceof File) {
      file = e;
    }
    if (!file) return;

    const isImgType = (file.type && file.type.toLowerCase().startsWith('image/')) ||
                      /\.(jpe?g|png|webp|gif|bmp|svg|avif|heic|heif)$/i.test(file.name || '');
    if (!isImgType) {
      alert('Please select a valid image file (JPG, PNG, WebP, etc.).');
      if (e && e.target && 'value' in e.target) e.target.value = '';
      return;
    }

    const spinner = document.getElementById('posterSpinner');
    if (spinner) spinner.style.display = 'flex';

    const reader = new FileReader();
    reader.onload = function(evt) {
      const rawDataUrl = evt.target.result;
      _applyCoreCustomCreativeDataUrl(rawDataUrl, file);

      const tempImg = new Image();
      tempImg.onload = function() {
        try {
          const maxDim = 1280;
          let w = tempImg.width || 800;
          let h = tempImg.height || 800;
          if (w > maxDim || h > maxDim) {
            if (w > h) {
              h = Math.round((h * maxDim) / w);
              w = maxDim;
            } else {
              w = Math.round((w * maxDim) / h);
              h = maxDim;
            }
          }
          const cvs = document.createElement('canvas');
          cvs.width = w;
          cvs.height = h;
          const ctx = cvs.getContext('2d');
          const isPng = (file.type && file.type.toLowerCase() === 'image/png') || /\.png$/i.test(file.name || '');
          if (!isPng) {
            ctx.fillStyle = '#ffffff';
            ctx.fillRect(0, 0, w, h);
          }
          ctx.drawImage(tempImg, 0, 0, w, h);

          const mimeType = isPng ? 'image/png' : 'image/jpeg';
          const quality = isPng ? undefined : 0.92;
          const dataUrl = cvs.toDataURL(mimeType, quality);

          cvs.toBlob(function(blob) {
            if (spinner) spinner.style.display = 'none';
            _applyCoreCustomCreativeDataUrl(dataUrl, blob || file);
          }, mimeType, quality);
        } catch (err) {
          if (spinner) spinner.style.display = 'none';
        }
      };
      tempImg.onerror = function() {
        if (spinner) spinner.style.display = 'none';
      };
      tempImg.src = rawDataUrl;
    };
    reader.onerror = function() {
      if (spinner) spinner.style.display = 'none';
      alert('Failed to read the selected image file.');
    };
    reader.readAsDataURL(file);
    if (e && e.target && 'value' in e.target) {
      e.target.value = '';
    }
  }

  function clearCustomCreativeImage() {
    window._customUploadedCreativeImage = null;
    window._customUploadedPosterImage = null;
    window._customUploadedCreativeBlob = null;

    const fileInput = document.getElementById('postCustomCreativeFile');
    if (fileInput) fileInput.value = '';
    const legacyInput = document.getElementById('postCustomImageFile');
    if (legacyInput) legacyInput.value = '';

    const card = document.getElementById('customCreativeImgCard');
    const placeholder = document.getElementById('customCreativeEmptyPlaceholder');
    const previewImg = document.getElementById('customCreativeImg');
    const topBadge = document.getElementById('customCreativeTopBadge');
    const statusBadge = document.getElementById('customCreativeStatusBadge');
    const notice = document.getElementById('customCreativeNotice');

    if (previewImg) previewImg.src = '';
    if (card) card.style.display = 'none';
    if (placeholder) placeholder.style.display = 'flex';
    if (topBadge) {
      topBadge.textContent = 'Optional Attachment';
      topBadge.style.background = '#1e293b';
      topBadge.style.color = '#9ca3af';
      topBadge.style.borderColor = '#334155';
    }
    if (statusBadge) {
      statusBadge.textContent = 'No Creative Attached';
      statusBadge.style.background = '#f3f4f6';
      statusBadge.style.color = '#6b7280';
    }
    if (notice) {
      notice.innerHTML = 'ℹ️ Auto-generated celebration poster will be dispatched with message (or upload custom creative to override).';
      notice.style.color = '#047857';
    }
  }

  // Export functions to global scope
  window.generateMemberPoster = generateMemberPoster;
  window.openAchievementPoster = generateMemberPoster;
  window.openPosterFromUnified = openPosterFromUnified;
  window.capturePosterCanvas = capturePosterCanvas;
  window.downloadPoster = downloadPoster;
  window.copyPosterImage = copyPosterImage;
  window.copyPosterText = copyPosterText;
  window.resetPosterShareText = resetPosterShareText;
  window.sendIndividualWhatsAppApiFirst = sendIndividualWhatsAppApiFirst;
  window.sharePoster = sharePoster;
  window.shareOnWhatsApp = shareOnWhatsApp;
  window.shareDefaultChannel = shareDefaultChannel;
  window._shareDefaultChannelCore = shareDefaultChannel;
  window.testShareToNumber = testShareToNumber;
  window._testShareToNumberCore = testShareToNumber;
  window.postPosterAnnouncement = window.openPostToPortalModal || postPosterAnnouncement;
  window._postPosterAnnouncementCore = postPosterAnnouncement;
  if (typeof showDirectWaShareDialog === 'function') {
    window.showDirectWaShareDialog = showDirectWaShareDialog;
  }
  window.changeThemePreset = changeThemePreset;
  window.setPosterPresetPeriod = setPosterPresetPeriod;
  window.recalculateTodayPayout = recalculateTodayPayout;
  window.changePayoutDateRange = changePayoutDateRange;
  window.updatePoster = updatePoster;
  window.handleMemberPhotoUpload = handleMemberPhotoUpload;
  window.handleSeniorPhotoUpload = handleSeniorPhotoUpload;
  window.handleCustomCreativeUpload = handleCustomCreativeUpload;
  window.handleCustomPosterImageUpload = handleCustomCreativeUpload;
  window.clearCustomCreativeImage = clearCustomCreativeImage;
  window.clearCustomPosterImage = clearCustomCreativeImage;
  window._meFormatInr = _meFormatInr;
})();
