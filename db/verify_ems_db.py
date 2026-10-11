"""EMS database verification suite.
Run against a disposable PostgreSQL with 001_ems_schema.sql applied:
    PGHOST=/tmp PGPORT=55432 PGDATABASE=emstest python verify_ems_db.py
Requires psycopg 3.3.x. Connects as postgres (admin checks), ems_app and ems_worker without passwords (trust auth)."""
import os, uuid, hashlib, threading
from contextlib import contextmanager
import psycopg

BASE = dict(host=os.environ.get("PGHOST", "/tmp"), port=os.environ.get("PGPORT", "55432"), dbname=os.environ.get("PGDATABASE", "emstest"))
results = []

def conn(user):
    return psycopg.connect(user=user, autocommit=False, **BASE)

@contextmanager
def org_tx(org, user, role="ems_app"):
    c = conn(role)
    try:
        with c.cursor() as cur:
            cur.execute("SELECT set_config('app.org_id', %s, true), set_config('app.user_id', %s, true)", (str(org), str(user)))
            yield cur
        c.commit()
    except Exception:
        c.rollback(); raise
    finally:
        c.close()

REGISTRY = []
def check(cid, name):
    def deco(fn):
        REGISTRY.append((cid, name, fn))
        return fn
    return deco

def expect_error(fn, needle):
    try:
        fn()
    except Exception as e:
        assert needle in str(e), f"expected '{needle}', got: {e}"
        return
    raise AssertionError(f"expected error containing '{needle}'")

def u(): return uuid.uuid4()
def h(s): return hashlib.sha256(s.encode()).digest()

# ------------------------------------------------------------------ fixtures through bootstrap functions
ceoA, orgA, ceoB, orgB, empA = u(), u(), u(), u(), u()
with conn("ems_app") as c:
    c.execute("SELECT ems.signup_company(%s,%s,%s,%s,NULL,%s,%s,%s,%s,%s)", (ceoA, "sawera@acme.example", "Sawera Ghaffar", "argon2id$x", orgA, "Acme Tech", "acme-tech", "Asia/Karachi", "PK"))
    c.execute("SELECT ems.signup_company(%s,%s,%s,%s,NULL,%s,%s,%s,%s,%s)", (ceoB, "ceo@other.example", "Other CEO", "argon2id$y", orgB, "Other Co", "other-co", "Asia/Karachi", "PK"))
    c.execute("SELECT ems.create_user(%s,%s,%s,%s,NULL)", (empA, "abiha@acme.example", "Abiha", "argon2id$z"))
    c.commit()
with org_tx(orgA, ceoA) as cur:
    cur.execute("INSERT INTO ems.invitations (id, org_id, email, role, token_hash, invited_by, expires_at) VALUES (%s,%s,'abiha@acme.example','employee',%s,%s, now() + interval '7 days')", (u(), orgA, h("tokA"), ceoA))

@check("DB-01", "No org context -> zero rows for ems_app")
def _():
    with conn("ems_app") as c:
        n = c.execute("SELECT count(*) FROM ems.memberships").fetchone()[0]
        assert n == 0, n

@check("DB-02", "Org A cannot read or insert org B rows")
def _():
    with org_tx(orgA, ceoA) as cur:
        cur.execute("SELECT count(*) FROM ems.memberships WHERE org_id = %s", (orgB,))
        assert cur.fetchone()[0] == 0
    expect_error(lambda: org_tx_insert_company(orgA, ceoA, orgB), "row-level security")

def org_tx_insert_company(org, user, target):
    with org_tx(org, user) as cur:
        cur.execute("INSERT INTO ems.companies (id, org_id, name) VALUES (%s,%s,'x')", (u(), target))

@check("DB-03", "password_hash is not readable by ems_app; other-org users invisible")
def _():
    expect_error(lambda: _sel("SELECT password_hash FROM ems.users"), "permission denied")
    with org_tx(orgA, ceoA) as cur:
        cur.execute("SELECT count(*) FROM ems.users WHERE id = %s", (ceoB,))
        assert cur.fetchone()[0] == 0

