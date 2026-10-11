import { useId } from 'react';
import type { RevenuePoint } from '@/demo/fixtures';

const WIDTH = 640;
const HEIGHT = 240;
const PAD_LEFT = 44;
const PAD_RIGHT = 16;
const PAD_TOP = 12;
const PAD_BOTTOM = 28;

/** Revenue line chart drawn as SVG (no chart dependency), matching Screen 07. */
export function RevenueChart({ points }: { points: RevenuePoint[] }) {
  const gradientId = useId();
  const max = Math.max(...points.map((p) => p.value)) * 1.08;
  const innerW = WIDTH - PAD_LEFT - PAD_RIGHT;
  const innerH = HEIGHT - PAD_TOP - PAD_BOTTOM;

  const coords = points.map((point, index) => {
    const x = PAD_LEFT + (points.length === 1 ? innerW / 2 : (index / (points.length - 1)) * innerW);
    const y = PAD_TOP + innerH - (point.value / max) * innerH;
    return { x, y, point };
  });
  const line = coords.map((c, i) => `${i === 0 ? 'M' : 'L'}${c.x.toFixed(1)},${c.y.toFixed(1)}`).join(' ');
  const area = `${line} L${coords[coords.length - 1].x.toFixed(1)},${(PAD_TOP + innerH).toFixed(1)} L${coords[0].x.toFixed(1)},${(PAD_TOP + innerH).toFixed(1)} Z`;

  const ticks = [50000, 100000, 150000, 200000];
  const tickY = (value: number) => PAD_TOP + innerH - (value / max) * innerH;

  return (
    <figure>
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label="Monthly revenue performance, rising from May to October" className="h-auto w-full">
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#4a6cf7" stopOpacity="0.22" />
            <stop offset="100%" stopColor="#4a6cf7" stopOpacity="0.04" />
          </linearGradient>
        </defs>
        {ticks.map((tick) => (
          <g key={tick}>
            <line x1={PAD_LEFT} x2={WIDTH - PAD_RIGHT} y1={tickY(tick)} y2={tickY(tick)} stroke="#e8ecf6" strokeWidth={1} />
            <text x={PAD_LEFT - 6} y={tickY(tick) + 4} textAnchor="end" fontSize={11} fill="#8b96b5">
              ${tick / 1000}k
            </text>
          </g>
        ))}
        <path d={area} fill={`url(#${gradientId})`} />
        <path d={line} fill="none" stroke="#4a6cf7" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" />
        {coords.map((c) => (
          <g key={c.point.month}>
            <circle cx={c.x} cy={c.y} r={5} fill="#fff" stroke="#4a6cf7" strokeWidth={2.5} />
            <text x={c.x} y={HEIGHT - 8} textAnchor="middle" fontSize={11} fill="#8b96b5">
              {c.point.month}
            </text>
          </g>
        ))}
      </svg>
      <figcaption className="mt-1 flex items-center gap-1.5 text-xs text-ink-muted">
        <span aria-hidden="true" className="size-2 rounded-full bg-chart-line" />
        Revenue (USD)
      </figcaption>
    </figure>
  );
}
