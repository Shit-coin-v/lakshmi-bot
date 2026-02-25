import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mocktail/mocktail.dart';

import 'package:lakshmi_market/features/orders/services/order_service.dart';
import 'package:lakshmi_market/features/cart/models/cart_item.dart';
import 'package:lakshmi_market/features/home/models/product.dart';
import 'package:lakshmi_market/features/auth/services/auth_service.dart';

import '../../../helpers/mocks.dart';

void main() {
  late MockDio mockDio;
  late MockAuthService mockAuth;

  setUp(() {
    mockDio = MockDio();
    mockAuth = MockAuthService();
  });

  ProviderContainer createContainer() {
    return ProviderContainer(overrides: [
      authServiceProvider.overrideWithValue(mockAuth),
      orderServiceProvider
          .overrideWith((ref) => OrderService(dio: mockDio)),
    ]);
  }

  // Helper to create test CartItem instances
  List<CartItem> createTestItems() {
    return [
      CartItem(
        product: Product(
          id: 'P001',
          name: 'Молоко',
          price: 89.90,
          description: 'Свежее молоко',
          stock: 10,
        ),
        quantity: 2,
      ),
      CartItem(
        product: Product(
          id: 'P002',
          name: 'Хлеб',
          price: 45.00,
          description: 'Белый хлеб',
          stock: 25,
        ),
        quantity: 1,
      ),
    ];
  }

  group('Cart OrderService', () {
    test('createOrder sends correct payload and returns id on 201', () async {
      final items = createTestItems();

      when(() => mockDio.post(
            '/api/orders/create/',
            data: any(named: 'data'),
          )).thenAnswer((_) async => Response(
            data: {'id': 99},
            statusCode: 201,
            requestOptions: RequestOptions(path: '/api/orders/create/'),
          ));

      final container = createContainer();
      addTearDown(container.dispose);

      final service = container.read(orderServiceProvider);
      final orderId = await service.createOrder(
        address: 'ул. Пушкина, д.10',
        phone: '+79991234567',
        comment: 'Позвоните заранее',
        paymentMethod: 'cash',
        totalPrice: 224.80,
        items: items,
        userId: 42,
        fulfillmentType: 'delivery',
      );

      expect(orderId, 99);

      final captured = verify(() => mockDio.post(
            '/api/orders/create/',
            data: captureAny(named: 'data'),
          )).captured.single as Map<String, dynamic>;

      expect(captured['customer'], 42);
      expect(captured['address'], 'ул. Пушкина, д.10');
      expect(captured['phone'], '+79991234567');
      expect(captured['comment'], 'Позвоните заранее');
      expect(captured['payment_method'], 'cash');
      expect(captured['fulfillment_type'], 'delivery');
      expect(captured['total_price'], 224.80);
      expect(captured['items'], isA<List>());
      expect((captured['items'] as List).length, 2);

      final firstItem = (captured['items'] as List)[0] as Map<String, dynamic>;
      expect(firstItem['product_code'], 'P001');
      expect(firstItem['quantity'], 2);
      expect(firstItem['price_at_moment'], 89.90);
    });

    test('createOrder returns null on non-201 status', () async {
      final items = createTestItems();

      when(() => mockDio.post(
            '/api/orders/create/',
            data: any(named: 'data'),
          )).thenAnswer((_) async => Response(
            data: {'error': 'something went wrong'},
            statusCode: 400,
            requestOptions: RequestOptions(path: '/api/orders/create/'),
          ));

      final container = createContainer();
      addTearDown(container.dispose);

      final service = container.read(orderServiceProvider);
      final orderId = await service.createOrder(
        address: 'ул. Пушкина, д.10',
        phone: '+79991234567',
        comment: '',
        paymentMethod: 'cash',
        totalPrice: 100.00,
        items: items,
        userId: 42,
      );

      expect(orderId, isNull);
    });

    test('createOrder uses "delivery" as default fulfillmentType', () async {
      final items = createTestItems();

      when(() => mockDio.post(
            '/api/orders/create/',
            data: any(named: 'data'),
          )).thenAnswer((_) async => Response(
            data: {'id': 100},
            statusCode: 201,
            requestOptions: RequestOptions(path: '/api/orders/create/'),
          ));

      final container = createContainer();
      addTearDown(container.dispose);

      final service = container.read(orderServiceProvider);
      // Call without specifying fulfillmentType to use default
      await service.createOrder(
        address: 'ул. Ленина, д.5',
        phone: '+79991234567',
        comment: '',
        paymentMethod: 'card',
        totalPrice: 200.00,
        items: items,
        userId: 42,
      );

      final captured = verify(() => mockDio.post(
            '/api/orders/create/',
            data: captureAny(named: 'data'),
          )).captured.single as Map<String, dynamic>;

      expect(captured['fulfillment_type'], 'delivery');
    });
  });
}
