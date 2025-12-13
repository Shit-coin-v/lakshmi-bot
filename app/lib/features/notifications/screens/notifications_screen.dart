import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import '../providers/notifications_provider.dart';
import '../models/notification_model.dart';

class NotificationsScreen extends ConsumerWidget {
  const NotificationsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final notifications = ref.watch(notificationsProvider);

    // Группируем уведомления перед отображением
    final groupedNotifications = _groupNotifications(notifications);

    return Scaffold(
      backgroundColor: const Color(
        0xFFF9FAFB,
      ), // Очень светлый фон как на макете
      appBar: AppBar(
        title: const Text(
          'Уведомления',
          style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18),
        ),
        centerTitle: true,
        backgroundColor: const Color(0xFFF9FAFB),
        elevation: 0,
        foregroundColor: Colors.black,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.of(context).pop(),
        ),
      ),
      body: notifications.isEmpty
          ? _buildEmptyState()
          : ListView.builder(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
              itemCount: groupedNotifications.length,
              itemBuilder: (context, index) {
                final item = groupedNotifications[index];
                if (item is String) {
                  return _DateHeader(text: item);
                } else if (item is NotificationModel) {
                  return _NotificationCard(notification: item);
                }
                return const SizedBox.shrink();
              },
            ),
    );
  }

  // Логика группировки списка для UI
  List<dynamic> _groupNotifications(List<NotificationModel> notifications) {
    if (notifications.isEmpty) return [];

    // Сортируем по дате (сначала новые)
    final sorted = List<NotificationModel>.from(notifications)
      ..sort((a, b) => b.date.compareTo(a.date));

    final groupedList = <dynamic>[];
    String? lastHeader;

    for (var notification in sorted) {
      final header = _getDateHeader(notification.date);
      if (header != lastHeader) {
        groupedList.add(header);
        lastHeader = header;
      }
      groupedList.add(notification);
    }
    return groupedList;
  }

  String _getDateHeader(DateTime date) {
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final yesterday = today.subtract(const Duration(days: 1));
    final checkDate = DateTime(date.year, date.month, date.day);

    if (checkDate == today) {
      return 'СЕГОДНЯ';
    } else if (checkDate == yesterday) {
      return 'ВЧЕРА';
    } else {
      // Формат "25 МАЯ 2024"
      return DateFormat('d MMMM yyyy', 'ru').format(date).toUpperCase();
    }
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.notifications_none, size: 64, color: Colors.grey[300]),
          const SizedBox(height: 16),
          Text(
            'Уведомлений пока нет',
            style: TextStyle(
              fontSize: 16,
              color: Colors.grey[500],
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }
}

// Виджет заголовка даты
class _DateHeader extends StatelessWidget {
  final String text;
  const _DateHeader({required this.text});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 24, bottom: 12),
      child: Text(
        text,
        style: TextStyle(
          color: Colors.grey[600],
          fontSize: 13,
          letterSpacing: 1.0,
          fontWeight: FontWeight.w500,
        ),
      ),
    );
  }
}

// Виджет карточки уведомления
class _NotificationCard extends ConsumerWidget {
  final NotificationModel notification;

  const _NotificationCard({required this.notification});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(
          20,
        ), // Сильное скругление как на фото
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.03),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Material(
        color: Colors.transparent,
        borderRadius: BorderRadius.circular(20),
        child: InkWell(
          borderRadius: BorderRadius.circular(20),
          onTap: () {
            ref
                .read(notificationsProvider.notifier)
                .markAsRead(notification.id);
            // Можно добавить открытие деталей, если нужно
          },
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Круглая иконка
                Container(
                  width: 48,
                  height: 48,
                  decoration: BoxDecoration(
                    color: const Color(0xFFE8F5E9), // Светло-зеленый фон
                    shape: BoxShape.circle,
                  ),
                  child: Icon(
                    _getIconForType(notification.type),
                    color: const Color(0xFF2E7D32), // Темно-зеленая иконка
                    size: 24,
                  ),
                ),
                const SizedBox(width: 16),
                // Текстовая часть
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        notification.title,
                        style: const TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w700,
                          color: Colors.black87,
                          height: 1.2,
                        ),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        notification.body,
                        style: TextStyle(
                          fontSize: 14,
                          color: Colors.grey[600],
                          height: 1.4,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  IconData _getIconForType(String? type) {
    // Подбор иконок под макет
    switch (type) {
      case 'order': // "Заказ в пути", "Доставлен"
        return Icons.local_shipping_outlined; // Или Icons.shopping_bag_outlined
      case 'promo': // "Новый купон"
        return Icons.confirmation_number_outlined; // Похоже на купон
      case 'bonus': // "Начислены баллы"
        return Icons.card_giftcard;
      case 'news': // "Свежие поступления"
        return Icons.campaign_outlined; // Рупор
      default:
        return Icons.notifications_none_outlined;
    }
  }
}
