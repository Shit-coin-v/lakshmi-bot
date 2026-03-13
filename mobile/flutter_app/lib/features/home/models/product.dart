import '../../../core/api_client.dart';

class Product {
  final String id;
  final String name;
  final double price;
  final String? imageUrl;
  final String description;
  final double stock;

  Product({
    required this.id,
    required this.name,
    required this.price,
    this.imageUrl,
    required this.description,
    required this.stock,
  });

  // Convert Django JSON to Dart object
  factory Product.fromJson(Map<String, dynamic> json) {
    return Product(
      id: json['product_code']?.toString() ?? '',
      name: json['name'] ?? 'Без названия',
      price: double.tryParse(json['price'].toString()) ?? 0.0,
      imageUrl: json['image_url'], // Comes as "/media/..."
      description: json['description'] ?? '',
      stock: (json['stock'] as num?)?.toDouble() ?? 0.0,
    );
  }

  // Smart getter for full image URL
  String get fullImageUrl {
    if (imageUrl == null) {
      return 'https://placehold.co/200x200/png?text=No+Image';
    }
    if (imageUrl!.startsWith('http')) return imageUrl!;
    // Combine domain + file path
    return ApiClient.resolveMediaUrl(imageUrl!);
  }
}
