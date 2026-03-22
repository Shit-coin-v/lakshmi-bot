import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/api_client.dart';
import '../models/bonus_history_item.dart';

final bonusHistoryServiceProvider = Provider((ref) => BonusHistoryService());

class BonusHistoryService {
  final Dio _dio = ApiClient().dio;

  Future<BonusHistoryResponse> getBonusHistory({String? cursor}) async {
    final queryParams = <String, dynamic>{};
    if (cursor != null) {
      queryParams['cursor'] = cursor;
    }

    final response = await _dio.get(
      '/api/customer/me/bonus-history/',
      queryParameters: queryParams,
    );

    return BonusHistoryResponse.fromJson(response.data as Map<String, dynamic>);
  }
}
