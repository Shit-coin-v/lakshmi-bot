import { useState } from 'react';
import { fmtDate } from '../utils/format.js';
import { ScreenSkeleton } from '../components/ScreenSkeleton.jsx';
import { ErrorBanner } from '../components/ErrorBanner.jsx';
import { useCampaigns } from '../hooks/useCampaigns.js';

const TABS = [
  { id: 'all',      label: 'Все' },
  { id: 'active',   label: 'Активные' },
  { id: 'draft',    label: 'Черновики' },
  { id: 'finished', label: 'Завершённые' },
];

const STATUS_LABEL = {
  active:   'Активна',
  draft:    'Черновик',
  finished: 'Завершена',
};

const STATUS_COLOR = {
  active:   'var(--success)',
  draft:    'var(--fg-muted)',
  finished: 'var(--fg-secondary)',
};

export default function CampaignsScreen() {
  const [tab, setTab] = useState('all');

  const apiStatus = tab === 'all' ? undefined : tab;
  const { data, isLoading, error, refetch } = useCampaigns({ status: apiStatus });
  if (isLoading) return <ScreenSkeleton variant="table" />;
  if (error)     return <ErrorBanner title="Не удалось загрузить кампании" error={error} onRetry={refetch} />;
  const list = data.results;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ display: 'flex', gap: 4, padding: 4, background: 'var(--surface-panel-elevated)', borderRadius: 'var(--radius-md)', alignSelf: 'flex-start' }}>
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            style={{
              padding: '6px 14px', borderRadius: 'var(--radius-sm)',
              border: 'none',
              background: tab === t.id ? 'var(--surface-panel)' : 'transparent',
              color: tab === t.id ? 'var(--fg-primary)' : 'var(--fg-secondary)',
              fontSize: 13, fontWeight: 500, cursor: 'pointer',
            }}
          >{t.label}</button>
        ))}
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 12 }}>
        {list.map((c) => (
          <div
            key={c.id}
            style={{
              background: 'var(--surface-panel)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-lg)',
              padding: 16,
              display: 'flex', flexDirection: 'column', gap: 8,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <div style={{ flex: 1, fontSize: 15, fontWeight: 600, color: 'var(--fg-primary)' }}>{c.name}</div>
              <span style={{
                fontSize: 11, fontWeight: 600, padding: '2px 8px', borderRadius: 999,
                background: 'var(--surface-panel-elevated)', color: STATUS_COLOR[c.status] || 'var(--fg-muted)',
              }}>{STATUS_LABEL[c.status] || c.status}</span>
            </div>
            <div style={{ fontSize: 12, color: 'var(--fg-muted)' }}>{c.id} · {c.slug}</div>
            <div style={{ fontSize: 13, color: 'var(--fg-secondary)' }}>{c.rules}</div>
            <div style={{ display: 'flex', gap: 16, fontSize: 12, color: 'var(--fg-muted)', marginTop: 4 }}>
              <span>Сегмент: <span style={{ color: 'var(--fg-secondary)' }}>{c.segment}</span></span>
              <span>Охват: <span style={{ color: 'var(--fg-secondary)' }}>{c.reach.toLocaleString('ru-RU')}</span></span>
              <span>Использовано: <span style={{ color: 'var(--fg-secondary)' }}>{c.used.toLocaleString('ru-RU')}</span></span>
            </div>
            <div style={{ fontSize: 12, color: 'var(--fg-muted)' }}>
              Период: {fmtDate(c.period.from)} – {fmtDate(c.period.to)}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
