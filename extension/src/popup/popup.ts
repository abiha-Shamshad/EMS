// Popup (spec Section 9.6): sign-in, monitoring consent, check-in/out with a task picker, break panel.
import type { Message } from "../background.js";
import { ApiError, api, clearSession, h, load, save, webUrl } from "../common.js";
import { EXTENSION_VERSION } from "../config.js";
import { minutesSince, needsConsent, type BreakState, type WorkSession } from "../logic.js";

type Me = { user: { id: string; name: string }; active_org: { name: string; role: string; time_zone: string } };
type Org = { room_policy_version: number; live_view_enabled: boolean };
type CheckIn = { session_id: string; started_at: string; minutes_late?: number; extension_token?: string; streaming_required?: boolean;
  camera_allowed?: boolean; already_open?: boolean };
type TaskOption = { id: string; title: string; project: string };

const app = document.getElementById("app")!;
const who = document.getElementById("who")!;

function render(...nodes: (Node | null | false)[]): void {
  app.replaceChildren(...nodes.filter((n): n is Node => Boolean(n)));
}
const errorBox = (e: unknown) => h("div", { class: "alert error", role: "alert" }, e instanceof Error ? e.message : String(e));
const send = (msg: Message) => chrome.runtime.sendMessage(msg);

async function start(): Promise<void> {
  let me: Me;
  try {
    me = await api<Me>("/me");
  } catch (e) {
    if (e instanceof ApiError && e.code === "AUTHENTICATION_REQUIRED") return signIn();
    if (e instanceof ApiError && e.code === "ORG_NOT_SELECTED") {
      return render(h("div", { class: "alert info" }, "You belong to several companies. Choose one on the EMS website, then reopen this popup."),
        h("button", { onclick: () => void chrome.tabs.create({ url: webUrl("/select-company") }) }, "Open EMS"));
    }
    return render(errorBox(e), h("button", { class: "ghost", onclick: () => void start() }, "Try again"));
  }
  who.textContent = `${me.user.name} · ${me.active_org.name}`;
  const org = await api<Org>("/org").catch(() => null);
  const s = await load();
  if (org && needsConsent(s.consentedVersion, org.room_policy_version) && !sessionStorage.getItem("consent-skipped")) return consent(org);
  if (s.session) return checkedIn(me);
  return checkIn(me);
}

// ------------------------------------------------------------------------------------------------ sign-in
function signIn(): void {
  who.textContent = "";
  const email = h("input", { type: "email", autocomplete: "email", placeholder: "name@company.com", required: true });
  const password = h("input", { type: "password", autocomplete: "current-password", required: true });
  const remember = h("input", { type: "checkbox" });
  const status = h("div");
  const form = h("form", { class: "card" },
    h("h1", {}, "Sign in to EMS"),
    h("p", { class: "muted" }, "Use your work account. If you are signed in on the EMS website, reopen this popup."),
    h("label", {}, "Work email", email), h("label", {}, "Password", password),
    h("label", { class: "check" }, remember, "Keep me signed in"), status,
    h("button", { type: "submit" }, "Sign in"),
    h("button", { type: "button", class: "ghost", onclick: () => void chrome.tabs.create({ url: webUrl("/login") }) }, "Sign in on the website (Google)"));
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    status.replaceChildren();
    api("/auth/login", { body: { email: email.value, password: password.value, remember: remember.checked } })
      .then(() => start())
      .catch((err) => status.replaceChildren(errorBox(err)));
  });
  render(form);
}

