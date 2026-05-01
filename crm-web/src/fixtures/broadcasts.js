// Сегменты и каналы — из плана.
// HISTORY портирована из reference (BroadcastScreen → "Последние рассылки").

export const SEGMENTS = ['Чемпионы', 'Лояльные', 'Новички', 'Спящие', 'Рискуют уйти'];

export const CHANNELS = [
  { id: 'push',     label: 'Push (мобильное)' },
  { id: 'telegram', label: 'Telegram' },
  { id: 'email',    label: 'Email' },
];

export const CATEGORIES = [
  { id: 'general', label: 'Общая' },
  { id: 'promo',   label: 'Акции и скидки' },
  { id: 'news',    label: 'Новости магазина' },
];

export const HISTORY = [
  { id: 'BR-103', sentAt: '2026-04-12T10:00:00', segment: 'Все клиенты',  channel: 'telegram', reach: 8240,  opened: 5612, clicked: 1820 },
  { id: 'BR-102', sentAt: '2026-04-08T12:00:00', segment: 'Все клиенты',  channel: 'telegram', reach: 10084, opened: 4120, clicked: 980 },
  { id: 'BR-101', sentAt: '2026-04-05T15:00:00', segment: 'Спящие',       channel: 'push',     reach: 1240,  opened: 380,  clicked: 110 },
];

export default { SEGMENTS, CHANNELS, CATEGORIES, HISTORY };
