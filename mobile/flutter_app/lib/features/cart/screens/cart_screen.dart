import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/extensions/price_extension.dart';
import '../../auth/services/auth_service.dart';
import '../models/cart_item.dart';
import '../providers/cart_provider.dart';
import '../../orders/services/order_service.dart';
import '../../address/providers/address_provider.dart';
import '../../address/models/address_model.dart';
import '../../home/providers/profile_provider.dart';
import '../../../core/config_provider.dart';

class CartScreen extends ConsumerStatefulWidget {
  const CartScreen({super.key});

  @override
  ConsumerState<CartScreen> createState() => _CartScreenState();
}

class _CartScreenState extends ConsumerState<CartScreen> {
  bool _isLoading = false;
  AddressModel? _selectedAddress;

  bool _isPickup = false;
  bool _phoneInitialized = false;
  String? _selectedZoneCode;

  String _paymentMethod = 'card_courier';
  double? _changeFrom;
  double _bonusUsed = 0;

  late TextEditingController _phoneController;
  late TextEditingController _commentController;
  late TextEditingController _bonusController;

  @override
  void initState() {
    super.initState();
    _phoneController = TextEditingController();
    _commentController = TextEditingController();
    _bonusController = TextEditingController(text: "0");
  }

  @override
  void dispose() {
    _phoneController.dispose();
    _commentController.dispose();
    _bonusController.dispose();
    super.dispose();
  }

  void _applySelectedAddress(AddressModel address) {
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
  }

  Future<void> _navigateToAddresses() async {
    final result = await context.push<AddressModel>('/home/saved-addresses?select=true');
    if (result != null && mounted) {
      _applySelectedAddress(result);
    }
  }

