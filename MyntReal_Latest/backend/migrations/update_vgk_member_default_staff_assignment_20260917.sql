-- ==============================================================================
-- Migration: update_vgk_member_default_staff_assignment_20260917.sql
-- Purpose: Default assignment of VGK Channel Partners to creating staff employees
--          and backfill of unassigned historical members created by staff.
-- ==============================================================================

-- Step 1: Assign unassigned VGK members whose registered_by_emp_code matches a staff employee
UPDATE official_partners op
SET assigned_staff_id = se.id,
    assigned_by_id = se.id,
    assigned_at = COALESCE(op.created_at, NOW())
FROM staff_employees se
WHERE op.category = 'VGK_TEAM'
  AND op.assigned_staff_id IS NULL
  AND UPPER(TRIM(op.registered_by_emp_code)) = UPPER(TRIM(se.emp_code));

-- Step 2: Assign unassigned VGK members whose registered_by_emp_code is NULL/empty or not matching staff,
-- but who were registered/created by a staff employee in vgk_points_ledger (welcome/signup points entry)
WITH first_points AS (
    SELECT DISTINCT ON (partner_id) partner_id, created_by
    FROM vgk_points_ledger
    WHERE created_by IS NOT NULL
    ORDER BY partner_id, id ASC
)
UPDATE official_partners op
SET assigned_staff_id = se.id,
    assigned_by_id = se.id,
    assigned_at = COALESCE(op.created_at, NOW()),
    registered_by_emp_code = COALESCE(NULLIF(TRIM(op.registered_by_emp_code), ''), se.emp_code)
FROM first_points fp
JOIN staff_employees se ON se.id = fp.created_by
WHERE op.category = 'VGK_TEAM'
  AND op.id = fp.partner_id
  AND op.assigned_staff_id IS NULL;
