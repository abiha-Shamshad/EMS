import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { toErrorMessage } from '@/api/errors';
import { inviteTeamRequest, type InviteTeamResult } from '@/api/auth';
import alertIcon from '@/assets/icons/alert.svg';
import checkIcon from '@/assets/icons/check.svg';
import mailIcon from '@/assets/icons/mail.svg';
import { ArrowLeftIcon } from '@/components/layout/icons';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { TeamIllustration } from '@/components/ui/Illustrations';
import { Modal } from '@/components/ui/Modal';
import { Select, SelectPlaceholder } from '@/components/ui/Select';
import { TextField } from '@/components/ui/TextField';
import { Textarea } from '@/components/ui/Textarea';
import { useToast } from '@/components/ui/Toast';
import { Role } from '@/lib/enums';
import { INVITE_ROLE_OPTIONS } from '@/lib/labels';
import { getSession, saveSession } from '@/lib/session';
import {
  inviteHasErrors,
  MAX_INVITE_MESSAGE_LENGTH,
  MAX_INVITE_ROWS,
  validateInvites,
  type InviteFieldErrors,
  type InviteRow,
} from '@/lib/validation';

function newRow(index: number): InviteRow {
  return { id: `invite-${Date.now()}-${index}-${Math.random().toString(36).slice(2, 7)}`, email: '', role: 'employee' };
}

const EMPTY_ERRORS: InviteFieldErrors = { rows: [], message: undefined, form: undefined };

