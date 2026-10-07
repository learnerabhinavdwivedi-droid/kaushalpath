import React from 'react';
import { useTranslation } from 'react-i18next';
import type { DistrictRow } from '../../api/client';

interface Props {
  districts: DistrictRow[];
  onSelect?: (district: string) => void;
}

/** India bounding box used for the offline equirectangular projection. */
const LON_MIN = 68;
const LON_MAX = 97;
const LAT_MIN = 8;
const LAT_MAX = 37;
const VIEW_W = 480;
const VIEW_H = 440;

function project(lat: number, lon: number) {
  const x = ((lon - LON_MIN) / (LON_MAX - LON_MIN)) * VIEW_W;
  // SVG y grows downward, so invert latitude.
  const y = ((LAT_MAX - lat) / (LAT_MAX - LAT_MIN)) * VIEW_H;
  return { x, y };
}

/** avg_rs 0..1 -> green (calm) .. red (high). Suppressed -> neutral grey. */
function colour(avgRs: number | null): string {
  if (avgRs == null) return '#9CA3AF';
  const hue = Math.round(120 * (1 - Math.min(1, Math.max(0, avgRs))));
  return `hsl(${hue}, 75%, 45%)`;
}

/**
 * Phase 16 — offline SVG district bubble map. No external tiles (works without
 * a network): lat/lon is projected straight into the viewport, bubble radius
 * encodes family count and fill colour encodes average resistance.
 */
export const DistrictBubbleMap: React.FC<Props> = ({ districts, onSelect }) => {
  const { t } = useTranslation();
  const shown = districts.filter((d) => d.n > 0);
  const maxN = Math.max(1, ...shown.map((d) => d.n));

  return (
    <div className="card">
      <h2 className="mb-1 font-bold text-lg">{t('admin_dash.map_title')}</h2>
      <p className="mb-3 text-xs text-textSecondary">{t('admin_dash.map_hint')}</p>
      {shown.length === 0 ? (
        <p className="text-sm text-textSecondary">{t('admin_dash.empty')}</p>
      ) : (
        <svg
          viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
          className="h-auto w-full max-w-md"
          role="group"
          aria-label={t('admin_dash.map_title')}
        >
          <rect x={0} y={0} width={VIEW_W} height={VIEW_H} className="fill-background" rx={12} />
          {shown.map((d) => {
            const { x, y } = project(d.lat, d.lon);
            const r = 6 + Math.sqrt(d.n / maxN) * 22;
            const label = d.is_suppressed
              ? `${d.district}: ${t('admin_dash.suppressed')}`
              : `${d.district}: ${d.n} ${t('admin_dash.families')}, ${t('admin_dash.avg_rs')} ${d.avg_rs}`;
            return (
              <circle
                key={d.district}
                cx={x}
                cy={y}
                r={r}
                fill={colour(d.avg_rs)}
                fillOpacity={0.75}
                stroke={colour(d.avg_rs)}
                strokeWidth={1.5}
                strokeDasharray={d.is_suppressed ? '4 3' : undefined}
                tabIndex={0}
                role="img"
                aria-label={label}
                onClick={() => onSelect?.(d.district)}
                onKeyDown={(e) => e.key === 'Enter' && onSelect?.(d.district)}
                style={{ cursor: 'pointer', outline: 'none' }}
              >
                <title>{label}</title>
              </circle>
            );
          })}
        </svg>
      )}
      <div className="mt-2 flex items-center gap-2 text-xs text-textSecondary">
        <span>{t('admin_dash.legend_low')}</span>
        <span className="h-3 w-16 rounded" style={{ background: 'linear-gradient(90deg, hsl(120,75%,45%), hsl(0,75%,45%))' }} />
        <span>{t('admin_dash.legend_high')}</span>
      </div>
    </div>
  );
};
