import { BRAND, RADIUS } from '../theme.js';
import { PHOTO_STATUS_FILTERS } from '../utils/photoStatus.js';

// Сегментированный фильтр по статусу фото.
export default function PhotoStatusFilter({ value, onChange }) {
  return (
    <div
      role="tablist"
      aria-label="Фильтр по статусу фото"
      style={{
        display: 'flex',
        background: BRAND.surface,
        borderRadius: RADIUS.md,
        border: `1px solid ${BRAND.border}`,
        padding: 3,
        gap: 2,
      }}
    >
      {PHOTO_STATUS_FILTERS.map((opt) => {
        const active = value === opt.value;
        return (
          <button
            key={opt.value}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => onChange(opt.value)}
            style={{
              flex: 1,
              padding: '8px 6px',
              fontSize: 13,
              fontWeight: active ? 600 : 500,
              color: active ? BRAND.white : BRAND.muted,
              background: active ? BRAND.green : 'transparent',
              borderRadius: RADIUS.sm,
              transition: 'background 0.15s, color 0.15s',
            }}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
