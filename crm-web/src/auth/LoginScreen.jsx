import { useState } from 'react';
import { useNavigate, useLocation, Navigate } from 'react-router-dom';
import { useLogin } from '../hooks/useAuth.js';
import { useAuthContext } from './AuthProvider.jsx';
import { ForbiddenError, UnauthorizedError } from '../api/client.js';
import lakshmiGlyph from '../assets/lakshmi-glyph.svg';

export function LoginScreen() {
  const { isAuthenticated, isLoading } = useAuthContext();
  const navigate = useNavigate();
  const location = useLocation();
  const next = location.state?.from?.pathname || '/dashboard';
  const login = useLogin();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);

  if (isLoading) return null;
  if (isAuthenticated) return <Navigate to={next} replace />;

  const canSubmit = email.includes('@') && password.length > 0 && !login.isPending;

  function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    login.mutate(
      { email: email.trim(), password },
      {
        onSuccess: () => navigate(next, { replace: true }),
        onError: (err) => {
          if (err instanceof UnauthorizedError) setError('Неверный email или пароль');
          else if (err instanceof ForbiddenError) setError('У этого аккаунта нет доступа в CRM');
          else setError('Ошибка сервера, попробуйте позже');
        },
      },
    );
  }

  return (
    <div style={{
      minHeight: '100vh', background: 'var(--surface-page)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
    }}>
      <form onSubmit={handleSubmit} style={{
        width: 360,
        background: 'var(--surface-panel)', border: '1px solid var(--border)',
        borderRadius: 'var(--radius-lg)', padding: 24,
        display: 'flex', flexDirection: 'column', gap: 16,
      }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
          <img src={lakshmiGlyph} width="48" height="48" alt="" style={{ borderRadius: 8 }} />
          <div style={{ fontSize: 16, fontWeight: 600 }}>Lakshmi CRM</div>
          <div style={{ fontSize: 13, color: 'var(--fg-muted)' }}>Вход для менеджеров</div>
        </div>

        <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <span style={{ fontSize: 12, color: 'var(--fg-muted)' }}>Email</span>
          <input
            type="email"
            autoComplete="username"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="manager@lakshmi.ru"
            style={{
              height: 36, padding: '0 12px',
              background: 'var(--surface-input)', border: '1px solid var(--border)',
              borderRadius: 'var(--radius-md)', color: 'var(--fg-primary)',
            }}
          />
        </label>
        <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <span style={{ fontSize: 12, color: 'var(--fg-muted)' }}>Пароль</span>
          <input
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            style={{
              height: 36, padding: '0 12px',
              background: 'var(--surface-input)', border: '1px solid var(--border)',
              borderRadius: 'var(--radius-md)', color: 'var(--fg-primary)',
            }}
          />
        </label>

        {error && (
          <div role="alert" style={{
            padding: '8px 12px', background: 'rgba(248, 113, 113, 0.12)',
            border: '1px solid var(--danger)', borderRadius: 'var(--radius-md)',
            color: 'var(--danger)', fontSize: 13,
          }}>{error}</div>
        )}

        <button type="submit" disabled={!canSubmit} style={{
          height: 36, padding: '0 14px',
          background: canSubmit ? 'var(--accent-600)' : 'var(--surface-panel-elevated)',
          color: canSubmit ? '#FFFFFF' : 'var(--fg-muted)',
          border: 'none', borderRadius: 'var(--radius-md)',
          fontSize: 13, fontWeight: 600, cursor: canSubmit ? 'pointer' : 'not-allowed',
        }}>
          {login.isPending ? 'Вход…' : 'Войти'}
        </button>
      </form>
    </div>
  );
}

export default LoginScreen;
