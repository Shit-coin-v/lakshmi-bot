import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mocktail/mocktail.dart';

import 'package:lakshmi_market/features/orders/services/order_service.dart';
import 'package:lakshmi_market/features/orders/models/order_model.dart';
import 'package:lakshmi_market/features/orders/models/order_detail_model.dart';
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
          .overrideWith((ref) => OrderService(ref, dio: mockDio)),
    ]);
  }

  // Reusable JSON factories
  Map<String, dynamic> orderJson({
    int id = 1,
    String totalPrice = '500.00',
    String status = 'new',
    String statusDisplay = 'Новый',
    int itemsCount = 3,
    String createdAt = '2025-06-15T10:30:00Z',
  }) =>
      {
        'id': id,
        'total_price': totalPrice,
        'status': status,
        'status_display': statusDisplay,
        'items_count': itemsCount,
        'created_at': createdAt,
      };

  Map<String, dynamic> orderDetailJson({
    int id = 1,
    String createdAt = '2025-06-15T10:30:00Z',
    String status = 'new',
    String statusDisplay = 'Новый',
    String paymentMethod = 'cash',
    String address = 'ул. Пушкина, д.10',
    String phone = '+79991234567',
    String comment = 'Комментарий',
    String productsPrice = '450.00',
    String deliveryPrice = '50.00',
    String totalPrice = '500.00',
    String? fulfillmentType,
    List<Map<String, dynamic>>? items,
  }) =>
      {
        'id': id,
        'created_at': createdAt,
        'status': status,
        'status_display': statusDisplay,
        'payment_method': paymentMethod,
        'address': address,
        'phone': phone,
        'comment': comment,
        'products_price': productsPrice,
        'delivery_price': deliveryPrice,
        'total_price': totalPrice,
        if (fulfillmentType != null) 'fulfillment_type': fulfillmentType,
        'items': items ??
            [
              {
                'product_code': 'P001',
                'name': 'Молоко',
                'quantity': 2,
                'price_at_moment': '89.90',
              },
              {
                'product_code': 'P002',
                'name': 'Хлеб',
                'quantity': 1,
                'price_at_moment': '45.00',
              },
            ],
      };

  group('Orders OrderService', () {
    test('fetchMyOrders returns list of OrderModel', () async {
      when(() => mockDio.get(
            '/api/orders/',
          )).thenAnswer((_) async => Response(
            data: [
              orderJson(id: 1, totalPrice: '500.00'),
              orderJson(id: 2, totalPrice: '300.00', status: 'delivered',
                  statusDisplay: 'Доставлен'),
            ],
            statusCode: 200,
            requestOptions: RequestOptions(path: '/api/orders/'),
          ));

      final container = createContainer();
      addTearDown(container.dispose);

      final service = container.read(orderServiceProvider);
      final orders = await service.fetchMyOrders();

      expect(orders, isA<List<OrderModel>>());
      expect(orders.length, 2);
      expect(orders[0].id, 1);
      expect(orders[0].totalPrice, 500.00);
      expect(orders[1].id, 2);
      expect(orders[1].status, 'delivered');
    });

    test('fetchMyOrders throws on network error', () async {
      when(() => mockDio.get('/api/orders/')).thenThrow(
        DioException(
          requestOptions: RequestOptions(path: '/api/orders/'),
          type: DioExceptionType.connectionError,
        ),
      );

      final container = createContainer();
      addTearDown(container.dispose);

      final service = container.read(orderServiceProvider);

      expect(
        () => service.fetchMyOrders(),
        throwsA(isA<Exception>().having(
          (e) => e.toString(),
          'message',
          contains('Ошибка загрузки списка'),
        )),
      );
    });

    test('fetchOrderById returns single OrderModel', () async {
      when(() => mockDio.get('/api/orders/5/')).thenAnswer((_) async =>
          Response(
            data: orderJson(id: 5, totalPrice: '750.00', status: 'assembling',
                statusDisplay: 'В сборке'),
            statusCode: 200,
            requestOptions: RequestOptions(path: '/api/orders/5/'),
          ));

      final container = createContainer();
      addTearDown(container.dispose);

      final service = container.read(orderServiceProvider);
      final order = await service.fetchOrderById(5);

      expect(order, isA<OrderModel>());
      expect(order.id, 5);
      expect(order.totalPrice, 750.00);
      expect(order.status, 'assembling');
      expect(order.statusDisplay, 'В сборке');
    });

    test('fetchOrderDetailById returns OrderDetailModel', () async {
      when(() => mockDio.get('/api/orders/5/')).thenAnswer((_) async =>
          Response(
            data: orderDetailJson(id: 5),
            statusCode: 200,
            requestOptions: RequestOptions(path: '/api/orders/5/'),
          ));

      final container = createContainer();
      addTearDown(container.dispose);

      final service = container.read(orderServiceProvider);
      final detail = await service.fetchOrderDetailById(5);

      expect(detail, isA<OrderDetailModel>());
      expect(detail.id, 5);
      expect(detail.productsPrice, 450.00);
      expect(detail.deliveryPrice, 50.00);
      expect(detail.totalPrice, 500.00);
      expect(detail.address, 'ул. Пушкина, д.10');
      expect(detail.items.length, 2);
      expect(detail.items[0].productCode, 'P001');
      expect(detail.items[0].name, 'Молоко');
      expect(detail.items[0].quantity, 2);
    });

    test('repeatOrder creates new order from existing', () async {
      // Stub GET /api/orders/10/ to return existing order detail
      when(() => mockDio.get('/api/orders/10/')).thenAnswer((_) async =>
          Response(
            data: orderDetailJson(
              id: 10,
              fulfillmentType: 'delivery',
              address: 'ул. Пушкина, д.10',
              phone: '+79991234567',
              paymentMethod: 'cash',
              comment: 'Старый комментарий',
            ),
            statusCode: 200,
            requestOptions: RequestOptions(path: '/api/orders/10/'),
          ));

      // Stub POST /api/orders/create/ to return new order
      when(() => mockDio.post(
            '/api/orders/create/',
            data: any(named: 'data'),
          )).thenAnswer((_) async => Response(
            data: {'id': 55},
            statusCode: 201,
            requestOptions: RequestOptions(path: '/api/orders/create/'),
          ));

      final container = createContainer();
      addTearDown(container.dispose);

      final service = container.read(orderServiceProvider);
      final newId = await service.repeatOrder(10, paymentMethod: 'cash');

      expect(newId, 55);

      // Verify the POST was called with correct data
      final captured = verify(() => mockDio.post(
            '/api/orders/create/',
            data: captureAny(named: 'data'),
          )).captured.single as Map<String, dynamic>;

      expect(captured['fulfillment_type'], 'delivery');
      expect(captured['address'], 'ул. Пушкина, д.10');
      expect(captured['phone'], '+79991234567');
      expect(captured['payment_method'], 'cash');
      expect(captured['comment'], contains('Повтор заказа №10'));
      expect(captured['items'], isA<List>());
      expect((captured['items'] as List).length, 2);
    });

    test('repeatOrder detects pickup from address "Самовывоз"', () async {
      // Return an order with address "Самовывоз" and no fulfillment_type
      when(() => mockDio.get('/api/orders/11/')).thenAnswer((_) async =>
          Response(
            data: orderDetailJson(
              id: 11,
              address: 'самовывоз',
              // No fulfillment_type key -- omit to trigger fallback detection
              items: [
                {
                  'product_code': 'P001',
                  'name': 'Молоко',
                  'quantity': 1,
                  'price_at_moment': '89.90',
                },
              ],
            ),
            statusCode: 200,
            requestOptions: RequestOptions(path: '/api/orders/11/'),
          ));

      when(() => mockDio.post(
            '/api/orders/create/',
            data: any(named: 'data'),
          )).thenAnswer((_) async => Response(
            data: {'id': 56},
            statusCode: 201,
            requestOptions: RequestOptions(path: '/api/orders/create/'),
          ));

      final container = createContainer();
      addTearDown(container.dispose);

      final service = container.read(orderServiceProvider);
      final newId = await service.repeatOrder(11, paymentMethod: 'cash');

      expect(newId, 56);

      final captured = verify(() => mockDio.post(
            '/api/orders/create/',
            data: captureAny(named: 'data'),
          )).captured.single as Map<String, dynamic>;

      // When fulfillment_type is absent and address is "самовывоз",
      // the service should detect it as pickup
      expect(captured['fulfillment_type'], 'pickup');
      expect(captured['address'], 'Самовывоз');
    });
  });
}
