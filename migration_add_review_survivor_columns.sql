-- Run once against the `portfolio` database.
-- The scoring step already determines which record would survive a merge;
-- this was being discarded before reaching dedup_review_queue, which meant
-- an approval had nothing to act on. Add both explicitly.

ALTER TABLE dedup_review_queue ADD COLUMN IF NOT EXISTS survivor_contact_id INT REFERENCES crm_working_copy(id);
ALTER TABLE dedup_review_queue ADD COLUMN IF NOT EXISTS loser_contact_id INT REFERENCES crm_working_copy(id);
