import { Link } from 'react-router-dom';

export default function NotFoundScreen() {
  return (
    <div style={{ padding: 48, textAlign: 'center', color: 'var(--fg-muted)' }}>
      <div style={{ fontSize: 56, fontWeight: 700, color: 'var(--fg-secondary)' }}>404</div>
      <div style={{ marginTop: 8, fontSize: 16 }}>Страница не найдена</div>
      <Link to="/dashboard" style={{
        display: 'inline-block', marginTop: 16,
        background: 'var(--accent-600)', color: '#FFFFFF',
        padding: '8px 14px', borderRadius: 'var(--radius-md)', fontWeight: 600, fontSize: 13,
      }}>На дашборд</Link>
    </div>
  );
}
