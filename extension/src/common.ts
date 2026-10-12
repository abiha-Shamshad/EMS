// API access and stored state for every extension context (service worker, popup, media page, settings).
import { EMS_ORIGIN } from "./config.js";
import type { BreakState, Presence, WorkSession } from "./logic.js";

export type ApiFailure = { status: number; code: string; message: string; retryable: boolean; details: Record<string, unknown> };

export class ApiError extends Error {
  constructor(readonly failure: ApiFailure) {
    super(failure.message);
  }
  get code(): string {
    return this.failure.code;
  }
}

/** Everything the extension keeps (chrome.storage.local). Tokens are never logged or sent anywhere but EMS. */
export type Stored = {
  session?: WorkSession;
  brk?: BreakState;
  streaming?: boolean;                 // the Media Session Page is publishing the screen right now
  camera?: boolean;                    // ... and the webcam
  presence?: Presence;
  viewers?: { viewer: string; reason: string }[];
  consentedVersion?: number;
  lastError?: string;
};

export async function load(): Promise<Stored> {
  return (await chrome.storage.local.get(null)) as Stored;
}

export async function save(patch: Partial<Stored>): Promise<void> {
  await chrome.storage.local.set(patch);
}

export async function clearSession(): Promise<void> {
  await chrome.storage.local.remove(["session", "brk", "streaming", "camera", "presence", "viewers"]);
}

async function csrfToken(): Promise<string | null> {
  const c = await chrome.cookies.get({ url: EMS_ORIGIN, name: "ems_csrf" });
  return c ? decodeURIComponent(c.value) : null;
}

/**
 * Call the EMS API. `auth: "session"` uses the web sign-in cookie (+ CSRF header on writes); `auth: "extension"` uses
 * the extension token issued at check-in (API-018), which is bound to that one work session.
 */
export async function api<T>(path: string, opts: { method?: string; body?: unknown; auth?: "session" | "extension"; token?: string } = {}): Promise<T> {
  const method = opts.method ?? (opts.body !== undefined ? "POST" : "GET");
  const headers: Record<string, string> = { Accept: "application/json" };
  if (opts.body !== undefined) headers["Content-Type"] = "application/json";
  if (opts.auth === "extension") {
    if (!opts.token) throw new ApiError({ status: 401, code: "AUTHENTICATION_REQUIRED", message: "Check in again.", retryable: false, details: {} });
    headers.Authorization = `Bearer ${opts.token}`;
  } else if (method !== "GET") {
    const csrf = await csrfToken();
    if (csrf) headers["X-CSRF-Token"] = csrf;
  }
  let res: Response;
  try {
    res = await fetch(`${EMS_ORIGIN}/api/v1${path}`, {
      method, headers, credentials: opts.auth === "extension" ? "omit" : "include",
      body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
    });
  } catch {
    throw new ApiError({ status: 0, code: "NETWORK", message: "Can't reach EMS. Check your connection.", retryable: true, details: {} });
  }
  const json = await res.json().catch(() => null);
  if (!res.ok || !json || json.success === false) {
    const e = json?.error ?? { code: "INTERNAL_ERROR", message: "Something went wrong.", retryable: true, details: {} };
    throw new ApiError({ status: res.status, ...e });
  }
  return json.data as T;
}

/** Small DOM helper for the vanilla pages. */
export function h<K extends keyof HTMLElementTagNameMap>(tag: K, attrs: Record<string, string | boolean | ((e: Event) => void)> = {},
  ...children: (Node | string | null | false)[]): HTMLElementTagNameMap[K] {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (typeof v === "function") el.addEventListener(k.replace(/^on/, "").toLowerCase(), v as EventListener);
    else if (v === true) el.setAttribute(k, "");
    else if (v !== false) el.setAttribute(k, v);
  }
  for (const c of children) if (c !== null && c !== false) el.append(c);
  return el;
}

export function webUrl(path: string): string {
  return `${EMS_ORIGIN}${path}`;
}
