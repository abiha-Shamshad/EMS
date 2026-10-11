// Small decorative illustrations drawn inline (stroke style), used on auth
// and onboarding screens. Larger brand/product art stays as asset files.
import type { SVGProps } from 'react';

function Base({ children, ...rest }: SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 64 64"
      fill="none"
      stroke="currentColor"
      strokeWidth={2.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      {...rest}
    >
      {children}
    </svg>
  );
}

export function EnvelopeIllustration(props: SVGProps<SVGSVGElement>) {
  return (
    <Base {...props}>
      <rect x="10" y="20" width="44" height="30" rx="5" />
      <path d="m13 24 19 14 19-14" />
      <circle cx="50" cy="14" r="4" fill="#27c3a6" stroke="none" />
    </Base>
  );
}

export function LockIllustration(props: SVGProps<SVGSVGElement>) {
  return (
    <Base {...props}>
      <rect x="16" y="28" width="32" height="24" rx="5" />
      <path d="M22 28v-6a10 10 0 0 1 20 0v6" />
      <circle cx="32" cy="40" r="3" fill="currentColor" stroke="none" />
    </Base>
  );
}

export function TeamIllustration(props: SVGProps<SVGSVGElement>) {
  return (
    <Base {...props}>
      <circle cx="32" cy="20" r="9" />
      <path d="M18 52c1.5-8 7-12 14-12s12.5 4 14 12" />
      <circle cx="14" cy="26" r="6" />
      <path d="M6 52c1-6 4.5-9.5 9-10.5" />
      <circle cx="50" cy="26" r="6" />
      <path d="M58 52c-1-6-4.5-9.5-9-10.5" />
    </Base>
  );
}

export function FolderIllustration(props: SVGProps<SVGSVGElement>) {
  return (
    <Base {...props}>
      <path d="M10 20a4 4 0 0 1 4-4h10l5 6h15a4 4 0 0 1 4 4v18a4 4 0 0 1-4 4H14a4 4 0 0 1-4-4Z" />
      <path d="M20 34h14M20 40h9" />
    </Base>
  );
}
