import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/product.dart';
import '../services/products_service.dart';

/// Ключ для family-провайдера. Меняется при смене search или категории —
/// это сбрасывает пагинацию и стартует заново с первой страницы.
class ProductsListKey {
  final String search;
  final int? categoryId;

  const ProductsListKey({required this.search, this.categoryId});

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is ProductsListKey &&
          other.search == search &&
          other.categoryId == categoryId);

  @override
  int get hashCode => Object.hash(search, categoryId);
}

/// Состояние пагинированного списка товаров.
class ProductsListState {
  final List<Product> items;
  final int page;
  final bool hasMore;
  final bool isLoadingMore;
  final Object? loadMoreError;

  const ProductsListState({
    required this.items,
    required this.page,
    required this.hasMore,
    required this.isLoadingMore,
    required this.loadMoreError,
  });

  ProductsListState copyWith({
    List<Product>? items,
    int? page,
    bool? hasMore,
    bool? isLoadingMore,
    Object? loadMoreError = _sentinel,
  }) {
    return ProductsListState(
      items: items ?? this.items,
      page: page ?? this.page,
      hasMore: hasMore ?? this.hasMore,
      isLoadingMore: isLoadingMore ?? this.isLoadingMore,
      loadMoreError: identical(loadMoreError, _sentinel)
          ? this.loadMoreError
          : loadMoreError,
    );
  }
}

const _sentinel = Object();

/// Провайдер списка товаров с пагинацией. autoDispose с keepAlive 5 минут —
/// сохраняет состояние при кратковременном уходе с экрана (например, на
/// детальную карточку товара). При смене ключа (search/categoryId) — старый
/// provider диспозится через autoDispose, новый стартует с page=1.
final productsListProvider = AsyncNotifierProvider.autoDispose
    .family<ProductsListNotifier, ProductsListState, ProductsListKey>(
  ProductsListNotifier.new,
);

class ProductsListNotifier
    extends AutoDisposeFamilyAsyncNotifier<ProductsListState, ProductsListKey> {
  static const _keepAliveTimeout = Duration(minutes: 5);

  @override
  Future<ProductsListState> build(ProductsListKey arg) async {
    // keepAlive — освобождаем кэш через 5 минут после последнего слушателя,
    // чтобы возврат с экрана товара не сбрасывал загруженные страницы.
    final link = ref.keepAlive();
    Timer? timer;
    ref.onDispose(() => timer?.cancel());
    ref.onCancel(() {
      timer = Timer(_keepAliveTimeout, link.close);
    });
    ref.onResume(() {
      timer?.cancel();
    });

    final firstPage = await _fetchPage(arg, 1);
    return ProductsListState(
      items: firstPage.items,
      page: 1,
      hasMore: firstPage.hasMore,
      isLoadingMore: false,
      loadMoreError: null,
    );
  }

  Future<void> loadMore() async {
    final current = state.value;
    if (current == null) return;
    if (current.isLoadingMore || !current.hasMore) return;
    if (current.loadMoreError != null) return;

    state = AsyncData(current.copyWith(isLoadingMore: true));

    try {
      final next = await _fetchPage(arg, current.page + 1);
      state = AsyncData(current.copyWith(
        items: [...current.items, ...next.items],
        page: current.page + 1,
        hasMore: next.hasMore,
        isLoadingMore: false,
      ));
    } catch (e) {
      state = AsyncData(current.copyWith(
        isLoadingMore: false,
        loadMoreError: e,
      ));
    }
  }

  Future<void> retryLoadMore() async {
    final current = state.value;
    if (current == null || current.loadMoreError == null) return;
    state = AsyncData(current.copyWith(loadMoreError: null));
    await loadMore();
  }

  Future<void> refresh() async {
    ref.invalidateSelf();
    await future;
  }

  Future<ProductPage> _fetchPage(ProductsListKey key, int page) {
    final service = ref.read(productsServiceProvider);
    if (key.search.isNotEmpty) {
      return service.getShowcase(search: key.search, page: page);
    }
    if (key.categoryId == null) {
      return service.getShowcase(page: page);
    }
    return service.getProducts(categoryId: key.categoryId, page: page);
  }
}
