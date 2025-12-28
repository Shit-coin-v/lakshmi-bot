import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../auth/services/auth_service.dart';
import '../../auth/models/user_model.dart';

// Провайдер, который загружает профиль пользователя (используя сохраненный QR)
final loyaltyProfileProvider = FutureProvider<UserModel?>((ref) async {
  final authService = ref.read(authServiceProvider);

  // 1. Достаем сохраненный QR из памяти телефона
  final savedQr = await authService.getSavedQr();

  if (savedQr == null) return null;

  // 2. Делаем "тихий" вход, чтобы обновить данные (баланс бонусов)
  // Это работает, так как API /onec/customer возвращает актуального юзера
  try {
    final user = await authService.loginWithQr(savedQr);
    return user;
  } catch (e) {
    // Если ошибка сети - попробуем вернуть хотя бы то, что есть (тут можно доработать кэширование)
    rethrow;
  }
});
