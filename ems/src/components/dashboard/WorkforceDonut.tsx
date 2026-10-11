import type { WorkforceSlice } from '@/demo/fixtures';

const COLORS: Record<WorkforceSlice['color'], string> = {
  blue: '#4a6cf7',
  teal: '#22b8a5',
  amber: '#e8a13d',
  slate: '#c3cbdf',
};

const RADIUS = 54;
const CIRC = 2 * Math.PI * RADIUS;

/** Donut chart (SVG) for employees by department, matching Screen 07. */
export function WorkforceDonut({ slices, total }: { slices: WorkforceSlice[]; total: number }) {
  const sum = slices.reduce((acc, slice) => acc + slice.count, 0) || 1;
  const lengths = slices.map((slice) => (slice.count / sum) * CIRC);
  const segments = slices.map((slice, index) => ({
    slice,
    length: lengths[index] ?? 0,
    start: lengths.slice(0, index).reduce((acc, len) => acc + len, 0),
  }));
  return (
    <div className="flex items-center gap-5">
      <div className="relative shrink-0" role="img" aria-label={`Workforce by department, ${total} employees total`}>
        <svg viewBox="0 0 140 140" className="size-[124px] sm:size-[140px]">
          <circle cx={70} cy={70} r={RADIUS} fill="none" stroke="#e9edf6" strokeWidth={16} />
          {segments.map(({ slice, length, start }) => {
            const dash = `${Math.max(length - 3, 1)} ${CIRC - Math.max(length - 3, 1)}`;
            return (
              <circle
                key={slice.label}
                cx={70}
                cy={70}
                r={RADIUS}
                fill="none"
                stroke={COLORS[slice.color]}
                strokeWidth={16}
                strokeDasharray={dash}
                strokeDashoffset={-start}
                strokeLinecap="butt"
                transform="rotate(-90 70 70)"
              />
            );
          })}
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <p className="text-xl leading-6 font-extrabold text-ink">{total}</p>
          <p className="text-[11px] text-ink-muted">Employees</p>
        </div>
      </div>
      <ul className="min-w-0 flex-1 space-y-2.5">
        {slices.map((slice) => (
          <li key={slice.label} className="flex items-center gap-2 text-[13px]">
            <span aria-hidden="true" className="size-2 shrink-0 rounded-full" style={{ background: COLORS[slice.color] }} />
            <span className="truncate text-ink-body">{slice.label}</span>
            <span className="ml-auto font-bold text-ink">{slice.count}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
