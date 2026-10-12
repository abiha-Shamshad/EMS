"""EMS worker: outbox loop + scheduler (DEC-004, TASK-006). Run: python -m worker.main

Connects as ems_worker (WORKER_DATABASE_URL). The outbox scan sees only unpublished rows across companies (DB-14);
each event is handled inside its own company's RLS context and marked published in the same transaction.
Retry state is stored on the event (db/004): a failing event gets `attempts` + 1 and `next_attempt_at` with exponential
back-off, and is marked `dead` after 10 attempts. The scan only takes events that are due and not dead, so failing
events can never block the rest of the outbox, and the counts survive a restart. Dead events stay unpublished for
operators (see MAINTENANCE_NOTES).
"""
import logging
import os
import signal
import threading

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import Engine, text

import worker.automation  # noqa: F401 - registers rule, starter-rule and nightly handlers
import worker.handlers  # noqa: F401 - registers handlers
import worker.jobs  # noqa: F401 - registers scheduled-event handlers
from app.platform.db import make_engine, transaction
from app.platform.web import configure_logging
from app.room.livekit import MediaConfig
from worker.registry import HANDLERS, Event

log = logging.getLogger("ems.worker")
POLL_SECONDS, BATCH, MAX_ATTEMPTS, MAX_BACKOFF = 1.0, 100, 10, 300


class OutboxLoop:
    def __init__(self, engine: Engine):
        self.engine = engine
        self.stop = threading.Event()

    def process(self, event_id, org_id) -> None:
        with transaction(self.engine) as db:
            db.set_context(org_id, None)
            row = db.one("SELECT id, org_id, routing_key, payload, created_at FROM ems.outbox_events "
                         "WHERE id = :id AND published_at IS NULL FOR UPDATE SKIP LOCKED", id=event_id)
            if row is None:
                return                                      # already published or being handled elsewhere
            event = Event(**row)
            for handler in HANDLERS.get(event.routing_key, []):
                handler(db, event)
            db.execute("UPDATE ems.outbox_events SET published_at = now() WHERE id = :id", id=event_id)

    def record_failure(self, event_id, org_id) -> tuple[int, bool]:
        """Count the failed attempt in its own transaction (the handler's transaction was rolled back)."""
        with transaction(self.engine) as db:
            db.set_context(org_id, None)
            row = db.one("UPDATE ems.outbox_events SET attempts = attempts + 1, dead = attempts + 1 >= :max, "
                         "next_attempt_at = now() + make_interval(secs => least(power(2, attempts + 1), :cap)) "
                         "WHERE id = :id AND published_at IS NULL RETURNING attempts, dead",
                         id=event_id, max=MAX_ATTEMPTS, cap=MAX_BACKOFF)
        return (row["attempts"], row["dead"]) if row else (0, False)

    def run_once(self) -> int:
        with self.engine.connect() as conn:
            rows = conn.execute(text("SELECT id, org_id FROM ems.outbox_events WHERE published_at IS NULL AND NOT dead "
                                     "AND (next_attempt_at IS NULL OR next_attempt_at <= now()) ORDER BY created_at LIMIT :n"),
                                {"n": BATCH}).all()
        done = 0
        for event_id, org_id in rows:
            try:
                self.process(event_id, org_id)
                done += 1
            except Exception:
                n, dead = self.record_failure(event_id, org_id)
                log.log(logging.ERROR if dead else logging.WARNING,
                        "event marked dead after the last attempt" if dead else "event handler failed; will retry", exc_info=True,
                        extra={"fields": {"event_id": str(event_id), "org_id": str(org_id), "attempt": n}})
        return done

    def run_forever(self) -> None:
        while not self.stop.is_set():
            try:
                self.run_once()
            except Exception:
                log.exception("outbox scan failed")
            self.stop.wait(POLL_SECONDS)


def main() -> None:
    url = os.environ.get("WORKER_DATABASE_URL", "").strip()
    if not url:
        raise SystemExit("WORKER_DATABASE_URL is required (connect as ems_worker).")
    configure_logging(os.environ.get("LOG_LEVEL", "info").upper())
    engine, media = make_engine(url), MediaConfig.from_env()      # LiveKit: to disconnect viewers in the sweep
    loop = OutboxLoop(engine)
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(worker.jobs.tick, "cron", second=0, args=[engine, media], id="minute_tick", max_instances=1, coalesce=True)
    scheduler.add_job(worker.automation.crawl_next_hunt, "interval", seconds=15, args=[engine], id="lead_hunter", max_instances=1,
                      coalesce=True)                                  # one hunt at a time; a crawl runs for minutes
    scheduler.start()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: loop.stop.set())
    log.info("worker started", extra={"fields": {"handlers": sorted(HANDLERS)}})
    try:
        loop.run_forever()
    finally:
        scheduler.shutdown(wait=False)
        engine.dispose()


if __name__ == "__main__":
    main()
