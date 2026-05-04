from rest_framework import serializers

from apps.main.models import BroadcastMessage


class BroadcastHistorySerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()
    sentAt = serializers.DateTimeField(source="created_at")
    segment = serializers.SerializerMethodField()
    channel = serializers.SerializerMethodField()
    reach = serializers.IntegerField(read_only=True)
    opened = serializers.IntegerField(read_only=True)
    clicked = serializers.SerializerMethodField()

    class Meta:
        model = BroadcastMessage
        fields = ["id", "sentAt", "segment", "channel", "reach", "opened", "clicked"]

    def get_id(self, obj) -> str:
        return f"BR-{obj.id}"

    def get_segment(self, obj) -> str:
        if obj.send_to_all:
            return "Все клиенты"
        return "Список ID"

    def get_channel(self, obj) -> str:
        # category — это general/promo/news. Для UI показываем как канал —
        # фактически рассылки уходят в Telegram + push, для CRM-history достаточно категории.
        return obj.get_category_display() if hasattr(obj, "get_category_display") else (obj.category or "general")

    def get_clicked(self, obj) -> int:
        # В модели NewsletterDelivery нет поля clicked_at — возвращаем 0 как стаб.
        return 0
