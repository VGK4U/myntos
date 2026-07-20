-- Phase 3a.2 — add seat_count to platform_subscriptions
-- Seat = staff login count for the tenant (operator-edited, default 1).
-- Reused by per-seat module pricing math (per_seat unit) and pro-rata billing.

ALTER TABLE platform_subscriptions
    ADD COLUMN IF NOT EXISTS seat_count INTEGER NOT NULL DEFAULT 1;

ALTER TABLE platform_subscriptions
    DROP CONSTRAINT IF EXISTS platform_sub_seat_count_check;
ALTER TABLE platform_subscriptions
    ADD CONSTRAINT platform_sub_seat_count_check CHECK (seat_count >= 1);
