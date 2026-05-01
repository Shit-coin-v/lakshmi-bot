// Портировано из reference FIXTURES.campaigns.
// Маппинг: name/slug — без изменений, audience → segment (русские RFM-имена),
// reward → rules, start/end → period.from/to (ISO), assigned → reach,
// active → status ('active'|'finished').

const AUDIENCE_TO_SEGMENT = {
  'RFM: Champions':    'Чемпионы',
  'RFM: Loyal':        'Лояльные',
  'RFM: Hibernating':  'Спящие',
  'Сегмент: Постоянные': 'Лояльные',
  'Сегмент: Именинники': 'Все',
};

function toIso(ddmmyyyy) {
  const [d, m, y] = ddmmyyyy.split('.');
  return `${y}-${m}-${d}`;
}

const SOURCE = [
  { id: 7, name: 'Весенний кешбэк 7%', slug: 'spring-cb-7',     audience: 'RFM: Champions',     reward: '7% бонусов',           start: '01.04.2026', end: '30.04.2026', priority: 200, assigned: 412,  used: 287, active: true },
  { id: 6, name: 'Возврат уснувших',   slug: 'wake-hibernating', audience: 'RFM: Hibernating',  reward: '+200 бонусов',         start: '10.04.2026', end: '24.04.2026', priority: 150, assigned: 1840, used: 92,  active: true },
  { id: 5, name: 'Скидка на молочку',  slug: 'dairy-15',        audience: 'Сегмент: Постоянные', reward: 'Скидка 15% на категорию', start: '08.04.2026', end: '22.04.2026', priority: 100, assigned: 2104, used: 880, active: true },
  { id: 4, name: 'День рождения',      slug: 'birthday',        audience: 'Сегмент: Именинники', reward: '+500 бонусов',         start: '01.01.2026', end: '31.12.2026', priority: 250, assigned: 380,  used: 380, active: true },
  { id: 3, name: 'Зимняя кампания',    slug: 'winter-2025',     audience: 'RFM: Loyal',         reward: '5% бонусов',           start: '01.12.2025', end: '28.02.2026', priority: 100, assigned: 980,  used: 712, active: false },
];

export default SOURCE.map((c) => ({
  id: `CMP-${c.id}`,
  name: c.name,
  slug: c.slug,
  status: c.active ? 'active' : 'finished',
  period: { from: toIso(c.start), to: toIso(c.end) },
  reach: c.assigned,
  used: c.used,
  segment: AUDIENCE_TO_SEGMENT[c.audience] || c.audience,
  audience: c.audience,
  rules: c.reward,
  priority: c.priority,
}));
