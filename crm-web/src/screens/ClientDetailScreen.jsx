import { useNavigate, useParams, Link } from 'react-router-dom';
import { Stat } from '../components/primitives/Stat.jsx';
import { KV } from '../components/primitives/KV.jsx';
import { Toggle } from '../components/primitives/Toggle.jsx';
import { ActiveCampaign } from '../components/primitives/ActiveCampaign.jsx';
import { EmptyState } from '../components/EmptyState.jsx';
import clients from '../fixtures/clients.js';
import orders from '../fixtures/orders.js';
import campaigns from '../fixtures/campaigns.js';
import { fmtRub, fmtDate } from '../utils/format.js';

export default function ClientDetailScreen() {
  const { id } = useParams();
  const navigate = useNavigate();
  const client = clients.find((c) => c.id === id);

  if (!client) {
    return (
      <EmptyState
        title="Клиент не найден"
        hint={`ID ${id} отсутствует в фикстурах`}
        onBack={() => navigate('/clients')}
        backLabel="← К списку клиентов"
      />
    );
  }

  const myOrders = orders.filter((o) => o.clientId === client.id);
  const activeForClient = campaigns.filter((c) => c.status === 'active' && c.segment === client.rfmSegment);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <Link to="/clients" style={{ color: 'var(--fg-muted)', fontSize: 12 }}>← Все клиенты</Link>
      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <div style={{
          width: 56, height: 56, borderRadius: 999,
          background: 'var(--accent-soft)', color: 'var(--accent-600)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 22, fontWeight: 600,
        }}>{client.name.split(' ').map((s) => s[0]).join('').slice(0, 2)}</div>
        <div>
          <div style={{ fontSize: 18, fontWeight: 600, color: 'var(--fg-primary)' }}>{client.name}</div>
          <div style={{ fontSize: 12, color: 'var(--fg-muted)' }}>{client.id} · {client.rfmSegment}</div>
        </div>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
        <Stat label="LTV" value={fmtRub(client.ltv)} />
        <Stat label="Бонусы" value={fmtRub(client.bonus)} />
        <Stat label="Заказов всего" value={client.purchaseCount ?? myOrders.length} />
        <Stat label="Последний заказ" value={fmtDate(client.lastOrder)} />
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        <div style={{ background: 'var(--surface-panel)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', padding: 16 }}>
          <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--fg-secondary)', marginBottom: 8 }}>Контакты</div>
          <KV k="Телефон" v={client.phone} mono />
          <KV k="Email" v={client.email || '—'} />
          <KV k="Telegram ID" v={client.telegramId || '—'} mono />
          <KV k="Теги" v={(client.tags || []).join(', ') || '—'} />
        </div>
        <div style={{ background: 'var(--surface-panel)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', padding: 16 }}>
          <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--fg-secondary)', marginBottom: 8 }}>Уведомления</div>
          <Toggle label="Push" on={!!client.preferences?.push} />
          <Toggle label="Telegram" on={!!client.preferences?.telegram} />
          <Toggle label="Email" on={!!client.preferences?.email} />
          <Toggle label="SMS" on={!!client.preferences?.sms} />
        </div>
      </div>
      {activeForClient.length > 0 && (
        <div style={{ background: 'var(--surface-panel)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', padding: 16 }}>
          <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--fg-secondary)', marginBottom: 8 }}>Активные кампании</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {activeForClient.map((c) => <ActiveCampaign key={c.id} name={c.name} hint={c.rules} />)}
          </div>
        </div>
      )}
      <div style={{ background: 'var(--surface-panel)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', padding: 16 }}>
        <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--fg-secondary)', marginBottom: 8 }}>История заказов</div>
        {myOrders.length === 0 ? (
          <div style={{ color: 'var(--fg-muted)', fontSize: 13 }}>Нет заказов</div>
        ) : (
          <table style={{ width: '100%', fontSize: 13 }}>
            <thead style={{ color: 'var(--fg-muted)' }}>
              <tr>
                <th style={{ textAlign: 'left', padding: '6px 0', fontWeight: 500 }}>Заказ</th>
                <th style={{ textAlign: 'left', padding: '6px 0', fontWeight: 500 }}>Дата</th>
                <th style={{ textAlign: 'right', padding: '6px 0', fontWeight: 500 }}>Сумма</th>
                <th style={{ textAlign: 'left', padding: '6px 0', fontWeight: 500 }}>Статус</th>
              </tr>
            </thead>
            <tbody>
              {myOrders.map((o) => (
                <tr key={o.id} style={{ borderTop: '1px solid var(--border)' }}>
                  <td style={{ padding: '8px 0', color: 'var(--fg-primary)' }}>{o.id}</td>
                  <td style={{ padding: '8px 0', color: 'var(--fg-secondary)' }}>{fmtDate(o.date)}</td>
                  <td style={{ padding: '8px 0', textAlign: 'right', color: 'var(--fg-primary)' }}>{fmtRub(o.amount)}</td>
                  <td style={{ padding: '8px 0', color: 'var(--fg-secondary)' }}>{o.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
