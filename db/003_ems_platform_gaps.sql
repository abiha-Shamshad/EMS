-- EMS Release 1 migration 003: storage and grants the API/worker contracts need but 001/002 do not provide.
-- Found while implementing TASK-003..017:
--   * Section 19.3 / DEC-004  "rate limits in PostgreSQL"              -> rate_limits + ems.rate_limit_hit()
--   * API-067                  "Cached 5 minutes per org and role"      -> dashboard_cache
--   * API-008                  link Google to an existing / invited user -> ems.link_google(), ems.pending_invitation_exists()
--   * API-001                  worker_lag_seconds (ems_app cannot see outbox rows without an org) -> ems.outbox_lag_seconds()
--   * TASK-006                 nightly jobs "per company time zone"      -> ems.worker_organizations() (worker cannot list orgs under RLS)
--   * API-027 sweeper, Section 32 retention job (both run in the worker) -> UPDATE (ended_at) / DELETE grants for ems_worker
-- Same conventions as 001/002: objects owned by ems_owner, FORCE RLS on every table, bootstrap functions owned by ems_lookup.
-- Run after 002 as an admin role.

RESET ROLE;
SET ROLE ems_owner;
SET search_path = ems, public;

-- ------------------------------------------------------------------ rate limits (no org context: login, signup, reset)
CREATE TABLE rate_limits (                       -- fixed-window counters; bucket = SHA-256 of "<limit name>|<subject>"
  bucket        bytea NOT NULL,
  window_start  timestamptz NOT NULL,
  hits          integer NOT NULL CHECK (hits >= 1),
  PRIMARY KEY (bucket, window_start)
);
CREATE INDEX ix_rate_limits_window ON rate_limits (window_start);
ALTER TABLE rate_limits ENABLE ROW LEVEL SECURITY;
ALTER TABLE rate_limits FORCE ROW LEVEL SECURITY;  -- no app policy: only ems.rate_limit_hit() touches it

-- ------------------------------------------------------------------ dashboard cache (API-067)
CREATE TABLE dashboard_cache (
  org_id       uuid NOT NULL REFERENCES organizations(id),
  role         text NOT NULL CHECK (role IN ('ceo','cto','cfo','coo','hr','employee')),
  period       text NOT NULL CHECK (period IN ('this_month','last_30_days')),
  scope_user   uuid NOT NULL,                     -- the viewer for the personal employee dashboard; nil UUID otherwise
  payload      jsonb NOT NULL,
  computed_at  timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (org_id, role, period, scope_user)
);
ALTER TABLE dashboard_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE dashboard_cache FORCE ROW LEVEL SECURITY;
CREATE POLICY org_isolation ON dashboard_cache TO ems_app, ems_worker
  USING (org_id = ems.current_org()) WITH CHECK (org_id = ems.current_org());
GRANT SELECT, INSERT, UPDATE ON dashboard_cache TO ems_app;

-- ------------------------------------------------------------------ worker grants
GRANT UPDATE (ended_at) ON stream_views TO ems_worker;                       -- sweeper closes views past the token lifetime
GRANT DELETE ON presence_segments, stream_views, agent_logs, crawl_log, notifications, audit_events TO ems_worker;  -- retention

-- ------------------------------------------------------------------ bootstrap functions
CREATE FUNCTION ems.rate_limit_hit(p_bucket bytea, p_limit integer, p_window_seconds integer)
RETURNS integer LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = ems, pg_temp AS
$$
DECLARE w timestamptz; n integer;
BEGIN
  w := to_timestamp(floor(extract(epoch FROM now()) / p_window_seconds) * p_window_seconds);
  INSERT INTO ems.rate_limits (bucket, window_start, hits) VALUES (p_bucket, w, 1)
  ON CONFLICT (bucket, window_start) DO UPDATE SET hits = ems.rate_limits.hits + 1
  RETURNING hits INTO n;
  IF n = 1 THEN                                                    -- first hit of a window: drop expired windows
    DELETE FROM ems.rate_limits WHERE window_start < now() - interval '1 day';
  END IF;
  IF n <= p_limit THEN RETURN 0; END IF;
  RETURN greatest(1, ceil(extract(epoch FROM (w + make_interval(secs => p_window_seconds) - now())))::integer);  -- Retry-After
END $$;

CREATE FUNCTION ems.link_google(p_user_id uuid, p_google_sub text)
RETURNS boolean LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = ems, pg_temp AS
$$
BEGIN
  UPDATE ems.users SET google_sub = p_google_sub WHERE id = p_user_id AND google_sub IS NULL;
  RETURN FOUND;                                                    -- false: already linked (to this or another Google account)
END $$;

CREATE FUNCTION ems.pending_invitation_exists(p_email text)
RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path = ems, pg_temp AS
$$ SELECT EXISTS (SELECT 1 FROM ems.invitations WHERE email = lower(p_email) AND status = 'pending' AND expires_at > now()) $$;

CREATE FUNCTION ems.outbox_lag_seconds()                          -- API-001 worker_lag_seconds; returns a number only
RETURNS integer LANGUAGE sql STABLE SECURITY DEFINER SET search_path = ems, pg_temp AS
$$ SELECT coalesce(extract(epoch FROM now() - min(created_at))::integer, 0) FROM ems.outbox_events WHERE published_at IS NULL $$;

CREATE FUNCTION ems.worker_organizations()
RETURNS TABLE (org_id uuid, time_zone text, work_hours jsonb) LANGUAGE sql STABLE SECURITY DEFINER SET search_path = ems, pg_temp AS
$$ SELECT id, time_zone, work_hours FROM ems.organizations $$;

DO $$
DECLARE f text;
BEGIN
  FOREACH f IN ARRAY ARRAY['rate_limit_hit(bytea,integer,integer)','link_google(uuid,text)','pending_invitation_exists(text)',
    'outbox_lag_seconds()'] LOOP
    EXECUTE format('ALTER FUNCTION ems.%s OWNER TO ems_lookup', f);
    EXECUTE format('REVOKE ALL ON FUNCTION ems.%s FROM PUBLIC', f);
    EXECUTE format('GRANT EXECUTE ON FUNCTION ems.%s TO ems_app', f);
  END LOOP;
END $$;
ALTER FUNCTION ems.worker_organizations() OWNER TO ems_lookup;
REVOKE ALL ON FUNCTION ems.worker_organizations() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ems.worker_organizations() TO ems_worker;
GRANT SELECT, INSERT, UPDATE, DELETE ON rate_limits TO ems_lookup;
RESET ROLE;
