// Sidebar + header icons (stroke style matching the Screen 07 reference).
// Brand/product illustrations stay as files in src/assets; these small UI
// glyphs are inline so they inherit text color and need no asset requests.
import type { SVGProps } from 'react';

function Base({ children, ...rest }: SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.7}
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

export function DashboardIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <Base {...props}>
      <rect x="3" y="3" width="6" height="6" rx="1.5" />
      <rect x="11" y="3" width="6" height="6" rx="1.5" />
      <rect x="3" y="11" width="6" height="6" rx="1.5" />
      <rect x="11" y="11" width="6" height="6" rx="1.5" />
    </Base>
  );
}

export function MonitoringIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <Base {...props}>
      <rect x="3" y="4" width="14" height="10" rx="2" />
      <path d="M8 18h4M10 14v4" />
    </Base>
  );
}

export function HrIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <Base {...props}>
      <circle cx="10" cy="7" r="3.2" />
      <path d="M4 16.5c.8-3 3.2-4.5 6-4.5s5.2 1.5 6 4.5" />
    </Base>
  );
}

export function ProjectsIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <Base {...props}>
      <rect x="3.5" y="5" width="13" height="11.5" rx="2" />
      <path d="M3.5 9h13M7 3v3M13 3v3" />
    </Base>
  );
}

export function CrmIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <Base {...props}>
      <rect x="3.5" y="3.5" width="13" height="13" rx="2" />
      <path d="m7.5 10 2.2 2.2 3-3.4" />
    </Base>
  );
}

export function LeadHunterIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <Base {...props}>
      <path d="M4 5.5h12M4 10h12M4 14.5h7" />
      <circle cx="15" cy="14.5" r="2.3" />
      <path d="m16.6 16.1 1.4 1.4" />
    </Base>
  );
}

export function AutomationsIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <Base {...props}>
      <circle cx="10" cy="10" r="6.5" />
      <path d="M3.5 10h13M10 3.5c-4 4-4 9 0 13 4-4 4-9 0-13Z" />
    </Base>
  );
}

export function ReportsIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <Base {...props}>
      <path d="M4 16.5h13" />
      <path d="M6.5 16.5v-5M10.5 16.5v-8M14.5 16.5v-3" />
    </Base>
  );
}

export function UsersIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <Base {...props}>
      <circle cx="7.5" cy="7.5" r="2.8" />
      <path d="M2.8 16c.7-2.6 2.5-4 4.7-4s4 1.4 4.7 4" />
      <circle cx="13.8" cy="8.5" r="2.2" />
      <path d="M13.4 12.2c2 .2 3.3 1.4 3.8 3.3" />
    </Base>
  );
}

export function IntegrationsIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <Base {...props}>
      <rect x="3" y="3" width="5.5" height="5.5" rx="1.2" />
      <rect x="11.5" y="3" width="5.5" height="5.5" rx="1.2" />
      <rect x="3" y="11.5" width="5.5" height="5.5" rx="1.2" />
      <path d="M14.2 11.5v5.5M11.5 14.2h5.5" />
    </Base>
  );
}

export function SettingsIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <Base {...props}>
      <circle cx="10" cy="10" r="2.6" />
      <path d="M10 2.8v2.4M10 14.8v2.4M2.8 10h2.4M14.8 10h2.4M4.9 4.9l1.7 1.7M13.4 13.4l1.7 1.7M15.1 4.9l-1.7 1.7M6.6 13.4l-1.7 1.7" />
    </Base>
  );
}

export function BellIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <Base {...props}>
      <path d="M10 3a4.5 4.5 0 0 0-4.5 4.5c0 4-1.5 5-1.5 5h12s-1.5-1-1.5-5A4.5 4.5 0 0 0 10 3Z" />
      <path d="M8.3 15.5a1.8 1.8 0 0 0 3.4 0" />
    </Base>
  );
}

export function SearchIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <Base {...props}>
      <circle cx="9" cy="9" r="5.5" />
      <path d="m13.5 13.5 3 3" />
    </Base>
  );
}

export function ChevronDownIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <Base {...props}>
      <path d="m5 8 5 5 5-5" />
    </Base>
  );
}

export function MenuIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <Base {...props}>
      <path d="M4 6.5h12M4 10h12M4 13.5h12" />
    </Base>
  );
}

export function CloseIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <Base {...props}>
      <path d="m6 6 8 8M14 6l-8 8" />
    </Base>
  );
}

export function ArrowLeftIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <Base {...props}>
      <path d="M12 5l-5 5 5 5M7.5 10H16" />
    </Base>
  );
}

export function ArrowRightIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <Base {...props}>
      <path d="M8 5l5 5-5 5M12.5 10H4" />
    </Base>
  );
}

export function LogoutIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <Base {...props}>
      <path d="M12 4H6.5A1.5 1.5 0 0 0 5 5.5v9A1.5 1.5 0 0 0 6.5 16H12" />
      <path d="M9 10h8M14.5 7.5 17 10l-2.5 2.5" />
    </Base>
  );
}
