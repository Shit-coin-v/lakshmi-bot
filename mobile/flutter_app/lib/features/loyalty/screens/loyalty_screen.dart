import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:qr_flutter/qr_flutter.dart';
import '../providers/loyalty_provider.dart';
import '../models/bonus_history_item.dart';
import '../providers/bonus_history_provider.dart';

class LoyaltyScreen extends ConsumerStatefulWidget {
  const LoyaltyScreen({super.key});

  @override
  ConsumerState<LoyaltyScreen> createState() => _LoyaltyScreenState();
}

class _LoyaltyScreenState extends ConsumerState<LoyaltyScreen> {
  final ScrollController _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
  }

  @override
  void dispose() {
    _scrollController.removeListener(_onScroll);
    _scrollController.dispose();
    super.dispose();
  }

  void _onScroll() {
    if (_scrollController.position.pixels >=
        _scrollController.position.maxScrollExtent - 200) {
      ref.read(bonusHistoryProvider.notifier).loadMore();
    }
  }

  @override
  Widget build(BuildContext context) {
    final profileAsync = ref.watch(loyaltyProfileProvider);
    final historyState = ref.watch(bonusHistoryProvider);

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
            onPressed: () {
              ref.invalidate(loyaltyProfileProvider);
              ref.read(bonusHistoryProvider.notifier).loadInitial();
            },
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
            controller: _scrollController,
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
                      ],
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
                        user.fullName ?? "Уважаемый клиент",
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
                          color: Colors.green,
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

                // --- BONUS HISTORY ---
                const Align(
                  alignment: Alignment.centerLeft,
                  child: Text(
                    "Последние операции",
                    style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                  ),
                ),
                const SizedBox(height: 16),

                _buildBonusHistory(historyState),

                const SizedBox(height: 20),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _buildBonusHistory(BonusHistoryState historyState) {
    // Initial loading
    if (historyState.isLoading && historyState.items.isEmpty) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: 32),
        child: Center(child: CircularProgressIndicator()),
      );
    }

    // Error on initial load
    if (historyState.error != null && historyState.items.isEmpty) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 32),
        child: Center(
          child: Text(
            'Не удалось загрузить историю',
            style: TextStyle(color: Colors.grey[500], fontSize: 15),
          ),
        ),
      );
    }

    // Empty state
    if (historyState.items.isEmpty) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 32),
        child: Center(
          child: Text(
            'История покупок пока пуста',
            style: TextStyle(color: Colors.grey[500], fontSize: 15),
          ),
        ),
      );
    }

    // List of items + optional loading indicator at the bottom
    return Column(
      children: [
        for (final item in historyState.items)
          _BonusHistoryTile(item: item),
        if (historyState.isLoading)
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 16),
            child: Center(child: CircularProgressIndicator()),
          ),
      ],
    );
  }
}

// Widget for a single bonus history row
class _BonusHistoryTile extends StatelessWidget {
  final BonusHistoryItem item;

  const _BonusHistoryTile({required this.item});

  @override
  Widget build(BuildContext context) {
    final dateStr = DateFormat('dd.MM.yyyy, HH:mm').format(item.date);
    final totalStr = '${item.purchaseTotal.toStringAsFixed(0)} \u20BD';

    final hasEarned = item.bonusEarned > 0;
    final hasSpent = item.bonusSpent > 0;

    // Determine icon style based on primary operation
    final isPositive = hasEarned && !hasSpent;

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
                  totalStr,
                  style: const TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 16,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  dateStr,
                  style: TextStyle(color: Colors.grey[500], fontSize: 13),
                ),
              ],
            ),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            mainAxisSize: MainAxisSize.min,
            children: [
              if (hasEarned)
                Text(
                  '+${item.bonusEarned.toStringAsFixed(0)} Б',
                  style: const TextStyle(
                    color: Colors.green,
                    fontWeight: FontWeight.bold,
                    fontSize: 15,
                  ),
                ),
              if (hasEarned && hasSpent)
                const SizedBox(height: 2),
              if (hasSpent)
                Text(
                  '\u2212${item.bonusSpent.toStringAsFixed(0)} Б',
                  style: const TextStyle(
                    color: Colors.red,
                    fontWeight: FontWeight.bold,
                    fontSize: 15,
                  ),
                ),
              if (!hasEarned && !hasSpent)
                Text(
                  '0 Б',
                  style: TextStyle(
                    color: Colors.grey[500],
                    fontWeight: FontWeight.bold,
                    fontSize: 15,
                  ),
                ),
            ],
          ),
        ],
      ),
    );
  }
}
