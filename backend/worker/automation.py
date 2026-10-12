"""Worker side of the rule engine, leakage run and Lead Hunter (TASK-012, TASK-013, Section 17).

* Rule triggers: every event a rule can fire on runs app/rules/service.py inside the event's transaction.
* org.created seeds the starter rules; the nightly job seeds them for older companies too (missing keys only).
* platform.nightly (01:00 company time, deterministic event ID): leakage detectors, then deal.stale / invoice.overdue
  events for the rules, each with a deterministic ID so a repeated run emits nothing new.
* Hunts are crawled by `crawl_next_hunt`, a scheduler job outside the outbox: a crawl takes minutes and must not hold
  the outbox transaction. A hunt whose heartbeat is older than 10 minutes (worker restarted mid-crawl) is picked up again.
"""
import logging
import os
import uuid

from sqlalchemy import Engine, text

from app.hunter.crawler import Crawler, http_fetch
from app.leakage import service as leakage
from app.platform import events
from app.platform.db import Db, transaction
from app.platform.timeutil import Calendar
from app.rules import service as rules
from app.rules import starter
from worker.registry import Event, handles

log = logging.getLogger("ems.worker.automation")
NS = uuid.UUID("7d0f3c55-61e2-4f0e-8a77-3c1f2e9b4d10")              # namespace for nightly rule-trigger event IDs
STALLED_AFTER = "10 minutes"                                            # a running hunt with no heartbeat for this long is resumed


@handles(*rules.TRIGGER_FOR_EVENT)
def run_rules(db: Db, e: Event) -> None:
    rules.run_for_event(db, e.org_id, e.id, e.routing_key, e.payload)


@handles("org.created")
def seed_starter_rules(db: Db, e: Event) -> None:
    starter.seed(db, e.org_id)


@handles("platform.nightly")
def nightly(db: Db, e: Event) -> None:
    starter.seed(db, e.org_id)
    result = leakage.run(db, e.org_id)
    org = db.one("SELECT time_zone, work_hours FROM ems.organizations")
    emitted = 0
    for routing_key, key, payload in leakage.rule_events(db, Calendar(org["time_zone"], org["work_hours"])):
        events.emit(db, e.org_id, routing_key, payload, event_id=uuid.uuid5(NS, f"{e.org_id}:{routing_key}:{key}"))
        emitted += 1
    log.info("nightly run", extra={"fields": {"org_id": str(e.org_id), **result, "rule_events": emitted}})


# ------------------------------------------------------------------------------------------------ Lead Hunter
def _user_agent() -> str:
    base = os.environ.get("APP_BASE_URL", "").strip().rstrip("/")
    return f"EMS-LeadHunter/1.0 (+{base}/bot)" if base else "EMS-LeadHunter/1.0"


def claim_hunt(engine: Engine) -> tuple[uuid.UUID, dict] | None:
    """Mark the oldest queued (or stalled) hunt of any company as running and return it, in its own committed transaction."""
    with engine.connect() as conn:
        orgs = [r[0] for r in conn.execute(text("SELECT org_id FROM ems.worker_organizations()")).all()]
    for org_id in orgs:
        with transaction(engine) as db:
            db.set_context(org_id, None)
            hunt = db.one("SELECT id, seeds, icp, created_by FROM ems.hunts WHERE status = 'queued' OR (status = 'running' AND "
                          "coalesce(CAST(stats->>'heartbeat_at' AS timestamptz), created_at) < now() - CAST(:stall AS interval)) "
                          "ORDER BY created_at LIMIT 1 FOR UPDATE SKIP LOCKED", stall=STALLED_AFTER)
            if hunt is not None:
                db.execute("UPDATE ems.hunts SET status = 'running', stats = stats || jsonb_build_object('heartbeat_at', now()) WHERE id = :h",
                           h=hunt["id"])
                return org_id, hunt
    return None


def crawl_next_hunt(engine: Engine, fetch=None, sleep=None) -> bool:
    """Scheduler job: crawl one hunt to completion. Returns False when nothing was waiting."""
    claimed = claim_hunt(engine)
    if claimed is None:
        return False
    org_id, hunt = claimed
    kwargs = {"sleep": sleep} if sleep is not None else {}
    try:
        Crawler(lambda: transaction(engine), org_id, hunt, fetch or http_fetch(_user_agent()), **kwargs).run()
    except Exception:
        log.exception("hunt failed", extra={"fields": {"org_id": str(org_id), "hunt_id": str(hunt["id"])}})
        with transaction(engine) as db:
            db.set_context(org_id, None)
            db.execute("UPDATE ems.hunts SET status = 'failed' WHERE id = :h", h=hunt["id"])
    return True
