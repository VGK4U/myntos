-- ==============================================================================
-- ROLLBACK SCRIPT FOR MYNTOS SAAS WORKFORCE PHASE 1: FOUNDATION MIGRATION
-- Migration Date: September 25, 2026
-- ==============================================================================

DO $$
BEGIN
    -- 1. Rollback staff_kra_templates
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'staff_kra_templates' AND column_name = 'company_id'
    ) THEN
        DROP INDEX IF EXISTS public.idx_staff_kra_templates_company_id;
        ALTER TABLE public.staff_kra_templates DROP COLUMN company_id;
        RAISE NOTICE 'Rolled back company_id from staff_kra_templates';
    END IF;

    -- 2. Rollback staff_tasks
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'staff_tasks' AND column_name = 'company_id'
    ) THEN
        DROP INDEX IF EXISTS public.idx_staff_tasks_company_id;
        ALTER TABLE public.staff_tasks DROP COLUMN company_id;
        RAISE NOTICE 'Rolled back company_id from staff_tasks';
    END IF;

    -- 3. Rollback staff_departments
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'staff_departments' AND column_name = 'company_id'
    ) THEN
        DROP INDEX IF EXISTS public.uq_staff_departments_company_name;
        DROP INDEX IF EXISTS public.idx_staff_departments_company_id;
        ALTER TABLE public.staff_departments DROP COLUMN company_id;
        
        -- Restore global unique constraint if no duplicates exist
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint WHERE conname = 'staff_departments_name_key'
        ) THEN
            ALTER TABLE public.staff_departments ADD CONSTRAINT staff_departments_name_key UNIQUE (name);
        END IF;
        
        RAISE NOTICE 'Rolled back company_id and restored staff_departments_name_key';
    END IF;

END $$;
