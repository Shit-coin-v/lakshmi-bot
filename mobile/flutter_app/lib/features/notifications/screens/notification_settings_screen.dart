import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/notification_settings_provider.dart';
import '../../home/providers/profile_provider.dart';

class NotificationSettingsScreen extends ConsumerWidget {
  const NotificationSettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final settings = ref.watch(notificationSettingsProvider);
    final notifier = ref.read(notificationSettingsProvider.notifier);
    final profileAsync = ref.watch(profileProvider);

    return Scaffold(
      backgroundColor: const Color(0xFFF9F9F9),
      appBar: AppBar(
        title: const Text('Настройки уведомлений'),
        centerTitle: true,
        backgroundColor: Colors.white,
        surfaceTintColor: Colors.transparent,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Padding(
              padding: EdgeInsets.only(left: 16, bottom: 8, top: 8),
              child: Text(
                'PUSH-УВЕДОМЛЕНИЯ',
                style: TextStyle(
                  color: Colors.grey,
                  fontSize: 13,
                  fontWeight: FontWeight.bold,
                  letterSpacing: 1.0,
                ),
              ),
            ),
            Container(
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
              child: profileAsync.when(
                loading: () => const Padding(
                  padding: EdgeInsets.all(16),
                  child: Center(child: CircularProgressIndicator()),
                ),
                error: (_, __) => const Padding(
                  padding: EdgeInsets.all(16),
                  child: Text('Не удалось загрузить настройки'),
                ),
                data: (user) => Column(
                  children: [
                    _SwitchTile(
                      title: 'Статусы заказов',
                      subtitle: 'Узнавайте, когда заказ собран или едет к вам',
                      value: settings.pushOrders,
                      onChanged: notifier.togglePushOrders,
                    ),
                    const Divider(height: 1, indent: 16),
                    _SwitchTile(
                      title: 'Акции и скидки',
                      subtitle: 'Персональные предложения и новинки',
                      value: user.promoEnabled,
                      onChanged: (value) {
                        ref.read(profileProvider.notifier).updateData(
                          promoEnabled: value,
                        );
                      },
                    ),
                    const Divider(height: 1, indent: 16),
                    _SwitchTile(
                      title: 'Новости магазина',
                      subtitle: 'Открытие новых точек и изменения в графике',
                      value: user.newsEnabled,
                      onChanged: (value) {
                        ref.read(profileProvider.notifier).updateData(
                          newsEnabled: value,
                        );
                      },
                    ),
                    const Divider(height: 1, indent: 16),
                    _SwitchTile(
                      title: 'Общие уведомления',
                      subtitle: 'Важные объявления и обновления',
                      value: user.generalEnabled,
                      onChanged: (value) {
                        ref.read(profileProvider.notifier).updateData(
                          generalEnabled: value,
                        );
                      },
                    ),
                  ],
                ),
              ),
            ),

          ],
        ),
      ),
    );
  }
}

class _SwitchTile extends StatelessWidget {
  final String title;
  final String? subtitle;
  final bool value;
  final ValueChanged<bool> onChanged;

  const _SwitchTile({
    required this.title,
    this.subtitle,
    required this.value,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return SwitchListTile(
      value: value,
      onChanged: onChanged,
      activeTrackColor: const Color(0xFF4CAF50),
      inactiveThumbColor: Colors.white,
      inactiveTrackColor: Colors.grey[300],
      trackOutlineColor: WidgetStateProperty.all(Colors.transparent),

      title: Text(
        title,
        style: const TextStyle(fontWeight: FontWeight.w500, fontSize: 16),
      ),
      subtitle: subtitle != null
          ? Text(
              subtitle!,
              style: TextStyle(color: Colors.grey[600], fontSize: 13),
            )
          : null,
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
    );
  }
}
