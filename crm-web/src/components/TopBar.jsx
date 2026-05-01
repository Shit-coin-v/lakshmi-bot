import { Icon } from './Icon.jsx';

export function TopBar({ title, breadcrumbs = [], primaryAction }) {
  return (
    <header style={{
      height: 'var(--topbar-h)',
      borderBottom: '1px solid var(--border)',
      background: 'var(--surface-page)',
      display: 'flex', alignItems: 'center', padding: '0 24px', gap: 16,
      flexShrink: 0,
    }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 2, flex: 1, minWidth: 0 }}>
        {breadcrumbs.length > 0 && (
          <div style={{ fontSize: 12, color: 'var(--fg-muted)' }}>
            {breadcrumbs.join(' / ')}
          </div>
        )}
        <h1 style={{ fontSize: 16, fontWeight: 600, color: 'var(--fg-primary)', letterSpacing: '-0.01em' }}>
          {title}
        </h1>
      </div>
      {primaryAction && (
        <button style={{
          display: 'inline-flex', alignItems: 'center', gap: 8,
          background: 'var(--accent-600)', color: '#FFFFFF',
          border: 'none', borderRadius: 'var(--radius-md)',
          padding: '8px 14px', fontSize: 13, fontWeight: 600, cursor: 'pointer',
        }}>
          {primaryAction.icon && <Icon name={primaryAction.icon} size={16} />}
          {primaryAction.label}
        </button>
      )}
      <button aria-label="Профиль" style={{
        background: 'var(--surface-panel)', border: '1px solid var(--border)',
        borderRadius: 999, width: 32, height: 32, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer',
      }}>
        <Icon name="user" size={16} />
      </button>
    </header>
  );
}

export default TopBar;
