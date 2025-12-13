import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../auth/services/auth_service.dart';
import '../models/cart_item.dart';
import '../providers/cart_provider.dart';
import '../services/order_service.dart';
import '../../address/providers/address_provider.dart';
import '../../address/models/address_model.dart';

class CartScreen extends ConsumerStatefulWidget {
  const CartScreen({super.key});

  @override
  ConsumerState<CartScreen> createState() => _CartScreenState();
}

class _CartScreenState extends ConsumerState<CartScreen> {
  bool _isLoading = false;
  AddressModel? _selectedAddress;

  // По умолчанию
  String _paymentMethod = 'card_courier';

  late TextEditingController _phoneController;
  late TextEditingController _commentController;

  @override
  void initState() {
    super.initState();
    _phoneController = TextEditingController(text: "+7 999 000-00-00");
    _commentController = TextEditingController();
  }

  @override
  void dispose() {
    _phoneController.dispose();
    _commentController.dispose();
    super.dispose();
  }

  // --- ВЫБОР АДРЕСА ---
  void _selectAddress() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) => _AddressPickerSheet(
        onSelect: (address) {
          setState(() {
            _selectedAddress = address;
            final details = [
              if (address.entrance.isNotEmpty) 'Подъезд ${address.entrance}',
              if (address.floor.isNotEmpty) 'Этаж ${address.floor}',
              if (address.intercom.isNotEmpty) 'Домофон ${address.intercom}',
              if (address.comment.isNotEmpty) address.comment,
            ].join(', ');
            if (details.isNotEmpty) _commentController.text = details;
          });
          Navigator.pop(context);
        },
      ),
    );
  }

  // --- ВЫБОР ОПЛАТЫ (НОВЫЙ МЕТОД) ---
  void _showPaymentMethodPicker() {
    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) {
        return Container(
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
                title: "Картой курьеру",
                icon: Icons.credit_card,
                value: "card_courier",
                groupValue: _paymentMethod,
                onChanged: (val) {
                  setState(() => _paymentMethod = val!);
                  Navigator.pop(context);
                },
              ),
              const SizedBox(height: 12),
              _PaymentOption(
                title: "Наличными",
                icon: Icons.payments_outlined,
                value: "cash",
                groupValue: _paymentMethod,
                onChanged: (val) {
                  setState(() => _paymentMethod = val!);
                  Navigator.pop(context);
                },
              ),
              const SizedBox(height: 12),
              _PaymentOption(
                title: "СБП",
                icon: Icons.qr_code_2,
                value: "sbp",
                groupValue: _paymentMethod,
                onChanged: (val) {
                  setState(() => _paymentMethod = val!);
                  Navigator.pop(context);
                },
              ),
              const SizedBox(height: 20),
            ],
          ),
        );
      },
    );
  }

  // Вспомогательные методы для отображения выбранного
  String _getPaymentTitle(String value) {
    switch (value) {
      case 'card_courier':
        return 'Картой курьеру';
      case 'cash':
        return 'Наличными';
      case 'sbp':
        return 'СБП';
      default:
        return 'Картой курьеру';
    }
  }

  IconData _getPaymentIcon(String value) {
    switch (value) {
      case 'card_courier':
        return Icons.credit_card;
      case 'cash':
        return Icons.payments_outlined;
      case 'sbp':
        return Icons.qr_code_2;
      default:
        return Icons.credit_card;
    }
  }

  Future<void> _submitOrder(double totalPrice, List<CartItem> items) async {
    if (_selectedAddress == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Пожалуйста, выберите адрес доставки')),
      );
      return;
    }

    setState(() => _isLoading = true);

    try {
      final authService = ref.read(authServiceProvider);
      final realUserId = await authService.getSavedUserId();
      final userIdToSend = realUserId ?? 1;

      final orderId = await ref
          .read(orderServiceProvider)
          .createOrder(
            address: _selectedAddress!.fullAddress,
            phone: _phoneController.text,
            comment: _commentController.text,
            paymentMethod: _paymentMethod,
            totalPrice: totalPrice,
            items: items,
            userId: userIdToSend,
          );

      if (orderId != null) {
        ref.read(cartProvider.notifier).clear();
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Заказ успешно оформлен! 🎉'),
              backgroundColor: Colors.green,
            ),
          );
          context.go(
            Uri(
              path: '/order-status/$orderId',
              queryParameters: {'new': 'true'},
            ).toString(),
          );
        }
      } else {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Не удалось создать заказ'),
              backgroundColor: Colors.red,
            ),
          );
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Ошибка: $e'), backgroundColor: Colors.red),
        );
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final cartItems = ref.watch(cartProvider);
    final productsTotal = ref.watch(cartTotalProvider);
    const double deliveryCost = 0.0;
    final finalTotal = productsTotal + deliveryCost;

    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        title: const Text(
          "Корзина",
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        centerTitle: true,
        backgroundColor: Colors.white,
        elevation: 0,
        foregroundColor: Colors.black,
      ),
      body: cartItems.isEmpty
          ? Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(
                    Icons.shopping_cart_outlined,
                    size: 100,
                    color: Colors.grey[300],
                  ),
                  const SizedBox(height: 20),
                  const Text(
                    "Корзина пуста 😔",
                    style: TextStyle(fontSize: 18, color: Colors.grey),
                  ),
                ],
              ),
            )
          : Column(
              children: [
                Expanded(
                  child: SingleChildScrollView(
                    child: Padding(
                      padding: const EdgeInsets.all(16.0),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              const Text(
                                "Ваш заказ",
                                style: TextStyle(
                                  fontSize: 20,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                              Text(
                                "${cartItems.length} поз.",
                                style: const TextStyle(color: Colors.grey),
                              ),
                            ],
                          ),
                          const SizedBox(height: 16),
                          ...cartItems.map((item) => _CartItemRow(item: item)),

                          const SizedBox(height: 24),
                          const Divider(),
                          const SizedBox(height: 16),

                          const Text(
                            "Детали доставки",
                            style: TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          const SizedBox(height: 16),

                          InkWell(
                            onTap: _selectAddress,
                            borderRadius: BorderRadius.circular(12),
                            child: Container(
                              padding: const EdgeInsets.all(16),
                              decoration: BoxDecoration(
                                border: Border.all(color: Colors.grey[300]!),
                                borderRadius: BorderRadius.circular(12),
                              ),
                              child: Row(
                                children: [
                                  const Icon(
                                    Icons.location_on_outlined,
                                    color: Colors.green,
                                  ),
                                  const SizedBox(width: 12),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      children: [
                                        Text(
                                          _selectedAddress == null
                                              ? "Выберите адрес"
                                              : "Адрес доставки",
                                          style: TextStyle(
                                            color: Colors.grey[600],
                                            fontSize: 12,
                                          ),
                                        ),
                                        const SizedBox(height: 4),
                                        Text(
                                          _selectedAddress?.fullAddress ??
                                              "Нажмите, чтобы выбрать",
                                          style: const TextStyle(
                                            fontWeight: FontWeight.bold,
                                            fontSize: 16,
                                          ),
                                          maxLines: 2,
                                          overflow: TextOverflow.ellipsis,
                                        ),
                                      ],
                                    ),
                                  ),
                                  const Icon(
                                    Icons.chevron_right,
                                    color: Colors.grey,
                                  ),
                                ],
                              ),
                            ),
                          ),

                          const SizedBox(height: 12),
                          TextField(
                            controller: _phoneController,
                            keyboardType: TextInputType.phone,
                            decoration: InputDecoration(
                              labelText: "Телефон для связи",
                              prefixIcon: const Icon(Icons.phone_outlined),
                              border: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(12),
                              ),
                              contentPadding: const EdgeInsets.symmetric(
                                horizontal: 16,
                                vertical: 14,
                              ),
                            ),
                          ),
                          const SizedBox(height: 12),
                          TextField(
                            controller: _commentController,
                            maxLines: 2,
                            decoration: InputDecoration(
                              labelText: "Комментарий к заказу",
                              hintText: "Подъезд, этаж, код домофона...",
                              prefixIcon: const Icon(Icons.comment_outlined),
                              border: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(12),
                              ),
                              contentPadding: const EdgeInsets.symmetric(
                                horizontal: 16,
                                vertical: 14,
                              ),
                            ),
                          ),

                          // 👇 МЫ УБРАЛИ ОТСЮДА СПИСОК ОПЛАТЫ, ЧТОБЫ ПОМЕСТИТЬ ЕГО ВНИЗ
                          const SizedBox(height: 20),
                        ],
                      ),
                    ),
                  ),
                ),

                // --- НИЖНЯЯ ПАНЕЛЬ ---
                Container(
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(
                    color: const Color(0xFFF5F5F5),
                    borderRadius: const BorderRadius.vertical(
                      top: Radius.circular(20),
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withValues(alpha: 0.05),
                        blurRadius: 10,
                        offset: const Offset(0, -5),
                      ),
                    ],
                  ),
                  child: SafeArea(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        _SummaryRow(
                          title: "Сумма",
                          value: "${productsTotal.toStringAsFixed(0)} ₽",
                        ),
                        const SizedBox(height: 8),
                        _SummaryRow(title: "Доставка", value: "Бесплатно"),
                        const SizedBox(height: 12),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            const Text(
                              "Итого",
                              style: TextStyle(
                                fontSize: 20,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            Text(
                              "${finalTotal.toStringAsFixed(0)} ₽",
                              style: const TextStyle(
                                fontSize: 20,
                                fontWeight: FontWeight.bold,
                                color: Colors.green,
                              ),
                            ),
                          ],
                        ),

                        const Divider(height: 24),

                        // 👇 ВОТ ЗДЕСЬ ТЕПЕРЬ ОПЛАТА (ВСЕГДА НА ВИДУ)
                        InkWell(
                          onTap: _showPaymentMethodPicker,
                          child: Row(
                            children: [
                              Container(
                                padding: const EdgeInsets.all(8),
                                decoration: BoxDecoration(
                                  color: Colors.green.withValues(alpha: 0.1),
                                  borderRadius: BorderRadius.circular(8),
                                ),
                                child: Icon(
                                  _getPaymentIcon(_paymentMethod),
                                  color: Colors.green,
                                ),
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    const Text(
                                      "Способ оплаты",
                                      style: TextStyle(
                                        color: Colors.grey,
                                        fontSize: 12,
                                      ),
                                    ),
                                    Text(
                                      _getPaymentTitle(_paymentMethod),
                                      style: const TextStyle(
                                        fontWeight: FontWeight.bold,
                                        fontSize: 15,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                              const Text(
                                "Изменить",
                                style: TextStyle(
                                  color: Colors.green,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ],
                          ),
                        ),

                        const SizedBox(height: 16),

                        SizedBox(
                          width: double.infinity,
                          height: 54,
                          child: ElevatedButton(
                            onPressed: _isLoading
                                ? null
                                : () => _submitOrder(finalTotal, cartItems),
                            style: ElevatedButton.styleFrom(
                              backgroundColor: const Color(0xFF4CAF50),
                              foregroundColor: Colors.white,
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(16),
                              ),
                              elevation: 0,
                            ),
                            child: _isLoading
                                ? const SizedBox(
                                    width: 24,
                                    height: 24,
                                    child: CircularProgressIndicator(
                                      color: Colors.white,
                                      strokeWidth: 2,
                                    ),
                                  )
                                : const Text(
                                    "Оформить заказ",
                                    style: TextStyle(
                                      fontSize: 18,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
    );
  }
}

// Виджет одной опции оплаты (используется внутри BottomSheet)
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

// ... Остальные виджеты (_AddressPickerSheet, _CartItemRow, _CountBtn, _SummaryRow)
// остаются БЕЗ ИЗМЕНЕНИЙ (скопируй из прошлого файла, они тут нужны!)
class _AddressPickerSheet extends ConsumerWidget {
  final Function(AddressModel) onSelect;
  const _AddressPickerSheet({required this.onSelect});
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final addresses = ref.watch(addressProvider);
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Text(
            "Выберите адрес доставки",
            style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 16),
          if (addresses.isEmpty)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20),
              child: Column(
                children: [
                  const SizedBox(height: 20),
                  const Icon(
                    Icons.location_off_outlined,
                    size: 48,
                    color: Colors.grey,
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    "У вас нет сохраненных адресов",
                    style: TextStyle(color: Colors.grey, fontSize: 16),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 30),
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      onPressed: () {
                        Navigator.pop(context);
                        context.push('/saved-addresses');
                      },
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF4CAF50),
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(vertical: 16),
                        elevation: 0,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(16),
                        ),
                      ),
                      child: const Text(
                        "Добавить адрес",
                        style: TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: 20),
                ],
              ),
            )
          else
            Flexible(
              child: ListView.separated(
                shrinkWrap: true,
                itemCount: addresses.length,
                separatorBuilder: (context, index) => const Divider(height: 1),
                itemBuilder: (context, index) {
                  final addr = addresses[index];
                  return ListTile(
                    contentPadding: const EdgeInsets.symmetric(
                      horizontal: 20,
                      vertical: 8,
                    ),
                    leading: Container(
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: Colors.green.withValues(alpha: 0.1),
                        shape: BoxShape.circle,
                      ),
                      child: Icon(
                        _getIconForLabel(addr.label),
                        color: Colors.green,
                        size: 24,
                      ),
                    ),
                    title: Text(
                      addr.label.isNotEmpty ? addr.label : "Адрес",
                      style: const TextStyle(fontWeight: FontWeight.bold),
                    ),
                    subtitle: Text(
                      addr.fullAddress,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    onTap: () => onSelect(addr),
                    trailing: const Icon(
                      Icons.check_circle_outline,
                      color: Colors.grey,
                    ),
                  );
                },
              ),
            ),
          if (addresses.isNotEmpty) ...[
            const SizedBox(height: 12),
            TextButton(
              onPressed: () {
                Navigator.pop(context);
                context.push('/saved-addresses');
              },
              child: const Text(
                "Управление адресами",
                style: TextStyle(fontSize: 16),
              ),
            ),
            const SizedBox(height: 12),
          ],
        ],
      ),
    );
  }

  IconData _getIconForLabel(String label) {
    switch (label) {
      case 'Дом':
        return Icons.home;
      case 'Работа':
        return Icons.work;
      default:
        return Icons.location_on;
    }
  }
}

