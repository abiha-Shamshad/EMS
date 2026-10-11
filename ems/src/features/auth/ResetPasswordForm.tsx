import { useState, type FormEvent } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { toErrorMessage } from '@/api/errors';
import { resetPasswordRequest } from '@/api/auth';
import alertIcon from '@/assets/icons/alert.svg';
import eyeIcon from '@/assets/icons/eye.svg';
import eyeOffIcon from '@/assets/icons/eye-off.svg';
import lockIcon from '@/assets/icons/lock.svg';
import { Button } from '@/components/ui/Button';
import { TextField } from '@/components/ui/TextField';
import {
  PASSWORD_STRENGTH_LABELS,
  passwordChecklist,
  passwordStrength,
  validateResetPassword,
  type ResetPasswordFieldErrors,
} from '@/lib/validation';

const CHECKS = [
  { key: 'length', label: 'At least 8 characters' },
  { key: 'upper', label: 'One uppercase letter' },
  { key: 'lower', label: 'One lowercase letter' },
  { key: 'number', label: 'One number' },
  { key: 'special', label: 'One special character' },
] as const;

const STRENGTH_TONE: Record<string, string> = {
  weak: 'text-danger',
  medium: 'text-warning-text',
  strong: 'text-success-text',
  'very-strong': 'text-success-text',
};

export function ResetPasswordForm() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get('token') ?? 'demo-token';
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [errors, setErrors] = useState<ResetPasswordFieldErrors>({});
  const [serverError, setServerError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const checklist = passwordChecklist(password);
  const strength = passwordStrength(password);
  const filledBars = strength === 'weak' ? 1 : strength === 'medium' ? 2 : strength === 'strong' ? 3 : 4;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setServerError(null);
    const next = validateResetPassword(password, confirm);
    setErrors(next);
    if (next.password || next.confirmPassword) return;
    setPending(true);
    try {
      await resetPasswordRequest({ token, newPassword: password });
      navigate('/login?reset=success', { replace: true });
    } catch (error) {
      setServerError(toErrorMessage(error));
    } finally {
      setPending(false);
    }
  }

  const eyeButton = (shown: boolean, onToggle: () => void, label: string) => (
    <button
      type="button"
      onClick={onToggle}
      aria-label={shown ? `Hide ${label}` : `Show ${label}`}
      aria-pressed={shown}
      className="flex size-8 cursor-pointer items-center justify-center rounded-md"
    >
      <img src={shown ? eyeOffIcon : eyeIcon} alt="" className="size-[22px]" />
    </button>
  );

  return (
    <form onSubmit={handleSubmit} noValidate>
      <TextField
        label="New Password"
        icon={lockIcon}
        type={showPassword ? 'text' : 'password'}
        name="new-password"
        autoComplete="new-password"
        placeholder="Enter new password"
        value={password}
        onChange={(event) => setPassword(event.target.value)}
        error={errors.password}
        trailing={eyeButton(showPassword, () => setShowPassword((v) => !v), 'password')}
      />

      {password.length > 0 && (
        <div className="mt-3">
          <div className="flex items-center gap-1.5" role="img" aria-label={`Password strength: ${PASSWORD_STRENGTH_LABELS[strength]}`}>
            {[1, 2, 3, 4].map((bar) => (
              <span
                key={bar}
                aria-hidden="true"
                className={`h-1.5 flex-1 rounded-full ${bar <= filledBars ? 'bg-primary' : 'bg-line-soft'}`}
              />
            ))}
            <span className={`ml-2 text-[11px] font-bold ${STRENGTH_TONE[strength]}`}>
              {PASSWORD_STRENGTH_LABELS[strength]}
            </span>
          </div>
        </div>
      )}

      <div className="mt-4">
        <p className="text-[13px] font-bold text-ink">Password must include:</p>
        <ul className="mt-2 space-y-1.5">
          {CHECKS.map((check) => {
            const met = checklist[check.key];
            return (
              <li key={check.key} className="flex items-center gap-2 text-[13px] text-ink-body">
                <span
                  aria-hidden="true"
                  className={`flex size-[18px] items-center justify-center rounded-full text-[11px] font-bold ${
                    met ? 'bg-success text-white' : 'bg-search-bg text-ink-muted'
                  }`}
                >
                  {met ? '✓' : '·'}
                </span>
                {check.label}
              </li>
            );
          })}
        </ul>
      </div>

      <TextField
        className="mt-5"
        label="Confirm New Password"
        icon={lockIcon}
        type={showConfirm ? 'text' : 'password'}
        name="confirm-password"
        autoComplete="new-password"
        placeholder="Confirm new password"
        value={confirm}
        onChange={(event) => setConfirm(event.target.value)}
        error={errors.confirmPassword}
        trailing={eyeButton(showConfirm, () => setShowConfirm((v) => !v), 'confirmation')}
      />

      {serverError && (
        <div role="alert" className="mt-5 flex items-start gap-2.5 rounded-xl bg-danger-soft px-4 py-3 text-sm text-danger">
          <img src={alertIcon} alt="" aria-hidden="true" className="mt-0.5 size-5 shrink-0" />
          <span>{serverError}</span>
        </div>
      )}

      <Button type="submit" className="mt-6" isLoading={pending} loadingLabel="Resetting...">
        <>
          Reset Password
          <span aria-hidden="true">→</span>
        </>
      </Button>

      <p className="mt-5 text-center text-[13px] text-ink-muted">
        Remember your password?{' '}
        <Link to="/login" className="font-bold text-accent hover:underline">
          Back to Sign In
        </Link>
      </p>
    </form>
  );
}
