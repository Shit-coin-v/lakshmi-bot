import { Icon } from './Icon.jsx';

export function ErrorBanner({ title = 'Что-то пошло не так', hint, error, onRetry }) {
  const message = hint || error?.message || error?.body?.detail || '';
  return (
    <div role="alert" style={{
      background: 'var(--surface-panel)',
      border: '1px solid var(--danger)',
      borderRadius: 'var(--radius-lg)',
      padding: 16,
      display: 'flex', alignItems: 'center', gap: 12,
    }}>
      <Icon name="alert-triangle" size={20} style={{ color: 'var(--danger)' }} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 14, fontWeight: 500, color: 'var(--fg-primary)' }}>{title}</div>
        {message && <div style={{ fontSize: 12, color: 'var(--fg-muted)', marginTop: 2 }}>{message}</div>}
      </div>
      {onRetry && (
        <button onClick={onRetry} style={{
          padding: '6px 12px', borderRadius: 'var(--radius-md)',
          background: 'var(--accent-600)', border: 'none', color: '#FFFFFF',
          fontSize: 13, fontWeight: 500, cursor: 'pointer',
        }}>Повторить</button>
      )}
    </div>
  );
}

export default ErrorBanner;
