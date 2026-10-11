interface AvatarProps {
  name: string;
  size?: 'sm' | 'md';
}

const COLORS = ['bg-purple-bg text-purple-text', 'bg-info-bg text-info-text', 'bg-success-bg text-success-text'];

export function Avatar({ name, size = 'md' }: AvatarProps) {
  const initials = name
    .split(' ')
    .map((part) => part[0])
    .filter(Boolean)
    .slice(0, 2)
    .join('')
    .toUpperCase();
  const color = COLORS[name.length % COLORS.length];
  const box = size === 'sm' ? 'size-8 text-xs' : 'size-10 text-[13px]';
  return (
    <span
      aria-hidden="true"
      className={`flex shrink-0 items-center justify-center rounded-full font-bold ${box} ${color}`}
    >
      {initials || '?'}
    </span>
  );
}
