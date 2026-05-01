import { useMemo, useState } from 'react';
import orders from '../fixtures/orders.js';
import { fmtRub, fmtDate } from '../utils/format.js';

const STATUSES = ['Все', 'new', 'accepted', 'assembly', 'ready', 'delivery', 'arrived', 'completed', 'canceled'];
const PURCHASE_TYPES = ['Все', 'delivery', 'pickup', 'in_store'];

const STATUS_COLOR = {
  new: 'var(--accent-600)',
  accepted: 'var(--accent-600)',
  assembly: 'var(--warning)',
  ready: 'var(--success)',
  delivery: 'var(--accent-700)',
  arrived: 'var(--success)',
  completed: 'var(--fg-muted)',
  canceled: 'var(--danger)',
};

const STATUS_LABEL = {
  new: 'Новый',
  accepted: 'Принят',
  assembly: 'Сборка',
  ready: 'Готов',
  delivery: 'В доставке',
  arrived: 'Прибыл',
  completed: 'Завершён',
  canceled: 'Отменён',
};

export default function OrdersScreen() {
  const [status, setStatus] = useState('Все');
  const [pType, setPType] = useState('Все');

  const list = useMemo(() => orders.filter((o) => {
    if (status !== 'Все' && o.status !== status) return false;
    if (pType !== 'Все' && o.purchaseType !== pType) return false;
    return true;
  }), [status, pType]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ display: 'flex', gap: 8 }}>
        <select value={status} onChange={(e) => setStatus(e.target.value)} style={selectStyle}>
          {STATUSES.map((s) => <option key={s} value={s}>{STATUS_LABEL[s] || s}</option>)}
        </select>
        <select value={pType} onChange={(e) => setPType(e.target.value)} style={selectStyle}>
          {PURCHASE_TYPES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>
      <div style={{ background: 'var(--surface-panel)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', overflow: 'hidden' }}>
        <table style={{ width: '100%', fontSize: 13 }}>
          <thead style={{ background: 'var(--surface-panel-elevated)', color: 'var(--fg-muted)' }}>
            <tr>
              {['Заказ', 'Дата', 'Клиент', 'Сумма', 'Статус', 'Способ'].map((h) => (
                <th key={h} style={{ textAlign: 'left', padding: '10px 12px', fontWeight: 500 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {list.map((o) => (
              <tr key={o.id} style={{ borderTop: '1px solid var(--border)' }}>
                <td style={{ padding: '10px 12px', color: 'var(--fg-primary)' }}>{o.id}</td>
                <td style={{ padding: '10px 12px', color: 'var(--fg-secondary)' }}>{fmtDate(o.date)}</td>
                <td style={{ padding: '10px 12px', color: 'var(--fg-primary)' }}>{o.clientName}</td>
                <td style={{ padding: '10px 12px', color: 'var(--fg-primary)' }}>{fmtRub(o.amount)}</td>
                <td style={{ padding: '10px 12px' }}>
                  <span style={{
                    fontSize: 11, fontWeight: 600, padding: '2px 8px', borderRadius: 999,
                    background: 'var(--surface-panel-elevated)',
                    color: STATUS_COLOR[o.status] || 'var(--fg-muted)',
                  }}>{STATUS_LABEL[o.status] || o.status}</span>
                </td>
                <td style={{ padding: '10px 12px', color: 'var(--fg-secondary)' }}>{o.purchaseType}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const selectStyle = {
  height: 36, padding: '0 12px',
  background: 'var(--surface-input)', border: '1px solid var(--border)',
  borderRadius: 'var(--radius-md)', color: 'var(--fg-primary)',
};
