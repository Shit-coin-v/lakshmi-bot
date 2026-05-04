import { Stat } from '../components/primitives/Stat.jsx';
import { BarChart } from '../components/primitives/BarChart.jsx';
import { ActiveCampaign } from '../components/primitives/ActiveCampaign.jsx';
import { ScreenSkeleton } from '../components/ScreenSkeleton.jsx';
import { ErrorBanner } from '../components/ErrorBanner.jsx';
import { useDashboard } from '../hooks/useDashboard.js';
import { fmtRubShort } from '../utils/format.js';

function fmtKpi(kpi) {
  if (kpi.format === 'rubShort') return fmtRubShort(kpi.value);
  return new Intl.NumberFormat('ru-RU').format(kpi.value);
}

export default function DashboardScreen() {
  const { data, isLoading, error, refetch } = useDashboard();

  if (isLoading) return <ScreenSkeleton variant="dashboard" />;
  if (error)     return <ErrorBanner title="Не удалось загрузить дашборд" error={error} onRetry={refetch} />;

  const barData = (data.daily || []).map((d) => ({
    label: d.date.slice(8, 10),
    value: d.revenue,
  }));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
        {data.kpis.map((k) => (
          <Stat key={k.id} label={k.label} value={fmtKpi(k)} delta={k.delta} deltaLabel={k.deltaLabel} />
        ))}
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16 }}>
        <div style={{ background: 'var(--surface-panel)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', padding: 16 }}>
          <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--fg-secondary)', marginBottom: 12 }}>Заказы за 14 дней</div>
          <BarChart data={barData} />
        </div>
        <div style={{ background: 'var(--surface-panel)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', padding: 16 }}>
          <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--fg-secondary)', marginBottom: 12 }}>RFM-сегменты</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: 13 }}>
            {(data.rfmSegments || []).map((s) => (
              <div key={s.name} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span style={{ flex: 1, color: 'var(--fg-primary)' }}>{s.name}</span>
                <span style={{ color: 'var(--fg-secondary)', fontVariantNumeric: 'tabular-nums' }}>{s.count.toLocaleString('ru-RU')}</span>
                <span style={{ color: 'var(--fg-muted)', width: 48, textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>{s.share}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>
      <div style={{ background: 'var(--surface-panel)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', padding: 16 }}>
        <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--fg-secondary)', marginBottom: 12 }}>Активные кампании</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {(data.activeCampaigns || []).map((c, i) => (
            <ActiveCampaign key={i} name={c.name} hint={c.hint} />
          ))}
        </div>
      </div>
    </div>
  );
}
