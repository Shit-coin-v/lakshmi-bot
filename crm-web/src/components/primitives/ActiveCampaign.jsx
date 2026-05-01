import { Icon } from '../Icon.jsx';

export function ActiveCampaign({ name, hint }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 10,
      padding: '10px 12px',
      borderRadius: 'var(--radius-md)',
      background: 'var(--surface-panel-elevated)',
      border: '1px solid var(--border)',
    }}>
      <Icon name="megaphone" size={16} style={{ color: 'var(--accent-600)' }} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--fg-primary)' }}>{name}</div>
        {hint && <div style={{ fontSize: 11, color: 'var(--fg-muted)' }}>{hint}</div>}
      </div>
    </div>
  );
}

export default ActiveCampaign;
