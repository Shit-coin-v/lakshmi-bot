import { useState, useRef, useEffect } from 'react';
import { Icon } from './Icon.jsx';
import { useAuthContext } from '../auth/AuthProvider.jsx';
import { useLogout } from '../hooks/useAuth.js';
import { useNavigate } from 'react-router-dom';

export function TopBar({ title, breadcrumbs = [], primaryAction }) {
  const { user } = useAuthContext();
  const logout = useLogout();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    function onClickOutside(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener('mousedown', onClickOutside);
    return () => document.removeEventListener('mousedown', onClickOutside);
  }, []);

  function handleLogout() {
    logout.mutate(undefined, {
      onSuccess: () => navigate('/login', { replace: true }),
    });
  }

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
          <div style={{ fontSize: 12, color: 'var(--fg-muted)' }}>{breadcrumbs.join(' / ')}</div>
        )}
        <h1 style={{ fontSize: 16, fontWeight: 600, color: 'var(--fg-primary)', letterSpacing: '-0.01em' }}>{title}</h1>
      </div>
      {primaryAction && (
        <button style={{
          display: 'inline-flex', alignItems: 'center', gap: 8,
          background: 'var(--accent-600)', color: '#FFFFFF', border: 'none',
          borderRadius: 'var(--radius-md)', padding: '8px 14px', fontSize: 13, fontWeight: 600, cursor: 'pointer',
        }}>
          {primaryAction.icon && <Icon name={primaryAction.icon} size={16} />}
          {primaryAction.label}
        </button>
      )}
      <div ref={ref} style={{ position: 'relative' }}>
        <button
          aria-label="Профиль"
          onClick={() => setOpen((v) => !v)}
          style={{
            background: 'var(--surface-panel)', border: '1px solid var(--border)',
            borderRadius: 999, width: 32, height: 32, display: 'inline-flex',
            alignItems: 'center', justifyContent: 'center', cursor: 'pointer',
          }}
        >
          <Icon name="user" size={16} />
        </button>
        {open && (
          <div style={{
            position: 'absolute', top: 36, right: 0, zIndex: 10,
            width: 220, background: 'var(--surface-panel)',
            border: '1px solid var(--border)', borderRadius: 'var(--radius-md)',
            padding: 4, boxShadow: '0 4px 16px rgba(0,0,0,0.4)',
          }}>
            {user && (
              <div style={{ padding: '8px 12px', borderBottom: '1px solid var(--border)' }}>
                <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--fg-primary)' }}>{user.name}</div>
                <div style={{ fontSize: 11, color: 'var(--fg-muted)' }}>{user.email}</div>
              </div>
            )}
            <button
              onClick={handleLogout}
              disabled={logout.isPending}
              style={{
                width: '100%', padding: '8px 12px',
                background: 'transparent', border: 'none', textAlign: 'left',
                color: 'var(--fg-primary)', fontSize: 13, cursor: 'pointer',
                borderRadius: 'var(--radius-sm)',
              }}
            >
              {logout.isPending ? 'Выход…' : 'Выйти'}
            </button>
          </div>
        )}
      </div>
    </header>
  );
}

export default TopBar;
