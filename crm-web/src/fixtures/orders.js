// Портировано из reference FIXTURES.orders.
// Маппинг: id(num) → id('ORD-30412'), customer → clientName, total → amount,
// created_at('DD.MM HH:MM') → date(ISO 2026), payment + courier — extra поля.
// Поскольку у всех заказов есть address+courier, purchaseType='delivery'.

const NAME_TO_CLIENT_ID = {
  'Сардаана Николаева':  'LC-001042',
  'Айсен Гаврильев':     'LC-001041',
  'Туйаара Винокурова':  'LC-001040',
  'Семён Слепцов':       'LC-001039',
  'Долгуяна Афанасьева': 'LC-001038',
  'Прокопий Захаров':    'LC-001037',
  'Кюнняй Готовцева':    'LC-001036',
  'Михаил Никифоров':    'LC-001035',
};

const SOURCE = [
  { id: 30412, customer: 'Сардаана Николаева',  address: 'ул. Лермонтова, 24, кв. 12',     total: 2340, status: 'assembly',  payment: 'sbp',          created_at: '15.04 14:32', courier: '—',         items: 7 },
  { id: 30411, customer: 'Айсен Гаврильев',     address: 'ул. Дзержинского, 1',             total: 890,  status: 'delivery',  payment: 'card_courier', created_at: '15.04 14:18', courier: 'Виктор М.', items: 3 },
  { id: 30410, customer: 'Долгуяна Афанасьева', address: 'пр. Ленина, 78, кв. 44',          total: 5610, status: 'arrived',   payment: 'cash',         created_at: '15.04 13:51', courier: 'Артур К.',  items: 12 },
  { id: 30409, customer: 'Кюнняй Готовцева',    address: 'ул. Орджоникидзе, 9',             total: 1230, status: 'ready',     payment: 'sbp',          created_at: '15.04 13:22', courier: '—',         items: 4 },
  { id: 30408, customer: 'Туйаара Винокурова',  address: 'ул. Кулаковского, 12, кв. 7',     total: 1450, status: 'new',       payment: 'card_courier', created_at: '15.04 13:08', courier: '—',         items: 5 },
  { id: 30407, customer: 'Семён Слепцов',       address: 'ул. Петровского, 33',             total: 720,  status: 'completed', payment: 'cash',         created_at: '15.04 12:40', courier: 'Виктор М.', items: 2 },
  { id: 30406, customer: 'Прокопий Захаров',    address: 'ул. Аммосова, 15',                total: 410,  status: 'canceled',  payment: 'sbp',          created_at: '15.04 12:11', courier: '—',         items: 1 },
];

function toIso(short) {
  // '15.04 14:32' → '2026-04-15T14:32:00'
  const [date, time] = short.split(' ');
  const [d, m] = date.split('.');
  return `2026-${m}-${d}T${time}:00`;
}

export default SOURCE.map((o) => ({
  id: `ORD-${o.id}`,
  date: toIso(o.created_at),
  clientId: NAME_TO_CLIENT_ID[o.customer] || null,
  clientName: o.customer,
  amount: o.total,
  status: o.status,
  purchaseType: 'delivery',
  items: o.items,
  address: o.address,
  payment: o.payment,
  courier: o.courier,
}));
