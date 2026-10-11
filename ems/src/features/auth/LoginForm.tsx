import { type FormEvent, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { toErrorMessage } from '@/api/errors';
import alertIcon from '@/assets/icons/alert.svg';
import checkIcon from '@/assets/icons/check.svg';
import eyeIcon from '@/assets/icons/eye.svg';
import eyeOffIcon from '@/assets/icons/eye-off.svg';
import googleIcon from '@/assets/icons/google.svg';
import lockIcon from '@/assets/icons/lock.svg';
import mailIcon from '@/assets/icons/mail.svg';
import { Button } from '@/components/ui/Button';
import { Checkbox } from '@/components/ui/Checkbox';
import { TextField } from '@/components/ui/TextField';
import { useLogin } from '@/hooks/useLogin';
import { Role } from '@/lib/enums';
import { saveSession } from '@/lib/session';
import { validateLogin, type LoginFieldErrors } from '@/lib/validation';

/* ── Demo role fixtures ──────────────────────────────────────────── */
const DEMO_ROLES: { role: Role; label: string; name: string; dashboardPath: string }[] = [
  { role: Role.Ceo, label: 'CEO', name: 'Sawera Ghaffar', dashboardPath: '/app/dashboard' },
  { role: Role.Cto, label: 'CTO', name: 'Tariq Mehmood', dashboardPath: '/app/cto-dashboard' },
  { role: Role.Cfo, label: 'CFO', name: 'Omar Siddiqui', dashboardPath: '/app/cfo-dashboard' },
  { role: Role.Coo, label: 'COO', name: 'Nadia Khan', dashboardPath: '/app/coo-dashboard' },
  { role: Role.Hr, label: 'HR', name: 'Hina Shah', dashboardPath: '/app/hr-dashboard' },
  { role: Role.Manager, label: 'Manager', name: 'Ava Chen', dashboardPath: '/app/manager-dashboard' },
  { role: Role.Employee, label: 'Employee', name: 'Bilal Ahmed', dashboardPath: '/app/employee-dashboard' },
];

export function LoginForm() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const resetSuccess = searchParams.get('reset') === 'success';
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [keepSignedIn, setKeepSignedIn] = useState(true);
  const [fieldErrors, setFieldErrors] = useState<LoginFieldErrors>({});
  const [googleNotice, setGoogleNotice] = useState(false);
  const login = useLogin();

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setGoogleNotice(false);
    const errors = validateLogin(email, password);
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) return;
    login.mutate({ email: email.trim(), password, keepSignedIn });
  }

  function handleDemoLogin(roleEntry: (typeof DEMO_ROLES)[number]) {
    saveSession(
      {
        accessToken: `demo-${roleEntry.role}-token`,
        refreshToken: null,
        user: {
          id: `demo-${roleEntry.role}`,
          name: roleEntry.name,
          email: `${roleEntry.role}@demo.ems`,
          role: roleEntry.role,
        },
      },
      true,
    );
    navigate(roleEntry.dashboardPath, { replace: true });
  }

  return (
    <div className="w-full max-w-[546px]">
      <p className="mb-[18px] flex items-center gap-2.5 text-[13px] font-semibold tracking-[0.04em] text-accent uppercase">
        <span aria-hidden="true" className="size-[7px] rounded-full bg-accent" />
        Your workspace awaits
      </p>
      <h1 className="text-[32px] leading-[1.2] font-bold tracking-[-0.02em] text-ink">
        Sign in to EMS
      </h1>
      <p className="mt-2 max-w-[300px] text-sm leading-5 text-ink-body">
        Use your work account to continue to your company workspace.
      </p>

      <form onSubmit={handleSubmit} noValidate className="mt-[30px]">
        {resetSuccess && (
          <div
            role="status"
            className="mb-5 flex items-start gap-2.5 rounded-xl bg-success-bg px-4 py-3 text-sm text-success-text"
          >
            <img src={checkIcon} alt="" aria-hidden="true" className="mt-0.5 size-5 shrink-0" />
            <span>
              Password changed. Sign in again.
              <button
                type="button"
                onClick={() => {
                  const next = new URLSearchParams(searchParams);
                  next.delete('reset');
                  setSearchParams(next, { replace: true });
                }}
                className="ml-2 font-semibold underline underline-offset-2 hover:no-underline"
                aria-label="Dismiss password reset confirmation"
              >
                Dismiss
              </button>
            </span>
          </div>
        )}
        <TextField
          label="Work email"
          icon={mailIcon}
          type="email"
          name="email"
          autoComplete="username"
          placeholder="name@company.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          error={fieldErrors.email}
        />
        <TextField
          className="mt-6"
          label="Password"
          icon={lockIcon}
          type={showPassword ? 'text' : 'password'}
          name="password"
          autoComplete="current-password"
          placeholder="Enter your password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          error={fieldErrors.password}
          trailing={
            <button
              type="button"
              onClick={() => setShowPassword((v) => !v)}
              aria-label={showPassword ? 'Hide password' : 'Show password'}
              aria-pressed={showPassword}
              className="flex size-8 cursor-pointer items-center justify-center rounded-md"
            >
              <img src={showPassword ? eyeOffIcon : eyeIcon} alt="" className="size-[22px]" />
            </button>
          }
        />

        <div className="mt-7 flex items-center justify-between">
          <Checkbox
            label="Keep me signed in"
            checked={keepSignedIn}
            onChange={(e) => setKeepSignedIn(e.target.checked)}
          />
          <Link
            to="/forgot-password"
            className="text-[13px] font-semibold text-accent hover:underline"
          >
            Forgot password?
          </Link>
        </div>

        {login.isError && (
          <div
            role="alert"
            className="mt-5 flex items-start gap-2.5 rounded-xl bg-danger-soft px-4 py-3 text-sm text-danger"
          >
            <img src={alertIcon} alt="" aria-hidden="true" className="mt-0.5 size-5 shrink-0" />
            <span>{toErrorMessage(login.error)}</span>
          </div>
        )}

        <Button
          type="submit"
          className="mt-[30px]"
          isLoading={login.isPending}
          loadingLabel="Signing in..."
        >
          Sign in
        </Button>
      </form>

      <div className="my-6 flex items-center gap-3" role="separator" aria-label="or">
        <span className="h-px flex-1 bg-line-soft" />
        <span className="text-xs text-ink-body uppercase">Or continue with</span>
        <span className="h-px flex-1 bg-line-soft" />
      </div>

      <Button
        type="button"
        variant="outline"
        leadingIcon={<img src={googleIcon} alt="" aria-hidden="true" className="size-5" />}
        onClick={() => setGoogleNotice(true)}
      >
        Continue with Google
      </Button>
      {googleNotice && (
        <p role="status" className="mt-3 text-center text-[13px] text-ink-muted">
          Google sign-in will be available once the EMS backend is connected.
        </p>
      )}

      <p className="mt-4 text-center text-sm text-ink-body">
        New to EMS?{' '}
        <Link
          to="/register"
          className="font-semibold text-accent underline decoration-accent/30 underline-offset-4 hover:decoration-accent"
        >
          Create a company account
        </Link>
      </p>

      {/* ── Frontend Demo Role Selector ─────────────────────────────── */}
      <div
        className="mt-8 rounded-2xl border border-dashed border-line-soft bg-panel-from px-5 py-4"
        role="region"
        aria-label="Demo role selector"
      >
        <p className="mb-3 text-center text-[11px] font-bold tracking-[0.07em] text-ink-muted uppercase">
          ⚡ Frontend demo — select a role
        </p>
        <div className="grid grid-cols-4 gap-2">
          {DEMO_ROLES.map((roleEntry) => (
            <button
              key={roleEntry.role}
              type="button"
              id={`demo-login-${roleEntry.role}`}
              onClick={() => handleDemoLogin(roleEntry)}
              className="flex flex-col items-center gap-1 rounded-xl border border-line-soft bg-white px-2 py-2.5 text-center text-[11px] font-semibold text-ink shadow-chip transition-all hover:border-accent hover:bg-accent-soft hover:text-accent hover:shadow-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
            >
              <span className="text-base leading-none">
                {roleEntry.role === 'ceo' ? '👔' : roleEntry.role === 'cto' ? '💻' : roleEntry.role === 'cfo' ? '💰' : roleEntry.role === 'coo' ? '⚙️' : roleEntry.role === 'hr' ? '🧑‍💼' : roleEntry.role === 'manager' ? '📋' : '👤'}
              </span>
              {roleEntry.label}
            </button>
          ))}
        </div>
        <p className="mt-2.5 text-center text-[10px] text-ink-muted">
          Demo only — no real auth. Each role opens its dashboard.
        </p>
      </div>
    </div>
  );
}
