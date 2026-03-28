import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:share_plus/share_plus.dart';
import '../../../../main.dart';
import '../providers/referral_provider.dart';
import '../models/referral_item.dart';

class ReferralScreen extends ConsumerWidget {
  const ReferralScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(referralProvider);

    return Scaffold(
      backgroundColor: const Color(0xFFF9F9F9),
      appBar: AppBar(
        title: const Text(
          'Пригласить друга',
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        centerTitle: true,
        backgroundColor: Colors.white,
        elevation: 0,
        foregroundColor: Colors.black,
      ),
      body: _buildBody(context, ref, state),
    );
  }

  Widget _buildBody(BuildContext context, WidgetRef ref, ReferralState state) {
    if (state.isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (state.error != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(
              'Ошибка загрузки: ${state.error}',
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 10),
            ElevatedButton(
              onPressed: () => ref.read(referralProvider.notifier).load(),
              child: const Text('Повторить'),
            ),
          ],
        ),
      );
    }

    final info = state.info;
    if (info == null) {
      return const Center(child: Text('Нет данных'));
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // --- Referral code card ---
          Container(
            padding: const EdgeInsets.all(24),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: Colors.grey.shade200),
            ),
            child: Column(
              children: [
                const Text(
                  'Ваш код приглашения',
                  style: TextStyle(
                    fontSize: 14,
                    color: Colors.grey,
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  info.referralCode,
                  style: const TextStyle(
                    fontSize: 32,
                    fontWeight: FontWeight.bold,
                    letterSpacing: 4,
                    color: kPrimaryGreen,
                  ),
                ),
                const SizedBox(height: 20),
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: () {
                          Clipboard.setData(
                            ClipboardData(text: info.referralCode),
                          );
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(
                              content: Text('Код скопирован'),
                              duration: Duration(seconds: 2),
                            ),
                          );
                        },
                        icon: const Icon(Icons.copy, size: 18),
                        label: const Text('Скопировать'),
                        style: OutlinedButton.styleFrom(
                          foregroundColor: kPrimaryGreen,
                          side: const BorderSide(color: kPrimaryGreen),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12),
                          ),
                          padding: const EdgeInsets.symmetric(vertical: 12),
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: ElevatedButton.icon(
                        onPressed: () {
                          SharePlus.instance.share(
                            ShareParams(
                              text:
                                  'Устанавливай приложение Lakshmi по моей ссылке и получай бонусы! ${info.referralLink}',
                            ),
                          );
                        },
                        icon: const Icon(Icons.share, size: 18),
                        label: const Text('Поделиться'),
                        style: ElevatedButton.styleFrom(
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12),
                          ),
                          padding: const EdgeInsets.symmetric(vertical: 12),
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),

          const SizedBox(height: 24),

          // --- Stats ---
          const Align(
            alignment: Alignment.centerLeft,
            child: Text(
              'СТАТИСТИКА',
              style: TextStyle(
                color: kPrimaryGreen,
                fontWeight: FontWeight.bold,
                fontSize: 14,
                letterSpacing: 1.0,
              ),
            ),
          ),
          const SizedBox(height: 12),
          Container(
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: Colors.grey.shade200),
            ),
            child: Column(
              children: [
                _StatRow(
                  icon: Icons.person_add,
                  label: 'Зарегистрировались',
                  value: info.stats.registeredCount.toString(),
                ),
                Divider(height: 1, indent: 50, color: Colors.grey.shade200),
                _StatRow(
                  icon: Icons.shopping_bag,
                  label: 'Совершили покупку',
                  value: info.stats.purchasedCount.toString(),
                ),
                Divider(height: 1, indent: 50, color: Colors.grey.shade200),
                _StatRow(
                  icon: Icons.star,
                  label: 'Бонусов получено',
                  value: info.stats.bonusEarned.toStringAsFixed(0),
                ),
              ],
            ),
          ),

          // --- Referrals list ---
          if (state.referrals.isNotEmpty) ...[
            const SizedBox(height: 24),
            const Align(
              alignment: Alignment.centerLeft,
              child: Text(
                'ПРИГЛАШЁННЫЕ',
                style: TextStyle(
                  color: kPrimaryGreen,
                  fontWeight: FontWeight.bold,
                  fontSize: 14,
                  letterSpacing: 1.0,
                ),
              ),
            ),
            const SizedBox(height: 12),
            Container(
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: Colors.grey.shade200),
              ),
              child: ListView.separated(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: state.referrals.length,
                separatorBuilder: (_, __) => Divider(
                  height: 1,
                  indent: 16,
                  color: Colors.grey.shade200,
                ),
                itemBuilder: (context, index) {
                  return _ReferralItemTile(item: state.referrals[index]);
                },
              ),
            ),
          ],

          const SizedBox(height: 40),
        ],
      ),
    );
  }
}

class _StatRow extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;

  const _StatRow({
    required this.icon,
    required this.label,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      child: Row(
        children: [
          Icon(icon, color: Colors.grey, size: 24),
          const SizedBox(width: 16),
          Expanded(
            child: Text(
              label,
              style: const TextStyle(fontSize: 15),
            ),
          ),
          Text(
            value,
            style: const TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }
}

class _ReferralItemTile extends StatelessWidget {
  final ReferralItem item;

  const _ReferralItemTile({required this.item});

  @override
  Widget build(BuildContext context) {
    final dateStr = DateFormat('dd.MM.yyyy', 'ru').format(item.registeredAt);

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Row(
        children: [
          CircleAvatar(
            radius: 20,
            backgroundColor: item.hasPurchased
                ? kPrimaryGreen.withValues(alpha: 0.15)
                : Colors.grey.shade200,
            child: Icon(
              item.hasPurchased ? Icons.check : Icons.person,
              color: item.hasPurchased ? kPrimaryGreen : Colors.grey,
              size: 20,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  item.fullName,
                  style: const TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  dateStr,
                  style: TextStyle(
                    fontSize: 12,
                    color: Colors.grey.shade600,
                  ),
                ),
              ],
            ),
          ),
          _buildStatusBadge(),
        ],
      ),
    );
  }

  Widget _buildStatusBadge() {
    if (item.rewardStatus == 'success') {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: kPrimaryGreen.withValues(alpha: 0.15),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Text(
          '+${item.bonusAmount?.toStringAsFixed(0) ?? "50"}',
          style: const TextStyle(
            color: kPrimaryGreen,
            fontWeight: FontWeight.bold,
            fontSize: 13,
          ),
        ),
      );
    }

    if (item.rewardStatus == 'pending') {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: Colors.orange.withValues(alpha: 0.15),
          borderRadius: BorderRadius.circular(8),
        ),
        child: const Text(
          'Ожидание',
          style: TextStyle(
            color: Colors.orange,
            fontWeight: FontWeight.w500,
            fontSize: 12,
          ),
        ),
      );
    }

    if (!item.hasPurchased) {
      return Text(
        'Нет покупок',
        style: TextStyle(
          color: Colors.grey.shade500,
          fontSize: 12,
        ),
      );
    }

    return const SizedBox.shrink();
  }
}
