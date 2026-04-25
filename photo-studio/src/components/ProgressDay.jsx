import { BRAND, RADIUS, SHADOW } from '../theme.js';

// Прогресс дня: сколько товаров сотрудник отснял сегодня.
// "Всего без фото" — справочное значение, передаётся из родителя.
export default function ProgressDay({ done, totalMissing }) {
  const target = Math.max(done, done + (totalMissing || 0));
  const percent = target > 0 ? Math.round((done / target) * 100) : 0;
  return (
    <div
      style={{
        background: BRAND.surface,
        borderRadius: RADIUS.lg,
        boxShadow: SHADOW.card,
        padding: '12px 16px',
        marginBottom: 12,
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'baseline',
          marginBottom: 8,
        }}
      >
        <span style={{ fontSize: 13, color: BRAND.muted }}>Прогресс дня</span>
        <span style={{ fontSize: 13, color: BRAND.text, fontWeight: 600 }}>
          {done} {totalMissing > 0 ? `/ ${done + totalMissing}` : ''}
          {totalMissing > 0 && ` · ${percent}%`}
        </span>
      </div>
      <div
        style={{
          height: 6,
          background: BRAND.greenSoft,
          borderRadius: 3,
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            height: '100%',
            width: `${percent}%`,
            background: BRAND.green,
            transition: 'width 0.3s ease',
          }}
        />
      </div>
    </div>
  );
}
