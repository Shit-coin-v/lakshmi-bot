export function Toggle({ label, on, locked }) {
  return (
    <label style={{
      display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12,
      padding: '8px 0', opacity: locked ? 0.6 : 1,
    }}>
      <span style={{ fontSize: 13, color: 'var(--fg-secondary)' }}>{label}</span>
      <span style={{
        width: 32, height: 18, borderRadius: 999,
        background: on ? 'var(--accent-600)' : 'var(--surface-panel-elevated)',
        position: 'relative', transition: 'background var(--dur-standard) var(--ease-standard)',
      }}>
        <span style={{
          position: 'absolute', top: 2, left: on ? 16 : 2,
          width: 14, height: 14, borderRadius: '50%', background: '#FFFFFF',
          transition: 'left var(--dur-standard) var(--ease-standard)',
        }} />
      </span>
    </label>
  );
}

export default Toggle;
