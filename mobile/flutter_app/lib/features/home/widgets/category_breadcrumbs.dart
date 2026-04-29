import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers/products_provider.dart';

class CategoryBreadcrumbs extends ConsumerWidget {
  const CategoryBreadcrumbs({super.key});

  static const _linkColor = Colors.green;
  static const _sepColor = Color(0xFFCCCCCC);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final path = ref.watch(categoryPathProvider);
    if (path.isEmpty) return const SizedBox.shrink();

    final items = <Widget>[];

    // «Все» — всегда кликабельна, ведёт в корень.
    items.add(_link(
      'Все',
      onTap: () => ref.read(categoryPathProvider.notifier).state = [],
    ));

    for (var i = 0; i < path.length; i++) {
      items.add(_separator());
      final isLast = i == path.length - 1;
      final node = path[i];

      if (isLast) {
        items.add(Text(
          node.name,
          style: const TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.bold,
            color: Colors.black,
          ),
        ));
      } else {
        items.add(_link(
          node.name,
          onTap: () => ref.read(categoryPathProvider.notifier).state =
              path.sublist(0, i + 1),
        ));
      }
    }

    return Container(
      color: Colors.white,
      padding: const EdgeInsets.fromLTRB(16, 4, 16, 8),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(children: items),
      ),
    );
  }

  Widget _link(String text, {required VoidCallback onTap}) {
    return InkWell(
      onTap: onTap,
      child: Text(
        text,
        style: const TextStyle(
          fontSize: 12,
          color: _linkColor,
          decoration: TextDecoration.underline,
        ),
      ),
    );
  }

  Widget _separator() => const Padding(
        padding: EdgeInsets.symmetric(horizontal: 4),
        child: Text(
          '›',
          style: TextStyle(color: _sepColor, fontSize: 12),
        ),
      );
}
