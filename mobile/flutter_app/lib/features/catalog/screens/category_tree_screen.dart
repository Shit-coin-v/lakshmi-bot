import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/category_node.dart';
import '../providers/catalog_provider.dart';

class CategoryTreeScreen extends ConsumerWidget {
  final int? parentId;
  final String title;

  const CategoryTreeScreen({
    super.key,
    this.parentId,
    this.title = 'Каталог',
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final asyncCategories = parentId == null
        ? ref.watch(rootCategoriesProvider)
        : ref.watch(childCategoriesProvider(parentId!));

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
        leading: parentId != null
            ? IconButton(
                icon: const Icon(Icons.arrow_back, color: Colors.black),
                onPressed: () => Navigator.of(context).pop(),
              )
            : null,
      ),
      body: asyncCategories.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, _) => Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text('Ошибка: $err', textAlign: TextAlign.center),
              const SizedBox(height: 10),
              ElevatedButton(
                onPressed: () {
                  if (parentId == null) {
                    ref.invalidate(rootCategoriesProvider);
                  } else {
                    ref.invalidate(childCategoriesProvider(parentId!));
                  }
                },
                child: const Text('Повторить'),
              ),
            ],
          ),
        ),
        data: (categories) {
          if (categories.isEmpty) {
            return const Center(
              child: Text('Нет категорий', style: TextStyle(color: Colors.grey)),
            );
          }
          return ListView.separated(
            padding: const EdgeInsets.all(16),
            itemCount: categories.length,
            separatorBuilder: (_, _) => const SizedBox(height: 8),
            itemBuilder: (context, index) {
              final node = categories[index];
              return _CategoryTile(node: node);
            },
          );
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
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: Text('Товары «${node.name}» будут подключены позже'),
                duration: const Duration(seconds: 2),
              ),
            );
          } else {
            Navigator.of(context).push(
              MaterialPageRoute(
                builder: (_) => CategoryTreeScreen(
                  parentId: node.id,
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
}
