"""Integration test fixtures: a disposable PostgreSQL database built from db/001..005, the API as ems_app, the worker as
ems_worker. Never point TEST_ADMIN_DATABASE_URL at a database with real data.

    TEST_ADMIN_DATABASE_URL=postgresql://postgres@127.0.0.1:55432/postgres pytest

The runtime roles connect without passwords, as in db/verify_ems_db.py (trust auth in a sandbox or CI service).
"""
import json
import os
import re
import secrets
import uuid
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.platform.db import make_engine

ROOT = Path(__file__).resolve().parents[2]
ADMIN_URL = os.environ.get("TEST_ADMIN_DATABASE_URL")
CONTRACTS = {e["id"]: e for e in json.loads((ROOT / "contracts" / "api-examples.json").read_text(encoding="utf-8"))}
PASSWORD = "correct-horse-battery-staple-42"

if not ADMIN_URL:
    pytest.skip("TEST_ADMIN_DATABASE_URL is not set; integration tests need a disposable PostgreSQL.", allow_module_level=True)


def _with(url: str, *, user: str | None = None, db: str | None = None, driver: str | None = None) -> str:
    u = urlparse(url)
    netloc = f"{user}@{u.hostname}:{u.port or 5432}" if user else u.netloc
    scheme = driver or u.scheme
    return urlunparse((scheme, netloc, f"/{db}" if db else u.path, "", "", ""))


@pytest.fixture(scope="session")
def database():
    name = f"ems_test_{uuid.uuid4().hex[:8]}"
    with psycopg.connect(ADMIN_URL, autocommit=True) as conn:
        conn.execute(f'CREATE DATABASE "{name}"')
    with psycopg.connect(_with(ADMIN_URL, db=name), autocommit=True) as conn:
        for f in ("001_ems_schema.sql", "002_ems_settings_tokens.sql", "003_ems_platform_gaps.sql", "004_ems_pilot_fixes.sql",
                  "005_ems_automation.sql"):
            conn.execute((ROOT / "db" / f).read_text(encoding="utf-8"))
    yield {"app": _with(ADMIN_URL, user="ems_app", db=name, driver="postgresql+psycopg"),
           "worker": _with(ADMIN_URL, user="ems_worker", db=name, driver="postgresql+psycopg"),
           "admin": _with(ADMIN_URL, db=name)}
    with psycopg.connect(ADMIN_URL, autocommit=True) as conn:
        conn.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')


def make_settings(database, **overrides) -> Settings:
    values = dict(database_url=database["app"], app_base_url="http://localhost:3000", session_cookie_secure=False,
                  csrf_secret=bytes.fromhex("ab" * 32), google_client_id="", google_client_secret="", livekit_url="",
                  livekit_api_key="", livekit_api_secret="", extension_id="", email_provider="none", ai_rephraser="disabled",
                  log_level="WARNING", forwarded_allow_ips="127.0.0.1")
    values.update(overrides)
    return Settings(**values)


@pytest.fixture(scope="session")
def app(database):
    return create_app(make_settings(database))


@pytest.fixture(scope="session")
def worker_engine(database):
    engine = make_engine(database["worker"])
    yield engine
    engine.dispose()


@pytest.fixture
def drain(worker_engine):
    """Run the outbox loop until no event is left (what the worker does every second)."""
    from worker.main import OutboxLoop

    def run() -> int:
        loop, total = OutboxLoop(worker_engine), 0
        while (n := loop.run_once()):
            total += n
        return total
    return run


@pytest.fixture
def admin_sql(database):
    def run(sql: str, *params):
        with psycopg.connect(database["admin"], autocommit=True) as conn:
            cur = conn.execute(sql, params or None)
            return cur.fetchall() if cur.description else None
    return run


class Api:
    """A browser: keeps cookies, echoes the CSRF cookie, adds Idempotency-Key when asked."""

    def __init__(self, app):
        # A distinct client address per browser, so per-IP rate limits behave as they would for real users.
        ip = f"10.{secrets.randbelow(250) + 1}.{secrets.randbelow(250) + 1}.{secrets.randbelow(250) + 1}"
        self.client = TestClient(app, client=(ip, 50000))
        self.user_id: str | None = None
        self.ext_token: str | None = None

    def call(self, method: str, path: str, json=None, *, idem: str | bool = False, headers=None, ext: bool = False, params=None):
        h = dict(headers or {})
        if ext:
            h["Authorization"] = f"Bearer {self.ext_token}"
        elif self.client.cookies.get("ems_csrf"):
            h.setdefault("X-CSRF-Token", self.client.cookies.get("ems_csrf"))
        if idem:
            h["Idempotency-Key"] = idem if isinstance(idem, str) else uuid.uuid4().hex
        return self.client.request(method, path, json=json, headers=h, params=params)

    def get(self, path, **kw):
        return self.call("GET", path, **kw)

    def post(self, path, json=None, **kw):
        return self.call("POST", path, json if json is not None else {}, **kw)

    def patch(self, path, json, **kw):
        return self.call("PATCH", path, json, **kw)

    def put(self, path, json, **kw):
        return self.call("PUT", path, json, **kw)


