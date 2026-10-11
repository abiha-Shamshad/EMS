-- EMS Release 1 canonical schema (executable)
-- Target PostgreSQL 17 on AWS RDS; verified on PostgreSQL 16.13 in the audit sandbox (no 17-only features used).
-- Run once per environment as an admin role. Creates roles, then switches to ems_owner for all objects.

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ems_owner')   THEN CREATE ROLE ems_owner LOGIN; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ems_app')     THEN CREATE ROLE ems_app LOGIN NOBYPASSRLS; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ems_worker')  THEN CREATE ROLE ems_worker LOGIN NOBYPASSRLS; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ems_lookup')  THEN CREATE ROLE ems_lookup NOLOGIN BYPASSRLS; END IF;
END $$;

CREATE EXTENSION IF NOT EXISTS btree_gist;   -- leave-overlap exclusion constraint (available on RDS)
CREATE SCHEMA IF NOT EXISTS ems AUTHORIZATION ems_owner;
GRANT USAGE ON SCHEMA ems TO ems_app, ems_worker, ems_lookup;
GRANT CREATE ON SCHEMA ems TO ems_lookup;
GRANT ems_lookup TO ems_owner;
SET ROLE ems_owner;
SET search_path = ems, public;

CREATE FUNCTION ems.current_org() RETURNS uuid LANGUAGE sql STABLE AS
$$ SELECT nullif(current_setting('app.org_id', true), '')::uuid $$;
CREATE FUNCTION ems.current_user_id() RETURNS uuid LANGUAGE sql STABLE AS
$$ SELECT nullif(current_setting('app.user_id', true), '')::uuid $$;

