import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { toErrorMessage } from '@/api/errors';
import { signupRequest } from '@/api/auth';
import alertIcon from '@/assets/icons/alert.svg';
import eyeIcon from '@/assets/icons/eye.svg';
import eyeOffIcon from '@/assets/icons/eye-off.svg';
import googleIcon from '@/assets/icons/google.svg';
import lockIcon from '@/assets/icons/lock.svg';
import mailIcon from '@/assets/icons/mail.svg';
import { Button } from '@/components/ui/Button';
import { Checkbox } from '@/components/ui/Checkbox';
import { TextField } from '@/components/ui/TextField';
import { hasErrors, validateRegister, type RegisterFieldErrors } from '@/lib/validation';

const BUILD_ICON =
  'data:image/svg+xml;utf8,' +
  encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#5d6b8f" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18Z"/><path d="M6 12H4a2 2 0 0 0-2 2v8h4"/><path d="M18 9h2a2 2 0 0 1 2 2v11h-4"/><path d="M10 6h4"/><path d="M10 10h4"/><path d="M10 14h4"/><path d="M10 18h4"/></svg>`,
  );

export function RegisterForm() {
  const navigate = useNavigate();
  const [companyName, setCompanyName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [agreed, setAgreed] = useState(false);
  const [errors, setErrors] = useState<RegisterFieldErrors>({});
  const [serverError, setServerError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setServerError(null);
    const next = validateRegister({ companyName, email, password, agreedToTerms: agreed });
    setErrors(next);
    if (hasErrors(next)) return;
    setPending(true);
    try {
      await signupRequest({ companyName: companyName.trim(), email: email.trim(), password });
      navigate('/company-setup', { replace: true });
    } catch (error) {
      setServerError(toErrorMessage(error));
    } finally {
      setPending(false);
    }
  }

  return (
    <div>
      <h1 className="text-[26px] leading-8 font-extrabold tracking-tight text-ink sm:text-[28px]">Create your company</h1>
      <p className="mt-1 text-sm text-ink-body">Start your EMS workspace in a few simple steps.</p>

      {/* 3-segment progress indicator (Step 1: Account of 3 onboarding steps) */}
      <div className="mt-4 flex items-center gap-2" role="progressbar" aria-valuenow={1} aria-valuemin={1} aria-valuemax={3} aria-label="Step 1 of 3: Account">
        <div className="h-1 flex-1 rounded-full bg-primary" />
        <div className="h-1 flex-1 rounded-full bg-line-soft" />
        <div className="h-1 flex-1 rounded-full bg-line-soft" />
      </div>

      <form onSubmit={handleSubmit} noValidate className="mt-6">
        <TextField
          label="Company name"
          icon={BUILD_ICON}
          name="companyName"
          autoComplete="organization"
          placeholder="e.g. Northstar Studio"
          value={companyName}
          onChange={(event) => setCompanyName(event.target.value)}
          error={errors.companyName}
        />
        <TextField
          className="mt-5"
          label="Work email"
          icon={mailIcon}
          type="email"
          name="email"
          autoComplete="email"
          placeholder="you@company.com"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          error={errors.email}
        />
        <div className="mt-5">
          <TextField
            label="Create password"
            icon={lockIcon}
            type={showPassword ? 'text' : 'password'}
            name="new-password"
            autoComplete="new-password"
            placeholder="Create a strong password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            error={errors.password}
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
          <p className="mt-2 text-xs text-ink-muted">Use at least 8 characters with a mix of letters and numbers.</p>
        </div>

        <div className="mt-5">
          <Checkbox
            checked={agreed}
            onChange={(event) => setAgreed(event.target.checked)}
            aria-describedby={errors.terms ? 'register-terms-error' : undefined}
            label={
              <span className="text-[13px] text-ink-body">
                I agree to the{' '}
                <Link to="/login" className="font-semibold text-accent hover:underline">
                  Terms of Service
                </Link>{' '}
                and{' '}
                <Link to="/login" className="font-semibold text-accent hover:underline">
                  Privacy Policy
                </Link>
              </span>
            }
          />
          {errors.terms && (
            <p id="register-terms-error" role="alert" className="mt-2 text-[13px] font-medium text-danger">
              {errors.terms}
            </p>
          )}
        </div>

        {serverError && (
          <div role="alert" className="mt-5 flex items-start gap-2.5 rounded-xl bg-danger-soft px-4 py-3 text-sm text-danger">
            <img src={alertIcon} alt="" aria-hidden="true" className="mt-0.5 size-5 shrink-0" />
            <span>{serverError}</span>
          </div>
        )}

        <Button type="submit" className="mt-6" isLoading={pending} loadingLabel="Creating account...">
          Create company account
        </Button>
      </form>

      <div className="my-5 flex items-center gap-3" role="separator" aria-label="or">
        <span className="h-px flex-1 bg-line-soft" />
        <span className="text-[11px] text-ink-muted uppercase">Or sign up with</span>
        <span className="h-px flex-1 bg-line-soft" />
      </div>

      <Button
        type="button"
        variant="outline"
        leadingIcon={<img src={googleIcon} alt="" aria-hidden="true" className="size-5" />}
        onClick={() => setServerError('Google sign-up will be available once the EMS backend is connected.')}
      >
        Continue with Google
      </Button>

      <p className="mt-5 text-center text-sm text-ink-body">
        Already have an EMS account?{' '}
        <Link to="/login" className="font-semibold text-accent hover:underline">
          Sign in
        </Link>
      </p>
    </div>
  );
}
