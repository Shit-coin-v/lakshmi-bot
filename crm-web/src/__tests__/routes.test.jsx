import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import App from '../App.jsx';
import { SCREEN_TITLES } from '../routes.jsx';

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
});
