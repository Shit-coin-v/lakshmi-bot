const ROWS = ['A', 'B', 'C'];
const COLS = ['X', 'Y', 'Z'];

export function AbcXyzMatrix({ matrix, formatter, unit = '' }) {
  const values = Object.values(matrix);
  const max = Math.max(...values, 1);

  return (
    <div style={{
      background: 'var(--surface-panel)', border: '1px solid var(--border)',
      borderRadius: 'var(--radius-lg)', padding: 16,
    }}>
      <div style={{ display: 'grid', gridTemplateColumns: '40px repeat(3, 1fr)', gap: 8 }}>
        <div />
        {COLS.map((c) => (
          <div key={c} style={{ textAlign: 'center', fontSize: 13, fontWeight: 600, color: `var(--xyz-${c.toLowerCase()})`, paddingBottom: 8 }}>
            {c}
          </div>
        ))}
        {ROWS.map((r) => (
          <div key={r} style={{ display: 'contents' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 13, fontWeight: 600, color: `var(--abc-${r.toLowerCase()})` }}>
              {r}
            </div>
            {COLS.map((c) => {
              const key = `${r}${c}`;
              const v = matrix[key] ?? 0;
              const intensity = v / max;
              return (
                <div
                  key={key}
                  style={{
                    aspectRatio: '2 / 1',
                    minHeight: 64,
                    display: 'flex', flexDirection: 'column',
                    alignItems: 'center', justifyContent: 'center',
                    background: `rgba(59, 130, 246, ${0.08 + intensity * 0.45})`,
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--radius-md)',
                    color: 'var(--fg-primary)',
                    gap: 2,
                  }}
                >
                  <div style={{ fontSize: 11, color: 'var(--fg-muted)', letterSpacing: '0.05em' }}>{key}</div>
                  <div style={{ fontSize: 16, fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>
                    {formatter ? formatter(v) : v.toLocaleString('ru-RU')}{unit ? ' ' + unit : ''}
                  </div>
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
}

export default AbcXyzMatrix;
