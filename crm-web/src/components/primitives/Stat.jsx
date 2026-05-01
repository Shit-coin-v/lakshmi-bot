export function Stat({ label, value, delta, deltaLabel, mono }) {
  const positive = (delta ?? 0) >= 0;
  return (
    <div style={{
      background: 'var(--surface-panel)', border: '1px solid var(--border)',
      borderRadius: 'var(--radius-lg)', padding: 16,
      display: 'flex', flexDirection: 'column', gap: 6,
    }}>
      <div style={{ fontSize: 12, color: 'var(--fg-muted)' }}>{label}</div>
      <div style={{ fontSize: 22, fontWeight: 600, color: 'var(--fg-primary)', fontFamily: mono ? 'ui-monospace, monospace' : 'inherit' }}>
        {value}
      </div>
      {deltaLabel && (
        <div style={{ fontSize: 12, color: positive ? 'var(--success)' : 'var(--danger)' }}>{deltaLabel}</div>
      )}
    </div>
  );
}

export default Stat;
