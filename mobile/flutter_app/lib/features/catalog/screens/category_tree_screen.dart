import 'package:flutter/material.dart';

import '../data/mock_categories.dart';
import '../models/category_node.dart';

class CategoryTreeScreen extends StatelessWidget {
  final List<CategoryNode> categories;
  final String title;

  const CategoryTreeScreen({
    super.key,
    this.categories = mockCategories,
    this.title = 'Каталог',
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF9F9F9),
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        title: Text(
          title,
          style: const TextStyle(
            fontWeight: FontWeight.bold,
            fontSize: 20,
            color: Colors.black,
          ),
        ),
        leading: title != 'Каталог'
            ? IconButton(
                icon: const Icon(Icons.arrow_back, color: Colors.black),
                onPressed: () => Navigator.of(context).pop(),
              )
            : null,
      ),
      body: ListView.separated(
        padding: const EdgeInsets.all(16),
        itemCount: categories.length,
        separatorBuilder: (_, _) => const SizedBox(height: 8),
        itemBuilder: (context, index) {
          final node = categories[index];
          return _CategoryTile(node: node);
        },
      ),
    );
  }
}

class _CategoryTile extends StatelessWidget {
  final CategoryNode node;

  const _CategoryTile({required this.node});

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(12),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: () {
          if (node.isLeaf) {
            _showLeafStub(context, node);
          } else {
            Navigator.of(context).push(
              MaterialPageRoute(
                builder: (_) => CategoryTreeScreen(
                  categories: node.children,
                  title: node.name,
                ),
              ),
            );
          }
        },
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
          child: Row(
            children: [
              Expanded(
                child: Text(
                  node.name,
                  style: const TextStyle(fontSize: 16),
                ),
              ),
              Icon(
                node.isLeaf ? Icons.chevron_right : Icons.arrow_forward_ios,
                size: 18,
                color: Colors.grey,
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _showLeafStub(BuildContext context, CategoryNode node) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Товары «${node.name}» будут подключены позже'),
        duration: const Duration(seconds: 2),
      ),
    );
  }
}
