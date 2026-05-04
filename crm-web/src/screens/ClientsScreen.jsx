import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Icon } from '../components/Icon.jsx';
import { ScreenSkeleton } from '../components/ScreenSkeleton.jsx';
import { ErrorBanner } from '../components/ErrorBanner.jsx';
import { useClients } from '../hooks/useClients.js';
import { fmtRub, fmtDate } from '../utils/format.js';

const SEGMENTS = ['Все', 'Чемпионы', 'Лояльные', 'Новички', 'Спящие', 'Рискуют уйти', 'Потерянные'];
const PAGE_SIZE = 50;

export default function ClientsScreen() {
  const navigate = useNavigate();
  const [q, setQ] = useState('');
  const [seg, setSeg] = useState('Все');
  const [page, setPage] = useState(1);

  const { data, isLoading, error, refetch } = useClients({
    q: q.trim() || undefined,
    segment: seg !== 'Все' ? seg : undefined,
    page,
    pageSize: PAGE_SIZE,
  });

  if (isLoading) return <ScreenSkeleton variant="table" />;
  if (error)     return <ErrorBanner title="Не удалось загрузить клиентов" error={error} onRetry={refetch} />;

  const rows = data.results;
  const pages = data.pagination.totalPages;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ display: 'flex', gap: 8 }}>
        <div style={{ position: 'relative', flex: 1 }}>
          <Icon name="search" size={16} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--fg-muted)' }} />
          <input
            value={q}
            onChange={(e) => { setQ(e.target.value); setPage(1); }}
            placeholder="Поиск по имени, телефону, email…"
            style={{
              width: '100%', height: 36, paddingLeft: 36, paddingRight: 12,
              background: 'var(--surface-input)', border: '1px solid var(--border)',
              borderRadius: 'var(--radius-md)', color: 'var(--fg-primary)',
            }}
          />
        </div>
        <select
          value={seg}
          onChange={(e) => { setSeg(e.target.value); setPage(1); }}
          style={{
            height: 36, padding: '0 12px',
            background: 'var(--surface-input)', border: '1px solid var(--border)',
            borderRadius: 'var(--radius-md)', color: 'var(--fg-primary)',
          }}
        >
          {SEGMENTS.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>
      <div style={{ background: 'var(--surface-panel)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', overflow: 'hidden' }}>
        <table style={{ width: '100%', fontSize: 13 }}>
          <thead style={{ background: 'var(--surface-panel-elevated)', color: 'var(--fg-muted)' }}>
            <tr>
              <th style={{ textAlign: 'left',  padding: '10px 12px', fontWeight: 500 }}>Клиент</th>
              <th style={{ textAlign: 'left',  padding: '10px 12px', fontWeight: 500 }}>Сегмент</th>
              <th style={{ textAlign: 'right', padding: '10px 12px', fontWeight: 500 }}>Бонусы</th>
              <th style={{ textAlign: 'right', padding: '10px 12px', fontWeight: 500 }}>LTV</th>
              <th style={{ textAlign: 'left',  padding: '10px 12px', fontWeight: 500 }}>Последний заказ</th>
              <th style={{ textAlign: 'left',  padding: '10px 12px', fontWeight: 500 }}>Теги</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((c) => (
              <tr key={c.id} onClick={() => navigate(`/clients/${c.id}`)} style={{ cursor: 'pointer', borderTop: '1px solid var(--border)' }}>
                <td style={{ padding: '10px 12px' }}>
                  <div style={{ fontWeight: 500, color: 'var(--fg-primary)' }}>{c.name}</div>
                  <div style={{ fontSize: 11, color: 'var(--fg-muted)' }}>{c.phone}</div>
                </td>
                <td style={{ padding: '10px 12px', color: 'var(--fg-secondary)' }}>{c.rfmSegment}</td>
                <td style={{ padding: '10px 12px', textAlign: 'right', color: 'var(--fg-primary)' }}>{fmtRub(c.bonus)}</td>
                <td style={{ padding: '10px 12px', textAlign: 'right', color: 'var(--fg-primary)' }}>{fmtRub(c.ltv)}</td>
                <td style={{ padding: '10px 12px', color: 'var(--fg-secondary)' }}>{c.lastOrder ? fmtDate(c.lastOrder) : '—'}</td>
                <td style={{ padding: '10px 12px', color: 'var(--fg-muted)' }}>{(c.tags || []).join(', ')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {pages > 1 && (
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 4 }}>
          {Array.from({ length: pages }).map((_, i) => (
            <button
              key={i}
              onClick={() => setPage(i + 1)}
              style={{
                width: 32, height: 32, borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border)',
                background: page === i + 1 ? 'var(--accent-600)' : 'var(--surface-panel)',
                color: page === i + 1 ? '#FFFFFF' : 'var(--fg-secondary)',
                cursor: 'pointer', fontSize: 13, fontWeight: 500,
              }}
            >{i + 1}</button>
          ))}
        </div>
      )}
    </div>
  );
}
