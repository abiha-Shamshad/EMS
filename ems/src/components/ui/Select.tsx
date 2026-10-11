import { useId, type ReactNode, type SelectHTMLAttributes } from 'react';

interface SelectProps extends Omit<SelectHTMLAttributes<HTMLSelectElement>, 'id'> {
  label: string;
  error?: string;
  hint?: string;
  optionalTag?: boolean;
  /** Visually hide the label (still announced by screen readers). */
  hideLabel?: boolean;
}

export function Select({ label, error, hint, optionalTag, hideLabel = false, className = '', children, ...rest }: SelectProps) {
  const id = useId();
  const errorId = `${id}-error`;
  const hintId = `${id}-hint`;
  const describedBy = [error ? errorId : null, hint ? hintId : null].filter(Boolean).join(' ') || undefined;
  return (
    <div className={className}>
      <label htmlFor={id} className={hideLabel ? 'sr-only' : 'mb-2 block text-[13px] font-semibold text-ink'}>
        {label}{' '}
        {optionalTag && <span className="font-normal text-ink-muted">(optional)</span>}
      </label>
      <div className="relative">
        <select
          {...rest}
          id={id}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
          className={`h-14 w-full appearance-none rounded-2xl border bg-white pr-12 pl-5 text-sm text-ink transition-colors focus:border-accent focus:ring-4 focus:ring-accent/15 focus:outline-none disabled:bg-search-bg disabled:text-ink-muted ${
            error ? 'border-danger' : 'border-line'
          } ${rest.value === '' ? 'text-placeholder' : ''}`}
        >
          {children}
        </select>
        <svg
          aria-hidden="true"
          viewBox="0 0 20 20"
          className="pointer-events-none absolute top-1/2 right-5 size-5 -translate-y-1/2 text-ink-muted"
          fill="none"
          stroke="currentColor"
          strokeWidth={1.8}
        >
          <path d="m5 7.5 5 5 5-5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>
      {hint && !error && (
        <p id={hintId} className="mt-2 text-[13px] text-ink-muted">
          {hint}
        </p>
      )}
      {error && (
        <p id={errorId} role="alert" className="mt-2 text-[13px] font-medium text-danger">
          {error}
        </p>
      )}
    </div>
  );
}

export function SelectPlaceholder({ children }: { children: ReactNode }) {
  return (
    <option value="" disabled>
      {children}
    </option>
  );
}
