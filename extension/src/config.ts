// Replaced at build time (build.mjs, EMS_ORIGIN). The extension talks only to this origin: the EMS web app, which
// proxies /api/v1 to the API, so the extension shares the web sign-in (spec Section 9.6: host permission for EMS only).
export const EMS_ORIGIN: string = "__EMS_ORIGIN__";
export const EXTENSION_VERSION = "1.0.0";
export const HEARTBEAT_ALARM = "ems-heartbeat";
export const IDLE_DETECTION_SECONDS = 300;            // chrome.idle interval (Section 9.3): under 5 minutes without input stays active
