import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import checkIcon from '@/assets/icons/check.svg';
import lockIcon from '@/assets/icons/lock.svg';
import mailIcon from '@/assets/icons/mail.svg';
import { Button } from '@/components/ui/Button';
import { TextField } from '@/components/ui/TextField';
import { forgotPasswordRequest } from '@/api/auth';
import { validateForgotPassword, type ForgotPasswordFieldErrors } from '@/lib/validation';

export function ForgotPasswordForm() {
  const [email, setEmail] = useState('');
  const [errors, setErrors] = useState<ForgotPasswordFieldErrors>({});
  const [pending, setPending] = useState(false);
  const [sent, setSent] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const next = validateForgotPassword(email);
    setErrors(next);
    if (next.email) return;
    setPending(true);
    try {
      await forgotPasswordRequest(email.trim());
      setSent(true);
    } finally {
      setPending(false);
    }
  }

  if (sent) {
    return (
      <div className="text-center">
        <span aria-hidden="true" className="mx-auto flex size-14 items-center justify-center rounded-full bg-success-bg">
          <img src={checkIcon} alt="" className="size-7" />
        </span>
        <h2 className="mt-4 text-xl font-extrabold text-ink">Check your inbox</h2>
        <p className="mx-auto mt-2 max-w-[320px] text-sm text-ink-body">
          If {email.trim()} has an account, a secure reset link is on its way. The link expires after a short time.
        </p>
        <p className="mt-6">
          <Link to="/login" className="text-sm font-bold text-accent hover:underline">
            ← Back to sign in
          </Link>
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} noValidate>
      <TextField
        label="Work email address"
        icon={mailIcon}
        type="email"
        name="email"
        autoComplete="email"
        placeholder="name@company.com"
        value={email}
        onChange={(event) => setEmail(event.target.value)}
        error={errors.email}
      />

      <Button type="submit" className="mt-6" isLoading={pending} loadingLabel="Sending link...">
        <>
          Send reset link
          <span aria-hidden="true">→</span>
        </>
      </Button>

      <p className="mt-5 flex items-start justify-center gap-2 text-center text-xs text-ink-muted">
        <img src={lockIcon} alt="" aria-hidden="true" className="size-4 shrink-0" />
        For your security, the reset link will expire after a short time.
      </p>

      <p className="mt-6 text-center">
        <Link to="/login" className="text-sm font-bold text-accent hover:underline">
          ← Back to sign in
        </Link>
      </p>
    </form>
  );
}