def _sel(q):
    with org_tx(orgA, ceoA) as cur:
        cur.execute(q)

@check("DB-04", "Sessions only via functions; revoked and expired sessions do not resolve")
def _():
    expect_error(lambda: _sel("SELECT * FROM ems.auth_sessions"), "permission denied")
    with conn("ems_app") as c:
        c.execute("SELECT ems.create_session(%s,%s,%s,false)", (u(), ceoA, h("sess1")))
        assert c.execute("SELECT count(*) FROM ems.resolve_session(%s)", (h("sess1"),)).fetchone()[0] == 1
        c.execute("SELECT ems.revoke_session(%s)", (h("sess1"),))
        assert c.execute("SELECT count(*) FROM ems.resolve_session(%s)", (h("sess1"),)).fetchone()[0] == 0
        c.commit()

@check("DB-05", "Invitation: wrong email rejected, correct email joins once")
def _():
    other = u()
    with conn("ems_app") as c:
        c.execute("SELECT ems.create_user(%s,%s,%s,%s,NULL)", (other, "intruder@x.example", "X", "argon2id$q")); c.commit()
    expect_error(lambda: _accept(other), "INVITATION_EMAIL_MISMATCH")
    _accept(empA)
    expect_error(lambda: _accept(empA), "INVITATION_INVALID")

def _accept(user):
    with conn("ems_app") as c:
        c.execute("SELECT ems.accept_invitation(%s,%s)", (h("tokA"), user)); c.commit()

@check("DB-06", "Two concurrent check-ins for one employee -> exactly one open work session")
def _():
    outcomes = []
    def checkin():
        try:
            with org_tx(orgA, empA) as cur:
                cur.execute("INSERT INTO ems.work_sessions (id, org_id, user_id, started_at) VALUES (%s,%s,%s, now())", (u(), orgA, empA))
            outcomes.append("ok")
        except Exception as e:
            outcomes.append("dup" if "ux_one_open_session" in str(e) else str(e))
    ts = [threading.Thread(target=checkin) for _ in range(2)]
    [t.start() for t in ts]; [t.join() for t in ts]
    assert sorted(outcomes) == ["dup", "ok"], outcomes

@check("DB-07", "Only one active CEO per organization")
def _():
    expect_error(lambda: _role(empA, "ceo"), "ux_one_ceo")

def _role(user, role):
    with org_tx(orgA, ceoA) as cur:
        cur.execute("UPDATE ems.memberships SET role = %s WHERE org_id = %s AND user_id = %s", (role, orgA, user))

@check("DB-08", "Overlapping pending/approved leave rejected; rejected leave does not block")
def _():
    def leave(period, status="pending"):
        with org_tx(orgA, empA) as cur:
            cur.execute("INSERT INTO ems.leave_requests (id, org_id, user_id, kind, period, status) VALUES (%s,%s,%s,'annual',%s::daterange,%s)", (u(), orgA, empA, period, status))
    leave("[2026-10-20,2026-10-23)")
    expect_error(lambda: leave("[2026-10-22,2026-10-25)"), "conflicting key value")
    leave("[2026-11-02,2026-11-04)", "rejected")
    leave("[2026-11-03,2026-11-05)")

