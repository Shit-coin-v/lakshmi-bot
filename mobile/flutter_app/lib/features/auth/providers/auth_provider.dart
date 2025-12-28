import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/user_model.dart';
import '../services/auth_service.dart';
import 'package:flutter/foundation.dart';
import '../../../core/push_notification_service.dart';

// Состояние: Либо User (вошли), либо null (не вошли)
class AuthState extends StateNotifier<UserModel?> {
  final Ref _ref;
  final AuthService _authService;

  AuthState(this._ref, this._authService) : super(null) {
    _checkSavedSession();
  }

  // При запуске приложения проверяем, входили ли мы раньше
  Future<void> _checkSavedSession() async {
    final savedQr = await _authService.getSavedQr();
    if (savedQr != null) {
      try {
        // Пробуем обновить данные с сервера
        final user = await _authService.loginWithQr(savedQr);
        state = user;
        await _ref
            .read(pushNotificationServiceProvider)
            .registerTokenForCurrentUser();
      } catch (e) {
        // Если ошибка (нет инета или QR устарел) - просто не входим
        debugPrint("Ошибка авто-входа: $e");
      }
    }
  }

  Future<void> login(String qrCode) async {
    final user = await _authService.loginWithQr(qrCode);
    state = user; // Обновляем состояние, приложение поймет, что мы вошли
    await _ref
        .read(pushNotificationServiceProvider)
        .registerTokenForCurrentUser();
  }

  Future<void> logout() async {
    await _authService.logout();
    state = null;
  }
}

// Глобальный провайдер авторизации
final authProvider = StateNotifierProvider<AuthState, UserModel?>((ref) {
  final authService = ref.watch(authServiceProvider);
  return AuthState(ref, authService);
});
