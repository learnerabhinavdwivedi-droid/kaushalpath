import React from 'react';

export interface RadarSeries {
  name: string;
  color: string;
  values: number[]; // 0..1, aligned to `axes`
}

interface RadarChartProps {
  axes: string[];
  series: RadarSeries[];
  size?: number;
  label?: string;
}

// Small, dependency-free radar. Kept hand-rolled (no chart library is a project
// dependency) so the PWA bundle stays lean and the render is deterministic.
export const RadarChart: React.FC<RadarChartProps> = ({ axes, series, size = 260, label }) => {
  const cx = size / 2;
  const cy = size / 2;
  const radius = size / 2 - 44;
  const n = axes.length;

  const pointAt = (index: number, value: number): [number, number] => {
    const angle = (Math.PI * 2 * index) / n - Math.PI / 2;
    const r = radius * Math.max(0, Math.min(1, value));
    return [cx + r * Math.cos(angle), cy + r * Math.sin(angle)];
  };

  const ringPoly = (frac: number) =>
    axes.map((_, i) => pointAt(i, frac).join(',')).join(' ');

  const seriesPoly = (values: number[]) =>
    values.map((v, i) => pointAt(i, v).join(',')).join(' ');

  return (
    <svg
      viewBox={`0 0 ${size} ${size}`}
      width="100%"
      role="img"
      aria-label={label || 'Radar comparison chart'}
      className="max-w-[320px] mx-auto"
    >
      {[0.25, 0.5, 0.75, 1].map((frac) => (
        <polygon
          key={frac}
          points={ringPoly(frac)}
          fill="none"
          stroke="#E5E7EB"
          strokeWidth={1}
        />
      ))}
      {axes.map((axis, i) => {
        const [x, y] = pointAt(i, 1);
        const [lx, ly] = pointAt(i, 1.18);
        return (
          <g key={axis}>
            <line x1={cx} y1={cy} x2={x} y2={y} stroke="#E5E7EB" strokeWidth={1} />
            <text
              x={lx}
              y={ly}
              fontSize={11}
              textAnchor="middle"
              dominantBaseline="middle"
              fill="#4B5563"
            >
              {axis}
            </text>
          </g>
        );
      })}
      {series.map((s) => (
        <polygon
          key={s.name}
          points={seriesPoly(s.values)}
          fill={s.color}
          fillOpacity={0.18}
          stroke={s.color}
          strokeWidth={2}
        />
      ))}
    </svg>
  );
};