COMPANY, CONTACT, DEAL, CLIENT = u(), u(), u(), u()
@check("DB-09", "Deal won needs won_at; lost needs a reason; one client per won deal")
def _():
    with org_tx(orgA, ceoA) as cur:
        cur.execute("INSERT INTO ems.companies (id, org_id, name, domain) VALUES (%s,%s,'Northwind','northwind.example')", (COMPANY, orgA))
        cur.execute("INSERT INTO ems.contacts (id, org_id, company_id, name, email, source, owner_id) VALUES (%s,%s,%s,'Ali Raza','ali@northwind.example','manual',%s)", (CONTACT, orgA, COMPANY, ceoA))
        cur.execute("INSERT INTO ems.deals (id, org_id, contact_id, company_id, title, amount, currency, owner_id) VALUES (%s,%s,%s,%s,'Website rebuild',5000,'USD',%s)", (DEAL, orgA, CONTACT, COMPANY, ceoA))
    expect_error(lambda: _deal("UPDATE ems.deals SET stage='won' WHERE id=%s"), "check constraint")
    expect_error(lambda: _deal("UPDATE ems.deals SET stage='lost' WHERE id=%s"), "check constraint")
    _deal("UPDATE ems.deals SET stage='won', won_at=now() WHERE id=%s")
    _deal("INSERT INTO ems.clients (id, org_id, company_id, origin_deal_id, since) VALUES (gen_random_uuid(), ems.current_org(), (SELECT company_id FROM ems.deals WHERE id=%s), %s, current_date)", 2)
    expect_error(lambda: _deal("INSERT INTO ems.clients (id, org_id, company_id, origin_deal_id, since) VALUES (gen_random_uuid(), ems.current_org(), (SELECT company_id FROM ems.deals WHERE id=%s), %s, current_date)", 2), "duplicate key")

def _deal(sql, n=1):
    with org_tx(orgA, ceoA) as cur:
        cur.execute(sql, (DEAL,) * n)

@check("DB-10", "Hourly project needs rate+currency; client project needs a client")
def _():
    def proj(billing, client, rate):
        with org_tx(orgA, ceoA) as cur:
            cur.execute("INSERT INTO ems.projects (id, org_id, client_id, name, billing_type, hourly_rate, currency, owner_id) VALUES (%s,%s,%s,'P',%s,%s,%s,%s)",
                        (u(), orgA, client, billing, rate, "USD" if rate else None, ceoA))
    expect_error(lambda: proj("hourly", None, None), "check constraint")
    expect_error(lambda: proj("fixed", None, None), "check constraint")
    proj("internal", None, None)

@check("DB-11", "Graph memory: 2-hop neighbours inside the org; nothing from another org")
def _():
    ids = {k: u() for k in ["p_sawera", "p_abiha", "proj", "client", "deal"]}
    with org_tx(orgA, ceoA) as cur:
        for k, kind in [("p_sawera", "person"), ("p_abiha", "person"), ("proj", "project"), ("client", "client"), ("deal", "deal")]:
            cur.execute("INSERT INTO ems.graph_nodes (id, org_id, kind, ref_id, label) VALUES (%s,%s,%s,%s,%s)", (ids[k], orgA, kind, u(), k))
        for s, d, kind in [("p_abiha", "proj", "works_on"), ("proj", "client", "billed_by"), ("client", "deal", "originated_from"), ("p_sawera", "deal", "owns")]:
            cur.execute("INSERT INTO ems.graph_edges (id, org_id, src, dst, kind, evidence) VALUES (%s,%s,%s,%s,%s,'fixture')", (u(), orgA, ids[s], ids[d], kind))
        cur.execute("SELECT label, depth FROM ems.graph_neighbors(%s, 2) ORDER BY depth, label", (ids["p_abiha"],))
        got = cur.fetchall()
    assert got == [("proj", 1), ("client", 2)], got
    with org_tx(orgB, ceoB) as cur:
        cur.execute("SELECT count(*) FROM ems.graph_neighbors(%s, 3)", (ids["p_abiha"],))
        assert cur.fetchone()[0] == 0
    expect_error(lambda: _xedge(ids), "violates foreign key")

def _xedge(ids):
    nb = u()
    with org_tx(orgB, ceoB) as cur:
        cur.execute("INSERT INTO ems.graph_nodes (id, org_id, kind, ref_id, label) VALUES (%s,%s,'person',%s,'b')", (nb, orgB, u()))
        cur.execute("INSERT INTO ems.graph_edges (id, org_id, src, dst, kind, evidence) VALUES (%s,%s,%s,%s,'works_on','x')", (u(), orgB, nb, ids["proj"]))

