import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:lakshmi_market/features/address/models/address_model.dart';
import 'package:lakshmi_market/features/address/providers/address_provider.dart';

class MockFlutterSecureStorage extends Mock implements FlutterSecureStorage {}

AddressModel _makeAddress({
  String id = 'addr-1',
  String fullAddress = 'ул. Тестовая, д. 1',
}) =>
    AddressModel(id: id, fullAddress: fullAddress);

void main() {
  late MockFlutterSecureStorage mockStorage;

  setUp(() {
    mockStorage = MockFlutterSecureStorage();
  });

  group('AddressNotifier', () {
    test('initial state is empty when storage returns null', () async {
      when(() => mockStorage.read(key: any(named: 'key')))
          .thenAnswer((_) async => null);

      final notifier = AddressNotifier(storage: mockStorage);

      // Let the async _loadAddresses() complete
      await Future.delayed(Duration.zero);

      expect(notifier.debugState, isEmpty);
    });

    test('addAddress adds to state and calls storage.write', () async {
      when(() => mockStorage.read(key: any(named: 'key')))
          .thenAnswer((_) async => null);
      when(() => mockStorage.write(
            key: any(named: 'key'),
            value: any(named: 'value'),
          )).thenAnswer((_) async {});

      final notifier = AddressNotifier(storage: mockStorage);
      await Future.delayed(Duration.zero);

      final address = _makeAddress();
      notifier.addAddress(address);

      expect(notifier.debugState, hasLength(1));
      expect(notifier.debugState.first.id, 'addr-1');
      expect(notifier.debugState.first.fullAddress, 'ул. Тестовая, д. 1');

      verify(() => mockStorage.write(
            key: 'user_addresses_v1',
            value: any(named: 'value'),
          )).called(1);
    });

    test('updateAddress replaces the matching address by id', () async {
      when(() => mockStorage.read(key: any(named: 'key')))
          .thenAnswer((_) async => null);
      when(() => mockStorage.write(
            key: any(named: 'key'),
            value: any(named: 'value'),
          )).thenAnswer((_) async {});

      final notifier = AddressNotifier(storage: mockStorage);
      await Future.delayed(Duration.zero);

      notifier.addAddress(_makeAddress(id: 'addr-1', fullAddress: 'Old'));
      notifier.updateAddress(
          _makeAddress(id: 'addr-1', fullAddress: 'Updated'));

      expect(notifier.debugState, hasLength(1));
      expect(notifier.debugState.first.fullAddress, 'Updated');
    });

    test('removeAddress removes by id', () async {
      when(() => mockStorage.read(key: any(named: 'key')))
          .thenAnswer((_) async => null);
      when(() => mockStorage.write(
            key: any(named: 'key'),
            value: any(named: 'value'),
          )).thenAnswer((_) async {});

      final notifier = AddressNotifier(storage: mockStorage);
      await Future.delayed(Duration.zero);

      notifier.addAddress(_makeAddress(id: 'addr-1'));
      notifier.addAddress(_makeAddress(id: 'addr-2', fullAddress: 'Другая'));
      notifier.removeAddress('addr-1');

      expect(notifier.debugState, hasLength(1));
      expect(notifier.debugState.first.id, 'addr-2');
    });

    test('_loadAddresses loads from storage on construction', () async {
      final storedAddresses = [
        _makeAddress(id: 'saved-1', fullAddress: 'Saved Address 1').toMap(),
        _makeAddress(id: 'saved-2', fullAddress: 'Saved Address 2').toMap(),
      ];

      when(() => mockStorage.read(key: 'user_addresses_v1'))
          .thenAnswer((_) async => json.encode(storedAddresses));

      final notifier = AddressNotifier(storage: mockStorage);

      // Let the async _loadAddresses() complete
      await Future.delayed(Duration.zero);

      expect(notifier.debugState, hasLength(2));
      expect(notifier.debugState[0].id, 'saved-1');
      expect(notifier.debugState[0].fullAddress, 'Saved Address 1');
      expect(notifier.debugState[1].id, 'saved-2');
      expect(notifier.debugState[1].fullAddress, 'Saved Address 2');
    });
  });
}
