import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/api_client.dart';
import '../models/referral_info.dart';
import '../models/referral_item.dart';

final referralServiceProvider = Provider((ref) => ReferralService());

class ReferralService {
  final Dio _dio = ApiClient().dio;

  Future<ReferralInfo> getReferralInfo() async {
    final response = await _dio.get('/api/customer/me/referral/');
    return ReferralInfo.fromJson(response.data as Map<String, dynamic>);
  }

  Future<List<ReferralItem>> getReferralList() async {
    final response = await _dio.get('/api/customer/me/referrals/');
    final data = response.data as Map<String, dynamic>;
    final results = data['results'] as List<dynamic>? ?? [];
    return results
        .map((e) => ReferralItem.fromJson(e as Map<String, dynamic>))
        .toList();
  }
}
