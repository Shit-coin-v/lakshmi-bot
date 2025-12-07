import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../auth/services/auth_service.dart';
import '../../cart/providers/cart_provider.dart';

class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // Данные заглушки
    const String userName = "Иванов Иван Иванович";
    const String userEmail = "ivanov.ii@example.com";
    const String userPhone = "+7 (999) 123-45-67";

    return Scaffold(
      backgroundColor: const Color(0xFFF9F9F9),
      appBar: AppBar(
        title: const Text(
          "Профиль",
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        centerTitle: true,
        backgroundColor: Colors.white,
        elevation: 0,
        foregroundColor: Colors.black,
        actions: [
          IconButton(
            icon: const Icon(Icons.logout, color: Colors.red),
            onPressed: () async {
              await ref.read(authServiceProvider).logout();
              ref.read(cartProvider.notifier).clear();
              if (context.mounted) context.go('/qr-auth');
            },
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          children: [
            // --- АВАТАРКА ---
            Center(
              child: Stack(
                children: [
                  const CircleAvatar(
                    radius: 50,
                    backgroundColor: Colors.grey,
                    child: Icon(Icons.person, size: 60, color: Colors.white),
                  ),
                  Positioned(
                    bottom: 0,
                    right: 0,
                    child: Container(
                      padding: const EdgeInsets.all(6),
                      decoration: const BoxDecoration(
                        color: Colors.green,
                        shape: BoxShape.circle,
                      ),
                      child: const Icon(
                        Icons.edit,
                        color: Colors.white,
                        size: 16,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            const Text(
              userName,
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 4),
            const Text(
              userEmail,
              style: TextStyle(color: Colors.grey),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 32),

            // --- ЛИЧНЫЕ ДАННЫЕ ---
            const _SectionHeader(title: "ЛИЧНЫЕ ДАННЫЕ"),
            const SizedBox(height: 12),
            Container(
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: Colors.grey.shade200),
              ),
              child: const Column(
                children: [
                  _ProfileItem(
                    icon: Icons.badge_outlined,
                    label: "ФИО",
                    value: userName,
                  ),
                  Divider(height: 1, indent: 50),
                  _ProfileItem(
                    icon: Icons.phone_outlined,
                    label: "Номер телефона",
                    value: userPhone,
                  ),
                ],
              ),
            ),

            const SizedBox(height: 24),

            // --- НАСТРОЙКИ ---
            const _SectionHeader(title: "НАСТРОЙКИ"),
            const SizedBox(height: 12),
            Container(
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: Colors.grey.shade200),
              ),
              child: Column(
                children: const [
                  // 👇 ВОТ ОНА - НОВАЯ КНОПКА ЗАКАЗОВ!
                  _SettingsItem(
                    icon: Icons.receipt_long,
                    title: "Мои заказы",
                    route: '/orders', // Ведет на экран заказов
                  ),
                  Divider(height: 1, indent: 50),
                  _SettingsItem(
                    icon: Icons.home_filled,
                    title: "Сохраненные адреса",
                  ),
                  Divider(height: 1, indent: 50),
                  _SettingsItem(
                    icon: Icons.notifications,
                    title: "Настройки уведомлений",
                  ),
                ],
              ),
            ),

            const SizedBox(height: 40),
          ],
        ),
      ),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  final String title;
  const _SectionHeader({required this.title});

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.centerLeft,
      child: Text(
        title,
        style: const TextStyle(
          color: Colors.green,
          fontWeight: FontWeight.bold,
          fontSize: 14,
          letterSpacing: 1.0,
        ),
      ),
    );
  }
}

class _ProfileItem extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;

  const _ProfileItem({
    required this.icon,
    required this.label,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
      child: Row(
        children: [
          Icon(icon, color: Colors.grey, size: 24),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  style: TextStyle(color: Colors.grey[600], fontSize: 12),
                ),
                const SizedBox(height: 2),
                Text(
                  value,
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
          ),
          const Icon(Icons.edit, color: Colors.grey, size: 20),
        ],
      ),
    );
  }
}

// Виджет строки настроек
class _SettingsItem extends StatelessWidget {
  final IconData icon;
  final String title;
  final String? route; // <-- Добавили поддержку маршрутов

  const _SettingsItem({required this.icon, required this.title, this.route});

  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: Icon(icon, color: Colors.grey[700]),
      title: Text(title, style: const TextStyle(fontSize: 16)),
      trailing: const Icon(
        Icons.arrow_forward_ios,
        size: 16,
        color: Colors.grey,
      ),
      onTap: () {
        // Если есть маршрут — переходим
        if (route != null) {
          context.push(route!);
        }
      },
    );
  }
}
