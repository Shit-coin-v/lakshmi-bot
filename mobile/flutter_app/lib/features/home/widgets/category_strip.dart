import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers/products_provider.dart';
import '../../catalog/models/category_node.dart';

class CategoryStrip extends ConsumerWidget {
  const CategoryStrip({super.key});

  static const _bgInactive = Color(0xFFF0F0F0);
  static const _bgBack = Color(0xFFFFE0B2);
  static const _fgBack = Color(0xFFC66900);
  static const _textInactive = Color(0xFF333333);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final path = ref.watch(categoryPathProvider);
    final asyncCategories = ref.watch(currentLevelCategoriesProvider);

    return Container(
      color: Colors.white,
      padding: const EdgeInsets.fromLTRB(12, 8, 12, 12),
      child: SizedBox(
        height: 36,
        child: asyncCategories.when(
          loading: () => _buildSkeleton(),
          error: (err, _) => _buildError(ref),
          data: (categories) => _buildChips(ref, path, categories),
        ),
      ),
    );
  }

  Widget _buildSkeleton() {
    return ListView.separated(
      key: const ValueKey('category-strip-loading'),
      scrollDirection: Axis.horizontal,
      itemCount: 4,
      separatorBuilder: (_, _) => const SizedBox(width: 8),
      itemBuilder: (context, _) => Container(
        key: const ValueKey('category-skeleton'),
        width: 80,
        decoration: BoxDecoration(
          color: _bgInactive,
          borderRadius: BorderRadius.circular(14),
        ),
      ),
    );
  }

  Widget _buildError(WidgetRef ref) {
    return Row(
      children: [
        const Expanded(
          child: Text(
            'Не удалось загрузить категории',
            style: TextStyle(color: Colors.red, fontSize: 12),
            overflow: TextOverflow.ellipsis,
          ),
        ),
        TextButton(
          onPressed: () => ref.invalidate(currentLevelCategoriesProvider),
          child: const Text('Повторить'),
        ),
      ],
    );
  }

  Widget _buildChips(
    WidgetRef ref,
    List<CategoryNode> path,
    List<CategoryNode> levelCategories,
  ) {
    final isRoot = path.isEmpty;
    final activeNode = path.isNotEmpty ? path.last : null;
    // На вложенных уровнях siblings = категории текущего уровня кроме активной.
    final siblings = activeNode == null
        ? levelCategories
        : levelCategories.where((c) => c.id != activeNode.id).toList();

    final children = <Widget>[];

    if (!isRoot) {
      children.add(_buildBackChip(ref, path));
      children.add(const SizedBox(width: 8));
    }

    if (isRoot) {
      children.add(_buildAllChip());
      children.add(const SizedBox(width: 8));
    } else if (activeNode != null) {
      children.add(_buildActiveChip(activeNode.name));
      children.add(const SizedBox(width: 8));
    }

    for (var i = 0; i < siblings.length; i++) {
      children.add(_buildInactiveChip(ref, siblings[i], path));
      if (i < siblings.length - 1) {
        children.add(const SizedBox(width: 8));
      }
    }

    return ListView(
      key: ValueKey('category-strip-${path.length}'),
      scrollDirection: Axis.horizontal,
      physics: const BouncingScrollPhysics(),
      children: children,
    );
  }

  Widget _buildBackChip(WidgetRef ref, List<CategoryNode> path) {
    return _ChipShell(
      backgroundColor: _bgBack,
      onTap: () => ref.read(categoryPathProvider.notifier).state =
          path.sublist(0, path.length - 1),
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      child: const Icon(Icons.arrow_back, size: 16, color: _fgBack),
    );
  }

  Widget _buildAllChip() {
    return _ChipShell(
      backgroundColor: Colors.green,
      onTap: () {}, // активный — без действия
      child: const Text(
        'Все',
        style: TextStyle(color: Colors.white, fontWeight: FontWeight.w600, fontSize: 13),
      ),
    );
  }

  Widget _buildActiveChip(String name) {
    return _ChipShell(
      backgroundColor: Colors.green,
      onTap: () {}, // активный — без действия
      child: Text(
        name,
        style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w600, fontSize: 13),
      ),
    );
  }

  Widget _buildInactiveChip(
    WidgetRef ref,
    CategoryNode node,
    List<CategoryNode> path,
  ) {
    return _ChipShell(
      backgroundColor: _bgInactive,
      onTap: () {
        ref.read(categoryPathProvider.notifier).state = [...path, node];
      },
      child: Text(
        node.name,
        style: const TextStyle(color: _textInactive, fontSize: 13),
      ),
    );
  }
}

class _ChipShell extends StatelessWidget {
  final Color backgroundColor;
  final VoidCallback onTap;
  final Widget child;
  final EdgeInsets padding;

  const _ChipShell({
    required this.backgroundColor,
    required this.onTap,
    required this.child,
    this.padding = const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
  });

  @override
  Widget build(BuildContext context) {
    return Material(
      color: backgroundColor,
      borderRadius: BorderRadius.circular(14),
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: onTap,
        child: Padding(
          padding: padding,
          child: Center(child: child),
        ),
      ),
    );
  }
}
