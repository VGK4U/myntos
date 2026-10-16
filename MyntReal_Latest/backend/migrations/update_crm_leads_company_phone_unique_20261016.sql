-- Migration: update_crm_leads_company_phone_unique_20261016.sql
-- Purpose: Convert global unique index on crm_leads(phone) to company-scoped unique index (company_id, phone).
-- Allows separate business entities/companies to maintain leads for multi-service customers (e.g. Solar, EV, Insurance)
-- without cross-company UniqueViolation collisions during Meta Lead Ads sync or manual creation.

BEGIN;

-- 1. Create the new company-scoped partial unique index
CREATE UNIQUE INDEX IF NOT EXISTS ux_crm_leads_company_phone 
ON public.crm_leads USING btree (company_id, phone) 
WHERE ((phone IS NOT NULL) AND (TRIM(BOTH FROM phone) <> ''::text));

-- 2. Drop the old global unique index
DROP INDEX IF EXISTS public.ux_crm_leads_phone;

COMMIT;
