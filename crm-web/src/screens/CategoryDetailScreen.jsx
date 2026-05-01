import { useNavigate, useParams, Link } from 'react-router-dom';
import { Stat } from '../components/primitives/Stat.jsx';
import { AbcBadge } from '../components/primitives/AbcBadge.jsx';
import { XyzBadge } from '../components/primitives/XyzBadge.jsx';
import { Sparkline } from '../components/primitives/Sparkline.jsx';
import { StockBar } from '../components/primitives/StockBar.jsx';
import { SuggestedOrder } from '../components/primitives/SuggestedOrder.jsx';
import { EmptyState } from '../components/EmptyState.jsx';
import categories from '../fixtures/categories.js';
import skus from '../fixtures/skus.js';
import { fmtRubShort, fmtPct } from '../utils/format.js';

export default function CategoryDetailScreen() {
  const { slug } = useParams();
  const navigate = useNavigate();
  const cat = categories.find((c) => c.slug === slug);

  if (!cat) {
    return (
      <EmptyState
        title="Категория не найдена"
        hint={`slug «${slug}» отсутствует в фикстурах`}
        onBack={() => navigate('/categories')}
        backLabel="← К списку категорий"
      />
    );
  }

  const catSkus = skus.filter((s) => s.categorySlug === cat.slug);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <Link to="/categories" style={{ color: 'var(--fg-muted)', fontSize: 12 }}>← Все категории</Link>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <div>
          <div style={{ fontSize: 18, fontWeight: 600, color: 'var(--fg-primary)' }}>{cat.name}</div>
          <div style={{ fontSize: 12, color: 'var(--fg-muted)' }}>{cat.code} · {cat.skus} SKU</div>
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          <AbcBadge v={cat.abc} />
          <XyzBadge v={cat.xyz} />
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
        <Stat label="Выручка / мес" value={fmtRubShort(cat.revenue)} />
        <Stat label="Себестоимость" value={fmtRubShort(cat.cogs)} />
        <Stat label="Доля в обороте" value={fmtPct(cat.share)} />
        <Stat label="Оборачиваемость" value={`${cat.turnover.toFixed(1).replace('.', ',')} дн`} />
      </div>

      <div style={{
        background: 'var(--surface-panel)', border: '1px solid var(--border)',
        borderRadius: 'var(--radius-lg)', padding: 16,
      }}>
        <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--fg-secondary)', marginBottom: 8 }}>Тренд за 12 месяцев</div>
        <Sparkline data={cat.trend} width={520} height={64} />
      </div>

      <div style={{ background: 'var(--surface-panel)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', overflow: 'hidden' }}>
        <table style={{ width: '100%', fontSize: 13 }}>
          <thead style={{ background: 'var(--surface-panel-elevated)', color: 'var(--fg-muted)' }}>
            <tr>
              <th style={{ textAlign: 'left',  padding: '10px 12px', fontWeight: 500 }}>SKU</th>
              <th style={{ textAlign: 'right', padding: '10px 12px', fontWeight: 500 }}>Выручка 30 д</th>
              <th style={{ textAlign: 'right', padding: '10px 12px', fontWeight: 500 }}>Шт 30 д</th>
              <th style={{ textAlign: 'left',  padding: '10px 12px', fontWeight: 500 }}>Остаток</th>
              <th style={{ textAlign: 'left',  padding: '10px 12px', fontWeight: 500 }}>Тренд</th>
              <th style={{ textAlign: 'center', padding: '10px 12px', fontWeight: 500 }}>ABC</th>
              <th style={{ textAlign: 'center', padding: '10px 12px', fontWeight: 500 }}>XYZ</th>
              <th style={{ textAlign: 'left',  padding: '10px 12px', fontWeight: 500 }}>Заказ</th>
            </tr>
          </thead>
          <tbody>
            {catSkus.length === 0 && (
              <tr><td colSpan={8} style={{ padding: 24, textAlign: 'center', color: 'var(--fg-muted)' }}>В этой категории пока нет SKU в фикстуре.</td></tr>
            )}
            {catSkus.map((s) => (
              <tr key={s.id} style={{ borderTop: '1px solid var(--border)' }}>
                <td style={{ padding: '10px 12px' }}>
                  <div style={{ fontWeight: 500, color: 'var(--fg-primary)' }}>{s.name}</div>
                  <div style={{ fontSize: 11, color: 'var(--fg-muted)' }}>{s.id} · {s.supplier}</div>
                </td>
                <td style={{ padding: '10px 12px', textAlign: 'right', color: 'var(--fg-primary)' }}>{fmtRubShort(s.sales30d)}</td>
                <td style={{ padding: '10px 12px', textAlign: 'right', color: 'var(--fg-secondary)' }}>{s.units30d}</td>
                <td style={{ padding: '10px 12px' }}><StockBar days={s.stockDays} /></td>
                <td style={{ padding: '10px 12px' }}><Sparkline data={s.spark} /></td>
                <td style={{ padding: '10px 12px', textAlign: 'center' }}><AbcBadge v={s.abc} /></td>
                <td style={{ padding: '10px 12px', textAlign: 'center' }}><XyzBadge v={s.xyz} /></td>
                <td style={{ padding: '10px 12px' }}><SuggestedOrder qty={s.suggestedOrder} velocity={s.units30d} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
