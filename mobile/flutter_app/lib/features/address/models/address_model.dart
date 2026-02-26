import 'dart:convert';

class AddressModel {
  final String id;
  final String fullAddress;
  final String apartment;
  final String entrance;
  final String floor;
  final String intercom;
  final String comment;
  final String label;

  AddressModel({
    required this.id,
    required this.fullAddress,
    this.apartment = '',
    this.entrance = '',
    this.floor = '',
    this.intercom = '',
    this.comment = '',
    this.label = 'Дом',
  });

  AddressModel copyWith({
    String? fullAddress,
    String? apartment,
    String? entrance,
    String? floor,
    String? intercom,
    String? comment,
    String? label,
  }) {
    return AddressModel(
      id: id,
      fullAddress: fullAddress ?? this.fullAddress,
      apartment: apartment ?? this.apartment,
      entrance: entrance ?? this.entrance,
      floor: floor ?? this.floor,
      intercom: intercom ?? this.intercom,
      comment: comment ?? this.comment,
      label: label ?? this.label,
    );
  }

  // 1. Convert object to Map (for storage)
  Map<String, dynamic> toMap() {
    return {
      'id': id,
      'fullAddress': fullAddress,
      'apartment': apartment,
      'entrance': entrance,
      'floor': floor,
      'intercom': intercom,
      'comment': comment,
      'label': label,
    };
  }

  // 2. Create object from Map (for loading)
  factory AddressModel.fromMap(Map<String, dynamic> map) {
    return AddressModel(
      id: map['id'] ?? '',
      fullAddress: map['fullAddress'] ?? '',
      apartment: map['apartment'] ?? '',
      entrance: map['entrance'] ?? '',
      floor: map['floor'] ?? '',
      intercom: map['intercom'] ?? '',
      comment: map['comment'] ?? '',
      label: map['label'] ?? 'Дом',
    );
  }

  // Helper methods for JSON
  String toJson() => json.encode(toMap());
  factory AddressModel.fromJson(String source) =>
      AddressModel.fromMap(json.decode(source));
}
