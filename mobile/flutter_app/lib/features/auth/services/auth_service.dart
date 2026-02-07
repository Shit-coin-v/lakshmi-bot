import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
// Импортируем наш настроенный клиент
import '../../../core/api_client.dart';
import '../models/user_model.dart';

// Провайдер, чтобы мы могли использовать сервис в других местах
final authServiceProvider = Provider((ref) => AuthService());

class AuthService {
  // ИСПОЛЬЗУЕМ НАСТРОЕННЫЙ КЛИЕНТ (С КЛЮЧАМИ)
  final Dio _dio = ApiClient().dio;

  final _storage = const FlutterSecureStorage();

  // Ключи для хранения данных в памяти телефона
  static const _storageQrKey = 'auth_qr_code';
  static const _storageIdKey = 'user_db_id';
  static const _storageTelegramIdKey = 'user_telegram_id';

  // Метод входа
  Future<UserModel> loginWithQr(String qrCode) async {
    await _storage.deleteAll();
    try {
      final response = await _dio.post(
        '/onec/customer',
        data: {"qr_code": qrCode},
      );

      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = response.data;

        if (data['customer'] != null) {
          final user = UserModel.fromJson(data);

          // 1. Сохраняем QR код (чтобы помнить вход)
          await _storage.write(key: _storageQrKey, value: qrCode);

          // 2. ВАЖНО: Сохраняем реальный ID пользователя из базы (если сервер его прислал)
          // (Убедитесь, что в Django views.py вы добавили "id": user.id в ответ)
          if (data['customer']['id'] != null) {
            await _storage.write(
              key: _storageIdKey,
              value: data['customer']['id'].toString(),
            );
          }

          // 3. Сохраняем telegram_id и устанавливаем глобальный header
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

  // Метод выхода
  Future<void> logout() async {
    await _storage.deleteAll(); // Удаляем и QR, и ID
    ApiClient().clearTelegramUserId();
  }

  // Получить сохраненный QR (для авто-входа)
  Future<String?> getSavedQr() async {
    return await _storage.read(key: _storageQrKey);
  }

  // Получить сохраненный ID пользователя (для отправки заказа)
  Future<int?> getSavedUserId() async {
    final idString = await _storage.read(key: _storageIdKey);
    if (idString != null) {
      return int.tryParse(idString);
    }
    return null;
  }

  // Получить сохраненный telegram_id
  Future<int?> getSavedTelegramId() async {
    final idString = await _storage.read(key: _storageTelegramIdKey);
    if (idString != null) {
      return int.tryParse(idString);
    }
    return null;
  }

  // Восстановить X-Telegram-User-Id header из storage (для авто-логина)
  Future<void> restoreTelegramHeader() async {
    final telegramId = await getSavedTelegramId();
    if (telegramId != null) {
      ApiClient().setTelegramUserId(telegramId);
    }
  }
}