  void _selectAddress() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (sheetContext) => _AddressPickerSheet(
        onSelect: (address) {
          _applySelectedAddress(address);
          Navigator.pop(sheetContext);
        },
        onNavigateToAddresses: () {
          Navigator.pop(sheetContext);
          _navigateToAddresses();
        },
      ),
    );
  }

  // --- BOTTOM SHEET: payment method only ---
  void _showPaymentSheet(double finalTotal, List<CartItem> cartItems, {String? deliveryZoneCode}) {
    // Validate before opening
    if (!_isPickup && _selectedAddress == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Пожалуйста, выберите адрес доставки')),
      );
      return;
    }
    if (_phoneController.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Укажите телефон для связи')),
      );
      return;
    }

    String paymentMethod = _paymentMethod;
    int? changeSelection;
    if (_changeFrom != null) {
      changeSelection = _changeFrom!.toInt();
    }
    String? changeError;

    final profile = ref.read(profileProvider).valueOrNull;
    final double availableBonuses = profile?.bonusBalance ?? 0;
    final double maxBonus = double.parse(
      [availableBonuses, finalTotal / 2].reduce((a, b) => a < b ? a : b).toStringAsFixed(2),
    );
    double sheetBonusUsed = _bonusUsed;
    _bonusController.text = sheetBonusUsed > 0 ? sheetBonusUsed.toStringAsFixed(2) : "";
    String? bonusError;

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (sheetContext) {
        return StatefulBuilder(
          builder: (sheetContext, setSheetState) {
            return Material(
              type: MaterialType.transparency,
              child: Container(
                padding: const EdgeInsets.fromLTRB(16, 24, 16, 24),
                decoration: const BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
                ),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Drag handle
                    Center(
                      child: Container(
                        width: 40,
                        height: 4,
                        margin: const EdgeInsets.only(bottom: 16),
                        decoration: BoxDecoration(
                          color: Colors.grey[300],
                          borderRadius: BorderRadius.circular(2),
                        ),
                      ),
                    ),
                    const Text(
                      "Способ оплаты",
                      style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 20),

                    _PaymentOption(
                      title: "Картой курьеру (карта или QR)",
                      icon: Icons.credit_card,
                      value: "card_courier",
                      groupValue: paymentMethod,
                      onChanged: (val) {
                        setSheetState(() {
                          paymentMethod = val!;
                          changeError = null;
                        });
                      },
                    ),
                    const SizedBox(height: 8),
                    _PaymentOption(
                      title: "Наличными",
                      icon: Icons.payments_outlined,
                      value: "cash",
                      groupValue: paymentMethod,
                      onChanged: (val) {
                        setSheetState(() {
                          paymentMethod = val!;
                          changeError = null;
                        });
                      },
                    ),

                    // Change amount (for cash)
                    AnimatedSize(
                      duration: const Duration(milliseconds: 200),
                      curve: Curves.easeInOut,
                      child: paymentMethod == 'cash'
                          ? Padding(
                              padding: const EdgeInsets.only(top: 12),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  const Text(
                                    "Сдача с какой суммы?",
                                    style: TextStyle(
                                      fontSize: 14,
                                      fontWeight: FontWeight.w600,
                                    ),
                                  ),
                                  const SizedBox(height: 8),
                                  Wrap(
                                    spacing: 8,
                                    runSpacing: 8,
                                    children: [
                                      for (final amount in [500, 1000, 5000])
                                        ChoiceChip(
                                          label: Text("$amount \u20bd"),
                                          selected: changeSelection == amount,
                                          onSelected: amount < finalTotal
                                              ? null
                                              : (sel) {
                                                  setSheetState(() {
                                                    changeSelection =
                                                        sel ? amount : null;
                                                    changeError = null;
                                                  });
                                                },
                                          selectedColor:
                                              Colors.green.withValues(alpha: 0.2),
                                          disabledColor: Colors.grey[200],
                                        ),
                                      ChoiceChip(
                                        label: const Text("Без сдачи"),
                                        selected: changeSelection == 0,
                                        onSelected: (sel) {
                                          setSheetState(() {
                                            changeSelection = sel ? 0 : null;
                                            changeError = null;
                                          });
                                        },
                                        selectedColor:
                                            Colors.green.withValues(alpha: 0.2),
                                      ),
                                    ],
                                  ),
                                  if (changeSelection != null &&
                                      changeSelection! > 0)
                                    Padding(
                                      padding: const EdgeInsets.only(top: 8),
                                      child: Text(
                                        "Сдача вам: ${changeSelection! - finalTotal.toInt()} \u20bd",
                                        style: const TextStyle(
                                          fontSize: 14,
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
                                        style: const TextStyle(
                                          color: Colors.red,
                                          fontSize: 13,
                                        ),
                                      ),
                                    ),
                                ],
                              ),
                            )
                          : const SizedBox.shrink(),
                    ),

                    // --- Bonus usage ---
                    if (availableBonuses > 0) ...[
                      const SizedBox(height: 20),
                      const Text(
                        "Списание бонусов",
                        style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        "Доступно: ${availableBonuses.toStringAsFixed(2)} бонусов "
                        "(макс. ${maxBonus.toStringAsFixed(2)})",
                        style: TextStyle(fontSize: 13, color: Colors.grey[600]),
                      ),
                      const SizedBox(height: 8),
                      TextField(
                        controller: _bonusController,
                        keyboardType: const TextInputType.numberWithOptions(decimal: true),
                        inputFormatters: [
                          TextInputFormatter.withFunction((oldValue, newValue) {
                            if (newValue.text.isEmpty) return newValue;
                            // Normalize comma to dot
                            final normalized = newValue.text.replaceAll(',', '.');
                            // Allow only digits, one dot, up to 2 decimal places
                            if (!RegExp(r'^\d*\.?\d{0,2}$').hasMatch(normalized)) {
                              return oldValue;
                            }
                            if (normalized != newValue.text) {
                              return newValue.copyWith(
                                text: normalized,
                                selection: TextSelection.collapsed(
                                  offset: normalized.length,
                                ),
                              );
                            }
                            return newValue;
                          }),
                        ],
                        decoration: InputDecoration(
                          labelText: "Сумма списания",
                          suffixText: "макс. ${maxBonus.toStringAsFixed(2)}",
                          filled: true,
                          fillColor: Colors.grey[100],
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(12),
                            borderSide: BorderSide.none,
                          ),
                          contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                          errorText: bonusError,
                        ),
                        onChanged: (val) {
                          final normalized = val.replaceAll(',', '.');
                          final parsed = double.tryParse(normalized) ?? 0;
                          setSheetState(() {
                            if (parsed < 0) {
                              bonusError = null;
                              sheetBonusUsed = 0;
                              _bonusController.text = "";
                              _bonusController.selection = const TextSelection.collapsed(offset: 0);
                            } else if (parsed > maxBonus) {
                              bonusError = null;
                              sheetBonusUsed = maxBonus;
                              _bonusController.text = maxBonus.toStringAsFixed(2);
                              _bonusController.selection = TextSelection.collapsed(
                                offset: _bonusController.text.length,
                              );
                            } else {
                              bonusError = null;
                              sheetBonusUsed = parsed;
                            }
                          });
                        },
                      ),
                      if (sheetBonusUsed > 0)
                        Padding(
                          padding: const EdgeInsets.only(top: 8),
                          child: Text(
                            "К оплате: ${(finalTotal - sheetBonusUsed).toStringAsFixed(2)} \u20bd",
                            style: const TextStyle(
                              fontSize: 15,
                              fontWeight: FontWeight.w600,
                              color: Color(0xFF4CAF50),
                            ),
                          ),
                        ),
                    ],

                    const SizedBox(height: 24),

                    // Confirm button
                    SizedBox(
                      width: double.infinity,
                      height: 54,
                      child: ElevatedButton(
                        onPressed: () {
                          if (paymentMethod == 'cash' &&
                              changeSelection == null) {
                            setSheetState(() {
                              changeError = "Выберите сумму";
                            });
                            return;
                          }

                          setState(() {
                            _paymentMethod = paymentMethod;
                            _changeFrom = (paymentMethod == 'cash' &&
                                    changeSelection != null &&
                                    changeSelection != 0)
                                ? changeSelection!.toDouble()
                                : null;
                            _bonusUsed = sheetBonusUsed;
                          });
                          Navigator.pop(sheetContext);
                          _submitOrder(finalTotal, cartItems, deliveryZoneCode: deliveryZoneCode);
                        },
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF4CAF50),
                          foregroundColor: Colors.white,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(16),
                          ),
                          elevation: 0,
                        ),
                        child: Text(
                          "Подтвердить \u00b7 ${finalTotal.formatPrice()}",
                          style: const TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                          ),
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

  Future<void> _submitOrder(double totalPrice, List<CartItem> items, {String? deliveryZoneCode}) async {
    if (!_isPickup && _selectedAddress == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Пожалуйста, выберите адрес доставки')),
      );
      return;
    }

    if (_phoneController.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Укажите телефон для связи с курьером')),
      );
      return;
    }

    setState(() => _isLoading = true);

    try {
      final authService = ref.read(authServiceProvider);
      final realUserId = await authService.getSavedUserId();
      if (realUserId == null) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Ошибка авторизации. Войдите заново.'),
              backgroundColor: Colors.red,
            ),
          );
          setState(() => _isLoading = false);
        }
        return;
      }

      final addressToSend = _isPickup
          ? "Самовывоз"
          : _selectedAddress!.fullAddress;

      String comment = _commentController.text;
      if (_paymentMethod == 'cash' && _changeFrom != null) {
        final changeAmount = _changeFrom!.toInt() - totalPrice.toInt();
        final changeLine = 'СДАЧА с ${_changeFrom!.toInt()} рб. Сдача клиенту: $changeAmount рб';
        comment = comment.isEmpty ? changeLine : '$comment\n$changeLine';
      }

      final orderId = await ref
          .read(orderServiceProvider)
          .createOrder(
            address: addressToSend,
            phone: _phoneController.text,
            comment: comment,
            paymentMethod: _paymentMethod,
            totalPrice: totalPrice,
            items: items,
            userId: realUserId,
            fulfillmentType: _isPickup ? "pickup" : "delivery",
            deliveryZoneCode: deliveryZoneCode,
            bonusUsed: _bonusUsed,
          );

      if (orderId != null) {
        ref.read(cartProvider.notifier).clear();
        setState(() {
          _bonusUsed = 0;
          _bonusController.text = "";
        });
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Заказ успешно оформлен! 🎉'),
              backgroundColor: Colors.green,
            ),
          );
          context.go(
            Uri(
              path: '/home/order-status/$orderId',
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
        String message = 'Ошибка оформления заказа';
        if (e is DioException && e.response?.data is Map) {
          final errors = e.response!.data as Map;
          final parts = <String>[];
          errors.forEach((key, value) {
            if (value is List) {
              parts.add(value.join(', '));
            }
          });
          if (parts.isNotEmpty) message = parts.join('\n');
        }
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(message), backgroundColor: Colors.red),
        );
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (!_phoneInitialized) {
      final profile = ref.read(profileProvider);
      final phone = profile.valueOrNull?.phone ?? "";
      _phoneController.text = phone;
      _phoneInitialized = true;
    }

    final cartItems = ref.watch(cartProvider);
    final productsTotal = ref.watch(cartTotalProvider);

    final zonesAsync = _isPickup ? null : ref.watch(deliveryZonesProvider);
    final bool zonesLoading = !_isPickup && zonesAsync != null && zonesAsync.isLoading;
    final bool zonesError = !_isPickup && zonesAsync != null && zonesAsync.hasError;
    final zones = zonesAsync?.valueOrNull ?? [];

    // Compute effective zone code without mutating state in build
    final String? effectiveZoneCode;
    if (_isPickup || zones.isEmpty) {
      effectiveZoneCode = null;
    } else {
      final currentValid = _selectedZoneCode != null &&
          zones.any((z) => z.productCode == _selectedZoneCode);
      if (currentValid) {
        effectiveZoneCode = _selectedZoneCode;
      } else {
        final defaultZone = zones.where((z) => z.isDefault).firstOrNull ?? zones.first;
        effectiveZoneCode = defaultZone.productCode;
        // Schedule state update for next frame
        WidgetsBinding.instance.addPostFrameCallback((_) {
          if (mounted) setState(() => _selectedZoneCode = effectiveZoneCode);
        });
      }
    }

    final bool zonesEmpty = !_isPickup && !zonesLoading && !zonesError && zones.isEmpty;
    final selectedZone = zones.where((z) => z.productCode == effectiveZoneCode).firstOrNull;
    final double? deliveryCostOrNull = _isPickup ? 0.0 : selectedZone?.price;
    final double finalTotal = productsTotal + (deliveryCostOrNull ?? 0.0);

    return Scaffold(
      backgroundColor: const Color(0xFFF9F9F9),
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
                          // --- Card 1: Your order ---
                          _Card(
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
                                ...cartItems.asMap().entries.map((entry) {
                                  final index = entry.key;
                                  final item = entry.value;
                                  return Column(
                                    children: [
                                      _CartItemRow(item: item),
                                      if (index < cartItems.length - 1)
                                        const Divider(height: 1),
                                    ],
                                  );
                                }),
                              ],
                            ),
                          ),

                          const SizedBox(height: 16),

                          // --- Card 2: Delivery details ---
                          _Card(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Text(
                                  "Детали доставки",
                                  style: TextStyle(
                                    fontSize: 18,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                                const SizedBox(height: 12),

                                Container(
                                  decoration: BoxDecoration(
                                    color: Colors.grey[100],
                                    borderRadius: BorderRadius.circular(12),
                                  ),
                                  child: SwitchListTile(
                                    contentPadding:
                                        const EdgeInsets.symmetric(horizontal: 12),
                                    title: const Text(
                                      "Самовывоз",
                                      style: TextStyle(fontWeight: FontWeight.bold),
                                    ),
                                    subtitle: const Text(
                                      "Заберу заказ сам из магазина",
                                      style: TextStyle(
                                        color: Colors.grey,
                                        fontSize: 13,
                                      ),
                                    ),
                                    value: _isPickup,
                                    onChanged: (v) {
                                      setState(() {
                                        _isPickup = v;
                                        if (_isPickup) _selectedAddress = null;
                                      });
                                    },
                                  ),
                                ),

                                const SizedBox(height: 12),

                                if (!_isPickup && zones.isNotEmpty) ...[
                                  InputDecorator(
                                    decoration: InputDecoration(
                                      labelText: "Зона доставки",
                                      border: OutlineInputBorder(
                                        borderRadius: BorderRadius.circular(12),
                                      ),
                                      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                                    ),
                                    child: DropdownButtonHideUnderline(
                                      child: DropdownButton<String>(
                                        value: effectiveZoneCode,
                                        isExpanded: true,
                                        items: zones.map((z) => DropdownMenuItem(
                                          value: z.productCode,
                                          child: Text("${z.name} — ${z.price.formatPrice()}"),
                                        )).toList(),
                                        onChanged: (v) {
                                          setState(() {
                                            _selectedZoneCode = v;
                                          });
                                        },
                                      ),
                                    ),
                                  ),
                                  const SizedBox(height: 12),
                                ],

                                if (zonesEmpty) ...[
                                  Container(
                                    padding: const EdgeInsets.all(12),
                                    decoration: BoxDecoration(
                                      color: Colors.orange[50],
                                      borderRadius: BorderRadius.circular(12),
                                    ),
                                    child: const Row(
                                      children: [
                                        Icon(Icons.info_outline, color: Colors.orange, size: 20),
                                        SizedBox(width: 8),
                                        Expanded(
                                          child: Text(
                                            "Нет доступных зон доставки",
                                            style: TextStyle(color: Colors.orange, fontSize: 14),
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                  const SizedBox(height: 12),
                                ],

                                if (!_isPickup) ...[
                                  InkWell(
                                    onTap: _selectAddress,
                                    borderRadius: BorderRadius.circular(12),
                                    child: Container(
                                      padding: const EdgeInsets.all(16),
                                      decoration: BoxDecoration(
                                        color: Colors.grey[100],
                                        borderRadius: BorderRadius.circular(12),
                                      ),
                                      child: Row(
                                        children: [
                                          const Icon(
                                            Icons.location_on_outlined,
                                            color: Color(0xFF4CAF50),
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
                                                    fontSize: 15,
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
                                ],

                                TextField(
                                  controller: _phoneController,
                                  keyboardType: TextInputType.phone,
                                  decoration: InputDecoration(
                                    labelText: "Телефон для связи",
                                    prefixIcon: const Icon(
                                      Icons.phone_outlined,
                                      color: Colors.grey,
                                    ),
                                    filled: true,
                                    fillColor: Colors.grey[100],
                                    border: OutlineInputBorder(
                                      borderRadius: BorderRadius.circular(12),
                                      borderSide: BorderSide.none,
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
                                    prefixIcon: const Icon(
                                      Icons.comment_outlined,
                                      color: Colors.grey,
                                    ),
                                    filled: true,
                                    fillColor: Colors.grey[100],
                                    border: OutlineInputBorder(
                                      borderRadius: BorderRadius.circular(12),
                                      borderSide: BorderSide.none,
                                    ),
                                    contentPadding: const EdgeInsets.symmetric(
                                      horizontal: 16,
                                      vertical: 14,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),

                          const SizedBox(height: 16),

                          // --- Card 3: Total ---
                          _Card(
                            child: Column(
                              children: [
                                _SummaryRow(
                                  title: "Сумма",
                                  value: productsTotal.formatPrice(),
                                ),
                                const SizedBox(height: 8),
                                _SummaryRow(
                                  title: "Доставка",
                                  value: _isPickup
                                      ? "Самовывоз"
                                      : zonesLoading
                                          ? "..."
                                          : zonesError
                                              ? "Ошибка"
                                              : zonesEmpty
                                                  ? "Недоступна"
                                                  : deliveryCostOrNull?.formatPrice() ?? "...",
                                ),
                                if (_bonusUsed > 0) ...[
                                  const SizedBox(height: 8),
                                  _SummaryRow(
                                    title: "Бонусы",
                                    value: "-${_bonusUsed.toStringAsFixed(2)} \u20bd",
                                  ),
                                ],
                                const SizedBox(height: 12),
                                Row(
                                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                  children: [
                                    const Text(
                                      "К оплате",
                                      style: TextStyle(
                                        fontSize: 20,
                                        fontWeight: FontWeight.bold,
                                      ),
                                    ),
                                    Text(
                                      deliveryCostOrNull != null
                                          ? (finalTotal - _bonusUsed).formatPrice()
                                          : "...",
                                      style: const TextStyle(
                                        fontSize: 20,
                                        fontWeight: FontWeight.bold,
                                        color: Color(0xFF4CAF50),
                                      ),
                                    ),
                                  ],
                                ),
                              ],
                            ),
                          ),

                          const SizedBox(height: 20),
                        ],
                      ),
                    ),
                  ),
                ),

                // --- BOTTOM PANEL: button only ---
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
                    child: SizedBox(
                      width: double.infinity,
                      height: 54,
                      child: zonesError
                          ? ElevatedButton.icon(
                              onPressed: () => ref.invalidate(deliveryZonesProvider),
                              icon: const Icon(Icons.refresh),
                              label: const Text(
                                "Не удалось загрузить цену доставки. Повторить",
                                style: TextStyle(fontSize: 14),
                              ),
                              style: ElevatedButton.styleFrom(
                                backgroundColor: Colors.red[400],
                                foregroundColor: Colors.white,
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(16),
                                ),
                                elevation: 0,
                              ),
                            )
                          : ElevatedButton(
                              onPressed: _isLoading || deliveryCostOrNull == null
                                  ? null
                                  : () => _showPaymentSheet(
                                        finalTotal,
                                        cartItems,
                                        deliveryZoneCode: _isPickup ? null : effectiveZoneCode,
                                      ),
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
                                  : Text(
                                      deliveryCostOrNull != null
                                          ? "Оформить заказ \u00b7 ${finalTotal.formatPrice()}"
                                          : zonesEmpty
                                              ? "Доставка недоступна"
                                              : "Загрузка...",
                                      style: const TextStyle(
                                        fontSize: 18,
                                        fontWeight: FontWeight.bold,
                                      ),
                                    ),
                            ),
                    ),
                  ),
                ),
              ],
            ),
    );
  }
}

// --- Payment option widget ---
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

// --- Address picker widget (bottom sheet) ---
class _AddressPickerSheet extends ConsumerWidget {
  final Function(AddressModel) onSelect;
  final VoidCallback onNavigateToAddresses;
  const _AddressPickerSheet({
    required this.onSelect,
    required this.onNavigateToAddresses,
  });
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
                      onPressed: onNavigateToAddresses,
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
              onPressed: onNavigateToAddresses,
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
                  item.product.price.formatPrice(),
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
        padding: const EdgeInsets.all(8),
        decoration: BoxDecoration(
          color: Colors.grey[200],
          borderRadius: BorderRadius.circular(8),
        ),
        child: Icon(icon, size: 22, color: Colors.grey[700]),
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
