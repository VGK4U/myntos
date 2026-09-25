-- ==============================================================================
-- MYNTOS SAAS WORKFORCE PHASE 1: FOUNDATION MIGRATION
-- Migration Date: September 25, 2026
-- Safety: Non-destructive, idempotent, preserves existing legacy records
-- Targets: staff_departments, staff_tasks, staff_kra_templates
-- ==============================================================================

DO $$
BEGIN
    -- 1. STAFF_DEPARTMENTS: Add company_id for company-custom departments
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' AND table_name = 'staff_departments' AND column_name = 'company_id'
    ) THEN
        ALTER TABLE public.staff_departments 
        ADD COLUMN company_id INTEGER REFERENCES public.associated_companies(id) ON DELETE SET NULL;
        
        RAISE NOTICE 'Added company_id column to staff_departments';
    END IF;

    -- Index on staff_departments(company_id)
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE schemaname = 'public' AND tablename = 'staff_departments' AND indexname = 'idx_staff_departments_company_id'
    ) THEN
        CREATE INDEX idx_staff_departments_company_id ON public.staff_departments(company_id);
    END IF;

    -- Safely drop global unique constraint if present on public.staff_departments
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'staff_departments_name_key' 
        AND conrelid = 'public.staff_departments'::regclass
    ) THEN
        ALTER TABLE public.staff_departments DROP CONSTRAINT staff_departments_name_key;
        RAISE NOTICE 'Dropped global staff_departments_name_key constraint';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE schemaname = 'public' AND tablename = 'staff_departments' AND indexname = 'uq_staff_departments_company_name'
    ) THEN
        CREATE UNIQUE INDEX uq_staff_departments_company_name 
        ON public.staff_departments (COALESCE(company_id, 0), lower(name));
        RAISE NOTICE 'Created company-scoped unique index on staff_departments(company_id, lower(name))';
    END IF;

    -- 2. STAFF_TASKS: Add company_id for authoritative company ownership
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' AND table_name = 'staff_tasks' AND column_name = 'company_id'
    ) THEN
        ALTER TABLE public.staff_tasks 
        ADD COLUMN company_id INTEGER REFERENCES public.associated_companies(id) ON DELETE CASCADE;
        
        RAISE NOTICE 'Added company_id column to staff_tasks';
    END IF;

    -- Index on staff_tasks(company_id)
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE schemaname = 'public' AND tablename = 'staff_tasks' AND indexname = 'idx_staff_tasks_company_id'
    ) THEN
        CREATE INDEX idx_staff_tasks_company_id ON public.staff_tasks(company_id);
    END IF;

    -- Backfill company_id on existing staff_tasks from created_by or primary_assignee_id
    UPDATE public.staff_tasks t
    SET company_id = COALESCE(
        (SELECT e.base_company_id FROM public.staff_employees e WHERE e.id = t.created_by),
        (SELECT e.base_company_id FROM public.staff_employees e WHERE e.id = t.primary_assignee_id),
        2
    )
    WHERE t.company_id IS NULL;

    -- 3. STAFF_KRA_TEMPLATES: Add company_id for company/tenant scoping
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' AND table_name = 'staff_kra_templates' AND column_name = 'company_id'
    ) THEN
        ALTER TABLE public.staff_kra_templates 
        ADD COLUMN company_id INTEGER REFERENCES public.associated_companies(id) ON DELETE CASCADE;
        
        RAISE NOTICE 'Added company_id column to staff_kra_templates';
    END IF;

    -- Index on staff_kra_templates(company_id)
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE schemaname = 'public' AND tablename = 'staff_kra_templates' AND indexname = 'idx_staff_kra_templates_company_id'
    ) THEN
        CREATE INDEX idx_staff_kra_templates_company_id ON public.staff_kra_templates(company_id);
    END IF;

    -- Backfill company_id on existing staff_kra_templates to company 2 (or creator's base_company_id)
    UPDATE public.staff_kra_templates t
    SET company_id = COALESCE(
        (SELECT e.base_company_id FROM public.staff_employees e WHERE e.id = t.created_by_employee_id),
        2
    )
    WHERE t.company_id IS NULL;

END $$;
