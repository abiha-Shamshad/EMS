"""EMS worker: outbox loop + scheduler (DEC-004, TASK-006). Run: python -m worker.main

Connects as ems_worker (WORKER_DATABASE_URL). The outbox scan sees only unpublished rows across companies (DB-14);
each event is handled inside its own company's RLS context and marked published in the same transaction.
A failing event is retried with exponential back-off; after 10 attempts it is logged as poison and skipped by this
process (it stays unpublished, so it is visible to operators and is retried after a restart).
"""
import logging
import os
import signal
import threading
import time

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import Engine, text

import worker.handlers  # noqa: F401 - registers handlers
import worker.jobs  # noqa: F401 - registers scheduled-event handlers
from app.platform.db import make_engine, transaction
from app.platform.web import configure_logging
from worker.registry import HANDLERS, Event

log = logging.getLogger("ems.worker")
POLL_SECONDS, BATCH, MAX_ATTEMPTS, MAX_BACKOFF = 1.0, 100, 10, 300


class OutboxLoop:
    def __init__(self, engine: Engine):
        self.engine = engine
        self.attempts: dict = {}
        self.retry_at: dict = {}
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

    def run_once(self) -> int:
        with self.engine.connect() as conn:
            rows = conn.execute(text("SELECT id, org_id FROM ems.outbox_events WHERE published_at IS NULL ORDER BY created_at LIMIT :n"),
                                {"n": BATCH}).all()
        done, now = 0, time.monotonic()
        for event_id, org_id in rows:
            if self.attempts.get(event_id, 0) >= MAX_ATTEMPTS or self.retry_at.get(event_id, 0) > now:
                continue
            try:
                self.process(event_id, org_id)
                self.attempts.pop(event_id, None)
                self.retry_at.pop(event_id, None)
                done += 1
            except Exception:
                n = self.attempts.get(event_id, 0) + 1
                self.attempts[event_id] = n
                self.retry_at[event_id] = now + min(2 ** n, MAX_BACKOFF)
                level = logging.ERROR if n >= MAX_ATTEMPTS else logging.WARNING
                log.log(level, "poison event skipped" if n >= MAX_ATTEMPTS else "event handler failed; will retry", exc_info=True,
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
    engine = make_engine(url)
    loop = OutboxLoop(engine)
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(worker.jobs.tick, "cron", second=0, args=[engine], id="minute_tick", max_instances=1, coalesce=True)
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
