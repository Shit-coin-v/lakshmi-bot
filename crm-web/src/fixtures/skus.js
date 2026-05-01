// Портировано из reference CAT_FIXTURES.skus (SKU категории "Молочные продукты", slug 'cat-01').
// Маппинг: code → id, abc_cat → abc, xyz_cat → xyz, days_left → stockDays,
// velocity → units30d, revenue → sales30d, suggested_order → suggestedOrder.
// spark — линейный тренд из category.trend (cat-01).

const CAT_TREND = [62, 68, 71, 69, 74, 78, 82, 85, 88, 86, 89, 92];

const SOURCE = [
  { code: '0101-001', name: 'Молоко «Молочный край» 3,2% 1 л',      stock: 84,  velocity: 142, revenue: 286000, abc_cat: 'A', xyz_cat: 'X', suggested_order: 920, days_left: 0.6, supplier: 'Молочный край' },
  { code: '0101-014', name: 'Молоко «Якутское» 2,5% 0,9 л',         stock: 42,  velocity: 98,  revenue: 184000, abc_cat: 'A', xyz_cat: 'X', suggested_order: 650, days_left: 0.4, supplier: 'Сахаагропродукт' },
  { code: '0102-007', name: 'Кефир «Простоквашино» 2,5% 930 г',     stock: 58,  velocity: 76,  revenue: 142000, abc_cat: 'A', xyz_cat: 'Y', suggested_order: 480, days_left: 0.8, supplier: 'Молочный край' },
  { code: '0103-002', name: 'Сметана «Домик в деревне» 20% 300 г',  stock: 102, velocity: 64,  revenue: 128000, abc_cat: 'A', xyz_cat: 'X', suggested_order: 360, days_left: 1.6, supplier: 'Молочный край' },
  { code: '0104-019', name: 'Творог 9% 200 г',                      stock: 31,  velocity: 58,  revenue: 119000, abc_cat: 'B', xyz_cat: 'Y', suggested_order: 380, days_left: 0.5, supplier: 'Сахаагропродукт' },
  { code: '0105-003', name: 'Йогурт «Активиа» персик 290 г',        stock: 144, velocity: 51,  revenue: 96000,  abc_cat: 'B', xyz_cat: 'X', suggested_order: 220, days_left: 2.8, supplier: 'Danone' },
  { code: '0106-022', name: 'Масло сливочное 82% 180 г',            stock: 22,  velocity: 38,  revenue: 88000,  abc_cat: 'B', xyz_cat: 'Y', suggested_order: 250, days_left: 0.6, supplier: 'Молочный край' },
  { code: '0107-008', name: 'Сыр «Российский» 200 г',               stock: 8,   velocity: 34,  revenue: 76000,  abc_cat: 'B', xyz_cat: 'Z', suggested_order: 240, days_left: 0.2, supplier: 'Хладкомбинат' },
  { code: '0107-031', name: 'Сыр «Маасдам» 150 г',                  stock: 45,  velocity: 19,  revenue: 58000,  abc_cat: 'C', xyz_cat: 'Z', suggested_order: 90,  days_left: 2.4, supplier: 'Хладкомбинат' },
  { code: '0108-005', name: 'Ряженка 4% 0,5 л',                     stock: 67,  velocity: 28,  revenue: 42000,  abc_cat: 'C', xyz_cat: 'Y', suggested_order: 130, days_left: 2.4, supplier: 'Молочный край' },
  { code: '0109-012', name: 'Творог зернёный 5% 350 г',             stock: 14,  velocity: 16,  revenue: 38000,  abc_cat: 'C', xyz_cat: 'Z', suggested_order: 100, days_left: 0.9, supplier: 'Сахаагропродукт' },
  { code: '0110-018', name: 'Молочный коктейль шоколад 200 мл',     stock: 92,  velocity: 12,  revenue: 22000,  abc_cat: 'C', xyz_cat: 'Z', suggested_order: 0,   days_left: 7.7, supplier: 'Чудо' },
];

function sparkFor(velocity, idx) {
  // Per-SKU sparkline: масштабируем CAT_TREND по velocity, добавляем небольшой сдвиг.
  const baseline = velocity / 4;
  return CAT_TREND.map((p, i) => Math.round(baseline + (p - 62) * (velocity / 100) + (i + idx) % 3));
}

export default SOURCE.map((s, idx) => ({
  id: s.code,
  name: s.name,
  categorySlug: 'cat-01',
  stock: s.stock,
  units30d: s.velocity,
  sales30d: s.revenue,
  abc: s.abc_cat,
  xyz: s.xyz_cat,
  suggestedOrder: s.suggested_order,
  stockDays: s.days_left,
  supplier: s.supplier,
  spark: sparkFor(s.velocity, idx),
}));
