import sys

from rest_framework import serializers

from .models import AnalyticsEvent


class AnalyticsEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalyticsEvent
        fields = ["event_type", "screen", "payload"]

    def validate_event_type(self, value):
        valid = {choice[0] for choice in AnalyticsEvent.EVENT_TYPES}
        if value not in valid:
            raise serializers.ValidationError(
                f"Invalid event_type. Must be one of: {', '.join(sorted(valid))}"
            )
        return value

    def validate_payload(self, value):
        max_size = 2048
        size = sys.getsizeof(str(value))
        if size > max_size:
            raise serializers.ValidationError("Payload too large (max 2KB)")
        return value