// ------------------------------------------------------------------------------------------------ consent (Section 9.2)
async function consent(org: Org): Promise<void> {
  const policies = await api<{ items: { topic: string; version: number; text: string }[] }>("/hr-agent/policies").catch(() => ({ items: [] }));
  const notice = policies.items.find((p) => p.topic === "monitoring");
  const status = h("div");
  const webcam = h("input", { type: "checkbox" });
  const accept = (yes: boolean) => {
    api<{ policy_version: number }>("/room/consent", { body: { policy_version: org.room_policy_version, accept: yes, ...(yes ? { webcam: webcam.checked } : {}) } })
      .then(async (r) => {
        if (yes) {
          const fresh = await load();
          await save({ consentedVersion: r.policy_version,
            ...(fresh.session ? { session: { ...fresh.session, camera_allowed: webcam.checked && org.live_view_enabled } } : {}) });
        } else sessionStorage.setItem("consent-skipped", "1");
        await start();
      })
      .catch((e) => status.replaceChildren(errorBox(e)));
  };
  render(h("div", { class: "card" },
    h("h1", {}, "Monitoring notice"),
    notice ? h("p", {}, notice.text) : null,
    h("p", {}, "While you are checked in, EMS records:"),
    h("ul", {}, h("li", {}, "check-in and check-out time, and the task you pick"), h("li", {}, "presence: active, idle or locked"),
      h("li", {}, "breaks"), h("li", {}, `your live screen, only to an authorized viewer, never stored${org.live_view_enabled ? "" : " (switched off for your company right now)"}`),
      h("li", {}, "your live webcam, only if you tick the box below; never stored")),
    h("p", {}, "EMS never collects keystrokes, browsing history, screenshots or recordings, audio, or anything while you are checked out or on a break."),
    h("label", { class: "check" }, webcam, "Also share my webcam live while I am checked in"),
    h("p", { class: "muted" }, "Every view of your screen is shown to you, with the viewer's name and reason. You can withdraw consent at any time."),
    status,
    h("button", { onclick: () => accept(true) }, "I consent"),
    h("button", { class: "ghost", onclick: () => { sessionStorage.setItem("consent-skipped", "1"); void start(); } }, "Not now (attendance only, no screen sharing)")));
}

// ------------------------------------------------------------------------------------------------ check-in
async function myTasks(meId: string): Promise<TaskOption[]> {
  const projects = await api<{ items: { id: string; name: string; status: string }[] }>("/projects?limit=20").catch(() => ({ items: [] }));
  const open = projects.items.filter((p) => !["completed", "cancelled"].includes(p.status)).slice(0, 10);
  const boards = await Promise.all(open.map((p) =>
    api<{ columns: Record<string, { id: string; title: string }[]> }>(`/projects/${p.id}/board?assignee_id=${meId}`)
      .then((b) => [...(b.columns.active ?? []), ...(b.columns.todo ?? []), ...(b.columns.review ?? [])].map((t) => ({ id: t.id, title: t.title, project: p.name })))
      .catch(() => [] as TaskOption[])));
  return boards.flat();
}

async function checkIn(me: Me): Promise<void> {
  const s = await load();
  const select = h("select", {}, h("option", { value: "" }, "No task selected"));
  const status = h("div", {}, s.lastError ? h("div", { class: "alert info" }, s.lastError) : null);
  const button = h("button", {}, "Check in");
  render(h("div", { class: "card" }, h("h1", {}, `Good to see you, ${me.user.name.split(" ")[0]}`),
    h("p", { class: "muted" }, "Check in to start your workday."), h("label", {}, "What are you working on?", select), status, button));
  void myTasks(me.user.id).then((tasks) => tasks.forEach((t) => select.append(h("option", { value: t.id }, `${t.title} · ${t.project}`))));

  button.addEventListener("click", () => {
    button.disabled = true;
    api<CheckIn>("/room/check-in", { body: { device: { kind: "chrome_extension", extension_version: EXTENSION_VERSION }, task_id: select.value || null } })
      .then(async (r) => {
        if (!r.extension_token) {
          status.replaceChildren(h("div", { class: "alert info" }, "EMS did not issue a token for this session. Check out and check in again."));
          button.disabled = false;
          return;
        }
        // After a web check-in the API returns the open session with a fresh token: the extension attaches to it.
        const session: WorkSession = { id: r.session_id, token: r.extension_token, started_at: r.started_at, task_id: select.value || null,
          streaming_required: Boolean(r.streaming_required), camera_allowed: Boolean(r.camera_allowed) };
        await save({ session, brk: { status: "none" }, streaming: false, lastError: undefined });
        await send({ type: "checked-in", openMedia: session.streaming_required });
        await start();
      })
      .catch((e) => { status.replaceChildren(errorBox(e)); button.disabled = false; });
  });
}

