// API client for the EMS backend (spec Section 19). Same-origin requests through the /api/v1 rewrite.
// Unsafe methods echo the ems_csrf cookie in X-CSRF-Token (double submit, Section 7.3); creating POSTs marked
// "Idempotency-Key required" pass `idempotent: true`, which sends a fresh key (a retry of the same submit reuses it).

export type ApiErrorBody = { code: string; message: string; retryable: boolean; details: Record<string, unknown> };

export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly retryable: boolean;
  readonly details: Record<string, unknown>;

  constructor(status: number, body: ApiErrorBody) {
    super(body.message);
    this.status = status;
    this.code = body.code;
    this.retryable = body.retryable;
    this.details = body.details ?? {};
  }

  /** Field errors from VALIDATION_FAILED, keyed by field path ("email", "invites[0].role"). */
  get fields(): Record<string, string> {
    const f = this.details.fields;
    return f && typeof f === "object" ? (f as Record<string, string>) : {};
  }
}

const ORG_KEY = "ems_org";
const UNSAFE = new Set(["POST", "PUT", "PATCH", "DELETE"]);

export function readCookie(name: string, cookies: string = typeof document === "undefined" ? "" : document.cookie): string | null {
  for (const part of cookies.split(";")) {
    const [k, ...v] = part.trim().split("=");
    if (k === name) return decodeURIComponent(v.join("="));
  }
  return null;
}

function selectedOrg(): string | null {
  try {
    return window.localStorage.getItem(ORG_KEY);
  } catch {
    return null;
  }
}

export function selectOrg(orgId: string | null): void {
  try {
    if (orgId) window.localStorage.setItem(ORG_KEY, orgId);
    else window.localStorage.removeItem(ORG_KEY);
  } catch {
    // storage unavailable (private mode): the backend picks the only company, or asks again
  }
}

export function newIdempotencyKey(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

type Options = {
  method?: string;
  body?: unknown;
  query?: Record<string, string | number | boolean | null | undefined>;
  idempotencyKey?: string;
  idempotent?: boolean;
  signal?: AbortSignal;
};

export function buildUrl(path: string, query?: Options["query"]): string {
  const url = `/api/v1${path}`;
  if (!query) return url;
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(query)) if (v !== undefined && v !== null && v !== "") qs.set(k, String(v));
  const s = qs.toString();
  return s ? `${url}?${s}` : url;
}

export async function api<T>(path: string, opts: Options = {}): Promise<T> {
  const method = (opts.method ?? (opts.body !== undefined ? "POST" : "GET")).toUpperCase();
  const headers: Record<string, string> = { Accept: "application/json" };
  if (opts.body !== undefined) headers["Content-Type"] = "application/json";
  if (UNSAFE.has(method)) {
    const csrf = readCookie("ems_csrf");
    if (csrf) headers["X-CSRF-Token"] = csrf;
  }
  const key = opts.idempotencyKey ?? (opts.idempotent ? newIdempotencyKey() : undefined);
  if (key) headers["Idempotency-Key"] = key;
  const org = typeof window === "undefined" ? null : selectedOrg();
  if (org) headers["X-Org-Id"] = org;

  let res: Response;
  try {
    res = await fetch(buildUrl(path, opts.query), {
      method,
      headers,
      body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
      credentials: "same-origin",
      signal: opts.signal,
    });
  } catch (e) {
    if ((e as Error).name === "AbortError") throw e;
    throw new ApiError(0, { code: "NETWORK", message: "Can't reach EMS. Check your connection and try again.", retryable: true, details: {} });
  }
  const json = await res.json().catch(() => null);
  if (!res.ok || !json || json.success === false) {
    const body: ApiErrorBody = json?.error ?? { code: "INTERNAL_ERROR", message: "Something went wrong.", retryable: true, details: {} };
    throw new ApiError(res.status, body);
  }
  return json.data as T;
}

export const get = <T>(path: string, query?: Options["query"], signal?: AbortSignal) => api<T>(path, { query, signal });
export const post = <T>(path: string, body: unknown = {}, extra: Omit<Options, "body" | "method"> = {}) =>
  api<T>(path, { ...extra, method: "POST", body });
export const patch = <T>(path: string, body: unknown) => api<T>(path, { method: "PATCH", body });
export const put = <T>(path: string, body: unknown) => api<T>(path, { method: "PUT", body });
