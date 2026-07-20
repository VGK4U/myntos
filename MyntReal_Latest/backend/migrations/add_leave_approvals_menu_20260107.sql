-- Add Leave Approvals Menu for Menu Access Control
-- DC Protocol: Jan 07, 2026
-- This enables granular view/edit permissions via StaffEmployeeMenuSettings

-- Insert leave-approvals menu for each company under ATTENDANCE section
INSERT INTO staff_menu_master (
    company_id, menu_code, menu_name, menu_description, 
    route_path, parent_id, menu_category, menu_icon,
    display_order, audience_scope, is_active,
    is_default_visible, is_default_accessible
)
SELECT 
    c.id as company_id,
    'leave-approvals' as menu_code,
    'Leave Approvals' as menu_name,
    'View and approve/reject leave requests from subordinates' as menu_description,
    '/staff/leave-approvals' as route_path,
    NULL as parent_id,
    'ATTENDANCE' as menu_category,
    'fas fa-user-check' as menu_icon,
    25 as display_order,
    'staff' as audience_scope,
    true as is_active,
    false as is_default_visible,  -- Not visible by default (requires explicit assignment)
    false as is_default_accessible  -- Not editable by default
FROM associated_companies c
WHERE NOT EXISTS (
    SELECT 1 FROM staff_menu_master m 
    WHERE m.menu_code = 'leave-approvals' AND m.company_id = c.id
);

-- Also insert my-leaves menu for each company
INSERT INTO staff_menu_master (
    company_id, menu_code, menu_name, menu_description, 
    route_path, parent_id, menu_category, menu_icon,
    display_order, audience_scope, is_active,
    is_default_visible, is_default_accessible
)
SELECT 
    c.id as company_id,
    'my-leaves' as menu_code,
    'My Leaves' as menu_name,
    'View leave balance, apply for leave, and track leave history' as menu_description,
    '/staff/my-leaves' as route_path,
    NULL as parent_id,
    'ATTENDANCE' as menu_category,
    'fas fa-calendar-minus' as menu_icon,
    20 as display_order,
    'staff' as audience_scope,
    true as is_active,
    true as is_default_visible,  -- Visible to all staff by default
    true as is_default_accessible  -- All staff can apply for leaves
FROM associated_companies c
WHERE NOT EXISTS (
    SELECT 1 FROM staff_menu_master m 
    WHERE m.menu_code = 'my-leaves' AND m.company_id = c.id
);

-- Log completion
DO $$
BEGIN
    RAISE NOTICE '[DC-LEAVE-MENU] Leave management menus added to staff_menu_master';
END $$;
