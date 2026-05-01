import { Icon } from '../Icon.jsx';

export function SuggestedOrder({ qty, velocity }) {
  if (!qty) {
    return <span style={{ fontSize: 12, color: 'var(--fg-muted)' }}>—</span>;
  }
  const hint = velocity ? `≈ ${velocity} шт/мес` : null;
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <span style={{
        display: 'inline-flex', alignItems: 'center', gap: 6,
        padding: '4px 10px', borderRadius: 999,
        background: 'var(--accent-soft)', color: 'var(--accent-600)',
        fontSize: 12, fontWeight: 600,
      }}>
        <Icon name="package-plus" size={12} />
        Заказать {qty} шт
      </span>
      {hint && <span style={{ fontSize: 11, color: 'var(--fg-muted)' }}>{hint}</span>}
    </div>
  );
}

export default SuggestedOrder;
