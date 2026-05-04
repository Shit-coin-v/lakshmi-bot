import { http, HttpResponse } from 'msw';

const BASE = '/api/crm';

export const FIXTURE_USER = { id: 1, email: 'manager@lakshmi.ru', name: 'Тестовый Менеджер' };

export const FIXTURE_CLIENT = {
  id: 'LC-000001', name: 'Алиса Иванова', phone: '+7 914 111-22-33',
  email: 'alice@example.ru', rfmSegment: 'Чемпионы',
  bonus: 1500, ltv: 50000, purchaseCount: 12, lastOrder: '2026-04-15', tags: ['vip'],
};

export const FIXTURE_ORDER = {
  id: 'ORD-30001', date: '2026-04-15T14:32:00', clientId: 'LC-000001',
  clientName: 'Алиса Иванова', amount: 2340, status: 'assembly',
  purchaseType: 'delivery', items: 5, address: 'ул. Тестовая, 1', payment: 'sbp', courier: '—',
};

export const FIXTURE_CAMPAIGN = {
  id: 'CMP-1', name: 'Тестовая кампания', slug: 'test', status: 'active',
  period: { from: '2026-04-01', to: '2026-04-30' }, reach: 100, used: 25,
  segment: 'Чемпионы', audience: 'RFM: Чемпионы', rules: '7% бонусов', priority: 200,
};

export const FIXTURE_BROADCAST = {
  id: 'BR-1', sentAt: '2026-04-12T10:00:00', segment: 'Все клиенты',
  channel: 'promo', reach: 100, opened: 50, clicked: 0,
};

export const FIXTURE_CATEGORY = {
  id: 1, slug: 'cat-01', code: '01', name: 'Молочные', skus: 5,
  revenue: 100000, cogs: 70000, share: 8.0, turnover: 5.0,
  abc: 'A', xyz: 'X', trend: [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120],
};

const PAGINATION_HEADERS = { 'X-Total-Count': '1', 'X-Page': '1', 'X-Page-Size': '50' };

export const authedHandlers = [
  http.get(`${BASE}/auth/me/`, () => HttpResponse.json({ user: FIXTURE_USER })),
  http.get(`${BASE}/dashboard/`, () => HttpResponse.json({
    kpis: [
      { id: 'customers', label: 'Активные клиенты', value: 100, delta: 0, deltaLabel: '', format: 'number' },
      { id: 'orders',    label: 'Заказы сегодня',  value: 5,   delta: 0, deltaLabel: '', format: 'number' },
      { id: 'revenue',   label: 'Выручка за неделю', value: 50000, delta: 0, deltaLabel: '', format: 'rubShort' },
      { id: 'bonuses',   label: 'Бонусов на балансе', value: 10000, delta: 0, deltaLabel: '', format: 'number' },
    ],
    daily: [{ date: '2026-04-15', orders: 5, revenue: 50000 }],
    activeCampaigns: [{ id: 'CMP-1', name: 'Тестовая', hint: 'RFM: Чемпионы' }],
    rfmSegments: [{ name: 'Чемпионы', count: 30, share: 30.0 }],
  })),
  // ⚠ Plain array (no {results: ...} wrap) — соответствует контракту HeaderPagination
  http.get(`${BASE}/clients/`, () => HttpResponse.json([FIXTURE_CLIENT], { headers: PAGINATION_HEADERS })),
  http.get(`${BASE}/clients/:cardId/`, ({ params }) => {
    if (params.cardId === 'LC-000001') {
      return HttpResponse.json({
        ...FIXTURE_CLIENT, telegramId: 142839201,
        preferences: { push: true, telegram: true, email: false, sms: false },
        orders: [FIXTURE_ORDER],
        activeCampaigns: [FIXTURE_CAMPAIGN],
      });
    }
    return HttpResponse.json({ detail: 'Клиент не найден' }, { status: 404 });
  }),
  http.get(`${BASE}/orders/`, () => HttpResponse.json([FIXTURE_ORDER], { headers: PAGINATION_HEADERS })),
  http.get(`${BASE}/campaigns/`, () => HttpResponse.json([FIXTURE_CAMPAIGN], { headers: PAGINATION_HEADERS })),
  http.get(`${BASE}/broadcasts/history/`, () => HttpResponse.json([FIXTURE_BROADCAST], { headers: PAGINATION_HEADERS })),
  // Категории: plain array, пагинации нет
  http.get(`${BASE}/categories/`, () => HttpResponse.json([FIXTURE_CATEGORY])),
  http.get(`${BASE}/categories/:slug/`, ({ params }) => {
    if (params.slug === 'cat-01') {
      return HttpResponse.json({ ...FIXTURE_CATEGORY, skuList: [] });
    }
    return HttpResponse.json({ detail: 'Категория не найдена' }, { status: 404 });
  }),
  http.get(`${BASE}/abc-xyz/`, () => HttpResponse.json({
    matrixSku: { AX: 1, AY: 1, AZ: 1, BX: 1, BY: 1, BZ: 1, CX: 1, CY: 1, CZ: 1 },
    matrixRevenue: { AX: 100, AY: 100, AZ: 100, BX: 100, BY: 100, BZ: 100, CX: 100, CY: 100, CZ: 100 },
    matrixShare: { AX: 11.1, AY: 11.1, AZ: 11.1, BX: 11.1, BY: 11.1, BZ: 11.1, CX: 11.1, CY: 11.1, CZ: 11.1 },
  })),
];

export const unauthedHandlers = [
  http.get(`${BASE}/auth/me/`, () => HttpResponse.json({ detail: 'Требуется авторизация' }, { status: 401 })),
];

export const handlers = authedHandlers;
