import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/bonus_history_item.dart';
import '../services/bonus_history_service.dart';

class BonusHistoryState {
  final List<BonusHistoryItem> items;
  final String? nextCursor;
  final bool isLoading;
  final String? error;

  const BonusHistoryState({
    this.items = const [],
    this.nextCursor,
    this.isLoading = false,
    this.error,
  });

  BonusHistoryState copyWith({
    List<BonusHistoryItem>? items,
    String? nextCursor,
    bool? isLoading,
    String? error,
    bool clearCursor = false,
    bool clearError = false,
  }) {
    return BonusHistoryState(
      items: items ?? this.items,
      nextCursor: clearCursor ? null : (nextCursor ?? this.nextCursor),
      isLoading: isLoading ?? this.isLoading,
      error: clearError ? null : (error ?? this.error),
    );
  }
}

class BonusHistoryNotifier extends StateNotifier<BonusHistoryState> {
  final BonusHistoryService _service;

  BonusHistoryNotifier(this._service) : super(const BonusHistoryState());

  Future<void> loadInitial() async {
    state = const BonusHistoryState(isLoading: true);
    try {
      final response = await _service.getBonusHistory();
      state = BonusHistoryState(
        items: response.results,
        nextCursor: response.nextCursor,
      );
    } catch (e) {
      debugPrint('BonusHistory loadInitial error: $e');
      state = BonusHistoryState(error: e.toString());
    }
  }

  Future<void> loadMore() async {
    if (state.isLoading) return;
    if (state.nextCursor == null) return;

    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final response = await _service.getBonusHistory(cursor: state.nextCursor);
      state = BonusHistoryState(
        items: [...state.items, ...response.results],
        nextCursor: response.nextCursor,
      );
    } catch (e) {
      debugPrint('BonusHistory loadMore error: $e');
      // Сохраняем уже загруженные items, не теряем nextCursor
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }
}

final bonusHistoryProvider =
    StateNotifierProvider.autoDispose<BonusHistoryNotifier, BonusHistoryState>(
  (ref) {
    final service = ref.watch(bonusHistoryServiceProvider);
    final notifier = BonusHistoryNotifier(service);
    notifier.loadInitial();
    return notifier;
  },
);
