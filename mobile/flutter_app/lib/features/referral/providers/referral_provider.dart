import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/referral_info.dart';
import '../models/referral_item.dart';
import '../services/referral_service.dart';

class ReferralState {
  final ReferralInfo? info;
  final List<ReferralItem> referrals;
  final bool isLoading;
  final String? error;

  const ReferralState({
    this.info,
    this.referrals = const [],
    this.isLoading = false,
    this.error,
  });

  ReferralState copyWith({
    ReferralInfo? info,
    List<ReferralItem>? referrals,
    bool? isLoading,
    String? error,
    bool clearError = false,
  }) {
    return ReferralState(
      info: info ?? this.info,
      referrals: referrals ?? this.referrals,
      isLoading: isLoading ?? this.isLoading,
      error: clearError ? null : (error ?? this.error),
    );
  }
}

class ReferralNotifier extends StateNotifier<ReferralState> {
  final ReferralService _service;

  ReferralNotifier(this._service) : super(const ReferralState());

  Future<void> load() async {
    state = const ReferralState(isLoading: true);
    try {
      final results = await Future.wait([
        _service.getReferralInfo(),
        _service.getReferralList(),
      ]);
      state = ReferralState(
        info: results[0] as ReferralInfo,
        referrals: results[1] as List<ReferralItem>,
      );
    } catch (e) {
      debugPrint('Referral load error: $e');
      state = ReferralState(error: e.toString());
    }
  }
}

final referralProvider =
    StateNotifierProvider.autoDispose<ReferralNotifier, ReferralState>(
  (ref) {
    final service = ref.watch(referralServiceProvider);
    final notifier = ReferralNotifier(service);
    notifier.load();
    return notifier;
  },
);
