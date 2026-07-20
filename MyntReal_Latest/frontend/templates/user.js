// User HTML Template Module
// Extracted from static-server.js for modular architecture

const BUILD_ID = process.env.FRONTEND_BUILD_ID || String(Date.now());

const createHTML = (title, content, sessionToken = '') => `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes">
    <title>${title} - MNR Membership & Business Facilitation Platform</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <link href="/public/css/dark-theme.css" rel="stylesheet">
    <link href="/public/css/light-theme.css" rel="stylesheet">
    <script src="/public/js/theme-manager.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f5f7fa; }
        
        /* Header */
        .top-header { 
            position: fixed; top: 0; left: 0; right: 0; height: 60px; 
            background: linear-gradient(135deg, #059669 0%, #1e40af 100%); 
            color: white; z-index: 1000; box-shadow: 0 2px 10px rgba(0,0,0,0.1); 
            display: flex !important; align-items: center; padding: 0 20px; justify-content: space-between;
        }
        .header-left { display: flex; align-items: center; gap: 15px; }
        .hamburger { cursor: pointer; font-size: 24px; }
        .header-logo { font-size: 16px; font-weight: bold; display: flex; align-items: center; gap: 10px; }
        .header-logo img { height: 40px; }
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
        
        /* Sidebar */
        .sidebar { 
            position: fixed; top: 60px; left: 0; width: 260px; height: calc(100vh - 60px); 
            background: white; box-shadow: 2px 0 10px rgba(0,0,0,0.05); 
            overflow-y: auto !important; transition: transform 0.3s; z-index: 999;
            scrollbar-width: thin; scrollbar-color: #d97706 #f3f4f6;
        }
        .sidebar::-webkit-scrollbar { width: 6px; }
        .sidebar::-webkit-scrollbar-track { background: #f3f4f6; }
        .sidebar::-webkit-scrollbar-thumb { background: #d97706; border-radius: 3px; }
        .sidebar::-webkit-scrollbar-thumb:hover { background: #b45309; }
        .sidebar.collapsed { transform: translateX(-100%); }
        .sidebar-menu { list-style: none; padding: 10px 0; }
        .sidebar-item { margin: 2px 0; }
        .sidebar-link { 
            display: flex !important; align-items: center; gap: 12px; padding: 12px 20px; 
            color: #555; text-decoration: none; transition: all 0.3s;
        }
        .sidebar-link:hover, .sidebar-link.active { 
            background: linear-gradient(90deg, #059669 0%, #1e40af 100%); 
            color: white; border-left: 4px solid #047857;
        }
        .sidebar-link i { width: 20px; text-align: center; }
        
        /* Grouped Menu Styles */
        .menu-group-header {
            display: flex !important; align-items: center; justify-content: space-between;
            padding: 12px 20px; color: #333; font-weight: 600; cursor: pointer;
            transition: background 0.3s; background: #f8f9fa;
        }
        .menu-group-header:hover { background: #e9ecef; }
        .menu-group-header i { width: 20px; text-align: center; }
        .menu-group-items { 
            list-style: none !important; 
            padding: 0 !important; 
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
        .menu-group-items .sidebar-link { padding-left: 52px; font-size: 14px; }
        
        /* Parent Menu Styles (for nested groups like User Menus) */
        .menu-parent-header {
            display: flex !important; align-items: center; justify-content: space-between;
            padding: 12px 20px; color: white; font-weight: 700; cursor: pointer;
            transition: all 0.3s; background: linear-gradient(135deg, #059669 0%, #1e40af 100%);
            text-transform: uppercase; font-size: 13px; letter-spacing: 0.5px;
        }
        .menu-parent-header:hover { 
            background: linear-gradient(135deg, #047857 0%, #1e3a8a 100%);
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .menu-parent-header i { width: 20px; text-align: center; }
        .menu-parent-items {
            list-style: none !important;
            padding: 0 !important;
            max-height: 0 !important;
            overflow: hidden !important;
            transition: max-height 0.3s ease !important;
            visibility: hidden !important;
            display: block !important;
            background: #fafafa;
        }
        .menu-parent-items.expanded {
            max-height: none !important;
            visibility: visible !important;
        }
        .menu-parent-items .menu-group-header {
            padding-left: 30px;
            background: #f3f4f6;
            border-left: 3px solid #d97706;
        }
        .menu-parent-items .menu-group-header:hover {
            background: #e5e7eb;
        }
        .menu-parent-items .menu-group-items .sidebar-link {
            padding-left: 62px;
        }
        
        /* Main Content */
        .main-content { 
            margin-left: 260px; margin-top: 60px; padding: 30px; 
            min-height: calc(100vh - 60px); transition: margin-left 0.3s;
        }
        .main-content.expanded { margin-left: 0; }
        
        /* Cards */
        .card { border: none; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
        .card-header { background: linear-gradient(135deg, #059669 0%, #1e40af 100%); color: white; border-radius: 12px 12px 0 0 !important; }
        
        /* Footer - Simple and Small */
        .footer {
            background: #f8f9fa;
            color: #666;
            padding: 8px 15px;
            margin-top: 30px;
            border-top: 1px solid #ddd;
            text-align: center;
            font-size: 12px;
        }
        .footer-logo {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            font-size: 11px;
        }
        .footer-logo img {
            height: 20px;
        }
        
        /* Top Performers Banner */
        .top-performers-banner {
            background: linear-gradient(135deg, #1e40af 0%, #059669 100%);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 25px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            overflow-x: auto;
        }
        .top-performers-title {
            color: white;
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 15px;
            text-align: center;
        }
        .performers-container {
            display: flex !important;
            gap: 15px;
            justify-content: center !important;
            flex-wrap: nowrap;
            min-width: min-content;
        }
        .performer-card {
            background: white;
            border-radius: 10px;
            padding: 15px;
            min-width: 180px;
            text-align: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            transition: transform 0.3s;
        }
        .performer-card:hover {
            transform: translateY(-5px);
        }
        .performer-rank {
            font-size: 32px;
            margin-bottom: 8px;
        }
        .performer-photo {
            width: 60px;
            height: 60px;
        }
        
        /* Birthday Banner - SPECTACULAR CELEBRATION DESIGN */
        .birthday-banner {
            background: linear-gradient(135deg, #ec4899 0%, #8b5cf6 100%);
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 25px;
            box-shadow: 0 8px 24px rgba(236, 72, 153, 0.4), 0 0 0 3px rgba(255, 255, 255, 0.3);
            overflow-x: auto;
            display: none;
            position: relative;
            border: 3px solid rgba(255, 255, 255, 0.3);
            animation: birthdayGlow 3s ease-in-out infinite;
        }
        .birthday-banner.show {
            display: block;
        }
        
        /* Daily Rotating Color Themes */
        .birthday-banner.theme-0 { background: linear-gradient(135deg, #FF6B9D 0%, #C06DD4 50%, #FFA07A 100%); }
        .birthday-banner.theme-1 { background: linear-gradient(135deg, #FFD700 0%, #FF69B4 50%, #87CEEB 100%); }
        .birthday-banner.theme-2 { background: linear-gradient(135deg, #00CED1 0%, #9370DB 50%, #FF1493 100%); }
        .birthday-banner.theme-3 { background: linear-gradient(135deg, #FF4500 0%, #FFD700 50%, #32CD32 100%); }
        .birthday-banner.theme-4 { background: linear-gradient(135deg, #FF69B4 0%, #4169E1 50%, #00FA9A 100%); }
        .birthday-banner.theme-5 { background: linear-gradient(135deg, #FF1493 0%, #FFA500 50%, #FF6347 100%); }
        .birthday-banner.theme-6 { background: linear-gradient(135deg, #9370DB 0%, #FF69B4 50%, #FFD700 100%); }
        
        @keyframes birthdayGlow {
            0%, 100% { box-shadow: 0 8px 24px rgba(236, 72, 153, 0.4), 0 0 0 3px rgba(255, 255, 255, 0.3), 0 0 30px rgba(255, 215, 0, 0.3); }
            50% { box-shadow: 0 8px 32px rgba(236, 72, 153, 0.6), 0 0 0 4px rgba(255, 255, 255, 0.5), 0 0 50px rgba(255, 215, 0, 0.5); }
        }
        
        .birthday-message {
            color: white;
            font-size: 26px;
            font-weight: 900;
            margin-bottom: 8px;
            text-align: center;
            text-shadow: 2px 2px 8px rgba(0,0,0,0.3), 0 0 20px rgba(255,255,255,0.5);
            letter-spacing: 1px;
            animation: celebrate 2s ease-in-out infinite;
        }
        
        @keyframes celebrate {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.05); }
        }
        
        .birthday-subtitle {
            color: rgba(255,255,255,0.95);
            font-size: 16px;
            text-align: center;
            margin-bottom: 20px;
            font-weight: 600;
            text-shadow: 1px 1px 4px rgba(0,0,0,0.3);
        }
        .birthday-container {
            display: flex !important;
            gap: 15px;
            justify-content: center !important;
            flex-wrap: nowrap;
            min-width: min-content;
        }
        .birthday-card {
            background: white;
            border-radius: 10px;
            padding: 15px;
            min-width: 180px;
            text-align: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            transition: transform 0.3s;
        }
        .birthday-card:hover {
            transform: translateY(-5px);
        }
        .birthday-photo {
            width: 60px;
            height: 60px;
            border-radius: 50%;
            object-fit: cover;
            margin-bottom: 10px;
            border: 3px solid #ec4899;
        }
        .birthday-initials {
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background: linear-gradient(135deg, #ec4899 0%, #8b5cf6 100%);
            color: white;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            font-weight: bold;
            margin: 0 auto 10px;
            border: 3px solid #ec4899;
        }
        .birthday-name {
            font-weight: 600;
            font-size: 14px;
            margin-bottom: 5px;
            color: #1e293b;
        }
        .birthday-location {
            color: #64748b;
            font-size: 12px;
        }
        .birthday-icon {
            font-size: 24px;
            margin-bottom: 8px;
        }
        .performer-initials {
            width: 60px;
            height: 60px;
            border-radius: 50%;
            margin: 0 auto 10px;
            background: linear-gradient(135deg, #8b5cf6 0%, #ec4899 100%);
            color: white;
            display: flex !important;
            align-items: center;
            justify-content: center !important;
            font-weight: bold;
            font-size: 20px;
            border: 3px solid #fbbf24;
        }
        .performer-name {
            font-weight: 600;
            color: #333;
            margin-bottom: 4px;
            font-size: 14px;
        }
        .performer-id {
            color: #666;
            font-size: 11px;
            margin-bottom: 8px;
        }
        .performer-earnings {
            color: #059669;
            font-weight: bold;
            font-size: 15px;
        }
        
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
        // API calls go through frontend proxy to backend
        const API_BASE_URL = '';  // Use relative URLs - frontend proxies to backend
        const sessionToken = '${escapeJSServer(sessionToken)}';  // Session token from login
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
        
        // DC Protocol (Dec 28, 2025): Use DCAuth cached user instead of redundant API call
        (async () => {
            const displayNameEl = document.getElementById('displayName');
            const displayIdEl = document.getElementById('displayUserId');
            
            try {
                // Wait for DCAuth to initialize (it passes role=mnr for MNR pages)
                if (typeof DCAuth !== 'undefined') {
                    const user = await DCAuth.getCurrentUser();
                    if (user) {
                        const userName = user.name || user.full_name || user.display_name || 'User';
                        if (displayNameEl) {
                            displayNameEl.textContent = userName;
                        }
                        
                        const userId = user.id || user.mnr_id || user.user_id || '';
                        if (displayIdEl && userId) {
                            displayIdEl.textContent = userId;
                        }
                        
                        console.log('[DC-Header] User info from DCAuth:', userName, '(' + userId + ')');
                        return;
                    }
                }
                
                // Fallback: Direct API call with role hint for MNR pages
                const response = await fetch(API_BASE_URL + '/api/v1/auth/me-hybrid?role=mnr', {
                    credentials: 'include',
                    headers: { 'Authorization': 'Bearer ' + sessionToken }
                });
                
                if (!response.ok) {
                    console.warn('[DC-Header] Auth API returned:', response.status);
                    return;
                }
                
                const data = await response.json();
                const user = data.data || data.employee || data;
                
                if (user) {
                    const userName = user.name || user.full_name || user.display_name || 'User';
                    if (displayNameEl) {
                        displayNameEl.textContent = userName;
                    }
                    
                    const userId = user.id || user.mnr_id || user.user_id || '';
                    if (displayIdEl && userId) {
                        displayIdEl.textContent = userId;
                    }
                    
                    console.log('[DC-Header] User info loaded:', userName, '(' + userId + ')');
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
            <!-- Profile Photo on LEFT -->
            <div id="headerProfilePhoto"></div>
            <div class="header-logo">
                <img src="/mnr-logo-horizontal.png" alt="MNR 2.0">
            </div>
        </div>
        <div class="header-right">
            <!-- Calendar Button -->
            <div style="position: relative;">
                <button class="header-calendar-btn" onclick="toggleCalendar()">
                    <i class="fas fa-calendar-alt"></i>
                    <span id="currentTime"></span>
                </button>
                <div class="calendar-dropdown" id="calendarDropdown">
                    <div class="calendar-header">
                        <button onclick="previousMonth()"><i class="fas fa-chevron-left"></i></button>
                        <h6 id="currentMonth" style="margin:0;"></h6>
                        <button onclick="nextMonth()"><i class="fas fa-chevron-right"></i></button>
                    </div>
                    <div class="calendar-grid" id="calendarGrid"></div>
                    <div class="calendar-footer">
                        <button onclick="goToToday()">Today</button>
                    </div>
                </div>
            </div>
            
            <!-- WhatsApp Share Button (Copy removed) -->
            <button class="share-btn" onclick="shareReferralWhatsApp()" style="background: #25D366; color: white; border: none; padding: 8px 16px; border-radius: 8px; cursor: pointer; transition: all 0.3s; display: flex; align-items: center; gap: 5px;">
                <i class="fab fa-whatsapp"></i>Share
            </button>
            
            <!-- Notification removed as per user request -->
            
            <!-- User Name with Last Login -->
            <div class="user-name-display" id="headerUserName">
                <span id="displayName">Loading...</span>
                <span style="font-size: 0.85em; opacity: 0.8; margin-left: 5px;">(<span id="displayUserId">...</span>)</span>
                <br><span class="header-last-login" id="lastLogin"></span>
            </div>
            
            <!-- Profile Dropdown Menu -->
            <div class="profile-dropdown">
                <button class="profile-btn" onclick="toggleProfileMenu()">
                    <i class="fas fa-user-circle"></i>
                    <span>Profile</span>
                    <i class="fas fa-chevron-down"></i>
                </button>
                <div class="dropdown-menu-custom" id="profileMenu">
                    <a href="/profile-view" class="dropdown-item-custom">
                        <i class="fas fa-user"></i> My Profile
                    </a>
                    <a href="/user/change-password" class="dropdown-item-custom">
                        <i class="fas fa-key"></i> Security Settings
                    </a>
                    <a href="/logout" class="dropdown-item-custom">
                        <i class="fas fa-sign-out-alt"></i> Sign Out
                    </a>
                </div>
            </div>
        </div>
    </div>

    <!-- Sidebar -->
    <div class="sidebar" id="sidebar">
        <ul class="sidebar-menu">
            <!-- DC Protocol Feb 2026: Non-activated sidebar by default -->
            <li class="sidebar-item">
                <a href="/user-home" class="sidebar-link"><i class="fas fa-home"></i> Home Dashboard</a>
            </li>
            <li class="sidebar-item">
                <a href="/profile-view" class="sidebar-link"><i class="fas fa-user"></i> View Profile</a>
            </li>
            <li class="sidebar-item">
                <a href="/create-member" class="sidebar-link"><i class="fas fa-user-plus"></i> Add Member</a>
            </li>
            <li class="sidebar-item">
                <div class="menu-group-header" onclick="toggleMenuGroup('coupons')">
                    <span><i class="fas fa-ticket-alt"></i> Coupon Modules</span>
                    <i class="fas fa-chevron-down" id="coupons-chevron"></i>
                </div>
                <ul class="menu-group-items" id="coupons-items">
                    <li><a href="/coupons?action=buy" class="sidebar-link">Buy Coupon</a></li>
                    <li><a href="/pins?action=activate" class="sidebar-link">Activate Coupon</a></li>
                    <li><a href="/pins" class="sidebar-link">Coupon Status</a></li>
                    <li><a href="/coupons" class="sidebar-link">Coupon Progress</a></li>
                    <li><a href="/coupon-transfer" class="sidebar-link">Coupon Transfer</a></li>
                </ul>
            </li>
            <!-- Settings Section -->
            <li class="sidebar-item" style="margin-top: auto; border-top: 2px solid rgba(255,255,255,0.1); padding-top: 10px;">
                <a href="#" class="sidebar-link" onclick="ThemeManager.toggle(); return false;">
                    <i class="fas fa-moon theme-toggle-icon"></i> <span class="theme-toggle-text">Theme Mode</span>
                </a>
            </li>
            <li class="sidebar-item">
                <a href="/user/change-password" class="sidebar-link">
                    <i class="fas fa-key"></i> Security Settings
                </a>
            </li>
            <li class="sidebar-item">
                <a href="#" onclick="logout(); return false;" class="sidebar-link" style="color: #ef4444;">
                    <i class="fas fa-sign-out-alt"></i> Logout
                </a>
            </li>
        </ul>
    </div>

    <!-- Main Content -->
    <div class="main-content" id="mainContent">
        ${content}
        
        <!-- Footer -->
        <div class="footer">
            <div class="footer-logo">
                <img src="/mnr-logo-horizontal.png" alt="MNR 2.0">
                <span>MNR Membership & Business Facilitation Platform</span>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script src="/auto-logout.js"></script>
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

        window.toggleProfileMenu = function() {
            const menu = document.getElementById('profileMenu');
            menu.classList.toggle('show');
        }
        
        // Calendar Functions
        let currentCalendarMonth = new Date();
        
        function toggleCalendar() {
            const dropdown = document.getElementById('calendarDropdown');
            dropdown.classList.toggle('show');
            if (dropdown.classList.contains('show')) {
                renderCalendar();
            }
        }
        
        function renderCalendar() {
            const grid = document.getElementById('calendarGrid');
            const monthEl = document.getElementById('currentMonth');
            const month = currentCalendarMonth.getMonth();
            const year = currentCalendarMonth.getFullYear();
            
            monthEl.textContent = new Date(year, month).toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
            
            const firstDay = new Date(year, month, 1).getDay();
            const daysInMonth = new Date(year, month + 1, 0).getDate();
            const daysInPrevMonth = new Date(year, month, 0).getDate();
            const today = new Date();
            
            let html = '';
            const dayNames = ['S', 'M', 'T', 'W', 'T', 'F', 'S'];
            dayNames.forEach(day => {
                html += \`<div style="font-weight:600;text-align:center;padding:5px;">\${day}</div>\`;
            });
            
            for (let i = firstDay - 1; i >= 0; i--) {
                html += \`<div class="calendar-day other-month">\${daysInPrevMonth - i}</div>\`;
            }
            
            for (let day = 1; day <= daysInMonth; day++) {
                const isToday = today.getDate() === day && today.getMonth() === month && today.getFullYear() === year;
                html += \`<div class="calendar-day\${isToday ? ' today' : ''}">\${day}</div>\`;
            }
            
            grid.innerHTML = html;
        }
        
        function previousMonth() {
            currentCalendarMonth.setMonth(currentCalendarMonth.getMonth() - 1);
            renderCalendar();
        }
        
        function nextMonth() {
            currentCalendarMonth.setMonth(currentCalendarMonth.getMonth() + 1);
            renderCalendar();
        }
        
        function goToToday() {
            currentCalendarMonth = new Date();
            renderCalendar();
        }
        
        // Update current date
        function updateCurrentTime() {
            const timeEl = document.getElementById('currentTime');
            if (timeEl) {
                const now = new Date();
                const options = { day: '2-digit', month: 'short', year: 'numeric' };
                timeEl.textContent = now.toLocaleDateString('en-IN', options);
            }
        }
        updateCurrentTime();  // Call once, no need to update every second for date
        
        // Notification Functions
        function toggleNotifications() {
            const dropdown = document.getElementById('notificationDropdown');
            dropdown.classList.toggle('show');
            if (dropdown.classList.contains('show')) {
                loadNotifications();
            }
        }
        
        async function loadNotifications() {
            try {
                const response = await fetch('/api/v1/users/notifications', {
                    headers: { 'Authorization': 'Bearer ' + sessionToken }
                });
                const data = await response.json();
                const list = document.getElementById('notificationList');
                const badge = document.getElementById('notificationBadge');
                
                if (data && data.data && data.data.length > 0) {
                    const unreadCount = data.data.filter(n => !n.read).length;
                    badge.textContent = unreadCount;
                    badge.style.display = unreadCount > 0 ? 'block' : 'none';
                    
                    list.innerHTML = data.data.map(notif => \`
                        <div class="notification-item\${!notif.read ? ' unread' : ''}">
                            <span class="notification-icon \${notif.type}">\${notif.type === 'income' ? '💰' : notif.type === 'team' ? '👥' : '🔔'}</span>
                            <div style="flex:1;">
                                <strong>\${notif.title}</strong><br>
                                <small>\${notif.message}</small><br>
                                <small style="opacity:0.6;">\${new Date(notif.created_at).toLocaleString()}</small>
                            </div>
                        </div>
                    \`).join('');
                } else {
                    badge.style.display = 'none';
                }
            } catch (err) {
                console.error('Failed to load notifications:', err);
            }
        }
        
        // WhatsApp Share Functions
        async function shareReferralWhatsApp() {
            try {
                const response = await fetch('/api/v1/auth/me', {
                    headers: { 'Authorization': 'Bearer ' + sessionToken }
                });
                const data = await response.json();
                // DC Protocol: Normalize response
                const user = data.data || data.employee || data;
                if (user && user.id) {
                    const referralLink = window.location.origin + '/signup?ref=' + user.id;
                    const message = \`Join MNR Reference Program using my link: \${referralLink}\`;
                    
                    // Check if mobile (use native share API for better mobile support)
                    if (navigator.share && /Android|iPhone|iPad|iPod/i.test(navigator.userAgent)) {
                        try {
                            await navigator.share({
                                title: 'MNR Reference Program',
                                text: message
                            });
                        } catch (shareErr) {
                            // If native share fails or is cancelled, fallback to WhatsApp link
                            if (shareErr.name !== 'AbortError') {
                                window.location.href = \`https://wa.me/?text=\${encodeURIComponent(message)}\`;
                            }
                        }
                    } else {
                        // Desktop or non-mobile - use WhatsApp Web
                        window.open(\`https://wa.me/?text=\${encodeURIComponent(message)}\`, '_blank');
                    }
                }
            } catch (err) {
                console.error('Failed to get referral link:', err);
                alert('Failed to get referral link');
            }
        }
        
        async function copyReferralLink() {
            try {
                const response = await fetch('/api/v1/auth/me', {
                    headers: { 'Authorization': 'Bearer ' + sessionToken }
                });
                const data = await response.json();
                // DC Protocol: Normalize response
                const user = data.data || data.employee || data;
                if (user && user.id) {
                    const referralLink = window.location.origin + '/signup?ref=' + user.id;
                    await navigator.clipboard.writeText(referralLink);
                    alert('Referral link copied to clipboard!');
                }
            } catch (err) {
                console.error('Failed to copy link:', err);
                alert('Failed to copy link');
            }
        }
        
        // Load Profile Photo and Last Login
        (async () => {
            try {
                const response = await fetch('/api/v1/auth/me', {
                    headers: { 'Authorization': 'Bearer ' + sessionToken }
                });
                const data = await response.json();
                // DC Protocol: Normalize response
                const user = data.data || data.employee || data;
                if (user && user.id) {
                    const photoContainer = document.getElementById('headerProfilePhoto');
                    const lastLoginEl = document.getElementById('lastLogin');
                    
                    // DC Protocol: Use initials for user profile display
                    // Profile photo serving for users is a future enhancement
                    const name = user.name || 'User';
                    const initials = name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
                    photoContainer.innerHTML = \`<div class="header-profile-initials">\${initials}</div>\`;
                    
                    // Display last login
                    if (user.last_login) {
                        const lastLogin = new Date(user.last_login);
                        const now = new Date();
                        const diffMs = now - lastLogin;
                        const diffMins = Math.floor(diffMs / 60000);
                        const diffHours = Math.floor(diffMs / 3600000);
                        const diffDays = Math.floor(diffMs / 86400000);
                        
                        let loginText = '';
                        if (diffMins < 1) loginText = 'Just now';
                        else if (diffMins < 60) loginText = \`\${diffMins}m ago\`;
                        else if (diffHours < 24) loginText = \`\${diffHours}h ago\`;
                        else loginText = \`\${diffDays}d ago\`;
                        
                        lastLoginEl.textContent = \`Last login: \${loginText}\`;
                    }
                }
            } catch (err) {
                console.error('Failed to load profile data:', err);
            }
        })();
        
        // Load Birthday Banner (DC Protocol - data from user table only)
        async function loadBirthdayBanner() {
            try {
                const response = await fetch('/api/v1/banners/birthday-today', {
                    headers: { 'Authorization': 'Bearer ' + sessionToken }
                });
                const data = await response.json();
                
                console.log('Birthday Banner Data:', data); // Debug log
                
                if (data.success && data.has_birthdays && data.users && data.users.length > 0) {
                    const banner = document.getElementById('topBirthdayBanner');
                    if (!banner) {
                        console.error('Birthday banner element not found!');
                        return;
                    }
                    
                    // Apply daily rotating theme (0-6 based on day of week)
                    const today = new Date();
                    const themeIndex = today.getDay(); // 0=Sunday, 6=Saturday
                    banner.className = 'birthday-banner show theme-' + themeIndex;
                    
                    // Set daily message and subtitle
                    const messageEl = document.getElementById('topBirthdayMessage');
                    if (messageEl) {
                        messageEl.textContent = data.message;
                    }
                    const subtitleEl = document.getElementById('topBirthdaySubtitle');
                    if (subtitleEl) {
                        subtitleEl.textContent = 'Celebrating Today:';
                    }
                    
                    // Render birthday users (Photo + Name + Location only)
                    // DC Protocol: Use initials only - user photo endpoint not available
                    const container = document.getElementById('topBirthdayContainer');
                    if (container) {
                        container.innerHTML = data.users.map(user => {
                            const initials = user.name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
                            const photoHtml = \`<div class="birthday-initials">\${initials}</div>\`;
                            
                            return \`
                                <div class="birthday-card">
                                    <div class="birthday-icon">🎂</div>
                                    \${photoHtml}
                                    <div class="birthday-name">\${user.name}</div>
                                    <div class="birthday-location">\${user.location}</div>
                                </div>
                            \`;
                        }).join('');
                    }
                    
                    console.log('Birthday banner loaded successfully with', data.users.length, 'birthdays');
                } else {
                    console.log('No birthdays today or banner hidden');
                }
            } catch (err) {
                console.error('Failed to load birthday banner:', err);
            }
        }
        
        // DC Protocol Feb 2026: Hide menus for non-activated users
        function hideActivationGatedMenus() {
            // Hide Facilitation & Recognition menu using ID selector
            const earningsItems = document.getElementById('earnings-items');
            if (earningsItems && earningsItems.parentElement) {
                earningsItems.parentElement.style.display = 'none';
                console.log('[DC Protocol] Hidden: Facilitation & Recognition menu');
            } else {
                console.warn('[DC Protocol] earnings-items element not found');
            }
            
            // Hide Recognition Programs (Awards) using ID selector
            const awardsItems = document.getElementById('awards-items');
            if (awardsItems && awardsItems.parentElement) {
                awardsItems.parentElement.style.display = 'none';
                console.log('[DC Protocol] Hidden: Recognition Programs menu');
            } else {
                console.warn('[DC Protocol] awards-items element not found');
            }
        }
        
        // DC Protocol Feb 2026: Check activation and upgrade sidebar for activated users
        
        
        // DC Protocol Feb 2026: Upgrade sidebar for activated users (only checks activation_date)
        (async function upgradeActivatedSidebar() {
            if (!sessionToken) return;
            try {
                const response = await fetch('/api/v1/auth/me-hybrid?role=mnr', {
                    headers: { 'Authorization': 'Bearer ' + sessionToken }
                });
                if (!response.ok) return;
                const data = await response.json();
                const user = data.data || data;
                const activationDate = user?.activation_date;
                // Only upgrade for users with valid activation_date (not null, not empty)
                const isActivated = !!(activationDate && activationDate !== 'null' && activationDate !== '' && activationDate !== 'None' && activationDate !== null);
                if (isActivated) {
                    const sidebar = document.getElementById('sidebar');
                    if (sidebar) {
                        sidebar.innerHTML = \`
        <ul class="sidebar-menu">
            <li class="sidebar-item">
                <a href="/user-home" class="sidebar-link"><i class="fas fa-home"></i> Home Dashboard</a>
            </li>
            <li class="sidebar-item">
                <div class="menu-group-header" onclick="toggleMenuGroup('announcements')">
                    <span><i class="fas fa-bullhorn"></i> Community Updates</span>
                    <i class="fas fa-chevron-down" id="announcements-chevron"></i>
                </div>
                <ul class="menu-group-items" id="announcements-items">
                    <li><a href="/user/announcements" class="sidebar-link">Official Updates</a></li>
                    <li><a href="/user/my-announcements" class="sidebar-link">My Submissions</a></li>
                    <li><a href="/user/my-announcements/pending" class="sidebar-link">Pending</a></li>
                    <li><a href="/user/my-announcements/approved" class="sidebar-link">Approved</a></li>
                    <li><a href="/user/my-announcements/rejected" class="sidebar-link">Rejected</a></li>
                </ul>
            </li>
            <li class="sidebar-item">
                <a href="/profile-view" class="sidebar-link"><i class="fas fa-user"></i> View Profile</a>
            </li>
            <li class="sidebar-item">
                <a href="/create-member" class="sidebar-link"><i class="fas fa-user-plus"></i> Add Member</a>
            </li>
            <li class="sidebar-item">
                <div class="menu-group-header" onclick="toggleMenuGroup('coupons')">
                    <span><i class="fas fa-ticket-alt"></i> Coupon Modules</span>
                    <i class="fas fa-chevron-down" id="coupons-chevron"></i>
                </div>
                <ul class="menu-group-items" id="coupons-items">
                    <li><a href="/coupons?action=buy" class="sidebar-link">Buy Coupon</a></li>
                    <li><a href="/pins?action=activate" class="sidebar-link">Activate Coupon</a></li>
                    <li><a href="/pins" class="sidebar-link">Coupon Status</a></li>
                    <li><a href="/coupons" class="sidebar-link">Coupon Progress</a></li>
                    <li><a href="/coupon-transfer" class="sidebar-link">Coupon Transfer</a></li>
                </ul>
            </li>
            <li class="sidebar-item">
                <div class="menu-group-header" onclick="toggleMenuGroup('members')">
                    <span><i class="fas fa-users"></i> My Connections</span>
                    <i class="fas fa-chevron-down" id="members-chevron"></i>
                </div>
                <ul class="menu-group-items" id="members-items">
                    <li><a href="/team" class="sidebar-link">All Connections</a></li>
                    <li><a href="/team?filter=direct" class="sidebar-link">Direct Connections</a></li>
                    <li><a href="/team-picture" class="sidebar-link">Connections Gallery</a></li>
                    <li><a href="/team?filter=ved" class="sidebar-link">Leadership Group (VED)</a></li>
                </ul>
            </li>
            <li class="sidebar-item">
                <div class="menu-group-header" onclick="toggleMenuGroup('mnr')">
                    <span><i class="fas fa-coins"></i> Facilitation & Recognition</span>
                    <i class="fas fa-chevron-down" id="mnr-chevron"></i>
                </div>
                <ul class="menu-group-items" id="mnr-items">
                    <li><a href="/earnings-overview" class="sidebar-link">Earnings Overview</a></li>
                    <li><a href="/earnings/direct-referral" class="sidebar-link">Direct Facilitation</a></li>
                    <li><a href="/earnings/matching-referral" class="sidebar-link">Group Performance Recognition</a></li>
                    <li><a href="/earnings/ved-income" class="sidebar-link">VED Leadership Recognition</a></li>
                    <li><a href="/earnings/guru-dakshina" class="sidebar-link">Mentorship Contribution Benefit</a></li>
                    <li><a href="/user/field-allowances" class="sidebar-link">Field Allowances</a></li>
                    <li><a href="/user/withdrawals" class="sidebar-link">Withdrawals</a></li>
                    <li><a href="/user/coupon-benefits" class="sidebar-link">Coupon Benefits</a></li>
                    <li><a href="/user/points-utilisation" class="sidebar-link">Points Utilisation</a></li>
                </ul>
            </li>
            <li class="sidebar-item">
                <div class="menu-group-header" onclick="toggleMenuGroup('myntreal')">
                    <span><i class="fas fa-gem"></i> MyntReal</span>
                    <i class="fas fa-chevron-down" id="myntreal-chevron"></i>
                </div>
                <ul class="menu-group-items" id="myntreal-items">
                    <li><a href="/user/my-leads" class="sidebar-link">My Leads</a></li>
                    <li><a href="/user/franchise-purchases" class="sidebar-link">Franchise Earnings</a></li>
                </ul>
            </li>
            <li class="sidebar-item">
                <div class="menu-group-header" onclick="toggleMenuGroup('vgk4u')">
                    <span><i class="fas fa-crown"></i> VGK4U</span>
                    <i class="fas fa-chevron-down" id="vgk4u-chevron"></i>
                </div>
                <ul class="menu-group-items" id="vgk4u-items">
                    <li><a href="/user/vgk4u/real-estate" class="sidebar-link">VGK Real Dreams (Real Estate)</a></li>
                    <li><a href="/user/vgk4u/insurance" class="sidebar-link">VGK Care (Insurance)</a></li>
                    <li><a href="/user/vgk4u/training" class="sidebar-link">EVolution Training Center (ETC)</a></li>
                </ul>
            </li>
            <li class="sidebar-item">
                <div class="menu-group-header" onclick="toggleMenuGroup('awards')">
                    <span><i class="fas fa-trophy"></i> Awards & Bonanza</span>
                    <i class="fas fa-chevron-down" id="awards-chevron"></i>
                </div>
                <ul class="menu-group-items" id="awards-items">
                    <li><a href="/user/awards" class="sidebar-link">Awards</a></li>
                    <li><a href="/user/awards?type=bonanza" class="sidebar-link">Bonanza Awards</a></li>
                </ul>
            </li>
            <li class="sidebar-item" style="margin-top: auto; border-top: 2px solid rgba(255,255,255,0.1); padding-top: 10px;">
                <a href="#" class="sidebar-link" onclick="ThemeManager.toggle(); return false;">
                    <i class="fas fa-moon theme-toggle-icon"></i> <span class="theme-toggle-text">Theme Mode</span>
                </a>
            </li>
            <li class="sidebar-item">
                <a href="/user/change-password" class="sidebar-link">
                    <i class="fas fa-key"></i> Security Settings
                </a>
            </li>
            <li class="sidebar-item">
                <a href="#" onclick="logout(); return false;" class="sidebar-link" style="color: #ef4444;">
                    <i class="fas fa-sign-out-alt"></i> Logout
                </a>
            </li>
        </ul>\`;
                    }
                }
            } catch (err) { }
        })();
        
        // Close sidebar when clicking outside on mobile
        document.addEventListener('DOMContentLoaded', function() {
            
            // Call birthday banner load on dashboard pages only (AFTER DOM ready)
            console.log('🎂 Birthday Check:', {
                sessionToken: !!sessionToken,
                pathname: window.location.pathname,
                shouldLoad: sessionToken && (window.location.pathname === '/user-home' || window.location.pathname === '/dashboard')
            });
            
            if (sessionToken && (window.location.pathname === '/user-home' || window.location.pathname === '/dashboard')) {
                console.log('🎂 Loading birthday banner...');
                setTimeout(loadBirthdayBanner, 300); // Small delay to ensure everything is ready
            }
            
            const sidebar = document.getElementById('sidebar');
            const mainContent = document.getElementById('mainContent');
            
            mainContent.addEventListener('click', function() {
                if (window.innerWidth <= 768 && sidebar.classList.contains('show')) {
                    sidebar.classList.remove('show');
                }
            });
        });
        
        function toggleMenuGroup(groupId) {
            const items = document.getElementById(groupId + '-items');
            const chevron = document.getElementById(groupId + '-chevron');
            items.classList.toggle('expanded');
            chevron.classList.toggle('fa-chevron-down');
            chevron.classList.toggle('fa-chevron-up');
            
            // Save the expanded state to sessionStorage
            saveMenuState();
        }

        function saveMenuState() {
            const expandedGroups = [];
            const menuGroups = ['announcements', 'coupons', 'members', 'rvz', 'myntreal', 'earnings', 'awards'];
            
            menuGroups.forEach(groupId => {
                const items = document.getElementById(groupId + '-items');
                if (items && items.classList.contains('expanded')) {
                    expandedGroups.push(groupId);
                }
            });
            
            sessionStorage.setItem('expandedMenuGroups', JSON.stringify(expandedGroups));
        }

        function restoreMenuState() {
            // Check if we should restore menu state
            const currentPath = window.location.pathname;
            const isDashboard = currentPath === '/user-home' || currentPath === '/dashboard' || currentPath === '/';
            
            // Only restore if NOT on dashboard pages
            if (!isDashboard) {
                const savedState = sessionStorage.getItem('expandedMenuGroups');
                if (savedState) {
                    try {
                        const expandedGroups = JSON.parse(savedState);
                        expandedGroups.forEach(groupId => {
                            const items = document.getElementById(groupId + '-items');
                            const chevron = document.getElementById(groupId + '-chevron');
                            if (items && chevron && !items.classList.contains('expanded')) {
                                items.classList.add('expanded');
                                chevron.classList.remove('fa-chevron-down');
                                chevron.classList.add('fa-chevron-up');
                            }
                        });
                    } catch (e) {
                        console.error('Error restoring menu state:', e);
                    }
                }
            } else {
                // Clear menu state when visiting dashboard
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

        // Highlight active menu item
        const currentPath = window.location.pathname;
        document.querySelectorAll('.sidebar-link').forEach(link => {
            if (link.getAttribute('href').startsWith(currentPath)) {
                link.classList.add('active');
            }
        });
    </script>
</body>
</html>`;


module.exports = { createHTML, BUILD_ID };
