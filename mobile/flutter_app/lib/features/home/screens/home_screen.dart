import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/analytics_service.dart';
import '../providers/products_provider.dart';
import '../widgets/products_grid_view.dart';
import '../widgets/cart_total_bar.dart';
import '../widgets/category_strip.dart';
import '../widgets/category_breadcrumbs.dart';
import '../../cart/providers/cart_provider.dart';
import '../../catalog/models/category_node.dart';
import '../../notifications/providers/notifications_provider.dart';

class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  Timer? _debounce;

  @override
  void dispose() {
    _debounce?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final productsAsyncValue = ref.watch(currentProductsProvider);

    final notificationsAsync = ref.watch(notificationsProvider);
    final hasUnread = notificationsAsync.maybeWhen(
      data: (items) => items.any((n) => n.isRead == false),
      orElse: () => false,
    );

    // Аналитика: фиксируем каждый переход на не пустой уровень категории.
    // Срабатывает на тапы по чипам, тапы по крошкам и сброс через стрелку «←».
    ref.listen<List<CategoryNode>>(categoryPathProvider, (prev, next) {
      if (next.isEmpty) return;
      AnalyticsService().trackCategoryView(
        categoryId: next.last.id,
        depth: next.length,
      );
    });

    return Scaffold(
      backgroundColor: const Color(0xFFF9F9F9),
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        centerTitle: false,
        title: const Text(
          'Лакшми Маркет',
          style: TextStyle(
            fontWeight: FontWeight.bold,
            fontSize: 20,
            color: Colors.black,
          ),
        ),
        actions: [
          IconButton(
            onPressed: () {
              AnalyticsService().trackCatalogButtonTap();
              context.push('/home/categories');
            },
            icon: const Icon(Icons.category_outlined, color: Colors.black),
          ),
          IconButton(
            onPressed: () {
              context.push('/home/notifications');
            },
            icon: Stack(
              clipBehavior: Clip.none,
              children: [
                const Icon(
                  Icons.notifications_none_rounded,
                  color: Colors.black,
                ),
                if (hasUnread)
                  Positioned(
                    right: -1,
                    top: -1,
                    child: Container(
                      width: 10,
                      height: 10,
                      decoration: const BoxDecoration(
                        color: Colors.red,
                        shape: BoxShape.circle,
                      ),
                    ),
                  ),
              ],
            ),
          ),

          Consumer(
            builder: (context, ref, child) {
              final cartCount = ref.watch(cartCountProvider);

              return IconButton(
                onPressed: () {
                  context.push('/home/cart');
                },
                icon: Badge(
                  isLabelVisible: cartCount > 0,
                  label: Text('$cartCount'),
                  backgroundColor: Colors.green,
                  child: const Icon(Icons.shopping_cart, color: Colors.black),
                ),
              );
            },
          ),
          const SizedBox(width: 8),
        ],
      ),
      bottomSheet: const CartTotalBar(),
      body: Column(
        children: [
          Container(
            color: Colors.white,
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
            child: Container(
              height: 46,
              decoration: BoxDecoration(
                color: const Color(0xFFF0F0F0),
                borderRadius: BorderRadius.circular(12),
              ),
              child: TextField(
                decoration: const InputDecoration(
                  hintText: 'Поиск товаров...',
                  prefixIcon: Icon(Icons.search, color: Colors.grey),
                  border: InputBorder.none,
                  contentPadding: EdgeInsets.symmetric(vertical: 12),
                ),
                onChanged: (value) {
                  _debounce?.cancel();
                  _debounce = Timer(const Duration(milliseconds: 300), () {
                    ref.read(searchQueryProvider.notifier).state = value;
                    if (value.isNotEmpty) {
                      // Сбрасываем выбранную категорию: поиск глобален.
                      if (ref.read(categoryPathProvider).isNotEmpty) {
                        ref.read(categoryPathProvider.notifier).state = [];
                      }
                      AnalyticsService().trackSearch(value, 0);
                    }
                  });
                },
              ),
            ),
          ),
          const CategoryStrip(),
          const CategoryBreadcrumbs(),
          Expanded(
            child: ProductsGridView(
              productsAsync: productsAsyncValue,
              onRetry: () => ref.invalidate(currentProductsProvider),
            ),
          ),
        ],
      ),
    );
  }
}
