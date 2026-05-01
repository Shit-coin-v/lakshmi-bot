import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import App from '../App.jsx';
import { SCREEN_TITLES } from '../routes.jsx';
import dashboard from '../fixtures/dashboard.js';
import clients from '../fixtures/clients.js';
import orders from '../fixtures/orders.js';

const URLS_TO_CHECK = [
  '/dashboard',
  '/clients',
  '/clients/123',
  '/orders',
  '/campaigns',
  '/rfm',
  '/broadcasts',
  '/catalog',
  '/categories',
  '/categories/some-slug',
  '/abc-xyz',
  '/analytics',
];

function titleFor(url) {
  if (url === '/clients/123') return SCREEN_TITLES['/clients/:id'].title;
  if (url === '/categories/some-slug') return SCREEN_TITLES['/categories/:slug'].title;
  return SCREEN_TITLES[url]?.title ?? '';
}

describe('CRM routing smoke', () => {
  it('renders / as redirect to /dashboard', () => {
    render(<MemoryRouter initialEntries={['/']}><App /></MemoryRouter>);
    expect(screen.getByRole('heading', { level: 1 }).textContent).toBe(SCREEN_TITLES['/dashboard'].title);
  });

  for (const url of URLS_TO_CHECK) {
    it(`renders ${url} without crash and shows correct title`, () => {
      render(<MemoryRouter initialEntries={[url]}><App /></MemoryRouter>);
      expect(screen.getByRole('heading', { level: 1 }).textContent).toBe(titleFor(url));
    });
  }

  it('renders 404 on unknown URL', () => {
    render(<MemoryRouter initialEntries={['/no-such-thing']}><App /></MemoryRouter>);
    expect(screen.getByText('404')).toBeInTheDocument();
  });

  it('dashboard shows first KPI label', () => {
    render(<MemoryRouter initialEntries={['/dashboard']}><App /></MemoryRouter>);
    expect(screen.getByText(dashboard.kpis[0].label)).toBeInTheDocument();
  });

  it('clients screen shows first client name', () => {
    render(<MemoryRouter initialEntries={['/clients']}><App /></MemoryRouter>);
    expect(screen.getByText(clients[0].name)).toBeInTheDocument();
  });

  it('client detail shows EmptyState for unknown id', () => {
    render(<MemoryRouter initialEntries={['/clients/no-such-client']}><App /></MemoryRouter>);
    expect(screen.getByText('Клиент не найден')).toBeInTheDocument();
  });

  it('client detail shows real client name', () => {
    const c = clients[0];
    render(<MemoryRouter initialEntries={[`/clients/${c.id}`]}><App /></MemoryRouter>);
    expect(screen.getAllByText(c.name).length).toBeGreaterThan(0);
  });

  it('orders screen shows first order id', () => {
    render(<MemoryRouter initialEntries={['/orders']}><App /></MemoryRouter>);
    expect(screen.getByText(orders[0].id)).toBeInTheDocument();
  });
});
