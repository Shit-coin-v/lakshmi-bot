class CategoryNode {
  final int id;
  final String name;
  final int? parentId;
  final List<CategoryNode> children;

  const CategoryNode({
    required this.id,
    required this.name,
    this.parentId,
    this.children = const [],
  });

  bool get isLeaf => children.isEmpty;
}
