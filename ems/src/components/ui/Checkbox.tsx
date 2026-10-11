import { useId, type InputHTMLAttributes, type ReactNode } from 'react';
import checkIcon from '@/assets/icons/check.svg';

interface CheckboxProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'id' | 'type'> {
  label: ReactNode;
}

export function Checkbox({ label, className = '', ...inputProps }: CheckboxProps) {
  const id = useId();
  return (
    <label htmlFor={id} className={`flex cursor-pointer items-center gap-2.5 ${className}`}>
      <span className="relative flex size-[18px] shrink-0">
        <input {...inputProps} id={id} type="checkbox" className="peer sr-only" />
        <span className="absolute inset-0 rounded-[5px] border border-line bg-white transition-colors peer-checked:border-accent peer-checked:bg-accent peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-accent" />
        <img
          src={checkIcon}
          alt=""
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 m-auto size-3 opacity-0 peer-checked:opacity-100"
        />
      </span>
      <span className="text-sm text-ink-body">{label}</span>
    </label>
  );
}
