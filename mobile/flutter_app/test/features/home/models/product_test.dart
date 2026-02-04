import 'package:flutter_test/flutter_test.dart';
import 'package:lakshmi_market/features/home/models/product.dart';

void main() {
  group('Product', () {
    test('fromJson: product_code maps to id', () {
      final json = {
        'product_code': 'ABC-123',
        'name': 'Test Product',
        'price': '100.0',
        'description': 'A test product',
        'stock': 10,
      };

      final product = Product.fromJson(json);

      expect(product.id, 'ABC-123');
    });

    test('fromJson: missing name defaults to "Без названия"', () {
      final json = {
        'product_code': '001',
        'price': '50',
        'description': '',
        'stock': 0,
      };

      final product = Product.fromJson(json);

      expect(product.name, 'Без названия');
    });

    test('price parsed from string', () {
      final json = {
        'product_code': '002',
        'name': 'Item',
        'price': '199.99',
        'description': '',
        'stock': 5,
      };

      final product = Product.fromJson(json);

      expect(product.price, 199.99);
    });

    test('invalid price string defaults to 0.0', () {
      final json = {
        'product_code': '003',
        'name': 'Item',
        'price': 'not_a_number',
        'description': '',
        'stock': 0,
      };

      final product = Product.fromJson(json);

      expect(product.price, 0.0);
    });

    test('fullImageUrl: null imageUrl returns placeholder URL', () {
      final product = Product(
        id: '1',
        name: 'Test',
        price: 10.0,
        imageUrl: null,
        description: '',
        stock: 0,
      );

      expect(
          product.fullImageUrl, 'https://placehold.co/200x200/png?text=No+Image');
    });

    test('fullImageUrl: http URL returned as-is', () {
      final product = Product(
        id: '2',
        name: 'Test',
        price: 10.0,
        imageUrl: 'https://cdn.example.com/image.png',
        description: '',
        stock: 0,
      );

      expect(product.fullImageUrl, 'https://cdn.example.com/image.png');
    });

    test('fullImageUrl: relative path prepends baseUrl', () {
      final product = Product(
        id: '3',
        name: 'Test',
        price: 10.0,
        imageUrl: '/media/products/photo.jpg',
        description: '',
        stock: 0,
      );

      expect(product.fullImageUrl,
          'http://127.0.0.1:8000/media/products/photo.jpg');
    });
  });
}
