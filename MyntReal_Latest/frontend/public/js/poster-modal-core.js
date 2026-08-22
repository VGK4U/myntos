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
                <label style="font-size:10px;font-weight:600;color:#6b7280;display:block;margin-bottom:2px">SENIOR PHOTO</label>
                <input type="file" id="postSeniorPhotoFile" accept="image/*" onchange="handleSeniorPhotoUpload(event)" style="font-size:11px;width:100%">
              </div>
              <div>
                <label style="font-size:10px;font-weight:600;color:#6b7280;display:block;margin-bottom:2px">HEADER TITLE</label>
                <input type="text" id="postTitle" oninput="updatePoster()" style="width:100%;padding:7px 9px;font-size:11.5px;border:1.5px solid #d1d5db;border-radius:6px" placeholder="CONGRATULATIONS">
              </div>
              <div>
                <label style="font-size:10px;font-weight:600;color:#6b7280;display:block;margin-bottom:2px">MEMBER NAME</label>
                <input type="text" id="postSubtitle" oninput="updatePoster()" style="width:100%;padding:7px 9px;font-size:11.5px;border:1.5px solid #d1d5db;border-radius:6px" placeholder="e.g. BANDI GANGARAJU">
              </div>
              <div>
                <label style="font-size:10px;font-weight:600;color:#6b7280;display:block;margin-bottom:2px">OVERALL EARNING (₹)</label>
                <input type="text" id="postHighlight" oninput="updatePoster()" style="width:100%;padding:7px 9px;font-size:11.5px;border:1.5px solid #d1d5db;border-radius:6px" placeholder="e.g. ₹1,07,880/-">
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
                    <input type="checkbox" id="payTypeStage1" checked onchange="recalculateTodayPayout()" style="accent-color:#059669"> Stage 1 Adv
                  </label>
                  <label style="font-size:10.5px;color:#374151;display:flex;align-items:center;gap:6px;cursor:pointer;user-select:none">
                    <input type="checkbox" id="payTypeStage2Adv" checked onchange="recalculateTodayPayout()" style="accent-color:#059669"> Stage 2 Adv
                  </label>
                  <label style="font-size:10.5px;color:#374151;display:flex;align-items:center;gap:6px;cursor:pointer;user-select:none">
                    <input type="checkbox" id="payTypeFinalComm" checked onchange="recalculateTodayPayout()" style="accent-color:#059669"> Final Comm
                  </label>
                  <label style="font-size:10.5px;color:#374151;display:flex;align-items:center;gap:6px;cursor:pointer;user-select:none">
                    <input type="checkbox" id="payTypeBrand" checked onchange="recalculateTodayPayout()" style="accent-color:#059669"> Brand Inc
                  </label>
                  <label style="font-size:10.5px;color:#374151;display:flex;align-items:center;gap:6px;cursor:pointer;user-select:none">
                    <input type="checkbox" id="payTypeBonanza" checked onchange="recalculateTodayPayout()" style="accent-color:#059669"> Bonanza
                  </label>
                  <label style="font-size:10.5px;color:#374151;display:flex;align-items:center;gap:6px;cursor:pointer;user-select:none">
                    <input type="checkbox" id="payTypeExtra" checked onchange="recalculateTodayPayout()" style="accent-color:#059669"> Extra Comm
                  </label>
                  <label style="font-size:10.5px;color:#374151;display:flex;align-items:center;gap:6px;cursor:pointer;user-select:none">
                    <input type="checkbox" id="payTypeAward" checked onchange="recalculateTodayPayout()" style="accent-color:#059669"> Award
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
                <input type="text" id="postTotalToday" oninput="updatePoster()" style="width:100%;padding:7px 9px;font-size:11.5px;border:1.5px solid #d1d5db;border-radius:6px" placeholder="e.g. ₹9,395/-">
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
                <input type="text" id="postPotential" oninput="updatePoster()" style="width:100%;padding:7px 9px;font-size:11.5px;border:1.5px solid #d1d5db;border-radius:6px" placeholder="e.g. ₹1,41,550/-">
              </div>
            </div>
          </div>
          
          <div style="border-top:1px solid #e5e7eb;margin-top:8px;padding-top:10px">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
              <h6 style="font-size:12px;font-weight:700;color:#111827;margin:0">SENIOR REFERRER DETAILS</h6>
              <label style="font-size:11px;font-weight:700;color:#059669;display:flex;align-items:center;gap:5px;cursor:pointer;user-select:none">
                <input type="checkbox" id="postShowSenior" checked onchange="updatePoster()" style="accent-color:#059669"> Show Senior
              </label>
            </div>
            <div style="display:flex;flex-direction:column;gap:8px">
              <div>
                <label style="font-size:10px;font-weight:600;color:#6b7280;display:block;margin-bottom:2px">SENIOR NAME</label>
                <input type="text" id="postSeniorName" oninput="updatePoster()" style="width:100%;padding:7px 9px;font-size:11.5px;border:1.5px solid #d1d5db;border-radius:6px" placeholder="e.g. MS. JARRA KUMARI">
              </div>
              <div>
                <label style="font-size:10px;font-weight:600;color:#6b7280;display:block;margin-bottom:2px">SENIOR TODAY'S EARNING (₹)</label>
                <input type="text" id="postSeniorToday" oninput="updatePoster()" style="width:100%;padding:7px 9px;font-size:11.5px;border:1.5px solid #d1d5db;border-radius:6px" placeholder="e.g. ₹1,835/-">
              </div>
              <div>
                <label style="font-size:10px;font-weight:600;color:#6b7280;display:block;margin-bottom:2px">SENIOR OVERALL (₹)</label>
                <input type="text" id="postSeniorEarning" oninput="updatePoster()" style="width:100%;padding:7px 9px;font-size:11.5px;border:1.5px solid #d1d5db;border-radius:6px" placeholder="e.g. ₹49,875/-">
              </div>
              <div>
                <label style="font-size:10px;font-weight:600;color:#6b7280;display:block;margin-bottom:2px">SENIOR POTENTIAL (₹)</label>
                <input type="text" id="postSeniorPotential" oninput="updatePoster()" style="width:100%;padding:7px 9px;font-size:11.5px;border:1.5px solid #d1d5db;border-radius:6px" placeholder="e.g. ₹91,650/-">
              </div>
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
          <div id="prevName" style="display:none"></div>
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

            <div style="background:linear-gradient(135deg, #854d0e 0%, #ca8a04 50%, #854d0e 100%);border:1.5px solid #fde047;color:#fffbeb;font-family:Georgia,serif;font-size:11px;font-weight:900;letter-spacing:1px;padding:4px 14px;border-radius:30px;box-shadow:0 4px 15px rgba(202,138,4,0.5);margin-bottom:5px;text-transform:uppercase;white-space:nowrap;max-width:100%;box-sizing:border-box">🎉 👑 ★★ CONGRATULATIONS ★★ 👑 🎉</div>

            <div style="width:100%;text-align:center;margin-bottom:6px">
              <div id="prevSubtitle" style="width:100%;background:#fbbf24;color:#000000 !important;-webkit-text-fill-color:#000000 !important;font-size:21px;font-weight:950;font-family:'Segoe UI',Roboto,Helvetica,sans-serif;text-transform:uppercase;letter-spacing:1px;line-height:1.2;padding:5px 12px;border:2.5px solid #ffffff;border-radius:12px;box-shadow:0 6px 20px rgba(251,191,36,0.75);box-sizing:border-box">MR. BANDI GANGARAJU</div>
            </div>

            <div style="position:relative;width:220px;height:220px;margin-bottom:12px">
              <div style="position:absolute;bottom:4px;left:-106px;font-size:82px;line-height:1;filter:drop-shadow(0 6px 16px rgba(251,191,36,0.9));z-index:10;user-select:none">🏆</div>

              <div style="width:220px;height:220px;border-radius:50%;border:5px solid #fde047;overflow:hidden;background:#001233;box-shadow:0 0 50px rgba(234,179,8,0.95);display:flex;align-items:center;justify-content:center">
                <img id="prevImg" src="" style="width:100%;height:100%;object-fit:cover;object-position:center 20%;display:none">
                <div id="prevAvatar" style="width:100%;height:100%;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#1d4ed8,#7c3aed);color:white;font-size:70px;font-weight:900">BG</div>
              </div>

              <div style="position:absolute;bottom:4px;right:-106px;font-size:82px;line-height:1;filter:drop-shadow(0 6px 16px rgba(251,191,36,0.9));z-index:10;user-select:none">🏆</div>
              <div style="position:absolute;bottom:-8px;left:50%;transform:translateX(-50%);background:linear-gradient(135deg,#b45309,#f59e0b,#b45309);border:1.5px solid #fef08a;color:#ffffff;font-size:10.5px;font-weight:900;padding:4px 18px;border-radius:14px;letter-spacing:1.2px;white-space:nowrap;box-shadow:0 4px 12px rgba(0,0,0,0.6);z-index:11">🏆 CHAMPION</div>
            </div>

            <div style="width:100%;background:linear-gradient(135deg, #ffffff 0%, #fffbeb 50%, #fef3c7 100%);border:2.5px solid #eab308;border-radius:16px;padding:7px 14px;text-align:center;margin-bottom:6px;box-shadow:0 8px 25px rgba(0,0,0,0.5), 0 0 20px rgba(251,191,36,0.3)">
              <div style="color:#92400e;font-size:11.5px;font-weight:900;letter-spacing:2px;text-transform:uppercase;margin-bottom:2px">★ OVERALL EARNING ★</div>
              <div id="prevHighlight" style="color:#b91c1c;font-size:34px;font-weight:950;line-height:1;font-family:'Segoe UI',Roboto,sans-serif;letter-spacing:-0.5px">₹1,07,880/-</div>
              <div id="prevHighlightInWords" style="font-size:9.5px;font-weight:850;color:#92400e;margin-top:3px;text-transform:uppercase;letter-spacing:0.3px;width:100%;line-height:1.2;text-align:center;word-break:break-word;overflow:visible">Rupees One Lakh Seven Thousand Eight Hundred Eighty Only</div>
            </div>

            <div style="width:100%;background:linear-gradient(135deg, #064e3b 0%, #047857 50%, #065f46 100%);border:1.5px solid #34d399;border-radius:14px;padding:8px 10px;text-align:center;margin-bottom:8px;box-shadow:0 4px 16px rgba(4,120,87,0.45);box-sizing:border-box">
              <div style="font-size:21px;font-weight:950;color:#ffffff;text-transform:uppercase;letter-spacing:0.5px;white-space:nowrap;max-width:100%;overflow:hidden"><span id="prevTodayLabelText">Today's Earning</span>: <span id="prevTotalToday" style="color:#fde047">₹9,395/-</span></div>
              <div id="prevAlreadyPaidText" style="font-size:12px;font-weight:800;color:#fde047;margin-top:3px;letter-spacing:0.3px;display:none">(Already Paid: ₹3,000/-)</div>
            </div>

            <div id="prevTodayPayout" style="display:none"></div>

            <div style="width:100%;display:grid;grid-template-columns:1fr 1fr 1.05fr;gap:6px;margin-bottom:8px;align-items:stretch">
              <!-- Files Card -->
              <div style="background:rgba(15,23,42,0.88);border:1.5px solid rgba(234,179,8,0.5);border-radius:12px;padding:6px 2px;text-align:center;display:flex;flex-direction:column;justify-content:center;align-items:center;gap:4px;min-height:60px;box-sizing:border-box">
                <div style="font-size:8px;font-weight:900;color:#93c5fd;text-transform:uppercase;letter-spacing:0.2px;line-height:1;white-space:nowrap">📂 FILES</div>
                <div id="prevFiles" style="display:flex;align-items:center;justify-content:center;font-size:11.5px;font-weight:950;color:#ffffff;line-height:1"><span style="display:inline-flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#f59e0b,#eab308);color:#0f172a;font-weight:950;font-size:9.5px;padding:2px 6px;border-radius:4px;line-height:1;white-space:nowrap">6 INSTALLED</span></div>
                <div id="prevTeamBreakupFiles" style="font-size:8px;font-weight:900;color:#93c5fd;letter-spacing:0.2px;line-height:1;white-space:nowrap">16 SUBMITTED</div>
              </div>
              
              <!-- Members / Team Size Card -->
              <div style="background:rgba(15,23,42,0.88);border:1.5px solid rgba(234,179,8,0.5);border-radius:12px;padding:6px 2px;text-align:center;display:flex;flex-direction:column;justify-content:center;align-items:center;gap:4px;min-height:60px;box-sizing:border-box">
                <div style="font-size:8px;font-weight:900;color:#a7f3d0;text-transform:uppercase;letter-spacing:0.2px;line-height:1;white-space:nowrap">👥 TEAM SIZE</div>
                <div id="prevOverall" style="display:flex;align-items:center;justify-content:center;font-size:12.5px;font-weight:950;color:#ffffff;line-height:1;white-space:nowrap">8 MEMBERS</div>
                <div id="prevTeamBreakup" style="font-size:8px;font-weight:800;color:#6ee7b7;line-height:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%">L2: 6 | L3: 2 | L4: 0</div>
              </div>

              <!-- Potential Pending Card -->
              <div style="background:linear-gradient(135deg, rgba(112,26,117,0.88), rgba(131,24,67,0.88));border:1.5px solid #f472b6;border-radius:12px;padding:6px 2px;text-align:center;display:flex;flex-direction:column;justify-content:center;align-items:center;gap:4px;min-height:60px;box-sizing:border-box">
                <div style="font-size:8px;font-weight:900;color:#fbcfe8;text-transform:uppercase;letter-spacing:0.2px;line-height:1;white-space:nowrap">💰 POTENTIAL PENDING</div>
                <div id="prevPotential" style="display:flex;align-items:center;justify-content:center;font-size:12.5px;font-weight:950;color:#ffffff;line-height:1;white-space:nowrap">₹1,41,550/-</div>
                <div style="font-size:8px;font-weight:800;color:#fbcfe8;letter-spacing:0.2px;line-height:1;white-space:nowrap">EXPECTED EARNING</div>
              </div>
            </div>

            <div id="prevSeniorRow" style="position:relative;width:100%;background:rgba(8,18,38,0.95);border:1.5px solid rgba(234,179,8,0.65);border-radius:16px;padding:8px 12px 8px 132px;display:flex;flex-direction:column;justify-content:center;margin-top:8px;margin-bottom:4px;min-height:96px;box-shadow:0 8px 25px rgba(0,0,0,0.6);box-sizing:border-box">
              <div style="position:absolute;top:-10px;left:10px;width:110px;height:110px;border-radius:50%;background:#1e3a8a;border:4.5px solid #fde047;box-shadow:0 6px 25px rgba(251,191,36,0.9);display:flex;align-items:center;justify-content:center;z-index:10;overflow:hidden">
                <img id="prevSeniorImg" src="" style="width:100%;height:100%;object-fit:cover;display:none">
                <div id="prevSeniorAvatar" style="width:100%;height:100%;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#1d4ed8,#7c3aed);color:white;font-size:36px;font-weight:900">NE</div>
              </div>

              <div id="prevSeniorName" style="font-size:13.5px;font-weight:950;color:#fde047;line-height:1.2;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-bottom:4px;letter-spacing:0.5px">Senior : MS. JARRA KUMARI</div>

              <div style="display:flex;justify-content:space-between;align-items:center;width:100%;padding-right:4px">
                <div style="text-align:left">
                  <div style="font-size:7.5px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:0.4px">Today</div>
                  <div id="prevSeniorToday" style="font-size:13px;font-weight:950;color:#ffffff">₹1,835/-</div>
                </div>
                <div style="text-align:center">
                  <div style="font-size:7.5px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:0.4px">Overall</div>
                  <div id="prevSeniorEarning" style="font-size:13px;font-weight:950;color:#34d399">₹49,875/-</div>
                </div>
                <div style="text-align:right">
                  <div style="font-size:7.5px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:0.4px">Potential</div>
                  <div id="prevSeniorPotential" style="font-size:13px;font-weight:950;color:#fb923c">₹91,650/-</div>
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
    
    <div style="background:#f3f4f6;padding:12px 24px;border-top:1px solid #e5e7eb;display:flex;justify-content:flex-end;align-items:center;gap:10px;flex-shrink:0;height:62px;box-sizing:border-box;z-index:20">
      <button onclick="closePosterModal()" style="background:#fff;color:#374151;border:1.5px solid #d1d5db;border-radius:8px;height:38px;padding:0 18px;font-size:13px;font-weight:600;cursor:pointer;display:inline-flex;align-items:center">Cancel</button>
      <button onclick="testShareToNumber()" style="background:linear-gradient(135deg,#0284c7,#0369a1);color:white;border:none;border-radius:8px;height:38px;padding:0 18px;font-size:13px;font-weight:700;cursor:pointer;display:inline-flex;align-items:center"><i class="fas fa-vial me-2"></i>Test Share (Custom No)</button>
      <button onclick="shareOnWhatsApp()" style="background:linear-gradient(135deg,#25d366,#128c7e);color:white;border:none;border-radius:8px;height:38px;padding:0 22px;font-size:13px;font-weight:700;cursor:pointer;display:inline-flex;align-items:center"><i class="fab fa-whatsapp me-2"></i>Share on WhatsApp</button>
      <button onclick="sharePoster()" style="background:linear-gradient(135deg,#3b82f6,#2563eb);color:white;border:none;border-radius:8px;height:38px;padding:0 22px;font-size:13px;font-weight:700;cursor:pointer;display:inline-flex;align-items:center"><i class="fas fa-share-alt me-2"></i>Share Poster</button>
      <button onclick="shareDefaultChannel()" style="background:linear-gradient(135deg,#8b5cf6,#6d28d9);color:white;border:none;border-radius:8px;height:38px;padding:0 22px;font-size:13px;font-weight:700;cursor:pointer;display:inline-flex;align-items:center"><i class="fas fa-bullhorn me-2"></i>Share Default</button>
      <button onclick="postPosterAnnouncement()" style="background:linear-gradient(135deg,#ec4899,#be185d);color:white;border:none;border-radius:8px;height:38px;padding:0 22px;font-size:13px;font-weight:700;cursor:pointer;display:inline-flex;align-items:center"><i class="fas fa-bullhorn me-2"></i>Post Announcement</button>
      <button onclick="downloadPoster()" style="background:linear-gradient(135deg,#059669,#047857);color:white;border:none;border-radius:8px;height:38px;padding:0 22px;font-size:13px;font-weight:700;cursor:pointer;display:inline-flex;align-items:center"><i class="fas fa-download me-2"></i>Download Image</button>
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
    if (!path || path === 'None' || path === 'null') return '';
    if (path.startsWith('http://') || path.startsWith('https://') || path.startsWith('data:')) {
      return path;
    }
    if (path.startsWith('/storage/')) {
      return window.location.origin + path;
    }
    if (path.startsWith('storage/')) {
      return window.location.origin + '/' + path;
    }
    if (path.startsWith('/')) {
      return window.location.origin + '/storage' + path;
    }
    return window.location.origin + '/storage/' + path;
  }

  function closePosterModal() {
    const el = document.getElementById('posterModal');
    if (el) el.style.display = 'none';
  }
  window.closePosterModal = closePosterModal;

  async function generateMemberPoster(partnerId) {
    ensurePosterModalDOM();
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
           || (window._vgkMemberCache || {})[pidStr];

      if (!m || !m.id) {
        try {
          const apiBase = (typeof API_BASE !== 'undefined') ? API_BASE : (typeof API !== 'undefined' ? API : '/api/v1');
          const paramStr = pidStr.startsWith('VGK') ? 'search=' + encodeURIComponent(pidStr) : 'partner_id=' + encodeURIComponent(pidStr);
          const freshRes = await safeFetch(apiBase + '/vgk/dashboard/member-earnings?' + paramStr + '&_cb=' + Date.now());
          const freshData = await freshRes.json();
          if (freshData.success && freshData.data && freshData.data.length) {
            const found = freshData.data.find(x => String(x.id) === pidStr || String(x.partner_code) === pidStr) || freshData.data[0];
            if (found) m = found;
          }
        } catch (e) {
          console.warn("Failed to fetch member data from API:", e);
        }
      }

      if (!m) throw new Error('Member details could not be loaded for ID: ' + pidStr);
      window._currentPosterMember = m;

      const prevName = document.getElementById('prevName');
      if (prevName) prevName.textContent = (m.partner_name || '').toUpperCase();
      
      const initials = (m.partner_name || '').trim().split(/\s+/).map(p => p[0]).join('').slice(0, 2).toUpperCase();
      if (prevAvatar) prevAvatar.textContent = initials;

      const photoPath = m.passport_photo || m.logo_path || m.profile_image || m.photo_url || m.avatar_url || m.id_card_photo || m.photo;
      const resolvedUrl = resolvePosterMediaUrl(photoPath);
      if (resolvedUrl && prevImg) {
        prevImg.crossOrigin = "anonymous";
        prevImg.onload = () => {
          prevImg.style.display = 'block';
          if (prevAvatar) prevAvatar.style.display = 'none';
        };
        prevImg.onerror = () => {
          prevImg.style.display = 'none';
          if (prevAvatar) prevAvatar.style.display = 'flex';
        };
        prevImg.src = resolvedUrl.includes('?') ? resolvedUrl : (resolvedUrl + '?t=' + Date.now());
      } else if (prevAvatar) {
        prevAvatar.style.display = 'flex';
      }

      const apiBase = (typeof API_BASE !== 'undefined') ? API_BASE : (typeof API !== 'undefined' ? API : '/api/v1');
      const targetPid = m.id || partnerId;
      const detailUrl = apiBase + '/vgk/dashboard/member-income-entries?partner_id=' + targetPid;

      const r = await safeFetch(detailUrl);
      const d = await r.json();
      const entries = (d.success && d.data) ? d.data : [];
      window._currentEntries = entries;

      window._seniorEntries = [];
      if (m.parent_partner_id) {
        try {
          const srRes = await safeFetch(apiBase + '/vgk/dashboard/member-income-entries?partner_id=' + m.parent_partner_id);
          const srData = await srRes.json();
          if (srData.success && srData.data) {
            window._seniorEntries = srData.data;
          }
        } catch (srErr) {
          console.warn("[Poster Debug] Failed to fetch senior partner entries:", srErr);
        }
      }

      const uniqueL1Leads = new Set();
      entries.forEach(e => {
        if (e.level === 1 && e.status !== 'CANCELLED' && e.source_lead_id) {
          uniqueL1Leads.add(e.source_lead_id);
        }
      });
      const activeFiles = uniqueL1Leads.size;

      // Potential Earning: Total potential earning irrespective of level
      const uniquePotentialLeads = {};
      entries.forEach(e => {
        if (e.status !== 'CANCELLED') {
          const leadId = e.source_lead_id || 0;
          const lvl = e.level !== null && e.level !== undefined ? e.level : -1;
          const key = `${leadId}_${lvl}`;
          const val = e.potential_overall_earning || e.commission_amount || 0;
          if (!uniquePotentialLeads[key] || val > uniquePotentialLeads[key]) {
            uniquePotentialLeads[key] = val;
          }
        }
      });
      const potentialEarning = Object.values(uniquePotentialLeads).reduce((a, b) => a + b, 0);

      const todayStr = new Date().toISOString().split('T')[0];
      const validDates = entries.filter(e => e.level === 1 && e.status !== 'CANCELLED' && e.income_date && e.income_date !== 'None').map(e => e.income_date).sort();
      const lastEarningDate = validDates.length > 0 ? validDates[validDates.length - 1] : todayStr;

      const mainDateFrom = (document.getElementById('meDateFrom')?.value || '').trim();
      const mainDateTo   = (document.getElementById('meDateTo')?.value || '').trim();

      let initFrom = mainDateFrom;
      let initTo   = mainDateTo;

      if (!initFrom && !initTo) {
        initFrom = lastEarningDate;
        initTo   = lastEarningDate;
      } else if (!initFrom) {
        initFrom = initTo;
      } else if (!initTo) {
        initTo = initFrom;
      }

      const pDateFrom = document.getElementById('postPayoutDateFrom');
      const pDateTo = document.getElementById('postPayoutDateTo');
      if (pDateFrom) pDateFrom.value = initFrom;
      if (pDateTo) pDateTo.value = initTo;

      const seniorName = m.senior_name || '—';
      const seniorEarning = m.senior_earning !== null && m.senior_earning !== undefined ? '₹' + _meFormatInr(m.senior_earning) + '/-' : '—';

      let customerName = '—', location = '—';
      const targetEntries = entries.filter(e => e.level === 1 && e.status !== 'CANCELLED' && (!initFrom || e.income_date >= initFrom) && (!initTo || e.income_date <= initTo));
      if (targetEntries.length) {
        customerName = targetEntries[0].client_name || '—';
        location = targetEntries[0].location || '—';
      } else if (entries.length) {
        customerName = entries[0].client_name || '—';
        location = entries[0].location || '—';
      }

      const installedStages = ['completed', 'installation_pending', 'net_meter_pending', 'balance_pending', 'balance_received', 'subsidy_pending', 'stage 2', 'installed'];
      const installedSet = new Set();
      entries.forEach(e => {
        if (e.level === 1 && e.status !== 'CANCELLED' && e.source_lead_id) {
          const typeStr = (e.income_type || e.kind || '').toLowerCase();
          const stageStr = (e.stage_name || e.solar_pipeline_status || e.stage || '').toString().toLowerCase();
          const isInst = installedStages.some(s => typeStr.includes(s) || stageStr.includes(s)) || (e.kind || '').toUpperCase() === 'DVR_ADVANCE' || (e.stage2_adv && e.stage2_adv > 0);
          if (isInst) {
            installedSet.add(e.source_lead_id);
          }
        }
      });
      let installedFiles = installedSet.size;
      const filesDisplay = (installedFiles > 0 ? `${installedFiles}/${activeFiles}` : `0/${activeFiles}`) + ' FILES';

      const setVal = (id, val) => { const el = document.getElementById(id); if (el) el.value = val; };
      const setChecked = (id, val) => { const el = document.getElementById(id); if (el) el.checked = val; };

      setVal('postTitle', 'CONGRATULATIONS');
      setVal('postSubtitle', m.partner_name || '');

      // Overall Earning: Total cumulative earnings irrespective of level
      const allTimeSum = entries.reduce((sum, e) => {
        if (e.status === 'CANCELLED') return sum;
        if (e.entry_number && String(e.entry_number).startsWith('VSCA-')) return sum;
        if (e.id && String(e.id).startsWith('VSCA-')) return sum;
        return sum + (parseFloat(e.commission_amount || e.amount || 0) || 0);
      }, 0);
      const overallVal = (allTimeSum > 0) ? allTimeSum : ((m.all_time_gross_earned !== undefined && m.all_time_gross_earned !== null) ? m.all_time_gross_earned : ((m.gross_earned !== undefined && m.gross_earned !== null) ? m.gross_earned : (m.received || 0)));
      setVal('postHighlight', '₹' + _meFormatInr(overallVal) + '/-');
      setVal('postFiles', filesDisplay);
      setVal('postOverall', (activeFiles || m.ground_leads_count || 0) + ' LEADS');
      setVal('postTeamBreakup', `L1 Ground-Source Business Only`);
      const potVal = (m && m.potential_earning !== undefined && m.potential_earning !== null) ? m.potential_earning : potentialEarning;
      setVal('postPotential', '₹' + _meFormatInr(potVal) + '/-');
      setVal('postCustomer', customerName);
      setVal('postLocation', location);
      setVal('postSeniorName', seniorName);
      setVal('postSeniorEarning', seniorEarning);
      const seniorPotentialVal = (m.senior_potential_earned !== null && m.senior_potential_earned !== undefined) ? '₹' + _meFormatInr(m.senior_potential_earned) + '/-' : '—';
      setVal('postSeniorPotential', seniorPotentialVal);

      const seniorNameUpper = (seniorName || '').toUpperCase().trim();
      const isVgkSupport = seniorNameUpper.includes('VGK SUPPORT') || seniorNameUpper.includes('SUPPORT') || seniorNameUpper === 'NONE' || seniorNameUpper === '—' || !seniorNameUpper;
      
      // VGK Support MUST ALWAYS BE HIDDEN on the Achievement Poster
      setChecked('postShowSenior', !isVgkSupport);
      const postShowSeniorEl = document.getElementById('postShowSenior');
      if (postShowSeniorEl && isVgkSupport) {
        postShowSeniorEl.checked = false;
        postShowSeniorEl.disabled = true;
      }

      setChecked('payTypeStage1', true);
      setChecked('payTypeStage2Adv', true);
      setChecked('payTypeFinalComm', true);
      setChecked('payTypeBrand', true);
      setChecked('payTypeBonanza', true);
      setChecked('payTypeExtra', true);
      setChecked('payTypeAward', true);

      const seniorImg = document.getElementById('prevSeniorImg');
      const seniorAvatar = document.getElementById('prevSeniorAvatar');
      if (seniorImg) {
        const seniorPhotoPath = m.senior_photo || m.senior_passport_photo || m.senior_logo_path || m.senior_profile_image;
        const resolvedSeniorUrl = resolvePosterMediaUrl(seniorPhotoPath);
        if (resolvedSeniorUrl) {
          seniorImg.crossOrigin = "anonymous";
          seniorImg.onload = () => { seniorImg.style.display = 'block'; if (seniorAvatar) seniorAvatar.style.display = 'none'; };
          seniorImg.onerror = () => { seniorImg.style.display = 'none'; if (seniorAvatar) seniorAvatar.style.display = 'flex'; };
          seniorImg.src = resolvedSeniorUrl.includes('?') ? resolvedSeniorUrl : (resolvedSeniorUrl + '?t=' + Date.now());
        } else {
          seniorImg.style.display = 'none';
          if (seniorAvatar) seniorAvatar.style.display = 'flex';
        }
      }

      if (document.getElementById('postThemePreset')) document.getElementById('postThemePreset').value = 'celebration_graphic';
      changeThemePreset();
      recalculateTodayPayout();
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
    recalculateTodayPayout();
  }

  function setPosterPresetPeriod(period) {
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
      const validDates = entries.filter(e => e.level === 1 && e.status !== 'CANCELLED' && e.income_date && e.income_date !== 'None').map(e => e.income_date).sort();
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

  function recalculateTodayPayout() {
    const showStage1    = document.getElementById('payTypeStage1')?.checked ?? true;
    const showStage2Adv = document.getElementById('payTypeStage2Adv')?.checked ?? true;
    const showFinalComm = document.getElementById('payTypeFinalComm')?.checked ?? true;
    const showBrand     = document.getElementById('payTypeBrand')?.checked ?? true;
    const showBonanza   = document.getElementById('payTypeBonanza')?.checked ?? true;
    const showExtra     = document.getElementById('payTypeExtra')?.checked ?? true;
    const showAward     = document.getElementById('payTypeAward')?.checked ?? true;

    const entries = window._currentEntries || [];
    const dateFrom = (document.getElementById('postPayoutDateFrom')?.value || '').trim();
    const dateTo = (document.getElementById('postPayoutDateTo')?.value || '').trim();

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

    let stage1Amt = 0, stage2AdvAmt = 0, finalCommBalGrossAmt = 0, finalCommAdvPaidAmt = 0;
    let brandAmt = 0, bonanzaAmt = 0, extraAmt = 0, awardAmt = 0, seniorTodayAmt = 0;

    // Ground-source L1 entries calculation only for the selected date context
    entries.forEach(e => {
      if (e.level === 1 && e.status !== 'CANCELLED' && e.income_date && e.income_date !== 'None') {
        const d = e.income_date;
        if (dateFrom && d < dateFrom) return;
        if (dateTo && d > dateTo) return;

        const grossAmt = parseFloat(e.commission_amount || 0);
        
        // Actual cash payment status check: only count advance_paid or paid if explicitly paid out
        const isPaidOut = e.status === 'PAID' || Boolean(e.paid_at) || Boolean(e.paid_bank_ledger_id) || Boolean(e.paid_cash_staff_id);
        const advPaid = isPaidOut ? parseFloat(e.commission_amount || e.advance_paid || 0) : 0;
        const balGross = Math.max(0, grossAmt - advPaid);

        const k = (e.kind || '').toUpperCase();
        const typeStr = (e.income_type || '').toLowerCase();

        if (k === 'ADVANCE' || typeStr.includes('stage 1 adv')) stage1Amt += grossAmt;
        else if (k === 'DVR_ADVANCE' || typeStr.includes('stage 2 adv')) stage2AdvAmt += grossAmt;
        else if (k === 'BRAND_COMMISSION' || typeStr.includes('brand')) brandAmt += grossAmt;
        else if (k === 'SLAB_BONUS' || typeStr.includes('bonanza') || typeStr.includes('slab')) bonanzaAmt += grossAmt;
        else if (k === 'EXTRA_COMMISSION' || typeStr.includes('extra')) extraAmt += grossAmt;
        else if (k === 'AWARD' || k === 'INCENTIVE' || k === 'ROYALTY' || typeStr.includes('award') || typeStr.includes('incentive')) awardAmt += grossAmt;
        else if (k === 'COMMISSION' || k === 'SENIOR_COMM') {
          finalCommBalGrossAmt += balGross;
          finalCommAdvPaidAmt += advPaid;
        }
      }
    });

    let breakupItems = [];
    let total = 0;
    let commByLevel = {};

    entries.forEach(e => {
      if (e.level === 1 && e.status !== 'CANCELLED' && e.income_date && e.income_date !== 'None') {
        const d = e.income_date;
        if (dateFrom && d < dateFrom) return;
        if (dateTo && d > dateTo) return;
        const k = (e.kind || '').toUpperCase();
        if (k === 'COMMISSION' || k === 'SENIOR_COMM') {
          const lvl = e.level || 1;
          const lbl = e.level_label || (lvl === 1 ? 'L1 Ground Source Comm' : `L${lvl} Commission`);
          const grossAmt = parseFloat(e.commission_amount || 0);
          const isPaidOut = e.status === 'PAID' || Boolean(e.paid_at);
          const advPaid = isPaidOut ? grossAmt : 0;
          if (!commByLevel[lbl]) commByLevel[lbl] = { gross: 0, adv: 0 };
          commByLevel[lbl].gross += grossAmt;
          commByLevel[lbl].adv += advPaid;
        }
      }
    });

    if (showStage1 && stage1Amt > 0) { breakupItems.push(`Stage 1 Advance: ₹${_meFormatInr(stage1Amt)}/-`); total += stage1Amt; }
    if (showStage2Adv && stage2AdvAmt > 0) { breakupItems.push(`Stage 2 Advance: ₹${_meFormatInr(stage2AdvAmt)}/-`); total += stage2AdvAmt; }

    let totalAdvPaid = 0; // Actual cash paid out
    entries.forEach(e => {
      if (e.level === 1 && e.status !== 'CANCELLED' && e.income_date && e.income_date !== 'None') {
        const d = e.income_date;
        if (dateFrom && d < dateFrom) return;
        if (dateTo && d > dateTo) return;
        if (e.status === 'PAID' || Boolean(e.paid_at)) {
          totalAdvPaid += parseFloat(e.commission_amount || e.amount || 0);
        }
      }
    });

    const payingGross = total;

    const postTodayPayoutEl = document.getElementById('postTodayPayout');
    if (postTodayPayoutEl) postTodayPayoutEl.value = breakupItems.map(s => s.replace(/<[^>]*>/g, '')).join(' | ');

    const postTotalTodayEl = document.getElementById('postTotalToday');
    if (postTotalTodayEl) postTotalTodayEl.value = '₹' + _meFormatInr(payingGross) + '/-';

    // Senior Partner Today Earning calculation from window._seniorEntries for date range
    seniorTodayAmt = 0;
    if (window._seniorEntries && window._seniorEntries.length) {
      window._seniorEntries.forEach(se => {
        if (se.status !== 'CANCELLED' && se.income_date && se.income_date !== 'None') {
          const sd = se.income_date;
          if (dateFrom && sd < dateFrom) return;
          if (dateTo && sd > dateTo) return;
          seniorTodayAmt += parseFloat(se.commission_amount || se.amount || 0);
        }
      });
    }

    const postSeniorToday = document.getElementById('postSeniorToday');
    if (postSeniorToday) {
      postSeniorToday.value = '₹' + _meFormatInr(seniorTodayAmt) + '/-';
    }

    window._currentTotalAdvPaid = totalAdvPaid;
    const prevTotalTodayEl = document.getElementById('prevTotalToday');
    if (prevTotalTodayEl) prevTotalTodayEl.textContent = '₹' + _meFormatInr(payingGross) + '/-';

    const prevAlreadyPaidEl = document.getElementById('prevAlreadyPaidText');
    if (prevAlreadyPaidEl) {
      if (totalAdvPaid > 0) {
        prevAlreadyPaidEl.textContent = `(Already Paid: ₹${_meFormatInr(totalAdvPaid)}/-)`;
        prevAlreadyPaidEl.style.display = 'block';
      } else {
        // HIDE COMPLETELY WHEN ACTUAL PAYMENT = 0
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

    setTxt('prevTitle', '★ ' + getVal('postTitle').toUpperCase() + ' ★');
    setTxt('prevSubtitle', getVal('postSubtitle').toUpperCase());

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
      const match = filesVal.match(/^(\d+)\s*\/\s*(\d+)\s*(.*)$/);
      if (match) {
        prevFilesEl.innerHTML = `<span style="display:inline-flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#f59e0b,#eab308);color:#0f172a;font-weight:950;font-size:9.5px;padding:2px 6px;border-radius:4px;line-height:1;white-space:nowrap">${match[1]} INSTALLED</span>`;
        if (prevTeamBreakupFilesEl) prevTeamBreakupFilesEl.innerHTML = `<span style="font-size:8px;font-weight:900;color:#93c5fd;letter-spacing:0.2px;line-height:1;white-space:nowrap">${match[2]} SUBMITTED</span>`;
      } else {
        prevFilesEl.textContent = filesVal;
      }
    }

    const prevTotalTodayEl = document.getElementById('prevTotalToday');
    if (prevTotalTodayEl) prevTotalTodayEl.textContent = getVal('postTotalToday');

    setTxt('prevOverall', getVal('postOverall'));
    setTxt('prevTeamBreakup', getVal('postTeamBreakup'));
    setTxt('prevCustomer', getVal('postCustomer').toUpperCase());
    setTxt('prevLocation', getVal('postLocation').toUpperCase());

    let rawSeniorName = getVal('postSeniorName').trim().toUpperCase();
    if (rawSeniorName && !rawSeniorName.startsWith('SENIOR :')) rawSeniorName = 'Senior : ' + rawSeniorName;
    setTxt('prevSeniorName', rawSeniorName || 'SENIOR : —');
    setTxt('prevSeniorToday', getVal('postSeniorToday'));
    setTxt('prevSeniorEarning', getVal('postSeniorEarning'));
    setTxt('prevSeniorPotential', getVal('postSeniorPotential'));

    const showSenior = document.getElementById('postShowSenior')?.checked ?? true;
    const prevSeniorRow = document.getElementById('prevSeniorRow');
    if (prevSeniorRow) prevSeniorRow.style.display = showSenior ? 'flex' : 'none';
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

  async function capturePosterCanvas(container) {
    if (!container) container = document.getElementById('posterCanvasWrapper');
    if (!container) return null;

    const w = container.scrollWidth || 480;
    const h = container.scrollHeight || 780;

    try {
      return await window.html2canvas(container, {
        useCORS: true,
        allowTaint: false,
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

    const partnerName = (document.getElementById('prevSubtitle')?.textContent || '').trim() || 'Channel Partner';
    const partnerOverall = (document.getElementById('prevHighlight')?.textContent || '').trim() || '';
    const partnerToday = (document.getElementById('prevTotalToday')?.textContent || '').trim() || '';
    const partnerPotential = (document.getElementById('prevPotential')?.textContent || '').trim() || '';

    const seniorName = (document.getElementById('prevSeniorName')?.textContent || '').replace(/^Senior\s*:\s*/i, '').trim() || '';
    const seniorToday = (document.getElementById('prevSeniorToday')?.textContent || '').trim() || '';
    const seniorOverall = (document.getElementById('prevSeniorEarning')?.textContent || '').trim() || '';

    const showSeniorInput = document.getElementById('postShowSenior');
    const isSeniorVisible = showSeniorInput ? showSeniorInput.checked : (document.getElementById('prevSeniorRow')?.style.display !== 'none');

    const spinner = document.getElementById('posterSpinner');
    if (spinner) spinner.style.display = 'flex';

    let shareText = `🎉 *[TEST BROADCAST] CONGRATULATIONS TO ${partnerName}!* 🎉\n\n` +
      `👤 *Member Name:* ${partnerName}\n` +
      `💰 *Today's Payout:* ${partnerToday}\n` +
      `📈 *Overall Earning:* ${partnerOverall}\n` +
      `🔮 *Potential Valuation:* ${partnerPotential}\n\n`;

    if (isSeniorVisible && seniorName && seniorName !== '—' && seniorName !== 'NONE' && !seniorName.endsWith('—')) {
      shareText += `🙌 *Senior Referrer:* ${seniorName}\n` +
        `💰 *Senior Today:* ${seniorToday} | *Overall:* ${seniorOverall}\n\n`;
    }

    shareText += `🌐 *Official Website:* https://vgk4u.com\n\n` +
      `🚀 Join VGK4U today & grow your earnings!`;

    let dataUrl = null;
    try {
      const canvas = await capturePosterCanvas(container);
      if (canvas) {
        try {
          dataUrl = canvas.toDataURL('image/png');
        } catch (cErr) {
          console.warn("Poster toDataURL failed:", cErr);
        }
      }
    } catch (capErr) {
      console.warn("capturePosterCanvas error:", capErr);
    }

    if (spinner) spinner.style.display = 'none';

    try {
      const res = await fetch('http://localhost:5002/api/send-message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone: cleanPhone, imageUrl: dataUrl, message: shareText })
      });
      const json = await res.json();
      if (json.success) {
        alert(`✅ TEST SHARE SENT SUCCESSFULLY!\n----------------------------------------\nRecipient: +91 ${cleanPhone.slice(-10)}\nImage: ${dataUrl ? 'Attached 🖼️' : 'Text Only'}\n\nPlease check your WhatsApp on +91 ${cleanPhone.slice(-10)} to verify!`);
      } else {
        alert(`❌ TEST SHARE FAILED: ${json.error || 'WhatsApp bot error'}`);
      }
    } catch (err) {
      alert(`❌ TEST SHARE ERROR: Could not connect to WhatsApp Bot on port 5002.\n(${err.message})`);
    }
  }

  function downloadPoster() {
    const container = document.getElementById('posterCanvasWrapper');
    const partnerName = document.getElementById('prevSubtitle')?.textContent?.trim() || 'Channel_Partner';
    capturePosterCanvas(container).then(canvas => {
      if (!canvas) return;
      const link = document.createElement('a');
      link.download = `${partnerName.replace(/\s+/g, '_')}_Achievement_Poster.png`;
      link.href = canvas.toDataURL('image/png');
      link.click();
    }).catch(err => alert('Failed to download image: ' + err.message));
  }

  function sharePoster() {
    const container = document.getElementById('posterCanvasWrapper');
    const partnerName = document.getElementById('prevSubtitle')?.textContent?.trim() || 'Partner';
    const totalPayout = document.getElementById('prevTotalToday')?.textContent?.trim() || '';
    const spinner = document.getElementById('posterSpinner');
    if (spinner) spinner.style.display = 'flex';

    capturePosterCanvas(container).then(canvas => {
      if (spinner) spinner.style.display = 'none';
      if (!canvas) return;
      canvas.toBlob(blob => {
        if (!blob) { alert('Failed to generate image file.'); return; }
        const file = new File([blob], `${partnerName.replace(/\s+/g, '_')}_Achievement.png`, { type: 'image/png' });
        if (navigator.canShare && navigator.canShare({ files: [file] })) {
          navigator.share({ title: 'VGK4U Celebration Poster', text: `Congratulations to ${partnerName} for earning ${totalPayout} today!`, files: [file] }).catch(err => {
            if (err.name !== 'AbortError') alert('Sharing failed: ' + err.message);
          });
        } else {
          const a = document.createElement('a');
          a.download = `${partnerName.replace(/\s+/g, '_')}_Achievement.png`;
          a.href = URL.createObjectURL(blob);
          a.click();
        }
      }, 'image/png');
    }).catch(err => {
      if (spinner) spinner.style.display = 'none';
      alert('Failed to generate sharing image: ' + err.message);
    });
  }

  function shareOnWhatsApp() {
    const container = document.getElementById('posterCanvasWrapper');
    const partnerName = document.getElementById('prevSubtitle')?.textContent?.trim() || '';
    const partnerOverall = document.getElementById('prevHighlight')?.textContent?.trim() || '';
    const partnerToday = document.getElementById('prevTotalToday')?.textContent?.trim() || '';
    const seniorName = document.getElementById('prevSeniorName')?.textContent?.trim() || '';
    const seniorOverall = document.getElementById('prevSeniorEarning')?.textContent?.trim() || '';
    const seniorToday = document.getElementById('prevSeniorToday')?.textContent?.trim() || '';
    const partnerPotential = document.getElementById('prevPotential')?.textContent?.trim() || '';
    const seniorPotential = document.getElementById('prevSeniorPotential')?.textContent?.trim() || '₹0/-';

    const showSeniorInput = document.getElementById('postShowSenior');
    const isSeniorVisible = showSeniorInput ? showSeniorInput.checked : (document.getElementById('prevSeniorRow')?.style.display !== 'none');

    let text = `🎉 *CONGRATULATIONS!* 🎉\n\n🌟 *Member Achievement:* 🌟\n👤 *Name:* ${partnerName}\n💰 *Today's Earning:* ${partnerToday}\n📈 *Overall Earning:* ${partnerOverall}\n🔮 *Potential Valuation:* ${partnerPotential}\n`;

    if (isSeniorVisible && seniorName && seniorName !== '—' && seniorName !== 'NONE' && !seniorName.endsWith('—')) {
      text += `\n----------------------------------\n\n🙌 *Senior Referrer Achievement:* 🙌\n👤 *Name:* ${seniorName}\n💰 *Today's Earning:* ${seniorToday}\n📈 *Overall Earning:* ${seniorOverall}\n🔮 *Potential Earning:* ${seniorPotential}\n`;
    }

    text += `\n🚀 Keep up the fantastic work! 🚀\nvgk4u.myntreal.com`;

    const shareWindow = window.open('', '_blank');
    if (shareWindow) {
      shareWindow.document.write('<html><head><title>Loading WhatsApp...</title><style>body{font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;background:#f3f4f6;color:#374151;} .loader{border:4px solid #e5e7eb;border-top:4px solid #25d366;border-radius:50%;width:40px;height:40px;animation:spin 1s linear infinite;margin-bottom:16px;} @keyframes spin{0%{transform:rotate(0deg);}100%{transform:rotate(360deg);}}</style></head><body><div style="text-align:center"><div class="loader" style="margin:0 auto 16px;"></div><div>Preparing your WhatsApp share & download... Please wait.</div></div></body></html>');
    }

    const spinner = document.getElementById('posterSpinner');
    if (spinner) spinner.style.display = 'flex';

    capturePosterCanvas(container).then(canvas => {
      if (spinner) spinner.style.display = 'none';
      if (!canvas) { if (shareWindow) shareWindow.close(); return; }

      try {
        const link = document.createElement('a');
        link.download = `${partnerName.replace(/\s+/g, '_')}_Achievement_Poster.png`;
        link.href = canvas.toDataURL('image/png');
        link.click();
      } catch (e) {}

      canvas.toBlob(async (blob) => {
        if (!blob) { alert('Failed to generate sharing image.'); if (shareWindow) shareWindow.close(); return; }
        try {
          if (navigator.clipboard && window.ClipboardItem) {
            await navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })]);
          }
        } catch (e) {}
        const url = `https://api.whatsapp.com/send?text=${encodeURIComponent(text)}`;
        if (shareWindow) shareWindow.location.href = url;
        else window.open(url, '_blank');
      }, 'image/png');
    }).catch(err => {
      if (spinner) spinner.style.display = 'none';
      if (shareWindow) shareWindow.close();
      alert('Failed to generate sharing image: ' + err.message);
    });
  }

  async function shareDefaultChannel() {
    const container = document.getElementById('posterCanvasWrapper');
    if (!container) return;

    const partnerName = (document.getElementById('prevSubtitle')?.textContent || '').trim() || 'Channel Partner';
    const partnerOverall = (document.getElementById('prevHighlight')?.textContent || '').trim() || '';
    const partnerToday = (document.getElementById('prevTotalToday')?.textContent || '').trim() || '';
    const partnerPotential = (document.getElementById('prevPotential')?.textContent || '').trim() || '';

    const seniorName = (document.getElementById('prevSeniorName')?.textContent || '').replace(/^Senior\s*:\s*/i, '').trim() || '';
    const seniorToday = (document.getElementById('prevSeniorToday')?.textContent || '').trim() || '';
    const seniorOverall = (document.getElementById('prevSeniorEarning')?.textContent || '').trim() || '';

    const showSeniorInput = document.getElementById('postShowSenior');
    const isSeniorVisible = showSeniorInput ? showSeniorInput.checked : (document.getElementById('prevSeniorRow')?.style.display !== 'none');

    const m = window._currentPosterMember || {};
    const mPhone = (m.phone || '').replace(/\D/g, '');
    const sPhone = isSeniorVisible ? (m.senior_phone || '').replace(/\D/g, '') : '';

    const spinner = document.getElementById('posterSpinner');
    if (spinner) spinner.style.display = 'flex';

    let shareText = `🎉 *CONGRATULATIONS TO ${partnerName}!* 🎉\n\n` +
      `👤 *Member Name:* ${partnerName}\n` +
      `💰 *Today's Payout:* ${partnerToday}\n` +
      `📈 *Overall Earning:* ${partnerOverall}\n` +
      `🔮 *Potential Valuation:* ${partnerPotential}\n\n`;

    if (isSeniorVisible && seniorName && seniorName !== '—' && seniorName !== 'NONE' && !seniorName.endsWith('—')) {
      shareText += `🙌 *Senior Referrer:* ${seniorName}\n` +
        `💰 *Senior Today:* ${seniorToday} | *Overall:* ${seniorOverall}\n\n`;
    }

    shareText += `🌐 *Official Website:* https://vgk4u.com\n\n` +
      `🚀 Join VGK4U today & grow your earnings!`;

    const dispatchTargets = [
      { id: 'member', type: 'member', label: `Member: ${partnerName}`, target: mPhone ? `+91 ${mPhone.slice(-10)}` : 'No Phone', phone: mPhone, status: 'sending', msg: 'Broadcasting...' },
      { id: 'senior', type: 'member', label: `Senior: ${seniorName || 'Referrer'}`, target: !isSeniorVisible ? 'Excluded (Show Senior unchecked)' : (sPhone ? `+91 ${sPhone.slice(-10)}` : 'No Phone'), phone: sPhone, status: isSeniorVisible ? (sPhone ? 'sending' : 'skipped') : 'skipped', msg: !isSeniorVisible ? 'Excluded by toggle' : (sPhone ? 'Broadcasting...' : 'No Senior Phone') },
      { id: 'channel_official', type: 'group', label: 'VGK4U Official Channel', target: 'whatsapp.com/channel/0029Vb7Vb5f9cDDXf3zWtf0m', inviteCode: '0029Vb7Vb5f9cDDXf3zWtf0m', status: 'sending', msg: 'Broadcasting to channel...' },
      { id: 'group_main', type: 'group', label: 'VGK Community Group', target: 'chat.whatsapp.com/HNQQoKXFfCm5PQngGdrlcY', inviteCode: 'HNQQoKXFfCm5PQngGdrlcY', status: 'sending', msg: 'Broadcasting to group...' },
      { id: 'group_exec', type: 'group', label: 'Executive Announcements', target: 'chat.whatsapp.com/LfX8mGootXa7SpwNIz7P5C', inviteCode: 'LfX8mGootXa7SpwNIz7P5C', status: 'sending', msg: 'Broadcasting to group...' },
      { id: 'group_ev_stars', type: 'group', label: 'Ev scooty. MNR (royal ev ) stars', target: 'Ev scooty. MNR (royal ev ) stars', groupName: 'Ev scooty. MNR (royal ev ) stars', status: 'sending', msg: 'Broadcasting to group...' },
      { id: 'group_mnr_gen', type: 'group', label: 'MNR General Group', target: 'MNR General Group', groupName: 'MNR General Group', status: 'sending', msg: 'Broadcasting to group...' },
      { id: 'group_vgk_vjd', type: 'group', label: 'VGK4U - Vijayawada', target: 'VGK4U - Vijayawada', groupName: 'VGK4U - Vijayawada', status: 'sending', msg: 'Broadcasting to group...' },
      { id: 'portal_shoutout', type: 'portal', label: 'VGK4U Login Page Shoutout', target: 'vgk4u.com (Login Banner)', status: 'sending', msg: 'Publishing shoutout...' }
    ];

    let dataUrl = null;
    let blob = null;

    try {
      const canvas = await capturePosterCanvas(container);
      if (canvas) {
        try {
          dataUrl = canvas.toDataURL('image/png');
          blob = await (await fetch(dataUrl)).blob();
        } catch (cErr) {
          console.warn("Poster toDataURL failed:", cErr);
        }
      }
    } catch (capErr) {
      console.warn("capturePosterCanvas error:", capErr);
    }

    if (spinner) spinner.style.display = 'none';
    showLiveDispatchStatusModal(dispatchTargets, partnerName);

    const fetchWithTimeout = async (url, opts = {}, ms = 2500) => {
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

      // 2. Member Direct Send via Scanned Bot
      if (mPhone) {
        try {
          const res = await fetchWithTimeout('http://localhost:5002/api/send-message', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ phone: mPhone, imageUrl: dataUrl, message: shareText })
          });
          const json = await res.json();
          if (json.success) {
            updateDispatchStatus('member', 'sent', 'Delivered via Scanned WhatsApp');
          } else {
            updateDispatchStatus('member', 'error', json.error || 'Bot Error');
          }
        } catch (mErr) {
          updateDispatchStatus('member', 'error', 'WhatsApp Bot Offline (port 5002)');
        }
      } else {
        updateDispatchStatus('member', 'skipped', 'No Phone Number');
      }

      // 3. Senior Direct Send via Scanned Bot
      if (isSeniorVisible && sPhone) {
        try {
          const res = await fetchWithTimeout('http://localhost:5002/api/send-message', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ phone: sPhone, imageUrl: dataUrl, message: shareText })
          });
          const json = await res.json();
          if (json.success) {
            updateDispatchStatus('senior', 'sent', 'Delivered via Scanned WhatsApp');
          } else {
            updateDispatchStatus('senior', 'error', json.error || 'Bot Error');
          }
        } catch (sErr) {
          updateDispatchStatus('senior', 'error', 'WhatsApp Bot Offline');
        }
      } else {
        updateDispatchStatus('senior', 'skipped', !isSeniorVisible ? 'Excluded by toggle' : 'No Senior Phone');
      }

      // 4. VGK4U Official Channel Send
      try {
        const res = await fetchWithTimeout('http://localhost:5002/api/send-group-message', {
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
        const res = await fetchWithTimeout('http://localhost:5002/api/send-group-message', {
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
        const res = await fetchWithTimeout('http://localhost:5002/api/send-group-message', {
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
        const res = await fetchWithTimeout('http://localhost:5002/api/send-group-message', {
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
        const res = await fetchWithTimeout('http://localhost:5002/api/send-group-message', {
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
        const res = await fetchWithTimeout('http://localhost:5002/api/send-group-message', {
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

    } catch (err) {
      if (spinner) spinner.style.display = 'none';
      console.warn("Share default dispatch error:", err);
      dispatchTargets.forEach(t => updateDispatchStatus(t.id, 'error', 'Dispatch Error'));
    }
  }

  async function postPosterAnnouncement() {
    const container = document.getElementById('posterCanvasWrapper');
    if (!container) {
      if (typeof toast === 'function') toast('Poster preview not ready', 'error');
      else alert('Poster preview not ready');
      return;
    }

    const partnerName = (document.getElementById('prevSubtitle')?.textContent || '').trim() || 'Channel Partner';
    const partnerOverall = (document.getElementById('prevHighlight')?.textContent || '').trim() || '';
    const partnerToday = (document.getElementById('prevTotalToday')?.textContent || '').trim() || '';
    const partnerPotential = (document.getElementById('prevPotential')?.textContent || '').trim() || '';

    if (!confirm(`📣 POST ANNOUNCEMENT ON LOGIN SCREEN\n--------------------------------------------------\n• Member Name: ${partnerName}\n• Today's Earning: ${partnerToday}\n• Overall Earning: ${partnerOverall}\n\nDo you want to publish this Achievement Poster announcement to the Login Screen slideshow now?`)) {
      return;
    }

    const spinner = document.getElementById('posterSpinner');
    if (spinner) spinner.style.display = 'flex';

    try {
      const canvas = await capturePosterCanvas(container);
      if (!canvas) throw new Error('Failed to capture poster canvas');

      const dataUrl = canvas.toDataURL('image/png');
      const blob = await (await fetch(dataUrl)).blob();

      let shareText = `🎉 *CONGRATULATIONS TO ${partnerName}!* 🎉\n\n` +
        `👤 *Member Name:* ${partnerName}\n` +
        `💰 *Today's Payout:* ${partnerToday}\n` +
        `📈 *Overall Earning:* ${partnerOverall}\n` +
        `🔮 *Potential Valuation:* ${partnerPotential}\n\n` +
        `🚀 Keep Leading. Keep Inspiring. Keep Growing! — Team VGK4U`;

      const formData = new FormData();
      formData.append('title', `🎉 Achievement Poster: ${partnerName}`);
      formData.append('description', shareText);
      formData.append('category_id', '1');
      formData.append('submission_type', 'photo');
      formData.append('files', blob, `${partnerName.replace(/\s+/g, '_')}_Achievement.png`);

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
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = function(evt) {
      const img = document.getElementById('prevImg');
      const avatar = document.getElementById('prevAvatar');
      if (img) {
        img.src = evt.target.result;
        img.style.display = 'block';
        if (avatar) avatar.style.display = 'none';
      }
    };
    reader.readAsDataURL(file);
  }

  function handleSeniorPhotoUpload(e) {
    const file = e.target.files[0];
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
  }

  // Export functions to global scope
  window.generateMemberPoster = generateMemberPoster;
  window.openAchievementPoster = generateMemberPoster;
  window.openPosterFromUnified = openPosterFromUnified;
  window.capturePosterCanvas = capturePosterCanvas;
  window.downloadPoster = downloadPoster;
  window.sharePoster = sharePoster;
  window.shareOnWhatsApp = shareOnWhatsApp;
  window.shareDefaultChannel = shareDefaultChannel;
  window.testShareToNumber = testShareToNumber;
  window.postPosterAnnouncement = postPosterAnnouncement;
  window.showDirectWaShareDialog = showDirectWaShareDialog;
  window.changeThemePreset = changeThemePreset;
  window.setPosterPresetPeriod = setPosterPresetPeriod;
  window.recalculateTodayPayout = recalculateTodayPayout;
  window.changePayoutDateRange = changePayoutDateRange;
  window.updatePoster = updatePoster;
  window.handleMemberPhotoUpload = handleMemberPhotoUpload;
  window.handleSeniorPhotoUpload = handleSeniorPhotoUpload;
  window._meFormatInr = _meFormatInr;
})();
