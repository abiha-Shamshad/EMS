-- EMS Release 1 migration 005: storage the HR Agent, Lead Hunter, rule engine and leakage operations (API-035..037,
-- API-055..066) need beyond 001-004.
--   * API-058 "repeat returns the same contact"        -> prospects.contact_id (set on promotion)
--   * API-055 crawler recovery after a worker restart  -> index for picking queued / stalled hunts
--   * API-064 run log filters (rule, outcome, time)      -> index on rule_runs
-- Same conventions as 001-004. Run after 004 as an admin role.

RESET ROLE;
SET ROLE ems_owner;
SET search_path = ems, public;

ALTER TABLE prospects ADD COLUMN contact_id uuid;          -- CRM contact created by API-058; NULL until promoted
ALTER TABLE prospects ADD FOREIGN KEY (org_id, contact_id) REFERENCES contacts (org_id, id);

CREATE INDEX ix_hunts_pending ON hunts (org_id, created_at) WHERE status IN ('queued', 'running');
CREATE INDEX ix_prospects_hunt ON prospects (org_id, hunt_id, score DESC);
CREATE INDEX ix_rule_runs_recent ON rule_runs (org_id, ran_at DESC);
CREATE INDEX ix_findings_open ON leakage_findings (org_id, kind, entity_id) WHERE status = 'open';

RESET ROLE;