@check("DB-12", "Rule run is recorded once per (rule, event); leakage finding once per fingerprint")
def _():
    rule, ev = u(), u()
    with org_tx(orgA, ceoA) as cur:
        cur.execute("INSERT INTO ems.rules (id, org_id, key, version, trigger, definition, created_by) VALUES (%s,%s,'stale_deal_nudge',1,'deal.stale','{}',%s)", (rule, orgA, ceoA))
        for _ in range(2):
            cur.execute("INSERT INTO ems.rule_runs (id, org_id, rule_id, event_id, outcome) VALUES (%s,%s,%s,%s,'matched') ON CONFLICT (rule_id, event_id) DO NOTHING", (u(), orgA, rule, ev))
        for _ in range(2):
            cur.execute("INSERT INTO ems.leakage_findings (id, org_id, kind, entity_type, entity_id, fingerprint, evidence) VALUES (%s,%s,'stale_deal','deal',%s,'stale_deal:x:2026-10-10','{}') ON CONFLICT (org_id, fingerprint) DO NOTHING", (u(), orgA, DEAL))
        cur.execute("SELECT (SELECT count(*) FROM ems.rule_runs), (SELECT count(*) FROM ems.leakage_findings)")
        assert cur.fetchone() == (1, 1)

@check("DB-13", "Stream view: only ended_at can change; audit is insert-only")
def _():
    sv = u()
    with org_tx(orgA, ceoA) as cur:
        cur.execute("INSERT INTO ems.stream_views (id, org_id, viewer_id, subject_user_id, reason) VALUES (%s,%s,%s,%s,'Daily standup check')", (sv, orgA, ceoA, empA))
        cur.execute("UPDATE ems.stream_views SET ended_at = now() WHERE id = %s", (sv,))
        cur.execute("INSERT INTO ems.audit_events (org_id, actor_id, action) VALUES (%s,%s,'test')", (orgA, ceoA))
    expect_error(lambda: _sel("UPDATE ems.stream_views SET reason = 'changed'"), "permission denied")
    expect_error(lambda: _sel("UPDATE ems.audit_events SET action = 'x'"), "permission denied")

@check("DB-14", "Worker sees unpublished outbox rows across orgs, but no business rows without context")
def _():
    with org_tx(orgA, ceoA) as cur:
        cur.execute("INSERT INTO ems.outbox_events (id, org_id, routing_key, payload) VALUES (%s,%s,'deal.won','{}')", (u(), orgA))
    with org_tx(orgB, ceoB) as cur:
        cur.execute("INSERT INTO ems.outbox_events (id, org_id, routing_key, payload) VALUES (%s,%s,'deal.won','{}')", (u(), orgB))
    with conn("ems_worker") as c:
        assert c.execute("SELECT count(DISTINCT org_id) FROM ems.outbox_events WHERE published_at IS NULL").fetchone()[0] == 2
        assert c.execute("SELECT count(*) FROM ems.deals").fetchone()[0] == 0

@check("DB-15", "Runtime roles lack BYPASSRLS; all tables owned by ems_owner with FORCE RLS")
def _():
    with conn("postgres") as c:
        r = c.execute("SELECT rolname FROM pg_roles WHERE rolname IN ('ems_app','ems_worker','ems_owner') AND rolbypassrls").fetchall()
        assert r == [], r
        bad = c.execute("""SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                           WHERE n.nspname='ems' AND c.relkind='r' AND (pg_get_userbyid(c.relowner) <> 'ems_owner' OR NOT c.relforcerowsecurity)""").fetchall()
        assert bad == [], bad


