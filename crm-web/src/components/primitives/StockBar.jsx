export function StockBar({ days, threshold = 1 }) {
  const tier = days < threshold ? 'danger' : (days < 3 ? 'warning' : 'ok');
  const color = tier === 'danger' ? 'var(--danger)' : tier === 'warning' ? 'var(--warning)' : 'var(--success)';
  const widthPct = Math.min(100, (days / 7) * 100);
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 110 }}>
      <div style={{ flex: 1, height: 4, background: 'var(--surface-panel-elevated)', borderRadius: 999, overflow: 'hidden' }}>
        <div style={{ width: `${widthPct}%`, height: '100%', background: color }} />
      </div>
      <span style={{ fontFamily: 'ui-monospace, monospace', fontSize: 12, color, minWidth: 40, textAlign: 'right', fontWeight: 500 }}>
        {days < 1 ? `${(days * 24).toFixed(0)} ч` : `${days.toFixed(1)} дн`}
      </span>
    </div>
  );
}

export default StockBar;
