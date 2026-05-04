import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { http, HttpResponse } from 'msw';
import App from '../App.jsx';
import { AuthProvider } from '../auth/AuthProvider.jsx';
import { server } from './setup.js';
import { unauthedHandlers, FIXTURE_USER } from './msw_handlers.js';

function renderApp(initialEntries = ['/']) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={initialEntries}>
        <AuthProvider>
          <App />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('Login flow', () => {
  beforeEach(() => {
    server.use(...unauthedHandlers);
  });

  it('shows login screen when unauthenticated', async () => {
    renderApp(['/dashboard']);
    await waitFor(() => expect(screen.getByText('Вход для менеджеров')).toBeInTheDocument());
  });

  it('login success redirects to /dashboard', async () => {
    // Стартуем неавторизованными (beforeEach выставил unauthedHandlers).
    // Рендерим логин, ждём форму, затем добавляем успешный POST-хендлер.
    renderApp(['/login']);
    await waitFor(() => expect(screen.getByText('Вход для менеджеров')).toBeInTheDocument());

    server.use(
      http.post('/api/crm/auth/login/', () => HttpResponse.json({ user: FIXTURE_USER })),
      http.get('/api/crm/auth/me/', () => HttpResponse.json({ user: FIXTURE_USER })),
    );

    fireEvent.change(screen.getByPlaceholderText('manager@lakshmi.ru'), { target: { value: 'manager@lakshmi.ru' } });
    fireEvent.change(document.querySelector('input[type="password"]'), { target: { value: 'secret' } });
    fireEvent.click(screen.getByRole('button', { name: /Войти/i }));

    await waitFor(() => expect(screen.queryByText('Вход для менеджеров')).not.toBeInTheDocument());
  });

  it('shows "Неверный email или пароль" on 401', async () => {
    server.use(http.post('/api/crm/auth/login/', () => HttpResponse.json({ detail: 'Неверный email или пароль' }, { status: 401 })));
    renderApp(['/login']);
    // Ждём, пока форма появится (LoginScreen рендерит null пока isLoading).
    await waitFor(() => expect(screen.getByPlaceholderText('manager@lakshmi.ru')).toBeInTheDocument());
    fireEvent.change(screen.getByPlaceholderText('manager@lakshmi.ru'), { target: { value: 'manager@lakshmi.ru' } });
    fireEvent.change(document.querySelector('input[type="password"]'), { target: { value: 'wrong' } });
    fireEvent.click(screen.getByRole('button', { name: /Войти/i }));

    await waitFor(() => expect(screen.getByRole('alert').textContent).toMatch(/Неверный/));
  });

  it('shows "нет доступа" on 403', async () => {
    server.use(http.post('/api/crm/auth/login/', () => HttpResponse.json({ detail: 'Нет доступа в CRM' }, { status: 403 })));
    renderApp(['/login']);
    // Ждём, пока форма появится (LoginScreen рендерит null пока isLoading).
    await waitFor(() => expect(screen.getByPlaceholderText('manager@lakshmi.ru')).toBeInTheDocument());
    fireEvent.change(screen.getByPlaceholderText('manager@lakshmi.ru'), { target: { value: 'user@lakshmi.ru' } });
    fireEvent.change(document.querySelector('input[type="password"]'), { target: { value: 'secret' } });
    fireEvent.click(screen.getByRole('button', { name: /Войти/i }));

    await waitFor(() => expect(screen.getByRole('alert').textContent).toMatch(/доступ/i));
  });
});
