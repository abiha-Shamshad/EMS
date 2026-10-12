-- EMS Release 1 migration 004: storage the pre-pilot review fixes need.
--   * Worker stall (worker/main.py): retry state lived in process memory, so 100 failing events at the head of the
--     outbox blocked every company and the counts were lost on restart -> attempts, next_attempt_at, dead on
--     outbox_events, and a scan index that skips dead rows.
--   * Leakage tiles (API-067) showed $0 before the first nightly run -> organizations.leakage_scanned_at, set by the
--     01:00 leakage job when a run completes; dashboards list leakage tiles under `unavailable` while it is NULL.
-- Same conventions as 001-003. Run after 003 as an admin role.

RESET ROLE;
SET ROLE ems_owner;
SET search_path = ems, public;

-- ------------------------------------------------------------------ outbox retry state
ALTER TABLE outbox_events
  ADD COLUMN attempts         integer NOT NULL DEFAULT 0 CHECK (attempts >= 0),
  ADD COLUMN next_attempt_at  timestamptz,                    -- NULL: ready now
  ADD COLUMN dead             boolean NOT NULL DEFAULT false; -- true after the last allowed attempt; never picked up again
CREATE INDEX ix_outbox_ready ON outbox_events (created_at) WHERE published_at IS NULL AND NOT dead;

-- worker_lag_seconds (API-001) measures events still waiting to run; dead events are an operator task, not lag.
CREATE OR REPLACE FUNCTION ems.outbox_lag_seconds()
RETURNS integer LANGUAGE sql STABLE SECURITY DEFINER SET search_path = ems, pg_temp AS
$$ SELECT coalesce(extract(epoch FROM now() - min(created_at))::integer, 0) FROM ems.outbox_events
   WHERE published_at IS NULL AND NOT dead $$;

-- ------------------------------------------------------------------ leakage run marker
ALTER TABLE organizations ADD COLUMN leakage_scanned_at timestamptz;   -- last completed nightly leakage run; NULL = never

RESET ROLE;
