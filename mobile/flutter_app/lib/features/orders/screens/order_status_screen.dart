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

  void _showCancelDialog(BuildContext context, WidgetRef ref, int id) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text("Отменить заказ?"),
        content: const Text("Вы уверены, что хотите отменить заказ?"),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text("Нет"),
          ),
          TextButton(
            onPressed: () async {
              Navigator.pop(ctx);
              try {
                final cancel = ref.read(cancelOrderProvider);
                await cancel(id);
                ref.invalidate(orderByIdProvider(id));
                if (context.mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(
                      content: Text("Заказ отменён"),
                      backgroundColor: Colors.green,
                    ),
                  );
                }
              } catch (e) {
                if (context.mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text("Ошибка: $e"),
                      backgroundColor: Colors.red,
                    ),
                  );
                }
              }
            },
            child: const Text("Да, отменить", style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );
  }

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
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh, color: Colors.black),
            onPressed: () {
              ref.invalidate(orderByIdProvider(orderId));
            },
          ),
        ],
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
          final isPickup = order.fulfillmentType == 'pickup';

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
              if (isPickup)
                const Text(
                  "Самовывоз",
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w500,
                  ),
                )
              else
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
                  child: Builder(
                    builder: (context) {
                      final status = order.status;
                      final isCanceled = status == 'canceled';

                      final statusOrder = isPickup
                          ? ['new', 'accepted', 'assembly', 'ready', 'completed']
                          : ['new', 'accepted', 'assembly', 'ready', 'delivery', 'arrived', 'completed'];
                      final activeIndex = isCanceled ? -1 : statusOrder.indexOf(status);

                      bool isStepActive(int stepIndex) => !isCanceled && stepIndex <= activeIndex;
                      bool isStepCompleted(int stepIndex) => !isCanceled && stepIndex < activeIndex;

                      final steps = isPickup
                          ? [
                              _StatusStep(
                                isActive: isStepActive(0),
                                isLast: false,
                                icon: Icons.fiber_new,
                                title: "Новый заказ",
                                time: timeFormat.format(order.createdAt),
                                isCompleted: isStepCompleted(0),
                              ),
                              _StatusStep(
                                isActive: isStepActive(1),
                                isLast: false,
                                icon: Icons.check_circle,
                                title: "Заказ принят",
                                isCompleted: isStepCompleted(1),
                              ),
                              _StatusStep(
                                isActive: isStepActive(2),
                                isLast: false,
                                icon: Icons.shopping_basket,
                                title: "Заказ собирается",
                                isCompleted: isStepCompleted(2),
                              ),
                              _StatusStep(
                                isActive: isStepActive(3),
                                isLast: false,
                                icon: Icons.inventory_2,
                                title: "Ваш заказ готов, можете забрать",
                                isCompleted: isStepCompleted(3),
                              ),
                              _StatusStep(
                                isActive: isStepActive(4),
                                isLast: true,
                                icon: Icons.done_all,
                                title: "Заказ выдан",
                                isCompleted: false,
                              ),
                            ]
                          : [
                              _StatusStep(
                                isActive: isStepActive(0),
                                isLast: false,
                                icon: Icons.fiber_new,
                                title: "Новый заказ",
                                time: timeFormat.format(order.createdAt),
                                isCompleted: isStepCompleted(0),
                              ),
                              _StatusStep(
                                isActive: isStepActive(1),
                                isLast: false,
                                icon: Icons.check_circle,
                                title: "Заказ принят",
                                isCompleted: isStepCompleted(1),
                              ),
                              _StatusStep(
                                isActive: isStepActive(2),
                                isLast: false,
                                icon: Icons.shopping_basket,
                                title: "Заказ собирается",
                                isCompleted: isStepCompleted(2),
                              ),
                              _StatusStep(
                                isActive: isStepActive(3),
                                isLast: false,
                                icon: Icons.inventory_2,
                                title: "Заказ собран, ждёт курьера",
                                isCompleted: isStepCompleted(3),
                              ),
                              _StatusStep(
                                isActive: isStepActive(4),
                                isLast: false,
                                icon: Icons.local_shipping,
                                title: "Курьер забрал заказ",
                                isCompleted: isStepCompleted(4),
                              ),
                              _StatusStep(
                                isActive: isStepActive(5),
                                isLast: false,
                                icon: Icons.place,
                                title: "Курьер пришёл и ждёт вас",
                                isCompleted: isStepCompleted(5),
                              ),
                              _StatusStep(
                                isActive: isStepActive(6),
                                isLast: true,
                                icon: Icons.done_all,
                                title: "Заказ доставлен",
                                isCompleted: false,
                              ),
                            ];

                      return ListView(children: steps);
                    },
                  ),
                ),
              ),

              Container(
                padding: const EdgeInsets.fromLTRB(20, 16, 20, 20),
                decoration: BoxDecoration(
                  color: Colors.white,
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: 0.08),
                      blurRadius: 10,
                      offset: const Offset(0, -5),
                    ),
                  ],
                ),
                child: SafeArea(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      if (!isPickup)
                        SizedBox(
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
                                borderRadius: BorderRadius.circular(16),
                              ),
                              elevation: 0,
                            ),
                          ),
                        ),
                      if (order.status == 'new' || order.status == 'accepted' || order.status == 'assembly' || order.status == 'ready') ...[
                        const SizedBox(height: 12),
                        SizedBox(
                          width: double.infinity,
                          height: 54,
                          child: OutlinedButton.icon(
                            onPressed: () => _showCancelDialog(context, ref, order.id),
                            icon: const Icon(Icons.close),
                            label: const Text("Отменить заказ"),
                            style: OutlinedButton.styleFrom(
                              foregroundColor: Colors.red,
                              side: const BorderSide(color: Colors.red),
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(16),
                              ),
                            ),
                          ),
                        ),
                      ],
                    ],
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
