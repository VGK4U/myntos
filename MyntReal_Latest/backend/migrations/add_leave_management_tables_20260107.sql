-- Leave Management System Migration (Jan 2026)
-- DC Protocol Compliant - Company-wise segregation
-- WVV Protocol Compliant - Role-based visibility, immutable audit trail

-- Create enum types for leave management
DO $$ BEGIN
    CREATE TYPE leave_request_status AS ENUM (
        'draft',
        'pending_manager',
        'pending_hr',
        'approved',
        'rejected_manager',
        'rejected_hr',
        'cancelled'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE half_day_type AS ENUM (
        'first_half',
        'second_half'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 1. Staff Leave Types (Master Table)
CREATE TABLE IF NOT EXISTS staff_leave_types (
    id SERIAL PRIMARY KEY,
    code VARCHAR(32) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    monthly_accrual NUMERIC(4,2) NOT NULL DEFAULT 0,
    monthly_accrual_partial NUMERIC(4,2) NOT NULL DEFAULT 0,
    is_accumulative BOOLEAN NOT NULL DEFAULT TRUE,
    max_accumulation NUMERIC(5,2),
    requires_document BOOLEAN NOT NULL DEFAULT FALSE,
    allow_half_day BOOLEAN NOT NULL DEFAULT TRUE,
    max_consecutive_days INTEGER,
    min_advance_days INTEGER NOT NULL DEFAULT 0,
    attendance_status VARCHAR(32) NOT NULL,
    display_order INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_leave_type_code ON staff_leave_types(code);
CREATE INDEX IF NOT EXISTS idx_leave_type_active ON staff_leave_types(is_active);

-- 2. Staff Leave Balances (Per-employee yearly tracking)
CREATE TABLE IF NOT EXISTS staff_leave_balances (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES associated_companies(id) ON DELETE CASCADE,
    employee_id INTEGER NOT NULL REFERENCES staff_employees(id) ON DELETE CASCADE,
    leave_type_id INTEGER NOT NULL REFERENCES staff_leave_types(id) ON DELETE CASCADE,
    year INTEGER NOT NULL,
    opening_balance NUMERIC(5,2) NOT NULL DEFAULT 0,
    accrued NUMERIC(5,2) NOT NULL DEFAULT 0,
    used NUMERIC(5,2) NOT NULL DEFAULT 0,
    balance NUMERIC(5,2) NOT NULL DEFAULT 0,
    last_accrual_month INTEGER,
    last_accrual_date TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_leave_balance_emp_type_year UNIQUE (employee_id, leave_type_id, year)
);

CREATE INDEX IF NOT EXISTS idx_leave_balance_company ON staff_leave_balances(company_id);
CREATE INDEX IF NOT EXISTS idx_leave_balance_employee ON staff_leave_balances(employee_id);
CREATE INDEX IF NOT EXISTS idx_leave_balance_year ON staff_leave_balances(year);

-- 3. Staff Leave Requests (Main Request Table)
CREATE TABLE IF NOT EXISTS staff_leave_requests (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES associated_companies(id) ON DELETE CASCADE,
    employee_id INTEGER NOT NULL REFERENCES staff_employees(id) ON DELETE CASCADE,
    leave_type_id INTEGER NOT NULL REFERENCES staff_leave_types(id) ON DELETE CASCADE,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    is_half_day BOOLEAN NOT NULL DEFAULT FALSE,
    half_day_type VARCHAR(32),
    total_days NUMERIC(4,2) NOT NULL,
    reason TEXT NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'pending_manager',
    manager_id INTEGER REFERENCES staff_employees(id) ON DELETE SET NULL,
    manager_decision_at TIMESTAMP,
    manager_comments TEXT,
    hr_id INTEGER REFERENCES staff_employees(id) ON DELETE SET NULL,
    hr_decision_at TIMESTAMP,
    hr_comments TEXT,
    has_attendance_conflict BOOLEAN NOT NULL DEFAULT FALSE,
    conflict_resolution VARCHAR(32),
    conflicting_dates JSONB,
    submitted_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT check_leave_dates_valid CHECK (end_date >= start_date)
);

CREATE INDEX IF NOT EXISTS idx_leave_request_company ON staff_leave_requests(company_id);
CREATE INDEX IF NOT EXISTS idx_leave_request_employee ON staff_leave_requests(employee_id);
CREATE INDEX IF NOT EXISTS idx_leave_request_status ON staff_leave_requests(status);
CREATE INDEX IF NOT EXISTS idx_leave_request_dates ON staff_leave_requests(start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_leave_request_manager ON staff_leave_requests(manager_id);

-- 4. Staff Leave Request Days (Per-day breakdown)
CREATE TABLE IF NOT EXISTS staff_leave_request_days (
    id SERIAL PRIMARY KEY,
    leave_request_id INTEGER NOT NULL REFERENCES staff_leave_requests(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    is_half_day BOOLEAN NOT NULL DEFAULT FALSE,
    half_day_type VARCHAR(32),
    day_value NUMERIC(3,2) NOT NULL,
    attendance_sheet_id INTEGER REFERENCES staff_attendance_sheets(id) ON DELETE SET NULL,
    is_processed BOOLEAN NOT NULL DEFAULT FALSE,
    processed_at TIMESTAMP,
    had_existing_attendance BOOLEAN NOT NULL DEFAULT FALSE,
    previous_status VARCHAR(32),
    CONSTRAINT uq_leave_request_day UNIQUE (leave_request_id, date)
);

CREATE INDEX IF NOT EXISTS idx_leave_day_request ON staff_leave_request_days(leave_request_id);
CREATE INDEX IF NOT EXISTS idx_leave_day_date ON staff_leave_request_days(date);

-- 5. Staff Leave Approvals (Immutable Audit Trail)
CREATE TABLE IF NOT EXISTS staff_leave_approvals (
    id SERIAL PRIMARY KEY,
    leave_request_id INTEGER NOT NULL REFERENCES staff_leave_requests(id) ON DELETE CASCADE,
    approver_id INTEGER NOT NULL REFERENCES staff_employees(id) ON DELETE SET NULL,
    approver_role VARCHAR(32) NOT NULL,
    action VARCHAR(32) NOT NULL,
    previous_status VARCHAR(32) NOT NULL,
    new_status VARCHAR(32) NOT NULL,
    comments TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_leave_approval_request ON staff_leave_approvals(leave_request_id);
CREATE INDEX IF NOT EXISTS idx_leave_approval_approver ON staff_leave_approvals(approver_id);
CREATE INDEX IF NOT EXISTS idx_leave_approval_created ON staff_leave_approvals(created_at);

-- Seed Leave Types Master Data
INSERT INTO staff_leave_types (code, name, description, monthly_accrual, monthly_accrual_partial, is_accumulative, requires_document, allow_half_day, attendance_status, display_order)
VALUES 
    ('casual_leave', 'Casual Leave', 'Casual leave for personal reasons', 1.0, 0.5, TRUE, FALSE, TRUE, 'casual_leave', 1),
    ('sick_leave', 'Sick Leave', 'Medical/sick leave - requires document for >2 days', 0.5, 0.5, TRUE, TRUE, TRUE, 'sick_leave', 2),
    ('approved_leave', 'Privilege Leave', 'Pre-approved privilege/earned leave', 0, 0, FALSE, FALSE, TRUE, 'approved_leave', 3),
    ('unpaid_leave', 'Unpaid Leave', 'Leave without pay (Loss of Pay)', 0, 0, FALSE, FALSE, TRUE, 'unpaid_leave', 4)
ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    monthly_accrual = EXCLUDED.monthly_accrual,
    monthly_accrual_partial = EXCLUDED.monthly_accrual_partial,
    updated_at = NOW();

-- Add menu entries for leave management
INSERT INTO staff_menu_master (menu_code, menu_name, menu_category, menu_icon, route_path, display_order)
VALUES 
    ('staff_my_leaves', 'My Leaves', 'staff_attendance', 'fas fa-calendar-minus', '/staff/my-leaves', 147),
    ('staff_leave_approvals', 'Leave Approvals', 'staff_attendance', 'fas fa-user-check', '/staff/leave-approvals', 148)
ON CONFLICT (menu_code) DO UPDATE SET
    menu_name = EXCLUDED.menu_name,
    route_path = EXCLUDED.route_path;

COMMIT;
