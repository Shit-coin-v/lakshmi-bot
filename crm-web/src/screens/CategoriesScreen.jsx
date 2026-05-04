import { useNavigate } from 'react-router-dom';
import { Stat } from '../components/primitives/Stat.jsx';
import { AbcBadge } from '../components/primitives/AbcBadge.jsx';
import { XyzBadge } from '../components/primitives/XyzBadge.jsx';
import { fmtRubShort, fmtPct } from '../utils/format.js';
import { ScreenSkeleton } from '../components/ScreenSkeleton.jsx';
import { ErrorBanner } from '../components/ErrorBanner.jsx';
import { useCategories } from '../hooks/useCategories.js';

export default function CategoriesScreen() {
  const navigate = useNavigate();

  const { data, isLoading, error, refetch } = useCategories();
  if (isLoading) return <ScreenSkeleton variant="table" />;
  if (error)     return <ErrorBanner title="Не удалось загрузить категории" error={error} onRetry={refetch} />;
  const categories = data;

  const totals = categories.reduce(
    (a, c) => ({
      revenue: a.revenue + c.revenue,
      cogs: a.cogs + c.cogs,
      skus: a.skus + c.skus,
    }),
    { revenue: 0, cogs: 0, skus: 0 }
  );
  const grossProfit = totals.revenue - totals.cogs;
  const margin = (grossProfit / totals.revenue) * 100;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12 }}>
        <Stat label="Категорий" value={categories.length} />
        <Stat label="SKU всего" value={totals.skus.toLocaleString('ru-RU')} />
        <Stat label="Выручка / мес" value={fmtRubShort(totals.revenue)} delta={0.042} deltaLabel="+4,2%" />
        <Stat label="Валовая прибыль" value={fmtRubShort(grossProfit)} delta={0.051} deltaLabel="+5,1%" />
        <Stat label="Рентабельность" value={fmtPct(margin)} delta={0.004} deltaLabel="+0,4 п.п." />
      </div>

      <div style={{ background: 'var(--surface-panel)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', overflow: 'hidden' }}>
        <table style={{ width: '100%', fontSize: 13 }}>
          <thead style={{ background: 'var(--surface-panel-elevated)', color: 'var(--fg-muted)' }}>
            <tr>
              <th style={{ textAlign: 'left',  padding: '10px 12px', fontWeight: 500 }}>Категория</th>
              <th style={{ textAlign: 'right', padding: '10px 12px', fontWeight: 500 }}>SKU</th>
              <th style={{ textAlign: 'right', padding: '10px 12px', fontWeight: 500 }}>Выручка</th>
              <th style={{ textAlign: 'right', padding: '10px 12px', fontWeight: 500 }}>Доля</th>
              <th style={{ textAlign: 'right', padding: '10px 12px', fontWeight: 500 }}>Оборачиваемость</th>
              <th style={{ textAlign: 'center', padding: '10px 12px', fontWeight: 500 }}>ABC</th>
              <th style={{ textAlign: 'center', padding: '10px 12px', fontWeight: 500 }}>XYZ</th>
            </tr>
          </thead>
          <tbody>
            {categories.map((c) => (
              <tr
                key={c.slug}
                onClick={() => navigate(`/categories/${c.slug}`)}
                style={{ cursor: 'pointer', borderTop: '1px solid var(--border)' }}
              >
                <td style={{ padding: '10px 12px' }}>
                  <div style={{ fontWeight: 500, color: 'var(--fg-primary)' }}>{c.name}</div>
                  <div style={{ fontSize: 11, color: 'var(--fg-muted)' }}>{c.code}</div>
                </td>
                <td style={{ padding: '10px 12px', textAlign: 'right', color: 'var(--fg-primary)' }}>{c.skus}</td>
                <td style={{ padding: '10px 12px', textAlign: 'right', color: 'var(--fg-primary)' }}>{fmtRubShort(c.revenue)}</td>
                <td style={{ padding: '10px 12px', textAlign: 'right', color: 'var(--fg-secondary)' }}>{fmtPct(c.share)}</td>
                <td style={{ padding: '10px 12px', textAlign: 'right', color: 'var(--fg-secondary)' }}>{c.turnover.toFixed(1).replace('.', ',')}</td>
                <td style={{ padding: '10px 12px', textAlign: 'center' }}><AbcBadge v={c.abc} /></td>
                <td style={{ padding: '10px 12px', textAlign: 'center' }}><XyzBadge v={c.xyz} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
