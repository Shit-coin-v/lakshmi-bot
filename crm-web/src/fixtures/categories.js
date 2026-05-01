// Портировано из reference CAT_FIXTURES.categories.
// Поля: code, name, skus, revenue, cogs, share, turnover, abc, xyz, trend.
// Slug — code-based ('cat-01' и т.д.), используется в маршруте /categories/:slug.

const SOURCE = [
  { id: 1,  code: '01', name: 'Молочные продукты',     skus: 142, revenue: 2840000, cogs: 1980000, share: 22.4, turnover: 8.4,  abc: 'A', xyz: 'X', trend: [62,68,71,69,74,78,82,85,88,86,89,92] },
  { id: 2,  code: '02', name: 'Хлеб и выпечка',        skus: 86,  revenue: 1820000, cogs: 1010000, share: 14.4, turnover: 12.1, abc: 'A', xyz: 'X', trend: [55,58,62,60,63,67,69,71,73,74,76,78] },
  { id: 3,  code: '03', name: 'Мясо и птица',          skus: 124, revenue: 2210000, cogs: 1680000, share: 17.4, turnover: 5.2,  abc: 'A', xyz: 'Y', trend: [70,68,82,75,71,88,79,84,77,90,82,86] },
  { id: 4,  code: '04', name: 'Овощи и фрукты',        skus: 108, revenue: 1240000, cogs:  890000, share: 9.8,  turnover: 9.7,  abc: 'B', xyz: 'Y', trend: [40,52,48,61,55,58,67,49,71,62,68,74] },
  { id: 5,  code: '05', name: 'Бакалея',               skus: 218, revenue: 1080000, cogs:  712000, share: 8.5,  turnover: 3.1,  abc: 'B', xyz: 'X', trend: [30,32,31,33,34,33,35,36,35,37,38,38] },
  { id: 6,  code: '06', name: 'Напитки',               skus: 167, revenue:  920000, cogs:  605000, share: 7.3,  turnover: 4.6,  abc: 'B', xyz: 'Y', trend: [44,38,52,47,55,42,58,49,61,53,57,62] },
  { id: 7,  code: '07', name: 'Замороженные продукты', skus: 92,  revenue:  710000, cogs:  468000, share: 5.6,  turnover: 3.8,  abc: 'B', xyz: 'Z', trend: [22,38,15,42,28,35,18,44,29,21,38,32] },
  { id: 8,  code: '08', name: 'Снеки и сладости',      skus: 198, revenue:  640000, cogs:  402000, share: 5.0,  turnover: 6.2,  abc: 'C', xyz: 'Y', trend: [35,28,40,32,38,42,36,44,30,46,38,42] },
  { id: 9,  code: '09', name: 'Детское питание',       skus: 64,  revenue:  410000, cogs:  281000, share: 3.2,  turnover: 4.4,  abc: 'C', xyz: 'X', trend: [18,19,21,20,22,21,23,22,24,23,25,26] },
  { id: 10, code: '10', name: 'Бытовая химия',         skus: 89,  revenue:  390000, cogs:  240000, share: 3.1,  turnover: 2.7,  abc: 'C', xyz: 'Z', trend: [12,28,18,32,15,9,38,21,11,34,17,25] },
  { id: 11, code: '11', name: 'Корма для животных',    skus: 41,  revenue:  180000, cogs:  119000, share: 1.4,  turnover: 5.1,  abc: 'C', xyz: 'X', trend: [14,15,15,16,15,16,17,16,17,18,17,18] },
  { id: 12, code: '12', name: 'Гигиена',               skus: 73,  revenue:  130000, cogs:   84000, share: 1.0,  turnover: 3.4,  abc: 'C', xyz: 'Y', trend: [10,12,9,11,13,10,14,12,11,13,14,12] },
];

export default SOURCE.map((c) => ({
  ...c,
  slug: `cat-${c.code}`,
}));
