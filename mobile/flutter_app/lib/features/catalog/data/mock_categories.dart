import '../models/category_node.dart';

const mockCategories = <CategoryNode>[
  CategoryNode(
    id: 1,
    name: 'Продукты питания',
    children: [
      CategoryNode(
        id: 10,
        name: 'Молочные продукты',
        parentId: 1,
        children: [
          CategoryNode(id: 100, name: 'Молоко', parentId: 10),
          CategoryNode(id: 101, name: 'Йогурты', parentId: 10),
          CategoryNode(id: 102, name: 'Сыры', parentId: 10),
        ],
      ),
      CategoryNode(
        id: 11,
        name: 'Хлеб и выпечка',
        parentId: 1,
        children: [
          CategoryNode(id: 110, name: 'Хлеб', parentId: 11),
          CategoryNode(id: 111, name: 'Сдоба', parentId: 11),
        ],
      ),
      CategoryNode(id: 12, name: 'Крупы и макароны', parentId: 1),
    ],
  ),
  CategoryNode(
    id: 2,
    name: 'Напитки',
    children: [
      CategoryNode(id: 20, name: 'Вода', parentId: 2),
      CategoryNode(id: 21, name: 'Соки', parentId: 2),
      CategoryNode(id: 22, name: 'Чай и кофе', parentId: 2),
    ],
  ),
  CategoryNode(
    id: 3,
    name: 'Бытовая химия',
    children: [
      CategoryNode(
        id: 30,
        name: 'Средства для стирки',
        parentId: 3,
        children: [
          CategoryNode(id: 300, name: 'Порошки', parentId: 30),
          CategoryNode(id: 301, name: 'Гели', parentId: 30),
        ],
      ),
      CategoryNode(id: 31, name: 'Средства для уборки', parentId: 3),
    ],
  ),
];
