// Date/time display. Screens format dates ONLY through these helpers.

const dateTimeFormatter = new Intl.DateTimeFormat('en-US', {
  month: 'short',
  day: 'numeric',
  year: 'numeric',
  hour: 'numeric',
  minute: '2-digit',
});

const dateFormatter = new Intl.DateTimeFormat('en-US', {
  month: 'short',
  day: 'numeric',
  year: 'numeric',
});

export function formatDateTime(value: string | Date): string {
  return dateTimeFormatter.format(value instanceof Date ? value : new Date(value));
}

export function formatDate(value: string | Date): string {
  return dateFormatter.format(value instanceof Date ? value : new Date(value));
}

/** Relative label used by the activity feed ("10 min ago"). */
export function timeAgo(value: string | Date, now: Date = new Date()): string {
  const diffMs = now.getTime() - new Date(value).getTime();
  const minutes = Math.max(0, Math.round(diffMs / 60000));
  if (minutes < 1) return 'Just now';
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} hour${hours === 1 ? '' : 's'} ago`;
  const days = Math.round(hours / 24);
  return `${days} day${days === 1 ? '' : 's'} ago`;
}
