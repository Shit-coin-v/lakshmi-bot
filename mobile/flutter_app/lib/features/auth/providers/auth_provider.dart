import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/user_model.dart';
import '../services/auth_service.dart';
import 'package:flutter/foundation.dart';
import '../../../core/api_client.dart';
import '../../../core/push_notification_service.dart';

class AuthState extends StateNotifier<UserModel?> {
  final Ref _ref;
  final AuthService _authService;
  StreamSubscription<void>? _forceLogoutSub;

  AuthState(this._ref, this._authService) : super(null) {
    _forceLogoutSub = ApiClient().onForceLogout.listen((_) async {
      await _authService.logout();
      state = null;
    });
    _checkSavedSession();
  }

  @override
  void dispose() {
    _forceLogoutSub?.cancel();
    super.dispose();
  }

  Future<void> _checkSavedSession() async {
    // 1. Try token-based auto-login (email accounts)
    final authMethod = await _authService.getSavedAuthMethod();
    if (authMethod == 'email') {
      try {
        final user = await _authService.tryTokenAutoLogin();
        if (user != null) {
          state = user;
          await _ref
              .read(pushNotificationServiceProvider)
              .registerTokenForCurrentUser();
          return;
        }
      } catch (e) {
        debugPrint("Ошибка авто-входа по токену: $e");
      }
    }

    // 2. Fallback: QR-based auto-login (Telegram accounts)
    final savedQr = await _authService.getSavedQr();
    if (savedQr != null) {
      try {
        final user = await _authService.loginWithQr(savedQr);
        state = user;
        await _ref
            .read(pushNotificationServiceProvider)
            .registerTokenForCurrentUser();
      } catch (e) {
        debugPrint("Ошибка авто-входа по QR: $e");
        await _authService.restoreTelegramHeader();
      }
    }
  }

  Future<void> login(String qrCode) async {
    final user = await _authService.loginWithQr(qrCode);
    state = user;
    await _ref
        .read(pushNotificationServiceProvider)
        .registerTokenForCurrentUser();
  }

  Future<void> loginWithEmail(String email, String password) async {
    final user = await _authService.loginWithEmail(
      email: email,
      password: password,
    );
    state = user;
    await _ref
        .read(pushNotificationServiceProvider)
        .registerTokenForCurrentUser();
  }

  Future<void> register({
    required String email,
    required String password,
    required String fullName,
    String? phone,
  }) async {
    await _authService.register(
      email: email,
      password: password,
      fullName: fullName,
      phone: phone,
    );
    // No state change — user is not created until email verification
  }

  Future<void> completeVerification(UserModel user) async {
    state = user;
    await _ref
        .read(pushNotificationServiceProvider)
        .registerTokenForCurrentUser();
  }

  Future<void> logout() async {
    await _authService.logout();
    state = null;
  }
}

final authProvider = StateNotifierProvider<AuthState, UserModel?>((ref) {
  final authService = ref.watch(authServiceProvider);
  return AuthState(ref, authService);
});
