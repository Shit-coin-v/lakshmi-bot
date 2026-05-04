import { useState } from 'react';
import { AbcXyzMatrix } from '../components/primitives/AbcXyzMatrix.jsx';
import { fmtRubShort } from '../utils/format.js';
import { ScreenSkeleton } from '../components/ScreenSkeleton.jsx';
import { ErrorBanner } from '../components/ErrorBanner.jsx';
import { useAbcXyz } from '../hooks/useAbcXyz.js';

export default function AbcXyzScreen() {
  const [unit, setUnit] = useState('sku'); // 'sku' | 'revenue'

  const { data: abcXyz, isLoading, error, refetch } = useAbcXyz();
  if (isLoading) return <ScreenSkeleton variant="dashboard" />;
  if (error)     return <ErrorBanner title="Не удалось загрузить матрицу" error={error} onRetry={refetch} />;

  const matrix = unit === 'sku' ? abcXyz.matrixSku : abcXyz.matrixRevenue;
  const formatter = unit === 'sku' ? null : fmtRubShort;

  const total = Object.values(matrix).reduce((s, v) => s + v, 0);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
        {[
          { id: 'sku', label: 'SKU' },
          { id: 'revenue', label: 'Выручка' },
        ].map((t) => (
          <button
            key={t.id}
            onClick={() => setUnit(t.id)}
            style={{
              padding: '6px 14px', borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border)',
              background: unit === t.id ? 'var(--accent-600)' : 'var(--surface-panel)',
              color: unit === t.id ? '#FFFFFF' : 'var(--fg-secondary)',
              cursor: 'pointer', fontSize: 13, fontWeight: 500,
            }}
          >{t.label}</button>
        ))}
        <div style={{ flex: 1 }} />
        <span style={{ fontSize: 12, color: 'var(--fg-muted)' }}>
          Всего: {unit === 'sku' ? total.toLocaleString('ru-RU') + ' SKU' : fmtRubShort(total)}
        </span>
      </div>
      <AbcXyzMatrix matrix={matrix} formatter={formatter} unit={unit === 'sku' ? 'SKU' : ''} />
    </div>
  );
}