-- ================================================================== identity and tenancy
CREATE TABLE organizations (
  id          uuid PRIMARY KEY,
  name        text NOT NULL CHECK (length(name) BETWEEN 2 AND 120),
  slug        text NOT NULL UNIQUE CHECK (slug ~ '^[a-z0-9][a-z0-9-]{1,40}$'),
  time_zone   text NOT NULL,
  country     char(2) NOT NULL,
  industry    text,
  size_band   text CHECK (size_band IN ('1-10','11-50','51-200','201-500','500+')),
  setup_state text NOT NULL DEFAULT 'account_created' CHECK (setup_state IN ('account_created','company_setup_done','team_invited','active')),
  version     integer NOT NULL DEFAULT 1,
  created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE users (                                  -- global identity; visible only to self and co-members
  id             uuid PRIMARY KEY,
  email          text NOT NULL UNIQUE CHECK (email = lower(email)),
  name           text NOT NULL,
  password_hash  text,                                -- argon2id; null for Google-only accounts
  google_sub     text UNIQUE,                         -- Google 'sub' claim (stable id), never the email
  created_at     timestamptz NOT NULL DEFAULT now(),
  CHECK (password_hash IS NOT NULL OR google_sub IS NOT NULL)
);

CREATE TABLE auth_sessions (                          -- opaque session tokens; read only via ems.resolve_session()
  id           uuid PRIMARY KEY,
  user_id      uuid NOT NULL REFERENCES users(id),
  token_hash   bytea NOT NULL UNIQUE,
  remember     boolean NOT NULL DEFAULT false,
  expires_at   timestamptz NOT NULL,
  revoked_at   timestamptz,
  created_at   timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE memberships (
  org_id       uuid NOT NULL REFERENCES organizations(id),
  user_id      uuid NOT NULL REFERENCES users(id),
  role         text NOT NULL CHECK (role IN ('ceo','cto','cfo','coo','hr','manager','employee')),
  status       text NOT NULL DEFAULT 'active' CHECK (status IN ('active','deactivated')),
  title        text,
  department   text,
  manager_id   uuid,
  cost_rate    numeric(12,2) CHECK (cost_rate >= 0),     -- internal cost per hour (CFO/CEO only)
  version      integer NOT NULL DEFAULT 1,
  created_at   timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (org_id, user_id),
  FOREIGN KEY (org_id, manager_id) REFERENCES memberships (org_id, user_id)
);
CREATE UNIQUE INDEX ux_one_ceo ON memberships (org_id) WHERE role = 'ceo' AND status = 'active';

CREATE TABLE invitations (
  id          uuid PRIMARY KEY,
  org_id      uuid NOT NULL REFERENCES organizations(id),
  email       text NOT NULL CHECK (email = lower(email)),
  role        text NOT NULL CHECK (role IN ('cto','cfo','coo','hr','manager','employee')),
  token_hash  bytea NOT NULL UNIQUE,
  message     text CHECK (length(message) <= 300),
  status      text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','accepted','expired','revoked')),
  invited_by  uuid NOT NULL,
  expires_at  timestamptz NOT NULL,
  created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX ux_invite_pending ON invitations (org_id, email) WHERE status = 'pending';

-- ================================================================== employee room
CREATE TABLE stream_consents (
  org_id          uuid NOT NULL,
  user_id         uuid NOT NULL,
  policy_version  integer NOT NULL,
  consented_at    timestamptz NOT NULL DEFAULT now(),
  revoked_at      timestamptz,
  PRIMARY KEY (org_id, user_id, policy_version),
  FOREIGN KEY (org_id, user_id) REFERENCES memberships (org_id, user_id)
);

CREATE TABLE work_sessions (
  id           uuid PRIMARY KEY,
  org_id       uuid NOT NULL,
  user_id      uuid NOT NULL,
  started_at   timestamptz NOT NULL,
  ended_at     timestamptz,
  state        text NOT NULL DEFAULT 'open' CHECK (state IN ('open','closed','auto_closed')),
  current_task_id uuid,
  last_heartbeat_at timestamptz,
  presence     text NOT NULL DEFAULT 'active' CHECK (presence IN ('active','idle','locked','on_break','offline')),
  streaming    boolean NOT NULL DEFAULT false,
  UNIQUE (org_id, id),
  FOREIGN KEY (org_id, user_id) REFERENCES memberships (org_id, user_id),
  CHECK ((state = 'open') = (ended_at IS NULL))
);
CREATE UNIQUE INDEX ux_one_open_session ON work_sessions (org_id, user_id) WHERE state = 'open';

CREATE TABLE presence_segments (                      -- closed intervals of one presence state
  id           uuid PRIMARY KEY,
  org_id       uuid NOT NULL,
  session_id   uuid NOT NULL,
  user_id      uuid NOT NULL,
  presence     text NOT NULL CHECK (presence IN ('active','idle','locked','on_break','offline')),
  task_id      uuid,
  started_at   timestamptz NOT NULL,
  ended_at     timestamptz NOT NULL,
  CHECK (ended_at > started_at),
  FOREIGN KEY (org_id, session_id) REFERENCES work_sessions (org_id, id)
);
CREATE INDEX ix_segments_user_day ON presence_segments (org_id, user_id, started_at);

CREATE TABLE breaks (
  id            uuid PRIMARY KEY,
  org_id        uuid NOT NULL,
  session_id    uuid NOT NULL,
  user_id       uuid NOT NULL,
  kind          text NOT NULL CHECK (kind IN ('short','lunch','prayer','personal')),
  status        text NOT NULL CHECK (status IN ('requested','approved','rejected','active','ended')),
  requested_minutes integer NOT NULL CHECK (requested_minutes BETWEEN 5 AND 120),
  decided_by    uuid,
  started_at    timestamptz,
  ended_at      timestamptz,
  created_at    timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY (org_id, session_id) REFERENCES work_sessions (org_id, id)
);
CREATE UNIQUE INDEX ux_one_active_break ON breaks (org_id, user_id) WHERE status = 'active';

CREATE TABLE stream_views (                           -- every live view is recorded and shown to the employee
  id               uuid PRIMARY KEY,
  org_id           uuid NOT NULL,
  viewer_id        uuid NOT NULL,
  subject_user_id  uuid NOT NULL,
  reason           text NOT NULL CHECK (length(reason) BETWEEN 3 AND 200),
  started_at       timestamptz NOT NULL DEFAULT now(),
  ended_at         timestamptz,
  FOREIGN KEY (org_id, viewer_id) REFERENCES memberships (org_id, user_id),
  FOREIGN KEY (org_id, subject_user_id) REFERENCES memberships (org_id, user_id)
);

-- ================================================================== HRM
CREATE TABLE leave_requests (
  id          uuid PRIMARY KEY,
  org_id      uuid NOT NULL,
  user_id     uuid NOT NULL,
  kind        text NOT NULL CHECK (kind IN ('annual','sick','casual','unpaid')),
  period      daterange NOT NULL CHECK (NOT isempty(period)),
  reason      text CHECK (length(reason) <= 500),
  status      text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','approved','rejected','cancelled')),
  decided_by  uuid,
  decided_at  timestamptz,
  version     integer NOT NULL DEFAULT 1,
  created_at  timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY (org_id, user_id) REFERENCES memberships (org_id, user_id),
  EXCLUDE USING gist (org_id WITH =, user_id WITH =, period WITH &&) WHERE (status IN ('pending','approved'))
);

-- ================================================================== CRM and client lifecycle
CREATE TABLE companies (
  id          uuid PRIMARY KEY,
  org_id      uuid NOT NULL,
  name        text NOT NULL,
  domain      text CHECK (domain = lower(domain)),
  industry    text,
  created_at  timestamptz NOT NULL DEFAULT now(),
  UNIQUE (org_id, id)
);
CREATE UNIQUE INDEX ux_company_domain ON companies (org_id, domain) WHERE domain IS NOT NULL;

CREATE TABLE contacts (
  id              uuid PRIMARY KEY,
  org_id          uuid NOT NULL,
  company_id      uuid,
  name            text NOT NULL,
  email           text CHECK (email = lower(email)),
  phone           text,
  lifecycle_stage text NOT NULL DEFAULT 'lead' CHECK (lifecycle_stage IN ('lead','qualified','opportunity','customer','churned','disqualified')),
  owner_id        uuid,
  source          text NOT NULL CHECK (source IN ('manual','import','lead_hunter','referral','website')),
  version         integer NOT NULL DEFAULT 1,
  created_at      timestamptz NOT NULL DEFAULT now(),
  UNIQUE (org_id, id),
  FOREIGN KEY (org_id, company_id) REFERENCES companies (org_id, id),
  FOREIGN KEY (org_id, owner_id) REFERENCES memberships (org_id, user_id)
);
CREATE UNIQUE INDEX ux_contact_email ON contacts (org_id, email) WHERE email IS NOT NULL;

CREATE TABLE deals (
  id             uuid PRIMARY KEY,
  org_id         uuid NOT NULL,
  contact_id     uuid NOT NULL,
  company_id     uuid,
  title          text NOT NULL,
  stage          text NOT NULL DEFAULT 'new' CHECK (stage IN ('new','qualified','proposal','negotiation','won','lost')),
  amount         numeric(14,2) NOT NULL CHECK (amount >= 0),
  currency       char(3) NOT NULL,
  owner_id       uuid NOT NULL,
  expected_close date,
  last_activity_at timestamptz NOT NULL DEFAULT now(),
  won_at         timestamptz,
  lost_reason    text,
  version        integer NOT NULL DEFAULT 1,
  created_at     timestamptz NOT NULL DEFAULT now(),
  UNIQUE (org_id, id),
  FOREIGN KEY (org_id, contact_id) REFERENCES contacts (org_id, id),
  FOREIGN KEY (org_id, owner_id) REFERENCES memberships (org_id, user_id),
  CHECK ((stage = 'won') = (won_at IS NOT NULL)),
  CHECK (stage <> 'lost' OR lost_reason IS NOT NULL)
);
CREATE INDEX ix_deals_pipeline ON deals (org_id, stage, last_activity_at);

CREATE TABLE clients (
  id              uuid PRIMARY KEY,
  org_id          uuid NOT NULL,
  company_id      uuid NOT NULL,
  origin_deal_id  uuid NOT NULL,
  status          text NOT NULL DEFAULT 'onboarding' CHECK (status IN ('onboarding','active','at_risk','churned')),
  since           date NOT NULL,
  renewal_date    date,
  UNIQUE (org_id, id),
  UNIQUE (org_id, origin_deal_id),
  FOREIGN KEY (org_id, company_id) REFERENCES companies (org_id, id),
  FOREIGN KEY (org_id, origin_deal_id) REFERENCES deals (org_id, id)
);

CREATE TABLE activities (
  id           uuid PRIMARY KEY,
  org_id       uuid NOT NULL,
  entity_type  text NOT NULL CHECK (entity_type IN ('contact','deal','client','project','task','employee')),
  entity_id    uuid NOT NULL,
  kind         text NOT NULL CHECK (kind IN ('note','call','email','meeting','stage_change','system')),
  note         text CHECK (length(note) <= 2000),
  actor_id     uuid,
  occurred_at  timestamptz NOT NULL,
  created_at   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_activities_entity ON activities (org_id, entity_type, entity_id, occurred_at);

-- ================================================================== projects and work
CREATE TABLE projects (
  id            uuid PRIMARY KEY,
  org_id        uuid NOT NULL,
  client_id     uuid,
  name          text NOT NULL,
  status        text NOT NULL DEFAULT 'planned' CHECK (status IN ('planned','active','on_hold','completed','cancelled')),
  billing_type  text NOT NULL CHECK (billing_type IN ('fixed','hourly','retainer','internal')),
  budget_amount numeric(14,2) CHECK (budget_amount >= 0),
  hourly_rate   numeric(12,2) CHECK (hourly_rate >= 0),
  currency      char(3),
  owner_id      uuid NOT NULL,
  version       integer NOT NULL DEFAULT 1,
  created_at    timestamptz NOT NULL DEFAULT now(),
  UNIQUE (org_id, id),
  FOREIGN KEY (org_id, client_id) REFERENCES clients (org_id, id),
  FOREIGN KEY (org_id, owner_id) REFERENCES memberships (org_id, user_id),
  CHECK (billing_type <> 'hourly' OR (hourly_rate IS NOT NULL AND currency IS NOT NULL)),
  CHECK (billing_type = 'internal' OR client_id IS NOT NULL)
);

CREATE TABLE tasks (
  id               uuid PRIMARY KEY,
  org_id           uuid NOT NULL,
  project_id       uuid NOT NULL,
  title            text NOT NULL CHECK (length(title) BETWEEN 1 AND 200),
  status           text NOT NULL DEFAULT 'todo' CHECK (status IN ('todo','active','review','done')),
  assignee_id      uuid,
  due_at           timestamptz,
  estimate_minutes integer CHECK (estimate_minutes > 0),
  billable         boolean NOT NULL DEFAULT true,
  position         integer NOT NULL DEFAULT 0,
  version          integer NOT NULL DEFAULT 1,
  created_at       timestamptz NOT NULL DEFAULT now(),
  UNIQUE (org_id, id),
  FOREIGN KEY (org_id, project_id) REFERENCES projects (org_id, id),
  FOREIGN KEY (org_id, assignee_id) REFERENCES memberships (org_id, user_id)
);
CREATE INDEX ix_tasks_board ON tasks (org_id, project_id, status, position);

CREATE TABLE time_entries (
  id          uuid PRIMARY KEY,
  org_id      uuid NOT NULL,
  task_id     uuid NOT NULL,
  user_id     uuid NOT NULL,
  started_at  timestamptz NOT NULL,
  minutes     integer NOT NULL CHECK (minutes BETWEEN 1 AND 1440),
  source      text NOT NULL CHECK (source IN ('manual','room')),
  billable    boolean NOT NULL,
  invoice_id  uuid,
  created_at  timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY (org_id, task_id) REFERENCES tasks (org_id, id),
  FOREIGN KEY (org_id, user_id) REFERENCES memberships (org_id, user_id)
);

CREATE TABLE invoices (
  id          uuid PRIMARY KEY,
  org_id      uuid NOT NULL,
  client_id   uuid NOT NULL,
  project_id  uuid,
  number      text NOT NULL,
  amount      numeric(14,2) NOT NULL CHECK (amount > 0),
  currency    char(3) NOT NULL,
  issued_on   date NOT NULL,
  due_on      date NOT NULL CHECK (due_on >= issued_on),
  status      text NOT NULL DEFAULT 'sent' CHECK (status IN ('draft','sent','partially_paid','paid','void')),
  version     integer NOT NULL DEFAULT 1,
  created_at  timestamptz NOT NULL DEFAULT now(),
  UNIQUE (org_id, id),
  UNIQUE (org_id, number),
  FOREIGN KEY (org_id, client_id) REFERENCES clients (org_id, id)
);
ALTER TABLE time_entries ADD FOREIGN KEY (org_id, invoice_id) REFERENCES invoices (org_id, id);

CREATE TABLE payments (
  id          uuid PRIMARY KEY,
  org_id      uuid NOT NULL,
  invoice_id  uuid NOT NULL,
  amount      numeric(14,2) NOT NULL CHECK (amount > 0),
  received_on date NOT NULL,
  method      text NOT NULL CHECK (method IN ('bank_transfer','card','cash','cheque','other')),
  created_at  timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY (org_id, invoice_id) REFERENCES invoices (org_id, id)
);

-- ================================================================== lead hunter
CREATE TABLE hunts (
  id          uuid PRIMARY KEY,
  org_id      uuid NOT NULL,
  name        text NOT NULL,
  seeds       jsonb NOT NULL,                         -- {"domains":[...]} supplied by the user; no search-engine scraping
  icp         jsonb NOT NULL,                         -- ideal-customer-profile rule set
  status      text NOT NULL DEFAULT 'queued' CHECK (status IN ('queued','running','completed','failed','cancelled')),
  stats       jsonb NOT NULL DEFAULT '{}',
  created_by  uuid NOT NULL,
  created_at  timestamptz NOT NULL DEFAULT now(),
  UNIQUE (org_id, id)
);

CREATE TABLE prospects (
  id             uuid PRIMARY KEY,
  org_id         uuid NOT NULL,
  hunt_id        uuid NOT NULL,
  domain         text NOT NULL CHECK (domain = lower(domain)),
  company_name   text,
  public_emails  text[] NOT NULL DEFAULT '{}',        -- only role addresses published on the site (info@, sales@ ...)
  signals        jsonb NOT NULL DEFAULT '{}',
  score          integer NOT NULL CHECK (score BETWEEN 0 AND 100),
  score_reasons  jsonb NOT NULL DEFAULT '[]',
  status         text NOT NULL DEFAULT 'new' CHECK (status IN ('new','promoted','discarded','suppressed')),
  source_url     text NOT NULL,
  fetched_at     timestamptz NOT NULL,
  FOREIGN KEY (org_id, hunt_id) REFERENCES hunts (org_id, id)
);
CREATE UNIQUE INDEX ux_prospect_domain ON prospects (org_id, domain);

CREATE TABLE crawl_log (
  id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  org_id          uuid NOT NULL,
  hunt_id         uuid NOT NULL,
  url             text NOT NULL,
  robots_decision text NOT NULL CHECK (robots_decision IN ('allowed','disallowed','unreachable_blocked')),
  http_status     integer,
  fetched_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE suppression_list (
  org_id      uuid NOT NULL,
  kind        text NOT NULL CHECK (kind IN ('email','domain')),
  value_hash  bytea NOT NULL,
  reason      text NOT NULL CHECK (reason IN ('opt_out','bounced','manual','legal')),
  created_at  timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (org_id, kind, value_hash)
);

-- ================================================================== rules, agent, leakage, graph memory
CREATE TABLE rules (
  id          uuid PRIMARY KEY,
  org_id      uuid NOT NULL,
  key         text NOT NULL CHECK (key ~ '^[a-z0-9_]{3,60}$'),
  version     integer NOT NULL,
  trigger     text NOT NULL,
  definition  jsonb NOT NULL,
  enabled     boolean NOT NULL DEFAULT true,
  created_by  uuid NOT NULL,
  created_at  timestamptz NOT NULL DEFAULT now(),
  UNIQUE (org_id, id),
  UNIQUE (org_id, key, version)
);

CREATE TABLE rule_runs (
  id            uuid PRIMARY KEY,
  org_id        uuid NOT NULL,
  rule_id       uuid NOT NULL,
  event_id      uuid NOT NULL,
  outcome       text NOT NULL CHECK (outcome IN ('matched','not_matched','action_failed','skipped_loop')),
  actions       jsonb NOT NULL DEFAULT '[]',
  ran_at        timestamptz NOT NULL DEFAULT now(),
  UNIQUE (rule_id, event_id),
  FOREIGN KEY (org_id, rule_id) REFERENCES rules (org_id, id)
);

CREATE TABLE leakage_findings (
  id              uuid PRIMARY KEY,
  org_id          uuid NOT NULL,
  kind            text NOT NULL CHECK (kind IN ('unbilled_time','overdue_invoice','stale_deal','won_without_project','won_without_invoice','over_budget','idle_paid_time','retainer_underused')),
  entity_type     text NOT NULL,
  entity_id       uuid NOT NULL,
  fingerprint     text NOT NULL,
  amount_at_risk  numeric(14,2),
  currency        char(3),
  evidence        jsonb NOT NULL,
  status          text NOT NULL DEFAULT 'open' CHECK (status IN ('open','resolved','dismissed')),
  detected_at     timestamptz NOT NULL DEFAULT now(),
  resolved_by     uuid,
  resolved_at     timestamptz,
  UNIQUE (org_id, fingerprint)
);

CREATE TABLE graph_nodes (
  id       uuid PRIMARY KEY,
  org_id   uuid NOT NULL,
  kind     text NOT NULL CHECK (kind IN ('person','client','company','contact','deal','project','task','invoice','skill')),
  ref_id   uuid NOT NULL,
  label    text NOT NULL,
  UNIQUE (org_id, id),
  UNIQUE (org_id, kind, ref_id)
);

CREATE TABLE graph_edges (
  id          uuid PRIMARY KEY,
  org_id      uuid NOT NULL,
  src         uuid NOT NULL,
  dst         uuid NOT NULL,
  kind        text NOT NULL CHECK (kind IN ('works_on','owns','manages','belongs_to','billed_by','originated_from','contact_of','has_skill','reports_to')),
  weight      real NOT NULL DEFAULT 1 CHECK (weight > 0),
  evidence    text NOT NULL,
  valid_from  timestamptz NOT NULL DEFAULT now(),
  valid_to    timestamptz,
  FOREIGN KEY (org_id, src) REFERENCES graph_nodes (org_id, id),
  FOREIGN KEY (org_id, dst) REFERENCES graph_nodes (org_id, id),
  CHECK (src <> dst)
);
CREATE UNIQUE INDEX ux_edge_current ON graph_edges (org_id, src, dst, kind) WHERE valid_to IS NULL;
CREATE INDEX ix_edges_src ON graph_edges (org_id, src) WHERE valid_to IS NULL;
CREATE INDEX ix_edges_dst ON graph_edges (org_id, dst) WHERE valid_to IS NULL;

CREATE TABLE agent_logs (                             -- intent only; the question text is not stored
  id          uuid PRIMARY KEY,
  org_id      uuid NOT NULL,
  asker_id    uuid NOT NULL,
  intent      text NOT NULL,
  answered    boolean NOT NULL,
  created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE notifications (
  id          uuid PRIMARY KEY,
  org_id      uuid NOT NULL,
  user_id     uuid NOT NULL,
  kind        text NOT NULL,
  title       text NOT NULL,
  ref_type    text,
  ref_id      uuid,
  read_at     timestamptz,
  created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_notifications_user ON notifications (org_id, user_id, created_at DESC);

CREATE TABLE audit_events (
  id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  org_id        uuid NOT NULL,
  actor_id      uuid,
  action        text NOT NULL,
  record_type   text,
  record_id     uuid,
  changed_fields text[],
  request_id    text,
  occurred_at   timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE outbox_events (
  id            uuid PRIMARY KEY,
  org_id        uuid NOT NULL,
  routing_key   text NOT NULL,
  payload       jsonb NOT NULL,
  created_at    timestamptz NOT NULL DEFAULT now(),
  published_at  timestamptz
);
CREATE INDEX ix_outbox_unpublished ON outbox_events (created_at) WHERE published_at IS NULL;

CREATE TABLE idempotency_keys (
  org_id         uuid NOT NULL,
  actor_id       uuid NOT NULL,
  route          text NOT NULL,
  key            text NOT NULL CHECK (length(key) BETWEEN 8 AND 100),
  request_hash   bytea NOT NULL,
  state          text NOT NULL CHECK (state IN ('in_progress','completed')),
  response_code  integer,
  response_body  jsonb,
  expires_at     timestamptz NOT NULL,
  PRIMARY KEY (org_id, actor_id, route, key)
);

-- ================================================================== row-level security
DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['memberships','invitations','stream_consents','work_sessions','presence_segments','breaks',
    'stream_views','leave_requests','companies','contacts','deals','clients','activities','projects','tasks','time_entries',
    'invoices','payments','hunts','prospects','crawl_log','suppression_list','rules','rule_runs','leakage_findings',
    'graph_nodes','graph_edges','agent_logs','notifications','audit_events','outbox_events','idempotency_keys']
  LOOP
    EXECUTE format('ALTER TABLE ems.%I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('ALTER TABLE ems.%I FORCE ROW LEVEL SECURITY', t);
    EXECUTE format('CREATE POLICY org_isolation ON ems.%I TO ems_app, ems_worker USING (org_id = ems.current_org()) WITH CHECK (org_id = ems.current_org())', t);
  END LOOP;
END $$;
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE organizations FORCE ROW LEVEL SECURITY;
CREATE POLICY org_isolation ON organizations TO ems_app, ems_worker USING (id = ems.current_org()) WITH CHECK (id = ems.current_org());
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE users FORCE ROW LEVEL SECURITY;
CREATE POLICY user_visibility ON users FOR SELECT TO ems_app, ems_worker USING (
  id = ems.current_user_id() OR EXISTS (SELECT 1 FROM ems.memberships m WHERE m.user_id = users.id));
ALTER TABLE auth_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE auth_sessions FORCE ROW LEVEL SECURITY;      -- no policy for app roles: only lookup functions touch it

-- Worker cross-org scan: only unpublished outbox rows (IDs and routing keys) are visible without org context.
CREATE POLICY outbox_scan ON outbox_events FOR SELECT TO ems_worker USING (published_at IS NULL);
CREATE POLICY outbox_mark ON outbox_events FOR UPDATE TO ems_worker USING (published_at IS NULL) WITH CHECK (true);

GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA ems TO ems_app, ems_worker;
GRANT DELETE ON idempotency_keys, notifications TO ems_app;
REVOKE UPDATE ON audit_events, activities, presence_segments, stream_views, rule_runs, crawl_log, agent_logs, payments FROM ems_app, ems_worker;
GRANT UPDATE (ended_at) ON stream_views TO ems_app;
REVOKE ALL ON users, auth_sessions FROM ems_app, ems_worker;
GRANT SELECT (id, email, name, created_at) ON users TO ems_app, ems_worker;

-- ================================================================== bootstrap lookups (before org context exists)
CREATE FUNCTION ems.signup_company(p_user_id uuid, p_email text, p_name text, p_password_hash text, p_google_sub text,
                                   p_org_id uuid, p_org_name text, p_slug text, p_tz text, p_country text)
RETURNS uuid LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = ems, pg_temp AS
$$
BEGIN
  INSERT INTO ems.users (id, email, name, password_hash, google_sub) VALUES (p_user_id, lower(p_email), p_name, p_password_hash, p_google_sub);
  INSERT INTO ems.organizations (id, name, slug, time_zone, country) VALUES (p_org_id, p_org_name, p_slug, p_tz, p_country);
  INSERT INTO ems.memberships (org_id, user_id, role) VALUES (p_org_id, p_user_id, 'ceo');
  RETURN p_org_id;
END $$;

CREATE FUNCTION ems.find_user_for_login(p_email text)
RETURNS TABLE (user_id uuid, password_hash text) LANGUAGE sql STABLE SECURITY DEFINER SET search_path = ems, pg_temp AS
$$ SELECT id, password_hash FROM ems.users WHERE email = lower(p_email) $$;

CREATE FUNCTION ems.find_user_by_google(p_sub text)
RETURNS TABLE (user_id uuid) LANGUAGE sql STABLE SECURITY DEFINER SET search_path = ems, pg_temp AS
$$ SELECT id FROM ems.users WHERE google_sub = p_sub $$;

CREATE FUNCTION ems.create_session(p_id uuid, p_user_id uuid, p_token_hash bytea, p_remember boolean)
RETURNS timestamptz LANGUAGE sql VOLATILE SECURITY DEFINER SET search_path = ems, pg_temp AS
$$ INSERT INTO ems.auth_sessions (id, user_id, token_hash, remember, expires_at)
   VALUES (p_id, p_user_id, p_token_hash, p_remember, now() + CASE WHEN p_remember THEN interval '30 days' ELSE interval '12 hours' END)
   RETURNING expires_at $$;

CREATE FUNCTION ems.resolve_session(p_token_hash bytea)
RETURNS TABLE (user_id uuid, expires_at timestamptz) LANGUAGE sql STABLE SECURITY DEFINER SET search_path = ems, pg_temp AS
$$ SELECT user_id, expires_at FROM ems.auth_sessions
   WHERE token_hash = p_token_hash AND revoked_at IS NULL AND expires_at > now() $$;

CREATE FUNCTION ems.revoke_session(p_token_hash bytea)
RETURNS void LANGUAGE sql VOLATILE SECURITY DEFINER SET search_path = ems, pg_temp AS
$$ UPDATE ems.auth_sessions SET revoked_at = now() WHERE token_hash = p_token_hash AND revoked_at IS NULL $$;

CREATE FUNCTION ems.user_memberships(p_user_id uuid)
RETURNS TABLE (org_id uuid, role text, status text) LANGUAGE sql STABLE SECURITY DEFINER SET search_path = ems, pg_temp AS
$$ SELECT org_id, role, status FROM ems.memberships WHERE user_id = p_user_id $$;

CREATE FUNCTION ems.resolve_invitation(p_token_hash bytea)
RETURNS TABLE (invitation_id uuid, org_id uuid, email text, role text, status text, expires_at timestamptz)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = ems, pg_temp AS
$$ SELECT id, org_id, email, role, status, expires_at FROM ems.invitations WHERE token_hash = p_token_hash $$;

CREATE FUNCTION ems.accept_invitation(p_token_hash bytea, p_user_id uuid)
RETURNS uuid LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = ems, pg_temp AS
$$
DECLARE inv record; u record;
BEGIN
  SELECT * INTO inv FROM ems.invitations WHERE token_hash = p_token_hash FOR UPDATE;
  IF inv IS NULL OR inv.status <> 'pending' OR inv.expires_at < now() THEN RAISE EXCEPTION 'INVITATION_INVALID' USING ERRCODE = 'P0001'; END IF;
  SELECT * INTO u FROM ems.users WHERE id = p_user_id;
  IF u.email <> inv.email THEN RAISE EXCEPTION 'INVITATION_EMAIL_MISMATCH' USING ERRCODE = 'P0001'; END IF;
  INSERT INTO ems.memberships (org_id, user_id, role) VALUES (inv.org_id, p_user_id, inv.role);
  UPDATE ems.invitations SET status = 'accepted' WHERE id = inv.id;
  RETURN inv.org_id;
END $$;

CREATE FUNCTION ems.create_user(p_user_id uuid, p_email text, p_name text, p_password_hash text, p_google_sub text)
RETURNS uuid LANGUAGE sql VOLATILE SECURITY DEFINER SET search_path = ems, pg_temp AS
$$ INSERT INTO ems.users (id, email, name, password_hash, google_sub) VALUES (p_user_id, lower(p_email), p_name, p_password_hash, p_google_sub) RETURNING id $$;

DO $$
DECLARE f text;
BEGIN
  FOREACH f IN ARRAY ARRAY['signup_company(uuid,text,text,text,text,uuid,text,text,text,text)','find_user_for_login(text)',
    'find_user_by_google(text)','create_session(uuid,uuid,bytea,boolean)','resolve_session(bytea)','revoke_session(bytea)',
    'user_memberships(uuid)','resolve_invitation(bytea)','accept_invitation(bytea,uuid)','create_user(uuid,text,text,text,text)']
  LOOP
    EXECUTE format('ALTER FUNCTION ems.%s OWNER TO ems_lookup', f);
    EXECUTE format('REVOKE ALL ON FUNCTION ems.%s FROM PUBLIC', f);
    EXECUTE format('GRANT EXECUTE ON FUNCTION ems.%s TO ems_app', f);
  END LOOP;
END $$;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA ems TO ems_lookup;

-- ================================================================== graph memory query (runs under the caller's RLS)
CREATE FUNCTION ems.graph_neighbors(p_node uuid, p_max_depth integer)
RETURNS TABLE (node_id uuid, kind text, label text, depth integer, path_kinds text[])
LANGUAGE sql STABLE SECURITY INVOKER SET search_path = ems, pg_temp AS
$$
  WITH RECURSIVE walk(node_id, depth, path, kinds) AS (
    SELECT p_node, 0, ARRAY[p_node], ARRAY[]::text[]
    UNION ALL
    SELECT CASE WHEN e.src = w.node_id THEN e.dst ELSE e.src END, w.depth + 1,
           w.path || CASE WHEN e.src = w.node_id THEN e.dst ELSE e.src END, w.kinds || e.kind
    FROM walk w
    JOIN ems.graph_edges e ON e.valid_to IS NULL AND (e.src = w.node_id OR e.dst = w.node_id)
    WHERE w.depth < least(p_max_depth, 3)
      AND NOT (CASE WHEN e.src = w.node_id THEN e.dst ELSE e.src END) = ANY (w.path)
  )
  SELECT DISTINCT ON (n.id) n.id, n.kind, n.label, w.depth, w.kinds
  FROM walk w JOIN ems.graph_nodes n ON n.id = w.node_id
  WHERE w.depth > 0
  ORDER BY n.id, w.depth
$$;
GRANT EXECUTE ON FUNCTION ems.graph_neighbors(uuid, integer) TO ems_app, ems_worker;
