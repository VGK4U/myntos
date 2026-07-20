-- DC Protocol (Jan 2026): Add Previous Experience Documents Support
-- Migration: add_experience_documents_20260128.sql
-- Purpose: Track and verify employee experience documentation

-- Step 1: Add is_experienced flag to staff_employees
ALTER TABLE staff_employees 
ADD COLUMN IF NOT EXISTS is_experienced BOOLEAN DEFAULT FALSE;

-- Step 2: Add experience document columns to staff_employee_kyc
ALTER TABLE staff_employee_kyc 
ADD COLUMN IF NOT EXISTS bank_statement_1_url TEXT,
ADD COLUMN IF NOT EXISTS bank_statement_2_url TEXT,
ADD COLUMN IF NOT EXISTS bank_statement_3_url TEXT,
ADD COLUMN IF NOT EXISTS offer_letter_url TEXT,
ADD COLUMN IF NOT EXISTS pay_slip_1_url TEXT,
ADD COLUMN IF NOT EXISTS pay_slip_2_url TEXT,
ADD COLUMN IF NOT EXISTS pay_slip_3_url TEXT;

-- Step 3: Add experience documents workflow tracking
ALTER TABLE staff_employee_kyc 
ADD COLUMN IF NOT EXISTS experience_docs_status VARCHAR(20) DEFAULT 'pending',
ADD COLUMN IF NOT EXISTS experience_docs_verified_by INTEGER REFERENCES staff_employees(id),
ADD COLUMN IF NOT EXISTS experience_docs_verified_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS experience_docs_remarks TEXT;

-- Step 4: Add index for experience docs status filtering
CREATE INDEX IF NOT EXISTS idx_staff_kyc_experience_status ON staff_employee_kyc(experience_docs_status);

-- Verification
SELECT 
    column_name, 
    data_type 
FROM information_schema.columns 
WHERE table_name = 'staff_employee_kyc' 
AND column_name LIKE '%experience%' OR column_name LIKE '%bank_statement%' OR column_name LIKE '%offer_letter%' OR column_name LIKE '%pay_slip%'
ORDER BY column_name;
