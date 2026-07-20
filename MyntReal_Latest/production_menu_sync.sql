-- Production SQL for Menu Auto-Sync Deployment
-- Generated: Dec 19, 2025
-- Purpose: Insert default StaffEmployeeMenuSettings for ALL active employees
--          for menus with is_default_visible=True
-- DC Protocol: Company-scoped settings, employee-centric access

-- Insert missing default settings for all active employees
INSERT INTO staff_employee_menu_settings (
    company_id, 
    employee_id, 
    menu_id, 
    can_view, 
    can_edit, 
    is_overridden, 
    set_by_code, 
    set_by_name, 
    created_at
)
SELECT 
    m.company_id,
    e.id as employee_id,
    m.id as menu_id,
    m.is_default_visible as can_view,
    m.is_default_accessible as can_edit,
    false as is_overridden,
    'SYSTEM' as set_by_code,
    'Auto-Sync Production' as set_by_name,
    NOW() as created_at
FROM staff_employees e
CROSS JOIN staff_menu_master m
LEFT JOIN staff_employee_menu_settings s 
    ON s.employee_id = e.id 
    AND s.menu_id = m.id 
    AND s.company_id = m.company_id
WHERE e.status = 'active' 
    AND e.is_deleted = false
    AND m.is_active = true 
    AND m.is_default_visible = true
    AND m.audience_scope IN ('staff', 'shared')
    AND s.id IS NULL
ON CONFLICT DO NOTHING;

-- Verify the insertion
SELECT 
    COUNT(*) as total_settings,
    COUNT(DISTINCT employee_id) as unique_employees,
    COUNT(DISTINCT menu_id) as unique_menus
FROM staff_employee_menu_settings
WHERE set_by_code = 'SYSTEM';
