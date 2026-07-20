-- DC Protocol: Full production menu registry sync
-- Created: 2026-01-02
-- Purpose: Sync all missing menu entries from development to production

-- 1. STAFF_DASHBOARD section (missing in production)
-- Note: /staff/overview removed - route does not exist
INSERT INTO staff_menu_registry (
    menu_code, menu_name, menu_description, route_path, menu_category, menu_icon,
    display_order, audience_scope, source, is_default_visible, is_default_accessible, 
    is_active, is_system_default, created_at, updated_at,
    sidebar_section, sidebar_section_title, sidebar_section_order, menu_type
) VALUES 
('staff_dashboard_main', 'Dashboard', 'Staff main dashboard', '/staff/dashboard', 'STAFF DASHBOARD', 'fas fa-tachometer-alt',
 1, 'staff', 'sidebar_sync', true, true, true, true, NOW(), NOW(), 'STAFF_DASHBOARD', 'STAFF DASHBOARD', 1, 'STAFF')
ON CONFLICT (menu_code) DO UPDATE SET
    sidebar_section = EXCLUDED.sidebar_section,
    sidebar_section_title = EXCLUDED.sidebar_section_title,
    sidebar_section_order = EXCLUDED.sidebar_section_order,
    is_active = true,
    updated_at = NOW();

-- 2. zy-member-earnings section (missing in production)
INSERT INTO staff_menu_registry (
    menu_code, menu_name, menu_description, route_path, menu_category, menu_icon,
    display_order, audience_scope, source, is_default_visible, is_default_accessible, 
    is_active, is_system_default, created_at, updated_at,
    sidebar_section, sidebar_section_title, sidebar_section_order, menu_type, parent_section, is_submenu
) VALUES 
('zy_incentive_approvals', 'Incentive Approvals', 'Zynova incentive approvals', '/staff/zynova/incentive-approvals', 'ZYNOVA', 'fas fa-check-circle',
 1, 'staff', 'sidebar_sync', true, true, true, true, NOW(), NOW(), 'zy-member-earnings', 'ZY Member Earnings', 8, 'STAFF', 'zynova', true),
('zy_all_members', 'All Zynova Members', 'All Zynova members list', '/staff/zynova/all-members', 'ZYNOVA', 'fas fa-users',
 2, 'staff', 'sidebar_sync', true, true, true, true, NOW(), NOW(), 'zy-member-earnings', 'ZY Member Earnings', 8, 'STAFF', 'zynova', true),
('zy_vgk_real_dreams', 'VGK Real Dreams', 'VGK Real Dreams management', '/staff/zynova/real-dreams', 'ZYNOVA', 'fas fa-home',
 3, 'staff', 'sidebar_sync', true, true, true, true, NOW(), NOW(), 'zy-member-earnings', 'ZY Member Earnings', 8, 'STAFF', 'zynova', true),
('zy_vgk_care', 'VGK Care', 'VGK Care management', '/staff/zynova/care', 'ZYNOVA', 'fas fa-heart',
 4, 'staff', 'sidebar_sync', true, true, true, true, NOW(), NOW(), 'zy-member-earnings', 'ZY Member Earnings', 8, 'STAFF', 'zynova', true)
ON CONFLICT (menu_code) DO UPDATE SET
    sidebar_section = EXCLUDED.sidebar_section,
    sidebar_section_title = EXCLUDED.sidebar_section_title,
    sidebar_section_order = EXCLUDED.sidebar_section_order,
    parent_section = EXCLUDED.parent_section,
    is_submenu = EXCLUDED.is_submenu,
    is_active = true,
    updated_at = NOW();

-- 3. Normalize journeys section (prod has journey-tracking, dev has journeys)
UPDATE staff_menu_registry 
SET sidebar_section = 'journeys', 
    sidebar_section_title = 'JOURNEYS',
    updated_at = NOW()
WHERE sidebar_section = 'journey-tracking' AND is_active = true;

-- 4. Normalize sfms sections (prod has financial-management, dev has sfms + sfms-inventory)
UPDATE staff_menu_registry 
SET sidebar_section = 'sfms', 
    sidebar_section_title = 'SFMS',
    updated_at = NOW()
WHERE sidebar_section = 'financial-management' AND is_active = true;

UPDATE staff_menu_registry 
SET sidebar_section = 'sfms-inventory', 
    sidebar_section_title = 'SFMS INVENTORY',
    updated_at = NOW()
WHERE sidebar_section = 'inventory' AND is_active = true;

-- 5. Fix real-dreams section (prod has 2, dev has 4)
UPDATE staff_menu_registry 
SET sidebar_section = 'real-dreams', 
    sidebar_section_title = 'Real Dreams',
    parent_section = 'zynova',
    is_submenu = true,
    updated_at = NOW()
WHERE route_path LIKE '/staff/zynova/real%' OR route_path LIKE '%/real-dreams%';

-- Verify final counts
SELECT sidebar_section, menu_type, COUNT(*) as cnt 
FROM staff_menu_registry 
WHERE is_active = true AND sidebar_section IS NOT NULL AND sidebar_section != ''
GROUP BY sidebar_section, menu_type 
ORDER BY menu_type, sidebar_section;