// ------------------------------------------------------------------------------------------------ checked in
async function checkedIn(me: Me): Promise<void> {
  const s = await load();
  const session = s.session!;
  const brk: BreakState = s.brk ?? { status: "none" };
  const status = h("div");
  const fail = (e: unknown) => status.replaceChildren(errorBox(e));
  const presence = s.presence ?? "active";

  const breakPanel = (() => {
    if (brk.status === "requested") return h("div", { class: "card" }, h("h2", {}, "Break request sent"),
      h("p", { class: "muted" }, `${brk.minutes}-minute ${brk.kind} break is above today's allowance and waits for your manager.`));
    if (brk.status === "active") {
      return h("div", { class: "card" }, h("h2", {}, `On a ${brk.kind} break`),
        h("p", { class: "muted" }, `${minutesSince(brk.started_at, new Date())} of ${brk.minutes} minutes. Screen sharing is paused.`),
        h("button", { onclick: () => {
          api<{ stream_resume: boolean }>(`/room/breaks/${brk.id}/end`, { method: "POST", auth: "extension", token: session.token })
            .then(async (r) => {
              await save({ brk: { status: "none" } });
              await send({ type: "heartbeat-now" });
              if (r.stream_resume) await chrome.tabs.create({ url: chrome.runtime.getURL("media/media.html"), pinned: true });
              await start();
            }).catch(fail);
        } }, "End break"));
    }
    const kind = h("select", {}, ...["short", "lunch", "prayer", "personal"].map((k) => h("option", { value: k }, k[0]!.toUpperCase() + k.slice(1))));
    const mins = h("input", { type: "number", min: "5", max: "120", value: "15" });
    return h("div", { class: "card" }, h("h2", {}, "Take a break"), h("div", { class: "row" }, kind, mins),
      h("button", { class: "ghost", onclick: () => {
        api<{ break_id: string; status: "active" | "requested"; started_at: string | null }>("/room/breaks", {
          body: { session_id: session.id, kind: kind.value, minutes: Number(mins.value) }, auth: "extension", token: session.token })
          .then(async (r) => {
            await save({ brk: r.status === "active"
              ? { status: "active", id: r.break_id, kind: kind.value, minutes: Number(mins.value), started_at: r.started_at ?? new Date().toISOString() }
              : { status: "requested", id: r.break_id, kind: kind.value, minutes: Number(mins.value) }, streaming: false });
            await send({ type: "heartbeat-now" });
            await start();
          }).catch(fail);
      } }, "Start break"));
  })();

  const note = h("textarea", { placeholder: "What did you get done? (optional)", maxlength: "2000" });
  const viewers = s.viewers ?? [];
  render(
    viewers.length ? h("div", { class: "alert live" }, ...viewers.map((v) => h("div", {}, `${v.viewer} is viewing your screen: ${v.reason}`))) : null,
    h("div", { class: "card" },
      h("div", { class: "row" }, h("h1", {}, "Checked in"), h("span", { class: `badge ${presence === "active" ? "ok" : presence === "offline" ? "off" : "warn"}` }, presence.replace("_", " "))),
      h("p", { class: "muted" }, `Since ${new Date(session.started_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} · ${me.active_org.name}`),
      h("p", {}, [s.streaming ? "Sharing your screen" : "Screen not shared", s.camera ? "webcam on" : "webcam off"].join(" · ")),
      (session.streaming_required || session.camera_allowed) && brk.status !== "active"
        ? h("button", { class: "ghost", onclick: () => void chrome.tabs.create({ url: chrome.runtime.getURL("media/media.html"), pinned: true }) }, "Open sharing page")
        : null),
    breakPanel,
    h("div", { class: "card" }, h("h2", {}, "Check out"), note,
      h("button", { class: "danger", onclick: () => {
        api<{ totals_minutes: Record<string, number> }>("/room/check-out", { body: { session_id: session.id, note: note.value || null }, auth: "extension", token: session.token })
          .then(async (r) => {
            await clearSession();
            await send({ type: "checked-out" });
            render(h("div", { class: "card" }, h("h1", {}, "Checked out. Good work today."),
              h("p", { class: "muted" }, `Active ${r.totals_minutes.active ?? 0} min · idle ${r.totals_minutes.idle ?? 0} min · breaks ${r.totals_minutes.on_break ?? 0} min`)));
          }).catch(async (e) => {
            if (e instanceof ApiError && (e.code === "NO_OPEN_SESSION" || e.code === "SESSION_CLOSED")) { await clearSession(); await send({ type: "checked-out" }); await start(); }
            else fail(e);
          });
      } }, "Check out")),
    status,
    h("div", { class: "row" },
      h("button", { class: "ghost", onclick: () => void chrome.runtime.openOptionsPage() }, "Settings"),
      h("button", { class: "ghost", onclick: () => void chrome.tabs.create({ url: webUrl("/room/me") }) }, "My workday")),
  );
}

void start();
