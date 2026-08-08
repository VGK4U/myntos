/**
 * MNR Lead Map Location Modal & URL Normalizer
 * Provides interactive map options (Google Maps, Apple Maps, Exact Customer GPS, Copy Link & Address).
 */
(function() {
  function escHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function parseCoordinate(val) {
    if (val === null || val === undefined) return null;
    const s = String(val).trim();
    if (!s || s === '—' || s === 'null' || s === 'undefined') return null;
    const num = parseFloat(s);
    return !isNaN(num) && isFinite(num) ? num : null;
  }

  function isValidUrl(str) {
    if (!str) return false;
    const s = String(str).trim().toLowerCase();
    return s.startsWith('http://') || s.startsWith('https://') || s.startsWith('geo:') || s.startsWith('maps:');
  }

  function normalizeMapData(lead) {
    const lat = parseCoordinate(lead.latitude || lead.lat);
    const lon = parseCoordinate(lead.longitude || lead.lng || lead.lon);
    const hasGps = (lat !== null && lon !== null);

    let rawMapsLink = lead.google_maps_link || lead.maps_link || lead.google_map || '';
    if (rawMapsLink === '—') rawMapsLink = '';

    // Build location string
    const locParts = [lead.address, lead.area, lead.city, lead.state, lead.pincode].filter(p => p && String(p).trim() && String(p).trim() !== '—');
    const formattedAddress = locParts.join(', ');

    let googleMapsUrl = '';
    let appleMapsUrl = '';

    if (hasGps) {
      googleMapsUrl = `https://www.google.com/maps/search/?api=1&query=${lat},${lon}`;
      appleMapsUrl = `https://maps.apple.com/?q=${encodeURIComponent(lead.name || 'Customer Location')}&ll=${lat},${lon}&z=16`;
    } else if (isValidUrl(rawMapsLink)) {
      googleMapsUrl = rawMapsLink.trim();
      appleMapsUrl = `https://maps.apple.com/?q=${encodeURIComponent(rawMapsLink.trim())}`;
    } else if (rawMapsLink.trim()) {
      const queryStr = rawMapsLink.trim();
      googleMapsUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(queryStr)}`;
      appleMapsUrl = `https://maps.apple.com/?q=${encodeURIComponent(queryStr)}`;
    } else if (formattedAddress) {
      googleMapsUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(formattedAddress)}`;
      appleMapsUrl = `https://maps.apple.com/?q=${encodeURIComponent(formattedAddress)}`;
    }

    return {
      hasGps,
      lat,
      lon,
      rawMapsLink,
      formattedAddress,
      googleMapsUrl,
      appleMapsUrl,
      customerName: lead.name || lead.customer_name || 'Customer Lead'
    };
  }

  window.openLeadMapModal = function(lead) {
    if (!lead) return;
    const info = normalizeMapData(lead);

    let modalEl = document.getElementById('mnrLeadMapModal');
    if (!modalEl) {
      modalEl = document.createElement('div');
      modalEl.id = 'mnrLeadMapModal';
      modalEl.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(15,23,42,0.65);backdrop-filter:blur(4px);z-index:99999;display:flex;align-items:center;justify-content:center;padding:16px';
      document.body.appendChild(modalEl);
    }

    const gpsBadgeHtml = info.hasGps ? `
      <div style="background:#ecfdf5;border:1px solid #a7f3d0;padding:10px 14px;border-radius:8px;margin-bottom:14px;display:flex;align-items:center;justify-content:space-between;gap:10px">
        <div>
          <div style="font-size:11px;font-weight:700;color:#047857;text-transform:uppercase;letter-spacing:0.5px">📍 Exact Customer GPS Coordinates</div>
          <div style="font-size:13px;font-weight:600;color:#065f46;margin-top:2px">${info.lat}, ${info.lon}</div>
        </div>
        <button onclick="mnrCopyText('${info.lat}, ${info.lon}', this)" style="background:#10b981;color:#fff;border:none;padding:5px 10px;border-radius:6px;font-weight:600;font-size:11px;cursor:pointer;white-space:nowrap;display:inline-flex;align-items:center;gap:4px">
          <i class="far fa-copy"></i> Copy GPS
        </button>
      </div>` : '';

    const addressHtml = info.formattedAddress ? `
      <div style="background:#f8fafc;border:1px solid #e2e8f0;padding:10px 14px;border-radius:8px;margin-bottom:14px">
        <div style="font-size:11px;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:0.5px">🏡 Customer Address</div>
        <div style="font-size:12px;color:#334155;margin-top:2px;line-height:1.4">${escHtml(info.formattedAddress)}</div>
      </div>` : '';

    modalEl.innerHTML = `
      <div style="background:#ffffff;border-radius:14px;max-width:440px;width:100%;box-shadow:0 20px 25px -5px rgba(0,0,0,0.1),0 10px 10px -5px rgba(0,0,0,0.04);overflow:hidden;animation:mnrPopIn 0.2s cubic-bezier(0.16, 1, 0.3, 1)">
        <div style="background:linear-gradient(135deg, #1e293b, #0f172a);padding:16px 20px;display:flex;align-items:center;justify-content:space-between;color:#fff">
          <div style="display:flex;align-items:center;gap:10px">
            <div style="width:34px;height:34px;border-radius:50%;background:rgba(255,255,255,0.15);display:flex;align-items:center;justify-content:center;color:#38bdf8;font-size:16px">
              <i class="fas fa-map-marked-alt"></i>
            </div>
            <div>
              <h5 style="margin:0;font-size:15px;font-weight:700;line-height:1.2">${escHtml(info.customerName)}</h5>
              <span style="font-size:11px;color:#94a3b8">Customer Map & Location Options</span>
            </div>
          </div>
          <button onclick="document.getElementById('mnrLeadMapModal').style.display='none'" style="background:transparent;border:none;color:#94a3b8;font-size:18px;cursor:pointer;padding:4px;display:flex;align-items:center;justify-content:center">
            <i class="fas fa-times"></i>
          </button>
        </div>
        <div style="padding:18px 20px">
          ${gpsBadgeHtml}
          ${addressHtml}

          <div style="display:flex;flex-direction:column;gap:10px;margin-top:10px">
            ${info.googleMapsUrl ? `
              <a href="${escHtml(info.googleMapsUrl)}" target="_blank" rel="noopener noreferrer" style="background:#ea4335;color:#ffffff;text-decoration:none;padding:11px 16px;border-radius:9px;font-weight:600;font-size:13px;display:flex;align-items:center;justify-content:space-between;box-shadow:0 2px 4px rgba(234,67,53,0.25);transition:all 0.15s">
                <span style="display:flex;align-items:center;gap:8px">
                  <i class="fab fa-google" style="font-size:16px"></i> Open in Google Maps
                </span>
                <i class="fas fa-external-link-alt" style="font-size:12px;opacity:0.8"></i>
              </a>` : ''}

            ${info.appleMapsUrl ? `
              <a href="${escHtml(info.appleMapsUrl)}" target="_blank" rel="noopener noreferrer" style="background:#000000;color:#ffffff;text-decoration:none;padding:11px 16px;border-radius:9px;font-weight:600;font-size:13px;display:flex;align-items:center;justify-content:space-between;box-shadow:0 2px 4px rgba(0,0,0,0.2);transition:all 0.15s">
                <span style="display:flex;align-items:center;gap:8px">
                  <i class="fab fa-apple" style="font-size:17px"></i> Open in Apple Maps (iOS)
                </span>
                <i class="fas fa-external-link-alt" style="font-size:12px;opacity:0.8"></i>
              </a>` : ''}

            <button onclick="mnrCopyText('${escHtml(info.googleMapsUrl)}', this)" style="background:#f1f5f9;color:#334155;border:1px solid #cbd5e1;padding:10px 16px;border-radius:9px;font-weight:600;font-size:13px;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:6px">
              <i class="far fa-copy"></i> Copy Google Maps URL
            </button>
          </div>
        </div>
        <div style="background:#f8fafc;padding:12px 20px;border-top:1px solid #f1f5f9;text-align:right">
          <button onclick="document.getElementById('mnrLeadMapModal').style.display='none'" style="background:#64748b;color:#fff;border:none;padding:7px 16px;border-radius:6px;font-size:12px;font-weight:600;cursor:pointer">
            Close
          </button>
        </div>
      </div>`;

    modalEl.style.display = 'flex';
  };

  window.mnrCopyText = function(text, btn) {
    if (!text) return;
    const oldText = btn.innerHTML;
    const copyPromise = navigator.clipboard && navigator.clipboard.writeText ?
      navigator.clipboard.writeText(text) :
      new Promise((resolve, reject) => {
        try {
          const ta = document.createElement('textarea');
          ta.value = text;
          ta.style.position = 'fixed';
          ta.style.opacity = '0';
          document.body.appendChild(ta);
          ta.select();
          document.execCommand('copy');
          document.body.removeChild(ta);
          resolve();
        } catch(e) { reject(e); }
      });

    copyPromise.then(() => {
      btn.innerHTML = `<i class="fas fa-check"></i> Copied!`;
      setTimeout(() => { btn.innerHTML = oldText; }, 2000);
    }).catch(err => {
      alert('Copied: ' + text);
    });
  };
})();
