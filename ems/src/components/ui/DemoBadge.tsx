import { env } from '@/lib/env';

/** Small "Demo data" pill shown on dashboard cards while the backend is not connected. */
export function DemoBadge() {
  if (!env.isDemoMode) return null;
  return (
    <span
      title="Fictional sample data for exploring the frontend. Connect the backend to see real numbers."
      className="inline-flex items-center rounded-full bg-warning-bg px-2.5 py-1 text-[11px] font-bold text-warning-text"
    >
      Demo data
    </span>
  );
}
