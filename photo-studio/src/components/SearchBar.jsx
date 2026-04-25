import { BRAND, RADIUS } from '../theme.js';

// Поиск с дебаунсом реализуется в родителе; сам компонент управляемый.
export default function SearchBar({ value, onChange, placeholder = 'Поиск по названию или SKU' }) {
  return (
    <div
      style={{
        position: 'relative',
        marginBottom: 10,
      }}
    >
      <input
        type="search"
        inputMode="search"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        aria-label="Поиск товара"
        style={{
          width: '100%',
          padding: '12px 14px 12px 40px',
          fontSize: 15,
          background: BRAND.surface,
          border: `1px solid ${BRAND.border}`,
          borderRadius: RADIUS.md,
          outline: 'none',
        }}
      />
      <svg
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        stroke={BRAND.muted}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
        style={{ position: 'absolute', top: '50%', left: 12, transform: 'translateY(-50%)' }}
      >
        <circle cx="11" cy="11" r="8" />
        <line x1="21" y1="21" x2="16.65" y2="16.65" />
      </svg>
    </div>
  );
}
