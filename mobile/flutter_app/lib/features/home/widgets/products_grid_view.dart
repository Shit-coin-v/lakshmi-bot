import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers/products_list_provider.dart';
import 'product_card.dart';

/// Сетка товаров с infinite-scroll пагинацией и pull-to-refresh.
/// Привязана к ProductsListKey (search + categoryId) — при смене ключа
/// автоматически перезагружается с первой страницы.
class ProductsGridView extends ConsumerStatefulWidget {
  final ProductsListKey listKey;
  final String emptyMessage;
  final IconData emptyIcon;

  const ProductsGridView({
    super.key,
    required this.listKey,
    this.emptyMessage = 'Ничего не найдено',
    this.emptyIcon = Icons.search_off,
  });

  @override
  ConsumerState<ProductsGridView> createState() => _ProductsGridViewState();
}

class _ProductsGridViewState extends ConsumerState<ProductsGridView> {
  static const _scrollThreshold = 200.0;

  late final ScrollController _scrollController;

  @override
  void initState() {
    super.initState();
    _scrollController = ScrollController()..addListener(_onScroll);
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  void _onScroll() {
    if (!_scrollController.hasClients) return;
    final position = _scrollController.position;
    if (position.pixels >= position.maxScrollExtent - _scrollThreshold) {
      ref.read(productsListProvider(widget.listKey).notifier).loadMore();
    }
  }

  @override
  Widget build(BuildContext context) {
    final asyncState = ref.watch(productsListProvider(widget.listKey));

    return asyncState.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (err, _) => _buildError(err),
      data: (state) => _buildBody(state),
    );
  }

  Widget _buildError(Object err) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text('Ошибка: $err', textAlign: TextAlign.center),
          const SizedBox(height: 10),
          ElevatedButton(
            onPressed: () =>
                ref.invalidate(productsListProvider(widget.listKey)),
            child: const Text('Повторить'),
          ),
        ],
      ),
    );
  }

  Widget _buildBody(ProductsListState state) {
    if (state.items.isEmpty) {
      return RefreshIndicator(
        onRefresh: () =>
            ref.read(productsListProvider(widget.listKey).notifier).refresh(),
        child: ListView(
          // ListView чтобы RefreshIndicator работал на пустом списке.
          children: [
            const SizedBox(height: 80),
            Icon(widget.emptyIcon, size: 60, color: Colors.grey[300]),
            const SizedBox(height: 10),
            Text(
              widget.emptyMessage,
              textAlign: TextAlign.center,
              style: const TextStyle(color: Colors.grey),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: () =>
          ref.read(productsListProvider(widget.listKey).notifier).refresh(),
      child: CustomScrollView(
        controller: _scrollController,
        slivers: [
          SliverPadding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 0),
            sliver: SliverGrid(
              gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: 2,
                childAspectRatio: 0.55,
                crossAxisSpacing: 16,
                mainAxisSpacing: 16,
              ),
              delegate: SliverChildBuilderDelegate(
                (context, index) => ProductCard(product: state.items[index]),
                childCount: state.items.length,
              ),
            ),
          ),
          SliverToBoxAdapter(child: _buildFooter(state)),
        ],
      ),
    );
  }

  Widget _buildFooter(ProductsListState state) {
    if (state.loadMoreError != null) {
      return Padding(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 96),
        child: Column(
          children: [
            const Text(
              'Не удалось загрузить',
              style: TextStyle(color: Colors.red),
            ),
            const SizedBox(height: 8),
            TextButton(
              onPressed: () => ref
                  .read(productsListProvider(widget.listKey).notifier)
                  .retryLoadMore(),
              child: const Text('Повторить'),
            ),
          ],
        ),
      );
    }

    if (state.isLoadingMore) {
      return const Padding(
        padding: EdgeInsets.fromLTRB(16, 16, 16, 96),
        child: Center(child: CircularProgressIndicator()),
      );
    }

    // hasMore=false и нет ошибки — пустой footer (сохраняем bottom padding
    // под CartTotalBar).
    return const SizedBox(height: 96);
  }
}
