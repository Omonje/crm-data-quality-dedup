-- Resets the CRM Data Quality demo to a clean state so the bulk pull
-- and matching pass can be re-run from scratch (e.g. before recording
-- the Loom). Safe to re-run any time — RESTART IDENTITY puts all three
-- SERIAL primary keys back at 1.
-- Run once against the `portfolio` database.

TRUNCATE TABLE dedup_review_queue, crm_working_copy, crm_raw_snapshot
    RESTART IDENTITY CASCADE;
