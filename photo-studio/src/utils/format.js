// Утилиты форматирования цены и остатка для карточек товара.

export function formatPrice(value) {
  if (value === null || value === undefined || value === '') return '—';
  const num = Number(value);
  if (Number.isNaN(num)) return String(value);
  return `${num.toLocaleString('ru-RU', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  })} ₽`;
}

export function formatStock(value) {
  if (value === null || value === undefined) return '—';
  const num = Number(value);
  if (Number.isNaN(num)) return String(value);
  if (Number.isInteger(num)) return String(num);
  return num.toFixed(2).replace(/\.?0+$/, '');
}
