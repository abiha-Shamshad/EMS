// Auth + onboarding API. All calls go through `api` (never raw fetch).
// In demo mode (VITE_DEMO_MODE=true) every flow below works against
// fictional sample data so the frontend is fully explorable without a
// backend. Set VITE_DEMO_MODE=false once Abiha's API is live.
import type { Role } from '@/lib/enums';
import { Role as RoleEnum } from '@/lib/enums';
import { env } from '@/lib/env';
import { slugifyCompanyName, type InviteRow } from '@/lib/validation';
import type { Session } from '@/lib/session';
import { api } from './client';
import { ApiError, ERROR_CODES } from './errors';

export const AUTH_ENDPOINTS = {
  login: '/api/v1/auth/login',
  signup: '/api/v1/auth/signup',
  forgotPassword: '/api/v1/auth/password/forgot',
  resetPassword: '/api/v1/auth/password/reset',
  companySetup: '/api/v1/org',
  invites: '/api/v1/invitations',
} as const;

// --- Shapes (CONTRACT-PENDING: replace with generated types after gen:api) ---

export interface LoginInput {
  email: string;
  password: string;
}

interface LoginResponse {
  access_token: string;
  refresh_token: string | null;
  user: { id: string; name: string; email: string; role: Role };
}

export interface SignupInput {
  companyName: string;
  email: string;
  password: string;
}

export interface SignupResult {
  companyName: string;
  companySlug: string;
  nextStep: 'company_setup';
}

export interface CompanySetupInput {
  companyName: string;
  industry: string;
  companySize: string;
  companyWebsite: string;
  timeZone: string;
  about: string;
}

export interface InviteResultItem {
  email: string;
  status: 'invited' | 'already_invited';
  invitationId: string;
  expiresAt: string;
}

export interface InviteTeamResult {
  results: InviteResultItem[];
  emailDelivery: 'not_configured' | 'sent';
  copyLinks: boolean;
  inviteLinks: Array<{ email: string; link: string }>;
}

// --- Public functions ---------------------------------------------------

export async function loginRequest(input: LoginInput): Promise<Session> {
  if (env.isDemoMode) return demoLogin(input);
  const data = await api.post<LoginResponse>(AUTH_ENDPOINTS.login, input, { auth: false });
  return { accessToken: data.access_token, refreshToken: data.refresh_token, user: data.user };
}

export async function signupRequest(input: SignupInput): Promise<SignupResult> {
  if (env.isDemoMode) return demoSignup(input);
  const data = await api.post<SignupResult>(
    AUTH_ENDPOINTS.signup,
    {
      company_name: input.companyName,
      company_slug: slugifyCompanyName(input.companyName),
      name: displayNameFromEmail(input.email),
      email: input.email,
      password: input.password,
    },
    { auth: false },
  );
  return data;
}

export async function forgotPasswordRequest(email: string): Promise<{ accepted: boolean }> {
  if (env.isDemoMode) {
    await delay(700);
    return { accepted: true };
  }
  return api.post<{ accepted: boolean }>(AUTH_ENDPOINTS.forgotPassword, { email }, { auth: false });
}

export async function resetPasswordRequest(input: {
  token: string;
  newPassword: string;
}): Promise<{ passwordChanged: boolean }> {
  if (env.isDemoMode) return demoResetPassword(input.token);
  const data = await api.post<{ password_changed: boolean }>(
    AUTH_ENDPOINTS.resetPassword,
    { token: input.token, new_password: input.newPassword },
    { auth: false },
  );
  return { passwordChanged: data.password_changed };
}

export async function companySetupRequest(input: CompanySetupInput): Promise<{ nextStep: string }> {
  if (env.isDemoMode) {
    await delay(800);
    saveDemoOrg(input);
    return { nextStep: 'invite_team' };
  }
  const data = await api.post<{ next_step: string }>(
    AUTH_ENDPOINTS.companySetup,
    {
      company_name: input.companyName,
      industry: input.industry,
      size_band: input.companySize,
      company_website: input.companyWebsite || undefined,
      time_zone: input.timeZone,
      about: input.about || undefined,
    },
  );
  return { nextStep: data.next_step };
}

