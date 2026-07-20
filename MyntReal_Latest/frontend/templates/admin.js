// Admin HTML Template Module
// DC Protocol (Dec 31, 2025): Refactored to use unified staff_sidebar.js
// Previously had inline sidebar - now uses shared sidebar component for consistency

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

const createAdminHTML = (title, content, sessionToken = '') => `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    <meta name="build-version" content="${BUILD_ID}">
    <title>${title} - Admin Panel</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <script src="/public/js/staff-token-manager.js"></script>
    <script src="/public/js/staff-fetch.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: #f5f7fa;
            min-height: 100vh;
        }
        
        /* Main content area with sidebar offset */
        .main-content { 
            margin-left: 260px; 
            padding: 24px; 
            min-height: 100vh;
            transition: margin-left 0.3s ease;
        }
        
        /* When sidebar is collapsed */
        body.sidebar-collapsed-mode .main-content {
            margin-left: 70px;
        }
        
        /* Mobile responsive */
        @media (max-width: 768px) {
            .main-content { 
                margin-left: 0 !important; 
                padding: 16px;
            }
        }
        
        /* Legacy card styles for backward compatibility */
        .card { 
            background: white; 
            border-radius: 10px; 
            box-shadow: 0 2px 10px rgba(0,0,0,0.05); 
            margin-bottom: 20px;
            border: none;
        }
        .card-header { 
            background: transparent; 
            border-bottom: 1px solid #eee; 
            padding: 15px 20px; 
            font-weight: 600;
            color: #333;
        }
        .card-body { padding: 20px; }
        
        /* Table styles */
        .table { margin: 0; }
        .table th { 
            background: #f8f9fa; 
            font-weight: 600; 
            color: #374151;
            border-bottom: 2px solid #e5e7eb;
        }
        .table td { vertical-align: middle; color: #4b5563; }
        
        /* Button styles */
        .btn-primary { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
        }
        .btn-primary:hover { 
            background: linear-gradient(135deg, #5a67d8 0%, #6b46a1 100%);
        }
        
        /* Status badges */
        .badge { font-weight: 500; padding: 5px 10px; }
        .badge-success, .bg-success { background: #10b981 !important; }
        .badge-warning, .bg-warning { background: #f59e0b !important; color: white !important; }
        .badge-danger, .bg-danger { background: #ef4444 !important; }
        .badge-info, .bg-info { background: #3b82f6 !important; }
        
        /* Form controls */
        .form-control:focus, .form-select:focus {
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.15);
        }
        
        /* Alert styles */
        .alert { border-radius: 8px; border: none; }
        
        /* Loading spinner */
        .loading-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(255,255,255,0.8);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 9999;
        }
        
        .spinner-border { color: #667eea; }
    </style>
</head>
<body class="has-unified-header">
    <!-- DC Protocol: Unified Header (rendered by staff_sidebar.js) -->
    <div id="unifiedHeader"></div>
    
    <!-- DC Protocol: Unified Sidebar (rendered by staff_sidebar.js) -->
    <nav id="staffSidebar"></nav>

    <!-- Main Content -->
    <div class="main-content" id="mainContent">
        ${content}
    </div>
    
    <!-- DC Protocol: Staff Sidebar Script (includes header + sidebar + CSS) -->
    <script src="/staff_sidebar.js?v=${BUILD_ID}"></script>
    
    <!-- Initialize Unified Layout -->
    <script>
        document.addEventListener('DOMContentLoaded', async function() {
            // Initialize staff sidebar (handles auth, menus, etc.)
            await StaffSidebar.init('staffSidebar');
            
            // Inject unified header with page title
            StaffSidebar.injectUnifiedHeader('unifiedHeader', '${escapeJSServer(title)}', 'fas fa-user-shield');
            
            console.log('[DC-ADMIN] Unified layout initialized');
        });
    </script>
    
    <!-- Global Variables for Admin Pages -->
    <script>
        // Backend API configuration - use relative URL for proxy
        window.BACKEND_URL = '/api/v1';
        window.sessionToken = '${sessionToken}';
        
        // Get current user ID from session token
        window.currentUserId = null;
        try {
            const staffUser = localStorage.getItem('staff_user');
            if (staffUser) {
                const userData = JSON.parse(staffUser);
                window.currentUserId = userData.employee_id || userData.id;
            }
        } catch (e) {
            console.error('[DC-ADMIN] Error loading user data:', e);
        }
    </script>
    
    <!-- Bootstrap JavaScript Bundle -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script src="/auto-logout.js"></script>
</body>
</html>`;


module.exports = { createAdminHTML, BUILD_ID };
