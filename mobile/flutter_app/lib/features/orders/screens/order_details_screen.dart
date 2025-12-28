import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../providers/orders_provider.dart';

class OrderDetailsScreen extends ConsumerWidget {
  final int orderId;

  const OrderDetailsScreen({super.key, required this.orderId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final detailAsync = ref.watch(orderDetailByIdProvider(orderId));

    return Scaffold(
      backgroundColor: const Color(0xFFF9F9F9),
      appBar: AppBar(
        title: const Text("Детали заказа"),
        centerTitle: true,
        backgroundColor: Colors.white,
        elevation: 0,
        foregroundColor: Colors.black,
      ),

      // ✅ Кнопка фиксированно снизу
      bottomNavigationBar: detailAsync.when(
        loading: () => const SizedBox.shrink(),
        error: (err, _) => const SizedBox.shrink(),

        data: (o) => SafeArea(
          minimum: const EdgeInsets.fromLTRB(16, 0, 16, 16),
          child: SizedBox(
            width: double.infinity,
            height: 54,
            child: ElevatedButton.icon(
              onPressed: () async {
                // 🧠⏳ маленький лоадер-диалог
                showDialog(
                  context: context,
                  barrierDismissible: false,
                  builder: (_) =>
                      const Center(child: CircularProgressIndicator()),
                );

                try {
                  final repeat = ref.read(repeatOrderProvider);
                  final newOrderId = await repeat(o.id);

                  if (context.mounted) Navigator.of(context).pop();

                  if (context.mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                        content: Text("Заказ повторён ✅"),
                        duration: Duration(seconds: 2),
                      ),
                    );

                    // ✅ Переходим на статус нового заказа
                    context.push('/order-status/$newOrderId');
                  }
                } catch (e) {
                  if (context.mounted) Navigator.of(context).pop();

                  if (context.mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(
                        content: Text("Ошибка: $e"),
                        backgroundColor: Colors.red,
                        duration: const Duration(seconds: 3),
                      ),
                    );
                  }
                }
              },
              icon: const Icon(Icons.replay),
              label: const Text("Повторить заказ"),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.black,
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(14),
                ),
              ),
            ),
          ),
        ),
      ),

      body: detailAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Text('Ошибка: $e', textAlign: TextAlign.center),
          ),
        ),
        data: (o) {
          final dt = DateFormat('dd.MM.yyyy HH:mm').format(o.createdAt);

          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              _Card(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      "Заказ №${o.id}",
                      style: const TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(dt, style: const TextStyle(color: Colors.grey)),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        const Text(
                          "Статус: ",
                          style: TextStyle(fontWeight: FontWeight.w600),
                        ),
                        Expanded(child: Text(o.statusDisplay)),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 12),

              _Card(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      "Товары",
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 12),
                    if (o.items.isEmpty)
                      const Text(
                        "Позиции не найдены",
                        style: TextStyle(color: Colors.grey),
                      )
                    else
                      ...o.items.map((it) {
                        final double lineTotal =
                            (it.priceAtMoment) * (it.quantity.toDouble());

                        return Padding(
                          padding: const EdgeInsets.only(bottom: 10),
                          child: Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Expanded(
                                child: Text(
                                  it.name,
                                  style: const TextStyle(fontSize: 14),
                                  maxLines: 2,
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ),
                              const SizedBox(width: 8),
                              Text(
                                "${it.quantity} × ${it.priceAtMoment.toStringAsFixed(0)} ₽",
                                style: const TextStyle(color: Colors.black87),
                              ),
                              const SizedBox(width: 8),
                              Text(
                                "${lineTotal.toStringAsFixed(0)} ₽",
                                style: const TextStyle(
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ],
                          ),
                        );
                      }),
                  ],
                ),
              ),
              const SizedBox(height: 12),

              _Card(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      "Доставка и оплата",
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 10),
                    Text("Адрес: ${o.address}"),
                    const SizedBox(height: 6),
                    Text("Телефон: ${o.phone}"),
                    if (o.comment.trim().isNotEmpty) ...[
                      const SizedBox(height: 6),
                      Text("Комментарий: ${o.comment}"),
                    ],
                  ],
                ),
              ),
              const SizedBox(height: 12),

              _Card(
                child: Column(
                  children: [
                    _PriceRow(title: "Товары", value: o.productsPrice),
                    const SizedBox(height: 6),
                    _PriceRow(title: "Доставка", value: o.deliveryPrice),
                    const Divider(height: 18),
                    _PriceRow(title: "Итого", value: o.totalPrice, bold: true),
                  ],
                ),
              ),

              const SizedBox(height: 8),
            ],
          );
        },
      ),
    );
  }
}

class _Card extends StatelessWidget {
  final Widget child;
  const _Card({required this.child});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.05),
            blurRadius: 5,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: child,
    );
  }
}

class _PriceRow extends StatelessWidget {
  final String title;
  final double value;
  final bool bold;
  const _PriceRow({
    required this.title,
    required this.value,
    this.bold = false,
  });

  @override
  Widget build(BuildContext context) {
    final style = TextStyle(
      fontSize: 14,
      fontWeight: bold ? FontWeight.bold : FontWeight.w500,
    );
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(title, style: style),
        Text("${value.toStringAsFixed(0)} ₽", style: style),
      ],
    );
  }
}
