import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/product.dart';
import 'product_card.dart';

/// Переиспользуемая сетка товаров с обработкой loading/error/empty.
class ProductsGridView extends StatelessWidget {
  final AsyncValue<List<Product>> productsAsync;
  final VoidCallback onRetry;
  final String emptyMessage;
  final IconData emptyIcon;

  const ProductsGridView({
    super.key,
    required this.productsAsync,
    required this.onRetry,
    this.emptyMessage = 'Ничего не найдено',
    this.emptyIcon = Icons.search_off,
  });

  @override
  Widget build(BuildContext context) {
    return productsAsync.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (err, _) => Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text('Ошибка: $err', textAlign: TextAlign.center),
            const SizedBox(height: 10),
            ElevatedButton(
              onPressed: onRetry,
              child: const Text('Повторить'),
            ),
          ],
        ),
      ),
      data: (products) {
        if (products.isEmpty) {
          return Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(emptyIcon, size: 60, color: Colors.grey[300]),
                const SizedBox(height: 10),
                Text(
                  emptyMessage,
                  style: const TextStyle(color: Colors.grey),
                ),
              ],
            ),
          );
        }
        return GridView.builder(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 80),
          gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: 2,
            childAspectRatio: 0.75,
            crossAxisSpacing: 16,
            mainAxisSpacing: 16,
          ),
          itemCount: products.length,
          itemBuilder: (context, index) {
            return ProductCard(product: products[index]);
          },
        );
      },
    );
  }
}
