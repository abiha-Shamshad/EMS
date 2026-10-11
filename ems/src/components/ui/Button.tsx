import type { ButtonHTMLAttributes, ReactNode } from 'react';

type Variant = 'primary' | 'outline';

const variants: Record<Variant, string> = {
  primary:
    'bg-primary text-white hover:bg-primary-hover disabled:bg-primary/60 border border-transparent',
  outline: 'bg-white text-ink border border-outline-strong hover:bg-panel-from disabled:opacity-60',
};

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  isLoading?: boolean;
  loadingLabel?: string;
  leadingIcon?: ReactNode;
}

export function Button({
  variant = 'primary',
  isLoading = false,
  loadingLabel = 'Please wait...',
  leadingIcon,
  disabled,
  className = '',
  children,
  ...rest
}: ButtonProps) {
  return (
    <button
      {...rest}
      disabled={disabled || isLoading}
      aria-busy={isLoading}
      className={`flex h-14 w-full cursor-pointer items-center justify-center gap-3 rounded-xl text-base font-semibold transition-colors disabled:cursor-not-allowed ${variants[variant]} ${className}`}
    >
      {isLoading ? (
        <>
          <span
            aria-hidden="true"
            className="size-4 animate-spin rounded-full border-2 border-white/40 border-t-white"
          />
          {loadingLabel}
        </>
      ) : (
        <>
          {leadingIcon}
          {children}
        </>
      )}
    </button>
  );
}
