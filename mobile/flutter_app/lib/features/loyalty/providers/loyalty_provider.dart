import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../auth/services/auth_service.dart';
import '../../auth/models/user_model.dart';

/// Провайдер профиля для экрана лояльности.
/// Поддерживает оба метода авторизации: email (JWT) и QR (Telegram).
final loyaltyProfileProvider = FutureProvider<UserModel?>((ref) async {
  final authService = ref.read(authServiceProvider);
  final authMethod = await authService.getSavedAuthMethod();

  UserModel? user;

  if (authMethod == 'email') {
    user = await authService.tryTokenAutoLogin();
  } else if (authMethod == 'qr') {
    final savedQr = await authService.getSavedQr();
    if (savedQr == null) return null;
    user = await authService.loginWithQr(savedQr);
  } else {
    return null;
  }

  if (user == null) return null;

  // Auto-generate QR for email-only users who don't have one yet
  if (user.qrCode == null || user.qrCode!.isEmpty) {
    try {
      await authService.generateUserQr();
      final userId = await authService.getSavedUserId();
      if (userId != null) {
        return await authService.fetchProfile(userId);
      }
    } catch (e) {
      debugPrint('QR generation failed: $e');
    }
  }

  return user;
});
