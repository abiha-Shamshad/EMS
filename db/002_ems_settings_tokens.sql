-- EMS Release 1 migration 002: company settings, HR policies, reset and extension tokens, contact search.
-- Found during contract review: API-005/006 (password reset), API-010 (work hours), API-018/019 (extension token),
-- API-036/037 (HR policies) and API-046 (contact search) had no storage in 001. Run after 001 as an admin role.

RESET ROLE;                                  -- 001 leaves the session as ems_owner when run in one psql call
CREATE EXTENSION IF NOT EXISTS pg_trgm;      -- contact search (available on RDS)
SET ROLE ems_owner;
SET search_path = ems, public;

-- ------------------------------------------------------------------ company settings
ALTER TABLE organizations
  ADD COLUMN work_hours jsonb NOT NULL DEFAULT
    '{"days":["mon","tue","wed","thu","fri"],"start":"09:00","end":"18:00","late_grace_minutes":10}',
  ADD COLUMN live_view_enabled boolean NOT NULL DEFAULT false,      -- off until the company accepts OD-02 conditions
  ADD COLUMN room_policy_version integer NOT NULL DEFAULT 1 CHECK (room_policy_version >= 1),
  ADD COLUMN daily_break_allowance_minutes integer NOT NULL DEFAULT 60 CHECK (daily_break_allowance_minutes BETWEEN 0 AND 240),
  ADD COLUMN base_currency char(3) NOT NULL DEFAULT 'USD' CHECK (base_currency ~ '^[A-Z]{3}$');

-- ------------------------------------------------------------------ HR policies quoted by the HR Agent
CREATE TABLE hr_policies (
  org_id        uuid NOT NULL REFERENCES organizations(id),
  topic         text NOT NULL CHECK (topic IN ('leave','attendance','breaks','general','monitoring')),
  version       integer NOT NULL CHECK (version >= 1),
  text          text NOT NULL CHECK (length(text) BETWEEN 10 AND 5000),
  rules         jsonb NOT NULL DEFAULT '{}',
  published_by  uuid NOT NULL,
  published_at  timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (org_id, topic, version)
);

-- ------------------------------------------------------------------ password reset tokens (bootstrap: no org context)
CREATE TABLE password_resets (
  token_hash  bytea PRIMARY KEY,
  user_id     uuid NOT NULL REFERENCES users(id),
  expires_at  timestamptz NOT NULL,
  used_at     timestamptz,
  created_at  timestamptz NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------------ extension bearer tokens (one per open work session)
CREATE TABLE extension_tokens (
  token_hash  bytea PRIMARY KEY,
  org_id      uuid NOT NULL,
  user_id     uuid NOT NULL,
  session_id  uuid NOT NULL,
  expires_at  timestamptz NOT NULL,
  revoked_at  timestamptz,
  created_at  timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY (org_id, user_id) REFERENCES memberships (org_id, user_id),
  FOREIGN KEY (org_id, session_id) REFERENCES work_sessions (org_id, id)
);

CREATE INDEX ix_contacts_trgm ON contacts USING gin ((lower(name) || ' ' || coalesce(email, '')) gin_trgm_ops);

DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['hr_policies','extension_tokens'] LOOP
    EXECUTE format('ALTER TABLE ems.%I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('ALTER TABLE ems.%I FORCE ROW LEVEL SECURITY', t);
    EXECUTE format('CREATE POLICY org_isolation ON ems.%I TO ems_app, ems_worker USING (org_id = ems.current_org()) WITH CHECK (org_id = ems.current_org())', t);
  END LOOP;
END $$;
ALTER TABLE password_resets ENABLE ROW LEVEL SECURITY;
ALTER TABLE password_resets FORCE ROW LEVEL SECURITY;  -- no app policy: functions only
GRANT SELECT, INSERT ON hr_policies TO ems_app, ems_worker;           -- policies are versioned, never updated
GRANT SELECT, INSERT, UPDATE ON extension_tokens TO ems_app, ems_worker;
GRANT SELECT, INSERT, UPDATE ON hr_policies, extension_tokens, password_resets TO ems_lookup;
REVOKE ALL ON password_resets FROM ems_app, ems_worker;

-- ------------------------------------------------------------------ bootstrap functions
CREATE FUNCTION ems.create_password_reset(p_email text, p_token_hash bytea)
RETURNS boolean LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = ems, pg_temp AS
$$
DECLARE uid uuid;
BEGIN
  SELECT id INTO uid FROM ems.users WHERE email = lower(p_email);
  IF uid IS NULL THEN RETURN false; END IF;                       -- caller still answers 202 (no account enumeration)
  UPDATE ems.password_resets SET used_at = now() WHERE user_id = uid AND used_at IS NULL;  -- newest token replaces older ones
  INSERT INTO ems.password_resets (token_hash, user_id, expires_at) VALUES (p_token_hash, uid, now() + interval '30 minutes');
  RETURN true;
END $$;

CREATE FUNCTION ems.consume_password_reset(p_token_hash bytea, p_new_hash text)
RETURNS integer LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = ems, pg_temp AS
$$
DECLARE r record; n integer;
BEGIN
  SELECT * INTO r FROM ems.password_resets WHERE token_hash = p_token_hash FOR UPDATE;
  IF r IS NULL OR r.used_at IS NOT NULL OR r.expires_at < now() THEN RAISE EXCEPTION 'RESET_TOKEN_EXPIRED' USING ERRCODE = 'P0001'; END IF;
  UPDATE ems.password_resets SET used_at = now() WHERE token_hash = p_token_hash;
  UPDATE ems.users SET password_hash = p_new_hash WHERE id = r.user_id;
  UPDATE ems.auth_sessions SET revoked_at = now() WHERE user_id = r.user_id AND revoked_at IS NULL;
  GET DIAGNOSTICS n = ROW_COUNT;
  RETURN n;                                                        -- sessions revoked
END $$;

CREATE FUNCTION ems.resolve_extension_token(p_token_hash bytea)
RETURNS TABLE (org_id uuid, user_id uuid, session_id uuid) LANGUAGE sql STABLE SECURITY DEFINER SET search_path = ems, pg_temp AS
$$ SELECT org_id, user_id, session_id FROM ems.extension_tokens
   WHERE token_hash = p_token_hash AND revoked_at IS NULL AND expires_at > now() $$;

DO $$
DECLARE f text;
BEGIN
  FOREACH f IN ARRAY ARRAY['create_password_reset(text,bytea)','consume_password_reset(bytea,text)','resolve_extension_token(bytea)'] LOOP
    EXECUTE format('ALTER FUNCTION ems.%s OWNER TO ems_lookup', f);
    EXECUTE format('REVOKE ALL ON FUNCTION ems.%s FROM PUBLIC', f);
    EXECUTE format('GRANT EXECUTE ON FUNCTION ems.%s TO ems_app', f);
  END LOOP;
END $$;
RESET ROLE;
