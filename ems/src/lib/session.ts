// Token storage. "Keep me signed in" ON => localStorage (survives restarts),
// OFF => sessionStorage (cleared when the tab closes).
// TODO(Day 3): read role/company from the JWT; add token refresh in api/client.ts.
import { Role } from './enums';

const KEY = 'ems.session';

export interface Session {
  accessToken: string;
  refreshToken: string | null;
  user: { id: string; name: string; email: string; role: Role };
}

const VALID_ROLES: ReadonlySet<string> = new Set(Object.values(Role));

/** Strict validator — returns null unless the parsed object has every required field. */
function isValidSession(value: unknown): value is Session {
  if (!value || typeof value !== 'object') return false;
  const s = value as Record<string, unknown>;
  if (typeof s['accessToken'] !== 'string' || !s['accessToken']) return false;
  const user = s['user'];
  if (!user || typeof user !== 'object') return false;
  const u = user as Record<string, unknown>;
  if (typeof u['id'] !== 'string' || !u['id']) return false;
  if (typeof u['name'] !== 'string' || !u['name']) return false;
  if (typeof u['email'] !== 'string' || !u['email']) return false;
  if (typeof u['role'] !== 'string' || !VALID_ROLES.has(u['role'])) return false;
  return true;
}

export function saveSession(session: Session, keepSignedIn: boolean): void {
  clearSession();
  (keepSignedIn ? localStorage : sessionStorage).setItem(KEY, JSON.stringify(session));
}

export function getSession(): Session | null {
  const raw = localStorage.getItem(KEY) ?? sessionStorage.getItem(KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw);
    if (!isValidSession(parsed)) {
      clearSession();
      return null;
    }
    return parsed;
  } catch {
    clearSession();
    return null;
  }
}

export function clearSession(): void {
  localStorage.removeItem(KEY);
  sessionStorage.removeItem(KEY);
}
