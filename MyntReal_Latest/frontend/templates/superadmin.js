// Super Admin HTML Template Module
// Extracted from static-server.js for modular architecture

const BUILD_ID = process.env.FRONTEND_BUILD_ID || String(Date.now());


// SERVER-SIDE JavaScript String Escaping - For embedding values in inline <script> tags
function escapeJSServer(str) {
  if (!str) return '';
  return String(str)
    .replace(/\\/g, '\\\\')   // Backslash
    .replace(/'/g, "\\'")     // Single quote  
    .replace(/"/g, '\\"')     // Double quote
    .replace(/\n/g, '\\n')    // Newline
    .replace(/\r/g, '\\r')    // Carriage return
    .replace(/\t/g, '\\t');   // Tab
}
const createSuperAdminHTML = (title, content, sessionToken = '') => `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    <meta name="build-version" content="${BUILD_ID}">
    <title>${title} - Super Admin</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f5f7fa; }
        
        /* Header - Purple/Indigo theme for Super Admin */
        .top-header { 
            position: fixed; top: 0; left: 0; right: 0; height: 60px; 
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); 
            color: white; z-index: 1000; box-shadow: 0 2px 10px rgba(0,0,0,0.1); 
            display: flex !important; align-items: center; padding: 0 20px; justify-content: space-between;
        }
        .header-left { display: flex; align-items: center; gap: 15px; }
        .hamburger { cursor: pointer; font-size: 24px; }
        .header-logo { font-size: 20px; font-weight: bold; }
        .header-right { display: flex; align-items: center; gap: 15px; }
        .user-name-display {
            display: flex !important; align-items: center; gap: 8px;
            color: white; padding: 8px 16px; background: rgba(255,255,255,0.15);
            border-radius: 20px; font-weight: 500; margin-right: 5px;
        }
        .user-name-display i { font-size: 18px; }
        .user-name-display span { font-size: 14px; }
        .profile-dropdown { position: relative; }
        .profile-btn { 
            background: rgba(255,255,255,0.2); border: none; color: white; 
            padding: 8px 15px; border-radius: 8px; cursor: pointer; display: flex; 
            align-items: center; gap: 8px;
        }
        .profile-btn:hover { background: rgba(255,255,255,0.3); }
        .dropdown-menu-custom { 
            position: absolute; top: 50px; right: 0; background: white; 
            min-width: 200px; border-radius: 8px; box-shadow: 0 5px 20px rgba(0,0,0,0.15); 
            display: none; z-index: 1001;
        }
        .dropdown-menu-custom.show { display: block; }
        .dropdown-item-custom { 
            padding: 12px 20px; color: #333; text-decoration: none; 
            display: flex !important; align-items: center; gap: 10px; border-bottom: 1px solid #eee;
        }
        .dropdown-item-custom:hover { background: #f8f9fa; }
        .dropdown-item-custom:last-child { border-bottom: none; }
        
        /* Header New Features - Calendar, Notifications, WhatsApp, Profile Photo */
        .header-calendar-btn, .header-notification-btn, .header-whatsapp-btn {
            background: rgba(255,255,255,0.2); border: none; color: white;
            padding: 8px 12px; border-radius: 8px; cursor: pointer;
            transition: all 0.3s; position: relative;
        }
        .header-calendar-btn:hover, .header-notification-btn:hover, .header-whatsapp-btn:hover {
            background: rgba(255,255,255,0.3); transform: translateY(-2px);
        }
        .header-calendar-btn { display: flex; align-items: center; gap: 5px; }
        .header-notification-btn .notification-badge {
            position: absolute; top: 2px; right: 2px;
            background: #ef4444; color: white; border-radius: 10px;
            padding: 2px 6px; font-size: 10px; font-weight: bold;
        }
        .header-profile-photo {
            width: 60px; height: 60px; border-radius: 50%;
            object-fit: cover; border: 2px solid rgba(255,255,255,0.5);
            cursor: pointer; transition: all 0.3s;
        }
        .header-profile-photo:hover { border-color: white; transform: scale(1.05); }
        .header-profile-initials {
            width: 60px; height: 60px; border-radius: 50%;
            background: linear-gradient(135deg, #8b5cf6 0%, #ec4899 100%);
            color: white; display: flex; align-items: center; justify-content: center;
            font-weight: bold; font-size: 22px; border: 2px solid rgba(255,255,255,0.5);
            cursor: pointer; transition: all 0.3s;
        }
        .header-profile-initials:hover { border-color: white; transform: scale(1.05); }
        .header-last-login {
            font-size: 11px; opacity: 0.8; margin-left: 3px; font-style: italic;
        }
        
        /* Calendar Dropdown */
        .calendar-dropdown {
            position: absolute; top: 50px; right: 0;
            background: white; border-radius: 12px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.15);
            padding: 15px; display: none; z-index: 1001;
            min-width: 300px; color: #333;
        }
        .calendar-dropdown.show { display: block; }
        .calendar-header {
            display: flex !important; justify-content-space-between; align-items: center;
            margin-bottom: 15px;
        }
        .calendar-header button {
            background: #f3f4f6; border: none; padding: 5px 10px;
            border-radius: 6px; cursor: pointer;
        }
        .calendar-header button:hover { background: #e5e7eb; }
        .calendar-grid {
            display: grid; grid-template-columns: repeat(7, 1fr);
            gap: 5px; margin-bottom: 10px;
        }
        .calendar-day {
            padding: 8px; text-align: center; border-radius: 6px;
            font-size: 14px; cursor: pointer;
        }
        .calendar-day:hover { background: #f3f4f6; }
        .calendar-day.today { background: #1e40af; color: white; font-weight: bold; }
        .calendar-day.other-month { opacity: 0.3; }
        .calendar-footer {
            text-align: center; padding-top: 10px;
            border-top: 1px solid #e5e7eb;
        }
        .calendar-footer button {
            background: #1e40af; color: white; border: none;
            padding: 6px 15px; border-radius: 6px; cursor: pointer;
        }
        .calendar-footer button:hover { background: #1e3a8a; }
        
        /* Notification Dropdown */
        .notification-dropdown {
            position: absolute; top: 50px; right: 0;
            background: white; border-radius: 12px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.15);
            display: none; z-index: 1001;
            min-width: 320px; max-width: 400px;
            max-height: 400px; overflow-y: auto;
        }
        .notification-dropdown.show { display: block; }
        .notification-header {
            padding: 15px; border-bottom: 1px solid #e5e7eb;
            font-weight: 600; color: #333;
        }
        .notification-item {
            padding: 12px 15px; border-bottom: 1px solid #f3f4f6;
            cursor: pointer; transition: background 0.3s;
        }
        .notification-item:hover { background: #f9fafb; }
        .notification-item.unread { background: #eff6ff; }
        .notification-icon { display: inline-block; width: 30px; height: 30px;
            border-radius: 50%; text-align: center; line-height: 30px;
            margin-right: 10px;
        }
        .notification-icon.income { background: #d1fae5; color: #059669; }
        .notification-icon.team { background: #dbeafe; color: #1e40af; }
        .notification-icon.system { background: #fef3c7; color: #d97706; }
        .notification-empty {
            padding: 40px 20px; text-align: center; color: #9ca3af;
        }
        
        /* WhatsApp Share Buttons */
        .whatsapp-share-container {
            display: flex !important; gap: 8px; align-items: center;
        }
        .whatsapp-icon {
            color: #25D366; font-size: 20px;
        }
        .share-btn {
            background: #25D366; color: white; border: none;
            padding: 6px 12px; border-radius: 6px; cursor: pointer;
            font-size: 12px; display: flex; align-items: center; gap: 5px;
            transition: all 0.3s;
        }
        .share-btn:hover { background: #128C7E; transform: translateY(-2px); }
        .copy-btn {
            background: rgba(255,255,255,0.2); color: white; border: 1px solid rgba(255,255,255,0.3);
            padding: 6px 12px; border-radius: 6px; cursor: pointer;
            font-size: 12px; display: flex; align-items: center; gap: 5px;
            transition: all 0.3s;
        }
        .copy-btn:hover { background: rgba(255,255,255,0.3); }
        
        /* Sidebar - Always visible scrollbar */
        .sidebar { 
            position: fixed; top: 60px; left: 0; width: 260px; height: calc(100vh - 60px); 
            background: white; box-shadow: 2px 0 10px rgba(0,0,0,0.05); 
            overflow-y: scroll !important; transition: transform 0.3s; z-index: 999;
            scrollbar-width: thin; scrollbar-color: #d97706 #f3f4f6;
        }
        .sidebar::-webkit-scrollbar { width: 8px; display: block !important; }
        .sidebar::-webkit-scrollbar-track { background: #f3f4f6; }
        .sidebar::-webkit-scrollbar-thumb { background: #d97706; border-radius: 4px; min-height: 40px; }
        .sidebar::-webkit-scrollbar-thumb:hover { background: #b45309; }
        .sidebar.collapsed { transform: translateX(-100%); }
        .sidebar-menu { list-style: none; padding: 10px 0; }
        .sidebar-item { margin: 2px 0; }
        .sidebar-link { 
            display: flex !important; align-items: center; gap: 12px; padding: 12px 20px; 
            color: #555; text-decoration: none; transition: all 0.3s;
        }
        .sidebar-link:hover, .sidebar-link.active { 
            background: linear-gradient(90deg, #6366f1 0%, #8b5cf6 100%); 
            color: white; border-left: 4px solid #7c3aed;
        }
        .sidebar-link i { width: 20px; text-align: center; }
        
        /* Collapsible Menu Groups */
        .menu-group-header {
            display: flex !important; align-items: center; justify-content: space-between;
            padding: 12px 20px; color: #555; cursor: pointer;
            transition: all 0.3s; font-weight: 500;
        }
        .menu-group-header:hover { background: #f8f9fa; }
        .menu-group-items {
            list-style: none !important; 
            padding-left: 0 !important; 
            max-height: 0 !important;
            overflow: hidden !important; 
            transition: max-height 0.3s ease !important;
            visibility: hidden !important;
            display: block !important;
        }
        .menu-group-items.expanded { 
            max-height: none !important; 
            visibility: visible !important;
        }
        .menu-group-items .sidebar-link {
            padding-left: 52px; font-size: 14px;
        }
        
        /* Main Content */
        .main-content { 
            margin-left: 260px; margin-top: 60px; padding: 30px; 
            min-height: calc(100vh - 60px); transition: margin-left 0.3s;
        }
        .main-content.expanded { margin-left: 0; }
        
        /* Cards */
        .card { border: none; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
        .card-header { background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); color: white; border-radius: 12px 12px 0 0 !important; }
        
        /* Responsive */
        @media (max-width: 768px) {
            .sidebar { 
                transform: translateX(-100%); 
                z-index: 1050;
                box-shadow: 2px 0 10px rgba(0,0,0,0.3);
            }
            .sidebar.show { 
                transform: translateX(0); 
            }
            .main-content { 
                margin-left: 0; 
                padding: 10px;
            }
            .top-header {
                padding: 0 10px;
            }
            .header-logo span {
                display: none;
            }
            /* Hide MNR logo and calendar date in mobile to show full name */
            .header-logo img {
                display: none !important;
            }
            .header-calendar-btn {
                display: none !important;
            }
            /* Make name display full width */
            .user-name-display {
                flex: 1;
                text-align: center;
            }
            .card {
                margin-bottom: 12px;
            }
            
            /* Fix data overlap ONLY in dashboard overview - make columns stack vertically on mobile */
            #dashboard-overview-mobile .card-body .row > [class*="col-"] {
                flex: 0 0 100%;
                max-width: 100%;
                margin-bottom: 8px;
            }
            
            #dashboard-overview-mobile .card-body {
                padding: 8px !important;
            }
            
            /* Smaller fonts for dashboard overview cards only */
            #dashboard-overview-mobile .card-body .text-center small {
                font-size: 0.6rem !important;
                word-wrap: break-word;
                overflow-wrap: break-word;
                display: block;
                line-height: 1.3;
            }
            #dashboard-overview-mobile .card-body .text-center strong {
                font-size: 0.7rem !important;
                display: block;
                margin-top: 2px;
            }
            
            #dashboard-overview-mobile .card-header h6 {
                font-size: 0.8rem !important;
            }
            
            /* Tables remain unchanged */
            .table-responsive {
                font-size: 11px;
                overflow-x: auto;
            }
            .table-responsive table {
                min-width: 100%;
            }
            .table th, .table td {
                padding: 6px 3px;
                font-size: 10px;
                white-space: nowrap;
            }
        }
    </style>
</head>
<body>
    <script>
        const API_BASE_URL = '';
        const sessionToken = '${escapeJSServer(sessionToken)}';
        console.log('🔗 API Base URL: Using frontend proxy (relative URLs)');
        console.log('🔑 Build ID: ${BUILD_ID}');
        
        // Browser-side escaping functions
        function escapeHTML(str) {
          if (!str) return '';
          return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
        }
        function escapeJS(str) {
          if (!str) return '';
          return String(str).replace(/\\\\/g, '\\\\\\\\').replace(/'/g, "\\\\'").replace(/"/g, '\\\\"').replace(/\\n/g, '\\\\n').replace(/\\r/g, '\\\\r').replace(/\\t/g, '\\\\t');
        }
        
        // DC Protocol (Dec 28, 2025): Fetch and display user name and ID in header with robust fallback
        (async () => {
            const displayNameEl = document.getElementById('displayName');
            const displayIdEl = document.getElementById('displayUserId');
            
            try {
                const response = await fetch(API_BASE_URL + '/api/v1/auth/me', {
                    headers: { 'Authorization': 'Bearer ' + sessionToken }
                });
                
                if (!response.ok) {
                    console.warn('[DC-Header] Auth API returned:', response.status);
                    return;
                }
                
                const data = await response.json();
                const user = data.data || data.employee || data;
                
                if (user) {
                    // Update name - try multiple fields for robustness
                    const userName = user.name || user.full_name || user.display_name || 'Super Admin';
                    if (displayNameEl) {
                        displayNameEl.textContent = userName;
                    }
                    
                    // Update ID - try multiple fields
                    const userId = user.id || user.mnr_id || user.user_id || '';
                    if (displayIdEl && userId) {
                        displayIdEl.textContent = userId;
                    }
                    
                    console.log('[DC-Header] Super Admin info loaded:', userName, '(' + userId + ')');
                }
            } catch (err) {
                console.error('[DC-Header] Failed to load user info:', err);
            }
        })();
    </script>
    
    <!-- Header -->
    <div class="top-header">
        <div class="header-left">
            <div class="hamburger" onclick="toggleSidebar()">
                <i class="fas fa-bars"></i>
            </div>
            <div class="header-logo">⭐ Super Admin Panel</div>
        </div>
        <div class="header-right">
            <div class="user-name-display" id="headerUserName">
                <i class="fas fa-crown"></i>
                <span id="displayName">Loading...</span>
            </div>
            <div class="profile-dropdown">
                <button class="profile-btn" onclick="toggleProfileMenu()">
                    <i class="fas fa-crown"></i>
                    <span>Super Admin</span>
                    <i class="fas fa-chevron-down"></i>
                </button>
                <div class="dropdown-menu-custom" id="profileMenu">
                    <a href="/superadmin/dashboard" class="dropdown-item-custom">
                        <i class="fas fa-tachometer-alt"></i> Dashboard
                    </a>
                    <a href="/user/change-password" class="dropdown-item-custom">
                        <i class="fas fa-key"></i> Change Password
                    </a>
                    <a href="/login?v=${BUILD_ID}" class="dropdown-item-custom">
                        <i class="fas fa-sign-out-alt"></i> Logout
                    </a>
                </div>
            </div>
        </div>
    </div>

    <!-- Super Admin Sidebar -->
    <div class="sidebar" id="sidebar">
        <ul class="sidebar-menu">
            <!-- Dashboard -->
            <li class="sidebar-item">
                <a href="/superadmin/dashboard" class="sidebar-link">
                    <i class="fas fa-tachometer-alt"></i> Dashboard
                </a>
            </li>
            
            <!-- Coupon Modules Group -->
            <li class="sidebar-item">
                <div class="menu-group-header" onclick="toggleMenuGroup('superadmin-coupons')">
                    <span><i class="fas fa-ticket-alt"></i> Coupon Modules</span>
                    <i class="fas fa-chevron-down" id="superadmin-coupons-chevron"></i>
                </div>
                <ul class="menu-group-items" id="superadmin-coupons-items">
                    <li><a href="/admin/coupons/buy" class="sidebar-link">Buy Coupon</a></li>
                    <li><a href="/admin/coupons/activate" class="sidebar-link">Activate Coupon</a></li>
                    <li><a href="/admin/coupons/status" class="sidebar-link">Coupon Status</a></li>
                    <li><a href="/admin/coupons/progress" class="sidebar-link">Coupon Progress</a></li>
                    <li><a href="/admin/coupons/transfer" class="sidebar-link">Coupon Transfer</a></li>
                </ul>
            </li>
            
            <!-- Members Group -->
            <li class="sidebar-item">
                <div class="menu-group-header" onclick="toggleMenuGroup('superadmin-members')">
                    <span><i class="fas fa-users"></i> Members</span>
                    <i class="fas fa-chevron-down" id="superadmin-members-chevron"></i>
                </div>
                <ul class="menu-group-items" id="superadmin-members-items">
                    <li><a href="/admin/members/all" class="sidebar-link">All Members</a></li>
                    <li><a href="/admin/members/direct-referrals" class="sidebar-link">Direct Facilitations</a></li>
                    <li><a href="/admin/members/picture-view" class="sidebar-link">Picture View</a></li>
                    <li><a href="/admin/members/ved-team" class="sidebar-link">Ved Team</a></li>
                </ul>
            </li>
            
            <!-- Income Approval Group - Super Admin Level -->
            <li class="sidebar-item">
                <div class="menu-group-header" onclick="toggleMenuGroup('superadmin-income-approval')">
                    <span><i class="fas fa-clipboard-check"></i> 💰 Income Approval</span>
                    <i class="fas fa-chevron-down" id="superadmin-income-approval-chevron"></i>
                </div>
                <ul class="menu-group-items" id="superadmin-income-approval-items">
                    <li><a href="/admin/income-pending" class="sidebar-link">⏳ Income Pending (View)</a></li>
                    <li><a href="/admin/income-verified" class="sidebar-link">✅ Income Verified (Approve)</a></li>
                    <li><a href="/rvz/income-history-supreme" class="sidebar-link">📋 Income History</a></li>
                </ul>
            </li>
            
            <!-- Earnings Group -->
            <li class="sidebar-item">
                <div class="menu-group-header" onclick="toggleMenuGroup('superadmin-earnings')">
                    <span><i class="fas fa-dollar-sign"></i> Earnings</span>
                    <i class="fas fa-chevron-down" id="superadmin-earnings-chevron"></i>
                </div>
                <ul class="menu-group-items" id="superadmin-earnings-items">
                    <li><a href="/admin/earnings/summary" class="sidebar-link">Earnings Summary</a></li>
                    <li><a href="/admin/earnings/direct-referral" class="sidebar-link">Direct Facilitation</a></li>
                    <li><a href="/admin/earnings/matching-referral" class="sidebar-link">Group Performance Recognition</a></li>
                    <li><a href="/admin/earnings/ved-income" class="sidebar-link">VED Leadership Recognition</a></li>
                    <li><a href="/admin/earnings/gurudakshina" class="sidebar-link">Gurudakshina</a></li>
                    <li><a href="/admin/earnings/withdrawals" class="sidebar-link">Withdrawals</a></li>
                </ul>
            </li>
            
            <!-- Withdrawal Approvals Group -->
            <li class="sidebar-item">
                <div class="menu-group-header" onclick="toggleMenuGroup('superadmin-withdrawal')">
                    <span><i class="fas fa-check-double"></i> Withdrawal Approvals</span>
                    <i class="fas fa-chevron-down" id="superadmin-withdrawal-chevron"></i>
                </div>
                <ul class="menu-group-items" id="superadmin-withdrawal-items">
                    <li><a href="/superadmin/withdrawal/approvals" class="sidebar-link">🔍 Approval Queue</a></li>
                    <li><a href="/superadmin/withdrawal/history" class="sidebar-link">📜 Approval History</a></li>
                </ul>
            </li>
            
            <!-- Awards & Bonanza Group -->
            <li class="sidebar-item">
                <div class="menu-group-header" onclick="toggleMenuGroup('superadmin-awards')">
                    <span><i class="fas fa-trophy"></i> Awards & Bonanza</span>
                    <i class="fas fa-chevron-down" id="superadmin-awards-chevron"></i>
                </div>
                <ul class="menu-group-items" id="superadmin-awards-items">
                    <li><a href="/superadmin/awards/approval-queue" class="sidebar-link">✅ Approval Queue</a></li>
                    <li><a href="/admin/awards/all" class="sidebar-link">Awards</a></li>
                    <li><a href="/admin/awards/bonanza" class="sidebar-link">Bonanza Awards</a></li>
                    <li><a href="/admin/bonanza-claims" class="sidebar-link">🎁 Bonanza Claims</a></li>
                </ul>
            </li>
            
            <!-- Incentives Group -->
            <li class="sidebar-item">
                <div class="menu-group-header" onclick="toggleMenuGroup('superadmin-incentives')">
                    <span><i class="fas fa-coins"></i> Incentives</span>
                    <i class="fas fa-chevron-down" id="superadmin-incentives-chevron"></i>
                </div>
                <ul class="menu-group-items" id="superadmin-incentives-items">
                    <li><a href="/staff/incentives/points" class="sidebar-link">🎯 MNR Points</a></li>
                </ul>
            </li>
            
            <!-- RVZ Earnings Group -->
            <li class="sidebar-item">
                <div class="menu-group-header" onclick="toggleMenuGroup('superadmin-rvz')">
                    <span><i class="fas fa-gem"></i> RVZ Earnings</span>
                    <i class="fas fa-chevron-down" id="superadmin-rvz-chevron"></i>
                </div>
                <ul class="menu-group-items" id="superadmin-rvz-items">
                    <li><a href="/admin/rvz/all-benefits" class="sidebar-link">All Benefits (7 Types)</a></li>
                    <li><a href="/admin/rvz/ev-discount-training" class="sidebar-link">EV Discount & Training</a></li>
                    <li><a href="/admin/rvz/referral-income" class="sidebar-link">My Referral Income</a></li>
                    <li><a href="/admin/rvz/insurance-earnings" class="sidebar-link">Insurance Earnings (RVZ Care)</a></li>
                    <li><a href="/admin/rvz/franchise-earnings" class="sidebar-link">Franchise Earnings</a></li>
                    <li><a href="/admin/rvz/fleet-orders" class="sidebar-link">Fleet Orders (Royal Ride)</a></li>
                </ul>
            </li>
            
            <!-- Members Management Group -->
            <li class="sidebar-item">
                <div class="menu-group-header" onclick="toggleMenuGroup('superadmin-members-mgmt')">
                    <span><i class="fas fa-users-cog"></i> Members Management</span>
                    <i class="fas fa-chevron-down" id="superadmin-members-mgmt-chevron"></i>
                </div>
                <ul class="menu-group-items" id="superadmin-members-mgmt-items">
                    <li><a href="/superadmin/users" class="sidebar-link">All Users</a></li>
                    <li><a href="/superadmin/user-status" class="sidebar-link">User Status</a></li>
                </ul>
            </li>
            
            <!-- DC Protocol Dec 23, 2025: Announcements Group - Skip Level Manager access -->
            <li class="sidebar-item">
                <div class="menu-group-header" onclick="toggleMenuGroup('superadmin-announcements')">
                    <span><i class="fas fa-bullhorn"></i> 📢 Announcements</span>
                    <i class="fas fa-chevron-down" id="superadmin-announcements-chevron"></i>
                </div>
                <ul class="menu-group-items" id="superadmin-announcements-items">
                    <li><a href="/admin/announcements/view" class="sidebar-link">📋 View Announcements</a></li>
                    <li><a href="/admin/feedback/pending" class="sidebar-link">⏳ Pending Approvals</a></li>
                    <li><a href="/superadmin/announcement/create" class="sidebar-link">✍️ Create Announcement</a></li>
                </ul>
            </li>
            
            <!-- Admin Functions Group -->
            <li class="sidebar-item">
                <div class="menu-group-header" onclick="toggleMenuGroup('superadmin-functions')">
                    <span><i class="fas fa-cog"></i> Super Admin Functions</span>
                    <i class="fas fa-chevron-down" id="superadmin-functions-chevron"></i>
                </div>
                <ul class="menu-group-items" id="superadmin-functions-items">
                    <li><a href="/admin/kyc-management" class="sidebar-link">🔐 KYC Management</a></li>
                    <li><a href="/admin/members/search" class="sidebar-link">🔍 Search Members</a></li>
                    <li><a href="/admin/birthdays" class="sidebar-link">🎂 Birthday Details</a></li>
                    <li><a href="/admin/bank-pending" class="sidebar-link">🏦 Bank Pending</a></li>
                    <li><a href="/admin/bank-all" class="sidebar-link">💳 All Bank Details</a></li>
                    <li><a href="/admin/pin-review" class="sidebar-link">🔑 PIN Review</a></li>
                    <li><a href="/admin/password-reset" class="sidebar-link">🔐 Password Reset</a></li>
                    <li><a href="/admin/reports" class="sidebar-link">📊 Reports</a></li>
                    <li><a href="/admin/emergency-wallet" class="sidebar-link">💰 Emergency Wallet</a></li>
                    <li><a href="/staff/accounts/expense-categories" class="sidebar-link">📝 Expense Categories</a></li>
                    <li><a href="/superadmin/global-config" class="sidebar-link">⚙️ Global Config</a></li>
                    <li><a href="/superadmin/system-health" class="sidebar-link">🏥 System Health</a></li>
                    <li><a href="/superadmin/red-id-oversight" class="sidebar-link">👁️ Red ID Oversight</a></li>
                    <li><a href="/superadmin/placement-approvals" class="sidebar-link">📍 Placement Approvals</a></li>
                    <li><a href="/admin/banners-management" class="sidebar-link">📢 Banners</a></li>
                    <li><a href="/admin/popups" class="sidebar-link">🔔 Popups</a></li>
                </ul>
            </li>
            
            <!-- Log Reports -->
            <li class="sidebar-item">
                <a href="/superadmin/log-reports" class="sidebar-link">
                    <i class="fas fa-file-alt"></i> Log Reports
                </a>
            </li>
            
            <!-- Support Tickets Group - DC Protocol Dec 23, 2025 -->
            <li class="sidebar-item">
                <div class="menu-group-header" onclick="toggleMenuGroup('superadmin-tickets')">
                    <span><i class="fas fa-ticket-alt"></i> 🎫 Support Tickets</span>
                    <i class="fas fa-chevron-down" id="superadmin-tickets-chevron"></i>
                </div>
                <ul class="menu-group-items" id="superadmin-tickets-items">
                    <li><a href="/admin/tickets-management" class="sidebar-link">🎫 Tickets Management</a></li>
                    <li><a href="/admin/tickets-assigned" class="sidebar-link">📌 Assigned Tickets</a></li>
                </ul>
            </li>
        </ul>
    </div>

    <!-- Main Content -->
    <div class="main-content" id="mainContent">
        <!-- Quick Navigation - Dashboard Button -->
        <div class="mb-3">
            <a href="/superadmin/dashboard" class="btn btn-sm btn-outline-primary">
                <i class="fas fa-tachometer-alt"></i> Go to Super Admin Dashboard
            </a>
        </div>
        ${content}
    </div>

    <script>
        function toggleSidebar() {
            const sidebar = document.getElementById('sidebar');
            const mainContent = document.getElementById('mainContent');
            
            // For mobile: toggle 'show' class
            if (window.innerWidth <= 768) {
                sidebar.classList.toggle('show');
            } else {
                // For desktop: toggle 'collapsed' class
                sidebar.classList.toggle('collapsed');
                if (sidebar.classList.contains('collapsed')) {
                    mainContent.classList.add('expanded');
                } else {
                    mainContent.classList.remove('expanded');
                }
            }
        }
        
        // Close sidebar when clicking outside on mobile
        document.addEventListener('DOMContentLoaded', function() {
            const sidebar = document.getElementById('sidebar');
            const mainContent = document.getElementById('mainContent');
            
            mainContent.addEventListener('click', function() {
                if (window.innerWidth <= 768 && sidebar.classList.contains('show')) {
                    sidebar.classList.remove('show');
                }
            });
        });

        window.toggleProfileMenu = function() {
            const menu = document.getElementById('profileMenu');
            menu.classList.toggle('show');
        }
        
        function toggleMenuGroup(groupId) {
            const items = document.getElementById(groupId + '-items');
            const chevron = document.getElementById(groupId + '-chevron');
            items.classList.toggle('expanded');
            chevron.classList.toggle('fa-chevron-down');
            chevron.classList.toggle('fa-chevron-up');
            
            // Save menu state
            saveMenuState(groupId, items.classList.contains('expanded'));
        }

        function saveMenuState(groupId, isExpanded) {
            try {
                let expandedGroups = JSON.parse(sessionStorage.getItem('expandedMenuGroups') || '{}');
                expandedGroups[groupId] = isExpanded;
                sessionStorage.setItem('expandedMenuGroups', JSON.stringify(expandedGroups));
            } catch (e) {
                console.error('Error saving menu state:', e);
            }
        }

        function restoreMenuState() {
            const currentPath = window.location.pathname;
            if (!currentPath.includes('/dashboard')) {
                try {
                    const expandedGroups = JSON.parse(sessionStorage.getItem('expandedMenuGroups') || '{}');
                    for (const [groupId, isExpanded] of Object.entries(expandedGroups)) {
                        if (isExpanded) {
                            const items = document.getElementById(groupId + '-items');
                            const chevron = document.getElementById(groupId + '-chevron');
                            if (items && chevron) {
                                items.classList.add('expanded');
                                chevron.classList.remove('fa-chevron-down');
                                chevron.classList.add('fa-chevron-up');
                            }
                        }
                    }
                } catch (e) {
                    console.error('Error restoring menu state:', e);
                }
            } else {
                sessionStorage.removeItem('expandedMenuGroups');
            }
        }

        // Close dropdown when clicking outside
        document.addEventListener('click', function(event) {
            const dropdown = document.querySelector('.profile-dropdown');
            const menu = document.getElementById('profileMenu');
            if (!dropdown.contains(event.target)) {
                menu.classList.remove('show');
            }
        });

        // Restore menu state on page load
        restoreMenuState();

        // Auto-close sidebar on mobile when clicking main content
        const mainContent = document.getElementById('mainContent');
        const sidebar = document.getElementById('sidebar');
        mainContent.addEventListener('click', function() {
            if (window.innerWidth <= 768 && !sidebar.classList.contains('collapsed')) {
                sidebar.classList.add('collapsed');
                mainContent.classList.add('expanded');
            }
        });

        // Highlight active menu item
        const currentPath = window.location.pathname;
        document.querySelectorAll('.sidebar-link').forEach(link => {
            if (link.getAttribute('href').includes(currentPath)) {
                link.classList.add('active');
            }
        });
    </script>
    
    <!-- Global Variables for Admin Pages -->
    <script>
        window.BACKEND_URL = '/api/v1';
        window.sessionToken = '${sessionToken}';
        window.currentUserId = null;
        try {
            const sessionData = sessionStorage.getItem('adminUserData');
            if (sessionData) {
                const userData = JSON.parse(sessionData);
                window.currentUserId = userData.userId || userData.mnr_id || userData.id;
            }
        } catch (e) { console.error('Error loading user data:', e); }
    </script>
    
    <!-- Bootstrap JavaScript Bundle -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script src="/auto-logout.js"></script>
</body>
</html>`;


module.exports = { createSuperAdminHTML, BUILD_ID };
