import 'dart:io';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../auth/models/user_model.dart';
import '../services/profile_service.dart';

// Этот провайдер загружает профиль и следит за ним
final profileProvider = AsyncNotifierProvider<ProfileNotifier, UserModel>(() {
  return ProfileNotifier();
});

class ProfileNotifier extends AsyncNotifier<UserModel> {
  @override
  Future<UserModel> build() async {
    return ref.read(profileServiceProvider).getProfile();
  }

  // Метод для обновления текстовых данных (ФИО, телефон, email)
  Future<void> updateData({String? name, String? phone, String? email, bool? newsletterEnabled}) async {
    state = const AsyncValue.loading(); // Показываем загрузку
    try {
      // 1. Отправляем на сервер
      await ref
          .read(profileServiceProvider)
          .updateProfile(fullName: name, phone: phone, email: email, newsletterEnabled: newsletterEnabled);

      // 2. Обновляем данные локально (перезапрашиваем с сервера)
      final newUser = await ref.read(profileServiceProvider).getProfile();
      state = AsyncValue.data(newUser);
    } catch (e, stack) {
      state = AsyncValue.error(e, stack);
    }
  }

  // 👇 ДОБАВЛЕННЫЙ МЕТОД ДЛЯ ЗАГРУЗКИ АВАТАРКИ
  Future<void> uploadUserAvatar(File file) async {
    // Можно включить loading, но иногда лучше оставить старую аватарку, пока грузится новая
    // state = const AsyncValue.loading();

    try {
      // 1. Загружаем файл через сервис
      await ref.read(profileServiceProvider).uploadAvatar(file);

      // 2. Получаем обновленный профиль (с новой ссылкой на картинку)
      final newUser = await ref.read(profileServiceProvider).getProfile();
      state = AsyncValue.data(newUser);
    } catch (e, stack) {
      state = AsyncValue.error(e, stack);
    }
  }
}
