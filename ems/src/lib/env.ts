// All environment access goes through here (VITE_ prefix, public values only).
export const env = {
  apiUrl: (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000',
  isDemoMode: import.meta.env.VITE_DEMO_MODE === 'true',
};
