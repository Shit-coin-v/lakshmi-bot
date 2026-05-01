import { Icon } from './Icon.jsx';

export function EmptyState({ title, hint, onBack, backLabel = '← Назад' }) {
  return (
    <div style={{
      background: 'var(--surface-panel)',
      border: '1px solid var(--border)',
      borderRadius: 'var(--radius-lg)',
      padding: 48, textAlign: 'center', color: 'var(--fg-muted)',
    }}>
      <Icon name="search-x" size={32} />
      <div style={{ marginTop: 12, fontSize: 16, fontWeight: 500, color: 'var(--fg-secondary)' }}>{title}</div>
      {hint && <div style={{ marginTop: 4, fontSize: 13 }}>{hint}</div>}
      {onBack && (
        <button onClick={onBack} style={{
          marginTop: 16, background: 'var(--accent-600)', color: '#FFFFFF',
          border: 'none', borderRadius: 'var(--radius-md)',
          padding: '8px 14px', fontSize: 13, fontWeight: 600, cursor: 'pointer',
        }}>{backLabel}</button>
      )}
    </div>
  );
}

export default EmptyState;
