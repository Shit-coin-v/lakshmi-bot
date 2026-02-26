import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:qr_flutter/qr_flutter.dart';
import '../providers/loyalty_provider.dart';

class LoyaltyScreen extends ConsumerWidget {
  const LoyaltyScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final profileAsync = ref.watch(loyaltyProfileProvider);

    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        title: const Text(
          'Моя карта',
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        centerTitle: true,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.refresh(loyaltyProfileProvider),
            tooltip: 'Обновить баланс',
          ),
        ],
      ),
      body: profileAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, stack) => Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.wifi_off, size: 50, color: Colors.grey),
              const SizedBox(height: 10),
              Text(
                'Не удалось загрузить данные:\n$err',
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 10),
              ElevatedButton(
                onPressed: () => ref.refresh(loyaltyProfileProvider),
                child: const Text('Повторить'),
              ),
            ],
          ),
        ),
        data: (user) {
          if (user == null) {
            return const Center(
              child: Text("Ошибка авторизации. Перезайдите в приложение."),
            );
          }

          return SingleChildScrollView(
            padding: const EdgeInsets.all(20),
            child: Column(
              children: [
                const SizedBox(height: 20),

                // --- LOYALTY CARD ---
                Container(
                  width: double.infinity,
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      colors: [
                        Color(0xFF4CAF50),
                        Color(0xFF2E7D32),
                      ], // Brand gradient
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                    ),
                    borderRadius: BorderRadius.circular(24),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.green.withValues(alpha: 0.4),
                        blurRadius: 20,
                        offset: const Offset(0, 10),
                      ),
                    ],
                  ),
                  child: Column(
                    children: [
                      const SizedBox(height: 30),

                      // White background for QR code
                      Container(
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(16),
                        ),
                        child: (user.qrCode != null && user.qrCode!.isNotEmpty)
                            ? QrImageView(
                                data: user.qrCode!,
                                version: QrVersions.auto,
                                size: 200.0,
                                backgroundColor: Colors.white,
                              )
                            : Column(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Icon(Icons.qr_code_scanner,
                                      size: 80, color: Colors.grey[400]),
                                  const SizedBox(height: 12),
                                  Text(
                                    'QR-код создаётся...',
                                    style: TextStyle(
                                        color: Colors.grey[600], fontSize: 14),
                                  ),
                                  const SizedBox(height: 12),
                                  ElevatedButton(
                                    onPressed: () =>
                                        ref.refresh(loyaltyProfileProvider),
                                    child: const Text('Обновить'),
                                  ),
                                ],
                              ),
                      ),

                      const SizedBox(height: 20),

                      Text(
                        user.fullName ??
                            "Уважаемый клиент", // Use data from model
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 18,
                          fontWeight: FontWeight.w500,
                        ),
                      ),

                      const SizedBox(height: 30),
                    ],
                  ),
                ),

                const SizedBox(height: 40),

                // --- BONUS BALANCE ---
                Container(
                  padding: const EdgeInsets.all(24),
                  width: double.infinity,
                  decoration: BoxDecoration(
                    color: Colors.grey[50],
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: Colors.grey[200]!),
                  ),
                  child: Column(
                    children: [
                      Text(
                        "Ваш баланс",
                        style: TextStyle(color: Colors.grey[600], fontSize: 16),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        "${user.bonusBalance.toStringAsFixed(0)} Б",
                        style: const TextStyle(
                          color: Colors.green, // kPrimaryGreen
                          fontSize: 42,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 8),
                      const Text(
                        "Покажите QR-код на кассе\nдля начисления или списания",
                        textAlign: TextAlign.center,
                        style: TextStyle(color: Colors.grey),
                      ),
                    ],
                  ),
                ),

                const SizedBox(height: 30),

                // --- RECENT TRANSACTIONS ---
                const Align(
                  alignment: Alignment.centerLeft,
                  child: Text(
                    "Последние операции",
                    style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                  ),
                ),
                const SizedBox(height: 16),

                // Placeholder transactions (not yet in API)
                _TransactionTile(
                  title: "Покупка продуктов",
                  date: "Сегодня, 14:30",
                  amount: "+ 125 Б",
                  isPositive: true,
                ),
                _TransactionTile(
                  title: "Списание бонусов",
                  date: "Вчера, 18:15",
                  amount: "- 50 Б",
                  isPositive: false,
                ),
                _TransactionTile(
                  title: "Приветственный бонус",
                  date: "01 дек, 09:00",
                  amount: "+ 500 Б",
                  isPositive: true,
                ),

                const SizedBox(height: 20),
              ],
            ),
          );
        },
      ),
    );
  }
}

// Widget for a single transaction row
class _TransactionTile extends StatelessWidget {
  final String title;
  final String date;
  final String amount;
  final bool isPositive;

  const _TransactionTile({
    required this.title,
    required this.date,
    required this.amount,
    required this.isPositive,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.grey[100]!),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.03),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: isPositive
                  ? Colors.green.withValues(alpha: 0.1)
                  : Colors.orange.withValues(alpha: 0.1),
              shape: BoxShape.circle,
            ),
            child: Icon(
              isPositive ? Icons.add : Icons.remove,
              color: isPositive ? Colors.green : Colors.orange,
              size: 20,
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 16,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  date,
                  style: TextStyle(color: Colors.grey[500], fontSize: 13),
                ),
              ],
            ),
          ),
          Text(
            amount,
            style: TextStyle(
              color: isPositive ? Colors.green : Colors.black,
              fontWeight: FontWeight.bold,
              fontSize: 16,
            ),
          ),
        ],
      ),
    );
  }
}
