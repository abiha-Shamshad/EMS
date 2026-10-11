import { useId, type InputHTMLAttributes, type ReactNode } from 'react';

interface TextFieldProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'id'> {
  label: string;
  /** Path of an SVG from assets/icons, shown at the left of the field. */
  icon: string;
  error?: string;
  trailing?: ReactNode;
  /** Visually hide the label (still announced by screen readers). */
  hideLabel?: boolean;
}

export function TextField({
  label,
  icon,
  error,
  trailing,
  hideLabel = false,
  className = '',
  ...inputProps
}: TextFieldProps) {
  const id = useId();
  const errorId = `${id}-error`;
  return (
    <div className={className}>
      <label htmlFor={id} className={hideLabel ? 'sr-only' : 'mb-2 block text-[13px] font-semibold text-ink'}>
        {label}
      </label>
      <div className="relative">
        <img
          src={icon}
          alt=""
          aria-hidden="true"
          className="pointer-events-none absolute top-1/2 left-5 size-[22px] -translate-y-1/2"
        />
        <input
          {...inputProps}
          id={id}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? errorId : undefined}
          className={`h-14 w-full rounded-2xl border bg-white pr-14 pl-14 text-sm text-ink transition-colors placeholder:text-placeholder focus:border-accent focus:outline-none focus:ring-4 focus:ring-accent/15 ${
            error ? 'border-danger' : 'border-line'
          }`}
        />
        {trailing && <div className="absolute top-1/2 right-4 -translate-y-1/2">{trailing}</div>}
      </div>
      {error && (
        <p id={errorId} role="alert" className="mt-2 text-[13px] font-medium text-danger">
          {error}
        </p>
      )}
    </div>
  );
}