export async function inviteTeamRequest(input: {
  rows: InviteRow[];
  message: string;
}): Promise<InviteTeamResult> {
  if (env.isDemoMode) return demoInvite(input.rows);
  const data = await api.post<{
    results: Array<{ email: string; status: 'invited'; invitation_id: string; expires_at: string }>;
    email_delivery: 'not_configured' | 'sent';
    copy_links: boolean;
  }>(AUTH_ENDPOINTS.invites, {
    invites: input.rows.map((row) => ({ email: row.email.trim(), role: row.role })),
    message: input.message || undefined,
  });
  const origin = window.location.origin;
  const results: InviteResultItem[] = data.results.map((row) => ({
    email: row.email,
    status: row.status,
    invitationId: row.invitation_id,
    expiresAt: row.expires_at,
  }));
  return {
    results,
    emailDelivery: data.email_delivery,
    copyLinks: data.copy_links,
    inviteLinks: results.map((row) => ({
      email: row.email,
      link: `${origin}/accept-invite?token=${row.invitationId}`,
    })),
  };
}

// --- Demo mode ----------------------------------------------------------

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export function displayNameFromEmail(email: string): string {
  const local = email.split('@')[0] ?? 'Demo user';
  const titled = local.replace(/[._-]+/g, ' ').trim() || 'Demo user';
  return titled.replace(/\b\w/g, (char) => char.toUpperCase());
}

async function demoLogin({ email, password }: LoginInput): Promise<Session> {
  await delay(700);
  if (password.length < 4) {
    throw new ApiError(401, ERROR_CODES.invalidCredentials, 'Incorrect email or password.');
  }
  const name = displayNameFromEmail(email);
  return {
    accessToken: 'demo-access-token',
    refreshToken: null,
    user: { id: 'demo-user', name, email, role: RoleEnum.Ceo },
  };
}

async function demoSignup(input: SignupInput): Promise<SignupResult> {
  await delay(900);
  if (input.email.trim().toLowerCase() === 'taken@company.com') {
    throw new ApiError(409, ERROR_CODES.emailInUse, 'An account with this email already exists. Try signing in.');
  }
  const slug = slugifyCompanyName(input.companyName);
  saveDemoOrg({ companyName: input.companyName } as CompanySetupInput);
  return { companyName: input.companyName.trim(), companySlug: slug, nextStep: 'company_setup' };
}

async function demoResetPassword(token: string): Promise<{ passwordChanged: boolean }> {
  await delay(800);
  if (!token || token === 'expired') {
    throw new ApiError(
      410,
      ERROR_CODES.resetTokenExpired,
      'This reset link has expired. Request a new one.',
    );
  }
  return { passwordChanged: true };
}

async function demoInvite(rows: InviteRow[]): Promise<InviteTeamResult> {
  await delay(900);
  const origin = window.location.origin;
  const results: InviteResultItem[] = rows.map((row, index) => ({
    email: row.email.trim(),
    status: 'invited',
    invitationId: `demo-invite-${Date.now()}-${index}`,
    expiresAt: new Date(Date.now() + 7 * 24 * 3600 * 1000).toISOString(),
  }));
  return {
    results,
    emailDelivery: 'not_configured',
    copyLinks: true,
    inviteLinks: results.map((row) => ({
      email: row.email,
      link: `${origin}/accept-invite?token=${row.invitationId}`,
    })),
  };
}

const DEMO_ORG_KEY = 'ems.demo.org';

export function saveDemoOrg(input: CompanySetupInput): void {
  try {
    localStorage.setItem(DEMO_ORG_KEY, JSON.stringify({ companyName: input.companyName }));
  } catch {
    /* storage unavailable - demo continues without it */
  }
}

export function getDemoOrgName(): string | null {
  try {
    const raw = localStorage.getItem(DEMO_ORG_KEY);
    if (!raw) return null;
    return (JSON.parse(raw) as { companyName?: string }).companyName ?? null;
  } catch {
    return null;
  }
}
