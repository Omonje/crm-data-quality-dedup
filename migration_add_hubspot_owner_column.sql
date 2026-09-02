-- Run once against the `portfolio` database.
-- The owner-assignment sweep only ever checked our own `owner` column for
-- NULL, but that column starts NULL for every contact regardless of
-- whether HubSpot already had a real assignee - the pull never captured
-- HubSpot's own owner field, so the system couldn't tell "genuinely
-- unassigned" apart from "we never asked." This column carries HubSpot's
-- existing owner forward so the assignment sweep can tell the difference
-- and never overwrite a real existing assignment.

ALTER TABLE crm_working_copy ADD COLUMN IF NOT EXISTS hubspot_owner_id VARCHAR(50);
