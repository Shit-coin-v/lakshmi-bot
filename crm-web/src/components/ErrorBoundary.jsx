import { Component } from 'react';

export class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }
  static getDerivedStateFromError(error) { return { error }; }
  componentDidCatch(error, info) { console.error('[ErrorBoundary]', error, info); }
  render() {
    if (this.state.error) {
      return (
        <div style={{ padding: 48, color: 'var(--fg-primary)', background: 'var(--surface-page)', minHeight: '100vh' }}>
          <h1 style={{ fontSize: 18, marginBottom: 8 }}>Что-то пошло не так</h1>
          <pre style={{ background: 'var(--surface-panel)', padding: 16, borderRadius: 8, color: 'var(--danger)', overflow: 'auto', fontSize: 12 }}>
            {String(this.state.error?.stack || this.state.error)}
          </pre>
          <button onClick={() => location.reload()} style={{
            marginTop: 16, background: 'var(--accent-600)', color: '#FFFFFF',
            border: 'none', borderRadius: 'var(--radius-md)', padding: '8px 14px', cursor: 'pointer',
          }}>Перезагрузить</button>
        </div>
      );
    }
    return this.props.children;
  }
}

export default ErrorBoundary;
