import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:lakshmi_market/features/address/models/address_model.dart';

void main() {
  group('AddressModel', () {
    test('toMap and fromMap round-trip preserves all fields', () {
      final address = AddressModel(
        id: 'addr-1',
        fullAddress: 'ул. Пушкина, д. 10',
        apartment: '42',
        entrance: '3',
        floor: '5',
        intercom: '42K',
        comment: 'Код домофона 1234',
        label: 'Работа',
      );

      final map = address.toMap();
      final restored = AddressModel.fromMap(map);

      expect(restored.id, 'addr-1');
      expect(restored.fullAddress, 'ул. Пушкина, д. 10');
      expect(restored.apartment, '42');
      expect(restored.entrance, '3');
      expect(restored.floor, '5');
      expect(restored.intercom, '42K');
      expect(restored.comment, 'Код домофона 1234');
      expect(restored.label, 'Работа');
    });

    test('toJson and fromJson (String-based) round-trip', () {
      final address = AddressModel(
        id: 'addr-2',
        fullAddress: 'пр. Мира, 25',
        apartment: '7',
        entrance: '1',
        floor: '2',
        intercom: '',
        comment: '',
        label: 'Дом',
      );

      final jsonString = address.toJson();
      final restored = AddressModel.fromJson(jsonString);

      expect(restored.id, 'addr-2');
      expect(restored.fullAddress, 'пр. Мира, 25');
      expect(restored.apartment, '7');
      expect(restored.label, 'Дом');

      // Verify it is actually valid JSON
      final decoded = json.decode(jsonString);
      expect(decoded, isA<Map<String, dynamic>>());
    });

    test('default label is "Дом"', () {
      final address = AddressModel(
        id: '1',
        fullAddress: 'Test Street',
      );

      expect(address.label, 'Дом');
    });

    test('empty optional fields default to empty string', () {
      final address = AddressModel(
        id: '2',
        fullAddress: 'Some Address',
      );

      expect(address.apartment, '');
      expect(address.entrance, '');
      expect(address.floor, '');
      expect(address.intercom, '');
      expect(address.comment, '');
    });

    test('copyWith preserves unchanged fields', () {
      final address = AddressModel(
        id: 'addr-3',
        fullAddress: 'Original Address',
        apartment: '10',
        entrance: '2',
        floor: '4',
        intercom: '10A',
        comment: 'Leave at door',
        label: 'Офис',
      );

      final updated = address.copyWith(apartment: '20');

      expect(updated.id, 'addr-3');
      expect(updated.fullAddress, 'Original Address');
      expect(updated.apartment, '20');
      expect(updated.entrance, '2');
      expect(updated.floor, '4');
      expect(updated.intercom, '10A');
      expect(updated.comment, 'Leave at door');
      expect(updated.label, 'Офис');
    });

    test('copyWith changes specified fields', () {
      final address = AddressModel(
        id: 'addr-4',
        fullAddress: 'Old Address',
        label: 'Дом',
      );

      final updated = address.copyWith(
        fullAddress: 'New Address',
        label: 'Дача',
        comment: 'Ring the bell',
      );

      expect(updated.fullAddress, 'New Address');
      expect(updated.label, 'Дача');
      expect(updated.comment, 'Ring the bell');
      // id should be unchanged
      expect(updated.id, 'addr-4');
    });
  });
}