def unique() -> str:
    return uuid.uuid4().hex[:8]


@pytest.fixture
def company(app):
    """A company with one member per role: {"ceo": Api, "cto": Api, ..., "org_id": str}. Bilal-style employee reports to the manager."""
    def build(roles=("cto", "cfo", "coo", "hr", "manager", "employee"), name="Acme Tech") -> dict:
        tag = unique()
        ceo = Api(app)
        r = ceo.post("/api/v1/auth/signup", {"company_name": name, "company_slug": f"acme-{tag}", "country": "PK",
                                             "time_zone": "Asia/Karachi", "name": "Imran Qureshi", "email": f"imran.{tag}@acme.example",
                                             "password": PASSWORD}, idem=True)
        assert r.status_code == 201, r.text
        ceo.user_id = r.json()["data"]["user"]["id"]
        out = {"ceo": ceo, "org_id": r.json()["data"]["org"]["id"], "tag": tag, "emails": {"ceo": f"imran.{tag}@acme.example"}}
        names = {"cto": "Sara Malik", "cfo": "Omar Siddiqui", "coo": "Zain Coo", "hr": "Hina Shah", "manager": "Usman Tariq",
                 "employee": "Bilal Ahmed"}
        invites = [{"email": f"{role}.{tag}@acme.example", "role": role} for role in roles]
        results = []
        if invites:
            r = ceo.post("/api/v1/invitations", {"invites": invites}, idem=True)
            assert r.status_code == 201, r.text
            results = r.json()["data"]["results"]
        for row, role in zip(results, roles, strict=True):
            member = Api(app)
            token = row["invite_link"].split("token=")[1]
            a = member.post("/api/v1/invitations/accept", {"token": token, "name": names[role], "password": PASSWORD})
            assert a.status_code == 200, a.text
            member.user_id = member.get("/api/v1/me").json()["data"]["user"]["id"]
            out[role] = member
            out["emails"][role] = row["email"]
        if "manager" in roles and "employee" in roles:
            set_member(out, out["employee"].user_id, manager_id=out["manager"].user_id, department="Engineering")
            set_member(out, out["manager"].user_id, department="Engineering")
        return out
    return build


def set_member(co: dict, user_id: str, **fields) -> dict:
    ceo = co["ceo"]
    members = ceo.get("/api/v1/members", params={"limit": 100}).json()["data"]["items"]
    version = next(m["version"] for m in members if m["user_id"] == user_id)
    r = ceo.patch(f"/api/v1/members/{user_id}", {"expected_version": version, **fields})
    assert r.status_code == 200, r.text
    return r.json()["data"]


def assert_contract(api_id: str, response, *, expect_status: int | None = None) -> dict:
    """TEST-001 shape check: listed status code, envelope, and every key of the documented example present."""
    spec = CONTRACTS[api_id]
    # Request-pipeline errors (Section 7.1 / 19.3) apply to every authenticated route even where a contract table omits them.
    allowed = set(spec["statuses"]) | ({401, 403, 423, 429} if spec["auth"] != "public" else {429})
    assert response.status_code in allowed, f"{api_id}: {response.status_code} not in {sorted(allowed)}: {response.text}"
    if expect_status is not None:
        assert response.status_code == expect_status, response.text
    body = response.json()
    if api_id == "API-001":
        return body
    example = spec["success"]["body"] if response.status_code == spec["success"]["status"] else None
    if body.get("success") is False:
        assert set(body) == {"success", "error", "meta"} and set(body["error"]) == {"code", "message", "retryable", "details"}
        assert set(body["meta"]) == {"api_version", "request_id"}
        return body
    assert body["success"] is True and set(body["meta"]) == {"api_version", "request_id", "timestamp"}
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", body["meta"]["timestamp"])
    if example is not None:
        _keys_present(example["data"], body["data"], api_id)
    return body["data"]


def _keys_present(example, actual, where: str) -> None:
    if isinstance(example, dict):
        assert isinstance(actual, dict), f"{where}: expected object, got {actual!r}"
        for k, v in example.items():
            assert k in actual, f"{where}: missing key '{k}'"
            if v is not None and actual[k] is not None:
                _keys_present(v, actual[k], f"{where}.{k}")
    elif isinstance(example, list) and example and isinstance(actual, list) and actual:
        _keys_present(example[0], actual[0], f"{where}[0]")
