from rest_framework import serializers

from apps.notifications.models import Notification


class UpdateFCMTokenSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField(required=False)
    user_id = serializers.IntegerField(required=False)
    fcm_token = serializers.CharField(max_length=255)
    platform = serializers.ChoiceField(choices=("android", "ios", "web"), required=False, default="android")

    def validate(self, attrs):
        customer_id = attrs.get("customer_id")
        user_id = attrs.get("user_id")

        if not customer_id and user_id:
            attrs["customer_id"] = user_id

        if not attrs.get("customer_id"):
            raise serializers.ValidationError({"customer_id": "Обязательное поле (или передай user_id)."})
        return attrs


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ("id", "user_id", "title", "body", "is_read", "created_at", "type")
        read_only_fields = fields


class NotificationReadSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    source = serializers.ChoiceField(choices=["inapp", "push"], required=False, default="inapp")
