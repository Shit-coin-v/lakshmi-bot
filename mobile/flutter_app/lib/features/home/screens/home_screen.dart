import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/analytics_service.dart';
import '../providers/products_provider.dart';
import '../widgets/products_grid_view.dart';
import '../widgets/cart_total_bar.dart';
import '../../cart/providers/cart_provider.dart';
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
    final productsAsyncValue = ref.watch(productsProvider);

    final notificationsAsync = ref.watch(notificationsProvider);
    final hasUnread = notificationsAsync.maybeWhen(
      data: (items) => items.any((n) => n.isRead == false),
      orElse: () => false,
    );

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
                      AnalyticsService().trackSearch(value, 0);
                    }
                  });
                },
              ),
            ),
          ),

          Expanded(
            child: ProductsGridView(
              productsAsync: productsAsyncValue,
              onRetry: () => ref.invalidate(productsProvider),
            ),
          ),
        ],
      ),
    );
  }
}
