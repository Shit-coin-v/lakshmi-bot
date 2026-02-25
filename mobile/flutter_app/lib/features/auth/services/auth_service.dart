import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/api_client.dart';
import '../models/user_model.dart';

final authServiceProvider = Provider((ref) => AuthService());

class AuthService {
  final Dio _dio = ApiClient().dio;
  final _storage = const FlutterSecureStorage();

  // Storage keys
  static const _storageQrKey = 'auth_qr_code';
  static const _storageIdKey = 'user_db_id';
  static const _storageTelegramIdKey = 'user_telegram_id';
  static const _storageAuthMethodKey = 'auth_method'; // "qr" or "email"

  // ─── QR login (existing flow) ───

  Future<UserModel> loginWithQr(String qrCode) async {
    try {
      final response = await _dio.post(
        '/onec/customer',
        data: {"qr_code": qrCode},
      );

      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = response.data;

        if (data['customer'] != null) {
          // Clear old session only after successful response
          await _storage.deleteAll();
          await ApiClient().clearTokens();

          final user = UserModel.fromJson(data);

          await _storage.write(key: _storageQrKey, value: qrCode);
          await _storage.write(key: _storageAuthMethodKey, value: 'qr');

          if (data['customer']['id'] != null) {
            await _storage.write(
              key: _storageIdKey,
              value: data['customer']['id'].toString(),
            );
          }

          if (data['customer']['telegram_id'] != null) {
            final telegramId = data['customer']['telegram_id'];
            await _storage.write(
              key: _storageTelegramIdKey,
              value: telegramId.toString(),
            );
            ApiClient().setTelegramUserId(
              telegramId is int ? telegramId : int.parse(telegramId.toString()),
            );
          }

          return user;
        } else {
          throw Exception('Сервер не вернул данные пользователя');
        }
      } else {
        throw Exception('Ошибка сервера: ${response.statusCode}');
      }
    } on DioException catch (e) {
      if (e.response?.statusCode == 404) {
        throw Exception('Пользователь с таким QR-кодом не найден');
      }
      if (e.response?.data != null && e.response?.data['detail'] != null) {
        throw Exception('Ошибка: ${e.response?.data['detail']}');
      }
      throw Exception('Ошибка сети: ${e.message}');
    }
  }

  // ─── Email registration ───

  Future<void> register({
    required String email,
    required String password,
    required String fullName,
    String? phone,
  }) async {
    try {
      await _dio.post('/api/auth/register/', data: {
        'email': email,
        'password': password,
        'full_name': fullName,
        if (phone != null && phone.isNotEmpty) 'phone': phone,
      });
      // No tokens returned — user is created only after email verification
    } on DioException catch (e) {
      final detail = e.response?.data?['detail'];
      if (detail != null) {
        throw Exception(detail.toString());
      }
      throw Exception('Ошибка регистрации: ${e.message}');
    }
  }

  // ─── Email login ───

  Future<UserModel> loginWithEmail({
    required String email,
    required String password,
  }) async {
    try {
      final response = await _dio.post('/api/auth/login/', data: {
        'email': email,
        'password': password,
      });

      final data = response.data;

      // Clear old session only after successful response
      await _storage.deleteAll();
      await ApiClient().clearTokens();

      // Save tokens
      final tokens = data['tokens'];
      await ApiClient().saveTokens(tokens['access'], tokens['refresh']);

      await _storage.write(key: _storageAuthMethodKey, value: 'email');
      await _storage.write(
        key: _storageIdKey,
        value: data['user_id'].toString(),
      );

      if (data['telegram_id'] != null) {
        await _storage.write(
          key: _storageTelegramIdKey,
          value: data['telegram_id'].toString(),
        );
      }

      // Fetch full profile
      return await fetchProfile(data['user_id']);
    } on DioException catch (e) {
      final detail = e.response?.data?['detail'];
      if (detail != null) {
        throw Exception(detail.toString());
      }
      throw Exception('Ошибка входа: ${e.message}');
    }
  }

  // ─── Token-based auto-login ───

  Future<UserModel?> tryTokenAutoLogin() async {
    final refreshToken = await ApiClient().getSavedRefreshToken();
    if (refreshToken == null) return null;

    try {
      final response = await _dio.post('/api/auth/refresh/', data: {
        'refresh': refreshToken,
      });

      final tokens = response.data['tokens'];
      await ApiClient().saveTokens(tokens['access'], tokens['refresh']);

      final userId = await getSavedUserId();
      if (userId == null) return null;

      return await fetchProfile(userId);
    } catch (e) {
      return null;
    }
  }

  // ─── Email verification ───

  Future<UserModel?> verifyEmail(String email, String code) async {
    final response = await _dio.post('/api/auth/verify-email/', data: {
      'email': email,
      'code': code,
    });
    if (response.statusCode != 200) {
      throw Exception(response.data?['detail'] ?? 'Ошибка подтверждения');
    }

    final data = response.data;
    // New registration — tokens are returned
    if (data['tokens'] != null) {
      final tokens = data['tokens'];
      await ApiClient().saveTokens(tokens['access'], tokens['refresh']);
      await _storage.write(key: _storageAuthMethodKey, value: 'email');
      await _storage.write(key: _storageIdKey, value: data['user_id'].toString());
      return await fetchProfile(data['user_id']);
    }
    return null;
  }

  // ─── Password reset ───

  Future<void> resetPassword(String email) async {
    await _dio.post('/api/auth/reset-password/', data: {'email': email});
  }

  Future<void> confirmResetPassword(
      String email, String code, String newPassword) async {
    final response = await _dio.post('/api/auth/reset-password/confirm/', data: {
      'email': email,
      'code': code,
      'new_password': newPassword,
    });
    if (response.statusCode != 200) {
      throw Exception(response.data?['detail'] ?? 'Ошибка сброса пароля');
    }
  }

  // ─── Logout ───

  Future<void> logout() async {
    await _storage.deleteAll();
    ApiClient().clearTelegramUserId();
    await ApiClient().clearTokens();
  }

  // ─── Helpers ───

  Future<UserModel> fetchProfile(int userId) async {
    final response = await _dio.get('/api/customer/$userId/');
    return UserModel.fromJson(response.data);
  }

  Future<String?> getSavedQr() async {
    return await _storage.read(key: _storageQrKey);
  }

  Future<int?> getSavedUserId() async {
    final idString = await _storage.read(key: _storageIdKey);
    if (idString != null) {
      return int.tryParse(idString);
    }
    return null;
  }

  Future<int?> getSavedTelegramId() async {
    final idString = await _storage.read(key: _storageTelegramIdKey);
    if (idString != null) {
      return int.tryParse(idString);
    }
    return null;
  }

  Future<String?> getSavedAuthMethod() async {
    return await _storage.read(key: _storageAuthMethodKey);
  }

  Future<void> restoreTelegramHeader() async {
    final telegramId = await getSavedTelegramId();
    if (telegramId != null) {
      ApiClient().setTelegramUserId(telegramId);
    }
  }

  // ─── Link Telegram by QR scan ───

  Future<Map<String, dynamic>> linkTelegramByQr(int telegramId) async {
    try {
      final response = await _dio.post('/api/auth/link-telegram/by-qr/', data: {
        'telegram_id': telegramId,
      });

      await _storage.write(
        key: _storageTelegramIdKey,
        value: telegramId.toString(),
      );
      ApiClient().setTelegramUserId(telegramId);

      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      final detail = e.response?.data?['detail'];
      if (detail != null) throw Exception(detail.toString());
      throw Exception('Ошибка привязки Telegram: ${e.message}');
    }
  }

  // ─── Generate QR for email-only user ───

  Future<Map<String, dynamic>> generateUserQr() async {
    try {
      final response = await _dio.post('/api/auth/generate-qr/');
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      final detail = e.response?.data?['detail'];
      if (detail != null) throw Exception(detail.toString());
      throw Exception('Ошибка генерации QR: ${e.message}');
    }
  }
}
