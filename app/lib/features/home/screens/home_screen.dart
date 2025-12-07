import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/products_provider.dart';
import '../models/product.dart';
import '../../cart/providers/cart_provider.dart';
import '../../cart/models/cart_item.dart';
import 'package:go_router/go_router.dart';

class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // Слушаем наш провайдер
    final productsAsyncValue = ref.watch(productsProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Лакшми Маркет'),
        actions: [
          IconButton(onPressed: () {}, icon: const Icon(Icons.search)),
          Consumer(
            builder: (context, ref, child) {
              // Слушаем общее количество товаров
              final cartCount = ref.watch(cartCountProvider);

              return IconButton(
                onPressed: () {
                  context.push('/cart');
                },
                icon: Badge(
                  // Если 0, то бейдж не показываем (isVisible: false)
                  isLabelVisible: cartCount > 0,
                  label: Text('$cartCount'),
                  backgroundColor: Colors.green, // Цвет кружочка
                  child: const Icon(Icons.shopping_cart),
                ),
              );
            },
          ),
        ],
      ),

      bottomSheet: const _CartTotalBar(),

      body: productsAsyncValue.when(
        // 1. Если данные загружаются - крутим колесико
        loading: () => const Center(child: CircularProgressIndicator()),

        // 2. Если ошибка - показываем текст и кнопку повтора
        error: (err, stack) => Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text('Ошибка: $err', textAlign: TextAlign.center),
              const SizedBox(height: 10),
              ElevatedButton(
                onPressed: () => ref.refresh(productsProvider),
                child: const Text('Повторить'),
              ),
            ],
          ),
        ),

        // 3. Если данные пришли - показываем сетку товаров
        data: (products) {
          if (products.isEmpty) {
            return const Center(child: Text('Товаров пока нет'));
          }
          return GridView.builder(
            padding: const EdgeInsets.all(16),
            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: 2, // 2 колонки
              childAspectRatio: 0.75, // Соотношение сторон карточки
              crossAxisSpacing: 16,
              mainAxisSpacing: 16,
            ),
            itemCount: products.length,
            itemBuilder: (context, index) {
              final product = products[index];
              return _ProductCard(product: product);
            },
          );
        },
      ),
    );
  }
}

class _ProductCard extends ConsumerWidget {
  // <-- Стало ConsumerWidget
  final Product product;

  const _ProductCard({required this.product});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // Ищем, есть ли этот товар в корзине
    final cartItems = ref.watch(cartProvider);
    final cartItem = cartItems.firstWhere(
      (item) => item.product.id == product.id,
      orElse: () => CartItem(product: product, quantity: 0), // Фейковый пустой
    );
    final quantity = cartItem.quantity;

    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.05),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Картинка (без изменений)
          Expanded(
            child: ClipRRect(
              borderRadius: const BorderRadius.vertical(
                top: Radius.circular(16),
              ),
              child: Image.network(
                product.fullImageUrl,
                fit: BoxFit.cover,
                width: double.infinity,
                errorBuilder: (ctx, err, stack) => const Center(
                  child: Icon(
                    Icons.image_not_supported,
                    size: 40,
                    color: Colors.grey,
                  ),
                ),
              ),
            ),
          ),
          // Текст и Кнопки
          Padding(
            padding: const EdgeInsets.all(8.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  product.name,
                  style: const TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 16,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 4),
                Text(
                  '${product.price} ₽',
                  style: const TextStyle(
                    color: Colors.green,
                    fontWeight: FontWeight.bold,
                    fontSize: 14,
                  ),
                ),
                const SizedBox(height: 8),

                // --- УМНАЯ КНОПКА ---
                if (quantity == 0)
                  // Если 0 - показываем большую кнопку "В корзину"
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      onPressed: product.stock > 0
                          ? () => ref
                                .read(cartProvider.notifier)
                                .addProduct(product)
                          : null,
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.green,
                        foregroundColor: Colors.white,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(8),
                        ),
                      ),
                      child: Text(
                        product.stock > 0 ? 'В корзину' : 'Нет в наличии',
                      ),
                    ),
                  )
                else
                  // Если > 0 - показываем "Минус Цифра Плюс"
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      _IconBtn(
                        icon: Icons.remove,
                        onTap: () => ref
                            .read(cartProvider.notifier)
                            .removeProduct(product),
                      ),
                      Text(
                        '$quantity',
                        style: const TextStyle(
                          fontWeight: FontWeight.bold,
                          fontSize: 16,
                        ),
                      ),
                      _IconBtn(
                        icon: Icons.add,
                        onTap: () =>
                            ref.read(cartProvider.notifier).addProduct(product),
                      ),
                    ],
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// Маленькая кнопка для +/-
class _IconBtn extends StatelessWidget {
  final IconData icon;
  final VoidCallback onTap;
  const _IconBtn({required this.icon, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(20),
      child: Container(
        padding: const EdgeInsets.all(4),
        decoration: BoxDecoration(
          color: Colors.green.withValues(alpha: 0.1),
          shape: BoxShape.circle,
        ),
        child: Icon(icon, size: 20, color: Colors.green),
      ),
    );
  }
}

class _CartTotalBar extends ConsumerWidget {
  const _CartTotalBar();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // Слушаем изменения суммы и количества
    final totalAmount = ref.watch(cartTotalProvider);
    final totalCount = ref.watch(cartCountProvider);

    // Если корзина пустая - прячем плашку (возвращаем пустоту)
    if (totalCount == 0) return const SizedBox.shrink();

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        boxShadow: [
          BoxShadow(
            // Используем .withValues, чтобы не было предупреждений
            color: Colors.black.withValues(alpha: 0.1),
            blurRadius: 10,
            offset: const Offset(0, -5),
          ),
        ],
      ),
      child: SafeArea(
        child: SizedBox(
          width: double.infinity,
          height: 54, // Чуть выше, чтобы удобнее нажимать
          child: ElevatedButton(
            onPressed: () {
              context.push('/cart');
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.green,
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
              ),
              elevation: 0,
              // Убираем стандартные отступы, чтобы настроить свои внутри
              padding: EdgeInsets.zero,
            ),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20.0),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text(
                    "В корзину",
                    style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                  ),
                  Text(
                    '${totalAmount.toStringAsFixed(0)} ₽',
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
