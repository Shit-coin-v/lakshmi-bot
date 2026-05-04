import lakshmiGlyph from '../assets/lakshmi-glyph.svg';

export function Splash() {
  return (
    <div style={{
      minHeight: '100vh',
      background: 'var(--surface-page)',
      display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center', gap: 16,
    }}>
      <img src={lakshmiGlyph} width="48" height="48" alt="" style={{ borderRadius: 8 }} />
      <div style={{ width: 32, height: 32, border: '3px solid var(--border-strong)', borderTopColor: 'var(--accent-600)', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

export default Splash;
