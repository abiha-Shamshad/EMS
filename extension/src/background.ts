// Service worker (spec Section 9.6): 30-second heartbeat alarm, presence from chrome.idle, break follow-up, viewer
// notices, and opening the Media Session Page after check-in. chrome.alarms allows a 30-second period from Chrome 120
// (manifest minimum_chrome_version), so heartbeats come from here; the server marks a session offline after 90 s of silence.
import { ApiError, api, clearSession, load, save } from "./common.js";
import { HEARTBEAT_ALARM, IDLE_DETECTION_SECONDS } from "./config.js";
import { breakAfterHeartbeat, heartbeatBody, openViewers, type HeartbeatResponse } from "./logic.js";

export type Message = { type: "checked-in"; openMedia: boolean } | { type: "checked-out" } | { type: "heartbeat-now" };

async function startHeartbeats(): Promise<void> {
  await chrome.alarms.create(HEARTBEAT_ALARM, { periodInMinutes: 0.5, delayInMinutes: 0.5 });
}

async function stopHeartbeats(): Promise<void> {
  await chrome.alarms.clear(HEARTBEAT_ALARM);
  await chrome.action.setBadgeText({ text: "" });
}

async function openMediaPage(): Promise<void> {
  const url = chrome.runtime.getURL("media/media.html");
  const [existing] = await chrome.tabs.query({ url });
  if (existing?.id !== undefined) await chrome.tabs.update(existing.id, { active: true });
  else await chrome.tabs.create({ url, pinned: true, active: true });
}

async function heartbeat(): Promise<void> {
  const s = await load();
  if (!s.session) {
    await stopHeartbeats();
    return;
  }
  const idle = await chrome.idle.queryState(IDLE_DETECTION_SECONDS);
  const brk = s.brk ?? { status: "none" as const };
  try {
    const res = await api<HeartbeatResponse>("/room/heartbeat", {
      body: heartbeatBody(s.session, idle, Boolean(s.streaming), brk, new Date(), Boolean(s.camera)), auth: "extension", token: s.session.token });
    const viewers = await api<{ items: { viewer: string; reason: string; seconds: number | null }[] }>("/room/my-viewers", {
      auth: "extension", token: s.session.token }).then((v) => openViewers(v.items)).catch(() => s.viewers ?? []);
    await save({ presence: res.presence, brk: breakAfterHeartbeat(brk, res, new Date()), viewers, lastError: undefined });
    await chrome.action.setBadgeBackgroundColor({ color: viewers.length ? "#c93a3a" : "#4f5bd5" });
    await chrome.action.setBadgeText({ text: viewers.length ? "LIVE" : res.presence === "on_break" ? "BRK" : "" });
  } catch (e) {
    const code = e instanceof ApiError ? e.code : "";
    if (code === "SESSION_CLOSED" || code === "AUTHENTICATION_REQUIRED" || code === "MEMBER_DEACTIVATED") {
      // Checked out elsewhere, auto-closed after work hours, or the token expired: stop until the next check-in.
      await clearSession();
      await stopHeartbeats();
      await save({ lastError: "Your work session has ended. Check in again to continue." });
    } else {
      await save({ lastError: (e as Error).message });
    }
  }
}

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === HEARTBEAT_ALARM) void heartbeat();
});

chrome.runtime.onMessage.addListener((msg: Message, _sender, reply) => {
  void (async () => {
    if (msg.type === "checked-in") {
      await startHeartbeats();
      await heartbeat();
      if (msg.openMedia) await openMediaPage();
    } else if (msg.type === "checked-out") {
      await stopHeartbeats();
    } else if (msg.type === "heartbeat-now") {
      await heartbeat();
    }
    reply({ ok: true });
  })();
  return true;                                          // async reply
});

// After a browser restart the session may still be open: resume heartbeats.
chrome.runtime.onStartup.addListener(() => {
  void load().then((s) => (s.session ? startHeartbeats() : undefined));
});
chrome.runtime.onInstalled.addListener(() => {
  void load().then((s) => (s.session ? startHeartbeats() : undefined));
});
