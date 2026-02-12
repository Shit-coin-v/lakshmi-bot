import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../providers/orders_provider.dart';

class OrderDetailsScreen extends ConsumerWidget {
  final int orderId;

  const OrderDetailsScreen({super.key, required this.orderId});

  void _showPaymentAndRepeat(BuildContext context, WidgetRef ref, int orderId, String oldPaymentMethod, double totalPrice) {
    String selectedMethod = oldPaymentMethod;
    int? selectedChange;
    String? changeError;

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (sheetContext) {
        return StatefulBuilder(
          builder: (sheetContext, setSheetState) {
            return Padding(
              padding: EdgeInsets.only(
                bottom: MediaQuery.of(sheetContext).viewInsets.bottom,
              ),
              child: Container(
                padding: const EdgeInsets.symmetric(vertical: 24, horizontal: 16),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Text(
                      "Выберите способ оплаты",
                      style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 20),
                    _PaymentOption(
                      title: "Картой курьеру (карта или QR)",
                      icon: Icons.credit_card,
                      value: "card_courier",
                      groupValue: selectedMethod,
                      onChanged: (val) {
                        setSheetState(() {
                          selectedMethod = val!;
                          changeError = null;
                        });
                      },
                    ),
                    const SizedBox(height: 12),
                    _PaymentOption(
                      title: "Наличными",
                      icon: Icons.payments_outlined,
                      value: "cash",
                      groupValue: selectedMethod,
                      onChanged: (val) {
                        setSheetState(() {
                          selectedMethod = val!;
                          changeError = null;
                        });
                      },
                    ),
                    AnimatedSize(
                      duration: const Duration(milliseconds: 200),
                      curve: Curves.easeInOut,
                      child: selectedMethod == 'cash'
                          ? Padding(
                              padding: const EdgeInsets.only(top: 16),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  const Text(
                                    "Сдача с какой суммы?",
                                    style: TextStyle(
                                      fontSize: 16,
                                      fontWeight: FontWeight.w600,
                                    ),
                                  ),
                                  const SizedBox(height: 12),
                                  Wrap(
                                    spacing: 8,
                                    runSpacing: 8,
                                    children: [
                                      for (final amount in [500, 1000, 5000])
                                        ChoiceChip(
                                          label: Text("$amount \u20bd"),
                                          selected: selectedChange == amount,
                                          onSelected: amount < totalPrice
                                              ? null
                                              : (sel) {
                                                  setSheetState(() {
                                                    selectedChange = sel ? amount : null;
                                                    changeError = null;
                                                  });
                                                },
                                          selectedColor: Colors.green.withValues(alpha: 0.2),
                                          disabledColor: Colors.grey[200],
                                        ),
                                      ChoiceChip(
                                        label: const Text("Без сдачи"),
                                        selected: selectedChange == 0,
                                        onSelected: (sel) {
                                          setSheetState(() {
                                            selectedChange = sel ? 0 : null;
                                            changeError = null;
                                          });
                                        },
                                        selectedColor: Colors.green.withValues(alpha: 0.2),
                                      ),
                                    ],
                                  ),
                                  if (selectedChange != null && selectedChange! > 0)
                                    Padding(
                                      padding: const EdgeInsets.only(top: 12),
                                      child: Text(
                                        "Сдача курьеру: ${selectedChange! - totalPrice.toInt()} \u20bd",
                                        style: const TextStyle(
                                          fontSize: 15,
                                          fontWeight: FontWeight.w600,
                                          color: Color(0xFF4CAF50),
                                        ),
                                      ),
                                    ),
                                  if (changeError != null)
                                    Padding(
                                      padding: const EdgeInsets.only(top: 8),
                                      child: Text(
                                        changeError!,
                                        style: const TextStyle(color: Colors.red, fontSize: 13),
                                      ),
                                    ),
                                ],
                              ),
                            )
                          : const SizedBox.shrink(),
                    ),
                    const SizedBox(height: 20),
                    SizedBox(
                      width: double.infinity,
                      height: 48,
                      child: ElevatedButton(
                        onPressed: () {
                          double? changeFrom;
                          if (selectedMethod == 'cash') {
                            if (selectedChange == null) {
                              setSheetState(() {
                                changeError = "Выберите сумму";
                              });
                              return;
                            }
                            changeFrom = selectedChange == 0
                                ? null
                                : selectedChange!.toDouble();
                          }
                          Navigator.pop(sheetContext);
                          _executeRepeat(context, ref, orderId, selectedMethod, changeFrom, totalPrice);
                        },
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF4CAF50),
                          foregroundColor: Colors.white,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12),
                          ),
                          elevation: 0,
                        ),
                        child: const Text(
                          "Готово",
                          style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );
  }

  void _executeRepeat(BuildContext context, WidgetRef ref, int orderId, String paymentMethod, double? changeFrom, double totalPrice) async {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (_) => const Center(child: CircularProgressIndicator()),
    );

    try {
      final repeat = ref.read(repeatOrderProvider);
      final newOrderId = await repeat(orderId, paymentMethod: paymentMethod, changeFrom: changeFrom, totalPrice: totalPrice);

      if (context.mounted) Navigator.of(context, rootNavigator: true).pop();

      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text("Заказ повторён"),
            duration: Duration(seconds: 2),
          ),
        );
        context.push('/profile/order-status/$newOrderId');
      }
    } catch (e) {
      if (context.mounted) Navigator.of(context, rootNavigator: true).pop();

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
  }

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
                ref.invalidate(orderDetailByIdProvider(id));
                ref.invalidate(myOrdersProvider);
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

        data: (o) {
          final canCancel = o.status == 'new' || o.status == 'assembly';
          return SafeArea(
            minimum: const EdgeInsets.fromLTRB(16, 0, 16, 16),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                SizedBox(
                  width: double.infinity,
                  height: 54,
                  child: ElevatedButton.icon(
                    onPressed: () => _showPaymentAndRepeat(
                      context, ref, o.id, o.paymentMethod, o.totalPrice,
                    ),
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
                if (canCancel) ...[
                  const SizedBox(height: 10),
                  SizedBox(
                    width: double.infinity,
                    height: 54,
                    child: OutlinedButton.icon(
                      onPressed: () => _showCancelDialog(context, ref, o.id),
                      icon: const Icon(Icons.close),
                      label: const Text("Отменить заказ"),
                      style: OutlinedButton.styleFrom(
                        foregroundColor: Colors.red,
                        side: const BorderSide(color: Colors.red),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(14),
                        ),
                      ),
                    ),
                  ),
                ],
              ],
            ),
          );
        },
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

class _PaymentOption extends StatelessWidget {
  final String title;
  final IconData icon;
  final String value;
  final String groupValue;
  final ValueChanged<String?> onChanged;

  const _PaymentOption({
    required this.title,
    required this.icon,
    required this.value,
    required this.groupValue,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    final isSelected = value == groupValue;
    return GestureDetector(
      onTap: () => onChanged(value),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        decoration: BoxDecoration(
          color: isSelected
              ? Colors.green.withValues(alpha: 0.05)
              : Colors.white,
          border: Border.all(
            color: isSelected ? Colors.green : Colors.grey[300]!,
            width: isSelected ? 1.5 : 1,
          ),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Row(
          children: [
            Icon(icon, color: isSelected ? Colors.green : Colors.grey[600]),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                title,
                style: TextStyle(
                  fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                  fontSize: 16,
                ),
              ),
            ),
            if (isSelected) const Icon(Icons.check_circle, color: Colors.green),
          ],
        ),
      ),
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
