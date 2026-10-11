#!/usr/bin/env python3
"""Static consistency checks for the EMS Release 1 specification pack.
Run from the pack root:  python3 tools/check_spec.py
Reads spec/parts/*.md, contracts/api-examples.json and db/*.sql. Standard library only."""
import json, os, re, sys, uuid
from decimal import Decimal

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = lambda *a: os.path.join(ROOT, *a)
md = {f: open(P("spec", "parts", f)).read() for f in sorted(os.listdir(P("spec", "parts"))) if f.endswith(".md")}
allmd = "\n".join(md.values())
ex = json.load(open(P("contracts", "api-examples.json")))
sql = open(P("db", "001_ems_schema.sql")).read() + open(P("db", "002_ems_settings_tokens.sql")).read()
R = []
def rec(i, name, ok, detail=""):
    R.append((i, name, "PASS" if ok else "FAIL", "" if ok else detail))

def bodies(e):
    out = [e["success"]["body"]] + [x["body"] for x in e["extra"]] + [e["error"]["body"]]
    return out + ([e["request"]] if e["request"] else [])

# CHK-01 JSON code blocks parse
bad = []
for f, text in md.items():
    for b in re.findall(r"(?:^    .*\n?)+", text, re.M):
        body = "\n".join(l[4:] for l in b.splitlines())
        if body.lstrip().startswith("{"):
            try: json.loads(body)
            except Exception as err: bad.append((f, body[:50], str(err)))
rec("CHK-01", "Every JSON code block in the specification parses", not bad, str(bad[:3]))

# CHK-02 API references exist
n = len(ex)
refs = set(int(x) for x in re.findall(r"API-(\d{3})", allmd + json.dumps(ex)))
rec("CHK-02", "Every API-### reference points to a registered operation", all(1 <= r <= n for r in refs), str(sorted(r for r in refs if r > n)))

# CHK-03 counts agree
c03 = md["03.md"]
contracts = len(re.findall(r"^## API-\d{3} ", c03, re.M))
rows = len(re.findall(r"^\| API-\d{3} \|", c03, re.M))
title = int(re.search(r"Endpoint Registry - (\d+) HTTP", c03).group(1))
appA = md["04.md"].split("# Appendix A")[1].split("# Appendix B")[0]
total = int(re.search(r"\*\*TOTAL\*\* \| \*\*(\d+)\*\*", appA).group(1))
dsum = sum(int(x) for x in re.findall(r"^\| [^*|][^|]* \| (\d+) \|$", appA, re.M))
prose = set(int(x) for x in re.findall(r"\b(\d{2}) operations\b", allmd))
ok = len({n, contracts, rows, title, total, dsum}) == 1 and prose <= {n}
rec("CHK-03", "Registry rows, contract sections, title, Appendix A total and domain sum agree", ok,
    f"n={n} contracts={contracts} rows={rows} title={title} total={total} sum={dsum} prose={sorted(prose)}")

# CHK-04 past-event timestamps not later than the response timestamp
PAST = {"created_at", "started_at", "ended_at", "since", "consented_at", "decided_at", "published_at", "won_at", "ran_at",
        "detected_at", "resolved_at", "last_activity_at", "occurred_at", "as_of", "server_time"}
viol = []
def walk(o, out):
    if isinstance(o, dict):
        for k, v in o.items():
            if k in PAST and isinstance(v, str) and re.match(r"\d{4}-\d\d-\d\dT", v): out.append((k, v))
            walk(v, out)
    elif isinstance(o, list):
        for v in o: walk(v, out)
for e in ex:
    for b in [e["success"]["body"]] + [x["body"] for x in e["extra"]]:
        if isinstance(b, dict) and "timestamp" in b.get("meta", {}):
            found = []; walk(b.get("data"), found)
            viol += [(e["id"], k, v) for k, v in found if v > b["meta"]["timestamp"]]
rec("CHK-04", "No example reports a past event later than its response timestamp", not viol, str(viol[:5]))

# CHK-05 enum values in examples exist in the schema CHECK constraints
def allowed(col_regex):
    m = re.search(col_regex, sql)
    assert m, col_regex
    line = sql[m.start(): sql.index("\n", m.end())]
    v = re.search(r"IN \(([^)]*)\)", line)
    assert v, col_regex
    return {x.strip().strip("'") for x in v.group(1).split(",")}