export function InviteTeamForm() {
  const navigate = useNavigate();
  const toast = useToast();
  const [rows, setRows] = useState<InviteRow[]>([newRow(0), newRow(1)]);
  const [message, setMessage] = useState('Hi! Join our company workspace on EMS to collaborate with the team.');
  const [errors, setErrors] = useState<InviteFieldErrors>(EMPTY_ERRORS);
  const [serverError, setServerError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [result, setResult] = useState<InviteTeamResult | null>(null);

  function updateRow(id: string, patch: Partial<InviteRow>) {
    setRows((prev) => prev.map((row) => (row.id === id ? { ...row, ...patch } : row)));
  }

  function removeRow(id: string) {
    if (rows.length <= 1) return;
    setRows((prev) => prev.filter((row) => row.id !== id));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setServerError(null);
    const next = validateInvites(rows, message);
    setErrors(next);
    if (inviteHasErrors(next)) return;
    setPending(true);
    try {
      const data = await inviteTeamRequest({ rows, message: message.trim() });
      setResult(data);
      toast.notify(`${data.results.length} invitation${data.results.length === 1 ? '' : 's'} created. Share the links to finish onboarding.`);
    } catch (error) {
      setServerError(toErrorMessage(error));
    } finally {
      setPending(false);
    }
  }

  function copyLink(link: string) {
    void navigator.clipboard
      ?.writeText(link)
      .then(() => toast.notify('Invite link copied.'))
      .catch(() => toast.notify('Copy failed. Select the link manually.', 'error'));
  }

  function finishOnboarding() {
    if (!getSession()) {
      saveSession(
        {
          accessToken: 'demo-signup-ceo-token',
          refreshToken: null,
          user: {
            id: 'demo-registered-user',
            name: 'Company Founder',
            email: 'founder@company.com',
            role: Role.Ceo,
          },
        },
        true,
      );
    }
    navigate('/app/dashboard', { replace: true });
  }

  return (
    <form onSubmit={handleSubmit} noValidate>
      <div>
        <h2 className="text-lg font-extrabold text-ink">Invite team members</h2>
        <p className="mt-0.5 text-[13px] text-ink-muted">Add work email addresses and assign the right access level.</p>
      </div>

      <div className="mt-5 hidden grid-cols-[1fr_200px_32px] gap-3 text-[11px] font-bold tracking-[0.06em] text-ink-muted uppercase sm:grid" aria-hidden="true">
        <span>Work email</span>
        <span>Role</span>
        <span />
      </div>

      <ul className="mt-2 space-y-3 sm:mt-2" aria-label="Invitations">
        {rows.map((row, index) => (
          <li key={row.id} className="grid gap-3 sm:grid-cols-[1fr_200px_32px] sm:items-start">
            <TextField
              label={`Work email ${index + 1}`}
              hideLabel
              icon={mailIcon}
              type="email"
              name={`invite-email-${index}`}
              autoComplete="email"
              placeholder={index === 0 ? 'colleague@company.com' : 'another@company.com'}
              value={row.email}
              onChange={(event) => updateRow(row.id, { email: event.target.value })}
              error={errors.rows[index]?.email}
              aria-label={`Work email ${index + 1}`}
            />
            <Select
              label={`Role for invite ${index + 1}`}
              hideLabel
              value={row.role}
              onChange={(event) => updateRow(row.id, { role: event.target.value })}
              aria-label={`Role for invite ${index + 1}`}
            >
              <SelectPlaceholder>Select role</SelectPlaceholder>
              {INVITE_ROLE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </Select>
            <button
              type="button"
              onClick={() => removeRow(row.id)}
              disabled={rows.length <= 1}
              aria-label={`Remove invite ${index + 1}`}
              className="flex size-8 cursor-pointer items-center justify-center rounded-lg text-ink-muted transition-colors hover:bg-danger-soft hover:text-danger disabled:cursor-not-allowed disabled:opacity-30"
            >
              ✕
            </button>
          </li>
        ))}
      </ul>

      <div className="mt-4 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <button
          type="button"
          onClick={() => rows.length < MAX_INVITE_ROWS && setRows((prev) => [...prev, newRow(prev.length)])}
          disabled={rows.length >= MAX_INVITE_ROWS}
          className="flex w-fit cursor-pointer items-center gap-1.5 text-sm font-bold text-primary hover:underline disabled:cursor-not-allowed disabled:opacity-50 disabled:no-underline"
        >
          <span aria-hidden="true" className="flex size-5 items-center justify-center rounded-full bg-info-bg text-primary">+</span>
          Add another email
        </button>
        <p className="text-xs text-ink-muted">You can invite more people later</p>
      </div>

      {errors.form && (
        <p role="alert" className="mt-3 text-[13px] font-medium text-danger">{errors.form}</p>
      )}

      <Textarea
        className="mt-5"
        label="Personal invitation message"
        optionalTag
        name="inviteMessage"
        placeholder="Hi! Join our company workspace on EMS to collaborate with the team."
        value={message}
        maxLength={MAX_INVITE_MESSAGE_LENGTH}
        showCount
        onChange={(event) => setMessage(event.target.value)}
        error={errors.message}
      />

      <p className="mt-4 flex items-start gap-2 rounded-xl bg-panel-from px-4 py-3 text-xs text-ink-body">
        <span aria-hidden="true" className="flex size-5 shrink-0 items-center justify-center rounded-full bg-info-bg text-[11px] font-bold text-info-text">i</span>
        Invited teammates will receive an email with a secure link to join EMS.
      </p>

      {serverError && (
        <div role="alert" className="mt-4 flex items-start gap-2.5 rounded-xl bg-danger-soft px-4 py-3 text-sm text-danger">
          <img src={alertIcon} alt="" aria-hidden="true" className="mt-0.5 size-5 shrink-0" />
          <span>{serverError}</span>
        </div>
      )}

      <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:items-center sm:justify-between">
        <button
          type="button"
          onClick={() => navigate('/company-setup')}
          className="flex h-12 cursor-pointer items-center justify-center gap-2 rounded-xl px-5 text-sm font-bold text-ink transition-colors hover:bg-panel-from"
        >
          <ArrowLeftIcon className="size-4" />
          Back
        </button>
        <div className="flex flex-col-reverse gap-3 sm:flex-row">
          <Button type="button" variant="outline" className="sm:w-44" onClick={finishOnboarding}>
            Skip for now
          </Button>
          <div className="sm:w-44">
            <Button type="submit" isLoading={pending} loadingLabel="Sending...">
              Send Invitation
            </Button>
          </div>
        </div>
      </div>

      <Modal
        open={result !== null}
        title="Invitations created"
        description="Email delivery is not configured yet, so share these secure links with your team."
        onClose={() => setResult(null)}
      >
        <ul className="space-y-3">
          {(result?.inviteLinks ?? []).map((item) => (
            <li key={item.email} className="rounded-xl border border-line-soft p-3">
              <p className="flex items-center gap-2 text-sm font-bold text-ink">
                <img src={checkIcon} alt="" aria-hidden="true" className="size-4" />
                {item.email}
              </p>
              <p className="mt-1 truncate text-xs text-ink-muted">{item.link}</p>
              <div className="mt-2 w-32">
                <Button type="button" variant="outline" onClick={() => copyLink(item.link)}>
                  Copy link
                </Button>
              </div>
            </li>
          ))}
        </ul>
        <div className="mt-4">
          <Button type="button" onClick={finishOnboarding}>
            Go to dashboard
          </Button>
        </div>
      </Modal>
    </form>
  );
}

export function InviteAside() {
  return (
    <div>
      <span aria-hidden="true" className="mx-auto flex size-20 items-center justify-center rounded-full bg-info-bg text-primary">
        <TeamIllustration className="size-10" />
      </span>
      <h2 className="mt-4 text-center text-lg font-extrabold text-ink sm:text-left">Better work, together</h2>
      <p className="mt-1 text-center text-[13px] text-ink-body sm:text-left">
        Invite your colleagues to make the most of your connected workspace.
      </p>
      <ul className="mt-5 space-y-3 border-t border-line-soft pt-5">
        {[
          { title: 'Choose the right role', text: 'Give each teammate relevant access' },
          { title: 'Secure invitations', text: 'Each person joins with their own link' },
        ].map((item) => (
          <li key={item.title} className="flex gap-2.5">
            <span aria-hidden="true" className="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full bg-success-bg text-[11px] font-bold text-success-text">✓</span>
            <div>
              <p className="text-[13px] font-bold text-ink">{item.title}</p>
              <p className="text-xs text-ink-muted">{item.text}</p>
            </div>
          </li>
        ))}
      </ul>
      <div className="mt-5 rounded-2xl bg-panel-from p-4">
        <p className="text-[13px] font-bold text-ink">Suggested roles</p>
        <p className="mt-2 flex flex-wrap gap-1.5">
          <Badge tone="info">Employee</Badge>
          <Badge tone="success">HR</Badge>
          <Badge tone="warning">Manager</Badge>
        </p>
        <p className="mt-2 text-xs text-ink-muted">Permissions can be changed later.</p>
      </div>
    </div>
  );
}
