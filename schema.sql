-- CRM Data Quality & Duplicate Prevention - demo schema
-- Three tables, matching the raw-snapshot / working-copy / review-queue
-- split described in the project plan.

-- Immutable copy of exactly what was pulled from HubSpot. Never updated
-- after insert - this is the rollback/audit reference.
CREATE TABLE crm_raw_snapshot (
    id SERIAL PRIMARY KEY,
    hubspot_contact_id VARCHAR(50) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    email VARCHAR(255),
    phone VARCHAR(50),
    company_name VARCHAR(255),
    job_title VARCHAR(255),
    industry VARCHAR(100),
    city VARCHAR(100),
    state VARCHAR(100),
    country VARCHAR(100),
    lifecycle_stage VARCHAR(100),
    lead_status VARCHAR(100),
    hubspot_created_date TIMESTAMP,
    pulled_at TIMESTAMP DEFAULT NOW()
);

-- Working copy - all normalization, matching, and merge decisions happen
-- here. Starts as an exact duplicate of crm_raw_snapshot.
CREATE TABLE crm_working_copy (
    id SERIAL PRIMARY KEY,
    hubspot_contact_id VARCHAR(50) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    email VARCHAR(255),
    phone VARCHAR(50),
    company_name VARCHAR(255),
    job_title VARCHAR(255),
    industry VARCHAR(100),
    city VARCHAR(100),
    state VARCHAR(100),
    country VARCHAR(100),
    lifecycle_stage VARCHAR(100),
    lead_status VARCHAR(100),
    -- normalization fields, filled in by the n8n matching step
    normalized_name VARCHAR(200),
    normalized_email VARCHAR(255),
    normalized_phone VARCHAR(50),
    -- merge/lifecycle tracking
    status VARCHAR(20) DEFAULT 'active', -- active | merged | pending_review
    merged_into_id INT REFERENCES crm_working_copy(id),
    owner VARCHAR(100),
    pushed_back_at TIMESTAMP, -- set once the merge result is written back to HubSpot
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Ambiguous candidate pairs awaiting human review via the Lovable UI.
CREATE TABLE dedup_review_queue (
    id SERIAL PRIMARY KEY,
    contact_a_id INT REFERENCES crm_working_copy(id),
    contact_b_id INT REFERENCES crm_working_copy(id),
    confidence_score NUMERIC(5,2) NOT NULL,
    matched_fields TEXT, -- e.g. "name similarity, phone match"
    decision VARCHAR(20) DEFAULT 'pending', -- pending | approved | rejected
    reviewed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_working_copy_normalized_email ON crm_working_copy(normalized_email);
CREATE INDEX idx_working_copy_normalized_phone ON crm_working_copy(normalized_phone);
CREATE INDEX idx_review_queue_decision ON dedup_review_queue(decision);
