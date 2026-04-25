import { BRAND } from '../theme.js';

// Простой CSS-spinner на основе keyframe-анимации в inline-стилях.
export default function Spinner({ size = 24, color = BRAND.green }) {
  const dimension = `${size}px`;
  return (
    <span
      role="status"
      aria-label="Загрузка"
      style={{
        display: 'inline-block',
        width: dimension,
        height: dimension,
        border: `3px solid ${BRAND.greenLight}`,
        borderTopColor: color,
        borderRadius: '50%',
        animation: 'lps-spin 0.8s linear infinite',
      }}
    >
      <style>{`@keyframes lps-spin { to { transform: rotate(360deg); } }`}</style>
    </span>
  );
}
