class CategoryNode {
  final int id;
  final String name;
  final int? parentId;
  final bool hasChildren;

  const CategoryNode({
    required this.id,
    required this.name,
    this.parentId,
    this.hasChildren = false,
  });

  bool get isLeaf => !hasChildren;

  factory CategoryNode.fromJson(Map<String, dynamic> json) {
    return CategoryNode(
      id: json['id'],
      name: json['name'] ?? '',
      parentId: json['parent_id'],
      hasChildren: json['has_children'] ?? false,
    );
  }
}
