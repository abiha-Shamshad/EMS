// Unit tests for the extension's state rules (run after `npm run build`: they import the compiled module).
import { strict as assert } from "node:assert";
import { test } from "node:test";

import { breakAfterHeartbeat, heartbeatBody, minutesSince, needsConsent, openViewers } from "../dist/logic.js";

const session = { id: "s1", token: "ext_x", started_at: "2026-10-12T04:02:00Z", task_id: null, streaming_required: true };
const now = new Date("2026-10-12T05:30:00Z");

test("heartbeat never reports streaming during a break", () => {
  assert.deepEqual(heartbeatBody(session, "active", true, { status: "none" }, now, true),
    { session_id: "s1", sent_at: "2026-10-12T05:30:00.000Z", idle_state: "active", streaming: true, camera: true });
  const onBreak = { status: "active", id: "b1", kind: "lunch", minutes: 45, started_at: now.toISOString() };
  const body = heartbeatBody(session, "idle", true, onBreak, now, true);
  assert.equal(body.streaming, false);
  assert.equal(body.camera, false);
});

test("a pending break request resolves from the heartbeat", () => {
  const pending = { status: "requested", id: "b1", kind: "personal", minutes: 90 };
  const still = { presence: "active", server_time: "", next_heartbeat_seconds: 30, pending_break_decision: { break_id: "b1", status: "requested" } };
  assert.deepEqual(breakAfterHeartbeat(pending, still, now), pending);
  const approved = breakAfterHeartbeat(pending, { ...still, presence: "on_break", pending_break_decision: null }, now);
  assert.equal(approved.status, "active");
  assert.deepEqual(breakAfterHeartbeat(pending, { ...still, pending_break_decision: null }, now), { status: "none" });
  assert.deepEqual(breakAfterHeartbeat({ status: "none" }, still, now), { status: "none" });
});

test("only open views are shown as live", () => {
  assert.deepEqual(openViewers([{ viewer: "Imran", reason: "Stand-up", seconds: null }, { viewer: "Zain", reason: "Old", seconds: 200 }]),
    [{ viewer: "Imran", reason: "Stand-up" }]);
});

test("consent is asked again when the notice version grows", () => {
  assert.equal(needsConsent(undefined, 1), true);
  assert.equal(needsConsent(1, 1), false);
  assert.equal(needsConsent(1, 2), true);
});

test("minutesSince floors and never goes negative", () => {
  assert.equal(minutesSince("2026-10-12T05:00:30Z", now), 29);
  assert.equal(minutesSince("2026-10-12T06:00:00Z", now), 0);
});
