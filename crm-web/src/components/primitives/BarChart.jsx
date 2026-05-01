export function BarChart({ data, height = 180, accent = 'var(--accent-600)' }) {
  if (!data?.length) return null;
  const max = Math.max(...data.map((d) => d.value));
  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', gap: 6, height }}>
      {data.map((d, i) => {
        const isLast = i === data.length - 1;
        const h = (d.value / max) * (height - 20);
        return (
          <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 6, alignItems: 'center' }}>
            <div style={{
              width: '100%', height: `${h}px`,
              background: isLast ? accent : 'var(--accent-soft)',
              borderRadius: '4px 4px 0 0',
              transition: 'background var(--dur-standard) var(--ease-standard)',
            }} />
            <span style={{ fontSize: 11, color: 'var(--fg-muted)' }}>{d.label}</span>
          </div>
        );
      })}
    </div>
  );
}

export default BarChart;
