-- DC Protocol: Sync missing service-tickets menu entries to production
-- Created: 2026-01-02
-- Purpose: Production has only 3 service-tickets entries, development has 10

-- Insert missing service-tickets menu items (using ON CONFLICT to avoid duplicates)
INSERT INTO staff_menu_registry (
    menu_code, menu_name, menu_description, route_path, menu_category, menu_icon,
    display_order, audience_scope, source, source_file, is_default_visible,
    is_default_accessible, is_active, is_system_default, created_at, updated_at,
    sidebar_section, sidebar_section_title, sidebar_section_order, menu_type, parent_section, is_submenu
) VALUES 
-- Dashboard
('staff_service_tickets_dashboard', 'Dashboard', 'Service tickets dashboard', '/staff/service-tickets/dashboard', 'SERVICE TICKETS', 'fas fa-tachometer-alt',
 1, 'staff', 'sidebar_sync', 'staff_sidebar.js', true, true, true, true, NOW(), NOW(),
 'service-tickets', 'SERVICE TICKETS', 4, 'STAFF', NULL, false),

-- Service Queue
('staff_service_tickets_queue', 'Service Queue', 'View and manage service queue', '/staff/service-tickets/queue', 'SERVICE TICKETS', 'fas fa-list-alt',
 2, 'staff', 'sidebar_sync', 'staff_sidebar.js', true, true, true, true, NOW(), NOW(),
 'service-tickets', 'SERVICE TICKETS', 4, 'STAFF', NULL, false),

-- Raise Ticket  
('staff_service_tickets_raise', 'Raise Ticket', 'Create new service ticket', '/staff/service-tickets/raise', 'SERVICE TICKETS', 'fas fa-plus-circle',
 3, 'staff', 'sidebar_sync', 'staff_sidebar.js', true, true, true, true, NOW(), NOW(),
 'service-tickets', 'SERVICE TICKETS', 4, 'STAFF', NULL, false),

-- Procurement
('staff_service_tickets_procurement', 'Procurement', 'Service ticket procurement', '/staff/service-tickets/procurement', 'SERVICE TICKETS', 'fas fa-shopping-cart',
 4, 'staff', 'sidebar_sync', 'staff_sidebar.js', true, true, true, true, NOW(), NOW(),
 'service-tickets', 'SERVICE TICKETS', 4, 'STAFF', NULL, false),

-- Procurement Queue
('staff_service_tickets_procurement_queue', 'Procurement Queue', 'View procurement queue', '/staff/service-tickets/procurement-queue', 'SERVICE TICKETS', 'fas fa-clipboard-list',
 5, 'staff', 'sidebar_sync', 'staff_sidebar.js', true, true, true, true, NOW(), NOW(),
 'service-tickets', 'SERVICE TICKETS', 4, 'STAFF', NULL, false),

-- Performance
('staff_service_tickets_performance', 'Performance', 'Service performance metrics', '/staff/service-tickets/performance', 'SERVICE TICKETS', 'fas fa-trophy',
 6, 'staff', 'sidebar_sync', 'staff_sidebar.js', true, true, true, true, NOW(), NOW(),
 'service-tickets', 'SERVICE TICKETS', 4, 'STAFF', NULL, false),

-- Reports
('staff_service_tickets_reports', 'Reports', 'Service ticket reports', '/staff/service-tickets/reports', 'SERVICE TICKETS', 'fas fa-file-alt',
 7, 'staff', 'sidebar_sync', 'staff_sidebar.js', true, true, true, true, NOW(), NOW(),
 'service-tickets', 'SERVICE TICKETS', 4, 'STAFF', NULL, false)

ON CONFLICT (menu_code) DO UPDATE SET
    menu_name = EXCLUDED.menu_name,
    route_path = EXCLUDED.route_path,
    menu_icon = EXCLUDED.menu_icon,
    sidebar_section = EXCLUDED.sidebar_section,
    sidebar_section_title = EXCLUDED.sidebar_section_title,
    sidebar_section_order = EXCLUDED.sidebar_section_order,
    menu_type = EXCLUDED.menu_type,
    is_active = true,
    updated_at = NOW();

-- Verify the sync
SELECT menu_code, menu_name, route_path, sidebar_section FROM staff_menu_registry 
WHERE sidebar_section = 'service-tickets' AND is_active = true
ORDER BY display_order;
