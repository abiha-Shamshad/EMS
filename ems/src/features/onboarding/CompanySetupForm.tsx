import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { toErrorMessage } from '@/api/errors';
import { companySetupRequest, getDemoOrgName } from '@/api/auth';
import { COMPANY_SIZE_OPTIONS, INDUSTRY_OPTIONS, TIME_ZONE_OPTIONS } from '@/demo/fixtures';
import alertIcon from '@/assets/icons/alert.svg';
import { ArrowLeftIcon } from '@/components/layout/icons';
import { Button } from '@/components/ui/Button';
import { Select, SelectPlaceholder } from '@/components/ui/Select';
import { TextField } from '@/components/ui/TextField';
import { Textarea } from '@/components/ui/Textarea';
import { hasErrors, MAX_ABOUT_LENGTH, validateCompanySetup, type CompanySetupFieldErrors } from '@/lib/validation';

const BUILD_ICON =
  'data:image/svg+xml;utf8,' +
  encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#5d6b8f" stroke-width="1.8" stroke-linecap="round"><rect x="5" y="8" width="14" height="12" rx="2"/><path d="M9 8V6a3 3 0 0 1 6 0v2M9 13h6"/></svg>`,
  );

export function CompanySetupForm() {
  const navigate = useNavigate();
  const [companyName, setCompanyName] = useState(() => getDemoOrgName() ?? '');
  const [industry, setIndustry] = useState('');
  const [companySize, setCompanySize] = useState('');
  const [website, setWebsite] = useState('');
  const [timeZone, setTimeZone] = useState('Asia/Karachi');
  const [about, setAbout] = useState('');
  const [errors, setErrors] = useState<CompanySetupFieldErrors>({});
  const [serverError, setServerError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setServerError(null);
    const next = validateCompanySetup({
      companyName,
      industry,
      companySize,
      companyWebsite: website,
      timeZone,
      about,
    });
    setErrors(next);
    if (hasErrors(next)) return;
    setPending(true);
    try {
      await companySetupRequest({
        companyName: companyName.trim(),
        industry,
        companySize,
        companyWebsite: website.trim(),
        timeZone,
        about: about.trim(),
      });
      navigate('/invite-team', { replace: true });
    } catch (error) {
      setServerError(toErrorMessage(error));
    } finally {
      setPending(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate>
      <div>
        <h2 className="text-lg font-extrabold text-ink">Company information</h2>
        <p className="mt-0.5 text-[13px] text-ink-muted">Fields marked with * are required.</p>
      </div>

      <TextField
        className="mt-5"
        label="Company name *"
        icon={BUILD_ICON}
        name="companyName"
        autoComplete="organization"
        placeholder="e.g. Acme Technologies"
        value={companyName}
        onChange={(event) => setCompanyName(event.target.value)}
        error={errors.companyName}
      />

      <div className="mt-5 grid gap-5 sm:grid-cols-2">
        <Select label="Industry *" value={industry} onChange={(event) => setIndustry(event.target.value)} error={errors.industry}>
          <SelectPlaceholder>Select your industry</SelectPlaceholder>
          {INDUSTRY_OPTIONS.map((option) => (
            <option key={option} value={option}>{option}</option>
          ))}
        </Select>
        <Select label="Company size *" value={companySize} onChange={(event) => setCompanySize(event.target.value)} error={errors.companySize}>
          <SelectPlaceholder>Select employee range</SelectPlaceholder>
          {COMPANY_SIZE_OPTIONS.map((option) => (
            <option key={option} value={option}>{option}</option>
          ))}
        </Select>
      </div>

      <div className="mt-5 grid gap-5 sm:grid-cols-2">
        <TextField
          label="Company website"
          icon={BUILD_ICON}
          type="url"
          name="companyWebsite"
          autoComplete="url"
          placeholder="https://company.com"
          value={website}
          onChange={(event) => setWebsite(event.target.value)}
          error={errors.companyWebsite}
        />
        <Select label="Time zone *" value={timeZone} onChange={(event) => setTimeZone(event.target.value)} error={errors.timeZone}>
          <SelectPlaceholder>Select time zone</SelectPlaceholder>
          {TIME_ZONE_OPTIONS.map((option) => (
            <option key={option} value={option}>{option}</option>
          ))}
        </Select>
      </div>

      <Textarea
        className="mt-5"
        label="What does your company do?"
        name="about"
        placeholder="Briefly describe your company or team..."
        value={about}
        maxLength={MAX_ABOUT_LENGTH}
        showCount={false}
        onChange={(event) => setAbout(event.target.value)}
        error={errors.about}
      />

      {serverError && (
        <div role="alert" className="mt-5 flex items-start gap-2.5 rounded-xl bg-danger-soft px-4 py-3 text-sm text-danger">
          <img src={alertIcon} alt="" aria-hidden="true" className="mt-0.5 size-5 shrink-0" />
          <span>{serverError}</span>
        </div>
      )}

      <div className="mt-7 flex flex-col-reverse gap-3 sm:flex-row sm:items-center sm:justify-between">
        <button
          type="button"
          onClick={() => navigate('/register')}
          className="flex h-12 cursor-pointer items-center justify-center gap-2 rounded-xl px-5 text-sm font-bold text-ink transition-colors hover:bg-panel-from"
        >
          <ArrowLeftIcon className="size-4" />
          Back
        </button>
        <div className="sm:w-64">
          <Button type="submit" isLoading={pending} loadingLabel="Saving...">
            Continue to invite team
          </Button>
        </div>
      </div>
    </form>
  );
}