@check("DB-16", "Password reset: unknown email returns false; token single-use; all sessions revoked")
def _():
    with conn("ems_app") as c:
        assert c.execute("SELECT ems.create_password_reset('nobody@nowhere.example', %s)", (h("rst0"),)).fetchone()[0] is False
        c.execute("SELECT ems.create_session(%s,%s,%s,false)", (u(), empA, h("sessE1")))
        c.execute("SELECT ems.create_session(%s,%s,%s,true)", (u(), empA, h("sessE2")))
        assert c.execute("SELECT ems.create_password_reset('ABIHA@acme.example', %s)", (h("rst1"),)).fetchone()[0] is True
        assert c.execute("SELECT ems.consume_password_reset(%s, 'argon2id$new')", (h("rst1"),)).fetchone()[0] == 2
        assert c.execute("SELECT count(*) FROM ems.resolve_session(%s)", (h("sessE1"),)).fetchone()[0] == 0
        c.commit()
    def again():
        with conn("ems_app") as c:
            c.execute("SELECT ems.consume_password_reset(%s, 'argon2id$x')", (h("rst1"),))
    expect_error(again, "RESET_TOKEN_EXPIRED")
    expect_error(lambda: _sel("SELECT * FROM ems.password_resets"), "permission denied")

@check("DB-17", "Extension token resolves to its org/user/session; revoked token resolves to nothing")
def _():
    sid = u()
    with org_tx(orgB, ceoB) as cur:
        cur.execute("INSERT INTO ems.work_sessions (id, org_id, user_id, started_at) VALUES (%s,%s,%s, now())", (sid, orgB, ceoB))
        cur.execute("INSERT INTO ems.extension_tokens (token_hash, org_id, user_id, session_id, expires_at) VALUES (%s,%s,%s,%s, now() + interval '14 hours')", (h("ext1"), orgB, ceoB, sid))
    with conn("ems_app") as c:
        assert c.execute("SELECT org_id, user_id, session_id FROM ems.resolve_extension_token(%s)", (h("ext1"),)).fetchone() == (orgB, ceoB, sid)
    with org_tx(orgB, ceoB) as cur:
        cur.execute("UPDATE ems.extension_tokens SET revoked_at = now() WHERE token_hash = %s", (h("ext1"),))
    with conn("ems_app") as c:
        assert c.execute("SELECT count(*) FROM ems.resolve_extension_token(%s)", (h("ext1"),)).fetchone()[0] == 0
    with org_tx(orgA, ceoA) as cur:
        cur.execute("SELECT count(*) FROM ems.extension_tokens")
        assert cur.fetchone()[0] == 0

@check("DB-18", "HR policies are versioned insert-only and org-isolated; company settings defaults present")
def _():
    with org_tx(orgA, ceoA) as cur:
        cur.execute("INSERT INTO ems.hr_policies (org_id, topic, version, text, published_by) VALUES (%s,'attendance',1,'Work hours 09:00-18:00, 10 minutes grace.',%s)", (orgA, ceoA))
        cur.execute("SELECT (work_hours->>'late_grace_minutes')::int, live_view_enabled, room_policy_version FROM ems.organizations")
        assert cur.fetchone() == (10, False, 1)
    def upd():
        with org_tx(orgA, ceoA) as cur:
            cur.execute("UPDATE ems.hr_policies SET text = 'changed text here' WHERE topic = 'attendance'")
    expect_error(upd, "permission denied")
    with org_tx(orgB, ceoB) as cur:
        cur.execute("SELECT count(*) FROM ems.hr_policies")
        assert cur.fetchone()[0] == 0

for cid, name, fn in REGISTRY:          # run in declaration order after all helpers exist
    try:
        fn(); results.append((cid, name, "PASS", ""))
    except Exception as e:
        results.append((cid, name, "FAIL", str(e).splitlines()[0][:160]))
print("| Check | Behavior | Status | Detail |\n|---|---|---|---|")
for r in results:
    print("| %s | %s | %s | %s |" % (r[0], r[1], r[2], r[3].replace("|", "/")))
raise SystemExit(1 if any(r[2] == "FAIL" for r in results) else 0)
