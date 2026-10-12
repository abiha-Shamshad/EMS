// Media Session Page (spec Section 9.4, DEC-006, plus the webcam from db/006): the employee clicks to share the screen
// (Chrome's picker every time) and, if they opted in, the webcam. Both publish to the employee's own LiveKit room with a
// publish-only token (API-024); breaks and check-out stop them; resuming needs a new click. No audio is ever captured.
import { LocalVideoTrack, Room, Track } from "livekit-client";

import { api, h, load, save, type Stored } from "../common.js";

type PublishToken = { livekit_url: string; token: string; room: string };
type Kind = "screen" | "camera";

const statusEl = document.getElementById("status")!;
const viewersEl = document.getElementById("viewers")!;
const preview = document.getElementById("preview") as HTMLVideoElement;
let room: Room | null = null;
const live: Record<Kind, MediaStreamTrack | null> = { screen: null, camera: null };

function show(...nodes: (Node | string | null)[]): void {
  statusEl.replaceChildren(...nodes.filter((n): n is Node | string => n !== null));
}

/** One LiveKit connection for both sources; the token allows the camera only with the webcam opt-in. */
async function connect(s: Required<Pick<Stored, "session">>): Promise<Room> {
  if (room) return room;
  const t = await api<PublishToken>("/room/stream/publish-token", {
    body: { session_id: s.session.id, camera: Boolean(s.session.camera_allowed) }, auth: "extension", token: s.session.token });
  const r = new Room({ adaptiveStream: false, dynacast: false });
  await r.connect(t.livekit_url, t.token);
  room = r;
  return r;
}

async function stop(kind: Kind | "all", note?: string): Promise<void> {
  for (const k of kind === "all" ? (["screen", "camera"] as Kind[]) : [kind]) {
    const track = live[k];
    if (!track) continue;
    track.stop();
    const pub = room?.localParticipant.getTrackPublication(k === "screen" ? Track.Source.ScreenShare : Track.Source.Camera);
    if (pub?.track) await room?.localParticipant.unpublishTrack(pub.track);
    live[k] = null;
  }
  if (!live.screen && !live.camera) {
    await room?.disconnect();
    room = null;
  }
  preview.hidden = !live.camera && !live.screen;
  await save({ streaming: Boolean(live.screen), camera: Boolean(live.camera) });
  await chrome.runtime.sendMessage({ type: "heartbeat-now" }).catch(() => undefined);
  await render(note);
}

async function start(kind: Kind): Promise<void> {
  const s = await load();
  if (!s.session) return render("You are not checked in. Check in from the EMS button in the toolbar.");
  let stream: MediaStream;
  try {
    // Must run inside the click handler: Chrome requires a user gesture (EV-001). Never audio.
    stream = kind === "screen"
      ? await navigator.mediaDevices.getDisplayMedia({ video: { frameRate: 5, width: { max: 1280 }, height: { max: 720 } }, audio: false })
      : await navigator.mediaDevices.getUserMedia({ video: { width: { ideal: 640 }, height: { ideal: 360 }, frameRate: { max: 10 } }, audio: false });
  } catch {
    return render(kind === "screen" ? "Screen sharing was cancelled." : "The webcam was not allowed or is in use by another app.");
  }
  const track = stream.getVideoTracks()[0];
  if (!track) return render("No video was selected.");
  try {
    const r = await connect({ session: s.session });
    await r.localParticipant.publishTrack(new LocalVideoTrack(track),
      { source: kind === "screen" ? Track.Source.ScreenShare : Track.Source.Camera, simulcast: false });
  } catch (e) {
    track.stop();
    return render(e instanceof Error ? e.message : "Could not start sharing.");
  }
  live[kind] = track;
  track.addEventListener("ended", () => void stop(kind, kind === "screen" ? "Screen sharing stopped." : "The webcam stopped."));
  if (kind === "camera" || !live.camera) {
    preview.srcObject = new MediaStream([track]);
    preview.hidden = false;
  }
  await save({ streaming: Boolean(live.screen), camera: Boolean(live.camera) });
  await chrome.runtime.sendMessage({ type: "heartbeat-now" }).catch(() => undefined);
  await render();
}

async function render(note?: string): Promise<void> {
  const s = await load();
  viewersEl.replaceChildren(...(s.viewers ?? []).map((x) => h("div", { class: "alert live" }, `${x.viewer} is viewing you live. Reason: ${x.reason}`)));
  if (!s.session) {
    show(h("h2", {}, "Not checked in"), h("p", { class: "muted" }, note ?? "Check in from the EMS button in the toolbar."));
    return;
  }
  if (s.brk?.status === "active") {
    show(h("h2", {}, "On a break"), h("p", { class: "muted" }, "Screen and webcam are paused. When the break ends, start them again here."));
    return;
  }
  const toggle = (kind: Kind, label: string) => live[kind]
    ? h("button", { class: "ghost", onclick: () => void stop(kind, `You stopped the ${label.toLowerCase()}.`) }, `Stop ${label.toLowerCase()}`)
    : h("button", { onclick: () => void start(kind) }, `Start ${label.toLowerCase()}`);
  show(
    h("h2", {}, [live.screen ? "Screen: live" : "Screen: off", live.camera ? "Webcam: live" : "Webcam: off"].join(" · ")),
    note ? h("p", { class: "muted" }, note) : null,
    h("div", { class: "row" }, toggle("screen", "Screen sharing"),
      s.session.camera_allowed ? toggle("camera", "Webcam") : h("p", { class: "muted" }, "Webcam: not opted in (change it in Settings or on the EMS website).")),
  );
}

// Breaks pause everything at once (Section 9.4 step 5); check-out stops it; viewers and break changes refresh the page.
chrome.storage.onChanged.addListener((changes) => {
  void (async () => {
    const s = await load();
    if (changes.brk && s.brk?.status === "active") await stop("all", "Break started: screen and webcam paused.");
    else if (changes.session && !s.session) await stop("all", "You checked out.");
    else if (changes.viewers || changes.brk || changes.session) await render();
  })();
});
window.addEventListener("pagehide", () => {
  live.screen?.stop();
  live.camera?.stop();
  void save({ streaming: false, camera: false });
});

void render();
