-- Migration: Add last_working_date and restart_date to staff_employees
-- DC Protocol (Jan 2026): Track status transition dates for complete audit trail
-- Date: 2026-01-29

-- Add last_working_date column - Set when status changes to paused/resigned/terminated/deactivated
ALTER TABLE staff_employees 
ADD COLUMN IF NOT EXISTS last_working_date DATE;

-- Add restart_date column - Set when status changes back to active (reactivation)
ALTER TABLE staff_employees 
ADD COLUMN IF NOT EXISTS restart_date DATE;

-- Add indexes for efficient filtering by these dates
CREATE INDEX IF NOT EXISTS idx_staff_emp_last_working_date ON staff_employees(last_working_date) WHERE last_working_date IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_staff_emp_restart_date ON staff_employees(restart_date) WHERE restart_date IS NOT NULL;

-- Add comments for documentation
COMMENT ON COLUMN staff_employees.last_working_date IS 'Final working day before status change to paused/resigned/terminated/deactivated';
COMMENT ON COLUMN staff_employees.restart_date IS 'Date when employee status was reactivated to active';
