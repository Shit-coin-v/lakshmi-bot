import { Icon } from './Icon.jsx';

export function Placeholder({ name }) {
  return (
    <div style={{
      background: 'var(--surface-panel)',
      border: '1px dashed var(--border-strong)',
      borderRadius: 'var(--radius-lg)',
      padding: 48, textAlign: 'center', color: 'var(--fg-muted)',
    }}>
      <Icon name="construction" size={32} />
      <div style={{ marginTop: 12, fontSize: 16, fontWeight: 500, color: 'var(--fg-secondary)' }}>
        Раздел «{name}»
      </div>
      <div style={{ marginTop: 4, fontSize: 13 }}>В разработке.</div>
    </div>
  );
}

export default Placeholder;
