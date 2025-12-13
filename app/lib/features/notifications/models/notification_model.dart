class NotificationModel {
  final String id;
  final String title;
  final String body;
  final DateTime date;
  final bool isRead;
  final String? type; // 'order', 'promo', 'system'

  NotificationModel({
    required this.id,
    required this.title,
    required this.body,
    required this.date,
    this.isRead = false,
    this.type = 'system',
  });

  // Для создания из JSON (когда подключим API)
  factory NotificationModel.fromJson(Map<String, dynamic> json) {
    return NotificationModel(
      id: json['id'].toString(),
      title: json['subject'] ?? 'Уведомление',
      body: json['content'] ?? '',
      date: DateTime.parse(json['created_at']),
      isRead: json['is_read'] ?? false,
      type: json['type'] ?? 'system',
    );
  }

  NotificationModel copyWith({bool? isRead}) {
    return NotificationModel(
      id: id,
      title: title,
      body: body,
      date: date,
      isRead: isRead ?? this.isRead,
      type: type,
    );
  }
}