class _CartItemRow extends ConsumerWidget {
  final CartItem item;
  const _CartItemRow({required this.item});
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 12.0),
      child: Row(
        children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(12),
            child: Image.network(
              item.product.fullImageUrl,
              width: 80,
              height: 80,
              fit: BoxFit.cover,
              errorBuilder: (context, error, stackTrace) =>
                  Container(width: 80, height: 80, color: Colors.grey[200]),
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  item.product.name,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  "${item.product.price.toStringAsFixed(2)} ₽",
                  style: const TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 16,
                  ),
                ),
              ],
            ),
          ),
          Row(
            children: [
              _CountBtn(
                icon: Icons.remove,
                onTap: () =>
                    ref.read(cartProvider.notifier).removeProduct(item.product),
              ),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 12),
                child: Text(
                  "${item.quantity}",
                  style: const TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 16,
                  ),
                ),
              ),
              _CountBtn(
                icon: Icons.add,
                onTap: () =>
                    ref.read(cartProvider.notifier).addProduct(item.product),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _CountBtn extends StatelessWidget {
  final IconData icon;
  final VoidCallback onTap;
  const _CountBtn({required this.icon, required this.onTap});
  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Container(
        padding: const EdgeInsets.all(4),
        child: Icon(icon, size: 20, color: Colors.grey[600]),
      ),
    );
  }
}

class _SummaryRow extends StatelessWidget {
  final String title;
  final String value;
  const _SummaryRow({required this.title, required this.value});
  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(title, style: const TextStyle(color: Colors.grey, fontSize: 16)),
        Text(
          value,
          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
        ),
      ],
    );
  }
}
