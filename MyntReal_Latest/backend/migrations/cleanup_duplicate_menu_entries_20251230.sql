-- DC Protocol (Dec 30, 2025): Cleanup duplicate menu entries in staff_menu_registry
-- This migration removes duplicate entries for task-related pages that cause duplicate sidebar items

-- Issue: Two menu entries for "Tasks Assigned by Me" page:
-- ID 78: staff_tasks_assigned_by_me (KEEP - has proper sidebar_section config)
-- ID 514: staff_tasks_assigned_by_me_v2 (DELETE - duplicate without sidebar config)

-- Issue: Two menu entries for "Task Tracker" page:
-- ID 76: staff_task_tracker (KEEP - has proper sidebar_section config)
-- ID 515: staff_tasks_tracker (DELETE - duplicate without sidebar config)

-- Safety check: Only delete if the duplicate entries exist
DELETE FROM staff_menu_registry 
WHERE menu_code = 'staff_tasks_assigned_by_me_v2' 
  AND route_path = '/staff/tasks/assigned-by-me-v2'
  AND id != (SELECT MIN(id) FROM staff_menu_registry WHERE route_path = '/staff/tasks/assigned-by-me-v2');

DELETE FROM staff_menu_registry 
WHERE menu_code = 'staff_tasks_tracker' 
  AND route_path = '/staff/tasks/tracker'
  AND id != (SELECT MIN(id) FROM staff_menu_registry WHERE route_path = '/staff/tasks/tracker');

-- Verification query to ensure no duplicates remain
-- Run after migration: SELECT route_path, COUNT(*) FROM staff_menu_registry GROUP BY route_path HAVING COUNT(*) > 1;
