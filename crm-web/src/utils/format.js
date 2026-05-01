export function fmtMoney(v) {
  return new Intl.NumberFormat('ru-RU').format(v) + ' ₽';
}

export function fmtRub(v) {
  return new Intl.NumberFormat('ru-RU').format(Math.round(v)) + ' ₽';
}

export function fmtRubShort(v) {
  if (v >= 1_000_000) return (v / 1_000_000).toFixed(1).replace('.', ',') + ' млн ₽';
  if (v >= 1_000) return (v / 1_000).toFixed(0) + ' тыс ₽';
  return new Intl.NumberFormat('ru-RU').format(Math.round(v)) + ' ₽';
}

export function fmtPct(v) {
  return v.toFixed(1).replace('.', ',') + '%';
}

export function fmtDate(iso) {
  const d = typeof iso === 'string' ? new Date(iso) : iso;
  return d.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' });
}