ENUMS = {
    "role": allowed(r"\n  role         text NOT NULL"), "presence": allowed(r"\n  presence     text NOT NULL DEFAULT"),
    "lifecycle_stage": allowed(r"lifecycle_stage text"), "source": allowed(r"\n  source          text NOT NULL"),
    "stage": allowed(r"\n  stage          text"), "to_stage": allowed(r"\n  stage          text"),
    "billing_type": allowed(r"billing_type  text"), "to_status": allowed(r"\n  status           text NOT NULL DEFAULT 'todo'"),
    "invoice_status": allowed(r"\n  status      text NOT NULL DEFAULT 'sent'"), "kind_finding": allowed(r"\n  kind            text NOT NULL"),
    "setup_state": allowed(r"setup_state text"), "outcome": allowed(r"\n  outcome       text"),
    "method": allowed(r"\n  method      text"), "entity_type": allowed(r"\n  entity_type  text"),
    "topic": allowed(r"\n  topic         text"), "size_band": allowed(r"size_band   text"),
}
ENUMS["kind_break"] = allowed(r"\n  kind          text NOT NULL")
ENUMS["kind_leave"] = allowed(r"\n  kind        text NOT NULL CHECK \(kind IN \('annual'")
ENUMS["kind_activity"] = allowed(r"\n  kind         text NOT NULL CHECK \(kind IN \('note'")
ENUMS["kind_suppression"] = allowed(r"\n  kind        text NOT NULL CHECK \(kind IN \('email'")
ENUMS["reason_suppression"] = allowed(r"\n  reason      text NOT NULL")
ENUMS["status_prospect"] = allowed(r"\n  status         text NOT NULL DEFAULT 'new'")
ENUMS["status_hunt"] = allowed(r"\n  status      text NOT NULL DEFAULT 'queued'")
ENUMS["status_leave"] = allowed(r"\n  status      text NOT NULL DEFAULT 'pending' CHECK \(status IN \('pending','approved'")
ENUMS["status_break"] = allowed(r"\n  status        text NOT NULL")
ENUMS["status_project"] = allowed(r"\n  status        text NOT NULL DEFAULT 'planned'")
ENUMS["status_client"] = allowed(r"\n  status          text NOT NULL DEFAULT 'onboarding'")
ENUMS["status_finding"] = allowed(r"\n  status          text NOT NULL DEFAULT 'open'")
ENUMS["invite_role"] = allowed(r"\n  role        text NOT NULL")
CTX = {"/leakage": ("kind", "kind_finding", "status", "status_finding"), "/room/breaks": ("kind", "kind_break", "status", "status_break"),
       "/leave-requests": ("kind", "kind_leave", "status", "status_leave"), "/activities": ("kind", "kind_activity", None, None),
       "/suppressions": ("kind", "kind_suppression", "reason", "reason_suppression"), "/hunts": (None, None, "status", "status_hunt"),
       "/prospects": (None, None, "status", "status_prospect"), "/projects": (None, None, "status", "status_project"),
       "/tasks": (None, None, "status", "to_status"), "/dashboards": ("source", None, None, None),
       "/deals/{dealId}/win": (None, None, "status", None), "/invitations": ("role", "invite_role", None, None)}
probs = []
def walk5(o, path, ctx):
    if isinstance(o, dict):
        for k, v in o.items():
            key = k
            if ctx and k == ctx[0] and ctx[1] is None: walk5(v, path, ctx); continue
            if ctx and k == ctx[0] and ctx[1]: key = ctx[1]
            elif ctx and k == ctx[2] and ctx[3]: key = ctx[3]
            elif k == "invoice_status": key = "invoice_status"
            if key in ENUMS and key not in ("role",) or (key == "role" and "/invitations" not in path):
                if key in ENUMS:
                    for x in (v if isinstance(v, list) else [v]):
                        if isinstance(x, str) and x not in ENUMS[key]: probs.append((path, k, x))
            walk5(v, path, ctx)
    elif isinstance(o, list):
        for v in o: walk5(v, path, ctx)
for e in ex:
    hits = [p for p in CTX if p in e["path"]]
    ctx = CTX[max(hits, key=lambda p: e["path"].rfind(p))] if hits else None
    if e["path"].endswith("/win"):
        ctx = None
    for b in bodies(e):
        walk5(b.get("data", b) if isinstance(b, dict) else b, e["path"], ctx)
probs = [p for p in probs if not (p[1] == "kind" and p[0] in ("/api/v1/notifications",))]
rec("CHK-05", "Enum values in examples exist in the schema CHECK constraints", not probs, str(sorted(set(probs))[:8]))

# CHK-06 error codes are catalogued
cat = set(re.findall(r"^\| ([A-Z_]+) \| \d{3} \|", md["04.md"], re.M))
used = {b["error"]["code"] for e in ex for b in [e["error"]["body"]] if "error" in b}
for m in re.finditer(r"^\| \d{3} \| (.*) \|$", c03, re.M):
    used |= set(re.findall(r"\b([A-Z]{2,}(?:_[A-Z]+)+)\b", m.group(1)))
