import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../home/providers/products_list_provider.dart';
import '../../home/widgets/products_grid_view.dart';
import '../../home/widgets/cart_total_bar.dart';

class CategoryProductsScreen extends ConsumerWidget {
  final int categoryId;
  final String title;

  const CategoryProductsScreen({
    super.key,
    required this.categoryId,
    required this.title,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final listKey = ProductsListKey(search: '', categoryId: categoryId);

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
      ),
      bottomSheet: const CartTotalBar(),
      body: ProductsGridView(
        listKey: listKey,
        emptyMessage: 'Нет товаров в этой категории',
        emptyIcon: Icons.inventory_2_outlined,
      ),
    );
  }
}
