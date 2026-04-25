import { BRAND, RADIUS } from '../theme.js';

// Плоский dropdown первого уровня категорий + опция "Все".
export default function CategoryFilter({ categories, value, onChange }) {
  return (
    <select
      value={value ?? ''}
      onChange={(e) => onChange(e.target.value || null)}
      aria-label="Категория"
      style={{
        flex: '1 1 auto',
        minWidth: 0,
        padding: '10px 12px',
        fontSize: 14,
        background: BRAND.surface,
        border: `1px solid ${BRAND.border}`,
        borderRadius: RADIUS.md,
        outline: 'none',
      }}
    >
      <option value="">Все категории</option>
      {categories.map((c) => (
        <option key={c.id} value={c.id}>
          {c.name}
        </option>
      ))}
    </select>
  );
}
