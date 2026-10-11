# EMS Release 1 - Implementation Pack v1.0

Status: **PARTIALLY READY**. TASK-001 to TASK-017 are ready to implement. Live viewing of real employees (OD-02), Chrome Web Store publication (OD-03), automatic email (INT-003 / OD-09) and any language-model feature (INT-006 / OD-06) are BLOCKED until their owner decisions close. No application code has been built yet; what is verified is listed below.

## Contents

| Path | What it is | Verified |
|---|---|---|
| `spec/EMS_R1_Implementation_Spec_v1.0.md` | Canonical specification (same content as the .docx) | CHK-01..12 |
| `spec/EMS_Idea_Briefing_v1.0.md` | Team idea briefing (same content as the .docx) | - |
| `spec/parts/01.md` .. `05.md` | Specification sources used by the checker (`03.md` is generated) | - |
| `db/001_ems_schema.sql` | Executable schema: tables, RLS, roles, bootstrap functions, graph query | Applied on PostgreSQL 16.13 |
| `db/002_ems_settings_tokens.sql` | Company settings, HR policies, password resets, extension tokens, contact search | Applied on PostgreSQL 16.13 |
| `db/verify_ems_db.py` | 18 database checks (isolation, concurrency, invariants, tokens) | 18/18 PASS on PostgreSQL 16.13 |
| `engine/` + `engine/tests/` | Rules, presence, leakage, robots.txt, scoring, HR Agent (standard library only) | 21/21 PASS (Python 3.11.15) |
| `contracts/api-examples.json` | Request, success and error examples for all 70 operations | Parsed and cross-checked |
| `tools/gen_api.py` | Generator for the endpoint registry, contracts and examples | - |
| `tools/check_spec.py` | Consistency checker for the spec, examples and schema | 12/12 PASS |
| `tools/check_livekit_tokens.py` | LiveKit grant and TTL checks for EMS tokens | 3/3 PASS (livekit-api 1.2.1) |

## Run the checks

```bash
# from this folder
python3 -m unittest engine.tests.test_engine
python3 tools/check_spec.py
pip install livekit-api==1.2.1 PyJWT==2.15.1 psycopg[binary]==3.3.6
python3 tools/check_livekit_tokens.py

# database checks need a disposable PostgreSQL (17 recommended) and an admin connection
psql "$ADMIN_DATABASE_URL" -v ON_ERROR_STOP=1 -f db/001_ems_schema.sql -f db/002_ems_settings_tokens.sql
PGHOST=<host> PGPORT=<port> PGDATABASE=<db> python3 db/verify_ems_db.py
```

`verify_ems_db.py` connects as `postgres`, `ems_app` and `ems_worker` without passwords (trust auth in a sandbox). Never run it against production data.

To regenerate contracts after editing `tools/gen_api.py`: `python3 tools/gen_api.py 21 spec/parts/03.md contracts/api-examples.json`, then rebuild the combined spec.

## Start building

Read the specification "Start here" box, then Appendix E, TASK-001. Give AI coding tools the handoff text in Appendix F with the files it names.
