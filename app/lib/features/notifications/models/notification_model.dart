class NotificationModel {
  final String id;
  final String title;
  final String body;
  final DateTime date;
  final bool isRead;
  final String? type; // backend: personal/broadcast (и возможные будущие типы)

  NotificationModel({
    required this.id,
    required this.title,
    required this.body,
    required this.date,
    this.isRead = false,
    this.type = 'personal',
  });

  factory NotificationModel.fromJson(Map<String, dynamic> json) {
    final createdAt = (json['created_at'] ?? json['createdAt'] ?? '')
        .toString();
    DateTime parsedDate;
    try {
      parsedDate = DateTime.parse(createdAt).toLocal();
    } catch (_) {
      parsedDate = DateTime.now();
    }

    return NotificationModel(
      id: json['id'].toString(),
      title: (json['title'] ?? json['subject'] ?? 'Уведомление').toString(),
      body: (json['body'] ?? json['content'] ?? '').toString(),
      date: parsedDate,
      isRead: (json['is_read'] ?? json['isRead'] ?? false) == true,
      type: (json['type'] ?? 'personal').toString(),
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
