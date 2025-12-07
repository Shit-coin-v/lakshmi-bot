import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import '../providers/orders_provider.dart';

class OrderStatusScreen extends ConsumerWidget {
  final int orderId;
  final bool fromOrderCreation; // <--- НОВОЕ ПОЛЕ

  const OrderStatusScreen({
    super.key,
    required this.orderId,
    this.fromOrderCreation = false, // <--- ЗНАЧЕНИЕ ПО УМОЛЧАНИЮ
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final orderAsync = ref.watch(orderByIdProvider(orderId));

    return Scaffold(
      backgroundColor: const Color(0xFFF9F9F9),
      appBar: AppBar(
        title: const Text("Статус заказа"),
        centerTitle: true,
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back, color: Colors.black),
          onPressed: () {
            if (fromOrderCreation) {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text(
                    "Статус заказа сохранился в разделе Профиль -> Мои заказы",
                  ),
                  backgroundColor: Colors.blueGrey,
                  duration: Duration(seconds: 3),
                ),
              );
              context.go('/home');
            } else {
              context.pop();
            }
          },
        ),
      ),
      body: orderAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, stack) => Center(child: Text('Ошибка: $err')),
        data: (order) {
          final deliveryTimeStart = order.createdAt.add(
            const Duration(minutes: 30),
          );
          final deliveryTimeEnd = order.createdAt.add(
            const Duration(minutes: 45),
          );
          final timeFormat = DateFormat('HH:mm');

          return Column(
            children: [
              const SizedBox(height: 20),
              Text(
                "Заказ №${order.id} из магазина",
                style: const TextStyle(fontSize: 16, color: Colors.grey),
              ),
              const SizedBox(height: 8),
              const Text(
                "Лакшми маркет",
                style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 16),
              Text(
                "Ожидаемое время доставки: ${timeFormat.format(deliveryTimeStart)} - ${timeFormat.format(deliveryTimeEnd)}",
                style: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w500,
                ),
              ),
              const SizedBox(height: 40),

              Expanded(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 32.0),
                  child: ListView(
                    children: [
                      _StatusStep(
                        isActive: true,
                        isLast: false,
                        icon: Icons.shopping_basket,
                        title: "Заказ собирается",
                        time: timeFormat.format(order.createdAt),
                        isCompleted: order.status != 'new',
                      ),
                      _StatusStep(
                        isActive: [
                          'delivery',
                          'completed',
                        ].contains(order.status),
                        isLast: false,
                        icon: Icons.local_shipping,
                        title: "Курьер забрал заказ",
                        subtitle: "Скоро",
                        isCompleted: order.status == 'completed',
                      ),
                      _StatusStep(
                        isActive: order.status == 'completed',
                        isLast: true,
                        icon: Icons.route,
                        title: "Курьер в пути",
                      ),
                    ],
                  ),
                ),
              ),

              Padding(
                padding: const EdgeInsets.all(20.0),
                child: SizedBox(
                  width: double.infinity,
                  height: 54,
                  child: ElevatedButton.icon(
                    onPressed: () {},
                    icon: const Icon(Icons.phone),
                    label: const Text("Связаться с курьером"),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF4CAF50),
                      foregroundColor: Colors.white,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(30),
                      ),
                    ),
                  ),
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}

class _StatusStep extends StatelessWidget {
  final bool isActive;
  final bool isCompleted;
  final bool isLast;
  final IconData icon;
  final String title;
  final String? subtitle;
  final String? time;

  const _StatusStep({
    required this.isActive,
    required this.isLast,
    required this.icon,
    required this.title,
    this.subtitle,
    this.time,
    this.isCompleted = false,
  });

  @override
  Widget build(BuildContext context) {
    final color = isActive ? const Color(0xFF4CAF50) : Colors.grey;

    return IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Column(
            children: [
              Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(color: color, shape: BoxShape.circle),
                child: Icon(icon, color: Colors.white, size: 20),
              ),
              if (!isLast)
                Expanded(
                  child: Container(
                    width: 2,
                    color: isCompleted
                        ? const Color(0xFF4CAF50)
                        : Colors.grey[300],
                  ),
                ),
            ],
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(height: 8),
                Text(
                  title,
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                if (subtitle != null) ...[
                  const SizedBox(height: 4),
                  Text(subtitle!, style: const TextStyle(color: Colors.grey)),
                ],
                if (time != null) ...[
                  const SizedBox(height: 4),
                  Text(time!, style: const TextStyle(color: Colors.grey)),
                ],
                const SizedBox(height: 40),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
