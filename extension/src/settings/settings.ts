// Settings (spec Section 9.6): company, the monitoring notice, consent, and "who viewed me".
import { ApiError, api, clearSession, h, load, save, webUrl } from "../common.js";
import { EMS_ORIGIN } from "../config.js";

type Me = { user: { name: string; email: string }; active_org: { name: string; role: string } };
type Viewer = { view_id: string; viewer: string; reason: string; started_at: string; seconds: number | null };

const app = document.getElementById("app")!;

async function main(): Promise<void> {
  let me: Me;
  try {
    me = await api<Me>("/me");
  } catch (e) {
    app.replaceChildren(h("h1", {}, "EMS extension"), h("div", { class: "alert info" }, e instanceof ApiError && e.code === "AUTHENTICATION_REQUIRED"
      ? "You are not signed in. Use the EMS button in the toolbar to sign in." : (e as Error).message));
    return;
  }
  const s = await load();
  const [org, policies, viewers] = await Promise.all([
    api<{ room_policy_version: number; live_view_enabled: boolean }>("/org").catch(() => null),
    api<{ items: { topic: string; version: number; text: string }[] }>("/hr-agent/policies").catch(() => ({ items: [] })),
    api<{ items: Viewer[] }>("/room/my-viewers").catch(() => ({ items: [] as Viewer[] })),
  ]);
  const notice = policies.items.find((p) => p.topic === "monitoring");
  const status = h("div");
  const webcam = h("input", { type: "checkbox", ...(s.session?.camera_allowed ? { checked: true } : {}) });
  const consent = (accept: boolean) => {
    if (!org) return;
    api<{ policy_version: number; webcam?: boolean }>("/room/consent", { body: { policy_version: org.room_policy_version, accept, ...(accept ? { webcam: webcam.checked } : {}) } })
      .then(async (r) => {
        const fresh = await load();
        await save({ consentedVersion: accept ? r.policy_version : undefined, ...(accept ? {} : { streaming: false, camera: false }),
          ...(fresh.session ? { session: { ...fresh.session, camera_allowed: accept && webcam.checked && Boolean(org.live_view_enabled) } } : {}) });
        status.replaceChildren(h("div", { class: "alert info" }, accept ? `Consent recorded${webcam.checked ? ", including the webcam" : " (screen only)"}.`
          : "Consent withdrawn. Screen and webcam sharing stopped and viewers were disconnected."));
      })
      .catch((e) => status.replaceChildren(h("div", { class: "alert error" }, (e as Error).message)));
  };

  app.replaceChildren(
    h("h1", {}, "EMS extension settings"),
    h("div", { class: "card" }, h("h2", {}, "Account"),
      h("p", {}, `${me.user.name} (${me.user.email})`), h("p", { class: "muted" }, `${me.active_org.name} · ${me.active_org.role.toUpperCase()}`),
      h("p", { class: "muted" }, `Connected to ${EMS_ORIGIN}`),
      h("div", { class: "row" },
        h("button", { class: "ghost", onclick: () => void chrome.tabs.create({ url: webUrl("/") }) }, "Open EMS"),
        h("button", { class: "ghost", onclick: () => void api("/auth/logout", { method: "POST" }).finally(async () => { await clearSession(); await main(); }) }, "Sign out"))),
    h("div", { class: "card" }, h("h2", {}, `Monitoring notice${org ? ` (version ${org.room_policy_version})` : ""}`),
      h("p", {}, notice?.text ?? "Your company has not published its own notice text yet. The EMS defaults apply: presence, idle state, current task, your live screen and (if you opt in) your live webcam while checked in; never recordings, keystrokes, browsing history or audio."),
      h("p", { class: "muted" }, org?.live_view_enabled ? "Live screen viewing is on for your company." : "Live screen viewing is switched off for your company."),
      h("p", { class: "muted" }, s.consentedVersion ? `You consented to version ${s.consentedVersion} on this browser.` : "You have not consented on this browser."),
      h("label", { class: "check" }, webcam, "Also share my webcam live while I am checked in"),
      h("div", { class: "row" }, h("button", { onclick: () => consent(true) }, "I consent"), h("button", { class: "danger", onclick: () => consent(false) }, "Withdraw consent")),
      status),
    h("div", { class: "card" }, h("h2", {}, "Who viewed me live (last 7 days)"),
      viewers.items.length === 0 ? h("p", { class: "muted" }, "Nobody has viewed you live.") :
        h("ul", {}, ...viewers.items.map((v) => h("li", {}, `${new Date(v.started_at).toLocaleString()} · ${v.viewer} · ${v.reason} · ${v.seconds === null ? "viewing now" : `${Math.max(1, Math.round(v.seconds / 60))} min`}`)))),
  );
}

void main();
