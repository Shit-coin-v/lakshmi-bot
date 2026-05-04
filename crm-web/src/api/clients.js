import { apiGet } from './client.js';

const SEGMENT_RU_TO_EN = {
  'Чемпионы': 'champions',
  'Лояльные': 'loyal',
  'Потенциально лояльные': 'potential_loyalists',
  'Новые клиенты': 'new_customers',
  'Под угрозой': 'at_risk',
  'Спящие': 'hibernating',
  'Потерянные': 'lost',
  // legacy names from prototype, alias to closest match:
  'Новички': 'new_customers',
  'Рискуют уйти': 'at_risk',
};

export async function listClients({ q, segment, page, pageSize } = {}) {
  const segmentEn = segment ? (SEGMENT_RU_TO_EN[segment] || segment) : undefined;
  const { data, pagination } = await apiGet('/clients/', {
    q, segment: segmentEn, page, page_size: pageSize,
  });
  return { results: data, pagination };
}

export async function getClient(cardId) {
  const { data } = await apiGet(`/clients/${encodeURIComponent(cardId)}/`);
  return data;
}