used |= set(re.findall(r"`([A-Z]{2,}(?:_[A-Z]+)+)`", md["01.md"] + md["02.md"]))
used -= {"DISPLAY_MEDIA", "WEB_RTC", "TRIGGER_FACTS", "FACT_NOT_ALLOWED", "AI_REPHRASER", "EMAIL_PROVIDER", "GOOGLE_CLIENT_ID", "LIVEKIT_URL"}
rec("CHK-06", "Every error code used is in the error catalogue (Section 33)", used <= cat, str(sorted(used - cat)))

# CHK-07 example status codes appear in each HTTP table
bad7 = [e["id"] for e in ex if e["success"]["status"] not in e["statuses"] or e["error"]["status"] not in e["statuses"]
        or any(x["status"] not in e["statuses"] for x in e["extra"])]
rec("CHK-07", "Each example status code is listed in its HTTP table", not bad7, str(bad7))

# CHK-08 IDs are valid UUIDs
blob = json.dumps(ex)
ids_blob = json.dumps([bodies(e) for e in ex])
ids = re.findall(r'"(?:[a-z_]*id|user_id)": "([^"]+)"', ids_blob)
badid = [i for i in ids if not re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-5[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}", i)
         and not i.startswith(("req_", "ems-"))]
rec("CHK-08", "Example IDs are UUIDv5 strings from the fixture namespace", not badid and len(ids) > 80, f"bad={badid[:5]} n={len(ids)}")

# CHK-09 envelopes
bad9 = []
for e in ex:
    if not e["path"].startswith("/api/v1") or "/auth/google/" in e["path"]:
        continue
    s, eb = e["success"]["body"], e["error"]["body"]
    if not (s.get("success") is True and set(s["meta"]) == {"api_version", "request_id", "timestamp"} and "data" in s): bad9.append((e["id"], "success"))
    if not (eb.get("success") is False and set(eb["error"]) == {"code", "message", "retryable", "details"}): bad9.append((e["id"], "error"))
rec("CHK-09", "Success and error envelopes follow Section 19.1", not bad9, str(bad9[:5]))

# CHK-10 TASK references resolve
tasks = set(re.findall(r"^### (TASK-\d{3})", md["05.md"], re.M))
trefs = set(re.findall(r"TASK-\d{3}", allmd + blob))
rec("CHK-10", "Every TASK reference points to a task card", tasks and trefs <= tasks, str(sorted(trefs - tasks)))

# CHK-11 decision, integration, evidence, requirement and audit IDs are defined
defs = set(re.findall(r"^\| ((?:OD|INT|DEC|EV|REQ|AUD|SRC)-\d{2,3}) \|", allmd, re.M))
irefs = set(re.findall(r"\b((?:OD|INT|DEC|EV|REQ|AUD|SRC)-\d{2,3})\b", allmd + blob))
rec("CHK-11", "Every OD, INT, DEC, EV, REQ, AUD and SRC reference is defined in a table", irefs <= defs, str(sorted(irefs - defs)))

# CHK-12 arithmetic in examples
E = {e["id"]: e for e in ex}
lk = E["API-065"]["success"]["body"]["data"]
s1 = sum(Decimal(i["amount_at_risk"]) for i in lk["items"]) == Decimal(lk["totals"]["amount_at_risk"]) and len(lk["items"]) == lk["totals"]["open"]
pl = E["API-049"]["success"]["body"]["data"]
prob = {"new": Decimal("0.10"), "qualified": Decimal("0.25"), "proposal": Decimal("0.50"), "negotiation": Decimal("0.70")}
s2 = sum(Decimal(s["amount"]) * prob[s["stage"]] for s in pl["stages"]) == Decimal(pl["weighted_open"])
co = E["API-020"]["success"]["body"]["data"]
from datetime import datetime
mins = (datetime.fromisoformat(co["ended_at"].replace("Z", "+00:00")) - datetime.fromisoformat(co["started_at"].replace("Z", "+00:00"))).seconds // 60
s3 = sum(co["totals_minutes"].values()) == mins
st = next(i for i in lk["items"] if i["kind"] == "stale_deal")
s4 = Decimal(st["evidence"]["deal_amount"]) * Decimal(st["evidence"]["weighting"]) == Decimal(st["amount_at_risk"])
rec("CHK-12", "Leakage total, weighted pipeline, check-out minutes and stale-deal weighting add up", s1 and s2 and s3 and s4, f"{s1} {s2} {s3}({mins}) {s4}")

print("| Check | Behavior | Status | Detail |\n|---|---|---|---|")
for r in R:
    print("| %s | %s | %s | %s |" % (r[0], r[1], r[2], r[3].replace("|", "/")))
sys.exit(1 if any(r[2] == "FAIL" for r in R) else 0)
