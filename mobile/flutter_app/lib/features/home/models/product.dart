import '../../../core/constants/api_constants.dart';

class Product {
  final String id;
  final String name;
  final double price;
  final String? imageUrl;
  final String description;
  final int stock;

  Product({
    required this.id,
    required this.name,
    required this.price,
    this.imageUrl,
    required this.description,
    required this.stock,
  });

  // Превращаем JSON от Django в объект Dart
  factory Product.fromJson(Map<String, dynamic> json) {
    return Product(
      id: json['product_code']?.toString() ?? '',
      name: json['name'] ?? 'Без названия',
      price: double.tryParse(json['price'].toString()) ?? 0.0,
      imageUrl: json['image_url'], // Тут приходит "/media/..."
      description: json['description'] ?? '',
      stock: json['stock'] ?? 0,
    );
  }

  // Умный геттер для полной ссылки на картинку
  String get fullImageUrl {
    if (imageUrl == null) {
      return 'https://placehold.co/200x200/png?text=No+Image';
    }
    if (imageUrl!.startsWith('http')) return imageUrl!;
    // Склеиваем домен + путь к файлу
    return '${ApiConstants.baseUrl}$imageUrl';
  }
}
