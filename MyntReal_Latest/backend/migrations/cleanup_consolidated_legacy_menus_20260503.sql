-- DC Task #48 (May 3, 2026): Cleanup legacy consolidated report menu entries
--
-- Task #47 collapsed four separate consolidated report pages
--   (Balance Sheet, P&L, Sales, Purchases)
-- into a single tabbed page at /staff/consolidated, registered under the
-- single menu code CONSOLIDATED_REPORTS.
--
-- Older startup runs registered the four legacy menu codes:
--   CONSOLIDATED_BALANCE_SHEET, CONSOLIDATED_PL,
--   CONSOLIDATED_SALES, CONSOLIDATED_PURCHASES
-- pointing at routes that now 404. Their per-company copies in
-- staff_menu_master and any per-employee grants in
-- staff_employee_menu_settings must be cleaned up so the menu access matrix
-- UI does not surface dead options.
--
-- This migration is idempotent: re-running it after the rows have been
-- removed is a no-op.

DO $$
DECLARE
    legacy_codes TEXT[] := ARRAY[
        'CONSOLIDATED_BALANCE_SHEET',
        'CONSOLIDATED_PL',
        'CONSOLIDATED_SALES',
        'CONSOLIDATED_PURCHASES'
    ];
    legacy_routes TEXT[] := ARRAY[
        '/staff/consolidated-balance-sheet',
        '/staff/consolidated-pl',
        '/staff/consolidated-sales',
        '/staff/consolidated-purchases'
    ];
BEGIN
    -- 1. For each company that already has a CONSOLIDATED_REPORTS master row,
    --    redirect any per-employee grants from a legacy menu to the new one
    --    (only when no grant for the new menu already exists for that employee).
    UPDATE staff_employee_menu_settings sems
       SET menu_id = new_master.id,
           updated_at = NOW()
      FROM staff_menu_master old_master
      JOIN staff_menu_master new_master
        ON new_master.company_id = old_master.company_id
       AND new_master.menu_code = 'CONSOLIDATED_REPORTS'
     WHERE sems.menu_id = old_master.id
       AND old_master.menu_code = ANY(legacy_codes)
       AND NOT EXISTS (
           SELECT 1
             FROM staff_employee_menu_settings ex
            WHERE ex.employee_id = sems.employee_id
              AND ex.menu_id = new_master.id
       );

    -- 2. Delete any remaining (now-redundant) per-employee grants that still
    --    reference legacy master rows.
    DELETE FROM staff_employee_menu_settings
     WHERE menu_id IN (
         SELECT id FROM staff_menu_master WHERE menu_code = ANY(legacy_codes)
     );

    -- 3. Drop per-company master rows for the four legacy codes.
    DELETE FROM staff_menu_master WHERE menu_code = ANY(legacy_codes);

    -- 4. Drop role-based access entries that referenced the legacy routes.
    DELETE FROM staff_role_menu_access WHERE route_path = ANY(legacy_routes);

    -- 5. Drop the global registry rows for the four legacy menu codes.
    DELETE FROM staff_menu_registry WHERE menu_code = ANY(legacy_codes);
END$$;
