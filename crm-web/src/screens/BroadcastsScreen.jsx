import { useState } from 'react';
import { Field } from '../components/primitives/Field.jsx';
import { fmtDate } from '../utils/format.js';
import { ScreenSkeleton } from '../components/ScreenSkeleton.jsx';
import { ErrorBanner } from '../components/ErrorBanner.jsx';
import { useBroadcastHistory } from '../hooks/useBroadcasts.js';

const SEGMENTS = ['Чемпионы', 'Лояльные', 'Новички', 'Спящие', 'Рискуют уйти'];
const CHANNELS = [
  { id: 'push',     label: 'Push (мобильное)' },
  { id: 'telegram', label: 'Telegram' },
  { id: 'email',    label: 'Email' },
];
const CATEGORIES = [
  { id: 'general', label: 'Общая' },
  { id: 'promo',   label: 'Акции и скидки' },
  { id: 'news',    label: 'Новости магазина' },
];

const inputStyle = {
  width: '100%', height: 36, padding: '0 12px',
  background: 'var(--surface-input)', border: '1px solid var(--border)',
  borderRadius: 'var(--radius-md)', color: 'var(--fg-primary)',
  fontSize: 13,
};

export default function BroadcastsScreen() {
  const [segment, setSegment] = useState(SEGMENTS[0]);
  const [channel, setChannel] = useState(CHANNELS[0].id);
  const [category, setCategory] = useState(CATEGORIES[1].id);

  const { data: history, isLoading: histLoading, error: histError, refetch } = useBroadcastHistory();
  const [text, setText] = useState('Завтра в наших магазинах -20% на свежую выпечку с 10:00 до 14:00. Не пропустите!');
  const [schedule, setSchedule] = useState('now');

  function handleSend() {
    // eslint-disable-next-line no-console
    console.log('demo: would send', { segment, channel, category, text, schedule });
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 360px', gap: 16 }}>
      <div style={{
        background: 'var(--surface-panel)', border: '1px solid var(--border)',
        borderRadius: 'var(--radius-lg)', padding: 16,
        display: 'flex', flexDirection: 'column', gap: 16,
      }}>
        <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--fg-primary)' }}>Новая рассылка</div>

        <Field label="Категория">
          <div style={{ display: 'flex', gap: 8 }}>
            {CATEGORIES.map((c) => (
              <button
                key={c.id}
                onClick={() => setCategory(c.id)}
                style={{
                  padding: '8px 14px', borderRadius: 'var(--radius-md)',
                  border: `1px solid ${category === c.id ? 'var(--accent-600)' : 'var(--border)'}`,
                  background: category === c.id ? 'var(--accent-soft)' : 'var(--surface-panel)',
                  color: category === c.id ? 'var(--accent-600)' : 'var(--fg-primary)',
                  fontSize: 13, fontWeight: 500, cursor: 'pointer',
                }}
              >{c.label}</button>
            ))}
          </div>
        </Field>

        <Field label="Сегмент">
          <select value={segment} onChange={(e) => setSegment(e.target.value)} style={inputStyle}>
            {SEGMENTS.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </Field>

        <Field label="Канал">
          <select value={channel} onChange={(e) => setChannel(e.target.value)} style={inputStyle}>
            {CHANNELS.map((c) => <option key={c.id} value={c.id}>{c.label}</option>)}
          </select>
        </Field>

        <Field label="Текст сообщения" hint="Поддерживается HTML: <b>, <i>, <a>. Длина до 4096 символов.">
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={6}
            style={{ ...inputStyle, height: 'auto', padding: 12, lineHeight: '20px', resize: 'vertical' }}
          />
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--fg-muted)', marginTop: 4 }}>
            <span>{CHANNELS.find((c) => c.id === channel)?.label}</span>
            <span>{text.length} / 4096</span>
          </div>
        </Field>

        <Field label="Запуск">
          <div style={{ display: 'flex', gap: 8 }}>
            {[['now', 'Сейчас'], ['scheduled', 'Запланировать…']].map(([k, l]) => (
              <button
                key={k}
                onClick={() => setSchedule(k)}
                style={{
                  padding: '8px 14px', borderRadius: 'var(--radius-md)',
                  border: `1px solid ${schedule === k ? 'var(--accent-600)' : 'var(--border)'}`,
                  background: schedule === k ? 'var(--accent-soft)' : 'var(--surface-panel)',
                  color: schedule === k ? 'var(--accent-600)' : 'var(--fg-primary)',
                  fontSize: 13, fontWeight: 500, cursor: 'pointer',
                }}
              >{l}</button>
            ))}
          </div>
        </Field>

        <div style={{ display: 'flex', gap: 8, paddingTop: 8, borderTop: '1px solid var(--border)' }}>
          <button style={{
            padding: '8px 14px', borderRadius: 'var(--radius-md)',
            background: 'var(--surface-panel-elevated)', border: '1px solid var(--border)',
            color: 'var(--fg-primary)', fontSize: 13, fontWeight: 500, cursor: 'pointer',
          }}>Сохранить черновик</button>
          <div style={{ flex: 1 }} />
          <button
            onClick={handleSend}
            style={{
              padding: '8px 14px', borderRadius: 'var(--radius-md)',
              background: 'var(--accent-600)', border: 'none',
              color: '#FFFFFF', fontSize: 13, fontWeight: 600, cursor: 'pointer',
            }}
          >▶ Отправить рассылку</button>
        </div>
      </div>

      <div style={{ background: 'var(--surface-panel)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', padding: 16 }}>
        <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--fg-primary)', marginBottom: 12 }}>История рассылок</div>
        {histLoading && <ScreenSkeleton variant="table" />}
        {histError && <ErrorBanner title="Не удалось загрузить историю" error={histError} onRetry={refetch} />}
        {history && (
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            {history.results.map((b, i) => (
              <div key={b.id} style={{ padding: '10px 0', borderBottom: i < history.results.length - 1 ? '1px solid var(--border)' : 'none' }}>
                <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--fg-primary)' }}>{b.id} · {b.segment}</div>
                <div style={{ display: 'flex', gap: 12, marginTop: 4, fontSize: 12, color: 'var(--fg-muted)' }}>
                  <span>{fmtDate(b.sentAt)}</span>
                  <span>·</span>
                  <span>{b.channel}</span>
                  <span>·</span>
                  <span>{b.reach.toLocaleString('ru-RU')} → {b.opened.toLocaleString('ru-RU')}</span>
                  <span style={{ color: 'var(--success)', fontWeight: 500 }}>{b.reach > 0 ? Math.round(b.opened / b.reach * 100) : 0}%</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
