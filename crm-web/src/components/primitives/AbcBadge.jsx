export function AbcBadge({ v }) {
  const color = `var(--abc-${(v || '').toLowerCase()})`;
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
      minWidth: 22, height: 22, padding: '0 6px',
      borderRadius: 4, fontSize: 11, fontWeight: 700, textAlign: 'center',
      color: '#0F172A', background: color,
    }}>{v}</span>
  );
}

export default AbcBadge;
