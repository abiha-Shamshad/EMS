import { useId, type TextareaHTMLAttributes } from 'react';

interface TextareaProps extends Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, 'id'> {
  label: string;
  error?: string;
  hint?: string;
  optionalTag?: boolean;
  maxLength?: number;
  showCount?: boolean;
}

export function Textarea({
  label,
  error,
  hint,
  optionalTag,
  maxLength,
  showCount,
  className = '',
  value,
  ...rest
}: TextareaProps) {
  const id = useId();
  const errorId = `${id}-error`;
  const count = typeof value === 'string' ? value.length : 0;
  return (
    <div className={className}>
      <label htmlFor={id} className="mb-2 block text-[13px] font-semibold text-ink">
        {label}{' '}
        {optionalTag && <span className="font-normal text-ink-muted">(optional)</span>}
      </label>
      <textarea
        {...rest}
        id={id}
        value={value}
        maxLength={maxLength}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? errorId : hint ? `${id}-hint` : undefined}
        rows={4}
        className={`min-h-[118px] w-full resize-y rounded-2xl border bg-white px-5 py-4 text-sm text-ink transition-colors placeholder:text-placeholder focus:border-accent focus:ring-4 focus:ring-accent/15 focus:outline-none ${
          error ? 'border-danger' : 'border-line'
        }`}
      />
      <div className="mt-2 flex items-center justify-between gap-3">
        <div>
          {hint && !error && (
            <p id={`${id}-hint`} className="text-[13px] text-ink-muted">
              {hint}
            </p>
          )}
          {error && (
            <p id={errorId} role="alert" className="text-[13px] font-medium text-danger">
              {error}
            </p>
          )}
        </div>
        {(showCount || maxLength) && (
          <p aria-live="polite" className="shrink-0 text-xs text-ink-muted">
            {count} / {maxLength}
          </p>
        )}
      </div>
    </div>
  );
}
