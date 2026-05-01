export function KV({ k, v, mono }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, padding: '6px 0' }}>
      <span style={{ color: 'var(--fg-muted)', fontSize: 12 }}>{k}</span>
      <span style={{
        color: 'var(--fg-primary)', fontSize: 13, fontWeight: 500,
        fontFamily: mono ? 'ui-monospace, monospace' : 'inherit',
      }}>{v}</span>
    </div>
  );
}

export default KV;
