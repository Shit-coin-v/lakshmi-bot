import { describe, it, expect } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from '../App.jsx';
import { SCREEN_TITLES } from '../routes.jsx';
import { AuthProvider } from '../auth/AuthProvider.jsx';

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

const URLS_TO_CHECK = [
  '/dashboard',
  '/clients',
  '/clients/LC-000001',
  '/orders',
  '/campaigns',
  '/rfm',
  '/broadcasts',
  '/catalog',
  '/categories',
  '/categories/cat-01',
  '/abc-xyz',
  '/analytics',
];

function titleFor(url) {
  if (url === '/clients/LC-000001') return SCREEN_TITLES['/clients/:id'].title;
  if (url === '/categories/cat-01') return SCREEN_TITLES['/categories/:slug'].title;
  return SCREEN_TITLES[url]?.title ?? '';
}

describe('CRM routing smoke (authenticated)', () => {
  it('redirects / to /dashboard', async () => {
    renderApp(['/']);
    await waitFor(() => expect(screen.getByRole('heading', { level: 1 }).textContent).toBe(SCREEN_TITLES['/dashboard'].title));
  });

  for (const url of URLS_TO_CHECK) {
    it(`renders ${url} with correct title`, async () => {
      renderApp([url]);
      await waitFor(() => expect(screen.getByRole('heading', { level: 1 }).textContent).toBe(titleFor(url)));
    });
  }

  it('renders 404 on unknown URL', async () => {
    renderApp(['/no-such-thing']);
    await waitFor(() => expect(screen.getByText('404')).toBeInTheDocument());
  });
});
