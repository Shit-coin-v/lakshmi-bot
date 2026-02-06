import 'dart:io';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/api_client.dart';
import '../../auth/services/auth_service.dart';
import '../../auth/models/user_model.dart';

final profileServiceProvider = Provider((ref) => ProfileService(ref));

class ProfileService {
  final Ref _ref;
  final Dio _dio;

  ProfileService(this._ref, {Dio? dio}) : _dio = dio ?? ApiClient().dio;

  // Получить данные профиля
  Future<UserModel> getProfile() async {
    final userId = await _ref.read(authServiceProvider).getSavedUserId();
    if (userId == null) throw Exception("Не найден ID пользователя");

    // Стучимся в твой новый Endpoint
    final response = await _dio.get('/api/customer/$userId/');
    return UserModel.fromJson(response.data);
  }

  // Обновить данные (PATCH)
  Future<void> updateProfile({
    String? fullName,
    String? phone,
    String? email,
    bool? newsletterEnabled,
    bool? promoEnabled,
    bool? newsEnabled,
    bool? generalEnabled,
  }) async {
    final userId = await _ref.read(authServiceProvider).getSavedUserId();
    if (userId == null) throw Exception("Не найден ID пользователя");

    final Map<String, dynamic> data = {};
    if (fullName != null) data['full_name'] = fullName;
    if (phone != null) data['phone'] = phone;
    if (email != null) data['email'] = email;
    if (newsletterEnabled != null) data['newsletter_enabled'] = newsletterEnabled;
    if (promoEnabled != null) data['promo_enabled'] = promoEnabled;
    if (newsEnabled != null) data['news_enabled'] = newsEnabled;
    if (generalEnabled != null) data['general_enabled'] = generalEnabled;

    await _dio.patch('/api/customer/$userId/', data: data);
  }

  // Метод для загрузки фото
  Future<void> uploadAvatar(File imageFile) async {
    final userId = await _ref.read(authServiceProvider).getSavedUserId();
    if (userId == null) throw Exception("Не найден ID пользователя");

    String fileName = imageFile.path.split('/').last;

    FormData formData = FormData.fromMap({
      "avatar": await MultipartFile.fromFile(
        imageFile.path,
        filename: fileName,
      ),
    });

    // Отправляем PATCH запрос
    await _dio.patch('/api/customer/$userId/', data: formData);
  }
}
