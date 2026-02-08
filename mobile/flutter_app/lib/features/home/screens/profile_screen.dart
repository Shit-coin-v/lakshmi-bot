import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../auth/services/auth_service.dart';
import '../../cart/providers/cart_provider.dart';
import '../widgets/edit_profile_modal.dart';
import '../providers/profile_provider.dart';
import 'dart:io';
import 'package:image_picker/image_picker.dart';

class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // Слушаем данные от сервера (1С/Django) через провайдер
    final profileAsync = ref.watch(profileProvider);

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
      body: profileAsync.when(
        // 1. Состояние загрузки
        loading: () => const Center(child: CircularProgressIndicator()),

        // 2. Состояние ошибки
        error: (err, stack) => Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text('Ошибка загрузки: $err', textAlign: TextAlign.center),
              const SizedBox(height: 10),
              ElevatedButton(
                onPressed: () => ref.refresh(profileProvider),
                child: const Text('Повторить'),
              ),
            ],
          ),
        ),

        // 3. Данные получены — строим экран
        data: (user) {
          return SingleChildScrollView(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              children: [
                // --- АВАТАРКА ---
                Center(
                  child: Stack(
                    children: [
                      // Кружок с фото или инициалами
                      CircleAvatar(
                        radius: 50,
                        backgroundColor: Colors.grey.shade300,
                        // Если есть URL, показываем картинку, иначе букву
                        backgroundImage: user.avatarUrl != null
                            ? NetworkImage(user.avatarUrl!)
                            : null,
                        child: user.avatarUrl == null
                            ? Text(
                                (user.fullName?.isNotEmpty == true)
                                    ? user.fullName![0]
                                    : "?",
                                style: const TextStyle(
                                  fontSize: 40,
                                  color: Colors.white,
                                ),
                              )
                            : null,
                      ),

                      // Кнопка камеры
                      Positioned(
                        bottom: 0,
                        right: 0,
                        child: GestureDetector(
                          onTap: () async {
                            // 1. Вызываем галерею
                            final ImagePicker picker = ImagePicker();
                            final XFile? image = await picker.pickImage(
                              source: ImageSource.gallery,
                              maxWidth: 512,
                              maxHeight: 512,
                              imageQuality: 85,
                            );

                            if (image != null) {
                              // 2. Если фото выбрано, отправляем на сервер
                              // (Тут нужно вызвать метод провайдера, давай добавим его ниже)
                              await ref
                                  .read(profileProvider.notifier)
                                  .uploadUserAvatar(File(image.path));
                            }
                          },
                          child: Container(
                            padding: const EdgeInsets.all(6),
                            decoration: const BoxDecoration(
                              color: Colors.green,
                              shape: BoxShape.circle,
                            ),
                            child: const Icon(
                              Icons.camera_alt,
                              color: Colors.white,
                              size: 16,
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),

                // Имя под аватаркой
                Text(
                  user.fullName ?? "Гость",
                  style: const TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                  ),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 4),
                // Email под аватаркой
                Text(
                  user.email ?? "Email не указан",
                  style: const TextStyle(color: Colors.grey),
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
                  child: Column(
                    children: [
                      // 1. ФИО (Редактирование через сервер)
                      _ProfileItem(
                        icon: Icons.badge_outlined,
                        label: "ФИО",
                        value: user.fullName ?? "Не указано",
                        onEdit: () {
                          showEditProfileModal(
                            context: context,
                            title: "Редактирование ФИО",
                            initialValue: user.fullName ?? "",
                            onSave: (newValue) {
                              // 👇 ОТПРАВЛЯЕМ НА СЕРВЕР
                              ref
                                  .read(profileProvider.notifier)
                                  .updateData(name: newValue);
                            },
                          );
                        },
                      ),
                      const Divider(height: 1, indent: 50),

                      // 2. Телефон
                      _ProfileItem(
                        icon: Icons.phone_outlined,
                        label: "Номер телефона",
                        value: user.phone ?? "Не указан",
                        onEdit: () {
                          showEditProfileModal(
                            context: context,
                            title: "Номер телефона",
                            initialValue: user.phone ?? "",
                            inputType: TextInputType.phone,
                            onSave: (newValue) {
                              // 👇 ОТПРАВЛЯЕМ НА СЕРВЕР
                              ref
                                  .read(profileProvider.notifier)
                                  .updateData(phone: newValue);
                            },
                          );
                        },
                      ),
                      const Divider(height: 1, indent: 50),

                      // 3. Email
                      _ProfileItem(
                        icon: Icons.email_outlined,
                        label: "Email",
                        value: user.email ?? "Не указан",
                        onEdit: () {
                          showEditProfileModal(
                            context: context,
                            title: "Email",
                            initialValue: user.email ?? "",
                            inputType: TextInputType.emailAddress,
                            onSave: (newValue) {
                              // 👇 ОТПРАВЛЯЕМ НА СЕРВЕР
                              ref
                                  .read(profileProvider.notifier)
                                  .updateData(email: newValue);
                            },
                          );
                        },
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
                      _SettingsItem(
                        icon: Icons.receipt_long,
                        title: "Мои заказы",
                        route: '/orders',
                      ),
                      Divider(height: 1, indent: 50),
                      _SettingsItem(
                        icon: Icons.home_filled,
                        title: "Сохраненные адреса",
                        route: '/saved-addresses',
                      ),
                      Divider(height: 1, indent: 50),
                      _SettingsItem(
                        icon: Icons.notifications,
                        title: "Настройки уведомлений",
                        route: '/notification-settings',
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 40),
              ],
            ),
          );
        },
      ),
    );
  }
}

// --- ВСПОМОГАТЕЛЬНЫЕ ВИДЖЕТЫ ---

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
  final VoidCallback onEdit;

  const _ProfileItem({
    required this.icon,
    required this.label,
    required this.value,
    required this.onEdit,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onEdit, // Вся строка кликабельна
      child: Padding(
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
            IconButton(
              icon: const Icon(Icons.edit, color: Colors.green, size: 20),
              onPressed: onEdit,
            ),
          ],
        ),
      ),
    );
  }
}

class _SettingsItem extends StatelessWidget {
  final IconData icon;
  final String title;
  final String? route;

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
        if (route != null) context.push(route!);
      },
    );
  }
}
