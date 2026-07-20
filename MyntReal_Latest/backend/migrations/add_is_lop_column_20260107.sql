-- Migration: Add is_lop column to staff_leave_requests
-- Date: January 07, 2026
-- Purpose: Track Loss of Pay (LOP) leave requests when balance is 0
-- DC Protocol: Column added for leave management feature

-- Add is_lop column to track leave requests marked as Loss of Pay
ALTER TABLE staff_leave_requests ADD COLUMN IF NOT EXISTS is_lop BOOLEAN NOT NULL DEFAULT FALSE;

-- Add comment for documentation
COMMENT ON COLUMN staff_leave_requests.is_lop IS 'True if leave was marked as Loss of Pay due to insufficient balance';
