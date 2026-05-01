// Значения портированы из reference FIXTURES.clients (8 записей).
// Маппинг: full_name → name, segment(en) → rfmSegment(ru),
// bonuses → bonus, total_spent → ltv, last_purchase('DD.MM.YYYY') → lastOrder('YYYY-MM-DD').
const SEG_MAP = {
  champions: 'Чемпионы',
  loyal: 'Лояльные',
  new_customer: 'Новички',
  hibernating: 'Спящие',
  at_risk: 'Рискуют уйти',
  lost: 'Потерянные',
};

const SOURCE = [
  { id: 1042, full_name: 'Сардаана Николаева',  card_id: 'LC-001042', telegram_id: 142839201, email: 'sardana@example.ru', phone: '+7 914 222-31-09', bonuses: 1840, segment: 'champions',     last_purchase: '14.04.2026', total_spent: 78420,  purchase_count: 34 },
  { id: 1041, full_name: 'Айсен Гаврильев',     card_id: 'LC-001041', telegram_id: 988421013, email: null,                phone: '+7 924 110-44-77', bonuses: 290,  segment: 'loyal',         last_purchase: '12.04.2026', total_spent: 21030,  purchase_count: 12 },
  { id: 1040, full_name: 'Туйаара Винокурова',  card_id: 'LC-001040', telegram_id: null,      email: 'tuyaara@example.ru', phone: '+7 914 555-12-19', bonuses: 0,    segment: 'new_customer',  last_purchase: '10.04.2026', total_spent: 1450,   purchase_count: 1 },
  { id: 1039, full_name: 'Семён Слепцов',       card_id: 'LC-001039', telegram_id: 449201337, email: null,                phone: '+7 924 901-77-62', bonuses: 540,  segment: 'at_risk',       last_purchase: '02.02.2026', total_spent: 14210,  purchase_count: 8 },
  { id: 1038, full_name: 'Долгуяна Афанасьева', card_id: 'LC-001038', telegram_id: 720104995, email: 'dolguyana@example.ru', phone: '+7 914 220-08-15', bonuses: 3120, segment: 'champions',     last_purchase: '15.04.2026', total_spent: 124800, purchase_count: 51 },
  { id: 1037, full_name: 'Прокопий Захаров',    card_id: 'LC-001037', telegram_id: null,      email: 'prokopy@example.ru',  phone: '+7 914 003-22-44', bonuses: 60,   segment: 'hibernating',   last_purchase: '11.10.2025', total_spent: 4980,   purchase_count: 3 },
  { id: 1036, full_name: 'Кюнняй Готовцева',    card_id: 'LC-001036', telegram_id: 318094221, email: null,                phone: '+7 924 408-19-30', bonuses: 870,  segment: 'loyal',         last_purchase: '09.04.2026', total_spent: 32400,  purchase_count: 18 },
  { id: 1035, full_name: 'Михаил Никифоров',    card_id: 'LC-001035', telegram_id: 871220119, email: 'mikhail.n@example.ru', phone: '+7 914 770-61-08', bonuses: 0,    segment: 'lost',          last_purchase: '24.07.2025', total_spent: 8200,   purchase_count: 5 },
];

function toIso(ddmmyyyy) {
  const [d, m, y] = ddmmyyyy.split('.');
  return `${y}-${m}-${d}`;
}

const tagsFor = (s) => {
  const tags = [];
  if (s.purchase_count >= 30) tags.push('vip');
  if (s.bonuses >= 1000) tags.push('много бонусов');
  if (s.email && s.telegram_id) tags.push('мульти-канал');
  return tags;
};

export default SOURCE.map((s) => ({
  id: s.card_id,
  name: s.full_name,
  phone: s.phone,
  email: s.email || '',
  rfmSegment: SEG_MAP[s.segment] || s.segment,
  bonus: s.bonuses,
  ltv: s.total_spent,
  purchaseCount: s.purchase_count,
  lastOrder: toIso(s.last_purchase),
  tags: tagsFor(s),
  preferences: {
    push: !!s.telegram_id,
    telegram: !!s.telegram_id,
    email: !!s.email,
    sms: false,
  },
  telegramId: s.telegram_id,
}));
