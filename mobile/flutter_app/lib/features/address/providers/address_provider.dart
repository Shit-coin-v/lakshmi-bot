import 'dart:convert';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../models/address_model.dart';

class AddressNotifier extends StateNotifier<List<AddressModel>> {
  // Создаем хранилище
  final _storage = const FlutterSecureStorage();
  static const _storageKey = 'user_addresses_v1';

  AddressNotifier() : super([]) {
    _loadAddresses(); // 👇 Загружаем при старте
  }

  // Загрузка из памяти
  Future<void> _loadAddresses() async {
    try {
      final jsonString = await _storage.read(key: _storageKey);
      if (jsonString != null) {
        final List<dynamic> decoded = json.decode(jsonString);
        state = decoded.map((map) => AddressModel.fromMap(map)).toList();
      }
    } catch (e) {
      // Если ошибка чтения (например, битый JSON), просто оставляем пустой список
      state = [];
    }
  }

  // Сохранение в память
  Future<void> _saveToStorage() async {
    final jsonString = json.encode(state.map((e) => e.toMap()).toList());
    await _storage.write(key: _storageKey, value: jsonString);
  }

  // --- МЕТОДЫ ИЗМЕНЕНИЯ (Теперь с сохранением) ---

  void addAddress(AddressModel address) {
    state = [...state, address];
    _saveToStorage(); // <-- Сохраняем!
  }

  void updateAddress(AddressModel updated) {
    state = [
      for (final addr in state)
        if (addr.id == updated.id) updated else addr,
    ];
    _saveToStorage(); // <-- Сохраняем!
  }

  void removeAddress(String id) {
    state = state.where((a) => a.id != id).toList();
    _saveToStorage(); // <-- Сохраняем!
  }
}

final addressProvider =
    StateNotifierProvider<AddressNotifier, List<AddressModel>>((ref) {
      return AddressNotifier();
    });
